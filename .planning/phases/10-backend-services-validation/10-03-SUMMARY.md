---
phase: 10-backend-services-validation
plan: 03
subsystem: validation
tags: [arm-prerequisite, sold-validation, union-types, business-rules, v4.0]

# Dependency graph
requires:
  - phase: 10-01
    provides: UnionService with batch operations
  - phase: 10-02
    provides: OccupationServiceV4 with INICIAR/FINALIZAR
provides:
  - ARM-before-SOLD validation at INICIAR time
  - SOLD completion logic with union type filtering
  - ArmPrerequisiteError exception with 403 response
  - SOLD disponibles filtered to ARM-completed unions only
  - Mixed union type handling (FW excluded from SOLD)
affects: [10-04, 10-05, frontend-v4, union-workflows]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Early validation at INICIAR to fail fast"
    - "Union type filtering for SOLD_REQUIRED_TYPES"
    - "Dependency injection of ValidationService"
    - "403 Forbidden for business rule violations"

key-files:
  created:
    - tests/unit/services/test_validation_service_v4.py
  modified:
    - backend/exceptions.py
    - backend/services/validation_service.py
    - backend/services/occupation_service.py

key-decisions:
  - "Validate ARM prerequisite at INICIAR (not FINALIZAR) to fail early"
  - "Filter SOLD disponibles by union type (exclude FW ARM-only unions)"
  - "Import SOLD_REQUIRED_TYPES constant instead of duplicating"
  - "Return 403 Forbidden for ARM prerequisite violation"
  - "Count only SOLD_REQUIRED_TYPES in _determine_action"

patterns-established:
  - "ValidationService receives union_repository via dependency injection"
  - "OccupationService receives validation_service via dependency injection"
  - "Business rule validation happens before lock acquisition"
  - "Union type filtering in finalizar_spool before action determination"

# Metrics
duration: 6min
completed: 2026-02-02
---

# Phase 10 Plan 03: ARM-before-SOLD Validation Summary

**ARM prerequisite validation with union type filtering enforces SOLD-after-ARM business rule at INICIAR time with 403 error before lock acquisition**

## Performance

- **Duration:** 6 min
- **Started:** 2026-02-02T13:36:19Z
- **Completed:** 2026-02-02T13:42:16Z
- **Tasks:** 6
- **Files modified:** 4
- **Tests:** 13 new unit tests (all passing)

## Accomplishments

- ARM-before-SOLD validation prevents INICIAR SOLD without ARM completion
- SOLD completion logic correctly handles mixed union types (FW exclusion)
- Fail-fast validation at INICIAR time (before lock acquisition)
- Comprehensive test coverage with 13 unit tests
- Clear 403 Forbidden error with business rule message

## Task Commits

Each task was committed atomically:

1. **Task 1: Add ArmPrerequisiteError exception** - `27365df` (feat)
2. **Task 2: Add validate_arm_prerequisite method** - `9381d89` (feat)
3. **Task 3: Integrate validation into iniciar_spool** - `6dfcb0e` (feat)
4. **Task 4: Verify SOLD disponibles filtering** - `a0173c5` (feat)
5. **Task 5: Add SOLD completion logic for union types** - `7854a22` (feat)
6. **Task 6: Add comprehensive unit tests** - `1acb2e6` (test)

## Files Created/Modified

- `backend/exceptions.py` - Added ArmPrerequisiteError with clear error message
- `backend/services/validation_service.py` - Added validate_arm_prerequisite() method
- `backend/services/occupation_service.py` - Integrated validation and union type filtering
- `tests/unit/services/test_validation_service_v4.py` - Created comprehensive test suite (13 tests)

## Decisions Made

**D61 (10-03):** Validate ARM prerequisite at INICIAR (not FINALIZAR) to fail early before lock acquisition
**D62 (10-03):** Filter SOLD disponibles by union type (exclude FW ARM-only unions) in finalizar_spool
**D63 (10-03):** Import SOLD_REQUIRED_TYPES constant from occupation_service to avoid duplication
**D64 (10-03):** Return 403 Forbidden for ARM prerequisite violation (business rule violation)
**D65 (10-03):** Count only SOLD_REQUIRED_TYPES unions in _determine_action for accurate completion logic

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

**AsyncMock setup:** Initial tests failed due to async method mocking. Resolved by using `AsyncMock` from `unittest.mock` for `acquire_lock`, `update_with_retry`, and `publish_spool_update` methods. All 13 tests now passing.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

**Ready for 10-04:**
- ARM validation complete and tested
- SOLD completion logic handles mixed union types correctly
- ValidationService available for additional business rules
- Exception hierarchy supports 403 responses

**Blockers:** None

**Integration points:**
- Router must map ArmPrerequisiteError to 403 HTTP response
- Frontend should display clear error message when SOLD blocked
- UnionRepository get_disponibles_sold_by_ot already filters correctly

---
*Phase: 10-backend-services-validation*
*Completed: 2026-02-02*
