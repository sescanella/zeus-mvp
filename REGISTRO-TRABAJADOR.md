# Registro de Trabajo del Trabajador

## Problema

Los armadores y soldadores llevan un **registro en papel** de las uniones que realizan, como proteccion personal. Si una union falla en terreno, pueden demostrar cuales hicieron y cuales no. ZEUES necesita capturar esa informacion digitalmente, de forma tan facil que eventualmente reemplace el papel.

## Contexto del usuario

### Que anotan en papel hoy
- **Nombre** del trabajador (encabezado)
- **TAG_SPOOL**
- **NV** (Nota de Venta) -- en la practica no la anotan
- **Diametro** (DN)
- **Uniones trabajadas** (ej: "del 1 al 6")
- **PD** (pulgadas-diametro = diametro x cantidad de uniones)
- **Fecha inicio** (MM/DD)
- **Fecha parcial** (solo cuando interrumpen un trabajo)
- **Fecha termino**
- **Soldador/Armador** (el otro trabajador, para referencia cruzada/defensa)

### Datos que ZEUES ya captura silenciosamente
| Dato | Columna Uniones | Cuando se escribe |
|---|---|---|
| TAG_SPOOL | `TAG_SPOOL` (col D) | Al crear la union |
| Quien lo hizo | `ARM_WORKER` / `SOL_WORKER` (col I/L) | Al FINALIZAR |
| Fecha inicio | `ARM_FECHA_INICIO` / `SOL_FECHA_INICIO` (col G/J) | Al FINALIZAR (viene de Fecha_Ocupacion) |
| Fecha termino | `ARM_FECHA_FIN` / `SOL_FECHA_FIN` (col H/K) | Al FINALIZAR (timestamp del momento) |
| PD | Calculable: sum(DN_UNION) por worker | Ya existe en metricas |

### Datos que requieren input del trabajador
| Dato | Columna Uniones | Estado |
|---|---|---|
| DN (diametro) | `DN_UNION` (col E) | Ya se captura en UnionesModal |
| TIPO_UNION | `TIPO_UNION` (col F) | Ya se captura en UnionesModal |
| Cuales uniones hizo | Seleccion al FINALIZAR | **Falta** |

### Datos que faltan en el sistema
| Dato | Existe? | Solucion |
|---|---|---|
| Fecha parcial (interrupcion) | No -- PAUSAR borra Fecha_Ocupacion | Necesita solucion |
| El otro trabajador | Derivable post-hoc (ARM_WORKER + SOL_WORKER) | No requiere input |

## Reglas de negocio clave

- **Union = indivisible**: una union la hace UN solo trabajador, no se comparte
- **Numeros de union son fijos**: vienen del plano isometrico, estan marcados fisicamente en el spool
- **Numeros siempre consecutivos** en los planos (1,2,3...N)
- **Un spool puede ser trabajado por 2+ armadores** (o 2+ soldadores): cada uno registra su subconjunto
- **DN casi siempre igual** para todas las uniones del spool (5 de 6 veces), pero puede variar
- **El trabajador decide al final** cuales uniones hizo (no se predefine antes de empezar)
- **Ventana corta de ingreso**: se sacan el traje y anotan inmediatamente
- **Produccion diaria**: 60-100 PD por trabajador/dia (variable cantidad de spools)
- **Doble ingreso inicial**: papel + app simultaneo hasta ganar confianza
- **Correccion permitida**: un trabajador puede corregir DN/TIPO que otro ingreso mal
- **Formato worker estandar**: `INICIALES(ID)` -- ej: `MR(93)`. Normalizar cualquier formato legacy a este
- **Eliminacion con confirmacion doble**: cualquier trabajador puede eliminar uniones sin trabajo, con patron Si/No

## Decisiones tomadas

1. **Formato worker**: `MR(93)` (INICIALES + ID). Corregir todos los lugares que escriban otro formato.
2. **Llamadas API separadas**: guardarUniones y finalizarSpool se mantienen como dos llamadas. Si la segunda falla, el modal muestra error y permite reintentar sin re-ingresar datos.
3. **Eliminacion de uniones**: se mantiene boton delete para uniones sin trabajo registrado, con confirmacion doble (Si/No). Cualquier trabajador puede eliminar/corregir.
4. **Boton de uniones en card**: abre modal en **modo consulta/edicion** (opcion C) -- muestra badges de workers en filas con trabajo, permite editar DN/TIPO, pero NO muestra checkboxes de seleccion de trabajo. La seleccion de trabajo solo ocurre desde FINALIZAR/PAUSAR.
5. **Mi Registro**: consulta al final de la jornada (no en tiempo real). WiFi disponible en sitio.
6. **SOLD sin ARM**: mostrar "Falta ARM" en las filas donde ARM no esta completado.
7. **Reparacion**: proceso diferente, no pasa por flujo de uniones. Ignorar para este scope.
8. **Reduccion de cantidad post-guardado**: NO se permite desde la app. Si se ingresaron uniones de mas, el administrador las elimina desde Google Sheets. Simplifica el modal.
9. **Prioridad**: Pieza 1 completa antes de empezar Pieza 2.
10. **El trabajador siempre sabe el total de uniones** porque tiene el plano isometrico.

---

## Plan de implementacion: Pieza 1

### Step 0a: Fix -- Normalizar formato worker en union_router.py [S]

**Problema:** `union_router.py` linea 336 escribe `f"{worker.apellido}({request.worker_id})"` produciendo `"Rodriguez(93)"` en vez del estandar `"MR(93)"`. Cada FINALIZAR por el router v4 escribe el formato incorrecto a `ARM_WORKER`/`SOL_WORKER`.

**Solucion:**
- En `backend/routers/union_router.py` linea 336: reemplazar `f"{worker.apellido}({request.worker_id})"` con `worker.nombre_completo` (que produce el formato `INICIALES(ID)`)
- Verificado: `worker.nombre_completo` produce `MR(93)` (confirmado en revision de codigo)

**Archivos:** `backend/routers/union_router.py`
**Dependencias:** Ninguna -- fix independiente

### Step 0b: Fix -- Invalidar cache de worksheet en metodos de escritura [S]

**Problema BLOCKER:** `UnionRepository` tiene metodos de escritura (`create_unions_batch`, `update_unions_batch`, `delete_unions_without_work`) que escriben directamente a Google Sheets pero solo invalidan `ColumnMapCache` (headers), NO el cache de datos del worksheet (TTL 60s en `SheetsRepository._cache`).

Esto causa que el flujo `guardarUniones` → `finalizarSpool` falle para spools con 0 uniones previas: `finalizarSpool` lee datos stale y no encuentra las uniones recien creadas.

**Solucion:**
Agregar invalidacion del cache de worksheet despues de cada escritura en estos metodos:
```python
self.sheets_repo._cache.invalidate(f"worksheet:{self._sheet_name}")
```

**Metodos a modificar:**
- `create_unions_batch` (despues de `append_rows`)
- `update_unions_batch` (despues de `batch_update`)
- `delete_unions_without_work` (despues de delete)
- `batch_update_arm_full` (despues de `batch_update`)
- `batch_update_sold_full` (despues de `batch_update`)

**Archivos:** `backend/repositories/union_repository.py`
**Dependencias:** Ninguna -- fix independiente, critico para que el flujo funcione

### Step 1: Bug fix -- Eliminar renumerado al borrar [S]

**Problema:** `renumber()` (linea 98-99 en UnionesModal.tsx) reasigna `n_union = i + 1` despues de filtrar. Los numeros de union son identificadores fisicos del plano -- renumerar destruye su identidad.

**Solucion:**
1. Eliminar funcion `renumber` completamente
2. En `handleDeleteRow`: cambiar `setRows(renumber(filtered))` a `setRows(filtered)` -- mantener el boton delete con confirmacion doble para uniones sin trabajo
3. En `handleCountChange` al reducir: eliminar logica de reduccion post-guardado. Solo permitir reducir filas vacias recien creadas (no guardadas aun). Si las uniones ya estan en Sheets, el admin las elimina desde Google Sheets
4. Al aumentar cantidad: asignar nuevos numeros como `max(n_union existentes) + 1, +2, ...`

**Archivos:** `zeues-frontend/components/UnionesModal.tsx`
**Dependencias:** Ninguna -- puede hacerse en paralelo con Steps 0a/0b

### Step 2: Backend -- Enriquecer respuesta de /todas con worker info + id [S]

**Problema:** `get_all_by_tag` retorna `has_work: bool` pero no *quien* hizo el trabajo. El modal necesita mostrar el nombre del worker en filas con trabajo. Tambien falta el `id` compuesto (OT+N_UNION) para enviar al FINALIZAR.

**Nota:** `get_all_by_tag` actualmente no lee la columna OT. Debe agregarse la lectura de `ot_col_idx` para sintetizar el ID.

**Cambios:**

`backend/models/union_api.py` -- `UnionEditable`:
- Agregar: `id: Optional[str] = None`
- Agregar: `arm_worker: Optional[str] = None`
- Agregar: `sol_worker: Optional[str] = None`

`backend/repositories/union_repository.py` -- `get_all_by_tag`:
- Leer columna OT ademas de TAG_SPOOL y N_UNION
- Exponer arm_worker y sol_worker en el dict retornado
- Agregar `id` con formato `OT+N_UNION`

`backend/routers/union_router.py` -- `get_todas_uniones`:
- Pasar los nuevos campos al construir `UnionEditable`

`zeues-frontend/lib/types.ts` -- `UnionEditable`:
- Agregar: `id?: string`, `arm_worker?: string | null`, `sol_worker?: string | null`

**Dependencias:** Ninguna -- adicion backward compatible

### Step 3: Frontend -- Tres modos del modal + badges de worker [L]

El modal ahora tiene 3 modos determinados por props:

| Modo | Cuando | `operacion` prop | Checkboxes | Badges | Edicion DN/TIPO | Delete |
|---|---|---|---|---|---|---|
| **Consulta/Edicion** | Boton uniones en card | `null` | No | Si | Si (sin trabajo) | Si (sin trabajo) |
| **Seleccion ARM** | FINALIZAR/PAUSAR ARM | `'ARM'` | Si | Si | Si (sin trabajo) | Si (sin trabajo) |
| **Seleccion SOLD** | FINALIZAR/PAUSAR SOLD | `'SOLD'` | Si | Si (sin trabajo) | Si (sin trabajo) |

**Cambios a `UnionRow`:**
```typescript
interface UnionRow {
  id: string | null;          // OT+N_UNION del backend
  n_union: number;
  dn_union: number | null;
  tipo_union: string | null;
  has_work: boolean;
  arm_worker: string | null;
  sol_worker: string | null;
  selected: boolean;          // solo usado en modo seleccion
}
```

**Cambios a props:**
```typescript
interface UnionesModalProps {
  isOpen: boolean;
  spool: SpoolCardData;
  operacion: 'ARM' | 'SOLD' | null;  // null = modo consulta/edicion
  onComplete: (selectedUnionIds: string[]) => void;  // retorna [] en modo consulta
  onClose: () => void;
  isTopOfStack?: boolean;
}
```

**UI por fila:**
- Badge de worker (ej "MR(93)") en filas con trabajo para esa operacion -- siempre visible en todos los modos
- Checkbox a la izquierda solo en modo seleccion (operacion !== null)
- DN y TIPO editables cuando no tiene trabajo registrado (`has_work === false`)
- Boton delete (X) con confirmacion doble para uniones sin trabajo
- En modo SOLD: filas sin ARM completado muestran etiqueta "Falta ARM" y no son seleccionables

**Reglas de seleccion (solo modos ARM/SOLD):**
- ARM: seleccionable si `arm_worker === null` y tiene DN + TIPO completos
- SOLD: seleccionable si `sol_worker === null` Y `arm_worker !== null` y tiene DN + TIPO completos
- Cuando `operacion === null`: sin checkboxes, `onComplete([])` al guardar

**Barra resumen (solo modos ARM/SOLD, encima de GUARDAR):**
- `"Seleccionaste N uniones = X PD"` donde PD = sum(dn_union) de filas seleccionadas

**Boton GUARDAR:**
- Modo consulta: texto "GUARDAR", guarda definiciones, llama `onComplete([])`
- Modo seleccion sin seleccion: texto "GUARDAR", guarda definiciones, llama `onComplete([])`
- Modo seleccion con seleccion: texto "GUARDAR Y CONFIRMAR", guarda definiciones, llama `onComplete(selectedIds)`

**Flujo primera vez (0 uniones) con FINALIZAR:**
- Worker abre FINALIZAR, modal se abre con una fila vacia
- Primero hace setup: cantidad, DN, TIPO (los checkboxes aparecen conforme las filas se completan)
- Luego selecciona cuales hizo
- Guardar hace ambas cosas en secuencia

**Archivos:** `zeues-frontend/components/UnionesModal.tsx`, `zeues-frontend/lib/types.ts`
**Dependencias:** Step 1, Step 2

### Step 4: Frontend -- Integrar modal con flujos FINALIZAR/PAUSAR/Card [L]

**Problema:** `page.tsx` tiene 3 puntos de entrada al modal que deben distinguirse en `handleUnionesComplete`.

**Solucion -- estado `pendingAction` en page.tsx:**
```typescript
type PendingAction = {
  type: 'FINALIZAR' | 'PAUSAR' | 'EDIT';
  spool: SpoolCardData;
  operation: 'ARM' | 'SOLD' | null;
  workerId: number | null;
};
```

**Rewiring de flujos:**

1. **FINALIZAR ARM/SOLD** (lineas 233-274): en vez de llamar `executeDirectAction`, setear `pendingAction = { type: 'FINALIZAR', spool, operation, workerId }` y abrir modal con `operacion = operation`

2. **PAUSAR ARM/SOLD** (lineas 220-231 + 233-274): ampliar el intercept -- siempre abrir modal para ARM/SOLD (no solo cuando `total_uniones === 0`). Setear `pendingAction = { type: 'PAUSAR', spool, operation, workerId }`

3. **Boton uniones en card** (linea 362-365): setear `pendingAction = { type: 'EDIT', spool, operation: null, workerId: null }` y abrir modal con `operacion = null`

**handleUnionesComplete reescrito:**
```
onComplete(selectedIds) =>
  if pendingAction.type === 'EDIT':
    solo refresh, toast "Uniones guardadas"
  if pendingAction.type === 'FINALIZAR' o 'PAUSAR':
    if selectedIds.length > 0:
      llamar finalizarSpool({ tag_spool, worker_id, operacion, selected_unions: selectedIds })
      -- sin action_override, backend auto-determina
    else if selectedIds.length === 0 y type === 'PAUSAR':
      llamar finalizarSpool con action_override: 'PAUSAR' y selected_unions: []
      -- PAUSAR sin registrar uniones (solo guardar definiciones)
```

**Manejo de fallo parcial:**
- Si `guardarUniones` funciona pero `finalizarSpool` falla: modal muestra error, no se cierra, usuario puede reintentar. Las definiciones ya estan guardadas, al reintentar solo se llama `finalizarSpool`.

**Call sites que mantienen `action_override`:**
- `handleRemoveSpool` (linea 338): sigue enviando `selected_unions: []` para cancelacion -- no cambia
- PAUSAR con 0 selecciones: envia `action_override: 'PAUSAR'` -- backend limpia ocupacion sin tocar uniones

**Archivos:** `zeues-frontend/app/page.tsx`, `zeues-frontend/components/UnionesModal.tsx`
**Dependencias:** Step 3

### Secuencia de implementacion

```
Step 0a (S) ── Fix formato worker ─────────────────────┐
Step 0b (S) ── Fix cache invalidation ─────────────────┤
Step 1  (S) ── Bug fix: eliminar renumerado ───────────┤
Step 2  (S) ── Backend: enriquecer /todas ─────────────┤
                                                        |
                                               Step 3 (L) ── Modal 3 modos + badges
                                                        |
                                               Step 4 (L) ── Integrar con flujos
```

Steps 0a, 0b, 1 y 2 pueden hacerse en paralelo. Step 3 depende de 1 y 2. Step 4 depende de 3.

### Lo que NO cambia

- **Endpoint FINALIZAR** (`/api/v4/occupation/finalizar`): ya acepta `selected_unions` y auto-determina PAUSAR/COMPLETAR
- **`batch_update_arm_full` / `batch_update_sold_full`**: ya funcionan con listas de union IDs
- **`guardarUniones` API**: ya maneja create/update/delete comparando incoming vs existentes
- **`OccupationService.finalizar_spool`**: ya maneja el flujo completo

### Riesgos y mitigaciones

| Riesgo | Mitigacion |
|---|---|
| Dos llamadas API (guardarUniones + finalizarSpool): fallo parcial deja definiciones guardadas sin trabajo registrado | Modal muestra error, no se cierra, permite reintentar solo finalizarSpool. Definiciones guardadas no se pierden |
| Formato de union ID debe ser exacto `OT+N_UNION` | Backend retorna `id` pre-formateado (Step 2), frontend nunca construye el ID |
| Datos stale entre abrir modal y guardar (otro worker completo uniones) | Backend retorna 409 en race condition. Frontend muestra error y sugiere recargar |
| PAUSAR intercept actual solo actua cuando total_uniones === 0 | Step 4 amplia la condicion: PAUSAR siempre abre modal para ARM/SOLD |
| `onComplete` signature change rompe callers existentes | Step 4 reescribe `handleUnionesComplete` con `pendingAction` para distinguir 3 flujos |
| Cache de worksheet stale despues de crear uniones | Step 0b invalida cache en todos los metodos de escritura de UnionRepository |

---

## Plan de implementacion: Pieza 2

### Step 1: Backend -- Response models [S]

**Archivo nuevo:** `backend/models/registro_api.py`

```python
class WorkerUnionRecord(BaseModel):
    n_union: int
    dn_union: float | None
    tipo_union: str | None
    fecha_inicio: str | None
    fecha_fin: str | None

class SpoolGroup(BaseModel):
    tag_spool: str
    operacion: str  # "ARM" o "SOLD"
    uniones: list[WorkerUnionRecord]
    pd_total: float  # sum(dn_union)
    otro_trabajador: str | None  # el otro worker (defensa). "Pendiente" si no asignado aun

class RegistroResumen(BaseModel):
    fecha: str
    pd_total: float
    total_uniones: int
    total_spools: int

class RegistroResponse(BaseModel):
    worker_id: int
    worker_nombre: str
    fecha: str
    resumen: RegistroResumen
    spools: list[SpoolGroup]
```

**Dependencias:** Ninguna

### Step 2: Backend -- Metodo de repositorio [M]

**Modificar:** `backend/repositories/union_repository.py`

Agregar `get_by_worker_id(worker_id: int, fecha: Optional[str] = None) -> list[dict]`:
- Lee todas las filas de Uniones (usa cache existente de `read_worksheet` si hay)
- Extrae el ID numerico de `ARM_WORKER` y `SOL_WORKER` via regex `\((\d+)\)$`
- Si el ID extraido coincide con `worker_id`, incluir la fila
- Si `fecha` proporcionada, filtrar por porcion de fecha de `ARM_FECHA_FIN` o `SOL_FECHA_FIN` (formato `DD-MM-YYYY`)
- Retorna dicts con: tag_spool, n_union, dn_union, tipo_union, operacion ("ARM"/"SOLD"), fecha_inicio, fecha_fin, arm_worker, sol_worker

**Matching por ID numerico:** El formato legacy puede ser `"Rodriguez(93)"` o `"MR(93)"`. Regex `\((\d+)\)` extrae el numero de ambos formatos. Es la unica estrategia confiable.

**Performance:** ~20K filas (2000 spools x 10 uniones). Consulta al final de jornada, no en tiempo real. Si `read_worksheet` ya cachea, es aceptable. Si no, considerar cache de 60s para este endpoint.

**Dependencias:** Step 1 (usa los models)

### Step 3: Backend -- Router nuevo [M]

**Archivo nuevo:** `backend/routers/registro_router.py`

- `GET /api/registro/{worker_id}?fecha=DD-MM-YYYY`
- Usa `get_worker_service` (para nombre) + `get_union_repository`
- Agrupa resultados por `(tag_spool, operacion)`
- Calcula `otro_trabajador`: si match fue en ARM, muestra SOL_WORKER; si SOLD, muestra ARM_WORKER. Si el otro campo es null: `"Pendiente"`
- Calcula `pd_total` por grupo y resumen general
- Default `fecha` a `today_chile()`

**Modificar:** `backend/main.py` -- agregar `app.include_router(registro_router.router, prefix="/api", tags=["Registro"])`

**Estado vacio:** Si el worker no tiene uniones para la fecha, retornar response valido con `spools: []` y `resumen.pd_total: 0`

**Dependencias:** Step 2

### Step 4: Frontend -- Types + API [S]

**Modificar:** `zeues-frontend/lib/types.ts` -- agregar interfaces RegistroResponse, SpoolGroup, WorkerUnionRecord, RegistroResumen
**Modificar:** `zeues-frontend/lib/api.ts` -- agregar `getRegistro(workerId: number, fecha?: string): Promise<RegistroResponse>`

**Dependencias:** Step 3 (backend debe existir)

### Step 5: Frontend -- Pagina /mi-registro [L]

**Archivo nuevo:** `zeues-frontend/app/mi-registro/page.tsx`

**Tres estados visuales:**

1. **Seleccion de worker**: lista completa con busqueda por texto, sin filtro de rol. `localStorage` para recordar ultimo worker seleccionado. Boton "Cambiar trabajador" visible cuando ya hay seleccion.

2. **Vista "Hoy"** (default):
   - Numero grande de PD del dia arriba
   - Resumen: X uniones en Y spools
   - Cards de spools: TAG, operacion (ARM/SOLD badge), uniones trabajadas, PD del spool, otro trabajador, fecha inicio/fin
   - Estado vacio: "No hay uniones registradas para hoy. Cuando finalices un spool, aparecera aqui."

3. **Navegacion por fecha**: `<input type="date">` nativo + boton "HOY" para volver a fecha actual
   - Nota UX: la fecha refleja cuando se finalizo el trabajo, no la sesion actual

**Design:** reusar `zeues-navy`, `zeues-orange`, white text, `font-mono`. Mobile-first (celular personal, no tablet).
Sin React Context, sin modal stack, sin polling. Simple `useState` + `useEffect`.

**Seguridad MVP:** Sin auth, cualquiera puede consultar cualquier worker por ID. Aceptado como trade-off MVP -- los datos son de produccion (PD), no sensibles personales.

**Dependencias:** Step 4

### Secuencia de implementacion

```
Backend:
  Step 1 (S, models) ──┐
                        ├── Step 2 (M, repo) ── Step 3 (M, router)
                        │
Frontend:
                        Step 4 (S, types + api) ── Step 5 (L, pagina)

Backend Step 3 debe estar deployado antes de que Step 5 funcione end-to-end.
```

### Riesgos y mitigaciones

| Riesgo | Mitigacion |
|---|---|
| Performance: 20K+ filas leidas en cada request | Consulta solo al final de jornada. Usar cache de `read_worksheet` existente. Si insuficiente, agregar cache de 60s |
| Worker ID matching con formato inconsistente | Regex `\((\d+)\)` extrae ID numerico de cualquier formato. No depende del prefijo |
| Sin auth: un worker ve datos de otro | Trade-off MVP aceptado. Datos son de produccion (PD), no sensibles. Futuro: auth simple |
| Timezone: trabajo a las 23:50, consulta a las 00:10 muestra "ayer" | Correcto por diseno -- la fecha es cuando se finalizo. Documentar en UX |
| "Otro trabajador" null cuando SOLD pendiente | Mostrar "Pendiente" en vez de vacio |

---

## Archivos relevantes (referencia rapida)

### Backend
- `backend/routers/union_router.py` -- endpoints /todas, /guardar, /finalizar. **FIX: linea 336 formato worker**
- `backend/repositories/union_repository.py` -- CRUD, batch_update, get_all_by_tag. **MODIFICAR: agregar worker+id a /todas, nuevo get_by_worker_id**
- `backend/services/occupation_service.py` -- iniciar_spool, finalizar_spool (no cambia)
- `backend/models/union_api.py` -- UnionEditable, SaveUnionsRequest, FinalizarRequestV4. **MODIFICAR: agregar campos**
- `backend/models/registro_api.py` -- **NUEVO: models para Mi Registro**
- `backend/routers/registro_router.py` -- **NUEVO: endpoint Mi Registro**
- `backend/main.py` -- **MODIFICAR: registrar nuevo router**

### Frontend
- `zeues-frontend/components/UnionesModal.tsx` -- modal actual. **REESCRIBIR: 3 modos, badges, seleccion**
- `zeues-frontend/app/page.tsx` -- modal stack, flujos. **MODIFICAR: pendingAction, rewiring**
- `zeues-frontend/lib/api.ts` -- fetch functions. **MODIFICAR: agregar getRegistro**
- `zeues-frontend/lib/types.ts` -- TypeScript types. **MODIFICAR: UnionEditable + Registro types**
- `zeues-frontend/app/mi-registro/page.tsx` -- **NUEVO: pagina Mi Registro**

## Prioridad de ejecucion

**Pieza 1 completa antes de Pieza 2.**

1. **Steps 0a + 0b (Pieza 1)**: Fixes criticos (formato worker + cache invalidation) -- hacer primero
2. **Steps 1 + 2 (Pieza 1)**: Bug fix renumerado + enriquecer backend -- en paralelo con 0a/0b
3. **Step 3 (Pieza 1)**: Modal 3 modos + badges -- depende de 1 y 2
4. **Step 4 (Pieza 1)**: Integrar con flujos FINALIZAR/PAUSAR/Card -- depende de 3
5. **Steps 1-3 (Pieza 2)**: Backend Mi Registro
6. **Steps 4-5 (Pieza 2)**: Frontend Mi Registro

## Hoja Uniones (17 columnas)

```
A: ID            (composite: OT+N_UNION)
B: OT            (FK a Operaciones)
C: N_UNION       (numero fijo del plano)
D: TAG_SPOOL     (FK a Operaciones)
E: DN_UNION      (diametro en pulgadas)
F: TIPO_UNION    (BW, SO, FILL, BR, FW, LET)
G: ARM_FECHA_INICIO
H: ARM_FECHA_FIN
I: ARM_WORKER    (formato estandar: INICIALES(ID) ej MR(93))
J: SOL_FECHA_INICIO
K: SOL_FECHA_FIN
L: SOL_WORKER    (formato estandar: INICIALES(ID) ej MR(93))
M: NDT_UNION
N: R_NDT_UNION
O: NDT_FECHA
P: NDT_STATUS
Q: version       (UUID4 optimistic locking)
```

## Hoja Operaciones (columnas relevantes)

```
B:  OT (Orden de Trabajo)
G:  TAG_SPOOL
H:  NV (Nota de Venta)
64: Ocupado_Por
65: Fecha_Ocupacion
67: Estado_Detalle
68: Total_Uniones
69: Uniones_ARM_Completadas
70: Uniones_SOLD_Completadas
71: Pulgadas_ARM
72: Pulgadas_SOLD
```
