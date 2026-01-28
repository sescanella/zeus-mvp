"""
Unit tests for CycleCounterService (Phase 6).

Tests cycle counting logic for reparación loop prevention.
"""

import pytest
from backend.services.cycle_counter_service import CycleCounterService


@pytest.fixture
def cycle_counter():
    """Fixture providing CycleCounterService instance."""
    return CycleCounterService()


# ==================== EXTRACTION TESTS ====================

def test_extract_cycle_from_rechazado_estado(cycle_counter):
    """Should extract cycle number from RECHAZADO estado."""
    estado = "RECHAZADO (Ciclo 2/3) - Pendiente reparación"
    assert cycle_counter.extract_cycle_count(estado) == 2


def test_extract_cycle_from_first_rejection(cycle_counter):
    """Should extract cycle 1 from first rejection."""
    estado = "RECHAZADO (Ciclo 1/3) - Pendiente reparación"
    assert cycle_counter.extract_cycle_count(estado) == 1


def test_extract_cycle_from_third_rejection(cycle_counter):
    """Should extract cycle 3 from third rejection."""
    estado = "RECHAZADO (Ciclo 3/3) - Pendiente reparación"
    assert cycle_counter.extract_cycle_count(estado) == 3


def test_extract_returns_max_for_bloqueado(cycle_counter):
    """Should return MAX_CYCLES for BLOQUEADO estado."""
    estado = "BLOQUEADO - Contactar supervisor"
    assert cycle_counter.extract_cycle_count(estado) == cycle_counter.MAX_CYCLES


def test_extract_returns_zero_for_no_cycle(cycle_counter):
    """Should return 0 when no cycle info found."""
    test_cases = [
        "PENDIENTE_METROLOGIA",
        "METROLOGIA_APROBADO ✓",
        "Disponible - ARM completado, SOLD pendiente",
        "",
        None
    ]

    for estado in test_cases:
        assert cycle_counter.extract_cycle_count(estado or "") == 0


def test_extract_handles_en_reparacion_estado(cycle_counter):
    """Should extract cycle from EN_REPARACION estado."""
    estado = "EN_REPARACION (Ciclo 2/3) - Ocupado: MR(93)"
    assert cycle_counter.extract_cycle_count(estado) == 2


def test_extract_handles_reparacion_pausada_estado(cycle_counter):
    """Should extract cycle from REPARACION_PAUSADA estado."""
    estado = "REPARACION_PAUSADA (Ciclo 2/3)"
    assert cycle_counter.extract_cycle_count(estado) == 2


# ==================== INCREMENT TESTS ====================

def test_increment_cycle_normal(cycle_counter):
    """Should increment cycle from 0 to 1."""
    assert cycle_counter.increment_cycle(0) == 1


def test_increment_cycle_from_one_to_two(cycle_counter):
    """Should increment cycle from 1 to 2."""
    assert cycle_counter.increment_cycle(1) == 2


def test_increment_cycle_from_two_to_three(cycle_counter):
    """Should increment cycle from 2 to 3."""
    assert cycle_counter.increment_cycle(2) == 3


def test_increment_caps_at_max(cycle_counter):
    """Should cap increment at MAX_CYCLES (3)."""
    assert cycle_counter.increment_cycle(3) == 3
    assert cycle_counter.increment_cycle(4) == 3


# ==================== BLOCKING LOGIC TESTS ====================

def test_should_block_at_max_cycles(cycle_counter):
    """Should block when cycle reaches MAX_CYCLES."""
    assert cycle_counter.should_block(3) is True


def test_should_block_above_max(cycle_counter):
    """Should block when cycle exceeds MAX_CYCLES."""
    assert cycle_counter.should_block(4) is True


def test_should_not_block_below_max(cycle_counter):
    """Should NOT block when cycle below MAX_CYCLES."""
    assert cycle_counter.should_block(0) is False
    assert cycle_counter.should_block(1) is False
    assert cycle_counter.should_block(2) is False


# ==================== ESTADO BUILDING TESTS ====================

def test_build_rechazado_with_cycle_one(cycle_counter):
    """Should build RECHAZADO estado with cycle 1."""
    estado = cycle_counter.build_rechazado_estado(1)
    assert estado == "RECHAZADO (Ciclo 1/3) - Pendiente reparación"


def test_build_rechazado_with_cycle_two(cycle_counter):
    """Should build RECHAZADO estado with cycle 2."""
    estado = cycle_counter.build_rechazado_estado(2)
    assert estado == "RECHAZADO (Ciclo 2/3) - Pendiente reparación"


def test_build_rechazado_with_cycle_three(cycle_counter):
    """Should build RECHAZADO estado with cycle 3."""
    estado = cycle_counter.build_rechazado_estado(3)
    assert estado == "BLOQUEADO - Contactar supervisor"


def test_build_bloqueado_at_limit(cycle_counter):
    """Should build BLOQUEADO estado when at cycle limit."""
    estado = cycle_counter.build_rechazado_estado(cycle_counter.MAX_CYCLES)
    assert "BLOQUEADO" in estado
    assert "supervisor" in estado


def test_build_en_reparacion_with_worker(cycle_counter):
    """Should build EN_REPARACION estado with worker name."""
    estado = cycle_counter.build_reparacion_estado("en_reparacion", 2, "MR(93)")
    assert estado == "EN_REPARACION (Ciclo 2/3) - Ocupado: MR(93)"


def test_build_en_reparacion_without_worker(cycle_counter):
    """Should build EN_REPARACION estado without worker name."""
    estado = cycle_counter.build_reparacion_estado("en_reparacion", 2)
    assert estado == "EN_REPARACION (Ciclo 2/3)"


def test_build_reparacion_pausada(cycle_counter):
    """Should build REPARACION_PAUSADA estado."""
    estado = cycle_counter.build_reparacion_estado("reparacion_pausada", 2)
    assert estado == "REPARACION_PAUSADA (Ciclo 2/3)"


def test_build_reparacion_handles_unknown_state(cycle_counter):
    """Should handle unknown state gracefully."""
    estado = cycle_counter.build_reparacion_estado("unknown_state", 2)
    assert "Ciclo 2/3" in estado


def test_reset_cycle_removes_info(cycle_counter):
    """Should reset cycle and return APROBADO estado."""
    estado = cycle_counter.reset_cycle()
    assert estado == "METROLOGIA_APROBADO ✓"
    assert "Ciclo" not in estado


# ==================== INTEGRATION SCENARIOS ====================

def test_full_cycle_progression(cycle_counter):
    """Should handle complete cycle progression: 0 → 1 → 2 → 3 → BLOQUEADO."""
    # Initial state (no cycle)
    estado_inicial = "METROLOGIA RECHAZADO - Pendiente reparación"
    cycle = cycle_counter.extract_cycle_count(estado_inicial)
    assert cycle == 0

    # First rejection
    cycle = cycle_counter.increment_cycle(cycle)
    assert cycle == 1
    assert not cycle_counter.should_block(cycle)
    estado = cycle_counter.build_rechazado_estado(cycle)
    assert "Ciclo 1/3" in estado

    # Second rejection
    cycle = cycle_counter.extract_cycle_count(estado)
    cycle = cycle_counter.increment_cycle(cycle)
    assert cycle == 2
    assert not cycle_counter.should_block(cycle)
    estado = cycle_counter.build_rechazado_estado(cycle)
    assert "Ciclo 2/3" in estado

    # Third rejection
    cycle = cycle_counter.extract_cycle_count(estado)
    cycle = cycle_counter.increment_cycle(cycle)
    assert cycle == 3
    assert cycle_counter.should_block(cycle)
    estado = cycle_counter.build_rechazado_estado(cycle)
    assert "BLOQUEADO" in estado


def test_cycle_reset_after_approval(cycle_counter):
    """Should reset cycle after APROBADO."""
    # Start with cycle 2
    estado_rechazado = "RECHAZADO (Ciclo 2/3) - Pendiente reparación"
    cycle = cycle_counter.extract_cycle_count(estado_rechazado)
    assert cycle == 2

    # Reset on approval
    estado_aprobado = cycle_counter.reset_cycle()
    cycle_after_reset = cycle_counter.extract_cycle_count(estado_aprobado)
    assert cycle_after_reset == 0


def test_extraction_from_complex_estado(cycle_counter):
    """Should extract cycle from complex estado strings."""
    test_cases = [
        ("EN_REPARACION (Ciclo 1/3) - Ocupado: JP(94)", 1),
        ("REPARACION_PAUSADA (Ciclo 3/3)", 3),
        ("RECHAZADO (Ciclo 2/3) - Pendiente reparación (worker: MR(93))", 2),
    ]

    for estado, expected_cycle in test_cases:
        assert cycle_counter.extract_cycle_count(estado) == expected_cycle
