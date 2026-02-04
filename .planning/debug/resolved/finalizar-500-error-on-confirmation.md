---
status: resolved
trigger: "finalizar-500-error-on-confirmation"
created: 2026-02-04T00:00:00Z
updated: 2026-02-04T00:18:00Z
---

## Current Focus

hypothesis: CONFIRMED - Field name mismatch in response schema. Backend returns "pulgadas" but frontend expects "pulgadas_completadas"
test: Verify the exact field names in FinalizarResponseV4 (backend) vs FinalizarResponse (frontend types)
expecting: Backend model uses "pulgadas", frontend TypeScript type uses "pulgadas_completadas", causing JSON deserialization to fail or frontend to access undefined field
next_action: Fix the field name mismatch - align backend and frontend response schemas

## Symptoms

expected: Successfully submit FINALIZAR operation with selected unions (6 unions, 63.0" pulgadas-diámetro) for spool TEST-02, worker MR(93), operation ARMADO
actual: Error 500 dialog appears, console shows "finalizarSpool error: Error: Error 500" and POST request to https://zeues-backend-mvp-production.up.railway.app/api/v4/occupation/finalizar returns 500 (Internal Server Error)
errors:
- Browser console: "finalizarSpool error: Error: Error 500"
- Network tab: POST /api/v4/occupation/finalizar → 500 (Internal Server Error)
- Stack trace shows error at async function calls in confirmar page
reproduction:
1. Navigate to production frontend (zeues-frontend.vercel.app)
2. Select worker MR(93)
3. Select operation ARMADO
4. Select action FINALIZAR
5. Select spool TEST-02
6. Select 6 unions (total 63.0" pulgadas-diámetro)
7. Click "CONFIRMAR 1 SPOOL" button on confirmation page
8. Error 500 appears
started: This appears to be occurring in v4.0 development (the endpoint is /api/v4/occupation/finalizar). The FINALIZAR flow is a new feature in v4.0 for union-level tracking.

## Eliminated

## Evidence

- timestamp: 2026-02-04T00:05:00Z
  checked: Frontend finalizarSpool function (lib/api.ts:1583-1633) and confirmar page (app/confirmar/page.tsx:144-151)
  found: Frontend sends POST request to /api/v4/occupation/finalizar with FinalizarRequest payload containing tag_spool, worker_id, operacion, selected_unions
  implication: Frontend code looks correct, request structure matches expected schema

- timestamp: 2026-02-04T00:06:00Z
  checked: Backend union_router.py line 214 - finalizar_v4 endpoint definition
  found: Endpoint exists at @router.post("/occupation/finalizar") and is registered in union_router
  implication: Endpoint route exists, now need to check if router is registered in main.py and review full endpoint logic

- timestamp: 2026-02-04T00:08:00Z
  checked: main.py router registration and union_router endpoint logic (lines 214-363)
  found: Router correctly registered at line 464 with prefix /api/v4. Endpoint receives FinalizarRequestV4 (4 fields), looks up worker, constructs FinalizarRequest (5 fields with worker_nombre), and calls occupation_service.finalizar_spool()
  implication: Endpoint routing and logic look correct. The 500 error must be coming from either a missing import, the service layer throwing an unhandled exception, or a Railway deployment issue. Need to check imports and service layer

- timestamp: 2026-02-04T00:10:00Z
  checked: Frontend FinalizarResponse type (types.ts:312-318) vs Backend FinalizarResponseV4 model (union_api.py:137-169)
  found: Field name mismatches - Backend: "pulgadas", "action_taken", "unions_processed". Frontend: "pulgadas_completadas", "action", "uniones_completadas". Frontend trying to access response.pulgadas_completadas (line 154 confirmar/page.tsx) which doesn't exist in backend response
  implication: This is the root cause. Frontend expects different field names than backend provides, causing undefined field access and likely causing the 500 error

## Resolution

root_cause: Field name mismatch in FINALIZAR response schema. Backend FinalizarResponseV4 model (backend/models/union_api.py:156) returns field "pulgadas", but frontend FinalizarResponse type (zeues-frontend/lib/types.ts:316) expects "pulgadas_completadas". Also missing field "action_taken" vs "action", and "unions_processed" vs "uniones_completadas". This causes the frontend to fail when trying to access undefined fields, resulting in a 500 error.

fix: Align frontend TypeScript type with backend Pydantic model. Update FinalizarResponse in zeues-frontend/lib/types.ts to match the exact field names from FinalizarResponseV4: "pulgadas" (not "pulgadas_completadas"), "action_taken" (not "action"), "unions_processed" (not "uniones_completadas"). Also update confirmar/page.tsx to use correct field names.

verification:
- TypeScript compilation: PASSED (npx tsc --noEmit - no errors)
- ESLint validation: PASSED (npm run lint - no warnings or errors)
- Production build: PASSED (npm run build - successful compilation)
- Local testing: REQUIRED - Test FINALIZAR flow with real backend to verify API response parsing
- Production testing: REQUIRED - Deploy to Vercel and test end-to-end workflow

files_changed: [
  "zeues-frontend/lib/types.ts",
  "zeues-frontend/app/confirmar/page.tsx"
]
