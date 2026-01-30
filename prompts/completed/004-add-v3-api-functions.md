<objective>
Add v3.0 API integration functions for TOMAR/PAUSAR/COMPLETAR/CANCELAR operations to support the new occupation tracking workflow.

This is a critical dependency for the frontend v3.0 migration. The API functions will be used by P5 (confirmar page) to call the new backend endpoints for occupation tracking with Redis locks, replacing the legacy v2.1 INICIAR/COMPLETAR workflow.
</objective>

<context>
**Current State:**
- File: `zeues-frontend/lib/api.ts`
- Currently has v2.1 functions: `iniciarAccion()`, `completarAccion()`, `cancelarAccion()`
- P3 (tipo-interaccion) has been updated to use new action types: 'tomar', 'pausar', 'completar', 'cancelar'

**v3.0 Backend Endpoints (from backend analysis):**
- POST `/api/occupation/tomar` - Acquire Redis lock, mark spool as OCUPADO
- POST `/api/occupation/pausar` - Release lock without completing, preserves progress
- POST `/api/occupation/completar` - Finish work, release lock, write fecha_armado/soldadura
- POST `/api/reparacion/tomar-reparacion` - Take rejected spool for repair
- POST `/api/reparacion/pausar-reparacion` - Pause repair work
- POST `/api/reparacion/completar-reparacion` - Complete repair (returns to metrología queue)
- POST `/api/reparacion/cancelar-reparacion` - Cancel repair (returns to RECHAZADO)

**Request/Response Models (from backend occupation.py):**
```python
# TOMAR
class TomarRequest(BaseModel):
    tag_spool: str
    worker_id: int
    operacion: ActionType  # ARM, SOLD, REPARACION

# PAUSAR
class PausarRequest(BaseModel):
    tag_spool: str
    worker_id: int
    operacion: ActionType

# COMPLETAR
class CompletarRequest(BaseModel):
    tag_spool: str
    worker_id: int
    operacion: ActionType

# Response
class OccupationResponse(BaseModel):
    success: bool
    tag_spool: str
    message: str
```

Read @zeues-frontend/lib/api.ts for current implementation patterns.
Read @CLAUDE.md for project conventions and TypeScript rules.
</context>

<requirements>
**Functional Requirements:**

1. **Add New API Functions:**
   - `tomarSpool(tagSpool: string, workerId: number, operacion: string): Promise<OccupationResponse>`
   - `pausarSpool(tagSpool: string, workerId: number, operacion: string): Promise<OccupationResponse>`
   - `completarSpool(tagSpool: string, workerId: number, operacion: string): Promise<OccupationResponse>`
   - `tomarReparacion(tagSpool: string, workerId: number): Promise<OccupationResponse>`
   - `pausarReparacion(tagSpool: string, workerId: number): Promise<OccupationResponse>`
   - `completarReparacion(tagSpool: string, workerId: number): Promise<OccupationResponse>`
   - `cancelarReparacion(tagSpool: string, workerId: number): Promise<OccupationResponse>`

2. **TypeScript Interface Definitions:**
   ```typescript
   interface OccupationRequest {
     tag_spool: string;
     worker_id: number;
     operacion: string;  // 'ARM', 'SOLD', 'REPARACION'
   }

   interface OccupationResponse {
     success: boolean;
     tag_spool: string;
     message: string;
   }
   ```

3. **Error Handling:**
   - 409 Conflict: Spool already occupied (SpoolOccupiedError)
   - 404 Not Found: Spool doesn't exist (SpoolNoEncontradoError)
   - 403 Forbidden: Not authorized or lock expired (NoAutorizadoError, LockExpiredError)
   - 400 Bad Request: Validation failed (DependenciasNoSatisfechasError)
   - Throw descriptive errors that UI can display to users

4. **HTTP Method and Headers:**
   - All endpoints: POST method
   - Content-Type: `application/json`
   - Use native fetch (NO axios - project standard)
   - Base URL from env: `process.env.NEXT_PUBLIC_API_URL`

5. **TypeScript Type Safety:**
   - NO `any` types (ESLint will fail)
   - Proper interface definitions for all request/response types
   - Type-safe function signatures

**Non-Functional Requirements:**
- Must pass: `npx tsc --noEmit` (TypeScript validation)
- Must pass: `npm run lint` (ESLint validation)
- Follow existing API function patterns in api.ts (consistency)
- Clear error messages for all HTTP status codes
</requirements>

<implementation>
**Step-by-step approach:**

1. **Add TypeScript interfaces at the top of api.ts:**
   ```typescript
   interface OccupationRequest {
     tag_spool: string;
     worker_id: number;
     operacion: string;
   }

   interface ReparacionRequest {
     tag_spool: string;
     worker_id: number;
   }

   interface OccupationResponse {
     success: boolean;
     tag_spool: string;
     message: string;
   }
   ```

2. **Implement tomarSpool function:**
   ```typescript
   export async function tomarSpool(
     tagSpool: string,
     workerId: number,
     operacion: string
   ): Promise<OccupationResponse> {
     const response = await fetch(`${API_URL}/api/occupation/tomar`, {
       method: 'POST',
       headers: { 'Content-Type': 'application/json' },
       body: JSON.stringify({
         tag_spool: tagSpool,
         worker_id: workerId,
         operacion: operacion
       })
     });

     if (!response.ok) {
       const error = await response.text();
       throw new Error(`Error ${response.status}: ${error}`);
     }

     return response.json();
   }
   ```

3. **Implement pausarSpool and completarSpool following the same pattern**

4. **Implement reparación functions (tomarReparacion, pausarReparacion, completarReparacion, cancelarReparacion):**
   - Use `/api/reparacion/tomar-reparacion` endpoint
   - Request only needs tag_spool and worker_id (no operacion field)

5. **Keep existing v2.1 functions for backward compatibility:**
   - Don't remove `iniciarAccion()`, `completarAccion()`, `cancelarAccion()`
   - These may still be used by other parts of the system

**What to avoid and WHY:**
- ❌ Don't use axios - Project uses native fetch for consistency and smaller bundle size
- ❌ Don't use `any` types - TypeScript strict mode is enforced for type safety
- ❌ Don't remove v2.1 functions - Backend still supports legacy endpoints, other pages may use them
- ❌ Don't add complex retry logic - Backend handles retry with optimistic locking, keep client simple
- ❌ Don't swallow errors - P5 (confirmar) needs detailed error messages to show users what went wrong
</implementation>

<output>
Modify the existing file:
- `./zeues-frontend/lib/api.ts` - Add 7 new API functions and TypeScript interfaces

DO NOT modify:
- Other pages (P4, P5) - those will be updated in subsequent prompts to use these functions
- Context or types files - OccupationResponse is local to api.ts
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

3. **Function signature verification:**
   - tomarSpool(tagSpool, workerId, operacion) → POST /api/occupation/tomar
   - pausarSpool(tagSpool, workerId, operacion) → POST /api/occupation/pausar
   - completarSpool(tagSpool, workerId, operacion) → POST /api/occupation/completar
   - tomarReparacion(tagSpool, workerId) → POST /api/reparacion/tomar-reparacion
   - pausarReparacion(tagSpool, workerId) → POST /api/reparacion/pausar-reparacion
   - completarReparacion(tagSpool, workerId) → POST /api/reparacion/completar-reparacion
   - cancelarReparacion(tagSpool, workerId) → POST /api/reparacion/cancelar-reparacion

4. **Error handling verification:**
   - Check that all fetch calls have proper error handling
   - Verify HTTP status codes are checked (!response.ok)
   - Confirm error messages are descriptive

5. **Type safety verification:**
   - All functions have explicit return type: Promise<OccupationResponse>
   - No `any` types used
   - Interfaces properly defined
</verification>

<success_criteria>
- ✓ 7 new API functions added (tomar, pausar, completar for general + 4 for reparación)
- ✓ TypeScript interfaces defined for request/response types
- ✓ All functions use native fetch (no axios)
- ✓ Proper error handling for all HTTP status codes
- ✓ TypeScript compilation passes (`npx tsc --noEmit`)
- ✓ ESLint passes with no warnings (`npm run lint`)
- ✓ No `any` types used
- ✓ Existing v2.1 functions preserved for backward compatibility
- ✓ Follows existing api.ts patterns for consistency
</success_criteria>

<notes>
**Why this matters:**
- This is a critical dependency - P5 (confirmar) cannot be updated until these functions exist
- v3.0 workflow relies on occupation tracking with Redis locks (TOMAR/PAUSAR/COMPLETAR)
- Clear error handling enables better UX when workers encounter conflicts (spool already occupied)
- Type safety prevents runtime errors from API contract mismatches

**Known dependencies:**
- P5 (confirmar/page.tsx) will consume these functions in the next prompt
- Backend endpoints already exist and are tested (occupation_service.py, reparacion_service.py)
</notes>
