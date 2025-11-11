# Guía Práctica: Cómo Utilizar los Agentes de Desarrollo Backend

Esta guía te enseña paso a paso cómo trabajar con cada agente para desarrollar el backend de ZEUES.

---

## 📚 Tabla de Contenidos

1. [Conceptos Básicos](#conceptos-básicos)
2. [Cómo Invocar Agentes](#cómo-invocar-agentes)
3. [Guía por Agente](#guía-por-agente)
4. [Workflows Completos](#workflows-completos)
5. [Mejores Prácticas](#mejores-prácticas)
6. [Solución de Problemas](#solución-de-problemas)

---

## Conceptos Básicos

### ¿Qué es un Agente?

Un agente es un asistente especializado con:
- **Una responsabilidad única** - Hace una cosa y la hace bien
- **Contexto específico** - Conoce archivos clave del proyecto (@proyecto.md, @CLAUDE.md)
- **Coordinación** - Puede sugerir qué agente usar después
- **Expertise** - Tiene conocimiento profundo de su dominio

### ¿Cuándo Usar Agentes?

**USA agentes cuando:**
- Tienes una tarea compleja que requiere expertise específico
- Quieres separar responsabilidades claramente
- Necesitas mantener calidad y consistencia
- Quieres documentar quién hizo qué

**NO uses agentes cuando:**
- La tarea es trivial (ej: leer un archivo)
- Es más rápido hacerlo directamente
- No requiere expertise especializado

---

## Cómo Invocar Agentes

### Método 1: Mención Directa (Recomendado)

```
@nombre-agente [instrucción clara]
```

**Ejemplos:**
```
@backend-architect diseña la estructura del backend
@google-sheets-specialist implementa get_workers()
@api-tester crea tests para ValidationService
```

### Método 2: Solicitud Contextual

```
"Necesito [tarea]. ¿Qué agente debería usar?"
```

Claude Code te recomendará el agente apropiado.

### Método 3: Workflow Secuencial

```
@backend-architect diseña estructura
[espera resultado]
@google-sheets-specialist implementa SheetsService según diseño anterior
```

---

## Guía por Agente

---

## 1. backend-architect 🏗️

### ¿Cuándo Usarlo?

- **Antes** de empezar a codificar
- Al inicio de cada módulo nuevo
- Cuando necesites decisiones arquitectónicas
- Al refactorizar estructura

### ¿Qué NO Hace?

- No implementa código funcional (solo diseña)
- No escribe tests
- No se conecta a APIs

### Ejemplos de Uso

#### Ejemplo 1: Diseño Inicial Completo

```
Tú: @backend-architect diseña la estructura completa del backend para ZEUES

Agente Responde:
1. Lee @proyecto.md
2. Propone estructura:
   ```
   backend/
   ├── main.py
   ├── models/
   │   ├── __init__.py
   │   ├── schemas.py
   │   └── enums.py
   ├── services/
   │   ├── __init__.py
   │   ├── sheets_service.py
   │   ├── validation_service.py
   │   └── action_service.py
   ├── routers/
   │   ├── __init__.py
   │   ├── workers.py
   │   ├── spools.py
   │   └── actions.py
   ├── exceptions.py
   └── utils/
       └── logging.py
   ```
3. Define Pydantic models:
   ```python
   class Worker(BaseModel):
       worker_id: str
       nombre: str
       apellido: Optional[str]
       activo: bool = True

   class Spool(BaseModel):
       id: str
       tag_spool: str
       arm: float  # 0, 0.1, 1.0
       sold: float
       fecha_materiales: Optional[str]
       armador: Optional[str]
       ...
   ```
4. Justifica decisiones
5. Sugiere: "Siguiente: @google-sheets-specialist para implementar SheetsService"
```

#### Ejemplo 2: Diseñar Solo un Módulo

```
Tú: @backend-architect diseña solo la estructura de excepciones personalizadas

Agente:
- Propone jerarquía de excepciones
- Define ZEUSError como base
- Crea excepciones específicas (SpoolNoEncontradoError, etc.)
- NO implementa el código, solo diseña
```

#### Ejemplo 3: Validar Decisión Arquitectónica

```
Tú: @backend-architect ¿debería usar Repository Pattern o Service Layer?

Agente:
- Analiza pros/contras para ZEUES
- Considera: MVP, Google Sheets como única fuente, complejidad
- Recomienda: Service Layer (más simple para MVP)
- Justifica decisión
```

### Output Esperado

✅ Estructura de carpetas detallada
✅ Definición de modelos (Pydantic schemas)
✅ Interfaces entre componentes
✅ Justificación de decisiones
✅ Sugerencia de siguiente agente

### Señales de Éxito

- Tienes claridad de qué archivos crear
- Sabes qué modelos necesitas
- Entiendes cómo se comunicarán los componentes
- Tienes un plan antes de codificar

---

## 2. google-sheets-specialist 📊

### ¿Cuándo Usarlo?

- Para TODA operación con Google Sheets
- Al implementar SheetsService
- Cuando hay errores de integración con Sheets
- Para optimizar lecturas/escrituras

### ¿Qué NO Hace?

- No implementa lógica de negocio
- No crea endpoints
- No escribe tests (solo código de integración)

### Ejemplos de Uso

#### Ejemplo 1: Implementar SheetsService Completo

```
Tú: @google-sheets-specialist implementa SheetsService completo para ZEUES

Agente:
1. Activa venv: source venv/bin/activate
2. Lee @GOOGLE-RESOURCES.md para Sheet ID
3. Lee @proyecto.md columnas críticas (G, V, W, BA, BB, BC, BD, BE)
4. Implementa autenticación con Service Account
5. Crea métodos:
   ```python
   class SheetsService:
       def __init__(self):
           # Autenticación con credenciales/zeus-mvp-*.json

       def get_workers(self) -> List[Worker]:
           """Lee hoja 'Trabajadores'"""

       def get_spools_para_iniciar(self, action_type: ActionType) -> List[Spool]:
           """
           ARM: V=0, BA llena, BB vacía
           SOLD: W=0, BB llena, BD vacía
           """

       def update_iniciar_accion(self, tag_spool: str, action_type: ActionType, worker_name: str):
           """ARM: V→0.1, BC=nombre | SOLD: W→0.1, BE=nombre"""
   ```
6. Agrega reintentos y logging
7. Maneja errores (timeout, permisos, rate limit)
```

#### Ejemplo 2: Solo una Operación Específica

```
Tú: @google-sheets-specialist implementa solo get_spools_para_iniciar() para ARM

Agente:
- Implementa método específico
- Filtra: V=0, BA llena (!=None), BB vacía (==None)
- Agrega logging
- Manejo de errores
```

#### Ejemplo 3: Debugging de Error

```
Tú: @google-sheets-specialist estoy recibiendo error 403 al leer Sheets

Agente:
- Verifica credenciales en credenciales/
- Verifica que Sheet esté compartido con SA
- Verifica permisos (debe ser Editor)
- Propone solución paso a paso
```

#### Ejemplo 4: Optimización

```
Tú: @google-sheets-specialist get_spools() tarda 3 segundos, optimízalo

Agente:
- Analiza: múltiples llamadas GET
- Implementa batch read (leer hoja completa una vez)
- Filtrar en memoria (Python) en lugar de múltiples queries
- Mide mejora: 3s → 0.8s
```

### Output Esperado

✅ backend/services/sheets_service.py completo
✅ Autenticación configurada
✅ Métodos con reintentos y logging
✅ Manejo robusto de errores
✅ Mapeo de columnas a Pydantic models

### Señales de Éxito

- Puedes leer trabajadores de hoja "Trabajadores"
- Puedes filtrar spools según reglas de negocio
- Puedes actualizar V/W y metadata (BC/BE/BB/BD)
- Errores de API manejados correctamente

---

## 3. service-developer 🔧

### ¿Cuándo Usarlo?

- Para implementar lógica de negocio
- Al crear servicios (ValidationService, ActionService)
- Para validaciones complejas
- Para orquestación entre servicios

### ¿Qué NO Hace?

- No crea endpoints (eso es @api-builder)
- No accede directamente a Sheets (usa SheetsService)
- No escribe tests (eso es @api-tester)

### Ejemplos de Uso

#### Ejemplo 1: Implementar ValidationService

```
Tú: @service-developer implementa ValidationService completo

Agente:
1. Activa venv
2. Lee @proyecto.md "Lógica Filtrado (CRÍTICA)"
3. Implementa:
   ```python
   class ValidationService:
       def can_start_action(self, spool: Spool, action_type: ActionType) -> bool:
           """Valida si spool puede iniciar acción"""
           if action_type == ActionType.ARM:
               # V=0 (no iniciado)
               if spool.arm != 0:
                   return False
               # BA llena (materiales listos)
               if not spool.fecha_materiales:
                   return False
               # BB vacía (aún no armado)
               if spool.fecha_armado:
                   return False
               return True
           # ... lógica SOLD

       def can_complete_action(self, spool: Spool, action_type: ActionType, worker_name: str) -> bool:
           """Valida si trabajador puede completar"""
           if action_type == ActionType.ARM:
               # V=0.1 (en progreso)
               if spool.arm != 0.1:
                   return False
               # BC=worker_name (solo quien inició)
               if spool.armador != worker_name:
                   return False
               return True
   ```
4. Crea excepciones custom
5. Agrega logging
```

#### Ejemplo 2: Implementar ActionService

```
Tú: @service-developer implementa ActionService que orquesta validaciones y Sheets

Agente:
```python
class ActionService:
    def __init__(self, sheets_service: SheetsService, validation_service: ValidationService):
        self.sheets = sheets_service
        self.validator = validation_service

    def iniciar_accion(self, worker_nombre: str, operacion: str, tag_spool: str):
        # 1. Obtener spool
        spool = self.sheets.find_spool_by_tag(tag_spool)
        if not spool:
            raise SpoolNoEncontradoError(tag_spool)

        # 2. Validar
        action_type = ActionType[operacion]
        if not self.validator.can_start_action(spool, action_type):
            raise OperacionYaIniciadaError(tag_spool, operacion)

        # 3. Actualizar Sheets
        self.sheets.update_iniciar_accion(tag_spool, action_type, worker_nombre)

        # 4. Log
        logger.info(f"Acción iniciada: {worker_nombre} → {operacion} → {tag_spool}")

        return {"success": True, "message": "Acción iniciada"}
```
```

#### Ejemplo 3: Solo Validaciones Específicas

```
Tú: @service-developer implementa solo la validación de dependencias (BA→BB→BD)

Agente:
```python
def check_dependencies(self, spool: Spool, action_type: ActionType) -> bool:
    """Verifica secuencia obligatoria"""
    if action_type == ActionType.ARM:
        # Para ARM, requiere BA (materiales)
        if not spool.fecha_materiales:
            raise DependenciaNoSatisfechaError("ARM", "Materiales (BA)")
        return True

    elif action_type == ActionType.SOLD:
        # Para SOLD, requiere BB (armado completado)
        if not spool.fecha_armado:
            raise DependenciaNoSatisfechaError("SOLD", "Armado (BB)")
        return True
```
```

### Output Esperado

✅ Servicios con lógica de negocio pura
✅ Validaciones según proyecto.md
✅ Excepciones custom para errores
✅ Logging en operaciones críticas
✅ Orquestación entre servicios

### Señales de Éxito

- Validaciones funcionan según reglas de proyecto.md
- Servicios son testeables (lógica pura, sin dependencias HTTP)
- Excepciones claras para errores de negocio
- Logs informativos en cada operación

---

## 4. api-builder ⚡

### ¿Cuándo Usarlo?

- Para crear endpoints FastAPI
- Al definir routers
- Para schemas de request/response
- Para documentación OpenAPI

### ¿Qué NO Hace?

- No implementa lógica de negocio (delega a servicios)
- No se conecta directamente a Sheets
- No escribe tests

### Ejemplos de Uso

#### Ejemplo 1: Crear Endpoint POST /api/iniciar-accion

```
Tú: @api-builder crea el endpoint POST /api/iniciar-accion

Agente:
1. Activa venv
2. Lee @proyecto.md Anexo A para payload
3. Crea router backend/routers/actions.py:
   ```python
   from fastapi import APIRouter, Depends, HTTPException
   from pydantic import BaseModel

   router = APIRouter(prefix="/api", tags=["actions"])

   class IniciarAccionRequest(BaseModel):
       worker_nombre: str
       operacion: str  # "ARM" o "SOLD"
       tag_spool: str

   class IniciarAccionResponse(BaseModel):
       success: bool
       message: str
       data: dict

   @router.post("/iniciar-accion", response_model=IniciarAccionResponse)
   async def iniciar_accion(request: IniciarAccionRequest):
       """
       Inicia una acción (ARM o SOLD) para un spool.

       - **worker_nombre**: Nombre del trabajador
       - **operacion**: "ARM" o "SOLD"
       - **tag_spool**: Código del spool (ej: MK-1335-CW-25238-011)

       Actualiza Google Sheets:
       - ARM: V→0.1, BC=worker_nombre
       - SOLD: W→0.1, BE=worker_nombre
       """
       try:
           action_service = get_action_service()  # Dependency injection
           result = action_service.iniciar_accion(
               request.worker_nombre,
               request.operacion,
               request.tag_spool
           )
           return IniciarAccionResponse(success=True, message="Acción iniciada", data=result)
       except SpoolNoEncontradoError as e:
           raise HTTPException(status_code=404, detail=e.message)
       except OperacionYaIniciadaError as e:
           raise HTTPException(status_code=400, detail=e.message)
   ```
4. Configura en main.py:
   ```python
   from fastapi import FastAPI
   from routers import actions

   app = FastAPI(title="ZEUES API")
   app.include_router(actions.router)
   ```
```

#### Ejemplo 2: Crear Todos los Endpoints

```
Tú: @api-builder crea todos los 6 endpoints del backend

Agente:
- GET /api/workers
- GET /api/spools/iniciar?operacion=ARM
- GET /api/spools/completar?operacion=ARM&worker_nombre=Juan
- POST /api/iniciar-accion
- POST /api/completar-accion
- GET /api/health

Crea 3 routers: workers.py, spools.py, actions.py
Define schemas Pydantic para cada uno
Documenta con docstrings
Configura dependency injection
```

#### Ejemplo 3: Solo Schemas Pydantic

```
Tú: @api-builder define solo los schemas Pydantic para los endpoints

Agente:
- Crea backend/models/schemas.py
- Define: Worker, Spool, IniciarAccionRequest, CompletarAccionRequest, etc.
- Agrega validaciones con Pydantic
```

### Output Esperado

✅ Routers FastAPI organizados
✅ Schemas Pydantic con validaciones
✅ Documentación OpenAPI automática
✅ Dependency injection configurada
✅ Status codes apropiados

### Señales de Éxito

- Endpoints responden correctamente
- Swagger UI muestra documentación completa
- Validaciones Pydantic funcionan
- Errores retornan status codes correctos

---

## 5. api-tester 🧪

### ¿Cuándo Usarlo?

- Después de implementar servicios o endpoints
- Para validar reglas de negocio
- Para crear mocks de dependencias
- Para generar reportes de coverage

### ¿Qué NO Hace?

- No implementa funcionalidad
- No arregla bugs (solo los detecta)

### Ejemplos de Uso

#### Ejemplo 1: Tests para ValidationService

```
Tú: @api-tester crea tests completos para ValidationService

Agente:
1. Activa venv
2. Crea backend/tests/test_validation_service.py
3. Implementa fixtures:
   ```python
   import pytest
   from models.schemas import Spool
   from services.validation_service import ValidationService

   @pytest.fixture
   def validation_service():
       return ValidationService()

   @pytest.fixture
   def spool_listo_para_arm():
       return Spool(
           id="1",
           tag_spool="MK-TEST-001",
           arm=0,  # No iniciado
           sold=0,
           fecha_materiales="2025-11-01",  # Materiales listos
           fecha_armado=None,  # Aún no armado
           armador=None,
           fecha_soldadura=None,
           soldador=None
       )
   ```
4. Tests happy path:
   ```python
   def test_can_start_arm_with_valid_dependencies(validation_service, spool_listo_para_arm):
       """✅ Debe permitir iniciar ARM si V=0, BA llena, BB vacía"""
       result = validation_service.can_start_action(spool_listo_para_arm, ActionType.ARM)
       assert result is True
   ```
5. Tests edge cases:
   ```python
   def test_cannot_start_arm_already_started(validation_service):
       """❌ No debe permitir iniciar ARM si ya está en progreso (V=0.1)"""
       spool = Spool(..., arm=0.1, ...)
       result = validation_service.can_start_action(spool, ActionType.ARM)
       assert result is False

   def test_cannot_start_arm_without_materials(validation_service):
       """❌ No debe permitir iniciar ARM sin materiales (BA vacía)"""
       spool = Spool(..., fecha_materiales=None, ...)
       result = validation_service.can_start_action(spool, ActionType.ARM)
       assert result is False
   ```
6. Ejecuta: pytest -v backend/tests/test_validation_service.py
```

#### Ejemplo 2: Tests de Integración de Endpoints

```
Tú: @api-tester crea tests de integración para POST /api/iniciar-accion

Agente:
```python
from fastapi.testclient import TestClient
from main import app

client = TestClient(app)

def test_iniciar_accion_arm_success():
    """✅ Debe iniciar ARM exitosamente con datos válidos"""
    response = client.post("/api/iniciar-accion", json={
        "worker_nombre": "Juan Pérez",
        "operacion": "ARM",
        "tag_spool": "MK-TEST-001"
    })
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert "iniciada" in data["message"].lower()

def test_iniciar_accion_spool_not_found():
    """❌ Debe retornar 404 si spool no existe"""
    response = client.post("/api/iniciar-accion", json={
        "worker_nombre": "Juan Pérez",
        "operacion": "ARM",
        "tag_spool": "SPOOL-INEXISTENTE"
    })
    assert response.status_code == 404

def test_iniciar_accion_already_started():
    """❌ Debe retornar 400 si acción ya iniciada"""
    # ... test
```
```

#### Ejemplo 3: Mocks de Google Sheets

```
Tú: @api-tester crea mocks de SheetsService para tests unitarios

Agente:
```python
# backend/tests/conftest.py
import pytest
from unittest.mock import Mock

@pytest.fixture
def mock_sheets_service():
    mock = Mock()
    mock.get_workers.return_value = [
        Worker(worker_id="1", nombre="Juan", activo=True),
        Worker(worker_id="2", nombre="Pedro", activo=True)
    ]
    mock.find_spool_by_tag.return_value = Spool(...)
    return mock
```
```

### Output Esperado

✅ Suite de tests completa (test_*.py)
✅ Fixtures reutilizables
✅ Mocks de dependencias externas
✅ Tests de casos happy path y edge cases
✅ Reporte de coverage >80%

### Señales de Éxito

- Todos los tests pasan: `pytest -v`
- Coverage alto: `pytest --cov`
- Casos edge cubiertos
- Mocks funcionan correctamente

---

## 6. error-handler 🛡️

### ¿Cuándo Usarlo?

- Al inicio (definir excepciones base)
- Cuando encuentres errores no manejados
- Para mejorar mensajes de error
- Para implementar logging centralizado

### ¿Qué NO Hace?

- No implementa lógica de negocio
- No crea endpoints
- No arregla bugs de lógica

### Ejemplos de Uso

#### Ejemplo 1: Definir Excepciones Custom

```
Tú: @error-handler define todas las excepciones personalizadas del sistema

Agente:
Crea backend/exceptions.py:
```python
class ZEUSError(Exception):
    """Excepción base del sistema"""
    def __init__(self, message: str, error_code: str, status_code: int):
        self.message = message
        self.error_code = error_code
        self.status_code = status_code
        super().__init__(self.message)

class SpoolNoEncontradoError(ZEUSError):
    def __init__(self, tag_spool: str):
        super().__init__(
            message=f"Spool {tag_spool} no encontrado. Verifica el código.",
            error_code="SPOOL_NO_ENCONTRADO",
            status_code=404
        )

class NoAutorizadoError(ZEUSError):
    def __init__(self, trabajador_esperado: str, trabajador_solicitante: str):
        super().__init__(
            message=f"Solo {trabajador_esperado} puede completar esta acción (él la inició).",
            error_code="NO_AUTORIZADO",
            status_code=403
        )

# ... más excepciones
```
```

#### Ejemplo 2: Middleware de Manejo de Errores

```
Tú: @error-handler implementa middleware FastAPI para capturar excepciones

Agente:
```python
# backend/middleware/error_handler.py
from fastapi import Request
from fastapi.responses import JSONResponse

@app.exception_handler(ZEUSError)
async def zeus_error_handler(request: Request, exc: ZEUSError):
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "success": False,
            "error": exc.error_code,
            "message": exc.message,
            "data": {}
        }
    )

@app.exception_handler(Exception)
async def general_error_handler(request: Request, exc: Exception):
    logger.error(f"Error no manejado: {exc}")
    return JSONResponse(
        status_code=500,
        content={
            "success": False,
            "error": "INTERNAL_SERVER_ERROR",
            "message": "Error interno del servidor. Contacta al administrador.",
            "data": {}
        }
    )
```
```

#### Ejemplo 3: Logging Estructurado

```
Tú: @error-handler configura logging estructurado para todo el backend

Agente:
```python
# backend/utils/logging.py
import logging
import json
from datetime import datetime

class StructuredLogger:
    def __init__(self, name: str):
        self.logger = logging.getLogger(name)
        handler = logging.StreamHandler()
        handler.setFormatter(logging.Formatter('%(message)s'))
        self.logger.addHandler(handler)
        self.logger.setLevel(logging.INFO)

    def log_operation(self, operation: str, details: dict, level="info"):
        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "operation": operation,
            **details
        }
        getattr(self.logger, level)(json.dumps(log_entry))
```
```

### Output Esperado

✅ Jerarquía de excepciones completa
✅ Middleware de error handling
✅ Logging estructurado configurado
✅ Mensajes user-friendly
✅ Documentación de códigos de error

### Señales de Éxito

- Excepciones custom funcionan
- Mensajes de error claros para usuarios
- Logs estructurados y buscables
- Status codes HTTP correctos

---

## 7. performance-optimizer ⚡

### ¿Cuándo Usarlo?

- Cuando detectes lentitud (>1s API)
- Para implementar caching
- Para optimizar queries
- Antes de ir a producción

### ¿Qué NO Hace?

- No optimiza sin medir primero
- No sacrifica legibilidad por micro-optimizaciones

### Ejemplos de Uso

#### Ejemplo 1: Optimizar Endpoint Lento

```
Tú: @performance-optimizer GET /api/spools/iniciar tarda 4 segundos, optimízalo

Agente:
1. Activa venv
2. Mide tiempo actual:
   ```python
   import time
   start = time.time()
   # ... operación
   print(f"Tiempo: {time.time() - start}s")  # 4.2s
   ```
3. Profiling: identifica bottleneck → Google Sheets API (3.8s)
4. Implementa batch read:
   ```python
   # ANTES: Múltiples llamadas GET
   for spool in spools:
       sheet.get_row(spool.row_number)  # N llamadas

   # DESPUÉS: Una llamada batch
   all_rows = sheet.get_all_records()  # 1 llamada
   spools = [Spool.from_dict(row) for row in all_rows]
   ```
5. Implementa cache:
   ```python
   @lru_cache(maxsize=128)
   def get_spools_cached(ttl=300):  # 5 min TTL
       return sheets_service.get_all_spools()
   ```
6. Mide después: 0.8s (mejora 81%)
7. Documenta: "GET /spools/iniciar: 4.2s → 0.8s (81% mejora, batch+cache)"
```

#### Ejemplo 2: Implementar Cache General

```
Tú: @performance-optimizer implementa caching para workers y spools

Agente:
```python
# backend/services/cache_service.py
from functools import lru_cache
import time

class CacheService:
    def __init__(self, ttl_seconds=300):
        self.cache = {}
        self.ttl = ttl_seconds

    def get_or_fetch(self, key: str, fetch_fn):
        if key in self.cache:
            data, timestamp = self.cache[key]
            if time.time() - timestamp < self.ttl:
                return data

        # Cache miss, fetch
        data = fetch_fn()
        self.cache[key] = (data, time.time())
        return data

# Uso:
cache = CacheService(ttl_seconds=300)
workers = cache.get_or_fetch("workers", lambda: sheets_service.get_workers())
```
```

#### Ejemplo 3: Monitoreo de Performance

```
Tú: @performance-optimizer agrega monitoreo de tiempos a todas las operaciones críticas

Agente:
```python
# backend/utils/monitoring.py
from functools import wraps
import time

def measure_time(operation_name: str):
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            start = time.time()
            result = func(*args, **kwargs)
            elapsed = time.time() - start
            logger.info(f"⏱️ {operation_name}: {elapsed:.2f}s")

            if elapsed > 1.0:  # Alertar si >1s
                logger.warning(f"⚠️ Operación lenta: {operation_name} ({elapsed:.2f}s)")

            return result
        return wrapper
    return decorator

# Uso:
@measure_time("Filtrar spools para INICIAR ARM")
def get_spools_para_iniciar_arm():
    ...
```
```

### Output Esperado

✅ Mejoras de performance documentadas con métricas
✅ Cache implementado donde corresponde
✅ Batch operations en Sheets
✅ Monitoreo de tiempos
✅ Reporte de mejoras (antes/después)

### Señales de Éxito

- Endpoints responden <1s
- Logs muestran tiempos de operación
- Cache reduce llamadas a Sheets
- Métricas documentadas (ej: "mejora 75%")

---

## Workflows Completos

### Workflow 1: Implementar Backend Completo (3 días)

```bash
# DÍA 1: Diseño + Sheets + Validaciones

# 1. Diseño (30 min)
@backend-architect diseña la estructura completa del backend para ZEUES

# 2. Google Sheets (2 horas)
@google-sheets-specialist implementa SheetsService completo

# 3. Validaciones (2 horas)
@service-developer implementa ValidationService

# 4. Orquestación (1.5 horas)
@service-developer implementa ActionService


# DÍA 2: API + Tests

# 5. Endpoints (3 horas)
@api-builder crea todos los 6 endpoints del backend

# 6. Tests (3 horas)
@api-tester crea suite completa de tests (unitarios + integración)


# DÍA 3: Robustez + Optimización

# 7. Errores (2 horas)
@error-handler implementa manejo completo de errores y logging

# 8. Performance (2 horas, opcional)
@performance-optimizer mide y optimiza si hay lentitud

# 9. Actualización (15 min)
@project-architect actualiza proyecto.md con backend completado
```

### Workflow 2: Debugging de Problema Específico

```bash
# Problema: Endpoint POST /iniciar-accion retorna 500

# 1. Identificar causa
@error-handler analiza por qué POST /iniciar-accion retorna 500

# 2. Si es problema de Sheets
@google-sheets-specialist debuggea error de conexión con Sheets

# 3. Si es lógica de negocio
@service-developer debuggea ValidationService

# 4. Agregar tests
@api-tester crea test que reproduzca el error

# 5. Actualizar
@project-architect documenta el bug y la solución
```

### Workflow 3: Agregar Nueva Funcionalidad

```bash
# Tarea: Agregar endpoint GET /api/spools/en-progreso

# 1. Diseño
@backend-architect diseña endpoint y filtro necesario

# 2. Sheets
@google-sheets-specialist implementa get_spools_en_progreso() (V=0.1 o W=0.1)

# 3. Endpoint
@api-builder crea GET /api/spools/en-progreso

# 4. Tests
@api-tester crea tests para nuevo endpoint

# 5. Documentar
@project-architect actualiza proyecto.md con nueva funcionalidad
```

---

## Mejores Prácticas

### 1. Un Agente a la Vez

✅ **Correcto:**
```
@backend-architect diseña estructura
[espera resultado]
@google-sheets-specialist implementa SheetsService según diseño
```

❌ **Incorrecto:**
```
@backend-architect @google-sheets-specialist @api-builder háganlo todo
```

### 2. Instrucciones Claras y Específicas

✅ **Correcto:**
```
@api-builder crea el endpoint POST /api/iniciar-accion con validación Pydantic
```

❌ **Incorrecto:**
```
@api-builder haz algo con las acciones
```

### 3. Referencia a Documentación

✅ **Correcto:**
```
@service-developer implementa ValidationService según reglas de @proyecto.md sección "Lógica Filtrado"
```

### 4. Valida Outputs

Después de cada agente:
- ✅ Lee el código generado
- ✅ Verifica que siga las reglas de proyecto.md
- ✅ Prueba si es posible (ejecuta, compila)
- ✅ Ajusta si es necesario

### 5. Mantén Contexto

```
# Referencia a trabajo anterior
@api-builder crea endpoints que usen el ActionService implementado por @service-developer
```

### 6. Actualiza Estado

```
# Después de completar fase
@project-architect actualiza proyecto.md: backend completado, listo para frontend
```

---

## Solución de Problemas

### Problema: Agente no entiende contexto

**Solución:**
```
# Sé más específico, referencia archivos
@google-sheets-specialist lee @GOOGLE-RESOURCES.md y @proyecto.md antes de implementar
```

### Problema: Output no es lo que esperaba

**Solución:**
```
# Da feedback específico
@api-builder el endpoint debe retornar status 403 (no 401) para error de autorización según @proyecto.md Anexo A
```

### Problema: Agente sugiere tecnología incorrecta

**Solución:**
```
# Recuerda el stack
@service-developer usa Python + Pydantic (no TypeScript) según @CLAUDE.md
```

### Problema: Código no funciona

**Solución:**
```
# Pide tests primero
@api-tester crea test que valide [funcionalidad específica]
# Luego debuggea con agente apropiado
```

---

## Resumen: ¿Qué Agente Usar?

| Necesito... | Agente |
|-------------|--------|
| Diseñar estructura | @backend-architect |
| Integrar Google Sheets | @google-sheets-specialist |
| Lógica de negocio / validaciones | @service-developer |
| Crear endpoints FastAPI | @api-builder |
| Escribir tests | @api-tester |
| Manejar errores | @error-handler |
| Optimizar performance | @performance-optimizer |
| Actualizar proyecto.md | @project-architect |

---

## Próximo Paso

Ahora que sabes cómo usar los agentes, ¿quieres:

**A)** Practicar con un ejemplo real (implementar una parte del backend)
**B)** Empezar el desarrollo backend real usando los agentes
**C)** Hacer más preguntas sobre algún agente específico

¿Qué prefieres?
