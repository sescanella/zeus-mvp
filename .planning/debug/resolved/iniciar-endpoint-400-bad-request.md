---
status: resolved
trigger: "v4.0 INICIAR endpoint returning HTTP 400 Bad Request. Frontend showing 'iniciarSpool error: Error: [object Object]'"
created: 2026-02-03T17:31:26Z
updated: 2026-02-03T21:07:00Z
---

## Current Focus

hypothesis: VERIFIED - Fixes implemented successfully
test: Manual verification in production
expecting: v3.0 spools filtered from INICIAR workflow, error messages readable
next_action: Deploy to production and verify user experience

## Symptoms

expected:
- POST /api/v4/occupation/iniciar should accept valid payload and return success
- Frontend should receive proper response and show success page
- Endpoint should occupy spool without touching Uniones sheet

actual:
- HTTP 400 Bad Request error
- Timestamp: Feb 3 2026 17:31:26
- Duration: 9ms (fast failure suggests validation error)
- Frontend error: "iniciarSpool error: Error: [object Object]" in /seleccionar-spool page
- Error object not properly serialized in frontend

errors:
```
HTTP 400 Bad Request
Endpoint: POST /api/v4/occupation/iniciar
Duration: 9ms
Frontend: iniciarSpool error: Error: [object Object]
Location: /seleccionar-spool
```

reproduction:
- Occurs in production (Railway + Vercel)
- Triggered when user tries to initiate spool from frontend
- Frontend sends request to /api/v4/occupation/iniciar

timeline:
- Currently happening in production
- v4.0 INICIAR endpoint is newly implemented
- According to CLAUDE.md, INICIAR is planned for v4.0 but may not be fully deployed
- Frontend may be calling endpoint that's not fully implemented

context:
- v4.0 endpoint definition (CLAUDE.md):
  - POST /api/iniciar - Occupies spool without touching Uniones
  - POST /api/finalizar - Union selection + auto PAUSAR/COMPLETAR
- Frontend location: zeues-frontend/app/seleccionar-spool (likely calling iniciarSpool function)
- Backend location: Likely backend/routers/union_router.py or backend/routers/occupation_router.py
- Pydantic schema validation may be rejecting payload
- 9ms duration suggests early validation failure, not business logic error

## Eliminated

## Evidence

- timestamp: 2026-02-03T21:04:45Z
  checked: Production INICIAR endpoint with TEST-01 spool
  found: HTTP 400 with detailed JSON error: {"error": "WRONG_VERSION", "message": "Spool is v3.0, use /api/v3/occupation/tomar instead", "spool_version": "v3.0", "correct_endpoint": "/api/v3/occupation/tomar", "total_uniones": 0}
  implication: Backend is correctly rejecting v3.0 spools (TEST-01 has total_uniones=0). The error is NOT a schema validation issue - it's business logic validation working as designed.

- timestamp: 2026-02-03T21:04:45Z
  checked: Frontend error handling in api.ts iniciarSpool() (lines 1469-1502)
  found: Line 1478-1481 catches HTTP 400 and extracts errorData.detail, but the detail is an object not a string
  implication: Frontend is receiving the full error object {"error": "WRONG_VERSION", ...} but trying to display it as a string, resulting in "[object Object]"

- timestamp: 2026-02-03T21:04:45Z
  checked: Frontend spool selection logic in page.tsx (lines 262-284)
  found: Line 268 calls iniciarSpool() for accion=INICIAR, but doesn't check if spool is v4.0 before calling
  implication: Frontend is allowing users to select and attempt to INICIAR v3.0 spools, which the backend correctly rejects

## Resolution

root_cause:
**Two issues:**
1. Frontend filtering logic in page.tsx (lines 149-156) filters by occupation status but NOT by spool version, allowing v3.0 spools (total_uniones=0) to appear in INICIAR workflow
2. Frontend error handling in api.ts (line 1480) tries to display errorData.detail as string, but detail is an object {"error": "WRONG_VERSION", ...}, resulting in "[object Object]"

Backend is working correctly - v4.0 INICIAR endpoint properly rejects v3.0 spools with helpful error message.

fix:
1. ✅ zeues-frontend/app/seleccionar-spool/page.tsx (lines 149-159):
   - Added version filter: `spool.version === 'v4.0'`
   - INICIAR now only shows v4.0 spools (total_uniones > 0)
   - Updated comment to document v4.0 requirement

2. ✅ zeues-frontend/lib/api.ts (lines 1478-1484):
   - Fixed error message extraction for nested object responses
   - Handles both string and object detail formats
   - Extracts errorData.detail.message when detail is object (WRONG_VERSION case)
   - Falls back to generic message if structure unexpected

verification:
✅ Code quality checks:
- TypeScript compilation: PASSED (no errors)
- ESLint: PASSED (no warnings or errors)
- Production build: PASSED (successful build)

✅ Code review:
- Version filter logic: `isDisponible && isV4` correctly filters v3.0 spools
- Error message extraction: Handles both string and object detail formats
- No breaking changes to existing v3.0 workflows (tipo-based navigation unchanged)

⏳ Production verification needed:
1. Navigate to P3 (tipo-interaccion) with ARM operation
2. Click INICIAR button
3. Verify spool selection page shows ONLY v4.0 spools (TEST-02, not TEST-01)
4. Select TEST-02 and click CONTINUAR
5. Verify navigation to success page (no error)
6. If TEST-01 somehow appears and is selected, verify error message is readable (not "[object Object]")

files_changed:
- zeues-frontend/app/seleccionar-spool/page.tsx
- zeues-frontend/lib/api.ts
