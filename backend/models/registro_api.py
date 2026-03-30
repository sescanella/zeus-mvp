"""
Response models for Mi Registro (worker daily production log).

Pieza 2: Allows workers to consult their daily union work records,
replacing the paper-based tracking system.
"""
from pydantic import BaseModel
from typing import Optional


class WorkerUnionRecord(BaseModel):
    n_union: int
    dn_union: Optional[float] = None
    tipo_union: Optional[str] = None
    fecha_inicio: Optional[str] = None
    fecha_fin: Optional[str] = None


class SpoolGroup(BaseModel):
    tag_spool: str
    operacion: str  # "ARM" or "SOLD"
    uniones: list[WorkerUnionRecord]
    pd_total: float  # sum(dn_union)
    otro_trabajador: Optional[str] = None  # the other worker. "Pendiente" if not assigned yet


class RegistroResumen(BaseModel):
    fecha: str
    pd_total: float
    total_uniones: int
    total_spools: int


class RegistroResponse(BaseModel):
    worker_id: int
    worker_nombre: str
    fecha: str
    resumen: RegistroResumen
    spools: list[SpoolGroup]
