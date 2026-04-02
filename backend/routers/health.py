"""
Health Check Router - Monitoreo del estado del sistema.

Endpoint para verificar que la API está funcionando y que la conexión
con Google Sheets está operativa. Usado por Railway y monitoreo externo.

Endpoints:
- GET /api/health - Health check con test de conexión Sheets

Note: Single-user mode - No Redis health check needed.
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

    Simplified for single-user mode: Only checks Google Sheets.

    Verifica:
    - Estado general de la API (si responde, está "alive")
    - Conexión con Google Sheets (intenta leer hoja Trabajadores)

    Status logic:
    - "healthy": Sheets OK
    - "unhealthy": Sheets FAIL (core features unavailable)

    Args:
        sheets_repo: Repositorio de Google Sheets (inyectado automáticamente).

    Returns:
        Dict con:
        - status: "healthy" or "unhealthy"
        - operational: Boolean indicating if core features work
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
            "operational": true,
            "timestamp": "2026-02-04T14:30:00Z",
            "environment": "production",
            "sheets_connection": "ok",
            "version": "4.0.0-single-user"
        }
        ```

    Usage:
        ```bash
        curl http://localhost:8000/api/health
        ```
    """
    logger.info("Health check requested (single-user mode)")

    # Test conexión Google Sheets (intentar leer 1 fila de Trabajadores)
    sheets_status = "ok"
    sheets_error = None
    try:
        sheets_repo.read_worksheet(config.HOJA_TRABAJADORES_NOMBRE)
        logger.debug("Sheets connection test successful")
    except Exception as e:
        logger.error(f"Health check failed: Sheets connection error - {str(e)}")
        sheets_status = "error"
        sheets_error = str(e)

    # Determine overall status (simplified: only Sheets matters)
    if sheets_status == "ok":
        status_value = "healthy"
        operational = True
    else:
        status_value = "unhealthy"
        operational = False

    # Construir response
    response = {
        "status": status_value,
        "operational": operational,
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "environment": config.ENVIRONMENT,
        "sheets_connection": sheets_status,
        "version": "4.0.0-single-user"
    }

    # Add error details if present
    if sheets_error:
        response["details"] = {"sheets_error": sheets_error}

    return response


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




