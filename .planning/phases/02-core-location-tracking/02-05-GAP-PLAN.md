---
phase: 02-core-location-tracking
plan: 05-gap
type: execute
wave: 5
depends_on: [02-01, 02-02, 02-03, 02-04]
files_modified:
  - backend/repositories/redis_repository.py
  - backend/services/redis_lock_service.py
autonomous: true
must_haves:
  truths:
    - "Workers can take spools without AttributeError on redis_repo.get_client()"
    - "Lock service instantiation succeeds with Redis client injection"
    - "Redis operations work after dependency injection completes"
  artifacts:
    - path: "backend/repositories/redis_repository.py"
      provides: "get_client() method for dependency injection"
      exports: ["get_client"]
  key_links:
    - from: "backend/core/dependency.py"
      to: "backend/repositories/redis_repository.py"
      via: "get_client() method call"
      pattern: "redis_repo\\.get_client\\(\\)"
---

# 02-05-GAP-PLAN: Fix Redis repository get_client method

## Goal

Add missing `get_client()` method to RedisRepository that dependency.py expects, enabling RedisLockService instantiation.

## Context

The verification report shows that `backend/core/dependency.py` line 346 calls `redis_repo.get_client()` to pass the Redis client to RedisLockService, but this method doesn't exist in RedisRepository. This causes an AttributeError at runtime, preventing any TOMAR/PAUSAR/COMPLETAR operations from working.

## Tasks

<task type="auto">
<name>Task 1: Add get_client() method to RedisRepository</name>
<files>
- backend/repositories/redis_repository.py
</files>
<action>
Add get_client() method after __init__ (around line 57) that returns the Redis client instance:
- Returns self.client (Redis instance if connected, None if not)
- Logs warning if client requested before connection
- Provides the missing interface that dependency.py expects at line 346
- Type hint: Optional[aioredis.Redis]
</action>
<verify>
Python REPL test: redis_repo.get_client() returns None before connect(), Redis instance after
</verify>
<done>false</done>
</task>

<task type="auto">
<name>Task 2: Update RedisLockService documentation</name>
<files>
- backend/services/redis_lock_service.py
</files>
<action>
Update __init__ method docstring to document redis_client requirement:
- Note that redis_client should come from RedisRepository.get_client()
- Mention it must be connected (not None) for operations to work
- Reference FastAPI startup event as connection point
</action>
<verify>
Docstring clearly explains connection requirement for redis_client parameter
</verify>
<done>false</done>
</task>

## Verification

### Test Steps

1. **Method exists and returns client:**
   ```python
   # In Python REPL or test
   from backend.repositories.redis_repository import RedisRepository

   redis_repo = RedisRepository()

   # Before connect - should return None with warning
   client = redis_repo.get_client()
   assert client is None

   # After connect - should return Redis instance
   await redis_repo.connect()
   client = redis_repo.get_client()
   assert client is not None
   assert hasattr(client, 'set')  # Has Redis methods
   ```

2. **Dependency injection works:**
   ```python
   from backend.core.dependency import get_redis_lock_service

   # This should not raise AttributeError anymore
   lock_service = get_redis_lock_service()
   assert lock_service is not None
   ```

3. **Integration test:**
   ```bash
   # Start the API
   cd backend
   uvicorn main:app --reload

   # In another terminal, test TOMAR endpoint
   curl -X POST http://localhost:8000/api/occupation/tomar \
     -H "Content-Type: application/json" \
     -d '{
       "worker_id": 93,
       "tag_spool": "TAG-001",
       "operacion": "ARM"
     }'
   # Should NOT get AttributeError about get_client
   ```

### Expected Outcomes

✅ **RedisRepository has get_client() method** - No AttributeError when dependency.py calls it
✅ **Method returns None before connect()** - Safe fallback with warning log
✅ **Method returns Redis client after connect()** - Actual Redis operations can proceed
✅ **RedisLockService can be instantiated** - Dependency injection chain works

