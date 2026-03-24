"""
SpoolStatus model and batch request/response models for v5.0 single-page frontend.

SpoolStatus wraps a Spool object and adds three computed fields:
operacion_actual, estado_trabajo, ciclo_rep.

State derivation strategy (v5.1):
  - estado_trabajo and operacion_actual are derived from FACTUAL columns
    (ocupado_por, fecha_armado, fecha_soldadura, fecha_qc_metrologia)
  - estado_detalle is passed through as-is for admin/debug display only
  - estado_detalle is ONLY used for reparacion/bloqueado detection (cycle info)
    since those states have no dedicated column — they embed in estado_detalle

These models are consumed by:
  - GET /api/spool/{tag}/status
  - POST /api/spools/batch-status
"""
from __future__ import annotations

import re
from typing import TYPE_CHECKING, Optional

from pydantic import BaseModel, Field

if TYPE_CHECKING:
    from backend.models.spool import Spool


def _derive_estado(spool: "Spool") -> dict:
    """
    Derive estado_trabajo and operacion_actual from factual spool columns.

    Priority order (first match wins):
    1. BLOQUEADO — estado_detalle contains "BLOQUEADO"
    2. RECHAZADO — estado_detalle contains "RECHAZADO"
    3. EN_REPARACION — estado_detalle contains "EN_REPARACION" + occupied
    4. PENDIENTE_METROLOGIA — estado_detalle contains "PENDIENTE_METROLOGIA"
       or (ARM+SOLD done, metrologia not done, not occupied)
    5. COMPLETADO — fecha_armado + fecha_soldadura + fecha_qc_metrologia all set
    6. EN_PROGRESO — ocupado_por is set
    7. LIBRE — default

    For states 1-4, estado_detalle is the only source (no dedicated columns).
    For states 5-7, factual columns are the sole authority.
    """
    ed = (spool.estado_detalle or "").strip()
    is_occupied = bool(spool.ocupado_por)
    arm_done = spool.fecha_armado is not None
    sold_done = spool.fecha_soldadura is not None
    met_done = spool.fecha_qc_metrologia is not None

    result: dict = {
        "operacion_actual": None,
        "estado_trabajo": "LIBRE",
        "ciclo_rep": None,
    }

    # 1. BLOQUEADO (only in estado_detalle)
    if "BLOQUEADO" in ed:
        result["estado_trabajo"] = "BLOQUEADO"
        return result

    # 2. RECHAZADO with cycle (only in estado_detalle)
    m = re.search(r"RECHAZADO.*?Ciclo\s+(\d+)/3", ed)
    if m:
        result["estado_trabajo"] = "RECHAZADO"
        result["ciclo_rep"] = int(m.group(1))
        return result
    if "RECHAZADO" in ed:
        result["estado_trabajo"] = "RECHAZADO"
        return result

    # 3. EN_REPARACION (only in estado_detalle)
    m = re.search(r"EN_REPARACION.*?Ciclo\s+(\d+)/3", ed)
    if m:
        result["operacion_actual"] = "REPARACION"
        result["estado_trabajo"] = "EN_PROGRESO"
        result["ciclo_rep"] = int(m.group(1))
        return result

    # 4. PENDIENTE_METROLOGIA (estado_detalle or factual)
    if "PENDIENTE_METROLOGIA" in ed or "REPARACION completado" in ed:
        result["estado_trabajo"] = "PENDIENTE_METROLOGIA"
        return result
    if arm_done and sold_done and not met_done and not is_occupied:
        result["estado_trabajo"] = "PENDIENTE_METROLOGIA"
        return result

    # 5. COMPLETADO — all three phases done
    if arm_done and sold_done and met_done:
        result["estado_trabajo"] = "COMPLETADO"
        return result

    # 6. EN_PROGRESO — occupied by a worker
    if is_occupied:
        result["estado_trabajo"] = "EN_PROGRESO"
        # Determine which operation from estado_detalle hint
        m_op = re.search(r"trabajando\s+(ARM|SOLD)", ed)
        if m_op:
            result["operacion_actual"] = m_op.group(1)
        elif not arm_done:
            result["operacion_actual"] = "ARM"
        elif not sold_done:
            result["operacion_actual"] = "SOLD"
        return result

    # 7. LIBRE — default
    return result


class SpoolStatus(BaseModel):
    """
    Computed view of a Spool for the v5.0 single-page frontend.

    Pass-through fields come directly from the Spool object.
    Computed fields (operacion_actual, estado_trabajo, ciclo_rep) are
    derived from factual spool columns via _derive_estado().
    """

    # Pass-through identity / state fields
    tag_spool: str = Field(..., description="TAG unico del spool")
    nv: Optional[str] = Field(
        None, description="Numero de Nota de Venta"
    )
    ocupado_por: Optional[str] = Field(
        None, description="Trabajador que ocupa el spool (formato 'MR(93)')"
    )
    ocupado_por_display: Optional[str] = Field(
        None, description="Nombre completo del trabajador (ej: 'Mauricio Rodriguez')"
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

    # Completion history (pass-through from Spool)
    fecha_armado: Optional[str] = Field(
        None, description="Fecha de completado ARM (DD-MM-YYYY or None)"
    )
    armador_display: Optional[str] = Field(
        None, description="Nombre completo del armador (ej: 'Mauricio Rodriguez')"
    )
    fecha_soldadura: Optional[str] = Field(
        None, description="Fecha de completado SOLD (DD-MM-YYYY or None)"
    )
    soldador_display: Optional[str] = Field(
        None, description="Nombre completo del soldador (ej: 'Carlos Pimiento')"
    )

    # Computed fields (derived from factual columns via _derive_estado)
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
    def from_spool(
        cls, spool: "Spool", workers: dict[int, str] | None = None
    ) -> "SpoolStatus":
        """
        Build a SpoolStatus from a Spool object.

        Calls _derive_estado() to derive computed fields from
        factual spool columns. The source Spool is not mutated.

        Args:
            spool: A Spool object (frozen Pydantic model).
            workers: Optional mapping of worker_id -> "Nombre Apellido"
                for resolving ocupado_por_display.

        Returns:
            SpoolStatus with all pass-through and computed fields populated.
        """
        parsed = _derive_estado(spool)

        # Resolve ocupado_por_display from workers dict
        ocupado_por_display: str | None = None
        if spool.ocupado_por and workers:
            match = re.search(r"\((\d+)\)$", spool.ocupado_por)
            if match:
                worker_id = int(match.group(1))
                ocupado_por_display = workers.get(worker_id, spool.ocupado_por)
            else:
                ocupado_por_display = spool.ocupado_por
        elif spool.ocupado_por:
            ocupado_por_display = spool.ocupado_por

        # Resolve armador_display from workers dict
        armador_display: str | None = None
        if spool.armador and workers:
            match_arm = re.search(r"\((\d+)\)$", spool.armador)
            if match_arm:
                arm_id = int(match_arm.group(1))
                armador_display = workers.get(arm_id, spool.armador)
            else:
                armador_display = spool.armador
        elif spool.armador:
            armador_display = spool.armador

        # Resolve soldador_display from workers dict
        soldador_display: str | None = None
        if spool.soldador and workers:
            match_sol = re.search(r"\((\d+)\)$", spool.soldador)
            if match_sol:
                sol_id = int(match_sol.group(1))
                soldador_display = workers.get(sol_id, spool.soldador)
            else:
                soldador_display = spool.soldador
        elif spool.soldador:
            soldador_display = spool.soldador

        return cls(
            tag_spool=spool.tag_spool,
            nv=spool.nv,
            ocupado_por=spool.ocupado_por,
            ocupado_por_display=ocupado_por_display,
            fecha_ocupacion=spool.fecha_ocupacion,
            estado_detalle=spool.estado_detalle,
            total_uniones=spool.total_uniones,
            uniones_arm_completadas=spool.uniones_arm_completadas,
            uniones_sold_completadas=spool.uniones_sold_completadas,
            pulgadas_arm=spool.pulgadas_arm,
            pulgadas_sold=spool.pulgadas_sold,
            fecha_armado=str(spool.fecha_armado) if spool.fecha_armado else None,
            armador_display=armador_display,
            fecha_soldadura=str(spool.fecha_soldadura) if spool.fecha_soldadura else None,
            soldador_display=soldador_display,
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
