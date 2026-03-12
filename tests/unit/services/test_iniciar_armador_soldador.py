"""
Unit tests for INICIAR writing Armador/Soldador columns.

Validates that when a worker starts (INICIAR) an operation:
- ARM operation writes worker_nombre to "Armador" column
- SOLD operation writes worker_nombre to "Soldador" column
- ARM does NOT write Soldador
- SOLD does NOT write Armador
"""
import pytest
from unittest.mock import MagicMock, patch
from datetime import date

from backend.services.occupation_service import OccupationService
from backend.models.occupation import IniciarRequest
from backend.models.spool import Spool
from backend.models.enums import ActionType


# ============================================================================
# FIXTURES
# ============================================================================

@pytest.fixture
def mock_sheets_repository():
    """Mock SheetsRepository."""
    repo = MagicMock()

    mock_spool = MagicMock(spec=Spool)
    mock_spool.tag_spool = "SPOOL-001"
    mock_spool.ot = "100"
    mock_spool.total_uniones = 10
    mock_spool.uniones_arm_completadas = 0
    mock_spool.uniones_sold_completadas = 0
    mock_spool.pulgadas_arm = 0.0
    mock_spool.pulgadas_sold = 0.0
    mock_spool.ocupado_por = None
    mock_spool.fecha_ocupacion = None
    mock_spool.version = "uuid-1"
    mock_spool.estado_detalle = None
    mock_spool.fecha_materiales = date(2026, 1, 20)
    mock_spool.armador = None
    mock_spool.soldador = None
    mock_spool.fecha_armado = None
    mock_spool.fecha_soldadura = None

    repo.get_spool_by_tag = MagicMock(return_value=mock_spool)
    repo.batch_update_by_column_name = MagicMock()

    mock_headers = [
        "TAG_SPOOL", "OT", "NV", "Fecha_Materiales", "Fecha_Armado", "Armador",
        "Fecha_Soldadura", "Soldador", "Ocupado_Por", "Fecha_Ocupacion",
        "version", "Estado_Detalle", "Total_Uniones", "Uniones_ARM_Completadas",
        "Pulgadas_ARM", "Uniones_SOLD_Completadas", "Pulgadas_SOLD"
    ]
    repo.read_worksheet = MagicMock(return_value=[mock_headers])

    return repo


@pytest.fixture
def mock_metadata_repository():
    """Mock MetadataRepository."""
    repo = MagicMock()
    repo.log_event = MagicMock()
    return repo


@pytest.fixture
def mock_union_repository():
    """Mock UnionRepository."""
    repo = MagicMock()
    repo.get_disponibles_arm_by_ot = MagicMock(return_value=[])
    repo.get_disponibles_sold_by_ot = MagicMock(return_value=[])
    return repo


@pytest.fixture
def mock_conflict_service():
    """Mock ConflictService."""
    service = MagicMock()
    service.generate_version_token = MagicMock(return_value="version-uuid")
    return service


@pytest.fixture
def occupation_service(
    mock_sheets_repository,
    mock_metadata_repository,
    mock_union_repository,
    mock_conflict_service
):
    """Create OccupationService for testing."""
    service = OccupationService(
        sheets_repository=mock_sheets_repository,
        metadata_repository=mock_metadata_repository,
        union_repository=mock_union_repository,
        conflict_service=mock_conflict_service
    )
    service.validation_service = MagicMock()
    return service


def _extract_updates_dict(mock_sheets_repository) -> dict:
    """Extract the column_name -> value dict from batch_update_by_column_name call."""
    call_kwargs = mock_sheets_repository.batch_update_by_column_name.call_args.kwargs
    batch_updates = call_kwargs["updates"]
    return {u["column_name"]: u["value"] for u in batch_updates}


# ============================================================================
# TESTS
# ============================================================================

@pytest.mark.asyncio
async def test_iniciar_arm_writes_armador(
    occupation_service,
    mock_sheets_repository
):
    """INICIAR ARM writes Armador column with worker_nombre."""
    request = IniciarRequest(
        tag_spool="SPOOL-001",
        worker_id=93,
        worker_nombre="MR(93)",
        operacion=ActionType.ARM
    )

    with patch('backend.services.estado_detalle_builder.EstadoDetalleBuilder') as mock_builder_class:
        mock_builder = MagicMock()
        mock_builder.build.return_value = "MR(93) trabajando ARM"
        mock_builder_class.return_value = mock_builder

        await occupation_service.iniciar_spool(request)

    updates = _extract_updates_dict(mock_sheets_repository)
    assert updates["Armador"] == "MR(93)"


@pytest.mark.asyncio
async def test_iniciar_sold_writes_soldador(
    occupation_service,
    mock_sheets_repository
):
    """INICIAR SOLD writes Soldador column with worker_nombre."""
    # Set ARM as completed so SOLD prereqs are met
    spool = mock_sheets_repository.get_spool_by_tag("SPOOL-001")
    spool.uniones_arm_completadas = 5

    request = IniciarRequest(
        tag_spool="SPOOL-001",
        worker_id=50,
        worker_nombre="JL(50)",
        operacion=ActionType.SOLD
    )

    with patch('backend.services.estado_detalle_builder.EstadoDetalleBuilder') as mock_builder_class:
        mock_builder = MagicMock()
        mock_builder.build.return_value = "JL(50) trabajando SOLD"
        mock_builder_class.return_value = mock_builder

        await occupation_service.iniciar_spool(request)

    updates = _extract_updates_dict(mock_sheets_repository)
    assert updates["Soldador"] == "JL(50)"


@pytest.mark.asyncio
async def test_iniciar_arm_does_not_write_soldador(
    occupation_service,
    mock_sheets_repository
):
    """INICIAR ARM does NOT write Soldador column."""
    request = IniciarRequest(
        tag_spool="SPOOL-001",
        worker_id=93,
        worker_nombre="MR(93)",
        operacion=ActionType.ARM
    )

    with patch('backend.services.estado_detalle_builder.EstadoDetalleBuilder') as mock_builder_class:
        mock_builder = MagicMock()
        mock_builder.build.return_value = "MR(93) trabajando ARM"
        mock_builder_class.return_value = mock_builder

        await occupation_service.iniciar_spool(request)

    updates = _extract_updates_dict(mock_sheets_repository)
    assert "Soldador" not in updates


@pytest.mark.asyncio
async def test_iniciar_sold_does_not_write_armador(
    occupation_service,
    mock_sheets_repository
):
    """INICIAR SOLD does NOT write Armador column."""
    spool = mock_sheets_repository.get_spool_by_tag("SPOOL-001")
    spool.uniones_arm_completadas = 5

    request = IniciarRequest(
        tag_spool="SPOOL-001",
        worker_id=50,
        worker_nombre="JL(50)",
        operacion=ActionType.SOLD
    )

    with patch('backend.services.estado_detalle_builder.EstadoDetalleBuilder') as mock_builder_class:
        mock_builder = MagicMock()
        mock_builder.build.return_value = "JL(50) trabajando SOLD"
        mock_builder_class.return_value = mock_builder

        await occupation_service.iniciar_spool(request)

    updates = _extract_updates_dict(mock_sheets_repository)
    assert "Armador" not in updates
