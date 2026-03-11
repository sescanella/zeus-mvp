# Phase 2: Frontend — Componentes Core - Context

**Gathered:** 2026-03-10
**Status:** Ready for planning
**Source:** PRD Express Path (.planning/v5.0-single-page/REQUIREMENTS.md)

<domain>
## Phase Boundary

Phase 2 delivers the **reusable visual components** that the v5.0 single-page + modal stack architecture needs. This includes:

1. **New components:** NotificationToast.tsx, SpoolCard.tsx, SpoolCardList.tsx
2. **Modified components:** SpoolTable.tsx, SpoolFilterPanel.tsx, Modal.tsx

These components consume the Phase 1 foundations (types, hooks, state machine) and will be assembled into the full page in Phase 4.

</domain>

<decisions>
## Implementation Decisions

### NotificationToast (CARD-02, UX-02, MODAL-07)
- Toast with auto-dismiss 3-5 seconds (UX-02) — Phase 1 hook uses 4000ms
- role="alert" for accessibility (ARIA live region)
- Renders success/error feedback after API operations (MODAL-07)
- Uses useNotificationToast hook from Phase 1 (01-03)

### SpoolCard (CARD-02, STATE-05, STATE-06)
- Displays: TAG, operación actual, acción, worker, tiempo en estado (CARD-02)
- Timer shows real-time elapsed since Fecha_Ocupacion when spool is occupied (STATE-05)
- PAUSADO shows static badge without timer (STATE-06)
- Renders all states: libre, iniciado, pausado, completado, rechazado, bloqueado
- Uses SpoolCardData type from Phase 1 (01-01)
- Click triggers OperationModal (Phase 3)

### SpoolCardList (CARD-06)
- Container for multiple SpoolCards
- Empty state when no spools added
- Supports adding/removing spools individually (CARD-06)

### SpoolTable Modification (UX-01)
- Add `disabledSpools` prop — already-added spools shown as disabled/grey (UX-01)
- Backward compatibility with existing usage

### SpoolFilterPanel Modification
- Add `showSelectionControls` prop for AddSpool modal context
- Backward compatibility with existing usage

### Modal Modification (MODAL stack)
- ESC key only closes the top modal in the stack (not all)
- Integrates with useModalStack from Phase 1 (01-03)

### Claude's Discretion
- Timer implementation details (setInterval vs requestAnimationFrame)
- SpoolCard layout and styling specifics within Blueprint palette
- Empty state design for SpoolCardList
- Animation choices for toast entrance/exit
- Test strategy for timer components

</decisions>

<specifics>
## Specific Ideas

- Blueprint Industrial palette: navy #001F3F, orange #FF6B35 (UX-04)
- Mobile-first, large touch targets (h-16/h-20) (UX-04)
- WCAG 2.1 Level AA compliance (project standard)
- State colors/badges should visually distinguish all 6+ spool states
- Timer format: HH:MM:SS or MM:SS for occupied spools

</specifics>

<deferred>
## Deferred Ideas

- Modal components (Phase 3)
- Page assembly and polling (Phase 4)
- Old code cleanup (Phase 5)

</deferred>

---

*Phase: 02-core-location-tracking*
*Context gathered: 2026-03-10 via PRD Express Path*
