# Redis Connection Crisis - Fix Checklist

**Issue:** Production Redis "Too many connections" error
**Impact:** All occupation features (TOMAR/PAUSAR/COMPLETAR) non-functional
**Discovered:** 2026-02-02 08:12:00

---

## ⚡ Emergency Fix (Do This First)

### Step 1: Restart Redis Service in Railway

1. Go to: https://railway.app (Railway Dashboard)
2. Select project: ZEUES Production
3. Navigate to: Redis service
4. Click: **"Restart"** button
5. Wait: 30-60 seconds for service to restart
6. Verify: Service shows "Running" status

### Step 2: Verify Redis Health

```bash
# Run this command to check Redis status:
curl https://zeues-backend-mvp-production.up.railway.app/api/redis-health

# Expected result after restart:
{
  "status": "healthy",
  "operational": true
}

# If still unhealthy, wait 2 minutes and try again
```

### Step 3: Test Basic Operations

```bash
# Test TOMAR operation:
curl -X POST https://zeues-backend-mvp-production.up.railway.app/api/occupation/tomar \
  -H "Content-Type: application/json" \
  -d '{
    "tag_spool": "TEST-02",
    "worker_id": 93,
    "worker_nombre": "MR(93)",
    "operacion": "ARM"
  }'

# Expected: 200 OK with success message
# If 500 error persists, Redis is still down
```

### Step 4: Re-run E2E Tests

```bash
cd /Users/sescanella/Proyectos/KM/ZEUES-by-KM
source venv/bin/activate
python test_production_v3_e2e_simple.py

# Expected: At least 6/8 tests should pass after Redis fix
```

---

## 🔧 Permanent Fix (Do This Week)

### File: `backend/repositories/redis_repository.py`

**Check for connection leaks:**

```python
# ❌ BAD - Connection leak:
def some_operation(self):
    redis_client = redis.Redis(...)
    result = redis_client.get("key")
    return result  # Connection never closed!

# ✅ GOOD - Proper connection management:
def some_operation(self):
    redis_client = redis.Redis(connection_pool=self.pool)
    try:
        result = redis_client.get("key")
        return result
    finally:
        # Connection returned to pool automatically
        pass
```

### File: `backend/config.py`

**Update Redis configuration:**

```python
# Add these settings:
REDIS_POOL_MAX_CONNECTIONS: int = 20  # Conservative limit
REDIS_SOCKET_TIMEOUT: int = 5
REDIS_SOCKET_CONNECT_TIMEOUT: int = 5
REDIS_HEALTH_CHECK_INTERVAL: int = 30
```

### File: `backend/core/redis_client.py` (create if not exists)

**Implement connection pool singleton:**

```python
import redis
from backend.config import config

class RedisClient:
    _pool = None

    @classmethod
    def get_pool(cls):
        if cls._pool is None:
            cls._pool = redis.ConnectionPool(
                host=config.REDIS_HOST,
                port=config.REDIS_PORT,
                password=config.REDIS_PASSWORD,
                max_connections=20,  # Conservative limit
                socket_timeout=5,
                socket_connect_timeout=5,
                health_check_interval=30
            )
        return cls._pool

    @classmethod
    def get_client(cls):
        return redis.Redis(connection_pool=cls.get_pool())
```

### File: `routers/occupation.py`

**Update health endpoint:**

```python
@router.get("/api/health")
async def health_check():
    # Check Sheets
    sheets_ok = check_sheets_connection()

    # Check Redis
    redis_ok = check_redis_connection()

    # Determine overall status
    if sheets_ok and redis_ok:
        status = "healthy"
        operational = True
    elif sheets_ok:
        status = "degraded"  # Sheets OK but Redis down
        operational = False
    else:
        status = "unhealthy"
        operational = False

    return {
        "status": status,
        "operational": operational,
        "sheets_connection": "ok" if sheets_ok else "error",
        "redis_connection": "ok" if redis_ok else "error",
        "timestamp": datetime.utcnow().isoformat()
    }
```

---

## 📊 Monitoring Setup

### Railway Dashboard

1. Go to: Redis service → Metrics
2. Monitor: **Connection Count** graph
3. Set Alert: Email when connections > 15 (75% of 20 limit)

### Application Logs

Add logging to track connection usage:

```python
import logging

logger = logging.getLogger(__name__)

def tomar_spool(...):
    pool = RedisClient.get_pool()
    logger.info(f"Redis pool: {pool.max_connections - len(pool._available_connections)} active connections")
    # ... rest of operation
```

---

## 🧪 Testing After Fix

### Manual Test Sequence

```bash
# 1. Test TOMAR
curl -X POST .../api/occupation/tomar -d '{"tag_spool": "TEST-02", ...}'
# → Expect: 200 OK

# 2. Test PAUSAR
curl -X POST .../api/occupation/pausar -d '{"tag_spool": "TEST-02", ...}'
# → Expect: 200 OK

# 3. Test TOMAR again
curl -X POST .../api/occupation/tomar -d '{"tag_spool": "TEST-02", ...}'
# → Expect: 200 OK

# 4. Test COMPLETAR
curl -X POST .../api/occupation/completar -d '{"tag_spool": "TEST-02", "fecha_operacion": "2026-02-02", ...}'
# → Expect: 200 OK

# 5. Check Redis health
curl .../api/redis-health
# → Expect: {"status": "healthy", "operational": true}
```

### Automated E2E Tests

```bash
# Run full test suite:
python test_production_v3_e2e_simple.py

# Expected results after fix:
# - Test 1 (ARM Flow): PASS
# - Test 2 (Race Condition): PASS
# - Test 3 (Invalid PAUSAR): PASS
# - Test 4 (Nonexistent Spool): PASS
# - Test 5 (History): PASS (after test fix)
# - Test 6 (Health): PASS
# - Test 7 (SOLD Flow): PASS (after test fix)
# - Test 8 (Metrología): PASS (after test fix)
#
# Target: 8/8 PASS (100%)
```

---

## ✅ Success Criteria

Redis fix is complete when:

- [ ] Redis health endpoint returns "healthy"
- [ ] TOMAR/PAUSAR/COMPLETAR operations return 200 OK
- [ ] E2E test suite passes ≥ 6/8 tests
- [ ] No "Too many connections" errors in logs for 2 hours
- [ ] Connection count stays below 15 during normal operations
- [ ] Health check reflects true system state

---

## 📝 Post-Fix Actions

### Update Documentation

- [ ] Update CLAUDE.md with correct API examples (fecha_operacion field)
- [ ] Document Redis connection pool configuration
- [ ] Add troubleshooting section for Redis issues

### Incident Postmortem

- [ ] Document root cause analysis
- [ ] List preventive measures implemented
- [ ] Update runbook for future Redis issues

### E2E Test Suite Improvements

- [ ] Fix test schema (add fecha_operacion)
- [ ] Fix history endpoint assertions
- [ ] Add Redis health pre-check before tests
- [ ] Auto-generate tests from OpenAPI schema

---

**Last Updated:** 2026-02-02 08:15:00
**Next Review:** After Redis fix and 48-hour stability period
