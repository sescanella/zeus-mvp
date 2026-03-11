# Phase 1: Frontend — Fundaciones - Research

**Researched:** 2026-03-10
**Domain:** TypeScript utility libraries, React hooks, localStorage, state machine patterns, API client integration (Next.js 14 + React 18)
**Confidence:** HIGH

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| CARD-01 | Botón "Añadir Spool" abre modal con SpoolTable + filtros | SpoolCardData interface feeds modal display; localStorage tags enable "already added" filtering |
| CARD-02 | Cards muestran: TAG, operación actual, acción, worker, tiempo en estado | SpoolCardData must include operacion_actual, estado_trabajo, ocupado_por, fecha_ocupacion |
| CARD-03 | Spools persisten en localStorage (solo tag_spool), estado se refresca 30s | local-storage.ts handles tags array; batchGetStatus API call drives refresh |
| CARD-04 | MET APROBADA remueve spool del listado | estado_trabajo = "COMPLETADO" after APROBADO → remove from localStorage list |
| CARD-05 | MET RECHAZADA mantiene spool para ir a Reparación | estado_trabajo = "RECHAZADO" → keep in list |
| CARD-06 | Múltiples spools, operar individualmente | useModalStack provides per-spool modal context |
| MODAL-01 | Click en card → OperationModal filtrado por estado | getValidOperations(spoolStatus) determines options |
| MODAL-02 | ARM/SOLD/REP → ActionModal filtrado por estado | getValidActions(spoolStatus) determines options |
| MODAL-03 | INICIAR/FINALIZAR/PAUSAR → WorkerModal filtrado por rol | API getWorkers + client-side role filter |
| MODAL-04 | CANCELAR no requiere worker — vuelve directo | getValidActions distinguishes CANCELAR as no-worker path |
| MODAL-05 | MET → MetrologiaModal (APROBADA/RECHAZADA) | Separate modal path for MET |
| MODAL-06 | Al seleccionar worker → API call → vuelve a pantalla | useModalStack.clear() after API success |
| MODAL-07 | NotificationToast feedback éxito/error | useNotificationToast enqueues messages |
| MODAL-08 | Eliminamos selección de uniones — PAUSAR reemplaza | PAUSAR uses action_override, no union selection needed |
| STATE-01 | Operaciones válidas dependen del estado del spool | getValidOperations() maps estado_trabajo → operation list |
| STATE-02 | Acciones válidas dependen del estado de ocupación | getValidActions() maps ocupado_por → action list |
| STATE-03 | CANCELAR en spool libre = quitar del listado (frontend-only) | Detected via ocupado_por == null |
| STATE-04 | CANCELAR en spool activo = reset operación backend + quitar | API call to cancel endpoint, then remove from localStorage |
| STATE-05 | Timer solo cuando spool está ocupado (Fecha_Ocupacion) | SpoolCardData.fecha_ocupacion non-null = timer active |
| STATE-06 | Spools PAUSADOS muestran badge estático sin timer | estado_trabajo = "PAUSADO" + ocupado_por null = no timer |
| UX-01 | Modal "Añadir Spool" muestra ya-añadidos como deshabilitados | localStorage tags set passed to SpoolTable as disabledSpools |
| UX-02 | Notificaciones toast auto-dismiss (3-5 segundos) | useNotificationToast implements auto-dismiss timer |
| UX-03 | No optimistic updates — loading spinner, esperar API | API functions return promises; no state pre-update |
| UX-04 | Mantener paleta Blueprint Industrial + mobile-first | Existing Tailwind config/classes unchanged |
</phase_requirements>

---

## Summary

Phase 1 creates the pure utility layer for ZEUES v5.0: TypeScript interfaces, localStorage persistence, a frontend state machine, the `parseEstadoDetalle` parser, two React hooks, and new API client functions. None of these artifacts render UI — they are the data and logic foundation that Phases 2, 3, and 4 build on top of.

The backend already provides the computed fields (`operacion_actual`, `estado_trabajo`, `ciclo_rep`) through `GET /api/spool/{tag}/status` and `POST /api/spools/batch-status` (both completed in Phase 0). The frontend parser (`lib/parse-estado-detalle.ts`) must mirror the backend `parse_estado_detalle()` logic in TypeScript, so both layers agree on how to interpret Estado_Detalle strings. The authoritative list of Estado_Detalle formats lives in `backend/services/estado_detalle_parser.py`.

The two hooks (`useModalStack`, `useNotificationToast`) are pure React hooks with no external library dependencies — the project uses only React 18 + Next.js 14 + Tailwind, with no state management library. All hooks must follow the existing pattern established in `hooks/useDebounce.ts` (simple `useState`/`useCallback`/`useEffect` composition, no third-party hooks).

**Primary recommendation:** Mirror the backend parser exactly, keep hooks dependency-free, use `unknown` instead of `any` in all TypeScript, and scope localStorage under a single versioned key to avoid stale data from previous app versions.

---

## Standard Stack

### Core (already installed — no new packages needed)

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| React | ^18.3.0 | Hooks (`useState`, `useEffect`, `useCallback`, `useRef`) | Already in project |
| TypeScript | ^5.4.0 | Type safety, `strict: true` enforced in tsconfig | Already in project |
| Next.js | ^14.2.0 | App Router environment; `'use client'` required for hooks | Already in project |

### No New Dependencies

Phase 1 adds zero npm packages. All required primitives are:
- `localStorage` (browser API)
- React hooks (`useState`, `useEffect`, `useCallback`, `useRef`)
- `fetch` (already used in `lib/api.ts`)
- Standard TypeScript

**Installation:** None required.

---

## Architecture Patterns

### Recommended File Structure for Phase 1

```
zeues-frontend/
├── lib/
│   ├── types.ts               # EXTEND: add SpoolCardData interface
│   ├── api.ts                 # EXTEND: add getSpoolStatus, batchGetStatus
│   ├── local-storage.ts       # NEW: saveTags, loadTags, removeTag
│   ├── spool-state-machine.ts # NEW: getValidOperations, getValidActions
│   ├── parse-estado-detalle.ts # NEW: parseEstadoDetalle (TS mirror of backend)
│   └── (existing files unchanged)
└── hooks/
    ├── useDebounce.ts         # EXISTING (reference pattern)
    ├── useModalStack.ts       # NEW: push/pop/clear stack management
    └── useNotificationToast.ts # NEW: enqueue/dismiss notification queue
```

### Pattern 1: SpoolCardData Interface (Task 1.1)

**What:** Extend `lib/types.ts` with a new interface that represents the data shape needed to render a spool card. This is the contract between the API response and UI components.

**When to use:** Used by every component that displays a spool card (Phase 2+).

**Key insight:** `SpoolCardData` maps 1:1 to `SpoolStatus` from the backend — it IS the API response type for the batch-status endpoint. Do not duplicate fields; re-use or alias.

```typescript
// Source: backend/models/spool_status.py (SpoolStatus model)
// SpoolCardData is the frontend representation of SpoolStatus

export type EstadoTrabajo =
  | 'LIBRE'
  | 'EN_PROGRESO'
  | 'PAUSADO'
  | 'COMPLETADO'
  | 'RECHAZADO'
  | 'BLOQUEADO'
  | 'PENDIENTE_METROLOGIA';

export type OperacionActual = 'ARM' | 'SOLD' | 'REPARACION' | null;

export interface SpoolCardData {
  tag_spool: string;
  ocupado_por: string | null;
  fecha_ocupacion: string | null;   // "DD-MM-YYYY HH:MM:SS" format
  estado_detalle: string | null;    // raw string, kept for debugging
  total_uniones: number | null;
  uniones_arm_completadas: number | null;
  uniones_sold_completadas: number | null;
  pulgadas_arm: number | null;
  pulgadas_sold: number | null;
  // Computed by backend (from parse_estado_detalle)
  operacion_actual: OperacionActual;
  estado_trabajo: EstadoTrabajo | null;
  ciclo_rep: number | null;         // 1-3 for RECHAZADO/REPARACION, null otherwise
}
```

### Pattern 2: localStorage Persistence (Task 1.2)

**What:** Thin wrapper over `localStorage` that stores the ordered list of spool tags. Only tags are persisted — state is always fetched from backend.

**When to use:** Called from Phase 4's `SpoolListContext` to persist/restore the user's spool list.

**Critical:** localStorage is only available client-side. All access must be wrapped in `typeof window !== 'undefined'` guards (Next.js SSR compatibility).

```typescript
// lib/local-storage.ts

const STORAGE_KEY = 'zeues_v5_spool_tags';  // versioned key

export function loadTags(): string[] {
  if (typeof window === 'undefined') return [];
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (!raw) return [];
    const parsed: unknown = JSON.parse(raw);
    if (!Array.isArray(parsed)) return [];
    return parsed.filter((t): t is string => typeof t === 'string');
  } catch {
    return [];
  }
}

export function saveTags(tags: string[]): void {
  if (typeof window === 'undefined') return;
  localStorage.setItem(STORAGE_KEY, JSON.stringify(tags));
}

export function addTag(tag: string): string[] {
  const current = loadTags();
  if (current.includes(tag)) return current;
  const updated = [...current, tag];
  saveTags(updated);
  return updated;
}

export function removeTag(tag: string): string[] {
  const updated = loadTags().filter(t => t !== tag);
  saveTags(updated);
  return updated;
}

export function clearTags(): void {
  if (typeof window === 'undefined') return;
  localStorage.removeItem(STORAGE_KEY);
}
```

### Pattern 3: Spool State Machine (Task 1.3)

**What:** Pure functions that map spool state → valid operations/actions. No class, no framework — just data transformation.

**State logic (from REQUIREMENTS.md STATE-01, STATE-02):**

```typescript
// lib/spool-state-machine.ts

import { SpoolCardData, EstadoTrabajo, OperacionActual } from './types';

export type Operation = 'ARM' | 'SOLD' | 'MET' | 'REP';
export type Action = 'INICIAR' | 'FINALIZAR' | 'PAUSAR' | 'CANCELAR';

// STATE-01: Valid operations by estado_trabajo
export function getValidOperations(spool: SpoolCardData): Operation[] {
  const estado = spool.estado_trabajo;
  const operacion = spool.operacion_actual;

  switch (estado) {
    case 'LIBRE':
      return ['ARM'];
    case 'PAUSADO':
      // ARM pausado → can continue ARM or start SOLD if ARM done
      if (operacion === 'ARM') return ['ARM'];
      if (operacion === null) return ['SOLD']; // ARM completado, SOLD pausado
      return [];
    case 'EN_PROGRESO':
      // Occupied — same operation continues
      if (operacion === 'ARM') return ['ARM'];
      if (operacion === 'SOLD') return ['SOLD'];
      if (operacion === 'REPARACION') return ['REP'];
      return [];
    case 'COMPLETADO':
      // Both ARM+SOLD done → MET
      return ['MET'];
    case 'PENDIENTE_METROLOGIA':
      return ['MET'];
    case 'RECHAZADO':
      return ['REP'];
    case 'BLOQUEADO':
      return [];
    default:
      return [];
  }
}

// STATE-02: Valid actions by occupation state
export function getValidActions(spool: SpoolCardData): Action[] {
  const isOccupied = spool.ocupado_por !== null && spool.ocupado_por !== '';

  if (isOccupied) {
    // En progreso → FINALIZAR / PAUSAR / CANCELAR
    return ['FINALIZAR', 'PAUSAR', 'CANCELAR'];
  } else {
    // Libre → INICIAR / CANCELAR
    return ['INICIAR', 'CANCELAR'];
  }
}
```

**Note on ARM-COMPLETADO / SOLD state:** The mapping `ARM-COMPLETADO → SOLD` and `ARM-PAUSADO → SOLD` requires checking both `estado_trabajo` and `operacion_actual`. The state machine above covers these transitions.

### Pattern 4: parseEstadoDetalle (Task 1.4)

**What:** TypeScript port of `backend/services/estado_detalle_parser.py`. Must produce identical output for identical input.

**All known Estado_Detalle formats (source: `backend/services/estado_detalle_parser.py`):**

| Input pattern | operacion_actual | estado_trabajo | ciclo_rep |
|---------------|-----------------|----------------|-----------|
| `null` or `""` | null | "LIBRE" | null |
| `"MR(93) trabajando ARM (...)"` | "ARM" | "EN_PROGRESO" | null |
| `"MR(93) trabajando SOLD (...)"` | "SOLD" | "EN_PROGRESO" | null |
| `"EN_REPARACION (Ciclo N/3) - Ocupado: MR(93)"` | "REPARACION" | "EN_PROGRESO" | N |
| `"BLOQUEADO - Contactar supervisor"` | null | "BLOQUEADO" | null |
| `"RECHAZADO (Ciclo N/3) - ..."` | null | "RECHAZADO" | N |
| `"RECHAZADO"` (bare) | null | "RECHAZADO" | null |
| `"REPARACION completado - PENDIENTE_METROLOGIA"` | null | "PENDIENTE_METROLOGIA" | null |
| `"... METROLOGIA APROBADO ✓"` | null | "COMPLETADO" | null |
| `"... ARM completado, SOLD completado"` | null | "COMPLETADO" | null |
| `"ARM completado, SOLD pendiente"` | "ARM" | "PAUSADO" | null |
| `"ARM completado, SOLD pausado"` | "ARM" | "PAUSADO" | null |
| `"ARM pausado"` | "ARM" | "PAUSADO" | null |

**CRITICAL pattern match order** (must match backend exactly — order matters):
1. Occupied ARM/SOLD (`trabajando ARM/SOLD`)
2. REPARACION in progress (`EN_REPARACION.*Ciclo`)
3. BLOQUEADO (keyword)
4. RECHAZADO with cycle (`RECHAZADO.*Ciclo`)
5. RECHAZADO bare (keyword)
6. PENDIENTE_METROLOGIA (keyword)
7. METROLOGIA APROBADO (keyword + ✓)
8. Both ARM + SOLD completado
9. ARM completado + SOLD pendiente/pausado
10. ARM pausado
11. Default → LIBRE

```typescript
// lib/parse-estado-detalle.ts

import { EstadoTrabajo, OperacionActual } from './types';

export interface ParsedEstadoDetalle {
  operacion_actual: OperacionActual;
  estado_trabajo: EstadoTrabajo;
  ciclo_rep: number | null;
  worker: string | null;
}

export function parseEstadoDetalle(estado: string | null | undefined): ParsedEstadoDetalle {
  const defaultResult: ParsedEstadoDetalle = {
    operacion_actual: null,
    estado_trabajo: 'LIBRE',
    ciclo_rep: null,
    worker: null,
  };

  if (!estado || !estado.trim()) return defaultResult;
  const s = estado.trim();

  // 1. Occupied ARM/SOLD
  const ocupadoMatch = s.match(/^(\S+)\s+trabajando\s+(ARM|SOLD)\s+/);
  if (ocupadoMatch) {
    return { ...defaultResult, worker: ocupadoMatch[1], operacion_actual: ocupadoMatch[2] as 'ARM' | 'SOLD', estado_trabajo: 'EN_PROGRESO' };
  }

  // 2. REPARACION en progreso
  const repMatch = s.match(/EN_REPARACION.*?Ciclo\s+(\d+)\/3/);
  if (repMatch) {
    return { ...defaultResult, operacion_actual: 'REPARACION', estado_trabajo: 'EN_PROGRESO', ciclo_rep: parseInt(repMatch[1], 10) };
  }

  // 3. BLOQUEADO
  if (s.includes('BLOQUEADO')) {
    return { ...defaultResult, estado_trabajo: 'BLOQUEADO' };
  }

  // 4. RECHAZADO con ciclo
  const rechazadoCicloMatch = s.match(/RECHAZADO.*?Ciclo\s+(\d+)\/3/);
  if (rechazadoCicloMatch) {
    return { ...defaultResult, estado_trabajo: 'RECHAZADO', ciclo_rep: parseInt(rechazadoCicloMatch[1], 10) };
  }

  // 5. RECHAZADO bare
  if (s.includes('RECHAZADO')) {
    return { ...defaultResult, estado_trabajo: 'RECHAZADO' };
  }

  // 6. PENDIENTE_METROLOGIA
  if (s.includes('PENDIENTE_METROLOGIA') || s.includes('REPARACION completado')) {
    return { ...defaultResult, estado_trabajo: 'PENDIENTE_METROLOGIA' };
  }

  // 7. METROLOGIA APROBADO
  if (s.includes('METROLOGIA APROBADO') || s.includes('APROBADO \u2713')) {
    return { ...defaultResult, estado_trabajo: 'COMPLETADO' };
  }

  // 8. ARM + SOLD completado
  if (s.includes('ARM completado') && s.includes('SOLD completado')) {
    return { ...defaultResult, estado_trabajo: 'COMPLETADO' };
  }

  // 9. ARM completado, SOLD pendiente/pausado
  if (s.includes('ARM completado') && (s.includes('SOLD pendiente') || s.includes('SOLD pausado'))) {
    return { ...defaultResult, estado_trabajo: 'PAUSADO', operacion_actual: 'ARM' };
  }

  // 10. ARM pausado
  if (s.includes('ARM pausado')) {
    return { ...defaultResult, estado_trabajo: 'PAUSADO', operacion_actual: 'ARM' };
  }

  // Default
  return defaultResult;
}
```

### Pattern 5: useModalStack (Task 1.5)

**What:** A React hook that manages an ordered stack of modal identifiers. Used to implement the multi-step modal flow (Card → Operation → Action → Worker).

**Design:** Stack entries are typed strings identifying which modal to show. The hook returns the current top-of-stack and push/pop/clear operations.

```typescript
// hooks/useModalStack.ts
'use client';

import { useState, useCallback } from 'react';

export type ModalId =
  | 'add-spool'
  | 'operation'
  | 'action'
  | 'worker'
  | 'metrologia';

export interface UseModalStackReturn {
  stack: ModalId[];
  current: ModalId | null;     // top of stack (last element)
  push: (modal: ModalId) => void;
  pop: () => void;
  clear: () => void;
  isOpen: (modal: ModalId) => boolean;
}

export function useModalStack(): UseModalStackReturn {
  const [stack, setStack] = useState<ModalId[]>([]);

  const push = useCallback((modal: ModalId) => {
    setStack(prev => [...prev, modal]);
  }, []);

  const pop = useCallback(() => {
    setStack(prev => prev.slice(0, -1));
  }, []);

  const clear = useCallback(() => {
    setStack([]);
  }, []);

  const current = stack.length > 0 ? stack[stack.length - 1] : null;

  const isOpen = useCallback((modal: ModalId) => {
    return stack[stack.length - 1] === modal;
  }, [stack]);

  return { stack, current, push, pop, clear, isOpen };
}
```

**Key behaviors:**
- `push` adds to top (never duplicates protection is Phase 3's responsibility)
- `pop` removes top only — ESC key behavior in Phase 2's Modal.tsx modification
- `clear` collapses entire stack on success or explicit close
- `isOpen(modal)` returns true only for the TOP modal (prevents rendering buried modals as "open")

### Pattern 6: useNotificationToast (Task 1.6)

**What:** A hook that manages a queue of toast notifications with auto-dismiss. No third-party library.

```typescript
// hooks/useNotificationToast.ts
'use client';

import { useState, useCallback, useRef } from 'react';

export type ToastType = 'success' | 'error';

export interface Toast {
  id: string;
  message: string;
  type: ToastType;
}

export interface UseNotificationToastReturn {
  toasts: Toast[];
  enqueue: (message: string, type: ToastType) => void;
  dismiss: (id: string) => void;
}

const AUTO_DISMISS_MS = 4000;  // 4s — within UX-02 spec (3-5s)

export function useNotificationToast(): UseNotificationToastReturn {
  const [toasts, setToasts] = useState<Toast[]>([]);
  const counterRef = useRef(0);

  const dismiss = useCallback((id: string) => {
    setToasts(prev => prev.filter(t => t.id !== id));
  }, []);

  const enqueue = useCallback((message: string, type: ToastType) => {
    const id = `toast-${Date.now()}-${counterRef.current++}`;
    const toast: Toast = { id, message, type };
    setToasts(prev => [...prev, toast]);
    setTimeout(() => {
      setToasts(prev => prev.filter(t => t.id !== id));
    }, AUTO_DISMISS_MS);
  }, []);

  return { toasts, enqueue, dismiss };
}
```

**Note:** `dismiss` is also exported for Phase 2's NotificationToast.tsx to allow manual early dismiss.

### Pattern 7: New API Functions (Task 1.7)

**What:** Add `getSpoolStatus` and `batchGetStatus` to `lib/api.ts`. These wrap the backend endpoints built in Phase 0.

**Import addition required:** `SpoolCardData` from `./types`.

```typescript
// Additions to lib/api.ts — import SpoolCardData from './types'

// GET /api/spool/{tag}/status (API-01)
export async function getSpoolStatus(tag: string): Promise<SpoolCardData> {
  const res = await fetch(`${API_URL}/api/spool/${tag}/status`, {
    method: 'GET',
    headers: { 'Content-Type': 'application/json' },
  });
  return handleResponse<SpoolCardData>(res);
}

// POST /api/spools/batch-status (API-02)
export async function batchGetStatus(tags: string[]): Promise<SpoolCardData[]> {
  const res = await fetch(`${API_URL}/api/spools/batch-status`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ tags }),
  });
  const data = await handleResponse<{ spools: SpoolCardData[]; total: number }>(res);
  return data.spools;
}
```

**Note:** These functions do NOT wrap errors in a user-friendly string — they let `ApiError` propagate. The modal layer (Phase 3) handles display.

### Anti-Patterns to Avoid

- **`any` type in TypeScript:** CLAUDE.md forbids it. Use `unknown` for dynamic data, exact types for known shapes.
- **Accessing localStorage without SSR guard:** Next.js renders server-side. Always check `typeof window !== 'undefined'`.
- **Storing full spool objects in localStorage:** Decision D-02 is explicit — store only `tag_spool` strings. State is always fetched from backend.
- **`useEffect` with missing deps:** The linter will catch this, and builds will fail. Always specify complete dependency arrays.
- **Mutable state in hooks:** `useModalStack` and `useNotificationToast` must use functional state updates (`prev => ...`) to avoid stale closures.
- **Duplicating parse logic:** `parseEstadoDetalle` in the frontend must mirror the backend exactly. If the backend adds a new Estado_Detalle format, both files must be updated together.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Toast auto-dismiss timer | Custom timer manager | `setTimeout` inside `useNotificationToast.enqueue` | Sufficient for single-instance toast queue |
| State machine framework | XState or custom FSM | Pure functions in `spool-state-machine.ts` | Only 7 states, 2 operations — no state machine library needed |
| localStorage serialization | Custom binary format | `JSON.stringify`/`JSON.parse` with type guard | Already sufficient for string arrays |
| Unique ID generation for toasts | UUID library | `Date.now() + counter ref` | No collision risk for single-tab single-user app |

**Key insight:** This is a single-user, single-tab app with simple state. Over-engineering with state machine libraries or global state managers would add complexity with no benefit.

---

## Common Pitfalls

### Pitfall 1: localStorage SSR Crash
**What goes wrong:** `localStorage is not defined` error during Next.js server-side rendering.
**Why it happens:** Next.js runs component initialization code on the server where `window` does not exist.
**How to avoid:** Every `localStorage` access in `lib/local-storage.ts` must check `typeof window !== 'undefined'` first, or return empty defaults.
**Warning signs:** Build error `ReferenceError: localStorage is not defined`.

### Pitfall 2: parseEstadoDetalle Pattern Order Mismatch
**What goes wrong:** A spool shows wrong `estado_trabajo` or `operacion_actual` — e.g., an ARM-in-progress spool shows as LIBRE.
**Why it happens:** The regex match order in the frontend `parseEstadoDetalle` differs from the backend. The backend uses early returns, so order matters.
**How to avoid:** Follow the exact 10-step order documented in Pattern 4. Tests must cover all known Estado_Detalle format strings.
**Warning signs:** SpoolCard shows wrong badge or timer for a spool that has a non-null `estado_detalle`.

### Pitfall 3: useModalStack ESC behavior regression
**What goes wrong:** ESC closes ALL modals instead of just the top one.
**Why it happens:** Phase 2 will modify `Modal.tsx` to respect `useModalStack`. If `clear()` is connected to ESC instead of `pop()`, all modals close.
**How to avoid:** Export `pop` (for ESC key → close top) and `clear` (for success → close all) as separate functions. Document in the hook.

### Pitfall 4: Toast duplicate IDs on fast consecutive calls
**What goes wrong:** Two toasts appear but only one dismisses properly.
**Why it happens:** Using only `Date.now()` for ID generation — two calls in the same millisecond produce the same ID.
**How to avoid:** Combine `Date.now()` with a `useRef` counter (see Pattern 6). This is safe for single-tab apps.

### Pitfall 5: SpoolCardData ≠ SpoolStatus field naming mismatch
**What goes wrong:** `getSpoolStatus()` returns data but TypeScript reports field not found.
**Why it happens:** Backend Python model uses `operacion_actual` (snake_case), frontend must use same naming. If frontend interface uses camelCase, the mapping breaks.
**How to avoid:** Keep `SpoolCardData` in snake_case matching the API response exactly. Do not camelCase-convert in the API client.

### Pitfall 6: Stale localStorage after v4.0 → v5.0 upgrade
**What goes wrong:** App loads and tries to restore an old spool list that was stored under a different key format.
**Why it happens:** If a prior version used a different localStorage key, loading it produces unexpected data.
**How to avoid:** Use the versioned key `zeues_v5_spool_tags`. The `loadTags` function includes a type guard that rejects non-string-array content and returns `[]`.

---

## Code Examples

### Existing hook pattern to follow (from `hooks/useDebounce.ts`)

```typescript
// Source: zeues-frontend/hooks/useDebounce.ts (existing reference)
'use client';
import { useState, useEffect } from 'react';

export function useDebounce<T>(value: T, delay = 500): T {
  const [debouncedValue, setDebouncedValue] = useState<T>(value);

  useEffect(() => {
    const timer = setTimeout(() => setDebouncedValue(value), delay);
    return () => clearTimeout(timer);
  }, [value, delay]);

  return debouncedValue;
}
```

**Pattern:** Named export, `'use client'` directive, generic typed, no external deps.

### Existing API pattern to follow (from `lib/api.ts`)

```typescript
// Source: zeues-frontend/lib/api.ts — handleResponse helper (existing)
async function handleResponse<T>(response: Response): Promise<T> {
  if (!response.ok) {
    const errorData = await response.json().catch(() => ({}));
    const message = errorData.message || errorData.detail || `Error ${response.status}: ${response.statusText}`;
    const detail = typeof errorData.detail === 'string' ? errorData.detail : errorData.detail?.message;
    throw new ApiError(response.status, message, detail);
  }
  return response.json();
}
```

**Pattern:** New API functions reuse this helper — no custom error handling in `getSpoolStatus`/`batchGetStatus`.

---

## State of the Art

| Old Approach | Current Approach | Impact |
|--------------|------------------|--------|
| Multi-page navigation (P1-P6) | Single page + modal stack | Phase 1 utilities are the foundation for this change |
| `context.tsx` stores all flow state (worker, operation, spool, unions) | Per-hook state (`useModalStack`, `useNotificationToast`) + localStorage | Old context remains until Phase 5 cleanup |
| Union selection page (seleccionar-uniones) | action_override=PAUSAR in FINALIZAR | Phase 1 API functions use new v5.0 endpoint signature |
| `sessionStorage` for union selection | No session storage needed | Phase 1 does not use sessionStorage at all |

**Deprecated (from TODO-v5-restructuring.md — to be removed in Phase 5):**
- `lib/context.tsx` `accion`, `selectedUnions`, `pulgadasCompletadas` fields — not needed in v5.0
- `lib/spool-selection-utils.ts` — entire file removed in Phase 5

---

## Open Questions

1. **getValidOperations: ARM-COMPLETADO / SOLD-PAUSADO disambiguation**
   - What we know: `estado_trabajo = "PAUSADO"` + `operacion_actual = "ARM"` can mean either "ARM is paused mid-work" OR "ARM is fully complete but stored as PAUSADO pending SOLD"
   - What's unclear: The REQUIREMENTS.md maps `ARM-PAUSADO → SOLD` and `ARM-COMPLETADO → SOLD` both to SOLD. But the `parseEstadoDetalle` output for "ARM completado, SOLD pendiente" sets `estado_trabajo = "PAUSADO"` and `operacion_actual = "ARM"`. The state machine would show ARM as the valid operation.
   - Recommendation: Use `uniones_arm_completadas` vs `total_uniones` to distinguish "ARM fully done" from "ARM partially paused". If `uniones_arm_completadas == total_uniones`, offer SOLD; else offer ARM. This uses already-available SpoolCardData fields. Resolve in planning.

2. **IniciarRequest still has worker_nombre field**
   - What we know: Plan 00-03 made `worker_nombre` optional in backend. `lib/types.ts` `IniciarRequest` still declares it as `string` (required).
   - What's unclear: Should the frontend type be updated to `worker_nombre?: string` in Phase 1 (Task 1.1) or left for Phase 3/4?
   - Recommendation: Update `IniciarRequest` in types.ts to `worker_nombre?: string` in Task 1.1 to match the current backend contract.

---

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Framework | Jest 30.2.0 + @testing-library/react 16.3.2 |
| Config file | `zeues-frontend/jest.config.js` |
| Quick run command | `cd zeues-frontend && npm test -- --testPathPattern="local-storage|spool-state-machine|parse-estado-detalle|useModalStack|useNotificationToast" --no-coverage` |
| Full suite command | `cd zeues-frontend && npm test` |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| STATE-01 | getValidOperations returns correct operations per estado_trabajo | unit | `npm test -- --testPathPattern="spool-state-machine"` | ❌ Wave 0 |
| STATE-02 | getValidActions returns INICIAR+CANCELAR (libre) or FINALIZAR+PAUSAR+CANCELAR (ocupado) | unit | `npm test -- --testPathPattern="spool-state-machine"` | ❌ Wave 0 |
| STATE-03 | getValidActions identifies CANCELAR on libre spool via ocupado_por==null | unit | `npm test -- --testPathPattern="spool-state-machine"` | ❌ Wave 0 |
| CARD-03 | loadTags/saveTags/addTag/removeTag round-trip correctly | unit | `npm test -- --testPathPattern="local-storage"` | ❌ Wave 0 |
| CARD-03 | loadTags returns [] when localStorage empty or malformed | unit | `npm test -- --testPathPattern="local-storage"` | ❌ Wave 0 |
| CARD-03 | SSR guard: loadTags/saveTags are no-ops when window undefined | unit | `npm test -- --testPathPattern="local-storage"` | ❌ Wave 0 |
| STATE-01 | parseEstadoDetalle produces correct output for all 11 known formats | unit | `npm test -- --testPathPattern="parse-estado-detalle"` | ❌ Wave 0 |
| MODAL-01/02 | useModalStack push/pop/clear/isOpen correct behavior | unit | `npm test -- --testPathPattern="useModalStack"` | ❌ Wave 0 |
| MODAL-07 | useNotificationToast enqueue adds toast, auto-dismiss removes it | unit | `npm test -- --testPathPattern="useNotificationToast"` | ❌ Wave 0 |
| UX-02 | useNotificationToast auto-dismiss fires within 3-5s | unit (fake timers) | `npm test -- --testPathPattern="useNotificationToast"` | ❌ Wave 0 |

### Sampling Rate

- **Per task commit:** Quick run targeting changed file's test pattern
- **Per wave merge:** `cd zeues-frontend && npm test && npx tsc --noEmit`
- **Phase gate:** Full suite green + `tsc --noEmit` + `npm run lint` before `/gsd:verify-work`

### Wave 0 Gaps

All test files are new (Phase 1 creates new files):

- [ ] `__tests__/lib/local-storage.test.ts` — covers CARD-03 localStorage persistence
- [ ] `__tests__/lib/spool-state-machine.test.ts` — covers STATE-01, STATE-02, STATE-03
- [ ] `__tests__/lib/parse-estado-detalle.test.ts` — covers all 11 Estado_Detalle formats
- [ ] `__tests__/hooks/useModalStack.test.ts` — covers MODAL-01, MODAL-02, push/pop/clear
- [ ] `__tests__/hooks/useNotificationToast.test.ts` — covers MODAL-07, UX-02

Existing infrastructure (`jest.config.js`, `jest.setup.js`, `@testing-library/react`) is sufficient — no new framework setup required.

---

## Sources

### Primary (HIGH confidence)

- `backend/services/estado_detalle_parser.py` — Complete list of Estado_Detalle formats with exact regex patterns. Frontend parser must mirror this exactly.
- `backend/models/spool_status.py` — SpoolStatus Pydantic model defines the exact JSON response shape for `SpoolCardData` interface.
- `backend/services/cycle_counter_service.py` — CycleCounterService documents all Estado_Detalle string formats for RECHAZADO/BLOQUEADO/REPARACION states.
- `zeues-frontend/lib/types.ts` — Existing type contracts; `SpoolCardData` extends the Spool model pattern.
- `zeues-frontend/lib/api.ts` — Established API client pattern (`handleResponse`, `ApiError`); new functions follow this pattern.
- `zeues-frontend/hooks/useDebounce.ts` — Reference implementation for hook pattern (structure, exports, 'use client').
- `zeues-frontend/jest.config.js` + `jest.setup.js` — Test infrastructure already in place; `__tests__/` is the correct location.
- `.planning/v5.0-single-page/REQUIREMENTS.md` — STATE-01/02 decision maps, decision table (D-01 through D-09).

### Secondary (MEDIUM confidence)

- `zeues-frontend/package.json` — Confirmed React 18.3.0, Next.js 14.2.0, TypeScript 5.4.0, Jest 30.2.0. No new packages needed.
- `zeues-frontend/tsconfig.json` — `strict: true` enforced, `@/*` path alias configured, `__tests__/` excluded from tsc.
- `zeues-frontend/TODO-v5-restructuring.md` — Documents known tech debt; SSR guard issue and `any` type restrictions confirmed.

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — package.json confirms all versions, no new deps needed
- Architecture: HIGH — backend parser source is authoritative, API response shape confirmed in spool_status.py
- Pitfalls: HIGH — SSR guard and parser order verified from existing code and TODO doc
- State machine logic: HIGH — directly from REQUIREMENTS.md STATE-01/02 tables

**Research date:** 2026-03-10
**Valid until:** 2026-04-10 (stable — React/Next.js/TypeScript versions won't change mid-milestone)
