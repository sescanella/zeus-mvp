"""
Metrología Router - Quality inspection instant completion.

Phase 5 feature for binary inspection workflow (APROBADO/RECHAZADO).
Skips occupation phase - instant completion with binary resultado.

Key endpoint:
- POST /api/metrologia/completar: Complete inspection with binary result
"""

from fastapi import APIRouter, Depends, status
from backend.core.dependency import get_metrologia_service, get_worker_service
from backend.services.metrologia_service import MetrologiaService
from backend.services.worker_service import WorkerService
from backend.models.metrologia import (
    CompletarMetrologiaRequest,
    CompletarMetrologiaResponse
)
from backend.services.estado_detalle_builder import EstadoDetalleBuilder
from backend.exceptions import (
    SpoolNoEncontradoError,
    WorkerNoEncontradoError,
    DependenciasNoSatisfechasError,
    OperacionYaCompletadaError,
    SpoolOccupiedError,
    RolNoAutorizadoError
)
import logging

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post("/completar", response_model=CompletarMetrologiaResponse, status_code=status.HTTP_200_OK)
async def completar_metrologia(
    request: CompletarMetrologiaRequest,
    metrologia_service: MetrologiaService = Depends(get_metrologia_service),
    worker_service: WorkerService = Depends(get_worker_service)
):
    """
    Complete metrología inspection with binary result (APROBADO/RECHAZADO).

    Instant completion workflow - no occupation phase, no TOMAR.
    Validates prerequisites: ARM + SOLD complete, spool not occupied.

    Validations:
    - Worker exists and is active
    - Worker has METROLOGIA role
    - Spool exists in Operaciones sheet
    - ARM and SOLD operations completed (Fecha_Armado + Fecha_Soldadura present)
    - Spool not occupied (Ocupado_Por = None)
    - Metrología not already done (Fecha_QC_Metrologia = None)

    Updates:
    - Fecha_QC_Metrologia: Set to today's date (DD/MM/YYYY)
    - Metadata log: COMPLETAR_METROLOGIA event with resultado

    Args:
        request: Inspection data (tag_spool, worker_id, resultado)
        metrologia_service: Metrología service (injected)
        worker_service: Worker service for name formatting (injected)

    Returns:
        CompletarMetrologiaResponse with success status and estado_detalle

    Raises:
        HTTPException 404: If worker or spool not found
        HTTPException 400: If prerequisites not met or already inspected
        HTTPException 409: If spool occupied (race condition)
        HTTPException 403: If worker lacks METROLOGIA role
        HTTPException 422: If resultado not APROBADO/RECHAZADO (Pydantic validation)

    Example request (APROBADO):
        ```json
        {
            "tag_spool": "MK-1335-CW-25238-011",
            "worker_id": 93,
            "resultado": "APROBADO"
        }
        ```

    Example response (APROBADO):
        ```json
        {
            "success": true,
            "tag_spool": "MK-1335-CW-25238-011",
            "resultado": "APROBADO",
            "estado_detalle": "Disponible - ARM completado, SOLD completado, METROLOGIA APROBADO ✓",
            "message": "Metrología aprobado para spool MK-1335-CW-25238-011"
        }
        ```

    Example request (RECHAZADO):
        ```json
        {
            "tag_spool": "MK-1335-CW-25238-012",
            "worker_id": 94,
            "resultado": "RECHAZADO"
        }
        ```

    Example response (RECHAZADO):
        ```json
        {
            "success": true,
            "tag_spool": "MK-1335-CW-25238-012",
            "resultado": "RECHAZADO",
            "estado_detalle": "Disponible - ARM completado, SOLD completado, METROLOGIA RECHAZADO - Pendiente reparación",
            "message": "Metrología rechazado para spool MK-1335-CW-25238-012"
        }
        ```
    """
    logger.info(
        f"POST /api/metrologia/completar - worker_id={request.worker_id}, "
        f"tag_spool={request.tag_spool}, resultado={request.resultado}"
    )

    # Fetch worker to get nombre_completo
    worker = worker_service.get_worker_by_id(request.worker_id)
    if not worker:
        raise WorkerNoEncontradoError(str(request.worker_id))

    worker_nombre = worker.nombre_completo  # Format: "INICIALES(ID)"

    # Delegate to MetrologiaService (orchestrator)
    # All validations performed in MetrologiaService
    # Exceptions propagate automatically to exception handler
    result = await metrologia_service.completar(
        tag_spool=request.tag_spool,
        worker_id=request.worker_id,
        worker_nombre=worker_nombre,
        resultado=request.resultado.value
    )

    # Build Estado_Detalle display string
    estado_builder = EstadoDetalleBuilder()

    # Determine metrologia state based on resultado
    metrologia_state = "aprobado" if request.resultado.value == "APROBADO" else "rechazado"

    # Build estado_detalle (ARM and SOLD are always completado at this point)
    estado_detalle = estado_builder.build(
        ocupado_por=None,
        arm_state="completado",
        sold_state="completado",
        metrologia_state=metrologia_state
    )

    logger.info(
        f"Metrología completed successfully - {request.tag_spool} -> {request.resultado}"
    )

    return CompletarMetrologiaResponse(
        success=True,
        tag_spool=request.tag_spool,
        resultado=request.resultado.value,
        estado_detalle=estado_detalle,
        message=result["message"]
    )
