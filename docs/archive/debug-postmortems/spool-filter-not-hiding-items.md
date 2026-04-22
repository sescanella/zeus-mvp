---
status: resolved
trigger: "spool-filter-not-hiding-items"
created: 2026-01-26T00:00:00Z
updated: 2026-01-26T00:08:00Z
---

## Current Focus

hypothesis: RESOLVED - Bug was already fixed in commit 2ee4678 (changed spools.map to filteredSpools.map)
test: Verified current code uses filteredSpools.map() and git diff confirms it was fixed
expecting: User may be experiencing browser cache issue with stale JavaScript bundle
next_action: Instruct user to hard refresh browser (Ctrl+Shift+R or Cmd+Shift+R)

## Symptoms

expected: Al buscar por TAG, la tabla debería mostrar solo el spool que coincide con el TAG ingresado. Los demás spools deberían desaparecer de la vista.

actual: El contador muestra "0/1 filtrados" correctamente (indica que detecta 1 spool coincidente), pero todos los spools permanecen visibles en la tabla. El filtrado no oculta los items que no coinciden.

errors: Usuario no ha revisado la consola del navegador aún. No hay reportes de errores visibles en UI.

reproduction:
1. Ir a la página de selección de spools (armado-iniciar)
2. Usar el buscador e ingresar un TAG de spool
3. Observar que el contador cambia a "0/1 filtrados"
4. Observar que todos los spools siguen mostrándose (no se filtran visualmente)

started: No estoy seguro - primera vez probando o funcionalidad reciente.

## Eliminated

## Evidence

- timestamp: 2026-01-26T00:01:00Z
  checked: seleccionar-spool/page.tsx lines 90-93
  found: filteredSpools computed correctly with both NV and TAG filters
  implication: Filter logic is working - counter uses filteredSpools.length (line 243)

- timestamp: 2026-01-26T00:01:30Z
  checked: seleccionar-spool/page.tsx line 273 (table body rendering)
  found: {filteredSpools.map((spool) => ... )} - WAIT, code shows filteredSpools.map()
  implication: Code looks CORRECT - need to investigate further

- timestamp: 2026-01-26T00:02:00Z
  checked: Re-reading line 273 carefully
  found: Code actually DOES use filteredSpools.map() on line 273
  implication: The rendering logic is correct. Bug might be elsewhere or already fixed.

- timestamp: 2026-01-26T00:03:00Z
  checked: Filter logic lines 90-93 for edge case behavior
  found: Filter uses .includes() which returns true for empty string - this is CORRECT behavior (empty filter = show all)
  implication: If user types a TAG and counter shows "0/1 filtrados", the filter is working. The code looks correct.

- timestamp: 2026-01-26T00:04:00Z
  checked: Analyzing user's report more carefully
  found: User says counter shows "0/1 filtrados" (0 selected out of 1 filtered) which proves filteredSpools.length = 1
  implication: If only 1 spool is in filteredSpools and table uses filteredSpools.map(), only 1 row should render. Code is correct.

- timestamp: 2026-01-26T00:05:00Z
  checked: Considering if this is a stale bug report
  found: Code on main branch shows filteredSpools.map() on line 273
  implication: Either bug was already fixed, or there's a deployed version mismatch, or user needs to refresh browser cache

- timestamp: 2026-01-26T00:06:00Z
  checked: Git history for seleccionar-spool/page.tsx
  found: Commit 2ee4678 "feat: Complete v2.0 multiselect UI" changed spools.map() to filteredSpools.map()
  implication: Bug was fixed when multiselect feature was implemented

- timestamp: 2026-01-26T00:07:00Z
  checked: Current branch is main (not v2.0-dev as mentioned in CLAUDE.md)
  found: CLAUDE.md says "Branch: v2.0-dev" but git shows we're on main, and v2.0-dev doesn't exist
  implication: Documentation is outdated - development is now on main branch

## Resolution

root_cause: Bug was already fixed in commit 2ee4678. The old code used `spools.map()` which rendered ALL spools regardless of filter. This was changed to `filteredSpools.map()` which correctly renders only filtered items. Current main branch code is correct (line 273 uses filteredSpools.map()).

fix: No fix needed - code is already correct. User is likely experiencing browser cache issue with stale JavaScript bundle from before the fix was deployed.

verification: Verified by:
1. Reading current code (line 273 uses filteredSpools.map()) ✓
2. Checking git history (bug fixed in commit 2ee4678) ✓
3. Confirming filter logic works correctly (lines 90-93) ✓
4. Confirming counter uses filteredSpools.length (line 243) ✓

files_changed: []

## Recommended Action

User should perform a hard refresh to clear browser cache:
- **Chrome/Firefox (Windows/Linux):** Ctrl + Shift + R
- **Chrome/Firefox (Mac):** Cmd + Shift + R
- **Safari (Mac):** Cmd + Option + R

If issue persists after hard refresh, check that frontend is deployed from latest main branch commit (c20016b) which includes the fix.
