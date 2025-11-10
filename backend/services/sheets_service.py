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
    # Hoja "Operaciones"
    IDX_TAG_SPOOL = 6           # G - TAG_SPOOL / CODIGO BARRA
    IDX_ARM = 21                # V - ARM (Armado)
    IDX_SOLD = 22               # W - SOLD (Soldado)
    IDX_FECHA_MATERIALES = 52   # BA - Fecha_Materiales
    IDX_FECHA_ARMADO = 53       # BB - Fecha_Armado
    IDX_ARMADOR = 54            # BC - Armador
    IDX_FECHA_SOLDADURA = 55    # BD - Fecha_Soldadura
    IDX_SOLDADOR = 56           # BE - Soldador

    # Hoja "Trabajadores" - Estructura real: Id | Nombre | Apellido | Rol | Activo
    IDX_WORKER_NOMBRE = 1       # B - Nombre (columna 1)
    IDX_WORKER_APELLIDO = 2     # C - Apellido (columna 2)
    IDX_WORKER_ACTIVO = 4       # E - Activo (columna 4)

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

        Args:
            row: Lista con valores de la fila (índices: Nombre=0, Apellido=1, Activo=2)

        Returns:
            Worker: Objeto Worker parseado

        Raises:
            ValueError: Si la fila no tiene suficientes columnas o nombre está vacío

        Examples:
            >>> row = ["Juan", "Pérez", "Si"]
            >>> worker = SheetsService.parse_worker_row(row)
            >>> worker.nombre
            'Juan'
            >>> worker.apellido
            'Pérez'
            >>> worker.activo
            True
        """
        # Validar longitud mínima
        if len(row) < 1:
            raise ValueError("Fila de trabajador vacía o sin nombre")

        # Parsear nombre (obligatorio)
        nombre = row[cls.IDX_WORKER_NOMBRE].strip() if len(row) > cls.IDX_WORKER_NOMBRE else ""
        if not nombre:
            raise ValueError("Nombre de trabajador vacío")

        # Parsear apellido (opcional)
        apellido = None
        if len(row) > cls.IDX_WORKER_APELLIDO and row[cls.IDX_WORKER_APELLIDO]:
            apellido = row[cls.IDX_WORKER_APELLIDO].strip()
            if apellido == '':
                apellido = None

        # Parsear activo (opcional, default=True)
        activo = True
        if len(row) > cls.IDX_WORKER_ACTIVO and row[cls.IDX_WORKER_ACTIVO]:
            activo_str = row[cls.IDX_WORKER_ACTIVO].strip().lower()
            # Valores que se consideran "activo"
            activo = activo_str in ["si", "sí", "yes", "true", "1", "y"]

        return Worker(
            nombre=nombre,
            apellido=apellido,
            activo=activo
        )

    @classmethod
    def parse_spool_row(cls, row: list) -> Spool:
        """
        Parsea una fila de la hoja 'Operaciones' a un objeto Spool.

        Maneja:
        - Conversión string→float para ARM/SOLD
        - Conversión ActionStatus.from_sheets_value()
        - Parseo de fechas en múltiples formatos
        - Valores vacíos/nulos en cualquier columna
        - Validación de consistencia (warning si ARM=0.1 sin armador)

        Args:
            row: Lista con valores de la fila (mínimo 57 columnas)

        Returns:
            Spool: Objeto Spool parseado

        Raises:
            ValueError: Si TAG_SPOOL está vacío

        Examples:
            >>> row = [''] * 57
            >>> row[6] = "MK-123"           # TAG_SPOOL
            >>> row[21] = "0.1"             # ARM (string!)
            >>> row[22] = "0"               # SOLD
            >>> row[52] = "30/7/2025"       # Fecha_Materiales
            >>> row[54] = "Juan Pérez"      # Armador
            >>> spool = SheetsService.parse_spool_row(row)
            >>> spool.tag_spool
            'MK-123'
            >>> spool.arm
            <ActionStatus.EN_PROGRESO: 'EN_PROGRESO'>
            >>> spool.sold
            <ActionStatus.PENDIENTE: 'PENDIENTE'>
        """
        # Validar y rellenar fila si es muy corta
        if len(row) < 57:
            # Rellenar con strings vacíos
            row = row + [''] * (57 - len(row))
            logger.debug(f"Fila corta rellenada a 57 columnas (original: {len(row)})")

        # 1. Parsear TAG_SPOOL (obligatorio)
        tag_spool = row[cls.IDX_TAG_SPOOL].strip() if row[cls.IDX_TAG_SPOOL] else None
        if not tag_spool:
            raise ValueError("TAG_SPOOL vacío en fila")

        # 2. Parsear estados ARM/SOLD con conversión string→float
        arm_float = cls.safe_float(row[cls.IDX_ARM], default=0.0)
        sold_float = cls.safe_float(row[cls.IDX_SOLD], default=0.0)

        # Convertir float a ActionStatus
        try:
            arm_status = ActionStatus.from_sheets_value(arm_float)
            sold_status = ActionStatus.from_sheets_value(sold_float)
        except ValueError as e:
            logger.error(
                f"Error parseando estados para spool {tag_spool}: {e}. "
                f"ARM={arm_float}, SOLD={sold_float}"
            )
            # Usar PENDIENTE como fallback
            arm_status = ActionStatus.PENDIENTE
            sold_status = ActionStatus.PENDIENTE

        # 3. Parsear fechas
        fecha_materiales = cls.parse_date(row[cls.IDX_FECHA_MATERIALES])
        fecha_armado = cls.parse_date(row[cls.IDX_FECHA_ARMADO])
        fecha_soldadura = cls.parse_date(row[cls.IDX_FECHA_SOLDADURA])

        # 4. Parsear trabajadores (limpiar espacios, None si vacío)
        armador = row[cls.IDX_ARMADOR].strip() if row[cls.IDX_ARMADOR] else None
        if armador == '':
            armador = None

        soldador = row[cls.IDX_SOLDADOR].strip() if row[cls.IDX_SOLDADOR] else None
        if soldador == '':
            soldador = None

        # 5. Validación de consistencia (warning si estado inconsistente con trabajador)
        if arm_status == ActionStatus.EN_PROGRESO and not armador:
            logger.warning(
                f"⚠️  Inconsistencia en spool {tag_spool}: ARM=0.1 (EN_PROGRESO) "
                f"pero armador está vacío"
            )
        if sold_status == ActionStatus.EN_PROGRESO and not soldador:
            logger.warning(
                f"⚠️  Inconsistencia en spool {tag_spool}: SOLD=0.1 (EN_PROGRESO) "
                f"pero soldador está vacío"
            )

        # 6. Crear objeto Spool
        return Spool(
            tag_spool=tag_spool,
            arm=arm_status,
            sold=sold_status,
            fecha_materiales=fecha_materiales,
            fecha_armado=fecha_armado,
            armador=armador,
            fecha_soldadura=fecha_soldadura,
            soldador=soldador,
            proyecto=None  # TODO: Agregar índice si existe en Sheet
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

    # Test parse_worker_row
    print("\n=== Test parse_worker_row ===")
    worker_row = ["Juan", "Pérez", "Si"]
    worker = SheetsService.parse_worker_row(worker_row)
    assert worker.nombre == "Juan"
    assert worker.apellido == "Pérez"
    assert worker.activo is True
    print(f"✅ parse_worker_row: {worker.nombre_completo}, activo={worker.activo}")

    # Test parse_spool_row
    print("\n=== Test parse_spool_row ===")
    spool_row = [''] * 57
    spool_row[6] = "MK-TEST-001"
    spool_row[21] = "0.1"  # ARM como string
    spool_row[22] = "0"    # SOLD como string
    spool_row[52] = "30/7/2025"
    spool_row[54] = "Juan Pérez"

    spool = SheetsService.parse_spool_row(spool_row)
    assert spool.tag_spool == "MK-TEST-001"
    assert spool.arm == ActionStatus.EN_PROGRESO
    assert spool.sold == ActionStatus.PENDIENTE
    assert spool.armador == "Juan Pérez"
    print(f"✅ parse_spool_row: {spool.tag_spool}, ARM={spool.arm.value}, armador={spool.armador}")

    print("\n✅ Todos los tests pasaron exitosamente")
