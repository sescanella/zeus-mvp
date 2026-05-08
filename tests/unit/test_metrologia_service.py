"""
Unit tests for MetrologiaService.

Tests instant completion workflow with APROBADO/RECHAZADO outcomes.
"""
import pytest
from unittest.mock import Mock, patch
from datetime import date

from backend.services.metrologia_service import MetrologiaService
from backend.services.validation_service import ValidationService
from backend.services.cycle_counter_service import CycleCounterService
from backend.models.spool import Spool
from backend.exceptions import (
    SpoolNoEncontradoError,
    DependenciasNoSatisfechasError,
    OperacionYaCompletadaError,
    SpoolOccupiedError
)


@pytest.fixture
def mock_sheets_repo():
    """Mock SheetsRepository (MetrologiaService uses state machine -> batch_update_by_column_name)."""
    repo = Mock()
    repo.find_row_by_column_value = Mock(return_value=10)
    repo.batch_update_by_column_name = Mock()
    # T-112: state machine reads Estado_Detalle to extract current cycle on RECHAZADO
    repo.get_cell_value = Mock(return_value="")
    return repo


@pytest.fixture
def mock_metadata_repo():
    """Mock MetadataRepository."""
    repo = Mock()
    repo.log_event = Mock(return_value="mock-event-id")
    return repo


@pytest.fixture
def validation_service():
    """Real ValidationService without role_service for testing."""
    return ValidationService(role_service=None)


@pytest.fixture
def cycle_counter():
    """Real CycleCounterService for testing (T-112: now required by MetrologiaService)."""
    return CycleCounterService()


@pytest.fixture
def metrologia_service(validation_service, mock_sheets_repo, mock_metadata_repo, cycle_counter):
    """MetrologiaService with mocked dependencies (single-user mode: no Redis)."""
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


@pytest.mark.asyncio
async def test_completar_aprobado_success(metrologia_service, mock_sheets_repo, ready_spool):
    """Test successful APROBADO completion."""
    mock_sheets_repo.get_spool_by_tag = Mock(return_value=ready_spool)

    result = await metrologia_service.completar(
        tag_spool="TEST-001",
        worker_id=95,
        worker_nombre="CP(95)",
        resultado="APROBADO"
    )

    # Verify success response
    assert result["success"] is True
    assert result["resultado"] == "APROBADO"
    assert result["tag_spool"] == "TEST-001"

    # Verify Sheets batch update was called (state machine updates Fecha_QC_Metrología + Estado_Detalle)
    mock_sheets_repo.batch_update_by_column_name.assert_called_once()


@pytest.mark.asyncio
async def test_completar_rechazado_success(metrologia_service, mock_sheets_repo, ready_spool):
    """Test successful RECHAZADO completion."""
    mock_sheets_repo.get_spool_by_tag = Mock(return_value=ready_spool)

    result = await metrologia_service.completar(
        tag_spool="TEST-001",
        worker_id=95,
        worker_nombre="CP(95)",
        resultado="RECHAZADO"
    )

    # Verify success response
    assert result["success"] is True
    assert result["resultado"] == "RECHAZADO"
    assert result["tag_spool"] == "TEST-001"

    # Verify Sheets batch update was called (state machine updates Fecha_QC_Metrología + Estado_Detalle)
    mock_sheets_repo.batch_update_by_column_name.assert_called_once()


@pytest.mark.asyncio
async def test_completar_spool_not_found(metrologia_service, mock_sheets_repo):
    """Test error when spool doesn't exist."""
    mock_sheets_repo.get_spool_by_tag = Mock(return_value=None)

    with pytest.raises(SpoolNoEncontradoError):
        await metrologia_service.completar(
            tag_spool="INVALID",
            worker_id=95,
            worker_nombre="CP(95)",
            resultado="APROBADO"
        )


@pytest.mark.asyncio
async def test_completar_logs_metadata_event(metrologia_service, mock_sheets_repo, mock_metadata_repo, ready_spool):
    """Test that metadata event is logged on completion."""
    mock_sheets_repo.get_spool_by_tag = Mock(return_value=ready_spool)

    await metrologia_service.completar(
        tag_spool="TEST-001",
        worker_id=95,
        worker_nombre="CP(95)",
        resultado="APROBADO"
    )

    # Verify metadata was logged via log_event(**event)
    mock_metadata_repo.log_event.assert_called_once()
    call_kwargs = mock_metadata_repo.log_event.call_args[1]
    assert call_kwargs["tag_spool"] == "TEST-001"
    assert call_kwargs["worker_id"] == 95
    assert call_kwargs["operacion"] == "METROLOGIA"
    assert "APROBADO" in call_kwargs["metadata_json"]


@pytest.mark.asyncio
async def test_completar_continues_on_metadata_failure(metrologia_service, mock_sheets_repo, mock_metadata_repo, ready_spool):
    """Test that operation continues even if metadata logging fails (best-effort)."""
    mock_sheets_repo.get_spool_by_tag = Mock(return_value=ready_spool)
    mock_metadata_repo.log_event = Mock(side_effect=Exception("Metadata API error"))

    # Should still succeed despite metadata failure
    result = await metrologia_service.completar(
        tag_spool="TEST-001",
        worker_id=95,
        worker_nombre="CP(95)",
        resultado="APROBADO"
    )

    assert result["success"] is True


# ============================================================================
# T-112 REGRESSION TESTS — cycle_counter injection
# ============================================================================


@pytest.mark.asyncio
async def test_t112_cycle_counter_passed_to_state_machine(
    validation_service, mock_sheets_repo, mock_metadata_repo, ready_spool
):
    """T-112: MetrologiaService must inject cycle_counter into MetrologiaStateMachine.

    Before fix, factory and constructor did not pass cycle_counter, so the
    on_enter_rechazado callback fell back to the static "METROLOGIA RECHAZADO -
    Pendiente reparación" string and never incremented the cycle. This test
    locks in the injection.
    """
    mock_sheets_repo.get_spool_by_tag = Mock(return_value=ready_spool)
    cycle_counter_mock = Mock(spec=CycleCounterService)

    service = MetrologiaService(
        validation_service=validation_service,
        sheets_repository=mock_sheets_repo,
        metadata_repository=mock_metadata_repo,
        cycle_counter=cycle_counter_mock
    )

    with patch("backend.services.metrologia_service.MetrologiaStateMachine") as sm_cls:
        # Provide a no-op state machine instance so completar() doesn't crash
        sm_instance = Mock()
        sm_cls.return_value = sm_instance

        await service.completar(
            tag_spool="TEST-001",
            worker_id=95,
            worker_nombre="CP(95)",
            resultado="RECHAZADO"
        )

        sm_cls.assert_called_once()
        kwargs = sm_cls.call_args.kwargs
        assert kwargs["cycle_counter"] is cycle_counter_mock, (
            "MetrologiaStateMachine must receive cycle_counter from MetrologiaService"
        )


@pytest.mark.asyncio
async def test_t112_first_rechazado_writes_ciclo_1(
    metrologia_service, mock_sheets_repo, ready_spool
):
    """T-112: First RECHAZADO writes Estado_Detalle with 'Ciclo 1/3'.

    Before fix, the cycle was never written because cycle_counter was None.
    """
    mock_sheets_repo.get_spool_by_tag = Mock(return_value=ready_spool)
    mock_sheets_repo.get_cell_value = Mock(return_value="")  # No prior cycle

    await metrologia_service.completar(
        tag_spool="TEST-001",
        worker_id=95,
        worker_nombre="CP(95)",
        resultado="RECHAZADO"
    )

    # Verify Estado_Detalle was written with cycle 1/3
    mock_sheets_repo.batch_update_by_column_name.assert_called_once()
    updates = mock_sheets_repo.batch_update_by_column_name.call_args.kwargs["updates"]
    estado_update = next(u for u in updates if u["column_name"] == "Estado_Detalle")
    assert "Ciclo 1/3" in estado_update["value"]
    assert "RECHAZADO" in estado_update["value"]


@pytest.mark.asyncio
async def test_t112_third_rechazado_transitions_to_bloqueado(
    metrologia_service, mock_sheets_repo, ready_spool
):
    """T-112: Third RECHAZADO transitions Estado_Detalle to BLOQUEADO.

    Simulates the state Sheets has after 2 prior rejections by returning
    'Ciclo 2/3' from get_cell_value. The third rejection should yield BLOQUEADO.
    """
    mock_sheets_repo.get_spool_by_tag = Mock(return_value=ready_spool)
    mock_sheets_repo.get_cell_value = Mock(
        return_value="RECHAZADO (Ciclo 2/3) - Pendiente reparación"
    )

    await metrologia_service.completar(
        tag_spool="TEST-001",
        worker_id=95,
        worker_nombre="CP(95)",
        resultado="RECHAZADO"
    )

    # Verify Estado_Detalle was set to BLOQUEADO
    updates = mock_sheets_repo.batch_update_by_column_name.call_args.kwargs["updates"]
    estado_update = next(u for u in updates if u["column_name"] == "Estado_Detalle")
    assert "BLOQUEADO" in estado_update["value"]
    assert "supervisor" in estado_update["value"].lower()


@pytest.mark.asyncio
async def test_t112_aprobado_resets_cycle(
    metrologia_service, mock_sheets_repo, ready_spool
):
    """T-112: APROBADO resets cycle counter (consecutive rejections broken).

    With cycle_counter injected, on_enter_aprobado now calls reset_cycle()
    instead of falling back to the static "METROLOGIA APROBADO ✓" string.
    """
    mock_sheets_repo.get_spool_by_tag = Mock(return_value=ready_spool)

    await metrologia_service.completar(
        tag_spool="TEST-001",
        worker_id=95,
        worker_nombre="CP(95)",
        resultado="APROBADO"
    )

    updates = mock_sheets_repo.batch_update_by_column_name.call_args.kwargs["updates"]
    estado_update = next(u for u in updates if u["column_name"] == "Estado_Detalle")
    # reset_cycle() returns "METROLOGIA APROBADO ✓"
    assert "APROBADO" in estado_update["value"]
    # Should not contain any "Ciclo" indicator after reset
    assert "Ciclo" not in estado_update["value"]
