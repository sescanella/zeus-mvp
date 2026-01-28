# Phase 6: Reparación Loops - Context

**Gathered:** 2026-01-28
**Status:** Ready for planning

<domain>
## Phase Boundary

Manufacturing rework workflow for rejected spools. After metrología RECHAZADO, spools enter a separate REPARACIÓN operation module where any production worker can repair defects. Repaired spools automatically return to metrología queue for re-inspection. After 3 consecutive rejections, spool becomes BLOQUEADO and requires manual supervisor intervention (Google Sheets edit + Metadata logging).

</domain>

<decisions>
## Implementation Decisions

### Operation Structure & Access
- **REPARACIÓN as 4th operation:** Separate operation module alongside ARM, SOLD, METROLOGÍA (not a sub-operation)
- **Role access:** No role restriction - all active workers can access REPARACIÓN module (no "Reparación" role in Roles sheet)
- **UI integration:** Add REPARACIÓN as 4th button on Operation selection page (P2)
- **Worker flow:** Same worker selection step as ARM/SOLD/METROLOGÍA - consistent UX across all operations

### Spool Filtering & Display
- **Filter criteria:** Show only RECHAZADO spools where ocupado_por = None (skip occupied spools, consistent with ARM/SOLD pattern)
- **List display:** TAG_SPOOL + rejection date (fecha_rechazo) on each card
- **No visual indicators:** Simple list - no cycle count badges, color coding, or urgency warnings in selection view
- **Batch operations:** Support multiselect up to 50 spools (same limit as ARM/SOLD batch operations)

### Workflow Actions
- **TOMAR/PAUSAR/COMPLETAR pattern:** REPARACIÓN follows same 3-action flow as ARM/SOLD (occupation-based workflow)
- **PAUSAR support:** Yes - worker can release occupation mid-repair, spool returns to REPARACION_PAUSADA estado
- **CANCELAR support:** Yes - add CANCELAR action for REPARACIÓN (clears ocupado_por, returns to RECHAZADO, logs CANCELAR_REPARACION event)
- **Completion behavior:** COMPLETAR reparación clears ocupado_por and transitions spool to PENDIENTE_METROLOGIA automatically

### Cycle Limit Enforcement
- **Cycle counting:** Increments on each metrología RECHAZADO event (not on repair completion)
- **Cycle storage:** Embed in Estado_Detalle field (e.g., "RECHAZADO (Ciclo 2/3)") - no separate reparacion_count column
- **Consecutive vs total:** Count consecutive rejections only - counter resets to 0 after APROBADO
- **3-cycle limit behavior:**
  - After 3rd RECHAZADO → estado becomes BLOQUEADO
  - BLOQUEADO spools visible but disabled in REPARACIÓN list (grayed out, unselectable)
  - Blocks REPARACIÓN TOMAR only - ARM/SOLD/METROLOGÍA operations still work if needed
- **Supervisor override:** Manual Estado_Detalle edit in Google Sheets to change BLOQUEADO → RECHAZADO
- **Override logging:** System detects Estado_Detalle change and logs SUPERVISOR_OVERRIDE event to Metadata automatically
- **Post-override success:** If BLOQUEADO spool passes metrología after override, cycle count resets to 0

### State Machine & Transitions
- **New ReparacionStateMachine:** Dedicated state machine following Phase 3 pattern
  - RECHAZADO → EN_REPARACION → REPARACION_PAUSADA → PENDIENTE_METROLOGIA
- **Estado_Detalle during repair:** "EN_REPARACION (Ciclo 2/3) - Ocupado: Juan(93)"
- **Estado_Detalle after PAUSAR:** "REPARACION_PAUSADA (Ciclo 2/3)" (indicates partial work done)
- **Estado_Detalle after COMPLETAR:** "PENDIENTE_METROLOGIA" (ready for re-inspection)
- **Final estado after approval:** "METROLOGIA_APROBADO ✓" (same as first-time approval, no distinction)
- **Occupation clearing:** Yes - COMPLETAR reparación clears ocupado_por and fecha_ocupacion fields
- **Self-repair allowed:** No restriction - worker can repair spools they originally worked on (ARM/SOLD)

### Metrología Re-inspection
- **Queue behavior:** Repaired spools appear in normal METROLOGÍA list (no separate "Re-inspection" filter)
- **Inspector assignment:** Any metrólogo can inspect repaired spool (no assignment to original inspector)
- **Completion tracking:** Simple - logs COMPLETAR_REPARACION event with worker, timestamp, spool (no defect details captured)

### Real-Time Updates & Dashboard
- **SSE integration:** Yes - same pattern as ARM/SOLD (TOMAR/PAUSAR/COMPLETAR publish SSE events)
- **Dashboard display:** Same format as ARM/SOLD - no visual distinction for repair work
- **No separate sections:** Repair work appears alongside production work in single "Who has what" list

### Visibility & Reporting
- **History view:** Show ALL events chronologically (ARM, SOLD, METROLOGÍA, REPARACION) - complete timeline
- **Confirmation page (P5):** Same format as ARM/SOLD - no cycle info displayed
- **Metadata enrichment:** Include cycle count in metadata_json: {"cycle": 2, "max_cycles": 3} for audit trail
- **Supervisor dashboard:** No dedicated BLOQUEADO spools view - supervisors review manually in Google Sheets

### Claude's Discretion
- Estado_Detalle formatting for BLOQUEADO state display
- Exact SSE event payload structure for REPARACION events
- Error messages for cycle limit violations
- Metadata event naming conventions (TOMAR_REPARACION vs INICIAR_REPARACION)

</decisions>

<specifics>
## Specific Ideas

- **Cycle count format:** "Ciclo X/3" embedded in Estado_Detalle string (e.g., "RECHAZADO (Ciclo 2/3)")
- **BLOQUEADO display:** Visible but disabled cards in spool list - clear visual feedback without hiding information
- **Override simplicity:** Manual Google Sheets edit + automatic Metadata logging - no complex API endpoint needed for Phase 6
- **Consistency priority:** Reuse ARM/SOLD patterns wherever possible (TOMAR/PAUSAR/COMPLETAR, batch operations, SSE events, dashboard display)

</specifics>

<deferred>
## Deferred Ideas

None - discussion stayed within phase scope. All decisions map directly to Phase 6 success criteria.

</deferred>

---

*Phase: 06-reparacion-loops*
*Context gathered: 2026-01-28*
