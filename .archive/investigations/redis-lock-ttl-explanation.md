# Explicación: Redis Lock TTL y Limpieza de Ocupado_Por

**Pregunta:** ¿Qué significa "Lock Redis expiró (TTL 1h) y sistema limpió Ocupado_Por"?

---

## Conceptos Básicos

### ¿Qué es un Lock de Redis?

Un **lock** (candado) de Redis es un mecanismo de sincronización distribuida que previene que múltiples trabajadores ocupen el mismo spool simultáneamente.

**Analogía:** Es como poner un candado físico en una herramienta en el taller. Solo quien tiene la llave puede usarla.

### ¿Qué es TTL (Time To Live)?

**TTL = Time To Live** (Tiempo de Vida)

Es el tiempo máximo que un lock puede existir antes de **expirar automáticamente**.

**En ZEUES v3.0:**
- TTL = **3600 segundos = 1 hora**
- Configurado en: `backend/config.py` línea 44

```python
REDIS_LOCK_TTL_SECONDS: int = int(os.getenv('REDIS_LOCK_TTL_SECONDS', '3600'))
```

---

## Flujo Normal: TOMAR → PAUSAR

### 1. TOMAR (Adquirir Lock)

Cuando un trabajador hace TOMAR en un spool:

```python
# backend/services/occupation_service.py líneas 140-173

# Step 2: Acquire Redis lock
lock_token = await redis_lock_service.acquire_lock(
    tag_spool="TEST-02",
    worker_id=93,
    worker_nombre="MR(93)"
)

# Step 3: Update Google Sheets
updates = {
    "Ocupado_Por": "MR(93)",         # ← Escribe en columna 64
    "Fecha_Ocupacion": "30-01-2026 14:30:00"  # ← Escribe en columna 65
}
await conflict_service.update_with_retry(tag_spool, updates)
```

**Estado resultante:**

| Sistema | Estado |
|---------|--------|
| **Redis** | Lock key `spool:TEST-02:lock` = `93:uuid-token` (TTL: 3600s) |
| **Google Sheets** | `Ocupado_Por` = "MR(93)" |
| **Google Sheets** | `Fecha_Ocupacion` = "30-01-2026 14:30:00" |

**El lock en Redis tiene un cronómetro interno que cuenta hacia atrás desde 3600 segundos.**

### 2. PAUSAR (Liberar Lock)

Cuando el trabajador hace PAUSAR:

```python
# backend/services/occupation_service.py líneas 319-362

# Step 3: Clear occupation in Sheets
updates = {
    "Ocupado_Por": "",               # ← Limpia columna 64
    "Fecha_Ocupacion": ""            # ← Limpia columna 65
}
await conflict_service.update_with_retry(tag_spool, updates)

# Step 4: Release Redis lock
await redis_lock_service.release_lock(tag_spool, worker_id, lock_token)
```

**Estado resultante:**

| Sistema | Estado |
|---------|--------|
| **Redis** | Lock key `spool:TEST-02:lock` ELIMINADO ✅ |
| **Google Sheets** | `Ocupado_Por` = "" (vacío) |
| **Google Sheets** | `Fecha_Ocupacion` = "" (vacío) |

---

## Problema: Lock Expira Automáticamente

### ¿Qué pasa si el trabajador NO hace PAUSAR?

**Escenario:** Trabajador hace TOMAR pero:
- Se va a almorzar
- Olvida hacer PAUSAR
- Cierra la aplicación sin completar
- Pierde conexión de red

**Después de 1 hora (3600 segundos):**

### Redis Auto-Expira el Lock

```
Tiempo:  0s          1800s         3600s
         |-------------|-------------|
         TOMAR         30 min        EXPIRE
         ↓                           ↓
Redis:   [LOCK SET]                  [LOCK AUTO-DELETED] ❌
```

**Redis ejecuta automáticamente:**
```bash
# Comando interno de Redis
DEL spool:TEST-02:lock
```

**Esto es AUTOMÁTICO.** Redis no necesita que nadie le diga que elimine el lock. Lo hace solo cuando el TTL llega a 0.

**Estado después de expiración:**

| Sistema | Estado |
|---------|--------|
| **Redis** | Lock key `spool:TEST-02:lock` **NO EXISTE** ❌ |
| **Google Sheets** | `Ocupado_Por` = **"MR(93)"** ⚠️ ← TODAVÍA EXISTE |
| **Google Sheets** | `Fecha_Ocupacion` = "30-01-2026 14:30:00" ⚠️ |

### 🚨 **PROBLEMA: Estado Inconsistente**

- **Redis dice:** Spool no está ocupado (lock no existe)
- **Google Sheets dice:** Spool ocupado por MR(93)

**Esto crea una inconsistencia crítica.**

---

## Hipótesis: ¿Sistema Limpia Ocupado_Por Automáticamente?

En mi análisis histórico mencioné:

> "Lock Redis expiró (TTL 1h) y **sistema limpió Ocupado_Por**"

Pero **DESPUÉS DE REVISAR EL CÓDIGO**, debo corregir esta hipótesis:

### ❌ NO existe cleanup automático de Ocupado_Por

**Evidencia:**

1. **No hay cron job o proceso programado** que limpie locks expirados
2. **No hay listener de Redis** que detecte expiración y limpie Sheets
3. **Redis no puede escribir a Google Sheets** - son sistemas independientes

```bash
# Búsqueda en todo el código
$ grep -r "cleanup\|expire.*ocupado" backend/
# RESULTADO: Sin coincidencias
```

### ✅ Corrección: Lock expira pero Ocupado_Por PERSISTE

**Lo que realmente sucede:**

1. **Lock expira** (automático por Redis)
2. **`Ocupado_Por` NO se limpia** (queda con valor "MR(93)")
3. **Spool queda en estado inconsistente** indefinidamente

**Tabla de estados:**

| Tiempo | Redis Lock | Ocupado_Por (Sheets) | Estado |
|--------|-----------|----------------------|--------|
| 0s (TOMAR) | ✅ Existe | "MR(93)" | ✅ Consistente |
| 1800s (30 min) | ✅ Existe | "MR(93)" | ✅ Consistente |
| 3600s (1 hora) | ❌ Expiró | "MR(93)" | ❌ **INCONSISTENTE** |
| 7200s (2 horas) | ❌ No existe | "MR(93)" | ❌ **INCONSISTENTE** |

**El spool queda "atorado" con `Ocupado_Por = "MR(93)"` pero sin lock válido.**

---

## Impacto en PAUSAR

### ¿Qué pasa si PAUSAR es llamado después de que el lock expiró?

```python
# backend/services/occupation_service.py línea 293-296

# Step 1: Verify lock ownership
lock_owner = await redis_lock_service.get_lock_owner(tag_spool)

if lock_owner is None:
    raise LockExpiredError(tag_spool)  # ← ERROR 410
```

**PAUSAR falla con Error 410 (Gone):**
```json
{
  "detail": "El lock para el spool 'TEST-02' ha expirado. El spool ya no está bajo tu ocupación."
}
```

### Pero eso NO explica el Error 400 actual

**El error actual es:**
```
Error 400: "Cannot PAUSAR ARM from state 'pendiente'"
```

**Esto es diferente.** Significa que:
- El código SÍ está verificando lock (línea 293-296)
- El código SÍ pasa la verificación de lock
- Pero LUEGO falla en validación de estado (línea 296 de `state_service.py`)

**Conclusión:**

Si fuera un problema de lock expirado:
- ❌ Veríamos **Error 410** (LockExpiredError)
- ❌ NO veríamos Error 400 (InvalidStateTransitionError)

**Por lo tanto, la hipótesis de "lock expirado" NO explica el error actual.**

---

## Escenarios de Estado Inconsistente

### Escenario A: Lock Expiró → Limpieza Manual

```
1. Usuario hace TOMAR                    Redis: ✅ Lock    Sheets: Ocupado_Por="MR(93)"
2. Espera 2 horas sin hacer PAUSAR       Redis: ❌ Expiró  Sheets: Ocupado_Por="MR(93)"
3. Admin detecta inconsistencia
4. Admin limpia manualmente Sheets       Redis: ❌         Sheets: Ocupado_Por=""
5. Usuario intenta PAUSAR                Redis: ❌ (Error 410)
```

**Resultado:** Error 410, no Error 400.

### Escenario B: Lock Expiró → Sistema NO Limpia → Usuario PAUSAR

```
1. Usuario hace TOMAR                    Redis: ✅ Lock    Sheets: Ocupado_Por="MR(93)"
2. Espera 2 horas                        Redis: ❌ Expiró  Sheets: Ocupado_Por="MR(93)"
3. Usuario intenta PAUSAR
```

**Resultado:** Error 410 (lock_owner is None), no Error 400.

### Escenario C: TOMAR Falló Parcialmente (Explicado en commit ac64c55)

```
1. TOMAR inicia
2. Redis lock adquirido                  Redis: ✅ Lock
3. Sheets update Ocupado_Por exitoso     Sheets: Ocupado_Por="MR(93)"
4. State machine callback falla          Sheets: Armador=None ❌ (debería ser "MR(93)")
5. Rollback falla parcialmente           Redis: ❌ Liberado  Sheets: Ocupado_Por="" ✅
6. Usuario reintenta TOMAR
7. Usuario hace PAUSAR
```

**Estado en PAUSAR:**
- `Ocupado_Por` = "" (limpiado por rollback)
- `Armador` = None
- Hydration → PENDIENTE
- Validación falla → **Error 400** ✅

**Este SÍ explica el Error 400.**

---

## Conclusión

### Hipótesis Original (INCORRECTA)

> "Lock Redis expiró (TTL 1h) y sistema limpió Ocupado_Por"

**Problemas:**
1. ❌ Sistema NO limpia `Ocupado_Por` automáticamente cuando lock expira
2. ❌ Si lock expira, PAUSAR falla con Error 410, no Error 400
3. ❌ No explica el error actual

### Hipótesis Corregida (MÁS PROBABLE)

> "TOMAR falló parcialmente: escribió `Ocupado_Por` pero no escribió `Armador`. Rollback limpió `Ocupado_Por` pero spool quedó con `Armador=None`. Cuando PAUSAR hydrata state, ve `Armador=None` y `Ocupado_Por=""` → hydrates to PENDIENTE → Error 400."

**Evidencia:**
1. ✅ Fix en commit ac64c55 intentó resolver este exact scenario
2. ✅ Debug doc muestra warning "INCONSISTENT STATE DETECTED"
3. ✅ Error 400 mensaje coincide: "state 'pendiente'"

### Redis Lock TTL NO es la causa raíz

**El TTL de 1 hora es correcto y funciona como esperado:**
- Lock expira automáticamente para prevenir "deadlocks" infinitos
- Si trabajador no completa en 1 hora, lock se libera
- Esto es **seguridad por diseño**, no un bug

**El problema real es la inconsistencia entre:**
- Estado en Redis (lock)
- Estado en Google Sheets (`Ocupado_Por`)
- Estado en Google Sheets (`Armador`)
- Estado de state machine (hydrated state)

---

## Verificación Necesaria

Para confirmar qué escenario es el real:

### 1. Verificar estado actual de TEST-02

```python
spool = sheets_repo.get_spool_by_tag("TEST-02")
print(f"Armador: {spool.armador}")
print(f"Ocupado_Por: {spool.ocupado_por}")
print(f"Fecha_Armado: {spool.fecha_armado}")
```

**Esperado si lock expiró:**
- `Ocupado_Por` = "MR(93)" (no limpiado)
- `Armador` = "MR(93)" (del TOMAR anterior)

**Esperado si TOMAR falló parcialmente:**
- `Ocupado_Por` = "" (limpiado por rollback)
- `Armador` = None (nunca fue escrito)

### 2. Verificar lock en Redis

```bash
redis-cli GET "spool:TEST-02:lock"
```

**Esperado si lock expiró:**
- Resultado: `(nil)` (lock no existe)

**Esperado si lock válido:**
- Resultado: `93:uuid-token`

### 3. Revisar logs de Railway

```bash
railway logs --filter "TEST-02" --tail 50
```

Buscar:
- ✅ "TOMAR operation started: TEST-02"
- ✅ "Lock acquired: TEST-02"
- ✅ "Sheets updated: TEST-02 occupied"
- ❌ "State machine transition failed" (indicaría TOMAR fallido)
- ⚠️ "INCONSISTENT STATE DETECTED" (confirmaría edge case fix ejecutando)

---

**Resumen:**
- Lock TTL de 1 hora es funcionalidad normal, no bug
- Redis NO limpia `Ocupado_Por` automáticamente cuando lock expira
- El Error 400 actual probablemente NO es causado por lock expirado
- Causa más probable: TOMAR falló parcialmente dejando spool en estado inconsistente
