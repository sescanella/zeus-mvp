# Phase 3: Frontend — Modales - Research

**Researched:** 2026-03-10
**Domain:** React modal components (Next.js 14, TypeScript, Tailwind CSS, @testing-library)
**Confidence:** HIGH

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- Click on card → OperationModal (ARM/SOLD/REP/MET filtered by spool state) [MODAL-01]
- ARM/SOLD/REP → ActionModal (INICIAR/FINALIZAR/PAUSAR/CANCELAR filtered by state) [MODAL-02]
- INICIAR/FINALIZAR/PAUSAR → WorkerModal (workers filtered by operation role) [MODAL-03]
- CANCELAR does NOT require worker — returns to main screen directly [MODAL-04]
- MET → MetrologiaModal (APROBADA/RECHAZADA) [MODAL-05]
- On worker or MET result selection → execute API call → return to main screen [MODAL-06]
- NotificationToast shows success/error feedback on main screen [MODAL-07]
- No union selection — PAUSAR replaces partial completion [MODAL-08]
- AddSpoolModal reuses existing SpoolTable + SpoolFilterPanel [D-08]
- Already-added spools shown as disabled/grey in AddSpoolModal [UX-01]
- Valid operations from spool-state-machine (getValidOperations, getValidActions) [STATE-01, STATE-02]
- No optimistic updates — loading spinner, wait for API response [UX-03, D-09]
- API errors shown inline in the active modal
- Blueprint Industrial palette (navy #001F3F, orange #FF6B35) [UX-04]
- Mobile-first, large touch targets [UX-04]

### Claude's Discretion
- Internal modal component structure and prop interfaces
- Loading state UX within modals
- Error display layout within modals
- Animation/transition between modal stack levels
- Worker list display format in WorkerModal

### Deferred Ideas (OUT OF SCOPE)
- Modal flow wiring to main page (Phase 4: Integration)
- Polling/refresh after modal action (Phase 4)
- Auto-remove on MET APROBADA (Phase 4)
- CANCELAR dual logic (Phase 4)
</user_constraints>

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| MODAL-01 | Click on card → OperationModal (ARM/SOLD/REP/MET filtered by spool state) | getValidOperations() from spool-state-machine.ts; Operation type = 'ARM' \| 'SOLD' \| 'MET' \| 'REP' |
| MODAL-02 | ARM/SOLD/REP → ActionModal (INICIAR/FINALIZAR/PAUSAR/CANCELAR filtered by state) | getValidActions() from spool-state-machine.ts; Action type = 'INICIAR' \| 'FINALIZAR' \| 'PAUSAR' \| 'CANCELAR' |
| MODAL-03 | INICIAR/FINALIZAR/PAUSAR → WorkerModal (workers filtered by operation role) | getWorkers() from api.ts; OPERATION_TO_ROLES from operation-config.ts |
| MODAL-04 | CANCELAR no requiere worker — returns to main screen directly | clear() from useModalStack; CANCELAR is deferred to Phase 4 wiring |
| MODAL-05 | MET → MetrologiaModal (APROBADA/RECHAZADA) | completarMetrologia() from api.ts |
| MODAL-06 | Worker or MET result selection → execute API call → return to main screen | iniciarSpool/finalizarSpool/completarMetrologia/tomarReparacion from api.ts |
| MODAL-07 | NotificationToast shows feedback on main screen | useNotificationToast hook + NotificationToast component already built |
| MODAL-08 | No union selection — PAUSAR replaces partial completion | finalizarSpool with action_override: 'PAUSAR' \| 'COMPLETAR' already in FinalizarRequest |
| UX-01 | AddSpoolModal shows already-added spools as disabled/grey | SpoolTable disabledSpools prop (built in Phase 2); SpoolFilterPanel showSelectionControls prop |
| STATE-01 | Valid operations depend on spool state (STATE-01 mapping) | getValidOperations() in spool-state-machine.ts |
| STATE-02 | Valid actions depend on occupation state (STATE-02 mapping) | getValidActions() in spool-state-machine.ts |
</phase_requirements>

---

## Summary

Phase 3 creates 5 modal components that form the entire operation flow in the v5.0 single-page architecture. All foundation infrastructure is already built: the `Modal` base component (with `isTopOfStack` ESC guard), `useModalStack` hook (push/pop/clear), `useNotificationToast` hook, `SpoolTable` (with `disabledSpools`), `SpoolFilterPanel` (with `showSelectionControls`), state machine functions (`getValidOperations`, `getValidActions`), all API functions (`iniciarSpool`, `finalizarSpool`, `completarMetrologia`, etc.), and typed data models.

Each modal is a presentational "leaf" component — it receives the selected spool and necessary callbacks, renders filtered options, handles its own loading/error state, and calls back up to the parent on completion. The parent (Phase 4) owns the modal stack wiring; Phase 3 components only need to expose clean callback interfaces.

The key architectural decision for Phase 3 is that each modal component is standalone (no cross-modal state coupling) and the CANCELAR path from ActionModal calls `onClose()` directly (the actual CANCELAR backend logic is Phase 4 scope). For REP actions, `tomarReparacion`/`pausarReparacion`/`completarReparacion`/`cancelarReparacion` are already in `api.ts`.

**Primary recommendation:** Build each modal as an independent component that receives `spool: SpoolCardData`, fires `onComplete()` or `onClose()`, and handles its own async API call + loading/error state. Wire the stack in Phase 4.

---

## Standard Stack

### Core (already installed)
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| next | ^14.2.0 | Next.js App Router, React Server/Client components | Project standard |
| react | ^18.3.0 | Component model, useState/useEffect/useCallback | Project standard |
| react-dom | ^18.3.0 | createPortal for Modal rendering | Project standard |
| typescript | ^5.4.0 | Type safety, no `any` rule | Project standard |
| tailwindcss | ^3.4.0 | Utility CSS; zeues-navy, zeues-orange, font-mono classes | Project standard |
| lucide-react | ^0.562.0 | Icons (X, CheckCircle, AlertCircle, Puzzle, Flame, etc.) | Project standard |

### Testing (already installed)
| Library | Version | Purpose |
|---------|---------|---------|
| jest | ^30.2.0 | Unit test runner |
| jest-environment-jsdom | ^30.2.0 | DOM environment for component tests |
| @testing-library/react | ^16.3.2 | render, screen, fireEvent, act, renderHook |
| @testing-library/jest-dom | ^6.9.1 | toBeInTheDocument, toHaveClass, etc. |
| jest-axe | ^10.0.0 | Accessibility (axe) assertions in Jest |

**Installation:** No new packages needed. All dependencies are in place.

---

## Architecture Patterns

### Recommended Modal File Structure
```
zeues-frontend/components/
├── Modal.tsx                  # Base modal (exists — portal, ESC, isTopOfStack)
├── NotificationToast.tsx      # Toast display (exists)
├── SpoolCard.tsx              # Card (exists)
├── SpoolCardList.tsx          # Card list (exists)
├── SpoolTable.tsx             # Table with disabledSpools (exists)
├── SpoolFilterPanel.tsx       # Filter panel (exists)
├── AddSpoolModal.tsx          # NEW — Phase 3.1
├── OperationModal.tsx         # NEW — Phase 3.2
├── ActionModal.tsx            # NEW — Phase 3.3
├── WorkerModal.tsx            # NEW — Phase 3.4
└── MetrologiaModal.tsx        # NEW — Phase 3.5

zeues-frontend/__tests__/components/
├── AddSpoolModal.test.tsx     # NEW
├── OperationModal.test.tsx    # NEW
├── ActionModal.test.tsx       # NEW
├── WorkerModal.test.tsx       # NEW
└── MetrologiaModal.test.tsx   # NEW
```

### Pattern 1: Base Modal Wrapper
Each modal wraps `<Modal>` from `@/components/Modal` directly. The base Modal handles:
- Portal rendering (`createPortal` to `document.body`)
- ESC key (only fires when `isTopOfStack !== false`)
- Backdrop click to close
- Body scroll lock
- SSR safety (mounted guard)

```typescript
// Source: zeues-frontend/components/Modal.tsx (existing)
import { Modal } from '@/components/Modal';

interface OperationModalProps {
  isOpen: boolean;
  spool: SpoolCardData;
  onSelectOperation: (op: Operation) => void;
  onClose: () => void;
  isTopOfStack?: boolean;
}

export function OperationModal({ isOpen, spool, onSelectOperation, onClose, isTopOfStack }: OperationModalProps) {
  const validOps = getValidOperations(spool);
  return (
    <Modal
      isOpen={isOpen}
      onClose={onClose}
      ariaLabel="Seleccionar operacion"
      className="bg-zeues-navy border-4 border-white rounded-none max-w-sm"
      isTopOfStack={isTopOfStack}
    >
      {/* content */}
    </Modal>
  );
}
```

### Pattern 2: Inline Loading + Error State
No optimistic updates — show spinner during API call, inline error below buttons on failure. This is per UX-03 (D-09).

```typescript
// Pattern for modals that make API calls (WorkerModal, MetrologiaModal)
const [loading, setLoading] = useState(false);
const [error, setError] = useState<string | null>(null);

const handleAction = async () => {
  setLoading(true);
  setError(null);
  try {
    await apiFunction(payload);
    onComplete();  // parent clears stack + enqueues toast
  } catch (err) {
    setError(err instanceof Error ? err.message : 'Error desconocido');
  } finally {
    setLoading(false);
  }
};
```

Error display inside modal (per success criteria: "API errors shown inline in the active modal"):
```typescript
{error && (
  <p role="alert" className="text-red-400 font-mono text-sm font-black mt-3">
    {error}
  </p>
)}
```

### Pattern 3: State-Filtered Button Lists
OperationModal and ActionModal render only valid options as large touch-target buttons.

```typescript
// Source: zeues-frontend/lib/spool-state-machine.ts (getValidOperations)
const validOps = getValidOperations(spool);   // Operation[]
const validActions = getValidActions(spool);  // Action[]

// Render each as a full-width button
{validOps.map((op) => (
  <button
    key={op}
    onClick={() => onSelectOperation(op)}
    className="w-full h-16 border-4 border-white font-mono font-black text-lg text-white
               active:bg-white active:text-zeues-navy transition-colors
               focus:outline-none focus:ring-2 focus:ring-zeues-orange focus:ring-inset"
    aria-label={`Seleccionar operacion ${op}`}
  >
    {op}
  </button>
))}
```

### Pattern 4: Worker Role Filtering
WorkerModal fetches workers, filters by operation role using `OPERATION_TO_ROLES`.

```typescript
// Source: zeues-frontend/lib/operation-config.ts (OPERATION_TO_ROLES)
// ARM → ['Armador', 'Ayudante']
// SOLD → ['Soldador', 'Ayudante']
// MET → ['Metrologia']  (but MET goes to MetrologiaModal, not WorkerModal)
// REP → ['Armador', 'Soldador']

const roleMap: Record<Operation, string[]> = {
  ARM: ['Armador', 'Ayudante'],
  SOLD: ['Soldador', 'Ayudante'],
  REP: ['Armador', 'Soldador'],
  MET: ['Metrologia'],  // not used in WorkerModal (MET has its own modal)
};

const filteredWorkers = workers.filter(
  (w) => w.roles?.some((r) => allowedRoles.includes(r)) ?? false
);
```

`Worker.roles` is an array (`string[]`). Workers with no matching role are excluded.

### Pattern 5: AddSpoolModal Composition
Reuses `SpoolTable` + `SpoolFilterPanel` with the props added in Phase 2.

```typescript
// SpoolTable with disabledSpools — shows already-tracked tags as grey/locked
<SpoolTable
  spools={filteredSpools}
  selectedSpools={[]}         // single-select: user picks one tag
  onToggleSelect={handleAdd}  // fires immediately on row click
  tipo={null}
  disabledSpools={alreadyTrackedTags}   // UX-01: grey out already-added spools
/>

// SpoolFilterPanel with showSelectionControls=false — no TODOS/NINGUNO in add modal
<SpoolFilterPanel
  showSelectionControls={false}
  /* ... search and filter props */
/>
```

AddSpoolModal fetches the spool list at open time. The "add" action is single-click (pick one spool → call `onAdd(tag)` → close). No multi-select needed.

### Pattern 6: API Call Routing by Operation + Action
WorkerModal must call the correct API function based on `(operation, action)` pair:

| operation | action | API function |
|-----------|--------|-------------|
| ARM / SOLD | INICIAR | `iniciarSpool({ tag_spool, worker_id, operacion })` |
| ARM / SOLD | FINALIZAR | `finalizarSpool({ tag_spool, worker_id, operacion, action_override: 'COMPLETAR' })` |
| ARM / SOLD | PAUSAR | `finalizarSpool({ tag_spool, worker_id, operacion, action_override: 'PAUSAR' })` |
| REP | INICIAR | `tomarReparacion({ tag_spool, worker_id })` |
| REP | FINALIZAR / PAUSAR | `completarReparacion` or `pausarReparacion` |

CANCELAR does not reach WorkerModal — ActionModal calls `onClose()` directly.
MetrologiaModal calls `completarMetrologia(tag, worker_id, resultado)`.

### Anti-Patterns to Avoid
- **Cross-modal state coupling:** Each modal must be self-contained. Do not pass state from ActionModal into WorkerModal as props — pass only `operation` and `action`.
- **Duplicate ESC handlers:** Do not add custom `keydown` listeners. The base `Modal` handles ESC via `isTopOfStack`.
- **Worker filter by `.rol` (singular):** Use `.roles` (array) not `.rol` (deprecated). See `Worker` type in `types.ts`.
- **`any` type:** Never use `any`. Use `unknown` for dynamic data.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Modal portal rendering | Custom portal wrapper | `Modal` from `@/components/Modal` | Handles SSR, ESC, backdrop, scroll lock |
| Toast notifications | Custom alert/banner | `useNotificationToast` + `NotificationToast` | Auto-dismiss, ARIA live, queue |
| Modal stack management | useState boolean per modal | `useModalStack` (push/pop/clear) | Stack semantics, isOpen computed correctly |
| State machine logic | Inline if/else for valid ops | `getValidOperations`, `getValidActions` | Already tested, edge cases handled |
| Worker role filtering | Inline role strings | `OPERATION_TO_ROLES` from `operation-config.ts` | Single source of truth |
| Spool list with disabled rows | Custom table | `SpoolTable` with `disabledSpools` prop | Built in Phase 2 exactly for this purpose |
| Filter UI | Custom filter form | `SpoolFilterPanel` with `showSelectionControls=false` | Built in Phase 2 exactly for this purpose |

**Key insight:** Every reusable piece was built in Phases 1 and 2 precisely to be consumed here. Rebuilding any of these would duplicate tested code.

---

## Common Pitfalls

### Pitfall 1: Worker.rol vs Worker.roles
**What goes wrong:** Filtering workers by `worker.rol` (singular, legacy field) misses multi-role workers.
**Why it happens:** `Worker` interface has both `rol?: string` (deprecated) and `roles?: string[]` (current).
**How to avoid:** Always use `worker.roles?.some(r => allowedRoles.includes(r))`.
**Warning signs:** Workers with multiple roles disappear from filtered list.

### Pitfall 2: isTopOfStack Not Wired
**What goes wrong:** All modals handle ESC, so pressing ESC on a lower-stack modal (e.g., ActionModal behind WorkerModal) fires the wrong close.
**Why it happens:** `isTopOfStack` defaults to `true` in Modal — safe only when there's one modal.
**How to avoid:** Each modal must pass `isTopOfStack` from the parent. In Phase 3, modals are built standalone (Phase 4 wires the stack). Keep the prop in the interface now; the prop defaults to `true` until Phase 4 wires it.
**Warning signs:** Multiple modals close simultaneously on single ESC press.

### Pitfall 3: Stale Worker Data (Fetch Timing)
**What goes wrong:** WorkerModal shows stale workers if fetched once at app load.
**Why it happens:** Workers rarely change, but fetching at component mount (each time modal opens) is safest.
**How to avoid:** Fetch workers inside WorkerModal on mount (in `useEffect` with `[]` deps), show loading state while fetching.
**Warning signs:** Deactivated workers appear in the list.

### Pitfall 4: Loading State Not Reset on Close
**What goes wrong:** Opening the modal a second time shows the previous error or loading spinner.
**Why it happens:** Component state persists while the modal is mounted (if parent keeps it in DOM).
**How to avoid:** Reset `loading` and `error` state on modal open (`useEffect([isOpen])`), or unmount the component when `isOpen=false`. The base `Modal` component returns null when not open, which unmounts children — this is the safe default.
**Warning signs:** Old error message visible immediately when reopening modal.

### Pitfall 5: CANCELAR Dual Logic
**What goes wrong:** Implementing the CANCELAR backend call in Phase 3 when it belongs in Phase 4.
**Why it happens:** CONTEXT.md says "CANCELAR sin worker cierra modales directo" which is frontend-only, but the full dual logic (free vs occupied) is Phase 4 scope.
**How to avoid:** ActionModal's CANCELAR button calls `onClose()` (or a specific `onCancel()` callback). Do NOT call any API from ActionModal. The Phase 4 integration layer decides whether to call backend CANCELAR.

### Pitfall 6: finalizarSpool With selected_unions vs action_override
**What goes wrong:** Passing `selected_unions: []` to finalizarSpool instead of `action_override: 'PAUSAR'`.
**Why it happens:** The `FinalizarRequest` type has both fields. An empty `selected_unions` array triggers CANCELADO (zero-union path), NOT PAUSAR.
**How to avoid:** Always use `action_override: 'PAUSAR'` for pause actions and `action_override: 'COMPLETAR'` for complete actions (v5.0 flow eliminates union selection entirely per MODAL-08).

---

## Code Examples

Verified patterns from existing codebase files:

### Operation button list (OperationModal)
```typescript
// Source: spool-state-machine.ts (getValidOperations + Operation type)
import { getValidOperations, type Operation } from '@/lib/spool-state-machine';

const OPERATION_LABELS: Record<Operation, string> = {
  ARM: 'ARMADO',
  SOLD: 'SOLDADURA',
  MET: 'METROLOGÍA',
  REP: 'REPARACIÓN',
};

const validOps = getValidOperations(spool);
// Renders buttons for each valid operation
```

### Action button list (ActionModal)
```typescript
// Source: spool-state-machine.ts (getValidActions + Action type)
import { getValidActions, type Action } from '@/lib/spool-state-machine';

const ACTION_LABELS: Record<Action, string> = {
  INICIAR: 'INICIAR',
  FINALIZAR: 'FINALIZAR',
  PAUSAR: 'PAUSAR',
  CANCELAR: 'CANCELAR',
};

const validActions = getValidActions(spool);
// CANCELAR in this list → onCancel() callback (no worker needed)
// Other actions → push('worker') in the modal stack
```

### API call for INICIAR ARM/SOLD (WorkerModal)
```typescript
// Source: api.ts (iniciarSpool, IniciarRequest)
import { iniciarSpool } from '@/lib/api';

await iniciarSpool({
  tag_spool: spool.tag_spool,
  worker_id: selectedWorker.id,
  // worker_nombre omitted — backend derives via WorkerService (Plan 00-03 decision)
  operacion: operation as 'ARM' | 'SOLD',
});
```

### API call for FINALIZAR/PAUSAR (WorkerModal)
```typescript
// Source: api.ts (finalizarSpool, FinalizarRequest)
import { finalizarSpool } from '@/lib/api';

// PAUSAR:
await finalizarSpool({
  tag_spool: spool.tag_spool,
  worker_id: selectedWorker.id,
  operacion: operation as 'ARM' | 'SOLD',
  action_override: 'PAUSAR',   // v5.0: no union selection (MODAL-08)
});

// FINALIZAR (COMPLETAR):
await finalizarSpool({
  tag_spool: spool.tag_spool,
  worker_id: selectedWorker.id,
  operacion: operation as 'ARM' | 'SOLD',
  action_override: 'COMPLETAR',
});
```

### API call for MET (MetrologiaModal)
```typescript
// Source: api.ts (completarMetrologia)
import { completarMetrologia } from '@/lib/api';

await completarMetrologia(
  spool.tag_spool,
  selectedWorker.id,
  resultado   // 'APROBADO' | 'RECHAZADO'
);
```

### API calls for REP (WorkerModal)
```typescript
// Source: api.ts (tomarReparacion, pausarReparacion, completarReparacion)
import { tomarReparacion, pausarReparacion, completarReparacion } from '@/lib/api';

// REP INICIAR:
await tomarReparacion({ tag_spool: spool.tag_spool, worker_id: selectedWorker.id });

// REP PAUSAR:
await pausarReparacion({ tag_spool: spool.tag_spool, worker_id: selectedWorker.id });

// REP FINALIZAR:
await completarReparacion({ tag_spool: spool.tag_spool, worker_id: selectedWorker.id });
```

### Accessibility pattern for modal buttons
```typescript
// Source: components/SpoolCard.tsx, components/NotificationToast.tsx (established patterns)
<button
  onClick={handleClick}
  aria-label="Seleccionar operacion ARM"
  className="w-full h-16 border-4 border-white font-mono font-black text-lg text-white
             active:bg-white active:text-zeues-navy transition-colors
             focus:outline-none focus:ring-2 focus:ring-zeues-orange focus:ring-inset"
>
  ARMADO
</button>
```

### Modal class string (Blueprint Industrial palette)
```typescript
// Source: components/SpoolFilterPanel.tsx (existing modal usage)
className="bg-zeues-navy border-4 border-white rounded-none max-w-sm"
// max-w-sm (384px) for operation/action/metrologia modals
// max-w-lg (512px) for AddSpoolModal (needs table space)
```

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Multi-page navigation (P1-P6) | Single page + modal stack | v5.0 (this milestone) | Modals replace page routes |
| Union selection in FINALIZAR | `action_override: PAUSAR/COMPLETAR` | Plan 00-03 (2026-03-10) | WorkerModal no longer needs union picker |
| `selected_unions: []` = CANCELAR | `action_override` or `selected_unions` with guard | Plan 00-03 (2026-03-10) | Zero-union guard updated; must use `action_override` |
| `worker_nombre` required in IniciarRequest | `worker_nombre` optional (backend derives it) | Plan 00-03 (2026-03-10) | WorkerModal doesn't need to format worker name |

---

## Open Questions

1. **AddSpoolModal: which endpoint to call for the spool list?**
   - What we know: `getSpoolsParaIniciar(operacion)` returns spools for ARM/SOLD; the AddSpoolModal doesn't filter by a specific operation.
   - What's unclear: Should AddSpoolModal show ALL spools (any state), or only spools that have at least one valid operation?
   - Recommendation: Fetch ALL spools from backend, show all, let `getValidOperations()` control the OperationModal. If no endpoint for "all spools" is available without operation filter, use `/api/spools/iniciar?operacion=ARM` as a starting point — but this is a Phase 4 concern since AddSpoolModal in Phase 3 only needs to call `onAdd(tag)`. Use `getSpoolsParaIniciar('ARM')` for the initial implementation (most common case) and document the limitation.

2. **REP action mapping in WorkerModal: FINALIZAR = completarReparacion or FINALIZAR = tomarReparacion+completar?**
   - What we know: `tomarReparacion` = INICIAR REP, `completarReparacion` = finish REP, `pausarReparacion` = pause.
   - What's unclear: FINALIZAR for REP maps to `completarReparacion`.
   - Recommendation: Map `(REP, INICIAR)` → `tomarReparacion`, `(REP, FINALIZAR)` → `completarReparacion`, `(REP, PAUSAR)` → `pausarReparacion`. Confidence: HIGH (matches operation-config.ts which shows REP has tomar/pausar/completar actions).

---

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | Jest 30.2.0 + @testing-library/react 16.3.2 + jest-axe 10.0.0 |
| Config file | `zeues-frontend/jest.config.js` |
| Quick run command | `cd zeues-frontend && npx jest __tests__/components/OperationModal.test.tsx --no-coverage` |
| Full suite command | `cd zeues-frontend && npm test -- --no-coverage` |

### Phase Requirements → Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| MODAL-01 | OperationModal renders only valid operations from getValidOperations | unit | `npx jest __tests__/components/OperationModal.test.tsx` | ❌ Wave 0 |
| MODAL-02 | ActionModal renders only valid actions from getValidActions | unit | `npx jest __tests__/components/ActionModal.test.tsx` | ❌ Wave 0 |
| MODAL-03 | WorkerModal fetches and filters workers by operation role | unit | `npx jest __tests__/components/WorkerModal.test.tsx` | ❌ Wave 0 |
| MODAL-04 | ActionModal CANCELAR button calls onClose (no worker needed) | unit | `npx jest __tests__/components/ActionModal.test.tsx` | ❌ Wave 0 |
| MODAL-05 | MetrologiaModal renders APROBADA/RECHAZADA buttons | unit | `npx jest __tests__/components/MetrologiaModal.test.tsx` | ❌ Wave 0 |
| MODAL-06 | WorkerModal / MetrologiaModal calls correct API and fires onComplete | unit | `npx jest __tests__/components/WorkerModal.test.tsx __tests__/components/MetrologiaModal.test.tsx` | ❌ Wave 0 |
| MODAL-07 | (Deferred to Phase 4 — NotificationToast integration) | — | — | ✅ already tested |
| MODAL-08 | WorkerModal calls finalizarSpool with action_override (no selected_unions) | unit | `npx jest __tests__/components/WorkerModal.test.tsx` | ❌ Wave 0 |
| UX-01 | AddSpoolModal passes alreadyTracked tags as disabledSpools to SpoolTable | unit | `npx jest __tests__/components/AddSpoolModal.test.tsx` | ❌ Wave 0 |
| STATE-01 | OperationModal shows ARM-only for LIBRE spool, MET-only for COMPLETADO | unit | `npx jest __tests__/components/OperationModal.test.tsx` | ❌ Wave 0 |
| STATE-02 | ActionModal shows INICIAR/CANCELAR for libre, FINALIZAR/PAUSAR/CANCELAR for occupied | unit | `npx jest __tests__/components/ActionModal.test.tsx` | ❌ Wave 0 |

### Accessibility (axe) per component
All modal components must pass `axe` assertions using `jest-axe`. Pattern established in `NotificationToast.test.tsx` and `SpoolCard.test.tsx`:
```typescript
// Use jest.useRealTimers() inside axe test blocks (established in Plan 02-01)
it('has no axe violations', async () => {
  jest.useRealTimers();
  const { container } = render(<OperationModal ... />);
  const results = await axe(container);
  expect(results).toHaveNoViolations();
}, 10000);
```

### Sampling Rate
- **Per task commit:** `cd zeues-frontend && npx jest __tests__/components/<ModalName>.test.tsx --no-coverage`
- **Per wave merge:** `cd zeues-frontend && npm test -- --no-coverage`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] `zeues-frontend/__tests__/components/AddSpoolModal.test.tsx` — covers UX-01
- [ ] `zeues-frontend/__tests__/components/OperationModal.test.tsx` — covers MODAL-01, STATE-01
- [ ] `zeues-frontend/__tests__/components/ActionModal.test.tsx` — covers MODAL-02, MODAL-04, STATE-02
- [ ] `zeues-frontend/__tests__/components/WorkerModal.test.tsx` — covers MODAL-03, MODAL-06, MODAL-08
- [ ] `zeues-frontend/__tests__/components/MetrologiaModal.test.tsx` — covers MODAL-05, MODAL-06
- [ ] `zeues-frontend/components/AddSpoolModal.tsx` — implementation (not a test gap, but listed for clarity)
- [ ] `zeues-frontend/components/OperationModal.tsx`
- [ ] `zeues-frontend/components/ActionModal.tsx`
- [ ] `zeues-frontend/components/WorkerModal.tsx`
- [ ] `zeues-frontend/components/MetrologiaModal.tsx`

---

## Sources

### Primary (HIGH confidence)
- `zeues-frontend/hooks/useModalStack.ts` — ModalId type, push/pop/clear/isOpen API (read directly)
- `zeues-frontend/hooks/useNotificationToast.ts` — Toast, enqueue/dismiss API (read directly)
- `zeues-frontend/components/Modal.tsx` — props interface incl. `isTopOfStack` (read directly)
- `zeues-frontend/components/SpoolTable.tsx` — `disabledSpools` prop (read directly)
- `zeues-frontend/components/SpoolFilterPanel.tsx` — `showSelectionControls` prop (read directly)
- `zeues-frontend/lib/spool-state-machine.ts` — `getValidOperations`, `getValidActions` (read directly)
- `zeues-frontend/lib/api.ts` — all API functions incl. `iniciarSpool`, `finalizarSpool`, `completarMetrologia`, reparacion endpoints (read directly)
- `zeues-frontend/lib/types.ts` — `SpoolCardData`, `Worker`, `IniciarRequest`, `FinalizarRequest` (read directly)
- `zeues-frontend/lib/operation-config.ts` — `OPERATION_TO_ROLES`, `OPERATION_ICONS` (read directly)
- `.planning/phases/03-frontend-modales/03-CONTEXT.md` — user decisions (read directly)
- `.planning/v5.0-single-page/REQUIREMENTS.md` — all requirements (read directly)

### Secondary (MEDIUM confidence)
- `.planning/STATE.md` — key decisions and phase history
- `.planning/phases/02-core-location-tracking/02-02-SUMMARY.md` — Phase 2 completion status

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — all packages visible in package.json
- Architecture: HIGH — all building blocks read from source; interfaces verified
- Pitfalls: HIGH — derived from direct reading of existing code patterns and decision logs
- API routing table: HIGH — derived from types.ts + api.ts directly

**Research date:** 2026-03-10
**Valid until:** 2026-04-10 (stable stack, no fast-moving deps)
