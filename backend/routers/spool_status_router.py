"""
Spool Status Router — v5.0 single-page frontend endpoints.

Provides:
  - GET  /api/spool/{tag}/status   — SpoolStatus for an individual spool
  - POST /api/spools/batch-status  — SpoolStatus for a list of spool tags

Both endpoints compute operacion_actual, estado_trabajo, ciclo_rep from the
Estado_Detalle string via parse_estado_detalle(). Reads use the cached
SheetsRepository (60 s TTL) so batch calls are efficient.

Reference:
- Plan: 00-01-PLAN.md + 00-02-PLAN.md (API-01, API-02)
- Research: 00-RESEARCH.md Pattern 1
"""
import logging
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException

from backend.core.dependency import get_sheets_repository, get_worker_service
from backend.repositories.sheets_repository import SheetsRepository
from backend.services.worker_service import WorkerService
from backend.models.spool_status import (
    SpoolStatus,
    BatchStatusRequest,
    BatchStatusResponse,
    BatchStatusError,
)
from backend.exceptions import SheetsConnectionError, SpoolDataCorruptError

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get(
    "/spool/{tag}/status",
    response_model=SpoolStatus,
    summary="Get spool status with computed fields",
    description=(
        "Returns SpoolStatus for a single spool. "
        "Computed fields (operacion_actual, estado_trabajo, ciclo_rep) are "
        "derived from Estado_Detalle. Returns 404 if spool tag not found."
    ),
    tags=["spool-status"],
)
async def get_spool_status(
    tag: str,
    sheets_repo: Annotated[SheetsRepository, Depends(get_sheets_repository)],
    worker_service: Annotated[WorkerService, Depends(get_worker_service)],
) -> SpoolStatus:
    """
    Fetch a spool by tag and return its computed SpoolStatus.

    Args:
        tag: The spool TAG_SPOOL identifier.
        sheets_repo: Injected SheetsRepository (singleton, cached).
        worker_service: Injected WorkerService for resolving worker names.

    Returns:
        SpoolStatus with pass-through and computed fields.

    Raises:
        HTTPException(404): If no spool with the given tag exists.
    """
    try:
        spool = sheets_repo.get_spool_by_tag(tag)
        if spool is None:
            logger.info(f"Spool not found for status request: tag={tag!r}")
            raise HTTPException(
                status_code=404,
                detail={"error": "SPOOL_NO_ENCONTRADO", "message": f"Spool '{tag}' no encontrado"},
            )

        # Build workers lookup: {id: "Nombre Apellido"}
        all_workers = worker_service.get_all_active_workers()
        workers_map = {w.id: f"{w.nombre} {w.apellido}" for w in all_workers}

        return SpoolStatus.from_spool(spool, workers=workers_map)

    except HTTPException:
        raise
    except SpoolDataCorruptError as e:
        # B-001/B-002: the spool exists in the sheet but a field doesn't
        # parse (Pydantic validation error in the repository). Surface as
        # 500 with actionable detail — never silently 404.
        logger.error(
            f"SPOOL_DATA_CORRUPT for tag={tag!r}: {e.data.get('validation_detail')}"
        )
        raise HTTPException(
            status_code=500,
            detail={
                "error": "SPOOL_DATA_CORRUPT",
                "message": (
                    f"El spool '{tag}' existe pero sus datos están malformados. "
                    f"Contacta soporte y reporta el TAG."
                ),
                "tag_spool": tag,
            },
        )
    except SheetsConnectionError:
        logger.error(f"Sheets connection error fetching spool status: tag={tag!r}", exc_info=True)
        raise HTTPException(
            status_code=503,
            detail={"error": "SERVICE_ERROR", "message": "Error al obtener estado del spool. Intenta nuevamente."},
        )
    except Exception as e:
        logger.error(f"Unexpected error in get_spool_status for {tag!r}: {e}", exc_info=True)
        raise HTTPException(
            status_code=503,
            detail={"error": "SERVICE_ERROR", "message": "Error al obtener estado del spool. Intenta nuevamente."},
        )


@router.post(
    "/spools/batch-status",
    response_model=BatchStatusResponse,
    summary="Get spool status for multiple tags",
    description=(
        "Accepts a list of spool tags (1–100) and returns SpoolStatus for each "
        "found spool. Tags not found are silently omitted. "
        "Cache-efficient: all tag lookups share the same 60 s SheetsRepository cache."
    ),
    tags=["spool-status"],
)
async def batch_spool_status(
    request: BatchStatusRequest,
    sheets_repo: Annotated[SheetsRepository, Depends(get_sheets_repository)],
    worker_service: Annotated[WorkerService, Depends(get_worker_service)],
) -> BatchStatusResponse:
    """
    Fetch multiple spools by tag and return their computed SpoolStatus objects.

    Args:
        request: BatchStatusRequest with tags list (1-100 tags).
        sheets_repo: Injected SheetsRepository (singleton, cached).
        worker_service: Injected WorkerService for resolving worker names.

    Returns:
        BatchStatusResponse with found spools and total count.
    """
    try:
        # Build workers lookup once for all spools: {id: "Nombre Apellido"}
        all_workers = worker_service.get_all_active_workers()
        workers_map = {w.id: f"{w.nombre} {w.apellido}" for w in all_workers}

        results: list[SpoolStatus] = []
        errors: list[BatchStatusError] = []
        for tag in request.tags:
            try:
                spool = sheets_repo.get_spool_by_tag(tag)
            except SpoolDataCorruptError as e:
                # B-001/B-002: surface per-tag corruption so the frontend
                # can show a toast instead of silently dropping the card
                # from the list (which used to look like "el spool
                # desapareció").
                logger.warning(
                    f"batch-status: SPOOL_DATA_CORRUPT for {tag!r}: "
                    f"{e.data.get('validation_detail')}"
                )
                errors.append(
                    BatchStatusError(
                        tag_spool=tag,
                        error_code="SPOOL_DATA_CORRUPT",
                        message=(
                            f"El spool '{tag}' tiene datos malformados. "
                            f"Contacta soporte."
                        ),
                    )
                )
                continue
            if spool is not None:
                results.append(SpoolStatus.from_spool(spool, workers=workers_map))

        logger.debug(
            f"batch-status: requested={len(request.tags)} "
            f"found={len(results)} errors={len(errors)}"
        )
        return BatchStatusResponse(
            spools=results, total=len(results), errors=errors
        )

    except SheetsConnectionError:
        logger.error("Sheets connection error in batch_spool_status", exc_info=True)
        raise HTTPException(
            status_code=503,
            detail={"error": "SERVICE_ERROR", "message": "Error al obtener estado de spools. Intenta nuevamente."},
        )
    except Exception as e:
        logger.error(f"Unexpected error in batch_spool_status: {e}", exc_info=True)
        raise HTTPException(
            status_code=503,
            detail={"error": "SERVICE_ERROR", "message": "Error al obtener estado de spools. Intenta nuevamente."},
        )
