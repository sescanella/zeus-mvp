"""
ARM (Assembly) operation state machine.

Manages ARM operation lifecycle:
- PENDIENTE → EN_PROGRESO (iniciar)
- EN_PROGRESO → COMPLETADO (completar)
- EN_PROGRESO → PENDIENTE (cancelar)

Callbacks update Operaciones sheet columns (Armador, Fecha_Armado) automatically.
No dependency guards - ARM is the first operation.
"""

from statemachine import State
from backend.services.state_machines.base_state_machine import BaseOperationStateMachine


class ARMStateMachine(BaseOperationStateMachine):
    """
    ARM operation state machine.

    States:
    - pendiente (initial): ARM not started (Armador = None)
    - en_progreso: ARM in progress (Armador != None, Fecha_Armado = None)
    - completado (final): ARM completed (Fecha_Armado != None)

    Transitions:
    - iniciar: pendiente → en_progreso
    - completar: en_progreso → completado
    - cancelar: en_progreso → pendiente
    """

    # Define states
    pendiente = State("pendiente", initial=True)
    en_progreso = State("en_progreso")
    completado = State("completado", final=True)

    # Define transitions
    iniciar = pendiente.to(en_progreso)
    completar = en_progreso.to(completado)
    cancelar = en_progreso.to(pendiente)

    def __init__(self, tag_spool: str, sheets_repo, metadata_repo):
        """
        Initialize ARM state machine for a specific spool.

        Args:
            tag_spool: Spool identifier
            sheets_repo: SheetsRepository for column updates
            metadata_repo: MetadataRepository for event logging
        """
        super().__init__(tag_spool, sheets_repo, metadata_repo)
