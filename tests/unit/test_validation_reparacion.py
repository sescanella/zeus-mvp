"""
Unit tests for reparación validation logic.

Tests validar_puede_tomar_reparacion() and validar_puede_cancelar_reparacion().
"""

import pytest
from unittest.mock import Mock
from backend.services.validation_service import ValidationService
from backend.models.spool import Spool
from backend.exceptions import (
    OperacionNoDisponibleError,
    SpoolOccupiedError,
    OperacionNoIniciadaError
)


@pytest.fixture
def validation_service():
    return ValidationService(role_service=None)


@pytest.fixture
def mock_spool():
    spool = Mock(spec=Spool)
    spool.tag_spool = "SPOOL-001"
    spool.ocupado_por = None
    spool.fecha_materiales = "01-01-2026"
    spool.armador = "MR(93)"
    spool.fecha_armado = "01-01-2026"
    spool.soldador = "JP(94)"
    spool.fecha_soldadura = "02-01-2026"
    spool.fecha_qc_metrologia = "03-01-2026"
    spool.estado_detalle = "RECHAZADO - Pendiente reparación"
    return spool


# ==================== TOMAR REPARACION - RECHAZADO VALIDATION ====================

def test_can_tomar_rechazado_spool(validation_service, mock_spool):
    """Should allow TOMAR when spool is RECHAZADO and not occupied."""
    mock_spool.estado_detalle = "RECHAZADO - Pendiente reparación"
    mock_spool.ocupado_por = None
    assert validation_service.validar_puede_tomar_reparacion(mock_spool, worker_id=93) is None


def test_can_tomar_metrologia_rechazado(validation_service, mock_spool):
    """Should allow TOMAR when spool has METROLOGIA RECHAZADO estado."""
    mock_spool.estado_detalle = "METROLOGIA RECHAZADO - Pendiente reparación"
    mock_spool.ocupado_por = None
    assert validation_service.validar_puede_tomar_reparacion(mock_spool, worker_id=93) is None


# ==================== TOMAR REPARACION - ESTADO VALIDATION ====================

def test_cannot_repair_aprobado_spool(validation_service, mock_spool):
    """Should raise OperacionNoDisponibleError when spool is APROBADO."""
    mock_spool.estado_detalle = "METROLOGIA APROBADO ✓"

    with pytest.raises(OperacionNoDisponibleError) as exc_info:
        validation_service.validar_puede_tomar_reparacion(mock_spool, worker_id=93)

    assert exc_info.value.data["operacion"] == "REPARACION"
    assert "RECHAZADOS" in exc_info.value.message


def test_cannot_repair_pendiente_metrologia(validation_service, mock_spool):
    """Should raise OperacionNoDisponibleError when spool is PENDIENTE_METROLOGIA."""
    mock_spool.estado_detalle = "PENDIENTE_METROLOGIA"
    with pytest.raises(OperacionNoDisponibleError):
        validation_service.validar_puede_tomar_reparacion(mock_spool, worker_id=93)


def test_cannot_repair_arm_en_progreso(validation_service, mock_spool):
    """Should raise OperacionNoDisponibleError when spool in ARM production state."""
    mock_spool.estado_detalle = "MR(93) trabajando ARM (ARM en progreso, SOLD pendiente)"
    with pytest.raises(OperacionNoDisponibleError):
        validation_service.validar_puede_tomar_reparacion(mock_spool, worker_id=93)


def test_cannot_repair_null_estado(validation_service, mock_spool):
    """Should raise OperacionNoDisponibleError when estado_detalle is None."""
    mock_spool.estado_detalle = None
    with pytest.raises(OperacionNoDisponibleError):
        validation_service.validar_puede_tomar_reparacion(mock_spool, worker_id=93)


# ==================== TOMAR REPARACION - OCCUPATION VALIDATION ====================

def test_cannot_tomar_occupied_spool(validation_service, mock_spool):
    """Should raise SpoolOccupiedError when spool is occupied."""
    mock_spool.estado_detalle = "RECHAZADO - Pendiente reparación"
    mock_spool.ocupado_por = "JP(94)"

    with pytest.raises(SpoolOccupiedError) as exc_info:
        validation_service.validar_puede_tomar_reparacion(mock_spool, worker_id=93)

    assert exc_info.value.data["owner_id"] == 94
    assert exc_info.value.data["owner_name"] == "JP(94)"


def test_cannot_tomar_en_reparacion_occupied(validation_service, mock_spool):
    """Should raise OperacionNoDisponibleError when spool is EN_REPARACION (not RECHAZADO)."""
    mock_spool.estado_detalle = "EN_REPARACION - Ocupado: MR(93)"
    mock_spool.ocupado_por = "MR(93)"
    with pytest.raises(OperacionNoDisponibleError):
        validation_service.validar_puede_tomar_reparacion(mock_spool, worker_id=94)


def test_can_tomar_after_reparacion_pausada(validation_service, mock_spool):
    """Should allow TOMAR after PAUSAR (REPARACION_PAUSADA accepted)."""
    mock_spool.estado_detalle = "REPARACION_PAUSADA"
    mock_spool.ocupado_por = None
    assert validation_service.validar_puede_tomar_reparacion(mock_spool, worker_id=93) is None


# ==================== CANCELAR REPARACION VALIDATION ====================

def test_can_cancelar_en_reparacion(validation_service, mock_spool):
    """Should allow CANCELAR when spool is EN_REPARACION."""
    mock_spool.estado_detalle = "EN_REPARACION - Ocupado: MR(93)"
    mock_spool.ocupado_por = "MR(93)"
    assert validation_service.validar_puede_cancelar_reparacion(mock_spool, "MR(93)", worker_id=93) is None


def test_can_cancelar_reparacion_pausada(validation_service, mock_spool):
    """Should allow CANCELAR when spool is REPARACION_PAUSADA."""
    mock_spool.estado_detalle = "REPARACION_PAUSADA"
    mock_spool.ocupado_por = None
    assert validation_service.validar_puede_cancelar_reparacion(mock_spool, "MR(93)", worker_id=93) is None


def test_cannot_cancelar_rechazado(validation_service, mock_spool):
    """Should raise OperacionNoIniciadaError when trying to CANCELAR RECHAZADO spool."""
    mock_spool.estado_detalle = "RECHAZADO - Pendiente reparación"

    with pytest.raises(OperacionNoIniciadaError) as exc_info:
        validation_service.validar_puede_cancelar_reparacion(mock_spool, "MR(93)", worker_id=93)

    assert exc_info.value.data["operacion"] == "REPARACION"


def test_cannot_cancelar_aprobado(validation_service, mock_spool):
    """Should raise OperacionNoIniciadaError when trying to CANCELAR APROBADO spool."""
    mock_spool.estado_detalle = "METROLOGIA APROBADO ✓"
    with pytest.raises(OperacionNoIniciadaError):
        validation_service.validar_puede_cancelar_reparacion(mock_spool, "MR(93)", worker_id=93)


# ==================== EDGE CASES ====================

def test_tomar_handles_malformed_ocupado_por(validation_service, mock_spool):
    """Should handle malformed ocupado_por format gracefully."""
    mock_spool.estado_detalle = "RECHAZADO - Pendiente reparación"
    mock_spool.ocupado_por = "InvalidFormat"

    with pytest.raises(SpoolOccupiedError) as exc_info:
        validation_service.validar_puede_tomar_reparacion(mock_spool, worker_id=93)

    assert exc_info.value.data["owner_id"] == 0
    assert exc_info.value.data["owner_name"] == "InvalidFormat"


def test_tomar_with_empty_estado_detalle(validation_service, mock_spool):
    """Should raise OperacionNoDisponibleError when estado_detalle is empty string."""
    mock_spool.estado_detalle = ""
    with pytest.raises(OperacionNoDisponibleError):
        validation_service.validar_puede_tomar_reparacion(mock_spool, worker_id=93)


def test_cancelar_with_null_estado(validation_service, mock_spool):
    """Should raise OperacionNoIniciadaError when estado_detalle is None."""
    mock_spool.estado_detalle = None
    with pytest.raises(OperacionNoIniciadaError):
        validation_service.validar_puede_cancelar_reparacion(mock_spool, "MR(93)", worker_id=93)


# ==================== ROLE VALIDATION (NO RESTRICTION) ====================

def test_any_worker_can_tomar_reparacion(validation_service, mock_spool):
    """Should allow any worker to TOMAR reparación (no role restriction)."""
    mock_spool.estado_detalle = "RECHAZADO - Pendiente reparación"
    mock_spool.ocupado_por = None
    for wid in [93, 94, 95]:
        assert validation_service.validar_puede_tomar_reparacion(mock_spool, worker_id=wid) is None
