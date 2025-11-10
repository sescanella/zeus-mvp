"""
Modelos Pydantic para Acciones (iniciar/completar operaciones).
"""
from pydantic import BaseModel, Field, field_validator, ConfigDict
from typing import Optional
from datetime import datetime
from .enums import ActionType


class ActionRequest(BaseModel):
    """
    Request body para iniciar o completar una acción.

    Utilizado por los endpoints POST /api/iniciar-accion y POST /api/completar-accion
    """
    worker_nombre: str = Field(
        ...,
        description="Nombre completo del trabajador (debe coincidir con BC/BE para completar)",
        min_length=1,
        examples=["Juan Pérez"]
    )
    operacion: ActionType = Field(
        ...,
        description="Tipo de operación a realizar (ARM o SOLD)"
    )
    tag_spool: str = Field(
        ...,
        description="TAG único del spool",
        min_length=1,
        examples=["MK-1335-CW-25238-011"]
    )
    timestamp: Optional[datetime] = Field(
        None,
        description="Timestamp para completar acción (default: now())",
        examples=["2025-11-08T14:30:00Z"]
    )

    @field_validator('timestamp', mode='before')
    @classmethod
    def set_timestamp_default(cls, v):
        """Si no se provee timestamp, usar datetime.now()."""
        return v or datetime.now()

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "worker_nombre": "Juan Pérez",
                    "operacion": "ARM",
                    "tag_spool": "MK-1335-CW-25238-011"
                },
                {
                    "worker_nombre": "María González",
                    "operacion": "SOLD",
                    "tag_spool": "MK-1335-CW-25238-012",
                    "timestamp": "2025-11-08T14:30:00Z"
                }
            ]
        }
    )


class ActionMetadata(BaseModel):
    """Metadata de la acción realizada (para response)."""
    armador: Optional[str] = Field(None, description="Armador asignado (si aplica)")
    soldador: Optional[str] = Field(None, description="Soldador asignado (si aplica)")
    fecha_armado: Optional[str] = Field(None, description="Fecha de armado completado (si aplica)")
    fecha_soldadura: Optional[str] = Field(None, description="Fecha de soldadura completada (si aplica)")


class ActionData(BaseModel):
    """Datos de la acción realizada (para response)."""
    tag_spool: str = Field(..., description="TAG del spool procesado")
    operacion: str = Field(..., description="Operación realizada (ARM/SOLD)")
    trabajador: str = Field(..., description="Trabajador que realizó la acción")
    fila_actualizada: int = Field(..., description="Número de fila actualizada en Sheets", ge=1)
    columna_actualizada: str = Field(..., description="Letra de columna actualizada (V/W)")
    valor_nuevo: float = Field(..., description="Nuevo valor (0.1 o 1.0)")
    metadata_actualizada: ActionMetadata = Field(..., description="Metadata actualizada")


class ActionResponse(BaseModel):
    """Response exitosa de una acción (iniciar o completar)."""
    success: bool = Field(True, description="Indica si la operación fue exitosa")
    message: str = Field(..., description="Mensaje legible para el usuario")
    data: ActionData = Field(..., description="Datos de la operación realizada")

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "success": True,
                    "message": "Acción ARM iniciada exitosamente. Spool asignado a Juan Pérez",
                    "data": {
                        "tag_spool": "MK-1335-CW-25238-011",
                        "operacion": "ARM",
                        "trabajador": "Juan Pérez",
                        "fila_actualizada": 25,
                        "columna_actualizada": "V",
                        "valor_nuevo": 0.1,
                        "metadata_actualizada": {
                            "armador": "Juan Pérez",
                            "soldador": None,
                            "fecha_armado": None,
                            "fecha_soldadura": None
                        }
                    }
                },
                {
                    "success": True,
                    "message": "Acción ARM completada exitosamente",
                    "data": {
                        "tag_spool": "MK-1335-CW-25238-011",
                        "operacion": "ARM",
                        "trabajador": "Juan Pérez",
                        "fila_actualizada": 25,
                        "columna_actualizada": "V",
                        "valor_nuevo": 1.0,
                        "metadata_actualizada": {
                            "armador": None,
                            "soldador": None,
                            "fecha_armado": "2025-11-08",
                            "fecha_soldadura": None
                        }
                    }
                }
            ]
        }
    )
