"""
Health Check Router - Monitoreo del estado del sistema.

Endpoint para verificar que la API está funcionando y que la conexión
con Google Sheets está operativa. Usado por Railway y monitoreo externo.

Endpoints:
- GET /api/health - Health check con test de conexión Sheets
"""

from fastapi import APIRouter, Depends, status
from datetime import datetime

from backend.core.dependency import get_sheets_repository
from backend.repositories.sheets_repository import SheetsRepository
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
