"""
Admin Router — manual override knobs for the operator.

For now exposes a single endpoint to invalidate ColumnMapCache and force
the next read to rebuild from a fresh header. Useful as a safety valve in
case the operator wants to force a refresh before the auto-detection
catches up.

Endpoints:
- POST /api/admin/invalidate-column-cache?sheet=Operaciones

TODO(security): the rest of the backend has no auth layer either, so for
v1 this endpoint is unprotected. Once auth is added across the API, wrap
this with the same gate.
"""
import logging
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query

from backend.core.column_map_cache import ColumnMapCache
from backend.core.dependency import get_sheets_repository
from backend.core.sheet_schema import ALL_SCHEMAS
from backend.repositories.sheets_repository import SheetsRepository

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post(
    "/admin/invalidate-column-cache",
    summary="Invalidate cached column map for a sheet and force a rebuild",
    description=(
        "Drops the in-memory column-name→index mapping for the requested "
        "sheet, then immediately rebuilds it by reading the current header "
        "row. Useful when the operator already knows the sheet structure "
        "changed and wants to refresh without waiting for the auto-detect "
        "hash check on the next read. Returns 503 if a critical column is "
        "missing after rebuild."
    ),
    tags=["Admin"],
)
async def invalidate_column_cache(
    sheets_repo: Annotated[SheetsRepository, Depends(get_sheets_repository)],
    sheet: str = Query(
        default="Operaciones",
        description="Name of the worksheet (must be declared in sheet_schema.py).",
    ),
):
    if sheet not in ALL_SCHEMAS:
        raise HTTPException(
            status_code=400,
            detail=(
                f"Unknown sheet '{sheet}'. Known sheets: "
                f"{sorted(ALL_SCHEMAS.keys())}."
            ),
        )

    ColumnMapCache.invalidate(sheet)
    # Also drop the row cache so the next read goes to Sheets and the
    # rebuild is based on a header that Google Sheets just confirmed.
    sheets_repo._cache.invalidate(f"worksheet:{sheet}")

    # Force immediate rebuild + validation so any critical drift surfaces
    # now (with a 503) instead of on the next user-facing request.
    new_map = ColumnMapCache.get_or_build(sheet, sheets_repo)
    ok, drifts = ColumnMapCache.validate_critical_columns_strict(
        sheet, sorted(ALL_SCHEMAS[sheet].critical_columns)
    )

    logger.info(
        f"Admin invalidate-column-cache for '{sheet}': "
        f"{len(new_map)} entries, critical_ok={ok}, drifts={drifts}"
    )

    return {
        "sheet": sheet,
        "invalidated": True,
        "column_count": len(new_map),
        "critical_ok": ok,
        "drifts": drifts,
        "header_hash": ColumnMapCache.get_header_hash(sheet),
    }
