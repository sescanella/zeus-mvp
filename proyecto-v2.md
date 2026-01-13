# ZEUES v2.0 - Sistema de Trazabilidad Avanzado

**Documentación del Proyecto - Versión 2.0**

📚 **Documentación del Proyecto:**
- `proyecto-v2.md` - Este archivo: Visión general y roadmap v2.0
- `proyecto-v2-backend.md` - **Documentación técnica completa del backend v2.0**
- `proyecto-v2-frontend.md` - **Documentación técnica completa del frontend v2.0**
- `proyecto.md` - Especificación MVP v1.0 (base completada)
- `proyecto-backend.md` - Documentación técnica backend v1.0
- `proyecto-frontend.md` - Documentación técnica frontend v1.0
- `CLAUDE.md` - Guía rápida para Claude Code

---

## 1. Visión y Objetivos v2.0

### Evolución desde MVP v1.0

**Estado v1.0 (Base - COMPLETADO):**
- ✅ 2 operaciones: ARM (Armado) y SOLD (Soldado)
- ✅ Flujos INICIAR/COMPLETAR básicos
- ✅ 4 trabajadores sin autenticación
- ✅ Actualización Google Sheets automática
- ✅ Restricción de propiedad implementada
- ✅ Deployado en producción (Railway + Vercel)
- ✅ 113 tests backend + 17 tests frontend passing

**Visión v2.0:**
Sistema robusto de trazabilidad empresarial con control de acceso por roles operativos múltiples, auditoría completa Event Sourcing, tercera operación (Metrología), operaciones batch para aumentar productividad 80%+, y migración a Sheet PRODUCCIÓN oficial.

### Objetivos v2.0

1. **Control de Acceso**: Sistema de roles operativos múltiples (Armador, Soldador, Metrologia, etc.) con validación granular - SIN autenticación JWT
2. **Trazabilidad Total**: Auditoría completa en hoja Metadata (quién, qué, cuándo) para cumplimiento y debugging ✅ **COMPLETADO**
3. **Expansión Operaciones**: Agregar METROLOGÍA como tercera operación crítica (nice-to-have si alcanza tiempo)
4. **Productividad**: Multiselect batch hasta 50 spools (reducir tiempo 80%: ~25 seg/spool → ~7 seg/spool)
5. **Producción Real**: Migrar de Sheet TESTING a Sheet PRODUCCIÓN oficial ✅ **COMPLETADO**
6. **CANCELAR**: Endpoint para revertir operaciones EN_PROGRESO (must-have)

### Criterios de Éxito v2.0

**Funcionales (Must-Have para 14 Dic):**
- ✅ 100% trabajadores con roles operativos múltiples definidos
- ✅ 100% acciones registradas en hoja Metadata (auditoría)
- ✅ Sheet PRODUCCIÓN funcionando sin errores
- 🔄 100% acciones validadas según rol del trabajador (backend + frontend)
- 🔄 Multiselect batch (hasta 50 spools simultáneos)
- 🔄 Endpoint CANCELAR operaciones EN_PROGRESO
- 🔄 Búsqueda TAG_SPOOL en P4
- 0 regresiones en funcionalidad v1.0

**Funcionales (Nice-to-Have si alcanza tiempo):**
- METROLOGÍA integrada y operativa (workflow BA→BB→BD→BF)

**Técnicos:**
- 150+ tests backend passing (v1.0: 113 → +40 nuevos mínimo)
- 20 tests E2E frontend passing (v1.0: 17 → +3 nuevos)
- Coverage backend > 80%
- Performance batch < 3 seg para 10 spools

---

## 2. Alcance v2.0 - Nuevas Funcionalidades

### 2.1. Sistema de Roles Operativos (**Ver `proyecto-v2-backend.md` sección 3 para detalles técnicos**)

**Objetivo:** Control de acceso basado en roles operativos múltiples por trabajador.

**Roles Operativos (7 tipos):**
- **Armador** → puede hacer operación ARM
- **Soldador** → puede hacer operación SOLD
- **Metrologia** → puede hacer operación METROLOGÍA
- **Ayudante** → puede asistir en operaciones
- **Revestimiento** → operaciones futuras
- **Pintura** → operaciones futuras
- **Despacho** → operaciones futuras

**Características:**
- **Multi-rol:** Un trabajador puede tener múltiples roles simultáneos (ej: Armador + Soldador)
- **Control granular:** Cada rol define exactamente qué operaciones puede realizar
- **Sin autenticación compleja:** NO requiere JWT, NO requiere login con email, NO hay niveles de privilegios
- **Simple:** Solo validación de rol antes de permitir cada operación

**Implementación:**
- Hoja "Trabajadores" (simplificada): Id, Nombre, Apellido, Activo
- Hoja "Roles" (nueva): Id (FK), Rol, Activo
- Backend: RoleRepository, validación rol en ActionService
- Frontend: Filtrado de operaciones disponibles según roles del trabajador

**Ejemplo:**
```
Trabajador Id=93 "Mauricio Rodriguez"
  → Roles: [Armador, Soldador]
  → Puede hacer: ARM ✅, SOLD ✅, METROLOGIA ❌

Trabajador Id=95 "Carlos Pimiento"
  → Roles: [Soldador, Metrologia]
  → Puede hacer: ARM ❌, SOLD ✅, METROLOGIA ✅
```

**Breaking Change:**
- Hoja "Trabajadores": Columna D (Rol) **ELIMINADA** (antes tenía rol único)
- Hoja "Roles": **NUEVA** (permite múltiples roles por trabajador)

**Documentación técnica completa:** `proyecto-v2-backend.md` sección 3

---

### 2.2. Hoja Metadata - Sistema de Auditoría ✅ **IMPLEMENTADO**

**Objetivo:** Registrar TODOS los movimientos para trazabilidad completa, debugging, auditoría y validación ownership.

**⚠️ CAMBIO CRÍTICO v2.0 - Hoja Operaciones READ-ONLY:**
- Hoja "Operaciones" es **READ-ONLY** (NUNCA se modifica desde el backend)
- Hoja "Metadata" registra TODOS los eventos (append-only, inmutable) para auditoría
- Estado actual se lee directamente de columnas específicas de Operaciones
- Validación de disponibilidad se basa en columnas de trabajadores y fechas (NO estados 0/0.1/1.0)
- Sistema v1.0 de estados numéricos (0 → 0.1 → 1.0) **ELIMINADO** en v2.0

**⚠️ IMPORTANTE - Coordenadas Volátiles:**
La hoja "Operaciones" cambia constantemente (se agregan/remueven columnas). **SIEMPRE usar nombres de columna (headers), NUNCA índices fijos**. Las coordenadas (AG, AI, AK) son solo referencia temporal - el código debe buscar por nombre.

**Condiciones de Disponibilidad v2.0 (por NOMBRE de columna):**

**INICIAR ARM:**
- Columna **"Fecha_Materiales"** **DEBE tener valor** (materiales llegaron)
- Columna **"Armador"** **DEBE estar vacía** (nadie asignado)

**INICIAR SOLD:**
- Columna **"Armador"** **DEBE tener valor** (ARM ya asignado/completado)
- Columna **"Soldador"** **DEBE estar vacía** (nadie asignado)

**Estructura Hoja Metadata:**
- Hoja "Metadata" en Google Sheets ✅ **(10 columnas A-J)**
- Columnas:
  - A: `id` (UUID único del evento)
  - B: `timestamp` (ISO 8601: 2025-12-10T14:30:00Z)
  - C: `evento_tipo` (INICIAR_ARM, COMPLETAR_ARM, INICIAR_SOLD, COMPLETAR_SOLD, INICIAR_METROLOGIA, COMPLETAR_METROLOGIA)
  - D: `tag_spool` (código del spool)
  - E: `worker_id` (ID numérico del trabajador)
  - F: `worker_nombre` (nombre completo del trabajador)
  - G: `operacion` (ARM, SOLD, METROLOGIA)
  - H: `accion` (INICIAR, COMPLETAR)
  - I: `fecha_operacion` (YYYY-MM-DD)
  - J: `metadata_json` (JSON con datos adicionales)

**Casos de Uso:**
- **Auditoría**: ¿Quién modificó spool X el día Y? → Consultar eventos filtrados por tag_spool
- **Trazabilidad**: Historia completa de un spool → Todos los eventos ordenados por timestamp
- **Ownership Validation**: ¿Quién inició ARM? → Leer worker_id del último evento INICIAR_ARM
- **Analytics**: Reportes productividad → Agrupar eventos por worker_id/operacion
- **Compliance**: Registro inmutable → Eventos nunca se modifican ni eliminan

**Implementación:**
- Backend: `MetadataRepository` ✅ (append_event, get_events_by_spool, get_latest_event)
- Modelos: `MetadataEvent` ✅ (Pydantic con to_sheets_row/from_sheets_row)
- Frontend: No requiere cambios (logging transparente en backend)

**Estado:** ✅ Headers creados, MetadataRepository implementado, modelos listos

---

### 2.3. Nueva Operación: METROLOGÍA (**Ver proyecto-v2-backend.md sección 5 + proyecto-v2-frontend.md sección 4**)

**Objetivo:** Tercera operación de manufactura (inspección de calidad post-soldadura).

**Workflow Completo:**
```
1. BA (Materiales)     → Fecha_Materiales llena
2. ARM (Armado)        → BB (Fecha_Armado) escrita al completar
3. SOLD (Soldado)      → BD (Fecha_Soldadura) escrita al completar
4. METROLOGÍA (Inspección) → BF (Fecha_Metrología) escrita al completar
```

**Estructura Google Sheets:**
- Columna X (24): estado_metrologia (0/0.1/1.0)
- Columna BF (58): fecha_metrologia (DD/MM/YYYY)
- Columna BG (59): metrologo (nombre trabajador)

**Validaciones:**
- **INICIAR**: Requiere SOLD=1.0 y BD llena
- **COMPLETAR**: Ownership validation (solo quien inició puede completar)

**UI:**
- Botón METROLOGÍA (verde 📏) en P2 - Operación
- Filtros automáticos en P4 (solo spools con SOLD completado)
- Colores distintos (verde vs naranja ARM vs rojo SOLD)

**Documentación técnica:**
- Backend: `proyecto-v2-backend.md` sección 5
- Frontend: `proyecto-v2-frontend.md` sección 4

---

### 2.4. Multiselect de Spools - Operaciones Batch (**Ver proyecto-v2-backend.md sección 6 + proyecto-v2-frontend.md sección 5**)

**Objetivo:** Seleccionar múltiples spools simultáneamente para reducir tiempo 80%+.

**Beneficio Cuantificado:**
- Actual (v1.0): 10 spools × 25 seg = 250 seg (~4 minutos)
- v2.0 batch: 15 seg setup + 15 seg selección + 5 seg confirmar = **35 seg para 5 spools**
- Por spool: 7 seg (reducción 72%)
- **Productividad: +257% (2.57x más rápido)**

**UX:**
- Checkboxes en cada Card spool
- "Seleccionar Todos" / "Deseleccionar Todos"
- Contador "X spools seleccionados"
- Confirmación batch: "¿Iniciar ARM en 5 spools?"
- Resultados batch: "5 de 5 exitosos" o "3 de 5 exitosos + 2 errores"

**Implementación:**
- Backend: Endpoints batch (`/api/iniciar-accion-batch`, `/completar-accion-batch`)
- Validación individual por spool (continúa si algunos fallan)
- Batch update Google Sheets (una sola llamada API para todos)
- Máximo 50 spools por batch (límite performance)

**Documentación técnica:**
- Backend: `proyecto-v2-backend.md` sección 6
- Frontend: `proyecto-v2-frontend.md` sección 5

---

### 2.5. Migración a Google Sheets PRODUCCIÓN ✅ **COMPLETADO**

**Objetivo:** Cambiar de Sheet TESTING a Sheet PRODUCCIÓN oficial. ✅ **MIGRADO**

**Sheets:**
- **v1.0 TESTING** (deprecated): `11v8fD5Shn0RSzDceZRvXhE9z4RIOBmPA9lpH5_zF-wM` - Desarrollo MVP
- **v2.0 PRODUCCIÓN** ✅ (activo): `17iOaq2sv4mSOuJY4B8dGQIsWTTUKPspCtb7gk6u-MaQ` - Datos reales
  - Título: `__Kronos_Registro_Piping R04`
  - 2,493 filas de datos reales

**Preparación Completada ✅:**
1. ✅ Hoja "Metadata" creada (10 columnas A-J) con headers - Event Sourcing
2. ✅ Hoja "Trabajadores" actualizada (4 columnas A-D: Id, Nombre, Apellido, Activo) - **Columna D (Rol) eliminada**
3. ✅ Hoja "Roles" creada (3 columnas A-C: Id, Rol, Activo) - **Multi-rol operativo** ✅
4. ✅ Hoja "Operaciones" confirmada (65 columnas, 2,493 filas) - READ-ONLY
5. ✅ Service Account con acceso Editor confirmado

**Migración Realizada (10-11 Dic 2025):**
- ✅ `GOOGLE_SHEET_ID` actualizado en `.env.local` y `backend/config.py`
- ✅ Variable `HOJA_METADATA_NOMBRE` agregada
- ✅ Headers Metadata creados en Sheet PRODUCCIÓN (10 columnas)
- ✅ **Hoja Trabajadores actualizada: Columna D (Rol) eliminada** (11 Dic)
- ✅ **Hoja Roles creada con headers y datos ejemplo** (11 Dic)
- ✅ Estructura verificada con Python scripts
- ⏳ Railway deployment pendiente (próximo paso)

**Nueva Arquitectura v2.0:**
- Hoja "Operaciones": **READ-ONLY** (NUNCA se modifica desde backend - solo lectura para validaciones)
- Hoja "Metadata": **APPEND-ONLY** (log inmutable de todos los eventos para auditoría + ownership validation)
- Hoja "Trabajadores": **READ-ONLY** (Id, Nombre, Apellido, Activo - SIN columna Rol)
- Hoja "Roles": **READ-ONLY** (Id, Rol, Activo - permite múltiples roles por trabajador)

**Columnas Operaciones v2.0 (Solo Lectura - por NOMBRE):**
- **"TAG_SPOOL"**: Código único de identificación
- **"Fecha_Materiales"**: Prerequisito para INICIAR ARM (debe tener valor)
- **"Fecha_Armado"**: Escrita al completar ARM
- **"Armador"**: Trabajador asignado a ARM (vacía = disponible)
- **"Soldador"**: Trabajador asignado a SOLD (vacía = disponible)

**⚠️ NUNCA usar coordenadas fijas (AG, AI, AK) en código - usar `find_column_by_header()`**

---

## 3. Arquitectura Técnica v2.0

### Stack (Sin Cambios Mayores)

**Backend:**
- Python 3.11+ + FastAPI 0.100+ + gspread 5.10+
- **Nuevas dependencias:** Ninguna (usa mismas de v1.0)
- **Nuevos módulos:** services (role, metadata), repositories (role, metadata)

**Frontend:**
- Next.js 14.2+ + React 18 + TypeScript 5 + Tailwind CSS
- **Nuevas dependencias:** Ninguna (usa mismas de v1.0)
- **Nuevos módulos:** Checkbox component, búsqueda TAG_SPOOL, CANCELAR button

**Deploy:**
- Backend: Railway (https://zeues-backend-v2-production.up.railway.app)
- Frontend: Vercel (https://zeues-v2.vercel.app)

### Cambios Arquitectónicos

**Backend (Ver `proyecto-v2-backend.md` sección 2):**
- 30 archivos (+8 nuevos vs v1.0)
- 10 endpoints REST (+4 nuevos: batch, cancelar, get roles)
- Middleware stack: CORS + Exception handlers (sin cambios vs v1.0)
- 150+ tests (+40 nuevos mínimo)

**Frontend (Ver `proyecto-v2-frontend.md` sección 2):**
- 29 archivos (+1 nuevo vs v1.0: Checkbox.tsx)
- 7 páginas (sin cambios vs v1.0)
- 6 componentes (+1 nuevo: Checkbox)
- Context API simple (sin cambios vs v1.0)
- 20 tests E2E (+3 nuevos)

### Google Sheets Schema v2.0

**Hojas:**
1. **Operaciones** (READ-ONLY): 65 columnas totales - NUNCA se modifica desde backend
2. **Trabajadores** (simplificada): 4 columnas (Id, Nombre, Apellido, Activo) - **Columna Rol eliminada**
3. **Metadata** (nueva): 10 columnas (Event Sourcing append-only) - ÚNICO lugar donde backend escribe
4. **Roles** (nueva): 3 columnas (Id, Rol, Activo) - **Multi-rol permitido**

**Columnas Críticas Operaciones (Solo Lectura - ⚠️ BUSCAR POR NOMBRE):**
| Nombre Columna (Header) | Uso v2.0 | Validación INICIAR ARM | Validación INICIAR SOLD |
|-------------------------|----------|------------------------|-------------------------|
| **"TAG_SPOOL"** | Identificador único | - | - |
| **"Fecha_Materiales"** | Prerequisito ARM | **DEBE tener valor** ✅ | - |
| **"Fecha_Armado"** | Confirmación ARM completado | - | (Info) |
| **"Armador"** | Worker asignado ARM | **DEBE estar vacía** ✅ | **DEBE tener valor** ✅ |
| **"Soldador"** | Worker asignado SOLD | - | **DEBE estar vacía** ✅ |

**⚠️ CRÍTICO:** Las coordenadas (AG, AI, AK) son **VOLÁTILES** y cambiarán cuando se agreguen/eliminen columnas. El código **DEBE** buscar columnas por nombre usando `worksheet.find()` o mapeo de headers.

**Relaciones:**
- Trabajadores ← 1:N → Roles (un trabajador puede tener múltiples roles)
- Metadata → Trabajadores (worker_id FK)

**Total columnas críticas:** 5 ("TAG_SPOOL", "Fecha_Materiales", "Fecha_Armado", "Armador", "Soldador")

---

## 4. Roadmap v2.0 - 3 Días (DEADLINE: 14 Dic 2025)

**Timeline ACTUALIZADO:**
- **Inicio:** 11 Dic 2025 (DÍA 1)
- **Deadline:** 14 Dic 2025 (DÍA 3) - **OBJETIVO**
- **Flexibilidad:** 15-16 Dic aceptable si es necesario
- **Desarrollo:** Solo con Claude Code (usuario)

---

### DÍA 1 (11-12 Dic): Backend Core - Roles + CANCELAR ✅ **100% COMPLETADO**

**Must-Have (prioridad crítica):**
1. ✅ RoleRepository (lectura hoja Roles) - **COMPLETADO** (224 líneas)
2. ✅ RoleService (validación rol por operación) - **COMPLETADO** (211 líneas)
3. ✅ ValidationService: validar rol antes de INICIAR/COMPLETAR - **COMPLETADO** (+170 líneas)
4. ✅ WorkerService: find_worker_by_id() - **COMPLETADO** (+37 líneas)
5. ✅ Endpoint POST /api/cancelar-accion (revertir EN_PROGRESO) - **COMPLETADO** (+120 líneas)
6. ✅ ActionService: migrar a worker_id (int) en vez de worker_nombre - **COMPLETADO** (+140 líneas)
7. ✅ Tests: 47 nuevos (roles + cancelar + worker_id) - **COMPLETADO** (47/47 passing = 100%)

**Entregable DÍA 1:** ✅ Backend valida roles + CANCELAR funcional + worker_id migration + 47 tests passing

**Archivos creados/modificados (11 Dic 2025):**
- Creados:
  - backend/models/role.py (185 líneas)
  - backend/repositories/role_repository.py (224 líneas)
  - backend/services/role_service.py (211 líneas)
  - tests/unit/test_role_repository.py (20 tests)
  - tests/unit/test_role_service.py (19 tests)
  - tests/unit/test_worker_service_v2.py (8 tests)
- Modificados:
  - ValidationService (+170 líneas - validar_puede_cancelar)
  - ActionService (+140 líneas - cancelar_accion + worker_id migration)
  - WorkerService (+37 líneas - find_worker_by_id)
  - models/metadata.py (CANCELAR event types)
  - models/action.py (worker_id migration)
  - routers/actions.py (+120 líneas - POST /api/cancelar-accion)
- Total código nuevo: ~1,300 líneas + 47 tests
- Tests: 47/47 passing (100% success)
- Breaking change: API ahora usa worker_id (int) en vez de worker_nombre (str)

---

### DÍA 2 (12-13 Dic): Backend Batch + Frontend Core

**Backend:** ✅ **COMPLETADO 12 Dic 2025**
1. ✅ ActionService: métodos batch (iniciarAccionBatch, completarAccionBatch) - +328 líneas
2. ✅ Endpoints POST /api/iniciar-accion-batch, /completar-accion-batch - +285 líneas con docstrings completos
3. ✅ Modelos Pydantic batch: BatchActionRequest, BatchActionResult, BatchActionResponse - +185 líneas
4. ✅ Manejo errores parciales (continuar si algunos spools fallan)
5. ✅ Ownership validation individual en completar batch
6. ✅ Performance < 3 seg para 10 spools (objetivo cumplido)
7. ✅ Tests batch: 14 nuevos (14/14 passing = 100%) - +620 líneas tests
   - Casos exitosos (todos los spools procesados)
   - Errores parciales (algunos spools fallan, otros exitosos)
   - Todos errores (ningún spool procesado)
   - Validación límites (50 max, lista vacía, exceder límite)
   - Ownership validation en completar batch
   - Performance tests
   - Operaciones ARM y SOLD

**Archivos Modificados/Creados DÍA 2:**
- backend/models/action.py (+185 líneas)
- backend/services/action_service.py (+328 líneas)
- backend/routers/actions.py (+285 líneas)
- tests/unit/test_action_service_batch.py (+620 líneas - nuevo archivo)
- Total código nuevo: ~1,418 líneas

**Frontend:** 🔴 **PENDIENTE**
1. 🔴 P2: Filtrado operaciones por roles (GET /workers/{id}/roles)
2. 🔴 P3: Botón CANCELAR
3. 🔴 P4: Multiselect UI (checkboxes, select all, contador)
4. 🔴 P4: Campo búsqueda TAG_SPOOL en tiempo real
5. 🔴 P5: Confirmación batch
6. 🔴 P6: Resultados batch (exitosos/fallidos)

**Entregable DÍA 2:** ✅ Backend Batch 100% completado | 🔴 Frontend pendiente

---

### DÍA 3 (13-14 Dic): Tests + Deploy + Validación

**Mañana (09:00-13:00):**
1. ✅ Tests E2E frontend: 3 nuevos (multiselect, cancelar, búsqueda)
2. ✅ Tests integración backend: flujos completos
3. ✅ Smoke tests: flujos críticos ARM/SOLD
4. ✅ Coverage > 80% backend

**Tarde (14:00-18:00):**
1. ✅ Deploy Railway con GOOGLE_SHEET_ID producción
2. ✅ Smoke tests producción (30 min)
3. ✅ Deploy Vercel frontend v2.0
4. ✅ Validación end-to-end en producción (1 hora)
5. ✅ Monitoreo inicial + ajustes críticos

**Entregable DÍA 3:** v2.0 en producción funcionando

---

### NICE-TO-HAVE (Solo si alcanza tiempo antes 14 Dic)

**METROLOGÍA:**
- Backend: validaciones prerequisitos (ARM+SOLD completados)
- Backend: columnas BF/BG escritura
- Frontend: botón verde METROLOGÍA en P2
- Tests: flujo completo METROLOGÍA

**Si NO alcanza tiempo:** Lanzar v2.0 SIN metrología, implementar después

---

## 5. Breaking Changes v1.0 → v2.0

### Incompatibilidades Críticas

⚠️ **BREAKING CHANGES:**

1. **Arquitectura READ-ONLY + Metadata Event Sourcing** ✅ **IMPLEMENTADO**
   - v1.0: Modificación directa de hoja "Operaciones" (columnas V, W, BA-BE) con estados 0/0.1/1.0
   - v2.0: Hoja "Operaciones" **READ-ONLY** + Eventos en "Metadata" (append-only)
   - **Impacto CRÍTICO:**
     - Hoja "Operaciones" **NUNCA se modifica** desde backend (solo lectura)
     - Sistema v1.0 estados 0/0.1/1.0 **ELIMINADO**
     - Validación disponibilidad basada en columnas de trabajadores (AG, AI, AK)
     - Metadata registra TODOS los eventos para auditoría + ownership validation
   - **Estado:** Backend implementado ✅, MetadataRepository ✅

2. **Modelo Worker Simplificado + Sistema Roles Múltiples** ✅ **SHEETS LISTOS** ⏳ Backend pendiente
   - v1.0: Worker (nombre, apellido, activo) - sin rol
   - v2.0: Worker (id, nombre, apellido, activo) + Hoja "Roles" separada
   - **Impacto:**
     - Hoja "Trabajadores": Columna D (Rol único) **ELIMINADA** ✅
     - Hoja "Roles": **CREADA** (Id, Rol, Activo) - permite múltiples roles por trabajador ✅
     - Un trabajador puede tener N roles simultáneos (ej: Id=93 tiene Armador + Soldador)
     - 7 roles operativos: Armador, Soldador, Ayudante, Metrologia, Revestimiento, Pintura, Despacho
   - **Estado:** Google Sheets listos ✅, implementación backend pendiente ⏳

3. **Validación de Rol por Operación** ⏳ PENDIENTE
   - v1.0: Cualquier trabajador puede hacer cualquier operación
   - v2.0: Validación de rol antes de permitir operación
   - **Impacto:**
     - Armador solo puede hacer ARM
     - Soldador solo puede hacer SOLD
     - Metrologia solo puede hacer METROLOGIA
     - Trabajadores con múltiples roles pueden hacer múltiples operaciones
   - **Estado:** Lógica de validación pendiente en ValidationService

4. **Sheet Structure Ampliada** ✅ **MIGRADO**
   - v1.0: 2 hojas (Operaciones, Trabajadores) - Sheet TESTING
   - v2.0: 4 hojas (+Metadata, +Roles) - Sheet PRODUCCIÓN ✅
   - **Impacto:**
     - Sheet ID cambió: `11v8fD...` → `17iOaq...`
     - Hoja "Metadata" creada (10 columnas) ✅
     - Hoja "Roles" pendiente creación (3 columnas) ⏳

5. **Modelo Spool con METROLOGÍA** ⏳ PENDIENTE
   - v1.0: 2 operaciones (ARM, SOLD)
   - v2.0: 3 operaciones (+METROLOGÍA)
   - **Impacto:** Columnas nuevas (AO=Fecha_Metrología) ya existen en Sheet PRODUCCIÓN

### Estrategia de Migración

**Opción Seleccionada: Big Bang (2 horas downtime)**
- Ventana mantenimiento planificada
- Migrar todo de una vez
- Rollback < 5 min disponible
- Menos complejidad vs migración gradual

---

## 6. Métricas de Éxito v2.0

### Funcionales (Must-Have 14 Dic)

- [x] Sheet PRODUCCIÓN funcionando sin errores ✅
- [x] 100% acciones registradas en hoja Metadata ✅
- [ ] 100% trabajadores con roles operativos validados
- [ ] Endpoint CANCELAR operaciones EN_PROGRESO funcional
- [ ] Multiselect batch hasta 50 spools funcional
- [ ] Búsqueda TAG_SPOOL en P4 funcional
- [ ] 80%+ reducción tiempo batch (25 → 7 seg/spool)
- [ ] 0 regresiones funcionalidad v1.0

### Funcionales (Nice-to-Have)

- [ ] METROLOGÍA operativa (solo si alcanza tiempo antes 14 dic)

### Técnicas (Mínimo Aceptable)

**Calidad:**
- [ ] 150+ tests backend passing (100%)
- [ ] 20 tests E2E frontend passing (100%)
- [ ] Coverage backend > 80%
- [ ] 0 errores build producción

**Performance:**
- [ ] Batch 10 spools: < 3 seg
- [ ] API response p95: < 2 seg

**Estabilidad:**
- [ ] 0 errores críticos logs post-deploy (24h)
- [ ] < 5% tasa error requests

---

## 7. Riesgos y Mitigación

### Riesgos Técnicos (Top 3)

| Riesgo | P | I | Mitigación |
|--------|---|---|------------|
| **Sheet PRODUCCIÓN corrupción** | B | C | Backup pre-migración, testing copia, rollback < 5 min |
| **Performance degradación batch 50** | M | A | Performance tests, limit 50, batch update optimizado |
| **Metadata > 5M celdas** | M | A | Monitoreo, archiving mensual, alertas 4M |

P=Probabilidad (B=Baja/M=Media) | I=Impacto (A=Alto/C=Crítico)

### Riesgos de Negocio (Top 3)

| Riesgo | P | I | Mitigación |
|--------|---|---|------------|
| **Resistencia login obligatorio** | M | A | Capacitación, UI simple, soporte día 1 |
| **Confusión 3 operaciones** | M | M | Íconos claros (📏), colores, tooltips |
| **Downtime migración afecta producción** | B | A | Horario bajo uso, comunicación, rollback |

---

## 8. Documentación Técnica Detallada

### Backend v2.0

**Ver `proyecto-v2-backend.md` para:**
- Estructura completa proyecto (35 archivos)
- Modelos Pydantic detallados (User, MetadataLog, Batch)
- Implementación AuthService, MetadataService, ActionService
- Middleware auth + metadata logging
- Repositories (User, Metadata, Sheets batch)
- 95 tests nuevos con ejemplos código
- Variables de entorno completas
- Deployment Railway v2.0
- Performance y optimización
- Troubleshooting

### Frontend v2.0

**Ver `proyecto-v2-frontend.md` para:**
- Estructura completa proyecto (43 archivos)
- Componentes nuevos (Checkbox, Badge, Header)
- Páginas admin panel (CRUD, reportes, metadata)
- AuthContext implementación completa
- Multiselect UI patterns detallados
- API client con fetchWithAuth
- Protected routes middleware
- 8 tests E2E nuevos con código
- Deployment Vercel v2.0

---

## 9. Recursos y Referencias

### Documentación

**Proyecto:**
- `proyecto-v2.md` - Este archivo (visión general)
- `proyecto-v2-backend.md` - Documentación técnica backend v2.0
- `proyecto-v2-frontend.md` - Documentación técnica frontend v2.0
- `proyecto.md` - MVP v1.0 (base completada)
- `CLAUDE.md` - Guía desarrollo

**Google:**
- `docs/GOOGLE-RESOURCES.md` - Configuración recursos Google

### Google Sheets

**TESTING (Desarrollo):**
- ID: `11v8fD5Shn0RSzDceZRvXhE9z4RIOBmPA9lpH5_zF-wM`
- URL: https://docs.google.com/spreadsheets/d/11v8fD5Shn0RSzDceZRvXhE9z4RIOBmPA9lpH5_zF-wM

**PRODUCCIÓN (Target):**
- ID: `17iOaq2sv4mSOuJY4B8dGQIsWTTUKPspCtb7gk6u-MaQ`
- URL: https://docs.google.com/spreadsheets/d/17iOaq2sv4mSOuJY4B8dGQIsWTTUKPspCtb7gk6u-MaQ

### URLs Deployment v2.0

**Target:**
- Backend: https://zeues-backend-v2-production.up.railway.app
- Frontend: https://zeues-v2.vercel.app

**v1.0 (Mantener durante desarrollo):**
- Backend: https://zeues-backend-mvp-production.up.railway.app
- Frontend: https://zeues-frontend.vercel.app

---

## 10. Glosario v2.0

**Términos Nuevos v2.0:**

- **Rol Operativo**: Tipo de trabajo que puede realizar un trabajador (Armador, Soldador, Metrologia, etc.)
- **Multi-rol**: Capacidad de un trabajador de tener múltiples roles simultáneos
- **METROLOGÍA**: Tercera operación manufactura, inspección calidad post-soldadura
- **Metrólogo**: Trabajador con rol "Metrologia" que puede hacer inspecciones
- **Metadata**: Hoja auditoría con registro completo (Event Sourcing append-only)
- **Event Sourcing**: Patrón arquitectónico donde eventos inmutables determinan el estado
- **Batch**: Operación sobre múltiples spools simultáneamente
- **Multiselect**: UI para seleccionar múltiples spools con checkboxes
- **Ownership Validation**: Restricción que solo permite completar a quien inició (v1.0: ARM/SOLD, v2.0: +METROLOGÍA)
- **Hoja "Roles"**: Sheet con asignación roles a trabajadores (Id, Rol, Activo)
- **Hoja "Metadata"**: Sheet con log completo acciones inmutables (10 columnas)

**Términos v1.0 (Vigentes):**

- **Spool**: Unidad manufactura cañería
- **TAG_SPOOL**: ID único spool (columna G)
- **ARM**: Armado (columna V)
- **SOLD**: Soldado (columna W)
- **INICIAR**: Primera interacción (estado → 0.1, asigna trabajador)
- **COMPLETAR**: Segunda interacción (estado → 1.0, registra fecha)
- **0**: Pendiente/no iniciado
- **0.1**: En progreso/iniciado
- **1.0**: Completado

**Secuencia Completa v2.0:**
```
BA (Materiales) → ARM (Armado) → SOLD (Soldado) → METROLOGÍA (Inspección)
                  BB              BD              BF
                  BC              BE              BG
```

---

## 11. Estado Actual del Proyecto

**Última Actualización:** 16 Dic 2025 - 19:00
**Branch Desarrollo:** `v2.0-dev`
**Estado:** 🔄 **REORGANIZACIÓN UX COMPLETADA** - Nueva arquitectura flujo (Operación → Trabajador)
**Deadline:** 14 Dic 2025 (EXTENDIDO - ajustes UX en progreso)

### Progreso v2.0

**Migración Sheet PRODUCCIÓN:** ✅ **COMPLETADO** (10 Dic 2025)
- [x] Sheet ID actualizado: `17iOaq2sv4mSOuJY4B8dGQIsWTTUKPspCtb7gk6u-MaQ`
- [x] Hoja "Metadata" creada con headers (10 columnas A-J)
- [x] Hoja "Trabajadores" verificada (9 trabajadores con Id + Rol)
- [x] Hoja "Operaciones" confirmada (2,493 filas, 65 columnas) - READ-ONLY
- [x] Arquitectura Event Sourcing implementada
- [x] Config actualizado (`.env.local`, `backend/config.py`)
- [ ] Deploy Railway pendiente (próximo paso)

**Validación Tests DÍA 1:** ✅ **COMPLETADO** (11 Dic 2025 - 4h sesión)
- **Estado Inicial:** 107 passed / 48 failed / 42 errors / 6 skipped (53% success)
- **Estado Final:** 76/79 v2.0 tests passing (96% success)
- **Fixes Aplicados:** 9 correcciones críticas
  1. ✅ Typos método `get_events_by_spool` (15 occurrences)
  2. ✅ Worker.rol → Optional (v2.0 multi-role architecture)
  3. ✅ ActionData.fila_actualizada constraint (ge=0 para Event Sourcing)
  4. ✅ WorkerNoEncontradoError parámetro `worker_nombre`
  5. ✅ ActionService variable scope `worker_nombre`
  6. ✅ ValidationService keyword arguments (3 métodos)
  7. ✅ RolNoAutorizadoError instance attributes
  8. ✅ ValidationService CANCELAR exception logic (COMPLETADO vs PENDIENTE)
  9. 🟡 test_action_service.py fixtures v1.0 (parcial - 21 tests pendientes)
- **Archivos Modificados:** 7 files (models, exceptions, services, tests)
- **Resultado:** DÍA 1 100% implementado y 96% validado
- **Pendiente:** 3 tests v2.0 menores (mock config) + 21 tests v1.0 (1-2h)

**Validación Tests DÍA 2 Batch:** ✅ **COMPLETADO** (12 Dic 2025)
- **Tests Batch:** 14/14 passing (100% success)
- **Archivo:** tests/unit/test_action_service_batch.py (+620 líneas)
- **Cobertura Tests Batch:**
  1. ✅ test_iniciar_accion_batch_success - Caso exitoso (todos los spools procesados)
  2. ✅ test_iniciar_accion_batch_partial_failure - Errores parciales (algunos spools fallan)
  3. ✅ test_iniciar_accion_batch_all_failures - Todos los spools fallan
  4. ✅ test_iniciar_accion_batch_validation_50_max - Validación límite 50 spools
  5. ✅ test_iniciar_accion_batch_empty_list - Lista vacía de spools
  6. ✅ test_iniciar_accion_batch_exceed_50_limit - Exceder límite 50 spools
  7. ✅ test_completar_accion_batch_success - Caso exitoso COMPLETAR
  8. ✅ test_completar_accion_batch_partial_failure - Errores parciales COMPLETAR
  9. ✅ test_completar_accion_batch_ownership_validation - Ownership validation individual
  10. ✅ test_completar_accion_batch_all_failures - Todos los spools fallan COMPLETAR
  11. ✅ test_iniciar_accion_batch_performance_10_spools - Performance < 3 seg (objetivo cumplido)
  12. ✅ test_completar_accion_batch_performance_10_spools - Performance COMPLETAR < 3 seg
  13. ✅ test_iniciar_accion_batch_sold_operation - Operación SOLD batch
  14. ✅ test_completar_accion_batch_sold_operation - COMPLETAR SOLD batch
- **Resultado:** DÍA 2 Backend Batch 100% implementado y 100% validado
- **Métricas:** ~1,418 líneas código nuevo (modelos + service + endpoints + tests)

**Backend Must-Have (para 14 Dic):**
- [x] Metadata Event Sourcing ✅ (implementado 10 Dic)
- [x] Worker con Id (migrado a int) ✅
- [x] MetadataRepository con ownership validation ✅
- [x] DÍA 1: RoleRepository + RoleService + validación roles ✅ (completado 11 Dic)
- [x] DÍA 1: Endpoint CANCELAR acción EN_PROGRESO ✅ (completado 11 Dic)
- [x] DÍA 1: ActionService migrado a worker_id (int) ✅ (completado 11 Dic)
- [x] DÍA 1: WorkerService con find_worker_by_id() ✅ (completado 11 Dic)
- [x] DÍA 1: Tests: 79 nuevos (76/79 passing = 96%) ✅ (validado 11 Dic - 4h test fix)
- [x] DÍA 2: ActionService batch (multiselect hasta 50) ✅ (completado 12 Dic - +328 líneas)
- [x] DÍA 2: Endpoints batch (iniciar/completar) ✅ (completado 12 Dic - +285 líneas)
- [x] DÍA 2: Modelos Pydantic batch ✅ (3 nuevos: BatchActionRequest/Result/Response - +185 líneas)
- [x] DÍA 2: Tests batch: 14 nuevos (14/14 passing = 100%) ✅ (completado 12 Dic - +620 líneas tests)
- [x] DÍA 2: Manejo errores parciales (continúa si algunos spools fallan) ✅
- [x] DÍA 2: Ownership validation individual en completar batch ✅
- [x] DÍA 2: Performance < 3 seg para 10 spools ✅ (objetivo cumplido)
- **Total:** 80% base completado (DÍA 1 + DÍA 2 Backend done), 20% pendiente (Frontend + Deploy)

**Frontend Must-Have (para 14 Dic):**
- [x] DÍA 2: P2 filtrado por roles (GET /workers/{id}/roles) ✅ **COMPLETADO 12 Dic**
- [x] DÍA 2: P3 botón CANCELAR + breaking change worker_id ✅ **COMPLETADO 13 Dic**
- [ ] DÍA 2: P4 multiselect UI (checkboxes + select all)
- [ ] DÍA 2: P4 búsqueda TAG_SPOOL
- [ ] DÍA 2: P5/P6 batch (confirmación + resultados)
- **Total:** 50% completado (2/4 features must-have), 50% pendiente

**Deploy (DÍA 3):**
- [x] Sheet PRODUCCIÓN migrado ✅
- [ ] Tests E2E +3 nuevos
- [ ] Deploy Railway v2.0
- [ ] Deploy Vercel v2.0
- [ ] Smoke tests producción
- **Total:** 20% base (sheet), 80% pendiente

### Próximos Pasos INMEDIATOS (Orden de Prioridad)

**DÍA 1 - Backend Core (11-12 Dic):** ✅ **COMPLETADO**
1. ✅ RoleRepository (lectura hoja Roles)
2. ✅ RoleService (validación rol por operación)
3. ✅ ValidationService integración roles
4. ✅ Endpoint GET /api/workers/{id}/roles
5. ✅ Endpoint POST /api/cancelar-accion
6. ✅ ActionService migrar a worker_id (int)
7. ✅ Tests: 79 nuevos (76/79 passing = 96%)

**DÍA 2 - Batch + Frontend (12-13 Dic):** ✅ **Backend COMPLETADO** | 🔄 **Frontend 50% (2/4)**
1. ✅ **Backend:** ActionService batch (iniciarBatch, completarBatch) - +328 líneas
2. ✅ **Backend:** Endpoints batch POST - +285 líneas
3. ✅ **Backend:** Modelos batch - +185 líneas
4. ✅ **Backend:** Tests 14/14 passing - +620 líneas tests
5. ✅ **Backend:** Performance < 3 seg para 10 spools ✅
6. ✅ **Frontend:** P2 filtrado roles - COMPLETADO (12 Dic 21:00)
7. ✅ **Frontend:** P3 CANCELAR + worker_id breaking change - COMPLETADO (13 Dic 01:00)
8. 🔴 **Frontend:** P4 multiselect + búsqueda
9. 🔴 **Frontend:** P5/P6 batch
10. 🟡 Tests: 3+ E2E frontend pendientes

**DÍA 3 - Deploy (13-14 Dic):**
1. 🔴 Tests finales (coverage >80%)
2. 🔴 Deploy Railway v2.0
3. 🔴 Deploy Vercel v2.0
4. 🔴 Smoke tests producción
5. 🟡 Ajustes críticos si necesario

**Documentación de Referencia:**
- Ver `proyecto-v2-backend.md` sección 4 para MetadataService
- Ver `proyecto-v2-backend.md` sección 3 para Sistema de Roles Operativos
- Ver `proyecto-v2-backend.md` sección 7.2 para tests

### 🔧 Cambios Técnicos Recientes

**REORGANIZACIÓN UX - Operación Primero, Trabajador Después (16 Dic 2025) ✅**

**Motivación:** Mejorar UX permitiendo que operaciones filtren trabajadores por rol (en vez de trabajadores filtrar operaciones).

**Cambio Arquitectónico:**
```
v1.0/v2.0 (anterior):
P1: Seleccionar TRABAJADOR → P2: Seleccionar OPERACIÓN (filtrada por roles)

v2.0 (nuevo - 16 Dic):
P1: Seleccionar OPERACIÓN → P2: Seleccionar TRABAJADOR (filtrado por rol)
```

**Archivos Modificados (4 total):**
1. **app/page.tsx (P1)** - REEMPLAZADO:
   - Antes: Grid trabajadores (4 cards)
   - Después: 3 botones operación verticales (🛠️ ARM, 🔥 SOLD, 📐 METROLOGÍA)
   - Fetch: getWorkers() → guarda en context.allWorkers
   - Navegación: onClick → setSelectedOperation → /operacion

2. **app/operacion/page.tsx (P2)** - REEMPLAZADO:
   - Antes: 3 botones operación + filtrado por roles
   - Después: Grid trabajadores filtrados por rol de operación seleccionada
   - Título dinámico: "🔧 ¿Quién va a armar?" | "🔥 ¿Quién va a soldar?" | "📐 ¿Quién va a medir?"
   - Filtrado: OPERATION_TO_ROLES mapping (ARM→Armador+Ayudante, SOLD→Soldador+Ayudante, METROLOGIA→Metrologia)
   - Multi-rol: Trabajador con Armador+Soldador aparece en ambas operaciones
   - Validación: Si filteredWorkers.length === 0 → ErrorMessage + botón Volver

3. **lib/context.tsx** - Actualizado:
   - +allWorkers: Worker[] (cache de todos los trabajadores)
   - selectedOperation: 'ARM' | 'SOLD' | 'METROLOGIA' (ya incluía METROLOGIA)

4. **lib/types.ts** - Actualizado:
   - ActionPayload.operacion: +METROLOGIA (ya estaba desde sesión anterior)

**Lógica de Filtrado P2:**
```typescript
const OPERATION_TO_ROLES: Record<string, string[]> = {
  'ARM': ['Armador', 'Ayudante'],
  'SOLD': ['Soldador', 'Ayudante'],
  'METROLOGIA': ['Metrologia'],
};

const eligible = state.allWorkers.filter(worker => {
  if (!worker.activo) return false;
  if (!worker.roles || worker.roles.length === 0) return false;
  return worker.roles.some(role => requiredRoles.includes(role));
});
```

**Beneficios:**
- ✅ UX más clara: Usuario decide QUÉ hacer antes de QUIÉN lo hace
- ✅ Código más simple: Filtrado de trabajadores en P2 (eliminado filtrado de operaciones)
- ✅ Arquitectura limpia: OPERATION_TO_ROLES mapping centralizado
- ✅ Mobile-first: 3 botones grandes verticales en P1
- ✅ Multi-rol support: Ayudante aparece en ARM y SOLD

**Breaking Changes:**
- ❌ Ninguno a nivel de API (solo cambios UI internos)

**Validación:**
- ✅ TypeScript: npx tsc --noEmit - 0 errores
- ✅ ESLint: npm run lint - 0 errores, 0 warnings
- ✅ Arquitectura: Código limpio, sin `any`, hooks correctos

**Impacto Frontend:**
- P1: Cambio completo (trabajadores → operaciones)
- P2: Cambio completo (operaciones → trabajadores)
- P3-P6: Sin cambios
- Context: +allWorkers (nuevo campo)
- Total líneas modificadas: ~200 líneas (2 páginas + context)

**Estado:** ✅ Implementado y validado (16 Dic 19:00)

---

**P3 CANCELAR + Breaking Change ActionPayload (worker_id) - COMPLETADO ✅ (13 Dic)**

**Breaking Change CRÍTICO - ActionPayload:**
```typescript
// v1.0 (DEPRECATED)
interface ActionPayload {
  worker_nombre: string;
  operacion: 'ARM' | 'SOLD';
  tag_spool: string;
}

// v2.0 (ACTUAL) ⚠️ BREAKING
interface ActionPayload {
  worker_id: number;        // 🔄 CAMBIO: worker_nombre → worker_id
  operacion: 'ARM' | 'SOLD';
  tag_spool: string;
  timestamp?: string;       // Para COMPLETAR
}
```

**Archivos Modificados (9 total):**
1. `lib/types.ts` - ActionPayload: worker_nombre → worker_id
2. `lib/context.tsx` - selectedTipo: +cancelar type
3. `lib/api.ts` - +2 funciones (getSpoolsParaCancelar, cancelarAccion) + JSDoc actualizado
4. `components/Button.tsx` - +variant cancelar (bg-yellow-600)
5. `app/tipo-interaccion/page.tsx` - P3: +botón CANCELAR amarillo
6. `app/seleccionar-spool/page.tsx` - P4: +lógica getSpoolsParaCancelar
7. `app/confirmar/page.tsx` - P5: payload migrado a worker_id + lógica 3 tipos
8. `app/exito/page.tsx` - P6: mensajería dinámica CANCELAR (warning amarillo)

**Nuevas Funciones API (9 total, +2 nuevas):**
1. getWorkers()
2. getSpoolsParaIniciar()
3. getSpoolsParaCompletar()
4. iniciarAccion()
5. completarAccion()
6. checkHealth()
7. getWorkerRoles() ✅ P2
8. **getSpoolsParaCancelar(operacion, workerId)** ✅ P3 NUEVO
9. **cancelarAccion(payload)** ✅ P3 NUEVO

**Implementación Completa:**
- P3: Tercer botón "⚠️ CANCELAR ACCIÓN" (amarillo, variant cancelar)
- P4: Condicional cancelar → fetch spools EN_PROGRESO (estado 0.1) del worker
- P5: Lógica 3 tipos (iniciar/completar/cancelar) + payload worker_id
- P6: Icon warning amarillo + mensaje "Spool vuelve a PENDIENTE" + color dinámico

**Flujo CANCELAR Completo:**
```
P1 (Worker) → P2 (ARM/SOLD según roles) → P3 (CANCELAR)
→ P4 (Spools 0.1 del worker) → P5 (Confirmar CANCELAR)
→ P6 (Warning amarillo + "PENDIENTE") → Auto-redirect P1 (5 seg)
```

**Validación:**
- ✅ npm run lint - 0 errores
- ✅ npx tsc --noEmit - 0 errores

**Métricas:**
- Archivos modificados: 9 (total acumulado 18 en DÍA 2)
- Breaking changes: 1 CRÍTICO (ActionPayload worker_id)
- Nuevas funciones API: +2 (total 9)
- Tests E2E pendientes: +1 CANCELAR (total 3 nuevos)

---

**P2 Filtrado por Roles - COMPLETADO ✅ (12 Dic)**

**Breaking Change - Worker Interface:**
```typescript
// v1.0 → v2.0
interface Worker {
  id: number;              // 🆕 AÑADIDO
  nombre_completo: string; // 🆕 AÑADIDO (computed)
  // ... resto sin cambios
}
```

**Archivos Modificados (9 total):**
- lib/types.ts, lib/context.tsx, lib/api.ts
- P1-P6 (app/page.tsx hasta app/exito/page.tsx)

**Nueva función API:**
- getWorkerRoles(workerId: number): Promise<string[]>

---

**FIN - proyecto-v2.md - ZEUES v2.0 - Versión 2.0 - 13 Dic 2025 01:00**

**Resumen ACTUALIZADO (Clarificación Arquitectura v2.0):**

**CAMBIOS CRÍTICOS vs versión anterior:**
1. ❌ **ELIMINADA autenticación JWT/login** - Frontend igual que v1.0 (sin login)
2. ✅ **Operaciones READ-ONLY** - NUNCA se modifica desde backend (solo lectura)
3. ✅ **Sistema estados 0/0.1/1.0 ELIMINADO** - v2.0 usa columnas de trabajadores (AG/AI/AK)
4. ✅ **Metadata para auditoría** - Event Sourcing append-only (única sheet donde backend escribe)
5. ✅ **Deadline real: 3 días** - 14 Dic 2025 (no 16 días)
6. ✅ **METROLOGÍA nice-to-have** - Solo si alcanza tiempo

**Must-Have (para 14 Dic):**
- Roles operativos múltiples validados (backend + frontend)
- Endpoint CANCELAR operaciones EN_PROGRESO
- Multiselect batch hasta 50 spools
- Búsqueda TAG_SPOOL en P4
- Migration worker_nombre → worker_id (int)
- 150+ tests backend, 20 tests E2E frontend

**Progreso Real:**
- ✅ 85% base (Sheet + Metadata + Worker Id + Roles + CANCELAR + Batch Backend + Tests + P2+P3 Frontend)
- ⏳ 15% pendiente (P4-P6 Frontend multiselect/búsqueda/batch + Deploy)

**Próximo paso crítico:**
- DÍA 2 Frontend (13 Dic): P4 multiselect + búsqueda + P5/P6 batch UI

**Reglas de Validación v2.0 (CRÍTICAS - por NOMBRE de columna):**

**INICIAR ARM:**
1. Columna **"Fecha_Materiales"** != vacío → Materiales llegaron ✅
2. Columna **"Armador"** == vacío → Nadie asignado ✅
3. Worker tiene rol ARMADOR ✅

**INICIAR SOLD:**
1. Columna **"Armador"** != vacío → ARM ya asignado/completado ✅
2. Columna **"Soldador"** == vacío → Nadie asignado ✅
3. Worker tiene rol SOLDADOR ✅

**COMPLETAR ARM:**
1. Columna **"Armador"** != vacío → ARM fue iniciado ✅
2. Worker_id == owner inicial (ownership validation via Metadata) ✅

**COMPLETAR SOLD:**
1. Columna **"Soldador"** != vacío → SOLD fue iniciado ✅
2. Worker_id == owner inicial (ownership validation via Metadata) ✅

**⚠️ IMPORTANTE:** Código debe buscar columnas por nombre de header, NO por índice (AG/AI/AK son volátiles)

**Para Desarrollo:**
- Ver `proyecto-v2-backend.md` (arquitectura detallada backend)
- Ver `proyecto-v2-frontend.md` (sin autenticación, solo multiselect/roles)
