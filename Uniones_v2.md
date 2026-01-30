# Uniones v4.0 - Trazabilidad Granular de Spools

## Historial de Versiones

- **v1.0 (30 Ene 2026):** Documento inicial con validaciones ARM→SOLD obligatorias
- **v2.0 (30 Ene 2026):** Eliminación validación ARM→SOLD, workflows paralelos, agregar uniones desde app

---

## 📋 Resumen Ejecutivo

### Objetivo
Agregar trazabilidad granular a nivel de unión dentro de cada spool, permitiendo workflows paralelos y flexibles entre ARM y SOLD, con capacidad de agregar uniones faltantes desde la app.

### Cambios Clave v4.0
1. ✅ **ARM y SOLD pueden intercalarse** (no secuencial, no bloqueante)
2. ✅ **Trabajadores pueden agregar uniones desde la app** (no solo ingeniería)
3. ✅ **Sin validación ARM→SOLD** (soldador puede trabajar spool parcialmente armado)
4. ✅ **Auto-determinación de estado** basado en completitud de uniones
5. ✅ **N_UNION no consecutivo** (puede tener gaps, solo debe ser único por OT)

### Cambio en UX
- **v3.0:** TOMAR → (trabajar) → PAUSAR/COMPLETAR (botones explícitos)
- **v4.0:** TOMAR → (trabajar) → **Seleccionar/Agregar Uniones** → Auto-determina estado

### Filosofía de Trabajo
- ARM y SOLD pueden trabajarse en paralelo (no bloqueante)
- Los trabajadores pueden descubrir y agregar uniones faltantes durante el trabajo
- El sistema auto-determina el estado del spool según completitud de uniones
- Sin validaciones restrictivas (máxima flexibilidad para la planta)

---

## 1. Modelo de Datos: Hoja Uniones

### Nueva Hoja en Google Sheets: `Uniones`

| # | Columna | Tipo | Descripción | Validaciones |
|---|---------|------|-------------|--------------|
| 1 | `ID` | String | PK compuesta: `{OT}+{N_UNION}` | Único, formato: "OT123+1" |
| 2 | `OT` | String | FK a Operaciones.OT | Debe existir en Operaciones |
| 3 | `N_UNION` | Integer | Número único 1-20 | Único por OT, 1 ≤ N ≤ 20 |
| 4 | `DN_UNION` | Decimal | Diámetro nominal (pulgadas) | > 0 |
| 5 | `TIPO_UNION` | Enum | Tipo de unión | `BW` \| `SO` \| `FILL` \| `BR` |
| 6 | `ARM_FECHA_INICIO` | DateTime | Timestamp del TOMAR (ARM) | `DD-MM-YYYY HH:MM` |
| 7 | `ARM_FECHA_FIN` | DateTime | Timestamp de salida (ARM) | `DD-MM-YYYY HH:MM`, ≥ INICIO |
| 8 | `ARM_WORKER` | String | Trabajador que armó | Formato: `XY(id)`, ej: `MR(93)` |
| 9 | `SOL_FECHA_INICIO` | DateTime | Timestamp del TOMAR (SOLD) | `DD-MM-YYYY HH:MM` |
| 10 | `SOL_FECHA_FIN` | DateTime | Timestamp de salida (SOLD) | `DD-MM-YYYY HH:MM`, ≥ INICIO |
| 11 | `SOL_WORKER` | String | Trabajador que soldó | Formato: `XY(id)` |
| 12 | `NDT_UNION` | Enum | Tipo de prueba NDT | `NA` \| `PT` \| `MT` \| `RT` \| `UT` |
| 13 | `R_NDT_UNION` | Enum | Resultado de prueba | `Aprobado` \| `Rechazado` \| `NA` |
| 14 | `version` | UUID | Token para optimistic locking | UUID4 |
| 15 | `Creado_Por` | String | Usuario que creó la fila | Worker ID o "INGENIERIA" |
| 16 | `Fecha_Creacion` | DateTime | Timestamp creación | `DD-MM-YYYY HH:MM` |
| 17 | `Modificado_Por` | String | Último usuario que modificó | Worker ID |
| 18 | `Fecha_Modificacion` | DateTime | Timestamp última modificación | `DD-MM-YYYY HH:MM` |

### Restricciones de Integridad

| Restricción | Estado | Validación |
|-------------|--------|------------|
| N_UNION único por OT | ✅ Activa | Backend + Frontend tiempo real |
| N_UNION rango 1-20 | ✅ Activa | Frontend |
| DN_UNION > 0 | ✅ Activa | Frontend |
| ARM_FECHA_FIN ≥ ARM_FECHA_INICIO | ✅ Activa | Backend |
| SOL_FECHA_FIN ≥ SOL_FECHA_INICIO | ✅ Activa | Backend |
| NDT_UNION = NA → R_NDT_UNION = NA | ✅ Activa | Backend |
| ~~N_UNION consecutivo sin gaps~~ | ❌ ELIMINADA | - |
| ~~ARM antes de SOLD~~ | ❌ ELIMINADA | - |

### Notas Importantes
- **N_UNION puede tener gaps:** Un spool puede tener uniones 1,2,3,5,7,9 (válido)
- **Edición solo desde Sheets:** Correcciones de DN_UNION, TIPO_UNION solo desde Google Sheets
- **Creación desde app:** Trabajadores pueden crear nuevas uniones durante selección

---

## 2. Flujo de Trabajo v4.0

### 2.1 Escenario Real de Planta

```
[Ingeniería pre-carga 10 uniones]
    Uniones: 1, 2, 3, 4, 5, 6, 7, 8, 9, 10
    ↓
[Armador hace TOMAR ARM → selecciona 7 uniones]
    Selecciona: 1, 2, 3, 4, 5, 6, 7
    Estado: ARM 7/10, SOLD 0/10
    ↓
[Soldador hace TOMAR SOLD → selecciona 5 uniones]
    IMPORTANTE: Puede soldar uniones SIN validar que estén armadas
    Selecciona: 1, 2, 3, 4, 5
    Estado: ARM 7/10, SOLD 5/10
    ↓
[Armador regresa, TOMAR ARM → selecciona 3 uniones]
    Selecciona: 8, 9, 10
    Estado: ARM 10/10 ✅, SOLD 5/10
    ↓
[Soldador regresa, TOMAR SOLD → selecciona 5 uniones]
    Selecciona: 6, 7, 8, 9, 10
    Estado: ARM 10/10 ✅, SOLD 10/10 ✅
    ↓
[Metrología registra NDT]
    Todas las uniones tienen ARM+SOLD completo
    Registra pruebas por unión
    ↓
[Resultado]
    - Armador en Operaciones: Primer ARM_WORKER (del armador)
    - Soldador en Operaciones: Primer SOL_WORKER (del soldador)
    - Estado_Detalle: "SOLD Completado" → Listo para siguiente fase
```

---

### 2.2 Flujo ARM con Agregar Uniones

```
┌────────────────────────────────────────────────────────────────┐
│ FASE 1: TOMAR SPOOL                                            │
└────────────────────────────────────────────────────────────────┘

[P1-P3: Trabajador selecciona ARM y hace TOMAR]
    1. Usuario en P1 (Identificación): Escanea/ingresa worker ID
    2. Usuario en P2 (Operación): Selecciona "ARM"
    3. Usuario en P3 (Tipo Interacción): Solo "TOMAR" visible
    4. Usuario en P4 (Seleccionar Spool): Elige TAG_SPOOL

    Backend al confirmar TOMAR:
    - Crea lock Redis: spool:{TAG}:lock
    - Payload Redis:
      {
        worker_id: "93",
        worker_display: "MR(93)",
        timestamp_tomar: "2026-01-30T10:00:00",
        operacion: "ARM",
        version: "uuid4-token",
        ttl: 3600
      }
    - Actualiza Operaciones:
      * Ocupado_Por = "MR(93)"
      * Fecha_Ocupacion = "30-01-2026 10:00:00"
    - NO modifica Uniones aún

    Frontend navega a → P5 (Seleccionar Uniones)

┌────────────────────────────────────────────────────────────────┐
│ FASE 2: PANTALLA SELECCIONAR UNIONES                           │
└────────────────────────────────────────────────────────────────┘

[P5: Pantalla "Seleccionar Uniones Armadas"]

    Backend GET /api/uniones/{TAG}/disponibles?operacion=ARM
    - Consulta hoja Uniones: WHERE OT={TAG} AND ARM_FECHA_FIN IS NULL
    - Retorna lista de uniones pendientes

    Frontend muestra:
    ┌────────────────────────────────────────────────────────────┐
    │ Uniones del Spool OT-123                                   │
    │ Trabajador: MR(93) | Operación: ARM                        │
    ├────────────────────────────────────────────────────────────┤
    │ ☐ Unión #1 - 2.5" - BW                                     │
    │ ☐ Unión #2 - 3.0" - SO                                     │
    │ ☐ Unión #3 - 2.5" - FILL                                   │
    │ ☐ Unión #5 - 4.0" - BW                                     │
    │ ...                                                        │
    ├────────────────────────────────────────────────────────────┤
    │ [+ Agregar Unión Faltante]                                 │
    │                                                            │
    │ Seleccionadas: 0                                           │
    │ [Cancelar Operación]                                       │
    └────────────────────────────────────────────────────────────┘

┌────────────────────────────────────────────────────────────────┐
│ FASE 3: AGREGAR UNIÓN FALTANTE (OPCIONAL)                      │
└────────────────────────────────────────────────────────────────┘

[Usuario hace clic en "+ Agregar Unión Faltante"]

    Frontend abre modal:
    ┌────────────────────────────────────────────────────────────┐
    │ Agregar Unión Faltante                                     │
    ├────────────────────────────────────────────────────────────┤
    │ Número de Unión:    [11]  ← auto-sugerido (max + 1)       │
    │ Diámetro (pulgadas): [___]                                 │
    │ Tipo de Unión:      [BW ▼]                                 │
    │                                                            │
    │ [Cancelar]  [Agregar]                                      │
    └────────────────────────────────────────────────────────────┘

    Validaciones frontend en tiempo real:
    1. Al cambiar N_UNION:
       → POST /api/uniones/validate {ot, n_union}
       → Si duplicado: Muestra error "Ya existe"
       → Si válido: Habilita botón Agregar

    2. Al hacer clic en "Agregar":
       → POST /api/uniones/crear
       {
         ot: "OT-123",
         n_union: 11,
         dn_union: 2.5,
         tipo_union: "BW"
       }

    Backend al crear unión:
    1. Valida N_UNION único:
       → SELECT COUNT(*) FROM Uniones WHERE OT={OT} AND N_UNION={N}
       → Si existe: Error 400 "N_UNION duplicado"

    2. Crea nueva fila en hoja Uniones:
       ID: "OT-123+11"
       OT: "OT-123"
       N_UNION: 11
       DN_UNION: 2.5
       TIPO_UNION: "BW"
       ARM_FECHA_INICIO: NULL  ← Pendiente
       ARM_FECHA_FIN: NULL
       ARM_WORKER: NULL
       SOL_FECHA_INICIO: NULL
       SOL_FECHA_FIN: NULL
       SOL_WORKER: NULL
       NDT_UNION: "NA"
       R_NDT_UNION: "NA"
       version: "uuid4"
       Creado_Por: "MR(93)"
       Fecha_Creacion: "30-01-2026 10:15:00"
       Modificado_Por: "MR(93)"
       Fecha_Modificacion: "30-01-2026 10:15:00"

    3. Loguea en Metadata:
       Tipo: UNION_CREADA
       OT: "OT-123"
       Worker: "MR(93)"
       Metadata: {"n_union": 11, "tipo": "BW", "dn": 2.5}

    4. Retorna nueva unión al frontend

    Frontend:
    - Cierra modal
    - Agrega nueva unión a la lista
    - Auto-selecciona la nueva unión (checkbox marcado)

┌────────────────────────────────────────────────────────────────┐
│ FASE 4: SELECCIÓN Y CONFIRMACIÓN                               │
└────────────────────────────────────────────────────────────────┘

[Usuario selecciona checkboxes de uniones trabajadas]

    Estado UI dinámico:
    - 0 seleccionadas → Botón: "Cancelar Operación"
    - 1-9 seleccionadas → Botón: "Confirmar (7 uniones)"
    - 10/10 seleccionadas → Botón: "Confirmar (10 uniones)"

[Usuario hace clic en "Confirmar"]

    Frontend → POST /api/occupation/confirmar-seleccion
    {
      ot: "OT-123",
      operacion: "ARM",
      selected_unions: [1, 2, 3, 4, 5, 6, 7]  // N_UNION
    }

    Backend proceso:

    1. Lee timestamp_tomar de Redis:
       lock_data = redis.get("spool:OT-123:lock")
       timestamp_tomar = lock_data["timestamp_tomar"]  // "2026-01-30T10:00:00"
       worker_id = lock_data["worker_id"]              // "93"

    2. Determina acción:
       total_uniones = COUNT(*) FROM Uniones WHERE OT="OT-123"  // 11
       seleccionadas = len([1,2,3,4,5,6,7])                    // 7

       if seleccionadas == 0:
           accion = "CANCELAR"
       elif seleccionadas == total_uniones:
           accion = "COMPLETAR"
       else:
           accion = "PAUSAR"

       // En este caso: PAUSAR (7/11)

    3. Escribe Uniones (batch update):
       Para cada N_UNION en [1,2,3,4,5,6,7]:
         UPDATE Uniones SET
           ARM_FECHA_INICIO = "30-01-2026 10:00:00"  ← timestamp_tomar
           ARM_FECHA_FIN = "30-01-2026 12:30:00"     ← now_chile()
           ARM_WORKER = "MR(93)"
           Modificado_Por = "MR(93)"
           Fecha_Modificacion = "30-01-2026 12:30:00"
         WHERE OT="OT-123" AND N_UNION IN (1,2,3,4,5,6,7)

    4. Calcula progreso:
       completadas_arm = COUNT(*) WHERE OT="OT-123" AND ARM_FECHA_FIN IS NOT NULL  // 7
       progreso_arm = "7/11"

    5. Actualiza Operaciones:
       UPDATE Operaciones SET
         Total_Uniones = 11
         Uniones_ARM_Completadas = "7/11"
         Estado_Detalle = "ARM Parcial (7/11)"
         Ocupado_Por = NULL              ← Libera
         Fecha_Ocupacion = NULL
       WHERE OT="OT-123"

       // NO actualiza Armador aún (solo cuando 11/11)

    6. Loguea en Metadata:
       Tipo: SPOOL_ARM_PAUSADO
       OT: "OT-123"
       Worker: "MR(93)"
       Metadata: {
         "uniones_completadas": 7,
         "total": 11,
         "uniones_trabajadas": [1,2,3,4,5,6,7]
       }

    7. Libera lock Redis:
       redis.delete("spool:OT-123:lock")

    8. Retorna al frontend:
       {
         "accion": "PAUSAR",
         "progreso": "7/11",
         "uniones_procesadas": 7
       }

[P6: Pantalla de Éxito]
    Muestra:
    "Uniones armadas: 7/11
     El spool permanece disponible para continuar"

    Redirige a P1 después de 5 segundos
```

---

### 2.3 Flujo SOLD (Sin Validación de ARM)

```
┌────────────────────────────────────────────────────────────────┐
│ FLUJO SOLD - SIN RESTRICCIONES ARM                             │
└────────────────────────────────────────────────────────────────┘

[P1-P3: Soldador hace TOMAR SOLD]
    1. Identificación: Worker ID "45"
    2. Operación: SOLD
    3. Tipo Interacción: TOMAR
    4. Seleccionar Spool: "OT-123"

    Backend:
    - NO valida que ARM esté completo ✅
    - Crea lock normalmente
    - Redis payload: {worker_id: "45", operacion: "SOLD", ...}

[P5: Pantalla "Seleccionar Uniones Soldadas"]

    Backend GET /api/uniones/{TAG}/disponibles?operacion=SOLD
    - Consulta: WHERE OT={TAG} AND SOL_FECHA_FIN IS NULL
    - NO filtra por ARM_FECHA_FIN ✅
    - Retorna TODAS las uniones sin SOL_FECHA_FIN

    Frontend muestra:
    ┌────────────────────────────────────────────────────────────┐
    │ Uniones del Spool OT-123                                   │
    │ Trabajador: JD(45) | Operación: SOLD                       │
    ├────────────────────────────────────────────────────────────┤
    │ ☐ Unión #1 - 2.5" - BW    ✓ Armada                        │
    │ ☐ Unión #2 - 3.0" - SO    ✓ Armada                        │
    │ ☐ Unión #3 - 2.5" - FILL  ✓ Armada                        │
    │ ☐ Unión #8 - 4.0" - BW    ⚠ Sin armar                     │
    │ ☐ Unión #9 - 2.5" - SO    ⚠ Sin armar                     │
    │ ...                                                        │
    ├────────────────────────────────────────────────────────────┤
    │ [+ Agregar Unión Faltante]                                 │
    │                                                            │
    │ Seleccionadas: 5                                           │
    │ [Confirmar (5 uniones)]                                    │
    └────────────────────────────────────────────────────────────┘

    Indicadores visuales:
    - ✓ Armada: ARM_FECHA_FIN != NULL (verde)
    - ⚠ Sin armar: ARM_FECHA_FIN = NULL (amarillo)

    IMPORTANTE: El usuario PUEDE seleccionar uniones sin armar

[Usuario selecciona 5 uniones y confirma]
    Selecciona: [1, 2, 3, 4, 5] (3 armadas, 2 sin armar)

    Backend proceso:
    1. Lee timestamp_tomar de Redis
    2. Escribe SOL_FECHA_INICIO, SOL_FECHA_FIN, SOL_WORKER
    3. Calcula progreso:
       completadas_sold = 5
       total = 11
       progreso_sold = "5/11"
    4. Actualiza Operaciones:
       Uniones_SOLD_Completadas = "5/11"
       Estado_Detalle = "En Progreso (ARM 7/11, SOLD 5/11)"
    5. Loguea: SPOOL_SOLD_PAUSADO
    6. Libera lock

[Resultado]
    Estado del spool:
    - ARM: 7/11
    - SOLD: 5/11
    - Uniones con SOL pero sin ARM: #4, #5 (válido ✅)
```

---

### 2.4 Flujo NDT (Metrología)

```
[Metrología - Acceso Instantáneo (SIN TOMAR)]

    - NO requiere lock Redis
    - Similar a inspección instantánea v3.0
    - Solo rol METROLOGIA puede acceder

[Pantalla "Registrar Pruebas NDT"]

    Backend GET /api/uniones/{TAG}/soldadas
    - Consulta: WHERE OT={TAG} AND SOL_FECHA_FIN IS NOT NULL
    - Retorna solo uniones con soldadura completa

    Frontend muestra formulario:
    ┌────────────────────────────────────────────────────────────┐
    │ Registro NDT - Spool OT-123                                │
    │ Inspector: PT(12)                                          │
    ├────────────────────────────────────────────────────────────┤
    │ Unión #1 - 2.5" - BW                                       │
    │   Tipo Prueba: [RT ▼] NA, PT, MT, RT, UT                  │
    │   Resultado:   [Aprobado ▼] NA, Aprobado, Rechazado       │
    │                                                            │
    │ Unión #2 - 3.0" - SO                                       │
    │   Tipo Prueba: [PT ▼]                                      │
    │   Resultado:   [Aprobado ▼]                                │
    │                                                            │
    │ Unión #3 - 2.5" - FILL                                     │
    │   Tipo Prueba: [NA ▼]                                      │
    │   Resultado:   [NA ▼]                                      │
    │ ...                                                        │
    ├────────────────────────────────────────────────────────────┤
    │ [Cancelar]  [Registrar Resultados]                         │
    └────────────────────────────────────────────────────────────┘

[Usuario registra resultados y confirma]

    Frontend → POST /api/metrologia/ndt
    {
      ot: "OT-123",
      worker_id: "12",
      resultados: [
        {n_union: 1, ndt_tipo: "RT", resultado: "Aprobado"},
        {n_union: 2, ndt_tipo: "PT", resultado: "Aprobado"},
        {n_union: 3, ndt_tipo: "NA", resultado: "NA"},
        {n_union: 5, ndt_tipo: "RT", resultado: "Rechazado"}  ← RECHAZO
      ]
    }

    Backend proceso:

    1. Actualiza hoja Uniones (batch):
       Para cada resultado:
         UPDATE Uniones SET
           NDT_UNION = resultado.ndt_tipo
           R_NDT_UNION = resultado.resultado
           Modificado_Por = "PT(12)"
           Fecha_Modificacion = now_chile()
         WHERE OT="OT-123" AND N_UNION=resultado.n_union

    2. Verifica rechazos:
       rechazos = [r for r in resultados if r.resultado == "Rechazado"]

       if len(rechazos) > 0:
           # Activa flujo de reparación
           UPDATE Operaciones SET
             Estado_Detalle = "REPARACION"
           WHERE OT="OT-123"

           # Loguea evento
           Metadata.insert({
             tipo: "SPOOL_NDT_RECHAZADO",
             ot: "OT-123",
             worker: "PT(12)",
             metadata: {
               "union_rechazada": 5,
               "ndt_tipo": "RT",
               "total_rechazos": 1
             }
           })

           # Aplica lógica v3.0 de reparación (bounded cycles, max 3)

       else:
           # Todas aprobadas o NA
           UPDATE Operaciones SET
             Estado_Detalle = "Aprobado"
           WHERE OT="OT-123"

           Metadata.insert({
             tipo: "SPOOL_NDT_APROBADO",
             ot: "OT-123",
             worker: "PT(12)",
             metadata: {"uniones_probadas": 11}
           })

    3. Retorna resultado

[Resultado]
    Si rechazado:
    - Spool entra en REPARACION
    - Se aplica flujo bounded cycles v3.0
    - Después de reparación, puede volver a tomar ARM/SOLD
```

---

## 3. Lógica de Auto-Determinación de Estado

### 3.1 Algoritmo de Cálculo de Estado

```python
def calculate_spool_status(ot: str) -> dict:
    """
    Calcula el estado del spool basado en completitud de uniones.
    No usa botones PAUSAR/COMPLETAR, se determina automáticamente.
    """
    # Contar uniones
    total = count_total_unions(ot)
    arm_completed = count_unions_with_arm_fin(ot)
    sold_completed = count_unions_with_sold_fin(ot)

    # Progreso
    arm_progress = f"{arm_completed}/{total}"
    sold_progress = f"{sold_completed}/{total}"

    # Determinación de estado
    if arm_completed == total and sold_completed == total:
        estado = "SOLD_COMPLETADO"
        detalle = "SOLD Completado"

    elif arm_completed == total and sold_completed < total:
        estado = "ARM_COMPLETADO"
        detalle = "ARM Completado"

    elif sold_completed == total and arm_completed < total:
        estado = "SOLD_COMPLETADO_SIN_ARM"  # Edge case
        detalle = f"SOLD Completado (ARM pendiente {arm_progress})"

    elif arm_completed > 0 or sold_completed > 0:
        estado = "EN_PROGRESO"
        detalle = f"En Progreso (ARM {arm_progress}, SOLD {sold_progress})"

    else:
        estado = "DISPONIBLE"
        detalle = "Disponible"

    return {
        "estado": estado,
        "estado_detalle": detalle,
        "arm_progress": arm_progress,
        "sold_progress": sold_progress,
        "total_uniones": total
    }
```

### 3.2 Actualización de Columnas en Operaciones

```python
def update_operaciones_after_selection(ot: str, operacion: str):
    """
    Actualiza hoja Operaciones después de selección de uniones.
    """
    # Calcular estado
    status = calculate_spool_status(ot)

    # Preparar updates
    updates = {
        "Total_Uniones": status["total_uniones"],
        "Uniones_ARM_Completadas": status["arm_progress"],
        "Uniones_SOLD_Completadas": status["sold_progress"],
        "Estado_Detalle": status["estado_detalle"],
        "Ocupado_Por": None,  # Liberar
        "Fecha_Ocupacion": None
    }

    # Actualizar Armador/Soldador solo si completo
    if status["estado"] in ["ARM_COMPLETADO", "SOLD_COMPLETADO"]:
        if operacion == "ARM":
            primer_arm_worker = get_first_arm_worker(ot)
            updates["Armador"] = primer_arm_worker
            updates["Fecha_Armado"] = get_latest_arm_fecha_fin(ot)

        elif operacion == "SOLD":
            primer_sol_worker = get_first_sol_worker(ot)
            updates["Soldador"] = primer_sol_worker
            updates["Fecha_Soldadura"] = get_latest_sol_fecha_fin(ot)

    # Escribir a Sheets
    operaciones_repo.update(ot, updates)
```

---

## 4. Backend (FastAPI)

### 4.1 Nuevo Router: `/api/uniones`

**Archivo:** `backend/routers/uniones.py`

```python
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import Literal

router = APIRouter(prefix="/api/uniones", tags=["uniones"])

# ============================================================
# DTOs
# ============================================================

class CrearUnionRequest(BaseModel):
    ot: str
    n_union: int
    dn_union: float
    tipo_union: Literal["BW", "SO", "FILL", "BR"]

class ValidateNUnionRequest(BaseModel):
    ot: str
    n_union: int

class UnionDisplay(BaseModel):
    n_union: int
    dn_union: float
    tipo_union: str
    tiene_arm: bool = False  # Solo para operacion=SOLD
    tiene_sold: bool = False

# ============================================================
# Endpoints
# ============================================================

@router.post("/crear")
async def crear_union(
    request: CrearUnionRequest,
    worker_id: str = Depends(get_worker_from_context)
):
    """
    Crea una nueva unión durante el proceso de selección.

    Validaciones:
    - N_UNION no duplicado (único por OT)
    - N_UNION en rango 1-20
    - DN_UNION > 0

    Respuesta:
    - 200: Union creada exitosamente
    - 400: N_UNION duplicado
    - 400: Validación fallida
    """
    try:
        service = UnionService()
        nueva_union = service.crear_union(
            ot=request.ot,
            n_union=request.n_union,
            dn_union=request.dn_union,
            tipo_union=request.tipo_union,
            creado_por=worker_id
        )
        return nueva_union
    except UnionDuplicadaError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except ValidationError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/validate")
async def validate_n_union(request: ValidateNUnionRequest):
    """
    Validación en tiempo real de N_UNION.

    Usado por frontend para mostrar error antes de submit.

    Respuesta:
    - 200: N_UNION disponible
    - 409: N_UNION duplicado
    """
    repo = UnionRepository()
    existing = repo.get_union(request.ot, request.n_union)

    if existing:
        raise HTTPException(
            status_code=409,
            detail=f"Unión #{request.n_union} ya existe en {request.ot}"
        )

    return {"valid": True}


@router.get("/{ot}/disponibles")
async def get_uniones_disponibles(
    ot: str,
    operacion: Literal["ARM", "SOLD"]
) -> list[UnionDisplay]:
    """
    Retorna uniones disponibles para selección.

    ARM: Uniones con ARM_FECHA_FIN = NULL
    SOLD: Uniones con SOL_FECHA_FIN = NULL (NO valida ARM)

    Para SOLD, incluye flag 'tiene_arm' para indicador visual.
    """
    service = UnionService()
    uniones = service.get_disponibles(ot, operacion)

    # Mapear a DTO
    result = []
    for u in uniones:
        result.append(UnionDisplay(
            n_union=u.n_union,
            dn_union=u.dn_union,
            tipo_union=u.tipo_union,
            tiene_arm=(u.arm_fecha_fin is not None),
            tiene_sold=(u.sol_fecha_fin is not None)
        ))

    return result


@router.get("/{ot}/sugerir-n-union")
async def sugerir_n_union(ot: str) -> dict:
    """
    Auto-sugiere el siguiente N_UNION disponible.

    Lógica: max(N_UNION) + 1

    Retorna: {"suggested": 11}
    """
    repo = UnionRepository()
    max_n = repo.get_max_n_union(ot) or 0
    return {"suggested": max_n + 1}


@router.get("/{ot}/soldadas")
async def get_uniones_soldadas(ot: str) -> list[UnionDisplay]:
    """
    Retorna uniones con SOL_FECHA_FIN != NULL.

    Usado por pantalla de registro NDT (metrología).
    """
    repo = UnionRepository()
    uniones = repo.get_by_filter(
        ot=ot,
        has_sol_fecha_fin=True
    )

    return [
        UnionDisplay(
            n_union=u.n_union,
            dn_union=u.dn_union,
            tipo_union=u.tipo_union
        )
        for u in uniones
    ]
```

---

### 4.2 UnionService

**Archivo:** `backend/services/union_service.py`

```python
from datetime import datetime
from uuid import uuid4
from backend.repositories.union_repository import UnionRepository
from backend.repositories.metadata_repository import MetadataRepository
from backend.utils.date_formatter import now_chile
from backend.exceptions import UnionDuplicadaError, ValidationError

class UnionService:
    def __init__(self):
        self.repo = UnionRepository()
        self.metadata_repo = MetadataRepository()

    def crear_union(
        self,
        ot: str,
        n_union: int,
        dn_union: float,
        tipo_union: str,
        creado_por: str
    ) -> Union:
        """
        Crea una nueva unión en la hoja Uniones.

        Validaciones:
        - N_UNION único por OT
        - N_UNION en rango 1-20
        - DN_UNION > 0
        """
        # Validación duplicado
        if self.repo.exists(ot, n_union):
            raise UnionDuplicadaError(
                f"Unión #{n_union} ya existe en {ot}"
            )

        # Validación rango
        if n_union < 1 or n_union > 20:
            raise ValidationError(
                f"N_UNION debe estar entre 1 y 20 (recibido: {n_union})"
            )

        # Validación DN
        if dn_union <= 0:
            raise ValidationError(
                f"DN_UNION debe ser mayor a 0 (recibido: {dn_union})"
            )

        # Crear nueva unión
        timestamp = now_chile()
        nueva = Union(
            id=f"{ot}+{n_union}",
            ot=ot,
            n_union=n_union,
            dn_union=dn_union,
            tipo_union=tipo_union,
            # Fechas vacías (pendiente)
            arm_fecha_inicio=None,
            arm_fecha_fin=None,
            arm_worker=None,
            sol_fecha_inicio=None,
            sol_fecha_fin=None,
            sol_worker=None,
            ndt_union="NA",
            r_ndt_union="NA",
            # Auditoría
            version=str(uuid4()),
            creado_por=creado_por,
            fecha_creacion=timestamp,
            modificado_por=creado_por,
            fecha_modificacion=timestamp
        )

        # Escribir a Sheets
        self.repo.create(nueva)

        # Loguear evento
        self.metadata_repo.log_event(
            tipo="UNION_CREADA",
            ot=ot,
            worker=creado_por,
            metadata={
                "n_union": n_union,
                "tipo": tipo_union,
                "dn": dn_union
            }
        )

        return nueva

    def get_disponibles(
        self,
        ot: str,
        operacion: str
    ) -> list[Union]:
        """
        Retorna uniones disponibles para selección.

        ARM: Uniones sin ARM_FECHA_FIN
        SOLD: Uniones sin SOL_FECHA_FIN (NO valida ARM)
        """
        if operacion == "ARM":
            return self.repo.get_by_filter(
                ot=ot,
                arm_fecha_fin=None
            )
        elif operacion == "SOLD":
            return self.repo.get_by_filter(
                ot=ot,
                sol_fecha_fin=None
            )
        else:
            raise ValueError(f"Operación inválida: {operacion}")

    def process_selection(
        self,
        ot: str,
        operacion: str,
        selected_unions: list[int],  # N_UNION
        timestamp_tomar: datetime,
        worker_id: str,
        worker_display: str
    ) -> dict:
        """
        Procesa la selección de uniones en salida.

        Retorna:
        {
          "accion": "PAUSAR" | "COMPLETAR" | "CANCELAR",
          "progreso": "7/11",
          "uniones_procesadas": 7
        }
        """
        # Validación
        if operacion not in ["ARM", "SOLD"]:
            raise ValueError(f"Operación inválida: {operacion}")

        # Caso: Cancelar (0 seleccionadas)
        if len(selected_unions) == 0:
            # Loguear evento
            self.metadata_repo.log_event(
                tipo="SPOOL_CANCELADO",
                ot=ot,
                worker=worker_display,
                metadata={
                    "operacion": operacion,
                    "motivo": "sin_seleccion"
                }
            )
            return {
                "accion": "CANCELAR",
                "progreso": "0/0",
                "uniones_procesadas": 0
            }

        # Actualizar uniones seleccionadas
        timestamp_fin = now_chile()

        if operacion == "ARM":
            self.repo.batch_update_arm(
                ot=ot,
                n_unions=selected_unions,
                fecha_inicio=timestamp_tomar,
                fecha_fin=timestamp_fin,
                worker=worker_display
            )
        elif operacion == "SOLD":
            self.repo.batch_update_sold(
                ot=ot,
                n_unions=selected_unions,
                fecha_inicio=timestamp_tomar,
                fecha_fin=timestamp_fin,
                worker=worker_display
            )

        # Calcular progreso
        total = self.repo.count_total(ot)
        completadas = (
            self.repo.count_completed_arm(ot)
            if operacion == "ARM"
            else self.repo.count_completed_sold(ot)
        )
        progreso = f"{completadas}/{total}"

        # Determinar acción
        if completadas == total:
            accion = "COMPLETAR"
            evento = f"SPOOL_{operacion}_COMPLETADO"
        else:
            accion = "PAUSAR"
            evento = f"SPOOL_{operacion}_PAUSADO"

        # Loguear evento
        self.metadata_repo.log_event(
            tipo=evento,
            ot=ot,
            worker=worker_display,
            metadata={
                "uniones_completadas": completadas,
                "total": total,
                "uniones_trabajadas": selected_unions
            }
        )

        return {
            "accion": accion,
            "progreso": progreso,
            "uniones_procesadas": len(selected_unions)
        }
```

---

### 4.3 UnionRepository

**Archivo:** `backend/repositories/union_repository.py`

```python
from typing import Optional
from backend.models.union import Union

class UnionRepository:
    def __init__(self):
        self.sheets_service = SheetsService()
        self.sheet_name = "Uniones"

    def create(self, union: Union) -> None:
        """Crea una nueva fila en hoja Uniones"""
        row = [
            union.id,
            union.ot,
            union.n_union,
            union.dn_union,
            union.tipo_union,
            union.arm_fecha_inicio or "",
            union.arm_fecha_fin or "",
            union.arm_worker or "",
            union.sol_fecha_inicio or "",
            union.sol_fecha_fin or "",
            union.sol_worker or "",
            union.ndt_union,
            union.r_ndt_union,
            union.version,
            union.creado_por,
            format_datetime_for_sheets(union.fecha_creacion),
            union.modificado_por or "",
            format_datetime_for_sheets(union.fecha_modificacion) if union.fecha_modificacion else ""
        ]
        self.sheets_service.append_row(self.sheet_name, row)

    def exists(self, ot: str, n_union: int) -> bool:
        """Verifica si existe una unión con ese OT y N_UNION"""
        union = self.get_union(ot, n_union)
        return union is not None

    def get_union(self, ot: str, n_union: int) -> Optional[Union]:
        """Obtiene una unión por OT y N_UNION"""
        all_data = self.sheets_service.read_all(self.sheet_name)
        headers = all_data[0]

        ot_idx = headers.index("OT")
        n_union_idx = headers.index("N_UNION")

        for row in all_data[1:]:
            if row[ot_idx] == ot and int(row[n_union_idx]) == n_union:
                return self._row_to_union(row, headers)

        return None

    def get_max_n_union(self, ot: str) -> Optional[int]:
        """Retorna el N_UNION más alto para un OT"""
        all_data = self.sheets_service.read_all(self.sheet_name)
        headers = all_data[0]

        ot_idx = headers.index("OT")
        n_union_idx = headers.index("N_UNION")

        max_n = None
        for row in all_data[1:]:
            if row[ot_idx] == ot:
                n = int(row[n_union_idx])
                if max_n is None or n > max_n:
                    max_n = n

        return max_n

    def get_by_filter(
        self,
        ot: str,
        arm_fecha_fin: Optional[str] = "ANY",
        sol_fecha_fin: Optional[str] = "ANY",
        has_sol_fecha_fin: bool = False
    ) -> list[Union]:
        """
        Obtiene uniones por OT con filtros opcionales.

        arm_fecha_fin=None: Solo sin ARM_FECHA_FIN
        sol_fecha_fin=None: Solo sin SOL_FECHA_FIN
        has_sol_fecha_fin=True: Solo con SOL_FECHA_FIN
        """
        all_data = self.sheets_service.read_all(self.sheet_name)
        headers = all_data[0]

        ot_idx = headers.index("OT")
        arm_fin_idx = headers.index("ARM_FECHA_FIN")
        sol_fin_idx = headers.index("SOL_FECHA_FIN")

        result = []
        for row in all_data[1:]:
            if row[ot_idx] != ot:
                continue

            # Filtro ARM_FECHA_FIN
            if arm_fecha_fin is not None and arm_fecha_fin != "ANY":
                if arm_fecha_fin is None and row[arm_fin_idx]:
                    continue

            # Filtro SOL_FECHA_FIN
            if sol_fecha_fin is not None and sol_fecha_fin != "ANY":
                if sol_fecha_fin is None and row[sol_fin_idx]:
                    continue

            # Filtro has_sol_fecha_fin
            if has_sol_fecha_fin:
                if not row[sol_fin_idx]:
                    continue

            result.append(self._row_to_union(row, headers))

        return result

    def batch_update_arm(
        self,
        ot: str,
        n_unions: list[int],
        fecha_inicio: datetime,
        fecha_fin: datetime,
        worker: str
    ) -> None:
        """Actualiza ARM_FECHA_* y ARM_WORKER en batch"""
        all_data = self.sheets_service.read_all(self.sheet_name)
        headers = all_data[0]

        ot_idx = headers.index("OT")
        n_union_idx = headers.index("N_UNION")
        arm_inicio_idx = headers.index("ARM_FECHA_INICIO")
        arm_fin_idx = headers.index("ARM_FECHA_FIN")
        arm_worker_idx = headers.index("ARM_WORKER")
        mod_por_idx = headers.index("Modificado_Por")
        mod_fecha_idx = headers.index("Fecha_Modificacion")

        updates = []
        for i, row in enumerate(all_data[1:], start=2):  # Row 2 = primera data
            if row[ot_idx] == ot and int(row[n_union_idx]) in n_unions:
                updates.append({
                    "row": i,
                    "col": arm_inicio_idx,
                    "value": format_datetime_for_sheets(fecha_inicio)
                })
                updates.append({
                    "row": i,
                    "col": arm_fin_idx,
                    "value": format_datetime_for_sheets(fecha_fin)
                })
                updates.append({
                    "row": i,
                    "col": arm_worker_idx,
                    "value": worker
                })
                updates.append({
                    "row": i,
                    "col": mod_por_idx,
                    "value": worker
                })
                updates.append({
                    "row": i,
                    "col": mod_fecha_idx,
                    "value": format_datetime_for_sheets(now_chile())
                })

        self.sheets_service.batch_update(self.sheet_name, updates)

    def batch_update_sold(
        self,
        ot: str,
        n_unions: list[int],
        fecha_inicio: datetime,
        fecha_fin: datetime,
        worker: str
    ) -> None:
        """Actualiza SOL_FECHA_* y SOL_WORKER en batch"""
        # Similar a batch_update_arm pero con columnas SOL_*
        pass

    def count_total(self, ot: str) -> int:
        """Cuenta total de uniones de un OT"""
        all_data = self.sheets_service.read_all(self.sheet_name)
        headers = all_data[0]
        ot_idx = headers.index("OT")

        return sum(1 for row in all_data[1:] if row[ot_idx] == ot)

    def count_completed_arm(self, ot: str) -> int:
        """Cuenta uniones con ARM_FECHA_FIN"""
        all_data = self.sheets_service.read_all(self.sheet_name)
        headers = all_data[0]

        ot_idx = headers.index("OT")
        arm_fin_idx = headers.index("ARM_FECHA_FIN")

        return sum(
            1 for row in all_data[1:]
            if row[ot_idx] == ot and row[arm_fin_idx]
        )

    def count_completed_sold(self, ot: str) -> int:
        """Cuenta uniones con SOL_FECHA_FIN"""
        all_data = self.sheets_service.read_all(self.sheet_name)
        headers = all_data[0]

        ot_idx = headers.index("OT")
        sol_fin_idx = headers.index("SOL_FECHA_FIN")

        return sum(
            1 for row in all_data[1:]
            if row[ot_idx] == ot and row[sol_fin_idx]
        )
```

---

## 5. Frontend (Next.js)

### 5.1 Componente: AgregarUnionModal

**Archivo:** `components/AgregarUnionModal.tsx`

```typescript
import { useState, useEffect } from 'react';
import { Button } from '@/components/Button';
import { Input } from '@/components/Input';
import { Select } from '@/components/Select';

interface AgregarUnionModalProps {
  ot: string;
  onUnionCreada: (union: Union) => void;
  onClose: () => void;
}

interface Union {
  n_union: number;
  dn_union: number;
  tipo_union: 'BW' | 'SO' | 'FILL' | 'BR';
  tiene_arm: boolean;
}

export function AgregarUnionModal({
  ot,
  onUnionCreada,
  onClose
}: AgregarUnionModalProps) {
  const [nUnion, setNUnion] = useState<number | null>(null);
  const [dnUnion, setDnUnion] = useState('');
  const [tipoUnion, setTipoUnion] = useState<'BW' | 'SO' | 'FILL' | 'BR'>('BW');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  // Auto-sugerir N_UNION al montar
  useEffect(() => {
    fetch(`/api/uniones/${ot}/sugerir-n-union`)
      .then(res => res.json())
      .then(data => setNUnion(data.suggested));
  }, [ot]);

  // Validación en tiempo real
  const handleNUnionChange = async (value: string) => {
    const num = parseInt(value);
    setNUnion(num);

    if (isNaN(num)) {
      setError('Debe ser un número');
      return;
    }

    if (num < 1 || num > 20) {
      setError('Debe estar entre 1 y 20');
      return;
    }

    try {
      const res = await fetch(`/api/uniones/validate`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ ot, n_union: num })
      });

      if (res.status === 409) {
        setError('Este número de unión ya existe');
      } else {
        setError('');
      }
    } catch {
      setError('Error al validar');
    }
  };

  const handleSubmit = async () => {
    if (!nUnion || !dnUnion || error) return;

    const dnNum = parseFloat(dnUnion);
    if (isNaN(dnNum) || dnNum <= 0) {
      setError('Diámetro debe ser mayor a 0');
      return;
    }

    setLoading(true);
    try {
      const res = await fetch(`/api/uniones/crear`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          ot,
          n_union: nUnion,
          dn_union: dnNum,
          tipo_union: tipoUnion
        })
      });

      if (!res.ok) {
        const data = await res.json();
        throw new Error(data.detail || 'Error al crear unión');
      }

      const nuevaUnion = await res.json();
      onUnionCreada({
        n_union: nuevaUnion.n_union,
        dn_union: nuevaUnion.dn_union,
        tipo_union: nuevaUnion.tipo_union,
        tiene_arm: false
      });
      onClose();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Error al crear la unión');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
      <div className="bg-white rounded-lg p-6 w-full max-w-md">
        <h2 className="text-2xl font-bold mb-6">Agregar Unión Faltante</h2>

        <div className="space-y-4">
          <Input
            label="Número de Unión"
            type="number"
            value={nUnion || ''}
            onChange={e => handleNUnionChange(e.target.value)}
            error={error}
            min={1}
            max={20}
            placeholder="Ej: 11"
          />

          <Input
            label="Diámetro (pulgadas)"
            type="number"
            step="0.1"
            value={dnUnion}
            onChange={e => setDnUnion(e.target.value)}
            placeholder="Ej: 2.5"
          />

          <Select
            label="Tipo de Unión"
            value={tipoUnion}
            onChange={(val) => setTipoUnion(val as typeof tipoUnion)}
            options={[
              { label: 'BW (Butt Weld)', value: 'BW' },
              { label: 'SO (Slip On)', value: 'SO' },
              { label: 'FILL (Fillet)', value: 'FILL' },
              { label: 'BR (Branch)', value: 'BR' }
            ]}
          />
        </div>

        <div className="flex gap-4 mt-6">
          <Button
            onClick={onClose}
            variant="secondary"
            className="flex-1"
          >
            Cancelar
          </Button>
          <Button
            onClick={handleSubmit}
            disabled={!nUnion || !dnUnion || !!error || loading}
            className="flex-1"
          >
            {loading ? 'Agregando...' : 'Agregar'}
          </Button>
        </div>
      </div>
    </div>
  );
}
```

---

### 5.2 Página: Seleccionar Uniones

**Archivo:** `app/seleccionar-uniones/page.tsx`

```typescript
'use client';

import { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { useAppContext } from '@/lib/context';
import { Button } from '@/components/Button';
import { Card } from '@/components/Card';
import { Checkbox } from '@/components/Checkbox';
import { AgregarUnionModal } from '@/components/AgregarUnionModal';

interface Union {
  n_union: number;
  dn_union: number;
  tipo_union: string;
  tiene_arm: boolean;
  tiene_sold: boolean;
}

export default function SeleccionarUnionesPage() {
  const router = useRouter();
  const context = useAppContext();
  const { tag, operacion, workerId, workerDisplay } = context;

  const [uniones, setUniones] = useState<Union[]>([]);
  const [selectedIds, setSelectedIds] = useState<number[]>([]);
  const [showModal, setShowModal] = useState(false);
  const [loading, setLoading] = useState(false);

  // Cargar uniones disponibles
  useEffect(() => {
    if (!tag || !operacion) {
      router.push('/');
      return;
    }

    fetch(`/api/uniones/${tag}/disponibles?operacion=${operacion}`)
      .then(res => res.json())
      .then(data => setUniones(data))
      .catch(err => console.error('Error al cargar uniones:', err));
  }, [tag, operacion, router]);

  const handleAgregarUnion = (nuevaUnion: Union) => {
    // Agregar a la lista y auto-seleccionar
    setUniones(prev => [...prev, nuevaUnion]);
    setSelectedIds(prev => [...prev, nuevaUnion.n_union]);
  };

  const handleToggle = (nUnion: number) => {
    setSelectedIds(prev => {
      if (prev.includes(nUnion)) {
        return prev.filter(id => id !== nUnion);
      } else {
        return [...prev, nUnion];
      }
    });
  };

  const handleConfirmar = async () => {
    setLoading(true);
    try {
      const res = await fetch(`/api/occupation/confirmar-seleccion`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          ot: tag,
          operacion,
          selected_unions: selectedIds,
          worker_id: workerId
        })
      });

      if (!res.ok) throw new Error('Error al confirmar selección');

      const result = await res.json();

      // Guardar resultado en context para pantalla de éxito
      context.setSelectionResult(result);

      // Navegar a pantalla de éxito
      router.push('/exito');
    } catch (err) {
      console.error('Error:', err);
      alert('Error al confirmar selección');
    } finally {
      setLoading(false);
    }
  };

  const total = uniones.length;
  const selected = selectedIds.length;

  const buttonText = selected === 0
    ? "Cancelar Operación"
    : `Confirmar (${selected} ${selected === 1 ? 'unión' : 'uniones'})`;

  return (
    <div className="container mx-auto px-4 py-8">
      <div className="max-w-2xl mx-auto">
        <h1 className="text-3xl font-bold mb-2">
          Seleccionar Uniones {operacion === 'ARM' ? 'Armadas' : 'Soldadas'}
        </h1>
        <p className="text-gray-600 mb-6">
          Spool: <span className="font-semibold">{tag}</span> |
          Trabajador: <span className="font-semibold">{workerDisplay}</span>
        </p>

        {/* Lista de uniones */}
        <div className="space-y-3 mb-6">
          {uniones.length === 0 ? (
            <Card className="p-6 text-center text-gray-500">
              No hay uniones pendientes.
              El spool se completará automáticamente.
            </Card>
          ) : (
            uniones.map(u => (
              <Card
                key={u.n_union}
                className="flex items-center gap-4 p-4 hover:bg-gray-50"
              >
                <Checkbox
                  checked={selectedIds.includes(u.n_union)}
                  onChange={checked => {
                    if (checked) {
                      setSelectedIds(prev => [...prev, u.n_union]);
                    } else {
                      setSelectedIds(prev => prev.filter(id => id !== u.n_union));
                    }
                  }}
                  className="h-6 w-6"
                />

                <div className="flex-1">
                  <p className="font-semibold text-lg">
                    Unión #{u.n_union}
                  </p>
                  <p className="text-sm text-gray-600">
                    {u.dn_union}" - {u.tipo_union}
                  </p>
                </div>

                {/* Indicador visual para SOLD */}
                {operacion === 'SOLD' && (
                  <span
                    className={`px-3 py-1 rounded-full text-sm font-medium ${
                      u.tiene_arm
                        ? 'bg-green-100 text-green-800'
                        : 'bg-yellow-100 text-yellow-800'
                    }`}
                  >
                    {u.tiene_arm ? '✓ Armada' : '⚠ Sin armar'}
                  </span>
                )}
              </Card>
            ))
          )}
        </div>

        {/* Botón agregar unión */}
        <Button
          onClick={() => setShowModal(true)}
          variant="secondary"
          className="w-full mb-4 h-16 text-lg"
        >
          + Agregar Unión Faltante
        </Button>

        {/* Info */}
        <div className="bg-blue-50 border border-blue-200 rounded-lg p-4 mb-4">
          <p className="text-sm text-blue-800">
            <strong>Seleccionadas:</strong> {selected} de {total}
            {selected === total && total > 0 && (
              <span className="ml-2">
                ✓ Todas las uniones (spool se completará)
              </span>
            )}
          </p>
        </div>

        {/* Botón confirmar */}
        <Button
          onClick={handleConfirmar}
          disabled={loading}
          className="w-full h-20 text-xl"
        >
          {loading ? 'Procesando...' : buttonText}
        </Button>
      </div>

      {/* Modal */}
      {showModal && (
        <AgregarUnionModal
          ot={tag}
          onUnionCreada={handleAgregarUnion}
          onClose={() => setShowModal(false)}
        />
      )}
    </div>
  );
}
```

---

## 6. Eventos de Metadata

### Nuevos Eventos v4.0

| Evento | Metadata | Disparador | Ejemplo |
|--------|----------|------------|---------|
| `UNION_CREADA` | `{n_union, tipo, dn, creado_por}` | Trabajador agrega unión desde app | `{n_union: 11, tipo: "BW", dn: 2.5, creado_por: "MR(93)"}` |
| `SPOOL_ARM_PAUSADO` | `{uniones_completadas, total, uniones_trabajadas}` | Selección parcial ARM | `{uniones_completadas: 7, total: 11, uniones_trabajadas: [1,2,3,4,5,6,7]}` |
| `SPOOL_ARM_COMPLETADO` | `{uniones_completadas, total, uniones_trabajadas}` | Todas ARM completas | `{uniones_completadas: 11, total: 11, uniones_trabajadas: [8,9,10,11]}` |
| `SPOOL_SOLD_PAUSADO` | `{uniones_completadas, total, uniones_trabajadas}` | Selección parcial SOLD | `{uniones_completadas: 5, total: 11, uniones_trabajadas: [1,2,3,4,5]}` |
| `SPOOL_SOLD_COMPLETADO` | `{uniones_completadas, total, uniones_trabajadas}` | Todas SOLD completas | `{uniones_completadas: 11, total: 11, uniones_trabajadas: [6,7,8,9,10,11]}` |
| `SPOOL_CANCELADO` | `{operacion, motivo}` | 0 uniones seleccionadas | `{operacion: "ARM", motivo: "sin_seleccion"}` |
| `SPOOL_NDT_RECHAZADO` | `{union_rechazada, ndt_tipo, total_rechazos}` | R_NDT = Rechazado | `{union_rechazada: 5, ndt_tipo: "RT", total_rechazos: 1}` |
| `SPOOL_NDT_APROBADO` | `{uniones_probadas}` | Todas Aprobado/NA | `{uniones_probadas: 11}` |

### Formato de Eventos

```python
{
  "tipo": "UNION_CREADA",
  "tag_spool": "OT-123",
  "worker": "MR(93)",
  "timestamp": "30-01-2026 10:15:00",
  "metadata": {
    "n_union": 11,
    "tipo": "BW",
    "dn": 2.5,
    "creado_por": "MR(93)"
  }
}
```

---

## 7. Diagrama de Estados

### Nivel Spool (Operaciones)

```
DISPONIBLE
    │
    ├──→ TOMAR ARM ──→ OCUPADO (ARM) ──→ Selección
    │                                       ├→ 0: DISPONIBLE (CANCELAR)
    │                                       ├→ Parcial: EN_PROGRESO (ARM 7/11)
    │                                       └→ Completo: ARM_COMPLETADO (11/11)
    │
    └──→ TOMAR SOLD ──→ OCUPADO (SOLD) ──→ Selección
                                              ├→ 0: (mantiene estado)
                                              ├→ Parcial: EN_PROGRESO (SOLD 5/11)
                                              └→ Completo: SOLD_COMPLETADO (11/11)
                                                               ↓
                                                          NDT (metrología)
                                                               ├→ Rechazado: REPARACION
                                                               └→ Aprobado: APROBADO

NOTAS:
- ARM y SOLD pueden intercalarse libremente
- Ejemplo válido: ARM 7/11 → SOLD 5/11 → ARM 11/11 → SOLD 11/11
- No existe validación ARM antes de SOLD
```

### Nivel Unión (Uniones)

```
CREADA (por ingeniería o trabajador)
    │
    ├──→ ARM_FECHA_FIN != NULL ──→ ARMADA
    │
    └──→ SOL_FECHA_FIN != NULL ──→ SOLDADA
                                       ↓
                                  NDT registrado
                                       ├→ Aprobado
                                       └→ Rechazado (activa REPARACION en spool)

NOTAS:
- Una unión puede estar SOLDADA sin estar ARMADA (válido ✅)
- N_UNION puede tener gaps (1,2,3,5,7,9 es válido)
- Múltiples trabajadores pueden trabajar el mismo spool
```

---

## 8. Modificaciones en Hoja Operaciones

### Nuevas Columnas

| # | Columna | Tipo | Descripción | Cálculo |
|---|---------|------|-------------|---------|
| 68 | `Total_Uniones` | Integer | Total de uniones del spool | `COUNT(*) FROM Uniones WHERE OT={TAG}` |
| 69 | `Uniones_ARM_Completadas` | String | Progreso ARM | `"{completadas}/{total}"` ej: "7/11" |
| 70 | `Uniones_SOLD_Completadas` | String | Progreso SOLD | `"{completadas}/{total}"` ej: "5/11" |

### Actualización de Estado_Detalle

```python
def get_estado_detalle(ot: str) -> str:
    total = count_total_unions(ot)
    arm = count_completed_arm(ot)
    sold = count_completed_sold(ot)

    if arm == total and sold == total:
        return "SOLD Completado"
    elif arm == total:
        return "ARM Completado"
    elif sold == total:
        return f"SOLD Completado (ARM pendiente {arm}/{total})"
    elif arm > 0 or sold > 0:
        return f"En Progreso (ARM {arm}/{total}, SOLD {sold}/{total})"
    else:
        return "Disponible"
```

---

## 9. Casos Edge

### Caso 1: Soldador trabaja unión sin armar

```
Estado inicial:
- Unión #5: ARM_FECHA_FIN = NULL, SOL_FECHA_FIN = NULL

Soldador hace TOMAR SOLD, selecciona #5:
- Backend NO valida que ARM_FECHA_FIN != NULL
- Escribe: SOL_FECHA_FIN = "30-01-2026 14:00"

Resultado:
- Unión #5: ARM_FECHA_FIN = NULL, SOL_FECHA_FIN = "30-01-2026 14:00"

✅ VÁLIDO - El sistema lo permite sin error
⚠️ Warning visual en frontend: "⚠ Sin armar" (amarillo)
```

### Caso 2: N_UNION con gaps

```
Estado:
- Uniones existentes: 1, 2, 3, 5, 7, 9

Trabajador agrega unión:
- Auto-sugerencia: 10 (max + 1)
- Puede elegir: 4, 6, 8, 10, 11, 12... (cualquier 1-20 no usado)

Trabajador elige: 4
- Backend valida que 4 no existe ✓
- Crea unión #4

Resultado:
- Uniones: 1, 2, 3, 4, 5, 7, 9

✅ VÁLIDO - No se requiere secuencia consecutiva
```

### Caso 3: Spool con 0 uniones

```
Estado:
- Spool OT-999 no tiene uniones pre-cargadas
- Total_Uniones = 0

Trabajador hace TOMAR ARM:
- Pantalla P5 muestra lista vacía
- Frontend muestra: "No hay uniones pendientes"
- Botón: "Confirmar" (habilitado)

Trabajador puede:
1. Agregar uniones con "+ Agregar Unión Faltante"
2. Confirmar sin seleccionar (0/0) → Auto-completa

✅ VÁLIDO - Permite spools sin uniones
```

### Caso 4: Múltiples trabajadores intercalados

```
Timeline:

T1: Armador A → TOMAR ARM → Selecciona 1,2,3,4,5 → 5/10 ARM
    - ARM_WORKER de uniones 1-5: "Trabajador A"

T2: Soldador B → TOMAR SOLD → Selecciona 1,2,3 → 3/10 SOLD
    - SOL_WORKER de uniones 1-3: "Trabajador B"
    - Estado: ARM 5/10, SOLD 3/10

T3: Armador C → TOMAR ARM → Selecciona 6,7,8 → 8/10 ARM
    - ARM_WORKER de uniones 6-8: "Trabajador C"
    - Estado: ARM 8/10, SOLD 3/10

T4: Soldador B → TOMAR SOLD → Selecciona 4,5,6,7,8,9,10 → 10/10 SOLD
    - SOL_WORKER de uniones 4-10: "Trabajador B"
    - Estado: ARM 8/10, SOLD 10/10 ✅

T5: Armador A → TOMAR ARM → Selecciona 9,10 → 10/10 ARM ✅
    - ARM_WORKER de uniones 9-10: "Trabajador A"
    - Estado: ARM 10/10 ✅, SOLD 10/10 ✅

Resultado en Operaciones:
- Armador: "Trabajador A" (primer ARM_WORKER encontrado, unión #1)
- Soldador: "Trabajador B" (primer SOL_WORKER encontrado, unión #1)
- Estado_Detalle: "SOLD Completado"

✅ VÁLIDO - Múltiples trabajadores pueden contribuir
```

---

## 10. Checklist de Implementación

### Backend

- [ ] **Modelo Union** (`backend/models/union.py`)
  - [ ] 18 campos
  - [ ] Validaciones Pydantic (n_union: 1-20, dn_union > 0)

- [ ] **UnionRepository** (`backend/repositories/union_repository.py`)
  - [ ] `create(union)` - Crear nueva unión
  - [ ] `exists(ot, n_union)` - Validar duplicado
  - [ ] `get_union(ot, n_union)` - Obtener por PK
  - [ ] `get_max_n_union(ot)` - Auto-sugerencia
  - [ ] `get_by_filter(ot, arm_fin, sol_fin)` - Filtros flexibles
  - [ ] `batch_update_arm(ot, n_unions, ...)` - Batch ARM
  - [ ] `batch_update_sold(ot, n_unions, ...)` - Batch SOLD
  - [ ] `count_total(ot)` - Total uniones
  - [ ] `count_completed_arm(ot)` - Completadas ARM
  - [ ] `count_completed_sold(ot)` - Completadas SOLD

- [ ] **UnionService** (`backend/services/union_service.py`)
  - [ ] `crear_union(...)` - Con validaciones
  - [ ] `get_disponibles(ot, operacion)` - Sin validación ARM→SOLD
  - [ ] `process_selection(...)` - Auto-determinar estado

- [ ] **Router /api/uniones** (`backend/routers/uniones.py`)
  - [ ] `POST /crear` - Crear unión
  - [ ] `POST /validate` - Validar N_UNION en tiempo real
  - [ ] `GET /{ot}/disponibles?operacion=ARM|SOLD` - Lista para selección
  - [ ] `GET /{ot}/sugerir-n-union` - Auto-sugerencia
  - [ ] `GET /{ot}/soldadas` - Para pantalla NDT

- [ ] **Modificar Router /api/occupation**
  - [ ] Nuevo endpoint `POST /confirmar-seleccion`
  - [ ] Recibe `{ot, operacion, selected_unions[]}`
  - [ ] Llama a `UnionService.process_selection()`
  - [ ] Actualiza Operaciones con progreso

- [ ] **Metadata**
  - [ ] Agregar 8 nuevos tipos de eventos
  - [ ] Tests de logging

- [ ] **Tests Unitarios**
  - [ ] Crear unión con N_UNION duplicado → Error 400
  - [ ] Crear unión con DN ≤ 0 → Error 400
  - [ ] Soldar unión sin ARM → OK (sin error)
  - [ ] Auto-determinar PAUSAR vs COMPLETAR
  - [ ] Cálculo progreso correcto

- [ ] **Tests Integración**
  - [ ] Flujo completo: TOMAR → Agregar unión → Seleccionar → Confirmar
  - [ ] Flujo intercalado: ARM parcial → SOLD parcial → ARM completo → SOLD completo
  - [ ] Validación N_UNION en tiempo real

### Frontend

- [ ] **Componente AgregarUnionModal** (`components/AgregarUnionModal.tsx`)
  - [ ] Input N_UNION con validación tiempo real
  - [ ] Input DN_UNION (number, step 0.1)
  - [ ] Select TIPO_UNION (BW, SO, FILL, BR)
  - [ ] Auto-sugerencia al montar
  - [ ] Manejo de errores

- [ ] **Página Seleccionar Uniones** (`app/seleccionar-uniones/page.tsx`)
  - [ ] Lista de uniones con checkboxes
  - [ ] Indicador "✓ Armada" / "⚠ Sin armar" para SOLD
  - [ ] Botón "+ Agregar Unión Faltante"
  - [ ] Botón dinámico: "Cancelar" / "Confirmar (N)"
  - [ ] Info box: "Seleccionadas: X de Y"

- [ ] **Context** (`lib/context.tsx`)
  - [ ] `selectionResult` state
  - [ ] `setSelectionResult()`

- [ ] **Página Éxito** (`app/exito/page.tsx`)
  - [ ] Mostrar: "Uniones armadas: 7/11" o "Spool completado"
  - [ ] Diferenciar PAUSAR vs COMPLETAR vs CANCELAR

- [ ] **E2E Tests** (Playwright)
  - [ ] Agregar unión desde app
  - [ ] Validación N_UNION duplicado
  - [ ] Flujo TOMAR → Seleccionar 5 → Confirmar → Validar progreso
  - [ ] Flujo TOMAR → Seleccionar 0 → Cancelar
  - [ ] Flujo intercalado ARM/SOLD

### Google Sheets

- [ ] **Crear hoja "Uniones"**
  - [ ] 18 columnas (ID, OT, N_UNION, ..., Fecha_Modificacion)
  - [ ] Data Validation: N_UNION (1-20, integer)
  - [ ] Data Validation: TIPO_UNION (BW, SO, FILL, BR)
  - [ ] Data Validation: DN_UNION (> 0)

- [ ] **Modificar hoja "Operaciones"**
  - [ ] Agregar columna 68: Total_Uniones
  - [ ] Agregar columna 69: Uniones_ARM_Completadas
  - [ ] Agregar columna 70: Uniones_SOLD_Completadas

- [ ] **Pre-cargar datos de testing**
  - [ ] 10 spools con 5-10 uniones cada uno
  - [ ] Algunos con N_UNION gaps (ej: 1,2,3,5,7)
  - [ ] Algunos con 0 uniones

### Documentación

- [ ] Actualizar `.planning/PROJECT.md` con v4.0
- [ ] Documentar eventos UNION_* en Metadata
- [ ] Diagrama UX: Flujo agregar unión (Figma/Miro)
- [ ] Guía para trabajadores: "Cómo agregar uniones faltantes"
- [ ] Guía técnica: Validaciones N_UNION
- [ ] Release notes v4.0

---

## 11. Resumen de Cambios Clave

### v1.0 → v2.0

| Aspecto | v1.0 (Original) | v2.0 (Final) |
|---------|-----------------|--------------|
| **Validación ARM→SOLD** | ✅ Obligatoria (soldador debe esperar ARM completo) | ❌ Eliminada (soldador puede trabajar sin ARM) |
| **N_UNION secuencial** | ✅ Consecutivo sin gaps (1,2,3,4...) | ❌ Solo único, puede tener gaps (1,3,5 válido) |
| **Agregar uniones** | Solo ingeniería desde Sheets | ✅ Trabajadores desde app + ingeniería Sheets |
| **Flujo ARM/SOLD** | Secuencial (primero ARM 100%, luego SOLD) | ✅ Paralelo e intercalado (ARM 7/10 + SOLD 5/10) |
| **Auto-completar** | Basado en botones PAUSAR/COMPLETAR | ✅ Basado en cantidad seleccionada (auto) |
| **Botones PAUSAR/COMPLETAR** | Explícitos en P3 | ❌ Eliminados (auto-determinación) |
| **Edición uniones** | Solo desde Sheets | ✅ Crear desde app, editar desde Sheets |
| **Multi-trabajador** | No contemplado | ✅ Múltiples trabajadores pueden trabajar mismo spool |

---

## 12. Preguntas Resueltas

1. ✅ **¿Se puede editar una unión después de que tiene ARM_FECHA_FIN?**
   → Sí, pero solo desde Google Sheets (no desde la app)

2. ✅ **¿Qué rol puede acceder a la pantalla de NDT?**
   → Solo metrología (validar por rol en backend)

3. ✅ **¿Se necesita un reporte visual de progreso por spool?**
   → No de momento (solo text: "7/11")

4. ✅ **¿Cómo se manejan correcciones de N_UNION si ingeniería cargó mal?**
   → Solo desde Google Sheets (edición manual)

5. ✅ **¿Se debe validar que DN_UNION y TIPO_UNION sean consistentes con estándares industriales?**
   → No (sin validaciones de estándares, máxima flexibilidad)

---

## Apéndice A: Glosario

- **ARM:** Armado (proceso de ensamblaje de uniones)
- **SOLD:** Soldadura (proceso de soldado de uniones)
- **NDT:** Non-Destructive Testing (Pruebas No Destructivas)
- **OT:** Orden de Trabajo (equivalente a TAG_SPOOL)
- **N_UNION:** Número secuencial de unión dentro de un spool (1-20)
- **DN_UNION:** Diámetro Nominal en pulgadas
- **TIPO_UNION:** Tipo de unión (BW, SO, FILL, BR)
- **BW:** Butt Weld (soldadura a tope)
- **SO:** Slip On (deslizable)
- **FILL:** Fillet (filete)
- **BR:** Branch (ramal)
- **PT:** Penetrant Testing (prueba de líquidos penetrantes)
- **MT:** Magnetic Testing (prueba magnética)
- **RT:** Radiographic Testing (prueba radiográfica)
- **UT:** Ultrasonic Testing (prueba ultrasónica)
- **NA:** No Aplica

---

**Versión:** 2.0
**Fecha:** 30 Enero 2026
**Autor:** Claude Code + Usuario
**Estado:** Documento Final para Implementación
