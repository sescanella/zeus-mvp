# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**ZEUES** - Manufacturing Traceability System for Pipe Spools

Mobile-first web app for tracking manufacturing actions (Assembly/Welding) on tablets, using Google Sheets as source of truth.

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

**MVP Scope:** 2 actions only
- Action 3: Armado (Assembly)
- Action 4: Soldado (Welding)

**Data Model:**
- Spools (Column A: Code, F: Assembly, G: Welding)
- Actions are binary: 0 = pending, 1 = completed
- Workers select from list (no complex auth)

**User Flow:** Worker ID → Action → Spool → Confirm → Update Sheets (< 30 sec)

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

**Project Documentation:**
- `proyecto.md` - **COMPLETE PROJECT SPECIFICATION** - Contains full project details, user stories, technical architecture, and current implementation status. This is the single source of truth for project scope and progress.
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

**Sheets Structure:**
- **Operaciones** sheet: Spools data (columns A-BE)
  - Column A: TAG_SPOOL
  - Column V (22): ARM status (0/0.1/1.0)
  - Column W (23): SOLD status (0/0.1/1.0)
  - Column BA (53): fecha_materiales (prerequisite)
  - Column BB (54): fecha_armado
  - Column BC (55): armador (worker name)
  - Column BD (56): fecha_soldado
  - Column BE (57): soldador (worker name)
- **Trabajadores** sheet: Workers list (columns A-C)
  - Column A: nombre
  - Column B: apellido
  - Column C: activo (TRUE/FALSE)

**State Transitions:**
- PENDIENTE: 0 → ready to start
- EN_PROGRESO: 0.1 → worker assigned, in progress
- COMPLETADO: 1.0 → action finished

**Workflow:**
1. **INICIAR**: status → 0.1, worker name → BC/BE
2. **COMPLETAR**: status → 1.0, date → BB/BD

**Environment Variables (see docs/GOOGLE-RESOURCES.md):**
- `GOOGLE_SHEET_ID` - Testing: `11v8fD5Shn0RSzDceZRvXhE9z4RIOBmPA9lpH5_zF-wM`
- `GOOGLE_SERVICE_ACCOUNT_EMAIL` - zeus-mvp@zeus-mvp.iam.gserviceaccount.com
- `GOOGLE_PRIVATE_KEY` - From Service Account JSON (keep secret)

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
