# External Integrations

**Analysis Date:** 2026-01-26

## APIs & External Services

**Google Sheets API:**
- **What it's used for:** Single source of truth for all manufacturing data (spools, workers, roles, audit trail)
- **SDK/Client:** gspread 6.2.1 (Python HTTP client for Sheets API v4)
- **Implementation:** `backend/repositories/sheets_repository.py` - Singleton repository pattern with lazy client initialization
- **Auth:** Service Account credentials (oauth2)
  - Environment: `GOOGLE_PRIVATE_KEY`, `GOOGLE_SERVICE_ACCOUNT_EMAIL`
  - Or JSON env var: `GOOGLE_APPLICATION_CREDENTIALS_JSON` (Railway production)
- **Scopes:**
  - https://www.googleapis.com/auth/spreadsheets
  - https://www.googleapis.com/auth/drive.file
- **Features:**
  - Dynamic column mapping by header name (not hardcoded indices)
  - Retry logic with exponential backoff (3 retries, 1s base)
  - Rate limiting error handling (429 Too Many Requests)
  - Batch operations support (update_cells)
- **Calls from:**
  - `backend/services/action_service.py` - Business logic orchestration
  - `backend/services/spool_service_v2.py` - Spool state queries
  - `backend/services/worker_service.py` - Worker and role lookups
  - `backend/services/validation_service.py` - State validation

## Data Storage

**Databases:**
- **Type/Provider:** Google Sheets (no traditional database)
- **Connection:**
  - `GOOGLE_SHEET_ID=17iOaq2sv4mSOuJY4B8dGQIsWTTUKPspCtb7gk6u-MaQ` (Production)
  - Testing: `11v8fD5Shn0RSzDceZRvXhE9z4RIOBmPA9lpH5_zF-wM` (deprecated v1.0)
- **Client:** gspread (Python) for backend reads/writes
- **Data Model v2.1 (Direct Read/Write):**
  - **Operaciones** sheet (READ-ONLY for state): 65+ columns, contains spool data
    - Key columns: TAG_SPOOL, Fecha_Materiales, Armador, Fecha_Armado, Soldador, Fecha_Soldadura
    - State determined by column presence (armador != None = EN_PROGRESO)
  - **Trabajadores** sheet (READ-ONLY): Workers (4 columns: Id, Nombre, Apellido, Activo)
  - **Roles** sheet (READ-ONLY): Multi-role mapping (3 columns: Id, Rol, Activo)
  - **Metadata** sheet (APPEND-ONLY): Event log for audit trail (10 columns: id, timestamp, evento_tipo, tag_spool, worker_id, worker_nombre, operacion, accion, fecha_operacion, metadata_json)

**File Storage:**
- Local filesystem only
- Service Account JSON credentials stored in `backend/credenciales/` directory (gitignored)

**Caching:**
- In-memory column map cache: `backend/core/column_map_cache.py`
  - Caches column index mappings for each sheet
  - TTL: `CACHE_TTL_SECONDS=300` (5 minutes default)
  - Pre-warmed on app startup

## Authentication & Identity

**Auth Provider:**
- Custom Service Account authentication (no JWT or OAuth for end-users)
- Google Cloud Service Account:
  - Email: `zeus-mvp@zeus-mvp.iam.gserviceaccount.com`
  - Project ID: `zeus-mvp`
  - Credentials location: `backend/credenciales/zeus-mvp-81282fb07109.json`
  - Private key loaded via environment variables

**Frontend Worker Authentication:**
- No API authentication implemented
- Worker identified by numeric `worker_id` passed in request payload
- CORS enabled for trusted origins only: `http://localhost:3000`, `https://zeues-frontend.vercel.app`
- Worker ownership validation enforced at business logic layer (ValidationService)

## Monitoring & Observability

**Error Tracking:**
- None detected (no Sentry, DataDog, etc.)
- Custom exception hierarchy in `backend/exceptions.py` (10+ custom ZEUSException subclasses)

**Logs:**
- Python logging to console (via uvicorn)
- Log level controlled by `LOG_LEVEL` env var (default: INFO)
- Logger setup: `backend/utils/logger.py`
- Key log points:
  - App startup/shutdown in `backend/main.py`
  - Sheets API errors with retry info in `backend/repositories/sheets_repository.py`
  - Business logic warnings/info in services

**Timezone:**
- Set to America/Santiago (UTC-3 standard, UTC-4 DST)
- Configured via `TIMEZONE` env var in `backend/config.py`

## CI/CD & Deployment

**Hosting:**
- **Backend:** Railway.app (Docker container)
  - Production API: https://zeues-backend-mvp-production.up.railway.app
  - Service name: `zeues-backend`
  - Port exposed: 8000 (configurable via `PORT` env var)
- **Frontend:** Vercel (Next.js native hosting)
  - Production URL: https://zeues-frontend.vercel.app

**CI Pipeline:**
- GitHub Actions (`.github/workflows/backend.yml`)
  - Trigger: Push to main on paths: `backend/**`, `tests/**`, `requirements.txt`
  - Steps:
    1. Checkout code (actions/checkout@v3)
    2. Setup Python 3.11 (actions/setup-python@v4)
    3. Install dependencies from requirements.txt
    4. Run pytest with coverage (`--cov=backend --cov-report=xml`)
    5. Check coverage >= 80% (fail-under=80)
    6. Deploy to Railway (if tests pass)
       - Install Railway CLI (`npm install -g @railway/cli`)
       - Run `railway up --service zeues-backend`
       - Auth: `RAILWAY_TOKEN` secret

**Docker:**
- Dockerfile: Python 3.9-slim base image
- Working directory: `/app`
- PYTHONPATH: `/app` (for module imports)
- Exposed port: 8000
- Start command: `python -m uvicorn backend.main:app --host 0.0.0.0 --port ${PORT:-8000}`

## Environment Configuration

**Required env vars:**
- `GOOGLE_CLOUD_PROJECT_ID` - GCP project ID
- `GOOGLE_SHEET_ID` - Google Sheets document ID
- `GOOGLE_SERVICE_ACCOUNT_EMAIL` - Service Account email
- `GOOGLE_PRIVATE_KEY` - Service Account private key (newline-escaped)
- **OR** `GOOGLE_APPLICATION_CREDENTIALS_JSON` - Full JSON credentials (for Railway production)

**Optional env vars:**
- `GOOGLE_SERVICE_ACCOUNT_JSON_PATH` - Path to local credentials file (default: `backend/credenciales/zeus-mvp-81282fb07109.json`)
- `ENVIRONMENT` - deployment environment (development/production, default: development)
- `TIMEZONE` - timezone for date handling (default: America/Santiago)
- `API_HOST` - FastAPI host binding (default: 0.0.0.0)
- `API_PORT` - FastAPI port (default: 8000)
- `ALLOWED_ORIGINS` - CORS allowed origins, comma-separated (default: http://localhost:3000)
- `LOG_LEVEL` - Python logging level (default: INFO)
- `CACHE_TTL_SECONDS` - Column map cache TTL (default: 300)
- `NEXT_PUBLIC_API_URL` - Frontend API endpoint (default: http://localhost:8000)

**Secrets location:**
- Development: `.env.local` file (gitignored)
- Production (Railway): Environment variables in Railway dashboard
- Service Account credentials: Secure project folder (`backend/credenciales/`) in gitignore

## Webhooks & Callbacks

**Incoming:**
- None detected

**Outgoing:**
- None detected
- System is read-heavy from Sheets, write via gspread API only

## Frontend Integration Points

**API Communication:**
- Native `fetch()` API only (no axios or other HTTP library)
- Endpoint: `NEXT_PUBLIC_API_URL` environment variable
- 6 main API functions in `zeues-frontend/lib/api.ts`:
  - `getWorkers()` - GET /api/workers
  - `getSpoolsParaIniciar(operacion)` - GET /api/spools/iniciar
  - `getSpoolsParaCompletar(operacion, workerNombre)` - GET /api/spools/completar
  - `iniciarAccion(payload)` - POST /api/iniciar-accion
  - `completarAccion(payload)` - POST /api/completar-accion
  - `checkHealth()` - GET /api/health
- Additional functions for v2.1:
  - `getWorkerRoles(workerId)` - GET /api/workers/{workerId}/roles
  - `getSpoolsParaCancelar(operacion, workerId)` - GET /api/spools/cancelar
  - `cancelarAccion(payload)` - POST /api/cancelar-accion
- Batch operations:
  - `iniciarAccionBatch(request)` - POST /api/iniciar-accion-batch
  - `completarAccionBatch(request)` - POST /api/completar-accion-batch
  - `cancelarAccionBatch(request)` - POST /api/cancelar-accion-batch

## Backend API Endpoints

**Health & Metadata:**
- `GET /api/health` - System health check (Sheets connectivity)
- `GET /` - Root endpoint with API info

**Read-Only:**
- `GET /api/workers` - List active workers
- `GET /api/workers/{worker_id}/roles` - Get worker roles
- `GET /api/spools/iniciar?operacion={ARM|SOLD}` - Spools available to start
- `GET /api/spools/completar?operacion={ARM|SOLD}&worker_nombre={name}` - Spools to complete
- `GET /api/spools/cancelar?operacion={ARM|SOLD}&worker_id={id}` - Spools to cancel

**Write Operations:**
- `POST /api/iniciar-accion` - Start manufacturing action
- `POST /api/completar-accion` - Complete action (ownership validated)
- `POST /api/cancelar-accion` - Cancel action (ownership validated)
- `POST /api/iniciar-accion-batch` - Start multiple actions (up to 50)
- `POST /api/completar-accion-batch` - Complete multiple actions (up to 50)
- `POST /api/cancelar-accion-batch` - Cancel multiple actions (up to 50)

**Error Handling:**
- Standard HTTP status codes (400, 403, 404, 429, 500, 503)
- JSON error response: `{success: false, error: "ERROR_CODE", message: "...", data: null}`
- Custom exception mapping in `backend/main.py` exception handlers

---

*Integration audit: 2026-01-26*
