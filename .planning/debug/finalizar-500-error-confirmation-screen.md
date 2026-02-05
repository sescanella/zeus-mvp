---
status: verifying
trigger: "finalizar-500-error-confirmation-screen"
created: 2026-02-05T00:00:00Z
updated: 2026-02-05T00:35:00Z
---

## Current Focus

hypothesis: Missing get_by_ids method in UnionRepository causes AttributeError
test: Verify method doesn't exist and add implementation
expecting: Method implementation will resolve 500 error
next_action: Implement get_by_ids method in union_repository.py

## Symptoms

expected: When confirming FINALIZAR with 6 of 12 unions selected for spool TEST-02, the system should:
- Clear Ocupado_Por and Fecha_Ocupacion columns in "Operaciones" sheet
- Add values to the union rows in "Uniones" sheet (ARM_FECHA_INICIO, ARM_FECHA_FIN, ARM_WORKER columns for the 6 selected unions)
- Use PAUSAR logic (partial completion, not COMPLETAR since only 6/12 unions done)

actual: Error 500 returned from POST /api/v4/occupation/finalizar endpoint when user presses "Confirmar" button

errors:
- POST https://zeues-backend-mvp-production.up.railway.app/api/v4/occupation/finalizar returns 500 (Internal Server Error)
- Frontend shows "finalizarSpool error: Error: Error 500"
- Console shows error at: 984-b480203539769bcc.js:1:1604 and 117-a0b7eec5d9d73bf1.js:1

reproduction:
1. Select worker: Mauricio Rodríguez (MR(93))
2. Select operation: ARMADO
3. Select action type: FINALIZAR
4. Select spool: TEST-02 (has 12 unions total in OT001)
5. Select 6 unions (partial completion)
6. Click "Continuar" to go to P5 confirmation screen
7. Click "Confirmar" button
8. Error 500 occurs

started: Error occurs after recent commit that "changed the finalizar system"

## Eliminated

## Evidence

- timestamp: 2026-02-05T00:10:00Z
  checked: Recent git commits and union_repository.py batch_update_*_full methods
  found: Recent commit c5dbc47 "feat: Implement P5 Confirmation Workflow (v4.0 Phase 8)" introduced new batch_update_arm_full and batch_update_sold_full methods that write INICIO + FIN + WORKER timestamps
  implication: The new methods are being called by finalizar_spool, likely causing the 500 error

- timestamp: 2026-02-05T00:15:00Z
  checked: occupation_service.py finalizar_spool method (lines 945-1400)
  found: Lines 1159-1174 call batch_update_arm_full/batch_update_sold_full with timestamp_inicio and timestamp_fin parameters. The timestamp_inicio is parsed from spool.fecha_ocupacion (line 1144-1155)
  implication: If Fecha_Ocupacion column is missing or has incorrect value, datetime parsing will fail

- timestamp: 2026-02-05T00:20:00Z
  checked: Union repository batch_update_*_full methods synthesize union IDs from OT+N_UNION
  found: Lines 988 and 1126 synthesize union_id as f"{row_ot}+{row_n_union}" to match frontend format
  implication: Union ID format is correct (OT+N_UNION), not the issue

- timestamp: 2026-02-05T00:25:00Z
  checked: Searched for get_by_ids method in UnionRepository
  found: Method is called at occupation_service.py:1177 but does NOT EXIST in union_repository.py
  implication: AttributeError exception when calculating pulgadas for metadata, causing 500 error

## Resolution

root_cause: occupation_service.py line 1177 calls self.union_repository.get_by_ids(selected_unions) to calculate pulgadas for metadata logging, but this method doesn't exist in UnionRepository class. This causes an AttributeError exception when FINALIZAR is called without UnionService (direct repository path), resulting in 500 error.

fix: Added get_by_ids method to UnionRepository (after get_by_spool method) that:
- Accepts list of union IDs in "OT+N_UNION" format
- Reads Uniones sheet with dynamic column mapping
- Synthesizes union IDs from OT+N_UNION columns (consistent with batch_update methods)
- Returns list of matching Union objects
- Used for calculating pulgadas in FINALIZAR metadata logging

verification:
- ✅ All 17 P5 workflow unit tests pass (test_occupation_service_p5_workflow.py)
- ✅ UnionRepository imports successfully
- ✅ get_by_ids method exists with correct signature
- ✅ Method implementation:
  - Accepts list[str] of union IDs in "OT+N_UNION" format
  - Uses dynamic column mapping (no hardcoded indices)
  - Synthesizes IDs from OT+N_UNION columns (consistent with batch_update methods)
  - Returns list[Union] of matching unions
  - Handles empty union_ids gracefully
- ✅ Logic verified: Lines 1177-1178 in occupation_service.py will now successfully:
  1. Call self.union_repository.get_by_ids(selected_unions)
  2. Calculate pulgadas = sum([u.dn_union for u in processed_unions if u.dn_union])
  3. Include pulgadas in metadata JSON

files_changed:
- backend/repositories/union_repository.py (added get_by_ids method after line 174)
