"""
History router - Occupation history endpoint.

Provides read-only access to occupation timeline showing which workers
worked on each spool and for how long.
"""

import logging
from fastapi import APIRouter, Depends, status
from typing import Annotated

from backend.services.history_service import HistoryService
from backend.models.history import HistoryResponse
from backend.core.dependency import get_history_service

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get(
    "/history/{tag_spool}",
    response_model=HistoryResponse,
    status_code=status.HTTP_200_OK,
    summary="Get occupation history for a spool",
    description="""
    Retrieve complete occupation history for a spool showing all workers
    who worked on it and for how long.

    Returns chronological list of sessions with:
    - Worker information (name, ID)
    - Operation type (ARM/SOLD/METROLOGIA)
    - Start/end timestamps
    - Duration in human-readable format (e.g., "2h 15m")

    If no history exists (no occupation events), returns empty sessions array.
    """,
    responses={
        200: {
            "description": "Occupation history retrieved successfully",
            "content": {
                "application/json": {
                    "example": {
                        "tag_spool": "MK-1335-CW-25238-011",
                        "sessions": [
                            {
                                "worker_nombre": "MR(93)",
                                "worker_id": 93,
                                "operacion": "ARM",
                                "start_time": "2026-01-27T10:30:00Z",
                                "end_time": "2026-01-27T12:45:00Z",
                                "duration": "2h 15m"
                            }
                        ]
                    }
                }
            }
        },
        404: {
            "description": "Spool not found"
        }
    }
)
async def get_occupation_history(
    tag_spool: str,
    history_service: Annotated[HistoryService, Depends(get_history_service)]
) -> HistoryResponse:
    """
    Get occupation history for a spool.

    Args:
        tag_spool: Spool TAG identifier
        history_service: Injected HistoryService dependency

    Returns:
        HistoryResponse with chronological list of occupation sessions

    Raises:
        SpoolNoEncontradoError: If spool doesn't exist (handled by exception handler → 404)
    """
    logger.info(f"[HISTORY] GET /api/history/{tag_spool}")

    history = await history_service.get_occupation_history(tag_spool)

    logger.info(f"[HISTORY] Retrieved {len(history.sessions)} sessions for {tag_spool}")

    return history
