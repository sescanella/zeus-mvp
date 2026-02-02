"""
Union query endpoints (v4.0 Phase 11).

Read-only endpoints for union disponibles and metrics queries.
Foundation for Phase 12 frontend union selection.

Endpoints:
- GET /api/v4/uniones/{tag}/disponibles?operacion=ARM|SOLD
- GET /api/v4/uniones/{tag}/metricas
- POST /api/v4/occupation/finalizar - Process selected unions with auto-determination
"""
import logging
from fastapi import APIRouter, Depends, HTTPException, Query

from backend.models.union_api import (
    DisponiblesResponse,
    MetricasResponse,
    UnionSummary,
    FinalizarRequestV4,
    FinalizarResponseV4
)
from backend.models.occupation import FinalizarRequest
from backend.repositories.union_repository import UnionRepository
from backend.repositories.sheets_repository import SheetsRepository
from backend.repositories.metadata_repository import MetadataRepository
from backend.services.occupation_service import OccupationService
from backend.services.union_service import UnionService
from backend.services.worker_service import WorkerService
from backend.services.redis_lock_service import RedisLockService
from backend.services.conflict_service import ConflictService
from backend.services.redis_event_service import RedisEventService
from backend.core.dependency import (
    get_union_repository,
    get_sheets_repository,
    get_metadata_repository,
    get_redis_lock_service,
    get_conflict_service,
    get_redis_event_service,
    get_worker_service
)
from backend.exceptions import SheetsConnectionError, SpoolNoEncontradoError, NoAutorizadoError
from backend.utils.version_detection import is_v4_spool


logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/uniones/{tag}/disponibles", response_model=DisponiblesResponse)
async def get_disponibles(
    tag: str,
    operacion: str = Query(..., pattern="^(ARM|SOLD)$"),
    union_repo: UnionRepository = Depends(get_union_repository),
    sheets_repo: SheetsRepository = Depends(get_sheets_repository)
):
    """
    Get available unions for a given spool and operation.

    ARM disponibles: unions where ARM_FECHA_FIN is NULL
    SOLD disponibles: unions where ARM_FECHA_FIN is NOT NULL and SOL_FECHA_FIN is NULL

    Args:
        tag: Spool TAG_SPOOL to query
        operacion: Operation type (ARM or SOLD)
        union_repo: UnionRepository dependency
        sheets_repo: SheetsRepository dependency

    Returns:
        DisponiblesResponse: List of available unions with count

    Raises:
        404: Spool not found
        500: Google Sheets connection error
    """
    try:
        # Get spool to extract OT (v4.0 uses OT as primary FK)
        spool = sheets_repo.get_spool_by_tag(tag)
        if not spool:
            logger.warning(f"Spool {tag} not found")
            raise HTTPException(status_code=404, detail=f"Spool {tag} not found")

        # Extract OT from spool
        ot = spool.get("OT")
        if not ot:
            logger.error(f"Spool {tag} missing OT field")
            raise HTTPException(
                status_code=500,
                detail=f"Spool {tag} has invalid data (missing OT)"
            )

        # Get available unions based on operation
        if operacion == "ARM":
            unions = union_repo.get_disponibles_arm_by_ot(ot)
        else:  # SOLD
            unions = union_repo.get_disponibles_sold_by_ot(ot)

        # Build response with core fields only (4 fields per UnionSummary)
        union_summaries = [
            UnionSummary(
                id=u.id,
                n_union=u.n_union,
                dn_union=u.dn_union,
                tipo_union=u.tipo_union
            )
            for u in unions
        ]

        logger.info(
            f"Found {len(union_summaries)} disponibles for {tag} ({operacion})"
        )

        return DisponiblesResponse(
            tag_spool=tag,
            operacion=operacion,
            unions=union_summaries,
            count=len(union_summaries)
        )

    except HTTPException:
        # Re-raise HTTP exceptions as-is
        raise
    except SheetsConnectionError as e:
        logger.error(f"Sheets connection error for {tag}: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to read union data: {str(e)}"
        )
    except Exception as e:
        logger.error(f"Unexpected error in get_disponibles for {tag}: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Internal server error: {str(e)}"
        )


@router.get("/uniones/{tag}/metricas", response_model=MetricasResponse)
async def get_metricas(
    tag: str,
    union_repo: UnionRepository = Depends(get_union_repository),
    sheets_repo: SheetsRepository = Depends(get_sheets_repository)
):
    """
    Get spool-level metrics (5 fields per CONTEXT.md specification).

    Always-fresh calculation from Uniones sheet (no caching per D33).
    Returns completion counts and pulgadas-diámetro business metric.

    Args:
        tag: Spool TAG_SPOOL to query
        union_repo: UnionRepository dependency
        sheets_repo: SheetsRepository dependency

    Returns:
        MetricasResponse: 5-field metrics (total, arm_count, sold_count, pulgadas_arm, pulgadas_sold)

    Raises:
        404: Spool not found or no unions
        500: Google Sheets connection error
    """
    try:
        # Get spool to extract OT
        spool = sheets_repo.get_spool_by_tag(tag)
        if not spool:
            logger.warning(f"Spool {tag} not found")
            raise HTTPException(status_code=404, detail=f"Spool {tag} not found")

        # Extract OT from spool
        ot = spool.get("OT")
        if not ot:
            logger.error(f"Spool {tag} missing OT field")
            raise HTTPException(
                status_code=500,
                detail=f"Spool {tag} has invalid data (missing OT)"
            )

        # Calculate metrics using bulk method (efficient single-call)
        metrics = union_repo.calculate_metrics(ot)

        # Verify spool has unions
        if metrics["total_uniones"] == 0:
            logger.warning(f"No unions found for spool {tag}")
            raise HTTPException(
                status_code=404,
                detail=f"No unions found for spool {tag}"
            )

        logger.info(
            f"Calculated metrics for {tag}: "
            f"{metrics['arm_completadas']}/{metrics['total_uniones']} ARM, "
            f"{metrics['sold_completadas']}/{metrics['total_uniones']} SOLD, "
            f"{metrics['pulgadas_arm']:.2f} pulgadas ARM, "
            f"{metrics['pulgadas_sold']:.2f} pulgadas SOLD"
        )

        return MetricasResponse(
            tag_spool=tag,
            total_uniones=metrics["total_uniones"],
            arm_completadas=metrics["arm_completadas"],
            sold_completadas=metrics["sold_completadas"],
            pulgadas_arm=metrics["pulgadas_arm"],
            pulgadas_sold=metrics["pulgadas_sold"]
        )

    except HTTPException:
        # Re-raise HTTP exceptions as-is
        raise
    except SheetsConnectionError as e:
        logger.error(f"Sheets connection error for {tag}: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to read union data: {str(e)}"
        )
    except Exception as e:
        logger.error(f"Unexpected error in get_metricas for {tag}: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Internal server error: {str(e)}"
        )


@router.post("/occupation/finalizar", response_model=FinalizarResponseV4)
async def finalizar_v4(
    request: FinalizarRequestV4,
    sheets_repo: SheetsRepository = Depends(get_sheets_repository),
    metadata_repo: MetadataRepository = Depends(get_metadata_repository),
    redis_lock_service: RedisLockService = Depends(get_redis_lock_service),
    conflict_service: ConflictService = Depends(get_conflict_service),
    redis_event_service: RedisEventService = Depends(get_redis_event_service),
    worker_service: WorkerService = Depends(get_worker_service),
    union_repo: UnionRepository = Depends(get_union_repository)
):
    """
    v4.0 FINALIZAR - Process selected unions and auto-determine action.

    This endpoint processes the selected unions and auto-determines whether to
    PAUSAR (partial completion), COMPLETAR (full completion), or CANCELADO
    (zero unions selected).

    Version Requirements:
    - Only accepts v4.0 spools (Total_Uniones > 0)
    - Rejects v3.0 spools with 400 Bad Request

    Request Body:
    - tag_spool: Spool TAG identifier
    - worker_id: Worker ID number
    - operacion: ARM or SOLD
    - selected_unions: List of union IDs (empty = cancellation)

    Success Response (200):
    {
        "success": true,
        "tag_spool": "OT-123",
        "message": "Trabajo pausado - 3 uniones procesadas",
        "action_taken": "PAUSAR",
        "unions_processed": 3,
        "pulgadas": 16.50,
        "metrologia_triggered": false
    }

    Error Responses:
    - 400: Spool is v3.0 (use /api/v3/occupation/completar instead)
    - 403: Worker doesn't own the spool
    - 404: Spool not found
    - 409: Race condition (some unions no longer available)
    """
    tag_spool = request.tag_spool

    logger.info(
        f"v4.0 FINALIZAR request: {tag_spool} by worker {request.worker_id} "
        f"for {request.operacion}, {len(request.selected_unions)} unions selected"
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
                f"v3.0 spool {tag_spool} rejected from v4.0 FINALIZAR endpoint "
                f"(Total_Uniones={spool.total_uniones})"
            )
            raise HTTPException(
                status_code=400,
                detail={
                    "error": "WRONG_VERSION",
                    "message": "Spool is v3.0, use /api/v3/occupation/completar instead",
                    "spool_version": "v3.0",
                    "correct_endpoint": "/api/v3/occupation/completar"
                }
            )

        # Step 2: Derive worker_nombre from worker_id
        worker = worker_service.get_worker_by_id(request.worker_id)
        if not worker:
            raise HTTPException(
                status_code=404,
                detail=f"Worker {request.worker_id} not found"
            )

        # Format worker_nombre as APELLIDO(ID)
        worker_nombre = f"{worker.apellido}({request.worker_id})"

        # Step 3: Create OccupationService with UnionService injected
        union_service = UnionService(
            union_repo=union_repo,
            metadata_repo=metadata_repo
        )

        occupation_service = OccupationService(
            redis_lock_service=redis_lock_service,
            sheets_repository=sheets_repo,
            metadata_repository=metadata_repo,
            conflict_service=conflict_service,
            redis_event_service=redis_event_service,
            union_repository=union_repo,
            union_service=union_service
        )

        # Step 4: Build Phase 10 FinalizarRequest
        finalizar_request = FinalizarRequest(
            tag_spool=request.tag_spool,
            worker_id=request.worker_id,
            worker_nombre=worker_nombre,
            operacion=request.operacion,
            selected_unions=request.selected_unions
        )

        # Step 5: Call service layer
        result = await occupation_service.finalizar_spool(finalizar_request)

        # Extract metrics from result
        action = result.action_taken or "UNKNOWN"
        unions_count = result.unions_processed or 0

        # Step 6: Calculate pulgadas if unions were processed
        pulgadas = None
        if unions_count > 0 and len(request.selected_unions) > 0:
            # Get OT from spool for metrics calculation
            ot = spool.ot
            if ot:
                # Get metrics to extract pulgadas for the processed operation
                metrics = union_repo.calculate_metrics(ot)
                if request.operacion.value == "ARM":
                    pulgadas = metrics["pulgadas_arm"]
                else:  # SOLD
                    pulgadas = metrics["pulgadas_sold"]

        # Step 7: Build message based on action
        if action == "CANCELADO":
            message = f"Trabajo cancelado - sin uniones seleccionadas"
        elif action == "PAUSAR":
            message = f"Trabajo pausado - {unions_count} uniones procesadas"
        else:  # COMPLETAR
            message = f"Operación completada - {unions_count} uniones procesadas"
            if result.metrologia_triggered:
                message += " (Listo para metrología)"

        pulgadas_str = f"{pulgadas:.2f}" if pulgadas is not None else "0.00"
        logger.info(
            f"✅ v4.0 FINALIZAR successful: {tag_spool} - {action} with {unions_count} unions, "
            f"{pulgadas_str} pulgadas"
        )

        return FinalizarResponseV4(
            success=True,
            tag_spool=request.tag_spool,
            message=message,
            action_taken=action,
            unions_processed=unions_count,
            pulgadas=pulgadas,
            metrologia_triggered=result.metrologia_triggered or False,
            new_state=result.new_state
        )

    except ValueError as e:
        # Race condition: selected > disponibles
        if "more unions than available" in str(e):
            logger.warning(f"Race condition detected for {tag_spool}: {e}")
            raise HTTPException(
                status_code=409,
                detail={
                    "error": "RACE_CONDITION",
                    "message": "Some unions no longer available (completed by another worker)",
                    "detail": str(e)
                }
            )
        # Re-raise other ValueErrors
        raise HTTPException(
            status_code=400,
            detail=str(e)
        )

    except NoAutorizadoError as e:
        # Ownership validation failed
        logger.warning(f"Authorization failed for {tag_spool}: {e.message}")
        raise HTTPException(
            status_code=403,
            detail={
                "error": "NO_AUTORIZADO",
                "message": "Worker doesn't own this spool"
            }
        )

    except SpoolNoEncontradoError as e:
        # Spool not found (should not happen after Step 1, but defensive)
        logger.error(f"Spool {tag_spool} not found after version check: {e}")
        raise HTTPException(
            status_code=404,
            detail=f"Spool {tag_spool} not found"
        )

    except HTTPException:
        # Re-raise HTTP exceptions as-is
        raise

    except Exception as e:
        # Unexpected error
        logger.error(f"Unexpected error in finalizar_v4 for {tag_spool}: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Internal server error: {str(e)}"
        )
