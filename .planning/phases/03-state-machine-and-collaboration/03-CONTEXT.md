# Phase 3: State Machine & Collaboration - Context

**Gathered:** 2026-01-27
**Status:** Ready for planning

<domain>
## Phase Boundary

System manages hierarchical spool states (occupation + operation progress) and enables sequential multi-worker collaboration on the same spool. Workers can take over paused work from other workers of the same role. Combined state display shows occupation status and ARM/SOLD progress in a single view.

</domain>

<decisions>
## Implementation Decisions

### State representation

- **Storage location:** New column `Estado_Detalle` added to Operaciones sheet
- **Occupied format:** `"MR(93) trabajando ARM (SOLD pendiente)"` - shows current worker, active operation, pending operations
- **Available format:** `"Disponible - ARM pendiente, SOLD pendiente"` - explicit status showing what operations remain
- **Completion terminology:** Use `"completado"` status only (e.g., "ARM completado, SOLD completado") - dates live in separate columns (Fecha_Armado, Fecha_Soldadura)
- **Operation status terminology:** Use `"en progreso"` for in-progress operations (e.g., "ARM en progreso")
- **Visibility:** Always show both ARM and SOLD statuses regardless of current state - full operation sequence visible
- **PAUSAR handling:** Revert to available format (e.g., "Disponible - ARM en progreso, SOLD pendiente") - no explicit "pausado" indicator
- **Update frequency:** Update Estado_Detalle on every state transition (TOMAR, PAUSAR, COMPLETAR, CANCELAR)

### State machine design

- **Architecture:** Separate state machines per operation - ARM has its own state machine (PENDIENTE → EN_PROGRESO → COMPLETADO), SOLD has its own, with coordination layer between them
- **Dependency validation:** Guard conditions in state machine - transitions have guards that check prerequisites (e.g., SOLD TOMAR transition checks ARM state)
- **Library choice:** Use `python-statemachine` library - mature, well-tested, provides guards, callbacks, and event handling
- **Service coordination:** StateService owns orchestration - becomes main orchestrator that calls OccupationService and ValidationService internally
- **Date tracking:** State machine tracks dates internally (fecha_armado, fecha_soldadura) - state machine is single source of truth for these dates
- **Instance lifecycle:** Per-spool instances - create new `ARMStateMachine(spool_tag)` for each operation, state machines are short-lived stateful objects
- **Estado_Detalle updates:** Automatic via callbacks - state machine callbacks (on_enter_estado, after_transition) update Estado_Detalle automatically
- **Initialization:** Hydrate from columns - read Armador, Fecha_Armado, Soldador, Fecha_Soldadura from Operaciones and reconstruct state machine to matching state

### Collaboration rules

- **Cross-worker collaboration:** Yes, full collaboration - any worker with Armador role can TOMAR and COMPLETAR ARM regardless of who initiated, pure role-based access with no individual ownership
- **Column update on takeover:** Overwrite with new worker - when worker B takes over, Armador/Soldador column changes from 'MR(93)' to 'JP(94)' to show current responsible worker
- **History tracking:** Metadata events only - rely on Metadata audit log for complete collaboration history, query TOMAR/PAUSAR/COMPLETAR events to show timeline
- **Operation dependency:** ARM must be initiated before SOLD - block SOLD INICIAR if Armador column is None, ARM work must start first (even if not complete)
- **CANCELAR authorization:** Block cancellation by others - only the current Ocupado_Por worker can CANCELAR, prevents accidental cancellations by different workers
- **Duration display:** Show durations - calculate and display work durations like 'MR(93) worked 2h 15m, JP(94) worked 1h 45m' for productivity tracking
- **Duration calculation for paused sessions:** Calculate up to PAUSAR - if worker did TOMAR at 10:00 and PAUSAR at 11:30, show 1h 30m as closed session
- **History filtering:** No filters needed - show all events chronologically in simple, complete history view
- **Race condition handling:** Redis lock from Phase 2 - use existing Redis locking mechanism, first TOMAR wins, second gets 409 Conflict

### Claude's Discretion

- Exact state transition diagram structure (number of states per operation, transition naming)
- Error messages for validation failures
- Cache strategy for state machine instances
- Metadata query optimization for history views

</decisions>

<specifics>
## Specific Ideas

- Estado_Detalle format should be concise and scannable - workers glance at this column frequently on tablets
- State machine should prevent common errors (SOLD before ARM) but allow flexibility in work order when safe
- History view prioritizes readability over technical precision - show "2h 15m" not "02:15:00"
- Collaboration model follows shop floor reality - workers help each other finish jobs, role matters more than individual ownership

</specifics>

<deferred>
## Deferred Ideas

None - discussion stayed within phase scope

</deferred>

---

*Phase: 03-state-machine-and-collaboration*
*Context gathered: 2026-01-27*
