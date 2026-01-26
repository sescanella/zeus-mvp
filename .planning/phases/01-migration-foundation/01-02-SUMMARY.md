# Phase 01 Plan 02: Column Mapping Infrastructure for v3.0 Summary

---
phase: 01-migration-foundation
plan: 02
subsystem: data-infrastructure
status: complete
tags: [migration, column-mapping, backward-compatibility, v3.0, pydantic]

# Dependency Graph
requires:
  - 01-01: Backup and Schema Expansion Scripts (V3_COLUMNS config)
provides:
  - Spool model with v3.0 fields (ocupado_por, fecha_ocupacion, version)
  - EventoTipo enum with TOMAR_SPOOL and PAUSAR_SPOOL events
  - EstadoOcupacion enum (DISPONIBLE, OCUPADO)
  - SheetsRepository v3.0 column access methods
  - Compatibility mode for safe v2.1 → v3.0 migration
affects:
  - 01-03: State machine implementation (uses v3.0 fields and enums)
  - 01-04: Frontend updates (displays occupation status)
  - All Phase 2+ plans: Depend on v3.0 data model being available

# Tech Stack
tech-stack.added:
  - None (leveraged existing Pydantic, gspread infrastructure)
tech-stack.patterns:
  - Compatibility mode pattern for safe migrations
  - Computed properties (@property) for derived state
  - Dynamic column mapping with normalization
  - Safe defaults for backward compatibility

# File Changes
key-files.created:
  - backend/scripts/verify_v3_compatibility.py: Comprehensive compatibility test suite

key-files.modified:
  - backend/models/spool.py: Added ocupado_por, fecha_ocupacion, version fields + esta_ocupado property
  - backend/models/enums.py: Added EventoTipo (TOMAR_SPOOL, PAUSAR_SPOOL) and EstadoOcupacion enums
  - backend/repositories/sheets_repository.py: Added v3.0 read/write methods + compatibility_mode
  - backend/services/sheets_service.py: Extended parse_spool_row to parse v3.0 columns
  - tests/conftest.py: Added v3.0 column indices to mock_column_map_operaciones

# Decisions
decisions:
  - decision: Use compatibility_mode flag instead of dual-write approach
    rationale: Simpler implementation, explicit migration control, no complex sync logic
    alternatives: [dual-write to both v2.1 and v3.0 columns, feature flags]

  - decision: Default to v2.1 mode until migration complete
    rationale: Safe rollout - existing code unaffected, opt-in to v3.0 features
    alternatives: [default to v3.0 mode, auto-detect based on column presence]

  - decision: Return safe defaults (None/0) in v2.1 mode for v3.0 columns
    rationale: Prevents errors, allows gradual migration, no breaking changes
    alternatives: [raise exceptions, log errors, return sentinel values]

  - decision: Add esta_ocupado as computed property instead of stored field
    rationale: Single source of truth (ocupado_por), always consistent, no sync issues
    alternatives: [separate boolean field, derive from multiple fields]

# Metrics
duration: 5 minutes
completed: 2026-01-26
tasks_completed: 3
commits: 3
files_changed: 6
---

## One-liner

Extended column mapping and Spool model to support v3.0 occupation fields with backward-compatible repository methods

## What Was Built

### Model Extensions (2 files)

1. **backend/models/spool.py** - v3.0 field additions
   - Added `ocupado_por: Optional[str]` - Worker occupying spool (format: "INICIALES(ID)")
   - Added `fecha_ocupacion: Optional[str]` - Date spool was occupied (YYYY-MM-DD)
   - Added `version: int = 0` - Optimistic locking token (increments on TOMAR/PAUSAR/COMPLETAR)
   - Added `@property esta_ocupado` - Computed field (returns True if ocupado_por is not None)
   - All v2.1 fields unchanged (arm, sold, armador, soldador, fechas)

2. **backend/models/enums.py** - v3.0 event types
   - Added `EventoTipo.TOMAR_SPOOL` - Worker occupies spool (marks work start)
   - Added `EventoTipo.PAUSAR_SPOOL` - Worker pauses work (releases resource)
   - Added `EstadoOcupacion` enum - DISPONIBLE (free) vs OCUPADO (occupied)
   - Preserved all v2.1 events (INICIAR_ARM, COMPLETAR_SOLD, etc.)

### Repository Infrastructure (2 files)

3. **backend/repositories/sheets_repository.py** - v3.0 column access
   - Added `compatibility_mode` parameter to `__init__` ("v2.1" or "v3.0")
   - Read methods:
     * `get_ocupado_por(sheet_name, row)` - Returns worker name or None
     * `get_fecha_ocupacion(sheet_name, row)` - Returns date or None
     * `get_version(sheet_name, row)` - Returns version token or 0
   - Write methods:
     * `set_ocupado_por(sheet_name, row, worker_nombre)` - Updates Ocupado_Por column
     * `set_fecha_ocupacion(sheet_name, row, fecha)` - Updates Fecha_Ocupacion column
     * `increment_version(sheet_name, row)` - Increments version token for optimistic locking
   - **v2.1 mode behavior:** All v3.0 methods return safe defaults (None/0), writes log warnings and skip
   - **v3.0 mode behavior:** Full column access enabled

4. **backend/services/sheets_service.py** - Parse v3.0 columns
   - Extended `parse_spool_row` to read 68 columns (65 v2.1 + 3 v3.0)
   - Added dynamic column lookups for Ocupado_Por, Fecha_Ocupacion, version
   - Parses version as integer with fallback to 0 on error
   - Returns Spool with v3.0 fields populated

### Testing Infrastructure (2 files)

5. **tests/conftest.py** - v3.0 test fixtures
   - Added v3.0 column indices to `mock_column_map_operaciones`:
     * "ocupadopor": 64
     * "fechaocupacion": 65
     * "version": 66
   - Maintains all v2.1 column mocks
   - Ensures test isolation with `clear_column_map_cache` fixture

6. **backend/scripts/verify_v3_compatibility.py** - Comprehensive test suite
   - Test 1: v2.1 mode returns safe defaults for v3.0 columns
   - Test 2: v3.0 mode can access all columns
   - Test 3: Spool model has v3.0 fields with correct defaults
   - Test 4: v3.0 enums (EventoTipo, EstadoOcupacion) defined correctly
   - Test 5: Compatibility mode switching works
   - All tests pass ✅

## How It Works

### Compatibility Mode Pattern

**v2.1 Mode (default until migration):**
```python
repo = SheetsRepository(compatibility_mode="v2.1")
repo.get_ocupado_por("Operaciones", 2)  # Returns: None
repo.get_version("Operaciones", 2)       # Returns: 0
repo.set_ocupado_por("Operaciones", 2, "MR(93)")  # Logs warning, skips write
```

**v3.0 Mode (after migration):**
```python
repo = SheetsRepository(compatibility_mode="v3.0")
repo.get_ocupado_por("Operaciones", 2)  # Reads from column 64
repo.increment_version("Operaciones", 2) # Writes to column 66
```

### Column Normalization

Column names automatically normalized for lookup:
- "Ocupado_Por" → "ocupadopor"
- "Fecha_Ocupacion" → "fechaocupacion"
- "version" → "version"

This is handled by existing `SheetsService.build_column_map()` logic (lowercase, no spaces/underscores).

### Computed Property Pattern

`esta_ocupado` derived from `ocupado_por`:
```python
@property
def esta_ocupado(self) -> bool:
    return self.ocupado_por is not None
```

**Benefits:**
- Single source of truth (ocupado_por)
- Always consistent (no sync issues)
- Read-only (prevents invalid state)

### Optimistic Locking with Version Token

```python
# Check version before write
current_version = repo.get_version("Operaciones", row)
if spool.version != current_version:
    raise ConflictError("Spool was modified by another worker")

# Increment on successful write
new_version = repo.increment_version("Operaciones", row)
```

## Test Results

### Verification Summary

✅ **All compatibility tests passed (5/5):**

1. ✅ v2.1 mode returns safe defaults (None/0) for v3.0 columns
2. ✅ v3.0 mode can access all columns
3. ✅ Spool model has v3.0 fields with correct defaults
4. ✅ v3.0 enums (EventoTipo, EstadoOcupacion) defined correctly
5. ✅ Compatibility mode switching works

✅ **Backward compatibility verified:**
- v2.1 functionality unaffected by v3.0 additions
- v3.0 fields accessible when needed
- Compatibility mode provides safe migration path
- All column sets accessible

✅ **Model validation:**
```python
# v2.1 style (no v3.0 fields)
spool_v2 = Spool(tag_spool="TEST-001")
assert spool_v2.ocupado_por is None
assert spool_v2.version == 0
assert spool_v2.esta_ocupado is False  # Computed correctly

# v3.0 style (with occupation)
spool_v3 = Spool(
    tag_spool="TEST-002",
    ocupado_por="MR(93)",
    fecha_ocupacion="2026-01-26",
    version=3
)
assert spool_v3.esta_ocupado is True  # Computed correctly
```

✅ **Success Criteria Met:**
1. ColumnMapCache maps all 68 columns correctly ✅
2. Spool model has v3.0 fields without breaking v2.1 ✅
3. SheetsRepository provides v3.0 column access ✅
4. Backward compatibility ensures v2.1 continues working ✅

## Deviations from Plan

None - plan executed exactly as specified.

All three tasks completed without deviation:
1. Extended column mapping and models ✅
2. Added repository v3.0 methods with compatibility mode ✅
3. Verified backward compatibility ✅

## Next Phase Readiness

### Prerequisites for 01-03 (State Machine)

✅ **Spool model ready:** Contains v3.0 fields (ocupado_por, fecha_ocupacion, version)
✅ **Enums available:** EventoTipo.TOMAR_SPOOL, EventoTipo.PAUSAR_SPOOL, EstadoOcupacion
✅ **Repository methods:** Read/write v3.0 columns with compatibility mode

### Prerequisites for 01-04 (Frontend)

✅ **Data model defined:** Frontend can display occupation status (esta_ocupado property)
✅ **Column positions known:** 64 (Ocupado_Por), 65 (Fecha_Ocupacion), 66 (version)
✅ **Computed properties:** esta_ocupado simplifies UI logic

### Migration Execution Readiness

**Current state:**
- System defaults to v2.1 mode (existing functionality preserved)
- v3.0 columns readable but return safe defaults until schema migration runs
- Can switch to v3.0 mode after running `add_v3_columns.py` script

**Migration steps:**
1. Verify v2.1 functionality working (✅ done)
2. Run schema expansion: `python backend/scripts/add_v3_columns.py` (01-01)
3. Switch compatibility_mode to "v3.0" (01-03)
4. Deploy state machine logic (01-03)

### Concerns

None identified. All functionality works as expected.

**Minor note:** OpenSSL warning from urllib3 in macOS development environment - does not affect functionality, only appears during local testing.

## Usage Examples

### Creating Spools with v3.0 Fields

```python
# v2.1 style (backward compatible)
spool = Spool(
    tag_spool="MK-1335-CW-25238-011",
    arm=ActionStatus.PENDIENTE,
    sold=ActionStatus.PENDIENTE,
    fecha_materiales=date(2026, 1, 26)
)

# v3.0 style (with occupation)
spool = Spool(
    tag_spool="MK-1335-CW-25238-012",
    arm=ActionStatus.EN_PROGRESO,
    ocupado_por="MR(93)",
    fecha_ocupacion="2026-01-26",
    version=1
)

# Check occupation status
if spool.esta_ocupado:
    print(f"Occupied by: {spool.ocupado_por}")
```

### Using Repository v3.0 Methods

```python
# Initialize in v3.0 mode
repo = SheetsRepository(compatibility_mode="v3.0")

# Read occupation status
ocupado_por = repo.get_ocupado_por("Operaciones", 25)
version = repo.get_version("Operaciones", 25)

# Occupy spool (TOMAR_SPOOL)
repo.set_ocupado_por("Operaciones", 25, "MR(93)")
repo.set_fecha_ocupacion("Operaciones", 25, "2026-01-26")
new_version = repo.increment_version("Operaciones", 25)

# Release spool (PAUSAR_SPOOL)
repo.set_ocupado_por("Operaciones", 25, None)  # Clear worker
repo.set_fecha_ocupacion("Operaciones", 25, None)  # Clear date
repo.increment_version("Operaciones", 25)
```

### Using v3.0 Enums

```python
from backend.models.enums import EventoTipo, EstadoOcupacion

# Log occupation event
evento = EventoTipo.TOMAR_SPOOL
metadata = {
    "evento_tipo": evento.value,
    "tag_spool": "MK-123",
    "worker_id": 93
}

# Check occupation state
if spool.esta_ocupado:
    estado = EstadoOcupacion.OCUPADO
else:
    estado = EstadoOcupacion.DISPONIBLE
```

## Commits

| Hash    | Type | Message                                                          |
|---------|------|------------------------------------------------------------------|
| f0e59e1 | feat | add v3.0 fields to Spool model and enums                        |
| e5faf45 | feat | add v3.0 repository methods with compatibility mode             |
| ede681b | test | verify backward compatibility with v3.0 columns                 |

**Total commits:** 3 (all atomic, one per task)

## Lessons Learned

### What Worked Well

1. **Compatibility mode pattern:** Explicit control over migration, no surprises
2. **Computed properties:** `esta_ocupado` eliminates sync issues between fields
3. **Dynamic column mapping:** No hardcoded indices, already handles v3.0 columns
4. **Safe defaults:** Returning None/0 in v2.1 mode prevents breaking changes

### Technical Notes

1. **Normalization automatic:** Existing `build_column_map()` already handles v3.0 column name formats
2. **Pydantic validation:** Version field has `ge=0` constraint for safety
3. **Repository pattern:** Clean separation between v2.1 and v3.0 logic via compatibility_mode
4. **Test fixtures:** pytest fixtures can't be called directly - must be used as test parameters

### For Future Development

1. Consider adding validation for worker_nombre format ("INICIALES(ID)")
2. Could add helper method to parse ocupado_por into worker_id and initials
3. Could add logging for compatibility mode switches to monitor production migration
4. Could add Prometheus metrics for v3.0 column access patterns

---

**Phase:** 01-migration-foundation (1 of 6)
**Plan:** 01-02 (2 of 5 in phase)
**Status:** ✅ Complete
**Duration:** 5 minutes
**Date:** 2026-01-26
