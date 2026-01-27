# Phase 2: Core Location Tracking - Research

**Researched:** 2026-01-27
**Domain:** Occupation tracking with race condition prevention for manufacturing spools
**Confidence:** HIGH

## Summary

Phase 2 implements physical occupation constraints for spool tracking, allowing workers to take (TOMAR), pause (PAUSAR), and complete (COMPLETAR) work with atomic locking to prevent race conditions. The standard approach uses Redis with atomic operations (SET NX EX pattern) for distributed locks, combined with optimistic locking via version tokens in the database layer. This dual-layer approach ensures both immediate race prevention (Redis) and eventual consistency (database versioning).

Key architectural decision: Redis serves as the primary lock manager for occupation state, while Google Sheets maintains the persistent state with version tokens. This separation allows sub-second lock acquisition while preserving the existing Sheets-based workflow.

**Primary recommendation:** Deploy Redis with atomic SET NX EX operations for occupation locking, implement optimistic locking with version tokens in Sheets, and use partial success patterns for batch operations.

## Standard Stack

The established libraries/tools for this domain:

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| redis | 5.0+ | Async Redis client (redis.asyncio) | Official client with native async support for FastAPI |
| fastapi | 0.109+ | Async web framework | Already in use, supports dependency injection for Redis |
| pydantic | 2.5+ | Data validation | Existing stack, extended for occupation models |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| python-redis-lock | 4.0+ | High-level locking abstraction | Complex lock scenarios with auto-renewal |
| tenacity | 8.2+ | Retry with backoff | Redis connection resilience |
| httpx | 0.25+ | Async HTTP client | Webhook notifications for conflicts |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Redis | PostgreSQL advisory locks | Would require database migration from Sheets |
| Redis | In-memory Python dict | No distribution support, loses state on restart |
| Optimistic locking | Pessimistic locking | Would block reads, poor mobile UX |

**Installation:**
```bash
pip install redis[hiredis] tenacity
```

## Architecture Patterns

### Recommended Project Structure
```
backend/
├── services/
│   ├── occupation_service.py    # TOMAR/PAUSAR/COMPLETAR orchestration
│   ├── conflict_service.py      # Optimistic locking + version management
│   └── redis_lock_service.py    # Atomic lock operations
├── repositories/
│   ├── sheets_repository.py     # Extended with version token updates
│   └── redis_repository.py      # Redis connection management
├── models/
│   ├── occupation.py             # Occupation state models
│   └── conflict.py               # Conflict resolution models
└── exceptions/
    └── occupation_errors.py      # SpoolOccupiedError, VersionConflictError
```

### Pattern 1: Atomic Occupation with Redis SET NX EX
**What:** Use Redis SET with NX (if not exists) and EX (expiration) flags for atomic lock acquisition
**When to use:** Every TOMAR operation to prevent simultaneous occupation
**Example:**
```python
# Source: Redis documentation + FastAPI best practices
async def tomar_spool(tag_spool: str, worker_id: int) -> bool:
    lock_key = f"spool_lock:{tag_spool}"
    lock_value = f"{worker_id}:{uuid.uuid4()}"  # Unique token

    # Atomic operation: set if not exists with 30min expiration
    acquired = await redis.set(
        lock_key,
        lock_value,
        nx=True,  # Only set if not exists
        ex=1800   # 30 minutes expiration
    )

    if not acquired:
        # Check current owner for error message
        current_owner = await redis.get(lock_key)
        raise SpoolOccupiedError(tag_spool, current_owner)

    return True
```

### Pattern 2: Optimistic Locking with Version Tokens
**What:** Each spool has a version token that increments on every state change
**When to use:** Database updates to detect and prevent lost updates
**Example:**
```python
# Source: Optimistic concurrency control patterns
def update_with_version_check(tag_spool: str, version_token: str, updates: dict):
    # Read current version
    current = sheets_repository.get_spool(tag_spool)

    if current.version != version_token:
        raise VersionConflictError(
            expected=version_token,
            actual=current.version,
            message="Spool was modified by another process"
        )

    # Update with new version
    updates['version'] = str(uuid.uuid4())  # New version token
    sheets_repository.update_spool(tag_spool, updates)
```

### Pattern 3: Partial Success for Batch Operations
**What:** Process each item independently, return detailed success/failure report
**When to use:** Batch TOMAR/PAUSAR operations on multiple spools
**Example:**
```python
# Source: API bulk processing best practices
async def batch_tomar(spools: List[str], worker_id: int) -> BatchResult:
    results = []

    for tag_spool in spools:
        try:
            await tomar_spool(tag_spool, worker_id)
            results.append({"tag_spool": tag_spool, "success": True})
        except SpoolOccupiedError as e:
            results.append({
                "tag_spool": tag_spool,
                "success": False,
                "error": f"409: Already occupied by {e.owner}"
            })

    return BatchResult(
        total=len(spools),
        succeeded=sum(1 for r in results if r["success"]),
        failed_count=sum(1 for r in results if not r["success"]),
        details=results
    )
```

### Anti-Patterns to Avoid
- **Separate SETNX + EXPIRE:** Creates race condition window if process dies between commands
- **No expiration on locks:** Can leave spools permanently locked if worker crashes
- **Blocking waits:** Never use blocking Redis operations in async FastAPI handlers
- **Global locks:** Don't lock entire operation types, only individual spools

## Don't Hand-Roll

Problems that look simple but have existing solutions:

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Distributed locking | Custom database flags | Redis SET NX EX | Atomic operations, automatic expiration, battle-tested |
| Lock release verification | Simple delete | Lua script with token check | Prevents accidental release of others' locks |
| Retry logic | While loops | tenacity library | Exponential backoff, jitter, max attempts |
| Connection pooling | Manual connection management | redis.asyncio.ConnectionPool | Handles reconnection, connection limits |
| Version generation | Incremental counters | UUID v4 tokens | No coordination needed, globally unique |

**Key insight:** Distributed locking seems simple but has numerous edge cases (process crashes, network partitions, clock skew). Redis with proper patterns handles these robustly.

## Common Pitfalls

### Pitfall 1: Redis Connection Loss During Critical Section
**What goes wrong:** Redis connection drops after acquiring lock but before Sheets update
**Why it happens:** Network issues, Redis restart, connection timeout
**How to avoid:** Implement connection pool with retry, use circuit breaker pattern
**Warning signs:** Intermittent 500 errors, locks held longer than expected

### Pitfall 2: Lock Expiration During Long Operations
**What goes wrong:** Lock expires while operation still in progress, another worker takes spool
**Why it happens:** Sheets API slowness, batch operations taking > 30 minutes
**How to avoid:** Extend lock TTL periodically (lock renewal), or use reasonable TTL (1-2 hours)
**Warning signs:** "Lost update" errors, workers reporting spool taken by others mid-work

### Pitfall 3: Version Token Mismatch in High Concurrency
**What goes wrong:** Multiple workers read same version, all try to update, all but one fail
**Why it happens:** Thundering herd on popular spools
**How to avoid:** Implement retry with exponential backoff and jitter
**Warning signs:** High conflict rate (>10%) on specific spools

### Pitfall 4: Forgetting to Release Lock on PAUSAR/COMPLETAR
**What goes wrong:** Spool remains locked in Redis even after marked available in Sheets
**Why it happens:** Missing delete operation, error handling bypasses cleanup
**How to avoid:** Use try/finally blocks, implement lock cleanup in background job
**Warning signs:** Spools show available but can't be taken

### Pitfall 5: Partial State After Batch Failure
**What goes wrong:** Some spools locked in Redis, others not, inconsistent state
**Why it happens:** Batch operation fails midway
**How to avoid:** Track all acquired locks, rollback on failure, use transaction-like patterns
**Warning signs:** Batch operations show partial success but state is corrupted

## Code Examples

Verified patterns from official sources:

### Redis Connection with FastAPI Dependency Injection
```python
# Source: Redis + FastAPI official documentation
from redis import asyncio as aioredis
from fastapi import Depends

class RedisService:
    def __init__(self):
        self.redis = None

    async def connect(self):
        self.redis = await aioredis.from_url(
            "redis://localhost",
            encoding="utf-8",
            decode_responses=True,
            max_connections=50
        )

    async def disconnect(self):
        await self.redis.close()

# Singleton
redis_service = RedisService()

async def get_redis():
    return redis_service.redis

# In endpoints
@router.post("/tomar")
async def tomar_endpoint(
    redis: aioredis.Redis = Depends(get_redis)
):
    # Use redis client
    pass
```

### Safe Lock Release with Lua Script
```python
# Source: Redis lock best practices
RELEASE_SCRIPT = """
if redis.call("get", KEYS[1]) == ARGV[1] then
    return redis.call("del", KEYS[1])
else
    return 0
end
"""

async def release_lock(redis, lock_key: str, lock_value: str):
    """Release lock only if we own it."""
    result = await redis.eval(
        RELEASE_SCRIPT,
        keys=[lock_key],
        args=[lock_value]
    )
    return result == 1  # True if released
```

### Handling 409 Conflicts with Retry
```python
# Source: tenacity documentation + API patterns
from tenacity import retry, stop_after_attempt, wait_exponential

@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=1, max=10),
    reraise=True
)
async def tomar_with_retry(tag_spool: str, worker_id: int):
    try:
        return await tomar_spool(tag_spool, worker_id)
    except SpoolOccupiedError as e:
        # Log conflict for monitoring
        logger.warning(f"Conflict on {tag_spool}: {e}")
        raise  # Retry will handle
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Database row locks | Redis distributed locks | 2023-2024 | Sub-second lock acquisition |
| Incremental versions | UUID version tokens | 2024 | No coordination required |
| 500 on all conflicts | 409 with retry guidance | 2024-2025 | Better client UX |
| Synchronous operations | Async with await | FastAPI adoption | 10x throughput |

**Deprecated/outdated:**
- aioredis separate package: Now integrated into redis-py as redis.asyncio
- SETNX command alone: Use SET with NX and EX flags instead
- Redlock algorithm: Controversial, single Redis instance with proper config usually sufficient

## Open Questions

Things that couldn't be fully resolved:

1. **Lock TTL Duration**
   - What we know: Must be longer than longest operation
   - What's unclear: Optimal duration (30 min vs 1 hour vs 2 hours)
   - Recommendation: Start with 1 hour, monitor and adjust

2. **Partial State Representation**
   - What we know: Need to mark "ARM parcial" or "SOLD parcial"
   - What's unclear: New column vs encoding in existing column
   - Recommendation: Add Estado_Parcial column for clarity

3. **Redis Deployment**
   - What we know: Need Redis instance accessible from backend
   - What's unclear: Railway Redis addon vs external service
   - Recommendation: Start with Railway Redis addon for simplicity

## Sources

### Primary (HIGH confidence)
- Redis official documentation - SET command with NX/EX flags
- FastAPI + Redis integration guides - Connection patterns, dependency injection
- redis-py async documentation - redis.asyncio module usage

### Secondary (MEDIUM confidence)
- Optimistic locking in REST APIs (sookocheff.com) - Version token patterns
- Medium articles on Redis + FastAPI - Real-world implementations verified against official docs

### Tertiary (LOW confidence)
- Community discussions on batch processing - Patterns need validation in production

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - Redis + FastAPI is well-established pattern
- Architecture: HIGH - Based on proven distributed systems patterns
- Pitfalls: MEDIUM - Common issues documented but need production validation

**Research date:** 2026-01-27
**Valid until:** 2026-02-27 (30 days - stable patterns)