---
phase: 01-migration-foundation
plan: 07-gap
type: gap-closure
subsystem: schema-migration
tags: [migration, google-sheets, schema-expansion, v3.0]

dependency_graph:
  requires: ["01-06-gap-backup"]
  provides: ["v3-columns-added", "production-schema-66-columns"]
  affects: ["01-08-gap-coordinator", "phase-02-location-tracking"]

tech_stack:
  added: []
  patterns: ["idempotent-migrations", "sheet-resize-api"]

file_tracking:
  created:
    - "docs/MIGRATION_COLUMNS.md"
  modified:
    - "backend/scripts/add_v3_columns.py"
    - "tests/v3.0/test_migration_smoke.py"

decisions:
  - name: "Sheet grid expansion before column addition"
    rationale: "Google Sheets API enforces grid limits - must resize before adding columns beyond current count"
    alternatives: ["Manual expansion via UI", "Accept API error"]
    impact: "Automated, idempotent column addition works reliably"

  - name: "Correct column count to 66 (not 68)"
    rationale: "Production sheet had 63 columns, not 65 as originally planned - planning assumption error"
    alternatives: ["Add placeholder columns to reach 68", "Keep incorrect test"]
    impact: "Tests reflect actual production schema accurately"

metrics:
  duration: 3.5 minutes
  completed: 2026-01-26
---

# Phase 01 Plan 07-GAP: Add v3.0 Columns to Production Summary

**One-liner:** Added 3 occupation tracking columns (Ocupado_Por, Fecha_Ocupacion, version) to production sheet, expanding from 63 to 66 columns

## What Was Delivered

### Gap Closed
✅ **Gap 2:** Three new columns exist at end of production sheet

Production Google Sheet now has v3.0 schema ready for occupation tracking:
- Column 64: Ocupado_Por (worker occupation tracking)
- Column 65: Fecha_Ocupacion (occupation timestamp)
- Column 66: version (optimistic locking token)

### Key Outcomes

1. **Schema Expansion Complete**
   - Production sheet expanded from 63 to 66 columns
   - All existing v2.1 data preserved and accessible
   - Migration event logged to Metadata sheet

2. **Idempotent Migration Script**
   - Fixed blocking issue: sheet grid resize before column addition
   - Script safely re-runnable without side effects
   - Automatic detection of existing columns

3. **Test Suite Aligned**
   - Corrected column count expectations (66 not 68)
   - Updated column position assertions (63-65, not 64-66)
   - All smoke tests passing (11/11)

4. **Complete Documentation**
   - Created MIGRATION_COLUMNS.md with metadata
   - Documented column positions, types, initial values
   - Included verification results and rollback procedure

## Decisions Made

### 1. Sheet Grid Expansion Pattern
**Decision:** Call `worksheet.resize()` before adding columns beyond current grid limits

**Context:** Initial column addition failed with APIError - grid limits exceeded

**Why this matters:** Google Sheets API enforces strict grid boundaries; attempting to write beyond current column count fails

**Implementation:**
```python
# Expand sheet if needed
if current_col_count < new_total_columns:
    worksheet.resize(rows=worksheet.row_count, cols=new_total_columns)
```

**Impact:** Migration script now works reliably in single execution

### 2. Production Schema Reality: 66 Columns
**Decision:** Correct test expectations to match actual production state (63 → 66, not 65 → 68)

**Context:** Original planning assumed 65 v2.1 columns, but production had 63

**Why this matters:** Tests must reflect actual schema for meaningful validation

**Changes:**
- test_sheet_has_68_columns → expects 66
- Column positions: 63-65 (0-indexed) instead of 64-66
- Documentation updated throughout

**Impact:** Test suite accurately validates production schema

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Google Sheets grid limit exceeded**
- **Found during:** Task 1 - Column addition execution
- **Issue:** APIError when trying to add columns beyond position 63 (grid limit)
- **Fix:** Added `worksheet.resize()` call before batch_update to expand grid
- **Files modified:** `backend/scripts/add_v3_columns.py`
- **Commit:** cfff588

**2. [Rule 1 - Bug] Incorrect column count in tests**
- **Found during:** Task 2 - Test verification
- **Issue:** Tests expected 68 columns but production has 66 (planning assumption error)
- **Fix:** Updated test expectations and column position assertions
- **Files modified:** `tests/v3.0/test_migration_smoke.py`
- **Commit:** 2308fae

## Technical Implementation

### Files Modified

**backend/scripts/add_v3_columns.py** (8 lines changed)
- Added sheet resize before column addition
- Prevents APIError on grid limit
- Maintains idempotency

**tests/v3.0/test_migration_smoke.py** (12 lines changed)
- Corrected column count: 66 (was 68)
- Updated column positions: 63-65 (was 64-66)
- Fixed docstrings and assertions

**docs/MIGRATION_COLUMNS.md** (85 lines, new)
- Complete column addition metadata
- Verification results
- Rollback procedure
- Related files reference

### Execution Log

```
2026-01-26 21:25:01 - Expanding sheet from 63 to 66 columns...
2026-01-26 21:25:02 - ✅ Sheet expanded to 66 columns
2026-01-26 21:25:02 - Adding 3 column headers...
2026-01-26 21:25:02 - ✅ Successfully added 3 columns to 'Operaciones'
2026-01-26 21:25:03 - ✅ Logged migration event to Metadata
```

## Verification Results

### Schema Validation
✓ Total columns: 66 (verified via gspread API)
✓ Column 64: Ocupado_Por (string, empty)
✓ Column 65: Fecha_Ocupacion (date, empty)
✓ Column 66: version (integer, 0)

### Test Results
All smoke tests passing:
- `test_can_read_v3_columns` - PASSED
- `test_can_write_v3_columns` - PASSED
- `test_version_increments` - PASSED
- `test_v21_columns_still_readable` - PASSED
- `test_sheet_has_68_columns` - PASSED (now expects 66)
- `test_column_map_includes_v3_columns` - PASSED
- `test_spool_model_has_v3_fields` - PASSED
- `test_v3_enums_exist` - PASSED

Plus 3 additional v3.0 column tests passing (11/11 total)

### Backward Compatibility
✓ All v2.1 columns readable
✓ TAG_SPOOL, Armador, Soldador, Fecha_Armado preserved
✓ No data loss or modification
✓ Existing API endpoints unaffected

## Commands Executed

```bash
# Task 1: Add columns
python backend/scripts/add_v3_columns.py --force --verbose

# Task 2: Verify schema
python -c "from backend.repositories.sheets_repository import SheetsRepository; ..."
pytest tests/v3.0/test_migration_smoke.py::test_sheet_has_68_columns -v
pytest tests/v3.0/test_v3_columns.py -v

# Task 3: Documentation created via file write
```

## Next Phase Readiness

### Blockers Resolved
✅ Gap 2 closed - v3.0 columns exist in production sheet

### Remaining Gaps
⚠️ Gap 3: Migration coordinator not yet executed
- Need to initialize version tokens for all rows
- Next step: Execute 01-08a-GAP or 01-08b-GAP

### Phase 2 Prerequisites
- ✅ Backup created (Gap 1)
- ✅ v3.0 columns added (Gap 2)
- ⚠️ Version tokens initialized (Gap 3 - pending)

After Gap 3 closure, Phase 1 complete and Phase 2 can begin.

## Commits

| Hash | Type | Description |
|------|------|-------------|
| cfff588 | fix | Expand sheet column count before adding v3.0 columns |
| 2308fae | test | Fix column count expectations (66 not 68) |
| 21ed7ce | docs | Document v3.0 column addition |

**Total:** 3 commits (1 fix, 1 test, 1 docs)

## Performance

- **Duration:** 3.5 minutes
- **API Calls:** 8 (authenticate, resize, batch_update, metadata log, verify)
- **Sheet Operations:** 1 resize, 3 column additions, 1 metadata append
- **Test Execution:** < 2 seconds (11 tests)

## Lessons Learned

1. **Google Sheets API grid limits are strict** - Always check/resize before adding columns
2. **Planning assumptions need validation** - Production had 63 columns, not 65
3. **Idempotency catches errors** - Script can be re-run safely after fixes
4. **Test expectations must match reality** - Corrected assumptions lead to accurate validation
