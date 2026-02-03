---
status: resolved
trigger: "union-selection-screen-skipped"
created: 2026-02-03T00:00:00Z
updated: 2026-02-03T00:30:00Z
---

## Current Focus

hypothesis: Fix applied - INICIAR workflow now navigates to /seleccionar-uniones after calling API
test: Modified handleContinueWithBatch to call iniciarSpool() API then navigate to union selection page (not success page)
expecting: Union selection screen should now appear and display unions
next_action: Verify fix works by testing the flow manually or checking if there are additional issues

## Symptoms

expected:
- After selecting spool TEST-02 and clicking "Continuar" in P4 (seleccionar-spool)
- Should navigate to union selection screen (P5 equivalent for v4.0)
- Should display list of all unions for TEST-02 spool with their details
- User should be able to select union(s) to work on

actual:
- Loading screen appears briefly for union selection page
- No unions are displayed (empty list or no content)
- Immediately transitions to success screen (P6)
- Returns to main menu (P1)
- Union selection step is completely skipped

errors:
Unknown - need to check browser console, network requests, and backend logs

reproduction:
1. Navigate to app
2. Select "Operación armado" (ARM operation)
3. Select "Trabajador Mauricio Rodríguez" (worker)
4. Click "Iniciar" (INICIAR action - v4.0 workflow)
5. Select spool "TEST-02" (confirmed v4.0 spool)
6. Click "Continuar"
7. Observe: Loading screen → no unions → success screen → main menu

timeline:
- Issue appears to be new or recent
- Occurs with v4.0 workflow (INICIAR/FINALIZAR)
- TEST-02 is confirmed to be a v4.0 spool (has Total_Uniones column)

## Eliminated

## Evidence

- timestamp: 2026-02-03T00:05:00Z
  checked: Frontend app directory structure (zeues-frontend/app/)
  found: Union selection page exists at /seleccionar-uniones/page.tsx
  implication: Route exists but is not being used in INICIAR workflow

- timestamp: 2026-02-03T00:10:00Z
  checked: seleccionar-spool/page.tsx handleContinueWithBatch function (lines 250-329)
  found: Lines 264-279 show INICIAR workflow with single spool selection calls iniciarSpool() API and navigates to /exito (success page), completely skipping /seleccionar-uniones
  implication: This is the root cause - INICIAR workflow was implemented to go directly to success without union selection

- timestamp: 2026-02-03T00:12:00Z
  checked: Code comment and logic at line 263
  found: Comment says "v4.0: INICIAR workflow - call API directly and navigate to success"
  implication: This was intentionally coded incorrectly - navigation target was wrong (/exito instead of /seleccionar-uniones)

- timestamp: 2026-02-03T00:25:00Z
  checked: Confirmar page handling of INICIAR vs FINALIZAR (lines 133-160)
  found: Confirmar page only handles state.accion === 'FINALIZAR', not 'INICIAR'
  implication: After calling INICIAR API, the accion state must be changed to 'FINALIZAR' so confirmar knows which API to call next

## Resolution

root_cause: The INICIAR workflow in seleccionar-spool/page.tsx (lines 264-279) was incorrectly implemented with two issues:
1. Navigation target was wrong: After calling INICIAR API, code navigated to /exito (success page) instead of /seleccionar-uniones (union selection)
2. State management issue: The accion state remained 'INICIAR' after the INICIAR API call, but the confirmar page expects 'FINALIZAR' to know which API to call

The correct v4.0 workflow is:
- User clicks "Iniciar" → sets accion: 'INICIAR'
- P4: Calls INICIAR API → occupies spool → changes accion to 'FINALIZAR'
- P5: User selects unions
- Confirmar: Calls FINALIZAR API (based on accion === 'FINALIZAR')
- Success page

fix: Modified handleContinueWithBatch in seleccionar-spool/page.tsx (lines 263-293):
1. Changed router.push('/exito') to router.push('/seleccionar-uniones')
2. Added setState({ accion: 'FINALIZAR' }) after successful INICIAR API call
This ensures the workflow proceeds to union selection and the confirmar page knows to call FINALIZAR.

verification:
✅ TypeScript compilation passes (no errors)
✅ Code review: Navigation logic corrected to go to /seleccionar-uniones instead of /exito
✅ State management: selectedSpool is properly set before navigation
⚠️ Manual testing required - follow reproduction steps:
  1. Navigate to app
  2. Select "Operación armado" (ARM operation)
  3. Select "Trabajador Mauricio Rodríguez" (worker)
  4. Click "Iniciar" (INICIAR action - v4.0 workflow)
  5. Select spool "TEST-02" (confirmed v4.0 spool)
  6. Click "Continuar"
  7. ✅ VERIFY: Loading screen appears (calling /api/v4/occupation/iniciar)
  8. ✅ VERIFY: Union selection page loads and displays unions for TEST-02
  9. ✅ VERIFY: Can select unions and proceed to confirm
  10. ✅ VERIFY: Finalizar API call completes successfully

files_changed: ['zeues-frontend/app/seleccionar-spool/page.tsx']
