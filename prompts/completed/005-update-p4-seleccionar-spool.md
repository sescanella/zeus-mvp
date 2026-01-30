<objective>
Update P4 (seleccionar-spool) page to handle new v3.0 action types (tomar, pausar, completar, cancelar) and filter spools appropriately based on the selected action.

This page is the spool selection step in the 7-page flow where workers choose which spool to work on. The updated version must filter spools differently based on whether the worker wants to TOMAR (show available spools), PAUSAR/COMPLETAR (show occupied spools), or CANCELAR (show spools in progress).
</objective>

<context>
**Current State:**
- File: `zeues-frontend/app/seleccionar-spool/page.tsx`
- Currently handles v2.1 action types: 'iniciar', 'completar', 'cancelar'
- Filters spools based on these legacy action types

**v3.0 Requirements:**
- P3 (tipo-interaccion) now sets selectedTipo to: 'tomar', 'pausar', 'completar', 'cancelar'
- URL param: `/seleccionar-spool?tipo={tomar|pausar|completar|cancelar}`

**Spool Filtering Logic (v3.0):**
- **TOMAR:** Show DISPONIBLE spools (not currently occupied, prerequisites met)
  - ARM: Fecha_Materiales filled, Ocupado_Por empty, ARM not started or pausado
  - SOLD: Fecha_Materiales + ARM complete, Ocupado_Por empty, SOLD not started or pausado
  - REPARACION: Estado_Detalle contains "RECHAZADO", not BLOQUEADO
- **PAUSAR:** Show spools OCUPADO by current worker
  - Filter: Ocupado_Por = current worker ID
- **COMPLETAR:** Show spools OCUPADO by current worker (same as PAUSAR)
  - Filter: Ocupado_Por = current worker ID
- **CANCELAR (REPARACIÓN only):** Show spools in reparación by current worker
  - Filter: Ocupado_Por = current worker ID, operacion = REPARACION

**API Endpoints (existing backend):**
- GET `/api/spools/disponible?operacion={ARM|SOLD|REPARACION}` - Available spools for TOMAR
- GET `/api/spools/ocupados?worker_id={id}&operacion={ARM|SOLD|REPARACION}` - Spools occupied by worker
- GET `/api/spools` - All spools (can filter client-side if needed)

Read @zeues-frontend/app/seleccionar-spool/page.tsx for current implementation.
Read @zeues-frontend/lib/api.ts to see available API functions.
Read @CLAUDE.md for project conventions and v3.0 architecture.
</context>

<requirements>
**Functional Requirements:**

1. **Update Action Type Handling:**
   - Read `tipo` query parameter: `'tomar' | 'pausar' | 'completar' | 'cancelar'`
   - Remove old 'iniciar' handling, replace with 'tomar'

2. **Conditional Spool Filtering:**
   - **For TOMAR:** Call `/api/spools/disponible?operacion={operation}`
     - Show spools that are available for the selected operation
   - **For PAUSAR/COMPLETAR:** Call `/api/spools/ocupados?worker_id={id}&operacion={operation}`
     - Show only spools currently occupied by the logged-in worker
   - **For CANCELAR:** Call `/api/spools/ocupados?worker_id={id}&operacion=REPARACION`
     - Show only reparación spools occupied by current worker

3. **Visual Updates:**
   - Update page title based on action type:
     - TOMAR: "SELECCIONAR SPOOL PARA TOMAR"
     - PAUSAR: "SELECCIONAR SPOOL PARA PAUSAR"
     - COMPLETAR: "SELECCIONAR SPOOL PARA COMPLETAR"
     - CANCELAR: "SELECCIONAR REPARACIÓN PARA CANCELAR"

4. **Empty State Messaging:**
   - TOMAR: "No hay spools disponibles para {operacion}"
   - PAUSAR: "No tienes spools en progreso para pausar"
   - COMPLETAR: "No tienes spools en progreso para completar"
   - CANCELAR: "No tienes reparaciones en progreso para cancelar"

5. **TypeScript Type Safety:**
   - NO `any` types (ESLint will fail)
   - Proper type for `tipo` query parameter
   - Update Context types if needed

**Non-Functional Requirements:**
- Must pass: `npx tsc --noEmit` (TypeScript validation)
- Must pass: `npm run lint` (ESLint validation)
- Mobile-first responsive design (tablet optimized)
- Maintain existing visual design language (grid background, border-4, font-mono, etc.)
</requirements>

<implementation>
**Step-by-step approach:**

1. **Update tipo query parameter handling:**
   ```typescript
   const searchParams = useSearchParams();
   const tipo = searchParams.get('tipo') as 'tomar' | 'pausar' | 'completar' | 'cancelar';
   ```

2. **Implement conditional API calls based on tipo:**
   ```typescript
   useEffect(() => {
     const fetchSpools = async () => {
       if (tipo === 'tomar') {
         // GET /api/spools/disponible?operacion={operation}
         const spools = await getSpoolsDisponible(state.selectedOperation);
       } else if (tipo === 'pausar' || tipo === 'completar') {
         // GET /api/spools/ocupados?worker_id={id}&operacion={operation}
         const spools = await getSpoolsOcupados(state.selectedWorker.id, state.selectedOperation);
       } else if (tipo === 'cancelar') {
         // GET /api/spools/ocupados?worker_id={id}&operacion=REPARACION
         const spools = await getSpoolsOcupados(state.selectedWorker.id, 'REPARACION');
       }
       setSpools(spools);
     };
     fetchSpools();
   }, [tipo, state]);
   ```

3. **Update page title dynamically:**
   ```typescript
   const getTitle = () => {
     switch(tipo) {
       case 'tomar': return 'SELECCIONAR SPOOL PARA TOMAR';
       case 'pausar': return 'SELECCIONAR SPOOL PARA PAUSAR';
       case 'completar': return 'SELECCIONAR SPOOL PARA COMPLETAR';
       case 'cancelar': return 'SELECCIONAR REPARACIÓN PARA CANCELAR';
     }
   };
   ```

4. **Update empty state messages:**
   ```typescript
   const getEmptyMessage = () => {
     switch(tipo) {
       case 'tomar': return `No hay spools disponibles para ${operationLabel}`;
       case 'pausar': return 'No tienes spools en progreso para pausar';
       case 'completar': return 'No tienes spools en progreso para completar';
       case 'cancelar': return 'No tienes reparaciones en progreso para cancelar';
     }
   };
   ```

5. **Add API functions if needed (check lib/api.ts first):**
   - If `getSpoolsDisponible()` doesn't exist, add it
   - If `getSpoolsOcupados()` doesn't exist, add it

**What to avoid and WHY:**
- ❌ Don't remove validation for selectedWorker/selectedOperation - page requires these from Context
- ❌ Don't make assumptions about spool state client-side - backend filtering is authoritative (avoids race conditions)
- ❌ Don't use `any` types - TypeScript strict mode is enforced for type safety
- ❌ Don't show ALL spools for PAUSAR/COMPLETAR - only show worker's own occupied spools (prevents accidental interference)
- ❌ Don't modify spool selection logic yet - just update filtering (P5 will handle API calls)
</implementation>

<output>
Modify the existing file:
- `./zeues-frontend/app/seleccionar-spool/page.tsx` - Update to handle v3.0 action types and filter spools appropriately

You may need to add to:
- `./zeues-frontend/lib/api.ts` - Add getSpoolsDisponible() and getSpoolsOcupados() functions if they don't exist

DO NOT modify:
- P5 (confirmar page) - that will be updated separately to call TOMAR/PAUSAR/COMPLETAR endpoints
- Context or types files - unless tipo type definition is missing
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

3. **Action type handling verification:**
   - TOMAR: Calls /api/spools/disponible with correct operation
   - PAUSAR: Calls /api/spools/ocupados with worker_id + operation
   - COMPLETAR: Calls /api/spools/ocupados with worker_id + operation
   - CANCELAR: Calls /api/spools/ocupados with worker_id + REPARACION

4. **Visual verification (if dev server running):**
   - Navigate: Home → Worker → ARM → TOMAR → Should see available ARM spools
   - Navigate: Home → Worker → SOLD → PAUSAR → Should see worker's occupied SOLD spools
   - Navigate: Home → Worker → REPARACION → CANCELAR → Should see worker's reparación spools

5. **Empty state verification:**
   - Each action type shows appropriate message when no spools match filter
</verification>

<success_criteria>
- ✓ P4 page handles all 4 v3.0 action types (tomar, pausar, completar, cancelar)
- ✓ Spool filtering logic matches v3.0 requirements
- ✓ Page title updates dynamically based on action type
- ✓ Empty state messages are contextual and helpful
- ✓ TypeScript compilation passes (`npx tsc --noEmit`)
- ✓ ESLint passes with no warnings (`npm run lint`)
- ✓ No `any` types used
- ✓ API functions exist for disponible/ocupados filtering
</success_criteria>

<notes>
**Why this matters:**
- P4 is the spool selection step - workers must see the RIGHT spools based on their intended action
- TOMAR requires showing available spools (prevent double-occupation)
- PAUSAR/COMPLETAR require showing worker's own occupied spools (prevent interfering with others)
- Proper filtering prevents UX confusion and backend validation errors

**Known dependencies:**
- Depends on lib/api.ts having getSpoolsDisponible() and getSpoolsOcupados() functions
- P5 (confirmar) will use the selected spool to call TOMAR/PAUSAR/COMPLETAR endpoints
</notes>
