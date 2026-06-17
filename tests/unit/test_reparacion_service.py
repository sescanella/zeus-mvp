"""
Unit tests for ReparacionService.

The 3-cycle limit (CycleCounterService, SpoolBloqueadoError, BLOQUEADO state)
has been removed; these tests cover the simplified single-cycle workflow.
"""

import pytest
from unittest.mock import AsyncMock, Mock, patch
from datetime import date

from backend.services.reparacion_service import ReparacionService
from backend.services.validation_service import ValidationService
from backend.repositories.sheets_repository import SheetsRepository
from backend.repositories.metadata_repository import MetadataRepository
from backend.models.spool import Spool


# ============================================================================
# FIXTURES
# ============================================================================


@pytest.fixture
def mock_validation_service():
    """Mock ValidationService."""
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
        metadata_repository=mock_metadata_repo,
    )


@pytest.fixture
def rechazado_spool():
    """Sample RECHAZADO spool (new format, no cycle marker)."""
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
        version=8,
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
        estado_detalle="EN_REPARACION - Ocupado: CP(95)",
        version=10,
    )


# ============================================================================
# TOMAR REPARACION
# ============================================================================


@pytest.mark.asyncio
async def test_tomar_returns_en_reparacion_estado(reparacion_service, mock_sheets_repo, rechazado_spool):
    """TOMAR returns the EN_REPARACION estado_detalle with the worker name."""
    mock_sheets_repo.get_spool_by_tag.return_value = rechazado_spool

    with patch("backend.services.reparacion_service.REPARACIONStateMachine") as MockStateMachine:
        mock_machine = AsyncMock()
        mock_machine.current_state.id = "en_reparacion"
        mock_machine.get_state_id.return_value = "en_reparacion"
        MockStateMachine.return_value = mock_machine

        result = await reparacion_service.tomar_reparacion(
            rechazado_spool.tag_spool, worker_id=95, worker_nombre="CP(95)"
        )

    assert result["success"] is True
    assert result["estado_detalle"] == "EN_REPARACION - Ocupado: CP(95)"
    # `cycle` field is no longer part of the response
    assert "cycle" not in result


# ============================================================================
# PAUSAR REPARACION
# ============================================================================


@pytest.mark.asyncio
async def test_pausar_clears_occupation(reparacion_service, mock_sheets_repo, en_reparacion_spool):
    """PAUSAR clears occupation and writes plain REPARACION_PAUSADA."""
    mock_sheets_repo.get_spool_by_tag.return_value = en_reparacion_spool

    with patch("backend.services.reparacion_service.REPARACIONStateMachine") as MockStateMachine:
        mock_machine = AsyncMock()
        mock_machine.current_state.id = "reparacion_pausada"
        mock_machine.get_state_id.return_value = "reparacion_pausada"
        MockStateMachine.return_value = mock_machine

        result = await reparacion_service.pausar_reparacion(en_reparacion_spool.tag_spool, worker_id=95)

    assert result["success"] is True
    assert result["estado_detalle"] == "REPARACION_PAUSADA"


# ============================================================================
# COMPLETAR REPARACION
# ============================================================================


@pytest.mark.asyncio
async def test_completar_sets_pendiente_metrologia(reparacion_service, mock_sheets_repo, en_reparacion_spool):
    """COMPLETAR returns the spool to the metrología queue."""
    mock_sheets_repo.get_spool_by_tag.return_value = en_reparacion_spool

    with patch("backend.services.reparacion_service.REPARACIONStateMachine") as MockStateMachine:
        mock_machine = AsyncMock()
        mock_machine.current_state.id = "pendiente_metrologia"
        mock_machine.get_state_id.return_value = "pendiente_metrologia"
        MockStateMachine.return_value = mock_machine

        result = await reparacion_service.completar_reparacion(
            en_reparacion_spool.tag_spool, worker_id=95, worker_nombre="CP(95)"
        )

    assert result["success"] is True
    assert result["estado_detalle"] == "PENDIENTE_METROLOGIA"


# ============================================================================
# CANCELAR REPARACION
# ============================================================================


@pytest.mark.asyncio
async def test_cancelar_returns_to_rechazado(reparacion_service, mock_sheets_repo, en_reparacion_spool):
    """CANCELAR returns plain RECHAZADO (no cycle suffix)."""
    mock_sheets_repo.get_spool_by_tag.return_value = en_reparacion_spool

    with patch("backend.services.reparacion_service.REPARACIONStateMachine") as MockStateMachine:
        mock_machine = AsyncMock()
        mock_machine.current_state.id = "rechazado"
        mock_machine.get_state_id.return_value = "rechazado"
        MockStateMachine.return_value = mock_machine

        result = await reparacion_service.cancelar_reparacion(en_reparacion_spool.tag_spool, worker_id=95)

    assert result["success"] is True
    assert result["estado_detalle"] == "RECHAZADO - Pendiente reparación"


# ============================================================================
# METADATA LOGGING
# ============================================================================


@pytest.mark.asyncio
async def test_metadata_logging_failure_does_not_block(
    reparacion_service, mock_sheets_repo, mock_metadata_repo, rechazado_spool
):
    """The operation must succeed even if metadata logging fails (best-effort)."""
    mock_sheets_repo.get_spool_by_tag.return_value = rechazado_spool
    mock_metadata_repo.log_event.side_effect = Exception("Sheets API error")

    with patch("backend.services.reparacion_service.REPARACIONStateMachine") as MockStateMachine:
        mock_machine = AsyncMock()
        mock_machine.current_state.id = "en_reparacion"
        mock_machine.get_state_id.return_value = "en_reparacion"
        MockStateMachine.return_value = mock_machine

        result = await reparacion_service.tomar_reparacion(
            rechazado_spool.tag_spool, worker_id=95, worker_nombre="CP(95)"
        )

    assert result["success"] is True
