# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-01-30)

**Core value:** Track work at the union level with the correct business metric (pulgadas-diámetro)
**Current focus:** Phase 13 - Performance Validation & Optimization (final phase)

## Current Position

Phase: 13 of 13 (Performance Validation & Optimization)
Plan: 2 of 6 in current phase
Status: In progress
Last activity: 2026-02-02 — Completed 13-02-PLAN.md

Progress: [████████████░] 100% v4.0 implementation (58 of 62 total plans complete)

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
| 10. Backend Services & Validation | 5 | 28.5 min | 5.7 min |
| 11. API Endpoints & Metrics | 6 | 34.9 min | 5.8 min |
| 12. Frontend Union Selection UX | 8 | 28.7 min | 3.6 min |
| 13. Performance Validation & Optimization | 2/6 | 8.4 min | 4.2 min |

**Recent Trend:**
- Last 5 plans: [3.8, 3.4, 4.0, 6.4, 4.4] min (avg: 4.4 min)
- Trend: Phase 13 in progress (2 of 6 plans, 4.2-min average so far)

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
- **D74 (11-01)**: URL versioning with /api/v3/ and /api/v4/ prefixes (explicit versioning prevents breaking changes)
- **D75 (11-01)**: Legacy router at /api/ prefix for backward compatibility during transition
- **D76 (11-01)**: Simple version detection utils in backend/utils/ (complement Phase 9 service for inline checks)
- **D77 (11-03)**: Version detection at router layer not middleware (simple, explicit, helpful error messages)
- **D78 (11-03)**: Reuse existing IniciarRequest model from occupation.py (DRY principle, single source of truth)
- **D79 (11-04)**: Router-level pulgadas calculation (service handles business logic, router adds presentation metrics)
- **D80 (11-04)**: Reuse FinalizarRequest from occupation.py (DRY principle, consistent with INICIAR pattern)
- **D81 (11-04)**: Worker name derivation at router layer (validates worker exists before service call)
- **D82 (11-05)**: Smoke tests verify endpoint routing without infrastructure (fast CI/CD, no Redis/Sheets needed)
- **D83 (11-05)**: Skipped workflow tests documented as pytest test cases (searchable, version-controlled, can be unskipped later)
- **D84 (11-05)**: Manual validation guide provides comprehensive testing (14 scenarios with curl commands)
- **D85 (11-05)**: pytest.ini updated for v4.0 (testpaths=tests, pythonpath=., maintains v3.0 compatibility)
- **D86 (11-06)**: Delegate union processing to UnionService for batch + granular metadata logging
- **D87 (11-06)**: Skip spool-level metadata logging when UnionService handles it (avoid duplicates)
- **D88 (11-06)**: Inject UnionService at router level instead of dependency.py (v4.0 specific)
- **D89 (12-03)**: 1 decimal precision for pulgadas in calculatePulgadas (aligns with service layer presentation, differs from 2-decimal repository storage)
- **D90 (12-03)**: resetV4State preserves worker/operation/spool (partial reset for workflow continuation)
- **D91 (12-03)**: All v4.0 helpers memoized with useCallback (prevents unnecessary re-renders)
- **D92 (12-01)**: Use native fetch() API for v4.0 functions (maintains consistency with v3.0 pattern, no new dependencies)
- **D93 (12-01)**: ESLint disable comments for future-use types (types defined now for Phase 12 UI components, consumed in plans 02-05)
- **D94 (12-02)**: Modal uses createPortal for body-level rendering (proper z-index stacking without parent constraints)
- **D95 (12-02)**: UnionTable shell without selection logic (deferred to Plan 04 for ARM-before-SOLD validation)
- **D96 (12-02)**: Version detection uses total_uniones > 0 (simple frontend-only check, no API latency)
- **D97 (12-02)**: Session storage for version caching (spool_version_{TAG} format, cleared on refresh for data freshness)
- **D98 (12-04)**: Fresh API call on P5 mount (accuracy over speed)
- **D99 (12-04)**: 1 decimal precision for pulgadas calculation (Math.round(total * 10) / 10)
- **D100 (12-04)**: Zero-selection modal with disabled backdrop click (onBackdropClick={null})
- **D101 (12-04)**: 56x56px checkbox touch targets (w-14 h-14 Tailwind classes)
- **D102 (12-04)**: "Seleccionar Todas" only selects available unions (completed unions excluded)
- **D103 (12-05)**: Fresh API call on P5 mount for accuracy over speed
- **D104 (12-05)**: Session storage preserves selection on error (unions_selection_{tag} format)
- **D105 (12-05)**: 409 conflict triggers 2-second auto-reload to P5
- **D106 (12-05)**: 403 ownership error shows clear message and redirects to spool selection
- **D107 (12-05)**: Clear session storage on successful FINALIZAR submission
- **D108 (12-05)**: Display pulgadas-diámetro with 1 decimal precision on confirmar
- **D109 (12-06)**: Version detected inline (total_uniones > 0) instead of using detectSpoolVersion helper (avoids type casting issues)
- **D110 (12-06)**: Session cache checked before API call (avoids unnecessary network latency)
- **D111 (12-06)**: Error defaults to v3.0 with retry button (backward compatible + user recovery path)
- **D112 (12-06)**: v4.0 INICIAR routes to /seleccionar-spool, FINALIZAR routes to /seleccionar-uniones (skip P4 for FINALIZAR)
- **D113 (12-06)**: Both button sets use consistent styling (h-20 for v4.0 full-width, h-40 for v3.0 grid)
- **D114 (12-07)**: Batch processing with 5 spools at a time prevents API overload during version detection
- **D115 (12-07)**: Session storage cache reduces redundant version detection API calls (spool_version_{TAG} format)
- **D116 (12-07)**: INICIAR navigation calls iniciarSpool API directly, skips union selection (simplified v4.0 workflow)
- **D117 (12-07)**: Type assertions for backend fields (Ocupado_Por) not in Spool interface (backend data completeness)
- **D118 (12-07)**: Default to v3.0 on version detection error (safer legacy workflow fallback)

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
  - 10-05 ✓: Integration tests and performance validation (6.0 min)
  - Test coverage: 34 new v4.0 integration/performance tests (100% passing)
  - Performance: <1s for 10-union batches (p95 requirement MET)
- **✅ Phase 11 Complete**: API Endpoints & Metrics (6/6 plans, 34.9 min total, 5.8-min avg)
  - 11-01 ✓: API Versioning & V3 Migration (5.2 min)
    - Created occupation_v3.py router with v3.0 endpoints at /api/v3/
    - Maintained legacy routes at /api/ for backward compatibility
    - Added version detection utils (is_v4_spool, get_spool_version)
    - 8 smoke tests validate versioning structure
  - 11-02 ✓: Union Query Endpoints (2.9 min)
    - GET /api/v4/uniones/{tag}/disponibles?operacion=ARM|SOLD
    - GET /api/v4/uniones/{tag}/metricas (5 fields, 2-decimal pulgadas)
    - API models: UnionSummary, DisponiblesResponse, MetricasResponse
    - 12 unit tests (6 disponibles, 6 metricas), all passing
  - 11-03 ✓: INICIAR Workflow Endpoint (5.2 min)
    - POST /api/v4/occupation/iniciar endpoint with version detection
    - Rejects v3.0 spools with helpful 400 error (correct_endpoint guidance)
    - ARM prerequisite validation for SOLD (403 Forbidden)
    - Error handling: 400/403/404/409/500
    - Reused existing IniciarRequest model (DRY principle)
    - 11 smoke tests passing
  - 11-04 ✓: FINALIZAR Workflow Endpoint (6.0 min)
    - POST /api/v4/occupation/finalizar with union selection
    - Auto-determines PAUSAR/COMPLETAR/CANCELADO based on selection
    - Calculates pulgadas-diámetro from union metrics (2 decimal precision)
    - Error handling: 400/403/404/409/500 status codes
    - Race condition detection (409 CONFLICT)
  - 11-05 ✓: Integration Tests & Validation (10.6 min)
    - 35 passing smoke tests (endpoint existence, validation, OpenAPI)
    - 12 skipped workflow tests (documented manual procedures)
    - Manual validation guide (14 comprehensive curl-based scenarios)
    - Updated pytest.ini for v4.0 test structure
    - Test coverage: v4.0 endpoints, versioning, error handling
  - 11-06 ✓: Fix Metadata Batch + Granular Event Logging (5.0 min, gap closure)
    - Refactored OccupationService.finalizar_spool() to use UnionService.process_selection()
    - Fixed metadata logging gap: 1 batch + N granular events per FINALIZAR
    - Satisfied METRIC-03/METRIC-04 requirements
    - Added test coverage for batch + granular metadata logging pattern
  - Test coverage: 48 new tests (36 passing, 12 skipped with manual procedures)
  - All v4.0 API endpoints implemented, validated, and metadata logging complete
- **✅ Phase 12 Complete**: Frontend Union Selection UX (8/8 plans, 28.7 min, 3.6-min avg)
  - 12-01 ✓: TypeScript Type Definitions (4.0 min)
    - Added Union, DisponiblesResponse, MetricasResponse types
    - IniciarRequest/Response, FinalizarRequest/Response types
    - Comprehensive JSDoc documentation for v4.0 types
    - TypeScript compilation verified
  - 12-02 ✓: Reusable Components (Modal, UnionTable) (2.0 min)
    - Modal component with portal rendering and backdrop
    - UnionTable component shell with TypeScript interfaces
    - Build and lint verification passed
  - 12-03 ✓: Context Extension with v4.0 State (2.0 min)
    - Extended AppContext with accion, selectedUnions, pulgadasCompletadas fields
    - Helper functions: resetV4State, calculatePulgadas, toggleUnionSelection, selectAllAvailableUnions
    - All helpers memoized with useCallback for performance
    - v3.0 backward compatibility maintained
  - 12-04 ✓: P5 Union Selection Page with Checkboxes (2.0 min)
    - Created app/seleccionar-uniones/page.tsx (219 lines)
    - Fresh API call via getDisponiblesUnions for accuracy
    - Sticky counter: "Seleccionadas: X/Y | Pulgadas: Z"
    - 56x56px checkboxes (w-14 h-14) for gloved hands
    - Zero-selection modal with disabled backdrop click
    - Full UnionTable selection logic with completion badges
  - 12-05 ✓: API Integration & Error Handling for P5 (3.8 min)
    - P5 loads unions via GET /api/v4/uniones/{tag}/disponibles
    - 409 conflict triggers modal with 2-second auto-reload countdown
    - 403 ownership error shows clear message and redirects
    - Session storage preserves selection on error for resilience
    - Confirmar page calls finalizarSpool for v4.0 FINALIZAR flow
    - Display selected unions count and pulgadas-diámetro on confirmation
  - 12-06 ✓: P3 Version Detection & Dual Button Sets (3.4 min)
    - P3 shows 2 buttons (INICIAR/FINALIZAR) for v4.0 spools
    - P3 shows 3 buttons (TOMAR/PAUSAR/COMPLETAR) for v3.0 spools
    - Version detected by total_uniones > 0 (inline check, no helper)
    - Session storage cache checked before API call
    - Error defaults to v3.0 with retry button
  - 12-07 ✓: P4 Spool Filtering & Version Badges (4.0 min)
    - P4 filters by action: INICIAR shows disponibles, FINALIZAR shows occupied
    - INICIAR calls iniciarSpool API directly, skips union selection
    - Version badges (green v4.0, gray v3.0) on SpoolTable
    - Batch version detection (5 spools at a time)
    - Session storage cache for version results
  - 12-08 ✓: P6 Success Page with Dynamic Messaging (6.4 min)
    - Dynamic success messages based on action type (INICIAR/FINALIZAR)
    - Work summary with union count and pulgadas-diámetro metric
    - "Continuar con Mismo Spool" button for FINALIZAR workflow
    - Session storage cleanup on successful workflow completion
    - Worker and timestamp information display

**v3.0 Technical Debt:**
- 4 failing tests in test_occupation_service.py (CompletarRequest schema change requires operacion field)
- Phase 4 missing formal VERIFICATION.md (code verified via integration checker)
- Frontend metrología/reparación integration unverified (backend complete, UI may be missing)
- No dedicated reparación router (endpoints in actions.py instead of separate router)
- No E2E SSE test with real infrastructure (verified at code level only)

## Session Continuity

Last session: 2026-02-02
Stopped at: Completed Phase 12 (all 8 plans executed successfully)
Resume file: None - Phase 12 complete

**Phase 12 Complete (8/8 plans, 28.7 min, 3.6-min avg):** Frontend Union Selection UX complete. All 7 success criteria verified through codebase inspection and build validation. Dual workflows (v3.0 3-button vs v4.0 2-button), union selection checkboxes, real-time pulgadas counter, zero-selection modal, version detection with session storage caching, action-based spool filtering, and dynamic success messages all implemented and verified. TypeScript/ESLint/Build all passing. Next: Phase 13 (final phase) for performance validation and optimization.
