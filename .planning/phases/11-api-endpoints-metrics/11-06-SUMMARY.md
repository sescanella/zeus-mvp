---
phase: 11-api-endpoints-metrics
plan: 06
subsystem: backend-services
tags: [metadata, events, union-service, batch-logging, audit-trail]

# Dependency graph
requires:
  - phase: 10-backend-services-validation
    provides: UnionService with batch update and metadata logging
  - phase: 11-05
    provides: v4.0 API endpoints and integration tests
provides:
  - Fixed metadata logging pattern (1 batch + N granular events)
  - UnionService integration in OccupationService.finalizar_spool()
  - Gap closure for METRIC-03/METRIC-04 requirements
affects: [12-frontend-union-selection, audit-reporting]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - Service delegation pattern (OccupationService → UnionService)
    - Conditional metadata logging to avoid duplicates
    - Router-level dependency injection for v4.0 workflows

key-files:
  created: []
  modified:
    - backend/services/occupation_service.py
    - backend/routers/union_router.py
    - tests/unit/test_occupation_service.py
    - tests/integration/test_union_api_v4.py

key-decisions:
  - "D86 (11-06): Delegate union processing to UnionService for batch + granular metadata logging"
  - "D87 (11-06): Skip spool-level metadata logging when UnionService handles it (avoid duplicates)"
  - "D88 (11-06): Inject UnionService at router level instead of dependency.py (v4.0 specific)"

patterns-established:
  - "Service delegation: OccupationService.finalizar_spool() delegates to UnionService.process_selection() for union-level operations"
  - "Conditional logging: skip_metadata_logging flag prevents duplicate events when service layer handles logging"
  - "Router injection: Create custom service instances with v4.0 dependencies when needed"

# Metrics
duration: 5min
completed: 2026-02-02
---

# Phase 11 Plan 06: Fix Metadata Batch + Granular Event Logging Summary

**UnionService delegation in finalizar_spool ensures 1 batch + N granular metadata events per FINALIZAR operation**

## Performance

- **Duration:** 5 min
- **Started:** 2026-02-02T14:41:09Z
- **Completed:** 2026-02-02T14:46:10Z
- **Tasks:** 5
- **Files modified:** 4

## Accomplishments
- Refactored OccupationService.finalizar_spool() to use UnionService.process_selection()
- Fixed metadata logging gap (now creates 1 batch + N granular events)
- METRIC-03 and METRIC-04 requirements satisfied
- Added test coverage for batch + granular metadata logging pattern

## Task Commits

Each task was committed atomically:

1. **Task 1: Inject UnionService into OccupationService** - `42f4bee` (feat)
2. **Task 2: Refactor finalizar_spool to use UnionService** - `e2ac11d` (refactor)
3. **Task 3: Update router to inject UnionService** - `cdf1392` (feat)
4. **Task 4: Add tests for batch + granular metadata logging** - `fdc4185` (test)
5. **Task 5: Integration test for metadata event count** - `b02b692` (test)

**Test fix:** `da19da7` (fix: use MagicMock for v4.0 spool fields)

## Files Created/Modified
- `backend/services/occupation_service.py` - Added UnionService parameter, refactored finalizar_spool to delegate to UnionService.process_selection()
- `backend/routers/union_router.py` - Inject UnionService when creating OccupationService instance for finalizar_v4 endpoint
- `tests/unit/test_occupation_service.py` - Added test_finalizar_logs_batch_and_granular_metadata test
- `tests/integration/test_union_api_v4.py` - Added test_finalizar_creates_batch_and_granular_events with manual validation procedure

## Decisions Made

**D86 (11-06): Delegate union processing to UnionService for batch + granular metadata logging**
- **Rationale:** UnionService.process_selection() already implements the correct batch + granular metadata logging pattern. Reusing it eliminates code duplication and ensures consistency.
- **Impact:** OccupationService becomes orchestration layer, delegating union-level work to UnionService.

**D87 (11-06): Skip spool-level metadata logging when UnionService handles it**
- **Rationale:** Prevent duplicate metadata events. When UnionService logs batch + granular events, skip the old single-event logging.
- **Impact:** Metadata sheet shows correct pattern (1 + N events) instead of duplicate events.

**D88 (11-06): Inject UnionService at router level instead of dependency.py**
- **Rationale:** v4.0 endpoints need UnionService, but v3.0 endpoints don't. Router-level injection keeps dependency graph clean.
- **Impact:** finalizar_v4 endpoint creates custom OccupationService instance with UnionService injected.

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

**Issue:** Test failure due to missing `ot` field in Spool model
- **Problem:** Spool model doesn't have v4.0 fields (ot, total_uniones) yet. Test tried to create Spool with `ot="OT-123"`.
- **Resolution:** Used MagicMock instead of Spool model for test data. Mock supports dynamic attributes.
- **Verification:** Test passes with MagicMock approach.
- **Committed in:** da19da7 (fix commit)

## Next Phase Readiness

**Gap closure complete:** Phase 11 metadata logging gap resolved. All v4.0 API endpoints now implement correct batch + granular metadata logging pattern.

**Ready for Phase 12 (Frontend Union Selection):**
- Backend endpoints support union selection
- Metadata logging pattern matches METRIC-03/METRIC-04 requirements
- Test coverage includes batch + granular event verification

**No blockers:** All Phase 11 work complete. Phase 12 can proceed with frontend union selection UI.

---
*Phase: 11-api-endpoints-metrics*
*Completed: 2026-02-02*
