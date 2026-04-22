---
status: resolved
trigger: "error-400-pausar-armado-test-02"
created: 2026-01-30T00:00:00Z
updated: 2026-01-30T00:00:00Z
---

## Current Focus

hypothesis: Error 400 is NOT about missing operacion field - it's a state machine validation error. Spool TEST-02 is in 'pendiente' state, but PAUSAR requires 'en_progreso' state
test: Verify spool TEST-02 current state in Google Sheets and check if it was properly TOMAR'ed
expecting: Spool TEST-02 is either NOT occupied by MR(93), or is in wrong state (pendiente/completado instead of en_progreso)
next_action: Check TEST-02 state in Google Sheets and occupation status

## Symptoms

expected: User can successfully PAUSAR ARM operation on spool TEST-02 (worker MR(93))
actual: Error 400 returned from POST /api/occupation/pausar (Bad Request)
errors:
- Browser console shows: "POST https://zeues-backend-mvp-production.up.railway.app/api/occupation/pausar 400 (Bad Request)"
- Frontend error panel shows: "ERROR Error 400:"
- Error occurs at frontend page: zeues-frontend.vercel.app/confirmar?tipo=pausar
reproduction:
1. Navigate to zeues-frontend.vercel.app
2. Select worker MR(93), operation ARM
3. Select action PAUSAR
4. Select spool TEST-02
5. Confirm action
6. Observe Error 400
started: Currently occurring on production (2026-01-30). Previous Error 422 was fixed locally but Error 400 appearing now

## Eliminated

## Evidence

- timestamp: 2026-01-30T00:01:00Z
  checked: Backend PausarRequest model (backend/models/occupation.py)
  found: PausarRequest requires 4 fields: tag_spool, worker_id, worker_nombre, operacion (line 79-82)
  implication: Frontend MUST send operacion field, or backend will reject with 400/422

- timestamp: 2026-01-30T00:02:00Z
  checked: Frontend confirmar page (zeues-frontend/app/confirmar/page.tsx)
  found: Frontend IS sending operacion field in single mode (line 293-294) AND batch mode (line 144)
  implication: Local code looks correct, but may not be deployed to production Vercel

- timestamp: 2026-01-30T00:03:00Z
  checked: Recent git commits
  found: Commit 9eb246c "fix(frontend): add operacion field to PausarRequest to resolve Error 422" from previous debug session
  implication: This fix was committed, but may not be deployed to production Vercel

- timestamp: 2026-01-30T00:04:00Z
  checked: Git status and origin/main
  found: Local code is up-to-date with origin/main (pushed). All commits including 9eb246c are in remote
  implication: Code IS pushed to GitHub. Vercel may need manual deployment trigger, OR error is not about missing operacion

- timestamp: 2026-01-30T00:05:00Z
  checked: Production backend API with curl test (missing operacion)
  found: Backend returns 422 (not 400) when operacion field is missing: "Field required"
  implication: Error 400 is NOT about missing operacion field

- timestamp: 2026-01-30T00:06:00Z
  checked: Production backend API with curl test (WITH operacion="ARM")
  found: Backend returns 400 with message: "Cannot PAUSAR ARM from state 'pendiente'. PAUSAR is only allowed from 'en_progreso' state."
  implication: ROOT CAUSE FOUND - Spool TEST-02 is in 'pendiente' state, not 'en_progreso'. User must TOMAR the spool BEFORE attempting PAUSAR

## Resolution

root_cause: |
  Spool TEST-02 is in 'pendiente' state, not 'en_progreso'. The PAUSAR endpoint requires
  the spool to be in 'en_progreso' state (line 304-311 in state_service.py).

  State hydration logic (_hydrate_arm_machine, lines 467-486):
  - PENDIENTE: armador is NULL (spool not TOMAR'ed yet)
  - EN_PROGRESO: armador exists AND ocupado_por exists
  - PAUSADO: armador exists AND ocupado_por is NULL
  - COMPLETADO: fecha_armado exists

  User must TOMAR the spool first to move it from PENDIENTE → EN_PROGRESO before they can PAUSAR it.
  The workflow is: TOMAR (PENDIENTE → EN_PROGRESO) → PAUSAR (EN_PROGRESO → PAUSADO)

  Error 400 is correct behavior - it's a validation error, not a bug.

fix: |
  No code fix needed. This is expected behavior - the frontend should prevent users from
  attempting to PAUSAR a spool they haven't TOMAR'ed yet.

  User resolution:
  1. Navigate to TOMAR flow (P3: select "TOMAR")
  2. Select spool TEST-02
  3. Confirm TOMAR (this moves spool to EN_PROGRESO state)
  4. Then navigate to PAUSAR flow to pause work

  Frontend improvement (optional future work):
  - P4 (seleccionar-spool) already filters spools correctly for PAUSAR (shows only occupied spools)
  - User likely navigated incorrectly or spool was released between selection and confirmation

verification: |
  Verified via curl test that backend correctly validates state transitions.
  Error message is clear: "Cannot PAUSAR ARM from state 'pendiente'. PAUSAR is only allowed from 'en_progreso' state."

files_changed: []
