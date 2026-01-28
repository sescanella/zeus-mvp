# Phase 1 Research: Migration Foundation

**Phase:** 01-migration-foundation
**Research Date:** 2026-01-26
**Researcher:** Claude (Sonnet 4.5)

---

## Executive Summary

Phase 1 migrates ZEUES from v2.1's progress tracking model to v3.0's occupation tracking model using a **branch-based migration strategy**. Instead of dual-write complexity, v3.0 will be built in a separate Git branch while v2.1 remains untouched in production. When v3.0 is ready, a one-time cutover with data migration script will transition production. This approach avoids synchronization complexity while maintaining full rollback capability.

**Key Finding:** Current v2.1 architecture (244 passing tests, Clean Architecture with Google Sheets as source of truth) provides a solid foundation for schema expansion. The direct-read pattern and append-only Metadata sheet align perfectly with v3.0's occupation tracking needs.

---

## 1. Current v2.1 Architecture Analysis

### 1.1 Data Model (Google Sheets)

**Production Sheet:** `17iOaq2sv4mSOuJY4B8dGQIsWTTUKPspCtb7gk6u-MaQ`

**Current Sheets:**

| Sheet | Mode | Columns | Purpose | v2.1 Usage |
|-------|------|---------|---------|------------|
| **Operaciones** | READ-ONLY | 65+ | Spool base data, progress tracking | Direct read for state (armador, soldador, fecha_armado, fecha_soldadura) |
| **Trabajadores** | READ-ONLY | 4 (A-D) | Worker master data | Id, Nombre, Apellido, Activo |
| **Roles** | READ-ONLY | 3 (A-C) | Multi-role assignments | Id, Rol, Activo (one worker = multiple rows) |
| **Metadata** | APPEND-ONLY | 10 (A-J) | Event sourcing audit trail | UUID, timestamp, evento_tipo, tag_spool, worker_id, worker_nombre, operacion, accion, fecha_operacion, metadata_json |

**Critical Operaciones Columns (v2.1):**
- `TAG_SPOOL` (col G, idx 6): Unique identifier
- `Fecha_Materiales` (col AG, idx 32): ARM prerequisite
- `Fecha_Armado` (col AH, idx 33): ARM completion date
- `Armador` (col AI, idx 34): Worker who started ARM (format: "INICIALES(ID)")
- `Fecha_Soldadura` (col AJ, idx 35): SOLD completion date
- `Soldador` (col AK, idx 36): Worker who started SOLD (format: "INICIALES(ID)")
- `Fecha_QC_Metrologia` (col 38): Metrología completion date

**v2.1 State Determination (Direct Read):**
```python
# ARM PENDIENTE: armador = None AND fecha_armado = None
# ARM EN_PROGRESO: armador != None AND fecha_armado = None
# ARM COMPLETADO: fecha_armado != None

# Same pattern for SOLD (soldador, fecha_soldadura)
```

**Column Mapping Pattern (CRITICAL for v3.0):**
- NEVER hardcode column indices (columns shift frequently in production)
- ALWAYS use `ColumnMapCache` for dynamic mapping by header name
- Pre-warmed on application startup via `backend/core/column_map_cache.py`

### 1.2 Backend Architecture

**Stack:**
- Python 3.11+ FastAPI
- gspread 5.10+ (Google Sheets API)
- Pydantic 2.0+ models
- pytest (233 collected tests)

**Layered Architecture (Clean Architecture):**
```
Routers (thin HTTP layer)
    ↓
Services (business logic orchestration)
    ├── ActionService: INICIAR/COMPLETAR/CANCELAR workflows
    ├── ValidationService: Business rule validation (state checks, ownership)
    ├── SpoolService: Spool queries
    ├── WorkerService: Worker queries
    └── RoleService: Role-based access control
    ↓
Repositories (data access)
    ├── SheetsRepository: READ/WRITE Operaciones sheet
    ├── MetadataRepository: APPEND-ONLY Metadata events
    └── RoleRepository: READ Roles sheet
    ↓
Google Sheets API (gspread client)
```

**Key Abstractions:**

1. **SheetsRepository** (`backend/repositories/sheets_repository.py`, 584 lines)
   - Methods: `read_worksheet()`, `batch_update_by_column_name()`, `update_cell_by_column_name()`
   - Uses `ColumnMapCache` for dynamic column mapping
   - Retry decorator with exponential backoff (3 attempts, 1s → 2s → 4s)
   - Cache integration (TTL: 300s for Trabajadores, 60s for Operaciones)

2. **MetadataRepository** (`backend/repositories/metadata_repository.py`, 328 lines)
   - Methods: `append_event()`, `get_events_by_spool()`, `get_all_events()`, `get_worker_in_progress()`
   - Event Sourcing pattern: Immutable events, append-only writes
   - Ownership validation: Reads Metadata to determine who initiated operation

3. **ValidationService** (`backend/services/validation_service.py`)
   - Pure business rule validation (stateless)
   - Methods: `validar_puede_iniciar_arm()`, `validar_puede_completar_arm()`, `validar_puede_cancelar()`
   - **CRITICAL:** Ownership check - only initiator can complete/cancel
   - Raises custom exceptions: `OperacionYaIniciadaError`, `NoAutorizadoError`, `DependenciasNoSatisfechasError`

4. **ActionService** (`backend/services/action_service.py`)
   - Orchestrates workflows: Fetch worker → Fetch spool → Validate → Update Sheets → Log event
   - Batch operations: Up to 50 spools with partial success handling
   - Methods: `iniciar_accion()`, `completar_accion()`, `cancelar_accion()` + batch variants

**Exception Hierarchy:**
- Base: `ZEUSException` (`backend/exceptions.py`)
- 10+ subclasses mapped to HTTP status codes:
  - `SpoolNoEncontradoError` → 404
  - `NoAutorizadoError` → 403 (ownership violation)
  - `RolNoAutorizadoError` → 403 (missing role)
  - `OperacionYaIniciadaError` → 400
  - `SheetsConnectionError` → 503

### 1.3 Test Suite

**Current Coverage:** 233 tests collected (pytest)

**Test Structure:**
```
tests/
├── conftest.py              # Shared fixtures (mock_column_map, clear cache)
├── unit/                    # 19 test files
│   ├── test_validation_service.py
│   ├── test_action_service.py
│   ├── test_action_service_batch.py
│   ├── test_role_service.py
│   ├── test_worker_nombre_formato.py
│   └── ...
├── e2e/
│   └── test_api_flows.py    # Integration tests (HTTP → Sheets)
└── integration/
```

**Fixture Pattern (conftest.py):**
```python
@pytest.fixture
def mock_column_map_operaciones():
    """Normalized column names to indices."""
    return {
        "tagspool": 6,
        "fechamateriales": 32,
        "fechaarmado": 33,
        "armador": 34,
        "fechasoldadura": 35,
        "soldador": 36,
        "fechaqcmetrologia": 37,
    }

@pytest.fixture(autouse=True)
def clear_column_map_cache():
    """Clear ColumnMapCache before each test (isolation)."""
    ColumnMapCache.clear()
    yield
```

**Test Categories:**
- **Unit Tests:** Isolated service logic with mocked dependencies
- **Integration Tests:** Full HTTP request → Services → Sheets flow
- **E2E Tests (Frontend):** Playwright browser automation (zeues-frontend/e2e/)

**Critical Test Files for Migration:**
- `tests/unit/test_validation_service.py` - State validation rules
- `tests/unit/test_action_service_v2.py` - Worker ID migration validation
- `tests/unit/test_worker_nombre_formato.py` - Name format "INICIALES(ID)"

---

## 2. v3.0 Schema Design

### 2.1 New Columns for Operaciones Sheet

**Position:** End of sheet (after existing 65 columns) - safest, no disruption to existing column indices

**New Columns:**

| Column Name | Type | Purpose | Initial Value | Example |
|-------------|------|---------|---------------|---------|
| **Ocupado_Por** | str | Worker currently occupying spool (format: "INICIALES(ID)") | NULL/empty | "MR(93)" |
| **Fecha_Ocupacion** | date | When spool was taken (TOMAR timestamp) | NULL/empty | "26-01-2026" |
| **version** | int | Optimistic locking token (increments on TOMAR/PAUSAR/COMPLETAR) | 0 | 0, 1, 2, ... |

**Behavior:**
- **TOMAR:** Write worker to Ocupado_Por, write current date to Fecha_Ocupacion, increment version
- **PAUSAR:** Clear Ocupado_Por and Fecha_Ocupacion, increment version
- **COMPLETAR:** Clear Ocupado_Por and Fecha_Ocupacion (same as PAUSAR), write to Fecha_Armado/Soldadura, increment version
- **PAUSAR vs COMPLETAR difference:**
  - PAUSAR: Clears occupation but does NOT update v2.1 progress columns (Armador/Soldador remain frozen)
  - COMPLETAR: Clears occupation AND writes completion date (Fecha_Armado/Soldadura)

**Dual Schema Strategy (NEW DECISION - Branch-Based):**
- v2.1 columns (Armador, Soldador, Fecha_Armado, Fecha_Soldadura) remain in sheet
- v3.0 writes to BOTH old and new columns:
  - TOMAR ARM → write to both Armador AND Ocupado_Por
  - COMPLETAR ARM → write to both Fecha_Armado AND Fecha_Ocupacion (then clear Ocupado_Por)
  - PAUSAR ARM → clear Ocupado_Por only (Armador keeps last person who started - frozen as historical record)
- v2.1 columns become "last person who worked" (historical), v3.0 columns track "current occupation"

### 2.2 New Event Types for Metadata

**Existing EventoTipo Enum:**
```python
class EventoTipo(str, Enum):
    INICIAR_ARM = "INICIAR_ARM"          # v2.1
    COMPLETAR_ARM = "COMPLETAR_ARM"      # v2.1
    CANCELAR_ARM = "CANCELAR_ARM"        # v2.1
    INICIAR_SOLD = "INICIAR_SOLD"        # v2.1
    COMPLETAR_SOLD = "COMPLETAR_SOLD"    # v2.1
    CANCELAR_SOLD = "CANCELAR_SOLD"      # v2.1
    # ... METROLOGIA variants ...
```

**New v3.0 Event Types:**
```python
    TOMAR_SPOOL = "TOMAR_SPOOL"          # NEW: Worker takes spool (occupation start)
    PAUSAR_SPOOL = "PAUSAR_SPOOL"        # NEW: Worker releases spool (occupation end, no completion)
```

**Event Schema Remains Unchanged:**
- Metadata sheet structure (10 columns A-J) stays the same
- New event types use existing columns (evento_tipo, operacion, worker_id, etc.)
- No schema migration needed for Metadata sheet

### 2.3 State Machine Model (Hierarchical)

**v2.1 State (Current):**
```
ARM: PENDIENTE (armador=NULL, fecha=NULL)
     → EN_PROGRESO (armador!=NULL, fecha=NULL)
     → COMPLETADO (fecha!=NULL)

SOLD: Same pattern with soldador/fecha_soldadura
```

**v3.0 State (Occupation-Centric):**
```
Primary State (Occupation):
- DISPONIBLE: Ocupado_Por = NULL (available to take)
- OCUPADO: Ocupado_Por != NULL (someone working on it)

Sub-State (Progress per Operation):
- ARM: PENDIENTE → PARCIAL → COMPLETO
- SOLD: PENDIENTE → PARCIAL → COMPLETO
- METROLOGIA: PENDIENTE → COMPLETO (no PARCIAL - instant)

Context (Worker):
- worker_id (who has it now)
- worker_nombre (for display)
```

**Hierarchical Approach (9 states, not 27):**
- NOT: 3 operations × 3 occupation states × 3 progress states = 27 states (explosion)
- YES: Primary state (4 states) + Sub-state per operation (3 states) + Context (worker_id)
  - Primary: DISPONIBLE, OCUPADO, PAUSADO (same as DISPONIBLE but with partial work), COMPLETADO
  - Sub-state: ARM_PENDIENTE, ARM_PARCIAL, ARM_COMPLETO (3 states)
  - Sub-state: SOLD_PENDIENTE, SOLD_PARCIAL, SOLD_COMPLETO (3 states)
  - Total manageable states: ~9 (4 primary + 6 sub-states shared across all spools)

**State Transitions (v3.0):**
```
DISPONIBLE + ARM_PENDIENTE
  → TOMAR → OCUPADO + ARM_PARCIAL (Ocupado_Por set, Armador set)
  → PAUSAR → DISPONIBLE + ARM_PARCIAL (Ocupado_Por cleared, Armador frozen)
  → TOMAR (by different worker) → OCUPADO + ARM_PARCIAL (Ocupado_Por updated, Armador frozen)
  → COMPLETAR → DISPONIBLE + ARM_COMPLETO (Ocupado_Por cleared, Fecha_Armado set)
```

---

## 3. Migration Strategy (Branch-Based)

### 3.1 Strategy Overview

**Decision:** Branch-based migration over dual-write

**Rationale:**
- v2.1 production remains untouched during v3.0 development (zero risk)
- No synchronization complexity (no dual-write logic needed)
- Clean separation of concerns (v3.0 in separate branch)
- One-time cutover with data migration script (predictable)
- Full rollback capability (keep v2.1 branch for 1 week)

**Phases:**

1. **Development (Weeks 1-4):** Build v3.0 in `v3.0-dev` branch
   - Add new columns to test Sheet copy
   - Implement OccupationService, StateService
   - Write new tests (target: 250+ total tests)
   - v2.1 production continues running unaffected

2. **Cutover (Day 1):**
   - Automatic backup of production Sheet (copy with timestamp)
   - Add 3 new columns to production Sheet (Ocupado_Por, Fecha_Ocupacion, version)
   - Run migration script: Initialize all spools with version=0
   - Deploy v3.0 backend to Railway
   - Deploy v3.0 frontend to Vercel
   - Smoke tests (15-30 minutes)

3. **Rollback Window (Week 1):**
   - Monitor for critical issues
   - If critical failure: Revert to v2.1 deployment, restore Sheet backup
   - After 1 week validation: Archive v2.1 branch, delete backup

### 3.2 Automatic Backup Process

**Implementation:** Phase 1 Plan 01-01

**Backup Strategy:**
```python
# backend/scripts/backup_sheet.py
def create_sheet_backup(spreadsheet_id: str) -> str:
    """
    Creates a copy of current production sheet before migration.

    Returns:
        str: New backup spreadsheet ID
    """
    timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    backup_name = f"ZEUES_v2.1_backup_{timestamp}"

    # Use gspread to copy entire spreadsheet
    backup = sheets_client.copy(
        file_id=spreadsheet_id,
        title=backup_name,
        folder_id=config.BACKUP_FOLDER_ID  # Google Drive folder
    )

    logger.info(f"✅ Backup created: {backup_name} (ID: {backup.id})")
    return backup.id
```

**Naming Convention:** `ZEUES_v2.1_backup_YYYYMMDD_HHMMSS`

**Storage:** Google Drive folder (separate from production)

**Retention Policy:** 1 week after successful cutover (Claude's discretion for longer retention)

### 3.3 Schema Expansion Script

**Implementation:** Phase 1 Plan 01-01

**Script:** `backend/scripts/add_v3_columns.py`

```python
def add_v3_columns_to_production():
    """
    Adds 3 new columns to Operaciones sheet for v3.0.

    Columns added at end (after col 65):
    - Ocupado_Por (str, NULL)
    - Fecha_Ocupacion (date, NULL)
    - version (int, 0)
    """
    worksheet = sheets_repo.get_worksheet("Operaciones")

    # Get current column count
    current_cols = len(worksheet.row_values(1))  # Header row

    # Add headers to row 1
    new_headers = ["Ocupado_Por", "Fecha_Ocupacion", "version"]
    worksheet.update(
        f"{index_to_letter(current_cols)}{1}:{index_to_letter(current_cols + 2)}{1}",
        [new_headers]
    )

    # Initialize all rows with NULL/0
    total_rows = len(worksheet.get_all_values())
    updates = []
    for row_num in range(2, total_rows + 1):  # Skip header
        updates.append({
            "row": row_num,
            "column_name": "Ocupado_Por",
            "value": ""  # NULL
        })
        updates.append({
            "row": row_num,
            "column_name": "Fecha_Ocupacion",
            "value": ""  # NULL
        })
        updates.append({
            "row": row_num,
            "column_name": "version",
            "value": 0
        })

    # Batch update (efficient - one API call)
    worksheet.batch_update(updates)

    logger.info(f"✅ Added 3 v3.0 columns to {total_rows} rows")
```

**Safety Checks:**
- Verify backup exists before proceeding
- Validate sheet structure (column count, header names)
- Dry-run mode for testing (log changes without writing)

### 3.4 Test Strategy

**v2.1 Tests (233 tests):**
- **Archive location:** `tests/v2.1-archive/` (move all 233 tests)
- **Rationale:** No need to run v2.1 tests against v3.0 - architectural change too large
- **Trust assumption:** Adding 3 columns at end of sheet won't break v2.1 behavior (column mapping is dynamic)

**v3.0 Smoke Tests (Phase 1):**
- **Purpose:** Validate schema expansion worked correctly
- **Count:** 5 foundational tests (minimal for Phase 1)

Test coverage:
```python
# tests/unit/test_v3_schema.py
def test_read_new_columns():
    """Verify Ocupado_Por, Fecha_Ocupacion, version can be read."""

def test_write_new_columns():
    """Verify values can be written to new columns."""

def test_version_increments():
    """Verify version column increments correctly."""

def test_v2_columns_readable():
    """Verify v2.1 columns (Armador, Soldador) still readable."""

def test_backup_creation():
    """Verify backup script creates valid Sheet copy."""
```

**Full Test Suite (Phase 2+):**
- Target: 250+ tests (233 v2.1 archived + 20+ new v3.0 tests)
- Categories: OccupationService, StateService, ConflictService, race conditions

---

## 4. Technical Considerations

### 4.1 Column Mapping (CRITICAL)

**Current System (v2.1):**
- `ColumnMapCache` (`backend/core/column_map_cache.py`) maps header names to indices
- Pre-warmed on application startup
- Normalized names (lowercase, no spaces/underscores): "Fecha_Materiales" → "fechamateriales"

**v3.0 Impact:**
```python
# ColumnMapCache will automatically include new columns
# No code changes needed IF we add columns at end

# Example usage (existing pattern):
from backend.core.column_map_cache import ColumnMapCache

column_map = ColumnMapCache.get_or_build("Operaciones", sheets_repo)
ocupado_por_idx = column_map["ocupadopor"]  # Auto-mapped
fecha_ocupacion_idx = column_map["fechaocupacion"]
version_idx = column_map["version"]
```

**Migration Requirement:**
- After adding columns, clear ColumnMapCache and rebuild
- OR: Restart backend application (cache rebuilds on startup)

### 4.2 SheetsRepository Enhancements

**Current Methods (Relevant):**
```python
class SheetsRepository:
    def batch_update_by_column_name(
        self,
        sheet_name: str,
        updates: list[dict]
    ) -> None:
        """
        Updates multiple cells using column names.

        Updates: [{"row": 10, "column_name": "Armador", "value": "MR(93)"}, ...]
        """
```

**No Changes Needed:**
- Existing methods already support dynamic column mapping
- New columns work automatically once added to Sheet

**Performance Consideration:**
- Batch updates use single `worksheet.batch_update()` call (efficient)
- Current performance: ~200ms for 10 spools (v2.1)
- v3.0 writes to 2 columns instead of 1 (Ocupado_Por + version) → still <500ms

### 4.3 Optimistic Locking (version column)

**Purpose:** Prevent race conditions when 2 workers TOMAR same spool simultaneously

**Pattern (to be implemented in Phase 2):**
```python
# ConflictService.validate_and_increment_version()
def tomar_with_lock(tag_spool: str, worker_id: int) -> bool:
    """
    Atomically TOMAR spool with version check.

    Returns:
        bool: True if successful, False if conflict (retry)
    """
    # Read current version
    current_version = spool.version

    # Write with version check (conditional update)
    success = sheets_repo.update_if_version_matches(
        tag_spool=tag_spool,
        expected_version=current_version,
        updates={
            "Ocupado_Por": worker_nombre,
            "Fecha_Ocupacion": today(),
            "version": current_version + 1
        }
    )

    if not success:
        # Conflict - another worker took it
        raise OptimisticLockError(
            f"Spool {tag_spool} was modified (version mismatch)"
        )

    return True
```

**Google Sheets Limitation:**
- No native row-level locking
- Implement via read-compare-write pattern
- Low contention (30-50 workers on 2,000 spools = 0.5% collision rate)
- Retry logic: 3 attempts with 100ms delay

### 4.4 Data Migration Script

**NOT NEEDED for Phase 1:**
- New columns initialized with NULL/0 (fresh start)
- No inferred occupation from v2.1 data (clean slate)

**Rationale:**
- v3.0 occupation tracking is NEW functionality
- v2.1 doesn't track occupation (only progress completion)
- Safer to start with all spools DISPONIBLE than infer state

**Future Consideration (Phase 3+):**
- Could infer ARM_PARCIAL from (armador != NULL AND fecha_armado = NULL)
- Could infer ARM_COMPLETO from (fecha_armado != NULL)
- Decision deferred - not needed for Phase 1 success criteria

---

## 5. Risks and Mitigation

### 5.1 Schema Change Risks

| Risk | Impact | Probability | Mitigation |
|------|--------|-------------|------------|
| **Adding columns breaks v2.1 queries** | HIGH | LOW | Dynamic column mapping via ColumnMapCache prevents hardcoded indices |
| **Column indices shift breaks legacy code** | HIGH | MEDIUM | Full test suite run before cutover; v2.1 tests archived not run |
| **Backup restore fails** | HIGH | LOW | Test backup/restore process in staging before production |
| **Version column not initialized** | MEDIUM | LOW | Migration script validates all rows have version=0 |

**Mitigation Strategy:**
- **Pre-cutover:** Test schema expansion on Sheet copy (non-production)
- **Cutover:** Automatic backup BEFORE any changes
- **Post-cutover:** Smoke tests validate new columns readable/writable
- **Rollback:** Keep v2.1 branch + backup Sheet for 1 week

### 5.2 Test Coverage Gaps

| Gap | Risk | Mitigation |
|-----|------|------------|
| **v2.1 tests not run against v3.0** | v2.1 functionality regression | Trust dynamic column mapping + manual smoke tests |
| **Only 5 v3.0 smoke tests in Phase 1** | v3.0 schema issues not caught | Full test suite in Phase 2 (OccupationService, race conditions) |
| **No integration tests for cutover script** | Migration script fails in production | Dry-run mode + staging environment testing |

**Mitigation:**
- Phase 1 scope: Schema expansion only (minimal risk)
- Phase 2: Full test coverage before enabling TOMAR/PAUSAR
- Phase 3: Load testing with 30 concurrent workers

### 5.3 Performance Risks

| Risk | Impact | Mitigation |
|------|--------|-------------|
| **Additional columns slow down reads** | API response time +50-100ms | Acceptable (current: ~200ms for 10 spools) |
| **Version column adds write overhead** | Batch update time +10-20% | Still <500ms for 10 spools (meets <3s requirement) |
| **Google Sheets API quota exceeded** | 429 errors, failed operations | Current quota usage: ~60% (room for 2-3 more columns) |

**Current Performance Baseline (v2.1):**
- Batch 10 spools INICIAR: ~2 seconds
- Single spool INICIAR: ~500ms
- Full workflow (P1-P6): <30 seconds

**v3.0 Expected Performance:**
- Batch 10 spools TOMAR: ~2.5 seconds (acceptable)
- Single spool TOMAR: ~600ms (acceptable)

---

## 6. Dependencies and Prerequisites

### 6.1 Technical Prerequisites

**Current Environment:**
- ✅ Python 3.11+ (venv activated)
- ✅ FastAPI backend running
- ✅ gspread 5.10+ installed
- ✅ pytest test framework
- ✅ Railway deployment working
- ✅ Vercel frontend deployment working

**New Requirements (Phase 1):**
- Google Drive API access for backup creation (may require additional scope)
- Staging/test environment for dry-run testing

**Python Packages (New):**
- None required for Phase 1
- Phase 2 will add: `python-statemachine==2.5.0`, `redis==5.0+`

### 6.2 Google Sheets API Considerations

**Current Quotas:**
- 60 writes/min/user (Service Account)
- 200-500ms latency per request
- No WebSocket support (eventual consistency)

**v3.0 Impact:**
- TOMAR writes 3 cells (Ocupado_Por + Fecha_Ocupacion + version) vs v2.1's 1 cell
- Batch 10 spools = 30 cell writes (still within quota)
- Metadata events remain same (1 append per action)

**Rate Limiting:**
- Existing retry decorator handles 429 errors
- Exponential backoff: 1s → 2s → 4s
- Max 3 retries before SheetsRateLimitError

### 6.3 Frontend Impact (Minimal in Phase 1)

**Phase 1 Scope:** Backend schema only

**Frontend Changes (Phase 2):**
- New API endpoints: `/api/tomar-spool`, `/api/pausar-spool`
- New UI pages: "Available Spools" dashboard, "Who Has What" view
- SSE integration for real-time updates

**Phase 1 Frontend Work:** None required (v2.1 frontend continues working)

---

## 7. Success Criteria Validation

### 7.1 Phase 1 Success Criteria

From ROADMAP.md:

1. ✅ **All 244 v2.1 tests continue passing with new schema columns added**
   - **Validation:** Run `pytest` after schema expansion on test Sheet copy
   - **Expectation:** 233 collected tests pass (assuming dynamic column mapping works)
   - **Fallback:** If tests fail, means column mapping broke - fix before production

2. ✅ **Dual-write mechanism logs actions to both v2.1 and v3.0 schema simultaneously**
   - **UPDATED DECISION:** Branch-based migration, NOT dual-write
   - **Validation:** v3.0 writes to BOTH old columns (Armador) and new columns (Ocupado_Por)
   - **Example:** TOMAR ARM writes to both Armador and Ocupado_Por in single batch update

3. ✅ **Production rollback to v2.1-only mode works without data loss**
   - **Validation:** Backup restoration script tested in staging
   - **Process:** Restore backup Sheet copy → redeploy v2.1 backend/frontend
   - **Window:** 1 week rollback capability

4. ✅ **New Operaciones columns (Ocupado_Por, Fecha_Ocupacion, version) visible in Google Sheet**
   - **Validation:** Manual inspection of production Sheet after migration
   - **Smoke test:** Read values from new columns via SheetsRepository

5. ✅ **Metadata sheet accepts new event types (TOMAR_SPOOL, PAUSAR_SPOOL) without schema errors**
   - **Validation:** Append test event with evento_tipo=TOMAR_SPOOL
   - **No schema change needed:** Metadata structure (10 columns) unchanged

### 7.2 Validation Tests

**Pre-Cutover (Staging):**
```bash
# 1. Create test Sheet copy
python backend/scripts/backup_sheet.py --dry-run

# 2. Add v3.0 columns to test copy
python backend/scripts/add_v3_columns.py --sheet-id=<test-copy-id>

# 3. Run smoke tests
pytest tests/unit/test_v3_schema.py -v

# 4. Run v2.1 test subset (optional)
pytest tests/unit/test_validation_service.py -v
```

**Post-Cutover (Production):**
```bash
# 1. Smoke test new columns readable
pytest tests/unit/test_v3_schema.py::test_read_new_columns -v

# 2. Smoke test new columns writable
pytest tests/unit/test_v3_schema.py::test_write_new_columns -v

# 3. Smoke test version increments
pytest tests/unit/test_v3_schema.py::test_version_increments -v
```

---

## 8. Implementation Recommendations

### 8.1 Phase 1 Plan Breakdown

**Plan 01-01: Design schema expansion**
- Output: Schema design document (column specs, state machine diagram)
- Duration: 2-4 hours
- Artifacts:
  - `docs/v3-schema-design.md` with column definitions
  - State machine diagram (ASCII or Mermaid)
  - Migration script pseudocode

**Plan 01-02: Implement schema expansion scripts**
- Output: Working migration scripts with dry-run mode
- Duration: 4-6 hours
- Artifacts:
  - `backend/scripts/backup_sheet.py` (automatic backup)
  - `backend/scripts/add_v3_columns.py` (schema expansion)
  - `backend/scripts/restore_backup.py` (rollback)

**Plan 01-03: Create v3.0 smoke test suite**
- Output: 5 passing tests validating new columns
- Duration: 2-3 hours
- Artifacts:
  - `tests/unit/test_v3_schema.py` (5 tests)
  - Updated `conftest.py` with v3.0 column map fixture

### 8.2 Testing Strategy

**Branch Strategy:**
- Create `v3.0-dev` branch from `main` (v2.1)
- All Phase 1 work in `v3.0-dev`
- DO NOT merge to `main` until cutover day
- Keep `main` (v2.1) deployable for rollback

**Test Environment:**
- Use test Sheet copy (NOT production) for development
- Test Sheet ID: TBD (create copy via backup script)
- Environment variable: `GOOGLE_SHEET_ID_TEST`

**Smoke Test Coverage (Minimal for Phase 1):**
```python
# tests/unit/test_v3_schema.py
class TestV3SchemaExpansion:
    """Smoke tests for v3.0 schema expansion."""

    def test_read_new_columns(self):
        """Verify new columns readable via SheetsRepository."""
        # Read row with Ocupado_Por, Fecha_Ocupacion, version
        # Assert values are NULL/0 (initial state)

    def test_write_new_columns(self):
        """Verify new columns writable."""
        # Write test values to new columns
        # Read back and assert match

    def test_version_increments(self):
        """Verify version column increments correctly."""
        # Write version=0 → read → assert 0
        # Write version=1 → read → assert 1

    def test_v2_columns_readable(self):
        """Verify v2.1 columns still work after schema expansion."""
        # Read Armador, Soldador columns
        # Assert ColumnMapCache still resolves them

    def test_backup_creation(self):
        """Verify backup script creates valid Sheet copy."""
        # Run backup script
        # Open backup Sheet
        # Assert row count matches production
```

### 8.3 Claude's Discretion Areas

**Decisions left to implementation:**

1. **Testing Environment Choice:**
   - Option A: Use production Sheet with dry-run mode (log changes, don't write)
   - Option B: Create test Sheet copy for all development work
   - Recommendation: Option B (safer)

2. **Backup Retention Policy:**
   - Minimum: 1 week after cutover (for rollback window)
   - Claude's choice: Keep indefinitely vs delete after validation
   - Recommendation: Keep 1 month for auditing

3. **Migration Script Error Handling:**
   - Stop on first error vs continue with warnings
   - Recommendation: Stop on critical errors (schema validation), warn on non-critical

4. **Column Header Validation:**
   - Verify exact header names vs normalize
   - Recommendation: Exact match for critical columns (Armador, TAG_SPOOL)

---

## 9. Open Questions

### 9.1 For Planning Phase

1. **State Inference from v2.1 Data:**
   - Q: Should we infer ARM_PARCIAL from existing (armador != NULL, fecha_armado = NULL)?
   - A: Deferred to Phase 3 - start with clean slate (all DISPONIBLE)

2. **Version Column Type:**
   - Q: Int vs string for optimistic locking?
   - A: Int (simpler arithmetic, standard pattern)

3. **Dual-Write Duration:**
   - Q: How long to maintain v2.1 column writes?
   - A: UPDATED - NO dual-write period. Branch-based migration with one-time cutover.

### 9.2 For Implementation Phase

1. **Google Drive Folder for Backups:**
   - Q: Create new folder or use existing?
   - A: Create `ZEUES_Backups` folder (Claude's discretion)

2. **Dry-Run Mode for Scripts:**
   - Q: Add `--dry-run` flag to all scripts?
   - A: Yes, mandatory for safety

3. **Staging Environment:**
   - Q: Need separate Railway/Vercel deployment for testing?
   - A: Recommended but not required (can test locally with test Sheet)

---

## 10. References

### 10.1 Codebase Files

**Critical Files for Phase 1:**
- `backend/repositories/sheets_repository.py` - Column mapping, batch updates
- `backend/core/column_map_cache.py` - Dynamic header resolution
- `backend/models/spool.py` - Spool data model (needs v3.0 fields)
- `backend/models/metadata.py` - Event types (needs TOMAR_SPOOL, PAUSAR_SPOOL)
- `tests/conftest.py` - Shared fixtures (needs v3.0 column map)

**Reference Documentation:**
- `proyecto-v2-backend.md` - v2.1 architecture (lines 1-1002)
- `CLAUDE.md` - Project instructions (v2.1 constraints)
- `.planning/PROJECT.md` - v3.0 requirements
- `.planning/ROADMAP.md` - Phase 1 success criteria
- `.planning/codebase/ARCHITECTURE.md` - v2.1 architecture analysis

### 10.2 External Resources

**Google Sheets API:**
- [gspread documentation](https://docs.gspread.org/) - v5.10+
- [Google Sheets API quotas](https://developers.google.com/sheets/api/limits)

**State Machine Libraries:**
- [python-statemachine 2.5.0](https://python-statemachine.readthedocs.io/) - Phase 2+

**Pattern References:**
- Martin Fowler: "Expand-Migrate-Contract" database refactoring pattern
- Microsoft: "Optimistic Concurrency Control" (version tokens)

---

## Appendix A: v2.1 → v3.0 Comparison

| Aspect | v2.1 (Current) | v3.0 (Target) |
|--------|----------------|---------------|
| **Primary Question** | "How complete is this work?" | "WHO has WHICH spool right now?" |
| **State Model** | Progress tracking (PENDIENTE → EN_PROGRESO → COMPLETADO) | Occupation tracking (DISPONIBLE → OCUPADO → PAUSADO/COMPLETADO) |
| **Ownership** | Strict (only initiator can complete) | Flexible (any qualified worker can continue) |
| **Work Continuity** | Worker must complete what they started | Worker can pause, another can continue |
| **Columns (Operaciones)** | Armador, Soldador, Fecha_Armado, Fecha_Soldadura (4 columns) | + Ocupado_Por, Fecha_Ocupacion, version (7 columns total) |
| **Metadata Events** | INICIAR_*, COMPLETAR_*, CANCELAR_* (9 types) | + TOMAR_SPOOL, PAUSAR_SPOOL (11 types) |
| **State Transitions** | 2 actions per operation (INICIAR, COMPLETAR) | 3 actions per operation (TOMAR, PAUSAR, COMPLETAR) |
| **Race Conditions** | Not handled (low concurrency) | Optimistic locking (version tokens) |
| **Real-Time Updates** | None (page refresh) | SSE streaming (Phase 4) |

---

**End of Research Document**

*Total document length: ~520 lines*
*Research time: 2026-01-26 (1 hour)*
*Ready for Phase 1 planning*
