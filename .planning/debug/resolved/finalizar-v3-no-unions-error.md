---
status: resolved
trigger: "finalizar-v3-no-unions-error"
created: 2026-02-05T00:00:00Z
updated: 2026-02-05T00:25:00Z
---

## Current Focus

hypothesis: CONFIRMED - The FINALIZAR router (union_router.py line 317) explicitly REJECTS v3.0 spools with 400 error directing users to non-existent /api/v3/occupation/completar endpoint. This is the root cause of the error.
test: Implement v3.0 support in FINALIZAR endpoint by detecting v3.0 and using simplified COMPLETAR logic
expecting: v3.0 spools should bypass union processing and directly update Fecha_Armado/Soldadura like the old COMPLETAR endpoint
next_action: Implement fix in occupation_service.py finalizar_spool method and update router

## Symptoms

expected: When finalizing a v3.0 spool (without unions), the system should:
- Clear Ocupado_Por and Fecha_Ocupacion columns in "Operaciones" sheet
- Update Fecha_Armado or Fecha_Soldadura (depending on operation)
- Mark spool as completed (COMPLETAR logic since v3.0 spools are all-or-nothing)
- NOT attempt to query or update "Uniones" sheet (since v3.0 spools don't have union tracking)

actual: Error occurs when pressing "Confirmar" button on P5 confirmation screen for v3.0 spool

errors: See screenshot provided by user (Image #1)

reproduction:
1. Select a v3.0 spool (spool without unions, no Total_Uniones value or Total_Uniones = 0)
2. Complete FINALIZAR flow through P5 confirmation screen
3. Click "Confirmar" button
4. Error occurs

started: Error discovered after fixing previous finalizar-500-error (which was for v4.0 spools WITH unions)

## Eliminated

## Evidence

- timestamp: 2026-02-05T00:01:00Z
  checked: occupation_service.py finalizar_spool method (lines 945-1400)
  found: Code path at line 999+ handles "zero unions selected" as cancellation, but this assumes the request HAS union tracking
  implication: v3.0 spools (without union tracking) will still try to execute union-related code

- timestamp: 2026-02-05T00:02:00Z
  checked: Lines 1059-1080 in finalizar_spool
  found: Code checks self.union_repository and calls get_disponibles_arm_by_ot / get_disponibles_sold_by_ot unconditionally
  implication: For v3.0 spools, union_repository might not be None (injected at startup), so it tries to query unions

- timestamp: 2026-02-05T00:03:00Z
  checked: Lines 1177-1178 (the critical error point)
  found: `processed_unions = self.union_repository.get_by_ids(selected_unions)` is called after batch_update_arm_full/batch_update_sold_full
  implication: For v3.0 spools with selected_unions=[], get_by_ids([]) might return empty list OR throw error if no Uniones sheet data exists

- timestamp: 2026-02-05T00:04:00Z
  checked: iniciar_spool method (lines 609-829)
  found: Already has v3.0 detection at lines 659-662: `is_v21 = spool.total_uniones is None`
  implication: Same detection pattern should be used in finalizar_spool to skip union processing for v3.0

- timestamp: 2026-02-05T00:05:00Z
  checked: Expected behavior for v3.0 FINALIZAR
  found: v3.0 spools should bypass all union-related code and go directly to COMPLETAR logic (update Fecha_Armado/Soldadura, clear occupation)
  implication: Need early return path for v3.0 spools that skips steps 3-6 (union processing)

- timestamp: 2026-02-05T00:06:00Z
  checked: Line 999 cancellation logic
  found: `if len(selected_unions) == 0:` treats empty selection as CANCELLATION (clears occupation, returns "CANCELADO")
  implication: This is WRONG for v3.0 spools - they should COMPLETAR (update fecha), not CANCELAR

- timestamp: 2026-02-05T00:07:00Z
  checked: get_by_ids implementation (union_repository.py line 191-192)
  found: `if not union_ids: return []` - safely handles empty list
  implication: The get_by_ids call is NOT the problem. The problem is the LOGIC PATH - v3.0 spools need different handling

- timestamp: 2026-02-05T00:08:00Z
  checked: union_router.py finalizar_v4 endpoint (lines 308-330)
  found: Line 317: `if not is_v4_spool(spool.model_dump()):` explicitly REJECTS v3.0 spools with 400 error
  implication: This is the ROOT CAUSE - v3.0 spools are rejected before reaching occupation_service

- timestamp: 2026-02-05T00:09:00Z
  checked: Error message content (line 326)
  found: Error directs user to "/api/v3/occupation/completar" which doesn't exist in v4.0 codebase
  implication: User sees 400 error telling them to use non-existent endpoint

- timestamp: 2026-02-05T00:10:00Z
  checked: CLAUDE.md documentation (line 18)
  found: "Version Compatibility: INICIAR works for v2.1 and v4.0, FINALIZAR for v4.0 only (v2.1 unsupported)"
  implication: This was INTENTIONAL but incorrect - v3.0 spools SHOULD be supported in FINALIZAR with simplified logic

## Resolution

root_cause: The FINALIZAR endpoint (backend/routers/union_router.py line 317) explicitly rejects v3.0 spools with a 400 error, directing users to a non-existent /api/v3/occupation/completar endpoint. The system was designed to only support v4.0 spools (with unions) in FINALIZAR, but this breaks the workflow for legacy v3.0 spools that still need to be finalized.

fix:
1. ✅ Removed v3.0 rejection check from union_router.py finalizar_v4 endpoint
2. ✅ Added v3.0 detection in occupation_service.py finalizar_spool method (line 999: is_v30 = spool.total_uniones is None)
3. ✅ Implemented _finalizar_v30_spool helper method that:
   - Skips all union processing entirely
   - Directly updates Fecha_Armado or Fecha_Soldadura based on operacion
   - Clears Ocupado_Por and Fecha_Ocupacion
   - Updates Estado_Detalle to show completion
   - Logs COMPLETAR event with spool_version marker
   - Returns COMPLETAR action (v3.0 is always all-or-nothing, no unions to track)
4. ✅ Updated documentation (union_router.py and occupation_v4.py)
5. ✅ Created comprehensive test suite (test_occupation_service_v30_finalizar.py with 4 tests)
6. ✅ Fixed existing tests to include total_uniones and fecha_ocupacion fields

verification:
- All 27 occupation service tests pass (including 4 new v3.0 tests)
- v3.0 spools now bypass union logic completely
- v3.0 spools always use COMPLETAR (no PAUSAR option)
- v4.0 spools continue working as before with union tracking
- Test coverage confirms union_repository methods never called for v3.0

files_changed:
- backend/routers/union_router.py (removed rejection, updated docs)
- backend/routers/occupation_v4.py (updated version compatibility docs)
- backend/services/occupation_service.py (added v3.0 detection + _finalizar_v30_spool method)
- tests/unit/services/test_occupation_service_v30_finalizar.py (new test file)
- tests/unit/services/test_occupation_service_v4.py (fixed mocks)
