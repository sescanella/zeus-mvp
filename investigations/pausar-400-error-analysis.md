# PAUSAR Error 400 Investigation Report

**Date:** 2026-01-30
**Issue:** Error 400 (Bad Request) when attempting to PAUSAR a spool in ARMADO operation
**Environment:** Production (Railway backend + Vercel frontend)
**Status:** Root cause identified - DO NOT FIX (investigation only)

---

## Error Summary

**What:** HTTP 400 Bad Request when calling `POST /api/occupation/pausar`
**When:** User attempts to pause spool TEST-02 in ARMADO operation after clicking "CONFIRMAR 1 SPOOL"
**Where:**
- **Frontend:** `/zeues-frontend/app/confirmar/page.tsx` line 295 (single mode PAUSAR)
- **Backend:** `/backend/routers/occupation.py` line 148-233 (pausar_spool endpoint)
- **Error Path:** Router → StateService.pausar() → InvalidStateTransitionError → HTTPException 400

**Exact Error Message:**
```
Frontend: "pausarOcupacion error: Error: Error 400:"
Backend: {"detail":"Cannot PAUSAR ARM from state 'pendiente'. PAUSAR is only allowed from 'en_progreso' state."}
```

---

## Request Flow Analysis

### Frontend Payload (Sent)
**File:** `zeues-frontend/app/confirmar/page.tsx` line 289-295

```typescript
const payload: PausarRequest = {
  tag_spool,          // "TEST-02"
  worker_id,          // 93
  worker_nombre,      // "MR(93)"
  operacion,          // "ARM"
};
await pausarOcupacion(payload);
```

**Actual Request:**
```json
POST https://zeues-backend-mvp-production.up.railway.app/api/occupation/pausar
Content-Type: application/json

{
  "tag_spool": "TEST-02",
  "worker_id": 93,
  "worker_nombre": "MR(93)",
  "operacion": "ARM"
}
```

✅ **Frontend payload is CORRECT** - includes all required fields including `operacion`.

---

### Backend Validation (Expected)
**File:** `backend/models/occupation.py` lines 55-96

```python
class PausarRequest(BaseModel):
    tag_spool: str = Field(..., min_length=1)
    worker_id: int = Field(..., gt=0)
    worker_nombre: str = Field(..., min_length=1)
    operacion: ActionType = Field(...)  # REQUIRED field (added in commit 6748fd1)
```

✅ **Pydantic validation PASSES** - All required fields present in request payload.

---

### Validation Failure Point

**File:** `backend/services/state_service.py` lines 259-343

The error occurs at **line 304-311** in the state machine validation logic:

```python
async def pausar(self, request: PausarRequest) -> OccupationResponse:
    # ... (lines 259-300: lock ownership verification)

    # Step 2: Trigger pausar transition BEFORE clearing occupation
    if operacion == ActionType.ARM:
        current_arm_state = arm_machine.get_state_id()  # Returns "pendiente"

        # Defensive validation - FAILS HERE
        if current_arm_state != "en_progreso":
            raise InvalidStateTransitionError(  # ← THIS IS WHERE 400 ORIGINATES
                f"Cannot PAUSAR ARM from state '{current_arm_state}'. "
                f"PAUSAR is only allowed from 'en_progreso' state.",
                tag_spool=tag_spool,
                current_state=current_arm_state,  # "pendiente"
                attempted_transition="pausar"
            )
```

**Error Path:**
1. `InvalidStateTransitionError` raised at line 305-311
2. Caught by router at `backend/routers/occupation.py` line 214-219
3. Mapped to `HTTPException(status_code=400, detail=...)`
4. Returns HTTP 400 to frontend

---

## Root Cause Hypotheses

### Hypothesis 1: Spool Not in EN_PROGRESO State (MOST LIKELY) ⭐

**Evidence:**
- Error message explicitly states: `current_arm_state = 'pendiente'`
- StateService.pausar() requires state to be `'en_progreso'` (line 304)
- Spool TEST-02 hydrated to PENDIENTE instead of EN_PROGRESO

**Reasoning:**
The ARM state machine hydration logic determines state based on Google Sheets columns:

**File:** `backend/services/state_service.py` lines 436-502 (_hydrate_arm_machine)

```python
def _hydrate_arm_machine(self, spool) -> ARMStateMachine:
    if spool.fecha_armado:
        # COMPLETADO: fecha_armado exists
        machine.current_state = machine.completado
    elif spool.armador:
        if spool.ocupado_por is None or spool.ocupado_por == "":
            # PAUSADO: armador exists but no occupation
            machine.current_state = machine.pausado
        else:
            # EN_PROGRESO: armador exists AND occupied
            machine.current_state = machine.en_progreso
    elif spool.ocupado_por and spool.ocupado_por != "":
        # EDGE CASE: Ocupado_Por set but Armador is None (inconsistent state)
        # Added in commit ac64c55 to handle partial TOMAR failure
        machine.current_state = machine.en_progreso
        logger.warning(f"⚠️ INCONSISTENT STATE DETECTED...")
    else:
        # PENDIENTE: default initial state
        logger.debug(f"ARM hydrated to PENDIENTE for {spool.tag_spool}")
```

**Hydration scenario for TEST-02:**
- `spool.fecha_armado` = None (not completed)
- `spool.armador` = **None or empty** (key issue!)
- `spool.ocupado_por` = "MR(93)" (occupied)
- **Result:** Falls to EDGE CASE block (lines 482-497) → hydrates to EN_PROGRESO

**BUT:** If `spool.armador` is actually populated (e.g., from a previous TOMAR operation), and `spool.ocupado_por` is empty:
- `spool.armador` = "MR(93)"
- `spool.ocupado_por` = "" (lock expired or manually cleared)
- **Result:** Falls to PAUSADO block (lines 474-477) → but validation expects EN_PROGRESO!

**Likely Scenario:**
1. Worker MR(93) performed TOMAR on TEST-02 (wrote `Armador = "MR(93)"`)
2. Redis lock expired (1-hour TTL passed) OR lock was manually released
3. `Ocupado_Por` column was cleared (either by lock expiration or cache issue)
4. User attempts PAUSAR
5. Hydration logic sees: `armador = "MR(93)"` BUT `ocupado_por = ""` → hydrates to **PAUSADO**
6. StateService.pausar() validation expects **EN_PROGRESO** → rejects with 400 error

**Alternative sub-scenario:**
- Cache invalidation issue in SheetsRepository (fixed in commit 8143499)
- Fresh read from Sheets shows `Armador = None` (TOMAR state machine callback failed)
- Hydration falls through to default PENDIENTE state
- PAUSAR validation fails

**Test to confirm:**
```bash
# Check actual Google Sheets data for TEST-02
curl https://zeues-backend-mvp-production.up.railway.app/api/occupation/diagnostic/TEST-02
```

Expected data patterns:
- **Pattern A (Lock Expired):** `Armador = "MR(93)"`, `Ocupado_Por = ""` → Hydrates to PAUSADO → Fails validation
- **Pattern B (TOMAR Failed):** `Armador = None`, `Ocupado_Por = "MR(93)"` → Hydrates to EN_PROGRESO (edge case) → Should pass
- **Pattern C (Cache Issue):** Fresh read shows `Armador = None`, `Ocupado_Por = ""` → Hydrates to PENDIENTE → Fails validation

---

### Hypothesis 2: CompletarRequest Missing `operacion` Field (MEDIUM LIKELIHOOD)

**Evidence:**
- StateService methods (`tomar`, `pausar`, `completar`) ALL expect `request.operacion` (lines 90, 282, 366)
- `CompletarRequest` model does NOT have `operacion` field (lines 98-145)
- This is a **design inconsistency** in the codebase

**File:** `backend/models/occupation.py` lines 98-145

```python
class CompletarRequest(BaseModel):
    tag_spool: str = Field(...)
    worker_id: int = Field(...)
    worker_nombre: str = Field(...)
    fecha_operacion: date = Field(...)
    # ❌ NO operacion field!
```

**BUT:**
- `TomarRequest` has `operacion: ActionType` (line 36-39)
- `PausarRequest` has `operacion: ActionType` (line 79-82) ← Added in commit 6748fd1

**Reasoning:**
If COMPLETAR has the same pattern as PAUSAR, this suggests `operacion` field was recently added to PausarRequest (commit 6748fd1) but NOT to CompletarRequest. This creates an asymmetry:

- TOMAR: ✅ Has operacion
- PAUSAR: ✅ Has operacion (added in 6748fd1)
- COMPLETAR: ❌ Missing operacion

**Impact on PAUSAR:**
This hypothesis is LESS likely to be the direct cause of the current PAUSAR 400 error, since:
1. PausarRequest DOES have the `operacion` field (verified in validation test)
2. The error is coming from state machine validation, not Pydantic validation

**However:** This suggests a recent refactoring where `operacion` was added to PausarRequest but not CompletarRequest. This could indicate:
- StateService.completar() may have similar AttributeError bugs
- The pattern is being applied inconsistently across operations

**Test to confirm:**
```python
# Test CompletarRequest validation
from backend.models.occupation import CompletarRequest
from datetime import date

req = CompletarRequest(
    tag_spool='TEST-02',
    worker_id=93,
    worker_nombre='MR(93)',
    fecha_operacion=date.today()
)

# This will fail:
print(req.operacion)  # AttributeError: 'CompletarRequest' object has no attribute 'operacion'
```

---

### Hypothesis 3: Lock Ownership Mismatch (LOWER LIKELIHOOD)

**Evidence:**
- PAUSAR validates lock ownership BEFORE state machine check (lines 292-306)
- If lock ownership fails, error would be 403 FORBIDDEN, not 400 BAD REQUEST
- Error is 400, so lock ownership validation passed

**Reasoning:**
The error happens at state machine validation (line 304-311), which occurs AFTER lock ownership check passes. This means:
1. Redis lock exists for TEST-02
2. Lock is owned by worker 93
3. But state machine is in wrong state

**This rules out lock ownership as the root cause.**

---

## Recent Changes Impact

### Commit 9eb246c (2026-01-30) - Frontend operacion field fix
**Changes:** Added `operacion` field to frontend PausarRequest TypeScript interface
**Impact:** ✅ Frontend now sends correct payload (verified above)
**Regression:** No - this was a fix, not a regression

### Commit 6748fd1 (2026-01-30) - Backend operacion field addition
**Changes:** Added `operacion: ActionType` field to PausarRequest Pydantic model
**Impact:** Backend now requires and validates `operacion` field
**Regression:** ⚠️ This introduced requirement for frontend to send `operacion`
**Note:** Commit 9eb246c fixed the frontend to match this change

### Commit 8143499 (2026-01-30) - Cache invalidation fix
**Title:** "fix: resolve PAUSAR Error 400 with cache invalidation in SheetsRepository"
**Changes:** Added `self.invalidate_cache()` after writing Armador/Soldador columns
**Impact:** Should prevent stale reads where `Armador = None` after TOMAR
**Regression:** No - this was a fix for existing cache issue

### Commit ac64c55 (2026-01-30) - Inconsistent state handling
**Title:** "fix: handle inconsistent state in PAUSAR when TOMAR partially fails"
**Changes:** Added edge case hydration logic (lines 482-497) to handle `Ocupado_Por` set but `Armador` None
**Impact:** Allows PAUSAR to recover from partial TOMAR failures
**Regression:** No - this improves robustness

### Commit f5c69cb (2026-01-30) - Estado_detalle + metadata fixes
**Title:** "fix: resolve PAUSAR ARM bugs (metadata logging + estado_detalle display)"
**Impact:** Fixed metadata logging and estado_detalle display logic
**Regression:** No - this was a fix

---

## Comparison with Working Flows

### TOMAR Workflow (Working)
**Endpoint:** `POST /api/occupation/tomar`
**State Machine Path:**
1. Hydrate to current state (PENDIENTE/PAUSADO/EN_PROGRESO/COMPLETADO)
2. If PENDIENTE → `iniciar()` transition (writes Armador, sets EN_PROGRESO)
3. If PAUSADO → `reanudar()` transition (updates occupation, sets EN_PROGRESO)
4. Updates Ocupado_Por, Fecha_Ocupacion, Estado_Detalle

**Why TOMAR works:**
- Accepts spools in PENDIENTE or PAUSADO states
- Multiple valid entry states
- No strict state validation before transition

### PAUSAR Workflow (Failing)
**Endpoint:** `POST /api/occupation/pausar`
**State Machine Path:**
1. Hydrate to current state
2. **STRICT VALIDATION:** Must be in EN_PROGRESO state (line 304)
3. If not EN_PROGRESO → raise InvalidStateTransitionError → HTTP 400
4. If EN_PROGRESO → `pausar()` transition → clears occupation

**Why PAUSAR fails:**
- **Only accepts EN_PROGRESO state** (strict validation)
- If spool hydrates to PENDIENTE or PAUSADO → immediate rejection
- No fallback or recovery logic

### COMPLETAR Workflow (Unknown - Potential Issue)
**Endpoint:** `POST /api/occupation/completar`
**State Machine Path:**
1. Delegate to OccupationService (validates lock + writes fecha)
2. Hydrate state machines AFTER write
3. Trigger `completar()` transition based on `request.operacion`

**Potential Issue:**
- StateService.completar() expects `request.operacion` (line 366)
- CompletarRequest model does NOT have `operacion` field
- This will cause `AttributeError: 'CompletarRequest' object has no attribute 'operacion'`
- **COMPLETAR may be broken** due to same pattern as PAUSAR pre-commit-6748fd1

---

## Next Steps for Fix

### Fix Option 1: Relax PAUSAR Validation (Recommended)

**Rationale:** PAUSAR should be able to recover from edge cases where:
- Lock expired but worker wants to pause anyway
- State machine is in PAUSADO but user clicks PAUSAR again (idempotent)
- Spool is in inconsistent state due to previous failures

**Changes Required:**
1. **File:** `backend/services/state_service.py` lines 300-314

   **Current (Strict):**
   ```python
   if operacion == ActionType.ARM:
       current_arm_state = arm_machine.get_state_id()

       if current_arm_state != "en_progreso":  # ← FAILS on PAUSADO/PENDIENTE
           raise InvalidStateTransitionError(...)
   ```

   **Proposed (Lenient):**
   ```python
   if operacion == ActionType.ARM:
       current_arm_state = arm_machine.get_state_id()

       # Allow PAUSAR from EN_PROGRESO (normal case) or PAUSADO (idempotent/recovery)
       if current_arm_state == "en_progreso":
           await arm_machine.pausar()
           logger.info(f"ARM state: en_progreso → pausado for {tag_spool}")

       elif current_arm_state == "pausado":
           # Already paused - idempotent operation
           logger.info(f"ARM already pausado for {tag_spool} - idempotent PAUSAR")

       elif current_arm_state == "pendiente":
           # Edge case: Occupation set but state machine in PENDIENTE
           # This can happen if TOMAR failed to write Armador but wrote Ocupado_Por
           # Clear occupation to recover from inconsistent state
           logger.warning(f"⚠️ PAUSAR from PENDIENTE - recovering from inconsistent state: {tag_spool}")

       elif current_arm_state == "completado":
           # Cannot pause completed work
           raise InvalidStateTransitionError(
               f"Cannot PAUSAR ARM - operation already completed",
               tag_spool=tag_spool,
               current_state=current_arm_state,
               attempted_transition="pausar"
           )
   ```

2. **Testing:** Verify PAUSAR works for all scenarios:
   - Normal: EN_PROGRESO → PAUSADO ✅
   - Idempotent: PAUSADO → PAUSADO ✅
   - Recovery: PENDIENTE → PENDIENTE (clears occupation) ✅
   - Rejected: COMPLETADO → Error 400 ✅

---

### Fix Option 2: Fix CompletarRequest Model (Critical)

**Rationale:** StateService.completar() expects `request.operacion` but CompletarRequest doesn't have it. This will cause AttributeError when anyone attempts COMPLETAR.

**Changes Required:**
1. **File:** `backend/models/occupation.py` lines 98-145

   **Add operacion field:**
   ```python
   class CompletarRequest(BaseModel):
       tag_spool: str = Field(...)
       worker_id: int = Field(...)
       worker_nombre: str = Field(...)
       fecha_operacion: date = Field(...)
       operacion: ActionType = Field(  # ← ADD THIS
           ...,
           description="Operación que se está completando (ARM/SOLD)"
       )
   ```

2. **File:** `zeues-frontend/lib/types.ts` line 127-132

   **Add operacion to CompletarRequest interface:**
   ```typescript
   export interface CompletarRequest {
       tag_spool: string;
       worker_id: number;
       worker_nombre: string;
       fecha_operacion: string;  // DD-MM-YYYY format
       operacion: 'ARM' | 'SOLD' | 'METROLOGIA' | 'REPARACION';  // ← ADD THIS
   }
   ```

3. **File:** `zeues-frontend/app/confirmar/page.tsx` lines 306-313

   **Include operacion in payload:**
   ```typescript
   const payload: CompletarRequest = {
       tag_spool,
       worker_id,
       worker_nombre,
       fecha_operacion: formatDateDDMMYYYY(new Date()),
       operacion,  // ← ADD THIS (already available in context)
   };
   ```

4. **Testing:** Verify COMPLETAR still works after adding required field

---

### Fix Option 3: Improve Hydration Logic (Long-term)

**Rationale:** Current hydration logic couples occupation state (Ocupado_Por) with operation state (Armador/Soldador), creating ambiguity. Future v4.0 should add Estado_ARM and Estado_SOLD columns for explicit state tracking.

**Technical Debt Note (from state_service.py lines 446-453):**
```python
# ⚠️ TECHNICAL DEBT: This creates coupling between occupation state
# (Ocupado_Por column managed by OccupationService) and state machine state
# (managed by StateService). Ideally, state machine state should be
# determinable from state-specific columns only.
#
# Future Refactoring (v4.0): Add Estado_ARM column (enum: PENDIENTE/EN_PROGRESO/
# PAUSADO/COMPLETADO) that is updated by state machine callbacks. This would
# eliminate the coupling and make hydration deterministic.
```

**No immediate fix needed** - document as technical debt for v4.0.

---

## References

### Key Files (with line numbers)
- **Frontend:**
  - `zeues-frontend/lib/api.ts` lines 1050-1084 (pausarOcupacion function)
  - `zeues-frontend/lib/types.ts` lines 114-119 (PausarRequest interface)
  - `zeues-frontend/app/confirmar/page.tsx` lines 289-296 (PAUSAR single mode)

- **Backend:**
  - `backend/routers/occupation.py` lines 148-233 (pausar_spool endpoint)
  - `backend/models/occupation.py` lines 55-96 (PausarRequest model), 98-145 (CompletarRequest model)
  - `backend/services/state_service.py` lines 259-343 (pausar method), 436-502 (hydration logic)
  - `backend/services/occupation_service.py` lines 256-417 (pausar implementation)

### Git Commits
- `ac64c55` - fix: handle inconsistent state in PAUSAR when TOMAR partially fails
- `8143499` - fix: resolve PAUSAR Error 400 with cache invalidation in SheetsRepository
- `3b51b2f` - fix: resolve PAUSAR Error 500 with comprehensive state machine robustness improvements
- `9eb246c` - fix(frontend): add operacion field to PausarRequest to resolve Error 422
- `6748fd1` - fix: add operacion field to PausarRequest model
- `f5c69cb` - fix: resolve PAUSAR ARM bugs (metadata logging + estado_detalle display)

### Documentation
- `.planning/PROJECT.md` - v3.0 architecture and requirements
- `.planning/debug/pausar-fix-validation-failed.md` - Previous investigation (still open)
- `.planning/debug/error-422-pausar-test-02.md` - HTTP 422 investigation (resolved by 9eb246c)

---

## Summary

### Root Cause (Most Likely)
**Spool TEST-02 is not in EN_PROGRESO state when PAUSAR is attempted.**

The state machine hydration logic determines state from Google Sheets columns:
- If `Armador` exists AND `Ocupado_Por` is empty → hydrates to **PAUSADO**
- If `Armador` is None AND `Ocupado_Por` is set → hydrates to **EN_PROGRESO** (edge case)
- If both are None/empty → hydrates to **PENDIENTE**

StateService.pausar() strictly validates `current_state == "en_progreso"` before allowing transition. If spool hydrated to PAUSADO or PENDIENTE, it immediately rejects with 400 error.

**Most likely scenario:** Redis lock expired, `Ocupado_Por` was cleared, but `Armador` remains set. Spool hydrates to PAUSADO instead of EN_PROGRESO, validation fails.

### Secondary Issue (Critical)
**CompletarRequest model is missing `operacion` field** that StateService.completar() expects. This will cause AttributeError when COMPLETAR is attempted. This suggests a recent refactoring (commit 6748fd1) added `operacion` to PausarRequest but not CompletarRequest.

### Recommended Actions
1. **Immediate:** Relax PAUSAR state validation to allow recovery from PAUSADO/PENDIENTE states
2. **Urgent:** Add `operacion` field to CompletarRequest (backend + frontend) before COMPLETAR breaks
3. **Long-term:** Add explicit Estado_ARM/Estado_SOLD columns in v4.0 to eliminate hydration ambiguity

---

**Investigation completed:** 2026-01-30
**Report saved to:** `investigations/pausar-400-error-analysis.md`
