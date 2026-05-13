# Bitácora de bugs — `docs/bugs/`

Bitácora forense de bugs encontrados en ZEUES. Cada bug es un archivo Markdown numerado secuencialmente (`B-001`, `B-002`, …). Esta carpeta vive en el repo para que el historial sobreviva a sesiones, deploys y rotaciones de chat.

## Para qué sirve

- **Bitácora forense local**: cuando un síntoma reaparece meses después, buscar en esta carpeta es más rápido que rastrear commits o Slack.
- **Contexto para investigaciones futuras**: cada bug deja el reporte verbatim del operador, las hipótesis que se barajaron y la resolución final con commit hash.
- **Evidencia auditable**: las imágenes que manda el operador en chat son efímeras (`~/.claude/image-cache/` se vacía); acá quedan archivadas y descritas en texto.

## Para qué NO sirve

- **NO reemplaza GitHub Issues**: si quieres tracking de PR, asignaciones, milestones, abre un issue.
- **NO reemplaza tareas del ASISTENTE** (`ASISTENTE/planning/tareas.md`): los IDs `T-NNN` se asignan allá. Si un bug genera tarea, se enlaza con `tarea_relacionada: T-NNN` en el frontmatter — pero el bug aquí queda como evidencia, la tarea allá queda como acción.
- **NO es un backlog**: no se priorizan ni se asignan bugs aquí. Solo se registran, investigan, resuelven y archivan.

## Cómo registrar un bug nuevo

1. **Buscar el último ID**: `ls docs/bugs/ | grep -oE 'B-[0-9]+' | sort -V | tail -1`. Sumar uno.
2. **Definir slug**: kebab-case corto que describa el síntoma (no la causa). Ej: `batch-iniciar-spools-quedan-libres`.
3. **Decidir estructura**:
   - **0 ó 1 imagen** → archivo plano: `docs/bugs/B-NNN-<slug>.md`.
   - **2 ó más imágenes / video / logs adjuntos** → carpeta: `docs/bugs/B-NNN-<slug>/B-NNN.md` + assets.
4. **Copiar el template** (sección [Template](#template) abajo) y llenarlo.
5. **Renombrar las imágenes** que mande el operador a `01-<slug>.png`, `02-<slug>.png`, etc. Nunca dejar nombres como `IMG_4523.jpg` ni los hashes del image-cache.
6. **Describir cada imagen en texto** dentro del bug (regla dura — ver [reglas de evidencia](#reglas-de-evidencia)).
7. **Hacer commit** con mensaje `docs(bugs): register B-NNN — <título corto>`.

## Template

Copiar tal cual al crear un bug nuevo. Llenar todos los campos del frontmatter (los que no apliquen, dejar `null` o explicar por qué).

```markdown
---
id: B-NNN
titulo: "<frase corta que describe el síntoma, no la causa>"
fecha_reporte: YYYY-MM-DD
reportado_por: <nombre o rol de quien lo reportó>
severidad: P0|P1|P2|deuda
area: frontend|backend|sheets|deploy|infra
estado: open|investigating|fixed|wontfix|duplicate
commit_when_reported: <hash-corto-del-deploy-en-prod-al-momento-del-reporte>
produccion_o_local: produccion|local|staging
archivos_sospechosos:
  - <ruta/al/archivo.ts>     # razón
  - <ruta/al/otro.py>        # razón
tarea_relacionada: T-NNN|null
---

## Reporte del usuario

> Texto verbatim del operador. Sin reformular, sin corregir ortografía. En su idioma original.
> Si vino con audio o video, transcribir aquí.

## Evidencia

### `01-<slug>.png`

Descripción textual obligatoria (3–5 frases). Qué pantalla es, qué elementos se ven, qué está señalando el operador (si hay dedo en la foto), qué condición específica documenta esta imagen. Esta descripción debe permitir entender el bug **sin abrir la imagen**.

### `02-<slug>.png`

(Misma estructura.)

## Pasos para reproducir

1. <paso accionable>
2. <paso accionable>
3. ...

## Comportamiento

- **Esperado**: <qué debería pasar>
- **Observado**: <qué pasa en realidad>

## Hipótesis iniciales

(Opcional, breve. Solo hipótesis razonadas, no especulación libre. Cada una con la ruta del archivo que sospechas.)

1. ...
2. ...

## Investigación

Append-only. Una entrada por sesión de diagnóstico. Nunca re-escribir entradas previas — si una hipótesis se invalida, escribir una entrada nueva que la invalide, no editar la antigua.

### YYYY-MM-DD — <nombre / quién investigó>

**Lo que se descartó** — cada item con `archivo:línea` + razón concreta. El "no es X porque Y" es tan valioso como el "es Z porque W": evita que la próxima persona repita el mismo descarte.

1. ...
2. ...

**Lo que se confirmó** — cada item con `archivo:línea` + cita corta del código relevante en backticks.

1. ...
2. ...

**Causa raíz propuesta** — una o dos frases. Marcar confianza al final: `(alta confianza)`, `(media)`, `(baja — necesita verificación adicional)`.

**Siguiente paso** — opcional. Qué falta verificar, qué fix candidato priorizar, qué pregunta abrir al usuario.

## Resolución

(Llenar solo cuando se cierra. Si `estado: wontfix` o `duplicate`, explicar por qué.)

- **Commit**: `<hash>` (`<branch>`)
- **Fecha**: YYYY-MM-DD
- **Qué se cambió**: <una o dos frases>
- **Por qué**: <causa raíz, no descripción del fix>
- **Cómo se verificó**: <prueba que confirma el fix>
```

## Reglas de evidencia

- **Imágenes siempre descritas en texto.** Si alguien lee el bug en GitHub Web y las imágenes no cargan (firewall, conexión lenta, render-only), la descripción es lo único que tiene. Sin descripción, el bug está incompleto.
- **Renombrar a `NN-<slug>.png`** antes de archivar (no `IMG_*.jpg` ni los hashes del image-cache de Claude).
- **PNG sobre JPG** para capturas de pantalla; JPG OK para fotos de tablet con reflejo.
- **Optimizar si pesa >500 KB** (sugerencia, no obligatorio). Usar `pngquant` o similar.
- **Video** → no embebir en el repo (pesa); en su lugar, transcribir las escenas clave en texto bajo `## Evidencia`. Si el video es esencial, subirlo a Drive y poner el link.
- **Logs / stack traces** → triple backticks dentro de la sección correspondiente. No archivos `.log` adjuntos.

## Estados

| Estado          | Significado |
|-----------------|-------------|
| `open`          | Reportado, sin investigar todavía. |
| `investigating` | En diagnóstico activo. |
| `fixed`         | Resuelto. La sección `## Resolución` está llena. |
| `wontfix`       | Decidido no arreglar (con justificación en `## Resolución`). |
| `duplicate`     | Mismo problema que otro `B-NNN` (linkear). |

### Cuándo se cambia `estado:`

- **`open → investigating`**: al escribir la primera entrada bajo `## Investigación`.
- **`investigating → fixed`**: cuando se llena `## Resolución` con commit + fecha + causa raíz + verificación.
- **`investigating → wontfix`**: cuando se decide no arreglar. La razón va en `## Resolución`.
- **`* → duplicate`**: cuando se descubre que es el mismo problema que otro `B-NNN`. Linkear al canónico en el cuerpo y dejar `## Resolución` apuntando al ID maestro.

El cambio de estado se hace en el **mismo commit** que la entrada de investigación / resolución, no en uno separado.

## Cómo citar evidencia

Dentro de las secciones `## Investigación` y `## Resolución`:

- **Referencias a código**: siempre `archivo:línea` (ej: `zeues-frontend/app/page.tsx:329`). Si es un rango: `archivo:inicio-fin`.
- **Identifiers / snippets**: backticks (`` `handleBatchWorkerPick` ``, `` `iniciar_spool` ``).
- **Snippets multilínea**: triple backtick con lenguaje, máximo ~20 líneas. Si necesitas más contexto, deja la referencia y describe en prosa.
- **Prohibido**: frases vagas tipo "creo que está en alguna parte de page.tsx" o "el reducer no funciona bien". Si no tienes archivo:línea, sigue investigando antes de escribir la entrada.

## Severidad

| Nivel    | Cuándo aplica |
|----------|---------------|
| `P0`     | Bloquea operación de planta. Operador no puede continuar. Datos corruptos. |
| `P1`     | Workaround existe pero es engorroso. Pierde tiempo significativo. |
| `P2`     | Molestia menor, cosmético, edge case. |
| `deuda`  | Bug técnico latente, no afecta operación todavía. |

## Cuando se cierra un bug

- **No borrar el archivo.** El historial es el activo.
- Actualizar el `estado:` en el frontmatter.
- Llenar `## Resolución` con commit + fecha + causa raíz + verificación.
- Si el bug generó tarea en ASISTENTE, dejar `tarea_relacionada: T-NNN` apuntando.
- Commit con mensaje `docs(bugs): close B-NNN — <causa raíz en una frase>`.

## Convenciones que se mantienen

- **Idioma**: español en el contenido, kebab-case en slugs, monospace en TAGs (`` `MK-1346-TW-28082-010` ``).
- **Sin emojis** en archivos del repo (regla de la organización).
- **Fechas**: ISO `YYYY-MM-DD`, no `DD/MM/YYYY` ni texto libre.
- **Hashes de commit**: forma corta de 7 caracteres salvo que haya colisión.

## Lecciones aprendidas del proceso

Reglas duras destiladas de errores reales al trabajar bugs en este folder. Cada una vino de cerrar un bug y descubrir después que no estaba resuelto.

- **Un bug no se cierra como `fixed` hasta que la verificación end-to-end manual contra la app corriendo esté documentada en `## Resolución`.** Frases tipo *"verificación pendiente tras deploy"* no cuentan como verificación — son promesas. Si no hay tiempo o medio de verificar, el estado correcto es `investigating` y se prioriza la verificación antes que el siguiente bug. Origen: B-001 cerrado prematuramente, reabierto el mismo día tras el test del operador.

- **Confianza alta en una causa raíz requiere evidencia directa, no solo razonamiento.** Una hipótesis razonable basada en lectura de código + memoria del proyecto puede merecer confianza media. Para confianza alta hace falta repro observado (Railway logs, audit sheet, DevTools, curl, etc.). Si no hay evidencia directa, marcar `(media)` o `(baja)` y dejar siguiente paso accionable. Origen: B-001 declarado con `(alta confianza)` sobre read-after-write contra Sheets API basado solo en código; al investigar el audit sheet, el timing real (6s post-INICIAR) descartaba la hipótesis.

- **Cuando un usuario reporta un síntoma sobre el listado de spools, leer el audit sheet ANTES de hipotetizar causas técnicas.** Memoria [[audit_sheet_resource]] explica el spreadsheet `ZEUES_App_Audit_PROD` con 3 tabs (`Lista`, `Audit`, `Snapshots_Legacy`). Tiene la cronología verbatim de modal opens/closes y mutaciones del tracking list — más confiable que cualquier código leído.

- **Si el código parece imposible que tenga el bug, lo más probable es que el bundle ejecutado no sea el que se está leyendo.** Antes de investigar más profundo, confirmar con el usuario: hard-refresh del tablet, servicio worker invalidado, deploy realmente activo. Origen: en B-002 podría haber sido esto (el operador confirmó hard-refresh y descartó la hipótesis, pero pude haber gastado horas investigando si no preguntaba).

## Índice

Bugs registrados (actualizar al crear / cerrar):

| ID      | Título                                                                    | Severidad | Estado | Fecha       |
|---------|---------------------------------------------------------------------------|-----------|--------|-------------|
| [B-001](./B-001-batch-iniciar-spools-quedan-libres/B-001.md) | Batch INICIAR cierra el modal sin error pero los spools quedan en estado "Libre" | P0 | investigating | 2026-05-13 |
| [B-002](./B-002-card-no-permite-avanzar-tras-iniciar.md) | Después de INICIAR la card no permite avanzar (re-abre OperationModal en lugar de ActionModal) | P0 | investigating | 2026-05-13 |
