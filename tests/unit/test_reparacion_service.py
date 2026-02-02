"""
Unit tests for ReparacionService (Phase 6).

Tests reparación orchestration with cycle tracking, SSE events, and state machine integration.
"""

import pytest
from unittest.mock import AsyncMock, Mock, patch
from datetime import date
import json

from backend.services.reparacion_service import ReparacionService
from backend.services.validation_service import ValidationService
from backend.services.cycle_counter_service import CycleCounterService
from backend.repositories.sheets_repository import SheetsRepository
from backend.repositories.metadata_repository import MetadataRepository
from backend.services.redis_event_service import RedisEventService
from backend.models.spool import Spool
from backend.exceptions import SpoolNoEncontradoError, SpoolBloqueadoError


# ============================================================================
# FIXTURES
# ============================================================================


@pytest.fixture
def mock_validation_service():
    """Mock ValidationService."""
    service = Mock(spec=ValidationService)
    service.validar_puede_tomar_reparacion.return_value = None  # Success
    service.validar_puede_cancelar_reparacion.return_value = None  # Success
    return service


@pytest.fixture
def mock_cycle_counter():
    """Mock CycleCounterService."""
    service = Mock(spec=CycleCounterService)
    service.extract_cycle_count.return_value = 1
    service.should_block.return_value = False
    service.build_reparacion_estado.return_value = "EN_REPARACION (Ciclo 1/3) - MR(93)"
    service.build_rechazado_estado.return_value = "RECHAZADO (Ciclo 1/3) - Pendiente reparación"
    service.MAX_CYCLES = 3
    return service


@pytest.fixture
def mock_sheets_repo():
    """Mock SheetsRepository."""
    repo = Mock(spec=SheetsRepository)
    return repo


@pytest.fixture
def mock_metadata_repo():
    """Mock MetadataRepository."""
    repo = Mock(spec=MetadataRepository)
    repo.append_event.return_value = None
    return repo


@pytest.fixture
def mock_redis_event_service():
    """Mock RedisEventService."""
    service = AsyncMock(spec=RedisEventService)
    service.publish_spool_update.return_value = True
    return service


@pytest.fixture
def reparacion_service(
    mock_validation_service,
    mock_cycle_counter,
    mock_sheets_repo,
    mock_metadata_repo,
    mock_redis_event_service
):
    """ReparacionService with all dependencies mocked."""
    return ReparacionService(
        validation_service=mock_validation_service,
        cycle_counter_service=mock_cycle_counter,
        sheets_repository=mock_sheets_repo,
        metadata_repository=mock_metadata_repo,
        redis_event_service=mock_redis_event_service
    )


@pytest.fixture
def rechazado_spool():
    """Sample RECHAZADO spool."""
    return Spool(
        tag_spool="UNIT-001",
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
def en_reparacion_spool():
    """Sample EN_REPARACION spool."""
    return Spool(
        tag_spool="UNIT-002",
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


# ============================================================================
# TOMAR REPARACION TESTS
# ============================================================================


@pytest.mark.asyncio
async def test_tomar_extracts_cycle_count(reparacion_service, mock_sheets_repo, mock_cycle_counter, rechazado_spool):
    """Should extract cycle count from Estado_Detalle when taking spool."""
    tag_spool = rechazado_spool.tag_spool
    worker_id = 95
    worker_nombre = "CP(95)"

    mock_sheets_repo.get_spool_by_tag.return_value = rechazado_spool

    # Mock state machine behavior
    with patch("backend.services.reparacion_service.REPARACIONStateMachine") as MockStateMachine:
        mock_machine = Mock()
        mock_machine.current_state.id = "en_reparacion"
        mock_machine.get_state_id.return_value = "en_reparacion"
        MockStateMachine.return_value = mock_machine

        result = await reparacion_service.tomar_reparacion(tag_spool, worker_id, worker_nombre)

    # Verify cycle counter called
    mock_cycle_counter.extract_cycle_count.assert_called_once_with(rechazado_spool.estado_detalle)
    assert result["cycle"] == 1  # Mocked return value


@pytest.mark.asyncio
async def test_tomar_checks_blocking(reparacion_service, mock_sheets_repo, mock_cycle_counter, rechazado_spool):
    """Should check if spool should be blocked based on cycle count."""
    tag_spool = rechazado_spool.tag_spool
    worker_id = 95
    worker_nombre = "CP(95)"

    mock_sheets_repo.get_spool_by_tag.return_value = rechazado_spool
    mock_cycle_counter.should_block.return_value = True  # Simulate blocking condition

    with pytest.raises(SpoolBloqueadoError):
        await reparacion_service.tomar_reparacion(tag_spool, worker_id, worker_nombre)

    # Verify should_block was called with extracted cycle
    mock_cycle_counter.should_block.assert_called_once_with(1)


@pytest.mark.asyncio
async def test_tomar_publishes_sse_event(reparacion_service, mock_sheets_repo, mock_redis_event_service, rechazado_spool):
    """Should publish SSE event when taking spool for repair."""
    tag_spool = rechazado_spool.tag_spool
    worker_id = 95
    worker_nombre = "CP(95)"

    mock_sheets_repo.get_spool_by_tag.return_value = rechazado_spool

    with patch("backend.services.reparacion_service.REPARACIONStateMachine") as MockStateMachine:
        mock_machine = Mock()
        mock_machine.current_state.id = "en_reparacion"
        mock_machine.get_state_id.return_value = "en_reparacion"
        MockStateMachine.return_value = mock_machine

        result = await reparacion_service.tomar_reparacion(tag_spool, worker_id, worker_nombre)

    # Verify SSE event published
    mock_redis_event_service.publish_spool_update.assert_called_once()
    call_kwargs = mock_redis_event_service.publish_spool_update.call_args[1]
    assert call_kwargs["event_type"] == "TOMAR_REPARACION"
    assert call_kwargs["tag_spool"] == tag_spool
    assert call_kwargs["worker_nombre"] == worker_nombre
    assert "cycle" in call_kwargs["additional_data"]


@pytest.mark.asyncio
async def test_tomar_sse_failure_does_not_block(reparacion_service, mock_sheets_repo, mock_redis_event_service, rechazado_spool):
    """Should continue operation even if SSE publishing fails (best-effort pattern)."""
    tag_spool = rechazado_spool.tag_spool
    worker_id = 95
    worker_nombre = "CP(95)"

    mock_sheets_repo.get_spool_by_tag.return_value = rechazado_spool
    mock_redis_event_service.publish_spool_update.side_effect = Exception("Redis connection failed")

    with patch("backend.services.reparacion_service.REPARACIONStateMachine") as MockStateMachine:
        mock_machine = Mock()
        mock_machine.current_state.id = "en_reparacion"
        mock_machine.get_state_id.return_value = "en_reparacion"
        MockStateMachine.return_value = mock_machine

        # Should NOT raise exception despite SSE failure
        result = await reparacion_service.tomar_reparacion(tag_spool, worker_id, worker_nombre)

    assert result["success"] is True


# ============================================================================
# PAUSAR REPARACION TESTS
# ============================================================================


@pytest.mark.asyncio
async def test_pausar_clears_occupation(
    reparacion_service, mock_sheets_repo, mock_cycle_counter, en_reparacion_spool
):
    """Should clear occupation when pausing repair work."""
    tag_spool = en_reparacion_spool.tag_spool
    worker_id = 95

    mock_sheets_repo.get_spool_by_tag.return_value = en_reparacion_spool
    # pausar_reparacion calls build_reparacion_estado("reparacion_pausada", cycle)
    mock_cycle_counter.build_reparacion_estado.return_value = "REPARACION_PAUSADA (Ciclo 1/3)"

    with patch("backend.services.reparacion_service.REPARACIONStateMachine") as MockStateMachine:
        mock_machine = Mock()
        mock_machine.current_state.id = "reparacion_pausada"
        mock_machine.get_state_id.return_value = "reparacion_pausada"
        MockStateMachine.return_value = mock_machine

        result = await reparacion_service.pausar_reparacion(tag_spool, worker_id)

    assert result["success"] is True
    assert "REPARACION_PAUSADA" in result["estado_detalle"]


@pytest.mark.asyncio
async def test_pausar_publishes_sse_event(reparacion_service, mock_sheets_repo, mock_redis_event_service, en_reparacion_spool):
    """Should publish SSE event when pausing repair."""
    tag_spool = en_reparacion_spool.tag_spool
    worker_id = 95

    mock_sheets_repo.get_spool_by_tag.return_value = en_reparacion_spool

    with patch("backend.services.reparacion_service.REPARACIONStateMachine") as MockStateMachine:
        mock_machine = Mock()
        mock_machine.current_state.id = "reparacion_pausada"
        mock_machine.get_state_id.return_value = "reparacion_pausada"
        MockStateMachine.return_value = mock_machine

        result = await reparacion_service.pausar_reparacion(tag_spool, worker_id)

    # Verify SSE event published
    mock_redis_event_service.publish_spool_update.assert_called_once()
    call_kwargs = mock_redis_event_service.publish_spool_update.call_args[1]
    assert call_kwargs["event_type"] == "PAUSAR_REPARACION"
    assert call_kwargs["worker_nombre"] is None  # No longer occupied


# ============================================================================
# COMPLETAR REPARACION TESTS
# ============================================================================


@pytest.mark.asyncio
async def test_completar_sets_pendiente_metrologia(reparacion_service, mock_sheets_repo, en_reparacion_spool):
    """Should set Estado_Detalle to PENDIENTE_METROLOGIA when completing repair."""
    tag_spool = en_reparacion_spool.tag_spool
    worker_id = 95
    worker_nombre = "CP(95)"

    mock_sheets_repo.get_spool_by_tag.return_value = en_reparacion_spool

    with patch("backend.services.reparacion_service.REPARACIONStateMachine") as MockStateMachine:
        mock_machine = Mock()
        mock_machine.current_state.id = "pendiente_metrologia"
        mock_machine.get_state_id.return_value = "pendiente_metrologia"
        MockStateMachine.return_value = mock_machine

        result = await reparacion_service.completar_reparacion(tag_spool, worker_id, worker_nombre)

    assert result["success"] is True
    assert result["estado_detalle"] == "PENDIENTE_METROLOGIA"


@pytest.mark.asyncio
async def test_completar_publishes_sse_event(reparacion_service, mock_sheets_repo, mock_redis_event_service, en_reparacion_spool):
    """Should publish SSE event when completing repair."""
    tag_spool = en_reparacion_spool.tag_spool
    worker_id = 95
    worker_nombre = "CP(95)"

    mock_sheets_repo.get_spool_by_tag.return_value = en_reparacion_spool

    with patch("backend.services.reparacion_service.REPARACIONStateMachine") as MockStateMachine:
        mock_machine = Mock()
        mock_machine.current_state.id = "pendiente_metrologia"
        mock_machine.get_state_id.return_value = "pendiente_metrologia"
        MockStateMachine.return_value = mock_machine

        result = await reparacion_service.completar_reparacion(tag_spool, worker_id, worker_nombre)

    # Verify SSE event published
    mock_redis_event_service.publish_spool_update.assert_called_once()
    call_kwargs = mock_redis_event_service.publish_spool_update.call_args[1]
    assert call_kwargs["event_type"] == "COMPLETAR_REPARACION"


# ============================================================================
# CANCELAR REPARACION TESTS
# ============================================================================


@pytest.mark.asyncio
async def test_cancelar_returns_to_rechazado(reparacion_service, mock_sheets_repo, mock_cycle_counter, en_reparacion_spool):
    """Should return spool to RECHAZADO state when cancelling repair."""
    tag_spool = en_reparacion_spool.tag_spool
    worker_id = 95

    mock_sheets_repo.get_spool_by_tag.return_value = en_reparacion_spool

    with patch("backend.services.reparacion_service.REPARACIONStateMachine") as MockStateMachine:
        mock_machine = Mock()
        mock_machine.current_state.id = "rechazado"
        mock_machine.get_state_id.return_value = "rechazado"
        MockStateMachine.return_value = mock_machine

        result = await reparacion_service.cancelar_reparacion(tag_spool, worker_id)

    assert result["success"] is True
    # Verify build_rechazado_estado called to construct estado_detalle
    mock_cycle_counter.build_rechazado_estado.assert_called_once()


@pytest.mark.asyncio
async def test_cancelar_publishes_sse_event(reparacion_service, mock_sheets_repo, mock_redis_event_service, en_reparacion_spool):
    """Should publish SSE event when cancelling repair."""
    tag_spool = en_reparacion_spool.tag_spool
    worker_id = 95

    mock_sheets_repo.get_spool_by_tag.return_value = en_reparacion_spool

    with patch("backend.services.reparacion_service.REPARACIONStateMachine") as MockStateMachine:
        mock_machine = Mock()
        mock_machine.current_state.id = "rechazado"
        mock_machine.get_state_id.return_value = "rechazado"
        MockStateMachine.return_value = mock_machine

        result = await reparacion_service.cancelar_reparacion(tag_spool, worker_id)

    # Verify SSE event published
    mock_redis_event_service.publish_spool_update.assert_called_once()
    call_kwargs = mock_redis_event_service.publish_spool_update.call_args[1]
    assert call_kwargs["event_type"] == "CANCELAR_REPARACION"


# ============================================================================
# METADATA LOGGING TESTS
# ============================================================================


@pytest.mark.asyncio
async def test_metadata_includes_cycle_info(reparacion_service, mock_sheets_repo, mock_metadata_repo, rechazado_spool):
    """Should include cycle information in metadata events."""
    tag_spool = rechazado_spool.tag_spool
    worker_id = 95
    worker_nome = "CP(95)"

    mock_sheets_repo.get_spool_by_tag.return_value = rechazado_spool

    with patch("backend.services.reparacion_service.REPARACIONStateMachine") as MockStateMachine:
        mock_machine = Mock()
        mock_machine.current_state.id = "en_reparacion"
        mock_machine.get_state_id.return_value = "en_reparacion"
        MockStateMachine.return_value = mock_machine

        result = await reparacion_service.tomar_reparacion(tag_spool, worker_id, worker_nome)

    # Verify metadata logged with cycle info
    mock_metadata_repo.append_event.assert_called_once()
    event = mock_metadata_repo.append_event.call_args[0][0]
    metadata = json.loads(event["metadata_json"])
    assert "cycle" in metadata
    assert metadata["cycle"] == 1
    assert metadata["max_cycles"] == 3


@pytest.mark.asyncio
async def test_metadata_logging_failure_does_not_block(reparacion_service, mock_sheets_repo, mock_metadata_repo, rechazado_spool):
    """Should continue operation even if metadata logging fails (best-effort pattern)."""
    tag_spool = rechazado_spool.tag_spool
    worker_id = 95
    worker_nombre = "CP(95)"

    mock_sheets_repo.get_spool_by_tag.return_value = rechazado_spool
    mock_metadata_repo.append_event.side_effect = Exception("Sheets API error")

    with patch("backend.services.reparacion_service.REPARACIONStateMachine") as MockStateMachine:
        mock_machine = Mock()
        mock_machine.current_state.id = "en_reparacion"
        mock_machine.get_state_id.return_value = "en_reparacion"
        MockStateMachine.return_value = mock_machine

        # Should NOT raise exception despite metadata failure
        result = await reparacion_service.tomar_reparacion(tag_spool, worker_id, worker_nombre)

    assert result["success"] is True
