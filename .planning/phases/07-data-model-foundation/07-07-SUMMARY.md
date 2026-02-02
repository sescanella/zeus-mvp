---
phase: 07-data-model-foundation
plan: 07
subsystem: documentation
tags: [engineering-handoff, uniones-sheet, validation-script, gap-closure]

requires:
  - phases: [07-06]
    reason: "Schema migrations executed, identified Uniones sheet gap"

provides:
  - artifact: docs/engineering-handoff.md
    capability: "Engineering requirements for Uniones completion"
  - artifact: backend/scripts/validate_uniones_sheet.py --fix
    capability: "Optional header structure setup for Engineering"

affects:
  - phase: 08
    impact: "Unblocks v4.0 deployment after Engineering populates Uniones data"
  - phase: deployment
    impact: "Startup validation will prevent deployment until Uniones complete"

tech-stack:
  added: []
  patterns: ["Engineering coordination checkpoint", "Optional fix capability", "Dry-run mode"]

key-files:
  created:
    - docs/engineering-handoff.md
  modified:
    - backend/scripts/validate_uniones_sheet.py

decisions:
  - id: D23
    choice: "Document Uniones requirements instead of auto-populating data"
    rationale: "Engineering owns union-level data, system provides structure"
    phase: 07-07
  - id: D24
    choice: "Optional --fix flag to add headers (structure only, not data)"
    rationale: "Let Engineering choose between manual setup or automated structure"
    phase: 07-07

metrics:
  duration: 2
  completed: 2026-02-02
---

# Phase 7 Plan 7: Document Uniones Requirements Summary

**One-liner:** Engineering handoff documentation for Uniones sheet with optional header setup script

**Completed:** 2026-02-02
**Duration:** ~2 minutes

## What Was Built

### 1. Engineering Handoff Documentation
- **File:** `docs/engineering-handoff.md`
- **Purpose:** Clear specification of 9 missing Uniones columns for Engineering team
- **Content:**
  - Current state analysis (13 existing columns, 18 required)
  - Missing column specifications (ID, TAG_SPOOL, NDT fields, audit fields)
  - Data format requirements (dates, worker format, UUID4)
  - Population guidelines (1-to-many relationship, unique constraints)
  - SQL-like schema definition
  - Example data rows

### 2. Enhanced Validation Script
- **File:** `backend/scripts/validate_uniones_sheet.py`
- **New capabilities:**
  - `--fix` flag: Adds missing column headers (structure only)
  - `--dry-run` mode: Shows what would be changed without modifying sheet
  - Batch update for efficient header addition
  - Preserves existing data in current 13 columns
  - Detailed logging of changes

## Technical Details

### Engineering Handoff Structure

```markdown
# Engineering Handoff: Uniones Sheet Completion

## Current State
- Existing: 13 columns (N_UNION through CONSUMIBLE)
- Required: 18 columns (9 missing)
- Status: Structure ready, awaiting data population

## Missing Columns (9 total)
1. ID - Unique identifier (int)
2. TAG_SPOOL - Foreign key (str)
3. NDT_FECHA - Testing date (DD-MM-YYYY)
4. NDT_STATUS - Test result (APROBADO/RECHAZADO/PENDIENTE)
5. version - Optimistic lock (UUID4)
6. Creado_Por - Created by (INICIALES(ID))
7. Fecha_Creacion - Created date (DD-MM-YYYY)
8. Modificado_Por - Modified by (INICIALES(ID))
9. Fecha_Modificacion - Modified date (DD-MM-YYYY)

## Data Requirements
- Each TAG_SPOOL can have multiple unions
- N_UNION unique within TAG_SPOOL
- DN_UNION in inches (float, 1 decimal)
- Worker format: "MR(93)" pattern
```

### Validation Script Enhancement

```python
# New flags
--fix          # Add missing column headers
--dry-run      # Show changes without applying

# Usage examples
python backend/scripts/validate_uniones_sheet.py
# Output: Reports 9 missing columns

python backend/scripts/validate_uniones_sheet.py --fix --dry-run
# Output: Shows what headers would be added

python backend/scripts/validate_uniones_sheet.py --fix
# Output: Adds missing headers to Uniones sheet
```

### Add Headers Implementation

```python
def add_missing_headers(client, sheet_id: str, worksheet: Worksheet,
                        headers: list[str], missing: list[str],
                        dry_run: bool = False):
    """Add missing column headers to Uniones sheet."""
    if dry_run:
        print(f"[DRY RUN] Would add {len(missing)} headers: {missing}")
        return

    # Get current headers
    current = worksheet.row_values(1)

    # Build complete header row
    complete = current + [h for h in headers if h not in current]

    # Batch update for efficiency
    worksheet.batch_update([{
        'range': f'A1:{chr(64 + len(complete))}1',
        'values': [complete]
    }])

    print(f"✅ Added {len(missing)} headers: {missing}")
```

## Commits

| Task | Commit | Type | Description |
|------|--------|------|-------------|
| 1 | 7b01277 | docs | Create engineering handoff for Uniones sheet completion |
| 2 | b59c90e | feat | Enhance validation script with fix and dry-run capabilities |
| 3 | (checkpoint) | verify | Human verification - documentation and script approved |

## Decisions Made

### D23: Document Requirements vs Auto-Populate
**Choice:** Create handoff documentation instead of auto-populating union data

**Options considered:**
- Auto-populate with dummy data → Risk of incorrect business data
- Generate from existing spool data → Insufficient information for unions
- Document requirements for Engineering → **SELECTED**

**Rationale:**
- Engineering owns union-level data (welder assignments, diameters, testing)
- System provides structure (columns, formats, validation)
- Clear separation of responsibilities

### D24: Optional Fix Capability
**Choice:** Add --fix flag for optional header setup (structure only)

**Options considered:**
- Manual header addition by Engineering → More coordination overhead
- Automatic header addition during validation → Too aggressive
- Optional --fix flag with dry-run mode → **SELECTED**

**Rationale:**
- Gives Engineering flexibility (manual or automated structure setup)
- Dry-run mode prevents accidents
- Still requires Engineering to populate actual data
- Reduces back-and-forth for simple structure setup

## Deviations from Plan

None - plan executed exactly as written.

## Testing

### Documentation Review
- ✅ Engineering handoff clearly specifies all 9 missing columns
- ✅ Data format requirements documented with examples
- ✅ SQL-like schema provided for clarity
- ✅ Population guidelines included (1-to-many, constraints)

### Script Enhancement
```bash
# Verify --fix flag available
python backend/scripts/validate_uniones_sheet.py --help | grep fix
# Output: --fix  Add missing column headers

# Verify dry-run mode
python backend/scripts/validate_uniones_sheet.py --fix --dry-run
# Output: [DRY RUN] Would add 9 headers: [ID, TAG_SPOOL, ...]

# Actual validation (reports missing columns)
python backend/scripts/validate_uniones_sheet.py
# Output: ❌ Uniones sheet missing 9 columns
```

## Integration Points

### Upstream Dependencies
- **07-06:** Schema migrations executed, identified Uniones gap
- **07-02:** Union model defined (column requirements established)

### Downstream Impact
- **Phase 08:** Union CRUD operations will need complete Uniones sheet
- **Deployment:** Startup validation blocks deployment until Uniones ready
- **Engineering:** Clear handoff enables parallel data population work

## Next Phase Readiness

**Blockers for Phase 8:**
- ⏳ Uniones sheet must be populated by Engineering (external dependency)
- ⏳ 9 missing columns need data: ID, TAG_SPOOL, NDT fields, audit fields
- ✅ Documentation provided for Engineering coordination
- ✅ Optional --fix available to setup structure

**Timeline:**
- Engineering coordination required before Phase 8 execution
- Startup validation will enforce completion before v4.0 deployment
- Optional: Run --fix to add headers now, Engineering populates data later

**Phase 7 Status:**
- ✅ All 7 plans complete (5 original + 2 gap closure)
- ✅ Production sheets extended to v4.0 schema (Operaciones 72 cols, Metadata 11 cols)
- ✅ Validation integrated into startup (fail-fast deployment protection)
- ⏳ Uniones data population pending (Engineering dependency documented)

## Knowledge Capture

### For Future Claude Sessions

**What this plan established:**
1. Engineering handoff process for external data dependencies
2. Optional fix capability pattern (--fix + --dry-run)
3. Clear documentation format for cross-team coordination

**Key files for union-level work:**
- `docs/engineering-handoff.md` - Complete requirements specification
- `backend/scripts/validate_uniones_sheet.py` - Validation + optional setup
- `.planning/STATE.md` - Blockers section documents Uniones dependency

**Engineering coordination:**
- Share engineering-handoff.md with Engineering team
- Coordinate timeline for data population
- Engineering decides: manual header setup or use --fix flag
- System ready to validate and reject deployment until complete

### Context for Phase 8

Phase 8 (Union CRUD Operations) CANNOT start until:
1. Engineering populates Uniones sheet data
2. Startup validation passes (18 columns present with data)
3. Coordination checkpoint with Engineering complete

Gap closure plan 07-07 documented the requirements clearly - now waiting on external team.
