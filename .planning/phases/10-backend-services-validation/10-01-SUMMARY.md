# Phase 10 Plan 01: Create UnionService for Batch Operations Summary

**One-liner:** UnionService orchestrates batch union updates with 1-decimal pulgadas calculation, batch/granular metadata events, and FW union exclusion from SOLD

---

## Metadata

```yaml
phase: 10
plan: 01
subsystem: backend-services
completed: 2026-02-02
duration: 5 minutes
status: complete
tags: [union-service, batch-operations, metadata-events, pulgadas-calculation, v4.0]
```

---

## Dependency Graph

```yaml
requires:
  - 08-01: UnionRepository batch update methods (batch_update_arm, batch_update_sold)
  - 08-04: MetadataRepository batch_log_events with union-level granularity
  - 07-03: Union model with 18 fields including OT foreign key

provides:
  - UnionService class for union-level workflow orchestration
  - process_selection method for batch ARM/SOLD completions
  - calcular_pulgadas with 1 decimal precision
  - build_eventos_metadata with batch + granular event structure
  - Helper methods for union validation and filtering (FW exclusion from SOLD)

affects:
  - 10-02: OccupationServiceV4 will use UnionService for FINALIZAR workflow
  - 10-03: INICIAR/FINALIZAR routers will inject UnionService
  - 11-XX: Frontend union selection UI will call FINALIZAR with union_ids
```

---

## Technical Decisions

### Decision D56: 1 Decimal Precision for Pulgadas Calculation

**Context:** Task requirements specified 1 decimal precision for pulgadas sums (e.g., 18.5)

**Decision:** Use `round(total, 1)` in `calcular_pulgadas` method

**Rationale:**
- Matches task requirement specification
- Simpler than 2-decimal precision (used in UnionRepository)
- Service layer can use different precision than repository layer

**Note:** UnionRepository uses 2 decimals (18.50) per D32 from Phase 8. This is acceptable - repository layer stores precise values, service layer can present rounded values for UI/API responses.

### Decision D57: SOLD_REQUIRED_TYPES Constant Excludes FW

**Context:** FW unions are ARM-only and do not require SOLD operations

**Decision:** Define `SOLD_REQUIRED_TYPES = ['BW', 'BR', 'SO', 'FILL', 'LET']` at module level

**Rationale:**
- Business rule: FW unions skip SOLD phase entirely
- Centralized constant prevents code duplication
- `filter_available_unions` checks against this constant for SOLD filtering

**Trade-offs:**
- Pro: Single source of truth for SOLD-required types
- Pro: Easy to modify if business rules change
- Con: Hardcoded list (could be database-driven in future)

### Decision D58: Batch + Granular Metadata Event Structure

**Context:** v4.0 requires both spool-level summary events and union-level detail events

**Decision:** `build_eventos_metadata` creates 1 batch event (N_UNION=None) + N granular events (N_UNION=1..N)

**Rationale:**
- Batch event provides spool-level summary with total pulgadas and union count
- Granular events enable union-level audit trail reconstruction
- Both use same evento_tipo (UNION_ARM_REGISTRADA or UNION_SOLD_REGISTRADA)
- metadata_json differentiates: batch has aggregates, granular has union_id

**Example:**
```
For 2 unions:
- Event 1: N_UNION=None, metadata={"union_count": 2, "pulgadas": 10.5, "union_ids": [...]}
- Event 2: N_UNION=1, metadata={"union_id": "OT-123+1"}
- Event 3: N_UNION=2, metadata={"union_id": "OT-123+2"}
```

### Decision D59: Partial Success Pattern for Unavailable Unions

**Context:** process_selection may receive union_ids that are already completed or not available

**Decision:** Filter unavailable unions and process only available ones, log warning

**Rationale:**
- Graceful degradation: process what can be processed
- Avoids failing entire batch for partial unavailability
- Logs warning for audit trail and debugging
- Returns actual processed count (may differ from requested count)

**Trade-offs:**
- Pro: Resilient to race conditions and stale data
- Pro: User sees progress even if some unions unavailable
- Con: Silent failure for unavailable unions (mitigated by warning logs)

---

## What Was Built

### UnionService Class (backend/services/union_service.py)

**Core Methods:**

1. **process_selection(tag_spool, union_ids, worker_id, worker_nombre, operacion)**
   - Validates union IDs exist and belong to same OT
   - Filters available unions (ARM: arm_fecha_fin=None, SOLD: ARM complete + sol_fecha_fin=None)
   - Calls batch_update_arm or batch_update_sold from UnionRepository
   - Calculates pulgadas sum
   - Builds and logs metadata events (batch + granular)
   - Returns summary: {union_count, action, pulgadas, event_count}

2. **calcular_pulgadas(unions)**
   - Sums DN_UNION values from list of Union objects
   - Handles None and invalid values gracefully
   - Returns float with 1 decimal precision (e.g., 10.5)

3. **build_eventos_metadata(tag_spool, worker_id, worker_nombre, operacion, union_ids, pulgadas)**
   - Creates 1 batch event at spool level (N_UNION=None)
   - Creates N granular events per union (N_UNION=union_number)
   - Supports UNION_ARM_REGISTRADA and UNION_SOLD_REGISTRADA event types
   - Extracts n_union from union_id format (OT-123+5 → n_union=5)
   - Returns list of MetadataEvent objects ready for batch_log_events

**Helper Methods:**

4. **validate_union_ownership(unions)** - Checks all unions belong to same OT
5. **filter_available_unions(unions, operacion)** - Filters by ARM/SOLD availability and type
6. **get_sold_required_types()** - Returns ['BW', 'BR', 'SO', 'FILL', 'LET'] constant

**Architecture:**
- Dependency injection (UnionRepository, MetadataRepository, SheetsRepository)
- Business logic bridge between API layer and data layer
- Orchestrates multi-step workflows: validate → batch update → calculate → log events

---

## Files Changed

### Created
- `backend/services/union_service.py` - UnionService class with 6 methods (216 lines)
- `tests/unit/services/test_union_service.py` - Comprehensive unit tests (607 lines, 26 tests)

### Modified
- `backend/services/__init__.py` - Export UnionService in __all__ list

**Total:** 1 new service, 26 passing tests, 100% coverage

---

## Test Coverage

### Unit Tests (26 tests, all passing)

**TestCalcularPulgadas (6 tests):**
- Sum with valid unions (4.0 + 6.5 = 10.5)
- Empty union list returns 0.0
- Single union
- Decimal precision rounding (10.690 → 10.7)
- Handle None DN_UNION values gracefully
- Handle invalid DN_UNION values gracefully

**TestBuildEventosMetadata (4 tests):**
- Build ARM events (1 batch + N granular)
- Build SOLD events (1 batch + N granular)
- Event structure validation (all required fields)
- Invalid union_id format handling (skip invalid, log warning)

**TestValidateUnionOwnership (4 tests):**
- Same OT returns True
- Different OTs returns False
- Empty list returns True
- Single union returns True

**TestFilterAvailableUnions (4 tests):**
- ARM filter (arm_fecha_fin=None)
- SOLD filter (ARM complete + sol_fecha_fin=None)
- FW union excluded from SOLD (tipo_union not in SOLD_REQUIRED_TYPES)
- Empty list returns []

**TestGetSoldRequiredTypes (2 tests):**
- Returns correct types ['BW', 'BR', 'SO', 'FILL', 'LET']
- Returns copy to prevent modification

**TestProcessSelection (6 tests):**
- Successful ARM processing (mock batch_update_arm)
- Successful SOLD processing (mock batch_update_sold)
- Empty union_ids raises ValueError
- Union IDs not found raises ValueError
- Mixed OT ownership raises ValueError
- Filters unavailable unions (partial success pattern)

**Coverage:** 100% of UnionService methods covered

---

## Integration Points

### Upstream Dependencies
- **UnionRepository** (Phase 8): batch_update_arm, batch_update_sold, get_by_spool
- **MetadataRepository** (Phase 8): batch_log_events with auto-chunking
- **SheetsRepository** (Phase 1): Google Sheets access (injected but not directly used)
- **Union model** (Phase 7): 18-field immutable model with OT foreign key
- **MetadataEvent model** (Phase 8): Support for n_union field (column K)

### Downstream Dependencies
- **OccupationServiceV4** (Phase 10-02): Uses UnionService for FINALIZAR workflow
- **INICIAR/FINALIZAR routers** (Phase 10-03): Injects UnionService at FastAPI startup
- **Frontend union selection** (Phase 11): Calls /api/finalizar with union_ids list

---

## Deviations from Plan

**None** - Plan executed exactly as written.

All 6 tasks completed:
1. ✓ UnionService class with dependency injection
2. ✓ process_selection method with batch orchestration
3. ✓ calcular_pulgadas with 1 decimal precision
4. ✓ build_eventos_metadata with batch + granular events
5. ✓ Helper methods for validation and filtering
6. ✓ Comprehensive unit tests with mocked dependencies

---

## Performance Characteristics

**Batch Operations:**
- Delegates to UnionRepository batch methods (< 1s for 10 unions per Phase 8)
- Single call to batch_log_events (auto-chunked at 900 rows)
- No N+1 queries - fetches all unions once via get_by_spool

**Pulgadas Calculation:**
- O(N) complexity where N = number of unions
- Graceful degradation for invalid values (continue processing)

**Event Building:**
- O(N) complexity where N = number of unions
- Creates N+1 events (1 batch + N granular)
- Minimal memory overhead (events built in list, logged in batch)

**Validation:**
- validate_union_ownership: O(N) single pass
- filter_available_unions: O(N) single pass
- Total: O(N) not O(N²)

---

## Next Phase Readiness

**Phase 10-02 (OccupationServiceV4) ready to proceed:**
- ✓ UnionService available for injection
- ✓ process_selection tested with ARM/SOLD operations
- ✓ Batch + granular metadata events working
- ✓ FW union exclusion implemented

**Blockers for Phase 11 (Frontend Union Selection):**
- None - service layer complete
- Frontend will call POST /api/finalizar with union_ids
- Expects response: {union_count, action, pulgadas, event_count}

**Remaining Phase 10 Work:**
- 10-02: OccupationServiceV4 with iniciar_spool and finalizar_spool
- 10-03: INICIAR/FINALIZAR routers with dependency injection
- 10-04: Auto-determination logic (PAUSAR vs COMPLETAR)
- 10-05: Integration tests with real infrastructure

---

## Commits

```
4ecd31d feat(10-01): create UnionService class with dependency injection
4af3739 feat(10-01): implement process_selection method
51eb307 feat(10-01): implement calcular_pulgadas method
c5d549d feat(10-01): implement build_eventos_metadata method
c5fae50 feat(10-01): add helper methods for union validation and filtering
29e1b93 feat(10-01): export UnionService from services module
365bdf9 test(10-01): add comprehensive unit tests for UnionService
```

**Duration:** 5 minutes (start: 1770049684, end: 1770049981)
**Commits:** 7 atomic commits
**Files:** 2 created, 1 modified
**Tests:** 26 passing unit tests

---

## Success Criteria

✅ **All must-haves delivered:**
- UnionService class with dependency injection
- process_selection orchestrates batch operations
- calcular_pulgadas sums with 1 decimal precision
- build_eventos_metadata creates batch + granular events
- SOLD_REQUIRED_TYPES constant = ['BW', 'BR', 'SO', 'FILL', 'LET']
- Comprehensive unit tests with mocked dependencies

✅ **Verification passed:**
- UnionService correctly orchestrates batch updates
- Pulgadas calculation uses 1 decimal precision (round(total, 1))
- Metadata events include both batch (N_UNION=None) and granular (N_UNION=1..N) entries
- SOLD_REQUIRED_TYPES constant excludes FW unions
- All 26 tests pass with 100% coverage of new service
- No integration with real infrastructure (all dependencies mocked)

---

**Status:** Complete and verified ✓
