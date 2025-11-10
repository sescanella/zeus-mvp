# ZEUES Frontend - Plan de Implementación DÍA 4: Integración API

**Sistema de Trazabilidad para Manufactura - Integración Frontend con Backend FastAPI**

Fecha de creación: 11 Nov 2025
Última actualización: 11 Nov 2025 - 01:15
Estado: EN PROGRESO - DÍA 4 - FASES 1-2 ✅ COMPLETADAS
Responsable: @api-integrator (frontend)

---

## 1. Contexto y Objetivos

### Estado Actual (DÍA 1-3 COMPLETADO)

**Frontend Implementado (100%):**
- ✅ 7 páginas completas con mock data (P1-P6)
- ✅ 5 componentes base funcionando (Button, Card, List, Loading, ErrorMessage)
- ✅ Context API implementado (estado global)
- ✅ Navegación completa P1→P2→P3→P4→P5→P6→P1
- ✅ Filtrado inteligente de spools en mock data (iniciar vs completar, ARM vs SOLD)
- ✅ Validación de propiedad (ownership) en mock data
- ✅ Build producción exitoso sin errores TypeScript/ESLint

**Backend Disponible (100%):**
- ✅ 6 endpoints API funcionando en `http://localhost:8000`
- ✅ 10/10 tests E2E passing (100% success rate)
- ✅ Ownership validation implementada y testeada
- ✅ OpenAPI docs en `/api/docs`
- ✅ Exception handling completo (ZEUSException → HTTP codes)

**FASE 1 COMPLETADA (10 Nov 2025 - 23:45):**
- ✅ API client (`/lib/api.ts`) creado con 6 funciones fetch (226 líneas)
- ✅ Interface `ActionResponse` agregada a `/lib/types.ts` (+14 líneas)
- ✅ Build producción exitoso sin errores TypeScript/ESLint
- ✅ URL encoding implementado para nombres con tildes
- ✅ Manejo especial 403 para ownership validation

**FASE 2 COMPLETADA (11 Nov 2025 - 01:15):**
- ✅ `app/page.tsx` integrado con API real
- ✅ Import `getWorkers` y `Worker` type agregados
- ✅ `MOCK_WORKERS` array eliminado completamente (6 líneas)
- ✅ Interface `Worker` local duplicada eliminada (6 líneas)
- ✅ `fetchWorkers()` reemplazado con API call real
- ✅ Error handling mejorado con `instanceof Error`
- ✅ TypeScript: `npx tsc --noEmit` - Sin errores
- ✅ ESLint: `npm run lint` - Sin warnings
- ✅ Build producción exitoso (9 páginas generadas)
- ✅ Cambio neto: -12 líneas (código más simple)

**Pendiente (Próximas Fases):**
- ⏳ FASE 3: Reemplazar mock data con API en P4 - Seleccionar Spool
- ⏳ FASE 4: Conectar P5 con POST requests (iniciar/completar acción)
- ⏳ FASE 5: Testing manual de integración completa

### Objetivo DÍA 4

Conectar el frontend Next.js (actualmente con mock data) al backend FastAPI usando fetch nativo, reemplazando los datos simulados con llamadas API reales y validando la integración completa de los flujos INICIAR→COMPLETAR.

**Tiempo Estimado:** 6-7 horas (1 día completo de trabajo)

---

## 2. Arquitectura de Integración

### Diagrama de Flujo (Frontend → Backend)

```
Frontend Next.js (Vercel)
    ├── Páginas (app/)
    │   ├── P1: Identificación (page.tsx)
    │   │   └── getWorkers() → GET /api/workers
    │   │
    │   ├── P4: Seleccionar Spool (seleccionar-spool/page.tsx)
    │   │   ├── getSpoolsParaIniciar() → GET /api/spools/iniciar?operacion={ARM|SOLD}
    │   │   └── getSpoolsParaCompletar() → GET /api/spools/completar?operacion={ARM|SOLD}&worker_nombre={nombre}
    │   │
    │   └── P5: Confirmar Acción (confirmar/page.tsx)
    │       ├── iniciarAccion() → POST /api/iniciar-accion
    │       └── completarAccion() → POST /api/completar-accion (ownership validation)
    │
    ├── API Client (/lib/api.ts)
    │   ├── Helper: handleResponse<T>() - DRY error handling
    │   ├── 6 funciones fetch (native fetch, NO axios)
    │   └── URL encoding para worker_nombre
    │
    ├── Types (/lib/types.ts)
    │   ├── Worker, Spool, ActionPayload (existentes)
    │   └── ActionResponse (nueva - DÍA 4)
    │
    └── Context (/lib/context.tsx)
        └── Estado global: selectedWorker, selectedOperation, selectedTipo, selectedSpool

                    ↓ HTTPS (fetch nativo)

Backend FastAPI (Railway/Localhost:8000)
    ├── GET  /api/workers
    ├── GET  /api/spools/iniciar?operacion={ARM|SOLD}
    ├── GET  /api/spools/completar?operacion={ARM|SOLD}&worker_nombre={nombre}
    ├── POST /api/iniciar-accion
    ├── POST /api/completar-accion (403 si ownership violation)
    └── GET  /api/health

                    ↓ gspread

Google Sheets (Fuente de Verdad)
```

### Estrategia de Integración

**Patrón:** Native fetch con try/catch básico (NO axios, NO complex libraries)

**Razón:**
- Simplicidad MVP: fetch es built-in, cero dependencias
- Type safety: TypeScript interfaces para requests/responses
- Error handling: Mapeo HTTP codes → mensajes user-friendly en español
- URL encoding: `encodeURIComponent()` para nombres con espacios/tildes

---

## 3. Orden de Implementación (5 Fases Justificadas)

### ✅ FASE 1: Crear API Client Base (COMPLETADA - 10 Nov 2025)
**Archivos:** `lib/api.ts` (226 líneas), `lib/types.ts` (+14 líneas)

**Justificación:**
1. API client es la base - sin él, no se pueden hacer requests
2. Helper function `handleResponse<T>` evita duplicación de código
3. Tipos TypeScript deben existir antes de usar las funciones
4. Variable `NEXT_PUBLIC_API_URL` debe configurarse

**Orden interno FASE 1:**
1. Actualizar `/lib/types.ts` con `ActionResponse` interface
2. Crear `/lib/api.ts` con helper `handleResponse<T>`
3. Implementar 6 funciones fetch en orden de complejidad:
   - `getWorkers()` (más simple - sin params)
   - `getSpoolsParaIniciar()` (query param operacion)
   - `getSpoolsParaCompletar()` (query params operacion + worker_nombre con URL encoding)
   - `checkHealth()` (sin params, para testing)
   - `iniciarAccion()` (POST con payload)
   - `completarAccion()` (POST con payload + manejo especial 403)

---

### ✅ FASE 2: Integrar P1 - Identificación (COMPLETADA - 11 Nov 2025)
**Archivos:** `app/page.tsx` (modificado - 71 líneas finales)
**Bloqueadores:** Ninguno - COMPLETADO

**Justificación:**
1. Endpoint más simple (GET sin params)
2. Valida que API client funciona antes de endpoints complejos
3. No hay lógica condicional (solo mostrar lista)
4. Estados loading/error ya implementados

---

### ⏳ FASE 3: Integrar P4 - Seleccionar Spool (PENDIENTE - PRÓXIMA)
**Archivos:** `app/seleccionar-spool/page.tsx` (modificar)
**Bloqueadores:** ✅ FASES 1-2 completadas - LISTO PARA IMPLEMENTAR

**Justificación:**
1. Usa query params condicionales (tipo=iniciar|completar)
2. Dos endpoints diferentes según flujo
3. Lógica condicional según operación (ARM vs SOLD)
4. Filtrado ahora en backend (eliminar `getFilteredSpools()`)

---

### ⏳ FASE 4: Integrar P5 - Confirmar Acción (PENDIENTE - CRÍTICO)
**Archivos:** `app/confirmar/page.tsx` (modificar)
**Bloqueadores:** ✅ FASES 1-2 completadas - LISTO PARA IMPLEMENTAR

**Justificación:**
1. POST endpoints son más críticos (modifican estado)
2. Payload construction con tipos correctos
3. **Ownership validation (403 error) debe funcionar**
4. Timestamp opcional en COMPLETAR
5. Loading message específico ("Actualizando Google Sheets...")

**Este es el archivo MÁS CRÍTICO del DÍA 4 - Requiere mayor atención.**

---

### ⏳ FASE 5: Testing y Validación Final (PENDIENTE)
**Método:** Testing manual en navegador
**Bloqueadores:** ⏳ FASE 2-4 deben completarse primero

**Justificación:**
1. Solo se puede validar integración cuando todos los endpoints están conectados
2. Valida flujos completos INICIAR→COMPLETAR (uso real)
3. Detecta problemas de integración (CORS, tipos, URL encoding)
4. Prueba ownership validation en contexto real (intento de completar con otro trabajador)

---

## 4. Especificación Detallada por Archivo

---

### 4.1 lib/types.ts (Actualizar)

**Propósito:** Agregar interface `ActionResponse` para respuestas de iniciar/completar acción.

**Cambios necesarios:**

**Agregar después de `ActionPayload` (línea 28):**

```typescript
// Agregar esta interface NUEVA
export interface ActionResponse {
  success: boolean;
  message: string;
  data: {
    tag_spool: string;
    operacion: string;
    trabajador: string;
    fila_actualizada: number;
    columna_actualizada: string;
    valor_nuevo: number;
    metadata_actualizada: Record<string, any>;
  };
}
```

**Líneas agregadas:** +17 (28 → 45 líneas totales)

**Resultado esperado:**
- Archivo pasa TypeScript compiler sin errores
- `ActionResponse` disponible para import en `api.ts`

---

### 4.2 lib/api.ts (Crear desde cero)

**Propósito:** Cliente HTTP con fetch nativo para conectar con backend FastAPI.

**Líneas esperadas:** ~280 líneas (vs 16 actuales)

**Estructura completa:**

```typescript
// /Users/sescanella/Proyectos/ZEUES-by-KM/zeues-frontend/lib/api.ts

// ============= IMPORTS =============
import { Worker, Spool, ActionPayload, ActionResponse } from './types';

// ============= CONSTANTS =============
const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

// ============= HELPER FUNCTIONS =============

/**
 * Helper para manejar respuestas HTTP de forma consistente.
 * Lanza error si response.ok === false.
 */
async function handleResponse<T>(response: Response): Promise<T> {
  if (!response.ok) {
    const errorData = await response.json().catch(() => ({}));
    const message = errorData.message || `Error ${response.status}: ${response.statusText}`;
    throw new Error(message);
  }
  return response.json();
}

// ============= API FUNCTIONS =============

/**
 * GET /api/workers
 * Obtiene lista de trabajadores activos.
 *
 * @returns Promise<Worker[]> - Array de trabajadores activos
 * @throws Error si falla la request o backend no disponible
 *
 * @example
 * const workers = await getWorkers();
 * console.log(workers); // [{nombre: "Juan", apellido: "Pérez", activo: true, nombre_completo: "Juan Pérez"}]
 */
export async function getWorkers(): Promise<Worker[]> {
  try {
    const res = await fetch(`${API_URL}/api/workers`, {
      method: 'GET',
      headers: { 'Content-Type': 'application/json' }
    });

    const data = await handleResponse<{ workers: Worker[], total: number }>(res);
    return data.workers;
  } catch (error) {
    console.error('getWorkers error:', error);
    throw new Error('No se pudieron cargar los trabajadores. Verifica tu conexión.');
  }
}

/**
 * GET /api/spools/iniciar?operacion={ARM|SOLD}
 * Obtiene spools disponibles para INICIAR (V/W=0, dependencias OK).
 *
 * @param operacion - Tipo de operación ("ARM" o "SOLD")
 * @returns Promise<Spool[]> - Array de spools elegibles para iniciar
 * @throws Error si operación inválida o falla request
 *
 * @example
 * const spools = await getSpoolsParaIniciar('ARM');
 * console.log(spools); // [{tag_spool: "MK-123", arm: 0, sold: 0, ...}]
 */
export async function getSpoolsParaIniciar(operacion: 'ARM' | 'SOLD'): Promise<Spool[]> {
  try {
    const url = `${API_URL}/api/spools/iniciar?operacion=${operacion}`;
    const res = await fetch(url, {
      method: 'GET',
      headers: { 'Content-Type': 'application/json' }
    });

    const data = await handleResponse<{ spools: Spool[], total: number, filtro_aplicado: string }>(res);
    return data.spools;
  } catch (error) {
    console.error('getSpoolsParaIniciar error:', error);
    throw new Error(`No se pudieron cargar spools para iniciar ${operacion}.`);
  }
}

/**
 * GET /api/spools/completar?operacion={ARM|SOLD}&worker_nombre={nombre}
 * Obtiene spools del trabajador para COMPLETAR (V/W=0.1, filtro ownership).
 *
 * @param operacion - Tipo de operación ("ARM" o "SOLD")
 * @param workerNombre - Nombre completo del trabajador (será URL encoded)
 * @returns Promise<Spool[]> - Array de spools propios del trabajador
 * @throws Error si operación inválida o falla request
 *
 * @example
 * const spools = await getSpoolsParaCompletar('ARM', 'Juan Pérez');
 * console.log(spools); // [{tag_spool: "MK-123", arm: 0.1, armador: "Juan Pérez", ...}]
 */
export async function getSpoolsParaCompletar(
  operacion: 'ARM' | 'SOLD',
  workerNombre: string
): Promise<Spool[]> {
  try {
    // URL encode del nombre para manejar espacios y tildes
    const encodedWorker = encodeURIComponent(workerNombre);
    const url = `${API_URL}/api/spools/completar?operacion=${operacion}&worker_nombre=${encodedWorker}`;

    const res = await fetch(url, {
      method: 'GET',
      headers: { 'Content-Type': 'application/json' }
    });

    const data = await handleResponse<{ spools: Spool[], total: number, filtro_aplicado: string }>(res);
    return data.spools;
  } catch (error) {
    console.error('getSpoolsParaCompletar error:', error);
    throw new Error(`No se pudieron cargar tus spools de ${operacion}.`);
  }
}

/**
 * POST /api/iniciar-accion
 * Inicia una acción (marca V/W→0.1, guarda trabajador en BC/BE).
 *
 * @param payload - Datos de la acción (worker_nombre, operacion, tag_spool)
 * @returns Promise<ActionResponse> - Respuesta con detalles de la operación
 * @throws Error si trabajador/spool no encontrado, ya iniciada, o dependencias no satisfechas
 *
 * @example
 * const result = await iniciarAccion({
 *   worker_nombre: 'Juan Pérez',
 *   operacion: 'ARM',
 *   tag_spool: 'MK-1335-CW-25238-011'
 * });
 * console.log(result.message); // "Acción ARM iniciada exitosamente..."
 */
export async function iniciarAccion(payload: ActionPayload): Promise<ActionResponse> {
  try {
    const res = await fetch(`${API_URL}/api/iniciar-accion`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    });

    return await handleResponse<ActionResponse>(res);
  } catch (error) {
    console.error('iniciarAccion error:', error);
    // Re-throw para que el componente maneje el error
    throw error;
  }
}

/**
 * POST /api/completar-accion
 * Completa una acción (marca V/W→1.0, guarda fecha en BB/BD).
 *
 * CRÍTICO: Solo quien inició (BC/BE) puede completar. Si otro trabajador intenta,
 * backend retorna 403 FORBIDDEN y esta función lanza error con mensaje específico.
 *
 * @param payload - Datos de la acción (worker_nombre, operacion, tag_spool, timestamp?)
 * @returns Promise<ActionResponse> - Respuesta con detalles de la operación
 * @throws Error si no autorizado (403), no iniciada, trabajador/spool no encontrado
 *
 * @example
 * // Caso exitoso (mismo trabajador que inició)
 * const result = await completarAccion({
 *   worker_nombre: 'Juan Pérez',
 *   operacion: 'ARM',
 *   tag_spool: 'MK-1335-CW-25238-011'
 * });
 * console.log(result.message); // "Acción ARM completada exitosamente..."
 *
 * @example
 * // Caso error 403 (trabajador diferente)
 * try {
 *   await completarAccion({
 *     worker_nombre: 'María López', // Diferente al que inició
 *     operacion: 'ARM',
 *     tag_spool: 'MK-1335-CW-25238-011'
 *   });
 * } catch (error) {
 *   console.error(error.message); // "Solo Juan Pérez puede completar esta acción..."
 * }
 */
export async function completarAccion(payload: ActionPayload): Promise<ActionResponse> {
  try {
    const res = await fetch(`${API_URL}/api/completar-accion`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    });

    // Manejo especial para 403 FORBIDDEN (ownership validation)
    if (res.status === 403) {
      const errorData = await res.json();
      const message = errorData.message || 'No estás autorizado para completar esta acción. Solo quien la inició puede completarla.';
      throw new Error(message);
    }

    return await handleResponse<ActionResponse>(res);
  } catch (error) {
    console.error('completarAccion error:', error);
    // Re-throw para que el componente maneje el error
    throw error;
  }
}

/**
 * GET /api/health
 * Health check del backend y conectividad Google Sheets.
 *
 * @returns Promise<{status: string, sheets_connection: string}> - Estado del sistema
 * @throws Error si backend no disponible
 *
 * @example
 * const health = await checkHealth();
 * console.log(health); // {status: "healthy", sheets_connection: "ok", ...}
 */
export async function checkHealth(): Promise<{ status: string, sheets_connection: string }> {
  try {
    const res = await fetch(`${API_URL}/api/health`, {
      method: 'GET',
      headers: { 'Content-Type': 'application/json' }
    });

    return await handleResponse<{ status: string, sheets_connection: string }>(res);
  } catch (error) {
    console.error('checkHealth error:', error);
    throw new Error('No se pudo verificar el estado del sistema.');
  }
}
```

**Decisiones de Diseño:**

1. **Native fetch (NO axios/ky):**
   - Razón: Simplicidad MVP, built-in browser API, cero dependencias externas
   - Trade-off: Sin retry automático, sin interceptors (no necesarios en MVP)

2. **Helper function `handleResponse<T>`:**
   - Razón: DRY (Don't Repeat Yourself), manejo consistente de errores JSON
   - Simplifica código en cada función fetch

3. **URL encoding para `worker_nombre`:**
   - Razón: Nombres con espacios ("Juan Pérez") y tildes ("María García")
   - Usa `encodeURIComponent()` nativo: "Juan Pérez" → "Juan%20P%C3%A9rez"

4. **Error messages user-friendly:**
   - En español, claros y accionables
   - Evita exposición de detalles técnicos al usuario
   - `console.error()` para debugging (dev tools)

5. **Manejo especial 403 en `completarAccion`:**
   - Check status 403 ANTES de `handleResponse`
   - Mensaje personalizado ownership: "Solo quien inició puede completar..."
   - Re-throw para que componente maneje el error

**Testing Manual en Browser Console:**

```javascript
// 1. Test getWorkers()
const workers = await getWorkers();
console.log(workers);

// 2. Test getSpoolsParaIniciar()
const spools = await getSpoolsParaIniciar('ARM');
console.log(spools);

// 3. Test iniciarAccion()
const result = await iniciarAccion({
  worker_nombre: 'Juan Pérez',
  operacion: 'ARM',
  tag_spool: 'MK-1335-CW-25238-011'
});
console.log(result);

// 4. Test error 403 (ownership)
try {
  await completarAccion({
    worker_nombre: 'María López', // Diferente
    operacion: 'ARM',
    tag_spool: 'MK-1335-CW-25238-011'
  });
} catch (error) {
  console.error(error.message); // Debe mostrar mensaje ownership
}
```

---

### 4.3 app/page.tsx (Modificar)

**Propósito:** Integrar P1 - Identificación con API real.

**Líneas a modificar:** -9 líneas (eliminar mock) + imports

**Cambios específicos:**

**1. Línea 1 - Agregar import:**
```typescript
import { getWorkers } from '@/lib/api'; // NUEVO
```

**2. Líneas 9-14 - ELIMINAR MOCK_WORKERS:**
```typescript
// ELIMINAR estas líneas:
const MOCK_WORKERS = [
  { nombre: 'Juan', apellido: 'Pérez', nombre_completo: 'Juan Pérez', activo: true },
  { nombre: 'María', apellido: 'López', nombre_completo: 'María López', activo: true },
  { nombre: 'Carlos', apellido: 'Díaz', nombre_completo: 'Carlos Díaz', activo: true },
  { nombre: 'Ana', apellido: 'García', nombre_completo: 'Ana García', activo: true },
];
```

**3. Líneas 30-43 - Reemplazar `fetchWorkers()`:**
```typescript
// ANTES (simulación con mock data):
const fetchWorkers = async () => {
  try {
    setLoading(true);
    setError('');

    // Simular API call con delay de 500ms
    await new Promise(resolve => setTimeout(resolve, 500));

    setWorkers(MOCK_WORKERS);
  } catch {
    setError('Error al cargar trabajadores. Intenta nuevamente.');
  } finally {
    setLoading(false);
  }
};

// DESPUÉS (API call real):
const fetchWorkers = async () => {
  try {
    setLoading(true);
    setError('');

    // API call real
    const workersData = await getWorkers();
    setWorkers(workersData);
  } catch (err) {
    const message = err instanceof Error ? err.message : 'Error al cargar trabajadores.';
    setError(message);
  } finally {
    setLoading(false);
  }
};
```

**Estados Loading/Error:**
- Ya implementados correctamente (líneas 27-28)
- `<Loading />` y `<ErrorMessage />` ya existen (líneas 65-66)
- No requiere cambios adicionales

**Testing Checklist P1:**
```
[ ] npm run dev funciona sin errores TypeScript
[ ] Página carga sin crashes
[ ] Loading spinner visible durante fetch
[ ] Lista de trabajadores del backend se muestra
[ ] Click en trabajador navega a /operacion
[ ] Error message si backend no responde (detener uvicorn y recargar)
[ ] Botón "Reintentar" funciona
[ ] Console.log muestra workers data correcta
```

---

### 4.4 app/seleccionar-spool/page.tsx (Modificar)

**Propósito:** Integrar P4 - Seleccionar Spool con API real.

**Líneas a modificar:** -37 líneas (eliminar mock + getFilteredSpools) + imports + state

**Cambios específicos:**

**1. Línea 5 - Agregar imports:**
```typescript
import { getSpoolsParaIniciar, getSpoolsParaCompletar } from '@/lib/api'; // NUEVO
```

**2. Líneas 9-43 - ELIMINAR MOCK_SPOOLS (35 líneas):**
```typescript
// ELIMINAR todo el MOCK_SPOOLS array
```

**3. Línea 58 - Agregar state para spools reales:**
```typescript
// AGREGAR después de const { state, setState } = useAppState();
const [spools, setSpools] = useState<Spool[]>([]);
```

**4. Líneas 72-85 - Reemplazar `fetchSpools()`:**
```typescript
// ANTES (simulación sin fetch):
const fetchSpools = async () => {
  try {
    setLoading(true);
    setError('');

    // Simular API call con delay de 500ms
    await new Promise(resolve => setTimeout(resolve, 500));

    setLoading(false);
  } catch {
    setError('Error al cargar spools. Intenta nuevamente.');
    setLoading(false);
  }
};

// DESPUÉS (API calls reales según tipo):
const fetchSpools = async () => {
  try {
    setLoading(true);
    setError('');

    // API call real según tipo (iniciar o completar)
    let spoolsData: Spool[] = [];

    if (tipo === 'iniciar') {
      spoolsData = await getSpoolsParaIniciar(state.selectedOperation!);
    } else if (tipo === 'completar') {
      spoolsData = await getSpoolsParaCompletar(
        state.selectedOperation!,
        state.selectedWorker!
      );
    }

    setSpools(spoolsData);
  } catch (err) {
    const message = err instanceof Error ? err.message : 'Error al cargar spools.';
    setError(message);
  } finally {
    setLoading(false);
  }
};
```

**5. Líneas 87-109 - ELIMINAR `getFilteredSpools()` (23 líneas):**
```typescript
// ELIMINAR toda la función getFilteredSpools()
// Backend ya filtra los spools correctamente
```

**6. Línea 132 - Eliminar cálculo de `filteredSpools`:**
```typescript
// ANTES:
const filteredSpools = getFilteredSpools();

// DESPUÉS:
// Ya no se necesita, usar state directamente
```

**7. Líneas 156-163 - Actualizar `<List>` component:**
```typescript
// ANTES:
<List
  items={filteredSpools.map((s) => ({ ... }))}
  onItemClick={handleSelectSpool}
  emptyMessage={getEmptyMessage()}
/>

// DESPUÉS:
<List
  items={spools.map((s) => ({
    id: s.tag_spool,
    label: s.tag_spool,
    subtitle: s.proyecto || 'Sin proyecto',
  }))}
  onItemClick={handleSelectSpool}
  emptyMessage={getEmptyMessage()}
/>
```

**Lógica Condicional (Tipo: Iniciar vs Completar):**

**Flujo INICIAR:**
- API: `getSpoolsParaIniciar(operacion)`
- Backend filtra: ARM (V=0, BA llena, BB vacía) o SOLD (W=0, BB llena, BD vacía)
- Frontend solo muestra lista (sin filtrado adicional)

**Flujo COMPLETAR:**
- API: `getSpoolsParaCompletar(operacion, worker_nombre)`
- Backend filtra: ARM (V=0.1, BC=worker) o SOLD (W=0.1, BE=worker)
- Frontend solo muestra lista (ownership ya validado por backend)

**Función `getEmptyMessage()` (mantener sin cambios):**
- Ya correcta para ambos flujos
- Backend retorna array vacío si no hay spools elegibles

**Testing Checklist P4:**
```
[ ] INICIAR ARM: Muestra spools con arm=0 del backend
[ ] INICIAR SOLD: Muestra spools con sold=0, arm=1.0 del backend
[ ] COMPLETAR ARM: Muestra solo mis spools (armador=yo)
[ ] COMPLETAR SOLD: Muestra solo mis spools (soldador=yo)
[ ] Empty state muestra mensaje correcto si no hay spools
[ ] Loading state funciona correctamente
[ ] Error state muestra mensaje de API
[ ] Click en spool navega a /confirmar con query param
[ ] Console Network tab muestra requests correctos
```

---

### 4.5 app/confirmar/page.tsx (Modificar - CRÍTICO)

**Propósito:** Integrar P5 - Confirmar Acción con API real POST.

**Líneas a modificar:** +15 líneas (payload construction + API calls)

**Cambios específicos:**

**1. Línea 5 - Agregar imports:**
```typescript
import { iniciarAccion, completarAccion } from '@/lib/api'; // NUEVO
import type { ActionPayload } from '@/lib/types'; // NUEVO
```

**2. Líneas 23-38 - Reemplazar `handleConfirm()`:**
```typescript
// ANTES (simulación con delay):
const handleConfirm = async () => {
  try {
    setLoading(true);
    setError('');

    // Simular API call con delay de 1 segundo
    await new Promise(resolve => setTimeout(resolve, 1000));

    // Simular éxito (en DÍA 4 se reemplaza con API real)
    router.push('/exito');
  } catch (err) {
    const message = err instanceof Error ? err.message : 'Error al procesar acción';
    setError(message);
  } finally {
    setLoading(false);
  }
};

// DESPUÉS (API calls reales):
const handleConfirm = async () => {
  try {
    setLoading(true);
    setError('');

    // Construir payload
    const payload: ActionPayload = {
      worker_nombre: state.selectedWorker!,
      operacion: state.selectedOperation!,
      tag_spool: state.selectedSpool!,
    };

    // Si es COMPLETAR, agregar timestamp actual (opcional)
    if (tipo === 'completar') {
      payload.timestamp = new Date().toISOString();
    }

    // API call según tipo
    if (tipo === 'iniciar') {
      await iniciarAccion(payload);
    } else {
      await completarAccion(payload); // Puede lanzar 403 si ownership falla
    }

    // Si llegamos aquí, éxito
    router.push('/exito');
  } catch (err) {
    const message = err instanceof Error
      ? err.message
      : 'Error al procesar acción. Intenta nuevamente.';
    setError(message);
  } finally {
    setLoading(false);
  }
};
```

**POST Request Payloads:**

**INICIAR payload:**
```json
{
  "worker_nombre": "Juan Pérez",
  "operacion": "ARM",
  "tag_spool": "MK-1335-CW-25238-011"
}
```

**COMPLETAR payload:**
```json
{
  "worker_nombre": "Juan Pérez",
  "operacion": "ARM",
  "tag_spool": "MK-1335-CW-25238-011",
  "timestamp": "2025-11-11T14:30:00.000Z"
}
```

**Manejo Error 403 (Ownership Validation):**

**Flujo de error:**
1. Usuario intenta completar spool que no inició
2. Backend valida BC/BE != worker_nombre
3. Backend retorna **403 FORBIDDEN** con mensaje descriptivo
4. `completarAccion()` captura 403 y lanza Error con mensaje
5. `handleConfirm()` captura Error y muestra en `<ErrorMessage>`
6. Usuario ve: "Solo Juan López puede completar esta acción. Tú eres María García."

**Loading Message (línea 101 - mantener):**
```tsx
<Loading message="Actualizando Google Sheets..." />
```

**Testing Checklist P5 (CRÍTICO):**
```
[ ] INICIAR ARM: POST exitoso, navega a /exito
[ ] COMPLETAR ARM: POST exitoso, navega a /exito
[ ] Error 403 ownership: Muestra mensaje claro (probar con otro trabajador)
[ ] Error 404 spool no encontrado: Muestra mensaje
[ ] Error 400 ya iniciada: Muestra mensaje
[ ] Loading message visible durante POST
[ ] Botón Cancelar funciona (confirmación + reset)
[ ] Resumen muestra datos correctos antes de confirmar
[ ] Timestamp se envía solo en COMPLETAR
[ ] Console Network tab muestra POST request correcto
[ ] Google Sheets actualizado correctamente (verificar en Sheet TESTING)
```

---

## 5. Configuración Environment Variables

### .env.local (Desarrollo)

**Archivo:** `zeues-frontend/.env.local`

**Contenido:**
```bash
NEXT_PUBLIC_API_URL=http://localhost:8000
```

**IMPORTANTE:**
- Variables que empiezan con `NEXT_PUBLIC_` son accesibles en browser (client-side)
- NO poner secrets aquí (keys, tokens, passwords)
- Backend debe estar corriendo en puerto 8000

### Verificación

```bash
# Terminal 1: Backend
cd /Users/sescanella/Proyectos/ZEUES-by-KM
source venv/bin/activate
uvicorn backend.main:app --reload --port 8000

# Terminal 2: Frontend
cd zeues-frontend
npm run dev

# Browser: http://localhost:3001
```

---

## 6. Testing Strategy

### Testing Manual (Suficiente para MVP)

**Filosofía:** Testing manual en navegador es suficiente para validar integración API en 6 días.

**Testing por Endpoint:**

**1. GET /api/workers (P1):**
```
[ ] Lista de trabajadores carga correctamente
[ ] Loading spinner visible durante fetch
[ ] Click en trabajador navega a /operacion
[ ] Error message si backend apagado
[ ] Network tab muestra GET request correcto
```

**2. GET /api/spools/iniciar (P4 - INICIAR):**
```
[ ] Spools con arm=0 se muestran (verificar en Sheets)
[ ] Proyecto visible como subtitle
[ ] Empty state si no hay spools
[ ] Error message si falla API
[ ] Network tab muestra query param operacion=ARM
```

**3. GET /api/spools/completar (P4 - COMPLETAR):**
```
[ ] Solo mis spools (BC/BE=mi nombre) se muestran
[ ] Empty state si no tengo spools en progreso
[ ] Error message si falla API
[ ] Network tab muestra query params operacion + worker_nombre URL encoded
```

**4. POST /api/iniciar-accion (P5 - INICIAR):**
```
[ ] Loading message "Actualizando Google Sheets..."
[ ] Navega a /exito después de éxito
[ ] P6 muestra checkmark verde
[ ] Google Sheets actualizado (V→0.1, BC=nombre)
[ ] Network tab muestra POST body correcto
```

**5. POST /api/completar-accion (P5 - COMPLETAR):**
```
[ ] POST exitoso con timestamp
[ ] Navega a /exito
[ ] Google Sheets actualizado (V→1.0, BB=fecha)
[ ] Network tab muestra POST body con timestamp
```

**6. Error 403 Ownership Validation (CRÍTICO):**
```
[ ] Worker1 inicia ARM en spool X
[ ] Worker2 intenta completar ARM en spool X
[ ] Error 403 FORBIDDEN capturado
[ ] Mensaje claro: "Solo [Worker1] puede completar..."
[ ] ErrorMessage component muestra el error
[ ] No navega a /exito
[ ] Usuario puede click "Volver" o "Cancelar"
```

### Comandos Curl de Ejemplo

```bash
# Health check
curl http://localhost:8000/api/health

# Get workers
curl http://localhost:8000/api/workers

# Get spools iniciar ARM
curl "http://localhost:8000/api/spools/iniciar?operacion=ARM"

# Get spools completar ARM (URL encoded)
curl "http://localhost:8000/api/spools/completar?operacion=ARM&worker_nombre=Juan%20P%C3%A9rez"

# Iniciar acción (POST)
curl -X POST http://localhost:8000/api/iniciar-accion \
  -H "Content-Type: application/json" \
  -d '{"worker_nombre": "Juan Pérez", "operacion": "ARM", "tag_spool": "MK-1335-CW-25238-011"}'

# Completar acción (POST)
curl -X POST http://localhost:8000/api/completar-accion \
  -H "Content-Type: application/json" \
  -d '{"worker_nombre": "Juan Pérez", "operacion": "ARM", "tag_spool": "MK-1335-CW-25238-011", "timestamp": "2025-11-11T14:30:00.000Z"}'
```

---

## 7. Criterios de Éxito DÍA 4

### Implementación
- [ ] `/lib/api.ts` creado con 6 funciones (280 líneas)
- [ ] `/lib/types.ts` actualizado con `ActionResponse` (+17 líneas)
- [ ] P1 integrado con `getWorkers()` (-9 líneas mock)
- [ ] P4 integrado con `getSpoolsParaIniciar()` y `getSpoolsParaCompletar()` (-37 líneas mock)
- [ ] P5 integrado con `iniciarAccion()` y `completarAccion()` (+15 líneas)
- [ ] Mock data completamente eliminado de P1, P4, P5
- [ ] Build sin errores TypeScript

### Testing Manual
- [ ] Flujo INICIAR ARM completo (P1→P6) con datos backend reales
- [ ] Flujo COMPLETAR ARM completo (P1→P6) con datos backend reales
- [ ] Ownership validation funciona (error 403 si otro trabajador intenta completar)
- [ ] Google Sheets actualizado correctamente (verificar en Sheet TESTING)
- [ ] Network tab muestra requests correctos (GET + POST)
- [ ] Error handling funciona (backend apagado, spool no encontrado, etc.)

### Integración
- [ ] Backend corriendo en `localhost:8000`
- [ ] Frontend corriendo en `localhost:3001`
- [ ] Variable `NEXT_PUBLIC_API_URL` configurada
- [ ] CORS permite requests desde localhost:3001
- [ ] Loading states visibles durante API calls
- [ ] Error messages user-friendly en español

---

## 8. Comandos de Ejecución

### Setup Inicial

```bash
# Terminal 1: Backend (MUST BE RUNNING)
cd /Users/sescanella/Proyectos/ZEUES-by-KM
source venv/bin/activate
uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000

# Terminal 2: Frontend
cd zeues-frontend

# Verificar .env.local existe con NEXT_PUBLIC_API_URL
cat .env.local

# Dev server
npm run dev

# Browser
open http://localhost:3001
```

### Verificación Rápida

```bash
# Verificar backend responde
curl http://localhost:8000/api/health

# Verificar workers endpoint
curl http://localhost:8000/api/workers

# Verificar frontend puede alcanzar backend (desde browser console)
fetch('http://localhost:8000/api/health').then(r => r.json()).then(console.log)
```

### Build Producción

```bash
cd zeues-frontend

# Build
npm run build

# Verificar no hay errores TypeScript
npm run lint
```

---

## 9. Resumen de Archivos y Líneas

| Archivo | Líneas Iniciales | Líneas Finales | Cambio | Estado |
|---------|------------------|----------------|--------|--------|
| `lib/types.ts` | 28 | **42** | **+14** | ✅ FASE 1 |
| `lib/api.ts` | 16 (stub) | **226** | **+210** | ✅ FASE 1 |
| `.env.local` | 5 | 5 | 0 | ✅ Verificado |
| `app/page.tsx` | 84 | **71** | **-13** | ✅ FASE 2 |
| `app/seleccionar-spool/page.tsx` | 177 | ~140 | -37 | ⏳ FASE 3 |
| `app/confirmar/page.tsx` | 125 | ~140 | +15 | ⏳ FASE 4 |
| **TOTAL FASES 1-2** | **133** | **344** | **+211** | ✅ **COMPLETADO** |
| **TOTAL DÍA 4** | **435** | **~624** | **~189** | 🔄 **40% completado** |

**Tiempo Estimado por Fase:**

| Fase | Tiempo Estimado | Tiempo Real | Estado | Bloqueadores |
|------|----------------|-------------|--------|--------------|
| FASE 1: API Client | 2-3 horas | ✅ ~2h | ✅ COMPLETADA | Ninguno |
| FASE 2: P1 Integration | 30 min | ✅ ~25 min | ✅ COMPLETADA | Ninguno |
| FASE 3: P4 Integration | 1-1.5 horas | - | ⏳ Pendiente | FASES 1-2 ✅ |
| FASE 4: P5 Integration | 1-1.5 horas | - | ⏳ Pendiente | FASES 1-2 ✅ |
| FASE 5: Testing Final | 1 hora | - | ⏳ Pendiente | FASE 2-4 |
| **TOTAL** | **6-7.5 horas** | **~2.4h / 6-7.5h** | **40% completado** | |

**Estimado conservador:** 1 día completo de trabajo (8 horas)
**Estimado optimista:** 6 horas si no hay bugs mayores

---

## 10. Riesgos y Mitigaciones

### Riesgo 1: CORS Bloquea Requests

**Problema:** Browser bloquea requests de `localhost:3001` a `localhost:8000`.

**Síntomas:**
- Error en console: "CORS policy: No 'Access-Control-Allow-Origin' header"
- Network tab muestra requests cancelados
- API calls fallan silenciosamente

**Mitigación:**
- Backend ya tiene CORS configurado en `main.py` (DÍA 3)
- Verificar `CORS_ORIGINS` incluye `http://localhost:3001`
- Verificar `allow_methods` incluye "POST"
- Test con curl primero, luego browser

### Riesgo 2: URL Encoding Falla para Nombres con Tildes

**Problema:** Nombres como "María González" no matchean en backend.

**Síntomas:**
- GET `/api/spools/completar` retorna array vacío
- Error 404 "Trabajador no encontrado"

**Mitigación:**
- `encodeURIComponent()` en `getSpoolsParaCompletar()`
- Backend usa case-insensitive matching (ya implementado)
- Test con nombre con tildes y espacios

### Riesgo 3: TypeScript Errors en Build

**Problema:** `npm run build` falla por tipos incorrectos.

**Síntomas:**
- Error: "Property 'data' does not exist on type 'ActionResponse'"
- Error: "Type 'number | string' is not assignable to type 'number'"

**Mitigación:**
- Agregar `ActionResponse` interface ANTES de usarla
- Usar `!` assertion solo cuando seguro (e.g., `state.selectedWorker!`)
- Run `npm run build` después de cada fase

### Riesgo 4: Ownership Validation No Funciona

**Problema:** Backend no retorna 403, o frontend no lo captura.

**Síntomas:**
- Trabajador diferente puede completar acción
- No se muestra error message
- Google Sheets actualizado incorrectamente

**Mitigación:**
- Backend ya tiene ownership validation (DÍA 2)
- `completarAccion()` tiene check específico para 403
- Test exhaustivo con 2 trabajadores diferentes

### Riesgo 5: Mock Data No Eliminado Completamente

**Problema:** Código sigue usando mock data en algunos casos.

**Síntomas:**
- Datos no se actualizan después de cambios en Sheets
- Filtrado no funciona correctamente
- Empty states no se muestran

**Mitigación:**
- Buscar y eliminar TODAS las constantes `MOCK_*`
- Eliminar función `getFilteredSpools()` en P4
- Grep para buscar residuos: `grep -r "MOCK_" zeues-frontend/app`

---

## 11. Próximos Pasos Después de DÍA 4

**DÍA 5 (12 Nov): Testing Flujos + Ajustes**
- Testing manual exhaustivo (checklist completo)
- Verificar ownership validation con múltiples trabajadores
- Fix bugs detectados
- Verificar Google Sheets actualiza correctamente

**DÍA 6 (13 Nov): Testing Exhaustivo + Deploy**
- Navegación completa y validaciones finales
- Testing mobile/tablet responsive
- Build producción
- Deploy Vercel
- Testing en URL producción

---

## 12. Checklist de Implementación (Copy-Paste)

### FASE 1: API Client Base ✅ COMPLETADA (10 Nov 2025)
- [x] `lib/types.ts` actualizado
  - [x] Interface `ActionResponse` agregada (+14 líneas - Record<string, unknown>)
  - [x] Build sin errores TypeScript
- [x] `lib/api.ts` creado desde cero (226 líneas)
  - [x] Constants: `API_URL` desde env var
  - [x] Helper: `handleResponse<T>()` implementado
  - [x] `getWorkers()` implementado
  - [x] `getSpoolsParaIniciar()` implementado
  - [x] `getSpoolsParaCompletar()` con URL encoding
  - [x] `iniciarAccion()` implementado
  - [x] `completarAccion()` con manejo 403
  - [x] `checkHealth()` implementado
  - [x] Todos los JSDoc comments completos
  - [x] Build sin errores TypeScript
- [x] `.env.local` verificado
  - [x] Contiene `NEXT_PUBLIC_API_URL=http://localhost:8000`

**Validaciones Completadas:**
- [x] `npx tsc --noEmit` - ✅ Sin errores
- [x] `npm run lint` - ✅ Sin warnings ni errors
- [x] `npm run build` - ✅ Build producción exitoso

### FASE 2: P1 Integration ✅ COMPLETADA (11 Nov 2025 - 01:15)
- [x] `app/page.tsx` modificado
  - [x] Import `getWorkers` agregado
  - [x] Import `Worker` type agregado
  - [x] `MOCK_WORKERS` eliminado (6 líneas)
  - [x] Interface `Worker` local duplicada eliminada (6 líneas)
  - [x] `fetchWorkers()` reemplazado con API call real
  - [x] Error handling mejorado con `instanceof Error`
  - [x] Build sin errores TypeScript
- [x] Validaciones
  - [x] `npx tsc --noEmit` - ✅ Sin errores
  - [x] `npm run lint` - ✅ Sin warnings ni errors
  - [x] `npm run build` - ✅ Build producción exitoso (9 páginas)
  - [x] Archivo final: 71 líneas (vs 84 originales, -13 líneas)

**Testing P1 - PENDIENTE (Requiere backend activo):**
- [ ] Backend corriendo en puerto 8000
- [ ] Lista trabajadores carga correctamente del API
- [ ] Loading spinner visible durante fetch
- [ ] Click trabajador navega a /operacion
- [ ] Error message si backend apagado
- [ ] Network tab muestra GET correcto

### FASE 3: P4 Integration ⏳ PENDIENTE
- [ ] `app/seleccionar-spool/page.tsx` modificado
  - [ ] Imports API functions agregados
  - [ ] `MOCK_SPOOLS` eliminado (líneas 9-43)
  - [ ] State `spools` agregado
  - [ ] `fetchSpools()` reemplazado con API calls condicionales
  - [ ] `getFilteredSpools()` eliminado (líneas 87-109)
  - [ ] `<List>` usando `spools` state
  - [ ] Build sin errores TypeScript
- [ ] Testing P4
  - [ ] INICIAR ARM: Spools arm=0 se muestran
  - [ ] COMPLETAR ARM: Solo mis spools (armador=yo)
  - [ ] Empty state funciona
  - [ ] Error message funciona
  - [ ] Network tab muestra query params correctos

### FASE 4: P5 Integration (CRÍTICO) ⏳ PENDIENTE
- [ ] `app/confirmar/page.tsx` modificado
  - [ ] Imports API functions agregados
  - [ ] Import `ActionPayload` type agregado
  - [ ] `handleConfirm()` reemplazado con API calls
  - [ ] Payload construction con tipos correctos
  - [ ] Timestamp agregado solo en COMPLETAR
  - [ ] Error handling con tipo correcto
  - [ ] Build sin errores TypeScript
- [ ] Testing P5 (CRÍTICO)
  - [ ] INICIAR ARM: POST exitoso, navega /exito
  - [ ] COMPLETAR ARM: POST exitoso, navega /exito
  - [ ] Error 403 ownership: Mensaje claro
  - [ ] Loading message visible durante POST
  - [ ] Google Sheets actualizado (verificar en Sheet)
  - [ ] Network tab muestra POST body correcto

### FASE 5: Testing Final ⏳ PENDIENTE
- [ ] Flujo INICIAR ARM completo (P1→P6)
- [ ] Flujo COMPLETAR ARM completo (P1→P6)
- [ ] Flujo INICIAR SOLD completo
- [ ] Flujo COMPLETAR SOLD completo
- [ ] Ownership validation funciona (2 trabajadores)
- [ ] Google Sheets actualizado correctamente
- [ ] Network tab requests correctos en todas las páginas
- [ ] Error handling funciona (backend apagado, 404, 400, 403)
- [ ] Build producción exitoso (`npm run build`)

---

---

## 13. PROGRESO Y ESTADO ACTUAL

### ✅ FASE 1 COMPLETADA (10 Nov 2025 - 23:45)

**Implementación:**
- ✅ `lib/types.ts` actualizado: +14 líneas (interface ActionResponse)
- ✅ `lib/api.ts` creado: 226 líneas (6 funciones fetch + helper)
- ✅ `.env.local` verificado: NEXT_PUBLIC_API_URL configurado

**Características Implementadas:**
- ✅ Native fetch (NO axios) - Simplicidad MVP
- ✅ Helper `handleResponse<T>()` - Type-safe error handling
- ✅ URL encoding con `encodeURIComponent()` - Nombres con tildes
- ✅ Manejo especial 403 en `completarAccion()` - Ownership validation
- ✅ JSDoc completo en todas las funciones
- ✅ Error messages en español user-friendly

**Validaciones:**
- ✅ `npx tsc --noEmit` - Sin errores TypeScript
- ✅ `npm run lint` - Sin warnings ni errors
- ✅ `npm run build` - Build producción exitoso

**Tiempo Real:** ~2 horas (dentro del estimado 2-3h)

### ✅ FASE 2 COMPLETADA (11 Nov 2025 - 01:15)

**Implementación:**
- ✅ `app/page.tsx` integrado con API real: 71 líneas finales (vs 84 originales)
- ✅ Import `getWorkers` y `Worker` type agregados
- ✅ `MOCK_WORKERS` eliminado (6 líneas)
- ✅ Interface `Worker` local duplicada eliminada (6 líneas)
- ✅ `fetchWorkers()` reemplazado con API call real

**Características Implementadas:**
- ✅ API call real a `GET /api/workers`
- ✅ Error handling mejorado con `instanceof Error`
- ✅ Type safety completo (NO uso de `any`)
- ✅ Código más simple y limpio (-13 líneas netas)

**Validaciones:**
- ✅ `npx tsc --noEmit` - Sin errores TypeScript
- ✅ `npm run lint` - Sin warnings ni errors
- ✅ `npm run build` - Build producción exitoso (9 páginas)

**Tiempo Real:** ~25 minutos (dentro del estimado 30 min)

**Testing Manual Pendiente:**
- Requiere backend activo en `localhost:8000`
- Validación de flujo P1 completo

### 📊 Progreso General DÍA 4

**Completado:** 2/5 fases (40% del tiempo estimado)
**Líneas implementadas:** 211 de ~189 netas (112% - más completo de lo estimado)
**Archivos completados:** 3/5 archivos

**Próximas Fases:**
1. ⏳ **FASE 3** (1-1.5h): Integrar P4 con API de spools - Filtrado backend
2. ⏳ **FASE 4** (1-1.5h): Integrar P5 con POST requests - Ownership validation crítica
3. ⏳ **FASE 5** (1h): Testing E2E completo - Validación flujos INICIAR→COMPLETAR

**Tiempo Restante Estimado:** 3.5-5 horas

---

**FIN - proyecto-frontend-api.md - ZEUES Frontend API Integration - DÍA 4 EN PROGRESO**

**Última Actualización:** 11 Nov 2025 - 01:15
**Estado:** FASES 1-2 ✅ COMPLETADAS | FASES 3-5 ⏳ PENDIENTES
**Progreso:** 40% completado (2/5 fases) - ~2.4h invertidas de 6-7.5h estimadas
**Próximo Paso:** Ejecutar FASE 3 - Integrar P4 Seleccionar Spool con `getSpoolsParaIniciar()` y `getSpoolsParaCompletar()`
