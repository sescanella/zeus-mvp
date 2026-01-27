"""
State machines for operation state management (Phase 3).

Each operation (ARM, SOLD) has its own state machine with 3 states:
- PENDIENTE (initial)
- EN_PROGRESO
- COMPLETADO (final)

State machines coordinate with OccupationService and update Estado_Detalle.
"""

from backend.services.state_machines.arm_state_machine import ARMStateMachine
from backend.services.state_machines.sold_state_machine import SOLDStateMachine

__all__ = ["ARMStateMachine", "SOLDStateMachine"]
