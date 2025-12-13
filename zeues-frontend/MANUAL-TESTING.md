# 📋 Plan de Pruebas Manuales - ZEUES v2.0

**Fecha:** 13 Diciembre 2025
**Versión:** v2.0 (Multiselect + Search + Batch CANCELAR)
**Ambiente:** Producción (Vercel + Railway)
**Tester:** _______________

---

## ✅ Pre-requisitos

- [ ] Frontend desplegado en Vercel: https://zeues-frontend.vercel.app
- [ ] Backend funcionando en Railway: https://zeues-backend-mvp-production.up.railway.app
- [ ] Google Sheet conectado (ID: 17iOaq2sv4mSOuJY4B8dGQIsWTTUKPspCtb7gk6u-MaQ)
- [ ] Tablet o navegador en modo responsive (768x1024)

---

## 📱 SECCIÓN 1: Flujo Básico v1.0 - INICIAR ARM

**Objetivo:** Verificar flujo de inicio de armado en modo individual

### Test 1.1: INICIAR ARM - Flujo Completo Individual
- [ ] **P1** - Abrir https://zeues-frontend.vercel.app
- [ ] **P1** - Verificar que aparecen 6 trabajadores (Mauricio, Nicolás, Carlos, Fernando, Manuel, Alexis)
- [ ] **P1** - Click en **Mauricio Rodriguez**
- [ ] **P2** - Verificar que aparece "Hola Mauricio Rodriguez, ¿Qué vas a hacer?"
- [ ] **P2** - Verificar que aparecen botones "🔧 ARMADO (ARM)" y "🔥 SOLDADO (SOLD)"
- [ ] **P2** - Click en **ARMADO (ARM)**
- [ ] **P3** - Verificar título "¿Qué acción vas a realizar?"
- [ ] **P3** - Verificar que aparecen botones "INICIAR ACCIÓN" y "COMPLETAR ACCIÓN"
- [ ] **P3** - Click en **INICIAR ACCIÓN**
- [ ] **P4** - Verificar título "Seleccionar Spool para INICIAR ARM"
- [ ] **P4** - Verificar que aparece toggle "Individual" (activado por defecto)
- [ ] **P4** - Verificar que aparece lista de spools disponibles (TAG_SPOOL: MK-1335-...)
- [ ] **P4** - Click en **primer spool disponible**
- [ ] **P5** - Verificar título "¿Confirmas INICIAR ARM?"
- [ ] **P5** - Verificar que muestra el TAG_SPOOL seleccionado
- [ ] **P5** - Verificar que aparecen botones "CONFIRMAR" (verde) y "Cancelar" (rojo)
- [ ] **P5** - Click en **CONFIRMAR**
- [ ] **P6** - Verificar que aparece página de éxito con ícono verde ✓
- [ ] **P6** - Verificar mensaje "¡Éxito! Acción registrada"
- [ ] **P6** - Verificar que muestra detalles: Trabajador, Operación ARM, INICIAR
- [ ] **P6** - Verificar que muestra TAG_SPOOL registrado
- [ ] **P6** - Verificar botón "REGISTRAR OTRA ACCIÓN"
- [ ] **P6** - Esperar 5 segundos → Verificar redirect automático a P1

**Resultado:** ✅ PASS / ❌ FAIL
**Notas:** _______________________________________________

---

## 📱 SECCIÓN 2: Flujo Básico v1.0 - COMPLETAR ARM

**Objetivo:** Verificar flujo de completar armado con ownership validation

### Test 2.1: COMPLETAR ARM - Mismo Trabajador (Ownership OK)
- [ ] **P1** - Seleccionar **Mauricio Rodriguez** (mismo que inició)
- [ ] **P2** - Click en **ARMADO (ARM)**
- [ ] **P3** - Click en **COMPLETAR ACCIÓN**
- [ ] **P4** - Verificar título "Seleccionar Spool para COMPLETAR ARM"
- [ ] **P4** - Verificar que solo aparecen spools EN_PROGRESO de Mauricio
- [ ] **P4** - Click en **spool que se inició en Test 1.1**
- [ ] **P5** - Click en **CONFIRMAR**
- [ ] **P6** - Verificar éxito ✓
- [ ] **P6** - Verificar detalles: COMPLETAR ARM

**Resultado:** ✅ PASS / ❌ FAIL

### Test 2.2: COMPLETAR ARM - Diferente Trabajador (Ownership FAIL)
- [ ] **P1** - Seleccionar **Nicolás Rodriguez** (diferente trabajador)
- [ ] **P2** - Click en **ARMADO (ARM)**
- [ ] **P3** - Click en **COMPLETAR ACCIÓN**
- [ ] **P4** - Si aparecen spools de Mauricio, intentar seleccionar uno
- [ ] **P5** - Click en **CONFIRMAR**
- [ ] **P6** - Verificar que muestra error 403 "No autorizado" o "Solo el trabajador que inició puede completar"

**Resultado:** ✅ PASS / ❌ FAIL
**Notas:** _______________________________________________

---

## 📱 SECCIÓN 3: Navegación y Botones

**Objetivo:** Verificar que navegación funciona correctamente

### Test 3.1: Botón "Volver" en cada página
- [ ] **P2** - Click en "← Volver" → Debe volver a P1
- [ ] **P1** - Seleccionar worker y navegar a P2
- [ ] **P3** - Click en "← Volver" → Debe volver a P2
- [ ] **P2** - Navegar a P3
- [ ] **P4** - Click en "← Volver" → Debe volver a P3
- [ ] **P3** - Navegar a P4
- [ ] **P5** - Click en "← Volver" → Debe volver a P4

**Resultado:** ✅ PASS / ❌ FAIL

### Test 3.2: Botón "Cancelar" (rojo) en P5
- [ ] **Navegar hasta P5** (cualquier flujo)
- [ ] **P5** - Click en **Cancelar** (botón rojo)
- [ ] Verificar que aparece modal de confirmación "¿Estás seguro?"
- [ ] Click en **Sí, cancelar** → Debe volver a P1
- [ ] **Navegar hasta P5** nuevamente
- [ ] **P5** - Click en **Cancelar**
- [ ] En modal, click en **No, continuar** → Debe permanecer en P5

**Resultado:** ✅ PASS / ❌ FAIL
**Notas:** _______________________________________________

---

## 🆕 SECCIÓN 4: Multiselect v2.0 - Toggle Individual ↔ Múltiple

**Objetivo:** Verificar que el toggle cambia entre modo individual y múltiple

### Test 4.1: Activar Modo Múltiple
- [ ] **Navegar hasta P4** (INICIAR ARM con Mauricio)
- [ ] **P4** - Verificar que toggle muestra "Individual" por defecto
- [ ] **P4** - Verificar que aparece lista de spools (sin checkboxes)
- [ ] **P4** - Click en **toggle switch** (activar modo múltiple)
- [ ] Verificar que cambia a "Múltiple (hasta 50)"
- [ ] Verificar que aparece barra de búsqueda con placeholder "Buscar por TAG_SPOOL"
- [ ] Verificar que aparece contador "0 de X spools seleccionados"
- [ ] Verificar que aparecen botones "Seleccionar Todos" y "Deseleccionar Todos"
- [ ] Verificar que cada spool ahora tiene un **checkbox** visible
- [ ] Verificar que botón "Continuar" está **deshabilitado** (0 seleccionados)

**Resultado:** ✅ PASS / ❌ FAIL

### Test 4.2: Volver a Modo Individual
- [ ] **P4** - Desde modo Múltiple, click en **toggle switch** nuevamente
- [ ] Verificar que vuelve a "Individual"
- [ ] Verificar que desaparecen checkboxes
- [ ] Verificar que desaparece barra de búsqueda
- [ ] Verificar que desaparecen botones "Seleccionar Todos/Deseleccionar Todos"
- [ ] Verificar que vuelve a lista normal (click directo en spool)

**Resultado:** ✅ PASS / ❌ FAIL
**Notas:** _______________________________________________

---

## 🆕 SECCIÓN 5: Multiselect v2.0 - Selección con Checkboxes

**Objetivo:** Verificar selección múltiple con checkboxes

### Test 5.1: Seleccionar 3 Spools Manualmente
- [ ] **P4** - Activar modo Múltiple
- [ ] Click en **checkbox del primer spool**
- [ ] Verificar que checkbox queda marcado ✓
- [ ] Verificar que contador muestra "1 de X spools seleccionados"
- [ ] Click en **checkbox del segundo spool**
- [ ] Verificar contador "2 de X spools seleccionados"
- [ ] Click en **checkbox del tercer spool**
- [ ] Verificar contador "3 de X spools seleccionados"
- [ ] Verificar que botón "Continuar con 3 spools" está **habilitado**
- [ ] Verificar color cyan en spools seleccionados

**Resultado:** ✅ PASS / ❌ FAIL

### Test 5.2: Deseleccionar Spool
- [ ] **P4** - Con 3 spools seleccionados
- [ ] Click en **checkbox del tercer spool** (deseleccionar)
- [ ] Verificar que checkbox queda desmarcado ☐
- [ ] Verificar contador "2 de X spools seleccionados"
- [ ] Verificar que botón cambia a "Continuar con 2 spools"

**Resultado:** ✅ PASS / ❌ FAIL

### Test 5.3: Botón "Seleccionar Todos"
- [ ] **P4** - Click en **Deseleccionar Todos** (limpiar selección)
- [ ] Verificar contador "0 de X"
- [ ] Click en **Seleccionar Todos**
- [ ] Verificar que TODOS los checkboxes visibles quedan marcados ✓
- [ ] Verificar contador "X de X spools seleccionados" (X = total disponibles)

**Resultado:** ✅ PASS / ❌ FAIL

### Test 5.4: Botón "Deseleccionar Todos"
- [ ] **P4** - Con todos seleccionados
- [ ] Click en **Deseleccionar Todos**
- [ ] Verificar que TODOS los checkboxes quedan desmarcados ☐
- [ ] Verificar contador "0 de X spools seleccionados"
- [ ] Verificar botón "Continuar" **deshabilitado**

**Resultado:** ✅ PASS / ❌ FAIL
**Notas:** _______________________________________________

---

## 🆕 SECCIÓN 6: Multiselect v2.0 - Batch INICIAR

**Objetivo:** Verificar que operación batch INICIAR funciona con múltiples spools

### Test 6.1: Batch INICIAR ARM con 3 Spools
- [ ] **P4** - Activar modo Múltiple
- [ ] Seleccionar **3 spools** con checkboxes
- [ ] Click en **Continuar con 3 spools**
- [ ] **P5** - Verificar título "¿Confirmas INICIAR ARM en 3 spools?"
- [ ] **P5** - Verificar que muestra "Spools seleccionados: 3"
- [ ] **P5** - Verificar que aparece lista con los 3 TAG_SPOOL
- [ ] Click en **CONFIRMAR**
- [ ] **P6** - Verificar título "Operación batch exitosa" (o similar)
- [ ] **P6** - Verificar stats: "3 exitosos / 0 fallidos de 3 spools"
- [ ] **P6** - Verificar sección "✓ Exitosos (3)" con lista de spools
- [ ] **P6** - Verificar que NO aparece sección "Fallidos"
- [ ] Esperar 5 segundos → Verificar redirect a P1

**Resultado:** ✅ PASS / ❌ FAIL
**Notas (anotar los 3 TAG_SPOOL iniciados):** _______________________________________________

---

## 🆕 SECCIÓN 7: Búsqueda TAG_SPOOL v2.0

**Objetivo:** Verificar que búsqueda filtra spools en tiempo real

### Test 7.1: Búsqueda Filtra en Tiempo Real
- [ ] **P4** - Activar modo Múltiple (debe aparecer barra de búsqueda)
- [ ] Verificar placeholder "Buscar por TAG_SPOOL"
- [ ] Contar cuántos spools aparecen inicialmente (anotar: ____)
- [ ] En barra de búsqueda, escribir **"MK-1335"**
- [ ] Verificar que la lista se filtra en tiempo real (mientras escribes)
- [ ] Verificar que solo aparecen spools con "MK-1335" en el TAG_SPOOL
- [ ] Verificar que aparece mensaje "Mostrando X de Y spools" (donde X < Y)
- [ ] Borrar búsqueda → Verificar que vuelven todos los spools

**Resultado:** ✅ PASS / ❌ FAIL

### Test 7.2: Búsqueda Case-Insensitive
- [ ] **P4** - En barra de búsqueda, escribir **"mk-1335"** (minúsculas)
- [ ] Verificar que encuentra spools (case-insensitive)
- [ ] Borrar y escribir **"MK-1335"** (MAYÚSCULAS)
- [ ] Verificar que encuentra los mismos spools
- [ ] Borrar y escribir **"Mk-1335"** (MixedCase)
- [ ] Verificar que funciona igual

**Resultado:** ✅ PASS / ❌ FAIL

### Test 7.3: Búsqueda Sin Resultados
- [ ] **P4** - En barra de búsqueda, escribir **"ZZZZZ-NOEXISTE-9999"**
- [ ] Verificar que aparece mensaje "No se encontraron spools que coincidan con 'ZZZZZ-NOEXISTE-9999'"
- [ ] Verificar que NO aparecen checkboxes
- [ ] Verificar que botones "Seleccionar Todos" y "Deseleccionar Todos" están **deshabilitados**
- [ ] Borrar búsqueda → Verificar que vuelven los spools

**Resultado:** ✅ PASS / ❌ FAIL

### Test 7.4: Seleccionar Spools Filtrados
- [ ] **P4** - Escribir **"MK-1335"** en búsqueda
- [ ] Seleccionar **2 spools** de los resultados filtrados con checkboxes
- [ ] Verificar contador "2 de X" (donde X = total filtrados, no total general)
- [ ] Click en **Continuar con 2 spools**
- [ ] **P5** - Verificar que muestra los 2 spools filtrados seleccionados
- [ ] **P5** - Click en **Volver**
- [ ] **P4** - Verificar que búsqueda y selección se mantienen

**Resultado:** ✅ PASS / ❌ FAIL
**Notas:** _______________________________________________

---

## 🆕 SECCIÓN 8: Batch CANCELAR v2.0

**Objetivo:** Verificar flujo CANCELAR (nueva acción v2.0)

### Test 8.1: Setup - INICIAR 3 Spools para Poder Cancelarlos
- [ ] **P1** - Seleccionar **Mauricio Rodriguez**
- [ ] **P2** - Click en **ARMADO (ARM)**
- [ ] **P3** - Click en **INICIAR ACCIÓN**
- [ ] **P4** - Activar modo Múltiple
- [ ] Seleccionar **3 spools**
- [ ] Click en **Continuar con 3 spools**
- [ ] **P5** - Click en **CONFIRMAR**
- [ ] **P6** - Verificar éxito "3 exitosos"
- [ ] Click en **REGISTRAR OTRA ACCIÓN** (volver a P1)

**Anotar los 3 TAG_SPOOL iniciados:**
1. _________________
2. _________________
3. _________________

### Test 8.2: Batch CANCELAR ARM con 3 Spools (Mismo Worker)
- [ ] **P1** - Seleccionar **Mauricio Rodriguez** (mismo que inició)
- [ ] **P2** - Click en **ARMADO (ARM)**
- [ ] **P3** - Click en **CANCELAR ACCIÓN** ⚠️
- [ ] **P4** - Verificar título "Seleccionar Spool para CANCELAR ARM"
- [ ] **P4** - Verificar que solo aparecen spools EN_PROGRESO
- [ ] **P4** - Activar modo Múltiple
- [ ] Seleccionar los **3 spools** que se iniciaron en Test 8.1
- [ ] Click en **Continuar con 3 spools**
- [ ] **P5** - Verificar título "¿Confirmas CANCELAR ARM en 3 spools?"
- [ ] **P5** - Click en **CONFIRMAR**
- [ ] **P6** - Verificar título con ícono amarillo ⚠️ (warning)
- [ ] **P6** - Verificar stats: "3 exitosos / 0 fallidos"
- [ ] **P6** - Verificar sección "Exitosos (3)"
- [ ] **P6** - Verificar que NO aparece sección "Fallidos"

**Resultado:** ✅ PASS / ❌ FAIL

### Test 8.3: Verificar Spools Cancelados Vuelven a PENDIENTE
- [ ] **P6** - Click en **REGISTRAR OTRA ACCIÓN**
- [ ] **P1** - Seleccionar **Mauricio Rodriguez**
- [ ] **P2** - Click en **ARMADO (ARM)**
- [ ] **P3** - Click en **INICIAR ACCIÓN**
- [ ] **P4** - Buscar los 3 spools que se cancelaron en Test 8.2
- [ ] Verificar que los 3 spools **aparecen nuevamente** en la lista (estado PENDIENTE)
- [ ] Verificar que se pueden seleccionar y volver a iniciar

**Resultado:** ✅ PASS / ❌ FAIL
**Notas:** _______________________________________________

---

## 🆕 SECCIÓN 9: Batch CANCELAR - Ownership Validation

**Objetivo:** Verificar que solo el worker que inició puede cancelar

### Test 9.1: CANCELAR con Diferente Worker (Debe Fallar)
- [ ] **P1** - Seleccionar **Nicolás Rodriguez** (diferente trabajador)
- [ ] **P2** - Click en **ARMADO (ARM)**
- [ ] **P3** - Click en **INICIAR ACCIÓN**
- [ ] **P4** - Activar modo Múltiple
- [ ] Seleccionar **2 spools**
- [ ] Click en **Continuar con 2 spools** → **CONFIRMAR**
- [ ] **P6** - Verificar éxito "2 exitosos" (Nicolás inició 2 spools)
- [ ] Click en **REGISTRAR OTRA ACCIÓN**
- [ ] **P1** - Seleccionar **Mauricio Rodriguez** (trabajador diferente)
- [ ] **P2** - Click en **ARMADO (ARM)**
- [ ] **P3** - Click en **CANCELAR ACCIÓN**
- [ ] **P4** - Si aparecen spools de Nicolás, intentar seleccionarlos
- [ ] Click en **Continuar** → **CONFIRMAR**
- [ ] **P6** - Verificar que muestra "X fallidos" > 0
- [ ] **P6** - Verificar sección "✗ Fallidos (X)"
- [ ] **P6** - Verificar mensaje de error "No autorizado" o "Solo el trabajador que inició puede cancelar"

**Resultado:** ✅ PASS / ❌ FAIL
**Notas:** _______________________________________________

---

## 🆕 SECCIÓN 10: Límite de 50 Spools

**Objetivo:** Verificar que no se pueden seleccionar más de 50 spools

### Test 10.1: Intentar Seleccionar Más de 50 (si hay suficientes spools)
- [ ] **P4** - Activar modo Múltiple
- [ ] Si hay 50+ spools disponibles, click en **Seleccionar Todos**
- [ ] Verificar que contador muestra "50 de X" (máximo 50)
- [ ] Verificar que aparece mensaje "Límite máximo: 50 spools"
- [ ] Verificar que checkboxes NO seleccionados están **deshabilitados** (grises)
- [ ] Intentar marcar un checkbox deshabilitado → Verificar que NO se puede

**Resultado:** ✅ PASS / ❌ FAIL (o N/A si hay menos de 50 spools)
**Notas:** _______________________________________________

---

## 📱 SECCIÓN 11: Responsive Design

**Objetivo:** Verificar que UI funciona en tablets y móviles

### Test 11.1: Diseño Mobile (375px)
- [ ] Abrir DevTools → Modo responsive → 375px x 667px (iPhone SE)
- [ ] **P1** - Verificar que cards de workers se apilan verticalmente (1 por fila)
- [ ] **P1** - Verificar que botones son grandes y táctiles (h-16)
- [ ] Navegar a **P4** modo Múltiple
- [ ] **P4** - Verificar que barra de búsqueda es full-width
- [ ] **P4** - Verificar que checkboxes son grandes (w-6 h-6 = 24px)
- [ ] **P4** - Verificar que grid de spools se adapta (2 columnas en mobile)

**Resultado:** ✅ PASS / ❌ FAIL

### Test 11.2: Diseño Tablet (768px)
- [ ] Modo responsive → 768px x 1024px (iPad)
- [ ] **P1** - Verificar que cards de workers se muestran en grid (2-3 por fila)
- [ ] **P4** - Verificar que grid de spools muestra 3 columnas
- [ ] **P6** - Si hay resultados mixtos (exitosos + fallidos), verificar layout 2-column grid

**Resultado:** ✅ PASS / ❌ FAIL
**Notas:** _______________________________________________

---

## 🔴 SECCIÓN 12: Casos de Error

**Objetivo:** Verificar manejo de errores

### Test 12.1: Backend No Disponible
- [ ] Detener backend manualmente (Railway down)
- [ ] Abrir frontend → **P1**
- [ ] Verificar que muestra mensaje "Error de conexión con el servidor"
- [ ] Verificar que aparece botón "Reintentar"
- [ ] Click en **Reintentar** → Verificar que intenta reconectar

**Resultado:** ✅ PASS / ❌ FAIL

### Test 12.2: Sin Spools Disponibles
- [ ] Navegar a **P4** con operación que no tiene spools disponibles
- [ ] Verificar que muestra mensaje "No hay spools disponibles para esta operación"

**Resultado:** ✅ PASS / ❌ FAIL
**Notas:** _______________________________________________

---

## ✅ Checklist Final Pre-Deploy

- [ ] ✅ PASS: Test 1.1 - INICIAR ARM Individual
- [ ] ✅ PASS: Test 2.1 - COMPLETAR ARM Ownership OK
- [ ] ✅ PASS: Test 2.2 - COMPLETAR ARM Ownership FAIL
- [ ] ✅ PASS: Test 3.1 - Navegación Volver
- [ ] ✅ PASS: Test 3.2 - Botón Cancelar
- [ ] ✅ PASS: Test 4.1 - Activar Modo Múltiple
- [ ] ✅ PASS: Test 5.1 - Seleccionar 3 Spools
- [ ] ✅ PASS: Test 5.3 - Seleccionar Todos
- [ ] ✅ PASS: Test 6.1 - Batch INICIAR 3 Spools
- [ ] ✅ PASS: Test 7.1 - Búsqueda Filtra Tiempo Real
- [ ] ✅ PASS: Test 7.3 - Búsqueda Sin Resultados
- [ ] ✅ PASS: Test 8.2 - Batch CANCELAR 3 Spools
- [ ] ✅ PASS: Test 8.3 - Spools Vuelven a PENDIENTE
- [ ] ✅ PASS: Test 9.1 - CANCELAR Ownership FAIL
- [ ] ✅ PASS: Test 11.1 - Responsive Mobile
- [ ] ✅ PASS: Test 11.2 - Responsive Tablet

---

## 📊 Resumen de Resultados

**Total Tests Ejecutados:** ______ / 25
**Tests Passed (✅):** ______
**Tests Failed (❌):** ______
**Tests Skipped/N/A:** ______

**Bugs Encontrados:**
1. _____________________________________________
2. _____________________________________________
3. _____________________________________________

**Decisión:**
- [ ] ✅ **APROBADO** - Deploy a producción
- [ ] ⚠️ **APROBADO CON RESERVAS** - Deploy con bugs menores conocidos
- [ ] ❌ **RECHAZADO** - Requiere fixes antes de deploy

**Firma Tester:** _______________
**Fecha:** _______________
**Hora:** _______________

---

## 🚀 Siguiente Paso

Si todos los tests críticos pasan, ejecutar:
```bash
cd zeues-frontend
vercel --prod --yes
```

Luego validar en producción: https://zeues-frontend.vercel.app
