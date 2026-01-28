"""
Pydantic models for Metrología instant completion workflow.

Phase 5 feature - Binary inspection results (APROBADO/RECHAZADO) without occupation.
"""

from enum import Enum
from pydantic import BaseModel, Field, ConfigDict


class ResultadoEnum(str, Enum):
    """
    Binary inspection outcome enum.

    Values:
        APROBADO: Quality inspection passed
        RECHAZADO: Quality inspection failed (rework required)
    """
    APROBADO = "APROBADO"
    RECHAZADO = "RECHAZADO"


class CompletarMetrologiaRequest(BaseModel):
    """
    Request body for instant metrología completion.

    Used by POST /api/metrologia/completar endpoint.
    Single-action inspection with binary outcome.

    Attributes:
        tag_spool: Spool identifier
        worker_id: Inspector worker ID
        resultado: Binary inspection result (APROBADO/RECHAZADO)
    """
    tag_spool: str = Field(
        ...,
        description="TAG único del spool a inspeccionar",
        min_length=1,
        examples=["MK-1335-CW-25238-011"]
    )
    worker_id: int = Field(
        ...,
        description="ID del inspector (trabajador con rol METROLOGIA)",
        gt=0,
        examples=[93, 94, 95]
    )
    resultado: ResultadoEnum = Field(
        ...,
        description="Resultado de la inspección (APROBADO o RECHAZADO)",
        examples=["APROBADO", "RECHAZADO"]
    )

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "tag_spool": "MK-1335-CW-25238-011",
                    "worker_id": 93,
                    "resultado": "APROBADO"
                },
                {
                    "tag_spool": "MK-1335-CW-25238-012",
                    "worker_id": 94,
                    "resultado": "RECHAZADO"
                }
            ]
        }
    )


class CompletarMetrologiaResponse(BaseModel):
    """
    Response body for metrología completion.

    Returns success status, resultado, and human-readable estado_detalle.

    Attributes:
        success: Whether operation succeeded
        tag_spool: Spool identifier
        resultado: Inspection result (APROBADO/RECHAZADO)
        estado_detalle: Human-readable status for Estado_Detalle column
        message: Success/error message
    """
    success: bool = Field(
        ...,
        description="Whether the operation succeeded"
    )
    tag_spool: str = Field(
        ...,
        description="TAG del spool inspeccionado"
    )
    resultado: str = Field(
        ...,
        description="Resultado de la inspección"
    )
    estado_detalle: str = Field(
        ...,
        description="Estado legible para columna Estado_Detalle"
    )
    message: str = Field(
        ...,
        description="Mensaje descriptivo del resultado"
    )

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "success": True,
                    "tag_spool": "MK-1335-CW-25238-011",
                    "resultado": "APROBADO",
                    "estado_detalle": "Disponible - ARM completado, SOLD completado, METROLOGIA APROBADO ✓",
                    "message": "Metrología APROBADO para spool MK-1335-CW-25238-011"
                },
                {
                    "success": True,
                    "tag_spool": "MK-1335-CW-25238-012",
                    "resultado": "RECHAZADO",
                    "estado_detalle": "Disponible - ARM completado, SOLD completado, METROLOGIA RECHAZADO - Pendiente reparación",
                    "message": "Metrología RECHAZADO para spool MK-1335-CW-25238-012"
                }
            ]
        }
    )
