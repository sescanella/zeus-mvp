# Análisis Histórico: Error 400 PAUSAR - Intentos de Solución

**Fecha:** 2026-01-30
**Estado Actual:** Error 400 persiste en producción después de 3 intentos de solución
**Commits Analizados:** 9e747d6, ac64c55, 8143499, 3b51b2f, 9eb246c, 6748fd1

---

## Resumen Ejecutivo

Se han realizado **4 intentos distintos de solucionar** el Error 400 en PAUSAR durante las últimas horas. A pesar de aplicar 3 fixes secuenciales (commits 8143499, ac64c55, 9e747d6), **el error persiste en producción**.

### Cronología de Fixes

1. **Commit 8143499** (12:22) - Cache invalidation fix
2. **Commit ac64c55** (13:20) - Edge case inconsistent state fix
3. **Commit 9e747d6** (13:37) - activate_initial_state() ordering fix
4. **Commit 931b50a** (ahora) - Investigation report (este análisis)

**Resultado:** Ninguno de los 3 fixes anteriores ha resuelto el problema en producción.

---

## Análisis de Cada Intento de Solución

### Fix #1: Cache Invalidation (Commit 8143499)

**Debug Document:** `.planning/debug/resolved/pausar-error-400-correct-flow.md`

#### Hipótesis
> "TOMAR escribe Armador via state machine callback que usa `update_cell_by_column_name()`, pero este método NO invalida cache. PAUSAR lee datos stale del cache con armador=null, hydrata a PENDIENTE, falla validación."

#### Solución Implementada
```python
# backend/repositories/sheets_repository.py línea 418-422
async def update_cell_by_column_name(...):
    # ... update logic ...

    # ✅ FIX: Invalidate cache to ensure fresh data on next read
    cache_key = f"worksheet:{sheet_name}"
    self._cache.invalidate(cache_key)
```

#### ¿Por qué falló?
**El análisis fue correcto pero incompleto.** La invalidación de cache SÍ era necesaria, pero **no era la causa raíz del error actual**.

El error que vemos en producción dice:
```
"Cannot PAUSAR ARM from state 'pendiente'"
```

Esto significa que cuando `StateService.pausar()` hydrata el spool:
- `spool.armador` es `None` O
- `spool.ocupado_por` es `None`/`""`

Si fuera solo un problema de cache, el cache invalidado habría resuelto el issue. **El hecho de que persista indica un problema de estado más fundamental.**

---

### Fix #2: Edge Case Inconsistent State (Commit ac64c55)

**Debug Document:** `.planning/debug/resolved/pausar-error-400-invalid-state.md`

#### Hipótesis
> "Spool en estado inconsistente: `Ocupado_Por='MR(93)'` pero `Armador=None`. Ocurre cuando TOMAR falla parcialmente: escribe Ocupado_Por exitosamente pero el callback de state machine falla al escribir Armador. Rollback incompleto deja spool en estado inconsistente."

#### Solución Implementada
```python
# backend/services/state_service.py línea 475-489
async def _hydrate_arm_machine(self, spool):
    # ... existing logic ...

    elif spool.ocupado_por and spool.ocupado_por != "":
        # ✅ FIX: EDGE CASE - Ocupado_Por set but Armador=None
        # Treat as EN_PROGRESO to allow PAUSAR recovery
        machine.current_state = machine.en_progreso
        logger.warning(
            f"⚠️ INCONSISTENT STATE DETECTED: {spool.tag_spool} has "
            f"Ocupado_Por='{spool.ocupado_por}' but Armador=None. "
            f"Hydrating to EN_PROGRESO to allow recovery via PAUSAR."
        )
```

#### ¿Por qué falló?
**El fix fue implementado correctamente, pero luego fue DESHECHO por otro problema.**

Según `.planning/debug/pausar-fix-validation-failed.md` línea 49-55:

> "Local test of TOMAR->PAUSAR flow with TEST-02:
> - Warning logged 'INCONSISTENT STATE DETECTED' ✅ (fix IS executing)
> - But still fails with 'state pendiente' ❌ (state is being RESET)"

**Hallazgo crítico:** El edge case fix SÍ ejecuta (línea 491 setea `machine.current_state = machine.en_progreso`), pero **el estado es reseteado inmediatamente después**.

---

### Fix #3: activate_initial_state() Ordering (Commit 9e747d6)

**Debug Document:** `.planning/debug/pausar-fix-validation-failed.md`

#### Hipótesis Confirmada
> "activate_initial_state() is resetting the machine to PENDIENTE after hydration sets it to EN_PROGRESO"

Análisis detallado (línea 50-56 del debug doc):

```
StateService.pausar() line 295:
- Calls await arm_machine.activate_initial_state() AFTER hydration
- This RESETS the machine back to PENDIENTE
- Undoing the hydration that set it to EN_PROGRESO
```

#### Solución Implementada
```python
# backend/services/state_service.py línea 455-468

async def _hydrate_arm_machine(self, spool):
    machine = ARMStateMachine(...)

    # ✅ FIX: Activate initial state FIRST (before setting current_state)
    await machine.activate_initial_state()

    # THEN manually override current_state to hydrate from Sheets
    if spool.fecha_armado:
        machine.current_state = machine.completado
    elif spool.armador:
        # ... hydration logic ...
```

**Cambio clave:** Movió `activate_initial_state()` DENTRO de los métodos de hydration (`_hydrate_arm_machine` y `_hydrate_sold_machine`) para llamarlo ANTES de setear `current_state`.

#### Estado Actual en Código
```bash
$ grep -n "activate_initial_state" backend/services/state_service.py
457:        await machine.activate_initial_state()  # ✅ Inside _hydrate_arm_machine
523:        await machine.activate_initial_state()  # ✅ Inside _hydrate_sold_machine
```

**Ya no hay llamadas a `activate_initial_state()` en `tomar()`, `pausar()`, o `completar()`.**

---

## Estado Actual del Código (Post-Fixes)

### Hydration Logic Actual

```python
# backend/services/state_service.py líneas 455-493
async def _hydrate_arm_machine(self, spool):
    machine = ARMStateMachine(...)

    # Step 1: Initialize machine (required by python-statemachine 2.5.0)
    await machine.activate_initial_state()  # ← FIX #3

    # Step 2: Override state based on Sheets data
    if spool.fecha_armado:
        machine.current_state = machine.completado
    elif spool.armador:
        if spool.ocupado_por is None or spool.ocupado_por == "":
            machine.current_state = machine.pausado
        else:
            machine.current_state = machine.en_progreso
    elif spool.ocupado_por and spool.ocupado_por != "":
        # ← FIX #2: Edge case for inconsistent state
        machine.current_state = machine.en_progreso
        logger.warning("⚠️ INCONSISTENT STATE DETECTED...")
    else:
        # State remains PENDIENTE (default from activate_initial_state)
        pass
```

### PAUSAR Validation Actual

```python
# backend/services/state_service.py líneas 290-303
async def pausar(self, request):
    # ... fetch spool, hydrate machines ...

    if operacion == ActionType.ARM:
        current_arm_state = arm_machine.get_state_id()

        # ❌ STRICT validation - only accepts 'en_progreso'
        if current_arm_state != "en_progreso":
            raise InvalidStateTransitionError(
                f"Cannot PAUSAR ARM from state '{current_arm_state}'. "
                f"PAUSAR is only allowed from 'en_progreso' state.",
                tag_spool=tag_spool,
                current_state=current_arm_state,
                attempted_transition="pausar"
            )
```

---

## ¿Por Qué los Fixes No Funcionaron?

### Análisis de Divergencia: Debug Docs vs. Realidad

Los debug documents asumen que después de aplicar cada fix, el problema está resuelto:

1. **pausar-error-400-correct-flow.md** (commit 8143499)
   - Status: `resolved` ✅
   - Verification: "Fix applied, all PAUSAR tests passing" ✅
   - **Pero:** Error 400 persiste en producción ❌

2. **pausar-error-400-invalid-state.md** (commit ac64c55)
   - Status: `resolved` ✅
   - Verification: "Fix committed and pushed to Railway" ✅
   - **Pero:** Error 400 persiste en producción ❌

3. **pausar-fix-validation-failed.md** (commit 9e747d6)
   - Status: `verifying` ⚠️
   - Next action: "Fix the code by moving activate_initial_state()" ✅
   - **Pero:** Error 400 AÚN persiste en producción ❌

### Hipótesis: ¿Por qué persiste el error?

#### Posibilidad #1: Deployment Gap
Los fixes están en `main` branch pero no están desplegados en Railway/Vercel production.

**Test:**
```bash
git log --oneline -5
# 9e747d6 fix: resolve PAUSAR hydration state reset bug  ← Último fix
# ac64c55 fix: handle inconsistent state in PAUSAR...
# 8143499 fix: resolve PAUSAR Error 400 with cache...

# ¿Está este código en producción?
curl https://zeues-backend-mvp-production.up.railway.app/api/health
```

#### Posibilidad #2: El problema NO es hydration
Los 3 fixes asumen que el problema es hydration (cache, edge case, activate ordering).

**Pero ¿y si el problema es anterior?**

Mirando el error:
```
"Cannot PAUSAR ARM from state 'pendiente'"
```

Esto significa que cuando PAUSAR lee el spool de Google Sheets:
- **Hipótesis A:** `Ocupado_Por` está vacío (lock expiró o fue liberado)
- **Hipótesis B:** `Armador` está vacío (TOMAR nunca completó)
- **Hipótesis C:** Ambos vacíos (spool nunca fue tomado)

**Verificación directa necesaria:**
```sql
SELECT TAG_SPOOL, Ocupado_Por, Armador, Fecha_Armado
FROM Operaciones
WHERE TAG_SPOOL = 'TEST-02'
```

#### Posibilidad #3: Lock TTL Expired (Redis)
El lock de Redis tiene TTL de 1 hora (3600 segundos).

Si el usuario hizo TOMAR hace >1 hora:
1. TOMAR escribe `Ocupado_Por='MR(93)'` y `Armador='MR(93)'`
2. Redis lock expira después de 1 hora
3. Sistema detecta lock expirado y **limpia Ocupado_Por** (posible cleanup job?)
4. PAUSAR lee spool con `Armador='MR(93)'` pero `Ocupado_Por=''`
5. Hydration: `elif spool.armador:` → `if spool.ocupado_por is None or spool.ocupado_por == "":` → **PAUSADO**
6. Validation falla: `current_arm_state='pausado'` != `'en_progreso'`

**WAIT.** El error dice `state='pendiente'`, no `'pausado'`.

Entonces debe ser:
- `Armador=None` Y `Ocupado_Por=None/""` → hydrates to PENDIENTE

#### Posibilidad #4: Frontend enviando operacion incorrecta
Si frontend envía `operacion='SOLD'` cuando debería ser `'ARM'`:
- Backend hydrata SOLD machine (no ARM)
- SOLD machine está en PENDIENTE
- Error: "Cannot PAUSAR SOLD from state 'pendiente'"

**Verificación:**
```typescript
// zeues-frontend/app/confirmar/page.tsx línea 289-295
const response = await pausarOcupacion({
  tag_spool: selectedSpool.tag_spool,
  worker_id: context.workerId!,
  worker_nombre: context.workerNombre!,
  operacion: context.operacion!  // ← ¿Qué valor tiene?
});
```

---

## Patrón Problemático Detectado

### El Ciclo de Debugging Incompleto

**Cada debug session sigue este patrón:**

1. ✅ Reproduce error localmente o en producción
2. ✅ Lee código fuente y encuentra una causa posible
3. ✅ Implementa fix
4. ✅ Tests unitarios pasan
5. ❌ **NO verifica el fix en producción con datos reales**
6. ✅ Marca como "resolved"
7. ❌ Error persiste en producción
8. 🔄 Repeat

**Falta crítica:** Ningún debug document incluye:
- Verificación con `curl` en production después del deploy
- Inspección de datos reales en Google Sheets para TEST-02
- Logs de producción mostrando el fix funcionando

### Red Flags

1. **pausar-fix-validation-failed.md** línea 60-66:
   ```
   root_cause: "activate_initial_state() resets machine after hydration"
   fix: "Moved activate_initial_state() INSIDE hydration methods"
   verification: "Fix committed (9e747d6) and pushed to Railway.
                 Waiting for deployment... The fix is sound."
   ```

   **Problema:** Dice "waiting for deployment" pero marca status como "verifying", luego nunca actualiza con resultado real.

2. **Todos los debug docs** asumen que si:
   - ✅ Fix aplicado
   - ✅ Tests pasan
   - ✅ Commit pushed

   Entonces ✅ Problema resuelto.

   **Pero no verifican contra producción real.**

---

## Conclusiones

### Fixes Implementados (Código Actual)

1. ✅ **Cache invalidation** (commit 8143499)
   - `update_cell_by_column_name()` ahora invalida cache
   - Correcto, necesario, pero no resolvió el issue

2. ✅ **Edge case handling** (commit ac64c55)
   - Hydration detecta `Ocupado_Por` set + `Armador` None
   - Setea state a `EN_PROGRESO` para permitir recovery
   - Correcto, necesario, pero no resolvió el issue

3. ✅ **activate_initial_state() ordering** (commit 9e747d6)
   - Llamado ANTES de setear `current_state` en hydration
   - Previene reset del estado hydratado
   - Correcto, necesario, pero **¿resolvió el issue?** NO VERIFICADO

### Root Cause Real (Hipótesis Actualizada)

**El problema NO es hydration logic.** Los 3 fixes mejoran el código pero no atacan la causa raíz.

**Nueva hipótesis basada en evidencia:**

El error `"Cannot PAUSAR ARM from state 'pendiente'"` indica que:
- `spool.armador = None`
- `spool.ocupado_por = None` o `""`

Esto significa que **el spool NO está ocupado cuando PAUSAR es llamado.**

**Escenarios posibles:**

1. **Lock expiró (TTL 1h) y se limpió Ocupado_Por**
   - Sistema automático detecta lock expirado
   - Limpia `Ocupado_Por` de Google Sheets
   - Usuario intenta PAUSAR pero spool ya está liberado

2. **Usuario nunca hizo TOMAR correctamente**
   - Frontend muestra TEST-02 como seleccionado
   - Pero TOMAR nunca ejecutó exitosamente
   - `Armador` y `Ocupado_Por` están vacíos

3. **TOMAR falló silenciosamente**
   - TOMAR devolvió error pero frontend no mostró
   - Usuario procede a PAUSAR pensando que TOMAR funcionó
   - Backend rechaza porque spool no está ocupado

4. **Race condition: PAUSAR llamado antes de TOMAR commit**
   - Frontend llama PAUSAR inmediatamente después de TOMAR
   - TOMAR aún no terminó de escribir a Sheets
   - PAUSAR lee estado anterior (vacío)

---

## Recomendaciones

### Debugging Inmediato

1. **Verificar estado real de TEST-02 en Google Sheets:**
   ```python
   # Leer directamente del sheet (no cache)
   spool = sheets_repo.get_spool_by_tag("TEST-02", bypass_cache=True)
   print(f"Armador: {spool.armador}")
   print(f"Ocupado_Por: {spool.ocupado_por}")
   print(f"Fecha_Armado: {spool.fecha_armado}")
   ```

2. **Revisar logs de Railway para TEST-02:**
   ```bash
   railway logs --filter "TEST-02" --tail 100
   ```

   Buscar:
   - ✅ TOMAR exitoso con TEST-02
   - ⚠️ Warnings "INCONSISTENT STATE DETECTED"
   - ❌ Errores en callbacks de state machine

3. **Verificar deployment status:**
   ```bash
   # ¿Qué commit está en producción?
   curl https://zeues-backend-mvp-production.up.railway.app/api/health

   # Debería incluir version/commit info
   ```

4. **Test end-to-end con curl:**
   ```bash
   # 1. TOMAR
   curl -X POST https://zeues-backend.../api/occupation/tomar \
     -H "Content-Type: application/json" \
     -d '{"tag_spool":"TEST-02","worker_id":93,"worker_nombre":"MR(93)","operacion":"ARM"}'

   # 2. Verificar estado
   curl https://zeues-backend.../api/occupation/diagnostic/TEST-02

   # 3. PAUSAR
   curl -X POST https://zeues-backend.../api/occupation/pausar \
     -H "Content-Type: application/json" \
     -d '{"tag_spool":"TEST-02","worker_id":93,"worker_nombre":"MR(93)","operacion":"ARM"}'
   ```

### Fixes Potenciales (Después de confirmar root cause)

#### Si el problema es validación demasiado estricta:

**Actual:** Solo permite PAUSAR desde `EN_PROGRESO`

**Propuesto:** Permitir PAUSAR desde múltiples estados (idempotente/recovery)

```python
# backend/services/state_service.py línea 296-303
if current_arm_state not in ["en_progreso", "pausado"]:
    raise InvalidStateTransitionError(
        f"Cannot PAUSAR ARM from state '{current_arm_state}'. "
        f"PAUSAR is only allowed from 'en_progreso' or 'pausado' state.",
        tag_spool=tag_spool,
        current_state=current_arm_state,
        attempted_transition="pausar"
    )

# Si ya está pausado, es idempotente (no-op)
if current_arm_state == "pausado":
    logger.info(f"ARM already in pausado state for {tag_spool}, operation is idempotent")
    # Continue to clear occupation anyway (recovery)
```

**Justificación:**
- `PAUSADO` → `PAUSADO`: Idempotente, usuario intenta pausar algo ya pausado
- `EN_PROGRESO` → `PAUSADO`: Transición normal
- `PENDIENTE` → Error: Spool no ocupado, PAUSAR no tiene sentido
- `COMPLETADO` → Error: No puedes pausar trabajo completado

#### Si el problema es Redis lock TTL:

**Actual:** Lock expira después de 1 hora, limpia `Ocupado_Por`

**Propuesto:** Extender TTL o permitir recovery

```python
# Option A: Extend TTL to 4 hours
OCCUPATION_LOCK_TTL = 14400  # 4 hours

# Option B: Allow PAUSAR to work on expired locks (recovery mode)
if lock_expired and spool.armador:
    logger.warning(f"Lock expired for {tag_spool} but allowing PAUSAR for recovery")
    # Treat as valid PAUSAR (clear occupation)
```

---

## Archivos de Referencia

### Debug Documents
- `.planning/debug/pausar-fix-validation-failed.md` (actual, en progreso)
- `.planning/debug/resolved/pausar-error-400-invalid-state.md` (commit ac64c55)
- `.planning/debug/resolved/pausar-error-400-correct-flow.md` (commit 8143499)
- `.planning/debug/error-422-pausar-test-02.md` (commit 9eb246c - Error 422, distinto)

### Commits Relacionados
```bash
9e747d6 - fix: resolve PAUSAR hydration state reset bug
ac64c55 - fix: handle inconsistent state in PAUSAR when TOMAR partially fails
8143499 - fix: resolve PAUSAR Error 400 with cache invalidation
9eb246c - fix(frontend): add operacion field to PausarRequest to resolve Error 422
6748fd1 - fix: add operacion field to PausarRequest model
```

### Código Relevante
- `backend/services/state_service.py` líneas 259-343 (pausar method)
- `backend/services/state_service.py` líneas 436-494 (_hydrate_arm_machine)
- `backend/repositories/sheets_repository.py` líneas 418-422 (cache invalidation)
- `zeues-frontend/app/confirmar/page.tsx` líneas 289-296 (pausar call)

---

**Fin del Análisis Histórico**
