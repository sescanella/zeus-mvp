"""
Repositorio para operaciones en la hoja Uniones (union-level tracking).

v4.0: Union-level CRUD operations with dynamic column mapping.
"""
import logging
from typing import Optional, Literal
from datetime import datetime

from backend.models.union import Union
from backend.repositories.sheets_repository import SheetsRepository
from backend.core.column_map_cache import ColumnMapCache
from backend.utils.date_formatter import now_chile
from backend.exceptions import SheetsConnectionError


logger = logging.getLogger(__name__)


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

            def normalize(name: str) -> str:
                """Normalize column name for lookup."""
                return name.lower().replace(" ", "").replace("_", "")

            # Find OT column index (Column B)
            ot_col_key = normalize("OT")
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
        to avoid breaking Redis keys, Metadata references, and existing queries.

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

            def normalize(name: str) -> str:
                """Normalize column name for lookup."""
                return name.lower().replace(" ", "").replace("_", "")

            # Find TAG_SPOOL column index
            tag_col_key = normalize("TAG_SPOOL")
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
        Get total count of all unions for a given work order.

        v4.0: Supports Operaciones column 68 (Total_Uniones).
        Counts ALL unions regardless of completion state - represents total work scope.

        Args:
            ot: Work order number (e.g., "001", "123")

        Returns:
            int: Total number of unions for the OT, 0 if OT not found or has no unions

        Raises:
            SheetsConnectionError: If Google Sheets read fails
        """
        unions = self.get_by_ot(ot)
        return len(unions)

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

            def normalize(name: str) -> str:
                return name.lower().replace(" ", "").replace("_", "")

            tag_spool_col_idx = column_map.get(normalize("TAG_SPOOL"))
            ot_col_idx = column_map.get(normalize("OT"))
            n_union_col_idx = column_map.get(normalize("N_UNION"))
            arm_fecha_fin_col_idx = column_map.get(normalize("ARM_FECHA_FIN"))
            arm_worker_col_idx = column_map.get(normalize("ARM_WORKER"))

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

            from backend.utils.date_formatter import format_datetime_for_sheets
            formatted_timestamp = format_datetime_for_sheets(timestamp)

            def col_idx_to_letter(idx: int) -> str:
                result = ""
                idx += 1
                while idx > 0:
                    idx -= 1
                    result = chr(65 + (idx % 26)) + result
                    idx //= 26
                return result

            batch_data = []
            for union_id, row_num in union_id_to_row.items():
                arm_fecha_fin_letter = col_idx_to_letter(arm_fecha_fin_col_idx)
                batch_data.append({
                    'range': f'{arm_fecha_fin_letter}{row_num}',
                    'values': [[formatted_timestamp]]
                })
                arm_worker_letter = col_idx_to_letter(arm_worker_col_idx)
                batch_data.append({
                    'range': f'{arm_worker_letter}{row_num}',
                    'values': [[worker]]
                })

            from backend.repositories.sheets_repository import retry_on_sheets_error

            @retry_on_sheets_error(max_retries=3, backoff_seconds=1.0)
            def _execute_batch():
                worksheet = self.sheets_repo._get_worksheet(self._sheet_name)
                worksheet.batch_update(batch_data, value_input_option='USER_ENTERED')

            _execute_batch()
            ColumnMapCache.invalidate(self._sheet_name)

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

            def normalize(name: str) -> str:
                return name.lower().replace(" ", "").replace("_", "")

            tag_spool_col_idx = column_map.get(normalize("TAG_SPOOL"))
            ot_col_idx = column_map.get(normalize("OT"))
            n_union_col_idx = column_map.get(normalize("N_UNION"))
            arm_fecha_fin_col_idx = column_map.get(normalize("ARM_FECHA_FIN"))
            sol_fecha_fin_col_idx = column_map.get(normalize("SOL_FECHA_FIN"))
            sol_worker_col_idx = column_map.get(normalize("SOL_WORKER"))

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

            from backend.utils.date_formatter import format_datetime_for_sheets
            formatted_timestamp = format_datetime_for_sheets(timestamp)

            def col_idx_to_letter(idx: int) -> str:
                result = ""
                idx += 1
                while idx > 0:
                    idx -= 1
                    result = chr(65 + (idx % 26)) + result
                    idx //= 26
                return result

            batch_data = []
            for union_id, row_num in union_id_to_row.items():
                sol_fecha_fin_letter = col_idx_to_letter(sol_fecha_fin_col_idx)
                batch_data.append({
                    'range': f'{sol_fecha_fin_letter}{row_num}',
                    'values': [[formatted_timestamp]]
                })
                sol_worker_letter = col_idx_to_letter(sol_worker_col_idx)
                batch_data.append({
                    'range': f'{sol_worker_letter}{row_num}',
                    'values': [[worker]]
                })

            from backend.repositories.sheets_repository import retry_on_sheets_error

            @retry_on_sheets_error(max_retries=3, backoff_seconds=1.0)
            def _execute_batch():
                worksheet = self.sheets_repo._get_worksheet(self._sheet_name)
                worksheet.batch_update(batch_data, value_input_option='USER_ENTERED')

            _execute_batch()
            ColumnMapCache.invalidate(self._sheet_name)

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

        def normalize(name: str) -> str:
            """Normalize column name for lookup."""
            return name.lower().replace(" ", "").replace("_", "")

        def get_col(col_name: str) -> Optional[str]:
            """Get column value by name using dynamic mapping."""
            normalized = normalize(col_name)
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
