# Phase 11: API Endpoints & Metrics - Context

**Gathered:** 2026-02-02
**Status:** Ready for planning

<domain>
## Phase Boundary

REST API layer that exposes union-level workflows (INICIAR/FINALIZAR) and metrics endpoints while maintaining backward compatibility with v3.0 spool-level endpoints. This phase creates the HTTP interface for v4.0 union workflows. Frontend integration and UX are Phase 12.

</domain>

<decisions>
## Implementation Decisions

### Endpoint structure & versioning
- **v4.0 endpoints use `/api/v4/...` prefix** (explicit versioning)
- **v3.0 endpoints move to `/api/v3/...`** (TOMAR, PAUSAR, COMPLETAR relocated)
- **Union queries under `/api/v4/uniones/{tag}/...`** path structure
  - Example: `GET /api/v4/uniones/TEST-01/disponibles?operacion=ARM`
- **Actions under `/api/v4/occupation/...`** separate from queries
  - `POST /api/v4/occupation/iniciar` (tag in payload)
  - `POST /api/v4/occupation/finalizar` (tag in payload)

### Request/response schemas
- **INICIAR payload: minimal fields** (tag_spool, worker_id, operacion)
  - worker_nombre derived from backend lookup (avoid redundant data)
- **FINALIZAR payload: array of union IDs** (selected_unions: ['uuid-1', 'uuid-2'])
  - Simple structure, frontend tracks UUIDs from disponibles query
- **FINALIZAR response: include completion stats**
  - `{action: 'PAUSAR'|'COMPLETAR', completadas: 7, total: 10, pulgadas: 18.5, message: '...'}`
- **Disponibles response: core fields only** (id, n_union, dn_union, tipo_union)
  - Minimal data for checkbox display in P5

### Error handling & status codes
- **v3.0 spool calling v4.0 endpoint → 400 Bad Request**
  - Error message: "Spool is v3.0, use /api/v3/occupation/tomar instead"
- **ARM-before-SOLD validation failure → 403 Forbidden**
  - Consistent with Phase 10 ValidationService implementation
- **Validation errors → field-level details**
  - Format: `{errors: [{field: 'selected_unions', message: 'Union ID uuid-x not found'}]}`
  - Detailed error messages for debugging (not simple "Invalid request")
- **Race condition (selected > disponibles) → Claude's discretion**
  - Choose 409 Conflict vs 400 Bad Request based on REST semantics

### Metrics endpoint design
- **Spool-level metrics only** (no worker/operation aggregation in this phase)
  - `GET /api/v4/uniones/{tag}/metricas` returns metrics for single spool
- **Match success criteria exactly** (5 fields)
  - total_uniones, arm_completadas, sold_completadas, pulgadas_arm, pulgadas_sold
  - No percentages or union type breakdowns
- **2 decimal precision for pulgadas** (matches repository storage, D32)
  - Example: pulgadas_arm: 18.50 (not 18.5)
- **Caching strategy → Claude's discretion**
  - Choose between always-fresh (Phase 10 D33 pattern) vs TTL cache based on performance needs

</decisions>

<specifics>
## Specific Ideas

- v3.0 endpoints require frontend update after relocation to /api/v3/...
- Separation of union queries (/api/v4/uniones/...) from actions (/api/v4/occupation/...) follows RESTful resource organization
- Precision decision (2 decimals) differs from Phase 10 UnionService (1 decimal) — API layer prefers storage precision over presentation precision

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 11-api-endpoints-metrics*
*Context gathered: 2026-02-02*
