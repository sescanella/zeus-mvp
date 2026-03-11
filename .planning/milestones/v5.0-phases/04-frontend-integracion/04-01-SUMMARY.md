---
phase: 04-frontend-integracion
plan: "01"
subsystem: frontend-state
tags: [context, react, useReducer, localStorage, tdd]
dependency_graph:
  requires:
    - "01-01: types.ts (SpoolCardData, EstadoTrabajo, OperacionActual)"
    - "01-01: local-storage.ts (loadTags, saveTags)"
    - "01-01: api.ts (getSpoolStatus, batchGetStatus)"
    - "01-02: spool-state-machine.ts (getValidOperations, getValidActions)"
  provides:
    - "SpoolListContext: SpoolListProvider + useSpoolList hook"
    - "Clean spool-state-machine.ts with no duplicate type definitions"
  affects:
    - "04-02: page.tsx wiring (SpoolListProvider wraps page)"
tech_stack:
  added: []
  patterns:
    - "useReducer with union action types (SET_SPOOLS/ADD_SPOOL/REMOVE_SPOOL/UPDATE_SPOOL)"
    - "useRef stable callback pattern for refreshAll (no polling stale closure)"
    - "On-mount hydration: loadTags -> batchGetStatus -> SET_SPOOLS"
    - "localStorage sync via useEffect on spools array"
    - "Re-export pattern for backward-compatible type relocation"
key_files:
  created:
    - zeues-frontend/lib/SpoolListContext.tsx
    - zeues-frontend/__tests__/lib/SpoolListContext.test.tsx
  modified:
    - zeues-frontend/lib/spool-state-machine.ts
decisions:
  - "refreshAll uses useRef (spoolsRef.current) to avoid stale closure — safe for 30s polling interval"
  - "addSpool duplicate guard in both spoolsRef.current check (early exit) AND reducer (double safety)"
  - "localStorage syncs via useEffect on spools array, not inside action handlers"
  - "Re-export type { SpoolCardData } from './types' in spool-state-machine.ts preserves OperationModal/ActionModal backward compatibility"
metrics:
  duration: "~3 minutes"
  completed_date: "2026-03-11"
  tasks_completed: 2
  tasks_total: 2
  files_created: 2
  files_modified: 1
  tests_added: 10
  tests_total: 338
---

# Phase 04 Plan 01: SpoolListContext + spool-state-machine type cleanup Summary

**One-liner:** SpoolListContext with useReducer + useRef stable polling pattern, localStorage sync on every state change, and backward-compatible type import cleanup in spool-state-machine.ts.

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 (RED) | SpoolListContext failing tests | 1bbb67b | `__tests__/lib/SpoolListContext.test.tsx` |
| 1 (GREEN) | SpoolListContext implementation | 7f15f9c | `lib/SpoolListContext.tsx` |
| 2 | Fix spool-state-machine.ts duplicate types | 8dd4852 | `lib/spool-state-machine.ts` |

## What Was Built

### SpoolListContext.tsx

State management backbone for the v5.0 single-page view. Provides:

- **`SpoolListProvider`** — React context provider wrapping the spool card list
- **`useSpoolList`** — hook exposing `spools`, `addSpool`, `removeSpool`, `refreshAll`, `refreshSingle`

Key implementation decisions:

1. **refreshAll uses `useRef` pattern**: `spoolsRef.current` is updated every render via `useEffect`, so `refreshAll` (wrapped in `useCallback([])`) always has fresh tag list without taking `spools` as a dependency. This is the critical pattern that makes it safe to use in a `setInterval` polling hook.

2. **Duplicate guard on addSpool**: Early exit via `spoolsRef.current.some(...)` before API call, plus reducer-level guard as double safety.

3. **localStorage sync via `useEffect`**: Whenever `state.spools` changes, `saveTags(spools.map(...))` is called. This covers adds, removes, and SET_SPOOLS (hydration).

### spool-state-machine.ts (cleanup)

Replaced local `EstadoTrabajo`, `OperacionActual`, and `SpoolCardData` type definitions with:
```typescript
import type { SpoolCardData } from './types';
export type { SpoolCardData } from './types';
```

The re-export preserves backward compatibility for:
- `zeues-frontend/components/OperationModal.tsx`
- `zeues-frontend/components/ActionModal.tsx`
- `zeues-frontend/__tests__/lib/spool-state-machine.test.ts`

## Tests

10 new tests in `SpoolListContext.test.tsx`:
- useSpoolList throws outside provider
- addSpool fetches + adds (API called once)
- addSpool rejects duplicate (no API call)
- removeSpool removes from list
- removeSpool syncs localStorage via saveTags
- refreshAll calls batchGetStatus with all tracked tags
- refreshAll no-op when list is empty
- refreshSingle updates one spool in place (other spools unchanged)
- Mount with persisted tags: loads + hydrates via batchGetStatus
- Mount with empty localStorage: empty state, no API call

All 338 tests pass. `tsc --noEmit` clean.

## Deviations from Plan

None — plan executed exactly as written.

## Self-Check

- [x] `zeues-frontend/lib/SpoolListContext.tsx` exists
- [x] `zeues-frontend/__tests__/lib/SpoolListContext.test.tsx` exists (329+ lines)
- [x] `zeues-frontend/lib/spool-state-machine.ts` has `import type { SpoolCardData } from './types'`
- [x] Commits 1bbb67b, 7f15f9c, 8dd4852 exist
- [x] All 338 tests pass
- [x] tsc --noEmit passes

## Self-Check: PASSED
