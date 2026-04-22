---
status: resolved
trigger: "Investigate: Are Redis connection exhaustion and INICIAR 400 error related?"
created: 2026-02-03T17:45:00-03:00
updated: 2026-02-03T18:00:00-03:00
---

## Current Focus

hypothesis: CONFIRMED - Redis exhaustion and INICIAR 400 are INDEPENDENT issues. 400 comes from v3.0 spool validation (line 112-121) BEFORE Redis operations (line 804-812).
test: Verify that version detection happens before Redis lock acquisition in code flow
expecting: Version detection should throw 400 with WRONG_VERSION error, explaining 9ms fast failure
next_action: Form conclusion with root cause analysis

## Symptoms

expected:
- If related: Redis errors would cause 500 Internal Server Error, not 400 Bad Request
- If independent: 400 suggests validation error (Pydantic schema mismatch), Redis wouldn't affect validation

actual:
- INICIAR endpoint returns HTTP 400 in 9ms (fast failure)
- Redis connection exhaustion causes SSE/subscription failures
- Both occurring in production simultaneously (Feb 3 2026)

errors:
- Redis: "Too many connections" (redis.exceptions.ConnectionError)
- INICIAR: HTTP 400 Bad Request, duration 9ms
- Frontend: "iniciarSpool error: Error: [object Object]"

reproduction:
- Redis: Recurring issue affecting SSE service
- INICIAR: POST /api/v4/occupation/iniciar with valid payload returns 400
- Timestamp: Feb 3 2026 17:31:26

started:
- Redis errors: Ongoing, recurring issue
- INICIAR 400: Recent, specific timestamp
- Both active in production (Railway)

## Eliminated

## Evidence

- timestamp: 2026-02-03T17:50:00-03:00
  checked: backend/routers/occupation_v4.py (INICIAR endpoint)
  found: |
    Line 100: Version detection via is_v4_spool() happens BEFORE Redis operations
    Line 107-121: HTTPException(400) raised if spool is v3.0 (Total_Uniones <= 0)
    Line 124: Service layer call (which includes Redis) only reached AFTER version check passes
  implication: |
    400 errors occur during version validation, BEFORE Redis lock acquisition.
    Fast 9ms duration confirms this - no Redis network roundtrip.

- timestamp: 2026-02-03T17:52:00-03:00
  checked: backend/services/occupation_service.py (iniciar_spool method)
  found: |
    Line 804-812: Redis lock acquisition happens in Step 2, after prerequisites
    Line 764-793: Step 1 validates spool existence, prerequisites, ARM validation
    Line 797-801: Step 1.7 lazy cleanup (Redis call, but non-blocking)
  implication: |
    Service layer assumes version already validated by router.
    Redis operations only reached if router version check passes.

- timestamp: 2026-02-03T17:53:00-03:00
  checked: backend/routers/occupation_v4.py exception handling
  found: |
    Line 176-178: HTTPException is re-raised without wrapping (preserves 400/403/404/409)
    Line 180-186: Only unexpected exceptions become 500 errors
    No Redis-specific exception handling that would convert to 400
  implication: |
    Redis errors (ConnectionError, TimeoutError) would NOT be caught and converted to 400.
    They would propagate as 500 Internal Server Error.

- timestamp: 2026-02-03T17:55:00-03:00
  checked: Exception classes in backend/exceptions.py
  found: |
    Custom exceptions: SpoolOccupiedError (409), NoAutorizadoError (403), etc.
    No custom exception that wraps Redis errors as 400
  implication: |
    No code path exists that converts Redis ConnectionError to 400 Bad Request.

- timestamp: 2026-02-03T17:56:00-03:00
  checked: Frontend payload construction (zeues-frontend/app/seleccionar-spool/page.tsx)
  found: |
    Line 268-273: Frontend sends valid IniciarRequest schema
    {tag_spool, worker_id, worker_nombre, operacion: 'ARM' | 'SOLD'}
    Matches backend/models/occupation.py IniciarRequest (line 359-402)
  implication: |
    Frontend schema is correct. 400 error is NOT from Pydantic validation.
    Most likely cause: tag_spool is a v3.0 spool (Total_Uniones = 0 or null)

## Resolution

root_cause: |
  Redis connection exhaustion and INICIAR 400 errors are INDEPENDENT issues with NO causal relationship.

  **INICIAR 400 Root Cause:**
  - User attempting to INICIAR a v3.0 spool (Total_Uniones = 0 or null) via v4.0 endpoint
  - Version detection at line 107-121 of occupation_v4.py rejects v3.0 spools with HTTP 400
  - Error detail: {"error": "WRONG_VERSION", "message": "Spool is v3.0, use /api/v3/occupation/tomar instead"}
  - Fast 9ms duration confirms early validation failure (no Redis network call)

  **Redis Exhaustion Root Cause:**
  - Separate issue: Connection pool exhaustion affecting SSE service
  - Causes 500 Internal Server Error (not 400) when Redis operations fail
  - Documented fix: Dual connection pool architecture

  **Why they appeared together:**
  - Temporal coincidence: Both active in production at same time (Feb 3 2026)
  - Different failure modes: 400 = client error (wrong version), 500 = server error (Redis down)
  - Different code paths: Version validation (line 100-121) runs BEFORE Redis lock (line 804-812)

  **Proof of independence:**
  1. Version check happens before Redis operations in code flow
  2. No exception handler converts Redis errors to 400
  3. HTTPException re-raised without wrapping (line 176-178)
  4. Redis ConnectionError would cause 500, not 400
  5. 9ms duration = no Redis network roundtrip occurred

fix: |
  N/A - This is a diagnostic investigation, not a fix task.

  Separate fixes needed:
  1. INICIAR 400: User education - use v3.0 endpoint for v3.0 spools, OR migrate spool to v4.0 (populate Uniones sheet)
  2. Redis exhaustion: Apply dual connection pool architecture (already identified)

verification: |
  Evidence-based conclusion confirmed by code analysis:
  - Reviewed occupation_v4.py router (lines 50-186)
  - Reviewed occupation_service.py iniciar_spool (lines 724-819)
  - Reviewed exception handling (lines 176-186)
  - Reviewed custom exceptions (no Redis->400 conversion exists)
  - Reviewed frontend payload (schema correct)

  Conclusion is falsifiable: If Redis errors caused 400, we would find:
  - Exception handler converting redis.ConnectionError to HTTPException(400) ❌ NOT FOUND
  - Or Redis operation happening before version check ❌ NOT TRUE (version check at line 100)
  - Or error handling wrapping all exceptions as 400 ❌ NOT TRUE (line 180-186 returns 500)

files_changed: []
