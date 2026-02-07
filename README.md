# ZEUES - Manufacturing Traceability System

[![v4.0](https://img.shields.io/badge/version-4.0--single--user-orange)](https://github.com)
[![Production](https://img.shields.io/badge/status-production-green)](https://zeues-frontend.vercel.app)
[![Backend](https://img.shields.io/badge/backend-railway-blue)](https://zeues-backend-mvp-production.up.railway.app)
[![Frontend](https://img.shields.io/badge/frontend-vercel-black)](https://zeues-frontend.vercel.app)

Digital mobile-first system for tracking manufacturing actions on pipe spools. Answers one question: **"WHO has WHICH spool right now?"**

Optimized for single-tablet use on the manufacturing floor with glove-friendly touch targets and Google Sheets as the source of truth.

---

## Production

| Service  | URL |
|----------|-----|
| Frontend | https://zeues-frontend.vercel.app |
| Backend  | https://zeues-backend-mvp-production.up.railway.app |
| API Docs | https://zeues-backend-mvp-production.up.railway.app/docs |

---

## Features

- **Occupation tracking** - INICIAR/FINALIZAR workflows with automatic PAUSAR vs COMPLETAR determination
- **Union-level tracking** - Individual union records per spool (Armado & Soldadura)
- **Metrologia** - Instant inspection workflow (APROBADO/RECHAZADO)
- **Reparacion** - Bounded repair cycles (max 3 before BLOQUEADO)
- **Hierarchical state machines** - ARM, SOLD, Metrologia, Reparacion
- **Pulgadas-diametro metrics** - DN_UNION sum business metric
- **P5 Confirmation Workflow** - All writes happen only at user confirmation
- **Audit trail** - Event Sourcing via Metadata sheet (append-only, immutable)
- **Blueprint Industrial UI** - Dark theme (#001F3F), orange accents (#FF6B35), WCAG 2.1 AA
- **Mobile-first** - Large buttons (h-16/h-20), touch-friendly for manufacturing floor

---

## Tech Stack

| Layer          | Technology |
|----------------|------------|
| Backend        | Python 3.11 + FastAPI + gspread + python-statemachine 2.5.0 |
| Frontend       | Next.js 14 + TypeScript + Tailwind CSS |
| Data           | Google Sheets (single source of truth) |
| State mgmt     | React Context API |
| Backend deploy | Railway |
| Frontend deploy| Vercel |
| Backend tests  | Pytest (48 test files) |
| Frontend tests | Jest + @testing-library/react (unit), Playwright (E2E) |
| Accessibility  | jest-axe + axe-core + Playwright a11y |

---

## Architecture

### Single-User Mode

ZEUES is designed for **1 tablet, 1 worker** at a time. This simplifies the architecture:

- No distributed locks
- No real-time sync
- Direct Google Sheets validation (Ocupado_Por column check)
- Last-Write-Wins (LWW) for race conditions

### Backend (Clean Architecture)

```
main.py
backend/
  routers/              # API endpoints
    occupation_v4.py    #   INICIAR/FINALIZAR (P5 workflow)
    union_router.py     #   Union CRUD + metrics
    metrologia.py       #   Inspection workflow
    health.py           #   Health check
    workers.py          #   Worker listing
    spools.py           #   Spool queries
    history.py          #   Audit history
    diagnostic.py       #   Spool diagnostic
    dashboard_router.py #   Dashboard data
    actions.py          #   Legacy actions
  services/             # Business logic
    occupation_service.py     # INICIAR/FINALIZAR orchestration
    validation_service.py     # Business rule validation
    state_service.py          # State machine transitions
    union_service.py          # Union operations
    metrologia_service.py     # Inspection logic
    reparacion_service.py     # Repair cycles
    conflict_service.py       # Version-aware updates
    estado_detalle_builder.py # Human-readable state display
    metadata_event_builder.py # Audit event construction
    state_machines/           # Hierarchical FSMs
      arm_state_machine.py
      sold_state_machine.py
      reparacion_state_machine.py
      base_state_machine.py
  repositories/         # Data access (Google Sheets)
    sheets_repository.py    # Core Sheets operations
    union_repository.py     # Uniones sheet access
    metadata_repository.py  # Event Sourcing audit trail
    role_repository.py      # Worker roles
  models/               # Pydantic schemas (16 modules)
  utils/                # Date formatting, helpers
  core/                 # App configuration
```

### Frontend (Next.js App Router)

```
zeues-frontend/
  app/                        # 7+ page flow
    page.tsx                  # P1: Operation selection (ARM/SOLD/MET/REP)
    operacion/                # P2: Worker identification (filtered by role)
    tipo-interaccion/         # P3: Action type (INICIAR/FINALIZAR)
    seleccionar-spool/        # P4: Spool selection (multi-select)
    seleccionar-uniones/      # P4b: Union selection
    confirmar/                # P5: Confirmation (writes happen here)
    exito/                    # P6: Success + auto-redirect
    resultado-metrologia/     # Metrologia results
    dashboard/                # Dashboard view
  components/                 # Reusable UI components
    SpoolTable.tsx            #   3-column spool table (SEL, NV, TAG)
    SpoolFilterPanel.tsx      #   Collapsible filter panel
    SpoolSelectionFooter.tsx  #   Selection count + continue button
    BatchLimitModal.tsx       #   Batch size limit warning
    UnionTable.tsx            #   Union selection table
    BlueprintPageWrapper.tsx  #   Page layout wrapper
    Modal.tsx / ErrorMessage.tsx / Loading.tsx / FixedFooter.tsx
  lib/
    api.ts                    # Native fetch (no axios)
    types.ts                  # TypeScript interfaces
    context.tsx               # React Context (global state)
    error-classifier.ts       # Error categorization
    operation-config.ts       # Operation definitions
    spool-selection-utils.ts  # Selection helpers
    hooks/                    # Custom React hooks
```

### Google Sheets Data Model

| Sheet | Columns | Purpose |
|-------|---------|---------|
| Operaciones | 72 | Spool master data + occupation + v4.0 counters |
| Uniones | 17 | Individual union records (ARM/SOLD/NDT) |
| Trabajadores | 4 | Worker registry (Id, Nombre, Apellido, Activo) |
| Roles | 3 | Multi-role support (Id, Rol, Activo) |
| Metadata | 11 | Event Sourcing audit trail (append-only) |

---

## User Flow

```
P1: Worker Identification
  |  (select name from list)
P2: Operation Selection (ARM / SOLD / MET / REP)
  |
P3: Action Type (INICIAR / FINALIZAR)
  |
P4: Spool Selection (filtered, multi-select)
  |  (P4b: Union selection for v4.0 spools)
P5: Confirmation (all writes happen here)
  |
P6: Success (auto-redirect to P1 after 5s)
```

---

## API Endpoints

```
# Health
GET  /api/health

# Workers
GET  /api/workers

# Occupation (v4.0 - P5 Workflow)
POST /api/v4/occupation/iniciar     # Write Ocupado_Por at confirmation
POST /api/v4/occupation/finalizar   # Process unions + auto PAUSAR/COMPLETAR

# Unions
GET  /api/v4/unions/{tag}           # List unions for spool
GET  /api/v4/metricas/{tag}         # Pulgadas-diametro metrics

# Spools
POST /api/spools/iniciar            # Available spools for operation
POST /api/spools/completar          # Worker's active spools

# Diagnostic
GET  /api/occupation/diagnostic/{tag}

# History
GET  /api/history/{tag_spool}

# Cache
POST /api/cache/clear
```

---

## Local Setup

### Prerequisites

- Python 3.11+
- Node.js 18+
- Google Cloud Service Account with Sheets API access

### Backend

```bash
# Activate virtual environment (REQUIRED)
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Configure environment
cp .env.example .env.local
# Edit with Google Service Account credentials

# Run dev server
uvicorn main:app --reload --port 8000
# API: http://localhost:8000
# Docs: http://localhost:8000/api/docs

# Run tests
PYTHONPATH=/Users/sescanella/Proyectos/KM/ZEUES-by-KM pytest tests/unit/ -v --tb=short
```

### Frontend

```bash
cd zeues-frontend

# Install dependencies
npm install

# Configure environment
echo "NEXT_PUBLIC_API_URL=http://localhost:8000" > .env.local

# Run dev server
npm run dev
# App: http://localhost:3000

# Quality checks (must pass before commit)
npx tsc --noEmit
npm run lint
npm run build

# Tests
npx jest                  # Unit tests
npx playwright test       # E2E tests
```

---

## Environment Variables

### Backend (.env.local)

```env
GOOGLE_SHEET_ID=17iOaq2sv4mSOuJY4B8dGQIsWTTUKPspCtb7gk6u-MaQ
HOJA_METADATA_NOMBRE=Metadata
GOOGLE_SERVICE_ACCOUNT_EMAIL=zeus-mvp@zeus-mvp.iam.gserviceaccount.com
GOOGLE_PRIVATE_KEY="-----BEGIN PRIVATE KEY-----\n...\n-----END PRIVATE KEY-----\n"
```

### Frontend (.env.local)

```env
NEXT_PUBLIC_API_URL=http://localhost:8000
```

---

## Deployment

| Service | Platform | Config |
|---------|----------|--------|
| Backend | Railway | Python 3.11, `uvicorn main:app --host 0.0.0.0 --port $PORT` |
| Frontend | Vercel | Next.js 14, auto-deploy from `main` |

```bash
# Railway CLI
railway logs       # View production logs
railway up         # Deploy from local
railway redeploy   # Force redeploy
```

---

## Security

- Google Service Account credentials stored only in Railway env vars (never in Git)
- `.env`, `.env.local`, `credenciales/` all in `.gitignore`
- Git history audited (2026-02-06) - no credential leaks found
- Debug endpoints removed (Feb 2026) - reduced attack surface
- Single public endpoint: `GET /api/health`

---

## Key Constraints

- Google Sheets is the sole source of truth (no database)
- Google Sheets limits: 60 writes/min/user, 200-500ms latency
- Manufacturing scale: 30-50 workers, 2,000+ spools
- Metadata audit trail is mandatory (append-only, immutable)
- Mobile-first UI with glove-friendly touch targets
- WCAG 2.1 Level AA accessibility compliance
- Timezone: America/Santiago (Chile)

---

## Project

**Client:** Kronos Mining
**System:** ZEUES (Manufacturing Traceability System)
**License:** Private - Kronos Mining

---

**Last updated:** 2026-02-07
**Version:** 4.0-single-user
