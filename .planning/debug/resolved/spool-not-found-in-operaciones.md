---
status: resolved
trigger: "spool-not-found-in-operaciones"
created: 2026-01-29T00:00:00Z
updated: 2026-01-29T00:15:00Z
---

## Current Focus

hypothesis: RESOLVED - Fix exists in main branch (commit b68e3b8), waiting for Railway deployment
test: Triggered Railway redeploy via empty commit 697e4f1
expecting: Railway to deploy latest code within 5-10 minutes
next_action: Manual verification required - user must check Railway dashboard or wait for auto-deploy to complete

## Symptoms

expected: Should insert record in Metadata sheet and update Operaciones columns (Armador, Fecha_Armado)
actual: Error "Spool 'TEST-02' no encontrado en hoja Operaciones" displayed on confirmation page
errors:
  - Frontend shows: "ERROR: Spool 'TEST-02' no encontrado en hoja Operaciones"
  - Console shows: "tomarOcupacion error: Error: Spool 'TEST-02' no encontrado en hoja Operaciones"
  - Backend 404 response from POST https://zeues-backend-mvp-production.up.railway.app/api/ocupacion/tomar
reproduction:
  1. Select operation ARMADO
  2. Select worker MR(93)
  3. Select action INICIAR
  4. Select any spool (e.g., TEST-02)
  5. Click "CONFIRMAR 1 SPOOL"
  6. Error appears
timeline: After recent code changes (was working before). Affects ALL test spools, not just TEST-02.
verification: TEST-02 is confirmed to exist in Operaciones sheet with Fecha_Materiales filled

## Eliminated

## Evidence

- timestamp: 2026-01-29T00:01:00Z
  checked: Backend endpoint POST /api/ocupacion/tomar
  found: Routes to StateService.tomar() (line 108 occupation.py)
  implication: Error originates from StateService or OccupationService.tomar()

- timestamp: 2026-01-29T00:02:00Z
  checked: OccupationService.tomar() method (occupation_service.py line 91-245)
  found: Line 127 calls sheets_repository.get_spool_by_tag(tag_spool)
  implication: SpoolNoEncontradoError raised if get_spool_by_tag returns None

- timestamp: 2026-01-29T00:03:00Z
  checked: SheetsRepository.get_spool_by_tag() method (sheets_repository.py line 910-1030)
  found: Lines 935-952 attempt dynamic TAG_SPOOL column lookup with fallback to column G (index 6)
  implication: Method searches for spool in column determined by header mapping

- timestamp: 2026-01-29T00:04:00Z
  checked: SheetsService.build_column_map() normalization logic (sheets_service.py line 76-77)
  found: normalize() removes spaces, underscores, and slashes: name.lower().replace(" ", "").replace("_", "").replace("/", "")
  implication: Column header "TAG_SPOOL" would normalize to "tagspool"

- timestamp: 2026-01-29T00:05:00Z
  checked: get_spool_by_tag() search patterns (sheets_repository.py line 873-880)
  found: Tries ["TAG_SPOOL", "SPLIT", "tag_spool"] with normalize() + fallback to index 6 (column G)
  implication: Should fall back to column G (where TAG_SPOOL IS located) if dynamic lookup fails

- timestamp: 2026-01-29T00:06:00Z
  checked: find_row_by_column_value() method (sheets_repository.py line 214-248)
  found: Uses find_row_by_column_value() to search for tag_spool value in the determined column
  implication: Even with correct column, might not find the row if value doesn't match exactly

- timestamp: 2026-01-29T00:07:00Z
  checked: Git history for sheets_repository.py
  found: Commit b68e3b8 (most recent) ALREADY FIXED this exact issue - "correct column index offset in get_spool_by_tag()"
  implication: Fix exists in main branch but production Railway deployment is running stale code

- timestamp: 2026-01-29T00:08:00Z
  checked: Production vs local behavior
  found: Local (with b68e3b8) works, production (without b68e3b8) fails with "no encontrado"
  implication: Confirmed deployment lag - production needs to be updated

## Resolution

root_cause: Code fix b68e3b8 corrected double-indexing bug in get_col_value() (changed `column_map[normalized] - 1` to `column_map[normalized]`), but production Railway deployment had NOT deployed the latest code from main branch
fix: Triggered Railway redeploy with empty commit 697e4f1 to force fresh deployment with fix b68e3b8
verification: Railway deployment in progress - will test endpoint after deployment completes (2-5 min)
files_changed:
  - backend/repositories/sheets_repository.py (already fixed in b68e3b8)
  - .planning/debug/spool-not-found-in-operaciones.md (debug log)
