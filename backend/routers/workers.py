"""
Workers Router - Gestión de trabajadores.

Endpoint para listar trabajadores activos del sistema.
Frontend usa esta lista para dropdowns de selección de trabajador.

Endpoints:
- GET /api/workers - Lista trabajadores activos
"""

from fastapi import APIRouter, Depends, status

from backend.core.dependency import get_worker_service
from backend.services.worker_service import WorkerService
from backend.models.worker import WorkerListResponse
import logging

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/workers", response_model=WorkerListResponse, status_code=status.HTTP_200_OK)
async def get_workers(
    worker_service: WorkerService = Depends(get_worker_service)
):
    """
    Lista todos los trabajadores activos del sistema.

    Retorna solo trabajadores con activo=True de la hoja Trabajadores en
    Google Sheets. Frontend usa esta lista para dropdowns de selección
    cuando un trabajador necesita identificarse.

    El filtrado de trabajadores activos se realiza en WorkerService, no en
    el router. Esto mantiene la separación de responsabilidades.

    Args:
        worker_service: Servicio de trabajadores (inyectado automáticamente).

    Returns:
        WorkerListResponse con:
        - workers: Lista de objetos Worker (nombre, apellido, activo)
        - total: Cantidad de trabajadores activos

    Raises:
        HTTPException 503: Si falla conexión con Google Sheets.
                           Manejado automáticamente por exception handler en main.py.

    Example request:
        ```bash
        curl http://localhost:8000/api/workers
        ```

    Example response (200 OK):
        ```json
        {
            "workers": [
                {
                    "nombre": "Juan",
                    "apellido": "Pérez",
                    "activo": true
                },
                {
                    "nombre": "María",
                    "apellido": "González",
                    "activo": true
                }
            ],
            "total": 2
        }
        ```

    Example response (503 - Sheets error):
        ```json
        {
            "success": false,
            "error": "SHEETS_CONNECTION_ERROR",
            "message": "Error al conectar con Google Sheets: Authentication failed"
        }
        ```

    Note:
        - Si no hay trabajadores activos, retorna lista vacía (NO es error)
        - Trabajadores con activo=False no aparecen en la respuesta
        - Cache se aplica en SheetsRepository (TTL 5 min para Trabajadores)
    """
    logger.info("GET /api/workers - Listing active workers")

    # Obtener trabajadores activos del servicio
    workers = worker_service.get_all_active_workers()

    logger.info(f"Found {len(workers)} active workers")

    # Construir response
    return WorkerListResponse(
        workers=workers,
        total=len(workers)
    )
