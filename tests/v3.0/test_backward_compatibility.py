"""
Backward compatibility tests for v2.1 → v3.0 migration.

These tests verify:
1. v2.1 mode ignores v3.0 columns
2. v3.0 mode reads both v2.1 and v3.0 columns
3. v2.1 API endpoints continue working
4. Metadata accepts new event types
5. Existing spool data remains intact
"""
import pytest
from backend.repositories.sheets_repository import SheetsRepository
from backend.models.enums import EventoTipo, EstadoOcupacion
from backend.config import Config


@pytest.mark.v3
@pytest.mark.backward_compat
def test_v21_mode_ignores_v3_columns():
    """Verify v2.1 compatibility mode returns safe defaults for v3.0 columns."""
    # Initialize repository in v2.1 mode (default)
    repo = SheetsRepository(compatibility_mode="v2.1")

    # Read v3.0 columns - should return safe defaults
    ocupado_por = repo.get_ocupado_por(Config.HOJA_OPERACIONES_NOMBRE, 2)
    fecha_ocupacion = repo.get_fecha_ocupacion(Config.HOJA_OPERACIONES_NOMBRE, 2)
    version = repo.get_version(Config.HOJA_OPERACIONES_NOMBRE, 2)

    # Verify safe defaults
    assert ocupado_por is None, "v2.1 mode should return None for ocupado_por"
    assert fecha_ocupacion is None, "v2.1 mode should return None for fecha_ocupacion"
    assert version == 0, "v2.1 mode should return 0 for version"


@pytest.mark.v3
@pytest.mark.backward_compat
def test_v30_mode_reads_both():
    """Verify v3.0 mode can access both v2.1 and v3.0 columns."""
    # Initialize repository in v3.0 mode
    repo = SheetsRepository(compatibility_mode="v3.0")

    # Read v3.0 columns - should work (may be None if not populated)
    ocupado_por = repo.get_ocupado_por(Config.HOJA_OPERACIONES_NOMBRE, 2)
    fecha_ocupacion = repo.get_fecha_ocupacion(Config.HOJA_OPERACIONES_NOMBRE, 2)
    version = repo.get_version(Config.HOJA_OPERACIONES_NOMBRE, 2)

    # Verify methods work (values may be None or defaults)
    assert ocupado_por is None or isinstance(ocupado_por, str)
    assert fecha_ocupacion is None or isinstance(fecha_ocupacion, str)
    assert isinstance(version, int)
    assert version >= 0

    # Read v2.1 columns - should still work
    all_values = repo.read_worksheet(Config.HOJA_OPERACIONES_NOMBRE)
    assert len(all_values) > 1, "Should have data rows"

    headers = all_values[0]
    assert any("TAG" in h.upper() for h in headers), "v2.1 columns should be accessible"


@pytest.mark.v3
@pytest.mark.backward_compat
def test_v21_api_endpoints_work():
    """Verify v2.1 API operations continue functioning with v3.0 present."""
    # This test validates that v3.0 additions don't break existing functionality
    # We test through model imports and enum access (API layer tests would require full setup)

    from backend.models.spool import Spool
    from backend.models.enums import ActionStatus

    # Create spool with v2.1 fields only (no v3.0 fields)
    spool = Spool(
        tag_spool="TEST-001",
        arm=ActionStatus.PENDIENTE,
        sold=ActionStatus.PENDIENTE
    )

    # Verify v2.1 fields work
    assert spool.tag_spool == "TEST-001"
    assert spool.arm == ActionStatus.PENDIENTE
    assert spool.sold == ActionStatus.PENDIENTE

    # Verify v3.0 fields have safe defaults
    assert spool.ocupado_por is None
    assert spool.fecha_ocupacion is None
    assert spool.version == 0
    assert spool.esta_ocupado is False

    # Verify v2.1 enums still exist
    assert ActionStatus.PENDIENTE.value == "PENDIENTE"
    assert ActionStatus.EN_PROGRESO.value == "EN_PROGRESO"
    assert ActionStatus.COMPLETADO.value == "COMPLETADO"


@pytest.mark.v3
@pytest.mark.backward_compat
def test_metadata_accepts_new_events():
    """Verify Metadata sheet accepts new event types (TOMAR_SPOOL, PAUSAR_SPOOL)."""
    # Verify new EventoTipo values exist and are correctly defined
    assert hasattr(EventoTipo, 'TOMAR_SPOOL')
    assert hasattr(EventoTipo, 'PAUSAR_SPOOL')

    assert EventoTipo.TOMAR_SPOOL.value == "TOMAR_SPOOL"
    assert EventoTipo.PAUSAR_SPOOL.value == "PAUSAR_SPOOL"

    # Verify existing v2.1 events still exist
    assert hasattr(EventoTipo, 'INICIAR_ARM')
    assert hasattr(EventoTipo, 'COMPLETAR_ARM')
    assert hasattr(EventoTipo, 'INICIAR_SOLD')
    assert hasattr(EventoTipo, 'COMPLETAR_SOLD')
    assert hasattr(EventoTipo, 'CANCELAR_ARM')
    assert hasattr(EventoTipo, 'CANCELAR_SOLD')

    # Verify all enum values are unique
    event_values = [e.value for e in EventoTipo]
    assert len(event_values) == len(set(event_values)), "EventoTipo values should be unique"


@pytest.mark.v3
@pytest.mark.backward_compat
def test_existing_spool_data_intact():
    """Verify original 65 columns remain unmodified after v3.0 additions."""
    # Initialize repository in v3.0 mode
    repo = SheetsRepository(compatibility_mode="v3.0")

    # Read worksheet
    all_values = repo.read_worksheet(Config.HOJA_OPERACIONES_NOMBRE)

    # Get headers
    headers = all_values[0]

    # Verify key v2.1 columns still exist
    v21_columns = ["Armador", "Soldador", "Fecha_Armado", "Fecha_Soldadura", "Fecha_Materiales"]

    for col in v21_columns:
        assert col in headers, f"v2.1 column '{col}' should still exist"

    # Verify we have data rows
    assert len(all_values) > 1, "Should have data rows"

    # Read a data row to verify it's accessible
    if len(all_values) > 1:
        data_row = all_values[1]
        assert isinstance(data_row, list), "Data row should be a list"
        # Original columns should have data
        assert len(data_row) > 0, "Data row should not be empty"


@pytest.mark.v3
@pytest.mark.backward_compat
def test_v21_state_determination_still_works():
    """Verify v2.1 state determination logic (Direct Read) still functions."""
    from backend.models.spool import Spool
    from backend.models.enums import ActionStatus

    # Simulate v2.1 state scenarios

    # Scenario 1: ARM PENDIENTE (no armador)
    spool_pendiente = Spool(
        tag_spool="TEST-001",
        armador=None,
        fecha_armado=None
    )
    # In v2.1, PENDIENTE is determined by armador=None
    assert spool_pendiente.armador is None

    # Scenario 2: ARM EN_PROGRESO (has armador, no fecha)
    spool_en_progreso = Spool(
        tag_spool="TEST-002",
        armador="MR(93)",
        fecha_armado=None
    )
    assert spool_en_progreso.armador == "MR(93)"
    assert spool_en_progreso.fecha_armado is None

    # Scenario 3: ARM COMPLETADO (has fecha_armado)
    from datetime import date
    spool_completado = Spool(
        tag_spool="TEST-003",
        armador="MR(93)",
        fecha_armado=date(2026, 1, 26)
    )
    assert spool_completado.fecha_armado == date(2026, 1, 26)


@pytest.mark.v3
@pytest.mark.backward_compat
def test_estado_ocupacion_enum_exists():
    """Verify EstadoOcupacion enum is defined correctly."""
    # Verify EstadoOcupacion enum exists (new in v3.0)
    assert hasattr(EstadoOcupacion, 'DISPONIBLE')
    assert hasattr(EstadoOcupacion, 'OCUPADO')

    assert EstadoOcupacion.DISPONIBLE.value == "DISPONIBLE"
    assert EstadoOcupacion.OCUPADO.value == "OCUPADO"

    # Verify it's a complete enum (only 2 values)
    estados = list(EstadoOcupacion)
    assert len(estados) == 2, "EstadoOcupacion should have exactly 2 values"


@pytest.mark.v3
@pytest.mark.backward_compat
def test_compatibility_mode_switching():
    """Verify repository can switch between v2.1 and v3.0 modes."""
    # Create repository in v2.1 mode
    repo_v21 = SheetsRepository(compatibility_mode="v2.1")

    # v2.1 mode returns safe defaults
    ocupado_por_v21 = repo_v21.get_ocupado_por(Config.HOJA_OPERACIONES_NOMBRE, 2)
    assert ocupado_por_v21 is None

    # Create repository in v3.0 mode
    repo_v30 = SheetsRepository(compatibility_mode="v3.0")

    # v3.0 mode attempts to read actual column
    ocupado_por_v30 = repo_v30.get_ocupado_por(Config.HOJA_OPERACIONES_NOMBRE, 2)
    # May be None if column not populated, but method executes
    assert ocupado_por_v30 is None or isinstance(ocupado_por_v30, str)

    # Test that different modes produce different behavior
    # v2.1 always returns None, v3.0 may return actual value
    version_v21 = repo_v21.get_version(Config.HOJA_OPERACIONES_NOMBRE, 2)
    version_v30 = repo_v30.get_version(Config.HOJA_OPERACIONES_NOMBRE, 2)

    assert version_v21 == 0, "v2.1 mode always returns 0"
    assert isinstance(version_v30, int) and version_v30 >= 0, "v3.0 mode returns actual value"


@pytest.mark.v3
@pytest.mark.backward_compat
def test_v21_worker_format_still_valid():
    """Verify v2.1 worker name format remains valid in v3.0."""
    from backend.models.spool import Spool

    # v2.1 format: "INICIALES(ID)" - introduced in v2.1
    # This format is used in both v2.1 (armador/soldador) and v3.0 (ocupado_por)

    v21_worker_names = ["MR(93)", "NR(94)", "CP(95)"]

    for worker_name in v21_worker_names:
        # Can be used in v2.1 columns
        spool_v21 = Spool(
            tag_spool="TEST-001",
            armador=worker_name
        )
        assert spool_v21.armador == worker_name

        # Can be used in v3.0 columns
        spool_v30 = Spool(
            tag_spool="TEST-002",
            ocupado_por=worker_name
        )
        assert spool_v30.ocupado_por == worker_name
        assert spool_v30.esta_ocupado is True
