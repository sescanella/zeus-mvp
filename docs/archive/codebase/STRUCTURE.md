# Codebase Structure

**Analysis Date:** 2026-01-26

## Directory Layout

```
ZEUES-by-KM/
├── backend/                    # Python FastAPI backend (REST API, Google Sheets integration)
│   ├── main.py                 # FastAPI app entry point, middleware, exception handlers
│   ├── config.py               # Configuration (env vars, sheet IDs, constants)
│   ├── exceptions.py           # ZEUSException hierarchy (error codes, messages)
│   ├── core/                   # Core infrastructure
│   │   ├── column_map_cache.py # Dynamic column mapping cache (v2.1)
│   │   └── dependency.py       # FastAPI Depends() factories (service injection)
│   ├── models/                 # Pydantic domain models
│   │   ├── worker.py           # Worker model (id, nombre, apellido, activo, roles)
│   │   ├── spool.py            # Spool model (tag_spool, estados, fechas, trabajadores)
│   │   ├── action.py           # Action models (ActionRequest, ActionResponse, Batch*)
│   │   ├── metadata.py         # MetadataEvent model (audit trail)
│   │   ├── role.py             # Role model (worker roles)
│   │   ├── enums.py            # Enums (ActionType, ActionStatus, Accion)
│   │   └── error.py            # ErrorResponse model
│   ├── repositories/           # Data access layer (Google Sheets API)
│   │   ├── sheets_repository.py   # Main Sheets CRUD (gspread client)
│   │   ├── metadata_repository.py # Metadata sheet append operations
│   │   └── role_repository.py     # Roles sheet queries
│   ├── services/               # Business logic layer (orchestration, validation)
│   │   ├── action_service.py      # INICIAR/COMPLETAR/CANCELAR workflows + batch
│   │   ├── validation_service.py  # State validation, ownership checks (CRITICAL)
│   │   ├── spool_service.py       # Spool queries (find by TAG)
│   │   ├── worker_service.py      # Worker queries (find by ID)
│   │   ├── role_service.py        # Role validation (worker has role for operation)
│   │   └── sheets_service.py      # Sheets integration helpers (legacy)
│   ├── routers/                # HTTP endpoints (thin controllers)
│   │   ├── health.py           # GET /api/health (connectivity check)
│   │   ├── workers.py          # GET /api/workers (list active workers)
│   │   ├── spools.py           # GET /api/spools/iniciar, /completar, /cancelar
│   │   └── actions.py          # POST /api/iniciar-accion, /completar-accion, /cancelar-accion
│   ├── utils/                  # Utilities
│   │   ├── logger.py           # Logging setup
│   │   ├── date_formatter.py   # Date formatting (DD-MM-YYYY for Sheets)
│   │   └── cache.py            # General cache utilities
│   └── requirements.txt        # Python dependencies (fastapi, gspread, pydantic, pytest)
│
├── zeues-frontend/             # Next.js React frontend (mobile-first tablet UI)
│   ├── app/                    # Next.js App Router (7-page linear flow)
│   │   ├── layout.tsx          # Root layout (AppProvider wrapper)
│   │   ├── page.tsx            # P1: Operation selection (ARM/SOLD/MET/REP)
│   │   ├── operacion/page.tsx  # P2: Worker identification (filtered by role)
│   │   ├── tipo-interaccion/page.tsx  # P3: Action type (INICIAR/COMPLETAR/CANCELAR)
│   │   ├── seleccionar-spool/page.tsx # P4: Spool selection (table, multiselect, search)
│   │   ├── confirmar/page.tsx  # P5: Confirmation summary (batch/single)
│   │   ├── exito/page.tsx      # P6: Success page (5sec auto-redirect to P1)
│   │   └── globals.css         # Global Tailwind styles
│   ├── components/             # Reusable React components
│   │   ├── Button.tsx          # Button (Tailwind, lg size for tablets)
│   │   ├── Card.tsx            # Card (worker/spool display)
│   │   ├── Checkbox.tsx        # Checkbox (multiselect rows)
│   │   ├── ErrorMessage.tsx    # Error display
│   │   ├── Loading.tsx         # Loading spinner
│   │   ├── NavigationHeader.tsx # Navigation bar (Volver/Cancelar buttons)
│   │   ├── SpoolTable.tsx      # Spool data table with filtering
│   │   ├── SpoolSearch.tsx     # Search input for spools
│   │   ├── SpoolSelector.tsx   # Multiselect logic + checkbox management
│   │   ├── List.tsx            # Generic list component
│   │   └── index.ts            # Barrel export
│   ├── lib/                    # Utilities and state management
│   │   ├── api.ts              # API client functions (fetch-based, 9+ functions)
│   │   ├── context.tsx         # React Context API (AppState, worker/operation/spools)
│   │   └── types.ts            # TypeScript interfaces (Worker, Spool, ActionResponse, etc.)
│   ├── e2e/                    # Playwright E2E tests (9+ test suites)
│   │   ├── 01-iniciar-arm.spec.ts
│   │   ├── 02-completar-arm.spec.ts
│   │   ├── 03-iniciar-sold.spec.ts
│   │   ├── 04-completar-sold.spec.ts
│   │   ├── 05-error-handling.spec.ts
│   │   ├── 06-cancelacion.spec.ts
│   │   ├── 07-multiselect-batch.spec.ts
│   │   ├── 08-search-filter.spec.ts
│   │   └── 09-batch-cancelar.spec.ts
│   ├── public/logos/           # Static assets (logos)
│   ├── tailwind.config.ts      # Tailwind configuration
│   ├── next.config.js          # Next.js configuration
│   ├── tsconfig.json           # TypeScript configuration
│   ├── playwright.config.ts    # Playwright configuration
│   └── package.json            # Dependencies (next, react, tailwindcss, playwright)
│
├── tests/                      # Python backend tests (pytest)
│   ├── unit/                   # Unit tests (services, models, helpers)
│   │   ├── test_validation_service.py       # ValidationService tests (60+ tests)
│   │   ├── test_action_service.py
│   │   ├── test_spool_service.py
│   │   └── test_worker_service.py
│   ├── integration/            # Integration tests (with mock Sheets)
│   │   ├── test_sheets_repository.py
│   │   └── test_action_integration.py
│   └── e2e/                    # E2E tests (real Sheets connection)
│       └── test_full_workflow.py
│
├── docs/                       # Documentation
│   └── GOOGLE-RESOURCES.md     # Google Sheets configuration (URLs, credentials)
│
├── credenciales/               # Service Account credentials (NEVER commit)
│   └── zeus-mvp-*.json         # Service Account JSON key
│
├── .planning/codebase/         # GSD planning documents
│   ├── ARCHITECTURE.md         # This file - Architecture patterns, layers, data flow
│   ├── STRUCTURE.md            # Directory layout, naming conventions
│   ├── STACK.md                # Technology stack
│   ├── INTEGRATIONS.md         # External APIs and services
│   ├── CONVENTIONS.md          # Code style, naming patterns
│   ├── TESTING.md              # Testing framework and patterns
│   └── CONCERNS.md             # Technical debt, issues, fragile areas
│
├── .github/workflows/          # CI/CD pipeline definitions
├── .env.local                  # Environment variables (NEVER commit)
├── proyecto-v2.md              # v2.1 Project roadmap and status
├── proyecto-v2-backend.md      # v2.1 Backend technical documentation
├── proyecto-v2-frontend.md     # v2.1 Frontend technical documentation
├── CLAUDE.md                   # Claude Code guidance (this file references it)
└── pyproject.toml              # Python project metadata
```

## Directory Purposes

**backend/**
- Purpose: REST API server for manufacturing actions
- Contains: Python service layer, repositories, models, HTTP routes
- Key files: `main.py` (app), `exceptions.py` (error handling), `config.py` (env config)

**zeues-frontend/**
- Purpose: Mobile-first tablet UI for workers
- Contains: Next.js App Router pages, React components, E2E tests
- Key files: `app/page.tsx` (worker selection), `lib/api.ts` (API client), `lib/context.tsx` (state)

**backend/services/**
- Purpose: Business logic orchestration
- Contains: ActionService (workflows), ValidationService (rules), RoleService, SpoolService, WorkerService
- Pattern: Dependency injection for testability; pure functions in ValidationService

**backend/repositories/**
- Purpose: Data access abstraction
- Contains: SheetsRepository (gspread client), MetadataRepository (audit logs), RoleRepository
- Pattern: Retry decorator, lazy initialization, ColumnMapCache for dynamic columns

**backend/models/**
- Purpose: Domain object definitions
- Contains: Pydantic models (schemas), Enums (ActionType, ActionStatus, Accion)
- Pattern: Type safety, FastAPI automatic documentation

**zeues-frontend/components/**
- Purpose: Reusable UI components
- Contains: Button, Card, Checkbox, Table, etc. - all Tailwind-styled
- Pattern: Props-based, functional components, no business logic (dumb components)

**zeues-frontend/lib/**
- Purpose: Utilities and state management
- Contains: `api.ts` (fetch functions), `context.tsx` (React Context), `types.ts` (TypeScript interfaces)
- Pattern: No Redux/Zustand - simple Context API for MVP

**tests/**
- Purpose: Test coverage (unit, integration, E2E)
- Contains: pytest fixtures, Playwright E2E tests
- Pattern: Test data factories, mocking Google Sheets API

## Key File Locations

**Entry Points:**
- Backend: `backend/main.py` (FastAPI app, starts at `uvicorn main:app --reload`)
- Frontend: `zeues-frontend/app/layout.tsx` (Next.js root layout, wrapped with AppProvider)

**Configuration:**
- Backend: `backend/config.py` (env vars: GOOGLE_SHEET_ID, ALLOWED_ORIGINS, etc.)
- Frontend: `zeues-frontend/.env.local` (NEXT_PUBLIC_API_URL)

**Core Logic:**
- Action workflows: `backend/services/action_service.py` (iniciar/completar/cancelar + batch)
- Validation rules: `backend/services/validation_service.py` (ownership, state checks - **CRITICAL**)
- Sheets integration: `backend/repositories/sheets_repository.py` (CRUD via gspread)

**Testing:**
- Backend unit tests: `tests/unit/` (pytest, 244+ passing tests)
- Frontend E2E tests: `zeues-frontend/e2e/` (Playwright, 9 test suites)

## Naming Conventions

**Files:**
- Backend: `snake_case.py` (e.g., `action_service.py`, `sheets_repository.py`)
- Frontend: `PascalCase.tsx` for components (e.g., `Button.tsx`, `SpoolTable.tsx`)
- Frontend: `camelCase.ts` for utilities (e.g., `api.ts`, `context.tsx`)
- Test files: `test_*.py` (Python) or `*.spec.ts` (Playwright)

**Functions:**
- Backend: `snake_case` with leading underscore for private (e.g., `_get_client()`, `validar_puede_iniciar_arm()`)
- Frontend: `camelCase` for functions, `PascalCase` for React components
- Async functions: `async def/function` (clearly marked)

**Variables:**
- Backend: `snake_case` for all (e.g., `action_service`, `tag_spool`, `worker_id`)
- Frontend: `camelCase` for all (e.g., `selectedWorker`, `tagSpool`, `workerId`)
- Constants: `UPPER_SNAKE_CASE` (e.g., `MAX_BATCH_SIZE = 50`, `API_URL`)

**Types:**
- TypeScript interfaces: `PascalCase` (e.g., `Worker`, `ActionResponse`, `BatchActionRequest`)
- Pydantic models: `PascalCase` (e.g., `Spool`, `ActionRequest`, `MetadataEvent`)
- Enums: `PascalCase` class name, `UPPER_CASE` values (e.g., `ActionType.ARM`, `ActionStatus.PENDIENTE`)

**URL Routes:**
- Backend: `/api/{resource}/{action}` (kebab-case)
  - Examples: `/api/workers`, `/api/spools/iniciar`, `/api/iniciar-accion`
- Frontend: kebab-case directory names for routes
  - Examples: `/operacion`, `/tipo-interaccion`, `/seleccionar-spool`, `/confirmar`

## Where to Add New Code

**New Feature (e.g., METROLOGIA operation):**
- Model: Add to `backend/models/enums.py` (ActionType enum)
- Validation: Add `validar_puede_iniciar_metrologia()` in `backend/services/validation_service.py`
- Workflow: Add branch in `backend/services/action_service.py` (iniciar_accion method)
- Endpoint: Extend `backend/routers/actions.py` (router already handles via ActionType param)
- Frontend: Add METROLOGIA option in `zeues-frontend/app/tipo-interaccion/page.tsx`

**New Component:**
- Create file: `zeues-frontend/components/ComponentName.tsx`
- Export in: `zeues-frontend/components/index.ts` (barrel export)
- Use: Import from `@/components` in pages
- Pattern: Export named function component (not default)

**New Service:**
- Create file: `backend/services/service_name.py`
- Pattern: Class-based with __init__ (dependency injection)
- Export in: `backend/core/dependency.py` via `get_service_name()` factory
- Inject: Use FastAPI `Depends()` in routers

**New Repository:**
- Create file: `backend/repositories/repository_name.py`
- Pattern: Class-based with __init__, include retry decorator where needed
- Responsibility: Single data source (e.g., one sheet or external API)

**New Utility:**
- Backend: Add to `backend/utils/` (logger.py, date_formatter.py, etc.)
- Frontend: Add to `zeues-frontend/lib/` (api.ts, types.ts, etc.)

## Special Directories

**backend/core/**
- Purpose: Core infrastructure (not business logic)
- Generated: No (hand-written)
- Committed: Yes
- Contents: ColumnMapCache (v2.1), dependency injection factories

**backend/.pytest_cache/**
- Purpose: pytest cache directory
- Generated: Yes (auto-created by pytest)
- Committed: No (.gitignore)

**zeues-frontend/.next/**
- Purpose: Next.js build output
- Generated: Yes (by `npm run build`)
- Committed: No (.gitignore)

**zeues-frontend/playwright-report/**
- Purpose: Playwright test report HTML
- Generated: Yes (by `npx playwright test`)
- Committed: No (.gitignore)

**tests/**
- Purpose: Test suites (unit, integration, E2E)
- Generated: No (hand-written)
- Committed: Yes
- Pattern: Mirror backend structure (tests/unit/test_services.py mirrors backend/services/)

**.planning/codebase/**
- Purpose: GSD planning and analysis documents
- Generated: No (manually maintained or AI-generated)
- Committed: Yes (part of orchestration system)

**credenciales/**
- Purpose: Google Cloud Service Account credentials
- Generated: No (from Google Cloud Console)
- Committed: No (CRITICAL - .gitignore prevents accidental exposure)
- Security: Store locally or in environment variables only

**.env.local**
- Purpose: Environment variables for development
- Generated: No (manually created)
- Committed: No (.gitignore)
- Contents: GOOGLE_PRIVATE_KEY, GOOGLE_SHEET_ID, etc.

## Adding New Code Patterns

**Adding a New Validation Rule:**
1. Create method in `ValidationService` (e.g., `validar_puede_iniciar_metrologia`)
2. Raise appropriate ZEUSException subclass on failure
3. Call from `ActionService` at appropriate workflow step
4. Exception automatically maps to HTTP status via handler

**Adding a New API Endpoint:**
1. Add POST/GET route in appropriate router (e.g., `backend/routers/actions.py`)
2. Define request model (Pydantic) and response model
3. Call service method via `Depends(get_action_service)`
4. Return model (FastAPI serializes automatically)
5. Document with docstring + OpenAPI annotations

**Adding a New Frontend Page:**
1. Create directory: `zeues-frontend/app/new-page/`
2. Create file: `zeues-frontend/app/new-page/page.tsx`
3. Use `useAppState()` hook for context access
4. Use `useRouter()` for navigation
5. Call API functions from `lib/api.ts`
6. Render components from `components/`

**Adding a Google Sheets Integration:**
1. Add column header mapping in `ColumnMapCache` (dynamic, don't hardcode)
2. Add read method in `SheetsRepository` (e.g., `read_special_column()`)
3. Wrap with retry decorator for resilience
4. Create repository class if different source (e.g., `MetadataRepository`)
5. Test with mock Sheets data in `tests/`

**Testing a New Feature:**
- Backend: Add test in `tests/unit/test_service_name.py` or `tests/integration/`
- Frontend: Add Playwright test in `zeues-frontend/e2e/NN-feature-name.spec.ts`
- Pattern: Setup → Action → Assert; use fixtures for data

**Adding Batch Operation Support:**
1. Implement single operation first (e.g., `action_service.iniciar_accion()`)
2. Add batch variant: `iniciar_accion_batch(worker_id, operacion, tag_spools[])`
3. Loop over tag_spools, catch exceptions per item
4. Return `BatchActionResponse` with exitosos/fallidos counts
5. Frontend multiselect → API batch call
