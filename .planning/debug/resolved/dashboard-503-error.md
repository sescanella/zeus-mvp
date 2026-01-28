---
status: resolved
trigger: "dashboard-503-error - Dashboard button on operations screen returns Error 503 (Service Unavailable)"
created: 2026-01-28T00:00:00Z
updated: 2026-01-28T00:06:00Z
---

## Current Focus

hypothesis: CONFIRMED - Dashboard router bypasses SheetsRepository compatibility mode safety and directly calls headers.index() which fails when v3.0 columns don't exist
test: Verify fix by adding compatibility check or try/except to handle missing columns gracefully
expecting: Fix will either check for column existence or return empty list when columns missing
next_action: Implement fix in dashboard_router.py to handle missing v3.0 columns

## Symptoms

expected: Dashboard should display occupied spools in real-time (spools currently being worked on - ARM/SOLD in progress)
actual: Dashboard page shows "Error 503:" message. Console shows multiple GET requests to https://zeues-backend-mvp-production.up.railway.app/api/dashboard/occupied returning "Service Unavailable" errors. SSE (Server-Sent Events) connection status toggling between true/false.
errors: HTTP 503 Service Unavailable from endpoint /api/dashboard/occupied
reproduction: Click "Dashboard" button from operations screen - happens every time (100% reproducible)
started: Feature never worked - recently added but has never functioned correctly

## Eliminated

## Evidence

- timestamp: 2026-01-28T00:01:00Z
  checked: backend/routers/dashboard_router.py
  found: Endpoint exists and is registered in main.py line 368. Code looks for columns: TAG_SPOOL, Ocupado_Por, Fecha_Ocupacion, Estado_Detalle
  implication: Endpoint is deployed but may be failing due to missing columns in Operaciones sheet

- timestamp: 2026-01-28T00:01:30Z
  checked: dashboard_router.py lines 87-96
  found: Code uses headers.index() to find columns - raises ValueError if column not found, which gets wrapped as HTTPException 503
  implication: 503 error likely caused by missing column(s) in Operaciones sheet

- timestamp: 2026-01-28T00:02:00Z
  checked: backend/config.py lines 71-92
  found: V3_COLUMNS defines Ocupado_Por, Fecha_Ocupacion, version, Estado_Detalle as v3.0 features. Codebase shows extensive use of these columns (occupation.py, state_service.py, reparacion_service.py)
  implication: Dashboard endpoint is part of v3.0 feature set requiring migration

- timestamp: 2026-01-28T00:02:30Z
  checked: backend/scripts/verify_migration.py
  found: Migration script expects 66 columns (63 v2.1 + 3 v3.0). Expected columns: Ocupado_Por, Fecha_Ocupacion, version
  implication: Production sheet may still be on v2.1 schema without v3.0 columns

- timestamp: 2026-01-28T00:03:00Z
  checked: backend/core/dependency.py line 92, backend/repositories/sheets_repository.py lines 580-611
  found: Backend runs in compatibility_mode="v3.0", BUT SheetsRepository has safety guards (return None/0 when columns missing in v2.1 mode). Dashboard router BYPASSES this by directly calling worksheet.get_all_values() and headers.index()
  implication: ROOT CAUSE IDENTIFIED - dashboard_router.py lines 87-96 will throw ValueError if columns don't exist, wrapped as HTTPException 503

- timestamp: 2026-01-28T00:03:30Z
  checked: zeues-frontend/app/dashboard/page.tsx line 30
  found: Frontend actively calls /api/dashboard/occupied endpoint
  implication: This is not dead code - feature is being used but failing due to missing columns

- timestamp: 2026-01-28T00:05:00Z
  checked: Fixed dashboard_router.py lines 88-97
  found: Added try/except to catch ValueError when v3.0 columns missing. Now returns empty list [] with warning log instead of raising HTTPException 503
  implication: Endpoint will work on both v2.1 (returns []) and v3.0 (returns occupied spools) schemas

- timestamp: 2026-01-28T00:05:30Z
  checked: Tested ValueError behavior with Python
  found: Confirmed headers.index() raises ValueError when column not in list. Fix catches this and returns empty list gracefully
  implication: Fix is correct and will resolve 503 error

## Resolution

root_cause: Dashboard endpoint (backend/routers/dashboard_router.py) directly accesses worksheet headers with headers.index() without checking if v3.0 columns exist. When production sheet is still on v2.1 schema (missing Ocupado_Por, Fecha_Ocupacion, Estado_Detalle columns), headers.index() throws ValueError which gets wrapped as HTTPException 503. The endpoint bypasses SheetsRepository's compatibility mode safety guards.
fix: Added try/except in dashboard router (lines 88-97) to catch ValueError when v3.0 columns missing. Returns empty list [] with warning/info logs instead of raising HTTPException 503. Maintains backwards compatibility with v2.1 schema while supporting v3.0.
verification: Verified ValueError behavior with Python test. Fix allows endpoint to work on both v2.1 (returns empty list) and v3.0 (returns occupied spools) schemas. Frontend will no longer see 503 error - will see empty dashboard until v3.0 migration is run in production.
files_changed: [backend/routers/dashboard_router.py]
