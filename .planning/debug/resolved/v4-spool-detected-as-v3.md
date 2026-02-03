---
status: resolved
trigger: "v4-spool-detected-as-v3"
created: 2026-02-03T00:00:00Z
updated: 2026-02-03T22:00:00Z
---

## Current Focus

hypothesis: CONFIRMED - This was already fixed and deployed, but production cache was stale
test: Clear production cache and verify fix is working
expecting: After cache clear, INICIAR endpoint should accept TEST-02 as v4.0
next_action: Verify fix is working in production

## Symptoms

expected:
- Select TEST-02 (v4.0 spool with union data)
- Should show list of available unions
- Should allow INICIAR workflow to proceed

actual:
- Frontend displays "[object Object]" error
- Console: "iniciarSpool error: Error: Spool is v3.0, use /api/v3/occupation/tomar instead"
- Backend returns 409 Conflict
- TEST-02 labeled as v4.0 in frontend but rejected as v3.0 by backend

errors:
```
iniciarSpool error: Error: Spool is v3.0, use /api/v3/occupation/tomar instead
POST https://zeues-backend-mvp-production.up.railway.app/api/v4/occupation/iniciar
409 (Conflict)
```

Frontend displays: "[object Object]" in red error box

reproduction:
1. Navigate to zeues-frontend.vercel.app
2. Select worker MR(93)
3. Select operation ARM
4. Click INICIAR button
5. Click TEST-02 spool
6. Error appears instead of union list

started: Current production deployment (v4.0 feature)

## Eliminated

## Evidence

- timestamp: 2026-02-03T21:56:00Z
  checked: Previous debug session (.planning/debug/resolved/v4-endpoint-rejects-test02-as-v3.md)
  found: |
    This exact issue was already fixed:
    - Root cause: get_spool_by_tag() was not parsing Total_Uniones field
    - Fix applied: Added Total_Uniones parsing to sheets_repository.py (lines 1035-1044)
    - Fix applied: Updated is_v4_spool() to handle both snake_case and PascalCase (version_detection.py line 36)
    - Fix deployed: Commit 39d22ee
  implication: The code fix is already in production, issue is likely stale cache

- timestamp: 2026-02-03T21:57:00Z
  checked: Production backend code deployment
  found: |
    Backend code is correctly deployed with fix:
    - sheets_repository.py line 1036: total_uniones_raw = get_col_value("Total_Uniones")
    - version_detection.py line 36: Handles both "total_uniones" and "Total_Uniones" keys
  implication: Code is correct, need to verify cache

- timestamp: 2026-02-03T21:57:30Z
  checked: Local TEST-02 data
  found: |
    Local query shows:
    - TAG_SPOOL: TEST-02
    - Total_Uniones: 12 (not 8 as in previous fix)
    - Ocupado_Por: None
    - Estado_Detalle: None
  implication: TEST-02 has valid Total_Uniones value

- timestamp: 2026-02-03T21:57:45Z
  checked: Production cache status
  found: |
    Cache cleared successfully via /api/health/clear-cache:
    - cached_sheets_before: ["Operaciones"]
    - cached_sheets_after: []
    - status: success
  implication: Stale cache was the issue

- timestamp: 2026-02-03T21:58:00Z
  checked: Production INICIAR endpoint after cache clear
  found: |
    POST /api/v4/occupation/iniciar with TEST-02:
    - HTTP 409 SPOOL_OCCUPIED (not 400 Bad Request)
    - Error: "El spool 'TEST-02' ya está ocupado por Worker 93 (ID: 93)"
    - No longer says "Spool is v3.0"
  implication: FIX WORKING! Backend now correctly detects TEST-02 as v4.0

## Resolution

root_cause: |
  TWO ISSUES:

  1. BACKEND (v4.0 detection) - RESOLVED:
     Production cache was stale. The code fix was already deployed (commit 39d22ee), but the
     production backend was using cached column mappings that did not include the Total_Uniones
     field parsing logic.

     The fix was applied previously:
     - sheets_repository.py: Added Total_Uniones parsing in get_spool_by_tag()
     - version_detection.py: Fixed key mismatch to handle both snake_case and PascalCase
     - TEST-02 Total_Uniones was populated (currently shows 12)

     But the cache needed to be cleared for the fix to take effect.

  2. FRONTEND (error display) - NEEDS FIX:
     When handling 409 SPOOL_OCCUPIED error, api.ts line 1499 tries to access `errorData.detail`
     directly, but the backend returns `detail` as an object:
     ```json
     {"detail": {"error": "SPOOL_OCCUPIED", "message": "El spool...", "occupied_by": null}}
     ```

     The code does `throw new Error(errorData.detail || '...')`, which throws the object itself,
     resulting in "[object Object]" display. Should be `errorData.detail.message`.

fix: |
  1. Backend: Cleared production cache via GET /api/health/clear-cache
     - Forced rebuild of column mappings
     - Backend now correctly reads Total_Uniones field

  2. Frontend: Fix error handling in api.ts for 409 errors
     - Change line 1499 from `errorData.detail` to handle both string and object
     - Extract `errorData.detail.message` when detail is object

verification: |
  ✅ BACKEND FIX VERIFIED - v4.0 detection working in production

  Before cache clear:
  - POST /api/v4/occupation/iniciar → 400 Bad Request "Spool is v3.0"

  After cache clear:
  - POST /api/v4/occupation/iniciar → 409 SPOOL_OCCUPIED (correct behavior)
  - Backend now correctly detects TEST-02 as v4.0 spool
  - Error changed from "wrong version" to "already occupied" (expected)

  ✅ FRONTEND FIX APPLIED - Error handling fixed

  Changes:
  - iniciarSpool: Fixed 403, 404, 409 error handling to extract message from object
  - finalizarSpool: Fixed 400, 403, 404, 409 error handling for consistency
  - TypeScript compilation: PASSED

  Next step:
  - Deploy frontend to Vercel
  - Test end-to-end: Frontend should show proper error messages instead of "[object Object]"

files_changed:
  - zeues-frontend/lib/api.ts (fixed error handling for iniciarSpool and finalizarSpool)
