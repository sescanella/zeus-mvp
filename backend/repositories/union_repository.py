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
            ot: TAG_SPOOL value (OT reference)

        Returns:
            int: Number of unions where arm_fecha_fin is not None, 0 if OT has no unions

        Raises:
            SheetsConnectionError: If Google Sheets read fails
        """
        unions = self.get_by_spool(ot)

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
            ot: TAG_SPOOL value (OT reference)

        Returns:
            int: Number of unions where sol_fecha_fin is not None, 0 if OT has no unions

        Raises:
            SheetsConnectionError: If Google Sheets read fails
        """
        unions = self.get_by_spool(ot)

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
            ot: TAG_SPOOL value (OT reference)

        Returns:
            float: Sum of DN_UNION where arm_fecha_fin is not None (2 decimal precision)
                   Returns 0.00 for empty OT

        Raises:
            SheetsConnectionError: If Google Sheets read fails
        """
        unions = self.get_by_spool(ot)

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
            ot: TAG_SPOOL value (OT reference)

        Returns:
            float: Sum of DN_UNION where sol_fecha_fin is not None (2 decimal precision)
                   Returns 0.00 for empty OT

        Raises:
            SheetsConnectionError: If Google Sheets read fails
        """
        unions = self.get_by_spool(ot)

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
            ot: TAG_SPOOL value (OT reference)

        Returns:
            int: Total number of unions for the OT, 0 if OT not found or has no unions

        Raises:
            SheetsConnectionError: If Google Sheets read fails
        """
        unions = self.get_by_spool(ot)
        return len(unions)

    def calculate_metrics(self, ot: str) -> dict:
        """
        Calculate all union metrics for a given work order in a single call.

        More efficient than calling 5 separate methods - fetches unions once
        and calculates all metrics. Supports Operaciones columns 68-72.

        Args:
            ot: TAG_SPOOL value (OT reference)

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
        unions = self.get_by_spool(ot)

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
        id_val = get_col("ID")
        ot_val = get_col("OT")
        tag_spool_val = get_col("TAG_SPOOL")
        n_union_val = get_col("N_UNION")
        dn_union_val = get_col("DN_UNION")
        tipo_union_val = get_col("TIPO_UNION")
        creado_por_val = get_col("Creado_Por")
        fecha_creacion_val = get_col("Fecha_Creacion")

        # Validate required fields
        if not id_val:
            raise ValueError("ID is required")
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
        if not creado_por_val:
            raise ValueError("Creado_Por is required")
        if not fecha_creacion_val:
            raise ValueError("Fecha_Creacion is required")

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

        # Parse audit fields
        version = get_col("version") or ""  # Default to empty if missing
        modificado_por = get_col("Modificado_Por")
        fecha_modificacion = parse_datetime(get_col("Fecha_Modificacion"))

        # Create Union object
        return Union(
            id=id_val,
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
            creado_por=creado_por_val,
            fecha_creacion=parse_datetime(fecha_creacion_val) or now_chile(),
            modificado_por=modificado_por,
            fecha_modificacion=fecha_modificacion,
        )
