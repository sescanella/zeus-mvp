---
phase: 07-data-model-foundation
plan: 03
subsystem: data-access
tags: [pydantic, repository-pattern, dynamic-column-mapping, unit-testing]

# Dependency graph
requires:
  - phase: 07-01
    provides: Operaciones schema extension with union metric columns
  - phase: 07-02
    provides: Uniones sheet validation and Metadata extension scripts
provides:
  - Union Pydantic model with 18 fields and optimistic locking
  - UnionRepository with dynamic column mapping for Uniones sheet access
  - Comprehensive unit test suite (15 tests, 100% passing)
affects: [07-04-startup-validation, union-tracking-workflows, metrics-aggregation]

# Tech tracking
tech-stack:
  added: []
  patterns: [pydantic-validation, repository-pattern, dynamic-column-mapping, unit-testing-with-mocks]

key-files:
  created:
    - backend/models/union.py
    - backend/repositories/union_repository.py
    - tests/unit/test_union_repository.py
  modified: []

key-decisions:
  - "Union model uses TAG_SPOOL as foreign key to Operaciones (maintains v3.0 compatibility with Redis keys and Metadata)"
  - "UnionRepository uses ColumnMapCache exclusively for all column access (NO hardcoded indices)"
  - "Worker format validation enforced via Pydantic field_validator (INICIALES(ID) pattern)"
  - "Datetime parsing handles both full (DD-MM-YYYY HH:MM:SS) and date-only (DD-MM-YYYY) formats"
  - "Union model frozen/immutable (all changes create new versions with new UUID)"

patterns-established:
  - "Union model follows same audit column pattern as v3.0 (version UUID4, creado_por, fecha_creacion)"
  - "Repository pattern with dependency injection of SheetsRepository"
  - "Comprehensive unit tests with mock fixtures for all repository methods"
  - "Dynamic column mapping shields from Google Sheets schema changes"

# Metrics
duration: 4min
completed: 2026-01-30
---

# Phase 07-03: Union Model & Repository Summary

**Union Pydantic model (18 fields) and UnionRepository with dynamic column mapping for v4.0 union-level tracking**

## Performance

- **Duration:** 4 minutes (215 seconds)
- **Started:** 2026-01-30T21:35:03Z
- **Completed:** 2026-01-30T21:38:38Z
- **Tasks:** 3
- **Files created:** 3
- **Lines of code:** 990 (188 model + 361 repository + 441 tests)
- **Test coverage:** 15 tests, 100% passing

## What Was Built

### 1. Union Pydantic Model (188 lines)
**File:** `backend/models/union.py`

Comprehensive Pydantic v2 model for union-level tracking:

**Identity fields (5):**
- `id`: Composite PK in format `{TAG_SPOOL}+{N_UNION}` (e.g., "OT-123+5")
- `tag_spool`: Foreign key to Operaciones.TAG_SPOOL (maintains v3.0 compatibility)
- `n_union`: Union number within spool (1-20)
- `dn_union`: Diameter in inches (primary business metric for pulgadas-diámetro)
- `tipo_union`: Union type classification

**ARM operation fields (3):**
- `arm_fecha_inicio`: ARM start timestamp
- `arm_fecha_fin`: ARM end timestamp (NULL = pending)
- `arm_worker`: Worker who completed ARM in format "INICIALES(ID)"

**SOLD operation fields (3):**
- `sol_fecha_inicio`: SOLD start timestamp
- `sol_fecha_fin`: SOLD end timestamp (NULL = pending)
- `sol_worker`: Worker who completed SOLD in format "INICIALES(ID)"

**NDT (Non-Destructive Testing) fields (2):**
- `ndt_fecha`: NDT inspection date
- `ndt_status`: NDT result (APROBADO/RECHAZADO/PENDIENTE)

**Audit columns (5):**
- `version`: UUID4 for optimistic locking
- `creado_por`: Worker who created record
- `fecha_creacion`: Creation timestamp
- `modificado_por`: Worker who last modified
- `fecha_modificacion`: Last modification timestamp

**Validation:**
- Worker format enforced via `@field_validator` (INICIALES(ID) pattern)
- N_UNION range: 1-20 (Pydantic constraint)
- DN_UNION must be positive float
- TAG_SPOOL non-empty string

**Helper properties:**
- `arm_completada`: bool (checks if arm_fecha_fin is not None)
- `sol_completada`: bool (checks if sol_fecha_fin is not None)
- `pulgadas_arm`: float (dn_union if ARM complete, else 0)
- `pulgadas_sold`: float (dn_union if SOLD complete, else 0)

**Model config:**
- `frozen=True`: Immutable (all changes create new versions)
- `str_strip_whitespace=True`: Auto-trim strings

### 2. UnionRepository (361 lines)
**File:** `backend/repositories/union_repository.py`

Repository for Uniones sheet access with dynamic column mapping:

**Core methods:**

**1. `get_by_spool(tag_spool: str) -> list[Union]`**
- Query all unions for a spool using TAG_SPOOL as foreign key
- Uses ColumnMapCache for dynamic column lookup (NO hardcoded indices)
- Returns empty list if no unions found
- Maintains v3.0 compatibility (TAG_SPOOL instead of OT)

**2. `get_disponibles(operacion: Literal["ARM", "SOLD"]) -> dict[str, list[Union]]`**
- ARM: Returns unions where ARM_FECHA_FIN is NULL
- SOLD: Returns unions where ARM_FECHA_FIN is NOT NULL and SOL_FECHA_FIN is NULL
- Groups by TAG_SPOOL for efficient lookup
- Example: `{"OT-123": [union1, union2], "OT-124": [union3]}`

**3. `count_completed(tag_spool: str, operacion: Literal["ARM", "SOLD"]) -> int`**
- Counts unions with FECHA_FIN != NULL for given operation
- Used for progress calculation (e.g., "7/10 ARM completed")

**4. `sum_pulgadas(tag_spool: str, operacion: Literal["ARM", "SOLD"]) -> float`**
- Sums DN_UNION for completed unions
- Returns with 1 decimal precision
- Primary business metric for v4.0 (not spool count)

**5. `_row_to_union(row_data: list, column_map: dict) -> Union`**
- Converts sheet row to Union object using dynamic mapping
- Handles datetime parsing (DD-MM-YYYY HH:MM:SS and DD-MM-YYYY formats)
- Handles empty cells gracefully
- Validates required fields

**Architecture patterns:**
- Dependency injection of SheetsRepository (follows MetadataRepository pattern)
- All column access via ColumnMapCache.get_or_build() (zero hardcoded indices)
- Comprehensive error handling with logging
- Follows existing v3.0 repository patterns

### 3. Unit Test Suite (441 lines)
**File:** `tests/unit/test_union_repository.py`

15 comprehensive tests covering all repository methods:

**Query tests (4):**
1. `test_get_by_spool_returns_unions` - Verifies correct unions returned for TAG_SPOOL
2. `test_get_by_spool_returns_empty_for_unknown` - Empty list for non-existent spool
3. `test_get_disponibles_arm` - Only ARM-available unions returned
4. `test_get_disponibles_sold` - Only SOLD-available unions returned (ARM complete, SOLD pending)

**Aggregation tests (2):**
5. `test_count_completed` - Counts ARM/SOLD completed unions correctly
6. `test_sum_pulgadas` - Sums pulgadas-diámetro with 1 decimal precision

**Architecture validation tests (3):**
7. `test_handles_missing_columns_gracefully` - Optional columns missing don't crash
8. `test_uses_column_map_cache` - Verifies ColumnMapCache usage
9. `test_uses_tag_spool_as_foreign_key` - Confirms TAG_SPOOL (not OT) used for queries

**Error handling tests (4):**
10. `test_row_to_union_validates_required_fields` - Missing required fields handled gracefully
11. `test_datetime_parsing_handles_multiple_formats` - Both full and date-only formats supported
12. `test_empty_sheet_returns_empty_list` - Empty sheet handled correctly
13. `test_get_disponibles_returns_empty_for_empty_sheet` - Empty dict for empty sheet

**Integration tests (2):**
14. `test_union_properties_work_correctly` - Union model properties (arm_completada, pulgadas_arm) work
15. `test_count_and_sum_for_nonexistent_spool` - Returns 0/0.0 for non-existent spools

**Test infrastructure:**
- Mock fixtures with realistic 18-column Uniones sheet data
- `autouse` fixture to clear ColumnMapCache between tests (isolation)
- Multiple test spools (OT-123, OT-124, OT-125) with varied states
- All tests passing (15/15) in 0.28 seconds

## Architecture Decisions

### Decision 1: TAG_SPOOL as Foreign Key (Not OT)
**Context:** v3.0 uses TAG_SPOOL as primary key in Redis, Metadata, and all queries. Changing to OT would break ~50 references.

**Decision:** Union model uses `tag_spool` field (column 2 in Uniones sheet) as foreign key to Operaciones.TAG_SPOOL.

**Why this approach:**
- **Zero breaking changes:** All v3.0 Redis keys (`spool:{TAG_SPOOL}:lock`) continue working
- **Metadata compatibility:** Metadata sheet uses TAG_SPOOL in column 4 (hardcoded but stable)
- **Query compatibility:** All existing queries filter by TAG_SPOOL
- **Incremental migration:** v4.0 can coexist with v3.0 during rollout

**Alternatives considered:**
- **Use OT as foreign key:** Would require migrating Redis keys, Metadata schema, and ~50 queries (high risk)
- **Use both TAG_SPOOL and OT:** Redundant, adds complexity without benefit

### Decision 2: ColumnMapCache Exclusively (No Hardcoded Indices)
**Context:** Google Sheets columns can be added/removed/reordered. Hardcoded indices break when schema changes.

**Decision:** UnionRepository uses ColumnMapCache.get_or_build() for ALL column access. Zero hardcoded numeric indices.

**Implementation:**
```python
def normalize(name: str) -> str:
    return name.lower().replace(" ", "").replace("_", "")

column_map = ColumnMapCache.get_or_build("Uniones", self.sheets_repo)
tag_col_idx = column_map[normalize("TAG_SPOOL")]  # Dynamic lookup
value = row_data[tag_col_idx]
```

**Why this approach:**
- **Resilient to schema changes:** Adding columns doesn't break code
- **Consistent with v3.0:** Follows established ColumnMapCache pattern
- **Self-documenting:** `get_col("ARM_FECHA_FIN")` is clearer than `row[6]`
- **Cache efficiency:** Map built once, reused for all queries

**Alternatives considered:**
- **Hardcoded indices:** Faster to write `row[6]` but brittle, breaks on column additions
- **Mixed approach:** Some dynamic, some hardcoded - inconsistent and error-prone

### Decision 3: Worker Format Validation via Pydantic
**Context:** Worker format "INICIALES(ID)" is critical business rule (e.g., "MR(93)"). Invalid format causes downstream errors.

**Decision:** Enforce format validation at model level using Pydantic `@field_validator`.

**Implementation:**
```python
@field_validator('arm_worker', 'sol_worker', 'creado_por', 'modificado_por')
@classmethod
def validate_worker_format(cls, v: Optional[str]) -> Optional[str]:
    if v is None:
        return v
    if not v or '(' not in v or ')' not in v:
        raise ValueError(f"Worker format must be 'INICIALES(ID)', got: {v}")
    return v
```

**Why this approach:**
- **Fail-fast:** Invalid data caught at model instantiation, not during business logic
- **Type safety:** Pydantic ensures validation runs before Union object created
- **Consistent validation:** Same rule enforced for all worker fields
- **Clear errors:** ValueError message guides developers/users to correct format

**Alternatives considered:**
- **Validation in repository:** Would allow invalid Union objects to exist in memory
- **Validation in service layer:** Too late - invalid data already in domain model
- **No validation:** Silent failures in downstream systems (Metadata, reports)

### Decision 4: Frozen/Immutable Union Model
**Context:** Union objects represent snapshots of Google Sheets state. Mutations should create new versions, not modify existing.

**Decision:** Union model configured with `frozen=True` (Pydantic ConfigDict).

**Why this approach:**
- **Immutability:** Prevents accidental modifications (e.g., `union.dn_union = 5.0` raises FrozenInstanceError)
- **Thread safety:** Immutable objects safe to share across async operations
- **Event sourcing compatibility:** Aligns with append-only Metadata pattern
- **Cache safety:** Cached Union objects can't be modified by callers

**Alternatives considered:**
- **Mutable model:** Easier to modify but risks accidental mutations and race conditions
- **Defensive copying:** Would require `.copy()` everywhere to prevent mutations

## Technical Implementation

### Pattern 1: Dynamic Column Access
All repository methods follow this pattern:

```python
def normalize(name: str) -> str:
    return name.lower().replace(" ", "").replace("_", "")

# Build column map (cached)
column_map = ColumnMapCache.get_or_build("Uniones", self.sheets_repo)

# Dynamic lookup (not row[6])
tag_col_idx = column_map[normalize("TAG_SPOOL")]
value = row_data[tag_col_idx]
```

**Benefits:**
- Resilient to column additions/reordering
- Self-documenting code
- Follows established v3.0 pattern

### Pattern 2: Datetime Parsing with Fallback
Handles both Sheets formats:

```python
def parse_datetime(value: Optional[str]) -> Optional[datetime]:
    if not value:
        return None
    try:
        # Full format: "30-01-2026 14:30:00"
        return datetime.strptime(value.strip(), "%d-%m-%Y %H:%M:%S")
    except ValueError:
        try:
            # Date only: "30-01-2026"
            return datetime.strptime(value.strip(), "%d-%m-%Y")
        except ValueError:
            logger.warning(f"Failed to parse datetime: {value}")
            return None
```

**Handles:**
- Full datetime from Metadata events
- Date-only from manual Sheets entry
- Invalid formats gracefully (log warning, return None)

### Pattern 3: Dependency Injection
Repository uses constructor injection:

```python
class UnionRepository:
    def __init__(self, sheets_repo: SheetsRepository):
        self.sheets_repo = sheets_repo
        self._sheet_name = "Uniones"
```

**Benefits:**
- Easy to mock for unit tests
- Follows MetadataRepository pattern
- No tight coupling to Google Sheets implementation

## Integration Points

### With 07-01 (Operaciones Extension)
- Union metrics (Pulgadas_ARM, Pulgadas_SOLD) will be calculated using `sum_pulgadas()`
- Uniones_ARM_Completadas will be calculated using `count_completed()`
- Both rely on TAG_SPOOL foreign key relationship

### With 07-02 (Validation Scripts)
- UnionRepository expects 18-column Uniones sheet structure
- Validation script ensures columns exist before repository used
- Missing columns handled gracefully (optional fields return None)

### With Future Plans (07-04+)
- Startup validation will verify UnionRepository can read Uniones sheet
- Union-level services will use `get_disponibles()` for workflow logic
- Metadata will log union-level events using `n_union` field

## Testing Results

### All Tests Passing (15/15)
```
tests/unit/test_union_repository.py::TestUnionRepository::test_get_by_spool_returns_unions PASSED
tests/unit/test_union_repository.py::TestUnionRepository::test_get_by_spool_returns_empty_for_unknown PASSED
tests/unit/test_union_repository.py::TestUnionRepository::test_get_disponibles_arm PASSED
tests/unit/test_union_repository.py::TestUnionRepository::test_get_disponibles_sold PASSED
tests/unit/test_union_repository.py::TestUnionRepository::test_count_completed PASSED
tests/unit/test_union_repository.py::TestUnionRepository::test_sum_pulgadas PASSED
tests/unit/test_union_repository.py::TestUnionRepository::test_handles_missing_columns_gracefully PASSED
tests/unit/test_union_repository.py::TestUnionRepository::test_uses_column_map_cache PASSED
tests/unit/test_union_repository.py::TestUnionRepository::test_uses_tag_spool_as_foreign_key PASSED
tests/unit/test_union_repository.py::TestUnionRepository::test_row_to_union_validates_required_fields PASSED
tests/unit/test_union_repository.py::TestUnionRepository::test_datetime_parsing_handles_multiple_formats PASSED
tests/unit/test_union_repository.py::TestUnionRepository::test_empty_sheet_returns_empty_list PASSED
tests/unit/test_union_repository.py::TestUnionRepository::test_get_disponibles_returns_empty_for_empty_sheet PASSED
tests/unit/test_union_repository.py::TestUnionRepository::test_union_properties_work_correctly PASSED
tests/unit/test_union_repository.py::TestUnionRepository::test_count_and_sum_for_nonexistent_spool PASSED

========================= 15 passed in 0.28s =========================
```

**Coverage:**
- All repository methods tested
- Edge cases covered (empty sheets, missing columns, invalid data)
- Architecture patterns validated (ColumnMapCache usage, TAG_SPOOL as FK)
- Union model properties tested

## Deviations from Plan

None - plan executed exactly as written.

All three tasks completed successfully:
1. Union Pydantic model created with 18 fields and validation
2. UnionRepository created with all 5 required methods
3. Comprehensive unit tests created (15 tests, all passing)

Pattern consistency maintained with existing v3.0 codebase (ColumnMapCache, repository pattern, Pydantic validation).

## Task Commits

Each task was committed atomically:

1. **Task 1: Create Union Pydantic model** - `4ec53c3` (feat)
   - 188 lines
   - 18 fields with validation
   - Helper properties and frozen config

2. **Task 2: Create UnionRepository** - `c7483f9` (feat)
   - 361 lines
   - 5 core methods with dynamic column mapping
   - Dependency injection pattern

3. **Task 3: Create comprehensive unit tests** - `2e036c7` (test)
   - 441 lines
   - 15 tests covering all methods
   - 100% passing

## Next Phase Readiness

### Blockers
None. All code complete and tested.

### Prerequisites for Phase 07-04 (Startup Validation)
- [x] Union model created and importable
- [x] UnionRepository created and importable
- [x] Unit tests passing
- [ ] Uniones sheet populated by Engineering (external dependency)

### Concerns
1. **Uniones sheet pre-population:** Engineering must complete 18-column structure before 07-04 startup validation can verify data integrity
2. **Integration testing:** Unit tests use mocks - integration tests with real Uniones sheet needed in 07-04

### Recommendations
1. Add UnionRepository to main.py dependency injection container
2. Create integration tests with real (test) Uniones sheet in 07-04
3. Document Union model in API docs for frontend consumption
4. Consider adding Union model to existing MetadataEvent for granular audit trail

## Performance Metrics

**Execution time:** 4 minutes (215 seconds)
- Task 1 (Union model): ~1 min
- Task 2 (UnionRepository): ~2 min
- Task 3 (Unit tests): ~1 min

**Code metrics:**
- Union model: 188 lines
- UnionRepository: 361 lines
- Unit tests: 441 lines
- Total: 990 lines of production + test code

**Test metrics:**
- 15 tests, 100% passing
- Execution time: 0.28 seconds
- Coverage: All repository methods + Union model properties

**Pattern reuse:**
- Follows Spool model pattern (Pydantic + frozen config)
- Follows MetadataRepository pattern (dependency injection)
- Follows existing unit test patterns (mock fixtures with autouse cache clearing)

## Lessons Learned

### What Went Well
1. **Pattern reuse accelerated development:** Copying Spool model and MetadataRepository patterns saved ~10 minutes
2. **Dynamic column mapping paid off:** Zero hardcoded indices makes code resilient to schema changes
3. **Comprehensive tests caught edge cases:** Empty sheet handling, datetime parsing, missing columns all covered
4. **Pydantic validation enforced business rules:** Worker format validation prevents downstream errors

### What Could Improve
1. **datetime parsing could be centralized:** Both UnionRepository and MetadataRepository have similar parsing logic (consider extracting to shared utility)
2. **ColumnMapCache warming could be automatic:** Manual get_or_build() calls could be replaced with startup pre-warming

### Recommendations for Future Plans
1. Extract datetime parsing to `backend/utils/date_formatter.py` (shared by UnionRepository, MetadataRepository)
2. Add ColumnMapCache pre-warming to main.py startup (eager loading instead of lazy)
3. Consider creating `backend/repositories/base_repository.py` with shared `_row_to_model()` pattern
4. Document TAG_SPOOL vs OT decision in architecture docs (avoid future confusion)

---

**Files Modified:**
- backend/models/union.py (created, 188 lines)
- backend/repositories/union_repository.py (created, 361 lines)
- tests/unit/test_union_repository.py (created, 441 lines)

**Commits:**
- 4ec53c3: feat(07-03): create Union Pydantic model with 18 fields
- c7483f9: feat(07-03): create UnionRepository for Uniones sheet access
- 2e036c7: test(07-03): add comprehensive unit tests for UnionRepository

**Next Plan:** 07-04 - Startup Validation (integrate validation scripts, verify Uniones sheet integrity)
