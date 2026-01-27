"""
Base state machine with shared functionality for all operations.

Provides common structure and utilities for ARM, SOLD, and future operation
state machines.
"""

from statemachine import StateMachine, State
from typing import Optional


class BaseOperationStateMachine(StateMachine):
    """
    Base class for operation state machines.

    All operation state machines inherit from this to ensure consistent
    state naming and transition patterns.

    Standard states:
    - pendiente (initial): Operation not started
    - en_progreso: Operation in progress
    - completado (final): Operation completed

    Subclasses should define:
    - Specific transitions (iniciar, completar, cancelar)
    - Callbacks for state changes (on_enter_*, after_transition)
    - Guards/validators for dependencies
    """

    # State names as class attributes for external access
    PENDIENTE = "pendiente"
    EN_PROGRESO = "en_progreso"
    COMPLETADO = "completado"

    def __init__(self, tag_spool: str, sheets_repo, metadata_repo):
        """
        Initialize state machine for a specific spool.

        Args:
            tag_spool: Spool identifier
            sheets_repo: Repository for Sheets operations
            metadata_repo: Repository for metadata logging
        """
        self.tag_spool = tag_spool
        self.sheets_repo = sheets_repo
        self.metadata_repo = metadata_repo
        super().__init__()

    def get_state_id(self) -> str:
        """
        Get current state ID.

        Returns:
            String ID of current state (pendiente, en_progreso, completado)
        """
        return self.current_state.id
