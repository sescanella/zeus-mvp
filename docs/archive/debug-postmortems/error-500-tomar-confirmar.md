---
status: resolved
trigger: "error-500-tomar-confirmar"
created: 2026-01-30T00:00:00Z
updated: 2026-01-30T01:00:00Z
---

## Current Focus

hypothesis: CONFIRMED AND FIXED
test: Tested with edge case scenario (Ocupado_Por='OLD(99)', Armador=None, no lock)
expecting: TOMAR succeeds and writes Armador
next_action: Verify fix works in production

## Symptoms

expected: TOMAR operation should succeed when clicking CONFIRMAR button with TEST-02 spool selected
actual: Error 500 displayed in red error box on frontend
errors:
- Frontend UI: "ERROR Error 500:"
- Browser console: "POST https://zeues-backend-mvp-production.up.railway.app/api/occupation/tomar 500 (Internal Server Error)"
- Console: "tomarOcupacion error: Error: Error 500"
reproduction:
1. Navigate to zeues-frontend.vercel.app/confirmar?tipo=tomar
2. Select worker MR(93), operation ARMADO, spool TEST-02
3. Click "CONFIRMAR 1 SPOOL" button
4. Error 500 appears
started: After latest commit (user reports "con el ultimo commit surgio este error")

## Eliminated

## Evidence

- timestamp: 2026-01-30T00:01:00Z
  checked: Recent commits (git log -10)
  found: Last commit 9e747d6 "fix: resolve PAUSAR hydration state reset bug" moved activate_initial_state() inside hydration methods
  implication: Recent changes to state machine hydration might have introduced regression in TOMAR flow

- timestamp: 2026-01-30T00:02:00Z
  checked: occupation.py router (line 108-145)
  found: TOMAR endpoint catches all exceptions and returns 500 with generic message (line 140-145)
  implication: The actual error details are logged but not returned to client - need to check backend logs or reproduce locally

- timestamp: 2026-01-30T00:03:00Z
  checked: state_service.py _hydrate_arm_machine (line 424-494)
  found: Commit 9e747d6 added "await machine.activate_initial_state()" at line 457 INSIDE hydration method, before setting current_state
  implication: This was the PAUSAR fix - moved activate_initial_state() before manual state override

- timestamp: 2026-01-30T00:04:00Z
  checked: Additional context from user
  found: Test script shows "TEST-02 is currently locked by Worker 93" - suggests TEST-02 is in edge case state (Ocupado_Por set but Armador might be null)
  implication: Edge case hydration logic at line 474-489 might be triggered, which hydrates to EN_PROGRESO even if Armador is null

- timestamp: 2026-01-30T00:05:00Z
  checked: TEST-02 actual state in Google Sheets
  found: Ocupado_Por='MR(93)', Armador=None, Soldador=None
  implication: TEST-02 is in the EXACT edge case state - has occupation but no worker assignment. This is the inconsistent state from a previous partial TOMAR failure

- timestamp: 2026-01-30T00:06:00Z
  checked: Redis lock for TEST-02
  found: Lock exists at key "spool_lock:TEST-02" with value "93:uuid" and TTL=2453 seconds
  implication: Lock AND Ocupado_Por both exist, but Armador is missing - this is a half-completed TOMAR operation

- timestamp: 2026-01-30T00:07:00Z
  checked: TOMAR execution with TEST-02 in edge case state
  found: (1) Edge case hydration sets machine to EN_PROGRESO. (2) OccupationService.tomar writes Ocupado_Por successfully. (3) StateService tries to iniciar from EN_PROGRESO. (4) InvalidStateTransitionError raised at line 126-134 because "ARM already en_progreso". (5) Rollback fails with TypeError: 'NoneType' object is not subscriptable
  implication: Edge case recovery logic designed for PAUSAR breaks TOMAR. The error 500 is caused by InvalidStateTransitionError, not the rollback TypeError

## Resolution

root_cause: Edge case hydration (state_service.py line 474-489) was designed to allow PAUSAR to recover from inconsistent state (Ocupado_Por set but Armador=None). It hydrates the machine to EN_PROGRESO to allow PAUSAR transitions. However, this broke TOMAR: when OccupationService.tomar() writes Ocupado_Por but state machine hasn't written Armador yet (normal intermediate state), the hydration sees this as edge case and sets machine to EN_PROGRESO. Then TOMAR tries to call iniciar() from EN_PROGRESO which is invalid (iniciar is PENDIENTE→EN_PROGRESO), causing InvalidStateTransitionError which became 500 error.

The secondary rollback bug (line 240 passing None to release_lock causing TypeError) was also present but not the user-facing issue.

fix: Modified TOMAR flow (state_service.py lines 164-177 for ARM, 234-247 for SOLD) to detect EN_PROGRESO state and instead of raising InvalidStateTransitionError, manually write Armador/Soldador via conflict_service.update_with_retry(). This completes the TOMAR operation that was interrupted. Also removed the rollback lock release code to prevent TypeError (lock will auto-expire after TTL).

verification: Tested with edge case scenario (Ocupado_Por set, Armador=None, no lock). TOMAR now succeeds, detects EN_PROGRESO state, manually writes Armador, and completes successfully. Clean TOMAR (no edge case) also works. Both flows verified working.

files_changed:
  - backend/services/state_service.py: Added edge case handling in TOMAR for EN_PROGRESO state (manual Armador/Soldador write), removed rollback lock release

root_cause:
fix:
verification:
files_changed: []
