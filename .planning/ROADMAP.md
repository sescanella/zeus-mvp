# Roadmap: ZEUES v3.0

## Overview

ZEUES v3.0 transforms the manufacturing traceability system from progress tracking to real-time location/occupation tracking. The journey starts with safe migration from v2.1 production (Phase 1), builds core TOMAR/PAUSAR/COMPLETAR operations with race condition prevention (Phase 2), adds hierarchical state machines for collaborative workflows (Phase 3), delivers real-time visibility dashboards (Phase 4), handles Metrología instant completion special case (Phase 5), and closes with bounded reparación cycles for quality loops (Phase 6).

## Phases

**Phase Numbering:**
- Integer phases (1, 2, 3): Planned milestone work
- Decimal phases (2.1, 2.2): Urgent insertions (marked with INSERTED)

Decimal phases appear between their surrounding integers in numeric order.

- [x] **Phase 1: Migration Foundation** - Safe v2.1 → v3.0 schema migration with backward compatibility ⚠️ Infrastructure complete, gaps found
- [ ] **Phase 2: Core Location Tracking** - TOMAR/PAUSAR/COMPLETAR operations with race condition prevention
- [ ] **Phase 3: State Machine & Collaboration** - Hierarchical states + collaborative workflows
- [ ] **Phase 4: Real-Time Visibility** - SSE updates + who-has-what dashboards
- [ ] **Phase 5: Metrología Workflow** - Instant completion with APROBADO/RECHAZADO
- [ ] **Phase 6: Reparación Loops** - Bounded quality cycles with supervisor escalation

## Phase Details

### Phase 1: Migration Foundation
**Goal**: v2.1 production data migrates to v3.0 schema without breaking existing functionality
**Depends on**: Nothing (first phase)
**Requirements**: BC-01, BC-02 (updated: tests pass before archiving)
**Success Criteria** (what must be TRUE):
  1. Production Google Sheet has complete backup copy with timestamp
  2. Three new columns (Ocupado_Por, Fecha_Ocupacion, version) exist at end of sheet
  3. All existing v2.1 data remains unmodified and accessible
  4. Migration executes atomically with checkpoint recovery
  5. Rollback capability restores v2.1 state completely if needed
**Plans**: 5 plans

Plans:
- [x] 01-01-PLAN.md — Backup and schema expansion scripts (5 min)
- [x] 01-02-PLAN.md — Column mapping infrastructure for v3.0 (5 min)
- [x] 01-03-PLAN.md — Test migration and v3.0 smoke tests (9 min)
- [x] 01-04-PLAN.md — Migration coordinator and rollback system (13 min)
- [x] 01-05-PLAN.md — End-to-end migration verification suite (5 min)

**Status:** Infrastructure complete (37 min) — Gaps found: production execution needed
**Completed:** 2026-01-26

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
**Plans**: TBD

Plans:
- [ ] 02-01: Deploy Redis cache with atomic locking (SETNX) and write-through pattern
- [ ] 02-02: Implement OccupationService with TOMAR/PAUSAR/COMPLETAR endpoints
- [ ] 02-03: Create ConflictService for optimistic locking with version tokens
- [ ] 02-04: Add race condition test suite (concurrent TOMAR validation)

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
**Plans**: TBD

Plans:
- [ ] 03-01: Design hierarchical state machine (< 15 states, peer-reviewed diagram)
- [ ] 03-02: Implement python-statemachine integration with guards/callbacks
- [ ] 03-03: Create StateService for combined state display logic
- [ ] 03-04: Build occupation history view (leverage Metadata events)

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
| 1. Migration Foundation | 5/5 | Gaps found (3/5 criteria) | 2026-01-26 |
| 2. Core Location Tracking | 0/4 | Not started | - |
| 3. State Machine & Collaboration | 0/4 | Not started | - |
| 4. Real-Time Visibility | 0/4 | Not started | - |
| 5. Metrología Workflow | 0/4 | Not started | - |
| 6. Reparación Loops | 0/4 | Not started | - |
