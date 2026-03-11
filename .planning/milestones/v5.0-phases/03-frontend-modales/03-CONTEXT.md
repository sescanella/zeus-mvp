# Phase 3: Frontend — Modales - Context

**Gathered:** 2026-03-10
**Status:** Ready for planning
**Source:** Auto-generated from REQUIREMENTS.md (v5.0-single-page)

<domain>
## Phase Boundary

This phase creates the 5 modals that form the operation flow in the single-page architecture:
- AddSpoolModal (add spools to the card list)
- OperationModal (select ARM/SOLD/REP/MET)
- ActionModal (select INICIAR/FINALIZAR/PAUSAR/CANCELAR)
- WorkerModal (select worker filtered by role)
- MetrologiaModal (APROBADA/RECHAZADA)

Each modal shows only valid options based on spool state (using spool-state-machine from Phase 1).

</domain>

<decisions>
## Implementation Decisions

### Modal Flow Architecture
- Click on card → OperationModal (ARM/SOLD/REP/MET filtered by spool state) [MODAL-01]
- ARM/SOLD/REP → ActionModal (INICIAR/FINALIZAR/PAUSAR/CANCELAR filtered by state) [MODAL-02]
- INICIAR/FINALIZAR/PAUSAR → WorkerModal (workers filtered by operation role) [MODAL-03]
- CANCELAR does NOT require worker — returns to main screen directly [MODAL-04]
- MET → MetrologiaModal (APROBADA/RECHAZADA) [MODAL-05]
- On worker or MET result selection → execute API call → return to main screen [MODAL-06]
- NotificationToast shows success/error feedback on main screen [MODAL-07]
- No union selection — PAUSAR replaces partial completion [MODAL-08]

### AddSpoolModal
- Reuses existing SpoolTable + SpoolFilterPanel components [D-08]
- Shows already-added spools as disabled/grey [UX-01]

### State Filtering
- Valid operations depend on spool state (STATE-01 mapping)
- Valid actions depend on occupation state (STATE-02 mapping)
- Uses spool-state-machine (getValidOperations, getValidActions) from Phase 1

### API Integration
- No optimistic updates — show loading spinner, wait for API response [UX-03, D-09]
- API errors shown inline in the active modal [Success Criteria]
- Uses existing API functions from Phase 1 (lib/api.ts)

### Visual Design
- Blueprint Industrial palette (navy #001F3F, orange #FF6B35) [UX-04]
- Mobile-first, large touch targets [UX-04]

### Claude's Discretion
- Internal modal component structure and prop interfaces
- Loading state UX within modals
- Error display layout within modals
- Animation/transition between modal stack levels
- Worker list display format in WorkerModal

</decisions>

<specifics>
## Specific Ideas

- AddSpoolModal reuses SpoolTable with `disabledSpools` prop (Phase 2 modification)
- AddSpoolModal reuses SpoolFilterPanel with `showSelectionControls` prop (Phase 2 modification)
- useModalStack hook from Phase 1 manages modal push/pop/clear
- CANCELAR dual behavior: frontend-only (libre) vs backend call (occupied) — but the dual logic is wired in Phase 4
- MetrologiaModal only shows for spools in SOLD-COMPLETADO or PENDIENTE_METROLOGIA state

</specifics>

<deferred>
## Deferred Ideas

- Modal flow wiring to main page (Phase 4: Integration)
- Polling/refresh after modal action (Phase 4)
- Auto-remove on MET APROBADA (Phase 4)
- CANCELAR dual logic (Phase 4)

</deferred>

---

*Phase: 03-frontend-modales*
*Context gathered: 2026-03-10 via auto-generation from REQUIREMENTS.md*
