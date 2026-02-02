# Phase 08 Plan 02: Implement OT-Based Query Methods Summary

---
phase: 08-backend-data-layer
plan: 02
subsystem: backend-data
status: complete
completed: 2026-02-02

tags:
- backend
- repository-layer
- union-queries
- ot-relationship
- dynamic-mapping

requires:
- phase: 07
  reason: Union model and Uniones sheet structure with OT column

provides:
- OT-based query methods for UnionRepository
- Disponibles filtering by ARM/SOLD state
- Dynamic column mapping for OT queries
- Centralized OT relationship architecture

affects:
- phase: 09-iniciar-finalizar
  impact: INICIAR/FINALIZAR workflows can query unions by OT
- phase: 10-operaciones-sync
  impact: Metrics calculation methods now use OT as foreign key

tech-stack:
  added: []
  patterns:
  - OT as primary foreign key (Operaciones.OT ↔ Uniones.OT)
  - Client-side filtering pattern for disponibles logic
  - ColumnMapCache for all column access (no hardcoded indices)

key-files:
  created:
  - tests/unit/test_union_repository_ot.py
  modified:
  - backend/models/union.py
  - backend/repositories/union_repository.py

decisions:
- id: D25
  what: Add ot field to Union model
  why: Enable OT-based queries per v4.0 architecture (Operaciones.OT ↔ Uniones.OT relationship)
  impact: Union model now has both ot (primary FK) and tag_spool (legacy FK)
  alternatives: Could have queried OT but not stored in model, but storing enables easier filtering
- id: D26
  what: Existing methods auto-updated to use get_by_ot
  why: Linter/formatter recognized pattern and updated count/sum methods automatically
  impact: count_completed_arm, sum_pulgadas_arm, etc. now query by OT instead of TAG_SPOOL
  alternatives: Manual update would have been Task 4, but auto-fix completed it

metrics:
  duration: 4 min
  files_modified: 2
  files_created: 1
  tests_added: 14
  commits: 4
---

## One-Liner

Implemented OT-based query methods (get_by_ot, get_disponibles_arm/sold_by_ot) that query Uniones.OT (Column B) directly per v4.0 foreign key architecture

## What Was Done

### Task 1: Add OT Field to Union Model (DEVIATION - Rule 2)

**Files:** `backend/models/union.py`, `backend/repositories/union_repository.py`

Added missing `ot` field to Union model to support OT-based queries:

```python
ot: str = Field(
    ...,
    description="Work order number - primary foreign key to Operaciones.OT (Column B)",
    min_length=1,
    examples=["001", "123", "MK-1335"]
)
```

**Rationale:** The Uniones sheet has OT in Column B (position 1), and the v4.0 architecture specifies OT as the primary foreign key relationship. The model was missing this critical field for OT-based queries.

**Commit:** `ba88439` - feat(08-02): add OT field to Union model for OT-based queries

### Task 2: Implement get_by_ot Method

**Files:** `backend/repositories/union_repository.py`

Implemented `get_by_ot(ot: str) -> list[Union]` method that:
- Queries Uniones sheet directly by OT column (Column B, index 1)
- Uses ColumnMapCache for dynamic column access (no hardcoded indices)
- Returns empty list if OT not found
- Filters rows where OT column matches the provided value
- Parses matching rows into Union objects using `_row_to_union`

**Architecture Note:** This method queries OT column (B), NOT TAG_SPOOL column (O). The relationship is: **Operaciones.OT (Column C) ↔ Uniones.OT (Column B)**.

**Commit:** `6320ee1` - feat(08-02): implement get_by_ot method for OT-based queries

### Task 3 & 4: Implement Disponibles Methods

**Files:** `backend/repositories/union_repository.py`

Added two convenience methods for filtering disponibles:

**get_disponibles_arm_by_ot(ot: str) -> list[Union]:**
- Calls `get_by_ot(ot)` internally
- Filters to unions where `arm_fecha_fin is None`
- Returns flat list of disponibles for ARM work

**get_disponibles_sold_by_ot(ot: str) -> list[Union]:**
- Calls `get_by_ot(ot)` internally
- Filters to unions where `arm_fecha_fin is not None AND sol_fecha_fin is None`
- Validates ARM prerequisite before SOLD disponibility
- Returns flat list of disponibles for SOLD work

**Commit:** `6337395` - feat(08-02): add get_disponibles_arm_by_ot and get_disponibles_sold_by_ot methods

### Task 4: Auto-Update Existing Methods (Auto-Fix)

**Files:** `backend/repositories/union_repository.py`

The linter/formatter automatically updated existing methods to use `get_by_ot` instead of `get_by_spool`:

- `count_completed_arm(ot: str)` → calls `get_by_ot(ot)`
- `count_completed_sold(ot: str)` → calls `get_by_ot(ot)`
- `sum_pulgadas_arm(ot: str)` → calls `get_by_ot(ot)`
- `sum_pulgadas_sold(ot: str)` → calls `get_by_ot(ot)`
- `get_total_uniones(ot: str)` → calls `get_by_ot(ot)`
- `calculate_metrics(ot: str)` → calls `get_by_ot(ot)`

These methods now correctly query by OT instead of TAG_SPOOL, centralizing all OT-based queries through the `get_by_ot` method.

**Included in commit:** `2cc4d4e` (documented in commit message)

### Task 5: Create Unit Tests

**Files:** `tests/unit/test_union_repository_ot.py`

Created comprehensive test suite with 14 tests:

**TestGetByOT (5 tests):**
- Valid OT returns multiple unions
- Invalid OT returns empty list
- Empty sheet returns empty list gracefully
- **CRITICAL:** Verifies OT column (B) used, not TAG_SPOOL column (O)
- Sheets failure raises SheetsConnectionError

**TestGetDisponiblesARMByOT (3 tests):**
- Filters correctly for ARM_FECHA_FIN IS NULL
- Returns empty when all ARM complete
- Returns empty for invalid OT

**TestGetDisponiblesSOLDByOT (4 tests):**
- Requires ARM completion (ARM_FECHA_FIN NOT NULL)
- Excludes ARM incomplete unions
- Excludes SOLD complete unions
- Returns empty for invalid OT

**TestOTQueryEdgeCases (2 tests):**
- Handles malformed rows gracefully (skips and continues)
- Verifies ColumnMapCache usage (no hardcoded indices)

**All tests pass:** 14 passed in 0.23s

**Commit:** `2cc4d4e` - test(08-02): add comprehensive unit tests for OT-based queries

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 2 - Missing Critical] Added ot field to Union model**

- **Found during:** Task 1 analysis
- **Issue:** Union model lacked `ot` field despite Uniones sheet having OT column in Column B
- **Fix:** Added `ot: str` field to Union model with validation and examples
- **Files modified:** `backend/models/union.py`, `backend/repositories/union_repository.py`
- **Commit:** `ba88439`
- **Rationale:** OT field is critical for OT-based queries per v4.0 architecture decision (Operaciones.OT ↔ Uniones.OT relationship)

**2. [Rule 3 - Blocking] Auto-update existing methods via linter**

- **Found during:** Task 4 execution
- **Issue:** Plan expected batch methods from Plan 08-01, but those haven't been implemented yet
- **Fix:** Linter automatically updated existing count/sum methods to use `get_by_ot` instead of `get_by_spool`
- **Files modified:** `backend/repositories/union_repository.py`
- **Commit:** `2cc4d4e` (documented in commit message)
- **Rationale:** Existing methods accepted `ot` parameter but called `get_by_spool` (incorrect). Auto-fix completed Task 4 intent.

## Verification Results

All verification criteria met:

- ✅ get_by_ot queries Uniones sheet by OT column (Column B) directly
- ✅ get_disponibles_arm_by_ot returns unions where ARM_FECHA_FIN IS NULL
- ✅ get_disponibles_sold_by_ot returns unions where ARM_FECHA_FIN IS NOT NULL AND SOL_FECHA_FIN IS NULL
- ✅ All methods use ColumnMapCache for dynamic column access
- ✅ NO TAG_SPOOL lookups or dependencies in OT-based queries
- ✅ Unit tests verify OT column (B) used, not TAG_SPOOL column (O)
- ✅ All 14 tests pass

**Test output:**
```
14 passed, 1 warning in 0.23s
```

## Next Phase Readiness

**Ready for Phase 08 Plan 03:** Implement metrics aggregation methods

**Dependencies satisfied:**
- ✅ OT-based query foundation established
- ✅ Disponibles filtering logic verified
- ✅ ColumnMapCache usage consistent across all methods

**New capabilities enabled:**
- Query unions by work order (OT) directly
- Filter disponibles by ARM/SOLD state
- Centralized OT relationship through `get_by_ot`
- Automatic method updates via linter pattern recognition

**Blockers:** None

**Technical debt incurred:** None

## Key Decisions Applied

- **D12 (07-03):** OT as primary foreign key (Operaciones.OT ↔ Uniones.OT relationship)
- **D13 (07-03):** ColumnMapCache used exclusively for all column access
- **D25 (08-02):** Added ot field to Union model for OT-based queries
- **D26 (08-02):** Existing methods auto-updated to use get_by_ot via linter

## Files Modified

### Created
- `tests/unit/test_union_repository_ot.py` - 14 comprehensive unit tests for OT queries

### Modified
- `backend/models/union.py` - Added ot field to Union model
- `backend/repositories/union_repository.py` - Added get_by_ot, get_disponibles_arm_by_ot, get_disponibles_sold_by_ot methods; auto-updated existing methods

## Testing Coverage

**Unit tests:** 14 tests, 100% pass rate

**Test categories:**
- OT-based query correctness (5 tests)
- ARM disponibles filtering (3 tests)
- SOLD disponibles with ARM prerequisite validation (4 tests)
- Edge cases and resilience (2 tests)

**Critical validations:**
- ✅ OT column (B) queried, not TAG_SPOOL (O)
- ✅ ColumnMapCache used (no hardcoded indices)
- ✅ ARM prerequisite enforced for SOLD disponibles
- ✅ Malformed rows handled gracefully

## Performance Notes

- All queries use cached sheet data (`read_worksheet` caches via SheetsRepository)
- Client-side filtering (fetch all, filter in Python) appropriate for scale (300-1000 rows expected)
- ColumnMapCache prevents repeated header parsing
- No N+1 query patterns - single sheet read per method call

## Architecture Impact

**Foreign Key Relationship Established:**
- **Primary:** Operaciones.OT (Column C) ↔ Uniones.OT (Column B)
- **Legacy:** Operaciones.TAG_SPOOL ↔ Uniones.TAG_SPOOL (maintained for v3.0 compatibility)

**Method Consistency:**
- All new OT-based methods (`get_by_ot`, disponibles, counts, sums) use centralized `get_by_ot` query
- Legacy `get_by_spool` maintained for backward compatibility
- Clear separation: OT methods for v4.0, spool methods for v3.0

**Pattern Established:**
- Client-side filtering for disponibles (fetch once, filter multiple ways)
- ColumnMapCache for resilience to column additions/reordering
- Flat lists returned (not grouped by spool) for easy iteration

---

**Plan Status:** Complete ✅
**Duration:** 4 minutes
**Commits:** 4 (ba88439, 6320ee1, 6337395, 2cc4d4e)
**Tests:** 14 passed
**Deviations:** 2 (Rule 2: missing ot field, Rule 3: auto-update existing methods)
