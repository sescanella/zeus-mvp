---
phase: 01-migration-foundation
plan: 07-gap
type: execute
wave: 2
depends_on: ["01-06-GAP-PLAN"]
files_modified:
  - "backend/scripts/add_v3_columns.py"
  - "backend/config.py"
  - "backend/logs/migration/"
  - "docs/MIGRATION_COLUMNS.md"
autonomous: false

must_haves:
  truths:
    - "Three new columns (Ocupado_Por, Fecha_Ocupacion, version) exist at end of sheet"
    - "All existing v2.1 data remains unmodified and accessible"
    - "Production sheet has exactly 68 columns"
  artifacts:
    - path: "docs/MIGRATION_COLUMNS.md"
      provides: "Column addition metadata"
      min_lines: 10
    - path: "backend/logs/migration/column_addition.log"
      provides: "Column addition execution log"
      contains: "Successfully added 3 v3.0 columns"
  key_links:
    - from: "add_v3_columns.py"
      to: "backend/config.py"
      via: "V3_COLUMNS import"
      pattern: "from.*config.*import.*V3_COLUMNS"
---

# Gap Closure: Add v3.0 Columns to Production

**Gap:** Three new columns (Ocupado_Por, Fecha_Ocupacion, version) don't exist in production sheet
**Impact:** Cannot track occupation without new columns - blocking Phase 2

## Current State

- `add_v3_columns.py` exists (322 lines) with idempotent logic
- Reads V3_COLUMNS from config.py (single source of truth)
- Production sheet has 63 columns (needs 68 after addition)
- test_sheet_has_68_columns currently SKIPS

## Tasks

<task type="manual">
  <name>Task 1: Verify backup and add columns</name>
  <files>docs/MIGRATION_BACKUP.md, backend/scripts/add_v3_columns.py, backend/logs/migration/column_addition.log</files>
  <action>
    Read docs/MIGRATION_BACKUP.md for backup sheet ID.
    Confirm backup is less than 1 hour old (if not, ABORT and return to gap 1).
    Run: python backend/scripts/add_v3_columns.py --force
    Use --force flag to ensure columns added even if partial exists.
    Capture output to logs/migration/column_addition.log.
    Expected: "Successfully added 3 v3.0 columns at positions 66-68"
  </action>
  <verify>grep "Successfully added 3 v3.0 columns" backend/logs/migration/column_addition.log</verify>
  <done>v3.0 columns added at positions 66-68</done>
</task>

<task type="manual">
  <name>Task 2: Verify columns and run tests</name>
  <files>tests/v3.0/test_smoke.py</files>
  <action>
    Access production sheet via gspread to verify column count = 68.
    Verify column 66 = "Ocupado_Por", 67 = "Fecha_Ocupacion", 68 = "version".
    Execute: pytest tests/v3.0/test_smoke.py::test_sheet_has_68_columns -v
    Should now PASS (not skip).
    Execute: pytest tests/v3.0/test_smoke.py::test_v3_columns_exist -v
    Both tests must pass before proceeding.
  </action>
  <verify>pytest tests/v3.0/test_smoke.py::test_sheet_has_68_columns -v | grep "PASSED"</verify>
  <done>Column tests passing, schema verified</done>
</task>

<task type="manual">
  <name>Task 3: Document column addition</name>
  <files>docs/MIGRATION_COLUMNS.md</files>
  <action>
    Create docs/MIGRATION_COLUMNS.md with:
    - Addition timestamp
    - Column positions: 66 (Ocupado_Por), 67 (Fecha_Ocupacion), 68 (version)
    - Initial values: all empty/0
    - Total columns after: 68
    - Column headers preserved: TAG_SPOOL, Armador, Soldador, etc.
  </action>
  <verify>[ -f docs/MIGRATION_COLUMNS.md ] && grep "Column positions: 66" docs/MIGRATION_COLUMNS.md</verify>
  <done>Column addition documented</done>
</task>

## Verification

**Success criteria:**
- Gap 2 closed: "Three new columns exist at end of sheet" ✓
- v3.0 schema ready for occupation tracking
- Can proceed to migration coordinator (gap 3)