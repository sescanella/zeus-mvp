---
id: B-002
titulo: "Después de INICIAR exitoso la card no permite avanzar (re-abre OperationModal y WorkerModal INICIAR en lugar de ActionModal FINALIZAR/PAUSAR)"
fecha_reporte: 2026-05-13
reportado_por: Operador en planta (Kronos)
severidad: P0
area: frontend
estado: investigating
commit_when_reported: d7fa7cd
produccion_o_local: produccion
archivos_sospechosos:
  - zeues-frontend/lib/SpoolListContext.tsx   # applyIniciarOptimistic — dispatch UPDATE_SPOOL no surte efecto
  - zeues-frontend/app/page.tsx               # handleWorkerComplete, handleCardClick, deriveOperation flow
  - zeues-frontend/lib/spool-state-machine.ts # deriveOperation, getValidActions — lectura de operacion_actual / ocupado_por
relacionado_con: B-001
tarea_relacionada: null
---

## Reporte del usuario

> "el bug no fue solucionado, acabo de hacer la prueba de asignar un armador a un spool libre, efectivamente se asignó el armador en la card salía armado en proceso por el armador, pasaron 30 segundos y la card de ese spool desapareció era el spool 28083-009 (algo así) revisa el sheet de auditoría. además cuando tiene el armador asignado, no me permite avanzar a una nueva etapa"

El operador también confirmó que **hizo hard-refresh del tablet antes del test**, así que el bundle del fix de B-001 (`d7fa7cd`) estaba activo durante el incidente.

## Evidencia (de `ZEUES_App_Audit_PROD`)

Memoria de referencia: [[audit_sheet_resource]] explica que el audit sheet es la fuente de verdad para incidentes sobre el listado y eventos de UI.

### `Lista` tab — la card NO desapareció

El TAG real es `MK-1346-TW-28082-010` (el operador dijo "28083-009" pero ese prefix no existe en el sheet; sí existe `28082`). Ambos `-009` y `-010` siguen presentes en `Lista`, sin `LIST_REMOVE`:

```
MK-1346-TW-28082-009    Added 13-05-2026 10:03:32    Updated 10:03:32 (nunca cambió)
MK-1346-TW-28082-010    Added 13-05-2026 10:03:57    Updated 10:03:57 (nunca cambió)
```

Lo que el operador percibió como "desapareció" probablemente fue confusión visual: las 4 cards (`-008/-009/-010/-011`) tienen el mismo NV (`NV0650`), mismo prefix, mismo `Uniones: 0`, y se ven idénticas en el tablet con reflejo (ver `B-001/01-cards-libre.png`). Cuando el poller corrió a los 30s y refrescó las cards, la del armador asignado pudo "perderse" visualmente entre las otras.

**Importante**: este síntoma es secundario / cosmético. El síntoma principal real es el segundo: "no me deja avanzar".

### `Audit` tab — secuencia que muestra el bug principal

Sesión `433599f3-f376-42bb-a60e-73216688f537`, TAG `MK-1346-TW-28082-010`, horario Chile:

| Tiempo | Evento | Modal | Interpretación |
|---|---|---|---|
| 14:08:12 | MODAL_OPEN | operation | tap card inicial (pre-INICIAR) |
| 14:08:23 | MODAL_CLOSE | operation | back/cancel |
| 14:08:45 | MODAL_OPEN | operation | reintenta |
| 14:08:47 | MODAL_CLOSE | operation | seleccionó ARMADO |
| 14:08:47 | MODAL_OPEN | worker | skipea ActionModal (1 sola acción válida: `INICIAR`) |
| **14:08:51** | **MODAL_CLOSE worker** | | **INICIAR exitoso (worker picked, modal cerró sin error)** |
| **14:08:57** | **MODAL_OPEN operation** | | **⚠️ tap card POST-INICIAR — vuelve a OperationModal en vez de ActionModal** |
| 14:08:59 | MODAL_CLOSE | operation | |
| 14:08:59 | MODAL_OPEN | worker | skipea ActionModal otra vez (sigue 1 sola acción INICIAR) |
| 14:09:03 | MODAL_CLOSE | worker | |
| ...iteración × 4 veces más... | | | operador insiste tratando de entender |
| 14:09:10 | MODAL_OPEN | worker | 8º intento |
| 14:15:51 | MODAL_CLOSE | worker | se rinde 6 min después |

## Pasos para reproducir

1. Estado inicial: spool con `estado_trabajo='LIBRE'`, `ocupado_por=null` en el sheet, agregado al supervisor list (`Lista` tab del audit sheet).
2. En la app, tap la card del spool.
3. `OperationModal` abre → tap ARMADO.
4. `WorkerModal` abre (skipea ActionModal porque `getValidActions` retorna `['INICIAR']`).
5. Tap un armador → `iniciarSpool` fires → modal cierra → toast "Operación completada" aparece.
6. **Esperado**: tap la card de nuevo → `deriveOperation` retorna `'ARM'` → `handleSelectOperation('ARM')` → `getValidActions` retorna `['FINALIZAR', 'PAUSAR']` → `ActionModal` abre con los 2 botones.
7. **Observado**: tap la card → `OperationModal` abre (idéntico al estado pre-INICIAR), y al elegir ARMADO se va directo a WorkerModal con INICIAR otra vez.

## Comportamiento

- **Esperado**: tras INICIAR exitoso, los campos `ocupado_por`, `operacion_actual='ARM'`, `estado_trabajo='EN_PROGRESO'` deben quedar reflejados en la card local. Tap subsiguiente debe abrir `ActionModal` con FINALIZAR / PAUSAR.
- **Observado**: la card local queda en estado pre-INICIAR (`ocupado_por=null`, `operacion_actual=null`). Tap subsiguiente abre `OperationModal` → re-INICIAR. La etapa no avanza.

## Hipótesis iniciales (post hard-refresh confirmado)

1. **Optimistic dispatch corre pero algo lo sobreescribe inmediatamente.** Sospechoso: re-render forzado por `modalStack.clear()` u otro setState dentro de `handleWorkerComplete` (`zeues-frontend/app/page.tsx:601-629`) que ocurre antes que el commit de `dispatch(UPDATE_SPOOL)` se observe.

2. **`spoolsRef.current.find` en `applyIniciarOptimistic` retorna undefined** → el helper bailea silenciosamente en su early return (`zeues-frontend/lib/SpoolListContext.tsx:343`). Esto requiere que `spoolsRef` no esté sincronizado con el state. Improbable porque los TAGs llevan 4+ horas en el state local antes del incidente.

3. **`worker.nombre_completo` viene undefined o vacío** del payload del backend `/api/workers` → `ocupado_por` queda como string falsy → `getValidActions` retorna `['INICIAR']` igual. Improbable porque el backend lo computa siempre como property (`backend/models/worker.py:67-98`).

4. **El dispatch nunca se llama porque hay un error JS antes** — captura silenciosa en algún try/catch alrededor de `applyIniciarOptimistic`. Requiere mirar consola en runtime.

## Investigación

### 2026-05-13 — Claude (Opus 4.7)

**Lo que se descartó**

1. **No es supervisor list removiendo el spool.** `Lista` tab tiene ambos TAGs intactos, ningún `LIST_REMOVE` en `Audit` para esta sesión.

2. **No es bundle cacheado en el tablet.** El operador confirmó hard-refresh antes del test.

3. **No es read-after-write inconsistency de Sheets** (mi hipótesis previa para B-001). El audit muestra que el síntoma ocurre **6 segundos** después de INICIAR (no 30s), bien dentro de la ventana donde Sheets API ya debería haber propagado la escritura, y antes de cualquier ejecución del poller (`zeues-frontend/app/page.tsx:153-166`, intervalo 30s).

4. **No es un bug en `getValidActions` o `deriveOperation`.** El segundo Explore agent verificó que estas funciones leen únicamente `ocupado_por` (`zeues-frontend/lib/spool-state-machine.ts:40-45`) y `operacion_actual` (`:75-93`) respectivamente. Si esos campos están seteados correctamente en el state local, las funciones devuelven los valores correctos y el flujo correcto se ejecuta.

**Lo que se confirmó**

1. **El optimistic dispatch no está produciendo el efecto observable esperado.** El audit muestra que post-INICIAR los campos `ocupado_por` y `operacion_actual` están vacíos/null en el frontend, exactamente como antes de INICIAR. Esto se deduce de:
   - `MODAL_OPEN operation` se dispara post-INICIAR → `deriveOperation` retornó null → `operacion_actual` era null/undefined.
   - Después de OperationModal → `MODAL_OPEN worker` sin `MODAL_OPEN action` intermedio → `getValidActions` retornó 1 acción (`['INICIAR']`) → `ocupado_por` era null/empty.

2. **El fix de B-001 (`4dbb810` + `d7fa7cd`) no resolvió el síntoma reportado.** Por eso B-001 vuelve a `estado: investigating`.

3. **Mi diagnóstico de causa raíz para B-001 estaba mal o incompleto.** El timing del bug (6s, no 30s) descarta read-after-write contra Sheets. La causa real está en el frontend y aún no la tengo identificada con certeza.

**Causa raíz propuesta** — `(baja confianza — necesita repro con DevTools)`

No tengo causa raíz confirmada. Las 4 hipótesis arriba son candidatas pero ninguna está validada empíricamente. Cualquiera de ellas requeriría una verificación específica en runtime que no puedo hacer leyendo código solo.

**Siguiente paso**

Antes de tocar más código:

1. Repro del flujo con **DevTools / consola abierta**. Probar en una laptop conectada al mismo backend de prod, o Chrome DevTools sobre el tablet via USB debugging. Capturar:
   - Network tab: confirmar status 200 del POST `/api/v4/occupation/iniciar`, body de la response.
   - Consola: cualquier error o warning de React.
   - React DevTools: inspeccionar el state `spools` del componente HomePage **inmediatamente después** del INICIAR exitoso. Confirmar qué valores tiene `spools[tag=...28082-010]` en los 5 campos que `applyIniciarOptimistic` debería haber seteado: `ocupado_por`, `ocupado_por_display`, `fecha_ocupacion`, `operacion_actual`, `estado_trabajo`.
2. Si los 5 campos están correctos en el state pero el siguiente tap-card aún abre OperationModal → bug en el flujo de re-render / closure entre `applyIniciarOptimistic` y `handleCardClick`.
3. Si los 5 campos están vacíos/null en el state → `applyIniciarOptimistic` no corrió o el dispatch fue silenciosamente revertido. Investigar el orden de operaciones en `handleWorkerComplete`.
4. Si el response del backend no es 200 → el INICIAR está fallando silenciosamente y `iniciarSpool` (en `zeues-frontend/lib/api.ts`) no está propagando el error como exception. Bug separado.

Cuando haya evidencia directa, abrir plan de fix con causa raíz confirmada.

## Resolución

(Vacío — bug abierto en `investigating`. No se cerrará hasta que la verificación end-to-end con el síntoma resuelto esté documentada aquí.)
