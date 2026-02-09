"""
Unit tests for metrología prerequisite validation logic.

Tests ValidationService.validar_puede_completar_metrologia() which enforces:
- ARM completion prerequisite (fecha_armado != None)
- SOLD completion prerequisite (fecha_soldadura != None)
- Not already inspected (fecha_qc_metrologia == None)
- Spool not occupied (ocupado_por == None)
- Worker has METROLOGIA role (role validation)

These are fast, isolated unit tests using mocked dependencies.
"""

import pytest
from datetime import date
from unittest.mock import Mock

from backend.services.validation_service import ValidationService
from backend.models.spool import Spool
from backend.exceptions import (
    DependenciasNoSatisfechasError,
    OperacionYaCompletadaError,
    SpoolOccupiedError,
    RolNoAutorizadoError
)


# ============================================================================
# FIXTURES
# ============================================================================


@pytest.fixture
def validation_service():
    """ValidationService without role_service for testing."""
    return ValidationService(role_service=None)


@pytest.fixture
def ready_spool():
    """Spool ready for metrología inspection."""
    return Spool(
        tag_spool="UNIT-001",
        fecha_materiales=date(2026, 1, 20),
        fecha_armado=date(2026, 1, 22),
        fecha_soldadura=date(2026, 1, 25),
        fecha_qc_metrologia=None,
        armador="MR(93)",
        soldador="JP(94)",
        ocupado_por=None
    )


# ============================================================================
# PREREQUISITE VALIDATION TESTS
# ============================================================================


def test_validar_puede_completar_metrologia_success(validation_service, ready_spool):
    """Test validation passes for spool ready for inspection."""
    # Should not raise exception
    validation_service.validar_puede_completar_metrologia(ready_spool, worker_id=95)


def test_validar_puede_completar_metrologia_arm_not_completed(validation_service):
    """Test validation fails if ARM not completed (prerequisite 1)."""
    spool = Spool(
        tag_spool="UNIT-002",
        fecha_materiales=date(2026, 1, 20),
        fecha_armado=None,  # ARM not completed
        fecha_soldadura=date(2026, 1, 25),
        fecha_qc_metrologia=None,
        armador=None,
        soldador="JP(94)",
        ocupado_por=None
    )

    with pytest.raises(DependenciasNoSatisfechasError) as exc:
        validation_service.validar_puede_completar_metrologia(spool, worker_id=95)

    assert "ARM completado" in str(exc.value)


def test_validar_puede_completar_metrologia_sold_not_completed(validation_service):
    """Test validation fails if SOLD not completed (prerequisite 2)."""
    spool = Spool(
        tag_spool="UNIT-003",
        fecha_materiales=date(2026, 1, 20),
        fecha_armado=date(2026, 1, 22),
        fecha_soldadura=None,  # SOLD not completed
        fecha_qc_metrologia=None,
        armador="MR(93)",
        soldador=None,
        ocupado_por=None
    )

    with pytest.raises(DependenciasNoSatisfechasError) as exc:
        validation_service.validar_puede_completar_metrologia(spool, worker_id=95)

    assert "SOLD completado" in str(exc.value)


def test_validar_puede_completar_metrologia_already_completed(validation_service):
    """Test validation fails if metrología already completed (prerequisite 3)."""
    spool = Spool(
        tag_spool="UNIT-004",
        fecha_materiales=date(2026, 1, 20),
        fecha_armado=date(2026, 1, 22),
        fecha_soldadura=date(2026, 1, 25),
        fecha_qc_metrologia=date(2026, 1, 27),  # Already inspected
        armador="MR(93)",
        soldador="JP(94)",
        ocupado_por=None
    )

    with pytest.raises(OperacionYaCompletadaError) as exc:
        validation_service.validar_puede_completar_metrologia(spool, worker_id=95)

    assert "METROLOGIA" in str(exc.value)


def test_validar_puede_completar_metrologia_rechazado(validation_service):
    """Test validation fails if spool was RECHAZADO (needs reparación, not re-inspection)."""
    spool = Spool(
        tag_spool="UNIT-012",
        fecha_materiales=date(2026, 1, 20),
        fecha_armado=date(2026, 1, 22),
        fecha_soldadura=date(2026, 1, 25),
        fecha_qc_metrologia=None,  # No fecha (RECHAZADO no longer writes it)
        armador="MR(93)",
        soldador="JP(94)",
        ocupado_por=None,
        estado_detalle="METROLOGIA RECHAZADO - Pendiente reparación"
    )

    with pytest.raises(OperacionYaCompletadaError) as exc:
        validation_service.validar_puede_completar_metrologia(spool, worker_id=95)

    assert "METROLOGIA" in str(exc.value)


def test_validar_puede_completar_metrologia_bloqueado(validation_service):
    """Test validation fails if spool is BLOQUEADO (needs supervisor intervention)."""
    spool = Spool(
        tag_spool="UNIT-013",
        fecha_materiales=date(2026, 1, 20),
        fecha_armado=date(2026, 1, 22),
        fecha_soldadura=date(2026, 1, 25),
        fecha_qc_metrologia=None,
        armador="MR(93)",
        soldador="JP(94)",
        ocupado_por=None,
        estado_detalle="BLOQUEADO (3/3 rechazos)"
    )

    with pytest.raises(OperacionYaCompletadaError) as exc:
        validation_service.validar_puede_completar_metrologia(spool, worker_id=95)

    assert "METROLOGIA" in str(exc.value)


def test_validar_puede_completar_metrologia_spool_occupied(validation_service):
    """Test validation fails if spool is occupied (prerequisite 4)."""
    spool = Spool(
        tag_spool="UNIT-005",
        fecha_materiales=date(2026, 1, 20),
        fecha_armado=date(2026, 1, 22),
        fecha_soldadura=date(2026, 1, 25),
        fecha_qc_metrologia=None,
        armador="MR(93)",
        soldador="JP(94)",
        ocupado_por="MR(93):lock-token-abc"  # Occupied by another worker
    )

    with pytest.raises(SpoolOccupiedError) as exc:
        validation_service.validar_puede_completar_metrologia(spool, worker_id=95)

    assert "ocupado" in str(exc.value).lower()
    assert "MR(93)" in str(exc.value)


# ============================================================================
# ROLE VALIDATION TESTS (Note: Role validation for METROLOGIA not yet implemented)
# ============================================================================


# Role validation deferred - ValidationService.validar_puede_completar_metrologia()
# currently doesn't check role_service. This will be added in a future enhancement
# to match the pattern used for ARM/SOLD operations.


# ============================================================================
# STATE MACHINE TRANSITION TESTS
# ============================================================================


def test_state_machine_pendiente_to_aprobado():
    """Test state machine allows PENDIENTE → APROBADO transition."""
    from backend.domain.state_machines.metrologia_machine import MetrologiaStateMachine
    from unittest.mock import Mock

    # Mock dependencies
    mock_sheets_repo = Mock()
    mock_metadata_repo = Mock()

    machine = MetrologiaStateMachine(
        tag_spool="UNIT-006",
        sheets_repo=mock_sheets_repo,
        metadata_repo=mock_metadata_repo
    )

    # Initial state should be PENDIENTE
    assert machine.get_state_id() == "pendiente"

    # Trigger APROBADO transition
    machine.aprobar(fecha_operacion=date(2026, 1, 27))

    # State should be APROBADO (terminal)
    assert machine.get_state_id() == "aprobado"


def test_state_machine_pendiente_to_rechazado():
    """Test state machine allows PENDIENTE → RECHAZADO transition."""
    from backend.domain.state_machines.metrologia_machine import MetrologiaStateMachine
    from unittest.mock import Mock

    # Mock dependencies
    mock_sheets_repo = Mock()
    mock_metadata_repo = Mock()

    machine = MetrologiaStateMachine(
        tag_spool="UNIT-007",
        sheets_repo=mock_sheets_repo,
        metadata_repo=mock_metadata_repo
    )

    # Initial state should be PENDIENTE
    assert machine.get_state_id() == "pendiente"

    # Trigger RECHAZADO transition
    machine.rechazar(fecha_operacion=date(2026, 1, 27))

    # State should be RECHAZADO (terminal)
    assert machine.get_state_id() == "rechazado"


def test_state_machine_aprobado_is_final():
    """Test that APROBADO is a terminal state (cannot transition)."""
    from backend.domain.state_machines.metrologia_machine import MetrologiaStateMachine
    from statemachine.exceptions import TransitionNotAllowed
    from unittest.mock import Mock

    # Mock dependencies
    mock_sheets_repo = Mock()
    mock_metadata_repo = Mock()

    machine = MetrologiaStateMachine(
        tag_spool="UNIT-008",
        sheets_repo=mock_sheets_repo,
        metadata_repo=mock_metadata_repo
    )

    # Transition to APROBADO
    machine.aprobar(fecha_operacion=date(2026, 1, 27))
    assert machine.get_state_id() == "aprobado"

    # Attempting to transition again should raise
    with pytest.raises(TransitionNotAllowed):
        machine.aprobar(fecha_operacion=date(2026, 1, 28))

    with pytest.raises(TransitionNotAllowed):
        machine.rechazar(fecha_operacion=date(2026, 1, 28))


def test_state_machine_rechazado_is_final():
    """Test that RECHAZADO is a terminal state (cannot transition)."""
    from backend.domain.state_machines.metrologia_machine import MetrologiaStateMachine
    from statemachine.exceptions import TransitionNotAllowed
    from unittest.mock import Mock

    # Mock dependencies
    mock_sheets_repo = Mock()
    mock_metadata_repo = Mock()

    machine = MetrologiaStateMachine(
        tag_spool="UNIT-009",
        sheets_repo=mock_sheets_repo,
        metadata_repo=mock_metadata_repo
    )

    # Transition to RECHAZADO
    machine.rechazar(fecha_operacion=date(2026, 1, 27))
    assert machine.get_state_id() == "rechazado"

    # Attempting to transition again should raise
    with pytest.raises(TransitionNotAllowed):
        machine.aprobar(fecha_operacion=date(2026, 1, 28))

    with pytest.raises(TransitionNotAllowed):
        machine.rechazar(fecha_operacion=date(2026, 1, 28))


# ============================================================================
# EDGE CASE TESTS
# ============================================================================


def test_validar_puede_completar_metrologia_both_arm_and_sold_incomplete(validation_service):
    """Test validation fails if both ARM and SOLD not completed."""
    spool = Spool(
        tag_spool="UNIT-010",
        fecha_materiales=date(2026, 1, 20),
        fecha_armado=None,  # ARM not completed
        fecha_soldadura=None,  # SOLD not completed
        fecha_qc_metrologia=None,
        armador=None,
        soldador=None,
        ocupado_por=None
    )

    with pytest.raises(DependenciasNoSatisfechasError) as exc:
        validation_service.validar_puede_completar_metrologia(spool, worker_id=95)

    # Should mention ARM (first check fails)
    assert "ARM completado" in str(exc.value)


def test_validar_puede_completar_metrologia_multiple_violations(validation_service):
    """Test validation fails fast on first violation encountered."""
    spool = Spool(
        tag_spool="UNIT-011",
        fecha_materiales=date(2026, 1, 20),
        fecha_armado=None,  # Violation 1: ARM not completed
        fecha_soldadura=None,  # Violation 2: SOLD not completed
        fecha_qc_metrologia=date(2026, 1, 27),  # Violation 3: Already inspected
        armador=None,
        soldador=None,
        ocupado_por="MR(93):lock"  # Violation 4: Occupied
    )

    with pytest.raises(DependenciasNoSatisfechasError) as exc:
        validation_service.validar_puede_completar_metrologia(spool, worker_id=95)

    # Should fail on first check (ARM)
    assert "ARM completado" in str(exc.value)
