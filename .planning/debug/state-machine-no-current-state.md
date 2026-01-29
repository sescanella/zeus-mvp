---
status: investigating
trigger: "state-machine-no-current-state"
created: 2026-01-29T00:00:00Z
updated: 2026-01-29T00:00:00Z
---

## Current Focus

hypothesis: CONFIRMED - _hydrate_arm_machine() sets current_state but doesn't call activate_initial_state()
test: Implement await arm_machine.activate_initial_state() after hydration
expecting: State machine will properly initialize and accept iniciar() transition
next_action: Fix StateService.tomar() to activate state machines after hydration

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

## Resolution

root_cause: StateService._hydrate_arm_machine() and _hydrate_sold_machine() set current_state directly without activating initial state. python-statemachine 2.5.0 requires await activate_initial_state() in async contexts before accessing current_state or triggering transitions. Additionally, iniciar() transition is called synchronously but callbacks are async.

fix: Add await activate_initial_state() after hydrating state machines in tomar(), pausar(), and completar() methods. Change iniciar() and completar() calls to await for proper async handling.

verification: Test POST /api/occupation/tomar with TEST-02 spool through frontend flow
files_changed: [backend/services/state_service.py]
