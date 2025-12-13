# ZEUES v2.0 - Backend Technical Documentation

**Última actualización:** 12 Dic 2025 16:30 | **Versión:** 2.1 | **Branch:** `v2.0-dev`

---

## 📋 Quick Reference

| Aspecto | Estado | Detalles |
|---------|--------|----------|
| **Progreso Backend** | 85% | 3 días completados (DÍA 4 + DÍA 1 + DÍA 2 completo) |
| **Tests** | 232/232 passing | v1.0: 113 → +119 nuevos (100%) |
| **Archivos** | 33 archivos | +11 nuevos vs v1.0 |
| **Código nuevo** | ~3,657 líneas | DÍA 4 (800) + DÍA 1 (1,300) + DÍA 2 (1,557) |
| **Sheet activo** | PRODUCCIÓN | ID: `17iOaq2sv4mSOuJY4B8dGQIsWTTUKPspCtb7gk6u-MaQ` |
| **Deadline** | 14 Dic 2025 | 2 días restantes |

### Estado Implementación

```
✅ COMPLETADO (85% backend):
  ✅ DÍA 4: Metadata Event Sourcing (54 tests)
  ✅ DÍA 1: Sistema Roles + CANCELAR (47 tests)
  ✅ DÍA 2: Operaciones Batch Backend (18 tests) - 100% COMPLETO

🔴 PENDIENTE (15%):
  🔴 DÍA 2: Frontend (multiselect, roles UI, cancelar)
  🔴 DÍA 3: Deploy + Tests E2E
  🟡 METROLOGÍA: Nice-to-have
```

### Breaking Changes v2.0

| Change | v1.0 | v2.0 |
|--------|------|------|
| **API Request** | `worker_nombre: str` | `worker_id: int` ✅ |
| **Sheet Trabajadores** | 5 columnas (con Rol) | 4 columnas (sin Rol) ✅ |
| **Sheet Roles** | No existe | Multi-rol (3 columnas) ✅ |
| **Arquitectura Data** | Operaciones R/W | Operaciones R/W + Metadata append-only ✅ |

---

## 🔧 Guía de Mantenimiento LLM-First

**Propósito:** Este documento es una **referencia técnica ejecutiva optimizada para LLMs**, NO un manual de implementación extenso.

### Principios de Optimización (SIEMPRE mantener)

1. **Token-efficiency es prioritario:**
   - Preferir tablas compactas sobre bloques de código extensos
   - Usar signatures en vez de implementaciones completas
   - Eliminar código repetitivo o boilerplate
   - Target: < 1,000 líneas, < 10,000 tokens

2. **Estructura Quick Reference obligatoria:**
   - Tabla de estado al inicio (progreso, tests, archivos, deadline)
   - Estado de implementación visual (✅/🔴/🟡)
   - Breaking changes destacados
   - **Actualizar SIEMPRE antes de cualquier otra sección**

3. **Formato preferido por sección:**
   - **Modelos/Schemas:** Solo JSON de request/response + tabla de campos
   - **Servicios:** Tabla de métodos con signatures (NOT implementación completa)
   - **Tests:** Lista compacta con nombres + archivos
   - **Endpoints:** Tabla HTTP + JSON schemas (NO código Python)
   - **Arquitectura:** Diagramas ASCII + tablas comparativas

4. **Qué ELIMINAR en actualizaciones:**
   - ❌ Bloques de código Python > 20 líneas
   - ❌ Docstrings extensos (mantener solo 1 línea de propósito)
   - ❌ Ejemplos de código "ANTES/DESPUÉS" verbosos (usar tabla comparativa)
   - ❌ Repetición de specs entre secciones
   - ❌ Código boilerplate (imports, decorators obvios, etc.)

5. **Qué MANTENER siempre:**
   - ✅ JSON request/response schemas completos
   - ✅ Tablas de estado/progreso/métricas
   - ✅ Breaking changes con ejemplos compactos
   - ✅ Method signatures con tipos y excepciones
   - ✅ Test counts y archivos
   - ✅ Números exactos (líneas código, tests passing, % progreso)

### Reglas de Actualización

**Cuando te diga "actualiza el archivo":**

1. **Primero actualizar Quick Reference:**
   - Progreso backend (%)
   - Tests (X/Y passing)
   - Archivos nuevos
   - Código nuevo (líneas)
   - Deadline restante

2. **Luego actualizar secciones afectadas:**
   - Cambiar estado PENDIENTE → ✅ COMPLETADO + fecha
   - Añadir métricas reales (tests, líneas código)
   - Actualizar tablas comparativas
   - NO añadir código completo, usar signatures

3. **Formato para nueva feature completada:**
```markdown
### X.Y. [Feature Name] (✅ COMPLETADO DD Dic 2025)

**Implementación:** XXX líneas | YY tests passing

**Archivos clave:**
- `path/to/file.py` - ZZZ líneas

**Métodos/Endpoints principales:**
- `method_name(params)` → ReturnType | raises ExceptionType

**Tests:**
- test_file.py (XX tests)
  - test_success
  - test_error_case
```

4. **Mantener límites:**
   - Si documento > 1,000 líneas: compactar secciones antiguas
   - Convertir código viejo a tablas
   - Mover detalles históricos a sección "Changelog resumido"

### Ejemplo de Transformación

**❌ INCORRECTO (verbose):**
```python
# backend/services/role_service.py
class RoleService:
    def validar_worker_tiene_rol_para_operacion(
        self,
        worker_id: int,
        operacion: str
    ) -> None:
        """
        Valida que el worker tenga el rol apropiado para la operación.

        Args:
            worker_id: ID del trabajador
            operacion: ARM, SOLD, o METROLOGIA

        Raises:
            WorkerNoEncontradoError: Si worker_id no existe
            RolNoAutorizadoError: Si worker no tiene rol requerido
        """
        roles = self.obtener_roles_worker(worker_id)
        # ... 30 líneas más de implementación
```
(~50 líneas de código)

**✅ CORRECTO (compacto):**
```markdown
**RoleService** (211 líneas | 19 tests)

**Métodos clave:**
- `validar_worker_tiene_rol_para_operacion(worker_id, operacion)` → None | raises RolNoAutorizadoError, WorkerNoEncontradoError
- `obtener_roles_worker(worker_id)` → List[RolTrabajador]

**Reglas de validación:**
| Operación | Roles autorizados |
|-----------|-------------------|
| ARM | ARMADOR, AYUDANTE |
| SOLD | SOLDADOR, AYUDANTE |
| METROLOGIA | METROLOGIA |
```
(~10 líneas)

### Checklist Pre-commit

Antes de marcar actualización como completa:
- [ ] Quick Reference actualizado con números reales
- [ ] Estado implementación visual correcto (✅/🔴/🟡)
- [ ] Breaking changes documentados si aplica
- [ ] Tests counts actualizados
- [ ] Documento < 1,000 líneas
- [ ] NO código Python > 20 líneas en ninguna sección
- [ ] Fecha y versión actualizadas en header

---

## 1. Stack Tecnológico

**Backend:**
- Python 3.11+ + FastAPI 0.100+
- gspread 5.10+ (Google Sheets API)
- Pydantic 2.0+ + pytest + uvicorn
- **Sin cambios de dependencias vs v1.0**

**Arquitectura:**
- Clean Architecture: Routers → Services → Repositories → Google Sheets
- Service Layer Pattern + Repository Pattern
- Custom Exceptions: `ZEUSException` → HTTP status codes
- Dependency Injection: FastAPI `Depends()`

---

## 2. Estructura del Proyecto

### Archivos Clave v2.0

**Nuevos modelos:**
- `backend/models/role.py` (185 líneas) - RolTrabajador enum, WorkerRole, WorkerWithRoles
- `backend/models/metadata.py` (195 líneas) - MetadataEvent, EventoTipo, Accion

**Nuevos repositories:**
- `backend/repositories/role_repository.py` (224 líneas) - CRUD hoja Roles multi-rol
- `backend/repositories/metadata_repository.py` (180 líneas) - Event Sourcing append-only

**Nuevos services:**
- `backend/services/role_service.py` (211 líneas) - Validación permisos por rol

**Modificados:**
- `backend/services/validation_service.py` (+170 líneas) - Integración roles + CANCELAR
- `backend/services/action_service.py` (+468 líneas) - Batch methods + worker_id migration
- `backend/services/worker_service.py` (+37 líneas) - find_worker_by_id()
- `backend/routers/actions.py` (+405 líneas) - Endpoints batch + cancelar

**Nuevos tests:**
- `tests/unit/test_role_repository.py` (20 tests)
- `tests/unit/test_role_service.py` (19 tests)
- `tests/unit/test_worker_service_v2.py` (8 tests)
- `tests/unit/test_action_service_batch.py` (14 tests)
- `tests/unit/test_validation_service_cancelar.py` (parte de 47)
- `tests/unit/test_action_service_v2.py` (parte de 47)

**Total:** 33 archivos (+11) | 228 tests (+115)

---

## 3. Sistema de Roles Operativos Múltiples ✅ COMPLETADO

### 3.1. Modelo de Datos

**RolTrabajador Enum:**
```python
ARMADOR, SOLDADOR, AYUDANTE, METROLOGIA, REVESTIMIENTO, PINTURA, DESPACHO
```

**Mapeo Operación → Rol:**
| Operación | Rol Requerido |
|-----------|---------------|
| ARM | ARMADOR |
| SOLD | SOLDADOR |
| METROLOGIA | METROLOGIA |

**WorkerRole:** `(id: int, rol: RolTrabajador, activo: bool)` - Inmutable

**WorkerWithRoles:** Combina Worker + lista roles activos
- `tiene_rol(rol)` → bool
- `puede_hacer_operacion(operacion)` → bool

### 3.2. Google Sheets - Hoja "Roles"

| Columna | Tipo | Descripción | Ejemplo |
|---------|------|-------------|---------|
| A: Id | int | FK Trabajadores (permite duplicados) | 93 |
| B: Rol | str | Uno de 7 valores RolTrabajador | Armador |
| C: Activo | bool | TRUE/FALSE | TRUE |

**Multi-rol:** Un worker puede tener N filas (ej: worker 93 → 2 roles: Armador + Soldador)

**Datos ejemplo:**
```
93 | Armador   | TRUE
93 | Soldador  | TRUE
95 | Soldador  | TRUE
95 | Metrologia| TRUE
```

### 3.3. RoleRepository ✅

**Métodos implementados:**
- `get_roles_by_worker_id(worker_id)` → List[WorkerRole]
- `worker_has_role(worker_id, rol)` → bool
- `get_all_roles()` → List[WorkerRole]

**Implementación:** 224 líneas | 20 tests passing

### 3.4. RoleService ✅

**Métodos clave:**
- `validar_worker_tiene_rol_para_operacion(worker_id, operacion)` → None | raises RolNoAutorizadoError
- `obtener_roles_worker(worker_id)` → List[RolTrabajador]
- `obtener_worker_con_roles(worker)` → WorkerWithRoles

**Implementación:** 211 líneas | 19 tests passing

### 3.5. Integración ValidationService ✅

**Cambios:**
- Constructor recibe `role_service: RoleService`
- `validar_puede_iniciar()` ahora valida rol antes de permitir operación
- `validar_puede_completar()` valida rol + ownership
- Nueva excepción: `RolNoAutorizadoError` → 403 FORBIDDEN

**Código modificado:** +170 líneas

### 3.6. Tests ✅

**47 tests passing (100%):**
- RoleRepository: 20 tests (multi-rol, activos, validaciones)
- RoleService: 19 tests (permisos, obtener roles, WorkerWithRoles)
- WorkerService: 8 tests (find_worker_by_id, integración)

---

## 3.7. Endpoint CANCELAR Acción ✅ COMPLETADO

**Endpoint:** `POST /api/cancelar-accion`

**Request:**
```json
{
  "worker_id": 93,
  "operacion": "ARM",
  "tag_spool": "MK-1335-CW-25238-011"
}
```

**Response 200:**
```json
{
  "message": "Acción ARM cancelada exitosamente",
  "data": {
    "tag_spool": "...",
    "operacion": "ARM",
    "estado_anterior": 0.1,
    "estado_nuevo": 0,
    "worker_id": 93,
    "fecha_cancelacion": "2025-12-11T14:30:00Z"
  }
}
```

**Validaciones:**
1. Spool existe
2. Operación válida
3. Estado = 0.1 (EN_PROGRESO)
4. Worker es quien inició (ownership)

**Workflow:**
1. Validar puede cancelar
2. UPDATE estado: 0.1 → 0
3. Limpiar worker asignado
4. Registrar evento CANCELAR en Metadata
5. Invalidar cache

**Código:** +120 líneas router | Tests incluidos en 47 tests DÍA 1

**Metadata Events:** `CANCELAR_ARM`, `CANCELAR_SOLD`, `CANCELAR_METROLOGIA`

---

## 3.8. Migration worker_nombre → worker_id ✅ COMPLETADO

**Breaking Change:** API ahora usa `worker_id: int` en vez de `worker_nombre: str`

**Motivación:**
- Evitar ambigüedad (nombres similares)
- Joins eficientes con hoja Trabajadores
- ID inmutable (nombre puede cambiar)

**Impacto:**
- `ActionRequest`: `worker_nombre: str` → `worker_id: int`
- ActionService: Recibe worker_id, obtiene nombre via `WorkerService.find_worker_by_id()`
- ValidationService: Valida por worker_id
- MetadataRepository: Registra worker_id + worker_nombre (auditoría)

**WorkerService nuevo método:**
```python
def find_worker_by_id(worker_id: int) -> Worker:
    # Raises: WorkerNoEncontradoError si no existe o inactivo
```

**Código:** +37 líneas | 8 tests

---

## 4. Sistema de Auditoría (Metadata) - Event Sourcing ✅ COMPLETADO DÍA 4

### 4.1. Arquitectura Event Sourcing

**Principio:** Estado actual se reconstruye desde eventos inmutables

**Hojas:**
- **Operaciones:** READ + WRITE controlado (UPDATE columnas AL/AN/AK/AM al INICIAR/COMPLETAR)
- **Metadata:** APPEND-ONLY (log inmutable eventos para auditoría + ownership validation)

**Flujo:**
1. INICIAR: Escribe evento → Metadata | Actualiza trabajador → Operaciones
2. COMPLETAR: Escribe evento → Metadata | Actualiza fecha → Operaciones
3. Query estado: Lee últimos eventos de Metadata para reconstruir ownership

### 4.2. Hoja "Metadata" - Estructura

| Columna | Tipo | Descripción | Ejemplo |
|---------|------|-------------|---------|
| A: id | UUID | Único del evento | 550e8400-e29b-... |
| B: timestamp | ISO 8601 | UTC con Z | 2025-12-10T14:35:22Z |
| C: evento_tipo | EventoTipo | INICIAR_ARM, COMPLETAR_ARM, etc. | INICIAR_ARM |
| D: tag_spool | str | Código spool | MK-1335-CW-25238-011 |
| E: worker_id | int | ID trabajador | 93 |
| F: worker_nombre | str | Nombre completo | Mauricio Rodriguez |
| G: operacion | str | ARM, SOLD, METROLOGIA | ARM |
| H: accion | Accion | INICIAR, COMPLETAR, CANCELAR | INICIAR |
| I: fecha_operacion | str | YYYY-MM-DD | 2025-12-10 |
| J: metadata_json | str? | JSON adicional | {"device":"tablet-01"} |

**EventoTipo Enum:**
```
INICIAR_ARM, COMPLETAR_ARM, CANCELAR_ARM
INICIAR_SOLD, COMPLETAR_SOLD, CANCELAR_SOLD
INICIAR_METROLOGIA, COMPLETAR_METROLOGIA, CANCELAR_METROLOGIA
```

### 4.3. MetadataRepository ✅

**Métodos implementados:**
- `append_event(event: MetadataEvent)` → None (con retry 3x + exponential backoff)
- `get_events_by_spool(tag_spool)` → List[MetadataEvent] (ordenados por timestamp)
- `has_completed_action(tag_spool, operacion)` → bool
- `get_worker_in_progress(tag_spool, operacion)` → Optional[str] (ownership validation)

**Características:**
- Retry decorator con exponential backoff (1s → 2s → 4s)
- Parsing robusto con error logging
- Inmutabilidad (nunca UPDATE/DELETE, solo APPEND)

**Implementación:** 180 líneas | Tests incluidos en 54 tests DÍA 4

### 4.4. Integración con ValidationService ✅

**Uso para ownership validation:**
```python
# Al COMPLETAR, verificar quién inició:
worker_iniciador = metadata_repo.get_worker_in_progress(tag_spool, operacion)
if worker_iniciador != worker_nombre_actual:
    raise NoAutorizadoError(...)
```

**Estado:** Implementado y 54 tests passing (SheetsService + ValidationService)

---

## 5. Operación METROLOGÍA 🟡 NICE-TO-HAVE

**Estado:** Especificado, NO implementado (prioridad baja, solo si alcanza tiempo antes 14 Dic)

**Workflow:** BA (Materiales) → ARM (BB) → SOLD (BD) → METROLOGÍA (BF)

**Columnas Sheet:**
- X (24): estado_metrologia (0/0.1/1.0)
- BF (58): fecha_metrologia (DD/MM/YYYY)
- BG (59): metrologo (nombre trabajador)

**Validaciones INICIAR:**
- SOLD = 1.0 (completado)
- BD llena (Fecha_Soldadura)
- metrologia = 0
- metrologo vacío

**Validaciones COMPLETAR:**
- metrologia = 0.1 (EN_PROGRESO)
- Ownership: metrologo = worker_nombre

**Decisión:** Implementar solo si hay tiempo después de Deploy (baja prioridad vs Frontend + Deploy)

---

## 6. Operaciones Batch (Multiselect) ✅ COMPLETADO DÍA 2

### 6.1. Modelos Batch

**BatchActionRequest:**
```python
{
  "worker_id": int,          # v2.0: int (no str)
  "operacion": ActionType,   # ARM | SOLD | METROLOGIA
  "tag_spools": List[str]    # Máximo 50 spools
}
```
Validación: `len(tag_spools) <= 50` (Pydantic validator)

**BatchActionResult:**
```python
{
  "tag_spool": str,
  "success": bool,
  "message": str,
  "error_code": str | None
}
```

**BatchActionResponse:**
```python
{
  "total": int,
  "exitosos": int,
  "fallidos": int,
  "resultados": List[BatchActionResult]
}
```

### 6.2. ActionService - Métodos Batch ✅

**iniciar_accion_batch(worker_id, operacion, tag_spools):**
- Validación individual por spool
- Continúa si algunos fallan (no lanza excepción)
- Batch update Google Sheets (UNA llamada API, no N)
- Invalidar cache
- Retorna resultados agregados

**completar_accion_batch(worker_id, operacion, tag_spools):**
- Similar pero valida ownership individual
- Actualiza estado → 1.0 + fecha

**cancelar_accion_batch(worker_id, operacion, tag_spools):** 🆕
- Valida ownership individual (solo quien inició puede cancelar)
- Actualiza estado → 0.0 (PENDIENTE)
- Limpia metadata (trabajador, fecha)
- Escribe eventos CANCELAR a Metadata sheet

**Implementación:** +467 líneas | 18 tests passing (100%)

### 6.3. SheetsRepository - Batch Update ✅

**batch_update_cells(updates: List[dict]):**
- UNA llamada `worksheet.batch_update()` para todos los spools
- Performance: ~200ms para 10 spools (vs 2 seg con llamadas individuales)
- Updates estructura:
  ```python
  {
    'fila': int,
    'columna_estado': str,
    'columna_trabajador': str,
    'valor_estado': float,
    'valor_trabajador': str
  }
  ```

### 6.4. Endpoints Batch ✅

**POST /api/iniciar-accion-batch:**
- Request: BatchActionRequest
- Response: BatchActionResponse
- Límite: 50 spools (validado en endpoint + modelo)
- Timeout: 60 seg (configurable uvicorn)

**POST /api/completar-accion-batch:**
- Similar pero valida ownership individual

**POST /api/cancelar-accion-batch:** 🆕
- Request: BatchActionRequest
- Response: BatchActionResponse
- Valida ownership individual (403 si no autorizado)
- Vuelve spools a estado PENDIENTE

**Implementación:** +423 líneas con docstrings completos

### 6.5. Performance Metrics ✅

| Métrica | Objetivo | Real |
|---------|----------|------|
| **Batch 10 spools** | < 3 seg | ~2 seg ✅ |
| **Llamadas API** | 1 (no N) | 1 ✅ |
| **Reducción tiempo** | 80%+ | ~87% ✅ |

**Tests batch:** 18/18 passing
- **INICIAR batch:** 7 tests (success, partial, limit, empty)
- **COMPLETAR batch:** 7 tests (success, partial, ownership, limit)
- **CANCELAR batch:** 4 tests 🆕 (success, partial, ownership, limit)
- Validación límite 50 spools
- Ownership validation individual
- Performance < 3 seg ✅
- Operaciones ARM y SOLD

**Total código DÍA 2:** ~1,557 líneas (+139 por CANCELAR batch)

---

## 7. Testing Backend v2.0

### 7.1. Pirámide de Tests

```
                 /\
                /  \
               / E2E\      20 tests
              /------\
             /        \
            / Integr. \   30 tests
           /------------\
          /              \
         /  Unit Tests    \  178 tests
        /------------------\
       Total: 228 tests (v1.0: 113 + v2.0: +115)
```

**Desglose v2.0:**
- **Unit:** 178 (v1.0: 83 + nuevos: 95)
  - RoleRepository: 20
  - RoleService: 19
  - WorkerService v2: 8
  - ActionService batch: 14
  - SheetsService Event Sourcing: 24
  - ValidationService Metadata: 10
- **Integration:** 30 (v1.0: 20 + nuevos: 10)
- **E2E:** 20 (v1.0: 10 + nuevos: 10)

### 7.2. Coverage Objetivo

| Componente | Target | Crítico |
|------------|--------|---------|
| Total | > 85% | - |
| ValidationService | > 95% | ✅ CRÍTICO |
| ActionService | > 95% | ✅ CRÍTICO |
| Services | > 90% | Alta |
| Repositories | > 80% | Media |
| Routers | > 70% | Baja (cubierto E2E) |

---

## 8. Google Sheets Schema v2.0

### Hojas Activas

| Hoja | Modo | Columnas | Filas | Descripción |
|------|------|----------|-------|-------------|
| **Operaciones** | R/W controlado | 65 | 2,493 | Datos base spools + UPDATE AL/AN/AK/AM |
| **Trabajadores** | READ-ONLY | 4 (A-D) | 9 | Id, Nombre, Apellido, Activo (SIN Rol) |
| **Roles** | READ-ONLY | 3 (A-C) | ~20 | Id, Rol, Activo (multi-rol) |
| **Metadata** | APPEND-ONLY | 10 (A-J) | growing | Event Sourcing log |

### Columnas Críticas Operaciones

| Código | Nombre | Descripción | Update |
|--------|--------|-------------|--------|
| G | TAG_SPOOL | ID único spool | Nunca |
| V | arm | Estado ARM (0/0.1/1.0) | INICIAR/COMPLETAR |
| W | sold | Estado SOLD (0/0.1/1.0) | INICIAR/COMPLETAR |
| X | metrologia | Estado METROLOGÍA (0/0.1/1.0) | Futuro |
| AK | Fecha_Armado | DD/MM/YYYY | COMPLETAR ARM |
| AL | Armador | Nombre trabajador | INICIAR ARM |
| AM | Fecha_Soldadura | DD/MM/YYYY | COMPLETAR SOLD |
| AN | Soldador | Nombre trabajador | INICIAR SOLD |
| AO | Fecha_Metrología | DD/MM/YYYY | Futuro |

### Variables de Entorno

```bash
# Sheet PRODUCCIÓN (ACTIVO)
GOOGLE_SHEET_ID=17iOaq2sv4mSOuJY4B8dGQIsWTTUKPspCtb7gk6u-MaQ

# Hojas
HOJA_OPERACIONES_NOMBRE=Operaciones
HOJA_TRABAJADORES_NOMBRE=Trabajadores
HOJA_ROLES_NOMBRE=Roles
HOJA_METADATA_NOMBRE=Metadata

# Service Account
GOOGLE_SERVICE_ACCOUNT_EMAIL=zeus-mvp@zeus-mvp.iam.gserviceaccount.com
GOOGLE_PRIVATE_KEY=<from-json>
```

---

## 9. API Endpoints v2.0

### Endpoints Implementados

| Método | Endpoint | Descripción | Estado |
|--------|----------|-------------|--------|
| GET | `/api/health` | Health check | v1.0 ✅ |
| GET | `/api/workers` | Lista trabajadores activos | v1.0 ✅ |
| GET | `/api/workers/{id}/roles` | Roles de trabajador | v2.0 ✅ |
| POST | `/api/spools/iniciar` | Spools para INICIAR | v1.0 ✅ |
| POST | `/api/spools/completar` | Spools para COMPLETAR | v1.0 ✅ |
| POST | `/api/iniciar-accion` | INICIAR operación (1 spool) | v1.0 ✅ |
| POST | `/api/completar-accion` | COMPLETAR operación (1 spool) | v1.0 ✅ |
| POST | `/api/cancelar-accion` | CANCELAR operación EN_PROGRESO | v2.0 ✅ |
| POST | `/api/iniciar-accion-batch` | INICIAR batch (hasta 50 spools) | v2.0 ✅ |
| POST | `/api/completar-accion-batch` | COMPLETAR batch (hasta 50 spools) | v2.0 ✅ |

**Total:** 10 endpoints (v1.0: 6 + v2.0: +4)

### Request/Response Schemas v2.0

**ActionRequest (breaking change):**
```json
{
  "worker_id": 93,           // v2.0: int (antes: worker_nombre str)
  "operacion": "ARM",        // ARM | SOLD | METROLOGIA
  "tag_spool": "MK-1335-..." // TAG_SPOOL
}
```

**BatchActionRequest:**
```json
{
  "worker_id": 93,
  "operacion": "ARM",
  "tag_spools": ["MK-001", "MK-002", ...]  // Max 50
}
```

**BatchActionResponse:**
```json
{
  "total": 5,
  "exitosos": 4,
  "fallidos": 1,
  "resultados": [
    {
      "tag_spool": "MK-001",
      "success": true,
      "message": "Acción ARM iniciada exitosamente"
    },
    {
      "tag_spool": "MK-002",
      "success": false,
      "message": "ARM ya fue iniciada en 'MK-002'",
      "error_code": "AccionYaIniciadaError"
    },
    ...
  ]
}
```

---

## 10. Custom Exceptions

| Exception | HTTP Status | Uso |
|-----------|-------------|-----|
| `SpoolNoEncontradoError` | 404 | Spool no existe en hoja Operaciones |
| `WorkerNoEncontradoError` | 404 | Worker ID no existe o inactivo |
| `OperacionInvalidaError` | 400 | Operación no es ARM/SOLD/METROLOGIA |
| `AccionYaIniciadaError` | 400 | Estado != 0 al INICIAR |
| `AccionNoIniciadaError` | 400 | Estado != 0.1 al COMPLETAR |
| `NoAutorizadoError` | 403 | Ownership violation (otro worker) |
| `RolNoAutorizadoError` | 403 | Worker sin rol necesario | v2.0 ✅ |
| `DependenciaNoCompletadaError` | 400 | Prerequisito no cumplido (ej: ARM sin BA) |
| `EstadoInvalidoError` | 400 | Estado no válido para operación |
| `SheetsConnectionError` | 503 | Error conexión Google Sheets API |
| `SheetsUpdateError` | 500 | Error escritura Google Sheets |

---

## 11. Deployment

### Railway Backend v2.0

**URL:** https://zeues-backend-v2-production.up.railway.app (pendiente deploy)

**Configuración:**
- Runtime: Python 3.11
- Start command: `uvicorn main:app --host 0.0.0.0 --port $PORT`
- Environment variables: Mismo `.env.local` + Sheet PRODUCCIÓN
- Health check: `GET /api/health`

**Estado:** 🔴 Pendiente deploy (Sheet PRODUCCIÓN listo, backend listo, falta ejecutar deploy)

### Vercel Frontend v2.0

**URL:** https://zeues-v2.vercel.app (pendiente deploy)

**Estado:** 🔴 Pendiente implementación frontend + deploy

---

## 12. Próximos Pasos (para 14 Dic 2025)

### DÍA 2 Frontend (12-13 Dic) 🔴 PENDIENTE

**P2 - Operación:** Filtrado por roles
- GET `/api/workers/{id}/roles` → mostrar solo operaciones permitidas
- Si worker no tiene rol ARMADOR → ocultar botón ARM

**P3 - Tipo Interacción:** Botón CANCELAR
- Mostrar si operación EN_PROGRESO
- POST `/api/cancelar-accion`

**P4 - Seleccionar Spool:** Multiselect
- Checkboxes en cada Card
- "Seleccionar Todos" / "Deseleccionar Todos"
- Contador "X spools seleccionados" (max 50)
- Campo búsqueda TAG_SPOOL (filtrado en tiempo real)

**P5/P6 - Confirmación/Éxito:** Batch UI
- P5: "¿Iniciar ARM en 5 spools?" con lista
- P6: Resultados batch (4 exitosos, 1 fallido con detalle)

### DÍA 3 Deploy (13-14 Dic) 🔴 PENDIENTE

1. **Tests E2E frontend:** +3 nuevos
   - Multiselect 5 spools
   - Cancelar acción EN_PROGRESO
   - Búsqueda TAG_SPOOL

2. **Deploy Railway backend v2.0:**
   - Verificar variables de entorno (Sheet PRODUCCIÓN)
   - Deploy desde branch `v2.0-dev`
   - Smoke tests (30 min)

3. **Deploy Vercel frontend v2.0:**
   - Environment variables (NEXT_PUBLIC_API_URL)
   - Build production
   - Smoke tests

4. **Validación end-to-end:**
   - Flujo completo: Login → Multiselect 5 spools ARM → INICIAR → COMPLETAR
   - Verificar Metadata registrado
   - Performance batch < 5 seg

---

## 13. Resumen Ejecutivo

### Lo Que Está Hecho (80% backend)

✅ **DÍA 4 (10 Dic):** Metadata Event Sourcing
- MetadataEvent model + MetadataRepository
- Arquitectura dual-sheet (Operaciones + Metadata)
- 54 tests passing

✅ **DÍA 1 (11-12 Dic):** Sistema Roles + CANCELAR
- RoleRepository + RoleService (multi-rol)
- ValidationService integración roles
- Endpoint POST /api/cancelar-accion
- Migration worker_id (breaking change)
- 47 tests passing

✅ **DÍA 2 Backend (12 Dic):** Operaciones Batch
- ActionService batch methods
- Endpoints batch (iniciar/completar)
- Modelos Pydantic batch
- Performance < 3 seg para 10 spools ✅
- 14 tests passing

**Total:** 228 tests passing | ~3,518 líneas código nuevo | 11 archivos nuevos

### Lo Que Falta (20%)

🔴 **DÍA 2 Frontend (12-13 Dic):**
- P2-P6 con multiselect, roles UI, cancelar, búsqueda
- ~6-8 horas desarrollo

🔴 **DÍA 3 Deploy (13-14 Dic):**
- Tests E2E frontend +3
- Deploy Railway + Vercel
- Smoke tests + validación
- ~4-6 horas total

🟡 **METROLOGÍA:** Nice-to-have (solo si alcanza tiempo)

### Breaking Changes Críticos

1. **API Request:** `worker_nombre: str` → `worker_id: int` ✅
2. **Sheet Trabajadores:** Columna D (Rol) eliminada ✅
3. **Sheet Roles:** Nueva hoja multi-rol (3 columnas) ✅
4. **Metadata Event Sourcing:** Arquitectura dual-sheet ✅

### Deadline

**14 Dic 2025** (2 días restantes) → Frontend + Deploy
**15-16 Dic:** Buffer si necesario

---

**FIN - proyecto-v2-backend.md - ZEUES v2.0 Backend - Versión 2.0 LLM-Optimized**
