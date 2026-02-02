<objective>
Execute Phase 2 of the Redis Crisis Recovery Plan: Implement permanent Redis connection pooling and health monitoring fixes.

**Context:** Phase 1 has successfully restored Redis service via restart and validated that basic operations work. E2E tests now pass at ≥75% (6+/8). However, the root cause (connection pool exhaustion) has not been fixed. Without proper connection management, the "Too many connections" error will reoccur within hours or days.

**This phase implements the permanent fix** to prevent future Redis connection exhaustion by:
1. Implementing connection pool singleton pattern
2. Fixing connection leaks in Redis repository
3. Updating health check to include Redis status
4. Adding connection monitoring and logging

This is a **P1 High Priority** task that must be completed within the week to ensure v3.0 production stability.
</objective>

<context>
**Prerequisites (verified in Phase 1):**
- Redis is healthy and operational
- E2E tests pass at ≥75% success rate
- Production is stable for 2+ hours post-restart

**Current Problem:**
- Backend not properly managing Redis connections
- No connection pooling (creating new connections per request)
- Possible connection leaks in error handlers
- Railway Redis connection limit (20-30) exceeded by production traffic (30-50 workers + SSE streams)

**Root Cause Evidence:**
From Phase 1 testing, Redis health endpoint returned "Too many connections" error, indicating connection pool exhaustion.

**Files to Modify:**
@backend/config.py
@backend/repositories/redis_repository.py
@routers/occupation.py (or @routers/health.py)

**New File to Create:**
backend/core/redis_client.py (connection pool singleton)

**Reference Documents:**
@/REDIS-FIX-CHECKLIST.md
@/PHASE1-REDIS-EMERGENCY-REPORT.md
</context>

<requirements>

**Task 1: Update Redis Configuration (backend/config.py)**

Add new configuration constants for connection pool management:

```python
# Redis Connection Pool Configuration
REDIS_POOL_MAX_CONNECTIONS: int = 20  # Conservative limit for Railway
REDIS_SOCKET_TIMEOUT: int = 5
REDIS_SOCKET_CONNECT_TIMEOUT: int = 5
REDIS_HEALTH_CHECK_INTERVAL: int = 30
```

**Rationale:**
- `max_connections=20`: Railway Redis likely has 20-30 connection limit. Setting to 20 leaves headroom.
- `socket_timeout=5`: Prevents hanging connections
- `socket_connect_timeout=5`: Fails fast if Redis unreachable
- `health_check_interval=30`: Proactively checks connection health every 30 seconds

**Task 2: Implement Connection Pool Singleton (backend/core/redis_client.py)**

Create a new file `backend/core/redis_client.py` with singleton pattern:

```python
"""
Redis Connection Pool Singleton

Provides centralized Redis connection management with proper pooling.
Prevents connection leaks and "Too many connections" errors.
"""
import redis
import logging
from backend.config import config

logger = logging.getLogger(__name__)

class RedisClient:
    """Singleton Redis connection pool manager"""

    _pool = None
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    @classmethod
    def get_pool(cls) -> redis.ConnectionPool:
        """
        Get or create the Redis connection pool.

        Returns:
            redis.ConnectionPool: Shared connection pool instance
        """
        if cls._pool is None:
            logger.info("Initializing Redis connection pool")
            cls._pool = redis.ConnectionPool(
                host=config.REDIS_HOST,
                port=config.REDIS_PORT,
                password=config.REDIS_PASSWORD,
                max_connections=config.REDIS_POOL_MAX_CONNECTIONS,
                socket_timeout=config.REDIS_SOCKET_TIMEOUT,
                socket_connect_timeout=config.REDIS_SOCKET_CONNECT_TIMEOUT,
                health_check_interval=config.REDIS_HEALTH_CHECK_INTERVAL,
                decode_responses=True
            )
            logger.info(f"Redis pool initialized with max_connections={config.REDIS_POOL_MAX_CONNECTIONS}")
        return cls._pool

    @classmethod
    def get_client(cls) -> redis.Redis:
        """
        Get a Redis client from the connection pool.

        Returns:
            redis.Redis: Redis client using shared pool
        """
        pool = cls.get_pool()
        client = redis.Redis(connection_pool=pool)

        # Log connection usage for monitoring
        pool_info = pool.get_connection('_')
        try:
            active_connections = pool.max_connections - len(pool._available_connections)
            logger.debug(f"Redis pool usage: {active_connections}/{pool.max_connections} active connections")
        except Exception:
            pass  # Ignore logging errors
        finally:
            pool.release(pool_info)

        return client

    @classmethod
    def get_connection_stats(cls) -> dict:
        """
        Get connection pool statistics for monitoring.

        Returns:
            dict: Pool statistics (active, max, available)
        """
        if cls._pool is None:
            return {"status": "pool_not_initialized"}

        try:
            max_conn = cls._pool.max_connections
            available = len(cls._pool._available_connections)
            active = max_conn - available

            return {
                "max_connections": max_conn,
                "active_connections": active,
                "available_connections": available,
                "utilization_percent": (active / max_conn) * 100
            }
        except Exception as e:
            logger.error(f"Error getting pool stats: {e}")
            return {"status": "error", "error": str(e)}
```

**Why singleton pattern?**
- Ensures only ONE connection pool exists across the entire application
- Prevents multiple pools competing for limited connections
- Centralizes connection management and monitoring

**Task 3: Fix Connection Leaks (backend/repositories/redis_repository.py)**

Review and update ALL methods in `RedisRepository` to use the singleton pool:

**Before (connection leak):**
```python
def some_operation(self):
    redis_client = redis.Redis(...)  # New connection every time!
    result = redis_client.get("key")
    return result  # Connection never closed
```

**After (proper pooling):**
```python
from backend.core.redis_client import RedisClient

def some_operation(self):
    client = RedisClient.get_client()  # Reuses connection from pool
    try:
        result = client.get("key")
        return result
    finally:
        # Connection automatically returned to pool when client goes out of scope
        pass
```

**Critical checklist for redis_repository.py:**
- [ ] Replace all `redis.Redis(...)` instantiations with `RedisClient.get_client()`
- [ ] Ensure all operations use try/finally blocks
- [ ] Verify error handlers don't leak connections
- [ ] Add connection count logging to high-traffic methods (TOMAR, PAUSAR, COMPLETAR)

**Example with logging:**
```python
def tomar_spool(self, tag_spool: str, worker_id: int, ttl: int = 3600):
    client = RedisClient.get_client()

    # Log connection usage
    stats = RedisClient.get_connection_stats()
    logger.info(f"TOMAR operation: Redis pool at {stats['utilization_percent']:.1f}% capacity")

    try:
        # ... existing tomar logic ...
        return result
    except redis.RedisError as e:
        logger.error(f"Redis error in tomar_spool: {e}")
        raise
    finally:
        # Connection returned to pool automatically
        pass
```

**Task 4: Update Health Check Endpoint (routers/occupation.py or routers/health.py)**

**Current problem:** `/api/health` returns "healthy" even when Redis is down (misleading).

**Update the health check endpoint** to check BOTH Sheets AND Redis:

```python
from backend.core.redis_client import RedisClient
import redis

@router.get("/api/health")
async def health_check():
    """
    Comprehensive health check including Sheets and Redis.

    Returns:
        - "healthy": All systems operational
        - "degraded": Sheets OK but Redis down (read-only mode)
        - "unhealthy": Critical systems down
    """
    # Check Sheets
    try:
        sheets_ok = check_sheets_connection()  # Existing function
    except Exception as e:
        logger.error(f"Sheets health check failed: {e}")
        sheets_ok = False

    # Check Redis
    try:
        client = RedisClient.get_client()
        client.ping()  # Simple ping test
        redis_ok = True
        redis_error = None
    except redis.RedisError as e:
        logger.error(f"Redis health check failed: {e}")
        redis_ok = False
        redis_error = str(e)

    # Determine overall status
    if sheets_ok and redis_ok:
        status = "healthy"
        operational = True
    elif sheets_ok and not redis_ok:
        status = "degraded"  # Can still read Sheets, but no occupation tracking
        operational = False
    else:
        status = "unhealthy"
        operational = False

    # Get connection pool stats if Redis is up
    connection_stats = None
    if redis_ok:
        connection_stats = RedisClient.get_connection_stats()

    return {
        "status": status,
        "operational": operational,
        "sheets_connection": "ok" if sheets_ok else "error",
        "redis_connection": "ok" if redis_ok else "error",
        "timestamp": datetime.utcnow().isoformat(),
        "details": {
            "redis_error": redis_error,
            "redis_pool_stats": connection_stats
        }
    }
```

**Why this matters:**
- Monitoring systems can now detect Redis outages automatically
- `operational: false` indicates system cannot perform core functions
- `degraded` status allows graceful degradation (read-only mode)

**Task 5: Add Connection Monitoring Endpoint (NEW)**

Create a new monitoring endpoint for DevOps:

```python
@router.get("/api/redis-connection-stats")
async def redis_connection_stats():
    """
    Get Redis connection pool statistics for monitoring.

    Returns connection utilization, active connections, and alerts.
    """
    stats = RedisClient.get_connection_stats()

    # Alert if utilization > 80%
    alert = None
    if stats.get("utilization_percent", 0) > 80:
        alert = "HIGH_UTILIZATION"

    return {
        **stats,
        "alert": alert,
        "timestamp": datetime.utcnow().isoformat()
    }
```

**Task 6: Test the Fixes**

After implementing all changes:

1. **Run unit tests:**
```bash
pytest tests/unit/test_redis_repository.py -v --tb=short
```

2. **Run integration tests:**
```bash
pytest tests/integration/ -k redis -v
```

3. **Verify connection count stays low:**
   - Start backend: `uvicorn main:app --reload`
   - Open browser: `http://localhost:8000/api/redis-connection-stats`
   - Execute 10 TOMAR operations in quick succession
   - Check stats: active_connections should stay below 15

4. **Monitor Railway production:**
   - Deploy changes to production
   - Monitor Railway Redis metrics for 2 hours
   - Watch for "Too many connections" errors in logs
   - Check `/api/health` returns "healthy"

</requirements>

<implementation>

**Execution Order (CRITICAL):**

1. **Create** `backend/core/redis_client.py` (new file with singleton)
2. **Update** `backend/config.py` (add pool config constants)
3. **Refactor** `backend/repositories/redis_repository.py` (fix connection leaks)
4. **Update** `routers/occupation.py` or `routers/health.py` (health check)
5. **Test locally** (pytest + manual connection stats check)
6. **Deploy to production** (Railway)
7. **Monitor** for 2 hours (Railway logs + connection stats)

**Do NOT skip the monitoring step.** The fix must be validated under production load before declaring success.

**Import order matters:**
```python
# Correct import order in redis_repository.py
from backend.core.redis_client import RedisClient  # Our singleton
import redis  # Only for type hints and exceptions, not instantiation
```

**Avoid these pitfalls:**
- ❌ Don't create multiple connection pools (defeats the purpose)
- ❌ Don't use `redis.Redis(...)` directly (bypasses pooling)
- ❌ Don't forget try/finally blocks (causes leaks)
- ❌ Don't skip the 2-hour monitoring (premature success declaration)

</implementation>

<output>

Create/modify these files:

1. **NEW FILE:** `./backend/core/redis_client.py`
   - Singleton connection pool manager
   - ~100 lines including docstrings

2. **UPDATE:** `./backend/config.py`
   - Add 4 new Redis pool config constants
   - ~4 lines added

3. **REFACTOR:** `./backend/repositories/redis_repository.py`
   - Replace all Redis instantiations with `RedisClient.get_client()`
   - Add connection logging to high-traffic methods
   - ~20-30 lines modified

4. **UPDATE:** `./routers/occupation.py` (or `./routers/health.py`)
   - Enhance `/api/health` to check Redis status
   - Add new `/api/redis-connection-stats` endpoint
   - ~40-50 lines added/modified

**Generate Phase 2 Report:**

`./PHASE2-REDIS-POOLING-REPORT.md`

**Report Structure:**

```markdown
# ZEUES v3.0 Redis Crisis - Phase 2 Connection Pooling Report

**Date:** [timestamp]
**Executed by:** Claude Code
**Duration:** [X hours]

---

## 1. Code Changes Summary

**Files Created (1):**
- `backend/core/redis_client.py` - Singleton connection pool manager

**Files Modified (3):**
- `backend/config.py` - Added pool config constants
- `backend/repositories/redis_repository.py` - Fixed connection leaks
- `routers/occupation.py` - Updated health check + monitoring endpoint

**Total Lines Changed:** ~[X] lines
**Git commits:** [link to commits]

---

## 2. Connection Pool Implementation

**Singleton Pattern:**
- ✅ Single connection pool across application
- ✅ Max connections: 20 (Railway limit-safe)
- ✅ Connection timeout: 5 seconds
- ✅ Health check interval: 30 seconds

**Connection Pooling Benefits:**
- Reuses existing connections instead of creating new ones
- Automatic connection health checks
- Graceful handling of connection failures
- Monitoring and logging built-in

**Connection Leaks Fixed:**
- Reviewed [X] methods in `redis_repository.py`
- All methods now use `RedisClient.get_client()`
- Try/finally blocks ensure connections returned to pool
- Error handlers no longer leak connections

---

## 3. Health Check Update

**Before (Misleading):**
```json
{
  "status": "healthy",
  "sheets_connection": "ok"
}
```
Problem: Returns "healthy" even when Redis down

**After (Accurate):**
```json
{
  "status": "degraded",
  "operational": false,
  "sheets_connection": "ok",
  "redis_connection": "error",
  "details": {
    "redis_error": "Too many connections",
    "redis_pool_stats": {
      "active_connections": 20,
      "max_connections": 20,
      "utilization_percent": 100
    }
  }
}
```
Improvement: Clearly indicates Redis outage and system operability

**New Monitoring Endpoint:**
- `/api/redis-connection-stats` - Real-time connection pool metrics
- Alerts when utilization > 80%
- Useful for Railway dashboard and monitoring systems

---

## 4. Testing Results

**Unit Tests:**
```
pytest tests/unit/test_redis_repository.py -v
[paste results]
```

**Integration Tests:**
```
pytest tests/integration/ -k redis -v
[paste results]
```

**Connection Count Verification (Local):**
- Executed 10 TOMAR operations
- Connection stats before: [X active / 20 max]
- Connection stats after: [Y active / 20 max]
- Peak utilization: [Z]%
- Verdict: [PASS/FAIL - connections stayed below 15]

---

## 5. Production Deployment

**Git Commit:**
```
git commit -m "fix: implement Redis connection pooling to prevent exhaustion

- Add RedisClient singleton for centralized connection management
- Update config with pool limits (max_connections=20)
- Fix connection leaks in redis_repository.py
- Enhance health check to include Redis status
- Add /api/redis-connection-stats monitoring endpoint

Fixes production Redis 'Too many connections' error.
Prevents connection pool exhaustion under load.

🤖 Generated with Claude Code
Co-Authored-By: Claude <noreply@anthropic.com>"
```

**Railway Deployment:**
- Deployed: [timestamp]
- Build status: [SUCCESS/FAILED]
- Health check after deploy: [paste curl result]

---

## 6. Production Monitoring (2-Hour Stability Window)

**Monitoring Period:** [start time] to [end time]

**Railway Redis Metrics:**
- Max connections observed: [X]
- Average utilization: [Y]%
- Peak utilization: [Z]%
- "Too many connections" errors: [0 / X occurrences]

**Connection Stats Samples:**

| Time | Active | Available | Utilization | Status |
|------|--------|-----------|-------------|--------|
| T+0min | [X] | [Y] | [Z]% | [OK/HIGH] |
| T+30min | [X] | [Y] | [Z]% | [OK/HIGH] |
| T+60min | [X] | [Y] | [Z]% | [OK/HIGH] |
| T+90min | [X] | [Y] | [Z]% | [OK/HIGH] |
| T+120min | [X] | [Y] | [Z]% | [OK/HIGH] |

**Backend Logs:**
```
[paste relevant log excerpts showing connection usage]
```

**Incidents During Monitoring:**
- [List any errors, high utilization alerts, or anomalies]
- [OR: "No incidents during monitoring period"]

---

## 7. Success Criteria Verification

**Phase 2 Success Criteria:**

- [✅/❌] Connection pool singleton implemented
- [✅/❌] Health check includes Redis status
- [✅/❌] No "Too many connections" errors for 2 hours
- [✅/❌] Connection count stays below 15 during operations
- [✅/❌] Unit tests pass for Redis repository

**All criteria met:** [YES/NO]

---

## 8. Next Steps

**Phase 3 Prerequisites:**

- [✅/❌] Phase 2 code deployed to production
- [✅/❌] 2-hour stability monitoring completed
- [✅/❌] Connection utilization remains <75%
- [✅/❌] Health check accurately reports system status

**Phase 3 Ready:** [YES/NO]

**If YES:** Proceed to Phase 3 (test suite fixes and documentation)

**If NO:** [Explain blockers and remediation plan]

---

## Conclusion

[2-3 paragraph summary of Phase 2 implementation, production stability, and readiness for Phase 3]

---

**Phase 2 Status:** [SUCCESS / PARTIAL SUCCESS / FAILED]
**Ready for Phase 3:** [YES / NO]
**Report generated:** [timestamp]
```

</output>

<verification>

Before declaring Phase 2 complete, verify:

1. **Code Implementation:**
   - [ ] `backend/core/redis_client.py` created with singleton pattern
   - [ ] `backend/config.py` updated with 4 pool config constants
   - [ ] `backend/repositories/redis_repository.py` refactored (no direct `redis.Redis()` calls)
   - [ ] Health check endpoint updated to include Redis status
   - [ ] Monitoring endpoint `/api/redis-connection-stats` added

2. **Testing:**
   - [ ] Unit tests pass for `redis_repository.py`
   - [ ] Integration tests pass for Redis operations
   - [ ] Local connection count verification successful (<15 active connections)

3. **Production Deployment:**
   - [ ] Changes committed to git with descriptive message
   - [ ] Deployed to Railway production
   - [ ] Health check returns correct status after deploy

4. **Monitoring (CRITICAL):**
   - [ ] Monitored production for full 2 hours
   - [ ] Zero "Too many connections" errors during monitoring
   - [ ] Connection utilization stayed below 75%
   - [ ] Railway Redis metrics stable

5. **Documentation:**
   - [ ] Phase 2 report generated and saved
   - [ ] Git commits documented in report
   - [ ] Monitoring data captured in report

**Do NOT skip the 2-hour monitoring.** This is critical to validate the fix under production load.

</verification>

<success_criteria>

**Phase 2 is complete when:**

✅ Connection pool singleton implemented correctly
✅ All connection leaks fixed in redis_repository.py
✅ Health check endpoint updated to include Redis status
✅ Monitoring endpoint `/api/redis-connection-stats` functional
✅ Unit and integration tests pass
✅ Code deployed to production
✅ **Production monitored for 2 hours with zero Redis errors**
✅ Connection utilization remains below 75% (15/20 connections)
✅ Health check accurately reports "healthy"/"degraded" status
✅ Phase 2 report generated and saved

**Minimum stability threshold:**
- 2 hours continuous operation without "Too many connections" errors
- Connection utilization <75% during normal operations
- Health check correctly detects Redis issues

**If stability threshold not met:**
- Investigate connection leaks further
- Consider reducing `REDIS_POOL_MAX_CONNECTIONS` to 15
- Add more aggressive connection timeouts
- Re-deploy and repeat 2-hour monitoring

</success_criteria>

<constraints>

**Railway Constraints:**
- Railway Redis has connection limit (20-30 connections)
- Must set `max_connections=20` conservatively
- Cannot exceed Railway plan limits

**Production Constraints:**
- Cannot take production down for deployment
- Deployment must be zero-downtime
- Must maintain existing functionality during transition

**Testing Constraints:**
- Must test locally before production deployment
- 2-hour monitoring window is mandatory (cannot be shortened)
- Must monitor during peak usage hours if possible

**Code Constraints:**
- Maintain backward compatibility with existing API contracts
- Do not change function signatures in `redis_repository.py`
- Keep health check response format compatible with frontend

</constraints>

<important_notes>

**Why 2-hour monitoring is non-negotiable:**
Connection leaks may not manifest immediately. Under production load, even small leaks accumulate over time. 2 hours provides sufficient observation window to detect issues before declaring success.

**Connection pool math:**
- 30-50 workers + SSE streams = ~50-80 concurrent operations
- With pooling and reuse, 20 connections should handle this load
- Without pooling, each operation creates a new connection → exhausts pool in minutes

**Dependencies for Phase 3:**
Phase 3 (test suite fixes) can begin immediately after Phase 2 deployment. However, Phase 3 completion should wait for Phase 2's 2-hour monitoring to finish to ensure overall system stability.

**Rollback plan:**
If Phase 2 changes cause new issues, rollback is simple:
```bash
git revert [commit-hash]
git push production main
```
The singleton pattern is additive (doesn't break existing code), so rollback risk is low.

</important_notes>
