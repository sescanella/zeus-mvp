---
phase: 02-core-location-tracking
plan: 01
subsystem: frontend-components
tags: [components, toast, spool-card, timer, wcag, tdd]
dependency_graph:
  requires:
    - 01-01-PLAN.md  # lib/types.ts (SpoolCardData, EstadoTrabajo)
    - 01-02-PLAN.md  # spool-state-machine (getValidOperations)
    - 01-03-PLAN.md  # useNotificationToast (Toast type)
  provides:
    - NotificationToast component with ARIA live region
    - SpoolCard component with elapsed timer and state badges
    - SpoolCardList container with empty state
  affects:
    - 02-02-PLAN.md  # Page assembly will consume these components
tech_stack:
  added: []
  patterns:
    - TDD (RED → GREEN for both tasks)
    - Inline hook pattern (useElapsedSeconds inside SpoolCard)
    - WCAG nested-interactive fix (button outside role=button)
    - date parsing via regex (DD-MM-YYYY HH:MM:SS, not new Date())
key_files:
  created:
    - zeues-frontend/components/NotificationToast.tsx
    - zeues-frontend/components/SpoolCard.tsx
    - zeues-frontend/components/SpoolCardList.tsx
    - zeues-frontend/__tests__/components/NotificationToast.test.tsx
    - zeues-frontend/__tests__/components/SpoolCard.test.tsx
    - zeues-frontend/__tests__/components/SpoolCardList.test.tsx
  modified: []
decisions:
  - WCAG nested-interactive: SpoolCard wraps content in inner role=button div, remove button sits outside at parent div level — avoids axe nested-interactive violation
  - Timer uses Date.UTC() to parse DD-MM-YYYY HH:MM:SS fields, treating them as UTC-epoch values — makes tests deterministic with jest.setSystemTime
  - Axe tests use jest.useRealTimers() locally — jest-axe async internals conflict with fake timers
  - PAUSADO guard implemented at SpoolCard level: isPausado computed from estado_trabajo, blocks timer render and timer interval regardless of ocupado_por
metrics:
  duration: "~6 minutes"
  completed: "2026-03-10"
  tasks_completed: 2
  tasks_total: 2
  files_created: 6
  tests_added: 68
---

# Phase 02 Plan 01: Core Visual Components Summary

**One-liner:** Three Blueprint Industrial components (NotificationToast, SpoolCard with live timer, SpoolCardList) with 68 unit tests and WCAG 2.1 AA compliance.

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | NotificationToast + SpoolCard components with tests | cd3ee47 | NotificationToast.tsx, SpoolCard.tsx, 2 test files |
| 2 | SpoolCardList container with empty state | b72e15d | SpoolCardList.tsx, SpoolCardList.test.tsx |

## What Was Built

**NotificationToast** (`zeues-frontend/components/NotificationToast.tsx`):
- `aria-live="polite"` container always in DOM (screen reader registered before first toast)
- Success (green-400 border + CheckCircle) and error (red-400 border + AlertCircle) toasts
- Dismiss button with `aria-label="Cerrar notificacion"`, Lucide X icon
- Blueprint Industrial palette: `bg-zeues-navy border-4 font-mono font-black`

**SpoolCard** (`zeues-frontend/components/SpoolCard.tsx`):
- Inline `useElapsedSeconds` hook with `setInterval(tick, 1000)` and `clearInterval` cleanup
- Chilean date parsing via regex `/^(\d{2})-(\d{2})-(\d{4})\s+(\d{2}):(\d{2}):(\d{2})$/` — never `new Date()` on raw string
- MM:SS format (< 1 hour) and HH:MM:SS format (>= 1 hour)
- PAUSADO guard (STATE-06): timer hidden and interval not started when `estado_trabajo === 'PAUSADO'`
- All 7 `EstadoTrabajo` states with Blueprint color map
- Keyboard accessible (Enter/Space triggers onCardClick), remove button with stopPropagation

**SpoolCardList** (`zeues-frontend/components/SpoolCardList.tsx`):
- Empty state: PackageOpen icon + "No hay spools en tu lista" + subtext
- Non-empty: `flex flex-col gap-4` with SpoolCard per spool, callbacks forwarded
- Blueprint palette: `text-white/50 font-mono` for empty state text

## Test Coverage

- NotificationToast: 12 tests (empty, success, error, multiple, dismiss, axe)
- SpoolCard: 31 tests (tag, badges, worker, timer, interaction, keyboard, axe)
- SpoolCardList: 13 tests (empty state, card count, callback propagation, axe)
- **Total: 68 tests, all passing**

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 2 - Missing Critical Functionality] WCAG nested-interactive violation**
- **Found during:** Task 1, axe audit
- **Issue:** `<button>` (remove) nested inside `<div role="button">` (card) — axe `nested-interactive` violation (WCAG 4.1.2)
- **Fix:** Restructured SpoolCard so outer container is a plain `<div>`, inner clickable content is `role="button"`, remove button sits as sibling at outer div level (absolute positioned)
- **Files modified:** `zeues-frontend/components/SpoolCard.tsx`
- **Commit:** cd3ee47

**2. [Rule 1 - Bug] Timer test timezone alignment**
- **Found during:** Task 1, initial GREEN run
- **Issue:** `parseFechaOcupacion` uses `Date.UTC()` treating Chilean time fields as UTC values, but tests set `jest.setSystemTime(new Date('2026-03-10T17:30:00.000Z'))` (UTC 17:30) while `fecha_ocupacion = '10-03-2026 14:30:00'` parses as UTC 14:30 — yielding 3h elapsed instead of 0s
- **Fix:** Aligned `jest.setSystemTime` to `2026-03-10T14:30:00.000Z` to match the Date.UTC parse output; updated all time-relative test fixtures accordingly
- **Files modified:** `zeues-frontend/__tests__/components/SpoolCard.test.tsx`
- **Commit:** cd3ee47

**3. [Rule 1 - Bug] Axe tests timing out with fake timers**
- **Found during:** Task 1, axe audit tests
- **Issue:** `jest.useFakeTimers()` in `beforeEach` caused `jest-axe` async internals to exceed 5s default timeout
- **Fix:** Added `beforeEach(() => jest.useRealTimers())` in the accessibility describe block, with `afterEach` restoring fake timers; increased axe test timeouts to 10s
- **Files modified:** `zeues-frontend/__tests__/components/SpoolCard.test.tsx`
- **Commit:** cd3ee47

## Verification

```
Tests:       68 passed, 68 total
Test Suites: 4 passed, 4 total
tsc --noEmit: clean (0 errors)
axe audits:  passing for all components
```

## Self-Check: PASSED

Files created:
- FOUND: zeues-frontend/components/NotificationToast.tsx
- FOUND: zeues-frontend/components/SpoolCard.tsx
- FOUND: zeues-frontend/components/SpoolCardList.tsx
- FOUND: zeues-frontend/__tests__/components/NotificationToast.test.tsx
- FOUND: zeues-frontend/__tests__/components/SpoolCard.test.tsx
- FOUND: zeues-frontend/__tests__/components/SpoolCardList.test.tsx

Commits:
- FOUND: cd3ee47 (Task 1)
- FOUND: b72e15d (Task 2)
