# Project Research Summary

**Project:** ZEUES v3.0 Real-Time Location Tracking
**Domain:** Manufacturing traceability with real-time occupation and state management
**Researched:** 2026-01-26
**Confidence:** HIGH

## Executive Summary

ZEUES v3.0 adds real-time "who has what spool right now" tracking to the existing v2.1 production system (244 passing tests, FastAPI + Google Sheets + Next.js). Research reveals that **Server-Sent Events (SSE) + Redis caching + optimistic locking** is the pragmatic approach for manufacturing floor tracking with Google Sheets constraints. The architecture uses **hierarchical state machines** (not flat 27-state enums) and **write-through caching** to overcome Google Sheets' 60 writes/min rate limit and 200-500ms latency.

The recommended approach: **phased migration** using expand-migrate-contract pattern to avoid breaking v2.1 production. Start with basic TOMAR/PAUSAR operations backed by Redis locks (Phase 1), add SSE real-time updates (Phase 2), then layer in progress tracking and repair loops (Phase 3-4). The critical risk is **race conditions** on simultaneous TOMAR attempts — mitigated with Redis atomic operations (SETNX) plus optimistic locking via version tokens in Google Sheets.

Key insight: This is NOT a "real-time" system like WebSocket chat. Manufacturing floor needs **"real enough"** updates (5-second polling acceptable), unidirectional server-to-client push (SSE over WebSockets), and **physical constraint validation** (one spool, one worker, one location) which Google Sheets doesn't natively support. Redis becomes the conflict arbiter, Sheets remains source of truth, Metadata provides forensic audit trail.

## Key Findings

### Recommended Stack

v3.0 extends v2.1's proven stack (FastAPI 0.121.0, Python 3.11, gspread, Next.js 14, Railway/Vercel) with two new libraries: **python-statemachine 2.5.0** for state management and **sse-starlette 2.2.0** for real-time updates. Redis added as write-through cache to reduce Google Sheets API calls by 80-90% and enable atomic conflict detection.

**Core technologies (new for v3.0):**
- **python-statemachine 2.5.0**: State machine engine — async native, 100% test coverage, expressive API for occupation lifecycle (DISPONIBLE → OCUPADO → EN_PROGRESO → COMPLETADO)
- **sse-starlette 2.2.0**: Server-Sent Events for FastAPI — unidirectional server-to-client push, HTTP-based (no WebSocket complexity), auto-reconnect built-in
- **Redis 7.x**: Write-through cache + pub/sub — atomic SETNX for locks, 60s TTL for spool states, coordinates SSE broadcasts across instances

**Why NOT WebSockets:** Workers mostly READ state (available spools) and occasionally POST actions (TOMAR/PAUSAR). SSE is simpler (HTTP-only), auto-reconnects on tablet network drops, and avoids sticky session complexity for horizontal scaling.

**Why NOT external databases:** Google Sheets is already source of truth (v2.1 design decision). Adding Postgres would create sync complexity. Redis is cache-only, not competing source of truth.

**Version compatibility:** All new libraries compatible with existing v2.1 stack — no breaking changes. Redis deployment adds infrastructure dependency but Railway supports it natively.

### Expected Features

Research identified 18 features across 3 priority tiers, with clear table stakes vs differentiators vs anti-features.

**Must have (launch blockers — 8 features):**
- **TOMAR operation** — Worker explicitly takes available spool (occupation begins)
- **Physical occupation constraint** — Prevent double-assignment via optimistic locking (critical for data integrity)
- **Real-time occupation status** — Visual indicator: available (green) vs occupied (red), < 2 sec latency expected
- **PAUSAR operation** — Worker releases spool without completing (essential for shift changes, breaks, blockers)
- **Who has what dashboard** — List view: "Juan → Spool-123, Spool-456 | María → Spool-789"
- **Combined state display** — Show both occupation AND progress: "Ocupado por: Juan (93) | Estado: ARM parcial, SOLD pendiente"
- **Available spool filtering** — Only show available spools in TOMAR screen (prevent wasted time)
- **Occupation audit trail** — Metadata events: TOMAR_ARM, PAUSAR_ARM, etc. (extends v2.1 Event Sourcing)

**Should have (competitive advantage — 5 features):**
- **Handoff workflow optimization** — When Juan PAUSARs after ARM, highlight spool for Soldador role (30-40% search time reduction)
- **Occupation history** — "This spool held by 3 workers for avg 2.5 hours each" (leverage existing Metadata)
- **Idle spool alerts** — Notify supervisor if spool TOMAR'd but no progress > 4 hours (proactive bottleneck detection)
- **Worker load balancing** — Dashboard shows "Juan has 8 spools, María has 2" for supervisor fairness
- **Occupation time warnings** — Visual indicator if spool held > 8 hours (prevents "forgotten" spools)

**Defer (v3.1+ complex features — 5 features):**
- **Batch TOMAR** — Take 10-50 spools at once (reuse v2.1 batch infra, adds 2x complexity for occupation validation)
- **Metrología-specific flow** — COMPLETAR only (no TOMAR/PAUSAR), with APROBADO/RECHAZADO result (separate state machine)
- **Reparación workflow** — Quality loop: SOLD→METROLOGÍA→RECHAZADO→REPARACIÓN→METROLOGÍA→APROBADO (multi-cycle complexity)
- **Collaborative locking advanced** — Handle edge cases: worker A PAUSARs, worker B TOMArs, worker A tries to resume (ownership transfer rules)
- **Analytics dashboard** — Avg occupation time, bottleneck detection, productivity trends (requires visualization layer)

**Anti-features (explicitly NOT building):**
- **Automatic PAUSAR on inactivity** — Creates false positives (worker on break vs working), manual tracking errors increase 43%
- **GPS/RFID physical location** — Over-engineering, $50K+ infrastructure cost, Google Sheets can't store real-time sensor data
- **Real-time sync < 1 second** — Google Sheets API quota (100 req/100s) can't support sub-second polling. 5-10 sec "real enough"
- **Spool reservation system** — Adds reservation vs occupation state complexity, creates "phantom unavailability"
- **Undo/Edit operations retroactively** — Destroys audit trail integrity, violates immutable Event Sourcing principle

### Architecture Approach

v3.0 uses **write-through cache (Redis + Google Sheets)** with **SSE for real-time push** and **hierarchical state machines** (NOT flat 27-state enums). Backend polls Google Sheets every 5 seconds, detects changes via hash comparison, broadcasts to SSE subscribers. Workers POST actions via REST (TOMAR/PAUSAR), backend atomically checks Redis lock, writes to Sheets, logs to Metadata, publishes SSE event. Frontend receives updates in < 100ms via EventSource API.

**Major components:**
1. **CacheRepository (NEW)** — Redis read-through cache with 60s TTL, write-through on TOMAR/PAUSAR, reduces Sheets API calls 80-90%
2. **OccupationService (NEW)** — Orchestrates TOMAR/PAUSAR/COMPLETAR with conflict detection, calls StateService for validation, ConflictService for locking
3. **StateService (NEW)** — python-statemachine integration for occupation lifecycle: DISPONIBLE → OCUPADO → EN_PROGRESO → PAUSADO → COMPLETADO
4. **ConflictService (NEW)** — Optimistic locking via Redis atomic SETNX plus version tokens in Sheets, read-after-write verification
5. **SSE Router (NEW)** — `/api/sse/spools-updates` endpoint streams changes via sse-starlette, uses Redis pub/sub to coordinate broadcasts
6. **SheetsRepository (EXTENDED)** — Add columns: Ocupado_Por, Fecha_Ocupacion, version (UUID), dynamic header mapping (NEVER hardcoded indices)
7. **MetadataRepository (EXTENDED)** — New event types: TOMAR_SPOOL, PAUSAR_SPOOL, append-only enforcement (NO updates)

**Data flow pattern:**
```
[Worker Tablet] → POST /api/tomar-spool
  → OccupationService validates (StateService guards)
  → ConflictService atomically checks Redis lock (SETNX)
  → Write to Sheets (background task) + Metadata (audit log)
  → Publish Redis event → SSE broadcast
  → All connected tablets receive update in < 100ms
```

**Key patterns:**
- **Write-through cache**: All writes hit Redis first (< 10ms), then Sheets asynchronously (200-500ms). Reads check Redis, fallback to Sheets on miss.
- **SSE over WebSockets**: Unidirectional server → client sufficient. SSE simpler (HTTP-based), auto-reconnects, no sticky sessions needed.
- **Optimistic locking**: Redis atomic SETNX for lock acquisition, version tokens in Sheets for conflict detection, 3x retry with exponential backoff.
- **Hierarchical state machines**: Primary state (Operation: ARM/SOLD), sub-state (Occupation: DISPONIBLE/OCUPADO/PAUSADO), context (Progress: 0-100%). Total 9 states, not 27.

### Critical Pitfalls

Research identified 6 critical pitfalls with prevention strategies mapped to phases.

1. **Race Conditions on TOMAR (Simultaneous Occupation)** — Two workers attempt TOMAR at same time, both read DISPONIBLE, both write occupation. **Prevention:** Redis atomic SETNX + version tokens in Sheets + read-after-write verification. **Address in Phase 1** (foundation, must be right before frontend integration).

2. **State Explosion from Dynamic States** — Combining 3 operations × 3 occupation states × 3 progress states = 27+ unmaintainable states. **Prevention:** Hierarchical state machines (primary + sub-state + context = 9 states). **Address in Phase 1** (design state diagram before implementation, peer review).

3. **Breaking v2.1 Production During Refactor** — Aggressive refactoring breaks working 244-test system. **Prevention:** Expand-migrate-contract pattern (add new columns, dual writes, gradual cutover over 2+ weeks). **Address in Phase 0** (migration strategy before any code changes).

4. **Polling Degradation with Scale** — Frontend polling every 2 seconds exhausts Google Sheets quota (60 req/min) with 30 workers. **Prevention:** Backend cache (5s TTL), exponential backoff, partial data loading (filter queries). **Address in Phase 2** (implement caching BEFORE frontend polling).

5. **Ignoring Event Sourcing Audit Trail** — Team assumes Metadata "optional" in v3.0 Direct Read architecture, skips logging TOMAR/PAUSAR. **Prevention:** Make append_metadata mandatory in all action workflows, test audit completeness. **Address in Phase 1** (extend MetadataService for v3.0 actions).

6. **Infinite Reparación Loops** — Metrología → Reparación → Metrología cycles infinitely without bounds. **Prevention:** Maximum 3 rework cycles, terminal states (RECHAZADO), supervisor override after limit. **Address in Phase 3** (design bounded repair workflow upfront).

**Additional technical traps:**
- **N+1 Sheets queries** — Load entire sheet once, filter in-memory (breaks > 10 concurrent users without caching)
- **Hardcoded column indices** — Use dynamic header mapping `headers["Armador"]` (sheet structure changes frequently in production)
- **Synchronous Sheets API calls** — Wrap gspread in `asyncio.to_thread()` (blocks FastAPI event loop)
- **No optimistic UI on TOMAR** — Show OCUPADO immediately, revert on error (2-5s delay unacceptable)

## Implications for Roadmap

Based on research dependencies, suggested phased migration with clear separation of concerns:

### Phase 0: Migration Strategy & Planning
**Rationale:** MUST document backward compatibility plan BEFORE any refactoring (Pitfall 3: Breaking v2.1 Production). Expand-migrate-contract requires upfront schema design and dual-write testing.

**Delivers:**
- Migration plan documented (which columns to add, dual-write strategy, rollback steps)
- Schema changes designed: Ocupado_Por, Fecha_Ocupacion, version (UUID) columns in Operaciones
- New Metadata event types defined: TOMAR_SPOOL, PAUSAR_SPOOL, ACTUALIZAR_PROGRESO
- Backward compatibility tests written (v2.1 endpoints must still work)

**Addresses:** Pitfall 3 (Breaking v2.1 Production) — prevent catastrophic production failure

**Effort:** 2 days

**Research flag:** Standard migration patterns, no deeper research needed.

---

### Phase 1: Foundation (Redis + Basic State Machine)
**Rationale:** Build conflict-free TOMAR/PAUSAR operations BEFORE any frontend integration (Pitfall 1: Race Conditions). Hierarchical state machine design prevents state explosion (Pitfall 2). Extend Metadata logging to maintain audit trail (Pitfall 5).

**Delivers:**
- Redis deployed on Railway, CacheRepository with read-through pattern (60s TTL)
- Basic SpoolStateMachine: DISPONIBLE → OCUPADO → COMPLETADO (no progress tracking yet)
- ConflictService with optimistic locking: Redis SETNX + version tokens
- New endpoints: POST /api/tomar-spool, POST /api/liberar-spool
- Extend MetadataRepository: TOMAR_SPOOL, LIBERAR_SPOOL events
- SheetsRepository supports new columns via dynamic header mapping

**Addresses:**
- **FEATURES.md:** TOMAR operation, Physical occupation constraint, Occupation audit trail
- **PITFALLS.md:** Race conditions (atomic locking), State explosion (hierarchical design), Missing Metadata (mandatory logging)

**Success criteria:**
- Concurrent TOMAR test: 10 parallel requests, only 1 succeeds, 9 get conflict errors
- Redis cache reduces Sheets API calls by 70%+
- State diagram shows < 15 states (hierarchical, peer-reviewed)
- TOMAR/LIBERAR complete in < 500ms

**Effort:** 3-4 days (1 day Redis setup, 2 days services, 1 day testing)

**Research flag:** SKIP research-phase — standard Redis caching + state machine patterns well-documented.

---

### Phase 2: Real-Time Updates (SSE)
**Rationale:** Add live updates so tablets see spool availability changes (core v3.0 value prop). Backend caching prevents polling degradation (Pitfall 4). SSE chosen over WebSockets for simplicity (unidirectional updates sufficient).

**Delivers:**
- SSE endpoint: GET /api/sse/spools-updates (sse-starlette integration)
- Redis pub/sub for event broadcasting
- Backend polling loop: Check Sheets every 5 seconds, detect changes via hash, broadcast to SSE subscribers
- Frontend EventSource integration (React hooks)
- SSE connection manager (track active clients, handle reconnects)

**Addresses:**
- **FEATURES.md:** Real-time occupation status, Who has what dashboard, Available spool filtering
- **PITFALLS.md:** Polling degradation (backend cache + exponential backoff)
- **STACK.md:** SSE over WebSockets (simpler for unidirectional push)

**Success criteria:**
- Workers see spool occupation changes in < 200ms
- SSE connection stays alive for 8-hour shift
- Auto-reconnect on network interruption
- Load test: 30 concurrent users, response time < 1s, Sheets API < 80 req/min

**Effort:** 2-3 days (1 day backend SSE, 1 day frontend integration, 1 day testing)

**Research flag:** SKIP research-phase — FastAPI SSE patterns verified in official docs.

---

### Phase 3: Advanced State Machine (Progress + Pause)
**Rationale:** Add PAUSAR/REANUDAR actions and progress tracking (0-100%). Enables shift handoffs and supervisor visibility. Build on Phase 1 hierarchical state machine.

**Delivers:**
- Extended SpoolStateMachine: Add PAUSADO state, PAUSAR/REANUDAR transitions
- Progress tracking via Redis (don't write every 1% to Sheets)
- Milestone writes to Sheets (every 25% progress, not noisy)
- Frontend progress bars with real-time SSE updates
- Occupation history view (leverage Metadata for "3 workers, avg 2.5 hrs each")

**Addresses:**
- **FEATURES.md:** PAUSAR operation, Combined state display, Occupation history, Idle spool alerts
- **ARCHITECTURE.md:** Hierarchical state machines with context (progress NOT a primary state)

**Success criteria:**
- Workers can pause and resume work
- Progress visible to supervisors in real-time
- Sheets stores milestones only (< 5 writes per spool completion)

**Effort:** 3-4 days (2 days state machine extension, 1 day frontend, 1 day testing)

**Research flag:** SKIP research-phase — state machine extension pattern straightforward.

---

### Phase 4: Conflict Resolution + Metrología
**Rationale:** Handle edge cases (simultaneous TOMAR conflicts), add Metrología special case (instant COMPLETAR with APROBADO/RECHAZADO, no TOMAR/PAUSAR). Prepare foundation for Reparación loops.

**Delivers:**
- Enhanced ConflictService: Retry with exponential backoff (3x attempts), frontend conflict feedback
- Metrología-specific workflow: COMPLETAR only (no occupation), with result (APROBADO/RECHAZADO)
- Resultado_Metrologia column in Operaciones sheet
- Supervisor override endpoint (force-release stuck spools)

**Addresses:**
- **FEATURES.md:** Metrología-specific flow (defer full Reparación to Phase 5)
- **PITFALLS.md:** Optimistic lock conflicts (retry logic), UX feedback ("Tomado por Juan hace 30 seg")

**Success criteria:**
- Conflict error rate < 1% (most TOMAR attempts succeed)
- Metrología workflow works without TOMAR/PAUSAR (different code path)
- Stuck spools can be recovered by supervisor

**Effort:** 3-4 days (2 days conflict logic, 1 day Metrología, 1 day testing)

**Research flag:** NEEDS research-phase — Metrología workflow unclear (instant completion, how to handle in state machine?).

---

### Phase 5: Reparación Loop (Optional, can be v3.1)
**Rationale:** Enable quality loop for rejected spools. Complex multi-cycle state machine requires Phase 3 stable first (bounded cycles to avoid infinite loops, Pitfall 6).

**Delivers:**
- Reparación workflow: SOLD → METROLOGÍA → RECHAZADO → REPARACIÓN → METROLOGÍA
- Maximum 3 rework cycles (reparacion_count column)
- Terminal states: RECHAZADO (after 3 cycles), COMPLETADO_FINAL
- Supervisor override for 4th repair attempt

**Addresses:**
- **FEATURES.md:** Reparación triggered workflow (v3.1 nice-to-have)
- **PITFALLS.md:** Infinite Reparación loops (bounded cycles, terminal states)

**Success criteria:**
- 4th repair attempt triggers supervisor flow
- Spool BLOQUEADO after max cycles (not DISPONIBLE)
- Metadata shows full repair history (forensic-grade audit)

**Effort:** 4-5 days (2 days repair loop state machine, 2 days supervisor override, 1 day testing)

**Research flag:** NEEDS research-phase — Manufacturing rework patterns (how many cycles typical? supervisor escalation rules?).

---

### Phase Ordering Rationale

**Critical path dependencies:**
1. **Phase 0 BEFORE Phase 1** — Migration strategy prevents breaking v2.1 production (244 tests must keep passing)
2. **Phase 1 BEFORE Phase 2** — Redis caching + conflict detection must work before SSE real-time updates (avoid broadcasting race conditions)
3. **Phase 2 BEFORE Phase 3** — Real-time push infrastructure needed for progress updates
4. **Phase 3 BEFORE Phase 4** — Basic state machine must be stable before adding Metrología special case
5. **Phase 4 BEFORE Phase 5** — Metrología APROBADO/RECHAZADO needed to trigger Reparación

**Parallel opportunities:**
- Frontend SSE integration (Phase 2) can start while backend state machine (Phase 3) progresses IF API contract defined upfront
- Metadata schema changes (Phase 1) independent of CacheRepository implementation

**Deferred to v3.1:**
- Batch TOMAR (adds 2x complexity, validate single-spool first)
- Analytics dashboard (requires visualization layer, text-based UI sufficient for MVP)
- Advanced collaborative locking (edge cases emerge from real usage, don't over-engineer Day 1)

### Research Flags

**Phases needing deeper research:**
- **Phase 4 (Metrología workflow):** Special case workflow unclear — instant COMPLETAR without occupation, how to handle in state machine? Separate state machine or special guards?
- **Phase 5 (Reparación loop):** Manufacturing rework best practices — typical max cycles? Supervisor escalation rules? Quality department approval workflows?

**Phases with standard patterns (skip research-phase):**
- **Phase 1 (Redis + State Machine):** Redis caching patterns well-documented (FastAPI + Redis official guides), python-statemachine has excellent docs
- **Phase 2 (SSE):** FastAPI SSE verified in official docs, sse-starlette production-ready, EventSource API browser standard
- **Phase 3 (Progress tracking):** State machine extension straightforward, progress tracking common pattern (don't spam Sheets, use milestones)

## Confidence Assessment

| Area | Confidence | Notes |
|------|------------|-------|
| Stack | HIGH | python-statemachine + sse-starlette verified in official docs (2025-2026). Redis caching proven pattern. All libraries compatible with v2.1 stack (no breaking changes). |
| Features | HIGH | Real-time tracking features well-researched (IoT Asset Tracking 2026 reports, manufacturing traceability systems). Table stakes vs differentiators clear from competitive analysis. |
| Architecture | MEDIUM-HIGH | Write-through cache + SSE patterns verified in multiple sources. Hierarchical state machines proven in game programming / embedded systems. Google Sheets conflict resolution inferred (not officially documented). |
| Pitfalls | HIGH | Race conditions, refactoring, backward compatibility verified in 2025-2026 engineering blogs (Kraken, Vfunction, PlanetScale). State explosion / polling degradation consistent across sources. |

**Overall confidence:** HIGH

### Gaps to Address

Research areas requiring validation during implementation:

1. **Google Sheets eventual consistency impact on optimistic locking:** Sheets API doesn't document consistency guarantees. Race window between read → check → write unclear. **Solution:** Test with 10+ concurrent TOMAR attempts in Phase 1, measure conflict rate, adjust lock timeout if needed.

2. **SSE connection limits on Railway:** Railway documentation doesn't specify max concurrent SSE connections per instance. **Solution:** Load test with 50 connected clients in Phase 2, monitor memory usage, prepare for horizontal scaling (Redis pub/sub coordinates broadcasts across instances).

3. **Metrología instant completion workflow:** How to handle "no occupation" special case in state machine? Separate state machine or conditional guards? **Solution:** Research-phase in Phase 4 to investigate manufacturing quality inspection patterns (likely instant COMPLETAR with result, skip occupation states).

4. **Repair cycle business rules:** What's typical maximum rework count? When does supervisor override? Quality department approval needed? **Solution:** Research-phase in Phase 5 + user interviews with production supervisors.

5. **Adaptive polling interval tuning:** What's optimal polling frequency based on activity? 5 sec sufficient or too slow? **Solution:** Monitor in production (Phase 2), collect metrics (user complaints about stale data), adjust dynamically (high activity → 2 sec, low activity → 10 sec).

## Sources

### Primary (HIGH confidence)

**Stack Research:**
- FastAPI WebSockets Official Docs: https://fastapi.tiangolo.com/advanced/websockets/ (WebSocket patterns, SSE comparison)
- python-statemachine Official Docs: https://python-statemachine.readthedocs.io/ (v2.5.0, async support, guards/callbacks)
- Google Sheets API Limits: https://developers.google.com/workspace/sheets/api/limits (60 writes/min/user, batch operations)

**Features Research:**
- IoT Asset Tracking Market Report (GlobeNewswire, Jan 2026): Growth to $18.91B by 2032
- Tulip WIP Tracking Best Practices (2026): Real-time visibility, barcode scanning, bottleneck detection
- MachineMetrics/Scytec Real-Time Dashboards (2026): OEE indicators, 3-5 sec refresh standard

**Pitfalls Research:**
- Kraken Engineering (Jan 2025): "Avoiding race conditions using MySQL locks" https://engineering.kraken.tech/news/2025/01/20/mysql-race-conditions.html
- PlanetScale (2025): "Backward compatible database changes" https://planetscale.com/blog/backward-compatible-databases-changes
- Vfunction (2025): "7 Pitfalls to Avoid in Refactoring Projects" https://vfunction.com/blog/7-pitfalls-to-avoid-in-application-refactoring-projects/

### Secondary (MEDIUM confidence)

**Architecture Research:**
- SSE vs WebSockets Comparison: https://fictionally-irrelevant.vercel.app/posts/why-you-should-use-server-side-events-over-web-sockets-and-long-polling (Real-world patterns, 2025)
- FastAPI Redis Caching: https://redis.io/learn/develop/python/fastapi (Redis integration, TTL strategies)
- Optimistic vs Pessimistic Locking: https://medium.com/@captain-uchiha/minimizing-lock-contention-optimistic-vs-pessimistic-locking-explained-clearly-0d3f6da9464a (Jan 2026)

**Features Research:**
- Navigine Industrial Asset Tracking: RTLS technologies (UWB, BLE), cost implications
- Hakunamatatatech Inventory Challenges (2026): 43% retailers lack real-time visibility
- Humly Workspace Management (2026): Color-coded occupancy (green=available, red=booked)

### Tertiary (LOW confidence, needs validation)

- State machine patterns for manufacturing: General concepts from multiple sources, not FastAPI-specific
- Google Sheets conflict resolution: Inferred from API behavior, not officially documented
- Manufacturing pause/resume workflows: Search results focused on general workflow automation, not shop floor specifics
- Shop floor item reservation conflicts: Results from building occupancy codes, not manufacturing-specific

**Context: ZEUES v2.1 Project Documentation:**
- proyecto-v2.md, proyecto-v2-backend.md (v2.1 Direct Read architecture, 244 tests, roles, batch operations)
- CLAUDE.md (Constraints: Google Sheets, mobile-first, < 30 sec operations)

---

**Research completed:** 2026-01-26
**Ready for roadmap:** YES

**Next steps for orchestrator:**
1. Load this SUMMARY.md as context
2. Proceed to requirements definition phase
3. Use phase suggestions as starting point for roadmap structure
4. Flag Phase 4 (Metrología) and Phase 5 (Reparación) for potential research-phase during planning
