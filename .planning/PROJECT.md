# ZEUES v5.0 - Single Page Manufacturing Traceability

## What This Is

ZEUES is a manufacturing traceability system for pipe spool fabrication. Workers manage spools from a single-page card interface with stacked modals — adding spools to their personal list, performing operations (ARM/SOLD/MET/REP) via modal flows, and tracking real-time state with 30-second auto-refresh. The system answers "WHO has WHICH spool right now?" with union-level granularity and pulgadas-diámetro as the primary business metric.

## Core Value

**Manage all spools from one screen, with every operation one click away.** Workers add spools to a persistent card list, tap a card to open operations, and complete workflows through a modal stack — no page navigation, no lost context.

## Requirements

### Validated

✓ **v2.1 Features (Production):**
- Worker management with multi-role system (Armador, Soldador, Metrología, Ayudante)
- Spool tracking with TAG_SPOOL barcodes
- Batch operations (up to 50 spools simultaneously)
- Metadata Event Sourcing audit trail (append-only immutable log)
- Google Sheets as source of truth (Operaciones, Trabajadores, Roles, Metadata sheets)
- FastAPI backend + Next.js mobile-first frontend
- Deployed on Railway + Vercel in production

✓ **v3.0 Real-Time Location Tracking (Shipped 2026-01-28):**
- Location tracking with TOMAR/PAUSAR/COMPLETAR workflows (Redis atomic locks)
- Race condition prevention (optimistic locking, 10 concurrent tests validated)
- Hierarchical state machines (6 states: 3 ARM + 3 SOLD)
- SSE streaming for dashboard updates
- Metrología instant inspection (APROBADO/RECHAZADO without occupation)
- Bounded reparación cycles (max 3 before BLOQUEADO)
- Collaborative worker handoffs without strict ownership

✓ **v4.0 Uniones System (Shipped 2026-02-02):**
- Union-level data model (18-column Uniones sheet, 5 metrics columns in Operaciones)
- Pulgadas-diámetro as primary business metric
- INICIAR/FINALIZAR workflows with auto-determination (PAUSAR vs COMPLETAR)
- Batch API writes (<1s p95 latency)
- Persistent Redis locks (no TTL, supports 5-8h sessions)
- Version detection routing v3.0 vs v4.0 workflows

✓ **v5.0 Single Page + Modal Stack (Shipped 2026-03-11, 14 plans, 27 requirements):**

**Cards — Main Screen (6/6):**
- ✓ **CARD-01**: "Añadir Spool" button opens modal with SpoolTable + filters — v5.0
- ✓ **CARD-02**: Cards show TAG, operation, action, worker, elapsed time — v5.0
- ✓ **CARD-03**: localStorage persistence (tags only) + 30s backend refresh — v5.0
- ✓ **CARD-04**: MET APROBADA auto-removes spool from list — v5.0
- ✓ **CARD-05**: MET RECHAZADA keeps spool for reparación — v5.0
- ✓ **CARD-06**: Multiple spools operable individually — v5.0

**Modals — Operation Flow (8/8):**
- ✓ **MODAL-01**: Card click → OperationModal (ARM/SOLD/REP/MET filtered by state) — v5.0
- ✓ **MODAL-02**: ARM/SOLD/REP → ActionModal (INICIAR/FINALIZAR/PAUSAR/CANCELAR filtered) — v5.0
- ✓ **MODAL-03**: INICIAR/FINALIZAR/PAUSAR → WorkerModal (role-filtered) — v5.0
- ✓ **MODAL-04**: CANCELAR no worker needed — direct return — v5.0
- ✓ **MODAL-05**: MET → MetrologiaModal (APROBADA/RECHAZADA two-step) — v5.0
- ✓ **MODAL-06**: Worker/MET selection → API call → back to main — v5.0
- ✓ **MODAL-07**: NotificationToast feedback after action (4s auto-dismiss) — v5.0
- ✓ **MODAL-08**: No union selection — PAUSAR replaces partial completion — v5.0

**State Logic (6/6):**
- ✓ **STATE-01**: Valid operations depend on spool state (state machine) — v5.0
- ✓ **STATE-02**: Valid actions depend on occupation state — v5.0
- ✓ **STATE-03**: CANCELAR libre = frontend-only removal — v5.0
- ✓ **STATE-04**: CANCELAR occupied = backend reset + remove — v5.0
- ✓ **STATE-05**: Timer from Fecha_Ocupacion when occupied — v5.0
- ✓ **STATE-06**: PAUSADO static badge without timer — v5.0

**API (3/3):**
- ✓ **API-01**: GET /api/spool/{tag}/status — individual status with computed fields — v5.0
- ✓ **API-02**: POST /api/spools/batch-status — batch refresh for polling — v5.0
- ✓ **API-03**: FINALIZAR action_override (PAUSAR/COMPLETAR) — v5.0

**UX (4/4):**
- ✓ **UX-01**: Already-tracked spools disabled/grey in AddSpoolModal — v5.0
- ✓ **UX-02**: Toast auto-dismiss 3-5s — v5.0
- ✓ **UX-03**: No optimistic updates — wait for API response — v5.0
- ✓ **UX-04**: Blueprint Industrial palette, mobile-first — v5.0

### Active

**Next Milestone Planning:**
- Fresh requirements needed — run `/gsd:new-milestone` to define v5.1+ goals

### Out of Scope

- **Automatic PAUSAR on timeout** — Manual only. Workers decide when to release spools.
- **GPS/RFID physical tracking** — Logical occupation only, not physical location sensors.
- **Sub-1-second real-time sync** — 30s polling sufficient for manufacturing floor.
- **Reservation system** — No "reserve for later" without physically taking spool.
- **Multi-operation TOMAR** — Worker can only work one operation at a time per spool.
- **Retroactive edits** — Metadata is append-only (regulatory requirement).
- **Complex role hierarchies** — Flat role system, no supervisor approval workflows.
- **Union-level selection in UI** — Eliminated in v5.0; action_override replaces manual union checkboxes.

## Context

**Current Codebase State (v5.0 shipped 2026-03-11):**
- ZEUES v5.0 in production (Railway + Vercel)
- Python 3.11+ FastAPI backend (22,006 LOC) with Clean Architecture
- Next.js 14 TypeScript frontend (4,489 LOC) — single-page modal architecture
- Google Sheets as database (Operaciones 72 cols, Uniones 17 cols, Metadata 11 cols)
- 301 Jest tests + 6 Playwright a11y tests passing
- WCAG 2.1 Level AA compliant

**v5.0 Achievements:**
- Replaced 9-page linear flow with single-page card list + modal stack
- 7 v4.0 route directories deleted, ~3000+ lines of dead code removed
- SpoolCard with live elapsed timer and 7-state badges (Blueprint Industrial palette)
- 30s batch-status polling with Page Visibility API pause when tab hidden/modal open
- Complete modal chain: AddSpool → Operation → Action → Worker → API → Toast
- CANCELAR dual logic: frontend-only (libre) vs backend reset (occupied)
- parseEstadoDetalle parser shared between backend (Python) and frontend (TypeScript)

**Known Technical Debt (from v5.0 audit — 6 items, all non-blocking):**
- Unused `parseEstadoDetalle` TypeScript mirror (157 + 310 lines) — zero consumers
- Unused `addTag`/`removeTag`/`clearTags` in local-storage.ts — superseded by SpoolListContext
- Orphaned `UnionTable.tsx` — exists but no consumers
- Stale v3.0 fields in `operation-config.ts` (skipP3, OPERATION_WORKFLOWS, ActionType)
- Pre-existing TODO in api.ts:315 (getSpoolsReparacion cycle hardcoded to 0)

## Constraints

- **Tech Stack (MUST keep)**: Python FastAPI + Next.js + Google Sheets (no database migration)
- **Mobile-First**: Tablet UI with large buttons (h-16/h-20), touch-friendly
- **Google Sheets Limits**: 60 writes/min/user, 200-500ms latency
- **Manufacturing Scale**: 30-50 workers, 2,000+ spools, 10-15 req/sec peak
- **Regulatory**: Metadata audit trail mandatory (append-only, immutable)
- **Accessibility**: WCAG 2.1 Level AA compliance (axe-core + Playwright tests)

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| **Single page + modal stack (no routing)** | Eliminates unnecessary navigation, all operations one click away from card list | ✓ Good — v5.0 replaced 9 pages with 1 page + 5 modals, zero page transitions |
| **localStorage for spool tag persistence** | Simple, no backend needed, persists between sessions, only stores tag strings | ✓ Good — SpoolListContext syncs via useEffect, survives page reloads |
| **30s polling via batch-status** | Balance between freshness and Google Sheets rate limits; pauses when tab hidden | ✓ Good — Page Visibility API + modal-open pause prevents wasted API calls |
| **Estado_Detalle as state source** | Already encodes all needed info (operation, progress, cycle), avoids new columns | ✓ Good — parseEstadoDetalle extracts operacion_actual, estado_trabajo, ciclo_reparacion |
| **action_override on FINALIZAR** | Eliminates union selection UI without breaking backend logic | ✓ Good — PAUSAR/COMPLETAR buttons directly map to override, simpler UX |
| **CANCELAR dual logic** | Frontend-only for libre spools (no API), backend reset for occupied spools | ✓ Good — Clean separation, no unnecessary API calls for simple list removal |
| **No optimistic updates** | Prevents frontend/backend state divergence; loading spinner + wait for response | ✓ Good — Simple mental model, no rollback complexity |
| **Reuse existing components** | SpoolTable, Modal, SpoolFilterPanel extended with new props, not rewritten | ✓ Good — Backward-compatible prop additions (disabledSpools, isTopOfStack, showSelectionControls) |
| **Hierarchical state machine (v3.0)** | 6 manageable states vs 27 combinatorial states | ✓ Good — Still valid in v5.0, getValidOperations/getValidActions use same logic |
| **Bounded reparación cycles (v3.0)** | Max 3 before BLOQUEADO, prevents infinite loops | ✓ Good — Still enforced, BLOQUEADO spools show no operations in OperationModal |
| **Metrología instant completion (v3.0)** | No occupation needed for quick inspection | ✓ Good — MetrologiaModal two-step flow (resultado → worker) matches workflow |

---
*Last updated: 2026-03-11 after v5.0 milestone*
