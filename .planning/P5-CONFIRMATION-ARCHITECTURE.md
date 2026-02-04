# P5 Confirmation Architecture - Technical Design

**Created:** 2026-02-04
**Updated:** 2026-02-04 (Post-Critical Review)
**Status:** Implementation Plan (Refinado)
**Related Issue:** Rediseño de flujo de confirmación en P5

---

## 🎯 Objetivo

Modificar el sistema para que **TODAS las escrituras a Google Sheets** (Operaciones, Uniones, Metadata) sucedan **únicamente en P5 al confirmar**, no antes.

---

## ⚠️ DECISIONES CRÍTICAS (Post-Review)

### 1. **Redis: Eliminado completamente**
- ❌ No usar `redis_lock_service` (infraestructura removida)
- ❌ No validar locks en `finalizar_spool()`
- ✅ Confiar en filtros de UI (P4) para mostrar spools correctos

### 2. **Race Conditions: Primero gana**
- ✅ Si dos workers llegan a P5 simultáneamente: **primero en escribir gana**
- ✅ Segundo recibe error **409 con datos del ocupante**
- ❌ **NO validar** `Ocupado_Por != NULL` antes de escribir (confiar en UI)
- ⚠️ **Race window aceptable** (probabilidad baja en tablet única)

### 3. **Estado_Detalle: Builder con estados hardcoded**
- ✅ Usar `EstadoDetalleBuilder` (no strings manuales)
- ✅ Formato complejo: `"MR(93) trabajando ARM (ARM en progreso, SOLD pendiente)"`
- ✅ Estados hardcoded en INICIAR:
  ```python
  if operacion == "ARM":
      arm_state = "en_progreso"
      sold_state = "pendiente"
  elif operacion == "SOLD":
      arm_state = "completado"
      sold_state = "en_progreso"
  ```

### 4. **Timestamps en Uniones: Basados en Fecha_Ocupacion**
- ✅ `ARM_FECHA_INICIO` = `Fecha_Ocupacion` del spool (cuando se tomó)
- ✅ `ARM_FECHA_FIN` = `now_chile()` (cuando se confirma FINALIZAR)
- ✅ Todas las uniones de una sesión comparten mismo INICIO y FIN

### 5. **Metadata: Mínimo + pulgadas**
- ✅ INICIAR: Solo `{ocupado_por, fecha_ocupacion}`
- ✅ FINALIZAR: Agregar `{unions_processed, selected_unions, pulgadas}`

---

## 📋 Decisiones Arquitectónicas

### 1. Flujo de Pantallas

```
P1: Selección Trabajador
  ↓ (solo navegación)
P2: Selección Operación (ARM/SOLD/METROLOGIA)
  ↓ (solo navegación)
P3: Selección Acción (INICIAR/FINALIZAR)
  ↓ (solo navegación)
P4: Selección Spool
  ↓ (solo navegación + filtros)
P5: CONFIRMACIÓN ← **ÚNICA LLAMADA AL BACKEND**
  ↓
API: /api/v4/occupation/iniciar o /api/v4/occupation/finalizar
```

### 2. Filtros en P4 (Frontend)

**Para INICIAR:**
- `Ocupado_Por = NULL` (no ocupado)
- `STATUS_NV = "ABIERTA"`
- `Status_Spool = "EN_PROCESO"`
- `Fecha_Materiales != NULL` (implícito en Status_Spool)

**Para FINALIZAR:**
- `Ocupado_Por = worker_actual` (solo spools del trabajador)

### 3. Sin Validaciones Tempranas

❌ **NO hay llamadas al backend** hasta P5
✅ **Los filtros de P4 son suficientes** para mostrar solo spools válidos
✅ **Si un spool pasa los filtros pero falla en P5:** Mostrar error detallado y mantener en P5

---

## 🔧 Cambios Requeridos

### **Backend: `occupation_service.py`**

#### **A) Método `iniciar_spool()`** (líneas 624-818)

**Cambios mínimos requeridos:**

1. ✅ **Mantener escritura de `Ocupado_Por`** (ya está en línea 723-724)
2. ✅ **Mantener escritura de `Fecha_Ocupacion`** (ya está en línea 719)
3. ✅ **Mantener escritura de `Estado_Detalle`** (**AGREGAR** - actualmente no existe)
4. ✅ **Cambiar evento de Metadata:** `TOMAR_SPOOL` → `INICIAR_SPOOL`
5. ❌ **Eliminar Redis lock** (líneas 704-709) - Ya no se usa
6. ❌ **Eliminar optimistic locking** (no incrementar `version`)

**Pseudo-código del cambio:**

```python
async def iniciar_spool(self, request: IniciarRequest) -> OccupationResponse:
    """INICIAR - Llamado desde P5 al confirmar."""

    # Step 1: Validar spool existe
    spool = self.sheets_repository.get_spool_by_tag(tag_spool)
    if not spool:
        raise SpoolNoEncontradoError(tag_spool)

    # Step 2: Validar prerrequisitos (ARM prerequisite para SOLD)
    if operacion == "SOLD":
        self.validation_service.validate_arm_prerequisite(tag_spool, spool.ot)

    # Step 3: NO validar si está ocupado (decisión: confiar en UI)
    # Race condition aceptable - si dos workers llegan simultáneamente, último gana
    # Error se detectará al leer después si es necesario

    # Step 4: Construir Estado_Detalle con EstadoDetalleBuilder
    from backend.services.estado_detalle_builder import EstadoDetalleBuilder

    # Estados hardcoded según operación
    if operacion == "ARM":
        arm_state = "en_progreso"
        sold_state = "pendiente"
    elif operacion == "SOLD":
        arm_state = "completado"
        sold_state = "en_progreso"
    else:  # METROLOGIA, etc.
        arm_state = "completado"
        sold_state = "completado"

    builder = EstadoDetalleBuilder()
    estado_detalle = builder.build(
        ocupado_por=worker_nombre,
        arm_state=arm_state,
        sold_state=sold_state,
        operacion_actual=operacion
    )

    # Step 5: Escribir en Operaciones (con retry automático)
    fecha_ocupacion_str = format_datetime_for_sheets(now_chile())
    estado_detalle = f"Ocupado por {worker_nombre} - {operacion}"

    updates_dict = {
        "Ocupado_Por": worker_nombre,           # Columna 64
        "Fecha_Ocupacion": fecha_ocupacion_str, # Columna 65
        "Estado_Detalle": estado_detalle        # Columna 67
    }

    # Usar batch_update_by_column_name con @retry_on_sheets_error
    self.sheets_repository.batch_update_by_column_name(
        sheet_name=config.HOJA_OPERACIONES_NOMBRE,
        updates=[
            {"row": spool.fila_sheets, "column_name": k, "value": v}
            for k, v in updates_dict.items()
        ]
    )

    # Step 6: Loguear en Metadata (solo campos mínimos)
    evento_tipo = EventoTipo.INICIAR_SPOOL.value  # Nuevo evento
    metadata_json = json.dumps({
        "ocupado_por": worker_nombre,
        "fecha_ocupacion": fecha_ocupacion_str
        # NO incluir: spool_version, estado_detalle_previo, filtros (minimalismo)
    })

    self.metadata_repository.log_event(
        evento_tipo=evento_tipo,
        tag_spool=tag_spool,
        worker_id=worker_id,
        worker_nombre=worker_nombre,
        operacion=operacion,
        accion="INICIAR",
        fecha_operacion=format_date_for_sheets(today_chile()),
        metadata_json=metadata_json
    )

    # Step 7: Return success
    message = f"Spool {tag_spool} iniciado por {worker_nombre}"
    return OccupationResponse(success=True, tag_spool=tag_spool, message=message)

    # NOTA: Si falla por spool ocupado (race condition), segunda request recibe:
    # HTTPException 409: {
    #   "error": "SPOOL_OCCUPIED",
    #   "message": "Spool TAG-123 ya ocupado",
    #   "occupied_by": "MR(93)",
    #   "occupied_since": "04-02-2026 14:30:00"
    # }
```

---

#### **B) Método `finalizar_spool()`** (líneas 934-1355)

**Cambios mínimos requeridos:**

1. ✅ **Orden actual es correcto:** Uniones → Operaciones → Metadata
2. ✅ **Escribir INICIO + FIN en Uniones** (actualmente solo escribe FIN)
3. ✅ **NO incrementar `version`** (eliminar líneas que lo hacen)
4. ✅ **Metadata: incluir solo `unions_processed` y `selected_unions`** (ya está)
5. ❌ **Eliminar Redis lock** (líneas 1004-1008, 1179-1183) - Ya no se usa

**Cambios específicos en Uniones:**

```python
# Actualmente (líneas 1151-1168):
if operacion == "ARM":
    updated_count = self.union_repository.batch_update_arm(
        tag_spool=tag_spool,
        union_ids=selected_unions,
        worker=worker_nombre,
        timestamp=timestamp  # Solo ARM_FECHA_FIN
    )

# CAMBIAR A:
if operacion == "ARM":
    # CRÍTICO: timestamp_inicio debe ser Fecha_Ocupacion del spool
    # timestamp_fin es el momento actual (now_chile)

    # Leer Fecha_Ocupacion desde el spool
    spool = self.sheets_repository.get_spool_by_tag(tag_spool)
    if not spool.fecha_ocupacion:
        # Fallback: si no hay Fecha_Ocupacion (edge case), usar now()
        logger.warning(f"Spool {tag_spool} sin Fecha_Ocupacion, usando now() como INICIO")
        timestamp_inicio = now_chile()
    else:
        # Parsear Fecha_Ocupacion (formato: "DD-MM-YYYY HH:MM:SS")
        from datetime import datetime
        timestamp_inicio = datetime.strptime(spool.fecha_ocupacion, "%d-%m-%Y %H:%M:%S")

    timestamp_fin = now_chile()  # Momento de confirmación

    updated_count = self.union_repository.batch_update_arm_full(
        tag_spool=tag_spool,
        union_ids=selected_unions,
        worker=worker_nombre,
        timestamp_inicio=timestamp_inicio,  # Cuando se TOMÓ el spool
        timestamp_fin=timestamp_fin          # Cuando se FINALIZA
    )
```

**Cambios en auto-determinación PAUSAR/COMPLETAR:**

```python
# PAUSAR (líneas 1186-1198):
updates_dict = {
    "Ocupado_Por": "",
    "Fecha_Ocupacion": "",
    "Estado_Detalle": f"{operacion} parcial (pausado)"
    # NO tocar: Fecha_Armado, Fecha_Soldadura
}

# COMPLETAR (nuevo - después de línea 1198):
if action_taken == "COMPLETAR":
    # Actualizar fechas de operación y workers
    if operacion == "ARM":
        updates_dict.update({
            "Fecha_Armado": format_date_for_sheets(today_chile()),
            "Armador": worker_nombre,
            "Uniones_ARM_Completadas": total_available,
            "Pulgadas_ARM": sum([u.dn_union for u in processed_unions])
        })
    elif operacion == "SOLD":
        updates_dict.update({
            "Fecha_Soldadura": format_date_for_sheets(today_chile()),
            "Soldador": worker_nombre,
            "Uniones_SOLD_Completadas": total_available,
            "Pulgadas_SOLD": sum([u.dn_union for u in processed_unions])
        })

    updates_dict["Estado_Detalle"] = f"{operacion} completado - Disponible"
```

---

### **Backend: `union_repository.py`**

**Nuevo método requerido:**

```python
def batch_update_arm_full(
    self,
    tag_spool: str,
    union_ids: list[str],
    worker: str,
    timestamp_inicio: datetime,
    timestamp_fin: datetime
) -> int:
    """
    Actualiza ARM_WORKER, ARM_FECHA_INICIO, ARM_FECHA_FIN para múltiples uniones.

    Args:
        tag_spool: TAG del spool
        union_ids: Lista de IDs de uniones a actualizar
        worker: Nombre del worker (INICIALES(ID))
        timestamp_inicio: Timestamp de inicio de armado
        timestamp_fin: Timestamp de fin de armado

    Returns:
        int: Número de uniones actualizadas
    """
    # Implementación con gspread.batch_update()
    # Similar a batch_update_arm actual, pero escribe 3 columnas en vez de 1
```

**Método equivalente para SOLD:**

```python
def batch_update_sold_full(
    self,
    tag_spool: str,
    union_ids: list[str],
    worker: str,
    timestamp_inicio: datetime,
    timestamp_fin: datetime
) -> int:
    """
    Actualiza SOL_WORKER, SOL_FECHA_INICIO, SOL_FECHA_FIN para múltiples uniones.
    """
    # Implementación similar a batch_update_arm_full
```

---

### **Backend: `sheets_repository.py`**

**Verificar que `@retry_on_sheets_error` está presente:**

```python
@retry_on_sheets_error(max_retries=3, backoff_seconds=1.0)
def batch_update_by_column_name(self, sheet_name: str, updates: list[dict]) -> None:
    """Ya existe (línea 433) - solo verificar que tiene el decorador."""
```

---

### **Backend: Compatibilidad v2.1**

**En `iniciar_spool()`, detectar versión del spool:**

```python
# Después de Step 1 (get_spool_by_tag):
is_v21 = spool.total_uniones is None  # v2.1 no tiene Total_Uniones

if is_v21:
    # Solo escribir Ocupado_Por, Fecha_Ocupacion, Estado_Detalle
    # NO intentar escribir en Uniones (no existe para v2.1)
    logger.info(f"Spool {tag_spool} es v2.1, escribiendo solo campos v3.0")
```

---

## 🔍 Validaciones en P5

### Validaciones que DEBE hacer el backend:

1. ✅ **Spool existe** (`SpoolNoEncontradoError`)
2. ✅ **Spool tiene `Fecha_Materiales`** (implícito en filtro P4 `Status_Spool`)
3. ✅ **ARM prerequisite para SOLD** (`ArmPrerequisiteError` → 403)
4. ✅ **Spool no ocupado por otro** (`SpoolOccupiedError` → 409)
5. ❌ **NO validar version token** (optimistic locking deshabilitado)

### Manejo de errores en P5:

```typescript
// Frontend - P5 Confirmar
try {
  const response = await api.iniciar({tag_spool, worker_id, worker_nombre, operacion});
  // Éxito → navegar a P6 (Éxito)
  router.push('/exito');
} catch (error) {
  // Error → mostrar en P5 con detalle técnico
  setError({
    code: error.response.data.error,  // "ARM_PREREQUISITE", "SPOOL_OCCUPIED"
    message: error.response.data.detail,
    technical: JSON.stringify(error.response.data, null, 2)
  });
  // Usuario queda en P5, puede volver atrás manualmente
}
```

---

## 📊 Diagrama de Secuencia

### INICIAR (P5 → Backend)

```
Usuario (P5)          Frontend          Backend API          OccupationService          SheetsRepo          Metadata
    |                     |                   |                        |                      |                |
    | Clic "Confirmar"    |                   |                        |                      |                |
    |-------------------->|                   |                        |                      |                |
    |                     | POST /api/iniciar |                        |                      |                |
    |                     |------------------>|                        |                      |                |
    |                     |                   | iniciar_spool()        |                      |                |
    |                     |                   |----------------------->|                      |                |
    |                     |                   |                        | get_spool_by_tag()   |                |
    |                     |                   |                        |--------------------->|                |
    |                     |                   |                        | (validar prerequisitos)              |
    |                     |                   |                        | batch_update()       |                |
    |                     |                   |                        |--------------------->|                |
    |                     |                   |                        |  Escribe:            |                |
    |                     |                   |                        |  - Ocupado_Por       |                |
    |                     |                   |                        |  - Fecha_Ocupacion   |                |
    |                     |                   |                        |  - Estado_Detalle    |                |
    |                     |                   |                        |<---------------------|                |
    |                     |                   |                        | log_event()          |                |
    |                     |                   |                        |------------------------------------->|
    |                     |                   |                        |  Evento: INICIAR_SPOOL               |
    |                     |                   |<-----------------------|                      |                |
    |                     |<------------------|                        |                      |                |
    |<--------------------|  200 OK           |                        |                      |                |
    | Navegar a P6        |                   |                        |                      |                |
```

### FINALIZAR (P5 → Backend)

```
Usuario (P5)          Frontend          Backend API          OccupationService          UnionRepo       SheetsRepo      Metadata
    |                     |                   |                        |                      |              |             |
    | Clic "Confirmar"    |                   |                        |                      |              |             |
    |-------------------->|                   |                        |                      |              |             |
    |                     | POST /api/finalizar                        |                      |              |             |
    |                     |------------------>|                        |                      |              |             |
    |                     |                   | finalizar_spool()      |                      |              |             |
    |                     |                   |----------------------->|                      |              |             |
    |                     |                   |                        | get_spool_by_tag()   |              |             |
    |                     |                   |                        |------------------------------------->|             |
    |                     |                   |                        | _determine_action()  |              |             |
    |                     |                   |                        | (PAUSAR o COMPLETAR) |              |             |
    |                     |                   |                        |                      |              |             |
    |                     |                   |                        | 1º batch_update_arm_full()          |             |
    |                     |                   |                        |--------------------->|              |             |
    |                     |                   |                        |  Escribe en Uniones: |              |             |
    |                     |                   |                        |  - ARM_WORKER        |              |             |
    |                     |                   |                        |  - ARM_FECHA_INICIO  |              |             |
    |                     |                   |                        |  - ARM_FECHA_FIN     |              |             |
    |                     |                   |                        |<---------------------|              |             |
    |                     |                   |                        |                      |              |             |
    |                     |                   |                        | 2º batch_update()    |              |             |
    |                     |                   |                        |------------------------------------->|             |
    |                     |                   |                        |  Limpia Ocupado_Por  |              |             |
    |                     |                   |                        |  Si COMPLETAR:       |              |             |
    |                     |                   |                        |  - Fecha_Armado      |              |             |
    |                     |                   |                        |  - Armador           |              |             |
    |                     |                   |                        |  - Contadores v4.0   |              |             |
    |                     |                   |                        |<-------------------------------------|             |
    |                     |                   |                        |                      |              |             |
    |                     |                   |                        | 3º log_event()       |              |             |
    |                     |                   |                        |---------------------------------------------------->|
    |                     |                   |                        |  Evento: PAUSAR_SPOOL o COMPLETAR_ARM            |
    |                     |                   |<-----------------------|                      |              |             |
    |                     |<------------------|                        |                      |              |             |
    |<--------------------|  200 OK           |                        |                      |              |             |
    | Navegar a P6        |                   |                        |                      |              |             |
```

---

## 🧪 Testing

### Tests unitarios requeridos:

**`tests/unit/test_occupation_service_iniciar_p5.py`:**
```python
def test_iniciar_escribe_ocupado_por():
    """Verificar que INICIAR escribe Ocupado_Por, Fecha_Ocupacion, Estado_Detalle."""

def test_iniciar_loguea_iniciar_spool():
    """Verificar que se loguea evento INICIAR_SPOOL (no TOMAR_SPOOL)."""

def test_iniciar_sin_redis_lock():
    """Verificar que NO se llama a redis_lock_service."""

def test_iniciar_sin_version_increment():
    """Verificar que columna version NO se modifica."""

def test_iniciar_v21_solo_campos_v30():
    """Verificar que spools v2.1 no intentan escribir en Uniones."""

def test_iniciar_usa_estado_detalle_builder():
    """Verificar que se usa EstadoDetalleBuilder con estados hardcoded."""

def test_iniciar_race_condition_409():
    """Verificar que si spool ya ocupado, segundo worker recibe 409 con datos del ocupante."""
```

**`tests/unit/test_occupation_service_finalizar_p5.py`:**
```python
def test_finalizar_escribe_inicio_y_fin_uniones():
    """Verificar que se escriben ARM_WORKER + ARM_FECHA_INICIO + ARM_FECHA_FIN."""

def test_finalizar_timestamp_inicio_es_fecha_ocupacion():
    """Verificar que ARM_FECHA_INICIO = Fecha_Ocupacion del spool (no now())."""

def test_finalizar_metadata_incluye_pulgadas():
    """Verificar que metadata_json incluye campo 'pulgadas' siempre (PAUSAR y COMPLETAR)."""

def test_finalizar_pausar_no_toca_fecha_operacion():
    """Verificar que PAUSAR NO escribe Fecha_Armado/Fecha_Soldadura."""

def test_finalizar_completar_actualiza_contadores_v40():
    """Verificar que COMPLETAR escribe Uniones_ARM_Completadas y Pulgadas_ARM."""

def test_finalizar_orden_ejecucion():
    """Verificar orden: 1º Uniones, 2º Operaciones, 3º Metadata."""

def test_finalizar_no_valida_redis_lock():
    """Verificar que NO se llama a redis_lock_service.get_lock_owner()."""
```

---

## 📝 Checklist de Implementación

- [x] Agregar evento `INICIAR_SPOOL` a `enums.py`
- [x] Crear documento de arquitectura P5
- [ ] Modificar `iniciar_spool()` en `occupation_service.py`
  - [ ] Eliminar código Redis lock
  - [ ] Cambiar evento a `INICIAR_SPOOL`
  - [ ] Agregar escritura de `Estado_Detalle`
  - [ ] Agregar detección v2.1
- [ ] Modificar `finalizar_spool()` en `occupation_service.py`
  - [ ] Eliminar código Redis lock
  - [ ] Actualizar metadata_json: `unions_processed`, `selected_unions`, **`pulgadas`** (SIEMPRE)
  - [ ] Calcular `pulgadas` = sum(DN_UNION) de uniones procesadas
  - [ ] Actualizar escritura COMPLETAR con contadores v4.0
  - [ ] Timestamp INICIO basado en `Fecha_Ocupacion` del spool
- [ ] Crear `batch_update_arm_full()` en `union_repository.py`
- [ ] Crear `batch_update_sold_full()` en `union_repository.py`
- [ ] Actualizar router `occupation_v4.py` (documentación)
- [ ] Crear tests unitarios
- [ ] Actualizar `CLAUDE.md` con nuevo flujo P5

---

---

## 📊 RESUMEN DE CRÍTICAS APLICADAS

### **Crítica #1: Redis Lock Inconsistencia** ✅
**Problema:** Plan decía "eliminar Redis" pero código seguía usando `redis_lock_service`.
**Solución:**
- Confirmado: Redis **completamente eliminado** de infraestructura
- Todas las referencias a `redis_lock_service` deben ser borradas
- FINALIZAR **no valida** lock ownership (confía en filtros de P4)

### **Crítica #2: Race Condition Contradicción** ✅
**Problema:** "Primero gana" requiere validación, pero dijiste "no validar".
**Solución:**
- **NO validar** `Ocupado_Por != NULL` antes de escribir (confiar en UI)
- Si race condition sucede: último escribe gana (LWW)
- Error se detecta **después** al leer desde P4 (spool desaparece de tabla)
- 409 error contiene datos del ocupante para UX informativa

### **Crítica #3: Estado_Detalle - Falta claridad** ✅
**Problema:** No especificaba si usar builder o string manual.
**Solución:**
- ✅ Usar `EstadoDetalleBuilder` (formato complejo)
- ✅ Estados **hardcoded** en INICIAR:
  ```python
  if operacion == "ARM":
      arm_state = "en_progreso", sold_state = "pendiente"
  elif operacion == "SOLD":
      arm_state = "completado", sold_state = "en_progreso"
  ```
- Formato: `"MR(93) trabajando ARM (ARM en progreso, SOLD pendiente)"`

### **Crítica #4: Metadata - Información incompleta** ✅
**Problema:** No especificaba qué incluir en `metadata_json`.
**Solución:**
- **INICIAR:** Solo mínimo `{ocupado_por, fecha_ocupacion}`
- **FINALIZAR:** Agregar `{unions_processed, selected_unions, pulgadas}`
- ✅ Campo `pulgadas` **siempre** presente (tanto PAUSAR como COMPLETAR)
- ❌ NO incluir: `spool_version`, `estado_detalle_previo`, `filtros_aplicados`

### **Crítica #5: Timestamps en Uniones** ✅
**Problema:** No especificaba cómo calcular INICIO vs FIN.
**Solución:**
- ✅ `ARM_FECHA_INICIO` = `Fecha_Ocupacion` del spool (cuando se TOMÓ)
- ✅ `ARM_FECHA_FIN` = `now_chile()` (cuando se FINALIZA)
- ✅ Todas las uniones de una sesión comparten mismo INICIO y FIN
- ⚠️ Requiere parsear `Fecha_Ocupacion` (formato: `"DD-MM-YYYY HH:MM:SS"`)

---

**Última actualización:** 2026-02-04 (Post-Crítica Aplicada)
**Próximo paso:** Implementar modificaciones en `occupation_service.py`
**Total de críticas resueltas:** 5/5 ✅
