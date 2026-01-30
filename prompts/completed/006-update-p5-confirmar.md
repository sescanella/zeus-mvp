<objective>
Update P5 (confirmar) page to call the new v3.0 occupation tracking endpoints (TOMAR/PAUSAR/COMPLETAR/CANCELAR) based on the selected action type, replacing the legacy v2.1 INICIAR/COMPLETAR workflow.

This page is the final confirmation step in the 7-page flow where the actual API calls are made. The updated version must call the correct v3.0 endpoint based on selectedTipo from Context and handle operation-specific logic (ARM vs SOLD vs REPARACIÓN).
</objective>

<context>
**Current State:**
- File: `zeues-frontend/app/confirmar/page.tsx`
- Currently calls v2.1 endpoints: `iniciarAccion()`, `completarAccion()`, `cancelarAccion()`
- Handles action types: 'iniciar', 'completar', 'cancelar'

**v3.0 Requirements:**
- P3 sets selectedTipo to: 'tomar', 'pausar', 'completar', 'cancelar'
- P4 filters spools based on selectedTipo
- P5 must call the appropriate v3.0 endpoint

**API Functions (from lib/api.ts - added in prompt 004):**
- `tomarSpool(tagSpool, workerId, operacion)` → POST /api/occupation/tomar
- `pausarSpool(tagSpool, workerId, operacion)` → POST /api/occupation/pausar
- `completarSpool(tagSpool, workerId, operacion)` → POST /api/occupation/completar
- `tomarReparacion(tagSpool, workerId)` → POST /api/reparacion/tomar-reparacion
- `pausarReparacion(tagSpool, workerId)` → POST /api/reparacion/pausar-reparacion
- `completarReparacion(tagSpool, workerId)` → POST /api/reparacion/completar-reparacion
- `cancelarReparacion(tagSpool, workerId)` → POST /api/reparacion/cancelar-reparacion

**Operation-Specific Logic:**
- **ARM/SOLD:** Use general occupation endpoints (tomar, pausar, completar)
- **REPARACIÓN:** Use reparación-specific endpoints (tomarReparacion, pausarReparacion, completarReparacion, cancelarReparacion)
- **METROLOGÍA:** Uses completarMetrologia() - already implemented, no changes needed

Read @zeues-frontend/app/confirmar/page.tsx for current implementation.
Read @zeues-frontend/lib/api.ts to see v3.0 API functions.
Read @CLAUDE.md for project conventions and v3.0 architecture.
</context>

<requirements>
**Functional Requirements:**

1. **Update Action Type Handling:**
   - Replace 'iniciar' → 'tomar'
   - Keep 'pausar', 'completar', 'cancelar' (new action types)

2. **Conditional API Calls Based on selectedTipo:**
   ```typescript
   if (selectedTipo === 'tomar') {
     if (operacion === 'REPARACION') {
       await tomarReparacion(tagSpool, workerId);
     } else {
       await tomarSpool(tagSpool, workerId, operacion);
     }
   } else if (selectedTipo === 'pausar') {
     if (operacion === 'REPARACION') {
       await pausarReparacion(tagSpool, workerId);
     } else {
       await pausarSpool(tagSpool, workerId, operacion);
     }
   } else if (selectedTipo === 'completar') {
     if (operacion === 'REPARACION') {
       await completarReparacion(tagSpool, workerId);
     } else {
       await completarSpool(tagSpool, workerId, operacion);
     }
   } else if (selectedTipo === 'cancelar') {
     // Only REPARACIÓN supports cancelar in v3.0
     await cancelarReparacion(tagSpool, workerId);
   }
   ```

3. **Error Handling:**
   - 409 Conflict: "Spool ya está ocupado por otro trabajador"
   - 403 Forbidden: "No tienes autorización para esta operación"
   - 404 Not Found: "Spool no encontrado"
   - 400 Bad Request: "Error de validación - verifica los datos"
   - Generic: "Error al {tomar|pausar|completar|cancelar} spool"

4. **Confirmation Messages:**
   - TOMAR: "¿Confirmar TOMAR spool {tag}?"
   - PAUSAR: "¿Confirmar PAUSAR trabajo en spool {tag}?"
   - COMPLETAR: "¿Confirmar COMPLETAR trabajo en spool {tag}?"
   - CANCELAR: "¿Confirmar CANCELAR reparación en spool {tag}?"

5. **TypeScript Type Safety:**
   - NO `any` types (ESLint will fail)
   - Proper type for selectedTipo
   - Type-safe API function calls

**Non-Functional Requirements:**
- Must pass: `npx tsc --noEmit` (TypeScript validation)
- Must pass: `npm run lint` (ESLint validation)
- Mobile-first responsive design (tablet optimized)
- Maintain existing visual design language (grid background, border-4, font-mono, etc.)
- Loading states during API calls
</requirements>

<implementation>
**Step-by-step approach:**

1. **Import new API functions:**
   ```typescript
   import {
     tomarSpool,
     pausarSpool,
     completarSpool,
     tomarReparacion,
     pausarReparacion,
     completarReparacion,
     cancelarReparacion
   } from '@/lib/api';
   ```

2. **Update handleConfirm function to call appropriate endpoint:**
   ```typescript
   const handleConfirm = async () => {
     try {
       setLoading(true);
       setError('');

       const tagSpool = state.selectedSpool;
       const workerId = state.selectedWorker.id;
       const operacion = state.selectedOperation;

       // Route to correct endpoint based on tipo and operation
       if (state.selectedTipo === 'tomar') {
         if (operacion === 'REPARACION') {
           await tomarReparacion(tagSpool, workerId);
         } else {
           await tomarSpool(tagSpool, workerId, operacion);
         }
       } else if (state.selectedTipo === 'pausar') {
         // ... similar pattern
       }
       // ... handle other tipos

       // Success - navigate to success page
       router.push('/exito');
     } catch (err) {
       // Error handling with specific messages
       const errorMessage = err instanceof Error ? err.message : 'Error desconocido';

       if (errorMessage.includes('409')) {
         setError('Spool ya está ocupado por otro trabajador');
       } else if (errorMessage.includes('403')) {
         setError('No tienes autorización para esta operación');
       }
       // ... handle other status codes
     } finally {
       setLoading(false);
     }
   };
   ```

3. **Update confirmation message display:**
   ```typescript
   const getConfirmationMessage = () => {
     const tag = state.selectedSpool;
     switch(state.selectedTipo) {
       case 'tomar': return `¿Confirmar TOMAR spool ${tag}?`;
       case 'pausar': return `¿Confirmar PAUSAR trabajo en spool ${tag}?`;
       case 'completar': return `¿Confirmar COMPLETAR trabajo en spool ${tag}?`;
       case 'cancelar': return `¿Confirmar CANCELAR reparación en spool ${tag}?`;
     }
   };
   ```

4. **Update button text:**
   ```typescript
   const getButtonText = () => {
     if (loading) return 'PROCESANDO...';
     switch(state.selectedTipo) {
       case 'tomar': return 'CONFIRMAR TOMAR';
       case 'pausar': return 'CONFIRMAR PAUSAR';
       case 'completar': return 'CONFIRMAR COMPLETAR';
       case 'cancelar': return 'CONFIRMAR CANCELAR';
     }
   };
   ```

**What to avoid and WHY:**
- ❌ Don't remove v2.1 function calls entirely - other flows may still use them (backward compatibility)
- ❌ Don't call TOMAR for METROLOGÍA - it bypasses P3/P4/P5 entirely (has separate resultado-metrologia page)
- ❌ Don't use `any` types - TypeScript strict mode is enforced for type safety
- ❌ Don't swallow errors - users need clear feedback when operations fail (e.g., spool already occupied)
- ❌ Don't skip validation checks - ensure selectedWorker, selectedSpool, selectedOperation, selectedTipo all exist
</implementation>

<output>
Modify the existing file:
- `./zeues-frontend/app/confirmar/page.tsx` - Update to call v3.0 occupation endpoints based on selectedTipo

DO NOT modify:
- lib/api.ts - API functions were added in prompt 004
- Other pages - P3, P4 are already updated
- Context - type definitions already updated in P3 prompt
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

3. **Endpoint routing verification:**
   - TOMAR + ARM → tomarSpool(tag, worker, 'ARM')
   - TOMAR + REPARACION → tomarReparacion(tag, worker)
   - PAUSAR + SOLD → pausarSpool(tag, worker, 'SOLD')
   - COMPLETAR + ARM → completarSpool(tag, worker, 'ARM')
   - CANCELAR (REPARACION only) → cancelarReparacion(tag, worker)

4. **Error handling verification:**
   - Check all HTTP status codes have specific error messages
   - Verify loading state shows during API calls
   - Confirm error messages are user-friendly

5. **Visual verification (if dev server running):**
   - Full flow: Home → Worker → ARM → TOMAR → Select spool → Confirm → Should call POST /api/occupation/tomar
   - Error case: Try to TOMAR already occupied spool → Should show "Spool ya está ocupado" error
</verification>

<success_criteria>
- ✓ P5 page calls correct v3.0 endpoint based on selectedTipo and selectedOperation
- ✓ ARM/SOLD use general occupation endpoints (tomar, pausar, completar)
- ✓ REPARACIÓN uses reparación-specific endpoints
- ✓ CANCELAR only works for REPARACIÓN (v3.0 constraint)
- ✓ Error handling provides clear, actionable messages
- ✓ Loading states prevent double-submissions
- ✓ TypeScript compilation passes (`npx tsc --noEmit`)
- ✓ ESLint passes with no warnings (`npm run lint`)
- ✓ No `any` types used
- ✓ Confirmation messages are contextual and clear
</success_criteria>

<notes>
**Why this matters:**
- P5 is where the actual v3.0 occupation tracking happens (Redis locks, Sheets updates, Metadata logging)
- Correct endpoint routing is critical - calling wrong endpoint could corrupt data or create race conditions
- Error handling quality directly impacts UX - workers need clear feedback when conflicts occur
- This completes the frontend v3.0 migration chain: P3 (action type) → P4 (spool selection) → P5 (API call)

**Testing recommendations:**
- Test full flow for each action type (TOMAR, PAUSAR, COMPLETAR)
- Test REPARACIÓN-specific flow including CANCELAR
- Test error cases (occupied spool, missing prerequisites, expired lock)
- Verify Metadata events are logged correctly in backend
</notes>
