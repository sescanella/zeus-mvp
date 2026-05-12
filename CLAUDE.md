# CLAUDE.md

Guidance for Claude Code working in this repository.

## External Orchestrator — ASISTENTE

This repository is the codebase. Strategic coordination, task tracking, and cross-project context live in a separate orchestrator at:

```
/Users/sescanella/Documents/Obsidian Vault/Proyectos/ASISTENTE
```

Relevant subtree for Zeus:

```
ASISTENTE/planning/proyectos/zeus-by-km/
├── pointer.md                       Map of this repo (paths, layers, shortcuts per task)
├── bugs-pendientes.md               Active bugs reported in production by Matías
├── v5.1-scope.md                    UX/feature backlog for next milestone
├── auditoria-YYYY-MM-DD-*.md        Technical audits done from ASISTENTE
├── HANDOFF-TO-ZEUS.md               Handoff note for starting a Zeus session
└── notas.md                         Tech debt, decisions

ASISTENTE/planning/tareas.md         All open tasks (IDs like T-095, T-096...)
ASISTENTE/planning/clientes/kronos/  Client-level context (Matías, Pablo, etc.)
```

### When to read ASISTENTE files

Read the orchestrator **at session start** if the operator mentions any of these signals:

- A task ID with prefix `T-NNN` (e.g., "trabajemos T-096").
- A bug ID with prefix `B-N` (e.g., "Bug 6").
- Phrases like "la auditoría", "el handoff", "lo que venimos trabajando".
- The operator opened this chat right after a session in ASISTENTE.

**What to read** (in this order):

1. `ASISTENTE/planning/proyectos/zeus-by-km/HANDOFF-TO-ZEUS.md` — single entry point. Lists hot tasks, recent audits, and what to do first.
2. The specific audit file referenced in the handoff.
3. `bugs-pendientes.md` or `v5.1-scope.md` as the handoff directs.

If there is no signal from the operator, do not proactively read the orchestrator — work from repo context as usual.

### What to write back to ASISTENTE

**By default, do not write to ASISTENTE from this chat.** Leave feedback via:

- Git commit messages referencing the task ID: `fix(T-096): metrologia auto-trigger respects total_uniones`.
- Branch names carrying the ID: `fix/T-096-metrologia-partial-sold`.

**Exception**: if the operator explicitly asks to update the orchestrator from here, edit under `ASISTENTE/planning/proyectos/zeus-by-km/` only. Never touch `ASISTENTE/planning/tareas.md` or client dashboards.

### Language

ASISTENTE is in Spanish. This repo is in English. Keep the separation.

## Project Overview

**ZEUES** — Location tracking system for pipe spools in manufacturing.

- **Stack:** FastAPI + Next.js + Google Sheets (single source of truth).
- **Deployment:** Railway (backend) + Vercel (frontend), auto-deploy from `main`.
- **Scale:** single-user mode (one tablet, one worker at a time). No distributed locks, no real-time sync.
- **Current milestone:** v5.x (single-page frontend, modal-based flow). History of v3.0/v4.0/v5.0 audits in `docs/archive/milestones/`.

**Core workflows:**
- TOMAR / PAUSAR / COMPLETAR (direct Sheets updates).
- INICIAR / FINALIZAR (P5 Confirmation Workflow: writes happen only on confirmation; FINALIZAR auto-determines CANCELADO / PAUSAR / COMPLETAR based on union completion).
- Metrología inspection (APROBADO / RECHAZADO).
- Reparación unlimited cycles (spools can be rejected and repaired indefinitely).
- Pulgadas-diámetro business metric (DN_UNION sums).

## CRITICAL: Python Virtual Environment

**ALWAYS WORK INSIDE THE VIRTUAL ENVIRONMENT.**

```bash
source venv/bin/activate         # before any Python work
pip install <package>            # inside venv only
pip freeze > requirements.txt    # always update after adding deps
```

**Rules:**
- NEVER install packages outside venv.
- ALWAYS activate venv before running Python.
- ALL Python work happens with venv activated.

## Tech Stack

- **Backend:** Python 3.11, FastAPI, gspread, python-statemachine 2.5.0
- **Frontend:** Next.js 14 (App Router), TypeScript, Tailwind CSS, native `fetch` (no axios)
- **Data:** Google Sheets
- **Deploy:** Railway (backend) + Vercel (frontend)

## Essential Commands

### Backend

```bash
source venv/bin/activate
uvicorn main:app --reload --port 8000      # http://localhost:8000  (docs: /api/docs)

PYTHONPATH="$(pwd)" pytest                  # all tests
pytest tests/unit/ -v --tb=short            # unit only
pytest tests/integration/ -v                # integration
```

### Frontend

```bash
cd zeues-frontend
npm run dev                  # http://localhost:3000
npx tsc --noEmit             # must pass before commit
npm run lint                 # must pass (no warnings)
npm run build                # must pass
npx playwright test          # E2E
```

### Railway

```bash
railway logs        # production logs
railway variables   # env vars
railway up          # deploy from local
railway status      # deployment status
```

## Architecture Quick Reference

### Backend (Clean Architecture)

```
main.py
├── routers/          API endpoints (occupation_v4, union_router, metrologia, history, health, ...)
├── services/         Business logic (occupation_service, union_service, state_service, ...)
├── repositories/     Data access (sheets_repository, union_repository, metadata_repository)
├── state_machines/   ARM, SOLD, Metrologia, Reparacion (hierarchical)
├── models/           Pydantic schemas
└── exceptions.py     Custom exceptions
```

**Patterns:** Service Layer + Repository Pattern, hierarchical state machines, direct Sheets validation (`Ocupado_Por` column check), event sourcing via the Metadata sheet.

### Frontend (Next.js App Router, single-page)

```
zeues-frontend/app/
├── page.tsx         Main single-page app (worker + spool selection, actions)
├── dashboard/       Supervisor dashboard view
├── mi-registro/     Worker self-registration flow
├── layout.tsx
└── globals.css

zeues-frontend/components/
├── ActionModal, OperationModal, MetrologiaModal, UnionesModal, NotasModal, WorkerModal,
│   AddSpoolModal, Modal, SpoolCard, SpoolTable, SpoolFilterPanel, ...

zeues-frontend/lib/
├── api.ts                  Native fetch (NO axios); all API calls go here
├── types.ts                TypeScript interfaces
├── SpoolListContext.tsx    React Context for spool state
├── spool-state-machine.ts  Frontend state machine
└── error-classifier.ts, haptic.ts, local-storage.ts, operation-config.ts, constants.ts
```

## Google Sheets Data Model

**Operaciones Sheet (71 columns):**
- v2.1 columns (1–63): TAG_SPOOL, Armador, Soldador, Fecha_Armado, Fecha_Soldadura, etc.
- Occupation columns (64–66): `Ocupado_Por` (e.g. `"MR(93)"` or empty), `Fecha_Ocupacion` (DD-MM-YYYY HH:MM:SS), `Estado_Detalle`.
- v4.0 counters (67–71): `Total_Uniones`, `Uniones_ARM_Completadas`, `Uniones_SOLD_Completadas`, `Pulgadas_ARM`, `Pulgadas_SOLD`.

**Uniones Sheet (17 columns):**
- Core: `ID`, `OT`, `N_UNION`, `TAG_SPOOL`, `DN_UNION`, `TIPO_UNION`
- ARM: `ARM_FECHA_INICIO`, `ARM_FECHA_FIN`, `ARM_WORKER`
- SOLD: `SOL_FECHA_INICIO`, `SOL_FECHA_FIN`, `SOL_WORKER`
- NDT: `NDT_UNION`, `R_NDT_UNION`, `NDT_FECHA`, `NDT_STATUS`

**Other sheets:**
- Trabajadores (4 cols): `Id`, `Nombre`, `Apellido`, `Activo`
- Roles (3 cols): `Id`, `Rol`, `Activo` (multi-role)
- Metadata (11 cols): event-sourcing audit trail (append-only, immutable)

**CRITICAL — dynamic header mapping, never indices:**

```python
headers["TAG_SPOOL"]    # ✅
row[0]                  # ❌ indices drift
```

## Date & Timezone Standards

**Timezone:** America/Santiago (Chile).

**ALWAYS use `backend.utils.date_formatter`:**

```python
from backend.utils.date_formatter import now_chile, today_chile, format_date_for_sheets, format_datetime_for_sheets

format_date_for_sheets(today_chile())       # "21-01-2026"
format_datetime_for_sheets(now_chile())     # "21-01-2026 14:30:00"
```

**NEVER use:** `datetime.utcnow()`, `datetime.now()`, `.isoformat()`.

## TypeScript Rules

**CRITICAL — NEVER use `any`.**

```typescript
// ❌ BAD — ESLint error
data: any

// ✅ GOOD
data: unknown                                                  // dynamic
data: { tag_spool: string; operacion: 'ARM' | 'SOLD' }         // known shape
```

**Before commit:** `npx tsc --noEmit && npm run lint && npm run build` must all pass.

## Must-Read Companion Docs

Certain topics are enforced rules, but kept in their own files to keep this one scannable. **Read the relevant one before working in that area:**

- **UI / accessibility work** → `docs/accessibility.md` (WCAG 2.1 AA patterns: ARIA, focus management, color contrast, keyboard nav, validation checklist).
- **MCP browser tooling** → `docs/mcp-browser.md` (when and how to use `mcp__MCP_DOCKER__browser_*` for production verification, Sheets inspection, and Swagger docs).
- **Historical context / architecture snapshots / resolved bug post-mortems** → `docs/archive/` (frozen; useful as forensic reference when a symptom reappears).
- **Uniones sheet specification** → `docs/engineering-handoff.md` (column semantics for the Engineering team).

## Environment Variables

**Backend (`.env`):**
```
GOOGLE_SHEET_ID=17iOaq2sv4mSOuJY4B8dGQIsWTTUKPspCtb7gk6u-MaQ
HOJA_METADATA_NOMBRE=Metadata
GOOGLE_SERVICE_ACCOUNT_EMAIL=zeus-mvp@zeus-mvp.iam.gserviceaccount.com
GOOGLE_PRIVATE_KEY="-----BEGIN PRIVATE KEY-----\n...\n-----END PRIVATE KEY-----\n"
```

**Frontend (`.env.local`):**
```
NEXT_PUBLIC_API_URL=http://localhost:8000                                  # dev
# NEXT_PUBLIC_API_URL=https://zeues-backend-mvp-production.up.railway.app  # prod
```

## Security

- Google Service Account credentials live ONLY in Railway env vars (`GOOGLE_APPLICATION_CREDENTIALS_JSON`). Never commit.
- Local credentials go in `.env.local` (gitignored).
- If credentials leak: rotate in [Google Cloud Console](https://console.cloud.google.com/iam-admin/serviceaccounts?project=zeus-mvp), update Railway, redeploy, delete the old key.

## Schema Validation

```bash
python backend/scripts/validate_schema_startup.py   # pre-deploy check
python backend/scripts/validate_uniones_sheet.py    # Uniones structure
python backend/scripts/validate_uniones_sheet.py --fix   # add missing headers (structure only)
```

Startup validation runs automatically in `main.py` after cache warming. Deployment fails fast on missing columns; extra columns are allowed.

## Production URLs

- Frontend: https://zeues-frontend.vercel.app
- Backend: https://zeues-backend-mvp-production.up.railway.app
- API Docs: https://zeues-backend-mvp-production.up.railway.app/api/docs

## Key Constraints

- Google Sheets is the source of truth — no database migration.
- Mobile-first UI: large touch targets (`h-16` / `h-20`), tablet-optimized.
- Google Sheets limits: 60 writes/min/user, 200–500 ms latency per call.
- Manufacturing scale target: 30–50 workers, 2,000+ spools, 10–15 req/sec.
- Regulatory: Metadata audit trail is mandatory (append-only, immutable).

---

**Last updated:** 2026-04-22 · **Document version:** 4.0
