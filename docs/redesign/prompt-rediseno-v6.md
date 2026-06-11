# Prompt de rediseño ZEUES v6 — para modelo Anthropic nuevo

**Qué es:** prompt listo para pegar a un modelo nuevo (sesión fresca, con acceso a este
repo) para que produzca un **informe de rediseño** hacia una versión radicalmente más
simple de ZEUES. No produce código: produce un documento de decisión.

**Cómo usarlo:** copiar las dos secciones siguientes — "EL PROMPT" y "Anexo: evidencia
verificada" — como primer mensaje de la sesión nueva.

**Evidencia:** el anexo fue verificado contra el código real el **2026-06-10**
(commit base `fdc275b`). Las líneas citadas son exactas a esa fecha; el prompt instruye
al modelo a re-verificar antes de afirmar.

---

## EL PROMPT (copiar/pegar al modelo nuevo)

> Sos un arquitecto de software senior. Vas a revisar **ZEUES**, una app de
> trazabilidad de *spools* de tubería en manufactura, y producir un **informe
> de rediseño hacia una versión mucho más simple**. NO escribas código todavía:
> el entregable es un documento de decisión.
>
> ### Qué es ZEUES (contexto de dominio)
> - Rastrea spools de tubería a través de dos operaciones: **ARM** (armado/
>   ensamblado) y **SOLD** (soldadura), más inspección **Metrología** y ciclos
>   de **Reparación**.
> - Un spool tiene N *uniones* (joints). Cada unión se arma y se suelda. Algunas
>   uniones tipo **FW** solo se arman (no se sueldan); el resto (BW/BR/SO/FILL/
>   LET) requieren soldadura.
> - Flujos: TOMAR/PAUSAR/COMPLETAR (directo) e INICIAR/FINALIZAR (con
>   confirmación; FINALIZAR auto-determina CANCELADO/PAUSAR/COMPLETAR según
>   cuántas uniones se completaron). Métrica de negocio: *pulgadas-diámetro*
>   (suma de DN de uniones completadas).
> - **Stack actual:** FastAPI (Python) + Next.js (TypeScript) + Google Sheets
>   como única fuente de verdad (sin base de datos). Deploy en Railway + Vercel.
> - **Escala real HOY:** 1 tablet, 1 trabajador a la vez, en planta. Objetivo
>   declarado en docs: 30-50 trabajadores, 2000+ spools — pero eso NO es la
>   realidad operativa actual.
>
> ### Tu misión
> Producir un informe que permita al dueño decidir cómo construir una versión
> **radicalmente más simple** del MISMO sistema (mismas capacidades de negocio,
> mucho menos accidente técnico). Tenés libertad para cuestionar decisiones de
> fondo, incluido **reemplazar Google Sheets por una base de datos** si lo
> justificás.
>
> ### Restricciones y supuestos que debés respetar
> 1. **No escribas el sistema.** Entregá un INFORME (texto + diagramas en
>    ASCII/markdown si ayudan). El dueño implementará después.
> 2. **Concurrencia:** hoy es 1 tablet / 1 worker, pero el cliente *podría*
>    escalar a multi-worker. NO asumas multi-user en todo el diseño (eso es
>    justamente parte del exceso actual), pero **aislá** la concurrencia como
>    una decisión explícita y desactivable, de modo que volver a multi-worker
>    sea un cambio acotado y no una reescritura.
> 3. **Preservá las reglas de negocio reales.** Antes de simplificar, separá
>    explícitamente **complejidad esencial** (reglas del dominio que el negocio
>    necesita) de **complejidad accidental** (parches, duplicación, peleas
>    contra la herramienta). Lista ambas.
> 4. **Auditoría regulatoria:** existe un trail de eventos inmutable (hoja
>    Metadata, append-only). Trátalo como requisito, no como accidente — pero
>    podés rediseñar CÓMO se implementa.
> 5. **Trazá una ruta de migración por fases.** El sistema está en producción;
>    no puede haber un big-bang sin red. Incluí cómo coexistirían viejo y nuevo,
>    y cómo migrar los datos que hoy viven en Sheets.
>
> ### Material que vas a recibir
> Tenés acceso al repositorio. Empezá por `CLAUDE.md` (mapa del proyecto) y por
> el "Anexo: evidencia" que acompaña este prompt — un inventario ya hecho de los
> puntos de complejidad, con archivos y líneas (verificado el 2026-06-10).
> **Verificá ese anexo contra el código actual** (puede haber drift) antes de
> afirmarlo como hecho.
>
> ### Preguntas que tu informe DEBE responder
> 1. **Cuellos de botella reales.** ¿Qué duele de verdad y por qué? Distinguí
>    el "impuesto Google Sheets" (sin transacciones, 60 writes/min, latencia
>    200-500ms, auto-formato de fechas, mapeo dinámico de columnas) de la deuda
>    de diseño propia (capas, duplicación de estado, parches).
> 2. **Vicios / scar tissue.** Catalogá los parches históricos (T-021, T-096,
>    T-240/T-241, B-001/B-002, guards "defensivos", "reconcile", "legacy",
>    "fallback") y explicá qué problema de raíz revela cada uno. Si varios
>    parches atacan el mismo síntoma, nómbralo.
> 3. **Duplicación de estado.** El estado de un spool hoy se representa de
>    múltiples formas que driftean entre sí (string Estado_Detalle, contadores
>    Uniones_*_Completadas, filas de la hoja Uniones, columnas Fecha_*,
>    máquinas de estado, eventos Metadata). ¿Cuál es la fuente de verdad mínima?
>    ¿Qué columnas/representaciones son derivadas y deberían computarse, no
>    almacenarse?
> 4. **Dualidad de modelo de datos.** Hoy conviven v2.1/v3.0 (estado a nivel
>    spool) y v4.0 (estado a nivel unión), con detección de versión y ramas
>    `is_v21`/`is_v30` por todos lados. ¿Se puede colapsar a UN modelo? ¿Cuál?
> 5. **¿Sheets o base de datos?** Evaluá explícitamente mantener Sheets vs.
>    migrar a SQLite/Postgres. Cuantificá qué complejidad desaparece con cada
>    opción (ej. cuántas líneas de cache/retry/parsing de fechas se eliminan) y
>    qué se pierde (Sheets es editable a mano por ingeniería; eso es una feature
>    real para ellos). Recomendá una con trade-offs honestos.
> 6. **Superficie de API y capas.** Hoy hay 16 routers / 34 endpoints y 19
>    clases de servicio para una app single-user. Propon un set mínimo de
>    endpoints y una arquitectura de capas plana. Mostrá el "antes/después" del
>    camino de un FINALIZAR.
> 7. **Frontend.** ¿El front duplica la lógica de estado del backend (máquina de
>    estado en TS, clasificación de errores, migración localStorage)? ¿Qué se
>    simplifica si el backend es la única fuente de verdad?
> 8. **Modelo de concurrencia.** Dado el supuesto (single hoy, multi quizá),
>    diseñá la frontera: qué se borra, qué se aísla tras un flag, qué costaría
>    reactivar multi-worker.
>
> ### Forma del entregable (estructura sugerida)
> 1. Resumen ejecutivo (1 página): los 3-5 problemas raíz y la recomendación.
> 2. Inventario: complejidad esencial vs accidental (dos listas).
> 3. Cuellos de botella priorizados (impacto × esfuerzo).
> 4. Arquitectura propuesta (datos, capas, API, frontend) con diagrama antes/
>    después de un FINALIZAR.
> 5. Decisión Sheets vs DB con trade-offs y números.
> 6. Modelo de estado único propuesto (qué es fuente de verdad, qué se deriva).
> 7. Ruta de migración por fases, con coexistencia y migración de datos.
> 8. Riesgos y qué NO tocar (reglas de negocio y auditoría a preservar).
>
> ### Cómo trabajar
> - Leé el código real antes de afirmar. Citá archivo:línea.
> - Sé opinionado pero honesto: si una "complejidad" está justificada, decílo;
>   no recomiendes simplificar algo que existe por una razón de dominio.
> - No inventes requisitos. Si algo del dominio es ambiguo (p. ej. si los
>   contadores deben persistir por rendimiento), marcalo como pregunta abierta
>   para el dueño en vez de asumir.

---

## Anexo: evidencia verificada (2026-06-10, adjuntar al prompt)

Inventario de los puntos de complejidad, verificado contra el código real el
2026-06-10 (commit base `fdc275b`). Líneas exactas a esa fecha; re-verificar
contra el repo antes de afirmar (puede haber drift posterior).

**Escala total del sistema**
- Backend: **25.923 líneas** de Python (`backend/`).
- Frontend: **13.715 líneas** de TS/TSX (`zeues-frontend/`, sin node_modules).
- Todo esto para un sistema single-user con 2 operaciones (ARM/SOLD) +
  metrología + reparación.

**Hotspot central**
- `backend/services/occupation_service.py` (**2.315 líneas**) concentra
  TOMAR/PAUSAR/COMPLETAR, INICIAR/FINALIZAR (`finalizar_spool` arranca en
  línea 1087), auto-determinación de acción, reconciliación y detección de
  versión.

**Parches históricos (scar tissue) — la misma raíz, varias curitas**
- **T-021** (`_determine_action`, `occupation_service.py:822-897`; guard en
  línea 878 con re-verificación `ya_completadas + selected_count >
  total_uniones_spool` en 879): COMPLETAR se decide contra el total real de
  uniones del spool, no contra el batch disponible. Defensa contra contadores
  que driftean.
- **T-096** (detección v3.0/v4.0 por TAG_SPOOL, no por OT; marcadores en
  `occupation_service.py:1023, 1171, 2165`; rama `is_v30` en 1202): la OT de
  Uniones driftea de la de Operaciones; contar por OT mandaba spools v4.0
  reales por la rama v3.0 que escribe Fecha_* incondicionalmente y corrompió
  datos en PROD.
- **T-240/T-241** (`_reconcile_completion_columns`,
  `occupation_service.py:973-1037`; invocaciones/marcadores en 1382, 1483,
  1831): backfill defensivo cuando todas las uniones están completas pero
  `Operaciones.Fecha_Armado/Soldadura` quedó vacío (rama PAUSAR). Existe SOLO
  porque hay estado duplicado.
- **B-001/B-002** (`backend/exceptions.py:41-66`, `SpoolDataCorruptError`,
  código `SPOOL_DATA_CORRUPT` en línea 61): corrupción de fechas serial-Excel;
  surface del error al operador.
- **Cross-sheet OT mismatch** (audit 2026-06-05, ~15 spools; commit `fdc275b`):
  recién arreglado moviendo el flujo FINALIZAR/INICIAR a resolver por
  TAG_SPOOL. Es la prueba viva de que la OT como FK entre hojas es frágil.

**Duplicación de estado (raíz de los reconcile-bugs)**
- Un spool se representa por: `Estado_Detalle` (string que codifica ocupación,
  progreso X/Y, ciclo de reparación), contadores `Uniones_ARM/SOLD_Completadas`
  y `Pulgadas_ARM/SOLD` (derivables de las filas de Uniones), columnas
  `Fecha_Armado/Soldadura` (duplican el `max(ARM/SOL_FECHA_FIN)` de Uniones),
  las filas de la hoja Uniones (verdad a nivel unión) y el trail Metadata.
- `backend/core/sheet_schema.py`: las columnas `Total_Uniones`,
  `Uniones_*_Completadas`, `Pulgadas_*` son derivadas y se almacenan → driftean.

**Dualidad de modelo (v2.1/v3.0 vs v4.0)**
- Ramas `is_v21` / `is_v30` en INICIAR y FINALIZAR; detección de versión
  inlineada; fallbacks "legacy" para spools híbridos (ARM a nivel spool, SOLD a
  nivel unión). `validation_service.py` tiene guards `[ARM_FALLBACK_OK]` y
  `[H2_GUARD_*]` por la misma razón.

**Máquinas de estado (python-statemachine) — uso parcial**
- ARM/SOLD state machines (`backend/services/state_machines/`) se importan en
  `state_service.py:18-19` y se hidratan (`_hydrate_arm_machine`:418,
  `_hydrate_sold_machine`:490) para TOMAR/PAUSAR/COMPLETAR a nivel spool, pero
  **NO están en el camino caliente de FINALIZAR v4.0**: cero referencias a
  state machines en `occupation_service.py:1087-2315`, que maneja uniones y
  arma Estado_Detalle a mano. Reparación (`reparacion_service.py:19`) y
  Metrología (`metrologia_service.py:19`) sí usan máquina. Hay que decidir:
  usarlas en serio en todos lados, o eliminarlas.

**Impuesto Google Sheets (complejidad para pelear con la herramienta)**
- `backend/repositories/sheets_repository.py` (**1.532 líneas**) +
  `backend/core/column_map_cache.py` (**443 líneas**): mapeo dinámico
  header→índice con hash SHA256 y lock de threading para tolerar que
  ingeniería renombre/agregue columnas; validación de columnas críticas →
  HTTP 503.
- Caches por hoja con TTL (`sheets_repository.py:251-255`: Operaciones 60s;
  Trabajadores/Uniones 300s tras incidente de rate-limit 2026-05-08).
- Decorador `@retry_on_sheets_error` (`sheets_repository.py:29-63`, backoff
  exponencial en línea 52) por errores 429/transitorios; cuota 60 writes/min.
- Lectura `UNFORMATTED_VALUE` (`sheets_repository.py:222`) + parseo dual de
  fechas por auto-formato de Sheets (serial-Excel → "1900-01-06";
  `sheets_repository.py:1081, 1093` y `sheets_service.py:220, 287`).
- Un FINALIZAR dispara múltiples lecturas/escrituras coordinadas sin
  transacción (read → validate → write uniones → write contadores → log
  Metadata), repartidas en 4+ servicios.

**Concurrencia sobre-dimensionada para single-user**
- `Ocupado_Por`/`Fecha_Ocupacion`, columnas `version`, optimistic locking,
  `conflict_service.py` (135 líneas), LWW — maquinaria para workers
  distribuidos que hoy no existen. El propio `conflict_service.py:3-8`
  documenta "NO optimistic locking, NO Redis, Last-Write-Wins".

**Superficie**
- **16 routers / 34 endpoints** (`backend/routers/`); **19 clases de servicio**
  (`backend/services/`: OccupationService, ConflictService,
  VersionDetectionService, SheetsService, StateService, UnionService,
  WorkerService, ReparacionService, MetrologiaService, HistoryService,
  NotasService, RoleService, CycleCounterService, SupervisorService,
  EstadoDetalleService, EstadoDetalleParser, EstadoDetalleBuilder,
  MetadataEventBuilder, ValidationService).
- El camino de un FINALIZAR atraviesa ~9 capas (trazado real):
  `union_router.py:218` (endpoint) →
  `occupation_service.finalizar_spool` (:1087) →
  `sheets_repository.get_spool_by_tag` (:1152) →
  `union_repository.get_by_spool / get_disponibles_*` (:1179-1348) →
  `ColumnMapCache.get_or_build` (:1247) →
  `sheets_repository.batch_update_by_column_name` (:1268) →
  `MetadataEventBuilder` (:1285) →
  `metadata_repository.log_event` (:1294) →
  Google Sheets API.

**Frontend que espeja al backend**
- `zeues-frontend/lib/spool-state-machine.ts` (107 líneas;
  `getValidActions`:40, `deriveOperation`:75) duplica lógica de estado del
  backend.
- `zeues-frontend/lib/error-classifier.ts` (132 líneas) debe coincidir con las
  excepciones del backend.
- `zeues-frontend/lib/SpoolListContext.tsx` (437 líneas) arrastra migración
  localStorage→server en 3 capas (Layer 0 snapshot:97, Layer 1 allSettled:100,
  Layer 2 ensureMigrated:317; trabajo T-242, sin marcador explícito en código).
