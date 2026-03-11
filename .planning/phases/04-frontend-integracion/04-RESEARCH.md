# Phase 4: Frontend — Integración - Research

**Researched:** 2026-03-10
**Domain:** Next.js 14 App Router + React Context + localStorage + Polling
**Confidence:** HIGH

## Summary

Phase 4 assembles all components built in Phases 1-3 into a working single-page application. The research reveals that all building blocks are already in place: SpoolCard, SpoolCardList, AddSpoolModal, OperationModal, ActionModal, WorkerModal, MetrologiaModal, NotificationToast, useModalStack, useNotificationToast, localStorage utilities (local-storage.ts), and complete API functions (batchGetStatus, getSpoolStatus). The primary work of this phase is wiring these pieces together in a new SpoolListContext and a rewritten app/page.tsx.

The existing `app/page.tsx` is the old v4.0 multi-page flow (operation selector with routing) — it must be completely replaced. The new page is a single-page application with no routing. The old `AppProvider` context (`lib/context.tsx`) is oriented toward the multi-page flow and should NOT be used as the basis for SpoolListContext; a new dedicated context is needed.

The most complex integration challenge is the CANCELAR dual logic: CANCELAR on a libre spool is frontend-only (just call `removeSpool(tag)`), but CANCELAR on an occupied spool requires calling `finalizarSpool` with no selected_unions and no action_override to trigger the zero-union cancellation path in the backend.

**Primary recommendation:** Create SpoolListContext with useReducer (spools array + dispatch actions), wire the complete modal flow in page.tsx with a local `selectedSpool` state for the currently-active modal card, and implement polling with Page Visibility API pause.

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- SpoolListContext manages the list of active spool cards (CARD-03, CARD-06)
- localStorage stores only tag_spool array; full state refreshed from backend (D-02)
- No optimistic updates — spinner + wait for API response (D-09, UX-03)
- Single page, no routing — app/page.tsx is the entire app (D-01)
- "Añadir Spool" button opens AddSpoolModal (CARD-01)
- SpoolCardList renders all active cards (CARD-02, CARD-06)
- NotificationToast overlay for feedback (MODAL-07, UX-02)
- Card click → OperationModal → ActionModal → WorkerModal → API call → toast + refresh (MODAL-01 through MODAL-06)
- MET path: Card → OperationModal → MetrologiaModal → API → toast (MODAL-05)
- CANCELAR skips WorkerModal, calls onCancel directly (MODAL-04)
- All modals use useModalStack for push/pop management
- 30-second interval using batchGetStatus (D-03, CARD-03)
- Refreshes all cards currently in the list
- Uses POST /api/spools/batch-status (API-02)
- MET APROBADA removes spool from list automatically (CARD-04)
- MET RECHAZADA keeps spool for Reparación flow (CARD-05)
- Spool libre (no ocupado_por): remove from list only, no API call (STATE-03, D-06)
- Spool occupied: call backend reset + remove from list (STATE-04, D-06)

### Claude's Discretion
- SpoolListContext implementation details (useReducer vs useState)
- Polling hook implementation (setInterval vs custom hook)
- Animation approach for auto-remove
- Error retry strategy for failed API calls in modal flow
- Loading state management during API calls

### Deferred Ideas (OUT OF SCOPE)
None — this phase covers full integration scope.
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| CARD-01 | Botón "Añadir Spool" abre modal con SpoolTable + filtros | AddSpoolModal already built; page.tsx needs button + modal instance |
| CARD-02 | Cards muestran TAG, operación actual, acción, worker, tiempo | SpoolCard + SpoolCardList fully built; feed SpoolCardData[] from context |
| CARD-03 | Spools persisten en localStorage (solo tag_spool), estado refresca cada 30s | local-storage.ts + batchGetStatus exist; SpoolListContext wires them |
| CARD-04 | MET APROBADA remueve spool automáticamente | MetrologiaModal.onComplete receives resultado; context.removeSpool() when APROBADO |
| CARD-05 | MET RECHAZADA mantiene spool para Reparación | Context does NOT remove on RECHAZADO; spool stays in list |
| CARD-06 | Múltiples spools, operar individualmente | SpoolCardList maps cards; modal flow uses selectedSpool local state |
| MODAL-01 | Click en card → OperationModal | page.tsx: onCardClick sets selectedSpool + push('operation') |
| MODAL-02 | ARM/SOLD/REP → ActionModal | OperationModal.onSelectOperation: push('action'), store selectedOperation |
| MODAL-03 | INICIAR/FINALIZAR/PAUSAR → WorkerModal | ActionModal.onSelectAction: push('worker'), store selectedAction |
| MODAL-04 | CANCELAR no requiere worker — directo a cancelar handler | ActionModal.onCancel: triggers CANCELAR dual logic directly |
| MODAL-05 | MET → MetrologiaModal | OperationModal.onSelectMet: push('metrologia') |
| MODAL-06 | Al seleccionar worker/resultado MET, ejecuta API + vuelve a principal | WorkerModal.onComplete + MetrologiaModal.onComplete: clear() + refresh card |
| MODAL-07 | NotificationToast éxito/error | useNotificationToast.enqueue() after every API call outcome |
| MODAL-08 | Eliminamos selección de uniones — PAUSAR reemplaza completación parcial | WorkerModal already uses action_override; no union selection needed |
| STATE-01 | Operaciones válidas según estado del spool | getValidOperations() in spool-state-machine.ts already handles this |
| STATE-02 | Acciones válidas según ocupación | getValidActions() in spool-state-machine.ts already handles this |
| STATE-03 | CANCELAR libre = quitar del listado (frontend-only) | Check spool.ocupado_por === null in cancelar handler; call removeSpool() |
| STATE-04 | CANCELAR ocupado = reset backend + quitar del listado | Call finalizarSpool({tag, worker_id, operacion, selected_unions: []}) then removeSpool |
| STATE-05 | Timer solo cuando spool ocupado | SpoolCard.useElapsedSeconds already handles this |
| STATE-06 | PAUSADOS muestran badge estático sin timer | SpoolCard isPausado guard already handles this |
| UX-01 | Modal "Añadir Spool" muestra spools ya añadidos como deshabilitados | AddSpoolModal.alreadyTracked prop → SpoolTable.disabledSpools; pass context.spools.map(s=>s.tag_spool) |
| UX-02 | Toasts auto-dismiss 3-5 segundos | AUTO_DISMISS_MS=4000 in useNotificationToast — already correct |
| UX-03 | No optimistic updates — loading spinner + esperar API | WorkerModal already implements this pattern |
| UX-04 | Mantener paleta Blueprint Industrial + mobile-first | All existing components use zeues-navy/zeues-orange palette |
</phase_requirements>

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| React | 18.3.0 | Component rendering + hooks | Project baseline |
| Next.js | 14.2.0 | App Router framework | Project baseline |
| TypeScript | 5.4.0 | Type safety | Project requirement (no `any`) |
| Tailwind CSS | 3.4.0 | Styling | Project baseline |

### Project-Specific Infrastructure Already Built
| Module | File | Purpose |
|--------|------|---------|
| localStorage utils | `lib/local-storage.ts` | loadTags, saveTags, addTag, removeTag, clearTags |
| API functions | `lib/api.ts` | getSpoolStatus, batchGetStatus (both ready) |
| Type definitions | `lib/types.ts` | SpoolCardData, EstadoTrabajo, OperacionActual |
| State machine | `lib/spool-state-machine.ts` | getValidOperations, getValidActions |
| Modal stack hook | `hooks/useModalStack.ts` | push, pop, clear, isOpen — manages stack of ModalId |
| Toast hook | `hooks/useNotificationToast.ts` | enqueue, dismiss, toasts — 4s auto-dismiss |
| SpoolCard | `components/SpoolCard.tsx` | Individual card with timer, badges, remove button |
| SpoolCardList | `components/SpoolCardList.tsx` | Container with empty state |
| AddSpoolModal | `components/AddSpoolModal.tsx` | Spool search + filter + add |
| OperationModal | `components/OperationModal.tsx` | ARM/SOLD/MET/REP selection |
| ActionModal | `components/ActionModal.tsx` | INICIAR/FINALIZAR/PAUSAR/CANCELAR |
| WorkerModal | `components/WorkerModal.tsx` | Worker selection + API call (INICIAR/FINALIZAR/PAUSAR) |
| MetrologiaModal | `components/MetrologiaModal.tsx` | Resultado selection + worker + API call |
| NotificationToast | `components/NotificationToast.tsx` | Fixed-position toast overlay |

**Installation:** No new packages required. All dependencies exist.

## Architecture Patterns

### Recommended Project Structure

New files to create in this phase:
```
lib/
└── SpoolListContext.tsx   # NEW: SpoolListContext + SpoolListProvider

app/
└── page.tsx               # REWRITE: single-page app (replaces old multi-page selector)
```

### Pattern 1: SpoolListContext with useReducer

**What:** Context that manages an array of `SpoolCardData`, syncs tags to localStorage, and exposes addSpool, removeSpool, refreshAll, and setSpools actions.

**When to use:** Single source of truth for all card list operations. Any component needing to read or modify the spool list imports `useSpoolList()`.

**Recommended interface:**
```typescript
// lib/SpoolListContext.tsx
'use client';

type SpoolListAction =
  | { type: 'ADD_SPOOL'; payload: SpoolCardData }
  | { type: 'REMOVE_SPOOL'; tag: string }
  | { type: 'REFRESH_ALL'; spools: SpoolCardData[] };

interface SpoolListContextValue {
  spools: SpoolCardData[];
  addSpool: (tag: string) => Promise<void>;  // fetch status + add to list
  removeSpool: (tag: string) => void;        // remove from list + localStorage
  refreshAll: () => Promise<void>;           // batchGetStatus all tracked tags
}
```

**useReducer vs useState:** Use `useReducer` for the spools array — the reducer handles all mutations atomically (no stale closure issues when updating based on previous state).

**localStorage sync:** After every reducer dispatch that changes the tags list, call `saveTags(newState.map(s => s.tag_spool))`.

**Initialization:** On mount, call `loadTags()` → `batchGetStatus(tags)` → dispatch REFRESH_ALL. Handle empty tags gracefully (no API call needed).

### Pattern 2: page.tsx — Modal Coordination State

**What:** The page holds `selectedSpool` (the card being operated on) plus `selectedOperation` and `selectedAction` as local state to pass to the modal chain. The `useModalStack` controls visibility.

**Correct pattern for page.tsx:**
```typescript
// app/page.tsx
const { spools, addSpool, removeSpool, refreshAll } = useSpoolList();
const modalStack = useModalStack();
const { toasts, enqueue, dismiss } = useNotificationToast();

const [selectedSpool, setSelectedSpool] = useState<SpoolCardData | null>(null);
const [selectedOperation, setSelectedOperation] = useState<Operation | null>(null);
const [selectedAction, setSelectedAction] = useState<Action | null>(null);

// Card click handler
const handleCardClick = (spool: SpoolCardData) => {
  setSelectedSpool(spool);
  modalStack.push('operation');
};

// After every modal action completes:
const handleModalComplete = async () => {
  modalStack.clear();
  setSelectedSpool(null);
  setSelectedOperation(null);
  setSelectedAction(null);
  if (selectedSpool) {
    // Refresh single card status
    const fresh = await getSpoolStatus(selectedSpool.tag_spool);
    // Update in context (dispatch SET_ONE or refreshAll)
  }
};
```

### Pattern 3: Polling with Page Visibility API

**What:** 30-second interval that pauses when tab is not visible.

**Implementation using useEffect + setInterval:**
```typescript
// Inside page.tsx or a usePollSpools hook
useEffect(() => {
  if (spools.length === 0) return;  // no-op if list empty

  const runPoll = () => {
    if (document.visibilityState === 'visible') {
      refreshAll();
    }
  };

  const id = setInterval(runPoll, 30_000);
  document.addEventListener('visibilitychange', runPoll);

  return () => {
    clearInterval(id);
    document.removeEventListener('visibilitychange', runPoll);
  };
}, [spools.length, refreshAll]);  // re-register when list changes size
```

**Alternative:** Extract as `usePolling(refreshAll, 30_000, enabled)` custom hook for testability.

**Note:** `refreshAll` must be memoized with `useCallback` in SpoolListContext to avoid infinite re-registrations.

### Pattern 4: CANCELAR Dual Logic

**What:** CANCELAR behaves differently depending on whether the spool is occupied.

**Decision point** — the ActionModal already calls `onCancel()` directly for CANCELAR. The page.tsx `onCancel` handler must check `selectedSpool.ocupado_por`:

```typescript
const handleCancel = async () => {
  if (!selectedSpool) return;

  if (!selectedSpool.ocupado_por) {
    // STATE-03: frontend-only — just remove from list
    removeSpool(selectedSpool.tag_spool);
    modalStack.clear();
    enqueue(`Spool ${selectedSpool.tag_spool} quitado del listado`, 'success');
    return;
  }

  // STATE-04: occupied — call backend reset
  // Determine operation from spool state to pass to finalizarSpool
  const operacion = selectedSpool.operacion_actual as 'ARM' | 'SOLD';
  // NOTE: For occupied spools, we don't have worker_id in SpoolCardData.
  // PROBLEM: finalizarSpool requires worker_id — need a "CANCELAR as any worker" approach.
  // RESOLUTION: The backend CANCELAR path (zero unions, no action_override) clears Ocupado_Por
  // regardless of who calls it. Use worker_id=0 or derive from ocupado_por string.
  // Recommended: parse worker_id from ocupado_por "MR(93)" → 93.
};
```

**CANCELAR with occupied spool — worker_id derivation:**
The `SpoolCardData.ocupado_por` field contains the format `"MR(93)"`. Parse the ID from this string:
```typescript
function parseWorkerIdFromOcupadoPor(ocupadoPor: string): number | null {
  const match = ocupadoPor.match(/\((\d+)\)$/);
  return match ? parseInt(match[1], 10) : null;
}
```
Then call `finalizarSpool({ tag_spool, worker_id, operacion, selected_unions: [] })` which triggers the zero-union CANCELAR path in occupation_service.py.

**If operacion_actual is REPARACION:** use `cancelarReparacion({ tag_spool, worker_id })` instead.

### Pattern 5: Auto-Remove on MET APROBADA

**What:** After MetrologiaModal calls `onComplete('APROBADO')`, remove the spool from the list.

```typescript
// In page.tsx MetrologiaModal prop:
onComplete={(resultado) => {
  modalStack.clear();
  if (resultado === 'APROBADO' && selectedSpool) {
    removeSpool(selectedSpool.tag_spool);
    enqueue(`${selectedSpool.tag_spool} aprobado — retirado del listado`, 'success');
  } else {
    enqueue(`Metrología completada: RECHAZADA`, 'success');
    // Refresh card (stays in list)
    refreshSingleCard(selectedSpool!.tag_spool);
  }
  setSelectedSpool(null);
}}
```

**Animation:** Brief CSS fade-out (300ms) before DOM removal. Use `opacity-0 transition-opacity duration-300` with `setTimeout(removeSpool, 300)`.

### Pattern 6: isTopOfStack Prop for All Modals

All modals accept `isTopOfStack?: boolean`. Pass `modalStack.isOpen(modalId)` as this prop so ESC key only triggers on the top-most modal:

```typescript
<AddSpoolModal
  isOpen={modalStack.isOpen('add-spool')}
  isTopOfStack={modalStack.isOpen('add-spool')}
  ...
/>
```

### Anti-Patterns to Avoid

- **Using AppContext for SpoolListContext:** The existing `lib/context.tsx` (AppContext) is a v4.0 multi-page context with routing-specific state (selectedWorker, selectedOperation for navigation). Do NOT add SpoolListContext into AppContext. Create a separate context file.
- **Optimistic updates:** Never update card state before API responds. Always show spinner (WorkerModal already has apiLoading state), wait for API, then refresh.
- **Polling while modals are open:** Consider pausing poll while any modal is open to avoid state refreshing under an active operation.
- **Re-creating polling interval on every render:** `refreshAll` must be stable (useCallback with empty deps or stable dep array) or the polling effect will endlessly re-register.
- **SSR crash on localStorage:** The `loadTags()`/`saveTags()` functions already guard with `typeof window === 'undefined'` — use them directly, never call `localStorage` directly.
- **Duplicate spool add:** `addTag()` in local-storage.ts already deduplicates. In SpoolListContext, also guard with `spools.find(s => s.tag_spool === tag)` before fetching.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| localStorage persistence | Custom serialization | `lib/local-storage.ts` (loadTags, saveTags, addTag, removeTag) | SSR-safe, deduplication, type-safe |
| Toast notifications | Custom notification state | `hooks/useNotificationToast.ts` + `components/NotificationToast.tsx` | Already built with auto-dismiss, ARIA live region |
| Modal stack management | Nested boolean states | `hooks/useModalStack.ts` (push/pop/clear/isOpen) | Stack semantics, ESC key support |
| Spool status fetch | Custom fetch wrappers | `lib/api.ts` (getSpoolStatus, batchGetStatus) | Error handling, typed responses |
| State machine logic | Switch statements | `lib/spool-state-machine.ts` (getValidOperations, getValidActions) | Already tested, handles all cases |
| Spool cards | Custom card components | `components/SpoolCard.tsx` + `components/SpoolCardList.tsx` | Timer, ARIA, PAUSADO guard all built |
| All modals | New modal components | AddSpoolModal, OperationModal, ActionModal, WorkerModal, MetrologiaModal | Phase 3 deliverables — fully built and tested |

**Key insight:** Phase 4 is a wiring phase, not a building phase. Every individual component and utility already exists with tests. The only new code is SpoolListContext, polling hook, and the rewritten page.tsx.

## Common Pitfalls

### Pitfall 1: selectedSpool Stale State in Closures
**What goes wrong:** `handleCancel` and `handleModalComplete` capture `selectedSpool` at closure time. If spool data was refreshed by polling between modal open and action confirm, `selectedSpool` may be stale.
**Why it happens:** React state closures + async operations.
**How to avoid:** Pass `spool` props through the modal chain rather than relying on a single captured reference. Or use a `useRef(selectedSpool)` that stays current.
**Warning signs:** CANCELAR calls wrong worker_id because state was stale.

### Pitfall 2: useCallback Dependency Array for refreshAll
**What goes wrong:** If `refreshAll` in SpoolListContext is not memoized, it changes on every render, causing the polling `useEffect` to teardown and recreate the interval on every render cycle.
**Why it happens:** Functions defined inside a component/hook body are new references each render.
**How to avoid:** Wrap `refreshAll` in `useCallback(async () => { ... }, [])` in SpoolListContext. Use `useReducer` so the dispatch function is stable.
**Warning signs:** Console shows interval being cleared and reset every second.

### Pitfall 3: Multiple SpoolListProvider Instances
**What goes wrong:** Wrapping page.tsx in a SpoolListProvider when layout.tsx also wraps with AppProvider causes context confusion.
**Why it happens:** Forgetting that Next.js App Router layouts wrap pages.
**How to avoid:** Add SpoolListProvider to `app/layout.tsx` alongside AppProvider, OR define it locally in page.tsx. Prefer local in page.tsx since SpoolListContext is only needed on the main page.
**Warning signs:** useSpoolList() returns undefined despite Provider being present.

### Pitfall 4: TypeScript Errors from SpoolCardData in spool-state-machine.ts
**What goes wrong:** `lib/spool-state-machine.ts` defines its own local `SpoolCardData` interface (with a TODO comment to import from types.ts). Passing `SpoolCardData` from `lib/types.ts` to `getValidOperations()` may cause type errors due to duplicate interface definitions.
**Why it happens:** Phase 1 Plan 01-02 noted this as a temporary duplication (Plan 01-01 was supposed to consolidate). The TODO is still present.
**How to avoid:** Before wiring, check if the two SpoolCardData interfaces are structurally compatible (they are — same fields). TypeScript structural typing will accept them. But explicitly resolve the TODO: update spool-state-machine.ts to import from types.ts and remove the duplicate interface.
**Warning signs:** `npx tsc --noEmit` reports type mismatch between two SpoolCardData definitions.

### Pitfall 5: CANCELAR for REP Operation
**What goes wrong:** For REPARACION, the CANCELAR backend path is `cancelarReparacion()` not `finalizarSpool()`.
**Why it happens:** REP has its own router (`/api/cancelar-reparacion`) separate from v4 occupation endpoints.
**How to avoid:** In the CANCELAR dual logic handler, branch on `operacion_actual`:
  - `'ARM' | 'SOLD'` → `finalizarSpool({ selected_unions: [] })`
  - `'REPARACION'` → `cancelarReparacion({ tag_spool, worker_id })`
  - `null` → frontend-only remove (spool is libre)
**Warning signs:** 404 error when calling finalizarSpool for a REP spool.

### Pitfall 6: Polling Triggering Refresh During Active API Call
**What goes wrong:** Polling fires refreshAll() while WorkerModal is in the middle of an API call. The batch status refresh overwrites the card's state before the operation's post-API refresh can run.
**Why it happens:** setInterval fires regardless of modal state.
**How to avoid:** Add a `pollingPaused` flag (useRef) that gets set to `true` when a modal is open. Check it in refreshAll before calling batchGetStatus.
**Warning signs:** Card briefly shows intermediate state after successful operation.

### Pitfall 7: batchGetStatus with Empty Tags Array
**What goes wrong:** When the spool list is empty, `batchGetStatus([])` makes an unnecessary API call and may return an empty array or error.
**Why it happens:** Polling doesn't check if list is empty.
**How to avoid:** In `refreshAll`, guard: `if (tags.length === 0) return;`
**Warning signs:** Network tab shows POST /api/spools/batch-status with `{"tags":[]}` every 30s.

## Code Examples

### SpoolListContext Structure
```typescript
// Source: Derived from existing local-storage.ts, api.ts, types.ts patterns
'use client';

import { createContext, useContext, useReducer, useCallback, useEffect } from 'react';
import type { SpoolCardData } from '@/lib/types';
import { loadTags, saveTags } from '@/lib/local-storage';
import { batchGetStatus, getSpoolStatus } from '@/lib/api';

type SpoolListAction =
  | { type: 'SET_SPOOLS'; spools: SpoolCardData[] }
  | { type: 'ADD_SPOOL'; spool: SpoolCardData }
  | { type: 'REMOVE_SPOOL'; tag: string }
  | { type: 'UPDATE_SPOOL'; spool: SpoolCardData };

function spoolListReducer(state: SpoolCardData[], action: SpoolListAction): SpoolCardData[] {
  switch (action.type) {
    case 'SET_SPOOLS':
      return action.spools;
    case 'ADD_SPOOL':
      if (state.some((s) => s.tag_spool === action.spool.tag_spool)) return state;
      return [...state, action.spool];
    case 'REMOVE_SPOOL':
      return state.filter((s) => s.tag_spool !== action.tag);
    case 'UPDATE_SPOOL':
      return state.map((s) => s.tag_spool === action.spool.tag_spool ? action.spool : s);
    default:
      return state;
  }
}

interface SpoolListContextValue {
  spools: SpoolCardData[];
  addSpool: (tag: string) => Promise<void>;
  removeSpool: (tag: string) => void;
  refreshAll: () => Promise<void>;
  refreshSingle: (tag: string) => Promise<void>;
}

export const SpoolListContext = createContext<SpoolListContextValue | undefined>(undefined);

export function SpoolListProvider({ children }: { children: React.ReactNode }) {
  const [spools, dispatch] = useReducer(spoolListReducer, []);

  // Initialize from localStorage on mount
  useEffect(() => {
    const tags = loadTags();
    if (tags.length === 0) return;
    batchGetStatus(tags)
      .then((fresh) => dispatch({ type: 'SET_SPOOLS', spools: fresh }))
      .catch(() => {
        // localStorage tags still tracked even if backend unreachable
      });
  }, []);

  // Sync localStorage whenever spools array changes
  useEffect(() => {
    saveTags(spools.map((s) => s.tag_spool));
  }, [spools]);

  const addSpool = useCallback(async (tag: string) => {
    const status = await getSpoolStatus(tag);
    dispatch({ type: 'ADD_SPOOL', spool: status });
  }, []);

  const removeSpool = useCallback((tag: string) => {
    dispatch({ type: 'REMOVE_SPOOL', tag });
  }, []);

  const refreshAll = useCallback(async () => {
    const tags = spools.map((s) => s.tag_spool);  // closure — stable if spools is from reducer
    if (tags.length === 0) return;
    const fresh = await batchGetStatus(tags);
    dispatch({ type: 'SET_SPOOLS', spools: fresh });
  }, [spools]);  // depends on spools — see polling pitfall note

  const refreshSingle = useCallback(async (tag: string) => {
    const fresh = await getSpoolStatus(tag);
    dispatch({ type: 'UPDATE_SPOOL', spool: fresh });
  }, []);

  return (
    <SpoolListContext.Provider value={{ spools, addSpool, removeSpool, refreshAll, refreshSingle }}>
      {children}
    </SpoolListContext.Provider>
  );
}

export function useSpoolList(): SpoolListContextValue {
  const ctx = useContext(SpoolListContext);
  if (!ctx) throw new Error('useSpoolList must be used within SpoolListProvider');
  return ctx;
}
```

**NOTE on refreshAll dependency:** `refreshAll` depends on `spools` to get current tags. This means the polling `useEffect` that depends on `refreshAll` will re-register every time spools changes. To avoid this, use a `useRef` pattern:
```typescript
const spoolsRef = useRef(spools);
useEffect(() => { spoolsRef.current = spools; }, [spools]);
const refreshAll = useCallback(async () => {
  const tags = spoolsRef.current.map(s => s.tag_spool);
  if (tags.length === 0) return;
  const fresh = await batchGetStatus(tags);
  dispatch({ type: 'SET_SPOOLS', spools: fresh });
}, []);  // stable — reads from ref, not closure
```

### page.tsx Skeleton
```typescript
// Source: project patterns from existing modal/hook usage
'use client';

import { useState, useEffect, useRef } from 'react';
import { SpoolListProvider, useSpoolList } from '@/lib/SpoolListContext';
import { SpoolCardList } from '@/components/SpoolCardList';
import { AddSpoolModal } from '@/components/AddSpoolModal';
import { OperationModal } from '@/components/OperationModal';
import { ActionModal } from '@/components/ActionModal';
import { WorkerModal } from '@/components/WorkerModal';
import { MetrologiaModal } from '@/components/MetrologiaModal';
import { NotificationToast } from '@/components/NotificationToast';
import { useModalStack } from '@/hooks/useModalStack';
import { useNotificationToast } from '@/hooks/useNotificationToast';
import type { SpoolCardData } from '@/lib/types';
import type { Operation, Action } from '@/lib/spool-state-machine';

// Rendered inside SpoolListProvider wrapper
function HomePage() {
  const { spools, addSpool, removeSpool, refreshAll, refreshSingle } = useSpoolList();
  const modalStack = useModalStack();
  const { toasts, enqueue, dismiss } = useNotificationToast();

  const [selectedSpool, setSelectedSpool] = useState<SpoolCardData | null>(null);
  const [selectedOperation, setSelectedOperation] = useState<Operation | null>(null);
  const [selectedAction, setSelectedAction] = useState<Action | null>(null);

  // 30s polling with Page Visibility API pause
  const refreshAllRef = useRef(refreshAll);
  useEffect(() => { refreshAllRef.current = refreshAll; }, [refreshAll]);

  useEffect(() => {
    const poll = () => {
      if (document.visibilityState === 'visible' && modalStack.stack.length === 0) {
        refreshAllRef.current().catch(() => {});
      }
    };
    const id = setInterval(poll, 30_000);
    document.addEventListener('visibilitychange', poll);
    return () => { clearInterval(id); document.removeEventListener('visibilitychange', poll); };
  }, [modalStack.stack.length]);  // pause when modals open

  // ... handlers
}

export default function Page() {
  return (
    <SpoolListProvider>
      <HomePage />
    </SpoolListProvider>
  );
}
```

### CANCELAR Dual Logic Handler
```typescript
// Source: CONTEXT.md STATE-03, STATE-04 + backend occupation_service.py zero-union path
import { finalizarSpool, cancelarReparacion } from '@/lib/api';

function parseWorkerIdFromOcupadoPor(ocupadoPor: string): number | null {
  const match = ocupadoPor.match(/\((\d+)\)$/);
  return match ? parseInt(match[1], 10) : null;
}

const handleCancel = async () => {
  if (!selectedSpool) return;

  const { tag_spool, ocupado_por, operacion_actual } = selectedSpool;

  if (!ocupado_por) {
    // STATE-03: libre — frontend only
    removeSpool(tag_spool);
    modalStack.clear();
    setSelectedSpool(null);
    enqueue(`Spool ${tag_spool} quitado`, 'success');
    return;
  }

  // STATE-04: occupied — call backend
  const workerId = parseWorkerIdFromOcupadoPor(ocupado_por);
  if (!workerId) {
    enqueue('No se pudo determinar el trabajador actual', 'error');
    return;
  }

  try {
    if (operacion_actual === 'REPARACION') {
      await cancelarReparacion({ tag_spool, worker_id: workerId });
    } else if (operacion_actual === 'ARM' || operacion_actual === 'SOLD') {
      await finalizarSpool({
        tag_spool,
        worker_id: workerId,
        operacion: operacion_actual,
        // No selected_unions, no action_override → triggers CANCELAR path
      });
    }
    removeSpool(tag_spool);
    modalStack.clear();
    setSelectedSpool(null);
    enqueue(`Operación cancelada — spool ${tag_spool} liberado`, 'success');
  } catch (err) {
    const msg = err instanceof Error ? err.message : 'Error al cancelar';
    enqueue(msg, 'error');
  }
};
```

### Fixing the SpoolCardData Duplicate Type Issue
```typescript
// In lib/spool-state-machine.ts — replace local interface definition with import:
// BEFORE (current state):
// type EstadoTrabajo = ... (local alias)
// export interface SpoolCardData { ... }

// AFTER (fix for Phase 4):
import type { SpoolCardData, EstadoTrabajo, OperacionActual } from './types';
// Remove local type aliases and SpoolCardData interface
// Add Operation and Action type exports (these are unique to spool-state-machine.ts)
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Multi-page navigation (P1-P6 pages) | Single page + modal stack | v5.0 (this milestone) | page.tsx must be completely rewritten |
| AppContext for all state | SpoolListContext dedicated to card list | v5.0 Phase 4 | New context file needed |
| Router-based state passing | Modal stack with local state | v5.0 Phase 1-3 | useModalStack already built |
| Union selection workflow | action_override PAUSAR/COMPLETAR | v5.0 Plan 00-03 | WorkerModal already uses action_override |

**Deprecated/outdated:**
- `app/page.tsx` current content: Old multi-page operation selector — to be replaced.
- `lib/context.tsx` AppContext: Still needed for layout (AppProvider wraps app), but SpoolListContext is separate and purpose-built.

## Open Questions

1. **SpoolListProvider placement — layout.tsx vs page.tsx**
   - What we know: layout.tsx wraps all pages with AppProvider; SpoolListContext is only needed on the main page.
   - What's unclear: Whether future pages (dashboard) might also need spool list access.
   - Recommendation: Define SpoolListProvider locally in page.tsx as a wrapper component. Easier to scope.

2. **refreshAll stable reference — useRef pattern vs spools dependency**
   - What we know: `refreshAll` depending on `spools` causes polling re-registration on every card add/remove. The useRef pattern (reading from ref inside a stable callback) breaks the dependency chain.
   - What's unclear: Whether test setup (jest.useFakeTimers) will handle the ref pattern cleanly.
   - Recommendation: Use the useRef pattern for production correctness. Tests can spy on the batch API directly.

3. **Animation for auto-remove**
   - What we know: CONTEXT.md says "300-500ms fade-out". SpoolCard has no animation state currently.
   - What's unclear: Whether to add animation to SpoolCard itself or manage it at the SpoolCardList level.
   - Recommendation: Keep it simple — add a `isRemoving` state to SpoolCardList that adds `opacity-0 transition-opacity duration-300` to the target card, then call removeSpool after 300ms. Avoids modifying SpoolCard.

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | Jest 30.2.0 + @testing-library/react 16.3.2 |
| Config file | `zeues-frontend/jest.config.js` |
| Quick run command | `cd zeues-frontend && npm test -- --testPathPattern=SpoolListContext --no-coverage` |
| Full suite command | `cd zeues-frontend && npm test -- --no-coverage` |

### Phase Requirements → Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| CARD-01 | Añadir Spool button opens modal | unit | `npm test -- --testPathPattern=page` | ❌ Wave 0 |
| CARD-02 | Cards render with correct data | unit | `npm test -- --testPathPattern=SpoolCardList` | ✅ (SpoolCardList.test.tsx) |
| CARD-03 | localStorage persistence + 30s poll | unit | `npm test -- --testPathPattern=SpoolListContext` | ❌ Wave 0 |
| CARD-04 | MET APROBADA removes card | unit | `npm test -- --testPathPattern=page` | ❌ Wave 0 |
| CARD-05 | MET RECHAZADA keeps card | unit | `npm test -- --testPathPattern=page` | ❌ Wave 0 |
| CARD-06 | Multiple spools in list | unit | `npm test -- --testPathPattern=SpoolListContext` | ❌ Wave 0 |
| MODAL-01 | Card click opens OperationModal | unit | `npm test -- --testPathPattern=page` | ❌ Wave 0 |
| MODAL-02–06 | Modal chain progression | unit | `npm test -- --testPathPattern=page` | ❌ Wave 0 |
| MODAL-07 | Toast shown after action | unit | `npm test -- --testPathPattern=page` | ❌ Wave 0 |
| STATE-03 | CANCELAR libre = frontend only | unit | `npm test -- --testPathPattern=page` | ❌ Wave 0 |
| STATE-04 | CANCELAR occupied = backend call | unit | `npm test -- --testPathPattern=page` | ❌ Wave 0 |

### Sampling Rate
- **Per task commit:** `cd zeues-frontend && npm test -- --testPathPattern="SpoolListContext|page" --no-coverage`
- **Per wave merge:** `cd zeues-frontend && npm test -- --no-coverage`
- **Phase gate:** Full suite green + `npm run build` passes before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] `zeues-frontend/__tests__/lib/SpoolListContext.test.tsx` — covers CARD-03, CARD-06, localStorage sync, refreshAll
- [ ] `zeues-frontend/__tests__/components/page.test.tsx` — covers CARD-01, CARD-04, CARD-05, MODAL-01 through MODAL-07, STATE-03, STATE-04

*(Existing test infrastructure covers all other requirements — SpoolCard, SpoolCardList, all modals, hooks already have tests.)*

## Sources

### Primary (HIGH confidence)
- Codebase inspection: `zeues-frontend/lib/`, `zeues-frontend/components/`, `zeues-frontend/hooks/` — all existing Phase 1-3 deliverables read directly
- `zeues-frontend/lib/local-storage.ts` — localStorage utility API
- `zeues-frontend/lib/api.ts` — batchGetStatus, getSpoolStatus, finalizarSpool, cancelarReparacion signatures
- `zeues-frontend/hooks/useModalStack.ts` — push/pop/clear/isOpen API
- `zeues-frontend/hooks/useNotificationToast.ts` — enqueue/dismiss API
- `backend/services/occupation_service.py` — zero-union CANCELAR path verified at line 1019

### Secondary (MEDIUM confidence)
- MDN Web Docs pattern: Page Visibility API (`document.visibilityState`, `visibilitychange` event) — standard browser API, no verification needed
- React docs pattern: useReducer for complex state, useRef for mutable values in effects

### Tertiary (LOW confidence)
- None — all findings verified against codebase directly

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — all libraries already installed, versions from package.json
- Architecture: HIGH — all building blocks exist and were read directly
- Pitfalls: HIGH — identified from direct code inspection (duplicate SpoolCardData, CANCELAR endpoint differences)

**Research date:** 2026-03-10
**Valid until:** This research is based on the codebase snapshot; valid until next phase execution changes component interfaces.
