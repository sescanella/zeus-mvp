# Architecture

**Analysis Date:** 2026-01-26

## Pattern Overview

**Overall:** Layered Clean Architecture with Service/Repository Pattern

**Key Characteristics:**
- Separation of concerns: Routes (thin) → Services (orchestration) → Repositories (data access)
- Domain-driven validation using custom exception hierarchy
- Direct read/write model (v2.1) - States read from Google Sheets columns, not reconstructed from events
- Event auditing (best-effort) via parallel Metadata sheet writes
- Batch operation support (up to 50 items with partial error handling)

## Layers

**API Router Layer (Thin Controllers):**
- Purpose: HTTP request/response mapping, parameter validation, status codes
- Location: `backend/routers/` (health.py, workers.py, spools.py, actions.py)
- Contains: FastAPI endpoints with minimal business logic
- Depends on: Services (ActionService, etc. via Depends())
- Used by: Frontend via HTTP; HTTP exception handlers in `backend/main.py`

**Service Layer (Orchestration & Business Logic):**
- Purpose: Coordinate workflows, validate rules, delegate to repositories
- Location: `backend/services/` (action_service.py, validation_service.py, spool_service.py, worker_service.py, role_service.py)
- Contains: ActionService (INICIAR/COMPLETAR/CANCELAR workflows), ValidationService (state checks + ownership), RoleService (role-based access), SpoolService (spool queries), WorkerService (worker queries)
- Depends on: Repositories (SheetsRepository, MetadataRepository, RoleRepository)
- Used by: Routers; orchestrates multi-step workflows

**Repository Layer (Data Access):**
- Purpose: Isolate Google Sheets API complexity, provide CRUD abstractions
- Location: `backend/repositories/` (sheets_repository.py, metadata_repository.py, role_repository.py)
- Contains: SheetsRepository (READ/WRITE Sheets via gspread, column mapping, batch updates), MetadataRepository (append-only event logging), RoleRepository (worker roles)
- Depends on: gspread client, Google Sheets API, ColumnMapCache
- Used by: Services for data access

**Model Layer (Domain Objects):**
- Purpose: Define data structures and validation schemas
- Location: `backend/models/` (worker.py, spool.py, action.py, enums.py, metadata.py, error.py, role.py)
- Contains: Pydantic models (Worker, Spool, ActionRequest, ActionResponse), Enums (ActionType, ActionStatus, Accion)
- Depends on: pydantic
- Used by: All layers for type safety

**Exception Hierarchy (Cross-cutting):**
- Purpose: Standardized error handling with HTTP status mapping
- Location: `backend/exceptions.py`
- Contains: ZEUSException base class + 10+ subclasses (SpoolNoEncontradoError 404, OperacionYaIniciadaError 400, NoAutorizadoError 403, SheetsConnectionError 503, etc.)
- Used by: Services raise exceptions; main.py exception handlers map to HTTP status codes

## Data Flow

**INICIAR Action (Start Manufacturing):**

1. Frontend POST /api/iniciar-accion → ActionRequest (worker_id, operacion, tag_spool)
2. Router validates request, calls ActionService.iniciar_accion()
3. ActionService:
   - Fetches Worker by ID (WorkerService.find_worker_by_id)
   - Fetches Spool by TAG (SpoolService.find_spool_by_tag)
   - Validates prerequisites (ValidationService.validar_puede_iniciar_arm/sold):
     * Checks fecha_materiales exists (ARM prerequisite)
     * Checks armador/soldador not already set (not EN_PROGRESO/COMPLETADO)
     * Validates worker has required role via RoleService
   - Finds spool row in Operaciones sheet (SheetsRepository.find_row_by_column_value)
   - Writes worker name to Armador/Soldador column (SheetsRepository.batch_update_by_column_name)
   - Logs event to Metadata sheet for audit trail (MetadataRepository.append_event - best effort)
   - Returns ActionResponse with success=True
4. Exception handler in main.py maps ZEUSException to HTTP status code
5. Frontend receives ActionResponse and displays success/error

**COMPLETAR Action (Complete Manufacturing):**

1. Frontend POST /api/completar-accion → ActionRequest
2. Router calls ActionService.completar_accion()
3. ActionService:
   - Fetches Worker by ID
   - Fetches Spool by TAG
   - Validates completion eligibility (ValidationService.validar_puede_completar_arm/sold):
     * **CRITICAL:** Ownership check - worker name must match armador/soldador
     * Checks operation is EN_PROGRESO (armador set, fecha_armado empty)
     * Validates worker has required role
   - Finds spool row in Operaciones sheet
   - Writes today's date to Fecha_Armado/Fecha_Soldadura column
   - Logs event to Metadata sheet (best effort)
   - Returns ActionResponse
4. If ownership check fails → NoAutorizadoError → 403 FORBIDDEN

**CANCELAR Action (Revert Manufacturing):**

1. Frontend POST /api/cancelar-accion → ActionRequest
2. Router calls ActionService.cancelar_accion()
3. ActionService:
   - Fetches Worker and Spool (same as INICIAR)
   - Validates cancellation eligibility (ValidationService.validar_puede_cancelar):
     * **CRITICAL:** Ownership validation (only initiator can cancel)
     * Checks operation is EN_PROGRESO (armador/soldador set, fecha empty)
   - Finds spool row
   - Clears Armador/Soldador column (writes empty string)
   - Logs event to Metadata sheet
   - Returns ActionResponse
4. Exception handling same as COMPLETAR

**Batch Operations (Multiple Spools):**

1. Frontend POST /api/iniciar-accion-batch → BatchActionRequest (worker_id, operacion, tag_spools[])
2. ActionService.iniciar_accion_batch():
   - Validates batch size (max 50 spools)
   - Iterates over each tag_spool
   - Calls iniciar_accion() for each spool individually
   - Catches exceptions per spool (continues on error)
   - Builds BatchActionResponse with exitosos/fallidos counts + per-spool results
3. Returns partial success even if some spools fail
4. **CRITICAL:** Ownership validation in batch completar/cancelar is per-spool

**State Determination (v2.1 Direct Read):**

- **ARM PENDIENTE:** armador = None AND fecha_armado = None
- **ARM EN_PROGRESO:** armador != None AND fecha_armado = None
- **ARM COMPLETADO:** fecha_armado != None (implies armador is set)
- Same logic applies for SOLD (soldador, fecha_soldadura)
- **No state reconstruction from Metadata events** - Direct Read from column values

## Key Abstractions

**ActionService:**
- Purpose: Orchestrate manufacturing action workflows
- Location: `backend/services/action_service.py`
- Pattern: Dependency injection (services/repositories passed to __init__)
- Key methods: iniciar_accion(), completar_accion(), cancelar_accion() + batch variants
- **CRITICAL:** Implements ownership validation - only initiator can complete/cancel

**ValidationService:**
- Purpose: Pure business rule validation
- Location: `backend/services/validation_service.py`
- Pattern: Stateless (no side effects), pure functions
- Key methods: validar_puede_iniciar_arm(), validar_puede_completar_arm(), validar_puede_cancelar()
- Returns: void (raises exceptions on validation failure)
- **CRITICAL:** Contains ownership checks (worker_nombre must match spool.armador/soldador)

**SheetsRepository:**
- Purpose: Abstract Google Sheets API, provide CRUD operations
- Location: `backend/repositories/sheets_repository.py`
- Pattern: Lazy client initialization, retry decorator for API resilience
- Key methods: find_row_by_column_value(), batch_update_by_column_name(), read_sheet_data()
- **CRITICAL:** Uses ColumnMapCache for dynamic column mapping (columns change frequently)

**ColumnMapCache:**
- Purpose: Cache column header → index mapping to avoid repeated Sheets API calls
- Location: `backend/core/column_map_cache.py`
- Pattern: Static cache dictionary with lazy building
- **CRITICAL:** Never hardcode column indices - always map by header name

**RoleService:**
- Purpose: Validate worker has required operational role
- Location: `backend/services/role_service.py`
- Pattern: Reads from Roles sheet (multi-role support - one worker can have multiple rows)
- Key methods: validar_worker_tiene_rol_para_operacion()

## Entry Points

**Backend API:**
- Location: `backend/main.py`
- Triggers: uvicorn (development) or Railway/Gunicorn (production)
- Responsibilities:
  * FastAPI app initialization
  * CORS middleware (frontend origins)
  * Exception handler registration (ZEUSException → HTTP status)
  * Router registration (health, workers, spools, actions)
  * Startup/shutdown events (column map pre-warming)

**Frontend App:**
- Location: `zeues-frontend/app/layout.tsx` (root) + pages
- Pages (7-page linear flow):
  * `app/page.tsx` → P1: Worker identification (fetch all workers)
  * `app/operacion/page.tsx` → P2: Operation selection (ARM/SOLD/METROLOGIA)
  * `app/tipo-interaccion/page.tsx` → P3: Action type (INICIAR/COMPLETAR/CANCELAR)
  * `app/seleccionar-spool/page.tsx` → P4: Spool selection (filtered by API)
  * `app/confirmar/page.tsx` → P5: Confirmation summary
  * `app/exito/page.tsx` → P6: Success page (5sec timeout → P1)
- Triggers: Next.js routing via useRouter()
- Responsibilities: UI rendering, state management, API orchestration

## Error Handling

**Strategy:** Exception-driven error handling with centralized mapping

**Patterns:**

1. **Business Rule Violations (400 Bad Request):**
   - OperacionYaIniciadaError, OperacionYaCompletadaError
   - DependenciasNoSatisfechasError, OperacionNoIniciadaError
   - Raised in ValidationService, caught by router exception handler

2. **Authorization Failures (403 Forbidden):**
   - **NoAutorizadoError:** Ownership violation (worker != initiator)
   - **RolNoAutorizadoError:** Missing required operational role
   - **CRITICAL:** 403 logged as WARNING for audit trail

3. **Resource Not Found (404 Not Found):**
   - SpoolNoEncontradoError, WorkerNoEncontradoError
   - Caught and mapped by exception handler

4. **External Service Failures (503 Service Unavailable):**
   - SheetsConnectionError, SheetsUpdateError
   - Indicates Google Sheets API unavailable
   - Retried with exponential backoff in SheetsRepository

5. **Rate Limiting (429 Too Many Requests):**
   - SheetsRateLimitError
   - Indicates Google Sheets quota exceeded

**Exception Handler (main.py):**
- Receives ZEUSException
- Maps error_code → HTTP status code
- Constructs ErrorResponse with error/message/data fields
- Logs according to severity (ERROR for 5xx, WARNING for 403, INFO for 4xx)
- Returns JSONResponse with appropriate status

## Cross-Cutting Concerns

**Logging:**
- Framework: Python logging module
- Location: Each service logs at DEBUG/INFO/WARNING/ERROR levels
- Pattern: `logger.info(f"[v2.1] Event description | Details")`
- Entry point setup: `backend/utils/logger.py` via `setup_logger()` on FastAPI startup

**Validation:**
- **Frontend:** Inline in components (type checks, minimal validation)
- **Backend:** Centralized in ValidationService (business rules), Pydantic models (schema validation)
- Pattern: ValidationService.validar_* methods raise exceptions on failure

**Authentication:**
- **Current:** Service Account (zeus-mvp@zeus-mvp.iam.gserviceaccount.com)
- **Pattern:** Credentials loaded from environment (GOOGLE_PRIVATE_KEY)
- **No JWT/user auth:** Worker ID passed in request body (mobile-first assumption)

**Caching:**
- **Column Mapping:** ColumnMapCache (static, pre-warmed on startup)
- **Workers/Spools:** No client-side cache (fresh on each page load for data integrity)
- **Pattern:** Lazy building - build on first request if not pre-warmed

**Rate Limiting:**
- Google Sheets API rate limits (429 handling via retry decorator)
- Exponential backoff: 1s, 2s, 4s between retries
- Max 3 retries before SheetsRateLimitError

## Architecture Decisions (v2.1)

**Direct Read vs Event Sourcing:**
- v2.0: State reconstructed from Metadata events (event sourcing)
- v2.1: State read directly from Operaciones columns (direct read)
- Rationale: Simpler, less error-prone, faster validation, Metadata is audit-only

**Column Mapping Strategy:**
- Never hardcode indices (columns shift frequently in production Sheets)
- Always map by header name (dynamic mapping via ColumnMapCache)
- Fail-fast on startup if critical columns missing

**Batch Operation Partial Success:**
- Batch operations continue on individual spool failures
- BatchActionResponse includes per-spool results + aggregate counts
- Rationale: Maximize throughput, allow user to retry only failed items

**Ownership Validation Timing:**
- Validated at COMPLETAR/CANCELAR time (not INICIAR)
- Uses worker_nombre from Sheets (format: "INICIALES(ID)")
- **CRITICAL:** Prevents unauthorized completions/cancellations
