"""
Services module - Business logic orchestration layer.

Phase 6 additions:
- ReparacionService: Repair workflow with cycle tracking and BLOQUEADO enforcement
- CycleCounterService: Cycle counting logic for reparacion loops
- EstadoDetalleService: Supervisor override detection and audit logging

Phase 10 additions:
- UnionService: Union-level batch operations and workflow orchestration
"""

from backend.services.reparacion_service import ReparacionService
from backend.services.cycle_counter_service import CycleCounterService
from backend.services.estado_detalle_service import EstadoDetalleService
from backend.services.union_service import UnionService

__all__ = [
    "ReparacionService",
    "CycleCounterService",
    "EstadoDetalleService",
    "UnionService"
]
