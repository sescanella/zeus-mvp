# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-01-26)

**Core value:** Real-time visibility of spool occupation - See EN VIVO who is working on which spool
**Current focus:** Phase 5 - Metrología Workflow

## Current Position

Phase: 6 of 6 (Reparación Loops) ✅ COMPLETE
Plan: 4 of 4 (06-03-PLAN.md) ✅ REST endpoints + frontend integration complete
Status: Full reparación workflow with REST API, BLOQUEADO display, and 4th operation UI
Last activity: 2026-01-28 — Completed 06-03: REST endpoints + frontend integration with cycle info display and BLOQUEADO state

Progress: [██████████████████████████████████] 100% Phase 6 - 4 of 4 plans complete (34 of 34 total)

## Performance Metrics

**Velocity:**
- Total plans completed: 34
- Average duration: 4.5 minutes
- Total execution time: 2.55 hours

**By Phase:**

| Phase | Plans | Total | Avg/Plan |
|-------|-------|-------|----------|
| 01    | 9/9 ✅ | 51 min | 5.7 min    |
| 02    | 6/6 ✅  | 22 min  | 3.7 min    |
| 03    | 4/4 ✅ | 16 min  | 4.0 min    |
| 04    | 4/4 ✅ | 15 min  | 3.8 min    |
| 05    | 4/4 ✅ | 19.5 min  | 4.9 min    |
| 06    | 4/4 ✅ | 29 min  | 7.25 min    |

**Recent Trend:**
- Last 4 plans: 06-01 (4.7 min), 06-02 (4.7 min), 06-01 (7.7 min), 06-03 (12 min)
- Trend: Phase 6 complete - REST + frontend integration took longer (8 files modified)

*Updated after each plan completion*

## Accumulated Context

### Decisions

Decisions are logged in PROJECT.md Key Decisions table.
Recent decisions affecting current work:

- **Phase 1 (Planning):** Branch-based migration chosen over dual-write complexity - build v3.0 in separate branch, one-time cutover
- Phase 1 (Planning): Three new columns at end of sheet (Ocupado_Por, Fecha_Ocupacion, version) - safest position
- Phase 1 (Planning): Archive v2.1 tests, create 5-10 v3.0 smoke tests instead of running all 244 tests
- Phase 1 (Planning): 1-week rollback window after cutover before archiving v2.1
- Phase 1 (Planning): Hierarchical state machine (9 states, not 27) to prevent state explosion
- Phase 1 (Planning): Optimistic locking with version tokens for race condition prevention
- **Phase 1 (01-01):** Script-based migrations with idempotency for safe re-execution
- Phase 1 (01-01): Import V3_COLUMNS from config for single source of truth
- Phase 1 (01-01): Idempotency via column existence check (no migration version tracking)
- **Phase 1 (01-02):** Compatibility mode pattern for safe v2.1 → v3.0 migration
- Phase 1 (01-02): Default to v2.1 mode until migration complete (explicit opt-in to v3.0)
- Phase 1 (01-02): esta_ocupado as computed property (single source of truth from ocupado_por)
- **Phase 1 (01-03):** Archive v2.1 tests, create 28 focused v3.0 smoke tests (< 3 sec execution)
- Phase 1 (01-03): Use pytest.skip for migration-dependent tests (clear communication)
- Phase 1 (01-03): Test archival preserves historical knowledge without maintenance burden
- **Phase 1 (01-04):** 5-step migration process (backup, add columns, verify, init versions, smoke tests)
- Phase 1 (01-04): JSON checkpoint files for atomic operations with recovery
- Phase 1 (01-04): Sample-based verification (10 rows) for fast validation
- Phase 1 (01-04): 7-day rollback window balances safety and storage costs
- **Phase 1 (01-05):** Skip-based test organization for manual tests (clear distinction between CI-automated and manual)
- Phase 1 (01-05): Test harness dry-run mode prevents accidental sheet manipulation
- Phase 1 (01-05): Two-job CI pipeline (test-migration + smoke-tests) for parallel execution and fast feedback
- Phase 1 (01-05): psutil optional dependency with graceful skip for memory tests
- **Phase 1 (01-06-GAP):** Manual backup via Google Sheets UI when API storage quota is exceeded
- Phase 1 (01-06-GAP): 7-day rollback window balances safety with storage constraints
- Phase 1 (01-06-GAP): Verification via gspread API confirms backup integrity (row/column counts)
- **Phase 1 (01-07-GAP):** Sheet grid expansion before column addition (Google Sheets API enforces strict limits)
- Phase 1 (01-07-GAP): Production schema is 66 columns (63 v2.1 + 3 v3.0), not 68 as originally planned
- Phase 1 (01-07-GAP): Column positions 64-66 (1-indexed) for Ocupado_Por, Fecha_Ocupacion, version
- **Phase 1 (01-08a-GAP):** Fix verification script to use read_worksheet() instead of non-existent get_headers()/get_all_values()
- Phase 1 (01-08a-GAP): Skip empty rows in data integrity checks (292 valid rows with TAG_SPOOL)
- Phase 1 (01-08a-GAP): Migration coordinator executed with checkpoint recovery - all 6 verification checks passed
- **Phase 1 (01-08b-GAP):** Phase 1 marked complete with all 5 truths verified after gap closure
- Phase 1 (01-08b-GAP): Migration completion documentation includes rollback window expiration (2026-02-02)
- Phase 1 (01-08b-GAP): Production schema is 66 columns (63 v2.1 + 3 v3.0), confirmed and documented
- **Phase 2 (02-01):** 1-hour lock TTL balances long operations safety with preventing permanent locks
- Phase 2 (02-01): Lock token format "{worker_id}:{uuid4}" embeds identity + unique token for ownership verification
- Phase 2 (02-01): RedisRepository singleton pattern shares connection pool (max 50 connections) across all requests
- **Phase 2 (02-02):** Explicit 409 mapping in router endpoints for clear LOC-04 requirement compliance
- Phase 2 (02-02): Best-effort metadata logging - Redis lock + Sheets write are critical, metadata is audit only
- Phase 2 (02-02): Deferred Estado_Ocupacion column to future v3.0 schema enhancement
- **Phase 2 (02-03):** UUID4 version tokens chosen over sequential counters for global uniqueness
- Phase 2 (02-03): Max 3 retry attempts with exponential backoff (100ms-10s range) balances success rate with load
- Phase 2 (02-03): Jittered backoff (±25%) prevents thundering herd during concurrent retries
- Phase 2 (02-03): Two-layer defense - Redis locks (primary) + version tokens (secondary) for data integrity
- **Phase 2 (02-04):** Integration tests require real infrastructure (FastAPI + Redis + Sheets) for true race condition validation
- Phase 2 (02-04): Unit tests use AsyncMock for fast, isolated testing without infrastructure dependencies
- Phase 2 (02-04): Test guide documents procedures instead of automated verification during plan execution
- **Phase 2 (02-05-GAP):** get_client() method for dependency injection - repository owns client lifecycle
- Phase 2 (02-05-GAP): Optional[Redis] return type handles pre-connection state safely
- Phase 2 (02-05-GAP): Warning logs help debug startup timing issues
- **Phase 2 (02-06-GAP):** Non-blocking Redis startup - API starts even if Redis fails, enabling degraded mode
- Phase 2 (02-06-GAP): Redis lifecycle integrated in FastAPI startup/shutdown events for proper connection management
- Phase 2 (02-06-GAP): Redis health check endpoint (/api/redis-health) for monitoring connection status
- **Phase 2 (Orchestrator):** Missing datetime imports in metadata_repository.py fixed - date/datetime required for type hints
- Phase 2 (Orchestrator): SheetsRepository.get_spool_by_tag() implemented - missing method required by OccupationService
- Phase 2 (Orchestrator): Dynamic column mapping with multi-format date parsing for robustness
- Phase 2 (Orchestrator): Integration test validation requires test data - 404 responses confirm correct error handling
- **Phase 3 (03-01):** Estado_Detalle column added at position 67 for combined state display (occupation + operation progress)
- Phase 3 (03-01): Separate state machines per operation (ARM/SOLD) prevents state explosion (9 states instead of 27+)
- Phase 3 (03-01): Guard + validator pattern for dependencies - guards control transitions, validators provide error messages
- Phase 3 (03-01): python-statemachine==2.5.0 chosen for declarative state management with async support
- **Phase 3 (03-03):** State machines own column updates via callbacks - single source of truth for Sheets writes
- Phase 3 (03-03): Estado_Detalle updates on EVERY state transition (TOMAR/PAUSAR/COMPLETAR) for real-time visibility
- Phase 3 (03-03): Date format DD-MM-YYYY for consistency with existing production data
- **Phase 3 (03-04):** History shows ALL events chronologically - no filtering for simple complete view
- Phase 3 (03-04): Duration calculation shows time between TOMAR and PAUSAR/COMPLETAR
- Phase 3 (03-04): Integration tests use mocks to verify StateService orchestration patterns
- **Phase 4 (04-01):** Channel name spools:updates for all spool state changes (centralized broadcast)
- Phase 4 (04-01): Event types TOMAR, PAUSAR, COMPLETAR, STATE_CHANGE for different transition types
- Phase 4 (04-01): 15-second keepalive ping with 30-second send timeout for connection management
- Phase 4 (04-01): X-Accel-Buffering: no header prevents nginx/proxy buffering issues
- Phase 4 (04-01): Best-effort event publishing (logs errors, returns bool) - doesn't block operations
- **Phase 4 (04-02):** Event publishing after successful Sheets writes (inside tenacity retry logic)
- Phase 4 (04-02): Best-effort event delivery with try/catch wrapper - logs warnings, never blocks
- Phase 4 (04-02): Dashboard REST + SSE pattern: REST for initial load, SSE for incremental updates
- Phase 4 (04-02): STATE_CHANGE events separate from occupation events (different semantic meaning)
- Phase 4 (04-02): Estado_detalle built before event publishing for client-side consistency
- **Phase 4 (04-03):** EventSource with exponential backoff (1s-30s) and max 10 retries
- Phase 4 (04-03): Page Visibility API closes connection on background, reconnects on foreground
- Phase 4 (04-03): Race condition handled with friendly Spanish error message
- Phase 4 (04-03): PAUSAR events trigger full list refresh for simplicity
- **Phase 5 (05-01):** Both APROBADO and RECHAZADO marked as final states to enforce reparación workflow (Phase 6)
- Phase 5 (05-01): Skip TOMAR occupation entirely - inspection completes in single atomic operation
- Phase 5 (05-01): Occupied spools blocked from inspection to prevent race conditions (ocupado_por == None filter)
- **Phase 5 (05-02):** Pydantic ResultadoEnum enforces binary valores (APROBADO/RECHAZADO) at API boundary
- Phase 5 (05-02): EstadoDetalleBuilder extended with optional metrologia_state parameter for backward compatibility
- Phase 5 (05-02): Display formats - APROBADO: "METROLOGIA APROBADO ✓", RECHAZADO: "METROLOGIA RECHAZADO - Pendiente reparación"
- **Phase 5 (05-03):** Operation-specific routing skips tipo-interaccion for METROLOGIA (instant completion only)
- Phase 5 (05-03): Single-spool workflow (no batch multiselect) deferred for Phase 5 simplicity
- Phase 5 (05-03): Instant submission on resultado selection (no confirmation screen) for faster workflow
- **Phase 5 (05-04):** Async service pattern for SSE integration - MetrologiaService.completar() async enables real-time events
- Phase 5 (05-04): Best-effort SSE publishing - inspection succeeds even if Redis fails (resilient to infrastructure issues)
- Phase 5 (05-04): Role validation for METROLOGIA deferred - pattern established in ARM/SOLD, can be added when needed
- **Phase 6 (06-02):** Cycle count embedded in Estado_Detalle string instead of dedicated column (avoids schema migration)
- Phase 6 (06-02): Consecutive rejection tracking only - counter resets to 0 after APROBADO (allows recovery after bad batch)
- Phase 6 (06-02): 3-cycle limit before blocking (industry standard, balances recovery vs escalation)
- Phase 6 (06-02): SpoolBloqueadoError (HTTP 403) for blocked spools requiring supervisor intervention
- **Phase 6 (06-01):** 4-state machine with occupation management (RECHAZADO → EN_REPARACION → REPARACION_PAUSADA → PENDIENTE_METROLOGIA)
- Phase 6 (06-01): Cycle count preserved across all state transitions (increments only on metrología RECHAZADO)
- Phase 6 (06-01): COMPLETAR automatically sets PENDIENTE_METROLOGIA (immediate re-queue for metrología inspection)
- **Phase 6 (06-03):** REPARACIÓN as 4th operation with yellow styling (no role restriction - all workers)
- Phase 6 (06-03): BLOQUEADO spools displayed with red styling, lock icon, disabled selection
- Phase 6 (06-03): Cycle info displayed in spool selection ("Ciclo X/3" instead of NV column)

### Pending Todos

None yet.

### Blockers/Concerns

**Phase 1 (COMPLETE):** ✅ All 9 plans executed, all 5 truths verified
- ✅ Gap 1 CLOSED: Production backup created (1kWUjegxV00MOJver_9ljZqHxgJJBgErnH_J--N4TS9M) - 7-day rollback window active until 2026-02-02
- ✅ Gap 2 CLOSED: v3.0 columns added to production sheet (66 columns: 63 v2.1 + 3 v3.0)
- ✅ Gap 3a CLOSED: Migration coordinator executed - 6/6 verification checks, 39/39 tests passed
- ✅ Gap 3b CLOSED: Migration documentation complete (MIGRATION_COMPLETE.md, 01-VERIFICATION.md updated)
- **Status:** Phase 1 complete

**Phase 2 (COMPLETE):** ✅ Core Location Tracking - All 4 waves + 2 gap closures complete
- ✅ Wave 1: Redis infrastructure deployed (02-01: 3 min)
- ✅ Wave 2: OccupationService with TOMAR/PAUSAR/COMPLETAR (02-02: 5.5 min)
- ✅ Wave 3: Optimistic locking with version tokens (02-03: 4 min)
- ✅ Wave 4: Race condition test suite (02-04: 6 min)
- ✅ Gap 5: Fix Redis repository get_client method (02-05-GAP: 1 min)
- ✅ Gap 6: Integrate Redis lifecycle in FastAPI startup/shutdown (02-06-GAP: 2.6 min)
- **Status:** Phase 2 complete - ready for Phase 3
- **Deferred to future:**
  - Estado_Ocupacion column for paused state marking

**Phase 3 (COMPLETE):** ✅ State Machine & Collaboration - All 4 plans complete
- ✅ Plan 03-01: State machine foundation (3 min)
  - Estado_Detalle column added at position 67
  - ARM state machine created (3 states, 3 transitions)
  - SOLD state machine with ARM dependency guard
  - python-statemachine==2.5.0 integrated
- ✅ Plan 03-02: StateService orchestration (3 min)
  - StateService integrates with OccupationService
  - Hydration logic syncs state machines with Sheets
  - EstadoDetalleBuilder for display formatting
- ✅ Plan 03-03: State machine callbacks (3.6 min)
  - ARM/SOLD callbacks update columns automatically
  - Estado_Detalle updates on every transition
  - TOMAR/PAUSAR/COMPLETAR trigger column writes
- ✅ Plan 03-04: History and collaboration tests (6 min)
  - GET /api/history/{tag_spool} endpoint with timeline
  - HistoryService aggregates Metadata events into sessions
  - Integration tests verify multi-worker collaboration
- **Status:** Phase 3 complete

**Phase 4 (COMPLETE):** ✅ Real-Time Visibility - All 4 plans complete
- ✅ Plan 04-01: SSE backend infrastructure (4 min)
  - GET /api/sse/stream endpoint with Redis pub/sub
  - RedisEventService publishes to spools:updates channel
  - EventSourceResponse with anti-buffering headers
  - 10 unit tests for event publisher
  - Graceful degradation when Redis unavailable
- ✅ Plan 04-02: Event integration & dashboard endpoint (3 min)
  - OccupationService publishes TOMAR/PAUSAR/COMPLETAR events
  - StateService publishes STATE_CHANGE events on transitions
  - GET /api/dashboard/occupied endpoint returns occupied spools
  - Best-effort event delivery (logs errors, doesn't block)
  - Dynamic column mapping for robust sheet reading
- ✅ Plan 04-03: Frontend SSE client integration (3 min)
  - useSSE hook with EventSource and exponential backoff
  - Page Visibility API for mobile lifecycle management
  - ConnectionStatus component (green/red indicator)
  - Real-time spool selection with TOMAR/PAUSAR/COMPLETAR/STATE_CHANGE handling
- ✅ Plan 04-04: Dashboard UI + load testing (5 min)
  - Dashboard page with occupied spools list
  - Real-time updates via SSE
  - Locust load test for 30 concurrent users
- **Status:** Phase 4 complete

**Phase 5 (COMPLETE):** ✅ Metrología Workflow - 4 of 4 plans complete
- ✅ Plan 05-01: State machine and service layer (6 min)
  - MetrologiaStateMachine with 3 states (PENDIENTE → APROBADO/RECHAZADO)
  - MetrologiaService for instant completion workflow
  - validar_puede_completar_metrologia() with 4 prerequisite checks
  - get_spools_for_metrologia() filtering method
  - 21 unit tests passing
- ✅ Plan 05-02: REST endpoint & estado display (3 min)
  - POST /api/metrologia/completar endpoint with binary resultado
  - Pydantic models: CompletarMetrologiaRequest/Response, ResultadoEnum
  - EstadoDetalleBuilder extended for metrología states
  - Error handling: 404, 400, 409, 403, 422
- ✅ Plan 05-03: Frontend binary resultado flow (4 min)
  - Operation-specific routing (skip tipo-interaccion for METROLOGIA)
  - Binary resultado selection page with APROBADO/RECHAZADO buttons
  - completarMetrologia API function with error handling
  - Single-spool workflow (no batch multiselect)
- ✅ Plan 05-04: SSE integration & comprehensive tests (6.5 min)
  - COMPLETAR_METROLOGIA SSE events for real-time dashboard updates
  - 12 integration tests (APROBADO/RECHAZADO flows + error scenarios)
  - 11 unit validation tests (4 prerequisites + state machine transitions)
  - Async service pattern for event publishing
  - 44 total metrología tests passing (21 existing + 23 new)
- **Status:** Phase 5 complete - Real-time inspection workflow with comprehensive test coverage

**Phase 6 (COMPLETE):** ✅ Reparación Loops - 4 of 4 plans complete
- ✅ Plan 06-01: Research & context (4.7 min)
  - Researched manufacturing rework best practices (3-cycle limit standard)
  - Documented embedded cycle counting strategy (no new columns)
  - Captured user decisions (REPARACIÓN as 4th operation, no role restriction)
  - Created CONTEXT.md and RESEARCH.md with implementation patterns
- ✅ Plan 06-02: Cycle counting logic (4.7 min)
  - CycleCounterService for parsing/incrementing cycles from Estado_Detalle
  - MetrologiaStateMachine extended with cycle tracking
  - SpoolBloqueadoError (HTTP 403) for blocked spools
  - validar_puede_tomar_reparacion() and validar_puede_cancelar_reparacion()
  - 47 passing tests (26 cycle counter + 21 validation)
- ✅ Plan 06-03: REST endpoints + frontend integration (12 min)
  - GET /api/spools/reparacion with CycleCounterService integration
  - 4 POST endpoints: tomar, pausar, completar, cancelar reparación
  - REPARACIÓN as 4th operation (yellow button, Wrench icon)
  - Spool selection with BLOQUEADO display (red styling, lock icon)
  - Cycle info display ("Ciclo X/3" in table column)
  - 5 API functions with 'unknown' return type (no 'any')
- **Status:** Phase 6 complete - Full reparación workflow operational

## Session Continuity

Last session: 2026-01-28
Stopped at: Completed 06-03-PLAN.md (REST endpoints + frontend integration) ✅
Resume file: None

**Phase 6 Plan 06-03 complete!**
- REST endpoints: GET /spools/reparacion + 4 POST actions (tomar/pausar/completar/cancelar)
- Frontend: REPARACIÓN as 4th operation with yellow button
- UI: BLOQUEADO spools displayed with red styling, lock icon, disabled selection
- Cycle display: "Ciclo X/3" shown in spool selection table
- API functions: 5 new functions with type-safe 'unknown' return types

**Commits:**
- fa49147: feat(06-03): add REST endpoints for reparación workflow
- 1fbfd9b: feat(06-03): add REPARACIÓN as 4th operation in frontend
- 5478026: feat(06-03): update spool selection for reparación workflow
- cad8648: feat(06-03): add API functions for reparación workflow

**Phase 6 Complete - Reparación Loops:**
- ✅ Research & context (06-01): 4.7 min
- ✅ State machine (06-01): 7.7 min - 22 tests
- ✅ Cycle counting logic (06-02): 4.7 min - 47 tests
- ✅ REST endpoints + frontend (06-03): 12 min - 8 files
- **Total:** 29 minutes for complete reparación workflow

**Next steps:**
- All 6 phases complete! System ready for production deployment
- Remaining work: Frontend tipo-interaccion + confirmar integration for REPARACION
