"""
Unit tests for parse_estado_detalle() - Estado_Detalle string parser.

Tests validate all known Estado_Detalle formats produced by EstadoDetalleBuilder.
"""
import pytest

from backend.services.estado_detalle_parser import parse_estado_detalle


# ==================== NULL / EMPTY INPUTS ====================


def test_parse_none_returns_defaults():
    result = parse_estado_detalle(None)
    assert result["operacion_actual"] is None
    assert result["estado_trabajo"] == "LIBRE"
    assert result["worker"] is None


def test_parse_empty_string_returns_defaults():
    result = parse_estado_detalle("")
    assert result["operacion_actual"] is None
    assert result["estado_trabajo"] == "LIBRE"
    assert result["worker"] is None


def test_parse_whitespace_only_returns_defaults():
    result = parse_estado_detalle("   ")
    assert result["operacion_actual"] is None
    assert result["estado_trabajo"] == "LIBRE"
    assert result["worker"] is None


# ==================== OCCUPIED (EN_PROGRESO) STATES ====================


def test_parse_arm_en_progreso():
    result = parse_estado_detalle("MR(93) trabajando ARM (ARM en progreso, SOLD pendiente)")
    assert result["operacion_actual"] == "ARM"
    assert result["estado_trabajo"] == "EN_PROGRESO"
    assert result["worker"] == "MR(93)"


def test_parse_sold_en_progreso():
    result = parse_estado_detalle("MR(93) trabajando SOLD (ARM completado, SOLD en progreso)")
    assert result["operacion_actual"] == "SOLD"
    assert result["estado_trabajo"] == "EN_PROGRESO"
    assert result["worker"] == "MR(93)"


def test_parse_different_worker_format():
    result = parse_estado_detalle("JP(94) trabajando ARM (ARM en progreso, SOLD pendiente)")
    assert result["worker"] == "JP(94)"
    assert result["operacion_actual"] == "ARM"
    assert result["estado_trabajo"] == "EN_PROGRESO"


# ==================== PAUSADO STATES ====================


def test_parse_disponible_arm_completado_sold_pendiente():
    result = parse_estado_detalle("Disponible - ARM completado, SOLD pendiente")
    assert result["operacion_actual"] == "ARM"
    assert result["estado_trabajo"] == "PAUSADO"
    assert result["worker"] is None


# ==================== COMPLETADO STATES ====================


def test_parse_metrologia_aprobado():
    result = parse_estado_detalle(
        "Disponible - ARM completado, SOLD completado, METROLOGIA APROBADO ✓"
    )
    assert result["estado_trabajo"] == "COMPLETADO"


def test_parse_arm_y_sold_completados():
    result = parse_estado_detalle("Disponible - ARM completado, SOLD completado")
    assert result["estado_trabajo"] == "COMPLETADO"


# ==================== RECHAZADO STATES ====================


def test_parse_rechazado():
    """RECHAZADO simple — sin ciclo embebido."""
    result = parse_estado_detalle("RECHAZADO - Pendiente reparación")
    assert result["estado_trabajo"] == "RECHAZADO"


def test_parse_rechazado_with_disponible_prefix():
    result = parse_estado_detalle("Disponible - ARM completado, SOLD completado, RECHAZADO - Pendiente reparación")
    assert result["estado_trabajo"] == "RECHAZADO"


# ==================== PENDIENTE_METROLOGIA STATES ====================


def test_parse_reparacion_completado_pendiente_metrologia():
    result = parse_estado_detalle("REPARACION completado - PENDIENTE_METROLOGIA")
    assert result["estado_trabajo"] == "PENDIENTE_METROLOGIA"
    assert result["operacion_actual"] is None


def test_parse_pendiente_metrologia_explicit():
    result = parse_estado_detalle("Disponible - PENDIENTE_METROLOGIA")
    assert result["estado_trabajo"] == "PENDIENTE_METROLOGIA"


# ==================== REPARACION EN_PROGRESO ====================


def test_parse_en_reparacion():
    result = parse_estado_detalle("EN_REPARACION - Ocupado: MR(93)")
    assert result["operacion_actual"] == "REPARACION"
    assert result["estado_trabajo"] == "EN_PROGRESO"


# ==================== RETURN STRUCTURE ====================


def test_parse_returns_all_keys():
    result = parse_estado_detalle(None)
    assert "operacion_actual" in result
    assert "estado_trabajo" in result
    assert "worker" in result
