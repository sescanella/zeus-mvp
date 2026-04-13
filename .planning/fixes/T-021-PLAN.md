---
id: T-021
title: Fix flujo parcial ARM/SOLD con bloqueo estricto a metrología
type: bug-fix
severity: critical
created: 2026-04-13
scope: backend + frontend + data remediation
---

# T-021 — Plan de implementación

## 1. Resumen ejecutivo

Bug crítico: spools con trabajo ARM/SOLD parcial son marcados como COMPLETADOS, se les escribe `Fecha_Armado`/`Fecha_Soldadura`, y quedan elegibles para METROLOGIA sin haber terminado todas las uniones.

**Causa raíz:** `_determine_action()` en `occupation_service.py` compara `selected_count` contra un `total_available` que refleja solo las uniones "trabajables ahora" (post-filtro por tipo SOLD-required y por ARM ya terminado), no contra `Total_Uniones` del spool. Cuando el operador termina el batch disponible, se marca COMPLETAR aunque queden uniones pendientes.

Un factor agravante es el **legacy SOLD fallback** (`occupation_service.py:1143-1150`) que se activa cuando `spool.fecha_armado` está seteada pero las uniones no tienen `arm_fecha_fin`. Si quedan uniones sin ARM rastreado, el fallback las incluye — pero las filas con ARM parcial real producen el subconteo observado en producción.

**Fix en 4 frentes:**
1. Backend: `_determine_action` y `finalizar_spool` contrastan contra `Total_Uniones` real.
2. Backend: no escribir `Fecha_Armado`/`Fecha_Soldadura` hasta completitud total.
3. Backend: filtro MET bloquea completamente si faltan uniones.
4. Frontend: `completion_history` distingue "completado" de "parcial X/Y".
5. Data: script dry-run + apply para limpiar los 2 spools corruptos.

## 2. Spools corruptos confirmados

| TAG_SPOOL | Total_Uniones | Uniones_SOLD_Completadas | Fecha_Soldadura (incorrecta) |
|---|---|---|---|
| MK-1923-TW-17422-004 | 7 | 2 | 10/4/2026 |
| MK-1923-TK-34058-001 | 7 | 3 | 9/4/2026 |

Ambos aparecen en P4 METROLOGIA y muestran "SOLD completado" en la card del home pese a tener 5 y 4 uniones sin soldar respectivamente.

## 3. Archivos afectados

### Backend
- `backend/services/occupation_service.py` — `_determine_action` (815-856), `finalizar_spool` flujo ARM/SOLD (1127-1165, 1278-1285, 1463-1487)
- `backend/services/filters/common_filters.py` — `SOLDCompletionFilter` (199-230), `ARMCompletionFilter` (258+)
- `backend/repositories/union_repository.py` — `calculate_metrics` y `get_total_uniones`
- `backend/models/spool_status.py` — `_build_completion_history` (138-186)

### Frontend
- `zeues-frontend/components/SpoolCard.tsx` — `completion_history` render (299-308). Ya tiene badges parciales (275-297), no se tocan.
- `zeues-frontend/lib/types.ts` — `CompletionEntry` (si hace falta agregar campos `kind: 'complete' | 'partial'` y `progress: string`).

### Data / scripts
- `backend/scripts/remediate_T021_corrupt_spools.py` (NUEVO)

### Tests
- `tests/unit/services/test_occupation_service_partial_completion.py` (NUEVO)
- `tests/unit/services/test_metrologia_transition.py` (EXISTENTE — extender)
- `tests/unit/filters/test_sold_completion_filter.py` (NUEVO o extender existente)
- `tests/integration/test_partial_sold_blocks_metrologia.py` (NUEVO)
- `zeues-frontend/tests/SpoolCard.completion.spec.ts` (NUEVO unit/component)

---

## 4. Plan por olas (waves)

### Wave 1 — Diagnóstico & tests rojos (paralelizable)

Objetivo: escribir TESTS que reproduzcan el bug y queden en ROJO antes de tocar lógica.

#### Plan 1.1 — Test unitario `_determine_action` reproduce bug
**Archivo:** `tests/unit/services/test_occupation_service_partial_completion.py`

Casos que deben quedar en ROJO (antes del fix):
- `test_sold_2_of_7_unions_should_pausar_not_completar`: mock spool con `Total_Uniones=7`, pasa `selected_count=2, total_available=2` (simula batch disponible recortado) → actualmente retorna COMPLETAR, debe retornar PAUSAR.
- `test_arm_3_of_7_unions_should_pausar_not_completar`: análogo para ARM.
- `test_sold_7_of_7_returns_completar`: sanity check del happy path.
- `test_pausar_when_total_uniones_is_zero_legacy_spool`: spools v3.0 con `Total_Uniones=0` deben seguir comportándose como antes (no regresión).

Dependencia: ninguna. Puede escribirse en paralelo a Plan 1.2.

#### Plan 1.2 — Test integración `finalizar_spool` no escribe `Fecha_Soldadura` con trabajo parcial
**Archivo:** `tests/integration/test_partial_sold_blocks_metrologia.py`

- `test_finalizar_sold_partial_does_not_write_fecha_soldadura`: fixture con spool 7 uniones, 2 con ARM+SOLD simulado, llama `finalizar_spool` con `selected_unions=[u1.id, u2.id]`. Verifica que mocks de sheets NO reciban update para `Fecha_Soldadura`, `Soldador`. Verifica `Estado_Detalle` contiene "parcial".
- `test_finalizar_sold_all_unions_writes_fecha_soldadura`: happy path, 7/7, escribe `Fecha_Soldadura`.
- `test_sold_completion_filter_rejects_2_of_7_spool`: construye `Spool` con `total_uniones=7, uniones_sold_completadas=2, fecha_soldadura=None` y `SOLDCompletionFilter` debe retornar `passed=False`.
- `test_sold_completion_filter_rejects_stale_fecha_soldadura`: `Spool` con `total_uniones=7, uniones_sold_completadas=2, fecha_soldadura="10-04-2026"` (el estado corrupto observado) — filtro debe retornar `passed=False`. Esto requiere reforzar el filtro (ver Plan 2.3).

Dependencia: ninguna. Corre tras Plan 1.1 o en paralelo.

#### Plan 1.3 — Test frontend: `completion_history` parcial
**Archivo:** `zeues-frontend/tests/SpoolCard.completion.spec.ts`

- `renders "ARM parcial 3/7" when arm partial`: entrada con `completion_history: [{operation: "ARM parcial 3/7", ...}]` → render en verde? (decisión: ver Plan 3.1 — parciales en amarillo, completos en verde).
- `renders "SOLD completado" only when 7/7`: sanity check.

Dependencia: puede escribirse en paralelo, pero ejecutarse tras Plan 3.1.

---

### Wave 2 — Fix backend (secuencial dentro, paralelo entre planes)

#### Plan 2.1 — Arreglar `_determine_action` contra `Total_Uniones` real
**Archivo:** `backend/services/occupation_service.py:815-856` y llamador `:1278-1285`

Cambio:
- `_determine_action` recibe un 4º parámetro `total_uniones_spool: int` (el total real del spool, no el disponible filtrado).
- Nueva regla: `COMPLETAR` solo si `ya_completadas + selected_count == total_uniones_spool`. En otro caso, `PAUSAR`.
- Para ARM: `ya_completadas = Uniones_ARM_Completadas` del spool antes de este batch.
- Para SOLD: `ya_completadas = Uniones_SOLD_Completadas` del spool antes de este batch.
- Race condition (`selected_count > total_available`) se mantiene.

En `finalizar_spool` (línea 1278-1285):
- Leer `spool.uniones_arm_completadas` / `spool.uniones_sold_completadas` y `spool.total_uniones` antes del batch.
- Si `total_uniones == 0` (spool v3.0 legacy sin uniones cargadas): caer al comportamiento actual (`selected == total_available` → COMPLETAR) SOLO para no romper spools legacy. Loggear warning.
- Si `total_uniones >= 1`: aplicar regla estricta.

**Verificación:** tests del Plan 1.1 pasan a VERDE.

**Dependencia:** bloquea Plan 2.2.

#### Plan 2.2 — No escribir `Fecha_Armado` / `Fecha_Soldadura` con trabajo parcial
**Archivo:** `backend/services/occupation_service.py:1463-1487`

El bloque actual ya condiciona la escritura a `action_taken == "COMPLETAR"`. Con Plan 2.1 ya resuelto, esto queda correcto por transitividad. Pero añadir **guard defensivo**:
- Antes de `updates_dict.update({"Fecha_Soldadura": ...})`: revalidar que `spool.uniones_sold_completadas + len(selected_unions) == spool.total_uniones` (o `spool.total_uniones == 0` para legacy). Si no, log ERROR y forzar `action_taken = "PAUSAR"` (falla segura).
- Análogo para ARM con `Fecha_Armado`.

Esto previene regresiones futuras y cubre el caso de `action_override="COMPLETAR"` viniendo del frontend (línea 1174-1186): si el frontend lo manda con información desincronizada, el backend rechaza.

**Verificación:** test `test_finalizar_sold_partial_does_not_write_fecha_soldadura` pasa a VERDE.

**Dependencia:** Plan 2.1.

#### Plan 2.3 — Endurecer `SOLDCompletionFilter` y `ARMCompletionFilter`
**Archivo:** `backend/services/filters/common_filters.py:199-230` y `ARMCompletionFilter` análogo

Cambio: cuando `Total_Uniones >= 1` (v4.0), IGNORAR `Fecha_Soldadura` y chequear **solamente** `uniones_sold_completadas == total_uniones`. Esto hace que los 2 spools corruptos (con `Fecha_Soldadura` escrita incorrectamente y 2/7 contadores) queden automáticamente excluidos del filtro MET mientras no se remedien.

Para v3.0 (`Total_Uniones == 0`): mantener chequeo por `Fecha_Soldadura` (no hay contadores).

Análogo para `ARMCompletionFilter` (usado por SOLD INICIAR).

**Nota importante:** el filtro actual en v4.0 (línea 222) **ya hace** `uniones_sold == total_uniones`. El bug no está en el filtro, está en que el *contador* se escribe correctamente (2/7) pero `Fecha_Soldadura` también se escribe (incorrectamente, confundiendo al frontend que muestra "SOLD completado" vía `_build_completion_history`). Entonces el filtro MET en backend ya bloquea correctamente los 2 spools (contador 2/7 < 7). Lo que falla es el mensaje en la card del home. **Verificar en browser MCP**: ¿realmente los 2 spools están apareciendo en P4 MET, o solo muestran "SOLD completado" en el home?

Acción: agregar test `test_sold_completion_filter_blocks_v4_despite_fecha_soldadura_set` que confirma el filtro YA bloquea. Si el test pasa sin cambios de código, **este plan queda como documentación y no cambia código**. Si falla, hay otro bug en el filtro.

**Dependencia:** paralelo a Plan 2.1 y 2.2.

#### Plan 2.4 — Revisar `legacy_sold_mode` fallback
**Archivo:** `backend/services/occupation_service.py:1142-1150`

El fallback actual activa cuando `len(all_disponibles) == 0 AND spool.fecha_armado` — recalcula disponibles como "todas las que no tienen SOL_FECHA_FIN". Esto NO aplica al caso de MK-1923-TW-17422-004 porque ese spool SÍ tiene uniones disponibles (las 5 sin ARM completo). Pero conviene:
- Loggear explícitamente cuando el fallback se activa, con `total_uniones` y counts.
- Añadir test `test_legacy_sold_fallback_still_respects_total_uniones` asegurando que aun en modo legacy, `_determine_action` contrasta contra `total_uniones` real.

**Dependencia:** Plan 2.1.

---

### Wave 3 — Fix frontend

#### Plan 3.1 — `_build_completion_history` distingue completo vs parcial
**Archivo:** `backend/models/spool_status.py:138-186`

Cambios:
- Leer `spool.uniones_arm_completadas`, `spool.uniones_sold_completadas`, `spool.total_uniones`.
- Si `total_uniones >= 1` (v4.0):
  - ARM entry solo se agrega si `uniones_arm_completadas >= 1`. Operación:
    - `uniones_arm_completadas == total_uniones` → `"ARM completado"`
    - else → `"ARM parcial {arm_completadas}/{total_uniones}"`
  - SOLD entry análogo.
  - Worker/date: usar `armador` / `soldador` y `fecha_armado` / `fecha_soldadura` si están. Si en parcial no están (porque Plan 2.2 no los escribió), usar `"—"` para date y `"—"` para worker (o buscar el último ARM_WORKER/SOL_WORKER de las uniones — ver decisión más abajo).
- Si `total_uniones == 0` (v3.0 legacy): mantener comportamiento actual basado en `fecha_armado`/`fecha_soldadura` puros.

**Decisión de producto:** en parcial, ¿qué worker mostrar?
- Opción A: el worker de la última unión actualizada (último `SOL_WORKER` con `SOL_FECHA_FIN` no nulo). Requiere `union_repository.get_by_spool`.
- Opción B: omitir worker en parciales, mostrar solo "SOLD parcial 3/7 — 09/04".

Recomiendo **Opción A** (más info para el operador). Se puede agregar en `_build_completion_history` inyectando unions resueltas.

**Verificación:** test `SpoolCard.completion.spec.ts` con fixture v4.0 parcial renderiza "ARM parcial 3/7 — NR — 09/04".

**Dependencia:** Plan 2.1 y 2.2 (para asegurar que el backend dejó de escribir `Fecha_Armado` incorrectamente, así el fallback v3.0 no se confunde).

#### Plan 3.2 — Color amarillo para `completion_history` parcial
**Archivo:** `zeues-frontend/components/SpoolCard.tsx:299-308`

Cambio: agregar campo `kind: 'complete' | 'partial'` a `CompletionEntry` (en `lib/types.ts` y `backend/models/spool_status.py`). Render:
```tsx
className={`font-mono text-sm ${entry.kind === 'partial' ? 'text-yellow-400' : 'text-green-400'}`}
```

Esto complementa los badges de arriba (275-297) que ya distinguen parcial/completo. El `completion_history` es el mensaje que menciona el usuario ("mensajes verdes que dicen ARM completado").

**Dependencia:** Plan 3.1.

---

### Wave 4 — Remediación de datos

#### Plan 4.1 — Script dry-run + apply para 2 spools corruptos
**Archivo nuevo:** `backend/scripts/remediate_T021_corrupt_spools.py`

Comportamiento:
- Hardcodea lista: `["MK-1923-TW-17422-004", "MK-1923-TK-34058-001"]`. No busca otros.
- Para cada spool:
  1. Lee fila actual de Operaciones.
  2. Verifica precondiciones: `Total_Uniones >= 1`, `Uniones_SOLD_Completadas < Total_Uniones`, `Fecha_Soldadura` no vacía. Si no cumple → SKIP con warning.
  3. Calcula nuevo `Estado_Detalle` usando misma lógica que Plan 3.1 → `"SOLD parcial {X}/{Y}"`.
  4. Dry-run (default): imprime el diff propuesto en tabla. No aplica.
  5. `--apply`: ejecuta `sheets_repository.batch_update_by_column_name` con:
     - `Fecha_Soldadura` → `""`
     - `Soldador` → `""` (también estaba incorrecto)
     - `Estado_Detalle` → `"SOLD parcial {X}/{Y}"`
  6. Loggea evento manual a Metadata: `T021_REMEDIATION` con metadata `{operacion: "SOLD", previous_fecha_soldadura, previous_soldador, new_uniones_sold_completadas}`.

Uso:
```bash
# Dry-run
python backend/scripts/remediate_T021_corrupt_spools.py

# Apply (tras revisar dry-run)
python backend/scripts/remediate_T021_corrupt_spools.py --apply
```

**Verificación:**
- Post-apply, el browser en producción muestra los 2 spools como "SOLD parcial 2/7" / "SOLD parcial 3/7" en amarillo.
- P4 METROLOGIA no los lista (si no los listaba ya por Plan 2.3, esto confirma consistencia).

**Dependencia:** Wave 3 debe estar desplegada en producción ANTES de ejecutar `--apply`, para que el frontend ya sepa renderizar parciales correctamente. Alternativa: ejecutar dry-run ahora, apply después del deploy de Wave 3.

---

### Wave 5 — Verificación E2E y despliegue

#### Plan 5.1 — Verificación manual en producción
Con browser MCP tras deploy de Waves 1-3:
1. `browser_navigate https://zeues-frontend.vercel.app` → confirmar que los 2 spools muestran "SOLD parcial X/7" (amarillo) en vez de "SOLD completado" (verde).
2. Seleccionar operación METROLOGIA en home → confirmar que los 2 spools NO aparecen.
3. Test positivo: elegir un spool con 7/7 soldadas real → aparece en MET.
4. Inspeccionar Sheets: `Fecha_Soldadura` en fila de los 2 spools corruptos vacía tras Wave 4 `--apply`.

#### Plan 5.2 — Checklist de despliegue
- [ ] Tests Wave 1 en ROJO confirmado antes de Wave 2.
- [ ] Tests Wave 1 en VERDE tras Wave 2.
- [ ] `npx tsc --noEmit` y `npm run lint` pasan tras Wave 3.
- [ ] `python backend/scripts/validate_schema_startup.py` pasa.
- [ ] `pytest tests/unit/ -v` pasa completo.
- [ ] Deploy backend a Railway.
- [ ] Deploy frontend a Vercel.
- [ ] Dry-run de Wave 4 revisado por humano.
- [ ] Apply de Wave 4 con `--apply`.
- [ ] Plan 5.1 ejecutado.

---

## 5. Criterios de éxito (goal-backward)

El plan está COMPLETO cuando:

1. ✅ Un spool con N uniones y K < N soldadas NO puede tener `Fecha_Soldadura` escrita ni aparecer en P4 MET, sin importar cómo se llegue ahí (flujo normal, `action_override`, legacy fallback).
2. ✅ La card del home de los 2 spools corruptos dice "SOLD parcial 2/7" (amarillo) y no "SOLD completado" (verde).
3. ✅ Suite de tests incluye al menos: 4 tests unit `_determine_action`, 3 tests integration `finalizar_spool`, 2 tests filter, 2 tests frontend component. Todos en verde.
4. ✅ Script de remediación ejecutado en `--apply` y verificado en producción.
5. ✅ Usuario (tú) confirma en app real que el comportamiento es el esperado.

## 6. Riesgos y mitigaciones

| Riesgo | Probabilidad | Mitigación |
|---|---|---|
| Plan 2.1 rompe spools v3.0 legacy (Total_Uniones=0) | media | Rama explícita `if total_uniones == 0` mantiene comportamiento actual + test de regresión |
| `action_override="COMPLETAR"` del frontend envía contadores desincronizados | media | Guard defensivo en Plan 2.2 |
| Plan 4.1 `--apply` ejecutado antes de desplegar Wave 3 | alta (error humano) | Checklist 5.2 + script imprime warning si detecta que frontend no muestra "parcial" aún (opcional: health-check) |
| Otros spools corruptos más allá de los 2 detectados | baja (el usuario confirmó que no busquemos) | Fuera de alcance explícito. Si aparecen, crear T-022 |
| `_build_completion_history` Opción A (worker de última unión) requiere llamada extra a UnionRepository por spool en el listado del home | media (perf) | Cachear unions por spool o precomputar en endpoint que ya lee unions. Si el impacto es alto, caer a Opción B. |

## 7. Fuera de alcance

- Marcar uniones como "fuera de alcance" (diferido a milestone futuro).
- Búsqueda automática de más spools corruptos.
- Cambios al schema de Uniones.
- Refactor del legacy SOLD fallback (línea 1142-1150) — solo se audita en Plan 2.4, no se reescribe.

## 8. Orden de ejecución recomendado

```
Wave 1 (paralelo: 1.1, 1.2, 1.3) → commit "test: T-021 red tests"
Wave 2 (secuencial: 2.1 → 2.2; paralelo: 2.3, 2.4) → commit por plan
Wave 3 (secuencial: 3.1 → 3.2) → commit por plan
Deploy backend + frontend
Wave 4 dry-run → revisar → --apply → commit "chore: T-021 remediate corrupt spools"
Wave 5 verificación
```

Commits atómicos, mensajes con prefijo `fix(T-021):` o `test(T-021):`.
