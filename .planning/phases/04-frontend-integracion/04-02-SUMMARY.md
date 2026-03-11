---
phase: 04-frontend-integracion
plan: "02"
subsystem: frontend-page
tags: [page, modal-stack, polling, cancelar, tdd, integration]
dependency_graph:
  requires:
    - "04-01: SpoolListContext (SpoolListProvider + useSpoolList)"
    - "01-03: useModalStack, useNotificationToast"
    - "02-01: SpoolCardList, NotificationToast"
    - "03-01: AddSpoolModal, OperationModal, ActionModal, WorkerModal, MetrologiaModal"
    - "01-01: api.ts (finalizarSpool, cancelarReparacion)"
  provides:
    - "app/page.tsx: v5.0 single-page application entry point"
    - "Full modal chain: add-spool -> operation -> action -> worker -> complete"
    - "MetrologiaModal path with APROBADO/RECHAZADO branching"
    - "CANCELAR dual logic: libre vs occupied spools"
    - "30s polling with Page Visibility API + modal pause"
  affects:
    - "User-facing: complete E2E workflow now functional"
tech_stack:
  added: []
  patterns:
    - "Two-component file pattern: HomePage (inner) + Page (provider wrapper, default export)"
    - "useRef(refreshAll) stable callback for polling setInterval"
    - "parseWorkerIdFromOcupadoPor('MR(93)') -> 93 helper"
    - "Mutable let mockSpools pattern for SWC-compatible jest mocks"
    - "Stack length guard in polling interval: stack.length === 0"
key_files:
  created:
    - zeues-frontend/__tests__/app/page.test.tsx
  modified:
    - zeues-frontend/app/page.tsx
    - zeues-frontend/components/SpoolCard.tsx
decisions:
  - "Two-component file pattern: Page (default export) wraps HomePage in SpoolListProvider — keeps hooks usage clean inside provider boundary"
  - "useRef(refreshAll) stores stable reference for 30s polling interval — avoids stale closure without adding refreshAll to useEffect deps"
  - "mockSpools as mutable let variable in tests — SWC mock factory limitations prevent jest.fn().mockReturnValue() pattern"
  - "CANCELAR operacion falls back to selectedOperation when operacion_actual is null — covers edge case where spool card has no operacion_actual set"
metrics:
  duration: "~8 minutes"
  completed_date: "2026-03-11"
  tasks_completed: 1
  tasks_total: 1
  files_created: 1
  files_modified: 2
  tests_added: 15
  tests_total: 353
---

# Phase 04 Plan 02: page.tsx — v5.0 Single-Page Modal Orchestration Summary

**One-liner:** page.tsx rewritten as capstone integration: SpoolListContext + 5-modal stack + 30s polling + CANCELAR dual-backend logic with parseWorkerIdFromOcupadoPor.

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 (RED) | Failing tests for page.tsx | 037dd73 | `__tests__/app/page.test.tsx` |
| 1 (GREEN) | page.tsx implementation + SpoolCard fix | 79d9c9f | `app/page.tsx`, `components/SpoolCard.tsx` |

## What Was Built

### app/page.tsx

Complete rewrite of the application entry point from the old multi-page routing approach to a v5.0 single-page application.

**Architecture — two components in one file:**

1. `HomePage` (inner component) — uses all hooks and renders all modals and the spool card list
2. `Page` (default export) — wraps `HomePage` in `SpoolListProvider`

**State managed in HomePage:**
- `selectedSpool: SpoolCardData | null` — card currently being operated on
- `selectedOperation: Operation | null` — from OperationModal
- `selectedAction: Action | null` — from ActionModal

**Modal chain:**
- Add-spool button → `push('add-spool')` → AddSpoolModal
- Card click → `setSelectedSpool` + `push('operation')` → OperationModal
- Select ARM/SOLD/REP → `push('action')` → ActionModal
- Select INICIAR/FINALIZAR/PAUSAR → `push('worker')` → WorkerModal → `onComplete`
- Select MET → `push('metrologia')` → MetrologiaModal → `onComplete(resultado)`

**CANCELAR dual logic (handleCancel):**
- `ocupado_por === null`: `removeSpool()` only — no API call (STATE-03)
- `operacion_actual === 'REPARACION'`: `cancelarReparacion({ tag_spool, worker_id })`
- `operacion_actual === 'ARM' | 'SOLD'`: `finalizarSpool({ ..., selected_unions: [] })` — zero-union CANCELAR path
- Worker ID parsed via `parseWorkerIdFromOcupadoPor("MR(93)") -> 93`

**30s polling:**
- `setInterval(30_000)` in `useEffect`
- Condition: `document.visibilityState === 'visible' && modalStack.stack.length === 0`
- Uses `useRef(refreshAll)` to avoid stale closure in interval callback

### SpoolCard.tsx (bug fix, Rule 3 - Blocking)

Removed unused `handleRemoveKeyDown` function that caused ESLint error `@typescript-eslint/no-unused-vars`. Pre-existing lint error was blocking `npm run build` which is part of task done criteria.

## Tests

15 new tests in `__tests__/app/page.test.tsx`:

1. Renders "Anadir Spool" button and SpoolCardList
2. "Anadir Spool" button opens AddSpoolModal
3. AddSpoolModal.onAdd calls addSpool and closes modal
4. Card click opens OperationModal with correct spool
5. OperationModal.onSelectOperation opens ActionModal with operation
6. OperationModal.onSelectMet opens MetrologiaModal
7. ActionModal.onSelectAction opens WorkerModal with action
8. WorkerModal.onComplete clears modals, refreshes card, shows success toast
9. MetrologiaModal APROBADO removes spool from list and shows toast
10. MetrologiaModal RECHAZADO keeps spool (refreshSingle), shows toast
11. CANCELAR on libre spool (ocupado_por=null) — no API call
12. CANCELAR on occupied ARM spool calls finalizarSpool then removeSpool
13. CANCELAR on REPARACION spool calls cancelarReparacion then removeSpool
14. Polling calls refreshAll every 30s (fake timers)
15. alreadyTracked prop contains current spool tags

All 353 tests pass. `tsc --noEmit` clean. `npm run build` succeeds.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Pre-existing lint error in SpoolCard.tsx blocked npm run build**
- **Found during:** Task 1 verification (npm run build step)
- **Issue:** `handleRemoveKeyDown` defined but never attached to any element — pre-existing `@typescript-eslint/no-unused-vars` error
- **Fix:** Removed the unused `handleRemoveKeyDown` function (3 lines)
- **Files modified:** `zeues-frontend/components/SpoolCard.tsx`
- **Commit:** 79d9c9f

**2. [Rule 2 - Test adjustment] SWC mock factory limitation**
- **Found during:** Task 1 (RED -> GREEN transition, tests 12 and 13)
- **Issue:** `useSpoolList` mock via `jest.mock` factory returns plain function, not `jest.MockedFunction` — `mockReturnValue` not available
- **Fix:** Changed `mockSpools` from `const` to `let` so tests can mutate it before render. Added `mockSpools = [...]` reset in `beforeEach`.
- **Files modified:** `zeues-frontend/__tests__/app/page.test.tsx`
- **Commit:** 037dd73 (test was updated before GREEN commit)

## Self-Check

- [x] `zeues-frontend/app/page.tsx` exists and is > 120 lines
- [x] `zeues-frontend/__tests__/app/page.test.tsx` exists and is > 100 lines
- [x] Commits 037dd73 and 79d9c9f exist
- [x] 353 tests pass (338 previous + 15 new)
- [x] `tsc --noEmit` passes
- [x] `npm run build` passes

## Self-Check: PASSED
