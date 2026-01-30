# Requirements: ZEUES v4.0 Uniones System

**Defined:** 2026-01-30
**Core Value:** Track work at the union level with the correct business metric (pulgadas-diámetro)

## v4.0 Requirements

Requirements for union-level tracking and partial completion workflows. Each maps to roadmap phases.

### Data Model & Schema

- [ ] **DATA-01**: Add 5 columns to Uniones sheet (14-18): version (UUID4), Creado_Por, Fecha_Creacion, Modificado_Por, Fecha_Modificacion
- [ ] **DATA-02**: Add 5 columns to Operaciones sheet (68-72): Total_Uniones, Uniones_ARM_Completadas, Uniones_SOLD_Completadas, Pulgadas_ARM, Pulgadas_SOLD
- [ ] **DATA-03**: Add N_UNION column to Metadata sheet (position 11 at end, nullable) for granular audit trail
- [ ] **DATA-04**: UnionRepository uses OT column (not TAG_SPOOL) for foreign key relationship to Operaciones
- [ ] **DATA-05**: System uses dynamic header mapping for all sheets (never hardcode column indices)

### Backend - Repositories & Models

- [ ] **REPO-01**: UnionRepository provides get_disponibles_arm() - returns unions where ARM_FECHA_FIN IS NULL
- [ ] **REPO-02**: UnionRepository provides get_disponibles_sold() - returns unions where ARM_FECHA_FIN IS NOT NULL AND SOL_FECHA_FIN IS NULL
- [ ] **REPO-03**: UnionRepository provides batch_update_arm() using gspread.batch_update() with A1 notation (1 API call for N unions)
- [ ] **REPO-04**: UnionRepository provides batch_update_sold() using gspread.batch_update() with A1 notation
- [ ] **REPO-05**: UnionRepository provides count_completed_arm() and count_completed_sold() for metrics
- [ ] **REPO-06**: UnionRepository provides sum_pulgadas_arm() and sum_pulgadas_sold() for metrics calculation
- [ ] **REPO-07**: MetadataRepository extends log_event() with n_union: Optional[int] parameter
- [ ] **REPO-08**: MetadataRepository provides batch_log_events() with auto-chunking (900 rows max per chunk)
- [ ] **REPO-09**: Union Pydantic model with 18 fields matching Uniones sheet structure

### Backend - Services & Business Logic

- [ ] **SVC-01**: UnionService provides process_selection() - orchestrates batch update + metadata logging
- [ ] **SVC-02**: UnionService provides calcular_pulgadas() - sums DN_UNION for selected unions with 1 decimal precision
- [ ] **SVC-03**: UnionService provides build_eventos_metadata() - creates batch + granular events
- [ ] **SVC-04**: OccupationService provides iniciar_spool() - writes Ocupado_Por + Fecha_Ocupacion + Redis lock (NO touch Uniones)
- [ ] **SVC-05**: OccupationService provides finalizar_spool() - auto-determines PAUSAR/COMPLETAR, delegates to UnionService, releases lock
- [ ] **SVC-06**: ValidationService enforces ARM→SOLD prerequisite (SOLD requires >= 1 union with ARM_FECHA_FIN != NULL)
- [ ] **SVC-07**: System auto-determines PAUSAR (len(selected) < total) vs COMPLETAR (len(selected) == total)
- [ ] **SVC-08**: System triggers metrología queue when SOLD 100% complete (Estado_Detalle = "En Cola Metrología")

### Backend - API Endpoints

- [ ] **API-01**: GET /api/uniones/{tag}/disponibles?operacion=ARM - returns unions where ARM_FECHA_FIN IS NULL
- [ ] **API-02**: GET /api/uniones/{tag}/disponibles?operacion=SOLD - returns unions where ARM_FECHA_FIN IS NOT NULL AND SOL_FECHA_FIN IS NULL
- [ ] **API-03**: GET /api/uniones/{tag}/metricas - returns {total_uniones, arm_completadas, sold_completadas, pulgadas_arm, pulgadas_sold}
- [ ] **API-04**: POST /api/occupation/iniciar - body: {tag_spool, worker_id, operacion} - occupies spool only
- [ ] **API-05**: POST /api/occupation/finalizar - body: {tag_spool, worker_id, operacion, selected_unions: list[int]} - auto-determines PAUSAR/COMPLETAR
- [ ] **API-06**: System maintains v3.0 endpoints (/tomar, /pausar, /completar) for backward compatibility

### Frontend - UX Workflows

- [ ] **UX-01**: P3 shows 2 buttons (INICIAR, FINALIZAR) for v4.0 spools
- [ ] **UX-02**: P3 shows 3 buttons (TOMAR, PAUSAR, COMPLETAR) for v3.0 spools
- [ ] **UX-03**: P4 filters spools by action - INICIAR: disponibles (STATUS_NV='ABIERTA' AND Status_Spool='EN_PROCESO' AND Ocupado_Por IN ('','DISPONIBLE'))
- [ ] **UX-04**: P4 filters spools by action - FINALIZAR: ocupados (Ocupado_Por LIKE '%(worker_id)%')
- [ ] **UX-05**: P5 (new page) shows union selection checkboxes with N_UNION, DN_UNION, TIPO_UNION
- [ ] **UX-06**: P5 shows live counter "Seleccionadas: 7/10 | Pulgadas: 18.5" updated in real-time
- [ ] **UX-07**: P5 shows modal confirmation "¿Liberar sin registrar?" when 0 unions selected
- [ ] **UX-08**: P5 disables checkboxes for already-completed unions with "✓ Armada" or "✓ Soldada" badge
- [ ] **UX-09**: Context stores accion ('INICIAR' | 'FINALIZAR'), selectedUnions (number[]), pulgadasCompletadas (number)
- [ ] **UX-10**: P6/P7 show dynamic text based on action and display pulgadasCompletadas for FINALIZAR

### Frontend - Version Detection

- [ ] **VER-01**: System detects spool version by querying union count (count > 0 = v4.0, count = 0 = v3.0)
- [ ] **VER-02**: Frontend renders appropriate UX based on spool version (2-button vs 3-button flow)
- [ ] **VER-03**: System validates v4.0 endpoints reject v3.0 spools (union count = 0) with clear error message

### Performance & Optimization

- [ ] **PERF-01**: Batch union updates achieve < 1s latency (p95) for 10-union selection
- [ ] **PERF-02**: Batch union updates achieve < 2s latency (p99) - acceptable threshold
- [ ] **PERF-03**: Single FINALIZAR operation makes max 2 Sheets API calls (1 batch update + 1 batch append)
- [ ] **PERF-04**: Metadata batch logging chunks eventos into 900-row groups (Google Sheets append_rows limit)
- [ ] **PERF-05**: System stays under 50% of Google Sheets rate limit (30 writes/min vs 60 limit)

### Metrics & Audit Trail

- [ ] **METRIC-01**: Dashboard displays pulgadas-diámetro as primary metric (not spool count)
- [ ] **METRIC-02**: System calculates worker performance as pulgadas-diámetro/day
- [ ] **METRIC-03**: Metadata logs SPOOL_ARM_PAUSADO event with {uniones_completadas, total, uniones_trabajadas, pulgadas}
- [ ] **METRIC-04**: Metadata logs SPOOL_ARM_COMPLETADO event with {uniones_completadas, total, pulgadas}
- [ ] **METRIC-05**: Metadata logs SPOOL_SOLD_PAUSADO and SPOOL_SOLD_COMPLETADO events
- [ ] **METRIC-06**: Metadata logs SPOOL_CANCELADO event when 0 unions selected (with operacion and motivo)
- [ ] **METRIC-07**: Metadata logs granular UNION_ARM_REGISTRADA event per union with {dn_union, tipo, timestamp_inicio, timestamp_fin, duracion_min}
- [ ] **METRIC-08**: Metadata logs granular UNION_SOLD_REGISTRADA event per union
- [ ] **METRIC-09**: Each FINALIZAR operation logs 1 batch event (N_UNION=NULL) + N granular events (N_UNION=1-20)

### Redis & State Management

- [ ] **REDIS-01**: Redis locks have NO TTL (permanent until FINALIZAR) to support 5-8 hour work sessions
- [ ] **REDIS-02**: System implements lazy cleanup executed on INICIAR (removes locks > 24h without Sheets.Ocupado_Por match)
- [ ] **REDIS-03**: System reconciles Redis locks from Sheets.Ocupado_Por on application startup (auto-recovery)
- [ ] **REDIS-04**: INICIAR writes Redis lock with key format "spool:{TAG_SPOOL}:lock" and value "{worker_id}"
- [ ] **REDIS-05**: FINALIZAR releases Redis lock and sets Ocupado_Por='DISPONIBLE' regardless of PAUSAR or COMPLETAR outcome

### Validation & Business Rules

- [ ] **VAL-01**: System validates INICIAR SOLD requires >= 1 union with ARM_FECHA_FIN != NULL
- [ ] **VAL-02**: System prevents selecting union for SOLD if ARM_FECHA_FIN IS NULL (backend filters + frontend validation)
- [ ] **VAL-03**: System supports partial ARM completion (worker A: 7/10, worker B: 3/10 later)
- [ ] **VAL-04**: System supports partial SOLD completion with armadas constraint (can complete 5 of 7 soldable unions)
- [ ] **VAL-05**: System handles edge case: 10 total unions, 6 armadas, 4 sin armar → SOLD shows 6 checkboxes, completing 6/6 = PAUSADO (not COMPLETADO)
- [ ] **VAL-06**: System enforces optimistic locking with version UUID on Uniones updates (3x retry with backoff)
- [ ] **VAL-07**: System allows 0 unions selected in FINALIZAR after modal confirmation (logs SPOOL_CANCELADO, releases lock)

### Backward Compatibility

- [ ] **COMPAT-01**: Metrología workflow stays at spool level (no changes to /api/metrologia/completar)
- [ ] **COMPAT-02**: Reparación workflow stays at spool level (no changes to /api/reparacion/*)
- [ ] **COMPAT-03**: Estado_Detalle continues calculating from spool-level data (no union-level granularity)
- [ ] **COMPAT-04**: Uniones columns NDT_UNION and R_NDT_UNION remain NULL in v4.0 (reserved for v4.1+)
- [ ] **COMPAT-05**: SSE endpoints /api/sse/disponible and /api/sse/quien-tiene-que remain unchanged (no new filters)
- [ ] **COMPAT-06**: Operaciones columns Armador, Soldador, Fecha_Armado, Fecha_Soldadura remain in schema (not removed)
- [ ] **COMPAT-07**: Backend calculates Armador/Soldador from Uniones on-demand when legacy endpoints request them

## Future Requirements (v4.1+)

Deferred to next milestone. Tracked but not in v4.0 roadmap.

### Metrología & Reparación Granularity

- **METRO-01**: Metrología inspects individual unions (not entire spool) with checkbox selection UI
- **METRO-02**: NDT_UNION and R_NDT_UNION columns populate per union (columns 12-13 of Uniones)
- **REPAR-01**: Reparación tracks cycles per union (not per spool) with independent cycle counters

### Analytics & Dashboards

- **DASH-01**: Supervisor dashboard shows pulgadas-diámetro trends over time
- **DASH-02**: Worker performance leaderboard by pulgadas-diámetro/day
- **DASH-03**: Bottleneck detection based on avg union completion time (ARM vs SOLD)

### Advanced Workflows

- **BATCH-01**: Multi-spool INICIAR (take 5 spools at once for batch processing)
- **FILTER-01**: SSE endpoints add STATUS_NV and Status_Spool filters for advanced dashboards

## Out of Scope

Explicitly excluded to prevent scope creep.

| Feature | Reason |
|---------|--------|
| Creating unions from app | Uniones sheet pre-populated by Engineering external process (spec S1) |
| Deleting unions from app | Engineering manages union lifecycle, app is read/update only |
| Editing historical union data | Metadata audit trail must remain immutable (regulatory requirement) |
| Real-time SSE for union completion | Adds complexity, spool-level SSE sufficient for v4.0 MVP |
| Automatic FINALIZAR on timeout | Manual control only, prevents accidental work loss during breaks |
| Complex role hierarchies for unions | Flat role system (Armador, Soldador) sufficient, no supervisor approval |

## Traceability

Which phases cover which requirements. Updated during roadmap creation.

| Requirement | Phase | Status |
|-------------|-------|--------|
| (to be filled by roadmapper) | - | - |

**Coverage:**
- v4.0 requirements: 63 total
- Mapped to phases: 0 (roadmap not created yet)
- Unmapped: 63 ⚠️

---
*Requirements defined: 2026-01-30*
*Last updated: 2026-01-30 after initial definition*
