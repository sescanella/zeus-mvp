---
phase: 02-core-location-tracking
plan: 06-gap
type: execute
wave: 5
depends_on: [02-01, 02-05]
files_modified:
  - backend/main.py
  - backend/config.py
  - backend/routers/health.py
autonomous: true
must_haves:
  truths:
    - "API accepts requests immediately after startup without Redis errors"
    - "Redis health check returns connected status when Redis is available"
    - "TOMAR operations work without 'Redis client not connected' errors"
    - "Redis connection pool is released cleanly on shutdown"
  artifacts:
    - path: "backend/main.py"
      provides: "Redis lifecycle management in startup/shutdown events"
      contains: "redis_repo.connect()"
    - path: "backend/routers/health.py"
      provides: "Redis health check endpoint for monitoring"
      exports: ["redis_health"]
  key_links:
    - from: "backend/main.py"
      to: "backend/repositories/redis_repository.py"
      via: "startup event connection"
      pattern: "redis_repo\\.connect\\(\\)"
---

# 02-06-GAP-PLAN: Integrate Redis lifecycle in FastAPI startup/shutdown

## Goal

Integrate Redis connection lifecycle into FastAPI startup and shutdown events, ensuring Redis is connected before any requests are handled.

## Context

The verification report shows that Redis is never connected because main.py's startup_event() doesn't call `redis_repo.connect()`. Without this, all Redis operations fail with "Redis client not connected". The shutdown event also doesn't disconnect, leading to potential connection pool leaks.

## Tasks

<task type="auto">
<name>Task 1: Add Redis repository import to main.py</name>
<files>
- backend/main.py
</files>
<action>
Add import statement after existing imports (around line 38):
- Import RedisRepository from backend.repositories.redis_repository
- Required for startup/shutdown event lifecycle management
</action>
<verify>
Import statement exists and no import errors on startup
</verify>
<done>false</done>
</task>

<task type="auto">
<name>Task 2: Add Redis connection to startup event</name>
<files>
- backend/main.py
</files>
<action>
Modify startup_event function (line 239) to include Redis connection:
- Create RedisRepository singleton instance
- Call await redis_repo.connect() with try/except
- Log success/failure (non-blocking - API starts even if Redis down)
- Place after logging setup but before pre-warm cache
</action>
<verify>
API logs show "Redis connected successfully" on startup
</verify>
<done>false</done>
</task>

<task type="auto">
<name>Task 3: Add Redis disconnection to shutdown event</name>
<files>
- backend/main.py
</files>
<action>
Modify shutdown_event function (line 296) to disconnect Redis:
- Get RedisRepository singleton instance
- Check if client exists, then await redis_repo.disconnect()
- Wrap in try/except to handle errors gracefully
- Log clean disconnection or warning on error
</action>
<verify>
API logs show "Redis disconnected cleanly" on shutdown
</verify>
<done>false</done>
</task>

<task type="auto">
<name>Task 4: Ensure Redis config variables exist</name>
<files>
- backend/config.py
</files>
<action>
Check and add if missing:
- REDIS_URL (default: redis://localhost:6379/0)
- REDIS_MAX_CONNECTIONS (default: 50)
- REDIS_LOCK_TTL_SECONDS (default: 3600)
Use os.getenv pattern consistent with existing config
</action>
<verify>
Config variables accessible and have sensible defaults
</verify>
<done>false</done>
</task>

<task type="auto">
<name>Task 5: Add Redis health check endpoint</name>
<files>
- backend/routers/health.py
</files>
<action>
Add GET /redis-health endpoint:
- Import RedisRepository
- Check if client is None (disconnected)
- If connected, ping Redis and get info stats
- Return status (healthy/unhealthy/disconnected) with details
</action>
<verify>
curl http://localhost:8000/api/redis-health returns connection status
</verify>
<done>false</done>
</task>

## Verification

### Test Steps

1. **Startup connects to Redis:**
   ```bash
   # Start the API and check logs
   cd backend
   uvicorn main:app --reload

   # Should see in logs:
   # "🔄 Connecting to Redis for occupation locking..."
   # "✅ Redis connected successfully"
   ```

2. **Redis health check works:**
   ```bash
   curl http://localhost:8000/api/redis-health

   # Should return:
   # {
   #   "status": "healthy",
   #   "message": "Redis connected and responding",
   #   "operational": true,
   #   "redis_version": "7.2.3",
   #   ...
   # }
   ```

3. **TOMAR endpoint works (no AttributeError):**
   ```bash
   curl -X POST http://localhost:8000/api/occupation/tomar \
     -H "Content-Type: application/json" \
     -d '{
       "worker_id": 93,
       "tag_spool": "TAG-001",
       "operacion": "ARM"
     }'

   # Should NOT get AttributeError
   # May fail with "Spool not found" but that's OK - Redis is working
   ```

4. **Shutdown disconnects cleanly:**
   ```bash
   # Stop the API with Ctrl+C
   # Should see in logs:
   # "🔴 ZEUES API shutting down..."
   # "✅ Redis disconnected cleanly"
   ```

### Expected Outcomes

✅ **Redis connects at startup** - Connection established before first request
✅ **Redis health endpoint available** - Can monitor Redis status
✅ **Occupation endpoints work** - No "Redis client not connected" errors
✅ **Clean shutdown** - Connection pool released properly

