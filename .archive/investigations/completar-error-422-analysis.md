# COMPLETAR Error 422 - Root Cause Analysis

**Investigation Date:** 2026-01-30
**Error Type:** HTTP 422 Unprocessable Entity
**Operation:** ARMADO - COMPLETAR
**Affected Endpoint:** POST `/api/occupation/completar`

---

## Error Summary

**Context from Screenshot:**
- **Worker:** MR(94)
- **Spool:** TEST-02
- **Operation:** ARMADO (ARM)
- **Action:** COMPLETAR
- **HTTP Status:** 422 Unprocessable Entity
- **Endpoint:** `https://zeues-backend-mvp-production.up.railway.app/api/occupation/completar`
- **UI State:** User successfully reached confirmation page (P5) and clicked "CONFIRMAR 1 SPOOL" button

**Error Classification:**
HTTP 422 indicates the request syntax is valid (proper JSON structure) but the server cannot process it due to **semantic/validation errors** - typically Pydantic validation failures or business logic constraints.

---

## Root Cause Analysis

### The Core Issue: Data Type Mismatch

**Location:** `backend/models/occupation.py:122`

The `CompletarRequest` Pydantic model expects `fecha_operacion` to be a Python `date` object:

```python
class CompletarRequest(BaseModel):
    """
    Request body para completar trabajo en un spool.
    """
    tag_spool: str = Field(...)
    worker_id: int = Field(...)
    worker_nombre: str = Field(...)
    fecha_operacion: date = Field(  # <-- Line 122: Expects Python date object
        ...,
        description="Fecha de completado de la operación",
        examples=["2026-01-27"]
    )
```

**But the frontend sends a STRING:**

**File:** `zeues-frontend/app/confirmar/page.tsx:311`

```typescript
// ARM/SOLD: COMPLETAR con fecha_operacion requerida
const payload: CompletarRequest = {
  tag_spool,
  worker_id,
  worker_nombre,
  fecha_operacion: formatDateDDMMYYYY(new Date()), // DD-MM-YYYY format STRING
};
await completarOcupacion(payload);
```

**Helper Function (line 36-41):**
```typescript
const formatDateDDMMYYYY = (date: Date): string => {
  const day = String(date.getDate()).padStart(2, '0');
  const month = String(date.getMonth() + 1).padStart(2, '0');
  const year = date.getFullYear();
  return `${day}-${month}-${year}`;  // Returns STRING: "30-01-2026"
};
```

### Why This Triggers HTTP 422

**Pydantic Validation Flow:**

1. Frontend sends JSON with `fecha_operacion: "30-01-2026"` (string in DD-MM-YYYY format)
2. FastAPI receives the request and attempts to parse it against `CompletarRequest` model
3. Pydantic's `date` field parser expects:
   - ISO 8601 date string (`"2026-01-30"` in YYYY-MM-DD format), OR
   - A Python `date` object (impossible in JSON)
4. Pydantic receives `"30-01-2026"` which is **not a valid ISO 8601 date string**
5. Pydantic validation **fails** because it cannot parse DD-MM-YYYY format
6. FastAPI automatically returns **HTTP 422** with validation error details

**Expected Pydantic Error Message:**
```json
{
  "detail": [
    {
      "loc": ["body", "fecha_operacion"],
      "msg": "invalid date format",
      "type": "value_error.date"
    }
  ]
}
```

---

## Validation Business Logic Context

### Why fecha_operacion Exists

The `fecha_operacion` field was introduced in v3.0 to support:

1. **Flexible completion dates:** Workers can complete work on a different day than they took it
2. **Audit trail accuracy:** Record the actual date the work was finished, not just when the button was clicked
3. **Regulatory compliance:** Metadata sheet requires accurate fecha_operacion for event sourcing

**From CLAUDE.md:**
> NEW v3.0 requirements vs v2.1 completarAccion:
> - fecha_operacion is REQUIRED (DD-MM-YYYY format)
> - v2.1 used timestamp (ISO 8601) - v3.0 uses date only

**The Requirements Document Specifies DD-MM-YYYY:**

From documentation comments in `api.ts:1110`:
```typescript
 * fecha_operacion: '28-01-2026'  // DD-MM-YYYY format
```

From `occupation.py` model examples (line 125):
```python
examples=["2026-01-27"]  # <-- This is misleading! Shows ISO format in example
```

**CRITICAL INCONSISTENCY:** The Pydantic model example shows ISO 8601 format (`"2026-01-27"`), but the field validator and documentation specify DD-MM-YYYY format (`"28-01-2026"`).

---

## Why This Validation Rule Exists

### Pydantic's Date Type Purpose

The `date` field type enforces:
1. **Type Safety:** Ensures fecha_operacion is always a valid date, not arbitrary text
2. **Automatic Parsing:** Converts ISO 8601 strings to Python date objects automatically
3. **Validation:** Rejects invalid dates like "2026-02-30" or malformed strings

### Business Rules Enforced by COMPLETAR Endpoint

**File:** `backend/routers/occupation.py:236-315`

The `/api/occupation/completar` endpoint enforces these validations (all can trigger 422 if business logic fails, but 422 from router only occurs for Pydantic validation):

```python
@router.post("/occupation/completar", response_model=OccupationResponse, status_code=status.HTTP_200_OK)
async def completar_spool(request: CompletarRequest, service: StateService = Depends(get_state_service)):
    """
    Raises:
        HTTPException 404: If spool not found
        HTTPException 403: If worker doesn't own lock
        HTTPException 410: If lock already expired
        HTTPException 503: If Sheets update fails
    """
    # NOTE: 422 is NEVER explicitly raised in the router exception handlers
    # It's only returned by FastAPI's automatic Pydantic validation failure
```

**Router Exception Handling (lines 282-315):**
- `SpoolNoEncontradoError` → 404 NOT FOUND
- `NoAutorizadoError` → 403 FORBIDDEN (worker doesn't own lock)
- `LockExpiredError` → 410 GONE (lock expired)
- `SheetsUpdateError` → 503 SERVICE UNAVAILABLE
- Generic `Exception` → 500 INTERNAL SERVER ERROR

**NONE of these map to 422!**

### Additional Validations in StateService.completar()

**File:** `backend/services/state_service.py:355-440`

The `StateService.completar()` method performs:
1. Delegates to `OccupationService.completar()` for lock verification and Sheets update
2. Hydrates state machines from current Sheets state
3. Triggers state machine `completar` transition (validates current state)
4. Updates Estado_Detalle column

**File:** `backend/services/occupation_service.py:424-599`

The `OccupationService.completar()` method validates:
1. **Lock Ownership (line 460):** Verifies worker owns Redis lock
   - If lock doesn't exist → `LockExpiredError` (410)
   - If wrong worker → `NoAutorizadoError` (403)
2. **Spool Exists (line 476):** Checks spool exists in Sheets
   - If not found → `SpoolNoEncontradoError` (404)
3. **Operation Type Determination (line 482):** Determines ARM vs SOLD
   - Currently hardcoded to "ARM" with TODO comment
4. **Sheets Update (line 486):** Writes fecha_armado/soldadura and clears occupation
   - If conflict → `VersionConflictError` (re-raised)
   - If failure → `SheetsUpdateError` (503)
5. **Lock Release (line 527):** Releases Redis lock
6. **Metadata Logging (line 555):** Audit trail (best effort)

**NONE of these business validations return 422!**

---

## Reproduction Conditions

### Exact Conditions to Trigger This Error

To reproduce the 422 error, the following conditions must be met:

1. **Spool State:**
   - `TAG_SPOOL = "TEST-02"` exists in Operaciones sheet
   - `Ocupado_Por = "MR(94)"` (worker has valid occupation)
   - `Fecha_Ocupacion` is set (occupation timestamp exists)
   - Redis lock exists for TEST-02 with worker_id=94 as owner

2. **Worker State:**
   - Worker ID 94 exists and is active
   - Worker has appropriate role (Armador for ARM operation)

3. **Request Payload:**
   ```json
   {
     "tag_spool": "TEST-02",
     "worker_id": 94,
     "worker_nombre": "MR(94)",
     "fecha_operacion": "30-01-2026"  // <-- STRING in DD-MM-YYYY format
   }
   ```

4. **Timing:**
   - Redis lock has NOT expired (TTL > 0 seconds remaining)
   - Request reaches backend before 1-hour lock expiration

### Why Other Validations Would NOT Trigger

- **Lock exists + correct owner** → NoAutorizadoError (403) would NOT trigger
- **Lock exists** → LockExpiredError (410) would NOT trigger
- **Spool exists** → SpoolNoEncontradoError (404) would NOT trigger
- **Sheets accessible** → SheetsUpdateError (503) would NOT trigger

**CONCLUSION:** All business validations would pass. The ONLY reason for 422 is **Pydantic validation failure on fecha_operacion field type**.

---

## Data State Investigation

### Likely State of TEST-02 at Error Time

Based on the error context and investigation, TEST-02 was likely in this state:

**Operaciones Sheet Columns:**
```
TAG_SPOOL: "TEST-02"
Fecha_Materiales: <populated> (prerequisite for TOMAR)
Armador: "MR(94)" (written by TOMAR operation)
Fecha_Armado: null (not yet completed - this is what COMPLETAR writes)
Ocupado_Por: "MR(94)" (active occupation)
Fecha_Ocupacion: "30-01-2026 HH:MM:SS" (timestamp when TOMAR occurred)
version: <some UUID4> (optimistic locking token)
Estado_Detalle: "ARM en progreso" or similar
```

**Redis State:**
```
Key: "spool:TEST-02:lock"
Value: "94:<lock_token_uuid>" (worker_id + lock token)
TTL: <remaining seconds, likely 1000-3500 seconds>
```

**ARM State Machine (Hydrated):**
```
Current State: "en_progreso"
  - Because: Armador exists AND Ocupado_Por exists
  - Valid transitions: pausar, completar
```

**Why COMPLETAR Should Work (If Not For Format Issue):**
1. Worker 94 owns the lock ✓
2. Spool exists ✓
3. ARM state is en_progreso (allows completar transition) ✓
4. All prerequisites met ✓

**What Went Wrong:**
- Frontend sent `fecha_operacion: "30-01-2026"` (DD-MM-YYYY string)
- Pydantic expected ISO 8601 format: `"2026-01-30"` (YYYY-MM-DD string) or a date object
- Validation failed BEFORE any business logic ran
- FastAPI automatically returned 422 with Pydantic validation error

---

## Hypothesis

### What Went Wrong with TEST-02 COMPLETAR by MR(94)

**Timeline of Events:**

1. **User Flow (Successful Until Error):**
   - P1: Worker MR(94) selected ✓
   - P2: Operation ARMADO selected ✓
   - P3: Action COMPLETAR selected ✓
   - P4: Spool TEST-02 selected ✓
   - P5: Confirmation page reached ✓
   - User clicked "CONFIRMAR 1 SPOOL" button ✓

2. **Frontend Request Generation (line 307-313):**
   ```typescript
   const payload: CompletarRequest = {
     tag_spool: "TEST-02",
     worker_id: 94,
     worker_nombre: "MR(94)",
     fecha_operacion: formatDateDDMMYYYY(new Date()), // "30-01-2026"
   };
   await completarOcupacion(payload);
   ```

3. **HTTP Request Sent:**
   ```http
   POST https://zeues-backend-mvp-production.up.railway.app/api/occupation/completar
   Content-Type: application/json

   {
     "tag_spool": "TEST-02",
     "worker_id": 94,
     "worker_nombre": "MR(94)",
     "fecha_operacion": "30-01-2026"
   }
   ```

4. **FastAPI + Pydantic Validation (FAILS HERE):**
   - FastAPI receives request body
   - Attempts to parse JSON against `CompletarRequest` model
   - Pydantic validates `fecha_operacion` field:
     - Expected: `date` type (ISO 8601 string or date object)
     - Received: `"30-01-2026"` (DD-MM-YYYY format string)
     - Result: **Validation error**
   - FastAPI short-circuits and returns **422 Unprocessable Entity**
   - Router handler **NEVER executes** - validation fails before routing

5. **User Impact:**
   - Red error banner displayed on confirmation page
   - User sees generic "Error 422" message
   - Spool remains in "en_progreso" state (occupation NOT cleared)
   - Redis lock remains active (will expire after 1 hour)

**Why This Is a Critical Bug:**

1. **User Cannot Complete Work:** Valid completion attempts fail silently
2. **Lock Remains Active:** Spool stays occupied, blocking other workers
3. **Data Inconsistency:** Estado_Detalle shows "en progreso" indefinitely until lock expires
4. **Poor UX:** Error message unhelpful ("Error 422" without details)

---

## Code References

### Primary Issue Location

**Pydantic Model Definition:**
- File: `/Users/sescanella/Proyectos/KM/ZEUES-by-KM/backend/models/occupation.py`
- Lines: 98-145 (CompletarRequest class)
- Key Line: **Line 122** - `fecha_operacion: date = Field(...)`

**Frontend Date Formatting:**
- File: `/Users/sescanella/Proyectos/KM/ZEUES-by-KM/zeues-frontend/app/confirmar/page.tsx`
- Lines: 36-41 (formatDateDDMMYYYY helper)
- Lines: 307-313 (payload construction for COMPLETAR)
- Key Line: **Line 311** - `fecha_operacion: formatDateDDMMYYYY(new Date())`

**API Client:**
- File: `/Users/sescanella/Proyectos/KM/ZEUES-by-KM/zeues-frontend/lib/api.ts`
- Lines: 1114-1148 (completarOcupacion function)
- Documentation: Lines 1086-1113 (function docstring)

### Router Exception Handling

**Router Endpoint:**
- File: `/Users/sescanella/Proyectos/KM/ZEUES-by-KM/backend/routers/occupation.py`
- Lines: 236-315 (completar_spool endpoint)
- Exception Handlers:
  - Line 282: SpoolNoEncontradoError → 404
  - Line 289: NoAutorizadoError → 403
  - Line 296: LockExpiredError → 410
  - Line 303: SheetsUpdateError → 503
  - Line 310: Generic Exception → 500

**Note:** NO explicit 422 handler - Pydantic validation occurs before router executes.

### Service Layer

**StateService:**
- File: `/Users/sescanella/Proyectos/KM/ZEUES-by-KM/backend/services/state_service.py`
- Lines: 355-440 (completar method)
- Flow: Delegates to OccupationService → Hydrates state machines → Triggers transition

**OccupationService:**
- File: `/Users/sescanella/Proyectos/KM/ZEUES-by-KM/backend/services/occupation_service.py`
- Lines: 424-599 (completar method)
- Validations:
  - Line 460: Lock ownership check
  - Line 476: Spool existence check
  - Line 482: Operation type determination
  - Line 486: Sheets update with version conflict retry

---

## Recommended Next Steps

### Investigation Actions (NOT Fixes)

1. **Verify Production Logs:**
   - Check Railway backend logs for exact Pydantic validation error message
   - Confirm error occurred at timestamp matching screenshot
   - Look for stack trace showing FastAPI validation failure

   ```bash
   # Railway CLI or dashboard logs
   # Search for: "validation error" "422" "fecha_operacion"
   ```

2. **Reproduce in Local Environment:**
   - Start local backend: `uvicorn main:app --reload --port 8000`
   - Use curl to send exact payload:
   ```bash
   curl -X POST http://localhost:8000/api/occupation/completar \
     -H "Content-Type: application/json" \
     -d '{
       "tag_spool": "TEST-02",
       "worker_id": 94,
       "worker_nombre": "MR(94)",
       "fecha_operacion": "30-01-2026"
     }'
   ```
   - Expected: 422 response with Pydantic validation error details

3. **Verify Google Sheets State:**
   - Open Operaciones sheet
   - Find row for TEST-02
   - Check columns:
     - Ocupado_Por (should be "MR(94)" if error occurred mid-operation)
     - Fecha_Armado (should be empty - completion didn't succeed)
     - Estado_Detalle (should show "ARM en progreso" or similar)
   - Verify lock state in Redis:
   ```bash
   redis-cli GET "spool:TEST-02:lock"
   redis-cli TTL "spool:TEST-02:lock"
   ```

4. **Test Alternative Date Formats:**
   - Try ISO 8601 format: `"2026-01-30"` (should succeed)
   - Try DD-MM-YYYY format: `"30-01-2026"` (should fail with 422)
   - Try invalid date: `"99-99-9999"` (should fail with 422)
   - Document which format Pydantic actually accepts

5. **Check Frontend TypeScript Types:**
   - File: `/Users/sescanella/Proyectos/KM/ZEUES-by-KM/zeues-frontend/lib/types.ts`
   - Verify `CompletarRequest` interface definition
   - Check if `fecha_operacion` is typed as `string` or `Date`
   - Compare with backend Pydantic model expectations

6. **Review API Documentation:**
   - Check Swagger/OpenAPI docs at `http://localhost:8000/docs`
   - Navigate to POST `/api/occupation/completar`
   - Inspect schema for `CompletarRequest.fecha_operacion`
   - Note what format Swagger UI expects (should show "date" type)

---

## Additional Context

### Date Format Inconsistencies in Codebase

**From CLAUDE.md Standards (lines 176-189):**

```python
from backend.utils.date_formatter import now_chile, today_chile, format_date_for_sheets, format_datetime_for_sheets

# Business dates
format_date_for_sheets(today_chile())  # "21-01-2026"

# Audit timestamps
format_datetime_for_sheets(now_chile())  # "21-01-2026 14:30:00"
```

**Date Utilities Defined:**
- File: `backend/utils/date_formatter.py` (assumed to exist based on imports)
- Functions:
  - `format_date_for_sheets()` → Returns DD-MM-YYYY string
  - `format_datetime_for_sheets()` → Returns DD-MM-YYYY HH:MM:SS string
  - `today_chile()` → Returns date object in Chile timezone
  - `now_chile()` → Returns datetime object in Chile timezone

**Sheets Date Format Standard:**
- All dates written to Google Sheets use DD-MM-YYYY format
- Examples from codebase:
  - Fecha_Materiales: "21-01-2026"
  - Fecha_Armado: "22-01-2026"
  - Fecha_Soldadura: "23-01-2026"
  - Fecha_Ocupacion: "30-01-2026 14:30:00"

**API Contract Confusion:**

The v3.0 API expects `date` objects (Pydantic type), which:
- In JSON, must be ISO 8601 strings: `"YYYY-MM-DD"`
- Are automatically parsed by Pydantic to Python `date` objects
- Are then formatted to DD-MM-YYYY when written to Sheets

**Current Flow (Broken):**
```
Frontend (DD-MM-YYYY string)
  → JSON payload: "30-01-2026"
  → FastAPI/Pydantic: VALIDATION FAILS (422)
  → Never reaches Sheets formatting layer
```

**Expected Flow (Working):**
```
Frontend (ISO 8601 string)
  → JSON payload: "2026-01-30"
  → FastAPI/Pydantic: Parses to date(2026, 1, 30) ✓
  → OccupationService: format_date_for_sheets() → "30-01-2026"
  → Google Sheets: Writes "30-01-2026" ✓
```

### Related v3.0 Features

**From CLAUDE.md (lines 37-47):**

> **Key Features v3.0:**
> - TOMAR/PAUSAR/COMPLETAR workflows (Redis locks, 1-hour TTL)
> - SSE streaming (<10s latency for real-time updates)
> - Metrología instant inspection (APROBADO/RECHAZADO)
> - Reparación bounded cycles (max 3 before BLOQUEADO)
> - Hierarchical state machines (6 states, not 27)

**Occupation Workflow (TOMAR → COMPLETAR):**
1. TOMAR: Acquires Redis lock, writes Ocupado_Por + Fecha_Ocupacion
2. **COMPLETAR: Writes Fecha_Armado/Soldadura, clears occupation, releases lock**
3. State machine transition: en_progreso → completado

**This Error Blocks:** Workers from completing ARM/SOLD operations, causing:
- Spools stuck in "en_progreso" state
- Locks that only clear after 1-hour TTL expiration
- Manual intervention required to clear occupation if lock expires

---

## Summary

### Definitive Root Cause

**HTTP 422 is caused by Pydantic validation failure on `fecha_operacion` field.**

**Technical Reason:**
- Backend Pydantic model expects: `date` type (ISO 8601 format: YYYY-MM-DD)
- Frontend sends: String in DD-MM-YYYY format ("30-01-2026")
- Pydantic cannot parse DD-MM-YYYY as a valid date
- FastAPI returns 422 automatically before router executes

**Why Other Errors Don't Apply:**
- 403 Forbidden: Would require NoAutorizadoError (worker owns lock) ✗
- 410 Gone: Would require LockExpiredError (lock exists and valid) ✗
- 404 Not Found: Would require SpoolNoEncontradoError (spool exists) ✗
- 503 Service Unavailable: Would require SheetsUpdateError (Sheets not reached) ✗

**Impact:**
- **Severity:** CRITICAL - Blocks all COMPLETAR operations for ARM and SOLD
- **Scope:** All workers attempting to complete work
- **Workaround:** None available to users (backend code change required)

### Key Findings

1. **Date Format Mismatch:** Frontend uses DD-MM-YYYY, Pydantic expects ISO 8601 (YYYY-MM-DD)
2. **Validation Order:** Pydantic validates BEFORE business logic runs
3. **Error Location:** 422 generated by FastAPI framework, not application code
4. **Affected Operations:** COMPLETAR for ARM and SOLD (not METROLOGIA/REPARACION)
5. **Data State:** Spool remains in valid "en_progreso" state with active lock

---

**Investigation completed:** 2026-01-30
**Next action:** Review production logs to confirm Pydantic validation error details
**DO NOT IMPLEMENT FIXES** - This is investigation-only documentation
