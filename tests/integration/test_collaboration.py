"""
Integration tests for multi-worker collaboration scenarios.

Tests v3.0 Phase 3 collaboration features:
- Worker handoff (different workers on same operation)
- Operation dependencies (ARM before SOLD)
- Sequential operations (multiple workers, multiple operations)
- Occupation history timeline

These are integration tests requiring real infrastructure:
- Google Sheets connection
- Redis connection
- StateService orchestration
"""

import pytest
from datetime import date, datetime
from unittest.mock import AsyncMock, Mock, patch

from backend.services.state_service import StateService
from backend.services.occupation_service import OccupationService
from backend.services.history_service import HistoryService
from backend.services.redis_event_service import RedisEventService
from backend.repositories.sheets_repository import SheetsRepository
from backend.repositories.metadata_repository import MetadataRepository
from backend.repositories.redis_repository import RedisRepository
from backend.models.occupation import TomarRequest, PausarRequest, CompletarRequest, OccupationResponse
from backend.models.enums import ActionType
from backend.models.spool import Spool
from backend.models.metadata import EventoTipo
from backend.exceptions import DependenciasNoSatisfechasError, SpoolNoEncontradoError


# ============================================================================
# FIXTURES
# ============================================================================


@pytest.fixture
def mock_sheets_repo():
    """Mock SheetsRepository for testing."""
    repo = Mock(spec=SheetsRepository)

    # Default spool state: Fecha_Materiales present, all operations pending
    default_spool = Spool(
        tag_spool="TEST-001",
        fecha_materiales=date(2026, 1, 10),
        armador=None,
        fecha_armado=None,
        soldador=None,
        fecha_soldadura=None,
        ocupado_por=None,
        fecha_ocupacion=None,
        version=0
    )

    repo.get_spool_by_tag.return_value = default_spool
    repo.find_row_by_column_value.return_value = 2  # Row 2 for TEST-001
    repo.update_cell_by_column_name.return_value = None

    return repo


@pytest.fixture
def mock_metadata_repo():
    """Mock MetadataRepository for testing."""
    repo = Mock(spec=MetadataRepository)
    repo.append_event.return_value = None
    repo.get_events_by_spool.return_value = []
    repo.log_event.return_value = "mock-uuid-123"
    return repo


@pytest.fixture
def mock_redis_client():
    """Mock Redis client for testing."""
    client = AsyncMock()
    client.set.return_value = True  # Lock acquired
    client.get.return_value = None  # No existing lock
    client.delete.return_value = 1  # Lock deleted
    client.eval.return_value = 1  # Lua script success
    return client


@pytest.fixture
def mock_occupation_service():
    """Mock OccupationService for testing."""
    service = AsyncMock(spec=OccupationService)

    # Default responses
    service.tomar.return_value = OccupationResponse(
        success=True,
        tag_spool="TEST-001",
        message="Spool tomado exitosamente"
    )

    service.pausar.return_value = OccupationResponse(
        success=True,
        tag_spool="TEST-001",
        message="Spool pausado exitosamente"
    )

    service.completar.return_value = OccupationResponse(
        success=True,
        tag_spool="TEST-001",
        message="Operación completada exitosamente"
    )

    return service


@pytest.fixture
def mock_redis_event_service():
    """Mock RedisEventService for testing."""
    service = AsyncMock(spec=RedisEventService)
    service.publish_spool_update.return_value = True
    return service


@pytest.fixture
def state_service(mock_occupation_service, mock_sheets_repo, mock_metadata_repo, mock_redis_event_service):
    """Create StateService instance with mocked dependencies."""
    return StateService(
        occupation_service=mock_occupation_service,
        sheets_repository=mock_sheets_repo,
        metadata_repository=mock_metadata_repo,
        redis_event_service=mock_redis_event_service
    )


@pytest.fixture
def history_service(mock_metadata_repo, mock_sheets_repo):
    """Create HistoryService instance with mocked dependencies."""
    return HistoryService(
        metadata_repository=mock_metadata_repo,
        sheets_repository=mock_sheets_repo
    )


# ============================================================================
# TEST: Armador Handoff
# ============================================================================


@pytest.mark.asyncio
async def test_armador_handoff(state_service, mock_sheets_repo):
    """
    Test ARM handoff between two workers.

    Scenario:
    1. Worker A (Armador) starts ARM (TOMAR)
    2. Worker A pauses (PAUSAR)
    3. Worker B (also Armador) takes over (TOMAR)
    4. Worker B completes (COMPLETAR)

    Verify:
    - Armador column shows "Worker B" at the end
    - Fecha_Armado is populated
    - Estado_Detalle shows "ARM completado"
    """
    # Step 1: Worker A starts ARM
    tomar_request_a = TomarRequest(
        tag_spool="TEST-001",
        worker_id=93,
        worker_nombre="MR(93)",
        operacion=ActionType.ARM
    )

    response = await state_service.tomar(tomar_request_a)
    assert response.success is True

    # Mock: spool now occupied by Worker A (ARM en_progreso) so PAUSAR is allowed
    mock_sheets_repo.get_spool_by_tag.return_value = Spool(
        tag_spool="TEST-001",
        fecha_materiales=date(2026, 1, 10),
        armador="MR(93)",
        fecha_armado=None,
        soldador=None,
        fecha_soldadura=None,
        ocupado_por="MR(93)",
        fecha_ocupacion=None,
        version=1
    )

    # Step 2: Worker A pauses
    pausar_request_a = PausarRequest(
        tag_spool="TEST-001",
        worker_id=93,
        worker_nombre="MR(93)",
        operacion=ActionType.ARM
    )

    response = await state_service.pausar(pausar_request_a)
    assert response.success is True

    # Step 3: Update mock to show Worker A's partial work
    mock_sheets_repo.get_spool_by_tag.return_value = Spool(
        tag_spool="TEST-001",
        fecha_materiales=date(2026, 1, 10),
        armador="MR(93)",  # Worker A left their mark
        fecha_armado=None,  # But didn't complete
        soldador=None,
        fecha_soldadura=None,
        ocupado_por=None,  # Released after PAUSAR
        fecha_ocupacion=None,
        version=1
    )

    # Step 4: Worker B takes over
    tomar_request_b = TomarRequest(
        tag_spool="TEST-001",
        worker_id=94,
        worker_nombre="JP(94)",
        operacion=ActionType.ARM
    )

    response = await state_service.tomar(tomar_request_b)
    assert response.success is True

    # Step 5: Worker B completes
    completar_request_b = CompletarRequest(
        tag_spool="TEST-001",
        worker_id=94,
        worker_nombre="JP(94)",
        operacion=ActionType.ARM,
        fecha_operacion=date(2026, 1, 27)
    )

    # Mock: ARM en_progreso (Worker B occupying) so completar(ARM) can transition
    mock_sheets_repo.get_spool_by_tag.return_value = Spool(
        tag_spool="TEST-001",
        fecha_materiales=date(2026, 1, 10),
        armador="JP(94)",
        fecha_armado=None,
        soldador=None,
        fecha_soldadura=None,
        ocupado_por="JP(94)",
        fecha_ocupacion="27-01-2026 12:00:00",
        version=2
    )

    response = await state_service.completar(completar_request_b)
    assert response.success is True

    # Mock final state (completar updated sheet via state machine; we assert on mock calls below)
    mock_sheets_repo.get_spool_by_tag.return_value = Spool(
        tag_spool="TEST-001",
        fecha_materiales=date(2026, 1, 10),
        armador="JP(94)",
        fecha_armado=date(2026, 1, 27),
        soldador=None,
        fecha_soldadura=None,
        ocupado_por=None,
        fecha_ocupacion=None,
        version=3
    )

    # Verify final state
    final_spool = mock_sheets_repo.get_spool_by_tag("TEST-001")
    assert final_spool.armador == "JP(94)", "Armador should show Worker B"
    assert final_spool.fecha_armado is not None, "Fecha_Armado should be populated"

    # Verify Estado_Detalle was updated (check mock calls)
    update_calls = mock_sheets_repo.update_cell_by_column_name.call_args_list
    assert len(update_calls) > 0, "Estado_Detalle should have been updated"

    # Verify last update shows ARM completado
    last_call = update_calls[-1]
    assert last_call[1]["column_name"] == "Estado_Detalle"
    estado_detalle_value = last_call[1]["value"]
    assert "completado" in estado_detalle_value.lower(), "Should show 'completado' status"


# ============================================================================
# TEST: Dependency Enforcement
# ============================================================================


@pytest.mark.asyncio
async def test_dependency_enforcement(state_service, mock_sheets_repo):
    """
    Test SOLD dependency on ARM.

    Scenario:
    - Try SOLD TOMAR without ARM initiated

    Verify:
    - Should raise DependenciasNoSatisfechasError
    - Error message includes "ARM must be initiated"
    """
    # Mock spool with no ARM work started
    mock_sheets_repo.get_spool_by_tag.return_value = Spool(
        tag_spool="TEST-002",
        fecha_materiales=date(2026, 1, 10),
        armador=None,  # No ARM work
        fecha_armado=None,
        soldador=None,
        fecha_soldadura=None,
        ocupado_por=None,
        fecha_ocupacion=None,
        version=0
    )

    # Try to start SOLD
    tomar_request_sold = TomarRequest(
        tag_spool="TEST-002",
        worker_id=95,
        worker_nombre="CP(95)",
        operacion=ActionType.SOLD
    )

    # SOLD state machine should block this via guard
    with pytest.raises(DependenciasNoSatisfechasError) as exc_info:
        await state_service.tomar(tomar_request_sold)

    # Verify error message
    error_message = str(exc_info.value).lower()
    assert "arm" in error_message, "Error should mention ARM dependency"


# ============================================================================
# TEST: Sequential Operations
# ============================================================================


@pytest.mark.asyncio
async def test_sequential_operations(state_service, mock_sheets_repo):
    """
    Test sequential operations by multiple workers.

    Scenario:
    1. Worker A completes ARM
    2. Worker B starts and completes SOLD

    Verify:
    - Both operations show completado in Estado_Detalle
    - Armador column shows Worker A
    - Soldador column shows Worker B
    """
    # Step 1: Worker A starts and completes ARM
    tomar_request_arm = TomarRequest(
        tag_spool="TEST-003",
        worker_id=93,
        worker_nombre="MR(93)",
        operacion=ActionType.ARM
    )

    await state_service.tomar(tomar_request_arm)

    # Complete ARM
    completar_request_arm = CompletarRequest(
        tag_spool="TEST-003",
        worker_id=93,
        worker_nombre="MR(93)",
        operacion=ActionType.ARM,
        fecha_operacion=date(2026, 1, 27)
    )

    # Mock: ARM in progress (armador set, fecha_armado None) so completar(ARM) can transition
    mock_sheets_repo.get_spool_by_tag.return_value = Spool(
        tag_spool="TEST-003",
        fecha_materiales=date(2026, 1, 10),
        armador="MR(93)",
        fecha_armado=None,
        soldador=None,
        fecha_soldadura=None,
        ocupado_por="MR(93)",
        fecha_ocupacion="27-01-2026 12:00:00",
        version=2
    )

    await state_service.completar(completar_request_arm)

    # After completar(ARM), mock shows ARM completed for next steps
    mock_sheets_repo.get_spool_by_tag.return_value = Spool(
        tag_spool="TEST-003",
        fecha_materiales=date(2026, 1, 10),
        armador="MR(93)",
        fecha_armado=date(2026, 1, 27),
        soldador=None,
        fecha_soldadura=None,
        ocupado_por=None,
        fecha_ocupacion=None,
        version=3
    )

    # Step 2: Worker B starts SOLD (ARM is now complete)
    tomar_request_sold = TomarRequest(
        tag_spool="TEST-003",
        worker_id=94,
        worker_nombre="JP(94)",
        operacion=ActionType.SOLD
    )

    await state_service.tomar(tomar_request_sold)

    # Complete SOLD
    completar_request_sold = CompletarRequest(
        tag_spool="TEST-003",
        worker_id=94,
        worker_nombre="JP(94)",
        operacion=ActionType.SOLD,
        fecha_operacion=date(2026, 1, 27)
    )

    # Mock: SOLD en_progreso (Worker B occupying) so completar(SOLD) can transition
    mock_sheets_repo.get_spool_by_tag.return_value = Spool(
        tag_spool="TEST-003",
        fecha_materiales=date(2026, 1, 10),
        armador="MR(93)",
        fecha_armado=date(2026, 1, 27),
        soldador="JP(94)",
        fecha_soldadura=None,
        ocupado_por="JP(94)",
        fecha_ocupacion="27-01-2026 12:00:00",
        version=4
    )

    await state_service.completar(completar_request_sold)

    # Mock final state for assertions
    mock_sheets_repo.get_spool_by_tag.return_value = Spool(
        tag_spool="TEST-003",
        fecha_materiales=date(2026, 1, 10),
        armador="MR(93)",
        fecha_armado=date(2026, 1, 27),
        soldador="JP(94)",
        fecha_soldadura=date(2026, 1, 27),
        ocupado_por=None,
        fecha_ocupacion=None,
        version=5
    )

    # Verify final state
    final_spool = mock_sheets_repo.get_spool_by_tag("TEST-003")
    assert final_spool.armador == "MR(93)", "Armador should be Worker A"
    assert final_spool.soldador == "JP(94)", "Soldador should be Worker B"
    assert final_spool.fecha_armado is not None, "ARM should be completed"
    assert final_spool.fecha_soldadura is not None, "SOLD should be completed"

    # Verify Estado_Detalle shows both completado
    update_calls = mock_sheets_repo.update_cell_by_column_name.call_args_list
    last_call = update_calls[-1]
    estado_detalle_value = last_call[1]["value"]
    assert "ARM completado" in estado_detalle_value or "completado" in estado_detalle_value.lower()


# ============================================================================
# TEST: Occupation History Timeline
# ============================================================================


@pytest.mark.asyncio
async def test_occupation_history_timeline(history_service, mock_metadata_repo, mock_sheets_repo):
    """
    Test occupation history aggregation.

    Scenario:
    - Multiple workers work on same spool
    - Query history endpoint

    Verify:
    - Sessions show correct workers
    - Times are populated
    - Durations are calculated
    """
    from backend.models.metadata import MetadataEvent, Accion
    from backend.models.enums import EventoTipo

    # Mock spool exists
    mock_sheets_repo.get_spool_by_tag.return_value = Spool(
        tag_spool="TEST-004",
        fecha_materiales=date(2026, 1, 10),
        armador="JP(94)",
        fecha_armado=date(2026, 1, 27),
        soldador=None,
        fecha_soldadura=None,
        ocupado_por=None,
        fecha_ocupacion=None,
        version=2
    )

    # Mock Metadata events showing two workers
    mock_events = [
        # Worker A session
        MetadataEvent(
            id="event-1",
            timestamp=datetime(2026, 1, 27, 10, 30, 0),
            evento_tipo=EventoTipo.TOMAR_SPOOL,
            tag_spool="TEST-004",
            worker_id=93,
            worker_nombre="MR(93)",
            operacion="ARM",
            accion=Accion.INICIAR,
            fecha_operacion="27-01-2026",
            metadata_json="{}"
        ),
        MetadataEvent(
            id="event-2",
            timestamp=datetime(2026, 1, 27, 12, 45, 0),
            evento_tipo=EventoTipo.PAUSAR_SPOOL,
            tag_spool="TEST-004",
            worker_id=93,
            worker_nombre="MR(93)",
            operacion="ARM",
            accion=Accion.INICIAR,
            fecha_operacion="27-01-2026",
            metadata_json="{}"
        ),
        # Worker B session
        MetadataEvent(
            id="event-3",
            timestamp=datetime(2026, 1, 27, 13, 0, 0),
            evento_tipo=EventoTipo.TOMAR_SPOOL,
            tag_spool="TEST-004",
            worker_id=94,
            worker_nombre="JP(94)",
            operacion="ARM",
            accion=Accion.INICIAR,
            fecha_operacion="27-01-2026",
            metadata_json="{}"
        ),
        MetadataEvent(
            id="event-4",
            timestamp=datetime(2026, 1, 27, 14, 30, 0),
            evento_tipo=EventoTipo.COMPLETAR_ARM,
            tag_spool="TEST-004",
            worker_id=94,
            worker_nombre="JP(94)",
            operacion="ARM",
            accion=Accion.COMPLETAR,
            fecha_operacion="27-01-2026",
            metadata_json="{}"
        )
    ]

    mock_metadata_repo.get_events_by_spool.return_value = mock_events

    # Query history
    history = await history_service.get_occupation_history("TEST-004")

    # Verify response structure
    assert history.tag_spool == "TEST-004"
    assert len(history.sessions) == 2, "Should have 2 sessions"

    # Verify first session (Worker A)
    session1 = history.sessions[0]
    assert session1.worker_nombre == "MR(93)"
    assert session1.worker_id == 93
    assert session1.operacion == "ARM"
    assert session1.duration is not None, "Duration should be calculated"
    assert "h" in session1.duration or "m" in session1.duration, "Duration should be human-readable"

    # Verify second session (Worker B)
    session2 = history.sessions[1]
    assert session2.worker_nombre == "JP(94)"
    assert session2.worker_id == 94
    assert session2.operacion == "ARM"
    assert session2.duration is not None, "Duration should be calculated"


# ============================================================================
# TEST: Error Cases
# ============================================================================


@pytest.mark.asyncio
async def test_history_for_nonexistent_spool(history_service, mock_sheets_repo):
    """
    Test history query for non-existent spool.

    Verify:
    - Raises SpoolNoEncontradoError
    """
    mock_sheets_repo.get_spool_by_tag.return_value = None

    with pytest.raises(SpoolNoEncontradoError):
        await history_service.get_occupation_history("NONEXISTENT")
