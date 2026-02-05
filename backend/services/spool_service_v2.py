"""
Servicio de Spools v2.1 con Direct Read (sin Event Sourcing).

Diferencias vs v2.0:
- Lee estados directamente desde columnas de Operaciones (NO reconstruye desde Metadata)
- Más simple, más rápido, más confiable
- Reglas de negocio basadas en presencia de datos en columnas:
  * INICIAR ARM: Fecha_Materiales llena Y Armador vacía
  * COMPLETAR ARM: Armador lleno Y Fecha_Armado vacía
  * INICIAR SOLD: Fecha_Armado llena Y Soldador vacío
  * COMPLETAR SOLD: Soldador lleno Y Fecha_Soldadura vacía

v2.2 Features (preserved):
- Mapeo dinámico de columnas (ColumnMapCache)
- Validación de columnas críticas al inicio
- Resistente a cambios en estructura del spreadsheet
- Logging detallado

Autor: ZEUES Team
Fecha: 2026-01-20 (v2.1 Direct Read)
"""
import logging
from typing import Optional

from backend.repositories.sheets_repository import SheetsRepository
from backend.services.sheets_service import SheetsService
from backend.core.column_map_cache import ColumnMapCache
from backend.models.spool import Spool
from backend.models.enums import ActionStatus
from backend.config import config

logger = logging.getLogger(__name__)


class SpoolServiceV2:
    """
    Servicio de spools con mapeo dinámico de columnas.

    Resuelve el problema de índices hardcodeados que se vuelven
    obsoletos cuando cambia la estructura del spreadsheet.
    """

    def __init__(
        self,
        sheets_repository: Optional[SheetsRepository] = None
    ):
        """
        Inicializa el servicio con repositorio de Sheets (v2.1 Direct Read).

        v2.1: Lee estados directamente desde columnas de Operaciones.
        v2.2: Usa ColumnMapCache para mapeo dinámico (lazy loading).

        Args:
            sheets_repository: Repositorio para acceso a Google Sheets
        """
        self.sheets_repository = sheets_repository or SheetsRepository()

        # v2.2: Obtener column_map desde cache (lazy load)
        self.column_map = ColumnMapCache.get_or_build(
            config.HOJA_OPERACIONES_NOMBRE,
            self.sheets_repository
        )

        # Crear SheetsService con column_map
        self.sheets_service = SheetsService(column_map=self.column_map)

        # Validar columnas críticas
        critical_columns = [
            "SPLIT",  # Spool identifier (actual column name in Sheet, NOT TAG_SPOOL)
            "Fecha_Materiales",
            "Fecha_Armado",
            "Armador",
            "Fecha_Soldadura",
            "Soldador",
            "Fecha_QC_Metrología"
        ]

        all_present, missing = ColumnMapCache.validate_critical_columns(
            config.HOJA_OPERACIONES_NOMBRE,
            critical_columns
        )

        if not all_present:
            raise ValueError(
                f"Missing critical columns in Operaciones sheet: {missing}. "
                f"Check Google Sheets structure."
            )

        logger.info(f"SpoolServiceV2 initialized with {len(self.column_map)} columns (v2.1 Direct Read)")

    def parse_spool_row(self, row: list) -> Spool:
        """
        Parsea una fila de Operaciones a objeto Spool usando mapeo dinámico.

        Args:
            row: Lista con valores de la fila

        Returns:
            Spool con datos base (estados PENDIENTE por defecto)

        Raises:
            ValueError: Si TAG_SPOOL está vacío
        """
        # Obtener índices dinámicamente por nombre de columna (column_map ya inicializado en constructor)
        idx_tag_spool = self.sheets_service._get_col_idx("TAG_SPOOL", fallback_idx=6)
        idx_ot = self.sheets_service._get_col_idx("OT", fallback_idx=1)
        idx_nv = self.sheets_service._get_col_idx("NV", fallback_idx=7)
        idx_fecha_materiales = self.sheets_service._get_col_idx("Fecha_Materiales", fallback_idx=32)
        idx_fecha_armado = self.sheets_service._get_col_idx("Fecha_Armado", fallback_idx=33)
        idx_armador = self.sheets_service._get_col_idx("Armador", fallback_idx=34)
        idx_fecha_soldadura = self.sheets_service._get_col_idx("Fecha_Soldadura", fallback_idx=35)
        idx_soldador = self.sheets_service._get_col_idx("Soldador", fallback_idx=36)
        idx_fecha_qc_metrologia = self.sheets_service._get_col_idx("Fecha_QC_Metrología", fallback_idx=37)
        idx_total_uniones = self.sheets_service._get_col_idx("Total_Uniones", fallback_idx=67)

        logger.debug(
            f"Column indices: TAG_SPOOL={idx_tag_spool}, "
            f"Fecha_Armado={idx_fecha_armado}, Armador={idx_armador}"
        )

        # Validar y rellenar fila si es corta
        required_len = max(idx_tag_spool, idx_fecha_armado, idx_armador, idx_soldador, idx_fecha_qc_metrologia, idx_total_uniones) + 1
        if len(row) < required_len:
            row = row + [''] * (required_len - len(row))

        # 1. TAG_SPOOL (obligatorio)
        tag_spool = row[idx_tag_spool].strip() if row[idx_tag_spool] else None
        if not tag_spool:
            raise ValueError("TAG_SPOOL vacío")

        # 2. OT (opcional) - v4.0 Foreign key para Uniones sheet
        ot = row[idx_ot].strip() if idx_ot < len(row) and row[idx_ot] else None
        if ot == '':
            ot = None

        # 3. NV (opcional)
        nv = row[idx_nv].strip() if idx_nv < len(row) and row[idx_nv] else None
        if nv == '':
            nv = None

        # 4. Estados ARM/SOLD siempre PENDIENTE (se reconstruyen desde Metadata)
        arm_status = ActionStatus.PENDIENTE
        sold_status = ActionStatus.PENDIENTE

        # 5. Parsear fechas usando SheetsService.parse_date()
        fecha_materiales = SheetsService.parse_date(row[idx_fecha_materiales] if idx_fecha_materiales < len(row) else "")
        fecha_armado = SheetsService.parse_date(row[idx_fecha_armado] if idx_fecha_armado < len(row) else "")
        fecha_soldadura = SheetsService.parse_date(row[idx_fecha_soldadura] if idx_fecha_soldadura < len(row) else "")
        fecha_qc_metrologia = SheetsService.parse_date(row[idx_fecha_qc_metrologia] if idx_fecha_qc_metrologia < len(row) else "")

        # 6. Parsear trabajadores
        armador = row[idx_armador].strip() if idx_armador < len(row) and row[idx_armador] else None
        if armador == '':
            armador = None

        soldador = row[idx_soldador].strip() if idx_soldador < len(row) and row[idx_soldador] else None
        if soldador == '':
            soldador = None

        # 7. v4.0: Parse Total_Uniones (columna 68) con validación
        total_uniones_raw = row[idx_total_uniones] if idx_total_uniones < len(row) and row[idx_total_uniones] else None
        total_uniones = None
        if total_uniones_raw:
            try:
                total_uniones = int(total_uniones_raw)
                if total_uniones < 0:
                    logger.warning(f"Negative Total_Uniones for {tag_spool}: {total_uniones}, defaulting to None")
                    total_uniones = None
            except (ValueError, TypeError):
                logger.warning(f"Invalid Total_Uniones for {tag_spool}: {total_uniones_raw}, defaulting to None")
                total_uniones = None

        # 8. v3.0: Parse Ocupado_Por (columna 64)
        idx_ocupado_por = self.sheets_service._get_col_idx("Ocupado_Por", fallback_idx=64)
        ocupado_por_raw = row[idx_ocupado_por].strip() if idx_ocupado_por < len(row) and row[idx_ocupado_por] else None
        ocupado_por = ocupado_por_raw if ocupado_por_raw else None

        return Spool(
            tag_spool=tag_spool,
            ot=ot,  # v4.0: Orden de Trabajo (FK para Uniones)
            nv=nv,
            total_uniones=total_uniones,  # v4.0: version detection field
            arm=arm_status,
            sold=sold_status,
            fecha_materiales=fecha_materiales,
            fecha_armado=fecha_armado,
            armador=armador,
            fecha_soldadura=fecha_soldadura,
            soldador=soldador,
            fecha_qc_metrologia=fecha_qc_metrologia,
            proyecto=None,
            ocupado_por=ocupado_por  # v3.0: Current occupation lock
        )

    def get_spools_disponibles_para_iniciar_arm(self) -> list[Spool]:
        """
        MIGRATED: Usa get_spools_disponibles("ARM", "INICIAR") internamente.

        REGLA DE NEGOCIO v3.0 (FilterRegistry - 2026-02-05):
        - Fecha_Materiales: CON DATO (prerequisito cumplido)
        - Ocupado_Por: SIN DATO (spool no está ocupado actualmente)

        Incluye spools:
        - PENDIENTE: nunca iniciados (Armador=None, Ocupado_Por=None)
        - PAUSADO: pausados (Armador!=None, Ocupado_Por=None)

        CAMBIOS vs v3.0:
        - ✅ Usa FilterRegistry (lógica centralizada)
        - ✅ Misma lógica: PrerequisiteFilter(fecha_materiales) + OcupacionFilter()
        - ✅ Logging detallado por filtro

        DEPRECATED (2026-02-05): Use get_spools_disponibles("ARM", "INICIAR") instead.
        Will be removed in v5.0 (estimated 2026-04-01).

        Returns:
            Lista de spools que cumplen las condiciones
        """
        logger.warning(
            "[DEPRECATED] get_spools_disponibles_para_iniciar_arm() is deprecated. "
            "Use get_spools_disponibles('ARM', 'INICIAR') instead."
        )

        # Delegar al método unificado
        return self.get_spools_disponibles("ARM", "INICIAR")

    def get_spools_disponibles_para_completar_arm(self) -> list[Spool]:
        """
        Obtiene spools disponibles para COMPLETAR ARM (v2.1 Direct Read).

        REGLA DE NEGOCIO v2.1 (Direct Read - 2026-01-20):
        - Armador: CON DATO (operación iniciada)
        - Fecha_Armado: SIN DATO (operación no completada)

        Returns:
            Lista de spools que cumplen las condiciones
        """
        logger.info("[V2.1] Retrieving spools available for COMPLETAR ARM (Direct Read)")

        all_rows = self.sheets_repository.read_worksheet(config.HOJA_OPERACIONES_NOMBRE)
        spools_disponibles = []

        for row_idx, row in enumerate(all_rows[1:], start=2):
            try:
                spool = self.parse_spool_row(row)

                # REGLA v2.1: Armador lleno Y Fecha_Armado vacía (Direct Read from columns)
                if spool.armador is not None and spool.fecha_armado is None:
                    spools_disponibles.append(spool)
                    logger.debug(
                        f"[V2.1] Spool {spool.tag_spool} disponible COMPLETAR ARM: "
                        f"armador={spool.armador}, fecha_armado={spool.fecha_armado}"
                    )

            except ValueError as e:
                logger.warning(f"Skipping invalid row {row_idx}: {str(e)}")
                continue

        logger.info(f"Found {len(spools_disponibles)} spools for COMPLETAR ARM")
        return spools_disponibles

    def get_spools_disponibles_para_iniciar_sold(self) -> list[Spool]:
        """
        MIGRATED: Usa get_spools_disponibles("SOLD", "INICIAR") internamente.

        REGLA DE NEGOCIO v3.0 (FilterRegistry - 2026-02-05):
        - Fecha_Armado: CON DATO (prerequisito ARM completado)
        - Ocupado_Por: SIN DATO (spool no está ocupado actualmente)

        Incluye spools:
        - PENDIENTE: nunca iniciados (Soldador=None, Ocupado_Por=None)
        - PAUSADO: pausados (Soldador!=None, Ocupado_Por=None)

        CAMBIOS vs v3.0:
        - ✅ Usa FilterRegistry (lógica centralizada)
        - ✅ Misma lógica: PrerequisiteFilter(fecha_armado) + OcupacionFilter()
        - ✅ Logging detallado por filtro

        DEPRECATED (2026-02-05): Use get_spools_disponibles("SOLD", "INICIAR") instead.
        Will be removed in v5.0 (estimated 2026-04-01).

        Returns:
            Lista de spools que cumplen las condiciones
        """
        logger.warning(
            "[DEPRECATED] get_spools_disponibles_para_iniciar_sold() is deprecated. "
            "Use get_spools_disponibles('SOLD', 'INICIAR') instead."
        )

        # Delegar al método unificado
        return self.get_spools_disponibles("SOLD", "INICIAR")

    def get_spools_disponibles_para_completar_sold(self) -> list[Spool]:
        """
        Obtiene spools disponibles para COMPLETAR SOLD (v2.1 Direct Read).

        REGLA DE NEGOCIO v2.1 (Direct Read - 2026-01-20):
        - Soldador: CON DATO (operación iniciada)
        - Fecha_Soldadura: SIN DATO (operación no completada)

        Returns:
            Lista de spools que cumplen las condiciones
        """
        logger.info("[V2.1] Retrieving spools available for COMPLETAR SOLD (Direct Read)")

        all_rows = self.sheets_repository.read_worksheet(config.HOJA_OPERACIONES_NOMBRE)
        spools_disponibles = []

        for row_idx, row in enumerate(all_rows[1:], start=2):
            try:
                spool = self.parse_spool_row(row)

                # REGLA v2.1: Soldador lleno Y Fecha_Soldadura vacía (Direct Read from columns)
                if spool.soldador is not None and spool.fecha_soldadura is None:
                    spools_disponibles.append(spool)
                    logger.debug(
                        f"[V2.1] Spool {spool.tag_spool} disponible COMPLETAR SOLD: "
                        f"soldador={spool.soldador}, fecha_soldadura={spool.fecha_soldadura}"
                    )

            except ValueError as e:
                logger.warning(f"Skipping invalid row {row_idx}: {str(e)}")
                continue

        logger.info(f"Found {len(spools_disponibles)} spools for COMPLETAR SOLD")
        return spools_disponibles

    def get_spools_disponibles_para_cancelar_arm(self, worker_id: int) -> list[Spool]:
        """
        Obtiene spools EN_PROGRESO de ARM del trabajador para CANCELAR (v2.1 Direct Read).

        NOTE: Currently not exposed via GET endpoint. Used internally by CANCELAR workflow.
        POST /api/cancelar-accion exists but no GET /api/spools/cancelar endpoint yet.
        TODO: Add GET endpoint if UI needs to list cancellable spools.

        REGLA DE NEGOCIO v2.1 (Direct Read - 2026-01-20):
        - Armador: CON DATO en formato "XX(ID)" donde ID = worker_id
        - Fecha_Armado: SIN DATO (operación no completada)
        - Ownership: Solo spools donde armador contiene "(worker_id)"

        Args:
            worker_id: ID numérico del trabajador para filtrar ownership

        Returns:
            Lista de spools EN_PROGRESO del trabajador específico
        """
        logger.info(f"[V2.1] Retrieving spools available for CANCELAR ARM by worker_id={worker_id} (Direct Read)")

        all_rows = self.sheets_repository.read_worksheet(config.HOJA_OPERACIONES_NOMBRE)
        spools_disponibles = []

        for row_idx, row in enumerate(all_rows[1:], start=2):
            try:
                spool = self.parse_spool_row(row)

                # REGLA v2.1: Armador lleno Y Fecha_Armado vacía Y Ownership
                if (spool.armador is not None and
                    spool.fecha_armado is None and
                    f"({worker_id})" in spool.armador):
                    spools_disponibles.append(spool)
                    logger.debug(
                        f"[V2.1] Spool {spool.tag_spool} disponible CANCELAR ARM: "
                        f"armador={spool.armador}, fecha_armado={spool.fecha_armado}, worker_id={worker_id}"
                    )

            except ValueError as e:
                logger.warning(f"Skipping invalid row {row_idx}: {str(e)}")
                continue

        logger.info(f"Found {len(spools_disponibles)} spools for CANCELAR ARM by worker_id={worker_id}")
        return spools_disponibles

    def get_spools_disponibles_para_cancelar_sold(self, worker_id: int) -> list[Spool]:
        """
        Obtiene spools EN_PROGRESO de SOLD del trabajador para CANCELAR (v2.1 Direct Read).

        NOTE: Currently not exposed via GET endpoint. Used internally by CANCELAR workflow.
        POST /api/cancelar-accion exists but no GET /api/spools/cancelar endpoint yet.
        TODO: Add GET endpoint if UI needs to list cancellable spools.

        REGLA DE NEGOCIO v2.1 (Direct Read - 2026-01-20):
        - Soldador: CON DATO en formato "XX(ID)" donde ID = worker_id
        - Fecha_Soldadura: SIN DATO (operación no completada)
        - Ownership: Solo spools donde soldador contiene "(worker_id)"

        Args:
            worker_id: ID numérico del trabajador para filtrar ownership

        Returns:
            Lista de spools EN_PROGRESO del trabajador específico
        """
        logger.info(f"[V2.1] Retrieving spools available for CANCELAR SOLD by worker_id={worker_id} (Direct Read)")

        all_rows = self.sheets_repository.read_worksheet(config.HOJA_OPERACIONES_NOMBRE)
        spools_disponibles = []

        for row_idx, row in enumerate(all_rows[1:], start=2):
            try:
                spool = self.parse_spool_row(row)

                # REGLA v2.1: Soldador lleno Y Fecha_Soldadura vacía Y Ownership
                if (spool.soldador is not None and
                    spool.fecha_soldadura is None and
                    f"({worker_id})" in spool.soldador):
                    spools_disponibles.append(spool)
                    logger.debug(
                        f"[V2.1] Spool {spool.tag_spool} disponible CANCELAR SOLD: "
                        f"soldador={spool.soldador}, fecha_soldadura={spool.fecha_soldadura}, worker_id={worker_id}"
                    )

            except ValueError as e:
                logger.warning(f"Skipping invalid row {row_idx}: {str(e)}")
                continue

        logger.info(f"Found {len(spools_disponibles)} spools for CANCELAR SOLD by worker_id={worker_id}")
        return spools_disponibles

    def get_spools_ocupados_por_worker(self, worker_id: int, operacion: str) -> list[Spool]:
        """
        Obtiene spools ocupados por un trabajador (v3.0/v4.0 unified).

        REGLA DE NEGOCIO UNIFICADA (v3.0 + v4.0):
        - Ocupado_Por: Contiene formato "(worker_id)" (ej: "MR(93)")
        - Independiente de versión del spool
        - Reemplaza get_spools_disponibles_para_cancelar_arm/sold (obsoletos)

        Esta función unifica el filtrado para ambas versiones:
        - v3.0: Spools ocupados con TOMAR (Ocupado_Por seteado)
        - v4.0: Spools ocupados con INICIAR (Ocupado_Por seteado)

        Args:
            worker_id: ID numérico del trabajador para filtrar ownership
            operacion: Tipo de operación (ARM, SOLD, REPARACION) - para logging

        Returns:
            Lista de spools ocupados por el trabajador específico
        """
        logger.info(f"[UNIFIED] Retrieving spools occupied by worker_id={worker_id} operacion={operacion}")

        all_rows = self.sheets_repository.read_worksheet(config.HOJA_OPERACIONES_NOMBRE)
        spools_ocupados = []

        for row_idx, row in enumerate(all_rows[1:], start=2):
            try:
                spool = self.parse_spool_row(row)

                # REGLA UNIFICADA: Ocupado_Por contiene "(worker_id)"
                if spool.ocupado_por and f"({worker_id})" in spool.ocupado_por:
                    spools_ocupados.append(spool)
                    logger.debug(
                        f"[UNIFIED] Spool {spool.tag_spool} occupied by worker: "
                        f"ocupado_por={spool.ocupado_por}, worker_id={worker_id}"
                    )

            except ValueError as e:
                logger.warning(f"Skipping invalid row {row_idx}: {str(e)}")
                continue

        logger.info(f"Found {len(spools_ocupados)} occupied spools for worker_id={worker_id} operacion={operacion}")
        return spools_ocupados

    def get_spools_disponibles_para_iniciar_metrologia(self) -> list[Spool]:
        """
        MIGRATED: Usa get_spools_disponibles("METROLOGIA", "INICIAR") internamente.

        REGLA DE NEGOCIO v3.0 (FilterRegistry - 2026-02-05):
        - Fecha_QC_Metrología: SIN DATO (operación METROLOGIA no completada)
        - Soldadura completada (v3.0 + v4.0 hybrid):
          * v3.0 (Total_Uniones=0): Fecha_Soldadura CON dato
          * v4.0 (Total_Uniones>=1): Uniones_SOLD_Completadas = Total_Uniones

        CAMBIOS vs v2.1:
        - ✅ Soporta spools v4.0 (contadores de uniones)
        - ✅ Detecta versión automáticamente (Total_Uniones)
        - ✅ Usa FilterRegistry (lógica centralizada)
        - ⚠️ NO filtra por Ocupado_Por (puede ver spools ocupados por ARM/SOLD)

        DEPRECATED: Usa get_spools_disponibles("METROLOGIA", "INICIAR") en su lugar.

        Returns:
            Lista de spools que cumplen las condiciones
        """
        logger.warning(
            "[DEPRECATED] get_spools_disponibles_para_iniciar_metrologia() "
            "is deprecated. Use get_spools_disponibles('METROLOGIA', 'INICIAR') instead."
        )

        # Delegar al método unificado
        return self.get_spools_disponibles("METROLOGIA", "INICIAR")

    def get_spools_disponibles(self, operation: str, action: str) -> list[Spool]:
        """
        Método unificado para obtener spools disponibles usando FilterRegistry (v3.0+).

        Reemplaza métodos individuales (get_spools_disponibles_para_iniciar_*) con
        un sistema de filtros configurable y centralizado.

        Args:
            operation: Tipo de operación ("ARM", "SOLD", "METROLOGIA", "REPARACION")
            action: Tipo de acción ("INICIAR", "FINALIZAR")

        Returns:
            Lista de spools que pasan TODOS los filtros configurados

        Raises:
            ValueError: Si la combinación (operation, action) no está soportada

        Example:
            >>> service.get_spools_disponibles("METROLOGIA", "INICIAR")
            [Spool(tag_spool="TAG-001", ...), Spool(tag_spool="TAG-002", ...)]
        """
        from backend.services.filters import FilterRegistry

        logger.info(f"[FilterRegistry] Retrieving spools disponibles for {operation} {action}")

        # Obtener filtros configurados para esta operación/acción
        try:
            filters = FilterRegistry.get_filters(operation, action)
        except ValueError as e:
            logger.error(f"Invalid operation/action combination: {operation}/{action}")
            raise

        # Leer todas las filas de Operaciones
        all_rows = self.sheets_repository.read_worksheet(config.HOJA_OPERACIONES_NOMBRE)
        spools_disponibles = []

        # Aplicar filtros a cada spool
        for row_idx, row in enumerate(all_rows[1:], start=2):
            try:
                spool = self.parse_spool_row(row)

                # Verificar si el spool pasa TODOS los filtros
                if FilterRegistry.passes_all_filters(spool, filters):
                    spools_disponibles.append(spool)
                    logger.debug(
                        f"[FilterRegistry] Spool {spool.tag_spool} ELEGIBLE para {operation} {action}"
                    )
                else:
                    # Log de por qué el spool NO pasa (solo en debug)
                    for filter_obj in filters:
                        result = filter_obj.apply(spool)
                        if not result.passed:
                            logger.debug(
                                f"[FilterRegistry] Spool {spool.tag_spool} RECHAZADO: "
                                f"{filter_obj.name} - {result.reason}"
                            )
                            break  # Solo loggear el primer filtro que falla

            except ValueError as e:
                logger.warning(f"Skipping invalid row {row_idx}: {str(e)}")
                continue

        logger.info(
            f"[FilterRegistry] Found {len(spools_disponibles)} spools for {operation} {action} "
            f"(applied {len(filters)} filters)"
        )
        return spools_disponibles

    def find_spool_by_tag(self, tag_spool: str) -> Optional[Spool]:
        """
        Busca un spool específico por su TAG usando mapeo dinámico.

        Búsqueda case-insensitive con normalización de espacios.

        Args:
            tag_spool: TAG del spool a buscar (ej: "MK-1335-CW-25238-011")

        Returns:
            Spool si se encuentra, None si no existe

        Logs:
            INFO: Inicio de búsqueda con TAG
            DEBUG: Resultado de búsqueda (encontrado/no encontrado)
        """
        logger.info(f"[V2] Searching for spool with TAG: '{tag_spool}'")

        # Normalizar TAG para búsqueda case-insensitive
        tag_normalized = tag_spool.strip().upper()

        # Leer todas las filas (desde row 2, skip header)
        all_rows = self.sheets_repository.read_worksheet(config.HOJA_OPERACIONES_NOMBRE)

        for row_idx, row in enumerate(all_rows[1:], start=2):
            try:
                spool = self.parse_spool_row(row)

                # Buscar por TAG normalizado
                if spool.tag_spool.upper() == tag_normalized:
                    logger.debug(f"[V2] Found spool: {spool.tag_spool} with fecha_materiales={spool.fecha_materiales}")
                    return spool

            except ValueError as e:
                logger.warning(f"Skipping invalid row {row_idx}: {str(e)}")
                continue

        logger.debug(f"[V2] Spool with TAG '{tag_spool}' not found")
        return None


if __name__ == "__main__":
    """
    Test script para verificar que el mapeo dinámico funciona con las 4 operaciones.
    """
    import sys
    from pathlib import Path

    # Add backend to path
    backend_path = Path(__file__).parent.parent
    sys.path.insert(0, str(backend_path))

    # Test service
    service = SpoolServiceV2()

    print("\n" + "=" * 80)
    print("SISTEMA DINÁMICO V2 - REGLAS DE NEGOCIO CORRECTAS")
    print("=" * 80)
    print()

    # Test 1: INICIAR ARM
    print("📦 1. INICIAR ARM (Fecha_Materiales llena Y Armador vacío)")
    spools_iniciar_arm = service.get_spools_disponibles_para_iniciar_arm()
    print(f"   ✅ {len(spools_iniciar_arm)} spools disponibles")
    if spools_iniciar_arm:
        print(f"   Ejemplos:")
        for spool in spools_iniciar_arm[:3]:
            print(f"     • {spool.tag_spool}: fecha_materiales={spool.fecha_materiales}, armador={spool.armador}")
    print()

    # Test 2: COMPLETAR ARM
    print("🔧 2. COMPLETAR ARM (Armador lleno Y Fecha_Armado vacía)")
    spools_completar_arm = service.get_spools_disponibles_para_completar_arm()
    print(f"   ✅ {len(spools_completar_arm)} spools disponibles")
    if spools_completar_arm:
        print(f"   Ejemplos:")
        for spool in spools_completar_arm[:3]:
            print(f"     • {spool.tag_spool}: armador={spool.armador}, fecha_armado={spool.fecha_armado}")
    print()

    # Test 3: INICIAR SOLD
    print("🔥 3. INICIAR SOLD (Fecha_Armado llena Y Soldador vacío)")
    spools_iniciar_sold = service.get_spools_disponibles_para_iniciar_sold()
    print(f"   ✅ {len(spools_iniciar_sold)} spools disponibles")
    if spools_iniciar_sold:
        print(f"   Ejemplos:")
        for spool in spools_iniciar_sold[:3]:
            print(f"     • {spool.tag_spool}: fecha_armado={spool.fecha_armado}, soldador={spool.soldador}")
    print()

    # Test 4: COMPLETAR SOLD
    print("✔️  4. COMPLETAR SOLD (Soldador lleno Y Fecha_Soldadura vacía)")
    spools_completar_sold = service.get_spools_disponibles_para_completar_sold()
    print(f"   ✅ {len(spools_completar_sold)} spools disponibles")
    if spools_completar_sold:
        print(f"   Ejemplos:")
        for spool in spools_completar_sold[:3]:
            print(f"     • {spool.tag_spool}: soldador={spool.soldador}, fecha_soldadura={spool.fecha_soldadura}")
    print()

    # Test 5: Verificar TEST-01
    print("🧪 5. VERIFICAR TEST-01")
    all_iniciar_arm = service.get_spools_disponibles_para_iniciar_arm()
    test_spool = [s for s in all_iniciar_arm if 'TEST' in s.tag_spool.upper()]

    if test_spool:
        print(f"   ✅ TEST-01 encontrado en INICIAR ARM")
        for s in test_spool:
            print(f"     • {s.tag_spool}: fecha_materiales={s.fecha_materiales}, armador={s.armador}")
    else:
        print(f"   ❌ TEST-01 NO encontrado (debe tener Fecha_Materiales llena y Armador vacío)")

    print()
    print("=" * 80)
