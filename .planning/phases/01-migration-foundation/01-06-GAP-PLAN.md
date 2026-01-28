---
phase: 01-migration-foundation
plan: 06-gap
type: execute
wave: 1
depends_on: []
files_modified:
  - "backend/scripts/backup_sheet.py"
  - "backend/logs/migration/"
  - "docs/MIGRATION_BACKUP.md"
autonomous: false

must_haves:
  truths:
    - "Production Google Sheet has complete backup copy with timestamp"
    - "Backup sheet accessible via Google Drive API"
    - "Backup contains exact copy of production data (63 columns)"
  artifacts:
    - path: "docs/MIGRATION_BACKUP.md"
      provides: "Backup metadata for rollback"
      min_lines: 10
    - path: "backend/logs/migration/backup_execution.log"
      provides: "Execution log with backup sheet ID"
      contains: "Backup created successfully"
  key_links:
    - from: "backup_sheet.py"
      to: "docs/MIGRATION_BACKUP.md"
      via: "documentation output"
      pattern: "Backup sheet ID"
---

# Gap Closure: Execute Production Backup

**Gap:** Production Google Sheet has no backup copy with timestamp
**Impact:** Cannot rollback if migration fails - blocking Phase 1 completion

## Current State

- `backup_sheet.py` exists (252 lines) and tested in dry-run mode
- Script uses `gspread.copy()` for full sheet duplication
- Includes `--dry-run` and `--verify` flags
- Never executed in production mode (only dry-runs in logs)

## Tasks

<task type="manual">
  <name>Task 1: Create migration execution log directory</name>
  <files>backend/logs/migration/</files>
  <action>
    Create backend/logs/migration/ directory if it doesn't exist.
    Initialize migration log file with timestamp for tracking execution.
  </action>
  <verify>[ -d backend/logs/migration/ ] && echo "Directory exists"</verify>
  <done>Directory created and accessible, ready for log files</done>
</task>

<task type="manual">
  <name>Task 2: Execute backup script in production mode</name>
  <files>backend/scripts/backup_sheet.py, backend/logs/migration/backup_execution.log</files>
  <action>
    Run: python backend/scripts/backup_sheet.py --verbose
    NO --dry-run flag (execute real backup).
    Capture output to logs/migration/backup_execution.log.
    Expected: "Backup created successfully: [BACKUP_SHEET_ID]"
  </action>
  <verify>grep "Backup created successfully" backend/logs/migration/backup_execution.log</verify>
  <done>Backup sheet created, sheet ID captured in log file</done>
</task>

<task type="manual">
  <name>Task 3: Verify backup sheet and document details</name>
  <files>docs/MIGRATION_BACKUP.md</files>
  <action>
    Access Google Drive with service account.
    Confirm backup sheet exists with naming: ZEUES_Operaciones_v2.1_backup_[timestamp].
    Verify backup has 63 columns (v2.1 schema) and row count matches production.
    Create docs/MIGRATION_BACKUP.md with:
    - Original sheet ID: 17iOaq2sv4mSOuJY4B8dGQIsWTTUKPspCtb7gk6u-MaQ
    - Backup sheet ID: [captured from task 2]
    - Backup timestamp: [ISO 8601 format]
    - Row count: [verified count]
    - Column count: 63
    - Rollback window expires: [timestamp + 7 days]
  </action>
  <verify>[ -f docs/MIGRATION_BACKUP.md ] && grep "Backup sheet ID" docs/MIGRATION_BACKUP.md</verify>
  <done>Backup documented, metadata available for rollback reference</done>
</task>

## Verification

**Success criteria:**
- Gap 1 closed: "Production Google Sheet has complete backup copy with timestamp" ✓
- Rollback capability established for 7-day window
- Can proceed to column addition (gap 2) safely