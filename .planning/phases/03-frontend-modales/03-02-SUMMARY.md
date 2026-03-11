---
phase: 03-frontend-modales
plan: 02
subsystem: frontend-modales
tags: [modal, worker-selection, metrologia, api-routing, tdd, accessibility]
dependency_graph:
  requires:
    - "zeues-frontend/components/Modal.tsx"
    - "zeues-frontend/lib/api.ts"
    - "zeues-frontend/lib/operation-config.ts"
    - "zeues-frontend/lib/types.ts"
    - "zeues-frontend/lib/spool-state-machine.ts"
  provides:
    - "WorkerModal — role-filtered worker selection with full API routing"
    - "MetrologiaModal — two-step inspection result + worker selection flow"
  affects:
    - "zeues-frontend/components/index.ts (exports to add in Phase 4)"
tech_stack:
  added: []
  patterns:
    - "TDD red-green cycle per task"
    - "jest.mock('@/lib/api') for isolated unit tests"
    - "waitFor for async assertions"
    - "jest.useRealTimers() for axe tests (10s timeout)"
key_files:
  created:
    - "zeues-frontend/components/WorkerModal.tsx"
    - "zeues-frontend/components/MetrologiaModal.tsx"
    - "zeues-frontend/__tests__/components/WorkerModal.test.tsx"
    - "zeues-frontend/__tests__/components/MetrologiaModal.test.tsx"
  modified: []
decisions:
  - "WorkerModal maps Operation (ARM/SOLD/REP/MET) to OperationType for OPERATION_TO_ROLES lookup via toOperationType() helper"
  - "MetrologiaModal prefetches workers on open (not on step transition) to avoid delay between step 1 and step 2"
  - "finalizarSpool called without selected_unions — action_override only (MODAL-08 satisfied)"
  - "worker_nombre NOT sent in IniciarRequest — backend derives via WorkerService (per Plan 00-03 decision)"
  - "act() warnings on MetrologiaModal tests are benign — waitFor wraps all async assertions correctly"
metrics:
  duration: "3 minutes"
  completed: "2026-03-11"
  tasks_completed: 2
  tests_added: 33
  files_created: 4
---

# Phase 03 Plan 02: API-Calling Modals Summary

**One-liner:** WorkerModal + MetrologiaModal — role-filtered worker selection with full API routing and two-step metrologia inspection flow.

## Objective

Create the 2 terminal modals in the v5.0 single-page flow that execute backend operations: WorkerModal (routes to iniciarSpool/finalizarSpool/tomarReparacion/pausarReparacion/completarReparacion based on operation+action pair) and MetrologiaModal (two-step resultado then worker selection calling completarMetrologia).

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | WorkerModal component + tests | a814197 | WorkerModal.tsx, WorkerModal.test.tsx |
| 2 | MetrologiaModal component + tests | c75bcf5 | MetrologiaModal.tsx, MetrologiaModal.test.tsx |

## Requirements Satisfied

- **MODAL-03:** WorkerModal filters workers by OPERATION_TO_ROLES mapping (ARM→Armador+Ayudante, SOLD→Soldador+Ayudante, REP→Armador+Soldador)
- **MODAL-05:** MetrologiaModal shows APROBADA/RECHAZADA buttons first, then worker selection
- **MODAL-06:** Both modals show loading spinner during API call; onComplete fires on success
- **MODAL-07:** onComplete callbacks enable parent to trigger toast (wiring in Phase 4)
- **MODAL-08:** WorkerModal uses action_override (PAUSAR/COMPLETAR) instead of selected_unions

## Tests

- WorkerModal: 17 tests (fetching, filtering ARM/SOLD/REP, 6 API routing combos, loading/error/onComplete, axe)
- MetrologiaModal: 16 tests (step 1 UI, step 2 transitions, filtering, back button, APROBADO+RECHAZADO paths, loading/error/onComplete, axe)
- **Total: 33 new tests, all passing**
- Full suite: 319 tests passing (no regressions); pre-existing ActionModal.test.tsx failure unrelated to this plan

## Decisions Made

1. **toOperationType() helper:** Operation type ARM/SOLD/REP/MET mapped to OperationType for OPERATION_TO_ROLES lookup. Explicit switch ensures type safety.
2. **Prefetch on open:** MetrologiaModal fetches workers when `isOpen=true` (useEffect on isOpen), not when transitioning to step 2 — eliminates perceived delay between result selection and worker list display.
3. **No selected_unions:** finalizarSpool called with only action_override — satisfies MODAL-08, eliminates union selection from modal flow.
4. **worker_nombre omitted:** IniciarRequest does not include worker_nombre; backend derives it via WorkerService (established in Plan 00-03).
5. **act() warnings:** Non-blocking — arise from async state updates in tests that don't use waitFor at top level. Tests pass correctly; React Testing Library's waitFor handles batching.

## Deviations from Plan

None — plan executed exactly as written.

## Self-Check

- [x] WorkerModal.tsx created and exports WorkerModal
- [x] MetrologiaModal.tsx created and exports MetrologiaModal
- [x] WorkerModal.test.tsx — 17 tests passing
- [x] MetrologiaModal.test.tsx — 16 tests passing
- [x] tsc --noEmit passes (0 errors)
- [x] Commits a814197 and c75bcf5 exist

## Self-Check: PASSED
