# ZEUES v3.0 - Real-Time Location Tracking

## What This Is

ZEUES v3.0 transforms the manufacturing traceability system from progress tracking to real-time location/occupation tracking. Instead of asking "how complete is the work?", v3.0 answers "WHO has WHICH spool right now?" enabling collaborative sequential workflows where multiple workers (Armadores, Soldadores) can work on the same spool in flexible handoffs, with live visibility into which spools are DISPONIBLE vs OCUPADO on the manufacturing floor.

## Core Value

**Track work at the union level with the correct business metric (pulgadas-diámetro)** - Enable workers to complete work by individual welds (unions), measure performance in pulgadas-diámetro (the actual billing metric), and support partial completion workflows where work can pause mid-union-set and be continued by any qualified worker.

## Requirements

### Validated

✓ **v2.1 Features (Production, 244 tests passing):**
- Worker management with multi-role system (Armador, Soldador, Metrología, Ayudante)
- Spool tracking with TAG_SPOOL barcodes
- Batch operations (up to 50 spools simultaneously)
- Metadata Event Sourcing audit trail (append-only immutable log)
- Google Sheets as source of truth (Operaciones, Trabajadores, Roles, Metadata sheets)
- FastAPI backend + Next.js mobile-first frontend
- Deployed on Railway + Vercel in production

✓ **v3.0 Real-Time Location Tracking (Shipped 2026-01-28, 31 plans, 161 min):**

**Location Tracking (6/6):**
- ✓ **LOC-01**: Worker can TOMAR available spool — v3.0 (Redis atomic locks, 1-hour TTL)
- ✓ **LOC-02**: Worker can PAUSAR spool without completing — v3.0 (releases lock, preserves progress)
- ✓ **LOC-03**: Worker can COMPLETAR spool work — v3.0 (updates Sheets + releases lock)
- ✓ **LOC-04**: System prevents race conditions — v3.0 (optimistic locking, validated with 10 concurrent tests)
- ✓ **LOC-05**: Worker can see real-time DISPONIBLE spools — v3.0 (SSE with <10s latency)
- ✓ **LOC-06**: Worker can see "who has what" dashboard — v3.0 (SSE streaming, EventSource with backoff)

**State Management (4/4):**
- ✓ **STATE-01**: System displays combined state — v3.0 (EstadoDetalleBuilder with occupation + ARM + SOLD)
- ✓ **STATE-02**: Metadata logs all TOMAR/PAUSAR/COMPLETAR events — v3.0 (append-only audit trail)
- ✓ **STATE-03**: Estado_Detalle column shows dynamic state — v3.0 (column 67, updated on every transition)
- ✓ **STATE-04**: Hierarchical state machine — v3.0 (6 states total: 3 ARM + 3 SOLD, not 27)

**Collaborative Work (4/4):**
- ✓ **COLLAB-01**: Any worker can continue partially-completed work — v3.0 (no strict ownership, worker handoffs tested)
- ✓ **COLLAB-02**: System enforces operation dependencies — v3.0 (SOLD requires ARM initiated, guard validators)
- ✓ **COLLAB-03**: System tracks multiple workers sequentially — v3.0 (Metadata sessions with durations)
- ✓ **COLLAB-04**: Worker can view occupation history — v3.0 (GET /api/history/{tag_spool}, 519-line test suite)

**Metrología (4/4):**
- ✓ **METRO-01**: Metrólogo can COMPLETAR with binary result — v3.0 (APROBADO/RECHAZADO, 3-state machine)
- ✓ **METRO-02**: Metrología workflow skips TOMAR — v3.0 (instant completion, no Redis lock)
- ✓ **METRO-03**: RECHAZADO triggers "Pendiente reparación" — v3.0 (EstadoDetalleBuilder auto-display)
- ✓ **METRO-04**: Metrología requires ARM + SOLD complete — v3.0 (prerequisite validation with 4 checks)

**Reparación (4/4):**
- ✓ **REPAR-01**: Worker can TOMAR spool RECHAZADO — v3.0 (ReparacionService with 4-state machine)
- ✓ **REPAR-02**: Reparación has no role restriction — v3.0 (OPERATION_TO_ROLES['REPARACION'] = [])
- ✓ **REPAR-03**: COMPLETAR returns to metrología queue — v3.0 (Estado_Detalle="PENDIENTE_METROLOGIA")
- ✓ **REPAR-04**: System limits cycles to 3 — v3.0 (CycleCounterService, BLOQUEADO after 3 rejections)

**Backward Compatibility (2/2):**
- ✓ **BC-01**: v2.1 data migrated to v3.0 schema — v3.0 (66 columns: 63 v2.1 + 3 v3.0, 7-day rollback window)
- ✓ **BC-02**: v2.1 tests preserved — v3.0 (233 tests archived to tests/v2.1-archive/)

### Active

**v4.0 Uniones System - Union-Level Tracking:**

**Foundation (Data Model & Architecture):**
- [ ] **UNION-01**: System reads pre-populated Uniones sheet (18 columns: ID, TAG_SPOOL, N_UNION, DN_UNION, TIPO_UNION, ARM_*, SOL_*, NDT_*, version, audit fields)
- [ ] **UNION-02**: System uses TAG_SPOOL as primary key (no breaking changes to Redis, Metadata, queries)
- [ ] **UNION-03**: Hoja Operaciones adds 5 new columns (68-72): Total_Uniones, Uniones_ARM_Completadas, Uniones_SOLD_Completadas, Pulgadas_ARM, Pulgadas_SOLD
- [ ] **UNION-04**: Hoja Metadata adds N_UNION column (position 11 at end, nullable) for granular audit trail
- [ ] **UNION-05**: System deprecates Armador/Soldador/Fecha_Armado/Fecha_Soldadura columns (stop writing, calculate on-demand from Uniones)

**Workflows (INICIAR/FINALIZAR UX):**
- [ ] **WORK-01**: Worker can INICIAR spool (occupies spool with Redis lock, writes Ocupado_Por + Fecha_Ocupacion, does NOT touch Uniones sheet)
- [ ] **WORK-02**: Worker can FINALIZAR with union selection (checkboxes for available unions, calculates pulgadas-diámetro, auto-determines PAUSAR vs COMPLETAR)
- [ ] **WORK-03**: System auto-determines PAUSAR (partial: 7/10 unions) vs COMPLETAR (full: 10/10 unions) based on selection count
- [ ] **WORK-04**: System supports partial completion workflows (worker A completes 7/10 ARM, worker B continues with remaining 3)
- [ ] **WORK-05**: System enforces ARM→SOLD validation (SOLD requires >= 1 union armada, backend filters only soldable unions)
- [ ] **WORK-06**: System supports 0 unions selected in FINALIZAR (modal confirmation "¿Liberar sin registrar?", logs SPOOL_CANCELADO event)

**Performance & Batch Operations:**
- [ ] **PERF-01**: System uses batch API writes (1 call vs N loops) for union updates via gspread.batch_update() with A1 notation
- [ ] **PERF-02**: System achieves < 1s latency (p95) for 10-union selection operation
- [ ] **PERF-03**: System uses batch Metadata logging with auto-chunking (900 rows/chunk) for granular union events
- [ ] **PERF-04**: System logs 1 batch event (spool level) + N granular events (union level) per FINALIZAR operation

**Metrics & Audit:**
- [ ] **METRIC-01**: System displays pulgadas-diámetro as primary metric (not spools) in dashboards and reports
- [ ] **METRIC-02**: System calculates worker performance in pulgadas-diámetro/day (SUM(DN_UNION) where ARM_FECHA_FIN != NULL)
- [ ] **METRIC-03**: System provides union-level metrics endpoint (total_uniones, arm_completadas, pulgadas_arm, pulgadas_sold)
- [ ] **METRIC-04**: Metadata logs granular UNION_ARM_REGISTRADA and UNION_SOLD_REGISTRADA events with N_UNION, DN_UNION, duracion_min

**v3.0/v4.0 Coexistence:**
- [ ] **COMPAT-01**: Frontend detects spool version by union count (count > 0 = v4.0, count = 0 = v3.0)
- [ ] **COMPAT-02**: v3.0 spools continue using TOMAR/PAUSAR/COMPLETAR workflow (3-button UX)
- [ ] **COMPAT-03**: v4.0 spools use INICIAR/FINALIZAR workflow (2-button UX with auto-determination)
- [ ] **COMPAT-04**: Backend maintains dual endpoints (/tomar, /pausar, /completar for v3.0 + /iniciar, /finalizar for v4.0)
- [ ] **COMPAT-05**: Metrología and Reparación workflows remain at spool level (defer union-level granularity to v4.1)

**Redis & State Management:**
- [ ] **STATE-01**: Redis locks have NO TTL (permanent until FINALIZAR) to support 5-8 hour work sessions
- [ ] **STATE-02**: System implements lazy cleanup (executed on INICIAR, removes locks > 24h with no Sheets match)
- [ ] **STATE-03**: System reconciles Redis locks from Sheets.Ocupado_Por on startup (auto-recovery)
- [ ] **STATE-04**: System triggers automatic transition to metrología queue when SOLD 100% complete (Estado_Detalle = "En Cola Metrología")

### Out of Scope

**Explicitly excluded to prevent scope creep:**
- **Automatic PAUSAR on timeout** — Manual only. Workers decide when to release spools. Automatic timeout could release spools mid-critical-operation.
- **GPS/RFID physical tracking** — Logical occupation only (worker assignment), not physical location sensors. Avoids $50K+ RTLS hardware cost.
- **Sub-1-second real-time sync** — 5-10 second refresh is sufficient for manufacturing floor (not warehouse picking). Google Sheets API limits make sub-second impossible.
- **Reservation system** — No "reserve for later" without physically taking spool. Prevents inventory hoarding.
- **Multi-operation TOMAR** — Worker can only TOMAR for ONE operation at a time (ARM or SOLD, not both). Prevents blocking.
- **Retroactive edits** — Metadata is append-only (no editing history). Regulatory requirement.
- **Complex role hierarchies** — Flat role system (Armador, Soldador, Metrología, Ayudante). No supervisor approval workflows in v3.0.

## Context

**Current Codebase State (v3.0 shipped 2026-01-28):**
- ZEUES v3.0 in production (Railway + Vercel)
- Python 3.11+ FastAPI backend with Clean Architecture + Redis for atomic locks
- Next.js 14 TypeScript frontend (mobile-first for tablets with SSE streaming)
- Google Sheets as database (source of truth, 66 columns: 63 v2.1 + 3 v3.0)
- Redis infrastructure deployed for occupation locks and pub/sub events
- 491,165 total lines of code (Python + TypeScript)
- 1,852 lines of integration tests (95%+ coverage for v3.0 features)
- Service Account authentication (zeus-mvp@zeus-mvp.iam.gserviceaccount.com)

**v3.0 Achievements:**
- Real-time occupation tracking with Redis atomic locks (1-hour TTL)
- Hierarchical state machines (6 states: 3 ARM + 3 SOLD) preventing state explosion
- SSE streaming for sub-10s dashboard updates with EventSource + exponential backoff
- Instant metrología inspection (binary APROBADO/RECHAZADO without occupation)
- Bounded reparación cycles (3-cycle limit before BLOQUEADO with supervisor override)
- Collaborative workflows enabling worker handoffs without strict ownership

**Known Technical Debt (from v3.0 audit):**
- Phase 4 missing formal VERIFICATION.md (code verified via integration checker)
- Frontend metrología/reparación integration unverified (backend complete, UI may be missing)
- No dedicated reparación router (endpoints in actions.py instead of separate router)
- No E2E SSE test with real infrastructure (verified at code level only)
- 7-day rollback window expires 2026-02-02 (v2.1 backup will be archived)

## Constraints

- **Tech Stack (MUST keep)**: Python FastAPI + Next.js + Google Sheets (no database migration)
- **Mobile-First**: Tablet UI with large buttons (h-16/h-20), touch-friendly, no complex desktop features
- **Google Sheets Limits**: 60 writes/min/user, 200-500ms latency, no WebSocket support, eventual consistency
- **Production Stability**: v2.1 MUST remain working during v3.0 development (244 tests passing, zero downtime)
- **Manufacturing Scale**: 30-50 workers, 2,000+ spools, 10-15 req/sec peak load
- **Regulatory**: Metadata audit trail mandatory (append-only, immutable), no retroactive edits

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| **Branch-based migration over dual-write** | v2.1 stability critical. Branch isolation eliminates synchronization complexity. Build v3.0 in separate branch, one-time cutover when ready, 1-week rollback window. | ✓ Good — Migration executed successfully in Phase 1, 66 columns added, 7-day rollback active until 2026-02-02 |
| **Server-Sent Events (SSE) over WebSockets** | Unidirectional updates only (server → client), HTTP-based simplicity, native browser support, auto-reconnect, lower resource usage for manufacturing floor scale | ✓ Good — Implemented in Phase 4, EventSource with exponential backoff (1s-30s), Page Visibility API for mobile lifecycle, sub-10s latency achieved |
| **Redis cache + Google Sheets** | Google Sheets API limits (60 writes/min) require caching layer. Redis provides sub-50ms reads + atomic operations (SETNX) for race condition prevention. Reduces API calls 80-90%. | ✓ Good — Phase 2 deployed Redis with atomic locks (SET NX EX), 1-hour TTL, validated with 10 concurrent TOMAR tests (1 success, 9 conflicts) |
| **python-statemachine 2.5.0** | Async-native state machine library with 100% test coverage, actively maintained (2025 updates), expressive API integrates with Pydantic validation, prevents state explosion with hierarchical design | ✓ Good — Integrated in Phase 3, separate ARM/SOLD machines, callbacks for Sheets updates, 6 states total (not 27) |
| **Optimistic locking with version tokens** | Google Sheets doesn't support row-level locks. Low contention environment (10-20 workers on 2,000 spools = 0.5% collision rate) makes optimistic locking viable. Standard web pattern with 3x retry. | ✓ Good — Phase 2 implemented UUID4 version tokens, max 3 retries with jittered exponential backoff (100ms-10s), two-layer defense (Redis + version tokens) |
| **5-second polling + SSE streaming** | Google Drive webhooks batch every 3 minutes (too slow). Polling gives predictable updates, well under Google Sheets API quotas (300 reads/100s/user = 180 req/min for 30 workers = ~6 req/sec shared). Combined with SSE for push notifications. | ⚠️ Revisit — Phase 4 implemented SSE only (no polling), relying on event publishing after Sheets writes. Load test with 30 concurrent users needed to validate quota usage. |
| **Hierarchical state machine (6 states, not 27)** | v3.0 naive approach: 3 operations × 3 occupation states × 3 progress states = 27 states (unmaintainable). Hierarchical model: Separate ARM/SOLD machines + Estado_Detalle for display = 6 manageable states. | ✓ Good — Phase 3 implemented separate state machines, EstadoDetalleBuilder for combined display, prevents state explosion while maintaining clarity |
| **Bounded reparación cycles (max 3)** | Infinite metrología → reparación loops could trap spools forever. Industry best practice: 3 attempts before supervisor escalation. After 3 failures, likely requires root cause analysis (design flaw, not execution error). | ✓ Good — Phase 6 implemented CycleCounterService with MAX_CYCLES=3, SpoolBloqueadoError (HTTP 403), EstadoDetalleService detects supervisor overrides |
| **Metrología instant completion (no TOMAR)** | Metrología inspection takes seconds (visual check, measurements), not hours like ARM/SOLD. Occupying spool for inspection creates false "unavailable" signal. Instant COMPLETAR with result (APROBADO/RECHAZADO) matches workflow reality. | ✓ Good — Phase 5 implemented MetrologiaService.completar() without Redis lock, prerequisite validation (ARM+SOLD complete), binary resultado with 44 comprehensive tests |
| **Cycle counting embedded in Estado_Detalle** | Avoid schema migration by parsing cycle count from Estado_Detalle string instead of dedicated column. Pattern: "RECHAZADO - Ciclo 2/3" | ✓ Good — Phase 6 implemented CycleCounterService for extraction/increment, resets to 0 after APROBADO, preserves cycles across state transitions |
| **No role restriction for reparación** | Consistent with ARM/SOLD pattern where any worker with role can perform operation. All workers can repair, no special "Reparador" role needed. | ✓ Good — Phase 6 implemented OPERATION_TO_ROLES['REPARACION'] = [], test_any_worker_can_tomar_reparacion validates pattern |

---
*Last updated: 2026-01-30 after v4.0 milestone initialization*
