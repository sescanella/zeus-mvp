"""
UnionService for batch union operations and workflow orchestration.

v4.0: Handles union selection, batch updates, metrics calculation, and metadata event building.
"""
import logging
from typing import Literal
from datetime import datetime

from backend.models.union import Union
from backend.models.metadata import MetadataEvent
from backend.repositories.union_repository import UnionRepository
from backend.repositories.metadata_repository import MetadataRepository
from backend.repositories.sheets_repository import SheetsRepository
from backend.exceptions import SheetsConnectionError


logger = logging.getLogger(__name__)


# SOLD_REQUIRED_TYPES: Union types that require SOLD operation
# FW unions are ARM-only (no SOLD needed)
SOLD_REQUIRED_TYPES = ['BW', 'BR', 'SO', 'FILL', 'LET']


class UnionService:
    """
    Service layer for union-level operations.

    Orchestrates union selection workflows with:
    - Batch updates to UnionRepository (ARM/SOLD completions)
    - Metrics calculation (pulgadas-diámetro sums)
    - Metadata event building (batch + granular audit trail)

    Architecture:
    - Dependency injection (UnionRepository, MetadataRepository, SheetsRepository)
    - Business logic bridge between API and data layer
    - Performance: < 1s for 10 union batch operations
    """

    def __init__(
        self,
        union_repo: UnionRepository,
        metadata_repo: MetadataRepository,
        sheets_repo: SheetsRepository
    ):
        """
        Initialize UnionService with dependency injection.

        Args:
            union_repo: UnionRepository instance for union data access
            metadata_repo: MetadataRepository instance for event logging
            sheets_repo: SheetsRepository instance for Google Sheets access
        """
        self.logger = logging.getLogger(__name__)
        self.union_repo = union_repo
        self.metadata_repo = metadata_repo
        self.sheets_repo = sheets_repo

    def process_selection(
        self,
        tag_spool: str,
        union_ids: list[str],
        worker_id: int,
        worker_nombre: str,
        operacion: Literal["ARM", "SOLD"]
    ) -> dict:
        """
        Orchestrate batch union updates for selected unions.

        Workflow:
        1. Validate selected union IDs exist and are available
        2. Call appropriate batch_update method from UnionRepository
        3. Build and log metadata events (batch + granular)
        4. Return processing summary

        Args:
            tag_spool: TAG_SPOOL value (e.g., "OT-123")
            union_ids: List of union IDs to mark as complete (e.g., ["OT-123+1", "OT-123+2"])
            worker_id: Worker ID
            worker_nombre: Worker name in format 'INICIALES(ID)'
            operacion: Operation type ("ARM" or "SOLD")

        Returns:
            dict with keys:
                - union_count (int): Number of unions processed
                - action (str): Action taken (e.g., "ARM_COMPLETAR")
                - pulgadas (float): Total pulgadas-diámetro (1 decimal)
                - event_count (int): Number of metadata events logged

        Raises:
            SheetsConnectionError: If batch update or event logging fails
            ValueError: If validation fails
        """
        if not union_ids:
            raise ValueError("union_ids cannot be empty")

        self.logger.info(
            f"Processing selection: {len(union_ids)} unions for {tag_spool} ({operacion})"
        )

        # Step 1: Validate unions exist and are available
        # Fetch all unions for this spool
        all_unions = self.union_repo.get_by_spool(tag_spool)
        if not all_unions:
            raise ValueError(f"No unions found for spool {tag_spool}")

        # Build map of union_id -> Union for validation
        union_map = {u.id: u for u in all_unions}

        # Validate all selected union IDs exist
        missing_ids = [uid for uid in union_ids if uid not in union_map]
        if missing_ids:
            raise ValueError(f"Union IDs not found: {missing_ids}")

        # Get the selected unions
        selected_unions = [union_map[uid] for uid in union_ids]

        # Validate ownership (all unions belong to same OT)
        if not self.validate_union_ownership(selected_unions):
            raise ValueError("All unions must belong to the same OT")

        # Filter for availability (check if unions can be completed for this operation)
        available_unions = self.filter_available_unions(selected_unions, operacion)
        if len(available_unions) != len(selected_unions):
            unavailable_count = len(selected_unions) - len(available_unions)
            self.logger.warning(
                f"{unavailable_count} unions are not available for {operacion}"
            )
            # Update selected_unions to only process available ones
            selected_unions = available_unions
            union_ids = [u.id for u in available_unions]

        # Step 2: Call batch update method based on operation
        from backend.utils.date_formatter import now_chile
        timestamp = now_chile()

        if operacion == "ARM":
            updated_count = self.union_repo.batch_update_arm(
                tag_spool=tag_spool,
                union_ids=union_ids,
                worker=worker_nombre,
                timestamp=timestamp
            )
        elif operacion == "SOLD":
            updated_count = self.union_repo.batch_update_sold(
                tag_spool=tag_spool,
                union_ids=union_ids,
                worker=worker_nombre,
                timestamp=timestamp
            )
        else:
            raise ValueError(f"Invalid operacion: {operacion}")

        self.logger.info(f"Batch update complete: {updated_count} unions updated")

        # Step 3: Calculate pulgadas for selected unions
        pulgadas = self.calcular_pulgadas(selected_unions)

        # Step 4: Build and log metadata events
        eventos = self.build_eventos_metadata(
            tag_spool=tag_spool,
            worker_id=worker_id,
            worker_nombre=worker_nombre,
            operacion=operacion,
            union_ids=union_ids,
            pulgadas=pulgadas
        )

        # Batch log all events
        self.metadata_repo.batch_log_events(eventos)

        self.logger.info(
            f"Metadata events logged: {len(eventos)} events "
            f"({updated_count} unions, {pulgadas} pulgadas)"
        )

        # Step 5: Return processing summary
        return {
            "union_count": updated_count,
            "action": f"{operacion}_COMPLETAR",
            "pulgadas": round(pulgadas, 1),  # 1 decimal precision
            "event_count": len(eventos)
        }

    def calcular_pulgadas(self, unions: list[Union]) -> float:
        """
        Sum pulgadas-diámetro for a list of unions.

        Uses 1 decimal precision per task requirements.
        Handles None values gracefully by skipping them.

        Args:
            unions: List of Union objects

        Returns:
            float: Sum of DN_UNION values with 1 decimal place (e.g., 18.5)

        Example:
            >>> unions = [Union(dn_union=4.0, ...), Union(dn_union=6.5, ...)]
            >>> service.calcular_pulgadas(unions)
            10.5
        """
        if not unions:
            return 0.0

        total = 0.0
        for union in unions:
            try:
                # Handle potential None values gracefully
                if union.dn_union is not None:
                    total += float(union.dn_union)
            except (ValueError, TypeError) as e:
                self.logger.warning(
                    f"Invalid DN_UNION value for union {union.id}: {union.dn_union}, "
                    f"skipping. Error: {e}"
                )
                continue

        # Return with 1 decimal precision per task requirements
        return round(total, 1)

    def build_eventos_metadata(
        self,
        tag_spool: str,
        worker_id: int,
        worker_nombre: str,
        operacion: Literal["ARM", "SOLD"],
        union_ids: list[str],
        pulgadas: float
    ) -> list[MetadataEvent]:
        """
        Build metadata events for audit trail.

        Creates two types of events:
        1. Batch event at spool level (N_UNION=None) with pulgadas calculation
        2. Granular events per union (N_UNION=union_number)

        Args:
            tag_spool: TAG_SPOOL value
            worker_id: Worker ID
            worker_nombre: Worker name in format 'INICIALES(ID)'
            operacion: Operation type ("ARM" or "SOLD")
            union_ids: List of union IDs (format: "OT-123+5")
            pulgadas: Total pulgadas-diámetro calculated

        Returns:
            list[MetadataEvent]: Events ready for batch_log_events

        Example:
            For ARM operation with 2 unions:
            - 1 batch event (N_UNION=None, metadata has pulgadas)
            - 2 granular events (N_UNION=1, N_UNION=2)
        """
        # Placeholder implementation (will be implemented in Task 4)
        raise NotImplementedError("build_eventos_metadata will be implemented in Task 4")

    def validate_union_ownership(self, unions: list[Union]) -> bool:
        """
        Validate that all unions belong to the same OT.

        Args:
            unions: List of Union objects to validate

        Returns:
            bool: True if all unions have the same OT, False otherwise

        Example:
            >>> unions = [Union(ot="001", ...), Union(ot="001", ...)]
            >>> service.validate_union_ownership(unions)
            True
            >>> unions = [Union(ot="001", ...), Union(ot="002", ...)]
            >>> service.validate_union_ownership(unions)
            False
        """
        # Placeholder implementation (will be implemented in Task 5)
        raise NotImplementedError("validate_union_ownership will be implemented in Task 5")

    def filter_available_unions(
        self,
        unions: list[Union],
        operacion: Literal["ARM", "SOLD"]
    ) -> list[Union]:
        """
        Filter unions based on operation type availability.

        ARM: Returns unions where arm_fecha_fin is None
        SOLD: Returns unions where arm_fecha_fin is not None and sol_fecha_fin is None

        Args:
            unions: List of Union objects to filter
            operacion: Operation type ("ARM" or "SOLD")

        Returns:
            list[Union]: Filtered unions available for the operation

        Example:
            >>> # ARM filter
            >>> unions = [Union(arm_fecha_fin=None, ...), Union(arm_fecha_fin=datetime.now(), ...)]
            >>> service.filter_available_unions(unions, "ARM")
            [Union(arm_fecha_fin=None, ...)]
        """
        # Placeholder implementation (will be implemented in Task 5)
        raise NotImplementedError("filter_available_unions will be implemented in Task 5")

    def get_sold_required_types(self) -> list[str]:
        """
        Get list of union types that require SOLD operation.

        FW unions are ARM-only and do not require SOLD.

        Returns:
            list[str]: Union types that require SOLD ['BW', 'BR', 'SO', 'FILL', 'LET']

        Example:
            >>> service.get_sold_required_types()
            ['BW', 'BR', 'SO', 'FILL', 'LET']
        """
        # Placeholder implementation (will be implemented in Task 5)
        raise NotImplementedError("get_sold_required_types will be implemented in Task 5")
