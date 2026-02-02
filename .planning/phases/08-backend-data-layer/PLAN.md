# Phase 8: Backend Data Layer - Execution Plans

**Phase Goal:** Repository layer can read/write union data with batch operations and performance optimization

## Overview

This phase implements the critical data layer for v4.0 union-level tracking. The focus is on batch operations using `gspread.batch_update()` to achieve <1 second performance for 10-union operations, OT-based querying, and Metadata batch logging with auto-chunking.

## Success Criteria

From phase definition:
1. ✅ UnionRepository can fetch disponibles for ARM and SOLD operations
2. ✅ UnionRepository can batch update timestamps using gspread.batch_update() in single API call
3. ✅ UnionRepository can count completed unions and sum pulgadas for metrics
4. ✅ MetadataRepository can log batch events with auto-chunking (900 rows max)
5. ✅ Union Pydantic model validates 18 fields (already complete from Phase 7)

## Execution Waves

### Wave 1: Core Repository Operations (Parallel)
- **08-01-PLAN.md**: Implement batch update methods for ARM and SOLD operations
  - `batch_update_arm()` and `batch_update_sold()` with A1 notation
  - Validation helpers and row lookup
  - Cache invalidation after updates

- **08-02-PLAN.md**: Implement OT-based query methods
  - `get_by_ot()` with OT→TAG_SPOOL lookup
  - `get_disponibles_arm_by_ot()` and `get_disponibles_sold_by_ot()`
  - Operaciones caching for performance

### Wave 2: Metrics and Metadata (Parallel)
- **08-03-PLAN.md**: Implement metrics aggregation methods
  - `count_completed_arm/sold()` with OT parameter
  - `sum_pulgadas_arm/sold()` with 2 decimal precision
  - `calculate_metrics()` for bulk retrieval

- **08-04-PLAN.md**: Extend Metadata with batch logging
  - Add N_UNION field to MetadataEvent model
  - `batch_log_events()` with 900-row auto-chunking
  - New event types for union granularity

### Wave 3: Integration and Validation
- **08-05-PLAN.md**: Integration tests and performance validation
  - Mock data fixture with 100 realistic unions
  - End-to-end workflow tests
  - Performance validation (<1 second for 10 unions)
  - API call optimization verification

## Key Technical Decisions

Based on phase research and context:

1. **Batch Operations**: Use `gspread.batch_update()` with A1 notation for 6-10x performance gain
2. **OT Relationship**: Implement OT→TAG_SPOOL→Uniones lookup (avoid schema changes)
3. **Error Handling**: Skip invalid unions with logging (resilient approach)
4. **Precision**: 2 decimal places for pulgadas sums (e.g., 18.50)
5. **Chunking**: 900-row chunks for Metadata batch append (safe Google Sheets limit)

## Dependencies

- Phase 7 complete ✅ (Union model, schema validation, column extensions)
- Engineering to populate Uniones sheet data (not blocking code, blocking integration tests)

## Risk Mitigation

1. **Engineering Delay**: Use comprehensive mock data for testing
2. **Performance Target**: Proven batch patterns from v3.0, measured in tests
3. **API Limits**: Batch operations + retry decorator handle rate limiting

## Estimated Duration

Total: ~8-10 hours
- Wave 1: 3-4 hours (parallel execution)
- Wave 2: 2-3 hours (parallel execution)
- Wave 3: 3 hours (depends on waves 1-2)

## Files Modified

### Repository Layer
- `backend/repositories/union_repository.py` - Batch updates, OT queries, metrics
- `backend/repositories/metadata_repository.py` - Batch logging with chunking

### Models
- `backend/models/metadata_event.py` - N_UNION field extension

### Tests
- `tests/unit/test_union_repository_batch.py` - Batch update tests
- `tests/unit/test_union_repository_ot.py` - OT query tests
- `tests/unit/test_union_repository_metrics.py` - Metrics tests
- `tests/unit/test_metadata_batch.py` - Metadata batch tests
- `tests/integration/test_union_repository_integration.py` - Workflow tests
- `tests/integration/test_metadata_batch_integration.py` - Chunking tests
- `tests/integration/test_performance_target.py` - <1s validation
- `tests/fixtures/mock_uniones_data.py` - Test data fixture

## Verification Steps

After all plans complete:

1. Run all unit tests for individual components
2. Run integration tests with mock data
3. Verify performance target (<1 second for 10 unions)
4. Confirm batch operations use single API calls
5. Test with actual Uniones data when available

## Next Phase

Phase 9: Redis & Version Detection - Extend Redis locks for long-running sessions and implement v3.0 vs v4.0 spool detection

---

*Phase 8 plans created: 2026-02-02*
*Estimated execution: 8-10 hours*
*Ready for: /gsd:execute-phase 8*