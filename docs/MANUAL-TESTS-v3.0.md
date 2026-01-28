# Manual Test Suite - ZEUES v3.0

**Version:** v3.0 Real-Time Location Tracking
**Created:** 2026-01-28
**Purpose:** Manual testing guide for validating v3.0 features in production/staging

---

## 📋 Pre-requisitos

### Ambiente de Prueba

- [ ] **Frontend:** https://zeues-frontend.vercel.app (producción)
- [ ] **Backend API:** https://zeues-backend-mvp-production.up.railway.app
- [ ] **Google Sheet ID:** `17iOaq2sv4mSOuJY4B8dGQIsWTTUKPspCtb7gk6u-MaQ`
- [ ] **Redis:** Activo en Railway (verificar salud con `/api/redis-health`)

### Herramientas Necesarias

- [ ] 2 navegadores diferentes (para simular 2 workers)
- [ ] Modo responsive/tablet en DevTools (simulación de tablet 768x1024)
- [ ] Acceso a Google Sheets (para verificar escrituras)
- [ ] Opcional: Postman/cURL para tests de API directos

### Verificación Inicial

```bash
# 1. Health check backend
curl https://zeues-backend-mvp-production.up.railway.app/api/health
# Esperado: {"status":"healthy"}

# 2. Redis health check
curl https://zeues-backend-mvp-production.up.railway.app/api/redis-health
# Esperado: {"redis":"connected"}

# 3. Verificar columnas v3.0 en Google Sheets
# Abrir: https://docs.google.com/spreadsheets/d/17iOaq2sv4mSOuJY4B8dGQIsWTTUKPspCtb7gk6u-MaQ
# Hoja "Operaciones" debe tener columnas 64-67:
# - Ocupado_Por (col 64)
# - Fecha_Ocupacion (col 65)
# - version (col 66)
# - Estado_Detalle (col 67)
```

---

## 🧪 Test Suite

---

## PHASE 2: Core Location Tracking (LOC-01 a LOC-04)

### Test 2.1: TOMAR Spool Básico (LOC-01)

**Objetivo:** Verificar que un worker puede tomar un spool disponible y el sistema marca ocupación.

**Pasos:**

1. Abrir frontend en Browser 1
2. Seleccionar Worker: **Mauricio Rodriguez (MR(93))**
3. Seleccionar Operación: **ARM (Armado)**
4. Seleccionar Acción: **TOMAR**
5. Seleccionar un spool disponible (ej: primer spool de la lista)
6. Confirmar

**Verificaciones:**

- [ ] Navegación exitosa a pantalla de éxito
- [ ] Mensaje: "Operación completada exitosamente"
- [ ] Abrir Google Sheets → Hoja "Operaciones"
- [ ] Columna "Ocupado_Por" (64) del spool = `MR(93)`
- [ ] Columna "Fecha_Ocupacion" (65) tiene fecha/hora actual
- [ ] Columna "Estado_Detalle" (67) = `"MR(93) trabajando ARM (ARM en progreso, SOLD pendiente)"`
- [ ] Abrir hoja "Metadata" → Última fila tiene evento `TOMAR_ARM`

**Resultado Esperado:** ✅ Spool marcado como OCUPADO por MR(93)

---

### Test 2.2: Race Condition - Doble TOMAR (LOC-04)

**Objetivo:** Verificar que 2 workers NO pueden tomar el mismo spool simultáneamente.

**Pasos:**

1. **Browser 1:**
   - Worker: Mauricio Rodriguez
   - Operación: ARM
   - Acción: TOMAR
   - **NO confirmar todavía** (dejar en pantalla de confirmación)

2. **Browser 2 (incognito/otro navegador):**
   - Worker: Juan Pérez (diferente worker)
   - Operación: ARM
   - Acción: TOMAR
   - Seleccionar **EL MISMO SPOOL** que Browser 1
   - Confirmar

3. **Browser 1:**
   - Ahora sí, confirmar

**Verificaciones:**

- [ ] Uno de los dos recibe error 409: "El spool ya está ocupado por otro trabajador"
- [ ] El otro worker tiene éxito
- [ ] Google Sheets muestra solo UNA ocupación (el que ganó la carrera)
- [ ] Metadata tiene solo UN evento TOMAR

**Resultado Esperado:** ✅ Redis lock previene doble ocupación (1 éxito, 1 conflict)

---

### Test 2.3: PAUSAR Spool (LOC-02)

**Objetivo:** Verificar que un worker puede pausar trabajo y el spool queda disponible.

**Prerequisito:** Tener un spool OCUPADO por Worker A (usar Test 2.1)

**Pasos:**

1. **Browser 1 (mismo worker que hizo TOMAR):**
   - Volver a página inicial
   - Seleccionar mismo Worker: Mauricio Rodriguez
   - Operación: ARM
   - Acción: **PAUSAR**
   - Seleccionar el spool que habías tomado antes
   - Confirmar

**Verificaciones:**

- [ ] Navegación exitosa a pantalla de éxito
- [ ] Google Sheets → Columna "Ocupado_Por" (64) = `NULL` (vacío)
- [ ] Columna "Fecha_Ocupacion" (65) = `NULL` (vacío)
- [ ] Columna "Estado_Detalle" (67) = `"Disponible - ARM en progreso, SOLD pendiente"`
- [ ] Columna "Armador" (AL) **sigue teniendo** `MR(93)` (preserva progreso)
- [ ] Metadata tiene evento `PAUSAR_ARM`

**Resultado Esperado:** ✅ Spool liberado pero progreso ARM preservado

---

### Test 2.4: COMPLETAR Spool (LOC-03)

**Objetivo:** Verificar que un worker puede completar operación y el spool queda disponible.

**Prerequisito:** Tener un spool OCUPADO por Worker A

**Pasos:**

1. Si no tienes spool ocupado, hacer Test 2.1 primero
2. **Browser 1 (mismo worker):**
   - Worker: Mauricio Rodriguez
   - Operación: ARM
   - Acción: **COMPLETAR**
   - Seleccionar el spool ocupado
   - Confirmar

**Verificaciones:**

- [ ] Navegación exitosa a pantalla de éxito
- [ ] Google Sheets → Columna "Ocupado_Por" (64) = `NULL`
- [ ] Columna "Fecha_Ocupacion" (65) = `NULL`
- [ ] Columna "Fecha_Armado" (AK) tiene fecha actual (DD-MM-YYYY)
- [ ] Columna "Estado_Detalle" (67) = `"Disponible - ARM completo, SOLD pendiente"`
- [ ] Metadata tiene evento `COMPLETAR_ARM`

**Resultado Esperado:** ✅ Operación completada, spool disponible, fecha registrada

---

## PHASE 3: State Machine & Collaboration (COLLAB-01 a COLLAB-04)

### Test 3.1: Worker Handoff - Continuación por otro Worker (COLLAB-01)

**Objetivo:** Verificar que Worker B puede continuar trabajo iniciado por Worker A.

**Pasos:**

1. **Browser 1 - Worker A:**
   - Worker: Mauricio Rodriguez
   - Operación: ARM
   - TOMAR spool S1
   - PAUSAR spool S1 (liberar sin completar)

2. **Browser 2 - Worker B (diferente):**
   - Worker: Juan Pérez (JP)
   - Operación: ARM
   - TOMAR el mismo spool S1
   - COMPLETAR spool S1

**Verificaciones:**

- [ ] Worker B puede TOMAR el spool (no hay error de ownership)
- [ ] Worker B puede COMPLETAR exitosamente
- [ ] Google Sheets → Columna "Fecha_Armado" tiene fecha actual
- [ ] Metadata muestra 4 eventos: TOMAR(A), PAUSAR(A), TOMAR(B), COMPLETAR(B)

**Resultado Esperado:** ✅ Colaboración sin ownership estricto

---

### Test 3.2: Dependency Validation - SOLD requiere ARM (COLLAB-02)

**Objetivo:** Verificar que no se puede TOMAR SOLD si ARM no está iniciado.

**Pasos:**

1. Identificar un spool con "Fecha_Materiales" ≠ NULL y "Armador" = NULL (ARM no iniciado)
2. **Browser 1:**
   - Worker: Cualquiera con rol Soldador
   - Operación: **SOLD**
   - Acción: TOMAR
   - Seleccionar el spool identificado
   - Confirmar

**Verificaciones:**

- [ ] Error: "El spool no tiene ARM iniciado. Debe iniciar ARM antes de SOLD."
- [ ] HTTP 400 (Bad Request)
- [ ] Google Sheets NO cambia (spool sigue sin Soldador)

**Resultado Esperado:** ✅ SOLD bloqueado si ARM no iniciado

---

### Test 3.3: Combined Estado_Detalle (STATE-01, STATE-03)

**Objetivo:** Verificar que Estado_Detalle muestra estado combinado correctamente.

**Pasos:**

1. Crear escenario:
   - Spool con ARM en progreso (Armador ≠ NULL, Fecha_Armado = NULL)
   - SOLD pendiente (Soldador = NULL)
   - OCUPADO por Worker X

2. Verificar Google Sheets → Columna "Estado_Detalle" (67)

**Verificaciones Esperadas:**

| Escenario | Estado_Detalle Esperado |
|-----------|-------------------------|
| DISPONIBLE, ARM pendiente, SOLD pendiente | `"Disponible - ARM pendiente, SOLD pendiente"` |
| OCUPADO por MR(93), ARM en progreso | `"MR(93) trabajando ARM (ARM en progreso, SOLD pendiente)"` |
| DISPONIBLE, ARM completo, SOLD pendiente | `"Disponible - ARM completo, SOLD pendiente"` |
| OCUPADO por JP(94), SOLD en progreso | `"JP(94) trabajando SOLD (ARM completo, SOLD en progreso)"` |
| DISPONIBLE, ARM completo, SOLD completo | `"Disponible - ARM completo, SOLD completo"` |

**Resultado Esperado:** ✅ Estado_Detalle refleja ocupación + progreso combinado

---

### Test 3.4: Occupation History (COLLAB-04)

**Objetivo:** Verificar endpoint de historial de ocupación.

**Pasos:**

1. Usar spool con múltiples eventos (ej: del Test 3.1)
2. Obtener TAG_SPOOL del spool
3. Llamar API:
   ```bash
   curl https://zeues-backend-mvp-production.up.railway.app/api/history/{TAG_SPOOL}
   ```

**Verificaciones:**

- [ ] Respuesta HTTP 200
- [ ] JSON contiene array `sessions`
- [ ] Cada sesión tiene: `worker_id`, `worker_nombre`, `operacion`, `inicio`, `fin`, `duracion`
- [ ] Duración en formato legible: "2h 15m" o "45m 30s"
- [ ] Sesiones ordenadas cronológicamente

**Resultado Esperado:** ✅ Historial completo de quién tuvo el spool y por cuánto tiempo

---

## PHASE 4: Real-Time Visibility (LOC-05, LOC-06)

### Test 4.1: Dashboard SSE Connection

**Objetivo:** Verificar que dashboard establece conexión SSE.

**Pasos:**

1. Abrir en Browser 1: `https://zeues-frontend.vercel.app/dashboard`
2. Abrir DevTools → Network tab → Filtrar por "stream"
3. Buscar request a `/api/sse/stream`

**Verificaciones:**

- [ ] Request con status "pending" (conexión activa)
- [ ] Response headers: `Content-Type: text/event-stream`
- [ ] Indicador verde en esquina superior derecha: "Conectado"
- [ ] Console NO muestra errores de conexión

**Resultado Esperado:** ✅ Conexión SSE establecida

---

### Test 4.2: Real-Time TOMAR Update (LOC-05, LOC-06)

**Objetivo:** Verificar actualización en tiempo real cuando worker toma spool.

**Pasos:**

1. **Browser 1:** Abrir dashboard (`/dashboard`)
2. **Browser 2:** Ejecutar flujo TOMAR:
   - Worker: Mauricio Rodriguez
   - Operación: ARM
   - Acción: TOMAR
   - Seleccionar spool
   - Confirmar

3. **Browser 1 (Dashboard):** Observar actualización

**Verificaciones:**

- [ ] Dashboard muestra nuevo spool ocupado **en menos de 10 segundos**
- [ ] Muestra: TAG_SPOOL, worker_nombre, operacion, estado_detalle
- [ ] Contador "Spools Ocupados" incrementa en +1

**Resultado Esperado:** ✅ Dashboard actualizado en tiempo real (<10s)

---

### Test 4.3: Real-Time PAUSAR Update

**Objetivo:** Verificar que PAUSAR actualiza dashboard en tiempo real.

**Prerequisito:** Tener un spool ocupado (Test 4.2)

**Pasos:**

1. **Browser 1:** Dashboard abierto
2. **Browser 2:** PAUSAR el spool ocupado
3. **Browser 1:** Observar cambio

**Verificaciones:**

- [ ] Spool desaparece de la lista de ocupados **en menos de 10 segundos**
- [ ] Contador "Spools Ocupados" decrementa en -1

**Resultado Esperado:** ✅ Dashboard refleja liberación en tiempo real

---

### Test 4.4: SSE Reconnection (Mobile Lifecycle)

**Objetivo:** Verificar que SSE se reconecta automáticamente.

**Pasos:**

1. Abrir dashboard en Browser 1
2. Verificar indicador verde "Conectado"
3. Ir a DevTools → Network → Find `/api/sse/stream` → Click derecho → "Cancel request"
4. Esperar 5-10 segundos

**Verificaciones:**

- [ ] Indicador cambia temporalmente a rojo "Desconectado"
- [ ] Después de 1-30 segundos, vuelve a verde "Conectado"
- [ ] Nueva conexión SSE aparece en Network tab
- [ ] Dashboard sigue mostrando datos actualizados

**Resultado Esperado:** ✅ Auto-reconexión con exponential backoff

---

## PHASE 5: Metrología Workflow (METRO-01 a METRO-04)

### Test 5.1: Prerequisite Validation (METRO-04)

**Objetivo:** Verificar que metrología requiere ARM + SOLD completos.

**Pasos:**

1. Identificar spool con:
   - Fecha_Armado = NULL (ARM no completo) O
   - Fecha_Soldadura = NULL (SOLD no completo)

2. **Browser 1:**
   - Worker: Metrólogo
   - Operación: **METROLOGIA**
   - Intentar seleccionar ese spool

**Verificaciones:**

- [ ] Spool NO aparece en la lista de selección
- [ ] O si aparece, al intentar COMPLETAR → Error 400: "ARM o SOLD no completados"

**Resultado Esperado:** ✅ Metrología bloqueada sin prerequisitos

---

### Test 5.2: Instant Completion - APROBADO (METRO-01, METRO-02)

**Objetivo:** Verificar flujo metrología con resultado APROBADO (sin TOMAR).

**Prerequisito:** Spool con ARM + SOLD completos

**Pasos:**

1. **Browser 1:**
   - Worker: Metrólogo
   - Operación: **METROLOGIA**
   - Spool aparece en lista (con ARM+SOLD completos)
   - Click en spool
   - Aparece pantalla con 2 botones grandes: APROBADO / RECHAZADO
   - Click **APROBADO** ✓
   - Confirmar

**Verificaciones:**

- [ ] Navegación a pantalla de éxito (sin pasar por TOMAR)
- [ ] Google Sheets → Columna "Estado_Detalle" = `"METROLOGIA APROBADO ✓"`
- [ ] Columna "Ocupado_Por" sigue en NULL (NO se ocupó)
- [ ] Metadata tiene evento `COMPLETAR_METROLOGIA` con resultado `APROBADO`

**Resultado Esperado:** ✅ Inspección instantánea aprobada sin ocupación

---

### Test 5.3: Instant Completion - RECHAZADO (METRO-03)

**Objetivo:** Verificar flujo metrología con resultado RECHAZADO.

**Pasos:**

1. Repetir Test 5.2 pero seleccionar **RECHAZADO** ✗

**Verificaciones:**

- [ ] Navegación a pantalla de éxito
- [ ] Google Sheets → Columna "Estado_Detalle" = `"METROLOGIA RECHAZADO - Pendiente reparación"`
- [ ] Columna "Ocupado_Por" = NULL (no ocupado)
- [ ] Metadata tiene evento `COMPLETAR_METROLOGIA` con resultado `RECHAZADO`

**Resultado Esperado:** ✅ Inspección rechazada, spool entra a cola de reparación

---

### Test 5.4: Occupied Spool Blocked (METRO-04)

**Objetivo:** Verificar que no se puede inspeccionar spool ocupado.

**Pasos:**

1. Tener spool con ARM+SOLD completos pero OCUPADO (otro worker haciendo algo)
2. Intentar METROLOGIA sobre ese spool

**Verificaciones:**

- [ ] Error 409: "El spool está ocupado por otro trabajador"
- [ ] O spool no aparece en lista de selección

**Resultado Esperado:** ✅ Metrología bloqueada si spool ocupado

---

## PHASE 6: Reparación Loops (REPAR-01 a REPAR-04)

### Test 6.1: TOMAR Spool Rechazado (REPAR-01)

**Objetivo:** Verificar que worker puede tomar spool RECHAZADO para reparación.

**Prerequisito:** Spool en estado RECHAZADO (usar Test 5.3)

**Pasos:**

1. **Browser 1:**
   - Worker: Cualquiera (no hay restricción de rol)
   - Operación: **REPARACION** (botón amarillo con icono llave inglesa)
   - Acción: **TOMAR**
   - Seleccionar spool RECHAZADO
   - Confirmar

**Verificaciones:**

- [ ] Botón REPARACION visible en lista de operaciones (4to botón, amarillo)
- [ ] Spool RECHAZADO aparece en lista
- [ ] Navegación exitosa a éxito
- [ ] Google Sheets → Columna "Ocupado_Por" = worker_nombre
- [ ] Columna "Estado_Detalle" = `"Worker trabajando REPARACION (RECHAZADO - Ciclo 1/3)"`
- [ ] Metadata tiene evento `TOMAR_REPARACION`

**Resultado Esperado:** ✅ Spool RECHAZADO tomado para reparación

---

### Test 6.2: COMPLETAR Reparación - Return to Metrología (REPAR-03)

**Objetivo:** Verificar que completar reparación devuelve spool a cola de metrología.

**Prerequisito:** Spool ocupado en reparación (Test 6.1)

**Pasos:**

1. **Browser 1 (mismo worker):**
   - Operación: REPARACION
   - Acción: **COMPLETAR**
   - Seleccionar el spool en reparación
   - Confirmar

**Verificaciones:**

- [ ] Navegación a éxito
- [ ] Google Sheets → Columna "Ocupado_Por" = NULL
- [ ] Columna "Estado_Detalle" = `"PENDIENTE_METROLOGIA (Ciclo 1/3)"`
- [ ] Spool ahora aparece disponible para METROLOGIA
- [ ] Metadata tiene evento `COMPLETAR_REPARACION`

**Resultado Esperado:** ✅ Spool vuelve a metrología automáticamente

---

### Test 6.3: Cycle Counting (REPAR-04)

**Objetivo:** Verificar conteo de ciclos de reparación.

**Pasos:**

1. Tomar spool RECHAZADO (Test 6.1) → Ciclo 1/3
2. Completar reparación (Test 6.2)
3. Metrólogo → RECHAZAR nuevamente → Ciclo 2/3
4. Repetir: TOMAR reparación → COMPLETAR
5. Metrólogo → RECHAZAR por tercera vez → Ciclo 3/3
6. Repetir: TOMAR reparación → COMPLETAR
7. Metrólogo → RECHAZAR por cuarta vez

**Verificaciones Paso a Paso:**

Ciclo 1:
- [ ] Estado_Detalle = `"... (Ciclo 1/3)"`

Ciclo 2:
- [ ] Estado_Detalle = `"... (Ciclo 2/3)"`

Ciclo 3:
- [ ] Estado_Detalle = `"... (Ciclo 3/3)"`

Después de 3er rechazo:
- [ ] Estado_Detalle = `"BLOQUEADO - Requiere supervisor"`
- [ ] Spool NO aparece en lista de REPARACION (bloqueado)
- [ ] Spool muestra icono candado 🔒 y texto rojo "BLOQUEADO"
- [ ] Click en spool bloqueado → deshabilitado (cursor not-allowed)

**Resultado Esperado:** ✅ Después de 3 rechazos consecutivos, spool BLOQUEADO

---

### Test 6.4: Supervisor Override Detection (REPAR-04)

**Objetivo:** Verificar que sistema detecta cuando supervisor libera manualmente un BLOQUEADO.

**Prerequisito:** Spool BLOQUEADO (Test 6.3)

**Pasos:**

1. Abrir Google Sheets manualmente
2. Buscar spool BLOQUEADO
3. Cambiar columna "Estado_Detalle" de `"BLOQUEADO..."` a `"RECHAZADO - Ciclo 0/3"` (simular reset por supervisor)
4. Guardar cambios en Sheets
5. Esperar ~30 segundos (para que sistema detecte cambio)
6. Verificar hoja "Metadata"

**Verificaciones:**

- [ ] Metadata tiene nuevo evento `SUPERVISOR_OVERRIDE`
- [ ] Evento tiene `worker_id = 0` y `worker_nombre = "SYSTEM"`
- [ ] Spool ahora disponible para REPARACION (ciclo reseteado)

**Resultado Esperado:** ✅ Sistema detecta y registra override de supervisor

---

### Test 6.5: No Role Restriction (REPAR-02)

**Objetivo:** Verificar que cualquier worker puede hacer reparación.

**Pasos:**

1. Tener spool RECHAZADO
2. Probar TOMAR con diferentes roles:
   - Worker con rol Armador
   - Worker con rol Soldador
   - Worker con rol Ayudante
   - Worker SIN ningún rol específico

**Verificaciones:**

- [ ] TODOS pueden acceder a operación REPARACION
- [ ] TODOS pueden TOMAR spool RECHAZADO
- [ ] No hay error de "rol no autorizado"

**Resultado Esperado:** ✅ REPARACION sin restricción de rol

---

## 🔄 Backward Compatibility Tests (BC-01, BC-02)

### Test 7.1: v2.1 Data Preservation

**Objetivo:** Verificar que datos v2.1 siguen intactos.

**Pasos:**

1. Abrir Google Sheets
2. Verificar columnas v2.1 (1-63) **NO han cambiado**
3. Verificar datos históricos pre-migración intactos

**Verificaciones:**

- [ ] Columnas 1-63 (v2.1) sin modificaciones
- [ ] TAG_SPOOL, Fecha_Materiales, Armador, Soldador preservados
- [ ] NV, Proyecto, Cliente, etc. intactos
- [ ] Hoja "Trabajadores" sin cambios (4 columnas A-D)
- [ ] Hoja "Roles" sin cambios (3 columnas A-C)

**Resultado Esperado:** ✅ Datos v2.1 preservados

---

### Test 7.2: v2.1 Tests Archived

**Objetivo:** Verificar que tests v2.1 fueron archivados correctamente.

**Pasos:**

```bash
cd /Users/sescanella/Proyectos/KM/ZEUES-by-KM

# Verificar archivo
ls tests/v2.1-archive/

# Debe contener:
# - TEST_RESULTS.txt (233 tests pasando)
# - Carpetas: integration/, unit/, e2e/
```

**Verificaciones:**

- [ ] Directorio `tests/v2.1-archive/` existe
- [ ] TEST_RESULTS.txt muestra 233 tests passing
- [ ] Archivos Python (.py) preservados
- [ ] README.md explica que son tests históricos

**Resultado Esperado:** ✅ Tests v2.1 archivados como referencia

---

## 🐛 Edge Cases & Error Handling

### Test 8.1: Network Interruption (SSE Reconnection)

**Pasos:**

1. Dashboard abierto con SSE activo
2. DevTools → Network → Throttling → Offline (simular desconexión)
3. Esperar 5 segundos
4. Network → Online

**Verificaciones:**

- [ ] Indicador cambia a rojo "Desconectado"
- [ ] Al volver online, reconecta automáticamente (verde)
- [ ] No hay errores en console
- [ ] Dashboard sigue funcional

**Resultado Esperado:** ✅ Reconexión automática resiliente

---

### Test 8.2: Invalid Spool Selection

**Pasos:**

1. Intentar TOMAR un spool que NO cumple prerequisitos:
   - ARM sin Fecha_Materiales
   - SOLD sin ARM iniciado
   - METROLOGIA sin ARM+SOLD completos

**Verificaciones:**

- [ ] Spool no aparece en lista de selección O
- [ ] Error claro en español: "El spool no cumple los prerequisitos"
- [ ] HTTP 400 con mensaje descriptivo

**Resultado Esperado:** ✅ Validaciones frontend + backend consistentes

---

### Test 8.3: Concurrent Operations - Different Operations

**Objetivo:** Verificar que Worker A en ARM y Worker B en SOLD del MISMO spool funcionan.

**Pasos:**

1. Spool S1 con ARM completo, SOLD pendiente
2. **Browser 1:** Worker A → METROLOGIA → COMPLETAR S1
3. **Browser 2:** (simultáneamente) Worker B → REPARACION → TOMAR S1

**Verificaciones:**

- [ ] Solo UNA operación tiene éxito
- [ ] La otra recibe 409 conflict
- [ ] No hay doble escritura en Sheets

**Resultado Esperado:** ✅ Redis locks previenen conflictos cross-operation

---

## 📊 Performance Tests

### Test 9.1: Dashboard Load Time

**Objetivo:** Verificar que dashboard carga rápido.

**Pasos:**

1. Abrir DevTools → Network → Clear
2. Abrir `/dashboard`
3. Medir tiempo de carga completo

**Verificaciones:**

- [ ] First Contentful Paint (FCP) < 2 segundos
- [ ] Time to Interactive (TTI) < 3 segundos
- [ ] SSE connection establecida < 1 segundo después de TTI

**Resultado Esperado:** ✅ Dashboard responsivo (<3s)

---

### Test 9.2: SSE Latency (LOC-05)

**Objetivo:** Verificar latencia de actualización en tiempo real < 10 segundos.

**Pasos:**

1. Dashboard abierto con timestamp visible
2. En otro browser, ejecutar TOMAR
3. Cronometrar tiempo desde click "Confirmar" hasta actualización en dashboard

**Verificaciones:**

- [ ] Actualización visible en dashboard < 10 segundos
- [ ] Típicamente < 5 segundos en buenas condiciones de red

**Resultado Esperado:** ✅ Latencia sub-10s (requisito LOC-05)

---

## ✅ Test Summary Template

Usar para reportar resultados:

```markdown
## Test Execution Report

**Date:** [YYYY-MM-DD]
**Tester:** [Nombre]
**Environment:** Production / Staging / Local
**Browser:** Chrome/Firefox/Safari [version]

### Results Summary

| Phase | Tests | Passed | Failed | Notes |
|-------|-------|--------|--------|-------|
| Phase 2: Core Tracking | 4 | 4 | 0 | ✅ All Redis locks working |
| Phase 3: State Machines | 4 | 4 | 0 | ✅ Collaboration works |
| Phase 4: Real-Time | 4 | 3 | 1 | ⚠️ SSE disconnect after 5min |
| Phase 5: Metrología | 4 | 4 | 0 | ✅ Instant completion verified |
| Phase 6: Reparación | 5 | 5 | 0 | ✅ Cycle counting accurate |
| Backward Compat | 2 | 2 | 0 | ✅ v2.1 data intact |
| Edge Cases | 3 | 2 | 1 | ⚠️ Race condition in Test 8.3 |
| Performance | 2 | 2 | 0 | ✅ <10s latency |

**Overall:** 28/30 tests passed (93%)

### Bugs Found

1. **[Bug ID]:** SSE connection drops after 5 minutes idle
   - **Severity:** Medium
   - **Reproduce:** Dashboard idle for 5+ minutes
   - **Expected:** Keepalive should maintain connection
   - **Actual:** Connection closes, requires manual refresh

2. **[Bug ID]:** ...

### Recommendations

- Fix SSE keepalive timeout
- Add loading spinner on TOMAR confirmation
- Improve error message when spool already occupied
```

---

## 📝 Notes

**Test Coverage:**
- ✅ All 24 v3.0 requirements (LOC-01 to REPAR-04)
- ✅ 6 phases completely covered
- ✅ Edge cases and error handling
- ✅ Performance validation

**Estimated Time:** 2-3 hours for complete suite

**Tips:**
- Use 2 browsers en paralelo para tests de race conditions
- Mantén Google Sheets abierto para verificar escrituras en tiempo real
- Usa DevTools Network tab para verificar SSE connections
- Documenta TAG_SPOOLs usados para reproducibilidad

---

**Version:** v3.0
**Last Updated:** 2026-01-28
**Maintainer:** ZEUES Development Team
