"""
Union query endpoints (v4.0 Phase 11).

Read-only endpoints for union disponibles and metrics queries.
Foundation for Phase 12 frontend union selection.

Endpoints:
- GET /api/v4/uniones/{tag}/disponibles?operacion=ARM|SOLD
- GET /api/v4/uniones/{tag}/metricas
"""
import logging
from fastapi import APIRouter, Depends, HTTPException, Query

from backend.models.union_api import DisponiblesResponse, MetricasResponse, UnionSummary
from backend.repositories.union_repository import UnionRepository
from backend.repositories.sheets_repository import SheetsRepository
from backend.core.dependency import get_union_repository, get_sheets_repository
from backend.exceptions import SheetsConnectionError


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
