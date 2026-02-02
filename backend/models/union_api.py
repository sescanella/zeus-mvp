"""
API response models for union query endpoints (v4.0).

These models provide read-only views of union data optimized for frontend consumption.
Separates API contract from internal Union domain model.
"""
from pydantic import BaseModel, Field
from typing import List


class UnionSummary(BaseModel):
    """
    Minimal union data for disponibles query.

    Contains only the 4 core fields needed for union selection UI.
    Lightweight response (no timestamps, no audit fields).
    """
    id: str = Field(
        ...,
        description="Composite ID: TAG_SPOOL+N_UNION (e.g., 'OT-123+5')"
    )
    n_union: int = Field(
        ...,
        description="Union number (1-20)",
        ge=1,
        le=20
    )
    dn_union: float = Field(
        ...,
        description="Diameter in inches",
        gt=0
    )
    tipo_union: str = Field(
        ...,
        description="Union type: BW, BR, SO, FW, FILL, LET, etc."
    )


class DisponiblesResponse(BaseModel):
    """
    Response for GET /api/v4/uniones/{tag}/disponibles endpoint.

    Returns list of available unions for a given operation (ARM or SOLD).
    Includes count for quick frontend display (e.g., "5 unions available").
    """
    tag_spool: str = Field(
        ...,
        description="Spool tag that owns these unions"
    )
    operacion: str = Field(
        ...,
        description="Operation type: ARM or SOLD"
    )
    unions: List[UnionSummary] = Field(
        default_factory=list,
        description="List of available unions (empty if none)"
    )
    count: int = Field(
        ...,
        description="Total available unions (same as len(unions), provided for convenience)",
        ge=0
    )


class MetricasResponse(BaseModel):
    """
    Response for GET /api/v4/uniones/{tag}/metricas endpoint.

    Spool-level metrics with exactly 5 fields per CONTEXT.md specification.
    Provides completion counts and pulgadas-diámetro business metric.

    Used for:
    - Dashboard progress display (7/10 ARM complete)
    - Performance tracking (18.50 pulgadas ARM)
    - Completion validation (auto PAUSAR vs COMPLETAR)
    """
    tag_spool: str = Field(
        ...,
        description="Spool tag for these metrics"
    )
    total_uniones: int = Field(
        ...,
        description="Total union count (all unions regardless of status)",
        ge=0
    )
    arm_completadas: int = Field(
        ...,
        description="Count of unions where ARM_FECHA_FIN is not NULL",
        ge=0
    )
    sold_completadas: int = Field(
        ...,
        description="Count of unions where SOL_FECHA_FIN is not NULL",
        ge=0
    )
    pulgadas_arm: float = Field(
        ...,
        description="Sum of DN_UNION for completed ARM unions (2 decimal precision)",
        ge=0
    )
    pulgadas_sold: float = Field(
        ...,
        description="Sum of DN_UNION for completed SOLD unions (2 decimal precision)",
        ge=0
    )
