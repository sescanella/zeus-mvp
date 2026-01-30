# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-01-30)

**Core value:** Track work at the union level with the correct business metric (pulgadas-diámetro)
**Current focus:** Phase 7 - Data Model Foundation

## Current Position

Phase: 7 of 13 (Data Model Foundation)
Plan: 3 of TBD in current phase
Status: In progress
Last activity: 2026-01-30 — Completed 07-03-PLAN.md (Union model & repository)

Progress: [██████░░░░░░░░] 46% (6 of 13 phases complete from v3.0, Phase 7 in progress)

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
| 7. Data Model Foundation | 3 | 7 min | 2.3 min |

**Recent Trend:**
- Last 5 plans: [5.6, 5.4, 1.0, 2.0, 4.0] min
- Trend: v4.0 Phase 7 progressing (Union model & repository complete)

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

### Pending Todos

None yet.

### Blockers/Concerns

**v4.0 Pre-Deployment:**
- Uniones sheet must be pre-populated by Engineering external process before v4.0 can deploy (currently 13/18 columns present)
- v3.0 7-day rollback window expires 2026-02-02 (v2.1 backup will be archived)
- Schema migration scripts (07-01, 07-02) verified in dry-run only - execute during startup validation (07-04)

**v3.0 Technical Debt:**
- Phase 4 missing formal VERIFICATION.md (code verified via integration checker)
- Frontend metrología/reparación integration unverified (backend complete, UI may be missing)
- No dedicated reparación router (endpoints in actions.py instead of separate router)
- No E2E SSE test with real infrastructure (verified at code level only)

## Session Continuity

Last session: 2026-01-30
Stopped at: Completed 07-03-PLAN.md (Union model & UnionRepository with 15 passing unit tests, 4 min duration)
Resume file: None
