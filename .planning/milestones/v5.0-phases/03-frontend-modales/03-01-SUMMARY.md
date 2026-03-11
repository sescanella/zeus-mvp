---
phase: 03-frontend-modales
plan: 01
subsystem: ui
tags: [react, typescript, modal, spool-state-machine, jest, jest-axe, tailwind]

# Dependency graph
requires:
  - phase: 02-frontend-componentes-core
    provides: SpoolTable with disabledSpools, SpoolFilterPanel with showSelectionControls, Modal with isTopOfStack
  - phase: 01-frontend-fundaciones
    provides: spool-state-machine (getValidOperations, getValidActions), types.ts (SpoolCardData)
provides:
  - AddSpoolModal: fetches spool list, shows tracked tags greyed-out (disabledSpools), fires onAdd(tag)
  - OperationModal: shows valid operations per spool state via getValidOperations(), routes MET to onSelectMet()
  - ActionModal: shows valid actions per occupation via getValidActions(), CANCELAR always fires onCancel()
affects: [04-frontend-integracion, SpoolCard click handler, modal stack orchestration]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - TDD with jest.mock for all child components + api modules; no import of real deps in tests
    - jest.useRealTimers() locally in axe tests (axe async internals conflict with fake timers); 10s timeout
    - Arrow-function jest.mock factories (no TypeScript type annotations inside factory — SWC limitation)
    - Operation routing: MET button calls onSelectMet() (different flow); all others call onSelectOperation()
    - CANCELAR routing: always calls onCancel() directly; never goes through onSelectAction() (MODAL-04)

key-files:
  created:
    - zeues-frontend/components/AddSpoolModal.tsx
    - zeues-frontend/components/OperationModal.tsx
    - zeues-frontend/components/ActionModal.tsx
    - zeues-frontend/__tests__/components/AddSpoolModal.test.tsx
    - zeues-frontend/__tests__/components/OperationModal.test.tsx
    - zeues-frontend/__tests__/components/ActionModal.test.tsx
  modified: []

key-decisions:
  - "Arrow-function jest.mock factories (no TypeScript type annotations) — SWC transformer rejects TS types in mock factories"
  - "MET operation routes to onSelectMet() not onSelectOperation() — MetrologiaModal uses a different flow than ARM/SOLD/REP"
  - "CANCELAR always calls onCancel() directly in ActionModal — no worker step needed (MODAL-04); applies to both libre and occupied spools"
  - "AddSpoolModal fetches via getSpoolsParaIniciar('ARM') — best available endpoint for full spool list (documented limitation)"

patterns-established:
  - "Modal mocking: jest.mock('@/components/Modal') renders children when isOpen=true, null otherwise — no portal issues in jsdom"
  - "State-machine mocking: jest.mock('@/lib/spool-state-machine') with mockReturnValue() in each test — full control over returned ops/actions"
  - "Fetch-state pattern: 'loading' | 'success' | 'error' tri-state with useCallback for retryable fetch"

requirements-completed: [MODAL-01, MODAL-02, MODAL-04, MODAL-08, UX-01, STATE-01, STATE-02]

# Metrics
duration: 4min
completed: 2026-03-11
---

# Phase 03 Plan 01: Frontend Modales — Presentational Modals Summary

**Three presentational modals (AddSpoolModal, OperationModal, ActionModal) with state-filtered button rendering, accessibility checks, and 32 unit tests covering all spool states and action callbacks**

## Performance

- **Duration:** ~4 min
- **Started:** 2026-03-11T00:10:02Z
- **Completed:** 2026-03-11T00:13:41Z
- **Tasks:** 2
- **Files modified:** 6 created

## Accomplishments

- AddSpoolModal wraps Modal with lazy spool fetch, alreadyTracked tags greyed-out via disabledSpools, and showSelectionControls=false on SpoolFilterPanel
- OperationModal calls getValidOperations(spool) and routes MET to separate onSelectMet() callback (different flow — MetrologiaModal)
- ActionModal calls getValidActions(spool) and always routes CANCELAR to onCancel() directly without worker step (MODAL-04)
- All 32 unit tests pass (12 AddSpoolModal + 12 OperationModal + 8 ActionModal) including axe accessibility checks for all three modals
- tsc --noEmit passes; full 328-test suite passes with no regressions

## Task Commits

Each task was committed atomically:

1. **Task 1: AddSpoolModal component + tests** - `44242c1` (feat)
2. **Task 2: OperationModal + ActionModal components + tests** - `8a9e71e` (feat)

_Note: TDD tasks: tests written first (RED), component implemented (GREEN), no refactor needed._

## Files Created/Modified

- `zeues-frontend/components/AddSpoolModal.tsx` — Modal wrapping SpoolFilterPanel + SpoolTable; fetches via getSpoolsParaIniciar('ARM'); loading/error/success states
- `zeues-frontend/components/OperationModal.tsx` — Calls getValidOperations(spool); renders ARM/SOLD/MET/REP buttons with label map; MET routes to onSelectMet()
- `zeues-frontend/components/ActionModal.tsx` — Calls getValidActions(spool); CANCELAR styled red and routes to onCancel(); others to onSelectAction()
- `zeues-frontend/__tests__/components/AddSpoolModal.test.tsx` — 12 tests: rendering, disabled spools, callbacks, retry, axe
- `zeues-frontend/__tests__/components/OperationModal.test.tsx` — 12 tests: all spool states, operation callbacks, MET routing, axe
- `zeues-frontend/__tests__/components/ActionModal.test.tsx` — 8 tests: libre vs occupied actions, CANCELAR routing, axe

## Decisions Made

- **Arrow-function jest.mock factories** — SWC transformer (used by Next.js Jest) rejects TypeScript type annotations inside mock factory callbacks. All mock factories use untyped `props` parameter pattern.
- **MET routes to onSelectMet()** — Metrología has a different modal flow (MetrologiaModal, not ActionModal), so MET click cannot share the same callback.
- **CANCELAR always calls onCancel()** — Applies to both libre (INICIAR + CANCELAR) and occupied (FINALIZAR + PAUSAR + CANCELAR) states. No worker step needed for cancellation (MODAL-04).
- **AddSpoolModal uses getSpoolsParaIniciar('ARM')** — Best available endpoint for all spools; documented as limitation in plan (v5.0 may add dedicated endpoint later).

## Deviations from Plan

None — plan executed exactly as written.

## Issues Encountered

- SWC transformer rejects TypeScript type annotations inside `jest.mock()` factory callbacks. Fixed by removing type annotations from all mock factory parameters (use untyped `props`). This is a known Next.js/SWC limitation.

## User Setup Required

None — no external service configuration required.

## Next Phase Readiness

- AddSpoolModal, OperationModal, ActionModal are ready for integration into the modal stack (Plan 03-02)
- All three components export named exports matching the plan's artifacts spec
- Components are purely presentational — no API calls except AddSpoolModal's fetch on open
- Modal stack integration (WorkerModal, MetrologiaModal) is the next step (Phase 03 Plan 02)

---
*Phase: 03-frontend-modales*
*Completed: 2026-03-11*
