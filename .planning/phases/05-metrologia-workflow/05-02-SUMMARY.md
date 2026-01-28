---
phase: 05-metrologia-workflow
plan: 02
subsystem: api-layer
tags: [rest-api, metrologia, estado-detalle, instant-completion]
requires:
  - "05-01: MetrologiaService and state machine"
  - "Phase 2: ValidationService prerequisite checks"
provides:
  - "POST /api/metrologia/completar endpoint"
  - "CompletarMetrologiaRequest/Response models"
  - "Estado_Detalle metrología display strings"
affects:
  - "05-03: Frontend will consume this endpoint"
  - "05-04: SSE integration will use estado_detalle format"
tech-stack:
  added: []
  patterns:
    - "FastAPI dependency injection for MetrologiaService"
    - "Pydantic enum validation for binary resultado"
    - "Estado_Detalle builder pattern extension"
key-files:
  created:
    - "backend/models/metrologia.py"
    - "backend/routers/metrologia.py"
  modified:
    - "backend/services/estado_detalle_builder.py"
    - "backend/core/dependency.py"
    - "backend/main.py"
decisions:
  - id: "05-02-01"
    title: "Enum validation enforces binary resultado at API boundary"
    rationale: "Pydantic ResultadoEnum prevents invalid valores from reaching service layer"
    alternatives: ["String validation in service layer"]
    chosen: "Pydantic enum - earlier validation, auto-generated OpenAPI schema"
  - id: "05-02-02"
    title: "Estado_Detalle builder uses optional metrologia_state parameter"
    rationale: "Backward compatible with existing ARM/SOLD estado display"
    alternatives: ["Separate builder for metrología", "Always require metrologia_state"]
    chosen: "Optional parameter - single builder, gradual adoption"
metrics:
  duration: "2 min 55 sec"
  completed: "2026-01-27"
---

# Phase 5 Plan 02: REST Endpoint & Estado Display Summary

**One-liner:** POST /api/metrologia/completar with binary resultado validation and human-readable estado_detalle

## What Was Built

REST API endpoint for instant metrología completion with Estado_Detalle integration:

1. **Pydantic Models** (backend/models/metrologia.py):
   - `ResultadoEnum`: Strict APROBADO/RECHAZADO values
   - `CompletarMetrologiaRequest`: tag_spool, worker_id, resultado
   - `CompletarMetrologiaResponse`: success, resultado, estado_detalle, message

2. **REST Endpoint** (backend/routers/metrologia.py):
   - `POST /api/metrologia/completar`: Instant completion with binary resultado
   - Error handling: 404 (not found), 400 (validation), 409 (occupied), 403 (unauthorized)
   - Worker name formatting via WorkerService

3. **Estado_Detalle Extension** (backend/services/estado_detalle_builder.py):
   - Optional `metrologia_state` parameter in build()
   - Display formats:
     * APROBADO: "METROLOGIA APROBADO ✓"
     * RECHAZADO: "METROLOGIA RECHAZADO - Pendiente reparación"
     * PENDIENTE: "Metrología pendiente"

4. **Dependency Injection** (backend/core/dependency.py):
   - `get_metrologia_service()` factory with all dependencies

5. **Main Integration** (backend/main.py):
   - Router registered with prefix `/api/metrologia`

## Technical Execution

### Task 1: Pydantic Models
```python
# ResultadoEnum enforces binary values at API boundary
class ResultadoEnum(str, Enum):
    APROBADO = "APROBADO"
    RECHAZADO = "RECHAZADO"

# Request validation with strict types
class CompletarMetrologiaRequest(BaseModel):
    tag_spool: str
    worker_id: int
    resultado: ResultadoEnum  # Pydantic validates enum
```

**Commit:** 0d9ed59

### Task 2: REST Endpoint
```python
@router.post("/completar")
async def completar_metrologia(
    request: CompletarMetrologiaRequest,
    metrologia_service: MetrologiaService = Depends(get_metrologia_service),
    worker_service: WorkerService = Depends(get_worker_service)
):
    # Fetch worker for nombre_completo
    worker = worker_service.get_worker_by_id(request.worker_id)
    worker_nombre = worker.nombre_completo  # "INICIALES(ID)"

    # Delegate to service layer
    result = metrologia_service.completar(
        tag_spool=request.tag_spool,
        worker_id=request.worker_id,
        worker_nombre=worker_nombre,
        resultado=request.resultado.value
    )

    # Build estado_detalle with metrologia state
    estado_builder = EstadoDetalleBuilder()
    metrologia_state = "aprobado" if request.resultado.value == "APROBADO" else "rechazado"
    estado_detalle = estado_builder.build(
        ocupado_por=None,
        arm_state="completado",
        sold_state="completado",
        metrologia_state=metrologia_state
    )

    return CompletarMetrologiaResponse(...)
```

**Commit:** 1a05e7c

### Task 3: EstadoDetalleBuilder Extension
```python
def build(
    self,
    ocupado_por: Optional[str],
    arm_state: str,
    sold_state: str,
    operacion_actual: Optional[str] = None,
    metrologia_state: Optional[str] = None  # NEW - v3.0 Phase 5
) -> str:
    base = f"Disponible - ARM {arm_display}, SOLD {sold_display}"

    # Append metrología state if provided
    if metrologia_state:
        metrologia_suffix = self._metrologia_to_display(metrologia_state)
        return f"{base}, {metrologia_suffix}"

    return base
```

**Commit:** 6f74f8f

## Verification Results

All verification tests passed:

| Test | Status | Details |
|------|--------|---------|
| Valid APROBADO request | ✓ | Pydantic accepts APROBADO |
| Valid RECHAZADO request | ✓ | Pydantic accepts RECHAZADO |
| Invalid resultado value | ✓ | Pydantic rejects with ValidationError |
| Endpoint routing | ✓ | Router has 1 route |
| Estado_Detalle APROBADO | ✓ | "METROLOGIA APROBADO ✓" |
| Estado_Detalle RECHAZADO | ✓ | "METROLOGIA RECHAZADO - Pendiente reparación" |

## Key Patterns Applied

1. **Enum Validation**: Pydantic `ResultadoEnum` enforces binary values before service layer
2. **Dependency Injection**: FastAPI `Depends()` for clean service orchestration
3. **Builder Pattern Extension**: EstadoDetalleBuilder extended with optional parameter for backward compatibility
4. **Error Propagation**: Exceptions auto-handled by main.py exception handlers

## Dependencies Created

### MetrologiaService Dependencies
```
POST /api/metrologia/completar
├── MetrologiaService (via get_metrologia_service)
│   ├── ValidationService (prerequisite checks)
│   ├── SheetsRepository (Fecha_QC_Metrologia updates)
│   ├── MetadataRepository (audit logging)
│   └── RedisEventService (SSE publishing)
└── WorkerService (worker name formatting)
```

## Estado_Detalle Display Examples

### APROBADO Flow
```
Input: resultado="APROBADO"
Build: metrologia_state="aprobado"
Output: "Disponible - ARM completado, SOLD completado, METROLOGIA APROBADO ✓"
```

### RECHAZADO Flow
```
Input: resultado="RECHAZADO"
Build: metrologia_state="rechazado"
Output: "Disponible - ARM completado, SOLD completado, METROLOGIA RECHAZADO - Pendiente reparación"
```

## OpenAPI Documentation

Endpoint automatically documented in FastAPI Swagger UI:

**POST /api/metrologia/completar**
- Request body: CompletarMetrologiaRequest (with enum dropdown for resultado)
- Response: 200 CompletarMetrologiaResponse
- Errors: 404, 400, 409, 403, 422

## Decisions Made

### Decision 1: Pydantic Enum Validation
**Context:** Need to enforce APROBADO/RECHAZADO binary values

**Options:**
1. String validation in service layer
2. Pydantic enum at API boundary

**Chosen:** Pydantic enum
- Validation happens before service layer
- Auto-generates OpenAPI schema with enum dropdown
- Type-safe in frontend TypeScript codegen

### Decision 2: Optional metrologia_state Parameter
**Context:** Need to extend EstadoDetalleBuilder without breaking existing code

**Options:**
1. Create separate builder for metrología
2. Always require metrologia_state parameter
3. Optional metrologia_state parameter

**Chosen:** Optional parameter
- Single builder maintains consistency
- Backward compatible with ARM/SOLD code
- Gradual adoption - only metrología routes use it

## Next Steps for Phase 5

### Plan 05-03: Frontend Binary Resultado Flow
- Create /metrologia page with APROBADO/RECHAZADO buttons
- Consume POST /api/metrologia/completar endpoint
- Display estado_detalle with metrología state

### Plan 05-04: SSE Integration & Tests
- Publish COMPLETAR_METROLOGIA events to spools:updates channel
- Dashboard displays metrología results in real-time
- E2E tests for complete workflow

## Commits

| Commit | Task | Description |
|--------|------|-------------|
| 0d9ed59 | 1 | Create Pydantic models for metrología instant completion |
| 1a05e7c | 2 | Implement POST /api/metrologia/completar endpoint |
| 6f74f8f | 3 | Extend EstadoDetalleBuilder for metrología states |

## Deviations from Plan

None - plan executed exactly as written.

## Blockers Resolved

None - all dependencies from 05-01 were in place.

## Risks Mitigated

1. **Invalid resultado values**: Pydantic enum validation prevents at API boundary
2. **Missing prerequisites**: ValidationService.validar_puede_completar_metrologia() enforces 4 checks
3. **Race conditions**: SpoolOccupiedError (409) if spool occupied during completion
4. **Unauthorized access**: RolNoAutorizadoError (403) if worker lacks METROLOGIA role

## Phase 5 Progress

**Wave 2 Complete!**

| Plan | Status | Description |
|------|--------|-------------|
| 05-01 | ✅ | State machine & service |
| 05-02 | ✅ | REST endpoint & estado display |
| 05-03 | 🔲 | Frontend binary resultado flow |
| 05-04 | 🔲 | SSE integration & tests |

**Progress:** 50% (2 of 4 plans complete)
