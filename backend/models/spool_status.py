"""
SpoolStatus model and batch request/response models for v5.0 single-page frontend.

SpoolStatus wraps a Spool object and adds three computed fields derived from
the Estado_Detalle string: operacion_actual, estado_trabajo, ciclo_rep.

These models are consumed by:
  - GET /api/spool/{tag}/status
  - POST /api/spools/batch-status

Reference:
- Plan: 00-01-PLAN.md (API-01, API-02)
- Research: 00-RESEARCH.md Pattern 2
"""
from __future__ import annotations

from typing import TYPE_CHECKING, Optional

from pydantic import BaseModel, Field

from backend.services.estado_detalle_parser import parse_estado_detalle

if TYPE_CHECKING:
    from backend.models.spool import Spool


class SpoolStatus(BaseModel):
    """
    Computed view of a Spool for the v5.0 single-page frontend.

    Pass-through fields come directly from the Spool object.
    Computed fields (operacion_actual, estado_trabajo, ciclo_rep) are
    derived from the Estado_Detalle string via parse_estado_detalle().
    """

    # Pass-through identity / state fields
    tag_spool: str = Field(..., description="TAG unico del spool")
    ocupado_por: Optional[str] = Field(
        None, description="Trabajador que ocupa el spool (formato 'MR(93)')"
    )
    fecha_ocupacion: Optional[str] = Field(
        None, description="Timestamp cuando fue ocupado (DD-MM-YYYY HH:MM:SS)"
    )
    estado_detalle: Optional[str] = Field(
        None, description="String Estado_Detalle crudo de la columna 67"
    )
    total_uniones: Optional[int] = Field(None, description="Total uniones en el spool", ge=0)
    uniones_arm_completadas: Optional[int] = Field(
        None, description="Uniones con ARM completado", ge=0
    )
    uniones_sold_completadas: Optional[int] = Field(
        None, description="Uniones con SOLD completado", ge=0
    )
    pulgadas_arm: Optional[float] = Field(
        None, description="Suma DN_UNION para ARM completado", ge=0.0
    )
    pulgadas_sold: Optional[float] = Field(
        None, description="Suma DN_UNION para SOLD completado", ge=0.0
    )

    # Computed fields (derived from estado_detalle via parse_estado_detalle)
    operacion_actual: Optional[str] = Field(
        None,
        description="Operacion en progreso: 'ARM' | 'SOLD' | 'REPARACION' | None"
    )
    estado_trabajo: Optional[str] = Field(
        None,
        description=(
            "Estado del spool: 'LIBRE' | 'EN_PROGRESO' | 'PAUSADO' | 'COMPLETADO'"
            " | 'RECHAZADO' | 'BLOQUEADO' | 'PENDIENTE_METROLOGIA'"
        )
    )
    ciclo_rep: Optional[int] = Field(
        None,
        description="Ciclo de reparacion (1-3) para RECHAZADO/REPARACION, None en otros casos"
    )

    @classmethod
    def from_spool(cls, spool: "Spool") -> "SpoolStatus":
        """
        Build a SpoolStatus from a Spool object.

        Calls parse_estado_detalle() to derive computed fields from
        the Estado_Detalle string. The source Spool is not mutated.

        Args:
            spool: A Spool object (frozen Pydantic model).

        Returns:
            SpoolStatus with all pass-through and computed fields populated.
        """
        parsed = parse_estado_detalle(spool.estado_detalle)
        return cls(
            tag_spool=spool.tag_spool,
            ocupado_por=spool.ocupado_por,
            fecha_ocupacion=spool.fecha_ocupacion,
            estado_detalle=spool.estado_detalle,
            total_uniones=spool.total_uniones,
            uniones_arm_completadas=spool.uniones_arm_completadas,
            uniones_sold_completadas=spool.uniones_sold_completadas,
            pulgadas_arm=spool.pulgadas_arm,
            pulgadas_sold=spool.pulgadas_sold,
            operacion_actual=parsed.get("operacion_actual"),
            estado_trabajo=parsed.get("estado_trabajo"),
            ciclo_rep=parsed.get("ciclo_rep"),
        )


class BatchStatusRequest(BaseModel):
    """
    Request body for POST /api/spools/batch-status.

    Accepts a list of spool tags (1-100). The backend resolves each tag
    independently using the cached SheetsRepository.
    """

    tags: list[str] = Field(
        ...,
        min_length=1,
        max_length=100,
        description="Lista de TAG_SPOOL a consultar (1 a 100 tags)"
    )


class BatchStatusResponse(BaseModel):
    """
    Response for POST /api/spools/batch-status.

    Returns only the spools that were found. Tags not found in Sheets are
    silently omitted. Use the total field to detect missing spools.
    """

    spools: list[SpoolStatus] = Field(..., description="Lista de SpoolStatus encontrados")
    total: int = Field(..., description="Cantidad de spools encontrados", ge=0)
