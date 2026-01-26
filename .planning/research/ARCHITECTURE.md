# Architecture Research: Real-Time Location Tracking + State Management

**Domain:** Manufacturing Traceability with Real-Time State Transitions
**Researched:** January 26, 2026
**Confidence:** MEDIUM (patterns verified, Google Sheets constraints documented, some areas need validation)

## Executive Summary

v3.0 adds real-time location tracking and state machines to ZEUES v2.1's clean architecture. The research reveals that **Server-Sent Events (SSE) + Redis caching** is the optimal pattern for manufacturing floor tracking with Google Sheets as the source of truth. The architecture uses **optimistic locking with timestamp checks** for conflict prevention and **python-statemachine** for managing occupation/progress states.

**Key Finding:** Google Sheets API limits (60 writes/min/user) make **direct polling expensive**. Solution: **Write-through cache** (Redis) + **SSE for real-time UI updates** + **batch operations** for scalability.

---

## Recommended Architecture v3.0

### System Overview

```
┌─────────────────────────────────────────────────────────────┐
│                    Frontend (Next.js)                        │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐       │
│  │  Worker UI   │  │  Supervisor  │  │  Dashboard   │       │
│  │  (Tablets)   │  │  Monitor     │  │  (Analytics) │       │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘       │
│         │                 │                 │               │
│         └─────────────────┴─────────────────┘               │
│                           │                                 │
│                      SSE Connection                         │
│                  (unidirectional updates)                   │
└───────────────────────────┼─────────────────────────────────┘
                            │
                            ↓
┌─────────────────────────────────────────────────────────────┐
│                  Backend (FastAPI)                           │
├─────────────────────────────────────────────────────────────┤
│  Routers (HTTP + SSE endpoints)                              │
│  ├─ POST /api/tomar-spool                                    │
│  ├─ POST /api/pausar-spool                                   │
│  ├─ GET /api/sse/spools-updates  ← SSE endpoint              │
│  └─ GET /api/spools/disponibles                              │
├─────────────────────────────────────────────────────────────┤
│  Services (Business Logic + State Machines)                  │
│  ├─ OccupationService (TOMAR/PAUSAR/COMPLETAR)              │
│  ├─ StateService (SpoolStateMachine)                         │
│  ├─ ConflictService (optimistic locking)                     │
│  └─ ValidationService (v2.1 extended)                        │
├─────────────────────────────────────────────────────────────┤
│  Repositories (Data Access)                                  │
│  ├─ SheetsRepository (Google Sheets API)                     │
│  ├─ MetadataRepository (Event log)                           │
│  └─ CacheRepository (Redis - NEW)                            │
├─────────────────────────────────────────────────────────────┤
│  Cache Layer (Redis)                                         │
│  ├─ Spool states (TTL: 60s)                                  │
│  ├─ Worker locations (TTL: 30s)                              │
│  ├─ Occupation locks (with timestamps)                       │
│  └─ SSE subscribers registry                                 │
└───────────────┬─────────────────────────────────────────────┘
                │
                ↓
┌─────────────────────────────────────────────────────────────┐
│              Google Sheets (Source of Truth)                 │
├─────────────────────────────────────────────────────────────┤
│  Operaciones Sheet (READ/WRITE)                              │
│  ├─ [NEW] Ocupado_Por (worker_id)                            │
│  ├─ [NEW] Fecha_Ocupacion (timestamp)                        │
│  ├─ [NEW] Estado_Progreso (0-100%)                           │
│  ├─ Armador, Soldador (v2.1)                                 │
│  └─ TAG_SPOOL, Fecha_Materiales (v2.1)                       │
├─────────────────────────────────────────────────────────────┤
│  Metadata Sheet (APPEND-ONLY audit log)                      │
│  └─ [NEW] TOMAR_SPOOL, PAUSAR_SPOOL, ACTUALIZAR_PROGRESO    │
└─────────────────────────────────────────────────────────────┘
```

### Component Responsibilities

| Component | Responsibility | v3.0 Changes |
|-----------|----------------|--------------|
| **Frontend (SSE Client)** | Consume real-time updates, display spool availability, send TOMAR/PAUSAR actions | NEW: EventSource API for SSE, real-time state indicators |
| **SSE Router** | Stream spool state changes to connected clients | NEW: `/api/sse/spools-updates` endpoint |
| **OccupationService** | Orchestrate TOMAR/PAUSAR/COMPLETAR with conflict detection | NEW: Check Redis lock before Sheets write |
| **StateService** | Manage state machine transitions (DISPONIBLE → OCUPADO → EN_PROGRESO → COMPLETADO) | NEW: python-statemachine integration |
| **ConflictService** | Implement optimistic locking with timestamps | NEW: Detect simultaneous TOMAR attempts |
| **CacheRepository** | Redis read/write with TTL management | NEW: Write-through cache for hot data |
| **SheetsRepository** | Batch writes to Operaciones sheet (v2.1 extended) | EXTENDED: New occupation columns |
| **MetadataRepository** | Audit trail for all state transitions (v2.1 extended) | EXTENDED: New event types (TOMAR, PAUSAR, PROGRESO) |

---

## Architectural Patterns

### Pattern 1: Write-Through Cache (Redis + Google Sheets)

**What:** All writes go to Redis first (fast), then asynchronously sync to Google Sheets (slow). Reads check Redis cache first, fall back to Sheets on miss.

**When to use:** When source of truth is slow (Google Sheets: 200-500ms latency) and reads far outnumber writes (manufacturing floor: 50 workers reading spools availability).

**Trade-offs:**
- **Pros:** Sub-50ms read latency, reduces Google Sheets API calls by 80-90%, supports real-time UI updates
- **Cons:** Cache invalidation complexity, Redis becomes critical dependency, potential cache-DB inconsistency (mitigated by TTL + background sync)

**Implementation:**
```python
# CacheRepository pattern
class CacheRepository:
    def __init__(self, redis_client, ttl_seconds=60):
        self.redis = redis_client
        self.ttl = ttl_seconds

    async def get_spool_state(self, tag_spool: str) -> Optional[SpoolState]:
        # 1. Try cache first (< 5ms)
        cached = await self.redis.get(f"spool:{tag_spool}")
        if cached:
            return SpoolState.parse_raw(cached)

        # 2. Cache miss → fetch from Sheets (200-500ms)
        spool = await sheets_repo.get_spool(tag_spool)
        if spool:
            # 3. Populate cache with TTL
            await self.redis.setex(
                f"spool:{tag_spool}",
                self.ttl,
                spool.json()
            )
        return spool

    async def set_spool_occupation(
        self,
        tag_spool: str,
        worker_id: int,
        timestamp: datetime
    ):
        # 1. Write to cache immediately (< 10ms)
        await self.redis.hset(
            f"spool:{tag_spool}",
            mapping={
                "ocupado_por": worker_id,
                "fecha_ocupacion": timestamp.isoformat()
            }
        )
        await self.redis.expire(f"spool:{tag_spool}", self.ttl)

        # 2. Background task: sync to Sheets (200-500ms)
        background_tasks.add_task(
            sheets_repo.update_spool_occupation,
            tag_spool,
            worker_id,
            timestamp
        )

        # 3. Publish SSE event for real-time updates
        await sse_manager.broadcast({
            "event": "spool_occupied",
            "tag_spool": tag_spool,
            "worker_id": worker_id
        })
```

**Cache Invalidation Strategy:**
- **TTL-based expiry:** 60s for spool states (balance freshness vs API load)
- **Event-driven invalidation:** Delete cache key on TOMAR/PAUSAR/COMPLETAR
- **Scheduled refresh:** Background job every 5 minutes syncs hot spools (those accessed in last hour)

---

### Pattern 2: Server-Sent Events (SSE) for Real-Time Updates

**What:** HTTP connection from server to clients that streams updates as they happen. Server pushes events, clients listen passively. One-way: server → client.

**When to use:** Manufacturing floor tablets need to see when spools become available/occupied, but don't need to send frequent updates back (they POST actions via REST).

**Trade-offs:**
- **Pros:** Simpler than WebSockets (HTTP-based, auto-reconnects, works through proxies), lower overhead, easier deployment (no CORS issues)
- **Cons:** Unidirectional (sufficient for this use case), older browsers need polyfill (not an issue with modern tablets)

**Why SSE over WebSockets:**
- Workers mostly READ state (which spools are available)
- Actions (TOMAR/PAUSAR) are infrequent (< 1 per minute per worker)
- SSE uses HTTP (easier Railway/Vercel deployment)
- WebSockets require sticky sessions (complicates horizontal scaling)

**Implementation:**
```python
# FastAPI SSE endpoint
from fastapi import FastAPI
from sse_starlette.sse import EventSourceResponse
import asyncio

@app.get("/api/sse/spools-updates")
async def stream_spool_updates(operacion: str):
    """
    SSE endpoint - streams spool state changes to connected clients.

    Client connects: EventSource('/api/sse/spools-updates?operacion=ARM')
    Server pushes: { event: 'spool_occupied', data: {...} }
    """
    async def event_generator():
        # Subscribe to Redis pub/sub channel
        pubsub = redis.pubsub()
        await pubsub.subscribe(f"spools:{operacion}")

        try:
            while True:
                # Wait for events from Redis
                message = await pubsub.get_message(timeout=30)
                if message and message['type'] == 'message':
                    yield {
                        "event": "update",
                        "data": message['data'].decode()
                    }
                else:
                    # Heartbeat every 30s to keep connection alive
                    yield {
                        "event": "ping",
                        "data": "keep-alive"
                    }
        finally:
            await pubsub.unsubscribe(f"spools:{operacion}")

    return EventSourceResponse(event_generator())

# Frontend (Next.js)
useEffect(() => {
    const eventSource = new EventSource(
        '/api/sse/spools-updates?operacion=ARM'
    );

    eventSource.addEventListener('update', (e) => {
        const data = JSON.parse(e.data);
        updateSpoolState(data); // Re-render UI
    });

    return () => eventSource.close();
}, [operacion]);
```

**SSE vs Polling Performance:**
| Approach | API Calls (10 workers, 5 min) | Latency | Complexity |
|----------|-------------------------------|---------|------------|
| **Short polling (5s)** | 600 calls | 0-5s delay | Low |
| **Long polling** | ~50 calls | < 1s delay | Medium |
| **SSE (recommended)** | 0 calls (push-based) | < 100ms | Medium |

---

### Pattern 3: Optimistic Locking with Timestamps

**What:** Allow multiple workers to attempt TOMAR simultaneously, but detect conflicts by checking timestamps. Last-write-wins rejected if another worker took the spool in between.

**When to use:** Google Sheets doesn't support database-level locks. Conflict scenario: Worker A and Worker B both click TOMAR on same spool at same moment.

**Trade-offs:**
- **Pros:** No need for distributed locks, simple implementation, graceful failure (one worker gets 409 Conflict)
- **Cons:** Race condition possible (mitigated by Redis atomic operations), retry logic needed in frontend

**Implementation:**
```python
# ConflictService
class ConflictService:
    async def try_occupy_spool(
        self,
        tag_spool: str,
        worker_id: int,
        timestamp: datetime
    ) -> bool:
        """
        Attempt to occupy spool with optimistic locking.
        Returns True if successful, False if conflict detected.
        """
        # 1. Atomic check-and-set in Redis
        lock_key = f"lock:spool:{tag_spool}"
        acquired = await redis.set(
            lock_key,
            worker_id,
            nx=True,  # Only set if doesn't exist (atomic)
            ex=300    # Lock expires in 5 minutes (safety)
        )

        if not acquired:
            # Another worker already took it
            current_owner = await redis.get(lock_key)
            logger.warning(
                f"Conflict: {tag_spool} already occupied by worker {current_owner}"
            )
            return False

        # 2. Check Google Sheets for double-verification
        spool = await sheets_repo.get_spool(tag_spool)
        if spool.ocupado_por is not None:
            # Race condition: Another process wrote to Sheets
            await redis.delete(lock_key)  # Release our lock
            raise SpoolYaOcupadoError(
                f"Spool {tag_spool} occupied by worker {spool.ocupado_por}"
            )

        # 3. Write to Sheets with timestamp
        await sheets_repo.update_spool_occupation(
            tag_spool,
            worker_id,
            timestamp
        )

        # 4. Verify write succeeded (read-after-write check)
        spool_verify = await sheets_repo.get_spool(tag_spool)
        if spool_verify.ocupado_por != worker_id:
            # Conflict: Another worker wrote after us
            await redis.delete(lock_key)
            raise SpoolOcupacionConflictError(
                f"Write conflict on {tag_spool}"
            )

        return True
```

**Conflict Resolution Strategy:**
1. **Prevention (Redis atomic ops):** Use `SETNX` (set if not exists) for lock acquisition
2. **Detection (timestamp checks):** Compare `fecha_ocupacion` in Sheets before overwriting
3. **Resolution (HTTP 409):** Return conflict error to client, frontend shows "Already taken by Worker X"
4. **Recovery (automatic):** Lock expires after 5 minutes (safety for crashed clients)

---

### Pattern 4: State Machine for Occupation Lifecycle

**What:** Model spool occupation as a state machine with explicit states and transition guards. Prevents invalid transitions (can't COMPLETAR if not OCUPADO).

**When to use:** Complex business logic with multiple states (DISPONIBLE → OCUPADO → EN_PROGRESO → PAUSADO → COMPLETADO) and business rules (only owner can pause, can't complete if progress < 100%).

**Trade-offs:**
- **Pros:** Type-safe transitions, centralized business rules, easy to test, self-documenting
- **Cons:** More boilerplate, learning curve for python-statemachine library

**Implementation:**
```python
# StateService with python-statemachine
from statemachine import StateMachine, State

class SpoolStateMachine(StateMachine):
    """
    State machine for spool occupation lifecycle.

    States:
    - disponible: Ready to be taken
    - ocupado: Worker has claimed but not started
    - en_progreso: Worker actively working (progress 1-99%)
    - pausado: Worker paused work
    - completado: Operation finished (progress 100%)
    """

    # Define states
    disponible = State(initial=True)
    ocupado = State()
    en_progreso = State()
    pausado = State()
    completado = State(final=True)

    # Define transitions
    tomar = disponible.to(ocupado)
    iniciar = ocupado.to(en_progreso)
    pausar = en_progreso.to(pausado) | en_progreso.to(en_progreso)
    reanudar = pausado.to(en_progreso)
    completar = en_progreso.to(completado)
    cancelar = (ocupado.to(disponible) |
                en_progreso.to(disponible) |
                pausado.to(disponible))

    # Transition guards (conditions)
    def before_tomar(self, worker_id: int):
        """Only allow TOMAR if spool is actually disponible."""
        if self.spool.ocupado_por is not None:
            raise SpoolYaOcupadoError(
                f"Spool already occupied by worker {self.spool.ocupado_por}"
            )

    def before_iniciar(self, worker_id: int):
        """Only owner can INICIAR."""
        if self.spool.ocupado_por != worker_id:
            raise NoAutorizadoError(
                f"Only worker {self.spool.ocupado_por} can start this spool"
            )

    def before_completar(self, worker_id: int):
        """Only owner can COMPLETAR, and progress must be 100%."""
        if self.spool.ocupado_por != worker_id:
            raise NoAutorizadoError("Not the owner")
        if self.spool.estado_progreso < 100:
            raise ProgresoIncompletoError(
                f"Progress is {self.spool.estado_progreso}%, need 100%"
            )

    # State callbacks
    def on_enter_ocupado(self, worker_id: int, timestamp: datetime):
        """Write to Sheets when entering OCUPADO state."""
        logger.info(f"Spool {self.spool.tag_spool} occupied by {worker_id}")
        sheets_repo.update_spool_occupation(
            self.spool.tag_spool,
            worker_id,
            timestamp
        )
        metadata_repo.append_event(
            MetadataEvent(
                evento_tipo=EventoTipo.TOMAR_SPOOL,
                tag_spool=self.spool.tag_spool,
                worker_id=worker_id,
                timestamp=timestamp
            )
        )

    def on_enter_completado(self):
        """Release occupation when completed."""
        logger.info(f"Spool {self.spool.tag_spool} completed")
        sheets_repo.clear_spool_occupation(self.spool.tag_spool)

# Usage in OccupationService
class OccupationService:
    async def tomar_spool(
        self,
        tag_spool: str,
        worker_id: int
    ) -> ActionResponse:
        # 1. Load spool
        spool = await spool_service.get_spool(tag_spool)

        # 2. Initialize state machine
        sm = SpoolStateMachine(spool=spool)

        # 3. Attempt transition (will call guards)
        try:
            sm.tomar(worker_id=worker_id)
        except TransitionNotAllowed as e:
            raise OperacionInvalidaError(f"Cannot TOMAR: {e}")

        # 4. Conflict detection (optimistic locking)
        success = await conflict_service.try_occupy_spool(
            tag_spool,
            worker_id,
            datetime.utcnow()
        )
        if not success:
            raise SpoolOcupacionConflictError("Another worker took the spool")

        return ActionResponse(
            message=f"Spool {tag_spool} taken successfully",
            data=ActionData(tag_spool=tag_spool, operacion="TOMAR")
        )
```

**State Diagram:**
```
                    TOMAR
    [DISPONIBLE] --------→ [OCUPADO]
         ↑                     ↓
         |                  INICIAR
         |                     ↓
         |              [EN_PROGRESO] ←--→ [PAUSADO]
         |                     ↓       PAUSAR / REANUDAR
         |                 COMPLETAR
         |                     ↓
         └─────────────── [COMPLETADO]
                CANCELAR
```

---

## Data Flow

### Request Flow: TOMAR Spool (New Action)

```
[Worker Tablet]
    ↓ POST /api/tomar-spool {worker_id, operacion, tag_spool}
[FastAPI Router]
    ↓ Call OccupationService.tomar_spool()
[OccupationService]
    ↓ 1. Validate worker has role (RoleService)
    ↓ 2. Load spool (SpoolService)
    ↓ 3. Check state machine (StateService)
    ↓ 4. Attempt occupation (ConflictService - optimistic lock)
[ConflictService]
    ↓ 1. Atomic Redis SETNX lock:spool:{tag}
    ↓ 2. Verify Sheets ocupado_por = NULL
    ↓ 3. Write to Sheets (background task)
    ↓ 4. Write to Metadata (audit log)
    ↓ 5. Publish Redis event → SSE
[Response to Worker]
    ← 200 OK {message: "Spool taken", data: {...}}

[SSE Broadcast]
    → All connected clients receive:
      {event: "spool_occupied", tag_spool, worker_id}
    → Other tablets hide spool from available list
```

### State Query Flow: Spools Disponibles

```
[Worker Tablet]
    ↓ GET /api/spools/disponibles?operacion=ARM
[FastAPI Router]
    ↓ Call SpoolService.get_spools_disponibles()
[SpoolService]
    ↓ 1. Check Redis cache (< 5ms)
[CacheRepository]
    ↓ Cache hit? Return cached list
    ↓ Cache miss? Fetch from Sheets
[SheetsRepository]
    ↓ 1. Read Operaciones sheet (200-500ms)
    ↓ 2. Filter: ocupado_por = NULL AND dependencies met
    ↓ 3. Populate cache with TTL=60s
    ↓ 4. Return results
[Response to Worker]
    ← 200 OK {spools: [{tag_spool, ...}, ...]}
```

### SSE Real-Time Update Flow

```
[Worker A takes spool MK-001]
    ↓ POST /api/tomar-spool
[OccupationService]
    ↓ Write to Redis + Sheets
    ↓ Publish event: redis.publish("spools:ARM", {tag: "MK-001", occupied: true})
[Redis Pub/Sub]
    ↓ Fanout to all SSE subscribers
[SSE Event Generator]
    ↓ yield {"event": "spool_occupied", "data": "{\"tag_spool\": \"MK-001\", ...}"}
[EventSource connection (Workers B, C, D)]
    ↓ Receive event in < 100ms
[Frontend React State]
    ↓ updateSpoolState(data)
    ↓ Remove MK-001 from available list
    ↓ Show "Occupied by Worker 93" badge
```

---

## Scaling Considerations

| Constraint | Current (v2.1) | At 50 workers | At 200 workers | At 1000+ workers |
|------------|----------------|---------------|----------------|------------------|
| **Google Sheets API** | 60 writes/min/user | Batch writes required | Multiple service accounts | Migrate to PostgreSQL |
| **Redis connections** | N/A | Single Redis instance OK | Redis Cluster | Redis Cluster + Sharding |
| **SSE connections** | N/A | 50 concurrent OK | Need load balancer | Sticky sessions + Redis pub/sub |
| **State latency** | N/A | < 100ms (cache) | < 200ms | < 500ms (acceptable) |

### Scaling Priorities

**First bottleneck (50-100 workers):** Google Sheets write rate limit (60/min/user)

**Solution:**
1. Batch operations: Group writes every 5 seconds instead of immediate
2. Multiple service accounts: Rotate between 3 accounts (180 writes/min total)
3. Write coalescing: If same spool updated twice in 5s window, only send final state

**Second bottleneck (200+ workers):** Redis memory + SSE connections

**Solution:**
1. Redis Cluster: Shard by spool prefix (MK-* on node 1, RP-* on node 2)
2. Sticky sessions: Load balancer pins worker to same FastAPI instance (for SSE)
3. Horizontal scaling: 3+ FastAPI instances behind load balancer, Redis pub/sub coordinates SSE broadcasts

**Third bottleneck (1000+ workers):** Google Sheets becomes impractical

**Solution:**
1. Migrate to PostgreSQL with real-time replication
2. Keep Sheets as read-only export for management
3. Event Sourcing becomes more critical (Metadata is full audit trail)

---

## Anti-Patterns

### Anti-Pattern 1: Polling Google Sheets Directly from Frontend

**What people do:** Frontend calls GET /api/spools/disponibles every 5 seconds to detect changes

**Why it's wrong:**
- Burns through Google Sheets API quota (60 requests/min/user exhausted by 12 workers)
- High latency (200-500ms per poll)
- Stale data (up to 5 seconds old)
- Unnecessary backend load

**Do this instead:**
- Use SSE to push updates to frontend (0 API calls during idle)
- Cache hot data in Redis (reads are < 5ms)
- Only poll Sheets on cache miss or manual refresh

---

### Anti-Pattern 2: Using WebSockets When SSE Suffices

**What people do:** Implement full WebSocket bidirectional connection for real-time updates

**Why it's wrong:**
- Workers don't need to send frequent updates (only POST actions occasionally)
- WebSockets require sticky sessions (complicates deployment)
- More complex error handling (need custom reconnection logic)
- CORS and proxy issues in corporate networks

**Do this instead:**
- Use SSE for server → client updates (browser auto-reconnects)
- Use REST POST for client → server actions (TOMAR, PAUSAR)
- Simpler deployment (HTTP-only, works through proxies)

---

### Anti-Pattern 3: Pessimistic Locking in Google Sheets

**What people do:** Try to implement distributed locks by writing a "lock" column before reading

**Why it's wrong:**
- Google Sheets API doesn't support atomic compare-and-swap
- Race conditions still possible (two writes at same millisecond)
- Lock cleanup is fragile (crashed client leaves lock forever)
- Increases API calls (lock acquire + lock release = 2x writes)

**Do this instead:**
- Use Redis for locks (atomic SETNX operation)
- Use optimistic locking with timestamps (simpler, graceful conflicts)
- Google Sheets is source of truth, not lock coordinator

---

### Anti-Pattern 4: Storing Volatile State in Google Sheets

**What people do:** Write progress updates (1%, 2%, 3%...) to Sheets as worker makes incremental progress

**Why it's wrong:**
- Progress updates are frequent (potentially every 10s)
- Exhausts API quota (60 writes/min = 1 per second, not enough for 50 workers)
- Sheets not designed for high-frequency volatile data
- Creates noise in Metadata audit log

**Do this instead:**
- Store progress in Redis with short TTL (30s)
- Only write to Sheets on major milestones (INICIAR, PAUSAR, COMPLETAR)
- Use WebSockets/SSE to stream progress to frontend (bypasses Sheets)
- Aggregate progress in Metadata (e.g., every 25% instead of every 1%)

---

## Integration Points

### External Services

| Service | Integration Pattern | Notes |
|---------|---------------------|-------|
| **Google Sheets API** | Batch operations via gspread | 60 writes/min/user limit, 2MB max payload, use exponential backoff on 429 |
| **Redis** | Write-through cache + pub/sub | Single instance OK for 50 workers, use Redis Cluster for 200+ |
| **Railway** | Docker deployment with environment variables | FastAPI + Redis in same project, use Railway's internal networking |

### Internal Boundaries

| Boundary | Communication | Notes |
|----------|---------------|-------|
| **Frontend ↔ Backend (Actions)** | REST POST (HTTP) | /api/tomar-spool, /api/pausar-spool - use existing ActionRequest pattern |
| **Frontend ↔ Backend (Updates)** | SSE (HTTP stream) | /api/sse/spools-updates?operacion=ARM - unidirectional push |
| **OccupationService ↔ StateService** | Direct method calls | StateService validates transitions, OccupationService orchestrates I/O |
| **FastAPI ↔ Redis** | redis-py async client | Use connection pooling, 5s timeout, exponential backoff on errors |
| **FastAPI instances (horizontal scaling)** | Redis pub/sub | Coordinate SSE broadcasts across instances |

---

## v3.0 Architecture Recommendations

### Phase 1: Foundation (Redis + Basic State Machine)

**Goal:** Add Redis caching and simple occupation tracking without breaking v2.1

**Components:**
1. CacheRepository with read-through pattern
2. Basic SpoolStateMachine (DISPONIBLE → OCUPADO → COMPLETADO)
3. New endpoints: POST /api/tomar-spool, POST /api/liberar-spool
4. Extend Operaciones sheet: Add columns Ocupado_Por, Fecha_Ocupacion
5. Extend Metadata: Add events TOMAR_SPOOL, LIBERAR_SPOOL

**Dependencies:**
- Redis must be deployed before FastAPI can use it
- SheetsRepository must support new columns (add to dynamic header mapping)
- Frontend still uses existing v2.1 flow (no real-time updates yet)

**Success Criteria:**
- Redis cache reduces Sheets API calls by 70%+
- TOMAR/LIBERAR actions complete in < 500ms
- Basic conflict detection prevents double-occupation

**Effort:** ~3-4 days (1 day Redis setup, 2 days service implementation, 1 day testing)

---

### Phase 2: Real-Time Updates (SSE)

**Goal:** Add live updates so tablets see when spools become available/occupied

**Components:**
1. SSE endpoint: GET /api/sse/spools-updates
2. Redis pub/sub for event broadcasting
3. Frontend EventSource integration
4. SSE connection manager (track active clients)

**Dependencies:**
- Phase 1 complete (Redis operational)
- Frontend refactor to React hooks for SSE
- Load balancer configured for long-lived HTTP connections

**Success Criteria:**
- Workers see spool occupation changes in < 200ms
- SSE connection stays alive for 8-hour work shift
- Auto-reconnect on network interruption

**Effort:** ~2-3 days (1 day backend SSE, 1 day frontend integration, 1 day testing)

---

### Phase 3: Advanced State Machine (Progress + Pause)

**Goal:** Add progress tracking (0-100%) and PAUSAR/REANUDAR actions

**Components:**
1. Extended SpoolStateMachine (add PAUSADO state)
2. Progress updates via Redis (don't write every update to Sheets)
3. Milestone writes to Sheets (every 25% progress)
4. Frontend progress bars with real-time updates

**Dependencies:**
- Phase 2 complete (SSE working)
- Business rules defined (when can worker pause? can others see progress?)

**Success Criteria:**
- Workers can pause and resume work
- Progress visible to supervisors in real-time
- Sheets only stores milestones (not noisy)

**Effort:** ~3-4 days (2 days state machine extension, 1 day frontend, 1 day testing)

---

### Phase 4: Conflict Resolution + Reparación Loop

**Goal:** Handle edge cases (simultaneous TOMAR, cyclic Metrología → Reparación flow)

**Components:**
1. ConflictService with optimistic locking
2. Rework state machine to allow loops (EN_PROGRESO → METROLOGIA → REPARACION → EN_PROGRESO)
3. Enhanced Metadata queries (show full history of spool repairs)
4. Supervisor override endpoint (force-release stuck spools)

**Dependencies:**
- Phase 3 complete (state machine working)
- Business rules for repair cycles defined

**Success Criteria:**
- Conflict error rate < 1% (most attempts succeed)
- Reparación loop works without manual intervention
- Stuck spools can be recovered by supervisor

**Effort:** ~4-5 days (2 days conflict logic, 2 days repair loop, 1 day testing)

---

## Build Order Implications

**Critical Path:**
1. **Redis Deployment** (blocker for Phase 1)
2. **CacheRepository + Basic State Machine** (Phase 1 - foundation for everything)
3. **SSE Endpoint** (Phase 2 - needed for real-time UX)
4. **Frontend SSE Integration** (Phase 2 - parallel with backend if APIs defined)
5. **Extended State Machine** (Phase 3 - builds on Phase 1/2)
6. **Conflict Resolution** (Phase 4 - polish, can be deferred if tight deadline)

**Parallel Tracks:**
- Backend state machine work can happen in parallel with frontend SSE integration (if API contract defined upfront)
- Metadata schema changes can happen alongside CacheRepository (independent)

**Deferred:**
- Progress tracking can be Phase 3.5 if Phase 3 scope too large
- Reparación loop is nice-to-have for v3.0, can be v3.1

---

## Sources

**HIGH CONFIDENCE:**
- [Google Sheets API Limits - Official Docs](https://developers.google.com/workspace/sheets/api/limits) - Rate limits: 60 writes/min/user, batch operations, exponential backoff
- [FastAPI WebSockets - Official Docs](https://fastapi.tiangolo.com/advanced/websockets/) - WebSocket patterns, connection management, dependency injection
- [python-statemachine - Official Docs](https://python-statemachine.readthedocs.io/en/latest/) - State machines, transitions, guards, callbacks

**MEDIUM CONFIDENCE:**
- [SSE vs WebSockets Comparison](https://fictionally-irrelevant.vercel.app/posts/why-you-should-use-server-side-events-over-web-sockets-and-long-polling) - Real-world comparison, SSE recommended for unidirectional updates
- [FastAPI Redis Caching Patterns](https://redis.io/learn/develop/python/fastapi) - Redis integration, connection pooling, TTL strategies
- [Optimistic vs Pessimistic Locking](https://medium.com/@captain-uchiha/minimizing-lock-contention-optimistic-vs-pessimistic-locking-explained-clearly-0d3f6da9464a) - Jan 2026 article on locking strategies

**LOW CONFIDENCE (WebSearch only, needs validation):**
- State machine patterns for manufacturing - general concepts from multiple sources, not FastAPI-specific
- Redis pub/sub for SSE coordination - best practice from community posts, not official documentation
- Google Sheets conflict resolution - inferred from API behavior, not explicitly documented

---

*Architecture research for: ZEUES v3.0 Real-Time Location Tracking*
*Researched: January 26, 2026*
*Next step: Roadmap creation with phase structure based on these patterns*
