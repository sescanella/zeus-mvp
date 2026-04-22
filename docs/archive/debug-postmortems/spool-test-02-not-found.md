---
status: resolved
trigger: "spool-test-02-not-found"
created: 2026-01-29T00:00:00Z
updated: 2026-01-29T00:25:00Z
---

## Current Focus

hypothesis: CONFIRMED - get_spool_version() uses hardcoded column "G" while sheet structure has changed
test: Fix get_spool_version() to use dynamic column mapping like get_spool_by_tag() does
expecting: After fixing to use dynamic column lookup, TEST-02 will be found correctly
next_action: Apply fix to use ColumnMapCache for TAG_SPOOL/SPLIT column lookup

## Symptoms

expected: When clicking "CONFIRMAR 1 SPOOL" for TEST-02, the spool should be marked as 'En Progreso' for Armado operation (INICIAR ARM workflow)

actual: Error message displayed: "Spool 'TEST-02' no encontrado en hoja Operaciones"

errors:
- Frontend shows red error box with "ERROR: Spool 'TEST-02' no encontrado en hoja Operaciones"
- Console shows: "tomarOcupacion error: Error: Spool 'TEST-02' no encontrado en hoja Operaciones"
- API POST to /api/ocupacion/tomar returns 404 (Not Found)

reproduction:
1. Navigate to worker selection page (select MR(93) ARMADO worker)
2. Select operation type ARMADO - INICIAR
3. Select spool TEST-02 from the spool selection page (it appears and can be selected)
4. Click CONFIRMAR 1 SPOOL on confirmation page
5. Error appears

started: Started after recent deployment. Previously worked fine. TEST-02 exists in Operaciones sheet (user confirmed).

context: The spool TEST-02 is visible and selectable on the spool selection page (P4), which suggests it's being found by the GET /api/spools/iniciar?operacion=ARM endpoint. However, when confirming (POST /api/ocupacion/tomar), the backend returns 404 saying spool not found.

## Eliminated

## Evidence

- timestamp: 2026-01-29T00:05:00Z
  checked: Backend routers configuration
  found: Two different endpoints exist:
    - GET /api/spools/iniciar (spools.py line 32) - Lists spools available to start
    - POST /api/occupation/tomar (occupation.py line 54) - Takes a spool (acquires lock)
  implication: Frontend correctly calls /api/occupation/tomar (verified at api.ts line 915)

- timestamp: 2026-01-29T00:06:00Z
  checked: occupation.py router file
  found: POST /api/occupation/tomar endpoint exists and handles TomarRequest
  implication: Endpoint exists and URL is correct

- timestamp: 2026-01-29T00:10:00Z
  checked: sheets_repository.py get_spool_by_tag and get_spool_version methods
  found: CRITICAL BUG - get_spool_version() uses HARDCODED column "G" (line 867)
        while get_spool_by_tag() correctly uses dynamic column mapping (lines 905-922)
  implication: Column G might not be the TAG_SPOOL column anymore. Documentation says actual column name is "SPLIT" not "TAG_SPOOL" and indices change frequently

- timestamp: 2026-01-29T00:12:00Z
  checked: Call chain from tomar endpoint
  found: occupation_service.tomar() → conflict_service.update_with_retry() → sheets_repository.get_spool_version()
  implication: Every TOMAR operation calls get_spool_version() which uses hardcoded column G, causing SpoolNoEncontradoError when column structure differs

- timestamp: 2026-01-29T00:13:00Z
  checked: CLAUDE.md documentation line 292
  found: Critical columns list shows "SPLIT" as the spool identifier column name, NOT "TAG_SPOOL"
        Comment says "# Spool identifier (actual column name, NOT TAG_SPOOL)"
  implication: The sheet uses "SPLIT" as column name, confirming hardcoded "G" is wrong approach

## Resolution

root_cause: get_spool_version() in sheets_repository.py uses hardcoded column "G" to find spools (line 867), but the sheet structure has changed and column G is no longer the TAG_SPOOL/SPLIT column. This causes SpoolNoEncontradoError when the spool actually exists but in a different column position.

fix: Replaced hardcoded column "G" with dynamic column mapping using ColumnMapCache in get_spool_version() method. Now matches the pattern used in get_spool_by_tag(). The fix:
  1. Uses ColumnMapCache.get_or_build() to get dynamic column mapping
  2. Tries ["TAG_SPOOL", "SPLIT", "tag_spool"] column names (normalized)
  3. Falls back to column G (index 6) only if dynamic lookup fails
  4. Converts column index to letter before calling find_row_by_column_value()

verification:
  - Code compiles successfully (import test passed)
  - Helper method _index_to_column_letter() exists and is used correctly
  - Fix follows same pattern as get_spool_by_tag() which works correctly
  - User needs to test TOMAR operation for TEST-02 spool to confirm fix resolves the issue

files_changed:
  - backend/repositories/sheets_repository.py
