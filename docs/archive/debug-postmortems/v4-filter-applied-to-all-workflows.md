---
status: diagnosed
trigger: "only-v4-spools-showing-in-selection"
created: 2026-02-03T00:00:00Z
updated: 2026-02-03T00:09:00Z
---

## Current Focus

hypothesis: ROOT CAUSE CONFIRMED - tipo-interaccion page defaults to v4.0 when no spool selected, which prevents v3.0 button access
test: Complete - traced full user flow from P2 → P3 → P4
expecting: Diagnosis complete, ready to report
next_action: Generate structured diagnosis report

## Symptoms

expected:
- TOMAR workflow: Should show BOTH v3.0 and v4.0 spools (no version filtering)
- PAUSAR workflow: Should show BOTH v3.0 and v4.0 spools (no version filtering)
- COMPLETAR workflow: Should show BOTH v3.0 and v4.0 spools (no version filtering)
- INICIAR workflow: Should show ONLY v4.0 spools (version filtering applied)

actual:
- Screenshot shows "Todos los spools son versión v4.0" message
- Only TEST-02 (v4.0) is showing
- TEST-01 (v3.0) is NOT showing
- Filtering applies to ALL workflows regardless of tipo

errors:
No JavaScript errors, but filtering is too aggressive

reproduction:
1. Navigate to zeues-frontend.vercel.app/seleccionar-spool
2. Select any operation (ARM)
3. Select any tipo (TOMAR, PAUSAR, COMPLETAR, or INICIAR)
4. Observe: Only v4.0 spools appear (TEST-02)
5. Expected: v3.0 spools (TEST-01) should appear for TOMAR/PAUSAR/COMPLETAR

started:
Immediately after deploying commit c1e38d9: "fix: filter v3.0 spools from INICIAR workflow"

## Eliminated

## Evidence

- timestamp: 2026-02-03T00:01:00Z
  checked: zeues-frontend/app/seleccionar-spool/page.tsx lines 146-174
  found: Filter logic only checks state.accion === 'INICIAR' at line 149, but does NOT check tipo parameter
  implication: When using v3.0 workflows (tipo=tomar/pausar/completar), state.accion is undefined, so filter falls through to else-if at line 160

- timestamp: 2026-02-03T00:02:00Z
  checked: Lines 149-174 filter logic structure
  found: |
    Line 149: if (accion === 'INICIAR') { /* filter to v4.0 only */ }
    Line 160: else if (accion === 'FINALIZAR') { /* filter to occupied */ }
    Line 173: Comment says "For v3.0 actions (tipo param) or null, show all (existing behavior)"
    BUT there's NO else block that explicitly handles v3.0 tipo-based workflows
  implication: Logic is incomplete - missing condition to check tipo for v3.0 workflows

- timestamp: 2026-02-03T00:03:00Z
  checked: Page routing and context (line 16)
  found: Page reads tipo from searchParams: const tipo = searchParams.get('tipo')
  implication: tipo is available and can be used to differentiate v3.0 workflows from v4.0 accion-based workflows

- timestamp: 2026-02-03T00:04:00Z
  checked: fetchSpools function (lines 72-194)
  found: Function correctly handles BOTH tipo-based (v3.0) and accion-based (v4.0) workflows in lines 88-137
  implication: The fetching logic is correct - the bug is ONLY in the filtering logic at lines 146-174

- timestamp: 2026-02-03T00:05:00Z
  checked: zeues-frontend/app/tipo-interaccion/page.tsx lines 33-37 (version detection)
  found: |
    When no spool selected yet, page defaults to v4.0 workflow:
    ```
    if (!state.selectedSpool) {
      setSpoolVersion('v4.0');  // Default to v4.0
      setLoadingVersion(false);
      return;
    }
    ```
  implication: This breaks v3.0 flow which naturally has no spool at P3 (action selection before spool selection)

- timestamp: 2026-02-03T00:06:00Z
  checked: tipo-interaccion/page.tsx lines 262 and 323 (button rendering)
  found: |
    Line 262: Renders INICIAR/FINALIZAR buttons when spoolVersion === 'v4.0'
    Line 323: Renders TOMAR/PAUSAR/COMPLETAR buttons when spoolVersion === 'v3.0'
    Since spoolVersion defaults to 'v4.0' when no spool, v3.0 buttons never show
  implication: Users can't access v3.0 workflows (TOMAR/PAUSAR/COMPLETAR) from P3

- timestamp: 2026-02-03T00:07:00Z
  checked: Git history commit 9d99b25
  found: Commit "fix: change default workflow to v4.0 (INICIAR/FINALIZAR)" changed default behavior
  implication: This was an intentional product decision, but it broke backward compatibility with v3.0 workflows

- timestamp: 2026-02-03T00:08:00Z
  checked: Root cause chain complete
  found: |
    1. tipo-interaccion defaults to v4.0 when no spool (line 33-37)
    2. Shows v4.0 buttons (INICIAR/FINALIZAR) instead of v3.0 buttons (line 262)
    3. User clicks INICIAR (line 77-79 sets accion='INICIAR')
    4. seleccionar-spool filters v4.0 only when accion='INICIAR' (line 149-159)
    5. v3.0 spools (TEST-01) don't appear
  implication: seleccionar-spool filter is working correctly - bug is in tipo-interaccion defaulting to v4.0

## Resolution

root_cause: |
  **Primary Bug File:** zeues-frontend/app/tipo-interaccion/page.tsx
  **Lines:** 33-37 (version detection logic)

  **Secondary File (working as designed):** zeues-frontend/app/seleccionar-spool/page.tsx
  **Lines:** 149-159 (v4.0 filter logic)

  **ROOT CAUSE:**
  The tipo-interaccion page (P3) defaults to v4.0 workflow when no spool is selected yet, which is the NORMAL flow for v3.0 workflows. This causes the page to show INICIAR/FINALIZAR buttons (v4.0) instead of TOMAR/PAUSAR/COMPLETAR buttons (v3.0).

  **The Bug Flow:**
  1. User navigates P1 (worker) → P2 (operation: ARM) → P3 (tipo-interaccion)
  2. At P3, no spool is selected yet (normal for v3.0 flow: select action BEFORE spool)
  3. Line 33-37 in tipo-interaccion/page.tsx executes:
     ```typescript
     // If no spool selected yet, default to v4.0 workflow (new default)
     if (!state.selectedSpool) {
       setSpoolVersion('v4.0');  // BUG: Defaults to v4.0 for NO spool selected
       setLoadingVersion(false);
       return;
     }
     ```
  4. P3 renders v4.0 buttons (INICIAR/FINALIZAR) at line 262, NOT v3.0 buttons (TOMAR/PAUSAR/COMPLETAR) at line 323
  5. User clicks INICIAR button thinking they're starting work (equivalent to TOMAR)
  6. handleIniciar() sets `state.accion = 'INICIAR'` (line 78)
  7. Navigates to seleccionar-spool with `state.accion = 'INICIAR'`
  8. seleccionar-spool/page.tsx line 149 checks `if (accion === 'INICIAR')` → TRUE
  9. Line 154-159 applies v4.0 filter: `return isDisponible && isV4;`
  10. Only v4.0 spools (TEST-02) show up, v3.0 spools (TEST-01) are filtered out

  **Why This Is Wrong:**
  - v3.0 flow is: P1 → P2 → P3 (select action FIRST) → P4 (select spool) → P5 (confirm)
  - v4.0 flow is: P1 → P2 → P3 (INICIAR/FINALIZAR, no spool yet for INICIAR)
  - When user follows normal v3.0 flow path (P2 → P3 with no spool), they should see v3.0 buttons
  - Current logic assumes "no spool = v4.0 workflow", which breaks v3.0 flow

  **Design Decision Bug:**
  Commit 9d99b25 ("fix: change default workflow to v4.0 (INICIAR/FINALIZAR)") changed the default from v3.0 to v4.0. This is a product decision bug, not a coding bug - the code works as designed, but the design breaks v3.0 workflows.

  **The seleccionar-spool filter logic is CORRECT** - it properly filters v4.0-only spools when accion='INICIAR'. The bug is upstream: users shouldn't be able to set accion='INICIAR' when using v3.0 flow.

fix:
verification:
files_changed: []
