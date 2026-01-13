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

    Todos los métodos son estáticos/classmethod ya que no mantienen estado.
    """

    # Índices de columnas en Google Sheets (0-indexed)
    # Hoja "Operaciones" v2.0 - Event Sourcing (READ-ONLY)
    # Nota: Estados ARM/SOLD se reconstruyen desde Metadata, NO desde estas columnas
    IDX_NV = 1                  # B  - NV (Número de Nota de Venta) - v2.0 filtrado multidimensional
    IDX_TAG_SPOOL = 6           # G  - TAG_SPOOL / CODIGO_BARRA
    IDX_FECHA_MATERIALES = 35   # AJ - Fecha_Materiales (prerequisito para ARM)
    IDX_FECHA_ARMADO = 36       # AK - Fecha_Armado (legacy - solo lectura)
    IDX_ARMADOR = 37            # AL - Armador (legacy - solo lectura)
    IDX_FECHA_SOLDADURA = 38    # AM - Fecha_Soldadura (legacy - solo lectura)
    IDX_SOLDADOR = 39           # AN - Soldador (legacy - solo lectura)
    IDX_FECHA_METROLOGIA = 40   # AO - Fecha_Metrología (v2.0 nuevo)

    # Hoja "Trabajadores" - Estructura v2.0: Id | Nombre | Apellido | Rol | Activo
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
            "%d/%m/%Y",     # 30/7/2025 (más común en Sheets)
            "%d/%m/%y",     # 30/7/25
            "%Y-%m-%d",     # 2025-11-08 (ISO format)
            "%d-%b-%Y",     # 08-Nov-2025
            "%d-%m-%Y",     # 08-11-2025
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

    @classmethod
    def parse_spool_row(cls, row: list) -> Spool:
        """
        Parsea una fila de la hoja 'Operaciones' a un objeto Spool (v2.0 Event Sourcing).

        **IMPORTANTE v2.0:**
        - La hoja Operaciones es READ-ONLY (no se modifica)
        - Estados ARM/SOLD se reconstruyen desde hoja Metadata (Event Sourcing)
        - Esta función solo lee datos base: tag_spool, fecha_materiales, etc.
        - Estados siempre se setean como PENDIENTE (se reconstruyen después)

        Args:
            row: Lista con valores de la fila (mínimo 41 columnas)

        Returns:
            Spool: Objeto Spool con datos base (estados PENDIENTE por defecto)

        Raises:
            ValueError: Si TAG_SPOOL está vacío

        Examples:
            >>> row = [''] * 65
            >>> row[6] = "MK-1335-CW-25238-011"  # TAG_SPOOL
            >>> row[35] = "30/7/2025"             # Fecha_Materiales (AJ)
            >>> spool = SheetsService.parse_spool_row(row)
            >>> spool.tag_spool
            'MK-1335-CW-25238-011'
            >>> spool.arm  # Siempre PENDIENTE (se reconstruye desde Metadata)
            <ActionStatus.PENDIENTE: 'PENDIENTE'>
        """
        # Validar y rellenar fila si es muy corta
        if len(row) < 41:  # Mínimo hasta AO (Fecha_Metrología)
            row = row + [''] * (41 - len(row))
            logger.debug(f"Fila corta rellenada a 41 columnas (original: {len(row)})")

        # 1. Parsear TAG_SPOOL (obligatorio)
        tag_spool = row[cls.IDX_TAG_SPOOL].strip() if row[cls.IDX_TAG_SPOOL] else None
        if not tag_spool:
            raise ValueError("TAG_SPOOL vacío en fila")

        # 1.5. Parsear NV (v2.0 - opcional para filtrado multidimensional)
        nv = row[cls.IDX_NV].strip() if cls.IDX_NV < len(row) and row[cls.IDX_NV] else None
        if nv == '':
            nv = None

        # 2. Estados ARM/SOLD siempre PENDIENTE (se reconstruyen desde Metadata)
        # No leemos estados de Operaciones porque es READ-ONLY en v2.0
        arm_status = ActionStatus.PENDIENTE
        sold_status = ActionStatus.PENDIENTE

        # 3. Parsear fechas (solo lectura, NO se usan para determinar estado)
        fecha_materiales = cls.parse_date(row[cls.IDX_FECHA_MATERIALES])
        fecha_armado = cls.parse_date(row[cls.IDX_FECHA_ARMADO])
        fecha_soldadura = cls.parse_date(row[cls.IDX_FECHA_SOLDADURA])

        # 4. Parsear trabajadores legacy (solo lectura informativa)
        armador = row[cls.IDX_ARMADOR].strip() if cls.IDX_ARMADOR < len(row) and row[cls.IDX_ARMADOR] else None
        if armador == '':
            armador = None

        soldador = row[cls.IDX_SOLDADOR].strip() if cls.IDX_SOLDADOR < len(row) and row[cls.IDX_SOLDADOR] else None
        if soldador == '':
            soldador = None

        # 5. Crear objeto Spool con datos base
        # NOTA: Los estados reales se reconstruyen en ValidationService desde MetadataRepository
        return Spool(
            tag_spool=tag_spool,
            nv=nv,  # v2.0: Número de Nota de Venta para filtrado
            arm=arm_status,  # DEFAULT: Se reconstruye después
            sold=sold_status,  # DEFAULT: Se reconstruye después
            fecha_materiales=fecha_materiales,
            fecha_armado=fecha_armado,
            armador=armador,
            fecha_soldadura=fecha_soldadura,
            soldador=soldador,
            proyecto=None  # TODO: Agregar si existe columna proyecto
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

    # Test parse_spool_row (v2.0 Event Sourcing - estados siempre PENDIENTE)
    print("\n=== Test parse_spool_row ===")
    spool_row = [''] * 65  # v2.0 tiene 65 columnas
    spool_row[6] = "MK-1335-CW-25238-011"  # G - TAG_SPOOL
    spool_row[35] = "30/7/2025"            # AJ - Fecha_Materiales
    spool_row[36] = "05/8/2025"            # AK - Fecha_Armado (legacy)
    spool_row[37] = "Juan Pérez"           # AL - Armador (legacy)

    spool = SheetsService.parse_spool_row(spool_row)
    assert spool.tag_spool == "MK-1335-CW-25238-011"
    assert spool.arm == ActionStatus.PENDIENTE  # Siempre PENDIENTE (se reconstruye desde Metadata)
    assert spool.sold == ActionStatus.PENDIENTE  # Siempre PENDIENTE
    assert spool.fecha_materiales == date(2025, 7, 30)
    assert spool.fecha_armado == date(2025, 8, 5)
    assert spool.armador == "Juan Pérez"
    print(f"✅ parse_spool_row: {spool.tag_spool}, ARM={spool.arm.value} (default), fecha_materiales={spool.fecha_materiales}")

    print("\n✅ Todos los tests pasaron exitosamente")
