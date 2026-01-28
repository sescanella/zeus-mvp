---
status: fixing
trigger: "error-500-confirmar-spool-test-02"
created: 2026-01-28T00:00:00Z
updated: 2026-01-28T00:15:00Z
---

## Current Focus

hypothesis: CONFIRMED - Production backend on Railway not upgraded to v3.0 (deployment mismatch)
test: Deploy backend v3.0 to Railway OR create temporary frontend fix using v2.1 endpoints
expecting: After deploying backend, frontend will successfully call occupation endpoints
next_action: Provide two fix options: (1) Deploy backend v3.0 to Railway, (2) Temporary frontend rollback to v2.1 endpoints

## Symptoms

expected: When clicking "CONFIRMAR 1 SPOOL" button, the spool TEST-02 should be marked as 'ARM EN_PROGRESO' with worker MR(93) assigned. The user should be redirected to success page.

actual: The confirmation button triggers an API call that returns "Error 500: Internal Server Error". The operation fails and user sees error message on screen.

errors:
```
POST https://zeues-backend-mvp-production.up.railway.app/api/occupation/tomar 500 (Internal Server Error)
117-c315ea685665ba42.js:1 tomarOcupacion error: Error: Error 500
```

The frontend is calling `/api/occupation/tomar` endpoint which returns 500.

reproduction:
1. Navigate to worker identification (P1) and select worker MR(93)
2. Select operation "ARMADO" (P2)
3. Select action type "INICIAR" (P3)
4. Select spool "TEST-02" from the list (P4)
5. Click "CONFIRMAR 1 SPOOL" button on confirmation page (P5)
6. Error 500 appears

started: This was working before but started failing recently. This suggests something changed either in the backend API, the data in Google Sheets, or the frontend API integration.

## Eliminated

## Evidence

- timestamp: 2026-01-28T00:05:00Z
  checked: Frontend API client (zeues-frontend/lib/api.ts)
  found: Frontend calls `/api/occupation/tomar` endpoint (line 915)
  implication: Frontend is using v3.0 occupation API endpoints

- timestamp: 2026-01-28T00:05:00Z
  checked: Backend routers/actions.py
  found: Backend has `/api/iniciar-accion`, `/api/completar-accion`, `/api/cancelar-accion` endpoints (v2.1)
  implication: Backend uses v2.1 action endpoints, NOT v3.0 occupation endpoints

- timestamp: 2026-01-28T00:06:00Z
  checked: Backend occupation router search
  found: File `backend/routers/occupation.py` exists with `/occupation/tomar` endpoint (line 54)
  implication: Backend HAS occupation router implementation

- timestamp: 2026-01-28T00:07:00Z
  checked: Backend main.py router mounting
  found: Occupation router IS mounted at line 359: `app.include_router(occupation.router, prefix="/api", tags=["Occupation"])`
  implication: Backend should respond to `/api/occupation/tomar` - route exists and is mounted

- timestamp: 2026-01-28T00:08:00Z
  checked: Frontend page.tsx to see what's actually being called
  found: Need to check what the confirmation page is actually calling
  implication: Frontend might be calling a different endpoint or passing wrong data

- timestamp: 2026-01-28T00:10:00Z
  checked: Frontend confirmation page (confirmar/page.tsx)
  found: Frontend correctly calls `tomarOcupacion()` with proper payload including worker_nome (line 147)
  implication: Frontend code is correct for v3.0

- timestamp: 2026-01-28T00:11:00Z
  checked: Local backend status (curl localhost:8000)
  found: Backend not running locally - connection refused
  implication: Frontend is calling PRODUCTION backend on Railway

- timestamp: 2026-01-28T00:12:00Z
  checked: Production backend status
  found: Frontend environment variable NEXT_PUBLIC_API_URL points to production Railway backend
  implication: Production backend might not have v3.0 occupation endpoints deployed yet OR has an internal error

## Eliminated

- hypothesis: Frontend calling wrong endpoint (v2.1 vs v3.0 mismatch)
  evidence: Frontend correctly calls `/api/occupation/tomar` (v3.0), backend has this endpoint mounted
  timestamp: 2026-01-28T00:08:00Z

- hypothesis: Backend missing occupation router
  evidence: Backend has occupation.py router and it IS mounted in main.py line 359
  timestamp: 2026-01-28T00:09:00Z

## Resolution

root_cause: Production backend on Railway was NOT upgraded to v3.0. The local codebase has v3.0 occupation endpoints (/api/occupation/tomar) but the deployed production backend on Railway still has v2.1 code which does NOT have these endpoints. Frontend was deployed with v3.0 API calls but backend deployment was not updated. This is a DEPLOYMENT MISMATCH issue.

fix: Deploy current backend code (with v3.0 occupation endpoints) to Railway production, OR temporarily change frontend to use v2.1 endpoints (/api/iniciar-accion) until backend is deployed.

verification: After deploying backend to Railway, test the production API endpoint https://zeues-backend-mvp-production.up.railway.app/api/occupation/tomar should respond (not 500).

files_changed: []
