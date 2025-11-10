"""
Actions Router - Manufacturing action write operations.

CRITICAL endpoints for starting and completing manufacturing actions (ARM/SOLD).
Delegates all business logic to ActionService. Exception handlers in main.py
automatically map ZEUSException subclasses to appropriate HTTP status codes.

Key features:
- POST /api/iniciar-accion: Start action (assign spool to worker)
- POST /api/completar-accion: Complete action (OWNERSHIP VALIDATION - CRITICAL)

Ownership restriction: Only the worker who started an action can complete it.
Attempting to complete another worker's action → 403 FORBIDDEN.
"""

from fastapi import APIRouter, Depends, status
from backend.core.dependency import get_action_service
from backend.services.action_service import ActionService
from backend.models.action import ActionRequest, ActionResponse
from backend.models.enums import ActionType
import logging

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post("/iniciar-accion", response_model=ActionResponse, status_code=status.HTTP_200_OK)
async def iniciar_accion(
    request: ActionRequest,
    action_service: ActionService = Depends(get_action_service)
):
    """
    Inicia una acción de manufactura (Armado o Soldado) en un spool.

    Asigna el spool al trabajador y marca la acción como iniciada (0.1).
    Actualiza Google Sheets en batch (2 celdas: estado + trabajador).

    Validaciones:
    - Trabajador existe y está activo
    - Spool existe en hoja Operaciones
    - Operación está en estado PENDIENTE (V/W=0)
    - Dependencias satisfechas (BA llena para ARM, BB llena para SOLD)
    - Fecha de completado vacía (BB vacía para ARM, BD vacía para SOLD)

    Actualizaciones Sheets:
    - ARM: V→0.1 (col 22), BC=worker_nombre (col 55)
    - SOLD: W→0.1 (col 23), BE=worker_nombre (col 57)

    Args:
        request: Datos de la acción a iniciar (worker_nombre, operacion, tag_spool)
        action_service: Servicio de acciones (inyectado)

    Returns:
        ActionResponse con success=True y metadata de la operación

    Raises:
        HTTPException 404: Si trabajador o spool no encontrado
        HTTPException 400: Si operación ya iniciada/completada o dependencias no satisfechas
        HTTPException 503: Si falla actualización Google Sheets

    Example request:
        ```json
        {
            "worker_nombre": "Juan Pérez",
            "operacion": "ARM",
            "tag_spool": "MK-1335-CW-25238-011"
        }
        ```

    Example response:
        ```json
        {
            "success": true,
            "message": "Acción ARM iniciada exitosamente. Spool MK-1335-CW-25238-011 asignado a Juan Pérez",
            "data": {
                "tag_spool": "MK-1335-CW-25238-011",
                "operacion": "ARM",
                "trabajador": "Juan Pérez",
                "fila_actualizada": 25,
                "columna_actualizada": "V",
                "valor_nuevo": 0.1,
                "metadata_actualizada": {
                    "armador": "Juan Pérez",
                    "soldador": null,
                    "fecha_armado": null,
                    "fecha_soldadura": null
                }
            }
        }
        ```
    """
    logger.info(
        f"POST /api/iniciar-accion - worker={request.worker_nombre}, "
        f"operacion={request.operacion}, tag_spool={request.tag_spool}"
    )

    # Delegar a ActionService (orchestrator)
    # Todas las validaciones se realizan en ActionService
    # Excepciones se propagan automáticamente al exception handler
    response = action_service.iniciar_accion(
        worker_nombre=request.worker_nombre,
        operacion=request.operacion,
        tag_spool=request.tag_spool
    )

    logger.info(
        f"Action started successfully - {request.operacion} on {request.tag_spool} "
        f"by {request.worker_nombre}"
    )

    return response


@router.post("/completar-accion", response_model=ActionResponse, status_code=status.HTTP_200_OK)
async def completar_accion(
    request: ActionRequest,
    action_service: ActionService = Depends(get_action_service)
):
    """
    Completa una acción de manufactura (Armado o Soldado) en un spool.

    Registra la fecha de finalización y marca la acción como completada (1.0).
    CRÍTICO: Valida ownership - solo quien inició puede completar (BC/BE check).

    Validaciones:
    - Trabajador existe y está activo
    - Spool existe en hoja Operaciones
    - Operación está en estado EN_PROGRESO (V/W=0.1)
    - **OWNERSHIP: BC/BE = worker_nombre (solo quien inició puede completar)**

    Actualizaciones Sheets:
    - ARM: V→1.0 (col 22), BB=fecha (col 54, formato DD/MM/YYYY)
    - SOLD: W→1.0 (col 23), BD=fecha (col 56, formato DD/MM/YYYY)

    Args:
        request: Datos de la acción a completar (worker_nombre, operacion, tag_spool, timestamp)
        action_service: Servicio de acciones (inyectado)

    Returns:
        ActionResponse con success=True y metadata de la operación

    Raises:
        HTTPException 404: Si trabajador o spool no encontrado
        HTTPException 400: Si operación no iniciada o ya completada
        HTTPException 403: Si trabajador != quien inició (CRÍTICO - ownership violation)
        HTTPException 503: Si falla actualización Google Sheets

    Example request:
        ```json
        {
            "worker_nombre": "Juan Pérez",
            "operacion": "ARM",
            "tag_spool": "MK-1335-CW-25238-011",
            "timestamp": "2025-11-10T14:30:00Z"
        }
        ```

    Example response (exitosa):
        ```json
        {
            "success": true,
            "message": "Acción ARM completada exitosamente. Spool MK-1335-CW-25238-011 completado por Juan Pérez",
            "data": {
                "tag_spool": "MK-1335-CW-25238-011",
                "operacion": "ARM",
                "trabajador": "Juan Pérez",
                "fila_actualizada": 25,
                "columna_actualizada": "V",
                "valor_nuevo": 1.0,
                "metadata_actualizada": {
                    "armador": null,
                    "soldador": null,
                    "fecha_armado": "10/11/2025",
                    "fecha_soldadura": null
                }
            }
        }
        ```

    Example response (403 - ownership violation):
        ```json
        {
            "success": false,
            "error": "NO_AUTORIZADO",
            "message": "Solo Juan López puede completar ARM en 'MK-1335-CW-25238-011' (él la inició). Tú eres Juan Pérez.",
            "data": {
                "tag_spool": "MK-1335-CW-25238-011",
                "trabajador_esperado": "Juan López",
                "trabajador_solicitante": "Juan Pérez",
                "operacion": "ARM"
            }
        }
        ```
    """
    logger.info(
        f"POST /api/completar-accion - worker={request.worker_nombre}, "
        f"operacion={request.operacion}, tag_spool={request.tag_spool}"
    )

    # Delegar a ActionService (orchestrator con ownership validation)
    # CRÍTICO: ActionService.completar_accion valida BC/BE = worker_nombre
    # Si worker != owner → raise NoAutorizadoError → 403 FORBIDDEN
    response = action_service.completar_accion(
        worker_nombre=request.worker_nombre,
        operacion=request.operacion,
        tag_spool=request.tag_spool,
        timestamp=request.timestamp
    )

    logger.info(
        f"Action completed successfully - {request.operacion} on {request.tag_spool} "
        f"by {request.worker_nombre}"
    )

    return response
