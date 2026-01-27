---
phase: 03-state-machine-and-collaboration
plan: 02
subsystem: state-orchestration
tags: [state-service, orchestration, hydration, estado-detalle]

requires:
  - 03-01 # State machines with guards
  - 02-02 # OccupationService TOMAR/PAUSAR/COMPLETAR

provides:
  - StateService orchestrator with hydration logic
  - EstadoDetalleBuilder display formatter
  - Integration between state machines and occupation service
  - Router endpoints using StateService

affects:
  - 03-03 # Will add callbacks to state machines for column updates
  - 03-04 # Will add Estado_Detalle updates to StateService

tech-stack:
  patterns:
    - Service orchestration pattern (StateService wraps OccupationService)
    - Hydration pattern (sync state machines with Sheets columns)
    - Builder pattern (EstadoDetalleBuilder for display strings)
    - Dependency injection via FastAPI Depends()

key-files:
  created:
    - backend/services/state_service.py
    - backend/services/estado_detalle_builder.py
    - backend/models/state.py
  modified:
    - backend/routers/occupation.py
    - backend/core/dependency.py

decisions:
  - id: PHASE3-02-STATE-SERVICE-ORCHESTRATION
    what: StateService wraps OccupationService instead of replacing it
    why: Maintains Phase 2 Redis locking while adding state machine layer
    impact: Router uses StateService, StateService delegates to OccupationService
    alternatives: Replace OccupationService (rejected - would lose Phase 2 infrastructure)

  - id: PHASE3-02-HYDRATION-PATTERN
    what: Hydrate state machines from Sheets columns on each operation
    why: State machines are ephemeral (per-request), must sync with persistent storage
    impact: _hydrate_arm_machine() and _hydrate_sold_machine() methods
    alternatives: Cache state machines (rejected - premature optimization, stale state risk)

  - id: PHASE3-02-BUILDER-PATTERN
    what: Centralize Estado_Detalle formatting in EstadoDetalleBuilder
    why: Single source of truth for display strings, consistency across operations
    impact: All Estado_Detalle updates use same formatting logic
    alternatives: Format in each state machine (rejected - duplicated code)

metrics:
  duration: 2.9 min
  completed: 2026-01-27
---

# Phase 03 Plan 02: StateService Orchestration Summary

**One-liner:** StateService orchestrates ARM/SOLD state machines with OccupationService via hydration pattern, EstadoDetalleBuilder formats combined display strings

## What Was Built

### StateService Orchestrator
Implemented StateService as the main coordination layer that:
- **Wraps OccupationService**: Delegates TOMAR/PAUSAR/COMPLETAR to Phase 2 service for Redis locking
- **Manages state machines**: Creates and hydrates ARM/SOLD state machines per operation
- **Coordinates transitions**: Triggers iniciar/completar/cancelar transitions based on operation type
- **Plans Estado_Detalle updates**: TODOs added for Plan 03-03 (actual column updates)

### Hydration Logic
Two hydration methods that sync state machines with Sheets reality:
- **_hydrate_arm_machine()**: Reads Armador/Fecha_Armado columns
  - `fecha_armado != None` → completado state
  - `armador != None` → en_progreso state
  - Otherwise → pendiente state (initial)
- **_hydrate_sold_machine()**: Same pattern for Soldador/Fecha_Soldadura columns
  - Ensures state machines always match current Sheets state
  - Handles cases where spool state changed since last operation

### EstadoDetalleBuilder
Created display string formatter service:
- **build() method**: Combines occupation + operation states
- **Occupied format**: `"{worker} trabajando {operation} (ARM {state}, SOLD {state})"`
- **Available format**: `"Disponible - ARM {state}, SOLD {state}"`
- **_state_to_display()**: Maps state IDs to Spanish terms (pendiente → "pendiente", en_progreso → "en progreso", completado → "completado")

### Router Integration
Updated occupation router to use StateService:
- **TOMAR endpoint**: StateService.tomar() (state machine + Redis lock)
- **PAUSAR endpoint**: StateService.pausar() (releases lock, will update Estado_Detalle in Plan 03-03)
- **COMPLETAR endpoint**: StateService.completar() (completar transition + lock release)
- **Batch operations**: Still use OccupationService directly (no per-spool state machines)

### Dependency Injection
Added get_state_service() factory:
- **Injects**: OccupationService, SheetsRepository, MetadataRepository
- **Returns**: Fresh StateService instance per request
- **Pattern**: Follows existing Phase 2 dependency injection structure

### Request Models
Created models/state.py with:
- **StateTransitionRequest**: Internal coordination model
- **StateInfo**: Operation state representation
- **CombinedSpoolState**: Full spool state (occupation + operations + display)

## Technical Implementation

### Orchestration Pattern
StateService acts as a **coordination layer** between Phase 2 infrastructure and Phase 3 state machines:
```
Router → StateService → OccupationService (Redis locks)
             ↓
       State Machines (ARM/SOLD)
             ↓
       EstadoDetalleBuilder
             ↓
       Sheets Updates (TODOs for Plan 03-03)
```

### Hydration Pattern
State machines are **ephemeral** (created per request):
1. Fetch spool from Sheets
2. Create state machine instances
3. Force state to match Sheets columns
4. Trigger transitions
5. State machines destroyed after request

**No caching** - state machines always reflect current Sheets state.

### Integration with Phase 2
StateService **wraps** OccupationService:
- Maintains Phase 2 Redis locking (atomic TOMAR)
- Adds state machine layer on top
- Router sees unified interface (StateService)
- OccupationService remains intact

## Deviations from Plan

None - plan executed exactly as written.

## Verification Results

✅ **Task 1 Verification:**
```bash
$ python -c "from backend.services.state_service import StateService; print('StateService imported successfully')"
StateService imported successfully
```

✅ **Task 2 Verification:**
```bash
$ grep -r "StateService" backend/routers/occupation.py backend/core/dependency.py
# Found in both files - router uses StateService, dependency provides get_state_service()
```

✅ **Task 3 Verification:**
```bash
$ python -c "from backend.services.estado_detalle_builder import EstadoDetalleBuilder; \
             b = EstadoDetalleBuilder(); \
             print(b.build(None, 'pendiente', 'pendiente'))"
Disponible - ARM pendiente, SOLD pendiente
```

## Next Phase Readiness

**Ready for Plan 03-03:** State machine callbacks
- StateService orchestration complete
- Hydration logic working
- Need: Add on_enter_* callbacks to state machines
- Need: Wire callbacks to update Armador/Soldador/Fecha columns

**Ready for Plan 03-04:** Estado_Detalle updates
- EstadoDetalleBuilder producing correct strings
- Need: Add Estado_Detalle column writes to StateService.tomar()
- Need: Add Estado_Detalle updates on PAUSAR/COMPLETAR

**Blocker identified:** None

**Concern identified:** None

## Files Changed

### Created (3 files)
1. **backend/services/state_service.py** (265 lines)
   - StateService orchestrator with tomar/pausar/completar methods
   - Hydration logic for ARM and SOLD state machines
   - Integration with OccupationService

2. **backend/services/estado_detalle_builder.py** (78 lines)
   - EstadoDetalleBuilder formatter service
   - build() method for display strings
   - State-to-display mapping

3. **backend/models/state.py** (48 lines)
   - StateTransitionRequest, StateInfo, CombinedSpoolState
   - Request/response models for state operations

### Modified (2 files)
1. **backend/routers/occupation.py** (+13 lines, -7 lines)
   - Changed TOMAR/PAUSAR/COMPLETAR to use StateService
   - Updated imports and docstrings

2. **backend/core/dependency.py** (+35 lines)
   - Added get_state_service() factory
   - StateService dependency injection setup

## Commits

| Task | Commit | Message |
|------|--------|---------|
| 1 | 2930c8e | feat(03-02): implement StateService with hydration logic |
| 2 | f3c6379 | feat(03-02): integrate StateService with OccupationService |
| 3 | 5872101 | feat(03-02): implement EstadoDetalleBuilder formatter service |

## Performance

- **Duration:** 2.9 minutes (174 seconds)
- **Tasks completed:** 3/3
- **Files created:** 3
- **Files modified:** 2
- **Lines added:** ~391 lines

---

*Phase: 03-state-machine-and-collaboration*
*Plan: 02*
*Completed: 2026-01-27*
