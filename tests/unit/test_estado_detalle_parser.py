"""
Unit tests for parse_estado_detalle() - Estado_Detalle string parser.

Tests validate all Estado_Detalle formats the backend produces today plus the
two legacy formats from the removed 3-cycle limit (`"RECHAZADO (Ciclo N/3)"`
and `"BLOQUEADO - Contactar supervisor"`), which must be tolerated without
a Sheet migration and mapped to plain RECHAZADO.

Reference:
- Service: backend/services/estado_detalle_parser.py
"""
from backend.services.estado_detalle_parser import parse_estado_detalle


# ==================== NULL / EMPTY INPUTS ====================


def test_parse_none_returns_defaults():
    """None input returns LIBRE defaults."""
    result = parse_estado_detalle(None)
    assert result["operacion_actual"] is None
    assert result["estado_trabajo"] == "LIBRE"
    assert result["worker"] is None


def test_parse_empty_string_returns_defaults():
    """Empty string returns LIBRE defaults."""
    result = parse_estado_detalle("")
    assert result["operacion_actual"] is None
    assert result["estado_trabajo"] == "LIBRE"
    assert result["worker"] is None


def test_parse_whitespace_only_returns_defaults():
    """Whitespace-only string returns LIBRE defaults."""
    result = parse_estado_detalle("   ")
    assert result["operacion_actual"] is None
    assert result["estado_trabajo"] == "LIBRE"
    assert result["worker"] is None


# ==================== OCCUPIED (EN_PROGRESO) STATES ====================


def test_parse_arm_en_progreso():
    """Worker doing ARM — EN_PROGRESO with ARM operacion_actual."""
    result = parse_estado_detalle("MR(93) trabajando ARM (ARM en progreso, SOLD pendiente)")
    assert result["operacion_actual"] == "ARM"
    assert result["estado_trabajo"] == "EN_PROGRESO"
    assert result["worker"] == "MR(93)"


def test_parse_sold_en_progreso():
    """Worker doing SOLD — EN_PROGRESO with SOLD operacion_actual."""
    result = parse_estado_detalle("MR(93) trabajando SOLD (ARM completado, SOLD en progreso)")
    assert result["operacion_actual"] == "SOLD"
    assert result["estado_trabajo"] == "EN_PROGRESO"
    assert result["worker"] == "MR(93)"


def test_parse_different_worker_format():
    """Worker with different initials format."""
    result = parse_estado_detalle("JP(94) trabajando ARM (ARM en progreso, SOLD pendiente)")
    assert result["worker"] == "JP(94)"
    assert result["operacion_actual"] == "ARM"
    assert result["estado_trabajo"] == "EN_PROGRESO"


# ==================== PAUSADO STATES ====================


def test_parse_disponible_arm_completado_sold_pendiente():
    """ARM done, SOLD pending — PAUSADO with ARM as operacion_actual."""
    result = parse_estado_detalle("Disponible - ARM completado, SOLD pendiente")
    assert result["operacion_actual"] == "ARM"
    assert result["estado_trabajo"] == "PAUSADO"
    assert result["worker"] is None


# ==================== COMPLETADO STATES ====================


def test_parse_metrologia_aprobado():
    """METROLOGIA APROBADO — COMPLETADO state."""
    result = parse_estado_detalle(
        "Disponible - ARM completado, SOLD completado, METROLOGIA APROBADO ✓"
    )
    assert result["estado_trabajo"] == "COMPLETADO"


def test_parse_arm_y_sold_completados():
    """Both ARM and SOLD completado (without METROLOGIA) — COMPLETADO."""
    result = parse_estado_detalle("Disponible - ARM completado, SOLD completado")
    assert result["estado_trabajo"] == "COMPLETADO"


# ==================== RECHAZADO STATES ====================


def test_parse_rechazado_plain():
    """Current format written by the state machine after rejection."""
    result = parse_estado_detalle("RECHAZADO - Pendiente reparación")
    assert result["estado_trabajo"] == "RECHAZADO"


def test_parse_rechazado_legacy_with_cycle():
    """Legacy 'RECHAZADO (Ciclo N/3)' from the removed 3-cycle limit must
    still parse as plain RECHAZADO — old sheet rows keep flowing."""
    result = parse_estado_detalle(
        "Disponible - RECHAZADO (Ciclo 2/3) - Pendiente reparacion"
    )
    assert result["estado_trabajo"] == "RECHAZADO"


def test_parse_bloqueado_legacy_maps_to_rechazado():
    """Legacy 'BLOQUEADO - Contactar supervisor' (3-cycle limit, removed)
    must be tolerated and mapped to RECHAZADO so the spool can be repaired."""
    result = parse_estado_detalle("BLOQUEADO - Contactar supervisor")
    assert result["estado_trabajo"] == "RECHAZADO"


# ==================== PENDIENTE_METROLOGIA STATES ====================


def test_parse_reparacion_completado_pendiente_metrologia():
    """REPARACION completado transitioning to PENDIENTE_METROLOGIA."""
    result = parse_estado_detalle("REPARACION completado - PENDIENTE_METROLOGIA")
    assert result["estado_trabajo"] == "PENDIENTE_METROLOGIA"
    assert result["operacion_actual"] is None


def test_parse_pendiente_metrologia_explicit():
    """Explicit PENDIENTE_METROLOGIA in string."""
    result = parse_estado_detalle("Disponible - PENDIENTE_METROLOGIA")
    assert result["estado_trabajo"] == "PENDIENTE_METROLOGIA"


# ==================== REPARACION EN_PROGRESO ====================


def test_parse_en_reparacion_plain():
    """Current format written by the state machine when repair starts."""
    result = parse_estado_detalle("EN_REPARACION - Ocupado: MR(93)")
    assert result["operacion_actual"] == "REPARACION"
    assert result["estado_trabajo"] == "EN_PROGRESO"


def test_parse_en_reparacion_legacy_with_cycle():
    """Legacy 'EN_REPARACION (Ciclo N/3) - Ocupado: ...' still parses."""
    result = parse_estado_detalle("EN_REPARACION (Ciclo 2/3) - Ocupado: JP(94)")
    assert result["operacion_actual"] == "REPARACION"
    assert result["estado_trabajo"] == "EN_PROGRESO"


# ==================== RETURN STRUCTURE ====================


def test_parse_returns_all_keys():
    """Result dict always contains all expected keys."""
    result = parse_estado_detalle(None)
    assert "operacion_actual" in result
    assert "estado_trabajo" in result
    assert "worker" in result
