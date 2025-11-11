# ZEUES Frontend - Detalles de Implementación UI

**Sistema de Trazabilidad para Manufactura de Cañerías - Componentes y Páginas**

Última actualización: 10 Nov 2025 - DÍA 3 COMPLETADO
Estado: EN DESARROLLO - UI completa con mock data

> **Nota:** Este archivo contiene detalles de implementación UI (componentes con código, páginas con wireframes y lógica). Para arquitectura, estado del proyecto e integración API, consultar **`proyecto-frontend.md`**.

---

## Índice

1. [Componentes UI Base (5 componentes)](#1-componentes-ui-base)
2. [Páginas Detalladas (P1-P6)](#2-páginas-detalladas)
3. [Estilos y Diseño Tailwind](#3-estilos-y-diseño-tailwind)
4. [Wireframes Visuales](#4-wireframes-visuales)
5. [Apéndices Técnicos](#5-apéndices-técnicos)

---

## 1. Componentes UI Base

### 1.1 Button Component (components/Button.tsx)

**Responsabilidad:** Botón grande (h-16 = 64px) con variantes de color según contexto.

**Props:**
```typescript
interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: 'primary' | 'iniciar' | 'completar' | 'cancel';
}
```

**Implementación Completa:**

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
    cancel: 'bg-gray-400 hover:bg-gray-500 text-white',
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

**Ejemplos de Uso:**

```tsx
// Botón principal naranja
<Button onClick={handleClick}>Juan Pérez</Button>

// Botón INICIAR cyan
<Button variant="iniciar" onClick={handleIniciar}>
  INICIAR ACCIÓN
</Button>

// Botón COMPLETAR verde
<Button variant="completar" onClick={handleCompletar}>
  COMPLETAR ACCIÓN
</Button>

// Botón cancelar gris
<Button variant="cancel" onClick={handleCancel}>
  Cancelar
</Button>

// Botón deshabilitado
<Button disabled>No disponible</Button>
```

**Características UI/UX:**
- ✅ h-16 (64px) = Target táctil grande para uso con guantes
- ✅ text-xl (20px) = Legible desde distancia
- ✅ Transiciones suaves (duration-200)
- ✅ Estados hover y disabled
- ✅ Mobile-first (100% width por defecto)

---

### 1.2 Card Component (components/Card.tsx)

**Responsabilidad:** Contenedor simple con shadow para agrupar contenido.

**Props:**
```typescript
interface CardProps {
  children: ReactNode;
  className?: string;
}
```

**Implementación Completa:**

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

**Ejemplos de Uso:**

```tsx
// Card simple
<Card>
  <h2 className="text-2xl font-bold mb-4">Título</h2>
  <p>Contenido del card</p>
</Card>

// Card con className adicional
<Card className="mb-6">
  <h2>Resumen</h2>
  <p><strong>Trabajador:</strong> Juan Pérez</p>
  <p><strong>Operación:</strong> ARM</p>
</Card>

// Card en P5 - Confirmar
<Card>
  <h2 className="text-xl font-bold mb-4">Resumen</h2>
  <div className="space-y-2 text-lg">
    <p><strong>Trabajador:</strong> {state.selectedWorker}</p>
    <p><strong>Operación:</strong> {state.selectedOperation}</p>
    <p><strong>Spool:</strong> {state.selectedSpool}</p>
  </div>
</Card>
```

**Características UI/UX:**
- ✅ Fondo blanco con shadow-md (elevación sutil)
- ✅ Padding consistente p-6 (24px)
- ✅ Esquinas redondeadas rounded-lg (8px)
- ✅ Extendible con className adicional

---

### 1.3 List Component (components/List.tsx)

**Responsabilidad:** Lista de items clickeables (trabajadores, spools).

**Props:**
```typescript
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
```

**Implementación Completa:**

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

export function List({
  items,
  onItemClick,
  emptyMessage = 'No hay items'
}: ListProps) {
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

**Ejemplos de Uso:**

```tsx
// Lista de spools en P4
<List
  items={spools.map((s) => ({
    id: s.tag_spool,
    label: s.tag_spool,
    subtitle: s.proyecto || 'Sin proyecto',
  }))}
  onItemClick={handleSelectSpool}
  emptyMessage="No hay spools disponibles"
/>

// Lista de trabajadores en P1 (alternativa a grid)
<List
  items={workers.map((w) => ({
    id: w.nombre,
    label: w.nombre_completo,
    subtitle: w.activo ? 'Activo' : 'Inactivo',
  }))}
  onItemClick={handleSelectWorker}
  emptyMessage="No hay trabajadores disponibles"
/>
```

**Características UI/UX:**
- ✅ Items clickeables con feedback hover (shadow increase)
- ✅ Título + subtítulo opcional
- ✅ Estado vacío con mensaje personalizable
- ✅ Spacing consistente space-y-3 (12px)
- ✅ Border sutil para separación visual

---

### 1.4 Loading Component (components/Loading.tsx)

**Responsabilidad:** Spinner con mensaje "Cargando..." para estados loading.

**Props:**
```typescript
interface LoadingProps {
  message?: string;
}
```

**Implementación Completa:**

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

**Ejemplos de Uso:**

```tsx
// Loading default
{loading && <Loading />}

// Loading con mensaje custom
{loading && <Loading message="Actualizando Google Sheets..." />}

// Loading en P1 durante fetch workers
{loading && <Loading message="Cargando trabajadores..." />}

// Loading como fallback de Suspense
<Suspense fallback={<Loading />}>
  <ContentComponent />
</Suspense>
```

**Características UI/UX:**
- ✅ Spinner animado con animate-spin (Tailwind)
- ✅ Color cyan (#0891B2) matching INICIAR
- ✅ Mensaje personalizable
- ✅ Centrado vertical y horizontal
- ✅ Padding generoso py-12 (48px)

---

### 1.5 ErrorMessage Component (components/ErrorMessage.tsx)

**Responsabilidad:** Mensaje de error rojo con opción de retry.

**Props:**
```typescript
interface ErrorMessageProps {
  message: string;
  onRetry?: () => void;
}
```

**Implementación Completa:**

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

**Ejemplos de Uso:**

```tsx
// Error con retry
{error && <ErrorMessage message={error} onRetry={fetchWorkers} />}

// Error sin retry
{error && <ErrorMessage message="Error al procesar acción" />}

// Error en P5 (wrapped en div para className)
{error && (
  <div className="mt-4">
    <ErrorMessage message={error} />
  </div>
)}

// Error 403 ownership
{error && (
  <ErrorMessage
    message="No estás autorizado para completar esta acción. Solo quien la inició puede completarla."
  />
)}
```

**Características UI/UX:**
- ✅ Fondo rojo claro bg-red-50
- ✅ Border rojo border-red-200
- ✅ Texto rojo oscuro text-red-700 (contraste suficiente)
- ✅ Botón "Reintentar" opcional
- ✅ Esquinas redondeadas rounded-lg

---

## 2. Páginas Detalladas

### 2.1 P1: Identificación (app/page.tsx)

**Ruta:** `/`
**Descripción:** Pantalla inicial - Grid de botones con nombres de trabajadores
**Estado:** ✅ Completada
**Componentes:** Button, Loading, ErrorMessage

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
- `useEffect` → fetch workers al montar (mock data por ahora)
- Mostrar Loading mientras carga
- Mostrar ErrorMessage si falla
- Renderizar grid 2 columnas con Button por cada worker
- Click worker → guardar en Context + navegar a `/operacion`

**Implementación (Resumen - DÍA 2):**

```tsx
// app/page.tsx
'use client';

import { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { Button, Loading, ErrorMessage } from '@/components';
import { useAppState } from '@/lib/context';

// Mock data temporal (DÍA 4 se reemplaza con API real)
const MOCK_WORKERS = [
  { nombre: 'Juan', apellido: 'Pérez', nombre_completo: 'Juan Pérez', activo: true },
  { nombre: 'María', apellido: 'López', nombre_completo: 'María López', activo: true },
  { nombre: 'Carlos', apellido: 'Díaz', nombre_completo: 'Carlos Díaz', activo: true },
  { nombre: 'Ana', apellido: 'García', nombre_completo: 'Ana García', activo: true },
];

export default function IdentificacionPage() {
  const router = useRouter();
  const { setState } = useAppState();
  const [workers, setWorkers] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    fetchWorkers();
  }, []);

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

  const handleSelectWorker = (worker) => {
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
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
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

**Características UI/UX:**
- ✅ Header naranja #FF5B00 (color principal ZEUES)
- ✅ Grid responsive: 1 columna móvil, 2 columnas tablet (md:grid-cols-2)
- ✅ Botones grandes h-16 (64px) para touch targets
- ✅ Loading state con spinner
- ✅ Error state con retry

---

### 2.2 P2: Operación (app/operacion/page.tsx)

**Ruta:** `/operacion`
**Descripción:** Seleccionar operación (ARM o SOLD)
**Estado:** ✅ Completada
**Componentes:** Button

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

**Implementación (Resumen - DÍA 2):**

```tsx
// app/operacion/page.tsx
'use client';

import { useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { Button } from '@/components';
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
        className="text-cyan-600 font-semibold mb-6 text-xl"
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

**Características UI/UX:**
- ✅ Botón Volver cyan (matching INICIAR)
- ✅ Saludo personalizado con nombre trabajador
- ✅ 2 botones grandes verticalmente apilados
- ✅ Emojis para identificación visual rápida
- ✅ Protección: redirect si no hay trabajador seleccionado

---

### 2.3 P3: Tipo Interacción (app/tipo-interaccion/page.tsx)

**Ruta:** `/tipo-interaccion`
**Descripción:** Seleccionar INICIAR ACCIÓN (cyan) o COMPLETAR ACCIÓN (verde)
**Estado:** ✅ Completada
**Componentes:** Button

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

**Implementación (Resumen - DÍA 2):**

```tsx
// app/tipo-interaccion/page.tsx
'use client';

import { useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { Button } from '@/components';
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

**Características UI/UX:**
- ✅ Botones diferenciados por color: cyan (iniciar) vs verde (completar)
- ✅ Título + descripción breve en cada botón
- ✅ text-left para alineación izquierda del texto interno
- ✅ Emojis para identificación visual inmediata
- ✅ Protección: redirect si falta contexto

---

### 2.4 P4: Seleccionar Spool (app/seleccionar-spool/page.tsx)

**Ruta:** `/seleccionar-spool?tipo=iniciar|completar`
**Descripción:** Lista de spools disponibles (tipo=iniciar) o propios (tipo=completar)
**Estado:** ✅ Completada
**Componentes:** List, Loading, ErrorMessage, Suspense

**Wireframe (INICIAR):**
```
┌─────────────────────────────────────┐
│  ← Volver                           │
│                                     │
│  Selecciona spool para INICIAR ARM  │
│                                     │
│  ┌─────────────────────────────┐   │
│  │ MK-1335-CW-25238-011        │   │
│  │ Proyecto Alpha              │   │
│  └─────────────────────────────┘   │
│  ┌─────────────────────────────┐   │
│  │ MK-1335-CW-25238-012        │   │
│  │ Proyecto Beta               │   │
│  └─────────────────────────────┘   │
│                                     │
└─────────────────────────────────────┘
```

**Lógica:**
- Leer `tipo` de query params (`?tipo=iniciar` o `?tipo=completar`)
- Validar Context completo
- Si `tipo=iniciar`:
  - ARM: Filtrar spools con arm=0
  - SOLD: Filtrar spools con arm=1.0 && sold=0
- Si `tipo=completar`:
  - ARM: Filtrar spools con arm=0.1 && armador=trabajador actual
  - SOLD: Filtrar spools con sold=0.1 && soldador=trabajador actual
- Click spool → guardar `selectedSpool` + navegar a `/confirmar?tipo={tipo}`

**Mock Data (20 spools):**
```typescript
const MOCK_SPOOLS = [
  // 5 spools pendientes ARM (arm=0)
  { tag_spool: 'MK-1335-CW-25238-011', arm: 0, sold: 0, proyecto: 'Proyecto Alpha' },
  // ... (otros 4)

  // 5 spools pendientes SOLD (arm=1.0, sold=0)
  { tag_spool: 'MK-1336-CW-25240-021', arm: 1.0, sold: 0, proyecto: 'Proyecto Alpha' },
  // ... (otros 4)

  // 2 spools en progreso ARM por "Juan Pérez"
  { tag_spool: 'MK-1337-CW-25250-031', arm: 0.1, sold: 0, proyecto: 'Proyecto Zeta', armador: 'Juan Pérez' },
  // ... (otro 1)

  // 2 spools en progreso ARM por "María López"
  // 2 spools en progreso SOLD por "Carlos Díaz"
  // 2 spools en progreso SOLD por "Ana García"
  // 2 spools completados (arm=1.0, sold=1.0)
];
```

**Implementación (Resumen - DÍA 3):**

```tsx
// app/seleccionar-spool/page.tsx
'use client';

import { Suspense, useState, useEffect } from 'react';
import { useRouter, useSearchParams } from 'next/navigation';
import { List, Loading, ErrorMessage } from '@/components';
import { useAppState } from '@/lib/context';

function SeleccionarSpoolContent() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const tipo = searchParams.get('tipo') as 'iniciar' | 'completar';
  const { state, setState } = useAppState();

  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    if (!state.selectedWorker || !state.selectedOperation || !tipo) {
      router.push('/');
      return;
    }
    fetchSpools();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const fetchSpools = async () => {
    try {
      setLoading(true);
      setError('');
      await new Promise(resolve => setTimeout(resolve, 500));
      setLoading(false);
    } catch {
      setError('Error al cargar spools. Intenta nuevamente.');
      setLoading(false);
    }
  };

  const getFilteredSpools = () => {
    const { selectedWorker, selectedOperation } = state;

    if (tipo === 'iniciar') {
      if (selectedOperation === 'ARM') {
        return MOCK_SPOOLS.filter(s => s.arm === 0);
      } else if (selectedOperation === 'SOLD') {
        return MOCK_SPOOLS.filter(s => s.arm === 1.0 && s.sold === 0);
      }
    } else if (tipo === 'completar') {
      if (selectedOperation === 'ARM') {
        return MOCK_SPOOLS.filter(s => s.arm === 0.1 && s.armador === selectedWorker);
      } else if (selectedOperation === 'SOLD') {
        return MOCK_SPOOLS.filter(s => s.sold === 0.1 && s.soldador === selectedWorker);
      }
    }
    return [];
  };

  const handleSelectSpool = (tag: string) => {
    setState({ selectedSpool: tag });
    router.push(`/confirmar?tipo=${tipo}`);
  };

  const filteredSpools = getFilteredSpools();
  const title = tipo === 'iniciar'
    ? `Selecciona spool para INICIAR ${state.selectedOperation}`
    : `Selecciona TU spool para COMPLETAR ${state.selectedOperation}`;

  return (
    <div className="min-h-screen bg-slate-50 p-6">
      <button onClick={() => router.back()} className="text-cyan-600 font-semibold mb-6 text-xl">
        ← Volver
      </button>

      <div className="max-w-2xl mx-auto">
        <h1 className="text-2xl font-semibold text-center mb-6">{title}</h1>

        {loading && <Loading />}
        {error && <ErrorMessage message={error} onRetry={fetchSpools} />}

        {!loading && !error && (
          <List
            items={filteredSpools.map((s) => ({
              id: s.tag_spool,
              label: s.tag_spool,
              subtitle: s.proyecto || 'Sin proyecto',
            }))}
            onItemClick={handleSelectSpool}
            emptyMessage={getEmptyMessage()}
          />
        )}
      </div>
    </div>
  );
}

export default function SeleccionarSpoolPage() {
  return (
    <Suspense fallback={<Loading />}>
      <SeleccionarSpoolContent />
    </Suspense>
  );
}
```

**Características UI/UX:**
- ✅ Filtrado inteligente según tipo y operación
- ✅ Ownership validation en filtrado (solo mis spools para completar)
- ✅ Suspense boundary (Next.js 14 requirement)
- ✅ Empty state con mensajes específicos
- ✅ Loading state durante fetch

---

### 2.5 P5: Confirmar Acción (app/confirmar/page.tsx)

**Ruta:** `/confirmar?tipo=iniciar|completar`
**Descripción:** Resumen y confirmación final antes de actualizar Google Sheets
**Estado:** ✅ Completada
**Componentes:** Card, Button, Loading, ErrorMessage, Suspense

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
  - Simular API call (1 seg, mensaje "Actualizando Google Sheets...")
  - Si éxito → navegar a `/exito`
  - Si error → mostrar ErrorMessage
- Click Cancelar → confirmar + resetear Context + navegar a `/`

**Implementación (Resumen - DÍA 3):**

```tsx
// app/confirmar/page.tsx
'use client';

import { Suspense, useState, useEffect } from 'react';
import { useRouter, useSearchParams } from 'next/navigation';
import { Card, Button, Loading, ErrorMessage } from '@/components';
import { useAppState } from '@/lib/context';

function ConfirmarContent() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const tipo = searchParams.get('tipo') as 'iniciar' | 'completar';
  const { state, resetState } = useAppState();

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
      await new Promise(resolve => setTimeout(resolve, 1000));
      router.push('/exito');
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Error al procesar acción';
      setError(message);
    } finally {
      setLoading(false);
    }
  };

  const handleCancel = () => {
    if (confirm('¿Seguro que quieres cancelar? Se perderá toda la información.')) {
      resetState();
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
      <button onClick={() => router.back()} className="text-cyan-600 font-semibold mb-6 text-xl">
        ← Volver
      </button>

      <div className="max-w-2xl mx-auto">
        <h1 className="text-2xl font-semibold text-center mb-6">{title}</h1>

        <Card>
          <h2 className="text-xl font-bold mb-4">Resumen</h2>
          <div className="space-y-2 text-lg">
            <p><strong>Trabajador:</strong> {state.selectedWorker}</p>
            <p><strong>Operación:</strong> {state.selectedOperation === 'ARM' ? 'ARMADO (ARM)' : 'SOLDADO (SOLD)'}</p>
            <p><strong>Spool:</strong> {state.selectedSpool}</p>
            {tipo === 'completar' && (
              <p><strong>Fecha:</strong> {new Date().toLocaleDateString('es-ES')}</p>
            )}
          </div>
        </Card>

        {error && (
          <div className="mt-4">
            <ErrorMessage message={error} />
          </div>
        )}

        {loading ? (
          <div className="mt-6">
            <Loading message="Actualizando Google Sheets..." />
          </div>
        ) : (
          <div className="space-y-3 mt-6">
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

export default function ConfirmarPage() {
  return (
    <Suspense fallback={<Loading />}>
      <ConfirmarContent />
    </Suspense>
  );
}
```

**Características UI/UX:**
- ✅ Card con resumen completo de la acción
- ✅ Botón CONFIRMAR con color según tipo (cyan/verde)
- ✅ Fecha actual si es completar
- ✅ Loading durante simulación API (1 seg)
- ✅ Botón Cancelar con confirmación nativa
- ✅ Suspense boundary implementado

---

### 2.6 P6: Éxito (app/exito/page.tsx)

**Ruta:** `/exito`
**Descripción:** Mensaje éxito + timeout 5seg automático a inicio
**Estado:** ✅ Completada
**Componentes:** Button

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
- Mostrar checkmark grande SVG (verde, w-32 h-32 = 128px)
- Mostrar mensaje éxito
- `useEffect` → countdown 5seg → resetear Context + navegar a `/`
- Botón "Registrar Otra" → resetear Context + navegar a `/` (cancela timeout)
- Botón "Finalizar" → resetear Context + navegar a `/` (cancela timeout)
- Cleanup timeout en unmount

**Implementación (Resumen - DÍA 3):**

```tsx
// app/exito/page.tsx
'use client';

import { useEffect, useState, useCallback } from 'react';
import { useRouter } from 'next/navigation';
import { Button } from '@/components';
import { useAppState } from '@/lib/context';

export default function ExitoPage() {
  const router = useRouter();
  const { resetState } = useAppState();
  const [countdown, setCountdown] = useState(5);

  const handleFinish = useCallback(() => {
    resetState();
    router.push('/');
  }, [resetState, router]);

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

    // Cleanup: cancelar timer al desmontar componente
    return () => clearInterval(timer);
  }, [handleFinish]);

  return (
    <div className="min-h-screen bg-slate-50 p-6 flex items-center justify-center">
      <div className="max-w-2xl mx-auto text-center">
        {/* Checkmark SVG Grande */}
        <div className="mb-6">
          <svg
            className="w-32 h-32 mx-auto text-green-600"
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

        {/* Mensaje Principal */}
        <h1 className="text-3xl font-bold text-green-600 mb-4">
          ¡Acción completada exitosamente!
        </h1>

        {/* Mensaje Secundario */}
        <p className="text-xl text-gray-700 mb-2">
          El spool ha sido actualizado en Google Sheets
        </p>

        {/* Countdown */}
        <p className="text-lg text-gray-500 mb-8">
          Volviendo al inicio en {countdown} {countdown === 1 ? 'segundo' : 'segundos'}...
        </p>

        {/* Botones */}
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

**Características UI/UX:**
- ✅ Checkmark SVG verde grande (128px)
- ✅ Countdown visible con actualización cada segundo
- ✅ useCallback para memoizar handleFinish
- ✅ Cleanup timer en unmount (previene memory leaks)
- ✅ Centrado vertical y horizontal (flex + items-center + justify-center)
- ✅ 2 botones para salir anticipadamente

---

## 3. Estilos y Diseño Tailwind

### 3.1 Paleta de Colores ZEUES

**Configuración completa:**

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

**Tabla de Uso:**

| Color | Hex | Uso Principal | Clase Tailwind |
|-------|-----|---------------|----------------|
| Naranja | #FF5B00 | Header, botones primarios, branding | `bg-[#FF5B00]` o `text-[#FF5B00]` |
| Naranja oscuro | #E64A19 | Hover naranja | `hover:bg-[#E64A19]` |
| Cyan | #0891B2 | INICIAR acción (P3, P5A, botones) | `bg-cyan-600 hover:bg-cyan-700` |
| Verde | #16A34A | COMPLETAR acción (P3, P5B, checkmark) | `bg-green-600 hover:bg-green-700` |
| Rojo | #DC2626 | Errores, validaciones fallidas | `bg-red-50 border-red-200 text-red-700` |
| Gris claro | #F8FAFC | Fondo app (slate-50) | `bg-slate-50` |
| Gris medio | #6B7280 | Textos secundarios | `text-gray-600` |
| Gris oscuro | #374151 | Textos principales | `text-gray-700` |

---

### 3.2 Tipografía

**Tamaños de Fuente:**

| Elemento | Clase Tailwind | Tamaño px | Uso |
|----------|----------------|-----------|-----|
| Header principal | `text-3xl` | 30px | H1 en P1 "ZEUES - Trazabilidad" |
| Título página | `text-2xl` | 24px | H1 en P2-P6 |
| Subtítulo | `text-xl` | 20px | H2, subtítulos, botones |
| Texto normal | `text-lg` | 18px | Párrafos, lista items |
| Texto pequeño | `text-sm` | 14px | Descripciones, subtítulos en botones |

**Pesos de Fuente:**

| Peso | Clase Tailwind | Uso |
|------|----------------|-----|
| Bold | `font-bold` | Headers principales |
| Semibold | `font-semibold` | Títulos, botones |
| Medium | `font-medium` | Énfasis en textos |
| Normal | `font-normal` | Textos regulares |

**Ejemplo de Jerarquía Tipográfica:**

```tsx
// Header principal (P1)
<h1 className="text-3xl font-bold text-center text-[#FF5B00]">
  ZEUES - Trazabilidad
</h1>

// Título página (P2-P6)
<h1 className="text-2xl font-semibold text-center">
  Hola Juan Pérez
</h1>

// Subtítulo
<h2 className="text-xl text-center text-gray-600">
  ¿Qué vas a hacer?
</h2>

// Botón texto
<button className="text-xl font-semibold">
  ARMADO (ARM)
</button>

// Descripción botón
<div className="text-sm font-normal">
  Asignar spool antes de trabajar
</div>
```

---

### 3.3 Responsive Mobile-First

**Breakpoints Tailwind:**

| Breakpoint | Tamaño | Dispositivo | Prefijo |
|------------|--------|-------------|---------|
| Base | <640px | Móvil vertical | (sin prefijo) |
| sm | ≥640px | Móvil horizontal | `sm:` |
| md | ≥768px | Tablet vertical | `md:` |
| lg | ≥1024px | Tablet horizontal / Desktop | `lg:` |

**Estrategia MVP:**

1. **Diseñar para móvil primero** (sin prefijo)
2. **Agregar `md:` solo si necesario** (tablet 10" = 768px-1024px target)
3. **NO usar `lg:` en MVP** (desktop no es prioridad)

**Ejemplos Responsive:**

```tsx
// Grid responsive: 1 columna móvil, 2 columnas tablet
<div className="grid grid-cols-1 md:grid-cols-2 gap-4">
  {/* Items */}
</div>

// Padding responsive
<div className="p-4 md:p-6">
  {/* Contenido */}
</div>

// Texto responsive (raro en MVP, tamaños fijos preferidos)
<h1 className="text-2xl md:text-3xl">
  Título
</h1>

// Botón Volver tamaño responsive
<button className="text-lg md:text-xl font-semibold">
  ← Volver
</button>
```

**Botones Grandes (Mobile-First):**

Todos los botones principales son **h-16** (64px) para maximizar touch targets:

```tsx
// Target táctil grande (mínimo 44x44px, ideal 64x64px)
<button className="w-full h-16 rounded-lg text-xl font-semibold">
  INICIAR ACCIÓN
</button>
```

**Justificación:** Trabajadores usan guantes y tablets en entorno industrial. 64px es el mínimo recomendado para touch con guantes.

---

### 3.4 Espaciado y Layout

**Padding/Margin Consistentes:**

| Elemento | Clase Tailwind | Tamaño px | Uso |
|----------|----------------|-----------|-----|
| Padding página | `p-6` | 24px | Contenedor principal min-h-screen |
| Padding card | `p-4` o `p-6` | 16px / 24px | Cards, items lista |
| Margin bottom secciones | `mb-6` o `mb-8` | 24px / 32px | Separación entre secciones |
| Gap grid | `gap-4` | 16px | Espacio entre items grid |
| Space entre botones | `space-y-3` o `space-y-4` | 12px / 16px | Stack vertical botones |

**Layout Containers:**

```tsx
// Contenedor principal (todas las páginas)
<div className="min-h-screen bg-slate-50 p-6">
  {/* Botón Volver si aplica */}

  <div className="max-w-2xl mx-auto">
    {/* Contenido centrado, max-width 672px */}
  </div>
</div>
```

**Justificación `max-w-2xl` (672px):**
- Tablet 10" en landscape ≈ 1024px width
- Content max 672px deja 176px margin cada lado
- Contenido centrado y legible
- Botones no se estiran demasiado horizontalmente

---

## 4. Wireframes Visuales

### 4.1 Flujo INICIAR Completo

```
┌─────────────────────────────────────────────────────────────────┐
│                       FLUJO INICIAR ARM                         │
└─────────────────────────────────────────────────────────────────┘

P1: Identificación           P2: Operación               P3: Tipo
┌──────────────────┐        ┌──────────────────┐        ┌──────────────────┐
│  ZEUES           │        │  ← Volver        │        │  ← Volver        │
│  ¿Quién eres?    │   →    │  Hola Juan,      │   →    │  ARMADO (ARM)    │
│                  │        │  ¿Qué haces?     │        │  ¿Qué acción?    │
│ [Juan Pérez]     │        │                  │        │                  │
│ [María López]    │        │ [🔧 ARM]         │        │ [🔵 INICIAR]     │
│ [Carlos Díaz]    │        │ [🔥 SOLD]        │        │ [✅ COMPLETAR]   │
│ [Ana García]     │        │                  │        │                  │
└──────────────────┘        └──────────────────┘        └──────────────────┘
        │                           │                           │
        └───────────────────────────┴───────────────────────────┘
                                    │
                                    ↓

P4A: Seleccionar Spool     P5A: Confirmar             P6: Éxito
┌──────────────────┐        ┌──────────────────┐        ┌──────────────────┐
│  ← Volver        │        │  ← Volver        │        │                  │
│  Selecciona      │   →    │  ¿Confirmas      │   →    │   ✓ GRANDE       │
│  spool INICIAR   │        │  INICIAR ARM?    │        │  ¡Completado!    │
│                  │        │                  │        │                  │
│ [MK-1335-011]    │        │ ┌──────────────┐ │        │  Volviendo en    │
│ [MK-1335-012]    │        │ │ Resumen:     │ │        │  5 seg...        │
│ [MK-1335-013]    │        │ │ Juan/ARM/MK  │ │        │                  │
│ [MK-1335-014]    │        │ └──────────────┘ │        │ [REGISTRAR OTRA] │
│ [MK-1335-015]    │        │ [✓ CONFIRMAR]    │        │ [FINALIZAR]      │
└──────────────────┘        └──────────────────┘        └──────────────────┘
                                                                 │
                                                                 ↓
                                                          Vuelve a P1
```

---

### 4.2 Flujo COMPLETAR Completo

```
┌─────────────────────────────────────────────────────────────────┐
│                     FLUJO COMPLETAR SOLD                        │
└─────────────────────────────────────────────────────────────────┘

P1: Identificación           P2: Operación               P3: Tipo
┌──────────────────┐        ┌──────────────────┐        ┌──────────────────┐
│  ZEUES           │        │  ← Volver        │        │  ← Volver        │
│  ¿Quién eres?    │   →    │  Hola Carlos,    │   →    │  SOLDADO (SOLD)  │
│                  │        │  ¿Qué haces?     │        │  ¿Qué acción?    │
│ [Juan Pérez]     │        │                  │        │                  │
│ [María López]    │        │ [🔧 ARM]         │        │ [🔵 INICIAR]     │
│ [Carlos Díaz] ✓  │        │ [🔥 SOLD] ✓      │        │ [✅ COMPLETAR] ✓ │
│ [Ana García]     │        │                  │        │                  │
└──────────────────┘        └──────────────────┘        └──────────────────┘
        │                           │                           │
        └───────────────────────────┴───────────────────────────┘
                                    │
                                    ↓

P4B: Mis Spools            P5B: Confirmar             P6: Éxito
┌──────────────────┐        ┌──────────────────┐        ┌──────────────────┐
│  ← Volver        │        │  ← Volver        │        │                  │
│  Selecciona TU   │   →    │  ¿Confirmas      │   →    │   ✓ GRANDE       │
│  spool COMPLETAR │        │  COMPLETAR SOLD? │        │  ¡Completado!    │
│                  │        │                  │        │                  │
│ [MK-1339-051]    │        │ ┌──────────────┐ │        │  Volviendo en    │
│ [MK-1339-052]    │        │ │ Resumen:     │ │        │  5 seg...        │
│  (solo mis       │        │ │ Carlos/SOLD  │ │        │                  │
│   spools en      │        │ │ MK-1339-051  │ │        │ [REGISTRAR OTRA] │
│   progreso)      │        │ │ Fecha: hoy   │ │        │ [FINALIZAR]      │
│                  │        │ └──────────────┘ │        │                  │
│                  │        │ [✓ CONFIRMAR]    │        │                  │
└──────────────────┘        └──────────────────┘        └──────────────────┘
                                                                 │
                                                                 ↓
                                                          Vuelve a P1
```

---

## 5. Apéndices Técnicos

### 5.1 Estructura de Archivos Implementados (DÍA 1-3)

```
zeues-frontend/
├── app/
│   ├── layout.tsx                 ✅ DÍA 1 - AppProvider + metadata
│   ├── page.tsx                   ✅ DÍA 2 - P1 Identificación
│   ├── globals.css                ✅ DÍA 1 - Tailwind imports
│   ├── operacion/
│   │   └── page.tsx               ✅ DÍA 2 - P2 Operación
│   ├── tipo-interaccion/
│   │   └── page.tsx               ✅ DÍA 2 - P3 Tipo
│   ├── seleccionar-spool/
│   │   └── page.tsx               ✅ DÍA 3 - P4 Seleccionar Spool
│   ├── confirmar/
│   │   └── page.tsx               ✅ DÍA 3 - P5 Confirmar
│   └── exito/
│       └── page.tsx               ✅ DÍA 3 - P6 Éxito
│
├── components/
│   ├── index.ts                   ✅ DÍA 2 - Exports centralizados
│   ├── Button.tsx                 ✅ DÍA 2 - 36 líneas
│   ├── Card.tsx                   ✅ DÍA 2 - 14 líneas
│   ├── List.tsx                   ✅ DÍA 2 - 40 líneas
│   ├── Loading.tsx                ✅ DÍA 2 - 15 líneas
│   └── ErrorMessage.tsx           ✅ DÍA 2 - 20 líneas
│
├── lib/
│   ├── context.tsx                ✅ DÍA 2 - Context API (62 líneas)
│   ├── types.ts                   ⏳ DÍA 4 - Interfaces TypeScript
│   └── api.ts                     ⏳ DÍA 4 - API client (6 funciones)
│
├── public/
│   ├── next.svg                   ✅ DÍA 1
│   └── vercel.svg                 ✅ DÍA 1
│
├── .env.local                     ✅ DÍA 1 - NEXT_PUBLIC_API_URL
├── .gitignore                     ✅ DÍA 1
├── next.config.js                 ✅ DÍA 1
├── package.json                   ✅ DÍA 1 - Dependencies
├── postcss.config.js              ✅ DÍA 1
├── tailwind.config.ts             ✅ DÍA 1 - Paleta ZEUES
├── tsconfig.json                  ✅ DÍA 1
├── README.md                      ✅ DÍA 1
└── TESTING-E2E.md                 ✅ DÍA 3 - Guía testing
```

**Total Archivos Implementados:** 29 archivos
**Líneas de Código (estimado):** ~1500 líneas (páginas + componentes + config)

---

### 5.2 Patterns y Convenciones

**Naming Conventions:**

| Elemento | Convention | Ejemplo |
|----------|------------|---------|
| Componentes | PascalCase | `Button`, `ErrorMessage` |
| Archivos componentes | PascalCase.tsx | `Button.tsx`, `List.tsx` |
| Archivos páginas | lowercase | `page.tsx`, `layout.tsx` |
| Hooks custom | useXxx | `useAppState`, `useWorkers` |
| Funciones API | camelCase | `getWorkers`, `iniciarAccion` |
| Interfaces | PascalCase | `ButtonProps`, `Worker` |
| Constantes | UPPER_SNAKE_CASE | `MOCK_WORKERS`, `API_URL` |

**File Organization Patterns:**

```tsx
// Pattern 1: Componente Simple
// 1. Imports
// 2. Interface Props
// 3. Componente funcional
// 4. Export default

import { ReactNode } from 'react';

interface CardProps {
  children: ReactNode;
  className?: string;
}

export function Card({ children, className = '' }: CardProps) {
  return <div className={`bg-white ${className}`}>{children}</div>;
}

// Pattern 2: Página con Estado
// 1. 'use client' directive
// 2. Imports
// 3. Mock data (si aplica)
// 4. Interfaces
// 5. Componente funcional con hooks
// 6. Handlers
// 7. JSX return

'use client';

import { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';

const MOCK_DATA = [...];

export default function PageName() {
  const router = useRouter();
  const [state, setState] = useState();

  useEffect(() => {
    // Effects
  }, []);

  const handleAction = () => {
    // Handler logic
  };

  return <div>{/* JSX */}</div>;
}
```

**Estado y Efectos:**

```tsx
// Pattern: Loading + Error + Data
const [data, setData] = useState([]);
const [loading, setLoading] = useState(true);
const [error, setError] = useState('');

const fetchData = async () => {
  try {
    setLoading(true);
    setError('');
    const result = await apiCall();
    setData(result);
  } catch (err) {
    setError('Error message');
  } finally {
    setLoading(false);
  }
};

// Pattern: Render condicional
{loading && <Loading />}
{error && <ErrorMessage message={error} onRetry={fetchData} />}
{!loading && !error && <DataComponent data={data} />}
```

---

### 5.3 Tailwind Utilities Más Usados

**Layout:**
```css
.min-h-screen          /* 100vh mínimo */
.max-w-2xl             /* max-width: 672px */
.mx-auto               /* margin horizontal auto (centrado) */
.flex                  /* display: flex */
.items-center          /* align-items: center */
.justify-center        /* justify-content: center */
.grid                  /* display: grid */
.grid-cols-1           /* 1 columna */
.md:grid-cols-2        /* 2 columnas en tablet+ */
```

**Spacing:**
```css
.p-6                   /* padding: 24px */
.mb-6                  /* margin-bottom: 24px */
.space-y-4             /* gap vertical 16px entre hijos */
.gap-4                 /* gap: 16px (grid/flex) */
```

**Typography:**
```css
.text-xl               /* font-size: 20px */
.font-semibold         /* font-weight: 600 */
.text-center           /* text-align: center */
.text-gray-700         /* color: #374151 */
```

**Background:**
```css
.bg-slate-50           /* #F8FAFC (fondo app) */
.bg-white              /* #FFFFFF */
.bg-[#FF5B00]          /* Naranja ZEUES custom */
.bg-cyan-600           /* #0891B2 (INICIAR) */
.bg-green-600          /* #16A34A (COMPLETAR) */
```

**Borders & Shadows:**
```css
.rounded-lg            /* border-radius: 8px */
.shadow-md             /* box-shadow media */
.hover:shadow-md       /* shadow en hover */
.border                /* border: 1px solid */
.border-gray-200       /* color border gris claro */
```

**Interactive:**
```css
.transition-colors     /* transición suave colores */
.duration-200          /* 200ms */
.hover:bg-cyan-700     /* color hover */
.disabled:opacity-50   /* opacity 0.5 si disabled */
.cursor-not-allowed    /* cursor no permitido */
```

---

### 5.4 Checklist de Calidad UI

**Accesibilidad:**
```
[ ] Botones con h-16 mínimo (64px touch target)
[ ] Contraste colores suficiente (WCAG AA mínimo)
[ ] Texto legible text-xl (20px) mínimo
[ ] Focus states visibles (outline por defecto)
[ ] Loading states con mensaje descriptivo
[ ] Error messages claros y accionables
```

**UX:**
```
[ ] Feedback visual inmediato (hover, active)
[ ] Loading durante operaciones async
[ ] Confirmación antes de acciones destructivas (Cancelar)
[ ] Mensajes de éxito claros (P6)
[ ] Empty states informativos (P4 sin spools)
[ ] Navegación Volver en todas las páginas
```

**Performance:**
```
[ ] Componentes funcionales (no clases)
[ ] useState para estado local simple
[ ] useCallback para handlers en useEffect
[ ] Cleanup en useEffect (timers, suscripciones)
[ ] Suspense boundaries para useSearchParams()
[ ] Mock data por ahora (DÍA 4 integra API real)
```

**Mobile-First:**
```
[ ] Diseño base para móvil (sin prefijo)
[ ] Grid 1 columna por defecto
[ ] Botones w-full (ancho completo)
[ ] Padding/margin generosos (touch friendly)
[ ] Texto grande (text-xl, text-lg)
[ ] md: prefijo solo si necesario (tablet)
```

---

**FIN - proyecto-frontend-ui.md - Detalles Implementación UI - v1.0 - 10 Nov 2025**

**Resumen:**
- ✅ 5 componentes base documentados con código completo
- ✅ 6 páginas detalladas con wireframes y lógica
- ✅ Paleta colores Tailwind ZEUES (#FF5B00, #0891B2, #16A34A)
- ✅ Patterns y convenciones establecidos
- ✅ Mobile-first responsive design
- ✅ Checklist de calidad UI/UX

**Referencias:**
- Arquitectura y estado: Ver `proyecto-frontend.md`
- Testing E2E: Ver `TESTING-E2E.md` en `zeues-frontend/`
- Backend API: Ver `proyecto-backend.md`

**Estado:** DÍA 1-3 COMPLETADOS (60% progreso frontend)
**Próximo:** DÍA 4 - @api-integrator integra API real (reemplazar mock data)
