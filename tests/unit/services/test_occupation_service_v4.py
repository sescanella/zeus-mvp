"""
Unit tests for OccupationService v4.0 operations (INICIAR/FINALIZAR).

Tests validate:
- INICIAR acquires persistent lock without touching Uniones
- FINALIZAR auto-determines PAUSAR vs COMPLETAR
- Zero-union cancellation releases lock without updates
- Race condition handling (union becomes unavailable)
- UnionRepository integration for batch updates

Reference:
- Service: backend/services/occupation_service.py
- Plan: 10-02-PLAN.md
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
    LockExpiredError
)


@pytest.fixture
def mock_redis_lock_service():
    """Mock RedisLockService for persistent locks."""
    service = AsyncMock()
    service.acquire_lock = AsyncMock(return_value="93:test-token-uuid")
    service.release_lock = AsyncMock(return_value=True)
    service.get_lock_owner = AsyncMock(return_value=(93, "test-token-uuid"))
    service.lazy_cleanup_one_abandoned_lock = AsyncMock()
    return service


@pytest.fixture
def mock_sheets_repository():
    """Mock SheetsRepository."""
    repo = MagicMock()

    # Create mock spool using MagicMock to allow ot attribute
    mock_spool = MagicMock(spec=Spool)
    mock_spool.tag_spool = "OT-123"
    mock_spool.ot = "123"  # v4.0 field (not yet in Spool model)
    mock_spool.fecha_materiales = "2026-01-20"
    mock_spool.armador = None
    mock_spool.soldador = None
    mock_spool.fecha_armado = None
    mock_spool.fecha_soldadura = None

    repo.get_spool_by_tag = MagicMock(return_value=mock_spool)
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
def mock_redis_event_service():
    """Mock RedisEventService."""
    service = AsyncMock()
    service.publish_spool_update = AsyncMock()
    return service


@pytest.fixture
def mock_union_repository():
    """Mock UnionRepository."""
    repo = MagicMock()

    # Create mock unions for testing
    def create_union(n_union: int, arm_complete: bool = False, sold_complete: bool = False):
        return Union(
            id=f"OT-123+{n_union}",
            ot="123",
            tag_spool="OT-123",
            n_union=n_union,
            dn_union=2.5,
            tipo_union="Tipo A",
            arm_fecha_inicio=None,
            arm_fecha_fin=datetime(2026, 1, 20) if arm_complete else None,
            arm_worker="MR(93)" if arm_complete else None,
            sol_fecha_inicio=None,
            sol_fecha_fin=datetime(2026, 1, 21) if sold_complete else None,
            sol_worker="MR(93)" if sold_complete else None,
            ndt_fecha=None,
            ndt_status=None,
            version="version-uuid",
            creado_por="SYSTEM(0)",
            fecha_creacion=datetime(2026, 1, 1)
        )

    # Default: 10 unions available for ARM
    repo.get_disponibles_arm_by_ot = MagicMock(return_value=[
        create_union(i) for i in range(1, 11)
    ])

    # Default: 5 unions available for SOLD (ARM already complete)
    repo.get_disponibles_sold_by_ot = MagicMock(return_value=[
        create_union(i, arm_complete=True) for i in range(1, 6)
    ])

    repo.batch_update_arm = MagicMock(return_value=3)  # 3 unions updated
    repo.batch_update_sold = MagicMock(return_value=2)  # 2 unions updated

    return repo


@pytest.fixture
def occupation_service_v4(
    mock_redis_lock_service,
    mock_sheets_repository,
    mock_metadata_repository,
    mock_conflict_service,
    mock_redis_event_service,
    mock_union_repository
):
    """Create OccupationService with v4.0 dependencies."""
    return OccupationService(
        redis_lock_service=mock_redis_lock_service,
        sheets_repository=mock_sheets_repository,
        metadata_repository=mock_metadata_repository,
        conflict_service=mock_conflict_service,
        redis_event_service=mock_redis_event_service,
        union_repository=mock_union_repository
    )


# ============================================================================
# INICIAR Tests
# ============================================================================

@pytest.mark.asyncio
async def test_iniciar_spool_success(occupation_service_v4, mock_redis_lock_service, mock_conflict_service):
    """Test INICIAR successfully occupies spool without touching Uniones."""
    request = IniciarRequest(
        tag_spool="OT-123",
        worker_id=93,
        worker_nombre="MR(93)",
        operacion=ActionType.ARM
    )

    response = await occupation_service_v4.iniciar_spool(request)

    assert response.success is True
    assert response.tag_spool == "OT-123"
    assert "iniciado por MR(93)" in response.message

    # Verify Redis lock acquired
    mock_redis_lock_service.acquire_lock.assert_called_once_with(
        tag_spool="OT-123",
        worker_id=93,
        worker_nombre="MR(93)"
    )

    # Verify Sheets updated with occupation
    mock_conflict_service.update_with_retry.assert_called_once()
    call_args = mock_conflict_service.update_with_retry.call_args
    assert call_args.kwargs["tag_spool"] == "OT-123"
    assert call_args.kwargs["updates"]["Ocupado_Por"] == "MR(93)"
    assert "Fecha_Ocupacion" in call_args.kwargs["updates"]


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
async def test_iniciar_spool_already_occupied(occupation_service_v4, mock_redis_lock_service):
    """Test INICIAR fails if spool already occupied."""
    mock_redis_lock_service.acquire_lock.side_effect = SpoolOccupiedError(
        tag_spool="OT-123",
        owner_id=94,
        owner_name="JP(94)"
    )

    request = IniciarRequest(
        tag_spool="OT-123",
        worker_id=93,
        worker_nombre="MR(93)",
        operacion=ActionType.ARM
    )

    with pytest.raises(SpoolOccupiedError):
        await occupation_service_v4.iniciar_spool(request)


# ============================================================================
# FINALIZAR Tests - PAUSAR outcome
# ============================================================================

@pytest.mark.asyncio
async def test_finalizar_spool_pausar(occupation_service_v4, mock_union_repository, mock_redis_lock_service):
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
    mock_union_repository.batch_update_arm.return_value = 3

    response = await occupation_service_v4.finalizar_spool(request)

    assert response.success is True
    assert response.action_taken == "PAUSAR"
    assert response.unions_processed == 3
    assert "pausado" in response.message.lower()

    # Verify batch update called
    mock_union_repository.batch_update_arm.assert_called_once()

    # Verify lock released
    mock_redis_lock_service.release_lock.assert_called_once()


# ============================================================================
# FINALIZAR Tests - COMPLETAR outcome
# ============================================================================

@pytest.mark.asyncio
async def test_finalizar_spool_completar(occupation_service_v4, mock_union_repository, mock_redis_lock_service):
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
    mock_union_repository.batch_update_arm.return_value = 10

    response = await occupation_service_v4.finalizar_spool(request)

    assert response.success is True
    assert response.action_taken == "COMPLETAR"
    assert response.unions_processed == 10
    assert "completada" in response.message.lower()

    # Verify batch update called with all unions
    mock_union_repository.batch_update_arm.assert_called_once()
    call_args = mock_union_repository.batch_update_arm.call_args
    assert len(call_args.kwargs["union_ids"]) == 10


# ============================================================================
# FINALIZAR Tests - Zero-union cancellation
# ============================================================================

@pytest.mark.asyncio
async def test_finalizar_spool_zero_union_cancellation(
    occupation_service_v4,
    mock_redis_lock_service,
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

    # Verify lock released
    mock_redis_lock_service.release_lock.assert_called_once()

    # Verify occupation cleared
    mock_conflict_service.update_with_retry.assert_called_once()
    call_args = mock_conflict_service.update_with_retry.call_args
    assert call_args.kwargs["updates"]["Ocupado_Por"] == ""

    # Verify NO batch update to Uniones
    mock_union_repository.batch_update_arm.assert_not_called()


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

    with pytest.raises(ValueError) as exc_info:
        await occupation_service_v4.finalizar_spool(request)

    assert "Race condition" in str(exc_info.value)


# ============================================================================
# FINALIZAR Tests - Ownership validation
# ============================================================================

@pytest.mark.asyncio
async def test_finalizar_spool_not_owner(occupation_service_v4, mock_redis_lock_service):
    """Test FINALIZAR fails if worker doesn't own the lock."""
    # Mock different owner
    mock_redis_lock_service.get_lock_owner.return_value = (94, "other-token")

    request = FinalizarRequest(
        tag_spool="OT-123",
        worker_id=93,  # Different from owner
        worker_nombre="MR(93)",
        operacion=ActionType.ARM,
        selected_unions=["OT-123+1"]
    )

    with pytest.raises(NoAutorizadoError):
        await occupation_service_v4.finalizar_spool(request)


@pytest.mark.asyncio
async def test_finalizar_spool_lock_expired(occupation_service_v4, mock_redis_lock_service):
    """Test FINALIZAR fails if lock no longer exists."""
    # Override default mock to return None (lock expired)
    mock_redis_lock_service.get_lock_owner = AsyncMock(return_value=None)

    request = FinalizarRequest(
        tag_spool="OT-123",
        worker_id=93,
        worker_nombre="MR(93)",
        operacion=ActionType.ARM,
        selected_unions=["OT-123+1"]
    )

    with pytest.raises(LockExpiredError):
        await occupation_service_v4.finalizar_spool(request)


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
    """Test _determine_action raises ValueError for race condition."""
    with pytest.raises(ValueError) as exc_info:
        occupation_service_v4._determine_action(
            selected_count=15,
            total_available=10,
            operacion="ARM"
        )
    assert "Race condition" in str(exc_info.value)


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

    # Mock 5 available SOLD unions
    mock_union_repository.get_disponibles_sold_by_ot.return_value = [
        MagicMock() for _ in range(5)
    ]
    mock_union_repository.batch_update_sold.return_value = 2

    response = await occupation_service_v4.finalizar_spool(request)

    assert response.success is True
    assert response.action_taken == "PAUSAR"  # 2 of 5
    assert response.unions_processed == 2

    # Verify SOLD batch update called (not ARM)
    mock_union_repository.batch_update_sold.assert_called_once()
    mock_union_repository.batch_update_arm.assert_not_called()
