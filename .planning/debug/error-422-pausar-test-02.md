---
status: fixing
trigger: "Investigate and debug the Error 422 that occurs when attempting to PAUSAR the spool TEST-02 in the ZEUES v3.0 frontend application."
created: 2026-01-30T00:00:00Z
updated: 2026-01-30T00:00:01Z
---

## Current Focus

hypothesis: Fix implemented - Added operacion field to PausarRequest interface and updated all callers
test: TypeScript validation and build test
expecting: No TypeScript errors, build succeeds
next_action: Verify fix by testing PAUSAR operation on TEST-02

## Symptoms

expected: User can PAUSAR ARM operation on spool TEST-02 successfully
actual: Error 422 (Unprocessable Content) returned from POST /api/occupation/pausar
errors:
- Frontend: "ERROR Error 422:"
- Browser console: "POST /api/occupation/pausar returned 422 (Unprocessable Content)"
- Frontend handler: "pausarOcupacion error: Error 422:"
reproduction:
1. Navigate to zeues-frontend.vercel.app/confirmar?tipo=pausar
2. Attempt to PAUSAR ARM operation on spool TEST-02
3. Observe 422 error
started: After recent backend deployment (commit 6748fd1 added `operacion` field to PausarRequest)

## Eliminated

(none - root cause confirmed on first hypothesis)

## Evidence

- timestamp: 2026-01-30T00:00:00Z
  checked: backend/models/occupation.py (PausarRequest model)
  found: PausarRequest has REQUIRED `operacion: ActionType` field (line 79-82)
  implication: Backend expects operacion field in request body

- timestamp: 2026-01-30T00:00:00Z
  checked: backend/routers/occupation.py (pausar endpoint)
  found: Endpoint uses PausarRequest model for validation (line 149)
  implication: Any missing required field will return 422 Unprocessable Entity

- timestamp: 2026-01-30T00:00:00Z
  checked: Recent commits context
  found: Commit 6748fd1 "Added `operacion` field to `PausarRequest` model"
  implication: This is a recent breaking change - frontend not updated yet

- timestamp: 2026-01-30T00:00:01Z
  checked: zeues-frontend/lib/types.ts (PausarRequest interface)
  found: TypeScript PausarRequest interface (line 114-118) has ONLY 3 fields: tag_spool, worker_id, worker_nombre - NO operacion field
  implication: Frontend request payload is missing required field, causing Pydantic validation to fail with 422

- timestamp: 2026-01-30T00:00:01Z
  checked: zeues-frontend/lib/api.ts (pausarOcupacion function)
  found: Function serializes PausarRequest as-is with JSON.stringify(request) (line 1055)
  implication: Function sends whatever fields are in PausarRequest type - missing operacion

- timestamp: 2026-01-30T00:00:01Z
  checked: Backend commit 6748fd1
  found: Backend added operacion to PausarRequest but frontend types NOT updated
  implication: Frontend-backend contract is BROKEN - frontend must be updated to match backend schema

## Resolution

root_cause: |
  Backend PausarRequest model was updated to REQUIRE `operacion: ActionType` field (commit 6748fd1),
  but frontend TypeScript PausarRequest interface was NOT updated. Frontend is sending payload with
  only {tag_spool, worker_id, worker_nombre}, missing the required `operacion` field.

  Pydantic validation in FastAPI rejects the request with 422 Unprocessable Entity because
  required field is missing.

fix: |
  IMPLEMENTED ✅
  1. Added `operacion: 'ARM' | 'SOLD' | 'METROLOGIA' | 'REPARACION'` to PausarRequest interface
     File: zeues-frontend/lib/types.ts (line 123)
  2. Updated batch PAUSAR to pass operacion field
     File: zeues-frontend/app/confirmar/page.tsx (line 144)
  3. Updated single PAUSAR to pass operacion field
     File: zeues-frontend/app/confirmar/page.tsx (line 292)

  TypeScript validation: ✅ PASSED (npx tsc --noEmit)

verification: |
  READY FOR TESTING
  1. Deploy frontend changes to vercel (or test locally)
  2. Navigate to zeues-frontend.vercel.app
  3. Attempt to PAUSAR ARM operation on spool TEST-02
  4. Expected: 200 OK response, spool estado_detalle = "ARM parcial (pausado)"
  5. Verify Redis lock is released
  6. Verify Metadata sheet has PAUSAR_ARM event

files_changed:
  - zeues-frontend/lib/types.ts
  - zeues-frontend/app/confirmar/page.tsx
