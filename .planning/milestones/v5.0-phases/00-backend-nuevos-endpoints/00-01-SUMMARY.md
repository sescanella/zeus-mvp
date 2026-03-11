---
phase: 00-backend-nuevos-endpoints
plan: 01
subsystem: backend
tags: [api, parser, pydantic, tdd, spool-status]
dependency_graph:
  requires: []
  provides: [GET /api/spool/{tag}/status, parse_estado_detalle(), SpoolStatus model]
  affects: [v5.0 frontend card refresh, batch-status plan 02]
tech_stack:
  added: []
  patterns: [pure-function parser, Pydantic from_spool classmethod, FastAPI DI with Annotated]
key_files:
  created:
    - backend/services/estado_detalle_parser.py
    - backend/models/spool_status.py
    - backend/routers/spool_status_router.py
    - tests/unit/test_estado_detalle_parser.py
    - tests/unit/test_spool_status_model.py
    - tests/unit/routers/test_spool_status_router.py
  modified:
    - backend/main.py
decisions:
  - "parse_estado_detalle() implemented as pure function in backend/services/ not models/ for separation of concerns"
  - "SpoolStatus placed in separate backend/models/spool_status.py not spool.py to avoid circular imports with parser"
  - "TYPE_CHECKING guard used in spool_status.py to import Spool without circular dependency"
  - "Router uses Annotated[SheetsRepository, Depends(...)] pattern consistent with occupation_v4.py"
metrics:
  duration: 4 minutes
  tasks_completed: 2
  files_created: 6
  files_modified: 1
  tests_added: 50
  completed_date: "2026-03-10"
requirements: [API-01]
---

# Phase 0 Plan 01: Individual Spool Status Endpoint — Summary

**One-liner:** Estado_Detalle parser + SpoolStatus Pydantic model + GET /api/spool/{tag}/status endpoint with 50 TDD unit tests.

## What Was Built

### Task 1: parse_estado_detalle() + SpoolStatus model (TDD)

**`backend/services/estado_detalle_parser.py`** — Pure function that parses all known Estado_Detalle strings produced by EstadoDetalleBuilder into a structured dict with 4 keys: `operacion_actual`, `estado_trabajo`, `ciclo_rep`, `worker`. Guards against None/empty input. Uses regex for occupied/reparacion/rechazado cycle extraction.

**`backend/models/spool_status.py`** — Three Pydantic models:
- `SpoolStatus`: 9 pass-through fields from Spool + 3 computed fields (operacion_actual, estado_trabajo, ciclo_rep) via `from_spool()` classmethod
- `BatchStatusRequest`: tags list with Field(min_length=1, max_length=100) validation
- `BatchStatusResponse`: spools list + total count

### Task 2: GET /api/spool/{tag}/status router

**`backend/routers/spool_status_router.py`** — APIRouter with:
- `GET /spool/{tag}/status` → SpoolStatus or 404
- `POST /spools/batch-status` → BatchStatusResponse (included here for completeness, tested in plan 02)

**`backend/main.py`** — Router registered at `/api` prefix with `spool-status` tag.

## Test Coverage

| File | Tests | Coverage |
|------|-------|----------|
| test_estado_detalle_parser.py | 19 | All 10+ Estado_Detalle formats |
| test_spool_status_model.py | 20 | from_spool(), BatchStatusRequest validation, BatchStatusResponse |
| test_spool_status_router.py | 11 | 200/404 responses, computed fields in response, dependency injection |
| **Total** | **50** | **All passing** |

## Estado_Detalle Formats Covered

| Input | estado_trabajo | operacion_actual | ciclo_rep |
|-------|---------------|-----------------|-----------|
| None / "" | LIBRE | None | None |
| "MR(93) trabajando ARM (...)" | EN_PROGRESO | ARM | None |
| "MR(93) trabajando SOLD (...)" | EN_PROGRESO | SOLD | None |
| "Disponible - ARM completado, SOLD pendiente" | PAUSADO | ARM | None |
| "Disponible - ARM completado, SOLD completado, METROLOGIA APROBADO ✓" | COMPLETADO | None | None |
| "Disponible - ... RECHAZADO (Ciclo 2/3) ..." | RECHAZADO | None | 2 |
| "BLOQUEADO - Contactar supervisor" | BLOQUEADO | None | None |
| "REPARACION completado - PENDIENTE_METROLOGIA" | PENDIENTE_METROLOGIA | None | None |
| "EN_REPARACION (Ciclo 1/3) - Ocupado: MR(93)" | EN_PROGRESO | REPARACION | 1 |

## Decisions Made

1. **Separate file for parser**: `backend/services/estado_detalle_parser.py` instead of inlining in the model to enable independent unit testing and reuse.
2. **Separate model file**: `backend/models/spool_status.py` instead of appending to `spool.py`. Avoids circular imports since SpoolStatus imports from the parser service.
3. **TYPE_CHECKING guard**: Used `from __future__ import annotations` + `TYPE_CHECKING` for `Spool` type hint to avoid circular import at runtime.
4. **Annotated DI pattern**: `Annotated[SheetsRepository, Depends(get_sheets_repository)]` matching occupation_v4.py style.

## Deviations from Plan

None — plan executed exactly as written.

## Self-Check: PASSED

All files exist on disk. Both task commits verified in git log.
