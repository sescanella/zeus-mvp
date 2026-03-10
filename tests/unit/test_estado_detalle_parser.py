"""
Unit tests for parse_estado_detalle() - Estado_Detalle string parser.

Tests validate all known Estado_Detalle formats produced by EstadoDetalleBuilder.

Reference:
- Service: backend/services/estado_detalle_parser.py
- Plan: 00-01-PLAN.md (API-01)
"""
import pytest

from backend.services.estado_detalle_parser import parse_estado_detalle


# ==================== NULL / EMPTY INPUTS ====================


def test_parse_none_returns_defaults():
    """None input returns LIBRE defaults."""
    result = parse_estado_detalle(None)
    assert result["operacion_actual"] is None
    assert result["estado_trabajo"] == "LIBRE"
    assert result["ciclo_rep"] is None
    assert result["worker"] is None


def test_parse_empty_string_returns_defaults():
    """Empty string returns LIBRE defaults."""
    result = parse_estado_detalle("")
    assert result["operacion_actual"] is None
    assert result["estado_trabajo"] == "LIBRE"
    assert result["ciclo_rep"] is None
    assert result["worker"] is None


def test_parse_whitespace_only_returns_defaults():
    """Whitespace-only string returns LIBRE defaults."""
    result = parse_estado_detalle("   ")
    assert result["operacion_actual"] is None
    assert result["estado_trabajo"] == "LIBRE"
    assert result["ciclo_rep"] is None
    assert result["worker"] is None


# ==================== OCCUPIED (EN_PROGRESO) STATES ====================


def test_parse_arm_en_progreso():
    """Worker doing ARM — EN_PROGRESO with ARM operacion_actual."""
    result = parse_estado_detalle("MR(93) trabajando ARM (ARM en progreso, SOLD pendiente)")
    assert result["operacion_actual"] == "ARM"
    assert result["estado_trabajo"] == "EN_PROGRESO"
    assert result["worker"] == "MR(93)"
    assert result["ciclo_rep"] is None


def test_parse_sold_en_progreso():
    """Worker doing SOLD — EN_PROGRESO with SOLD operacion_actual."""
    result = parse_estado_detalle("MR(93) trabajando SOLD (ARM completado, SOLD en progreso)")
    assert result["operacion_actual"] == "SOLD"
    assert result["estado_trabajo"] == "EN_PROGRESO"
    assert result["worker"] == "MR(93)"
    assert result["ciclo_rep"] is None


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
    assert result["ciclo_rep"] is None
    assert result["worker"] is None


# ==================== COMPLETADO STATES ====================


def test_parse_metrologia_aprobado():
    """METROLOGIA APROBADO — COMPLETADO state."""
    result = parse_estado_detalle(
        "Disponible - ARM completado, SOLD completado, METROLOGIA APROBADO \u2713"
    )
    assert result["estado_trabajo"] == "COMPLETADO"


def test_parse_arm_y_sold_completados():
    """Both ARM and SOLD completado (without METROLOGIA) — COMPLETADO."""
    result = parse_estado_detalle("Disponible - ARM completado, SOLD completado")
    assert result["estado_trabajo"] == "COMPLETADO"


# ==================== RECHAZADO STATES ====================


def test_parse_rechazado_ciclo_2():
    """RECHAZADO with ciclo 2/3 — extracts ciclo_rep correctly."""
    result = parse_estado_detalle(
        "Disponible - ARM completado, SOLD completado, RECHAZADO (Ciclo 2/3) - Pendiente reparacion"
    )
    assert result["estado_trabajo"] == "RECHAZADO"
    assert result["ciclo_rep"] == 2


def test_parse_rechazado_ciclo_1():
    """RECHAZADO with ciclo 1/3 — extracts ciclo_rep correctly."""
    result = parse_estado_detalle(
        "Disponible - RECHAZADO (Ciclo 1/3) - Pendiente reparacion"
    )
    assert result["estado_trabajo"] == "RECHAZADO"
    assert result["ciclo_rep"] == 1


def test_parse_rechazado_ciclo_3():
    """RECHAZADO with ciclo 3/3 — extracts ciclo_rep correctly."""
    result = parse_estado_detalle(
        "Disponible - RECHAZADO (Ciclo 3/3) - Pendiente reparacion"
    )
    assert result["estado_trabajo"] == "RECHAZADO"
    assert result["ciclo_rep"] == 3


# ==================== BLOQUEADO STATES ====================


def test_parse_bloqueado():
    """BLOQUEADO — returns BLOQUEADO estado_trabajo."""
    result = parse_estado_detalle("BLOQUEADO - Contactar supervisor")
    assert result["estado_trabajo"] == "BLOQUEADO"
    assert result["operacion_actual"] is None
    assert result["ciclo_rep"] is None


# ==================== PENDIENTE_METROLOGIA STATES ====================


def test_parse_reparacion_completado_pendiente_metrologia():
    """REPARACION completado transitioning to PENDIENTE_METROLOGIA."""
    result = parse_estado_detalle("REPARACION completado - PENDIENTE_METROLOGIA")
    assert result["estado_trabajo"] == "PENDIENTE_METROLOGIA"
    assert result["operacion_actual"] is None
    assert result["ciclo_rep"] is None


def test_parse_pendiente_metrologia_explicit():
    """Explicit PENDIENTE_METROLOGIA in string."""
    result = parse_estado_detalle("Disponible - PENDIENTE_METROLOGIA")
    assert result["estado_trabajo"] == "PENDIENTE_METROLOGIA"


# ==================== REPARACION EN_PROGRESO ====================


def test_parse_en_reparacion_ciclo_1():
    """EN_REPARACION ciclo 1 — REPARACION operacion_actual EN_PROGRESO."""
    result = parse_estado_detalle("EN_REPARACION (Ciclo 1/3) - Ocupado: MR(93)")
    assert result["operacion_actual"] == "REPARACION"
    assert result["estado_trabajo"] == "EN_PROGRESO"
    assert result["ciclo_rep"] == 1


def test_parse_en_reparacion_ciclo_2():
    """EN_REPARACION ciclo 2 — extracts ciclo_rep."""
    result = parse_estado_detalle("EN_REPARACION (Ciclo 2/3) - Ocupado: JP(94)")
    assert result["operacion_actual"] == "REPARACION"
    assert result["estado_trabajo"] == "EN_PROGRESO"
    assert result["ciclo_rep"] == 2


# ==================== RETURN STRUCTURE ====================


def test_parse_returns_all_keys():
    """Result dict always contains all expected keys."""
    result = parse_estado_detalle(None)
    assert "operacion_actual" in result
    assert "estado_trabajo" in result
    assert "ciclo_rep" in result
    assert "worker" in result


def test_parse_en_progreso_has_no_ciclo_rep():
    """EN_PROGRESO ARM state has no ciclo_rep."""
    result = parse_estado_detalle("MR(93) trabajando ARM (ARM en progreso, SOLD pendiente)")
    assert result["ciclo_rep"] is None
