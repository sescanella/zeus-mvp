"""
Servicio para parsear filas de Google Sheets a modelos Pydantic.

Responsabilidades:
- Conversión robusta de valores (string→float, string→date)
- Parseo de filas de Trabajadores → Worker
- Parseo de filas de Operaciones → Spool
- Manejo de valores vacíos, nulos e inválidos
- Validación de consistencia de datos
"""
from typing import Optional, Union, TYPE_CHECKING
from datetime import datetime, date, timedelta
import logging

from backend.models.worker import Worker
from backend.models.spool import Spool
from backend.models.enums import ActionStatus
from backend.exceptions import CriticalColumnDriftError

if TYPE_CHECKING:
    from backend.repositories.sheets_repository import SheetsRepository

logger = logging.getLogger(__name__)


class SheetsService:
    """
    Servicio para parsear filas de Google Sheets a modelos Pydantic.

    v2.1 (Dynamic Column Mapping) + drift-resilient:
    - Lee headers (row 1) para construir mapeo dinámico
    - Busca columnas por NOMBRE en lugar de índice hardcodeado
    - `_column_map` es un property que SIEMPRE consulta el caché global
      `ColumnMapCache` — si la planilla cambió y el caché fue invalidado,
      el próximo acceso ya ve los índices nuevos sin reinstanciar este
      servicio.
    """

    def __init__(
        self,
        sheet_name: Optional[str] = None,
        sheets_repository: Optional["SheetsRepository"] = None,
        column_map: Optional[dict[str, int]] = None,
    ):
        """
        Inicializa el servicio. Acepta dos firmas:

        Recomendada (drift-resilient):
            SheetsService(sheet_name="Operaciones", sheets_repository=repo)
            → `_column_map` será una property dinámica que siempre lee el
              caché global. Cualquier rebuild posterior se refleja
              automáticamente.

        Legacy (tests, scripts ad-hoc):
            SheetsService(column_map=some_static_map)
            → `_column_map` queda fijo en el dict pasado. Útil para tests
              unitarios sin SheetsRepository.

        Raises:
            ValueError: Si ni column_map ni (sheet_name + sheets_repository)
                están presentes; o si column_map se pasa vacío.
        """
        if sheet_name is not None and sheets_repository is not None:
            self._sheet_name = sheet_name
            self._sheets_repo = sheets_repository
            self._static_column_map: Optional[dict[str, int]] = None
            # Fail-fast at construction: trigger a build if not cached yet.
            _ = self._column_map
        elif column_map:
            self._sheet_name = None
            self._sheets_repo = None
            self._static_column_map = dict(column_map)
        else:
            raise ValueError(
                "SheetsService requires either (sheet_name + sheets_repository) "
                "or a non-empty column_map. Use ColumnMapCache.get_or_build() "
                "to obtain a map."
            )

    @property
    def _column_map(self) -> dict[str, int]:
        """
        Always returns the live column map.

        If constructed with `sheet_name + sheets_repository`, defers to the
        global ColumnMapCache — picks up any rebuild done by
        `read_worksheet` automatically. Otherwise returns the static map
        provided at construction time.
        """
        if self._static_column_map is not None:
            return self._static_column_map
        from backend.core.column_map_cache import ColumnMapCache
        return ColumnMapCache.get_or_build(self._sheet_name, self._sheets_repo)

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

        from backend.utils.normalize import normalize_column_name as normalize

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

    def _get_col_idx(self, column_name: str) -> int:
        """
        Obtiene el índice de una columna por su nombre.

        Si la columna no existe en el mapeo (planilla rota o columna crítica
        renombrada/eliminada), se lanza `CriticalColumnDriftError` que
        propaga como HTTP 503 — mejor fallar fuerte que devolver índice
        equivocado y corromper datos silenciosamente.

        Args:
            column_name: Nombre de la columna (ej: "Fecha_Armado").

        Returns:
            Índice (0-based) de la columna en la fila.

        Raises:
            CriticalColumnDriftError: Si la columna no está en el mapeo
                vigente.
        """
        from backend.utils.normalize import normalize_column_name
        normalized = normalize_column_name(column_name)

        column_map = self._column_map
        if normalized in column_map:
            return column_map[normalized]

        raise CriticalColumnDriftError(
            sheet_name=self._sheet_name or "<static-map>",
            expected_column=column_name,
            actual_header_at_index=None,
        )

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
    def parse_date(value) -> Optional[date]:
        """
        Parsea fechas en múltiples formatos comunes.

        Acepta:
        - Strings: DD/MM/YYYY, DD/MM/YY, YYYY-MM-DD, DD-MMM-YYYY, DD-MM-YYYY
        - Excel serial dates como int/float (resultado de leer una celda con
          formato "Fecha" con value_render_option=UNFORMATTED_VALUE). El
          epoch de Google Sheets/Excel es 1899-12-30 (compensa el bug de
          año bisiesto 1900 que tiene Excel).

        Returns:
            date object o None si vacío/inválido

        Examples:
            >>> SheetsService.parse_date("30/7/2025")
            date(2025, 7, 30)
            >>> SheetsService.parse_date(46153)
            date(2026, 5, 11)
            >>> SheetsService.parse_date("")
            None
        """
        # Manejar valores vacíos/nulos
        if value is None or value == "":
            return None

        # Excel/Google Sheets serial date (cell with date format read as
        # UNFORMATTED_VALUE). Treat booleans as not-a-date even though they
        # are subclasses of int in Python.
        if isinstance(value, bool):
            return None
        if isinstance(value, (int, float)):
            try:
                return date(1899, 12, 30) + timedelta(days=int(value))
            except (ValueError, OverflowError) as e:
                logger.warning(
                    f"Valor inválido para serial date: {value!r}. "
                    f"Error: {e}"
                )
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

    @staticmethod
    def parse_datetime(value) -> Optional[datetime]:
        """
        Parsea datetimes (fecha + hora) en múltiples formatos comunes.

        Hermano de parse_date pero retorna datetime (no date).

        Acepta:
        - Strings: "DD-MM-YYYY HH:MM:SS" (formato canónico — usado para
          Fecha_Ocupacion), "DD/MM/YYYY HH:MM:SS", "YYYY-MM-DD HH:MM:SS",
          y también solo-fecha como fallback ("DD-MM-YYYY", "YYYY-MM-DD").
        - Excel/Google Sheets serial datetime como float (resultado
          UNFORMATTED_VALUE en celda con formato "Fecha y hora"). La parte
          entera son días desde epoch 1899-12-30, la fraccional es hora
          del día (0.5 = mediodía). Compensa el bug año bisiesto 1900 de
          Excel igual que parse_date.

        Returns:
            datetime object o None si vacío/inválido.

        Examples:
            >>> SheetsService.parse_datetime("13-05-2026 11:33:48")
            datetime(2026, 5, 13, 11, 33, 48)
            >>> SheetsService.parse_datetime(46155.48180555556)
            datetime(2026, 5, 13, 11, 33, 48)  # approx
            >>> SheetsService.parse_datetime("")
            None
        """
        if value is None or value == "":
            return None
        if isinstance(value, bool):
            return None
        if isinstance(value, (int, float)):
            try:
                return datetime(1899, 12, 30) + timedelta(days=float(value))
            except (ValueError, OverflowError) as e:
                logger.warning(
                    f"Serial datetime inválido: {value!r}. Error: {e}"
                )
                return None

        value_str = str(value).strip()
        if value_str == "":
            return None

        formats = [
            "%d-%m-%Y %H:%M:%S",  # canónico (cómo lo escribe el backend)
            "%d/%m/%Y %H:%M:%S",  # legacy
            "%Y-%m-%d %H:%M:%S",  # ISO
            "%d-%m-%Y",            # fallback: solo fecha
            "%Y-%m-%d",            # fallback ISO
        ]
        for fmt in formats:
            try:
                return datetime.strptime(value_str, fmt)
            except ValueError:
                continue

        logger.warning(f"Formato de datetime no reconocido: '{value_str}'")
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

        # With value_render_option=UNFORMATTED_VALUE, the worker Id may come
        # back as int and the Activo column may come back as a Python bool.
        # Coerce defensively before calling .strip()/.isdigit()/etc.
        def _as_text(v) -> str:
            if v is None:
                return ""
            if isinstance(v, bool):
                return "TRUE" if v else "FALSE"
            return str(v).strip()

        # Detectar formato basándose en si la primera columna es un Id numérico
        first_col_is_id = False
        if isinstance(row[0], (int, float)) and not isinstance(row[0], bool):
            first_col_is_id = True
        elif row[0] and _as_text(row[0]).isdigit():
            first_col_is_id = True

        # Determinar estructura del sheet
        if len(row) >= 5 and first_col_is_id:
            # Formato v2.0 completo: A=Id | B=Nombre | C=Apellido | D=Rol | E=Activo
            worker_id = int(_as_text(row[0]))
            idx_nombre = 1
            idx_apellido = 2
            idx_rol = 3
            idx_activo = 4
            has_rol = True
        elif len(row) == 4 and first_col_is_id:
            # Formato híbrido (migración parcial): A=Id | B=Nombre | C=Apellido | D=Activo (SIN Rol)
            worker_id = int(_as_text(row[0]))
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
        nombre = _as_text(row[idx_nombre])
        if not nombre:
            raise ValueError("Nombre de trabajador vacío")

        # 3. Parsear apellido (obligatorio)
        apellido = _as_text(row[idx_apellido])
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
            rol_str = _as_text(row[idx_rol])
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
        # UNFORMATTED_VALUE returns checkbox/boolean cells as Python bool;
        # FORMATTED_VALUE returns the string "TRUE"/"FALSE". Handle both.
        raw_activo = row[idx_activo]
        if isinstance(raw_activo, bool):
            activo = bool(raw_activo)
        else:
            activo_str = _as_text(raw_activo).upper()
            if not activo_str:
                logger.warning(f"Campo Activo vacío para {nombre} {apellido}, usando FALSE por defecto")
                activo = False
            else:
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

        # 1. Obtener índices usando mapeo dinámico (column map validated at startup)
        idx_tag_spool = self._get_col_idx("SPLIT")  # Real column name in Sheet
        idx_ot = self._get_col_idx("OT")  # v4.0: Orden de Trabajo
        idx_nv = self._get_col_idx("NV")
        idx_fecha_materiales = self._get_col_idx("Fecha_Materiales")
        idx_fecha_armado = self._get_col_idx("Fecha_Armado")
        idx_armador = self._get_col_idx("Armador")
        idx_fecha_soldadura = self._get_col_idx("Fecha_Soldadura")
        idx_soldador = self._get_col_idx("Soldador")

        # v3.0: Índices de columnas de ocupación
        idx_ocupado_por = self._get_col_idx("Ocupado_Por")
        idx_fecha_ocupacion = self._get_col_idx("Fecha_Ocupacion")
        idx_estado_detalle = self._get_col_idx("Estado_Detalle")

        # v4.0: Índices de columnas de métricas de uniones
        idx_total_uniones = self._get_col_idx("Total_Uniones")
        idx_uniones_arm = self._get_col_idx("Uniones_ARM_Completadas")
        idx_uniones_sold = self._get_col_idx("Uniones_SOLD_Completadas")
        idx_pulgadas_arm = self._get_col_idx("Pulgadas_ARM")
        idx_pulgadas_sold = self._get_col_idx("Pulgadas_SOLD")

        # With value_render_option=UNFORMATTED_VALUE every cell can come back
        # as int/float/bool/str depending on its on-sheet type. The helpers
        # below normalize each value so calling .strip()/int()/float() is
        # always safe.
        def _cell_str(v) -> Optional[str]:
            if v is None:
                return None
            s = str(v).strip()
            return s if s != "" else None

        def _cell_int(v, field_name: str, tag: str) -> Optional[int]:
            if v is None or v == "":
                return None
            try:
                n = int(v) if not isinstance(v, bool) else None
                if n is None:
                    return None
                if n < 0:
                    logger.warning(f"Negative {field_name} for {tag}: {n}, defaulting to None")
                    return None
                return n
            except (ValueError, TypeError):
                logger.warning(f"Invalid {field_name} for {tag}: {v!r}, defaulting to None")
                return None

        def _cell_float(v, field_name: str, tag: str) -> Optional[float]:
            if v is None or v == "":
                return None
            try:
                f = float(v) if not isinstance(v, bool) else None
                if f is None:
                    return None
                if f < 0:
                    logger.warning(f"Negative {field_name} for {tag}: {f}, defaulting to None")
                    return None
                return f
            except (ValueError, TypeError):
                logger.warning(f"Invalid {field_name} for {tag}: {v!r}, defaulting to None")
                return None

        # 2. Parsear SPLIT (spool identifier - obligatorio)
        tag_spool = _cell_str(row[idx_tag_spool]) if idx_tag_spool < len(row) else None
        if not tag_spool:
            raise ValueError("SPLIT (spool identifier) vacío en fila")

        # 3. Parsear NV (v2.0 - opcional para filtrado multidimensional)
        nv = _cell_str(row[idx_nv]) if idx_nv < len(row) else None

        # 4. Estados ARM/SOLD siempre PENDIENTE (se reconstruyen desde Metadata)
        # No leemos estados de Operaciones porque es READ-ONLY en v2.0
        arm_status = ActionStatus.PENDIENTE
        sold_status = ActionStatus.PENDIENTE

        # 5. Parsear fechas — parse_date acepta tanto strings DD/MM/YYYY como
        # Excel serial dates (int/float, resultado de UNFORMATTED_VALUE
        # sobre celdas con formato Fecha).
        fecha_materiales = self.parse_date(row[idx_fecha_materiales]) if idx_fecha_materiales < len(row) else None
        fecha_armado = self.parse_date(row[idx_fecha_armado]) if idx_fecha_armado < len(row) else None
        fecha_soldadura = self.parse_date(row[idx_fecha_soldadura]) if idx_fecha_soldadura < len(row) else None

        # 6. Parsear trabajadores legacy (solo lectura informativa)
        armador = _cell_str(row[idx_armador]) if idx_armador < len(row) else None
        soldador = _cell_str(row[idx_soldador]) if idx_soldador < len(row) else None

        # 7. Parsear campos v3.0 (ocupación)
        ocupado_por = _cell_str(row[idx_ocupado_por]) if idx_ocupado_por < len(row) else None
        fecha_ocupacion = _cell_str(row[idx_fecha_ocupacion]) if idx_fecha_ocupacion < len(row) else None
        estado_detalle = _cell_str(row[idx_estado_detalle]) if idx_estado_detalle < len(row) else None

        # 8. v4.0: Parse campos de métricas de uniones
        ot = _cell_str(row[idx_ot]) if idx_ot < len(row) else None

        total_uniones = _cell_int(
            row[idx_total_uniones] if idx_total_uniones < len(row) else None,
            "Total_Uniones", tag_spool,
        )
        uniones_arm_completadas = _cell_int(
            row[idx_uniones_arm] if idx_uniones_arm < len(row) else None,
            "Uniones_ARM_Completadas", tag_spool,
        )
        uniones_sold_completadas = _cell_int(
            row[idx_uniones_sold] if idx_uniones_sold < len(row) else None,
            "Uniones_SOLD_Completadas", tag_spool,
        )
        pulgadas_arm = _cell_float(
            row[idx_pulgadas_arm] if idx_pulgadas_arm < len(row) else None,
            "Pulgadas_ARM", tag_spool,
        )
        pulgadas_sold = _cell_float(
            row[idx_pulgadas_sold] if idx_pulgadas_sold < len(row) else None,
            "Pulgadas_SOLD", tag_spool,
        )

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
