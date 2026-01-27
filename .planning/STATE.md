# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-01-26)

**Core value:** Real-time visibility of spool occupation - See EN VIVO who is working on which spool
**Current focus:** Phase 2 - Core Location Tracking

## Current Position

Phase: 3 of 6 (State Machine & Collaboration) 🚧 IN PROGRESS
Plan: 1 of 4 (03-01-PLAN.md) ✓ State machine foundation complete
Status: Estado_Detalle column added + ARM/SOLD state machines created
Last activity: 2026-01-27 — Completed 03-01: State machine foundation with guards

Progress: [████████████░░] 67% Phase 3 - 1/4 plans complete (State machine foundation done)

## Performance Metrics

**Velocity:**
- Total plans completed: 16
- Average duration: 4.5 minutes
- Total execution time: 1.24 hours

**By Phase:**

| Phase | Plans | Total | Avg/Plan |
|-------|-------|-------|----------|
| 01    | 9/9 ✅ | 51 min | 5.7 min    |
| 02    | 6/6 ✅  | 22 min  | 3.7 min    |
| 03    | 1/4 🚧 | 3 min  | 3.0 min    |

**Recent Trend:**
- Last 3 plans: 02-05-GAP (1 min), 02-06-GAP (2.6 min), 03-01 (3 min)
- Trend: Phase 3 starting strong - 3 min for foundation (faster than Phase 1/2 averages)

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

**Phase 3 (IN PROGRESS):** 🚧 State Machine & Collaboration - 1/4 plans complete
- ✅ Plan 03-01: State machine foundation (3 min)
  - Estado_Detalle column added at position 67
  - ARM state machine created (3 states, 3 transitions)
  - SOLD state machine with ARM dependency guard
  - python-statemachine==2.5.0 integrated
- **Next:** Plan 03-02 - Add state machine callbacks for column updates
- **Status:** Foundation ready, no blockers

**Phase 4 (Metrología):** Special case workflow requires research - instant COMPLETAR without occupation, how to handle in state machine (separate state machine or conditional guards)?

**Phase 5 (Reparación):** Manufacturing rework best practices need validation - typical max cycles, supervisor escalation rules, quality department workflows.

## Session Continuity

Last session: 2026-01-27
Stopped at: Completed 03-01-PLAN.md (State machine foundation) ✅
Resume file: None

**Phase 3 progress:**
1. ✅ Plan 03-01 complete - State machine foundation with guards (3 min)

**Phase 3 Plan 03-01 complete!**
- Estado_Detalle column added at position 67 in production sheet
- ARM state machine created with 3 states (pendiente/en_progreso/completado)
- SOLD state machine created with ARM dependency guard
- BaseOperationStateMachine shared foundation
- python-statemachine==2.5.0 library integrated
- Guard + validator pattern for dependencies

**Commits:**
- 89cd263: feat(03-01): add Estado_Detalle column to Operaciones sheet
- ee60eb1: feat(03-01): create ARM and SOLD state machines with guards

**Next steps:**
- Plan 03-02: Add state machine callbacks for column updates (on_enter_*, after_transition)
- Plan 03-03: StateService orchestration with hydration logic
- Plan 03-04: Estado_Detalle builder and update logic
