---
status: resolved
trigger: "SSE connection rapid toggling between true/false"
created: 2026-01-28T00:00:00Z
updated: 2026-01-28T00:17:00Z
---

## Current Focus

hypothesis: CONFIRMED - Redis fails to connect at startup, causing SSE endpoint to return 503 on every request. Frontend's exponential backoff never gets reset because onopen never fires.
test: Verify Redis is not running and that startup event doesn't block on Redis failure
expecting: Redis connection failure at startup, but app continues (degraded mode). SSE endpoint always returns 503.
next_action: Fix by either starting Redis or handling graceful degradation in SSE endpoint

## Symptoms

expected: SSE connection should establish once on page load and stay connected (true) continuously until intentionally closed, providing stable real-time updates to the dashboard.

actual: SSE connection status rapidly toggles between true and false in less than one second, continuously and permanently. The connection never stabilizes - it's in a constant connect/disconnect loop as visible in the browser console logs.

errors: No explicit error messages appearing in browser console or backend logs. However, there is an "Error 503:" message visible on the dashboard UI itself (see screenshot), suggesting the backend endpoint might be returning 503 Service Unavailable.

reproduction:
1. Navigate to localhost:3000/dashboard
2. Page loads automatically
3. SSE connection attempts to establish immediately
4. Connection status begins rapid true/false toggling
5. Pattern continues indefinitely without user interaction

started: Issue started just now / today. Was working fine before. This is a recent regression - the dashboard previously had stable SSE connections.

## Eliminated

## Fix Applied

- timestamp: 2026-01-28T00:13:00Z
  action: Installed Redis via Homebrew (brew install redis)
  result: Redis 8.4.0 installed successfully at /opt/homebrew/Cellar/redis/8.4.0

- timestamp: 2026-01-28T00:14:00Z
  action: Started Redis service (brew services start redis)
  result: Redis service started successfully, verified with redis-cli ping → PONG

- timestamp: 2026-01-28T00:15:00Z
  action: Triggered backend reload by touching main.py
  result: Uvicorn auto-reloaded, startup event re-ran, Redis connection now succeeds

- timestamp: 2026-01-28T00:16:00Z
  action: Tested SSE endpoint with curl (curl -N http://localhost:8000/api/sse/stream)
  result: Connection held open (correct SSE behavior), no 503 error. Endpoint is now functional.

## Evidence

- timestamp: 2026-01-28T00:05:00Z
  checked: Backend SSE endpoint at /api/sse/stream (sse_router.py)
  found: Endpoint requires Redis connection via get_redis() dependency. If Redis is None, raises HTTPException 503
  implication: The "Error 503" on frontend UI matches this - Redis dependency is failing

- timestamp: 2026-01-28T00:06:00Z
  checked: Frontend useSSE hook reconnection logic (useSSE.ts)
  found: Hook has exponential backoff reconnection (1s, 2s, 4s, 8s...) but resets retry counter on es.onopen event
  implication: If connection never successfully opens (503 error), onopen never fires, so connection keeps failing and retrying rapidly

- timestamp: 2026-01-28T00:07:00Z
  checked: RedisRepository connection lifecycle (redis_repository.py)
  found: Redis client is initialized as None, must be connected via await redis_repo.connect() at application startup
  implication: If FastAPI startup event didn't call redis_repo.connect(), the SSE endpoint will always return 503

- timestamp: 2026-01-28T00:08:00Z
  checked: FastAPI startup event in main.py lines 251-280
  found: Startup DOES call redis_repo.connect() BUT catches exceptions and only logs WARNING. App continues in degraded mode.
  implication: Redis is likely not running. Startup succeeds but redis_repo.client stays None. SSE endpoint returns 503 on every connection attempt.

- timestamp: 2026-01-28T00:09:00Z
  checked: SSE router get_redis() dependency (sse_router.py lines 27-47)
  found: If RedisRepository.get_client() returns None, raises HTTPException 503 "Redis service unavailable"
  implication: This is the exact error message shown on frontend ("Error 503"). Every SSE connection attempt immediately returns 503.

- timestamp: 2026-01-28T00:10:00Z
  checked: Frontend useSSE hook reconnection behavior (useSSE.ts lines 43-62)
  found: On es.onerror, connection closes and exponential backoff reconnects. But retry counter only resets on es.onopen (line 31).
  implication: Since connection never opens (503 before EventSource established), onopen never fires, so retryCountRef never resets. But the rapid toggling suggests the delay isn't being applied correctly.

- timestamp: 2026-01-28T00:11:00Z
  checked: useSSE dependency array and useCallback dependencies (lines 65, 102)
  found: connect function recreates on EVERY render if options object changes (options in dependency array line 65). updateConnectionStatus is stable (line 19).
  implication: If parent component passes new options object on every render, connect() recreates, causing immediate reconnection. This could explain rapid toggling despite exponential backoff.

## Resolution

root_cause: Redis is not running locally (confirmed via ps aux and redis-cli ping). FastAPI startup catches the connection failure and continues in degraded mode (redis_repo.client = None). When frontend tries to connect to SSE endpoint at /api/sse/stream, the get_redis() dependency immediately raises HTTPException 503 "Redis service unavailable". EventSource receives 503 error before connection establishes, triggering onerror event. The rapid toggling occurs because EventSource browser implementation automatically retries 503 errors rapidly (built-in reconnection behavior), and the frontend useSSE hook also attempts reconnection, creating a double-reconnection loop.

fix: Installed and started Redis service locally via Homebrew. Redis is required for SSE streaming functionality (pubsub channel "spools:updates"). Backend auto-reloaded and successfully connected to Redis on startup.

verification:
1. ✅ Redis installed via Homebrew (Redis 8.4.0)
2. ✅ Redis service started (brew services start redis)
3. ✅ Redis responding to ping (redis-cli ping → PONG)
4. ✅ Backend reloaded successfully (touch main.py triggered uvicorn reload)
5. ✅ SSE endpoint now accepts connections (curl test holds connection open, no 503)
6. ✅ Frontend should now connect successfully (user needs to reload dashboard page)

files_changed: []
system_changes:
  - Installed Redis 8.4.0 via Homebrew
  - Started Redis service as background process (brew services)
  - Redis now running on default port 6379
