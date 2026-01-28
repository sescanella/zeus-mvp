---
phase: 06
plan: 01
subsystem: reparacion-state-machine
tags: [state-machine, reparacion, occupation, cycle-tracking, testing]
requires: [06-02]
provides:
  - REPARACIONStateMachine with 4 states
  - ReparacionService with TOMAR/PAUSAR/COMPLETAR/CANCELAR methods
  - REPARACION ActionType and EventoTipo enums
  - 22 passing unit tests for state transitions
affects: [06-03, 06-04]
tech-stack:
  added: []
  patterns:
    - 4-state occupation workflow (RECHAZADO → EN_REPARACION → REPARACION_PAUSADA → PENDIENTE_METROLOGIA)
    - State machine callbacks for atomic column updates
    - Cycle tracking preservation across state transitions
    - CycleCounterService integration for estado formatting
key-files:
  created:
    - backend/services/state_machines/reparacion_state_machine.py
    - backend/services/reparacion_service.py
    - backend/services/__init__.py
    - tests/unit/test_reparacion_machine.py
  modified:
    - backend/services/state_machines/__init__.py
    - backend/models/enums.py
decisions:
  - id: state-machine-pattern
    choice: 4-state machine with occupation management
    rationale: Follows Phase 3 ARM/SOLD pattern with PAUSAR support for flexibility
  - id: cycle-preservation
    choice: Preserve cycle count across all state transitions
    rationale: Cycle increments only on metrología RECHAZADO, must persist through repair workflow
  - id: auto-queue
    choice: COMPLETAR automatically sets PENDIENTE_METROLOGIA
    rationale: Repaired spools immediately return to metrología queue without manual intervention
metrics:
  duration: 7.7 minutes
  tests-added: 22
  completed: 2026-01-28
---

# Phase 06 Plan 01: Reparación State Machine Summary

**One-liner:** 4-state machine for RECHAZADO spool repair with TOMAR/PAUSAR/COMPLETAR actions and automatic metrología re-queue

## What Was Built

Implemented reparación state machine with occupation management following Phase 3 patterns. Workers can TOMAR rejected spools, PAUSAR mid-repair, COMPLETAR to return to metrología queue, or CANCELAR to abort. State machine preserves cycle count across transitions and automatically updates Ocupado_Por, Fecha_Ocupacion, and Estado_Detalle columns via callbacks.

### Core Components

**1. REPARACIONStateMachine** (`backend/services/state_machines/reparacion_state_machine.py`)
- 4 states: rechazado (initial), en_reparacion, reparacion_pausada, pendiente_metrologia (final)
- 4 transitions: tomar (from rechazado or reparacion_pausada), pausar, completar, cancelar
- Callbacks for atomic column updates on state entry:
  - `on_enter_en_reparacion`: Set Ocupado_Por + Fecha_Ocupacion + Estado_Detalle with cycle
  - `on_enter_reparacion_pausada`: Clear occupation + preserve cycle in Estado_Detalle
  - `on_enter_pendiente_metrologia`: Clear occupation + set estado to PENDIENTE_METROLOGIA
  - `on_enter_rechazado`: Clear occupation + restore RECHAZADO estado with cycle (CANCELAR only)
- CycleCounterService integration for estado formatting with cycle info

**2. ReparacionService** (`backend/services/reparacion_service.py`)
- `tomar_reparacion()`: Validates BLOQUEADO, triggers TOMAR, logs TOMAR_REPARACION event
- `pausar_reparacion()`: Verifies ownership, triggers PAUSAR, logs PAUSAR_REPARACION event
- `completar_reparacion()`: Triggers COMPLETAR, auto-queues for metrología, logs COMPLETAR_REPARACION event
- `cancelar_reparacion()`: Triggers CANCELAR, returns to RECHAZADO, logs CANCELAR_REPARACION event
- All methods publish SSE events for real-time dashboard updates
- Injects CycleCounterService for cycle extraction and estado building

**3. ActionType and EventoTipo Enums** (`backend/models/enums.py`)
- Added `REPARACION` to ActionType enum
- Added REPARACION events to EventoTipo: TOMAR_REPARACION, PAUSAR_REPARACION, COMPLETAR_REPARACION, CANCELAR_REPARACION

**4. Comprehensive Test Suite** (`tests/unit/test_reparacion_machine.py`)
- 22 tests covering all state transitions and column updates
- State configuration tests (3 tests): initial state, final state, 4 states total
- TOMAR transition tests (4 tests): from RECHAZADO, from PAUSADA, occupation updates, cycle info
- PAUSAR transition tests (4 tests): from EN_REPARACION, clears occupation, preserves cycle, invalid transitions
- COMPLETAR transition tests (3 tests): to PENDIENTE_METROLOGIA, clears occupation, invalid transitions
- CANCELAR transition tests (3 tests): from EN_REPARACION, from PAUSADA, restores RECHAZADO estado
- Integration workflow tests (5 tests): complete workflow, pause/resume, cancelar, cycle tracking

## Technical Decisions

### 4-State Machine Pattern
**Decision:** Use 4 states (RECHAZADO → EN_REPARACION → REPARACION_PAUSADA → PENDIENTE_METROLOGIA) instead of 3-state ARM/SOLD pattern

**Rationale:**
- Adds REPARACION_PAUSADA state for mid-repair flexibility (worker can pause and another can resume)
- PENDIENTE_METROLOGIA as final state enables automatic re-queue for metrología inspection
- Follows occupation-based workflow pattern established in Phase 3

**Trade-offs:**
- ✅ Flexible workflow supports pausing and resuming repair work
- ✅ Automatic return to metrología queue (no manual intervention)
- ⚠️ More complex than 3-state pattern (4 states vs 3)
- ✅ Consistent with ARM/SOLD TOMAR/PAUSAR pattern

### Cycle Count Preservation
**Decision:** Preserve cycle count across all state transitions (EN_REPARACION, REPARACION_PAUSADA, PENDIENTE_METROLOGIA)

**Rationale:**
- Cycle increments only on metrología RECHAZADO event (not during repair)
- Cycle must persist through entire repair workflow until next metrología decision
- CycleCounterService provides consistent estado formatting with cycle info

**Implementation:**
- State machine reads Estado_Detalle on entry to EN_REPARACION
- Extracts cycle count using `cycle_counter.extract_cycle_count()`
- Builds estado strings using `cycle_counter.build_reparacion_estado()` for EN_REPARACION and REPARACION_PAUSADA
- PENDIENTE_METROLOGIA clears cycle display (next metrología decision will increment or reset)

### Automatic Metrología Re-queue
**Decision:** COMPLETAR transition automatically sets Estado_Detalle to PENDIENTE_METROLOGIA

**Rationale:**
- Repaired spools immediately appear in metrología spool list (no manual queue step)
- Any metrólogo can inspect repaired spool (no assignment to original inspector)
- Simplifies workflow - worker completes repair and moves on

**Alternatives considered:**
- Manual re-queue step: Adds unnecessary complexity and delay
- Separate "Re-inspection" queue: Creates visual distinction with no functional benefit

## Key Patterns

### Pattern 1: Occupation Management via State Machine
```python
# TOMAR transition sets occupation
reparacion_machine.tomar(worker_id=93, worker_nombre="MR(93)")
# on_enter_en_reparacion callback:
# - Sets Ocupado_Por = "MR(93)"
# - Sets Fecha_Ocupacion = "28-01-2026"
# - Sets Estado_Detalle = "EN_REPARACION (Ciclo 2/3) - Ocupado: MR(93)"

# PAUSAR transition clears occupation
reparacion_machine.pausar()
# on_enter_reparacion_pausada callback:
# - Clears Ocupado_Por = ""
# - Clears Fecha_Ocupacion = ""
# - Preserves cycle: Estado_Detalle = "REPARACION_PAUSADA (Ciclo 2/3)"
```

### Pattern 2: Cycle Tracking Integration
```python
# Extract cycle count from Estado_Detalle
estado = "RECHAZADO (Ciclo 2/3) - Pendiente reparación"
cycle = cycle_counter.extract_cycle_count(estado)  # Returns 2

# Build estado with cycle info
estado_en_reparacion = cycle_counter.build_reparacion_estado(
    "en_reparacion",
    cycle,
    "MR(93)"
)
# Returns: "EN_REPARACION (Ciclo 2/3) - Ocupado: MR(93)"
```

### Pattern 3: Service Orchestration
```python
# ReparacionService orchestrates validation + state machine + metadata
async def tomar_reparacion(tag_spool, worker_id, worker_nombre):
    # 1. Validate prerequisites (RECHAZADO, not BLOQUEADO, not occupied)
    spool = sheets_repo.get_spool_by_tag(tag_spool)
    validation_service.validar_puede_tomar_reparacion(spool, worker_id)

    # 2. Check cycle limit
    cycle = cycle_counter.extract_cycle_count(spool.estado_detalle)
    if cycle_counter.should_block(cycle):
        raise SpoolBloqueadoError(tag_spool)

    # 3. Execute state transition
    machine = REPARACIONStateMachine(tag_spool, sheets_repo, metadata_repo, cycle_counter)
    machine.current_state = machine.rechazado  # Hydrate to current state
    machine.tomar(worker_id=worker_id, worker_nombre=worker_nombre)

    # 4. Log metadata event
    metadata_repo.append_event({
        "evento_tipo": "TOMAR_REPARACION",
        "metadata_json": json.dumps({"cycle": cycle})
    })

    # 5. Publish SSE event
    await redis_event_service.publish_spool_update(...)
```

## Test Coverage

### State Configuration Tests (3 tests)
- `test_rechazado_is_initial_state`: Verify RECHAZADO is initial state
- `test_pendiente_metrologia_is_final_state`: Verify PENDIENTE_METROLOGIA is terminal
- `test_has_exactly_four_states`: Verify machine has 4 states

### TOMAR Transition Tests (4 tests)
- `test_tomar_from_rechazado`: RECHAZADO → EN_REPARACION transition
- `test_tomar_from_reparacion_pausada`: REPARACION_PAUSADA → EN_REPARACION (resume)
- `test_tomar_updates_occupation_columns`: Verifies Ocupado_Por, Fecha_Ocupacion, Estado_Detalle updates
- `test_tomar_estado_includes_cycle_info`: Verifies Estado_Detalle includes "Ciclo X/3"

### PAUSAR Transition Tests (4 tests)
- `test_pausar_from_en_reparacion`: EN_REPARACION → REPARACION_PAUSADA transition
- `test_pausar_clears_occupation`: Verifies Ocupado_Por and Fecha_Ocupacion cleared
- `test_pausar_preserves_cycle_info`: Verifies Estado_Detalle preserves "Ciclo X/3"
- `test_cannot_pausar_from_rechazado`: Invalid transition raises TransitionNotAllowed

### COMPLETAR Transition Tests (3 tests)
- `test_completar_to_pendiente_metrologia`: EN_REPARACION → PENDIENTE_METROLOGIA transition
- `test_completar_clears_occupation_and_sets_pendiente_metrologia`: Verifies occupation cleared and estado set
- `test_cannot_completar_from_pausada`: Invalid transition raises TransitionNotAllowed

### CANCELAR Transition Tests (3 tests)
- `test_cancelar_from_en_reparacion_to_rechazado`: EN_REPARACION → RECHAZADO transition
- `test_cancelar_from_reparacion_pausada_to_rechazado`: REPARACION_PAUSADA → RECHAZADO transition
- `test_cancelar_clears_occupation_and_restores_rechazado`: Verifies occupation cleared and RECHAZADO estado restored

### Integration Workflow Tests (5 tests)
- `test_complete_workflow_rechazado_to_pendiente_metrologia`: Full workflow RECHAZADO → TOMAR → COMPLETAR → PENDIENTE_METROLOGIA
- `test_workflow_with_pause_and_resume`: Workflow with PAUSAR and resume (TOMAR again)
- `test_workflow_with_cancelar`: Workflow with CANCELAR (return to RECHAZADO)
- `test_cycle_tracking_across_transitions`: Verifies cycle count preserved through all transitions
- `test_pendiente_metrologia_is_final_state_no_transitions`: Verifies terminal state has no outgoing transitions

## Integration Points

### Upstream (Depends On)
- **06-02**: CycleCounterService for cycle parsing, incrementing, and estado building
- **Phase 3**: Base state machine pattern and occupation management
- **Phase 5**: Estado_Detalle as display string pattern

### Downstream (Affects)
- **06-03**: API endpoints will instantiate ReparacionService and call TOMAR/PAUSAR/COMPLETAR/CANCELAR methods
- **06-04**: Frontend will display REPARACION as 4th operation button and show cycle info in spool list
- **Future**: SSE events enable real-time dashboard updates for repair work

## Deviations from Plan

None - plan executed exactly as written.

## Performance Characteristics

- **State machine transitions**: O(1) state lookup + callback execution
- **Column updates**: Single `batch_update_by_column_name` per transition (3 columns atomically)
- **Cycle extraction**: O(1) regex search with compiled pattern
- **Test execution**: 22 tests run in 0.08 seconds

## Next Phase Readiness

**Phase 6 Plan 03 (API Endpoints) can proceed:**
- ✅ ReparacionService ready with all TOMAR/PAUSAR/COMPLETAR/CANCELAR methods
- ✅ State machine handles occupation management automatically
- ✅ Metadata logging and SSE event publishing integrated
- ✅ CycleCounterService provides cycle validation and BLOQUEADO enforcement

**Unblocked work:**
- Create POST `/api/actions/tomar-reparacion` endpoint
- Create POST `/api/actions/pausar-reparacion` endpoint
- Create POST `/api/actions/completar-reparacion` endpoint
- Create POST `/api/actions/cancelar-reparacion` endpoint
- Frontend integration for REPARACION operation selection

## Lessons Learned

1. **State machine callback signatures**: Callbacks receive kwargs directly as parameters, not through `event_data.kwargs` object
2. **Hydration pattern critical**: Tests must set `machine.current_state` explicitly to simulate StateService hydration
3. **Cycle preservation**: CycleCounterService provides consistent estado formatting across all states
4. **Atomic column updates**: `batch_update_by_column_name` prevents race conditions between occupation and estado updates

---

**Duration:** 7.7 minutes
**Tests Added:** 22 (all passing)
**Commits:** 2 (97e9ee0, f48ce36)
**Completed:** 2026-01-28
