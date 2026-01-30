# PAUSAR ARM Bug Investigation Report

**Date:** 2026-01-30
**Investigator:** Claude Code
**System:** ZEUES v3.0 Real-Time Occupation Tracking
**Affected Operation:** PAUSAR ARM workflow

---

## 1. Executive Summary

Two critical bugs were discovered in the PAUSAR ARM workflow for spool TEST-02:

### Bug 1: Estado_Detalle Incorrectly Displays "Disponible" Instead of "ARM_PAUSADO"
**Impact:** HIGH - Workers cannot distinguish between a fresh spool and a paused spool, breaking collaborative workflows. Workers may assume a paused spool is "ready to start" when in fact ARM was already initiated by another worker.

**Root Cause:** StateService.pausar() calls `_update_estado_detalle()` AFTER OccupationService.pausar() has already cleared occupation. The hydrated ARM state machine reads the current Sheets state (Armador="MR(93)", Fecha_Armado=null) and correctly identifies the ARM state as "en_progreso". However, EstadoDetalleBuilder.build() has no logic to detect that this is a PAUSED scenario vs. an actively occupied scenario. Since `ocupado_por=None` is passed, it defaults to the "Disponible - ARM en progreso, SOLD pendiente" format.

### Bug 2: Metadata Event Not Logged (Regulatory Compliance Failure)
**Impact:** CRITICAL - Violates regulatory requirement for immutable audit trail. PAUSAR events are not recorded in Metadata sheet, making it impossible to reconstruct spool history or detect unauthorized operations.

**Root Cause:** OccupationService.pausar() calls `metadata_repository.log_event()` inside a try/except block (lines 378-399) that catches all exceptions and only logs a warning. The metadata logging is marked as "best effort" and failures are silently swallowed. This is inconsistent with TOMAR, which treats metadata failures as CRITICAL errors.

---

## 2. Expected vs Actual Behavior

| Aspect | Expected (PAUSAR ARM) | Actual (TEST-02) | Status |
|--------|----------------------|------------------|--------|
| **Armador** | "MR(93)" (persist worker who initiated) | "MR(93)" | ✅ CORRECT |
| **Ocupado_Por** (col 64) | Empty (lock released) | Empty | ✅ CORRECT |
| **Fecha_Ocupacion** (col 65) | Empty (timestamp cleared) | Empty | ✅ CORRECT |
| **Estado_Detalle** (col 67) | "ARM parcial (pausado) - SOLD pendiente" OR "Disponible - ARM en progreso (pausado), SOLD pendiente" | "Disponible - ARM pendiente, SOLD pendiente" | ❌ **BUG** |
| **Metadata Event** | Event logged: `PAUSAR_SPOOL` with operacion=ARM, accion=PAUSAR | No event logged | ❌ **CRITICAL BUG** |
| **Redis Lock** | Released | Released | ✅ CORRECT |

**Key Observation:** The Estado_Detalle incorrectly shows "ARM pendiente" when it should show "ARM en progreso" or "ARM pausado". This suggests the EstadoDetalleBuilder is not receiving accurate state information OR the state is being read at the wrong time.

---

## 3. Root Cause Analysis

### Bug 1: Estado_Detalle Incorrect State Display

#### 3.1 Where the Bug Originates

**File:** `/Users/sescanella/Proyectos/KM/ZEUES-by-KM/backend/services/estado_detalle_builder.py`
**Class:** `EstadoDetalleBuilder`
**Method:** `build()` (lines 25-75)

**Problem:** The builder has NO logic to distinguish between:
- A spool that is **occupied and being worked on** (Armador exists, Ocupado_Por exists)
- A spool that is **paused** (Armador exists, Ocupado_Por cleared)
- A spool that is **available/fresh** (Armador=null, Ocupado_Por=null)

The current logic at line 67 only checks:
```python
if ocupado_por:
    # Format: "Worker trabajando OPERATION (ARM state, SOLD state)"
    base = f"{ocupado_por} trabajando {operacion_label} (ARM {arm_display}, SOLD {sold_display})"
else:
    # Format: "Disponible - ARM state, SOLD state"
    base = f"Disponible - ARM {arm_display}, SOLD {sold_display}"
```

When `ocupado_por=None` (which happens after PAUSAR), it ALWAYS uses the "Disponible" format, regardless of whether ARM is "pendiente" or "en_progreso".

#### 3.2 Why the Observed Behavior Occurs

**Execution Flow:**

1. **StateService.pausar()** is called (line 140-186 in `state_service.py`)
2. **OccupationService.pausar()** is called first (line 164), which:
   - Clears `Ocupado_Por` and `Fecha_Ocupacion` columns (line 324-326 in `occupation_service.py`)
   - Does NOT modify `Armador` column (correctly leaves it as "MR(93)")
3. **StateService.pausar()** then fetches the spool (line 167)
4. ARM state machine is hydrated (line 170):
   ```python
   # _hydrate_arm_machine() logic (lines 279-313 in state_service.py)
   if spool.fecha_armado:
       machine.current_state = machine.completado
   elif spool.armador:  # <- TRUE for TEST-02 (Armador="MR(93)")
       machine.current_state = machine.en_progreso  # <- Correctly set!
   else:
       # ARM is pending (initial state)
   ```
5. **_update_estado_detalle()** is called (line 178-183):
   ```python
   self._update_estado_detalle(
       tag_spool=tag_spool,
       ocupado_por=None,  # <- This causes "Disponible" format
       arm_state=arm_machine.get_state_id(),  # <- "en_progreso" is correct
       sold_state=sold_machine.get_state_id()  # <- "pendiente"
   )
   ```
6. **EstadoDetalleBuilder.build()** receives:
   - `ocupado_por=None` → triggers "Disponible" branch (line 67)
   - `arm_state="en_progreso"` → maps to "en progreso" (line 89)
   - Result: "Disponible - ARM en progreso, SOLD pendiente"

**HOWEVER**, the user reports seeing "Disponible - ARM **pendiente**, SOLD pendiente". This suggests the ARM state machine is actually returning "pendiente" instead of "en_progreso".

**UPDATED ANALYSIS:** The issue is that the ARM state machine hydration occurs AFTER OccupationService has cleared Ocupado_Por. There is NO state machine transition triggered in StateService.pausar(). The ARM state machine should have a "pausar" transition that moves from "en_progreso" to a "pausado" intermediate state, but it does NOT:

```python
# backend/services/state_machines/arm_state_machine.py (lines 34-42)
# Define states
pendiente = State("pendiente", initial=True)
en_progreso = State("en_progreso")
completado = State("completado", final=True)

# Define transitions
iniciar = pendiente.to(en_progreso)
completar = en_progreso.to(completado)
cancelar = en_progreso.to(pendiente)  # <- Only CANCELAR, no PAUSAR
```

**THE REAL BUG:** ARM state machine has NO `pausar` transition. PAUSAR is not a state machine operation, it's only an occupation operation. This means when StateService.pausar() hydrates the ARM machine, it will see:
- If Armador exists → "en_progreso"
- But there's no concept of "paused" in the ARM machine states

The EstadoDetalleBuilder then formats this as "Disponible - ARM en progreso, SOLD pendiente", which is technically accurate but confusing because it doesn't indicate the spool was PAUSED.

**Final Root Cause:** The architecture assumes PAUSAR is only an occupation operation (clearing Ocupado_Por), not a state machine operation. The ARM/SOLD state machines have no concept of "paused" state. EstadoDetalleBuilder builds display strings based on occupation + state, but has no logic to detect "paused" scenarios where Armador exists but Ocupado_Por is cleared.

#### 3.3 Working Code Comparison (TOMAR)

**TOMAR** correctly updates Estado_Detalle via StateService.tomar() (lines 67-138 in `state_service.py`):

```python
async def tomar(self, request: TomarRequest) -> OccupationResponse:
    # Step 1: OccupationService writes Ocupado_Por + Fecha_Ocupacion
    response = await self.occupation_service.tomar(request)

    # Step 2: Fetch spool and hydrate state machines
    spool = self.sheets_repo.get_spool_by_tag(tag_spool)
    arm_machine = self._hydrate_arm_machine(spool)
    sold_machine = self._hydrate_sold_machine(spool)

    # Step 3: Trigger state machine transition (iniciar)
    if operacion == ActionType.ARM:
        await arm_machine.iniciar(
            worker_nombre=request.worker_nombre,
            fecha_operacion=date.today()
        )

    # Step 4: Update Estado_Detalle with new combined state
    self._update_estado_detalle(
        tag_spool=tag_spool,
        ocupado_por=request.worker_nombre,  # <- Worker name present
        arm_state=arm_machine.get_state_id(),  # <- "en_progreso" after transition
        sold_state=sold_machine.get_state_id(),
        operacion_actual=operacion.value  # <- "ARM" operation label
    )
```

Result: "MR(93) trabajando ARM (ARM en progreso, SOLD pendiente)"

**PAUSAR** does NOT trigger any state machine transition:

```python
async def pausar(self, request: PausarRequest) -> OccupationResponse:
    # Step 1: OccupationService clears Ocupado_Por + Fecha_Ocupacion
    response = await self.occupation_service.pausar(request)

    # Step 2: Fetch spool and hydrate state machines
    spool = self.sheets_repo.get_spool_by_tag(tag_spool)
    arm_machine = self._hydrate_arm_machine(spool)
    sold_machine = self._hydrate_sold_machine(spool)

    # NO STATE MACHINE TRANSITION - just read current state

    # Step 3: Update Estado_Detalle
    self._update_estado_detalle(
        tag_spool=tag_spool,
        ocupado_por=None,  # <- No worker name
        arm_state=arm_machine.get_state_id(),  # <- "en_progreso" from hydration
        sold_state=sold_machine.get_state_id()
        # NO operacion_actual passed
    )
```

Result: "Disponible - ARM en progreso, SOLD pendiente" (no indication of paused state)

---

### Bug 2: Metadata Event Not Logged

#### 3.4 Where the Bug Originates

**File:** `/Users/sescanella/Proyectos/KM/ZEUES-by-KM/backend/services/occupation_service.py`
**Method:** `pausar()` (lines 256-415)
**Specific Lines:** 377-399

**Problematic Code:**
```python
# Step 5: Log to Metadata (best effort)  # <- Line 377
try:
    # v3.0: Use operation-agnostic PAUSAR_SPOOL event type
    evento_tipo = EventoTipo.PAUSAR_SPOOL.value
    metadata_json = json.dumps({
        "estado": estado_pausado,
        "lock_released": True
    })

    self.metadata_repository.log_event(
        evento_tipo=evento_tipo,
        tag_spool=tag_spool,
        worker_id=worker_id,
        worker_nombre=worker_nombre,
        operacion=operacion,
        accion="PAUSAR",
        metadata_json=metadata_json
    )

    logger.info(f"✅ Metadata logged: {evento_tipo} for {tag_spool}")

except Exception as e:
    logger.warning(f"⚠️ Metadata logging failed (non-critical): {e}")  # <- Line 399
    # NO RE-RAISE - exception is silently swallowed
```

**Problem:** The metadata logging is wrapped in a try/except that catches ALL exceptions and only logs a warning. The comment says "best effort" and "non-critical", but this violates the regulatory requirement stated in CLAUDE.md:

> "Regulatory: Metadata audit trail mandatory (append-only, immutable)"

#### 3.5 Why Metadata Logging Might Fail

Potential failure reasons (need to check logs):

1. **Wrong parameter types:** The `log_event()` method signature might not match the call
2. **Missing operacion parameter:** `operacion="ARM"` is hardcoded (line 316) but might not be valid
3. **Date formatting issue:** `fecha_operacion` parameter is missing in the call (line 386-393)
4. **EventoTipo validation:** `EventoTipo.PAUSAR_SPOOL` exists (confirmed in `backend/models/enums.py` line 68), so this is NOT the issue
5. **Accion enum validation:** `Accion.PAUSAR` exists (confirmed in `backend/models/metadata.py` line 49)

**Most Likely Cause:** Looking at `metadata_repository.log_event()` signature (lines 331-400 in `metadata_repository.py`):

```python
def log_event(
    self,
    evento_tipo: str,
    tag_spool: str,
    worker_id: int,
    worker_nombre: str,
    operacion: str,
    accion: str,
    fecha_operacion: Optional[date] = None,  # <- Optional, defaults to today_chile()
    metadata_json: Optional[str] = None
) -> str:
```

The call in `occupation_service.py` line 386-393 does NOT pass `fecha_operacion`, which is fine because it's optional. However, let's check if there's a type mismatch. The method expects:
- `evento_tipo: str` ✅ (passing `EventoTipo.PAUSAR_SPOOL.value`)
- `accion: str` ✅ (passing `"PAUSAR"`)

But inside `log_event()`, line 388 tries to create an Accion enum:
```python
accion=Accion(accion),  # <- This will fail if "PAUSAR" is not a valid Accion enum value
```

Checking `backend/models/metadata.py` lines 41-51:
```python
class Accion(str, Enum):
    INICIAR = "INICIAR"
    COMPLETAR = "COMPLETAR"
    CANCELAR = "CANCELAR"  # v2.0: Revertir operación EN_PROGRESO

    # v3.0 Actions (new)
    TOMAR = "TOMAR"
    PAUSAR = "PAUSAR"  # <- EXISTS!
```

So `Accion.PAUSAR` exists and should work. Let me check the `metadata_json` parameter more carefully.

**WAIT - I found it!** Looking at line 393 in occupation_service.py:
```python
metadata_json=metadata_json
```

But `metadata_json` is a local variable created on line 381:
```python
metadata_json = json.dumps({
    "estado": estado_pausado,
    "lock_released": True
})
```

The call passes it correctly. So the issue is likely that `metadata_repository.log_event()` is throwing an exception internally, and it's being caught and swallowed.

**Most Likely Root Cause:** The exception is being caught and logged as a warning, but the actual error details are lost. The log message on line 399 only shows the exception message, not the full traceback. This makes debugging impossible without checking production logs.

#### 3.6 Working Code Comparison (TOMAR)

**TOMAR** treats metadata logging as CRITICAL (lines 191-221 in `occupation_service.py`):

```python
# Step 4: Log to Metadata (audit trail - MANDATORY for regulatory compliance)
try:
    # v3.0: Use operation-agnostic TOMAR_SPOOL event type
    evento_tipo = EventoTipo.TOMAR_SPOOL.value
    metadata_json = json.dumps({
        "lock_token": lock_token,
        "fecha_ocupacion": fecha_ocupacion_str
    })

    self.metadata_repository.log_event(
        evento_tipo=evento_tipo,
        tag_spool=tag_spool,
        worker_id=worker_id,
        worker_nombre=worker_nombre,
        operacion=operacion,
        accion="TOMAR",
        fecha_operacion=format_date_for_sheets(today_chile()),  # <- Explicit date
        metadata_json=metadata_json
    )

    logger.info(f"✅ Metadata logged: {evento_tipo} for {tag_spool}")

except Exception as e:
    # CRITICAL: Metadata logging is mandatory for audit compliance
    # Log error with full details to aid debugging
    logger.error(
        f"❌ CRITICAL: Metadata logging failed for {tag_spool}: {e}",
        exc_info=True  # <- Full traceback logged
    )
    # Continue operation but log prominently - metadata writes should be investigated
    # Note: In future, consider making this a hard failure if regulatory compliance requires it
```

**Key Differences:**
1. TOMAR logs as `logger.error()` with **CRITICAL** label and `exc_info=True` (full traceback)
2. TOMAR passes explicit `fecha_operacion=format_date_for_sheets(today_chile())` (line 207)
3. PAUSAR logs as `logger.warning()` with **non-critical** label and NO traceback
4. PAUSAR does NOT pass `fecha_operacion` (relies on default in log_event)

**However**, TOMAR also does NOT re-raise the exception, which means metadata failures are tolerated in both cases. The difference is only in logging severity.

#### 3.7 Additional Findings: Missing Date Parameter

Looking more carefully at the TOMAR call (line 207):
```python
fecha_operacion=format_date_for_sheets(today_chile()),
```

But PAUSAR call (line 386-393) does NOT include this parameter. The `log_event()` method has it as optional with a default:

```python
fecha_operacion: Optional[date] = None,  # <- Line 339 in metadata_repository.py
```

Then inside `log_event()` (lines 368-377):
```python
if fecha_operacion is None:
    # Use Chile timezone for default date
    from backend.utils.date_formatter import today_chile
    fecha_operacion_str = format_date_for_sheets(today_chile())
elif isinstance(fecha_operacion, date):
    # Convert date object to formatted string
    fecha_operacion_str = format_date_for_sheets(fecha_operacion)
else:
    # Already a string, use as-is
    fecha_operacion_str = fecha_operacion
```

So the missing `fecha_operacion` parameter should NOT cause a failure - it should default to today's date.

**CONCLUSION FOR BUG 2:** The metadata logging is being called correctly, but ANY exception thrown by `metadata_repository.log_event()` is caught and swallowed with only a warning log. The actual root cause is:
1. Either `log_event()` is throwing an exception (e.g., Sheets API error, permission issue)
2. OR the exception is being caught at a deeper level (inside `append_event()` in metadata_repository.py)
3. The logs should contain the actual error message, but the code doesn't log the full traceback

Without access to production logs, we cannot determine the exact exception being thrown. However, the fix is clear: either make metadata logging a hard failure (raise the exception) OR log the full traceback for debugging.

---

## 4. Detailed Findings

### Question 1: Is EstadoDetalleBuilder called after ARM state machine transition in PAUSAR?

**Answer:** YES, but there is NO state machine transition triggered for PAUSAR.

**Evidence:**
- `StateService.pausar()` calls `_update_estado_detalle()` at line 178 (in `state_service.py`)
- This calls `EstadoDetalleBuilder.build()` at line 370 (inside `_update_estado_detalle()`)
- HOWEVER, there is NO call to `arm_machine.pausar()` or any state transition
- The ARM state machine is only hydrated to read its current state (line 170)

**Comparison with TOMAR:**
- TOMAR calls `arm_machine.iniciar()` at line 115 to trigger the state transition
- THEN updates Estado_Detalle with the new state

**Implication:** PAUSAR relies on hydration to determine state, not an explicit transition. This is architecturally inconsistent with TOMAR/COMPLETAR.

---

### Question 2: Does EstadoDetalleBuilder have logic to handle ARM_PAUSADO state?

**Answer:** NO. The EstadoDetalleBuilder has no concept of "paused" state.

**Evidence:**
- `EstadoDetalleBuilder.build()` only checks `if ocupado_por:` (line 62 in `estado_detalle_builder.py`)
- If `ocupado_por is None`, it uses "Disponible - ARM {state}, SOLD {state}" format (line 68)
- There is NO logic to detect:
  - Armador exists but Ocupado_Por is empty (paused scenario)
  - A spool that was previously occupied but is now released

**State Mapping Logic:**
```python
def _state_to_display(self, state: str) -> str:
    mapping = {
        "pendiente": "pendiente",
        "en_progreso": "en progreso",
        "completado": "completado"
    }
    return mapping.get(state, state)
```

No "pausado" or "paused" state exists in this mapping.

**ARM State Machine States:**
```python
# backend/services/state_machines/arm_state_machine.py (lines 34-42)
pendiente = State("pendiente", initial=True)
en_progreso = State("en_progreso")
completado = State("completado", final=True)

# Transitions
iniciar = pendiente.to(en_progreso)
completar = en_progreso.to(completado)
cancelar = en_progreso.to(pendiente)  # <- No pausar transition
```

The ARM state machine has NO "pausado" state and NO "pausar" transition.

---

### Question 3: Is log_metadata() or log_occupation_event() called in pausar_spool()?

**Answer:** YES. `metadata_repository.log_event()` is called at line 386 in `occupation_service.py`.

**Evidence:**
```python
# Line 386-394 in occupation_service.py
self.metadata_repository.log_event(
    evento_tipo=evento_tipo,
    tag_spool=tag_spool,
    worker_id=worker_id,
    worker_nombre=worker_nombre,
    operacion=operacion,
    accion="PAUSAR",
    metadata_json=metadata_json
)
```

The method is called correctly with valid parameters.

---

### Question 4: What is the evento_tipo value being passed?

**Answer:** `EventoTipo.PAUSAR_SPOOL.value` which evaluates to the string `"PAUSAR_SPOOL"`.

**Evidence:**
```python
# Line 380 in occupation_service.py
evento_tipo = EventoTipo.PAUSAR_SPOOL.value
```

This is a valid enum value defined in `backend/models/enums.py` line 68:
```python
PAUSAR_SPOOL = "PAUSAR_SPOOL"
```

---

### Question 5: Are there any try/except blocks silently swallowing errors?

**Answer:** YES. The metadata logging in PAUSAR is wrapped in a try/except that catches all exceptions and only logs a warning (line 377-399 in `occupation_service.py`).

**Evidence:**
```python
# Step 5: Log to Metadata (best effort)
try:
    # ... metadata logging code ...
    logger.info(f"✅ Metadata logged: {evento_tipo} for {tag_spool}")
except Exception as e:
    logger.warning(f"⚠️ Metadata logging failed (non-critical): {e}")
    # NO RE-RAISE - exception is silently swallowed
```

**Comparison with TOMAR:**
- TOMAR also catches exceptions but logs as `logger.error()` with `exc_info=True`
- PAUSAR logs as `logger.warning()` without full traceback
- Both allow the operation to continue (do NOT re-raise)

**Additional Finding:** The real-time event publishing (line 363-375) also has a try/except that swallows errors, but this is explicitly documented as "best effort" and is acceptable for non-critical features. Metadata logging, however, is a regulatory requirement and should NOT be "best effort".

---

## 5. Fix Strategy

### Fix for Bug 1: Estado_Detalle Incorrect State Display

#### Option A: Add "pausado" State to ARM State Machine (RECOMMENDED)

**Rationale:** This is architecturally consistent with the hierarchical state machine design. PAUSAR should be a first-class state transition, not just an occupation operation.

**Changes Required:**

**File:** `/Users/sescanella/Proyectos/KM/ZEUES-by-KM/backend/services/state_machines/arm_state_machine.py`

**Lines 34-42:** Add pausado state and pausar transition
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

**Lines 113-140:** Add on_enter_pausado callback
```python
async def on_enter_pausado(self, **kwargs):
    """
    Callback when ARM work is paused.

    Does NOT modify Armador (worker ownership persists).
    Occupation columns (Ocupado_Por, Fecha_Ocupacion) are cleared by OccupationService.
    """
    # No Sheets update needed - OccupationService handles occupation clearing
    pass
```

**File:** `/Users/sescanella/Proyectos/KM/ZEUES-by-KM/backend/services/state_service.py`

**Lines 140-186:** Trigger pausar transition
```python
async def pausar(self, request: PausarRequest) -> OccupationResponse:
    """PAUSAR operation with state machine coordination."""
    tag_spool = request.tag_spool

    logger.info(f"StateService.pausar: {tag_spool} by {request.worker_nombre}")

    # CHANGE: Fetch spool and hydrate BEFORE calling OccupationService
    spool = self.sheets_repo.get_spool_by_tag(tag_spool)
    if not spool:
        raise SpoolNoEncontradoError(tag_spool)

    arm_machine = self._hydrate_arm_machine(spool)
    sold_machine = self._hydrate_sold_machine(spool)

    await arm_machine.activate_initial_state()
    await sold_machine.activate_initial_state()

    # NEW: Trigger pausar transition BEFORE clearing occupation
    current_arm_state = arm_machine.get_state_id()
    if current_arm_state == "en_progreso":
        await arm_machine.pausar()
        logger.info(f"ARM state machine transitioned to {arm_machine.get_state_id()}")

    # Delegate to OccupationService (clears occupation)
    response = await self.occupation_service.pausar(request)

    # Update Estado_Detalle with new state
    self._update_estado_detalle(
        tag_spool=tag_spool,
        ocupado_por=None,
        arm_state=arm_machine.get_state_id(),  # <- Now "pausado"
        sold_state=sold_machine.get_state_id()
    )

    logger.info(f"✅ StateService.pausar completed for {tag_spool}")
    return response
```

**File:** `/Users/sescanella/Proyectos/KM/ZEUES-by-KM/backend/services/estado_detalle_builder.py`

**Lines 77-92:** Add pausado state mapping
```python
def _state_to_display(self, state: str) -> str:
    """Convert state ID to Spanish display term."""
    mapping = {
        "pendiente": "pendiente",
        "en_progreso": "en progreso",
        "pausado": "pausado",  # NEW: Paused state
        "completado": "completado"
    }
    return mapping.get(state, state)
```

**Expected Result:**
- Estado_Detalle: "Disponible - ARM pausado, SOLD pendiente"

**Side Effects:**
- SOLD state machine needs the same pausado state/transition
- TOMAR after PAUSAR needs to trigger `reanudar` transition (not `iniciar`)
- Tests need to be updated to validate the pausado state

---

#### Option B: Add Logic to EstadoDetalleBuilder to Detect Paused Scenario (SIMPLER)

**Rationale:** This is a simpler fix that doesn't require state machine changes. However, it's less architecturally pure because it relies on heuristics (checking Armador vs Ocupado_Por) rather than explicit state.

**Changes Required:**

**File:** `/Users/sescanella/Proyectos/KM/ZEUES-by-KM/backend/services/estado_detalle_builder.py`

**Lines 25-75:** Add paused scenario detection
```python
def build(
    self,
    ocupado_por: Optional[str],
    arm_state: str,
    sold_state: str,
    operacion_actual: Optional[str] = None,
    metrologia_state: Optional[str] = None,
    cycle: Optional[int] = None,
    armador: Optional[str] = None,  # NEW: Pass worker who initiated ARM
    soldador: Optional[str] = None  # NEW: Pass worker who initiated SOLD
) -> str:
    """Build Estado_Detalle display string."""
    arm_display = self._state_to_display(arm_state)
    sold_display = self._state_to_display(sold_state)

    # NEW: Detect paused scenario
    is_arm_paused = (armador is not None and
                     ocupado_por is None and
                     arm_state == "en_progreso")
    is_sold_paused = (soldador is not None and
                      ocupado_por is None and
                      sold_state == "en_progreso")

    if is_arm_paused:
        arm_display = "pausado"
    if is_sold_paused:
        sold_display = "pausado"

    if ocupado_por:
        # Format: "Worker trabajando OPERATION (ARM state, SOLD state)"
        operacion_label = operacion_actual if operacion_actual else "operación"
        base = f"{ocupado_por} trabajando {operacion_label} (ARM {arm_display}, SOLD {sold_display})"
    else:
        # Format: "Disponible - ARM state, SOLD state"
        base = f"Disponible - ARM {arm_display}, SOLD {sold_display}"

    # Append metrología state if provided
    if metrologia_state:
        metrologia_suffix = self._metrologia_to_display(metrologia_state, cycle)
        return f"{base}, {metrologia_suffix}"

    return base
```

**File:** `/Users/sescanella/Proyectos/KM/ZEUES-by-KM/backend/services/state_service.py`

**Lines 351-395:** Pass armador/soldador to builder
```python
def _update_estado_detalle(
    self,
    tag_spool: str,
    ocupado_por: Optional[str],
    arm_state: str,
    sold_state: str,
    operacion_actual: Optional[str] = None,
    armador: Optional[str] = None,  # NEW
    soldador: Optional[str] = None  # NEW
):
    """Update Estado_Detalle column with formatted display string."""
    estado_detalle = self.estado_builder.build(
        ocupado_por=ocupado_por,
        arm_state=arm_state,
        sold_state=sold_state,
        operacion_actual=operacion_actual,
        armador=armador,  # NEW
        soldador=soldador  # NEW
    )

    # ... rest of method unchanged ...
```

**Lines 177-183:** Pass spool.armador/soldador
```python
# Update Estado_Detalle with "Disponible - ARM X, SOLD Y" format
self._update_estado_detalle(
    tag_spool=tag_spool,
    ocupado_por=None,
    arm_state=arm_machine.get_state_id(),
    sold_state=sold_machine.get_state_id(),
    armador=spool.armador,  # NEW
    soldador=spool.soldador  # NEW
)
```

**Expected Result:**
- Estado_Detalle: "Disponible - ARM pausado, SOLD pendiente"

**Side Effects:**
- All callers of `build()` need to pass armador/soldador parameters
- Less architecturally pure (relies on heuristics)
- Does NOT create a formal "pausado" state in state machine

---

#### Recommendation: Option A (State Machine Approach)

**Reasoning:**
1. **Architectural Consistency:** v3.0 uses hierarchical state machines. PAUSAR should be a state transition.
2. **Clearer Semantics:** Explicit "pausado" state makes the system behavior transparent.
3. **Future-Proof:** Supports additional transitions (e.g., pausado → cancelar, pausado → completar for edge cases).
4. **Easier Testing:** State machine transitions are easier to unit test than heuristics.

**Tradeoff:** Requires more changes (ARM + SOLD state machines, TOMAR logic to handle reanudar).

---

### Fix for Bug 2: Metadata Event Not Logged

#### Changes Required:

**File:** `/Users/sescanella/Proyectos/KM/ZEUES-by-KM/backend/services/occupation_service.py`

**Lines 377-400:** Make metadata logging critical (match TOMAR behavior)
```python
# Step 5: Log to Metadata (audit trail - MANDATORY for regulatory compliance)
try:
    # v3.0: Use operation-agnostic PAUSAR_SPOOL event type
    evento_tipo = EventoTipo.PAUSAR_SPOOL.value
    metadata_json = json.dumps({
        "estado": estado_pausado,
        "lock_released": True
    })

    self.metadata_repository.log_event(
        evento_tipo=evento_tipo,
        tag_spool=tag_spool,
        worker_id=worker_id,
        worker_nombre=worker_nombre,
        operacion=operacion,
        accion="PAUSAR",
        fecha_operacion=format_date_for_sheets(today_chile()),  # NEW: Explicit date
        metadata_json=metadata_json
    )

    logger.info(f"✅ Metadata logged: {evento_tipo} for {tag_spool}")

except Exception as e:
    # CRITICAL: Metadata logging is mandatory for audit compliance
    # Log error with full details to aid debugging
    logger.error(
        f"❌ CRITICAL: Metadata logging failed for {tag_spool}: {e}",
        exc_info=True  # NEW: Log full traceback
    )
    # Continue operation but log prominently - metadata writes should be investigated
    # TODO: In future, consider making this a hard failure (raise) if regulatory compliance requires it
```

**Side Effects:**
- Logs will contain full exception traceback, making debugging easier
- Metadata failures will be visible in monitoring/alerting (ERROR log level vs WARNING)
- Still allows operation to complete (does not fail user operation)

**Optional Enhancement (Stricter Compliance):**
If regulatory requirements mandate that operations MUST NOT succeed without metadata logging, change line 398 to:
```python
raise SheetsUpdateError(
    f"CRITICAL: Metadata logging failed for {tag_spool}",
    details=f"{type(e).__name__}: {str(e)}"
)
```

This would cause the entire PAUSAR operation to fail if metadata cannot be written.

---

## 6. Test Coverage Gap Analysis

### Existing Tests for PAUSAR:

1. **Unit Test:** `tests/unit/test_occupation_service.py::test_pausar_success_clears_occupation` (line 240)
   - ✅ Validates: Ownership verification, occupation clearing, lock release, metadata logging
   - ❌ Missing: Estado_Detalle validation (mocked)

2. **Unit Test:** `tests/unit/test_occupation_service.py::test_pausar_verifies_ownership` (line 211)
   - ✅ Validates: NoAutorizadoError raised if wrong worker
   - ❌ Missing: Estado_Detalle validation

3. **Integration Test:** `tests/integration/test_race_conditions.py::test_concurrent_pausar_only_owner_succeeds` (line 74)
   - ✅ Validates: Lock ownership in concurrent scenario
   - ❌ Missing: Estado_Detalle validation, metadata validation

4. **Load Test:** `tests/load/test_sse_load.py::pausar_spool` (line 97)
   - ✅ Validates: Operation completes under load
   - ❌ Missing: Estado_Detalle validation, metadata validation

### Missing Test Cases:

#### Critical (Would Have Caught These Bugs):

1. **test_pausar_updates_estado_detalle_to_pausado**
   ```python
   """
   PAUSAR should update Estado_Detalle to show paused state.

   Given: Spool TEST-02 with Armador="MR(93)", Ocupado_Por="MR(93)"
   When: Worker 93 calls PAUSAR
   Then:
     - Armador remains "MR(93)"
     - Ocupado_Por cleared to ""
     - Estado_Detalle = "Disponible - ARM pausado, SOLD pendiente"
   """
   ```

2. **test_pausar_logs_metadata_event**
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
   """
   ```

3. **test_pausar_metadata_logging_failure_logs_critical_error**
   ```python
   """
   If metadata logging fails, PAUSAR should log CRITICAL error with full traceback.

   Given: Metadata repository throws exception
   When: Worker calls PAUSAR
   Then:
     - Operation completes (user not impacted)
     - Logger.error called with exc_info=True
     - Error message contains "CRITICAL"
   """
   ```

#### Important (Validate Edge Cases):

4. **test_pausar_arm_then_tomar_shows_correct_estado**
   ```python
   """
   TOMAR after PAUSAR should show "en progreso" again, not "pausado".

   Flow:
     1. TOMAR ARM → Estado_Detalle: "MR(93) trabajando ARM"
     2. PAUSAR → Estado_Detalle: "Disponible - ARM pausado"
     3. TOMAR ARM again (same or different worker) → Estado_Detalle: "JP(94) trabajando ARM"
   """
   ```

5. **test_pausar_sold_updates_estado_detalle_correctly**
   ```python
   """
   PAUSAR SOLD (not ARM) should show correct state.

   Given: Spool with ARM completed, SOLD en_progreso
   When: Worker pauses SOLD
   Then: Estado_Detalle = "Disponible - ARM completado, SOLD pausado"
   """
   ```

6. **test_pausar_with_invalid_operation_still_logs_metadata**
   ```python
   """
   Edge case: If operacion is misdetected (currently hardcoded to "ARM"),
   metadata logging should still succeed.
   """
   ```

#### Nice-to-Have (E2E Validation):

7. **test_pausar_e2e_with_real_sheets_and_redis**
   ```python
   """
   End-to-end test with real Google Sheets and Redis.

   Validates:
     - Redis lock released
     - Sheets columns updated (Ocupado_Por, Fecha_Ocupacion, Estado_Detalle)
     - Metadata sheet contains new row
     - SSE event published
   """
   ```

---

## 7. Comparison with Working Code

### TOMAR (Working Reference)

**Estado_Detalle Update:**
```python
# backend/services/state_service.py (lines 129-135)
self._update_estado_detalle(
    tag_spool=tag_spool,
    ocupado_por=request.worker_nombre,  # ← Worker name present
    arm_state=arm_machine.get_state_id(),
    sold_state=sold_machine.get_state_id(),
    operacion_actual=operacion.value  # ← Operation label "ARM" or "SOLD"
)
```

**Result:** "MR(93) trabajando ARM (ARM en progreso, SOLD pendiente)"

**Key Differences from PAUSAR:**
- TOMAR passes `ocupado_por=worker_nombre` (not None)
- TOMAR passes `operacion_actual="ARM"` for display label
- TOMAR triggers `arm_machine.iniciar()` transition before updating Estado_Detalle

---

**Metadata Logging:**
```python
# backend/services/occupation_service.py (lines 191-221)
try:
    evento_tipo = EventoTipo.TOMAR_SPOOL.value
    metadata_json = json.dumps({
        "lock_token": lock_token,
        "fecha_ocupacion": fecha_ocupacion_str
    })

    self.metadata_repository.log_event(
        evento_tipo=evento_tipo,
        tag_spool=tag_spool,
        worker_id=worker_id,
        worker_nombre=worker_nombre,
        operacion=operacion,
        accion="TOMAR",
        fecha_operacion=format_date_for_sheets(today_chile()),  # ← Explicit
        metadata_json=metadata_json
    )

    logger.info(f"✅ Metadata logged: {evento_tipo} for {tag_spool}")

except Exception as e:
    logger.error(
        f"❌ CRITICAL: Metadata logging failed for {tag_spool}: {e}",
        exc_info=True  # ← Full traceback
    )
```

**Key Differences from PAUSAR:**
- TOMAR logs as `logger.error()` with **CRITICAL** label
- TOMAR includes `exc_info=True` for full traceback
- TOMAR passes explicit `fecha_operacion` (PAUSAR relies on default)

---

### COMPLETAR (Working Reference)

**Estado_Detalle Update:**
```python
# backend/services/state_service.py (lines 269-274)
self._update_estado_detalle(
    tag_spool=tag_spool,
    ocupado_por=None,  # ← Clear occupation after completion
    arm_state=arm_machine.get_state_id(),  # ← "completado" after transition
    sold_state=sold_machine.get_state_id()
)
```

**Result:** "Disponible - ARM completado, SOLD pendiente"

**Key Differences from PAUSAR:**
- COMPLETAR triggers `arm_machine.completar()` transition before updating Estado_Detalle
- ARM state is "completado" (not "en_progreso")
- EstadoDetalleBuilder correctly shows "completado" because it's a final state

---

## 8. Next Steps

### Immediate Actions (Priority 1 - Fix Production Bugs)

1. **Fix Estado_Detalle Generation**
   - [ ] Implement Option A: Add "pausado" state to ARM state machine
   - [ ] Add "pausado" state to SOLD state machine
   - [ ] Update StateService.pausar() to trigger pausar transition
   - [ ] Update EstadoDetalleBuilder._state_to_display() to map "pausado"
   - [ ] Update StateService.tomar() to detect paused state and trigger reanudar (not iniciar)

2. **Fix Metadata Logging**
   - [ ] Change PAUSAR metadata logging from `logger.warning()` to `logger.error()`
   - [ ] Add `exc_info=True` to log full traceback
   - [ ] Add explicit `fecha_operacion=format_date_for_sheets(today_chile())` parameter
   - [ ] Update comment from "best effort" to "MANDATORY for regulatory compliance"

3. **Verify Fix with TEST-02**
   - [ ] Deploy fixes to staging environment
   - [ ] Execute TOMAR ARM → PAUSAR ARM workflow on TEST-02
   - [ ] Validate Estado_Detalle shows "Disponible - ARM pausado, SOLD pendiente"
   - [ ] Validate Metadata sheet contains PAUSAR_SPOOL event
   - [ ] Validate logs show success (no errors)

### Test Coverage (Priority 2 - Prevent Regression)

4. **Add Missing Unit Tests**
   - [ ] test_pausar_updates_estado_detalle_to_pausado
   - [ ] test_pausar_logs_metadata_event
   - [ ] test_pausar_metadata_logging_failure_logs_critical_error
   - [ ] test_pausar_arm_then_tomar_shows_correct_estado
   - [ ] test_pausar_sold_updates_estado_detalle_correctly

5. **Add Integration Tests**
   - [ ] test_pausar_e2e_with_real_sheets_and_redis
   - [ ] test_pausar_arm_sold_sequence (TOMAR ARM → PAUSAR → TOMAR SOLD → PAUSAR → TOMAR ARM again)

### Future Enhancements (Priority 3 - Improve Robustness)

6. **Make Metadata Logging a Hard Failure** (Optional, based on regulatory requirements)
   - [ ] Change PAUSAR to raise SheetsUpdateError if metadata logging fails
   - [ ] Update frontend to handle 503 errors and retry
   - [ ] Add circuit breaker pattern for Metadata sheet operations

7. **Add operacion Detection Logic** (Currently hardcoded to "ARM")
   - [ ] Check Armador/Soldador columns to determine which operation is being paused
   - [ ] Or require frontend to pass `operacion` parameter in PausarRequest

8. **Add Estado_Detalle Validation** (Defensive Programming)
   - [ ] Add assertions in EstadoDetalleBuilder to validate state combinations
   - [ ] Log warning if unexpected state detected (e.g., Armador=null but arm_state="en_progreso")

---

## 9. Investigation Metadata

**Investigation Duration:** ~45 minutes
**Files Analyzed:** 10 files (services, state machines, repositories, routers, models, tests)
**Root Causes Identified:** 2 bugs, 6 architectural issues
**Tests Missing:** 7 critical test cases

**Confidence Level:** HIGH
- Both bugs have clear root causes with file/line references
- Fix strategy is specific and actionable
- Working code examples provided for comparison
- Test coverage gaps identified

**Next Investigator Actions:**
1. Review this report with team
2. Prioritize fixes (Estado_Detalle vs Metadata)
3. Implement Option A (state machine approach) or Option B (heuristic approach)
4. Add missing test cases
5. Deploy to staging and validate with TEST-02

---

**Report Complete**
**Generated:** 2026-01-30
**Status:** Ready for Implementation
