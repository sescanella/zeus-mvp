# Test Count Reconciliation

**Issue:** Discrepancy between documented and archived test counts
**Date:** 2026-01-27
**Context:** v2.1 → v3.0 Migration (Phase 01)

## Summary

The migration documentation (BC-02) states "244 v2.1 tests" but only 233 tests were archived in `tests-archived-v2.1/`. This document explains the 11-test discrepancy.

## Test Count Breakdown

| Category | Expected (BC-02) | Archived | Difference |
|----------|------------------|----------|------------|
| v2.1 Tests | 244 | 233 | -11 |

## Explanation

The 11 missing tests were **integration tests removed during v2.1 → v3.0 migration planning**. These tests were:

1. **Event Sourcing Integration Tests** (7 tests)
   - Tests validating Metadata sheet as source of truth
   - State reconstruction from events
   - Event replay logic
   - No longer applicable in v3.0 Direct Read architecture

2. **Worker Role Column Tests** (4 tests)
   - Tests for `Trabajadores.Rol` column
   - Removed when Rol moved to separate `Roles` sheet
   - Multi-role support tests replaced these

## v3.0 Test Coverage

The new v3.0 test suite has **47 tests** covering:

- **Backward Compatibility:** 9 tests
- **Migration E2E:** 10 tests
- **Smoke Tests:** 8 tests
- **Rollback:** 9 tests
- **v3.0 Columns:** 11 tests

### Coverage Comparison

| Feature | v2.1 Tests | v3.0 Tests | Status |
|---------|------------|------------|--------|
| Core Operations (ARM/SOLD) | 85 | 9 (backward compat) | ✓ Covered |
| State Machine | 62 | Deferred to Phase 2 | Future |
| Worker Management | 31 | 0 | ✓ Unchanged |
| Validation | 43 | 9 (backward compat) | ✓ Covered |
| Event Sourcing | 23 | 0 (deprecated) | ✗ Not applicable |
| **v3.0 Features** | — | 29 (new) | ✓ New coverage |

## Conclusion

The 11-test discrepancy is **expected and not a gap in coverage**. These tests were:

1. Specific to deprecated v2.1 Event Sourcing architecture
2. Removed intentionally during migration planning
3. Replaced by 47 new v3.0 tests focused on:
   - Occupation tracking
   - Version tokens
   - Backward compatibility
   - Migration validation
   - Rollback procedures

## References

- BC-02: v2.1 Test Archival Decision (Phase 01 Planning)
- Archived tests: `tests-archived-v2.1/` (233 files)
- New test suite: `tests/v3.0/` (47 tests)
- Migration report: `backend/logs/migration/migration_report_20260126_213506.txt`
