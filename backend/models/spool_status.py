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


def _resolve_worker_name(raw: str | None, workers: dict[int, str] | None) -> str | None:
    """Resolve 'MR(93)' to 'Mauricio Rodriguez' using workers dict."""
    if not raw:
        return None
    if workers:
        m = re.search(r"\((\d+)\)$", raw)
        if m:
            return workers.get(int(m.group(1)), raw)
    return raw


def _format_short_date(date_val) -> str | None:
    """Format a date to 'DD/MM' (no year). Accepts date objects or strings."""
    if date_val is None:
        return None
    s = str(date_val)  # handles both date objects and strings
    # Try ISO format: YYYY-MM-DD
    m = re.match(r"(\d{4})-(\d{2})-(\d{2})", s)
    if m:
        return f"{m.group(3)}/{m.group(2)}"
    # Try DD-MM-YYYY
    m = re.match(r"(\d{2})-(\d{2})-(\d{4})", s)
    if m:
        return f"{m.group(1)}/{m.group(2)}"
    return s


def _build_completion_history(
    spool: "Spool",
    parsed: dict,
    workers: dict[int, str] | None,
) -> list[dict]:
    """
    Build completion history entries, filtering out redundant info.

    Rules:
    - If ARM EN_PROGRESO and armador == ocupado_por → skip ARM entry (redundant)
    - If SOLD EN_PROGRESO and soldador == ocupado_por → skip SOLD entry (redundant)
    - Otherwise include completed operations with worker name + short date
    """
    entries: list[dict] = []
    op_actual = parsed.get("operacion_actual")
    is_occupied = bool(spool.ocupado_por)

    # ARM history
    if spool.fecha_armado:
        arm_worker = _resolve_worker_name(spool.armador, workers)
        # Skip if ARM is the active operation and same worker is working
        skip_arm = (
            is_occupied
            and op_actual == "ARM"
            and spool.armador == spool.ocupado_por
        )
        if not skip_arm:
            entries.append({
                "operation": "ARM",
                "worker": arm_worker or "—",
                "date": _format_short_date(spool.fecha_armado) or "—",
            })

    # SOLD history
    if spool.fecha_soldadura:
        sold_worker = _resolve_worker_name(spool.soldador, workers)
        skip_sold = (
            is_occupied
            and op_actual == "SOLD"
            and spool.soldador == spool.ocupado_por
        )
        if not skip_sold:
            entries.append({
                "operation": "SOLD",
                "worker": sold_worker or "—",
                "date": _format_short_date(spool.fecha_soldadura) or "—",
            })

    return entries


class CompletionEntry(BaseModel):
    """A single completion history entry for display on SpoolCard."""
    operation: str = Field(..., description="ARM or SOLD")
    worker: str = Field(..., description="Worker display name")
    date: str = Field(..., description="Short date DD/MM")


class SpoolStatus(BaseModel):
    """
    Computed view of a Spool for the v5.0 single-page frontend.

    Pass-through fields come directly from the Spool object.
    Computed fields (operacion_actual, estado_trabajo, ciclo_rep) are
    derived from factual spool columns via _derive_estado().
    completion_history is computed to avoid redundant display logic in frontend.
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

    # Completion history — computed, filtered, formatted by backend
    completion_history: list[CompletionEntry] = Field(
        default_factory=list,
        description="Completed operations to display (redundant entries filtered out)"
    )

    # Legacy pass-through (kept for backward compat, may be removed later)
    fecha_armado: Optional[str] = Field(None)
    armador_display: Optional[str] = Field(None)
    fecha_soldadura: Optional[str] = Field(None)
    soldador_display: Optional[str] = Field(None)

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

        ocupado_por_display = _resolve_worker_name(spool.ocupado_por, workers)
        armador_display = _resolve_worker_name(spool.armador, workers)
        soldador_display = _resolve_worker_name(spool.soldador, workers)

        history = _build_completion_history(spool, parsed, workers)

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
            completion_history=[CompletionEntry(**e) for e in history],
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
