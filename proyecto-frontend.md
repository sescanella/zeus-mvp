# ZEUES Frontend - Documentación Técnica Completa

**Sistema de Trazabilidad para Manufactura de Cañerías - Frontend Web App**

Última actualización: 10 Nov 2025 - DÍA 1 COMPLETADO
Estado: EN DESARROLLO - DÍA 1 ✅ (Setup completo)

---

## 1. Visión y Arquitectura Frontend

### Decisión de Stack: React/Next.js + Tailwind CSS

**Stack Seleccionado:** Next.js 14+ (App Router) + TypeScript + Tailwind CSS + shadcn/ui

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

### Arquitectura: Mobile-First + Component-Based

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

## 3. Componentes UI (3-5 componentes MVP)

### 3.1 Button Component (components/Button.tsx)

**Responsabilidad:** Botón grande (h-16 = 64px) con variantes de color según contexto.

**Props:**
- `children`: ReactNode - Contenido del botón
- `onClick?`: () => void - Handler click
- `variant?`: 'primary' | 'iniciar' | 'completar' | 'cancel' - Color variant
- `disabled?`: boolean - Estado deshabilitado
- `className?`: string - Clases adicionales Tailwind

**Implementación MVP:**

```tsx
// components/Button.tsx
import { ButtonHTMLAttributes } from 'react';

interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: 'primary' | 'iniciar' | 'completar' | 'cancel';
}

export function Button({
  children,
  variant = 'primary',
  disabled,
  className = '',
  ...props
}: ButtonProps) {
  const variants = {
    primary: 'bg-[#FF5B00] hover:bg-[#E64A19] text-white',
    iniciar: 'bg-cyan-600 hover:bg-cyan-700 text-white',
    completar: 'bg-green-600 hover:bg-green-700 text-white',
    cancel: 'bg-gray-400 hover:bg-gray-500 text-white'
  };

  return (
    <button
      {...props}
      disabled={disabled}
      className={`
        w-full h-16 rounded-lg text-xl font-semibold
        transition-colors duration-200
        disabled:opacity-50 disabled:cursor-not-allowed
        ${variants[variant]}
        ${className}
      `}
    >
      {children}
    </button>
  );
}
```

**Uso:**
```tsx
<Button onClick={() => router.push('/operacion')}>Juan Pérez</Button>
<Button variant="iniciar">INICIAR ACCIÓN</Button>
<Button variant="completar">COMPLETAR ACCIÓN</Button>
<Button variant="cancel">Cancelar</Button>
```

---

### 3.2 Card Component (components/Card.tsx)

**Responsabilidad:** Contenedor simple con shadow para agrupar contenido.

**Props:**
- `children`: ReactNode - Contenido del card
- `className?`: string - Clases adicionales

**Implementación MVP:**

```tsx
// components/Card.tsx
import { ReactNode } from 'react';

interface CardProps {
  children: ReactNode;
  className?: string;
}

export function Card({ children, className = '' }: CardProps) {
  return (
    <div className={`bg-white rounded-lg shadow-md p-6 ${className}`}>
      {children}
    </div>
  );
}
```

**Uso:**
```tsx
<Card>
  <h2 className="text-2xl font-bold mb-4">Confirmar Iniciar ARM</h2>
  <p><strong>Trabajador:</strong> Juan Pérez</p>
  <p><strong>Operación:</strong> ARM</p>
  <p><strong>Spool:</strong> MK-1335-CW-25238-011</p>
</Card>
```

---

### 3.3 List Component (components/List.tsx)

**Responsabilidad:** Lista de items clickeables (trabajadores, spools).

**Props:**
- `items`: Array<{ id: string; label: string; subtitle?: string }> - Items a mostrar
- `onItemClick`: (id: string) => void - Handler click item
- `emptyMessage?`: string - Mensaje cuando lista vacía

**Implementación MVP:**

```tsx
// components/List.tsx
interface ListItem {
  id: string;
  label: string;
  subtitle?: string;
}

interface ListProps {
  items: ListItem[];
  onItemClick: (id: string) => void;
  emptyMessage?: string;
}

export function List({ items, onItemClick, emptyMessage = 'No hay items' }: ListProps) {
  if (items.length === 0) {
    return (
      <div className="text-center py-8 text-gray-500">
        <p>{emptyMessage}</p>
      </div>
    );
  }

  return (
    <div className="space-y-3">
      {items.map((item) => (
        <button
          key={item.id}
          onClick={() => onItemClick(item.id)}
          className="w-full p-4 bg-white rounded-lg shadow hover:shadow-md
                     transition-shadow text-left border border-gray-200"
        >
          <p className="text-lg font-semibold text-slate-900">{item.label}</p>
          {item.subtitle && (
            <p className="text-sm text-gray-600 mt-1">{item.subtitle}</p>
          )}
        </button>
      ))}
    </div>
  );
}
```

**Uso:**
```tsx
<List
  items={spools.map(s => ({
    id: s.tag_spool,
    label: s.tag_spool,
    subtitle: s.proyecto
  }))}
  onItemClick={(tag) => handleSelectSpool(tag)}
  emptyMessage="No hay spools disponibles"
/>
```

---

### 3.4 Loading Component (components/Loading.tsx)

**Responsabilidad:** Spinner con mensaje "Cargando..." para estados loading.

**Props:**
- `message?`: string - Texto custom (default: "Cargando...")

**Implementación MVP:**

```tsx
// components/Loading.tsx
interface LoadingProps {
  message?: string;
}

export function Loading({ message = 'Cargando...' }: LoadingProps) {
  return (
    <div className="flex flex-col items-center justify-center py-12">
      <div className="animate-spin w-12 h-12 border-4 border-cyan-600
                      border-t-transparent rounded-full mb-4">
      </div>
      <p className="text-lg text-gray-600">{message}</p>
    </div>
  );
}
```

**Uso:**
```tsx
{loading && <Loading />}
{loading && <Loading message="Actualizando Google Sheets..." />}
```

---

### 3.5 ErrorMessage Component (components/ErrorMessage.tsx)

**Responsabilidad:** Mensaje de error rojo con opción de retry.

**Props:**
- `message`: string - Texto del error
- `onRetry?`: () => void - Handler para botón "Reintentar"

**Implementación MVP:**

```tsx
// components/ErrorMessage.tsx
interface ErrorMessageProps {
  message: string;
  onRetry?: () => void;
}

export function ErrorMessage({ message, onRetry }: ErrorMessageProps) {
  return (
    <div className="bg-red-50 border border-red-200 rounded-lg p-4">
      <p className="text-red-700 font-medium mb-2">{message}</p>
      {onRetry && (
        <button
          onClick={onRetry}
          className="text-red-600 underline text-sm font-semibold"
        >
          Reintentar
        </button>
      )}
    </div>
  );
}
```

**Uso:**
```tsx
{error && <ErrorMessage message={error} onRetry={fetchWorkers} />}
```

---

## 4. Páginas y Flujos (7 páginas)

### 4.1 P1: Identificación (app/page.tsx)

**Ruta:** `/`
**Descripción:** Pantalla inicial - Grid de botones con nombres de trabajadores
**Estado:** Pendiente
**Componentes:** Button, Card, Loading, ErrorMessage

**Wireframe:**
```
┌─────────────────────────────────────┐
│      ZEUES - Trazabilidad           │
│                                     │
│      ¿Quién eres?                   │
│                                     │
│  ┌─────────────┐  ┌─────────────┐  │
│  │ Juan Pérez  │  │ María López │  │
│  └─────────────┘  └─────────────┘  │
│                                     │
│  ┌─────────────┐  ┌─────────────┐  │
│  │Carlos Díaz  │  │Ana García   │  │
│  └─────────────┘  └─────────────┘  │
│                                     │
└─────────────────────────────────────┘
```

**Lógica:**
- `useEffect` → fetch GET /api/workers al montar
- Mostrar Loading mientras carga
- Mostrar ErrorMessage si falla
- Renderizar grid 2 columnas con Button por cada worker
- Click worker → guardar en Context + navegar a `/operacion`

**Implementación MVP:**

```tsx
// app/page.tsx
'use client';

import { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { Button } from '@/components/Button';
import { Loading } from '@/components/Loading';
import { ErrorMessage } from '@/components/ErrorMessage';
import { useAppState } from '@/lib/context';
import { getWorkers } from '@/lib/api';
import type { Worker } from '@/lib/types';

export default function IdentificacionPage() {
  const router = useRouter();
  const { setState } = useAppState();
  const [workers, setWorkers] = useState<Worker[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  const fetchWorkers = async () => {
    try {
      setLoading(true);
      setError('');
      const data = await getWorkers();
      setWorkers(data);
    } catch (err) {
      setError('Error al cargar trabajadores. Intenta nuevamente.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchWorkers();
  }, []);

  const handleSelectWorker = (worker: Worker) => {
    setState({ selectedWorker: worker.nombre_completo });
    router.push('/operacion');
  };

  return (
    <div className="min-h-screen bg-slate-50 p-6">
      <div className="max-w-2xl mx-auto">
        <h1 className="text-3xl font-bold text-center text-[#FF5B00] mb-2">
          ZEUES - Trazabilidad
        </h1>
        <h2 className="text-2xl font-semibold text-center text-slate-700 mb-8">
          ¿Quién eres?
        </h2>

        {loading && <Loading />}
        {error && <ErrorMessage message={error} onRetry={fetchWorkers} />}

        {!loading && !error && (
          <div className="grid grid-cols-2 gap-4">
            {workers.map((worker) => (
              <Button
                key={worker.nombre}
                onClick={() => handleSelectWorker(worker)}
              >
                {worker.nombre_completo}
              </Button>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
```

---

### 4.2 P2: Operación (app/operacion/page.tsx)

**Ruta:** `/operacion`
**Descripción:** Seleccionar operación (ARM o SOLD)
**Estado:** Pendiente
**Componentes:** Button, Card

**Wireframe:**
```
┌─────────────────────────────────────┐
│  ← Volver                           │
│                                     │
│  Hola Juan Pérez,                   │
│  ¿Qué vas a hacer?                  │
│                                     │
│  ┌─────────────────────────────┐   │
│  │    🔧 ARMADO (ARM)          │   │
│  └─────────────────────────────┘   │
│                                     │
│  ┌─────────────────────────────┐   │
│  │    🔥 SOLDADO (SOLD)        │   │
│  └─────────────────────────────┘   │
│                                     │
└─────────────────────────────────────┘
```

**Lógica:**
- Leer `selectedWorker` de Context
- Si no existe → redirect a `/`
- Click ARM/SOLD → guardar en Context + navegar a `/tipo-interaccion`
- Botón Volver → `router.back()`

**Implementación MVP:**

```tsx
// app/operacion/page.tsx
'use client';

import { useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { Button } from '@/components/Button';
import { useAppState } from '@/lib/context';

export default function OperacionPage() {
  const router = useRouter();
  const { state, setState } = useAppState();

  useEffect(() => {
    if (!state.selectedWorker) {
      router.push('/');
    }
  }, [state.selectedWorker, router]);

  const handleSelectOperation = (operacion: 'ARM' | 'SOLD') => {
    setState({ selectedOperation: operacion });
    router.push('/tipo-interaccion');
  };

  if (!state.selectedWorker) return null;

  return (
    <div className="min-h-screen bg-slate-50 p-6">
      <button
        onClick={() => router.back()}
        className="text-cyan-600 font-semibold mb-6"
      >
        ← Volver
      </button>

      <div className="max-w-2xl mx-auto">
        <h1 className="text-2xl font-semibold text-center mb-2">
          Hola {state.selectedWorker},
        </h1>
        <h2 className="text-xl text-center text-gray-600 mb-8">
          ¿Qué vas a hacer?
        </h2>

        <div className="space-y-4">
          <Button onClick={() => handleSelectOperation('ARM')}>
            🔧 ARMADO (ARM)
          </Button>
          <Button onClick={() => handleSelectOperation('SOLD')}>
            🔥 SOLDADO (SOLD)
          </Button>
        </div>
      </div>
    </div>
  );
}
```

---

### 4.3 P3: Tipo Interacción (app/tipo-interaccion/page.tsx)

**Ruta:** `/tipo-interaccion`
**Descripción:** Seleccionar INICIAR ACCIÓN (cyan) o COMPLETAR ACCIÓN (verde)
**Estado:** Pendiente
**Componentes:** Button, Card

**Wireframe:**
```
┌─────────────────────────────────────┐
│  ← Volver                           │
│                                     │
│  ARMADO (ARM)                       │
│  ¿Qué acción realizarás?            │
│                                     │
│  ┌─────────────────────────────┐   │
│  │ 🔵 INICIAR ACCIÓN          │   │ (CYAN)
│  │ Asignar spool antes de     │   │
│  │ trabajar                    │   │
│  └─────────────────────────────┘   │
│                                     │
│  ┌─────────────────────────────┐   │
│  │ ✅ COMPLETAR ACCIÓN        │   │ (VERDE)
│  │ Registrar finalización     │   │
│  └─────────────────────────────┘   │
│                                     │
└─────────────────────────────────────┘
```

**Lógica:**
- Validar `selectedWorker` y `selectedOperation` en Context
- Si faltan → redirect a `/`
- Click INICIAR → guardar `selectedTipo: 'iniciar'` + navegar a `/seleccionar-spool?tipo=iniciar`
- Click COMPLETAR → guardar `selectedTipo: 'completar'` + navegar a `/seleccionar-spool?tipo=completar`
- Botón Volver → `router.back()`

**Implementación MVP:**

```tsx
// app/tipo-interaccion/page.tsx
'use client';

import { useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { Button } from '@/components/Button';
import { useAppState } from '@/lib/context';

export default function TipoInteraccionPage() {
  const router = useRouter();
  const { state, setState } = useAppState();

  useEffect(() => {
    if (!state.selectedWorker || !state.selectedOperation) {
      router.push('/');
    }
  }, [state, router]);

  const handleSelectTipo = (tipo: 'iniciar' | 'completar') => {
    setState({ selectedTipo: tipo });
    router.push(`/seleccionar-spool?tipo=${tipo}`);
  };

  if (!state.selectedWorker || !state.selectedOperation) return null;

  return (
    <div className="min-h-screen bg-slate-50 p-6">
      <button
        onClick={() => router.back()}
        className="text-cyan-600 font-semibold mb-6"
      >
        ← Volver
      </button>

      <div className="max-w-2xl mx-auto">
        <h1 className="text-2xl font-semibold text-center mb-2">
          {state.selectedOperation === 'ARM' ? 'ARMADO (ARM)' : 'SOLDADO (SOLD)'}
        </h1>
        <h2 className="text-xl text-center text-gray-600 mb-8">
          ¿Qué acción realizarás?
        </h2>

        <div className="space-y-4">
          <Button
            variant="iniciar"
            onClick={() => handleSelectTipo('iniciar')}
          >
            <div className="text-left">
              <div className="text-xl font-bold mb-1">🔵 INICIAR ACCIÓN</div>
              <div className="text-sm font-normal">
                Asignar spool antes de trabajar
              </div>
            </div>
          </Button>

          <Button
            variant="completar"
            onClick={() => handleSelectTipo('completar')}
          >
            <div className="text-left">
              <div className="text-xl font-bold mb-1">✅ COMPLETAR ACCIÓN</div>
              <div className="text-sm font-normal">
                Registrar finalización del trabajo
              </div>
            </div>
          </Button>
        </div>
      </div>
    </div>
  );
}
```

---

### 4.4 P4: Seleccionar Spool (app/seleccionar-spool/page.tsx)

**Ruta:** `/seleccionar-spool?tipo=iniciar|completar`
**Descripción:** Lista de spools disponibles (tipo=iniciar) o propios (tipo=completar)
**Estado:** Pendiente
**Componentes:** List, Loading, ErrorMessage

**Wireframe (INICIAR):**
```
┌─────────────────────────────────────┐
│  ← Volver                           │
│                                     │
│  Selecciona spool para INICIAR ARM  │
│                                     │
│  ┌─────────────────────────────┐   │
│  │ MK-1335-CW-25238-011        │   │
│  │ Proyecto X - Materiales OK  │   │
│  └─────────────────────────────┘   │
│  ┌─────────────────────────────┐   │
│  │ MK-1336-CW-25239-012        │   │
│  │ Proyecto Y - Materiales OK  │   │
│  └─────────────────────────────┘   │
│                                     │
└─────────────────────────────────────┘
```

**Lógica:**
- Leer `tipo` de query params (`?tipo=iniciar` o `?tipo=completar`)
- Validar Context completo
- Si `tipo=iniciar` → GET `/api/spools/iniciar?operacion={ARM|SOLD}`
- Si `tipo=completar` → GET `/api/spools/completar?operacion={ARM|SOLD}&worker_nombre={nombre}`
- Click spool → guardar `selectedSpool` + navegar a `/confirmar?tipo={tipo}`

**Implementación MVP:**

```tsx
// app/seleccionar-spool/page.tsx
'use client';

import { useState, useEffect } from 'react';
import { useRouter, useSearchParams } from 'next/navigation';
import { List } from '@/components/List';
import { Loading } from '@/components/Loading';
import { ErrorMessage } from '@/components/ErrorMessage';
import { useAppState } from '@/lib/context';
import { getSpoolsParaIniciar, getSpoolsParaCompletar } from '@/lib/api';
import type { Spool } from '@/lib/types';

export default function SeleccionarSpoolPage() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const tipo = searchParams.get('tipo') as 'iniciar' | 'completar';
  const { state, setState } = useAppState();

  const [spools, setSpools] = useState<Spool[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    if (!state.selectedWorker || !state.selectedOperation || !tipo) {
      router.push('/');
      return;
    }
    fetchSpools();
  }, [state, tipo]);

  const fetchSpools = async () => {
    try {
      setLoading(true);
      setError('');

      const data = tipo === 'iniciar'
        ? await getSpoolsParaIniciar(state.selectedOperation!)
        : await getSpoolsParaCompletar(state.selectedOperation!, state.selectedWorker!);

      setSpools(data);
    } catch (err) {
      setError('Error al cargar spools. Intenta nuevamente.');
    } finally {
      setLoading(false);
    }
  };

  const handleSelectSpool = (tag: string) => {
    setState({ selectedSpool: tag });
    router.push(`/confirmar?tipo=${tipo}`);
  };

  if (!state.selectedWorker || !state.selectedOperation) return null;

  const title = tipo === 'iniciar'
    ? `Selecciona spool para INICIAR ${state.selectedOperation}`
    : `Selecciona TU spool para COMPLETAR ${state.selectedOperation}`;

  const emptyMessage = tipo === 'iniciar'
    ? 'No hay spools disponibles para iniciar'
    : 'No tienes spools en progreso';

  return (
    <div className="min-h-screen bg-slate-50 p-6">
      <button
        onClick={() => router.back()}
        className="text-cyan-600 font-semibold mb-6"
      >
        ← Volver
      </button>

      <div className="max-w-2xl mx-auto">
        <h1 className="text-xl font-semibold text-center mb-6">
          {title}
        </h1>

        {loading && <Loading />}
        {error && <ErrorMessage message={error} onRetry={fetchSpools} />}

        {!loading && !error && (
          <List
            items={spools.map((s) => ({
              id: s.tag_spool,
              label: s.tag_spool,
              subtitle: s.proyecto || 'Sin proyecto',
            }))}
            onItemClick={handleSelectSpool}
            emptyMessage={emptyMessage}
          />
        )}
      </div>
    </div>
  );
}
```

---

### 4.5 P5: Confirmar Acción (app/confirmar/page.tsx)

**Ruta:** `/confirmar?tipo=iniciar|completar`
**Descripción:** Resumen y confirmación final antes de actualizar Google Sheets
**Estado:** Pendiente
**Componentes:** Card, Button, Loading, ErrorMessage

**Wireframe (INICIAR):**
```
┌─────────────────────────────────────┐
│  ← Volver                           │
│                                     │
│  ¿Confirmas INICIAR ARM?            │
│                                     │
│  ┌─────────────────────────────┐   │
│  │ Resumen                     │   │
│  │ • Trabajador: Juan Pérez    │   │
│  │ • Operación: ARMADO (ARM)   │   │
│  │ • Spool: MK-1335-CW-25238-01│   │
│  └─────────────────────────────┘   │
│                                     │
│  ┌─────────────────────────────┐   │
│  │ ✓ CONFIRMAR                 │   │ (CYAN)
│  └─────────────────────────────┘   │
│  ┌─────────────────────────────┐   │
│  │ Cancelar                    │   │ (GRIS)
│  └─────────────────────────────┘   │
│                                     │
└─────────────────────────────────────┘
```

**Lógica:**
- Validar Context completo + query param `tipo`
- Mostrar resumen: Trabajador, Operación, Spool, (Fecha si completar)
- Click CONFIRMAR:
  - Si `tipo=iniciar` → POST `/api/iniciar-accion` con payload
  - Si `tipo=completar` → POST `/api/completar-accion` con payload
  - Loading durante API call
  - Si éxito → navegar a `/exito`
  - Si error → mostrar ErrorMessage (especial para 403 ownership)
- Click Cancelar → confirmar + resetear Context + navegar a `/`

**Implementación MVP:**

```tsx
// app/confirmar/page.tsx
'use client';

import { useState, useEffect } from 'react';
import { useRouter, useSearchParams } from 'next/navigation';
import { Card } from '@/components/Card';
import { Button } from '@/components/Button';
import { Loading } from '@/components/Loading';
import { ErrorMessage } from '@/components/ErrorMessage';
import { useAppState } from '@/lib/context';
import { iniciarAccion, completarAccion } from '@/lib/api';

export default function ConfirmarPage() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const tipo = searchParams.get('tipo') as 'iniciar' | 'completar';
  const { state, reset } = useAppState();

  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  useEffect(() => {
    if (!state.selectedWorker || !state.selectedOperation || !state.selectedSpool || !tipo) {
      router.push('/');
    }
  }, [state, tipo, router]);

  const handleConfirm = async () => {
    try {
      setLoading(true);
      setError('');

      const payload = {
        worker_nombre: state.selectedWorker!,
        operacion: state.selectedOperation!,
        tag_spool: state.selectedSpool!,
      };

      if (tipo === 'iniciar') {
        await iniciarAccion(payload);
      } else {
        await completarAccion(payload);
      }

      router.push('/exito');
    } catch (err: any) {
      setError(err.message || 'Error al procesar acción');
    } finally {
      setLoading(false);
    }
  };

  const handleCancel = () => {
    if (confirm('¿Seguro que quieres cancelar? Se perderá toda la información.')) {
      reset();
      router.push('/');
    }
  };

  if (!state.selectedWorker || !state.selectedOperation || !state.selectedSpool) {
    return null;
  }

  const title = tipo === 'iniciar'
    ? `¿Confirmas INICIAR ${state.selectedOperation}?`
    : `¿Confirmas COMPLETAR ${state.selectedOperation}?`;

  const variant = tipo === 'iniciar' ? 'iniciar' : 'completar';

  return (
    <div className="min-h-screen bg-slate-50 p-6">
      <button
        onClick={() => router.back()}
        className="text-cyan-600 font-semibold mb-6"
      >
        ← Volver
      </button>

      <div className="max-w-2xl mx-auto">
        <h1 className="text-2xl font-semibold text-center mb-6">
          {title}
        </h1>

        <Card className="mb-6">
          <h2 className="text-xl font-bold mb-4">Resumen</h2>
          <div className="space-y-2 text-lg">
            <p>
              <strong>Trabajador:</strong> {state.selectedWorker}
            </p>
            <p>
              <strong>Operación:</strong>{' '}
              {state.selectedOperation === 'ARM' ? 'ARMADO (ARM)' : 'SOLDADO (SOLD)'}
            </p>
            <p>
              <strong>Spool:</strong> {state.selectedSpool}
            </p>
            {tipo === 'completar' && (
              <p>
                <strong>Fecha:</strong> {new Date().toLocaleDateString('es-ES')}
              </p>
            )}
          </div>
        </Card>

        {error && <ErrorMessage message={error} className="mb-4" />}

        {loading ? (
          <Loading message="Actualizando Google Sheets..." />
        ) : (
          <div className="space-y-3">
            <Button variant={variant} onClick={handleConfirm}>
              ✓ CONFIRMAR
            </Button>
            <Button variant="cancel" onClick={handleCancel}>
              Cancelar
            </Button>
          </div>
        )}
      </div>
    </div>
  );
}
```

---

### 4.6 P6: Éxito (app/exito/page.tsx)

**Ruta:** `/exito`
**Descripción:** Mensaje éxito + timeout 5seg automático a inicio
**Estado:** Pendiente
**Componentes:** Card, Button

**Wireframe:**
```
┌─────────────────────────────────────┐
│                                     │
│         ✓ (CHECKMARK GRANDE)       │ (VERDE)
│                                     │
│  ¡Acción completada exitosamente!  │
│                                     │
│  El spool ha sido actualizado       │
│  en Google Sheets                   │
│                                     │
│  Volviendo al inicio en 5 seg...   │
│                                     │
│  ┌─────────────────────────────┐   │
│  │ REGISTRAR OTRA              │   │
│  └─────────────────────────────┘   │
│  ┌─────────────────────────────┐   │
│  │ FINALIZAR                   │   │
│  └─────────────────────────────┘   │
│                                     │
└─────────────────────────────────────┘
```

**Lógica:**
- Mostrar checkmark grande (verde)
- Mostrar mensaje éxito
- `useEffect` → timeout 5seg → resetear Context + navegar a `/`
- Botón "Registrar Otra" → resetear Context + navegar a `/` (cancelar timeout)
- Botón "Finalizar" → resetear Context + navegar a `/` (cancelar timeout)
- Cleanup timeout en unmount

**Implementación MVP:**

```tsx
// app/exito/page.tsx
'use client';

import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import { Card } from '@/components/Card';
import { Button } from '@/components/Button';
import { useAppState } from '@/lib/context';

export default function ExitoPage() {
  const router = useRouter();
  const { reset } = useAppState();
  const [countdown, setCountdown] = useState(5);

  useEffect(() => {
    const timer = setInterval(() => {
      setCountdown((prev) => {
        if (prev <= 1) {
          clearInterval(timer);
          handleFinish();
          return 0;
        }
        return prev - 1;
      });
    }, 1000);

    return () => clearInterval(timer);
  }, []);

  const handleFinish = () => {
    reset();
    router.push('/');
  };

  return (
    <div className="min-h-screen bg-slate-50 p-6 flex items-center justify-center">
      <div className="max-w-2xl mx-auto text-center">
        <div className="mb-6">
          <svg
            className="w-24 h-24 mx-auto text-green-600"
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M5 13l4 4L19 7"
            />
          </svg>
        </div>

        <h1 className="text-3xl font-bold text-green-600 mb-4">
          ¡Acción completada exitosamente!
        </h1>

        <p className="text-xl text-gray-700 mb-2">
          El spool ha sido actualizado en Google Sheets
        </p>

        <p className="text-lg text-gray-500 mb-8">
          Volviendo al inicio en {countdown} segundos...
        </p>

        <div className="space-y-3">
          <Button onClick={handleFinish}>
            REGISTRAR OTRA
          </Button>
          <Button variant="cancel" onClick={handleFinish}>
            FINALIZAR
          </Button>
        </div>
      </div>
    </div>
  );
}
```

---

## 5. Integración API (6 endpoints)

### 5.1 API Client (/lib/api.ts)

**Responsabilidad:** Cliente HTTP simple con fetch nativo para conectar con backend FastAPI.

**Características:**
- Fetch nativo (NO axios)
- Error handling básico (try/catch)
- Base URL configurable (env var)
- Tipos TypeScript para requests/responses
- Manejo especial error 403 (ownership)

**Código Completo:**

```typescript
// lib/api.ts

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

// ============= TIPOS =============

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

// ============= ENDPOINTS =============

/**
 * GET /api/workers
 * Obtiene lista de trabajadores activos
 */
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

/**
 * GET /api/spools/iniciar?operacion={ARM|SOLD}
 * Obtiene spools disponibles para INICIAR (valor=0, dependencias satisfechas)
 */
export async function getSpoolsParaIniciar(operacion: 'ARM' | 'SOLD'): Promise<Spool[]> {
  try {
    const res = await fetch(`${API_URL}/api/spools/iniciar?operacion=${operacion}`);
    if (!res.ok) throw new Error('Error al obtener spools');
    const data = await res.json();
    return data.spools;
  } catch (error) {
    console.error('getSpoolsParaIniciar error:', error);
    throw new Error('No se pudieron cargar los spools disponibles');
  }
}

/**
 * GET /api/spools/completar?operacion={ARM|SOLD}&worker_nombre={nombre}
 * Obtiene spools del trabajador para COMPLETAR (valor=0.1, filtro ownership)
 */
export async function getSpoolsParaCompletar(
  operacion: 'ARM' | 'SOLD',
  workerNombre: string
): Promise<Spool[]> {
  try {
    const res = await fetch(
      `${API_URL}/api/spools/completar?operacion=${operacion}&worker_nombre=${encodeURIComponent(workerNombre)}`
    );
    if (!res.ok) throw new Error('Error al obtener spools');
    const data = await res.json();
    return data.spools;
  } catch (error) {
    console.error('getSpoolsParaCompletar error:', error);
    throw new Error('No se pudieron cargar tus spools en progreso');
  }
}

/**
 * POST /api/iniciar-accion
 * Inicia una acción (marca valor=0.1, guarda trabajador en metadata)
 */
export async function iniciarAccion(payload: ActionPayload): Promise<ActionResponse> {
  try {
    const res = await fetch(`${API_URL}/api/iniciar-accion`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    });

    const data = await res.json();

    if (!res.ok) {
      throw new Error(data.message || 'Error al iniciar acción');
    }

    return data;
  } catch (error: any) {
    console.error('iniciarAccion error:', error);
    throw error;
  }
}

/**
 * POST /api/completar-accion
 * Completa una acción (marca valor=1.0, guarda fecha en metadata)
 * VALIDACIÓN CRÍTICA: Solo quien inició puede completar (error 403)
 */
export async function completarAccion(payload: ActionPayload): Promise<ActionResponse> {
  try {
    const res = await fetch(`${API_URL}/api/completar-accion`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    });

    const data = await res.json();

    if (!res.ok) {
      // Manejo especial para error 403 OWNERSHIP
      if (res.status === 403) {
        throw new Error(
          'No estás autorizado para completar esta acción. Solo quien la inició puede completarla.'
        );
      }
      throw new Error(data.message || 'Error al completar acción');
    }

    return data;
  } catch (error: any) {
    console.error('completarAccion error:', error);
    throw error;
  }
}

/**
 * GET /api/health
 * Health check backend + conectividad Google Sheets
 */
export async function checkHealth() {
  try {
    const res = await fetch(`${API_URL}/api/health`);
    if (!res.ok) throw new Error('API no disponible');
    return await res.json();
  } catch (error) {
    console.error('checkHealth error:', error);
    throw new Error('El servidor no está disponible');
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

## 6. State Management (Context API simple)

### 6.1 AppContext (/lib/context.tsx)

**Responsabilidad:** Estado global compartido entre páginas (trabajador, operación, tipo, spool).

**Características:**
- Context API simple (NO Redux/Zustand)
- Estado: selectedWorker, selectedOperation, selectedTipo, selectedSpool
- Métodos: setState (actualizar parcial), reset (limpiar todo)
- Provider en layout.tsx (wrapping app completo)

**Código Completo:**

```typescript
// lib/context.tsx
'use client';

import { createContext, useContext, useState, ReactNode } from 'react';

// ============= TIPOS =============

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

// ============= CONTEXT =============

const AppContext = createContext<AppContextType | null>(null);

const initialState: AppState = {
  selectedWorker: null,
  selectedOperation: null,
  selectedTipo: null,
  selectedSpool: null,
};

// ============= PROVIDER =============

export function AppProvider({ children }: { children: ReactNode }) {
  const [state, setStateInternal] = useState<AppState>(initialState);

  const setState = (newState: Partial<AppState>) => {
    setStateInternal((prev) => ({ ...prev, ...newState }));
  };

  const reset = () => {
    setStateInternal(initialState);
  };

  return (
    <AppContext.Provider value={{ state, setState, reset }}>
      {children}
    </AppContext.Provider>
  );
}

// ============= HOOK =============

export function useAppState() {
  const context = useContext(AppContext);
  if (!context) {
    throw new Error('useAppState must be used within AppProvider');
  }
  return context;
}
```

**Uso en layout.tsx:**

```tsx
// app/layout.tsx
import { AppProvider } from '@/lib/context';
import './globals.css';

export const metadata = {
  title: 'ZEUES - Trazabilidad',
  description: 'Sistema de trazabilidad para manufactura de cañerías',
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="es">
      <body>
        <AppProvider>
          {children}
        </AppProvider>
      </body>
    </html>
  );
}
```

**Ejemplos de Uso:**

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

## 7. Navegación y Routing (Next.js App Router)

### 7.1 Flujo INICIAR (P1→P2→P3→P4A→P5A→P6→P1)

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

### 7.2 Flujo COMPLETAR (P1→P2→P3→P4B→P5B→P6→P1)

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
│ P3: Tipo     │ → Click COMPLETAR ACCIÓN (verde)
│ /tipo-inter  │    setState({ selectedTipo: 'completar' })
└──────┬───────┘    router.push('/seleccionar-spool?tipo=completar')
       │
       v
┌──────────────┐
│ P4B: Mis     │ → GET /api/spools/completar?worker_nombre=...
│ Spools       │    Muestra SOLO MIS spools (V/W=0.1, BC/BE=mi nombre)
│ ?tipo=compl  │    Click spool → setState({ selectedSpool })
└──────┬───────┘    router.push('/confirmar?tipo=completar')
       │
       v
┌──────────────┐
│ P5B: Confirmar│ → Muestra resumen + fecha actual
│ /confirmar   │    Click CONFIRMAR (verde)
│ ?tipo=compl  │    POST /api/completar-accion
└──────┬───────┘    Si éxito → router.push('/exito')
       │            Si 403 → ErrorMessage ownership
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

---

### 7.3 Navegación Especial

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

## 8. Estilos y Diseño (Tailwind CSS)

### 8.1 Paleta de Colores

**Configuración Tailwind:**

```javascript
// tailwind.config.ts
import type { Config } from 'tailwindcss';

const config: Config = {
  content: [
    './pages/**/*.{js,ts,jsx,tsx,mdx}',
    './components/**/*.{js,ts,jsx,tsx,mdx}',
    './app/**/*.{js,ts,jsx,tsx,mdx}',
  ],
  theme: {
    extend: {
      colors: {
        // Colores ZEUES custom
        zeues: {
          orange: '#FF5B00',        // Principal
          'orange-dark': '#E64A19', // Hover
          blue: '#0A7EA4',          // Secundario
          cyan: '#0891B2',          // INICIAR
          green: '#16A34A',         // COMPLETAR
          red: '#DC2626',           // Error
          warning: '#EA580C',       // Warning
        },
      },
    },
  },
  plugins: [],
};

export default config;
```

**Uso en Componentes:**

```tsx
// Naranja principal
<div className="bg-[#FF5B00] text-white">Principal</div>

// Cyan INICIAR
<button className="bg-cyan-600 hover:bg-cyan-700">INICIAR</button>

// Verde COMPLETAR
<button className="bg-green-600 hover:bg-green-700">COMPLETAR</button>

// Error
<div className="bg-red-50 border border-red-200 text-red-700">Error</div>

// Fondo app
<div className="bg-slate-50">Background</div>
```

---

### 8.2 Componentes Base Estilizados

**Botones Grandes (Mobile-First):**

```tsx
// h-16 = 64px altura (mínimo para guantes)
<button className="w-full h-16 text-xl font-semibold rounded-lg">
  Texto Grande
</button>
```

**Tarjetas con Shadow:**

```tsx
<div className="bg-white rounded-lg shadow-md p-6">
  Contenido
</div>
```

**Listas Clickeables:**

```tsx
<button className="w-full p-4 bg-white rounded-lg shadow hover:shadow-md
                   transition-shadow text-left border border-gray-200">
  Item
</button>
```

**Loading Spinner:**

```tsx
<div className="animate-spin w-12 h-12 border-4 border-cyan-600
                border-t-transparent rounded-full">
</div>
```

---

### 8.3 Responsive Mobile-First

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

## 9. Testing y Quality (Manual en MVP)

### 9.1 Estrategia de Testing MVP

**Filosofía:** Testing manual es suficiente para MVP simple con 7 pantallas. Tests automatizados requieren tiempo/setup que no tenemos en 6 días.

**Testing Manual Obligatorio:**

**Día 6 - Testing Completo (2-3 horas):**

1. **Flujo INICIAR ARM** (15 min):
   - P1 → Seleccionar trabajador → P2
   - P2 → Seleccionar ARM → P3
   - P3 → Click INICIAR → P4A
   - P4A → Ver spools disponibles → Seleccionar uno → P5A
   - P5A → Verificar resumen → Click CONFIRMAR → P6
   - P6 → Ver checkmark verde → Esperar 5seg → vuelve a P1
   - Verificar en Google Sheets: V=0.1, BC=nombre trabajador

2. **Flujo COMPLETAR ARM** (15 min):
   - P1 → Seleccionar mismo trabajador → P2
   - P2 → Seleccionar ARM → P3
   - P3 → Click COMPLETAR → P4B
   - P4B → Ver solo MI spool en progreso → Seleccionar → P5B
   - P5B → Verificar resumen con fecha → Click CONFIRMAR → P6
   - P6 → Ver checkmark verde → Click "Registrar Otra" → vuelve a P1
   - Verificar en Google Sheets: V=1.0, BB=fecha actual

3. **Flujo INICIAR SOLD** (15 min):
   - Similar a INICIAR ARM pero con SOLD
   - Verificar que solo muestra spools con BB llena (armado completado)
   - Verificar en Sheets: W=0.1, BE=nombre

4. **Flujo COMPLETAR SOLD** (15 min):
   - Similar a COMPLETAR ARM pero con SOLD
   - Verificar en Sheets: W=1.0, BD=fecha

5. **Testing Ownership Validation** (10 min):
   - INICIAR ARM con Trabajador A
   - Intentar COMPLETAR con Trabajador B (diferente)
   - Debe mostrar error: "Solo quien la inició puede completarla"
   - Verificar que NO actualiza Google Sheets

6. **Testing Navegación** (10 min):
   - Botón Volver en cada página (P2, P3, P4, P5)
   - Verificar que mantiene estado seleccionado
   - Botón Cancelar en P5 → Confirmar → Vuelve a P1 y resetea
   - Verificar que pierde todas las selecciones

7. **Testing Error Handling** (10 min):
   - Desconectar internet → Error en fetch
   - Backend caído → Error "API no disponible"
   - Spool no encontrado → Error 404
   - Dependencias no satisfechas → Error 400

8. **Testing Mobile/Tablet** (30 min):
   - Abrir en tablet real (o DevTools responsive mode)
   - Verificar botones grandes clickeables con dedos
   - Verificar texto legible
   - Verificar contraste alto en luz variable
   - Probar rotación landscape/portrait
   - Tiempo total por interacción < 30 segundos

**Checklist de Validación:**

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

---

### 9.2 Tests Automatizados (FASE 2)

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

## 10. Deployment (Vercel)

### 10.1 Vercel Configuration

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

### 10.2 Environment Variables

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

### 10.3 Vercel Configuration File

**vercel.json (Opcional para config avanzada):**

```json
{
  "framework": "nextjs",
  "buildCommand": "npm run build",
  "devCommand": "npm run dev",
  "installCommand": "npm install",
  "env": {
    "NEXT_PUBLIC_API_URL": "https://zeues-backend.up.railway.app"
  }
}
```

---

### 10.4 Deployment Checklist

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

## 11. Roadmap de Implementación Frontend (6 días)

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

**Archivos Creados (21 total):**
- app/layout.tsx, app/page.tsx
- app/operacion/page.tsx, app/tipo-interaccion/page.tsx
- app/seleccionar-spool/page.tsx, app/confirmar/page.tsx, app/exito/page.tsx
- lib/api.ts, lib/types.ts, lib/context.tsx
- components/ (directorio vacío preparado)
- tailwind.config.ts, tsconfig.json, next.config.js
- .env.local, .gitignore, README.md
- package.json, postcss.config.js, app/globals.css
- public/next.svg, public/vercel.svg

---

### DÍA 2-3 (13-14 Nov): Componentes Base + Primeras Páginas

**Responsable:** @ui-builder-mvp
**Tiempo:** 1.5 días

**Tareas DÍA 2 (13 Nov):**
1. Crear componentes base (4-5 horas):
   - Button.tsx (variants: primary, iniciar, completar, cancel)
   - Card.tsx
   - List.tsx
   - Loading.tsx
   - ErrorMessage.tsx
2. Implementar P1 - Identificación (2 horas):
   - Grid botones trabajadores (mock data primero)
   - Loading state
   - Error handling
3. Implementar P2 - Operación (1 hora):
   - Botones ARM/SOLD
   - Botón Volver
   - Saludo con nombre trabajador

**Tareas DÍA 3 (14 Nov):**
4. Implementar P3 - Tipo Interacción (2 horas):
   - Botones INICIAR (cyan) y COMPLETAR (verde)
   - Descripciones breves
   - Botón Volver
5. Implementar Context API (2 horas):
   - `/lib/context.tsx` con AppProvider
   - Estado: selectedWorker, selectedOperation, selectedTipo, selectedSpool
   - Métodos: setState, reset
   - Integrar en layout.tsx
6. Conectar navegación P1→P2→P3 (1 hora):
   - Click trabajador → setState + router.push
   - Click operación → setState + router.push
   - Click tipo → setState + router.push

**Entregable:**
- 5 componentes base funcionando
- 3 páginas completas (P1, P2, P3)
- Context API implementado
- Navegación P1→P2→P3 funcional

**Criterio Éxito:**
- Componentes reutilizables y estilizados
- P1→P2→P3 navegación fluida
- Estado preservado en Context
- Botones Volver funcionan

---

### DÍA 4 (15 Nov): Integración API + Flujo INICIAR

**Responsables:** @api-integrator + @ui-builder-mvp
**Tiempo:** 1 día

**Tareas API Integrator (3 horas):**
1. Crear `/lib/api.ts` con 6 funciones:
   - getWorkers()
   - getSpoolsParaIniciar()
   - getSpoolsParaCompletar()
   - iniciarAccion()
   - completarAccion()
   - checkHealth()
2. Crear `/lib/types.ts` con interfaces:
   - Worker, Spool, ActionPayload, ActionResponse
3. Testing API calls en navegador (console.log)

**Tareas UI Builder (4 horas):**
4. Integrar getWorkers() en P1:
   - useEffect fetch al montar
   - Reemplazar mock data con API real
5. Implementar P4A - Seleccionar Spool INICIAR (2 horas):
   - Query param `?tipo=iniciar`
   - GET /api/spools/iniciar?operacion={ARM|SOLD}
   - List component con spools
   - Click spool → setState + router.push
6. Implementar P5A - Confirmar INICIAR (2 horas):
   - Query param `?tipo=iniciar`
   - Card con resumen
   - Button CONFIRMAR (cyan)
   - POST /api/iniciar-accion
   - Loading durante API call
   - Error handling
   - Si éxito → router.push('/exito')

**Entregable:**
- `/lib/api.ts` con 6 funciones
- P1 integrado con API real
- P4A y P5A implementadas
- Flujo INICIAR completo (P1→P2→P3→P4A→P5A)

**Criterio Éxito:**
- GET /api/workers funciona en P1
- GET /api/spools/iniciar funciona en P4A
- POST /api/iniciar-accion funciona en P5A
- Loading/error states visibles

---

### DÍA 5 (16 Nov): Flujo COMPLETAR

**Responsables:** @api-integrator + @ui-builder-mvp
**Tiempo:** 1 día

**Tareas (7 horas):**
1. Implementar P4B - Seleccionar Spool COMPLETAR (2 horas):
   - Query param `?tipo=completar`
   - GET /api/spools/completar?operacion={ARM|SOLD}&worker_nombre=...
   - List component con MIS spools
   - Mensaje "Solo tus spools en progreso"
   - Click spool → setState + router.push
2. Implementar P5B - Confirmar COMPLETAR (2 horas):
   - Query param `?tipo=completar`
   - Card con resumen + fecha actual
   - Button CONFIRMAR (verde)
   - POST /api/completar-accion
   - Loading durante API call
   - Error handling especial 403 ownership
   - Si éxito → router.push('/exito')
3. Implementar P6 - Éxito (2 horas):
   - Checkmark SVG grande verde
   - Mensaje "¡Acción completada exitosamente!"
   - Countdown 5 segundos
   - useEffect → setTimeout → reset() + router.push('/')
   - Botón "Registrar Otra" → reset() + router.push('/')
   - Botón "Finalizar" → reset() + router.push('/')
4. Testing manual flujo COMPLETAR (1 hora):
   - P1→P2→P3→P4B→P5B→P6→P1

**Entregable:**
- P4B y P5B implementadas
- P6 implementada con timeout
- Flujo COMPLETAR completo (P1→P2→P3→P4B→P5B→P6→P1)
- Ownership validation testeada (error 403)

**Criterio Éxito:**
- GET /api/spools/completar funciona en P4B
- POST /api/completar-accion funciona en P5B
- Error 403 ownership muestra mensaje claro
- Timeout 5seg funciona en P6
- Flujo completo COMPLETAR testeado

---

### DÍA 6 (17 Nov): Navegación + Testing + Deploy

**Responsables:** @navigation-orchestrator + @ui-builder-mvp
**Tiempo:** 1 día

**Tareas Navegación (2 horas):**
1. Revisar botones Volver en todas las páginas:
   - P2, P3, P4, P5 tienen botón Volver
   - Volver mantiene estado Context
2. Implementar botón Cancelar en P5:
   - Confirmar antes de cancelar
   - reset() + router.push('/')
3. Verificar timeout P6:
   - 5 segundos exactos
   - Cleanup en unmount
4. Testing navegación completa (1 hora):
   - Volver en cada página
   - Cancelar en P5
   - Timeout P6

**Tareas Testing Manual (3 horas):**
5. Testing Flujo INICIAR ARM (30 min)
6. Testing Flujo COMPLETAR ARM (30 min)
7. Testing Flujo INICIAR SOLD (30 min)
8. Testing Flujo COMPLETAR SOLD (30 min)
9. Testing Ownership Validation (15 min)
10. Testing Error Handling (30 min)
11. Testing Mobile/Tablet (45 min)
12. Fix bugs detectados (variable)

**Tareas Deploy (2 horas):**
13. Build local (npm run build)
14. Fix errores build si los hay
15. Push código a GitHub
16. Deploy Vercel (auto desde GitHub)
17. Configurar env vars producción
18. Testing manual en URL producción
19. Verificar API calls funcionan
20. Verificar Google Sheets actualiza

**Entregable:**
- Navegación completa funcional
- Testing manual completo (checklist ✓)
- Bugs críticos resueltos
- Frontend deployed en Vercel
- URL producción funcionando
- Google Sheets TESTING actualizado correctamente

**Criterio Éxito:**
- Checklist testing 100% completado
- 0 bugs críticos bloqueantes
- Deploy Vercel exitoso
- API calls funcionan en producción
- Ownership validation funciona en prod
- Tiempo total por interacción < 30 segundos

---

## 12. Estado Actual del Frontend

**Estado General:** ✅ DÍA 1 COMPLETADO (10 Nov 2025) - EN DESARROLLO
**Progreso:** ~15% (1/6 días completados)
**Bloqueadores:** Ninguno - backend listo para integración

**Backend Status:**
- ✅ 6 endpoints API funcionando
- ✅ 10 tests E2E passing (100%)
- ✅ Ownership validation implementada
- ✅ Google Sheets TESTING configurado
- ✅ Deployed en Railway (o localhost disponible)

**Frontend - DÍA 1 Completado:**
- ✅ Proyecto Next.js 14.2.33 creado y configurado
- ✅ 7 páginas placeholder con routing automático
- ✅ Tailwind CSS configurado con paleta ZEUES custom
- ✅ Estructura de carpetas completa (app/, components/, lib/)
- ✅ Variables de entorno configuradas (.env.local)
- ✅ Git repository inicializado (commit 05cb9d4)
- ✅ Build exitoso validado
- ✅ Dev server funcionando (puerto 3001)
- ✅ README.md frontend documentado

**Frontend Pendiente (DÍA 2-6):**
- [ ] Componentes base (Button, Card, List, Loading, ErrorMessage) - DÍA 2
- [ ] P1, P2, P3 páginas implementadas - DÍA 2-3
- [ ] Context API (estado global) - DÍA 3
- [ ] API client (/lib/api.ts) funcional - DÍA 4
- [ ] Flujo INICIAR completo (P4A, P5A) - DÍA 4
- [ ] Flujo COMPLETAR completo (P4B, P5B, P6) - DÍA 5
- [ ] Navegación completa - DÍA 6
- [ ] Testing manual - DÍA 6
- [ ] Deploy Vercel - DÍA 6

**Recursos Disponibles:**
- ✅ Documentación completa (proyecto.md, proyecto-backend.md, proyecto-frontend.md)
- ✅ Wireframes conceptuales
- ✅ Paleta de colores definida (#FF5B00, #0891B2, #16A34A)
- ✅ API endpoints documentados
- ✅ Agentes frontend definidos (4 CORE)
- ✅ Proyecto Next.js configurado y validado

**Próximo Paso:** DÍA 2 (11-12 Nov) - @ui-builder-mvp crea componentes base y páginas P1, P2, P3

---

## 13. Apéndices

### A. Comandos Útiles

**Desarrollo:**
```bash
# Crear proyecto Next.js
npx create-next-app@latest zeues-frontend --typescript --tailwind --app

# Instalar dependencias
npm install

# Dev server
npm run dev              # http://localhost:3000

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
    "next": "^14.0.0",
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
    "eslint-config-next": "^14.0.0"
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

### D. Arquitectura Visual

**Diagrama Flujo Completo:**

```
┌─────────────────────────────────────────────────────────────┐
│                    FRONTEND (Vercel)                        │
│  Next.js 14+ App Router + TypeScript + Tailwind CSS        │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  ┌──────────┐    ┌──────────┐    ┌──────────┐            │
│  │   P1     │ → │   P2     │ → │   P3     │            │
│  │  Inicio  │    │Operación │    │  Tipo    │            │
│  └──────────┘    └──────────┘    └──────────┘            │
│                                                             │
│       ↓               ↓               ↓                     │
│                                                             │
│  ┌──────────┐    ┌──────────┐    ┌──────────┐            │
│  │  P4A/B   │ → │  P5A/B   │ → │   P6     │            │
│  │  Spool   │    │Confirmar │    │  Éxito   │            │
│  └──────────┘    └──────────┘    └──────────┘            │
│                                        ↓                    │
│                                   (reset + /)               │
│                                                             │
│  ┌─────────────────────────────────────────────┐          │
│  │  Context API (Estado Global)                │          │
│  │  • selectedWorker                            │          │
│  │  • selectedOperation (ARM/SOLD)              │          │
│  │  • selectedTipo (iniciar/completar)          │          │
│  │  • selectedSpool (tag_spool)                 │          │
│  └─────────────────────────────────────────────┘          │
│                                                             │
│  ┌─────────────────────────────────────────────┐          │
│  │  API Client (/lib/api.ts)                   │          │
│  │  • getWorkers()                              │          │
│  │  • getSpoolsParaIniciar()                    │          │
│  │  • getSpoolsParaCompletar()                  │          │
│  │  • iniciarAccion()                           │          │
│  │  • completarAccion()                         │          │
│  │  • checkHealth()                             │          │
│  └─────────────────────────────────────────────┘          │
│                       ↓ HTTPS                               │
└───────────────────────┼─────────────────────────────────────┘
                        │
┌───────────────────────┼─────────────────────────────────────┐
│                  BACKEND (Railway)                          │
│        Python FastAPI + gspread + Google Sheets API        │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  6 Endpoints:                                               │
│  • GET  /api/workers                                        │
│  • GET  /api/spools/iniciar?operacion=...                  │
│  • GET  /api/spools/completar?operacion=...&worker_nombre=│
│  • POST /api/iniciar-accion                                 │
│  • POST /api/completar-accion (OWNERSHIP VALIDATION)       │
│  • GET  /api/health                                         │
│                                                             │
│  ┌─────────────────────────────────────────────┐          │
│  │  ActionService (Orquestador)                │          │
│  │  • iniciar_accion()                          │          │
│  │  • completar_accion() → validación ownership│          │
│  └─────────────────────────────────────────────┘          │
│                       ↓ gspread                             │
└───────────────────────┼─────────────────────────────────────┘
                        │
┌───────────────────────┼─────────────────────────────────────┐
│                 GOOGLE SHEETS (Fuente de Verdad)            │
│                       292 spools                            │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  Hoja "Operaciones":                                        │
│  • Col G: TAG_SPOOL (único)                                 │
│  • Col V: ARM (0/0.1/1.0)                                   │
│  • Col W: SOLD (0/0.1/1.0)                                  │
│  • Col BA: Fecha_Materiales (requisito INICIAR ARM)        │
│  • Col BB: Fecha_Armado (requisito INICIAR SOLD)           │
│  • Col BC: Armador (OWNERSHIP ARM)                          │
│  • Col BD: Fecha_Soldadura                                  │
│  • Col BE: Soldador (OWNERSHIP SOLD)                        │
│                                                             │
│  Hoja "Trabajadores":                                       │
│  • 4 trabajadores activos (2 armadores + 2 soldadores)     │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

---

### E. Checklist Final Pre-Lanzamiento

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

**Documentación:**
```
[ ] README.md frontend con instrucciones setup
[ ] Comentarios críticos en código
[ ] Types TypeScript documentados
[ ] API client funciones documentadas
```

**Pre-Lanzamiento:**
```
[ ] Cambiar backend a Google Sheets PRODUCCIÓN
[ ] Capacitación trabajadores (4 personas)
[ ] Capacitación admins (2 personas)
[ ] Monitoreo logs configurado
[ ] Plan rollback si falla
```

---

**FIN - proyecto-frontend.md - ZEUES Frontend - v1.1 - 10 Nov 2025**

**Resumen:**
- ✅ Stack configurado: Next.js 14.2.33 + TypeScript 5.4 + Tailwind CSS 3.4
- ✅ 7 páginas placeholder con routing automático funcionando
- ⏳ 5 componentes reutilizables (Button, Card, List, Loading, ErrorMessage) - Pendiente DÍA 2
- ⏳ Context API simple para estado global - Pendiente DÍA 3
- ⏳ API client fetch nativo (6 funciones) - Pendiente DÍA 4
- ⏳ 2 flujos completos (INICIAR/COMPLETAR) - Pendiente DÍA 4-5
- ⏳ Ownership validation integrada - Pendiente DÍA 5
- ⏳ Testing manual obligatorio (checklist completo) - Pendiente DÍA 6
- ⏳ Deployment Vercel con CI/CD automático - Pendiente DÍA 6
- Timeline: 6 días (10-15 Nov 2025) - DÍA 1 ✅ COMPLETADO

**Filosofía MVP:**
- Funcionalidad sobre estética
- Simple y funcional sobre complejo y perfecto
- Testing manual suficiente para MVP
- Deploy rápido para feedback temprano

**Progreso Actual:** DÍA 1 COMPLETADO ✅ (15% del proyecto)

**Próximo Paso:** DÍA 2 (11-12 Nov 2025) - @ui-builder-mvp crea componentes base (Button, Card, List, Loading, ErrorMessage) y páginas P1, P2, P3

**Agentes Frontend:**
1. ✅ @frontend-architect (DÍA 1) - COMPLETADO
2. ⏳ @ui-builder-mvp (DÍA 2-6) - PRÓXIMO
3. ⏳ @api-integrator (DÍA 4-5)
4. ⏳ @navigation-orchestrator (DÍA 6)

**Backend Listo:**
- ✅ 6 endpoints API funcionando
- ✅ 10/10 tests E2E passing
- ✅ Ownership validation implementada
- ✅ Google Sheets integración completa
- ✅ Deployed Railway (o localhost)

**Frontend DÍA 1:**
- ✅ Proyecto Next.js 14.2.33 configurado
- ✅ 21 archivos creados
- ✅ Git commit inicial (05cb9d4)
- ✅ Build exitoso validado
- ✅ Dev server funcionando (puerto 3001)

**Estado:** DÍA 1 completado (10 Nov 2025), DÍA 2 pendiente inicio
