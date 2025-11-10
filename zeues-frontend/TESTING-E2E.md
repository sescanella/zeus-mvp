# Testing E2E - ZEUES Frontend MVP

Guía de testing end-to-end para verificar los flujos completos de INICIAR y COMPLETAR acciones (ARM/SOLD).

**Servidor:** http://localhost:3001

---

## Flujo 1: INICIAR ARM (Armado)

### Pasos:
1. **P1 - Identificación**: Navegar a `/`
   - ✅ Verificar que aparecen 4 trabajadores (Juan Pérez, María López, Carlos Díaz, Ana García)
   - ✅ Seleccionar "Juan Pérez"

2. **P2 - Operación**: Navegar a `/operacion`
   - ✅ Verificar botón "Volver" funciona (regresa a P1)
   - ✅ Seleccionar "ARMADO (ARM)"

3. **P3 - Tipo Interacción**: Navegar a `/tipo-interaccion`
   - ✅ Verificar título muestra "ARMADO (ARM)"
   - ✅ Seleccionar "🔵 INICIAR ACCIÓN"

4. **P4 - Seleccionar Spool**: Navegar a `/seleccionar-spool?tipo=iniciar`
   - ✅ Verificar título: "Selecciona spool para INICIAR ARM"
   - ✅ Verificar que aparecen 5 spools disponibles (arm=0):
     - MK-1335-CW-25238-011
     - MK-1335-CW-25238-012
     - MK-1335-CW-25238-013
     - MK-1335-CW-25238-014
     - MK-1335-CW-25238-015
   - ✅ Seleccionar cualquier spool (ej: MK-1335-CW-25238-011)

5. **P5 - Confirmar**: Navegar a `/confirmar?tipo=iniciar`
   - ✅ Verificar título: "¿Confirmas INICIAR ARM?"
   - ✅ Verificar resumen muestra:
     - Trabajador: Juan Pérez
     - Operación: ARMADO (ARM)
     - Spool: MK-1335-CW-25238-011
   - ✅ Botón "Cancelar" muestra confirmación nativa
   - ✅ Presionar "✓ CONFIRMAR"
   - ✅ Verificar loading "Actualizando Google Sheets..."

6. **P6 - Éxito**: Navegar a `/exito`
   - ✅ Verificar checkmark verde grande (SVG)
   - ✅ Verificar mensaje: "¡Acción completada exitosamente!"
   - ✅ Verificar countdown de 5 segundos funciona
   - ✅ Verificar botón "REGISTRAR OTRA" funciona (regresa a P1)
   - ✅ Verificar botón "FINALIZAR" funciona (regresa a P1)
   - ✅ Verificar auto-redirect después de 5 segundos

---

## Flujo 2: COMPLETAR ARM (Armado)

### Pasos:
1. **P1 - Identificación**: Seleccionar "Juan Pérez"

2. **P2 - Operación**: Seleccionar "ARMADO (ARM)"

3. **P3 - Tipo Interacción**: Seleccionar "✅ COMPLETAR ACCIÓN"

4. **P4 - Seleccionar Spool**: `/seleccionar-spool?tipo=completar`
   - ✅ Verificar título: "Selecciona TU spool para COMPLETAR ARM"
   - ✅ Verificar que aparecen 2 spools en progreso asignados a "Juan Pérez":
     - MK-1337-CW-25250-031 (arm=0.1, armador=Juan Pérez)
     - MK-1337-CW-25250-032 (arm=0.1, armador=Juan Pérez)
   - ✅ Seleccionar cualquier spool

5. **P5 - Confirmar**: `/confirmar?tipo=completar`
   - ✅ Verificar título: "¿Confirmas COMPLETAR ARM?"
   - ✅ Verificar resumen incluye fecha actual
   - ✅ Presionar "✓ CONFIRMAR"

6. **P6 - Éxito**: Verificar flujo completo

---

## Flujo 3: INICIAR SOLD (Soldado)

### Pasos:
1. **P1 - Identificación**: Seleccionar "Carlos Díaz"

2. **P2 - Operación**: Seleccionar "SOLDADO (SOLD)"

3. **P3 - Tipo Interacción**: Seleccionar "🔵 INICIAR ACCIÓN"

4. **P4 - Seleccionar Spool**: `/seleccionar-spool?tipo=iniciar`
   - ✅ Verificar título: "Selecciona spool para INICIAR SOLD"
   - ✅ Verificar que aparecen 5 spools listos para soldar (arm=1.0, sold=0):
     - MK-1336-CW-25240-021
     - MK-1336-CW-25240-022
     - MK-1336-CW-25240-023
     - MK-1336-CW-25240-024
     - MK-1336-CW-25240-025
   - ✅ Seleccionar cualquier spool

5. **P5 - Confirmar**: `/confirmar?tipo=iniciar`
   - ✅ Verificar título: "¿Confirmas INICIAR SOLD?"
   - ✅ Verificar resumen muestra "SOLDADO (SOLD)"

6. **P6 - Éxito**: Verificar flujo completo

---

## Flujo 4: COMPLETAR SOLD (Soldado)

### Pasos:
1. **P1 - Identificación**: Seleccionar "Carlos Díaz"

2. **P2 - Operación**: Seleccionar "SOLDADO (SOLD)"

3. **P3 - Tipo Interacción**: Seleccionar "✅ COMPLETAR ACCIÓN"

4. **P4 - Seleccionar Spool**: `/seleccionar-spool?tipo=completar`
   - ✅ Verificar título: "Selecciona TU spool para COMPLETAR SOLD"
   - ✅ Verificar que aparecen 2 spools en progreso asignados a "Carlos Díaz":
     - MK-1339-CW-25270-051 (arm=1.0, sold=0.1, soldador=Carlos Díaz)
     - MK-1339-CW-25270-052 (arm=1.0, sold=0.1, soldador=Carlos Díaz)
   - ✅ Seleccionar cualquier spool

5. **P5 - Confirmar**: `/confirmar?tipo=completar`
   - ✅ Verificar título: "¿Confirmas COMPLETAR SOLD?"

6. **P6 - Éxito**: Verificar flujo completo

---

## Tests de Validación de Propiedad (Ownership)

### Test 5: Intentar completar spool de otro trabajador

1. Seleccionar "María López" en P1
2. Seleccionar "ARMADO (ARM)" en P2
3. Seleccionar "✅ COMPLETAR ACCIÓN" en P3
4. **Verificar** que solo aparecen los 2 spools de María López:
   - MK-1338-CW-25260-041
   - MK-1338-CW-25260-042
5. **NO deben aparecer** los spools de Juan Pérez

### Test 6: Intentar iniciar SOLD sin ARM completo

Este test se verifica con la lógica de filtrado:
- INICIAR SOLD solo muestra spools con `arm=1.0 && sold=0`
- Si un spool tiene `arm=0` o `arm=0.1`, NO aparece en INICIAR SOLD

---

## Tests de Navegación

### Test 7: Botón "Volver" en cada página
- ✅ P2 → P1
- ✅ P3 → P2
- ✅ P4 → P3
- ✅ P5 → P4

### Test 8: Botón "Cancelar" en P5
- ✅ Muestra confirmación nativa del navegador
- ✅ Si acepta: limpia estado y regresa a P1
- ✅ Si cancela: permanece en P5

### Test 9: Protección de rutas
- ✅ Navegar directamente a `/operacion` sin seleccionar trabajador → redirige a `/`
- ✅ Navegar a `/seleccionar-spool` sin estado → redirige a `/`
- ✅ Navegar a `/confirmar` sin spool → redirige a `/`

---

## Tests de UI/UX

### Test 10: Loading States
- ✅ P1: Loading al cargar trabajadores (500ms simulado)
- ✅ P4: Loading al cargar spools (500ms simulado)
- ✅ P5: Loading al confirmar (1s simulado, mensaje "Actualizando Google Sheets...")

### Test 11: Empty States
- ✅ P4: Si no hay spools disponibles, mostrar mensaje apropiado

### Test 12: Responsive Design
- ✅ Verificar en tablet (768px+): Grid 2 columnas en P1
- ✅ Verificar en móvil (<768px): Grid 1 columna
- ✅ Botones grandes (h-16 = 64px) para touch targets

---

## Checklist de Completitud DÍA 3

- ✅ P4: Seleccionar Spool implementada
- ✅ P5: Confirmar Acción implementada
- ✅ P6: Éxito implementada
- ✅ Filtrado de spools según tipo y operación
- ✅ Mock data (20 spools) cubre todos los escenarios
- ✅ Validación de propiedad (ownership)
- ✅ Estados de loading y error
- ✅ Navegación "Volver" en todas las páginas
- ✅ Cancelar con confirmación en P5
- ✅ Countdown y auto-redirect en P6
- ✅ Build production exitoso
- ✅ TypeScript sin errores
- ✅ ESLint sin warnings

---

## Notas Técnicas

**Mock Data:**
- 5 spools pendientes ARM (arm=0)
- 5 spools pendientes SOLD (arm=1.0, sold=0)
- 2 spools en progreso ARM por Juan Pérez
- 2 spools en progreso ARM por María López
- 2 spools en progreso SOLD por Carlos Díaz
- 2 spools en progreso SOLD por Ana García
- 2 spools completados (arm=1.0, sold=1.0)

**Próximo DÍA 4:**
- Integrar API real con backend FastAPI
- Reemplazar MOCK_SPOOLS con llamadas a `/api/spools`
- Reemplazar MOCK_WORKERS con llamadas a `/api/workers`
- Implementar POST `/api/iniciar-accion` y `/api/completar-accion`

---

**Fecha:** 10 Nov 2025
**Estado:** DÍA 3 completado - Listo para testing E2E manual
