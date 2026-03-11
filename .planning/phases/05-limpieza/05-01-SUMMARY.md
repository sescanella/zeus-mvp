---
phase: 05-limpieza
plan: 01
subsystem: ui
tags: [nextjs, typescript, dead-code-removal, cleanup, tailwind]

# Dependency graph
requires:
  - phase: 04-frontend-integracion
    provides: v5.0 single-page modal stack that fully replaces all old multi-page flow routes
provides:
  - Clean frontend codebase with only v5.0 files; ~3000+ lines of dead v4.0 code removed
affects: []

# Tech tracking
tech-stack:
  added: []
  patterns:
    - SpoolListProvider lives inside page.tsx (not layout.tsx) — root layout is provider-free

key-files:
  created: []
  modified:
    - zeues-frontend/app/layout.tsx
    - zeues-frontend/components/index.ts

key-decisions:
  - "Deleted context.tsx and updated layout.tsx atomically — AppProvider removal done in single commit to prevent broken build state"
  - ".next cache cleared after page directory deletions to remove stale type declarations from old routes"
  - "UnionTable.tsx retained — no live consumers but not in scope for this plan (deferred)"

patterns-established:
  - "Pattern: SpoolListProvider scoped to page.tsx — root layout stays minimal (no global context providers)"

requirements-completed: []

# Metrics
duration: 10min
completed: 2026-03-11
---

# Phase 5 Plan 01: Limpieza — Dead Code Removal Summary

**Removed ~3100 lines of dead v4.0 multi-page flow code: 7 page directories, 3 dead components, context.tsx, spool-selection-utils.ts, 3 dead test files — production build, lint, and 301 Jest tests all green.**

## Performance

- **Duration:** 10 min
- **Started:** 2026-03-11T02:01:19Z
- **Completed:** 2026-03-11T02:11:00Z
- **Tasks:** 3
- **Files modified:** 17 deleted + 2 edited

## Accomplishments

- Deleted all 7 dead v4.0 route directories (operacion/, tipo-interaccion/, seleccionar-spool/, seleccionar-uniones/, confirmar/, exito/, resultado-metrologia/)
- Deleted 3 dead components (FixedFooter, SpoolSelectionFooter, BatchLimitModal), their 3 test files, context.tsx and spool-selection-utils.ts
- Cleaned layout.tsx (no AppProvider) and components/index.ts (no dead exports) — full pipeline green: tsc, build, lint, 18 Jest suites / 301 tests

## Task Commits

Each task was committed atomically:

1. **Task 1: Delete dead page directories** - `97dc908` (chore)
2. **Task 2: Delete dead components/tests/lib + update layout.tsx and barrel** - `822b697` (chore)
3. **Task 3: Final build verification and dead code audit** - no file changes (verification only)

## Files Created/Modified

**Deleted (17 files):**
- `zeues-frontend/app/operacion/page.tsx` — old P2 operation selection
- `zeues-frontend/app/tipo-interaccion/page.tsx` — old P3 action type selection
- `zeues-frontend/app/seleccionar-spool/page.tsx` — old P4 spool selection
- `zeues-frontend/app/seleccionar-uniones/page.tsx` — old P4b union selection
- `zeues-frontend/app/confirmar/page.tsx` — old P5 confirmation screen
- `zeues-frontend/app/exito/page.tsx` — old P6 success screen
- `zeues-frontend/app/resultado-metrologia/page.tsx` — old metrologia result screen
- `zeues-frontend/components/FixedFooter.tsx` — replaced by modal-based actions
- `zeues-frontend/components/SpoolSelectionFooter.tsx` — replaced by SpoolCardList + modals
- `zeues-frontend/components/BatchLimitModal.tsx` — batch concept removed in v5.0
- `zeues-frontend/__tests__/components/BatchLimitModal.test.tsx` — tests dead component
- `zeues-frontend/__tests__/components/SpoolSelectionFooter.test.tsx` — tests dead component
- `zeues-frontend/__tests__/lib/spool-selection-utils.test.ts` — tests dead utility
- `zeues-frontend/lib/context.tsx` — replaced by SpoolListContext in page.tsx
- `zeues-frontend/lib/spool-selection-utils.ts` — logic moved to spool-state-machine.ts

**Modified (2 files):**
- `zeues-frontend/app/layout.tsx` — removed AppProvider import and wrapper; children render directly
- `zeues-frontend/components/index.ts` — removed FixedFooter, SpoolSelectionFooter, BatchLimitModal exports; only 5 live component exports remain

## Decisions Made

- Cleared `.next/` cache after Task 1 deletions — stale type declarations in `.next/types/app/` were causing false TypeScript errors referencing the deleted route pages.
- `context.tsx` deletion and `layout.tsx` update treated as single atomic Task 2 commit — avoids intermediate broken build state (as warned in RESEARCH.md pitfall #1).
- UnionTable.tsx has no live consumers in app/, lib/, or components/ — confirmed via grep; retained as out-of-scope per CONTEXT.md.

## Deviations from Plan

None — plan executed exactly as written.

## Issues Encountered

- `.next/` build cache contained stale type declarations for deleted routes (`.next/types/app/confirmar/page.ts` etc.) — cleared with `rm -rf .next`. Not a code issue; standard Next.js cache behavior after route deletion.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- Codebase is clean: only v5.0 live files remain in frontend
- Dead code audit passed: no references to deleted modules in any live file
- UnionTable.tsx has zero consumers — candidate for future cleanup in a subsequent limpieza plan
- Full pipeline green: tsc + build + lint + 301 Jest tests passing

---
*Phase: 05-limpieza*
*Completed: 2026-03-11*
