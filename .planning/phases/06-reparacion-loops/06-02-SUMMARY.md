---
phase: 06
plan: 02
subsystem: reparacion-cycle-tracking
tags: [cycle-counter, validation, bloqueado, metrologia, testing]
requires: [05-04]
provides:
  - CycleCounterService for parsing and incrementing cycles
  - MetrologiaStateMachine with cycle tracking
  - SpoolBloqueadoError exception
  - validar_puede_tomar_reparacion validation
  - 47 passing tests for cycle counting and validation
affects: [06-03, 06-04]
tech-stack:
  added: []
  patterns:
    - Embedded cycle counting in Estado_Detalle field
    - Consecutive rejection tracking (resets on APROBADO)
    - 3-cycle limit with BLOQUEADO escalation
key-files:
  created:
    - backend/services/cycle_counter_service.py
    - tests/unit/test_cycle_counter.py
    - tests/unit/test_validation_reparacion.py
  modified:
    - backend/domain/state_machines/metrologia_machine.py
    - backend/services/estado_detalle_builder.py
    - backend/services/validation_service.py
    - backend/exceptions.py
decisions:
  - id: cycle-storage
    choice: Embed cycle count in Estado_Detalle string
    rationale: Avoids schema migration, audit-friendly display
  - id: cycle-type
    choice: Consecutive rejections only (resets on APROBADO)
    rationale: Allows recovery after bad batch, prevents perpetual loops
  - id: max-cycles
    choice: 3 consecutive rejections before blocking
    rationale: Industry standard, balances recovery vs escalation
metrics:
  duration: 4.7 minutes
  tests-added: 47
  completed: 2026-01-28
---

# Phase 06 Plan 02: Cycle Counting Logic Summary

**One-liner:** Embedded cycle counter in Estado_Detalle tracks consecutive rejections with 3-cycle limit and BLOQUEADO escalation

## What Was Built

Implemented cycle counting logic that tracks consecutive rejections without requiring a dedicated database column. Cycle count is embedded in Estado_Detalle field using pattern "Ciclo X/3", increments on each metrología RECHAZADO event, and enforces 3-cycle limit by blocking spools after third rejection.

### Core Components

**1. CycleCounterService** (`backend/services/cycle_counter_service.py`)
- Parse cycle count from Estado_Detalle regex pattern `Ciclo (\d+)/3`
- Increment cycle on each rejection (max 3, caps at MAX_CYCLES)
- Check if should block after 3rd rejection
- Build formatted estado strings: RECHAZADO (Ciclo X/3), BLOQUEADO, EN_REPARACION, etc.
- Reset cycle counter after APROBADO (consecutive tracking only)

**2. MetrologiaStateMachine Extension** (`backend/domain/state_machines/metrologia_machine.py`)
- Accept `cycle_counter` dependency in `__init__`
- `on_enter_rechazado`: Read Estado_Detalle, extract cycle, increment, check if should block
- Build estado: "BLOQUEADO - Contactar supervisor" if at limit, else "RECHAZADO (Ciclo X/3)"
- `on_enter_aprobado`: Reset cycle counter via `cycle_counter.reset_cycle()`
- Update Estado_Detalle + Fecha_QC_Metrologia atomically via `batch_update_by_column_name`

**3. EstadoDetalleBuilder Extension** (`backend/services/estado_detalle_builder.py`)
- Add optional `cycle` parameter to `build()` method
- `_metrologia_to_display()` accepts cycle parameter for RECHAZADO formatting
- Format: "RECHAZADO (Ciclo 2/3) - Pendiente reparación"

**4. Validation & Exceptions**
- **SpoolBloqueadoError** (HTTP 403): Raised when trying to TOMAR BLOQUEADO spool
- **OperacionNoDisponibleError** (HTTP 400): Raised when operation not valid for current estado
- **validar_puede_tomar_reparacion()**: Check BLOQUEADO → raise, check RECHAZADO → allow, check occupied → raise
- **validar_puede_cancelar_reparacion()**: Check EN_REPARACION or REPARACION_PAUSADA required

**5. Comprehensive Test Suite**
- `test_cycle_counter.py`: 26 tests covering extraction, increment, blocking, estado building
- `test_validation_reparacion.py`: 21 tests covering TOMAR/CANCELAR validation, edge cases
- All 47 tests passing

## Technical Decisions

### Cycle Storage Strategy
**Decision:** Embed cycle count in Estado_Detalle string instead of dedicated column

**Rationale:**
- Avoids schema migration (no new column needed)
- Audit-friendly display (cycle visible in Estado_Detalle)
- Consistent with v3.0 architecture (Estado_Detalle as display string)
- Performance: Regex parsing cached via compiled pattern

**Trade-offs:**
- ✅ No schema changes, no migration needed
- ✅ Human-readable in Google Sheets
- ⚠️ Requires regex parsing (mitigated by compiled pattern)
- ❌ Can't query by cycle count directly (not needed for Phase 6)

### Consecutive vs Total Rejections
**Decision:** Track consecutive rejections only, reset counter on APROBADO

**Rationale:**
- Allows recovery after "bad batch" spike (e.g., 2 rejections, then approval → counter resets to 0)
- Prevents blocking spools with mostly-successful history
- Industry best practice (2025-2026 manufacturing standards)

**Implementation:**
- `on_enter_aprobado`: Call `cycle_counter.reset_cycle()` → "METROLOGIA_APROBADO ✓"
- `on_enter_rechazado`: Read current cycle, increment, check limit
- Breaking consecutive chain restarts from 0

### 3-Cycle Limit
**Decision:** Block after 3 consecutive rejections (MAX_CYCLES = 3)

**Rationale:**
- Industry standard (most manufacturing systems use 3-5 attempt limits)
- Balances recovery opportunity vs escalation necessity
- Forces root cause analysis after 3 failures
- Prevents infinite rework loops

**Alternatives considered:**
- 5 cycles: Too permissive, delays escalation
- Unlimited: Perpetual rework, no forcing function for quality improvement
- 1-2 cycles: Too strict, doesn't allow for legitimate multi-attempt repairs

## Key Patterns

### Pattern 1: Embedded Cycle Counter
```python
# Parse cycle from estado
estado = "RECHAZADO (Ciclo 2/3) - Pendiente reparación"
cycle = cycle_counter.extract_cycle_count(estado)  # Returns 2

# Increment and check
new_cycle = cycle_counter.increment_cycle(cycle)  # Returns 3
should_block = cycle_counter.should_block(new_cycle)  # Returns True

# Build new estado
if should_block:
    estado = "BLOQUEADO - Contactar supervisor"
else:
    estado = "RECHAZADO (Ciclo 3/3) - Pendiente reparación"
```

### Pattern 2: Consecutive Tracking with Reset
```python
# Scenario: 2 rejections → approval → 1 rejection
# Rejection 1
cycle = 0 → 1  # "RECHAZADO (Ciclo 1/3)"

# Rejection 2
cycle = 1 → 2  # "RECHAZADO (Ciclo 2/3)"

# APROBADO resets cycle
cycle = reset → 0  # "METROLOGIA_APROBADO ✓"

# Rejection after approval starts fresh
cycle = 0 → 1  # "RECHAZADO (Ciclo 1/3)" (NOT Ciclo 3/3)
```

### Pattern 3: Atomic Estado Updates
```python
# MetrologiaStateMachine.on_enter_rechazado
# Update Fecha_QC_Metrologia + Estado_Detalle atomically
self.sheets_repo.batch_update_by_column_name(
    sheet_name="Operaciones",
    updates=[
        {"row": row_num, "column_name": "Fecha_QC_Metrología", "value": fecha_str},
        {"row": row_num, "column_name": "Estado_Detalle", "value": estado_detalle}
    ]
)
```

## Test Coverage

### test_cycle_counter.py (26 tests)
**Extraction (7 tests):**
- Extract from RECHAZADO, BLOQUEADO, EN_REPARACION, REPARACION_PAUSADA
- Return 0 for no cycle info, MAX_CYCLES for BLOQUEADO

**Increment (4 tests):**
- Normal progression: 0 → 1 → 2 → 3
- Cap at MAX_CYCLES (3 → 3, 4 → 3)

**Blocking Logic (3 tests):**
- Block at cycle >= 3
- Allow below 3

**Estado Building (9 tests):**
- RECHAZADO with cycle 1/2/3
- BLOQUEADO at limit
- EN_REPARACION with/without worker
- REPARACION_PAUSADA
- Reset removes cycle info

**Integration (3 tests):**
- Full cycle progression 0 → 1 → 2 → 3 → BLOQUEADO
- Cycle reset after approval
- Extraction from complex estado strings

### test_validation_reparacion.py (21 tests)
**TOMAR BLOQUEADO Validation (2 tests):**
- Raise SpoolBloqueadoError for BLOQUEADO estado

**TOMAR RECHAZADO Validation (3 tests):**
- Allow TOMAR when RECHAZADO and not occupied
- Allow cycle 1, 2, without cycle info

**Estado Validation (4 tests):**
- Raise OperacionNoDisponibleError for APROBADO, PENDIENTE_METROLOGIA, ARM EN_PROGRESO, null estado

**Occupation Validation (3 tests):**
- Raise SpoolOccupiedError when occupied
- Handle malformed ocupado_por format

**CANCELAR Validation (6 tests):**
- Allow CANCELAR EN_REPARACION, REPARACION_PAUSADA
- Raise OperacionNoIniciadaError for RECHAZADO, BLOQUEADO, APROBADO, null estado

**Role Validation (1 test):**
- Any worker can TOMAR reparación (no role restriction)

**Edge Cases (2 tests):**
- Empty estado_detalle string
- Null estado_detalle

## Integration Points

### Upstream (Depends On)
- **05-04**: MetrologiaStateMachine base implementation
- **Phase 5**: Estado_Detalle as display string pattern

### Downstream (Affects)
- **06-03**: ReparacionStateMachine will use CycleCounterService for estado formatting
- **06-04**: Frontend will display cycle count from API responses
- **Future**: Metadata logging will include cycle count in metadata_json

## Deviations from Plan

None - plan executed exactly as written.

## Performance Characteristics

- **Regex parsing**: Compiled pattern cached (negligible overhead)
- **Cycle extraction**: O(1) regex search
- **Estado updates**: Single batch_update_by_column_name (2 columns atomically)
- **Test execution**: 47 tests run in 0.12 seconds

## Next Phase Readiness

**Phase 6 Plan 03 (ReparacionStateMachine) can proceed:**
- ✅ CycleCounterService ready for estado formatting
- ✅ Validation methods available for TOMAR/CANCELAR
- ✅ SpoolBloqueadoError exception ready for API error handling
- ✅ EstadoDetalleBuilder supports cycle parameter

**Unblocked work:**
- Create ReparacionStateMachine with RECHAZADO → EN_REPARACION → REPARACION_PAUSADA → PENDIENTE_METROLOGIA
- Implement POST /api/actions/tomar-reparacion endpoint
- Frontend spool filtering with BLOQUEADO handling

## Lessons Learned

1. **Embedded state is sufficient**: No need for dedicated cycle column - Estado_Detalle embedding works well
2. **Consecutive vs total matters**: Reset on approval allows recovery, prevents blocking long-lived spools
3. **Test-driven validation**: 47 tests caught edge cases (malformed ocupado_por, null estados)
4. **Atomic updates critical**: batch_update_by_column_name prevents race conditions between Fecha and Estado updates

---

**Duration:** 4.7 minutes
**Tests Added:** 47 (all passing)
**Commits:** 4 (c0e44de, 22a928e, 6179f3e, 934a38b)
**Completed:** 2026-01-28
