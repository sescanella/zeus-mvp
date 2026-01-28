# Phase 5: Metrología Workflow - Context

**Gathered:** 2026-01-27
**Status:** Ready for planning

<domain>
## Phase Boundary

Metrología inspection workflow with instant completion (no occupation period). Metrólogo executes binary approval/rejection on finished spools that have completed both ARM and SOLD operations. This phase delivers the inspection action only — reparación workflow after rejection belongs to Phase 6.

</domain>

<decisions>
## Implementation Decisions

### Instant completion flow
- Skip tipo-interacción page entirely (no INICIAR/COMPLETAR choice)
- Flow: Operation Selection → Worker → Spool Selection → APROBADO/RECHAZADO → Success
- Direct resultado selection after spool (no separate confirmation screen before submit)
- Single spool inspection only (no batch multiselect)
- Standard metadata logging: worker_id, timestamp, operacion=METROLOGIA, accion=COMPLETAR, resultado in metadata_json

### Binary result handling
- Two large buttons: APROBADO (green) and RECHAZADO (red) for mobile-first UX
- Submit immediately on button click (no summary confirmation)
- Update Estado_Detalle column only (no new Metrólogo or Fecha_Metrologia columns)
- RECHAZADO displays simple message: "METROLOGIA RECHAZADO - Pendiente reparación"

### Prerequisite validation
- Filter at spool selection stage (only show spools ready for inspection)
- Reuse existing endpoint: GET /api/spools/iniciar?operacion=METROLOGIA
- Backend filter: fecha_armado != None AND fecha_soldadura != None AND ocupado_por = None
- Empty state message: "No hay spools listos para metrología" + hint about ARM/SOLD completion
- Block occupied spools (cannot inspect if ocupado_por != None)

### State machine design
- Separate METROLOGIA state machine (not integrated with ARM/SOLD)
- 3 states: PENDIENTE → APROBADO (terminal), PENDIENTE → RECHAZADO (terminal)
- One-way transitions only (no reversals or re-inspection after completion)
- State machine owns Estado_Detalle updates via callbacks (follows Phase 3 pattern)

### Claude's Discretion
- Exact wording of empty state hint message
- Loading states during API calls
- Error message formatting for validation failures
- Position of APROBADO/RECHAZADO buttons on screen

</decisions>

<specifics>
## Specific Ideas

- "Instant completion" means skipping the TOMAR occupation step entirely — inspection happens in seconds, not hours
- Estado_Detalle should clearly communicate next steps for rejected spools (Phase 6 reparación workflow)
- Filtering occupied spools prevents race conditions (metrólogo can't inspect while worker is actively modifying)

</specifics>

<deferred>
## Deferred Ideas

- Batch multiselect for approved spools — could speed up approvals but rejected for Phase 5 simplicity
- Additional metadata fields (inspection_notes, defect_type, inspector_signature) — deferred to future enhancement
- Re-inspection capability (APROBADO/RECHAZADO → PENDIENTE) — correction scenarios handled in future phase
- Metrólogo and Fecha_Metrologia columns — kept minimal for Phase 5, could add in data model enhancement

</deferred>

---

*Phase: 05-metrologia-workflow*
*Context gathered: 2026-01-27*
