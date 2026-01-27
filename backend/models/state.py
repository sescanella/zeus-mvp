"""
Modelos Pydantic para operaciones de estado de spools (v3.0).

Extiende los modelos de occupation con estado de operaciones ARM/SOLD.
"""
from pydantic import BaseModel, Field
from typing import Optional


class StateTransitionRequest(BaseModel):
    """
    Request base para transiciones de estado.

    Utilizado internamente por StateService para coordinar transiciones.
    """
    tag_spool: str = Field(
        ...,
        description="TAG único del spool",
        min_length=1
    )
    worker_nombre: str = Field(
        ...,
        description="Nombre completo del trabajador (formato: INICIALES(ID))",
        min_length=1
    )
    operacion: str = Field(
        ...,
        description="Operación (ARM/SOLD/METROLOGIA)"
    )


class StateInfo(BaseModel):
    """
    Información de estado de una operación.

    Representa el estado actual de una operación en su state machine.
    """
    operacion: str = Field(..., description="Tipo de operación (ARM/SOLD)")
    estado: str = Field(..., description="Estado actual (pendiente/en_progreso/completado)")
    trabajador_actual: Optional[str] = Field(None, description="Trabajador asignado si en progreso")
    fecha_completado: Optional[str] = Field(None, description="Fecha de completado si completado")


class CombinedSpoolState(BaseModel):
    """
    Estado combinado de un spool (ocupación + operaciones).

    Representa el estado completo de un spool incluyendo:
    - Estado de ocupación (Redis lock)
    - Estado de operaciones ARM/SOLD (state machines)
    - Estado_Detalle display string
    """
    tag_spool: str = Field(..., description="TAG del spool")
    ocupado: bool = Field(..., description="Si el spool está ocupado (Redis lock)")
    ocupado_por: Optional[str] = Field(None, description="Worker que ocupa el spool")
    arm_estado: StateInfo = Field(..., description="Estado de operación ARM")
    sold_estado: StateInfo = Field(..., description="Estado de operación SOLD")
    estado_detalle: str = Field(..., description="Display string combinado")
