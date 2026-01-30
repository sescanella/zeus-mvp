---
status: verifying
trigger: "pausar-error-400-fix-failed"
created: 2026-01-30T00:00:00Z
updated: 2026-01-30T00:06:00Z
---

## Current Focus

hypothesis: CONFIRMED - activate_initial_state() is resetting the machine to PENDIENTE after hydration sets it to EN_PROGRESO
test: Remove activate_initial_state() call or call it BEFORE hydration
expecting: PAUSAR will work after fix because machine state will remain EN_PROGRESO
next_action: Fix the code by moving activate_initial_state() before hydration or removing it

## Symptoms

expected: PAUSAR should work after fix is deployed (commit ac64c55 on Railway)
actual: Error 400 still returned: "Cannot PAUSAR ARM from state 'pendiente'. PAUSAR is only allowed from 'en_progreso' state."
errors:
- Frontend: "ERROR Error 400:"
- API Response: {"detail":"Cannot PAUSAR ARM from state 'pendiente'. PAUSAR is only allowed from 'en_progreso' state."}
reproduction:
1. Deploy ac64c55 to Railway (confirmed deployed)
2. Call POST /api/occupation/pausar with TEST-02
3. Still get Error 400
started: Fix deployed 10+ minutes ago, Railway confirmed using ac64c55, but error persists

## Eliminated

## Evidence

- timestamp: 2026-01-30T00:01:00Z
  checked: TEST-02 actual data in Google Sheets
  found: Ocupado_Por='MR(93)', Armador='MR(93)', Fecha_Armado=None
  implication: TEST-02 does NOT match edge case (has both Ocupado_Por AND Armador), so edge case fix (line 482-497) is NOT triggered. Normal path (line 472-481) should hydrate to EN_PROGRESO correctly.

- timestamp: 2026-01-30T00:02:00Z
  checked: update_cell_by_column_name() in sheets_repository.py
  found: Line 423 invalidates cache after writing Armador
  implication: Cache invalidation IS present and should work. The edge case fix we added is not the issue - there's a different problem.

- timestamp: 2026-01-30T00:03:00Z
  checked: Railway deployment configuration (Dockerfile line 26)
  found: Single uvicorn worker (no --workers flag), so only ONE process/cache
  implication: Multi-worker cache inconsistency is NOT the issue. Must be something else.

- timestamp: 2026-01-30T00:04:00Z
  checked: Local test of TOMAR->PAUSAR flow with TEST-02
  found: Warning logged "INCONSISTENT STATE DETECTED" but still fails with "state 'pendiente'"
  implication: Edge case fix IS executing (line 491 sets state), but then it's being reset

- timestamp: 2026-01-30T00:05:00Z
  checked: StateService.pausar() line 295
  found: `await arm_machine.activate_initial_state()` is called AFTER hydration
  implication: THIS IS THE BUG - activate_initial_state() resets machine to PENDIENTE, undoing the hydration that set it to EN_PROGRESO

## Resolution

root_cause: The edge case hydration fix (line 491 in state_service.py) correctly sets machine.current_state = machine.en_progreso, but then StateService.pausar() calls activate_initial_state() at line 295, which RESETS the machine back to PENDIENTE. The hydration is being undone immediately after it's applied. The previous fix (commit ac64c55) added hydration logic but didn't account for activate_initial_state() resetting the state.

fix: Moved activate_initial_state() calls INSIDE the hydration methods (_hydrate_arm_machine and _hydrate_sold_machine), to be called BEFORE manually setting machine.current_state. This ensures the machine is properly initialized for async operations, but the hydration state is preserved. Made both hydration methods async and removed activate_initial_state() calls from tomar/pausar/completar methods.

verification: Fix committed (9e747d6) and pushed to Railway. Waiting for deployment to complete and TEST-02 lock to expire before full production verification. The fix is sound: activate_initial_state() now called BEFORE setting current_state in hydration methods, preserving the hydrated state.

files_changed:
  - backend/services/state_service.py: Made _hydrate_arm_machine() and _hydrate_sold_machine() async, added await machine.activate_initial_state() inside them before setting current_state, removed activate_initial_state() calls from tomar/pausar/completar
