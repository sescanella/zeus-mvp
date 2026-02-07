# Phase 3: Frontend Refactoring - Execution Plan

**Created:** 2026-02-07
**Status:** READY FOR EXECUTION
**Depends on:** Phase 1 ✅, Phase 2 ✅
**Risk:** LOW-MEDIUM
**Estimated LOC Reduction:** ~600-800 LOC

---

## Agent Team Architecture

Phase 3 uses **4 parallel specialized agents** to maximize throughput. Each agent owns an independent work stream with no cross-dependencies in the first wave.

```
┌─────────────────────────────────────────────────────────────┐
│                    WAVE 1 (Parallel)                         │
│                                                              │
│  Agent A              Agent B             Agent C            │
│  Blueprint UI         Version &           Error Handling     │
│  Components           API Cleanup         & Utilities        │
│                                                              │
│  - BlueprintPage      - Remove version    - Consolidate      │
│    Wrapper              caching             error handling    │
│  - BlueprintHeader    - Remove detect     - Remove unused    │
│  - PrimaryButton        VersionFromSpool    formatErrorForUI │
│                       - Clean unused      - Operation labels │
│                         imports             centralization   │
├─────────────────────────────────────────────────────────────┤
│                    WAVE 2 (Sequential)                       │
│                                                              │
│  Agent D                                                     │
│  Context API Simplification                                  │
│  (depends on Wave 1 cleanup)                                 │
│                                                              │
│  - Remove batchResults (use pulgadasCompletadas)             │
│  - Replace batchMode with derived check                      │
│  - Update confirmar/page.tsx references                      │
│  - Update seleccionar-spool/page.tsx references              │
└─────────────────────────────────────────────────────────────┘
```

---

## Wave 1: Parallel Agents (Independent Work)

### Agent A: Blueprint UI Component Extraction

**Goal:** Extract 3 shared components from duplicated patterns across 9 pages.
**Files created:** 3 new components in `components/`
**Files modified:** 9 page files
**Estimated:** -300 LOC net reduction
**Risk:** LOW (pure refactor, no logic changes)

#### Task A.1: Create `<BlueprintPageWrapper>`

**New file:** `zeues-frontend/components/BlueprintPageWrapper.tsx`

Extract the repeated background grid pattern found in all 9 pages:
```tsx
// Current pattern (duplicated 9 times):
<div
  className="min-h-screen bg-[#001F3F]"
  style={{
    backgroundImage: `
      linear-gradient(rgba(255,255,255,0.03) 1px, transparent 1px),
      linear-gradient(90deg, rgba(255,255,255,0.03) 1px, transparent 1px)
    `,
    backgroundSize: '50px 50px'
  }}
>
  {children}
</div>
```

**Component contract:**
```tsx
interface BlueprintPageWrapperProps {
  children: React.ReactNode;
}
```

**Pages to update (9):**
1. `app/page.tsx`
2. `app/operacion/page.tsx`
3. `app/tipo-interaccion/page.tsx`
4. `app/seleccionar-spool/page.tsx`
5. `app/seleccionar-uniones/page.tsx`
6. `app/confirmar/page.tsx`
7. `app/exito/page.tsx`
8. `app/resultado-metrologia/page.tsx`
9. `app/dashboard/page.tsx`

**Validation:** Read each page first to confirm the exact pattern, then replace with `<BlueprintPageWrapper>`.

#### Task A.2: Create `<BlueprintHeader>`

**New file:** `zeues-frontend/components/BlueprintHeader.tsx`

Extract the repeated header pattern (logo + operation icon + worker info):
```tsx
// Current pattern variations across pages:
<div className="sticky top-0 z-10 ...">
  <div className="flex justify-center pt-8 pb-6 ... border-b-4 border-white/30">
    <Image src="/logos/logo-grisclaro-F8F9FA.svg" alt="Kronos Mining" width={200} height={80} priority />
  </div>
  <div className="px-10 ... py-6 ... border-b-4 border-white/30">
    <div className="flex items-center justify-center gap-4 mb-4">
      <OperationIcon size={48} strokeWidth={3} className="text-zeues-orange" />
      <h2 className="text-3xl ... font-black text-white tracking-[0.25em] font-mono">
        {operationLabel}
      </h2>
    </div>
  </div>
</div>
```

**Component contract:**
```tsx
interface BlueprintHeaderProps {
  operationIcon?: LucideIcon;
  operationLabel?: string;
  showLogo?: boolean;      // default: true
  showWorkerInfo?: boolean; // default: false
  workerName?: string;
  subtitle?: string;
}
```

**IMPORTANT:** Read ALL 9 page headers before implementing. There are slight variations (P1 has no operation icon, dashboard has different layout). The component must accommodate these variations through props.

**Pages to update:** 7 pages (P2-P7 + dashboard; P1 has unique header)

#### Task A.3: Create `<PrimaryButton>`

**New file:** `zeues-frontend/components/PrimaryButton.tsx`

Extract the repeated orange CTA button pattern (~15 instances):
```tsx
// Current pattern:
<button
  onClick={handleAction}
  disabled={loading}
  className="w-full h-24 bg-transparent border-4 border-white
    flex items-center justify-center gap-4 cursor-pointer
    active:bg-zeues-orange active:border-zeues-orange
    transition-all duration-200 disabled:opacity-50 group
    focus:outline-none focus:ring-2 focus:ring-white focus:ring-inset"
>
  <Icon size={48} strokeWidth={3} className="text-white" />
  <span className="text-3xl font-black text-white font-mono tracking-[0.25em]">
    CONFIRMAR
  </span>
</button>
```

**Component contract:**
```tsx
interface PrimaryButtonProps {
  onClick: () => void;
  disabled?: boolean;
  icon?: LucideIcon;
  iconSize?: number;
  children: React.ReactNode;
  className?: string;      // allow override for specific pages
  'aria-label'?: string;   // WCAG compliance
}
```

**IMPORTANT:** Preserve ALL accessibility attributes (focus:ring, aria-label, onKeyDown). Check CLAUDE.md WCAG 2.1 AA requirements.

#### Task A.4: Update barrel export

**File:** `zeues-frontend/components/index.ts`

Add new components to barrel export.

#### Validation for Agent A:
```bash
cd zeues-frontend
npx tsc --noEmit   # Must pass
npm run lint        # Must pass
npm run build       # Must pass
```

---

### Agent B: Version Caching & API Cleanup

**Goal:** Remove unused version caching, deprecated wrapper functions, and unused imports.
**Files modified:** 5 files
**Estimated:** -80 LOC
**Risk:** LOW

#### Task B.1: Remove version caching functions from `lib/version.ts`

**File:** `zeues-frontend/lib/version.ts`

**Remove (lines 42-69):**
- `getVersionCacheKey()` - used only by caching functions
- `cacheSpoolVersion()` - unnecessary (detection is O(1) from `total_uniones`)
- `getCachedVersion()` - unnecessary

**Keep:**
- `SpoolMetrics` interface
- `isV4Spool()` function
- `detectSpoolVersion()` function

**Rationale:** Version detection is instant from `total_uniones` field. Single-user mode means no cross-tab sync needed.

#### Task B.2: Remove caching calls from `tipo-interaccion/page.tsx`

**File:** `zeues-frontend/app/tipo-interaccion/page.tsx`

**Current usage (lines 10, 42, 58):**
```typescript
import { cacheSpoolVersion, getCachedVersion, detectSpoolVersion } from '@/lib/version';
// line 42: const cached = getCachedVersion(state.selectedSpool);
// line 58: cacheSpoolVersion(state.selectedSpool, version);
```

**Change to:**
- Import only `detectSpoolVersion`
- Replace `getCachedVersion` check with direct `detectSpoolVersion` call
- Remove `cacheSpoolVersion` call

#### Task B.3: Remove `detectVersionFromSpool` wrapper from `lib/api.ts`

**File:** `zeues-frontend/lib/api.ts` (line 643)

**Current:**
```typescript
export function detectVersionFromSpool(spool: Spool): 'v3.0' | 'v4.0' {
  return detectSpoolVersion(spool);
}
```

**Action:** Remove this function. Update callers to import from `lib/version.ts` directly.

**Callers to update:**
- `components/SpoolTable.tsx:4,35` - change import from `@/lib/api` to `@/lib/version`

#### Task B.4: Clean unused imports from `lib/api.ts`

**File:** `zeues-frontend/lib/api.ts`

Check for and remove any `eslint-disable-next-line @typescript-eslint/no-unused-vars` comments with unused imports.

#### Validation for Agent B:
```bash
cd zeues-frontend
npx tsc --noEmit   # Must pass
npm run lint        # Must pass
npm run build       # Must pass
```

---

### Agent C: Error Handling & Utility Consolidation

**Goal:** Consolidate error handling patterns, remove unused utilities, centralize operation labels.
**Files modified:** 4-6 files
**Estimated:** -60 LOC
**Risk:** LOW

#### Task C.1: Verify `formatErrorForUI` is unused and confirm no removal needed

**File:** `zeues-frontend/lib/error-classifier.ts`

Grep confirms `formatErrorForUI` does NOT exist in current codebase (already removed in Phase 1). No action needed.

#### Task C.2: Centralize operation label mapping

**Current state:** `OPERATION_WORKFLOWS` in `lib/operation-config.ts` already has `label` field.

**But** `tipo-interaccion/page.tsx:140` still uses inline mapping:
```typescript
const operationLabel = state.selectedOperation === 'ARM' ? 'ARMADO' :
  state.selectedOperation === 'SOLD' ? 'SOLDADURA' :
  state.selectedOperation === 'METROLOGIA' ? 'METROLOGÍA' : 'REPARACIÓN';
```

**And** `lib/spool-selection-utils.ts:16` has its own `getOperationLabel()` function.

**Action:**
1. Verify if `getOperationLabel()` from `spool-selection-utils.ts` uses `OPERATION_WORKFLOWS`
2. If not, refactor it to delegate to `OPERATION_WORKFLOWS[op].label`
3. Replace the inline mapping in `tipo-interaccion/page.tsx` with `OPERATION_WORKFLOWS[op].label`
4. Replace inline mapping in `confirmar/page.tsx` (line 297) if applicable

#### Task C.3: Remove redundant version checks in spool selection

**File:** `zeues-frontend/app/seleccionar-spool/page.tsx`

Check for double-detection of spool version (detected once in list mapping, then re-detected when selecting). Use the already-computed `spool.version` field.

#### Task C.4: Remove `shouldRefresh` SSE artifact (if still present)

**File:** `zeues-frontend/app/seleccionar-spool/page.tsx`

Check for commented-out SSE code (`shouldRefresh` state, commented useEffect). Remove if found.

#### Validation for Agent C:
```bash
cd zeues-frontend
npx tsc --noEmit   # Must pass
npm run lint        # Must pass
npm run build       # Must pass
```

---

## Wave 2: Sequential Agent (Depends on Wave 1)

### Agent D: Context API Simplification

**Goal:** Remove redundant fields from AppState, simplify state management.
**Files modified:** 3-4 files
**Estimated:** -80 LOC
**Risk:** MEDIUM (state management affects all pages)
**Depends on:** Wave 1 completion (especially Agent B removing version caching)

#### Task D.1: Analyze `batchMode` usage

**Current usage:**
- `seleccionar-spool/page.tsx` sets `batchMode: true/false` (6 occurrences)
- `confirmar/page.tsx:55` reads: `const isBatchMode = state.batchMode && state.selectedSpools.length > 0`

**Analysis:** `batchMode` is redundant - it's always equivalent to `selectedSpools.length > 1`. However, `confirmar/page.tsx` uses it extensively for branching logic.

**Decision:** Replace `batchMode` with a derived check:
```typescript
// In confirmar/page.tsx, replace:
const isBatchMode = state.batchMode && state.selectedSpools.length > 0;
// With:
const isBatchMode = state.selectedSpools.length > 1;
```

**Action:**
1. Remove `batchMode` from `AppState` interface
2. Remove from `initialState`
3. Remove all `batchMode: true/false` setState calls in `seleccionar-spool/page.tsx`
4. Replace `state.batchMode` reads in `confirmar/page.tsx` with `state.selectedSpools.length > 1`

#### Task D.2: Analyze `batchResults` usage

**Current usage in `confirmar/page.tsx`:**
- Line 156: `setState({ batchResults: batchResponse })`
- Line 174: `setState({ batchResults: null })`
- Line 185: `setState({ batchResults: null })`
- Line 242: `setState({ batchResults: batchResponse })`
- Line 255: `setState({ batchResults: null })`

**Analysis:** `batchResults` is still ACTIVELY USED in confirmar/page.tsx for v3.0 batch operations (TOMAR/PAUSAR/COMPLETAR). This is NOT safe to remove yet.

**Decision: KEEP `batchResults` for now.** It's used in the v3.0 TOMAR/PAUSAR/COMPLETAR workflow which still exists. Removing it would break the confirmar page's batch result display.

**Note:** `batchResults` can be removed in a future phase when v3.0 spools are fully migrated to v4.0.

#### Task D.3: Remove `batchMode` field only

Based on analysis above:
- **REMOVE:** `batchMode` (derived from `selectedSpools.length > 1`)
- **KEEP:** `batchResults` (actively used in v3.0 batch workflow)

**AppState after simplification (12 fields → 11 fields):**
```typescript
interface AppState {
  allWorkers: Worker[];
  selectedWorker: Worker | null;
  selectedOperation: 'ARM' | 'SOLD' | 'METROLOGIA' | 'REPARACION' | null;
  selectedTipo: 'tomar' | 'pausar' | 'completar' | 'cancelar' | null;
  selectedSpool: string | null;
  selectedSpools: string[];
  // REMOVED: batchMode (derived from selectedSpools.length > 1)
  batchResults: { ... } | null;  // KEPT: actively used in v3.0 batch workflow
  accion: 'INICIAR' | 'FINALIZAR' | null;
  selectedUnions: string[];
  pulgadasCompletadas: number;
}
```

#### Task D.4: Update all references

**Files to update:**
1. `lib/context.tsx` - Remove `batchMode` from interface, initialState
2. `app/seleccionar-spool/page.tsx` - Remove all `batchMode: true/false` from setState calls
3. `app/confirmar/page.tsx` - Replace `state.batchMode` with `state.selectedSpools.length > 1`

#### Validation for Agent D:
```bash
cd zeues-frontend
npx tsc --noEmit   # Must pass (catches all broken references)
npm run lint        # Must pass
npm run build       # Must pass
```

---

## Execution Order

```
Time ──────────────────────────────────────────────────────►

Wave 1 (parallel):
  Agent A [Blueprint UI] ──────────────────────┐
  Agent B [Version/API]  ─────────────┐        │
  Agent C [Error/Utils]  ─────────────┤        │
                                      │        │
Wave 2 (after Wave 1):                ▼        ▼
  Agent D [Context API]  ──────── (starts) ─────────────┐
                                                         │
Validation:                                              ▼
  Final Build Verification ─────────────────────── (end)
```

---

## Final Validation Checklist

After ALL agents complete, run:

```bash
cd zeues-frontend

# 1. TypeScript compilation
npx tsc --noEmit
# Expected: 0 errors

# 2. ESLint
npm run lint
# Expected: 0 warnings, 0 errors

# 3. Production build
npm run build
# Expected: Build succeeds

# 4. Verify no broken imports
grep -r "from.*version.*cacheSpoolVersion\|from.*version.*getCachedVersion" app/ lib/ components/
# Expected: 0 matches

# 5. Verify batchMode removed
grep -r "batchMode" app/ lib/ components/
# Expected: 0 matches

# 6. Verify new components exist
ls -la components/BlueprintPageWrapper.tsx components/BlueprintHeader.tsx components/PrimaryButton.tsx
# Expected: 3 files exist
```

---

## Risk Mitigation

| Risk | Mitigation |
|------|-----------|
| BlueprintHeader variations break pages | Read ALL 9 pages before creating component; use optional props |
| batchResults removal breaks v3.0 flow | Kept batchResults (analysis showed active usage) |
| Version caching removal causes perf regression | Detection is O(1) from total_uniones - no regression possible |
| PrimaryButton missing WCAG attributes | Explicitly include focus:ring, aria-label, onKeyDown in component |

---

## Commit Strategy

One atomic commit per wave:

1. **Wave 1 commit:** `refactor: Phase 3 Wave 1 - Extract Blueprint UI, clean version caching, consolidate utilities`
2. **Wave 2 commit:** `refactor: Phase 3 Wave 2 - Simplify Context API (remove batchMode)`

---

## Summary

| Agent | Focus | LOC Reduction | Files Changed | Risk |
|-------|-------|---------------|---------------|------|
| A | Blueprint UI Components | -300 | 9 pages + 3 new | LOW |
| B | Version/API Cleanup | -80 | 5 files | LOW |
| C | Error/Utility Consolidation | -60 | 4-6 files | LOW |
| D | Context API Simplification | -30 | 3 files | MEDIUM |
| **Total** | | **~470-600** | **~20 files** | **LOW-MED** |

**Note:** Original estimate of -800 LOC was optimistic. After analysis, `batchResults` cannot be safely removed (still actively used), and some "duplicate" patterns have slight variations that limit extraction. Revised estimate: ~470-600 LOC.
