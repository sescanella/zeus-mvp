"""
Integration tests for reparación workflow.

Tests v3.0 Phase 6 reparación features:
- TOMAR/PAUSAR/COMPLETAR/CANCELAR actions
- Metrología → Reparación → Metrología loop

These are integration tests using mocked dependencies to verify
the full orchestration flow through ReparacionService.
"""

import pytest
from datetime import date
from unittest.mock import Mock

from backend.services.reparacion_service import ReparacionService
from backend.services.validation_service import ValidationService
from backend.repositories.metadata_repository import MetadataRepository
from backend.models.spool import Spool
from backend.exceptions import (
    SpoolOccupiedError,
    NoAutorizadoError,
)


@pytest.fixture
def mock_sheets_repo():
    repo = Mock()
    repo.get_spool_by_tag.return_value = None
    repo.find_row_by_column_value.return_value = 2
    repo.get_cell_value.return_value = ""
    repo.batch_update_by_column_name.return_value = None
    return repo


@pytest.fixture
def mock_metadata_repo():
    repo = Mock(spec=MetadataRepository)
    repo.append_event.return_value = None
    repo.get_events_by_spool.return_value = []
    return repo


@pytest.fixture
def validation_service():
    return ValidationService(role_service=None)


@pytest.fixture
def reparacion_service(validation_service, mock_sheets_repo, mock_metadata_repo):
    return ReparacionService(
        validation_service=validation_service,
        sheets_repository=mock_sheets_repo,
        metadata_repository=mock_metadata_repo
    )


@pytest.fixture
def rechazado_spool():
    """Spool rejected (no occupation, no cycle counter)."""
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
        estado_detalle="RECHAZADO - Pendiente reparación",
        version=8
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
        estado_detalle="EN_REPARACION - Ocupado: CP(95)",
        version=10
    )


# ============================================================================
# HAPPY PATH TESTS
# ============================================================================


@pytest.mark.asyncio
async def test_complete_repair_cycle_success(reparacion_service, mock_sheets_repo, rechazado_spool):
    """
    Complete repair cycle: RECHAZADO → TOMAR → COMPLETAR → PENDIENTE_METROLOGIA.
    """
    tag_spool = rechazado_spool.tag_spool
    worker_id = 95
    worker_nombre = "CP(95)"

    mock_sheets_repo.get_spool_by_tag.return_value = rechazado_spool

    result = await reparacion_service.tomar_reparacion(tag_spool, worker_id, worker_nombre)

    assert result["success"] is True
    assert result["tag_spool"] == tag_spool
    assert result["worker_nombre"] == worker_nombre
    assert "EN_REPARACION" in result["estado_detalle"]
    assert mock_sheets_repo.get_spool_by_tag.called

    # Switch mock to EN_REPARACION state for completar
    en_rep = Spool(
        tag_spool=tag_spool,
        fecha_materiales=rechazado_spool.fecha_materiales,
        fecha_armado=rechazado_spool.fecha_armado,
        fecha_soldadura=rechazado_spool.fecha_soldadura,
        fecha_qc_metrologia=rechazado_spool.fecha_qc_metrologia,
        armador=rechazado_spool.armador,
        soldador=rechazado_spool.soldador,
        ocupado_por=worker_nombre,
        fecha_ocupacion="28/01/2026",
        estado_detalle=f"EN_REPARACION - Ocupado: {worker_nombre}",
        version=9
    )
    mock_sheets_repo.get_spool_by_tag.return_value = en_rep

    result = await reparacion_service.completar_reparacion(tag_spool, worker_id, worker_nombre)

    assert result["success"] is True
    assert result["estado_detalle"] == "PENDIENTE_METROLOGIA"


@pytest.mark.asyncio
async def test_pausar_and_resume_repair(reparacion_service, mock_sheets_repo, en_reparacion_spool):
    """Worker can PAUSAR and later resume repair work."""
    tag_spool = en_reparacion_spool.tag_spool
    worker_id = 95
    worker_nombre = "CP(95)"

    mock_sheets_repo.get_spool_by_tag.return_value = en_reparacion_spool

    result = await reparacion_service.pausar_reparacion(tag_spool, worker_id)
    assert result["success"] is True
    assert "REPARACION_PAUSADA" in result["estado_detalle"]

    pausada = Spool(
        tag_spool=tag_spool,
        fecha_materiales=en_reparacion_spool.fecha_materiales,
        fecha_armado=en_reparacion_spool.fecha_armado,
        fecha_soldadura=en_reparacion_spool.fecha_soldadura,
        fecha_qc_metrologia=en_reparacion_spool.fecha_qc_metrologia,
        armador=en_reparacion_spool.armador,
        soldador=en_reparacion_spool.soldador,
        ocupado_por=None,
        fecha_ocupacion=None,
        estado_detalle="REPARACION_PAUSADA",
        version=11
    )
    mock_sheets_repo.get_spool_by_tag.return_value = pausada

    result = await reparacion_service.tomar_reparacion(tag_spool, worker_id, worker_nombre)
    assert result["success"] is True


@pytest.mark.asyncio
async def test_cancelar_returns_to_rechazado(reparacion_service, mock_sheets_repo, en_reparacion_spool):
    """CANCELAR returns spool to RECHAZADO state."""
    tag_spool = en_reparacion_spool.tag_spool
    mock_sheets_repo.get_spool_by_tag.return_value = en_reparacion_spool

    result = await reparacion_service.cancelar_reparacion(tag_spool, 95)

    assert result["success"] is True
    assert "RECHAZADO" in result["estado_detalle"]


# ============================================================================
# ERROR CASES
# ============================================================================


@pytest.mark.asyncio
async def test_cannot_completar_without_ownership(reparacion_service, mock_sheets_repo, en_reparacion_spool):
    """COMPLETAR raises NoAutorizadoError if worker doesn't own the spool."""
    mock_sheets_repo.get_spool_by_tag.return_value = en_reparacion_spool
    with pytest.raises(NoAutorizadoError):
        await reparacion_service.completar_reparacion(en_reparacion_spool.tag_spool, 99, "WW(99)")


@pytest.mark.asyncio
async def test_cannot_tomar_already_occupied(reparacion_service, mock_sheets_repo, rechazado_spool):
    """TOMAR raises SpoolOccupiedError if spool already occupied."""
    occupied = Spool(
        tag_spool=rechazado_spool.tag_spool,
        fecha_materiales=rechazado_spool.fecha_materiales,
        fecha_armado=rechazado_spool.fecha_armado,
        fecha_soldadura=rechazado_spool.fecha_soldadura,
        fecha_qc_metrologia=rechazado_spool.fecha_qc_metrologia,
        armador=rechazado_spool.armador,
        soldador=rechazado_spool.soldador,
        ocupado_por="CP(95)",
        fecha_ocupacion="28/01/2026",
        estado_detalle="RECHAZADO - Pendiente reparación",
        version=8
    )
    mock_sheets_repo.get_spool_by_tag.return_value = occupied

    with pytest.raises(SpoolOccupiedError):
        await reparacion_service.tomar_reparacion(occupied.tag_spool, 96, "NW(96)")
