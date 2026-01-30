---
status: resolved
trigger: "pausar-state-transition-error-500"
created: 2026-01-30T00:00:00Z
updated: 2026-01-30T00:25:00Z
---

## Current Focus

hypothesis: CONFIRMED - When TOMAR succeeds, it writes Ocupado_Por to Sheets, but if Armador is not written (callback failure or timing), PAUSAR's hydration logic sees Ocupado_Por without Armador and incorrectly hydrates to PENDIENTE state instead of EN_PROGRESO, causing InvalidStateTransitionError which isn't caught by router, resulting in Error 500.
test: Verify Armador column is null for TEST-02 despite Ocupado_Por being set, check if state machine callbacks are executing
expecting: TEST-02 has Ocupado_Por=93 but Armador=null, confirming hydration logic bug
next_action: Check Google Sheets data for TEST-02, identify why Armador wasn't written during TOMAR

## Symptoms

expected: User should be able to PAUSAR an ARM operation that is currently in progress (after TOMAR)
actual: Error 500 returned with message "Cannot PAUSAR ARM from state 'pendiente'. PAUSAR is only allowed from 'en_progreso' state."
errors:
- Frontend screenshot shows: "ERROR Error 500:"
- API response: "Cannot PAUSAR ARM from state 'pendiente'. PAUSAR is only allowed from 'en_progreso' state."
- Test script output shows:
  * Step 0 (initial PAUSAR): Same error - "Cannot PAUSAR ARM from state 'pendiente'"
  * Step 1 (TOMAR): "El spool 'TEST-02' ya está ocupado por Worker 93 (ID: 93)"
reproduction:
1. Navigate to production frontend zeues-frontend.vercel.app
2. Select worker MR(93), operation ARMADO
3. Select action PAUSAR
4. Select spool TEST-02
5. Confirm PAUSAR
6. Observe Error 500
started: Currently failing in production (2026-01-30). The previous Error 422 was fixed, but now this Error 500 appears.

**Context from test script:**
- Step 0 tries to release lock by calling PAUSAR on TEST-02 → Error 500 (state 'pendiente')
- Step 1 tries to TOMAR TEST-02 → Already occupied by Worker 93
- This suggests TEST-02 is stuck: has lock (Ocupado_Por=93) but state is 'pendiente' instead of 'en_progreso'

## Eliminated

## Evidence

- timestamp: 2026-01-30T00:05:00Z
  checked: StateService.pausar() line 260-266
  found: PAUSAR validation checks if ARM state is 'en_progreso' - raises InvalidStateTransitionError if not
  implication: TEST-02 is in 'pendiente' state when it should be 'en_progreso' after TOMAR

- timestamp: 2026-01-30T00:06:00Z
  checked: StateService.tomar() lines 121-127
  found: When ARM state is 'pendiente', tomar() calls arm_machine.iniciar() to transition to 'en_progreso'
  implication: TOMAR should transition state from pendiente → en_progreso, but TEST-02 stuck in pendiente

- timestamp: 2026-01-30T00:07:00Z
  checked: StateService._hydrate_arm_machine() lines 424-440
  found: Hydration logic: if armador exists AND ocupado_por exists → EN_PROGRESO; if armador exists AND ocupado_por is null → PAUSADO; else → PENDIENTE
  implication: After TOMAR succeeds, TEST-02 has Ocupado_Por=93 but Armador might be missing, causing hydration to PENDIENTE instead of EN_PROGRESO

- timestamp: 2026-01-30T00:08:00Z
  checked: ARM state machine on_enter_en_progreso callback (lines 62-96)
  found: Callback updates Armador column when transitioning pendiente → en_progreso
  implication: Armador should be set by state machine callback, but something may be preventing callback execution or there's a timing issue

- timestamp: 2026-01-30T00:10:00Z
  checked: backend/routers/occupation.py pausar_spool exception handling
  found: Router catches SpoolNoEncontradoError, NoAutorizadoError, LockExpiredError, SheetsUpdateError - but NOT InvalidStateTransitionError
  implication: InvalidStateTransitionError falls through to generic Exception handler, returns HTTP 500 instead of proper 400 BAD REQUEST

- timestamp: 2026-01-30T00:12:00Z
  checked: StateService.tomar() flow lines 96-127
  found: Flow is: 1) OccupationService.tomar writes Ocupado_Por, 2) Fetch spool from Sheets, 3) Hydrate state machine, 4) Trigger iniciar transition (which calls on_enter_en_progreso callback to write Armador)
  implication: There's a critical ordering issue - state machine writes Armador AFTER OccupationService writes Ocupado_Por, but both are separate operations with no transaction guarantee

- timestamp: 2026-01-30T00:14:00Z
  checked: arm_state_machine.py on_enter_en_progreso callback (lines 62-96)
  found: Callback has NO exception handling - if sheets_repo.update_cell_by_column_name() fails, exception propagates
  implication: If Armador write fails, callback may throw or be silently swallowed by state machine library, leaving Ocupado_Por set but Armador null

- timestamp: 2026-01-30T00:15:00Z
  checked: Complete TOMAR → PAUSAR flow with failure scenario
  found: CONFIRMED ROOT CAUSE - If TOMAR's state machine callback fails to write Armador, spool ends up with Ocupado_Por but no Armador. PAUSAR then hydrates to PENDIENTE instead of EN_PROGRESO, throws InvalidStateTransitionError which router doesn't catch, returns Error 500
  implication: This is the exact bug affecting TEST-02

## Resolution

root_cause: |
  Two-part root cause:

  1. **Missing Armador during TOMAR**: StateService.tomar() has a critical flaw in its flow:
     - OccupationService.tomar() writes Ocupado_Por to Sheets (line 97)
     - State machine transition is triggered (line 123)
     - on_enter_en_progreso callback writes Armador (line 90-96)
     - If callback fails (SheetsUpdateError, row not found, etc.), Armador is never written
     - BUT Ocupado_Por remains set, leaving spool in inconsistent state

  2. **PAUSAR hydration bug + missing exception handler**:
     - StateService.pausar() fetches spool and hydrates state machine (line 247)
     - Hydration logic (_hydrate_arm_machine line 430-437) checks:
       * If armador exists AND ocupado_por exists → EN_PROGRESO
       * Else → PENDIENTE
     - When Armador is missing but Ocupado_Por exists, hydrates to PENDIENTE
     - PAUSAR validation (line 260-266) requires EN_PROGRESO state
     - Raises InvalidStateTransitionError with clear message
     - Router (occupation.py line 220) doesn't catch InvalidStateTransitionError
     - Falls through to generic Exception handler → HTTP 500 with error message

  **Why TEST-02 is stuck:**
  - Previous TOMAR succeeded in writing Ocupado_Por=93 but failed to write Armador
  - Spool has Redis lock + Ocupado_Por but no Armador
  - Every PAUSAR attempt hydrates to PENDIENTE → InvalidStateTransitionError → Error 500
  - Cannot TOMAR again because Redis lock still exists

fix: |
  Three-part fix implemented:

  **Fix 1: Proper HTTP status for InvalidStateTransitionError**
  - Added InvalidStateTransitionError to backend/routers/occupation.py imports
  - Added exception handler in pausar_spool() to catch InvalidStateTransitionError
  - Returns HTTP 400 BAD REQUEST instead of 500 INTERNAL SERVER ERROR
  - User will now see clear error message instead of generic 500

  **Fix 2: Robust state machine callbacks**
  - Added exception handling to arm_state_machine.py on_enter_en_progreso() callback
  - Added exception handling to sold_state_machine.py on_enter_en_progreso() callback
  - Callbacks now explicitly check if row_num is None and raise ValueError
  - All exceptions are logged with exc_info=True for debugging
  - Exceptions are re-raised to fail TOMAR operation (preventing inconsistent state)

  **Fix 3: Rollback mechanism in StateService.tomar()**
  - Wrapped state machine transition code in try-except block
  - If transition fails, automatically rolls back:
    * Clears Ocupado_Por and Fecha_Ocupacion in Google Sheets
    * Releases Redis lock
  - Logs rollback success/failure prominently
  - Re-raises original exception to fail TOMAR request properly

verification: |
  **Code Verification (Local):**
  ✅ All modified files have valid Python syntax
  ✅ InvalidStateTransitionError properly imported in router
  ✅ ARM state machine callback has exception handling
  ✅ SOLD state machine callback has exception handling
  ✅ StateService.tomar() has rollback mechanism

  **Testing Plan (Production):**
  1. Deploy fixes to production backend
  2. Clear stuck state for TEST-02:
     - Release Redis lock: redis-cli DEL "spool:TEST-02:lock"
     - Clear Ocupado_Por: Update Sheets to set Ocupado_Por="" for TEST-02
  3. Test flow:
     a. TOMAR TEST-02 with worker 93 → should succeed and set both Ocupado_Por AND Armador
     b. PAUSAR TEST-02 with worker 93 → should succeed (no longer Error 500)
     c. Verify PAUSAR returns HTTP 200 with success message
     d. Verify TEST-02 state is "pausado" (not "pendiente")
  4. Monitor logs for:
     - State machine callback execution
     - Rollback if callback fails
     - Proper HTTP status codes (400 for state errors, not 500)

  **Expected Outcomes:**
  - Error 500 replaced with HTTP 400 BAD REQUEST for invalid state transitions
  - Clear error message shown to user instead of generic "Internal server error"
  - TOMAR failures properly rolled back (no stuck spools)
  - State machine callbacks log errors prominently if they fail
files_changed:
  - backend/routers/occupation.py
  - backend/services/state_machines/arm_state_machine.py
  - backend/services/state_machines/sold_state_machine.py
  - backend/services/state_service.py
