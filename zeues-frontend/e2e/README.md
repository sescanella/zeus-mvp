# Tests E2E Automatizados - ZEUES Frontend

Tests automatizados con Playwright para los 4 flujos principales del MVP.

## Estructura de Tests

```
e2e/
├── 01-iniciar-arm.spec.ts      # Flujo INICIAR ARM (happy path)
├── 02-completar-arm.spec.ts    # Flujo COMPLETAR ARM (happy path)
├── 03-iniciar-sold.spec.ts     # Flujo INICIAR SOLD (happy path)
├── 04-completar-sold.spec.ts   # Flujo COMPLETAR SOLD (happy path)
├── 05-error-handling.spec.ts   # Tests de manejo de errores (403, 400, 404, network, 503)
├── 06-cancelacion.spec.ts      # Tests de flujo de cancelación
└── README.md
```

## Prerequisitos

1. **Asegurar que el servidor está corriendo en localhost:3001**
   ```bash
   cd zeues-frontend
   npm run dev
   ```

2. **Instalar navegadores de Playwright** (solo primera vez)
   ```bash
   npx playwright install
   ```

## Comandos Disponibles

### 1. Ejecutar todos los tests (headless)
```bash
npm run test:e2e
```

Este comando:
- Ejecuta todos los tests en modo headless
- Genera reporte HTML automáticamente
- Útil para CI/CD y validación rápida

### 2. Modo UI (Recomendado para desarrollo)
```bash
npm run test:e2e:ui
```

Abre una interfaz visual donde puedes:
- Ver los tests en tiempo real
- Ejecutar tests individuales
- Ver el timeline de cada paso
- Inspeccionar elementos

### 3. Modo Debug
```bash
npm run test:e2e:debug
```

Abre Playwright Inspector para:
- Ejecutar tests paso a paso
- Pausar en breakpoints
- Inspeccionar el DOM
- Ver selectores en tiempo real

### 4. Modo Headed (Ver el navegador)
```bash
npm run test:e2e:headed
```

Ejecuta los tests mostrando el navegador en acción.

### 5. Ver reporte HTML
```bash
npm run test:e2e:report
```

Abre el último reporte generado en el navegador.

## Ejecutar un test específico

```bash
# Solo el flujo INICIAR ARM
npx playwright test 01-iniciar-arm

# Solo el flujo COMPLETAR SOLD
npx playwright test 04-completar-sold

# Con UI mode
npx playwright test 01-iniciar-arm --ui
```

## Cobertura de Tests

### ✅ Flujo 1: INICIAR ARM (01-iniciar-arm.spec.ts)
- Selección de trabajador (Juan Pérez)
- Selección de operación ARMADO
- Tipo de interacción INICIAR
- Selección de spool disponible (arm=0)
- Confirmación con loading
- Página de éxito con countdown
- Navegación Volver entre páginas

### ✅ Flujo 2: COMPLETAR ARM (02-completar-arm.spec.ts)
- Trabajador con spools en progreso
- Filtrado por propiedad (ownership)
- Solo muestra spools del trabajador actual
- Validación de fecha en confirmación
- Test de aislamiento entre trabajadores

### ✅ Flujo 3: INICIAR SOLD (03-iniciar-sold.spec.ts)
- Trabajador soldador (Carlos Díaz)
- Solo spools con arm=1.0 (armado completo)
- Validación de prerequisitos
- No muestra spools con arm=0 o arm=0.1

### ✅ Flujo 4: COMPLETAR SOLD (04-completar-sold.spec.ts)
- Trabajador con spools SOLD en progreso
- Filtrado por propiedad del soldador
- Test de auto-redirect después de 5 segundos
- Validación de aislamiento entre soldadores

### ✅ Error Handling (05-error-handling.spec.ts)
- **Test 3**: 403 Forbidden - Ownership Violation (CRÍTICO)
- **Test 4**: 400 Bad Request - Error de validación (operación ya iniciada)
- **Test 5**: 404 Not Found - Spool no encontrado
- **Test 6**: Network Error - Backend no disponible + botón Reintentar
- **Test 7**: 503 Service Unavailable - Google Sheets no disponible

### ✅ Flujo de Cancelación (06-cancelacion.spec.ts)
- **Test 10**: Cancelar desde página de confirmación (INICIAR)
- Cancelar desde página de confirmación (COMPLETAR)
- Rechazar cancelación y permanecer en confirmación
- Verificar reset completo de estado
- Verificar alerta de confirmación "¿Seguro que quieres cancelar?"

## Validaciones Implementadas

1. **Ownership (Propiedad)**
   - COMPLETAR solo muestra spools propios
   - Validación por nombre de trabajador
   - Aislamiento entre trabajadores
   - Error 403 cuando se intenta completar acción de otro trabajador

2. **Prerequisites (Prerequisitos)**
   - INICIAR SOLD solo con arm=1.0
   - Filtrado correcto por estado de spool
   - Error 400 cuando operación ya está iniciada

3. **Navegación**
   - Botones Volver funcionan
   - Redirecciones correctas
   - Estado compartido entre páginas
   - Cancelar con confirmación y reset completo

4. **UI/UX**
   - Loading states visibles
   - Mensajes de confirmación
   - Countdown funcional
   - Auto-redirect después de 5 segundos

5. **Error Handling (NUEVO)**
   - Manejo de 403 Forbidden (ownership violation)
   - Manejo de 400 Bad Request (validación de negocio)
   - Manejo de 404 Not Found (spool no existe)
   - Manejo de Network Error (backend caído)
   - Manejo de 503 Service Unavailable (Sheets no disponible)
   - Botón Reintentar para errores recuperables
   - Iconos específicos según tipo de error
   - Mensajes descriptivos y accionables

## Configuración

La configuración de Playwright está en `playwright.config.ts`:

- **Base URL:** http://localhost:3001
- **Viewport:** 768x1024 (tablet)
- **Timeout:** 30 segundos por test
- **Screenshots:** Solo en fallas
- **Videos:** Solo en retry
- **Trace:** En primera retry

## Debugging

### Si un test falla:

1. **Ver el reporte HTML:**
   ```bash
   npm run test:e2e:report
   ```

2. **Ejecutar en modo UI:**
   ```bash
   npm run test:e2e:ui
   ```

3. **Ver el test específico con debug:**
   ```bash
   npx playwright test 01-iniciar-arm --debug
   ```

4. **Ver screenshots de fallas:**
   Los screenshots se guardan en `test-results/`

## CI/CD

Para ejecutar en GitHub Actions u otro CI:

```yaml
- name: Install dependencies
  run: cd zeues-frontend && npm install

- name: Install Playwright Browsers
  run: cd zeues-frontend && npx playwright install --with-deps

- name: Run E2E tests
  run: cd zeues-frontend && npm run test:e2e
```

## Resumen de Cobertura

| Categoría | Tests | Descripción |
|-----------|-------|-------------|
| Happy Paths | 6 tests | Flujos INICIAR/COMPLETAR ARM/SOLD + navegación |
| Error Handling | 5 tests | 403, 400, 404, Network, 503 |
| Cancelación | 3 tests | Cancelar, rechazar, reset estado |
| **TOTAL** | **14 tests** | **Cobertura completa del TESTING-MANUAL.md** |

## Próximos pasos

✅ **Tests E2E completos** - Alineados 100% con TESTING-MANUAL.md

Para ejecutar con backend real:

1. Verificar que backend esté corriendo en puerto 8000
2. Verificar que frontend esté corriendo en puerto 3001
3. Ejecutar: `npm run test:e2e`
4. Para demo visual: `npm run test:e2e:demo`

**Pendiente:**
- Tests de performance (< 30 segundos por flujo)
- Tests de integración con Google Sheets real (requiere datos de prueba)

---

**Última actualización:** 10 Nov 2025
**Estado:** Tests E2E completos - 14 tests automatizados (Tests 1-10 del manual)
