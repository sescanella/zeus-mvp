# Phase 7 Gap Closure Plans

## Context

Phase 7 verification (2026-02-02) found that while all code artifacts were complete and tested, the actual Google Sheets schemas were not updated. This gap-closure phase addresses the 3 critical schema gaps.

## Gaps Identified

1. **Operaciones Schema Gap**: Sheet has 67 columns, needs 72 (missing metrics columns)
2. **Metadata Schema Gap**: Sheet has 10 columns, needs 11 (missing N_UNION column)
3. **Uniones Schema Gap**: Sheet has 13 columns, needs 18 (Engineering dependency)

## Plans Created

### Wave 1 (Parallel Execution)
- **07-06**: Execute Operaciones schema migration (add columns 68-72)
- **07-07**: Execute Metadata schema migration (add column 11)

### Wave 2 (After Wave 1)
- **07-08**: Validate all schemas and handle Uniones gap

## Critical Path

1. **Immediate Actions** (Wave 1):
   - Run `extend_operaciones_schema.py` to add metrics columns
   - Run `extend_metadata_schema.py` to add N_UNION column
   - Both can execute in parallel (different sheets)

2. **Validation** (Wave 2):
   - Run comprehensive validation after migrations
   - Document Uniones requirements for Engineering
   - Adjust FastAPI startup to handle incomplete Uniones gracefully

3. **External Dependency**:
   - Engineering must complete Uniones sheet population
   - System will fail-fast until Uniones has all 18 columns
   - This is intentional - prevents v4.0 deployment with incomplete data

## Success Criteria

After gap closure:
1. Operaciones has 72 columns with union metrics
2. Metadata has 11 columns with N_UNION support
3. Uniones validation clearly identifies what Engineering needs to provide
4. FastAPI startup validation prevents deployment with incomplete schemas

## Time Estimate

- Wave 1: ~5 minutes (2 parallel migrations)
- Wave 2: ~5 minutes (validation and documentation)
- Total: ~10 minutes of execution time

Engineering dependency for Uniones is external and timeline unknown.