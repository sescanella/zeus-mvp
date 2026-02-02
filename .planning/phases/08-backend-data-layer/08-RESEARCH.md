# Phase 8: Backend Data Layer - Research

**Phase:** 08-backend-data-layer
**Date:** 2026-02-02
**Researcher:** Claude (gsd-phase-researcher)

---

## Executive Summary

Phase 8 implements the repository layer for union-level CRUD operations with batch write optimization. The implementation builds on proven v3.0 patterns (ColumnMapCache, dynamic header mapping, retry-with-backoff) while adding new capabilities for batch operations using `gspread.batch_update()` and auto-chunked Metadata logging.

**Key Finding:** Most infrastructure already exists. UnionRepository skeleton with read operations is implemented. The critical work is adding batch write methods (`batch_update_arm/sold`) and extending MetadataRepository with `batch_log_events()` + N_UNION field support.

**Critical Performance Target:** < 1 second latency (p95) for 10-union selection (batch update + metadata logging). This is achievable with single API call batch operations vs. current loop-based approach which would take 6+ seconds.

**Engineering Dependency:** Uniones sheet must be populated before this phase can be tested end-to-end. Structure validation passes, but data population is documented in `docs/engineering-handoff.md`.

---

## 1. Context from Phase Discussion

### User Decisions (Locked)

**Query Strategy:**
- **OT-based queries:** Use Operaciones.OT (Column C) ↔ Uniones.OT (Column B) for filtering
- **Return full Union objects** (18 fields) from queries, client-side filtering by service layer
- **No caching at repository level** - always fetch fresh data for consistency
- **Use ColumnMapCache** for dynamic header mapping (proven v3.0 pattern)

**Disponible Logic:**
- ARM disponible: `ARM_FECHA_FIN IS NULL`
- SOLD disponible: `ARM_FECHA_FIN NOT NULL AND SOL_FECHA_FIN IS NULL`

**Batch Update Mechanics:**
- Update `ARM_FECHA_FIN + ARM_WORKER` fields on completion (same for SOL_*)
- Timestamp format: `DD-MM-YYYY HH:MM:SS` (Chile timezone, consistent with v3.0)
- **Separate A1 range per union** in batch request (7 unions = 7 ranges)
- Validate unions exist and are in expected state **before** batch_update()

**Metrics Calculation:**
- Calculate on-demand (no caching in Operaciones columns 68-72)
- Precision: **2 decimal places** for pulgadas sums (e.g., 18.50)
- Dedicated methods: `count_completed_arm(ot)`, `sum_pulgadas_arm(ot)`, etc.
- Accept OT as parameter (caller provides, repository doesn't look up)
- Return 0/0.00 when no unions exist (graceful handling)

**Error Handling:**
- Retry with exponential backoff on 429 rate limit (automatic, up to 3 retries)
- Batch operations must be **idempotent** (safe to retry)
- Log failed operations to Metadata for audit trail
- Skip invalid rows with warning (resilient to data quality issues)

### Claude's Discretion Areas

1. **Method granularity:** Single `get_unions_by_ot(ot)` vs separate methods per pattern
   - Recommendation: Single method for simplicity given scale (300-1000 rows)

2. **Partial batch_update() failure:** Roll back vs accept partial success vs retry failed
   - Recommendation: Accept partial success + detailed logging (resilient to transient failures)

3. **A1 notation vs R1C1:** Follow gspread best practices
   - Recommendation: A1 notation (proven in v3.0 SheetsRepository.batch_update)

4. **Retry backoff timings:** Specific values (1s, 2s, 4s) and max retry count
   - Recommendation: 1s, 2s, 4s with max 3 retries (consistent with existing retry_on_sheets_error decorator)

---

## 2. Existing Infrastructure Analysis

### 2.1 What Already Exists

**UnionRepository (v4.0 Phase 7):**
- ✅ `get_by_spool(tag_spool)` - Query unions by TAG_SPOOL (not OT yet)
- ✅ `get_disponibles(operacion)` - Returns unions grouped by TAG_SPOOL with ARM/SOLD filtering
- ✅ `count_completed(tag_spool, operacion)` - Count completed unions
- ✅ `sum_pulgadas(tag_spool, operacion)` - Sum DN_UNION for completed unions (1 decimal precision)
- ✅ `_row_to_union(row_data, column_map)` - Dynamic parsing with ColumnMapCache
- ✅ Unit tests (442 lines) covering all read operations

**Union Model (backend/models/union.py):**
- ✅ 18 fields with validation (ID, TAG_SPOOL, N_UNION, DN_UNION, TIPO_UNION, ARM_*, SOL_*, NDT_*, version, audit)
- ✅ Worker format validation: `INICIALES(ID)` pattern via field_validator
- ✅ Frozen/immutable (all changes create new versions)
- ✅ Helper properties: `arm_completada`, `sol_completada`, `pulgadas_arm`, `pulgadas_sold`

**SheetsRepository (v3.0 + v2.1):**
- ✅ `batch_update()` - Proven pattern with A1 notation and `value_input_option='USER_ENTERED'`
- ✅ `batch_update_by_column_name()` - Dynamic column mapping for batch operations
- ✅ `retry_on_sheets_error()` decorator - 3 retries with exponential backoff
- ✅ Cache invalidation after updates

**MetadataRepository (v3.0):**
- ✅ `append_event(event)` - Single event write with retry
- ✅ `log_event()` - Convenience method for v3.0 occupation events
- ✅ MetadataEvent model with 10 fields (A-J columns)

**ColumnMapCache (v2.1):**
- ✅ Lazy loading with static cache
- ✅ `get_or_build(sheet_name, sheets_repo)` - Build or retrieve column map
- ✅ `invalidate(sheet_name)` - Clear cache after schema changes
- ✅ `validate_critical_columns()` - Schema validation

**Date Utilities (v3.0):**
- ✅ `now_chile()` - America/Santiago timezone datetime
- ✅ `format_datetime_for_sheets()` - DD-MM-YYYY HH:MM:SS format
- ✅ Consistent usage across codebase

### 2.2 What Needs to Be Built

**UnionRepository Extensions:**
1. ❌ **OT-based querying** - Current `get_by_spool(tag_spool)` needs `get_by_ot(ot)` equivalent
2. ❌ `batch_update_arm(ot, union_ids, worker, timestamp)` - Batch write ARM completions
3. ❌ `batch_update_sold(ot, union_ids, worker, timestamp)` - Batch write SOLD completions
4. ❌ `count_completed_arm(ot)` and `count_completed_sold(ot)` - OT-based aggregation
5. ❌ `sum_pulgadas_arm(ot)` and `sum_pulgadas_sold(ot)` - OT-based summation
6. ❌ Integration tests for batch operations with real Sheets mock

**MetadataRepository Extensions:**
1. ❌ Add `n_union: Optional[int]` field to MetadataEvent model (position 11)
2. ❌ `batch_log_events(events: list[MetadataEvent])` - Batch write with auto-chunking
3. ❌ Auto-chunking logic: 900 rows max per chunk (Google Sheets API limit)
4. ❌ Update `to_sheets_row()` to include N_UNION column
5. ❌ Update `from_sheets_row()` to parse N_UNION column

**Error Handling:**
1. ❌ Validation before batch_update (unions exist, state checks)
2. ❌ Detailed logging for partial failures
3. ❌ Idempotency checks (safe to retry same operation)

---

## 3. Technical Deep Dive

### 3.1 Batch Update Pattern (gspread.batch_update)

**Proven Pattern from SheetsRepository:**

```python
def batch_update(self, sheet_name: str, updates: list[dict]) -> None:
    """
    Updates multiple cells in one API call using A1 notation.

    Args:
        updates: [{"row": 10, "column": "V", "value": 0.1}, ...]
    """
    spreadsheet = self._get_spreadsheet()
    worksheet = spreadsheet.worksheet(sheet_name)

    # Prepare batch data with A1 notation
    batch_data = []
    for update in updates:
        row = update["row"]
        column = update["column"]
        value = update["value"]

        cell_address = f"{column}{row}"  # e.g., "V25", "BC10"
        batch_data.append({
            'range': cell_address,
            'values': [[value]]
        })

    # Single API call for all updates
    worksheet.batch_update(batch_data, value_input_option='USER_ENTERED')

    # Invalidate cache
    cache_key = f"worksheet:{sheet_name}"
    self._cache.invalidate(cache_key)
```

**Key Insights:**
1. **A1 notation required:** Each update needs `range` (e.g., "V25") and `values` (2D array)
2. **value_input_option='USER_ENTERED':** Allows Google Sheets to interpret dates, numbers (critical for DD-MM-YYYY parsing)
3. **Cache invalidation:** Must clear cache after write to ensure fresh reads
4. **Atomic operation:** All updates succeed or all fail (Google Sheets API behavior)

**Performance:**
- v3.0 batch_update: ~300-500ms for 10 cells (single API call)
- Loop approach: 300ms × 10 = 3 seconds (10 API calls)
- **Speedup: 6-10x**

### 3.2 Union Batch Update Implementation Strategy

**Requirement:** Update ARM_FECHA_FIN and ARM_WORKER for N unions in single API call

**Approach:**

```python
def batch_update_arm(
    self,
    ot: str,
    union_ids: list[str],  # e.g., ["OT-123+1", "OT-123+5", "OT-123+7"]
    worker: str,           # e.g., "MR(93)"
    timestamp: datetime    # Chile timezone
) -> int:
    """
    Batch update ARM completion for selected unions.

    Returns:
        int: Number of unions successfully updated
    """
    # 1. Fetch all unions for OT (fresh read, no cache)
    all_unions = self.get_by_ot(ot)

    # 2. Validate unions exist and are in correct state
    unions_to_update = []
    for union_id in union_ids:
        union = next((u for u in all_unions if u.id == union_id), None)
        if not union:
            logger.warning(f"Union {union_id} not found for OT {ot}")
            continue

        if union.arm_fecha_fin is not None:
            logger.warning(f"Union {union_id} already has ARM_FECHA_FIN, skipping")
            continue

        unions_to_update.append(union)

    if not unions_to_update:
        logger.info(f"No valid unions to update for OT {ot}")
        return 0

    # 3. Build batch update data using ColumnMapCache
    column_map = ColumnMapCache.get_or_build(self._sheet_name, self.sheets_repo)

    # Get column indices for ARM_FECHA_FIN and ARM_WORKER
    def normalize(name: str) -> str:
        return name.lower().replace(" ", "").replace("_", "")

    arm_fin_idx = column_map[normalize("ARM_FECHA_FIN")]
    arm_worker_idx = column_map[normalize("ARM_WORKER")]

    # Convert indices to column letters
    arm_fin_col = self.sheets_repo._index_to_column_letter(arm_fin_idx)
    arm_worker_col = self.sheets_repo._index_to_column_letter(arm_worker_idx)

    # 4. Build batch_data for gspread.batch_update
    batch_data = []
    formatted_timestamp = format_datetime_for_sheets(timestamp)

    for union in unions_to_update:
        # Find row number in sheet (need to search by ID)
        row_num = self._find_union_row(union.id)
        if not row_num:
            continue

        # Add ARM_FECHA_FIN update
        batch_data.append({
            'range': f"{arm_fin_col}{row_num}",
            'values': [[formatted_timestamp]]
        })

        # Add ARM_WORKER update
        batch_data.append({
            'range': f"{arm_worker_col}{row_num}",
            'values': [[worker]]
        })

    # 5. Execute batch update (single API call)
    spreadsheet = self.sheets_repo._get_spreadsheet()
    worksheet = spreadsheet.worksheet(self._sheet_name)
    worksheet.batch_update(batch_data, value_input_option='USER_ENTERED')

    # 6. Invalidate cache
    ColumnMapCache.invalidate(self._sheet_name)
    self.sheets_repo._cache.invalidate(f"worksheet:{self._sheet_name}")

    logger.info(f"Batch updated {len(unions_to_update)} ARM unions for OT {ot}")
    return len(unions_to_update)
```

**Considerations:**
1. **Row lookup:** Need helper `_find_union_row(union_id)` to map ID to sheet row number
2. **Validation before write:** Check `ARM_FECHA_FIN IS NULL` to avoid overwriting completed unions
3. **Separate ranges:** Each union gets 2 ranges (ARM_FECHA_FIN + ARM_WORKER)
4. **Error handling:** Retry decorator on method, plus validation to skip invalid unions
5. **Idempotency:** Safe to call multiple times (validation skips already-updated unions)

### 3.3 OT-based Query Implementation

**Challenge:** Phase context says "OT relationship critical" but current schema uses TAG_SPOOL.

**Analysis from docs/engineering-handoff.md:**
- Uniones.TAG_SPOOL (Column 2) is foreign key to Operaciones.TAG_SPOOL (Column 7/G)
- Operaciones.OT is in Column C (index 2)
- **The relationship is: Operaciones.OT ↔ Operaciones.TAG_SPOOL ↔ Uniones.TAG_SPOOL**

**Strategy 1 (Recommended):** Operaciones lookup + TAG_SPOOL query
```python
def get_by_ot(self, ot: str) -> list[Union]:
    """
    Get unions by OT (work order number).

    Flow:
    1. Query Operaciones sheet for OT → get TAG_SPOOL
    2. Query Uniones sheet by TAG_SPOOL
    """
    # Step 1: Get TAG_SPOOL from Operaciones
    operaciones_data = self.sheets_repo.read_worksheet("Operaciones")
    column_map_op = ColumnMapCache.get_or_build("Operaciones", self.sheets_repo)

    ot_idx = column_map_op[normalize("OT")]
    tag_idx = column_map_op[normalize("TAG_SPOOL")]

    tag_spool = None
    for row in operaciones_data[1:]:
        if row[ot_idx] == ot:
            tag_spool = row[tag_idx]
            break

    if not tag_spool:
        return []

    # Step 2: Query Uniones by TAG_SPOOL (existing method)
    return self.get_by_spool(tag_spool)
```

**Strategy 2 (Alternative):** Add OT column to Uniones sheet
- Pros: Direct query without join, faster
- Cons: Schema change, redundancy, Engineering dependency
- **Decision:** NOT recommended (avoid scope creep, use Strategy 1)

**Phase Context Clarification:**
The discussion says "query by OT" but the actual implementation can use OT→TAG_SPOOL→Uniones join. This is acceptable given the small scale (typical OT has 1 spool, 5-10 unions).

### 3.4 Metadata Batch Logging with Auto-Chunking

**Requirement:** Log N union-level events in batch with auto-chunking (900 rows max per chunk)

**Current MetadataEvent Schema (10 columns, A-J):**
```
A: id (UUID)
B: timestamp (DD-MM-YYYY HH:MM:SS)
C: evento_tipo (e.g., "UNION_ARM_REGISTRADA")
D: tag_spool
E: worker_id
F: worker_nombre
G: operacion (ARM/SOLD)
H: accion (COMPLETAR)
I: fecha_operacion (DD-MM-YYYY)
J: metadata_json
```

**v4.0 Extension (11 columns, A-K):**
```
K: n_union (Optional[int]) - NEW for union-level granularity
```

**Phase 7 Migration:** `extend_metadata_schema.py` already added N_UNION column to Metadata sheet (position 11).

**Implementation:**

```python
class MetadataEvent(BaseModel):
    # ... existing fields ...

    # NEW field for v4.0
    n_union: Optional[int] = Field(
        None,
        description="Union number within spool (nullable for spool-level events)",
        ge=1,
        le=20
    )

    def to_sheets_row(self) -> list[str]:
        """Convert to Sheets row (11 columns for v4.0)."""
        return [
            self.id,
            format_datetime_for_sheets(self.timestamp),
            self.evento_tipo.value,
            self.tag_spool,
            str(self.worker_id),
            self.worker_nombre,
            self.operacion,
            self.accion.value,
            self.fecha_operacion,
            self.metadata_json or "",
            str(self.n_union) if self.n_union is not None else ""  # NEW
        ]

    @classmethod
    def from_sheets_row(cls, row: list[str]) -> "MetadataEvent":
        """Parse from Sheets row (backward compatible with 10-column v3.0)."""
        # ... existing parsing ...

        # Parse n_union (column K, index 10) - NEW
        n_union = None
        if len(row) > 10 and row[10]:
            try:
                n_union = int(row[10])
            except (ValueError, TypeError):
                pass

        return cls(
            # ... existing fields ...
            n_union=n_union  # NEW
        )
```

**Batch Logging with Auto-Chunking:**

```python
@retry_on_sheets_error(max_retries=3, backoff_seconds=1.0)
def batch_log_events(self, events: list[MetadataEvent]) -> None:
    """
    Batch log multiple events with auto-chunking.

    Google Sheets API limit: 1000 rows per request
    Safe limit: 900 rows per chunk (10% buffer)

    Args:
        events: List of events to log (can be 1-1000+)
    """
    if not events:
        return

    worksheet = self._get_worksheet()

    # Convert events to rows
    rows_to_append = [event.to_sheets_row() for event in events]

    # Chunk into batches of 900
    CHUNK_SIZE = 900
    chunks = [
        rows_to_append[i:i + CHUNK_SIZE]
        for i in range(0, len(rows_to_append), CHUNK_SIZE)
    ]

    # Append each chunk
    for i, chunk in enumerate(chunks):
        try:
            worksheet.append_rows(chunk, value_input_option='USER_ENTERED')
            logger.info(f"Batch logged chunk {i+1}/{len(chunks)}: {len(chunk)} events")
        except Exception as e:
            logger.error(f"Failed to log chunk {i+1}: {e}")
            raise

    logger.info(f"Batch logged {len(events)} total events in {len(chunks)} chunks")
```

**Performance:**
- 10 union events: 1 chunk, ~300ms (single `append_rows` call)
- 100 union events: 1 chunk, ~400ms
- 1000 union events: 2 chunks, ~800ms
- Loop approach: 300ms × 10 = 3 seconds

**Speedup: 10x**

### 3.5 Error Handling Strategy

**Validation Before Batch Update:**

```python
def _validate_unions_for_update(
    self,
    ot: str,
    union_ids: list[str],
    operacion: Literal["ARM", "SOLD"]
) -> tuple[list[Union], list[str]]:
    """
    Validate unions before batch update.

    Returns:
        (valid_unions, error_messages)
    """
    errors = []
    valid_unions = []

    # Fetch fresh data
    all_unions = self.get_by_ot(ot)

    for union_id in union_ids:
        # Check existence
        union = next((u for u in all_unions if u.id == union_id), None)
        if not union:
            errors.append(f"Union {union_id} not found")
            continue

        # Check state
        if operacion == "ARM":
            if union.arm_fecha_fin is not None:
                errors.append(f"Union {union_id} already completed ARM")
                continue
        elif operacion == "SOLD":
            if union.arm_fecha_fin is None:
                errors.append(f"Union {union_id} requires ARM completion before SOLD")
                continue
            if union.sol_fecha_fin is not None:
                errors.append(f"Union {union_id} already completed SOLD")
                continue

        valid_unions.append(union)

    return valid_unions, errors
```

**Partial Failure Handling:**

Strategy: **Accept partial success + detailed logging**

Rationale:
- Resilient to transient failures (network hiccups, rate limits)
- Better UX: Some unions complete rather than all-or-nothing failure
- Audit trail preserved in Metadata for failed operations

Implementation:
```python
try:
    updated_count = batch_update_arm(ot, union_ids, worker, timestamp)

    if updated_count < len(union_ids):
        logger.warning(
            f"Partial success: {updated_count}/{len(union_ids)} unions updated. "
            f"Check logs for validation errors."
        )

    return updated_count
except Exception as e:
    # Log to Metadata for audit
    metadata_repo.log_event(
        evento_tipo="BATCH_UPDATE_FAILED",
        tag_spool=tag_spool,
        worker_id=worker_id,
        worker_nombre=worker,
        operacion=operacion,
        accion="ERROR",
        metadata_json=json.dumps({"error": str(e), "union_ids": union_ids})
    )
    raise
```

**Idempotency:**
- Validation skips already-updated unions (check ARM_FECHA_FIN/SOL_FECHA_FIN)
- Retry-safe: Calling batch_update multiple times with same data has no side effects
- UUID version tokens on Union model prevent concurrent modification conflicts

---

## 4. Implementation Patterns & Best Practices

### 4.1 Follow v3.0 Proven Patterns

**ColumnMapCache Usage:**
```python
# ✅ ALWAYS use ColumnMapCache for column access
column_map = ColumnMapCache.get_or_build("Uniones", self.sheets_repo)
arm_fin_idx = column_map[normalize("ARM_FECHA_FIN")]

# ❌ NEVER hardcode column indices
arm_fin_idx = 6  # BAD - breaks if columns reorder
```

**Date Formatting:**
```python
# ✅ ALWAYS use Chile timezone utilities
from backend.utils.date_formatter import now_chile, format_datetime_for_sheets

timestamp = now_chile()  # America/Santiago aware datetime
formatted = format_datetime_for_sheets(timestamp)  # "02-02-2026 14:30:00"

# ❌ NEVER use UTC or ISO format
datetime.utcnow()  # WRONG timezone
datetime.now().isoformat()  # WRONG format
```

**Retry Pattern:**
```python
# ✅ Use existing decorator for all Sheets operations
@retry_on_sheets_error(max_retries=3, backoff_seconds=1.0)
def batch_update_arm(...):
    # Automatic retry on 429 rate limit
    pass

# ❌ Don't implement custom retry logic
```

**Cache Invalidation:**
```python
# ✅ Invalidate after ALL writes
ColumnMapCache.invalidate(sheet_name)
self.sheets_repo._cache.invalidate(f"worksheet:{sheet_name}")

# ❌ Forgetting invalidation causes stale reads
```

### 4.2 Metrics Calculation Best Practices

**On-Demand Calculation:**
```python
# ✅ Calculate when requested (no caching)
def sum_pulgadas_arm(self, ot: str) -> float:
    unions = self.get_by_ot(ot)
    total = sum(u.dn_union for u in unions if u.arm_fecha_fin is not None)
    return round(total, 2)  # 2 decimal precision

# ❌ Don't write metrics to Operaciones columns 68-72
# Those columns are deprecated in favor of on-demand calculation
```

**Graceful Handling:**
```python
# ✅ Return 0/0.00 for empty results
if not unions:
    return 0  # count
    return 0.00  # pulgadas

# ❌ Don't raise exceptions for empty data
```

### 4.3 Testing Strategy

**Unit Tests (mock SheetsRepository):**
- Test batch_update with 1, 10, 100 unions
- Test validation (already-completed, missing unions)
- Test OT→TAG_SPOOL lookup
- Test auto-chunking (900 row limit)
- Test error handling (partial failures)

**Integration Tests (real Sheets mock data):**
- Test end-to-end batch update flow
- Test cache invalidation
- Test retry on 429 rate limit
- Test concurrent updates (optimistic locking)

**Example from test_union_repository.py:**
```python
def test_batch_update_arm(mock_sheets_repository):
    """Test batch update ARM completion for multiple unions."""
    repo = UnionRepository(mock_sheets_repository)

    # Setup: 3 unions pending ARM
    union_ids = ["OT-123+1", "OT-123+2", "OT-123+3"]
    worker = "MR(93)"
    timestamp = now_chile()

    # Execute batch update
    updated_count = repo.batch_update_arm("OT-123", union_ids, worker, timestamp)

    # Assert
    assert updated_count == 3

    # Verify batch_update was called once (not 3 times)
    assert mock_sheets_repository.batch_update.call_count == 1
```

---

## 5. Scale & Performance Analysis

### 5.1 Expected Scale (from Phase Context)

**Sheet Size:**
- Month 1: ~300 rows (30 spools × 10 unions)
- Month 6: ~1000 rows (100 spools × 10 unions)
- Typical OT: 5-10 unions

**Operation Volume:**
- Peak: 30-50 workers simultaneous
- 10-15 req/sec peak load
- Typical FINALIZAR: 7-10 unions selected

### 5.2 Performance Targets

**Phase 10 Requirement:**
> "UnionService can process selection with batch update and metadata logging in under 1 second for 10 unions"

**Breakdown:**
1. Fetch disponibles: ~200ms (read Uniones sheet, cached)
2. Batch update ARM (10 unions): ~300ms (single API call, 20 ranges)
3. Batch log Metadata (10 events): ~300ms (single append_rows)
4. Update Operaciones metrics: ~200ms (5 cells)
**Total: ~1000ms ✅**

**Comparison to Loop Approach:**
1. Fetch disponibles: ~200ms
2. Update 10 unions individually: 10 × 300ms = 3000ms ❌
3. Log 10 events individually: 10 × 300ms = 3000ms ❌
4. Update Operaciones: ~200ms
**Total: ~6400ms ❌ (6.4x slower)**

### 5.3 Google Sheets API Limits

**Rate Limits:**
- 60 writes/min/user
- 300 reads/min/user
- 500 requests/100s/project

**Quota Management:**
- Batch operations count as 1 write (not N writes)
- Cache reduces read quota usage by 80-90%
- Retry-with-backoff handles 429 errors automatically

**Batch Size Limits:**
- Max 1000 rows per `append_rows()` call
- Safe limit: 900 rows (10% buffer for v4.0)
- Max 1000 ranges per `batch_update()` call
- Typical: 20 ranges for 10 unions (2 fields each)

---

## 6. Data Relationships & Schema

### 6.1 OT → TAG_SPOOL → Uniones Relationship

```
Operaciones Sheet:
Column C (OT) → Column G (TAG_SPOOL)
Example: "OT-2026-042" → "TEST-01"

Uniones Sheet:
Column B (TAG_SPOOL) ← Foreign Key
Example: "TEST-01" has 10 unions (N_UNION: 1-10)
```

**Join Strategy:**
```python
# Step 1: OT → TAG_SPOOL (Operaciones lookup)
tag_spool = get_tag_spool_by_ot("OT-2026-042")  # "TEST-01"

# Step 2: TAG_SPOOL → Uniones (existing method)
unions = get_by_spool("TEST-01")  # 10 unions
```

**Alternative (if needed in future):**
- Add OT column to Uniones sheet (redundant but faster)
- Current approach is acceptable for v4.0 scale

### 6.2 Uniones Sheet Structure (18 columns)

**Phase 7 Status:** Structure complete, data population pending Engineering

| Column | Name | Type | Nullable | Notes |
|--------|------|------|----------|-------|
| 1 | ID | int | NO | Composite PK: {TAG_SPOOL}+{N_UNION} |
| 2 | TAG_SPOOL | string | NO | FK to Operaciones.TAG_SPOOL |
| 3 | N_UNION | int | NO | 1-20, unique within TAG_SPOOL |
| 4 | DN_UNION | float | NO | Diameter in inches, 1 decimal |
| 5 | TIPO_UNION | string | NO | Brida, Socket, Acople, Codo |
| 6 | ARM_FECHA_INICIO | datetime | YES | DD-MM-YYYY HH:MM:SS |
| 7 | ARM_FECHA_FIN | datetime | YES | **Updated by batch_update_arm** |
| 8 | ARM_WORKER | string | YES | **Updated by batch_update_arm** |
| 9 | SOL_FECHA_INICIO | datetime | YES | DD-MM-YYYY HH:MM:SS |
| 10 | SOL_FECHA_FIN | datetime | YES | **Updated by batch_update_sold** |
| 11 | SOL_WORKER | string | YES | **Updated by batch_update_sold** |
| 12 | NDT_FECHA | date | YES | DD-MM-YYYY |
| 13 | NDT_STATUS | string | YES | APROBADO/RECHAZADO/empty |
| 14 | version | UUID | NO | UUID4 for optimistic locking |
| 15 | Creado_Por | string | NO | INICIALES(ID) format |
| 16 | Fecha_Creacion | datetime | NO | DD-MM-YYYY HH:MM:SS |
| 17 | Modificado_Por | string | YES | INICIALES(ID) format |
| 18 | Fecha_Modificacion | datetime | YES | DD-MM-YYYY HH:MM:SS |

### 6.3 Metadata Sheet Structure (11 columns for v4.0)

**Phase 7 Migration:** Column K (N_UNION) added at position 11

| Column | Name | Type | Nullable | Notes |
|--------|------|------|----------|-------|
| A | id | UUID | NO | Event UUID |
| B | timestamp | datetime | NO | DD-MM-YYYY HH:MM:SS |
| C | evento_tipo | enum | NO | UNION_ARM_REGISTRADA, etc. |
| D | tag_spool | string | NO | Spool reference |
| E | worker_id | int | NO | Worker ID |
| F | worker_nombre | string | NO | INICIALES(ID) |
| G | operacion | enum | NO | ARM/SOLD/METROLOGIA |
| H | accion | enum | NO | COMPLETAR |
| I | fecha_operacion | date | NO | DD-MM-YYYY |
| J | metadata_json | JSON | YES | Additional data |
| K | n_union | int | **YES** | **NEW: Union number** |

**Event Types for v4.0:**
- `UNION_ARM_REGISTRADA` - Union ARM completion logged
- `UNION_SOLD_REGISTRADA` - Union SOLD completion logged
- `SPOOL_CANCELADO` - 0 unions selected in FINALIZAR (special case)

---

## 7. Open Questions & Recommendations

### 7.1 OT vs TAG_SPOOL Query Pattern

**Question:** Should all repository methods accept `ot` parameter or `tag_spool`?

**Context:**
- Phase discussion emphasizes "OT relationship critical"
- Current implementation uses TAG_SPOOL
- OT → TAG_SPOOL is 1:1 mapping in current schema

**Recommendation:**
- **Phase 8:** Implement both patterns
  - `get_by_ot(ot)` - Does OT→TAG_SPOOL lookup internally
  - `get_by_spool(tag_spool)` - Direct query (existing)
- **Rationale:** Flexibility for service layer to use either pattern
- **Performance:** Minimal overhead (single Operaciones lookup cached)

### 7.2 Precision for Pulgadas Sums

**Question:** 1 decimal (e.g., 18.5) or 2 decimals (e.g., 18.50)?

**Context:**
- Phase discussion says "2 decimal places"
- Current `sum_pulgadas()` uses 1 decimal: `round(total, 1)`

**Recommendation:**
- **Change to 2 decimals:** `round(total, 2)`
- **Rationale:** Aligns with phase discussion decision
- **Impact:** Minimal (display formatting change)

### 7.3 Method Granularity

**Question:** Single `get_unions_by_ot(ot)` vs separate `get_disponibles_arm(ot)`, `get_disponibles_sold(ot)`?

**Recommendation:**
- **Keep current pattern:** Single `get_disponibles(operacion)` that returns grouped dict
- **Add convenience methods** for service layer clarity:
  ```python
  def get_disponibles_arm_by_ot(ot: str) -> list[Union]:
      tag_spool = self._get_tag_spool_by_ot(ot)
      disponibles = self.get_disponibles("ARM")
      return disponibles.get(tag_spool, [])
  ```
- **Rationale:** Balance between simplicity and intent clarity

### 7.4 Batch Update Validation Strictness

**Question:** Fail entire batch if 1 union invalid, or skip invalid and continue?

**Recommendation:**
- **Skip invalid with warning** (resilient approach)
- **Log validation errors** to Metadata
- **Return count of successfully updated** unions
- **Rationale:** Better UX, aligns with phase context decision on error handling

---

## 8. Dependencies & Blockers

### 8.1 Engineering Dependency (Non-Blocking for Code)

**Status:** Uniones sheet structure complete, data population pending

**Impact:**
- Phase 8 code can be written and unit tested with mocks
- Integration tests require populated Uniones sheet
- End-to-end testing blocked until Engineering completes data

**Timeline:**
- Code implementation: Can proceed immediately
- Integration testing: Blocked on Engineering (8-12 hours estimated)
- Deployment: Blocked until Uniones fully populated

**Mitigation:**
- Write comprehensive unit tests with mock data
- Validate with `validate_uniones_sheet.py` script
- Coordinate with Engineering using `docs/engineering-handoff.md`

### 8.2 Phase 7 Prerequisites (Complete)

✅ Union Pydantic model (18 fields)
✅ Uniones sheet schema validation
✅ Metadata N_UNION column migration
✅ Operaciones 5-column extension (68-72)
✅ ColumnMapCache integration

---

## 9. Success Criteria Breakdown

**From Phase 8 Requirements:**

1. ✅ **Fetch disponibles:** `get_disponibles(operacion)` exists with ARM/SOLD filtering
   - **Gap:** Need OT-based variant `get_disponibles_by_ot(ot, operacion)`

2. ❌ **Batch update ARM/SOLD:** Need `batch_update_arm()` and `batch_update_sold()` with A1 notation
   - **Implementation:** 2-3 hours (proven pattern from SheetsRepository)

3. ✅ **Count/sum metrics:** `count_completed()` and `sum_pulgadas()` exist
   - **Gap:** Need OT-based variants + change precision to 2 decimals

4. ❌ **Metadata batch logging:** Need `batch_log_events()` with auto-chunking
   - **Implementation:** 1-2 hours (extend MetadataEvent model + chunking logic)

5. ✅ **Union model validation:** 18 fields complete with worker format validation

**Estimated Implementation:** 6-8 hours for core functionality + 4-6 hours for comprehensive tests

---

## 10. Key Takeaways for Planning

### What You Need to Know

1. **Infrastructure is Solid:** 80% of needed patterns already exist in v3.0/v2.1 code
2. **Batch Operations Critical:** Must use `gspread.batch_update()` for <1s performance target
3. **OT Relationship:** Implement OT→TAG_SPOOL lookup in repository, keep TAG_SPOOL as FK
4. **Metadata Extension:** Add N_UNION field (schema ready, model update needed)
5. **Error Handling:** Skip invalid unions with logging, return success count (resilient)
6. **Engineering Dependency:** Code can be written now, integration tests need populated Uniones
7. **Testing Strategy:** Unit tests with mocks first, integration tests when data ready
8. **Performance:** Batch approach is 6-10x faster than loop (300ms vs 3s for 10 unions)

### Implementation Priority

**High Priority (Phase 8 Core):**
1. `batch_update_arm()` and `batch_update_sold()` methods
2. `batch_log_events()` with auto-chunking
3. MetadataEvent N_UNION field extension
4. OT-based query methods
5. Comprehensive unit tests

**Medium Priority (Nice to Have):**
1. Validation helper methods
2. Row lookup optimization
3. Integration tests (depends on Engineering)

**Low Priority (Future Phases):**
1. Performance monitoring
2. Metrics dashboard
3. Retry statistics logging

### Risks & Mitigation

**Risk 1:** Engineering data population delays
- **Mitigation:** Unit test with mocks, defer integration tests

**Risk 2:** Google Sheets rate limiting
- **Mitigation:** Retry decorator + batch operations (already built-in)

**Risk 3:** OT→TAG_SPOOL relationship changes
- **Mitigation:** Abstract lookup into helper method, easy to change

**Risk 4:** Performance target not met
- **Mitigation:** Proven batch patterns from v3.0, load testing before deployment

---

## 11. Recommended Plan Outline

### Plan 1: Batch Update Methods (REPO-03, REPO-04)
- Implement `batch_update_arm()` using gspread.batch_update pattern
- Implement `batch_update_sold()` with same pattern
- Add validation helper `_validate_unions_for_update()`
- Add row lookup helper `_find_union_row()`
- Unit tests with mock SheetsRepository

### Plan 2: OT-Based Queries (REPO-01, REPO-02)
- Implement `get_by_ot()` with OT→TAG_SPOOL lookup
- Add convenience methods `get_disponibles_arm_by_ot()`, `get_disponibles_sold_by_ot()`
- Update existing methods to support both TAG_SPOOL and OT
- Unit tests for OT queries

### Plan 3: Metrics Aggregation (REPO-05, REPO-06)
- Implement `count_completed_arm(ot)` and `count_completed_sold(ot)`
- Implement `sum_pulgadas_arm(ot)` and `sum_pulgadas_sold(ot)` with 2 decimal precision
- Add `get_total_uniones(ot)` for Total_Uniones metric
- Unit tests for all aggregation methods

### Plan 4: Metadata Batch Logging (REPO-07, REPO-08)
- Extend MetadataEvent model with `n_union: Optional[int]` field
- Update `to_sheets_row()` to include N_UNION (column K)
- Update `from_sheets_row()` to parse N_UNION (backward compatible)
- Implement `batch_log_events()` with 900-row auto-chunking
- Unit tests for batch logging and chunking

### Plan 5: Integration Tests & Validation (REPO-09)
- Create mock Uniones data (100 rows) for testing
- Integration tests for batch update flow
- Integration tests for metrics calculation
- Integration tests for Metadata batch logging
- End-to-end test: FINALIZAR with 10 unions (validate <1s target)

---

**Research Complete. Ready for planning.**
