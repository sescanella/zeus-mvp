"""
v4.0 Occupation Router - P5 Confirmation Workflow (INICIAR/FINALIZAR).

⚠️  CRITICAL ARCHITECTURE CHANGE (v4.0 Phase 8):
All endpoints in this router are called ONLY from P5 (confirmation screen).
No writes occur until user confirms in P5.

Workflow:
- P4 (Spool Selection): UI filters spools and validates eligibility
- P5 (Confirmation): User confirms → API writes to Operaciones/Uniones/Metadata

Endpoints:
- POST /api/v4/occupation/iniciar - Occupy spool (writes Ocupado_Por + Fecha_Ocupacion)
- POST /api/v4/occupation/finalizar - Process unions + auto PAUSAR/COMPLETAR

Version Compatibility:
- INICIAR: Works for v2.1 and v4.0 spools (v2.1 skips Uniones writes)
- FINALIZAR: Union selection for v4.0 only (v2.1 unsupported)

Key Differences from v3.0:
- ❌ NO Redis locks (infrastructure removed)
- ❌ NO optimistic locking (version column not updated)
- ❌ NO backend validation before write (trust P4 filters)
- ✅ Last-Write-Wins (LWW) for race conditions
- ✅ Automatic retry on transient Sheets errors (3 attempts)

References:
- Architecture: .planning/P5-CONFIRMATION-ARCHITECTURE.md
- Service: backend/services/occupation_service.py (iniciar_spool, finalizar_spool)
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
# is_v4_spool import removed - no longer rejecting v3.0 spools
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
    INICIAR - P5 Confirmation Endpoint (occupies spool, writes Ocupado_Por + Fecha_Ocupacion).

    ⚠️  ARCHITECTURE: Called ONLY from P5 (confirmation screen) after user confirms.
    All validation happens in P4 UI filters. Backend trusts P4 and writes directly.

    What this endpoint does:
    1. Validates spool exists (404 if not found)
    2. Validates ARM prerequisite for SOLD (403 if not met)
    3. Writes Ocupado_Por, Fecha_Ocupacion, Estado_Detalle to Operaciones sheet
    4. Logs INICIAR_SPOOL event to Metadata sheet
    5. NO Redis locks, NO optimistic locking, NO backend validation of occupation status

    Version Compatibility:
    - v2.1 spools: Writes Ocupado_Por + Fecha_Ocupacion only (no Uniones)
    - v4.0 spools: Same as v2.1 + sets Estado_Detalle with EstadoDetalleBuilder

    ARM Prerequisite Validation:
    - SOLD operations require ARM to be 100% complete (validated via Uniones sheet for v4.0)
    - Returns 403 Forbidden if ARM prerequisite not met

    Race Condition Handling:
    - Last-Write-Wins (LWW) strategy - no validation before write
    - If race occurs, P4 will detect occupied spool when re-reading table
    - Frontend shows 409 error with occupant information

    Request Body:
    {
        "tag_spool": "OT-123",        // Spool TAG identifier
        "worker_id": 93,              // Worker ID number
        "worker_nombre": "MR(93)",    // Worker name (format: INICIALES(ID))
        "operacion": "ARM"            // ARM or SOLD
    }

    Success Response (200):
    {
        "success": true,
        "tag_spool": "OT-123",
        "message": "Spool OT-123 iniciado por MR(93)",
        "data": {
            "worker_nombre": "MR(93)",
            "operacion": "ARM",
            "fecha_ocupacion": "04-02-2026 14:30:00"
        }
    }

    Error Responses:
    - 403 Forbidden (ARM_PREREQUISITE):
      {
          "error": "ARM_PREREQUISITE",
          "message": "Cannot start SOLD - ARM must be 100% complete first",
          "tag_spool": "OT-123",
          "operacion": "SOLD"
      }

    - 404 Not Found (SPOOL_NO_ENCONTRADO):
      {
          "error": "SPOOL_NO_ENCONTRADO",
          "message": "Spool OT-123 not found"
      }

    - 409 Conflict (SPOOL_OCCUPIED) - detected AFTER write during P4 re-read:
      {
          "error": "SPOOL_OCCUPIED",
          "message": "Spool OT-123 already occupied by JP(45)",
          "occupied_by": "JP(45)",
          "occupied_since": "04-02-2026 14:29:55"
      }

    - 500 Internal Server Error - Sheets write failed after 3 retries
    """
    tag_spool = request.tag_spool

    logger.info(
        f"INICIAR request: {tag_spool} by worker {request.worker_id} "
        f"({request.worker_nombre}) for {request.operacion}"
    )

    try:
        # Step 1: Validate spool exists (accepts v2.1 and v4.0)
        spool = sheets_repo.get_spool_by_tag(tag_spool)
        if not spool:
            raise HTTPException(
                status_code=404,
                detail=f"Spool {tag_spool} not found"
            )

        # Step 2: Call service layer (P5 confirmation workflow)
        # Service handles:
        # - ARM prerequisite validation
        # - Ocupado_Por + Fecha_Ocupacion + Estado_Detalle writes
        # - INICIAR_SPOOL metadata event logging
        # - Automatic retry on transient errors (3 attempts)
        result = await occupation_service.iniciar_spool(request)

        logger.info(
            f"✅ INICIAR successful: {tag_spool} occupied by {request.worker_nombre}"
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
