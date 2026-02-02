# Roadmap: ZEUES Manufacturing Traceability System

## Milestones

- ✅ **v3.0 Real-Time Location Tracking** - Phases 1-6 (shipped 2026-01-28)
- 🚧 **v4.0 Uniones System** - Phases 7-13 (in progress)

## Phases

<details>
<summary>✅ v3.0 Real-Time Location Tracking (Phases 1-6) - SHIPPED 2026-01-28</summary>

**Delivered:** Real-time spool occupation tracking with Redis-backed atomic locks, hierarchical state machines, SSE streaming for sub-10s dashboard updates, instant metrología inspection, and bounded reparación cycles with supervisor override.

**Stats:** 158 commits, 491K LOC, 31 plans, 161 minutes execution time, 3 days from requirements to ship

</details>

### 🚧 v4.0 Uniones System (In Progress)

**Milestone Goal:** Track work at the union level with the correct business metric (pulgadas-diámetro). Enable workers to complete work by individual welds, measure performance in pulgadas-diámetro, and support partial completion workflows.

#### Phase 7: Data Model Foundation
**Goal**: Sheets schema ready for union-level tracking with audit columns and metrics aggregations
**Depends on**: v3.0 Phase 6 (shipped)
**Requirements**: DATA-01, DATA-02, DATA-03, DATA-04, DATA-05
**Success Criteria** (what must be TRUE):
  1. Uniones sheet has 18 columns including 5 audit fields (version, Creado_Por, Fecha_Creacion, Modificado_Por, Fecha_Modificacion)
  2. Operaciones sheet has 72 columns including 5 new metrics columns (Total_Uniones, Uniones_ARM_Completadas, Uniones_SOLD_Completadas, Pulgadas_ARM, Pulgadas_SOLD)
  3. Metadata sheet has 11 columns including N_UNION field at position 11 for granular audit trail
  4. System queries all sheets using dynamic header mapping (no hardcoded column indices)
  5. UnionRepository can query Uniones using OT column as foreign key to Operaciones
**Plans**: 7 plans (including 2 gap closure plans)

Plans:
- [x] 07-01-PLAN.md — Extend Operaciones sheet to 72 columns with metrics
- [x] 07-02-PLAN.md — Validate Uniones sheet and extend Metadata schema
- [x] 07-03-PLAN.md — Create Union model and repository with tests
- [x] 07-04-PLAN.md — Add startup schema validation for all sheets
- [x] 07-05-PLAN.md — Integrate v4.0 schema validation into FastAPI startup
- [x] 07-06-PLAN.md — Execute schema migrations for Operaciones and Metadata (gap closure)
- [x] 07-07-PLAN.md — Document Uniones requirements for Engineering (gap closure)

#### Phase 8: Backend Data Layer
**Goal**: Repository layer can read/write union data with batch operations and performance optimization
**Depends on**: Phase 7
**Requirements**: REPO-01, REPO-02, REPO-03, REPO-04, REPO-05, REPO-06, REPO-07, REPO-08, REPO-09
**Success Criteria** (what must be TRUE):
  1. UnionRepository can fetch disponibles for ARM (where ARM_FECHA_FIN IS NULL) and SOLD (where ARM_FECHA_FIN IS NOT NULL AND SOL_FECHA_FIN IS NULL)
  2. UnionRepository can batch update ARM and SOLD timestamps using gspread.batch_update() with A1 notation in single API call
  3. UnionRepository can count completed unions and sum pulgadas for ARM and SOLD operations
  4. MetadataRepository can log batch events with auto-chunking (900 rows max per chunk)
  5. Union Pydantic model validates 18 fields matching Uniones sheet structure
**Plans**: 5 plans

Plans:
- [x] 08-01-PLAN.md — Implement batch update methods for ARM and SOLD operations
- [x] 08-02-PLAN.md — Implement OT-based query methods for union repository
- [x] 08-03-PLAN.md — Implement metrics aggregation methods for union tracking
- [x] 08-04-PLAN.md — Extend metadata repository with batch logging and N_UNION field
- [x] 08-05-PLAN.md — Integration tests and performance validation

#### Phase 9: Redis & Version Detection
**Goal**: Redis locks support long-running sessions and system detects v3.0 vs v4.0 spools for dual workflow routing
**Depends on**: Phase 8
**Requirements**: REDIS-01, REDIS-02, REDIS-03, REDIS-04, REDIS-05, VER-01, VER-02, VER-03
**Success Criteria** (what must be TRUE):
  1. Redis locks have NO TTL and persist until FINALIZAR operation releases them
  2. System executes lazy cleanup on INICIAR removing locks older than 24h without matching Sheets.Ocupado_Por
  3. System reconciles Redis locks from Sheets.Ocupado_Por on application startup for auto-recovery
  4. Frontend detects spool version by union count (count > 0 = v4.0, count = 0 = v3.0)
  5. System validates v4.0 endpoints reject v3.0 spools with clear error message
**Plans**: 6 plans

Plans:
- [x] 09-01-PLAN.md — Implement persistent Redis locks without TTL
- [x] 09-02-PLAN.md — Add lazy cleanup mechanism for abandoned locks
- [x] 09-03-PLAN.md — Implement startup reconciliation from Sheets
- [x] 09-04-PLAN.md — Create version detection service and diagnostic endpoint
- [x] 09-05-PLAN.md — Integration tests for persistent locks and version detection
- [x] 09-06-PLAN.md — Frontend version detection and badges

#### Phase 10: Backend Services & Validation
**Goal**: Business logic orchestrates union selection with auto-determination of PAUSAR vs COMPLETAR and ARM-before-SOLD validation
**Depends on**: Phase 9
**Requirements**: SVC-01, SVC-02, SVC-03, SVC-04, SVC-05, SVC-06, SVC-07, SVC-08, VAL-01, VAL-02, VAL-03, VAL-04, VAL-05, VAL-06, VAL-07
**Success Criteria** (what must be TRUE):
  1. UnionService can process selection with batch update and metadata logging in under 1 second for 10 unions
  2. UnionService calculates pulgadas-diámetro by summing DN_UNION with 1 decimal precision
  3. OccupationService.iniciar_spool() writes Ocupado_Por and Fecha_Ocupacion without touching Uniones sheet
  4. OccupationService.finalizar_spool() auto-determines PAUSAR (partial) vs COMPLETAR (100%) based on selection count
  5. ValidationService enforces ARM-before-SOLD rule: SOLD requires at least 1 union with ARM_FECHA_FIN != NULL
  6. System triggers automatic transition to metrología queue when SOLD is 100% complete
  7. System allows 0 unions selected in FINALIZAR after modal confirmation (logs SPOOL_CANCELADO event)
**Plans**: 5 plans

Plans:
- [x] 10-01-PLAN.md — Create UnionService for batch operations
- [x] 10-02-PLAN.md — Enhance OccupationService with INICIAR/FINALIZAR
- [x] 10-03-PLAN.md — Add ARM-before-SOLD validation
- [x] 10-04-PLAN.md — Implement metrología auto-transition
- [x] 10-05-PLAN.md — Integration tests and performance validation

#### Phase 11: API Endpoints & Metrics
**Goal**: REST API exposes union workflows with INICIAR/FINALIZAR endpoints and maintains v3.0 compatibility
**Depends on**: Phase 10
**Requirements**: API-01, API-02, API-03, API-04, API-05, API-06, METRIC-01, METRIC-02, METRIC-03, METRIC-04, METRIC-05, METRIC-06, METRIC-07, METRIC-08, METRIC-09
**Success Criteria** (what must be TRUE):
  1. GET /api/uniones/{tag}/disponibles?operacion=ARM|SOLD returns filtered unions based on operation type
  2. GET /api/uniones/{tag}/metricas returns aggregated metrics (total_uniones, arm_completadas, sold_completadas, pulgadas_arm, pulgadas_sold)
  3. POST /api/occupation/iniciar occupies spool with Redis lock without modifying Uniones sheet
  4. POST /api/occupation/finalizar accepts selected_unions array and auto-determines PAUSAR or COMPLETAR
  5. v3.0 endpoints (/tomar, /pausar, /completar) remain functional for backward compatibility
  6. Metadata logs 1 batch event (spool level) plus N granular events (union level) per FINALIZAR operation
  7. Dashboard displays pulgadas-diámetro as primary metric instead of spool count
**Plans**: 6 plans (including 1 gap closure plan)

Plans:
- [x] 11-01-PLAN.md — API versioning and v3.0 endpoint migration
- [x] 11-02-PLAN.md — Union query endpoints (disponibles, metricas)
- [x] 11-03-PLAN.md — INICIAR workflow endpoint
- [x] 11-04-PLAN.md — FINALIZAR workflow endpoint
- [x] 11-05-PLAN.md — Integration tests and validation
- [x] 11-06-PLAN.md — Fix metadata batch + granular event logging (gap closure)

#### Phase 12: Frontend Union Selection UX
**Goal**: Mobile-first UI supports dual workflows (v3.0 3-button vs v4.0 2-button INICIAR/FINALIZAR) with union selection checkboxes
**Depends on**: Phase 11
**Requirements**: UX-01, UX-02, UX-03, UX-04, UX-05, UX-06, UX-07, UX-08, UX-09, UX-10, COMPAT-01, COMPAT-02, COMPAT-03, COMPAT-04, COMPAT-05, COMPAT-06, COMPAT-07
**Success Criteria** (what must be TRUE):
  1. P3 shows 2 buttons (INICIAR, FINALIZAR) for v4.0 spools and 3 buttons (TOMAR, PAUSAR, COMPLETAR) for v3.0 spools
  2. P4 filters spools by action type: INICIAR shows disponibles, FINALIZAR shows ocupados by current worker
  3. P5 (new page) shows union selection checkboxes with N_UNION, DN_UNION, TIPO_UNION columns
  4. P5 displays live counter updating "Seleccionadas: 7/10 | Pulgadas: 18.5" as user selects checkboxes
  5. P5 shows modal confirmation "¿Liberar sin registrar?" when 0 unions selected
  6. P5 disables checkboxes for already-completed unions with visual "✓ Armada" or "✓ Soldada" badge
  7. Metrología and Reparación workflows remain at spool level with no changes to existing UI
**Plans**: TBD

Plans:
- [ ] 12-01: [TBD during phase planning]

#### Phase 13: Performance Validation & Optimization
**Goal**: System meets performance SLA (< 1s p95 for 10 unions) and stays under Google Sheets rate limits
**Depends on**: Phase 12
**Requirements**: PERF-01, PERF-02, PERF-03, PERF-04, PERF-05
**Success Criteria** (what must be TRUE):
  1. Batch union updates achieve < 1s latency at p95 for 10-union selection operation
  2. Batch union updates achieve < 2s latency at p99 (acceptable threshold)
  3. Single FINALIZAR operation makes maximum 2 Sheets API calls (1 batch update + 1 batch append)
  4. Metadata batch logging chunks eventos into 900-row groups to respect Google Sheets append_rows limit
  5. System stays under 50% of Google Sheets write rate limit (30 writes/min vs 60 limit) during normal operations
**Plans**: TBD

Plans:
- [ ] 13-01: [TBD during phase planning]

## Progress

**Execution Order:**
Phases execute in numeric order: 7 → 8 → 9 → 10 → 11 → 12 → 13

| Phase | Milestone | Plans Complete | Status | Completed |
|-------|-----------|----------------|--------|-----------|
| 1. Migration Foundation | v3.0 | Complete | Complete | 2026-01-26 |
| 2. Redis Occupation Infrastructure | v3.0 | Complete | Complete | 2026-01-26 |
| 3. State Machine Architecture | v3.0 | Complete | Complete | 2026-01-27 |
| 4. Real-Time SSE Dashboard | v3.0 | Complete | Complete | 2026-01-27 |
| 5. Metrología Instant Inspection | v3.0 | Complete | Complete | 2026-01-28 |
| 6. Reparación Bounded Cycles | v3.0 | Complete | Complete | 2026-01-28 |
| 7. Data Model Foundation | v4.0 | 7/7 | Complete | 2026-02-02 |
| 8. Backend Data Layer | v4.0 | 5/5 | Complete | 2026-02-02 |
| 9. Redis & Version Detection | v4.0 | 6/6 | Complete | 2026-02-02 |
| 10. Backend Services & Validation | v4.0 | 5/5 | Complete | 2026-02-02 |
| 11. API Endpoints & Metrics | v4.0 | 6/6 | Complete | 2026-02-02 |
| 12. Frontend Union Selection UX | v4.0 | 0/TBD | Not started | - |
| 13. Performance Validation & Optimization | v4.0 | 0/TBD | Not started | - |

---

*Last updated: 2026-02-02 (Phase 11 complete)*