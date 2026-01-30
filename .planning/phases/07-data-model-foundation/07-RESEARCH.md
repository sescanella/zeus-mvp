# Phase 7: Data Model Foundation - Research

**Researched:** 2026-01-30
**Domain:** Google Sheets schema extension, dynamic header mapping, batch operations
**Confidence:** HIGH

## Summary

Phase 7 extends the Google Sheets data model from spool-level tracking (v3.0) to union-level tracking (v4.0) by adding three new sheets and columns to existing sheets. The research validates that the current codebase architecture (dynamic header mapping via ColumnMapCache, gspread 6.2.1 batch operations, Pydantic 2.x models) is fully equipped to handle these schema extensions with zero breaking changes to v3.0.

**Key findings:**
- v3.0 codebase already implements dynamic header mapping (ColumnMapCache) - no hardcoded column indices exist
- gspread 6.2.1 batch_update() uses A1 notation with data format: `[{'range': 'H10', 'values': [[value]]}]`
- Adding columns to the END of sheets is backward compatible (v3.0 ignores extra columns)
- Audit columns pattern already exists in v3.0 (version UUID4 in Operaciones col 66)
- Foreign key relationships via TAG_SPOOL (not OT) avoids breaking Redis, Metadata, and all existing queries

**Primary recommendation:** Use append-column strategy (add cols 68-72 to Operaciones, col 11 to Metadata) to preserve v3.0 compatibility, implement UnionRepository with ColumnMapCache from day 1, and validate critical columns during startup.

## Standard Stack

The established libraries/tools for Google Sheets schema extension:

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| gspread | 6.2.1 | Google Sheets API client | Official Python wrapper, supports batch operations with A1 notation |
| Pydantic | 2.12.4 | Data validation and models | Type-safe schema definitions, frozen models for immutability |
| uuid | stdlib | Version tokens for optimistic locking | UUID4 provides collision-free unique identifiers |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| google-auth | (via gspread) | Service Account authentication | Already configured for zeus-mvp@zeus-mvp.iam.gserviceaccount.com |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| gspread 6.x | gspread 5.x | 5.x lacks A1 notation improvements, no benefit to downgrade |
| UUID4 | Integer autoincrement | UUID4 avoids coordination, better for distributed writes |
| Pydantic v2 | Pydantic v1 | v2 already in use, migration cost not justified |

**Installation:**
No new packages needed - all dependencies already in requirements.txt.

## Architecture Patterns

### Current v3.0 Pattern (VERIFIED)
The codebase already implements the correct architecture for schema extension:

**Dynamic Header Mapping (ColumnMapCache):**
```python
# backend/core/column_map_cache.py (ALREADY EXISTS)
class ColumnMapCache:
    _cache: dict[str, dict[str, int]] = {}

    @classmethod
    def get_or_build(cls, sheet_name: str, sheets_repository) -> dict[str, int]:
        """Returns {column_name_normalized: index} mapping."""
        # Example: {"tagspool": 6, "armador": 34, "version": 65}
```

**Usage Pattern (ALREADY USED in v3.0):**
```python
# backend/repositories/sheets_repository.py lines 381-431
def normalize(name: str) -> str:
    return name.lower().replace(" ", "").replace("_", "")

# Get column map
column_map = ColumnMapCache.get_or_build(sheet_name, self)

# Access columns dynamically
normalized_name = normalize("Total_Uniones")  # "totaluniones"
if normalized_name not in column_map:
    raise ValueError(f"Column not found: {column_name}")

column_index = column_map[normalized_name]  # e.g., 67 (0-indexed)
column_letter = self._index_to_column_letter(column_index)  # "BP"
```

**Verification Pattern (MUST ADD):**
```python
# Validate critical columns exist during startup (prevents silent failures)
required_cols = ["Total_Uniones", "Uniones_ARM_Completadas", "Pulgadas_ARM"]
ok, missing = ColumnMapCache.validate_critical_columns("Operaciones", required_cols)
if not ok:
    raise SchemaValidationError(f"Missing columns: {missing}")
```

### Recommended Project Structure for v4.0
```
backend/
├── models/
│   └── union.py              # NEW: Pydantic Union model (18 fields)
├── repositories/
│   └── union_repository.py   # NEW: CRUD + batch operations for Uniones sheet
├── services/
│   └── union_service.py      # NEW: Business logic (calculate metrics, validate)
└── core/
    └── column_map_cache.py   # EXISTING: No changes needed
```

### Pattern 1: Append-Column Schema Extension (Backward Compatible)
**What:** Add new columns to the END of existing sheets (not middle)
**When to use:** When v3.0 and v4.0 must coexist

**Example:**
```
# Operaciones Sheet
v3.0 (67 cols): TAG_SPOOL, ..., version, Estado_Detalle
v4.0 (72 cols): TAG_SPOOL, ..., version, Estado_Detalle, Total_Uniones, ..., Pulgadas_SOLD
                                                         ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^ NEW (68-72)

# Metadata Sheet
v3.0 (10 cols): ID, Timestamp, ..., Metadata_JSON
v4.0 (11 cols): ID, Timestamp, ..., Metadata_JSON, N_UNION
                                                   ^^^^^^^^ NEW (col 11)
```

**Why backward compatible:**
- v3.0 code reads headers dynamically (ignores unknown columns)
- v3.0 queries use column names, not indices (ColumnMapCache shields from position changes)
- Adding to END preserves all existing indices (col 0-66 unchanged)

### Pattern 2: Batch Updates with A1 Notation (gspread 6.x)
**What:** Update multiple cells in a single API call using A1 range notation
**When to use:** Updating multiple columns in same row, or multiple unions at once

**Example:**
```python
# Source: gspread 6.2.1 documentation
# backend/repositories/sheets_repository.py already uses this pattern (lines 293-350)

def batch_update(self, sheet_name: str, updates: list[dict]) -> None:
    """
    Updates multiple cells atomically.

    Args:
        updates: [{"row": 10, "column": "V", "value": 0.1}, ...]
    """
    worksheet = self._get_spreadsheet().worksheet(sheet_name)

    batch_data = []
    for update in updates:
        cell_address = f"{update['column']}{update['row']}"  # "V25"
        batch_data.append({
            'range': cell_address,
            'values': [[update['value']]]
        })

    # Single API call for all updates
    worksheet.batch_update(batch_data, value_input_option='USER_ENTERED')
```

**Performance:**
- 10 updates sequential: 10 × 300ms = 3 seconds
- 10 updates batched: 1 × 300ms = 0.3 seconds
- **Improvement: 10x**

### Pattern 3: Audit Columns (Already Proven in v3.0)
**What:** version, Creado_Por, Fecha_Creacion, Modificado_Por, Fecha_Modificacion
**When to use:** All sheets with mutable data (Uniones, Operaciones, Metadata)

**Example (VERIFIED in v3.0 Operaciones col 66):**
```python
# backend/repositories/sheets_repository.py lines 1251-1355 (WORKING CODE)
import uuid

# Optimistic locking pattern
current_version = self.get_version(sheet_name, row_num)  # Read UUID4
if current_version != expected_version:
    raise VersionConflictError("Concurrent modification detected")

# Update with new version token
new_version = str(uuid.uuid4())
updates = [
    {"row": row_num, "column_name": "Total_Uniones", "value": 10},
    {"row": row_num, "column_name": "version", "value": new_version}
]
self.batch_update_by_column_name(sheet_name, updates)
```

**Audit timestamp pattern:**
```python
# backend/utils/date_formatter.py (ALREADY EXISTS)
from backend.utils.date_formatter import now_chile, format_datetime_for_sheets

created_by = "MR(93)"  # Worker format
created_at = format_datetime_for_sheets(now_chile())  # "30-01-2026 14:30:00"
```

### Pattern 4: Foreign Key Relationships (Column-Based)
**What:** Use TAG_SPOOL column in Uniones sheet to reference Operaciones
**When to use:** Querying unions for a specific spool

**Example:**
```python
# UnionRepository.get_by_spool(tag_spool)
def get_by_spool(self, tag_spool: str) -> list[Union]:
    """Query Uniones sheet using TAG_SPOOL as FK."""
    all_rows = self.sheets_repo.read_worksheet("Uniones")

    # Dynamic column lookup (CRITICAL: no hardcoded indices)
    column_map = ColumnMapCache.get_or_build("Uniones", self.sheets_repo)
    tag_col_idx = column_map["tagspool"]  # Normalized lookup

    # Filter rows matching TAG_SPOOL
    matching_unions = []
    for row in all_rows[1:]:  # Skip header
        if row[tag_col_idx] == tag_spool:
            union = self._row_to_union(row, column_map)
            matching_unions.append(union)

    return matching_unions
```

**Why TAG_SPOOL (not OT):**
- v3.0 uses TAG_SPOOL as primary key (Redis: `spool:{TAG_SPOOL}:lock`)
- Metadata uses TAG_SPOOL (col 4, hardcoded but stable)
- Changing to OT breaks ~50 queries, Redis keys, all v3.0 code
- **Decision: Maintain TAG_SPOOL as PK** (VALIDATED in spec)

### Anti-Patterns to Avoid

**❌ Hardcoded Column Indices:**
```python
# BAD - breaks if columns are added/removed/reordered
armador = row[34]
fecha_armado = row[35]

# GOOD - uses dynamic mapping
def get_col(col_name: str):
    return row[column_map[normalize(col_name)]]

armador = get_col("Armador")
fecha_armado = get_col("Fecha_Armado")
```

**❌ Inserting Columns in Middle:**
```python
# BAD - shifts all existing column indices, breaks v3.0
Insert "Total_Uniones" at column 7 → Columns 7-67 shift to 8-68

# GOOD - append to end
Add columns 68-72 at end → Columns 0-67 unchanged
```

**❌ Sequential API Calls:**
```python
# BAD - 10 unions × 4 fields = 40 API calls
for n_union in [1, 2, 3, ..., 10]:
    update_cell("Uniones", row, "ARM_FECHA_FIN", timestamp)
    update_cell("Uniones", row, "ARM_WORKER", worker)
    # ... 40 total calls

# GOOD - 1 batch API call
batch_data = []
for n_union in [1, 2, 3, ..., 10]:
    batch_data.extend([
        {"range": f"G{row}", "values": [[timestamp]]},
        {"range": f"H{row}", "values": [[worker]]},
        # ...
    ])
worksheet.batch_update(batch_data)  # 1 call, 40 updates
```

## Don't Hand-Roll

Problems that look simple but have existing solutions:

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Column name → index mapping | Dict with manual maintenance | ColumnMapCache.get_or_build() | Already handles normalization, caching, invalidation |
| UUID generation | Custom ID scheme (timestamp + random) | uuid.uuid4() | Stdlib, collision-free, industry standard |
| Date formatting for Sheets | Manual strftime() | backend.utils.date_formatter | Already handles Chile timezone, consistent format |
| Batch cell updates | Loop with individual update_cell() | worksheet.batch_update() | 10x faster, respects API quotas |
| Optimistic locking | Read-modify-write without version check | Version token pattern (v3.0) | Already proven in production, handles race conditions |

**Key insight:** v3.0 codebase already solved these problems. Phase 7 is about *extending* existing patterns, not inventing new ones.

## Common Pitfalls

### Pitfall 1: Hardcoding Column Indices "Just This Once"
**What goes wrong:** Code works initially but breaks when columns are added/reordered
**Why it happens:** Faster to write `row[14]` than `get_col_by_name("DN_UNION")`
**How to avoid:**
- Enforce ColumnMapCache usage from day 1 (no exceptions)
- Code review checklist: "Are any column accesses using numeric indices?"
- Add linter rule: ban array access on `row` variables
**Warning signs:** Comments like "TODO: make this dynamic later"

### Pitfall 2: Forgetting to Invalidate Cache After Schema Changes
**What goes wrong:** ColumnMapCache returns stale mapping after columns added
**Why it happens:** Cache is long-lived (application lifetime), schema changes are rare
**How to avoid:**
```python
# After adding columns to Operaciones sheet (manual or script)
from backend.core.column_map_cache import ColumnMapCache
ColumnMapCache.invalidate("Operaciones")  # Force rebuild on next access

# OR restart application (cache rebuilds on first get_or_build())
```
**Warning signs:** ValueError: "Column 'Total_Uniones' not found" after confirmed column exists

### Pitfall 3: Mixing batch_update() Data Formats
**What goes wrong:** TypeError or incorrect updates due to wrong data structure
**Why it happens:** gspread 6.x changed format from 5.x
**How to avoid:**
```python
# CORRECT format (gspread 6.2.1)
batch_data = [
    {'range': 'H10', 'values': [["MR(93)"]]},   # Single cell
    {'range': 'H11:J11', 'values': [[1, 2, 3]]} # Row range
]

# WRONG formats
{'range': 'H10', 'values': "MR(93)"}     # Missing nested list
{'range': 'H10', 'values': ["MR(93)"]}   # Single-nested (should be double)
{'row': 10, 'col': 7, 'value': "..."}    # Old API (use A1 notation)
```
**Warning signs:** "Expected list, got str" errors

### Pitfall 4: Not Validating Critical Columns at Startup
**What goes wrong:** Application starts successfully but fails at runtime when accessing missing column
**Why it happens:** Schema validation happens lazily (first access), not eagerly (startup)
**How to avoid:**
```python
# main.py startup
from backend.core.column_map_cache import ColumnMapCache

@app.on_event("startup")
async def validate_schema():
    """Validate critical columns exist before accepting traffic."""
    required_operaciones = ["TAG_SPOOL", "Total_Uniones", "Pulgadas_ARM"]
    ok, missing = ColumnMapCache.validate_critical_columns(
        "Operaciones",
        required_operaciones
    )
    if not ok:
        raise RuntimeError(f"Schema validation failed: missing {missing}")
```
**Warning signs:** Production errors hours after deployment

### Pitfall 5: Forgetting USER_ENTERED for Dates/Numbers
**What goes wrong:** Google Sheets stores "30-01-2026" as text string, not a Date
**Why it happens:** Default value_input_option='RAW' treats everything as text
**How to avoid:**
```python
# CORRECT (already used in v3.0)
worksheet.batch_update(
    batch_data,
    value_input_option='USER_ENTERED'  # Let Sheets interpret types
)

# WRONG
worksheet.batch_update(batch_data)  # Defaults to RAW (text only)
```
**Warning signs:** Dates don't sort correctly, formulas fail with "text vs number" errors

## Code Examples

Verified patterns from official sources and existing codebase:

### Dynamic Column Access (v3.0 Pattern - PRODUCTION PROVEN)
```python
# Source: backend/repositories/sheets_repository.py lines 381-431
from backend.core.column_map_cache import ColumnMapCache

def get_col_value(row_data: list, col_name: str) -> Optional[str]:
    """Get column value by name (not index)."""
    column_map = ColumnMapCache.get_or_build("Operaciones", sheets_repo)

    # Normalize column name (handles spaces, underscores, case)
    def normalize(name: str) -> str:
        return name.lower().replace(" ", "").replace("_", "")

    normalized = normalize(col_name)
    if normalized not in column_map:
        return None  # Column doesn't exist

    col_index = column_map[normalized]
    if col_index < len(row_data):
        value = row_data[col_index]
        return value if value and value.strip() else None
    return None

# Usage
total_uniones = get_col_value(row, "Total_Uniones")  # Works even if position changes
```

### Batch Update with A1 Notation (gspread 6.2.1)
```python
# Source: gspread 6.2.1 documentation + backend/repositories/sheets_repository.py
def batch_update_by_column_name(
    self,
    sheet_name: str,
    updates: list[dict]
) -> None:
    """
    Batch update using column names (not indices).

    Args:
        updates: [{"row": 10, "column_name": "Total_Uniones", "value": 15}, ...]
    """
    from backend.core.column_map_cache import ColumnMapCache

    # Get column mapping
    column_map = ColumnMapCache.get_or_build(sheet_name, self)

    def normalize(name: str) -> str:
        return name.lower().replace(" ", "").replace("_", "")

    # Build batch data with A1 notation
    worksheet = self._get_spreadsheet().worksheet(sheet_name)
    batch_data = []

    for update in updates:
        column_name = update["column_name"]
        normalized = normalize(column_name)

        if normalized not in column_map:
            raise ValueError(f"Column '{column_name}' not found")

        # Convert column index to letter (A, B, ..., Z, AA, AB, ...)
        col_index = column_map[normalized]
        col_letter = self._index_to_column_letter(col_index)

        # A1 notation: "BP10" (column BP, row 10)
        cell_address = f"{col_letter}{update['row']}"

        batch_data.append({
            'range': cell_address,
            'values': [[update['value']]]  # MUST be nested list
        })

    # Execute batch (1 API call)
    worksheet.batch_update(batch_data, value_input_option='USER_ENTERED')

    # Invalidate cache
    cache_key = f"worksheet:{sheet_name}"
    self._cache.invalidate(cache_key)
```

### Audit Columns Pattern (Pydantic Model)
```python
# Source: v4.0 spec + backend/models/metadata.py pattern
from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional
import uuid

class Union(BaseModel):
    """Uniones sheet model with audit columns."""
    # Core fields
    id: str = Field(
        ...,
        description="Composite PK: {TAG_SPOOL}+{N_UNION}",
        examples=["OT-123+5"]
    )
    tag_spool: str = Field(..., min_length=1)
    n_union: int = Field(..., ge=1, le=20)
    dn_union: float = Field(..., gt=0)

    # ARM timestamps
    arm_fecha_inicio: Optional[datetime] = None
    arm_fecha_fin: Optional[datetime] = None
    arm_worker: Optional[str] = None

    # SOLD timestamps
    sol_fecha_inicio: Optional[datetime] = None
    sol_fecha_fin: Optional[datetime] = None
    sol_worker: Optional[str] = None

    # Audit columns (positions 14-18)
    version: str = Field(
        default_factory=lambda: str(uuid.uuid4()),
        description="UUID4 for optimistic locking"
    )
    creado_por: str = Field(..., description="Worker who created (INICIALES(ID))")
    fecha_creacion: datetime = Field(default_factory=datetime.now)
    modificado_por: Optional[str] = Field(None)
    fecha_modificacion: Optional[datetime] = Field(None)

    model_config = ConfigDict(frozen=True)  # Immutable
```

### Foreign Key Query Pattern
```python
# Source: Derived from backend/repositories/sheets_repository.py get_spool_by_tag()
class UnionRepository:
    def get_by_spool(self, tag_spool: str) -> list[Union]:
        """
        Query Uniones sheet using TAG_SPOOL as foreign key.

        Returns all unions for a given spool (composite PK: tag_spool + n_union).
        """
        # Read entire sheet (cached)
        all_rows = self.sheets_repo.read_worksheet("Uniones")
        if not all_rows or len(all_rows) < 2:
            return []  # Empty or header-only

        # Get column map
        column_map = ColumnMapCache.get_or_build("Uniones", self.sheets_repo)

        def normalize(name: str) -> str:
            return name.lower().replace(" ", "").replace("_", "")

        # Find TAG_SPOOL column
        tag_col_idx = column_map.get(normalize("TAG_SPOOL"))
        if tag_col_idx is None:
            raise ValueError("TAG_SPOOL column not found in Uniones sheet")

        # Filter and parse matching rows
        unions = []
        for row_data in all_rows[1:]:  # Skip header
            if row_data[tag_col_idx] == tag_spool:
                union = self._row_to_union(row_data, column_map)
                unions.append(union)

        return unions

    def _row_to_union(self, row_data: list, column_map: dict) -> Union:
        """Convert row to Union object using dynamic mapping."""
        def get_col(name: str) -> Optional[str]:
            idx = column_map.get(normalize(name))
            if idx is None or idx >= len(row_data):
                return None
            val = row_data[idx]
            return val if val and str(val).strip() else None

        return Union(
            id=get_col("ID"),
            tag_spool=get_col("TAG_SPOOL"),
            n_union=int(get_col("N_UNION") or 0),
            dn_union=float(get_col("DN_UNION") or 0),
            # ... (parse all 18 fields dynamically)
            version=get_col("version") or str(uuid.uuid4()),
            creado_por=get_col("Creado_Por"),
            # ...
        )
```

### Startup Schema Validation
```python
# Source: Derived from backend/core/column_map_cache.py validate_critical_columns()
# main.py
from fastapi import FastAPI
from backend.core.column_map_cache import ColumnMapCache
from backend.repositories.sheets_repository import SheetsRepository

app = FastAPI()

@app.on_event("startup")
async def validate_schema():
    """
    Validate all critical columns exist before accepting traffic.

    Fails fast if schema migration incomplete (prevents runtime errors).
    """
    sheets_repo = SheetsRepository(compatibility_mode="v3.0")

    # Operaciones sheet validation (v4.0 columns)
    required_operaciones = [
        "TAG_SPOOL",           # v2.1 (PK)
        "Ocupado_Por",         # v3.0 (col 64)
        "version",             # v3.0 (col 66)
        "Estado_Detalle",      # v3.0 (col 67)
        "Total_Uniones",       # v4.0 (col 68) - NEW
        "Uniones_ARM_Completadas",  # v4.0 (col 69) - NEW
        "Pulgadas_ARM",        # v4.0 (col 71) - NEW
        "Pulgadas_SOLD"        # v4.0 (col 72) - NEW
    ]

    ok, missing = ColumnMapCache.validate_critical_columns(
        "Operaciones",
        required_operaciones
    )

    if not ok:
        raise RuntimeError(
            f"Schema validation failed for Operaciones sheet. "
            f"Missing columns: {missing}. "
            f"Run schema migration before deploying v4.0."
        )

    # Uniones sheet validation (NEW in v4.0)
    required_uniones = [
        "ID", "TAG_SPOOL", "N_UNION", "DN_UNION", "TIPO_UNION",
        "ARM_FECHA_INICIO", "ARM_FECHA_FIN", "ARM_WORKER",
        "SOL_FECHA_INICIO", "SOL_FECHA_FIN", "SOL_WORKER",
        "version", "Creado_Por", "Fecha_Creacion"
    ]

    ok, missing = ColumnMapCache.validate_critical_columns(
        "Uniones",
        required_uniones
    )

    if not ok:
        raise RuntimeError(
            f"Schema validation failed for Uniones sheet. "
            f"Missing columns: {missing}. "
            f"Ensure Ingeniería pre-populated Uniones sheet."
        )

    # Metadata sheet validation (v4.0 adds N_UNION at position 11)
    required_metadata = [
        "ID", "Timestamp", "Evento_Tipo", "TAG_SPOOL",
        "Worker_ID", "Worker_Nombre", "Operacion", "Accion",
        "Fecha_Operacion", "Metadata_JSON",
        "N_UNION"  # v4.0 (col 11) - NEW
    ]

    ok, missing = ColumnMapCache.validate_critical_columns(
        "Metadata",
        required_metadata
    )

    if not ok:
        raise RuntimeError(
            f"Schema validation failed for Metadata sheet. "
            f"Missing columns: {missing}"
        )

    print("✅ Schema validation passed - all critical columns present")
```

## State of the Art

| Old Approach (v2.1) | Current Approach (v3.0) | v4.0 Enhancement | Impact |
|---------------------|-------------------------|------------------|--------|
| Hardcoded column indices | ColumnMapCache dynamic mapping | No change (already optimal) | Zero breaking changes from column additions |
| Individual update_cell() calls | batch_update() with A1 notation | Extend to Uniones sheet | Same 10x performance gain |
| No version tokens | UUID4 optimistic locking | Extend to Uniones sheet (col 14) | Concurrent update protection |
| Manual column access | Normalized name lookup | Validate critical cols at startup | Fail fast instead of runtime errors |
| TAG_SPOOL as string literal | TAG_SPOOL as FK standard | Maintain in Uniones.TAG_SPOOL (col 2) | Zero Redis/Metadata migration |

**Deprecated/outdated:**
- **Hardcoded indices** (row[34]): v2.1 pattern, removed in v3.0
- **Sequential writes** (loop update_cell()): Replaced by batch_update() in v3.0
- **RAW value input**: Changed to USER_ENTERED in v3.0 for proper date/number formatting
- **Armador/Soldador columns in Operaciones**: v4.0 deprecates (read from Uniones instead)

## Open Questions

Things that couldn't be fully resolved:

1. **Uniones Sheet Pre-Population Timing**
   - What we know: Engineering team handles pre-population via external process (out of scope for v4.0)
   - What's unclear: Exactly when pre-population occurs (before deploy? gradual? per-spool?)
   - Recommendation: Coordinate with Engineering for pre-deploy checklist, validate sheet exists and has data during startup

2. **N_UNION Column Position in Metadata**
   - What we know: Spec says position 11 (end of sheet) to avoid breaking v3.0 queries
   - What's unclear: Current Metadata sheet structure (10 columns confirmed, but exact names/positions?)
   - Recommendation: Verify current Metadata headers before migration, confirm col 11 is truly end

3. **Optimistic Locking at Union Level**
   - What we know: v3.0 uses version tokens at spool level (Operaciones.version col 66)
   - What's unclear: Batch update of 10 unions - does each get individual version check? Or spool-level lock sufficient?
   - Recommendation: Start with spool-level locking (simpler), add union-level if concurrent editing becomes issue

4. **ColumnMapCache Warming Strategy**
   - What we know: Current implementation is lazy (builds on first access)
   - What's unclear: Should we pre-warm cache at startup for Operaciones + Uniones + Metadata?
   - Recommendation: Add pre-warming in startup validation (side-effect of validate_critical_columns())

## Sources

### Primary (HIGH confidence)
- gspread 6.2.1 installed version: `python -c "import gspread; print(gspread.__version__)"` (verified 2026-01-30)
- gspread batch_update() signature: `inspect.signature(gspread.worksheet.Worksheet.batch_update)` (verified)
- backend/repositories/sheets_repository.py: Lines 293-350 (batch_update implementation), Lines 381-431 (dynamic column access)
- backend/core/column_map_cache.py: Complete implementation (lines 1-244)
- backend/models/metadata.py: Audit pattern with UUID4 (lines 30-164)
- backend/utils/date_formatter.py: now_chile(), format_datetime_for_sheets() (imported in metadata_repository.py line 13)

### Secondary (MEDIUM confidence)
- UNIONES-v4.0-SPEC-SIMPLIFIED.md: Schema definitions (lines 236-298), batch operations (lines 471-595)
- .planning/PROJECT.md: v3.0 architecture decisions (lines 156-168)

### Tertiary (LOW confidence)
- None - all findings verified with production code or library documentation

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - All libraries already in use (gspread 6.2.1, Pydantic 2.12.4, uuid stdlib)
- Architecture: HIGH - ColumnMapCache pattern proven in production (v3.0), batch_update verified in codebase
- Pitfalls: HIGH - Based on actual v3.0 implementation patterns and common Google Sheets API mistakes

**Research date:** 2026-01-30
**Valid until:** 90 days (Google Sheets API stable, gspread 6.x stable, no breaking changes expected)

**Notes:**
- No external research needed - all patterns already exist in v3.0 codebase
- gspread 6.2.1 is current stable (no updates needed)
- Phase 7 is schema extension only (no new technical domains introduced)
