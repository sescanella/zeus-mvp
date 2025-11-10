# ZEUES Frontend - Sistema de Trazabilidad MVP

Web app mobile-first para registro de acciones ARM/SOLD en tablets industriales.

## Stack Tecnológico

- **Framework:** Next.js 14+ (App Router)
- **Lenguaje:** TypeScript
- **Estilos:** Tailwind CSS
- **State:** Context API simple
- **API:** Fetch nativo (NO axios)
- **Deploy:** Vercel

## Estructura del Proyecto

```
zeues-frontend/
├── app/                    # Páginas Next.js (7 rutas)
│   ├── page.tsx            # P1: Identificación
│   ├── operacion/          # P2: Seleccionar operación
│   ├── tipo-interaccion/   # P3: INICIAR o COMPLETAR
│   ├── seleccionar-spool/  # P4: Lista spools
│   ├── confirmar/          # P5: Confirmación
│   └── exito/              # P6: Éxito + timeout
├── components/             # Componentes reutilizables (5 max)
├── lib/                    # API client, Context, types
├── public/                 # Assets estáticos
└── styles/                 # Tailwind globals.css
```

## Instalación y Setup

```bash
# Instalar dependencias
npm install

# Variables de entorno
cp .env.local.example .env.local
# Editar NEXT_PUBLIC_API_URL con URL backend

# Dev server
npm run dev              # http://localhost:3000

# Build producción
npm run build
npm run start

# Linting
npm run lint
```

## Variables de Entorno

```bash
# .env.local (desarrollo)
NEXT_PUBLIC_API_URL=http://localhost:8000

# Producción (Vercel dashboard)
NEXT_PUBLIC_API_URL=https://zeues-backend.up.railway.app
```

## Comandos Útiles

```bash
# Desarrollo
npm run dev                # Dev server
npm run build              # Build producción
npm run lint               # Linter

# Testing API Backend
curl http://localhost:8000/api/health
curl http://localhost:8000/api/workers
```

## Arquitectura MVP

**Filosofía:** SIMPLE, funcional, rápido
- 7 páginas básicas (NO over-engineer)
- 5 componentes máximo
- Context API simple (NO Redux/Zustand)
- Fetch nativo (NO axios)
- Testing manual (NO tests automatizados en MVP)

## Flujos Principales

1. **INICIAR:** P1→P2→P3→P4A→P5A→P6→P1
2. **COMPLETAR:** P1→P2→P3→P4B→P5B→P6→P1

## Roadmap Desarrollo

- **DÍA 1 (12 Nov):** ✅ Setup + estructura (este archivo)
- **DÍA 2-3 (13-14 Nov):** Componentes + P1/P2/P3
- **DÍA 4 (15 Nov):** API integración + flujo INICIAR
- **DÍA 5 (16 Nov):** Flujo COMPLETAR
- **DÍA 6 (17 Nov):** Navegación + testing + deploy

## Documentación Completa

Ver: `/proyecto-frontend.md` (raíz del proyecto)

## Estado Actual

**Backend:** ✅ 100% completado (6 endpoints, 10/10 tests passing)
**Frontend:** DÍA 1 completado - Setup y estructura listos

## Contacto

Ver: `CLAUDE.md` y `proyecto.md` en raíz del proyecto
