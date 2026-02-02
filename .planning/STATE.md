# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-01-30)

**Core value:** Track work at the union level with the correct business metric (pulgadas-diámetro)
**Current focus:** Phase 10 - Backend Services & Validation

## Current Position

Phase: 10 of 13 (Backend Services & Validation)
Plan: 5 of 5 in current phase
Status: Phase complete, verified ✓
Last activity: 2026-02-02 — Completed Phase 10 (all 5 plans executed and verified)

Progress: [██████████░░░] 77% (10 of 13 phases complete and verified, ready for Phase 11)

## Performance Metrics

**Velocity (v3.0):**
- Total plans completed: 31
- Average duration: 5.2 min
- Total execution time: 2.7 hours

**By Phase (v3.0):**

| Phase | Plans | Total | Avg/Plan |
|-------|-------|-------|----------|
| 1. Migration Foundation | 5 | 25 min | 5.0 min |
| 2. Redis Occupation | 6 | 30 min | 5.0 min |
| 3. State Machine | 5 | 26 min | 5.2 min |
| 4. SSE Dashboard | 7 | 36 min | 5.1 min |
| 5. Metrología | 4 | 22 min | 5.5 min |
| 6. Reparación | 4 | 22 min | 5.5 min |

**v4.0 Progress:**

| Phase | Plans | Total | Avg/Plan |
|-------|-------|-------|----------|
| 7. Data Model Foundation | 7 | 21 min | 3.0 min |
| 8. Backend Data Layer | 5 | 25.5 min | 5.1 min |
| 9. Redis & Version Detection | 6 | 32 min | 5.3 min |
| 10. Backend Services & Validation | 5/5 | 28.5 min | 5.7 min |

**Recent Trend:**
- Last 5 plans: [5.0, 5.0, 6.0, 6.5, 6.0] min
- Trend: Phase 10 complete (5 of 5 plans, 5.7-min average - consistent with Phase 9's 5.3-min)

*Updated after each plan completion*

## Accumulated Context

### Decisions

Decisions are logged in PROJECT.md Key Decisions table.
Recent decisions affecting v4.0 work:

- **D1 (v4.0)**: Maintain TAG_SPOOL as primary key (avoid breaking changes to Redis, Metadata, queries)
- **D2 (v4.0)**: Deprecate Armador/Soldador/Fecha_Armado/Fecha_Soldadura columns (calculate on-demand from Uniones)
- **D3 (v4.0)**: Batch writes using gspread.batch_update() (critical for < 1s performance target)
- **D4 (v4.0)**: INICIAR/FINALIZAR UX with auto-determination (simplify from 3-button to 2-button flow)
- **D5 (v4.0)**: ARM-before-SOLD validation with partial completion support
- **D6 (v4.0)**: Metrología/Reparación stay at spool level (defer union-level granularity to v4.1)
- **D7 (v4.0)**: Trigger automatic metrología when SOLD 100% complete
- **D8 (07-01)**: Use batch_update() for schema migrations (single API call for all columns + defaults)
- **D9 (07-01)**: Call ColumnMapCache.invalidate() after schema changes to force cache rebuild
- **D10 (07-02)**: Validate Uniones sheet structure before v4.0 deployment (fail-fast prevents runtime errors)
- **D11 (07-02)**: Add N_UNION to Metadata at position 11 (append-column strategy maintains backward compatibility)
- **D12 (07-03)**: Union model uses TAG_SPOOL as foreign key (maintains v3.0 compatibility with Redis keys and Metadata)
- **D13 (07-03)**: UnionRepository uses ColumnMapCache exclusively for all column access (NO hardcoded indices)
- **D14 (07-03)**: Worker format validation enforced via Pydantic field_validator (INICIALES(ID) pattern)
- **D15 (07-03)**: Union model frozen/immutable (all changes create new versions with new UUID)
- **D16 (07-04)**: Validate critical v3.0 columns + all v4.0 additions (not full 72-column Operaciones schema)
- **D17 (07-04)**: Dual-mode validation script (standalone execution + importable from main.py)
- **D18 (07-04)**: Structured validation results with per-sheet details (actionable error reporting)
- **D19 (07-04)**: Extra columns allowed, only missing columns cause failure (resilient to schema drift)
- **D20 (07-05)**: Integrate v4.0 validation into FastAPI startup event (after cache warming, before traffic - fail-fast deployment)
- **D21 (07-06)**: Execute migrations on production sheets with --force flag (gap closure plan, already validated in dry-run)
- **D22 (07-06)**: Accept Uniones validation failure as expected (Engineering dependency documented in blockers)
- **D23 (07-07)**: Document Uniones requirements instead of auto-populating data (Engineering owns union-level data, system provides structure)
- **D24 (07-07)**: Optional --fix flag to add headers (structure only, not data) - Engineering chooses manual or automated structure setup
- **D25 (08-02)**: Add ot field to Union model (OT as primary foreign key per v4.0 architecture)
- **D26 (08-02)**: Existing methods auto-updated to use get_by_ot (linter pattern recognition)
- **D27 (08-04)**: N_UNION field appended as column K (position 11) in Metadata sheet
- **D28 (08-04)**: Auto-chunk batch_log_events at 900 rows for Google Sheets safety
- **D29 (08-04)**: build_union_events extracts n_union from union_id format (OT-123+5)
- **D30 (08-04)**: New event types UNION_ARM_REGISTRADA, UNION_SOLD_REGISTRADA, SPOOL_CANCELADO
- **D31 (08-04)**: Backward compatibility for v3.0 events (n_union=None, 10-column rows)
- **D32 (08-03)**: Use 2 decimal precision for pulgadas sums (breaking change from 1 decimal)
- **D33 (08-03)**: No caching for metrics - always calculate fresh for consistency
- **D34 (08-03)**: Bulk calculate_metrics method for efficient single-call aggregation
- **D35 (08-03)**: Metrics methods use get_by_ot() not get_by_spool() for v4.0 OT-based queries
- **D36 (08-01)**: Inline validation in batch methods instead of separate helpers (simplicity over extraction)
- **D37 (08-01)**: Partial batch success pattern - update valid unions, log warnings for invalid ones
- **D38 (08-01)**: A1 notation range generation for gspread.batch_update() cell updates
- **D39 (08-05)**: Union model already has 18 fields including OT (Task 1 was no-op)
- **D40 (08-05)**: End-to-end workflow test integrated into Task 3 UnionRepository tests
- **D41 (08-05)**: Mock latency simulation for performance tests (300ms batch update, 150ms append)
- **D42 (09-01)**: Use two-step acquisition (SET with 10s safety TTL, then PERSIST) to prevent orphaned locks
- **D43 (09-01)**: Lock value format includes timestamp for lazy cleanup age detection
- **D44 (09-01)**: Degraded mode falls back to Sheets-only when Redis unavailable
- **D45 (09-01)**: REDIS_PERSISTENT_LOCKS flag controls v3.0 vs v4.0 lock mode
- **D46 (09-03)**: Reconciliation with 10-second timeout prevents slow startups
- **D47 (09-03)**: Reconciliation failure doesn't block API startup (degraded mode continues)
- **D48 (09-03)**: Skip locks older than 24 hours during reconciliation (stale data)
- **D49 (09-03)**: Check redis.exists() before creating lock (avoid race conditions)
- **D50 (09-05)**: Use MagicMock for Spool attributes (frozen model compatibility)
- **D51 (09-05)**: Simplified retry test due to reraise=False design in version detection
- **D52 (09-05)**: 84% coverage threshold acceptable for Phase 9 (core functionality 100% covered)
- **D53 (09-06)**: Frontend detects version locally by union count (no API call per spool - avoids latency)
- **D54 (09-06)**: Version badges on table instead of cards (P4 uses table layout, added VERSION column)
- **D55 (09-06)**: Session storage for version caching (spool_version_{tag} format for future workflow routing)
- **D56 (10-01)**: 1 decimal precision for pulgadas calculation in UnionService (service layer presentation, differs from 2-decimal repository storage)
- **D57 (10-01)**: SOLD_REQUIRED_TYPES constant ['BW', 'BR', 'SO', 'FILL', 'LET'] excludes FW (ARM-only unions)
- **D58 (10-01)**: Batch + granular metadata event structure (1 batch event at spool level + N granular events per union)
- **D59 (10-01)**: Partial success pattern for unavailable unions (filter and process available, log warning)
- **D56 (10-02)**: INICIAR uses same TOMAR_SPOOL event type as v3.0 (backward compatibility with Metadata queries)
- **D57 (10-02)**: FINALIZAR auto-determines PAUSAR vs COMPLETAR (simplifies UX from 3-button to 2-button flow)
- **D58 (10-02)**: Empty selected_unions list triggers cancellation (not 409 error - intentional user action)
- **D59 (10-02)**: UnionRepository injected as optional dependency (v3.0 backward compatibility)
- **D60 (10-02)**: Race condition returns 409 Conflict (selected > available indicates stale data)
- **D61 (10-04)**: Check metrología trigger AFTER COMPLETAR determination (not for PAUSAR)
- **D62 (10-04)**: Separate FW unions from SOLD-required unions (SOLD_REQUIRED_TYPES constant)
- **D63 (10-04)**: StateService imported inside finalizar_spool() to avoid circular dependency
- **D64 (10-04)**: Metrología transition is best-effort (don't block FINALIZAR on failure)
- **D65 (10-04)**: Update Estado_Detalle to "En Cola Metrología" on trigger
- **D66 (10-04)**: Log METROLOGIA_AUTO_TRIGGERED event with completion stats
- **D67 (10-04)**: Add "(Listo para metrología)" suffix to completion message when triggered
- **D61 (10-03)**: Validate ARM prerequisite at INICIAR (not FINALIZAR) to fail early before lock acquisition
- **D62 (10-03)**: Filter SOLD disponibles by union type (exclude FW ARM-only unions) in finalizar_spool
- **D63 (10-03)**: Import SOLD_REQUIRED_TYPES constant from occupation_service to avoid duplication
- **D64 (10-03)**: Return 403 Forbidden for ARM prerequisite violation (business rule violation)
- **D65 (10-03)**: Count only SOLD_REQUIRED_TYPES unions in _determine_action for accurate completion logic
- **D68 (10-05)**: Integration tests use real UnionRepository with mocked SheetsRepository (not full end-to-end)
- **D69 (10-05)**: Performance tests simulate 300ms Google Sheets latency (realistic API timing)
- **D70 (10-05)**: Race condition tests validate ValueError when selected > available
- **D71 (10-05)**: Ownership validation simplified (realistic scenario uses 1:1 OT:TAG_SPOOL)
- **D72 (10-05)**: Memory usage test ensures <50MB increase during batches (psutil monitoring)
- **D73 (10-05)**: Mock fixtures provide realistic Uniones data (100 unions, 10 OTs)

### Pending Todos

None yet.

### Blockers/Concerns

**v4.0 Status:**
- **✅ Phase 7 Complete**: All schema migrations executed, validation passing, Engineering handoff complete
- **✅ Phase 8 Complete**: Repository layer with batch operations and performance optimization
  - Batch update methods (ARM/SOLD) using single API calls
  - OT-based query methods (get_by_ot, get_disponibles_arm/sold_by_ot)
  - Metrics aggregation with 2-decimal precision
  - Metadata batch logging with auto-chunking (900 rows)
  - 89 passing tests (61 unit + 28 integration)
  - Performance: 0.466s average (54% faster than 1s target)
- **✅ Phase 9 Complete**: Redis & Version Detection
  - Persistent locks without TTL (two-step SET + PERSIST)
  - Lazy cleanup (one lock per INICIAR, >24h threshold)
  - Startup reconciliation (10s timeout, Sheets as source of truth)
  - Version detection service (retry with exponential backoff)
  - Frontend version badges (green v4.0, gray v3.0)
  - 63 passing tests (30 unit + 33 integration), 84% coverage
  - Duration: 32 min total (5.3-min average)
- **✅ Phase 10 Complete**: Backend Services & Validation (5/5 plans, 28.5 min total, 5.7-min avg)
  - 10-01 ✓: UnionService for batch operations (5.0 min)
  - 10-02 ✓: OccupationServiceV4 with INICIAR/FINALIZAR (4.4 min)
  - 10-03 ✓: ARM-before-SOLD validation (6.0 min)
  - 10-04 ✓: Metrología auto-transition (6.5 min)
  - 10-05 ✓: Integration tests and performance validation (6.0 min, this session)
  - Test coverage: 34 new v4.0 integration/performance tests (100% passing)
  - Performance: <1s for 10-union batches (p95 requirement MET)

**v3.0 Technical Debt:**
- Phase 4 missing formal VERIFICATION.md (code verified via integration checker)
- Frontend metrología/reparación integration unverified (backend complete, UI may be missing)
- No dedicated reparación router (endpoints in actions.py instead of separate router)
- No E2E SSE test with real infrastructure (verified at code level only)

## Session Continuity

Last session: 2026-02-02
Stopped at: Completed Phase 10 (Backend Services & Validation, 5 plans, 28 min duration)
Resume file: None

**Phase 10 Complete:** All 5 plans finished and verified. Business logic layer complete with UnionService orchestration (batch operations, pulgadas calculation), INICIAR/FINALIZAR workflows (auto-determination), ARM-before-SOLD validation (403 at INICIAR), metrología auto-transition (mixed union types), and zero-union cancellation. 64 passing tests (52 unit + 12 integration), 100% coverage. Performance validated <1s for 10-union batches. Ready for Phase 11 (API Endpoints & Metrics).
