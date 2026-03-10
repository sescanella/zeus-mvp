"""
Unit tests for SpoolStatus model and from_spool() classmethod.

Tests validate:
- SpoolStatus.from_spool() extracts pass-through fields
- SpoolStatus.from_spool() populates computed fields via parse_estado_detalle()
- BatchStatusRequest validates min/max tags
- BatchStatusResponse structure

Reference:
- Model: backend/models/spool_status.py
- Plan: 00-01-PLAN.md (API-01)
"""
import pytest
from pydantic import ValidationError

from backend.models.spool import Spool
from backend.models.spool_status import SpoolStatus, BatchStatusRequest, BatchStatusResponse


# ==================== FIXTURES ====================


def make_spool(**overrides) -> Spool:
    """Create a minimal Spool for testing."""
    defaults = {
        "tag_spool": "MK-TEST-001",
        "ocupado_por": None,
        "fecha_ocupacion": None,
        "estado_detalle": None,
        "total_uniones": None,
        "uniones_arm_completadas": None,
        "uniones_sold_completadas": None,
        "pulgadas_arm": None,
        "pulgadas_sold": None,
    }
    defaults.update(overrides)
    return Spool(**defaults)


# ==================== PASS-THROUGH FIELDS ====================


def test_from_spool_extracts_tag_spool():
    """from_spool() correctly copies tag_spool."""
    spool = make_spool(tag_spool="MK-1335-CW-25238-011")
    status = SpoolStatus.from_spool(spool)
    assert status.tag_spool == "MK-1335-CW-25238-011"


def test_from_spool_extracts_ocupado_por():
    """from_spool() correctly copies ocupado_por."""
    spool = make_spool(ocupado_por="MR(93)")
    status = SpoolStatus.from_spool(spool)
    assert status.ocupado_por == "MR(93)"


def test_from_spool_extracts_fecha_ocupacion():
    """from_spool() correctly copies fecha_ocupacion."""
    spool = make_spool(fecha_ocupacion="10-03-2026 14:30:00")
    status = SpoolStatus.from_spool(spool)
    assert status.fecha_ocupacion == "10-03-2026 14:30:00"


def test_from_spool_extracts_estado_detalle():
    """from_spool() correctly copies estado_detalle."""
    spool = make_spool(estado_detalle="MR(93) trabajando ARM (ARM en progreso, SOLD pendiente)")
    status = SpoolStatus.from_spool(spool)
    assert status.estado_detalle == "MR(93) trabajando ARM (ARM en progreso, SOLD pendiente)"


def test_from_spool_extracts_union_counts():
    """from_spool() correctly copies union count fields."""
    spool = make_spool(
        total_uniones=10,
        uniones_arm_completadas=3,
        uniones_sold_completadas=2
    )
    status = SpoolStatus.from_spool(spool)
    assert status.total_uniones == 10
    assert status.uniones_arm_completadas == 3
    assert status.uniones_sold_completadas == 2


def test_from_spool_extracts_pulgadas():
    """from_spool() correctly copies pulgadas fields."""
    spool = make_spool(pulgadas_arm=24.5, pulgadas_sold=12.0)
    status = SpoolStatus.from_spool(spool)
    assert status.pulgadas_arm == 24.5
    assert status.pulgadas_sold == 12.0


# ==================== COMPUTED FIELDS ====================


def test_from_spool_none_estado_detalle_gives_libre():
    """None estado_detalle → estado_trabajo=LIBRE, computed fields None."""
    spool = make_spool(estado_detalle=None)
    status = SpoolStatus.from_spool(spool)
    assert status.estado_trabajo == "LIBRE"
    assert status.operacion_actual is None
    assert status.ciclo_rep is None


def test_from_spool_arm_en_progreso():
    """ARM EN_PROGRESO estado_detalle → computed fields populated correctly."""
    spool = make_spool(
        ocupado_por="MR(93)",
        estado_detalle="MR(93) trabajando ARM (ARM en progreso, SOLD pendiente)"
    )
    status = SpoolStatus.from_spool(spool)
    assert status.operacion_actual == "ARM"
    assert status.estado_trabajo == "EN_PROGRESO"
    assert status.ciclo_rep is None


def test_from_spool_sold_en_progreso():
    """SOLD EN_PROGRESO estado_detalle → computed fields populated correctly."""
    spool = make_spool(
        ocupado_por="JP(94)",
        estado_detalle="JP(94) trabajando SOLD (ARM completado, SOLD en progreso)"
    )
    status = SpoolStatus.from_spool(spool)
    assert status.operacion_actual == "SOLD"
    assert status.estado_trabajo == "EN_PROGRESO"
    assert status.ciclo_rep is None


def test_from_spool_rechazado_ciclo_2():
    """RECHAZADO ciclo 2 → ciclo_rep=2 computed correctly."""
    spool = make_spool(
        estado_detalle="Disponible - ARM completado, SOLD completado, RECHAZADO (Ciclo 2/3) - Pendiente reparacion"
    )
    status = SpoolStatus.from_spool(spool)
    assert status.estado_trabajo == "RECHAZADO"
    assert status.ciclo_rep == 2


def test_from_spool_bloqueado():
    """BLOQUEADO estado_detalle → BLOQUEADO estado_trabajo."""
    spool = make_spool(estado_detalle="BLOQUEADO - Contactar supervisor")
    status = SpoolStatus.from_spool(spool)
    assert status.estado_trabajo == "BLOQUEADO"
    assert status.operacion_actual is None


def test_from_spool_en_reparacion():
    """EN_REPARACION ciclo 1 → REPARACION operacion_actual, ciclo_rep=1."""
    spool = make_spool(
        ocupado_por="MR(93)",
        estado_detalle="EN_REPARACION (Ciclo 1/3) - Ocupado: MR(93)"
    )
    status = SpoolStatus.from_spool(spool)
    assert status.operacion_actual == "REPARACION"
    assert status.estado_trabajo == "EN_PROGRESO"
    assert status.ciclo_rep == 1


def test_from_spool_completado():
    """METROLOGIA APROBADO → COMPLETADO estado_trabajo."""
    spool = make_spool(
        estado_detalle="Disponible - ARM completado, SOLD completado, METROLOGIA APROBADO \u2713"
    )
    status = SpoolStatus.from_spool(spool)
    assert status.estado_trabajo == "COMPLETADO"


# ==================== BatchStatusRequest VALIDATION ====================


def test_batch_request_valid():
    """Valid tags list passes validation."""
    req = BatchStatusRequest(tags=["TAG-001", "TAG-002"])
    assert len(req.tags) == 2


def test_batch_request_single_tag():
    """Single tag (min_length=1) is valid."""
    req = BatchStatusRequest(tags=["TAG-001"])
    assert len(req.tags) == 1


def test_batch_request_empty_tags_fails():
    """Empty tags list fails min_length validation."""
    with pytest.raises(ValidationError):
        BatchStatusRequest(tags=[])


def test_batch_request_too_many_tags_fails():
    """More than 100 tags fails max_length validation."""
    tags = [f"TAG-{i:03d}" for i in range(101)]
    with pytest.raises(ValidationError):
        BatchStatusRequest(tags=tags)


def test_batch_request_100_tags_passes():
    """Exactly 100 tags passes max_length validation."""
    tags = [f"TAG-{i:03d}" for i in range(100)]
    req = BatchStatusRequest(tags=tags)
    assert len(req.tags) == 100


# ==================== BatchStatusResponse STRUCTURE ====================


def test_batch_response_structure():
    """BatchStatusResponse contains spools list and total."""
    spool = make_spool(tag_spool="TAG-001")
    status = SpoolStatus.from_spool(spool)
    response = BatchStatusResponse(spools=[status], total=1)
    assert response.total == 1
    assert len(response.spools) == 1
    assert response.spools[0].tag_spool == "TAG-001"


def test_batch_response_empty():
    """BatchStatusResponse with empty spools list is valid."""
    response = BatchStatusResponse(spools=[], total=0)
    assert response.total == 0
    assert response.spools == []
