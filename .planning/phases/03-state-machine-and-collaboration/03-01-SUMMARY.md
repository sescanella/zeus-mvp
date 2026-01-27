---
phase: 03-state-machine-and-collaboration
plan: 01
subsystem: state-management
tags: [state-machine, python-statemachine, hierarchical-states, guards]

requires:
  - 02-02 # OccupationService TOMAR/PAUSAR/COMPLETAR
  - 01-08b-GAP # v3.0 columns in production

provides:
  - Estado_Detalle column at position 67
  - ARM state machine (3 states, 3 transitions)
  - SOLD state machine with ARM dependency guard
  - BaseOperationStateMachine shared foundation

affects:
  - 03-02 # Will add callbacks to state machines
  - 03-03 # StateService will orchestrate these machines

tech-stack:
  added:
    - python-statemachine==2.5.0
  patterns:
    - Per-operation state machines (ARM/SOLD separate)
    - Guard conditions for operation dependencies
    - Validator pattern for explicit error messages

key-files:
  created:
    - backend/scripts/add_estado_detalle_column.py
    - backend/services/state_machines/__init__.py
    - backend/services/state_machines/base_state_machine.py
    - backend/services/state_machines/arm_state_machine.py
    - backend/services/state_machines/sold_state_machine.py
  modified:
    - backend/config.py
    - backend/requirements.txt

decisions:
  - id: PHASE3-01-ESTADO-DETALLE
    what: Add Estado_Detalle column at position 67
    why: Store combined state display (occupation + operation progress)
    impact: New column in production sheet for UI display strings
    alternatives: Calculate on-the-fly (rejected - too slow for tablets)

  - id: PHASE3-01-SEPARATE-MACHINES
    what: Separate state machines per operation (ARM/SOLD)
    why: Prevents state explosion (9 states instead of 27+)
    impact: StateService orchestrates multiple machines
    alternatives: Single combined state machine (rejected - unmaintainable)

  - id: PHASE3-01-GUARDS
    what: Use guard + validator pattern for dependencies
    why: Guards control transitions, validators provide error messages
    impact: SOLD blocks iniciar if ARM not started
    alternatives: Manual validation in service layer (rejected - less declarative)

metrics:
  duration: 2.87 min
  completed: 2026-01-27
---

# Phase 03 Plan 01: State Machine Foundation Summary

**One-liner:** Estado_Detalle column added + ARM/SOLD state machines with dependency guards using python-statemachine library

## What Was Built

### Estado_Detalle Column Migration
Created production-ready migration script to add Estado_Detalle column at position 67 (after v3.0 columns at 64-66). Column will store formatted display strings like "MR(93) trabajando ARM (SOLD pendiente)" or "Disponible - ARM pendiente, SOLD pendiente".

Migration includes:
- Idempotency check (safe to run multiple times)
- Dry-run mode for testing
- Grid expansion before column addition
- Metadata event logging
- Confirmation prompts for safety

### ARM State Machine
Implemented ARM (Assembly) operation state machine with 3 states:
- **pendiente** (initial): ARM not started (Armador = None)
- **en_progreso**: ARM in progress (Armador != None, Fecha_Armado = None)
- **completado** (final): ARM completed (Fecha_Armado != None)

Transitions:
- `iniciar`: pendiente → en_progreso
- `completar`: en_progreso → completado
- `cancelar`: en_progreso → pendiente

No dependency guards - ARM is the first operation in the workflow.

### SOLD State Machine
Implemented SOLD (Welding) operation state machine with ARM dependency:
- Same 3-state pattern as ARM (pendiente/en_progreso/completado)
- **Guard method** `arm_not_initiated()`: Returns boolean indicating if ARM started
- **Validator method** `validate_arm_initiated()`: Raises DependenciasNoSatisfechasError if ARM not started
- **before_iniciar hook**: Prevents SOLD from starting without ARM

Guard checks if Armador column is None (ARM not initiated), blocking SOLD's iniciar transition.

### Base State Machine
Created `BaseOperationStateMachine` abstract class with:
- Common state name constants (PENDIENTE, EN_PROGRESO, COMPLETADO)
- Constructor pattern (tag_spool, sheets_repo, metadata_repo)
- State ID accessor method
- Foundation for ARM, SOLD, and future operations (METROLOGIA)

## Technical Implementation

### python-statemachine Integration
Installed and integrated python-statemachine v2.5.0:
- Declarative state and transition definitions
- Guard conditions for dependency validation
- Callback hooks for state changes (to be added in Plan 02)
- Async support (ready for Phase 3 expansion)

### Architecture Pattern
**Per-operation state machines** instead of single combined machine:
- ARM has its own 3-state machine
- SOLD has its own 3-state machine with ARM guard
- StateService (future Plan 03) will orchestrate both
- Prevents state explosion: 6 states total vs 27+ in combined approach

### Migration Safety
Estado_Detalle column addition follows Phase 1 patterns:
- Same script structure as add_v3_columns.py
- Idempotency via column existence check
- Sheet grid expansion before header addition
- config.py single source of truth for V3_COLUMNS
- Metadata logging for audit trail

## Deviations from Plan

None - plan executed exactly as written.

## Verification Results

✅ **Task 1 Verification:**
- Dry-run successful: Would add column at position 67
- Actual execution: Sheet expanded from 66 to 67 columns
- Column header "Estado_Detalle" added at BO1
- Visible in Google Sheets UI

✅ **Task 2 Verification:**
```bash
$ python -c "from backend.services.state_machines.arm_state_machine import ARMStateMachine; \
             m = ARMStateMachine('TEST-001', None, None); \
             print(f'Initial: {m.current_state.id}')"
Initial: pendiente
```

✅ **Task 3 Verification:**
```bash
$ python -c "from backend.services.state_machines.sold_state_machine import SOLDStateMachine; \
             m = SOLDStateMachine('TEST-001', None, None); \
             print(f'Has guard: {hasattr(m, \"arm_not_initiated\")}')"
Has guard: True
```

## Next Phase Readiness

**Ready for Plan 02:** Add state machine callbacks
- State machines exist and are instantiable
- Transition methods defined (iniciar, completar, cancelar)
- Guard/validator pattern established
- Needs: on_enter_* callbacks for Armador/Soldador column updates

**Ready for Plan 03:** StateService orchestration
- Both ARM and SOLD machines ready
- Constructor pattern consistent
- Guard conditions in place
- Needs: Hydration logic to sync with Sheets state

**Blocker identified:** None

**Concern identified:** None

## Files Changed

### Created (5 files)
1. **backend/scripts/add_estado_detalle_column.py** (280 lines)
   - Migration script for Estado_Detalle column
   - Idempotency check, dry-run mode, metadata logging

2. **backend/services/state_machines/__init__.py** (14 lines)
   - Package exports for ARMStateMachine and SOLDStateMachine

3. **backend/services/state_machines/base_state_machine.py** (59 lines)
   - Abstract base class with common state machine functionality
   - State name constants, constructor pattern

4. **backend/services/state_machines/arm_state_machine.py** (60 lines)
   - ARM operation state machine (3 states, 3 transitions)
   - No dependency guards

5. **backend/services/state_machines/sold_state_machine.py** (104 lines)
   - SOLD operation state machine with ARM dependency
   - Guard method + validator for dependency checking

### Modified (2 files)
1. **backend/config.py** (+7 lines)
   - Added Estado_Detalle to V3_COLUMNS list

2. **backend/requirements.txt** (+1 line)
   - Added python-statemachine==2.5.0

## Commits

| Task | Commit | Message |
|------|--------|---------|
| 1 | 89cd263 | feat(03-01): add Estado_Detalle column to Operaciones sheet |
| 2+3 | ee60eb1 | feat(03-01): create ARM and SOLD state machines with guards |

## Performance

- **Duration:** 2.87 minutes (172 seconds)
- **Tasks completed:** 3/3
- **Files created:** 5
- **Files modified:** 2
- **Production impact:** Estado_Detalle column added (67 total columns)

---

*Phase: 03-state-machine-and-collaboration*
*Plan: 01*
*Completed: 2026-01-27*
