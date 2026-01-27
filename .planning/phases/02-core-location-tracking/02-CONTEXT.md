# Phase 2: Core Location Tracking - Context

**Gathered:** 2026-01-27
**Status:** Ready for planning

<domain>
## Phase Boundary

Build API operations that let workers take (TOMAR), pause (PAUSAR), and complete (COMPLETAR) work on spools with occupation tracking and race condition prevention. This phase establishes the core location tracking mechanism - who has which spool at any moment - and enforces physical occupation constraints (can't take what's occupied).

</domain>

<decisions>
## Implementation Decisions

### Occupation Behavior

- **Multiple spools allowed**: Workers can TOMAR multiple spools simultaneously (no limit on quantity)
- **No hard limit**: Unlimited concurrent occupations per worker - trust worker judgment on their capacity
- **Occupation display**: Show "Ocupado por: INICIALES(ID)" only (e.g., "MR(93)") - name format, no timestamp/duration
- **Prerequisite validation**: TOMAR only validates Fecha_Materiales must contain a value - no other prerequisites checked
- **Available actions**: Workers see PAUSAR + COMPLETAR + CANCELAR options for their occupied spools
- **Admin override only**: Only ADMIN role can force-release occupied spools - supervisors cannot override
- **No time tracking**: System doesn't track or warn about occupation duration for Phase 2
- **Shown as unavailable**: Occupied spools appear in lists but grayed out/disabled with "Ocupado por: XX" indicator
- **All operations mixed**: "My Occupied Spools" view shows ARM + SOLD + METROLOGIA together in single list
- **Partial success allowed**: Batch TOMAR processes each spool independently - report "7 of 10 succeeded, 3 failed: [reasons]"
- **Error code + message**: TOMAR failures show technical format: "Error 409: Spool TAG-123 already occupied by JP(94)"
- **No device tracking**: Don't track tablet/device info - only worker_id and timestamp in metadata
- **Fully independent**: Workers operate independently - no coordination, priority queues, or load balancing hints

### PAUSAR Semantics

- **Save + mark partial**: PAUSAR preserves occupation history in Metadata AND marks spool state as "ARM parcial (paused)" or "SOLD parcial (paused)"
- **Fully available to anyone**: After PAUSAR, spool becomes available to any qualified worker (first-come-first-served, no preference)
- **Previous worker only**: New worker taking paused spool sees "Trabajo previo: INICIALES(ID)" without times or pause reason
- **Simple confirmation**: PAUSAR shows "¿Pausar trabajo en TAG-123?" Yes/No dialog before executing
- **Batch same as single**: Batch PAUSAR = multiple individual pauses, each gets its own confirmation dialog
- **Special indicator**: Paused spools (marked "parcial") have visual distinction (icon/badge/color) in available spools list
- **Can retake immediately**: Worker who paused can TOMAR same spool again immediately (no cooldown or restrictions)
- **Standard metadata only**: PAUSAR logs timestamp, worker_id, tag_spool - no % completion, pause reason, or quality notes
- **Disappear immediately**: After PAUSAR, spool removed from "My Occupied Spools" instantly (no brief status display)
- **Simple confirmation text**: Dialog shows "¿Pausar trabajo en TAG-123?" only - doesn't mention spool becomes available to others
- **No cycle limits**: Spools can be paused/resumed unlimited times - no warnings or blocks after N cycles

### Claude's Discretion

- **PAUSAR data model**: Claude determines whether TOMAR sets Fecha_Operacion or if it's only set on COMPLETAR (affects what PAUSAR clears)
- **Race condition UX**: Claude implements specific retry mechanism and user feedback for conflict scenarios
- **Metadata event structure**: Claude designs exact JSON schema for metadata_json column beyond core fields
- **Partial state representation**: Claude implements how "ARM parcial" vs "SOLD parcial" states are represented in Operaciones sheet
- **Visual indicators**: Claude designs specific icon/badge/color for paused spools in mobile-first UI

</decisions>

<specifics>
## Specific Ideas

- Use existing v2.1 worker name format: "INICIALES(ID)" (e.g., "MR(93)", "JP(94)")
- Leverage v2.1 Direct Read architecture: read state from Operaciones columns (Armador/Soldador), write events to Metadata
- Prerequisite validation minimal for Phase 2: only Fecha_Materiales check (same as v2.1 INICIAR validation)
- Admin override needed for emergency scenarios (worker went home, forgot to pause, spool stuck)
- Partial state marking enables Phase 3 collaboration (multiple workers can contribute to same spool sequentially)

</specifics>

<deferred>
## Deferred Ideas

- Time-based warnings for long-occupied spools → Phase 4 (Real-Time Visibility) dashboard
- Priority queues or recommended next spool → Future phase (workload optimization)
- Load balancing hints (X workers on ARM, Y on SOLD) → Phase 4 dashboard feature
- Extended metadata (% completion, pause reasons, quality notes) → Phase 5/6 (quality workflows)
- GPS location tracking for device → Phase 4 or future audit requirements
- Pause reason categorization → Phase 5 (Metrología) or Phase 6 (Reparación) for quality tracking

</deferred>

---

*Phase: 02-core-location-tracking*
*Context gathered: 2026-01-27*
