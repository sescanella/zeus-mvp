# Phase 4: Frontend — Integración - Context

**Gathered:** 2026-03-10
**Status:** Ready for planning
**Source:** Auto-generated from ROADMAP.md + REQUIREMENTS.md

<domain>
## Phase Boundary

This phase assembles all v5.0 components (from Phases 1-3) into a working single-page application. It creates the SpoolListContext, rewrites the main page, wires the complete modal flow, implements polling, auto-remove on MET APROBADA, and dual CANCELAR logic. After this phase, the E2E user workflow is functional.

**Delivers:**
- SpoolListContext (card list state + localStorage sync)
- Rewritten app/page.tsx (single page with AddSpool + SpoolCardList + Toasts)
- Complete modal wiring (AddSpool → Operation → Action → Worker → API → refresh)
- 30s polling via batch-status
- Auto-remove on MET APROBADA
- Dual CANCELAR (frontend-only vs backend)

</domain>

<decisions>
## Implementation Decisions

### State Management
- SpoolListContext manages the list of active spool cards (CARD-03, CARD-06)
- localStorage stores only tag_spool array; full state refreshed from backend (D-02)
- No optimistic updates — spinner + wait for API response (D-09, UX-03)

### Page Architecture
- Single page, no routing — app/page.tsx is the entire app (D-01)
- "Añadir Spool" button opens AddSpoolModal (CARD-01)
- SpoolCardList renders all active cards (CARD-02, CARD-06)
- NotificationToast overlay for feedback (MODAL-07, UX-02)

### Modal Flow Wiring
- Card click → OperationModal → ActionModal → WorkerModal → API call → toast + refresh (MODAL-01 through MODAL-06)
- MET path: Card → OperationModal → MetrologiaModal → API → toast (MODAL-05)
- CANCELAR skips WorkerModal, calls onCancel directly (MODAL-04)
- All modals use useModalStack for push/pop management

### Polling
- 30-second interval using batchGetStatus (D-03, CARD-03)
- Refreshes all cards currently in the list
- Uses POST /api/spools/batch-status (API-02)

### Auto-Remove
- MET APROBADA removes spool from list automatically (CARD-04)
- MET RECHAZADA keeps spool for Reparación flow (CARD-05)

### CANCELAR Dual Logic
- Spool libre (no ocupado_por): remove from list only, no API call (STATE-03, D-06)
- Spool occupied: call backend reset + remove from list (STATE-04, D-06)

### Claude's Discretion
- SpoolListContext implementation details (useReducer vs useState)
- Polling hook implementation (setInterval vs custom hook)
- Animation approach for auto-remove
- Error retry strategy for failed API calls in modal flow
- Loading state management during API calls

</decisions>

<specifics>
## Specific Ideas

- SpoolListContext should expose: addSpool, removeSpool, spools, refreshAll
- Polling should pause when tab is not visible (Page Visibility API)
- Auto-remove animation should be brief (300-500ms fade-out)
- Toast feedback must distinguish success vs error (MODAL-07)
- AddSpoolModal disables already-added spools (UX-01) — handled by SpoolTable disabledSpools prop from Phase 2

</specifics>

<deferred>
## Deferred Ideas

None — this phase covers full integration scope.

</deferred>

---

*Phase: 04-frontend-integracion*
*Context gathered: 2026-03-10 via auto-generation from ROADMAP + REQUIREMENTS*
