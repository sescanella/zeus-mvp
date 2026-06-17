"""
Integration tests for the reparación workflow.

Covers:
- TOMAR / PAUSAR / COMPLETAR / CANCELAR actions
- Metrología → Reparación → Metrología loop
- Legacy BLOQUEADO tolerance (3-cycle limit was removed)
- Ownership and occupation errors
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


# ============================================================================
# FIXTURES
# ============================================================================


@pytest.fixture
def mock_sheets_repo():
    """Mock SheetsRepository (state machine uses batch_update + get_cell_value)."""
    repo = Mock()
    repo.get_spool_by_tag.return_value = None
    repo.find_row_by_column_value.return_value = 2
    repo.get_cell_value.return_value = ""
    repo.batch_update_by_column_name.return_value = None
    repo.get_tag_spool_column_letter.return_value = "G"
    return repo


@pytest.fixture
def mock_metadata_repo():
    repo = Mock(spec=MetadataRepository)
    repo.log_event.return_value = "mock-event-id"
    return repo


@pytest.fixture
def validation_service():
    return ValidationService(role_service=None)


@pytest.fixture
def reparacion_service(validation_service, mock_sheets_repo, mock_metadata_repo):
    return ReparacionService(
        validation_service=validation_service,
        sheets_repository=mock_sheets_repo,
        metadata_repository=mock_metadata_repo,
    )


@pytest.fixture
def rechazado_spool():
    """Spool rejected by metrología and waiting for repair."""
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
        version=8,
    )


@pytest.fixture
def legacy_bloqueado_spool():
    """Sheet row left over from the removed 3-cycle limit. Must be treated
    like plain RECHAZADO and be repair-eligible."""
    return Spool(
        tag_spool="REPAIR-LEGACY",
        fecha_materiales=date(2026, 1, 20),
        fecha_armado=date(2026, 1, 22),
        fecha_soldadura=date(2026, 1, 25),
        fecha_qc_metrologia=date(2026, 1, 27),
        armador="MR(93)",
        soldador="JP(94)",
        ocupado_por=None,
        fecha_ocupacion=None,
        estado_detalle="BLOQUEADO - Contactar supervisor",
        version=15,
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
        version=10,
    )


# ============================================================================
# HAPPY PATH — TOMAR → COMPLETAR
# ============================================================================


@pytest.mark.asyncio
async def test_complete_repair_cycle_success(reparacion_service, mock_sheets_repo, rechazado_spool):
    """
    RECHAZADO → TOMAR → COMPLETAR → PENDIENTE_METROLOGIA.
    """
    tag_spool = rechazado_spool.tag_spool
    worker_id = 95
    worker_nombre = "CP(95)"

    # Step 1: TOMAR
    mock_sheets_repo.get_spool_by_tag.return_value = rechazado_spool
    result = await reparacion_service.tomar_reparacion(tag_spool, worker_id, worker_nombre)

    assert result["success"] is True
    assert result["tag_spool"] == tag_spool
    assert result["worker_nombre"] == worker_nombre
    assert result["estado_detalle"] == f"EN_REPARACION - Ocupado: {worker_nombre}"

    # Step 2: COMPLETAR (state must now reflect EN_REPARACION)
    en_reparacion_state = Spool(
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
        version=9,
    )
    mock_sheets_repo.get_spool_by_tag.return_value = en_reparacion_state

    result = await reparacion_service.completar_reparacion(tag_spool, worker_id, worker_nombre)

    assert result["success"] is True
    assert result["estado_detalle"] == "PENDIENTE_METROLOGIA"


# ============================================================================
# LEGACY BLOQUEADO TOLERANCE
# ============================================================================


@pytest.mark.asyncio
async def test_can_repair_legacy_bloqueado_spool(reparacion_service, mock_sheets_repo, legacy_bloqueado_spool):
    """A row left behind with 'BLOQUEADO - Contactar supervisor' (legacy) must
    be takeable for repair, and the resulting Estado_Detalle is the clean
    EN_REPARACION marker — the legacy text is overwritten on the next write."""
    mock_sheets_repo.get_spool_by_tag.return_value = legacy_bloqueado_spool

    result = await reparacion_service.tomar_reparacion(
        legacy_bloqueado_spool.tag_spool, worker_id=95, worker_nombre="CP(95)"
    )

    assert result["success"] is True
    assert result["estado_detalle"] == "EN_REPARACION - Ocupado: CP(95)"


# ============================================================================
# PAUSAR / RESUME
# ============================================================================


@pytest.mark.asyncio
async def test_pausar_and_resume_repair(reparacion_service, mock_sheets_repo, en_reparacion_spool):
    """EN_REPARACION → PAUSAR → REPARACION_PAUSADA → TOMAR (resume) → EN_REPARACION."""
    tag_spool = en_reparacion_spool.tag_spool
    worker_id = 95
    worker_nombre = "CP(95)"

    mock_sheets_repo.get_spool_by_tag.return_value = en_reparacion_spool

    result = await reparacion_service.pausar_reparacion(tag_spool, worker_id)
    assert result["success"] is True
    assert result["estado_detalle"] == "REPARACION_PAUSADA"

    pausada_spool = Spool(
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
        version=11,
    )
    mock_sheets_repo.get_spool_by_tag.return_value = pausada_spool

    result = await reparacion_service.tomar_reparacion(tag_spool, worker_id, worker_nombre)
    assert result["success"] is True


# ============================================================================
# CANCELAR
# ============================================================================


@pytest.mark.asyncio
async def test_cancelar_returns_to_rechazado(reparacion_service, mock_sheets_repo, en_reparacion_spool):
    """EN_REPARACION → CANCELAR → RECHAZADO (plain marker)."""
    mock_sheets_repo.get_spool_by_tag.return_value = en_reparacion_spool

    result = await reparacion_service.cancelar_reparacion(en_reparacion_spool.tag_spool, worker_id=95)

    assert result["success"] is True
    assert result["estado_detalle"] == "RECHAZADO - Pendiente reparación"


# ============================================================================
# ERROR CASES
# ============================================================================


@pytest.mark.asyncio
async def test_cannot_completar_without_ownership(reparacion_service, mock_sheets_repo, en_reparacion_spool):
    """COMPLETAR by a worker who doesn't own the spool → NoAutorizadoError."""
    mock_sheets_repo.get_spool_by_tag.return_value = en_reparacion_spool

    with pytest.raises(NoAutorizadoError):
        await reparacion_service.completar_reparacion(
            en_reparacion_spool.tag_spool, worker_id=99, worker_nombre="WW(99)"
        )


@pytest.mark.asyncio
async def test_cannot_tomar_already_occupied(reparacion_service, mock_sheets_repo, rechazado_spool):
    """TOMAR on a spool already occupied by another worker → SpoolOccupiedError."""
    occupied_spool = Spool(
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
        version=8,
    )
    mock_sheets_repo.get_spool_by_tag.return_value = occupied_spool

    with pytest.raises(SpoolOccupiedError):
        await reparacion_service.tomar_reparacion(
            occupied_spool.tag_spool, worker_id=96, worker_nombre="NW(96)"
        )
