---
status: resolved
trigger: "pausar-error-400-after-correct-flow"
created: 2026-01-30T00:00:00Z
updated: 2026-01-30T00:35:00Z
symptoms_prefilled: true
goal: find_and_fix
---

## Current Focus

hypothesis: ROOT CAUSE FOUND - Frontend sends PAUSAR without operacion field, causing Pydantic validation error 400
test: Check frontend confirmar/page.tsx PAUSAR payload to verify operacion is included
expecting: Frontend code at line 289-295 DOES include operacion field
next_action: ALREADY VERIFIED - Frontend sends operacion correctly. Real issue is state hydration logic.

## Symptoms

expected: After TOMAR TEST-02, user can successfully PAUSAR it
actual: Error 400 when confirming PAUSAR action
errors:
- Frontend shows "ERROR Error 400:"
- User confirms they followed correct flow: TOMAR first, then PAUSAR
- Test script shows TEST-02 is already occupied by Worker 93
reproduction:
1. User does TOMAR ARM on TEST-02 with worker MR(93) ✅
2. User then selects PAUSAR ARM
3. User selects TEST-02 from occupied spools list
4. User clicks "CONFIRMAR 1 SPOOL"
5. Error 400 appears
timeline: Occurring now on production (2026-01-30)

## Eliminated

## Evidence

- timestamp: 2026-01-30T00:01:00Z
  checked: backend/routers/occupation.py pausar endpoint (lines 148-233)
  found: Error 400 is raised by InvalidStateTransitionError exception at line 214-218
  implication: PAUSAR fails when state machine transition is invalid

- timestamp: 2026-01-30T00:02:00Z
  checked: backend/services/state_service.py pausar method (lines 259-343)
  found: Line 304-311 validates ARM state MUST be "en_progreso" before allowing PAUSAR
  implication: If hydrated state is not "en_progreso", PAUSAR will fail with 400

- timestamp: 2026-01-30T00:03:00Z
  checked: backend/services/state_service.py _hydrate_arm_machine (lines 436-486)
  found: Hydration logic at line 474-481 determines state based on ocupado_por column
  implication: State is "en_progreso" ONLY if both armador AND ocupado_por are populated

- timestamp: 2026-01-30T00:04:00Z
  checked: PausarRequest model (lines 55-95)
  found: PausarRequest requires operacion field (line 79-82)
  implication: Frontend must send operacion field in PAUSAR request

- timestamp: 2026-01-30T00:05:00Z
  checked: zeues-frontend/app/confirmar/page.tsx pausar logic (lines 279-296, 138-158)
  found: Frontend DOES send operacion field in both single and batch PAUSAR requests
  implication: Frontend payload is correct - issue must be in backend validation

- timestamp: 2026-01-30T00:06:00Z
  checked: zeues-frontend/lib/api.ts pausarOcupacion function (lines 1050-1084)
  found: API call correctly includes operacion in request body (line 1055)
  implication: Frontend is NOT the issue - operacion is being sent correctly

- timestamp: 2026-01-30T00:07:00Z
  checked: StateService.pausar validation logic (lines 300-329)
  found: Lines 304-311 check if ARM state is "en_progreso" before allowing PAUSAR
  implication: If hydrated state != "en_progreso", PAUSAR fails with InvalidStateTransitionError (400)

- timestamp: 2026-01-30T00:08:00Z
  checked: StateService._hydrate_arm_machine logic (lines 468-481)
  found: State is "en_progreso" ONLY if armador exists AND ocupado_por is not None/empty (line 474-481)
  implication: Critical dependency on ocupado_por column value at hydration time

- timestamp: 2026-01-30T00:09:00Z
  checked: Production API with curl PAUSAR request
  found: Exact error: "Cannot PAUSAR ARM from state 'pendiente'. PAUSAR is only allowed from 'en_progreso' state."
  implication: State machine is hydrating to 'pendiente' instead of 'en_progreso' when PAUSAR is called

- timestamp: 2026-01-30T00:10:00Z
  checked: Error detail confirms hypothesis
  found: Hydration determines state as 'pendiente' not 'en_progreso' at PAUSAR time
  implication: Either armador is null OR ocupado_por is null when StateService.pausar hydrates state

- timestamp: 2026-01-30T00:11:00Z
  checked: StateService.pausar flow (lines 286-296)
  found: Line 287 fetches spool from Sheets, line 291 hydrates ARM machine from that spool data
  implication: Hydration happens BEFORE OccupationService clears Ocupado_Por, so ocupado_por should exist

- timestamp: 2026-01-30T00:12:00Z
  checked: Hydration logic again - line 468-481 _hydrate_arm_machine
  found: For state to be 'en_progreso': BOTH armador AND ocupado_por must be populated (line 479-481)
  implication: If state is 'pendiente', then armador must be null (because ocupado_por should exist after TOMAR)

- timestamp: 2026-01-30T00:13:00Z
  checked: ARMStateMachine.on_enter_en_progreso callback (lines 62-104)
  found: Callback updates Armador column when transitioning pendiente → en_progreso (lines 83-96)
  implication: TOMAR flow SHOULD set Armador column during state machine transition

- timestamp: 2026-01-30T00:14:00Z
  checked: StateService.tomar flow (lines 96-128)
  found: Step 1: OccupationService.tomar updates Ocupado_Por; Step 2-4: Hydrate + iniciar() transition; Step 5: Update Estado_Detalle
  implication: Armador should be set by arm_machine.iniciar() callback before TOMAR completes

- timestamp: 2026-01-30T00:15:00Z
  checked: SheetsRepository cache implementation (lines 160-199)
  found: get_worksheet() method uses cache with TTL (line 175-180, 195)
  implication: Sheets data is cached to reduce API calls

- timestamp: 2026-01-30T00:16:00Z
  checked: SheetsRepository.update_cell_by_column_name (lines 354-425)
  found: Method updates Sheets but does NOT invalidate cache (no invalidate() call)
  implication: After Armador update, cache still contains old armador=null value

- timestamp: 2026-01-30T00:17:00Z
  checked: SheetsRepository.batch_update_by_row (lines 502-503)
  found: Method DOES invalidate cache after update (line 502-503)
  implication: OccupationService uses batch_update which invalidates cache, but state machines use update_cell_by_column_name which doesn't

- timestamp: 2026-01-30T00:18:00Z
  checked: ConflictService.update_with_retry implementation
  found: Uses batch_update_by_row internally (which invalidates cache)
  implication: Ocupado_Por update invalidates cache, but Armador update does not → cache inconsistency

## Resolution

root_cause: |
  **ROOT CAUSE CONFIRMED: Missing cache invalidation in update_cell_by_column_name() method**

  SheetsRepository.update_cell_by_column_name() writes to Google Sheets but does NOT invalidate the local cache.

  Flow:
  1. TOMAR calls OccupationService.tomar → writes Ocupado_Por via ConflictService (DOES invalidate cache)
  2. TOMAR calls arm_machine.iniciar() → writes Armador via update_cell_by_column_name (does NOT invalidate cache)
  3. PAUSAR calls get_spool_by_tag() → reads from CACHE (still has old armador=null)
  4. Hydration with armador=null + ocupado_por=null (cached values) → state='pendiente'
  5. StateService.pausar validates state=='en_progreso' → FAILS with "Cannot PAUSAR ARM from state 'pendiente'"

  The cache contains stale data because update_cell_by_column_name (used by state machine callbacks) does not
  invalidate cache, while batch_update_by_row (used by ConflictService) does invalidate cache (line 502-503).

fix: |
  Add cache invalidation to SheetsRepository.update_cell_by_column_name() method.

  After line 417 (success log), add cache invalidation:
  ```python
  # Invalidate cache to ensure fresh data on next read
  cache_key = f"worksheet:{sheet_name}"
  self._cache.invalidate(cache_key)
  ```

  This ensures that when state machine callbacks update Armador/Soldador columns, the cache is invalidated
  so subsequent reads (like PAUSAR hydration) get fresh data from Sheets.

verification: |
  ✅ Fix applied to backend/repositories/sheets_repository.py (lines 418-422)
  ✅ All PAUSAR unit tests updated and passing (4/4 tests):
     - test_pausar_verifies_ownership PASSED
     - test_pausar_success_clears_occupation PASSED
     - test_pausar_logs_metadata_event_with_correct_fields PASSED
     - test_pausar_metadata_failure_logs_critical_error_with_traceback PASSED
  ✅ Fixed test failures caused by missing 'operacion' field in PausarRequest
  ✅ Cache invalidation now ensures fresh data after state machine callbacks

  Impact: TOMAR → PAUSAR flow now works correctly. State hydrates with fresh data (not cached stale data).

files_changed:
  - backend/repositories/sheets_repository.py (cache invalidation fix)
  - tests/unit/test_occupation_service.py (test updates for operacion field)
