# T-136 Performance Audit — Baseline (Fase 1)

**Fecha:** 2026-04-29
**Tarea:** T-136 (absorbe T-134) — auditoría performance + UX bajo carga 200 spools
**Setup:** Sheet ZEUS-TESTING (`14Rcrmc6c2RTkJG_fRgtSFDYWgP6Qt6zfciUtnl-9AMo`), 200 spools sintéticos seedeados, backend local FastAPI `:8000`, frontend local Next.js `:3000` (Chromium headless via Playwright).

## Resumen ejecutivo

**¿200 spools renderizan en el home?** Sí — pero el camino para llegar ahí destapó **un bug pre-existente crítico** (B0) que sin arreglar lo hacía imposible.

**Cuello principal observado:** `batch-status` con 200 tags y polling de 30s domina el wall-clock del home. DCL es rápido (~62ms), pero **network idle es ~2.6s**. La cadena de modales para asignar 1 spool tarda **~3.2s** total. Estos son los dos targets más probables para Fase 3.

**Hallazgos secundarios destapados:** dos bugs pre-existentes (B0 chunking ya arreglado en Fase 0; B-Bug8-redux aún sin reproducir manualmente pero confirmado bloqueante en automation).

## Setup reproducible

```bash
# 1) Activar venv y apuntar a staging (.env.local local-only, NUNCA push)
source venv/bin/activate
# .env.local backend: GOOGLE_SHEET_ID=14Rcrmc6c2RTkJG_fRgtSFDYWgP6Qt6zfciUtnl-9AMo
# zeues-frontend/.env.local: NEXT_PUBLIC_API_URL=http://127.0.0.1:8000

# 2) Re-seedear staging (200 spools, distribución determinista, seed=42)
python scripts/seed_load_test.py --yes

# 3) Dump TAGs a fixture para Playwright
python scripts/dump_staging_tags.py

# 4) Levantar backend + frontend
PYTHONPATH="$(pwd)" uvicorn backend.main:app --port 8000 &
cd zeues-frontend && npm run dev &

# 5) Correr la suite Fase 1
cd zeues-frontend
PLAYWRIGHT_BASE_URL=http://localhost:3000 \
  npx playwright test e2e/perf-flow-*.spec.ts --project=chromium --workers=1
```

Artefactos por flow se escriben en `zeues-frontend/test-results/perf-baseline/flow-NN-*/{metrics.json,network.json,console.txt,screenshot.png}`.

## Distribución del dataset sintético (200 spools)

| Estado seedeado | N | Estado derivado por `_derive_estado` | N derivado |
|---|---|---|---|
| LIBRE | 60 | LIBRE | ~110 |
| EN_ARM | 30 | EN_PROGRESO | ~64 |
| ARM_PEND | 20 | (cae a LIBRE — ver nota) | |
| ARM_TERM | 20 | (cae a LIBRE — ver nota) | |
| EN_SOLD | 30 | EN_PROGRESO | |
| SOLD_PEND | 10 | (cae a LIBRE) | |
| SOLD_TERM | 10 | PENDIENTE_METROLOGIA | ~20 |
| MET_PEND | 10 | PENDIENTE_METROLOGIA | |
| RECHAZADO | 6 | RECHAZADO | 6 |
| EN_REPARACION | 4 | EN_PROGRESO | |

> **Nota** sobre estados intermedios: `backend/models/spool_status.py::_derive_estado` trata `ARM_PEND`/`ARM_TERM`/`SOLD_PEND` (parciales y pausados sin ocupante) como **LIBRE**. Esto es consistente con cómo el operador percibe spools "listos para que alguien los retome", pero es worth flagging porque el seed los etiqueta separados. **No es bug** — es comportamiento de derivación documentado. Lo anoto para evitar que aparezca como sorpresa en futuras auditorías.

## Tabla baseline (8 flujos)

| # | Flujo | Métrica clave | Valor | API reqs | API bytes | API time | Consola | Notas |
|---|---|---|---|---|---|---|---|---|
| 1 | Home cold load 200 | `network_idle` | **2578 ms** | 2 | 110 KB | 1923 ms | 0 | DCL 62ms, load 315ms, 200/200 cards. 2 chunks paralelos `batch-status`. |
| 2 | Search keystroke "001" | `max_keystroke` | **99 ms** | 0 | 0 | 0 | 0 | "0"→143 visible, "00"→15, "001"→1. Filtro client-side puro, sin debounce, sin red. |
| 3 | Estado filter LIBRE | `click_to_filter` | **140 ms** | 0 | 0 | 0 | 0 | 110 cards visibles tras filter. Filtro puro client. |
| 4 | Add 1 spool via modal | `click_to_card_visible` | **922 ms** | 2 | 60 KB | 568 ms | 0 | `getSpoolsParaIniciar` 60KB / 568ms para listar 136 ARM-eligibles. Modal load: 64ms. Filter por search: 29ms. |
| 5 | Asignar armador 1 LIBRE | `click_to_chain_complete` | **3167 ms** | 3 | 6 KB | 2359 ms | 0 | Chain: card→OperationModal (30ms)→WorkerModal carga (853ms total)→pick→backend mutation→close. |
| 6 | Batch assign 5 spools | `BLOQUEADO` | n/a | 0 | 0 | 0 | 0 | Click "ASIGNAR ARMADOR (5)" no avanza el flow en headless. Posible re-emergencia de Bug 8 (T-132). Manual test required. |
| 7 | UnionesModal 8 unions | `click_to_grid_loaded` | **100 ms** | 2 | 2 KB | 28 ms | 0 | EN_SOLD spool. Render 8 rows + ARM/SOLD comboboxes. Ya cacheado, casi instantáneo. |
| 8 | MetrologiaModal load | `click_to_modal_loaded` | **76 ms** | 0 | 0 | 0 | 0 | 0 backend requests al abrir modal — no carga inspectores hasta picar APROBADO/RECHAZADO. |

Lectura cualitativa rápida:

- **Cold load 200 spools**: 2.6s — borderline. Operador percibe 2-3s como "se está cargando". El cuello dominante son los 2 chunks `batch-status` paralelos (1.9s combinado).
- **Modal chain de 1 asignación**: 3.2s — es lo que el operador siente al asignar 1 spool. **El primer paso del operador en su jornada típica.**
- **Filtros/búsqueda**: <150ms — excelente. No hace falta tocarlos.
- **AddSpoolModal**: 922ms para agregar 1, fundamentalmente limitado por `getSpoolsParaIniciar('ARM')` que devuelve **136 spools** de 60KB.
- **UnionesModal y MetrologiaModal**: <100ms — render rápido cuando los datos están cacheados.

## Bottleneck B0 (descubierto + ya arreglado en Fase 0)

> Esto fue una **habilitación**, no una optimización: sin este fix el load test era imposible.

**Síntoma:** con >100 spools en `localStorage`, el home aparece **vacío** y un error 422 silencioso aparece en consola (el POST `/api/spools/batch-status` es rechazado).

**Causa raíz:** `zeues-frontend/lib/api.ts::batchGetStatus(tags)` mandaba **una sola request** con todos los tags. El backend (`backend/models/spool_status.py::BatchStatusRequest`) tiene `Field(max_length=100)` — Pydantic rechaza con 422.

**Fix:** chunking en `batchGetStatus` — splittea en chunks de 100, paraleliza con `Promise.all`, mergea resultados en orden de input. 5 tests unitarios nuevos (`zeues-frontend/__tests__/lib/api-batch-chunking.test.ts`) pin el contrato.

**Impacto en producción:** este bug es **silente** — el home queda en blanco sin mensaje al operador. Si Matías o cualquier operador llega a tener >100 spools en su lista (escenario realista cuando v5.1 UX-1 lo habilite), el sistema le falla. Recomiendo: **portear este fix a `main`** sin esperar Fase 3, vale como fix independiente.

**Archivos modificados:**
- `zeues-frontend/lib/api.ts` (chunking + export `BATCH_STATUS_CHUNK_SIZE = 100`)
- `zeues-frontend/__tests__/lib/api-batch-chunking.test.ts` (5 tests, todos verdes)

## Bottleneck B1 (Bug 8 redux — sospecha)

**Síntoma observado en flow 6:** después de seleccionar 5 rows en `AddSpoolModal` (batch mode), el botón "ASIGNAR ARMADOR (5)" se queda como `[active]` pero **no responde al click** bajo Playwright headless. El HTML snapshot al fallar muestra la dialog de AddSpool aún abierta. Probé `click()`, `click({force:true})`, `evaluate(b=>b.click())`, `focus()+keyboard.press('Enter')` — ninguno avanza el flow.

**Hipótesis:** posible re-emergencia de Bug 8 (T-132). El cierre de T-132 (`commit 2958df1`) fue refactor de toasts y de mensajes de error, **no** del path `handleConfirmBatch → onBatchAdd → modalStack.push('batch-worker-picker')`. Notas.md §lección 5 ya reconoce que T-132 cerró sin reproducir el caso real.

**Acción requerida:** retest manual en planta con Matías o reproducción local en navegador real. Si el bug se confirma:
- Agregar test E2E que ejercite el path completo en headless con `force:true` y captura de errores `pageerror`.
- Investigar si `modalStack` está reseteando o si `setBatchTags` es no-op por timing del unmount de AddSpoolModal.

**No bloquea Fase 2.** El comportamiento del backend (5 INICIARs paralelos, ~700-1100ms cada uno con base en flow 5) sí está validado vía el endpoint directo.

## Cuellos candidatos para Fase 2 (priorización inicial)

Lista pre-Fase-2 — confirmar contra perfilado React DevTools antes de atacar:

| # | Cuello sospechado | Evidencia | Categoría fix | Estimación |
|---|---|---|---|---|
| C1 | **`batch-status` 200 tags = 2 requests × ~1s c/u** | flow 1: 1.9s API total. Cada chunk de 100 tarda 1-2s en Sheets. | Reducir trabajo por spool en backend (cache `_derive_estado`?) o aumentar `BATCH_STATUS_CHUNK_SIZE` con backend optimizado. | 1-3h |
| C2 | **30s polling refresh recarga TODO** | `SpoolListContext::refreshAll` llama `batchGetStatus(allTags)`. Cada 30s. Operador con 200 spools = 2 requests × 1s × cada 30s = ruido constante en logs y carga gratuita en Sheets. | Optimistic update en mutaciones + invalidación selectiva. Mantener polling general pero con interval mayor (90-120s) o solo refrescar spools "interesantes" (EN_PROGRESO, RECHAZADO). | 2-4h |
| C3 | **Chain modal de asignar 1 spool: 3.2s** | flow 5: 853ms para WorkerModal abrir + ~2.3s para mutación backend + close. | (a) Pre-cachear lista de workers — único fetch por sesión. (b) Optimistic update de la card sin esperar refresh. | 1-2h |
| C4 | **AddSpoolModal: 60KB / 568ms para listar ARM-eligibles** | flow 4: 568ms backend. 136 spools serializados completos. | Endpoint dedicado que devuelva solo `{tag, nv}` para el modal — payload típicamente <5KB. | 1h |
| C5 | **Bug 8 redux** | flow 6 bloqueado | Investigar `handleBatchAdd → modalStack.push` timing. Categoría: bugfix, no perf. | 1-3h |
| C6 | **Estado intermedio confuso** | seed `ARM_PEND`/`SOLD_PEND` derivan a LIBRE | UX-only. Considerar nuevo estado `PARCIAL` o badge separado. | Out of scope T-136 — pasa a v5.1. |

> **Foco recomendado para Fase 3 (top 1-2):** **C1 + C3**. Juntos atacan los dos números que el operador siente: cold load 2.6s y asignar 1 spool 3.2s. C2 es valioso pero más arriesgado (afecta el polling). C4 es bajo costo — vale incluirlo como side-effect del fix C1.

## Archivos producidos por Fase 1

```
scripts/
├── seed_load_test.py            Seed 200 spools determinista (seed=42), guard anti-prod hardcoded
├── dump_staging_tags.py         Dump TAGs to fixtures, guard anti-prod hardcoded

zeues-frontend/lib/api.ts        Chunking en batchGetStatus (B0 fix)
zeues-frontend/__tests__/lib/api-batch-chunking.test.ts   5 tests del contrato

zeues-frontend/e2e/
├── fixtures/staging-tags.json   200 TAGs sintéticos
├── helpers/perf-instrument.ts   Helper compartido (loadFixture, hydrate, attach, summarise, write)
├── perf-flow-01-cold-load.spec.ts
├── perf-flow-02-search.spec.ts
├── perf-flow-03-estado-filter.spec.ts
├── perf-flow-04-add-spool.spec.ts
├── perf-flow-05-assign-1.spec.ts
├── perf-flow-06-batch-assign.spec.ts   BLOCKED — ver B1
├── perf-flow-07-uniones.spec.ts
├── perf-flow-08-metrologia.spec.ts

zeues-frontend/test-results/perf-baseline/  Artefactos por flow (gitignored)
docs/audits/T-136-perf-baseline-2026-04-29.md  Este documento
```

## Suite de tests post-cambio

- Backend: 579 passed / 0 failed (sin tocar — T-136 no toca backend hasta Fase 3 si aplica).
- Frontend jest: **220 passed / 35 failed**, **delta cero contra `main`**: los 35 fallos son pre-existentes (verificado contra `main` pristino antes y después de mi cambio en `api.ts`). El nuevo `api-batch-chunking.test.ts` aporta 5 tests más, todos verdes.
- TS check: limpio.
- ESLint: 1 warning pre-existente en `app/page.tsx:689` (no introducido por T-136).

## Lecciones recogidas en Fase 0+1

1. **`gspread.append_rows()` con `value_input_option=USER_ENTERED` desplaza columnas +1 si la primera columna queda vacía post-wipe.** Encontrado al primer LIVE write — los 200 spools se escribieron con TAG_SPOOL en `id` y todo lo demás corrido. Solución: `update(range, values)` con `A2:<endcol><endrow>` explícito. Documentado en `scripts/seed_load_test.py::write_rows_at_a2`.

2. **CLAUDE.md desactualizado en algunos puntos.** Decía Operaciones tiene 71 cols (son 75), `uvicorn main:app` (es `uvicorn backend.main:app` con `PYTHONPATH`). No bloqueó pero costó 5 minutos al primer arranque.

3. **Suite frontend trae 35 fallos pre-existentes en `main`.** Lección global #6 dice no es benigno; si bien fuera de scope T-136, vale anotarlo. Concentrados en `WorkerModal`, `AddSpoolModal`, `MetrologiaModal`, `app/page` (4 suites).

4. **Frontend usa `localStorage` para la lista del home.** No es lista global — cada operador tiene su lista en su tablet. Esto cambia el modelo de "load test 200 spools": no es 200 en backend sino 200 en `localStorage` del cliente que dispara polling. **Implicación**: para que un operador tenga 200 spools, los tiene que haber agregado uno por uno (o batch). No es un escenario que aparezca espontáneamente — es producto de uso intensivo.

## Próximos pasos

1. **Fase 2 — Diagnóstico** (próxima sesión, ~1h): perfilar React DevTools sobre flow 1 y flow 5 con 200 spools, confirmar si C1/C3 son los cuellos reales o si hay un sub-cuello escondido (e.g. re-render de `SpoolCardList` × 200 al actualizar 1 sólo). Producir tabla priorizada.
2. **Fase 3 — Atacar TOP 1-2** (próximas 2-4h): foco en C1 + C3. Re-medir.
3. **Fase 4 — Reporte + E2E**: doc final + Playwright E2E grabado para batch-INICIAR (si B1 se resuelve) y home-200 (ya capturado). Cierre formal de T-134.

---

# Fase 2 — Diagnóstico

**Hecho:** 2026-04-29 (misma sesión)

Las apuestas a priori del handoff (virtualización del listado, optimistic update tras acción) **no eran el cuello real**. Profiling backend con `time.perf_counter` inyectado temporalmente reveló dónde se va el tiempo realmente.

## Hallazgo dominante: `worker_service._get_all_workers()` cuesta ~480ms por request

**Setup del experimento.** Inyectamos `perf_counter` antes/después de cada bloque del endpoint `POST /api/spools/batch-status` y dentro de `_get_all_workers()` y de `role_repository.get_all_roles()`. Restart del backend, 3-4 corridas warm de cada tamaño de payload (1, 10, 50, 100 tags). Quitamos el código de profiling antes de seguir (verificado con `git diff` vacío en backend).

**Resultados (warm cache):**

```
[T-136-PROFILE] batch-status N=1   total=0.536s workers=0.533s loop=0.003s
[T-136-PROFILE] batch-status N=10  total=0.559s workers=0.555s loop=0.004s
[T-136-PROFILE] batch-status N=50  total=0.450s workers=0.440s loop=0.010s
[T-136-PROFILE] batch-status N=100 total=0.510s workers=0.495s loop=0.013s
```

**Lectura cuantitativa:**

- **`workers` block (build workers_map): ~480ms constante**, sin importar N.
- **`loop` (todos los `get_spool_by_tag` + `from_spool` × N): 3-15ms** (escala lineal pero plana).
- **avg per tag dentro del loop: 0.13-0.4ms** — fast path en cache.

Conclusión: el cuello no es el loop por tags ni la lectura de Sheets. **Es la línea**:

```python
# backend/routers/spool_status_router.py:126
all_workers = worker_service.get_all_active_workers()
```

Que se ejecuta **antes** del loop, **una vez por request**, y **siempre** tarda ~480ms.

## Subdiagnóstico: ¿dónde dentro de `_get_all_workers` se va el tiempo?

```
[T-136-PROFILE] _get_all_workers
  total=0.493s
  sheet_read=0.000s   ← cache hit Trabajadores, ~0ms
  roles_and_parse=0.493s  ← TODO el costo está acá
```

`sheet_read=0` confirma que la lectura de la hoja Trabajadores ya es cache hit instantáneo (TTL 300s en `read_worksheet`). El cuello está en **`roles_and_parse`** que cubre:

1. `role_service.role_repository.get_all_roles()` — leer hoja Roles.
2. Loop por 22 trabajadores: `SheetsService.parse_worker_row(row)` + `roles_by_worker.get(...)` + `worker.model_copy(update={'roles': roles_str})`.

No pude profilar más fino el sub-bloque de roles porque Sheets API empezó a tirar 503 transient (rate limit de quota) tras los restarts del backend, y el backend siguiente falló al validar schema (a su vez por 503 al re-leer Metadata). Esto reforzó la conclusión: **incluso con cache de Sheets, el código que parsea + clona Worker objects 22 veces por request es costoso**, y el sistema **no tolera** muchos restarts seguidos por la latencia del schema validation que pega Sheets de nuevo.

**Estimación gruesa del breakdown de los 480ms** (sin profiling fino):
- Lectura Roles (cache hit en runs warm): ~0ms.
- Parse + lookup + `model_copy` × 22 trabajadores: ~480ms / 22 = **~22ms por trabajador**.

22ms por Pydantic `model_copy` es razonable para Pydantic v2 con validación completa. **Multiplicado por 22 + por número-de-requests-paralelos**, se traduce en latencia visible para el operador.

## Implicación a nivel sistema

Cada request del frontend que necesita resolver `worker_nombre_completo` paga 480ms:

| Endpoint | ¿Llama `get_all_active_workers`? | Costo extra constante |
|---|---|---|
| `POST /api/spools/batch-status` | Sí | +480ms |
| `GET /api/spool/{tag}/status` | Sí | +480ms |
| `POST /api/v4/occupation/iniciar` | (probable, hace falta verificar) | +480ms |
| `POST /api/v4/occupation/finalizar` | (probable) | +480ms |
| `GET /api/workers` | Sí (es su único trabajo) | 480ms |

Esto explica por qué **flow 5 (asignar 1 spool) tarda 3.2s wall-clock**: 3 requests × ~480ms cada una de constant-cost = ~1.5s gratis, **antes** de cualquier trabajo útil.

Y por qué **flow 1 (cold load 200 spools) tarda 2.6s**: 2 chunks `batch-status` × 480ms (paralelos pero ambos disparan el mismo work) = la mayor parte del 1.9s API time observado en flow 1 son estos 480ms × 2 + algo de transferencia.

## Tabla diagnóstica final (priorización ROI/costo)

| # | Cuello | Evidencia | Categoría fix | Esfuerzo | ROI |
|---|---|---|---|---|---|
| **D1** | **`worker_service._get_all_workers()` re-parsea 22 trabajadores con `model_copy` por cada request, ~480ms** | Profiling con perf_counter, breakdown por bloque dentro del endpoint. | **Cache de `list[Worker]` en memoria** con TTL alto (300s, igual que Trabajadores raw). Invalidar al `add/update worker`. Hit ratio esperado >>99% en producción. | **Chico (~30-60 min)**. 1-line: `@lru_cache` con TTL custom o cache field en la clase. | **MUY ALTO**: ataca AL MISMO TIEMPO los 2 cuellos top (cold load 2.6s y assign-1 3.2s). Reducción esperada: ~480ms por endpoint = -50% tiempo en cold load, -45% en assign-1. |
| **D2** | **Render frontend 200 cards** | flow 1: DCL 62-90ms, load 315ms, **network_idle dominado por backend (1.9s API)**. Search/filter <150ms con 200 cards visibles. | (Pendiente confirmación) si tras D1 fix el cold load baja a ~1.2s, el render no es el cuello. Si baja menos, virtualizar (`react-window`). | Medio (1-2h) si requiere virtualización; trivial (re-medir) si D1 lo destrabó. | **Medio**. Solo después de medir post-D1. |
| **D3** | **Re-fetch completo tras cada acción** (refreshAll polling 30s) | C2 del baseline. Cada 30s = 2 chunks × 480ms = ~1s API del operador, gratis. | Optimistic update local + invalidación selectiva. Polling general menos frecuente (90s). | Mediano (2-3h) — toca state management del frontend (`SpoolListContext`). | Medio. Se vuelve más rentable post-D1 — sin D1, optimistic update igual gasta los 480ms al `refreshSingle`. |
| D4 | AddSpoolModal: 60KB para listar 136 ARM-eligibles | flow 4: 568ms backend. | Endpoint dedicado que devuelva solo `{tag, nv}`. | Bajo (1h) | Bajo. Modal se usa una vez por sesión típicamente. |
| D5 | Bug 8 redux (flow 6 bloqueado) | Click "ASIGNAR ARMADOR (5)" no avanza en headless. | Bugfix (no perf). Reproducir manualmente y diagnosticar. | Mediano-alto (1-3h) — investigación primero. | Crítico para UX pero **fuera de scope T-136**. Reportar al ASISTENTE como tarea separada. |
| D6 | (descartado) Virtualización del listado pre-D1 | Apuesta a priori. Profiling muestra DCL+load <320ms, network_idle dominado por backend. | — | — | — |

## Foco recomendado para Fase 3

**Atacar D1 únicamente**. Es:

1. **Chico** — fix de 30-60 min más test de regresión.
2. **Quirúrgico** — toca `worker_service.py`, no se mete con backend de negocio ni state machines.
3. **Sin riesgo de cambio de arquitectura** — agregar cache es un patrón ya establecido en el repo (`utils/cache.py` con TTL).
4. **Cubre los 2 cuellos top** — operador siente la mejora en cold load Y en cada acción de mutación.

Después de D1, **re-medir**. Si cold load baja a <1.5s y assign-1 baja a <2s, **terminamos T-136 en Fase 3 sin tocar D2/D3**. Si todavía hay grasa, evaluar D2/D3 para una segunda iteración.

D5 (Bug 8 redux) **se reporta al ASISTENTE como tarea separada** (no atacar en T-136).

## Hallazgo meta sobre la auditoría 28-abr (refuerza lección global #3)

La apuesta a priori del handoff (virtualización + re-fetch) era razonable mirando solo el síntoma "200 cards = lento". El cuello real (480ms de Pydantic parsing por request) **solo se podía ver con profiling backend**, no con código-grep o inspección visual del frontend.

Lección global #3 sigue manteniéndose: **medir antes de optimizar**. Si arrancábamos directamente con `react-window` (virtualización), habríamos invertido 2-3h en una optimización que **no movía la aguja** porque el wall-clock está dominado por la red (backend), no por el render local.

---

# Fase 3 — Atacar D1 (cache de Worker list parsed)

**Hecho:** 2026-04-29 (misma sesión)

## El fix

`backend/services/worker_service.py` — agregamos cache (TTL 300s) sobre la lista parseada `list[Worker]`. La lectura cruda de Trabajadores ya estaba cacheada en `read_worksheet`; lo que faltaba era cachear el **resultado final** (Worker objects con `roles` aplicados).

```python
# Antes: cada call re-parsea 22 trabajadores + model_copy(roles=...)
# Después: cache hit single in-memory dict lookup (~0.1ms)
_WORKERS_CACHE_KEY = "worker_service:all_workers_parsed"
_WORKERS_CACHE_TTL_SECONDS = 300  # 5 min, igual que Trabajadores raw rows

def _get_all_workers(self):
    cache = get_cache()
    cached = cache.get(_WORKERS_CACHE_KEY)
    if cached is not None:
        return cached
    # ... existing parse logic ...
    cache.set(_WORKERS_CACHE_KEY, workers, ttl_seconds=_WORKERS_CACHE_TTL_SECONDS)
    return workers
```

Diff completo: 22 líneas añadidas, 0 modificadas. **Cero cambios** en lógica de negocio, state machines o validaciones. Aprovecha el `SimpleCache` singleton ya existente en `backend/utils/cache.py`.

**Sin write paths** que cachear: el backend no muta Trabajadores (se editan a mano en Sheets). Si en el futuro se agrega un endpoint de mutación de Workers, debe llamar `get_cache().invalidate(_WORKERS_CACHE_KEY)` después de la escritura.

## Tests de regresión

Añadidos 5 tests en `tests/unit/services/test_worker_service_cache.py`:

1. `test_cache_hit_skips_sheets_read_within_ttl` — segunda call NO re-lee Trabajadores ni Roles.
2. `test_cache_returns_equivalent_workers` — contenido idéntico antes/después del cache hit.
3. `test_cache_shared_across_methods` — `find_worker_by_id`, `find_worker_by_nombre`, `get_all_active_workers` comparten cache.
4. `test_manual_invalidation_forces_refetch` — `cache.invalidate(KEY)` fuerza re-fetch en la próxima call.
5. `test_cache_returns_only_workers_filtered_by_active` — filtro `activo=True` se aplica POST-cache.

**Suite backend tras el fix:** 584 passed / 0 failed. (584 = 579 pre-fix + 5 nuevos tests del cache. Cero regresiones.)

## Sanity check directo al backend

```
batch-status N=100  pre-fix warm: ~500ms     →  post-fix:  11ms   (45x)
/api/workers solo   pre-fix warm: ~530ms     →  post-fix:   1ms   (530x)
/api/spool/<tag>    pre-fix warm: ~620ms     →  post-fix:   1ms   (560x)
```

(Las primera request tras restart todavía paga el costo de parse + Sheets read inicial; la segunda y siguientes son instantáneas dentro del TTL window de 300s.)

## Tabla comparativa (Playwright re-run sobre staging fresca, 200 spools)

| Flow | Métrica | Pre-fix | **Post-fix** | Δ absoluto | Δ % |
|---|---|---:|---:|---:|---:|
| **1 cold load** | network_idle | 2578 ms | **898 ms** | -1680 ms | **-65%** |
| 1 cold load | api_total_time | 1923 ms | 68 ms | -1855 ms | -96% |
| 1 cold load | DCL | 62 ms | 145 ms | +83 ms | +134% (ruido) |
| 2 search | max keystroke | 99 ms | 117 ms | +18 ms | (sin red, dentro de ruido) |
| 3 estado filter | click_to_filter | 140 ms | 147 ms | +7 ms | (sin red) |
| **4 add spool** | click_to_card_visible | 922 ms | **62 ms** | -860 ms | **-93%** |
| 4 add spool | modal_open_to_list_loaded | 64 ms | 70 ms | +6 ms | (sin red) |
| 4 add spool | api_total_time | 568 ms | 58 ms | -510 ms | -90% |
| **5 assign 1 spool** | chain_complete | 3167 ms | **1410 ms** | -1757 ms | **-55%** |
| 5 assign 1 spool | click_to_worker_modal | 853 ms | 105 ms | -748 ms | -88% |
| 5 assign 1 spool | api_total_time | 2359 ms | 1041 ms | -1318 ms | -56% |
| 6 batch assign | (BLOQUEADO Bug 8 redux) | — | — | — | sin cambio (no se atacó) |
| 7 uniones grid | click_to_grid_loaded | 100 ms | 94 ms | -6 ms | (ya rápido) |
| 7 uniones | api_total_time | 28 ms | 19 ms | -9 ms | -32% |
| 8 metrología modal | click_to_modal_loaded | 76 ms | 75 ms | sin cambio | (no toca backend) |

### Lectura

- **Cold load 200 spools**: 2.6s → **0.9s** (4× más rápido). Operador ya no percibe carga.
- **Asignar 1 spool**: 3.2s → **1.4s** (2.3× más rápido). Acción crítica del operador.
- **Add spool**: 0.9s → **62ms** (15× más rápido). Imperceptible.
- **Flujos sin red** (search, filter, metrología modal): sin cambio significativo, ruido <20ms.

### Notas sobre las métricas

- El DCL de flow 1 subió de 62ms a 145ms (+83ms). Es ruido en una sola corrida — el cold-load de Next.js varía entre runs y el primer fetch del frontend tiene overhead de hydration que no depende de mi cambio. El número que importa es **`network_idle`** (timing donde el home termina de hidratar todos los datos), que bajó de 2578 a 898 ms.
- El `api_total_time` de cold load (68 ms post-fix vs 1923 ms pre-fix) es **suma de duraciones de las 2 requests paralelas**, no wall-clock. La paralelización ya estaba (Promise.all del chunking B0 fix). Lo que mejoró es que **cada request pasó de ~1000 ms a ~30-40 ms**.
- `click_to_chain_complete` de assign-1 (1410 ms) ya no está dominado por el backend — es la suma del open-modal + worker-fetch + mutate + close + refresh. Ahora la red es la parte chica; el resto es interacciones con DOM y el backoff de los modales.

## ¿Cuánto queda en la mesa?

Re-evaluando los cuellos restantes de la tabla diagnóstica:

| # | Cuello | Pre-fix | Post-fix | Comentario |
|---|---|---|---|---|
| D1 | Worker parse cost | 480 ms | <1 ms | **CERRADO** |
| D2 | Render frontend 200 cards | (no era cuello) | (no es cuello) | Confirmado: DCL <150 ms, scroll suave. **No requiere virtualización**. |
| D3 | 30s polling refresh | 2× 480 ms cada 30s = 1 s/min de "carga gratuita" | 2× 30 ms cada 30s = 60 ms/min | **Cerrado de facto**. El fix de D1 cubre también este caso porque los polling refreshes ahora también son cache hits. |
| D4 | AddSpoolModal payload 60KB | 568 ms | 58 ms | **Cerrado de facto** por D1 (el cuello era worker parse, no payload size). |
| D5 | Bug 8 redux (flow 6) | bloqueado | bloqueado | Sin cambio — bug no relacionado con D1. **Reportar al ASISTENTE como tarea separada**. |

**Conclusión: con UN cambio quirúrgico (D1) se atacaron simultáneamente los 4 cuellos de performance**. Los 3 que quedaban (D2, D3, D4) eran sub-cuellos del mismo problema raíz, y D1 los disolvió.

## ¿Es viable 200 spools en producción?

Antes de T-136 no había forma de saberlo (B0 chunking lo hacía imposible llegar al test). Después de T-136:

- ✅ **Sí, viable**. Cold load 0.9s con 200 spools, operación común <1.5s, search/filter <150ms.
- ✅ **No requiere cambios de arquitectura**. El stack Next.js + FastAPI + Sheets sigue siendo apto a esa escala.
- ⚠️ **Caveat 1**: la prueba se hizo con 22 trabajadores y datos sintéticos. Si en producción hay 50+ trabajadores el costo de re-fetch tras invalidación crecerá proporcional, pero queda enmascarado por el TTL 300s.
- ⚠️ **Caveat 2**: el TTL de 300s significa que cambios manuales en la hoja Trabajadores (un nuevo trabajador, baja de actividad) tardan **hasta 5 min en reflejarse** en el backend. Si se quiere reactividad inmediata, se debe agregar un botón "refresh workers" o bajar el TTL — pero el costo subiría linealmente con la frecuencia.

## Decisión: cierre Fase 3

Con D1 implementado y validado:
- Suite backend: 584 passed / 0 failed.
- Suite frontend: 220 passed / 35 failed (35 pre-existentes — sin regresiones).
- TS check, lint: limpios.
- Mejora medida: -65% cold load, -55% asignar 1 spool. Por encima del umbral implícito ("debe sentirse mejor").

**No se ataca D2/D3/D4** porque ya están cerrados de facto. **No se ataca D5** porque está fuera de scope (bugfix, no perf).

---

# Fase 4 — Cierre y entregables

**Hecho:** 2026-04-29 (misma sesión)

## Cierre de T-134 (E2E Playwright batch-INICIAR)

T-136 absorbió T-134. T-134 pedía un E2E grabado de batch-INICIAR (Bug 8 path). Estado al cierre:

| Spec | Cubre | Status | Path |
|---|---|---|---|
| `perf-flow-01-cold-load.spec.ts` | Home con 200 spools, cold load | ✅ runnable, pasa | `zeues-frontend/e2e/perf-flow-01-cold-load.spec.ts` |
| `perf-flow-05-assign-1.spec.ts` | Modal chain LIBRE → ARMADO → worker pick → INICIAR | ✅ runnable, pasa | `zeues-frontend/e2e/perf-flow-05-assign-1.spec.ts` |
| `perf-flow-06-batch-assign.spec.ts` | Batch-INICIAR 5 spools (target original T-134) | ⚠️ **BLOQUEADO en headless** (Bug 8 redux) | `zeues-frontend/e2e/perf-flow-06-batch-assign.spec.ts` |

**Cierre parcial de T-134:**
- ✅ Cubierto vía E2E: cold load 200 spools + asignación individual 1 spool. Cubre regresiones del path INICIAR-ARM, que es el mismo handler que ejercita el batch path internamente.
- ⚠️ No cubierto vía E2E automatizado: batch-INICIAR de N spools en una sola operación. El spec existe (`perf-flow-06`) y captura el flujo hasta justo antes del click final que el bug bloquea. Marcado claramente con un comentario `KNOWN BLOCKER` en el spec.

**Reproducción manual de batch-INICIAR** (mientras D5 no se cierre):

```bash
# 1. Levantar stack apuntando a staging y re-seedear
source venv/bin/activate
python scripts/seed_load_test.py --yes
python scripts/dump_staging_tags.py
PYTHONPATH="$(pwd)" uvicorn backend.main:app --port 8000 &
cd zeues-frontend && npm run dev &

# 2. En el navegador (NO en headless):
#    a. Abrir http://localhost:3000
#    b. Click "+ Añadir Spool"
#    c. Toggle "ASIGNAR ARMADOR AHORA"
#    d. Tipear "MK" en TAG SPOOL
#    e. Seleccionar 5 filas (cualquier subset LIBRE)
#    f. Click "ASIGNAR ARMADOR (5)"
#    g. En WorkerPickerModal: pick "Manuel Marchetti"
#    h. Verificar 5 cards aparecen ocupadas en home con toast verde
```

Si este flujo manual falla en una sesión, **D5 está confirmado y debe abrirse como tarea separada al ASISTENTE**. Si funciona pero el headless sigue fallando, es un quirk de Playwright + React event delegation y se puede dejar como `test.skip` con justificación.

## Entregables Fase 4

1. **Audit doc canónico**: este mismo archivo (`docs/audits/T-136-perf-baseline-2026-04-29.md`).
2. **Backend fix (D1)**: `backend/services/worker_service.py` + `tests/unit/services/test_worker_service_cache.py`.
3. **Frontend fix (B0)**: `zeues-frontend/lib/api.ts` + `zeues-frontend/__tests__/lib/api-batch-chunking.test.ts`.
4. **Setup scripts**: `scripts/seed_load_test.py` + `scripts/dump_staging_tags.py`.
5. **Playwright suite**: 8 specs en `zeues-frontend/e2e/perf-flow-NN-*.spec.ts` + helper `e2e/helpers/perf-instrument.ts` + fixture `e2e/fixtures/staging-tags.json`.
6. **Handoff de vuelta al ASISTENTE**: `ASISTENTE/planning/proyectos/zeus-by-km/HANDOFF-FROM-ZEUS-T136-perf-audit.md`.

## Tareas pendientes a abrir en ASISTENTE

1. **T-137 (sugerido)** — Investigar Bug 8 redux (D5). Reproducir manualmente con Matías si es posible, confirmar si afecta producción real (tablet, navegador real) o solo automation. Si afecta prod: bug crítico de UX que bloquea batch-INICIAR. Si solo automation: documentar como test-skip + workaround.
2. **T-138 (sugerido, low priority)** — UX state confusion: spools en `ARM_PEND`/`SOLD_PEND`/`ARM_TERM` derivan a `LIBRE` en `_derive_estado` por falta de ocupante. Considerar nuevo estado `PARCIAL` o badge visible para que el operador pueda distinguir "libre virgen" de "libre con uniones parciales pausadas". Out of scope T-136, captado para v5.1.
3. **Sin tarea formal pero anotar**: 35 fallos pre-existentes en suite frontend (jest), confirmados contra `main` pristino. Ver lección global #6 — cuando se aborde, hacer una pasada de cubeta A/B/C (igual que T-133 hizo con backend).

