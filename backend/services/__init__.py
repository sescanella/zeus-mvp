"""
Services module - Business logic orchestration layer.

Phase 6 additions:
- ReparacionService: Repair workflow with cycle tracking and BLOQUEADO enforcement
- CycleCounterService: Cycle counting logic for reparacion loops
"""

from backend.services.reparacion_service import ReparacionService
from backend.services.cycle_counter_service import CycleCounterService

__all__ = ["ReparacionService", "CycleCounterService"]
