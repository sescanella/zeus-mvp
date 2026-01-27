"""
Health Check Router - Monitoreo del estado del sistema.

Endpoint para verificar que la API está funcionando y que la conexión
con Google Sheets está operativa. Usado por Railway y monitoreo externo.

Endpoints:
- GET /api/health - Health check con test de conexión Sheets
- GET /api/redis-health - Health check con test de conexión Redis
"""

from fastapi import APIRouter, Depends, status
from datetime import datetime

from backend.core.dependency import get_sheets_repository
from backend.repositories.sheets_repository import SheetsRepository
from backend.repositories.redis_repository import RedisRepository
from backend.config import config
import logging

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/health", status_code=status.HTTP_200_OK)
async def health_check(
    sheets_repo: SheetsRepository = Depends(get_sheets_repository)
):
    """
    Health check endpoint para monitoreo del sistema.

    Verifica:
    - Estado general de la API (si responde, está "alive")
    - Conexión con Google Sheets (intenta leer hoja Trabajadores)

    Si Google Sheets falla, retorna status "degraded" en lugar de error 503.
    Esto permite que Railway/Monitoring vean que la API responde, pero con
    funcionalidad reducida.

    Args:
        sheets_repo: Repositorio de Google Sheets (inyectado automáticamente).

    Returns:
        Dict con:
        - status: "healthy" si todo OK, "degraded" si Sheets falla
        - timestamp: Timestamp UTC actual (ISO 8601 format)
        - environment: Ambiente de ejecución (development/production)
        - sheets_connection: "ok" si Sheets responde, "error" si falla
        - version: Versión de la API

    Raises:
        No lanza excepciones. Siempre retorna 200 OK con status apropiado.

    Example response (healthy):
        ```json
        {
            "status": "healthy",
            "timestamp": "2025-11-10T14:30:00Z",
            "environment": "development",
            "sheets_connection": "ok",
            "version": "1.0.0"
        }
        ```

    Example response (degraded):
        ```json
        {
            "status": "degraded",
            "timestamp": "2025-11-10T14:30:00Z",
            "environment": "development",
            "sheets_connection": "error",
            "version": "1.0.0"
        }
        ```

    Usage:
        ```bash
        curl http://localhost:8000/api/health
        ```

    Note:
        Railway usa este endpoint para health checks. Si retornara 503 en lugar
        de 200 con status="degraded", Railway consideraría la app como down y
        la reiniciaría innecesariamente.
    """
    logger.info("Health check requested")

    # Test conexión Google Sheets (intentar leer 1 fila de Trabajadores)
    sheets_status = "ok"
    try:
        # Leer hoja Trabajadores (usa cache si disponible)
        sheets_repo.read_worksheet(config.HOJA_TRABAJADORES_NOMBRE)
        logger.debug("Sheets connection test successful")
    except Exception as e:
        # Log error pero no propagarlo (retornar degraded en lugar de 503)
        logger.error(f"Health check failed: Sheets connection error - {str(e)}")
        sheets_status = "error"

    # Construir response
    return {
        "status": "healthy" if sheets_status == "ok" else "degraded",
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "environment": config.ENVIRONMENT,
        "sheets_connection": sheets_status,
        "version": "1.0.0"
    }


@router.get("/health/diagnostic", status_code=status.HTTP_200_OK)
async def diagnostic_check(
    sheets_repo: SheetsRepository = Depends(get_sheets_repository)
):
    """
    Diagnostic endpoint para troubleshooting de problemas de despliegue.

    Expone información útil sobre la configuración sin revelar credenciales:
    - GOOGLE_SHEET_ID parcialmente enmascarado
    - Lista de hojas disponibles en el spreadsheet
    - Si la hoja "Roles" existe
    - Cuántos roles hay en la hoja "Roles"

    Este endpoint es temporal y solo debe usarse para debugging.
    """
    logger.info("Diagnostic check requested")

    diagnostic_info = {
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "environment": config.ENVIRONMENT,
        "google_sheet_id_masked": f"{config.GOOGLE_SHEET_ID[:8]}...{config.GOOGLE_SHEET_ID[-8:]}",
        "config_sheet_names": {
            "operaciones": config.HOJA_OPERACIONES_NOMBRE,
            "trabajadores": config.HOJA_TRABAJADORES_NOMBRE,
            "metadata": config.HOJA_METADATA_NOMBRE,
        }
    }

    # Intentar listar hojas disponibles
    try:
        spreadsheet = sheets_repo._get_spreadsheet()
        all_worksheets = spreadsheet.worksheets()

        diagnostic_info["spreadsheet_title"] = spreadsheet.title
        diagnostic_info["available_sheets"] = [ws.title for ws in all_worksheets]
        diagnostic_info["total_sheets"] = len(all_worksheets)

        # Verificar si hoja "Roles" existe
        roles_sheet_exists = "Roles" in diagnostic_info["available_sheets"]
        diagnostic_info["roles_sheet_exists"] = roles_sheet_exists

        if roles_sheet_exists:
            try:
                roles_sheet = spreadsheet.worksheet("Roles")
                all_records = roles_sheet.get_all_records()
                diagnostic_info["roles_count"] = len(all_records)

                # Contar roles activos
                active_roles = [r for r in all_records if str(r.get('Activo', '')).upper() == 'TRUE']
                diagnostic_info["active_roles_count"] = len(active_roles)
            except Exception as e:
                diagnostic_info["roles_error"] = str(e)
        else:
            diagnostic_info["roles_count"] = 0
            diagnostic_info["active_roles_count"] = 0

    except Exception as e:
        diagnostic_info["error"] = str(e)
        diagnostic_info["error_type"] = type(e).__name__

    return diagnostic_info


@router.get("/redis-health", status_code=status.HTTP_200_OK)
async def redis_health():
    """
    Redis health check endpoint for monitoring Redis connection status.

    Checks:
    - If Redis client is connected
    - If Redis responds to PING command
    - Redis server info (version, clients, memory, uptime)

    Returns:
        Dict with:
        - status: "healthy" if connected and responding, "unhealthy" if not responding, "disconnected" if not connected
        - message: Human-readable status description
        - operational: Boolean indicating if Redis is operational
        - redis_version: Redis server version (if connected)
        - connected_clients: Number of connected clients (if connected)
        - used_memory_human: Human-readable memory usage (if connected)
        - uptime_in_seconds: Redis server uptime (if connected)

    Example response (healthy):
        ```json
        {
            "status": "healthy",
            "message": "Redis connected and responding",
            "operational": true,
            "redis_version": "7.2.3",
            "connected_clients": 5,
            "used_memory_human": "1.2M",
            "uptime_in_seconds": 86400
        }
        ```

    Example response (disconnected):
        ```json
        {
            "status": "disconnected",
            "message": "Redis client not connected",
            "operational": false
        }
        ```

    Usage:
        ```bash
        curl http://localhost:8000/api/redis-health
        ```
    """
    logger.info("Redis health check requested")

    redis_repo = RedisRepository()

    # Check if client is connected
    if redis_repo.client is None:
        logger.warning("Redis health check: client not connected")
        return {
            "status": "disconnected",
            "message": "Redis client not connected",
            "operational": False
        }

    # Perform health check with PING
    health_result = await redis_repo.health_check()

    if health_result["status"] == "healthy":
        # Get Redis info stats
        try:
            info = await redis_repo.get_info()
            logger.debug("Redis health check: healthy")
            return {
                "status": "healthy",
                "message": "Redis connected and responding",
                "operational": True,
                **info  # Include version, connected_clients, used_memory_human, uptime_in_seconds
            }
        except Exception as e:
            logger.warning(f"Redis health check: failed to get info - {e}")
            return {
                "status": "healthy",
                "message": "Redis connected and responding (info unavailable)",
                "operational": True
            }
    else:
        # Unhealthy - not responding to PING
        logger.warning(f"Redis health check: unhealthy - {health_result.get('error', 'unknown')}")
        return {
            "status": "unhealthy",
            "message": f"Redis not responding: {health_result.get('error', 'unknown')}",
            "operational": False
        }
