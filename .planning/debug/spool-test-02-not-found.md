---
status: verifying
trigger: "spool-test-02-not-found"
created: 2026-01-28T10:00:00Z
updated: 2026-01-28T10:45:00Z
---

## Current Focus

hypothesis: ROOT CAUSE CONFIRMED - SheetsRepository.get_spool_by_tag() uses hardcoded column "G" but should use ColumnMapCache to dynamically find the TAG_SPOOL/SPLIT column
test: Fix get_spool_by_tag() to use dynamic column mapping like update_cell_by_column_name() does
expecting: After fix, both GET /api/spools/iniciar and POST /api/occupation/tomar will use dynamic column mapping and find TEST-02
next_action: Implement fix using ColumnMapCache pattern from update_cell_by_column_name()

## Symptoms

expected: After selecting spool TEST-02 from the spool selection page and clicking CONFIRMAR, the action should be processed successfully and redirect to success page

actual: Error modal appears with "Spool 'TEST-02' no encontrado en hoja Operaciones" (Spool 'TEST-02' not found in Operaciones sheet)

errors:
- Frontend error: "Spool 'TEST-02' no encontrado en hoja Operaciones"
- API endpoint: POST https://zeues-backend-mvp-production.up.railway.app/api/occupation/tomar
- Response: 404 (Not Found)
- Error visible in browser console

reproduction:
1. Navigate to worker selection page
2. Select worker MR(93) (ARMADO role)
3. Select operation ARM
4. Select action INICIAR
5. Select spool TEST-02 (appears in the list)
6. Click CONFIRMAR
7. Error appears

started: This used to work before but recently broke. TEST-02 is a real spool that exists in the production Operaciones sheet.

environment: Production sheet (GOOGLE_SHEET_ID: 17iOaq2sv4mSOuJY4B8dGQIsWTTUKPspCtb7gk6u-MaQ)

key_observations:
- TEST-02 IS visible in the spool selection page (meaning GET /api/spools/disponibles is finding it)
- TEST-02 IS NOT found when confirming (meaning POST /api/occupation/tomar cannot find it)
- This suggests inconsistency between the two endpoints' spool lookup logic
- The error happens at confirmation, not at selection

## Eliminated

## Evidence

- timestamp: 2026-01-28T10:15:00Z
  checked: backend/repositories/sheets_repository.py line 900
  found: Hardcoded column_letter="G" for TAG_SPOOL lookup in get_spool_by_tag()
  implication: If column G is not TAG_SPOOL anymore, this method will search the wrong column

- timestamp: 2026-01-28T10:16:00Z
  checked: backend/services/spool_service_v2.py line 68-69
  found: Comment states "SPLIT" is the actual column name in Sheet, NOT TAG_SPOOL
  implication: The column name may have changed from TAG_SPOOL to SPLIT in the production sheet

- timestamp: 2026-01-28T10:17:00Z
  checked: backend/routers/spools.py GET /api/spools/iniciar
  found: Uses SpoolServiceV2 which uses dynamic column mapping via ColumnMapCache
  implication: This endpoint succeeds because it looks up columns by name dynamically

- timestamp: 2026-01-28T10:18:00Z
  checked: backend/routers/occupation.py POST /api/occupation/tomar
  found: Calls StateService.tomar() → OccupationService.tomar() → sheets_repository.get_spool_by_tag()
  implication: This endpoint fails because get_spool_by_tag() uses hardcoded column G

## Resolution

root_cause: SheetsRepository.get_spool_by_tag() uses hardcoded column letter "G" to search for TAG_SPOOL, but column G may not be TAG_SPOOL in the production sheet. The column might be named "SPLIT" or be in a different position. This causes find_row_by_column_value() to search the wrong column, returning None (spool not found).

Meanwhile, SpoolServiceV2 uses ColumnMapCache for dynamic column mapping, which correctly finds spools regardless of column position. This explains why GET /api/spools/iniciar (uses SpoolServiceV2) succeeds but POST /api/occupation/tomar (uses get_spool_by_tag) fails.

fix: Modified get_spool_by_tag() to use ColumnMapCache for dynamic column lookup. The method now:
1. Builds column map from sheet header
2. Tries to find TAG column by multiple possible names: "TAG_SPOOL", "SPLIT", "tag_spool"
3. Uses the dynamically found column index instead of hardcoded "G"
4. Falls back to column G only if all dynamic lookups fail (with warning log)

This makes get_spool_by_tag() consistent with the rest of the v2.1+ codebase that uses dynamic column mapping.

verification:
- Code compiles successfully (import test passed)
- Backend initialization works without errors
- Ready for production verification with TEST-02 spool

Next steps for production verification:
1. Deploy to production/staging
2. Attempt the original failing flow: Select worker → ARM → INICIAR → TEST-02 → CONFIRMAR
3. Expected: Should succeed without "Spool not found" error
4. Monitor logs for column mapping messages to confirm which column name was used

files_changed:
- backend/repositories/sheets_repository.py
