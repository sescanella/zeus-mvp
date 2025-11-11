"""
ZEUES API - Entry Point.

Sistema de Trazabilidad para Manufactura de Pipe Spools.
API REST con FastAPI para registro de acciones (Armado/Soldado) desde tablets.

Configuración:
- FastAPI app con OpenAPI docs automática
- CORS para frontend (localhost + Railway)
- Exception handlers para errores custom (ZEUSException)
- Logging comprehensivo
- Middleware de rate limiting (futuro)

Endpoints:
- GET  /               - Root endpoint (info API)
- GET  /api/docs       - OpenAPI documentation (Swagger UI)
- GET  /api/redoc      - OpenAPI documentation (ReDoc)
- GET  /api/health     - Health check (FASE 2)
- GET  /api/workers    - Lista trabajadores activos (FASE 2)
- GET  /api/spools/*   - Spools disponibles para iniciar/completar (FASE 2)
- POST /api/*-accion   - Iniciar/completar acciones de manufactura (FASE 3)

Ver proyecto-backend-api.md para especificaciones completas de endpoints.
"""

from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import logging

from backend.config import config
from backend.exceptions import ZEUSException
from backend.models.error import ErrorResponse
from backend.utils.logger import setup_logger

# FASE 2: Routers READ-ONLY implementados (health, workers, spools)
from backend.routers import health, workers, spools
# FASE 3: Router WRITE implementado (actions)
from backend.routers import actions


# ============================================================================
# INICIALIZACIÓN FASTAPI
# ============================================================================

app = FastAPI(
    title="ZEUES API",
    description="""
    API de trazabilidad para manufactura de pipe spools.

    ## Funcionalidades

    - **Trabajadores**: Listar trabajadores activos del sistema
    - **Spools**: Consultar spools disponibles para iniciar/completar acciones
    - **Acciones**: Iniciar y completar acciones de manufactura (Armado/Soldado)
    - **Health Check**: Monitoreo del estado del sistema y conexión Google Sheets

    ## Flujo de Trabajo

    1. **INICIAR ACCIÓN**: Trabajador selecciona operación (ARM/SOLD) y spool disponible
       - Sistema valida elegibilidad (estado PENDIENTE, dependencias satisfechas)
       - Actualiza Google Sheets: estado → 0.1 (EN_PROGRESO), trabajador → nombre
       - Spool queda asignado al trabajador

    2. **COMPLETAR ACCIÓN**: Trabajador selecciona operación y spool propio
       - Sistema valida ownership (solo quien inició puede completar) - **CRÍTICO**
       - Actualiza Google Sheets: estado → 1.0 (COMPLETADO), fecha → fecha actual
       - Acción queda registrada

    ## Restricción de Propiedad (CRÍTICA)

    Solo el trabajador que inició una acción puede completarla.
    Intentar completar una acción iniciada por otro trabajador retorna **403 FORBIDDEN**.

    ## Integración

    - **Google Sheets**: Fuente de verdad para spools y trabajadores
    - **Frontend**: React/Next.js (Vercel) → API (Railway) → Google Sheets
    - **Autenticación**: Service Account (zeus-mvp@zeus-mvp.iam.gserviceaccount.com)
    """,
    version="1.0.0",
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    contact={
        "name": "ZEUES Team",
        "email": "support@zeues.com"
    },
    license_info={
        "name": "Proprietary"
    }
)


# ============================================================================
# MIDDLEWARE - CORS
# ============================================================================

app.add_middleware(
    CORSMiddleware,
    allow_origins=config.ALLOWED_ORIGINS,  # Frontend URLs (local + production)
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"]
)


# ============================================================================
# EXCEPTION HANDLERS
# ============================================================================


@app.exception_handler(ZEUSException)
async def zeus_exception_handler(request: Request, exc: ZEUSException):
    """
    Handler global para todas las excepciones custom de ZEUES.

    Mapea ZEUSException.error_code → HTTP status code apropiado y
    retorna ErrorResponse consistente con el modelo de error estándar.

    Mapeo de error_code → HTTP status:
        - SPOOL_NO_ENCONTRADO, WORKER_NO_ENCONTRADO → 404 NOT FOUND
        - OPERACION_YA_INICIADA, OPERACION_YA_COMPLETADA,
          DEPENDENCIAS_NO_SATISFECHAS, OPERACION_NO_PENDIENTE,
          OPERACION_NO_INICIADA → 400 BAD REQUEST
        - NO_AUTORIZADO → 403 FORBIDDEN (CRÍTICO - ownership violation)
        - SHEETS_RATE_LIMIT → 429 TOO MANY REQUESTS
        - SHEETS_CONNECTION_ERROR, SHEETS_UPDATE_ERROR → 503 SERVICE UNAVAILABLE

    Logging según severidad:
        - 500+: ERROR con stack trace
        - 403: WARNING (auditoría crítica de ownership violations)
        - 400: INFO (errores cliente esperados)

    Args:
        request: Request de FastAPI
        exc: Excepción ZEUSException capturada

    Returns:
        JSONResponse con ErrorResponse y HTTP status code apropiado
    """
    # Mapeo de error_code → HTTP status
    status_map = {
        # 404 NOT FOUND
        "SPOOL_NO_ENCONTRADO": status.HTTP_404_NOT_FOUND,
        "WORKER_NO_ENCONTRADO": status.HTTP_404_NOT_FOUND,

        # 400 BAD REQUEST
        "OPERACION_YA_INICIADA": status.HTTP_400_BAD_REQUEST,
        "OPERACION_YA_COMPLETADA": status.HTTP_400_BAD_REQUEST,
        "DEPENDENCIAS_NO_SATISFECHAS": status.HTTP_400_BAD_REQUEST,
        "OPERACION_NO_PENDIENTE": status.HTTP_400_BAD_REQUEST,
        "OPERACION_NO_INICIADA": status.HTTP_400_BAD_REQUEST,

        # 403 FORBIDDEN (CRÍTICO - ownership violation)
        "NO_AUTORIZADO": status.HTTP_403_FORBIDDEN,

        # 429 TOO MANY REQUESTS
        "SHEETS_RATE_LIMIT": status.HTTP_429_TOO_MANY_REQUESTS,

        # 503 SERVICE UNAVAILABLE
        "SHEETS_CONNECTION_ERROR": status.HTTP_503_SERVICE_UNAVAILABLE,
        "SHEETS_UPDATE_ERROR": status.HTTP_503_SERVICE_UNAVAILABLE
    }

    http_status = status_map.get(exc.error_code, status.HTTP_500_INTERNAL_SERVER_ERROR)

    # Construir ErrorResponse
    error_response = ErrorResponse(
        success=False,
        error=exc.error_code,
        message=exc.message,
        data=exc.data if exc.data else None
    )

    # Log según severidad
    if http_status >= 500:
        logging.error(f"Server error: {exc.message}", exc_info=True)
    elif http_status == 403:
        # CRÍTICO: Ownership violation - log como WARNING para auditoría
        logging.warning(f"Forbidden: {exc.message}")
    else:
        logging.info(f"Client error: {exc.message}")

    return JSONResponse(
        status_code=http_status,
        content=error_response.model_dump()
    )


@app.exception_handler(Exception)
async def generic_exception_handler(request: Request, exc: Exception):
    """
    Handler para excepciones no manejadas (fallback).

    Captura cualquier excepción que no sea ZEUSException y la convierte
    en un error 500 con mensaje genérico.

    En desarrollo (ENVIRONMENT=local): Incluye detalles del error en data
    En producción: Solo mensaje genérico (no exponer detalles internos)

    Args:
        request: Request de FastAPI
        exc: Excepción genérica capturada

    Returns:
        JSONResponse con ErrorResponse y HTTP 500
    """
    logging.error(f"Unhandled exception: {str(exc)}", exc_info=True)

    error_response = ErrorResponse(
        success=False,
        error="INTERNAL_SERVER_ERROR",
        message="Error interno del servidor. Contacta al administrador.",
        data={"detail": str(exc)} if config.ENVIRONMENT == "local" else None
    )

    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content=error_response.model_dump()
    )


# ============================================================================
# STARTUP/SHUTDOWN EVENTS
# ============================================================================


@app.on_event("startup")
async def startup_event():
    """
    Configurar sistema al iniciar app.

    Acciones:
    - Configurar logging con setup_logger()
    - Log de información del ambiente
    - Log de configuración Google Sheets
    - Validar variables de entorno (futuro)
    """
    setup_logger()
    logging.info("✅ ZEUES API iniciada correctamente")
    logging.info(f"Environment: {config.ENVIRONMENT}")
    logging.info(f"Google Sheet ID: {config.GOOGLE_SHEET_ID[:10]}...{config.GOOGLE_SHEET_ID[-10:]}")
    logging.info(f"CORS Origins: {config.ALLOWED_ORIGINS}")


@app.on_event("shutdown")
async def shutdown_event():
    """
    Limpieza al apagar app.

    Acciones:
    - Log de shutdown
    - Cerrar conexiones pendientes (futuro)
    - Flush de cache (futuro)
    """
    logging.info("🔴 ZEUES API shutting down...")


# ============================================================================
# ROUTERS
# ============================================================================

# FASE 2: Routers READ-ONLY registrados
app.include_router(health.router, prefix="/api", tags=["Health"])
app.include_router(workers.router, prefix="/api", tags=["Workers"])
app.include_router(spools.router, prefix="/api", tags=["Spools"])

# FASE 3: Router WRITE registrado (CRÍTICO - ownership validation)
app.include_router(actions.router, prefix="/api", tags=["Actions"])


# ============================================================================
# ROOT ENDPOINT
# ============================================================================


@app.get("/", tags=["Root"])
async def root():
    """
    Root endpoint - Información básica de la API.

    Retorna metadata sobre la API y enlaces a documentación.
    Útil para verificar que la API está funcionando.

    Returns:
        Dict con información básica de la API:
        - message: Descripción corta del sistema
        - version: Versión de la API
        - docs: URL de documentación OpenAPI (Swagger UI)
        - redoc: URL de documentación ReDoc
        - health: URL de health check (futuro)

    Example response:
        ```json
        {
            "message": "ZEUES API - Manufacturing Traceability System",
            "version": "1.0.0",
            "docs": "/api/docs",
            "redoc": "/api/redoc",
            "health": "/api/health"
        }
        ```
    """
    return {
        "message": "ZEUES API - Manufacturing Traceability System",
        "version": "1.0.0",
        "docs": "/api/docs",
        "redoc": "/api/redoc",
        "health": "/api/health"
    }
