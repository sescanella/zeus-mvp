# Bug 1: Estado_Detalle Display Fix - Implementation Plan v1.0

**Date:** 2026-01-30
**Bug:** Estado_Detalle shows "Disponible - ARM pendiente, SOLD pendiente" instead of "ARM_PAUSADO" after PAUSAR ARM operation
**Root Cause:** ARM state machine has no `pausado` state; EstadoDetalleBuilder cannot detect paused scenario

---

## 1. Approach Selection

### Decision: **State Machine Approach (RECOMMENDED)**

**Rationale:**

1. **Architectural Consistency:** ZEUES v3.0 uses hierarchical state machines as the core architectural pattern. PAUSAR should be a first-class state transition, not just an occupation operation.

2. **Explicit Semantics:** Adding a `pausado` state makes the system behavior transparent and easier to reason about. The state machine clearly shows: pendiente → en_progreso → pausado → en_progreso → completado.

3. **Future-Proof:** Supports additional transitions if needed (e.g., pausado → cancelar, pausado → completado for edge cases).

4. **Easier Testing:** State machine transitions are easier to unit test than heuristics that rely on multiple column checks.

5. **Symmetry:** Works identically for both ARM and SOLD operations, maintaining architectural symmetry.

6. **Consistency with TOMAR/COMPLETAR:** TOMAR and COMPLETAR trigger state machine transitions. PAUSAR should follow the same pattern.

**Tradeoffs:**
- Requires more code changes (ARM + SOLD state machines, StateService pausar/tomar logic)
- Requires understanding of python-statemachine 2.5.0 library

**Alternative Considered:**
- **Heuristic Approach:** Detect paused via EstadoDetalleBuilder by checking (Armador exists + Ocupado_Por is None + ARM state = "en_progreso")
- **Rejected Because:** Less architecturally pure, relies on fragile heuristics, doesn't align with state machine design pattern

---

## 2. Estado_Detalle Display Format

### Format Design

**After PAUSAR ARM:**
```
"Disponible - ARM pausado, SOLD pendiente"
```

**After PAUSAR SOLD (ARM completed):**
```
"Disponible - ARM completado, SOLD pausado"
```

**After PAUSAR both (edge case - ARM paused, then complete, then SOLD paused):**
```
"Disponible - ARM completado, SOLD pausado"
```

**Rationale:**
- Uses existing "Disponible - ARM X, SOLD Y" format pattern for consistency
- "pausado" is clear and human-readable for manufacturing floor workers
- Matches Spanish terminology used in existing states (pendiente, en progreso, completado)
- Fits on tablet screens without truncation

---

## 3. Implementation Details

### 3.1 ARM State Machine Changes

**File:** `/Users/sescanella/Proyectos/KM/ZEUES-by-KM/backend/services/state_machines/arm_state_machine.py`

**Lines 34-42: Add pausado state and transitions**

**BEFORE:**
```python
# Define states
pendiente = State("pendiente", initial=True)
en_progreso = State("en_progreso")
completado = State("completado", final=True)

# Define transitions
iniciar = pendiente.to(en_progreso)
completar = en_progreso.to(completado)
cancelar = en_progreso.to(pendiente)
```

**AFTER:**
```python
# Define states
pendiente = State("pendiente", initial=True)
en_progreso = State("en_progreso")
pausado = State("pausado")  # NEW: Intermediate paused state
completado = State("completado", final=True)

# Define transitions
iniciar = pendiente.to(en_progreso)
pausar = en_progreso.to(pausado)  # NEW: Pause work
reanudar = pausado.to(en_progreso)  # NEW: Resume work
completar = en_progreso.to(completado)
cancelar = en_progreso.to(pendiente)
```

**Lines 113-140: Add on_enter_pausado callback**

**NEW CODE:**
```python
async def on_enter_pausado(self, **kwargs):
    """
    Callback when ARM work is paused.

    Does NOT modify Armador column (worker ownership persists).
    Occupation columns (Ocupado_Por, Fecha_Ocupacion) are cleared by OccupationService.

    This callback is intentionally empty because:
    - Armador column should remain set (worker who initiated ARM is preserved)
    - Ocupado_Por is cleared by OccupationService.pausar() (not by state machine)
    - Estado_Detalle is updated by StateService after this transition

    Args:
        **kwargs: Event arguments (ignored)
    """
    # No Sheets update needed - OccupationService handles occupation clearing
    # Armador persists to track who initiated ARM before pause
    pass
```

**Rationale:**
- Empty callback is intentional - we don't want to modify Armador (preserves worker ownership)
- OccupationService clears Ocupado_Por, not the state machine
- Follows separation of concerns: state machine manages state, occupation service manages locks

---

### 3.2 SOLD State Machine Changes

**File:** `/Users/sescanella/Proyectos/KM/ZEUES-by-KM/backend/services/state_machines/sold_state_machine.py`

**Lines 37-45: Add pausado state and transitions**

**BEFORE:**
```python
# Define states
pendiente = State("pendiente", initial=True)
en_progreso = State("en_progreso")
completado = State("completado", final=True)

# Define transitions
iniciar = pendiente.to(en_progreso)
completar = en_progreso.to(completado)
cancelar = en_progreso.to(pendiente)
```

**AFTER:**
```python
# Define states
pendiente = State("pendiente", initial=True)
en_progreso = State("en_progreso")
pausado = State("pausado")  # NEW: Intermediate paused state
completado = State("completado", final=True)

# Define transitions
iniciar = pendiente.to(en_progreso)
pausar = en_progreso.to(pausado)  # NEW: Pause work
reanudar = pausado.to(en_progreso)  # NEW: Resume work
completar = en_progreso.to(completado)
cancelar = en_progreso.to(pendiente)
```

**Lines 161-187: Add on_enter_pausado callback**

**NEW CODE:**
```python
async def on_enter_pausado(self, **kwargs):
    """
    Callback when SOLD work is paused.

    Does NOT modify Soldador column (worker ownership persists).
    Occupation columns (Ocupado_Por, Fecha_Ocupacion) are cleared by OccupationService.

    This callback is intentionally empty because:
    - Soldador column should remain set (worker who initiated SOLD is preserved)
    - Ocupado_Por is cleared by OccupationService.pausar() (not by state machine)
    - Estado_Detalle is updated by StateService after this transition

    Args:
        **kwargs: Event arguments (ignored)
    """
    # No Sheets update needed - OccupationService handles occupation clearing
    # Soldador persists to track who initiated SOLD before pause
    pass
```

---

### 3.3 StateService.pausar() Changes

**File:** `/Users/sescanella/Proyectos/KM/ZEUES-by-KM/backend/services/state_service.py`

**Lines 140-186: Trigger pausar transition BEFORE clearing occupation**

**BEFORE:**
```python
async def pausar(self, request: PausarRequest) -> OccupationResponse:
    """PAUSAR operation with state machine coordination."""
    tag_spool = request.tag_spool

    logger.info(f"StateService.pausar: {tag_spool} by {request.worker_nombre}")

    # Delegate to OccupationService
    response = await self.occupation_service.pausar(request)

    # Fetch current spool state
    spool = self.sheets_repo.get_spool_by_tag(tag_spool)
    if spool:
        # Hydrate state machines to get current states
        arm_machine = self._hydrate_arm_machine(spool)
        sold_machine = self._hydrate_sold_machine(spool)

        # Activate initial state for async context
        await arm_machine.activate_initial_state()
        await sold_machine.activate_initial_state()

        # Update Estado_Detalle with "Disponible - ARM X, SOLD Y" format
        self._update_estado_detalle(
            tag_spool=tag_spool,
            ocupado_por=None,  # Clear occupation
            arm_state=arm_machine.get_state_id(),
            sold_state=sold_machine.get_state_id()
        )

    logger.info(f"✅ StateService.pausar completed for {tag_spool}")
    return response
```

**AFTER:**
```python
async def pausar(self, request: PausarRequest) -> OccupationResponse:
    """
    PAUSAR operation with state machine coordination.

    Flow:
    1. Fetch spool and hydrate state machines
    2. Trigger pausar transition on state machine (en_progreso → pausado)
    3. Delegate to OccupationService (verify lock + release occupation)
    4. Update Estado_Detalle with pausado state

    Args:
        request: PAUSAR request with tag_spool, worker_id, worker_nombre, operacion

    Returns:
        OccupationResponse with success status and message

    Raises:
        NoAutorizadoError: If worker doesn't own the lock
        LockExpiredError: If lock no longer exists
    """
    tag_spool = request.tag_spool
    operacion = request.operacion  # NEW: Get operation type

    logger.info(f"StateService.pausar: {tag_spool} {operacion} by {request.worker_nombre}")

    # CHANGE: Fetch spool and hydrate BEFORE calling OccupationService
    spool = self.sheets_repo.get_spool_by_tag(tag_spool)
    if not spool:
        raise SpoolNoEncontradoError(tag_spool)

    arm_machine = self._hydrate_arm_machine(spool)
    sold_machine = self._hydrate_sold_machine(spool)

    # Activate initial state for async context
    await arm_machine.activate_initial_state()
    await sold_machine.activate_initial_state()

    # NEW: Trigger pausar transition BEFORE clearing occupation
    # This ensures state machine is in "pausado" state when EstadoDetalleBuilder reads it
    if operacion == ActionType.ARM:
        current_arm_state = arm_machine.get_state_id()
        if current_arm_state == "en_progreso":
            await arm_machine.pausar()
            logger.info(f"ARM state machine transitioned to {arm_machine.get_state_id()}")
        else:
            logger.warning(f"Cannot pause ARM - current state is {current_arm_state}, expected en_progreso")
    elif operacion == ActionType.SOLD:
        current_sold_state = sold_machine.get_state_id()
        if current_sold_state == "en_progreso":
            await sold_machine.pausar()
            logger.info(f"SOLD state machine transitioned to {sold_machine.get_state_id()}")
        else:
            logger.warning(f"Cannot pause SOLD - current state is {current_sold_state}, expected en_progreso")

    # Delegate to OccupationService (clears Ocupado_Por, releases lock)
    response = await self.occupation_service.pausar(request)

    # Update Estado_Detalle with pausado state
    self._update_estado_detalle(
        tag_spool=tag_spool,
        ocupado_por=None,  # Occupation cleared
        arm_state=arm_machine.get_state_id(),  # Now "pausado" for ARM operation
        sold_state=sold_machine.get_state_id()  # Now "pausado" for SOLD operation
    )

    logger.info(f"✅ StateService.pausar completed for {tag_spool}")
    return response
```

**Key Changes:**
1. Fetch spool and hydrate state machines BEFORE calling OccupationService
2. Trigger `arm_machine.pausar()` or `sold_machine.pausar()` based on operation
3. State machine is now in "pausado" state when EstadoDetalleBuilder reads it
4. Added state validation (only pause if current state is "en_progreso")

---

### 3.4 StateService.tomar() Changes

**File:** `/Users/sescanella/Proyectos/KM/ZEUES-by-KM/backend/services/state_service.py`

**Lines 67-138: Detect pausado state and trigger reanudar (not iniciar)**

**BEFORE:**
```python
# Trigger state machine transition (iniciar)
if operacion == ActionType.ARM:
    await arm_machine.iniciar(
        worker_nombre=request.worker_nombre,
        fecha_operacion=date.today()
    )
```

**AFTER:**
```python
# Trigger state machine transition (iniciar or reanudar)
if operacion == ActionType.ARM:
    current_arm_state = arm_machine.get_state_id()

    if current_arm_state == "pausado":
        # Resume paused work
        await arm_machine.reanudar(worker_nombre=request.worker_nombre)
        logger.info(f"ARM state machine resumed from pausado to {arm_machine.get_state_id()}")
    elif current_arm_state == "pendiente":
        # Start new work
        await arm_machine.iniciar(
            worker_nombre=request.worker_nombre,
            fecha_operacion=date.today()
        )
        logger.info(f"ARM state machine transitioned to {arm_machine.get_state_id()}")
    else:
        logger.warning(f"Cannot initiate ARM - current state is {current_arm_state}")
```

**Similar change for SOLD operation**

**Rationale:**
- TOMAR after PAUSAR should resume work (reanudar), not restart (iniciar)
- Preserves existing Armador/Soldador columns when resuming
- Prevents overwriting worker name if different worker resumes

**NOTE:** We need to decide if `reanudar` should update Armador/Soldador or leave it unchanged.

**Recommendation:** `on_enter_en_progreso` callback should check if coming from `pausado` state. If yes, do NOT update Armador/Soldador (preserve original worker). If coming from `pendiente`, update normally.

---

### 3.5 EstadoDetalleBuilder Changes

**File:** `/Users/sescanella/Proyectos/KM/ZEUES-by-KM/backend/services/estado_detalle_builder.py`

**Lines 77-92: Add pausado state mapping**

**BEFORE:**
```python
def _state_to_display(self, state: str) -> str:
    """
    Convert state ID to Spanish display term.

    Args:
        state: State ID (pendiente/en_progreso/completado)

    Returns:
        Spanish display term
    """
    mapping = {
        "pendiente": "pendiente",
        "en_progreso": "en progreso",
        "completado": "completado"
    }
    return mapping.get(state, state)
```

**AFTER:**
```python
def _state_to_display(self, state: str) -> str:
    """
    Convert state ID to Spanish display term.

    Args:
        state: State ID (pendiente/en_progreso/pausado/completado)

    Returns:
        Spanish display term
    """
    mapping = {
        "pendiente": "pendiente",
        "en_progreso": "en progreso",
        "pausado": "pausado",  # NEW: Paused state
        "completado": "completado"
    }
    return mapping.get(state, state)
```

**Rationale:**
- Simple mapping addition to recognize new state
- No heuristics needed - state machine provides explicit state

---

## 4. Testing Strategy

### 4.1 Unit Tests for State Machines

**File:** `tests/unit/test_arm_state_machine.py` (NEW)

**Test Cases:**

1. **test_pausar_transition_from_en_progreso_to_pausado**
   ```python
   """
   ARM state machine should transition from en_progreso to pausado.

   Given: ARM state machine in en_progreso state
   When: pausar() transition is triggered
   Then: Current state should be "pausado"
   And: Armador column should remain unchanged
   """
   ```

2. **test_reanudar_transition_from_pausado_to_en_progreso**
   ```python
   """
   ARM state machine should transition from pausado back to en_progreso.

   Given: ARM state machine in pausado state
   When: reanudar() transition is triggered
   Then: Current state should be "en_progreso"
   And: Armador column should remain unchanged
   """
   ```

3. **test_pausar_from_pendiente_should_fail**
   ```python
   """
   Cannot pause work that hasn't started.

   Given: ARM state machine in pendiente state
   When: pausar() transition is attempted
   Then: TransitionNotAllowed exception should be raised
   """
   ```

4. **test_reanudar_from_pendiente_should_fail**
   ```python
   """
   Cannot resume work that was never started.

   Given: ARM state machine in pendiente state
   When: reanudar() transition is attempted
   Then: TransitionNotAllowed exception should be raised
   """
   ```

**File:** `tests/unit/test_sold_state_machine.py` (NEW)

**Test Cases:** Same as ARM (test_pausar_transition, test_reanudar_transition, etc.)

---

### 4.2 Unit Tests for EstadoDetalleBuilder

**File:** `tests/unit/test_estado_detalle_builder.py` (EXISTING - add new tests)

**Test Cases:**

1. **test_build_pausado_arm_pendiente_sold**
   ```python
   """
   Estado_Detalle for paused ARM should show "pausado".

   Given: ocupado_por=None, arm_state="pausado", sold_state="pendiente"
   When: build() is called
   Then: Result should be "Disponible - ARM pausado, SOLD pendiente"
   """
   ```

2. **test_build_completado_arm_pausado_sold**
   ```python
   """
   Estado_Detalle for paused SOLD should show "pausado".

   Given: ocupado_por=None, arm_state="completado", sold_state="pausado"
   When: build() is called
   Then: Result should be "Disponible - ARM completado, SOLD pausado"
   """
   ```

---

### 4.3 Integration Tests

**File:** `tests/integration/test_occupation_flow.py` (EXISTING - add new tests)

**Critical Test Cases:**

1. **test_pausar_arm_updates_estado_detalle_to_pausado**
   ```python
   """
   PAUSAR ARM should update Estado_Detalle to show paused state.

   Given: Spool TEST-02 with ARM en_progreso, occupied by MR(93)
   When: Worker 93 calls PAUSAR for ARM operation
   Then:
     - Armador remains "MR(93)"
     - Ocupado_Por cleared to ""
     - ARM state machine in "pausado" state
     - Estado_Detalle = "Disponible - ARM pausado, SOLD pendiente"
     - Metadata event logged with tipo=PAUSAR_SPOOL
   """
   ```

2. **test_pausar_sold_updates_estado_detalle_to_pausado**
   ```python
   """
   PAUSAR SOLD should update Estado_Detalle to show paused state.

   Given: Spool TEST-02 with ARM completado, SOLD en_progreso, occupied by JP(94)
   When: Worker 94 calls PAUSAR for SOLD operation
   Then:
     - Soldador remains "JP(94)"
     - Ocupado_Por cleared to ""
     - SOLD state machine in "pausado" state
     - Estado_Detalle = "Disponible - ARM completado, SOLD pausado"
     - Metadata event logged
   """
   ```

3. **test_tomar_after_pausar_resumes_work**
   ```python
   """
   TOMAR after PAUSAR should resume work, not restart.

   Flow:
     1. TOMAR ARM by MR(93) → Estado_Detalle: "MR(93) trabajando ARM (ARM en progreso, SOLD pendiente)"
     2. PAUSAR ARM → Estado_Detalle: "Disponible - ARM pausado, SOLD pendiente"
     3. TOMAR ARM by JP(94) → Estado_Detalle: "JP(94) trabajando ARM (ARM en progreso, SOLD pendiente)"

   Expected:
     - ARM state transitions: pendiente → en_progreso → pausado → en_progreso
     - Armador remains "MR(93)" (original worker preserved)
     - Ocupado_Por changes from "MR(93)" to "" to "JP(94)"
   """
   ```

4. **test_pausar_from_pendiente_state_fails_gracefully**
   ```python
   """
   Cannot pause work that hasn't started.

   Given: Spool TEST-03 with ARM pendiente (no Armador)
   When: Attempt to PAUSAR ARM
   Then: Should return error (cannot pause non-started work)
   """
   ```

5. **test_pausar_metadata_logging**
   ```python
   """
   PAUSAR must log PAUSAR_SPOOL event to Metadata sheet.

   Given: Spool TEST-02 occupied by Worker 93
   When: Worker 93 calls PAUSAR
   Then:
     - Metadata sheet contains new row
     - evento_tipo = "PAUSAR_SPOOL"
     - operacion = "ARM"
     - accion = "PAUSAR"
     - worker_id = 93
     - worker_nombre = "MR(93)"
   """
   ```

---

### 4.4 Edge Case Tests

1. **test_completar_from_pausado_state**
   ```python
   """
   Can worker complete work directly from pausado state?

   Options:
   A. Require TOMAR (resume) before COMPLETAR → Safer, enforces workflow
   B. Allow direct pausado → completado transition → Convenient, but bypasses occupation lock

   Recommendation: Option A (require TOMAR before COMPLETAR)
   """
   ```

2. **test_cancelar_from_pausado_state**
   ```python
   """
   Can worker cancel work from pausado state?

   Recommendation: YES - Allow pausado → pendiente (cancelar) transition
   This handles cases where worker decides not to continue paused work.
   """
   ```

---

## 5. Migration Considerations

### 5.1 Existing Paused Spools in Production

**Scenario:** Spools currently in "paused" state (Armador exists, Ocupado_Por cleared) will be hydrated as "en_progreso" before the fix is deployed.

**After Fix Deployed:**
- Hydration logic reads current Sheets state
- If Armador exists and Fecha_Armado is null → state = "en_progreso"
- BUT we want these to be "pausado"

**Solution Options:**

**Option A: No Migration (Acceptable)**
- Paused spools show "en_progreso" until next PAUSAR/TOMAR operation
- Estado_Detalle shows "Disponible - ARM en progreso, SOLD pendiente" temporarily
- Next TOMAR will trigger `iniciar` (not `reanudar`) because state is "en_progreso"
- Impact: Minor - only affects spools currently paused at deployment time
- Recommendation: **ACCEPTABLE** - temporary inconsistency, self-heals on next operation

**Option B: One-Time Migration Script (Overkill)**
- Scan all spools for paused state (Armador exists, Ocupado_Por cleared, Fecha_Armado null)
- Manually trigger `pausar` transition for each
- Complexity: HIGH
- Risk: Could break spools if detection logic is wrong
- Recommendation: **NOT NEEDED** for this fix

**Chosen Approach: Option A (No Migration)**

---

### 5.2 Hydration Logic Update (IMPORTANT)

**File:** `/Users/sescanella/Proyectos/KM/ZEUES-by-KM/backend/services/state_service.py`

**Lines 279-313: Update _hydrate_arm_machine() to detect pausado state**

**BEFORE:**
```python
def _hydrate_arm_machine(self, spool) -> ARMStateMachine:
    """Hydrate ARM state machine from spool data."""
    arm_machine = ARMStateMachine(
        tag_spool=spool.tag_spool,
        sheets_repo=self.sheets_repo,
        metadata_repo=self.metadata_repo
    )

    # Set current state based on spool data
    if spool.fecha_armado:
        arm_machine.current_state = arm_machine.completado
    elif spool.armador:
        arm_machine.current_state = arm_machine.en_progreso
    else:
        # ARM is pending (initial state)
        pass

    return arm_machine
```

**AFTER:**
```python
def _hydrate_arm_machine(self, spool) -> ARMStateMachine:
    """
    Hydrate ARM state machine from spool data.

    State detection logic:
    - completado: Fecha_Armado exists
    - pausado: Armador exists, Fecha_Armado null, Ocupado_Por null
    - en_progreso: Armador exists, Fecha_Armado null, Ocupado_Por exists
    - pendiente: Armador null (initial state)
    """
    arm_machine = ARMStateMachine(
        tag_spool=spool.tag_spool,
        sheets_repo=self.sheets_repo,
        metadata_repo=self.metadata_repo
    )

    # Set current state based on spool data
    if spool.fecha_armado:
        # ARM completed
        arm_machine.current_state = arm_machine.completado
    elif spool.armador:
        # ARM initiated - check if paused or in progress
        if spool.ocupado_por is None or spool.ocupado_por == "":
            # Paused: Worker assigned but no current occupation
            arm_machine.current_state = arm_machine.pausado
        else:
            # In progress: Worker assigned and occupied
            arm_machine.current_state = arm_machine.en_progreso
    else:
        # ARM is pending (initial state)
        pass

    return arm_machine
```

**Similar change for _hydrate_sold_machine()**

**Rationale:**
- Hydration logic now detects pausado state from Sheets data
- This handles existing paused spools in production (Option A migration)
- Estado_Detalle will correctly show "pausado" immediately after deployment

**CRITICAL:** This change means hydration logic now depends on `Ocupado_Por` column, which creates a coupling between occupation state and state machine state. This is a necessary tradeoff to handle existing paused spools.

---

## 6. Implementation Checklist

- [ ] **ARM State Machine:**
  - [ ] Add `pausado` state definition
  - [ ] Add `pausar` transition (en_progreso → pausado)
  - [ ] Add `reanudar` transition (pausado → en_progreso)
  - [ ] Add `on_enter_pausado()` callback (empty, documented)
  - [ ] Update `on_enter_en_progreso()` to handle resume vs initial start

- [ ] **SOLD State Machine:**
  - [ ] Add `pausado` state definition
  - [ ] Add `pausar` transition (en_progreso → pausado)
  - [ ] Add `reanudar` transition (pausado → en_progreso)
  - [ ] Add `on_enter_pausado()` callback (empty, documented)
  - [ ] Update `on_enter_en_progreso()` to handle resume vs initial start

- [ ] **StateService:**
  - [ ] Update `pausar()` to fetch spool BEFORE calling OccupationService
  - [ ] Trigger `arm_machine.pausar()` or `sold_machine.pausar()` based on operation
  - [ ] Add state validation (only pause if en_progreso)
  - [ ] Update `tomar()` to detect pausado state and trigger reanudar
  - [ ] Update `_hydrate_arm_machine()` to detect pausado from Ocupado_Por
  - [ ] Update `_hydrate_sold_machine()` to detect pausado from Ocupado_Por

- [ ] **EstadoDetalleBuilder:**
  - [ ] Add "pausado" to `_state_to_display()` mapping

- [ ] **Unit Tests:**
  - [ ] test_pausar_transition_from_en_progreso_to_pausado (ARM)
  - [ ] test_reanudar_transition_from_pausado_to_en_progreso (ARM)
  - [ ] test_pausar_transition_from_en_progreso_to_pausado (SOLD)
  - [ ] test_reanudar_transition_from_pausado_to_en_progreso (SOLD)
  - [ ] test_build_pausado_arm_pendiente_sold (EstadoDetalleBuilder)
  - [ ] test_build_completado_arm_pausado_sold (EstadoDetalleBuilder)

- [ ] **Integration Tests:**
  - [ ] test_pausar_arm_updates_estado_detalle_to_pausado
  - [ ] test_pausar_sold_updates_estado_detalle_to_pausado
  - [ ] test_tomar_after_pausar_resumes_work
  - [ ] test_pausar_metadata_logging

- [ ] **Manual Verification:**
  - [ ] Run backend locally
  - [ ] Execute TOMAR ARM on TEST-02
  - [ ] Verify Estado_Detalle = "MR(93) trabajando ARM (ARM en progreso, SOLD pendiente)"
  - [ ] Execute PAUSAR ARM on TEST-02
  - [ ] Verify Estado_Detalle = "Disponible - ARM pausado, SOLD pendiente"
  - [ ] Verify Metadata event logged
  - [ ] Execute TOMAR ARM again (resume)
  - [ ] Verify Estado_Detalle = "JP(94) trabajando ARM (ARM en progreso, SOLD pendiente)"
  - [ ] Verify Armador still shows "MR(93)" (original worker preserved)

---

## 7. Risk Assessment

### High Risk Areas

1. **Hydration Logic Coupling:**
   - Hydration now depends on `Ocupado_Por` column to detect pausado state
   - Risk: If OccupationService and StateService get out of sync, hydration could be wrong
   - Mitigation: Add integration tests that validate hydration in all scenarios

2. **TOMAR After PAUSAR Worker Ownership:**
   - Decision needed: Should `reanudar` preserve Armador/Soldador or allow reassignment?
   - Current plan: Preserve original worker (Armador/Soldador unchanged)
   - Risk: If new worker resumes, they don't get credit for the work
   - Mitigation: Document this behavior, add test to validate

3. **State Machine Transition Order:**
   - Must trigger pausar BEFORE OccupationService clears Ocupado_Por
   - Risk: If order is wrong, Estado_Detalle will still be incorrect
   - Mitigation: Integration test validates full flow

### Medium Risk Areas

1. **Existing Tests Breaking:**
   - Adding pausado state could break existing tests that assume only 3 states
   - Mitigation: Run full test suite before and after changes

2. **Edge Cases (completar/cancelar from pausado):**
   - Current plan disallows these transitions
   - Risk: Workers might want to complete/cancel without resuming first
   - Mitigation: Document requirement to TOMAR before COMPLETAR

### Low Risk Areas

1. **EstadoDetalleBuilder Changes:**
   - Simple mapping addition, low risk of breaking

2. **Display Format:**
   - "pausado" is clear Spanish term, already used in investigation report

---

## 8. Success Criteria

### Must Have (Blocking)

- [ ] Estado_Detalle shows "Disponible - ARM pausado, SOLD pendiente" after PAUSAR ARM
- [ ] Estado_Detalle shows "Disponible - ARM completado, SOLD pausado" after PAUSAR SOLD
- [ ] TOMAR after PAUSAR transitions from pausado → en_progreso (not pendiente → en_progreso)
- [ ] All new tests pass
- [ ] All existing tests pass (no regressions)
- [ ] Metadata event still logged correctly for PAUSAR operations

### Should Have (Important)

- [ ] Manual verification on TEST-02 spool confirms fix
- [ ] Armador/Soldador preserved when resuming work
- [ ] Hydration logic correctly detects pausado state for existing paused spools

### Nice to Have (Optional)

- [ ] Documentation updated with pausado state workflows
- [ ] Frontend updated to handle pausado state in UI (future work)

---

## 9. Timeline Estimate

**Complexity:** Medium

**Estimated Time:**
- State machine changes (ARM + SOLD): 1 hour
- StateService changes (pausar + tomar + hydration): 1.5 hours
- EstadoDetalleBuilder changes: 15 minutes
- Unit tests: 1 hour
- Integration tests: 1.5 hours
- Manual verification: 30 minutes
- **Total: ~6 hours**

---

## 10. Open Questions

1. **Should reanudar update Armador/Soldador or preserve original worker?**
   - Current plan: Preserve (do not update)
   - Rationale: Original worker gets credit for initiating the work
   - Tradeoff: New worker who resumes doesn't get credit

2. **Should we allow completar from pausado without resuming first?**
   - Current plan: NO (require TOMAR before COMPLETAR)
   - Rationale: Enforces occupation lock, prevents unauthorized completion
   - Tradeoff: Extra step for workers

3. **Should we allow cancelar from pausado?**
   - Current plan: YES (allow pausado → pendiente)
   - Rationale: Workers should be able to cancel paused work
   - Tradeoff: None identified

---

**Plan Complete - Ready for Phase 2 Critique**
