# Phase 11: API Endpoints & Metrics - Research Findings

**Research Date:** 2026-02-02
**Phase Goal:** REST API layer exposing union-level workflows (INICIAR/FINALIZAR) and metrics endpoints with v3.0 backward compatibility

## Executive Summary

Phase 11 builds the HTTP interface layer for v4.0 union workflows established in Phase 10. The key architectural decisions from CONTEXT.md guide this implementation:

- **Explicit versioning** via `/api/v3/...` and `/api/v4/...` prefixes
- **Separation of concerns**: Union queries under `/uniones/`, actions under `/occupation/`
- **Minimal payloads**: Backend derives data (worker_nombre lookup, disponibles filtering)
- **Detailed error responses**: Field-level validation errors for debugging
- **Spool-level metrics only** (no aggregation in this phase)

Phase 10 completed the business logic layer (UnionService, OccupationService, ValidationService). This phase wraps that logic with RESTful endpoints and proper HTTP semantics.

---

## 1. Current Architecture Analysis

### 1.1 Existing Router Patterns (v3.0)

**Current v3.0 endpoints** (occupation.py):
```python
POST /api/occupation/tomar           # TomarRequest → StateService.tomar()
POST /api/occupation/pausar          # PausarRequest → StateService.pausar()
POST /api/occupation/completar       # CompletarRequest → StateService.completar()
POST /api/occupation/batch-tomar     # BatchTomarRequest → OccupationService.batch_tomar()
```

**Key patterns identified:**
1. **Exception mapping**: ZEUSException → HTTP status codes in main.py global handler
   - `SpoolOccupiedError` → 409 CONFLICT
   - `NoAutorizadoError` → 403 FORBIDDEN
   - `ArmPrerequisiteError` → 403 FORBIDDEN (Phase 10)
   - `DependenciasNoSatisfechasError` → 400 BAD REQUEST

2. **Validation errors**: Pydantic models throw 422 UNPROCESSABLE ENTITY automatically

3. **Response model**: `OccupationResponse` with success/message/optional fields
   ```python
   class OccupationResponse:
       success: bool
       tag_spool: str
       message: str
       action_taken: Optional[str]  # v4.0: "PAUSAR"/"COMPLETAR"/"CANCELADO"
       unions_processed: Optional[int]  # v4.0: count of unions
   ```

4. **Dependency injection**: Services injected via `Depends(get_*)` pattern

### 1.2 Phase 10 Service Layer (Backend Logic)

**OccupationService** (occupation_service.py):
- Lines 720-914: `iniciar_spool(IniciarRequest)` - v4.0 INICIAR implementation
  - Validates prerequisites (Fecha_Materiales, ARM for SOLD)
  - Acquires persistent Redis lock (no TTL)
  - Updates Ocupado_Por + Fecha_Ocupacion
  - Does NOT touch Uniones sheet

- Lines 1030-1423: `finalizar_spool(FinalizarRequest)` - v4.0 FINALIZAR implementation
  - Verifies lock ownership
  - Handles zero-union cancellation (logs SPOOL_CANCELADO event)
  - Auto-determines PAUSAR vs COMPLETAR based on selected vs total
  - Calls UnionService.process_selection() for batch updates
  - Triggers metrología auto-transition if 100% complete

- Lines 916-954: `_determine_action()` - Auto-determination logic
  ```python
  if selected_count == total_available:
      return "COMPLETAR"
  else:
      return "PAUSAR"
  # Raises ValueError if selected_count > total_available (race condition)
  ```

- Lines 956-1028: `should_trigger_metrologia()` - Metrología detection
  - FW unions: All must have ARM_FECHA_FIN != NULL
  - SOLD-required unions: All must have SOL_FECHA_FIN != NULL

**UnionService** (union_service.py):
- Lines 60-184: `process_selection()` - Batch orchestration
  - Returns: `{union_count, action, pulgadas, event_count}`
  - pulgadas rounded to 1 decimal (line 182)

- Lines 186-221: `calcular_pulgadas()` - DN_UNION summation
  - Returns 1 decimal precision (line 221)
  - Handles None values gracefully

**ValidationService** (validation_service.py):
- Lines 189-263: `validar_puede_completar_metrologia()` - v3.0 prerequisite checks
- Lines 265-322: `validar_puede_tomar_reparacion()` - v3.0 Phase 6
- Phase 10 added: `validate_arm_prerequisite()` - ARM-before-SOLD validation
  - Raises `ArmPrerequisiteError` (403 FORBIDDEN)
  - Used in OccupationService.iniciar_spool() line 776-789

### 1.3 Existing Models (Pydantic Schemas)

**occupation.py models**:
```python
class IniciarRequest(BaseModel):        # Lines 351-394
    tag_spool: str
    worker_id: int
    worker_nombre: str
    operacion: ActionType  # ARM or SOLD

class FinalizarRequest(BaseModel):      # Lines 397-455
    tag_spool: str
    worker_id: int
    worker_nombre: str
    operacion: ActionType
    selected_unions: list[str]  # Empty list = cancellation

class OccupationResponse(BaseModel):    # Lines 214-265
    success: bool
    tag_spool: str
    message: str
    action_taken: Optional[str]         # v4.0
    unions_processed: Optional[int]     # v4.0
    metrologia_triggered: Optional[bool] # v4.0
    new_state: Optional[str]            # v4.0
```

**union.py model** (lines 12-194):
```python
class Union(BaseModel):
    id: str                              # Composite PK: "{TAG_SPOOL}+{N_UNION}"
    ot: str
    tag_spool: str
    n_union: int                         # 1-20
    dn_union: float                      # Diameter in inches
    tipo_union: str                      # BW, BR, SO, FW, FILL, LET
    arm_fecha_inicio: Optional[datetime]
    arm_fecha_fin: Optional[datetime]
    arm_worker: Optional[str]
    sol_fecha_inicio: Optional[datetime]
    sol_fecha_fin: Optional[datetime]
    sol_worker: Optional[str]
    # ... NDT fields, audit fields
```

### 1.4 Error Handling Infrastructure

**main.py global exception handler** (lines 127-200):
```python
@app.exception_handler(ZEUSException)
async def zeus_exception_handler(request: Request, exc: ZEUSException):
    status_map = {
        "SPOOL_NO_ENCONTRADO": 404,
        "OPERACION_YA_INICIADA": 400,
        "NO_AUTORIZADO": 403,
        "SPOOL_OCCUPIED": 409,
        "VERSION_CONFLICT": 409,
        "LOCK_EXPIRED": 410,
        "SPOOL_BLOQUEADO": 403,
        "SHEETS_UPDATE_ERROR": 503
        # ... more mappings
    }
```

**Exception classes** (exceptions.py grep output):
- `SpoolNoEncontradoError` (line 30)
- `NoAutorizadoError` (line 152) - Ownership violations
- `SpoolOccupiedError` (line 264) - Race conditions
- `VersionConflictError` (line 286) - Optimistic locking failures
- `ArmPrerequisiteError` (line 396) - Phase 10 new exception
- `DependenciasNoSatisfechasError` (line 90)
- `SheetsUpdateError` (line 237)

---

## 2. Implementation Knowledge Base

### 2.1 Endpoint Structure & Versioning

**Decision from CONTEXT.md:**
- v4.0 endpoints: `/api/v4/...` prefix
- v3.0 endpoints: Relocate to `/api/v3/...` (TOMAR, PAUSAR, COMPLETAR)
- Union queries: `/api/v4/uniones/{tag}/...`
- Actions: `/api/v4/occupation/...`

**Current v3.0 routes** (need relocation):
```
/api/occupation/tomar       → /api/v3/occupation/tomar
/api/occupation/pausar      → /api/v3/occupation/pausar
/api/occupation/completar   → /api/v3/occupation/completar
/api/occupation/batch-tomar → /api/v3/occupation/batch-tomar
```

**New v4.0 routes** (to create):
```
GET  /api/v4/uniones/{tag}/disponibles?operacion=ARM|SOLD
GET  /api/v4/uniones/{tag}/metricas
POST /api/v4/occupation/iniciar
POST /api/v4/occupation/finalizar
```

**Why this matters:**
1. Explicit versioning prevents breaking changes for v3.0 frontend
2. Separation of queries vs actions follows REST best practices
3. Path parameters (`{tag}`) vs query params (`?operacion=...`) per RESTful conventions

### 2.2 Request/Response Schemas

**INICIAR endpoint** (POST /api/v4/occupation/iniciar):

```python
# Request (minimal fields per decision)
{
  "tag_spool": "TEST-02",
  "worker_id": 93,
  "operacion": "ARM"
}
# worker_nombre derived by backend (lookup from worker_id)

# Response (success)
{
  "success": true,
  "tag_spool": "TEST-02",
  "message": "Spool TEST-02 iniciado por MR(93)"
}

# Response (403 - ARM prerequisite failure for SOLD)
{
  "success": false,
  "error": "ARM_PREREQUISITE",
  "message": "Cannot start SOLD: No ARM unions completed for spool TEST-02"
}
```

**FINALIZAR endpoint** (POST /api/v4/occupation/finalizar):

```python
# Request (array of union IDs)
{
  "tag_spool": "TEST-02",
  "worker_id": 93,
  "operacion": "ARM",
  "selected_unions": ["TEST-02+1", "TEST-02+2", "TEST-02+3"]
}

# Response (PAUSAR - partial completion)
{
  "success": true,
  "tag_spool": "TEST-02",
  "message": "Trabajo pausado - 3 uniones procesadas",
  "action_taken": "PAUSAR",
  "unions_processed": 3,
  "pulgadas": 18.5
}

# Response (COMPLETAR - full completion)
{
  "success": true,
  "tag_spool": "TEST-02",
  "message": "Operación completada - 10 uniones procesadas (Listo para metrología)",
  "action_taken": "COMPLETAR",
  "unions_processed": 10,
  "pulgadas": 45.2,
  "metrologia_triggered": true
}
```

**DISPONIBLES query** (GET /api/v4/uniones/{tag}/disponibles?operacion=ARM):

```python
# Response (core fields only per decision)
{
  "tag_spool": "TEST-02",
  "operacion": "ARM",
  "unions": [
    {
      "id": "TEST-02+1",
      "n_union": 1,
      "dn_union": 6.0,
      "tipo_union": "BW"
    },
    {
      "id": "TEST-02+2",
      "n_union": 2,
      "dn_union": 4.5,
      "tipo_union": "FW"
    }
    // ... more unions
  ]
}
```

**METRICAS query** (GET /api/v4/uniones/{tag}/metricas):

```python
# Response (5 fields matching success criteria)
{
  "tag_spool": "TEST-02",
  "total_uniones": 10,
  "arm_completadas": 7,
  "sold_completadas": 5,
  "pulgadas_arm": 18.50,    # 2 decimal precision per decision
  "pulgadas_sold": 12.75
}
```

### 2.3 Error Handling & Status Codes

**Validation errors** (Pydantic automatic):
```python
# Request: {"tag_spool": "TEST-02", "worker_id": 93}  # Missing operacion
# Response: 422 UNPROCESSABLE ENTITY
{
  "detail": [
    {
      "type": "missing",
      "loc": ["body", "operacion"],
      "msg": "Field required",
      "input": {...}
    }
  ]
}
```

**Business rule violations** (from service layer):
```python
# CONTEXT.md decision: Field-level error details
{
  "success": false,
  "error": "VALIDATION_ERROR",
  "message": "Invalid request data",
  "errors": [
    {
      "field": "selected_unions",
      "message": "Union ID TEST-02+999 not found for this spool"
    }
  ]
}
```

**HTTP status code mapping** (from CONTEXT.md + exception handler):
- **400 Bad Request**: Invalid spool version (v3.0 spool calls v4.0 endpoint)
- **403 Forbidden**: ARM prerequisite failure for SOLD (ArmPrerequisiteError)
- **404 Not Found**: Spool or union not found
- **409 Conflict**: Race condition (selected > disponibles) - **NEED TO DECIDE** 409 vs 400
- **503 Service Unavailable**: Google Sheets API failures

**Key insight from CONTEXT.md:**
> "v3.0 spool calling v4.0 endpoint → 400 Bad Request"
> "Error message: 'Spool is v3.0, use /api/v3/occupation/tomar instead'"

This requires **version detection** logic in v4.0 endpoint handlers. Options:
1. Check `Total_Uniones` column (68): if NULL or 0 → v3.0 spool
2. Query Uniones sheet: if no rows for TAG_SPOOL → v3.0 spool
3. Use diagnostic endpoint pattern (see diagnostic.py router)

### 2.4 Metrics Endpoint Design

**Decision from CONTEXT.md:**
- Spool-level metrics only (no worker/operation aggregation)
- 5 fields matching success criteria
- 2 decimal precision (storage precision, not presentation)

**Data source options:**

**Option A: Read from Operaciones columns 68-72** (Phase 7 schema):
```python
# Operaciones sheet columns:
# 68: Total_Uniones
# 69: Uniones_ARM_Completadas
# 70: Uniones_SOLD_Completadas
# 71: Pulgadas_ARM
# 72: Pulgadas_SOLD

# Advantage: Single Sheets read, pre-calculated
# Disadvantage: Stale if Uniones updated but Operaciones not synced
```

**Option B: Calculate from Uniones sheet** (Phase 10 D33 pattern):
```python
# Query Uniones sheet by TAG_SPOOL
unions = union_repo.get_by_spool(tag_spool)

# Calculate fresh metrics
total = len(unions)
arm_completadas = sum(1 for u in unions if u.arm_fecha_fin is not None)
sold_completadas = sum(1 for u in unions if u.sol_fecha_fin is not None)
pulgadas_arm = sum(u.dn_union for u in unions if u.arm_fecha_fin is not None)
pulgadas_sold = sum(u.dn_union for u in unions if u.sol_fecha_fin is not None)

# Advantage: Always fresh (Phase 10 D33 "always-fresh reads")
# Disadvantage: Slower (Uniones sheet query + calculation)
```

**Recommendation:** Option B (always-fresh) per Phase 10 D33 decision:
> "Read fresh from Uniones sheet when querying disponibles (no caching, prevent stale data races)"

**Caching strategy:** CONTEXT.md leaves this to Claude's discretion. Options:
1. **No cache** (always-fresh) - Consistent with Phase 10 D33 for disponibles queries
2. **Short TTL cache** (5-10s) - Reduce load for dashboard polling
3. **Cache invalidation** - Clear on FINALIZAR completion

**Recommendation:** Start with **no cache** (Option 1) for consistency with Phase 10. Can add TTL cache in performance optimization phase if needed.

### 2.5 Integration with Phase 10 Services

**Service dependencies:**
```python
# Router needs these services (dependency injection):
from backend.core.dependency import (
    get_occupation_service,     # OccupationService (v3.0 + v4.0)
    get_union_service,          # UnionService (Phase 10)
    get_validation_service,     # ValidationService (v2.1 + Phase 10)
    get_union_repository        # UnionRepository (Phase 8)
)

# New router structure:
class UnionV4Router:
    def __init__(
        self,
        occupation_service: OccupationService,
        union_service: UnionService,
        union_repository: UnionRepository
    ):
        ...
```

**Flow for INICIAR endpoint:**
```
1. Parse IniciarRequest (Pydantic validation)
2. Derive worker_nombre from worker_id (WorkerRepository lookup)
3. Call occupation_service.iniciar_spool()
   - Validates prerequisites (Fecha_Materiales, ARM for SOLD)
   - Acquires Redis lock
   - Updates Operaciones.Ocupado_Por
   - Logs TOMAR_SPOOL event
4. Return OccupationResponse
```

**Flow for FINALIZAR endpoint:**
```
1. Parse FinalizarRequest (Pydantic validation)
2. Call occupation_service.finalizar_spool()
   - Verifies lock ownership
   - If selected_unions empty: cancellation flow
   - Else: batch update via union_service.process_selection()
   - Auto-determines PAUSAR vs COMPLETAR
   - Triggers metrología if 100% complete
3. Return OccupationResponse with action_taken, unions_processed, pulgadas
```

**Flow for DISPONIBLES query:**
```
1. Parse tag_spool (path param) and operacion (query param)
2. Get spool by TAG_SPOOL to extract OT
3. Call union_repository.get_disponibles_arm_by_ot(ot) or get_disponibles_sold_by_ot(ot)
4. Build response with minimal fields (id, n_union, dn_union, tipo_union)
5. Return DisponiblesResponse
```

**Flow for METRICAS query:**
```
1. Parse tag_spool (path param)
2. Call union_repository.get_by_spool(tag_spool)
3. Calculate metrics:
   - total_uniones = len(unions)
   - arm_completadas = count where arm_fecha_fin != None
   - sold_completadas = count where sol_fecha_fin != None
   - pulgadas_arm = sum(dn_union) where arm_fecha_fin != None
   - pulgadas_sold = sum(dn_union) where sol_fecha_fin != None
4. Format pulgadas to 2 decimals
5. Return MetricasResponse
```

---

## 3. Technical Constraints & Considerations

### 3.1 Backward Compatibility (v3.0 vs v4.0)

**From PROJECT.md requirement COMPAT-01:**
> "Frontend detects spool version by union count (count > 0 = v4.0, count = 0 = v3.0)"

**Implementation options for v4.0 endpoint protection:**

**Option A: Check Total_Uniones column** (Operaciones column 68):
```python
@router.post("/v4/occupation/iniciar")
async def iniciar_v4(request: IniciarRequest):
    spool = sheets_repo.get_spool_by_tag(request.tag_spool)

    # Check if v3.0 spool (no unions)
    if spool.total_uniones is None or spool.total_uniones == 0:
        raise HTTPException(
            status_code=400,
            detail="Spool is v3.0, use /api/v3/occupation/tomar instead"
        )

    # Continue with v4.0 logic
    return await occupation_service.iniciar_spool(request)
```

**Option B: Query Uniones sheet:**
```python
# More accurate but slower (extra Sheets query)
unions = union_repo.get_by_spool(request.tag_spool)
if len(unions) == 0:
    raise HTTPException(status_code=400, detail="...")
```

**Recommendation:** Option A (check Total_Uniones column) - Faster, single Sheets read already happening.

**Frontend compatibility impact:**
- Frontend MUST continue calling v3.0 endpoints for v3.0 spools
- Frontend MUST call v4.0 endpoints for v4.0 spools
- This phase does NOT modify frontend (Phase 12)
- Backend provides clear error messages if wrong endpoint called

### 3.2 Performance Considerations

**Google Sheets API limits** (from CLAUDE.md):
- 60 writes/min/user
- 200-500ms latency per request
- 300 reads/100s/user quota

**Phase 10 batch operations** (Phase 10 PLAN.md D3):
> "Batch writes using gspread.batch_update() (critical for < 1s performance target)"

**v4.0 performance requirements** (PERF-02 from PROJECT.md):
> "System achieves < 1s latency (p95) for 10-union selection operation"

**Phase 10 VERIFICATION.md results:**
```
✓ Performance validation passed
- 10-union batch update: 0.85s (target: < 1s)
- Union selection processing: 0.92s
- Metadata batch logging: 0.3s
```

**Implications for API endpoints:**
1. **INICIAR**: Fast (~200ms) - Single Sheets write (Ocupado_Por + Fecha_Ocupacion)
2. **FINALIZAR**: ~1s for 10 unions - Already optimized in Phase 10
3. **DISPONIBLES query**: ~300ms - Single Sheets read (Uniones sheet)
4. **METRICAS query**: ~300ms - Single Sheets read (Uniones sheet)

**No additional optimization needed** - Phase 10 batch operations already meet performance targets.

### 3.3 Race Conditions & Edge Cases

**From CONTEXT.md decision:**
> "Race condition (selected > disponibles) → Claude's discretion: 409 Conflict vs 400 Bad Request"

**Scenario: Union becomes unavailable between query and submission**
```
1. Frontend queries GET /api/v4/uniones/TEST-02/disponibles?operacion=ARM
   Response: [{id: "TEST-02+1"}, {id: "TEST-02+2"}, {id: "TEST-02+3"}]

2. User selects 3 unions in checkbox UI

3. Meanwhile, another worker completes union TEST-02+2

4. Frontend submits POST /api/v4/occupation/finalizar
   selected_unions: ["TEST-02+1", "TEST-02+2", "TEST-02+3"]

5. Backend validation: union TEST-02+2 no longer available
```

**HTTP semantics:**
- **409 Conflict**: "Request conflicts with current state of resource"
  - Pro: Semantically correct (state changed between GET and POST)
  - Pro: Distinguishes from 400 Bad Request (malformed input)

- **400 Bad Request**: "Invalid request data"
  - Con: Less specific than 409
  - Con: Doesn't indicate race condition explicitly

**Recommendation: 409 Conflict** with detailed error message:
```python
{
  "success": false,
  "error": "RACE_CONDITION",
  "message": "1 union no longer available (completed by another worker)",
  "data": {
    "unavailable_unions": ["TEST-02+2"],
    "available_count": 2,
    "requested_count": 3
  }
}
```

**Handling strategy:**
```python
# In union_service.process_selection() (line 123-131)
available_unions = self.filter_available_unions(selected_unions, operacion)
if len(available_unions) != len(selected_unions):
    unavailable_count = len(selected_unions) - len(available_unions)
    # Don't fail completely - process available unions only
    # Frontend should refetch disponibles and retry
    logger.warning(f"{unavailable_count} unions unavailable, processing {len(available_unions)}")
    # Update selected_unions to only available ones
```

This is **already implemented in Phase 10** (lines 123-132). The router just needs to handle the case gracefully.

### 3.4 Version Detection & Routing

**Diagnostic router pattern** (diagnostic.py lines 36-80):
```python
@router.get("/{tag}/version")
async def get_version(tag: str):
    # Uses union count to determine v3.0 vs v4.0
    ...
```

**Need for v4.0 endpoints:**
```python
def is_v4_spool(spool: Spool) -> bool:
    """Detect if spool is v4.0 (has unions) or v3.0 (no unions)."""
    return spool.total_uniones is not None and spool.total_uniones > 0
```

**Router protection pattern:**
```python
@router.post("/v4/occupation/iniciar")
async def iniciar_v4(request: IniciarRequest):
    spool = sheets_repo.get_spool_by_tag(request.tag_spool)

    if not is_v4_spool(spool):
        raise HTTPException(
            status_code=400,
            detail={
                "error": "WRONG_VERSION",
                "message": "Spool is v3.0, use /api/v3/occupation/tomar instead",
                "spool_version": "v3.0",
                "correct_endpoint": "/api/v3/occupation/tomar"
            }
        )
```

---

## 4. Open Questions & Decisions Needed

### 4.1 Claude's Discretion Items from CONTEXT.md

**1. Race condition HTTP status (selected > disponibles)**
- **Options:** 409 Conflict vs 400 Bad Request
- **Recommendation:** 409 Conflict (see Section 3.3)
- **Rationale:** More semantically correct, distinguishes from malformed input

**2. Metrics caching strategy**
- **Options:** Always-fresh (no cache) vs TTL cache vs invalidation
- **Recommendation:** No cache initially (consistent with Phase 10 D33)
- **Rationale:** Simplicity, correctness over performance. Can optimize later if needed.

### 4.2 Implementation Details

**1. Worker name derivation**
- **Context:** CONTEXT.md decision: "worker_nombre derived from backend lookup"
- **Current pattern:** occupation.py uses `worker_nombre` in request body
- **Options:**
  - A. Keep worker_nombre in request (simpler, no DB lookup)
  - B. Remove worker_nombre from request, lookup in router
- **Recommendation:** Keep worker_nombre in request (Option A)
- **Rationale:** Consistent with v3.0 pattern, avoids extra Sheets lookup

**2. Endpoint consolidation**
- **Question:** Should INICIAR/FINALIZAR be in occupation.py or new union_router.py?
- **Recommendation:** Create new `backend/routers/union_router.py` for v4.0 endpoints
- **Rationale:** Clean separation, avoid conflicts with v3.0 routes during migration

**3. Response format for FINALIZAR**
- **Question:** Should response include pulgadas field?
- **Current:** Phase 10 doesn't return pulgadas in OccupationResponse
- **Recommendation:** Add pulgadas to response (optional field)
- **Rationale:** Frontend needs this for immediate feedback (Success criteria mentions it)

**4. URL path structure**
- **Question:** `/api/v4/uniones/{tag}/disponibles` vs `/api/v4/disponibles/{tag}`?
- **Recommendation:** `/api/v4/uniones/{tag}/disponibles` (resource-first)
- **Rationale:** RESTful convention - resource noun first, action second

---

## 5. Testing Strategy

### 5.1 Unit Tests Required

**Router-level tests** (new file: `tests/unit/routers/test_union_router_v4.py`):
```python
# INICIAR endpoint
- test_iniciar_success_arm()
- test_iniciar_success_sold()
- test_iniciar_403_arm_prerequisite()  # SOLD without ARM
- test_iniciar_400_v3_spool()          # v3.0 spool calls v4.0 endpoint
- test_iniciar_409_spool_occupied()
- test_iniciar_422_missing_operacion() # Pydantic validation

# FINALIZAR endpoint
- test_finalizar_pausar_success()      # Partial completion
- test_finalizar_completar_success()   # Full completion
- test_finalizar_cancelado_success()   # Zero unions selected
- test_finalizar_403_not_owner()       # Worker doesn't own lock
- test_finalizar_409_race_condition()  # Union became unavailable
- test_finalizar_metrologia_triggered() # Auto-transition to metrología

# DISPONIBLES query
- test_disponibles_arm_success()
- test_disponibles_sold_filtered()     # Only ARM-completed unions
- test_disponibles_404_spool_not_found()
- test_disponibles_400_invalid_operacion()

# METRICAS query
- test_metricas_success()
- test_metricas_2_decimal_precision()
- test_metricas_404_spool_not_found()
```

### 5.2 Integration Tests Required

**API-level tests** (new file: `tests/integration/test_union_api_v4.py`):
```python
# End-to-end workflows
- test_iniciar_finalizar_pausar_flow()
- test_iniciar_finalizar_completar_flow()
- test_iniciar_finalizar_cancelar_flow()
- test_sold_requires_arm_prerequisite()
- test_metrologia_auto_trigger()
- test_race_condition_handling()

# Version detection
- test_v3_spool_rejects_v4_endpoint()
- test_v4_spool_rejects_v3_endpoint()  # Optional: guard v3.0 endpoints

# Performance validation
- test_finalizar_10_unions_under_1s()  # PERF-02 requirement
```

### 5.3 Manual Testing Checklist

```
□ Test INICIAR ARM on v4.0 spool (success)
□ Test INICIAR SOLD without ARM (403 failure)
□ Test INICIAR SOLD after ARM (success)
□ Test FINALIZAR with 3/10 unions (PAUSAR response)
□ Test FINALIZAR with 10/10 unions (COMPLETAR response)
□ Test FINALIZAR with 0 unions (CANCELADO response)
□ Test disponibles query filters ARM-completed for SOLD
□ Test metricas query returns 5 fields with 2 decimals
□ Test v3.0 spool calling v4.0 endpoint (400 error)
□ Test concurrent FINALIZAR (race condition handling)
```

---

## 6. File Changes Summary

### New Files to Create

1. **`backend/routers/union_router.py`** - v4.0 union endpoints
   - POST /api/v4/occupation/iniciar
   - POST /api/v4/occupation/finalizar
   - GET /api/v4/uniones/{tag}/disponibles
   - GET /api/v4/uniones/{tag}/metricas

2. **`backend/routers/occupation_v3.py`** - v3.0 relocated endpoints
   - POST /api/v3/occupation/tomar
   - POST /api/v3/occupation/pausar
   - POST /api/v3/occupation/completar
   - POST /api/v3/occupation/batch-tomar

3. **`backend/models/union_api.py`** - v4.0 request/response models
   - DisponiblesResponse
   - MetricasResponse
   - (IniciarRequest/FinalizarRequest already exist in occupation.py)

4. **`tests/unit/routers/test_union_router_v4.py`** - Router unit tests

5. **`tests/integration/test_union_api_v4.py`** - API integration tests

### Files to Modify

1. **`backend/main.py`** - Register new routers
   ```python
   from backend.routers import union_router, occupation_v3
   app.include_router(union_router.router, prefix="/api/v4", tags=["v4-unions"])
   app.include_router(occupation_v3.router, prefix="/api/v3", tags=["v3-occupation"])
   ```

2. **`backend/core/dependency.py`** - Add get_union_router dependencies

3. **`backend/models/occupation.py`** - Add pulgadas field to OccupationResponse
   ```python
   pulgadas: Optional[float] = Field(None, description="Total pulgadas-diámetro procesadas")
   ```

4. **`backend/exceptions.py`** - Add WRONG_VERSION error code (optional)

---

## 7. Implementation Roadmap (3-Wave Structure)

### Wave 1: Version Detection & Routing (10-15 min)
**Goal:** Establish URL versioning and version detection logic

1. Create `backend/routers/union_router.py` skeleton
2. Add `is_v4_spool()` helper function
3. Relocate v3.0 endpoints to `occupation_v3.py`
4. Register routers in main.py with `/api/v3/` and `/api/v4/` prefixes
5. Add version detection guard to INICIAR endpoint

**Dependencies:** None
**Validation:** Version detection test passes, v3.0 endpoints still work

### Wave 2: Union Query Endpoints (15-20 min)
**Goal:** Implement read-only disponibles and metricas queries

**Plan 11-01: DISPONIBLES Query Endpoint**
- GET /api/v4/uniones/{tag}/disponibles?operacion=ARM|SOLD
- Parse path param (tag) and query param (operacion)
- Get spool by TAG_SPOOL, extract OT
- Call union_repository.get_disponibles_{arm|sold}_by_ot()
- Build DisponiblesResponse with core fields only
- Handle 404 NOT FOUND if spool doesn't exist

**Plan 11-02: METRICAS Query Endpoint**
- GET /api/v4/uniones/{tag}/metricas
- Call union_repository.get_by_spool(tag)
- Calculate 5 metrics fields
- Format pulgadas to 2 decimals
- Return MetricasResponse
- Handle 404 NOT FOUND if spool doesn't exist

**Dependencies:** Wave 1 (router structure)
**Validation:** Query tests pass, response format matches success criteria

### Wave 3: Union Action Endpoints (20-25 min)
**Goal:** Implement INICIAR/FINALIZAR with orchestration

**Plan 11-03: INICIAR Endpoint**
- POST /api/v4/occupation/iniciar
- Parse IniciarRequest
- Version detection guard (reject v3.0 spools)
- Call occupation_service.iniciar_spool()
- Map exceptions to HTTP status codes
- Return OccupationResponse

**Plan 11-04: FINALIZAR Endpoint**
- POST /api/v4/occupation/finalizar
- Parse FinalizarRequest
- Version detection guard
- Call occupation_service.finalizar_spool()
- Extract pulgadas from service response (if available)
- Add pulgadas to OccupationResponse
- Handle race conditions (409 CONFLICT)
- Return OccupationResponse with action_taken, unions_processed, pulgadas

**Dependencies:** Wave 2 (models created)
**Validation:** Integration tests pass, auto-determination works correctly

---

## 8. Key Decisions Summary

| Decision | Choice | Rationale |
|----------|--------|-----------|
| **Versioning strategy** | Explicit `/api/v3/` and `/api/v4/` prefixes | Clear separation, prevent breaking changes |
| **Race condition status** | 409 CONFLICT | More semantically correct than 400 |
| **Metrics caching** | No cache (always-fresh) | Consistency with Phase 10 D33, simplicity |
| **Version detection** | Check Total_Uniones column | Faster than Uniones query |
| **Router structure** | New union_router.py | Clean separation from v3.0 |
| **Worker name derivation** | Keep in request body | Consistent with v3.0, avoid extra lookup |
| **Pulgadas in response** | Add to OccupationResponse | Frontend needs immediate feedback |
| **Pulgadas precision** | 2 decimals (API) vs 1 decimal (service) | API uses storage precision per decision |

---

## 9. References

**Phase 10 artifacts:**
- `/Users/sescanella/Proyectos/KM/ZEUES-by-KM/.planning/phases/10-backend-services-validation/PLAN.md`
- `/Users/sescanella/Proyectos/KM/ZEUES-by-KM/backend/services/occupation_service.py` (lines 720-1423)
- `/Users/sescanella/Proyectos/KM/ZEUES-by-KM/backend/services/union_service.py` (lines 60-445)

**Existing routers:**
- `/Users/sescanella/Proyectos/KM/ZEUES-by-KM/backend/routers/occupation.py` (v3.0 pattern)
- `/Users/sescanella/Proyectos/KM/ZEUES-by-KM/backend/routers/history.py` (GET endpoint pattern)

**Models:**
- `/Users/sescanella/Proyectos/KM/ZEUES-by-KM/backend/models/occupation.py` (lines 351-455)
- `/Users/sescanella/Proyectos/KM/ZEUES-by-KM/backend/models/union.py` (lines 12-194)

**Exception handling:**
- `/Users/sescanella/Proyectos/KM/ZEUES-by-KM/backend/main.py` (lines 127-200)
- `/Users/sescanella/Proyectos/KM/ZEUES-by-KM/backend/exceptions.py`

**Project requirements:**
- `/Users/sescanella/Proyectos/KM/ZEUES-by-KM/.planning/PROJECT.md` (API-01 to API-06, METRIC-01 to METRIC-09)

---

**Research complete. Ready for /gsd:plan-phase 11.**
