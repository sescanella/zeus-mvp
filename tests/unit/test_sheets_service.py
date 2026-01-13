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
    """Tests para el método parse_worker_row (v2.0 estructura)."""

    def test_parse_worker_row_full_data(self):
        """Test: Parsea trabajador con todos los datos (v2.0: Id, Nombre, Apellido, Rol, Activo)."""
        row = ["93", "Mauricio", "Rodriguez", "Armador", "TRUE"]
        worker = SheetsService.parse_worker_row(row)

        assert isinstance(worker, Worker)
        assert worker.id == 93
        assert worker.nombre == "Mauricio"
        assert worker.apellido == "Rodriguez"
        assert worker.rol.value == "Armador"
        assert worker.activo is True

    def test_parse_worker_row_soldador(self):
        """Test: Parsea trabajador con rol Soldador."""
        row = ["42", "Pedro", "López", "Soldador", "TRUE"]
        worker = SheetsService.parse_worker_row(row)

        assert worker.id == 42
        assert worker.nombre == "Pedro"
        assert worker.rol.value == "Soldador"
        assert worker.activo is True

    def test_parse_worker_row_inactive_worker(self):
        """Test: Parsea trabajador inactivo."""
        row = ["10", "María", "González", "Armador", "FALSE"]
        worker = SheetsService.parse_worker_row(row)

        assert worker.nombre == "María"
        assert worker.activo is False

    def test_parse_worker_row_case_insensitive_rol(self):
        """Test: Rol es case-insensitive."""
        # Lowercase
        row = ["1", "Test", "User", "armador", "TRUE"]
        worker = SheetsService.parse_worker_row(row)
        assert worker.rol.value == "Armador"

        # UPPERCASE
        row = ["2", "Test", "User", "SOLDADOR", "TRUE"]
        worker = SheetsService.parse_worker_row(row)
        assert worker.rol.value == "Soldador"

    def test_parse_worker_row_activo_formats(self):
        """Test: Reconoce TRUE/FALSE como strings de Sheets."""
        # Activo
        row = ["1", "Test", "User", "Armador", "TRUE"]
        assert SheetsService.parse_worker_row(row).activo is True

        row = ["1", "Test", "User", "Armador", "true"]
        assert SheetsService.parse_worker_row(row).activo is True

        # Inactivo
        row = ["1", "Test", "User", "Armador", "FALSE"]
        assert SheetsService.parse_worker_row(row).activo is False

        row = ["1", "Test", "User", "Armador", "false"]
        assert SheetsService.parse_worker_row(row).activo is False

    def test_parse_worker_row_raises_on_invalid_id(self):
        """Test: Lanza ValueError si Id no es numérico."""
        with pytest.raises(ValueError, match="Id de trabajador inválido"):
            SheetsService.parse_worker_row(["abc", "Juan", "Pérez", "Armador", "TRUE"])

    def test_parse_worker_row_raises_on_empty_nombre(self):
        """Test: Lanza ValueError si nombre está vacío."""
        with pytest.raises(ValueError, match="Nombre de trabajador vacío"):
            SheetsService.parse_worker_row(["93", "", "Pérez", "Armador", "TRUE"])

    def test_parse_worker_row_raises_on_empty_apellido(self):
        """Test: Lanza ValueError si apellido está vacío (obligatorio en v2.0)."""
        with pytest.raises(ValueError, match="Apellido de trabajador vacío"):
            SheetsService.parse_worker_row(["93", "Juan", "", "Armador", "TRUE"])

    def test_parse_worker_row_raises_on_invalid_rol(self):
        """Test: Lanza ValueError si rol no es válido."""
        with pytest.raises(ValueError, match="Rol inválido"):
            SheetsService.parse_worker_row(["93", "Juan", "Pérez", "INVALID_ROL", "TRUE"])

    def test_parse_worker_row_raises_on_short_row(self):
        """Test: Lanza ValueError si fila no tiene 5 columnas."""
        with pytest.raises(ValueError, match="Fila de trabajador incompleta"):
            SheetsService.parse_worker_row(["93", "Juan", "Pérez"])  # Solo 3 columnas

    def test_parse_worker_row_strips_whitespace(self):
        """Test: Limpia espacios en todos los campos."""
        row = ["  93  ", "  Juan  ", "  Pérez  ", "  Armador  ", "  TRUE  "]
        worker = SheetsService.parse_worker_row(row)

        assert worker.id == 93
        assert worker.nombre == "Juan"
        assert worker.apellido == "Pérez"
        assert worker.rol.value == "Armador"


class TestParseSpoolRow:
    """Tests para el método parse_spool_row (v2.0 Event Sourcing)."""

    def test_parse_spool_row_full_data(self):
        """Test: Parsea spool con datos base (v2.0: estados siempre PENDIENTE)."""
        row = [''] * 65  # v2.0: 65 columnas en producción
        row[6] = "MK-1335-CW-25238-011"  # G - TAG_SPOOL
        row[35] = "30/7/2025"            # AJ - Fecha_Materiales
        row[36] = "08/11/2025"           # AK - Fecha_Armado (legacy)
        row[37] = "Juan Pérez"           # AL - Armador (legacy)
        row[38] = "10/11/2025"           # AM - Fecha_Soldadura (legacy)
        row[39] = "María González"       # AN - Soldador (legacy)

        spool = SheetsService.parse_spool_row(row)

        assert isinstance(spool, Spool)
        assert spool.tag_spool == "MK-1335-CW-25238-011"
        # v2.0: Estados siempre PENDIENTE (se reconstruyen desde Metadata)
        assert spool.arm == ActionStatus.PENDIENTE
        assert spool.sold == ActionStatus.PENDIENTE
        # Fechas y trabajadores legacy (solo lectura)
        assert spool.fecha_materiales == date(2025, 7, 30)
        assert spool.fecha_armado == date(2025, 11, 8)
        assert spool.armador == "Juan Pérez"
        assert spool.fecha_soldadura == date(2025, 11, 10)
        assert spool.soldador == "María González"

    def test_parse_spool_row_estados_siempre_pendiente(self):
        """Test v2.0: ARM/SOLD siempre retornan PENDIENTE (Event Sourcing)."""
        row = [''] * 65
        row[6] = "MK-TEST"
        # En v2.0, no hay columnas ARM/SOLD numéricas - todo viene PENDIENTE

        spool = SheetsService.parse_spool_row(row)

        # CRÍTICO v2.0: Estados SIEMPRE son PENDIENTE (se reconstruyen después)
        assert spool.arm == ActionStatus.PENDIENTE
        assert spool.sold == ActionStatus.PENDIENTE

    def test_parse_spool_row_handles_short_row(self):
        """Test: Rellena filas cortas con strings vacíos (mínimo 41 columnas)."""
        row = [""] * 10  # Solo 10 columnas (necesita 41 mínimo)
        row[6] = "MK-SHORT"

        spool = SheetsService.parse_spool_row(row)

        assert spool.tag_spool == "MK-SHORT"
        assert spool.arm == ActionStatus.PENDIENTE
        assert spool.sold == ActionStatus.PENDIENTE

    def test_parse_spool_row_handles_none_values(self):
        """Test: Maneja valores None en columnas opcionales."""
        row = [''] * 65
        row[6] = "MK-TEST"
        row[35] = None  # Fecha_Materiales None
        row[37] = None  # Armador None

        spool = SheetsService.parse_spool_row(row)

        assert spool.tag_spool == "MK-TEST"
        assert spool.fecha_materiales is None
        assert spool.armador is None

    def test_parse_spool_row_raises_on_empty_tag_spool(self):
        """Test: Lanza ValueError si TAG_SPOOL está vacío."""
        row = [''] * 65
        row[6] = ""  # TAG_SPOOL vacío

        with pytest.raises(ValueError, match="TAG_SPOOL vacío"):
            SheetsService.parse_spool_row(row)

    def test_parse_spool_row_strips_whitespace_in_workers(self):
        """Test: Limpia espacios en nombres de trabajadores legacy."""
        row = [''] * 65
        row[6] = "MK-TEST"
        row[37] = "  Juan Pérez  "    # Armador con espacios
        row[39] = "  María González  " # Soldador con espacios

        spool = SheetsService.parse_spool_row(row)

        assert spool.armador == "Juan Pérez"
        assert spool.soldador == "María González"

    def test_parse_spool_row_empty_strings_become_none(self):
        """Test: Strings vacíos en trabajadores se convierten a None."""
        row = [''] * 65
        row[6] = "MK-TEST"
        row[37] = ""  # Armador vacío
        row[39] = ""  # Soldador vacío

        spool = SheetsService.parse_spool_row(row)

        assert spool.armador is None
        assert spool.soldador is None

    def test_parse_spool_row_prerequisito_fecha_materiales(self):
        """Test: Fecha_Materiales es prerequisito para iniciar ARM."""
        row = [''] * 65
        row[6] = "MK-TEST"
        row[35] = "30/7/2025"  # AJ - Prerequisito

        spool = SheetsService.parse_spool_row(row)

        assert spool.fecha_materiales == date(2025, 7, 30)
        # Estados siempre PENDIENTE (validación de prerequisitos en ValidationService)
        assert spool.arm == ActionStatus.PENDIENTE


class TestColumnIndices:
    """Tests para verificar que los índices de columnas son correctos (v2.0)."""

    def test_column_indices_workers(self):
        """Test: Índices de columnas Workers v2.0."""
        assert SheetsService.IDX_WORKER_ID == 0       # A - Id
        assert SheetsService.IDX_WORKER_NOMBRE == 1   # B - Nombre
        assert SheetsService.IDX_WORKER_APELLIDO == 2 # C - Apellido
        assert SheetsService.IDX_WORKER_ROL == 3      # D - Rol
        assert SheetsService.IDX_WORKER_ACTIVO == 4   # E - Activo

    def test_column_indices_operaciones(self):
        """Test: Índices de columnas Operaciones v2.0 (READ-ONLY)."""
        assert SheetsService.IDX_TAG_SPOOL == 6           # G
        assert SheetsService.IDX_FECHA_MATERIALES == 35   # AJ
        assert SheetsService.IDX_FECHA_ARMADO == 36       # AK (legacy)
        assert SheetsService.IDX_ARMADOR == 37            # AL (legacy)
        assert SheetsService.IDX_FECHA_SOLDADURA == 38    # AM (legacy)
        assert SheetsService.IDX_SOLDADOR == 39           # AN (legacy)
        assert SheetsService.IDX_FECHA_METROLOGIA == 40   # AO (v2.0 nuevo)


if __name__ == "__main__":
    """Ejecutar tests con pytest."""
    pytest.main([__file__, "-v"])
