# Informe de rediseño ZEUES v6 — hacia una versión radicalmente más simple

**Fecha:** 2026-06-10 · **Commit base:** `fdc275b` · **Autor:** arquitectura (sesión Fable 5)
**Naturaleza:** documento de decisión. No contiene código; propone qué construir y en qué orden.
**Evidencia:** todas las citas `archivo:línea` fueron re-verificadas contra el código real el
2026-06-10. Donde el anexo del prompt tenía drift, este informe usa los números corregidos.
**Decisiones del dueño:** las preguntas abiertas fueron respondidas por Sebastián el 2026-06-10
y ya están incorporadas como decisiones firmes (resumidas abajo, detalladas en §8.3).

---

## 0. Decisiones del dueño (2026-06-10) — incorporadas a este informe

| # | Pregunta | Decisión | Impacto en el diseño |
|---|----------|----------|----------------------|
| 1 | ¿Ingeniería corrige datos de ejecución a mano? | **Sí, hay que poder corregir errores de carga, pero no todos los usuarios deben tener ese derecho** | +1 endpoint de corrección supervisado (con rol) que escribe un evento de corrección auditable; nunca edición silenciosa |
| 2 | ¿El trail de auditoría debe vivir en Google Sheets? | **No. La metadata es para los devs; le da igual dónde viva** | El trail vive **solo** en la tabla `eventos` (DB). Se elimina todo espejado a Sheets → diseño más simple |
| 3 | ¿Migrar la Metadata histórica? | **No. Partir de cero; la historia anterior no suma** | La Fase 1 no migra eventos históricos. La hoja Metadata vieja se **archiva** (no se borra) por si un auditor pide historia pre-cutover |
| 4 | ¿Horizonte 30-50 workers? | **No. Máx. ~3 usuarios simultáneos, ~12 en total** | **SQLite confirmado, con margen de sobra.** El multi-worker queda cubierto desde el día uno con WAL — deja de ser una preocupación futura |
| 5 | ¿Se usan supervisor (audit-batch/legacy-snapshot) y `mi-registro`? | **No se utilizan** | Se **eliminan** en la migración → menos endpoints y menos código frontend |
| 6 | ¿Quién custodia los backups? | **Sebastián al inicio, con objetivo de pasar la responsabilidad a Matías** | El job de backup se diseña desde el inicio para ser **operable por alguien no-dev** (verificación con un click + alertas claras), no solo legible en logs |

**Efecto neto:** las respuestas *simplificaron* el diseño en 3 puntos (2, 3, 5), lo *confirmaron*
en el más crítico (4 → SQLite), y agregaron una pieza chica (1 → endpoint de corrección con rol).
El sistema final queda aún más liviano que la estimación original.

---

## 1. Resumen ejecutivo

ZEUES hace bien su trabajo de negocio: trazar spools a través de ARM/SOLD a nivel de unión,
con metrología, reparación acotada y un trail de auditoría inmutable. El problema no es el
dominio — es que **39.480 líneas de código** (25.923 backend + 13.557 frontend) sostienen un
sistema que opera con **una tablet y un trabajador a la vez**, y la mayor parte de esas líneas
no implementa reglas de negocio: defiende al sistema de sí mismo.

### Los 5 problemas raíz

1. **Estado derivado almacenado.** El estado de un spool se representa de 6 formas que
   driftean entre sí (string `Estado_Detalle`, contadores `Uniones_*_Completadas` y
   `Pulgadas_*`, columnas `Fecha_Armado/Soldadura`, filas de Uniones, eventos Metadata,
   máquinas de estado en memoria). Todo el *scar tissue* del proyecto — T-021, T-096,
   T-240/T-241, B-001/B-002, el fix cross-sheet de `fdc275b` — son curitas sobre esta única
   herida: **lo que se puede computar, se almacena; y lo almacenado drifta.**

2. **El impuesto Google Sheets.** ~2.836 líneas (`sheets_repository.py` 1.532,
   `column_map_cache.py` 443, `sheets_service.py` 739, `date_formatter.py` 122) existen solo
   para pelear con la herramienta: mapeo dinámico de columnas con hash SHA256 y lock de
   threading, caches TTL tras un incidente de rate-limit, retry con backoff exponencial,
   parseo dual de fechas serial-Excel. Y lo peor no son las líneas: **un FINALIZAR son 6-11
   llamadas API sin transacción** — una falla parcial deja el sistema inconsistente, y eso es
   exactamente lo que generó los bugs que los parches defienden.

3. **Dualidad de modelo de datos.** v2.1/v3.0 (estado a nivel spool) y v4.0 (a nivel unión)
   conviven con detección de versión inlineada (`is_v21` en `occupation_service.py:623`,
   `is_v30` en `:1202`), fallbacks "legacy" y guards `[ARM_FALLBACK_OK]`/`[H2_GUARD_*]`. La
   detección por TAG_SPOOL (T-096) existe porque la detección anterior por OT corrompió datos
   en PROD.

4. **Frontend que simula al backend.** Máquina de estados en TS, clasificador de errores que
   solo conoce 1 de 20+ códigos del backend, parsing por regex del string `Estado_Detalle` y
   del formato `"MR(93)"`, y una migración localStorage→server en 3 capas. Cada regla de
   negocio vive dos veces y puede driftar.

5. **Concurrencia vestigial.** Maquinaria de optimistic locking, columna `version`,
   `conflict_service.py` — cuyo propio docstring admite que la columna version ya fue removida
   y que el sistema es Last-Write-Wins. Es peso muerto que confunde sobre cuál es el modelo
   real.

### La recomendación en una frase

**Un solo modelo de datos a nivel de unión, almacenado en SQLite sobre un volumen de Railway
(confirmado por la escala real: máx. ~3 usuarios simultáneos, ~12 totales), con todo el estado
derivado computado on-read por una función pura; Google Sheets pasa de ser la base de datos a
ser la interfaz de ingeniería (hoja de carga + hoja de reporte read-only); el trail de
auditoría vive solo en la base de datos; migración en 4 fases sin big-bang.**

Resultado estimado: backend 25.923 → **~4.500 líneas**, frontend 13.557 → **~8.000 líneas**,
34 → **~10 endpoints**, 20 servicios → **~4-5 módulos**, FINALIZAR de 9 saltos / 6-11 llamadas
sin transacción → **3 saltos / 1 transacción SQL**. Las reglas de negocio se preservan
íntegras; lo que desaparece es la defensa contra el drift, porque el drift deja de ser posible.

---

## 2. Inventario: complejidad esencial vs accidental

### 2.1 Complejidad esencial (reglas del dominio — NO tocar)

| # | Regla | Dónde vive hoy |
|---|-------|----------------|
| E1 | Un spool tiene N uniones; cada una se arma y (salvo FW) se suelda. FW es solo-ARM; BW/BR/SO/FILL/LET requieren soldadura | `validation_service.py`, hoja Uniones |
| E2 | SOLD de una unión requiere su ARM completado | `validation_service.py`, `exceptions.py:471-493` (`ArmPrerequisiteError`) |
| E3 | FINALIZAR auto-determina CANCELADO / PAUSAR / COMPLETAR según cuántas uniones se completaron | `_determine_action`, `occupation_service.py:822-897` |
| E4 | Metrología APROBADO/RECHAZADO tras completar soldadura; auto-trigger cuando todo el trabajo soldable está hecho | `metrologia_service.py` |
| E5 | Reparación en ciclos acotados: máximo 3, luego BLOQUEADO | `reparacion_service.py`, `cycle_counter_service.py` |
| E6 | Métrica pulgadas-diámetro = suma de DN_UNION de uniones completadas | contadores en Operaciones (la *métrica* es esencial; *almacenarla* es accidental) |
| E7 | Trail de auditoría inmutable, append-only (requisito regulatorio) | hoja Metadata, `metadata_repository.py` |
| E8 | Ocupación: un spool lo trabaja una persona a la vez (TOMAR/INICIAR lo marca, PAUSAR/FINALIZAR lo libera) | `Ocupado_Por`/`Fecha_Ocupacion` |
| E9 | Ingeniería edita datos maestros a mano (alta de spools/uniones, corrección de DN/tipo). **Es una feature real, no un accidente** | el hecho de que la verdad viva en una hoja editable |
| E10 | Confirmación en dos pasos para INICIAR/FINALIZAR: las escrituras ocurren solo al confirmar | flujo P5, `union_router.py` |

### 2.2 Complejidad accidental (pelea contra la herramienta o contra el propio diseño)

| # | Síntoma | Evidencia | Raíz |
|---|---------|-----------|------|
| A1 | Contadores almacenados (`Total_Uniones`, `Uniones_ARM/SOLD_Completadas`, `Pulgadas_*`) que driftean | `sheet_schema.py:64-73` | estado derivado almacenado |
| A2 | `Estado_Detalle` como string construido a mano y parseado por regex en 3 lugares | `estado_detalle_builder.py` (132), `estado_detalle_parser.py` (118), frontend `api.ts:327-334` | un string de display usado como dato |
| A3 | `Fecha_Armado/Soldadura` duplicando `max(ARM/SOL_FECHA_FIN)` de Uniones | `occupation_service.py:1820-1830` | estado derivado almacenado |
| A4 | Reconciliación defensiva `_reconcile_completion_columns` | `occupation_service.py:973-1084`, invocada en `:1390` y `:1783` (T-240/T-241) | existe SOLO porque A1+A3 driftean |
| A5 | Guard T-021: re-verificar `ya_completadas + selected_count > total_uniones_spool` | `occupation_service.py:878-879` | defensa contra A1 |
| A6 | Detección de versión por TAG_SPOOL con fail-safe | `occupation_service.py:1171-1202`, marcadores T-096 en `:619, :1023, :2165` | dualidad de modelo + OT como FK frágil entre hojas |
| A7 | Guards `[ARM_FALLBACK_OK]` y `[H2_GUARD_*]` para spools híbridos (ARM a nivel spool, SOLD a nivel unión) | `validation_service.py:252, :307-355` | dualidad de modelo |
| A8 | `SpoolDataCorruptError` por fechas serial-Excel ("1900-01-06") | `exceptions.py:41-66` (B-001/B-002) | auto-formato de Sheets |
| A9 | Mapeo dinámico header→índice con SHA256 + threading lock + 503 por columna crítica | `column_map_cache.py` (443 líneas) | Sheets no tiene schema |
| A10 | Caches TTL por hoja (Operaciones 60s; Uniones/Trabajadores 300s tras incidente 429 del 2026-05-08) | `sheets_repository.py:251-255` | cuota 60 writes/min |
| A11 | Retry con backoff exponencial | `sheets_repository.py:29-63` (backoff en `:52`) | errores 429/transitorios de Sheets |
| A12 | Parseo dual de fechas (string DD-MM-YYYY *y* serial Excel) | `sheets_repository.py:222` (UNFORMATTED_VALUE), `sheets_service.py:220-345` | auto-formato de Sheets |
| A13 | Máquinas de estado a medio usar: ARM/SOLD hidratadas para TOMAR/PAUSAR/COMPLETAR (`state_service.py:18-19, :418, :490`) pero **cero referencias en el hot path FINALIZAR** (`occupation_service.py:1087-2315` arma Estado_Detalle a mano) | verificado 2026-06-10 | una abstracción que el camino principal esquiva no garantiza nada |
| A14 | Concurrencia vestigial: `conflict_service.py` (135 líneas) cuyo docstring (`:3-8`) admite "version column removed… Last-Write-Wins" | verificado | sobre-diseño para multi-worker que no existe |
| A15 | Frontend espejo: `spool-state-machine.ts` (107), `error-classifier.ts` (132, conoce 1 de 20+ códigos), `SpoolListContext.tsx` (437, migración localStorage en 3 capas, T-242), parsing `"MR(93)"` en `page.tsx:71-74` | verificado | el backend no expone estado computado ni acciones válidas |
| A16 | Superficie: 15 routers / 34 endpoints / 20 clases de servicio; FINALIZAR cruza ~9 capas | `backend/routers/`, `backend/services/` | capas heredadas de una ambición multi-user |

**Lectura clave:** A4 y A5 están *justificados hoy* — mientras exista estado duplicado, los
guards son lo único que evita corromper PROD de nuevo. No hay que borrarlos primero; hay que
eliminar la razón de su existencia (A1/A3) y entonces caen solos.

---

## 3. Cuellos de botella priorizados (impacto × esfuerzo)

Separando el **impuesto Sheets** (columna S) de la **deuda de diseño propia** (columna D):

| Prioridad | Cuello de botella | Tipo | Impacto | Esfuerzo de eliminar |
|---|---|---|---|---|
| 1 | Sin transacciones: FINALIZAR = 6-11 escrituras/lecturas API independientes; falla parcial = estado inconsistente (la fábrica de bugs) | S | Crítico — es el origen de T-240/T-241 y del audit del 2026-06-05 | Alto (requiere cambiar storage) — pero es EL cambio que paga todo lo demás |
| 2 | Estado derivado almacenado (contadores, fechas, Estado_Detalle) | D | Crítico — origen de T-021, T-096, reconciles | Medio — computar on-read puede empezar HOY sobre Sheets (Fase 0) |
| 3 | Dualidad v2.1/v3.0 vs v4.0 con detección de versión | D | Alto — cada flujo nuevo debe considerar 3 ramas | Medio — colapsa con el modelo único (§6) |
| 4 | Latencia: 200-500 ms × llamada → 1-4 s por FINALIZAR; cuota 60 writes/min ya causó un incidente | S | Alto — UX en planta y techo de escala | Cae con el punto 1 |
| 5 | Frontend espejo (estado, errores, parsing de strings) | D | Medio-alto — cada cambio de backend rompe silenciosamente el front | Bajo — backend expone `estado` + `valid_actions` + errores estructurados |
| 6 | Mapeo dinámico de columnas + parseo de fechas + retry (2.836 líneas) | S | Medio — costo de mantenimiento permanente, B-001/B-002 | Cae con el punto 1 |
| 7 | Superficie API/servicios (34 endpoints, 20 servicios, 9 capas) | D | Medio — fricción de desarrollo, onboarding | Medio — rediseño de API (§4) |
| 8 | Concurrencia vestigial | D | Bajo — confunde, no rompe | Trivial — borrar |

---

## 4. Arquitectura propuesta

### 4.1 Principio rector

**Almacenar solo hechos; computar todo lo demás en lectura.** Un hecho es algo que ocurrió:
"la unión 3 del spool X terminó su ARM el 10-06 a manos del worker 93". Un estado
("EN_PROGRESO 4/7", "12.5 pulgadas ARM") es una *vista* sobre los hechos. Hoy ZEUES almacena
las vistas, y por eso necesita reconciliadores; mañana las vistas se computan y no pueden
driftar.

### 4.2 Datos: 4 tablas de hechos

| Tabla | Contenido | Reemplaza |
|---|---|---|
| `spools` | Identidad + datos maestros: `tag_spool` PK, `ot`, `nv`, `split`, `fecha_materiales`, `notas`, `legacy_fecha_armado`, `legacy_fecha_soldadura` | columnas de identidad de Operaciones |
| `uniones` | `id`, `tag_spool` FK, `n_union`, `dn_union`, `tipo_union`, `arm_fecha_inicio/fin`, `arm_worker`, `sol_fecha_inicio/fin`, `sol_worker`, campos NDT | hoja Uniones (sin la columna `version`, muerta) |
| `ocupaciones` | `tag_spool` UNIQUE, `worker_id`, `operacion`, `modo` (directo/confirmación), `fecha_ocupacion` | `Ocupado_Por` + `Fecha_Ocupacion` |
| `eventos` | Append-only; mismos campos que el evento Metadata actual + columna `source`; UPDATE/DELETE bloqueados por trigger | hoja Metadata |

Más `trabajadores` y `roles` (triviales, igual que hoy).

**Todo lo demás se computa:** `Estado_Detalle` → `derive_estado(...)`; contadores →
`COUNT(*)`; pulgadas → `SUM(dn_union)`; `Fecha_Armado/Soldadura` → `MAX(fecha_fin)`;
ciclo de reparación → `COUNT(eventos REPARACION_INICIO)` (máx 3 → BLOQUEADO es un conteo,
no un contador almacenado).

### 4.3 Capas: de 9 saltos a 3

```
ANTES (FINALIZAR, hoy — 9 saltos, 6-11 llamadas API, sin transacción):

union_router.py:218 ──► occupation_service.finalizar_spool (:1087)
                            │ detección de versión (T-096, :1171-1202)
                            ▼
                        validation_service (guards ARM_FALLBACK / H2)
                            ▼
                        union_repository.get_by_spool / get_disponibles_*   [READ Uniones ×2-3]
                            ▼
                        sheets_repository.get_spool_by_tag                  [READ Operaciones ×2]
                            ▼
                        ColumnMapCache.get_or_build (SHA256 + lock)
                            ▼
                        sheets_repository.batch_update_by_column_name       [WRITE Uniones]
                            ▼
                        _reconcile_completion_columns (:1390/:1783)         [WRITE Operaciones]
                            │ estado_detalle_builder (string a mano)
                            ▼
                        MetadataEventBuilder ──► metadata_repository        [APPEND Metadata]
                            ▼
                        Google Sheets API  ←— cualquier falla intermedia = estado inconsistente


DESPUÉS (FINALIZAR propuesto — 3 saltos, 1 transacción):

router ──► domain/spools.finalizar(tag, worker, operacion, uniones_sel)
               ▼
           db: BEGIN IMMEDIATE
               ├─ assert ocupación pertenece al worker        (precondición)
               ├─ UPDATE uniones seleccionadas (fecha_fin, worker)
               ├─ acción = derivar(completadas vs total)      (E3, misma regla)
               ├─ DELETE ocupación
               └─ INSERT evento(s)                            (E7, mismo trail)
           COMMIT  ←— falla = rollback limpio, nada a medio escribir
               ▼
           return { estado: derive_estado(...), valid_actions: [...] }
```

### 4.4 API mínima: 3 routers, ~11 endpoints

| # | Endpoint | Reemplaza (de los 34 actuales) |
|---|---|---|
| 1 | `GET /api/spools?filter=…` — lista con `estado` computado, `valid_actions[]`, contadores, pulgadas | `spools/iniciar`, `spools/ocupados`, `spools/reparacion`, `dashboard`, `spool_status`, `batchGetStatus` |
| 2 | `GET /api/spools/{tag}` — detalle + uniones (disponibles/completadas por operación) | `uniones/{tag}/disponibles`, `/todas`, `/metricas` |
| 3 | `POST /api/spools/{tag}/ocupar` `{worker_id, operacion, modo}` — TOMAR e INICIAR | iniciar v4, tomar, tomar-reparación |
| 4 | `POST /api/spools/{tag}/liberar` `{worker_id}` — PAUSAR directo / cancelar | variantes pausar/cancelar |
| 5 | `POST /api/spools/{tag}/finalizar` `{worker_id, operacion, uniones[]}` — el server deriva CANCELADO/PAUSAR/COMPLETAR | finalizar v4, completar-reparación |
| 6 | `POST /api/spools/{tag}/metrologia` `{veredicto}` | metrología/completar |
| 7 | `PUT /api/spools/{tag}/notas` | notas GET/POST |
| 8 | `GET /api/spools/{tag}/historial` | history (supervisor audit/legacy-snapshot **se eliminan**, decisión #5) |
| 9 | `GET /api/workers` | workers (`mi-registro`/registro_router **se eliminan**, decisión #5) |
| 10 | `POST /api/admin/sync-master` — sincronizar hoja intake + disparar export | admin, scripts de validación de schema |
| 11 | `POST /api/spools/{tag}/corregir` `{worker_id, campo, valor}` — **rol supervisor/admin**; escribe el cambio + un evento de corrección auditable | (nuevo — decisión #1; reemplaza la edición manual de ejecución en la hoja) |

**Contratos clave:**
- Toda respuesta de mutación devuelve `{estado, valid_actions}` recomputados → el frontend
  nunca deriva nada.
- Errores estructurados: `{code, message_es, severity, retryable}` → muere el clasificador
  por HTTP status del frontend.
- **Corrección (#11) es el único endpoint con control de rol.** Decisión #1: "no todos los
  usuarios deberían tener derecho a corregir". El resto de la app no necesita permisos finos
  (escala de ~12 usuarios, confianza alta). La corrección nunca sobreescribe en silencio:
  aplica el cambio *y* registra un evento `CORRECCION` (campo, valor viejo → nuevo, quién),
  preservando la inmutabilidad del trail.

Estructura backend resultante (~4-5 módulos en lugar de 20 servicios):

```
backend/
├── main.py
├── routers/        spools.py, workers.py, admin.py
├── domain/         spools.py (comandos), estado.py (derive_estado + valid_actions),
│                   eventos.py (builder de auditoría)
├── db.py           conexión, transacciones, schema  (~300 líneas; única pieza que
│                   cambiaría si algún día se migra a Postgres)
└── sync/           intake_sheet.py, export_sheet.py
```

### 4.5 Frontend: dejar de simular al backend

| Se elimina | Líneas hoy | Por qué existía |
|---|---|---|
| `spool-state-machine.ts` | 107 | re-derivaba estado en el cliente |
| Regex de `Estado_Detalle` (`api.ts:327-334`) + parsing `"MR(93)"` (`page.tsx:71-74`) | ~80 | parseaba un string de display como dato |
| `error-classifier.ts` (heurística por HTTP status) | 132 → ~30 | el backend ahora manda `{code, message_es, severity, retryable}`; el front solo renderiza |
| Migración localStorage 3 capas en `SpoolListContext.tsx` | 437 → ~150 | localStorage era una segunda fuente de verdad; la lista del server pasa a ser la única (localStorage queda solo para `{worker_id, prefs UI}`) |
| `api.ts` 29 funciones | 1.188 → ~400 | espejaba 34 endpoints; con 10 quedan ~12 funciones tipadas |
| Orquestación en `page.tsx` | 1.264 → ~600 | la mayor parte del branching era "¿en qué estado estoy realmente?" — lo responde `valid_actions` |

La UI visible (modales, cards, flujo de confirmación P5, touch targets) **no cambia**. Solo se
adelgaza la capa de datos. Estimado: 13.557 → ~8.000 líneas.

---

## 5. Decisión: ¿Sheets o base de datos?

### 5.1 Tabla de trade-offs

| Criterio | Sheets (status quo, adelgazado) | **SQLite en volumen Railway** | Railway Postgres |
|---|---|---|---|
| Atomicidad de FINALIZAR | Nunca. 6-11 llamadas sin transacción (la realidad de hoy) | 1 transacción `BEGIN IMMEDIATE`, <10 ms | 1 transacción |
| Código que muere | ~0 — el impuesto es inherente: las **2.836 líneas se quedan** (mapeo de columnas, SHA256+lock, TTL caches, retry/backoff, parseo serial-Excel, 503 por columna) | Las ~2.836 líneas mueren; las reemplaza un `db.py` de ~300 líneas + schema | Igual que SQLite, + tooling de migraciones y pool de conexiones |
| Latencia por operación | 200-500 ms × 6-11 llamadas (1-4 s por FINALIZAR) | <10 ms | 5-20 ms |
| Rate limits | 60 writes/min (ya causó el incidente 429 del 2026-05-08 → los caches TTL) | No hay | No hay |
| Clase de bugs B-001/B-002 (fechas serial-Excel) | Permanente | Imposible (tipos reales) | Imposible |
| Edición manual de ingeniería | Nativa | Vía hojas intake/export (§5.2) | Igual |
| Carga operativa (mantenedor solo) | Ninguna extra | Volumen + script de dump nocturno | +1 servicio gestionado, credenciales, costo menor; backups gestionados |
| Backup | Implícito de Google | `.backup` nocturno + CSV a Google Drive con la **service account ya provisionada** | Backups automáticos de Railway |
| Escala real (decisión #4: máx. ~3 simultáneos, ~12 totales) | Sobra capacidad, pero arrastra todo el impuesto | **WAL + `BEGIN IMMEDIATE` cubre 3 escritores concurrentes sin esfuerzo** — el multi-worker no es trabajo futuro, viene gratis | Sobredimensionado: paga un servicio gestionado por concurrencia que no se necesita |

### 5.2 La feature real: ingeniería edita a mano

Hoy la hoja es la base de datos y el código se defiende de los humanos. La inversión
propuesta: **la hoja pasa a ser la interfaz de ingeniería, y la base de datos se defiende
sola.** Dos hojas con roles distintos, ninguna fuente de verdad de ejecución:

1. **Hoja intake (ingeniería ESCRIBE):** siguen cargando y corrigiendo datos maestros
   (spools nuevos, uniones, DN, tipo) exactamente como hoy. Un job de sync (botón en el
   dashboard + programado) hace upsert hacia `spools`/`uniones` **solo para filas sin hechos
   de ejecución**; ediciones que chocan con uniones ya ejecutadas se *reportan* en vez de
   aplicarse en silencio.
2. **Hoja reporte (read-only):** cada N minutos / a demanda, el backend exporta la vista
   computada completa — las mismas columnas que ven hoy (Estado, contadores, pulgadas,
   fechas). Ingeniería no pierde nada visualmente; gana una hoja que **nunca está mal**,
   porque es un render, no un store.

Para corregir datos de *ejecución* mal cargados (no maestros), ingeniería/supervisión NO usa la
hoja: usa el endpoint de corrección con rol (§4.4 #11, decisión #1), que registra el cambio en
el trail. Así la hoja intake queda limitada a datos maestros y la corrección de ejecución queda
auditada.

### 5.3 Recomendación: SQLite en volumen Railway

Decisión #4 confirma la escala real: **máx. ~3 usuarios simultáneos, ~12 totales**. Eso está
órdenes de magnitud por debajo del punto donde Postgres se justificaría. SQLite con WAL maneja 3
escritores concurrentes sin esfuerzo (los lectores nunca bloquean), así que el "modo
multi-worker" no es trabajo futuro: viene cubierto desde el día uno. Postgres solo agregaría un
servicio gestionado, credenciales y costo para comprar concurrencia que no se necesita. El
escape hatch SQLite→Postgres queda igual de mecánico (mismo SQL, mismo schema, cambiar `db.py`)
por si la escala alguna vez sorprende — pero no se paga por adelantado.

**Historia de backup (decisión #6):** dump nocturno (`sqlite3 .backup`) + CSV por tabla subido a
Google Drive con la service account existente; la hoja de reporte es además una réplica
humano-legible continuamente fresca. Como la responsabilidad arranca en Sebastián pero el
objetivo es traspasarla a Matías (no-dev), el job se diseña **operable sin leer logs**: un
indicador visible de "último backup OK / fecha" y una alerta clara cuando falla, no solo una
línea en consola.

**Qué se pierde honestamente:** (a) la edición directa de datos de *ejecución* en la hoja — se
reemplaza por el endpoint de corrección auditado (§4.4 #11); (b) "cero infraestructura" — ahora
hay un archivo de datos del que hacer backup (mitigado arriba); (c) la inspección casual del
dato crudo en la hoja — la cubre la hoja de reporte.

---

## 6. Modelo de estado único

### 6.1 Colapsar v2.1/v3.0/v4.0 en UN modelo

El modelo único es **v4.0: la unión es la unidad de trabajo**. Las versiones dejan de ser una
propiedad detectada por heurística (TAG_SPOOL, T-096) y pasan a ser una propiedad evidente de
los datos:

- **Spools legacy (v2.1/v3.0, sin filas de uniones):** migrar `Fecha_Armado`/`Fecha_Soldadura`
  a `spools.legacy_fecha_armado/_soldadura` como **hechos históricos congelados**.
  `derive_estado` hace short-circuit: spool con 0 uniones y fechas legacy → estado derivado de
  esas fechas (ambas presentes → COMPLETADO). Contribuyen 0 a pulgadas (nunca contribuyeron a
  nivel unión).
- **NO sintetizar pseudo-uniones** para los legacy. Dos razones: una unión fabricada no tiene
  `DN_UNION` real (corrompería la métrica de pulgadas o exigiría un DN falso), e inventar
  registros en un sistema de trazabilidad regulado es exactamente lo que un auditor marca.
- Con esto mueren: `version_detection_service.py`, las ramas `is_v21` (`:623`) / `is_v30`
  (`:1202`), los fallbacks híbridos `[ARM_FALLBACK_OK]`/`[H2_GUARD_*]`, y la detección T-096
  completa.

### 6.2 Derivación pura en lugar de máquinas de estado

`python-statemachine` hoy custodia TOMAR/PAUSAR/COMPLETAR, Metrología y Reparación — pero
**no el hot path FINALIZAR v4.0** (cero referencias en `occupation_service.py:1087-2315`).
Una máquina de estados que la transición principal esquiva es documentación, no garantía.
Recomendación: **eliminar la librería** y reemplazarla por dos funciones puras:

```
derive_estado(spool, uniones, ocupacion, eventos) -> EstadoSpool     (~100-120 líneas)
valid_actions(estado, ocupacion, worker?)        -> list[Accion]     (~40 líneas)
```

Reglas que codifican (hoy dispersas en 6 representaciones): FW solo-ARM y excluidas del total
SOLD; SOLD disponible solo tras su ARM; metrología pendiente cuando todas las uniones soldables
están completas; veredicto = último evento de metrología; reparaciones ≥ 3 → BLOQUEADO.

La **legalidad de las transiciones** se garantiza con precondiciones al inicio de cada comando
de dominio (`ocupar` verifica que no haya ocupación; `finalizar` verifica ownership), **dentro
de la misma transacción** que aplica el cambio. Eso es más fuerte que la máquina actual,
porque no se puede esquivar. Y como `derive_estado` la usan idénticamente la lista, el detalle
y cada respuesta de mutación, frontend y backend no pueden estar en desacuerdo.

### 6.3 Frontera de concurrencia (explícita y desactivable)

**Se borra ya (vestigial):** `conflict_service.py` (135 líneas), `models/conflict.py`,
restos de la columna `version` en Uniones y su parsing, todo stub de optimistic locking.

**Se conserva (cubre la escala real de decisión #4 — ~3 simultáneos / ~12 totales):** la tabla
`ocupaciones` con `UNIQUE(tag_spool)` — la forma relacional de `Ocupado_Por`. Un conflicto de
ocupación es una violación de constraint → 409 estructurado. Eso es todo.

**Multi-worker no es trabajo futuro: viene resuelto desde el día uno.** Con ~3 escritores
simultáneos, SQLite en modo WAL + `BEGIN IMMEDIATE` los serializa correctamente (los lectores
nunca bloquean) sin ninguna maquinaria extra. No hay que diseñar "modo single" y "modo multi"
por separado: el mismo código sirve para ambos a esta escala.

**Escape hatch (por si la escala alguna vez sorprende, cambio acotado y no reescritura):** swap
de `db.py` a Postgres + `SELECT FOR UPDATE` sobre la fila del spool. Las funciones de dominio, el
contrato de API y el frontend no se tocan. La concurrencia queda confinada a **un módulo**
(`db.py`), no tejida en 20 servicios como en v3.0.

---

## 7. Ruta de migración por fases (producción, sin big-bang)

| Fase | Qué se hace | Coexistencia / rollback |
|---|---|---|
| **0 — Derive-on-read sobre la API actual** (Sheets sin cambios) | Implementar `derive_estado` + `valid_actions` en el backend; lista y detalle los devuelven; el frontend los consume y borra su máquina de estados, el clasificador heurístico y el parsing de strings. Se deja de *confiar* en las columnas derivadas almacenadas (se siguen escribiendo para la vista de ingeniería) | Riesgo casi nulo; totalmente reversible; mata de inmediato la clase de bug más grande (desacuerdo frontend/backend) |
| **1 — SQLite en sombra** | Crear schema; script de migración one-shot del **estado vivo**: Operaciones → `spools` (fechas legacy preservadas, §6.1), Uniones → `uniones`. **La Metadata histórica NO se migra** (decisión #3): `eventos` arranca vacío y se llena con los eventos nuevos desde este punto. Dual-write: cada mutación escribe DB primero, Sheets después (best-effort). Job nocturno de diff reporta divergencias. Correr 1-2 semanas | La hoja Metadata vieja se **archiva read-only** (no se borra) por si un auditor pide historia pre-cutover — pero sale del sistema. Rollback: apagar dual-write |
| **2 — Cutover de lecturas + export/intake** | Lecturas servidas desde SQLite. Las escrituras a Sheets se reemplazan por el job de export (DB → hoja reporte read-only) + sync de intake para los datos maestros. Se habilita el endpoint de corrección con rol (#11). Se dan de baja las superficies vestigiales (supervisor audit/legacy-snapshot, `mi-registro` — decisión #5). La hoja PROD sale del camino de escritura | Rollback: volver las lecturas a Sheets — el dual-write la mantuvo al día |
| **3 — Borrar el legacy** | Eliminar `sheets_repository`, `column_map_cache`, `sheets_service`, retry/backoff, manejo de corrupción de fechas, trío estado_detalle, detección de versión, conflict_service, ~24 endpoints, código muerto del frontend | Aquí ocurre de verdad 25.923 → ~4.500 líneas. Es solo borrado: el sistema ya corre en el modelo nuevo desde Fase 2 |
| **4 — Hardening (opcional)** | Backup a Drive operable por no-dev (indicador "último backup OK" + alerta clara, decisión #6) y verificado con test de restore; hash-chain sobre `eventos` si el auditor quiere evidencia de no-manipulación más allá del trigger append-only | — |

**Migración de datos:** el script de Fase 1 solo migra el **estado vivo** (spools + uniones), no
historia de eventos (decisión #3), y es idempotente (se puede correr N veces contra la sombra
antes del cutover). Los ~15 spools del audit cross-sheet del 2026-06-05 deben resolverse (o
marcarse) *antes* de la Fase 1 — el script debe validar integridad TAG_SPOOL↔uniones y reportar
huérfanos en vez de migrarlos en silencio.

---

## 8. Riesgos, qué NO tocar y decisiones tomadas

### 8.1 Qué NO tocar (esencial — la lista E1-E10 de §2.1)

- Las reglas FW/BW, prerequisito ARM→SOLD, auto-determinación de FINALIZAR, metrología,
  reparación máx 3, pulgadas-diámetro: se **reimplementan idénticas**, no se simplifican.
- El trail de auditoría: append-only e inmutable sigue siendo requisito; cambia el *cómo*
  (tabla `eventos` con trigger anti-borrado, **solo en la DB** — decisión #2), no el *qué*.
- El flujo de confirmación en dos pasos (P5) y la UX de tablet: intocados.
- La capacidad de ingeniería de editar datos maestros a mano: preservada vía hoja intake.
- **Los guards T-021 y los reconciles T-240/T-241 NO se borran en Fase 0-1.** Caen en Fase 3,
  cuando el estado duplicado que defienden ya no existe. Borrarlos antes re-abriría las
  heridas que cerraron.

### 8.2 Riesgos principales

| Riesgo | Mitigación |
|---|---|
| El script de migración traduce mal datos legacy (fechas serial-Excel, OT drifteadas, los ~15 spools del audit) | Fase 1 en sombra con job de diff; validación de integridad con reporte de huérfanos; la hoja vieja queda congelada como referencia |
| Ingeniería rechaza perder escritura directa sobre ejecución | Resuelto (decisión #1): endpoint de corrección con rol que audita el cambio. Validar el flujo con ellos en Fase 1; habilitarlo en Fase 2 |
| Pérdida del volumen Railway sin backup probado | El test de restore es parte de la definición de "hecho" de Fase 2, no un opcional |
| El dual-write de Fase 1 introduce divergencias propias | DB primero (verdad), Sheets después (best-effort) + diff nocturno; las divergencias se *esperan* y se miden, no se descubren |
| Scope creep: rediseñar UI al mismo tiempo | Este informe propone explícitamente NO tocar la UX; el rediseño es de la capa de datos |

### 8.3 Decisiones tomadas (Sebastián, 2026-06-10)

Las preguntas abiertas originales ya fueron respondidas. Quedan registradas como decisiones
firmes (resumen en §0; cómo impactan, en las secciones citadas):

1. **Corrección de datos de ejecución → SÍ, con rol.** *"Hay que estar preparados cuando un
   trabajador ingrese mal un dato y sea necesario corregirlo. No todos los usuarios deberían
   tener derecho a corregir."* → Endpoint `POST /spools/{tag}/corregir` con rol supervisor/admin
   que aplica el cambio y registra un evento `CORRECCION` auditable; nunca edición silenciosa
   (§4.4 #11, §5.2).
2. **Trail de auditoría → solo en la DB, fuera de Sheets.** *"Le da igual la metadata, podría
   perfectamente no vivir en el gsheets, la metadata es para los dev."* → La tabla `eventos`
   (con trigger anti-borrado) es el único trail; se elimina todo espejado a una hoja (§8.1).
3. **Metadata histórica → no migrar, empezar de cero.** *"Partamos desde cero, la metadata
   anterior no me suma."* → La Fase 1 migra solo estado vivo; `eventos` arranca vacío. La hoja
   vieja se archiva read-only por las dudas (§7).
4. **Escala → SQLite confirmado.** *"Máximo habrán 3 usuarios simultáneos, y máximo como 12
   usuarios que utilicen la app."* → SQLite + WAL cubre la concurrencia desde el día uno; no se
   paga Postgres (§5.3, §6.3).
5. **Superficies vestigiales → eliminar.** *"No se utiliza."* (supervisor audit-batch/
   legacy-snapshot y `mi-registro`) → se dan de baja en Fase 2; se borra su código (§4.4, §7).
6. **Backup → Sebastián ahora, Matías después.** *"Yo me haré responsable pero con el objetivo
   de pasar esa responsabilidad a Matías."* → El job de backup se diseña operable por no-dev
   (indicador "último backup OK" + alerta clara), no solo legible en logs (§5.3, Fase 4).
7. **Persistir contadores por rendimiento → NO** (decisión técnica, no requería al dueño). Con
   SQLite un `COUNT`/`SUM` es sub-milisegundo; almacenarlos solo reintroduce el drift. Se deja
   registrada por si alguien la re-propone.

---

## Apéndice: números antes/después (estimados)

| Métrica | Hoy (verificado 2026-06-10) | Propuesto |
|---|---|---|
| Backend (líneas Python) | 25.923 | ~4.500 |
| Frontend (líneas TS/TSX) | 13.557 | ~8.000 |
| Endpoints | 34 (15 routers) | ~11 (3 routers) |
| Clases de servicio / módulos | 20 | ~4-5 |
| Saltos de un FINALIZAR | ~9 capas | 3 |
| Llamadas de storage por FINALIZAR | 6-11 (sin transacción) | 1 transacción (~4 statements) |
| Latencia FINALIZAR | 1-4 s | <50 ms |
| Representaciones del estado de un spool | 6 (driftean) | 1 fuente de hechos + 1 función de derivación |
| "Impuesto Sheets" | ~2.836 líneas | ~300 (`db.py`) + jobs intake/export |
| Líneas defendiendo drift (guards/reconciles/detección de versión) | ~600+ | 0 (el drift es imposible por construcción) |
