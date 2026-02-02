---
phase: 12-frontend-union-selection-ux
plan: 05
subsystem: frontend
tags: [next.js, typescript, react, api-integration, error-handling, session-storage]

# Dependency graph
requires:
  - phase: 12-04
    provides: P5 union selection page with checkboxes
  - phase: 12-01
    provides: TypeScript type definitions for v4.0 API
  - phase: 11-04
    provides: FINALIZAR endpoint with auto-determination
provides:
  - Complete P5 API integration with getDisponiblesUnions
  - Error handling for 409/403 with modals and auto-reload
  - Session storage for selection resilience
  - Updated confirmar page for FINALIZAR flow
affects: [12-06, 12-07, frontend-v4.0-workflows]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - Session storage for preserving UI state on error
    - 409 conflict auto-reload with countdown timer
    - Error modal with custom handlers per status code
    - Conditional v3.0/v4.0 logic in confirmar page

key-files:
  created: []
  modified:
    - zeues-frontend/app/seleccionar-uniones/page.tsx
    - zeues-frontend/app/confirmar/page.tsx

key-decisions:
  - "Fresh API call on P5 mount for accuracy over speed"
  - "Session storage preserves selection on error (unions_selection_{tag} format)"
  - "409 conflict triggers 2-second auto-reload to P5"
  - "403 ownership error shows clear message and redirects to spool selection"
  - "Clear session storage on successful FINALIZAR submission"
  - "Display pulgadas-diámetro with 1 decimal precision on confirmar"

patterns-established:
  - "Error handler pattern: handleApiError with modal state for v4.0 flows"
  - "Conditional flow: state.accion === 'FINALIZAR' for v4.0 vs tipo for v3.0"
  - "Session storage lifecycle: restore on mount, save on change, clear on success"

# Metrics
duration: 3.8min
completed: 2026-02-02
---

# Phase 12 Plan 05: API Integration & Error Handling for P5 Summary

**P5 connects to v4.0 API with 409 auto-reload, 403 ownership errors, and session storage resilience; confirmar page handles FINALIZAR with union metrics display**

## Performance

- **Duration:** 3m 46s
- **Started:** 2026-02-02T18:48:46Z
- **Completed:** 2026-02-02T18:52:32Z
- **Tasks:** 3 (2 commits - Task 3 integrated into Task 2)
- **Files modified:** 2

## Accomplishments
- P5 loads unions via GET /api/v4/uniones/{tag}/disponibles with loading state
- 409 conflict triggers modal with 2-second auto-reload countdown
- 403 ownership error shows clear message and redirects
- Session storage preserves selection on error for resilience
- Confirmar page calls finalizarSpool for v4.0 FINALIZAR flow
- Display selected unions count and pulgadas-diámetro on confirmation

## Task Commits

Each task was committed atomically:

1. **Task 1: Add API loading and error handling to P5** - `64afecd` (feat)
   - Load unions on mount via getDisponiblesUnions API
   - Sort unions by n_union ascending
   - Add loading bar during submission (Guardando...)
   - Add network error retry button
   - Session storage preserves selection on error
   - METROLOGIA operation redirects to home

2. **Task 2: Update confirmar page for FINALIZAR flow** - `9acdf43` (feat)
   - Import finalizarSpool from API
   - Add conditional logic for v4.0 vs v3.0 submission
   - Call finalizarSpool with selected_unions payload
   - Display selected unions count on confirmation (4xl font)
   - Add 409 conflict handling with auto-reload
   - Add 403 ownership error with clear message
   - Store pulgadas_completadas for success page
   - Clear session storage on successful submission
   - Error modal component with Modal wrapper

_Task 3 (error modal component) integrated into Task 2_

## Files Created/Modified
- `zeues-frontend/app/seleccionar-uniones/page.tsx` - API integration with loading states, session storage for selection persistence, network error retry button, METROLOGIA redirect guard
- `zeues-frontend/app/confirmar/page.tsx` - v4.0 FINALIZAR flow with finalizarSpool API call, error modal for 409/403 handling, union metrics display (count + pulgadas), countdown timer for auto-reload

## Decisions Made
- **Fresh API call on P5 mount:** Accuracy over speed - always load latest union state
- **Session storage for resilience:** Preserve selection on error (unions_selection_{tag} format)
- **409 auto-reload pattern:** 2-second countdown timer with visual feedback before navigating to P5
- **403 ownership error:** Clear message "No eres el dueño de este spool" + redirect to spool selection
- **Clear session storage on success:** Prevent stale selection data after FINALIZAR completes
- **1 decimal pulgadas precision:** Math.round(total * 10) / 10 for consistency with service layer
- **Error modal with null backdrop:** Force user to acknowledge error via button click

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

**1. Button variant type error**
- **Issue:** Used `variant="secondary"` which doesn't exist in Button component
- **Resolution:** Changed to `variant="cancel"` (gray button for retry action)
- **Verification:** TypeScript compilation passed

**2. ESLint unused variable**
- **Issue:** Catch block parameter `e` defined but never used
- **Resolution:** Removed parameter, used catch without binding
- **Verification:** ESLint passed with no warnings

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

**Ready for Phase 12-06 (P6 Confirmar Integration):**
- P5 API integration complete with comprehensive error handling
- Session storage provides resilience for user selections
- Confirmar page handles both v3.0 and v4.0 flows
- Error modals provide clear user feedback for 409/403 scenarios

**Ready for Phase 12-07 (INICIAR/FINALIZAR Endpoints):**
- Frontend prepared to call iniciarSpool and finalizarSpool endpoints
- Error handling infrastructure in place for v4.0 API responses

**No blockers** - all v4.0 union selection UX components integrated and tested

---
*Phase: 12-frontend-union-selection-ux*
*Completed: 2026-02-02*
