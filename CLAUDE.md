# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**ZEUES v3.0** - Real-Time Location Tracking System for Pipe Spools

**Current Status:** v3.0 SHIPPED ✅ (2026-01-28)
- Core Value: "WHO has WHICH spool right now?" (real-time occupation tracking)
- Tech: FastAPI + Next.js + Google Sheets + Redis
- Stats: 491K LOC | 1,852 tests | 24/24 requirements | 158 commits
- Next: Planning v3.1/v4.0 milestone

**Key Features v3.0:**
- TOMAR/PAUSAR/COMPLETAR workflows (Redis locks, 1-hour TTL)
- SSE streaming (<10s latency for real-time updates)
- Metrología instant inspection (APROBADO/RECHAZADO)
- Reparación bounded cycles (max 3 before BLOQUEADO)
- Hierarchical state machines (6 states, not 27)

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
- `.planning/PROJECT.md` - Current requirements & architecture
- `.planning/STATE.md` - Current milestone state
- `.planning/MILESTONES.md` - Milestone history

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

## Google Sheets Data Model v3.0

**Operaciones Sheet (67 columns):**
- v2.1 columns (63): TAG_SPOOL, Armador, Soldador, Fecha_Armado, Fecha_Soldadura, etc.
- v3.0 NEW (4):
  - `Ocupado_Por` (64): Current worker (format: "MR(93)" or null)
  - `Fecha_Ocupacion` (65): Timestamp (DD-MM-YYYY HH:MM:SS)
  - `version` (66): UUID4 for optimistic locking
  - `Estado_Detalle` (67): Human-readable state display

**Other Sheets:**
- Trabajadores (4 cols): Id, Nombre, Apellido, Activo
- Roles (3 cols): Id, Rol, Activo (multi-role support)
- Metadata (10 cols): Event Sourcing audit trail

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

### v3.0 Endpoints

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

## v3.0 Technical Debt (Non-Blocking)

From milestone audit (2026-01-28):
- Phase 4 missing formal VERIFICATION.md
- Frontend metrología/reparación integration unverified
- No dedicated reparación router
- No E2E SSE test with real infrastructure
- 7-day rollback window expires 2026-02-02

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

**Last updated:** 2026-01-29 (optimized to ~2.5K tokens)
