# Phase 2 Gap Closure Plan

**Phase:** 02-core-location-tracking
**Created:** 2026-01-27
**Status:** Ready for execution

## Overview

Phase 2 implementation is 95% complete but has 2 critical gaps preventing the core location tracking from working. All the business logic, services, and endpoints exist but Redis is never connected, causing runtime failures.

## Gaps Identified

### Gap 1: Missing get_client() method (02-05-GAP-PLAN)
- **Issue:** dependency.py line 346 calls `redis_repo.get_client()` which doesn't exist
- **Impact:** AttributeError prevents RedisLockService instantiation
- **Fix:** Add get_client() method to RedisRepository

### Gap 2: Redis lifecycle not integrated (02-06-GAP-PLAN)
- **Issue:** FastAPI startup/shutdown events don't connect/disconnect Redis
- **Impact:** Redis client is always None, all lock operations fail
- **Fix:** Add Redis connection to startup_event(), disconnection to shutdown_event()

## Execution Strategy

Both gaps are in **Wave 5** and can be executed in parallel:

```
Wave 5 (parallel):
├── 02-05-GAP-PLAN: Fix get_client() method
└── 02-06-GAP-PLAN: Integrate Redis lifecycle
```

**Why parallel:** The fixes are independent:
- 02-05 adds a missing method to RedisRepository
- 02-06 adds Redis calls to main.py startup/shutdown
- Neither depends on the other's implementation

## Verification After Gap Closure

After executing both gap plans, verify Phase 2 completion:

1. **Start Redis locally:**
   ```bash
   docker run -d -p 6379:6379 redis:7-alpine
   ```

2. **Start the API:**
   ```bash
   cd backend
   source venv/bin/activate
   uvicorn main:app --reload
   ```

3. **Check Redis health:**
   ```bash
   curl http://localhost:8000/api/redis-health
   # Should show "operational": true
   ```

4. **Test TOMAR operation:**
   ```bash
   # First create test data in Google Sheets:
   # - Add a spool with TAG_SPOOL = "TEST-001" and Fecha_Materiales filled
   # - Add a worker with Id = 93, Nombre = "Test", Apellido = "Worker"

   curl -X POST http://localhost:8000/api/occupation/tomar \
     -H "Content-Type: application/json" \
     -d '{
       "worker_id": 93,
       "tag_spool": "TEST-001",
       "operacion": "ARM"
     }'
   ```

5. **Run race condition test:**
   ```bash
   cd backend
   pytest tests/integration/test_race_conditions.py::test_concurrent_tomar_prevents_double_booking -v
   # Should show 1 success, 9 conflicts (409 responses)
   ```

## Success Criteria

Phase 2 is complete when:

✅ Redis connects at API startup (see logs: "✅ Redis connected successfully")
✅ Redis health endpoint returns operational=true
✅ TOMAR endpoint doesn't throw AttributeError
✅ PAUSAR endpoint works for occupied spools
✅ COMPLETAR endpoint works and releases occupation
✅ Race condition test shows proper conflict handling (1 success, 9 conflicts)
✅ Metadata sheet has TOMAR/PAUSAR/COMPLETAR events logged

## Risk Mitigation

**Risk:** Production doesn't have Redis yet
**Mitigation:** Config defaults to localhost:6379, production will need REDIS_URL env var

**Risk:** Redis connection fails at startup
**Mitigation:** Non-blocking - API starts anyway, occupation endpoints return 503

**Risk:** Existing v2.1 functionality affected
**Mitigation:** Redis is isolated to occupation endpoints only - v2.1 endpoints unchanged

## Next Steps

1. Execute gap closure: `/gsd:execute-phase 2 --gaps-only`
2. Verify all 5 truths pass
3. Update 02-VERIFICATION.md with completion status
4. Move to Phase 3: State Machine & Collaboration

---
*Gap closure plan created: 2026-01-27*