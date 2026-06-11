# Informe de oportunidades UX — ZEUES terreno (v1)

**Fecha:** 2026-06-10 · **Complementa:** `informe-rediseno-v6.md` y los 33 issues del proyecto Linear ZEUS-by-KM (Fases 0–4).

---

## 1. Contexto y modelo de operación

El rediseño v6 en curso es casi en su totalidad una reestructuración de la capa de datos (SQLite, estado derivado on-read, ~11 endpoints, Sheets como hoja intake + reporte). Declara explícitamente que **no cambia la UX de tablet**. Este informe cubre el espacio que v6 deja fuera: hacer la app más simple y rápida para el usuario en terreno.

**Modelo de operación real (validado con el dueño del producto):**

- Los spools **nacen en Google Sheets**, cargados por una persona de oficina (ingeniería/planificación) que **no usa la app** y ve el avance desde el mismo Sheets.
- En terreno, **un coordinador opera la tablet** y registra el trabajo de varios armadores/soldadores. La app es el "traductor" de lo que pasa en terreno. Elegir trabajador en cada acción es necesario (la atribución ES el dato), pero optimizable.
- El **dato de mayor valor** es el ingreso de uniones: cantidad, DN y tipo **se descubren en terreno** durante/al finalizar el trabajo. Oficina no maneja esa información; la app es el único canal de captura. El modal de uniones es inevitable — su UX interna es donde se gana velocidad.
- El ingreso de spools a la lista de la app es hoy un paso manual; el dueño pidió evaluar mantenerlo vs automatizarlo (§4, OP-4).

**Principios de diseño que ordenan este informe:**

1. **La acción siguiente siempre visible** — el coordinador no debería navegar modales para descubrir qué puede hacer con un spool.
2. **Confirmar > navegar** — preferir un botón grande de confirmación con buen default sobre una secuencia de selecciones.
3. **Rápido exige reversible** — acelerar la captura solo es seguro si equivocarse cuesta poco (corrección visible).
4. **Terreno confirma, oficina propone** — los datos pueden pre-poblarse desde oficina como borrador, pero el hecho registrado es siempre la confirmación en terreno.

---

## 2. Baseline verificado

### 2.1 Atajos que YA existen (no re-proponer)

| Atajo | Evidencia |
|---|---|
| Skip de OperationModal cuando la operación es derivable (T-110: ARM_TERM→SOLD, SOLD_TERM→MET; MET-ready abre MetrologiaModal directo) | `page.tsx:398-416` |
| Skip de ActionModal cuando hay una sola acción válida | `page.tsx:422-429` |
| Skip de WorkerModal en FINALIZAR/PAUSAR (worker parseado de `ocupado_por` "MR(93)") | `page.tsx:438-466` |
| Chaining post-FINALIZAR (T-111): ARM→WorkerModal SOLD, SOLD→MET, REP→MET | `page.tsx:485-511` |
| Batch INICIAR (v5.1): N spools → 1 armador → INICIAR todos | `AddSpoolModal.tsx` |
| UnionesModal: "SELECCIONAR TODAS", input TOTAL numérico, defaults DN/TIPO para filas vacías | `UnionesModal.tsx` |

### 2.2 Taps por flujo (hoy)

| Flujo | Interacciones hoy | Nota |
|---|---|---|
| INICIAR ARM (spool nuevo en lista) | 3 (card → ARM → worker) | OperationModal aparece porque un spool LIBRE sin trabajo deriva `null` |
| INICIAR SOLD post-ARM | 2 (card → worker) | operación derivada |
| FINALIZAR ARM con 5 uniones nuevas | ~9-10 (card → FINALIZAR → TOTAL + defaults DN/TIPO + SELECCIONAR TODAS + botón) | + modal encadenado de SOLD |
| FINALIZAR con uniones ya cargadas | ~4 (card → FINALIZAR → SELECCIONAR TODAS → botón) | |
| Añadir 1 spool a la lista | ~7 (botón → escribir 2+ chars → fila → LISTO → …) | batch: ~6 para N spools |

---

## 3. Oportunidades

Ficha estándar: **Problema** (con evidencia) / **Propuesta** / **Ahorro** / **Dependencia v6** / **Riesgo · Costo**.

### Prioridad 1 — alto impacto

#### OP-1 · Acción directa en la card (one-tap action)

- **Problema:** la card entera es un botón genérico que abre una cadena de modales. El coordinador ve el estado (badge) pero no la acción siguiente — que casi siempre es única — escondida tras 1-2 modales (`SpoolCard.tsx`, `page.tsx:398-432`).
- **Propuesta:** renderizar en la card el botón de la acción primaria derivada: "INICIAR ARM", "FINALIZAR SOLD", "METROLOGÍA". Tocarlo salta directo al modal terminal (Worker/Uniones/Metrología). Un tap secundario ("⋯" o la card misma) da acceso a acciones alternativas (PAUSAR, otra operación).
- **Ahorro:** elimina OperationModal y ActionModal del ~90% de los flujos: INICIAR ARM 3→2 taps; FINALIZAR 2→1 tap hasta el modal de uniones. La ganancia mayor es **predictibilidad**: el coordinador escanea la lista y ve qué toca hacer en cada spool sin abrir nada.
- **Dependencia v6:** prototipo posible hoy con `getValidActions`/`deriveOperation` del frontend, pero el caso "spool LIBRE sin trabajo" deriva `null` (por eso existe OperationModal). Con **Fase 0** (`valid_actions` del backend, 5IN-23/5IN-26) el botón es 100% confiable y se borra la duplicación frontend.
- **Riesgo · Costo:** taps accidentales en planta — mitigado porque toda acción mutadora sigue pasando por un modal de confirmación. Costo medio (rediseño de card).

#### OP-2 · Worker sticky / recientes en WorkerModal

- **Problema:** `WorkerModal.tsx:75-95` carga la lista completa filtrada por rol en cada apertura, sin orden por uso ni memoria del último seleccionado. Con cuadrillas chicas (~12 usuarios según decisión #4 del v6), el coordinador selecciona al mismo armador/soldador muchas veces seguidas.
- **Propuesta:** (a) sección "RECIENTES" arriba con los últimos 2-3 workers usados **por operación** (localStorage, clave `last_worker_{ARM|SOLD|REP}`); (b) variante sticky: chip preseleccionado "CONFIRMAR — MIGUEL R." como primer botón gigante + "elegir otro". En sinergia con OP-1, el botón de card puede mostrar "INICIAR SOLD · MR" y confirmar en 1 tap.
- **Ahorro:** 0-1 taps, pero elimina el scroll/búsqueda visual en cada acción. Donde más rinde: el WorkerModal encadenado post-FINALIZAR ARM.
- **Dependencia v6:** ninguna. Hacible ya.
- **Riesgo · Costo:** atribuir trabajo al worker equivocado por inercia — mitigar con nombre grande en el chip y en el toast de éxito ("ARM finalizado — atribuido a MIGUEL R."). Costo bajo.

#### OP-3 · Acelerar la entrada de uniones (el dato de mayor valor)

- **Problema** (cuatro, con evidencia):
  1. En modo FINALIZAR el caso dominante ("terminé todo") abre con **cero selección**: exige "SELECCIONAR TODAS" o N checkboxes.
  2. Las filas nuevas nacen vacías; los defaults DN/TIPO del header existen pero exigen 2 dropdowns extra y hay que descubrirlos.
  3. DN es un `<select>` nativo de **33 opciones** (`UnionesModal.tsx:15-31`) — hostil con guantes en tablet.
  4. **Label engañoso en PAUSAR:** el botón principal dice "FINALIZAR N UNIONES" aunque el flujo sea pausar, porque el modal recibe `operacion` pero no la acción (`UnionesModal.tsx:320-324`; `page.tsx:1217` solo pasa `operacion`).
- **Propuesta:**
  - **Preselección automática** de todas las uniones seleccionables al abrir en modo FINALIZAR (deseleccionar es la excepción). PAUSAR abre con cero (lo hecho es la excepción).
  - **Herencia de fila:** una fila nueva copia DN/TIPO de la última fila con datos (las uniones de un spool suelen ser homogéneas); los defaults del header quedan como override.
  - **Grilla de botones para DN** (bottom-sheet con los 8-10 DN frecuentes en botones grandes + "más…") en lugar del select de 33 opciones; TIPO como 5 botones segmentados (`BW/SO/FILL/BR/MIT`).
  - **Pasar `action` como prop** y etiquetar según el caso: "FINALIZAR N UNIONES" / "GUARDAR AVANCE Y PAUSAR".
  - ~~Precarga desde hoja intake~~ — **DESCARTADA (decisión del dueño, 2026-06-10):** oficina no quiere ingresar datos de uniones; la captura queda 100% en terreno. ⚠️ Discrepancia con el informe v6 §5.2, que asume que la hoja intake incluye "uniones, DN, tipo" cargadas por ingeniería — el alcance de la hoja intake y del sync (5IN-40) debe reducirse a datos maestros de **spools**.
- **Ahorro:** uniones ya cargadas: 4→3 taps (preselección). 5 uniones nuevas homogéneas: ~9-10→~5 interacciones.
- **Dependencia v6:** ninguna — preselección, herencia, grilla DN y fix del label son hacibles ya.
- **Riesgo · Costo:** la preselección puede registrar de más si el coordinador no revisa — mitigar resaltando el resumen ya existente "Seleccionaste N uniones = X PD". Costo bajo (preselección/label), medio (grilla DN).

### Prioridad 2 — alto valor, requieren decisión o fase v6

#### OP-4 · Ingreso de spools: manual vs automático (análisis pedido)

- **Problema:** añadir un spool exige botón → escribir 2+ caracteres → tap fila → LISTO; y el cache TTL de 60s del backend sobre Sheets + poller de 30s hacen que un spool recién creado en oficina "no aparezca" de inmediato — la fricción percibida es real.
- **Opción A — mantener manual (mejorado).** La lista curada funciona como *plan de trabajo del turno*: corta, intencional, el coordinador controla qué ve. **Pros:** foco, sin ruido, escala con 2.000+ spools en el maestro. **Contras:** paso repetitivo, riesgo de olvido, doble trabajo mental (oficina crea, terreno re-busca).
- **Opción B — bandeja automática.** Todo spool nuevo del intake con materiales listos aparece solo en una sección "POR INICIAR". **Pros:** cero pasos, nada se pierde, oficina "empuja" trabajo. **Contras:** la lista crece sin control (exigiría que oficina asigne prioridad/NV — trabajo nuevo para ella), se pierde la semántica de "mi lista del turno", e introduce una pregunta de coordinación que hoy no existe: ¿quién decide qué se fabrica hoy, la hoja o el coordinador?
- **Recomendación — híbrido:** mantener la lista curada + **badge "N NUEVOS"** en el botón Añadir Spool que abre el modal ya filtrado a los spools creados desde la última visita, con **"agregar todos los de NV-XXXX" en 1 tap**. Da el ~80% del beneficio de B sin sus contras.
- **Dependencia v6:** el badge "nuevos" necesita distinguir fecha de alta → natural en **Fase 2** (tabla `spools` con timestamp de sync). El "agregar todos por NV" se puede hacer ya (el modal ya busca por NV y tiene batch mode).
- **Riesgo · Costo:** bajo · medio.

#### OP-5 · Corrección / undo visible

- **Problema:** no existe camino de corrección en la app: un FINALIZAR con worker o uniones equivocadas solo se arregla editando Sheets a mano. Peor: el toast genérico "Operacion completada" (`page.tsx:501`) no permite detectar el error en el momento.
- **Propuesta en dos etapas:**
  1. **Ya:** toasts con contenido verificable ("ARM finalizado — 5 uniones — MIGUEL R.") + historial visible por card (el endpoint de history existe).
  2. **Con Fase 2:** botón "Corregir" sobre el último registro, montado sobre `POST /spools/{tag}/corregir` (5IN-41/5IN-44). **El rol corrector será el administrador de la planilla** (decisión del dueño, 2026-06-10) — implicancia nueva: esa persona, que hoy no usa la app, pasa a ser usuaria para correcciones, probablemente desde computador → la UI de corrección debe funcionar bien en desktop, no solo tablet. Este informe define solo la superficie UX; no duplica el issue del endpoint.
- **Ahorro:** no es de taps sino de **confianza**: reduce el costo de equivocarse, que es lo que habilita acelerar OP-1/OP-3 (principio 3: rápido exige reversible).
- **Dependencia v6:** etapa 1 independiente; etapa 2 = Fase 2.
- **Riesgo · Costo:** mantener la etapa 2 como wireframe hasta que exista el endpoint. Costo bajo (etapa 1).

#### OP-6 · Chaining post-FINALIZAR: de push a oferta

- **Problema:** tras FINALIZAR ARM se abre automáticamente el WorkerModal de SOLD (`chainNextModalAfterFinalizar`, `page.tsx:485-511`). Si la soldadura no parte ahora (lo habitual: el spool espera en cola), el coordinador debe CANCELAR — un tap extra y un modal sorpresivo. Además el helper hace `await refreshSingle(tag)` **antes** de mostrar el modal (`page.tsx:491-500`): 1-4s de latencia Sheets en medio de la cadena.
- **Propuesta:** reemplazar el push por una **oferta no bloqueante**: banner/toast persistente "ARM listo — ¿Iniciar soldadura? [SÍ] [después]", o directamente que la card refrescada muestre el botón "INICIAR SOLD" (con OP-1 el chaining se vuelve innecesario). Mover el `refreshSingle` a paralelo, fuera del camino crítico.
- **Ahorro:** −1 tap y −1 interrupción cuando no se sigue de inmediato; −1-4s de espera percibida siempre.
- **Dependencia v6:** independiente. La latencia desaparece sola en Fase 2 (<50ms), pero el problema de interacción no.
- **Riesgo · Costo:** revierte parcialmente T-111 — validar con el coordinador real cuál patrón prefiere (ver §7). Costo bajo.

### Prioridad 3 — pulido y percepción

#### OP-7 · Frescura de datos

- **Problema:** el poller de 30s se pausa mientras haya cualquier modal abierto (`page.tsx:161-179`, condición `modalStack.stack.length === 0`); tras una sesión larga de modales los datos pueden quedar viejos. No hay indicador de frescura ni refresh manual.
- **Propuesta:** (a) disparar `refreshAll()` al vaciarse el stack de modales (hoy solo se refresca el spool tocado); (b) indicador discreto "ACTUALIZADO HACE 12s" con tap-to-refresh; (c) post-Fase 2, bajar el intervalo a 5-10s o pasar a refetch-on-focus — el poller de 30s existe por la cuota de Sheets (60 writes/min) y pierde su razón de ser tras el cutover.
- **Dependencia:** (a)(b) ya; (c) Fase 2. **Riesgo · Costo:** nulo · bajo.

#### OP-8 · Confirmaciones consistentes

- **Problema:** quitar un spool ocupado usa `window.confirm()` nativo (`page.tsx:728-731`) — diminuto y visualmente ajeno en tablet — mientras la app usa confirmación inline en otros lugares (SpoolCard, borrado de uniones). Además "Quitar" un spool ocupado ejecuta un `finalizarSpool` con `selected_unions: []` para liberarlo (`page.tsx:738-743`): semántica oculta que merece copy explícito.
- **Propuesta:** unificar al patrón inline de 2 taps + copy que explique la consecuencia ("esto libera el trabajo en curso de MIGUEL R.").
- **Dependencia:** ya. **Riesgo · Costo:** nulo · bajo.

#### OP-9 · OperationModal honesto

- **Problema:** cuando aparece (spool sin trabajo), ofrece siempre las 4 operaciones (`OperationModal.tsx:78-89`, "always show all 4") — SOLD/MET/REP sobre un spool virgen fallan recién en el backend, con error críptico.
- **Propuesta:** deshabilitar (no ocultar) operaciones inválidas con el motivo como sub-texto ("SOLD — requiere ARM completo"). Con OP-1 este modal casi desaparece; mientras exista, que no mienta.
- **Dependencia:** hacible ya con datos de la card; perfecto con `valid_actions` de Fase 0. **Riesgo · Costo:** nulo · bajo.

---

## 4. Matriz oportunidad × fase v6

| Oportunidad | Ya (código actual) | Fase 0 (`valid_actions`) | Fase 2 (SQLite + intake + corregir) |
|---|:---:|:---:|:---:|
| OP-1 Acción directa en card | prototipo | **consolidación** | — |
| OP-2 Worker sticky/recientes | **✓** | — | — |
| OP-3 Uniones rápidas (preselección, herencia, grilla DN, label PAUSAR) | **✓** | — | — *(precarga descartada)* |
| OP-4 Bandeja de nuevos (híbrido) | "todos por NV" | — | badge "N NUEVOS" |
| OP-5 Corrección visible | toasts + historial | — | botón "Corregir" |
| OP-6 Chaining como oferta | **✓** | mejor con OP-1 | latencia desaparece |
| OP-7 Frescura | refresh al cerrar modales + indicador | — | bajar intervalo |
| OP-8 Confirmaciones | **✓** | — | — |
| OP-9 OperationModal honesto | parcial | **✓** | — |

**Complementariedad con Linear:** ninguna oportunidad duplica los 33 issues existentes (capa de datos). Las que dependen de v6 *consumen* sus contratos: `valid_actions` (5IN-23, 5IN-26), errores estructurados (5IN-24, 5IN-29), sync intake→DB (5IN-40), endpoint corregir (5IN-41) + check de rol (5IN-44). Si estas oportunidades pasan a Linear, deben enlazarse como dependencias de esos issues, no como duplicados.

---

## 5. Roadmap sugerido (3 olas)

| Ola | Cuándo | Contenido |
|---|---|---|
| **1** | Ya, sobre el código actual | OP-3 quick-wins (preselección, herencia, grilla DN, fix label PAUSAR) · OP-2 worker recientes · OP-5 etapa 1 (toasts verificables) · OP-7a refresh al cerrar modales · OP-8 confirmaciones · OP-9 parcial |
| **2** | Con Fase 0 (derive-on-read) | OP-1 acción directa consolidada · OP-6 chaining como oferta · OP-9 completo |
| **3** | Con Fase 2 (cutover + intake) | OP-4 híbrido (badge nuevos) · OP-5 etapa 2 (botón Corregir, desktop-friendly) |

La Ola 1 es deliberadamente independiente de la migración: si v6 se atrasa, el terreno igual gana velocidad ahora. La Ola 2 conviene hacerla *junto con* Fase 0 — el mismo PR que hace al frontend consumir `valid_actions` (5IN-25) puede rediseñar la card.

---

## 6. Descartadas (y por qué)

- **Login/sesión por trabajador individual:** contradice el modelo coordinador-única-tablet.
- **Eliminar WorkerModal:** imposible — la atribución de trabajo ES el dato. Solo se optimiza (OP-2).
- **Ingresar uniones desde oficina (incluso como borrador a confirmar):** descartado por decisión del dueño (2026-06-10) — oficina no quiere cargar datos de uniones. La captura es 100% de terreno, y ahí está el valor diferencial del dato.
- **Rediseño visual general:** v6 declara la UX de tablet intocada; este informe se limita a flujo e interacción.

---

## 7. Preguntas abiertas — estado (actualizado 2026-06-10)

1. ~~¿Oficina puede/quiere precargar uniones en la hoja intake?~~ **Respondida: NO.** Oficina no quiere ingresar datos de uniones; captura 100% en terreno. Precarga descartada de OP-3; reduce el alcance de la hoja intake del v6 §5.2 (solo datos maestros de spools).
2. ¿Quién decide qué se fabrica primero si los spools aparecen solos en la app? → **movida al cuestionario** (`cuestionario-rediseno.md`, preguntas A1-A3). Define OP-4.
3. ¿Chaining push u oferta? → **se le preguntará al coordinador directamente** (`cuestionario-rediseno.md`, pregunta B1). Define OP-6; B2/B3 validan OP-1/OP-2.
4. ~~¿Quién tendrá el rol para "Corregir"?~~ **Respondida: el administrador de la planilla.** Pasa a ser usuario de la app para correcciones (ver OP-5); el cuestionario confirma dispositivo y disposición (pregunta A12).

**Siguiente paso:** entrevistar con `cuestionario-rediseno.md` (Sección A: administrador de la planilla; Sección B: coordinador de terreno) y volcar las respuestas aquí para repensar OP-4, OP-6 y el alcance de Fase 2.

---

## 8. Apéndice — taps antes/después (consolidado)

| Flujo | Hoy | Con Ola 1 | Con Olas 1-3 |
|---|:---:|:---:|:---:|
| INICIAR ARM spool nuevo | 3 | 3 | **2** (OP-1) |
| INICIAR SOLD post-ARM | 2 | 2 | **1-2** (OP-1 + OP-2 sticky) |
| FINALIZAR ARM, 5 uniones nuevas homogéneas | ~9-10 | **~5** (preselección + herencia) | **~4** (OP-1, −1 tap de entrada) |
| FINALIZAR, uniones ya cargadas | ~4 | **3** (preselección) | **2** (OP-1) |
| Añadir spool + iniciar | ~7 | ~6 ("todos por NV") | **~3** (badge nuevos + batch) |
| Declinar el chaining post-FINALIZAR | 1 tap + modal sorpresivo | 0 (oferta ignorable) | 0 |
