# Technology Stack Research: Real-Time Location Tracking

**Project:** ZEUES v3.0 Real-Time Location Tracking
**Domain:** Manufacturing Traceability - Real-time occupation and location tracking
**Researched:** 2026-01-26
**Confidence:** HIGH

## Executive Summary

v3.0 adds real-time location tracking and occupation state management to existing v2.1 FastAPI + Google Sheets stack. Research focused on: (1) real-time communication patterns, (2) concurrency control for physical resource occupation, (3) state machine libraries for dynamic states, and (4) event sourcing continuation.

**Recommended approach:** Server-Sent Events (SSE) + polling hybrid, python-statemachine for state management, optimistic locking with version tokens, continue v2.1 event sourcing architecture.

---

## Recommended Stack

### Core Technologies (Existing v2.1 - KEEP)

| Technology | Version | Purpose | Why Recommended |
|------------|---------|---------|-----------------|
| **Python** | 3.11+ | Backend runtime | Already in production, async/await native, excellent library ecosystem |
| **FastAPI** | 0.121.0+ | Web framework | Native WebSocket + SSE support, async-first, already deployed |
| **gspread** | 6.2.1+ | Google Sheets API | Already integrated, batch operations proven in v2.1 |
| **Pydantic** | 2.12.4+ | Data validation | Already used, excellent for state machine validation |
| **Next.js** | 14.x | Frontend framework | Already deployed, built-in SSE support via fetch API |
| **Railway** | N/A | Backend hosting | Already configured, supports WebSockets and long-lived connections |
| **Vercel** | N/A | Frontend hosting | Already configured, no changes needed |

### New Technologies for v3.0

| Technology | Version | Purpose | Why Recommended |
|------------|---------|---------|-----------------|
| **python-statemachine** | 2.5.0+ | State machine engine | Async native, 100% test coverage, expressive API, Django-ready for future |
| **sse-starlette** | 2.2.0+ | Server-Sent Events | FastAPI-compatible, production-ready SSE implementation (Starlette-based) |

### Supporting Libraries

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| **python-dateutil** | 2.9.0+ (existing) | Timestamp handling | Already used, keep for consistency |
| **pytest-asyncio** | 0.25.0+ | Async testing | Testing state machines and SSE endpoints |
| **httpx** | 0.28.1+ (existing) | HTTP client | Already used, keep for API tests |

### Development Tools

| Tool | Purpose | Notes |
|------|---------|-------|
| **pytest** | Testing framework | Already configured, add async fixtures |
| **uvicorn** | ASGI server | Already used, supports SSE long-lived connections |
| **Playwright** | E2E testing | Already configured, test real-time updates |

---

## Installation

```bash
# Backend - New dependencies only (v3.0 additions)
cd backend
source venv/bin/activate  # ALWAYS activate first

# State machine
pip install python-statemachine==2.5.0

# Server-Sent Events
pip install sse-starlette==2.2.0

# Testing async
pip install pytest-asyncio==0.25.0

# Update requirements
pip freeze > requirements.txt

# Frontend - NO new dependencies needed
# Next.js 14 has native EventSource API support
```

---

## Real-Time Communication Strategy

### Recommended: Server-Sent Events (SSE) for v3.0

**Decision:** Use SSE instead of WebSockets

**Rationale:**

1. **Unidirectional communication sufficient** - v3.0 needs server → client updates (who has what spool), NOT bidirectional chat
2. **HTTP-based simplicity** - SSE works over regular HTTP, firewall-friendly, no special infrastructure needed on Railway/Vercel
3. **Built-in reconnection** - EventSource API auto-reconnects on network drops (critical for factory tablets)
4. **Lower resource consumption** - SSE uses less memory than WebSockets for unidirectional streams
5. **Easier debugging** - SSE is text-based, debuggable with curl/browser DevTools
6. **Native browser support** - No libraries needed on frontend (EventSource API standard)

**Confidence:** HIGH (verified with FastAPI official docs + 2025 production patterns)

### SSE Implementation Pattern

**Backend (FastAPI + sse-starlette):**
```python
from sse_starlette.sse import EventSourceResponse
from fastapi import APIRouter

router = APIRouter()

@router.get("/api/sse/spools")
async def spool_updates(worker_id: int):
    """
    Stream spool occupation updates to client.
    Client receives events when ANY spool changes state.
    """
    async def event_generator():
        while True:
            # Poll Google Sheets every 5 seconds
            changes = await check_for_changes()
            if changes:
                yield {
                    "event": "spool_update",
                    "data": json.dumps(changes)
                }
            await asyncio.sleep(5)

    return EventSourceResponse(event_generator())
```

**Frontend (Next.js 14 - native EventSource):**
```typescript
// No libraries needed - built-in browser API
const eventSource = new EventSource(`/api/sse/spools?worker_id=${workerId}`);

eventSource.onmessage = (event) => {
  const updates = JSON.parse(event.data);
  // Update UI with real-time changes
};

eventSource.onerror = (error) => {
  // Auto-reconnects by default
};
```

**Confidence:** HIGH (official FastAPI patterns + Browser standard API)

---

## Alternatives Considered

| Category | Recommended | Alternative | Why Not Alternative |
|----------|-------------|-------------|---------------------|
| **Real-time** | SSE | WebSockets | Overkill - v3.0 doesn't need bidirectional. WebSockets require more complex connection management, no auto-reconnect. |
| **Real-time** | SSE | Short polling (5-10s) | SSE more efficient - keeps connection open, lower latency. Polling acceptable as fallback. |
| **Real-time** | SSE | Long polling | SSE cleaner - native browser API vs manual AJAX loop. Both HTTP-based but SSE has better DX. |
| **State machine** | python-statemachine | Transitions | python-statemachine has better async support, 100% test coverage, more active (2025 updates). |
| **State machine** | python-statemachine | Statesman | Statesman archived/inactive. python-statemachine actively maintained. |
| **Pub/Sub** | None (SSE direct) | Redis pub/sub | Unnecessary dependency - Google Sheets IS the source of truth. SSE + polling simpler. |
| **Pub/Sub** | None (SSE direct) | Kafka | Massive overkill for 10-20 concurrent workers. Adds operational complexity. |
| **Locking** | Optimistic (version tokens) | Pessimistic (row locks) | Google Sheets doesn't support true locking. Optimistic works with Sheets' eventual consistency. |

---

## What NOT to Use

| Avoid | Why | Use Instead |
|-------|-----|-------------|
| **WebSockets** | Bidirectional overhead unnecessary - v3.0 is server → client only | **SSE** - simpler, HTTP-based, auto-reconnect |
| **Redis/external message broker** | Adds operational complexity, Google Sheets is already source of truth | **SSE + polling Google Sheets** directly |
| **Database (Postgres/MySQL)** | Conflicts with v2.1 architecture (Google Sheets = source of truth) | **Continue Google Sheets** + Metadata event log |
| **Celery** | Too heavy for simple polling tasks, requires Redis/RabbitMQ broker | **asyncio.create_task()** with FastAPI lifespan |
| **Django Channels** | Requires Django migration from FastAPI (massive rewrite) | **FastAPI + sse-starlette** (stays in ecosystem) |
| **Socket.IO** | JavaScript library adds complexity, not idiomatic Python | **SSE** (native browser + Python async) |

---

## State Machine Architecture

### Recommended: python-statemachine 2.5.0

**Why this library:**

1. **Async native** - Full async/await support (critical for FastAPI integration)
2. **100% test coverage** - Production-ready, well-maintained
3. **Expressive API** - Pythonic, easy to reason about state transitions
4. **Validation support** - Integrates with Pydantic (already using v2.12.4)
5. **Event callbacks** - Hooks for before/after transitions (logging to Metadata sheet)
6. **Django-ready** - If you migrate from Google Sheets to Django in future

**Confidence:** HIGH (official docs verified, 2025 active development)

### State Machine Pattern for v3.0

**Dynamic states computed from occupation + progress:**

```python
from statemachine import StateMachine, State

class SpoolStateMachine(StateMachine):
    """
    v3.0: States determined by occupation + operation progress.
    NOT fixed enums - computed dynamically.
    """
    # States
    disponible = State('Disponible', initial=True)
    ocupado_arm = State('Ocupado ARM')
    ocupado_sold = State('Ocupado SOLD')
    ocupado_metrologia = State('Ocupado METROLOGÍA')
    arm_completado = State('ARM Completado')
    sold_completado = State('SOLD Completado')
    aprobado = State('Aprobado')
    rechazado = State('Rechazado')
    reparacion = State('En Reparación')

    # Transitions (v3.0 new operations)
    tomar_arm = disponible.to(ocupado_arm)
    pausar_arm = ocupado_arm.to(disponible)
    completar_arm = ocupado_arm.to(arm_completado)

    tomar_sold = arm_completado.to(ocupado_sold)
    pausar_sold = ocupado_sold.to(arm_completado)
    completar_sold = ocupado_sold.to(sold_completado)

    tomar_metrologia = sold_completado.to(ocupado_metrologia)
    aprobar = ocupado_metrologia.to(aprobado)
    rechazar = ocupado_metrologia.to(rechazado)

    enviar_reparacion = rechazado.to(reparacion)
    retornar_reparacion = reparacion.to(disponible)

    # Guards (validation)
    def before_tomar_arm(self, worker_id: int):
        if not self.spool.is_available():
            raise SpoolOcupadoError(f"Spool occupied by worker {self.spool.current_owner}")
        if not self.worker_has_role(worker_id, 'ARMADOR'):
            raise RolNoAutorizadoError()

    # Callbacks (event logging)
    def on_tomar_arm(self, worker_id: int):
        self.metadata_repo.append_event(
            MetadataEvent(
                evento_tipo="TOMAR_ARM",
                tag_spool=self.spool.tag,
                worker_id=worker_id,
                timestamp=datetime.utcnow()
            )
        )
```

**Confidence:** HIGH (library verified, pattern aligns with v2.1 event sourcing)

---

## Concurrency Control Strategy

### Recommended: Optimistic Locking with Version Tokens

**Why optimistic over pessimistic:**

1. **Google Sheets limitation** - Sheets API doesn't support row-level locks or transactions
2. **Low contention** - 10-20 concurrent workers, not 1000s (optimistic excels here)
3. **Better UX** - Workers see instant feedback, conflicts resolved retroactively
4. **Sheets native pattern** - Google Sheets itself uses optimistic concurrency (operational transformation)

**Implementation pattern:**

```python
class SpoolRepository:
    async def take_spool_optimistic(
        self,
        tag_spool: str,
        worker_id: int,
        expected_version: str  # From last read
    ) -> SpoolOccupation:
        """
        Optimistic lock pattern:
        1. Read current state + version
        2. Validate expectations
        3. Write if version matches
        4. Retry if conflict
        """
        current = await self.get_spool_with_version(tag_spool)

        # Conflict detection
        if current.version != expected_version:
            raise OptimisticLockError(
                f"Spool modified by another worker. Expected v{expected_version}, found v{current.version}"
            )

        # Physical constraint validation
        if current.ocupado_por is not None:
            raise SpoolOcupadoError(
                f"Spool already occupied by worker {current.ocupado_por}"
            )

        # Write with new version
        new_version = str(uuid.uuid4())
        await self.sheets.update_spool(
            tag_spool=tag_spool,
            ocupado_por=worker_id,
            version=new_version,
            timestamp=datetime.utcnow()
        )

        return SpoolOccupation(
            tag_spool=tag_spool,
            worker_id=worker_id,
            version=new_version
        )
```

**Version token storage:**
- Add column "version" to Operaciones sheet (UUID string)
- Update version on every TOMAR/PAUSAR/COMPLETAR
- Frontend reads version with spool data, sends back on mutations

**Retry strategy:**
```python
@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=0.5, max=2),
    retry=retry_if_exception_type(OptimisticLockError)
)
async def take_spool_with_retry(tag_spool, worker_id):
    # Read fresh version on retry
    spool = await repo.get_spool(tag_spool)
    return await repo.take_spool_optimistic(
        tag_spool, worker_id, spool.version
    )
```

**Confidence:** MEDIUM-HIGH (pattern verified, but Google Sheets eventual consistency requires testing)

### Conflict Resolution UI

When optimistic lock fails:

```typescript
// Frontend retry with exponential backoff
async function takeSpoolWithRetry(tagSpool: string, workerId: number) {
  for (let attempt = 0; attempt < 3; attempt++) {
    try {
      // Read fresh version
      const spool = await fetchSpool(tagSpool);

      // Attempt take with version
      return await api.post('/api/tomar-accion', {
        tag_spool: tagSpool,
        worker_id: workerId,
        version: spool.version  // Version from last read
      });
    } catch (error) {
      if (error.code === 'OptimisticLockError') {
        // Show user: "Another worker took this spool. Refreshing..."
        await sleep(Math.pow(2, attempt) * 500);  // 0.5s, 1s, 2s
        continue;
      }
      throw error;  // Other errors bubble up
    }
  }
  throw new Error('Failed to take spool after 3 attempts');
}
```

**Confidence:** HIGH (standard web pattern)

---

## Polling Strategy for Google Sheets

### Recommended: Adaptive Polling with SSE

**Pattern:** Backend polls Google Sheets, pushes changes via SSE to connected clients

**Why polling (not webhooks):**
1. **Google Drive webhooks batched** - Only fire every 3 minutes minimum (too slow for "real-time")
2. **Polling more predictable** - Consistent 5-second updates, no batching delays
3. **Simpler infrastructure** - No webhook endpoint setup, no ngrok for local dev

**Polling implementation:**

```python
import asyncio
from fastapi import FastAPI
from contextlib import asynccontextmanager

class SheetChangeDetector:
    def __init__(self, sheets_repo):
        self.sheets_repo = sheets_repo
        self.last_hash = None
        self.subscribers = []  # SSE clients

    async def poll_loop(self):
        """Background task polls Google Sheets every 5 seconds."""
        while True:
            try:
                # Efficient: Only fetch columns we care about (ocupado_por, version)
                current_occupations = await self.sheets_repo.get_all_occupations()
                current_hash = self._compute_hash(current_occupations)

                # Detect changes
                if current_hash != self.last_hash:
                    self.last_hash = current_hash
                    # Push to all SSE subscribers
                    await self._broadcast_changes(current_occupations)

                await asyncio.sleep(5)  # 5 second polling interval
            except Exception as e:
                logger.error(f"Polling error: {e}")
                await asyncio.sleep(10)  # Back off on error

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: Start polling task
    detector = SheetChangeDetector(sheets_repo)
    task = asyncio.create_task(detector.poll_loop())

    yield  # App runs

    # Shutdown: Cancel polling task
    task.cancel()
    try:
        await task
    except asyncio.CancelledError:
        pass

app = FastAPI(lifespan=lifespan)
```

**Polling intervals:**
- **Default:** 5 seconds (good balance of freshness vs API quota)
- **High activity:** 2 seconds (if many workers active, detected by request rate)
- **Low activity:** 10 seconds (no requests for 5 minutes, reduce API calls)
- **Error backoff:** 30 seconds (after 3 consecutive failures)

**Google Sheets API quotas:**
- **Read limit:** 300 requests/100s/user (sufficient for 5s polling with 10 workers)
- **Write limit:** 60 requests/60s/user (sufficient for batch operations)

**Optimization: Change detection hash**
```python
def _compute_hash(self, occupations: List[SpoolOccupation]) -> str:
    """
    Fast hash of current state. Only push if hash changed.
    Avoids broadcasting if no actual changes.
    """
    hash_input = "".join([
        f"{o.tag_spool}:{o.worker_id}:{o.version}"
        for o in sorted(occupations, key=lambda x: x.tag_spool)
    ])
    return hashlib.sha256(hash_input.encode()).hexdigest()
```

**Confidence:** HIGH (proven pattern, quotas verified)

---

## Event Sourcing Continuation (v2.1 → v3.0)

### Keep Existing Metadata Architecture

**DO NOT CHANGE:** v2.1 event sourcing pattern is solid, extend it for v3.0

**New event types to add:**

```python
class EventoTipo(str, Enum):
    # v2.1 existing (KEEP)
    INICIAR_ARM = "INICIAR_ARM"
    COMPLETAR_ARM = "COMPLETAR_ARM"
    CANCELAR_ARM = "CANCELAR_ARM"
    # ... (SOLD, METROLOGIA same)

    # v3.0 new
    TOMAR_ARM = "TOMAR_ARM"                    # Worker takes physical possession
    PAUSAR_ARM = "PAUSAR_ARM"                  # Worker releases without completing
    TOMAR_SOLD = "TOMAR_SOLD"
    PAUSAR_SOLD = "PAUSAR_SOLD"
    TOMAR_METROLOGIA = "TOMAR_METROLOGIA"
    COMPLETAR_METROLOGIA_APROBADO = "COMPLETAR_METROLOGIA_APROBADO"
    COMPLETAR_METROLOGIA_RECHAZADO = "COMPLETAR_METROLOGIA_RECHAZADO"
    INICIAR_REPARACION = "INICIAR_REPARACION"
    COMPLETAR_REPARACION = "COMPLETAR_REPARACION"
```

**Metadata sheet columns (unchanged):**
- A: id (UUID)
- B: timestamp (ISO 8601)
- C: evento_tipo (new event types above)
- D: tag_spool
- E: worker_id
- F: worker_nombre
- G: operacion (ARM, SOLD, METROLOGIA, REPARACION)
- H: accion (TOMAR, PAUSAR, COMPLETAR)
- I: fecha_operacion (YYYY-MM-DD)
- J: metadata_json (new: {"resultado": "APROBADO"} for metrología)

**Confidence:** HIGH (extends proven v2.1 architecture)

---

## Google Sheets Schema Changes for v3.0

### New Columns for Operaciones Sheet

Add these columns to existing 65 columns:

| Column | Name | Type | Purpose | Example |
|--------|------|------|---------|---------|
| AR (66) | ocupado_por | int? | Worker ID currently holding spool | 93 |
| AS (67) | version | str | Optimistic lock version token (UUID) | "550e8400-..." |
| AT (68) | timestamp_ocupacion | ISO 8601 | When TOMAR occurred | "2025-01-26T14:30:00Z" |
| AU (69) | resultado_metrologia | str? | APROBADO / RECHAZADO | "APROBADO" |
| AV (70) | reparacion_ciclo | int | Number of repair cycles | 0 |

**CRITICAL: Dynamic header mapping**
- NEVER hardcode indices (66, 67, etc.) - use v2.1 pattern `headers["ocupado_por"]`
- Column positions WILL change as sheet evolves

**Confidence:** HIGH (follows v2.1 column mapping pattern)

---

## Stack Patterns by Scenario

### Scenario 1: Real-Time Updates (High Priority)

**If:** Multiple workers need to see who has what spool in real-time

**Stack:**
- FastAPI SSE endpoint (`/api/sse/spools`)
- Backend polling Google Sheets every 5 seconds
- sse-starlette library for SSE implementation
- Next.js native EventSource API

**Because:** SSE is simplest for unidirectional updates, no new infrastructure needed

---

### Scenario 2: Occupation Conflicts (Critical)

**If:** Two workers try to take same spool simultaneously

**Stack:**
- Optimistic locking with version tokens (UUID in column AS)
- python-statemachine guards prevent invalid transitions
- 3x retry with exponential backoff
- Frontend shows "Another worker took this spool" message

**Because:** Google Sheets can't do pessimistic locks, optimistic is proven pattern for low contention

---

### Scenario 3: State Machine Complexity (High)

**If:** Need to compute dynamic states from occupation + progress data

**Stack:**
- python-statemachine 2.5.0 for state definitions and transitions
- Pydantic models for state validation
- State computed on-demand (not stored in Sheets)

**Because:** State machine library handles complexity better than manual if/else chains

---

### Scenario 4: Long-Running Processes (Background Polling)

**If:** Need continuous polling while FastAPI app runs

**Stack:**
- `asyncio.create_task()` in FastAPI lifespan context
- NOT BackgroundTasks (those are request-scoped)
- Graceful shutdown with task.cancel()

**Because:** Lifespan-managed tasks run app lifetime, BackgroundTasks die after request

---

## Version Compatibility

| Package | Compatible With | Notes |
|---------|-----------------|-------|
| python-statemachine 2.5.0 | Python 3.10-3.14 | Async requires 3.10+ |
| sse-starlette 2.2.0 | FastAPI 0.100+ / Starlette 0.37+ | Already compatible with v2.1 FastAPI 0.121.0 |
| pytest-asyncio 0.25.0 | pytest 8.0+ | Already using pytest 8.4.2 in v2.1 |
| FastAPI 0.121.0 | Pydantic 2.x | Already using Pydantic 2.12.4 ✅ |
| gspread 6.2.1 | google-auth 2.x | Already using google-auth 2.41.1 ✅ |

**NO breaking changes** - All new libraries compatible with existing v2.1 stack

---

## Migration Strategy (v2.1 → v3.0)

### Phase 1: State Machine (No Breaking Changes)
1. Install python-statemachine
2. Define SpoolStateMachine with v3.0 states/transitions
3. Integrate with existing ValidationService
4. Add unit tests for state machine (target: 40+ tests)

### Phase 2: Real-Time (Additive Only)
1. Install sse-starlette
2. Add `/api/sse/spools` endpoint (NEW, doesn't touch existing endpoints)
3. Implement polling loop with asyncio.create_task()
4. Add EventSource to frontend (additive, existing pages work without it)

### Phase 3: Optimistic Locking (Schema Change)
1. Add columns AR-AV to Operaciones sheet (NON-BREAKING if nullable)
2. Update SheetsRepository with new column mappings
3. Add version token logic to TOMAR/PAUSAR/COMPLETAR operations
4. Test conflict scenarios with 2 concurrent workers

### Phase 4: New Operations (API Expansion)
1. Add POST `/api/tomar-accion` (NEW)
2. Add POST `/api/pausar-accion` (NEW)
3. Extend Metadata event types
4. Frontend adds TOMAR/PAUSAR buttons

**Confidence:** HIGH (phased approach minimizes risk)

---

## Testing Strategy

### Unit Tests (Target: 60+ new tests)

```bash
# State machine tests (20 tests)
tests/unit/test_spool_state_machine.py
  - test_tomar_arm_from_disponible_success
  - test_tomar_arm_when_occupied_fails
  - test_pausar_arm_returns_to_disponible
  - test_completar_requires_ocupado_state
  - test_metrologia_aprobar_rechazar
  - test_reparacion_cycle
  - test_guards_prevent_invalid_transitions

# Optimistic locking tests (15 tests)
tests/unit/test_optimistic_locking.py
  - test_take_spool_with_correct_version_succeeds
  - test_take_spool_with_stale_version_fails
  - test_concurrent_take_only_one_succeeds
  - test_retry_logic_succeeds_on_fresh_version
  - test_version_updates_on_every_mutation

# SSE tests (10 tests)
tests/unit/test_sse_endpoint.py
  - test_sse_connection_established
  - test_sse_receives_updates_on_change
  - test_sse_reconnects_after_disconnect
  - test_polling_loop_starts_on_startup
  - test_polling_loop_stops_on_shutdown

# Polling tests (10 tests)
tests/unit/test_sheet_polling.py
  - test_poll_detects_changes_via_hash
  - test_poll_broadcasts_to_subscribers
  - test_poll_backoff_on_error
  - test_adaptive_interval_on_activity
```

### Integration Tests (Target: 20+ new tests)

```bash
tests/integration/test_occupation_workflow.py
  - test_tomar_pausar_completar_full_flow
  - test_concurrent_workers_occupation_conflict
  - test_metrologia_rechazar_reparacion_cycle
  - test_sse_receives_occupation_updates

tests/integration/test_state_machine_integration.py
  - test_state_transitions_log_to_metadata
  - test_invalid_transition_raises_business_error
```

### E2E Tests (Frontend + Backend)

```bash
tests/e2e/test_real_time_occupation.py
  - test_worker_a_takes_spool_worker_b_sees_update
  - test_worker_b_cannot_take_occupied_spool
  - test_sse_updates_ui_within_5_seconds
```

**Confidence:** HIGH (test patterns proven in v2.1)

---

## Performance Considerations

| Concern | At 10 Workers | At 50 Workers | At 100 Workers |
|---------|---------------|---------------|----------------|
| **SSE connections** | 10 open connections | 50 connections (Railway handles) | 100 connections - may need horizontal scaling |
| **Polling rate** | 5 sec (60 req/min to Sheets) | 5 sec (same - shared poll) | Consider 7-10 sec interval to stay under quota |
| **Optimistic conflicts** | Rare (<1% operations) | Low (5-10% if high contention) | Medium (10-20% - add UI feedback) |
| **Google Sheets quota** | Safe (well under 300 reads/100s) | Safe (under quota) | Monitor quota usage, consider caching |
| **Memory (SSE)** | ~10 MB (1 MB per connection) | ~50 MB | ~100 MB - acceptable for Railway |
| **Response time** | < 500ms (TOMAR/PAUSAR) | < 800ms (batch operations) | < 1s (with retry) |

**Scaling recommendations:**
- **< 50 workers:** Single Railway instance, 5 sec polling
- **50-100 workers:** Horizontal scaling (2 instances), 7 sec polling, shared Redis cache (optional)
- **> 100 workers:** Reconsider Google Sheets as database (migrate to Postgres + read replicas)

**Confidence:** MEDIUM (performance estimates based on similar systems, requires load testing)

---

## Sources

### HIGH Confidence (Official Documentation)

- **FastAPI WebSockets:** https://fastapi.tiangolo.com/advanced/websockets/ (Official docs, verified 2026-01-26)
- **python-statemachine:** https://python-statemachine.readthedocs.io/ (Official docs, v2.5.0, verified 2026-01-26)
- **Google Sheets API Batch Update:** https://developers.google.com/sheets/api/guides/batchupdate (Official docs, verified 2026-01-26)

### MEDIUM Confidence (Verified with Multiple Sources)

- **SSE vs WebSockets:** Medium articles + Better Stack Community (2025 patterns, consistent across sources)
- **FastAPI SSE Implementation:** TestDriven.io tutorials (July 2025) + GitHub examples
- **Optimistic Locking Patterns:** ByteByteGo + System Design guides (consistent across sources)

### MEDIUM-LOW Confidence (WebSearch Only - Requires Validation)

- **Google Sheets polling best practices:** Adaptive polling patterns (5-10s intervals) - no single authoritative source, aggregate from multiple articles
- **Google Drive webhook limitations:** 3-minute batching mentioned in GitHub issues, but not officially documented
- **Performance estimates:** Based on similar system reports, requires load testing for v3.0 specific case

---

**Researcher Notes:**

1. **SSE over WebSockets** is clear winner for v3.0 - unidirectional updates, simpler infrastructure, better mobile reliability
2. **python-statemachine** is actively maintained (2025 updates), async-native, well-tested - best choice for state management
3. **Optimistic locking** is pragmatic choice given Google Sheets constraints - low contention (10-20 workers) makes this viable
4. **NO external dependencies** (Redis, Kafka) recommended - keeps architecture simple, Google Sheets remains source of truth
5. **Polling at 5 seconds** is sweet spot - fresh enough for "real-time feel", well under API quotas
6. **Version token approach** is standard web pattern, proven in many production systems

**Gaps requiring phase-specific research:**

- Load testing with 50+ concurrent SSE connections (Phase 2)
- Google Sheets eventual consistency impact on optimistic locking (Phase 3)
- Adaptive polling interval tuning based on real usage patterns (Phase 2)

---

*Stack research for: ZEUES v3.0 Real-Time Location Tracking*
*Researched: 2026-01-26*
*Confidence: HIGH (Core technologies) / MEDIUM (Performance estimates)*
