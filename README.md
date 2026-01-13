# ZEUES - Sistema de Trazabilidad para Manufactura

[![v2.0](https://img.shields.io/badge/version-2.0--dev-orange)](https://github.com)
[![Production](https://img.shields.io/badge/status-production-green)](https://zeues-frontend.vercel.app)
[![Backend](https://img.shields.io/badge/backend-railway-blue)](https://zeues-backend-mvp-production.up.railway.app)
[![Frontend](https://img.shields.io/badge/frontend-vercel-black)](https://zeues-frontend.vercel.app)

Sistema digital móvil-first para registro de acciones de manufactura en spools de cañerías con autenticación, auditoría completa y sincronización automática a Google Sheets.

**v2.0 EN DESARROLLO:** Autenticación JWT, Sistema de Roles, Auditoría (Event Sourcing), METROLOGÍA, Operaciones Batch

---

## 🚀 Producción

### v1.0 (Producción Activa)
**Aplicación Web:** https://zeues-frontend.vercel.app
**API Backend:** https://zeues-backend-mvp-production.up.railway.app
**API Docs:** https://zeues-backend-mvp-production.up.railway.app/docs

**Estado:** MVP v1.0 - 100% funcional y desplegado en producción

### v2.0 (Desarrollo Activo)
**Branch:** `v2.0-dev`
**Estado:** 🚧 En desarrollo - Event Sourcing + Sheet PRODUCCIÓN migrado
**Progress:** DÍA 4 (Metadata) - 6% completado
**Target Launch:** 27 Dic 2025

---

## 📋 Descripción

ZEUES digitaliza el registro de acciones de manufactura en piso de producción mediante tablets con autenticación por roles y auditoría completa. Los usuarios pueden:

- **Autenticarse** con email (JWT + roles: Trabajador/Supervisor/Administrador)
- **Iniciar acciones** para auto-asignarse spools antes de trabajar
- **Completar acciones** al terminar su trabajo
- **Operaciones batch** (multiselect) para aumentar productividad 80%+
- **Auditoría completa** con Event Sourcing (hoja Metadata)
- Actualización automática en Google Sheets (fuente de verdad)
- Interfaz optimizada para uso con guantes en ambiente industrial

### Características v1.0 (Producción)

✅ Registro de 2 operaciones: Armado (ARM) y Soldado (SOLD)
✅ Flujo INICIAR → COMPLETAR con asignación automática
✅ Validación de propiedad: solo quien inicia puede completar
✅ Filtrado inteligente de spools disponibles
✅ Actualización tiempo real en Google Sheets
✅ Interfaz mobile-first (botones grandes h-16, alto contraste)
✅ Tiempo de registro < 30 segundos

### Características v2.0 (En Desarrollo)

🚧 **Sistema de Roles** - Autenticación JWT con 3 roles (Trabajador/Supervisor/Admin)
🚧 **Auditoría Event Sourcing** - Hoja Metadata con log completo inmutable (append-only)
🚧 **METROLOGÍA** - Tercera operación (inspección calidad post-soldadura)
🚧 **Operaciones Batch** - Multiselect con checkboxes (5+ spools simultáneos)
🚧 **Admin Panel** - CRUD usuarios, reportes, metadata query
✅ **Sheet PRODUCCIÓN** - Migrado a Sheet oficial (2,493 spools reales)
✅ **Worker Model v2.0** - ID numérico + Rol (7 roles disponibles)
✅ **MetadataRepository** - Event Sourcing implementado (5 métodos)

---

## 🛠️ Tech Stack

### Backend
- **Python 3.11** + FastAPI
- **Google Sheets API** (gspread) - Base de datos
- **Pydantic** - Validación de datos
- **Pytest** - Testing (coverage > 80%)
- **Deploy:** Railway

### Frontend
- **Next.js 14** + TypeScript
- **Tailwind CSS** - Estilos
- **React Context API** - Estado compartido
- **Playwright** - Testing E2E
- **Deploy:** Vercel

### Infraestructura
- **Google Cloud Platform** - Service Account (zeus-mvp)
- **Google Sheets** - Base de datos (TESTING + PRODUCCIÓN)
- **CI/CD:** GitHub Actions

---

## 📁 Estructura del Proyecto

```
ZEUES-by-KM/
├── backend/                    # FastAPI backend
│   ├── app/
│   │   ├── models/            # Pydantic models
│   │   ├── services/          # Business logic
│   │   ├── repositories/      # Google Sheets access
│   │   ├── routes/            # API endpoints
│   │   └── exceptions/        # Custom exceptions
│   ├── tests/                 # Pytest tests
│   ├── main.py                # FastAPI app
│   └── requirements.txt
│
├── zeues-frontend/            # Next.js frontend
│   ├── app/                   # App router (7 páginas)
│   ├── components/            # React components
│   ├── lib/                   # API integration
│   ├── context/               # State management
│   └── tests/                 # Playwright E2E
│
├── docs/                      # Documentación
│   ├── GOOGLE-RESOURCES.md   # Configuración Google
│   └── ...
│
├── proyecto.md                # Especificación MVP v1.0
├── proyecto-backend.md        # Docs técnicas backend v1.0
├── proyecto-frontend.md       # Docs arquitectura frontend v1.0
├── proyecto-v2.md             # 🆕 Roadmap y visión v2.0
├── proyecto-v2-backend.md     # 🆕 Docs técnicas backend v2.0
├── proyecto-v2-frontend.md    # 🆕 Docs técnicas frontend v2.0
└── CLAUDE.md                  # Guía desarrollo
```

---

## 🚀 Setup Local

### Requisitos
- Python 3.11+
- Node.js 18+
- Cuenta Google Cloud con Service Account configurado

### Backend

```bash
# 1. Activar virtual environment
cd backend
source venv/bin/activate  # macOS/Linux
# venv\Scripts\activate   # Windows

# 2. Instalar dependencias
pip install -r requirements.txt

# 3. Configurar variables de entorno
cp .env.example .env
# Editar .env con credenciales de Google Service Account

# 4. Ejecutar servidor de desarrollo
uvicorn main:app --reload --port 8000

# 5. Ejecutar tests
PYTHONPATH=/Users/sescanella/Proyectos/ZEUES-by-KM pytest
```

**Backend corriendo en:** http://localhost:8000
**API Docs:** http://localhost:8000/docs

### Frontend

```bash
# 1. Instalar dependencias
cd zeues-frontend
npm install

# 2. Configurar variables de entorno
cp .env.example .env.local
# Editar NEXT_PUBLIC_API_URL=http://localhost:8000

# 3. Ejecutar servidor de desarrollo
npm run dev

# 4. Ejecutar tests E2E
npx playwright test

# 5. Ver reporte de tests
npx playwright show-report
```

**Frontend corriendo en:** http://localhost:3000

---

## 🔐 Variables de Entorno

### Backend (.env)

```env
# Google Cloud
GOOGLE_CLOUD_PROJECT_ID=zeus-mvp
GOOGLE_SERVICE_ACCOUNT_EMAIL=zeus-mvp@zeus-mvp.iam.gserviceaccount.com
GOOGLE_PRIVATE_KEY="-----BEGIN PRIVATE KEY-----\n...\n-----END PRIVATE KEY-----\n"

# Google Sheets v1.0
# GOOGLE_SHEET_ID=11v8fD5Shn0RSzDceZRvXhE9z4RIOBmPA9lpH5_zF-wM  # TESTING (deprecated)

# Google Sheets v2.0 (PRODUCCIÓN - ACTIVO)
GOOGLE_SHEET_ID=17iOaq2sv4mSOuJY4B8dGQIsWTTUKPspCtb7gk6u-MaQ
HOJA_METADATA_NOMBRE=Metadata  # Event Sourcing log (append-only)
```

### Frontend (.env.local)

```env
NEXT_PUBLIC_API_URL=http://localhost:8000  # Desarrollo
# NEXT_PUBLIC_API_URL=https://zeues-backend-mvp-production.up.railway.app  # Producción
```

**Nota:** Ver `docs/GOOGLE-RESOURCES.md` para instrucciones completas de configuración.

---

## 🧪 Testing

### Backend - Pytest

```bash
cd backend
source venv/bin/activate

# Ejecutar todos los tests
PYTHONPATH=/Users/sescanella/Proyectos/ZEUES-by-KM pytest

# Con coverage
PYTHONPATH=/Users/sescanella/Proyectos/ZEUES-by-KM pytest --cov=app

# Tests específicos
PYTHONPATH=/Users/sescanella/Proyectos/ZEUES-by-KM pytest tests/test_models.py
```

**Coverage:** > 80%

### Frontend - Playwright E2E

```bash
cd zeues-frontend

# Ejecutar tests E2E (headless)
npx playwright test

# Con UI interactiva
npx playwright test --ui

# Ver reporte
npx playwright show-report
```

**Test Cases:** 12 flujos E2E completos (ver `zeues-frontend/TESTING-E2E.md`)

---

## 🚢 Deployment

### Backend → Railway

**URL:** https://zeues-backend-mvp-production.up.railway.app

**Configuración:**
- Runtime: Python 3.11
- Start command: `uvicorn main:app --host 0.0.0.0 --port $PORT`
- Environment variables configuradas en Railway dashboard
- Health check: `GET /api/health`

**CI/CD:**
- GitHub Actions en `.github/workflows/backend.yml`
- Deploy automático en push a `main`

### Frontend → Vercel

**URL:** https://zeues-frontend.vercel.app

**Configuración:**
- Framework: Next.js 14
- Node version: 18.x
- Environment variables configuradas en Vercel dashboard
- Auto-deploy desde `main` branch

**Build:**
```bash
npm run build
npm run start
```

---

## 📚 Documentación

### Documentos Principales

#### v1.0 (Base Completada)
| Documento | Descripción |
|-----------|-------------|
| `proyecto.md` | Especificación completa del MVP v1.0 (visión, alcance, roadmap) |
| `proyecto-backend.md` | Documentación técnica backend v1.0 (arquitectura, modelos, servicios, API) |
| `proyecto-frontend.md` | Arquitectura frontend v1.0 (estructura, páginas, componentes) |
| `proyecto-frontend-ui.md` | Detalles implementación UI v1.0 (componentes, estilos, validaciones) |
| `zeues-frontend/TESTING-E2E.md` | Guía testing manual E2E (12 casos) |

#### v2.0 (Desarrollo Activo) 🆕
| Documento | Descripción |
|-----------|-------------|
| `proyecto-v2.md` | **Visión general y roadmap v2.0** - 5 funcionalidades nuevas, 16 días timeline |
| `proyecto-v2-backend.md` | **Docs técnicas backend v2.0** - Auth JWT, Metadata Event Sourcing, Batch operations |
| `proyecto-v2-frontend.md` | **Docs técnicas frontend v2.0** - Login, Multiselect, Admin Panel, Protected Routes |

#### Generales
| Documento | Descripción |
|-----------|-------------|
| `CLAUDE.md` | Guía rápida para desarrollo |
| `docs/GOOGLE-RESOURCES.md` | Configuración Google Cloud y Sheets |

### API Documentation

**Swagger UI (producción):** https://zeues-backend-mvp-production.up.railway.app/docs
**ReDoc:** https://zeues-backend-mvp-production.up.railway.app/redoc

#### Endpoints principales

```
GET  /api/health              - Health check
GET  /api/workers             - Lista trabajadores activos
POST /api/spools/iniciar      - Spools disponibles para iniciar (ARM/SOLD)
POST /api/spools/completar    - Spools propios para completar
POST /api/iniciar-accion      - Iniciar acción (V/W → 0.1)
POST /api/completar-accion    - Completar acción (V/W → 1.0)
```

---

## 🗺️ Flujo de Usuario

```
P1: Identificación Trabajador
    ↓ (selecciona nombre)
P2: Selección Operación (ARM/SOLD)
    ↓
P3: Tipo Interacción (INICIAR/COMPLETAR)
    ↓
P4: Selección Spool (filtrado inteligente)
    ↓
P5: Confirmación (resumen completo)
    ↓
P6: Éxito (mensaje + timeout 5seg → P1)
```

**Navegación:**
- Botón "Volver" en cada paso
- Botón "Cancelar" (rojo) vuelve a P1
- Auto-redirect a P1 después de 5 segundos en P6

---

## 🎯 Roadmap

### ✅ v1.0 MVP (Completado - Nov 2025)
- Backend FastAPI + Google Sheets
- Frontend Next.js mobile-first
- 2 operaciones (ARM/SOLD)
- Deploy Railway + Vercel
- Testing E2E completo
- 113 tests backend + 17 tests frontend passing

### 🚧 v2.0 (En Desarrollo - Dic 2025)
**Timeline:** 10 Dic - 27 Dic 2025 (16 días)
**Progress:** DÍA 4 (6% completado)

**Fase 1: Backend (8 días)**
- [ ] DÍA 1-3: Sistema de Roles (JWT + UserRepository + AuthService)
- [x] DÍA 4: **Metadata Event Sourcing** (60% completado)
  - [x] MetadataEvent model (10 columnas)
  - [x] MetadataRepository (5 métodos)
  - [x] Worker model v2.0 (id + rol)
  - [ ] Integración Services
- [ ] DÍA 5-6: MetadataMiddleware + METROLOGÍA
- [ ] DÍA 7-8: Multiselect Batch
- **Target:** 208 tests passing (+95 nuevos)

**Fase 2: Frontend (5 días)**
- [ ] DÍA 9-11: Auth + Roles (Login, AuthContext, Protected Routes)
- [ ] DÍA 12-14: METROLOGÍA + Multiselect UI
- **Target:** 25 tests E2E (+8 nuevos)

**Fase 3: Deploy (3 días)**
- [x] DÍA 15: Sheet PRODUCCIÓN preparado (Metadata headers creados)
- [ ] DÍA 16: Migración y Deploy Railway + Vercel
- [ ] DÍA 17: Post-Migración + Monitoreo

**Launch:** 27 Dic 2025

### 🔮 Fase 3 (Futuro)
- 10 operaciones completas (expandir desde 3)
- Reportes avanzados de productividad
- Modo offline con sincronización
- Notificaciones push

---

## 👥 Equipo

**Cliente:** Kronos Mining
**Sistema:** ZEUES (Manufacturing Traceability System)
**Proyecto:** Kronos Mining Pipe Spools Tracking

**Service Account:** zeus-mvp@zeus-mvp.iam.gserviceaccount.com
**Google Cloud Project:** zeus-mvp

---

## 📝 Notas Importantes

### Python Virtual Environment

**SIEMPRE trabajar dentro del virtual environment:**

```bash
# Activar ANTES de cualquier trabajo
source venv/bin/activate

# Instalar paquetes dentro del venv
pip install <package-name>

# Actualizar requirements después de instalar
pip freeze > requirements.txt
```

### TypeScript

**NUNCA usar `any` type:**
- ❌ `any` → ESLint error
- ✅ `unknown` para tipos dinámicos
- ✅ Tipos explícitos para funciones
- ✅ Validación con type guards

```bash
# Validar antes de commit
npx tsc --noEmit  # TypeScript
npm run lint      # ESLint
npm run build     # Build producción
```

### Google Sheets

**Sheet TESTING (v1.0 - deprecated):**
- ID: `11v8fD5Shn0RSzDceZRvXhE9z4RIOBmPA9lpH5_zF-wM`
- URL: https://docs.google.com/spreadsheets/d/11v8fD5Shn0RSzDceZRvXhE9z4RIOBmPA9lpH5_zF-wM
- Estado: ⚠️ Deprecated - Solo referencia histórica

**Sheet PRODUCCIÓN (v2.0 - ACTIVO):** ✅
- ID: `17iOaq2sv4mSOuJY4B8dGQIsWTTUKPspCtb7gk6u-MaQ`
- URL: https://docs.google.com/spreadsheets/d/17iOaq2sv4mSOuJY4B8dGQIsWTTUKPspCtb7gk6u-MaQ
- Título: `__Kronos_Registro_Piping R04`
- Filas: 2,493 spools reales
- Hojas:
  - **Operaciones** (READ-ONLY) - 65 columnas, datos base
  - **Trabajadores** (READ-ONLY) - 9 trabajadores con Id + Rol
  - **Metadata** ✅ (WRITE-ONLY) - Event Sourcing log (10 columnas A-J)
  - **Roles** (pendiente) - Para autenticación v2.0

---

## 🔒 Seguridad

- **Credenciales:** NUNCA commitear archivos JSON de Service Account
- **Variables de entorno:** Usar `.env.local` (en .gitignore)
- **Secrets:** Configurar en Railway/Vercel dashboards
- **Service Account:** Permisos mínimos (solo lectura/escritura en Sheets específicos)

---

## 📄 Licencia

Proyecto privado - Kronos Mining / ZEUES System

---

## 🆘 Soporte

Para dudas o problemas:
1. Revisar documentación en `/docs`
2. Consultar `proyecto.md` y `proyecto-backend.md`
3. Ver guía de desarrollo en `CLAUDE.md`

---

**Última actualización:** 10 Diciembre 2025
**Versión:** 2.0.0-dev (En Desarrollo Activo)
**Branch:** v2.0-dev
**Progress:** DÍA 4 - Metadata Event Sourcing (60% completado)
