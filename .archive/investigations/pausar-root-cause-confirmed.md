# ROOT CAUSE CONFIRMADO: Error 400 PAUSAR

**Fecha:** 2026-01-30
**Investigación:** Verificación directa del estado de TEST-02
**Método:** Lectura directa de Google Sheets + análisis de hydration logic

---

## 🎯 HIPÓTESIS CONFIRMADA

El Error 400 `"Cannot PAUSAR ARM from state 'pendiente'"` es causado porque:

**El spool TEST-02 está completamente VACÍO en Google Sheets.**

---

## 📊 Datos Reales (Verificados directamente)

### Estado Actual en Google Sheets

```
TAG_SPOOL:        TEST-02
Armador:          None
Soldador:         None
Ocupado_Por:      None
Fecha_Ocupacion:  None
Fecha_Armado:     None
Fecha_Soldadura:  None
Estado_Detalle:   None
version:          0
```

**TODOS los campos están vacíos o en None.**

### Estado Hydrated de State Machine

Según lógica de hydration en `backend/services/state_service.py` líneas 460-492:

```python
if spool.fecha_armado:
    # → No (None)
elif spool.armador:
    # → No (None)
elif spool.ocupado_por and spool.ocupado_por != "":
    # → No (None)
else:
    # → SÍ - Falls through to PENDIENTE
    estado = "PENDIENTE"
```

**Resultado:** Estado hydrated = **PENDIENTE**

### Validación de PAUSAR

```python
# backend/services/state_service.py línea 296
if current_arm_state != "en_progreso":
    raise InvalidStateTransitionError(
        f"Cannot PAUSAR ARM from state '{current_arm_state}'."
        # → "Cannot PAUSAR ARM from state 'pendiente'"
    )
```

**Resultado:** ❌ Error 400

---

## ✅ Confirmación de Causa Raíz

### Hipótesis RECHAZADAS

1. ❌ **Lock Redis expiró y sistema limpió Ocupado_Por**
   - Datos muestran: `Ocupado_Por = None`
   - Pero si lock expiró, `Ocupado_Por` habría permanecido con valor
   - NO hay proceso que limpie automáticamente

2. ❌ **TOMAR falló parcialmente (edge case ac64c55)**
   - Datos muestran: `Ocupado_Por = None` Y `Armador = None`
   - Edge case es: `Ocupado_Por` tiene valor pero `Armador = None`
   - NO aplica aquí

3. ❌ **activate_initial_state() reseteando estado (fix 9e747d6)**
   - Datos muestran: Spool completamente vacío
   - No hay estado hydratado que resetear
   - NO aplica aquí

### Hipótesis CONFIRMADA ✅

**El spool TEST-02 NUNCA fue tomado exitosamente** O **fue completamente limpiado**.

**Evidencia:**
- ✅ Todos los campos vacíos (None)
- ✅ version = 0 (estado inicial o reseteado)
- ✅ No hay rastro de ocupación previa

---

## 🔍 ¿Por qué los 3 Fixes Anteriores No Resolvieron?

### Fix #1: Cache Invalidation (commit 8143499)

**Objetivo:** Invalidar cache después de writes para evitar lecturas stale

**Por qué no resolvió:**
- El problema NO era cache stale
- El spool realmente ESTÁ vacío en Google Sheets
- Cache estaría mostrando datos correctos (vacío)

### Fix #2: Edge Case Handling (commit ac64c55)

**Objetivo:** Hydrate a EN_PROGRESO cuando `Ocupado_Por` existe pero `Armador` no

**Por qué no resolvió:**
- Edge case: `Ocupado_Por = "MR(93)"` + `Armador = None`
- Realidad: `Ocupado_Por = None` + `Armador = None`
- **El fix es correcto pero NO aplica a este caso**

### Fix #3: activate_initial_state() Ordering (commit 9e747d6)

**Objetivo:** Evitar que `activate_initial_state()` resetee estado hydratado

**Por qué no resolvió:**
- El estado hydratado ES PENDIENTE (correcto basado en datos)
- No hay estado para "resetear"
- **El fix es correcto pero NO aplica a este caso**

---

## 💡 Entonces, ¿Cuál es el Problema Real?

### Escenarios Posibles

#### Escenario A: Usuario Intentó PAUSAR sin hacer TOMAR

**Flujo del usuario:**
1. Usuario abre app
2. Ve TEST-02 en lista de spools
3. Selecciona "PAUSAR"
4. Selecciona TEST-02
5. Hace clic en "CONFIRMAR"
6. Error 400

**Problema:** El usuario no hizo TOMAR primero. El spool está disponible (PENDIENTE), no ocupado.

**Evidencia a favor:**
- ✅ Spool completamente vacío
- ✅ Estado PENDIENTE es correcto para spool disponible

**Pregunta clave:** ¿Cómo llegó TEST-02 a la lista de spools en la página de PAUSAR si no está ocupado?

#### Escenario B: TOMAR Falló Silenciosamente + Frontend Mostró Éxito

**Flujo:**
1. Usuario hace TOMAR en TEST-02
2. Backend rechaza con error (spool no disponible, dependencias, etc.)
3. Frontend NO muestra error correctamente
4. Usuario procede a PAUSAR pensando que TOMAR funcionó
5. Error 400

**Evidencia a favor:**
- ✅ Explicaría por qué usuario intenta PAUSAR spool no ocupado
- ✅ Frontend podría tener bug en manejo de errores

**Evidencia en contra:**
- ❌ Frontend debería mostrar mensaje de error
- ❌ Usuario no debería ver TEST-02 en lista de ocupados

#### Escenario C: TOMAR + COMPLETAR Ya Ejecutaron (Spool Disponible de Nuevo)

**Flujo:**
1. Usuario hizo TOMAR en TEST-02 (ayer)
2. Usuario completó el armado (COMPLETAR)
3. Sistema limpió todos los datos (spool disponible)
4. Hoy usuario vuelve e intenta PAUSAR el mismo spool
5. Error 400

**Evidencia a favor:**
- ✅ Spool limpio indica operación completada
- ✅ version = 0 podría ser reset después de COMPLETAR

**Evidencia en contra:**
- ❌ Después de COMPLETAR, `Fecha_Armado` debería existir (no None)
- ❌ Logs mostrarían COMPLETAR reciente

#### Escenario D: Context State Desincronizado (Frontend)

**Flujo:**
1. Usuario hace TOMAR en TEST-02
2. TOMAR exitoso, spool ocupado
3. Usuario navega entre páginas, context state se corrompe
4. Context muestra `operacion: ARM`, `tag_spool: TEST-02` pero datos son stale
5. Usuario hace clic en PAUSAR
6. Frontend envía request con TEST-02 pero TEST-02 YA NO está ocupado
7. Error 400

**Evidencia a favor:**
- ✅ Frontend usa React Context para state
- ✅ Context puede tener datos stale si no se actualiza

**Evidencia en contra:**
- ❌ Frontend debería validar estado antes de enviar PAUSAR

---

## 🧪 Verificaciones Adicionales Necesarias

### 1. Revisar Logs de Railway (Backend)

```bash
railway logs --filter "TEST-02" --tail 100
```

**Buscar:**
- ❌ Intentos fallidos de TOMAR con TEST-02
- ✅ TOMAR exitoso reciente
- ✅ COMPLETAR que limpió el spool
- ❌ Excepciones/errores durante operaciones

### 2. Revisar Console del Browser (Frontend)

**Buscar:**
- Estado de Context antes de PAUSAR
- Request payload enviado a `/api/occupation/pausar`
- Response del backend
- Errores de validación frontend

### 3. Verificar Flujo de Usuario Real

**Preguntas:**
- ¿Usuario hizo TOMAR antes de PAUSAR?
- ¿Cuánto tiempo pasó entre TOMAR y PAUSAR?
- ¿Usuario navegó entre páginas?
- ¿Vio TEST-02 en lista de "Spools Ocupados" o "Spools Disponibles"?

### 4. Verificar Lista de Spools en Frontend

**Código a revisar:**
- `zeues-frontend/app/seleccionar-spool/page.tsx`
- Filtro para mostrar spools ocupados en PAUSAR
- ¿Cómo se determina qué spools mostrar?

```typescript
// ¿Hay lógica como esta?
if (tipo === 'pausar') {
    spools = spools.filter(s => s.ocupado_por === context.workerNombre)
}
```

---

## 🎯 Conclusión

### Causa Raíz REAL

**El spool TEST-02 está en estado PENDIENTE (completamente vacío).**

Esto significa que:
1. ✅ El backend está funcionando CORRECTAMENTE
2. ✅ La validación es CORRECTA (no se puede pausar lo que no está ocupado)
3. ❌ El problema está en el **FLUJO DEL USUARIO** o **FRONTEND**

### Los 3 Fixes Anteriores

**TODOS los fixes implementados son correctos** pero no aplican a este caso porque:
- No hay cache stale (spool realmente está vacío)
- No hay edge case (ambos campos vacíos)
- No hay estado para resetear (estado PENDIENTE es correcto)

**Los fixes son buenos para edge cases futuros** pero no resuelven el problema actual.

### Problema Real NO es Backend Hydration

El problema real es:

**¿Por qué el usuario está intentando PAUSAR un spool que no está ocupado?**

Posibles causas:
1. Frontend muestra TEST-02 en lista de PAUSAR cuando no debería
2. Context state tiene datos stale/incorrectos
3. Usuario confundido sobre el flujo (intenta PAUSAR sin TOMAR primero)
4. Bug en filtrado de spools ocupados vs disponibles

---

## 🔧 Acciones Recomendadas

### Acción 1: Verificar Frontend Filtering

**Revisar:**
```typescript
// zeues-frontend/app/seleccionar-spool/page.tsx
// ¿Cómo filtra spools para PAUSAR?
```

**Esperado:**
- PAUSAR solo debe mostrar spools donde `ocupado_por === current_worker`
- No debe mostrar spools en PENDIENTE

### Acción 2: Añadir Validación Frontend

**Antes de navegar a confirmar PAUSAR:**
```typescript
if (!spool.ocupado_por || spool.ocupado_por !== context.workerNombre) {
    alert("Este spool no está ocupado por ti. No puedes pausarlo.");
    return;
}
```

### Acción 3: Mejorar Mensaje de Error 400

**Backend actual:**
```
"Cannot PAUSAR ARM from state 'pendiente'"
```

**Mejor mensaje:**
```
"Cannot PAUSAR ARM: el spool TEST-02 no está ocupado.
Debes hacer TOMAR primero antes de PAUSAR."
```

### Acción 4: Logs de Usuario

**Añadir logging frontend:**
```typescript
console.log("PAUSAR attempt:", {
    tag_spool: selectedSpool.tag_spool,
    ocupado_por: selectedSpool.ocupado_por,
    worker: context.workerNombre,
    context_state: context
});
```

---

## 📁 Archivos de Evidencia

- **Script de verificación:** `./scripts/simple_test02_check.py`
- **Output del script:** Guardado en esta investigación (arriba)
- **Datos confirmados:** Google Sheets TEST-02 completamente vacío

---

**FIN DE INVESTIGACIÓN**

**Resultado:** ✅ Causa raíz confirmada - Spool en estado PENDIENTE (vacío)
**Problema:** Frontend/UX, no backend hydration
**Fixes anteriores:** Correctos pero no aplican a este caso
