# ZEUES - Sistema de Trazabilidad para Manufactura de Cañerías

**Documentación del Proyecto - Vista de Producto y Negocio**

📚 **Documentación del Proyecto:**
- `proyecto.md` - Especificación general del MVP (este archivo)
- `proyecto-backend.md` - Documentación técnica completa del backend Python/FastAPI
- `proyecto-frontend.md` - Arquitectura y estado del frontend Next.js (max 1500 líneas)
- `proyecto-frontend-ui.md` - Detalles implementación UI: componentes y páginas (max 1500 líneas)
- `zeues-frontend/TESTING-E2E.md` - Guía testing manual E2E (12 test cases)
- `CLAUDE.md` - Guía rápida para Claude Code
- `docs/GOOGLE-RESOURCES.md` - Configuración de recursos Google

---

## 1. Visión y Objetivos

### Visión
Sistema digital simple con 2 interacciones por acción: trabajadores INICIAN acciones para asignarse spools antes de trabajar, y COMPLETAN acciones al terminar. Actualización automática Google Sheets, eliminando entrada manual.

### Objetivos del MVP
1. Digitalizar registro de ARM (Armado) y SOLD (Soldado) desde tablet
2. Eliminar errores manuales de entrada de datos
3. Actualizar Google Sheets en tiempo real automáticamente
4. Validar viabilidad con 2 operaciones antes de escalar
5. Interfaz intuitiva sin capacitación técnica extensa

### Criterios de Éxito
- 100% acciones ARM/SOLD vía tablet en semana 2
- Tiempo registro < 30 segundos
- 0 errores sincronización con Google Sheets
- Adopción 80%+ trabajadores en semana 1
- Feedback positivo sobre facilidad de uso

---

## 2. Problema y Alcance

### Estado Actual
- Administrador marca manualmente acciones en Google Sheets (sistema ternario: 1=completado, 0.1=en progreso, 0=pendiente)
- Trabajadores no pueden auto-asignarse spools ni registrar inicio/finalización directamente
- Entrada manual genera errores y delay en tiempo real
- Falta visibilidad en tiempo real de quién está trabajando en qué spool

### DENTRO del Alcance MVP
✅ Identificación trabajador (botones con nombres)
✅ Selección operación: ARM o SOLD
✅ Selección tipo interacción: INICIAR o COMPLETAR acción
✅ Identificación spool por TAG_SPOOL
✅ Pantallas confirmación para inicio y finalización
✅ Actualización automática Google Sheets (V/W: 0→0.1→1, metadata BB/BC/BD/BE)
✅ Filtrado inteligente: solo spools disponibles para iniciar (0) o propios para completar (0.1)
✅ Interfaz mobile-first para tablets

### FUERA del Alcance MVP
❌ Otras 8 acciones | ❌ Auth complejo | ❌ Panel admin | ❌ Reports avanzados | ❌ Notificaciones | ❌ Modo offline | ❌ Edición/eliminación registros | ❌ Función "cancelar" acción iniciada (solo admin resuelve manualmente)

### Fase 2
🔄 10 acciones completas | Panel admin | Reports productividad | Modo offline | Notificaciones

---

## 3. Usuarios

### Trabajador de Planta (Principal)
- Realiza armado/soldado de spools en piso de producción
- Experiencia técnica limitada, trabaja con guantes en ambiente industrial
- Necesita: UI simple, botones grandes (60px+), proceso < 30 seg por interacción, confirmación visual, ver solo spools disponibles o propios
- Pain points: No puede auto-asignarse spools antes de trabajar, no puede registrar inicio/fin directamente, no visibilidad de quién tiene qué spool

### Administrador de Plantilla (Secundario)
- Gestiona Google Sheets (fuente de verdad)
- Define qué spools requieren qué acciones
- Necesita: Sheets actualizado automáticamente, visibilidad acciones registradas
- Pain points: Entrada manual tediosa y propensa a errores

---

## 4. Funcionalidades Clave MVP

**F1. Identificación Trabajador**: Botones grandes con nombres, sin credenciales
**F2. Selección Operación**: Botones ARM/SOLD con íconos visuales
**F3. Selección Tipo Interacción**: Botones INICIAR ACCIÓN / COMPLETAR ACCIÓN
**F4. Identificación Spool**:
- **INICIAR**: Búsqueda TAG_SPOOL, lista filtrada:
  - ARM: V=0, BA contiene dato, BB vacía
  - SOLD: W=0, BB contiene valor, BD vacía
- **COMPLETAR**: Lista filtrada (valor=0.1 en V/W, trabajador coincide en BC/BE)
**F5. Confirmación**: Resumen (trabajador, acción, tipo interacción, spool), botones Confirmar/Cancelar
**F6. Actualización Sheets**:
- **INICIAR**: V/W → 0.1, escribir nombre en BC (ARM) o BE (SOLD)
- **COMPLETAR**: V/W → 1.0, escribir fecha en BB (ARM) o BD (SOLD)
**F7. Feedback Éxito**: Mensaje claro, opción registrar otra interacción, timeout 5seg → inicio
**F8. Restricción Propiedad**: Solo el trabajador que inició puede completar (validación backend)

---

## 5. Historias de Usuario

**HU-01: Iniciar ARM**
Como trabajador que va a comenzar armado, quiero iniciar acción desde tablet para asignarme el spool antes de trabajar.
Acepto: Identificación, selección ARM, botón INICIAR, lista spools (V=0, BA llena, BB vacía), confirmación, V→0.1 + BC=mi nombre, éxito visual, < 30 seg

**HU-02: Completar ARM**
Como trabajador que terminó armado, quiero completar acción desde tablet para registrar finalización.
Acepto: Identificación, selección ARM, botón COMPLETAR, lista solo mis spools (V=0.1, BC=mi nombre), confirmación, V→1.0 + BB=fecha, éxito visual, < 30 seg

**HU-03: Iniciar SOLD**
Como trabajador que va a comenzar soldado, quiero iniciar acción desde tablet para asignarme el spool antes de trabajar.
Acepto: Identificación, selección SOLD, botón INICIAR, lista spools (W=0, BB llena, BD vacía), confirmación, W→0.1 + BE=mi nombre, éxito visual, < 30 seg

**HU-04: Completar SOLD**
Como trabajador que terminó soldado, quiero completar acción desde tablet para registrar finalización.
Acepto: Identificación, selección SOLD, botón COMPLETAR, lista solo mis spools (W=0.1, BE=mi nombre), confirmación, W→1.0 + BD=fecha, éxito visual, < 30 seg

**HU-05: Restricción Propiedad**
Como sistema, debo asegurar que solo el trabajador que inició una acción pueda completarla.
Acepto: Al COMPLETAR, filtrar solo spools con nombre trabajador en BC (ARM) o BE (SOLD), validación backend

**HU-06: Cancelar Antes Confirmar**
Como trabajador, quiero cancelar/volver antes de confirmar para corregir errores.
Acepto: Botón Volver en cada pantalla, regresar sin perder contexto, no registra hasta confirmación

**HU-07: Ver Spools Relevantes**
Como trabajador, quiero ver solo spools disponibles para iniciar o mis propios spools para completar.
Acepto: INICIAR ARM → V=0+BA llena+BB vacía | INICIAR SOLD → W=0+BB llena+BD vacía | COMPLETAR → filtro por mi nombre en BC/BE

---

## 6. Flujo de Usuario (2 Flujos: INICIAR y COMPLETAR)

### FLUJO A: INICIAR ACCIÓN (Asignarse spool antes de trabajar)

**1. IDENTIFICACIÓN**: "¿Quién eres?" → Botones nombres trabajadores → Registra usuario_id
**2. OPERACIÓN**: "Hola [Nombre], ¿qué vas a hacer?" → Botones ARM/SOLD → Registra tipo_operacion
**3. TIPO INTERACCIÓN**: Botones grandes [🔵 INICIAR ACCIÓN] / [✅ COMPLETAR ACCIÓN] → Selecciona INICIAR
**4. SPOOL DISPONIBLE**: "Selecciona spool para iniciar" → Lista filtrada:
  - ARM: V=0, BA llena, BB vacía (solo spools con materiales disponibles)
  - SOLD: W=0, BB llena, BD vacía (solo spools armados disponibles)
  - Muestra: TAG_SPOOL | Proyecto | Estado dependencias
**5. CONFIRMACIÓN**: "¿Iniciar [ARM/SOLD] en [TAG]?" → Resumen (Trabajador|Acción|Spool) → Botones CONFIRMAR (cyan #0891B2) / CANCELAR
**6. PROCESAMIENTO**: Loading → API busca fila (col G) → Actualiza:
  - ARM: V→0.1, BC=nombre trabajador
  - SOLD: W→0.1, BE=nombre trabajador
**7. ÉXITO**: "¡Spool asignado! Ya puedes trabajar" + Checkmark cyan → Botones [REGISTRAR OTRA] / [FINALIZAR] → Timeout 5seg → PASO 1

### FLUJO B: COMPLETAR ACCIÓN (Registrar finalización)

**1. IDENTIFICACIÓN**: "¿Quién eres?" → Botones nombres trabajadores → Registra usuario_id
**2. OPERACIÓN**: "Hola [Nombre], ¿qué completaste?" → Botones ARM/SOLD → Registra tipo_operacion
**3. TIPO INTERACCIÓN**: Botones grandes [🔵 INICIAR ACCIÓN] / [✅ COMPLETAR ACCIÓN] → Selecciona COMPLETAR
**4. MIS SPOOLS EN PROGRESO**: "Selecciona spool para completar" → Lista filtrada SOLO PROPIOS:
  - ARM: V=0.1, BC=mi nombre (solo mis spools en progreso)
  - SOLD: W=0.1, BE=mi nombre (solo mis spools en progreso)
  - Muestra: TAG_SPOOL | Proyecto
**5. CONFIRMACIÓN**: "¿Completar [ARM/SOLD] en [TAG]?" → Resumen (Trabajador|Acción|Spool|Fecha actual) → Botones CONFIRMAR (verde #16A34A) / CANCELAR
**6. PROCESAMIENTO**: Loading → API busca fila (col G) → Valida propiedad (BC/BE = usuario) → Actualiza:
  - ARM: V→1.0, BB=fecha actual
  - SOLD: W→1.0, BD=fecha actual
**7. ÉXITO**: "¡Acción completada! Registrado exitosamente" + Checkmark verde → Botones [REGISTRAR OTRA] / [FINALIZAR] → Timeout 5seg → PASO 1

### FLUJOS ALTERNATIVOS

- **Error Validación**: "Este spool no te pertenece. Solo puedes completar acciones iniciadas por ti" → Volver PASO 4
- **Error Conexión**: "Error al conectar con Sheets. Intenta nuevamente" → Botones REINTENTAR/CANCELAR, mantener datos
- **Cancelar**: Confirmar cancelación → Volver PASO 1, no guarda nada
- **Volver**: Botón disponible en cada pantalla, regresa paso anterior, mantiene información
- **Sin Spools**: INICIAR muestra "No hay spools disponibles" | COMPLETAR muestra "No tienes spools en progreso"
- **Spool Abandonado**: Si trabajador nunca completa acción iniciada → Solo admin puede resetear manualmente en Sheets (no hay función cancelar en MVP)

---

## 7. Modelo de Datos

### Archivo plantilla.xlsx
**Hoja**: "Operaciones" | **Spools**: 292 filas | **Columnas**: 78

### Columnas Críticas

**Identificación:**
- **A**: id (interno)
- **G**: TAG_SPOOL / CODIGO BARRA (único) - Ej: "MK-1335-CW-25238-011"

**Estado (no crítico MVP):**
- **H**: STATUS_NV | **I**: Status_Spool | **R**: PROCESO | **S**: Prioridad

**Operaciones MVP:**
- **V**: ARM (1.0=completado, 0.1=en progreso/iniciado, 0=pendiente/no iniciado) - Actualizado por sistema
- **W**: SOLD (1.0=completado, 0.1=en progreso/iniciado, 0=pendiente/no iniciado) - Actualizado por sistema

**Metadata Acciones (CRÍTICAS):**
- **BA**: Fecha_Materiales (requisito para iniciar ARM: BA debe estar llena)
- **BB**: Fecha_Armado (requisito para iniciar SOLD: BB debe estar llena) - Escrita al COMPLETAR ARM (no al iniciar)
- **BC**: Armador - Escrito al INICIAR ARM, usado para filtrar al COMPLETAR ARM
- **BD**: Fecha_Soldadura - Escrita al COMPLETAR SOLD (no al iniciar)
- **BE**: Soldador - Escrito al INICIAR SOLD, usado para filtrar al COMPLETAR SOLD

**Otras Operaciones (Fase 2):**
- **X**: MET | **Y**: NDT | **Z**: REV | **AA**: PINT | **AB**: LIBER | **AC**: DESP | **AD**: Avance_(%)

### Modelo Aplicación

**Trabajador**: `{ worker_id, nombre, apellido?, activo }` - Fuente: Hoja "Trabajadores"

**Spool**: `{ id, tag_spool, arm, sold, fecha_materiales, fecha_armado, armador, fecha_soldadura, soldador, ... }`

### Lógica Filtrado (CRÍTICA)

**⚠️ SECUENCIA OBLIGATORIA**: Materiales (BA) → Armado (BB) → Soldadura (BD)

**INICIAR ARM**: Mostrar spools con V=0 (no iniciado), BA llena (materiales listos), BB vacía (aún no armado)
**COMPLETAR ARM**: Mostrar spools con V=0.1 (en progreso) Y BC=nombre_trabajador (solo mis spools)
**INICIAR SOLD**: Mostrar spools con W=0 (no iniciado), BB llena (ya armado), BD vacía (aún no soldado)
**COMPLETAR SOLD**: Mostrar spools con W=0.1 (en progreso) Y BE=nombre_trabajador (solo mis spools)

**FLUJO COMPLETO POR ACCIÓN**:
- **ARM**: INICIAR (V: 0→0.1, BC=nombre) → Trabajo físico → COMPLETAR (V: 0.1→1.0, BB=fecha)
- **SOLD**: INICIAR (W: 0→0.1, BE=nombre) → Trabajo físico → COMPLETAR (W: 0.1→1.0, BD=fecha)

**VALORES POSIBLES**: 0 = pendiente | 0.1 = en progreso/iniciado | 1.0 = completado

---

## 8. Arquitectura Técnica

### Stack Seleccionado: Python FastAPI + React/Next.js

**Backend**: Python + FastAPI + gspread (Google Sheets API) - Ver `proyecto-backend.md` para detalles técnicos completos
**Frontend**: React/Next.js + Tailwind CSS + shadcn/ui - Ver `proyecto-frontend.md` para detalles técnicos completos
**Deploy**: Railway (backend) + Vercel (frontend)
**Razón**: Mejor soporte Google Sheets, separación frontend/backend, escalabilidad

### Arquitectura General
```
TABLET → HTTPS → FRONTEND (Vercel) → API REST → BACKEND (Railway) → Google Sheets API → GOOGLE SHEETS (fuente verdad)
```

### API Endpoints (6 endpoints)

```
GET  /api/workers                  - Lista trabajadores activos
GET  /api/spools/iniciar           - Spools para iniciar (V/W=0, dependencias ok)
     ?operacion=ARM|SOLD
GET  /api/spools/completar         - Spools para completar (V/W=0.1, filtro por trabajador)
     ?operacion=ARM|SOLD&worker_nombre=Juan
POST /api/iniciar-accion           - Iniciar acción (V/W→0.1, BC/BE=nombre)
     { worker_nombre, operacion, tag_spool }
POST /api/completar-accion         - Completar acción (V/W→1.0, BB/BD=fecha)
     { worker_nombre, operacion, tag_spool }
GET  /api/health                   - Health check
```

**Documentación Técnica Completa:** Ver `proyecto-backend.md` para detalles de implementación, modelos, servicios, repositorio, excepciones, testing y deployment.

### Validaciones Clave

**Backend (Ver proyecto-backend.md para detalles):**
- Validación restricción propiedad (solo quien inició puede completar)
- Validación estados (0/0.1/1.0)
- Validación dependencias (BA→BB→BD)
- Error handling con 10 excepciones custom
- Retry con backoff exponencial

**Frontend:**
- Validaciones cliente (campos requeridos, formato)
- Confirmación antes de acciones irreversibles
- Loading states y error handling
- Feedback visual inmediato

---

## 9. Diseño UI/UX

### Principios
1. Botones grandes (60px+ altura), espaciado generoso - uso con guantes
2. Contraste alto - legible en luz variable
3. Feedback inmediato - respuesta visual cada acción
4. Minimal typing - preferir selección
5. Confirmación antes acciones irreversibles
6. Progreso visible - usuario sabe en qué paso está

### Paleta de Colores

**MARCA Y PRIMARIOS**
- Principal: #FF5B00 (Naranja ZEUES) - Marca, header, botones primarios, elementos destacados
- Secundario: #0A7EA4 (Azul Profundo) - Soporte, navegación secundaria, contraste frío
- Acento: #E64A19 (Naranja Oscuro) - Hover estados, énfasis cálido

**BOTONES DE ACCIÓN (CRÍTICOS - Alta diferenciación)**
- INICIAR: #0891B2 (Cyan Industrial) - Botón iniciar acción, pantallas P3/P5A/P6A, badges "en progreso"
- COMPLETAR: #16A34A (Verde Acción) - Botón completar acción, pantallas P3/P5B/P6B, confirmaciones finales

**ESTADOS DEL SISTEMA**
- Éxito: #16A34A (Verde Acción) - Mensajes confirmación, checkmarks, operaciones exitosas
- Error: #DC2626 (Rojo Alerta) - Mensajes error, validaciones fallidas, estados críticos
- Warning: #EA580C (Naranja Warning) - Advertencias, acciones que requieren atención
- Info: #0891B2 (Cyan Industrial) - Mensajes informativos, tooltips, ayuda contextual

**UI Y FONDOS**
- Fondo Principal: #F8FAFC (Gris Claro) - Fondo general app, máxima legibilidad
- Fondo Secundario: #FFFFFF (Blanco) - Cards, modales, áreas contenido
- Fondo Hover: #F1F5F9 (Gris Hover) - Interacciones hover sobre listas/botones secundarios
- Texto Primario: #0F172A (Gris Oscuro) - Texto principal, títulos, contenido crítico
- Texto Secundario: #64748B (Gris Medio) - Texto descriptivo, labels, metadata
- Bordes: #E2E8F0 (Gris Borde) - Separadores, bordes cards, divisores

**CONTRASTE Y ACCESIBILIDAD**
- Todos los colores cumplen WCAG AA (4.5:1 texto, 3:1 UI)
- INICIAR (#0891B2) vs COMPLETAR (#16A34A): Diferenciación inmediata (frío vs cálido)
- Texto sobre fondos coloreados usa blanco (#FFFFFF) con ratio >7:1
- Bordes visibles con contraste mínimo 3:1 en todas las condiciones de luz

### Wireframes (Conceptual)
**P1 - Identificación**: "¿Quién eres?" + Grid botones nombres trabajadores
**P2 - Operación**: "Hola [Nombre], ¿qué vas a hacer?" + Botones grandes [🔧 ARM] [🔥 SOLD] + Botón Volver
**P3 - Tipo Interacción**: Título acción seleccionada + Botones grandes [🔵 INICIAR ACCIÓN cyan] [✅ COMPLETAR ACCIÓN verde] + Descripciones breves + Botón Volver
**P4A - Spool Iniciar**: "Selecciona spool para iniciar [ARM/SOLD]" + Lista filtrada (TAG|Proyecto|Estado dependencias) + Botón Volver
**P4B - Spool Completar**: "Selecciona TU spool para completar [ARM/SOLD]" + Lista solo propios (TAG|Proyecto) + Mensaje "Solo tus spools en progreso" + Botón Volver
**P5A - Confirmación Iniciar**: "¿Iniciar [ARM/SOLD]?" + Card resumen (Trabajador|Acción|Spool) + Botones [✓ CONFIRMAR cyan] [Cancelar]
**P5B - Confirmación Completar**: "¿Completar [ARM/SOLD]?" + Card resumen (Trabajador|Acción|Spool|Fecha) + Botones [✓ CONFIRMAR verde] [Cancelar]
**P6A - Éxito Iniciar**: Checkmark cyan + "¡Spool asignado! Ya puedes trabajar" + Botones [REGISTRAR OTRA] [FINALIZAR] + "Vuelve en 5seg"
**P6B - Éxito Completar**: Checkmark verde + "¡Acción completada!" + Botones [REGISTRAR OTRA] [FINALIZAR] + "Vuelve en 5seg"

### Especificaciones
**Tipografía**: Títulos 24-32px bold | Botones 18-20px semibold | Cuerpo 16-18px regular
**Espaciado**: Padding botones 16px vert / 24px horiz | Gap 16px | Margen contenedor 24px

---

## 10. Roadmap del Proyecto

### Fase 0: Setup ✅ COMPLETADA (07 Nov 2025)
**Duración:** 1 día
**Tareas:** Google Cloud + Service Account, compartir Sheets TESTING, variables de entorno, Git
**Entregable:** Repo configurado, API access ok, credenciales protegidas
**Estado:** 100% completado - Sin bloqueadores

### Fase 1: Backend (08-11 Nov 2025)
**Duración:** 4 días
**Documentación:** Ver `proyecto-backend.md` para detalles técnicos completos

**Día 1 ✅ COMPLETADO (08 Nov):** Setup + Models + Repository + Tests
- 10 archivos implementados
- 4 tests pasando (100%)
- Conexión Google Sheets verificada

**Día 2 (09 Nov) ✅ COMPLETADO:** Services + Validations
- ValidationService (restricción propiedad CRÍTICA) ✅
- SheetsService, SpoolService, WorkerService ✅
- ActionService (orquesta workflow completo) ✅
- Tests unitarios 95% coverage ActionService (objetivo >90%) ✅
- 113 tests totales pasando ✅

**Día 3 (10 Nov) ✅ COMPLETADO:** API Endpoints + Integration
- 6 endpoints FastAPI funcionando
- Exception handlers completos
- Dependency injection integrada
- Tests E2E (10 tests: 5 passing, 5 skipped esperando datos)

**Día 4 (11 Nov - PENDIENTE):** Deploy + Testing exhaustivo + Monitoreo
- Railway deployment
- Agregar datos prueba a Sheets TESTING
- Tests E2E completos (10/10 passing)
- Monitoreo y logs

**Entregable:** API backend funcionando en Railway, documentación OpenAPI, tests pasando

### Fase 2: Frontend (12-17 Nov 2025)
**Duración:** 6 días
**Tareas:**
- 6 pantallas (ID, Operación, Tipo Interacción, Spool, Confirmar, Éxito)
- Navegación 2 flujos (INICIAR/COMPLETAR)
- Integración API (6 endpoints)
- Loading/error states
- Mobile-first UI (Tailwind + shadcn/ui)

**Entregable:** 2 flujos completos navegables, integración frontend-backend ok

### Fase 3: Testing (18 Nov 2025)
**Duración:** 1 día
**Tareas:** E2E completos, test tablet real, ajustes UX, edge cases
**Entregable:** App testeada, validación restricción propiedad ok

### Fase 4: Deploy (19 Nov 2025)
**Duración:** 1 día
**Tareas:** Vercel frontend, cambio a Sheet PRODUCCIÓN, testing prod
**Entregable:** App live en producción

### Fase 5: Launch (20 Nov 2025)
**Duración:** 1 día
**Tareas:** Capacitación usuarios, lanzamiento gradual, monitoreo
**Entregable:** MVP en uso

### Fase 6: Post-MVP (continuo)
**Tareas:** Métricas, feedback, mejoras, planning Fase 2 (10 acciones)

---

## 11. Supuestos, Restricciones y Riesgos

### Supuestos
**Técnicos**: WiFi estable en planta | Google Sheets configurado y compartido | Estructura columnas consistente | Browsers modernos | Single tablet MVP
**Negocio**: Lista trabajadores definida | Spools con código único | Secuencia ARM→SOLD | Administrador disponible | Volumen moderado (~10 spools/día)

### Restricciones
- Presupuesto bajo (servicios gratuitos/baratos)
- Timeline: 2-3 semanas max (target 17 Nov 2025 = 11 días)
- Recursos: 1-2 desarrolladores
- Integrar con Google Sheets existente (no reemplazar)
- Equipo planta sin expertise técnico
- Google Sheets limits: 500 req/100seg/proyecto, 100 req/100seg/usuario, 5M celdas/sheet

### Dependencias Externas
Google Sheets API (crítica - si down, sistema no funciona) | Internet planta | Tablet física (a adquirir)

### Riesgos y Mitigación
| Riesgo | P | I | Mitigación |
|--------|---|---|------------|
| Conectividad intermitente | M | A | Reintentos auto, mensajes claros, offline Fase 2 |
| Límites API Sheets | B | A | Caché 5min, batch, monitoreo quota, DB Fase 2 |
| Resistencia cambio trabajadores | M | A | UI simple, capacitación práctica enfatizando INICIAR→COMPLETAR, gradual, feedback |
| Confusión flujo 2 interacciones | M | A | UI muy clara (colores distintos INICIAR/COMPLETAR), capacitación enfática, tooltips, mensajes contextuales |
| Spools abandonados (iniciados no completados) | M | M | Monitoreo admin (filtrar V/W=0.1 antiguos), reseteo manual, dashboard admin Fase 2 |
| Errores validación propiedad | B | C | Tests exhaustivos, mensajes error claros, logging auditoría |
| Errores update Sheets | M | C | Tests, validaciones backend, logging, confirmación |
| Cambios estructura Sheets | M | A | Documentar, validación inicio, comunicación admin |
| Acceso tablet no controlado | B | M | Logs auditoría, ubicación controlada, PIN Fase 2 |
| Múltiples tablets | A | M | Arquitectura escala, concurrencia API, locking Fase 2 |

P=Probabilidad (B=Baja/M=Media/A=Alta) | I=Impacto (M=Medio/A=Alto/C=Crítico)

---

## 12. Respuestas del Cliente (27 Preguntas) - ✅ TODAS RESPONDIDAS

**Actualizado**: 06 Nov 2025

### CRÍTICAS - Estructura Datos
**1. Valor 0.1**: Operación iniciada/en progreso (ahora marcado por trabajador al INICIAR, no por admin)
**2. Metadata Actualización**:
- **INICIAR ARM**: V→0.1 + BC=Nombre Armador (NO escribe BB)
- **COMPLETAR ARM**: V→1.0 + BB=Fecha_Armado (BC ya existe)
- **INICIAR SOLD**: W→0.1 + BE=Nombre Soldador (NO escribe BD)
- **COMPLETAR SOLD**: W→1.0 + BD=Fecha_Soldadura (BE ya existe)
**3. Filtrado Spools**: SECUENCIA OBLIGATORIA por fechas BA→BB→BD
- **INICIAR ARM**: V=0, BA llena, BB vacía (spools con materiales disponibles)
- **COMPLETAR ARM**: V=0.1, BC=nombre_trabajador (solo mis spools iniciados)
- **INICIAR SOLD**: W=0, BB llena, BD vacía (spools armados disponibles)
- **COMPLETAR SOLD**: W=0.1, BE=nombre_trabajador (solo mis spools iniciados)
**4. Sheets vs Excel**: Google Sheets ACTIVO, plantilla.xlsx es copia referencia
**5. Nombre Hoja**: "Operaciones"
**6. TAG_SPOOL**: SIN patrón específico, buscar coincidencia exacta col G
**7. Otras Columnas**: Solo BA/BB/BD para filtros MVP, H/I/R/S no relevantes

### Trabajadores
**8. Cantidad**: 8 total planta (2 admins, 2 soldadores, 2 armadores, 2 ayudantes) | 4 usuarios tablet (2+2) | Escalable a 12
**9. Fijos/Rotan**: FIJOS (mismos 4 trabajadores)
**10. Especialización**: TODOS ven ARM y SOLD (armador puede soldar y viceversa)
**11. Turnos**: NO hay turnos, solo fecha/hora suficiente
**12. Gestión Lista**: Crear hoja "Trabajadores" en Sheets para admin agregar/quitar sin modificar código

### Spools y Proceso
**13. ID Física**: Etiqueta física con TAG_SPOOL visible
**14. Códigos Barras**: NO en MVP, búsqueda manual (scanner Fase 2)
**15. Deshacer/Cancelar Iniciada**: NO incluir en MVP, si trabajador inicia y no completa → solo admin resetea manualmente (modifica 0.1→0 y limpia BC/BE en Sheets)
**16. Secuencia ARM→SOLD**: SÍ obligatoria por filtros fechas BA→BB→BD
**17. Op Ya Completada**: Mostrar error "ya completada, contactar admin si necesita corrección"
**18. Restricción Propiedad**: Solo quien INICIÓ (nombre en BC/BE) puede COMPLETAR esa acción

### Hardware/Infraestructura
**19-20. Tablet**: AÚN NO tienen, planean comprar, web app funciona cualquier tablet moderna (Android/iPad)
**21. WiFi**: SÍ disponible y confiable en toda planta
**22. Ubicación**: Estación fija (montada lugar específico)
**23. Modo Kiosko**: NO necesario MVP, acceso navegador normal

### Lanzamiento
**24. Fecha Objetivo**: 17 Noviembre 2025 (11 días)
**25. Prueba**: Lanzamiento gradual con 4 trabajadores
**26. Soporte**: 2 admins plantilla (nivel 1), desarrollador (nivel técnico)
**27. Volumen**: ~10 spools/día (~40 interacciones/día: 10 INICIAR ARM + 10 COMPLETAR ARM + 10 INICIAR SOLD + 10 COMPLETAR SOLD), bajo, manejable MVP

---

## 13. Métricas de Éxito (KPIs)

**Adopción**: 100% interacciones vía tablet semana 2 | 80%+ trabajadores usando sistema | 2+ interacciones/trabajador/turno (INICIAR+COMPLETAR)
**Eficiencia**: < 30 seg/interacción (INICIAR o COMPLETAR) | 99%+ tasa éxito | < 5 min delay entre INICIAR y trabajo físico
**Calidad**: 0 errores sync/día | < 1% registros incorrectos | 99%+ uptime | 0 completados por trabajador incorrecto (validación propiedad)
**Satisfacción**: NPS > 7/10 | Ratio feedback 4:1 positivo | 0 solicitudes volver manual
**Técnicas**: < 2 seg carga página | < 1 seg respuesta API | < 50% quota Sheets | Filtros INICIAR/COMPLETAR < 500ms

---

## 14. Estado Actual del Proyecto

**Última Actualización**: 11 Nov 2025
**Inicio Desarrollo**: 07 Nov 2025
**Estado**: BACKEND 100% COMPLETADO Y DEPLOYADO ✅ | Frontend 60% en progreso

### Backend (Ver proyecto-backend.md para detalles técnicos)

**✅ DÍA 0: Setup (07 Nov 2025) - 100% COMPLETADO**
- Infraestructura Google Cloud configurada (proyecto zeus-mvp)
- Service Account creada y credenciales descargadas
- Google Sheets API habilitada y verificada
- Sheet TESTING compartido y accesible
- Variables de entorno configuradas
- Estructura de columnas validada (78 totales, 9 críticas)

**✅ DÍA 1: Backend Setup + Models + Repository (08 Nov 2025) - 100% COMPLETADO**
- 10 archivos backend implementados y funcionando
- Modelos Pydantic completos (5 archivos)
- Jerarquía de excepciones (10 custom)
- SheetsRepository con retry y batch operations
- 4 tests pasando (100% exitosos)
- Conexión Google Sheets verificada: 292 spools, 5 trabajadores

**✅ DÍA 2 FASE 0: BLOQUEANTES RESUELTOS (09 Nov 2025) - 100% COMPLETADO**
- Cache implementado con TTL configurable (300s Trabajadores, 60s Operaciones)
- Parser robusto string→float sin crashes (292 spools parseados exitosamente)
- 42 tests unitarios pasando (13 cache + 29 SheetsService)
- Reducción -92% API calls verificada (4,800 → 372 calls/hora estimado)
- Coverage: cache 100%, SheetsService 66%
- 4 archivos nuevos creados, 2 modificados

**✅ DÍA 2 FASE 1: SERVICES + VALIDATIONS (09 Nov 2025) - 100% COMPLETADO**
- ValidationService implementado (345 líneas, 24 tests) - **OWNERSHIP VALIDATION CRÍTICA** ✅
- SpoolService implementado (243 líneas, 15 tests) - Filtros INICIAR/COMPLETAR ✅
- WorkerService implementado (134 líneas, 11 tests) - CRUD trabajadores ✅
- 50 tests nuevos pasando (total acumulado: 92 tests)
- Coverage: 83% total (superando objetivo 80%)
- 6 archivos nuevos creados, 1 modificado (requirements.txt)

**✅ DÍA 2 FASE 2: ACTION SERVICE (09 Nov 2025) - 100% COMPLETADO**
- ActionService implementado (484 líneas, 21 tests) - **WORKFLOW ORCHESTRATION COMPLETO** ✅
- Métodos: `iniciar_accion()` y `completar_accion()` con validación crítica de ownership ✅
- Batch updates a Google Sheets para performance ✅
- Cache invalidation automática después de updates ✅
- 21 tests nuevos pasando (total acumulado: 113 tests)
- Coverage: 95% ActionService (superando objetivo 90%)
- 2 archivos nuevos creados (service + tests)

**✅ DÍA 3: API LAYER (10 Nov 2025) - 100% COMPLETADO**
- 8 archivos implementados (2,044 líneas vs 1,810 estimadas)
- FASE 1: Infraestructura Base (logger.py, dependency.py, main.py) - 673 líneas ✅
- FASE 2: Routers READ-ONLY (health.py, workers.py, spools.py) - 450 líneas ✅
- FASE 3: Router WRITE CRÍTICO (actions.py con ownership validation) - 224 líneas ✅
- FASE 4: Tests E2E (test_api_flows.py con 10 tests) - 697 líneas ✅
- 6 endpoints API funcionando: health, workers, spools iniciar/completar, iniciar-accion, completar-accion
- Exception handlers completos (ZEUSException → HTTP status codes)
- OpenAPI docs automático en /api/docs
- 10 tests E2E: 5 passing, 5 skipped (esperando datos en Sheets TESTING)

**✅ DÍA 4 FASE 1: TESTING EXHAUSTIVO (10 Nov 2025) - 100% COMPLETADO**
- **✅ 10/10 tests E2E passing (100% success rate) - OBJETIVO CUMPLIDO**
- Dataset especializado generado: 20 spools (6 destructivos + 10 buffer + 4 edge cases)
- Script `generate_testing_data.py` implementado (440 líneas) para generación automática de datos
- 3 bugs críticos resueltos:
  1. ValidationService - Diferenciación estados EN_PROGRESO/COMPLETADO
  2. ActionService - Exception handling completo para errores business logic
  3. Test assertions - String matching corregido
- 3 archivos modificados: ValidationService, ActionService, Tests E2E
- 0 regresiones
- Coverage E2E completo: INICIAR/COMPLETAR ARM/SOLD, ownership, validaciones, errores

**✅ DÍA 4 FASE 2: DEPLOY RAILWAY (10-11 Nov 2025) - 100% COMPLETADO**
- **✅ Backend deployado y funcionando en producción**
- URL producción: https://zeues-backend-mvp-production.up.railway.app
- 6 endpoints API funcionando: health, workers, spools iniciar/completar, actions
- Health check: status=healthy, sheets_connection=ok
- Variables de entorno configuradas (6): GOOGLE_CLOUD_PROJECT_ID, GOOGLE_SHEET_ID, ENVIRONMENT, CACHE_TTL_SECONDS, ALLOWED_ORIGINS, GOOGLE_APPLICATION_CREDENTIALS_JSON
- Start Command configurado: uvicorn backend.main:app --host 0.0.0.0 --port $PORT
- Integración Google Sheets funcionando con Sheet de TESTING
- Problemas resueltos: Start command no detectado, credenciales desde env var (fix from_service_account_info)
- Archivos creados: Procfile, railway.json, .github/workflows/backend.yml, backend/README.md, DEPLOY-PRODUCTION.md
- Commits: 3 (railway config, auth fix, production docs)
- OpenAPI docs disponible en /api/docs

**Logros Arquitectónicos DÍA 2+3+4:**
- ✅ Ownership validation implementada y testeada: Solo quien inició puede completar (BC/BE validation)
- ✅ Clean Architecture mantenida: Services independientes, dependency injection completa
- ✅ 0 acceso directo Google Sheets: Todo via SheetsService/Repository abstraction
- ✅ Case-insensitive matching: Todos los nombres normalizan case/whitespace
- ✅ State validation: PENDIENTE → EN_PROGRESO → COMPLETADO
- ✅ Dependency validation: Secuencia obligatoria BA → BB → BD
- ✅ Logging comprehensivo: INFO/WARNING/ERROR con timestamps
- ✅ CORS configurado para desarrollo y producción
- ✅ **Tests E2E 10/10 passing: Backend 100% funcional y validado**
- ✅ **Dataset testing automatizado: Generación reproducible de datos de prueba**

**✅ BACKEND COMPLETADO - Backend 100% funcional en producción**
- URL: https://zeues-backend-mvp-production.up.railway.app
- 6 endpoints operativos con documentación OpenAPI
- Integración Google Sheets verificada
- Tests E2E 10/10 passing

**📋 Próximo: DÍA 4-5 Frontend - Integración API Real (11-12 Nov)**
- Crear /lib/api.ts con 6 funciones fetch
- Reemplazar mock data con llamadas API reales
- Testing flujos completos con backend deployado
- Manejo de errores y estados loading

### Frontend (Ver proyecto-frontend.md y proyecto-frontend-ui.md para detalles técnicos)

**✅ DÍA 1: Setup + Arquitectura (10 Nov 2025) - 100% COMPLETADO**
- Proyecto Next.js 14.2.33 creado y configurado
- 7 páginas placeholder con routing automático
- Tailwind CSS configurado con paleta ZEUES custom (#FF5B00, #0891B2, #16A34A)
- Estructura de carpetas completa (app/, components/, lib/)
- Variables de entorno configuradas (.env.local)
- Git repository inicializado (commit 05cb9d4)
- Build exitoso validado
- Dev server funcionando (puerto 3001)

**✅ DÍA 2: Componentes Base + Primeras Páginas (10 Nov 2025) - 100% COMPLETADO**
- 5 componentes base implementados: Button, Card, List, Loading, ErrorMessage
- P1 - Identificación implementada con mock data (4 trabajadores)
- P2 - Operación implementada (ARM/SOLD)
- P3 - Tipo Interacción implementada (INICIAR/COMPLETAR cyan/verde)
- Context API implementado (/lib/context.tsx)
- Layout.tsx con AppProvider
- Navegación P1→P2→P3 funcional
- Build sin errores

**✅ DÍA 3: Últimas Páginas + Mock Data (10 Nov 2025) - 100% COMPLETADO**
- P4 - Seleccionar Spool implementada con mock data (20 spools cubriendo todos escenarios)
- P5 - Confirmar Acción implementada con resumen y validaciones
- P6 - Éxito implementada con countdown 5seg y auto-redirect
- Filtrado inteligente de spools (iniciar vs completar, ARM vs SOLD)
- Validación de propiedad (ownership) en mock data
- Estados loading, error y empty correctamente manejados
- Suspense boundaries para useSearchParams() (Next.js 14 requirement)
- Build producción exitoso sin errores TypeScript/ESLint
- Guía testing E2E documentada (TESTING-E2E.md con 12 test cases)

**📋 Próximo: DÍA 4 - Integración API Real (11 Nov)**
- Crear /lib/api.ts con 6 funciones fetch
- Reemplazar mock data con API calls reales
- Integrar getWorkers(), getSpoolsParaIniciar(), getSpoolsParaCompletar()
- Implementar iniciarAccion() y completarAccion()
- Testing flujos completos con backend

**Estado Actual Frontend:**
- ✅ 60% completado (3/6 días - adelantado del timeline)
- ✅ 7 páginas completas con mock data
- ✅ 5 componentes reutilizables funcionando
- ✅ Context API simple implementado
- ✅ Build producción exitoso
- ⏳ Integración API real pendiente (DÍA 4-5)
- ⏳ Deploy Vercel pendiente (DÍA 6)
- **Documentación:** Ver `proyecto-frontend.md` (arquitectura) y `proyecto-frontend-ui.md` (componentes/páginas)
- **Testing:** Ver `zeues-frontend/TESTING-E2E.md` (12 test cases manuales)
- **Tecnologías:** Next.js 14.2.33 + TypeScript 5.4 + Tailwind CSS 3.4
- **Duración:** 6 días (10-15 Nov 2025) - DÍA 1-3 ✅ completados

### Hitos Completados

**Planificación y Diseño:**
- ✅ Especificación completa del MVP (proyecto.md)
- ✅ 27 preguntas críticas respondidas
- ✅ Lógica 2 interacciones (INICIAR/COMPLETAR) definida
- ✅ Historias de usuario (7 HU)
- ✅ Wireframes conceptuales (6 pantallas)
- ✅ Paleta de colores y principios UX

**Infraestructura:**
- ✅ Google Cloud Platform configurado
- ✅ Service Account creada y operativa
- ✅ Sheets TESTING y PRODUCCIÓN identificados
- ✅ Estructura columnas validada (9 críticas)
- ✅ Convención nombres estandarizada

**Backend Día 1:**
- ✅ Estructura proyecto backend (35 archivos definidos, 10 implementados)
- ✅ Modelos Pydantic completos (5 archivos)
- ✅ Repositorio Google Sheets funcional
- ✅ Tests pasando (4/4 exitosos)

**Documentación:**
- ✅ proyecto.md (vista producto/negocio)
- ✅ proyecto-backend.md (documentación técnica completa backend)
- ✅ GOOGLE-RESOURCES.md (configuración recursos)
- ✅ CLAUDE.md (guía desarrollo)

### Info Confirmada
**Técnico**: Google Sheets activo | Hoja "Operaciones" | Crear hoja "Trabajadores" | 292 spools | TAG_SPOOL col G único | ARM col V, SOLD col W | Metadata BC/BE (nombres), BB/BD (fechas) | Filtros V/W + BA/BB/BD + BC/BE
**Recursos Google**: Ver `GOOGLE-RESOURCES.md` para URLs y configuración completa
**Convención Columnas**: Palabra_Con_Mayusculas (estándar PascalCase con underscores) - Ver `ADMIN-configuracion-sheets.md`
**Estados**: 0=pendiente | 0.1=en progreso/iniciado | 1.0=completado
**Lógica NUEVA**:
- INICIAR ARM: V=0, BA llena, BB vacía → V→0.1, BC=nombre
- COMPLETAR ARM: V=0.1, BC=mi nombre → V→1.0, BB=fecha
- INICIAR SOLD: W=0, BB llena, BD vacía → W→0.1, BE=nombre
- COMPLETAR SOLD: W=0.1, BE=mi nombre → W→1.0, BD=fecha
- Restricción: Solo quien inició puede completar
**Usuarios**: 4 trabajadores (2 armadores + 2 soldadores) | Todos ven ARM y SOLD | Fijos, escalable a 12
**Hardware**: Tablet a adquirir (moderna Android/iPad) | Fija en planta | WiFi confiable | Sin kiosko MVP
**Volumen**: ~10 spools/día (~40 interacciones/día: INICIAR+COMPLETAR para ARM y SOLD), bajo, ideal MVP

### Recursos Google (Configurados 07 Nov 2025)

**Carpeta Drive**: https://drive.google.com/drive/u/0/folders/1QDlvt3OwGlYL1hClZVyZRdzIrz7qREGQ

**Google Sheets TESTING (para desarrollo MVP)**:
- URL: https://docs.google.com/spreadsheets/d/11v8fD5Shn0RSzDceZRvXhE9z4RIOBmPA9lpH5_zF-wM/edit?gid=1994081358#gid=1994081358
- ID: `11v8fD5Shn0RSzDceZRvXhE9z4RIOBmPA9lpH5_zF-wM`
- Uso: EXCLUSIVAMENTE para desarrollo y pruebas del MVP

**Google Sheets PRODUCCIÓN (NO usar hasta MVP 100% listo)**:
- URL: https://docs.google.com/spreadsheets/d/17iOaq2sv4mSOuJY4B8dGQIsWTTUKPspCtb7gk6u-MaQ/edit?gid=1994081358#gid=1994081358
- ID: `17iOaq2sv4mSOuJY4B8dGQIsWTTUKPspCtb7gk6u-MaQ`
- Uso: Solo cuando sistema esté completamente validado

📋 **NOMENCLATURA**:
- **Kronos** = Empresa/Cliente (Kronos Mining)
- **ZEUES** = Sistema de trazabilidad que estamos desarrollando
- Los archivos en Drive usan "Kronos" porque son del cliente, el sistema se llama ZEUES

Ver detalles completos en: `GOOGLE-RESOURCES.md`

### Próximos Pasos

**Timeline Actualizado:** Target 20 Nov 2025 (13 días desde inicio)

**📅 09 Nov (DÍA 2): Services + Validations - ✅ COMPLETADO**
- [x] ValidationService (restricción propiedad CRÍTICA) - 345 líneas, 24 tests
- [x] SheetsService (parseo filas → modelos) - 350 líneas, 29 tests
- [x] SpoolService (filtros INICIAR/COMPLETAR) - 243 líneas, 15 tests
- [x] WorkerService (CRUD trabajadores) - 134 líneas, 11 tests
- [x] ActionService (workflow completo INICIAR/COMPLETAR) - 484 líneas, 21 tests
- [x] Tests unitarios 95% coverage ActionService (objetivo >90% cumplido)
- [x] Total: 113 tests pasando, 0 regresiones

**📅 10 Nov (DÍA 3): API Endpoints + Integration - ✅ COMPLETADO**
- [x] 6 endpoints FastAPI implementados (health, workers, spools, actions)
- [x] Exception handlers completos (ZEUSException → HTTP codes)
- [x] Dependency injection integrada
- [x] Tests E2E flujos INICIAR/COMPLETAR (10 tests: 5 passing, 5 skipped esperando datos)
- [x] OpenAPI docs automático en /api/docs
- [x] Logging comprehensivo (INFO/WARNING/ERROR)
- [x] CORS configurado

**📅 10 Nov (DÍA 4 FASE 1): Testing Exhaustivo - ✅ COMPLETADO**
- [x] Dataset especializado generado (20 spools, script automático 440 líneas)
- [x] **✅ Tests E2E 10/10 passing (100% success rate) - OBJETIVO CUMPLIDO**
- [x] 3 bugs críticos resueltos (ValidationService, ActionService, test assertions)
- [x] 0 regresiones
- [x] Coverage E2E completo (INICIAR/COMPLETAR ARM/SOLD, ownership, errores)

**📅 10-11 Nov (DÍA 4 FASE 2): Backend Deploy - ✅ COMPLETADO**
- [x] Railway deployment exitoso
- [x] Env vars producción configuradas (6 variables)
- [x] Health check + logs funcionando
- [x] URL producción: https://zeues-backend-mvp-production.up.railway.app
- [x] Documentación README.md backend + DEPLOY-PRODUCTION.md

**📅 12-17 Nov: Frontend**
- [ ] 6 pantallas mobile-first
- [ ] Integración API backend
- [ ] 2 flujos completos navegables
- [ ] Loading/error states

**📅 18 Nov: Testing E2E**
- [ ] Tests tablet real
- [ ] Validación restricción propiedad
- [ ] Edge cases completos

**📅 19 Nov: Deploy Frontend**
- [ ] Vercel deployment
- [ ] Cambio a Sheet PRODUCCIÓN
- [ ] Testing prod completo

**📅 20 Nov: Launch MVP**
- [ ] Capacitación usuarios (4 trabajadores + 2 admins)
- [ ] Lanzamiento gradual
- [ ] Monitoreo día 1

**Bloqueadores Actuales:** ✅ NINGUNO
- ✅ **Bloqueante resuelto:** Datos de prueba en Sheets TESTING
  - Solución: Script `generate_testing_data.py` genera dataset especializado automáticamente
  - 20 spools con cobertura completa de escenarios
  - Datos regenerables para múltiples ejecuciones de tests
- ✅ **Bloqueante resuelto:** Backend deploy en Railway
  - Solución: Credenciales desde variable de entorno JSON, start command configurado manualmente
  - Backend funcionando en producción con health check OK
  - 6 endpoints API operativos

**Riesgo General:** 🟢 MUY BAJO - Backend 100% completado y deployado en producción, frontend 60% avanzado, integración API siguiente

---

## 15. Glosario

**Spool**: Unidad manufactura cañería (pieza tubería). Secuencia: Materiales → Armado → Soldadura
**TAG_SPOOL / CODIGO BARRA**: ID único spool, columna G, etiqueta física. Ej: "MK-1335-CW-25238-011". Sin patrón específico
**Operación**: Paso proceso manufactura. 10 posibles (ARM, SOLD, MET, NDT, REV, PINT, LIBER, DESP), MVP usa 2
**ARM**: Armado, col V. Valores: 0=pendiente | 0.1=iniciado | 1.0=completado
**SOLD**: Soldado, col W. Valores: 0=pendiente | 0.1=iniciado | 1.0=completado
**INICIAR**: Primera interacción, trabajador se asigna spool antes de trabajar físicamente (marca V/W→0.1, escribe nombre en BC/BE)
**COMPLETAR**: Segunda interacción, trabajador registra finalización trabajo físico (marca V/W→1.0, escribe fecha en BB/BD)
**Restricción Propiedad**: Solo quien INICIÓ (nombre en BC/BE) puede COMPLETAR esa acción
**Fecha_Materiales (BA)**: Col BA, requisito para INICIAR ARM
**Fecha_Armado (BB)**: Col BB, escrita auto al COMPLETAR ARM, requisito para INICIAR SOLD
**Armador (BC)**: Col BC, escrito al INICIAR ARM, usado para validar al COMPLETAR ARM
**Fecha_Soldadura (BD)**: Col BD, escrita auto al COMPLETAR SOLD
**Soldador (BE)**: Col BE, escrito al INICIAR SOLD, usado para validar al COMPLETAR SOLD
**Secuencia Obligatoria**: BA → BB → BD, spool no avanza sin completar anterior
**Spool Abandonado**: Spool marcado 0.1 (iniciado) pero nunca completado (valor 1.0). Solo admin resetea manualmente en Sheets
**Trabajador Planta**: Realiza ops físicas. 4 trabajadores (2 armadores + 2 soldadores), todos hacen ARM y SOLD
**Admin Plantilla**: Gestiona Google Sheets (fuente verdad). 2 admins, soporte nivel 1
**MVP**: Minimum Viable Product. Fecha objetivo: 17 Nov 2025
**Tablet Planta**: A adquirir, estación fija, acceso web
**Google Sheets API**: Integración programática con Sheets, único punto integración
**Service Account**: Cuenta Google Cloud para auth apps (no humanos)
**Mobile-First**: Diseño prioriza tablets, botones 60px+ para guantes
**plantilla.xlsx**: Excel referencia, copia hoja "Operaciones" (292 spools, 78 cols)
**Hoja "Operaciones"**: Principal en Sheets, contiene spools y estados, fuente verdad
**Hoja "Trabajadores"**: A crear en Sheets para gestión lista sin modificar código

---

## 16. Archivos del Proyecto

**Documentación Principal:**
- `proyecto.md` - Este archivo: especificación MVP (vista producto/negocio)
- `proyecto-backend.md` - Documentación técnica completa del backend
- `proyecto-frontend.md` - Documentación técnica completa del frontend
- `CLAUDE.md` - Guía para Claude Code sobre el proyecto

**Recursos Google:**
- `GOOGLE-RESOURCES.md` - URLs Drive/Sheets, configuración env vars, IDs
- `ADMIN-configuracion-sheets.md` - Guía administradores sobre estructura Sheets

**Backend:**
- `backend/` - Código fuente backend Python FastAPI (35 archivos)
- `tests/` - Suite de tests (unit, integration, e2e)
- `requirements.txt` - Dependencias Python backend
- `.env.local` - Variables de entorno desarrollo

**Frontend:**
- `frontend/` - Código fuente frontend Next.js (a crear)
- `frontend/app/` - Páginas Next.js (7 rutas)
- `frontend/components/` - Componentes React (Button, Card, List)
- `frontend/lib/` - API client, Context, types
- `package.json` - Dependencias frontend
- `.env.local` - Variables de entorno frontend (NEXT_PUBLIC_API_URL)

**Datos de Referencia:**
- `plantilla.xlsx` - Excel estructura original (292 spools, 78 columnas)
- `credenciales/` - Credenciales Google Service Account (NO en Git)

---

## 17. Anexos

### A. Ejemplo de Payloads API

**Ver `proyecto-backend.md` sección 7 para especificación completa backend.**
**Ver `proyecto-frontend.md` sección 5 para implementación completa API client frontend.**

**POST /api/iniciar-accion - Request:**
```json
{"worker_nombre": "Juan Pérez", "operacion": "ARM", "tag_spool": "MK-1335-CW-25238-011"}
```

**POST /api/iniciar-accion - Response 200 OK:**
```json
{
  "success": true,
  "message": "Acción ARM iniciada exitosamente. Spool asignado a Juan Pérez",
  "data": {
    "tag_spool": "MK-1335-CW-25238-011",
    "operacion": "ARM",
    "trabajador": "Juan Pérez",
    "fila_actualizada": 25,
    "columna_actualizada": "V",
    "valor_nuevo": 0.1,
    "metadata_actualizada": {"armador": "Juan Pérez"}
  }
}
```

**POST /api/completar-accion - Response 403 Error (Restricción Propiedad):**
```json
{
  "success": false,
  "error": "NO_AUTORIZADO",
  "message": "Solo Juan López puede completar ARM en 'MK-123' (él la inició). Tú eres Juan Pérez.",
  "data": {
    "tag_spool": "MK-123",
    "trabajador_esperado": "Juan López",
    "trabajador_solicitante": "Juan Pérez"
  }
}
```

### B. Variables de Entorno

**Ver `proyecto-backend.md` Apéndice D para configuración completa.**

**Variables Críticas (.env.local):**
```env
GOOGLE_CLOUD_PROJECT_ID=zeus-mvp
GOOGLE_SHEET_ID=11v8fD5Shn0RSzDceZRvXhE9z4RIOBmPA9lpH5_zF-wM  # TESTING
GOOGLE_SERVICE_ACCOUNT_EMAIL=zeus-mvp@zeus-mvp.iam.gserviceaccount.com
HOJA_OPERACIONES_NOMBRE=Operaciones
HOJA_TRABAJADORES_NOMBRE=Trabajadores
```

**Producción:** Cambiar `GOOGLE_SHEET_ID` a Sheet PRODUCCIÓN cuando MVP esté 100% validado.

### C. Comandos Útiles

**Backend:**
```bash
# Activar venv
source venv/bin/activate

# Tests
pytest tests/ -v

# Run backend local
uvicorn backend.main:app --reload --port 8000
```

**Frontend (cuando esté implementado):**
```bash
npm run dev       # Dev server
npm run build     # Build producción
npm run test      # Tests
```

---

**FIN - proyecto.md - ZEUES MVP - v3.5 - 11 Nov 2025**

**Cambios v3.5 (11 Nov 2025):**
- **BACKEND 100% COMPLETADO Y DEPLOYADO:** Railway deployment exitoso ✅
- **URL producción:** https://zeues-backend-mvp-production.up.railway.app
- **6 endpoints operativos:** health (OK), workers, spools, actions
- **Health check verificado:** status=healthy, sheets_connection=ok
- **3 problemas resueltos:** Start command, credenciales env var, deploys manuales
- **7 archivos nuevos:** Procfile, railway.json, workflows, README, DEPLOY-PRODUCTION.md
- **Modificaciones código:** config.py (get_credentials_dict), sheets_repository.py (from_service_account_info)
- **Estado:** Backend 100% funcional en producción, frontend 60% con mock data
- **Próximo:** Integración API real en frontend (DÍA 4-5)

**Cambios v3.4 (10 Nov 2025):**
- **DÍA 3 + DÍA 4 FASE 1 COMPLETADOS:** API Layer + Tests E2E 10/10 passing ✅
- **Dataset testing automatizado:** Script generador 440 líneas, 20 spools especializados
- **3 bugs críticos resueltos:** ValidationService, ActionService, test assertions
- **OpenAPI docs:** Documentación automática en /api/docs

**Cambios v3.3 (10 Nov 2025):**
- **DÍA 2 COMPLETADO AL 100%:** ActionService implementado y testeado ✅
- **113 tests totales pasando:** 21 nuevos ActionService + 92 previos (0 regresiones)
- **95% coverage ActionService:** Superando objetivo 90%
- **Workflow orchestration completo:** iniciar_accion() y completar_accion() con ownership validation ✅
- **Batch updates optimizados:** Múltiples celdas actualizadas en una operación
- **Archivos totales:** 22 de 35 implementados en backend

**Cambios v3.2 (09 Nov 2025):**
- **DÍA 2 FASE 1 COMPLETADO:** 3 Business Logic Services implementados ✅
- **92 tests totales pasando:** 50 nuevos services tests + 42 previos (100% success rate)
- **83% coverage total:** Superando objetivo 80%
- **Ownership validation implementada:** Solo quien inició puede completar (CRÍTICA) ✅
- **Archivos totales:** 20 de 35 implementados en backend

**Cambios v3.1 (09 Nov 2025):**
- **Bloqueantes resueltos:** Cache + Parser implementados y verificados
- **42 tests pasando:** 13 cache + 29 SheetsService (73% coverage)
- **-92% API calls verificado:** 4,800 → 372 calls/hora estimado
- **Estado actualizado:** DÍA 1 + Bloqueantes completados

**Cambios v3.0 (08 Nov 2025):**
- **Documentación separada:** Backend técnico movido a proyecto-backend.md
- **Backend Día 1 completado:** 10 archivos, 4 tests, conexión verificada
- **proyecto.md actualizado:** Enfoque en producto/negocio, referencias a proyecto-backend.md
- **Roadmap actualizado:** Timeline 13 días (target 20 Nov 2025)

**Cambios v2.2 (07 Nov 2025):**
- Setup Fase completada 100%
- Google Cloud Platform operativo
- Conexión Google Sheets verificada
- 0 errores bloqueantes

**Cambios v2.1 (07 Nov 2025):**
- Inicio oficial desarrollo
- Recursos Google configurados
- Documentación administrativa creada
