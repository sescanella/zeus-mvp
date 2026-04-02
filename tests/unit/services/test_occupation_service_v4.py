"""
Unit tests for OccupationService v4.0 operations (INICIAR/FINALIZAR).

Tests validate:
- INICIAR writes occupation fields to Sheets (no Redis locks)
- FINALIZAR auto-determines PAUSAR vs COMPLETAR
- Zero-union cancellation clears occupation without updates
- Race condition handling (union becomes unavailable)
- Ownership validation via Ocupado_Por column (single-user mode)

Reference:
- Service: backend/services/occupation_service.py
"""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime

from backend.services.occupation_service import OccupationService
from backend.models.occupation import (
    IniciarRequest,
    FinalizarRequest
)
from backend.models.spool import Spool
from backend.models.union import Union
from backend.models.enums import ActionType
from backend.exceptions import (
    SpoolNoEncontradoError,
    SpoolOccupiedError,
    DependenciasNoSatisfechasError,
    NoAutorizadoError,
    LockExpiredError,
    RaceConditionError
)


@pytest.fixture
def mock_sheets_repository():
    """Mock SheetsRepository."""
    repo = MagicMock()

    # Create mock spool using MagicMock to allow ot attribute
    mock_spool = MagicMock(spec=Spool)
    mock_spool.tag_spool = "OT-123"
    mock_spool.ot = "123"  # v4.0 field (not yet in Spool model)
    mock_spool.total_uniones = 10  # v4.0 spool (has unions)
    mock_spool.fecha_materiales = "2026-01-20"
    mock_spool.fecha_ocupacion = "04-02-2026 10:00:00"  # When spool was taken
    mock_spool.ocupado_por = None  # Not occupied by default
    mock_spool.armador = None
    mock_spool.soldador = None
    mock_spool.fecha_armado = None
    mock_spool.fecha_soldadura = None

    repo.get_spool_by_tag = MagicMock(return_value=mock_spool)

    # Mock methods needed by iniciar_spool's Sheets write path
    repo.batch_update_by_column_name = MagicMock()
    repo._index_to_column_letter = MagicMock(return_value="G")
    repo.find_row_by_column_value = MagicMock(return_value=5)

    # Mock read_worksheet to return headers (needed for ColumnMapCache)
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
def mock_conflict_service():
    """Mock ConflictService."""
    service = MagicMock()
    service.generate_version_token = MagicMock(return_value="version-uuid")
    service.update_with_retry = AsyncMock(return_value="new-version-uuid")
    return service


@pytest.fixture
def mock_union_repository():
    """Mock UnionRepository."""
    repo = MagicMock()

    # Create mock unions for testing
    # tipo_union in SOLD_REQUIRED_TYPES ('BW','BR','SO','FILL','LET') for SOLD filtering
    def create_union(n_union: int, arm_complete: bool = False, sold_complete: bool = False, tipo_union: str = "Tipo A"):
        return Union(
            id=f"OT-123+{n_union}",
            ot="123",
            tag_spool="OT-123",
            n_union=n_union,
            dn_union=2.5,
            tipo_union=tipo_union,
            arm_fecha_inicio=None,
            arm_fecha_fin=datetime(2026, 1, 20) if arm_complete else None,
            arm_worker="MR(93)" if arm_complete else None,
            sol_fecha_inicio=None,
            sol_fecha_fin=datetime(2026, 1, 21) if sold_complete else None,
            sol_worker="MR(93)" if sold_complete else None,
            ndt_fecha=None,
            ndt_status=None,
            version="version-uuid",
        )

    # Default: 10 unions available for ARM
    repo.get_disponibles_arm_by_ot = MagicMock(return_value=[
        create_union(i) for i in range(1, 11)
    ])

    # Default: 5 unions available for SOLD (ARM complete + tipo in SOLD_REQUIRED_TYPES)
    repo.get_disponibles_sold_by_ot = MagicMock(return_value=[
        create_union(i, arm_complete=True, tipo_union="BW") for i in range(1, 6)
    ])

    repo.batch_update_arm = MagicMock(return_value=3)  # 3 unions updated
    repo.batch_update_sold = MagicMock(return_value=2)  # 2 unions updated

    # P5 batch methods (full timestamp support)
    repo.batch_update_arm_full = MagicMock(return_value=3)
    repo.batch_update_sold_full = MagicMock(return_value=2)

    # For pulgadas calculation
    repo.get_by_ids = MagicMock(return_value=[
        create_union(1), create_union(2), create_union(3)
    ])

    # v4.0 detection: return 10 unions (v4.0 spool)
    repo.get_total_uniones = MagicMock(return_value=10)

    # Metrics for v4.0 counters
    repo.calculate_metrics = MagicMock(return_value={
        "arm_completadas": 3,
        "sold_completadas": 0,
        "pulgadas_arm": 7.5,
        "pulgadas_sold": 0.0,
    })
    repo._find_spool_row = MagicMock(return_value=5)

    return repo


@pytest.fixture
def occupation_service_v4(
    mock_sheets_repository,
    mock_metadata_repository,
    mock_conflict_service,
    mock_union_repository
):
    """Create OccupationService with v4.0 dependencies (single-user mode: no Redis)."""
    return OccupationService(
        sheets_repository=mock_sheets_repository,
        metadata_repository=mock_metadata_repository,
        conflict_service=mock_conflict_service,
        union_repository=mock_union_repository
    )


# ============================================================================
# INICIAR Tests
# ============================================================================

@pytest.mark.asyncio
async def test_iniciar_spool_success(occupation_service_v4, mock_sheets_repository):
    """Test INICIAR successfully occupies spool via Sheets write (no Redis)."""
    request = IniciarRequest(
        tag_spool="OT-123",
        worker_id=93,
        worker_nombre="MR(93)",
        operacion=ActionType.ARM
    )

    with patch('backend.services.estado_detalle_builder.EstadoDetalleBuilder') as mock_builder_class:
        mock_builder = MagicMock()
        mock_builder.build.return_value = "MR(93) trabajando ARM"
        mock_builder_class.return_value = mock_builder

        response = await occupation_service_v4.iniciar_spool(request)

    assert response.success is True
    assert response.tag_spool == "OT-123"
    assert "iniciado" in response.message.lower()

    # Verify Sheets updated with occupation via batch_update_by_column_name
    mock_sheets_repository.batch_update_by_column_name.assert_called_once()


@pytest.mark.asyncio
async def test_iniciar_spool_missing_prerequisite(occupation_service_v4, mock_sheets_repository):
    """Test INICIAR fails if Fecha_Materiales is missing."""
    # Mock spool without Fecha_Materiales
    mock_sheets_repository.get_spool_by_tag.return_value = Spool(
        tag_spool="OT-123",
        ot="123",
        fecha_materiales=None,
        armador=None,
        soldador=None,
        fecha_armado=None,
        fecha_soldadura=None
    )

    request = IniciarRequest(
        tag_spool="OT-123",
        worker_id=93,
        worker_nombre="MR(93)",
        operacion=ActionType.ARM
    )

    with pytest.raises(DependenciasNoSatisfechasError) as exc_info:
        await occupation_service_v4.iniciar_spool(request)

    assert "Fecha_Materiales" in str(exc_info.value)


@pytest.mark.asyncio
async def test_iniciar_spool_already_occupied(occupation_service_v4, mock_sheets_repository):
    """
    Test INICIAR on already-occupied spool succeeds (LWW in single-user mode).

    In P5 Confirmation workflow, INICIAR does NOT validate if already occupied.
    It trusts P4 filters and accepts last-write-wins for any race condition.
    """
    # Mock spool already occupied by another worker
    mock_spool = mock_sheets_repository.get_spool_by_tag.return_value
    mock_spool.ocupado_por = "JP(94)"

    request = IniciarRequest(
        tag_spool="OT-123",
        worker_id=93,
        worker_nombre="MR(93)",
        operacion=ActionType.ARM
    )

    with patch('backend.services.estado_detalle_builder.EstadoDetalleBuilder') as mock_builder_class:
        mock_builder = MagicMock()
        mock_builder.build.return_value = "MR(93) trabajando ARM"
        mock_builder_class.return_value = mock_builder

        # In single-user/LWW mode, INICIAR succeeds even if spool is occupied
        response = await occupation_service_v4.iniciar_spool(request)

    assert response.success is True
    # Sheets write overwrites previous occupation (LWW)
    mock_sheets_repository.batch_update_by_column_name.assert_called_once()


# ============================================================================
# FINALIZAR Tests - PAUSAR outcome
# ============================================================================

@pytest.mark.asyncio
async def test_finalizar_spool_pausar(occupation_service_v4, mock_union_repository, mock_conflict_service):
    """Test FINALIZAR with partial selection results in PAUSAR."""
    # Select 3 out of 10 available unions
    request = FinalizarRequest(
        tag_spool="OT-123",
        worker_id=93,
        worker_nombre="MR(93)",
        operacion=ActionType.ARM,
        selected_unions=["OT-123+1", "OT-123+2", "OT-123+3"]
    )

    # Mock 10 available unions
    mock_union_repository.get_disponibles_arm_by_ot.return_value = [
        MagicMock() for _ in range(10)
    ]
    mock_union_repository.batch_update_arm_full.return_value = 3

    response = await occupation_service_v4.finalizar_spool(request)

    assert response.success is True
    assert response.action_taken == "PAUSAR"
    assert response.unions_processed == 3
    assert "pausado" in response.message.lower()

    # Verify batch update called
    mock_union_repository.batch_update_arm_full.assert_called_once()


# ============================================================================
# FINALIZAR Tests - COMPLETAR outcome
# ============================================================================

@pytest.mark.asyncio
async def test_finalizar_spool_completar(occupation_service_v4, mock_union_repository, mock_conflict_service):
    """Test FINALIZAR with full selection results in COMPLETAR."""
    # Select all 10 available unions
    request = FinalizarRequest(
        tag_spool="OT-123",
        worker_id=93,
        worker_nombre="MR(93)",
        operacion=ActionType.ARM,
        selected_unions=[f"OT-123+{i}" for i in range(1, 11)]
    )

    # Mock 10 available unions
    mock_union_repository.get_disponibles_arm_by_ot.return_value = [
        MagicMock() for _ in range(10)
    ]
    mock_union_repository.batch_update_arm_full.return_value = 10

    response = await occupation_service_v4.finalizar_spool(request)

    assert response.success is True
    assert response.action_taken == "COMPLETAR"
    assert response.unions_processed == 10
    assert "completada" in response.message.lower()

    # Verify batch update called with all unions
    mock_union_repository.batch_update_arm_full.assert_called_once()
    call_args = mock_union_repository.batch_update_arm_full.call_args
    assert len(call_args.kwargs["union_ids"]) == 10


# ============================================================================
# FINALIZAR Tests - Zero-union cancellation
# ============================================================================

@pytest.mark.asyncio
async def test_finalizar_spool_zero_union_cancellation(
    occupation_service_v4,
    mock_conflict_service,
    mock_union_repository
):
    """Test FINALIZAR with empty selection triggers cancellation."""
    request = FinalizarRequest(
        tag_spool="OT-123",
        worker_id=93,
        worker_nombre="MR(93)",
        operacion=ActionType.ARM,
        selected_unions=[]  # Empty list = cancellation
    )

    response = await occupation_service_v4.finalizar_spool(request)

    assert response.success is True
    assert response.action_taken == "CANCELADO"
    assert response.unions_processed == 0
    assert "cancelado" in response.message.lower()

    # Verify occupation cleared via conflict_service.update_with_retry
    mock_conflict_service.update_with_retry.assert_called_once()
    call_args = mock_conflict_service.update_with_retry.call_args
    assert call_args.kwargs["updates"]["Ocupado_Por"] == ""

    # Verify NO batch update to Uniones
    mock_union_repository.batch_update_arm_full.assert_not_called()


# ============================================================================
# FINALIZAR Tests - Race condition
# ============================================================================

@pytest.mark.asyncio
async def test_finalizar_spool_race_condition(occupation_service_v4, mock_union_repository):
    """Test FINALIZAR fails if selected > available (race condition)."""
    # Select 15 unions but only 10 available
    request = FinalizarRequest(
        tag_spool="OT-123",
        worker_id=93,
        worker_nombre="MR(93)",
        operacion=ActionType.ARM,
        selected_unions=[f"OT-123+{i}" for i in range(1, 16)]  # 15 unions
    )

    # Mock only 10 available unions
    mock_union_repository.get_disponibles_arm_by_ot.return_value = [
        MagicMock() for _ in range(10)
    ]

    with pytest.raises(RaceConditionError):
        await occupation_service_v4.finalizar_spool(request)


# ============================================================================
# FINALIZAR Tests - Ownership validation
# ============================================================================

@pytest.mark.asyncio
async def test_finalizar_spool_not_owner(occupation_service_v4, mock_sheets_repository):
    """
    Test FINALIZAR succeeds even with different owner (trust P4 filters).

    In P5 Confirmation workflow, FINALIZAR does NOT verify lock ownership.
    It trusts that P4 filters already ensured only the owner can reach P5.
    """
    # Mock spool occupied by a different worker
    mock_spool = mock_sheets_repository.get_spool_by_tag.return_value
    mock_spool.ocupado_por = "JP(94)"

    request = FinalizarRequest(
        tag_spool="OT-123",
        worker_id=93,  # Different from owner
        worker_nombre="MR(93)",
        operacion=ActionType.ARM,
        selected_unions=["OT-123+1"]
    )

    # In single-user mode with P5 workflow, ownership is NOT validated
    # The service trusts P4 filters (only spools owned by the worker appear)
    response = await occupation_service_v4.finalizar_spool(request)
    assert response.success is True


@pytest.mark.asyncio
async def test_finalizar_spool_no_occupation(occupation_service_v4, mock_sheets_repository):
    """
    Test FINALIZAR succeeds even when spool has no occupation (trust P4 filters).

    In P5 Confirmation workflow, FINALIZAR does NOT check if occupation exists.
    The spool appearing in P4 list is sufficient proof of occupation.
    """
    # Mock spool with no occupation
    mock_spool = mock_sheets_repository.get_spool_by_tag.return_value
    mock_spool.ocupado_por = None
    mock_spool.fecha_ocupacion = None

    request = FinalizarRequest(
        tag_spool="OT-123",
        worker_id=93,
        worker_nombre="MR(93)",
        operacion=ActionType.ARM,
        selected_unions=["OT-123+1"]
    )

    # In single-user mode, service trusts P4 filters and proceeds
    response = await occupation_service_v4.finalizar_spool(request)
    assert response.success is True


# ============================================================================
# Auto-determination helper tests
# ============================================================================

def test_determine_action_pausar(occupation_service_v4):
    """Test _determine_action returns PAUSAR for partial work."""
    result = occupation_service_v4._determine_action(
        selected_count=3,
        total_available=10,
        operacion="ARM"
    )
    assert result == "PAUSAR"


def test_determine_action_completar(occupation_service_v4):
    """Test _determine_action returns COMPLETAR for full work."""
    result = occupation_service_v4._determine_action(
        selected_count=10,
        total_available=10,
        operacion="ARM"
    )
    assert result == "COMPLETAR"


def test_determine_action_race_condition(occupation_service_v4):
    """Test _determine_action raises RaceConditionError for race condition."""
    with pytest.raises(RaceConditionError):
        occupation_service_v4._determine_action(
            selected_count=15,
            total_available=10,
            operacion="ARM"
        )


# ============================================================================
# SOLD operation tests
# ============================================================================

@pytest.mark.asyncio
async def test_finalizar_sold_operation(occupation_service_v4, mock_union_repository):
    """Test FINALIZAR works with SOLD operation."""
    request = FinalizarRequest(
        tag_spool="OT-123",
        worker_id=93,
        worker_nombre="MR(93)",
        operacion=ActionType.SOLD,
        selected_unions=["OT-123+1", "OT-123+2"]
    )

    # Mock 5 available SOLD unions (tipo_union must be in SOLD_REQUIRED_TYPES for filter)
    mock_union_repository.get_disponibles_sold_by_ot.return_value = [
        MagicMock(tipo_union="BW") for _ in range(5)
    ]
    mock_union_repository.batch_update_sold_full.return_value = 2
    mock_union_repository.get_by_ids.return_value = [
        MagicMock(dn_union=4.0),
        MagicMock(dn_union=6.0)
    ]

    response = await occupation_service_v4.finalizar_spool(request)

    assert response.success is True
    assert response.action_taken == "PAUSAR"  # 2 of 5
    assert response.unions_processed == 2

    # Verify SOLD batch update called (not ARM)
    mock_union_repository.batch_update_sold_full.assert_called_once()
    mock_union_repository.batch_update_arm_full.assert_not_called()
