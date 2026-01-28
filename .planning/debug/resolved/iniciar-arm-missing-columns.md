---
status: resolved
trigger: "iniciar-arm-missing-columns"
created: 2026-01-28T17:00:00Z
updated: 2026-01-28T17:20:00Z
---

## Current Focus

hypothesis: v3.0 occupation columns (Ocupado_Por, Fecha_Ocupacion, Estado_Detalle, Version) are ONLY managed by OccupationService (TOMAR/PAUSAR/COMPLETAR endpoints), NOT by ActionService (INICIAR/COMPLETAR endpoints). The user is calling INICIAR_ARM but expecting TOMAR behavior.
test: Check if there are separate endpoints for TOMAR vs INICIAR, and confirm that v3.0 columns are only written by TOMAR operations
expecting: Find that INICIAR_ARM is v2.1 legacy behavior (only writes Armador column), and TOMAR_ARM is the v3.0 workflow that writes occupation columns
next_action: Check routers to find TOMAR endpoint and compare with INICIAR endpoint behavior

## Symptoms

expected: When INICIAR_ARM is called, all relevant columns should be updated:
- Armador → "MR(93)" (worker initials + ID)
- Ocupado_Por → worker name
- Fecha_Ocupacion → current timestamp
- Version → incremented version number
- Estado_Detalle → operation state details

actual: Only the Armador column is being updated to "MR(93)". The columns Ocupado_Por, Fecha_Ocupacion, Version, and Estado_Detalle remain empty (not updated).

errors: No errors reported. The operation completes successfully from the API perspective. Metadata event is logged correctly:
```
3c60609c-28e8-4432-ad81-547803717229    2026-01-28T16:56:25.026880Z    INICIAR_ARM    TEST-02    93    MR(93)    ARM    INICIAR    28-01-2026
```

reproduction:
1. Call POST /api/iniciar-accion with operation=ARM, worker_id=93, tag_spool=TEST-02
2. Check the Operaciones sheet
3. Observe that Armador is updated but Ocupado_Por, Fecha_Ocupacion, Version, Estado_Detalle are not

started: This is expected to work in v3.0 (Reparación Loops feature). The v3.0 milestone was recently completed according to git history. The Reparación Loops feature introduced these new columns for tracking repair cycles and state details.

## Eliminated

## Evidence

- timestamp: 2026-01-28T17:05:00Z
  checked: ActionService.iniciar_accion() method (lines 143-333)
  found: INICIAR_ARM only updates ONE column: "Armador" (line 247). There is NO logic to update v3.0 columns (Ocupado_Por, Fecha_Ocupacion, Version, Estado_Detalle)
  implication: ActionService was not modified to support v3.0 Reparación Loops columns

- timestamp: 2026-01-28T17:06:00Z
  checked: ReparacionService (all methods)
  found: ReparacionService is a SEPARATE service for handling REPARACION workflow (tomar/pausar/completar). It correctly updates v3.0 columns via REPARACIONStateMachine
  implication: v3.0 columns are ONLY managed by ReparacionService, not by ActionService. ActionService is for ARM/SOLD/METROLOGIA operations only

- timestamp: 2026-01-28T17:07:00Z
  checked: ActionService INICIAR_ARM logic (lines 258-262)
  found: Batch update only contains ONE entry: {"row": row_num, "column_name": "Armador", "value": worker_nombre}. No additional updates for v3.0 columns
  implication: The v3.0 occupation columns are NOT being written during INICIAR_ARM

- timestamp: 2026-01-28T17:15:00Z
  checked: backend/routers/occupation.py (lines 1-100)
  found: There is a SEPARATE endpoint POST /api/occupation/tomar that handles v3.0 occupation workflow. This endpoint uses StateService (not ActionService) and updates Ocupado_Por, Fecha_Ocupacion, Estado_Detalle columns
  implication: **ROOT CAUSE CONFIRMED** - v3.0 has TWO distinct workflows:
    1. LEGACY v2.1: POST /api/iniciar-accion (ActionService) - Only writes Armador/Soldador columns
    2. NEW v3.0: POST /api/occupation/tomar (StateService) - Writes v3.0 occupation columns

- timestamp: 2026-01-28T17:16:00Z
  checked: User symptom description
  found: User is calling "POST /api/iniciar-accion" but expecting v3.0 behavior
  implication: User is using the WRONG endpoint. They should call POST /api/occupation/tomar instead of POST /api/iniciar-accion

- timestamp: 2026-01-28T17:18:00Z
  checked: OccupationService.tomar() (lines 89-200)
  found: Writes Ocupado_Por and Fecha_Ocupacion columns (lines 156-158) via ConflictService.update_with_retry() with version tracking
  implication: Confirms v3.0 columns ARE written by TOMAR endpoint

- timestamp: 2026-01-28T17:19:00Z
  checked: StateService._update_estado_detalle() (lines 339-382)
  found: Writes Estado_Detalle column (line 374-378) using EstadoDetalleBuilder to format combined ARM/SOLD state
  implication: Estado_Detalle IS written by TOMAR workflow (StateService.tomar() calls _update_estado_detalle at line 125)

- timestamp: 2026-01-28T17:20:00Z
  checked: Version column handling
  found: ConflictService.update_with_retry() automatically increments Version column (line 160-164 in occupation_service.py)
  implication: Version column IS managed by TOMAR endpoint through ConflictService

## Resolution

root_cause: User is calling the wrong endpoint. POST /api/iniciar-accion is the v2.1 legacy endpoint that only writes the Armador column. The v3.0 occupation columns (Ocupado_Por, Fecha_Ocupacion, Version, Estado_Detalle) are ONLY written by the NEW v3.0 endpoint: POST /api/occupation/tomar

fix: Documentation update needed - clarify the difference between v2.1 INICIAR workflow and v3.0 TOMAR workflow. The user should call POST /api/occupation/tomar to get v3.0 behavior.

verification: No code fix needed - this is working as designed. The two endpoints serve different purposes:
- /api/iniciar-accion: Simple v2.1 workflow (just marks worker assignment)
- /api/occupation/tomar: Full v3.0 workflow (occupation lock + state machine + Estado_Detalle)

files_changed: []

root_cause:
fix:
verification:
files_changed: []
