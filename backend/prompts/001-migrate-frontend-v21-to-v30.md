<objective>
Migrate the ZEUES frontend from v2.1 legacy endpoints to v3.0 occupation endpoints.

**Why this matters:** The frontend currently calls v2.1 endpoints (`/api/iniciar-accion`) which only update the `Armador` column. The v3.0 endpoints (`/api/occupation/tomar`) write ALL occupation columns (`Ocupado_Por`, `Fecha_Ocupacion`, `Version`, `Estado_Detalle`) and provide Redis-based race condition protection, optimistic locking, and real-time event streaming capabilities.

**End goal:** Complete frontend integration with v3.0 backend, enabling full occupation tracking with concurrency protection.
</objective>

<context>
**Current state (v2.1 legacy):**
- Frontend uses: `POST /api/iniciar-accion`, `POST /api/completar-accion`, `POST /api/cancelar-accion`
- These endpoints only update basic columns (Armador/Soldador, Fecha_Armado/Fecha_Soldadura)
- No Redis locks, no version control, no Estado_Detalle tracking

**Target state (v3.0):**
- Backend v3.0 is FULLY IMPLEMENTED and ACTIVE (244/244 tests passing)
- v3.0 endpoints available: `POST /api/occupation/tomar`, `POST /api/occupation/pausar`, `POST /api/occupation/completar`, `POST /api/occupation/batch-tomar`
- These provide: Redis locks, optimistic version control, Estado_Detalle updates, SSE events

**Tech stack:**
- Frontend: Next.js 14 + TypeScript + Tailwind CSS
- API client: Native fetch (NO axios) in `zeues-frontend/lib/api.ts`
- Type definitions: `zeues-frontend/lib/types.ts`

**Files to examine:**
@../zeues-frontend/lib/api.ts - Current API functions (v2.1)
@../zeues-frontend/lib/types.ts - TypeScript interfaces
@routers/occupation.py - v3.0 endpoint specifications
@models/occupation.py - v3.0 request/response schemas (CRITICAL: verify exact schemas)
@models/enums.py - ActionType enum (valid operations: ARM, SOLD, METROLOGIA, REPARACION)
@../CLAUDE.md - Project conventions and rules

**CRITICAL:** Working directory is `/backend`. All frontend paths must use `../zeues-frontend/`
</context>

<requirements>
**Phase 1: API Layer (lib/api.ts)**

1. **Create new v3.0 API functions:**
   - `tomarOcupacion(payload)` → `POST /api/occupation/tomar`
   - `pausarOcupacion(payload)` → `POST /api/occupation/pausar`
   - `completarOcupacion(payload)` → `POST /api/occupation/completar`
   - `tomarOcupacionBatch(payload)` → `POST /api/occupation/batch-tomar`

2. **Payload differences (v2.1 → v3.0):**

   **TOMAR (equivalent to v2.1 INICIAR):**
   - v2.1 INICIAR: `{ worker_id, operacion, tag_spool }`
   - v3.0 TOMAR: `{ tag_spool, worker_id, worker_nombre, operacion }` ← **NEW: worker_nombre required**

   **COMPLETAR:**
   - v2.1: `{ worker_id, operacion, tag_spool, timestamp? }`
   - v3.0: `{ tag_spool, worker_id, worker_nombre, fecha_operacion }` ← **NEW: worker_nombre + fecha_operacion required**

   **PAUSAR (NEW in v3.0 - NOT equivalent to CANCELAR):**
   - v3.0: `{ tag_spool, worker_id, worker_nombre }`
   - Semantic difference: PAUSAR marks as "parcial (pausado)", CANCELAR reverts to PENDIENTE

   **BATCH:**
   - v2.1: `{ worker_id, operacion, tag_spools[] }`
   - v3.0: `{ tag_spools[], worker_id, worker_nombre, operacion }` ← **NEW: worker_nombre required**

3. **Response differences (CRITICAL - verify with backend models):**
   - v2.1: Complex `ActionResponse` with data object
   - v3.0: Simple `OccupationResponse` with **ONLY 3 fields:**
     ```typescript
     {
       success: boolean;
       tag_spool: string;
       message: string;
     }
     ```
   ⚠️ **WARNING:** Backend does NOT return `ocupado_por`, `fecha_ocupacion`, `version`, `estado_detalle` in response.
   These columns are written to Sheets but NOT returned in API response.

4. **Error handling (CRITICAL):**
   - Handle NEW v3.0 error codes:
     - `409 CONFLICT` → Spool occupied by another worker (Redis lock active)
     - `409 VERSION_CONFLICT` → Version mismatch (optimistic locking failure)
     - `410 GONE` → Lock expired (worker took too long)
   - Preserve v2.1 error handling for 403, 404, 400

**Phase 2: Type Definitions (lib/types.ts)**

5. **Add v3.0 TypeScript interfaces (CORRECTED to match backend models/occupation.py):**
   ```typescript
   // TOMAR Request
   export interface TomarRequest {
     tag_spool: string;
     worker_id: number;
     worker_nombre: string;  // Format: "INICIALES(ID)" e.g., "MR(93)"
     operacion: 'ARM' | 'SOLD' | 'METROLOGIA' | 'REPARACION';
   }

   // PAUSAR Request
   export interface PausarRequest {
     tag_spool: string;
     worker_id: number;
     worker_nombre: string;
   }

   // COMPLETAR Request
   export interface CompletarRequest {
     tag_spool: string;
     worker_id: number;
     worker_nombre: string;
     fecha_operacion: string;  // REQUIRED - Format: "YYYY-MM-DD" (e.g., "2026-01-28")
   }

   // BATCH TOMAR Request
   export interface BatchTomarRequest {
     tag_spools: string[];  // Min 1, Max 50 (validated by backend)
     worker_id: number;
     worker_nombre: string;
     operacion: 'ARM' | 'SOLD' | 'METROLOGIA' | 'REPARACION';
   }

   // Response for single operations (TOMAR/PAUSAR/COMPLETAR)
   export interface OccupationResponse {
     success: boolean;
     tag_spool: string;
     message: string;
   }

   // Response for batch operations
   export interface BatchOccupationResponse {
     total: number;      // Total spools processed
     succeeded: number;  // Number of successful operations
     failed: number;     // Number of failed operations
     details: OccupationResponse[];  // Individual results per spool
   }
   ```

   **CRITICAL NOTES:**
   - ❌ NO `location` field - not implemented in backend
   - ✅ `worker_nombre` is REQUIRED in ALL v3.0 requests (not in v2.1)
   - ✅ `fecha_operacion` is REQUIRED for COMPLETAR
   - ✅ Response uses English field names: `succeeded`/`failed` (NOT `exitosos`/`fallidos`)
   - ✅ `OccupationResponse` has ONLY 3 fields (backend doesn't return occupation details in response)

6. **CRITICAL TypeScript rule:** NEVER use `any` type (ESLint will fail). Use `unknown` for dynamic data or explicit types.

**Phase 3: Identify Component Migration Targets**

7. **Search for ALL v2.1 usage:**
   ```bash
   # Search for v2.1 function calls in frontend
   cd ../zeues-frontend
   grep -rn "iniciarAccion\|completarAccion\|cancelarAccion" app/ lib/ --include="*.tsx" --include="*.ts"
   ```
   Expected results: `app/confirmar/page.tsx` (imports and calls on lines ~9-15, ~59, ~84-89)

8. **Check for existing tests:**
   ```bash
   grep -r "iniciarAccion\|completarAccion\|cancelarAccion" **/*.test.{ts,tsx} 2>/dev/null
   ```
   Document any tests that need updating.

**Phase 4: Component Migration (CRITICAL - This solves the original problem)**

9. **Migrate `app/confirmar/page.tsx` to v3.0:**

   This is the PRIMARY file causing the issue (calls v2.1 endpoints which don't update occupation columns).

   **Step 9a: Update imports (lines ~9-15):**
   ```typescript
   // ❌ BEFORE (v2.1)
   import {
     iniciarAccion,
     completarAccion,
     cancelarAccion,
     iniciarAccionBatch,
     completarAccionBatch,
     cancelarAccionBatch
   } from '@/lib/api';

   // ✅ AFTER (v3.0)
   import {
     tomarOcupacion,
     completarOcupacion,
     pausarOcupacion,
     tomarOcupacionBatch,
     completarOcupacionBatch,
     pausarOcupacionBatch  // Note: PAUSAR not CANCELAR (semantic difference)
   } from '@/lib/api';
   import type { TomarRequest, CompletarRequest, PausarRequest, BatchTomarRequest } from '@/lib/types';
   ```

   **Step 9b: Update single spool handler (lines ~74-90):**
   ```typescript
   // ❌ BEFORE (v2.1)
   const payload: ActionPayload = {
     worker_id: state.selectedWorker!.id,
     operacion: state.selectedOperation as 'ARM' | 'SOLD',
     tag_spool: state.selectedSpool!,
     ...(tipo === 'completar' && { timestamp: new Date().toISOString() }),
   };

   if (tipo === 'iniciar') {
     await iniciarAccion(payload);
   } else if (tipo === 'completar') {
     await completarAccion(payload);
   } else {
     await cancelarAccion(payload);
   }

   // ✅ AFTER (v3.0)
   const worker_nombre = state.selectedWorker!.nombre_completo; // Format: "INICIALES(ID)"

   if (tipo === 'iniciar') {
     const payload: TomarRequest = {
       tag_spool: state.selectedSpool!,
       worker_id: state.selectedWorker!.id,
       worker_nombre,
       operacion: state.selectedOperation as 'ARM' | 'SOLD' | 'METROLOGIA' | 'REPARACION',
     };
     await tomarOcupacion(payload);
   } else if (tipo === 'completar') {
     const payload: CompletarRequest = {
       tag_spool: state.selectedSpool!,
       worker_id: state.selectedWorker!.id,
       worker_nombre,
       fecha_operacion: new Date().toISOString().split('T')[0], // YYYY-MM-DD format
     };
     await completarOcupacion(payload);
   } else {
     // tipo === 'cancelar'
     const payload: PausarRequest = {
       tag_spool: state.selectedSpool!,
       worker_id: state.selectedWorker!.id,
       worker_nombre,
     };
     await pausarOcupacion(payload); // PAUSAR not CANCELAR (semantic change)
   }
   ```

   **Step 9c: Update batch handler (lines ~46-65):**
   ```typescript
   // ❌ BEFORE (v2.1)
   const batchPayload: BatchActionRequest = {
     worker_id: state.selectedWorker!.id,
     operacion: state.selectedOperation as 'ARM' | 'SOLD',
     tag_spools: state.selectedSpools,
     ...(tipo === 'completar' && { timestamp: new Date().toISOString() }),
   };

   if (tipo === 'iniciar') {
     batchResponse = await iniciarAccionBatch(batchPayload);
   } else if (tipo === 'completar') {
     batchResponse = await completarAccionBatch(batchPayload);
   } else {
     batchResponse = await cancelarAccionBatch(batchPayload);
   }

   // ✅ AFTER (v3.0)
   const worker_nombre = state.selectedWorker!.nombre_completo;

   if (tipo === 'iniciar') {
     const batchPayload: BatchTomarRequest = {
       tag_spools: state.selectedSpools,
       worker_id: state.selectedWorker!.id,
       worker_nombre,
       operacion: state.selectedOperation as 'ARM' | 'SOLD' | 'METROLOGIA' | 'REPARACION',
     };
     batchResponse = await tomarOcupacionBatch(batchPayload);
   } else if (tipo === 'completar') {
     // Note: Batch COMPLETAR requires iterating to call completarOcupacion() individually
     // because each spool needs its own fecha_operacion
     const fecha_operacion = new Date().toISOString().split('T')[0];
     const results = await Promise.allSettled(
       state.selectedSpools.map(tag_spool =>
         completarOcupacion({
           tag_spool,
           worker_id: state.selectedWorker!.id,
           worker_nombre,
           fecha_operacion,
         })
       )
     );
     // Map Promise.allSettled results to BatchOccupationResponse format
     batchResponse = {
       total: results.length,
       succeeded: results.filter(r => r.status === 'fulfilled').length,
       failed: results.filter(r => r.status === 'rejected').length,
       details: results.map((r, i) => ({
         success: r.status === 'fulfilled',
         tag_spool: state.selectedSpools[i],
         message: r.status === 'fulfilled' ? r.value.message : (r.reason?.message || 'Error desconocido'),
       })),
     };
   } else {
     // tipo === 'cancelar' → Use PAUSAR batch
     const batchPayload = {
       tag_spools: state.selectedSpools,
       worker_id: state.selectedWorker!.id,
       worker_nombre,
     };
     // Note: Backend might not have batch PAUSAR - call individually
     const results = await Promise.allSettled(
       state.selectedSpools.map(tag_spool =>
         pausarOcupacion({
           tag_spool,
           worker_id: state.selectedWorker!.id,
           worker_nombre,
         })
       )
     );
     batchResponse = {
       total: results.length,
       succeeded: results.filter(r => r.status === 'fulfilled').length,
       failed: results.filter(r => r.status === 'rejected').length,
       details: results.map((r, i) => ({
         success: r.status === 'fulfilled',
         tag_spool: state.selectedSpools[i],
         message: r.status === 'fulfilled' ? r.value.message : (r.reason?.message || 'Error desconocido'),
       })),
     };
   }
   ```

   **Step 9d: Update error handling (lines ~98-120):**
   ```typescript
   // Add v3.0-specific error handling
   catch (err) {
     const errorMessage = err instanceof Error ? err.message : 'Error al procesar acción';

     // v3.0 specific errors
     if (errorMessage.includes('ocupado') || errorMessage.includes('409')) {
       setError('Este spool está siendo usado por otro trabajador. Intenta más tarde.');
       setErrorType('forbidden');
     } else if (errorMessage.includes('expiró') || errorMessage.includes('410')) {
       setError('La operación tardó demasiado. Por favor vuelve a intentar.');
       setErrorType('validation');
     } else if (errorMessage.includes('404')) {
       setError('Spool o trabajador no encontrado.');
       setErrorType('not-found');
     } else {
       setError(errorMessage);
       setErrorType('generic');
     }

     setLoading(false);
   }
   ```

10. **Verify Worker.nombre_completo is available:**
    Check `lib/context.tsx` to ensure `selectedWorker` has `nombre_completo` field:
    ```typescript
    // In context, Worker type should have:
    interface Worker {
      id: number;
      nombre: string;
      apellido?: string;
      nombre_completo: string; // ← REQUIRED for v3.0 (format: "INICIALES(ID)")
      activo: boolean;
    }
    ```
    If missing, this field comes from backend `GET /api/workers` response.

11. **Handle batch partial failures in UI:**
    ```typescript
    // In confirmar/page.tsx, after batch response:
    if (batchResponse.failed > 0 && batchResponse.succeeded > 0) {
      // Partial success scenario
      setState({
        batchResults: {
          ...batchResponse,
          partialSuccess: true,
          successMessage: `${batchResponse.succeeded} de ${batchResponse.total} spools procesados exitosamente.`,
        },
      });
    }
    ```

**Phase 5: Deprecation Strategy**

12. **Mark v2.1 functions as deprecated (DO NOT DELETE yet):**
    - Add `@deprecated` JSDoc comments to v2.1 functions
    - Add console.warn() in v2.1 functions: "⚠️ This function uses legacy v2.1 endpoint. Migrate to v3.0 occupation endpoints."
    - Keep v2.1 functions for backward compatibility during transition
    - Example:
      ```typescript
      /**
       * @deprecated Use tomarOcupacion() instead (v3.0 endpoint with Redis locks)
       */
      export async function iniciarAccion(payload: ActionPayload): Promise<ActionResponse> {
        console.warn('⚠️ iniciarAccion() is deprecated. Migrate to tomarOcupacion() for v3.0 features.');
        // ... existing implementation
      }
      ```

11. **READ-ONLY endpoints remain unchanged:**
    - `GET /api/workers` - Keep as-is
    - `GET /api/spools/iniciar` - Keep as-is
    - `GET /api/spools/completar` - Keep as-is
    - `GET /api/spools/cancelar` - Keep as-is (used for listing, not canceling)
    - `GET /api/health` - Keep as-is

    These work perfectly with v3.0 and don't need changes.

**Phase 6: Semantic Clarification (PAUSAR vs CANCELAR)**

13. **Understand workflow differences:**

    **v2.1 CANCELAR:**
    - Endpoint: `POST /api/cancelar-accion`
    - Effect: Reverts state 0.1 → 0 (back to PENDIENTE)
    - Use case: Worker started by mistake, wants to undo completely
    - Columns cleared: Armador/Soldador, Fecha_Armado/Soldadura

    **v3.0 PAUSAR:**
    - Endpoint: `POST /api/occupation/pausar`
    - Effect: Marks as "ARM parcial (pausado)" or "SOLD parcial (pausado)"
    - Use case: Worker needs to pause work temporarily (e.g., break, shift end)
    - Columns updated: Estado_Detalle = "parcial (pausado)", Ocupado_Por/Fecha_Ocupacion cleared

    **Migration decision:**
    - If frontend has "Cancelar" button → Map to v3.0 PAUSAR (semantically closer)
    - If need true cancellation (revert to PENDIENTE) → Keep using v2.1 CANCELAR endpoint
    - **RECOMMENDATION:** Use PAUSAR for v3.0, but keep CANCELAR available for true revert scenarios
</requirements>

<implementation>
**Approach:**

1. **Read backend specifications first (CRITICAL - avoid schema mismatches):**
   - Examine `routers/occupation.py` for exact endpoint signatures and error handling
   - Examine `models/occupation.py` for request/response Pydantic models
   - Examine `models/enums.py` to verify valid ActionType values
   - **DO NOT assume fields exist** - verify every field in backend models before adding to TypeScript interfaces
   - This ensures API client matches backend exactly and prevents runtime errors

2. **Implement incrementally:**
   - Start with single-spool functions (tomar, pausar, completar)
   - Test each function before moving to batch operations
   - Add comprehensive error handling for v3.0 codes

3. **TypeScript best practices:**
   - Explicit return types for all functions
   - Use union types for operation: `'ARM' | 'SOLD' | 'METROLOGIA' | 'REPARACION'`
   - Optional chaining (`?.`) for nested properties
   - Nullish coalescing (`??`) for default values

4. **Error handling pattern:**
   ```typescript
   // Handle v3.0-specific errors before generic handleResponse
   if (res.status === 409) {
     const errorData = await res.json();
     if (errorData.error === 'VERSION_CONFLICT') {
       throw new Error('Conflicto de versión. Otro trabajador modificó este spool. Recarga la página.');
     }
     throw new Error(errorData.message || 'Spool ocupado por otro trabajador.');
   }

   if (res.status === 410) {
     const errorData = await res.json();
     throw new Error(errorData.message || 'La operación expiró. Por favor intenta nuevamente.');
   }

   return await handleResponse<OccupationResponse>(res);
   ```

5. **What to avoid and WHY:**
   - ❌ DO NOT delete v2.1 functions yet → WHY: Allows gradual migration and easy rollback if issues arise
   - ❌ DO NOT use `any` type → WHY: ESLint rule `@typescript-eslint/no-explicit-any` will fail build
   - ❌ DO NOT hardcode API_URL → WHY: Must work in local dev and production via env var
   - ❌ DO NOT skip error handling for 409/410 → WHY: v3.0 introduces new failure modes that users need feedback on
</implementation>

<output>
**Files to create/modify (relative to working directory `/backend`):**

1. `../zeues-frontend/lib/api.ts`
   - Add new v3.0 functions: `tomarOcupacion`, `pausarOcupacion`, `completarOcupacion`, `tomarOcupacionBatch`
   - Mark v2.1 functions as `@deprecated` with console warnings
   - Add v3.0 error handling for 409 CONFLICT, 410 GONE
   - Include `worker_nombre` in all v3.0 payloads (get from Worker.nombre_completo)
   - Include `fecha_operacion` in completar payload (use `new Date().toISOString().split('T')[0]`)

2. `../zeues-frontend/lib/types.ts`
   - Add interfaces: `TomarRequest`, `PausarRequest`, `CompletarRequest`, `BatchTomarRequest`
   - Add interfaces: `OccupationResponse`, `BatchOccupationResponse`
   - Verify operation union type includes all 4 values from backend enum: `'ARM' | 'SOLD' | 'METROLOGIA' | 'REPARACION'`

3. `../MIGRATION-V3.md` (create new file at project root)
   - Document migration steps for developers
   - List components that need updating (from grep search results)
   - Provide v2.1 → v3.0 API mapping table with payload differences
   - Clarify PAUSAR vs CANCELAR semantic differences
   - Include testing checklist
   - Include batch partial failure handling examples
</output>

<verification>
Before declaring complete, verify your work:

1. **TypeScript compilation:**
   ```bash
   cd ../zeues-frontend
   npx tsc --noEmit
   ```
   Must pass with ZERO errors.

2. **ESLint check:**
   ```bash
   cd ../zeues-frontend
   npm run lint
   ```
   Must pass with no `@typescript-eslint/no-explicit-any` violations.

3. **API function signatures match backend exactly:**
   ```bash
   # Verify interfaces match Pydantic models
   cd backend
   grep -A 20 "class TomarRequest" models/occupation.py
   grep -A 20 "class OccupationResponse" models/occupation.py
   grep -A 20 "class BatchOccupationResponse" models/occupation.py
   ```
   - Compare each field name and type
   - Verify REQUIRED vs OPTIONAL fields match
   - Ensure no extra fields that backend doesn't return

4. **Error handling coverage:**
   - Confirm 409 CONFLICT handled with user-friendly message
   - Confirm 410 GONE handled with retry suggestion
   - Confirm SpoolOccupiedError displays different message than generic 409

5. **Backward compatibility:**
   - v2.1 functions still callable (even if deprecated)
   - No breaking changes to existing function signatures
   - Console warnings appear when calling deprecated functions

6. **Component search verification:**
   ```bash
   cd ../zeues-frontend
   # Verify NO MORE v2.1 usage in components (should only find deprecated definitions in api.ts)
   grep -r "iniciarAccion\(" app/ --include="*.tsx"
   grep -r "completarAccion\(" app/ --include="*.tsx"
   grep -r "cancelarAccion\(" app/ --include="*.tsx"
   ```
   Expected: NO results (or only comments/deprecated warnings)
   If any results found → migration incomplete

7. **Manual verification in Google Sheets:**
   After running the app:
   - TOMAR a spool TEST-01
   - Open Google Sheets Operaciones tab
   - Verify columns updated:
     - ✅ `Ocupado_Por` = "MR(93)" (worker nombre_completo)
     - ✅ `Fecha_Ocupacion` = today's date
     - ✅ `Version` = 1 (incremented)
     - ✅ `Estado_Detalle` = "ARM en progreso" (or similar)
   - If any column is empty/null → v3.0 endpoint NOT being called
</verification>

<success_criteria>
- [ ] All v3.0 API functions implemented in `lib/api.ts` (tomarOcupacion, pausarOcupacion, completarOcupacion, batch)
- [ ] All v3.0 TypeScript interfaces added to `lib/types.ts` (TomarRequest, CompletarRequest, PausarRequest, etc.)
- [ ] `app/confirmar/page.tsx` imports updated to use v3.0 functions
- [ ] `app/confirmar/page.tsx` single spool handler migrated to v3.0 payloads (includes worker_nombre)
- [ ] `app/confirmar/page.tsx` batch handler migrated to v3.0 payloads
- [ ] `timestamp` replaced with `fecha_operacion` in YYYY-MM-DD format
- [ ] Worker.nombre_completo field verified in context (required for v3.0)
- [ ] v2.1 functions marked as deprecated but still functional
- [ ] v3.0 error codes (409, 410) handled with user-friendly messages
- [ ] TypeScript compilation passes (`npx tsc --noEmit`)
- [ ] ESLint passes with no `any` type violations
- [ ] Migration documentation created in `MIGRATION-V3.md`
- [ ] Payload/response types match backend Pydantic models exactly
- [ ] No more calls to `/api/iniciar-accion` endpoint (verify with grep)
</success_criteria>

<testing_guidance>
**CRITICAL:** The PRIMARY goal is to verify that clicking "Iniciar" in the UI now calls `/api/occupation/tomar` (v3.0) instead of `/api/iniciar-accion` (v2.1), and that ALL occupation columns are updated.

After implementation, test manually:

1. **Test END-TO-END UI flow (SOLVES ORIGINAL PROBLEM):**
   - Open frontend: http://localhost:3000
   - Select worker "Mauricio Rodriguez" (id: 93)
   - Select operation "ARM"
   - Select action type "INICIAR"
   - Select spool "TEST-01"
   - Click "Confirmar"
   - **Open browser DevTools Network tab:**
     - ✅ VERIFY request goes to `POST /api/occupation/tomar` (NOT `/api/iniciar-accion`)
     - ✅ VERIFY request body includes `worker_nombre: "MR(93)"`
   - **Open Google Sheets Operaciones tab:**
     - ✅ VERIFY `Ocupado_Por` column = "MR(93)" (NOT empty)
     - ✅ VERIFY `Fecha_Ocupacion` column = today's date (NOT empty)
     - ✅ VERIFY `Version` column = 1 (NOT empty)
     - ✅ VERIFY `Estado_Detalle` column = "ARM en progreso" (NOT empty)
   - **If ANY column is empty:** v2.1 endpoint is still being called → migration failed

2. **Test 409 CONFLICT:**
   - Worker A calls `tomarOcupacion()` for spool TEST-01
   - Worker B calls `tomarOcupacion()` for same spool TEST-01 (should fail immediately)
   - Verify Worker B gets 409 error with message: "Spool ocupado por otro trabajador"

3. **Test COMPLETAR with required fecha_operacion:**
   - Call `completarOcupacion()` with:
     ```json
     {
       "tag_spool": "TEST-01",
       "worker_id": 93,
       "worker_nombre": "MR(93)",
       "fecha_operacion": "2026-01-28"
     }
     ```
   - Verify success response
   - Check Sheets: Fecha_Armado updated, Ocupado_Por cleared

4. **Test batch operations with partial failures:**
   - Call `tomarOcupacionBatch()` with 5 spools (some PENDIENTE, some already occupied)
   - Verify response structure:
     ```json
     {
       "total": 5,
       "succeeded": 3,
       "failed": 2,
       "details": [
         {"success": true, "tag_spool": "...", "message": "..."},
         {"success": false, "tag_spool": "...", "message": "Spool ocupado..."}
       ]
     }
     ```
   - Verify frontend shows partial success message: "3 de 5 spools tomados"

5. **Test v2.1 deprecation warnings:**
   - Call deprecated `iniciarAccion()` function
   - Open browser console
   - Verify console.warn() appears: "⚠️ iniciarAccion() is deprecated..."

6. **Test PAUSAR vs CANCELAR semantics:**
   - PAUSAR: Verify Estado_Detalle = "ARM parcial (pausado)", spool NOT back to PENDIENTE
   - CANCELAR (v2.1): Verify state reverts to 0 (PENDIENTE), Armador cleared

7. **E2E Testing with Playwright (if tests exist):**
   ```bash
   cd ../zeues-frontend
   npx playwright test tests/e2e/iniciar-flow.spec.ts --headed
   ```
   - Update test to verify network request goes to `/api/occupation/tomar`
   - Update test to check Google Sheets columns are populated
   - Add test for 409 CONFLICT scenario (two workers, same spool)
</testing_guidance>
