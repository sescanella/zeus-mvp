# Bug 1: Estado_Detalle Fix - Plan v1.0 Critique

**Date:** 2026-01-30
**Reviewer:** Senior Code Reviewer
**Plan Version:** v1.0

---

## Executive Summary

The plan is **architecturally sound** and addresses the root cause correctly by adding a `pausado` state to the state machines. However, there are **several critical issues** that must be addressed before implementation:

1. **Hydration logic creates dangerous coupling** between occupation state and state machine state
2. **Incomplete analysis of on_enter_en_progreso callback** behavior for resume scenarios
3. **Missing transition guards** for pausar/reanudar operations
4. **Inconsistent error handling** when pausar is called from wrong state
5. **Migration strategy is too optimistic** - existing paused spools will not self-heal correctly

**Overall Assessment:** NEEDS REVISION (Medium severity issues found)

---

## 1. Architectural Consistency

### ✅ STRENGTH: Correct Approach Choice

The decision to use the State Machine approach is **correct and well-justified**:
- Aligns with hierarchical state machine design pattern
- Maintains consistency with TOMAR/COMPLETAR operations
- Provides explicit semantics for paused state
- Future-proof for additional transitions

**No changes needed in this area.**

---

### ⚠️ CONCERN: Hydration Logic Coupling

**Issue:** Section 5.2 introduces a **dangerous coupling** between `Ocupado_Por` column (managed by OccupationService) and state machine hydration (managed by StateService).

**Problematic Code:**
```python
def _hydrate_arm_machine(self, spool) -> ARMStateMachine:
    # ...
    elif spool.armador:
        if spool.ocupado_por is None or spool.ocupado_por == "":
            # Paused: Worker assigned but no current occupation
            arm_machine.current_state = arm_machine.pausado  # ⚠️ DANGEROUS
        else:
            # In progress: Worker assigned and occupied
            arm_machine.current_state = arm_machine.en_progreso
```

**Why This Is Dangerous:**

1. **Violation of Single Responsibility:**
   - State machine state should be determinable from state machine columns (Armador, Fecha_Armado)
   - Occupation state should be determinable from occupation columns (Ocupado_Por, Fecha_Ocupacion)
   - Mixing these creates tight coupling

2. **Race Condition Risk:**
   - If OccupationService clears Ocupado_Por but state machine hasn't transitioned to pausado yet, hydration will incorrectly show pausado state
   - If StateService hydrates after OccupationService but before pausar transition, state will be wrong

3. **Breaks Separation of Concerns:**
   - Hydration should be idempotent and deterministic based only on state machine columns
   - This change makes hydration dependent on external occupation state

**Proposed Solution:**

**Option A: Add Paused Tracking Column (BEST)**
- Add new column: `Estado_ARM` (enum: PENDIENTE/EN_PROGRESO/PAUSADO/COMPLETADO)
- Add new column: `Estado_SOLD` (enum: PENDIENTE/EN_PROGRESO/PAUSADO/COMPLETADO)
- State machine callbacks update these columns explicitly
- Hydration reads from these columns (NOT from Ocupado_Por)
- **Tradeoff:** Requires schema change (2 new columns)
- **Benefit:** Clean separation of concerns, no coupling

**Option B: Keep Hydration Simple, Rely on Transition Sequence (ACCEPTABLE)**
- Do NOT update hydration logic
- Hydration continues to detect only 3 states: pendiente/en_progreso/completado
- When StateService.pausar() is called:
  1. Hydrate ARM machine (will show "en_progreso")
  2. Trigger pausar transition (now shows "pausado")
  3. Call OccupationService.pausar() (clears Ocupado_Por)
  4. Estado_Detalle is built with "pausado" state
- **Tradeoff:** Existing paused spools will show "en_progreso" until next operation (temporary inconsistency)
- **Benefit:** No coupling, simpler implementation

**Recommendation: Option B** (Keep hydration simple, accept temporary inconsistency for existing paused spools)

---

## 2. Completeness

### ⚠️ INCOMPLETE: on_enter_en_progreso Callback Behavior

**Issue:** Section 3.4 mentions updating `on_enter_en_progreso()` to handle resume vs initial start, but the plan **does not provide the implementation**.

**Current Callback:**
```python
async def on_enter_en_progreso(self, worker_nombre: str = None, **kwargs):
    """Callback when ARM work starts."""
    if worker_nombre and self.sheets_repo:
        # Update Armador column with worker name
        self.sheets_repo.update_cell_by_column_name(
            sheet_name=config.HOJA_OPERACIONES_NOMBRE,
            row=row_num,
            column_name="Armador",
            value=worker_nombre
        )
```

**Problem:** When resuming from pausado, this callback will **overwrite Armador** with the new worker's name, losing the original worker.

**Expected Behavior:**
- **Initial start (pendiente → en_progreso):** Update Armador with worker_nombre
- **Resume (pausado → en_progreso):** Do NOT update Armador (preserve original worker)

**Proposed Solution:**
```python
async def on_enter_en_progreso(self, worker_nombre: str = None, source: 'State' = None, **kwargs):
    """
    Callback when ARM work starts or resumes.

    Args:
        worker_nombre: Worker name (only used for initial start, ignored for resume)
        source: Source state from transition (used to detect resume)
        **kwargs: Other event arguments
    """
    if worker_nombre and self.sheets_repo:
        # Only update Armador if coming from pendiente (initial start)
        # Do NOT update if coming from pausado (resume)
        if source and source.id == 'pausado':
            # Resume: Do not modify Armador
            logger.info(f"ARM work resumed by {worker_nombre}, Armador unchanged")
            return

        # Initial start: Update Armador
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
```

**Same change needed for SOLDStateMachine.on_enter_en_progreso()**

---

### ⚠️ INCOMPLETE: StateService.tomar() Implementation

**Issue:** Section 3.4 shows partial code for detecting pausado state in TOMAR, but the full implementation is not provided.

**Missing Details:**
1. How does `reanudar` transition pass worker_nombre parameter?
2. Should the new worker name be passed to `reanudar` or ignored?
3. What happens to Ocupado_Por column when resuming?

**Proposed Complete Implementation:**
```python
# In StateService.tomar()
if operacion == ActionType.ARM:
    current_arm_state = arm_machine.get_state_id()

    if current_arm_state == "pausado":
        # Resume paused work
        # NOTE: Pass worker_nombre but on_enter_en_progreso will ignore it
        await arm_machine.reanudar(worker_nombre=request.worker_nombre)
        logger.info(f"ARM resumed from pausado to {arm_machine.get_state_id()}")
    elif current_arm_state == "pendiente":
        # Start new work
        await arm_machine.iniciar(
            worker_nombre=request.worker_nombre,
            fecha_operacion=date.today()
        )
        logger.info(f"ARM started from pendiente to {arm_machine.get_state_id()}")
    elif current_arm_state == "en_progreso":
        # Already in progress - this should not happen (occupation lock prevents it)
        logger.warning(f"ARM already en_progreso for {tag_spool}, Ocupado_Por should prevent this")
        raise OccupationError(f"Spool {tag_spool} already occupied")
    else:
        logger.error(f"Cannot initiate ARM from state {current_arm_state}")
        raise InvalidStateTransitionError(f"Cannot TOMAR ARM from state {current_arm_state}")
```

---

### ❌ MISSING: Transition Guards

**Issue:** The plan does not include **guard conditions** for pausar and reanudar transitions.

**Why Guards Are Needed:**

1. **pausar should only work from en_progreso:**
   - Prevent pausar from pendiente (nothing to pause)
   - Prevent pausar from pausado (already paused)
   - Prevent pausar from completado (already done)

2. **reanudar should only work from pausado:**
   - Prevent reanudar from pendiente (nothing to resume)
   - Prevent reanudar from en_progreso (already in progress)
   - Prevent reanudar from completado (already done)

**Proposed Solution:**

Add guard methods to ARMStateMachine:

```python
class ARMStateMachine(BaseOperationStateMachine):
    # ...existing code...

    # Update transitions with guards
    pausar = en_progreso.to(pausado, cond="is_en_progreso")
    reanudar = pausado.to(en_progreso, cond="is_pausado")

    def is_en_progreso(self) -> bool:
        """Guard: Only allow pausar from en_progreso state."""
        return self.current_state.id == "en_progreso"

    def is_pausado(self) -> bool:
        """Guard: Only allow reanudar from pausado state."""
        return self.current_state.id == "pausado"
```

**Wait, this is wrong!** The guard condition is checking `self.current_state.id`, but the state machine already knows the source state from the transition definition. Guards are for **external conditions**, not state validation.

**Revised Understanding:**
- python-statemachine already validates source state via transition definition (`en_progreso.to(pausado)`)
- If transition is invalid, it raises `TransitionNotAllowed` exception
- **No additional guards needed** - the transition definitions are sufficient

**However**, the plan should explicitly state that invalid transitions will raise exceptions and show how StateService handles these exceptions.

---

## 3. Display Clarity

### ✅ STRENGTH: Clear Display Format

The proposed Estado_Detalle format is **clear and consistent**:
- "Disponible - ARM pausado, SOLD pendiente"
- Uses existing pattern
- Spanish terminology is appropriate
- Fits on tablet screens

**No changes needed in this area.**

---

## 4. Testing

### ⚠️ INCOMPLETE: Missing Test Cases

The plan includes good test coverage, but **misses several critical edge cases**:

#### Missing Test Case 1: Concurrent PAUSAR
```python
def test_concurrent_pausar_same_spool():
    """
    Only one worker should be able to PAUSAR a spool at a time.

    Given: Spool occupied by Worker A
    When: Worker A and Worker B both call PAUSAR simultaneously
    Then: Only Worker A succeeds (lock ownership verified)
    And: Worker B gets NoAutorizadoError
    """
```

#### Missing Test Case 2: PAUSAR with Expired Lock
```python
def test_pausar_with_expired_lock():
    """
    Cannot PAUSAR if lock has expired (TTL reached).

    Given: Spool occupied by Worker A, but lock TTL expired
    When: Worker A calls PAUSAR
    Then: LockExpiredError raised
    And: Estado_Detalle not updated
    And: Metadata event not logged
    """
```

#### Missing Test Case 3: Double PAUSAR
```python
def test_pausar_twice_fails():
    """
    Cannot PAUSAR a spool that is already paused.

    Given: Spool already in pausado state
    When: Worker calls PAUSAR again
    Then: TransitionNotAllowed exception (or graceful error)
    And: Estado_Detalle unchanged
    """
```

#### Missing Test Case 4: COMPLETAR from pausado
```python
def test_completar_from_pausado_requires_tomar_first():
    """
    Cannot COMPLETAR work that is paused without resuming first.

    Given: Spool in pausado state
    When: Worker calls COMPLETAR
    Then: Should fail with error (no occupation lock)
    """
```

#### Missing Test Case 5: Hydration from Sheets State
```python
def test_hydrate_arm_machine_detects_pausado_state():
    """
    Hydration should correctly detect pausado state from Sheets.

    Given: Sheets row with:
      - Armador = "MR(93)"
      - Fecha_Armado = null
      - Ocupado_Por = null (if using Option A from critique)
    When: StateService hydrates ARM state machine
    Then: Current state should be "pausado"
    """
```

**NOTE:** This test depends on which hydration approach is chosen (Option A vs Option B from Section 1).

---

### ⚠️ CONCERN: Test Data Setup Complexity

**Issue:** Integration tests require complex Sheets setup:
- Create test spools with specific state combinations
- Trigger TOMAR → PAUSAR → TOMAR workflows
- Verify Sheets columns AND Estado_Detalle AND Metadata events

**Recommendation:** Use test fixtures to create reusable spool setups:
```python
@pytest.fixture
def spool_arm_en_progreso(sheets_repo, redis_client):
    """Create test spool with ARM en_progreso, occupied by MR(93)."""
    # Setup logic...
    yield spool
    # Cleanup logic...
```

---

## 5. Migration

### ❌ CRITICAL ISSUE: Migration Strategy Is Incorrect

**Issue:** Section 5.1 claims "Option A (No Migration)" is acceptable and that existing paused spools will "self-heal on next operation". **This is false.**

**Why Self-Healing Won't Work:**

**Scenario:** Existing paused spool in production
- Armador = "MR(93)"
- Fecha_Armado = null
- Ocupado_Por = null (cleared by previous PAUSAR)

**With Option A (No Migration) + Current Hydration:**
1. StateService.tomar() is called by Worker JP(94)
2. Hydration reads spool and sees: Armador exists, Fecha_Armado null
3. Hydration sets state to "en_progreso" (current logic, not pausado)
4. TOMAR calls `arm_machine.iniciar()` (not reanudar)
5. `on_enter_en_progreso` callback **overwrites Armador** from "MR(93)" to "JP(94)"
6. **DATA LOSS:** Original worker MR(93) is lost!

**If Using Updated Hydration from Section 5.2:**
1. Hydration checks Ocupado_Por is null → sets state to "pausado"
2. TOMAR calls `arm_machine.reanudar()` (correct)
3. `on_enter_en_progreso` callback does NOT update Armador (correct)
4. **Works correctly** - original worker preserved

**Conclusion:**
- If using **Option B from Section 1 critique** (simple hydration), **Option A migration is BROKEN**
- If using **updated hydration from Section 5.2** (Ocupado_Por-based), **Option A migration works**

**This creates a contradiction:**
- Section 1 critique recommends **NOT** updating hydration (to avoid coupling)
- Section 5.2 recommends **updating** hydration (to handle migration)
- These are **incompatible**

**Proposed Resolution:**

**Choose ONE approach:**

**Approach 1: Simple Hydration + Manual Migration (SAFEST)**
- Do NOT update hydration logic (keep it simple)
- Run one-time migration script to transition existing paused spools
- Script logic:
  ```python
  for spool in all_spools:
      if spool.armador and not spool.fecha_armado and not spool.ocupado_por:
          # This spool is paused
          # Manually set state to pausado (how? need Estado_ARM column)
  ```
- **Problem:** Can't set state without a column to store it
- **Conclusion:** This approach requires Estado_ARM/Estado_SOLD columns

**Approach 2: Updated Hydration + No Migration (PRAGMATIC)**
- Accept the coupling in hydration logic (use Ocupado_Por to detect pausado)
- No migration script needed
- Existing paused spools automatically detected as pausado on next hydration
- **Tradeoff:** Tight coupling, but simpler deployment

**Approach 3: Add Estado_ARM/Estado_SOLD Columns (CLEANEST)**
- Add 2 new columns: Estado_ARM (col 68), Estado_SOLD (col 69)
- State machine callbacks update these columns explicitly
- Hydration reads from these columns (deterministic, no coupling)
- Migration script sets Estado_ARM/Estado_SOLD for existing spools based on current state
- **Tradeoff:** Schema change, requires Google Sheets update, migration script

**Recommendation: Approach 2** (Updated Hydration + No Migration)
- Pragmatic choice for v3.0 time constraints
- Accept coupling as technical debt
- Document for future refactoring in v4.0

---

## 6. Consistency

### ⚠️ INCONSISTENCY: Error Handling in StateService.pausar()

**Issue:** Section 3.3 shows StateService.pausar() logging a **warning** when pausar is called from wrong state:

```python
if current_arm_state == "en_progreso":
    await arm_machine.pausar()
else:
    logger.warning(f"Cannot pause ARM - current state is {current_arm_state}, expected en_progreso")
```

**Problem:** This logs a warning but **continues execution**, calling OccupationService.pausar() anyway.

**Expected Behavior:**
- If ARM state is NOT "en_progreso", **PAUSAR should fail**
- Should raise an exception (e.g., InvalidStateTransitionError)
- Should NOT call OccupationService.pausar()
- Should NOT update Estado_Detalle

**Comparison with TOMAR/COMPLETAR:**
- TOMAR raises DependenciasNoSatisfechasError if dependencies not met
- COMPLETAR would fail if state machine transition fails
- PAUSAR should follow the same pattern

**Proposed Fix:**
```python
if operacion == ActionType.ARM:
    current_arm_state = arm_machine.get_state_id()

    if current_arm_state != "en_progreso":
        raise InvalidStateTransitionError(
            f"Cannot PAUSAR ARM from state {current_arm_state}. "
            f"PAUSAR is only allowed from en_progreso state."
        )

    await arm_machine.pausar()
    logger.info(f"ARM state machine transitioned to {arm_machine.get_state_id()}")
```

**Same fix needed for SOLD operation.**

---

## 7. Additional Concerns

### ⚠️ CONCERN: Redundant State Validation

**Issue:** StateService.pausar() validates current state before calling pausar transition:

```python
if current_arm_state == "en_progreso":
    await arm_machine.pausar()
```

**But** python-statemachine already validates this via transition definition:
```python
pausar = en_progreso.to(pausado)
```

If state is not en_progreso, calling `pausar()` will raise `TransitionNotAllowed` exception.

**Question:** Is the explicit validation redundant?

**Answer:** YES, but it's **defensive programming** and provides better error messages.

**Recommendation:** Keep the explicit validation for better error handling, but add a comment explaining this is defensive:

```python
# Defensive validation - state machine will also validate, but this provides clearer error
if current_arm_state != "en_progreso":
    raise InvalidStateTransitionError(...)
```

---

### ❌ MISSING: InvalidStateTransitionError Definition

**Issue:** The plan references `InvalidStateTransitionError` but this exception is not defined in the codebase.

**Check:** Does this exception exist?

**If not**, need to define it:
```python
# backend/exceptions.py

class InvalidStateTransitionError(Exception):
    """Raised when attempting an invalid state machine transition."""

    def __init__(self, message: str, tag_spool: str = None, current_state: str = None, attempted_transition: str = None):
        self.tag_spool = tag_spool
        self.current_state = current_state
        self.attempted_transition = attempted_transition
        super().__init__(message)
```

---

### ⚠️ CONCERN: Logging Clarity

**Issue:** The plan shows logging like:
```python
logger.info(f"ARM state machine transitioned to {arm_machine.get_state_id()}")
```

**Problem:** Doesn't show the transition that occurred (from → to).

**Better:**
```python
logger.info(f"ARM state machine: {current_arm_state} → pausado for {tag_spool}")
```

---

## 8. Open Questions Analysis

### Question 1: Should reanudar update Armador/Soldador?

**Plan's Answer:** Preserve (do not update)

**Critique:** **CORRECT DECISION**

**Justification:**
- Original worker should get credit for initiating the work
- Manufacturing floor needs to track who started each operation (regulatory requirement)
- If new worker resumes, they are just continuing existing work

**However**, there's a **data gap**: We don't track who resumed the work.

**Recommendation:** Consider adding columns:
- `Armador_Resumido_Por` (who resumed ARM work)
- `Soldador_Resumido_Por` (who resumed SOLD work)

**For v3.0:** Accept the data gap, log in Metadata instead.

---

### Question 2: Should we allow completar from pausado without resuming?

**Plan's Answer:** NO (require TOMAR before COMPLETAR)

**Critique:** **CORRECT DECISION**

**Justification:**
- Enforces occupation lock (prevents unauthorized completion)
- Maintains workflow consistency
- Prevents race conditions (two workers trying to complete same spool)

**No changes needed.**

---

### Question 3: Should we allow cancelar from pausado?

**Plan's Answer:** YES (allow pausado → pendiente)

**Critique:** **NEEDS DISCUSSION**

**Issue:** The plan doesn't define the `cancelar` transition from pausado state.

**Current Transitions:**
```python
cancelar = en_progreso.to(pendiente)
```

**If we want to allow cancelar from pausado:**
```python
cancelar = en_progreso.to(pendiente) | pausado.to(pendiente)
```

**Question:** Should cancelar from pausado:
- Clear Armador/Soldador columns (revert to unassigned)?
- Or preserve Armador/Soldador (mark as cancelled but keep history)?

**Recommendation:**
- YES, allow `pausado → pendiente` transition
- Clear Armador/Soldador columns (same behavior as cancelar from en_progreso)
- Add this to the implementation plan

---

## 9. Summary of Issues

### Critical (Must Fix Before Implementation)

1. **Resolve hydration logic coupling contradiction** (Section 1)
   - Choose: Simple hydration + migration script OR Updated hydration with coupling
   - Recommendation: Updated hydration (Approach 2)

2. **Complete on_enter_en_progreso callback** (Section 2)
   - Detect source state (pausado vs pendiente)
   - Only update Armador/Soldador on initial start

3. **Fix error handling in StateService.pausar()** (Section 6)
   - Raise exception instead of logging warning when state is wrong

4. **Fix migration strategy** (Section 5)
   - Acknowledge coupling in hydration logic
   - Or implement migration script + Estado_ARM/SOLD columns

### Important (Should Fix)

5. **Complete StateService.tomar() implementation** (Section 2)
   - Show full code with all state branches

6. **Add missing test cases** (Section 4)
   - Concurrent PAUSAR, expired lock, double PAUSAR, hydration

7. **Define cancelar from pausado transition** (Section 8)
   - Update state machine definitions

8. **Define InvalidStateTransitionError** (Section 7)
   - Add to exceptions.py if not exists

### Minor (Nice to Have)

9. **Improve logging clarity** (Section 7)
   - Show from → to transitions in logs

10. **Add test fixtures** (Section 4)
    - Simplify integration test setup

---

## 10. Revised Risk Assessment

### Critical Risks (Added)

1. **Hydration Coupling:**
   - If hydration logic is updated but OccupationService has a bug, all estado calculations will be wrong
   - Mitigation: Extensive integration tests, consider Estado_ARM/SOLD columns in v4.0

2. **Data Loss on Resume:**
   - If on_enter_en_progreso callback is not updated, original Armador will be overwritten
   - Mitigation: MUST implement source state detection

3. **Migration Data Corruption:**
   - If migration approach is wrong, existing paused spools will lose Armador data
   - Mitigation: Choose Approach 2 (updated hydration) to avoid migration script

---

## Final Recommendation

**Overall Assessment:** The plan is **sound in principle** but has **critical gaps** that must be addressed.

**Required Changes Before Implementation:**
1. Resolve hydration logic approach (choose Approach 2)
2. Complete on_enter_en_progreso callback with source state detection
3. Fix StateService.pausar() error handling (raise exceptions)
4. Add missing test cases
5. Define cancelar from pausado transition
6. Update migration strategy to acknowledge coupling

**Estimated Additional Effort:** +2 hours (total: 8 hours)

**Proceed to Phase 3:** Convert these critiques to actionable feedback items.

---

**Critique Complete**
