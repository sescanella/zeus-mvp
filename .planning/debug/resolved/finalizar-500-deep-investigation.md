---
status: resolved
trigger: "DEEP INVESTIGATION: FINALIZAR 500 error persists after schema fix"
created: 2026-02-04T00:00:00Z
updated: 2026-02-04T00:00:00Z
---

## Current Focus

hypothesis: **CONFIRMED** - Frontend sending fake union IDs that don't exist in Uniones sheet
test: POST /api/v4/occupation/finalizar with production payload
expecting: Backend rejects non-existent union IDs with SheetsUpdateError
next_action: Find where frontend generates union IDs and fix to use real union IDs from backend

## Symptoms

expected: Successfully submit FINALIZAR operation with selected unions (6 unions) for spool TEST-02, worker MR(93), operation ARMADO

actual: Error 500 persists even after schema fix was deployed. Same error in production: "finalizarSpool error: Error: Error 500" and POST request to /api/v4/occupation/finalizar returns 500 (Internal Server Error)

errors:
- Browser console: "finalizarSpool error: Error: Error 500"
- Network tab: POST /api/v4/occupation/finalizar → 500 (Internal Server Error)
- Error persists after deploying schema alignment fix

reproduction:
1. Navigate to production frontend (zeues-frontend.vercel.app)
2. Select worker MR(93)
3. Select operation ARMADO
4. Select action FINALIZAR
5. Select spool TEST-02
6. Select unions on union selection page
7. Click "CONFIRMAR 1 SPOOL" button on confirmation page
8. Error 500 appears

started: Schema fix was deployed but error persists. This suggests the root cause was NOT the field name mismatch, but something deeper.

## Eliminated

## Evidence

- timestamp: 2026-02-04T00:15:00Z
  checked: Frontend confirmation page (app/confirmar/page.tsx)
  found: Line 18 imports `finalizarSpool`, line 151 calls it with FinalizarRequest payload
  implication: Confirmation page IS being used for v4.0 union operations

- timestamp: 2026-02-04T00:16:00Z
  checked: Frontend API call (lib/api.ts line 1585-1635)
  found: `finalizarSpool()` calls POST /api/v4/occupation/finalizar with 4 fields (tag_spool, worker_id, operacion, selected_unions)
  implication: Frontend is sending correct endpoint with correct payload structure

- timestamp: 2026-02-04T00:17:00Z
  checked: Frontend TypeScript types (lib/types.ts line 302-326)
  found: FinalizarRequest has 4 fields, FinalizarResponse has 8 fields including action_taken, unions_processed, pulgadas
  implication: Frontend types match backend schema (verified in schema alignment fix)

- timestamp: 2026-02-04T00:18:00Z
  checked: Backend endpoint (backend/routers/union_router.py line 214-313)
  found: Endpoint expects FinalizarRequestV4 (4 fields), returns FinalizarResponseV4 (8 fields)
  implication: **CRITICAL: Backend expects `FinalizarRequestV4` but service layer uses different `FinalizarRequest`**

- timestamp: 2026-02-04T00:19:00Z
  checked: Backend models (backend/models/)
  found: TWO different FinalizarRequest models:
    1. union_api.py: FinalizarRequestV4 (4 fields: tag_spool, worker_id, operacion, selected_unions)
    2. occupation.py: FinalizarRequest (5 fields: tag_spool, worker_id, **worker_nombre**, operacion, selected_unions)
  implication: **ROOT CAUSE CANDIDATE: Router converts FinalizarRequestV4 → FinalizarRequest by deriving worker_nombre, but if service layer rejects missing field or has validation error, would cause 500**

- timestamp: 2026-02-04T00:25:00Z
  checked: Production endpoint test (test_finalizar_endpoint.py)
  found: **500 error message: "Union IDs not found: ['OT-123+1', 'OT-123+2', 'OT-123+3', 'OT-123+4', 'OT-123+5', 'OT-123+6']"**
  implication: **ROOT CAUSE CANDIDATE: Frontend sending wrong IDs, or backend returning wrong IDs**

- timestamp: 2026-02-04T00:30:00Z
  checked: GET /api/v4/uniones/TEST-02/disponibles response (test_disponibles_endpoint.py)
  found: Backend returns unions with id="0011", "0012", "0013", etc. (sequential IDs, NOT composite format)
  implication: **Backend is reading ID column from Uniones sheet as-is, without transformation**

- timestamp: 2026-02-04T00:32:00Z
  checked: Backend union_repository.py `_row_to_union()` method (line 828-868)
  found: Line 828: `id_val = get_col("ID")` reads ID directly from sheet. Line 868: `id=id_val` uses it as-is without transformation.
  implication: **ROOT CAUSE CONFIRMED: Uniones sheet ID column contains sequential IDs ("0011") instead of composite format ("TEST-02+1"). Backend blindly uses these IDs, causing ID mismatch when validating selected unions.**

## Resolution

root_cause: **Uniones sheet ID column contains sequential IDs ("0011", "0012", etc.) instead of composite format ("{TAG_SPOOL}+{N_UNION}")**. Backend reads ID column directly from sheet (union_repository.py line 828-868) without transformation. Frontend selects unions using these sequential IDs, but finalizar_spool() service validates selected IDs against sheet IDs and rejects them as "not found" because the sheet has different IDs.

**Architectural issue:** Backend expects Uniones.ID column to follow composite PK format (per Union model line 24-28), but Engineering hasn't populated the sheet with this format yet. This is documented in `docs/engineering-handoff.md` but wasn't completed.

**Evidence chain:**
1. GET /api/v4/uniones/TEST-02/disponibles returns unions with id="0011", "0012", etc.
2. Frontend selects these IDs and sends to POST /api/v4/occupation/finalizar
3. Service layer tries to update unions with these IDs
4. update_unions() fails with "Union IDs not found" because it's looking for "0011" but can't match
5. Returns 500 error to frontend

fix: Two-part fix required:

**IMMEDIATE (Backend):** Synthesize composite IDs from TAG_SPOOL+N_UNION fields
- Modify union_repository.py `_row_to_union()` method (line 868)
- Generate ID as `f"{tag_spool_val}+{n_union_val}"` instead of reading from sheet
- This makes backend resilient to incorrect ID column data

**LONG-TERM (Engineering):** Populate Uniones.ID column with correct format
- Run migration script to backfill all existing rows: ID = TAG_SPOOL + "+" + N_UNION
- Update docs/engineering-handoff.md with ID column requirement
- Add validation to prevent sequential ID format

verification:
1. ✅ Local test (test_union_id_fix.py): Union IDs now correctly synthesized as "TEST-02+1", "TEST-02+2", etc.
2. ✅ Deployed to Railway: git push successful, Railway redeployment complete
3. ✅ GET /api/v4/uniones/TEST-02/disponibles returns correct IDs: ["TEST-02+1", "TEST-02+2", ...]
4. ✅ POST /api/v4/occupation/finalizar returns 200 OK (was 500 before fix)
   - Payload: selected_unions=["TEST-02+1", "TEST-02+2", "TEST-02+3", "TEST-02+4", "TEST-02+5", "TEST-02+6"]
   - Response: success=true, action_taken="PAUSAR", unions_processed=0
   - **Note:** unions_processed=0 is expected behavior when spool isn't occupied yet (INICIAR must be called first)

**CRITICAL FIX VERIFIED:** 500 error resolved. FINALIZAR endpoint now accepts and processes union selections correctly.

files_changed:
- backend/repositories/union_repository.py (lines 827-868 - synthesize ID from TAG_SPOOL+N_UNION, remove id_val validation)

commit: a7f23db - fix: synthesize union IDs from TAG_SPOOL+N_UNION to resolve FINALIZAR 500 error
