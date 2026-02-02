# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**ZEUES v3.0** - Real-Time Location Tracking System for Pipe Spools

**Current Status:** v4.0 IN DEVELOPMENT - Phase 7/13 Complete (2026-02-02)
- Core Value v3.0: "WHO has WHICH spool right now?" (real-time occupation tracking)
- Core Value v4.0: Track work at the union level with correct business metric (pulgadas-diámetro)
- Tech: FastAPI + Next.js + Google Sheets + Redis
- Progress: 54% complete (7 of 13 phases), pending Engineering handoff for Uniones sheet population

**Shipped v3.0 Features:**
- TOMAR/PAUSAR/COMPLETAR workflows (Redis locks, 1-hour TTL)
- SSE streaming (<10s latency for real-time updates)
- Metrología instant inspection (APROBADO/RECHAZADO)
- Reparación bounded cycles (max 3 before BLOQUEADO)
- Hierarchical state machines (6 states, not 27)

**v4.0 In Development:**
- Union-level tracking (18-column Uniones sheet)
- INICIAR/FINALIZAR workflows (auto-determination of PAUSAR vs COMPLETAR)
- Pulgadas-diámetro business metric (DN_UNION sums)
- Batch operations with gspread.batch_update() for <1s performance
- Schema migrations complete (Operaciones: 72 cols, Metadata: 11 cols)

**See `.planning/PROJECT.md` for complete v3.0 requirements and architecture details.**

## CRITICAL: Python Virtual Environment

**ALWAYS WORK INSIDE THE VIRTUAL ENVIRONMENT**

```bash
# Activate BEFORE any work
source venv/bin/activate

# Install packages inside venv
pip install <package-name>

# Always update requirements
pip freeze > requirements.txt
```

**RULES:**
- NEVER install packages outside venv
- ALWAYS activate venv before running Python
- ALL Python work must be done with venv activated

## Tech Stack

- **Backend:** Python 3.11 + FastAPI + gspread + python-statemachine==2.5.0 + redis==5.0.1
- **Frontend:** Next.js 14 + TypeScript + Tailwind CSS
- **Data:** Google Sheets (source of truth) + Redis (locks + pub/sub)
- **Deploy:** Railway (backend) + Vercel (frontend)

## Essential Commands

### Backend (FastAPI + Python)

```bash
# Run dev server (from project root with venv active)
source venv/bin/activate
uvicorn main:app --reload --port 8000
# API: http://localhost:8000
# Docs: http://localhost:8000/api/docs

# Testing
PYTHONPATH=/Users/sescanella/Proyectos/KM/ZEUES-by-KM pytest
pytest tests/unit/ -v --tb=short
pytest tests/integration/ -v

# Package management
pip install <package>
pip freeze > requirements.txt
```

### Frontend (Next.js + TypeScript)

```bash
cd zeues-frontend

# Run dev server
npm run dev  # http://localhost:3000

# Quality checks (MUST pass before commit)
npx tsc --noEmit  # TypeScript
npm run lint      # ESLint
npm run build     # Production build

# E2E tests
npx playwright test
npx playwright show-report
```

## GSD Workflow Commands

**Start here when beginning work:**

```bash
/gsd:progress              # Check current state, get next action
/gsd:new-milestone         # Start new milestone (v3.1/v4.0)
/gsd:plan-phase 1          # Create execution plan for phase
/gsd:execute-phase 1       # Execute with atomic commits
/gsd:verify-work           # Conversational UAT
/gsd:audit-milestone       # Pre-archive audit
```

**Important Files:**
- `.planning/PROJECT.md` - Current requirements & architecture (v4.0 specifications)
- `.planning/STATE.md` - Current milestone state (Phase 7 status)
- `.planning/MILESTONES.md` - Milestone history
- `docs/engineering-handoff.md` - Uniones sheet requirements for Engineering team

## Architecture Quick Reference

### Backend (Clean Architecture)

```
main.py
├── routers/           # API endpoints (occupation, sse, history, metrologia)
├── services/          # Business logic (state, occupation, validation)
├── repositories/      # Data access (sheets, redis, metadata)
├── state_machines/    # ARM, SOLD, Metrologia, Reparacion
├── models/            # Pydantic schemas
└── exceptions.py      # Custom exceptions
```

**Key Patterns:**
- Service Layer + Repository Pattern
- Hierarchical State Machines (python-statemachine 2.5.0)
- Optimistic Locking (UUID4 version tokens)
- SSE Streaming (sse-starlette)
- Event Sourcing (Metadata sheet)

### Frontend (Next.js App Router)

```
app/                   # 7-page linear flow
├── page.tsx          # P1: Worker identification
├── operacion/        # P2: Operation selection
├── tipo-interaccion/ # P3: Action type (TOMAR/PAUSAR/COMPLETAR)
├── seleccionar-spool/# P4: Spool selection
├── confirmar/        # P5: Confirmation
└── exito/            # P6: Success

components/            # Button, Card, etc.
lib/
├── api.ts            # Native fetch (NO axios)
├── types.ts          # TypeScript interfaces
└── context.tsx       # React Context (state management)
```

## Google Sheets Data Model

**Operaciones Sheet (72 columns - v4.0 ready):**
- v2.1 columns (63): TAG_SPOOL, Armador, Soldador, Fecha_Armado, Fecha_Soldadura, etc.
- v3.0 columns (4):
  - `Ocupado_Por` (64): Current worker (format: "MR(93)" or null)
  - `Fecha_Ocupacion` (65): Timestamp (DD-MM-YYYY HH:MM:SS)
  - `version` (66): UUID4 for optimistic locking
  - `Estado_Detalle` (67): Human-readable state display
- v4.0 NEW (5):
  - `Total_Uniones` (68): Count of unions in spool
  - `Uniones_ARM_Completadas` (69): Count of completed armado unions
  - `Uniones_SOLD_Completadas` (70): Count of completed soldadura unions
  - `Pulgadas_ARM` (71): Sum of DN_UNION for completed ARM
  - `Pulgadas_SOLD` (72): Sum of DN_UNION for completed SOLD

**Uniones Sheet (18 columns - v4.0 critical, Engineering dependency):**
- Core fields: ID, TAG_SPOOL (FK), N_UNION, DN_UNION, TIPO_UNION
- ARM fields: ARM_FECHA_INICIO, ARM_FECHA_FIN, ARM_WORKER
- SOLD fields: SOL_FECHA_INICIO, SOL_FECHA_FIN, SOL_WORKER
- NDT fields: NDT_FECHA, NDT_STATUS
- System fields: version (UUID4)
- Audit fields: Creado_Por, Fecha_Creacion, Modificado_Por, Fecha_Modificacion

**⚠️ BLOCKER:** Uniones sheet missing 9 columns. See `docs/engineering-handoff.md` for population requirements.

**Other Sheets:**
- Trabajadores (4 cols): Id, Nombre, Apellido, Activo
- Roles (3 cols): Id, Rol, Activo (multi-role support)
- Metadata (11 cols - v4.0): Event Sourcing audit trail + N_UNION column

**Redis:**
- Occupation locks: `spool:{tag}:lock` (1-hour TTL)
- Pub/sub: Real-time SSE updates

**CRITICAL:** Use dynamic header mapping - NEVER hardcode column indices
```python
headers["TAG_SPOOL"]  # ✅ Good
row[0]                # ❌ Bad - indices change
```

## Date & Timezone Standards

**Timezone:** America/Santiago (Chile)

**ALWAYS use:**
```python
from backend.utils.date_formatter import now_chile, today_chile, format_date_for_sheets, format_datetime_for_sheets

# Business dates
format_date_for_sheets(today_chile())  # "21-01-2026"

# Audit timestamps
format_datetime_for_sheets(now_chile())  # "21-01-2026 14:30:00"
```

**NEVER use:** `datetime.utcnow()`, `datetime.now()`, `.isoformat()`

## TypeScript Rules

**CRITICAL: NEVER use `any` type**

```typescript
// ❌ BAD - ESLint error
data: any

// ✅ GOOD
data: unknown  // for dynamic data
data: { tag_spool: string; operacion: 'ARM' | 'SOLD' }  // for known structure
```

**Validation Commands:**
```bash
npx tsc --noEmit  # MUST pass
npm run lint      # MUST pass (no warnings)
npm run build     # MUST pass
```

## Environment Variables

**Backend (.env):**
```env
GOOGLE_SHEET_ID=17iOaq2sv4mSOuJY4B8dGQIsWTTUKPspCtb7gk6u-MaQ
HOJA_METADATA_NOMBRE=Metadata
GOOGLE_SERVICE_ACCOUNT_EMAIL=zeus-mvp@zeus-mvp.iam.gserviceaccount.com
GOOGLE_PRIVATE_KEY="-----BEGIN PRIVATE KEY-----\n...\n-----END PRIVATE KEY-----\n"

# v3.0 Redis
REDIS_URL=redis://...
REDIS_PASSWORD=...
OCCUPATION_LOCK_TTL=3600
```

**Frontend (.env.local):**
```env
NEXT_PUBLIC_API_URL=http://localhost:8000  # Dev
# NEXT_PUBLIC_API_URL=https://zeues-backend-mvp-production.up.railway.app  # Prod
```

## Debugging

### API Endpoints

**v3.0 Endpoints (Production):**
```bash
# Occupation
POST /api/occupation/tomar
POST /api/occupation/pausar
POST /api/occupation/completar
GET  /api/occupation/diagnostic/{tag}

# SSE Streaming
GET /api/sse/disponible?operacion=ARM
GET /api/sse/quien-tiene-que

# History
GET /api/history/{tag_spool}

# Cache
POST /api/cache/clear
```

**v4.0 Endpoints (Planned):**
```bash
# Union-level workflows
POST /api/iniciar          # Occupies spool without touching Uniones
POST /api/finalizar        # Union selection + auto PAUSAR/COMPLETAR
GET  /api/unions/{tag}     # List available unions for spool

# Metrics
GET /api/metrics/{tag}     # Pulgadas-diámetro performance data
```

### COMPLETAR Operation Schema

**Endpoint:** `POST /api/occupation/completar`

**Required Fields:**
```json
{
  "tag_spool": "TEST-02",
  "worker_id": 93,
  "worker_nombre": "MR(93)",
  "operacion": "ARM",                // REQUIRED: ARM, SOLD, or METROLOGIA
  "fecha_operacion": "2026-02-02"   // REQUIRED: YYYY-MM-DD format
}
```

**Optional Fields:**
```json
{
  "resultado": "APROBADO"  // Required for METROLOGIA only (APROBADO/RECHAZADO)
}
```

**Common Errors:**
- **422 Validation Error:** Missing `fecha_operacion` or `operacion` field
- **403 Forbidden:** Worker doesn't own the spool (ownership validation failed)
- **409 Conflict:** Spool not in correct state for completion
- **500 Internal Server Error:** Backend model mismatch (check Pydantic schema)

### Redis Debugging

```bash
# Check lock
redis-cli GET "spool:TEST-01:lock"

# Check TTL
redis-cli TTL "spool:TEST-01:lock"

# List all locks
redis-cli KEYS "spool:*:lock"

# Emergency release (use with caution)
redis-cli DEL "spool:TEST-01:lock"
```

## Redis Troubleshooting

### Connection Pool Exhaustion

**Symptoms:**
- "Too many connections" error in Railway logs
- 500 Internal Server Error on TOMAR/PAUSAR/COMPLETAR endpoints
- `/api/redis-health` returns `{"status": "unhealthy"}`
- High error rate on occupation operations

**Quick Fix (Emergency):**
```bash
# Restart Redis service in Railway Dashboard
# Railway → Project → Redis → Restart
# Wait 1-2 minutes for service to restart

# Verify health
curl https://zeues-backend-mvp-production.up.railway.app/api/redis-health
# Expected: {"status": "healthy", "operational": true}
```

**Permanent Fix (Implemented in v3.0):**
- Connection pool singleton pattern (`backend/core/redis_client.py`)
- Max connections: 20 (Railway-safe limit)
- Automatic connection reuse and health checks
- Monitoring endpoint: `/api/redis-connection-stats`

**Prevention:**
```bash
# Monitor connection usage
curl https://zeues-backend-mvp-production.up.railway.app/api/redis-connection-stats

# Expected response:
# {
#   "max_connections": 20,
#   "active_connections": 8,
#   "available_connections": 12,
#   "utilization_percent": 40.0
# }

# Alert if utilization > 80%
```

**Connection Pool Configuration:**
```python
# backend/config.py
REDIS_POOL_MAX_CONNECTIONS = 20  # Railway limit-safe
REDIS_SOCKET_TIMEOUT = 5
REDIS_SOCKET_CONNECT_TIMEOUT = 5
REDIS_HEALTH_CHECK_INTERVAL = 30
```

**Common Causes:**
1. Connection leaks (fixed in Phase 2 - February 2026)
2. Not using singleton pool (fixed in Phase 2)
3. High concurrent load (30-50 workers + SSE streams)
4. Long-lived SSE connections holding pools open
5. Missing connection pool configuration

**Debugging Commands:**
```bash
# Check Railway Redis logs
# Railway Dashboard → Redis → Logs

# Test basic Redis operation
curl -X POST https://zeues-backend-mvp-production.up.railway.app/api/occupation/tomar \
  -H "Content-Type: application/json" \
  -d '{"tag_spool": "TEST-02", "worker_id": 93, "worker_nombre": "MR(93)", "operacion": "ARM"}'

# Monitor connection stats real-time (requires jq)
watch -n 5 'curl -s https://zeues-backend-mvp-production.up.railway.app/api/redis-connection-stats | jq'

# Check Redis health
curl https://zeues-backend-mvp-production.up.railway.app/api/redis-health
```

**Incident History:**
- **2026-02-02:** Redis Crisis - Connection pool exhaustion causing 500 errors
  - Root cause: Missing connection pooling configuration
  - Resolution: Singleton pool with max 20 connections
  - See: `INCIDENT-POSTMORTEM-REDIS-CRISIS.md`

### Common Issues

**ImportError:**
```bash
source venv/bin/activate
PYTHONPATH=/Users/sescanella/Proyectos/KM/ZEUES-by-KM pytest
```

**Redis connection:**
```bash
redis-cli ping  # Should return PONG
python -c "import redis; r = redis.from_url('redis://localhost:6379'); print(r.ping())"
```

**SSE streaming test:**
```bash
curl -N http://localhost:8000/api/sse/disponible?operacion=ARM
```

## Schema Validation & Startup Checks

**Pre-deployment validation:**
```bash
# Validate v4.0 schema before deployment (critical + v4.0 columns)
python backend/scripts/validate_schema_startup.py

# Check Uniones sheet structure (18 columns)
python backend/scripts/validate_uniones_sheet.py

# Add missing Uniones headers (structure only, no data)
python backend/scripts/validate_uniones_sheet.py --fix
```

**FastAPI startup validation:**
- Integrated at `main.py` startup event (after cache warming)
- Validates Operaciones (72 cols), Metadata (11 cols), Uniones (18 cols)
- Deployment fails fast if schema incomplete
- Extra columns allowed, only missing columns cause failure

## Current Blockers & Technical Debt

**v4.0 Pre-Deployment Blockers:**
- ⚠️ **CRITICAL:** Uniones sheet missing 9 columns (ID, TAG_SPOOL, NDT fields, audit fields)
- Engineering handoff documentation ready: `docs/engineering-handoff.md`
- Optional automated fix available: `validate_uniones_sheet.py --fix`
- Phase 8+ blocked until Uniones data populated

**v3.0 Technical Debt (Non-Blocking):**
- Phase 4 missing formal VERIFICATION.md
- Frontend metrología/reparación integration unverified
- No dedicated reparación router
- No E2E SSE test with real infrastructure
- v2.1 7-day rollback window EXPIRED 2026-02-02 (backup archived)

## Production URLs

- Frontend: https://zeues-frontend.vercel.app
- Backend API: https://zeues-backend-mvp-production.up.railway.app
- API Docs: https://zeues-backend-mvp-production.up.railway.app/docs

## Git Workflow

- **Current Branch:** `main` (v3.0 in production)
- **Git Tag:** `v3.0` (2026-01-28)
- **Commits:** 158 commits in v3.0 milestone

**GSD creates atomic commits automatically per plan.**

## Key Constraints

- Google Sheets is source of truth (no database migration)
- Mobile-first UI (large buttons h-16/h-20, touch-friendly)
- Google Sheets limits: 60 writes/min/user, 200-500ms latency
- Manufacturing scale: 30-50 workers, 2,000+ spools, 10-15 req/sec
- Regulatory: Metadata audit trail mandatory (append-only, immutable)

---

**For detailed v3.0 architecture, requirements, and technical decisions, see `.planning/PROJECT.md`**

---

**Last updated:** 2026-02-02 (v4.0 Phase 7 complete, Engineering handoff pending)
**Document version:** 2.0
