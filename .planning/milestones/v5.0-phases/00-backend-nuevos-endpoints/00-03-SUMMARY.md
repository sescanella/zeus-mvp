---
phase: 00-backend-nuevos-endpoints
plan: 03
subsystem: api
tags: [fastapi, pydantic, occupation, finalizar, worker-derivation, tdd]

# Dependency graph
requires:
  - phase: 00-backend-nuevos-endpoints
    provides: INICIAR/FINALIZAR endpoints from plans 01-02

provides:
  - action_override field on FinalizarRequest (PAUSAR/COMPLETAR buttons for v5.0 UI)
  - worker_nombre optional on IniciarRequest and FinalizarRequest with backend derivation
  - WorkerService injected into OccupationService via get_occupation_service_v4()
affects:
  - Frontend v5.0 (eliminates union selection screen, uses action_override directly)
  - All callers of FINALIZAR endpoint (backward compatible)

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "action_override Optional[Literal['PAUSAR', 'COMPLETAR']] pattern for operation override"
    - "Optional worker field with backend derivation via WorkerService.find_worker_by_id()"
    - "Bypass cancellation path with `not action_override` guard on zero-union check"

key-files:
  created:
    - tests/unit/services/test_finalizar_action_override.py
    - tests/unit/services/test_worker_derivation.py
  modified:
    - backend/models/occupation.py
    - backend/services/occupation_service.py
    - backend/core/dependency.py

key-decisions:
  - "action_override=PAUSAR takes an early return path (skips union writes + metrologia check)"
  - "action_override=COMPLETAR replaces selected_unions with all disponibles before existing COMPLETAR logic"
  - "Zero-union cancellation check guarded with `not action_override` to prevent COMPLETAR override from becoming CANCELADO"
  - "worker_nombre derivation raises SpoolNoEncontradoError if worker_id not found (reuses existing exception)"
  - "WorkerService injected as Optional to preserve backward compatibility with non-v4 service creation"

patterns-established:
  - "Override pattern: Optional[Literal] field + early return in service method for new UX flows"
  - "Backward-compat optional fields: Optional[str] = None with derivation guard `if not worker_nombre`"

requirements-completed: [API-03]

# Metrics
duration: 6min
completed: 2026-03-10
---

# Phase 0 Plan 03: action_override for FINALIZAR + Optional worker_nombre Summary

**FINALIZAR endpoint gains action_override (PAUSAR/COMPLETAR buttons) and optional worker_nombre derivation from worker_id, enabling the v5.0 single-page frontend to eliminate the union selection screen.**

## Performance

- **Duration:** 6 min
- **Started:** 2026-03-10T21:15:52Z
- **Completed:** 2026-03-10T21:21:51Z
- **Tasks:** 2
- **Files modified:** 5

## Accomplishments
- FinalizarRequest.action_override: Optional[Literal['PAUSAR', 'COMPLETAR']] — PAUSAR skips all union writes and clears occupation directly; COMPLETAR auto-selects all disponibles
- IniciarRequest.worker_nombre and FinalizarRequest.worker_nombre are now Optional — backend derives via WorkerService.find_worker_by_id() when not provided
- WorkerService injected into OccupationService.__init__() and wired in get_occupation_service_v4() factory
- 27 unit tests across both test files — all pass (15 for action_override, 12 for derivation)

## Task Commits

Each task was committed atomically:

1. **Task 1: action_override on FinalizarRequest** - `fb09914` (feat)
2. **Task 2: worker_nombre optional with derivation and DI wiring** - `5ccf221` (feat)

_Note: Both tasks followed TDD: RED (failing tests written first), then GREEN (implementation)._

## Files Created/Modified
- `backend/models/occupation.py` - Added action_override field to FinalizarRequest; made worker_nombre Optional in IniciarRequest and FinalizarRequest
- `backend/services/occupation_service.py` - action_override logic in finalizar_spool(), worker_nombre derivation in iniciar_spool() and finalizar_spool(), worker_service parameter in __init__()
- `backend/core/dependency.py` - Added worker_service: WorkerService = Depends(get_worker_service) to get_occupation_service_v4()
- `tests/unit/services/test_finalizar_action_override.py` - 15 tests for action_override model validation and service behavior
- `tests/unit/services/test_worker_derivation.py` - 12 tests for optional worker_nombre and derivation behavior

## Decisions Made
- action_override=PAUSAR uses an early return path (independent of union processing code) — avoids complex conditional threading through Steps 5-8
- Zero-union cancellation guard: changed `if len(selected_unions) == 0:` to `if len(selected_unions) == 0 and not action_override:` — prevents action_override=COMPLETAR from accidentally triggering cancellation when selected_unions is empty
- Worker derivation raises SpoolNoEncontradoError (not a new exception type) since "worker not found" is semantically equivalent to a missing resource
- WorkerService added as Optional parameter in OccupationService.__init__() to avoid breaking existing test fixtures and non-v4 factory calls

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

Pre-existing test failures in test_union_repository_batch.py, test_metadata_event_builder.py, test_union_repository_ot.py and test_validation_reparacion.py (45 total) were present before this plan. Verified via git stash. All are out-of-scope per deviation rules and logged here for reference.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness
- API-03 complete: FINALIZAR action_override ready for v5.0 frontend to use PAUSAR/COMPLETAR buttons directly
- worker_nombre optional in both INICIAR and FINALIZAR — v5.0 frontend only needs to pass worker_id
- Existing P5 workflow tests all still pass (backward compatibility confirmed)

---
*Phase: 00-backend-nuevos-endpoints*
*Completed: 2026-03-10*

## Self-Check: PASSED

- backend/models/occupation.py: FOUND
- backend/services/occupation_service.py: FOUND
- backend/core/dependency.py: FOUND
- tests/unit/services/test_finalizar_action_override.py: FOUND
- tests/unit/services/test_worker_derivation.py: FOUND
- .planning/phases/00-backend-nuevos-endpoints/00-03-SUMMARY.md: FOUND
- Commit fb09914: FOUND
- Commit 5ccf221: FOUND
