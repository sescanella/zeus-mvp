"""
Servicio para parsear filas de Google Sheets a modelos Pydantic.

Responsabilidades:
- Conversión robusta de valores (string→float, string→date)
- Parseo de filas de Trabajadores → Worker
- Parseo de filas de Operaciones → Spool
- Manejo de valores vacíos, nulos e inválidos
- Validación de consistencia de datos
"""
from typing import Optional
from datetime import datetime, date
import logging

from backend.models.worker import Worker
from backend.models.spool import Spool
from backend.models.enums import ActionStatus

logger = logging.getLogger(__name__)


class SheetsService:
    """
    Servicio para parsear filas de Google Sheets a modelos Pydantic.

    v2.1 (Dynamic Column Mapping):
    - Lee headers (row 1) para construir mapeo dinámico
    - Busca columnas por NOMBRE en lugar de índice hardcodeado
    - Resistente a cambios en estructura del spreadsheet
    """

    def __init__(self, column_map: dict[str, int]):
        """
        Inicializa el servicio con un mapeo de columnas (REQUERIDO v2.1).

        Args:
            column_map: Diccionario {nombre_columna_normalizado: índice}.
                        Obtener desde ColumnMapCache.get_or_build()

        Raises:
            ValueError: Si column_map está vacío o es None

        Examples:
            >>> from backend.core.column_map_cache import ColumnMapCache
            >>> column_map = ColumnMapCache.get_or_build("Operaciones", sheets_repo)
            >>> sheets_service = SheetsService(column_map=column_map)
        """
        if not column_map:
            raise ValueError(
                "column_map is required. "
                "Use ColumnMapCache.get_or_build() to obtain it."
            )
        self._column_map = column_map

    @staticmethod
    def build_column_map(header_row: list[str]) -> dict[str, int]:
        """
        Construye un mapeo dinámico: nombre_columna → índice.

        Busca nombres de columnas en el header (case-insensitive, ignora espacios).

        Args:
            header_row: Lista con nombres de columnas del header (row 1)

        Returns:
            Dict con mapeo {nombre_normalizado: índice}

        Examples:
            >>> header = ["NV", "TAG_SPOOL", "Fecha_Armado", "Armador"]
            >>> column_map = SheetsService.build_column_map(header)
            >>> column_map["Fecha_Armado"]  # Returns: 2
        """
        column_map = {}

        # Normalizar nombres: lowercase, sin espacios, sin underscores
        def normalize(name: str) -> str:
            return name.lower().replace(" ", "").replace("_", "")

        for idx, col_name in enumerate(header_row):
            if not col_name:
                continue

            # Almacenar nombre normalizado
            normalized = normalize(col_name)
            column_map[normalized] = idx

            # También almacenar nombres parciales comunes para búsqueda
            # Ejemplo: "TAG_SPOOL / CODIGO_BARRA" → también buscar por "tagspool"
            if "/" in col_name:
                first_part = col_name.split("/")[0].strip()
                column_map[normalize(first_part)] = idx

        logger.debug(f"Built column map with {len(column_map)} entries")
        return column_map

    def _get_col_idx(self, column_name: str, fallback_idx: Optional[int] = None) -> Optional[int]:
        """
        Obtiene el índice de una columna por su nombre.

        Args:
            column_name: Nombre de la columna (ej: "Fecha_Armado")
            fallback_idx: Índice legacy a usar si no hay mapeo

        Returns:
            Índice de la columna, o fallback_idx si no se encuentra
        """
        normalized = column_name.lower().replace(" ", "").replace("_", "")

        if normalized in self._column_map:
            return self._column_map[normalized]

        if fallback_idx is not None:
            logger.warning(
                f"Column '{column_name}' not found in map, using fallback index {fallback_idx}"
            )
            return fallback_idx

        logger.error(f"Column '{column_name}' not found and no fallback provided")
        return None

    # ==================== WORKER SHEET CONSTANTS (STABLE) ====================
    # Hoja "Trabajadores" - Estructura estable (no cambia)
    IDX_WORKER_ID = 0           # A - Id (numérico)
    IDX_WORKER_NOMBRE = 1       # B - Nombre
    IDX_WORKER_APELLIDO = 2     # C - Apellido
    IDX_WORKER_ROL = 3          # D - Rol (Armador, Soldador, etc.)
    IDX_WORKER_ACTIVO = 4       # E - Activo (TRUE/FALSE)

    @staticmethod
    def safe_float(value: str, default: float = 0.0) -> float:
        """
        Convierte string a float de forma segura, manejando valores vacíos e inválidos.

        Args:
            value: Valor a convertir (puede ser string, int, float, None)
            default: Valor por defecto si conversión falla (default: 0.0)

        Returns:
            float: Valor convertido o default

        Examples:
            >>> SheetsService.safe_float("0.1")
            0.1
            >>> SheetsService.safe_float("1")
            1.0
            >>> SheetsService.safe_float("")
            0.0
            >>> SheetsService.safe_float(None)
            0.0
            >>> SheetsService.safe_float("abc")
            0.0  # + warning log
        """
        # Manejar None explícitamente
        if value is None:
            return default

        # Convertir a string y limpiar espacios
        value_str = str(value).strip()

        # Manejar string vacío
        if value_str == '':
            return default

        # Intentar conversión
        try:
            return float(value_str)
        except (ValueError, TypeError) as e:
            logger.warning(
                f"Valor inválido para float: '{value}' (type: {type(value).__name__}). "
                f"Usando default {default}"
            )
            return default

    @staticmethod
    def parse_date(value: str) -> Optional[date]:
        """
        Parsea fechas en múltiples formatos comunes.

        Formatos soportados:
        - DD/MM/YYYY (ej: 30/7/2025, 08/11/2025)
        - DD/MM/YY (ej: 30/7/25, 08/11/25)
        - YYYY-MM-DD (ej: 2025-11-08)
        - DD-MMM-YYYY (ej: 08-Nov-2025)
        - DD-MM-YYYY (ej: 08-11-2025)

        Args:
            value: String con la fecha

        Returns:
            date object o None si vacío/inválido

        Examples:
            >>> SheetsService.parse_date("30/7/2025")
            date(2025, 7, 30)
            >>> SheetsService.parse_date("2025-11-08")
            date(2025, 11, 8)
            >>> SheetsService.parse_date("")
            None
            >>> SheetsService.parse_date("invalid")
            None  # + warning log
        """
        # Manejar valores vacíos/nulos
        if not value or value is None:
            return None

        # Limpiar espacios
        value_str = str(value).strip()
        if value_str == '':
            return None

        # Formatos a intentar (en orden de más común a menos común)
        formats = [
            "%d-%m-%Y",     # 21-01-2026 (formato principal - DD-MM-YYYY)
            "%d/%m/%Y",     # 30/7/2025 (legacy - mantener compatibilidad)
            "%d/%m/%y",     # 30/7/25 (legacy)
            "%Y-%m-%d",     # 2025-11-08 (legacy ISO format)
            "%d-%b-%Y",     # 08-Nov-2025
        ]

        # Intentar cada formato
        for fmt in formats:
            try:
                return datetime.strptime(value_str, fmt).date()
            except ValueError:
                continue

        # Ningún formato funcionó
        logger.warning(f"Formato de fecha no reconocido: '{value_str}'")
        return None

    @classmethod
    def parse_worker_row(cls, row: list) -> Worker:
        """
        Parsea una fila de la hoja 'Trabajadores' a un objeto Worker.

        Soporta dos formatos (backward compatibility):
        - v1.0 (4 cols): A=Nombre | B=Apellido | C=Rol | D=Activo
        - v2.0 (5 cols): A=Id | B=Nombre | C=Apellido | D=Rol | E=Activo

        Args:
            row: Lista con valores de la fila (mínimo 4 columnas)

        Returns:
            Worker: Objeto Worker parseado

        Raises:
            ValueError: Si la fila no tiene suficientes columnas o campos obligatorios vacíos

        Examples:
            >>> row = ["93", "Mauricio", "Rodriguez", "Armador", "TRUE"]
            >>> worker = SheetsService.parse_worker_row(row)
            >>> worker.id
            93
            >>> worker.nombre
            'Mauricio'
            >>> worker.rol
            <RolTrabajador.ARMADOR: 'Armador'>
        """
        # Validar longitud mínima (al menos 4 columnas)
        if len(row) < 4:
            raise ValueError(f"Fila de trabajador incompleta: {len(row)} columnas (se esperan al menos 4)")

        # Detectar formato basándose en si la primera columna es un Id numérico
        first_col_is_id = False
        if row[0] and str(row[0]).strip().isdigit():
            first_col_is_id = True

        # Determinar estructura del sheet
        if len(row) >= 5 and first_col_is_id:
            # Formato v2.0 completo: A=Id | B=Nombre | C=Apellido | D=Rol | E=Activo
            worker_id = int(row[0].strip())
            idx_nombre = 1
            idx_apellido = 2
            idx_rol = 3
            idx_activo = 4
            has_rol = True
        elif len(row) == 4 and first_col_is_id:
            # Formato híbrido (migración parcial): A=Id | B=Nombre | C=Apellido | D=Activo (SIN Rol)
            worker_id = int(row[0].strip())
            idx_nombre = 1
            idx_apellido = 2
            idx_rol = None  # No hay columna Rol
            idx_activo = 3
            has_rol = False
        else:
            # Formato v1.0 legacy: A=Nombre | B=Apellido | C=Rol | D=Activo (sin Id)
            # Generar Id sintético desde hash de nombre+apellido
            idx_nombre = 0
            idx_apellido = 1
            idx_rol = 2
            idx_activo = 3
            has_rol = True
            worker_id = None  # Se genera después de parsear nombre+apellido

        # 2. Parsear nombre (obligatorio)
        nombre = row[idx_nombre].strip() if row[idx_nombre] else ""
        if not nombre:
            raise ValueError("Nombre de trabajador vacío")

        # 3. Parsear apellido (obligatorio)
        apellido = row[idx_apellido].strip() if row[idx_apellido] else ""
        if not apellido:
            raise ValueError(f"Apellido de trabajador vacío (nombre: {nombre})")

        # Si worker_id aún es None, generar Id sintético (formato v1.0)
        if worker_id is None:
            import hashlib
            hash_str = f"{nombre}{apellido}".encode('utf-8')
            worker_id = abs(int(hashlib.md5(hash_str).hexdigest()[:8], 16)) % 100000

        # 4. Parsear rol (si existe columna Rol)
        from backend.models.worker import RolTrabajador

        if has_rol and idx_rol is not None:
            # Parsear rol desde columna
            rol_str = row[idx_rol].strip() if row[idx_rol] else ""
            if not rol_str:
                raise ValueError(f"Rol de trabajador vacío (nombre: {nombre} {apellido})")

            try:
                rol = RolTrabajador(rol_str)
            except ValueError:
                # Intentar case-insensitive match
                rol_str_normalized = rol_str.upper()
                valid_roles = [r.value for r in RolTrabajador]

                # Buscar coincidencia case-insensitive
                matched_rol = None
                for valid_rol in RolTrabajador:
                    if valid_rol.value.upper() == rol_str_normalized:
                        matched_rol = valid_rol
                        break

                if matched_rol:
                    rol = matched_rol
                else:
                    raise ValueError(
                        f"Rol inválido '{rol_str}' para trabajador {nombre} {apellido}. "
                        f"Roles válidos: {valid_roles}"
                    )
        else:
            # Sin columna Rol - usar valor por defecto (AYUDANTE genérico)
            logger.warning(f"Worker {nombre} {apellido} sin columna Rol, usando AYUDANTE por defecto")
            rol = RolTrabajador.AYUDANTE

        # 5. Parsear activo (obligatorio, TRUE/FALSE)
        activo_str = row[idx_activo].strip().upper() if row[idx_activo] else ""
        if not activo_str:
            logger.warning(f"Campo Activo vacío para {nombre} {apellido}, usando FALSE por defecto")
            activo = False
        else:
            # Google Sheets retorna "TRUE" o "FALSE" como strings
            activo = activo_str == "TRUE"

        return Worker(
            id=worker_id,
            nombre=nombre,
            apellido=apellido,
            rol=rol,
            activo=activo
        )

    def parse_spool_row(self, row: list) -> Spool:
        """
        Parsea una fila de la hoja 'Operaciones' a un objeto Spool (v2.1 Dynamic Mapping).

        **IMPORTANTE v2.1:**
        - Usa mapeo dinámico de columnas (_get_col_idx) - resistente a cambios de estructura
        - La hoja Operaciones es READ-ONLY (no se modifica)
        - Estados ARM/SOLD se reconstruyen desde hoja Metadata (Event Sourcing)
        - Esta función solo lee datos base: tag_spool, fecha_materiales, etc.
        - Estados siempre se setean como PENDIENTE (se reconstruyen después)

        Args:
            row: Lista con valores de la fila (mínimo recomendado: 65 columnas)

        Returns:
            Spool: Objeto Spool con datos base (estados PENDIENTE por defecto)

        Raises:
            ValueError: Si TAG_SPOOL está vacío o no se encuentra

        Examples:
            >>> column_map = ColumnMapCache.get_or_build("Operaciones", sheets_repo)
            >>> sheets_service = SheetsService(column_map=column_map)
            >>> row = all_rows[1]  # Segunda fila (skip header)
            >>> spool = sheets_service.parse_spool_row(row)
            >>> spool.tag_spool
            'MK-1335-CW-25238-011'
            >>> spool.arm  # Siempre PENDIENTE (se reconstruye desde Metadata)
            <ActionStatus.PENDIENTE: 'PENDIENTE'>
        """
        # Rellenar fila si es muy corta (evitar index out of range)
        # v4.0: Extendido a 72 columnas (68 v3.0 + 5 v4.0)
        if len(row) < 72:  # Hoja Operaciones tiene ~72 columnas en v4.0
            row = row + [''] * (72 - len(row))
            logger.debug(f"Fila corta rellenada a 72 columnas (original: {len(row) - (72 - len(row))})")

        # 1. Obtener índices usando mapeo dinámico
        idx_tag_spool = self._get_col_idx("SPLIT", fallback_idx=5)  # Real column name in Sheet
        idx_ot = self._get_col_idx("OT", fallback_idx=1)  # v4.0: Orden de Trabajo
        idx_nv = self._get_col_idx("NV", fallback_idx=7)
        idx_fecha_materiales = self._get_col_idx("Fecha_Materiales", fallback_idx=32)
        idx_fecha_armado = self._get_col_idx("Fecha_Armado", fallback_idx=33)
        idx_armador = self._get_col_idx("Armador", fallback_idx=34)
        idx_fecha_soldadura = self._get_col_idx("Fecha_Soldadura", fallback_idx=35)
        idx_soldador = self._get_col_idx("Soldador", fallback_idx=36)

        # v3.0: Índices de columnas de ocupación
        idx_ocupado_por = self._get_col_idx("Ocupado_Por", fallback_idx=64)
        idx_fecha_ocupacion = self._get_col_idx("Fecha_Ocupacion", fallback_idx=65)
        idx_version = self._get_col_idx("version", fallback_idx=66)
        idx_estado_detalle = self._get_col_idx("Estado_Detalle", fallback_idx=67)

        # v4.0: Índices de columnas de métricas de uniones
        idx_total_uniones = self._get_col_idx("Total_Uniones", fallback_idx=67)
        idx_uniones_arm = self._get_col_idx("Uniones_ARM_Completadas", fallback_idx=68)
        idx_uniones_sold = self._get_col_idx("Uniones_SOLD_Completadas", fallback_idx=69)
        idx_pulgadas_arm = self._get_col_idx("Pulgadas_ARM", fallback_idx=70)
        idx_pulgadas_sold = self._get_col_idx("Pulgadas_SOLD", fallback_idx=71)

        # 2. Parsear SPLIT (spool identifier - obligatorio)
        tag_spool = row[idx_tag_spool].strip() if idx_tag_spool < len(row) and row[idx_tag_spool] else None
        if not tag_spool:
            raise ValueError("SPLIT (spool identifier) vacío en fila")

        # 3. Parsear NV (v2.0 - opcional para filtrado multidimensional)
        nv = row[idx_nv].strip() if idx_nv < len(row) and row[idx_nv] else None
        if nv == '':
            nv = None

        # 4. Estados ARM/SOLD siempre PENDIENTE (se reconstruyen desde Metadata)
        # No leemos estados de Operaciones porque es READ-ONLY en v2.0
        arm_status = ActionStatus.PENDIENTE
        sold_status = ActionStatus.PENDIENTE

        # 5. Parsear fechas (solo lectura, NO se usan para determinar estado)
        fecha_materiales = self.parse_date(row[idx_fecha_materiales]) if idx_fecha_materiales < len(row) else None
        fecha_armado = self.parse_date(row[idx_fecha_armado]) if idx_fecha_armado < len(row) else None
        fecha_soldadura = self.parse_date(row[idx_fecha_soldadura]) if idx_fecha_soldadura < len(row) else None

        # 6. Parsear trabajadores legacy (solo lectura informativa)
        armador = row[idx_armador].strip() if idx_armador < len(row) and row[idx_armador] else None
        if armador == '':
            armador = None

        soldador = row[idx_soldador].strip() if idx_soldador < len(row) and row[idx_soldador] else None
        if soldador == '':
            soldador = None

        # 7. Parsear campos v3.0 (ocupación)
        ocupado_por = row[idx_ocupado_por].strip() if idx_ocupado_por < len(row) and row[idx_ocupado_por] else None
        if ocupado_por == '':
            ocupado_por = None

        fecha_ocupacion = row[idx_fecha_ocupacion].strip() if idx_fecha_ocupacion < len(row) and row[idx_fecha_ocupacion] else None
        if fecha_ocupacion == '':
            fecha_ocupacion = None

        # Version defaults to 0 if empty or invalid
        version = 0
        if idx_version < len(row) and row[idx_version]:
            try:
                version = int(row[idx_version])
            except (ValueError, TypeError):
                logger.warning(f"Invalid version value '{row[idx_version]}' for {tag_spool}, defaulting to 0")
                version = 0

        # Estado_Detalle (v3.0)
        estado_detalle = row[idx_estado_detalle].strip() if idx_estado_detalle < len(row) and row[idx_estado_detalle] else None
        if estado_detalle == '':
            estado_detalle = None

        # 8. v4.0: Parse campos de métricas de uniones
        # OT (Orden de Trabajo)
        ot = row[idx_ot].strip() if idx_ot < len(row) and row[idx_ot] else None
        if ot == '':
            ot = None

        # Total_Uniones (v4.0 version detection field)
        total_uniones = None
        total_uniones_raw = row[idx_total_uniones] if idx_total_uniones < len(row) and row[idx_total_uniones] else None
        if total_uniones_raw:
            try:
                total_uniones = int(total_uniones_raw)
                if total_uniones < 0:
                    logger.warning(f"Negative Total_Uniones for {tag_spool}: {total_uniones}, defaulting to None")
                    total_uniones = None
            except (ValueError, TypeError):
                logger.warning(f"Invalid Total_Uniones for {tag_spool}: {total_uniones_raw}, defaulting to None")
                total_uniones = None

        # Uniones_ARM_Completadas
        uniones_arm_completadas = None
        uniones_arm_raw = row[idx_uniones_arm] if idx_uniones_arm < len(row) and row[idx_uniones_arm] else None
        if uniones_arm_raw:
            try:
                uniones_arm_completadas = int(uniones_arm_raw)
                if uniones_arm_completadas < 0:
                    logger.warning(f"Negative Uniones_ARM_Completadas for {tag_spool}: {uniones_arm_completadas}, defaulting to None")
                    uniones_arm_completadas = None
            except (ValueError, TypeError):
                logger.warning(f"Invalid Uniones_ARM_Completadas for {tag_spool}: {uniones_arm_raw}, defaulting to None")
                uniones_arm_completadas = None

        # Uniones_SOLD_Completadas
        uniones_sold_completadas = None
        uniones_sold_raw = row[idx_uniones_sold] if idx_uniones_sold < len(row) and row[idx_uniones_sold] else None
        if uniones_sold_raw:
            try:
                uniones_sold_completadas = int(uniones_sold_raw)
                if uniones_sold_completadas < 0:
                    logger.warning(f"Negative Uniones_SOLD_Completadas for {tag_spool}: {uniones_sold_completadas}, defaulting to None")
                    uniones_sold_completadas = None
            except (ValueError, TypeError):
                logger.warning(f"Invalid Uniones_SOLD_Completadas for {tag_spool}: {uniones_sold_raw}, defaulting to None")
                uniones_sold_completadas = None

        # Pulgadas_ARM
        pulgadas_arm = None
        pulgadas_arm_raw = row[idx_pulgadas_arm] if idx_pulgadas_arm < len(row) and row[idx_pulgadas_arm] else None
        if pulgadas_arm_raw:
            try:
                pulgadas_arm = float(pulgadas_arm_raw)
                if pulgadas_arm < 0:
                    logger.warning(f"Negative Pulgadas_ARM for {tag_spool}: {pulgadas_arm}, defaulting to None")
                    pulgadas_arm = None
            except (ValueError, TypeError):
                logger.warning(f"Invalid Pulgadas_ARM for {tag_spool}: {pulgadas_arm_raw}, defaulting to None")
                pulgadas_arm = None

        # Pulgadas_SOLD
        pulgadas_sold = None
        pulgadas_sold_raw = row[idx_pulgadas_sold] if idx_pulgadas_sold < len(row) and row[idx_pulgadas_sold] else None
        if pulgadas_sold_raw:
            try:
                pulgadas_sold = float(pulgadas_sold_raw)
                if pulgadas_sold < 0:
                    logger.warning(f"Negative Pulgadas_SOLD for {tag_spool}: {pulgadas_sold}, defaulting to None")
                    pulgadas_sold = None
            except (ValueError, TypeError):
                logger.warning(f"Invalid Pulgadas_SOLD for {tag_spool}: {pulgadas_sold_raw}, defaulting to None")
                pulgadas_sold = None

        # 9. Crear objeto Spool con datos base
        # NOTA: Los estados reales se reconstruyen en ValidationService desde MetadataRepository
        return Spool(
            tag_spool=tag_spool,
            ot=ot,  # v4.0: Orden de Trabajo
            nv=nv,  # v2.0: Número de Nota de Venta para filtrado
            total_uniones=total_uniones,  # v4.0: version detection field
            uniones_arm_completadas=uniones_arm_completadas,  # v4.0: ARM counter
            uniones_sold_completadas=uniones_sold_completadas,  # v4.0: SOLD counter
            pulgadas_arm=pulgadas_arm,  # v4.0: ARM pulgadas-diámetro metric
            pulgadas_sold=pulgadas_sold,  # v4.0: SOLD pulgadas-diámetro metric
            arm=arm_status,  # DEFAULT: Se reconstruye después
            sold=sold_status,  # DEFAULT: Se reconstruye después
            fecha_materiales=fecha_materiales,
            fecha_armado=fecha_armado,
            armador=armador,
            fecha_soldadura=fecha_soldadura,
            soldador=soldador,
            proyecto=None,  # TODO: Agregar si existe columna proyecto
            # v3.0: Campos de ocupación
            ocupado_por=ocupado_por,
            fecha_ocupacion=fecha_ocupacion,
            version=version,
            estado_detalle=estado_detalle
        )


if __name__ == "__main__":
    """Script de prueba para validar el servicio."""
    import logging
    logging.basicConfig(level=logging.INFO)

    # Test safe_float
    print("\n=== Test safe_float ===")
    assert SheetsService.safe_float("0.1") == 0.1
    assert SheetsService.safe_float("1") == 1.0
    assert SheetsService.safe_float("") == 0.0
    assert SheetsService.safe_float(None) == 0.0
    assert SheetsService.safe_float("abc") == 0.0
    print("✅ safe_float tests passed")

    # Test parse_date
    print("\n=== Test parse_date ===")
    assert SheetsService.parse_date("30/7/2025") == date(2025, 7, 30)
    assert SheetsService.parse_date("2025-11-08") == date(2025, 11, 8)
    assert SheetsService.parse_date("") is None
    assert SheetsService.parse_date(None) is None
    print("✅ parse_date tests passed")

    # Test parse_worker_row (v2.0 con Id y Rol)
    print("\n=== Test parse_worker_row ===")
    worker_row = ["93", "Mauricio", "Rodriguez", "Armador", "TRUE"]
    worker = SheetsService.parse_worker_row(worker_row)
    assert worker.id == 93
    assert worker.nombre == "Mauricio"
    assert worker.apellido == "Rodriguez"
    assert worker.rol.value == "Armador"
    assert worker.activo is True
    print(f"✅ parse_worker_row: Id={worker.id}, {worker.nombre_completo}, rol={worker.rol.value}, activo={worker.activo}")

    # Test parse_spool_row (v2.1 Dynamic Mapping - estados siempre PENDIENTE)
    print("\n=== Test parse_spool_row ===")

    # Crear column_map mockeado con índices correctos
    mock_column_map = {
        "tagspool": 6,
        "nv": 1,
        "fechamateriales": 32,  # Columna AG (correcto)
        "fechaarmado": 33,      # Columna AH (correcto)
        "armador": 34,          # Columna AI (correcto)
        "fechasoldadura": 35,   # Columna AJ (correcto)
        "soldador": 36          # Columna AK (correcto)
    }

    # Instanciar SheetsService con column_map
    sheets_service = SheetsService(column_map=mock_column_map)

    # Crear fila de prueba con índices correctos
    spool_row = [''] * 65
    spool_row[6] = "MK-1335-CW-25238-011"  # G - TAG_SPOOL
    spool_row[32] = "30/7/2025"            # AG - Fecha_Materiales (CORRECTO)
    spool_row[33] = "05/8/2025"            # AH - Fecha_Armado (CORRECTO)
    spool_row[34] = "Juan Pérez"           # AI - Armador (CORRECTO)

    spool = sheets_service.parse_spool_row(spool_row)
    assert spool.tag_spool == "MK-1335-CW-25238-011"
    assert spool.arm == ActionStatus.PENDIENTE  # Siempre PENDIENTE (se reconstruye desde Metadata)
    assert spool.sold == ActionStatus.PENDIENTE  # Siempre PENDIENTE
    assert spool.fecha_materiales == date(2025, 7, 30)
    assert spool.fecha_armado == date(2025, 8, 5)
    assert spool.armador == "Juan Pérez"
    print(f"✅ parse_spool_row: {spool.tag_spool}, ARM={spool.arm.value} (default), fecha_materiales={spool.fecha_materiales}")

    print("\n✅ Todos los tests pasaron exitosamente")
