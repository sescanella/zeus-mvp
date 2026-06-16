"""
Unit tests for ReparacionService.

Tests reparación orchestration and state machine integration.
"""

import pytest
from unittest.mock import AsyncMock, Mock, patch
from datetime import date
import json

from backend.services.reparacion_service import ReparacionService
from backend.services.validation_service import ValidationService
from backend.repositories.sheets_repository import SheetsRepository
from backend.repositories.metadata_repository import MetadataRepository
from backend.models.spool import Spool
from backend.exceptions import SpoolNoEncontradoError


@pytest.fixture
def mock_validation_service():
    service = Mock(spec=ValidationService)
    service.validar_puede_tomar_reparacion.return_value = None
    service.validar_puede_cancelar_reparacion.return_value = None
    return service


@pytest.fixture
def mock_sheets_repo():
    return Mock(spec=SheetsRepository)


@pytest.fixture
def mock_metadata_repo():
    repo = Mock(spec=MetadataRepository)
    repo.log_event.return_value = "mock-event-id"
    return repo


@pytest.fixture
def reparacion_service(mock_validation_service, mock_sheets_repo, mock_metadata_repo):
    return ReparacionService(
        validation_service=mock_validation_service,
        sheets_repository=mock_sheets_repo,
        metadata_repository=mock_metadata_repo
    )


@pytest.fixture
def rechazado_spool():
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
        estado_detalle="RECHAZADO - Pendiente reparación",
        version=8
    )


@pytest.fixture
def en_reparacion_spool():
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
        estado_detalle="EN_REPARACION - Ocupado: CP(95)",
        version=10
    )


@pytest.mark.asyncio
async def test_tomar_returns_success(reparacion_service, mock_sheets_repo, rechazado_spool):
    """TOMAR should return success with estado_detalle when spool valid."""
    mock_sheets_repo.get_spool_by_tag.return_value = rechazado_spool

    with patch("backend.services.reparacion_service.REPARACIONStateMachine") as MockStateMachine:
        mock_machine = AsyncMock()
        mock_machine.current_state.id = "en_reparacion"
        mock_machine.get_state_id.return_value = "en_reparacion"
        MockStateMachine.return_value = mock_machine

        result = await reparacion_service.tomar_reparacion(rechazado_spool.tag_spool, 95, "CP(95)")

    assert result["success"] is True
    assert "EN_REPARACION" in result["estado_detalle"]
    assert "CP(95)" in result["estado_detalle"]


@pytest.mark.asyncio
async def test_tomar_raises_when_spool_not_found(reparacion_service, mock_sheets_repo):
    """TOMAR should raise SpoolNoEncontradoError when spool doesn't exist."""
    mock_sheets_repo.get_spool_by_tag.return_value = None
    with pytest.raises(SpoolNoEncontradoError):
        await reparacion_service.tomar_reparacion("MISSING", 95, "CP(95)")


@pytest.mark.asyncio
async def test_pausar_clears_occupation(reparacion_service, mock_sheets_repo, en_reparacion_spool):
    """PAUSAR should return REPARACION_PAUSADA estado."""
    mock_sheets_repo.get_spool_by_tag.return_value = en_reparacion_spool

    with patch("backend.services.reparacion_service.REPARACIONStateMachine") as MockStateMachine:
        mock_machine = AsyncMock()
        mock_machine.current_state.id = "reparacion_pausada"
        mock_machine.get_state_id.return_value = "reparacion_pausada"
        MockStateMachine.return_value = mock_machine

        result = await reparacion_service.pausar_reparacion(en_reparacion_spool.tag_spool, 95)

    assert result["success"] is True
    assert result["estado_detalle"] == "REPARACION_PAUSADA"


@pytest.mark.asyncio
async def test_completar_sets_pendiente_metrologia(reparacion_service, mock_sheets_repo, en_reparacion_spool):
    """COMPLETAR should set estado_detalle to PENDIENTE_METROLOGIA."""
    mock_sheets_repo.get_spool_by_tag.return_value = en_reparacion_spool

    with patch("backend.services.reparacion_service.REPARACIONStateMachine") as MockStateMachine:
        mock_machine = AsyncMock()
        mock_machine.current_state.id = "pendiente_metrologia"
        mock_machine.get_state_id.return_value = "pendiente_metrologia"
        MockStateMachine.return_value = mock_machine

        result = await reparacion_service.completar_reparacion(en_reparacion_spool.tag_spool, 95, "CP(95)")

    assert result["success"] is True
    assert result["estado_detalle"] == "PENDIENTE_METROLOGIA"


@pytest.mark.asyncio
async def test_cancelar_returns_to_rechazado(reparacion_service, mock_sheets_repo, en_reparacion_spool):
    """CANCELAR should return spool to RECHAZADO."""
    mock_sheets_repo.get_spool_by_tag.return_value = en_reparacion_spool

    with patch("backend.services.reparacion_service.REPARACIONStateMachine") as MockStateMachine:
        mock_machine = AsyncMock()
        mock_machine.current_state.id = "rechazado"
        mock_machine.get_state_id.return_value = "rechazado"
        MockStateMachine.return_value = mock_machine

        result = await reparacion_service.cancelar_reparacion(en_reparacion_spool.tag_spool, 95)

    assert result["success"] is True
    assert "RECHAZADO" in result["estado_detalle"]


@pytest.mark.asyncio
async def test_metadata_logged_on_tomar(reparacion_service, mock_sheets_repo, mock_metadata_repo, rechazado_spool):
    """TOMAR should log a metadata event."""
    mock_sheets_repo.get_spool_by_tag.return_value = rechazado_spool

    with patch("backend.services.reparacion_service.REPARACIONStateMachine") as MockStateMachine:
        mock_machine = AsyncMock()
        mock_machine.current_state.id = "en_reparacion"
        mock_machine.get_state_id = Mock(return_value="en_reparacion")
        MockStateMachine.return_value = mock_machine

        await reparacion_service.tomar_reparacion(rechazado_spool.tag_spool, 95, "CP(95)")

    mock_metadata_repo.log_event.assert_called_once()


@pytest.mark.asyncio
async def test_metadata_logging_failure_does_not_block(reparacion_service, mock_sheets_repo, mock_metadata_repo, rechazado_spool):
    """TOMAR should continue even if metadata logging fails (best-effort)."""
    mock_sheets_repo.get_spool_by_tag.return_value = rechazado_spool
    mock_metadata_repo.log_event.side_effect = Exception("Sheets API error")

    with patch("backend.services.reparacion_service.REPARACIONStateMachine") as MockStateMachine:
        mock_machine = AsyncMock()
        mock_machine.current_state.id = "en_reparacion"
        mock_machine.get_state_id.return_value = "en_reparacion"
        MockStateMachine.return_value = mock_machine

        result = await reparacion_service.tomar_reparacion(rechazado_spool.tag_spool, 95, "CP(95)")

    assert result["success"] is True
