# Phase 5: Limpieza - Research

**Researched:** 2026-03-10
**Domain:** Next.js dead code removal, TypeScript cleanup, barrel exports, accessibility test migration
**Confidence:** HIGH

## Summary

Phase 5 is a pure deletion and cleanup phase — no new features, no new dependencies. The v5.0 single-page modal stack (assembled in Phases 1-4) fully replaces the old multi-page v4.0 flow. All target files have been confirmed to exist and have been audited for cross-references.

The critical dependency chain is: all dead pages import from `context.tsx` AND `layout.tsx` also imports `AppProvider` from `context.tsx`. This means `context.tsx` cannot be deleted outright — it must be replaced with a no-op shell or its `AppProvider` usage must be removed from `layout.tsx` first. This is the single most important pitfall in this phase.

The accessibility tests (`tests/accessibility.spec.ts`) are 100% tied to the old multi-page flow and must be fully rewritten to test the new single-page + modal architecture. All five test cases navigate through old page routes that will no longer exist.

**Primary recommendation:** Delete pages first (removing all consumers of dead context/components), then remove dead components, then clean `context.tsx` and `layout.tsx` together in the same commit, then update barrel and tests.

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- Delete all old route directories: operacion/, tipo-interaccion/, seleccionar-spool/, seleccionar-uniones/, confirmar/, exito/, resultado-metrologia/
- Delete FixedFooter.tsx, SpoolSelectionFooter.tsx, BatchLimitModal.tsx
- Clean old context.tsx (multi-page state management)
- Clean spool-selection-utils.ts
- Update components/index.ts to remove deleted component exports
- npm run build, tsc --noEmit, npm run lint must all pass with 0 warnings

### Claude's Discretion
- Order of deletion (pages first vs components first)
- Whether to batch deletions or do incremental commits
- How to handle any shared utilities used by both old and new code

### Deferred Ideas (OUT OF SCOPE)
None — this phase is self-contained cleanup with no future dependencies.
</user_constraints>

## Standard Stack

### Core
| Tool | Version | Purpose | Why Standard |
|------|---------|---------|--------------|
| Next.js App Router | 14.x | Route directories = pages; deleting the folder removes the route | Framework convention |
| TypeScript | 5.x | `tsc --noEmit` is the authoritative lint for dangling imports | Project standard |
| ESLint (Next.js config) | Latest | `npm run lint` catches `no-unused-vars`, `no-unreachable` | Project standard |
| Jest + jest-environment-jsdom | Per package.json | Unit/component tests in `__tests__/` | Project standard |
| Playwright + @axe-core/playwright | Per package.json | E2E accessibility tests in `tests/` | Project standard |

### No New Dependencies
This phase installs nothing. It only deletes files and updates existing ones.

**Verification commands:**
```bash
cd zeues-frontend
npx tsc --noEmit       # Catches dangling imports (primary gate)
npm run lint           # ESLint clean
npm run build          # Production build gate
npm test               # Jest unit tests
npx playwright test tests/accessibility.spec.ts  # After rewrite
```

## Architecture Patterns

### What Gets Deleted vs What Survives

**Dead (delete entirely):**
```
app/
├── operacion/             # Old P2: Operation selection
├── tipo-interaccion/      # Old P3: Action type selection
├── seleccionar-spool/     # Old P4: Spool selection table
├── seleccionar-uniones/   # Old P4b: Union selection (v4.0)
├── confirmar/             # Old P5: Confirmation screen
├── exito/                 # Old P6: Success screen
└── resultado-metrologia/  # Old: Metrologia result screen

components/
├── FixedFooter.tsx        # Only used by dead pages
├── SpoolSelectionFooter.tsx   # Only used by dead pages
└── BatchLimitModal.tsx    # Only used by dead pages (batch concept removed)

lib/
├── spool-selection-utils.ts  # Only used by seleccionar-spool/page.tsx

__tests__/
├── components/BatchLimitModal.test.tsx     # Tests dead component
├── components/SpoolSelectionFooter.test.tsx  # Tests dead component
└── lib/spool-selection-utils.test.ts         # Tests dead utility
```

**Survives (live, keep as-is):**
```
app/
├── page.tsx              # v5.0 single page (NEW — do not touch)
├── layout.tsx            # NEEDS EDIT: remove AppProvider import
├── dashboard/            # Not in scope (keep)
└── globals.css

components/
├── ActionModal.tsx       # v5.0 modal stack
├── AddSpoolModal.tsx     # v5.0 modal stack
├── BlueprintPageWrapper.tsx  # Still in use (SpoolCardList, modals)
├── ErrorMessage.tsx      # Still in use
├── Loading.tsx           # Still in use
├── MetrologiaModal.tsx   # v5.0 modal stack
├── Modal.tsx             # v5.0 base modal
├── NotificationToast.tsx # v5.0 feedback
├── OperationModal.tsx    # v5.0 modal stack
├── SpoolCard.tsx         # v5.0 card list
├── SpoolCardList.tsx     # v5.0 main view
├── SpoolFilterPanel.tsx  # Used inside AddSpoolModal
├── SpoolTable.tsx        # Used inside AddSpoolModal
├── UnionTable.tsx        # Keep (may be used, verify)
├── WorkerModal.tsx       # v5.0 modal stack
└── index.ts              # NEEDS EDIT: remove dead exports

lib/
├── SpoolListContext.tsx   # v5.0 state management (NEW)
├── api.ts                # Keep
├── context.tsx           # NEEDS EDIT: delete file + remove from layout.tsx
├── error-classifier.ts   # Keep
├── hooks/                # Keep
├── local-storage.ts      # Keep
├── operation-config.ts   # Keep (used by spool-state-machine.ts)
├── parse-estado-detalle.ts  # Keep
├── spool-state-machine.ts   # Keep
├── types.ts              # Keep
└── version.ts            # Keep
```

### Pattern 1: AppProvider Removal (Critical)

**What:** `layout.tsx` imports `AppProvider` from `context.tsx`. After all dead pages are deleted, `context.tsx` has no consumers except `layout.tsx`. The file must be deleted AND `layout.tsx` updated simultaneously.

**Current layout.tsx:**
```typescript
import { AppProvider } from '@/lib/context';
// ...
<AppProvider>
  {children}
</AppProvider>
```

**After cleanup (layout.tsx):**
```typescript
// No AppProvider import — SpoolListProvider is used at page.tsx level, not layout
export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="es">
      <body>
        {children}
      </body>
    </html>
  );
}
```

**Why:** `SpoolListProvider` is already rendered inside `page.tsx` itself (Plan 04-02 decision: "Two-component file pattern: Page (default export) wraps HomePage in SpoolListProvider"). The root layout does not need a global context provider anymore.

### Pattern 2: Barrel Export Cleanup

**Current components/index.ts (dead exports highlighted):**
```typescript
export { BlueprintPageWrapper } from './BlueprintPageWrapper';  // KEEP
export { Loading } from './Loading';                             // KEEP
export { ErrorMessage } from './ErrorMessage';                   // KEEP
export { FixedFooter } from './FixedFooter';                    // DELETE
export { SpoolFilterPanel } from './SpoolFilterPanel';           // KEEP
export { SpoolTable } from './SpoolTable';                       // KEEP
export { SpoolSelectionFooter } from './SpoolSelectionFooter';  // DELETE
export { BatchLimitModal } from './BatchLimitModal';             // DELETE
```

**After cleanup:**
```typescript
export { BlueprintPageWrapper } from './BlueprintPageWrapper';
export { Loading } from './Loading';
export { ErrorMessage } from './ErrorMessage';
export { SpoolFilterPanel } from './SpoolFilterPanel';
export { SpoolTable } from './SpoolTable';
```

**Note:** New v5.0 components (ActionModal, AddSpoolModal, SpoolCard, SpoolCardList, etc.) are imported directly by path in page.tsx — not via barrel. No new exports needed in index.ts.

### Pattern 3: Accessibility Test Rewrite

**Current `tests/accessibility.spec.ts` tests (all dead):**
- P1: Worker identification page (navigates to `/`)  — stale: old P1 was worker selection
- P2: Operation selection (clicks `MANUEL RODRÍGUEZ`) — stale: old multi-page flow
- P4: Spool selection Blueprint UI (clicks ARMADO/TOMAR) — stale: old route
- Keyboard navigation: Tab through P4 spool table — stale: old `seleccionar-spool/` route
- Keyboard navigation: Collapsible filter panel toggle — stale: old route
- Screen reader: Table rows announce correctly — stale: old route

**New architecture to test:**
- Main page renders SpoolCard list + "Anadir Spool" button
- "Anadir Spool" opens AddSpoolModal with SpoolTable + SpoolFilterPanel inside
- SpoolCard is the primary interactive element (role="button" on inner div)
- Modal stack: OperationModal → ActionModal → WorkerModal / MetrologiaModal
- NotificationToast: auto-dismiss feedback

**New test structure:**
```typescript
// tests/accessibility.spec.ts — v5.0 single-page modal stack

test('Main page has no a11y violations', async ({ page }) => {
  await page.goto('http://localhost:3000/');
  // axe scan on initial state
});

test('"Anadir Spool" button is keyboard accessible', async ({ page }) => {
  // Tab to button, Enter to open modal
});

test('AddSpoolModal has no a11y violations', async ({ page }) => {
  // Open modal, axe scan
});

test('SpoolCard keyboard navigation', async ({ page }) => {
  // Add spool, Tab to card, Enter to open OperationModal
});
```

**Note:** Tests require `localhost:3000` running with mocked backend or test data. The planner must decide if these are smoke tests only (no spool data loaded) vs tests that require the API.

### Anti-Patterns to Avoid

- **Deleting context.tsx without updating layout.tsx:** TypeScript build will break immediately because `layout.tsx` imports `AppProvider`.
- **Deleting barrel exports before deleting the component files:** `tsc --noEmit` will catch missing exports from deleted files before barrel is updated.
- **Leaving `__tests__/lib/spool-selection-utils.test.ts` alive:** After deleting `spool-selection-utils.ts`, this test file imports a non-existent module — build breaks.
- **Rewriting accessibility tests to test pages that no longer exist:** Current tests navigate through `/operacion`, `/tipo-interaccion` routes that will 404 after deletion.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Find all imports of a deleted file | Custom script | `npx tsc --noEmit` | TypeScript compiler is authoritative — flags all dangling imports |
| Verify no dead code remains | Manual search | `npm run lint` with `no-unused-vars` | ESLint catches unreferenced exports |
| Verify app still works after deletion | Manual testing | `npm run build` | Next.js build catches unresolved modules, missing pages |

**Key insight:** The TypeScript compiler + Next.js build pipeline already validates correctness after deletion. Run `tsc --noEmit` immediately after each deletion step — it will surface any remaining references instantly.

## Common Pitfalls

### Pitfall 1: AppProvider in layout.tsx (Critical)

**What goes wrong:** `context.tsx` deleted but `layout.tsx` still imports `AppProvider` → TypeScript error → build fails.
**Why it happens:** `layout.tsx` is not in the list of "pages to delete" — it's a live file that wraps the entire app. Easy to miss.
**How to avoid:** Treat context.tsx cleanup and layout.tsx update as a single atomic change. Delete context.tsx file AND remove the AppProvider import/usage from layout.tsx in the same step.
**Warning signs:** `tsc --noEmit` output includes: `Cannot find module '@/lib/context' or its corresponding type declarations`

### Pitfall 2: Dead Test Files Causing Build Failure

**What goes wrong:** Deleting `spool-selection-utils.ts` while `__tests__/lib/spool-selection-utils.test.ts` still exists → Jest fails importing deleted module.
**Why it happens:** Test files are not compiled by `tsc --noEmit` by default (they're in `__tests__/`) but Jest runs them and fails.
**How to avoid:** Delete each source file AND its corresponding test file together.
**Files affected:**
- `lib/spool-selection-utils.ts` + `__tests__/lib/spool-selection-utils.test.ts`
- `components/BatchLimitModal.tsx` + `__tests__/components/BatchLimitModal.test.tsx`
- `components/SpoolSelectionFooter.tsx` + `__tests__/components/SpoolSelectionFooter.test.tsx`

### Pitfall 3: Stale Accessibility Tests Pass Vacuously

**What goes wrong:** Old Playwright tests navigate to routes that return 404 — test may pass (no axe violations on empty page) or fail with navigation error.
**Why it happens:** Playwright doesn't throw if `page.goto` returns 404 by default unless you add explicit status checks.
**How to avoid:** Rewrite accessibility tests for the new architecture before running the Playwright suite.

### Pitfall 4: UnionTable.tsx May Have Live Consumers

**What goes wrong:** `UnionTable.tsx` is not in the delete list but was originally part of the old `seleccionar-uniones/` flow. If it has zero imports in live code, it's dead weight.
**Why it happens:** The CONTEXT.md lists specific targets — UnionTable.tsx was not listed. But it's worth verifying.
**How to avoid:** After deletions, run `npm run lint` — ESLint will flag unused imports but not unused exports. Cross-check with grep.

## Code Examples

### Verifying what references a file before deleting it
```bash
# Before deleting any file, check live references
grep -r "from.*FixedFooter\|import.*FixedFooter" zeues-frontend/app zeues-frontend/lib zeues-frontend/components
# Expected after pages are deleted: only components/index.ts (barrel) remains

grep -r "from.*context\|AppProvider\|useAppState" zeues-frontend/app zeues-frontend/lib
# Expected after pages deleted: only app/layout.tsx remains
```

### Running TypeScript check after each deletion
```bash
cd zeues-frontend
npx tsc --noEmit 2>&1 | head -20
# Must show 0 errors before moving to next step
```

### Updating components/index.ts (final state)
```typescript
// Source: direct audit of live consumers
export { BlueprintPageWrapper } from './BlueprintPageWrapper';
export { Loading } from './Loading';
export { ErrorMessage } from './ErrorMessage';
export { SpoolFilterPanel } from './SpoolFilterPanel';
export { SpoolTable } from './SpoolTable';
```

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | Jest (jest-environment-jsdom) + Playwright (@axe-core/playwright) |
| Config file | `zeues-frontend/jest.config.js` |
| Quick run command | `cd zeues-frontend && npm test -- --testPathPattern="__tests__"` |
| Full suite command | `cd zeues-frontend && npm test && npx playwright test tests/accessibility.spec.ts` |

### Phase Requirements → Test Map

This phase has no REQ IDs (cleanup phase). Validation is build-gate based:

| Behavior | Test Type | Automated Command | Status |
|----------|-----------|-------------------|--------|
| No dangling TypeScript imports after deletion | Build check | `npx tsc --noEmit` | Runs after each step |
| No ESLint violations | Lint | `npm run lint` | Runs after all deletions |
| Production build succeeds | Build | `npm run build` | Final gate |
| Dead component tests removed | Jest | `npm test` | No failures for deleted modules |
| Accessibility tests updated for v5.0 | Playwright | `npx playwright test tests/accessibility.spec.ts` | Requires rewrite (Wave 0 gap) |

### Sampling Rate
- **Per task commit:** `cd zeues-frontend && npx tsc --noEmit`
- **Per wave merge:** `cd zeues-frontend && npm run build && npm test`
- **Phase gate:** `npm run build && npm test && npm run lint` all green

### Wave 0 Gaps
- [ ] `tests/accessibility.spec.ts` — must be rewritten for v5.0 single-page modal architecture (current tests 100% tied to deleted pages)

## Sources

### Primary (HIGH confidence)
- Direct file system audit — all target files confirmed to exist at specified paths
- `grep` cross-reference analysis — all import relationships verified
- `zeues-frontend/app/layout.tsx` — AppProvider usage confirmed
- `zeues-frontend/__tests__/` — dead test files confirmed
- `zeues-frontend/tests/accessibility.spec.ts` — confirmed all 5 tests use old flow

### Secondary (MEDIUM confidence)
- Next.js App Router conventions — deleting a route directory removes the route
- Jest config (`jest.config.js`) — confirms `tests/` directory is excluded from Jest (Playwright only), `__tests__/` is included

## Metadata

**Confidence breakdown:**
- File inventory: HIGH — direct filesystem audit
- Dependency map: HIGH — grep cross-reference confirmed
- layout.tsx AppProvider trap: HIGH — confirmed in file
- Dead test files: HIGH — confirmed in __tests__/
- Accessibility test rewrite scope: HIGH — all 5 tests use deleted routes
- Order of operations: HIGH — TypeScript build validates each step

**Research date:** 2026-03-10
**Valid until:** Not time-sensitive — codebase is static until phase execution
