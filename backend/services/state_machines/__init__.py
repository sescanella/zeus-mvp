"""
State machines for operation state management (Phase 3 + Phase 6).

Each operation has its own state machine:
- ARM, SOLD: 3 states (PENDIENTE → EN_PROGRESO → COMPLETADO)
- REPARACION: 4 states (RECHAZADO → EN_REPARACION → REPARACION_PAUSADA → PENDIENTE_METROLOGIA)

State machines coordinate with OccupationService and update Estado_Detalle.
"""

from backend.services.state_machines.arm_state_machine import ARMStateMachine
from backend.services.state_machines.sold_state_machine import SOLDStateMachine
from backend.services.state_machines.reparacion_state_machine import REPARACIONStateMachine

__all__ = ["ARMStateMachine", "SOLDStateMachine", "REPARACIONStateMachine"]
