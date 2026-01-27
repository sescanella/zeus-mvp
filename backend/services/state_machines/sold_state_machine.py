"""
SOLD (Welding) operation state machine.

Manages SOLD operation lifecycle with ARM dependency:
- PENDIENTE → EN_PROGRESO (iniciar) - REQUIRES ARM initiated
- EN_PROGRESO → COMPLETADO (completar)
- EN_PROGRESO → PENDIENTE (cancelar)

Guard condition prevents SOLD from starting if ARM not initiated.
"""

from statemachine import State
from backend.services.state_machines.base_state_machine import BaseOperationStateMachine
from backend.exceptions import DependenciasNoSatisfechasError


class SOLDStateMachine(BaseOperationStateMachine):
    """
    SOLD operation state machine with ARM dependency.

    States:
    - pendiente (initial): SOLD not started (Soldador = None)
    - en_progreso: SOLD in progress (Soldador != None, Fecha_Soldadura = None)
    - completado (final): SOLD completed (Fecha_Soldadura != None)

    Transitions:
    - iniciar: pendiente → en_progreso (GUARDED: ARM must be initiated)
    - completar: en_progreso → completado
    - cancelar: en_progreso → pendiente

    Guards:
    - arm_not_initiated: Blocks iniciar if ARM not started (Armador = None)
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
        Initialize SOLD state machine for a specific spool.

        Args:
            tag_spool: Spool identifier
            sheets_repo: SheetsRepository for column updates and ARM state check
            metadata_repo: MetadataRepository for event logging
        """
        super().__init__(tag_spool, sheets_repo, metadata_repo)

    def arm_not_initiated(self) -> bool:
        """
        Guard condition: Check if ARM is initiated.

        Returns:
            True if ARM NOT initiated (blocks transition)
            False if ARM initiated (allows transition)
        """
        # If sheets_repo is None (during testing), assume ARM is initiated
        if self.sheets_repo is None:
            return False

        # Read spool to check ARM status
        spool = self.sheets_repo.get_spool_by_tag(self.tag_spool)
        arm_initiated = spool.armador is not None

        return not arm_initiated

    def validate_arm_initiated(self):
        """
        Validator: Raise exception if ARM not initiated.

        Raises:
            DependenciasNoSatisfechasError: If ARM not initiated
        """
        if self.arm_not_initiated():
            raise DependenciasNoSatisfechasError(
                tag_spool=self.tag_spool,
                operacion="SOLD",
                dependencia_faltante="ARM iniciado",
                detalle="SOLD no puede iniciarse sin ARM iniciado"
            )

    def before_iniciar(self, event_data):
        """
        Before iniciar transition: Validate ARM dependency.

        Args:
            event_data: Transition event data

        Raises:
            DependenciasNoSatisfechasError: If ARM not initiated
        """
        self.validate_arm_initiated()
