# Agentes de Desarrollo Frontend - ZEUES MVP

**Versión Simplificada para MVP con UI/UX Simple**

Definición de 4 agentes CORE para desarrollo rápido de frontend funcional sin sobre-ingeniería.

**Filosofía MVP:** Funcionalidad básica primero, refinamiento después. Evitar complejidad innecesaria.

---

## 🎯 Agentes CORE para MVP (4 esenciales)

Estos son los únicos agentes necesarios para completar el MVP en 6 días (12-17 Nov 2025).

---

## 1. frontend-architect 🏗️ [CORE MVP]

**Rol:** Arquitecto de Frontend (Versión Simplificada)

**Responsabilidad Única:** Definir estructura básica de carpetas, páginas y componentes

### Tareas Específicas MVP (NO sobre-arquitecturar):
- Crear estructura de carpetas Next.js estándar (app, components, lib, types)
- Definir 7 páginas básicas (P1-P7) con routing simple
- Listar 3-5 componentes reutilizables máximo (Button, Card, List)
- Establecer convención naming simple (kebab-case files, PascalCase components)
- Definir flujo básico de navegación entre pantallas

### 🚫 NO HACER en MVP:
- Arquitecturas complejas (no Redux, no Zustand, no patrones avanzados)
- Hooks personalizados complejos (useState básico suficiente)
- Optimizaciones prematuras
- Diagramas extensos o documentación excesiva

### Cuándo Activar:
- DÍA 1: Antes de escribir cualquier código
- Solo si hay cambio estructural grande (post-MVP)

### Input Esperado:
- 7 pantallas del proyecto.md (P1: Identificación → P7: Éxito)
- 2 flujos (INICIAR y COMPLETAR)
- Wireframes conceptuales del proyecto.md

### Output Esperado (MVP Simple):
- Estructura carpetas básica (5-7 carpetas máximo)
- Lista de 7 páginas con rutas
- Lista de 3-5 componentes reutilizables
- Convención naming (1 párrafo)

**Tiempo Estimado:** 1-2 horas (DÍA 1)

---

## 2. ui-builder-mvp 🎨 [CORE MVP - FUSIONADO]

**Rol:** Constructor de UI + UX Simple + Validaciones Inline (3 en 1)

**Responsabilidad Única:** Implementar componentes y páginas funcionales con estilo básico

**FUSIONA:** ui-builder + ux-specialist + form-validator (simplificados para MVP)

### Tareas Específicas MVP (Simple y Funcional):
- Crear 3-5 componentes React básicos (Button, Card, List, Input, Modal)
- Implementar 7 páginas Next.js con estilos Tailwind inline
- Usar componentes shadcn/ui directamente SIN customización excesiva
- Aplicar paleta de colores del proyecto.md (naranja #FF5B00, cyan #0891B2, verde #16A34A)
- Botones grandes (h-16 = 64px) con text-xl para uso con guantes
- Validaciones inline básicas (campo requerido, mensaje error simple)
- Loading states simples (spinner + texto "Cargando...")
- Feedback visual básico (mensaje éxito/error)

### 🚫 NO HACER en MVP:
- Animaciones complejas (solo transiciones básicas Tailwind)
- Componentes altamente configurables con 20+ props
- Design system completo
- Librerías de validación (react-hook-form, zod, etc.)
- Optimizaciones de re-render
- Storybook o documentación de componentes
- Tests de componentes (FASE 2)

### Cuándo Activar:
- DÍA 2-6: Para cada página o componente nuevo
- Continuamente durante desarrollo

### Input Esperado:
- Wireframes del proyecto.md (P1-P7)
- Paleta de colores del proyecto.md
- Principios: mobile-first, botones grandes, contraste alto

### Output Esperado (MVP Simple):
- Componentes funcionales básicos (Button, Card, List)
- 7 páginas implementadas con estilos inline Tailwind
- Validaciones inline (if/else simples)
- Loading/error states básicos
- Sin documentación extensa (código auto-documentado)

**Ejemplos MVP Simple:**

**Botón básico:**
```tsx
<button className="w-full h-16 bg-orange-600 text-white text-xl font-semibold rounded-lg">
  {children}
</button>
```

**Validación inline simple:**
```tsx
{!selectedWorker && <p className="text-red-600">Selecciona un trabajador</p>}
```

**Loading básico:**
```tsx
{loading && <div className="text-center">Cargando...</div>}
```

**Tiempo Estimado:** 4-5 días (DÍA 2-6)

---

## 3. api-integrator 🔌 [CORE MVP]

**Rol:** Integrador de API (Versión Simplificada)

**Responsabilidad Única:** Conectar frontend con 6 endpoints backend

### Tareas Específicas MVP (Básico y Funcional):
- Crear archivo `/lib/api.ts` con 6 funciones fetch
- Usar fetch nativo (NO axios, NO librerías complejas)
- Implementar error handling básico (try/catch + alert simple)
- Parsear respuestas JSON
- Headers simples (Content-Type: application/json)
- NO autenticación en MVP (solo nombres trabajadores)

### 🚫 NO HACER en MVP:
- Cliente API complejo con interceptors
- Retry automático (FASE 2)
- Timeouts configurables (usar default navegador)
- Caching de requests (backend ya tiene cache)
- Librerías como axios, ky, o tanstack-query

### Cuándo Activar:
- DÍA 4-5: Al implementar integración con backend
- Una vez backend esté deployed (o usar localhost)

### Input Esperado:
- 6 endpoints del proyecto-backend.md:
  1. GET /api/workers
  2. GET /api/spools/iniciar?operacion=ARM|SOLD
  3. GET /api/spools/completar?operacion=...&worker_nombre=...
  4. POST /api/iniciar-accion
  5. POST /api/completar-accion
  6. GET /api/health
- URL base API (localhost:8000 o Railway URL)

### Output Esperado (MVP Simple):
- Archivo `/lib/api.ts` con 6 funciones
- Error handling básico (try/catch)
- Tipos TypeScript simples (interfaces básicas)

**Ejemplo MVP Simple:**

```typescript
// /lib/api.ts
const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

export async function getWorkers() {
  try {
    const res = await fetch(`${API_URL}/api/workers`);
    if (!res.ok) throw new Error('Error al obtener trabajadores');
    return await res.json();
  } catch (error) {
    console.error(error);
    throw error;
  }
}

export async function iniciarAccion(data: { worker_nombre: string; operacion: string; tag_spool: string }) {
  const res = await fetch(`${API_URL}/api/iniciar-accion`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data),
  });
  if (!res.ok) throw new Error('Error al iniciar acción');
  return await res.json();
}
```

**Tiempo Estimado:** 2-3 horas (DÍA 4)

---

## 4. navigation-orchestrator 🗺️ [CORE MVP]

**Rol:** Orquestador de Navegación (Versión Simplificada)

**Responsabilidad Única:** Conectar flujo de navegación entre 7 pantallas

### Tareas Específicas MVP (Routing Básico):
- Implementar routing Next.js App Router con 7 rutas
- Pasar estado entre páginas (URL params o Context simple)
- Implementar botones "Volver" (router.back() o href)
- Implementar botones "Cancelar" (redirect a P1)
- Timeout 5seg después de éxito → redirect a P1
- Preservar selecciones (trabajador, operación) en navegación

### 🚫 NO HACER en MVP:
- Breadcrumbs complejos
- Animaciones de transición entre páginas
- Historial de navegación personalizado
- Deep linking complejo
- Query string params complejos

### Cuándo Activar:
- DÍA 5-6: Al conectar las 7 páginas implementadas
- Después de tener páginas básicas funcionando

### Input Esperado:
- 2 flujos del proyecto.md (INICIAR y COMPLETAR)
- 7 pantallas (P1→P2→P3→P4→P5→P6→P7)
- Reglas de navegación (cuándo Volver, Cancelar, timeout)

### Output Esperado (MVP Simple):
- 7 rutas Next.js configuradas
- Navegación entre pantallas funcional
- Botones Volver/Cancelar trabajando
- Timeout 5seg implementado (setTimeout simple)
- Estado preservado (Context o URL params)

**Ejemplo MVP Simple:**

```tsx
// Botón Volver
<button onClick={() => router.back()}>Volver</button>

// Botón Cancelar
<button onClick={() => router.push('/')}>Cancelar</button>

// Timeout 5seg a inicio
useEffect(() => {
  const timer = setTimeout(() => router.push('/'), 5000);
  return () => clearTimeout(timer);
}, []);

// Pasar datos con Context simple
const [selectedWorker, setSelectedWorker] = useState(null);
```

**Tiempo Estimado:** 2-3 horas (DÍA 6)

---

## 📦 Agentes FASE 2 (Post-MVP)

Estos agentes NO son necesarios para completar el MVP. Se pueden implementar después del lanzamiento inicial.

### 5. state-manager 🔄 [FASE 2]

**Por qué NO en MVP:** useState básico y Context simple son suficientes para 7 pantallas. No necesitamos Redux/Zustand/hooks complejos.

**Cuándo implementar:** Post-MVP si escalamos a 20+ pantallas o estado se vuelve inmanejable.

---

### 6. component-tester 🧪 [FASE 2]

**Por qué NO en MVP:** Testing manual es suficiente para MVP simple con 7 pantallas. Tests automatizados requieren tiempo y setup.

**Cuándo implementar:** Post-MVP cuando tengamos múltiples developers o antes de escalar features.

---

### 7. accessibility-specialist ♿ [FASE 2]

**Por qué NO en MVP:** Seguir principios básicos (contraste, botones grandes) es suficiente. Validación formal WCAG es post-MVP.

**Cuándo implementar:** Antes de certificación o si detectamos problemas de usabilidad serios.

---

## 🚀 Workflow MVP Simplificado (6 días)

### DÍA 1 (12 Nov): Setup + Arquitectura

**Agente:** frontend-architect

**Tareas:**
1. Crear proyecto Next.js 14+ con TypeScript
2. Instalar Tailwind CSS + shadcn/ui
3. Definir estructura carpetas (app/, components/, lib/, types/)
4. Crear 7 rutas vacías (pages/identificacion, pages/operacion, etc.)
5. Configurar env vars (NEXT_PUBLIC_API_URL)

**Entregable:** Proyecto configurado, 7 páginas vacías con routing

**Tiempo:** 2-3 horas

---

### DÍA 2-3 (13-14 Nov): Componentes Base + Primeras Páginas

**Agentes:** ui-builder-mvp

**Tareas DÍA 2:**
1. Crear componentes base (Button, Card, List) con Tailwind
2. Aplicar paleta colores (#FF5B00, #0891B2, #16A34A)
3. Implementar P1 (Identificación) - Grid botones trabajadores
4. Implementar P2 (Operación) - Botones ARM/SOLD

**Tareas DÍA 3:**
5. Implementar P3 (Tipo Interacción) - Botones INICIAR/COMPLETAR
6. Validaciones inline básicas (campo seleccionado)
7. Loading states simples (Cargando...)

**Entregable:** 3 páginas funcionales + componentes base

**Tiempo:** 1.5 días

---

### DÍA 4 (15 Nov): Integración API + Flujo INICIAR

**Agentes:** api-integrator + ui-builder-mvp

**Tareas:**
1. Crear `/lib/api.ts` con 6 funciones fetch
2. Implementar P4A (Seleccionar Spool para Iniciar) + integración GET /spools/iniciar
3. Implementar P5A (Confirmar Iniciar) + integración POST /iniciar-accion
4. Error handling básico (try/catch + alert)

**Entregable:** Flujo INICIAR funcional end-to-end

**Tiempo:** 1 día

---

### DÍA 5 (16 Nov): Flujo COMPLETAR

**Agentes:** api-integrator + ui-builder-mvp

**Tareas:**
1. Implementar P4B (Seleccionar Spool para Completar) + GET /spools/completar
2. Implementar P5B (Confirmar Completar) + POST /completar-accion
3. Implementar P6 (Éxito) con feedback visual
4. Manejo de errores 403 ownership

**Entregable:** Flujo COMPLETAR funcional end-to-end

**Tiempo:** 1 día

---

### DÍA 6 (17 Nov): Navegación + Testing Manual + Deploy

**Agentes:** navigation-orchestrator + ui-builder-mvp

**Tareas:**
1. Conectar navegación completa (botones Volver/Cancelar)
2. Implementar timeout 5seg en P6 → redirect P1
3. Preservar estado (Context simple o URL params)
4. Testing manual tablet/navegador
5. Fix bugs detectados
6. Deploy Vercel

**Entregable:** MVP completo deployed

**Tiempo:** 1 día

---

## 📊 Resumen de Prioridades

### ✅ Agentes CORE MVP (Implementar en orden):

1. **frontend-architect** → DÍA 1 (2-3 horas)
2. **ui-builder-mvp** → DÍA 2-6 (4 días)
3. **api-integrator** → DÍA 4-5 (2 días)
4. **navigation-orchestrator** → DÍA 6 (3 horas)

### ❌ Agentes FASE 2 (NO implementar en MVP):

5. **state-manager** → Post-MVP si escalamos
6. **component-tester** → Post-MVP antes de escalar
7. **accessibility-specialist** → Post-MVP certificación

---

## 🎯 Principios MVP Simple

### DO ✅:
- Funcionalidad básica trabajando end-to-end
- Estilos inline Tailwind (sin archivos CSS separados)
- Componentes simples (3-5 máximo)
- useState + Context simple para estado
- fetch nativo para API
- Validaciones inline (if/else simples)
- Testing manual

### DON'T ❌:
- Sobre-arquitecturar (no Redux/Zustand/arquitecturas complejas)
- Optimizaciones prematuras
- Animaciones complejas
- Design system completo
- Tests automatizados
- Librerías externas innecesarias (axios, react-hook-form, etc.)
- Documentación extensa

---

## 📦 Stack Tecnológico MVP

**Obligatorio:**
- Next.js 14+ (App Router)
- TypeScript
- Tailwind CSS 3+
- shadcn/ui (componentes base)

**Opcional (si necesario):**
- React Icons (íconos simples)
- clsx o cn (utility class merging)

**NO usar:**
- Redux, Zustand, Recoil (estado complejo)
- axios, ky (fetch nativo suficiente)
- react-hook-form, formik (validaciones inline suficiente)
- framer-motion (animaciones complejas)
- Storybook (documentación extensa)
- Jest, React Testing Library (tests MVP)

---

## 🔗 Criterios de Éxito MVP

**Funcionalidad:**
- ✅ 2 flujos completos (INICIAR y COMPLETAR) funcionando end-to-end
- ✅ Conexión con 6 endpoints backend verificada
- ✅ Navegación fluida entre 7 pantallas
- ✅ Loading states y error handling básico
- ✅ Validaciones inline funcionando

**UX/UI:**
- ✅ Botones grandes (h-16 = 64px) para uso con guantes
- ✅ Contraste alto (colores proyecto.md aplicados)
- ✅ Mobile-first responsive
- ✅ Feedback visual inmediato (loading, éxito, error)
- ✅ < 30 segundos por interacción INICIAR/COMPLETAR

**Deployment:**
- ✅ Frontend deployed en Vercel
- ✅ Backend deployed en Railway (o accesible)
- ✅ Testing manual exitoso en tablet/navegador

---

## 📚 Notas Adicionales

### Para Claude Code:
- Estos agentes son **roles contextuales** - Claude actúa como el agente indicado según la fase
- Seguir workflow DÍA 1-6 estrictamente
- NO sobre-arquitecturar ni agregar features no especificadas
- Mantener código simple y funcional

### Recordatorios Críticos:
1. **UI/UX muy simples** - Funcionalidad sobre estética
2. **4 agentes CORE solamente** - No agregar más complejidad
3. **6 días timeline** - Respetar tiempo estimado por fase
4. **Testing manual** - NO tests automatizados en MVP
5. **Backend ya está listo** - Solo conectar 6 endpoints

---

**Versión:** 2.0 (MVP Simplificado)
**Fecha:** 10 Nov 2025 (Actualizado)
**Proyecto:** ZEUES Manufacturing Traceability System
