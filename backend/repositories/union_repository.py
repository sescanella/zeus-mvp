"""
Repositorio para operaciones en la hoja Uniones (union-level tracking).

v4.0: Union-level CRUD operations with dynamic column mapping.
"""
import logging
import re
import uuid
from typing import Optional, Literal
from datetime import datetime

from backend.models.union import Union
from backend.repositories.sheets_repository import SheetsRepository, retry_on_sheets_error
from backend.core.column_map_cache import ColumnMapCache
from backend.utils.cache import get_cache
from backend.utils.date_formatter import now_chile, format_datetime_for_sheets
from backend.utils.sanitize import sanitize_for_sheets, sanitize_row_for_sheets
from backend.exceptions import SheetsConnectionError


logger = logging.getLogger(__name__)


def _normalize(name: str) -> str:
    """Normalize column name for lookup (lowercase, no spaces/underscores/slashes)."""
    return name.lower().replace(" ", "").replace("_", "").replace("/", "")


def _col_idx_to_letter(idx: int) -> str:
    """Convert a 0-based column index to a Sheets column letter (A, B, ..., Z, AA, ...)."""
    result = ""
    idx += 1
    while idx > 0:
        idx -= 1
        result = chr(65 + (idx % 26)) + result
        idx //= 26
    return result


class UnionRepository:
    """
    Repositorio para acceso a la hoja Uniones.

    Responsabilidades:
    - Query unions by TAG_SPOOL (foreign key to Operaciones)
    - Get available unions for ARM/SOLD operations
    - Count completed unions for progress tracking
    - Sum pulgadas-diámetro for metrics
    - Convert sheet rows to Union objects using dynamic mapping

    Architecture:
    - Uses ColumnMapCache for all column access (NO hardcoded indices)
    - TAG_SPOOL as foreign key (maintains v3.0 compatibility)
    - Dependency injection of SheetsRepository
    """

    def __init__(self, sheets_repo: SheetsRepository):
        """
        Initialize UnionRepository with dependency injection.

        Args:
            sheets_repo: SheetsRepository instance for Google Sheets access
        """
        self.logger = logging.getLogger(__name__)
        self.sheets_repo = sheets_repo
        self._sheet_name = "Uniones"
        self._worksheet = None  # Lazy loading

    def _get_worksheet(self):
        """
        Get worksheet instance with lazy loading (gspread.Worksheet).

        Returns:
            gspread.Worksheet for batch_update operations

        Raises:
            SheetsConnectionError: If sheet not found
        """
        if self._worksheet is None:
            try:
                spreadsheet = self.sheets_repo._get_spreadsheet()
                self._worksheet = spreadsheet.worksheet(self._sheet_name)
                self.logger.debug(f"Worksheet '{self._sheet_name}' loaded (lazy)")
            except Exception as e:
                raise SheetsConnectionError(
                    f"Failed to load worksheet '{self._sheet_name}'",
                    details=str(e)
                )
        return self._worksheet

    def get_by_ot(self, ot: str) -> list[Union]:
        """
        Query all unions for a given work order using OT as foreign key.

        This method queries Uniones.OT (Column B) directly per v4.0 architecture.
        OT is the primary foreign key: Operaciones.OT (Column C) ↔ Uniones.OT (Column B).

        Args:
            ot: Work order number to filter by (e.g., "001", "123")

        Returns:
            list[Union]: List of unions for the OT, empty if none found

        Raises:
            SheetsConnectionError: If Google Sheets read fails
        """
        try:
            # Read all rows from Uniones sheet (cached)
            all_rows = self.sheets_repo.read_worksheet(self._sheet_name)

            if not all_rows or len(all_rows) < 2:
                self.logger.debug(f"Uniones sheet is empty or header-only")
                return []

            # Get column mapping (dynamic, no hardcoded indices)
            column_map = ColumnMapCache.get_or_build(self._sheet_name, self.sheets_repo)

            # Find OT column index (Column B)
            ot_col_key = _normalize("OT")
            if ot_col_key not in column_map:
                raise ValueError(f"OT column not found in {self._sheet_name} sheet")

            ot_col_idx = column_map[ot_col_key]

            # Filter and convert matching rows
            unions = []
            for row_data in all_rows[1:]:  # Skip header (row 0)
                # Skip empty rows
                if not row_data or len(row_data) <= ot_col_idx:
                    continue

                # Check if OT matches
                if row_data[ot_col_idx] == ot:
                    try:
                        union = self._row_to_union(row_data, column_map)
                        unions.append(union)
                    except Exception as e:
                        self.logger.warning(
                            f"Failed to parse union row for OT {ot}: {e}",
                            exc_info=True
                        )
                        continue

            self.logger.debug(f"Found {len(unions)} unions for OT {ot}")
            return unions

        except Exception as e:
            self.logger.error(f"Failed to query unions for OT {ot}: {e}", exc_info=True)
            raise SheetsConnectionError(f"Failed to read Uniones sheet: {e}")

    def get_by_spool(self, tag_spool: str) -> list[Union]:
        """
        Query all unions for a given spool using TAG_SPOOL as foreign key.

        This method maintains v3.0 compatibility by using TAG_SPOOL (not OT)
        to avoid breaking Metadata references and existing queries.

        Args:
            tag_spool: TAG_SPOOL value to filter by (e.g., "OT-123")

        Returns:
            list[Union]: List of unions for the spool, empty if none found

        Raises:
            SheetsConnectionError: If Google Sheets read fails
        """
        try:
            # Read all rows from Uniones sheet (cached)
            all_rows = self.sheets_repo.read_worksheet(self._sheet_name)

            if not all_rows or len(all_rows) < 2:
                self.logger.debug(f"Uniones sheet is empty or header-only")
                return []

            # Get column mapping (dynamic, no hardcoded indices)
            column_map = ColumnMapCache.get_or_build(self._sheet_name, self.sheets_repo)

            # Find TAG_SPOOL column index
            tag_col_key = _normalize("TAG_SPOOL")
            if tag_col_key not in column_map:
                raise ValueError(f"TAG_SPOOL column not found in {self._sheet_name} sheet")

            tag_col_idx = column_map[tag_col_key]

            # Filter and convert matching rows
            unions = []
            for row_data in all_rows[1:]:  # Skip header (row 0)
                # Skip empty rows
                if not row_data or len(row_data) <= tag_col_idx:
                    continue

                # Check if TAG_SPOOL matches
                if row_data[tag_col_idx] == tag_spool:
                    try:
                        union = self._row_to_union(row_data, column_map)
                        unions.append(union)
                    except Exception as e:
                        self.logger.warning(
                            f"Failed to parse union row for {tag_spool}: {e}",
                            exc_info=True
                        )
                        continue

            self.logger.debug(f"Found {len(unions)} unions for spool {tag_spool}")
            return unions

        except Exception as e:
            self.logger.error(f"Failed to query unions for {tag_spool}: {e}", exc_info=True)
            raise SheetsConnectionError(f"Failed to read Uniones sheet: {e}")

    def get_by_ids(self, union_ids: list[str]) -> list[Union]:
        """
        Query unions by their IDs (OT+N_UNION format).

        Used by FINALIZAR workflow to calculate pulgadas for metadata logging.

        Args:
            union_ids: List of union IDs in format "OT+N_UNION" (e.g., ["001+1", "001+2"])

        Returns:
            list[Union]: List of matching unions, empty if none found

        Raises:
            SheetsConnectionError: If Google Sheets read fails
        """
        if not union_ids:
            return []

        try:
            # Read all rows from Uniones sheet (cached)
            all_rows = self.sheets_repo.read_worksheet(self._sheet_name)

            if not all_rows or len(all_rows) < 2:
                self.logger.debug(f"Uniones sheet is empty or header-only")
                return []

            # Get column mapping (dynamic, no hardcoded indices)
            column_map = ColumnMapCache.get_or_build(self._sheet_name, self.sheets_repo)

            # Find OT and N_UNION column indices
            ot_col_key = _normalize("OT")
            n_union_col_key = _normalize("N_UNION")

            if ot_col_key not in column_map or n_union_col_key not in column_map:
                raise ValueError(f"OT or N_UNION column not found in {self._sheet_name} sheet")

            ot_col_idx = column_map[ot_col_key]
            n_union_col_idx = column_map[n_union_col_key]

            # Convert union_ids to set for fast lookup
            union_ids_set = set(union_ids)

            # Filter and convert matching rows
            unions = []
            for row_data in all_rows[1:]:  # Skip header (row 0)
                # Skip empty rows
                if not row_data or len(row_data) <= max(ot_col_idx, n_union_col_idx):
                    continue

                # Synthesize union ID from OT+N_UNION
                row_ot = row_data[ot_col_idx] if ot_col_idx < len(row_data) else None
                row_n_union = row_data[n_union_col_idx] if n_union_col_idx < len(row_data) else None

                if not row_ot or not row_n_union:
                    continue

                synthesized_id = f"{row_ot}+{row_n_union}"

                # Check if ID matches
                if synthesized_id in union_ids_set:
                    try:
                        union = self._row_to_union(row_data, column_map)
                        unions.append(union)
                    except Exception as e:
                        self.logger.warning(
                            f"Failed to parse union row for ID {synthesized_id}: {e}",
                            exc_info=True
                        )
                        continue

            self.logger.debug(f"Found {len(unions)} unions for {len(union_ids)} IDs")
            return unions

        except Exception as e:
            self.logger.error(f"Failed to query unions by IDs: {e}", exc_info=True)
            raise SheetsConnectionError(f"Failed to read Uniones sheet: {e}")

    def get_disponibles_arm_by_ot(self, ot: str) -> list[Union]:
        """
        Get disponibles unions for ARM operation for a given work order.

        Convenience method that filters unions where ARM_FECHA_FIN is NULL.

        Args:
            ot: Work order number to filter by (e.g., "001", "123")

        Returns:
            list[Union]: Flat list of unions available for ARM work, empty if none

        Raises:
            SheetsConnectionError: If Google Sheets read fails
        """
        # Fetch all unions for the OT
        all_unions = self.get_by_ot(ot)

        # Filter to disponibles (ARM not yet completed)
        disponibles = [u for u in all_unions if u.arm_fecha_fin is None]

        self.logger.debug(f"Found {len(disponibles)} ARM disponibles for OT {ot}")
        return disponibles

    def get_disponibles_sold_by_ot(self, ot: str) -> list[Union]:
        """
        Get disponibles unions for SOLD operation for a given work order.

        Convenience method that filters unions where:
        - ARM_FECHA_FIN is NOT NULL (ARM must be completed first)
        - SOL_FECHA_FIN is NULL (SOLD not yet completed)

        Args:
            ot: Work order number to filter by (e.g., "001", "123")

        Returns:
            list[Union]: Flat list of unions available for SOLD work, empty if none

        Raises:
            SheetsConnectionError: If Google Sheets read fails
        """
        # Fetch all unions for the OT
        all_unions = self.get_by_ot(ot)

        # Filter to disponibles (ARM complete, SOLD not yet complete)
        disponibles = [
            u for u in all_unions
            if u.arm_fecha_fin is not None and u.sol_fecha_fin is None
        ]

        self.logger.debug(f"Found {len(disponibles)} SOLD disponibles for OT {ot}")
        return disponibles

    def get_disponibles(
        self,
        operacion: Literal["ARM", "SOLD"]
    ) -> dict[str, list[Union]]:
        """
        Get available unions for a given operation, grouped by TAG_SPOOL.

        ARM disponibles: ARM_FECHA_FIN is NULL (union not yet completed for ARM)
        SOLD disponibles: ARM_FECHA_FIN is NOT NULL and SOL_FECHA_FIN is NULL

        Args:
            operacion: Operation type ("ARM" or "SOLD")

        Returns:
            dict[str, list[Union]]: Unions grouped by TAG_SPOOL
                                    e.g., {"OT-123": [union1, union2], "OT-124": [union3]}

        Raises:
            SheetsConnectionError: If Google Sheets read fails
        """
        try:
            # Read all rows
            all_rows = self.sheets_repo.read_worksheet(self._sheet_name)

            if not all_rows or len(all_rows) < 2:
                return {}

            # Get column mapping
            column_map = ColumnMapCache.get_or_build(self._sheet_name, self.sheets_repo)

            # Parse all unions and filter
            disponibles: dict[str, list[Union]] = {}

            for row_data in all_rows[1:]:  # Skip header
                if not row_data:
                    continue

                try:
                    union = self._row_to_union(row_data, column_map)

                    # Filter based on operation
                    if operacion == "ARM":
                        # ARM disponible: ARM not yet completed
                        if union.arm_fecha_fin is None:
                            if union.tag_spool not in disponibles:
                                disponibles[union.tag_spool] = []
                            disponibles[union.tag_spool].append(union)

                    elif operacion == "SOLD":
                        # SOLD disponible: ARM complete but SOLD not yet complete
                        if union.arm_fecha_fin is not None and union.sol_fecha_fin is None:
                            if union.tag_spool not in disponibles:
                                disponibles[union.tag_spool] = []
                            disponibles[union.tag_spool].append(union)

                except Exception as e:
                    self.logger.warning(f"Failed to parse union row: {e}", exc_info=True)
                    continue

            self.logger.debug(
                f"Found {sum(len(v) for v in disponibles.values())} disponibles "
                f"unions for {operacion} across {len(disponibles)} spools"
            )
            return disponibles

        except Exception as e:
            self.logger.error(f"Failed to get disponibles for {operacion}: {e}", exc_info=True)
            raise SheetsConnectionError(f"Failed to read Uniones sheet: {e}")

    def count_completed(
        self,
        tag_spool: str,
        operacion: Literal["ARM", "SOLD"]
    ) -> int:
        """
        Count completed unions for a given spool and operation.

        Used for progress calculation (e.g., 7/10 ARM completed).

        Args:
            tag_spool: TAG_SPOOL to filter by
            operacion: Operation type ("ARM" or "SOLD")

        Returns:
            int: Number of completed unions (FECHA_FIN is not NULL)

        Raises:
            SheetsConnectionError: If Google Sheets read fails
        """
        unions = self.get_by_spool(tag_spool)

        count = 0
        for union in unions:
            if operacion == "ARM" and union.arm_fecha_fin is not None:
                count += 1
            elif operacion == "SOLD" and union.sol_fecha_fin is not None:
                count += 1

        return count

    def count_completed_arm(self, ot: str) -> int:
        """
        Count completed ARM unions for a given work order.

        v4.0: Supports Operaciones column 69 (Uniones_ARM_Completadas).
        No caching - always calculates fresh for consistency.

        Args:
            ot: Work order number (e.g., "001", "123")

        Returns:
            int: Number of unions where arm_fecha_fin is not None, 0 if OT has no unions

        Raises:
            SheetsConnectionError: If Google Sheets read fails
        """
        unions = self.get_by_ot(ot)

        count = 0
        for union in unions:
            if union.arm_fecha_fin is not None:
                count += 1

        return count

    def count_completed_sold(self, ot: str) -> int:
        """
        Count completed SOLD unions for a given work order.

        v4.0: Supports Operaciones column 70 (Uniones_SOLD_Completadas).
        No caching - always calculates fresh for consistency.
        Ensures ARM prerequisite consistency (SOLD requires ARM complete).

        Args:
            ot: Work order number (e.g., "001", "123")

        Returns:
            int: Number of unions where sol_fecha_fin is not None, 0 if OT has no unions

        Raises:
            SheetsConnectionError: If Google Sheets read fails
        """
        unions = self.get_by_ot(ot)

        count = 0
        for union in unions:
            if union.sol_fecha_fin is not None:
                count += 1

        return count

    def sum_pulgadas(
        self,
        tag_spool: str,
        operacion: Literal["ARM", "SOLD"]
    ) -> float:
        """
        Sum pulgadas-diámetro for completed unions.

        This is the primary business metric for v4.0 (not spool count).

        BREAKING CHANGE: v08-03 changed from 1 to 2 decimal precision (18.50 not 18.5).

        Args:
            tag_spool: TAG_SPOOL to filter by
            operacion: Operation type ("ARM" or "SOLD")

        Returns:
            float: Sum of DN_UNION for completed unions (2 decimal precision)

        Raises:
            SheetsConnectionError: If Google Sheets read fails
        """
        unions = self.get_by_spool(tag_spool)

        total = 0.0
        for union in unions:
            if operacion == "ARM" and union.arm_fecha_fin is not None:
                total += union.dn_union
            elif operacion == "SOLD" and union.sol_fecha_fin is not None:
                total += union.dn_union

        # Return with 2 decimal precision (v08-03 breaking change)
        return round(total, 2)

    def sum_pulgadas_arm(self, ot: str) -> float:
        """
        Sum pulgadas-diámetro for completed ARM unions.

        v4.0: Supports Operaciones column 71 (Pulgadas_ARM).

        Args:
            ot: Work order number (e.g., "001", "123")

        Returns:
            float: Sum of DN_UNION where arm_fecha_fin is not None (2 decimal precision)
                   Returns 0.00 for empty OT

        Raises:
            SheetsConnectionError: If Google Sheets read fails
        """
        unions = self.get_by_ot(ot)

        total = 0.0
        for union in unions:
            if union.arm_fecha_fin is not None:
                total += union.dn_union

        # Return with 2 decimal precision
        return round(total, 2)

    def sum_pulgadas_sold(self, ot: str) -> float:
        """
        Sum pulgadas-diámetro for completed SOLD unions.

        v4.0: Supports Operaciones column 72 (Pulgadas_SOLD).

        Args:
            ot: Work order number (e.g., "001", "123")

        Returns:
            float: Sum of DN_UNION where sol_fecha_fin is not None (2 decimal precision)
                   Returns 0.00 for empty OT

        Raises:
            SheetsConnectionError: If Google Sheets read fails
        """
        unions = self.get_by_ot(ot)

        total = 0.0
        for union in unions:
            if union.sol_fecha_fin is not None:
                total += union.dn_union

        # Return with 2 decimal precision
        return round(total, 2)

    def get_total_uniones(self, ot: str) -> int:
        """
        Count ALL union rows for a given OT, regardless of DN/TIPO completeness.

        Unlike get_by_ot which skips incomplete rows (null DN_UNION or TIPO_UNION),
        this counts every row matching the OT. This ensures Total_Uniones reflects
        the actual number of union rows, including partially-defined ones created
        via the modal with empty DN/TIPO fields.

        v4.0: Supports Operaciones column 68 (Total_Uniones).

        Args:
            ot: Work order number (e.g., "001", "123")

        Returns:
            int: Total number of union rows for the OT, 0 if OT not found or error
        """
        try:
            all_rows = self.sheets_repo.read_worksheet(self._sheet_name)
            if not all_rows or len(all_rows) < 2:
                return 0

            column_map = ColumnMapCache.get_or_build(self._sheet_name, self.sheets_repo)
            ot_col_key = _normalize("OT")
            if ot_col_key not in column_map:
                raise ValueError(f"OT column not found in {self._sheet_name} sheet")
            ot_col_idx = column_map[ot_col_key]

            count = 0
            for row_data in all_rows[1:]:
                if not row_data or len(row_data) <= ot_col_idx:
                    continue
                if str(row_data[ot_col_idx]).strip() == str(ot).strip():
                    count += 1

            return count

        except Exception as e:
            self.logger.error(f"Failed to count total uniones for OT {ot}: {e}", exc_info=True)
            return 0

    def calculate_metrics(self, ot: str) -> dict:
        """
        Calculate all union metrics for a given work order in a single call.

        More efficient than calling 5 separate methods - fetches unions once
        and calculates all metrics. Supports Operaciones columns 68-72.

        Args:
            ot: Work order number (e.g., "001", "123")

        Returns:
            dict with keys:
                - total_uniones (int): Total union count (column 68)
                - arm_completadas (int): ARM completed count (column 69)
                - sold_completadas (int): SOLD completed count (column 70)
                - pulgadas_arm (float): ARM pulgadas sum with 2 decimals (column 71)
                - pulgadas_sold (float): SOLD pulgadas sum with 2 decimals (column 72)

        Raises:
            SheetsConnectionError: If Google Sheets read fails
        """
        unions = self.get_by_ot(ot)

        # Initialize metrics
        total_uniones = len(unions)
        arm_completadas = 0
        sold_completadas = 0
        pulgadas_arm = 0.0
        pulgadas_sold = 0.0

        # Single pass calculation
        for union in unions:
            # Handle invalid DN_UNION values
            try:
                dn_value = float(union.dn_union)
            except (ValueError, TypeError):
                self.logger.warning(
                    f"Invalid DN_UNION value for union {union.id}: {union.dn_union}, skipping"
                )
                continue

            # Count and sum ARM completions
            if union.arm_fecha_fin is not None:
                arm_completadas += 1
                pulgadas_arm += dn_value

            # Count and sum SOLD completions
            if union.sol_fecha_fin is not None:
                sold_completadas += 1
                pulgadas_sold += dn_value

        return {
            "total_uniones": total_uniones,
            "arm_completadas": arm_completadas,
            "sold_completadas": sold_completadas,
            "pulgadas_arm": round(pulgadas_arm, 2),
            "pulgadas_sold": round(pulgadas_sold, 2),
        }


    def batch_update_arm(
        self,
        tag_spool: str,
        union_ids: list[str],
        worker: str,
        timestamp: datetime
    ) -> int:
        """
        # DEPRECATED: Use batch_update_arm_full instead
        Batch update ARM completion for multiple unions in a single API call.

        Performance: Updates 10 unions in < 1 second using gspread.batch_update().

        Args:
            tag_spool: TAG_SPOOL value to filter unions (e.g., "OT-123")
            union_ids: List of union IDs to mark as ARM complete
            worker: Worker who completed ARM in format 'INICIALES(ID)'
            timestamp: Completion timestamp (Chile timezone)

        Returns:
            int: Number of unions successfully updated

        Raises:
            SheetsConnectionError: If Google Sheets write fails
            ValueError: If validation fails
        """
        if not union_ids:
            self.logger.warning("batch_update_arm called with empty union_ids")
            return 0

        try:
            all_rows = self.sheets_repo.read_worksheet(self._sheet_name)
            if not all_rows or len(all_rows) < 2:
                return 0

            column_map = ColumnMapCache.get_or_build(self._sheet_name, self.sheets_repo)

            tag_spool_col_idx = column_map.get(_normalize("TAG_SPOOL"))
            ot_col_idx = column_map.get(_normalize("OT"))
            n_union_col_idx = column_map.get(_normalize("N_UNION"))
            arm_fecha_fin_col_idx = column_map.get(_normalize("ARM_FECHA_FIN"))
            arm_worker_col_idx = column_map.get(_normalize("ARM_WORKER"))

            if any(idx is None for idx in [tag_spool_col_idx, ot_col_idx, n_union_col_idx, arm_fecha_fin_col_idx, arm_worker_col_idx]):
                raise ValueError("Required columns not found in Uniones sheet")

            union_id_to_row = {}
            for row_idx, row_data in enumerate(all_rows[1:], start=2):
                if not row_data or len(row_data) <= max(tag_spool_col_idx, ot_col_idx, n_union_col_idx, arm_fecha_fin_col_idx):
                    continue

                row_tag_spool = row_data[tag_spool_col_idx] if tag_spool_col_idx < len(row_data) else None
                if row_tag_spool != tag_spool:
                    continue

                # CRITICAL FIX: Synthesize union ID from OT+N_UNION instead of reading raw ID column
                # Sheet ID column contains sequential IDs like "0011", but union_ids from frontend use "OT+N_UNION" format
                row_ot = row_data[ot_col_idx] if ot_col_idx < len(row_data) else None
                row_n_union = row_data[n_union_col_idx] if n_union_col_idx < len(row_data) else None

                if not row_ot or not row_n_union:
                    continue

                synthesized_union_id = f"{row_ot}+{row_n_union}"

                if synthesized_union_id in union_ids:
                    arm_fecha_fin = row_data[arm_fecha_fin_col_idx] if arm_fecha_fin_col_idx < len(row_data) else None
                    if arm_fecha_fin and str(arm_fecha_fin).strip():
                        self.logger.warning(f"Skipping union {synthesized_union_id} - already ARM completed")
                        continue
                    union_id_to_row[synthesized_union_id] = row_idx

            if not union_id_to_row:
                self.logger.warning(f"No valid unions found for TAG_SPOOL {tag_spool}")
                return 0
            formatted_timestamp = format_datetime_for_sheets(timestamp)

            safe_worker = sanitize_for_sheets(worker)
            batch_data = []
            for union_id, row_num in union_id_to_row.items():
                arm_fecha_fin_letter = _col_idx_to_letter(arm_fecha_fin_col_idx)
                batch_data.append({
                    'range': f'{arm_fecha_fin_letter}{row_num}',
                    'values': [[formatted_timestamp]]
                })
                arm_worker_letter = _col_idx_to_letter(arm_worker_col_idx)
                batch_data.append({
                    'range': f'{arm_worker_letter}{row_num}',
                    'values': [[safe_worker]]
                })

            @retry_on_sheets_error(max_retries=3, backoff_seconds=1.0)
            def _execute_batch():
                worksheet = self._get_worksheet()
                worksheet.batch_update(batch_data, value_input_option='USER_ENTERED')

            _execute_batch()
            ColumnMapCache.invalidate(self._sheet_name)
            get_cache().invalidate(f"worksheet:{self._sheet_name}")

            updated_count = len(union_id_to_row)
            self.logger.info(f"✅ batch_update_arm: {updated_count} unions updated for TAG_SPOOL {tag_spool}")
            return updated_count

        except Exception as e:
            self.logger.error(f"Failed to batch update ARM for TAG_SPOOL {tag_spool}: {e}", exc_info=True)
            raise SheetsConnectionError(f"Failed to batch update ARM: {e}")

    def batch_update_sold(
        self,
        tag_spool: str,
        union_ids: list[str],
        worker: str,
        timestamp: datetime
    ) -> int:
        """
        # DEPRECATED: Use batch_update_sold_full instead
        Batch update SOLD completion for multiple unions in a single API call.

        CRITICAL: Validates ARM completion before allowing SOLD update.

        Args:
            tag_spool: TAG_SPOOL value to filter unions
            union_ids: List of union IDs to mark as SOLD complete
            worker: Worker who completed SOLD in format 'INICIALES(ID)'
            timestamp: Completion timestamp (Chile timezone)

        Returns:
            int: Number of unions successfully updated

        Raises:
            SheetsConnectionError: If Google Sheets write fails
            ValueError: If validation fails (ARM not complete)
        """
        if not union_ids:
            self.logger.warning("batch_update_sold called with empty union_ids")
            return 0

        try:
            all_rows = self.sheets_repo.read_worksheet(self._sheet_name)
            if not all_rows or len(all_rows) < 2:
                return 0

            column_map = ColumnMapCache.get_or_build(self._sheet_name, self.sheets_repo)

            tag_spool_col_idx = column_map.get(_normalize("TAG_SPOOL"))
            ot_col_idx = column_map.get(_normalize("OT"))
            n_union_col_idx = column_map.get(_normalize("N_UNION"))
            arm_fecha_fin_col_idx = column_map.get(_normalize("ARM_FECHA_FIN"))
            sol_fecha_fin_col_idx = column_map.get(_normalize("SOL_FECHA_FIN"))
            sol_worker_col_idx = column_map.get(_normalize("SOL_WORKER"))

            if any(idx is None for idx in [tag_spool_col_idx, ot_col_idx, n_union_col_idx, arm_fecha_fin_col_idx, sol_fecha_fin_col_idx, sol_worker_col_idx]):
                raise ValueError("Required columns not found in Uniones sheet")

            union_id_to_row = {}
            for row_idx, row_data in enumerate(all_rows[1:], start=2):
                if not row_data or len(row_data) <= max(tag_spool_col_idx, ot_col_idx, n_union_col_idx, arm_fecha_fin_col_idx, sol_fecha_fin_col_idx):
                    continue

                row_tag_spool = row_data[tag_spool_col_idx] if tag_spool_col_idx < len(row_data) else None
                if row_tag_spool != tag_spool:
                    continue

                # CRITICAL FIX: Synthesize union ID from OT+N_UNION instead of reading raw ID column
                # Sheet ID column contains sequential IDs like "0011", but union_ids from frontend use "OT+N_UNION" format
                row_ot = row_data[ot_col_idx] if ot_col_idx < len(row_data) else None
                row_n_union = row_data[n_union_col_idx] if n_union_col_idx < len(row_data) else None

                if not row_ot or not row_n_union:
                    continue

                synthesized_union_id = f"{row_ot}+{row_n_union}"

                if synthesized_union_id in union_ids:
                    arm_fecha_fin = row_data[arm_fecha_fin_col_idx] if arm_fecha_fin_col_idx < len(row_data) else None
                    if not arm_fecha_fin or not str(arm_fecha_fin).strip():
                        self.logger.warning(f"Skipping union {synthesized_union_id} - ARM not yet completed")
                        continue

                    sol_fecha_fin = row_data[sol_fecha_fin_col_idx] if sol_fecha_fin_col_idx < len(row_data) else None
                    if sol_fecha_fin and str(sol_fecha_fin).strip():
                        self.logger.warning(f"Skipping union {synthesized_union_id} - already SOLD completed")
                        continue

                    union_id_to_row[synthesized_union_id] = row_idx

            if not union_id_to_row:
                self.logger.warning(f"No valid unions found for TAG_SPOOL {tag_spool}")
                return 0
            formatted_timestamp = format_datetime_for_sheets(timestamp)
            safe_worker = sanitize_for_sheets(worker)

            batch_data = []
            for union_id, row_num in union_id_to_row.items():
                sol_fecha_fin_letter = _col_idx_to_letter(sol_fecha_fin_col_idx)
                batch_data.append({
                    'range': f'{sol_fecha_fin_letter}{row_num}',
                    'values': [[formatted_timestamp]]
                })
                sol_worker_letter = _col_idx_to_letter(sol_worker_col_idx)
                batch_data.append({
                    'range': f'{sol_worker_letter}{row_num}',
                    'values': [[safe_worker]]
                })

            @retry_on_sheets_error(max_retries=3, backoff_seconds=1.0)
            def _execute_batch():
                worksheet = self._get_worksheet()
                worksheet.batch_update(batch_data, value_input_option='USER_ENTERED')

            _execute_batch()
            ColumnMapCache.invalidate(self._sheet_name)
            get_cache().invalidate(f"worksheet:{self._sheet_name}")

            updated_count = len(union_id_to_row)
            self.logger.info(f"✅ batch_update_sold: {updated_count} unions updated for TAG_SPOOL {tag_spool}")
            return updated_count

        except Exception as e:
            self.logger.error(f"Failed to batch update SOLD for TAG_SPOOL {tag_spool}: {e}", exc_info=True)
            raise SheetsConnectionError(f"Failed to batch update SOLD: {e}")

    def _row_to_union(self, row_data: list, column_map: dict) -> Union:
        """
        Convert a sheet row to Union object using dynamic column mapping.

        This method uses ColumnMapCache exclusively (NO hardcoded indices)
        to be resilient to column additions/reordering.

        Args:
            row_data: Single row from Google Sheets
            column_map: Column name → index mapping from ColumnMapCache

        Returns:
            Union: Parsed Union object

        Raises:
            ValueError: If required fields are missing
        """

        def get_col(col_name: str) -> Optional[str]:
            """Get column value by name using dynamic mapping."""
            normalized = _normalize(col_name)
            if normalized not in column_map:
                return None

            col_index = column_map[normalized]
            if col_index >= len(row_data):
                return None

            value = row_data[col_index]
            # Return None for empty cells
            return value if value and str(value).strip() else None

        def parse_datetime(value: Optional[str]) -> Optional[datetime]:
            """Parse datetime from Sheets format (DD-MM-YYYY HH:MM:SS)."""
            if not value:
                return None

            try:
                # Handle Sheets format: "30-01-2026 14:30:00"
                return datetime.strptime(value.strip(), "%d-%m-%Y %H:%M:%S")
            except ValueError:
                # Try alternative format without time
                try:
                    dt = datetime.strptime(value.strip(), "%d-%m-%Y")
                    return dt
                except ValueError:
                    self.logger.warning(f"Failed to parse datetime: {value}")
                    return None

        # Required fields
        # NOTE: ID column is read but overridden below (synthesized from TAG_SPOOL+N_UNION)
        # This makes backend resilient to incorrect ID format in Uniones sheet
        id_val = get_col("ID")  # Read for validation, but will be overridden
        ot_val = get_col("OT")
        tag_spool_val = get_col("TAG_SPOOL")
        n_union_val = get_col("N_UNION")
        dn_union_val = get_col("DN_UNION")
        tipo_union_val = get_col("TIPO_UNION")

        # Validate required fields
        # NOTE: id_val validation removed - we synthesize ID from TAG_SPOOL+N_UNION
        if not ot_val:
            raise ValueError("OT is required")
        if not tag_spool_val:
            raise ValueError("TAG_SPOOL is required")
        if not n_union_val:
            raise ValueError("N_UNION is required")
        if not dn_union_val:
            raise ValueError("DN_UNION is required")
        if not tipo_union_val:
            raise ValueError("TIPO_UNION is required")

        # BUGFIX: Synthesize composite ID from OT + N_UNION
        # Uniones sheet ID column may contain sequential IDs ("0011", "0012")
        # instead of composite format ("001+1", "001+2").
        # Generate correct format here to match Union model expectations.
        # CRITICAL: Use OT not TAG_SPOOL, because:
        # 1. Union IDs in Uniones sheet are OT+N_UNION (e.g., "001+1")
        # 2. Multiple spools can share same OT (many-to-one relationship)
        # 3. Union ID uniquely identifies union within an OT
        synthesized_id = f"{ot_val}+{n_union_val}"

        # Parse ARM timestamps
        arm_fecha_inicio = parse_datetime(get_col("ARM_FECHA_INICIO"))
        arm_fecha_fin = parse_datetime(get_col("ARM_FECHA_FIN"))
        arm_worker = get_col("ARM_WORKER")

        # Parse SOLD timestamps
        sol_fecha_inicio = parse_datetime(get_col("SOL_FECHA_INICIO"))
        sol_fecha_fin = parse_datetime(get_col("SOL_FECHA_FIN"))
        sol_worker = get_col("SOL_WORKER")

        # Parse NDT fields
        ndt_fecha = parse_datetime(get_col("NDT_FECHA"))
        ndt_status = get_col("NDT_STATUS")

        # Parse version field for optimistic locking
        version = get_col("version") or ""  # Default to empty if missing

        # Create Union object
        return Union(
            id=synthesized_id,  # Use synthesized composite ID (OT+N_UNION), not sheet ID column
            ot=ot_val,
            tag_spool=tag_spool_val,
            n_union=int(n_union_val),
            dn_union=float(dn_union_val),
            tipo_union=tipo_union_val,
            arm_fecha_inicio=arm_fecha_inicio,
            arm_fecha_fin=arm_fecha_fin,
            arm_worker=arm_worker,
            sol_fecha_inicio=sol_fecha_inicio,
            sol_fecha_fin=sol_fecha_fin,
            sol_worker=sol_worker,
            ndt_fecha=ndt_fecha,
            ndt_status=ndt_status,
            version=version,
        )

    def batch_update_arm_full(
        self,
        tag_spool: str,
        union_ids: list[str],
        worker: str,
        timestamp_inicio: datetime,
        timestamp_fin: datetime
    ) -> int:
        """
        Batch update ARM with INICIO + FIN + WORKER for P5 FINALIZAR workflow.

        Writes 3 columns per union:
        - ARM_WORKER: Worker who completed ARM
        - ARM_FECHA_INICIO: When spool was taken (from Fecha_Ocupacion)
        - ARM_FECHA_FIN: When FINALIZAR was confirmed

        Performance: Updates 10 unions (30 cells) in < 1 second using gspread.batch_update().

        Args:
            tag_spool: TAG_SPOOL value to filter unions (e.g., "OT-123")
            union_ids: List of union IDs to mark as ARM complete
            worker: Worker who completed ARM in format 'INICIALES(ID)'
            timestamp_inicio: Start timestamp (from Fecha_Ocupacion)
            timestamp_fin: End timestamp (when FINALIZAR confirmed)

        Returns:
            int: Number of unions successfully updated

        Raises:
            SheetsConnectionError: If Google Sheets write fails
            ValueError: If validation fails
        """
        if not union_ids:
            self.logger.warning("batch_update_arm_full called with empty union_ids")
            return 0

        try:
            all_rows = self.sheets_repo.read_worksheet(self._sheet_name)
            if not all_rows or len(all_rows) < 2:
                return 0

            column_map = ColumnMapCache.get_or_build(self._sheet_name, self.sheets_repo)

            tag_spool_col_idx = column_map.get(_normalize("TAG_SPOOL"))
            ot_col_idx = column_map.get(_normalize("OT"))
            n_union_col_idx = column_map.get(_normalize("N_UNION"))
            arm_fecha_inicio_col_idx = column_map.get(_normalize("ARM_FECHA_INICIO"))
            arm_fecha_fin_col_idx = column_map.get(_normalize("ARM_FECHA_FIN"))
            arm_worker_col_idx = column_map.get(_normalize("ARM_WORKER"))

            if any(idx is None for idx in [tag_spool_col_idx, ot_col_idx, n_union_col_idx, arm_fecha_inicio_col_idx, arm_fecha_fin_col_idx, arm_worker_col_idx]):
                raise ValueError("Required columns not found in Uniones sheet")

            union_id_to_row = {}
            for row_idx, row_data in enumerate(all_rows[1:], start=2):
                if not row_data or len(row_data) <= max(tag_spool_col_idx, ot_col_idx, n_union_col_idx):
                    continue

                row_tag_spool = row_data[tag_spool_col_idx] if tag_spool_col_idx < len(row_data) else None
                if row_tag_spool != tag_spool:
                    continue

                # Synthesize union ID from OT+N_UNION
                row_ot = row_data[ot_col_idx] if ot_col_idx < len(row_data) else None
                row_n_union = row_data[n_union_col_idx] if n_union_col_idx < len(row_data) else None

                if not row_ot or not row_n_union:
                    continue

                synthesized_union_id = f"{row_ot}+{row_n_union}"

                if synthesized_union_id in union_ids:
                    arm_fecha_fin = row_data[arm_fecha_fin_col_idx] if arm_fecha_fin_col_idx < len(row_data) else None
                    if arm_fecha_fin and str(arm_fecha_fin).strip():
                        self.logger.warning(f"Skipping union {synthesized_union_id} - already ARM completed")
                        continue
                    union_id_to_row[synthesized_union_id] = row_idx

            if not union_id_to_row:
                self.logger.warning(f"No valid unions found for TAG_SPOOL {tag_spool}")
                return 0
            formatted_timestamp_inicio = format_datetime_for_sheets(timestamp_inicio)
            formatted_timestamp_fin = format_datetime_for_sheets(timestamp_fin)
            safe_worker = sanitize_for_sheets(worker)

            batch_data = []
            for union_id, row_num in union_id_to_row.items():
                # Write ARM_WORKER
                arm_worker_letter = _col_idx_to_letter(arm_worker_col_idx)
                batch_data.append({
                    'range': f'{arm_worker_letter}{row_num}',
                    'values': [[safe_worker]]
                })
                # Write ARM_FECHA_INICIO
                arm_fecha_inicio_letter = _col_idx_to_letter(arm_fecha_inicio_col_idx)
                batch_data.append({
                    'range': f'{arm_fecha_inicio_letter}{row_num}',
                    'values': [[formatted_timestamp_inicio]]
                })
                # Write ARM_FECHA_FIN
                arm_fecha_fin_letter = _col_idx_to_letter(arm_fecha_fin_col_idx)
                batch_data.append({
                    'range': f'{arm_fecha_fin_letter}{row_num}',
                    'values': [[formatted_timestamp_fin]]
                })

            @retry_on_sheets_error(max_retries=3, backoff_seconds=1.0)
            def _execute_batch():
                worksheet = self._get_worksheet()
                worksheet.batch_update(batch_data, value_input_option='USER_ENTERED')

            _execute_batch()
            ColumnMapCache.invalidate(self._sheet_name)
            get_cache().invalidate(f"worksheet:{self._sheet_name}")

            updated_count = len(union_id_to_row)
            self.logger.info(f"✅ batch_update_arm_full: {updated_count} unions updated for TAG_SPOOL {tag_spool} (INICIO={formatted_timestamp_inicio}, FIN={formatted_timestamp_fin})")
            return updated_count

        except Exception as e:
            self.logger.error(f"Failed to batch update ARM full for TAG_SPOOL {tag_spool}: {e}", exc_info=True)
            raise SheetsConnectionError(f"Failed to batch update ARM full: {e}")

    def batch_update_sold_full(
        self,
        tag_spool: str,
        union_ids: list[str],
        worker: str,
        timestamp_inicio: datetime,
        timestamp_fin: datetime,
        skip_arm_check: bool = False
    ) -> int:
        """
        Batch update SOLD with INICIO + FIN + WORKER for P5 FINALIZAR workflow.

        Writes 3 columns per union:
        - SOL_WORKER: Worker who completed SOLD
        - SOL_FECHA_INICIO: When spool was taken (from Fecha_Ocupacion)
        - SOL_FECHA_FIN: When FINALIZAR was confirmed

        CRITICAL: Validates ARM completion before allowing SOLD update
        (unless skip_arm_check=True for legacy spools where ARM was done at spool level).

        Args:
            tag_spool: TAG_SPOOL value to filter unions
            union_ids: List of union IDs to mark as SOLD complete
            worker: Worker who completed SOLD in format 'INICIALES(ID)'
            timestamp_inicio: Start timestamp (from Fecha_Ocupacion)
            timestamp_fin: End timestamp (when FINALIZAR confirmed)

        Returns:
            int: Number of unions successfully updated

        Raises:
            SheetsConnectionError: If Google Sheets write fails
            ValueError: If validation fails (ARM not complete)
        """
        if not union_ids:
            self.logger.warning("batch_update_sold_full called with empty union_ids")
            return 0

        try:
            all_rows = self.sheets_repo.read_worksheet(self._sheet_name)
            if not all_rows or len(all_rows) < 2:
                return 0

            column_map = ColumnMapCache.get_or_build(self._sheet_name, self.sheets_repo)

            tag_spool_col_idx = column_map.get(_normalize("TAG_SPOOL"))
            ot_col_idx = column_map.get(_normalize("OT"))
            n_union_col_idx = column_map.get(_normalize("N_UNION"))
            arm_fecha_fin_col_idx = column_map.get(_normalize("ARM_FECHA_FIN"))
            sol_fecha_inicio_col_idx = column_map.get(_normalize("SOL_FECHA_INICIO"))
            sol_fecha_fin_col_idx = column_map.get(_normalize("SOL_FECHA_FIN"))
            sol_worker_col_idx = column_map.get(_normalize("SOL_WORKER"))

            if any(idx is None for idx in [tag_spool_col_idx, ot_col_idx, n_union_col_idx, arm_fecha_fin_col_idx, sol_fecha_inicio_col_idx, sol_fecha_fin_col_idx, sol_worker_col_idx]):
                raise ValueError("Required columns not found in Uniones sheet")

            union_id_to_row = {}
            for row_idx, row_data in enumerate(all_rows[1:], start=2):
                if not row_data or len(row_data) <= max(tag_spool_col_idx, ot_col_idx, n_union_col_idx, arm_fecha_fin_col_idx):
                    continue

                row_tag_spool = row_data[tag_spool_col_idx] if tag_spool_col_idx < len(row_data) else None
                if row_tag_spool != tag_spool:
                    continue

                # Synthesize union ID from OT+N_UNION
                row_ot = row_data[ot_col_idx] if ot_col_idx < len(row_data) else None
                row_n_union = row_data[n_union_col_idx] if n_union_col_idx < len(row_data) else None

                if not row_ot or not row_n_union:
                    continue

                synthesized_union_id = f"{row_ot}+{row_n_union}"

                if synthesized_union_id in union_ids:
                    # Validate ARM completion before SOLD (skip for legacy spools
                    # where ARM was done at spool level without union-level tracking)
                    arm_fecha_fin = row_data[arm_fecha_fin_col_idx] if arm_fecha_fin_col_idx < len(row_data) else None
                    if not arm_fecha_fin or not str(arm_fecha_fin).strip():
                        if not skip_arm_check:
                            raise ValueError(f"Union {synthesized_union_id} ARM not completed - cannot update SOLD")

                    sol_fecha_fin = row_data[sol_fecha_fin_col_idx] if sol_fecha_fin_col_idx < len(row_data) else None
                    if sol_fecha_fin and str(sol_fecha_fin).strip():
                        self.logger.warning(f"Skipping union {synthesized_union_id} - already SOLD completed")
                        continue

                    union_id_to_row[synthesized_union_id] = row_idx

            if not union_id_to_row:
                self.logger.warning(f"No valid unions found for TAG_SPOOL {tag_spool}")
                return 0
            formatted_timestamp_inicio = format_datetime_for_sheets(timestamp_inicio)
            formatted_timestamp_fin = format_datetime_for_sheets(timestamp_fin)
            safe_worker = sanitize_for_sheets(worker)

            batch_data = []
            for union_id, row_num in union_id_to_row.items():
                # Write SOL_WORKER
                sol_worker_letter = _col_idx_to_letter(sol_worker_col_idx)
                batch_data.append({
                    'range': f'{sol_worker_letter}{row_num}',
                    'values': [[safe_worker]]
                })
                # Write SOL_FECHA_INICIO
                sol_fecha_inicio_letter = _col_idx_to_letter(sol_fecha_inicio_col_idx)
                batch_data.append({
                    'range': f'{sol_fecha_inicio_letter}{row_num}',
                    'values': [[formatted_timestamp_inicio]]
                })
                # Write SOL_FECHA_FIN
                sol_fecha_fin_letter = _col_idx_to_letter(sol_fecha_fin_col_idx)
                batch_data.append({
                    'range': f'{sol_fecha_fin_letter}{row_num}',
                    'values': [[formatted_timestamp_fin]]
                })

            @retry_on_sheets_error(max_retries=3, backoff_seconds=1.0)
            def _execute_batch():
                worksheet = self._get_worksheet()
                worksheet.batch_update(batch_data, value_input_option='USER_ENTERED')

            _execute_batch()
            ColumnMapCache.invalidate(self._sheet_name)
            get_cache().invalidate(f"worksheet:{self._sheet_name}")

            updated_count = len(union_id_to_row)
            self.logger.info(f"✅ batch_update_sold_full: {updated_count} unions updated for TAG_SPOOL {tag_spool} (INICIO={formatted_timestamp_inicio}, FIN={formatted_timestamp_fin})")
            return updated_count

        except Exception as e:
            self.logger.error(f"Failed to batch update SOLD full for TAG_SPOOL {tag_spool}: {e}", exc_info=True)
            raise SheetsConnectionError(f"Failed to batch update SOLD full: {e}")

    def get_all_by_tag(self, tag_spool: str) -> list[dict]:
        """
        Get all unions for a spool with has_work flag for editability.

        Args:
            tag_spool: TAG_SPOOL to filter by

        Returns:
            list[dict]: Each dict has n_union, dn_union, tipo_union, has_work
        """
        try:
            all_rows = self.sheets_repo.read_worksheet(self._sheet_name)

            if not all_rows or len(all_rows) < 2:
                return []

            column_map = ColumnMapCache.get_or_build(self._sheet_name, self.sheets_repo)

            tag_col_idx = column_map.get(_normalize("TAG_SPOOL"))
            n_union_col_idx = column_map.get(_normalize("N_UNION"))
            dn_union_col_idx = column_map.get(_normalize("DN_UNION"))
            tipo_union_col_idx = column_map.get(_normalize("TIPO_UNION"))
            arm_worker_col_idx = column_map.get(_normalize("ARM_WORKER"))
            sol_worker_col_idx = column_map.get(_normalize("SOL_WORKER"))
            ot_col_idx = column_map.get(_normalize("OT"))

            if any(idx is None for idx in [tag_col_idx, n_union_col_idx, dn_union_col_idx, tipo_union_col_idx]):
                raise ValueError("Required columns not found in Uniones sheet")

            results = []
            for row_data in all_rows[1:]:
                if not row_data or len(row_data) <= tag_col_idx:
                    continue

                if row_data[tag_col_idx] != tag_spool:
                    continue

                def get_val(idx: Optional[int]) -> str:
                    if idx is None or idx >= len(row_data):
                        return ""
                    return str(row_data[idx]).strip() if row_data[idx] else ""

                arm_worker = get_val(arm_worker_col_idx)
                sol_worker = get_val(sol_worker_col_idx)
                has_work = bool(arm_worker or sol_worker)

                try:
                    n_union = int(get_val(n_union_col_idx))
                except (ValueError, TypeError):
                    self.logger.warning(f"Failed to parse union row for {tag_spool}")
                    continue

                dn_raw = get_val(dn_union_col_idx)
                dn_union = float(dn_raw) if dn_raw else None
                tipo_union = get_val(tipo_union_col_idx) or None

                # Build composite ID: OT+N_UNION (e.g., "001+5")
                ot_val = get_val(ot_col_idx)
                union_id = f"{ot_val}+{n_union}" if ot_val else None

                results.append({
                    "n_union": n_union,
                    "dn_union": dn_union,
                    "tipo_union": tipo_union,
                    "has_work": has_work,
                    "id": union_id,
                    "arm_worker": arm_worker or None,
                    "sol_worker": sol_worker or None,
                })

            self.logger.debug(f"get_all_by_tag: Found {len(results)} unions for {tag_spool}")
            return results

        except Exception as e:
            self.logger.error(f"Failed to get_all_by_tag for {tag_spool}: {e}", exc_info=True)
            raise SheetsConnectionError(f"Failed to read Uniones sheet: {e}")

    def create_unions_batch(self, ot: str, tag_spool: str, unions: list) -> int:
        """
        Append new union rows to the Uniones sheet.

        Args:
            ot: Work order number
            tag_spool: Spool TAG identifier
            unions: List of dicts with n_union, dn_union, tipo_union

        Returns:
            int: Count of created unions
        """
        if not unions:
            return 0

        try:
            column_map = ColumnMapCache.get_or_build(self._sheet_name, self.sheets_repo)

            # Get all column indices
            col_names = ["ID", "OT", "N_UNION", "TAG_SPOOL", "DN_UNION", "TIPO_UNION",
                         "ARM_FECHA_INICIO", "ARM_FECHA_FIN", "ARM_WORKER",
                         "SOL_FECHA_INICIO", "SOL_FECHA_FIN", "SOL_WORKER",
                         "NDT_UNION", "R_NDT_UNION", "NDT_FECHA", "NDT_STATUS", "version"]

            col_indices = {}
            for name in col_names:
                key = _normalize(name)
                if key in column_map:
                    col_indices[name] = column_map[key]

            # Determine row width (max column index + 1)
            max_col = max(col_indices.values()) + 1

            rows_to_append = []
            for u in unions:
                row = [""] * max_col
                union_id = f"{ot}+{u['n_union']}"

                if "ID" in col_indices:
                    row[col_indices["ID"]] = union_id
                if "OT" in col_indices:
                    row[col_indices["OT"]] = ot
                if "N_UNION" in col_indices:
                    row[col_indices["N_UNION"]] = u["n_union"]
                if "TAG_SPOOL" in col_indices:
                    row[col_indices["TAG_SPOOL"]] = tag_spool
                if "DN_UNION" in col_indices:
                    row[col_indices["DN_UNION"]] = u["dn_union"] if u["dn_union"] is not None else ""
                if "TIPO_UNION" in col_indices:
                    row[col_indices["TIPO_UNION"]] = u["tipo_union"] if u["tipo_union"] is not None else ""
                if "version" in col_indices:
                    row[col_indices["version"]] = str(uuid.uuid4())

                rows_to_append.append(sanitize_row_for_sheets(row))

            @retry_on_sheets_error(max_retries=3, backoff_seconds=1.0)
            def _execute_append():
                worksheet = self._get_worksheet()
                worksheet.append_rows(rows_to_append, value_input_option='USER_ENTERED', table_range='A1')

            _execute_append()
            ColumnMapCache.invalidate(self._sheet_name)
            get_cache().invalidate(f"worksheet:{self._sheet_name}")

            self.logger.info(f"create_unions_batch: {len(rows_to_append)} unions created for {tag_spool}")
            return len(rows_to_append)

        except Exception as e:
            self.logger.error(f"Failed to create unions for {tag_spool}: {e}", exc_info=True)
            raise SheetsConnectionError(f"Failed to create unions: {e}")

    def update_unions_batch(self, tag_spool: str, unions: list) -> int:
        """
        Update DN_UNION and TIPO_UNION for existing unions.

        Args:
            tag_spool: Spool TAG identifier
            unions: List of dicts with n_union, dn_union, tipo_union

        Returns:
            int: Count of updated unions
        """
        if not unions:
            return 0

        try:
            all_rows = self.sheets_repo.read_worksheet(self._sheet_name)
            if not all_rows or len(all_rows) < 2:
                return 0

            column_map = ColumnMapCache.get_or_build(self._sheet_name, self.sheets_repo)

            tag_col_idx = column_map.get(_normalize("TAG_SPOOL"))
            n_union_col_idx = column_map.get(_normalize("N_UNION"))
            dn_union_col_idx = column_map.get(_normalize("DN_UNION"))
            tipo_union_col_idx = column_map.get(_normalize("TIPO_UNION"))

            if any(idx is None for idx in [tag_col_idx, n_union_col_idx, dn_union_col_idx, tipo_union_col_idx]):
                raise ValueError("Required columns not found in Uniones sheet")

            # Build n_union -> sheet row number mapping
            n_union_to_row: dict[int, int] = {}
            for row_idx, row_data in enumerate(all_rows[1:], start=2):
                if not row_data or len(row_data) <= max(tag_col_idx, n_union_col_idx):
                    continue
                if row_data[tag_col_idx] != tag_spool:
                    continue
                try:
                    row_n = int(row_data[n_union_col_idx])
                    n_union_to_row[row_n] = row_idx
                except (ValueError, TypeError):
                    continue

            batch_data = []
            updated = 0
            for u in unions:
                row_num = n_union_to_row.get(u["n_union"])
                if row_num is None:
                    self.logger.warning(f"Union {tag_spool}+{u['n_union']} not found for update")
                    continue

                dn_letter = _col_idx_to_letter(dn_union_col_idx)
                batch_data.append({
                    'range': f'{dn_letter}{row_num}',
                    'values': [[sanitize_for_sheets(u["dn_union"]) if u["dn_union"] is not None else ""]]
                })

                tipo_letter = _col_idx_to_letter(tipo_union_col_idx)
                batch_data.append({
                    'range': f'{tipo_letter}{row_num}',
                    'values': [[sanitize_for_sheets(u["tipo_union"]) if u["tipo_union"] is not None else ""]]
                })
                updated += 1

            if batch_data:

                @retry_on_sheets_error(max_retries=3, backoff_seconds=1.0)
                def _execute_batch():
                    worksheet = self._get_worksheet()
                    worksheet.batch_update(batch_data, value_input_option='USER_ENTERED')

                _execute_batch()
                ColumnMapCache.invalidate(self._sheet_name)
                get_cache().invalidate(f"worksheet:{self._sheet_name}")

            self.logger.info(f"update_unions_batch: {updated} unions updated for {tag_spool}")
            return updated

        except Exception as e:
            self.logger.error(f"Failed to update unions for {tag_spool}: {e}", exc_info=True)
            raise SheetsConnectionError(f"Failed to update unions: {e}")

    def delete_unions_without_work(self, tag_spool: str, n_unions_to_delete: list[int]) -> int:
        """
        Delete union rows that have no work (ARM_WORKER and SOL_WORKER empty).

        Deletes from bottom to top to avoid index shifting issues.

        Args:
            tag_spool: Spool TAG identifier
            n_unions_to_delete: List of N_UNION values to delete

        Returns:
            int: Count of deleted unions
        """
        if not n_unions_to_delete:
            return 0

        try:
            all_rows = self.sheets_repo.read_worksheet(self._sheet_name)
            if not all_rows or len(all_rows) < 2:
                return 0

            column_map = ColumnMapCache.get_or_build(self._sheet_name, self.sheets_repo)

            tag_col_idx = column_map.get(_normalize("TAG_SPOOL"))
            n_union_col_idx = column_map.get(_normalize("N_UNION"))
            arm_worker_col_idx = column_map.get(_normalize("ARM_WORKER"))
            sol_worker_col_idx = column_map.get(_normalize("SOL_WORKER"))

            if any(idx is None for idx in [tag_col_idx, n_union_col_idx]):
                raise ValueError("Required columns not found in Uniones sheet")

            n_union_set = set(n_unions_to_delete)

            # Collect rows to delete (store as list of row indices, 1-indexed)
            rows_to_delete = []
            for row_idx, row_data in enumerate(all_rows[1:], start=2):
                if not row_data or len(row_data) <= max(tag_col_idx, n_union_col_idx):
                    continue
                if row_data[tag_col_idx] != tag_spool:
                    continue
                try:
                    row_n = int(row_data[n_union_col_idx])
                except (ValueError, TypeError):
                    continue

                if row_n not in n_union_set:
                    continue

                # Safety: only delete if no work done
                def get_val(idx: Optional[int]) -> str:
                    if idx is None or idx >= len(row_data):
                        return ""
                    return str(row_data[idx]).strip() if row_data[idx] else ""

                arm_worker = get_val(arm_worker_col_idx)
                sol_worker = get_val(sol_worker_col_idx)
                if arm_worker or sol_worker:
                    self.logger.warning(f"Skipping delete of {tag_spool}+{row_n} — has work")
                    continue

                rows_to_delete.append(row_idx)

            # Delete from bottom to top
            rows_to_delete.sort(reverse=True)

            worksheet = self._get_worksheet()
            deleted_count = 0
            for row_num in rows_to_delete:
                @retry_on_sheets_error(max_retries=3, backoff_seconds=1.0)
                def _delete_row(rn=row_num):
                    worksheet.delete_rows(rn)

                try:
                    _delete_row()
                    deleted_count += 1
                except Exception as e:
                    self.logger.error(
                        f"delete_unions_without_work: failed at row {row_num} for {tag_spool} "
                        f"after {deleted_count}/{len(rows_to_delete)} deletions: {e}"
                    )
                    raise SheetsConnectionError(
                        f"Partial delete for {tag_spool}: {deleted_count}/{len(rows_to_delete)} "
                        f"rows deleted before failure at row {row_num}: {e}"
                    )

            if deleted_count > 0:
                ColumnMapCache.invalidate(self._sheet_name)
                get_cache().invalidate(f"worksheet:{self._sheet_name}")

            self.logger.info(f"delete_unions_without_work: {deleted_count} unions deleted for {tag_spool}")
            return deleted_count

        except Exception as e:
            self.logger.error(f"Failed to delete unions for {tag_spool}: {e}", exc_info=True)
            raise SheetsConnectionError(f"Failed to delete unions: {e}")

    def update_total_uniones(self, tag_spool: str, total: int) -> None:
        """
        Update Total_Uniones column in Operaciones sheet for the given spool.

        Uses RAW value_input_option to prevent Google Sheets from interpreting
        the integer as a date (USER_ENTERED would format 4 as 1900-01-03).

        Args:
            tag_spool: Spool TAG identifier
            total: New total union count
        """
        try:
            from backend.config import config
            row_num = self._find_spool_row(tag_spool)

            column_map = ColumnMapCache.get_or_build(config.HOJA_OPERACIONES_NOMBRE, self.sheets_repo)
            total_col_idx = column_map.get(_normalize("Total_Uniones"))
            if total_col_idx is None:
                raise ValueError("Total_Uniones column not found in Operaciones sheet")

            col_letter = _col_idx_to_letter(total_col_idx)
            cell_address = f"{col_letter}{row_num}"

            worksheet = self.sheets_repo._get_spreadsheet().worksheet(config.HOJA_OPERACIONES_NOMBRE)
            worksheet.update(cell_address, [[total]], value_input_option='RAW')

            get_cache().invalidate(f"worksheet:{config.HOJA_OPERACIONES_NOMBRE}")
            self.logger.info(f"update_total_uniones: {tag_spool} → {total}")
        except Exception as e:
            self.logger.error(f"Failed to update Total_Uniones for {tag_spool}: {e}", exc_info=True)
            raise SheetsConnectionError(f"Failed to update Total_Uniones: {e}")

    def _find_spool_row(self, tag_spool: str) -> int:
        """
        Find the row number of a spool in Operaciones sheet.

        Args:
            tag_spool: TAG_SPOOL to find

        Returns:
            int: 1-indexed row number

        Raises:
            ValueError: If spool not found
        """
        from backend.config import config
        from backend.core.column_map_cache import ColumnMapCache

        column_map = ColumnMapCache.get_or_build(config.HOJA_OPERACIONES_NOMBRE, self.sheets_repo)

        tag_col_idx = None
        for col_name in ["TAG_SPOOL", "SPLIT", "tag_spool"]:
            normalized = _normalize(col_name)
            if normalized in column_map:
                tag_col_idx = column_map[normalized]
                break

        if tag_col_idx is None:
            raise ValueError("TAG_SPOOL column not found in Operaciones sheet")

        column_letter = _col_idx_to_letter(tag_col_idx)
        row_num = self.sheets_repo.find_row_by_column_value(
            sheet_name=config.HOJA_OPERACIONES_NOMBRE,
            column_letter=column_letter,
            value=tag_spool
        )

        if row_num is None:
            raise ValueError(f"Spool {tag_spool} not found in Operaciones sheet")

        return row_num

    def get_by_worker_id(self, worker_id: int, fecha: Optional[str] = None) -> list[dict]:
        """
        Get all union records where a worker participated (ARM or SOLD).

        Matches on numeric ID extracted from ARM_WORKER/SOL_WORKER fields
        using regex \\((\\d+)\\) to handle any name format (e.g. "MR(93)", "Rodriguez(93)").

        A single row can match TWICE if the same worker did both ARM and SOLD.

        Args:
            worker_id: Numeric worker ID to match (e.g. 93)
            fecha: Optional date filter (DD-MM-YYYY) applied to fecha_fin

        Returns:
            list[dict]: Each dict has tag_spool, n_union, dn_union, tipo_union,
                        operacion, fecha_inicio, fecha_fin, arm_worker, sol_worker
        """
        _WORKER_ID_PATTERN = re.compile(r"\((\d+)\)")

        def extract_worker_id(raw: str) -> Optional[int]:
            """Extract numeric ID from worker string like 'MR(93)'."""
            if not raw:
                return None
            match = _WORKER_ID_PATTERN.search(raw)
            return int(match.group(1)) if match else None

        def extract_date_part(datetime_str: str) -> Optional[str]:
            """Extract DD-MM-YYYY from 'DD-MM-YYYY HH:MM:SS' or 'DD-MM-YYYY'."""
            if not datetime_str:
                return None
            return datetime_str.strip().split(" ")[0]

        try:
            all_rows = self.sheets_repo.read_worksheet(self._sheet_name)

            if not all_rows or len(all_rows) < 2:
                return []

            column_map = ColumnMapCache.get_or_build(self._sheet_name, self.sheets_repo)

            # Resolve all needed column indices dynamically
            tag_col_idx = column_map.get(_normalize("TAG_SPOOL"))
            n_union_col_idx = column_map.get(_normalize("N_UNION"))
            dn_union_col_idx = column_map.get(_normalize("DN_UNION"))
            tipo_union_col_idx = column_map.get(_normalize("TIPO_UNION"))
            arm_worker_col_idx = column_map.get(_normalize("ARM_WORKER"))
            sol_worker_col_idx = column_map.get(_normalize("SOL_WORKER"))
            arm_inicio_col_idx = column_map.get(_normalize("ARM_FECHA_INICIO"))
            arm_fin_col_idx = column_map.get(_normalize("ARM_FECHA_FIN"))
            sol_inicio_col_idx = column_map.get(_normalize("SOL_FECHA_INICIO"))
            sol_fin_col_idx = column_map.get(_normalize("SOL_FECHA_FIN"))

            required = [tag_col_idx, n_union_col_idx, arm_worker_col_idx, sol_worker_col_idx]
            if any(idx is None for idx in required):
                raise ValueError(
                    "Required columns (TAG_SPOOL, N_UNION, ARM_WORKER, SOL_WORKER) "
                    "not found in Uniones sheet"
                )

            def get_val(row: list, idx: Optional[int]) -> str:
                if idx is None or idx >= len(row):
                    return ""
                return str(row[idx]).strip() if row[idx] else ""

            results = []

            for row_data in all_rows[1:]:  # Skip header
                if not row_data or len(row_data) <= tag_col_idx:
                    continue

                arm_worker_raw = get_val(row_data, arm_worker_col_idx)
                sol_worker_raw = get_val(row_data, sol_worker_col_idx)

                arm_id = extract_worker_id(arm_worker_raw)
                sol_id = extract_worker_id(sol_worker_raw)

                matched_arm = arm_id == worker_id
                matched_sol = sol_id == worker_id

                if not matched_arm and not matched_sol:
                    continue

                # Parse common fields
                tag_spool = get_val(row_data, tag_col_idx)
                try:
                    n_union = int(get_val(row_data, n_union_col_idx))
                except (ValueError, TypeError):
                    self.logger.warning(f"Failed to parse N_UNION for worker {worker_id}")
                    continue

                dn_raw = get_val(row_data, dn_union_col_idx)
                dn_union = float(dn_raw) if dn_raw else None
                tipo_union = get_val(row_data, tipo_union_col_idx) or None

                arm_inicio = get_val(row_data, arm_inicio_col_idx)
                arm_fin = get_val(row_data, arm_fin_col_idx)
                sol_inicio = get_val(row_data, sol_inicio_col_idx)
                sol_fin = get_val(row_data, sol_fin_col_idx)

                # Emit one record per matching operation
                if matched_arm:
                    fecha_fin_val = arm_fin
                    if fecha and fecha_fin_val:
                        date_part = extract_date_part(fecha_fin_val)
                        if date_part != fecha:
                            pass  # Skip: date doesn't match
                        else:
                            results.append({
                                "tag_spool": tag_spool,
                                "n_union": n_union,
                                "dn_union": dn_union,
                                "tipo_union": tipo_union,
                                "operacion": "ARM",
                                "fecha_inicio": arm_inicio or None,
                                "fecha_fin": arm_fin or None,
                                "arm_worker": arm_worker_raw or None,
                                "sol_worker": sol_worker_raw or None,
                            })
                    elif not fecha:
                        results.append({
                            "tag_spool": tag_spool,
                            "n_union": n_union,
                            "dn_union": dn_union,
                            "tipo_union": tipo_union,
                            "operacion": "ARM",
                            "fecha_inicio": arm_inicio or None,
                            "fecha_fin": arm_fin or None,
                            "arm_worker": arm_worker_raw or None,
                            "sol_worker": sol_worker_raw or None,
                        })
                    elif fecha and not fecha_fin_val:
                        # Unfinished work: include when date filter is active (active/in-progress work)
                        results.append({
                            "tag_spool": tag_spool,
                            "n_union": n_union,
                            "dn_union": dn_union,
                            "tipo_union": tipo_union,
                            "operacion": "ARM",
                            "fecha_inicio": arm_inicio or None,
                            "fecha_fin": None,
                            "arm_worker": arm_worker_raw or None,
                            "sol_worker": sol_worker_raw or None,
                        })

                if matched_sol:
                    fecha_fin_val = sol_fin
                    if fecha and fecha_fin_val:
                        date_part = extract_date_part(fecha_fin_val)
                        if date_part != fecha:
                            pass  # Skip: date doesn't match
                        else:
                            results.append({
                                "tag_spool": tag_spool,
                                "n_union": n_union,
                                "dn_union": dn_union,
                                "tipo_union": tipo_union,
                                "operacion": "SOLD",
                                "fecha_inicio": sol_inicio or None,
                                "fecha_fin": sol_fin or None,
                                "arm_worker": arm_worker_raw or None,
                                "sol_worker": sol_worker_raw or None,
                            })
                    elif not fecha:
                        results.append({
                            "tag_spool": tag_spool,
                            "n_union": n_union,
                            "dn_union": dn_union,
                            "tipo_union": tipo_union,
                            "operacion": "SOLD",
                            "fecha_inicio": sol_inicio or None,
                            "fecha_fin": sol_fin or None,
                            "arm_worker": arm_worker_raw or None,
                            "sol_worker": sol_worker_raw or None,
                        })
                    elif fecha and not fecha_fin_val:
                        # Unfinished work: include when date filter is active (active/in-progress work)
                        results.append({
                            "tag_spool": tag_spool,
                            "n_union": n_union,
                            "dn_union": dn_union,
                            "tipo_union": tipo_union,
                            "operacion": "SOLD",
                            "fecha_inicio": sol_inicio or None,
                            "fecha_fin": None,
                            "arm_worker": arm_worker_raw or None,
                            "sol_worker": sol_worker_raw or None,
                        })

            self.logger.info(
                f"get_by_worker_id: Found {len(results)} records for worker {worker_id}"
                + (f" on {fecha}" if fecha else "")
            )
            return results

        except Exception as e:
            self.logger.error(
                f"Failed to get_by_worker_id for worker {worker_id}: {e}",
                exc_info=True
            )
            raise SheetsConnectionError(f"Failed to read Uniones sheet: {e}")
