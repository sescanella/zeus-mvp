---
phase: 11
plan: 02
subsystem: api
tags: [union-queries, disponibles, metricas, pydantic, fastapi, v4.0]
requires: [11-01, 08-01, 08-02, 08-03]
provides: [union-api-models, disponibles-endpoint, metricas-endpoint]
affects: [11-03, 11-04, 12-01]
tech-stack:
  added: []
  patterns: [response-models, query-endpoints, dependency-injection]
key-files:
  created:
    - backend/models/union_api.py
    - backend/routers/union_router.py
    - tests/unit/routers/test_union_router.py
  modified:
    - backend/core/dependency.py
    - backend/main.py
decisions: []
metrics:
  duration: 2.9 min
  completed: 2026-02-02
---

# Phase 11 Plan 02: Union Query Endpoints Summary

**One-liner:** Read-only union query endpoints for disponibles filtering (ARM/SOLD) and 5-field spool metrics with 2-decimal pulgadas precision

## What Was Built

### API Response Models (`backend/models/union_api.py`)

Created three Pydantic models separating API contract from internal Union domain model:

1. **UnionSummary** - Lightweight 4-field model for union selection UI
   - `id`, `n_union`, `dn_union`, `tipo_union`
   - No timestamps, no audit fields (optimized for frontend consumption)

2. **DisponiblesResponse** - Wrapper for disponibles query results
   - `tag_spool`, `operacion`, `unions` (list), `count`
   - Convenience count field for quick UI display ("5 unions available")

3. **MetricasResponse** - Spool-level metrics per CONTEXT.md specification
   - Exactly 5 fields: `total_uniones`, `arm_completadas`, `sold_completadas`, `pulgadas_arm`, `pulgadas_sold`
   - 2-decimal precision enforced for pulgadas values (18.50, not 18.5)

### Union Router (`backend/routers/union_router.py`)

Implemented two read-only query endpoints:

#### `GET /api/v4/uniones/{tag}/disponibles?operacion=ARM|SOLD`

- **ARM disponibles**: Returns unions where `ARM_FECHA_FIN IS NULL`
- **SOLD disponibles**: Returns unions where `ARM_FECHA_FIN IS NOT NULL AND SOL_FECHA_FIN IS NULL`
- OT-based queries via `get_disponibles_arm_by_ot()` / `get_disponibles_sold_by_ot()`
- Returns 4-field UnionSummary objects (minimal payload)
- Error handling: 404 (spool not found), 422 (invalid operacion), 500 (Sheets error)

#### `GET /api/v4/uniones/{tag}/metricas`

- Always-fresh calculation from Uniones sheet (no caching per D33)
- Uses `calculate_metrics()` bulk method for efficiency (single query, all metrics)
- Returns exactly 5 fields per CONTEXT.md specification
- 2-decimal precision for pulgadas maintained from repository layer
- Error handling: 404 (spool not found, no unions), 500 (Sheets error)

### Dependency Injection

Added `get_union_repository()` factory to `backend/core/dependency.py`:
- Returns new UnionRepository instance per request
- Injects SheetsRepository dependency
- Documented as v4.0 Phase 8 integration

### Router Registration

Registered `union_router` in `backend/main.py`:
- Prefix: `/api/v4` (v4.0 versioned endpoints)
- Tag: `v4-unions` (OpenAPI grouping)
- Endpoints accessible at `/api/v4/uniones/{tag}/*`

### Comprehensive Tests

Created 12 unit tests in `tests/unit/routers/test_union_router.py`:

**Disponibles Tests (6):**
- `test_disponibles_arm_returns_incomplete` - ARM filtering validation
- `test_disponibles_sold_requires_arm_complete` - SOLD filtering validation
- `test_disponibles_empty_list_when_none_available` - Empty response handling
- `test_disponibles_404_spool_not_found` - 404 for missing spools
- `test_disponibles_400_invalid_operacion` - 422 validation for invalid operacion
- `test_disponibles_500_sheets_connection_error` - 500 on Sheets failure

**Metricas Tests (6):**
- `test_metricas_returns_five_fields` - 5-field response validation
- `test_metricas_2_decimal_precision` - 2-decimal pulgadas validation (18.50 not 18.5)
- `test_metricas_404_spool_not_found` - 404 for missing spools
- `test_metricas_404_no_unions` - 404 when spool has no unions
- `test_metricas_500_sheets_connection_error` - 500 on Sheets failure
- `test_metricas_zero_pulgadas_when_no_completions` - 0.00 baseline handling

All 12 tests passing with mocked dependencies.

## Technical Implementation

### Query Flow

**Disponibles endpoint:**
```
Client → GET /api/v4/uniones/{tag}/disponibles?operacion=ARM
  ↓
union_router.get_disponibles()
  ↓
sheets_repo.get_spool_by_tag(tag) → Extract OT
  ↓
union_repo.get_disponibles_arm_by_ot(ot)
  ↓
Filter unions where arm_fecha_fin IS NULL
  ↓
Build DisponiblesResponse with UnionSummary objects
  ↓
Return JSON response
```

**Metricas endpoint:**
```
Client → GET /api/v4/uniones/{tag}/metricas
  ↓
union_router.get_metricas()
  ↓
sheets_repo.get_spool_by_tag(tag) → Extract OT
  ↓
union_repo.calculate_metrics(ot)
  ↓
Single-pass calculation: counts + pulgadas sums (2 decimals)
  ↓
Build MetricasResponse with 5 fields
  ↓
Return JSON response
```

### Design Decisions

1. **Separate API models from domain models** - UnionSummary provides minimal 4-field view while internal Union model has 18 fields
2. **OT-based queries** - Uses `get_disponibles_arm_by_ot(ot)` for v4.0 architecture consistency
3. **No caching** - Always-fresh metrics calculation per Decision D33
4. **Bulk metrics method** - `calculate_metrics()` fetches unions once and calculates all 5 metrics in single pass
5. **Strict error handling** - Distinct 404 (not found), 422 (validation), 500 (Sheets error) codes
6. **2-decimal precision** - Enforced at repository layer, maintained through API response

## Deviations from Plan

None - plan executed exactly as written.

## Commits

1. **59ab9bf** - `feat(11-02): add union API response models`
   - Created UnionSummary, DisponiblesResponse, MetricasResponse
   - Separated API contract from domain model

2. **9322bf9** - `feat(11-02): add union query endpoints router`
   - GET /uniones/{tag}/disponibles?operacion=ARM|SOLD
   - GET /uniones/{tag}/metricas
   - Added get_union_repository dependency injection
   - OT-based queries with error handling

3. **ab171a8** - `feat(11-02): register union router in main.py`
   - Import union_router
   - Include with /api/v4 prefix
   - Add v4-unions tag

4. **ae4016e** - `test(11-02): add comprehensive union router tests`
   - 12 unit tests (6 disponibles, 6 metricas)
   - All tests passing with mocked dependencies

## Dependencies

**Requires:**
- **11-01**: API versioning structure (v4.0 endpoints at /api/v4/)
- **08-01**: UnionRepository query methods (`get_disponibles_arm_by_ot`, `get_disponibles_sold_by_ot`)
- **08-02**: OT-based architecture (foreign key for union queries)
- **08-03**: Metrics calculation (`calculate_metrics` bulk method, 2-decimal precision)

**Provides:**
- Union API response models (UnionSummary, DisponiblesResponse, MetricasResponse)
- Disponibles endpoint for ARM/SOLD union filtering
- Metricas endpoint for spool-level performance data

**Affects:**
- **11-03**: Metrics API can use MetricasResponse structure
- **11-04**: Union listing uses same response models
- **12-01**: Frontend union selection will consume disponibles endpoint

## Requirements Met

- ✅ **API-01**: GET disponibles?operacion=ARM returns unions where ARM_FECHA_FIN IS NULL
- ✅ **API-02**: GET disponibles?operacion=SOLD returns unions where ARM_FECHA_FIN IS NOT NULL AND SOL_FECHA_FIN IS NULL
- ✅ **API-03**: GET metricas returns {total_uniones, arm_completadas, sold_completadas, pulgadas_arm, pulgadas_sold}
- ✅ **METRIC-01**: Pulgadas-diámetro in metrics response (foundation for dashboard display)
- ✅ **METRIC-02**: Performance calculation support (pulgadas data available)

## Testing Coverage

- 12 unit tests covering both endpoints
- ARM disponibles filtering validation
- SOLD disponibles filtering validation (ARM prerequisite)
- 2-decimal precision validation for pulgadas
- Error handling: 404, 422, 500
- Empty list handling
- Zero pulgadas baseline handling

All tests passing with mocked UnionRepository and SheetsRepository.

## Next Phase Readiness

**Ready for Phase 11 Plan 03 (Metrics API):**
- MetricasResponse structure can be reused
- 2-decimal precision established
- Error handling patterns defined

**Ready for Phase 12 Plan 01 (Frontend Union Selection):**
- Disponibles endpoint provides union list for ARM/SOLD operations
- UnionSummary has minimal 4 fields needed for UI
- Count field enables quick "X unions available" display

**No blockers.**

## Performance Notes

- Disponibles queries use OT-based filtering (efficient single foreign key lookup)
- Metricas uses `calculate_metrics()` bulk method (single Sheets read, single-pass aggregation)
- No caching overhead (always-fresh data per D33)
- Response models minimal (4-6 fields, no heavy audit data)

## Documentation

- Router endpoints documented with docstrings
- OpenAPI schema generated via Pydantic models
- Error responses documented with status codes
- Test cases document expected behavior

---

**Duration:** 2.9 minutes
**Completed:** 2026-02-02
**Status:** ✅ Complete - All tasks executed, 12 tests passing, no deviations
