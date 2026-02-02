# ZEUES v4.0 - Sistema de Uniones: Especificación Técnica SIMPLIFICADA

**Fecha:** 2026-01-30
**Estado:** ✅ Spec para implementación
**Validación:** ✅ Confirmado con usuarios de planta
**Versión:** SIMPLIFIED (post-análisis)

---

## CHANGELOG vs Spec Original

**Simplificaciones aplicadas:**
- ❌ **S1:** Eliminado workflow completo de creación de uniones (hoja pre-poblada por Ingeniería)
- ❌ **S2:** Eliminado evento `UNION_CREADA` de Metadata
- ❌ **S3:** Rechazado cambio SSE endpoints (mantener v3.0)
- ✅ **C1:** Agregado trigger automático metrología (100% SOLD)
- ✅ **C2:** Corregida validación ARM→SOLD con escenarios parciales
- ✅ **A1:** Confirmado Redis locks permanentes (sin TTL)
- ✅ **A2:** Aclarado Performance SLA

**Impacto:**
- -4 endpoints API (crear/validar uniones)
- -1 componente frontend (AgregarUnionModal)
- -1 breaking change (SSE endpoints)
- -5 tests unitarios
- ~20% reducción complejidad

---

## 1. Contexto y Justificación

### Problema v3.0
- **Métrica incorrecta**: v3.0 rastrea a nivel de spool, pero la unidad de medida real es **pulgada-diámetro**
- **Facturación**: Cliente paga por pulgadas-diámetro trabajadas, no por spools
- **Rendimiento**: Trabajadores se miden por pulgadas-diámetro completadas por día
- **Workflow real**: Trabajadores trabajan por unión individual (no por spool completo)
- **Metrología**: Inspecciona cada unión, no el spool agregado

### Validación Usuario
> "La principal unidad de medida es la pulgada diámetro, así se mide el rendimiento de la planta, de los trabajadores y es la información que necesita el cliente. La pulgada diámetro te la dan las uniones no el spool. Además los trabajadores trabajan por unión no por spool al igual que metrología."

**Conclusión**: v4.0 es **crítico**. v3.0 mide la métrica equivocada.

---

## 2. Decisiones Arquitectónicas CRÍTICAS

### ✅ D1: Mantener TAG_SPOOL como Primary Key
**NO renombrar a OT**

**Razón**: Evitar breaking changes innecesarios
**Impacto**: Redis keys, Metadata, queries permanecen sin cambios

```
✅ Mantener: spool:{TAG_SPOOL}:lock
❌ NO hacer: spool:{OT}:lock
```

---

### ✅ D2: Deprecar Armador/Soldador/Fecha_Armado/Fecha_Soldadura
**Dejar de escribir en estas 4 columnas de Operaciones**

**Razón**: Redundante con hoja Uniones (single source of truth)
**Estrategia**: Calcular on-demand desde Uniones cuando se necesite

```python
# ❌ NO escribir más
Operaciones.Armador / Soldador / Fecha_Armado / Fecha_Soldadura

# ✅ Calcular desde Uniones
get_primer_armador(tag_spool) → query Uniones WHERE ARM_WORKER != NULL ORDER BY ARM_FECHA_INICIO LIMIT 1
```

**Migración**:
- Columnas quedan en Operaciones (no eliminar físicamente)
- Nuevos registros: NULL
- Registros v3.0 antiguos: mantienen valores históricos
- Frontend lee desde Uniones para datos nuevos

---

### ✅ D3: Batch Writes (NO Sequential Loop)
**Usar batch API de Google Sheets**

**Razón**: Performance crítica

```python
# ❌ Original VERSION-4.0 (6+ segundos para 10 uniones)
for n_union in selected_unions:
    union_repo.update_arm(...)   # 300ms
    metadata_repo.log_event(...) # 300ms

# ✅ v4.0 Optimizado (< 1 segundo)
union_repo.batch_update_arm(tag_spool, selected_unions, ...)  # 1 batch call
metadata_repo.batch_log_events(eventos)                       # 1 batch call
```

**Técnica**: `gspread.batch_update()` y `worksheet.append_rows()`

---

### ✅ D4: UX Simplificada - INICIAR/FINALIZAR con Auto-determinación
**Simplificar de 3 botones (TOMAR/PAUSAR/COMPLETAR) a 2 botones (INICIAR/FINALIZAR)**

**Razón**: Reducir complejidad cognitiva del usuario. Auto-determinación PAUSAR vs COMPLETAR basada en selección de uniones.

**UX Flow:**
```
P3: [INICIAR] o [FINALIZAR]

INICIAR:
  → P4: Seleccionar spool disponible
  → P5: Confirmar
  → Efecto: Solo ocupa spool (Ocupado_Por + lock Redis), NO toca hoja Uniones

FINALIZAR:
  → P4: Seleccionar spool ocupado por el trabajador
  → P5: Seleccionar uniones completadas (checkboxes)
  → P6: Confirmar
  → Efecto:
     - Si 7/10 uniones → PAUSAR (libera spool)
     - Si 10/10 uniones → COMPLETAR (libera spool)
     - Auto-determinación sin intervención del usuario
```

**Timestamps:**
- `ARM_FECHA_INICIO` = `Fecha_Ocupacion` (del INICIAR previo)
- `ARM_FECHA_FIN` = `now()` (al confirmar FINALIZAR)

---

### ✅ D5: Validación ARM→SOLD Configurable con Parcialidad

**Regla física:** No puedes soldar sin armar (validación de integridad manufacturera)

**Implementación v4.0:**

**INICIAR SOLD (nivel spool):**
```python
REQUIRE_ARM_BEFORE_SOLD = True  # Config default

if operacion == "SOLD":
    uniones_armadas = count_uniones_where(tag_spool, ARM_FECHA_FIN IS NOT NULL)
    if uniones_armadas == 0:
        raise ValidationError("El spool debe tener al menos 1 unión armada antes de iniciar soldadura")
```

**FINALIZAR SOLD (nivel unión):**
```python
# GET /api/uniones/{tag}/disponibles?operacion=SOLD
# Retorna SOLO uniones soldables (armadas pero no soldadas)
WHERE ARM_FECHA_FIN IS NOT NULL AND SOL_FECHA_FIN IS NULL
```

**Frontend P5:**
- Usuario ve checkboxes SOLO para uniones soldables (backend ya filtró)
- Puede seleccionar parcial (ej: 5 de 7 soldables) → `SPOOL_SOLD_PAUSADO`
- Puede seleccionar todas (7 de 7 soldables) → Verifica si 7 = total uniones del spool

**Escenario edge case:**
```
Spool 10 uniones: 6 armadas, 4 sin armar
→ INICIAR SOLD: ✅ Pasa (>= 1 armada)
→ P5 muestra: 6 checkboxes (solo las 6 armadas)
→ Completa 6/6 → SPOOL_SOLD_PAUSADO (porque 6 ≠ 10 total)
→ Las 4 sin armar quedan pendientes para ARM futuro
```

**Validación adicional:** Backend previene seleccionar unión sin armar (imposible por filtro, pero doble-check en API)

---

### ✅ D6: Metrología/Reparación v3.0 Temporal (Nivel Spool)

**Scope v4.0:** NO implementar metrología/reparación a nivel de unión.

**Razón**: Reducir complejidad MVP. Granularidad unión requiere:
- Workflow metrología por unión (10x inspecciones)
- Reparación granular (tracking ciclos por unión)
- UI adicional (pantallas selección uniones para NDT)
- Testing extensivo de nuevos flujos

**Implementación v4.0:**
- Metrología sigue v3.0: Inspección nivel spool (APROBADO/RECHAZADO binario)
- Columnas `NDT_UNION`, `R_NDT_UNION` (cols 12-13) quedan NULL en v4.0
- `Estado_Detalle` sigue calculándose a nivel spool
- Endpoints `/api/metrologia/completar` sin cambios
- Frontend metrología/reparación sin modificaciones

**Future (v4.1+):**
- Migrar a inspección granular por unión
- NDT selecciona uniones específicas para inspeccionar (similar a P5)
- Reparación por unión (ciclos independientes)
- Columnas NDT_UNION se empiezan a usar

**Compatibilidad:**
- Endpoints `/api/metrologia/*` y `/api/reparacion/*` sin cambios v4.0
- Estado_Detalle_Builder sigue usando datos nivel spool
- Hoja Uniones incluye columnas NDT pero permanecen NULL (preparación futura)

---

### ✅ D7: Trigger Automático a Metrología (100% SOLD) **[NUEVO]**

**Regla de negocio:**
- SOLD parcial (< 100% uniones) → `SPOOL_SOLD_PAUSADO` (libera spool, NO gatilla metrología)
- SOLD completo (100% uniones) → `SPOOL_SOLD_COMPLETADO` + **Trigger automático a metrología**

**Implementación:**
```python
def finalizar_spool_sold(tag_spool, selected_unions, total_unions):
    if len(selected_unions) == total_unions:
        # 100% completado
        operaciones_repo.update(tag_spool, {
            "Estado": "SOLD",  # Máquina estados v3.0
            "Estado_Detalle": "Soldadura Completada - En Cola Metrología"
        })
        metadata_repo.log_event("SPOOL_SOLD_COMPLETADO", ...)

        # Backend automáticamente lo hace disponible para NDT
        # (Inspector ve el spool en GET /api/metrologia/disponibles)
    else:
        # Parcial
        operaciones_repo.update(tag_spool, {
            "Estado_Detalle": f"Soldadura Parcial ({len(selected_unions)}/{total_unions})"
        })
        metadata_repo.log_event("SPOOL_SOLD_PAUSADO", ...)
```

**UX:** Sin cambios respecto a v3.0 (flujo metrología mantiene mismo comportamiento)

---

## 3. Modelo de Datos

### 3.1 Hoja Uniones - Datos Pre-existentes **[MODIFICADO]**

**✅ IMPORTANTE:** La hoja `Uniones` es creada y poblada por Ingeniería mediante proceso externo (fuera del alcance de la aplicación v4.0).

**PK compuesta**: `TAG_SPOOL + N_UNION`

| # | Columna | Tipo | Validaciones | Notas |
|---|---------|------|--------------|-------|
| 1 | `ID` | String | Único | Formato: `"{TAG_SPOOL}+{N_UNION}"` ej: `"OT-123+5"` |
| 2 | `TAG_SPOOL` | String | FK a Operaciones | Debe existir |
| 3 | `N_UNION` | Integer | Único por TAG_SPOOL, 1 ≤ N ≤ 20 | **Gaps permitidos** (puede ser 1,2,3,5,7) |
| 4 | `DN_UNION` | Decimal | > 0 | Diámetro nominal en pulgadas |
| 5 | `TIPO_UNION` | Enum | `BW` \| `SO` \| `FILL` \| `BR` | Tipo de unión |
| 6 | `ARM_FECHA_INICIO` | DateTime | `DD-MM-YYYY HH:MM:SS` | Timestamp INICIAR (ARM) |
| 7 | `ARM_FECHA_FIN` | DateTime | ≥ ARM_FECHA_INICIO | Timestamp FINALIZAR (ARM) |
| 8 | `ARM_WORKER` | String | Formato: `XY(id)` | ej: `MR(93)` |
| 9 | `SOL_FECHA_INICIO` | DateTime | `DD-MM-YYYY HH:MM:SS` | Timestamp INICIAR (SOLD) |
| 10 | `SOL_FECHA_FIN` | DateTime | ≥ SOL_FECHA_INICIO | Timestamp FINALIZAR (SOLD) |
| 11 | `SOL_WORKER` | String | Formato: `XY(id)` | - |
| 12 | `NDT_UNION` | Enum | `NA` \| `PT` \| `MT` \| `RT` \| `UT` | v4.1+ (NULL en v4.0) |
| 13 | `R_NDT_UNION` | Enum | `Aprobado` \| `Rechazado` \| `NA` | v4.1+ (NULL en v4.0) |
| 14 | `version` | UUID | UUID4 | Optimistic locking |
| 15-18 | Auditoría | - | - | Creado_Por, Fecha_Creacion, Modificado_Por, Fecha_Modificacion |

**Validaciones de integridad (solo para UPDATE):**
- ✅ N_UNION existe en hoja (no crear nuevos)
- ✅ ARM_FECHA_FIN ≥ ARM_FECHA_INICIO
- ✅ SOL_FECHA_FIN ≥ SOL_FECHA_INICIO
- ⚠️ ARM antes de SOLD (configurable: `REQUIRE_ARM_BEFORE_SOLD`)

**Responsabilidad v4.0:**
- ✅ **READ**: Consultar uniones disponibles por spool
- ✅ **UPDATE**: Escribir timestamps ARM/SOLD al completar trabajo
- ❌ **CREATE**: NO implementar creación de uniones (Ingeniería lo hace externamente)
- ❌ **DELETE**: NO implementar eliminación

---

### 3.2 Modificaciones Hoja `Operaciones`

**SIN CAMBIOS**:
- TAG_SPOOL (PK) - Mantener
- Columnas 1-67 (todas v3.0)

**DEPRECATED** (dejar de escribir):
```
Armador           → Calcular desde Uniones.ARM_WORKER
Soldador          → Calcular desde Uniones.SOL_WORKER
Fecha_Armado      → Calcular desde MAX(Uniones.ARM_FECHA_FIN)
Fecha_Soldadura   → Calcular desde MAX(Uniones.SOL_FECHA_FIN)
```

**NUEVAS** (agregar al final, columnas 68-72):

| # | Columna | Tipo | Cálculo |
|---|---------|------|---------|
| 68 | `Total_Uniones` | Integer | `COUNT(*) FROM Uniones WHERE TAG_SPOOL={tag}` |
| 69 | `Uniones_ARM_Completadas` | String | Formato: `"{completadas}/{total}"` ej: `"7/11"` |
| 70 | `Uniones_SOLD_Completadas` | String | Formato: `"{completadas}/{total}"` ej: `"5/11"` |
| 71 | `Pulgadas_ARM` | Decimal | `SUM(DN_UNION) WHERE ARM_FECHA_FIN IS NOT NULL` |
| 72 | `Pulgadas_SOLD` | Decimal | `SUM(DN_UNION) WHERE SOL_FECHA_FIN IS NOT NULL` |

---

### 3.3 Modificaciones Hoja `Metadata`

**Cambio**: Agregar columna `N_UNION` (posición 11 al final, nullable)

**⚠️ IMPORTANTE:** Agregar al FINAL para evitar desplazamiento de columnas existentes.

```
v3.0 (10 cols): ID, Tipo, TAG_SPOOL, Worker, Timestamp, Metadata, version, Creado_Por, Fecha_Creacion, Fecha_Modificacion
v4.0 (11 cols): ID, Tipo, TAG_SPOOL, Worker, Timestamp, Metadata, version, Creado_Por, Fecha_Creacion, Fecha_Modificacion, N_UNION
                                                                                                                          ^^^^^^^^ NUEVA (col 11)
```

**Razón del cambio de posición:**
- Insertar en posición 4 desplaza columnas 4-10 → Rompe queries v3.0 que usan índices
- Agregar al final (posición 11) → Backward compatible, v3.0 ignora columna adicional
- Queries v3.0: `row[3]` (Worker) sigue funcionando
- Queries v4.0: `row[10]` (N_UNION) o usar headers dinámicos

**Reglas de uso N_UNION**:
- **NULL**: Eventos a nivel de spool
- **1-20**: Eventos a nivel de unión específica

**Nuevos tipos de eventos v4.0**:

#### Eventos de Spool (N_UNION = NULL)
| Tipo | Metadata JSON (ejemplo) |
|------|-------------------------|
| `SPOOL_ARM_PAUSADO` | `{uniones_completadas: 7, total: 11, uniones_trabajadas: [1,2,3,4,5,6,7], pulgadas: 18.5}` |
| `SPOOL_ARM_COMPLETADO` | `{uniones_completadas: 11, total: 11, uniones_trabajadas: [8,9,10,11], pulgadas: 28.0}` |
| `SPOOL_SOLD_PAUSADO` | `{uniones_completadas: 5, total: 11, uniones_trabajadas: [1,2,3,4,5], pulgadas: 12.5}` |
| `SPOOL_SOLD_COMPLETADO` | `{uniones_completadas: 11, total: 11, pulgadas: 28.0}` |
| `SPOOL_CANCELADO` | `{operacion: "ARM", motivo: "sin_seleccion"}` |

#### Eventos de Unión Granular (N_UNION = 1-20)
| Tipo | Metadata JSON (ejemplo) |
|------|-------------------------|
| `UNION_ARM_REGISTRADA` | `{dn_union: 2.5, tipo: "BW", timestamp_inicio: "...", timestamp_fin: "...", duracion_min: 45}` |
| `UNION_SOLD_REGISTRADA` | `{dn_union: 3.0, tipo: "SO", timestamp_inicio: "...", timestamp_fin: "...", duracion_min: 60}` |

**Patrón de escritura**: 1 evento batch (spool) + N eventos granulares (uniones)

```
Ejemplo: Seleccionar 7 uniones ARM
→ 8 eventos totales:
  1. SPOOL_ARM_PAUSADO (N_UNION=NULL)
  2-8. UNION_ARM_REGISTRADA (N_UNION=1,2,3,4,5,6,7)
```

---

## 4. Backend Architecture

### 4.1 Nuevos Componentes

**Componente** | **Responsabilidad** | **Métodos Clave**
---|---|---
`models/union.py` | Modelo Pydantic Union | 18 campos (id, tag_spool, n_union, dn_union, arm_*, sol_*, ndt_*, auditoría)
`repositories/union_repository.py` | READ + UPDATE + Queries + **Batch Updates** | `get_disponibles_arm/sold()`, `batch_update_arm/sold()`, `count_completed_*()`, `sum_pulgadas_*()`
`services/union_service.py` | Business logic + Orquestación | `process_selection()`, `calcular_pulgadas()`, `build_eventos_metadata()`
`routers/uniones.py` | API endpoints | `GET /{tag}/disponibles`, `GET /{tag}/metricas`

**CRÍTICO**: `batch_update_arm/sold()` debe usar `gspread.batch_update()` para 1 API call (no loop de N calls)

---

### 4.2 Modificaciones a Componentes Existentes

**MetadataRepository**:
- Agregar parámetro `n_union: Optional[int]` a `log_event()`
- Agregar método `batch_log_events(eventos: list[dict])` para batch insert

**OperacionesRepository**:
- Filtrar deprecated columns en `update()` (ignorar silenciosamente Armador/Soldador/Fecha_Armado/Fecha_Soldadura)
- Agregar métodos `get_armador(tag_spool)` y `get_soldador(tag_spool)` que consultan Uniones

**OccupationService**:
- **NUEVO:** `iniciar_spool(tag_spool, worker_id, operacion)` - Solo escribe Ocupado_Por + Fecha_Ocupacion + lock Redis (NO toca Uniones)
- **NUEVO:** `finalizar_spool(tag_spool, worker_id, operacion, selected_unions)` - Auto-determina PAUSAR/COMPLETAR, batch update Uniones, libera spool
- Delegar a `UnionService.process_selection()` para escritura granular de uniones

---

### 4.3 SSE Endpoints - SIN CAMBIOS v4.0 **[MODIFICADO]**

**✅ DECISIÓN:** NO modificar endpoints SSE en v4.0

**Razón:**
- SSE es componente crítico con requirement < 10s latency
- v3.0 funciona correctamente (solo filtra por Ocupado_Por)
- Filtros adicionales (STATUS_NV, Status_Spool) agregan complejidad sin justificación clara
- Si dashboards necesitan filtros adicionales, implementar client-side

**Endpoints mantienen lógica v3.0:**
- `GET /api/sse/disponible?operacion=ARM` → Filtra solo por `Ocupado_Por IN ('', 'DISPONIBLE')`
- `GET /api/sse/quien-tiene-que` → Sin cambios

**Compatibilidad:** v3.0 y v4.0 usan mismos endpoints SSE (zero breaking changes)

---

## 5. Frontend Architecture

### 5.1 Componentes Modificados **[SIMPLIFICADO]**

**P3 - Tipo de Interacción** (`app/tipo-interaccion/page.tsx`):
- **ANTES:** 3 botones (TOMAR, PAUSAR, COMPLETAR)
- **DESPUÉS:** 2 botones (INICIAR, FINALIZAR)
- Descripción textual debajo de cada botón para claridad

**P4 - Seleccionar Spool** (modificado):
- Filtro dinámico según acción seleccionada en P3:
  - **INICIAR:** `STATUS_NV='ABIERTA' AND Status_Spool='EN_PROCESO' AND Ocupado_Por IN ('', 'DISPONIBLE')`
  - **FINALIZAR:** `Ocupado_Por LIKE '%(worker_id)%'` (sin filtros adicionales, muestra ARM y SOLD)
- Título dinámico según contexto
- NO multi-select en FINALIZAR (solo 1 spool)

**P5 - Nueva Pantalla (solo FINALIZAR):** Selección de Uniones
- Mostrar todas las uniones del spool seleccionado (backend filtra disponibles)
- Checkboxes con datos: N_UNION, DN_UNION, TIPO_UNION
- Contador en vivo: "Seleccionadas: 7/10 | Pulgadas: 18.5"
- Validación 0 uniones: Modal confirmación "¿Liberar sin registrar trabajo?"
- ❌ **NO incluir botón "➕ Agregar Unión"** (eliminado por S1)

**Context** (`lib/context.tsx`):
- Agregar `accion: 'INICIAR' | 'FINALIZAR'`, `setAccion()`
- Agregar `selectedUnions: number[]`, `setSelectedUnions()`
- Agregar `pulgadasCompletadas: number`, `setPulgadasCompletadas()`

**P6/P7 - Confirmación y Éxito**:
- Texto dinámico según acción (INICIAR vs FINALIZAR)
- Mostrar `pulgadasCompletadas` en FINALIZAR
- Llamada API dinámica: `api.iniciarSpool()` o `api.finalizarSpool()`

---

## 6. API Endpoints

### Nuevos (v4.0) **[SIMPLIFICADO]**

**Método** | **Path** | **Descripción** | **Response**
---|---|---|---
GET | `/api/uniones/{tag}/disponibles?operacion=ARM\|SOLD` | **Listar uniones PENDIENTES** (ver lógica abajo) | `Union[]`
GET | `/api/uniones/{tag}/metricas` | Métricas agregadas | `{total_uniones, arm_completadas, pulgadas_arm, ...}`

**GET /disponibles - Lógica de filtrado:**
```python
# operacion=ARM → Uniones pendientes de armar
WHERE ARM_FECHA_FIN IS NULL

# operacion=SOLD → Uniones armadas pero no soldadas
WHERE ARM_FECHA_FIN IS NOT NULL AND SOL_FECHA_FIN IS NULL
```

**Nota:** Frontend recibe solo uniones trabajables, simplifica UI (no necesita lógica filtrado).

---

### Modificados (v4.0)

**Método** | **Path** | **Cambio v3.0 → v4.0**
---|---|---
POST | `/api/occupation/iniciar` | **NUEVO** - Reemplaza `/tomar` en flujo v4.0. Body: `{tag_spool, worker_id, operacion}`. Solo ocupa spool (NO toca Uniones)
POST | `/api/occupation/finalizar` | **NUEVO** - Reemplaza `/pausar` y `/completar`. Body: `{tag_spool, worker_id, operacion, selected_unions: list[int]}`. Auto-determina PAUSAR/COMPLETAR según `len(selected_unions) == total`

**Compatibilidad v3.0**: Endpoints antiguos (`/tomar`, `/pausar`, `/completar`) siguen funcionando para flujo legacy

---

## 7. Performance Optimization

### 7.1 Batch API - Implementación (gspread A1 Notation)

**⚠️ IMPORTANTE:** gspread 6.0+ requiere A1 notation (NO índices row/col).

**SheetsService:**
```python
def batch_update(self, sheet_name: str, range_value_pairs: list[dict]) -> None:
    """
    Batch update con A1 notation de gspread.

    Args:
        range_value_pairs: [{"range": "H10", "values": [["MR(93)"]]}, ...]
    """
    worksheet = self.client.open_by_key(SHEET_ID).worksheet(sheet_name)
    worksheet.batch_update(range_value_pairs)

def batch_append_rows(self, sheet_name: str, rows: list[list]) -> None:
    """Append múltiples filas (1 API call)"""
    worksheet = self.client.open_by_key(SHEET_ID).worksheet(sheet_name)
    worksheet.append_rows(rows, value_input_option='USER_ENTERED')
```

**UnionRepository.batch_update_arm() - Ejemplo Real:**
```python
def batch_update_arm(
    self,
    tag_spool: str,
    n_unions: list[int],
    worker: str,
    fecha_inicio: datetime,
    fecha_fin: datetime
):
    """Actualiza ARM timestamps para múltiples uniones (1 API call)"""

    # 1. Obtener filas de las uniones
    uniones_rows = {n: self._get_row_index(tag_spool, n) for n in n_unions}

    # 2. Construir updates A1 notation
    updates = []
    for n, row_idx in uniones_rows.items():
        updates.extend([
            {"range": f"F{row_idx}", "values": [[format_datetime(fecha_inicio)]]},  # ARM_FECHA_INICIO (col 6)
            {"range": f"G{row_idx}", "values": [[format_datetime(fecha_fin)]]},     # ARM_FECHA_FIN (col 7)
            {"range": f"H{row_idx}", "values": [[worker]]},                         # ARM_WORKER (col 8)
            {"range": f"N{row_idx}", "values": [[str(uuid4())]]}                    # version (col 14)
        ])

    # 3. Batch update (1 API call para 4N updates)
    self.sheets_service.batch_update("Uniones", updates)
```

**Performance:**
- 10 uniones: 1 batch call con 40 updates (4 campos × 10 uniones)
- vs Sequential: 40 API calls × 300ms = 12 segundos
- Batch: 1 API call × 300ms = 0.3 segundos
- **Mejora: 40x**

**Performance Benchmark**:
```
Selección de 10 uniones:

❌ Sequential (VERSION-4.0 original):
  20 API calls × 300ms = 6 segundos

✅ Batch (v4.0 optimizado):
  2 API calls × 300ms = 0.6 segundos

Mejora: 10x
```

**Google Sheets Rate Limits**:
- Límite: 60 writes/min/user
- v4.0 batch: 2 writes por operación (vs 21 sequential)
- Capacidad: 30 operaciones/min (vs 3 con sequential)

---

### 7.2 Batch Metadata - Chunking para Google Sheets Limit

**Límite:** `append_rows()` max 1000 filas/request

**Escenario extremo:**
- Spool 20 uniones × 50 trabajadores = 1,050 eventos (excede límite)

**Implementación:**
```python
class MetadataRepository:
    CHUNK_SIZE = 900  # Safety margin

    def batch_log_events(self, eventos: list[dict]) -> None:
        """Log múltiples eventos con chunking automático"""
        for chunk in self._chunks(eventos, self.CHUNK_SIZE):
            rows = [self._evento_to_row(e) for e in chunk]
            self.sheets_service.batch_append_rows("Metadata", rows)

    def _chunks(self, lst: list, n: int):
        """Divide lista en chunks de tamaño n"""
        for i in range(0, len(lst), n):
            yield lst[i:i + n]

    def _evento_to_row(self, evento: dict) -> list:
        """Convierte evento dict a row de Metadata"""
        return [
            str(uuid4()),                          # ID
            evento["tipo"],                        # Tipo
            evento["tag_spool"],                   # TAG_SPOOL
            evento["worker"],                      # Worker
            format_datetime(now_chile()),          # Timestamp
            json.dumps(evento["metadata"]),        # Metadata JSON
            str(uuid4()),                          # version
            evento["worker"],                      # Creado_Por
            format_datetime(now_chile()),          # Fecha_Creacion
            format_datetime(now_chile()),          # Fecha_Modificacion
            evento.get("n_union", "")              # N_UNION (col 11, nullable)
        ]
```

**Trade-offs:**
- Spools típicos (1-10 uniones): 1 append_rows (11 eventos < 900 ✅)
- Spools grandes (20 uniones): 1 append_rows (21 eventos < 900 ✅)
- Extremo (50 workers × 20): 2 append_rows (1,050 eventos chunked en 900 + 150)

**Performance impact:** Despreciable (1-2 chunks máximo en casos extremos).

---

## 8. Migration Strategy

### 8.1 Scope y Convivencia v3.0/v4.0

**✅ DECISIÓN CRÍTICA:** v4.0 solo aplica a spools NUEVOS (post-deploy).

**Spools v3.0 (existentes antes de v4.0):**
- **Identificación:** `count_uniones(tag_spool) == 0` (hoja Uniones vacía)
- **Workflow:** TOMAR/PAUSAR/COMPLETAR (3 botones en P3)
- **Hoja Operaciones:** Armador/Soldador/Fecha_Armado/Fecha_Soldadura se siguen leyendo
- **Estado:** Read-only (no migración automática, evita riesgo)
- **Endpoints:** `/tomar`, `/pausar`, `/completar` siguen funcionando

**Spools v4.0 (nuevos post-deploy):**
- **Identificación:** `count_uniones(tag_spool) > 0` (hoja Uniones con registros)
- **Workflow:** INICIAR/FINALIZAR (2 botones en P3)
- **Hoja Uniones:** Fuente de verdad para timestamps ARM/SOLD
- **Hoja Operaciones:** Armador/Soldador quedan NULL (deprecated)
- **Endpoints:** `/iniciar`, `/finalizar` + `/uniones/*`

**Frontend Detection:**
```typescript
// lib/utils.ts
export async function getSpoolVersion(tagSpool: string): Promise<'v3' | 'v4'> {
  const count = await api.getUnionesCount(tagSpool)
  return count > 0 ? 'v4' : 'v3'
}

// app/tipo-interaccion/page.tsx
const version = await getSpoolVersion(tagSpool)

if (version === 'v4') {
  return <IniciarFinalizarUI />  // 2 botones
} else {
  return <TomarPausarCompletarUI />  // 3 botones
}
```

**Backend Compatibility:**
```python
# routers/occupation.py
@router.post("/tomar")  # v3.0 - Mantener
async def tomar_spool(...):
    # Lógica v3.0 sin cambios

@router.post("/iniciar")  # v4.0 - Nuevo
async def iniciar_spool(...):
    # Validar que spool tenga uniones
    if union_repo.count_total(tag_spool) == 0:
        raise ValidationError("Spool v3.0 no compatible con flujo INICIAR/FINALIZAR")
    # Lógica v4.0
```

**Ventajas:**
- ✅ Zero migration risk (no tocar datos existentes)
- ✅ Rollback instant (feature flag OFF)
- ✅ Gradual adoption (nuevos spools usan v4.0)
- ✅ Testing real en producción con spools nuevos

**Trade-offs:**
- ⚠️ Dos UX paralelas temporales (se unifica cuando v3.0 spools completen ciclo)
- ⚠️ Código dual en frontend (se depreca cuando v3.0 < 5% uso)

---

### 8.2 Pre-Deployment (Preparación)

**Paso** | **Acción** | **Rollback**
---|---|---
1 | Backup completo Google Sheets | Restaurar desde backup
2 | Crear hoja `Uniones` vacía (18 columnas) | Eliminar hoja
3 | **Ingeniería pre-carga uniones** (proceso externo) | Eliminar filas creadas
4 | Agregar columnas 68-72 a `Operaciones` | No afecta v3.0 (columnas nuevas ignoradas)
5 | Agregar columna 11 `N_UNION` a `Metadata` (al final) | No afecta v3.0 (valores NULL ignorados)

---

### 8.3 Deployment (Zero Downtime)

**Fase** | **Acción** | **Verificación**
---|---|---
1 | Deploy backend v4.0 a Railway | `curl /health` + v3.0 endpoints funcionan
2 | Deploy frontend v4.0 a Vercel | Detección automática v3/v4 por spool
3 | Testing con spool nuevo (v4.0 flow) | INICIAR/FINALIZAR funciona, uniones se registran
4 | Monitoreo Metadata | Eventos granulares escribiéndose correctamente

**Compatibilidad:** v3.0 y v4.0 coexisten. Frontend detecta versión por spool.

---

### 8.4 Rollback Plan

**Si falla v4.0:**
1. Revertir deploy backend/frontend (Git revert)
2. Validar v3.0 funciona (spools antiguos siguen operando)
3. Hoja Uniones queda como "reference data" (ignorada hasta próximo intento)
4. Spools v4.0 creados durante testing: Marcar como bloqueados manualmente

**Data Safety:** Rollback sin pérdida de datos (window: 7 días post-deploy)

---

## 9. Testing Strategy

### Backend Tests

**Estructura de archivos:**
```
tests/
├── unit/
│   ├── v4/
│   │   ├── test_union_repository.py
│   │   ├── test_union_service.py
│   │   ├── test_batch_operations.py
│   │   └── test_validation_arm_sold.py
│   └── v3/ (existente, no modificar)
│       ├── test_occupation_service.py
│       └── ...
├── integration/
│   ├── v4/
│   │   ├── test_iniciar_finalizar_flow.py
│   │   ├── test_sheets_uniones_crud.py
│   │   └── test_metadata_granular.py
│   └── v3/ (existente, no modificar)
└── e2e/
    ├── test_v4_complete_workflow.py (Playwright)
    └── test_v3_v4_coexistence.py
```

**Tests Clave - Unit:**

| Test | Descripción | Coverage Target |
|------|-------------|-----------------|
| `test_batch_update_arm_updates_multiple_unions()` | Valida A1 notation correcta (F, G, H, N columns) | UnionRepository |
| `test_calcular_pulgadas_sums_dn_union()` | Suma pulgadas con redondeo a 1 decimal | UnionService |
| `test_finalizar_sold_filters_only_armadas()` | GET /disponibles?operacion=SOLD retorna solo ARM_FECHA_FIN != NULL | UnionRepository |

**Tests Clave - Integration:**

| Test | Descripción | Validación |
|------|-------------|------------|
| `test_iniciar_finalizar_flow_complete()` | INICIAR → FINALIZAR 7/10 → Valida PAUSAR | Metadata tiene SPOOL_ARM_PAUSADO |
| `test_batch_update_performance_less_than_1_second()` | 10 uniones en < 1s | Benchmark con mock Sheets |
| `test_metadata_granular_events()` | 1 batch + N granulares escritos | 11 filas nuevas en Metadata |
| `test_v3_v4_spool_coexistence()` | Spool v3.0 usa /tomar, v4.0 usa /iniciar | Ambos flujos funcionan sin conflictos |

---

### Frontend Tests

**Estructura:**
```
zeues-frontend/
├── e2e/
│   ├── v4/
│   │   ├── iniciar-finalizar.spec.ts
│   │   └── seleccionar-uniones.spec.ts
│   └── v3/ (existente)
└── components/
    └── __tests__/
        (sin AgregarUnionModal - eliminado)
```

**Tests Clave - E2E (Playwright):**

| Test | Flujo | Validación |
|------|-------|------------|
| `test_p5_checkboxes_disabled_for_completed()` | ARM: Unión #3 ya armada → Checkbox disabled | Badge "✓ Armada" visible |
| `test_contador_pulgadas_updates_realtime()` | Seleccionar 7 uniones → Contador muestra "18.5" | State actualizado |
| `test_modal_confirmacion_cero_uniones()` | FINALIZAR sin seleccionar → Modal "¿Liberar?" | Evento SPOOL_CANCELADO |
| `test_v3_v4_detection_shows_correct_ui()` | Spool v3.0 → 3 botones, Spool v4.0 → 2 botones | getSpoolVersion() correcto |

**Coverage Target:** >80% para código v4.0 nuevo (excluye v3.0 legacy).

---

## 10. Acceptance Criteria

### Performance SLA **[ACLARADO]**

**Performance Target:**
- **Target (p95):** < 1s para operación con 10 uniones
- **Acceptable (p99):** < 2s
- **Failure (p50):** >= 2s (bloqueante)

### v4.0 exitoso si:

1. ✅ Performance: Operación con 10 uniones < 1s (p95)
2. ✅ Métricas: Dashboard muestra pulgadas-diámetro (no spools)
3. ✅ Workflow paralelo: ARM/SOLD intercalables sin bloqueos
4. ✅ Auditoría: Metadata registra N_UNION granular (nivel unión individual)
5. ✅ Compatibilidad: v3.0 sigue operando (zero breaking changes)
6. ✅ Rollback: < 5 min sin data loss

### v4.0 falla si:

1. ❌ Performance > 2s (p50)
2. ❌ Breaking changes que rompen v3.0
3. ❌ Data loss en rollback
4. ❌ Rate limit errors en producción
5. ❌ UX confuso (regresión)

---

## 11. Riesgos y Mitigación

**Riesgo** | **Probabilidad** | **Impacto** | **Mitigación**
---|---|---|---
Google Sheets rate limit en peak | Media | Alto | Batch writes + monitoreo + alertas
UX confuso con checkboxes | Media | Medio | Training + tooltips + UAT previa
Performance degradation 20+ uniones | Baja | Medio | Load testing previo + paginación si necesario
Hoja Uniones no pre-poblada | Baja | Alto | Validar con Ingeniería pre-deploy + script verificación

---

## 12. Success Metrics (KPIs)

### Negocio
- **Pulgadas-diámetro/día**: Métrica primaria (reemplaza spools/día)
- **Pulgadas-diámetro/trabajador**: Rendimiento individual
- **Tiempo promedio/unión**: Benchmark ARM vs SOLD

### Técnicas
- **Latencia p95**: < 1s para selección
- **Latencia p99**: < 2s (acceptable)
- **Error rate**: < 0.1%
- **Sheets API quota**: < 50% límite
- **Rollback incidents**: 0 en primer mes

---

## 13. Timeline

**Semana 1**: Backend (models, repos, services, batch optimization)
**Semana 2**: API + Frontend (router, componentes, páginas)
**Semana 3**: Testing + Deploy (E2E, performance, staging, production)

**Total: 8 días desarrollo** (ajustado por testing robusto)

---

## 14. UX INICIAR/FINALIZAR - Decisiones Técnicas Adicionales

### Filtros de Spool P4

**INICIAR (disponibles):**
```sql
STATUS_NV = 'ABIERTA'              -- Col H: Nota de Venta abierta
AND Status_Spool = 'EN_PROCESO'    -- Col I: Significa "disponible para trabajar" (nomenclatura contra-intuitiva)
AND Ocupado_Por IN ('', 'DISPONIBLE')  -- Col 64: No ocupado
```
**Importante:** NO filtrar por columna Estado (state machine) ni por operación

**FINALIZAR (ocupados):**
```sql
Ocupado_Por LIKE '%(worker_id)%'  -- Col 64: Ocupado por el trabajador
```
**Importante:** NO filtrar por STATUS_NV, Status_Spool, ni operación (mostrar ARM y SOLD juntos)

---

### Redis Locks **[CONFIRMADO]**

**Cambio crítico:** Locks SIN TTL (permanentes hasta FINALIZAR)

**Razón:** Procesos manufactureros duran 5-8 horas (TTL 1h de v3.0 inadecuado)

**Limpieza:** Lazy cleanup (Railway free tier compatible)

**Implementación:**
- Lazy cleanup ejecutado al hacer INICIAR (sin cron job)
- Reconciliación al startup: Recrear locks Redis desde Sheets.Ocupado_Por
- Cleanup locks > 24 horas sin coincidencia en Sheets

**Trade-offs:**
- ✅ Zero-cost (Railway free tier)
- ✅ Auto-reconciliación en restarts
- ⚠️ Cleanup irregular (solo cuando hay actividad INICIAR)

---

### Validaciones Multi-Spool

**Permitido:**
- ✅ Múltiples spools ocupados simultáneamente (sin límite)
- ✅ Re-iniciar spool parcialmente completado (puede reanudar trabajo)
- ✅ 0 uniones seleccionadas en FINALIZAR → Modal confirmación "¿Liberar sin registrar?"

---

### Escritura de Timestamps

**INICIAR:**
- `Fecha_Ocupacion = now()` → Columna 65 de Operaciones
- NO escribe en hoja Uniones

**FINALIZAR:**
- `ARM_FECHA_INICIO = Fecha_Ocupacion` (reutiliza timestamp del INICIAR previo)
- `ARM_FECHA_FIN = now()` (timestamp actual al confirmar)
- `Ocupado_Por = 'DISPONIBLE'` (SIEMPRE libera, sin importar si PAUSAR o COMPLETAR)

---

## 15. Decisiones Resueltas (Análisis Pre-Planificación)

### ✅ Simplificaciones Aplicadas

| # | Decisión | Justificación |
|---|----------|---------------|
| S1 | **Eliminar creación de uniones desde app** | Hoja Uniones pre-poblada por Ingeniería (proceso externo) |
| S2 | **Eliminar evento UNION_CREADA** | Sin creación de uniones, evento innecesario |
| S3 | **Rechazar cambios SSE endpoints** | Mantener estabilidad v3.0, cero breaking changes |

### ✅ Correcciones Aplicadas

| # | Decisión | Justificación |
|---|----------|---------------|
| C1 | **Trigger automático metrología (100% SOLD)** | Backend detecta 100% completado y actualiza Estado_Detalle |
| C2 | **Validación ARM→SOLD con parcialidad** | SOLD puede completarse parcialmente, filtro backend previene selección no-armadas |

### ✅ Aclaraciones

| # | Decisión | Justificación |
|---|----------|---------------|
| A1 | **Redis locks permanentes (sin TTL)** | Procesos duran 5-8 horas, TTL 1h inadecuado |
| A2 | **Performance SLA: < 1s target, < 2s acceptable** | Clarifica criterios exitoso/falla |

---

**Fin de especificación SIMPLIFICADA**

**Fecha última actualización:** 2026-01-30
**Estado:** ✅ Listo para planificación
**Próximo paso:** `/gsd:new-milestone v4.0-uniones` o `/gsd:plan-phase 1`

**Uso:** Contexto técnico simplificado para planificación de implementación (GSD, manual, etc.)

**Reducción complejidad:** ~20% menos código estimado vs spec original
