"""
Servicio de Spools v2.2 con mapeo dinámico y validación de estructura.

Diferencias vs v1.0:
- Lee header (row 1) para construir mapeo: nombre_columna → índice
- Resistente a cambios en estructura del spreadsheet
- Reglas de negocio correctas para 4 operaciones:
  * INICIAR ARM: Fecha_Materiales llena Y Armador vacía
  * COMPLETAR ARM: Armador lleno Y Fecha_Armado vacía
  * INICIAR SOLD: Fecha_Armado llena Y Soldador vacío
  * COMPLETAR SOLD: Soldador lleno Y Fecha_Soldadura vacía

v2.2 PROTECCIONES:
- Validación de columnas críticas al inicio
- Detecta eliminación accidental de columnas
- Busca nombres alternativos (ej: "TAG_SPOOL" o "tag" o "codigobarra")
- Error descriptivo con soluciones si falta alguna columna
- Logging detallado de mapeo de columnas

CASO LÍMITE MANEJADO:
Si se elimina una columna no crítica → Sistema continúa funcionando ✅
Si se elimina una columna crítica → Sistema falla FAST con error claro ❌
Si se renombra columna → Sistema busca nombres alternativos ✅

Autor: ZEUES Team
Fecha: 2026-01-14
"""
import logging
from typing import Optional
from datetime import date

from backend.repositories.sheets_repository import SheetsRepository
from backend.services.sheets_service import SheetsService
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

    def __init__(self, sheets_repository: Optional[SheetsRepository] = None):
        """
        Inicializa el servicio con repositorio de Sheets.

        Args:
            sheets_repository: Repositorio para acceso a Google Sheets
        """
        self.sheets_repository = sheets_repository or SheetsRepository()
        self.column_map: Optional[dict[str, int]] = None
        self.sheets_service: Optional[SheetsService] = None

    def _ensure_column_map(self):
        """
        Construye el mapeo de columnas si no existe.

        Lee el header (row 1) de la hoja Operaciones y crea el mapeo
        nombre_columna → índice.

        VALIDACIÓN: Verifica que todas las columnas críticas existen.
        Si falta alguna columna crítica, lanza error detallado.
        """
        if self.column_map is not None:
            return  # Ya inicializado

        logger.info("Building column map from header row")

        # Leer hoja Operaciones completa (incluye header)
        all_rows = self.sheets_repository.read_worksheet(
            config.HOJA_OPERACIONES_NOMBRE
        )

        if not all_rows or len(all_rows) == 0:
            raise ValueError("Hoja Operaciones vacía")

        # Row 1 = header
        header_row = all_rows[0]

        # Construir mapeo dinámico
        self.column_map = SheetsService.build_column_map(header_row)

        # Crear SheetsService con column_map
        self.sheets_service = SheetsService(column_map=self.column_map)

        logger.info(f"Column map built with {len(self.column_map)} entries")

        # VALIDACIÓN CRÍTICA: Verificar que columnas obligatorias existen
        self._validate_critical_columns()

    def _validate_critical_columns(self):
        """
        Valida que todas las columnas críticas existen en el spreadsheet.

        COLUMNAS CRÍTICAS (obligatorias para funcionamiento):
        - TAG_SPOOL: Identificador único del spool
        - Fecha_Materiales: Prerequisito para iniciar ARM
        - Fecha_Armado: Estado de completitud ARM
        - Armador: Worker asignado a ARM
        - Fecha_Soldadura: Estado de completitud SOLD
        - Soldador: Worker asignado a SOLD

        Raises:
            ValueError: Si falta alguna columna crítica, con detalles de:
                       - Columnas faltantes
                       - Columnas encontradas
                       - Posibles soluciones
        """
        # Definir columnas críticas con nombres alternativos posibles
        critical_columns = {
            "TAG_SPOOL": ["tagspool", "tag", "codigobarra"],
            "Fecha_Materiales": ["fechamateriales", "materialesdate"],
            "Fecha_Armado": ["fechaarmado", "armadodate"],
            "Armador": ["armador", "worker_arm"],
            "Fecha_Soldadura": ["fechasoldadura", "soldaduradate"],
            "Soldador": ["soldador", "worker_sold"]
        }

        missing_columns = []
        found_columns = {}

        for col_name, alternatives in critical_columns.items():
            # Intentar encontrar la columna (normalizada)
            normalized_name = col_name.lower().replace("_", "").replace(" ", "")

            # Buscar en column_map (ya normalizado)
            found = False
            for alt in [normalized_name] + alternatives:
                if alt in self.column_map:
                    found_columns[col_name] = self.column_map[alt]
                    found = True
                    break

            if not found:
                missing_columns.append(col_name)

        # Si faltan columnas críticas, lanzar error detallado
        if missing_columns:
            error_msg = f"""
❌ ESTRUCTURA DE SPREADSHEET INVÁLIDA

Columnas CRÍTICAS faltantes: {', '.join(missing_columns)}

Esto puede ocurrir si:
1. Se eliminó una columna del spreadsheet
2. Se cambió el nombre de una columna en el header (row 1)
3. El header (row 1) está vacío para esa columna

SOLUCIÓN:
1. Verifica que el header (row 1) de la hoja "Operaciones" contenga:
   {', '.join(critical_columns.keys())}

2. Si eliminaste una columna por error, restáurala desde el historial

3. Si cambiaste el nombre, usa el nombre original o actualiza el código

Columnas encontradas correctamente: {len(found_columns)}/{len(critical_columns)}
{chr(10).join(f'  ✅ {name} → columna {idx}' for name, idx in found_columns.items())}
"""
            logger.error(error_msg)
            raise ValueError(error_msg)

        logger.info(f"✅ All {len(critical_columns)} critical columns validated successfully")

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
        # Asegurar que column_map existe
        self._ensure_column_map()

        # Obtener índices dinámicamente por nombre de columna
        idx_tag_spool = self.sheets_service._get_col_idx("TAG_SPOOL", fallback_idx=6)
        idx_nv = self.sheets_service._get_col_idx("NV", fallback_idx=1)
        idx_fecha_materiales = self.sheets_service._get_col_idx("Fecha_Materiales", fallback_idx=32)
        idx_fecha_armado = self.sheets_service._get_col_idx("Fecha_Armado", fallback_idx=33)
        idx_armador = self.sheets_service._get_col_idx("Armador", fallback_idx=34)
        idx_fecha_soldadura = self.sheets_service._get_col_idx("Fecha_Soldadura", fallback_idx=35)
        idx_soldador = self.sheets_service._get_col_idx("Soldador", fallback_idx=36)

        logger.debug(
            f"Column indices: TAG_SPOOL={idx_tag_spool}, "
            f"Fecha_Armado={idx_fecha_armado}, Armador={idx_armador}"
        )

        # Validar y rellenar fila si es corta
        required_len = max(idx_tag_spool, idx_fecha_armado, idx_armador, idx_soldador) + 1
        if len(row) < required_len:
            row = row + [''] * (required_len - len(row))

        # 1. TAG_SPOOL (obligatorio)
        tag_spool = row[idx_tag_spool].strip() if row[idx_tag_spool] else None
        if not tag_spool:
            raise ValueError("TAG_SPOOL vacío")

        # 2. NV (opcional)
        nv = row[idx_nv].strip() if idx_nv < len(row) and row[idx_nv] else None
        if nv == '':
            nv = None

        # 3. Estados ARM/SOLD siempre PENDIENTE (se reconstruyen desde Metadata)
        arm_status = ActionStatus.PENDIENTE
        sold_status = ActionStatus.PENDIENTE

        # 4. Parsear fechas usando SheetsService.parse_date()
        fecha_materiales = SheetsService.parse_date(row[idx_fecha_materiales] if idx_fecha_materiales < len(row) else "")
        fecha_armado = SheetsService.parse_date(row[idx_fecha_armado] if idx_fecha_armado < len(row) else "")
        fecha_soldadura = SheetsService.parse_date(row[idx_fecha_soldadura] if idx_fecha_soldadura < len(row) else "")

        # 5. Parsear trabajadores
        armador = row[idx_armador].strip() if idx_armador < len(row) and row[idx_armador] else None
        if armador == '':
            armador = None

        soldador = row[idx_soldador].strip() if idx_soldador < len(row) and row[idx_soldador] else None
        if soldador == '':
            soldador = None

        return Spool(
            tag_spool=tag_spool,
            nv=nv,
            arm=arm_status,
            sold=sold_status,
            fecha_materiales=fecha_materiales,
            fecha_armado=fecha_armado,
            armador=armador,
            fecha_soldadura=fecha_soldadura,
            soldador=soldador,
            proyecto=None
        )

    def get_spools_disponibles_para_iniciar_arm(self) -> list[Spool]:
        """
        Obtiene spools disponibles para INICIAR ARM.

        REGLA DE NEGOCIO (CORRECTA - 2026-01-14):
        - Fecha_Materiales (col AG): CON DATO (prerequisito cumplido)
        - Armador (col AI): VACÍO (nadie asignado aún)

        Returns:
            Lista de spools que cumplen las condiciones
        """
        logger.info("Retrieving spools available for INICIAR ARM")
        self._ensure_column_map()
        all_rows = self.sheets_repository.read_worksheet(config.HOJA_OPERACIONES_NOMBRE)
        spools_disponibles = []

        for row_idx, row in enumerate(all_rows[1:], start=2):
            try:
                spool = self.parse_spool_row(row)

                # REGLA: Fecha_Materiales llena Y Armador vacío
                if spool.fecha_materiales is not None and spool.armador is None:
                    spools_disponibles.append(spool)
                    logger.debug(
                        f"Spool {spool.tag_spool} disponible INICIAR ARM: "
                        f"fecha_materiales={spool.fecha_materiales}, armador={spool.armador}"
                    )

            except ValueError as e:
                logger.warning(f"Skipping invalid row {row_idx}: {str(e)}")
                continue

        logger.info(f"Found {len(spools_disponibles)} spools for INICIAR ARM")
        return spools_disponibles

    def get_spools_disponibles_para_completar_arm(self) -> list[Spool]:
        """
        Obtiene spools disponibles para COMPLETAR o CANCELAR ARM.

        REGLA DE NEGOCIO:
        - Armador (col AI): CON DATO (alguien lo inició)
        - Fecha_Armado (col AH): VACÍO (no completado aún)

        Returns:
            Lista de spools que cumplen las condiciones
        """
        logger.info("Retrieving spools available for COMPLETAR ARM")
        self._ensure_column_map()
        all_rows = self.sheets_repository.read_worksheet(config.HOJA_OPERACIONES_NOMBRE)
        spools_disponibles = []

        for row_idx, row in enumerate(all_rows[1:], start=2):
            try:
                spool = self.parse_spool_row(row)

                # REGLA: Armador lleno Y Fecha_Armado vacía
                if spool.armador is not None and spool.fecha_armado is None:
                    spools_disponibles.append(spool)
                    logger.debug(
                        f"Spool {spool.tag_spool} disponible COMPLETAR ARM: "
                        f"armador={spool.armador}, fecha_armado={spool.fecha_armado}"
                    )

            except ValueError as e:
                logger.warning(f"Skipping invalid row {row_idx}: {str(e)}")
                continue

        logger.info(f"Found {len(spools_disponibles)} spools for COMPLETAR ARM")
        return spools_disponibles

    def get_spools_disponibles_para_iniciar_sold(self) -> list[Spool]:
        """
        Obtiene spools disponibles para INICIAR SOLD.

        REGLA DE NEGOCIO:
        - Fecha_Armado (col AH): CON DATO (prerequisito ARM completado)
        - Soldador (col AK): VACÍO (nadie asignado aún)

        Returns:
            Lista de spools que cumplen las condiciones
        """
        logger.info("Retrieving spools available for INICIAR SOLD")
        self._ensure_column_map()
        all_rows = self.sheets_repository.read_worksheet(config.HOJA_OPERACIONES_NOMBRE)
        spools_disponibles = []

        for row_idx, row in enumerate(all_rows[1:], start=2):
            try:
                spool = self.parse_spool_row(row)

                # REGLA: Fecha_Armado llena Y Soldador vacío
                if spool.fecha_armado is not None and spool.soldador is None:
                    spools_disponibles.append(spool)
                    logger.debug(
                        f"Spool {spool.tag_spool} disponible INICIAR SOLD: "
                        f"fecha_armado={spool.fecha_armado}, soldador={spool.soldador}"
                    )

            except ValueError as e:
                logger.warning(f"Skipping invalid row {row_idx}: {str(e)}")
                continue

        logger.info(f"Found {len(spools_disponibles)} spools for INICIAR SOLD")
        return spools_disponibles

    def get_spools_disponibles_para_completar_sold(self) -> list[Spool]:
        """
        Obtiene spools disponibles para COMPLETAR o CANCELAR SOLD.

        REGLA DE NEGOCIO:
        - Soldador (col AK): CON DATO (alguien lo inició)
        - Fecha_Soldadura (col AJ): VACÍO (no completado aún)

        Returns:
            Lista de spools que cumplen las condiciones
        """
        logger.info("Retrieving spools available for COMPLETAR SOLD")
        self._ensure_column_map()
        all_rows = self.sheets_repository.read_worksheet(config.HOJA_OPERACIONES_NOMBRE)
        spools_disponibles = []

        for row_idx, row in enumerate(all_rows[1:], start=2):
            try:
                spool = self.parse_spool_row(row)

                # REGLA: Soldador lleno Y Fecha_Soldadura vacía
                if spool.soldador is not None and spool.fecha_soldadura is None:
                    spools_disponibles.append(spool)
                    logger.debug(
                        f"Spool {spool.tag_spool} disponible COMPLETAR SOLD: "
                        f"soldador={spool.soldador}, fecha_soldadura={spool.fecha_soldadura}"
                    )

            except ValueError as e:
                logger.warning(f"Skipping invalid row {row_idx}: {str(e)}")
                continue

        logger.info(f"Found {len(spools_disponibles)} spools for COMPLETAR SOLD")
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
        self._ensure_column_map()

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
