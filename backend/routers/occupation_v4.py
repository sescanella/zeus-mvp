"""
v4.0 Occupation Router - INICIAR/FINALIZAR workflows with union-level tracking.

Endpoints:
- POST /api/v4/occupation/iniciar - Occupy spool without modifying Uniones sheet
- POST /api/v4/occupation/finalizar - Process selected unions with auto-determination

Version Detection:
- Rejects v3.0 spools (400 Bad Request with helpful error)
- Only accepts spools with Total_Uniones > 0

References:
- Plan: 11-03-PLAN.md (INICIAR endpoint)
- Service: backend/services/occupation_service.py (iniciar_spool, finalizar_spool methods)
"""

import logging
from fastapi import APIRouter, Depends, HTTPException
from typing import Annotated

from backend.core.dependency import (
    get_occupation_service_v4,
    get_sheets_repository,
    get_worker_service
)
from backend.services.occupation_service import OccupationService
from backend.repositories.sheets_repository import SheetsRepository
from backend.services.worker_service import WorkerService
from backend.models.occupation import (
    IniciarRequest,
    FinalizarRequest,
    OccupationResponse
)
from backend.utils.version_detection import is_v4_spool
from backend.exceptions import (
    SpoolNoEncontradoError,
    ArmPrerequisiteError,
    NoAutorizadoError,
    SpoolOccupiedError
)

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/occupation",
    tags=["v4-occupation"]
)


@router.post("/iniciar", response_model=OccupationResponse)
async def iniciar_v4(
    request: IniciarRequest,
    occupation_service: Annotated[OccupationService, Depends(get_occupation_service_v4)],
    sheets_repo: Annotated[SheetsRepository, Depends(get_sheets_repository)]
):
    """
    v4.0 INICIAR - Occupy spool without touching unions.

    This endpoint occupies a spool with a persistent Redis lock and updates
    the Ocupado_Por/Fecha_Ocupacion fields in the Operaciones sheet WITHOUT
    modifying the Uniones sheet. The worker must later call FINALIZAR to
    select which unions they worked on.

    Version Requirements:
    - Only accepts v4.0 spools (Total_Uniones > 0)
    - Rejects v3.0 spools with 400 Bad Request

    ARM Prerequisite:
    - SOLD operations require ARM to be 100% complete
    - Returns 403 Forbidden if ARM prerequisite not met

    Request Body:
    - tag_spool: Spool TAG identifier
    - worker_id: Worker ID number
    - worker_nombre: Worker name (format: INICIALES(ID))
    - operacion: ARM or SOLD

    Success Response (200):
    {
        "success": true,
        "tag_spool": "OT-123",
        "message": "Spool OT-123 iniciado por MR(93)"
    }

    Error Responses:
    - 400: Spool is v3.0 (use /api/v3/occupation/tomar instead)
    - 403: ARM prerequisite not met for SOLD operation
    - 404: Spool not found
    - 409: Spool already occupied by another worker
    """
    tag_spool = request.tag_spool

    logger.info(
        f"v4.0 INICIAR request: {tag_spool} by worker {request.worker_id} "
        f"({request.worker_nombre}) for {request.operacion}"
    )

    try:
        # Step 1: Version detection - reject v3.0 spools
        spool = sheets_repo.get_spool_by_tag(tag_spool)
        if not spool:
            raise HTTPException(
                status_code=404,
                detail=f"Spool {tag_spool} not found"
            )

        if not is_v4_spool(spool.model_dump()):
            logger.warning(
                f"v3.0 spool {tag_spool} rejected from v4.0 INICIAR endpoint "
                f"(Total_Uniones={spool.total_uniones})"
            )
            raise HTTPException(
                status_code=400,
                detail={
                    "error": "WRONG_VERSION",
                    "message": "Spool is v3.0, use /api/v3/occupation/tomar instead",
                    "spool_version": "v3.0",
                    "correct_endpoint": "/api/v3/occupation/tomar",
                    "total_uniones": spool.total_uniones or 0
                }
            )

        # Step 2: Call service layer (handles ARM prerequisite, lock acquisition, etc.)
        result = await occupation_service.iniciar_spool(request)

        logger.info(
            f"✅ v4.0 INICIAR successful: {tag_spool} occupied by {request.worker_nombre}"
        )

        return result

    except ArmPrerequisiteError as e:
        # ARM prerequisite validation failed - return 403
        logger.warning(f"ARM prerequisite failed for {tag_spool}: {e.message}")
        raise HTTPException(
            status_code=403,
            detail={
                "error": "ARM_PREREQUISITE",
                "message": e.message,
                "tag_spool": tag_spool,
                "operacion": request.operacion.value
            }
        )

    except NoAutorizadoError as e:
        # Ownership validation failed - return 403
        logger.warning(f"Authorization failed for {tag_spool}: {e.message}")
        raise HTTPException(
            status_code=403,
            detail={
                "error": "NO_AUTORIZADO",
                "message": e.message
            }
        )

    except SpoolOccupiedError as e:
        # Spool already occupied - return 409
        logger.warning(f"Spool {tag_spool} already occupied: {e.message}")
        raise HTTPException(
            status_code=409,
            detail={
                "error": "SPOOL_OCCUPIED",
                "message": e.message,
                "occupied_by": e.data.get("occupied_by")
            }
        )

    except SpoolNoEncontradoError as e:
        # Spool not found - return 404
        logger.warning(f"Spool {tag_spool} not found")
        raise HTTPException(
            status_code=404,
            detail=e.message
        )

    except HTTPException:
        # Re-raise HTTPException (400, 403, 404, 409) without wrapping in 500
        raise

    except Exception as e:
        # Unexpected error - return 500
        logger.error(f"Unexpected error during INICIAR for {tag_spool}: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Internal server error during INICIAR: {str(e)}"
        )
