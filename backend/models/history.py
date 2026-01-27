"""
Models for occupation history endpoint.

Represents worker occupation sessions extracted from Metadata events.
"""

from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime


class OccupationSession(BaseModel):
    """
    A single occupation session for a worker on a spool.

    Represents the time period from TOMAR_SPOOL to PAUSAR/COMPLETAR.
    """
    worker_nombre: str = Field(
        ...,
        description="Worker name in format INICIALES(ID)",
        examples=["MR(93)", "JP(94)"]
    )
    worker_id: int = Field(
        ...,
        description="Worker ID",
        gt=0,
        examples=[93, 94]
    )
    operacion: str = Field(
        ...,
        description="Operation (ARM/SOLD/METROLOGIA)",
        pattern="^(ARM|SOLD|METROLOGIA)$",
        examples=["ARM", "SOLD"]
    )
    start_time: datetime = Field(
        ...,
        description="Session start timestamp (TOMAR event)",
        examples=["2026-01-27T10:30:00Z"]
    )
    end_time: Optional[datetime] = Field(
        None,
        description="Session end timestamp (PAUSAR/COMPLETAR event), None if still in progress",
        examples=["2026-01-27T12:45:00Z"]
    )
    duration: Optional[str] = Field(
        None,
        description="Human-readable duration (e.g., '2h 15m'), None if still in progress",
        examples=["2h 15m", "45m", None]
    )


class HistoryResponse(BaseModel):
    """
    Complete occupation history for a spool.

    Contains all worker sessions showing who worked on the spool and for how long.
    """
    tag_spool: str = Field(
        ...,
        description="Spool TAG identifier",
        examples=["MK-1335-CW-25238-011"]
    )
    sessions: List[OccupationSession] = Field(
        default_factory=list,
        description="Chronological list of occupation sessions"
    )

    model_config = {
        "json_schema_extra": {
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
                    },
                    {
                        "worker_nombre": "JP(94)",
                        "worker_id": 94,
                        "operacion": "ARM",
                        "start_time": "2026-01-27T13:00:00Z",
                        "end_time": None,
                        "duration": None
                    }
                ]
            }
        }
    }
