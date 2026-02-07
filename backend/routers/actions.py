"""
Actions Router - Reparacion endpoints (v3.0 Phase 6).

Contains TOMAR/PAUSAR/COMPLETAR/CANCELAR operations for RECHAZADO spools.
v2.1 endpoints (iniciar-accion, completar-accion, cancelar-accion) have been removed.
v4.0 uses /api/v4/occupation/iniciar and /api/v4/occupation/finalizar instead.
"""

from fastapi import APIRouter, Depends, status
from backend.core.dependency import get_reparacion_service
from backend.services.reparacion_service import ReparacionService
from backend.models.action import ActionRequest
import logging

logger = logging.getLogger(__name__)
router = APIRouter()


# ============================================================================
# REPARACION ENDPOINTS (v3.0 Phase 6)
# ============================================================================

@router.post("/tomar-reparacion", response_model=dict, status_code=status.HTTP_200_OK)
async def tomar_reparacion(
    request: ActionRequest,
    reparacion_service: ReparacionService = Depends(get_reparacion_service)
):
    """
    Worker takes RECHAZADO spool for repair (v3.0 Phase 6).

    Validates:
    - Spool exists and is RECHAZADO (not BLOQUEADO)
    - Spool not currently occupied
    - Worker exists and is active

    Updates:
    - Ocupado_Por = worker_nombre
    - Fecha_Ocupacion = current datetime
    - Estado_Detalle = "EN_REPARACION (Ciclo X/3) - Ocupado: {worker}"

    Args:
        request: ActionRequest (worker_id, tag_spool)
        reparacion_service: ReparacionService (injected)

    Returns:
        dict with success message and estado_detalle

    Raises:
        HTTPException 404: Spool or worker not found
        HTTPException 400: Spool not RECHAZADO
        HTTPException 403: Spool is BLOQUEADO (HTTP 403)
        HTTPException 409: Spool occupied by another worker

    Example request:
        ```json
        {
            "worker_id": 93,
            "tag_spool": "MK-1335-CW-25238-011"
        }
        ```

    Example response (200 OK):
        ```json
        {
            "success": true,
            "message": "Reparacion tomada para spool MK-1335-CW-25238-011",
            "tag_spool": "MK-1335-CW-25238-011",
            "worker_nombre": "MR(93)",
            "estado_detalle": "EN_REPARACION (Ciclo 2/3) - Ocupado: MR(93)",
            "cycle": 2
        }
        ```
    """
    logger.info(f"POST /api/tomar-reparacion - worker_id={request.worker_id}, tag_spool={request.tag_spool}")

    # Worker nombre_completo needs to be fetched from worker_id
    # For now, use format "W{worker_id}" as placeholder - service will fetch actual name
    result = await reparacion_service.tomar_reparacion(
        tag_spool=request.tag_spool,
        worker_id=request.worker_id,
        worker_nombre=f"W({request.worker_id})"  # Placeholder - service fetches actual name
    )

    logger.info(f"Reparacion tomada: {request.tag_spool} by worker_id {request.worker_id}")
    return result


@router.post("/pausar-reparacion", response_model=dict, status_code=status.HTTP_200_OK)
async def pausar_reparacion(
    request: ActionRequest,
    reparacion_service: ReparacionService = Depends(get_reparacion_service)
):
    """
    Worker pauses repair work and releases occupation (v3.0 Phase 6).

    Validates:
    - Spool exists and is EN_REPARACION
    - Worker owns the spool (ownership validation)

    Updates:
    - Ocupado_Por = None
    - Fecha_Ocupacion = None
    - Estado_Detalle = "REPARACION_PAUSADA (Ciclo X/3)"

    Args:
        request: ActionRequest (worker_id, tag_spool)
        reparacion_service: ReparacionService (injected)

    Returns:
        dict with success message and estado_detalle

    Raises:
        HTTPException 404: Spool not found
        HTTPException 400: Spool not EN_REPARACION
        HTTPException 403: Worker doesn't own the spool

    Example response (200 OK):
        ```json
        {
            "success": true,
            "message": "Reparacion pausada para spool MK-1335-CW-25238-011",
            "tag_spool": "MK-1335-CW-25238-011",
            "estado_detalle": "REPARACION_PAUSADA (Ciclo 2/3)"
        }
        ```
    """
    logger.info(f"POST /api/pausar-reparacion - worker_id={request.worker_id}, tag_spool={request.tag_spool}")

    result = await reparacion_service.pausar_reparacion(
        tag_spool=request.tag_spool,
        worker_id=request.worker_id
    )

    logger.info(f"Reparacion pausada: {request.tag_spool}")
    return result


@router.post("/completar-reparacion", response_model=dict, status_code=status.HTTP_200_OK)
async def completar_reparacion(
    request: ActionRequest,
    reparacion_service: ReparacionService = Depends(get_reparacion_service)
):
    """
    Worker completes repair and returns spool to metrologia queue (v3.0 Phase 6).

    Validates:
    - Spool exists and is EN_REPARACION
    - Worker owns the spool (ownership validation)

    Updates:
    - Ocupado_Por = None
    - Fecha_Ocupacion = None
    - Estado_Detalle = "PENDIENTE_METROLOGIA"

    Args:
        request: ActionRequest (worker_id, tag_spool)
        reparacion_service: ReparacionService (injected)

    Returns:
        dict with success message and estado_detalle

    Raises:
        HTTPException 404: Spool not found
        HTTPException 400: Spool not EN_REPARACION
        HTTPException 403: Worker doesn't own the spool

    Example response (200 OK):
        ```json
        {
            "success": true,
            "message": "Reparacion completada para spool MK-1335-CW-25238-011 - devuelto a metrologia",
            "tag_spool": "MK-1335-CW-25238-011",
            "estado_detalle": "PENDIENTE_METROLOGIA",
            "cycle": 2
        }
        ```
    """
    logger.info(f"POST /api/completar-reparacion - worker_id={request.worker_id}, tag_spool={request.tag_spool}")

    result = await reparacion_service.completar_reparacion(
        tag_spool=request.tag_spool,
        worker_id=request.worker_id,
        worker_nombre=f"W({request.worker_id})"  # Placeholder
    )

    logger.info(f"Reparacion completada: {request.tag_spool} -> PENDIENTE_METROLOGIA")
    return result


@router.post("/cancelar-reparacion", response_model=dict, status_code=status.HTTP_200_OK)
async def cancelar_reparacion(
    request: ActionRequest,
    reparacion_service: ReparacionService = Depends(get_reparacion_service)
):
    """
    Worker cancels repair work and returns spool to RECHAZADO (v3.0 Phase 6).

    Validates:
    - Spool exists and is EN_REPARACION or REPARACION_PAUSADA

    Updates:
    - Ocupado_Por = None
    - Fecha_Ocupacion = None
    - Estado_Detalle = "RECHAZADO (Ciclo X/3) - Pendiente reparacion"

    Args:
        request: ActionRequest (worker_id, tag_spool)
        reparacion_service: ReparacionService (injected)

    Returns:
        dict with success message and estado_detalle

    Raises:
        HTTPException 404: Spool not found
        HTTPException 400: Spool not EN_REPARACION or REPARACION_PAUSADA

    Example response (200 OK):
        ```json
        {
            "success": true,
            "message": "Reparacion cancelada para spool MK-1335-CW-25238-011",
            "tag_spool": "MK-1335-CW-25238-011",
            "estado_detalle": "RECHAZADO (Ciclo 2/3) - Pendiente reparacion"
        }
        ```
    """
    logger.info(f"POST /api/cancelar-reparacion - worker_id={request.worker_id}, tag_spool={request.tag_spool}")

    result = await reparacion_service.cancelar_reparacion(
        tag_spool=request.tag_spool,
        worker_id=request.worker_id
    )

    logger.info(f"Reparacion cancelada: {request.tag_spool}")
    return result
