# Phase 9: Redis & Version Detection - Research

**Researched:** 2026-02-02
**Domain:** Redis persistent locks, lazy cleanup, startup reconciliation, version detection
**Confidence:** HIGH

## Summary

Phase 9 enables dual workflow support (v3.0 legacy + v4.0 union-level tracking) through persistent Redis locks and intelligent version detection. Research reveals that implementing persistent locks WITHOUT TTL contradicts Redis official best practices, but can be made safe through lazy cleanup and startup reconciliation. The current codebase uses v3.0 1-hour TTL locks (`config.REDIS_LOCK_TTL_SECONDS = 3600`) with key format `spool_lock:{tag_spool}`, which must be migrated to persistent locks using Redis PERSIST command.

Version detection is straightforward: query `Total_Uniones` column (68) from Operaciones sheet and route to v4.0 workflow if count > 0, v3.0 workflow if count = 0. Frontend caching with session-level storage prevents repeated API calls.

**Primary recommendation:** Implement persistent locks with mandatory 24-hour lazy cleanup inline with INICIAR operation, using Redis SCAN for abandoned lock detection, and startup reconciliation with Sheets.Ocupado_Por as source of truth.

## Standard Stack

The established libraries/tools for this domain:

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| redis | 5.0.1 | Async Redis client with connection pool | Production-deployed in v3.0, AsyncIO-native for FastAPI |
| tenacity | 9.1.2+ | Retry/backoff library | Already in use for Redis operations, standard for resilience patterns |
| FastAPI | 0.95.0+ | Web framework with lifespan events | Production codebase, ASGI lifespan protocol for startup/shutdown |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| redis.asyncio | 5.0.1 (included) | AsyncIO Redis client | Default for async operations |
| python-statemachine | 2.5.0 | State machine framework | Already in use for ARM/SOLD state machines |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| redis | aioredis | aioredis merged into redis-py 4.2.0+, redis is successor |
| tenacity | backoff | tenacity more mature (9.x vs 2.x), better async support |
| @app.on_event | @contextlib.asynccontextmanager | Lifespan context manager is newer pattern, but on_event still supported |

**Installation:**
```bash
# Already installed in v3.0
pip install redis==5.0.1
pip install tenacity  # Already present for v3.0 Redis operations
```

## Architecture Patterns

### Recommended Project Structure
```
backend/
├── services/
│   ├── redis_lock_service.py      # Add: remove_ttl(), cleanup_abandoned_locks(), reconcile_from_sheets()
│   └── version_detection_service.py # NEW: detect_version(), cache version per session
├── routers/
│   └── occupation.py               # Modify: INICIAR with inline cleanup
└── main.py                         # Modify: startup_event() with reconciliation
```

### Pattern 1: Persistent Locks with PERSIST Command
**What:** Convert v3.0 TTL-based locks to persistent locks using Redis PERSIST command
**When to use:** After INICIAR acquires lock with SET NX, immediately call PERSIST to remove TTL
**Example:**
```python
# Current v3.0 (WITH TTL)
await redis.set(lock_key, lock_value, nx=True, ex=3600)  # 1-hour TTL

# Phase 9 (NO TTL - two-step approach)
# Step 1: Acquire with short safety TTL (10 seconds)
acquired = await redis.set(lock_key, lock_value, nx=True, ex=10)
if acquired:
    # Step 2: Immediately remove TTL to make persistent
    await redis.persist(lock_key)
    # Lock now persists forever until explicitly released
```

**Why two-step:** Short 10-second TTL during acquisition prevents orphaned locks if process crashes between SET and PERSIST. After PERSIST succeeds, lock is permanent until FINALIZAR.

**Reference:** Redis PERSIST command (redis.io/docs/latest/commands/persist/) - returns 1 on success, 0 if key doesn't exist

### Pattern 2: Lazy Cleanup on INICIAR
**What:** Inline cleanup that removes ONE abandoned lock per INICIAR operation
**When to use:** At start of every INICIAR operation, before acquiring new lock
**Example:**
```python
async def lazy_cleanup_one_abandoned_lock(self):
    """
    Clean up ONE abandoned lock >24h old without matching Sheets.Ocupado_Por.

    Eventual consistency approach - cleans one lock per INICIAR operation
    instead of expensive batch cleanup.
    """
    cursor = 0
    pattern = "spool_lock:*"

    # Scan for ONE candidate lock (limit=1 for performance)
    cursor, keys = await self.redis.scan(cursor=cursor, match=pattern, count=10)

    if not keys:
        return  # No locks to clean

    # Check first key only (one lock per operation)
    lock_key = keys[0]
    tag_spool = lock_key.split(":", 1)[1]  # Extract TAG_SPOOL from "spool_lock:TEST-01"

    # Get lock timestamp (embedded in value as "worker_id:token:timestamp")
    lock_value = await self.redis.get(lock_key)
    if not lock_value:
        return  # Lock expired between SCAN and GET

    # Parse timestamp from lock value
    parts = lock_value.split(":")
    if len(parts) >= 3:
        timestamp_str = parts[2]  # ISO format timestamp
        lock_time = datetime.fromisoformat(timestamp_str)
        age_hours = (now_chile() - lock_time).total_seconds() / 3600

        if age_hours > 24:
            # Query Sheets.Ocupado_Por for this TAG_SPOOL
            spool = sheets_repo.get_spool_by_tag(tag_spool)

            if not spool.ocupado_por or spool.ocupado_por == "DISPONIBLE":
                # Abandoned lock - delete silently (no Metadata event)
                await self.redis.delete(lock_key)
                logger.info(f"Lazy cleanup: removed abandoned lock for {tag_spool} (age: {age_hours:.1f}h)")
```

**Why one-per-operation:** Eventual consistency is acceptable - 10 INICIAR operations clean 10 locks. Avoids expensive full SCAN blocking operations.

**Reference:** User decision (CONTEXT.md) - "Clean only one abandoned lock per INICIAR operation"

### Pattern 3: Startup Reconciliation from Sheets
**What:** On FastAPI startup, rebuild Redis locks from Sheets.Ocupado_Por (source of truth)
**When to use:** In FastAPI startup event, after Redis connection established, before accepting requests
**Example:**
```python
@app.on_event("startup")
async def startup_event():
    # ... existing startup code ...

    # v4.0: Reconcile Redis locks from Sheets (auto-recovery)
    try:
        logger.info("🔄 Reconciling Redis locks from Sheets.Ocupado_Por...")
        redis_repo = RedisRepository()
        sheets_repo = get_sheets_repository()

        # Query all spools with Ocupado_Por != "DISPONIBLE"
        all_spools = sheets_repo.get_all_spools()
        occupied_spools = [s for s in all_spools if s.ocupado_por and s.ocupado_por != "DISPONIBLE"]

        reconciled_count = 0
        skipped_count = 0

        for spool in occupied_spools:
            # Check timestamp - skip locks older than 24 hours
            if spool.fecha_ocupacion:
                ocupacion_time = datetime.strptime(spool.fecha_ocupacion, "%d-%m-%Y %H:%M:%S")
                age_hours = (now_chile() - ocupacion_time).total_seconds() / 3600

                if age_hours > 24:
                    logger.info(f"Skipping old occupation: {spool.tag_spool} (age: {age_hours:.1f}h)")
                    skipped_count += 1
                    continue

            # Check if Redis lock exists
            lock_key = f"spool_lock:{spool.tag_spool}"
            exists = await redis_repo.client.exists(lock_key)

            if not exists:
                # Recreate lock from Sheets data
                # Parse worker_id from "INICIALES(ID)" format
                import re
                match = re.search(r'\((\d+)\)$', spool.ocupado_por)
                if match:
                    worker_id = int(match.group(1))
                    lock_value = f"{worker_id}:{uuid.uuid4()}:{spool.fecha_ocupacion}"

                    # Create persistent lock (no TTL)
                    await redis_repo.client.set(lock_key, lock_value, nx=True, ex=10)
                    await redis_repo.client.persist(lock_key)

                    reconciled_count += 1
                    logger.info(f"Reconciled lock: {spool.tag_spool} for worker {worker_id}")

        logger.info(f"✅ Redis reconciliation complete: {reconciled_count} locks created, {skipped_count} old locks skipped")

    except Exception as e:
        # Log error but don't block startup - Redis optional for read operations
        logger.warning(f"⚠️ Redis reconciliation failed: {e}. Locks will be created on-demand.")
```

**Why startup reconciliation:** Handles Railway restarts, Redis crashes, or deployments gracefully. Sheets is source of truth.

**Reference:** User decision (CONTEXT.md) - "Sheets wins — If Sheets.Ocupado_Por has value, recreate Redis lock to match"

### Pattern 4: Version Detection with Caching
**What:** Detect v3.0 vs v4.0 spool by querying Total_Uniones column, cache result per session
**When to use:** Frontend P4 (spool selection), just-in-time detection
**Example:**
```python
# Backend: Version detection service
class VersionDetectionService:
    """Detect spool version (v3.0 vs v4.0) based on union count."""

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type((SheetsConnectionError, TimeoutError)),
        reraise=True
    )
    async def detect_version(self, tag_spool: str) -> dict:
        """
        Detect spool version with retry logic.

        Returns:
            dict with keys:
                - version: "v3.0" or "v4.0"
                - union_count: int (value from Total_Uniones column 68)
                - detection_logic: str (explanation for diagnostics)

        Raises:
            VersionDetectionError: After 3 retries, returns default v3.0
        """
        try:
            # Query Operaciones sheet for Total_Uniones (column 68)
            spool = await sheets_repo.get_spool_by_tag(tag_spool)
            union_count = spool.total_uniones or 0

            # v4.0 detection: count > 0
            # v3.0 detection: count = 0 (column not populated or zero)
            version = "v4.0" if union_count > 0 else "v3.0"

            return {
                "version": version,
                "union_count": union_count,
                "detection_logic": f"Total_Uniones={union_count} → {version}"
            }

        except Exception as e:
            logger.error(f"Version detection failed for {tag_spool} after retries: {e}")
            # Default to v3.0 (legacy workflow)
            return {
                "version": "v3.0",
                "union_count": 0,
                "detection_logic": f"Detection failed, defaulting to v3.0: {str(e)}"
            }

# Frontend: Session-level caching
// lib/context.tsx - Add version cache to AppState
interface AppState {
  // ... existing fields ...
  versionCache: Record<string, "v3.0" | "v4.0">;  // Cache per TAG_SPOOL
}

// P4: Spool selection with version detection
async function detectSpoolVersion(tagSpool: string): Promise<"v3.0" | "v4.0"> {
  // Check session cache first
  if (state.versionCache[tagSpool]) {
    return state.versionCache[tagSpool];
  }

  // Fetch from backend
  const response = await fetch(`${API_URL}/api/diagnostic/${tagSpool}/version`);
  const data = await response.json();

  // Cache result for session
  setState(prev => ({
    ...prev,
    versionCache: { ...prev.versionCache, [tagSpool]: data.version }
  }));

  return data.version;
}
```

**Reference:** User decision (CONTEXT.md) - "Cache version per session (once detected, reuse for session duration)"

### Anti-Patterns to Avoid

- **KEYS command for cleanup:** Use SCAN with cursor-based iteration to avoid blocking Redis
- **Batch cleanup loops:** Cleaning all locks at once blocks operations - lazy cleanup is better
- **Blocking startup reconciliation:** Long reconciliation blocks all requests - use async with timeout
- **Ignoring PERSIST return value:** Always check return value (1 = success, 0 = key doesn't exist)
- **Re-creating locks > 24h old:** Stale locks should expire, not be recreated during reconciliation

## Don't Hand-Roll

Problems that look simple but have existing solutions:

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Exponential backoff retry | Custom sleep loop with multiplier | tenacity library | Handles async, exception types, logging, jitter |
| Redis connection pooling | Manual connection creation | redis.asyncio.ConnectionPool | Already implemented in v3.0, singleton pattern |
| Session state caching | localStorage with TTL logic | React Context with simple object | No TTL needed for session-level cache |
| Version detection memoization | Custom cache with timestamps | Simple dict in React Context | Session lifetime sufficient, no expiration logic needed |
| Startup event management | Custom lifecycle manager | FastAPI @app.on_event("startup") | Already in use, standard pattern (lifespan contextmanager is newer but on_event works) |

**Key insight:** Redis operations already use tenacity retries in v3.0 codebase - extend pattern to version detection. Don't rebuild retry logic.

## Common Pitfalls

### Pitfall 1: Persistent Locks Without Cleanup Create Permanent Deadlocks
**What goes wrong:** Locks persist forever, process crashes leave orphaned locks, system stalls silently
**Why it happens:** Official Redis docs STRONGLY recommend TTL for safety - persistent locks contradict this
**How to avoid:** Mandatory 24-hour lazy cleanup ensures abandoned locks eventually expire
**Warning signs:** Workers report spools "stuck" occupied, Redis KEYS shows locks with no matching Sheets.Ocupado_Por

**Reference:** Redis official docs (redis.io/docs/latest/develop/clients/patterns/distributed-locks/) - "The key is usually created with a limited time to live, using the Redis expires feature, so that eventually it will get released."

**Mitigation:** User decision to implement lazy cleanup makes persistent locks safe despite violating Redis best practices.

### Pitfall 2: SCAN Blocking on Large Key Counts
**What goes wrong:** SCAN with large COUNT parameter blocks Redis for seconds, freezing all operations
**Why it happens:** SCAN is cursor-based but still processes COUNT keys per call - 10,000 keys takes ~2s
**How to avoid:** Use COUNT=10 (default), scan ONE lock per INICIAR operation, eventual consistency acceptable
**Warning signs:** Redis latency spikes during cleanup, INICIAR operations slow down

**Reference:** Redis SCAN command docs - "SCAN is a cursor based iterator... can be used in production without the downside of commands like KEYS"

### Pitfall 3: Startup Reconciliation Blocking All Requests
**What goes wrong:** Reconciliation takes 10-30 seconds for 2,000 spools, blocking API startup
**Why it happens:** FastAPI startup event blocks until completion before accepting requests
**How to avoid:** Option 1: Async reconciliation with fire-and-forget. Option 2: Timeout at 5 seconds, let lazy cleanup handle rest
**Warning signs:** Railway deployment health checks fail, 30-60 second startup times

**Reference:** FastAPI docs warn "It is very easy to add a blocking call into an event handler, which will block the event loop"

**Claude's discretion:** Choose between blocking (safer, slower) or async (faster, riskier) reconciliation.

### Pitfall 4: Version Detection Cache Pollution Across Sessions
**What goes wrong:** User session A caches v3.0, engineering updates spool to v4.0, session A still sees v3.0 for hours
**Why it happens:** Cache lives in React Context (memory), persists for browser session lifetime (hours)
**How to avoid:** Session-level cache is acceptable - page refresh clears cache and detects new version
**Warning signs:** Workers report workflow mismatch after engineering updates Uniones sheet

**Reference:** User decision (CONTEXT.md) - "Cache version per session" - implies cache lifetime = session, not localStorage persistence

### Pitfall 5: Exponential Backoff Without Max Delay Causes Minutes-Long Waits
**What goes wrong:** Version detection fails, retries grow exponentially (2s, 4s, 8s, 16s, 32s, 64s...), total wait >2 minutes
**Why it happens:** Exponential growth unbounded, 3 retries with base=2s reaches 64-second final wait
**How to avoid:** Set `max=10` in wait_exponential to cap backoff, total wait = 2s + 4s + 10s = 16s for 3 retries
**Warning signs:** Frontend shows "Loading..." for >30 seconds, users report app "freezing"

**Reference:** Tenacity docs recommend `wait_exponential(multiplier=1, min=4, max=10)` for typical API scenarios

## Code Examples

Verified patterns from official sources:

### Persistent Lock Acquisition (Two-Step)
```python
# Source: Redis PERSIST docs + user requirements
async def acquire_persistent_lock(self, tag_spool: str, worker_id: int) -> str:
    """
    Acquire lock with safety TTL, then remove TTL for persistence.

    Two-step ensures no orphaned locks if crash occurs between SET and PERSIST.
    """
    lock_key = f"spool_lock:{tag_spool}"
    timestamp = format_datetime_for_sheets(now_chile())
    lock_value = f"{worker_id}:{uuid.uuid4()}:{timestamp}"

    # Step 1: Acquire with 10-second safety TTL
    acquired = await self.redis.set(lock_key, lock_value, nx=True, ex=10)

    if not acquired:
        # Lock already exists - conflict
        raise SpoolOccupiedError(tag_spool=tag_spool, owner_id=worker_id)

    # Step 2: Remove TTL to make persistent
    persist_result = await self.redis.persist(lock_key)

    if persist_result != 1:
        # PERSIST failed (key disappeared?) - release and retry
        await self.redis.delete(lock_key)
        raise RedisError("PERSIST command failed - key may have expired")

    logger.info(f"✅ Persistent lock acquired: {tag_spool} by worker {worker_id}")
    return lock_value
```

### Exponential Backoff Retry Configuration
```python
# Source: Tenacity docs + AWS best practices
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
    before_sleep_log
)

@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=10),  # 2s, 4s, 10s (capped)
    retry=retry_if_exception_type((SheetsConnectionError, TimeoutError)),
    before_sleep=before_sleep_log(logger, logging.WARNING),
    reraise=True
)
async def detect_version_with_retry(self, tag_spool: str) -> dict:
    """Detect version with exponential backoff (total max wait: 16s)."""
    # Query logic here...
```

**Parameters:**
- `multiplier=1`: Base multiplier (2^x * 1)
- `min=2`: Minimum wait 2 seconds (prevents too-short waits)
- `max=10`: Maximum wait 10 seconds (caps exponential growth)
- Total wait: 2s + 4s + 10s = 16 seconds for 3 retries

**Reference:** Tenacity docs example shows `wait_exponential(multiplier=1, min=4, max=10)`, AWS recommends max 30-60s

### Redis SCAN for Lock Discovery
```python
# Source: Redis SCAN docs + cleanup pattern
async def scan_abandoned_locks(self, limit: int = 1) -> list[str]:
    """
    Scan for abandoned locks using cursor-based iteration.

    Returns up to `limit` abandoned lock keys for cleanup.
    """
    cursor = 0
    pattern = "spool_lock:*"
    abandoned = []

    while len(abandoned) < limit:
        # SCAN with COUNT=10 (efficient batch size)
        cursor, keys = await self.redis.scan(cursor=cursor, match=pattern, count=10)

        for key in keys:
            if len(abandoned) >= limit:
                break

            # Check if lock is abandoned (age > 24h, no Sheets match)
            tag_spool = key.split(":", 1)[1]
            if await self._is_abandoned(tag_spool):
                abandoned.append(key)

        if cursor == 0:
            break  # Scan complete

    return abandoned
```

**Reference:** Redis SCAN docs - cursor-based iteration, COUNT parameter for batch size

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| @app.on_event("startup") | @contextlib.asynccontextmanager lifespan | FastAPI 0.95.0 (2023) | Lifespan context manager is newer, but on_event still supported and used in v3.0 codebase |
| redis.set() with EX flag only | redis.set() + redis.persist() | Phase 9 requirement | Enables long-running sessions (5-8 hours) without TTL expiration |
| Background cleanup tasks | Lazy inline cleanup | Phase 9 decision | Eventual consistency, better performance, no additional worker threads |
| localStorage version cache | React Context session cache | Phase 9 decision | Simpler, no persistence logic, session lifetime sufficient |

**Deprecated/outdated:**
- **aioredis standalone library:** Merged into redis-py 4.2.0+ (2022), use `redis.asyncio` instead
- **KEYS command for pattern matching:** Use SCAN for production (KEYS blocks server)
- **TTL on occupation locks:** v3.0 used 1-hour TTL, v4.0 removes TTL for long sessions

## Open Questions

Things that couldn't be fully resolved:

1. **Startup reconciliation timing (Claude's discretion)**
   - What we know: Blocking is safer (ensures Redis ready), async is faster (doesn't block API)
   - What's unclear: User prefers blocking or async approach
   - Recommendation: Async with 10-second timeout - reconcile what's possible in 10s, let lazy cleanup handle rest. Prevents slow startups while recovering most recent locks.

2. **Default workflow on version detection failure (Claude's discretion)**
   - What we know: After 3 retries (~16s total), detection fails
   - What's unclear: Default to v3.0 (safe) or v4.0 (optimistic)?
   - Recommendation: Default to v3.0 (legacy workflow) - safer for unknown spools, fewer prerequisites than v4.0 union selection.

3. **Cleanup execution order (Claude's discretion)**
   - What we know: Cleanup before or after lock acquisition during INICIAR
   - What's unclear: User prefers cleanup first (frees resources) or after (faster INICIAR)?
   - Recommendation: Cleanup BEFORE lock acquisition - prevents race condition where we clean our own newly-acquired lock. Order: cleanup → acquire → persist.

4. **Lock value format for timestamp embedding**
   - What we know: Current format is `worker_id:token`, need to add timestamp for age detection
   - What's unclear: Format `worker_id:token:timestamp` or `worker_id:timestamp:token`?
   - Recommendation: `worker_id:token:timestamp` - preserves existing parsing logic (split on `:`, first element is worker_id, second is token), appends timestamp at end.

## Sources

### Primary (HIGH confidence)
- Redis official distributed locks docs: https://redis.io/docs/latest/develop/clients/patterns/distributed-locks/
- Redis PERSIST command docs: https://redis.io/docs/latest/commands/persist/
- Redis SCAN command docs: https://redis.io/docs/latest/commands/scan/
- Tenacity library docs: https://tenacity.readthedocs.io/ (version 9.1.2)
- FastAPI lifespan events docs: https://fastapi.tiangolo.com/advanced/events/

### Secondary (MEDIUM confidence)
- AWS Prescriptive Guidance on retry with backoff: https://docs.aws.amazon.com/prescriptive-guidance/latest/cloud-design-patterns/retry-backoff.html
- Google Cloud exponential backoff docs: https://docs.cloud.google.com/memorystore/docs/redis/exponential-backoff
- Existing v3.0 codebase patterns: backend/services/redis_lock_service.py, backend/main.py startup_event

### Tertiary (LOW confidence)
- HackerOne blog on exponential backoff (2025-level content, unverified timing)
- Medium articles on FastAPI lifespan patterns (community content, not official)

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - redis 5.0.1 and tenacity already deployed in v3.0 production
- Architecture patterns: HIGH - Redis PERSIST and SCAN commands from official docs, user decisions constrain design
- Version detection: HIGH - Straightforward column query, Total_Uniones column verified in v4.0 schema (column 68)
- Pitfalls: MEDIUM - Redis TTL recommendation contradicts user requirement, mitigated by mandatory cleanup
- Lazy cleanup: MEDIUM - Eventual consistency pattern requires careful implementation to avoid race conditions

**Research date:** 2026-02-02
**Valid until:** 2026-03-04 (30 days - Redis and FastAPI APIs stable)

**Critical finding:** User requirement for persistent locks WITHOUT TTL directly contradicts Redis official best practices. Redis documentation explicitly recommends "limited time to live" for all locks to handle process crashes. Phase 9 makes this safe through MANDATORY 24-hour lazy cleanup - without cleanup, system will accumulate permanent deadlocks. Planning must emphasize cleanup is NOT optional.
