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

from backend.core.dependency import get_sheets_repository
from backend.repositories.sheets_repository import SheetsRepository
from backend.models.spool_status import (
    SpoolStatus,
    BatchStatusRequest,
    BatchStatusResponse,
)

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
) -> SpoolStatus:
    """
    Fetch a spool by tag and return its computed SpoolStatus.

    Args:
        tag: The spool TAG_SPOOL identifier.
        sheets_repo: Injected SheetsRepository (singleton, cached).

    Returns:
        SpoolStatus with pass-through and computed fields.

    Raises:
        HTTPException(404): If no spool with the given tag exists.
    """
    spool = sheets_repo.get_spool_by_tag(tag)
    if spool is None:
        logger.info(f"Spool not found for status request: tag={tag!r}")
        raise HTTPException(status_code=404, detail=f"Spool {tag} not found")
    return SpoolStatus.from_spool(spool)


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
) -> BatchStatusResponse:
    """
    Fetch multiple spools by tag and return their computed SpoolStatus objects.

    Args:
        request: BatchStatusRequest with tags list (1-100 tags).
        sheets_repo: Injected SheetsRepository (singleton, cached).

    Returns:
        BatchStatusResponse with found spools and total count.
    """
    results: list[SpoolStatus] = []
    for tag in request.tags:
        spool = sheets_repo.get_spool_by_tag(tag)
        if spool is not None:
            results.append(SpoolStatus.from_spool(spool))

    logger.debug(
        f"batch-status: requested={len(request.tags)} found={len(results)}"
    )
    return BatchStatusResponse(spools=results, total=len(results))
