# ZEUES Frontend - Arquitectura y Estado del Proyecto

**Sistema de Trazabilidad para Manufactura de Cañerías - Frontend Web App**

Última actualización: 10 Nov 2025 - DÍA 3 COMPLETADO
Estado: EN DESARROLLO - 60% completado (3/6 días - adelantado)

---

## Documentación Relacionada

Este documento forma parte del sistema de documentación del proyecto ZEUES:

**Contexto del Proyecto:**
- **[proyecto.md](./proyecto.md)** - Especificación completa del MVP (visión producto, user stories, flujos de usuario)

**Documentos de Backend:**
- **[proyecto-backend.md](./proyecto-backend.md)** - Documentación técnica completa del backend (incluye especificación de los 6 endpoints API)
- **[proyecto-backend-api.md](./proyecto-backend-api.md)** - Plan ejecución DÍA 3: Implementación API Layer

**Documentos de Frontend:**
- **[proyecto-frontend-ui.md](./proyecto-frontend-ui.md)** - **Implementación UI detallada** (código completo de componentes y páginas DÍA 1-3)
- **[proyecto-frontend-api.md](./proyecto-frontend-api.md)** - **Plan integración API** (DÍA 4: reemplazo mock data con backend real)

**Relación con este documento:**
- Este documento (`proyecto-frontend.md`) contiene la **arquitectura y estado del frontend**
- Cubre: decisiones técnicas, estructura de proyecto, estado de desarrollo, navegación, componentes overview
- **Estado actual:** DÍA 3 completado (60% - componentes + páginas con mock data), DÍA 4 pendiente (integración API)

**Referencias rápidas:**
- Para entender el **flujo del usuario** → `proyecto.md` (secciones 4-5)
- Para ver **código completo de componentes y páginas** → `proyecto-frontend-ui.md`
- Para integrar con el **backend API real** → `proyecto-frontend-api.md`

---

## 1. Visión y Decisiones de Arquitectura

### 1.1 Stack Seleccionado: React/Next.js + Tailwind CSS

**Stack Técnico:** Next.js 14+ (App Router) + TypeScript + Tailwind CSS + shadcn/ui

**Justificación:**
- **Next.js 14+ (App Router):** Routing file-based automático, SSR/CSR flexible, Server Components, deployment Vercel optimizado
- **TypeScript:** Type safety, mejor DX, integración con backend Python (tipos compartidos), catch errors en compile-time
- **Tailwind CSS:** Rapid prototyping, mobile-first nativo, sin CSS files separados, utility-first para MVP rápido
- **shadcn/ui:** Componentes accesibles pre-construidos (no librería pesada), copiable/customizable, Radix UI bajo el capó

**Beneficios para MVP:**
- Setup rápido (create-next-app + shadcn init = 15 min)
- Routing automático (7 páginas = 7 archivos)
- Deploy zero-config a Vercel
- Mobile-first por defecto (Tailwind)
- Componentes accesibles listos (shadcn/ui)
- Performance excelente (Server Components by default)

**Trade-offs:**
- Learning curve App Router si team no lo conoce (pero docs excelentes)
- Tailwind genera clases largas inline (pero más rápido que CSS files en MVP)
- shadcn/ui copia código (no npm install), pero da control total

**Decisión Final:** Next.js + Tailwind por velocidad de desarrollo MVP (6 días), deployment Vercel 1-click, y stack moderno con futuro escalable.

---

## 2. Estructura del Proyecto Frontend

### 2.1 Arquitectura: Mobile-First + Component-Based

```
zeues-frontend/                          # Root del frontend
├── app/                                 # Next.js 14+ App Router
│   ├── layout.tsx                       # Layout principal (AppProvider, fonts, metadata)
│   ├── page.tsx                         # P1: Identificación (home /)
│   ├── operacion/
│   │   └── page.tsx                     # P2: Seleccionar Operación
│   ├── tipo-interaccion/
│   │   └── page.tsx                     # P3: INICIAR o COMPLETAR
│   ├── seleccionar-spool/
│   │   └── page.tsx                     # P4: Seleccionar Spool (A o B dinámico)
│   ├── confirmar/
│   │   └── page.tsx                     # P5: Confirmar Acción (A o B dinámico)
│   └── exito/
│       └── page.tsx                     # P6: Éxito + timeout 5seg
│
├── components/                          # Componentes reutilizables (3-5 MVP)
│   ├── Button.tsx                       # Botón grande (h-16) con variants
│   ├── Card.tsx                         # Contenedor simple con shadow
│   ├── List.tsx                         # Lista clickeable (spools)
│   ├── Loading.tsx                      # Spinner + texto "Cargando..."
│   └── ErrorMessage.tsx                 # Mensaje error rojo
│
├── lib/                                 # Utilidades y lógica
│   ├── api.ts                           # 6 funciones fetch (workers, spools, actions)
│   ├── context.tsx                      # AppContext (estado global simple)
│   └── types.ts                         # Interfaces TypeScript (Worker, Spool, etc.)
│
├── public/                              # Assets estáticos
│   └── favicon.ico
│
├── styles/
│   └── globals.css                      # Tailwind imports + custom styles mínimos
│
├── .env.local                           # Variables entorno desarrollo
├── .env.production                      # Variables entorno producción
├── .gitignore                           # Ignora node_modules, .next, .env*
├── next.config.js                       # Config Next.js (CORS, env vars)
├── package.json                         # Dependencias npm
├── tailwind.config.ts                   # Config Tailwind (colores custom)
├── tsconfig.json                        # Config TypeScript
└── README.md                            # Instrucciones setup frontend
```

**Total:** ~20 archivos (7 páginas + 5 componentes + 3 lib + 5 config)

**Responsabilidades por Capa:**

1. **app/ (Páginas):** Lógica de cada pantalla, API calls, navegación, estado local (useState)
2. **components/ (UI):** Componentes reutilizables simples, props básicos, estilos Tailwind inline
3. **lib/ (Utilidades):** API client (fetch), Context (estado global), tipos TypeScript
4. **public/ (Assets):** Iconos, imágenes (mínimos en MVP)
5. **styles/ (Estilos):** Solo globals.css con Tailwind imports

---

## 3. State Management (Context API)

### 3.1 AppContext (/lib/context.tsx)

**Responsabilidad:** Estado global compartido entre páginas (trabajador, operación, tipo, spool).

**Características:**
- Context API simple (NO Redux/Zustand)
- Estado: selectedWorker, selectedOperation, selectedTipo, selectedSpool
- Métodos: setState (actualizar parcial), reset (limpiar todo)
- Provider en layout.tsx (wrapping app completo)

**Tipos:**

```typescript
interface AppState {
  selectedWorker: string | null;
  selectedOperation: 'ARM' | 'SOLD' | null;
  selectedTipo: 'iniciar' | 'completar' | null;
  selectedSpool: string | null;
}

interface AppContextType {
  state: AppState;
  setState: (newState: Partial<AppState>) => void;
  reset: () => void;
}
```

**Uso:**

```tsx
// Actualizar estado parcial
const { setState } = useAppState();
setState({ selectedWorker: 'Juan Pérez' });

// Leer estado
const { state } = useAppState();
console.log(state.selectedWorker); // "Juan Pérez"

// Resetear todo
const { reset } = useAppState();
reset(); // Vuelve a null todos los valores
```

---

## 4. Integración API Backend (6 endpoints)

### 4.1 API Client (/lib/api.ts)

**Responsabilidad:** Cliente HTTP simple con fetch nativo para conectar con backend FastAPI.

**Características:**
- Fetch nativo (NO axios)
- Error handling básico (try/catch)
- Base URL configurable (env var)
- Tipos TypeScript para requests/responses
- Manejo especial error 403 (ownership)

**Endpoints Implementados:**

| Método | Endpoint | Descripción | Usado en |
|--------|----------|-------------|----------|
| GET | /api/workers | Lista trabajadores activos | P1 |
| GET | /api/spools/iniciar?operacion={ARM\|SOLD} | Spools disponibles iniciar (V/W=0) | P4A |
| GET | /api/spools/completar?operacion={ARM\|SOLD}&worker_nombre={nombre} | Spools propios completar (V/W=0.1) | P4B |
| POST | /api/iniciar-accion | Iniciar acción (V/W→0.1, BC/BE=nombre) | P5A |
| POST | /api/completar-accion | Completar acción (V/W→1.0, BB/BD=fecha) | P5B |
| GET | /api/health | Health check backend | - |

**Interfaces TypeScript:**

```typescript
export interface Worker {
  nombre: string;
  apellido?: string;
  activo: boolean;
  nombre_completo: string;
}

export interface Spool {
  tag_spool: string;
  arm: number;
  sold: number;
  proyecto?: string;
  fecha_materiales?: string;
  fecha_armado?: string;
  armador?: string;
  fecha_soldadura?: string;
  soldador?: string;
}

export interface ActionPayload {
  worker_nombre: string;
  operacion: 'ARM' | 'SOLD';
  tag_spool: string;
  timestamp?: string;
}

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

**Ejemplo Implementación:**

```typescript
const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

export async function getWorkers(): Promise<Worker[]> {
  try {
    const res = await fetch(`${API_URL}/api/workers`);
    if (!res.ok) throw new Error('Error al obtener trabajadores');
    const data = await res.json();
    return data.workers;
  } catch (error) {
    console.error('getWorkers error:', error);
    throw new Error('No se pudieron cargar los trabajadores');
  }
}
```

**Configuración Env Vars:**

```bash
# .env.local (desarrollo)
NEXT_PUBLIC_API_URL=http://localhost:8000

# .env.production (producción)
NEXT_PUBLIC_API_URL=https://zeues-backend.up.railway.app
```

---

## 5. Navegación y Flujos (Next.js App Router)

### 5.1 Flujo INICIAR (P1→P2→P3→P4A→P5A→P6→P1)

**Diagrama de Navegación:**

```
┌──────────────┐
│ P1: Inicio   │ → Selecciona trabajador
│ /            │    setState({ selectedWorker })
└──────┬───────┘    router.push('/operacion')
       │
       v
┌──────────────┐
│ P2: Operación│ → Selecciona ARM/SOLD
│ /operacion   │    setState({ selectedOperation })
└──────┬───────┘    router.push('/tipo-interaccion')
       │
       v
┌──────────────┐
│ P3: Tipo     │ → Click INICIAR ACCIÓN (cyan)
│ /tipo-inter  │    setState({ selectedTipo: 'iniciar' })
└──────┬───────┘    router.push('/seleccionar-spool?tipo=iniciar')
       │
       v
┌──────────────┐
│ P4A: Spool   │ → GET /api/spools/iniciar
│ /seleccionar │    Muestra spools disponibles (V/W=0, dependencias OK)
│ ?tipo=iniciar│    Click spool → setState({ selectedSpool })
└──────┬───────┘    router.push('/confirmar?tipo=iniciar')
       │
       v
┌──────────────┐
│ P5A: Confirmar│ → Muestra resumen
│ /confirmar   │    Click CONFIRMAR (cyan)
│ ?tipo=iniciar│    POST /api/iniciar-accion
└──────┬───────┘    Si éxito → router.push('/exito')
       │
       v
┌──────────────┐
│ P6: Éxito    │ → Muestra checkmark verde
│ /exito       │    Timeout 5seg → reset() + router.push('/')
└──────┬───────┘    Botón "Registrar Otra" → reset() + router.push('/')
       │
       v
┌──────────────┐
│ P1: Inicio   │ (LOOP)
└──────────────┘
```

**Estado en Context durante Flujo INICIAR:**

| Paso | selectedWorker | selectedOperation | selectedTipo | selectedSpool |
|------|----------------|-------------------|--------------|---------------|
| P1   | null           | null              | null         | null          |
| P2   | "Juan Pérez"   | null              | null         | null          |
| P3   | "Juan Pérez"   | "ARM"             | null         | null          |
| P4A  | "Juan Pérez"   | "ARM"             | "iniciar"    | null          |
| P5A  | "Juan Pérez"   | "ARM"             | "iniciar"    | "MK-123"      |
| P6   | "Juan Pérez"   | "ARM"             | "iniciar"    | "MK-123"      |
| P1   | null           | null              | null         | null          |

---

### 5.2 Flujo COMPLETAR (P1→P2→P3→P4B→P5B→P6→P1)

**Diferencias clave con INICIAR:**
- **P3:** Click "✅ COMPLETAR ACCIÓN" (verde)
- **P4B:** GET /api/spools/completar → Solo MIS spools (V/W=0.1, BC/BE=mi nombre)
- **P5B:** Resumen incluye fecha actual, botón verde "COMPLETAR"
- **P5B:** POST /api/completar-accion → Si 403: ErrorMessage ownership

**Validación Crítica Ownership:**
- Backend valida que `worker_nombre` === BC (ARM) o BE (SOLD)
- Si no coincide → 403 FORBIDDEN → Frontend muestra error claro
- Filtro en P4B ya previene mostrar spools de otros (defensa en profundidad)

---

### 5.3 Navegación Especial

**Botón Volver:**
- Disponible en: P2, P3, P4, P5
- Acción: `router.back()` - Vuelve a página anterior
- Estado: Preservado (NO se pierde)

**Botón Cancelar:**
- Disponible en: P5 (confirmación)
- Acción: Confirmación → `reset()` + `router.push('/')`
- Estado: Reseteado (pierde todo)

**Timeout Automático:**
- Página: P6 (éxito)
- Duración: 5 segundos
- Acción: `reset()` + `router.push('/')`
- Cancelable: Sí (click "Registrar Otra" o "Finalizar" cancela timer)

---

## 6. Estilos y Diseño (Tailwind CSS)

### 6.1 Paleta de Colores ZEUES

**Configuración Tailwind:**

```javascript
// tailwind.config.ts
colors: {
  zeues: {
    orange: '#FF5B00',        // Principal
    'orange-dark': '#E64A19', // Hover
    blue: '#0A7EA4',          // Secundario
    cyan: '#0891B2',          // INICIAR
    green: '#16A34A',         // COMPLETAR
    red: '#DC2626',           // Error
    warning: '#EA580C',       // Warning
  },
}
```

**Uso en Componentes:**

| Color | Uso | Clase Tailwind |
|-------|-----|----------------|
| Naranja #FF5B00 | Header, botones primarios | `bg-[#FF5B00]` |
| Cyan #0891B2 | INICIAR acción, P3/P5A/P6A | `bg-cyan-600 hover:bg-cyan-700` |
| Verde #16A34A | COMPLETAR acción, P3/P5B/P6B | `bg-green-600 hover:bg-green-700` |
| Rojo #DC2626 | Errores, validaciones fallidas | `bg-red-50 border-red-200 text-red-700` |
| Gris #F8FAFC | Fondo app | `bg-slate-50` |

---

### 6.2 Responsive Mobile-First

**Breakpoints Tailwind:**
- `sm`: 640px (tablet vertical)
- `md`: 768px (tablet horizontal)
- `lg`: 1024px (desktop pequeño)

**Estrategia MVP:**
- Diseñar para móvil primero (sin prefijo)
- Agregar `md:` solo si necesario
- Target principal: tablet 10" (768px-1024px)

**Ejemplo:**

```tsx
<div className="grid grid-cols-1 md:grid-cols-2 gap-4">
  {/* 1 columna móvil, 2 columnas tablet */}
</div>
```

---

## 7. Testing Strategy

### 7.1 Testing Manual MVP (Suficiente para 6 días)

**Filosofía:** Testing manual es suficiente para MVP simple con 7 pantallas. Tests automatizados requieren tiempo/setup que no tenemos.

**Checklist de Validación (DÍA 6):**

```
[ ] Flujo INICIAR ARM completo (P1→P6→P1)
[ ] Flujo COMPLETAR ARM completo (P1→P6→P1)
[ ] Flujo INICIAR SOLD completo
[ ] Flujo COMPLETAR SOLD completo
[ ] Ownership validation funciona (error 403)
[ ] Botones Volver mantienen estado
[ ] Botón Cancelar resetea estado
[ ] Timeout 5seg funciona en P6
[ ] Loading states visibles durante API calls
[ ] Error messages claros y user-friendly
[ ] Google Sheets actualizado correctamente
[ ] Botones grandes clickeables (h-16)
[ ] Texto legible (text-xl)
[ ] Contraste alto (colores correctos)
[ ] Responsive tablet 10"
[ ] Tiempo total < 30 seg por interacción
```

**Referencia Completa:** Ver `TESTING-E2E.md` para 12 test cases detallados.

---

### 7.2 Tests Automatizados (FASE 2 - Post-MVP)

**NO implementar en MVP. Documentar para post-lanzamiento:**

**Testing Stack Recomendado (Fase 2):**
- Jest + React Testing Library (tests unitarios componentes)
- Playwright (tests E2E flujos completos)
- MSW (Mock Service Worker para API mocks)

**Tests Críticos a Implementar (Fase 2):**
1. Unit tests componentes (Button, Card, List)
2. Integration tests páginas (P1-P6)
3. E2E tests flujos completos (INICIAR/COMPLETAR)
4. E2E test ownership validation (403 error)
5. Visual regression tests (Chromatic/Percy)

**Tiempo Estimado Fase 2:** 2-3 días adicionales

---

## 8. Deployment (Vercel)

### 8.1 Vercel Configuration

**Por qué Vercel:**
- Deploy zero-config para Next.js
- Free tier generoso (100GB bandwidth/mes)
- CI/CD automático desde GitHub
- Preview deployments por PR
- Edge Network global (CDN)
- Environment variables UI fácil

**Setup Deployment:**

```bash
# 1. Install Vercel CLI
npm i -g vercel

# 2. Login Vercel
vercel login

# 3. Link proyecto
vercel link

# 4. Deploy a producción
vercel --prod
```

---

### 8.2 Environment Variables

**Variables Producción (Vercel Dashboard):**

```bash
# Backend API URL (Railway)
NEXT_PUBLIC_API_URL=https://zeues-backend.up.railway.app
```

**Configuración en Vercel:**
1. Dashboard → Proyecto → Settings → Environment Variables
2. Agregar `NEXT_PUBLIC_API_URL` con valor Railway URL
3. Select: Production, Preview, Development
4. Save

---

### 8.3 Deployment Checklist

**Pre-Deploy:**
```
[ ] Backend deployed en Railway (API URL disponible)
[ ] Env var NEXT_PUBLIC_API_URL configurada en Vercel
[ ] Testing manual completo en localhost
[ ] Google Sheets TESTING funcionando
[ ] Ownership validation testeada
[ ] Build local exitoso (npm run build)
[ ] No console.errors en navegador
```

**Deploy Production:**
```
[ ] Push código a main branch (GitHub)
[ ] Vercel auto-deploy triggered
[ ] Build exitoso en Vercel dashboard
[ ] URL producción accesible
[ ] Testing manual en URL producción
[ ] API calls funcionan (verificar Network tab)
[ ] Google Sheets actualiza correctamente
[ ] Ownership validation funciona en prod
```

**Post-Deploy:**
```
[ ] Cambiar backend a Google Sheets PRODUCCIÓN (no TESTING)
[ ] Notificar admins/trabajadores
[ ] Monitorear logs Vercel primeras 24hrs
[ ] Capacitación usuarios (4 trabajadores + 2 admins)
```

---

## 9. Roadmap de Implementación Frontend (6 días)

### DÍA 1 (10 Nov): Setup + Arquitectura ✅ COMPLETADO

**Responsable:** @frontend-architect
**Tiempo:** 2-3 horas
**Estado:** ✅ COMPLETADO (10 Nov 2025)

**Tareas Completadas:**
1. ✅ Proyecto Next.js 14.2.33 creado manualmente (estructura completa)
2. ✅ 385 dependencias instaladas (next, react, typescript, tailwindcss, eslint)
3. ✅ Tailwind config con paleta ZEUES custom (#FF5B00, #0891B2, #16A34A)
4. ✅ Estructura carpetas completa:
   - `app/` (7 páginas placeholder con routing automático)
   - `components/` (directorio preparado)
   - `lib/` (api.ts, types.ts, context.tsx preparados)
5. ✅ Variables entorno .env.local configuradas (NEXT_PUBLIC_API_URL)
6. ✅ Git repository inicializado + commit inicial (21 archivos, commit 05cb9d4)
7. ✅ README.md frontend con documentación completa
8. ✅ .gitignore actualizado para frontend

**Entregables Completados:**
- ✅ Proyecto Next.js 14.2.33 configurado y validado
- ✅ 7 páginas placeholder funcionando con routing automático
- ✅ Tailwind configurado con colores ZEUES custom
- ✅ Build exitoso (npm run build)
- ✅ Dev server funcionando en puerto 3001
- ✅ Git commit inicial creado

**Criterio Éxito Validado:**
- ✅ `npm run dev` funciona en localhost:3001
- ✅ Todas las rutas accesibles: /, /operacion, /tipo-interaccion, /seleccionar-spool, /confirmar, /exito
- ✅ Colores custom Tailwind aplicados y validados
- ✅ Build completo sin errores

---

### DÍA 2 (10 Nov): Componentes Base + Primeras Páginas ✅ COMPLETADO

**Responsable:** @ui-builder-mvp
**Tiempo:** 6-7 horas
**Estado:** ✅ COMPLETADO (10 Nov 2025)

**Tareas Completadas:**
1. ✅ Componentes base creados (4-5 horas):
   - Button.tsx (variants: primary, iniciar, completar, cancel)
   - Card.tsx
   - List.tsx
   - Loading.tsx
   - ErrorMessage.tsx
2. ✅ P1 - Identificación implementada (2 horas):
   - Grid botones trabajadores (mock data)
   - Loading state
   - Error handling
3. ✅ P2 - Operación implementada (1 hora):
   - Botones ARM/SOLD
   - Botón Volver
   - Saludo con nombre trabajador
4. ✅ P3 - Tipo Interacción implementada (2 horas):
   - Botones INICIAR (cyan) y COMPLETAR (verde)
   - Descripciones breves
   - Botón Volver
5. ✅ Context API implementado (2 horas):
   - `/lib/context.tsx` con AppProvider
   - Estado: selectedWorker, selectedOperation, selectedTipo, selectedSpool
   - Métodos: setState, reset
   - Integrar en layout.tsx
6. ✅ Navegación P1→P2→P3 funcional (1 hora):
   - Click trabajador → setState + router.push
   - Click operación → setState + router.push
   - Click tipo → setState + router.push

**Entregables Completados:**
- ✅ 5 componentes base funcionando
- ✅ 3 páginas completas (P1, P2, P3)
- ✅ Context API implementado
- ✅ Navegación P1→P2→P3 funcional

**Criterio Éxito Validado:**
- ✅ Componentes reutilizables y estilizados
- ✅ P1→P2→P3 navegación fluida
- ✅ Estado preservado en Context
- ✅ Botones Volver funcionan

---

### DÍA 3 (10 Nov): Últimas Páginas + Mock Data ✅ COMPLETADO

**Responsable:** @ui-builder-mvp
**Tiempo:** 6-7 horas
**Estado:** ✅ COMPLETADO (10 Nov 2025)

**Tareas Completadas:**
1. ✅ P4 - Seleccionar Spool implementada (2-3 horas):
   - Query param `?tipo=iniciar|completar`
   - Mock data: 20 spools (5 ARM pendiente, 5 SOLD pendiente, 4x2 en progreso, 2 completados)
   - Filtrado inteligente según tipo y operación:
     - INICIAR ARM: arm=0
     - COMPLETAR ARM: arm=0.1, armador=trabajador actual
     - INICIAR SOLD: arm=1.0, sold=0
     - COMPLETAR SOLD: sold=0.1, soldador=trabajador actual
   - List component con spools
   - Click spool → setState + router.push
   - Estado empty: "No hay spools disponibles"
2. ✅ P5 - Confirmar implementada (2-3 horas):
   - Query param `?tipo=iniciar|completar`
   - Card con resumen (trabajador, operación, spool, fecha si completar)
   - Botón CONFIRMAR con color según tipo (cyan/verde)
   - Botón Cancelar con confirmación
   - Loading simulado (1 seg, mensaje "Actualizando Google Sheets...")
   - Mock success → router.push('/exito')
3. ✅ P6 - Éxito implementada (1-2 horas):
   - Checkmark SVG grande verde
   - Mensaje "¡Acción completada exitosamente!"
   - Countdown 5 segundos visible
   - useEffect → setTimeout → reset() + router.push('/')
   - Botón "Registrar Otra" → reset() + router.push('/')
   - Botón "Finalizar" → reset() + router.push('/')
   - Cleanup timeout en unmount
4. ✅ Suspense boundaries (1 hora):
   - Implementados en P4 y P5 para useSearchParams()
   - Next.js 14 requirement para client components
5. ✅ Build producción exitoso:
   - 0 errores TypeScript
   - 0 warnings ESLint
   - Build completo sin issues

**Entregables Completados:**
- ✅ P4, P5, P6 implementadas y funcionando
- ✅ Mock data con 20 spools cubriendo todos los escenarios
- ✅ Filtrado inteligente de spools (iniciar vs completar, ARM vs SOLD)
- ✅ Validación de propiedad (ownership) en mock data
- ✅ Estados loading, error y empty correctamente manejados
- ✅ Navegación completa P1→P2→P3→P4→P5→P6→P1
- ✅ Suspense boundaries para useSearchParams()
- ✅ Build producción exitoso
- ✅ Guía testing E2E documentada (TESTING-E2E.md)

**Criterio Éxito Validado:**
- ✅ Flujo INICIAR completo navegable con mock data
- ✅ Flujo COMPLETAR completo navegable con mock data
- ✅ Filtrado de spools funciona correctamente
- ✅ Ownership validation lógica implementada
- ✅ Loading/error states visibles
- ✅ Timeout 5seg funciona en P6
- ✅ Build sin errores

---

### DÍA 4 (11 Nov): Integración API Real - PENDIENTE

**Responsables:** @api-integrator + @ui-builder-mvp
**Tiempo:** 1 día (6-7 horas)

**Tareas DÍA 4:**
1. Crear `/lib/api.ts` con 6 funciones (3 horas):
   - getWorkers()
   - getSpoolsParaIniciar()
   - getSpoolsParaCompletar()
   - iniciarAccion()
   - completarAccion()
   - checkHealth()
2. Crear `/lib/types.ts` con interfaces (incluido):
   - Worker, Spool, ActionPayload, ActionResponse
3. Integrar API real en páginas (3-4 horas):
   - P1: Reemplazar MOCK_WORKERS con getWorkers()
   - P4A: Reemplazar mock con getSpoolsParaIniciar()
   - P4B: Reemplazar mock con getSpoolsParaCompletar()
   - P5A: POST iniciarAccion() real
   - P5B: POST completarAccion() real con manejo 403
4. Testing API calls en navegador (1 hora):
   - Verificar Network tab
   - Console.log responses
   - Error handling

**Entregable:**
- `/lib/api.ts` con 6 funciones implementadas
- P1, P4, P5 integradas con API real
- Flujos INICIAR/COMPLETAR funcionando con backend

**Criterio Éxito:**
- GET /api/workers funciona en P1
- GET /api/spools/iniciar funciona en P4A
- GET /api/spools/completar funciona en P4B
- POST /api/iniciar-accion funciona en P5A
- POST /api/completar-accion funciona en P5B
- Error 403 ownership muestra mensaje claro

---

### DÍA 5 (12 Nov): Testing Flujos + Ajustes - PENDIENTE

**Responsables:** @ui-builder-mvp + @api-integrator
**Tiempo:** 1 día (6-7 horas)

**Tareas DÍA 5:**
1. Testing manual flujos completos (3 horas):
   - Flujo INICIAR ARM end-to-end (30 min)
   - Flujo COMPLETAR ARM end-to-end (30 min)
   - Flujo INICIAR SOLD end-to-end (30 min)
   - Flujo COMPLETAR SOLD end-to-end (30 min)
   - Ownership validation (15 min)
   - Error handling (30 min)
2. Verificar Google Sheets actualiza (1 hora):
   - INICIAR: V/W → 0.1, BC/BE = nombre
   - COMPLETAR: V/W → 1.0, BB/BD = fecha
3. Fix bugs detectados (2-3 horas):
   - Priorizar bugs críticos bloqueantes
   - Ajustes UX menores

**Entregable:**
- Flujos INICIAR/COMPLETAR ARM/SOLD testeados
- Google Sheets actualizado correctamente
- Bugs críticos resueltos

**Criterio Éxito:**
- 0 bugs críticos bloqueantes
- Google Sheets se actualiza correctamente
- Ownership validation funciona
- Flujos navegables sin crashes

---

### DÍA 6 (13 Nov): Testing Exhaustivo + Deploy - PENDIENTE

**Responsables:** @navigation-orchestrator + @ui-builder-mvp
**Tiempo:** 1 día (7-8 horas)

**Tareas Navegación (2 horas):**
1. Revisar botones Volver en todas las páginas
2. Implementar botón Cancelar en P5
3. Verificar timeout P6 (5seg exactos, cleanup unmount)
4. Testing navegación completa

**Tareas Testing Manual (3 horas):**
5. Ejecutar checklist completo (16 items)
6. Testing mobile/tablet responsive
7. Fix bugs detectados

**Tareas Deploy (2 horas):**
8. Build local (npm run build)
9. Fix errores build si los hay
10. Push código a GitHub
11. Deploy Vercel (auto desde GitHub)
12. Configurar env vars producción
13. Testing manual en URL producción

**Entregable:**
- Navegación completa funcional
- Testing manual completo (checklist ✓)
- Bugs críticos resueltos
- Frontend deployed en Vercel
- URL producción funcionando

**Criterio Éxito:**
- Checklist testing 100% completado
- 0 bugs críticos bloqueantes
- Deploy Vercel exitoso
- API calls funcionan en producción
- Ownership validation funciona en prod
- Tiempo total por interacción < 30 segundos

---

## 10. Estado Actual del Frontend

**Estado General:** ✅ DÍA 1-3 COMPLETADO (10 Nov 2025) - EN DESARROLLO
**Progreso:** ~60% (3/6 días completados - adelantados)
**Bloqueadores:** Ninguno - backend listo para integración API real

### 10.1 Completado (DÍA 1-3)

**Backend Status:**
- ✅ 6 endpoints API funcionando
- ✅ 10/10 tests E2E passing (100%)
- ✅ Ownership validation implementada
- ✅ Google Sheets TESTING configurado
- ✅ Deployed en Railway (o localhost disponible)

**Frontend - DÍA 1 Completado (10 Nov):**
- ✅ Proyecto Next.js 14.2.33 creado y configurado
- ✅ 7 páginas placeholder con routing automático
- ✅ Tailwind CSS configurado con paleta ZEUES custom
- ✅ Estructura de carpetas completa (app/, components/, lib/)
- ✅ Variables de entorno configuradas (.env.local)
- ✅ Git repository inicializado (commit 05cb9d4)
- ✅ Build exitoso validado
- ✅ Dev server funcionando (puerto 3001)
- ✅ README.md frontend documentado

**Frontend - DÍA 2 Completado (10 Nov):**
- ✅ Componentes base creados (Button, Card, List, Loading, ErrorMessage)
- ✅ P1 - Identificación implementada con mock data
- ✅ P2 - Operación implementada
- ✅ P3 - Tipo Interacción implementada
- ✅ Context API implementado (/lib/context.tsx)
- ✅ Layout.tsx con AppProvider
- ✅ Navegación P1→P2→P3 funcional

**Frontend - DÍA 3 Completado (10 Nov):**
- ✅ P4 - Seleccionar Spool implementada con mock data (20 spools)
- ✅ P5 - Confirmar Acción implementada con resumen
- ✅ P6 - Éxito implementada con countdown 5seg
- ✅ Filtrado inteligente de spools (iniciar vs completar, ARM vs SOLD)
- ✅ Validación de propiedad (ownership) en mock data
- ✅ Estados loading, error y empty correctamente manejados
- ✅ Suspense boundaries para useSearchParams()
- ✅ Build producción exitoso sin errores TypeScript/ESLint
- ✅ Guía testing E2E documentada (TESTING-E2E.md)

---

### 10.2 Pendiente (DÍA 4-6)

**Frontend Pendiente:**
- [ ] API client (/lib/api.ts) con integración real - DÍA 4
- [ ] Reemplazar mock data con API calls reales - DÍA 4
- [ ] Testing flujos completos INICIAR/COMPLETAR - DÍA 4-5
- [ ] Verificar ownership validation con backend - DÍA 5
- [ ] Navegación completa y validaciones finales - DÍA 6
- [ ] Testing manual exhaustivo (checklist completo) - DÍA 6
- [ ] Deploy Vercel - DÍA 6

---

### 10.3 Recursos Disponibles

- ✅ Documentación completa (proyecto.md, proyecto-backend.md, proyecto-frontend.md, proyecto-frontend-ui.md)
- ✅ Wireframes conceptuales
- ✅ Paleta de colores definida (#FF5B00, #0891B2, #16A34A)
- ✅ API endpoints documentados
- ✅ Agentes frontend definidos (4 CORE)
- ✅ Proyecto Next.js configurado y validado
- ✅ TESTING-E2E.md con 12 test cases

**Próximo Paso:** DÍA 4 (11 Nov) - @api-integrator integra API real del backend (reemplazar mock data)

---

## 11. Apéndices

### A. Comandos Útiles

**Desarrollo:**
```bash
# Instalar dependencias
npm install

# Dev server
npm run dev              # http://localhost:3001

# Build producción
npm run build

# Preview build
npm run start

# Linter
npm run lint
```

**Deployment:**
```bash
# Vercel CLI
npm i -g vercel
vercel login
vercel link
vercel --prod

# Ver logs Vercel
vercel logs

# Env vars
vercel env add NEXT_PUBLIC_API_URL production
```

**Testing API:**
```bash
# Health check backend
curl http://localhost:8000/api/health

# Get workers
curl http://localhost:8000/api/workers

# Get spools iniciar ARM
curl "http://localhost:8000/api/spools/iniciar?operacion=ARM"
```

---

### B. Variables de Entorno

**Desarrollo (.env.local):**
```bash
NEXT_PUBLIC_API_URL=http://localhost:8000
```

**Producción (.env.production o Vercel Dashboard):**
```bash
NEXT_PUBLIC_API_URL=https://zeues-backend.up.railway.app
```

**IMPORTANTE:** Variables que empiezan con `NEXT_PUBLIC_` son accesibles en browser (client-side). NO poner secrets aquí.

---

### C. Dependencies (package.json)

**Dependencias Principales:**
```json
{
  "dependencies": {
    "next": "14.2.33",
    "react": "^18.2.0",
    "react-dom": "^18.2.0",
    "typescript": "^5.0.0"
  },
  "devDependencies": {
    "@types/node": "^20.0.0",
    "@types/react": "^18.2.0",
    "@types/react-dom": "^18.2.0",
    "autoprefixer": "^10.0.0",
    "postcss": "^8.0.0",
    "tailwindcss": "^3.3.0",
    "eslint": "^8.0.0",
    "eslint-config-next": "14.2.33"
  }
}
```

**NO instalar en MVP:**
- axios (usar fetch nativo)
- Redux/Zustand (usar Context)
- react-hook-form (validaciones inline)
- framer-motion (animaciones complejas)
- Jest/Testing Library (testing manual)

---

### D. Checklist Final Pre-Lanzamiento

**Funcionalidad:**
```
[ ] Flujo INICIAR ARM funcional end-to-end
[ ] Flujo COMPLETAR ARM funcional end-to-end
[ ] Flujo INICIAR SOLD funcional end-to-end
[ ] Flujo COMPLETAR SOLD funcional end-to-end
[ ] Ownership validation funciona (error 403 mostrado)
[ ] Navegación Volver mantiene estado
[ ] Navegación Cancelar resetea estado
[ ] Timeout 5seg P6 funciona
[ ] Loading states visibles
[ ] Error messages claros
[ ] Google Sheets actualiza correctamente
```

**UI/UX:**
```
[ ] Botones grandes (h-16 = 64px)
[ ] Texto legible (text-xl = 20px)
[ ] Contraste alto (colores correctos)
[ ] Paleta ZEUES aplicada (#FF5B00, #0891B2, #16A34A)
[ ] Mobile-first responsive tablet 10"
[ ] Feedback visual inmediato
[ ] < 30 segundos por interacción
```

**Deployment:**
```
[ ] Backend deployed Railway (API URL disponible)
[ ] Frontend deployed Vercel (URL pública)
[ ] Env vars configuradas
[ ] Build exitoso sin errores
[ ] API calls funcionan en producción
[ ] Google Sheets TESTING actualizado
[ ] Ownership validation funciona en prod
```

---

**FIN - proyecto-frontend.md - Arquitectura y Estado - v3.0 - 10 Nov 2025**

**Resumen Ejecutivo:**
- ✅ DÍA 1-3 COMPLETADOS (60% progreso - adelantado)
- ✅ Stack: Next.js 14.2.33 + TypeScript + Tailwind CSS
- ✅ 7 páginas completas con mock data
- ✅ 5 componentes reutilizables
- ✅ Context API simple
- ✅ Build producción exitoso
- ⏳ Integración API real pendiente (DÍA 4)
- ⏳ Deploy Vercel pendiente (DÍA 6)

**Próximo Paso:** DÍA 4 (11 Nov 2025) - @api-integrator integra API real

**Referencias:**
- Detalles de componentes UI: Ver `proyecto-frontend-ui.md`
- Testing E2E: Ver `TESTING-E2E.md`
- Backend: Ver `proyecto-backend.md`
- Proyecto general: Ver `proyecto.md`
