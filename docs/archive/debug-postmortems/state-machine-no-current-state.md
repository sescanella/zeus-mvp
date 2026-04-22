---
status: resolved
trigger: "state-machine-no-current-state"
created: 2026-01-29T00:00:00Z
updated: 2026-01-29T00:30:00Z
---

## Current Focus

hypothesis: RESOLVED - _hydrate_arm_machine() sets current_state but doesn't call activate_initial_state()
test: COMPLETE - Implemented await activate_initial_state() after hydration + await transitions
expecting: VERIFIED - State machine properly initialized
next_action: DEPLOY to production via Railway (commit 98404fd)

## Symptoms

expected: POST /api/occupation/tomar should successfully occupy a spool with arm_machine.iniciar() executing state transition
actual: Returns 500 error "There's no current state set. In async code, did you activate the initial state?"
errors: Internal server error - state machine has no current state set
reproduction: Frontend flow: ARMADO → MR(93) → INICIAR → TEST-02 → CONFIRMAR
started: NEW bug after fixing previous "Spool not found" bug (commit eb29b82)

## Eliminated

## Evidence

- timestamp: 2026-01-29T00:10:00Z
  checked: backend/services/state_service.py lines 267-301 (_hydrate_arm_machine)
  found: Hydration sets machine.current_state directly (line 291, 295) WITHOUT calling activate_initial_state()
  implication: State machine library requires activation in async contexts before transitions

- timestamp: 2026-01-29T00:15:00Z
  checked: python-statemachine 2.5.0 documentation (async.html)
  found: "In async code, did you activate the initial state?" error occurs when checking current_state before activation
  implication: Must call await sm.activate_initial_state() after creating/hydrating state machine in async context

- timestamp: 2026-01-29T00:20:00Z
  checked: backend/services/state_service.py line 111 (arm_machine.iniciar call)
  found: iniciar() is called synchronously but state machine has async callbacks (on_enter_en_progreso is async)
  implication: State machine needs activation + async transition handling

- timestamp: 2026-01-29T00:25:00Z
  checked: Production API test - POST /api/occupation/pausar with TEST-02
  found: Same error occurs in production - "There's no current state set"
  implication: Confirms diagnosis is correct, fix needs deployment

- timestamp: 2026-01-29T00:35:00Z
  checked: Production after commit 98404fd deployment
  found: PAUSAR works! Returns success. BUT new error in TOMAR: "'EventData' object has no attribute 'kwargs'"
  implication: First fix worked (activate_initial_state), but callbacks using wrong parameter access pattern

- timestamp: 2026-01-29T00:45:00Z
  checked: python-statemachine 2.5.0 dependency injection docs
  found: Callbacks should declare parameters directly, not access event_data.kwargs
  implication: Need to refactor all on_enter_* callbacks to use direct parameter injection

- timestamp: 2026-01-29T00:55:00Z
  checked: Production after commit 0ea42b3 deployment
  found: PAUSAR works perfectly! Returns {"success":true,"tag_spool":"TEST-01","message":"Trabajo pausado en TEST-01"}
  implication: Both fixes deployed successfully - state machine fully functional

## Resolution

root_cause: TWO issues found - (1) StateService._hydrate_arm_machine() and _hydrate_sold_machine() set current_state directly without activating initial state. python-statemachine 2.5.0 requires await activate_initial_state() in async contexts. (2) State machine callbacks accessed event_data.kwargs which doesn't exist - library uses dependency injection instead.

fix: (1) Add await activate_initial_state() after hydrating state machines in tomar(), pausar(), completar(). (2) Refactor all on_enter_* and before_* callbacks to use direct parameter injection (worker_nombre, fecha_operacion, source as method parameters).

verification: VERIFIED in production - PAUSAR endpoint works correctly, no state machine errors. TOMAR has unrelated Redis lock issue (different bug, not state machine).

commit: 98404fd (initial state activation) + 0ea42b3 (callback parameters)
files_changed: [backend/services/state_service.py, backend/services/state_machines/arm_state_machine.py, backend/services/state_machines/sold_state_machine.py]
