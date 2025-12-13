# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**ZEUES v2.0** - Manufacturing Traceability System for Pipe Spools

Mobile-first web app for tracking manufacturing actions (Assembly/Welding/Metrology) on tablets with **JWT authentication**, **role-based access control**, **Event Sourcing auditing**, and **batch operations** using Google Sheets as source of truth.

**Current Status:** v2.0 Development (Branch: `v2.0-dev`)
- ✅ v1.0 MVP in Production (2 operations: ARM/SOLD)
- 🚧 v2.0 In Development: Auth + Metadata Event Sourcing + METROLOGÍA + Batch
- 📅 Target Launch: 27 Dic 2025
- 📊 Progress: DÍA 4 (6%) - Metadata Repository implemented

## CRITICAL: Python Virtual Environment

**ALWAYS WORK INSIDE THE VIRTUAL ENVIRONMENT**

```bash
# Activate BEFORE any work
source venv/bin/activate

# Install ANY new package inside venv
pip install <package-name>

# Always update requirements after installing
pip freeze > requirements.txt
```

**RULES:**
- NEVER install packages outside venv
- ALWAYS activate venv before running Python code
- ALWAYS activate venv before installing dependencies
- ALL Python work must be done with venv activated

**Production URLs:**
- Frontend: https://zeues-frontend.vercel.app
- Backend API: https://zeues-backend-mvp-production.up.railway.app
- API Docs: https://zeues-backend-mvp-production.up.railway.app/docs

## Tech Stack

**Backend:** Python + FastAPI + gspread (Google Sheets API)
**Frontend:** React/Next.js + Tailwind CSS
**Data Source:** Google Sheets (single source of truth)
**Auth:** Service Account (zeus-mvp@zeus-mvp.iam.gserviceaccount.com)

## Core Concepts

**v1.0 MVP Scope (Production):** 2 operations
- ARM: Armado (Assembly)
- SOLD: Soldado (Welding)

**v2.0 Scope (Development):** 3 operations + Auth + Auditing + Batch
- ARM: Armado (Assembly)
- SOLD: Soldado (Welding)
- METROLOGIA: Metrología (Quality Inspection) 🆕
- **Event Sourcing:** All actions logged to Metadata sheet (append-only, immutable) 🆕
- **JWT Auth:** Email-based login with roles (Trabajador/Supervisor/Administrador) 🆕
- **Batch Operations:** Multiselect up to 50 spools simultaneously 🆕

**Data Model v2.0:**
- **Spools** - Operaciones sheet (READ-ONLY): TAG_SPOOL, ARM status, SOLD status, METROLOGÍA status
- **Workers** - Trabajadores sheet (READ-ONLY): Id, Nombre, Apellido, Rol, Activo
- **Metadata** - Event Sourcing log (WRITE-ONLY): 10 columns (id, timestamp, evento_tipo, tag_spool, worker_id, worker_nombre, operacion, accion, fecha_operacion, metadata_json)
- **Roles** - Authentication (pending): email, nombre_completo, rol, activo
- Actions: 0 = pending, 0.1 = in progress, 1 = completed

**User Flow v2.0:**
Login (email) → Worker Select → Operation → INICIAR/COMPLETAR → Spool(s) Multiselect → Confirm Batch → Success + Metadata Log (< 30 sec)

## Development Commands

### Backend (FastAPI + Python)

**Always activate venv first:**
```bash
cd backend
source venv/bin/activate  # macOS/Linux
# venv\Scripts\activate   # Windows
```

**Run development server:**
```bash
# From project root (with venv activated)
uvicorn main:app --reload --port 8000
# API available at: http://localhost:8000
# Docs at: http://localhost:8000/api/docs
```

**Testing:**
```bash
# Run all tests (from project root with venv active)
PYTHONPATH=/Users/sescanella/Proyectos/ZEUES-by-KM pytest

# Run with coverage
PYTHONPATH=/Users/sescanella/Proyectos/ZEUES-by-KM pytest --cov=backend

# Run specific test file
PYTHONPATH=/Users/sescanella/Proyectos/ZEUES-by-KM pytest tests/test_validation_service.py

# Run single test
PYTHONPATH=/Users/sescanella/Proyectos/ZEUES-by-KM pytest tests/test_validation_service.py::test_validar_puede_iniciar_arm_success
```

**Package management:**
```bash
# Install new package (venv must be active)
pip install <package-name>

# ALWAYS update requirements after installing
pip freeze > requirements.txt
```

### Frontend (Next.js + TypeScript)

**Run development server:**
```bash
cd zeues-frontend
npm run dev
# App available at: http://localhost:3000
```

**Build and type checking:**
```bash
cd zeues-frontend

# TypeScript compilation check (MUST pass)
npx tsc --noEmit

# ESLint (MUST pass - no warnings, no errors)
npm run lint

# Production build (MUST pass)
npm run build

# Run production build locally
npm run start
```

**Testing (Playwright E2E):**
```bash
cd zeues-frontend

# Run all E2E tests (headless)
npx playwright test

# Run with UI mode (interactive)
npx playwright test --ui

# Run in headed mode (see browser)
npx playwright test --headed

# Slow motion demo mode
SLOW_MO=2000 npx playwright test --headed --workers=1 --max-failures=1

# Show test report
npx playwright show-report
```

## Architecture Overview

### Backend Structure (Clean Architecture)

**Layered Architecture:**
```
main.py                      # FastAPI app, CORS, exception handlers
├── routers/                 # API endpoints (thin layer)
│   ├── health.py           # GET /api/health
│   ├── workers.py          # GET /api/workers
│   ├── spools.py           # POST /api/spools/iniciar, /completar
│   └── actions.py          # POST /api/iniciar-accion, /completar-accion (CRITICAL)
├── services/                # Business logic (orchestration)
│   ├── action_service.py   # Orchestrates validation + repository
│   └── validation_service.py # Pure business rules (CRITICAL ownership)
├── repositories/            # Data access layer
│   └── sheets_repository.py # Google Sheets CRUD (gspread)
├── models/                  # Pydantic schemas
│   ├── worker.py
│   ├── spool.py
│   ├── action.py
│   └── enums.py            # ActionType, ActionStatus
├── exceptions.py            # 10+ custom exceptions (ZEUSException)
└── config.py               # Environment variables
```

**Key Patterns:**
- **Service Layer Pattern**: ActionService orchestrates ValidationService + SheetsRepository
- **Repository Pattern**: SheetsRepository abstracts Google Sheets API (gspread)
- **Custom Exceptions**: All business errors use ZEUSException subclasses → HTTP status in main.py
- **Dependency Injection**: FastAPI Depends() for service instantiation

**CRITICAL: Ownership Restriction**
```python
# backend/services/validation_service.py
def validar_puede_completar_arm(self, spool: Spool, worker_nombre: str) -> None:
    """
    CRITICAL: Only worker who started can complete (spool.armador == worker_nombre).
    Violation → NoAutorizadoError → 403 FORBIDDEN
    """
```

### Frontend Structure (Next.js App Router)

**7-Page Linear Flow:**
```
app/
├── page.tsx                        # P1: Worker identification
├── operacion/page.tsx             # P2: Operation selection (ARM/SOLD)
├── tipo-interaccion/page.tsx      # P3: Action type (INICIAR/COMPLETAR)
├── seleccionar-spool/page.tsx     # P4: Spool selection (filtered by API)
├── confirmar/page.tsx             # P5: Confirmation summary
└── exito/page.tsx                 # P6: Success (5sec timeout → P1)

components/
├── Button.tsx                      # Reusable button (Tailwind inline)
├── Card.tsx                        # Worker/spool cards
└── ...

lib/
├── api.ts                          # 6 API functions (native fetch, NO axios)
├── types.ts                        # TypeScript interfaces
└── context.tsx                     # React Context (shared state)
```

**State Management:**
- **React Context API** (lib/context.tsx) for cross-page state
- NO Redux/Zustand (keeping MVP simple)
- State: worker, operacion, tipoInteraccion, selectedSpool

**Navigation:**
- Standard Next.js routing (`useRouter()`)
- "Volver" button on each page (go back one step)
- "Cancelar" button (red) resets to P1
- Auto-redirect to P1 after 5 seconds on success page

**API Integration:**
- Native `fetch()` only (NO axios)
- Simple try/catch error handling
- API functions in `lib/api.ts`:
  - `getWorkers()`
  - `getSpoolsIniciar(operacion)`
  - `getSpoolsCompletar(operacion, workerNombre)`
  - `iniciarAccion(payload)`
  - `completarAccion(payload)`

## Important Files

**Project Documentation v2.0:** 🆕
- `proyecto-v2.md` - **v2.0 ROADMAP** - Vision, 5 new features, 16-day timeline, breaking changes, metrics
- `proyecto-v2-backend.md` - **v2.0 BACKEND DOCS (LLM-FIRST)** - Auth JWT, Event Sourcing, Metadata, Batch operations, 95 new tests
- `proyecto-v2-frontend.md` - **v2.0 FRONTEND DOCS (LLM-FIRST)** - Login, AuthContext, Multiselect, Admin Panel, 8 new E2E tests

**CRITICAL: Actualización de Documentos v2.0**

**Archivos Activos (actualizar SIEMPRE en esta etapa):**
- `proyecto-v2.md` - **SIEMPRE** después de avanzar en roadmap (completar días, features, cambios estado)
- `proyecto-v2-backend.md` - **SIEMPRE** después de modificar backend (código, tests, arquitectura, endpoints)
- `proyecto-v2-frontend.md` - **SIEMPRE** después de modificar frontend (componentes, páginas, API client, types)

**Archivos Historial (NO actualizar - solo referencia v1.0):**
- `proyecto.md`, `proyecto-backend.md`, `proyecto-frontend.md`, `proyecto-frontend-ui.md` - Base v1.0 completada

**Cuándo actualizar cada archivo:**
- `proyecto-v2.md` → Después de completar días del roadmap, cambiar estado progreso, añadir features, identificar blockers
- `proyecto-v2-backend.md` → Después de implementar servicios, endpoints, modelos, tests, cambios arquitectura
- `proyecto-v2-frontend.md` → Después de implementar componentes, páginas, hooks, API integration, tests E2E

**Cómo actualizar:**
1. **Comando directo:**
   - `"actualiza proyecto-v2.md"` → Actualiza roadmap y estado general
   - `"actualiza proyecto-v2-backend.md"` → Actualiza docs técnicas backend
   - `"actualiza proyecto-v2-frontend.md"` → Actualiza docs técnicas frontend
2. **Seguir guía interna:** Cada archivo técnico (backend/frontend) tiene sección "🔧 Guía de Mantenimiento LLM-First"
3. **Formato obligatorio:**
   - Actualizar Quick Reference/Estado PRIMERO (progreso, tests, archivos, deadline)
   - Usar tablas > código (NO bloques > 20 líneas en archivos técnicos)
   - Mantener límites: proyecto-v2.md (~780 líneas) / backend (~1,000) / frontend (~800)

**Ejemplo workflow completo:**
```bash
# Después de completar DÍA 2 Backend Batch
"actualiza proyecto-v2-backend.md"  # Añade métricas batch, tests, performance
"actualiza proyecto-v2.md"           # Marca DÍA 2 Backend ✅, actualiza progreso 80%→90%
```

**Project Documentation v1.0 (Base):**
- `proyecto.md` - **v1.0 MVP SPECIFICATION** - Complete v1.0 project details, user stories, technical architecture
- `proyecto-backend.md` - v1.0 backend technical docs (architecture, models, services, API)
- `proyecto-frontend.md` - v1.0 frontend architecture (structure, pages, components)
- `proyecto-frontend-ui.md` - v1.0 UI implementation details (components, styles, validations)
- `CLAUDE.md` - This file - Quick reference guide for Claude Code

**Google Resources:**
- `docs/GOOGLE-RESOURCES.md` - **GOOGLE CONFIGURATION** - URLs for Drive and Sheets (Testing & Production), Service Account details, environment variables, and security guidelines

**Credentials (NEVER commit to Git):**
- `credenciales/` - Contains Google Cloud Service Account JSON files
  - `zeus-mvp-81282fb07109.json` - Service Account credentials for API access
  - Files in this directory are in `.gitignore` for security

**Data & Environment:**
- `plantilla.xlsx` - Data structure template (reference copy)
- `venv/` - Python virtual environment
- `.env.local` - Environment variables (NEVER commit)
- `backend/requirements.txt` - Python dependencies

**Key Dependencies:**
- Backend: `fastapi`, `gspread`, `pydantic`, `pytest`, `uvicorn`
- Frontend: `next@14`, `react@18`, `typescript`, `tailwindcss`, `@playwright/test`

## Google Sheets Integration

**Data Source:** Google Sheets is the single source of truth (no database)

**v2.0 Architecture - Event Sourcing:** ✅
- **Operaciones** sheet: **READ-ONLY** - Base data, never modified
- **Metadata** sheet: **WRITE-ONLY** - All events logged here (append-only, immutable)
- State is reconstructed from events, NOT read from Operaciones columns

**Sheets Structure v2.0:**
- **Operaciones** sheet (READ-ONLY): Spools base data (65 columns)
  - Column G: TAG_SPOOL (código de barra)
  - Column AK (37): Fecha_Armado (read-only reference)
  - Column AL (38): Armador (read-only reference)
  - Column AM (39): Fecha_Soldadura (read-only reference)
  - Column AN (40): Soldador (read-only reference)
  - Column AO (41): Fecha_Metrología (read-only reference) 🆕

- **Trabajadores** sheet (READ-ONLY): Workers list (columns A-E) 🆕
  - Column A: Id (numeric, e.g., 93, 94, 95)
  - Column B: Nombre
  - Column C: Apellido
  - Column D: Rol (Armador, Soldador, Ayudante, Metrologia, Revestimiento, Pintura, Despacho)
  - Column E: Activo (TRUE/FALSE)

- **Metadata** sheet (WRITE-ONLY - Event Sourcing): 10 columns 🆕
  - Column A: id (UUID v4)
  - Column B: timestamp (ISO 8601: 2025-12-10T14:30:00Z)
  - Column C: evento_tipo (INICIAR_ARM, COMPLETAR_ARM, INICIAR_SOLD, COMPLETAR_SOLD, INICIAR_METROLOGIA, COMPLETAR_METROLOGIA)
  - Column D: tag_spool
  - Column E: worker_id (numeric: 93, 94, 95...)
  - Column F: worker_nombre
  - Column G: operacion (ARM, SOLD, METROLOGIA)
  - Column H: accion (INICIAR, COMPLETAR)
  - Column I: fecha_operacion (YYYY-MM-DD)
  - Column J: metadata_json (JSON string with additional data)

- **Roles** sheet (pending): Authentication 🆕
  - Column A: email
  - Column B: nombre_completo
  - Column C: rol (TRABAJADOR, SUPERVISOR, ADMINISTRADOR)
  - Column D: activo
  - Column E: fecha_creacion
  - Column F: ultima_modificacion

**State Transitions:**
- PENDIENTE: 0 → ready to start
- EN_PROGRESO: 0.1 → worker assigned, in progress
- COMPLETADO: 1.0 → action finished

**Workflow v2.0 (Event Sourcing):**
1. **INICIAR**: Write event to Metadata (INICIAR_ARM/INICIAR_SOLD/INICIAR_METROLOGIA)
2. **COMPLETAR**: Write event to Metadata (COMPLETAR_ARM/COMPLETAR_SOLD/COMPLETAR_METROLOGIA)
3. **State Query**: Read latest events from Metadata to reconstruct current state

**Environment Variables (see docs/GOOGLE-RESOURCES.md):**
- `GOOGLE_SHEET_ID` - **PRODUCTION (ACTIVE):** `17iOaq2sv4mSOuJY4B8dGQIsWTTUKPspCtb7gk6u-MaQ` ✅
- `HOJA_METADATA_NOMBRE` - `Metadata` (Event Sourcing log) 🆕
- `GOOGLE_SERVICE_ACCOUNT_EMAIL` - zeus-mvp@zeus-mvp.iam.gserviceaccount.com
- `GOOGLE_PRIVATE_KEY` - From Service Account JSON (keep secret)

**Sheet TESTING (deprecated):**
- ID: `11v8fD5Shn0RSzDceZRvXhE9z4RIOBmPA9lpH5_zF-wM` ⚠️ (v1.0 only - historical reference)

## Key Constraints

1. Google Sheets is source of truth (preserve existing workflow)
2. Mobile-first design (large buttons, high contrast)
3. Speed critical (< 30 seconds per registration)
4. Simple UI (minimal typing, immediate feedback)

## TypeScript & Code Quality Rules

**CRITICAL: NEVER use `any` type**

**TypeScript Best Practices:**
- ❌ NEVER use `any` - ESLint will fail with `@typescript-eslint/no-explicit-any`
- ✅ ALWAYS use `unknown` for dynamic/uncertain types
- ✅ ALWAYS use explicit types for function parameters and return values
- ✅ Use `Record<string, unknown>` instead of `Record<string, any>`
- ✅ Prefer union types (`'ARM' | 'SOLD'`) over string when values are known
- ✅ Use optional chaining (`?.`) and nullish coalescing (`??`) for safety

**Examples:**
```typescript
// ❌ BAD - ESLint error
interface Response {
  metadata: Record<string, any>;  // ERROR
  data: any;  // ERROR
}

// ✅ GOOD - ESLint passes
interface Response {
  metadata: Record<string, unknown>;  // OK
  data: unknown;  // OK - if truly dynamic
  // OR better - be specific:
  data: {
    tag_spool: string;
    operacion: 'ARM' | 'SOLD';
  };
}

// ❌ BAD - implicit any
function fetchData(url) {  // ERROR - implicit any on 'url'
  return fetch(url);
}

// ✅ GOOD - explicit types
function fetchData(url: string): Promise<Response> {
  return fetch(url);
}
```

**Validation Commands (Must pass before any commit):**
```bash
# TypeScript compilation - MUST pass
npx tsc --noEmit

# ESLint - MUST pass (no warnings, no errors)
npm run lint

# Build production - MUST pass
npm run build
```

**When to use `unknown` vs specific types:**
- Use `unknown` for truly dynamic data from external sources (APIs, JSON parsing)
- Cast `unknown` to specific types after validation/type guards
- Prefer specific interfaces over `unknown` whenever structure is known

**Type Guards Example:**
```typescript
// Dynamic data from API
const data: unknown = await response.json();

// Type guard before using
if (isValidWorker(data)) {
  // Now TypeScript knows data is Worker type
  console.log(data.nombre);
}

function isValidWorker(obj: unknown): obj is Worker {
  return (
    typeof obj === 'object' &&
    obj !== null &&
    'nombre' in obj &&
    'activo' in obj
  );
}
```

## Specialized Agents

### Project-Specific Agents (ZEUES Backend)

**backend-architect** - Use for architectural design and planning
- When: Before implementing new features, restructuring code, defining data models
- Purpose: Design backend architecture, service interfaces, error handling patterns
- Example: "Design the architecture for worker authentication" or "Plan the caching strategy for Sheets data"

**google-sheets-specialist** - Use for Google Sheets API integration
- When: Implementing/modifying SheetsService, handling API errors, optimizing performance
- Purpose: CRUD operations, authentication, rate limiting, retry logic, batch operations
- Example: "Implement batch read for spools" or "Fix 429 rate limit errors"

**service-developer** - Use for business logic implementation
- When: Implementing ValidationService, ActionService, or orchestration workflows
- Purpose: Business rules, validation logic, service layer coordination
- Example: "Implement validation for assembly prerequisites" or "Create action workflow orchestration"

**api-builder** - Use for FastAPI endpoints
- When: Creating/modifying REST endpoints, adding validations, API documentation
- Purpose: Routers, Pydantic schemas, request/response models, endpoint documentation
- Example: "Create POST /api/iniciar-accion endpoint" or "Add validation for operation types"

### Project-Specific Agents (ZEUES Frontend MVP)

**frontend-architect** - Use for frontend structure and architecture (MVP simple)
- When: Before starting frontend development, defining folder structure, planning pages/components
- Purpose: Design simple folder structure, define 7 pages, list 3-5 components max, establish naming conventions
- Example: "Design frontend structure for 7 screens" or "Define component architecture for MVP"
- Time: 1-2 hours (DAY 1)
- Philosophy: NO over-architecture, keep it SIMPLE

**ui-builder-mvp** - Use for implementing UI components and pages (3-in-1: UI + UX + Validation)
- When: Creating React components, implementing pages, applying styles, adding basic validations
- Purpose: Build Button/Card/List components, implement 7 pages with Tailwind inline, mobile-first design (h-16 buttons), basic inline validations
- Example: "Implement P1 Identification page with worker grid" or "Create Button component with Tailwind"
- Time: 4-5 days (DAY 2-6)
- Philosophy: Simple functional components, NO complex animations, inline styles, basic validations
- **TypeScript:** Explicit prop types, NEVER use `any`, type all component props and state

**api-integrator** (frontend) - Use for connecting frontend with backend API
- When: Integrating with backend endpoints, handling API calls, error handling
- Purpose: Create /lib/api.ts with 6 fetch functions, use native fetch (NO axios), basic error handling
- Example: "Integrate GET /api/workers endpoint" or "Create iniciarAccion API function"
- Time: 2-3 hours (DAY 4)
- Philosophy: Native fetch only, simple try/catch, NO complex libraries
- **TypeScript:** NEVER use `any` - use `unknown` for dynamic data, explicit types for all functions

**navigation-orchestrator** - Use for connecting navigation flow between pages
- When: Setting up routing, implementing navigation between 7 screens, state management
- Purpose: Implement Next.js routing, Context API for shared state, Volver/Cancelar buttons, 5sec timeout to home
- Example: "Connect navigation flow INICIAR" or "Implement Context API for state sharing"
- Time: 2-3 hours (DAY 6)
- Philosophy: Simple routing, basic Context (NO Redux/Zustand), functional navigation

**Frontend MVP Workflow (6 days):**
- DAY 1: frontend-architect → structure
- DAY 2-3: ui-builder-mvp → components + P1, P2, P3
- DAY 4: api-integrator + ui-builder-mvp → API + P4A, P5A
- DAY 5: ui-builder-mvp → P4B, P5B, P6
- DAY 6: navigation-orchestrator → complete flow + deploy

### Project Management Agents

**project-architect** - Use for project documentation and planning
- When: Updating proyecto.md, refining strategy, documenting implementations, reviewing project state
- Purpose: Transform ideas into structured projects, maintain up-to-date documentation
- Example: "@actualizar-docs" after implementation or "Review MVP gaps"

**Explore** - Use for codebase exploration
- When: Finding files by patterns, searching for keywords, understanding architecture
- Purpose: Fast exploration with thoroughness levels (quick/medium/very thorough)
- Example: "Find all API endpoints" or "How does error handling work?"

**Plan** - Use for planning and strategy
- When: Similar to Explore but for planning implementation steps
- Purpose: Fast planning with thoroughness configuration
- Example: Planning feature implementation approach

### Personal/General Agents

**linkedin-post-pillars** - Generate LinkedIn content ideation framework
- When: Creating LinkedIn content strategy, brainstorming post ideas
- Purpose: 50 unique post pillars combining objectives and core messages
- Example: "Generate LinkedIn content ideas for tech leadership"

**linkedin-seo-keyword-generator** - LinkedIn SEO optimization
- When: Optimizing LinkedIn profile, finding hashtags, developing content strategy
- Purpose: Bilingual (EN/ES) keyword research, hashtags, profile optimization
- Example: "Optimize my LinkedIn profile for software architect"

**google-seo-keyword-generator** - Google SEO strategy
- When: Website optimization, keyword research, content marketing for search engines
- Purpose: Bilingual SEO strategy, technical optimization, keyword research
- Example: "SEO strategy for tech blog"

**audience-strategist** - Define and analyze target audiences
- When: Starting new projects, after user research, planning content strategy
- Purpose: Audience segmentation, persona creation, market analysis
- Example: "Define target audience for SaaS product"

**research-reporter** - Internet research with detailed reports
- When: Need comprehensive research on any topic with documentation
- Purpose: Market research, technology investigation, competitive analysis
- Example: "Research best practices for FastAPI authentication"

### Usage Guidelines

- **Proactive use:** Use agents without explicit user request when task matches agent purpose
- **Parallel execution:** Launch multiple agents simultaneously when possible for efficiency
- **Stateless:** Each agent invocation is independent, provide complete context in prompt
- **Results:** Agent returns one final message with results, no back-and-forth

## Custom Commands

### /actualizar-docs
Updates project documentation after implementation work.

**Updates:**
- `proyecto.md` - General MVP documentation (max 850 lines)
- `proyecto-backend.md` - Backend technical docs (max 1000 lines)

**Usage:** Run after completing features, fixing bugs, or making architectural changes.

**What it captures:**
- Project state changes
- Technical decisions
- Blockers identified/resolved
- Implementation progress
- Roadmap updates

**Example:**
```bash
# After implementing a new feature
/actualizar-docs
```

The command uses the `project-architect` agent to extract relevant information from the conversation and update both documentation files while preserving critical information and compacting less important details if needed.
