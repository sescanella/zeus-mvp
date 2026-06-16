"""
Unit tests for MetrologiaService.

Tests instant completion workflow with APROBADO/RECHAZADO outcomes.
"""
import pytest
from unittest.mock import Mock
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
    repo = Mock()
    repo.find_row_by_column_value = Mock(return_value=10)
    repo.batch_update_by_column_name = Mock()
    repo.get_cell_value = Mock(return_value="")
    return repo


@pytest.fixture
def mock_metadata_repo():
    repo = Mock()
    repo.log_event = Mock(return_value="mock-event-id")
    return repo


@pytest.fixture
def validation_service():
    return ValidationService(role_service=None)


@pytest.fixture
def metrologia_service(validation_service, mock_sheets_repo, mock_metadata_repo):
    return MetrologiaService(
        validation_service=validation_service,
        sheets_repository=mock_sheets_repo,
        metadata_repository=mock_metadata_repo
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
    validation_service.validar_puede_completar_metrologia(ready_spool, worker_id=95)


def test_validar_puede_completar_metrologia_arm_not_completed(validation_service):
    spool = Spool(
        tag_spool="TEST-001",
        fecha_materiales=date(2026, 1, 20),
        fecha_armado=None,
        fecha_soldadura=date(2026, 1, 25),
        fecha_qc_metrologia=None,
        ocupado_por=None
    )
    with pytest.raises(DependenciasNoSatisfechasError) as exc:
        validation_service.validar_puede_completar_metrologia(spool, worker_id=95)
    assert "ARM completado" in str(exc.value)


def test_validar_puede_completar_metrologia_sold_not_completed(validation_service):
    spool = Spool(
        tag_spool="TEST-001",
        fecha_materiales=date(2026, 1, 20),
        fecha_armado=date(2026, 1, 22),
        fecha_soldadura=None,
        fecha_qc_metrologia=None,
        ocupado_por=None
    )
    with pytest.raises(DependenciasNoSatisfechasError) as exc:
        validation_service.validar_puede_completar_metrologia(spool, worker_id=95)
    assert "SOLD completado" in str(exc.value)


def test_validar_puede_completar_metrologia_already_completed(validation_service):
    spool = Spool(
        tag_spool="TEST-001",
        fecha_materiales=date(2026, 1, 20),
        fecha_armado=date(2026, 1, 22),
        fecha_soldadura=date(2026, 1, 25),
        fecha_qc_metrologia=date(2026, 1, 27),
        ocupado_por=None
    )
    with pytest.raises(OperacionYaCompletadaError) as exc:
        validation_service.validar_puede_completar_metrologia(spool, worker_id=95)
    assert "METROLOGIA" in str(exc.value)


def test_validar_puede_completar_metrologia_spool_occupied(validation_service):
    spool = Spool(
        tag_spool="TEST-001",
        fecha_materiales=date(2026, 1, 20),
        fecha_armado=date(2026, 1, 22),
        fecha_soldadura=date(2026, 1, 25),
        fecha_qc_metrologia=None,
        ocupado_por="MR(93)"
    )
    with pytest.raises(SpoolOccupiedError) as exc:
        validation_service.validar_puede_completar_metrologia(spool, worker_id=95)
    assert "ocupado" in str(exc.value).lower()


@pytest.mark.asyncio
async def test_completar_aprobado_success(metrologia_service, mock_sheets_repo, ready_spool):
    mock_sheets_repo.get_spool_by_tag = Mock(return_value=ready_spool)

    result = await metrologia_service.completar(
        tag_spool="TEST-001",
        worker_id=95,
        worker_nombre="CP(95)",
        resultado="APROBADO"
    )

    assert result["success"] is True
    assert result["resultado"] == "APROBADO"
    assert result["tag_spool"] == "TEST-001"
    mock_sheets_repo.batch_update_by_column_name.assert_called_once()


@pytest.mark.asyncio
async def test_completar_rechazado_success(metrologia_service, mock_sheets_repo, ready_spool):
    mock_sheets_repo.get_spool_by_tag = Mock(return_value=ready_spool)

    result = await metrologia_service.completar(
        tag_spool="TEST-001",
        worker_id=95,
        worker_nombre="CP(95)",
        resultado="RECHAZADO"
    )

    assert result["success"] is True
    assert result["resultado"] == "RECHAZADO"
    assert result["tag_spool"] == "TEST-001"
    mock_sheets_repo.batch_update_by_column_name.assert_called_once()


@pytest.mark.asyncio
async def test_completar_spool_not_found(metrologia_service, mock_sheets_repo):
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
    mock_sheets_repo.get_spool_by_tag = Mock(return_value=ready_spool)

    await metrologia_service.completar(
        tag_spool="TEST-001",
        worker_id=95,
        worker_nombre="CP(95)",
        resultado="APROBADO"
    )

    mock_metadata_repo.log_event.assert_called_once()
    call_kwargs = mock_metadata_repo.log_event.call_args[1]
    assert call_kwargs["tag_spool"] == "TEST-001"
    assert call_kwargs["worker_id"] == 95
    assert call_kwargs["operacion"] == "METROLOGIA"
    assert "APROBADO" in call_kwargs["metadata_json"]


@pytest.mark.asyncio
async def test_completar_continues_on_metadata_failure(metrologia_service, mock_sheets_repo, mock_metadata_repo, ready_spool):
    mock_sheets_repo.get_spool_by_tag = Mock(return_value=ready_spool)
    mock_metadata_repo.log_event = Mock(side_effect=Exception("Metadata API error"))

    result = await metrologia_service.completar(
        tag_spool="TEST-001",
        worker_id=95,
        worker_nombre="CP(95)",
        resultado="APROBADO"
    )

    assert result["success"] is True


@pytest.mark.asyncio
async def test_rechazado_writes_rechazado_estado(metrologia_service, mock_sheets_repo, ready_spool):
    """RECHAZADO writes 'RECHAZADO - Pendiente reparación' to Estado_Detalle."""
    mock_sheets_repo.get_spool_by_tag = Mock(return_value=ready_spool)

    await metrologia_service.completar(
        tag_spool="TEST-001",
        worker_id=95,
        worker_nombre="CP(95)",
        resultado="RECHAZADO"
    )

    updates = mock_sheets_repo.batch_update_by_column_name.call_args.kwargs["updates"]
    estado_update = next(u for u in updates if u["column_name"] == "Estado_Detalle")
    assert "RECHAZADO" in estado_update["value"]


@pytest.mark.asyncio
async def test_aprobado_writes_aprobado_estado(metrologia_service, mock_sheets_repo, ready_spool):
    """APROBADO writes 'METROLOGIA APROBADO ✓' to Estado_Detalle."""
    mock_sheets_repo.get_spool_by_tag = Mock(return_value=ready_spool)

    await metrologia_service.completar(
        tag_spool="TEST-001",
        worker_id=95,
        worker_nombre="CP(95)",
        resultado="APROBADO"
    )

    updates = mock_sheets_repo.batch_update_by_column_name.call_args.kwargs["updates"]
    estado_update = next(u for u in updates if u["column_name"] == "Estado_Detalle")
    assert "APROBADO" in estado_update["value"]
