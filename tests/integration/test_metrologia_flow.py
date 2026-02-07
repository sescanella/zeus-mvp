"""
Integration tests for metrología instant completion workflow.

Tests v3.0 Phase 5 metrología features:
- Binary resultado completion (APROBADO/RECHAZADO)
- Prerequisite validation (ARM + SOLD complete, not occupied)
- Estado_Detalle display updates
- Metadata event logging
- Empty state handling

These are integration tests using mocked dependencies to verify
the full orchestration flow through MetrologiaService.
"""

import pytest
from datetime import date
from unittest.mock import AsyncMock, Mock, patch

from backend.services.metrologia_service import MetrologiaService
from backend.services.validation_service import ValidationService
from backend.repositories.sheets_repository import SheetsRepository
from backend.repositories.metadata_repository import MetadataRepository
from backend.models.spool import Spool
from backend.exceptions import (
    SpoolNoEncontradoError,
    DependenciasNoSatisfechasError,
    OperacionYaCompletadaError,
    SpoolOccupiedError,
    RolNoAutorizadoError
)


# ============================================================================
# FIXTURES
# ============================================================================


@pytest.fixture
def mock_sheets_repo():
    """Mock SheetsRepository for testing (MetrologiaService uses batch_update_by_column_name)."""
    repo = Mock(spec=SheetsRepository)
    repo.find_row_by_column_value.return_value = 2
    repo.update_cell_by_column_name.return_value = None
    repo.batch_update_by_column_name.return_value = None
    return repo


@pytest.fixture
def mock_metadata_repo():
    """Mock MetadataRepository for testing."""
    repo = Mock(spec=MetadataRepository)
    repo.append_event.return_value = None
    return repo


@pytest.fixture
def validation_service():
    """Real ValidationService for prerequisite validation."""
    return ValidationService(role_service=None)


@pytest.fixture
def metrologia_service(validation_service, mock_sheets_repo, mock_metadata_repo):
    """MetrologiaService with mocked dependencies."""
    return MetrologiaService(
        validation_service=validation_service,
        sheets_repository=mock_sheets_repo,
        metadata_repository=mock_metadata_repo
    )


@pytest.fixture
def ready_spool():
    """Spool ready for metrología (ARM + SOLD complete, not occupied)."""
    return Spool(
        tag_spool="INTEGRATION-001",
        fecha_materiales=date(2026, 1, 20),
        fecha_armado=date(2026, 1, 22),
        fecha_soldadura=date(2026, 1, 25),
        fecha_qc_metrologia=None,
        armador="MR(93)",
        soldador="JP(94)",
        ocupado_por=None,
        fecha_ocupacion=None,
        version=5
    )


@pytest.fixture
def occupied_spool():
    """Spool currently occupied by another worker."""
    return Spool(
        tag_spool="INTEGRATION-002",
        fecha_materiales=date(2026, 1, 20),
        fecha_armado=date(2026, 1, 22),
        fecha_soldadura=date(2026, 1, 25),
        fecha_qc_metrologia=None,
        armador="MR(93)",
        soldador="JP(94)",
        ocupado_por="MR(93):lock-token-123",
        fecha_ocupacion="27/01/2026",  # String format DD/MM/YYYY
        version=7
    )


@pytest.fixture
def arm_incomplete_spool():
    """Spool with SOLD complete but ARM not complete."""
    return Spool(
        tag_spool="INTEGRATION-003",
        fecha_materiales=date(2026, 1, 20),
        fecha_armado=None,  # ARM not complete
        fecha_soldadura=date(2026, 1, 25),
        fecha_qc_metrologia=None,
        armador=None,
        soldador="JP(94)",
        ocupado_por=None,
        fecha_ocupacion=None,
        version=3
    )


@pytest.fixture
def already_inspected_spool():
    """Spool already inspected (fecha_qc_metrologia present)."""
    return Spool(
        tag_spool="INTEGRATION-004",
        fecha_materiales=date(2026, 1, 20),
        fecha_armado=date(2026, 1, 22),
        fecha_soldadura=date(2026, 1, 25),
        fecha_qc_metrologia=date(2026, 1, 27),  # Already inspected
        armador="MR(93)",
        soldador="JP(94)",
        ocupado_por=None,
        fecha_ocupacion=None,
        version=8
    )


# ============================================================================
# HAPPY PATH TESTS
# ============================================================================


@pytest.mark.asyncio
async def test_completar_aprobado_success(metrologia_service, mock_sheets_repo, ready_spool):
    """Test successful APROBADO completion flow."""
    # Arrange
    mock_sheets_repo.get_spool_by_tag.return_value = ready_spool

    # Act
    result = await metrologia_service.completar(
        tag_spool="INTEGRATION-001",
        worker_id=95,
        worker_nombre="CP(95)",
        resultado="APROBADO"
    )

    # Assert response
    assert result["success"] is True
    assert result["resultado"] == "APROBADO"
    assert result["tag_spool"] == "INTEGRATION-001"
    assert "aprobado" in result["message"].lower()

    # Verify Fecha_QC_Metrología was updated (Metrologia machine uses batch_update_by_column_name)
    mock_sheets_repo.batch_update_by_column_name.assert_called()
    call_args = mock_sheets_repo.batch_update_by_column_name.call_args
    updates = call_args[1]["updates"]
    column_names = [u["column_name"] for u in updates]
    assert "Fecha_QC_Metrología" in column_names


@pytest.mark.asyncio
async def test_completar_rechazado_success(metrologia_service, mock_sheets_repo, ready_spool):
    """Test successful RECHAZADO completion flow."""
    # Arrange
    mock_sheets_repo.get_spool_by_tag.return_value = ready_spool

    # Act
    result = await metrologia_service.completar(
        tag_spool="INTEGRATION-001",
        worker_id=95,
        worker_nombre="CP(95)",
        resultado="RECHAZADO"
    )

    # Assert response
    assert result["success"] is True
    assert result["resultado"] == "RECHAZADO"
    assert result["tag_spool"] == "INTEGRATION-001"
    assert "rechazado" in result["message"].lower()

    # Verify Fecha_QC_Metrología was updated (Metrologia machine uses batch_update_by_column_name)
    mock_sheets_repo.batch_update_by_column_name.assert_called()


@pytest.mark.asyncio
async def test_completar_logs_metadata_event(metrologia_service, mock_sheets_repo, mock_metadata_repo, ready_spool):
    """Test that metadata event is logged with resultado."""
    # Arrange
    mock_sheets_repo.get_spool_by_tag.return_value = ready_spool

    # Act
    await metrologia_service.completar(
        tag_spool="INTEGRATION-001",
        worker_id=95,
        worker_nombre="CP(95)",
        resultado="APROBADO"
    )

    # Assert metadata was logged
    mock_metadata_repo.append_event.assert_called_once()
    event = mock_metadata_repo.append_event.call_args[0][0]
    assert event["tag_spool"] == "INTEGRATION-001"
    assert event["worker_id"] == 95
    assert event["worker_nombre"] == "CP(95)"
    assert event["operacion"] == "METROLOGIA"
    assert event["accion"] == "COMPLETAR"
    assert "APROBADO" in event["metadata_json"]


# SSE event test removed - single-user mode no longer uses Redis/SSE


# ============================================================================
# VALIDATION FAILURE TESTS
# ============================================================================


@pytest.mark.asyncio
async def test_completar_spool_not_found(metrologia_service, mock_sheets_repo):
    """Test error when spool doesn't exist."""
    # Arrange
    mock_sheets_repo.get_spool_by_tag.return_value = None

    # Act & Assert
    with pytest.raises(SpoolNoEncontradoError) as exc:
        await metrologia_service.completar(
            tag_spool="NONEXISTENT",
            worker_id=95,
            worker_nombre="CP(95)",
            resultado="APROBADO"
        )

    assert "NONEXISTENT" in str(exc.value)


@pytest.mark.asyncio
async def test_completar_arm_not_complete(metrologia_service, mock_sheets_repo, arm_incomplete_spool):
    """Test error when ARM not completed."""
    # Arrange
    mock_sheets_repo.get_spool_by_tag.return_value = arm_incomplete_spool

    # Act & Assert
    with pytest.raises(DependenciasNoSatisfechasError) as exc:
        await metrologia_service.completar(
            tag_spool="INTEGRATION-003",
            worker_id=95,
            worker_nombre="CP(95)",
            resultado="APROBADO"
        )

    assert "ARM completado" in str(exc.value)


@pytest.mark.asyncio
async def test_completar_sold_not_complete(metrologia_service, mock_sheets_repo):
    """Test error when SOLD not completed."""
    # Arrange
    sold_incomplete_spool = Spool(
        tag_spool="INTEGRATION-005",
        fecha_materiales=date(2026, 1, 20),
        fecha_armado=date(2026, 1, 22),
        fecha_soldadura=None,  # SOLD not complete
        fecha_qc_metrologia=None,
        armador="MR(93)",
        soldador=None,
        ocupado_por=None
    )
    mock_sheets_repo.get_spool_by_tag.return_value = sold_incomplete_spool

    # Act & Assert
    with pytest.raises(DependenciasNoSatisfechasError) as exc:
        await metrologia_service.completar(
            tag_spool="INTEGRATION-005",
            worker_id=95,
            worker_nombre="CP(95)",
            resultado="APROBADO"
        )

    assert "SOLD completado" in str(exc.value)


@pytest.mark.asyncio
async def test_completar_already_inspected(metrologia_service, mock_sheets_repo, already_inspected_spool):
    """Test error when metrología already completed."""
    # Arrange
    mock_sheets_repo.get_spool_by_tag.return_value = already_inspected_spool

    # Act & Assert
    with pytest.raises(OperacionYaCompletadaError) as exc:
        await metrologia_service.completar(
            tag_spool="INTEGRATION-004",
            worker_id=95,
            worker_nombre="CP(95)",
            resultado="APROBADO"
        )

    assert "METROLOGIA" in str(exc.value)


@pytest.mark.asyncio
async def test_completar_spool_occupied(metrologia_service, mock_sheets_repo, occupied_spool):
    """Test error when spool is occupied (409 conflict)."""
    # Arrange
    mock_sheets_repo.get_spool_by_tag.return_value = occupied_spool

    # Act & Assert
    with pytest.raises(SpoolOccupiedError) as exc:
        await metrologia_service.completar(
            tag_spool="INTEGRATION-002",
            worker_id=95,
            worker_nombre="CP(95)",
            resultado="APROBADO"
        )

    assert "ocupado" in str(exc.value).lower()


# ============================================================================
# BEST-EFFORT ERROR HANDLING TESTS
# ============================================================================


@pytest.mark.asyncio
async def test_completar_continues_on_metadata_failure(metrologia_service, mock_sheets_repo, mock_metadata_repo, ready_spool):
    """Test that operation continues even if metadata logging fails (best-effort)."""
    # Arrange
    mock_sheets_repo.get_spool_by_tag.return_value = ready_spool
    mock_metadata_repo.append_event.side_effect = Exception("Metadata API error")

    # Act
    result = await metrologia_service.completar(
        tag_spool="INTEGRATION-001",
        worker_id=95,
        worker_nombre="CP(95)",
        resultado="APROBADO"
    )

    # Assert - should still succeed
    assert result["success"] is True
    assert result["resultado"] == "APROBADO"


# SSE failure test removed - single-user mode no longer uses Redis/SSE


# ============================================================================
# EMPTY STATE TESTS
# ============================================================================


def test_spool_prerequisites_for_metrologia(occupied_spool, arm_incomplete_spool):
    """
    Test that spool fixtures correctly represent filtering criteria.

    These are data validation tests - actual filtering happens in
    SheetsRepository.get_spools_for_metrologia() which is tested separately.
    """
    # Occupied spools should be filtered out
    assert occupied_spool.ocupado_por is not None

    # ARM incomplete spools should be filtered out
    assert arm_incomplete_spool.fecha_armado is None

    # Both should have fecha_materiales (base requirement)
    assert occupied_spool.fecha_materiales is not None
    assert arm_incomplete_spool.fecha_materiales is not None
