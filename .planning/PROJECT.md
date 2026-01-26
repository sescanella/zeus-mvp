# ZEUES v3.0 - Real-Time Location Tracking

## What This Is

ZEUES v3.0 transforms the manufacturing traceability system from progress tracking to real-time location/occupation tracking. Instead of asking "how complete is the work?", v3.0 answers "WHO has WHICH spool right now?" enabling collaborative sequential workflows where multiple workers (Armadores, Soldadores) can work on the same spool in flexible handoffs, with live visibility into which spools are DISPONIBLE vs OCUPADO on the manufacturing floor.

## Core Value

**Real-time visibility of spool occupation** - See EN VIVO who is physically working on which spool, identify available vs occupied spools instantly, and enable flexible collaborative workflows where work can pause mid-stream and be continued by any qualified worker.

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

### Active

**v3.0 - 25 requirements across 6 categories:**

**Location Tracking (6):**
- [ ] **LOC-01**: Worker can TOMAR available spool (occupation constraint enforced - physical impossibility of being in 2 places)
- [ ] **LOC-02**: Worker can PAUSAR spool without completing (releases occupation → DISPONIBLE, preserves partial progress)
- [ ] **LOC-03**: Worker can COMPLETAR spool work (finishes operation → DISPONIBLE)
- [ ] **LOC-04**: System prevents race conditions (2 workers cannot TOMAR same spool simultaneously - optimistic locking)
- [ ] **LOC-05**: Worker can see real-time list of DISPONIBLE spools (< 10s refresh latency)
- [ ] **LOC-06**: Worker can see real-time "who has what" dashboard (OCUPADO spools with owner name)

**State Management (4):**
- [ ] **STATE-01**: System displays combined state (occupation + ARM progress + SOLD progress in single view)
- [ ] **STATE-02**: Metadata logs all TOMAR/PAUSAR/COMPLETAR events (regulatory audit trail)
- [ ] **STATE-03**: Estado_Detalle column shows dynamic state ("Armando: Juan (93) - ARM parcial, SOLD pendiente")
- [ ] **STATE-04**: Hierarchical state machine prevents state explosion (9 manageable states, not 27+)

**Collaborative Work (4):**
- [ ] **COLLAB-01**: Any worker with correct role can continue partially-completed work (no strict ownership)
- [ ] **COLLAB-02**: System enforces operation dependencies (SOLD requires ARM initiated first)
- [ ] **COLLAB-03**: System tracks multiple workers on same spool sequentially (collaborative audit trail)
- [ ] **COLLAB-04**: Worker can view occupation history per spool (who had it, when, for how long)

**Metrología (4):**
- [ ] **METRO-01**: Metrólogo can COMPLETAR with binary result (APROBADO / RECHAZADO only - no progress tracking)
- [ ] **METRO-02**: Metrología workflow skips TOMAR (instant completion, no occupation period)
- [ ] **METRO-03**: RECHAZADO result triggers estado "Pendiente reparación" (automatic transition)
- [ ] **METRO-04**: Metrología requires ARM + SOLD both COMPLETADO (prerequisite validation)

**Reparación (4):**
- [ ] **REPAR-01**: Worker can TOMAR spool with estado RECHAZADO for reparación
- [ ] **REPAR-02**: Reparación specifies responsible role (Armador for ARM defects, Soldador for SOLD defects)
- [ ] **REPAR-03**: COMPLETAR reparación returns spool to metrología queue (cycle back)
- [ ] **REPAR-04**: System limits reparación cycles (max 3 loops before supervisor escalation)

**Backward Compatibility (3):**
- [ ] **BC-01**: v2.1 production data migrates to v3.0 schema without data loss (expand-migrate-contract pattern)
- [ ] **BC-02**: All 244 existing v2.1 tests continue passing during and after migration
- [ ] **BC-03**: Dual-write period (2-4 weeks) supports gradual production cutover with rollback capability

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

**Technical Environment:**
- Existing ZEUES v2.1 in production (Railway + Vercel)
- Python 3.11+ FastAPI backend with Clean Architecture
- Next.js 14 TypeScript frontend (mobile-first for tablets)
- Google Sheets as database (source of truth, 2,493 spools)
- 244 passing tests (pytest backend, Playwright E2E frontend)
- Service Account authentication (zeus-mvp@zeus-mvp.iam.gserviceaccount.com)

**User Research (Questioning Phase):**
- Manufacturing plant workflow: Workers pause mid-operation (shift change, missing parts, blocked), handoff spools to next available worker (not necessarily same person), flexible sequential collaboration is reality (not strict linear ARM 100% → SOLD 100%)
- Core problem v2.1 doesn't solve: "Who has which spool right now?" - Can't see available spools vs occupied, can't identify why spools are stuck
- Expected behavior: Worker scans/selects spool → TOMAR (occupies physically) → works → PAUSAR (releases) OR COMPLETAR (finishes) → next worker TOMAR → continues work
- Metrología special case: Instant approval/rejection (seconds, not hours), no occupation period needed, binary outcome (pass/fail)
- Reparación reality: Can fail metrología multiple times (weld defect, re-weld, fail again, re-weld again), need bounded cycles to prevent infinite loops

**Known Issues v2.1 to Address:**
- Ownership restriction too strict (only worker who INICIAR can COMPLETAR) - blocks collaborative work
- No visibility into "work in progress" vs "available" - workers waste time checking unavailable spools
- Sequential ARM 100% → SOLD 100% doesn't match reality - partial work common

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
| **Server-Sent Events (SSE) over WebSockets** | Unidirectional updates only (server → client), HTTP-based simplicity, native browser support, auto-reconnect, lower resource usage for manufacturing floor scale | — Pending (Phase 2 implementation) |
| **Redis cache + Google Sheets** | Google Sheets API limits (60 writes/min) require caching layer. Redis provides sub-50ms reads + atomic operations (SETNX) for race condition prevention. Reduces API calls 80-90%. | — Pending (Phase 1 architecture decision) |
| **python-statemachine 2.5.0** | Async-native state machine library with 100% test coverage, actively maintained (2025 updates), expressive API integrates with Pydantic validation, prevents state explosion with hierarchical design | — Pending (Phase 1 implementation) |
| **Optimistic locking with version tokens** | Google Sheets doesn't support row-level locks. Low contention environment (10-20 workers on 2,000 spools = 0.5% collision rate) makes optimistic locking viable. Standard web pattern with 3x retry. | — Pending (Phase 1 conflict resolution) |
| **5-second polling + SSE streaming** | Google Drive webhooks batch every 3 minutes (too slow). Polling gives predictable updates, well under Google Sheets API quotas (300 reads/100s/user = 180 req/min for 30 workers = ~6 req/sec shared). Combined with SSE for push notifications. | — Pending (Phase 2 real-time architecture) |
| **Hierarchical state machine (9 states, not 27)** | v3.0 naive approach: 3 operations × 3 occupation states × 3 progress states = 27 states (unmaintainable). Hierarchical model: Primary state (DISPONIBLE/OCUPADO/PAUSADO/COMPLETADO) + sub-state (ARM_PENDIENTE/ARM_PARCIAL/ARM_COMPLETO, SOLD_PENDIENTE/etc) + context (worker_id) = 9 manageable states. | — Pending (Phase 1 state machine design) |
| **Expand-Migrate-Contract pattern** | Breaking v2.1 production is unacceptable (244 tests, real users). Add v3.0 columns without removing v2.1 columns, dual-write to both schemas during 2-4 week migration, gradual cutover with rollback capability if v3.0 fails. | — Pending (Phase 0 migration strategy) |
| **Bounded reparación cycles (max 3)** | Infinite metrología → reparación loops could trap spools forever. Industry best practice: 3 attempts before supervisor escalation. After 3 failures, likely requires root cause analysis (design flaw, not execution error). | — Pending (Phase 5 implementation) |
| **Metrología instant completion (no TOMAR)** | Metrología inspection takes seconds (visual check, measurements), not hours like ARM/SOLD. Occupying spool for inspection creates false "unavailable" signal. Instant COMPLETAR with result (APROBADO/RECHAZADO) matches workflow reality. | — Pending (Phase 4 special case handling) |

---
*Last updated: 2026-01-26 after initialization*
