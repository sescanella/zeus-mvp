# Guía de Testing Manual - Integración API ZEUES

**Fecha:** 10 Nov 2025
**Estado Backend:** ✅ Running (http://localhost:8000)
**Estado Frontend:** Listo para testing

---

## Pre-requisitos

### 1. Backend debe estar corriendo

```bash
# Terminal 1 - Backend
t
source venv/bin/activate
uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000
```

**Verificar health check:**
```bash
curl http://localhost:8000/api/health
# Debe retornar: {"status":"healthy","sheets_connection":"ok"}
```

### 2. Frontend debe estar corriendo

```bash
# Terminal 2 - Frontend
cd /Users/sescanella/Proyectos/ZEUES-by-KM/zeues-frontend
npm run dev
```

**Abrir en navegador:**
```
http://localhost:3000
```

---

## Test 1: Flujo INICIAR ARM (Happy Path)

**Objetivo:** Verificar que un trabajador puede iniciar una acción de ARMADO correctamente.

### Pasos:

1. **Seleccionar trabajador**
   - Abrir http://localhost:3000
   - Clic en un trabajador de la lista (ej: "Juan Pérez")
   - Verificar navegación a `/operacion`

2. **Seleccionar operación ARMADO**
   - Clic en botón "ARMADO (ARM)"
   - Verificar navegación a `/tipo-interaccion`

3. **Seleccionar INICIAR**
   - Clic en botón "INICIAR"
   - Verificar navegación a `/seleccionar-spool?tipo=iniciar`

4. **Verificar lista de spools disponibles**
   - Debe mostrar "Selecciona spool para INICIAR ARM"
   - Debe cargar spools desde API (sin mock data)
   - Verificar loading spinner durante carga
   - Verificar lista de spools con `arm=0`

5. **Seleccionar un spool**
   - Clic en un spool de la lista
   - Verificar navegación a `/confirmar?tipo=iniciar`

6. **Confirmar acción**
   - Verificar resumen muestra:
     - Trabajador correcto
     - Operación: ARMADO (ARM)
     - Tag del spool seleccionado
   - Clic en "✓ CONFIRMAR"
   - Verificar loading "Actualizando Google Sheets..."
   - Verificar navegación a `/exito`

7. **Verificar Google Sheets**
   - Abrir Google Sheets TESTING
   - Buscar el spool por TAG (columna G)
   - Verificar columna V (ARM) = 0.1 (EN_PROGRESO)
   - Verificar columna BC (Armador) = "Juan Pérez"

**Resultado esperado:** ✅ Acción iniciada correctamente, Sheets actualizado

---

## Test 2: Flujo COMPLETAR ARM (Happy Path)

**Objetivo:** Verificar que un trabajador puede completar SU PROPIA acción.

### Pasos:

1. **Usar mismo trabajador que inició** (ej: "Juan Pérez")
   - Seleccionar "Juan Pérez"
   - Seleccionar "ARMADO (ARM)"
   - Seleccionar "COMPLETAR"

2. **Verificar lista de spools propios**
   - Debe mostrar "Selecciona TU spool para COMPLETAR ARM"
   - Debe cargar solo spools donde `armador = "Juan Pérez"`
   - Lista puede estar vacía si no tiene spools en progreso

3. **Seleccionar el spool que inició en Test 1**
   - Clic en el spool
   - Confirmar

4. **Verificar Google Sheets**
   - Columna V (ARM) = 1.0 (COMPLETADO)
   - Columna BB (Fecha Armado) = fecha actual (DD/MM/YYYY)

**Resultado esperado:** ✅ Acción completada correctamente

---

## Test 3: Ownership Violation (403 Error) - CRÍTICO

**Objetivo:** Verificar que solo quien inició puede completar (validación crítica).

### Pasos:

1. **Iniciar ARM con trabajador 1**
   - Seleccionar trabajador 1 (ej: "Juan Pérez")
   - Iniciar ARM en un spool nuevo

2. **Intentar completar con trabajador 2 (diferente)**
   - Seleccionar trabajador 2 (ej: "María López")
   - Seleccionar ARM → COMPLETAR
   - Verificar lista VACÍA (no ve el spool de Juan)

   **Alternativa:** Modificar manualmente el estado del contexto (si tienes acceso a DevTools React) para forzar el intento de completar el spool de Juan

3. **Verificar error 403**
   - Debe mostrar componente `<ErrorMessage>` con:
     - Tipo: `forbidden` (🚫 icono)
     - Título: "No Autorizado"
     - Mensaje: "Solo Juan Pérez puede completar..."

**Resultado esperado:** ✅ Error 403 mostrado correctamente, ownership protegido

---

## Test 4: Error de Validación (400)

**Objetivo:** Verificar manejo de errores de validación (operación ya iniciada/completada).

### Pasos:

1. **Intentar iniciar ARM dos veces en mismo spool**
   - Iniciar ARM en spool X
   - Intentar iniciar ARM nuevamente en spool X

2. **Verificar error 400**
   - Debe mostrar `<ErrorMessage>` tipo `validation` (⚠️ icono)
   - Mensaje: "La operación ARM ya está iniciada..."

**Resultado esperado:** ✅ Error 400 mostrado con tipo correcto

---

## Test 5: Spool No Encontrado (404)

**Objetivo:** Verificar manejo de recursos no encontrados.

### Pasos:

1. **Seleccionar un spool que no existe**
   - (Requiere modificar temporalmente el código o usar DevTools)
   - Forzar tag_spool = "INVALID-TAG-12345"

2. **Verificar error 404**
   - Debe mostrar `<ErrorMessage>` tipo `not-found` (🔍 icono)
   - Mensaje: "Spool no encontrado..."

**Resultado esperado:** ✅ Error 404 mostrado correctamente

---

## Test 6: Error de Conexión (Network Error)

**Objetivo:** Verificar manejo cuando backend no está disponible.

### Pasos:

1. **Detener el backend**
   - En terminal del backend: Ctrl+C

2. **Intentar seleccionar spools**
   - Navegar a selección de spools
   - Esperar loading...

3. **Verificar error de red**
   - Debe mostrar `<ErrorMessage>` tipo `network` (🔌 icono)
   - Mensaje: "Error de conexión con el servidor..."
   - Debe mostrar botón "Reintentar"

4. **Probar botón Reintentar**
   - Clic en "Reintentar"
   - Debe volver a intentar carga

5. **Reiniciar backend y reintentar**
   - Iniciar backend nuevamente
   - Clic en "Reintentar"
   - Lista debe cargar correctamente

**Resultado esperado:** ✅ Error de red manejado, botón reintentar funciona

---

## Test 7: Error del Servidor (503)

**Objetivo:** Verificar manejo cuando Google Sheets no está disponible.

### Pasos:

1. **Simular error de Sheets**
   - (Requiere desconectar credenciales temporalmente o mock en backend)

2. **Verificar error 503**
   - Debe mostrar `<ErrorMessage>` tipo `server` (❌ icono)
   - Mensaje: "Error del servidor de Google Sheets..."
   - Debe mostrar botón "Reintentar"

**Resultado esperado:** ✅ Error 503 manejado correctamente

---

## Test 8: Flujo INICIAR SOLD (Happy Path)

**Objetivo:** Verificar flujo completo para SOLDADO.

### Pasos:

1. **Seleccionar trabajador**
   - Seleccionar trabajador (ej: "Carlos Díaz")

2. **Seleccionar SOLDADO**
   - Clic en "SOLDADO (SOLD)"
   - Seleccionar "INICIAR"

3. **Verificar filtros correctos**
   - Debe mostrar solo spools con:
     - `arm=1.0` (armado completado)
     - `sold=0` (soldadura pendiente)

4. **Completar flujo**
   - Seleccionar spool
   - Confirmar
   - Verificar Sheets actualizado:
     - W = 0.1
     - BE = "Carlos Díaz"

**Resultado esperado:** ✅ Flujo SOLD funciona correctamente

---

## Test 9: Flujo COMPLETAR SOLD

**Objetivo:** Verificar completar soldadura.

### Pasos:

1. **Usar mismo trabajador**
   - Seleccionar "Carlos Díaz"
   - SOLDADO → COMPLETAR

2. **Completar el spool iniciado**
   - Seleccionar spool
   - Confirmar

3. **Verificar Sheets**
   - W = 1.0
   - BD = fecha actual

**Resultado esperado:** ✅ Soldadura completada correctamente

---

## Test 10: Cancelar en cualquier paso

**Objetivo:** Verificar que botón "Cancelar" funciona en confirmación.

### Pasos:

1. **Llegar a página de confirmación**
   - Seleccionar trabajador, operación, tipo, spool

2. **Clic en "Cancelar"**
   - Debe mostrar alerta: "¿Seguro que quieres cancelar?"
   - Clic en "Aceptar"

3. **Verificar reset**
   - Debe redirigir a `/` (página inicial)
   - Estado debe estar limpio

**Resultado esperado:** ✅ Cancelar resetea estado correctamente

---

## Checklist de Verificación Final

- [ ] ✅ TypeScript compila sin errores (`npx tsc --noEmit`)
- [ ] ✅ ESLint sin warnings (`npm run lint`)
- [ ] ✅ Build production funciona (`npm run build`)
- [ ] ✅ Backend health check OK
- [ ] ✅ Test 1: INICIAR ARM funciona
- [ ] ✅ Test 2: COMPLETAR ARM funciona
- [ ] ✅ Test 3: Ownership 403 error funciona
- [ ] ✅ Test 4: Error 400 validación funciona
- [ ] ✅ Test 5: Error 404 not found funciona
- [ ] ✅ Test 6: Error de red funciona + botón reintentar
- [ ] ✅ Test 7: Error 503 servidor funciona
- [ ] ✅ Test 8: INICIAR SOLD funciona
- [ ] ✅ Test 9: COMPLETAR SOLD funciona
- [ ] ✅ Test 10: Cancelar funciona
- [ ] ✅ Google Sheets se actualiza correctamente
- [ ] ✅ No hay `any` types en código TypeScript
- [ ] ✅ Mock data eliminado completamente
- [ ] ✅ Componente ErrorMessage muestra iconos correctos

---

## Comandos Útiles

### Backend
```bash
# Health check
curl http://localhost:8000/api/health

# Listar workers
curl http://localhost:8000/api/workers

# Spools para iniciar ARM
curl "http://localhost:8000/api/spools/iniciar?operacion=ARM"

# Spools para completar ARM de Juan
curl "http://localhost:8000/api/spools/completar?operacion=ARM&worker_nombre=Juan%20Pérez"

# Iniciar acción (POST)
curl -X POST http://localhost:8000/api/iniciar-accion \
  -H "Content-Type: application/json" \
  -d '{"worker_nombre": "Juan Pérez", "operacion": "ARM", "tag_spool": "MK-XXX"}'
```

### Frontend
```bash
# Build de producción
npm run build

# TypeScript check
npx tsc --noEmit

# Lint check
npm run lint
```

---

## Bugs Conocidos a Verificar

1. **Loading state no se muestra:** Si la API responde muy rápido, el loading puede no verse
2. **Navegación hacia atrás pierde estado:** Verificar que Context API persiste datos
3. **Espacios en nombres de trabajadores:** Verificar URL encoding correcto
4. **Case sensitivity en nombres:** Backend normaliza con `.lower()`, verificar coincidencia

---

## Próximos Pasos Después de Testing

1. ✅ Todos los tests pasando
2. ✅ Bugs encontrados documentados
3. ✅ Correcciones implementadas
4. ✅ Re-testing después de fixes
5. ✅ Deploy a Railway (frontend + backend)
6. ✅ Testing en producción

---

**¿Todo funciona?** → Marcar tarea "Testing manual completo" como ✅
**Encontraste bugs?** → Pasar a tarea "Corregir bugs encontrados"
