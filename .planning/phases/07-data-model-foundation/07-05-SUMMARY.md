---
phase: 07-data-model-foundation
plan: 05
subsystem: infrastructure
tags: [fastapi, schema-validation, startup-hook, fail-fast]

# Dependency graph
requires:
  - phase: 07-04
    provides: Standalone v4.0 schema validation script
provides:
  - Startup validation hook preventing deployment with incomplete schema
  - Fail-fast error detection before accepting traffic
  - Clear error messages identifying missing columns/sheets
affects: [deployment, operations, 08-union-crud, 09-occupation-tracking]

# Tech tracking
tech-stack:
  added: []
  patterns: [startup-validation, fail-fast-deployment]

key-files:
  created: []
  modified: [backend/main.py]

key-decisions:
  - "D20: Integrate v4.0 validation into FastAPI startup event (after cache warming, before traffic)"

patterns-established:
  - "Startup validation: Run schema checks in @app.on_event('startup') to prevent deployment with incomplete schema"
  - "Clear error reporting: Structured validation results with per-sheet status for operational diagnostics"

# Metrics
duration: 8min
completed: 2026-02-02
---

# Phase 7 Plan 5: Integrate v4.0 Schema Validation Summary

**FastAPI startup validation prevents deployment if v4.0 schema incomplete, with clear error reporting for missing columns/sheets**

## Performance

- **Duration:** 8 min
- **Started:** 2026-02-02T[checkpoint start]
- **Completed:** 2026-02-02T[checkpoint approval]
- **Tasks:** 2 (1 auto, 1 human-verify checkpoint)
- **Files modified:** 1

## Accomplishments
- Integrated validate_v4_schema() into FastAPI startup event handler
- App refuses to start if any v4.0 columns missing in Operaciones, Uniones, or Metadata
- Clear error messages identify which sheets have validation failures
- Validation runs after cache pre-warming but before accepting traffic (fail-fast pattern)

## Task Commits

Each task was committed atomically:

1. **Task 1: Integrate validation into FastAPI startup** - `47caea6` (feat)

**Plan metadata:** (pending completion)

## Files Created/Modified
- `backend/main.py` - Added v4.0 schema validation to startup event handler after existing v3.0 validation

## Decisions Made

**D20: Integrate v4.0 validation into FastAPI startup event (after cache warming, before traffic)**
- Rationale: Fail-fast deployment prevents runtime errors from incomplete schema
- Placement: After cache pre-warming, before accepting traffic
- Error handling: Raise RuntimeError with clear message listing failed sheets
- Backward compatibility: Kept v3.0 validation for dual-mode operation during migration

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None - integration straightforward, validation script designed for dual-mode use (standalone + importable).

## Human Verification Results

**Verification completed successfully:**
- Standalone validation script correctly detects missing v4.0 columns (Operaciones: 68-72, Uniones: 18 cols, Metadata: N_UNION)
- FastAPI startup validation blocks server start with clear error messages
- Error messages identify exactly which sheets and columns are missing
- System behaves as expected (will pass after migration scripts 07-01 and 07-02 run)

**Expected behavior confirmed:**
- Current state: Validation fails (v4.0 columns not yet added)
- Error message format: "v4.0 schema validation failed for: ['Operaciones', 'Uniones', 'Metadata']"
- After migration: Server will start normally with "v4.0 schema validation passed" log message

## Next Phase Readiness

**Ready for Phase 8 (Union CRUD):**
- Schema validation infrastructure complete
- Startup hooks prevent deployment without required columns
- Clear error reporting enables rapid diagnosis of schema issues

**Blockers:**
- Migration scripts (07-01, 07-02) must execute before v4.0 code can deploy
- Uniones sheet must be pre-populated by Engineering before system operational

**Phase 7 Status:**
- 5 of 5 plans complete (Data Model Foundation phase complete)
- Ready to proceed to Phase 8 (Union CRUD Operations)

---
*Phase: 07-data-model-foundation*
*Completed: 2026-02-02*
