---
status: resolved
trigger: "dashboard-503-error - Error 503 when accessing /dashboard page - SSE connection rapidly toggling true/false"
created: 2026-01-28T00:00:00Z
updated: 2026-01-28T00:20:00Z
---

## Current Focus

hypothesis: CONFIRMED - dashboard_router.py calls worksheet.get_all_values() on list object instead of gspread Worksheet
test: Fix dashboard_router.py to use the list returned by read_worksheet directly (no get_all_values call)
expecting: Dashboard will load occupied spools without 503 error
next_action: Fix dashboard_router.py line 73-76 to remove get_all_values() call

## Symptoms

expected: Dashboard should display occupied spools with worker names, estado_detalle, and time occupied. Should show "No hay carretes ocupados actualmente" if no spools are occupied.

actual: Page shows "Error 503" in red text. Browser console shows SSE connection status messages rapidly alternating between true and false (connection is unstable).

errors:
- Error 503 displayed on page
- Frontend calls GET /api/dashboard/occupied (line 30 of zeues-frontend/app/dashboard/page.tsx)
- SSE connection to /api/sse/stream is unstable (toggling connection status)

reproduction:
1. Navigate to https://zeues-frontend.vercel.app/dashboard
2. Error 503 appears immediately
3. Console shows rapid SSE connection status toggling

started: Error has existed since the dashboard was first implemented. Never worked correctly. Backend is Railway production (https://zeues-backend-mvp-production.up.railway.app).

additional_context:
- Frontend code at zeues-frontend/app/dashboard/page.tsx calls:
  - GET ${process.env.NEXT_PUBLIC_API_URL}/api/dashboard/occupied (line 30)
  - SSE stream at ${process.env.NEXT_PUBLIC_API_URL}/api/sse/stream (line 87)
- Expected response: Array of OccupiedSpool objects with {tag_spool, worker_nombre, estado_detalle, fecha_ocupacion}
- Dashboard uses SSE for real-time updates (useSSE hook)
- ConnectionStatus component shows SSE connection state

## Eliminated

## Evidence

- timestamp: 2026-01-28T00:05:00Z
  checked: Backend dashboard_router.py implementation (lines 69-145)
  found: Endpoint exists and handles v3.0 columns (Ocupado_Por, Fecha_Ocupacion, Estado_Detalle). Returns empty array if v3.0 columns missing (line 87-97). Raises HTTPException 503 on any unexpected error (line 142-145).
  implication: 503 error likely caused by either: (1) v3.0 columns don't exist in sheet (returns empty array, NOT 503), OR (2) unexpected exception during sheet read (line 140-145)

- timestamp: 2026-01-28T00:06:00Z
  checked: SSE router implementation (sse_router.py lines 50-100)
  found: SSE endpoint /api/sse/stream requires Redis connection. get_redis() dependency raises HTTPException 503 if Redis is None (lines 40-45). SSE stream uses event_generator with keep-alive ping every 15s.
  implication: SSE connection instability likely caused by Redis being unavailable or flaky on Railway production

- timestamp: 2026-01-28T00:07:00Z
  checked: Frontend useSSE hook (useSSE.ts)
  found: Hook implements exponential backoff retry (max 10 retries, max 30s delay). onopen sets connected=true, onerror sets connected=false and retries. Page visibility API closes/reopens connection when page hidden/visible.
  implication: Rapid toggling suggests SSE connection is repeatedly failing and retrying quickly (early in exponential backoff sequence)

- timestamp: 2026-01-28T00:10:00Z
  checked: Production endpoint curl test
  found: GET /api/dashboard/occupied returns: {"detail":"Failed to read occupied spools: 'list' object has no attribute 'get_all_values'"}
  implication: Root cause identified - dashboard_router.py is calling .get_all_values() on a list instead of a worksheet

- timestamp: 2026-01-28T00:12:00Z
  checked: sheets_repository.py read_worksheet method signature (line 158)
  found: read_worksheet() returns list[list] directly (already calls get_all_values internally at line 188 and returns result at line 201)
  implication: dashboard_router.py line 73 should NOT call worksheet.get_all_values() because worksheet IS already the list. Should use it directly as all_data.

## Resolution

root_cause: dashboard_router.py line 73-76 incorrectly calls worksheet.get_all_values() on a list object. SheetsRepository.read_worksheet() already returns list[list] (calls get_all_values internally), so the router should use this list directly as all_data, not call get_all_values() again.

fix: Removed .get_all_values() call on line 76. Changed from:
  worksheet = sheets_repo.read_worksheet(config.HOJA_OPERACIONES_NOMBRE)
  all_data = worksheet.get_all_values()
To:
  all_data = sheets_repo.read_worksheet(config.HOJA_OPERACIONES_NOMBRE)

verification:
- ✅ dashboard_router.py imports successfully (syntax check passed)
- ✅ Endpoint /api/dashboard/occupied registered correctly
- ⏳ Needs production deployment to verify 503 error resolved
- ⏳ Needs verification that SSE connection stabilizes after dashboard loads

files_changed:
- backend/routers/dashboard_router.py (lines 72-76: removed intermediate worksheet variable and .get_all_values() call)

root_cause:
fix:
verification:
files_changed: []
