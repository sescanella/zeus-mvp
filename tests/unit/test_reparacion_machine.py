"""
Unit tests for REPARACION state machine.

Tests the 4-state machine with occupation management:
- RECHAZADO → EN_REPARACION → REPARACION_PAUSADA → PENDIENTE_METROLOGIA
"""
import pytest
from unittest.mock import Mock
from backend.services.state_machines.reparacion_state_machine import REPARACIONStateMachine
from statemachine.exceptions import TransitionNotAllowed


@pytest.fixture
def mock_sheets_repo():
    repo = Mock()
    repo.find_row_by_column_value = Mock(return_value=10)
    repo.update_cell_by_column_name = Mock()
    repo.batch_update_by_column_name = Mock()
    repo.get_cell_value = Mock(return_value="RECHAZADO - Pendiente reparación")
    return repo


@pytest.fixture
def mock_metadata_repo():
    return Mock()


@pytest.fixture
def reparacion_machine(mock_sheets_repo, mock_metadata_repo):
    machine = REPARACIONStateMachine(
        tag_spool="TEST-001",
        sheets_repo=mock_sheets_repo,
        metadata_repo=mock_metadata_repo,
    )
    # Hydrate via direct assignment (sync mode — works without await)
    machine.current_state = machine.rechazado
    return machine


# ==================== STATE CONFIGURATION TESTS ====================

def test_rechazado_is_initial_state(reparacion_machine):
    assert reparacion_machine.current_state.id == "rechazado"
    assert reparacion_machine.rechazado.initial is True


def test_pendiente_metrologia_is_final_state(reparacion_machine):
    assert reparacion_machine.pendiente_metrologia.final is True


def test_has_exactly_four_states(reparacion_machine):
    states = [
        reparacion_machine.rechazado,
        reparacion_machine.en_reparacion,
        reparacion_machine.reparacion_pausada,
        reparacion_machine.pendiente_metrologia
    ]
    assert len(states) == 4


# ==================== TOMAR TRANSITION TESTS ====================

def test_tomar_from_rechazado(reparacion_machine, mock_sheets_repo):
    """TOMAR transition from RECHAZADO → EN_REPARACION."""
    mock_sheets_repo.reset_mock()
    mock_sheets_repo.find_row_by_column_value = Mock(return_value=10)

    reparacion_machine.tomar(worker_id=93, worker_nombre="MR(93)")

    assert reparacion_machine.current_state.id == "en_reparacion"
    assert mock_sheets_repo.batch_update_by_column_name.called
    updates = mock_sheets_repo.batch_update_by_column_name.call_args.kwargs["updates"]

    assert len(updates) == 3
    column_names = [u["column_name"] for u in updates]
    assert "Ocupado_Por" in column_names
    assert "Fecha_Ocupacion" in column_names
    assert "Estado_Detalle" in column_names

    ocupado_por_update = next(u for u in updates if u["column_name"] == "Ocupado_Por")
    assert ocupado_por_update["value"] == "MR(93)"


def test_tomar_from_reparacion_pausada(reparacion_machine, mock_sheets_repo):
    """TOMAR transition from REPARACION_PAUSADA → EN_REPARACION (resume)."""
    reparacion_machine.tomar(worker_id=93, worker_nombre="MR(93)")
    reparacion_machine.pausar()
    assert reparacion_machine.current_state.id == "reparacion_pausada"

    mock_sheets_repo.reset_mock()
    mock_sheets_repo.find_row_by_column_value = Mock(return_value=10)

    reparacion_machine.tomar(worker_id=94, worker_nombre="JP(94)")

    assert reparacion_machine.current_state.id == "en_reparacion"
    mock_sheets_repo.batch_update_by_column_name.assert_called_once()


def test_tomar_updates_occupation_columns(reparacion_machine, mock_sheets_repo):
    """TOMAR updates Ocupado_Por, Fecha_Ocupacion, Estado_Detalle."""
    reparacion_machine.tomar(worker_id=93, worker_nombre="MR(93)")

    updates = mock_sheets_repo.batch_update_by_column_name.call_args.kwargs["updates"]

    ocupado_por_update = next(u for u in updates if u["column_name"] == "Ocupado_Por")
    fecha_ocupacion_update = next(u for u in updates if u["column_name"] == "Fecha_Ocupacion")
    estado_detalle_update = next(u for u in updates if u["column_name"] == "Estado_Detalle")

    assert ocupado_por_update["value"] == "MR(93)"
    assert fecha_ocupacion_update["value"]
    assert "EN_REPARACION" in estado_detalle_update["value"]
    assert "MR(93)" in estado_detalle_update["value"]


# ==================== PAUSAR TRANSITION TESTS ====================

def test_pausar_from_en_reparacion(reparacion_machine, mock_sheets_repo):
    """PAUSAR transition from EN_REPARACION → REPARACION_PAUSADA."""
    reparacion_machine.tomar(worker_id=93, worker_nombre="MR(93)")
    assert reparacion_machine.current_state.id == "en_reparacion"

    mock_sheets_repo.reset_mock()
    mock_sheets_repo.find_row_by_column_value = Mock(return_value=10)

    reparacion_machine.pausar()

    assert reparacion_machine.current_state.id == "reparacion_pausada"
    mock_sheets_repo.batch_update_by_column_name.assert_called_once()


def test_pausar_clears_occupation(reparacion_machine, mock_sheets_repo):
    """PAUSAR clears Ocupado_Por and Fecha_Ocupacion."""
    reparacion_machine.tomar(worker_id=93, worker_nombre="MR(93)")
    mock_sheets_repo.reset_mock()
    mock_sheets_repo.find_row_by_column_value = Mock(return_value=10)

    reparacion_machine.pausar()

    updates = mock_sheets_repo.batch_update_by_column_name.call_args.kwargs["updates"]
    ocupado_por_update = next(u for u in updates if u["column_name"] == "Ocupado_Por")
    fecha_ocupacion_update = next(u for u in updates if u["column_name"] == "Fecha_Ocupacion")
    estado_detalle_update = next(u for u in updates if u["column_name"] == "Estado_Detalle")

    assert ocupado_por_update["value"] == ""
    assert fecha_ocupacion_update["value"] == ""
    assert estado_detalle_update["value"] == "REPARACION_PAUSADA"


def test_cannot_pausar_from_rechazado(reparacion_machine):
    """PAUSAR is not allowed from RECHAZADO state."""
    with pytest.raises(TransitionNotAllowed):
        reparacion_machine.pausar()


# ==================== COMPLETAR TRANSITION TESTS ====================

def test_completar_to_pendiente_metrologia(reparacion_machine, mock_sheets_repo):
    """COMPLETAR transition from EN_REPARACION → PENDIENTE_METROLOGIA."""
    reparacion_machine.tomar(worker_id=93, worker_nombre="MR(93)")
    mock_sheets_repo.reset_mock()
    mock_sheets_repo.find_row_by_column_value = Mock(return_value=10)

    reparacion_machine.completar()

    assert reparacion_machine.current_state.id == "pendiente_metrologia"
    mock_sheets_repo.batch_update_by_column_name.assert_called_once()


def test_completar_clears_occupation_and_sets_pendiente_metrologia(reparacion_machine, mock_sheets_repo):
    """COMPLETAR clears occupation and sets PENDIENTE_METROLOGIA."""
    reparacion_machine.tomar(worker_id=93, worker_nombre="MR(93)")
    mock_sheets_repo.reset_mock()
    mock_sheets_repo.find_row_by_column_value = Mock(return_value=10)

    reparacion_machine.completar()

    updates = mock_sheets_repo.batch_update_by_column_name.call_args.kwargs["updates"]
    ocupado_por_update = next(u for u in updates if u["column_name"] == "Ocupado_Por")
    fecha_ocupacion_update = next(u for u in updates if u["column_name"] == "Fecha_Ocupacion")
    estado_detalle_update = next(u for u in updates if u["column_name"] == "Estado_Detalle")

    assert ocupado_por_update["value"] == ""
    assert fecha_ocupacion_update["value"] == ""
    assert estado_detalle_update["value"] == "PENDIENTE_METROLOGIA"


def test_cannot_completar_from_pausada(reparacion_machine):
    """COMPLETAR is not allowed from REPARACION_PAUSADA state."""
    reparacion_machine.tomar(worker_id=93, worker_nombre="MR(93)")
    reparacion_machine.pausar()

    with pytest.raises(TransitionNotAllowed):
        reparacion_machine.completar()


def test_pendiente_metrologia_is_final_state_no_transitions(reparacion_machine):
    """PENDIENTE_METROLOGIA is terminal (no transitions out)."""
    reparacion_machine.tomar(worker_id=93, worker_nombre="MR(93)")
    reparacion_machine.completar()

    assert reparacion_machine.current_state.id == "pendiente_metrologia"
    assert reparacion_machine.current_state.final is True


# ==================== CANCELAR TRANSITION TESTS ====================

def test_cancelar_from_en_reparacion_to_rechazado(reparacion_machine, mock_sheets_repo):
    """CANCELAR transition from EN_REPARACION → RECHAZADO."""
    reparacion_machine.tomar(worker_id=93, worker_nombre="MR(93)")
    mock_sheets_repo.reset_mock()
    mock_sheets_repo.find_row_by_column_value = Mock(return_value=10)

    reparacion_machine.cancelar()

    assert reparacion_machine.current_state.id == "rechazado"
    mock_sheets_repo.batch_update_by_column_name.assert_called_once()


def test_cancelar_from_reparacion_pausada_to_rechazado(reparacion_machine, mock_sheets_repo):
    """CANCELAR transition from REPARACION_PAUSADA → RECHAZADO."""
    reparacion_machine.tomar(worker_id=93, worker_nombre="MR(93)")
    reparacion_machine.pausar()
    mock_sheets_repo.reset_mock()
    mock_sheets_repo.find_row_by_column_value = Mock(return_value=10)

    reparacion_machine.cancelar()

    assert reparacion_machine.current_state.id == "rechazado"


def test_cancelar_clears_occupation_and_restores_rechazado(reparacion_machine, mock_sheets_repo):
    """CANCELAR clears occupation and restores RECHAZADO estado."""
    reparacion_machine.tomar(worker_id=93, worker_nombre="MR(93)")
    mock_sheets_repo.reset_mock()
    mock_sheets_repo.find_row_by_column_value = Mock(return_value=10)

    reparacion_machine.cancelar()

    updates = mock_sheets_repo.batch_update_by_column_name.call_args.kwargs["updates"]
    ocupado_por_update = next(u for u in updates if u["column_name"] == "Ocupado_Por")
    fecha_ocupacion_update = next(u for u in updates if u["column_name"] == "Fecha_Ocupacion")
    estado_detalle_update = next(u for u in updates if u["column_name"] == "Estado_Detalle")

    assert ocupado_por_update["value"] == ""
    assert fecha_ocupacion_update["value"] == ""
    assert "RECHAZADO" in estado_detalle_update["value"]


# ==================== INTEGRATION TESTS ====================

def test_complete_workflow_rechazado_to_pendiente_metrologia(reparacion_machine):
    """Complete workflow: RECHAZADO → EN_REPARACION → PENDIENTE_METROLOGIA."""
    assert reparacion_machine.current_state.id == "rechazado"
    reparacion_machine.tomar(worker_id=93, worker_nombre="MR(93)")
    assert reparacion_machine.current_state.id == "en_reparacion"
    reparacion_machine.completar()
    assert reparacion_machine.current_state.id == "pendiente_metrologia"


def test_workflow_with_pause_and_resume(reparacion_machine):
    """Workflow with PAUSAR and resume."""
    assert reparacion_machine.current_state.id == "rechazado"
    reparacion_machine.tomar(worker_id=93, worker_nombre="MR(93)")
    reparacion_machine.pausar()
    assert reparacion_machine.current_state.id == "reparacion_pausada"
    reparacion_machine.tomar(worker_id=94, worker_nombre="JP(94)")
    assert reparacion_machine.current_state.id == "en_reparacion"
    reparacion_machine.completar()
    assert reparacion_machine.current_state.id == "pendiente_metrologia"


def test_workflow_with_cancelar(reparacion_machine):
    """Workflow with CANCELAR: RECHAZADO → EN_REPARACION → RECHAZADO."""
    assert reparacion_machine.current_state.id == "rechazado"
    reparacion_machine.tomar(worker_id=93, worker_nombre="MR(93)")
    reparacion_machine.cancelar()
    assert reparacion_machine.current_state.id == "rechazado"


# ============================================================================
# T-131 / Bug 7 — async hydration regression tests
# ============================================================================
#
# python-statemachine 2.5.0 silently ignores assignment to `current_state`
# when transitions are awaited. Hydrating via the constructor's `start_value`
# argument and `await activate_initial_state()` is the only path that propagates
# state to the async engine. These tests pin that contract so a future refactor
# can't reintroduce the direct-assignment bug.


@pytest.fixture
def repo_for_async():
    repo = Mock()
    repo.get_tag_spool_column_letter = Mock(return_value="G")
    repo.find_row_by_column_value = Mock(return_value=10)
    repo.get_cell_value = Mock(return_value="EN_REPARACION - Ocupado: NR(93)")
    repo.batch_update_by_column_name = Mock()
    return repo


@pytest.mark.asyncio
async def test_async_completar_from_en_reparacion(repo_for_async, mock_metadata_repo):
    """COMPLETAR via async engine when SM is hydrated to en_reparacion."""
    machine = REPARACIONStateMachine(
        tag_spool="TEST-001",
        sheets_repo=repo_for_async,
        metadata_repo=mock_metadata_repo,
        start_value="en_reparacion",
    )
    await machine.activate_initial_state()
    assert machine.current_state.id == "en_reparacion"

    await machine.completar()

    assert machine.current_state.id == "pendiente_metrologia"
    repo_for_async.batch_update_by_column_name.assert_called_once()
    updates = repo_for_async.batch_update_by_column_name.call_args.kwargs["updates"]
    estado = next(u for u in updates if u["column_name"] == "Estado_Detalle")
    assert estado["value"] == "PENDIENTE_METROLOGIA"


@pytest.mark.asyncio
async def test_async_pausar_from_en_reparacion(repo_for_async, mock_metadata_repo):
    """PAUSAR via async engine when SM is hydrated to en_reparacion."""
    machine = REPARACIONStateMachine(
        tag_spool="TEST-001",
        sheets_repo=repo_for_async,
        metadata_repo=mock_metadata_repo,
        start_value="en_reparacion",
    )
    await machine.activate_initial_state()

    await machine.pausar()

    assert machine.current_state.id == "reparacion_pausada"
    repo_for_async.batch_update_by_column_name.assert_called_once()


@pytest.mark.asyncio
async def test_async_cancelar_from_en_reparacion(repo_for_async, mock_metadata_repo):
    """CANCELAR via async engine when SM is hydrated to en_reparacion."""
    machine = REPARACIONStateMachine(
        tag_spool="TEST-001",
        sheets_repo=repo_for_async,
        metadata_repo=mock_metadata_repo,
        start_value="en_reparacion",
    )
    await machine.activate_initial_state()

    await machine.cancelar()

    assert machine.current_state.id == "rechazado"


@pytest.mark.asyncio
async def test_async_cancelar_from_reparacion_pausada(repo_for_async, mock_metadata_repo):
    """CANCELAR via async engine when SM is hydrated to reparacion_pausada."""
    repo_for_async.get_cell_value = Mock(return_value="REPARACION_PAUSADA")
    machine = REPARACIONStateMachine(
        tag_spool="TEST-001",
        sheets_repo=repo_for_async,
        metadata_repo=mock_metadata_repo,
        start_value="reparacion_pausada",
    )
    await machine.activate_initial_state()

    await machine.cancelar()

    assert machine.current_state.id == "rechazado"


@pytest.mark.asyncio
async def test_async_tomar_resume_from_pausada(repo_for_async, mock_metadata_repo):
    """TOMAR (resume) via async engine when SM is hydrated to reparacion_pausada."""
    repo_for_async.get_cell_value = Mock(return_value="REPARACION_PAUSADA")
    machine = REPARACIONStateMachine(
        tag_spool="TEST-001",
        sheets_repo=repo_for_async,
        metadata_repo=mock_metadata_repo,
        start_value="reparacion_pausada",
    )
    await machine.activate_initial_state()

    await machine.tomar(worker_id=93, worker_nombre="MR(93)")

    assert machine.current_state.id == "en_reparacion"


@pytest.mark.asyncio
async def test_async_direct_assignment_does_not_hydrate(repo_for_async, mock_metadata_repo):
    """
    Pin Bug 7: replicate the EXACT pre-fix code path —
    construct, assign current_state directly to a non-initial state, then
    await a transition. python-statemachine 2.5.0 raises TransitionNotAllowed
    because the async engine never saw the assignment.

    If python-statemachine ever fixes this, this test will start failing
    (DID NOT RAISE), and we can simplify reparacion_service back to direct
    assignment.
    """
    machine = REPARACIONStateMachine(
        tag_spool="TEST-001",
        sheets_repo=repo_for_async,
        metadata_repo=mock_metadata_repo,
    )
    machine.current_state = machine.en_reparacion
    assert machine.current_state.id == "en_reparacion"
    with pytest.raises(TransitionNotAllowed) as excinfo:
        await machine.completar()
    assert "rechazado" in str(excinfo.value).lower()
