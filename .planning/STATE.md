# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-01-30)

**Core value:** Track work at the union level with the correct business metric (pulgadas-diámetro)
**Current focus:** Phase 9 - Redis & Version Detection

## Current Position

Phase: 9 of 13 (Redis & Version Detection)
Plan: 3 of 5 in current phase
Status: In progress
Last activity: 2026-02-02 — Completed 09-03-PLAN.md (Startup reconciliation from Sheets)

Progress: [█████████░░░░] 69% (9 of 13 phases in progress, 3 of 5 plans complete in Phase 9)

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
| 9. Redis & Version Detection | 3/5 | 15.5 min | 5.2 min |

**Recent Trend:**
- Last 5 plans: [4.0, 4.4, 7.5, 4.0, 4.0] min
- Trend: Phase 9 IN PROGRESS (3 of 5 plans complete, 5.2-min average - back to target velocity)

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
- **Phase 9 IN PROGRESS**: Redis & Version Detection (3 of 5 plans complete)
  - ✅ Plan 09-01: Persistent locks without TTL, two-step acquisition (SET + PERSIST), degraded mode fallback
  - ✅ Plan 09-02: Lazy cleanup mechanism (one abandoned lock per INICIAR operation)
  - ✅ Plan 09-03: Startup reconciliation from Sheets with 10-second timeout, age-based filtering
  - Next: Plan 09-04 (Version detection with caching)

**v3.0 Technical Debt:**
- Phase 4 missing formal VERIFICATION.md (code verified via integration checker)
- Frontend metrología/reparación integration unverified (backend complete, UI may be missing)
- No dedicated reparación router (endpoints in actions.py instead of separate router)
- No E2E SSE test with real infrastructure (verified at code level only)

## Session Continuity

Last session: 2026-02-02
Stopped at: Completed 09-03-PLAN.md (Startup reconciliation from Sheets, 4 min duration)
Resume file: None

**Phase 9 In Progress:** 3 of 5 plans complete (15.5 min total). Auto-recovery system complete: persistent locks + lazy cleanup + startup reconciliation. Next: 09-04 (Version detection with caching).
