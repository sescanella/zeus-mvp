# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-01-26)

**Core value:** Real-time visibility of spool occupation - See EN VIVO who is working on which spool
**Current focus:** Phase 4 - Real-Time Visibility

## Current Position

Phase: 4 of 6 (Real-Time Visibility) 🔄 IN PROGRESS
Plan: 1 of 3 (04-01-PLAN.md) ✓ SSE backend infrastructure complete
Status: Phase 4 started - Real-time event streaming via SSE + Redis pub/sub
Last activity: 2026-01-27 — Completed 04-01: SSE endpoint with Redis pub/sub broadcasting

Progress: [█████████████████░] 33% Phase 4 - 1 of 3 plans complete

## Performance Metrics

**Velocity:**
- Total plans completed: 24
- Average duration: 4.2 minutes
- Total execution time: 1.68 hours

**By Phase:**

| Phase | Plans | Total | Avg/Plan |
|-------|-------|-------|----------|
| 01    | 9/9 ✅ | 51 min | 5.7 min    |
| 02    | 6/6 ✅  | 22 min  | 3.7 min    |
| 03    | 4/4 ✅ | 16 min  | 4.0 min    |
| 04    | 1/3 🔄 | 4 min  | 4.0 min    |

**Recent Trend:**
- Last 3 plans: 03-03 (3.6 min), 03-04 (6 min), 04-01 (4 min)
- Trend: Phase 4 started strong with 4 min (matching Phase 3 average)

*Updated after each plan completion*

## Accumulated Context

### Decisions

Decisions are logged in PROJECT.md Key Decisions table.
Recent decisions affecting current work:

- **Phase 1 (Planning):** Branch-based migration chosen over dual-write complexity - build v3.0 in separate branch, one-time cutover
- Phase 1 (Planning): Three new columns at end of sheet (Ocupado_Por, Fecha_Ocupacion, version) - safest position
- Phase 1 (Planning): Archive v2.1 tests, create 5-10 v3.0 smoke tests instead of running all 244 tests
- Phase 1 (Planning): 1-week rollback window after cutover before archiving v2.1
- Phase 1 (Planning): Hierarchical state machine (9 states, not 27) to prevent state explosion
- Phase 1 (Planning): Optimistic locking with version tokens for race condition prevention
- **Phase 1 (01-01):** Script-based migrations with idempotency for safe re-execution
- Phase 1 (01-01): Import V3_COLUMNS from config for single source of truth
- Phase 1 (01-01): Idempotency via column existence check (no migration version tracking)
- **Phase 1 (01-02):** Compatibility mode pattern for safe v2.1 → v3.0 migration
- Phase 1 (01-02): Default to v2.1 mode until migration complete (explicit opt-in to v3.0)
- Phase 1 (01-02): esta_ocupado as computed property (single source of truth from ocupado_por)
- **Phase 1 (01-03):** Archive v2.1 tests, create 28 focused v3.0 smoke tests (< 3 sec execution)
- Phase 1 (01-03): Use pytest.skip for migration-dependent tests (clear communication)
- Phase 1 (01-03): Test archival preserves historical knowledge without maintenance burden
- **Phase 1 (01-04):** 5-step migration process (backup, add columns, verify, init versions, smoke tests)
- Phase 1 (01-04): JSON checkpoint files for atomic operations with recovery
- Phase 1 (01-04): Sample-based verification (10 rows) for fast validation
- Phase 1 (01-04): 7-day rollback window balances safety and storage costs
- **Phase 1 (01-05):** Skip-based test organization for manual tests (clear distinction between CI-automated and manual)
- Phase 1 (01-05): Test harness dry-run mode prevents accidental sheet manipulation
- Phase 1 (01-05): Two-job CI pipeline (test-migration + smoke-tests) for parallel execution and fast feedback
- Phase 1 (01-05): psutil optional dependency with graceful skip for memory tests
- **Phase 1 (01-06-GAP):** Manual backup via Google Sheets UI when API storage quota is exceeded
- Phase 1 (01-06-GAP): 7-day rollback window balances safety with storage constraints
- Phase 1 (01-06-GAP): Verification via gspread API confirms backup integrity (row/column counts)
- **Phase 1 (01-07-GAP):** Sheet grid expansion before column addition (Google Sheets API enforces strict limits)
- Phase 1 (01-07-GAP): Production schema is 66 columns (63 v2.1 + 3 v3.0), not 68 as originally planned
- Phase 1 (01-07-GAP): Column positions 64-66 (1-indexed) for Ocupado_Por, Fecha_Ocupacion, version
- **Phase 1 (01-08a-GAP):** Fix verification script to use read_worksheet() instead of non-existent get_headers()/get_all_values()
- Phase 1 (01-08a-GAP): Skip empty rows in data integrity checks (292 valid rows with TAG_SPOOL)
- Phase 1 (01-08a-GAP): Migration coordinator executed with checkpoint recovery - all 6 verification checks passed
- **Phase 1 (01-08b-GAP):** Phase 1 marked complete with all 5 truths verified after gap closure
- Phase 1 (01-08b-GAP): Migration completion documentation includes rollback window expiration (2026-02-02)
- Phase 1 (01-08b-GAP): Production schema is 66 columns (63 v2.1 + 3 v3.0), confirmed and documented
- **Phase 2 (02-01):** 1-hour lock TTL balances long operations safety with preventing permanent locks
- Phase 2 (02-01): Lock token format "{worker_id}:{uuid4}" embeds identity + unique token for ownership verification
- Phase 2 (02-01): RedisRepository singleton pattern shares connection pool (max 50 connections) across all requests
- **Phase 2 (02-02):** Explicit 409 mapping in router endpoints for clear LOC-04 requirement compliance
- Phase 2 (02-02): Best-effort metadata logging - Redis lock + Sheets write are critical, metadata is audit only
- Phase 2 (02-02): Deferred Estado_Ocupacion column to future v3.0 schema enhancement
- **Phase 2 (02-03):** UUID4 version tokens chosen over sequential counters for global uniqueness
- Phase 2 (02-03): Max 3 retry attempts with exponential backoff (100ms-10s range) balances success rate with load
- Phase 2 (02-03): Jittered backoff (±25%) prevents thundering herd during concurrent retries
- Phase 2 (02-03): Two-layer defense - Redis locks (primary) + version tokens (secondary) for data integrity
- **Phase 2 (02-04):** Integration tests require real infrastructure (FastAPI + Redis + Sheets) for true race condition validation
- Phase 2 (02-04): Unit tests use AsyncMock for fast, isolated testing without infrastructure dependencies
- Phase 2 (02-04): Test guide documents procedures instead of automated verification during plan execution
- **Phase 2 (02-05-GAP):** get_client() method for dependency injection - repository owns client lifecycle
- Phase 2 (02-05-GAP): Optional[Redis] return type handles pre-connection state safely
- Phase 2 (02-05-GAP): Warning logs help debug startup timing issues
- **Phase 2 (02-06-GAP):** Non-blocking Redis startup - API starts even if Redis fails, enabling degraded mode
- Phase 2 (02-06-GAP): Redis lifecycle integrated in FastAPI startup/shutdown events for proper connection management
- Phase 2 (02-06-GAP): Redis health check endpoint (/api/redis-health) for monitoring connection status
- **Phase 2 (Orchestrator):** Missing datetime imports in metadata_repository.py fixed - date/datetime required for type hints
- Phase 2 (Orchestrator): SheetsRepository.get_spool_by_tag() implemented - missing method required by OccupationService
- Phase 2 (Orchestrator): Dynamic column mapping with multi-format date parsing for robustness
- Phase 2 (Orchestrator): Integration test validation requires test data - 404 responses confirm correct error handling
- **Phase 3 (03-01):** Estado_Detalle column added at position 67 for combined state display (occupation + operation progress)
- Phase 3 (03-01): Separate state machines per operation (ARM/SOLD) prevents state explosion (9 states instead of 27+)
- Phase 3 (03-01): Guard + validator pattern for dependencies - guards control transitions, validators provide error messages
- Phase 3 (03-01): python-statemachine==2.5.0 chosen for declarative state management with async support
- **Phase 3 (03-03):** State machines own column updates via callbacks - single source of truth for Sheets writes
- Phase 3 (03-03): Estado_Detalle updates on EVERY state transition (TOMAR/PAUSAR/COMPLETAR) for real-time visibility
- Phase 3 (03-03): Date format DD-MM-YYYY for consistency with existing production data
- **Phase 3 (03-04):** History shows ALL events chronologically - no filtering for simple complete view
- Phase 3 (03-04): Duration calculation shows time between TOMAR and PAUSAR/COMPLETAR
- Phase 3 (03-04): Integration tests use mocks to verify StateService orchestration patterns
- **Phase 4 (04-01):** Channel name spools:updates for all spool state changes (centralized broadcast)
- Phase 4 (04-01): Event types TOMAR, PAUSAR, COMPLETAR, STATE_CHANGE for different transition types
- Phase 4 (04-01): 15-second keepalive ping with 30-second send timeout for connection management
- Phase 4 (04-01): X-Accel-Buffering: no header prevents nginx/proxy buffering issues
- Phase 4 (04-01): Best-effort event publishing (logs errors, returns bool) - doesn't block operations

### Pending Todos

None yet.

### Blockers/Concerns

**Phase 1 (COMPLETE):** ✅ All 9 plans executed, all 5 truths verified
- ✅ Gap 1 CLOSED: Production backup created (1kWUjegxV00MOJver_9ljZqHxgJJBgErnH_J--N4TS9M) - 7-day rollback window active until 2026-02-02
- ✅ Gap 2 CLOSED: v3.0 columns added to production sheet (66 columns: 63 v2.1 + 3 v3.0)
- ✅ Gap 3a CLOSED: Migration coordinator executed - 6/6 verification checks, 39/39 tests passed
- ✅ Gap 3b CLOSED: Migration documentation complete (MIGRATION_COMPLETE.md, 01-VERIFICATION.md updated)
- **Status:** Phase 1 complete

**Phase 2 (COMPLETE):** ✅ Core Location Tracking - All 4 waves + 2 gap closures complete
- ✅ Wave 1: Redis infrastructure deployed (02-01: 3 min)
- ✅ Wave 2: OccupationService with TOMAR/PAUSAR/COMPLETAR (02-02: 5.5 min)
- ✅ Wave 3: Optimistic locking with version tokens (02-03: 4 min)
- ✅ Wave 4: Race condition test suite (02-04: 6 min)
- ✅ Gap 5: Fix Redis repository get_client method (02-05-GAP: 1 min)
- ✅ Gap 6: Integrate Redis lifecycle in FastAPI startup/shutdown (02-06-GAP: 2.6 min)
- **Status:** Phase 2 complete - ready for Phase 3
- **Deferred to future:**
  - Estado_Ocupacion column for paused state marking

**Phase 3 (COMPLETE):** ✅ State Machine & Collaboration - All 4 plans complete
- ✅ Plan 03-01: State machine foundation (3 min)
  - Estado_Detalle column added at position 67
  - ARM state machine created (3 states, 3 transitions)
  - SOLD state machine with ARM dependency guard
  - python-statemachine==2.5.0 integrated
- ✅ Plan 03-02: StateService orchestration (3 min)
  - StateService integrates with OccupationService
  - Hydration logic syncs state machines with Sheets
  - EstadoDetalleBuilder for display formatting
- ✅ Plan 03-03: State machine callbacks (3.6 min)
  - ARM/SOLD callbacks update columns automatically
  - Estado_Detalle updates on every transition
  - TOMAR/PAUSAR/COMPLETAR trigger column writes
- ✅ Plan 03-04: History and collaboration tests (6 min)
  - GET /api/history/{tag_spool} endpoint with timeline
  - HistoryService aggregates Metadata events into sessions
  - Integration tests verify multi-worker collaboration
- **Status:** Phase 3 complete

**Phase 4 (IN PROGRESS):** 🔄 Real-Time Visibility - 1 of 3 plans complete
- ✅ Plan 04-01: SSE backend infrastructure (4 min)
  - GET /api/sse/stream endpoint with Redis pub/sub
  - RedisEventService publishes to spools:updates channel
  - EventSourceResponse with anti-buffering headers
  - 10 unit tests for event publisher
  - Graceful degradation when Redis unavailable
- 🔲 Plan 04-02: Frontend SSE client integration (pending)
- 🔲 Plan 04-03: Event integration with state machines (pending)
- **Status:** Phase 4 Wave 1 complete - Real-time push infrastructure ready

**Phase 4 Next:** Integrate RedisEventService with state machine callbacks to broadcast TOMAR/PAUSAR/COMPLETAR events

**Phase 5 (Metrología):** Special case workflow requires research - instant COMPLETAR without occupation, how to handle in state machine (separate state machine or conditional guards)?

**Phase 6 (Reparación):** Manufacturing rework best practices need validation - typical max cycles, supervisor escalation rules, quality department workflows.

## Session Continuity

Last session: 2026-01-27
Stopped at: Completed 04-01-PLAN.md (SSE backend infrastructure) ✅
Resume file: None

**Phase 4 IN PROGRESS:**
1. ✅ Plan 04-01 complete - SSE backend infrastructure (4 min)

**Phase 4 Plan 04-01 complete!**
- GET /api/sse/stream endpoint streams Redis events to clients
- RedisEventService publishes state changes to spools:updates channel
- EventSourceResponse with anti-buffering headers and timeouts
- 10 unit tests for event publisher with 100% coverage
- Graceful degradation when Redis unavailable (503 response)

**Commits:**
- cb7660a: chore(04-01): add sse-starlette dependency
- d6dad2a: feat(04-01): add Redis event publisher service
- 59a830a: feat(04-01): implement SSE streaming endpoint

**Phase 4 Plan 04-01 - All Success Criteria Met:**
- ✅ SSE endpoint returns EventSource stream with ping keepalive
- ✅ Redis pub/sub channel "spools:updates" created
- ✅ EventSourceResponse streams events with proper headers
- ✅ Connection cleanup on client disconnect
- ✅ No buffering issues (X-Accel-Buffering header set)

**Next steps:**
- Plan 04-02: Frontend SSE client integration (EventSource, auto-reconnect)
- Plan 04-03: Integrate RedisEventService with state machine callbacks
