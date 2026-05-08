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
from backend.services.cycle_counter_service import CycleCounterService
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
    # T-112: state machine reads Estado_Detalle to extract current cycle on RECHAZADO
    repo.get_cell_value.return_value = ""
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
def cycle_counter():
    """Real CycleCounterService for testing (T-112: now required by MetrologiaService)."""
    return CycleCounterService()


@pytest.fixture
def metrologia_service(validation_service, mock_sheets_repo, mock_metadata_repo, cycle_counter):
    """MetrologiaService with mocked dependencies."""
    return MetrologiaService(
        validation_service=validation_service,
        sheets_repository=mock_sheets_repo,
        metadata_repository=mock_metadata_repo,
        cycle_counter=cycle_counter
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


# ============================================================================
# T-112 REGRESSION — 3 consecutive RECHAZADOs activate BLOQUEADO branch
# ============================================================================


@pytest.mark.asyncio
async def test_t112_three_consecutive_rechazados_reach_bloqueado(
    metrologia_service, mock_sheets_repo, ready_spool
):
    """T-112: 3 consecutive RECHAZADOs through MetrologiaService transition spool to BLOQUEADO.

    Simulates the end-to-end metrología side of the cycle: each rejection reads the
    Estado_Detalle that was written by the previous rejection. The reparación leg
    (TOMAR/CANCELAR) is mocked away because it preserves Estado_Detalle and is
    covered by separate tests in test_reparacion_service.py — what matters here is
    that Metrología's own callback now reads + increments + persists the cycle,
    which was the dead branch before T-112.
    """
    mock_sheets_repo.get_spool_by_tag.return_value = ready_spool

    # Simulate Sheets persistence: get_cell_value returns whatever was written last.
    written_estados = [""]  # Initial state: no cycle info

    def fake_get_cell_value(**kwargs):
        return written_estados[-1]

    def fake_batch_update(**kwargs):
        for update in kwargs.get("updates", []):
            if update["column_name"] == "Estado_Detalle":
                written_estados.append(update["value"])

    mock_sheets_repo.get_cell_value.side_effect = fake_get_cell_value
    mock_sheets_repo.batch_update_by_column_name.side_effect = fake_batch_update

    # Rejection 1
    await metrologia_service.completar(
        tag_spool="INTEGRATION-001",
        worker_id=95,
        worker_nombre="CP(95)",
        resultado="RECHAZADO"
    )
    assert "Ciclo 1/3" in written_estados[-1]

    # Rejection 2
    await metrologia_service.completar(
        tag_spool="INTEGRATION-001",
        worker_id=95,
        worker_nombre="CP(95)",
        resultado="RECHAZADO"
    )
    assert "Ciclo 2/3" in written_estados[-1]

    # Rejection 3 → BLOQUEADO
    await metrologia_service.completar(
        tag_spool="INTEGRATION-001",
        worker_id=95,
        worker_nombre="CP(95)",
        resultado="RECHAZADO"
    )
    assert "BLOQUEADO" in written_estados[-1]
    assert "supervisor" in written_estados[-1].lower()


@pytest.mark.asyncio
async def test_t112_bloqueado_blocks_tomar_reparacion(mock_sheets_repo, ready_spool):
    """T-112: Once BLOQUEADO, ReparacionService.tomar_reparacion raises 403 SPOOL_BLOQUEADO.

    Verifies the downstream enforcement of the cycle: a spool whose Estado_Detalle
    has reached BLOQUEADO must not be takeable for repair.
    """
    from backend.services.reparacion_service import ReparacionService
    from backend.exceptions import SpoolBloqueadoError
    from backend.models.spool import Spool
    from datetime import date as _date

    bloqueado_spool = Spool(
        tag_spool="INTEGRATION-001",
        fecha_materiales=_date(2026, 1, 20),
        fecha_armado=_date(2026, 1, 22),
        fecha_soldadura=_date(2026, 1, 25),
        fecha_qc_metrologia=None,
        armador="MR(93)",
        soldador="JP(94)",
        ocupado_por=None,
        fecha_ocupacion=None,
        estado_detalle="BLOQUEADO - Contactar supervisor",
        version=10
    )
    mock_sheets_repo.get_spool_by_tag.return_value = bloqueado_spool

    validation = ValidationService(role_service=None)
    cycle_counter = CycleCounterService()
    metadata_repo = Mock(spec=MetadataRepository)

    reparacion_service = ReparacionService(
        validation_service=validation,
        cycle_counter_service=cycle_counter,
        sheets_repository=mock_sheets_repo,
        metadata_repository=metadata_repo
    )

    with pytest.raises(SpoolBloqueadoError) as exc:
        await reparacion_service.tomar_reparacion(
            tag_spool="INTEGRATION-001",
            worker_id=95,
            worker_nombre="CP(95)"
        )

    # SpoolBloqueadoError maps to HTTP 403 with code SPOOL_BLOQUEADO (main.py:187)
    assert "BLOQUEADO" in str(exc.value).upper() or "bloqueado" in str(exc.value).lower()
