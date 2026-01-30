# Bug 1: Estado_Detalle Fix - Actionable Feedback Checklist

**Date:** 2026-01-30
**Source:** Critique of Plan v1.0
**Target:** Plan v2.0 (Final)

---

## Instructions

This document converts the critique into specific, actionable feedback items. Each item includes:
- Clear problem statement
- Concrete solution
- Rationale for why the solution improves the plan
- Implementation effort estimate
- Breaking change assessment

---

## Critical Issues (Must Address)

### ❌ Issue 1: Hydration Logic Coupling Contradiction

**Problem:** Plan Section 5.2 proposes updating hydration logic to detect `pausado` state by checking `Ocupado_Por` column. This creates dangerous coupling between occupation state (managed by OccupationService) and state machine state (managed by StateService). The critique identifies this violates separation of concerns and creates race condition risks.

**Solution:**
Accept the coupling as a pragmatic tradeoff for v3.0 constraints. Update hydration logic to check `Ocupado_Por` column when detecting pausado state. Document this as technical debt for future refactoring.

**Specific Code Change:**
```python
# backend/services/state_service.py - _hydrate_arm_machine()

def _hydrate_arm_machine(self, spool) -> ARMStateMachine:
    """
    Hydrate ARM state machine from spool data.

    State detection logic:
    - completado: Fecha_Armado exists
    - pausado: Armador exists, Fecha_Armado null, Ocupado_Por null (⚠️ COUPLING)
    - en_progreso: Armador exists, Fecha_Armado null, Ocupado_Por exists
    - pendiente: Armador null (initial state)

    ⚠️ TECHNICAL DEBT: This creates coupling between occupation state and
    state machine state. Ideally, state machine state should be determinable
    from state-specific columns only. Consider adding Estado_ARM column in v4.0.
    """
    arm_machine = ARMStateMachine(
        tag_spool=spool.tag_spool,
        sheets_repo=self.sheets_repo,
        metadata_repo=self.metadata_repo
    )

    if spool.fecha_armado:
        arm_machine.current_state = arm_machine.completado
    elif spool.armador:
        # Check occupation to distinguish paused vs in-progress
        if spool.ocupado_por is None or spool.ocupado_por == "":
            arm_machine.current_state = arm_machine.pausado
        else:
            arm_machine.current_state = arm_machine.en_progreso
    # else: pendiente (initial state)

    return arm_machine
```

**Rationale:** This is the most pragmatic solution that:
- Avoids schema changes (no new columns needed)
- Avoids complex migration scripts
- Handles existing paused spools automatically
- Documents the coupling for future refactoring

**Effort:** Small (add comments and coupling acknowledgment)

**Breaking:** No

---

### ❌ Issue 2: Incomplete on_enter_en_progreso Callback

**Problem:** Plan mentions updating `on_enter_en_progreso()` to handle resume vs initial start, but doesn't provide the implementation. Without this fix, resuming paused work will overwrite Armador/Soldador columns, losing the original worker.

**Solution:**
Update `on_enter_en_progreso()` callback to detect source state using the `source` parameter. Only update Armador/Soldador when transitioning from `pendiente` (initial start). Do NOT update when transitioning from `pausado` (resume).

**Specific Code Change:**
```python
# backend/services/state_machines/arm_state_machine.py

async def on_enter_en_progreso(self, worker_nombre: str = None, source: 'State' = None, **kwargs):
    """
    Callback when ARM work starts or resumes.

    Behavior:
    - Initial start (pendiente → en_progreso): Update Armador with worker_nombre
    - Resume (pausado → en_progreso): Do NOT update Armador (preserve original)

    Args:
        worker_nombre: Worker name (only used for initial start)
        source: Source state from transition (auto-injected by statemachine)
        **kwargs: Other event arguments (ignored)
    """
    if worker_nombre and self.sheets_repo:
        # Check if resuming from pausado state
        if source and source.id == 'pausado':
            # Resume: Do not modify Armador (preserve original worker)
            logger.info(f"ARM work resumed for {self.tag_spool}, Armador unchanged")
            return

        # Initial start: Update Armador column
        row_num = self.sheets_repo.find_row_by_column_value(
            sheet_name=config.HOJA_OPERACIONES_NOMBRE,
            column_letter="G",
            value=self.tag_spool
        )

        if row_num:
            self.sheets_repo.update_cell_by_column_name(
                sheet_name=config.HOJA_OPERACIONES_NOMBRE,
                row=row_num,
                column_name="Armador",
                value=worker_nombre
            )
            logger.info(f"ARM work started for {self.tag_spool}, Armador set to {worker_nombre}")
```

**Same change for SOLDStateMachine.on_enter_en_progreso()**

**Rationale:** Preserves original worker data when resuming paused work. Critical for regulatory tracking and manufacturing floor accountability.

**Effort:** Small (add source parameter check)

**Breaking:** No (backward compatible - source param is optional)

---

### ❌ Issue 3: Incorrect Error Handling in StateService.pausar()

**Problem:** Plan shows StateService.pausar() logging a **warning** when state is invalid, but continuing execution. This allows PAUSAR to proceed even when state machine transition will fail, causing confusing errors.

**Solution:**
Raise `InvalidStateTransitionError` exception when current state is not `en_progreso`. Stop execution immediately instead of logging warning and continuing.

**Specific Code Change:**
```python
# backend/services/state_service.py - pausar()

# Trigger pausar transition BEFORE clearing occupation
if operacion == ActionType.ARM:
    current_arm_state = arm_machine.get_state_id()

    # Defensive validation - state machine will also validate, but this provides clearer error
    if current_arm_state != "en_progreso":
        raise InvalidStateTransitionError(
            f"Cannot PAUSAR ARM from state '{current_arm_state}'. "
            f"PAUSAR is only allowed from 'en_progreso' state.",
            tag_spool=tag_spool,
            current_state=current_arm_state,
            attempted_transition="pausar"
        )

    await arm_machine.pausar()
    logger.info(f"ARM state: en_progreso → pausado for {tag_spool}")

elif operacion == ActionType.SOLD:
    current_sold_state = sold_machine.get_state_id()

    if current_sold_state != "en_progreso":
        raise InvalidStateTransitionError(
            f"Cannot PAUSAR SOLD from state '{current_sold_state}'. "
            f"PAUSAR is only allowed from 'en_progreso' state.",
            tag_spool=tag_spool,
            current_state=current_sold_state,
            attempted_transition="pausar"
        )

    await sold_machine.pausar()
    logger.info(f"SOLD state: en_progreso → pausado for {tag_spool}")
```

**Rationale:** Fail-fast error handling prevents confusing errors downstream. Consistent with TOMAR/COMPLETAR error handling patterns.

**Effort:** Small (change warning to exception)

**Breaking:** No (existing valid code paths unchanged)

---

### ❌ Issue 4: Missing InvalidStateTransitionError Definition

**Problem:** Plan references `InvalidStateTransitionError` but this exception doesn't exist in the codebase.

**Solution:**
Define `InvalidStateTransitionError` in `backend/exceptions.py` with appropriate fields for debugging.

**Specific Code Change:**
```python
# backend/exceptions.py

class InvalidStateTransitionError(Exception):
    """
    Raised when attempting an invalid state machine transition.

    Examples:
    - PAUSAR from pendiente state (nothing to pause)
    - REANUDAR from en_progreso state (already in progress)
    - COMPLETAR from pausado state (need to resume first)
    """

    def __init__(
        self,
        message: str,
        tag_spool: str = None,
        current_state: str = None,
        attempted_transition: str = None
    ):
        self.tag_spool = tag_spool
        self.current_state = current_state
        self.attempted_transition = attempted_transition
        super().__init__(message)
```

**Rationale:** Provides clear exception type for state transition errors, making error handling and debugging easier.

**Effort:** Trivial (add new exception class)

**Breaking:** No (new exception type)

---

### ❌ Issue 5: Migration Strategy Contradiction

**Problem:** Plan Section 5.1 states "Option A (No Migration)" is acceptable and existing paused spools will "self-heal". But this only works if hydration logic is updated (Section 5.2). Without updated hydration, existing paused spools will have Armador overwritten on next TOMAR.

**Solution:**
Clarify that migration strategy depends on accepting the hydration coupling (Issue 1). Update Section 5 to explicitly state: "No migration script needed because updated hydration logic (Section 5.2) automatically detects pausado state for existing spools."

**Specific Documentation Change:**
```markdown
## 5. Migration Strategy

**Approach:** No migration script needed

**Rationale:**
The updated hydration logic (Section 5.2) detects pausado state by checking:
- Armador exists AND
- Fecha_Armado is null AND
- Ocupado_Por is null

This means existing paused spools in production will be automatically detected
as "pausado" state when hydrated. No manual migration required.

**Deployment Steps:**
1. Deploy code with updated state machines and hydration logic
2. Existing paused spools will show "Disponible - ARM pausado, SOLD pendiente" immediately
3. Next TOMAR on paused spool will trigger reanudar (not iniciar)
4. Armador/Soldador preserved correctly

**No downtime or manual intervention required.**
```

**Rationale:** Removes contradiction between Section 5.1 and Section 5.2. Makes migration strategy clear and consistent.

**Effort:** Trivial (documentation clarification)

**Breaking:** No

---

## Important Issues (Should Address)

### ⚠️ Issue 6: Incomplete StateService.tomar() Implementation

**Problem:** Plan Section 3.4 shows partial code for detecting pausado state in TOMAR, but doesn't show full implementation with all state branches (en_progreso, completado error handling).

**Solution:**
Provide complete implementation showing all state branches with proper error handling.

**Specific Code Change:**
```python
# backend/services/state_service.py - tomar()

# Trigger state machine transition (iniciar or reanudar)
if operacion == ActionType.ARM:
    current_arm_state = arm_machine.get_state_id()

    if current_arm_state == "pausado":
        # Resume paused work
        await arm_machine.reanudar(worker_nombre=request.worker_nombre)
        logger.info(f"ARM state: pausado → en_progreso for {tag_spool}")

    elif current_arm_state == "pendiente":
        # Start new work
        await arm_machine.iniciar(
            worker_nombre=request.worker_nombre,
            fecha_operacion=date.today()
        )
        logger.info(f"ARM state: pendiente → en_progreso for {tag_spool}")

    elif current_arm_state == "en_progreso":
        # Already in progress - should not happen (occupation lock prevents it)
        # If we reach here, it means OccupationService failed to detect existing lock
        logger.error(f"ARM already en_progreso for {tag_spool}, this indicates a bug in occupation lock validation")
        raise OccupationConflictError(f"Spool {tag_spool} is already occupied (ARM en_progreso)")

    elif current_arm_state == "completado":
        # Cannot restart completed work
        raise InvalidStateTransitionError(
            f"Cannot TOMAR ARM - operation already completed",
            tag_spool=tag_spool,
            current_state=current_arm_state,
            attempted_transition="iniciar"
        )

    else:
        # Unknown state - should never happen
        logger.error(f"Unknown ARM state '{current_arm_state}' for {tag_spool}")
        raise InvalidStateTransitionError(
            f"Unknown ARM state '{current_arm_state}'",
            tag_spool=tag_spool,
            current_state=current_arm_state,
            attempted_transition="iniciar"
        )
```

**Same for SOLD operation**

**Rationale:** Complete implementation handles all edge cases. Prevents confusing errors if unexpected state is encountered.

**Effort:** Medium (add all branches and error handling)

**Breaking:** No

---

### ⚠️ Issue 7: Missing Test Cases

**Problem:** Plan test coverage is good but misses several critical edge cases identified in critique.

**Solution:**
Add the following test cases to test plan:

**Add to Unit Tests:**
```python
# tests/unit/test_arm_state_machine.py

def test_pausar_from_pendiente_raises_transition_not_allowed():
    """Cannot pause work that hasn't started."""
    pass

def test_pausar_from_completado_raises_transition_not_allowed():
    """Cannot pause work that's already completed."""
    pass

def test_reanudar_from_pendiente_raises_transition_not_allowed():
    """Cannot resume work that was never started."""
    pass

def test_reanudar_from_en_progreso_raises_transition_not_allowed():
    """Cannot resume work that's already in progress."""
    pass
```

**Add to Integration Tests:**
```python
# tests/integration/test_occupation_flow.py

async def test_concurrent_pausar_same_spool():
    """Only lock owner can PAUSAR."""
    pass

async def test_pausar_with_expired_lock():
    """Cannot PAUSAR if lock expired."""
    pass

async def test_double_pausar_fails():
    """Cannot PAUSAR already paused spool."""
    pass

async def test_completar_from_pausado_requires_tomar_first():
    """Cannot COMPLETAR paused spool without resuming."""
    pass

async def test_hydrate_arm_machine_detects_pausado_state():
    """Hydration detects pausado from Sheets data."""
    pass
```

**Rationale:** These test cases catch edge cases that could cause data corruption or confusing errors.

**Effort:** Medium (5 additional test cases)

**Breaking:** No

---

### ⚠️ Issue 8: Missing cancelar from pausado Transition

**Problem:** Plan Open Question 3 suggests allowing `pausado → pendiente` (cancelar) transition, but doesn't add it to state machine definition.

**Solution:**
Update transition definition to allow cancelar from both en_progreso AND pausado states.

**Specific Code Change:**
```python
# backend/services/state_machines/arm_state_machine.py

# Define transitions
iniciar = pendiente.to(en_progreso)
pausar = en_progreso.to(pausado)
reanudar = pausado.to(en_progreso)
completar = en_progreso.to(completado)
cancelar = (en_progreso.to(pendiente) |  # Cancel in-progress work
            pausado.to(pendiente))         # Cancel paused work
```

**Add callback for cancelar from pausado:**
```python
async def on_enter_pendiente(self, source: 'State' = None, **kwargs):
    """
    Callback when returning to pendiente state (CANCELAR).

    Clears Armador column to revert the spool to unassigned state.

    Args:
        source: Source state from transition (en_progreso or pausado)
        **kwargs: Other event arguments (ignored)
    """
    # Clear Armador if coming from EN_PROGRESO or PAUSADO
    if source and source.id in ['en_progreso', 'pausado'] and self.sheets_repo:
        row_num = self.sheets_repo.find_row_by_column_value(
            sheet_name=config.HOJA_OPERACIONES_NOMBRE,
            column_letter="G",
            value=self.tag_spool
        )

        if row_num:
            self.sheets_repo.update_cell_by_column_name(
                sheet_name=config.HOJA_OPERACIONES_NOMBRE,
                row=row_num,
                column_name="Armador",
                value=""
            )
            logger.info(f"CANCELAR ARM from {source.id} - Armador cleared for {self.tag_spool}")
```

**Same for SOLD state machine**

**Rationale:** Workers should be able to cancel paused work, not just in-progress work. This handles abandonment scenarios.

**Effort:** Small (add transition variant and update callback)

**Breaking:** No (adds new capability)

---

## Minor Issues (Nice to Have)

### ℹ️ Issue 9: Improve Logging Clarity

**Problem:** Logging shows final state but not the transition (from → to), making debugging harder.

**Solution:**
Update log messages to show transition explicitly.

**Specific Code Change:**
```python
# Before
logger.info(f"ARM state machine transitioned to {arm_machine.get_state_id()}")

# After
logger.info(f"ARM state: {current_arm_state} → {arm_machine.get_state_id()} for {tag_spool}")
```

**Apply to all state transition logs in StateService**

**Rationale:** Clearer logs make debugging and production monitoring easier.

**Effort:** Trivial (update log messages)

**Breaking:** No

---

### ℹ️ Issue 10: Add Test Fixtures for Complex Setups

**Problem:** Integration tests require complex Sheets setup. Without fixtures, tests will have a lot of duplicated setup code.

**Solution:**
Add pytest fixtures for common spool states.

**Specific Code Change:**
```python
# tests/integration/conftest.py

@pytest.fixture
async def spool_arm_en_progreso(sheets_repo, redis_client):
    """
    Create test spool with ARM en_progreso, occupied by MR(93).

    State:
    - TAG_SPOOL: TEST-PAUSAR-01
    - Armador: MR(93)
    - Fecha_Armado: None
    - Ocupado_Por: MR(93)
    - Redis lock: spool:TEST-PAUSAR-01:lock = MR(93)
    """
    # Setup logic...
    yield spool
    # Cleanup logic...

@pytest.fixture
async def spool_arm_pausado(sheets_repo, redis_client):
    """
    Create test spool with ARM pausado (paused after PAUSAR).

    State:
    - TAG_SPOOL: TEST-PAUSAR-02
    - Armador: MR(93)
    - Fecha_Armado: None
    - Ocupado_Por: None (cleared)
    - Redis lock: None (released)
    """
    # Setup logic...
    yield spool
    # Cleanup logic...
```

**Rationale:** Reduces test duplication, makes tests more readable, easier to maintain.

**Effort:** Medium (create fixtures)

**Breaking:** No

---

## Feedback Summary Table

| # | Issue | Severity | Effort | Breaking | Status |
|---|-------|----------|--------|----------|--------|
| 1 | Hydration coupling contradiction | Critical | Small | No | ✅ To Apply |
| 2 | Incomplete on_enter_en_progreso | Critical | Small | No | ✅ To Apply |
| 3 | Incorrect error handling in pausar() | Critical | Small | No | ✅ To Apply |
| 4 | Missing InvalidStateTransitionError | Critical | Trivial | No | ✅ To Apply |
| 5 | Migration strategy contradiction | Critical | Trivial | No | ✅ To Apply |
| 6 | Incomplete tomar() implementation | Important | Medium | No | ✅ To Apply |
| 7 | Missing test cases | Important | Medium | No | ✅ To Apply |
| 8 | Missing cancelar from pausado | Important | Small | No | ✅ To Apply |
| 9 | Improve logging clarity | Minor | Trivial | No | ✅ To Apply |
| 10 | Add test fixtures | Minor | Medium | No | ⚠️ Optional |

**Total Estimated Additional Effort:** +2-3 hours (brings total from 6h to 8-9h)

---

## Rejected Feedback Items

None. All critique items are valid and should be applied.

---

## Next Steps

Proceed to **Phase 4: Apply Feedback and Refine Plan** to create `bug1-estado-detalle-plan-v2-final.md` with all feedback items incorporated.

---

**Feedback Checklist Complete - Ready for Phase 4**
