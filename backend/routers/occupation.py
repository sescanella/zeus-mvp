"""
Occupation Router - Spool occupation operations (v3.0).

Core endpoints for TOMAR/PAUSAR/COMPLETAR operations with Redis locking.
Implements LOC-04 requirement: explicit 409 Conflict for race conditions.

Key features:
- POST /api/occupation/tomar: Take single spool (atomic lock)
- POST /api/occupation/pausar: Pause work on spool (release lock)
- POST /api/occupation/completar: Complete work on spool (release lock)
- POST /api/occupation/batch-tomar: Take multiple spools (up to 50)
- GET /api/occupation/status/{tag_spool}: Check occupation status

Exception handling:
- SpoolOccupiedError → 409 CONFLICT (LOC-04 requirement)
- NoAutorizadoError → 403 FORBIDDEN
- SpoolNoEncontradoError → 404 NOT FOUND
- Other errors → appropriate HTTP status codes
"""

from fastapi import APIRouter, Depends, HTTPException, status
from backend.core.dependency import get_occupation_service
from backend.services.occupation_service import OccupationService
from backend.models.occupation import (
    TomarRequest,
    PausarRequest,
    CompletarRequest,
    BatchTomarRequest,
    OccupationResponse,
    BatchOccupationResponse,
    OccupationStatus
)
from backend.exceptions import (
    SpoolOccupiedError,
    SpoolNoEncontradoError,
    NoAutorizadoError,
    LockExpiredError,
    DependenciasNoSatisfechasError,
    SheetsUpdateError
)
import logging

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post("/occupation/tomar", response_model=OccupationResponse, status_code=status.HTTP_200_OK)
async def tomar_spool(
    request: TomarRequest,
    service: OccupationService = Depends(get_occupation_service)
):
    """
    Take a spool (acquire occupation lock).

    Atomically acquires Redis lock and updates Ocupado_Por/Fecha_Ocupacion
    in Operaciones sheet. Prevents concurrent TOMAR on same spool.

    Validations:
    - Spool exists in Operaciones sheet
    - Spool has Fecha_Materiales (prerequisite)
    - Spool not already occupied (atomic lock check)

    Updates (atomic):
    1. Redis lock: SET NX EX with worker_id token
    2. Sheets: Ocupado_Por = worker_nombre, Fecha_Ocupacion = today
    3. Metadata: Log TOMAR event (audit trail)

    Args:
        request: TomarRequest with tag_spool, worker_id, worker_nombre, operacion
        service: OccupationService (injected)

    Returns:
        OccupationResponse with success status and message

    Raises:
        HTTPException 404: If spool not found
        HTTPException 400: If Fecha_Materiales missing (prerequisite)
        HTTPException 409: If spool already occupied (LOC-04 requirement)
        HTTPException 503: If Sheets update fails

    Example request:
        ```json
        {
            "tag_spool": "MK-1335-CW-25238-011",
            "worker_id": 93,
            "worker_nombre": "MR(93)",
            "operacion": "ARM"
        }
        ```

    Example response:
        ```json
        {
            "success": true,
            "tag_spool": "MK-1335-CW-25238-011",
            "message": "Spool MK-1335-CW-25238-011 tomado por MR(93)"
        }
        ```
    """
    try:
        return await service.tomar(request)

    except SpoolOccupiedError as e:
        # LOC-04 requirement: Return 409 Conflict for race conditions
        logger.warning(f"Spool occupation conflict: {e.message}")
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=e.message
        )

    except SpoolNoEncontradoError as e:
        logger.info(f"Spool not found: {e.message}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=e.message
        )

    except DependenciasNoSatisfechasError as e:
        logger.info(f"Prerequisites not met: {e.message}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=e.message
        )

    except SheetsUpdateError as e:
        logger.error(f"Sheets update failed: {e.message}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=e.message
        )

    except Exception as e:
        logger.error(f"Unexpected error in tomar_spool: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal server error: {str(e)}"
        )


@router.post("/occupation/pausar", response_model=OccupationResponse, status_code=status.HTTP_200_OK)
async def pausar_spool(
    request: PausarRequest,
    service: OccupationService = Depends(get_occupation_service)
):
    """
    Pause work on a spool (mark as paused and release lock).

    Verifies worker owns the lock, marks spool as "ARM parcial (pausado)"
    or "SOLD parcial (pausado)", clears occupation, and releases Redis lock.

    Validations:
    - Spool exists
    - Worker owns the Redis lock (ownership check)

    Updates:
    1. Sheets: Estado = "ARM/SOLD parcial (pausado)", clear Ocupado_Por/Fecha_Ocupacion
    2. Redis: Release lock (Lua script with ownership verification)
    3. Metadata: Log PAUSAR event

    Args:
        request: PausarRequest with tag_spool, worker_id, worker_nombre
        service: OccupationService (injected)

    Returns:
        OccupationResponse with success status

    Raises:
        HTTPException 404: If spool not found
        HTTPException 403: If worker doesn't own lock
        HTTPException 410: If lock already expired
        HTTPException 503: If Sheets update fails

    Example request:
        ```json
        {
            "tag_spool": "MK-1335-CW-25238-011",
            "worker_id": 93,
            "worker_nombre": "MR(93)"
        }
        ```
    """
    try:
        return await service.pausar(request)

    except SpoolNoEncontradoError as e:
        logger.info(f"Spool not found: {e.message}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=e.message
        )

    except NoAutorizadoError as e:
        logger.warning(f"Unauthorized pausar attempt: {e.message}")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=e.message
        )

    except LockExpiredError as e:
        logger.warning(f"Lock expired: {e.message}")
        raise HTTPException(
            status_code=status.HTTP_410_GONE,
            detail=e.message
        )

    except SheetsUpdateError as e:
        logger.error(f"Sheets update failed: {e.message}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=e.message
        )

    except Exception as e:
        logger.error(f"Unexpected error in pausar_spool: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal server error: {str(e)}"
        )


@router.post("/occupation/completar", response_model=OccupationResponse, status_code=status.HTTP_200_OK)
async def completar_spool(
    request: CompletarRequest,
    service: OccupationService = Depends(get_occupation_service)
):
    """
    Complete work on a spool (mark operation complete and release lock).

    Verifies worker owns the lock, updates fecha_armado or fecha_soldadura,
    clears occupation, and releases Redis lock.

    Validations:
    - Spool exists
    - Worker owns the Redis lock (ownership check)

    Updates:
    1. Sheets: Fecha_Armado/Soldadura = fecha_operacion, clear Ocupado_Por/Fecha_Ocupacion
    2. Redis: Release lock
    3. Metadata: Log COMPLETAR event

    Args:
        request: CompletarRequest with tag_spool, worker_id, worker_nombre, fecha_operacion
        service: OccupationService (injected)

    Returns:
        OccupationResponse with success status

    Raises:
        HTTPException 404: If spool not found
        HTTPException 403: If worker doesn't own lock
        HTTPException 410: If lock already expired
        HTTPException 503: If Sheets update fails

    Example request:
        ```json
        {
            "tag_spool": "MK-1335-CW-25238-011",
            "worker_id": 93,
            "worker_nombre": "MR(93)",
            "fecha_operacion": "2026-01-27"
        }
        ```
    """
    try:
        return await service.completar(request)

    except SpoolNoEncontradoError as e:
        logger.info(f"Spool not found: {e.message}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=e.message
        )

    except NoAutorizadoError as e:
        logger.warning(f"Unauthorized completar attempt: {e.message}")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=e.message
        )

    except LockExpiredError as e:
        logger.warning(f"Lock expired: {e.message}")
        raise HTTPException(
            status_code=status.HTTP_410_GONE,
            detail=e.message
        )

    except SheetsUpdateError as e:
        logger.error(f"Sheets update failed: {e.message}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=e.message
        )

    except Exception as e:
        logger.error(f"Unexpected error in completar_spool: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal server error: {str(e)}"
        )


@router.post("/occupation/batch-tomar", response_model=BatchOccupationResponse, status_code=status.HTTP_200_OK)
async def batch_tomar_spools(
    request: BatchTomarRequest,
    service: OccupationService = Depends(get_occupation_service)
):
    """
    Take multiple spools in batch (up to 50).

    Processes each spool independently. Returns detailed results showing
    which spools succeeded and which failed.

    Partial success is allowed: If 7 of 10 spools succeed, the operation
    returns 200 OK with details about successes and failures.

    Args:
        request: BatchTomarRequest with tag_spools list (max 50)
        service: OccupationService (injected)

    Returns:
        BatchOccupationResponse with total, succeeded, failed counts and details

    Example request:
        ```json
        {
            "tag_spools": [
                "MK-1335-CW-25238-011",
                "MK-1335-CW-25238-012",
                "MK-1335-CW-25238-013"
            ],
            "worker_id": 93,
            "worker_nombre": "MR(93)",
            "operacion": "ARM"
        }
        ```

    Example response:
        ```json
        {
            "total": 3,
            "succeeded": 2,
            "failed": 1,
            "details": [
                {
                    "success": true,
                    "tag_spool": "MK-1335-CW-25238-011",
                    "message": "Spool tomado exitosamente"
                },
                {
                    "success": true,
                    "tag_spool": "MK-1335-CW-25238-012",
                    "message": "Spool tomado exitosamente"
                },
                {
                    "success": false,
                    "tag_spool": "MK-1335-CW-25238-013",
                    "message": "Spool ya ocupado por JP(94)"
                }
            ]
        }
        ```
    """
    try:
        return await service.batch_tomar(request)

    except Exception as e:
        logger.error(f"Unexpected error in batch_tomar_spools: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal server error: {str(e)}"
        )
