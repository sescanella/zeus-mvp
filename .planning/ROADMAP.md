# Roadmap: ZEUES v3.0

## Overview

ZEUES v3.0 transforms the manufacturing traceability system from progress tracking to real-time location/occupation tracking. The journey starts with safe migration from v2.1 production (Phase 1), builds core TOMAR/PAUSAR/COMPLETAR operations with race condition prevention (Phase 2), adds hierarchical state machines for collaborative workflows (Phase 3), delivers real-time visibility dashboards (Phase 4), handles Metrología instant completion special case (Phase 5), and closes with bounded reparación cycles for quality loops (Phase 6).

## Phases

**Phase Numbering:**
- Integer phases (1, 2, 3): Planned milestone work
- Decimal phases (2.1, 2.2): Urgent insertions (marked with INSERTED)

Decimal phases appear between their surrounding integers in numeric order.

### Phase 1: Migration Foundation
**Goal**: Safe transition from v2.1 to v3.0 schema without disrupting production operations
**Depends on**: None
**Requirements**: MIG-01, MIG-02, MIG-03, MIG-04
**Success Criteria** (what must be TRUE):
  1. Production sheet has 3 new v3.0 columns: Ocupado_Por, Fecha_Ocupacion, version
  2. v2.1 backend continues working unchanged with existing 63 columns
  3. Test migration executed successfully showing compatibility
  4. Rollback capability documented and tested within 1-week window
  5. Performance baseline shows <5% degradation with new columns
**Plans**: 9 plans (5 initial + 4 gap closure)

Plans:
- [x] 01-01-PLAN.md — Database schema update (9 min)
- [x] 01-02-PLAN.md — Backward compatibility layer (13 min)
- [x] 01-03-PLAN.md — Test migration execution (5 min)
- [x] 01-04-PLAN.md — Rollback capability (6 min)
- [x] 01-05-PLAN.md — Performance baseline (4 min)
- [x] 01-06-GAP-PLAN.md — Schema verification coordinator (2 min)
- [x] 01-07-GAP-PLAN.md — v3.0 column addition (3.5 min)
- [x] 01-08a-GAP-PLAN.md — Migration coordinator execution (5 min)
- [x] 01-08b-GAP-PLAN.md — Migration documentation (3.5 min)

**Status:** Complete (51 min total: 37 min infrastructure + 14 min gap closure)
**Completed:** 2026-01-27

### Phase 2: Core Location Tracking
**Goal**: Workers can take, pause, and complete spool work with physical occupation constraints enforced
**Depends on**: Phase 1
**Requirements**: LOC-01, LOC-02, LOC-03, LOC-04
**Success Criteria** (what must be TRUE):
  1. Worker can TOMAR available spool and system marks it OCUPADO with their name
  2. Worker can PAUSAR spool mid-work and it becomes DISPONIBLE for others
  3. Worker can COMPLETAR spool and it becomes DISPONIBLE with operation marked complete
  4. Two workers cannot TOMAR same spool simultaneously (race condition test with 10 parallel requests shows 1 success, 9 conflicts)
  5. Metadata logs TOMAR/PAUSAR/COMPLETAR events with worker_id, timestamp, operation type
**Plans**: 6 plans (4 initial + 2 gap closure)

Plans:
- [x] 02-01-PLAN.md — Deploy Redis infrastructure and lock service (3 min)
- [x] 02-02-PLAN.md — Implement OccupationService with TOMAR/PAUSAR/COMPLETAR (5.5 min)
- [x] 02-03-PLAN.md — Add optimistic locking with version tokens (4 min)
- [x] 02-04-PLAN.md — Race condition test suite (TDD) (6 min)
- [x] 02-05-GAP-PLAN.md — Fix Redis repository get_client method (1 min)
- [x] 02-06-GAP-PLAN.md — Integrate Redis lifecycle in FastAPI startup/shutdown (2.6 min)

**Status:** Complete (22.1 min total: 18.5 min infrastructure + 3.6 min gap closure)
**Completed:** 2026-01-27

### Phase 3: State Machine & Collaboration
**Goal**: System manages hierarchical spool states and enables multiple workers to collaborate on same spool sequentially
**Depends on**: Phase 2
**Requirements**: STATE-01, STATE-02, STATE-03, STATE-04, COLLAB-01, COLLAB-02, COLLAB-03, COLLAB-04
**Success Criteria** (what must be TRUE):
  1. Dashboard displays combined state: occupation status + ARM progress + SOLD progress in single view
  2. Estado_Detalle column shows dynamic state like "Ocupado: Juan (93) - ARM parcial, SOLD pendiente"
  3. Any Armador can continue ARM work started by different Armador (no strict ownership)
  4. System prevents SOLD TOMAR if ARM not initiated (dependency validation)
  5. Worker can view occupation history showing 3 workers worked on spool sequentially with durations
**Plans**: 4 plans

Plans:
- [x] 03-01-PLAN.md — Schema and state machine foundation (2.87 min)
- [x] 03-02-PLAN.md — StateService orchestration with hydration (2.9 min)
- [x] 03-03-PLAN.md — State callbacks and column updates (3.6 min)
- [x] 03-04-PLAN.md — Collaboration history and testing (6 min)

**Status:** Complete (15.37 min total)
**Completed:** 2026-01-27

### Phase 4: Real-Time Visibility
**Goal**: Workers see available vs occupied spools in real-time with sub-10-second refresh latency
**Depends on**: Phase 3
**Requirements**: LOC-05, LOC-06
**Success Criteria** (what must be TRUE):
  1. Available spools list refreshes within 10 seconds when another worker TOMArs a spool
  2. "Who has what" dashboard shows all occupied spools with owner names updated in real-time
  3. SSE connection stays alive for 8-hour worker shift with auto-reconnect on network drops
  4. 30 concurrent workers generate less than 80 Google Sheets API requests per minute
**Plans**: TBD

Plans:
- [ ] 04-01: Implement SSE endpoint with sse-starlette and Redis pub/sub
- [ ] 04-02: Build frontend EventSource integration with React hooks
- [ ] 04-03: Create "who has what" dashboard component
- [ ] 04-04: Load test with 30 concurrent users (verify API quota, response times)

### Phase 5: Metrología Workflow
**Goal**: Metrología inspection completes instantly with binary result without occupation period
**Depends on**: Phase 4
**Requirements**: METRO-01, METRO-02, METRO-03, METRO-04
**Success Criteria** (what must be TRUE):
  1. Metrólogo can COMPLETAR metrología with APROBADO result and spool transitions to final state
  2. Metrólogo can COMPLETAR metrología with RECHAZADO result and spool estado shows "Pendiente reparación"
  3. Metrología workflow skips TOMAR step (instant completion, no occupation)
  4. System blocks metrología attempt if ARM or SOLD not both COMPLETADO (prerequisite validation)
**Plans**: TBD

Plans:
- [ ] 05-01: Design Metrología state machine (separate from ARM/SOLD occupation flow)
- [ ] 05-02: Implement instant COMPLETAR endpoint with resultado (APROBADO/RECHAZADO)
- [ ] 05-03: Add prerequisite validation (ARM + SOLD must be COMPLETADO)
- [ ] 05-04: Create frontend Metrología flow (skip spool selection, direct completion)

### Phase 6: Reparación Loops
**Goal**: Rejected spools can be repaired and re-inspected with bounded cycles preventing infinite loops
**Depends on**: Phase 5
**Requirements**: REPAR-01, REPAR-02, REPAR-03, REPAR-04
**Success Criteria** (what must be TRUE):
  1. Worker can TOMAR spool with estado RECHAZADO for reparación work
  2. Reparación UI shows responsible role (Armador for ARM defects, Soldador for SOLD defects)
  3. COMPLETAR reparación returns spool to metrología queue automatically
  4. After 3 reparación cycles, spool becomes BLOQUEADO and requires supervisor override
**Plans**: TBD

Plans:
- [ ] 06-01: Implement reparación state transitions (RECHAZADO → REPARACION → METROLOGIA)
- [ ] 06-02: Add reparacion_count column and cycle limit validation (max 3)
- [ ] 06-03: Create supervisor override endpoint for 4th repair attempt
- [ ] 06-04: Build reparación frontend flow with role specification

## Progress

**Execution Order:**
Phases execute in numeric order: 1 → 2 → 3 → 4 → 5 → 6

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 1: Migration Foundation | 9/9 ✓ | Complete | 2026-01-27 |
| 2: Core Location Tracking | 6/6 ✓ | Complete | 2026-01-27 |
| 3: State Machine & Collaboration | 4/4 ✓ | Complete | 2026-01-27 |
| 4: Real-Time Visibility | 0/4 | Ready | — |
| 5: Metrología Workflow | 0/4 | Blocked (needs Phase 4) | — |
| 6: Reparación Loops | 0/4 | Blocked (needs Phase 5) | — |

**Overall:** 19/35 plans (54%)

## Decision Log

| Phase | Decision | Rationale | Date |
|-------|----------|-----------|------|
| Planning | Branch-based migration | Safer than dual-write complexity | 2026-01-26 |
| Phase 1 | Columns at sheet end (64-66) | Safest position for backward compatibility | 2026-01-26 |
| Phase 1 | Archive v2.1 tests | 244 tests → 5-10 smoke tests for v3.0 | 2026-01-26 |
| Phase 1 | 1-week rollback window | Balance safety with moving forward | 2026-01-26 |
| Phase 2 | Hierarchical states (<15) | Prevent state explosion (not 27 combinations) | 2026-01-26 |
| Phase 2 | Optimistic locking | Better UX than pessimistic blocking | 2026-01-26 |

## Next Actions

**Immediate (Phase 2):**
1. Execute plans: `/gsd:execute-phase 2`
2. Deploy Redis instance (Railway addon or external)
3. Implement atomic locking infrastructure

**Upcoming (Phase 3):**
1. Design state machine diagram
2. Review with team before implementation
3. Plan collaboration flows

## Risk Register

| Risk | Impact | Mitigation | Status |
|------|--------|------------|--------|
| Google Sheets API quotas | High | Redis caching, batch operations | Planned (Phase 2) |
| Race conditions | High | Redis locks + version tokens | Planned (Phase 2) |
| State explosion | Medium | Hierarchical state machine | Planned (Phase 3) |
| Network latency | Medium | SSE + local state cache | Planned (Phase 4) |
| Infinite reparación | Low | 3-cycle limit + supervisor override | Planned (Phase 6) |