<objective>
Update the P3 (tipo-interaccion) page from v2.1 workflow (INICIAR/COMPLETAR/CANCELAR) to v3.0 workflow (TOMAR/PAUSAR/COMPLETAR) to align with the new occupation tracking system.

This page is critical in the 7-page user flow as it determines which action type the worker will perform on a spool. The updated version must support the new v3.0 real-time occupation tracking with Redis locks while handling special cases for METROLOGÍA (which bypasses TOMAR) and REPARACIÓN workflows.
</objective>

<context>
**Current State:**
- P3 shows: INICIAR | COMPLETAR | CANCELAR ACCIÓN (v2.1 workflow)
- File: `zeues-frontend/app/tipo-interaccion/page.tsx`
- Currently maps to legacy v2.1 endpoints

**v3.0 Requirements (from PROJECT.md and backend analysis):**
- **ARM/SOLD operations:** TOMAR → PAUSAR → COMPLETAR workflow
  - TOMAR: Acquire Redis lock, mark spool as OCUPADO
  - PAUSAR: Release lock without completing, preserves progress
  - COMPLETAR: Finish work, release lock, write fecha_armado/soldadura
- **METROLOGÍA operation:** Skip P3 entirely, go directly to resultado-metrología page
  - Instant completion with APROBADO/RECHAZADO binary result
  - No TOMAR needed (inspection takes seconds, not hours)
- **REPARACIÓN operation:** TOMAR → COMPLETAR workflow
  - Supports CANCELAR_REPARACION (returns to RECHAZADO state)

**Backend Endpoints (from occupation_service.py and enums.py):**
- POST `/api/occupation/tomar`
- POST `/api/occupation/pausar`
- POST `/api/occupation/completar`
- POST `/api/metrologia/completar`
- POST `/api/reparacion/tomar-reparacion`
- POST `/api/reparacion/completar-reparacion`
- POST `/api/reparacion/cancelar-reparacion`

**Event Types (EventoTipo enum):**
- v3.0: TOMAR_SPOOL, PAUSAR_SPOOL
- Reparación: TOMAR_REPARACION, PAUSAR_REPARACION, COMPLETAR_REPARACION, CANCELAR_REPARACION
- Legacy v2.1: INICIAR_ARM, COMPLETAR_ARM, CANCELAR_ARM (still supported but not primary)

Read @zeues-frontend/app/tipo-interaccion/page.tsx for current implementation.
Read @zeues-frontend/app/resultado-metrologia/page.tsx to understand METROLOGÍA flow.
Read @CLAUDE.md for project conventions and v3.0 architecture.
</context>

<requirements>
**Functional Requirements:**

1. **Dynamic Button Display Based on Operation:**
   - For ARM/SOLD: Show 3 buttons (TOMAR, PAUSAR, COMPLETAR)
   - For METROLOGÍA: Bypass P3 entirely, redirect to `/resultado-metrologia`
   - For REPARACIÓN: Show all 4 buttons (TOMAR, PAUSAR, COMPLETAR, CANCELAR)

2. **Update Action Type Definitions:**
   - Change from `'iniciar' | 'completar' | 'cancelar'` to `'tomar' | 'pausar' | 'completar' | 'cancelar'`
   - Update selectedTipo in Context to support new action types

3. **Visual Design (Mobile-First, Tablet UI):**
   - **TOMAR button:** Orange accent (zeues-orange), Play icon (from lucide-react)
   - **PAUSAR button:** Yellow/amber accent, Pause icon (from lucide-react)
   - **COMPLETAR button:** Green accent (green-500), CheckCircle icon
   - **CANCELAR button (REPARACIÓN only):** Red accent (red-500), XCircle icon
   - 3-column grid layout for TOMAR/PAUSAR/COMPLETAR (h-40 narrow:h-32)
   - CANCELAR as full-width button below (h-24 narrow:h-20) - only for REPARACIÓN

4. **Navigation Logic:**
   - METROLOGÍA: `if (state.selectedOperation === 'METRO') router.push('/resultado-metrologia')`
   - Other operations: `router.push(\`/seleccionar-spool?tipo=\${tipo}\`)`
   - Remove old "CANCELAR ACCIÓN" navigation button (not a spool operation in v3.0)
   - Keep bottom navigation: VOLVER | INICIO (existing pattern)

5. **TypeScript Type Safety:**
   - NO `any` types (ESLint will fail)
   - Proper type definitions for action types
   - Update Context type definitions if needed

**Non-Functional Requirements:**
- Must pass: `npx tsc --noEmit` (TypeScript validation)
- Must pass: `npm run lint` (ESLint validation)
- Mobile-first responsive design (tablet optimized)
- Maintain existing visual design language (grid background, border-4, font-mono, etc.)
</requirements>

<implementation>
**Step-by-step approach:**

1. **Add METROLOGÍA bypass logic at the top of the component:**
   ```typescript
   useEffect(() => {
     // Redirect check
     if (!state.selectedWorker || !state.selectedOperation) {
       router.push('/');
       return;
     }

     // METROLOGÍA bypass - skip P3, go directly to resultado
     if (state.selectedOperation === 'METRO') {
       router.push('/resultado-metrologia');
     }
   }, [state, router]);
   ```

2. **Update handleSelectTipo function:**
   - Change parameter type to `'tomar' | 'pausar' | 'completar' | 'cancelar'`
   - Update setState and router.push logic

3. **Import Pause icon from lucide-react:**
   ```typescript
   import { Pause } from 'lucide-react';
   ```

4. **Replace INICIAR/COMPLETAR/CANCELAR buttons with TOMAR/PAUSAR/COMPLETAR:**
   - Use 3-column grid for ARM/SOLD/REPARACIÓN (without CANCELAR)
   - Add conditional CANCELAR button for REPARACIÓN only:
     ```typescript
     {state.selectedOperation === 'REPARACION' && (
       <button onClick={() => handleSelectTipo('cancelar')} ...>
         CANCELAR REPARACIÓN
       </button>
     )}
     ```

5. **Update visual styling:**
   - TOMAR: `active:bg-zeues-orange active:border-zeues-orange`
   - PAUSAR: `active:bg-yellow-500 active:border-yellow-500` (new color)
   - COMPLETAR: `active:bg-green-500 active:border-green-500` (existing)
   - CANCELAR: `active:bg-red-500 active:border-red-500` (existing)

**What to avoid and WHY:**
- ❌ Don't show CANCELAR button for ARM/SOLD operations - v3.0 uses PAUSAR instead (CANCELAR only exists for REPARACIÓN)
- ❌ Don't call TOMAR for METROLOGÍA - it bypasses occupation tracking entirely (inspection is instant)
- ❌ Don't use `any` types - TypeScript strict mode is enforced for type safety
- ❌ Don't remove the worker info bar or bottom navigation - these are part of the consistent UX pattern across all pages
- ❌ Don't make API calls in P3 - this page only sets selectedTipo in Context, actual API calls happen in P5 (confirmar page)
</implementation>

<output>
Modify the existing file:
- `./zeues-frontend/app/tipo-interaccion/page.tsx` - Update to v3.0 workflow with TOMAR/PAUSAR/COMPLETAR buttons and METROLOGÍA bypass

You may need to update:
- `./zeues-frontend/lib/context.tsx` - If selectedTipo type definition needs updating
- `./zeues-frontend/lib/types.ts` - If ActionType interface needs updating

DO NOT modify:
- API integration files (lib/api.ts) - those updates will be handled separately
- Other pages (P4, P5) - those will be updated in subsequent prompts
</output>

<verification>
Before declaring complete, verify your work:

1. **TypeScript validation:**
   ```bash
   cd zeues-frontend
   npx tsc --noEmit
   ```
   Must pass with no errors.

2. **ESLint validation:**
   ```bash
   npm run lint
   ```
   Must pass with no warnings (especially no `any` types).

3. **Visual inspection:**
   - Run dev server: `npm run dev`
   - Navigate to P3: Select worker → Select ARM operation → Should see TOMAR/PAUSAR/COMPLETAR buttons
   - Test METROLOGÍA bypass: Select worker → Select METROLOGÍA → Should skip P3 and go to resultado-metrologia

4. **Operation-specific rendering:**
   - ARM: Shows TOMAR, PAUSAR, COMPLETAR (3 buttons)
   - SOLD: Shows TOMAR, PAUSAR, COMPLETAR (3 buttons)
   - METROLOGÍA: Bypasses P3 entirely
   - REPARACIÓN: Shows TOMAR, PAUSAR, COMPLETAR, CANCELAR (4 buttons)

5. **Context state verification:**
   - Click TOMAR → Context should set selectedTipo='tomar'
   - Click PAUSAR → Context should set selectedTipo='pausar'
   - Click COMPLETAR → Context should set selectedTipo='completar'
   - Verify navigation to `/seleccionar-spool?tipo=${tipo}` works
</verification>

<success_criteria>
- ✓ P3 page displays TOMAR/PAUSAR/COMPLETAR buttons for ARM/SOLD operations
- ✓ METROLOGÍA operation bypasses P3 and redirects to resultado-metrologia
- ✓ REPARACIÓN operation shows all 4 buttons including CANCELAR
- ✓ TypeScript compilation passes (`npx tsc --noEmit`)
- ✓ ESLint passes with no warnings (`npm run lint`)
- ✓ Visual design matches ZEUES design language (mobile-first, large buttons, grid background)
- ✓ Navigation works correctly (selectedTipo set in Context, router.push to seleccionar-spool)
- ✓ No `any` types used
- ✓ METROLOGÍA bypass confirmed in browser (skips P3)
</success_criteria>

<notes>
**Why this matters:**
- P3 is the decision point in the 7-page flow where workers choose their action type
- v3.0's TOMAR/PAUSAR/COMPLETAR workflow enables real-time occupation tracking with Redis locks
- METROLOGÍA bypass is critical - showing TOMAR for instant inspections would create false "occupied" signals
- This update unblocks the rest of the frontend migration to v3.0 (P4, P5 will follow)

**Known dependencies:**
- P4 (seleccionar-spool) and P5 (confirmar) will need updates after this to handle new action types
- API integration (lib/api.ts) will need new functions for TOMAR/PAUSAR endpoints
- These are intentionally out of scope for this prompt to keep changes atomic
</notes>
