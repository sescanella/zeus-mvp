# Phase 0: Backend — Nuevos Endpoints (prerequisito) - Research

**Researched:** 2026-03-10
**Domain:** FastAPI + Python — New REST endpoints on existing backend codebase
**Confidence:** HIGH

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| API-01 | `GET /api/spool/{tag}/status` — estado individual con campos computados (operacion_actual, estado_trabajo) | `get_spool_by_tag()` in SheetsRepository already returns a full `Spool` object; need a thin new router + `SpoolStatus` model with computed fields |
| API-02 | `POST /api/spools/batch-status` — refresh batch aceptando `{tags: ["TAG1", "TAG2"]}` | `get_all_spools()` exists; implement as N sequential `get_spool_by_tag()` calls (cache handles the I/O cost) or filter from a single `get_all_spools()` read |
| API-03 | Modificar `POST /api/v4/occupation/finalizar` — aceptar `action_override: 'PAUSAR' \| 'COMPLETAR'` | `finalizar_spool()` service method uses `_determine_action()` to auto-pick; need to wire an optional override that bypasses that logic |
</phase_requirements>

---

## Summary

Phase 0 is a pure backend extension: three API surface changes that the new single-page frontend needs before any frontend work can begin. The codebase is clean and well-layered (routers → services → repositories), so each task maps to a narrow, well-contained change.

Task 0.1 (GET spool/{tag}/status) is a new read-only router that calls the already-existing `SheetsRepository.get_spool_by_tag()` and wraps the result in a new `SpoolStatus` Pydantic model with three computed fields (`operacion_actual`, `estado_trabajo`, `ciclo_rep`). The computation requires `parseEstadoDetalle()` logic (task 0.5), which must be implemented first or in parallel.

Task 0.2 (POST batch-status) is a batch variant — receive a list of tags, call `get_spool_by_tag()` N times (the cache with 60 s TTL makes this cheap), and return an array of `SpoolStatus` objects. The cache is already warmed at startup and invalidated on writes.

Task 0.3 (FINALIZAR `action_override`) is a targeted modification: add an optional `action_override: Optional[Literal['PAUSAR', 'COMPLETAR']] = None` field to `FinalizarRequest`. Inside `finalizar_spool()`, replace the `_determine_action()` call with: use override if provided, otherwise fall back to existing auto-determination. PAUSAR override must skip union writes entirely and only clear occupation. COMPLETAR override must auto-select all available unions.

Task 0.7 (worker_nombre derivation) closes a gap: the frontend currently sends both `worker_id` and `worker_nombre`. The goal is to accept only `worker_id` and derive `worker_nombre` in the backend via `WorkerService.find_worker_by_id(id).nombre_completo`. This touches `IniciarRequest`, `FinalizarRequest`, and the service layer.

**Primary recommendation:** Implement in dependency order — 0.5 and 0.4 first (model + parser), then 0.1 and 0.2 (new endpoints that consume them), then 0.3 (FINALIZAR override), then 0.7 (worker derivation), then 0.6 (tests).

---

## Standard Stack

### Core (already in project — no new installs needed)

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| FastAPI | project baseline | API router, dependency injection | Already used; `APIRouter` pattern established |
| Pydantic v2 | project baseline | Request/response models, validation | `BaseModel`, `ConfigDict`, `computed_field` already used |
| gspread | project baseline | Google Sheets I/O via `SheetsRepository` | Already used; do not bypass it |
| pytest | project baseline | Unit tests | Pattern established in `tests/unit/` |

### No new packages required

All work stays within existing dependencies. Do not add packages.

---

## Architecture Patterns

### Existing Router Pattern (use this exactly)

```
backend/routers/          ← add new router file here
backend/services/         ← extend occupation_service.py or add spool_status_service.py
backend/models/           ← add SpoolStatus to spool.py or occupation.py
backend/core/dependency.py ← add dependency factories if needed
main.py                   ← register new router
```

### Pattern 1: New Read-Only Router (for 0.1 and 0.2)

**What:** A new `APIRouter` file registered in `main.py` under `/api`.
**When to use:** Any new endpoint that reads Sheets data.
**Example (modeled after existing `spools.py`):**

```python
# backend/routers/spool_status_router.py
from fastapi import APIRouter, Depends, HTTPException
from backend.core.dependency import get_sheets_repository
from backend.repositories.sheets_repository import SheetsRepository
from backend.models.spool import SpoolStatus, BatchStatusRequest, BatchStatusResponse

router = APIRouter()

@router.get("/spool/{tag}/status", response_model=SpoolStatus)
async def get_spool_status(
    tag: str,
    sheets_repo: SheetsRepository = Depends(get_sheets_repository)
):
    spool = sheets_repo.get_spool_by_tag(tag)
    if not spool:
        raise HTTPException(status_code=404, detail=f"Spool {tag} not found")
    return SpoolStatus.from_spool(spool)

@router.post("/spools/batch-status", response_model=BatchStatusResponse)
async def batch_spool_status(
    request: BatchStatusRequest,
    sheets_repo: SheetsRepository = Depends(get_sheets_repository)
):
    results = []
    for tag in request.tags:
        spool = sheets_repo.get_spool_by_tag(tag)
        if spool:
            results.append(SpoolStatus.from_spool(spool))
    return BatchStatusResponse(spools=results, total=len(results))
```

### Pattern 2: SpoolStatus Model with Computed Fields (for 0.4)

**What:** A new Pydantic model that wraps `Spool` and adds three computed fields.

```python
# In backend/models/spool.py — add below existing Spool class

from pydantic import BaseModel, Field, model_validator
from typing import Optional, Literal

class SpoolStatus(BaseModel):
    """
    Computed view of a Spool for the v5.0 single-page frontend.
    Adds operacion_actual, estado_trabajo, ciclo_rep derived from Estado_Detalle.
    """
    # Pass-through identity fields
    tag_spool: str
    ocupado_por: Optional[str] = None
    fecha_ocupacion: Optional[str] = None
    estado_detalle: Optional[str] = None
    total_uniones: Optional[int] = None
    uniones_arm_completadas: Optional[int] = None
    uniones_sold_completadas: Optional[int] = None

    # Computed fields (derived from estado_detalle)
    operacion_actual: Optional[str] = None      # "ARM" | "SOLD" | "REPARACION" | None
    estado_trabajo: Optional[str] = None         # "LIBRE" | "EN_PROGRESO" | "PAUSADO" | "COMPLETADO" | "RECHAZADO" | "BLOQUEADO"
    ciclo_rep: Optional[int] = None              # 1–3 for RECHAZADO/REPARACION, None otherwise

    @classmethod
    def from_spool(cls, spool: 'Spool') -> 'SpoolStatus':
        parsed = parse_estado_detalle(spool.estado_detalle)
        return cls(
            tag_spool=spool.tag_spool,
            ocupado_por=spool.ocupado_por,
            fecha_ocupacion=spool.fecha_ocupacion,
            estado_detalle=spool.estado_detalle,
            total_uniones=spool.total_uniones,
            uniones_arm_completadas=spool.uniones_arm_completadas,
            uniones_sold_completadas=spool.uniones_sold_completadas,
            operacion_actual=parsed.get("operacion_actual"),
            estado_trabajo=parsed.get("estado_trabajo"),
            ciclo_rep=parsed.get("ciclo_rep"),
        )


class BatchStatusRequest(BaseModel):
    tags: list[str] = Field(..., min_length=1, max_length=100)

class BatchStatusResponse(BaseModel):
    spools: list[SpoolStatus]
    total: int
```

### Pattern 3: parseEstadoDetalle() Backend Function (for 0.5)

**What:** A pure function that parses the `Estado_Detalle` string into a structured dict.
**Where:** `backend/services/estado_detalle_parser.py` (new file, pure functions only).

Known Estado_Detalle formats from `EstadoDetalleBuilder`:
- `"MR(93) trabajando ARM (ARM en progreso, SOLD pendiente)"` → ocupado + ARM en progreso
- `"MR(93) trabajando SOLD (ARM completado, SOLD en progreso)"` → ocupado + SOLD en progreso
- `"Disponible - ARM completado, SOLD pendiente"` → ARM done, libre
- `"Disponible - ARM completado, SOLD completado, METROLOGIA APROBADO ✓"` → aprobado
- `"Disponible - ARM completado, SOLD completado, RECHAZADO (Ciclo 2/3) - Pendiente reparación"` → rechazado ciclo 2
- `"BLOQUEADO - Contactar supervisor"` → bloqueado
- `"REPARACION completado - PENDIENTE_METROLOGIA"` → reparacion done, pending met
- `"EN_REPARACION (Ciclo 1/3) - Ocupado: MR(93)"` → reparacion en progreso
- `None` or `""` → desconocido / libre

```python
# backend/services/estado_detalle_parser.py
import re
from typing import Optional

def parse_estado_detalle(estado: Optional[str]) -> dict:
    """
    Parse Estado_Detalle string into structured dict.

    Returns:
        {
            "operacion_actual": "ARM" | "SOLD" | "REPARACION" | None,
            "estado_trabajo": "LIBRE" | "EN_PROGRESO" | "PAUSADO" | "COMPLETADO"
                              | "RECHAZADO" | "BLOQUEADO" | "PENDIENTE_METROLOGIA",
            "ciclo_rep": int | None,
            "worker": str | None,  # e.g. "MR(93)"
        }
    """
    result = {
        "operacion_actual": None,
        "estado_trabajo": "LIBRE",
        "ciclo_rep": None,
        "worker": None,
    }

    if not estado or not estado.strip():
        return result

    estado = estado.strip()

    # Occupied: "MR(93) trabajando ARM (...)"
    m = re.match(r'^(\S+)\s+trabajando\s+(ARM|SOLD)\s+', estado)
    if m:
        result["worker"] = m.group(1)
        result["operacion_actual"] = m.group(2)
        result["estado_trabajo"] = "EN_PROGRESO"
        return result

    # REPARACION in progress: "EN_REPARACION (Ciclo N/3) - Ocupado: MR(93)"
    m = re.search(r'EN_REPARACION.*Ciclo\s+(\d+)/3', estado)
    if m:
        result["operacion_actual"] = "REPARACION"
        result["estado_trabajo"] = "EN_PROGRESO"
        result["ciclo_rep"] = int(m.group(1))
        return result

    # BLOQUEADO
    if "BLOQUEADO" in estado:
        result["estado_trabajo"] = "BLOQUEADO"
        return result

    # RECHAZADO: "RECHAZADO (Ciclo N/3) - ..."
    m = re.search(r'RECHAZADO.*Ciclo\s+(\d+)/3', estado)
    if m:
        result["estado_trabajo"] = "RECHAZADO"
        result["ciclo_rep"] = int(m.group(1))
        return result
    if "RECHAZADO" in estado:
        result["estado_trabajo"] = "RECHAZADO"
        return result

    # REPARACION completado → PENDIENTE_METROLOGIA
    if "PENDIENTE_METROLOGIA" in estado or "REPARACION completado" in estado:
        result["estado_trabajo"] = "PENDIENTE_METROLOGIA"
        return result

    # METROLOGIA APROBADO
    if "METROLOGIA APROBADO" in estado or "APROBADO ✓" in estado:
        result["estado_trabajo"] = "COMPLETADO"
        return result

    # Disponible - ARM completado, SOLD completado → COMPLETADO
    if "ARM completado" in estado and "SOLD completado" in estado:
        result["estado_trabajo"] = "COMPLETADO"
        return result

    # Disponible - ARM completado, SOLD pendiente → PAUSADO (ARM done)
    if "ARM completado" in estado and ("SOLD pendiente" in estado or "SOLD pausado" in estado):
        result["estado_trabajo"] = "PAUSADO"
        result["operacion_actual"] = "ARM"
        return result

    # Disponible - ARM pausado
    if "ARM pausado" in estado:
        result["estado_trabajo"] = "PAUSADO"
        result["operacion_actual"] = "ARM"
        return result

    return result  # Default: LIBRE
```

### Pattern 4: action_override in FinalizarRequest (for 0.3)

**What:** Add optional `action_override` field to the existing `FinalizarRequest` model and honor it in `finalizar_spool()`.

Changes to `backend/models/occupation.py`:
```python
from typing import Optional, Literal

class FinalizarRequest(BaseModel):
    tag_spool: str = ...
    worker_id: int = ...
    worker_nombre: str = ...  # still accepted for backward compat until task 0.7
    operacion: ActionType = ...
    selected_unions: list[str] = ...  # still accepted (ignored when action_override=PAUSAR)
    action_override: Optional[Literal['PAUSAR', 'COMPLETAR']] = Field(
        None,
        description="Override auto-determination: PAUSAR clears occupation without touching unions; "
                    "COMPLETAR selects all available unions automatically"
    )
```

Changes to `finalizar_spool()` in `occupation_service.py`:

```python
# After step 4b (standard ARM/SOLD path), replace _determine_action call:
if request.action_override:
    action_taken = request.action_override
    if action_taken == "COMPLETAR":
        # Auto-select all available unions
        selected_unions = [u.id for u in disponibles]
    elif action_taken == "PAUSAR":
        # PAUSAR: skip union writes, only clear occupation
        selected_unions = []  # will be handled by existing PAUSAR path
else:
    action_taken = self._determine_action(selected_count, total_available, operacion)
```

**PAUSAR override logic:** When `action_override == 'PAUSAR'`, clear `Ocupado_Por` / `Fecha_Ocupacion` only. Do NOT update Estado_Detalle with completion info. Do NOT touch Uniones sheet.

**COMPLETAR override logic:** When `action_override == 'COMPLETAR'`, replace `selected_unions` with all available unions from `disponibles`, then proceed normally through the existing COMPLETAR path.

### Pattern 5: worker_nombre Derivation (for 0.7)

**What:** Accept only `worker_id` from the frontend. Backend derives `worker_nombre` from `WorkerService.find_worker_by_id(id).nombre_completo`.

```python
# In IniciarRequest / FinalizarRequest — make worker_nombre optional with None default
worker_nombre: Optional[str] = Field(
    None,
    description="Deprecated: backend derives from worker_id if not provided"
)
```

In the service/router, before calling `iniciar_spool()` or `finalizar_spool()`:
```python
if not request.worker_nombre:
    worker = worker_service.find_worker_by_id(request.worker_id)
    if not worker:
        raise HTTPException(status_code=404, detail=f"Worker {request.worker_id} not found")
    # Build a new request with derived nombre (Pydantic models are frozen — use model_copy)
    request = request.model_copy(update={"worker_nombre": worker.nombre_completo})
```

**Note:** `Spool` is frozen (`ConfigDict(frozen=True)`). `FinalizarRequest` and `IniciarRequest` do NOT have `frozen=True` currently, but use `model_copy()` pattern for safety anyway.

### Anti-Patterns to Avoid

- **Hardcoding column indices:** Never use `row[6]`. Always use `headers["TAG_SPOOL"]` via `ColumnMapCache`.
- **Bypassing SheetsRepository:** Never call gspread directly from a router or service. All Sheets I/O goes through `SheetsRepository`.
- **Reimplementing get_spool_by_tag:** Do not re-scan all rows in new code. Call `sheets_repo.get_spool_by_tag(tag)`.
- **Breaking the frozen Spool model:** `Spool` has `ConfigDict(frozen=True)`. When you need a modified copy, use `.model_copy(update={...})`.
- **Using datetime.utcnow() or datetime.now():** Always use `now_chile()` / `today_chile()` from `backend.utils.date_formatter`.
- **Using any type in new models:** TypeScript rule doesn't apply to Python, but all Pydantic fields must have explicit types. No `Any`.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Reading a spool by tag | Custom Sheets scan | `SheetsRepository.get_spool_by_tag()` | Already handles cache, column map, date parsing |
| Reading multiple spools | Re-implement batch scan | Call `get_spool_by_tag()` N times (cache hit) or use `get_all_spools()` + filter | Cache TTL=60s makes per-tag calls cheap |
| Worker name formatting | String concat | `Worker.nombre_completo` computed field | Already implements `INICIALES(ID)` format |
| Worker lookup by ID | Sheet scan | `WorkerService.find_worker_by_id(id)` | Already implemented, tested |
| Retry on Sheets errors | Custom retry loop | `@retry_on_sheets_error(max_retries=3)` decorator | Already defined in `SheetsRepository` |
| Column index lookup | Hardcoded index | `ColumnMapCache.get_or_build()` + `normalize()` | Existing pattern throughout codebase |
| Timestamp formatting | `.isoformat()` or `datetime.now()` | `format_datetime_for_sheets(now_chile())` | Enforced by CLAUDE.md |

---

## Common Pitfalls

### Pitfall 1: Batch-Status Hitting Sheets Rate Limits

**What goes wrong:** If batch-status with 20+ tags fires 20 uncached `get_spool_by_tag()` calls on a cold start, it can exceed 60 writes/min/user limit (reads also count against quota).
**Why it happens:** Cache TTL is 60 s. First call after TTL expiry re-reads the full Operaciones sheet. But each `get_spool_by_tag()` call calls `read_worksheet()` internally, which is cached. So the 20 tags → 20 cache lookups → at most 1 Sheets API call (the first one reads and caches all rows).
**How to avoid:** The cache architecture already handles this. Each `get_spool_by_tag()` internally calls `read_worksheet()`, which is cached at the sheet level. First call reads all rows; subsequent calls within the TTL return the cached data.
**Warning signs:** If you ever see N Sheets API calls for N tags, something is wrong with cache key construction.

### Pitfall 2: Parsing None/Empty Estado_Detalle

**What goes wrong:** `Estado_Detalle` can be `None` (new spool never worked), empty string, or have whitespace. Regex operations on None crash.
**Why it happens:** Not all spools have Estado_Detalle set (v2.1/v3.0 spools without this column).
**How to avoid:** `parseEstadoDetalle()` must guard with `if not estado or not estado.strip(): return defaults`.
**Warning signs:** `AttributeError: 'NoneType' object has no attribute 'strip'` in logs.

### Pitfall 3: action_override=COMPLETAR Without Unions Available

**What goes wrong:** If `action_override=COMPLETAR` is sent for a spool with 0 available unions (all already done), `disponibles` is empty and `selected_unions` becomes `[]`, which triggers the cancellation path.
**Why it happens:** The auto-select logic uses `[u.id for u in disponibles]` which returns `[]` when all unions are already completed.
**How to avoid:** After substituting `selected_unions` from `disponibles`, if the list is empty and `action_override == 'COMPLETAR'`, treat it as COMPLETAR with 0 unions to process (not cancellation). Distinguish the two empty-list cases: override-COMPLETAR vs genuine cancellation.

### Pitfall 4: worker_nombre Optional Migration — Backward Compatibility

**What goes wrong:** Making `worker_nombre` Optional breaks validation for existing callers that send it as a required field (they still pass it). Also, if the frontend passes it explicitly, the backend should use the passed value OR the derived value — need a clear rule.
**Why it happens:** Task 0.7 description says "solo worker_id desde frontend, backend deriva nombre". But existing callers and tests still send `worker_nombre`.
**How to avoid:** Make `worker_nombre` optional with `None` default. If provided (non-None), use it as-is (backward compat). If `None`, derive from `worker_id`. Existing tests continue to pass.

### Pitfall 5: Frozen Spool Model

**What goes wrong:** `Spool` has `frozen=True`. Any attempt to mutate a field raises `ValidationError`.
**Why it happens:** The compute fields in `SpoolStatus.from_spool()` read from the spool but never mutate it.
**How to avoid:** `SpoolStatus` is a separate model — it's not a `Spool`. `from_spool()` is a classmethod that reads from the source. No mutation of `spool` needed.

### Pitfall 6: FINALIZAR PAUSAR Override Leaves Estado_Detalle Stale

**What goes wrong:** When `action_override=PAUSAR`, if the code doesn't update `Estado_Detalle`, the column may still say "MR(93) trabajando ARM (...)" even after clearing `Ocupado_Por`.
**Why it happens:** The existing PAUSAR path updates `Estado_Detalle` to reflect the paused state. If the override bypasses union processing but doesn't update `Estado_Detalle`, the column becomes inconsistent.
**How to avoid:** When processing PAUSAR override (clearing occupation), also update `Estado_Detalle` using `EstadoDetalleBuilder` — set it to the paused state equivalent (e.g., "Disponible - ARM pausado, SOLD pendiente").

---

## Code Examples

### Registering a New Router in main.py

```python
# Source: existing pattern in backend/main.py
from backend.routers import spool_status_router

app.include_router(
    spool_status_router.router,
    prefix="/api",
    tags=["spool-status"]
)
```

### Dependency Injection Pattern (from existing routers)

```python
# Source: existing pattern in backend/routers/occupation_v4.py
from typing import Annotated
from fastapi import Depends
from backend.core.dependency import get_sheets_repository

async def my_endpoint(
    sheets_repo: Annotated[SheetsRepository, Depends(get_sheets_repository)]
):
    ...
```

### Cache-Aware Batch Pattern (extrapolated from existing get_spool_by_tag + read_worksheet cache)

```python
# All calls to get_spool_by_tag() share the same cached worksheet read.
# Up to 100 tags → at most 1 Sheets API call within the 60s TTL window.
results = []
for tag in request.tags:
    spool = sheets_repo.get_spool_by_tag(tag)  # Cache hit after first call
    if spool:
        results.append(SpoolStatus.from_spool(spool))
```

### model_copy for Frozen-Safe Mutation

```python
# Source: Pydantic v2 docs — model_copy replaces deprecated copy(update=...)
new_request = request.model_copy(update={"worker_nombre": worker.nombre_completo})
```

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| selected_unions required in FINALIZAR | `action_override` optional field | v5.0 Phase 0 (this phase) | Eliminates union selection screen |
| Frontend sends worker_nombre | Frontend sends worker_id only, backend derives nombre | v5.0 Phase 0 (this phase, task 0.7) | Frontend simplification |
| No single-spool status endpoint | `GET /api/spool/{tag}/status` | v5.0 Phase 0 | Enables card refresh without full list fetch |
| No batch status endpoint | `POST /api/spools/batch-status` | v5.0 Phase 0 | Enables 30s polling for N cards in 1 call |

---

## Open Questions

1. **COMPLETAR override with 0 available unions**
   - What we know: When `action_override=COMPLETAR` but all unions are already done, `disponibles` is empty.
   - What's unclear: Should this be a 400 error ("nothing to complete"), or a silent no-op COMPLETAR?
   - Recommendation: Treat as COMPLETAR with `unions_processed=0`. Log a warning. The spool was already in fully-completed state, the write is a no-op harmless duplicate.

2. **BatchStatusRequest max size**
   - What we know: Google Sheets rate limit is 60 writes/min/user. Reads are less constrained but still limited. The cache makes batch reads cheap (1 Sheets call for any batch size within TTL).
   - What's unclear: Maximum safe batch size without risking rate limit under cache miss conditions.
   - Recommendation: Cap `tags` list at 100 (`max_length=100`). Sufficient for any foreseeable localStorage size.

3. **SpoolStatus: Which fields to include in the response?**
   - What we know: The frontend card needs: `tag_spool`, `ocupado_por`, `fecha_ocupacion`, `operacion_actual`, `estado_trabajo`, `ciclo_rep`, `total_uniones`, `uniones_arm_completadas`, `uniones_sold_completadas`.
   - What's unclear: Whether pulgadas fields (`pulgadas_arm`, `pulgadas_sold`) are needed in the card view.
   - Recommendation: Include them in `SpoolStatus` for completeness. Frontend can ignore what it doesn't use.

---

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Framework | pytest (already installed in venv) |
| Config file | none — use `PYTHONPATH="$(pwd)" pytest` |
| Quick run command | `source venv/bin/activate && PYTHONPATH="$(pwd)" pytest tests/unit/ -v --tb=short` |
| Full suite command | `source venv/bin/activate && PYTHONPATH="$(pwd)" pytest -v --tb=short` |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| API-01 | `SpoolStatus.from_spool()` computes correct `operacion_actual`, `estado_trabajo`, `ciclo_rep` | unit | `PYTHONPATH="$(pwd)" pytest tests/unit/test_spool_status_model.py -v` | ❌ Wave 0 |
| API-01 | `parse_estado_detalle()` handles all known Estado_Detalle formats | unit | `PYTHONPATH="$(pwd)" pytest tests/unit/test_estado_detalle_parser.py -v` | ❌ Wave 0 |
| API-02 | `BatchStatusRequest` validates tags list min/max | unit | `PYTHONPATH="$(pwd)" pytest tests/unit/test_batch_status_model.py -v` | ❌ Wave 0 |
| API-03 | `FinalizarRequest.action_override` field accepts PAUSAR/COMPLETAR/None | unit | `PYTHONPATH="$(pwd)" pytest tests/unit/test_finalizar_action_override.py -v` | ❌ Wave 0 |
| API-03 | `action_override=PAUSAR` clears occupation without union writes | unit (mock) | `PYTHONPATH="$(pwd)" pytest tests/unit/test_occupation_service_action_override.py -v` | ❌ Wave 0 |
| API-03 | `action_override=COMPLETAR` auto-selects all available unions | unit (mock) | `PYTHONPATH="$(pwd)" pytest tests/unit/test_occupation_service_action_override.py -v` | ❌ Wave 0 |
| 0.7 | Worker derivation from worker_id when worker_nombre is None | unit | `PYTHONPATH="$(pwd)" pytest tests/unit/test_worker_derivation.py -v` | ❌ Wave 0 |

### Sampling Rate

- **Per task commit:** `PYTHONPATH="$(pwd)" pytest tests/unit/ -v --tb=short`
- **Per wave merge:** `PYTHONPATH="$(pwd)" pytest -v --tb=short`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps

- [ ] `backend/tests/unit/test_spool_status_model.py` — covers API-01 model behavior
- [ ] `backend/tests/unit/test_estado_detalle_parser.py` — covers API-01 + 0.5 parsing logic
- [ ] `backend/tests/unit/test_batch_status_model.py` — covers API-02 request validation
- [ ] `backend/tests/unit/test_finalizar_action_override.py` — covers API-03 model validation
- [ ] `backend/tests/unit/test_occupation_service_action_override.py` — covers API-03 service behavior (uses mock repos)
- [ ] `backend/tests/unit/test_worker_derivation.py` — covers task 0.7 worker derivation

---

## Sources

### Primary (HIGH confidence)

- Direct code inspection: `backend/repositories/sheets_repository.py` — `get_spool_by_tag()`, `get_all_spools()`, cache architecture
- Direct code inspection: `backend/services/occupation_service.py` — `finalizar_spool()`, `_determine_action()`, PAUSAR/COMPLETAR paths
- Direct code inspection: `backend/models/spool.py` — `Spool` model fields and `frozen=True` constraint
- Direct code inspection: `backend/models/occupation.py` — `FinalizarRequest`, `IniciarRequest` existing structure
- Direct code inspection: `backend/services/estado_detalle_builder.py` — all known Estado_Detalle format strings
- Direct code inspection: `backend/services/worker_service.py` + `backend/models/worker.py` — `find_worker_by_id()`, `nombre_completo` computed field
- Direct code inspection: `backend/routers/occupation_v4.py` + `backend/routers/spools.py` — router patterns, DI patterns
- Direct code inspection: `backend/main.py` — router registration pattern
- Direct code inspection: `backend/tests/unit/test_spool_version_detection.py` — test pattern used in this project

### Secondary (MEDIUM confidence)

- `.planning/REQUIREMENTS.md` — v5.0 requirements, API-01/02/03 spec
- `.planning/ROADMAP.md` — task breakdown and success criteria
- `CLAUDE.md` — project conventions, timezone, venv rules

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — all code inspected directly; no external dependency research needed
- Architecture: HIGH — existing patterns are clear, consistent, and well-documented in code
- Pitfalls: HIGH — derived from direct code analysis of cache behavior, frozen model constraints, and existing PAUSAR/COMPLETAR paths
- Parser patterns: MEDIUM — Estado_Detalle formats inferred from `EstadoDetalleBuilder`; edge cases may exist in production data not covered by the builder

**Research date:** 2026-03-10
**Valid until:** 2026-04-10 (stable codebase — 30 days)
