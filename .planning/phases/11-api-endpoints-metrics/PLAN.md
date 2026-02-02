# Phase 11: API Endpoints & Metrics - Master Plan

**Phase Goal:** REST API exposes union workflows with INICIAR/FINALIZAR endpoints and maintains v3.0 compatibility

**Success Criteria:**
1. GET /api/v4/uniones/{tag}/disponibles?operacion=ARM|SOLD returns filtered unions based on operation type
2. GET /api/v4/uniones/{tag}/metricas returns aggregated metrics (total_uniones, arm_completadas, sold_completadas, pulgadas_arm, pulgadas_sold)
3. POST /api/v4/occupation/iniciar occupies spool with Redis lock without modifying Uniones sheet
4. POST /api/v4/occupation/finalizar accepts selected_unions array and auto-determines PAUSAR or COMPLETAR
5. v3.0 endpoints (/tomar, /pausar, /completar) remain functional at new /api/v3/ prefix for backward compatibility
6. Metadata logs 1 batch event (spool level) plus N granular events (union level) per FINALIZAR operation
7. Dashboard displays pulgadas-diámetro as primary metric instead of spool count

## Plans Overview

| Plan | Title | Wave | Dependencies | Focus |
|------|-------|------|--------------|--------|
| 11-01 | API Versioning & V3 Migration | 1 | None | Relocate v3.0 endpoints to /api/v3/ prefix, setup router structure |
| 11-02 | Union Query Endpoints | 2 | 11-01 | Implement disponibles and metricas read-only queries |
| 11-03 | INICIAR Workflow Endpoint | 2 | 11-01 | Create v4.0 spool occupation endpoint |
| 11-04 | FINALIZAR Workflow Endpoint | 3 | 11-03 | Implement union selection and auto-determination |
| 11-05 | Integration Tests & Validation | 3 | 11-04 | Comprehensive testing and performance validation |
| 11-06 | Fix Metadata Batch + Granular Logging (Gap) | 1 | 11-05 | Fix missing N union-level metadata events in FINALIZAR |

## Key Technical Decisions (from CONTEXT.md)

1. **Explicit versioning**: `/api/v3/...` and `/api/v4/...` prefixes
2. **Resource organization**: Union queries under `/uniones/`, actions under `/occupation/`
3. **Minimal payloads**: Backend derives worker_nombre from worker_id lookup
4. **Race condition handling**: 409 CONFLICT for unavailable unions
5. **Metrics precision**: 2 decimals for pulgadas (storage precision)
6. **No caching initially**: Always-fresh reads, consistent with Phase 10

## Requirements Mapping

| Requirement | Plan | Implementation |
|------------|------|----------------|
| API-01 | 11-02 | GET disponibles?operacion=ARM filter |
| API-02 | 11-02 | GET disponibles?operacion=SOLD filter |
| API-03 | 11-02 | GET metricas with 5 fields |
| API-04 | 11-03 | POST iniciar endpoint |
| API-05 | 11-04 | POST finalizar endpoint |
| API-06 | 11-01 | v3.0 endpoints relocated |
| METRIC-01 | 11-02 | Pulgadas in metrics response |
| METRIC-02 | 11-02 | Performance calculation support |
| METRIC-03-09 | (Phase 10) | Already implemented in UnionService |

## Validation Approach

1. **Unit tests**: Router-level validation (test_union_router_v4.py)
2. **Integration tests**: End-to-end API workflows
3. **Performance tests**: < 1s for 10-union operations
4. **Manual validation**: Version detection, race conditions
5. **Frontend compatibility**: v3.0 endpoints still functional

---

*Generated: 2026-02-02*
*Phase: 11 of 13*
*Previous: Phase 10 (Backend Services & Validation) - Complete*
*Next: Phase 12 (Frontend Integration & UX)*