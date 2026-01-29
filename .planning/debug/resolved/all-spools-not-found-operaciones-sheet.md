---
status: resolved
trigger: "all-spools-not-found-operaciones-sheet"
created: 2026-01-29T00:00:00Z
updated: 2026-01-29T00:25:00Z
---

## Current Focus

hypothesis: CONFIRMED - Double index conversion bug in get_col_value() helpers
test: Apply fix by removing incorrect -1 offset in three locations
expecting: Column lookups will use correct index, spools will be found
next_action: Fix lines 987, 1070, 1175 in sheets_repository.py

## Symptoms

expected: User selects spool TEST-02 to start ARM operation, system finds spool in Operaciones sheet and processes the INICIAR action, success confirmation shown
actual: User selects spool TEST-02, system shows error "Spool 'TEST-02' no encontrado en hoja Operaciones", operation fails
errors: "ERROR: Spool 'TEST-02' no encontrado en hoja Operaciones" from tomarOcupacion error at 984-5c764ced9a171128.js:1:3457
reproduction: Navigate to confirmar page with tipo=iniciar, select worker MR(93) ARMADO, select spool TEST-02, click CONFIRMAR button, error appears immediately
started: Previously worked, now ALL spools failing (systemic issue, not data problem)

## Eliminated

## Evidence

- timestamp: 2026-01-29T00:05:00Z
  checked: Backend error flow from occupation.py → state_service.py → occupation_service.py
  found: Error originates in occupation_service.py line 127: `spool = self.sheets_repository.get_spool_by_tag(tag_spool)` returns None
  implication: get_spool_by_tag() failing to find spool TEST-02 even though it exists in sheet

- timestamp: 2026-01-29T00:06:00Z
  checked: get_spool_by_tag() implementation in sheets_repository.py (lines 910-1030)
  found: |
    Lines 936-953: Dynamic column lookup tries ["TAG_SPOOL", "SPLIT", "tag_spool"]
    Line 946: If lookup fails, falls back to hardcoded index 6 (column G)
    Line 958-962: Uses find_row_by_column_value() with column_letter to find spool
    Line 964: Returns None if row_num is None
  implication: Either column mapping failed OR find_row_by_column_value() is failing to match the tag

- timestamp: 2026-01-29T00:10:00Z
  checked: ColumnMapCache and build_column_map() implementation
  found: |
    column_map_cache.py line 98: Uses SheetsService.build_column_map(header_row)
    sheets_service.py line 85: `column_map[normalized] = idx` (idx is enumerate() result, 0-indexed)
    Confirmed: column_map stores 0-indexed values directly from enumerate()
  implication: column_map values are ALREADY 0-indexed, no conversion needed

- timestamp: 2026-01-29T00:12:00Z
  checked: Usage of column_map in sheets_repository.py get_col_value() helpers
  found: |
    Line 987: `col_index = column_map[normalized] - 1  # Convert 1-indexed to 0-indexed`
    Line 1070: Same incorrect conversion
    Line 1175: Same incorrect conversion
    Comment says "Convert 1-indexed to 0-indexed" but column_map is ALREADY 0-indexed
  implication: ROOT CAUSE CONFIRMED - Double conversion causes wrong column lookup for ALL spools

## Resolution

root_cause: |
  CONFIRMED: Double index conversion in sheets_repository.py

  Lines 987, 1070, 1175 in get_col_value() helper functions incorrectly subtract 1 from column_map indices:
  `col_index = column_map[normalized] - 1  # Convert 1-indexed to 0-indexed`

  However, column_map already stores 0-indexed values (built by SheetsService.build_column_map line 85: `column_map[normalized] = idx`).
  This causes TAG_SPOOL column lookup to use wrong column (offset by -1), resulting in "no encontrado" for ALL spools.

  Example: If TAG_SPOOL is at column index 6 (0-indexed, column G):
  - column_map["tagspool"] = 6
  - Code does: col_index = 6 - 1 = 5 (looks in column F instead of G!)
  - find_row_by_column_value() fails to find spool
  - get_spool_by_tag() returns None
  - SpoolNoEncontradoError raised

fix: |
  Removed incorrect -1 offset in three get_col_value() helper functions:
  - Line 987: Changed `col_index = column_map[normalized] - 1` to `col_index = column_map[normalized]`
  - Line 1070: Same change
  - Line 1175: Same change

  Updated comment from "Convert 1-indexed to 0-indexed" to "Already 0-indexed from build_column_map"

  Root cause: column_map stores 0-indexed values (from enumerate() in build_column_map),
  but code incorrectly subtracted 1, causing TAG_SPOOL lookups to search wrong column.

verification: |
  Test 1 - Single spool lookup:
  ```
  repo = SheetsRepository(compatibility_mode='v2.1')
  spool = repo.get_spool_by_tag('TEST-02')
  Result: ✅ SUCCESS - Found spool TEST-02
  - Fecha Materiales: 2026-01-20
  ```

  Test 2 - Multiple spools:
  ```
  TEST-01: ✅ Found (Materiales: 2026-12-14)
  TEST-02: ✅ Found (Materiales: 2026-01-20)
  ```

  Test 3 - Bulk operations using same get_col_value():
  ```
  get_spools_for_metrologia(): ✅ Found 17 spools
  get_all_spools(): ✅ Found 1180 total spools
  ```

  VERIFIED: Original "no encontrado" error completely resolved for ALL spools.
  All three get_col_value() helper functions now work correctly.

files_changed: ["backend/repositories/sheets_repository.py"]
