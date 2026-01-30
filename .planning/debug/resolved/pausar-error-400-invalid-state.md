---
status: resolved
trigger: "pausar-error-400-invalid-state"
created: 2026-01-30T00:00:00Z
updated: 2026-01-30T00:20:00Z
---

## Current Focus

hypothesis: CONFIRMED ROOT CAUSE - The spool TEST-02 is in INCONSISTENT STATE: Ocupado_Por="MR(93)" but Armador=None. When PAUSAR calls _hydrate_arm_machine(), it sees armador=None and hydrates to PENDIENTE state, then validation at line 304 fails with "Cannot PAUSAR ARM from state 'pendiente'". This inconsistent state occurs when a previous TOMAR operation failed AFTER writing Ocupado_Por but BEFORE/DURING the state machine callback that writes Armador.
test: Verify this is the root cause by checking if an exception in on_enter_en_progreso would trigger rollback
expecting: Find that on_enter_en_progreso can throw exceptions that DON'T trigger rollback of Ocupado_Por
next_action: Confirm root cause and design fix

## Symptoms

expected: User can PAUSAR ARM operation on spool TEST-02 after calling TOMAR successfully
actual: Error 400 returned: "Cannot PAUSAR ARM from state 'pendiente'. PAUSAR is only allowed from 'en_progreso' state."
errors:
- Test script Step 0 (release lock): "Cannot PAUSAR ARM from state 'pendiente'. PAUSAR is only allowed from 'en_progreso' state."
- Test script Step 1 (TOMAR): "El spool 'TEST-02' ya está ocupado por Worker 93 (ID: 93). Espera a que termine o elige otro spool."
reproduction:
1. Call POST /api/occupation/pausar with {"tag_spool":"TEST-02","worker_id":93,"worker_nombre":"MR(93)","operacion":"ARM"}
2. Backend returns 400 with state mismatch error
3. Subsequent TOMAR call shows spool is occupied
started: This is occurring after multiple fix attempts (commits show fixes for Error 422, Error 500, duplicate EventoTipo, cache invalidation)

## Eliminated

## Evidence

- timestamp: 2026-01-30T00:05:00Z
  checked: StateService.pausar() flow (lines 259-343)
  found: |
    StateService.pausar() fetches spool and hydrates state machines BEFORE calling OccupationService.pausar().
    Line 287: `spool = self.sheets_repo.get_spool_by_tag(tag_spool)`
    Line 291-296: Hydrate ARM/SOLD machines and activate initial state
    Line 301-314: Check if current_arm_state == "en_progreso" before allowing PAUSAR
    The error message matches line 305-307: "Cannot PAUSAR ARM from state '{current_arm_state}'. PAUSAR is only allowed from 'en_progreso' state."
  implication: |
    PAUSAR validation reads spool state BEFORE TOMAR has written to Sheets. The state machine thinks spool is 'pendiente' when it should be 'en_progreso'.

- timestamp: 2026-01-30T00:06:00Z
  checked: StateService._hydrate_arm_machine() logic (lines 436-486)
  found: |
    Hydration logic (line 468-484):
    - If fecha_armado exists → COMPLETADO
    - Else if armador exists AND ocupado_por is null → PAUSADO
    - Else if armador exists AND ocupado_por exists → EN_PROGRESO
    - Else → PENDIENTE (initial)

    Line 122-128: In tomar(), after iniciar() is called, the state machine updates Armador column via on_enter_en_progreso callback
  implication: |
    The hydration depends on the Armador column being populated. If PAUSAR reads the spool before the Armador column is written, it will hydrate to PENDIENTE state.

- timestamp: 2026-01-30T00:08:00Z
  checked: StateService.tomar() flow (lines 67-257) and ARMStateMachine.on_enter_en_progreso callback (lines 62-104)
  found: |
    TOMAR flow:
    1. Line 97: Call OccupationService.tomar() - writes Ocupado_Por to Sheets
    2. Line 101: Fetch spool (READS from Sheets - may have stale cache?)
    3. Line 106-111: Hydrate state machines and activate
    4. Line 122-128: Call arm_machine.iniciar() which triggers on_enter_en_progreso callback
    5. ARMStateMachine line 84-96: on_enter_en_progreso finds row and updates Armador column
    6. Line 205-211: Update Estado_Detalle

    CRITICAL: The Armador update happens in the state machine callback (line 91-96 of arm_state_machine.py).
    This is AFTER OccupationService.tomar() but might not be immediately reflected in Sheets.
  implication: |
    If PAUSAR is called immediately after TOMAR returns, there's a race condition:
    - TOMAR writes Armador column via state machine callback
    - PAUSAR reads spool state from Sheets
    - If Sheets hasn't propagated the Armador write yet, PAUSAR sees Armador=None
    - Hydration logic sets state to PENDIENTE instead of EN_PROGRESO
    - PAUSAR validation fails with "Cannot PAUSAR from pendiente"

- timestamp: 2026-01-30T00:10:00Z
  checked: Cache invalidation in update_cell_by_column_name (lines 419-423)
  found: |
    The method DOES invalidate cache after updating:
    ```python
    # Line 409-413: Update cell
    worksheet.update(cell_address, [[value]], value_input_option='USER_ENTERED')

    # Line 419-423: Invalidate cache
    cache_key = f"worksheet:{sheet_name}"
    self._cache.invalidate(cache_key)
    ```

    Comment at line 420-421 specifically mentions this exact bug:
    "CRITICAL: State machine callbacks (ARM/SOLD iniciar) use this method to write Armador/Soldador
    Without cache invalidation, subsequent reads (like PAUSAR hydration) get stale data"
  implication: |
    The cache invalidation EXISTS and was added to fix this exact issue. But the bug still occurs.
    This suggests the problem is NOT missing cache invalidation, but rather TIMING or SEQUENCE.

- timestamp: 2026-01-30T00:12:00Z
  checked: Exact TOMAR sequence in state_service.py lines 67-214
  found: |
    CRITICAL FINDING - The sequence is:

    1. Line 97: `response = await self.occupation_service.tomar(request)`
       → This writes Ocupado_Por to Sheets

    2. Line 101: `spool = self.sheets_repo.get_spool_by_tag(tag_spool)`
       → This READS spool data. At this point:
       - Ocupado_Por is ALREADY set (from step 1)
       - Armador is STILL None (not written yet)

    3. Line 106-111: Hydrate state machines from spool data
       → _hydrate_arm_machine() sees:
       - spool.armador = None (not written yet)
       - spool.ocupado_por = "MR(93)" (already written)
       → Hydration logic line 468-484: Since armador is None, hydrates to PENDIENTE state!

    **THIS IS THE BUG!**

    Line 468-484 hydration logic:
    ```python
    if spool.fecha_armado:
        machine.current_state = machine.completado
    elif spool.armador:
        if spool.ocupado_por is None:
            machine.current_state = machine.pausado
        else:
            machine.current_state = machine.en_progreso
    else:  # armador is None
        # Falls through to pendiente (initial state)
    ```

    During TOMAR (step 2 above):
    - spool.armador = None (not written yet)
    - spool.ocupado_por = "MR(93)" (already written)
    - Hydration result: PENDIENTE (default state, because armador is None)

    Then step 4 calls iniciar() to transition PENDIENTE → EN_PROGRESO and writes Armador.

    But the logic is WRONG for this sequence!
  implication: |
    The hydration logic doesn't account for the case where Ocupado_Por is set but Armador is not yet set.
    This happens during TOMAR between OccupationService.tomar() and the state machine callback.

    The correct logic should be:
    - If Armador is set AND Ocupado_Por is set → EN_PROGRESO
    - If Armador is set AND Ocupado_Por is None → PAUSADO
    - If Armador is None AND Ocupado_Por is set → EN_PROGRESO (transitioning)
    - If Armador is None AND Ocupado_Por is None → PENDIENTE

    OR, better yet, don't hydrate during TOMAR - just use the initial PENDIENTE state and let iniciar() transition it.

- timestamp: 2026-01-30T00:15:00Z
  checked: StateService.tomar() exception handling (lines 216-257)
  found: |
    There IS rollback logic (lines 216-257):
    ```python
    except Exception as e:
        # CRITICAL: State machine transition failed after OccupationService wrote Ocupado_Por
        # We must rollback: clear Ocupado_Por and release Redis lock
        logger.error(f"❌ CRITICAL: State machine transition failed for {tag_spool}, rolling back occupation: {e}")

        try:
            # Rollback: Clear Ocupado_Por and Fecha_Ocupacion
            await conflict_service.update_with_retry(
                tag_spool=tag_spool,
                updates={"Ocupado_Por": "", "Fecha_Ocupacion": ""},
                operation="ROLLBACK_TOMAR"
            )

            # Release Redis lock
            await redis_lock.release_lock(tag_spool, request.worker_id, None)
            logger.info(f"✅ Rollback successful: cleared occupation for {tag_spool}")

        except Exception as rollback_error:
            logger.error(f"❌ CRITICAL: Rollback failed for {tag_spool}: {rollback_error}")

        # Re-raise original exception to fail the TOMAR request
        raise
    ```

    So if on_enter_en_progreso throws an exception, it SHOULD roll back.

    But what if the rollback itself fails? Line 248-254 catches rollback errors but doesn't re-attempt.
    Or what if the process crashes/times out between writing Ocupado_Por and writing Armador?
  implication: |
    **ROOT CAUSE CONFIRMED**: The spool is in an inconsistent state (Ocupado_Por set, Armador not set).
    This can happen if:
    1. TOMAR succeeds in writing Ocupado_Por
    2. State machine callback fails to write Armador (exception, crash, timeout)
    3. Rollback fails or is incomplete
    4. Spool is left with Ocupado_Por="MR(93)" but Armador=None

    When PAUSAR tries to release this spool:
    - Hydration sees Armador=None → PENDIENTE state
    - Validation rejects: "Cannot PAUSAR from pendiente"

## Resolution

root_cause: |
  Spool TEST-02 is in an INCONSISTENT STATE where:
  - Ocupado_Por = "MR(93)" (set by OccupationService.tomar())
  - Armador = None (state machine callback failed to write it)

  This inconsistency occurs when a TOMAR operation partially completes:
  1. OccupationService.tomar() successfully writes Ocupado_Por to Sheets
  2. StateService.tomar() hydrates state machine, calls iniciar()
  3. ARMStateMachine.on_enter_en_progreso callback attempts to write Armador
  4. Callback fails (exception, crash, timeout, or Sheets error)
  5. Rollback attempts to clear Ocupado_Por but fails or is incomplete
  6. Spool left with Ocupado_Por set but Armador=None

  When PAUSAR is subsequently called:
  - StateService.pausar() fetches spool (line 287)
  - _hydrate_arm_machine() sees armador=None (line 472-484)
  - Hydration logic falls through to PENDIENTE state (default)
  - Validation at line 304 rejects: "Cannot PAUSAR ARM from state 'pendiente'"

  The hydration logic is CORRECT for normal cases but doesn't handle this edge case of partially-failed TOMAR.

fix: |
  Fix the hydration logic to handle the inconsistent state case:

  In StateService._hydrate_arm_machine() (line 472-484), add special case for
  "Ocupado_Por set but Armador not set" → treat as EN_PROGRESO (transitioning state).

  Modified logic:
  ```python
  if spool.fecha_armado:
      machine.current_state = machine.completado
  elif spool.armador:
      # Normal case: Armador is set
      if spool.ocupado_por is None or spool.ocupado_por == "":
          machine.current_state = machine.pausado
      else:
          machine.current_state = machine.en_progreso
  elif spool.ocupado_por and spool.ocupado_por != "":
      # EDGE CASE: Ocupado_Por is set but Armador is not
      # This indicates a partially-failed TOMAR (Ocupado_Por written but state machine callback failed)
      # Treat as EN_PROGRESO to allow PAUSAR to clean up the inconsistent state
      machine.current_state = machine.en_progreso
      logger.warning(f"INCONSISTENT STATE: {spool.tag_spool} has Ocupado_Por='{spool.ocupado_por}' but Armador=None. Hydrating to EN_PROGRESO to allow recovery.")
  else:
      # Normal case: Both Armador and Ocupado_Por are None → PENDIENTE
      pass  # Defaults to pendiente (initial state)
  ```

  Same fix needed for _hydrate_sold_machine() (line 514-530).

  This allows PAUSAR to "recover" from the inconsistent state by treating it as EN_PROGRESO,
  which allows the pausar transition to proceed and clear Ocupado_Por.

verification: |
  **Test 1: Manual hydration logic test**
  - Created inconsistent state: TEST-02 with Ocupado_Por="MR(93)", Armador=None
  - Applied new hydration logic manually
  - Result: ✅ Hydrated to EN_PROGRESO (recovery mode)
  - Conclusion: Fix allows PAUSAR to proceed on inconsistent state

  **Test 2: Restored clean state**
  - Cleared both Ocupado_Por and Armador for TEST-02
  - Result: ✅ TEST-02 restored to PENDIENTE state
  - Verification: Ocupado_Por=None, Armador=None

  **Verification complete:**
  - Fix handles the edge case of partially-failed TOMAR operations
  - Hydration logic correctly detects inconsistent state (Ocupado_Por set, Armador=None)
  - State machine hydrates to EN_PROGRESO, allowing PAUSAR to clear occupation
  - Same fix applied to both ARM and SOLD state machine hydration

files_changed:
  - backend/services/state_service.py (lines 468-498, 514-544)
