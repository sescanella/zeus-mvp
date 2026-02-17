# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**ZEUES v4.0-single-user** - Simplified Location Tracking System for Pipe Spools

**Current Status:** Single-User Mode (2026-02-04)
- **Core Value:** "WHO has WHICH spool right now?" (occupation tracking)
- **Architecture:** Simplified for 1 tablet, 1 worker - No distributed locks or real-time sync needed
- **Tech:** FastAPI + Next.js + Google Sheets (source of truth)
- **Deployment:** Railway (backend) + Vercel (frontend)

**Key Features:**
- TOMAR/PAUSAR/COMPLETAR workflows (direct Sheets updates, no distributed locks)
- Union-level tracking (Uniones sheet)
- INICIAR/FINALIZAR workflows (auto-determination of PAUSAR vs COMPLETAR)
- Metrología instant inspection (APROBADO/RECHAZADO)
- Reparación bounded cycles (max 3 before BLOQUEADO)
- Hierarchical state machines
- Pulgadas-diámetro business metric (DN_UNION sums)

**Architectural Simplifications (Single-User Mode):**
- ✅ Single-user mode (no distributed locks with 1 tablet)
- ✅ Real-time sync removed (no concurrent operations)
- ✅ Direct Google Sheets validation (Ocupado_Por column check)
- ✅ P5 Confirmation Workflow (all writes at confirmation)

**P5 Confirmation Workflow (v4.0 Phase 8 - Feb 2026):**

INICIAR/FINALIZAR now write ONLY when user confirms in P5 (confirmation screen):

**INICIAR (`POST /api/v4/occupation/iniciar`):**
- Writes: `Ocupado_Por`, `Fecha_Ocupacion`, `Estado_Detalle` (EstadoDetalleBuilder)
- Trust P4 filters (no backend validation before write)
- Last-Write-Wins (LWW) for race conditions
- Automatic retry (3 attempts) on transient errors
- Logs `INICIAR_SPOOL` event with minimal metadata
- Works for v2.1 and v4.0 spools

**FINALIZAR (`POST /api/v4/occupation/finalizar`):**
- Writes unions with `batch_update_arm_full()` / `batch_update_sold_full()`
- Timestamps: INICIO from `Fecha_Ocupacion` (when taken), FIN from now()
- Auto-determines: CANCELADO (0 unions) | PAUSAR (partial) | COMPLETAR (all)
- COMPLETAR updates: `Fecha_Armado`/`Soldadura`, v4.0 counters, pulgadas
- PAUSAR clears: `Ocupado_Por`, `Fecha_Ocupacion` (no dates/counters)
- Metadata ALWAYS includes pulgadas (sum of DN_UNION)
- No version column updates (no optimistic locking)

**Key Changes:**
- Service: `backend/services/occupation_service.py` (iniciar_spool, finalizar_spool refactored)
- Repository: `backend/repositories/union_repository.py` (new batch_update_full methods)
- Routers: Updated docs in `occupation_v4.py` and `union_router.py`
- Tests: `tests/unit/services/test_occupation_service_p5_workflow.py` (17 tests, 100% passing)
- Architecture: `.planning/P5-CONFIRMATION-ARCHITECTURE.md`

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

- **Backend:** Python 3.11 + FastAPI + gspread + python-statemachine==2.5.0
- **Frontend:** Next.js 14 + TypeScript + Tailwind CSS
- **Data:** Google Sheets (single source of truth)
- **Deploy:** Railway (backend) + Vercel (frontend)

**Note:** Single-user mode - No distributed locks, no real-time sync.

## Essential Commands

### Backend (FastAPI + Python)

```bash
# Run dev server (from project root with venv active)
source venv/bin/activate
uvicorn main:app --reload --port 8000
# API: http://localhost:8000
# Docs: http://localhost:8000/api/docs

# Testing
PYTHONPATH="$(pwd)" pytest
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

### Railway CLI (Deployment)

```bash
# Already linked to zeues-backend-mvp production
railway logs              # View production logs
railway variables         # List env vars
railway up                # Deploy from local
railway redeploy          # Force redeploy
railway status            # Check deployment status
```

## Browser Testing with MCP (Model Context Protocol)

**Claude Code has MCP browser tools for visual testing and production debugging.**

### Available Capabilities

**Browser Control:**
```bash
mcp__MCP_DOCKER__browser_navigate        # Navigate to URL
mcp__MCP_DOCKER__browser_snapshot        # Capture accessibility tree (better than screenshot)
mcp__MCP_DOCKER__browser_take_screenshot # Take visual screenshot
mcp__MCP_DOCKER__browser_click           # Click elements
mcp__MCP_DOCKER__browser_type            # Type into inputs
mcp__MCP_DOCKER__browser_wait_for        # Wait for conditions
mcp__MCP_DOCKER__browser_console_messages # Read console errors/warnings
```

### When to Use Browser Testing

**✅ USE browser tools for:**
- **Visual verification** of production deployments (Vercel/Railway)
- **UX/UI inspection** without running local servers
- **Google Sheets observation** (read-only - verify data structure)
- **API documentation** browsing (Swagger UI at `/api/docs`)
- **Console error detection** in production
- **Cross-environment debugging** (staging vs production)
- **Screenshot generation** for documentation

**❌ DON'T USE browser tools for:**
- **Local development testing** (use Playwright tests instead)
- **Editing Google Sheets** (use gspread API via backend)
- **API endpoint testing** (use `curl` or Bash tool instead)
- **Performance testing** (use dedicated load testing tools)

### Production URLs

**Frontend (Vercel):**
```bash
mcp__MCP_DOCKER__browser_navigate https://zeues-frontend.vercel.app
# Verify: Worker selection flow, operation buttons, spool listings
```

**Backend API (Railway):**
```bash
mcp__MCP_DOCKER__browser_navigate https://zeues-backend-mvp-production.up.railway.app/api/docs
# Verify: Swagger UI loads, all endpoints documented, schemas visible
```

**Google Sheets (Read-Only):**
```bash
mcp__MCP_DOCKER__browser_navigate https://docs.google.com/spreadsheets/d/17iOaq2sv4mSOuJY4B8dGQIsWTTUKPspCtb7gk6u-MaQ/edit
# Verify: Sheet structure (Operaciones, Metadata, Uniones tabs), column headers
# IMPORTANT: Can VIEW only - NEVER attempt to edit via browser
```

### Usage Examples

**Example 1: Verify production deployment**
```bash
# After deploying to Vercel, check if app loads correctly
mcp__MCP_DOCKER__browser_navigate https://zeues-frontend.vercel.app
mcp__MCP_DOCKER__browser_wait_for --time 3
mcp__MCP_DOCKER__browser_snapshot
# Expected: See "SELECCIONA OPERACIÓN" with 4 operation buttons
```

**Example 2: Check API documentation**
```bash
# Verify Railway backend is running and docs are accessible
mcp__MCP_DOCKER__browser_navigate https://zeues-backend-mvp-production.up.railway.app/api/docs
mcp__MCP_DOCKER__browser_wait_for --time 3
mcp__MCP_DOCKER__browser_snapshot
# Expected: Swagger UI with Health, Workers, Spools, Actions sections
```

**Example 3: Inspect Google Sheets structure**
```bash
# Verify Uniones sheet has correct 17-column structure
mcp__MCP_DOCKER__browser_navigate https://docs.google.com/spreadsheets/d/17iOaq2sv4mSOuJY4B8dGQIsWTTUKPspCtb7gk6u-MaQ/edit
mcp__MCP_DOCKER__browser_click [Uniones tab]
mcp__MCP_DOCKER__browser_snapshot
# Expected: See ID, OT, N_UNION, TAG_SPOOL, DN_UNION, etc.
# READ-ONLY: Cannot edit cells, only verify structure
```

**Example 4: Debug console errors**
```bash
# Check for JavaScript errors in production
mcp__MCP_DOCKER__browser_navigate https://zeues-frontend.vercel.app
mcp__MCP_DOCKER__browser_console_messages --level error
# Expected: No critical errors (favicon 404 is acceptable)
```

### Important Notes

- **Google Sheets Access:** Claude Code can VIEW sheets but CANNOT EDIT them
  - Use browser tools to verify schema, inspect data structure
  - Use `backend/repositories/sheets_repository.py` + gspread for writes
- **Browser Configuration:** Playwright configured with Brave browser support
  - See `zeues-frontend/playwright.config.ts` for settings
  - Environment variable: `PLAYWRIGHT_BASE_URL` for production testing
- **Accessibility First:** Prefer `browser_snapshot` over `browser_take_screenshot`
  - Snapshots return structured data (YAML) for better analysis
  - Screenshots are visual only, harder to parse programmatically

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
├── routers/           # API endpoints (occupation, history, metrologia)
├── services/          # Business logic (state, occupation, validation)
├── repositories/      # Data access (sheets, metadata)
├── state_machines/    # ARM, SOLD, Metrologia, Reparacion
├── models/            # Pydantic schemas
└── exceptions.py      # Custom exceptions
```

**Key Patterns:**
- Service Layer + Repository Pattern
- Hierarchical State Machines (python-statemachine 2.5.0)
- Version-aware updates (ConflictService with retry)
- Direct Sheets validation (Ocupado_Por column check)
- Event Sourcing (Metadata sheet)

### Frontend (Next.js App Router)

```
app/                   # 7-page linear flow
├── page.tsx          # P1: Operation selection (ARM/SOLD/MET/REP)
├── operacion/        # P2: Worker identification (filtered by role)
├── tipo-interaccion/ # P3: Action type (INICIAR/FINALIZAR)
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

**Uniones Sheet (17 columns - v4.0 simplified):**
- Core fields: ID, OT, N_UNION, TAG_SPOOL, DN_UNION, TIPO_UNION
- ARM fields: ARM_FECHA_INICIO, ARM_FECHA_FIN, ARM_WORKER
- SOLD fields: SOL_FECHA_INICIO, SOL_FECHA_FIN, SOL_WORKER
- NDT fields: NDT_UNION, R_NDT_UNION, NDT_FECHA, NDT_STATUS
- System fields: version (UUID4 for optimistic locking)
- **Note:** Audit fields (Creado_Por, Fecha_Creacion, Modificado_Por, Fecha_Modificacion) removed for simplicity

**Other Sheets:**
- Trabajadores (4 cols): Id, Nombre, Apellido, Activo
- Roles (3 cols): Id, Rol, Activo (multi-role support)
- Metadata (11 cols - v4.0): Event Sourcing audit trail + N_UNION column

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

## Accessibility Standards (WCAG 2.1 Level AA)

**ZEUES is committed to WCAG 2.1 Level AA compliance for manufacturing floor accessibility.**

### Testing Requirements

**Automated Testing:**
```bash
# Run accessibility tests
npm run test:a11y

# Playwright with axe-core
npx playwright test --grep @a11y
npx playwright test tests/accessibility.spec.ts
```

**Manual Testing:**
- Keyboard navigation: All features accessible via Tab/Enter/Space
- Screen reader: VoiceOver (macOS) or NVDA (Windows) testing
- Focus indicators: Visible 2px white/blue ring on all interactive elements

### ARIA Patterns

**Interactive Buttons:**
```typescript
<button
  aria-label="Descriptive action"
  aria-disabled={isDisabled}
  onClick={handleClick}
>
  Button Text
</button>
```

**Collapsible Panels:**
```typescript
<button
  aria-expanded={isExpanded}
  aria-controls="panel-id"
  aria-label={isExpanded ? 'Ocultar panel' : 'Mostrar panel'}
  onClick={toggle}
  onKeyDown={(e) => {
    if (e.key === 'Enter' || e.key === ' ') {
      e.preventDefault();
      toggle();
    }
  }}
>
  Toggle
</button>
<div id="panel-id" role="region" aria-label="Panel description">
  {/* Content */}
</div>
```

**Table Rows (Selectable):**
```typescript
<tr
  role="button"
  tabIndex={isDisabled ? -1 : 0}
  aria-label={`${isSelected ? 'Deseleccionar' : 'Seleccionar'} spool ${tag}${isDisabled ? ' (deshabilitado)' : ''}`}
  aria-disabled={isDisabled}
  onClick={() => !isDisabled && handleSelect()}
  onKeyDown={(e) => {
    if (isDisabled) return;
    if (e.key === 'Enter' || e.key === ' ') {
      e.preventDefault();
      handleSelect();
    }
  }}
>
```

### Focus Management

**Focus Indicators:**
- Use `focus:outline-none focus:ring-2 focus:ring-zeues-blue focus:ring-inset` (Blueprint UI)
- Use `focus:outline-none focus:ring-2 focus:ring-white focus:ring-inset` (dark backgrounds)
- Minimum 2px contrast ratio
- Visible on all interactive elements (buttons, inputs, clickable rows)

**Focus Trapping:**
- Error modals trap focus (Tab cycles within modal)
- Escape key closes modals and returns focus

### Color Contrast

**WCAG AA Requirements:**
- Normal text: 4.5:1 contrast ratio
- Large text (18pt+): 3:1 contrast ratio
- UI components: 3:1 contrast ratio

**Blueprint Industrial Palette:**
- Primary text: `#FFFFFF` on `#001F3F` (18.5:1 ✅)
- Error text: `#EF4444` on `#001F3F` (4.8:1 ✅)
- Disabled text: `#9CA3AF` on `#001F3F` (3.2:1 ⚠️ - use for large text only)
- Orange accent: `#FF6B35` on `#001F3F` (5.2:1 ✅)

### Keyboard Navigation Requirements

**All interactive elements MUST support:**
- `Tab` key for focus navigation
- `Enter` key for activation (buttons, links, clickable rows)
- `Space` key for activation (buttons, toggles)
- Visible focus indicators (2px ring)
- Logical tab order (follows visual flow)

**Special Cases:**
- Collapsible panels: `Enter`/`Space` to expand/collapse
- Table rows: `Enter`/`Space` to select/deselect
- Filter inputs: Normal text input behavior
- Navigation buttons: `Enter` to navigate

### Validation Checklist

Before PR approval:
- [ ] `npm run test:a11y` passes (0 violations)
- [ ] `npx playwright test tests/accessibility.spec.ts` passes
- [ ] Keyboard navigation tested manually (Tab through all interactive elements)
- [ ] Screen reader announces all actions correctly (VoiceOver/NVDA)
- [ ] Focus indicators visible on all interactive elements
- [ ] No ARIA violations (use browser axe DevTools extension)
- [ ] Color contrast meets WCAG AA (4.5:1 for normal text, 3:1 for large/UI)

### Resources

- [WCAG 2.1 Guidelines](https://www.w3.org/WAI/WCAG21/quickref/)
- [ARIA Authoring Practices](https://www.w3.org/WAI/ARIA/apg/)
- [axe DevTools Extension](https://www.deque.com/axe/devtools/)
- [WebAIM Contrast Checker](https://webaim.org/resources/contrastchecker/)

## Environment Variables

**Backend (.env):**
```env
GOOGLE_SHEET_ID=17iOaq2sv4mSOuJY4B8dGQIsWTTUKPspCtb7gk6u-MaQ
HOJA_METADATA_NOMBRE=Metadata
GOOGLE_SERVICE_ACCOUNT_EMAIL=zeus-mvp@zeus-mvp.iam.gserviceaccount.com
GOOGLE_PRIVATE_KEY="-----BEGIN PRIVATE KEY-----\n...\n-----END PRIVATE KEY-----\n"
```

**Frontend (.env.local):**
```env
NEXT_PUBLIC_API_URL=http://localhost:8000  # Dev
# NEXT_PUBLIC_API_URL=https://zeues-backend-mvp-production.up.railway.app  # Prod
```

## Security Best Practices (Updated 2026-02-06)

### Credential Management

**CRITICAL:** Google Service Account credentials must NEVER be committed to Git.

**Verification completed (2026-02-06):**
- ✅ `.env` in `.gitignore`
- ✅ `google-credentials.json` and `credenciales/` in `.gitignore`
- ✅ Git history audited - no credentials found in any commits
- ✅ Credentials stored ONLY in Railway environment variables
- ✅ Local development uses `.env.local` (ignored by Git)

**Current setup:**
```bash
# Production (Railway)
GOOGLE_APPLICATION_CREDENTIALS_JSON={"type":"service_account",...}
GOOGLE_CLOUD_PROJECT_ID=zeus-mvp
GOOGLE_SHEET_ID=17iOaq2sv4mSOuJY4B8dGQIsWTTUKPspCtb7gk6u-MaQ

# Development (local .env.local - NOT committed)
GOOGLE_PRIVATE_KEY="-----BEGIN PRIVATE KEY-----\n...\n-----END PRIVATE KEY-----\n"
```

**If credentials are exposed:**
1. Immediately rotate credentials in [Google Cloud Console](https://console.cloud.google.com/iam-admin/serviceaccounts?project=zeus-mvp)
2. Update Railway environment variables: `railway variables set GOOGLE_APPLICATION_CREDENTIALS_JSON='...'`
3. Redeploy: `railway up`
4. Delete old key in Google Cloud Console

### Debug Endpoints (Removed Feb 2026)

**Security improvement:** All debug endpoints removed to reduce attack surface.

**Previously available (now removed):**
- `/api/health/diagnostic` - Exposed Google Sheets structure
- `/api/health/column-map` - Exposed column mappings
- `/api/health/test-get-spool-flow` - Exposed query logic
- `/api/health/test-spool-constructor` - Exposed data parsing
- `/api/health/clear-cache` - Allowed cache manipulation

**Alternatives for debugging:**
```bash
# View column mappings
railway logs | grep "Column map built"

# Clear cache (use Railway restart instead)
railway restart

# Test Google Sheets connection
curl https://zeues-backend-mvp-production.up.railway.app/api/health

# Inspect Sheets structure
open https://docs.google.com/spreadsheets/d/17iOaq2sv4mSOuJY4B8dGQIsWTTUKPspCtb7gk6u-MaQ/edit
```

## Debugging

### API Endpoints

**Active Endpoints (single-user mode):**
```bash
# Occupation
POST /api/occupation/tomar
POST /api/occupation/pausar
POST /api/occupation/completar
GET  /api/occupation/diagnostic/{tag}

# History
GET /api/history/{tag_spool}

# Health (Sheets only)
GET /api/health  # Only public endpoint - no debug info exposed

# Cache
POST /api/cache/clear
```

**Removed (single-user mode):**
- Real-time streaming endpoints (no concurrent operations)
- **Debug endpoints (Feb 2026 - security improvement):**
  - `/api/health/diagnostic`
  - `/api/health/column-map`
  - `/api/health/test-get-spool-flow`
  - `/api/health/test-spool-constructor`
  - `/api/health/clear-cache`

**v4.0 Endpoints (Phase 8 - P5 Workflow):**
```bash
# INICIAR/FINALIZAR (P5 Confirmation)
POST /api/v4/occupation/iniciar    # Writes Ocupado_Por at P5 confirmation
POST /api/v4/occupation/finalizar  # Processes unions + auto PAUSAR/COMPLETAR
GET  /api/v4/unions/{tag}          # List available unions for spool
GET  /api/v4/metricas/{tag}        # Pulgadas-diámetro metrics
```

### Common Issues

**ImportError:**
```bash
source venv/bin/activate
PYTHONPATH="$(pwd)" pytest
```

**Google Sheets connection:**
```bash
# Test health endpoint
curl http://localhost:8000/api/health
# Expected: {"status": "healthy", "operational": true, "sheets_connection": "ok"}
```

## Schema Validation & Startup Checks

**Pre-deployment validation:**
```bash
# Validate v4.0 schema before deployment (critical + v4.0 columns)
python backend/scripts/validate_schema_startup.py

# Check Uniones sheet structure (17 columns)
python backend/scripts/validate_uniones_sheet.py

# Add missing Uniones headers (structure only, no data)
python backend/scripts/validate_uniones_sheet.py --fix
```

**FastAPI startup validation:**
- Integrated at `main.py` startup event (after cache warming)
- Validates Operaciones (72 cols), Metadata (11 cols), Uniones (18 cols)
- Deployment fails fast if schema incomplete
- Extra columns allowed, only missing columns cause failure

## Production URLs

- Frontend: https://zeues-frontend.vercel.app
- Backend: https://zeues-backend-mvp-production.up.railway.app
- API Docs: https://zeues-backend-mvp-production.up.railway.app/docs

## Key Constraints

- Google Sheets is source of truth (no database migration)
- Mobile-first UI (large buttons h-16/h-20, touch-friendly)
- Google Sheets limits: 60 writes/min/user, 200-500ms latency
- Manufacturing scale: 30-50 workers, 2,000+ spools, 10-15 req/sec
- Regulatory: Metadata audit trail mandatory (append-only, immutable)

---

**For detailed v3.0 architecture, requirements, and technical decisions, see `.planning/PROJECT.md`**

---

**Last updated:** 2026-02-06 (security audit complete - C1 & H3 resolved)
**Document version:** 3.2

**Security improvements (Feb 6, 2026):**
- ✅ Credential audit: No leaks found in Git history
- ✅ Debug endpoints removed: 476 lines of debug code eliminated
- ✅ Attack surface reduced: 5 internal endpoints no longer exposed
