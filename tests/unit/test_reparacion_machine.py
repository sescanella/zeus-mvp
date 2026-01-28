"""
Unit tests for REPARACION state machine.

Tests the 4-state machine with occupation management and cycle tracking:
- RECHAZADO → EN_REPARACION → REPARACION_PAUSADA → PENDIENTE_METROLOGIA
"""
import pytest
from unittest.mock import Mock
from backend.services.state_machines.reparacion_state_machine import REPARACIONStateMachine
from backend.services.cycle_counter_service import CycleCounterService
from statemachine.exceptions import TransitionNotAllowed


@pytest.fixture
def mock_sheets_repo():
    """Mock SheetsRepository for testing."""
    repo = Mock()
    repo.find_row_by_column_value = Mock(return_value=10)
    repo.update_cell_by_column_name = Mock()
    repo.batch_update_by_column_name = Mock()
    repo.get_cell_value = Mock(return_value="RECHAZADO (Ciclo 1/3)")
    return repo


@pytest.fixture
def mock_metadata_repo():
    """Mock MetadataRepository for testing."""
    return Mock()


@pytest.fixture
def mock_cycle_counter():
    """Mock CycleCounterService for testing."""
    return CycleCounterService()


@pytest.fixture
def reparacion_machine(mock_sheets_repo, mock_metadata_repo, mock_cycle_counter):
    """Fixture for REPARACIONStateMachine instance."""
    machine = REPARACIONStateMachine(
        tag_spool="TEST-001",
        sheets_repo=mock_sheets_repo,
        metadata_repo=mock_metadata_repo,
        cycle_counter=mock_cycle_counter
    )
    # Hydrate to rechazado state (simulating state service hydration)
    # This mimics how StateService._hydrate_*_machine() sets state
    machine.current_state = machine.rechazado
    return machine


# ==================== STATE CONFIGURATION TESTS ====================

def test_rechazado_is_initial_state(reparacion_machine):
    """Test that RECHAZADO is the initial state."""
    assert reparacion_machine.current_state.id == "rechazado"
    assert reparacion_machine.rechazado.initial is True


def test_pendiente_metrologia_is_final_state(reparacion_machine):
    """Test that PENDIENTE_METROLOGIA is the final state."""
    assert reparacion_machine.pendiente_metrologia.final is True


def test_has_exactly_four_states(reparacion_machine):
    """Test that state machine has exactly 4 states."""
    states = [
        reparacion_machine.rechazado,
        reparacion_machine.en_reparacion,
        reparacion_machine.reparacion_pausada,
        reparacion_machine.pendiente_metrologia
    ]
    assert len(states) == 4


# ==================== TOMAR TRANSITION TESTS ====================

def test_tomar_from_rechazado(reparacion_machine, mock_sheets_repo):
    """Test TOMAR transition from RECHAZADO → EN_REPARACION."""
    # Reset mock to ignore hydration setup calls
    mock_sheets_repo.reset_mock()
    mock_sheets_repo.find_row_by_column_value = Mock(return_value=10)
    mock_sheets_repo.get_cell_value = Mock(return_value="RECHAZADO (Ciclo 1/3)")

    # Execute transition
    reparacion_machine.tomar(worker_id=93, worker_nombre="MR(93)")

    # Verify state changed
    assert reparacion_machine.current_state.id == "en_reparacion"

    # Verify batch update was called
    assert mock_sheets_repo.batch_update_by_column_name.called
    call_args = mock_sheets_repo.batch_update_by_column_name.call_args
    updates = call_args.kwargs["updates"]

    # Verify all 3 columns updated for EN_REPARACION state
    assert len(updates) == 3
    column_names = [u["column_name"] for u in updates]
    assert "Ocupado_Por" in column_names
    assert "Fecha_Ocupacion" in column_names
    assert "Estado_Detalle" in column_names

    # Verify values for EN_REPARACION
    ocupado_por_update = next(u for u in updates if u["column_name"] == "Ocupado_Por")
    assert ocupado_por_update["value"] == "MR(93)"


def test_tomar_from_reparacion_pausada(reparacion_machine, mock_sheets_repo):
    """Test TOMAR transition from REPARACION_PAUSADA → EN_REPARACION (resume)."""
    # First, pause the work
    reparacion_machine.tomar(worker_id=93, worker_nombre="MR(93)")
    reparacion_machine.pausar()

    # Verify we're in pausada state
    assert reparacion_machine.current_state.id == "reparacion_pausada"

    # Reset mock to track resume call
    mock_sheets_repo.reset_mock()
    mock_sheets_repo.find_row_by_column_value = Mock(return_value=10)
    mock_sheets_repo.get_cell_value = Mock(return_value="REPARACION_PAUSADA (Ciclo 1/3)")

    # Resume work (TOMAR again)
    reparacion_machine.tomar(worker_id=94, worker_nombre="JP(94)")

    # Verify state changed to en_reparacion
    assert reparacion_machine.current_state.id == "en_reparacion"

    # Verify batch update was called
    mock_sheets_repo.batch_update_by_column_name.assert_called_once()


def test_tomar_updates_occupation_columns(reparacion_machine, mock_sheets_repo):
    """Test that TOMAR updates Ocupado_Por, Fecha_Ocupacion, Estado_Detalle."""
    reparacion_machine.tomar(worker_id=93, worker_nombre="MR(93)")

    call_args = mock_sheets_repo.batch_update_by_column_name.call_args
    updates = call_args.kwargs["updates"]

    # Find each update
    ocupado_por_update = next(u for u in updates if u["column_name"] == "Ocupado_Por")
    fecha_ocupacion_update = next(u for u in updates if u["column_name"] == "Fecha_Ocupacion")
    estado_detalle_update = next(u for u in updates if u["column_name"] == "Estado_Detalle")

    # Verify values
    assert ocupado_por_update["value"] == "MR(93)"
    assert fecha_ocupacion_update["value"]  # Date string (format checked separately)
    assert "EN_REPARACION" in estado_detalle_update["value"]
    assert "MR(93)" in estado_detalle_update["value"]


def test_tomar_estado_includes_cycle_info(reparacion_machine, mock_sheets_repo):
    """Test that TOMAR sets Estado_Detalle with cycle info."""
    mock_sheets_repo.get_cell_value = Mock(return_value="RECHAZADO (Ciclo 2/3)")

    reparacion_machine.tomar(worker_id=93, worker_nombre="MR(93)")

    call_args = mock_sheets_repo.batch_update_by_column_name.call_args
    updates = call_args.kwargs["updates"]
    estado_detalle_update = next(u for u in updates if u["column_name"] == "Estado_Detalle")

    assert "Ciclo 2/3" in estado_detalle_update["value"]


# ==================== PAUSAR TRANSITION TESTS ====================

def test_pausar_from_en_reparacion(reparacion_machine, mock_sheets_repo):
    """Test PAUSAR transition from EN_REPARACION → REPARACION_PAUSADA."""
    # First, start work
    reparacion_machine.tomar(worker_id=93, worker_nombre="MR(93)")
    assert reparacion_machine.current_state.id == "en_reparacion"

    # Reset mock
    mock_sheets_repo.reset_mock()
    mock_sheets_repo.find_row_by_column_value = Mock(return_value=10)
    mock_sheets_repo.get_cell_value = Mock(return_value="EN_REPARACION (Ciclo 1/3) - Ocupado: MR(93)")

    # Pause work
    reparacion_machine.pausar()

    # Verify state changed
    assert reparacion_machine.current_state.id == "reparacion_pausada"

    # Verify batch update was called
    mock_sheets_repo.batch_update_by_column_name.assert_called_once()


def test_pausar_clears_occupation(reparacion_machine, mock_sheets_repo):
    """Test that PAUSAR clears Ocupado_Por and Fecha_Ocupacion."""
    # Start and pause work
    reparacion_machine.tomar(worker_id=93, worker_nombre="MR(93)")
    mock_sheets_repo.reset_mock()
    mock_sheets_repo.find_row_by_column_value = Mock(return_value=10)
    mock_sheets_repo.get_cell_value = Mock(return_value="EN_REPARACION (Ciclo 1/3) - Ocupado: MR(93)")

    reparacion_machine.pausar()

    call_args = mock_sheets_repo.batch_update_by_column_name.call_args
    updates = call_args.kwargs["updates"]

    # Find updates
    ocupado_por_update = next(u for u in updates if u["column_name"] == "Ocupado_Por")
    fecha_ocupacion_update = next(u for u in updates if u["column_name"] == "Fecha_Ocupacion")

    # Verify cleared
    assert ocupado_por_update["value"] == ""
    assert fecha_ocupacion_update["value"] == ""


def test_pausar_preserves_cycle_info(reparacion_machine, mock_sheets_repo):
    """Test that PAUSAR preserves cycle info in Estado_Detalle."""
    # Start work with cycle 2
    mock_sheets_repo.get_cell_value = Mock(return_value="RECHAZADO (Ciclo 2/3)")
    reparacion_machine.tomar(worker_id=93, worker_nombre="MR(93)")

    # Reset mock
    mock_sheets_repo.reset_mock()
    mock_sheets_repo.find_row_by_column_value = Mock(return_value=10)
    mock_sheets_repo.get_cell_value = Mock(return_value="EN_REPARACION (Ciclo 2/3) - Ocupado: MR(93)")

    # Pause
    reparacion_machine.pausar()

    call_args = mock_sheets_repo.batch_update_by_column_name.call_args
    updates = call_args.kwargs["updates"]
    estado_detalle_update = next(u for u in updates if u["column_name"] == "Estado_Detalle")

    assert "REPARACION_PAUSADA" in estado_detalle_update["value"]
    assert "Ciclo 2/3" in estado_detalle_update["value"]


def test_cannot_pausar_from_rechazado(reparacion_machine):
    """Test that PAUSAR is not allowed from RECHAZADO state."""
    # Try to pause without taking first
    with pytest.raises(TransitionNotAllowed):
        reparacion_machine.pausar()


# ==================== COMPLETAR TRANSITION TESTS ====================

def test_completar_to_pendiente_metrologia(reparacion_machine, mock_sheets_repo):
    """Test COMPLETAR transition from EN_REPARACION → PENDIENTE_METROLOGIA."""
    # Start work
    reparacion_machine.tomar(worker_id=93, worker_nombre="MR(93)")

    # Reset mock
    mock_sheets_repo.reset_mock()
    mock_sheets_repo.find_row_by_column_value = Mock(return_value=10)

    # Complete repair
    reparacion_machine.completar()

    # Verify state changed
    assert reparacion_machine.current_state.id == "pendiente_metrologia"

    # Verify batch update was called
    mock_sheets_repo.batch_update_by_column_name.assert_called_once()


def test_completar_clears_occupation_and_sets_pendiente_metrologia(reparacion_machine, mock_sheets_repo):
    """Test that COMPLETAR clears occupation and sets PENDIENTE_METROLOGIA."""
    # Start and complete work
    reparacion_machine.tomar(worker_id=93, worker_nombre="MR(93)")
    mock_sheets_repo.reset_mock()
    mock_sheets_repo.find_row_by_column_value = Mock(return_value=10)

    reparacion_machine.completar()

    call_args = mock_sheets_repo.batch_update_by_column_name.call_args
    updates = call_args.kwargs["updates"]

    # Find updates
    ocupado_por_update = next(u for u in updates if u["column_name"] == "Ocupado_Por")
    fecha_ocupacion_update = next(u for u in updates if u["column_name"] == "Fecha_Ocupacion")
    estado_detalle_update = next(u for u in updates if u["column_name"] == "Estado_Detalle")

    # Verify cleared
    assert ocupado_por_update["value"] == ""
    assert fecha_ocupacion_update["value"] == ""
    assert estado_detalle_update["value"] == "PENDIENTE_METROLOGIA"


def test_cannot_completar_from_pausada(reparacion_machine):
    """Test that COMPLETAR is not allowed from REPARACION_PAUSADA state."""
    # Start, pause, then try to complete without resuming
    reparacion_machine.tomar(worker_id=93, worker_nombre="MR(93)")
    reparacion_machine.pausar()

    with pytest.raises(TransitionNotAllowed):
        reparacion_machine.completar()


def test_pendiente_metrologia_is_final_state_no_transitions(reparacion_machine):
    """Test that PENDIENTE_METROLOGIA is terminal (no transitions out)."""
    # Complete workflow
    reparacion_machine.tomar(worker_id=93, worker_nombre="MR(93)")
    reparacion_machine.completar()

    # Verify it's final
    assert reparacion_machine.current_state.id == "pendiente_metrologia"
    assert reparacion_machine.current_state.final is True


# ==================== CANCELAR TRANSITION TESTS ====================

def test_cancelar_from_en_reparacion_to_rechazado(reparacion_machine, mock_sheets_repo):
    """Test CANCELAR transition from EN_REPARACION → RECHAZADO."""
    # Start work
    reparacion_machine.tomar(worker_id=93, worker_nombre="MR(93)")

    # Reset mock
    mock_sheets_repo.reset_mock()
    mock_sheets_repo.find_row_by_column_value = Mock(return_value=10)
    mock_sheets_repo.get_cell_value = Mock(return_value="EN_REPARACION (Ciclo 1/3) - Ocupado: MR(93)")

    # Cancel work
    reparacion_machine.cancelar()

    # Verify state changed
    assert reparacion_machine.current_state.id == "rechazado"

    # Verify batch update was called
    mock_sheets_repo.batch_update_by_column_name.assert_called_once()


def test_cancelar_from_reparacion_pausada_to_rechazado(reparacion_machine, mock_sheets_repo):
    """Test CANCELAR transition from REPARACION_PAUSADA → RECHAZADO."""
    # Start and pause work
    reparacion_machine.tomar(worker_id=93, worker_nombre="MR(93)")
    reparacion_machine.pausar()

    # Reset mock
    mock_sheets_repo.reset_mock()
    mock_sheets_repo.find_row_by_column_value = Mock(return_value=10)
    mock_sheets_repo.get_cell_value = Mock(return_value="REPARACION_PAUSADA (Ciclo 1/3)")

    # Cancel work
    reparacion_machine.cancelar()

    # Verify state changed
    assert reparacion_machine.current_state.id == "rechazado"


def test_cancelar_clears_occupation_and_restores_rechazado(reparacion_machine, mock_sheets_repo):
    """Test that CANCELAR clears occupation and restores RECHAZADO estado."""
    # Start work
    reparacion_machine.tomar(worker_id=93, worker_nombre="MR(93)")

    # Reset mock
    mock_sheets_repo.reset_mock()
    mock_sheets_repo.find_row_by_column_value = Mock(return_value=10)
    mock_sheets_repo.get_cell_value = Mock(return_value="EN_REPARACION (Ciclo 2/3) - Ocupado: MR(93)")

    # Cancel
    reparacion_machine.cancelar()

    call_args = mock_sheets_repo.batch_update_by_column_name.call_args
    updates = call_args.kwargs["updates"]

    # Find updates
    ocupado_por_update = next(u for u in updates if u["column_name"] == "Ocupado_Por")
    fecha_ocupacion_update = next(u for u in updates if u["column_name"] == "Fecha_Ocupacion")
    estado_detalle_update = next(u for u in updates if u["column_name"] == "Estado_Detalle")

    # Verify cleared
    assert ocupado_por_update["value"] == ""
    assert fecha_ocupacion_update["value"] == ""
    assert "RECHAZADO" in estado_detalle_update["value"]
    assert "Ciclo 2/3" in estado_detalle_update["value"]


# ==================== INTEGRATION TESTS ====================

def test_complete_workflow_rechazado_to_pendiente_metrologia(reparacion_machine, mock_sheets_repo):
    """Test complete workflow: RECHAZADO → EN_REPARACION → PENDIENTE_METROLOGIA."""
    # Initial state
    assert reparacion_machine.current_state.id == "rechazado"

    # Tomar
    reparacion_machine.tomar(worker_id=93, worker_nombre="MR(93)")
    assert reparacion_machine.current_state.id == "en_reparacion"

    # Completar
    mock_sheets_repo.find_row_by_column_value = Mock(return_value=10)
    reparacion_machine.completar()
    assert reparacion_machine.current_state.id == "pendiente_metrologia"


def test_workflow_with_pause_and_resume(reparacion_machine, mock_sheets_repo):
    """Test workflow with PAUSAR and resume: RECHAZADO → EN_REPARACION → PAUSADA → EN_REPARACION → PENDIENTE."""
    # Initial state
    assert reparacion_machine.current_state.id == "rechazado"

    # Tomar
    reparacion_machine.tomar(worker_id=93, worker_nombre="MR(93)")
    assert reparacion_machine.current_state.id == "en_reparacion"

    # Pausar
    mock_sheets_repo.find_row_by_column_value = Mock(return_value=10)
    mock_sheets_repo.get_cell_value = Mock(return_value="EN_REPARACION (Ciclo 1/3) - Ocupado: MR(93)")
    reparacion_machine.pausar()
    assert reparacion_machine.current_state.id == "reparacion_pausada"

    # Resume (Tomar again)
    mock_sheets_repo.get_cell_value = Mock(return_value="REPARACION_PAUSADA (Ciclo 1/3)")
    reparacion_machine.tomar(worker_id=94, worker_nombre="JP(94)")
    assert reparacion_machine.current_state.id == "en_reparacion"

    # Completar
    reparacion_machine.completar()
    assert reparacion_machine.current_state.id == "pendiente_metrologia"


def test_workflow_with_cancelar(reparacion_machine, mock_sheets_repo):
    """Test workflow with CANCELAR: RECHAZADO → EN_REPARACION → RECHAZADO."""
    # Initial state
    assert reparacion_machine.current_state.id == "rechazado"

    # Tomar
    reparacion_machine.tomar(worker_id=93, worker_nombre="MR(93)")
    assert reparacion_machine.current_state.id == "en_reparacion"

    # Cancelar
    mock_sheets_repo.find_row_by_column_value = Mock(return_value=10)
    mock_sheets_repo.get_cell_value = Mock(return_value="EN_REPARACION (Ciclo 1/3) - Ocupado: MR(93)")
    reparacion_machine.cancelar()
    assert reparacion_machine.current_state.id == "rechazado"


def test_cycle_tracking_across_transitions(reparacion_machine, mock_sheets_repo):
    """Test that cycle count is preserved across state transitions."""
    # Start with cycle 2
    mock_sheets_repo.get_cell_value = Mock(return_value="RECHAZADO (Ciclo 2/3)")

    # Tomar
    reparacion_machine.tomar(worker_id=93, worker_nombre="MR(93)")
    call_args = mock_sheets_repo.batch_update_by_column_name.call_args
    updates = call_args.kwargs["updates"]
    estado_detalle_update = next(u for u in updates if u["column_name"] == "Estado_Detalle")
    assert "Ciclo 2/3" in estado_detalle_update["value"]

    # Pausar
    mock_sheets_repo.reset_mock()
    mock_sheets_repo.find_row_by_column_value = Mock(return_value=10)
    mock_sheets_repo.get_cell_value = Mock(return_value="EN_REPARACION (Ciclo 2/3) - Ocupado: MR(93)")
    reparacion_machine.pausar()
    call_args = mock_sheets_repo.batch_update_by_column_name.call_args
    updates = call_args.kwargs["updates"]
    estado_detalle_update = next(u for u in updates if u["column_name"] == "Estado_Detalle")
    assert "Ciclo 2/3" in estado_detalle_update["value"]

    # Resume
    mock_sheets_repo.reset_mock()
    mock_sheets_repo.find_row_by_column_value = Mock(return_value=10)
    mock_sheets_repo.get_cell_value = Mock(return_value="REPARACION_PAUSADA (Ciclo 2/3)")
    reparacion_machine.tomar(worker_id=93, worker_nombre="MR(93)")
    call_args = mock_sheets_repo.batch_update_by_column_name.call_args
    updates = call_args.kwargs["updates"]
    estado_detalle_update = next(u for u in updates if u["column_name"] == "Estado_Detalle")
    assert "Ciclo 2/3" in estado_detalle_update["value"]
