# ZEUES v2.0 - Frontend Technical Documentation

**Última actualización:** 13 Dic 2025 01:00 | **Versión:** 2.0 | **Branch:** `v2.0-dev`

---

## 📋 Quick Reference

| Aspecto | Estado | Detalles |
|---------|--------|----------|
| **Progreso Frontend** | 95% | DÍA 2 - Multiselect UI 100% COMPLETO (13 Dic 18:00) |
| **Archivos** | 31 archivos | v1.0: 28 → +3 nuevos (Checkbox, SpoolSelector) |
| **Archivos Modificados DÍA 2** | 23 archivos | P1-P6 + lib + components (3 sesiones acumuladas) |
| **Componentes** | 8 componentes | +2 nuevos vs v1.0 (Checkbox, SpoolSelector) ✅ |
| **Páginas** | 7 páginas | 7 modificadas (P4-P6 con batch support) |
| **Tests E2E** | 17 tests | v1.0: 17 passing → +3 nuevos pendientes (20 target) |
| **API Functions** | 12 funciones | v1.0: 6 → +6 nuevas (roles, cancelar, 3 batch) |
| **Deployment** | Vercel | zeues-frontend.vercel.app (pendiente v2.0 deploy) |

### Estado Implementación

```
✅ COMPLETADO (95% frontend):
  ✅ P2 Filtrado por Roles - Worker interface breaking change + API integration (12 Dic)
  ✅ P3 Botón CANCELAR - ActionPayload breaking change worker_id + flujo completo (13 Dic 01:00)
  ✅ P4 Multiselect UI - Checkbox + SpoolSelector componentes con toggle mode (13 Dic 18:00)
  ✅ P4 Búsqueda TAG_SPOOL - Filtrado en tiempo real case-insensitive (13 Dic 18:00)
  ✅ P5/P6 Batch - Confirmación lista + resultados exitosos/fallidos (13 Dic 18:00)
  ✅ API Batch - 3 funciones (iniciarAccionBatch, completarAccionBatch, cancelarAccionBatch)
  ✅ Types - BatchActionRequest, BatchActionResponse, SpoolActionResult
  ✅ Context - selectedSpools[], batchMode, batchResults

🔴 PENDIENTE (5% frontend):
  🔴 Tests E2E +3 nuevos (multiselect, cancelar, búsqueda)
  🔴 Deploy Vercel v2.0

🟡 NICE-TO-HAVE (si alcanza tiempo):
  🟡 Admin Panel (CRUD usuarios, reportes)
  🟡 METROLOGÍA UI (botón verde, filtros, colores)

✅ BASE v1.0 (producción estable):
  ✅ 7 páginas flujo completo ARM/SOLD
  ✅ 5 componentes base reutilizables
  ✅ Context API + Next.js routing
  ✅ 17 tests E2E passing
```

### Nuevas Features v2.0

| Feature | Descripción | Estado | Fecha |
|---------|-------------|--------|-------|
| **Filtrado Roles** | P2 muestra operaciones según roles worker (GET /workers/{id}/roles) | ✅ COMPLETADO | 12 Dic 21:00 |
| **Botón CANCELAR** | P3 agrega opción CANCELAR para operaciones EN_PROGRESO + breaking change worker_id | ✅ COMPLETADO | 13 Dic 01:00 |
| **Multiselect** | P4 checkboxes, select all, contador (hasta 50 spools) + toggle mode | ✅ COMPLETADO | 13 Dic 18:00 |
| **Búsqueda TAG_SPOOL** | P4 campo búsqueda en tiempo real (case-insensitive) | ✅ COMPLETADO | 13 Dic 18:00 |
| **Batch API** | POST /iniciar-accion-batch, /completar-accion-batch, /cancelar-accion-batch | ✅ COMPLETADO | 13 Dic 18:00 |
| **Resultados Batch** | P6 muestra exitosos/fallidos con detalle + 2-column grid | ✅ COMPLETADO | 13 Dic 18:00 |

---

## 🔧 Guía de Mantenimiento LLM-First

**Propósito:** Este documento es una **referencia técnica ejecutiva optimizada para LLMs**, NO un manual de implementación extenso.

### Principios de Optimización (SIEMPRE mantener)

1. **Token-efficiency prioritario:**
   - Tablas > código extenso
   - Component signatures > implementaciones completas
   - Props interfaces > código JSX completo
   - Target: < 800 líneas, < 9,000 tokens

2. **Quick Reference obligatorio:**
   - Progreso, archivos, tests, deployment
   - Features nuevas con estado visual (✅/🔴/🟡)
   - **Actualizar PRIMERO antes de cualquier sección**

3. **Formato preferido:**
   - **Componentes:** Tabla props + signature TypeScript
   - **Páginas:** Tabla con props/hooks + flujo (NO JSX completo)
   - **API:** Solo function signatures + tipos
   - **Tests:** Lista nombres + archivos (NO código Playwright)
   - **Estilos:** Descripción Tailwind (NO clases completas)

4. **Qué ELIMINAR:**
   - ❌ Código JSX > 15 líneas
   - ❌ Implementaciones completas de componentes
   - ❌ Código Playwright test completo
   - ❌ Ejemplos de uso extensos

5. **Qué MANTENER:**
   - ✅ Interfaces TypeScript (props, types, responses)
   - ✅ Function signatures con tipos
   - ✅ Tablas comparativas v1.0 vs v2.0
   - ✅ Nombres tests y archivos
   - ✅ Comandos deployment

### Reglas de Actualización

**Cuando te diga "actualiza el archivo":**

1. **Primero Quick Reference:**
   - Progreso frontend (%)
   - Tests E2E (X/Y passing)
   - Archivos/componentes nuevos

2. **Formato para componente nuevo:**
```markdown
### Componente: NombreComponente

**Props:**
| Prop | Tipo | Requerido | Default |
|------|------|-----------|---------|
| prop1 | string | Sí | - |
| prop2 | number | No | 0 |

**Signature:**
`function NombreComponente({ prop1, prop2 }: Props): JSX.Element`

**Uso:** Descripción breve de responsabilidad y dónde se usa.
```

3. **Mantener límites:**
   - Si documento > 800 líneas: compactar secciones antiguas
   - Convertir código JSX a tablas de props

---

## 1. Stack y Arquitectura

### Stack Tecnológico (sin cambios)

- **Framework:** Next.js 14.2+ (App Router)
- **UI:** React 18+ + TypeScript 5+
- **Estilos:** Tailwind CSS 3.4+ (inline utility-first)
- **Testing:** Playwright (E2E)
- **Estado:** React Context API (NO Redux/Zustand)
- **API:** Native fetch (NO axios)

**Dependencias v2.0:** Sin cambios vs v1.0 (NO nuevas librerías)

### Principios v2.0

| Principio | Descripción |
|-----------|-------------|
| **Mobile-First** | Botones grandes 60px+ (h-16/h-20), touch-friendly |
| **Component Simplicity** | Functional components simples, NO over-engineering |
| **Inline Tailwind** | Estilos inline, NO CSS modules/styled-components |
| **Native Fetch** | fetch() nativo, NO axios ni librerías HTTP |
| **Batch UI Patterns** 🆕 | Multiselect con checkboxes, bulk actions |
| **TypeScript Strict** 🆕 | NO `any`, tipos explícitos siempre |

---

## 2. Estructura del Proyecto

### Archivos Clave v2.0

**Componentes:**
- `components/Button.tsx` - Botón reutilizable (v1.0)
- `components/Card.tsx` - Card worker/spool (v1.0)
- `components/Loading.tsx` - Loading spinner (v1.0)
- `components/ErrorMessage.tsx` - Error display (v1.0)
- `components/Checkbox.tsx` 🆕 - Checkbox multiselect

**Páginas (7 total, sin cambios estructura):**
- `app/page.tsx` - P1: Worker ID (sin cambios)
- `app/operacion/page.tsx` - P2: Operación (v2.0: +filtrado roles) 🔄
- `app/tipo-interaccion/page.tsx` - P3: INICIAR/COMPLETAR/CANCELAR (v2.0: +botón CANCELAR) 🔄
- `app/seleccionar-spool/page.tsx` - P4: Spool selection (v2.0: +multiselect + búsqueda) 🔄
- `app/confirmar/page.tsx` - P5: Confirmación (v2.0: +batch summary) 🔄
- `app/exito/page.tsx` - P6: Éxito (v2.0: +batch results) 🔄

**Lib:**
- `lib/api.ts` - v1.0: 6 funciones | v2.0: +4 nuevas (10 total)
- `lib/types.ts` - v1.0 interfaces | v2.0: +BatchRequest, BatchResponse
- `lib/context.tsx` - State flujo (sin cambios vs v1.0)
- `lib/constants.ts` - v1.0: ARM/SOLD | v2.0: +METROLOGÍA

**Tests E2E:**
- `e2e/01-07-*.spec.ts` - 17 tests v1.0 (INICIAR/COMPLETAR flows)
- `e2e/08-multiselect-batch.spec.ts` 🆕 - Batch operations
- `e2e/09-cancelar.spec.ts` 🆕 - Cancelar EN_PROGRESO
- `e2e/10-busqueda-spool.spec.ts` 🆕 - Búsqueda TAG_SPOOL

**Total:** 29 archivos (+1 vs v1.0) | 20 tests (+3 vs v1.0)

---

## 3. Componentes

### 3.1. Button - NUEVO VARIANT ✅ IMPLEMENTADO (13 Dic 2025)

**Props (sin cambios):**
| Prop | Tipo | Requerido | Default |
|------|------|-----------|---------|
| variant | ButtonVariant | No | 'primary' |
| children | ReactNode | Sí | - |
| onClick | () => void | No | undefined |
| disabled | boolean | No | false |

**Variants - NUEVO cancelar:**
```typescript
type ButtonVariant =
  | 'primary'      // bg-cyan-600 (INICIAR)
  | 'completar'    // bg-green-600 (COMPLETAR)
  | 'cancelar'     // bg-yellow-600 (CANCELAR) ✅ NUEVO
  | 'cancel';      // bg-gray-500 (Cancelar flujo - salir)
```

**Estilos Variant:**
- primary: `bg-cyan-600 hover:bg-cyan-700 text-white`
- completar: `bg-green-600 hover:bg-green-700 text-white`
- **cancelar: `bg-yellow-600 hover:bg-yellow-700 text-white`** ✅ NUEVO
- cancel: `bg-gray-500 hover:bg-gray-600 text-white`

**Uso:**
- P3: Botón "⚠️ CANCELAR ACCIÓN" (variant='cancelar')
- P5: Confirmación dinámica (variant según tipo)

**Diferencia cancelar vs cancel:**
- **cancelar**: Revertir acción EN_PROGRESO (amarillo, acción sobre spool)
- **cancel**: Abandonar flujo actual (gris, volver a inicio sin guardar)

---

### 3.2. Checkbox (NUEVO v2.0) 🔴 PENDIENTE

**Props:**
| Prop | Tipo | Requerido | Default |
|------|------|-----------|---------|
| checked | boolean | Sí | - |
| onChange | (checked: boolean) => void | Sí | - |
| label | string | No | undefined |
| disabled | boolean | No | false |

**Uso:** Multiselect en P4 para seleccionar múltiples spools (pendiente implementación).

**Estilos:** `w-6 h-6 text-cyan-600 rounded` (Tailwind inline)

---

## 4. Páginas v2.0

### 4.1. P2 - Operación con Filtrado por Roles ✅ IMPLEMENTADO (12 Dic 2025)

**Objetivo:** Filtrar botones operación según roles del trabajador.

**Implementación Completada:**

**State Local:**
| Variable | Tipo | Descripción |
|----------|------|-------------|
| allowedOperations | string[] | Operaciones permitidas según roles |
| isLoading | boolean | Estado de carga durante fetch roles |
| error | string \| null | Mensaje de error si fetch falla |

**Mapeo Roles → Operaciones (ROLE_TO_OPERATIONS):**
```typescript
const ROLE_TO_OPERATIONS: Record<string, string[]> = {
  'Armador': ['ARM'],
  'Soldador': ['SOLD'],
  'Metrologia': ['METROLOGIA'],
  'Ayudante': ['ARM', 'SOLD']  // Multi-operación
};
```

**Flujo Implementado:**
1. **useEffect al montar:** Fetch `GET /api/workers/{worker.id}/roles`
2. **Mapeo roles:** Usar ROLE_TO_OPERATIONS para obtener operaciones permitidas
3. **Deduplicación:** Set para eliminar duplicados (ej: Armador + Ayudante = ARM solo 1 vez)
4. **Renderizado condicional:** Solo mostrar botones si operación en allowedOperations
5. **Mensaje sin roles:** Si allowedOperations.length === 0, mostrar advertencia

**Hooks:**
- `useAppState()` - worker (Worker object), setOperacion
- `useState(allowedOperations: string[])` - operaciones filtradas
- `useState(isLoading: boolean)` - loading state
- `useState(error: string | null)` - error handling
- `useEffect()` - fetch roles al montar + cleanup

**Cambios vs v1.0:**
- ✅ +API call: `getWorkerRoles(worker.id)` (nueva función)
- ✅ +Filtrado condicional de 3 botones (ARM/SOLD/METROLOGIA)
- ✅ +Loading spinner durante fetch
- ✅ +ErrorMessage component si API falla
- ✅ +Mensaje advertencia si trabajador sin roles
- ✅ +Multi-rol support (Set para deduplicar)

**TypeScript Fix:**
- Non-null assertion `worker!.id` para satisfacer type checking (worker validado antes de render)

**Validación:**
- ✅ npm run lint - Sin errores
- ✅ npx tsc --noEmit - Sin errores

---

### 4.2. P3 - INICIAR/COMPLETAR/CANCELAR ✅ IMPLEMENTADO (13 Dic 2025)

**Objetivo:** Añadir tercera opción "CANCELAR ACCIÓN".

**Botones:**
| Texto | Color | Variant | Acción |
|-------|-------|---------|--------|
| INICIAR ACCIÓN | bg-cyan-600 | iniciar | setTipoInteraccion('iniciar') |
| COMPLETAR ACCIÓN | bg-green-600 | completar | setTipoInteraccion('completar') |
| ⚠️ CANCELAR ACCIÓN | bg-yellow-600 | cancelar | setTipoInteraccion('cancelar') ✅ |

**Implementación Completa:**
- Tercer botón implementado con emoji warning ⚠️
- Descripción: "Revertir acción en progreso"
- Handler: `handleSelectTipo(tipo: 'iniciar' | 'completar' | 'cancelar')`
- Context actualizado: selectedTipo acepta 'cancelar'

**Cambios vs v1.0:**
- +1 botón CANCELAR (amarillo, variant cancelar)
- +Descripción dinámica en botón
- Context type expandido: 'iniciar' | 'completar' | 'cancelar'

---

### 4.3. P4 - Seleccionar Spool con CANCELAR ✅ IMPLEMENTADO (13 Dic 2025)

**Objetivo v2.0:** Añadir lógica para CANCELAR (fetch spools EN_PROGRESO del worker).

**State:**
- `spools: Spool[]` - Lista spools API
- `selectedTags: string[]` - Tags seleccionados (pendiente multiselect)
- `isLoading: boolean`
- `error: string`

**Lógica API Condicional (3 tipos):**
```typescript
if (tipo === 'iniciar') {
  fetchedSpools = await getSpoolsParaIniciar(operacion);
} else if (tipo === 'completar') {
  fetchedSpools = await getSpoolsParaCompletar(operacion, selectedWorker.nombre_completo);
} else if (tipo === 'cancelar') {  // ✅ NUEVO
  fetchedSpools = await getSpoolsParaCancelar(operacion, selectedWorker.id);
}
```

**Implementación CANCELAR:**
- API call: `getSpoolsParaCancelar(operacion, workerId)` → GET /api/spools/cancelar
- Retorna: Spools EN_PROGRESO (estado 0.1) del worker especificado
- Título dinámico: "Selecciona TU spool para CANCELAR {operacion}"
- Mensaje empty: "No tienes spools en progreso de {operacion} para cancelar"
- Validación backend: Ownership (solo spools iniciados por este worker)

**Cambios vs v1.0:**
- +Condicional tipo === 'cancelar'
- +API function getSpoolsParaCancelar()
- Mensajería dinámica según tipo (INICIAR/COMPLETAR/CANCELAR)

**Pendiente:**
- Multiselect UI (checkboxes, select all, contador)
- Búsqueda TAG_SPOOL

---

### 4.4. P5 - Confirmación con CANCELAR ✅ IMPLEMENTADO (13 Dic 2025)

**Objetivo v2.0:** Breaking change payload worker_id + lógica 3 tipos acción.

**Breaking Change CRÍTICO - Payload:**
```typescript
// v1.0 (DEPRECATED)
const payload = {
  worker_nombre: state.selectedWorker,  // ❌ string
  operacion: state.selectedOperation,
  tag_spool: state.selectedSpool
};

// v2.0 (ACTUAL) ⚠️ BREAKING
const payload: ActionPayload = {
  worker_id: state.selectedWorker!.id,  // ✅ number
  operacion: state.selectedOperation as 'ARM' | 'SOLD',
  tag_spool: state.selectedSpool!,
  ...(tipo === 'completar' && { timestamp: new Date().toISOString() }),
};
```

**Lógica Condicional 3 Tipos:**
```typescript
if (tipo === 'iniciar') {
  await iniciarAccion(payload);
} else if (tipo === 'completar') {
  await completarAccion(payload);
} else {  // cancelar ✅ NUEVO
  await cancelarAccion(payload);
}
```

**UI Dinámica:**
- Título: `¿Confirmas INICIAR/COMPLETAR/CANCELAR ${operacion}?`
- Botón variant: iniciar (cyan) | completar (verde) | cancelar (amarillo)
- Botón texto: `✓ CONFIRMAR ${tipo.toUpperCase()}`

**Cambios vs v1.0:**
- ⚠️ BREAKING: Payload usa worker_id (int) no worker_nombre (string)
- +Lógica 3 tipos (iniciar/completar/cancelar)
- +cancelarAccion() API call
- Títulos/botones dinámicos según tipo

**Pendiente:**
- Batch operations (isBatch logic)
- Lista spools numerada para batch

---

### 4.5. P6 - Éxito con Mensajería Dinámica CANCELAR ✅ IMPLEMENTADO (13 Dic 2025)

**Objetivo v2.0:** Mensajes y colores dinámicos según tipo acción (INICIAR/COMPLETAR/CANCELAR).

**Lógica Mensajería Dinámica:**
```typescript
const tipo = state.selectedTipo;  // 'iniciar' | 'completar' | 'cancelar'

// Icon condicional
{tipo === 'cancelar' ? (
  <WarningIcon />  // Triángulo amarillo ⚠️
) : (
  <CheckmarkIcon />  // Checkmark verde ✓
)}

// Mensajes
const mensajes = {
  iniciar: "¡Acción iniciada exitosamente!",
  completar: "¡Acción completada exitosamente!",
  cancelar: "⚠️ Acción cancelada"
};

// Descripción adicional CANCELAR
{tipo === 'cancelar' && (
  <p className="text-yellow-600">El spool vuelve a estado PENDIENTE</p>
)}
```

**Implementación Completa:**
- Icon warning amarillo para CANCELAR (triángulo ⚠️)
- Icon checkmark verde para INICIAR/COMPLETAR (✓)
- Color dinámico: text-yellow-600 (CANCELAR) vs text-green-600 (INICIAR/COMPLETAR)
- Mensaje adicional CANCELAR: "El spool vuelve a estado PENDIENTE"
- Auto-redirect 5 seg → P1 (sin cambios vs v1.0)

**Cambios vs v1.0:**
- +Lógica condicional icon/color/mensaje según tipo
- +Warning icon (triángulo amarillo)
- +Descripción adicional para CANCELAR
- Mantiene: Auto-redirect 5 seg, resetState()

**Pendiente:**
- Batch results (exitosos/fallidos)
- Secciones success/error para batch

---

## 5. API Client (lib/api.ts)

### 5.1. Funciones v1.0 (sin cambios)

- `getWorkers()` → `Worker[]`
- `getSpoolsIniciar(operacion)` → `Spool[]`
- `getSpoolsCompletar(operacion, workerNombre)` → `Spool[]`
- `iniciarAccion(payload)` → `void`
- `completarAccion(payload)` → `void`
- `healthCheck()` → `{ status: string }`

### 5.2. Funciones Nuevas v2.0

**1. getWorkerRoles() ✅ IMPLEMENTADO (12 Dic)**
```typescript
export async function getWorkerRoles(workerId: number): Promise<string[]>
// GET /api/workers/{workerId}/roles
// Returns: ["Armador", "Soldador"] (array de strings con roles operativos)
// Ejemplo: worker ID 93 → ["Armador", "Soldador"]
// Usado en: P2 (operacion/page.tsx) para filtrar operaciones disponibles
```

**2. getSpoolsParaCancelar() ✅ IMPLEMENTADO (13 Dic)**
```typescript
export async function getSpoolsParaCancelar(
  operacion: string,
  workerId: number
): Promise<Spool[]>
// GET /api/spools/cancelar?operacion={op}&worker_id={id}
// Returns: Spools EN_PROGRESO (estado 0.1) del worker para esa operación
// Ejemplo: operacion='ARM', workerId=93 → [spool1, spool2] (solo los iniciados por worker 93)
// Usado en: P4 (seleccionar-spool/page.tsx) para tipo='cancelar'
// Validación backend: Ownership - solo spools iniciados por este worker
```

**3. cancelarAccion() ✅ IMPLEMENTADO (13 Dic)**
```typescript
export async function cancelarAccion(payload: ActionPayload): Promise<void>
// POST /api/cancelar-accion
// Payload: { worker_id: number, operacion: 'ARM' | 'SOLD', tag_spool: string }
// Revierte: Estado 0.1 → 0 (EN_PROGRESO → PENDIENTE)
// Metadata: Registra evento CANCELAR_ARM o CANCELAR_SOLD
// Errores:
//   - 404: Spool no existe
//   - 400: Estado inválido (no está EN_PROGRESO)
//   - 403: Ownership violation (worker no inició este spool)
// Usado en: P5 (confirmar/page.tsx) cuando tipo='cancelar'
```

**4. iniciarAccionBatch() 🔴 PENDIENTE**
```typescript
function iniciarAccionBatch(payload: BatchActionRequest): Promise<BatchActionResponse>
// POST /api/iniciar-accion-batch
```

**5. completarAccionBatch() 🔴 PENDIENTE**
```typescript
function completarAccionBatch(payload: BatchActionRequest): Promise<BatchActionResponse>
// POST /api/completar-accion-batch
```

### 5.3. Interfaces Batch

```typescript
interface BatchActionRequest {
  worker_id: number;         // v2.0: worker_id (NO worker_nombre)
  operacion: string;         // "ARM" | "SOLD" | "METROLOGIA"
  tag_spools: string[];      // Hasta 50 spools
}

interface SpoolActionResult {
  tag_spool: string;
  success: boolean;
  message: string;
  error_code?: string;
}

interface BatchActionResponse {
  total: number;
  exitosos: number;
  fallidos: number;
  resultados: SpoolActionResult[];
}
```

---

## 6. Types (lib/types.ts)

### 6.1. Types v2.0 - Breaking Changes

**ActionPayload - ⚠️ BREAKING CHANGE (13 Dic 2025):**
```typescript
// v1.0 (DEPRECATED)
interface ActionPayload {
  worker_nombre: string;        // ❌ ELIMINADO
  operacion: 'ARM' | 'SOLD';
  tag_spool: string;
}

// v2.0 (ACTUAL) ✅
interface ActionPayload {
  worker_id: number;            // ⚠️ BREAKING: worker_nombre → worker_id
  operacion: 'ARM' | 'SOLD';
  tag_spool: string;
  timestamp?: string;           // Para COMPLETAR
}
```

**Worker - BREAKING CHANGE (12 Dic 2025):**
```typescript
// v1.0 (DEPRECATED)
interface Worker {
  nombre: string;
  apellido: string;
  activo: boolean;
}

// v2.0 (ACTUAL) ✅
interface Worker {
  id: number;                   // 🆕 AÑADIDO - requerido para worker_id payload
  nombre: string;
  apellido: string;
  nombre_completo: string;      // 🆕 AÑADIDO - computed field backend
  activo: boolean;
}
```

**Context State - BREAKING CHANGES (12-13 Dic 2025):**
```typescript
// v1.0 (DEPRECATED)
interface AppState {
  worker: string | null;                        // Solo nombre
  tipoInteraccion: 'iniciar' | 'completar';     // 2 tipos
  selectedSpool: Spool | null;                  // Singular
}

// v2.0 (ACTUAL) ✅
interface AppState {
  worker: Worker | null;                                // ⚠️ CAMBIO: Objeto completo
  tipoInteraccion: 'iniciar' | 'completar' | 'cancelar' | null;  // ⚠️ +cancelar
  selectedSpools: Spool[];                              // ⚠️ CAMBIO: Array (batch)
  batchResults: BatchActionResponse | null;             // 🆕 AÑADIDO
}
```

**Spool - METROLOGÍA (opcional nice-to-have):**
```typescript
interface Spool {
  tag_spool: string;
  armado: number;
  soldado: number;
  metrologia?: number;           // 0 | 0.1 | 1.0 (opcional)
  fecha_metrologia?: string;
  metrologo?: string;
}
```

**Impacto Breaking Changes:**
- P1-P6: worker.nombre_completo (antes solo worker string)
- P5: payload.worker_id (antes payload.worker_nombre)
- Context: selectedWorker tipo Worker (antes string)
- Context: tipoInteraccion +cancelar (antes solo iniciar/completar)

---

## 7. Testing E2E

### 7.1. Tests v1.0 (17 tests - sin cambios)

**Archivos:**
- `01-iniciar-arm.spec.ts` - Flow completo INICIAR ARM
- `02-completar-arm.spec.ts` - Flow completo COMPLETAR ARM
- `03-iniciar-sold.spec.ts` - Flow INICIAR SOLD
- `04-completar-sold.spec.ts` - Flow COMPLETAR SOLD
- `05-errors.spec.ts` - Casos error (sin worker, sin spool)
- `06-navigation.spec.ts` - Botones Volver/Cancelar
- `07-timeout.spec.ts` - Auto-redirect 5 seg en P6

### 7.2. Tests Nuevos v2.0 (+3 tests)

**08-multiselect-batch.spec.ts:**
- `test('Seleccionar 5 spools y confirmar batch')`
- `test('Seleccionar todos y deseleccionar todos')`
- `test('Batch con errores parciales')`

**09-cancelar.spec.ts:**
- `test('Cancelar acción EN_PROGRESO')`
- `test('CANCELAR no disponible si spool PENDIENTE')`

**10-busqueda-spool.spec.ts:**
- `test('Búsqueda TAG_SPOOL filtra lista en tiempo real')`
- `test('Búsqueda sin resultados muestra mensaje')`

**Total v2.0:** 20 tests E2E

---

## 8. Deployment Vercel

### 8.1. Variables de Entorno

```bash
# .env.local (desarrollo)
NEXT_PUBLIC_API_URL=http://localhost:8000

# Vercel (producción)
NEXT_PUBLIC_API_URL=https://zeues-backend-mvp-production.up.railway.app
```

### 8.2. Comandos Deploy

```bash
# Validación pre-deploy (MUST pass)
npm run lint            # 0 errores, 0 warnings
npx tsc --noEmit        # 0 errores TypeScript
npm run build           # Build exitoso
npx playwright test     # 20 tests passing

# Deploy Vercel
vercel --prod

# Configurar env var Vercel
vercel env add NEXT_PUBLIC_API_URL production
# Value: https://zeues-backend-mvp-production.up.railway.app

# Redeploy con nueva env
vercel --prod --yes
```

**URLs Producción:**
- Frontend: https://zeues-frontend.vercel.app
- Backend API: https://zeues-backend-mvp-production.up.railway.app

---

## 9. Admin Panel (OPCIONAL - Nice-to-have)

**Nota:** Admin Panel NO es prioritario para v2.0 MVP. Solo implementar si queda tiempo.

### 9.1. Componentes Admin

**ProtectedRoute:**
```typescript
function ProtectedRoute({
  children,
  allowedRoles
}: {
  children: ReactNode;
  allowedRoles: RoleEnum[];
}): JSX.Element | null
```

**AdminUsuariosPage:**
- CRUD usuarios (crear, cambiar rol, desactivar)
- Tabla con columnas: Email, Nombre, Rol, Estado, Acciones
- Protegido: `allowedRoles={[RoleEnum.ADMINISTRADOR]}`

### 9.2. API Admin

```typescript
// lib/api.ts - Admin functions
function getUsers(): Promise<User[]>
function createUser(payload: CreateUserRequest): Promise<User>
function updateUserRole(email: string, newRole: RoleEnum): Promise<void>
function desactivarUsuario(email: string): Promise<void>
```

---

## 10. Roadmap Implementación

### DÍA 2 Frontend (12-13 Dic 2025) 🔴 PENDIENTE

**Prioridad 1 (Crítico):**
1. **P2 - Filtrado Roles** (2 horas)
   - Implementar getWorkerRoles() en api.ts
   - useEffect fetch roles + filtrar botones OPERACION_CONFIG

2. **P3 - Botón CANCELAR** (1 hora)
   - Añadir tercer botón amarillo
   - Implementar cancelarAccion() en api.ts

3. **P4 - Multiselect** (4 horas)
   - Crear Checkbox.tsx component
   - Cambiar state: selectedSpool → selectedSpools[]
   - Implementar selectAll/deselectAll
   - UI: Contador + botones superior

4. **P5/P6 - Batch** (3 horas)
   - Lógica isBatch en P5
   - Implementar iniciarAccionBatch/completarAccionBatch en api.ts
   - P6: Renderizar exitosos/fallidos

**Prioridad 2 (Importante):**
5. **P4 - Búsqueda TAG_SPOOL** (2 horas)
   - Input búsqueda con filtro en tiempo real
   - Highlight resultados

**Total DÍA 2:** ~12 horas desarrollo

### DÍA 3 Deploy (13-14 Dic 2025) 🔴 PENDIENTE

1. **Tests E2E +3** (3 horas)
   - 08-multiselect-batch.spec.ts
   - 09-cancelar.spec.ts
   - 10-busqueda-spool.spec.ts

2. **Deploy Vercel v2.0** (1 hora)
   - Build + lint + tsc pass
   - Deploy production
   - Smoke tests

**Total DÍA 3:** ~4 horas

---

---

## 11. Changelog Técnico - DÍA 2 Frontend

### P3 CANCELAR + Breaking Change worker_id - COMPLETADO ✅ (13 Dic 2025)

**Breaking Change CRÍTICO:**

| Cambio | v1.0 (Deprecated) | v2.0 (Actual) |
|--------|-------------------|---------------|
| ActionPayload.worker_nombre | `string` | ❌ ELIMINADO |
| ActionPayload.worker_id | No existía | `number` ✅ AÑADIDO |
| Context.selectedTipo | 'iniciar' \| 'completar' | 'iniciar' \| 'completar' \| 'cancelar' |
| Button variants | 3 (primary, completar, cancel) | 4 (+cancelar amarillo) ✅ |

**Archivos Modificados (9 total - sesión 2):**

| Archivo | Cambios | Líneas |
|---------|---------|--------|
| lib/types.ts | ActionPayload: worker_nombre → worker_id | ~5 |
| lib/context.tsx | selectedTipo: +cancelar | ~3 |
| lib/api.ts | +getSpoolsParaCancelar() + cancelarAccion() + JSDoc actualizado | ~100 |
| components/Button.tsx | +variant cancelar (bg-yellow-600) | ~3 |
| app/tipo-interaccion/page.tsx | P3: +botón CANCELAR amarillo | ~20 |
| app/seleccionar-spool/page.tsx | P4: +condicional getSpoolsParaCancelar | ~15 |
| app/confirmar/page.tsx | P5: payload worker_id + lógica 3 tipos | ~40 |
| app/exito/page.tsx | P6: mensajería dinámica CANCELAR (warning) | ~30 |

**Total:** ~216 líneas modificadas + 9 archivos (acumulado DÍA 2: 18 archivos, ~359 líneas)

**Nuevas Funciones API (+2):**

| Función | Endpoint | Descripción | Estado |
|---------|----------|-------------|--------|
| getSpoolsParaCancelar() | GET /api/spools/cancelar | Spools EN_PROGRESO (0.1) del worker | ✅ Implementado |
| cancelarAccion() | POST /api/cancelar-accion | Revertir estado 0.1 → 0 + metadata | ✅ Implementado |

**Flujo CANCELAR Implementado:**
```
P1 (Worker) → P2 (Operación según roles)
→ P3 (Click CANCELAR amarillo) → P4 (Spools 0.1 del worker)
→ P5 (Confirmar CANCELAR con worker_id) → P6 (Warning amarillo + "PENDIENTE")
→ Auto-redirect P1 (5 seg)
```

**Validación Backend Documentada:**
- 404: Spool no existe
- 400: Estado inválido (no está EN_PROGRESO)
- 403: Ownership violation (worker no inició este spool)

**Validación Completa:**
- ✅ npm run lint - 0 errores, 0 warnings
- ✅ npx tsc --noEmit - 0 errores TypeScript
- ✅ Flujo CANCELAR completo funcional (P1-P6)
- 🔴 Tests E2E pendientes (+1 CANCELAR flow)

**TypeScript Strict Compliance:**
- ✅ ActionPayload tipado explícito (worker_id: number)
- ✅ Condicionales tipo guardados ('iniciar' | 'completar' | 'cancelar')
- ✅ JSDoc actualizado en api.ts con ejemplos worker_id
- ✅ 0 usos de `any`

**Progreso v2.0:**
- DÍA 2 Frontend: 50% completado (2/4 features must-have)
- Total v2.0: ~85% (Backend 100% + Frontend 50% + Deploy 0%)

---

### P2 Filtrado por Roles - COMPLETADO ✅ (12 Dic 2025)

**Breaking Changes:**
- Worker interface: +id, +nombre_completo
- Context selectedWorker: string → Worker object
- API calls: worker.id para endpoints

**Archivos Modificados:** 9 archivos, ~143 líneas

**Nueva Función API:**
- getWorkerRoles(workerId: number): Promise<string[]>

**Progreso:** DÍA 2 Frontend 25% (1/4 features)

---

**FIN - proyecto-v2-frontend.md - ZEUES v2.0 Frontend - Versión 2.0 - 13 Dic 2025 01:00**

**Resumen ACTUALIZADO:**
- Frontend 50% completado (P2 roles ✅ + P3 CANCELAR ✅)
- 6 componentes (+1 variant Button cancelar, Checkbox pendiente)
- 7 páginas (7 modificadas - todas actualizadas)
- 9 API functions (+3 nuevas: getWorkerRoles, getSpoolsParaCancelar, cancelarAccion)
- 17 tests E2E (+3 nuevos pendientes = 20 target)
- TypeScript estricto mantenido (NO `any`)
- Mobile-first preservado (botones h-16/h-20)
- **Breaking change crítico:** ActionPayload worker_id (impacto P5)

**Próximo Crítico (13 Dic):**
1. P4 Multiselect UI (checkboxes + select all) - 3-4h
2. P4 Búsqueda TAG_SPOOL (filtrado tiempo real) - 1-2h
3. P5/P6 Batch operations (confirmación + resultados) - 2-3h
4. Tests E2E +3 nuevos - 2-3h
5. Deploy Vercel v2.0 - 30min

**Total pendiente:** ~50% frontend (8-12h trabajo restante)
