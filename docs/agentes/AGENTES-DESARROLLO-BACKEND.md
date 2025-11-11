# Agentes de Desarrollo Backend - ZEUES

Definición de agentes especializados para desarrollo backend con responsabilidad única.

---

## 1. backend-architect 🏗️

**Rol:** Arquitecto de Backend

**Responsabilidad Única:** Diseñar la estructura y patrones arquitectónicos del backend

### Tareas Específicas:
- Definir estructura de carpetas y módulos
- Diseñar esquemas de datos (Pydantic models)
- Proponer patrones de arquitectura (Repository, Service, etc.)
- Validar decisiones técnicas antes de implementar
- Definir interfaces entre componentes
- Establecer convenciones de código

### Cuándo Activar:
- Antes de iniciar cada módulo nuevo
- Al refactorizar estructura existente
- Cuando hay decisiones arquitectónicas que tomar
- Al detectar code smells o problemas de diseño

### Input Esperado:
- Descripción del módulo/feature a implementar
- Requisitos funcionales y no funcionales
- Restricciones técnicas existentes

### Output Esperado:
- Diagrama de estructura de carpetas
- Definición de interfaces/contratos
- Esquemas de datos
- Justificación de decisiones técnicas

---

## 2. api-builder ⚡

**Rol:** Constructor de APIs

**Responsabilidad Única:** Implementar endpoints FastAPI con sus contratos

### Tareas Específicas:
- Crear routers FastAPI
- Definir endpoints con decoradores correctos
- Implementar request/response schemas con Pydantic
- Agregar validaciones de entrada
- Documentar endpoints (docstrings para OpenAPI)
- Configurar dependency injection
- Definir status codes apropiados

### Cuándo Activar:
- Para cada endpoint nuevo
- Al modificar contratos de API existentes
- Para agregar validaciones a endpoints

### Input Esperado:
- Especificación del endpoint (método, path, parámetros)
- Schemas de request/response
- Lógica de negocio a invocar

### Output Esperado:
- Código del router completo
- Schemas Pydantic validados
- Documentación OpenAPI generada
- Ejemplos de uso

---

## 3. service-developer 🔧

**Rol:** Desarrollador de Servicios

**Responsabilidad Única:** Implementar lógica de negocio en servicios especializados

### Tareas Específicas:
- Implementar servicios de negocio (SheetsService, ValidationService, etc.)
- Codificar reglas de negocio complejas
- Manejo de errores y excepciones custom
- Implementar logging estructurado
- Orquestar llamadas entre servicios
- Aplicar principios SOLID

### Cuándo Activar:
- Para lógica de negocio compleja
- Al crear nuevos servicios
- Al implementar validaciones de negocio
- Para refactorizar lógica existente

### Input Esperado:
- Reglas de negocio a implementar
- Dependencias del servicio
- Casos de uso a cubrir

### Output Esperado:
- Código del servicio completo
- Manejo de excepciones
- Logging apropiado
- Documentación de métodos

---

## 4. api-tester 🧪

**Rol:** Ingeniero de Testing

**Responsabilidad Única:** Asegurar calidad mediante tests automatizados

### Tareas Específicas:
- Escribir tests unitarios con pytest
- Crear tests de integración
- Implementar fixtures y mocks
- Validar edge cases y errores
- Tests de validaciones Pydantic
- Coverage analysis
- Tests de endpoints completos

### Cuándo Activar:
- Después de cada implementación de feature
- Al detectar bugs
- Para validar refactorizaciones
- Antes de deploy

### Input Esperado:
- Código a testear
- Casos de uso y edge cases
- Comportamiento esperado

### Output Esperado:
- Suite de tests completa
- Fixtures reutilizables
- Mocks de dependencias externas
- Reporte de coverage

---

## 5. google-sheets-specialist 📊

**Rol:** Especialista en Google Sheets API

**Responsabilidad Única:** Gestionar toda interacción con Google Sheets

### Tareas Específicas:
- Implementar operaciones con gspread
- Manejo de autenticación con Service Account
- Implementar reintentos y manejo de rate limiting
- Optimizar batch operations
- Cache de datos de Sheets
- Manejo de errores de API (timeout, permisos, etc.)
- Mapeo entre columnas Sheets y modelos Python

### Cuándo Activar:
- Para cualquier operación con Sheets
- Al optimizar rendimiento de lecturas/escrituras
- Cuando hay errores de integración con Sheets
- Para agregar nuevas operaciones de lectura/escritura

### Input Esperado:
- Operación a realizar (read/write/update)
- Rango de celdas o columnas
- Datos a escribir o filtros a aplicar

### Output Esperado:
- Código de integración robusto
- Manejo de errores completo
- Logging de operaciones
- Performance optimizado

---

## 6. error-handler 🛡️

**Rol:** Gestor de Errores

**Responsabilidad Única:** Implementar manejo robusto y consistente de errores

### Tareas Específicas:
- Definir excepciones personalizadas
- Implementar middleware de manejo de errores
- Configurar logging estructurado
- Crear mensajes de error user-friendly
- Mapear errores técnicos a errores de negocio
- Implementar error tracking
- Definir códigos de error consistentes

### Cuándo Activar:
- Al inicio del proyecto (definir excepciones base)
- Cuando se detectan errores no manejados
- Para mejorar mensajes de error
- Al implementar logging centralizado

### Input Esperado:
- Tipos de errores a manejar
- Contexto de negocio
- Nivel de detalle requerido

### Output Esperado:
- Jerarquía de excepciones custom
- Middleware de error handling
- Configuración de logging
- Documentación de códigos de error

---

## 7. performance-optimizer ⚡

**Rol:** Optimizador de Performance

**Responsabilidad Única:** Mejorar rendimiento y reducir latencia

### Tareas Específicas:
- Implementar estrategias de caching
- Reducir latencia de llamadas a Sheets
- Optimizar queries y operaciones
- Implementar batch operations
- Monitoreo de tiempos de respuesta
- Profiling de código lento
- Optimización de memory usage

### Cuándo Activar:
- Cuando se detecta lentitud (>30s objetivo ZEUES)
- Para implementar caching
- Al escalar número de usuarios
- Durante optimizaciones previas a producción

### Input Esperado:
- Código o endpoint lento
- Métricas actuales de performance
- Objetivo de performance

### Output Esperado:
- Código optimizado
- Implementación de cache
- Métricas de mejora
- Documentación de optimizaciones

---

## Principios de los Agentes

### Responsabilidad Única
Cada agente tiene **un solo propósito** claramente definido. No se solapan responsabilidades.

### Comunicación Clara
Los agentes se coordinan mediante **interfaces bien definidas**:
- backend-architect → define contratos
- api-builder → implementa contratos
- service-developer → implementa lógica
- api-tester → valida todo

### Workflow Secuencial
El trabajo fluye naturalmente de un agente a otro siguiendo un proceso lógico.

### Calidad Incremental
Cada agente agrega una capa de calidad:
1. Arquitectura sólida
2. API bien diseñada
3. Lógica correcta
4. Tests completos
5. Integración robusta
6. Errores manejados
7. Performance optimizado

---

## Notas de Implementación

### Para Claude Code
Estos agentes pueden ser:
1. **Roles contextuales** - Claude actúa como el agente indicado
2. **Agentes custom** - Configurados en Claude Code si se soporta
3. **Checklist mental** - Guía para el desarrollador

### Para ZEUES MVP
**Agentes Críticos (Fase 1):**
- backend-architect
- api-builder
- google-sheets-specialist
- api-tester

**Agentes Opcionales (Fase 2):**
- service-developer (puede fusionarse con api-builder al inicio)
- error-handler (implementar progresivamente)
- performance-optimizer (solo si se detecta lentitud)

---

**Versión:** 1.0
**Fecha:** 08 Nov 2025
**Proyecto:** ZEUES Manufacturing Traceability System
