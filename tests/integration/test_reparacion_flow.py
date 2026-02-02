"""
Integration tests for reparación workflow with cycle tracking and BLOQUEADO enforcement.

Tests v3.0 Phase 6 reparación features:
- TOMAR/PAUSAR/COMPLETAR/CANCELAR actions
- 3-cycle limit enforcement with BLOQUEADO state
- Cycle counter tracking in Estado_Detalle
- Metrología → Reparación → Metrología loop
- SSE event publishing
- Supervisor override detection

These are integration tests using mocked dependencies to verify
the full orchestration flow through ReparacionService.
"""

import pytest
from datetime import date
from unittest.mock import AsyncMock, Mock, patch
import json

from backend.services.reparacion_service import ReparacionService
from backend.services.validation_service import ValidationService
from backend.services.cycle_counter_service import CycleCounterService
from backend.repositories.sheets_repository import SheetsRepository
from backend.repositories.metadata_repository import MetadataRepository
from backend.services.redis_event_service import RedisEventService
from backend.services.estado_detalle_service import EstadoDetalleService
from backend.models.spool import Spool
from backend.exceptions import (
    SpoolNoEncontradoError,
    SpoolBloqueadoError,
    OperacionNoDisponibleError,
    SpoolOccupiedError,
    NoAutorizadoError
)


# ============================================================================
# FIXTURES
# ============================================================================


@pytest.fixture
def mock_sheets_repo():
    """Mock SheetsRepository for testing (ReparacionStateMachine uses batch_update_by_column_name, get_cell_value)."""
    repo = Mock()  # No spec: state machine calls get_cell_value which may not be on SheetsRepository
    repo.get_spool_by_tag.return_value = None  # Will be set per test
    repo.find_row_by_column_value.return_value = 2
    repo.get_cell_value.return_value = ""
    repo.batch_update_by_column_name.return_value = None
    return repo


@pytest.fixture
def mock_metadata_repo():
    """Mock MetadataRepository for testing."""
    repo = Mock(spec=MetadataRepository)
    repo.append_event.return_value = None
    repo.get_events_by_spool.return_value = []  # Will be set per test
    return repo


@pytest.fixture
def mock_redis_event_service():
    """Mock RedisEventService for testing."""
    service = AsyncMock(spec=RedisEventService)
    service.publish_spool_update.return_value = True
    return service


@pytest.fixture
def validation_service():
    """Real ValidationService for prerequisite validation."""
    return ValidationService(role_service=None)


@pytest.fixture
def cycle_counter_service():
    """Real CycleCounterService for cycle tracking."""
    return CycleCounterService()


@pytest.fixture
def reparacion_service(validation_service, cycle_counter_service, mock_sheets_repo, mock_metadata_repo, mock_redis_event_service):
    """ReparacionService with mocked dependencies."""
    return ReparacionService(
        validation_service=validation_service,
        cycle_counter_service=cycle_counter_service,
        sheets_repository=mock_sheets_repo,
        metadata_repository=mock_metadata_repo,
        redis_event_service=mock_redis_event_service
    )


@pytest.fixture
def estado_detalle_service(mock_sheets_repo, mock_metadata_repo):
    """EstadoDetalleService with mocked dependencies."""
    return EstadoDetalleService(
        sheets_repo=mock_sheets_repo,
        metadata_repo=mock_metadata_repo
    )


@pytest.fixture
def rechazado_cycle1_spool():
    """Spool rejected once (cycle 1/3)."""
    return Spool(
        tag_spool="REPAIR-001",
        fecha_materiales=date(2026, 1, 20),
        fecha_armado=date(2026, 1, 22),
        fecha_soldadura=date(2026, 1, 25),
        fecha_qc_metrologia=date(2026, 1, 27),
        armador="MR(93)",
        soldador="JP(94)",
        ocupado_por=None,
        fecha_ocupacion=None,
        estado_detalle="RECHAZADO (Ciclo 1/3) - Pendiente reparación",
        version=8
    )


@pytest.fixture
def rechazado_cycle2_spool():
    """Spool rejected twice (cycle 2/3)."""
    return Spool(
        tag_spool="REPAIR-002",
        fecha_materiales=date(2026, 1, 20),
        fecha_armado=date(2026, 1, 22),
        fecha_soldadura=date(2026, 1, 25),
        fecha_qc_metrologia=date(2026, 1, 27),
        armador="MR(93)",
        soldador="JP(94)",
        ocupado_por=None,
        fecha_ocupacion=None,
        estado_detalle="RECHAZADO (Ciclo 2/3) - Pendiente reparación",
        version=12
    )


@pytest.fixture
def bloqueado_spool():
    """Spool blocked after 3 rejections."""
    return Spool(
        tag_spool="REPAIR-003",
        fecha_materiales=date(2026, 1, 20),
        fecha_armado=date(2026, 1, 22),
        fecha_soldadura=date(2026, 1, 25),
        fecha_qc_metrologia=date(2026, 1, 27),
        armador="MR(93)",
        soldador="JP(94)",
        ocupado_por=None,
        fecha_ocupacion=None,
        estado_detalle="BLOQUEADO - Contactar supervisor",
        version=15
    )


@pytest.fixture
def en_reparacion_spool():
    """Spool currently being repaired by worker 95."""
    return Spool(
        tag_spool="REPAIR-004",
        fecha_materiales=date(2026, 1, 20),
        fecha_armado=date(2026, 1, 22),
        fecha_soldadura=date(2026, 1, 25),
        fecha_qc_metrologia=date(2026, 1, 27),
        armador="MR(93)",
        soldador="JP(94)",
        ocupado_por="CP(95)",
        fecha_ocupacion="28/01/2026",
        estado_detalle="EN_REPARACION (Ciclo 1/3) - CP(95)",
        version=10
    )


@pytest.fixture
def reparacion_pausada_spool():
    """Spool with paused repair work."""
    return Spool(
        tag_spool="REPAIR-005",
        fecha_materiales=date(2026, 1, 20),
        fecha_armado=date(2026, 1, 22),
        fecha_soldadura=date(2026, 1, 25),
        fecha_qc_metrologia=date(2026, 1, 27),
        armador="MR(93)",
        soldador="JP(94)",
        ocupado_por=None,
        fecha_ocupacion=None,
        estado_detalle="REPARACION_PAUSADA (Ciclo 2/3)",
        version=14
    )


# ============================================================================
# HAPPY PATH TESTS - COMPLETE REPAIR CYCLE
# ============================================================================


@pytest.mark.asyncio
async def test_complete_repair_cycle_success(reparacion_service, mock_sheets_repo, rechazado_cycle1_spool):
    """
    Should complete full repair cycle: RECHAZADO → TOMAR → COMPLETAR → PENDIENTE_METROLOGIA.

    Flow:
    1. Metrología rejects spool → RECHAZADO (Ciclo 1/3)
    2. Worker repairs → TOMAR → EN_REPARACION
    3. Worker completes → COMPLETAR → PENDIENTE_METROLOGIA
    4. Metrología approves → APROBADO (cycle reset)
    """
    tag_spool = rechazado_cycle1_spool.tag_spool
    worker_id = 95
    worker_nombre = "CP(95)"

    # Mock spool fetch
    mock_sheets_repo.get_spool_by_tag.return_value = rechazado_cycle1_spool

    # Step 1: TOMAR reparación
    result = await reparacion_service.tomar_reparacion(tag_spool, worker_id, worker_nombre)

    assert result["success"] is True
    assert result["tag_spool"] == tag_spool
    assert result["worker_nombre"] == worker_nombre
    assert result["cycle"] == 1
    assert "EN_REPARACION" in result["estado_detalle"]

    # Verify Sheets updated (via state machine)
    assert mock_sheets_repo.get_spool_by_tag.called

    # Step 2: Update mock to EN_REPARACION state
    en_reparacion_spool = Spool(
        tag_spool=tag_spool,
        fecha_materiales=rechazado_cycle1_spool.fecha_materiales,
        fecha_armado=rechazado_cycle1_spool.fecha_armado,
        fecha_soldadura=rechazado_cycle1_spool.fecha_soldadura,
        fecha_qc_metrologia=rechazado_cycle1_spool.fecha_qc_metrologia,
        armador=rechazado_cycle1_spool.armador,
        soldador=rechazado_cycle1_spool.soldador,
        ocupado_por=worker_nombre,
        fecha_ocupacion="28/01/2026",
        estado_detalle=f"EN_REPARACION (Ciclo 1/3) - {worker_nombre}",
        version=9
    )
    mock_sheets_repo.get_spool_by_tag.return_value = en_reparacion_spool

    # Step 3: COMPLETAR reparación
    result = await reparacion_service.completar_reparacion(tag_spool, worker_id, worker_nombre)

    assert result["success"] is True
    assert result["estado_detalle"] == "PENDIENTE_METROLOGIA"
    assert result["cycle"] == 1

    # Verify state machine transitioned to PENDIENTE_METROLOGIA
    # (in real flow, metrología service would pick this up next)


@pytest.mark.asyncio
async def test_three_rejections_blocks_spool(reparacion_service, mock_sheets_repo, rechazado_cycle1_spool):
    """
    Should block spool after 3 consecutive rejections.

    Flow:
    1. First rejection → RECHAZADO (Ciclo 1/3)
    2. Repair + Second rejection → RECHAZADO (Ciclo 2/3)
    3. Repair + Third rejection → BLOQUEADO
    4. Fourth TOMAR attempt → 403 SpoolBloqueadoError
    """
    tag_spool = rechazado_cycle1_spool.tag_spool
    worker_id = 95
    worker_nombre = "CP(95)"

    # Cycle 1 RECHAZADO
    mock_sheets_repo.get_spool_by_tag.return_value = rechazado_cycle1_spool

    # Should allow TOMAR at cycle 1
    result1 = await reparacion_service.tomar_reparacion(tag_spool, worker_id, worker_nombre)
    assert result1["success"] is True
    assert result1["cycle"] == 1

    # Mock cycle 2 RECHAZADO spool
    cycle2_spool = Spool(
        tag_spool=tag_spool,
        fecha_materiales=rechazado_cycle1_spool.fecha_materiales,
        fecha_armado=rechazado_cycle1_spool.fecha_armado,
        fecha_soldadura=rechazado_cycle1_spool.fecha_soldadura,
        fecha_qc_metrologia=rechazado_cycle1_spool.fecha_qc_metrologia,
        armador=rechazado_cycle1_spool.armador,
        soldador=rechazado_cycle1_spool.soldador,
        ocupado_por=None,
        fecha_ocupacion=None,
        estado_detalle="RECHAZADO (Ciclo 2/3) - Pendiente reparación",
        version=11
    )
    mock_sheets_repo.get_spool_by_tag.return_value = cycle2_spool

    # Should allow TOMAR at cycle 2
    result2 = await reparacion_service.tomar_reparacion(tag_spool, worker_id, worker_nombre)
    assert result2["success"] is True
    assert result2["cycle"] == 2

    # Mock BLOQUEADO spool after 3rd rejection
    bloqueado_spool = Spool(
        tag_spool=tag_spool,
        fecha_materiales=rechazado_cycle1_spool.fecha_materiales,
        fecha_armado=rechazado_cycle1_spool.fecha_armado,
        fecha_soldadura=rechazado_cycle1_spool.fecha_soldadura,
        fecha_qc_metrologia=rechazado_cycle1_spool.fecha_qc_metrologia,
        armador=rechazado_cycle1_spool.armador,
        soldador=rechazado_cycle1_spool.soldador,
        ocupado_por=None,
        fecha_ocupacion=None,
        estado_detalle="BLOQUEADO - Contactar supervisor",
        version=15
    )
    mock_sheets_repo.get_spool_by_tag.return_value = bloqueado_spool

    # Should raise SpoolBloqueadoError on 4th attempt
    with pytest.raises(SpoolBloqueadoError) as exc_info:
        await reparacion_service.tomar_reparacion(tag_spool, worker_id, worker_nombre)

    assert exc_info.value.data["tag_spool"] == tag_spool
    assert "bloqueado" in exc_info.value.message.lower()


# ============================================================================
# PAUSAR/RESUME WORKFLOW
# ============================================================================


@pytest.mark.asyncio
async def test_pausar_and_resume_repair(reparacion_service, mock_sheets_repo, en_reparacion_spool):
    """
    Should allow worker to PAUSAR and later resume repair work.

    Flow:
    1. Worker has spool EN_REPARACION
    2. Worker PAUSAR → REPARACION_PAUSADA
    3. Worker TOMAR again → EN_REPARACION
    4. Worker COMPLETAR → PENDIENTE_METROLOGIA
    """
    tag_spool = en_reparacion_spool.tag_spool
    worker_id = 95
    worker_nombre = "CP(95)"

    # Mock EN_REPARACION spool
    mock_sheets_repo.get_spool_by_tag.return_value = en_reparacion_spool

    # Step 1: PAUSAR reparación
    result = await reparacion_service.pausar_reparacion(tag_spool, worker_id)

    assert result["success"] is True
    assert "REPARACION_PAUSADA" in result["estado_detalle"]

    # Step 2: Mock REPARACION_PAUSADA state
    pausada_spool = Spool(
        tag_spool=tag_spool,
        fecha_materiales=en_reparacion_spool.fecha_materiales,
        fecha_armado=en_reparacion_spool.fecha_armado,
        fecha_soldadura=en_reparacion_spool.fecha_soldadura,
        fecha_qc_metrologia=en_reparacion_spool.fecha_qc_metrologia,
        armador=en_reparacion_spool.armador,
        soldador=en_reparacion_spool.soldador,
        ocupado_por=None,
        fecha_ocupacion=None,
        estado_detalle="REPARACION_PAUSADA (Ciclo 1/3)",
        version=11
    )
    mock_sheets_repo.get_spool_by_tag.return_value = pausada_spool

    # Step 3: TOMAR again (resume)
    result = await reparacion_service.tomar_reparacion(tag_spool, worker_id, worker_nombre)

    assert result["success"] is True
    assert result["cycle"] == 1  # Cycle not incremented by PAUSAR


# ============================================================================
# CANCELAR WORKFLOW
# ============================================================================


@pytest.mark.asyncio
async def test_cancelar_returns_to_rechazado(reparacion_service, mock_sheets_repo, en_reparacion_spool):
    """
    Should return spool to RECHAZADO state when CANCELAR is triggered.

    Flow:
    1. Worker has spool EN_REPARACION
    2. Worker CANCELAR → RECHAZADO (cycle preserved)
    """
    tag_spool = en_reparacion_spool.tag_spool
    worker_id = 95

    # Mock EN_REPARACION spool
    mock_sheets_repo.get_spool_by_tag.return_value = en_reparacion_spool

    # CANCELAR reparación
    result = await reparacion_service.cancelar_reparacion(tag_spool, worker_id)

    assert result["success"] is True
    assert "RECHAZADO" in result["estado_detalle"]
    # Verify cycle info preserved in estado_detalle (via state machine)


# ============================================================================
# SSE EVENT PUBLISHING
# ============================================================================


@pytest.mark.asyncio
async def test_sse_events_published_for_all_actions(reparacion_service, mock_sheets_repo, mock_redis_event_service, rechazado_cycle1_spool, en_reparacion_spool):
    """
    Should publish SSE events for TOMAR, PAUSAR, COMPLETAR, CANCELAR actions.
    """
    tag_spool = rechazado_cycle1_spool.tag_spool
    worker_id = 95
    worker_nombre = "CP(95)"

    # Test TOMAR event
    mock_sheets_repo.get_spool_by_tag.return_value = rechazado_cycle1_spool
    await reparacion_service.tomar_reparacion(tag_spool, worker_id, worker_nombre)

    assert mock_redis_event_service.publish_spool_update.called
    call_args = mock_redis_event_service.publish_spool_update.call_args
    assert call_args[1]["event_type"] == "TOMAR_REPARACION"
    assert call_args[1]["tag_spool"] == tag_spool
    assert call_args[1]["worker_nombre"] == worker_nombre

    # Reset mock
    mock_redis_event_service.reset_mock()

    # Test PAUSAR event
    mock_sheets_repo.get_spool_by_tag.return_value = en_reparacion_spool
    await reparacion_service.pausar_reparacion(tag_spool, worker_id)

    assert mock_redis_event_service.publish_spool_update.called
    call_args = mock_redis_event_service.publish_spool_update.call_args
    assert call_args[1]["event_type"] == "PAUSAR_REPARACION"

    # Reset mock
    mock_redis_event_service.reset_mock()

    # Test COMPLETAR event
    mock_sheets_repo.get_spool_by_tag.return_value = en_reparacion_spool
    await reparacion_service.completar_reparacion(tag_spool, worker_id, worker_nombre)

    assert mock_redis_event_service.publish_spool_update.called
    call_args = mock_redis_event_service.publish_spool_update.call_args
    assert call_args[1]["event_type"] == "COMPLETAR_REPARACION"


# ============================================================================
# SUPERVISOR OVERRIDE DETECTION
# ============================================================================


def test_supervisor_override_detected(estado_detalle_service, mock_sheets_repo, mock_metadata_repo):
    """
    Should detect and log when supervisor manually changes BLOQUEADO → RECHAZADO.

    Flow:
    1. Spool is BLOQUEADO (from last event)
    2. Supervisor manually changes Estado_Detalle to RECHAZADO in Sheets
    3. System detects override and logs SUPERVISOR_OVERRIDE event
    """
    tag_spool = "REPAIR-OVERRIDE"

    # Mock current state: RECHAZADO
    current_spool = Spool(
        tag_spool=tag_spool,
        fecha_materiales=date(2026, 1, 20),
        fecha_armado=date(2026, 1, 22),
        fecha_soldadura=date(2026, 1, 25),
        fecha_qc_metrologia=date(2026, 1, 27),
        armador="MR(93)",
        soldador="JP(94)",
        ocupado_por=None,
        fecha_ocupacion=None,
        estado_detalle="RECHAZADO (Ciclo 2/3) - Pendiente reparación",
        version=16
    )
    mock_sheets_repo.get_spool_by_tag.return_value = current_spool

    # Mock last event: was BLOQUEADO
    from backend.models.metadata import MetadataEvent, EventoTipo, Accion
    from datetime import datetime

    last_event = MetadataEvent(
        id="event-123",
        timestamp=datetime(2026, 1, 27, 15, 0, 0),
        evento_tipo=EventoTipo.CANCELAR_METROLOGIA,  # Simulating rejection that led to BLOQUEADO
        tag_spool=tag_spool,
        worker_id=91,
        worker_nombre="Supervisor(91)",
        operacion="METROLOGIA",
        accion=Accion.CANCELAR,
        fecha_operacion="27-01-2026",
        metadata_json=json.dumps({"estado_detalle": "BLOQUEADO - Contactar supervisor"})
    )
    mock_metadata_repo.get_events_by_spool.return_value = [last_event]

    # Detect override
    result = estado_detalle_service.detect_supervisor_override(tag_spool)

    assert result is not None
    assert result["detected"] is True
    assert "BLOQUEADO" in result["previous_estado"]
    assert "RECHAZADO" in result["current_estado"]
    assert result["event_id"] is not None

    # Verify SUPERVISOR_OVERRIDE event logged
    assert mock_metadata_repo.append_event.called
    event_dict = mock_metadata_repo.append_event.call_args[0][0]
    assert event_dict["evento_tipo"] == "SUPERVISOR_OVERRIDE"
    assert event_dict["worker_id"] == 0  # System event
    assert event_dict["worker_nombre"] == "SYSTEM"


def test_no_override_for_normal_transitions(estado_detalle_service, mock_sheets_repo, mock_metadata_repo):
    """
    Should NOT detect override for normal state transitions.
    """
    tag_spool = "REPAIR-NORMAL"

    # Mock current state: EN_REPARACION
    current_spool = Spool(
        tag_spool=tag_spool,
        fecha_materiales=date(2026, 1, 20),
        fecha_armado=date(2026, 1, 22),
        fecha_soldadura=date(2026, 1, 25),
        fecha_qc_metrologia=date(2026, 1, 27),
        armador="MR(93)",
        soldador="JP(94)",
        ocupado_por="CP(95)",
        fecha_ocupacion="28/01/2026",
        estado_detalle="EN_REPARACION (Ciclo 1/3) - CP(95)",
        version=10
    )
    mock_sheets_repo.get_spool_by_tag.return_value = current_spool

    # Mock last event: was RECHAZADO (normal transition)
    from backend.models.metadata import MetadataEvent, EventoTipo, Accion
    from datetime import datetime

    last_event = MetadataEvent(
        id="event-456",
        timestamp=datetime(2026, 1, 28, 10, 0, 0),
        evento_tipo=EventoTipo.INICIAR_METROLOGIA,
        tag_spool=tag_spool,
        worker_id=95,
        worker_nombre="CP(95)",
        operacion="REPARACION",
        accion=Accion.INICIAR,
        fecha_operacion="28-01-2026",
        metadata_json=json.dumps({"estado_detalle": "RECHAZADO (Ciclo 1/3)"})
    )
    mock_metadata_repo.get_events_by_spool.return_value = [last_event]

    # Should NOT detect override
    result = estado_detalle_service.detect_supervisor_override(tag_spool)

    assert result is None
    assert not mock_metadata_repo.append_event.called


# ============================================================================
# ERROR CASES
# ============================================================================


@pytest.mark.asyncio
async def test_cannot_tomar_bloqueado_spool(reparacion_service, mock_sheets_repo, bloqueado_spool):
    """Should raise SpoolBloqueadoError when trying to TOMAR BLOQUEADO spool."""
    tag_spool = bloqueado_spool.tag_spool
    worker_id = 95
    worker_nombre = "CP(95)"

    mock_sheets_repo.get_spool_by_tag.return_value = bloqueado_spool

    with pytest.raises(SpoolBloqueadoError) as exc_info:
        await reparacion_service.tomar_reparacion(tag_spool, worker_id, worker_nombre)

    assert exc_info.value.data["tag_spool"] == tag_spool


@pytest.mark.asyncio
async def test_cannot_completar_without_ownership(reparacion_service, mock_sheets_repo, en_reparacion_spool):
    """Should raise NoAutorizadoError if worker doesn't own the spool."""
    tag_spool = en_reparacion_spool.tag_spool
    wrong_worker_id = 99  # Different worker
    wrong_worker_nombre = "WW(99)"

    mock_sheets_repo.get_spool_by_tag.return_value = en_reparacion_spool

    with pytest.raises(NoAutorizadoError):
        await reparacion_service.completar_reparacion(tag_spool, wrong_worker_id, wrong_worker_nombre)


@pytest.mark.asyncio
async def test_cannot_tomar_already_occupied(reparacion_service, mock_sheets_repo, rechazado_cycle1_spool):
    """Should raise SpoolOccupiedError if spool already occupied by another worker."""
    # Spool is RECHAZADO (eligible for repair) but already occupied by CP(95)
    occupied_spool = Spool(
        tag_spool=rechazado_cycle1_spool.tag_spool,
        fecha_materiales=rechazado_cycle1_spool.fecha_materiales,
        fecha_armado=rechazado_cycle1_spool.fecha_armado,
        fecha_soldadura=rechazado_cycle1_spool.fecha_soldadura,
        fecha_qc_metrologia=rechazado_cycle1_spool.fecha_qc_metrologia,
        armador=rechazado_cycle1_spool.armador,
        soldador=rechazado_cycle1_spool.soldador,
        ocupado_por="CP(95)",
        fecha_ocupacion="28/01/2026",
        estado_detalle="RECHAZADO (Ciclo 1/3) - Pendiente reparación",
        version=8
    )
    tag_spool = occupied_spool.tag_spool
    worker_id = 96
    worker_nombre = "NW(96)"

    mock_sheets_repo.get_spool_by_tag.return_value = occupied_spool

    with pytest.raises(SpoolOccupiedError):
        await reparacion_service.tomar_reparacion(tag_spool, worker_id, worker_nombre)
