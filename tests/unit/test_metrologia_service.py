"""
Unit tests for MetrologiaService.

Tests instant completion workflow with APROBADO/RECHAZADO outcomes.
"""
import pytest
from unittest.mock import Mock, patch
from datetime import date

from backend.services.metrologia_service import MetrologiaService
from backend.services.validation_service import ValidationService
from backend.models.spool import Spool
from backend.exceptions import (
    SpoolNoEncontradoError,
    DependenciasNoSatisfechasError,
    OperacionYaCompletadaError,
    SpoolOccupiedError
)


@pytest.fixture
def mock_sheets_repo():
    """Mock SheetsRepository."""
    repo = Mock()
    repo.find_row_by_column_value = Mock(return_value=10)
    repo.update_cell_by_column_name = Mock()
    return repo


@pytest.fixture
def mock_metadata_repo():
    """Mock MetadataRepository."""
    repo = Mock()
    repo.append_event = Mock()
    return repo


@pytest.fixture
def mock_redis_event_service():
    """Mock RedisEventService."""
    service = Mock()
    service.publish_state_change = Mock()
    return service


@pytest.fixture
def validation_service():
    """Real ValidationService without role_service for testing."""
    return ValidationService(role_service=None)


@pytest.fixture
def metrologia_service(validation_service, mock_sheets_repo, mock_metadata_repo, mock_redis_event_service):
    """MetrologiaService with mocked dependencies."""
    return MetrologiaService(
        validation_service=validation_service,
        sheets_repository=mock_sheets_repo,
        metadata_repository=mock_metadata_repo,
        redis_event_service=mock_redis_event_service
    )


@pytest.fixture
def ready_spool():
    """Spool ready for metrología (ARM + SOLD complete, not occupied)."""
    return Spool(
        tag_spool="TEST-001",
        fecha_materiales=date(2026, 1, 20),
        fecha_armado=date(2026, 1, 22),
        fecha_soldadura=date(2026, 1, 25),
        fecha_qc_metrologia=None,
        armador="MR(93)",
        soldador="JP(94)",
        ocupado_por=None
    )


def test_validar_puede_completar_metrologia_success(validation_service, ready_spool):
    """Test validation passes for ready spool."""
    # Should not raise exception
    validation_service.validar_puede_completar_metrologia(ready_spool, worker_id=95)


def test_validar_puede_completar_metrologia_arm_not_completed(validation_service):
    """Test validation fails if ARM not completed."""
    spool = Spool(
        tag_spool="TEST-001",
        fecha_materiales=date(2026, 1, 20),
        fecha_armado=None,  # ARM not completed
        fecha_soldadura=date(2026, 1, 25),
        fecha_qc_metrologia=None,
        ocupado_por=None
    )

    with pytest.raises(DependenciasNoSatisfechasError) as exc:
        validation_service.validar_puede_completar_metrologia(spool, worker_id=95)

    assert "ARM completado" in str(exc.value)


def test_validar_puede_completar_metrologia_sold_not_completed(validation_service):
    """Test validation fails if SOLD not completed."""
    spool = Spool(
        tag_spool="TEST-001",
        fecha_materiales=date(2026, 1, 20),
        fecha_armado=date(2026, 1, 22),
        fecha_soldadura=None,  # SOLD not completed
        fecha_qc_metrologia=None,
        ocupado_por=None
    )

    with pytest.raises(DependenciasNoSatisfechasError) as exc:
        validation_service.validar_puede_completar_metrologia(spool, worker_id=95)

    assert "SOLD completado" in str(exc.value)


def test_validar_puede_completar_metrologia_already_completed(validation_service):
    """Test validation fails if metrología already completed."""
    spool = Spool(
        tag_spool="TEST-001",
        fecha_materiales=date(2026, 1, 20),
        fecha_armado=date(2026, 1, 22),
        fecha_soldadura=date(2026, 1, 25),
        fecha_qc_metrologia=date(2026, 1, 27),  # Already completed
        ocupado_por=None
    )

    with pytest.raises(OperacionYaCompletadaError) as exc:
        validation_service.validar_puede_completar_metrologia(spool, worker_id=95)

    assert "METROLOGIA" in str(exc.value)


def test_validar_puede_completar_metrologia_spool_occupied(validation_service):
    """Test validation fails if spool is occupied."""
    spool = Spool(
        tag_spool="TEST-001",
        fecha_materiales=date(2026, 1, 20),
        fecha_armado=date(2026, 1, 22),
        fecha_soldadura=date(2026, 1, 25),
        fecha_qc_metrologia=None,
        ocupado_por="MR(93)"  # Occupied by another worker
    )

    with pytest.raises(SpoolOccupiedError) as exc:
        validation_service.validar_puede_completar_metrologia(spool, worker_id=95)

    assert "ocupado" in str(exc.value).lower()
    assert "MR(93)" in str(exc.value)


def test_completar_aprobado_success(metrologia_service, mock_sheets_repo, ready_spool):
    """Test successful APROBADO completion."""
    mock_sheets_repo.get_spool_by_tag = Mock(return_value=ready_spool)

    result = metrologia_service.completar(
        tag_spool="TEST-001",
        worker_id=95,
        worker_nombre="CP(95)",
        resultado="APROBADO"
    )

    # Verify success response
    assert result["success"] is True
    assert result["resultado"] == "APROBADO"
    assert result["tag_spool"] == "TEST-001"

    # Verify Sheets update was called
    mock_sheets_repo.update_cell_by_column_name.assert_called_once()


def test_completar_rechazado_success(metrologia_service, mock_sheets_repo, ready_spool):
    """Test successful RECHAZADO completion."""
    mock_sheets_repo.get_spool_by_tag = Mock(return_value=ready_spool)

    result = metrologia_service.completar(
        tag_spool="TEST-001",
        worker_id=95,
        worker_nombre="CP(95)",
        resultado="RECHAZADO"
    )

    # Verify success response
    assert result["success"] is True
    assert result["resultado"] == "RECHAZADO"
    assert result["tag_spool"] == "TEST-001"

    # Verify Sheets update was called
    mock_sheets_repo.update_cell_by_column_name.assert_called_once()


def test_completar_spool_not_found(metrologia_service, mock_sheets_repo):
    """Test error when spool doesn't exist."""
    mock_sheets_repo.get_spool_by_tag = Mock(return_value=None)

    with pytest.raises(SpoolNoEncontradoError):
        metrologia_service.completar(
            tag_spool="INVALID",
            worker_id=95,
            worker_nombre="CP(95)",
            resultado="APROBADO"
        )


def test_completar_logs_metadata_event(metrologia_service, mock_sheets_repo, mock_metadata_repo, ready_spool):
    """Test that metadata event is logged on completion."""
    mock_sheets_repo.get_spool_by_tag = Mock(return_value=ready_spool)

    metrologia_service.completar(
        tag_spool="TEST-001",
        worker_id=95,
        worker_nombre="CP(95)",
        resultado="APROBADO"
    )

    # Verify metadata was logged
    mock_metadata_repo.append_event.assert_called_once()
    event = mock_metadata_repo.append_event.call_args[0][0]
    assert event["tag_spool"] == "TEST-001"
    assert event["worker_id"] == 95
    assert event["operacion"] == "METROLOGIA"
    assert "APROBADO" in event["metadata_json"]


def test_completar_publishes_sse_event(metrologia_service, mock_sheets_repo, mock_redis_event_service, ready_spool):
    """Test that SSE event is published on completion."""
    mock_sheets_repo.get_spool_by_tag = Mock(return_value=ready_spool)

    metrologia_service.completar(
        tag_spool="TEST-001",
        worker_id=95,
        worker_nombre="CP(95)",
        resultado="RECHAZADO"
    )

    # Verify SSE event was published
    mock_redis_event_service.publish_state_change.assert_called_once()
    call_args = mock_redis_event_service.publish_state_change.call_args
    assert call_args[1]["data"]["resultado"] == "RECHAZADO"


def test_completar_continues_on_metadata_failure(metrologia_service, mock_sheets_repo, mock_metadata_repo, ready_spool):
    """Test that operation continues even if metadata logging fails (best-effort)."""
    mock_sheets_repo.get_spool_by_tag = Mock(return_value=ready_spool)
    mock_metadata_repo.append_event = Mock(side_effect=Exception("Metadata API error"))

    # Should still succeed despite metadata failure
    result = metrologia_service.completar(
        tag_spool="TEST-001",
        worker_id=95,
        worker_nombre="CP(95)",
        resultado="APROBADO"
    )

    assert result["success"] is True


def test_completar_continues_on_sse_failure(metrologia_service, mock_sheets_repo, mock_redis_event_service, ready_spool):
    """Test that operation continues even if SSE publishing fails (best-effort)."""
    mock_sheets_repo.get_spool_by_tag = Mock(return_value=ready_spool)
    mock_redis_event_service.publish_state_change = Mock(side_effect=Exception("Redis error"))

    # Should still succeed despite SSE failure
    result = metrologia_service.completar(
        tag_spool="TEST-001",
        worker_id=95,
        worker_nombre="CP(95)",
        resultado="APROBADO"
    )

    assert result["success"] is True
