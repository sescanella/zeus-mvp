# Phase 1: Migration Foundation - Execution Plan

**Phase:** 01-migration-foundation
**Goal:** v2.1 production data migrates to v3.0 schema without breaking existing functionality
**Strategy:** Branch-based migration with one-time cutover (no dual-write complexity)
**Timeline:** 3 waves of parallel execution

## Overview

Phase 1 establishes the foundation for ZEUES v3.0 by safely adding new columns to the Google Sheets schema while preserving full v2.1 functionality. Using a branch-based approach, we build v3.0 in isolation while v2.1 continues running in production untouched.

## Success Criteria

All of these must be TRUE for phase completion:

1. ✓ All 244 v2.1 tests continue passing with new schema columns added
2. ✓ New Operaciones columns (Ocupado_Por, Fecha_Ocupacion, version) visible in Google Sheet
3. ✓ Metadata sheet accepts new event types (TOMAR_SPOOL, PAUSAR_SPOOL) without errors
4. ✓ Production rollback to v2.1-only mode works without data loss
5. ✓ Migration process is fully automated and idempotent

## Execution Waves

### Wave 1: Foundation Scripts (Parallel)
Can execute simultaneously as they don't depend on each other:

- **Plan 01-01:** Backup and Schema Expansion Scripts
  - Create automated backup system for Google Sheets
  - Add 3 new columns (Ocupado_Por, Fecha_Ocupacion, version)
  - Implement idempotent, reversible schema changes

- **Plan 01-02:** Column Mapping Infrastructure
  - Update ColumnMapCache for v3.0 columns
  - Extend Spool model with occupation fields
  - Add backward compatibility wrapper

### Wave 2: Test Infrastructure
Depends on Wave 1 completion:

- **Plan 01-03:** Test Migration and v3.0 Smoke Tests
  - Archive 244 v2.1 tests for reference
  - Create 5-10 focused v3.0 smoke tests
  - Verify backward compatibility

### Wave 3: Orchestration & Verification (Parallel)
Depends on Wave 2 completion:

- **Plan 01-04:** Migration Coordinator and Rollback System
  - Master script orchestrating entire migration
  - Checkpoint-based recovery system
  - Automated rollback capability

- **Plan 01-05:** End-to-End Migration Verification Suite
  - Comprehensive E2E test suite
  - Dual-write verification tests
  - CI/CD pipeline integration

## Key Deliverables

1. **Migration Scripts** (backend/scripts/)
   - backup_sheet.py - Automated Google Sheets backup
   - add_v3_columns.py - Schema expansion script
   - migration_coordinator.py - Master orchestration
   - rollback_migration.py - Emergency recovery

2. **Updated Models** (backend/models/)
   - Spool model with ocupado_por, fecha_ocupacion, version
   - New EventoTipo enum values (TOMAR_SPOOL, PAUSAR_SPOOL)
   - EstadoOcupacion enum (DISPONIBLE, OCUPADO)

3. **Test Suites** (tests/v3.0/)
   - 5+ smoke tests for core migration validation
   - E2E tests for full migration flow
   - Rollback scenario tests

4. **Infrastructure**
   - ColumnMapCache handling 68 columns
   - Backward compatibility mode toggle
   - CI pipeline for migration testing

## Risk Mitigation

| Risk | Impact | Mitigation |
|------|--------|------------|
| Production data corruption | Critical | Automatic backup before any changes, tested rollback procedure |
| v2.1 breakage during migration | High | Branch isolation, compatibility mode, smoke tests |
| Column index shifts | Medium | Dynamic column mapping, never hardcode positions |
| Incomplete migration | Medium | Checkpoint system for safe resume |
| API rate limits | Low | Batch operations, exponential backoff |

## Verification Checklist

Before marking Phase 1 complete:

- [ ] Test migration runs successfully on test sheet copy
- [ ] All 5 smoke tests pass
- [ ] Rollback tested and verified to restore v2.1 state
- [ ] Performance acceptable (< 60 seconds for 1000 spools)
- [ ] v2.1 API endpoints continue working
- [ ] Migration is idempotent (safe to run multiple times)
- [ ] Logs and monitoring in place
- [ ] Documentation updated

## Next Phase

Upon successful completion of Phase 1, we proceed to **Phase 2: Core Location Tracking** where we implement the TOMAR/PAUSAR/COMPLETAR operations that leverage the new schema columns.

---

*Generated: 2026-01-26*
*Phase: 01-migration-foundation*
*Plans: 5 total (Wave 1: 2 parallel, Wave 2: 1, Wave 3: 2 parallel)*