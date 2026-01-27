# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-01-26)

**Core value:** Real-time visibility of spool occupation - See EN VIVO who is working on which spool
**Current focus:** Phase 2 - Core Location Tracking

## Current Position

Phase: 2 of 6 (Core Location Tracking)
Plan: 1 of N (02-01-PLAN.md) ✓ COMPLETE
Status: Phase 2 started - Redis infrastructure deployed
Last activity: 2026-01-27 — Completed 02-01: Redis infrastructure for atomic spool locking

Progress: [██████████░░░░░░░░░░] 17% Phase 1 complete + Phase 2 started (1 plan)

## Performance Metrics

**Velocity:**
- Total plans completed: 10
- Average duration: 5.7 minutes
- Total execution time: 0.95 hours

**By Phase:**

| Phase | Plans | Total | Avg/Plan |
|-------|-------|-------|----------|
| 01    | 9/9 ✅ | 51 min | 6 min    |
| 02    | 1/N   | 3 min  | 3 min    |

**Recent Trend:**
- Last 5 plans: 01-06-gap (2 min), 01-07-gap (3.5 min), 01-08a-gap (5 min), 01-08b-gap (3.5 min), 02-01 (3 min)
- Trend: Infrastructure plans fast when following established patterns (3 min)

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

### Pending Todos

None yet.

### Blockers/Concerns

**Phase 1 (COMPLETE):** ✅ All 9 plans executed, all 5 truths verified
- ✅ Gap 1 CLOSED: Production backup created (1kWUjegxV00MOJver_9ljZqHxgJJBgErnH_J--N4TS9M) - 7-day rollback window active until 2026-02-02
- ✅ Gap 2 CLOSED: v3.0 columns added to production sheet (66 columns: 63 v2.1 + 3 v3.0)
- ✅ Gap 3a CLOSED: Migration coordinator executed - 6/6 verification checks, 39/39 tests passed
- ✅ Gap 3b CLOSED: Migration documentation complete (MIGRATION_COMPLETE.md, 01-VERIFICATION.md updated)
- **Status:** Phase 1 complete

**Phase 2 (IN PROGRESS):** Core Location Tracking - Building occupation tracking API endpoints
- ✅ Plan 02-01 COMPLETE: Redis infrastructure deployed (3 commits: b3f0cba, 3936944, 3d15394)
- **Next:** Plan 02-02 - TOMAR endpoint with atomic locking
- **Gaps:** FastAPI startup/shutdown events needed for Redis connection lifecycle

**Phase 4 (Metrología):** Special case workflow requires research - instant COMPLETAR without occupation, how to handle in state machine (separate state machine or conditional guards)?

**Phase 5 (Reparación):** Manufacturing rework best practices need validation - typical max cycles, supervisor escalation rules, quality department workflows.

## Session Continuity

Last session: 2026-01-27
Stopped at: Completed 02-01-PLAN.md (Redis Infrastructure) ✅
Resume file: None

**Phase 2 progress:**
1. ✅ Plan 02-01 complete - Redis infrastructure deployed
2. ⏳ Plan 02-02 next - TOMAR endpoint with atomic locking
3. ⏳ Plan 02-03 pending - PAUSAR/COMPLETAR endpoints
4. ⏳ Plan 02-04 pending - Batch operations

**Next steps:**
- Integrate Redis connection lifecycle with FastAPI (startup/shutdown events in main.py)
- Implement TOMAR endpoint using RedisLockService
- Add Redis health check endpoint for monitoring
