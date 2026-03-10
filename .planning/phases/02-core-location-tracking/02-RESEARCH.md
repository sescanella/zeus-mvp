# Phase 2: Frontend — Componentes Core - Research

**Researched:** 2026-03-10
**Domain:** React/Next.js component development (TypeScript, Tailwind CSS, WCAG 2.1 AA)
**Confidence:** HIGH

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

**NotificationToast (CARD-02, UX-02, MODAL-07)**
- Toast with auto-dismiss 3-5 seconds (UX-02) — Phase 1 hook uses 4000ms
- role="alert" for accessibility (ARIA live region)
- Renders success/error feedback after API operations (MODAL-07)
- Uses useNotificationToast hook from Phase 1 (01-03)

**SpoolCard (CARD-02, STATE-05, STATE-06)**
- Displays: TAG, operación actual, acción, worker, tiempo en estado (CARD-02)
- Timer shows real-time elapsed since Fecha_Ocupacion when spool is occupied (STATE-05)
- PAUSADO shows static badge without timer (STATE-06)
- Renders all states: libre, iniciado, pausado, completado, rechazado, bloqueado
- Uses SpoolCardData type from Phase 1 (01-01)
- Click triggers OperationModal (Phase 3)

**SpoolCardList (CARD-06)**
- Container for multiple SpoolCards
- Empty state when no spools added
- Supports adding/removing spools individually (CARD-06)

**SpoolTable Modification (UX-01)**
- Add `disabledSpools` prop — already-added spools shown as disabled/grey (UX-01)
- Backward compatibility with existing usage

**SpoolFilterPanel Modification**
- Add `showSelectionControls` prop for AddSpool modal context
- Backward compatibility with existing usage

**Modal Modification (MODAL stack)**
- ESC key only closes the top modal in the stack (not all)
- Integrates with useModalStack from Phase 1 (01-03)

**Claude's Discretion**
- Timer implementation details (setInterval vs requestAnimationFrame)
- SpoolCard layout and styling specifics within Blueprint palette
- Empty state design for SpoolCardList
- Animation choices for toast entrance/exit
- Test strategy for timer components

### Deferred Ideas (OUT OF SCOPE)
- Modal components (Phase 3)
- Page assembly and polling (Phase 4)
- Old code cleanup (Phase 5)
</user_constraints>

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| CARD-02 | Cards show: TAG, operación actual, acción, worker, tiempo en estado | SpoolCard layout patterns; SpoolCardData interface (12 fields) already in types.ts |
| CARD-06 | Multiple spools addable; each operated individually | SpoolCardList container; empty state pattern; remove callback |
| STATE-05 | Timer shows elapsed since Fecha_Ocupacion only when occupied | setInterval with ISO-to-Date parse; Fecha_Ocupacion from SpoolCardData |
| STATE-06 | PAUSADO shows static badge without timer | Conditional timer render: `ocupado_por !== null` gates timer; estado_trabajo='PAUSADO' gates badge |
| MODAL-07 | NotificationToast shows feedback on main page after action | role="alert" + aria-live="assertive"; uses Toast/enqueue from useNotificationToast |
| UX-01 | AddSpool modal shows already-added spools as disabled/grey | `disabledSpools: string[]` prop on SpoolTable; visual pattern: grey/opacity-50 + tabIndex=-1 |
| UX-02 | Toast auto-dismiss 3-5 seconds | Already locked at 4000ms in useNotificationToast; NotificationToast just renders |
| UX-04 | Blueprint Industrial palette, mobile-first, large touch targets | Navy #001F3F / orange #FF5B00 via `zeues-navy`/`zeues-orange` classes; h-16/h-20 |
</phase_requirements>

---

## Summary

Phase 2 is a pure frontend component authoring phase. All business logic foundations (types, hooks, pure functions) were completed in Phase 1. The work here is: render SpoolCardData into visual components correctly, and surgically add props to three existing components without breaking their existing contracts.

The main technical risk is the live countdown timer in SpoolCard (STATE-05). `fecha_ocupacion` arrives as a `"DD-MM-YYYY HH:MM:SS"` string (Chile timezone format from `format_datetime_for_sheets`) — the format requires custom parsing since `new Date()` cannot parse it directly. This is the single non-trivial implementation detail in the phase.

The other risk is the Modal.tsx ESC change: currently every open modal instance registers its own keydown listener. With modal stacking, pressing ESC fires ALL listeners. The fix is to make ESC conditional on being the top-of-stack modal — which requires passing an `isTopOfStack` or `isActive` prop, or consuming the stack context directly.

**Primary recommendation:** Use `setInterval` at 1-second tick for the timer (not `requestAnimationFrame` — the RaF approach is for 60fps animations; a seconds counter needs 1-second ticks). Guard `fecha_ocupacion` parsing with a try/catch. Render `null` for timer when `ocupado_por` is null.

---

## Standard Stack

### Core (all already installed)

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| React | 18.3.0 | Component rendering, hooks (useState, useEffect, useRef, useCallback) | Project foundation |
| Next.js | 14.2.0 | App Router, `'use client'` directive, `createPortal` SSR guard | Project foundation |
| TypeScript | 5.4.0 | Strict typing, no `any` | Project constraint (ESLint enforced) |
| Tailwind CSS | 3.4.0 | Styling via utility classes; `zeues-navy`, `zeues-orange` tokens | Project standard |
| lucide-react | 0.562.0 | Icons only (no emojis, no other icon libs) | Project standard |

### Testing (all already installed)

| Library | Version | Purpose |
|---------|---------|---------|
| Jest 30 + jest-environment-jsdom | 30.2.0 | Unit tests; `testPathPatterns` flag (not legacy `testPathPattern`) |
| @testing-library/react | 16.3.2 | `render`, `screen`, `fireEvent`, `act`, `renderHook` |
| jest-axe | 10.0.0 | `axe(container)` for automated WCAG audit |

### No New Dependencies

Phase 2 requires zero new npm packages. Everything is available.

**Installation:** Nothing to install.

---

## Architecture Patterns

### Recommended File Layout

```
zeues-frontend/
├── components/
│   ├── NotificationToast.tsx     # NEW — renders toasts from useNotificationToast
│   ├── SpoolCard.tsx             # NEW — single spool card with timer
│   ├── SpoolCardList.tsx         # NEW — container + empty state
│   ├── SpoolTable.tsx            # MODIFY — add disabledSpools prop
│   ├── SpoolFilterPanel.tsx      # MODIFY — add showSelectionControls prop
│   └── Modal.tsx                 # MODIFY — ESC only closes top modal
└── __tests__/components/
    ├── NotificationToast.test.tsx # NEW
    ├── SpoolCard.test.tsx         # NEW
    └── SpoolCardList.test.tsx     # NEW
    # SpoolTable.test.tsx already exists — extend with disabledSpools cases
    # SpoolFilterPanel.test.tsx already exists — extend with showSelectionControls cases
```

### Pattern 1: New Component Structure (NotificationToast, SpoolCard, SpoolCardList)

**What:** Functional component with `'use client'` directive, explicit TypeScript props interface, Tailwind-only styling.

**When to use:** All new components in this phase.

```typescript
// Source: existing components (Modal.tsx, SpoolTable.tsx)
'use client';

import React from 'react';

interface MyComponentProps {
  // explicit types — never any, never unknown unless truly dynamic
}

export function MyComponent({ ... }: MyComponentProps) {
  // ...
}
```

### Pattern 2: Timer with setInterval (SpoolCard STATE-05)

**What:** Elapsed timer using `setInterval` at 1-second tick. Stores seconds as integer state. Clears on unmount.

**When to use:** SpoolCard — only when `spool.ocupado_por !== null`.

```typescript
// Source: React docs — useEffect + setInterval cleanup pattern
'use client';

import { useState, useEffect } from 'react';

function useElapsedSeconds(fechaOcupacion: string | null): number | null {
  const [elapsed, setElapsed] = useState<number | null>(null);

  useEffect(() => {
    if (!fechaOcupacion) {
      setElapsed(null);
      return;
    }

    // Parse "DD-MM-YYYY HH:MM:SS" (Chile format from format_datetime_for_sheets)
    const parsed = parseFechaOcupacion(fechaOcupacion);
    if (!parsed) {
      setElapsed(null);
      return;
    }

    const tick = () => setElapsed(Math.floor((Date.now() - parsed.getTime()) / 1000));
    tick(); // initial render
    const id = setInterval(tick, 1000);
    return () => clearInterval(id);
  }, [fechaOcupacion]);

  return elapsed;
}

// Chile format: "DD-MM-YYYY HH:MM:SS" → Date object
function parseFechaOcupacion(s: string): Date | null {
  try {
    // "21-01-2026 14:30:00" → [DD, MM, YYYY, HH, MM, SS]
    const match = s.match(/^(\d{2})-(\d{2})-(\d{4})\s+(\d{2}):(\d{2}):(\d{2})$/);
    if (!match) return null;
    const [, dd, mm, yyyy, hh, min, sec] = match;
    // Month is 0-indexed in JS Date
    return new Date(
      parseInt(yyyy), parseInt(mm) - 1, parseInt(dd),
      parseInt(hh), parseInt(min), parseInt(sec)
    );
  } catch {
    return null;
  }
}

// Format elapsed seconds as MM:SS or HH:MM:SS
function formatElapsed(seconds: number): string {
  const h = Math.floor(seconds / 3600);
  const m = Math.floor((seconds % 3600) / 60);
  const s = seconds % 60;
  const pad = (n: number) => String(n).padStart(2, '0');
  if (h > 0) return `${pad(h)}:${pad(m)}:${pad(s)}`;
  return `${pad(m)}:${pad(s)}`;
}
```

**CRITICAL:** `new Date("DD-MM-YYYY HH:MM:SS")` returns `Invalid Date` — always use the custom parser above. Never use ISO format assumptions on this string.

### Pattern 3: Adding Props with Backward Compatibility (SpoolTable, SpoolFilterPanel)

**What:** Add optional props with default values so all existing call sites remain valid.

**When to use:** SpoolTable (disabledSpools), SpoolFilterPanel (showSelectionControls).

```typescript
// Source: TypeScript optional props pattern — existing SpoolTable.tsx
interface SpoolTableProps {
  spools: Spool[];
  selectedSpools: string[];
  onToggleSelect: (tag: string) => void;
  tipo: TipoParam;
  disabledSpools?: string[]; // NEW — defaults to []
}

export function SpoolTable({
  spools,
  selectedSpools,
  onToggleSelect,
  tipo,
  disabledSpools = [], // default: empty, no behavior change for existing callers
}: SpoolTableProps) {
  // isDisabled replaces isBloqueado for the new "already added" concept
  // Both conditions need to block interaction
  const isDisabledSpool = (tag: string) => disabledSpools.includes(tag);
  // ...
}
```

**For SpoolFilterPanel `showSelectionControls`:** When `false`, hide the TODOS/NINGUNO/LIMPIAR FILTROS controls row (used in AddSpool modal context where selection is single-click, not batch).

### Pattern 4: Modal ESC Fix (Modal.tsx)

**What:** Current Modal.tsx registers a `keydown` listener on `document` whenever `isOpen && onClose`. With stacked modals, all open modal instances fire their `onClose` on a single ESC press. The fix: add an `isTopOfStack` prop (default `true` for backward compat) and only respond to ESC when `isTopOfStack === true`.

**When to use:** Only one change needed in Modal.tsx.

```typescript
// Source: existing Modal.tsx ESC handler — add isTopOfStack guard
interface ModalProps {
  isOpen: boolean;
  onClose?: () => void;
  onBackdropClick?: (() => void) | null;
  children: React.ReactNode;
  className?: string;
  ariaLabel?: string;
  isTopOfStack?: boolean; // NEW — default true for backward compat
}

// In the ESC useEffect:
useEffect(() => {
  if (!isOpen || !onClose) return;
  if (isTopOfStack === false) return; // not top — ignore ESC

  const handleEscape = (event: KeyboardEvent) => {
    if (event.key === 'Escape') onClose();
  };
  document.addEventListener('keydown', handleEscape);
  return () => document.removeEventListener('keydown', handleEscape);
}, [isOpen, onClose, isTopOfStack]);
```

**Alternative approach (also valid):** Pass an `onEscapeKey` override handler from the parent that calls `stack.pop()`. The `isTopOfStack` boolean prop is simpler and avoids coupling Modal to the stack hook.

### Pattern 5: NotificationToast ARIA

**What:** `role="alert"` with `aria-live="assertive"` causes screen readers to announce toast immediately. Render a wrapper div that always exists in DOM (empty when no toasts) so the live region is present before the first toast appears — ARIA live regions must be in DOM before content is injected.

```typescript
// Source: WAI-ARIA Live Regions spec
// The container MUST be rendered before the first toast is added
<div
  role="status"
  aria-live="polite"    // use "polite" for success, "assertive" for error
  aria-atomic="false"   // announce each toast independently
  className="fixed top-4 right-4 z-[100] flex flex-col gap-2 pointer-events-none"
>
  {toasts.map((toast) => (
    <div
      key={toast.id}
      role="alert"
      aria-live="assertive"
      // ...
    />
  ))}
</div>
```

**Decision:** Use a single outer `aria-live` region rendering all toasts vs individual `role="alert"` per toast. Both work — the existing codebase uses `role="alert"` per-element in similar patterns (see WCAG section of CLAUDE.md). Use `role="alert"` on each individual toast div for maximum screen reader compatibility.

### State Colors for SpoolCard (Blueprint palette)

| Estado | Color Class | Tailwind Token |
|--------|-------------|----------------|
| LIBRE | white/neutral | `text-white border-white/30` |
| EN_PROGRESO (ARM/SOLD/REP) | orange | `text-zeues-orange border-zeues-orange` |
| PAUSADO | yellow | `text-yellow-400 border-yellow-400` |
| COMPLETADO | green | `text-green-400 border-green-400` |
| RECHAZADO | red | `text-red-400 border-red-400` |
| PENDIENTE_METROLOGIA | blue accent | `text-blue-300 border-blue-300` |
| BLOQUEADO | dark red/muted | `text-red-600 border-red-600 opacity-75` |

### Anti-Patterns to Avoid

- **`new Date(fechaOcupacion)` directly:** `DD-MM-YYYY HH:MM:SS` is not ISO 8601. Returns `Invalid Date`. Always use the custom regex parser.
- **`requestAnimationFrame` for 1-second timer:** RAF is for smooth 60fps animations. A seconds-tick timer needs `setInterval(fn, 1000)`. Using RAF wastes CPU with 60 calls/sec for a timer that updates once/sec.
- **Forgetting `clearInterval` in cleanup:** Causes stale closures and memory leaks. Always return `() => clearInterval(id)` from the useEffect.
- **Missing `'use client'` directive:** All these components use hooks/events — they require `'use client'`. Next.js App Router defaults to Server Components.
- **`any` types in props:** ESLint will fail. Use explicit union types or `unknown` + type guard.
- **Hardcoded hex colors in JSX:** Use `zeues-orange`, `zeues-navy` Tailwind tokens, not `#FF5B00`.
- **Emoji in rendered output:** Inconsistent across devices (CLAUDE.md constraint). Use Lucide icons.
- **Mutating SpoolFilterPanel's existing props:** The `showSelectionControls` change must keep all 13 existing props working. Default `showSelectionControls` to `true` (current behavior = show controls).
- **Adding `disabledSpools` logic that also blocks `isBloqueado` from reparacion spools:** These are two separate disable concepts. Keep them independent — OR both conditions in the disabled check.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| WCAG audit in tests | Custom a11y checker | `jest-axe` — already in devDependencies | Handles 40+ WCAG rules automatically |
| Toast ID uniqueness | UUID library | `useRef(0)` counter already in useNotificationToast | Already solved in Phase 1 |
| Modal portal SSR | DIY mounted check | `createPortal` + `mounted` state — already in Modal.tsx | Solved — copy the pattern |
| State parsing for card | Re-implement parser | `parseEstadoDetalle` + `getValidOperations` from Phase 1 | Already TDD-verified, 48 tests passing |
| Timer format | moment.js / date-fns | Inline `formatElapsed` — trivial math, no dep needed | Simple arithmetic, no library warranted |

**Key insight:** The Phase 1 logic layer is complete and tested. Phase 2 components are pure rendering — they receive `SpoolCardData` and call Phase 1 pure functions. No business logic belongs in these components.

---

## Common Pitfalls

### Pitfall 1: fecha_ocupacion Format Assumption
**What goes wrong:** Developer writes `new Date(spool.fecha_ocupacion)` expecting ISO parsing. Gets `Invalid Date`. Timer shows `NaN:NaN` or crashes.
**Why it happens:** `fecha_ocupacion` is `"21-01-2026 14:30:00"` (Chilean DD-MM-YYYY), not ISO 8601. JS `Date` constructor only reliably parses ISO strings.
**How to avoid:** Use the custom regex parser described in Pattern 2 above. Add a null/Invalid Date guard before rendering timer.
**Warning signs:** Timer showing "NaN:NaN" in dev; `isNaN(parsedDate.getTime())` returns true.

### Pitfall 2: Modal ESC Double-Close
**What goes wrong:** Two modals open (e.g., operation + action). User presses ESC. Both `onClose` handlers fire. Stack jumps from 2 to 0 instead of 2 to 1.
**Why it happens:** Current Modal.tsx registers one `document.addEventListener('keydown', ...)` per open modal instance. ESC event bubbles to all of them.
**How to avoid:** Add `isTopOfStack` prop (default `true`). In Phase 3 when modals are assembled, the parent passes `isTopOfStack={modalStack.current === 'operation'}` etc.
**Warning signs:** Stack skips levels on ESC; `pop()` called multiple times per keypress.

### Pitfall 3: SpoolTable disabledSpools Breaking Existing Tests
**What goes wrong:** Adding `disabledSpools` interaction logic changes row behavior for existing test fixtures that don't pass the prop.
**Why it happens:** If default is `undefined` (not `[]`), `disabledSpools.includes(tag)` throws TypeError.
**How to avoid:** Default `disabledSpools = []` in destructuring. Existing tests pass no prop → default empty array → no rows disabled.
**Warning signs:** `TypeError: Cannot read properties of undefined (reading 'includes')` in test runner.

### Pitfall 4: Timer Memory Leak on SpoolCard Unmount
**What goes wrong:** SpoolCard is removed from SpoolCardList (user removes spool). The `setInterval` from the timer keeps running, updating state of an unmounted component.
**Why it happens:** Missing `clearInterval` in useEffect cleanup.
**How to avoid:** Always return `() => clearInterval(id)` from the useEffect. React logs a warning but doesn't throw.
**Warning signs:** "Warning: Can't perform a React state update on an unmounted component" in test output.

### Pitfall 5: ARIA Live Region Not Pre-Rendered
**What goes wrong:** First toast is never announced by screen reader.
**Why it happens:** ARIA live regions must exist in the DOM before content changes. If the `role="alert"` wrapper is only mounted when toasts array is non-empty, the screen reader hasn't observed it yet.
**How to avoid:** Always render the container div (it's empty when `toasts.length === 0`). Only the inner toast elements are conditionally rendered.
**Warning signs:** axe audit passes but manual screen reader testing reveals silent first toast.

---

## Code Examples

### SpoolCard — Full State Badge Logic

```typescript
// Source: CONTEXT.md decisions + SpoolCardData from zeues-frontend/lib/types.ts
import type { SpoolCardData } from '@/lib/types';
import { getValidOperations } from '@/lib/spool-state-machine';

// State label map — all 7 EstadoTrabajo values
const STATE_LABELS: Record<string, string> = {
  LIBRE: 'LIBRE',
  EN_PROGRESO: 'EN PROGRESO',
  PAUSADO: 'PAUSADO',
  COMPLETADO: 'COMPLETADO',
  RECHAZADO: 'RECHAZADO',
  PENDIENTE_METROLOGIA: 'PEND. METROLOGÍA',
  BLOQUEADO: 'BLOQUEADO',
};

// Show timer only when occupied (ocupado_por is non-null and non-empty)
const showTimer = spool.ocupado_por !== null && spool.ocupado_por !== '';

// Show PAUSADO badge when estado_trabajo is PAUSADO (no timer)
const isPausado = spool.estado_trabajo === 'PAUSADO';
```

### SpoolTable — disabledSpools prop integration

```typescript
// Source: existing SpoolTable.tsx — surgical addition
// In the row render:
const isDisabled = disabledSpools.includes(spool.tag_spool);
const isBlocked = tipo === 'reparacion' && (spool as unknown as { bloqueado?: boolean }).bloqueado;

// Combined disable: either disabled (already added) or blocked (reparacion)
const isInert = isDisabled || isBlocked;

// Disabled (already added) style: grey with opacity
// Blocked (reparacion) style: red with cursor-not-allowed
const rowClassName = isInert
  ? isBlocked
    ? 'bg-red-500/20 border-red-500 cursor-not-allowed'
    : 'bg-white/10 opacity-50 cursor-not-allowed'
  : isSelected
  ? 'bg-zeues-orange/20 cursor-pointer'
  : 'hover:bg-white/5 cursor-pointer';
```

### NotificationToast — complete minimal implementation

```typescript
// Source: useNotificationToast hook contract (zeues-frontend/hooks/useNotificationToast.ts)
import type { Toast } from '@/hooks/useNotificationToast';

interface NotificationToastProps {
  toasts: Toast[];
  onDismiss: (id: string) => void;
}

export function NotificationToast({ toasts, onDismiss }: NotificationToastProps) {
  // Container always in DOM for ARIA live region to be observed by screen readers
  return (
    <div
      aria-live="polite"
      aria-atomic="false"
      className="fixed top-4 right-4 z-[100] flex flex-col gap-2 pointer-events-none"
    >
      {toasts.map((toast) => (
        <div
          key={toast.id}
          role="alert"
          className={`
            pointer-events-auto
            flex items-center gap-3
            px-4 py-3
            border-4
            font-mono font-black text-sm
            ${toast.type === 'success'
              ? 'bg-zeues-navy border-green-400 text-green-400'
              : 'bg-zeues-navy border-red-400 text-red-400'
            }
          `}
        >
          <span className="flex-1">{toast.message}</span>
          <button
            onClick={() => onDismiss(toast.id)}
            aria-label="Cerrar notificación"
            className="text-current opacity-70 hover:opacity-100 focus:outline-none focus:ring-2 focus:ring-white focus:ring-inset"
          >
            ×
          </button>
        </div>
      ))}
    </div>
  );
}
```

---

## State of the Art

| Old Approach | Current Approach | Impact |
|--------------|------------------|--------|
| Multi-page navigation (9 pages) | Single page + modal stack (v5.0) | Phase 2 components are the visual building blocks of the new paradigm |
| Spool selection via SpoolTable (batch) | SpoolCardList (individual cards per tag) | SpoolCard is a new concept; SpoolCardList is a new container |
| No timer (state is static snapshot) | Live countdown timer via fecha_ocupacion | Timer only meaningful when `ocupado_por` non-null (D-07 decision) |
| Toast feedback via page navigation result | NotificationToast on main page post-API | Uses Phase 1 useNotificationToast hook |

---

## Open Questions

1. **Where does SpoolCard's onClick lead in Phase 2?**
   - What we know: Context says "Click triggers OperationModal (Phase 3)" — that modal doesn't exist yet in Phase 2
   - What's unclear: Should SpoolCard accept an `onClick: (spool: SpoolCardData) => void` callback prop (provided as no-op in Phase 2 tests, wired up in Phase 4)?
   - Recommendation: Yes — define `onCardClick: (spool: SpoolCardData) => void` as a required prop. Pass `jest.fn()` in tests. This avoids a breaking change when Phase 4 wires it up.

2. **SpoolCardList "remove spool" callback — where does it come from?**
   - What we know: CARD-06 requires individual removal; localStorage functions are in local-storage.ts
   - What's unclear: Does SpoolCardList own the remove button, or does SpoolCard?
   - Recommendation: Put "remove" (X) button on SpoolCard itself. Pass `onRemove: (tag: string) => void` down through SpoolCardList. This keeps each card self-contained.

3. **SpoolFilterPanel `showSelectionControls=false` — hide just TODOS/NINGUNO or also the selection counter?**
   - What we know: The prop is for AddSpool modal context
   - What's unclear: In AddSpool context, do we still show the "SELECCIONADOS: X / Y" counter?
   - Recommendation: `showSelectionControls=false` hides only the TODOS/NINGUNO/LIMPIAR row (the action buttons). Keep the counter visible — it's informational, not a control. Keeps the trigger bar unchanged.

---

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Framework | Jest 30 + @testing-library/react 16.3.2 |
| Config file | `zeues-frontend/jest.config.js` |
| Quick run command | `cd zeues-frontend && npx jest --testPathPatterns="SpoolCard\|SpoolCardList\|NotificationToast" --no-coverage` |
| Full suite command | `cd zeues-frontend && npx jest --no-coverage` |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| CARD-02 | SpoolCard renders TAG, operación, worker fields | unit | `npx jest --testPathPatterns="SpoolCard.test" -t "renders"` | ❌ Wave 0 |
| CARD-06 | SpoolCardList renders multiple cards; shows empty state | unit | `npx jest --testPathPatterns="SpoolCardList.test"` | ❌ Wave 0 |
| STATE-05 | Timer renders when ocupado_por non-null; shows elapsed text | unit | `npx jest --testPathPatterns="SpoolCard.test" -t "timer"` | ❌ Wave 0 |
| STATE-06 | PAUSADO badge visible; timer NOT rendered | unit | `npx jest --testPathPatterns="SpoolCard.test" -t "PAUSADO"` | ❌ Wave 0 |
| MODAL-07 | NotificationToast renders role=alert; success/error variants | unit | `npx jest --testPathPatterns="NotificationToast.test"` | ❌ Wave 0 |
| UX-01 | disabledSpools rows get aria-disabled + tabIndex=-1 + grey style | unit | `npx jest --testPathPatterns="SpoolTable.test" -t "disabled"` | ✅ (add cases) |
| UX-02 | Toast auto-dismiss already covered in useNotificationToast tests | unit | (already passing, 10 tests) | ✅ |
| UX-04 | Components use zeues-navy/zeues-orange class tokens | unit/axe | `npx jest --testPathPatterns="SpoolCard.test" -t "a11y"` | ❌ Wave 0 |

### Sampling Rate
- **Per task commit:** `cd zeues-frontend && npx jest --testPathPatterns="<affected-test>" --no-coverage`
- **Per wave merge:** `cd zeues-frontend && npx jest --no-coverage`
- **Phase gate:** Full suite green + `npx tsc --noEmit` + `npm run lint` before `/gsd:verify-work`

### Wave 0 Gaps

- [ ] `zeues-frontend/__tests__/components/NotificationToast.test.tsx` — covers MODAL-07, UX-02 rendering
- [ ] `zeues-frontend/__tests__/components/SpoolCard.test.tsx` — covers CARD-02, STATE-05, STATE-06, UX-04
- [ ] `zeues-frontend/__tests__/components/SpoolCardList.test.tsx` — covers CARD-06

Existing test files that need new test cases added (not new files):
- [ ] `zeues-frontend/__tests__/components/SpoolTable.test.tsx` — add `disabledSpools` suite (UX-01)
- [ ] `zeues-frontend/__tests__/components/SpoolFilterPanel.test.tsx` — add `showSelectionControls` suite

---

## Sources

### Primary (HIGH confidence)
- Direct code inspection: `zeues-frontend/components/Modal.tsx` — current ESC handler pattern confirmed
- Direct code inspection: `zeues-frontend/components/SpoolTable.tsx` — current props + bloqueado pattern confirmed
- Direct code inspection: `zeues-frontend/components/SpoolFilterPanel.tsx` — current props (13) confirmed
- Direct code inspection: `zeues-frontend/hooks/useNotificationToast.ts` — Toast interface, enqueue/dismiss API confirmed
- Direct code inspection: `zeues-frontend/hooks/useModalStack.ts` — ModalId type, stack API confirmed
- Direct code inspection: `zeues-frontend/lib/types.ts` — SpoolCardData (12 fields), EstadoTrabajo (7 literals) confirmed
- Direct code inspection: `zeues-frontend/lib/spool-state-machine.ts` — getValidOperations, getValidActions confirmed
- Direct code inspection: `zeues-frontend/tailwind.config.ts` — zeues-navy, zeues-orange, km-orange token names confirmed
- Direct code inspection: `zeues-frontend/package.json` — all test dependencies confirmed installed
- Direct code inspection: Phase 1 SUMMARYs (01-01, 01-02, 01-03) — confirmed what was built and the decisions made

### Secondary (MEDIUM confidence)
- CLAUDE.md project instructions — WCAG 2.1 AA requirements, Blueprint palette, mobile-first, no emojis
- .claude/skills/ui-ux/SKILL.md — Industrial Professional design patterns, touch target minimums (h-16)
- CONTEXT.md decisions — locked implementation choices for each component

### Tertiary (LOW confidence — none)

No LOW confidence findings in this phase. Everything is verifiable from the existing codebase.

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — all packages confirmed in package.json; no new deps needed
- Architecture patterns: HIGH — inferred directly from existing component code and Phase 1 deliverables
- Pitfalls: HIGH — fecha_ocupacion format verified from CLAUDE.md date standards; ESC issue verified by reading Modal.tsx source; others are standard React patterns

**Research date:** 2026-03-10
**Valid until:** 2026-04-10 (stable — no fast-moving ecosystem; all internal to project)
