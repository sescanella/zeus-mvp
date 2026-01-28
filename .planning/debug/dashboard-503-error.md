---
status: investigating
trigger: "dashboard-503-error - Error 503 when accessing /dashboard page - SSE connection rapidly toggling true/false"
created: 2026-01-28T00:00:00Z
updated: 2026-01-28T00:00:00Z
---

## Current Focus

hypothesis: Backend /api/dashboard/occupied endpoint is failing or missing, causing 503 error. SSE instability may be secondary issue or consequence.
test: Check if /api/dashboard/occupied endpoint exists in backend and inspect its implementation
expecting: Either endpoint is missing, or it has a bug causing 503 response
next_action: Read backend router files to find dashboard endpoint implementation

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

## Resolution

root_cause:
fix:
verification:
files_changed: []
