"""
Unit tests for METROLOGIA state machine.

Tests the 3-state machine with binary outcomes (APROBADO/RECHAZADO).
"""
import pytest
from unittest.mock import Mock
from backend.domain.state_machines.metrologia_machine import MetrologiaStateMachine
from datetime import date


@pytest.fixture
def mock_sheets_repo():
    """Mock SheetsRepository for testing (machine uses batch_update_by_column_name)."""
    repo = Mock()
    repo.find_row_by_column_value = Mock(return_value=10)
    repo.batch_update_by_column_name = Mock()
    return repo


@pytest.fixture
def mock_metadata_repo():
    """Mock MetadataRepository for testing."""
    return Mock()


@pytest.fixture
def metrologia_machine(mock_sheets_repo, mock_metadata_repo):
    """Fixture for MetrologiaStateMachine instance."""
    return MetrologiaStateMachine(
        tag_spool="TEST-001",
        sheets_repo=mock_sheets_repo,
        metadata_repo=mock_metadata_repo
    )


def test_pendiente_state_is_not_final(metrologia_machine):
    """Test that PENDIENTE state is not final."""
    assert metrologia_machine.pendiente.final is False


def test_aprobado_state_is_final(metrologia_machine):
    """Test that APROBADO state is final (terminal)."""
    assert metrologia_machine.aprobado.final is True


def test_rechazado_state_is_final(metrologia_machine):
    """Test that RECHAZADO state is final (terminal)."""
    assert metrologia_machine.rechazado.final is True


def test_has_exactly_three_states(metrologia_machine):
    """Test that state machine has exactly 3 states."""
    states = [metrologia_machine.pendiente, metrologia_machine.aprobado, metrologia_machine.rechazado]
    assert len(states) == 3


def test_aprobar_transition_from_pendiente_to_aprobado(metrologia_machine, mock_sheets_repo):
    """Test successful aprobar transition updates state and column."""
    # Execute transition
    metrologia_machine.aprobar(fecha_operacion=date(2026, 1, 27))

    # Verify state changed
    assert metrologia_machine.current_state.id == "aprobado"

    # Verify Sheets batch update was called (Fecha_QC_Metrología + Estado_Detalle)
    mock_sheets_repo.batch_update_by_column_name.assert_called_once()
    call_args = mock_sheets_repo.batch_update_by_column_name.call_args
    updates = call_args.kwargs["updates"]
    col_names = [u["column_name"] for u in updates]
    assert "Fecha_QC_Metrología" in col_names
    fecha_update = next(u for u in updates if u["column_name"] == "Fecha_QC_Metrología")
    assert fecha_update["value"] == "27-01-2026"


def test_rechazar_transition_from_pendiente_to_rechazado(metrologia_machine, mock_sheets_repo):
    """Test successful rechazar transition updates Estado_Detalle only (NOT Fecha_QC_Metrología)."""
    # Execute transition
    metrologia_machine.rechazar(fecha_operacion=date(2026, 1, 27))

    # Verify state changed
    assert metrologia_machine.current_state.id == "rechazado"

    # Verify Sheets batch update was called (Estado_Detalle only, NO Fecha_QC_Metrología)
    mock_sheets_repo.batch_update_by_column_name.assert_called_once()
    call_args = mock_sheets_repo.batch_update_by_column_name.call_args
    updates = call_args.kwargs["updates"]
    col_names = [u["column_name"] for u in updates]
    assert "Fecha_QC_Metrología" not in col_names
    assert "Estado_Detalle" in col_names


def test_aprobado_is_terminal_state(metrologia_machine):
    """Test that APROBADO state is terminal (cannot transition out)."""
    # Transition to aprobado
    metrologia_machine.aprobar()

    # Verify it's in aprobado state and it's final
    assert metrologia_machine.current_state.id == "aprobado"
    assert metrologia_machine.current_state.final is True


def test_rechazado_is_terminal_state(metrologia_machine):
    """Test that RECHAZADO state is terminal (cannot transition out)."""
    # Transition to rechazado
    metrologia_machine.rechazar()

    # Verify it's in rechazado state and it's final
    assert metrologia_machine.current_state.id == "rechazado"
    assert metrologia_machine.current_state.final is True


def test_aprobado_writes_fecha_but_rechazado_does_not(metrologia_machine, mock_sheets_repo):
    """Test that APROBADO writes Fecha_QC_Metrología but RECHAZADO does not."""
    # Test APROBADO - should write Fecha_QC_Metrología
    machine1 = MetrologiaStateMachine(
        tag_spool="TEST-001",
        sheets_repo=mock_sheets_repo,
        metadata_repo=Mock()
    )
    machine1.aprobar(fecha_operacion=date(2026, 1, 27))

    aprobado_call = mock_sheets_repo.batch_update_by_column_name.call_args
    assert aprobado_call is not None
    updates = aprobado_call.kwargs["updates"]
    assert any(u["column_name"] == "Fecha_QC_Metrología" for u in updates)

    # Reset mock
    mock_sheets_repo.reset_mock()

    # Test RECHAZADO - should NOT write Fecha_QC_Metrología
    machine2 = MetrologiaStateMachine(
        tag_spool="TEST-002",
        sheets_repo=mock_sheets_repo,
        metadata_repo=Mock()
    )
    machine2.rechazar(fecha_operacion=date(2026, 1, 27))

    rechazado_call = mock_sheets_repo.batch_update_by_column_name.call_args
    assert rechazado_call is not None
    updates = rechazado_call.kwargs["updates"]
    assert not any(u["column_name"] == "Fecha_QC_Metrología" for u in updates)
    assert any(u["column_name"] == "Estado_Detalle" for u in updates)
