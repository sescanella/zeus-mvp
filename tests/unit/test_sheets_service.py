"""
Tests unitarios para SheetsService (parseo de filas).

Tests:
- safe_float: Conversión string→float
- parse_date: Parseo de fechas múltiples formatos
- parse_worker_row: Parseo de trabajadores
- parse_spool_row: Parseo de spools con conversión de tipos
"""
import pytest
from datetime import date
from backend.services.sheets_service import SheetsService
from backend.models.worker import Worker
from backend.models.spool import Spool
from backend.models.enums import ActionStatus


class TestSafeFloat:
    """Tests para el método safe_float."""

    def test_safe_float_converts_string_to_float(self):
        """Test: Convierte strings numéricos a float."""
        assert SheetsService.safe_float("0.1") == 0.1
        assert SheetsService.safe_float("1") == 1.0
        assert SheetsService.safe_float("0") == 0.0
        assert SheetsService.safe_float("123.456") == 123.456

    def test_safe_float_handles_empty_values(self):
        """Test: Maneja valores vacíos retornando default."""
        assert SheetsService.safe_float("") == 0.0
        assert SheetsService.safe_float(None) == 0.0
        assert SheetsService.safe_float("  ") == 0.0

    def test_safe_float_handles_invalid_values(self):
        """Test: Maneja valores inválidos retornando default."""
        assert SheetsService.safe_float("abc") == 0.0
        assert SheetsService.safe_float("0.1.2") == 0.0
        assert SheetsService.safe_float("text123") == 0.0

    def test_safe_float_with_custom_default(self):
        """Test: Respeta valor default personalizado."""
        assert SheetsService.safe_float("", default=99.9) == 99.9
        assert SheetsService.safe_float(None, default=-1.0) == -1.0
        assert SheetsService.safe_float("invalid", default=42.0) == 42.0

    def test_safe_float_strips_whitespace(self):
        """Test: Limpia espacios antes de convertir."""
        assert SheetsService.safe_float("  0.1  ") == 0.1
        assert SheetsService.safe_float("\t1.5\n") == 1.5

    def test_safe_float_handles_int_input(self):
        """Test: Maneja input de tipo int correctamente."""
        assert SheetsService.safe_float(1) == 1.0
        assert SheetsService.safe_float(0) == 0.0

    def test_safe_float_handles_float_input(self):
        """Test: Maneja input de tipo float correctamente."""
        assert SheetsService.safe_float(0.1) == 0.1
        assert SheetsService.safe_float(1.5) == 1.5


class TestParseDate:
    """Tests para el método parse_date."""

    def test_parse_date_multiple_formats(self):
        """Test: Soporta múltiples formatos de fecha."""
        # DD/MM/YYYY
        assert SheetsService.parse_date("30/7/2025") == date(2025, 7, 30)
        assert SheetsService.parse_date("08/11/2025") == date(2025, 11, 8)

        # YYYY-MM-DD (ISO format)
        assert SheetsService.parse_date("2025-11-08") == date(2025, 11, 8)

        # DD-MM-YYYY
        assert SheetsService.parse_date("08-11-2025") == date(2025, 11, 8)

    def test_parse_date_returns_none_for_empty(self):
        """Test: Retorna None para valores vacíos."""
        assert SheetsService.parse_date("") is None
        assert SheetsService.parse_date(None) is None
        assert SheetsService.parse_date("  ") is None

    def test_parse_date_logs_warning_for_unknown_format(self):
        """Test: Retorna None y logea warning para formato desconocido."""
        result = SheetsService.parse_date("invalid-date")
        assert result is None

        result = SheetsService.parse_date("99/99/9999")
        assert result is None

    def test_parse_date_handles_short_year(self):
        """Test: Maneja años cortos (YY)."""
        assert SheetsService.parse_date("08/11/25") == date(2025, 11, 8)


class TestParseWorkerRow:
    """Tests para el método parse_worker_row."""

    def test_parse_worker_row_full_data(self):
        """Test: Parsea trabajador con todos los datos."""
        row = ["Juan", "Pérez", "Si"]
        worker = SheetsService.parse_worker_row(row)

        assert isinstance(worker, Worker)
        assert worker.nombre == "Juan"
        assert worker.apellido == "Pérez"
        assert worker.activo is True

    def test_parse_worker_row_without_apellido(self):
        """Test: Parsea trabajador sin apellido."""
        row = ["María", "", "Si"]
        worker = SheetsService.parse_worker_row(row)

        assert worker.nombre == "María"
        assert worker.apellido is None
        assert worker.activo is True

    def test_parse_worker_row_inactive_worker(self):
        """Test: Parsea trabajador inactivo."""
        row = ["Pedro", "López", "No"]
        worker = SheetsService.parse_worker_row(row)

        assert worker.nombre == "Pedro"
        assert worker.activo is False

    def test_parse_worker_row_various_activo_formats(self):
        """Test: Reconoce múltiples formatos de 'activo'."""
        # Activo
        assert SheetsService.parse_worker_row(["Test", "", "si"]).activo is True
        assert SheetsService.parse_worker_row(["Test", "", "sí"]).activo is True
        assert SheetsService.parse_worker_row(["Test", "", "Si"]).activo is True
        assert SheetsService.parse_worker_row(["Test", "", "yes"]).activo is True
        assert SheetsService.parse_worker_row(["Test", "", "true"]).activo is True
        assert SheetsService.parse_worker_row(["Test", "", "1"]).activo is True

        # Inactivo
        assert SheetsService.parse_worker_row(["Test", "", "no"]).activo is False
        assert SheetsService.parse_worker_row(["Test", "", "false"]).activo is False
        assert SheetsService.parse_worker_row(["Test", "", "0"]).activo is False

    def test_parse_worker_row_default_activo_true(self):
        """Test: Si campo activo vacío, default es True."""
        row = ["Juan", "Pérez"]  # Sin campo activo
        worker = SheetsService.parse_worker_row(row)

        assert worker.activo is True

    def test_parse_worker_row_raises_on_empty_nombre(self):
        """Test: Lanza ValueError si nombre está vacío."""
        with pytest.raises(ValueError, match="vacío"):
            SheetsService.parse_worker_row(["", "Pérez", "Si"])

    def test_parse_worker_row_raises_on_empty_row(self):
        """Test: Lanza ValueError si fila está vacía."""
        with pytest.raises(ValueError, match="vacía"):
            SheetsService.parse_worker_row([])

    def test_parse_worker_row_strips_whitespace(self):
        """Test: Limpia espacios en nombre y apellido."""
        row = ["  Juan  ", "  Pérez  ", "Si"]
        worker = SheetsService.parse_worker_row(row)

        assert worker.nombre == "Juan"
        assert worker.apellido == "Pérez"


class TestParseSpoolRow:
    """Tests para el método parse_spool_row."""

    def test_parse_spool_row_full_data(self):
        """Test: Parsea spool con todos los datos."""
        row = [''] * 57
        row[6] = "MK-123"               # TAG_SPOOL
        row[21] = "0.1"                 # ARM (string)
        row[22] = "0"                   # SOLD (string)
        row[52] = "30/7/2025"           # Fecha_Materiales
        row[53] = "08/11/2025"          # Fecha_Armado
        row[54] = "Juan Pérez"          # Armador
        row[55] = "10/11/2025"          # Fecha_Soldadura
        row[56] = "María González"      # Soldador

        spool = SheetsService.parse_spool_row(row)

        assert isinstance(spool, Spool)
        assert spool.tag_spool == "MK-123"
        assert spool.arm == ActionStatus.EN_PROGRESO
        assert spool.sold == ActionStatus.PENDIENTE
        assert spool.fecha_materiales == date(2025, 7, 30)
        assert spool.fecha_armado == date(2025, 11, 8)
        assert spool.armador == "Juan Pérez"
        assert spool.fecha_soldadura == date(2025, 11, 10)
        assert spool.soldador == "María González"

    def test_parse_spool_row_converts_strings_to_action_status(self):
        """Test: Convierte strings ARM/SOLD a ActionStatus correctamente."""
        row = [''] * 57
        row[6] = "MK-TEST"
        row[21] = "0.1"  # String "0.1"
        row[22] = "1"    # String "1"

        spool = SheetsService.parse_spool_row(row)

        assert spool.arm == ActionStatus.EN_PROGRESO
        assert spool.sold == ActionStatus.COMPLETADO

    def test_parse_spool_row_handles_empty_arm_sold(self):
        """Test: Maneja ARM/SOLD vacíos (default PENDIENTE)."""
        row = [''] * 57
        row[6] = "MK-TEST"
        row[21] = ""    # ARM vacío
        row[22] = ""    # SOLD vacío

        spool = SheetsService.parse_spool_row(row)

        assert spool.arm == ActionStatus.PENDIENTE
        assert spool.sold == ActionStatus.PENDIENTE

    def test_parse_spool_row_handles_short_row(self):
        """Test: Rellena filas cortas con strings vacíos."""
        row = [""] * 10  # Solo 10 columnas (necesita 57)
        row[6] = "MK-SHORT"

        spool = SheetsService.parse_spool_row(row)

        assert spool.tag_spool == "MK-SHORT"
        assert spool.arm == ActionStatus.PENDIENTE
        assert spool.sold == ActionStatus.PENDIENTE

    def test_parse_spool_row_handles_none_values(self):
        """Test: Maneja valores None en columnas opcionales."""
        row = [''] * 57
        row[6] = "MK-TEST"
        row[52] = None  # Fecha_Materiales None
        row[54] = None  # Armador None

        spool = SheetsService.parse_spool_row(row)

        assert spool.tag_spool == "MK-TEST"
        assert spool.fecha_materiales is None
        assert spool.armador is None

    def test_parse_spool_row_raises_on_empty_tag_spool(self):
        """Test: Lanza ValueError si TAG_SPOOL está vacío."""
        row = [''] * 57
        row[6] = ""  # TAG_SPOOL vacío

        with pytest.raises(ValueError, match="TAG_SPOOL vacío"):
            SheetsService.parse_spool_row(row)

    def test_parse_spool_row_logs_warning_for_inconsistency(self):
        """Test: Logea warning si ARM=0.1 sin armador."""
        row = [''] * 57
        row[6] = "MK-INCONSISTENT"
        row[21] = "0.1"  # ARM EN_PROGRESO
        row[54] = ""     # Armador vacío (inconsistente)

        # No debe lanzar error, solo warning
        spool = SheetsService.parse_spool_row(row)

        assert spool.tag_spool == "MK-INCONSISTENT"
        assert spool.arm == ActionStatus.EN_PROGRESO
        assert spool.armador is None

    def test_parse_spool_row_strips_whitespace_in_workers(self):
        """Test: Limpia espacios en nombres de trabajadores."""
        row = [''] * 57
        row[6] = "MK-TEST"
        row[54] = "  Juan Pérez  "
        row[56] = "  María González  "

        spool = SheetsService.parse_spool_row(row)

        assert spool.armador == "Juan Pérez"
        assert spool.soldador == "María González"

    def test_parse_spool_row_handles_various_arm_sold_values(self):
        """Test: Maneja diferentes valores de ARM/SOLD (0, 0.1, 1, 1.0)."""
        # ARM=0 (PENDIENTE)
        row = [''] * 57
        row[6] = "TEST1"
        row[21] = "0"
        assert SheetsService.parse_spool_row(row).arm == ActionStatus.PENDIENTE

        # ARM=0.1 (EN_PROGRESO)
        row[6] = "TEST2"
        row[21] = "0.1"
        assert SheetsService.parse_spool_row(row).arm == ActionStatus.EN_PROGRESO

        # ARM=1 (COMPLETADO)
        row[6] = "TEST3"
        row[21] = "1"
        assert SheetsService.parse_spool_row(row).arm == ActionStatus.COMPLETADO

        # ARM=1.0 (COMPLETADO)
        row[6] = "TEST4"
        row[21] = "1.0"
        assert SheetsService.parse_spool_row(row).arm == ActionStatus.COMPLETADO


class TestColumnIndices:
    """Tests para verificar que los índices de columnas son correctos."""

    def test_column_indices_are_correct(self):
        """Test: Índices de columnas coinciden con la documentación."""
        assert SheetsService.IDX_TAG_SPOOL == 6        # G
        assert SheetsService.IDX_ARM == 21             # V
        assert SheetsService.IDX_SOLD == 22            # W
        assert SheetsService.IDX_FECHA_MATERIALES == 52  # BA
        assert SheetsService.IDX_FECHA_ARMADO == 53      # BB
        assert SheetsService.IDX_ARMADOR == 54           # BC
        assert SheetsService.IDX_FECHA_SOLDADURA == 55   # BD
        assert SheetsService.IDX_SOLDADOR == 56          # BE


if __name__ == "__main__":
    """Ejecutar tests con pytest."""
    pytest.main([__file__, "-v"])
