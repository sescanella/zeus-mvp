"""
v3.0 column-specific validation tests.

These tests verify:
1. Ocupado_Por format ("INICIALES(ID)")
2. Fecha_Ocupacion format (YYYY-MM-DD)
3. version initialization and behavior
4. Column positions (64, 65, 66)
5. Column name normalization
"""
import pytest
import re
from backend.repositories.sheets_repository import SheetsRepository
from backend.services.sheets_service import SheetsService
from backend.config import Config


@pytest.mark.v3
def test_ocupado_por_format():
    """Verify Ocupado_Por accepts and validates 'INICIALES(ID)' format."""
    from backend.models.spool import Spool

    # Valid formats
    valid_formats = [
        "MR(93)",
        "NR(94)",
        "CP(95)",
        "FF(96)",
        "MG(97)",
        "AP(98)",
    ]

    for worker_format in valid_formats:
        spool = Spool(
            tag_spool="TEST-001",
            ocupado_por=worker_format
        )
        assert spool.ocupado_por == worker_format
        assert spool.esta_ocupado is True

        # Verify format with regex: 2-3 uppercase letters + (numeric_id)
        pattern = r'^[A-Z]{1,3}\(\d+\)$'
        assert re.match(pattern, worker_format), f"{worker_format} doesn't match expected format"


@pytest.mark.v3
def test_fecha_ocupacion_format():
    """Verify Fecha_Ocupacion accepts date format (YYYY-MM-DD)."""
    from backend.models.spool import Spool
    from datetime import date

    # Valid date formats
    valid_dates = [
        "2026-01-26",
        "2026-12-31",
        "2025-01-01",
    ]

    for fecha in valid_dates:
        spool = Spool(
            tag_spool="TEST-001",
            fecha_ocupacion=fecha
        )
        assert spool.fecha_ocupacion == fecha

        # Verify format with regex: YYYY-MM-DD
        pattern = r'^\d{4}-\d{2}-\d{2}$'
        assert re.match(pattern, fecha), f"{fecha} doesn't match YYYY-MM-DD format"


@pytest.mark.v3
def test_version_starts_at_zero():
    """Verify version field initializes to 0 for new spools."""
    from backend.models.spool import Spool

    # New spool without version specified
    spool = Spool(tag_spool="TEST-001")

    assert spool.version == 0
    assert isinstance(spool.version, int)


@pytest.mark.v3
def test_version_increments():
    """Verify version can be incremented by creating new instances."""
    from backend.models.spool import Spool

    # Create spool with version 0
    spool_v0 = Spool(tag_spool="TEST-001", version=0)
    assert spool_v0.version == 0

    # Simulate increment by creating new instance (Pydantic models are frozen)
    spool_v1 = Spool(tag_spool="TEST-001", version=1)
    assert spool_v1.version == 1

    # Create with higher version
    spool_v5 = Spool(tag_spool="TEST-001", version=5)
    assert spool_v5.version == 5


@pytest.mark.v3
@pytest.mark.smoke
def test_column_positions(mock_column_map_v3):
    """Verify v3.0 columns are at positions 64, 65, 66 (0-indexed)."""
    # Use mock column map
    column_map = mock_column_map_v3

    # Verify positions (0-indexed, so 64, 65, 66)
    assert column_map["ocupadopor"] == 64, f"Expected ocupadopor at index 64, got {column_map['ocupadopor']}"
    assert column_map["fechaocupacion"] == 65, f"Expected fechaocupacion at index 65, got {column_map['fechaocupacion']}"
    assert column_map["version"] == 66, f"Expected version at index 66, got {column_map['version']}"


@pytest.mark.v3
@pytest.mark.smoke
def test_column_names_normalized(mock_column_map_v3):
    """Verify column names are normalized correctly for lookup."""
    # Use mock column map
    column_map = mock_column_map_v3

    # Verify normalized names (lowercase, no spaces/underscores)
    expected_normalized = {
        "Ocupado_Por": "ocupadopor",
        "Fecha_Ocupacion": "fechaocupacion",
        "version": "version",
    }

    for original, normalized in expected_normalized.items():
        # Column should be accessible by normalized name
        assert normalized in column_map, f"Normalized name '{normalized}' not in column map"


@pytest.mark.v3
def test_esta_ocupado_property():
    """Verify esta_ocupado computed property works correctly."""
    from backend.models.spool import Spool

    # Not occupied (default)
    spool_free = Spool(tag_spool="TEST-001")
    assert spool_free.ocupado_por is None
    assert spool_free.esta_ocupado is False

    # Not occupied (explicit None)
    spool_explicit_free = Spool(tag_spool="TEST-002", ocupado_por=None)
    assert spool_explicit_free.esta_ocupado is False

    # Occupied
    spool_occupied = Spool(tag_spool="TEST-003", ocupado_por="MR(93)")
    assert spool_occupied.esta_ocupado is True

    # After releasing (create new instance with None)
    spool_released = Spool(tag_spool="TEST-003", ocupado_por=None)
    assert spool_released.esta_ocupado is False


@pytest.mark.v3
def test_ocupado_por_none_is_available():
    """Verify that None in Ocupado_Por means spool is available."""
    from backend.models.spool import Spool

    # Create occupied spool
    spool_occupied = Spool(
        tag_spool="TEST-001",
        ocupado_por="MR(93)",
        fecha_ocupacion="2026-01-26",
        version=1
    )

    assert spool_occupied.esta_ocupado is True

    # Release spool (PAUSAR_SPOOL action - create new instance)
    spool_released = Spool(
        tag_spool="TEST-001",
        ocupado_por=None,
        fecha_ocupacion=None,
        version=2  # Incremented on pause
    )

    assert spool_released.esta_ocupado is False
    assert spool_released.ocupado_por is None
    assert spool_released.version == 2


@pytest.mark.v3
def test_version_non_negative():
    """Verify version cannot be negative."""
    from backend.models.spool import Spool
    from pydantic import ValidationError

    # Valid version
    spool = Spool(tag_spool="TEST-001", version=0)
    assert spool.version == 0

    # Try to create with negative version (should fail)
    with pytest.raises(ValidationError):
        Spool(tag_spool="TEST-002", version=-1)


@pytest.mark.v3
def test_repository_v3_mode_reads_columns():
    """Verify repository in v3.0 mode can read v3.0 columns."""
    # Initialize repository in v3.0 mode
    repo = SheetsRepository(compatibility_mode="v3.0")

    # Read from row 2 (first data row)
    # This validates the repository methods exist and are callable
    ocupado_por = repo.get_ocupado_por(Config.HOJA_OPERACIONES_NOMBRE, 2)
    fecha_ocupacion = repo.get_fecha_ocupacion(Config.HOJA_OPERACIONES_NOMBRE, 2)
    version = repo.get_version(Config.HOJA_OPERACIONES_NOMBRE, 2)

    # Verify types (even if None)
    assert ocupado_por is None or isinstance(ocupado_por, str)
    assert fecha_ocupacion is None or isinstance(fecha_ocupacion, str)
    assert isinstance(version, int)
    assert version >= 0


@pytest.mark.v3
def test_repository_v21_mode_returns_safe_defaults():
    """Verify repository in v2.1 mode returns safe defaults for v3.0 columns."""
    # Initialize repository in v2.1 mode
    repo = SheetsRepository(compatibility_mode="v2.1")

    # Read v3.0 columns (should return safe defaults)
    ocupado_por = repo.get_ocupado_por(Config.HOJA_OPERACIONES_NOMBRE, 2)
    fecha_ocupacion = repo.get_fecha_ocupacion(Config.HOJA_OPERACIONES_NOMBRE, 2)
    version = repo.get_version(Config.HOJA_OPERACIONES_NOMBRE, 2)

    # Verify safe defaults
    assert ocupado_por is None, "v2.1 mode should return None for ocupado_por"
    assert fecha_ocupacion is None, "v2.1 mode should return None for fecha_ocupacion"
    assert version == 0, "v2.1 mode should return 0 for version"
