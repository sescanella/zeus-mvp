"""
Notas Router — F-1 Spool notes (v5.1).

Endpoints:
- GET /api/spool/{tag}/notas — read current Notas cell content
- POST /api/spool/{tag}/notas — append a new dated entry to Notas

Append-only: previous history is never overwritten. Every append is
audited in the Metadata sheet as NOTAS_ACTUALIZADA event.
"""

import logging

from fastapi import APIRouter, Depends, status
from pydantic import BaseModel, Field

from backend.core.dependency import get_notas_service
from backend.services.notas_service import NotasService

logger = logging.getLogger(__name__)
router = APIRouter()


class NotaReadResponse(BaseModel):
    """Response for GET notas."""

    tag_spool: str
    nota: str  # empty string if never written


class NotaAppendRequest(BaseModel):
    """Request body for POST notas."""

    worker_id: int = Field(..., gt=0, description="ID del trabajador autor de la nota")
    texto: str = Field(
        ...,
        min_length=1,
        max_length=500,
        description="Contenido de la nota (sin prefijo de fecha)",
    )


class NotaAppendResponse(BaseModel):
    """Response for POST notas — returns full updated content."""

    success: bool
    tag_spool: str
    nota: str  # full content after the append


@router.get(
    "/spool/{tag_spool}/notas",
    response_model=NotaReadResponse,
    status_code=status.HTTP_200_OK,
)
async def get_notas(
    tag_spool: str,
    notas_service: NotasService = Depends(get_notas_service),
):
    """Read the current content of the `Notas` cell for a spool.

    Returns empty string if the cell has never been written.

    Raises:
        HTTPException 404: Spool not found
    """
    logger.info(f"GET /api/spool/{tag_spool}/notas")
    nota = notas_service.get_nota(tag_spool)
    return NotaReadResponse(tag_spool=tag_spool, nota=nota)


@router.post(
    "/spool/{tag_spool}/notas",
    response_model=NotaAppendResponse,
    status_code=status.HTTP_200_OK,
)
async def append_nota(
    tag_spool: str,
    request: NotaAppendRequest,
    notas_service: NotasService = Depends(get_notas_service),
):
    """Append a new dated entry to the `Notas` cell of a spool.

    The stored entry is prefixed with `YYYYMMDD:` (Chile timezone),
    matching the convention already used by planning team. Previous
    content is preserved — new entry is appended with a newline.

    Raises:
        HTTPException 404: Spool or worker not found
        HTTPException 422: Pydantic validation (empty text, worker_id <= 0)
    """
    logger.info(
        f"POST /api/spool/{tag_spool}/notas - worker_id={request.worker_id}, "
        f"text_length={len(request.texto)}"
    )
    new_content = notas_service.append_nota(
        tag_spool=tag_spool,
        worker_id=request.worker_id,
        texto=request.texto,
    )
    return NotaAppendResponse(success=True, tag_spool=tag_spool, nota=new_content)
