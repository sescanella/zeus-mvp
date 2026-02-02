"""
Unit tests for EstadoDetalleService supervisor override detection (Phase 6).

Tests automatic detection and logging of manual Estado_Detalle changes by supervisors.
"""

import pytest
from unittest.mock import Mock
from datetime import date, datetime
import json

from backend.services.estado_detalle_service import EstadoDetalleService
from backend.repositories.sheets_repository import SheetsRepository
from backend.repositories.metadata_repository import MetadataRepository
from backend.models.spool import Spool
from backend.models.metadata import MetadataEvent, EventoTipo, Accion


# ============================================================================
# FIXTURES
# ============================================================================


@pytest.fixture
def mock_sheets_repo():
    """Mock SheetsRepository."""
    repo = Mock(spec=SheetsRepository)
    return repo


@pytest.fixture
def mock_metadata_repo():
    """Mock MetadataRepository."""
    repo = Mock(spec=MetadataRepository)
    repo.get_events_by_spool.return_value = []
    repo.append_event.return_value = None
    return repo


@pytest.fixture
def estado_detalle_service(mock_sheets_repo, mock_metadata_repo):
    """EstadoDetalleService with mocked dependencies."""
    return EstadoDetalleService(
        sheets_repo=mock_sheets_repo,
        metadata_repo=mock_metadata_repo
    )


# ============================================================================
# OVERRIDE DETECTION TESTS
# ============================================================================


def test_detects_bloqueado_to_rechazado_change(estado_detalle_service, mock_sheets_repo, mock_metadata_repo):
    """Should detect when BLOQUEADO spool is manually changed to RECHAZADO."""
    tag_spool = "OVERRIDE-001"

    # Mock current state: RECHAZADO (after supervisor override)
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
    last_event = MetadataEvent(
        id="event-123",
        timestamp=datetime(2026, 1, 27, 15, 0, 0),
        evento_tipo=EventoTipo.CANCELAR_METROLOGIA,
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


def test_ignores_normal_transitions(estado_detalle_service, mock_sheets_repo, mock_metadata_repo):
    """Should NOT detect override for normal state transitions."""
    tag_spool = "NORMAL-001"

    # Mock current state: EN_REPARACION (normal transition)
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

    # Mock last event: was RECHAZADO (normal TOMAR transition)
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


def test_logs_supervisor_override_event(estado_detalle_service, mock_sheets_repo, mock_metadata_repo):
    """Should log SUPERVISOR_OVERRIDE event to Metadata when detected."""
    tag_spool = "OVERRIDE-002"

    # Mock BLOQUEADO → RECHAZADO transition
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

    last_event = MetadataEvent(
        id="event-789",
        timestamp=datetime(2026, 1, 27, 15, 0, 0),
        evento_tipo=EventoTipo.CANCELAR_METROLOGIA,
        tag_spool=tag_spool,
        worker_id=91,
        worker_nombre="Supervisor(91)",
        operacion="METROLOGIA",
        accion=Accion.CANCELAR,
        fecha_operacion="27-01-2026",
        metadata_json=json.dumps({"estado_detalle": "BLOQUEADO - Contactar supervisor"})
    )
    mock_metadata_repo.get_events_by_spool.return_value = [last_event]

    # Detect and log override
    result = estado_detalle_service.detect_supervisor_override(tag_spool)

    # Verify SUPERVISOR_OVERRIDE event logged
    assert mock_metadata_repo.append_event.called
    event_dict = mock_metadata_repo.append_event.call_args[0][0]
    assert event_dict["evento_tipo"] == "SUPERVISOR_OVERRIDE"
    assert event_dict["tag_spool"] == tag_spool
    assert event_dict["operacion"] == "REPARACION"
    assert event_dict["accion"] == "OVERRIDE"


def test_override_event_includes_metadata(estado_detalle_service, mock_sheets_repo, mock_metadata_repo):
    """Should include previous/current estado in metadata_json of override event."""
    tag_spool = "OVERRIDE-003"

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
        estado_detalle="RECHAZADO (Ciclo 1/3) - Pendiente reparación",
        version=16
    )
    mock_sheets_repo.get_spool_by_tag.return_value = current_spool

    last_event = MetadataEvent(
        id="event-abc",
        timestamp=datetime(2026, 1, 27, 15, 0, 0),
        evento_tipo=EventoTipo.CANCELAR_METROLOGIA,
        tag_spool=tag_spool,
        worker_id=91,
        worker_nombre="Supervisor(91)",
        operacion="METROLOGIA",
        accion=Accion.CANCELAR,
        fecha_operacion="27-01-2026",
        metadata_json=json.dumps({"estado_detalle": "BLOQUEADO - Contactar supervisor"})
    )
    mock_metadata_repo.get_events_by_spool.return_value = [last_event]

    result = estado_detalle_service.detect_supervisor_override(tag_spool)

    # Verify metadata_json contains override details
    event_dict = mock_metadata_repo.append_event.call_args[0][0]
    metadata = json.loads(event_dict["metadata_json"])
    assert "previous_estado" in metadata
    assert "new_estado" in metadata
    assert "BLOQUEADO" in metadata["previous_estado"]
    assert "RECHAZADO" in metadata["new_estado"]
    assert metadata["override_type"] == "BLOQUEADO_TO_RECHAZADO"


def test_system_worker_id_zero(estado_detalle_service, mock_sheets_repo, mock_metadata_repo):
    """Should use worker_id=0 for system events (SUPERVISOR_OVERRIDE)."""
    tag_spool = "OVERRIDE-004"

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

    last_event = MetadataEvent(
        id="event-def",
        timestamp=datetime(2026, 1, 27, 15, 0, 0),
        evento_tipo=EventoTipo.CANCELAR_METROLOGIA,
        tag_spool=tag_spool,
        worker_id=91,
        worker_nombre="Supervisor(91)",
        operacion="METROLOGIA",
        accion=Accion.CANCELAR,
        fecha_operacion="27-01-2026",
        metadata_json=json.dumps({"estado_detalle": "BLOQUEADO - Contactar supervisor"})
    )
    mock_metadata_repo.get_events_by_spool.return_value = [last_event]

    result = estado_detalle_service.detect_supervisor_override(tag_spool)

    # Verify worker_id=0 and worker_nombre=SYSTEM
    event_dict = mock_metadata_repo.append_event.call_args[0][0]
    assert event_dict["worker_id"] == 0
    assert event_dict["worker_nombre"] == "SYSTEM"


# ============================================================================
# EDGE CASE TESTS
# ============================================================================


def test_no_previous_event(estado_detalle_service, mock_sheets_repo, mock_metadata_repo):
    """Should return None if no previous events found for spool."""
    tag_spool = "NEW-SPOOL-001"

    current_spool = Spool(
        tag_spool=tag_spool,
        fecha_materiales=date(2026, 1, 20),
        fecha_armado=date(2026, 1, 22),
        fecha_soldadura=date(2026, 1, 25),
        fecha_qc_metrologia=None,
        armador="MR(93)",
        soldador="JP(94)",
        ocupado_por=None,
        fecha_ocupacion=None,
        estado_detalle="RECHAZADO (Ciclo 1/3) - Pendiente reparación",
        version=8
    )
    mock_sheets_repo.get_spool_by_tag.return_value = current_spool

    # No previous events
    mock_metadata_repo.get_events_by_spool.return_value = []

    result = estado_detalle_service.detect_supervisor_override(tag_spool)

    assert result is None
    assert not mock_metadata_repo.append_event.called


def test_spool_not_found(estado_detalle_service, mock_sheets_repo, mock_metadata_repo):
    """Should return None if spool doesn't exist."""
    tag_spool = "NONEXISTENT-001"

    mock_sheets_repo.get_spool_by_tag.return_value = None

    result = estado_detalle_service.detect_supervisor_override(tag_spool)

    assert result is None
    assert not mock_metadata_repo.append_event.called


def test_multiple_overrides(estado_detalle_service, mock_sheets_repo, mock_metadata_repo):
    """Should detect multiple overrides for same spool."""
    tag_spool = "OVERRIDE-MULTI"

    # First override detection
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

    first_bloqueado_event = MetadataEvent(
        id="event-first",
        timestamp=datetime(2026, 1, 27, 15, 0, 0),
        evento_tipo=EventoTipo.CANCELAR_METROLOGIA,
        tag_spool=tag_spool,
        worker_id=91,
        worker_nombre="Supervisor(91)",
        operacion="METROLOGIA",
        accion=Accion.CANCELAR,
        fecha_operacion="27-01-2026",
        metadata_json=json.dumps({"estado_detalle": "BLOQUEADO - Contactar supervisor"})
    )
    mock_metadata_repo.get_events_by_spool.return_value = [first_bloqueado_event]

    result1 = estado_detalle_service.detect_supervisor_override(tag_spool)
    assert result1 is not None
    assert result1["detected"] is True

    # Second override (spool blocked again, supervisor overrides again)
    # Mock new state showing another override happened
    second_bloqueado_event = MetadataEvent(
        id="event-second",
        timestamp=datetime(2026, 1, 28, 16, 0, 0),
        evento_tipo=EventoTipo.CANCELAR_METROLOGIA,
        tag_spool=tag_spool,
        worker_id=91,
        worker_nombre="Supervisor(91)",
        operacion="METROLOGIA",
        accion=Accion.CANCELAR,
        fecha_operacion="28-01-2026",
        metadata_json=json.dumps({"estado_detalle": "BLOQUEADO - Contactar supervisor"})
    )
    mock_metadata_repo.get_events_by_spool.return_value = [first_bloqueado_event, second_bloqueado_event]

    result2 = estado_detalle_service.detect_supervisor_override(tag_spool)
    assert result2 is not None
    assert result2["detected"] is True

    # Verify both overrides logged
    assert mock_metadata_repo.append_event.call_count == 2


def test_logging_failure_returns_error(estado_detalle_service, mock_sheets_repo, mock_metadata_repo):
    """Should return detection result even if logging fails."""
    tag_spool = "OVERRIDE-LOG-FAIL"

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

    last_event = MetadataEvent(
        id="event-fail",
        timestamp=datetime(2026, 1, 27, 15, 0, 0),
        evento_tipo=EventoTipo.CANCELAR_METROLOGIA,
        tag_spool=tag_spool,
        worker_id=91,
        worker_nombre="Supervisor(91)",
        operacion="METROLOGIA",
        accion=Accion.CANCELAR,
        fecha_operacion="27-01-2026",
        metadata_json=json.dumps({"estado_detalle": "BLOQUEADO - Contactar supervisor"})
    )
    mock_metadata_repo.get_events_by_spool.return_value = [last_event]

    # Mock append_event to fail
    mock_metadata_repo.append_event.side_effect = Exception("Sheets API error")

    result = estado_detalle_service.detect_supervisor_override(tag_spool)

    # Should still return detection result
    assert result is not None
    assert result["detected"] is True
    assert result["event_id"] is None
    assert "error" in result


# ============================================================================
# BATCH CHECK TESTS
# ============================================================================


def test_batch_check_returns_only_overrides(estado_detalle_service, mock_sheets_repo, mock_metadata_repo):
    """Should return only spools with detected overrides in batch check."""
    tag_spools = ["BATCH-001", "BATCH-002", "BATCH-003"]

    # Mock BATCH-001: has override
    override_spool = Spool(
        tag_spool="BATCH-001",
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

    # Mock BATCH-002: normal transition
    normal_spool = Spool(
        tag_spool="BATCH-002",
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

    # Mock BATCH-003: no events
    no_events_spool = Spool(
        tag_spool="BATCH-003",
        fecha_materiales=date(2026, 1, 20),
        fecha_armado=date(2026, 1, 22),
        fecha_soldadura=date(2026, 1, 25),
        fecha_qc_metrologia=None,
        armador="MR(93)",
        soldador="JP(94)",
        ocupado_por=None,
        fecha_ocupacion=None,
        estado_detalle="RECHAZADO (Ciclo 1/3) - Pendiente reparación",
        version=8
    )

    def get_spool_side_effect(tag):
        if tag == "BATCH-001":
            return override_spool
        elif tag == "BATCH-002":
            return normal_spool
        elif tag == "BATCH-003":
            return no_events_spool
        return None

    mock_sheets_repo.get_spool_by_tag.side_effect = get_spool_side_effect

    # Mock events
    bloqueado_event = MetadataEvent(
        id="batch-event-1",
        timestamp=datetime(2026, 1, 27, 15, 0, 0),
        evento_tipo=EventoTipo.CANCELAR_METROLOGIA,
        tag_spool="BATCH-001",
        worker_id=91,
        worker_nombre="Supervisor(91)",
        operacion="METROLOGIA",
        accion=Accion.CANCELAR,
        fecha_operacion="27-01-2026",
        metadata_json=json.dumps({"estado_detalle": "BLOQUEADO - Contactar supervisor"})
    )

    normal_event = MetadataEvent(
        id="batch-event-2",
        timestamp=datetime(2026, 1, 28, 10, 0, 0),
        evento_tipo=EventoTipo.INICIAR_METROLOGIA,
        tag_spool="BATCH-002",
        worker_id=95,
        worker_nombre="CP(95)",
        operacion="REPARACION",
        accion=Accion.INICIAR,
        fecha_operacion="28-01-2026",
        metadata_json=json.dumps({"estado_detalle": "RECHAZADO (Ciclo 1/3)"})
    )

    def get_events_side_effect(tag):
        if tag == "BATCH-001":
            return [bloqueado_event]
        elif tag == "BATCH-002":
            return [normal_event]
        elif tag == "BATCH-003":
            return []
        return []

    mock_metadata_repo.get_events_by_spool.side_effect = get_events_side_effect

    # Batch check
    overrides = estado_detalle_service.check_spools_for_overrides(tag_spools)

    # Should only return BATCH-001 (has override)
    assert len(overrides) == 1
    assert overrides[0]["detected"] is True
    assert overrides[0]["tag_spool"] == "BATCH-001"
