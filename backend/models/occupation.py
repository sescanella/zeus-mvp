"""
Modelos Pydantic para operaciones de ocupación de spools (v3.0).

Soporta TOMAR/PAUSAR/COMPLETAR con validación de ownership y batch operations.
"""
from pydantic import BaseModel, Field, field_validator, ConfigDict
from typing import Optional
from datetime import datetime, date
from .enums import ActionType


class TomarRequest(BaseModel):
    """
    Request body para tomar un spool (iniciar ocupación).

    Utilizado por endpoint POST /api/occupation/tomar.
    """
    tag_spool: str = Field(
        ...,
        description="TAG único del spool a ocupar",
        min_length=1,
        examples=["MK-1335-CW-25238-011"]
    )
    worker_id: int = Field(
        ...,
        description="ID del trabajador que toma el spool",
        gt=0,
        examples=[93, 94, 95]
    )
    worker_nombre: str = Field(
        ...,
        description="Nombre completo del trabajador (formato: INICIALES(ID))",
        min_length=1,
        examples=["MR(93)", "JP(94)"]
    )
    operacion: ActionType = Field(
        ...,
        description="Operación a realizar (ARM/SOLD/METROLOGIA)"
    )

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "tag_spool": "MK-1335-CW-25238-011",
                    "worker_id": 93,
                    "worker_nombre": "MR(93)",
                    "operacion": "ARM"
                }
            ]
        }
    )


class PausarRequest(BaseModel):
    """
    Request body para pausar trabajo en un spool.

    Utilizado por endpoint POST /api/occupation/pausar.
    """
    tag_spool: str = Field(
        ...,
        description="TAG único del spool a pausar",
        min_length=1,
        examples=["MK-1335-CW-25238-011"]
    )
    worker_id: int = Field(
        ...,
        description="ID del trabajador que pausa (debe ser el owner)",
        gt=0,
        examples=[93, 94, 95]
    )
    worker_nombre: str = Field(
        ...,
        description="Nombre completo del trabajador",
        min_length=1,
        examples=["MR(93)", "JP(94)"]
    )
    operacion: ActionType = Field(
        ...,
        description="Operación que se está pausando (ARM/SOLD)"
    )

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "tag_spool": "MK-1335-CW-25238-011",
                    "worker_id": 93,
                    "worker_nombre": "MR(93)",
                    "operacion": "ARM"
                }
            ]
        }
    )


class CompletarRequest(BaseModel):
    """
    Request body para completar trabajo en un spool.

    Utilizado por endpoint POST /api/occupation/completar.
    """
    tag_spool: str = Field(
        ...,
        description="TAG único del spool a completar",
        min_length=1,
        examples=["MK-1335-CW-25238-011"]
    )
    worker_id: int = Field(
        ...,
        description="ID del trabajador que completa (debe ser el owner)",
        gt=0,
        examples=[93, 94, 95]
    )
    worker_nombre: str = Field(
        ...,
        description="Nombre completo del trabajador",
        min_length=1,
        examples=["MR(93)", "JP(94)"]
    )
    operacion: ActionType = Field(
        ...,
        description="Operación a completar (ARM/SOLD/METROLOGIA)"
    )
    fecha_operacion: date = Field(
        ...,
        description="Fecha de completado de la operación",
        examples=["2026-01-27"]
    )
    resultado: Optional[str] = Field(
        None,
        description="Resultado de metrología (APROBADO/RECHAZADO) - solo para METROLOGIA",
        examples=["APROBADO", "RECHAZADO"]
    )

    @field_validator('fecha_operacion', mode='before')
    @classmethod
    def set_fecha_default(cls, v):
        """Si no se provee fecha, usar date.today()."""
        return v or date.today()

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "tag_spool": "MK-1335-CW-25238-011",
                    "worker_id": 93,
                    "worker_nombre": "MR(93)",
                    "operacion": "ARM",
                    "fecha_operacion": "2026-01-27"
                }
            ]
        }
    )


class BatchTomarRequest(BaseModel):
    """
    Request body para tomar múltiples spools en batch.

    Utilizado por endpoint POST /api/occupation/batch-tomar.
    """
    tag_spools: list[str] = Field(
        ...,
        description="Lista de TAGs de spools a ocupar (máximo 50)",
        min_length=1,
        max_length=50,
        examples=[["MK-1335-CW-25238-011", "MK-1335-CW-25238-012"]]
    )
    worker_id: int = Field(
        ...,
        description="ID del trabajador que toma los spools",
        gt=0,
        examples=[93, 94, 95]
    )
    worker_nombre: str = Field(
        ...,
        description="Nombre completo del trabajador",
        min_length=1,
        examples=["MR(93)", "JP(94)"]
    )
    operacion: ActionType = Field(
        ...,
        description="Operación a realizar (ARM/SOLD/METROLOGIA)"
    )

    @field_validator('tag_spools')
    @classmethod
    def validate_unique_tags(cls, v):
        """Validar que no haya TAGs duplicados."""
        if len(v) != len(set(v)):
            raise ValueError("tag_spools no puede contener duplicados")
        return v

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "tag_spools": [
                        "MK-1335-CW-25238-011",
                        "MK-1335-CW-25238-012",
                        "MK-1335-CW-25238-013"
                    ],
                    "worker_id": 93,
                    "worker_nombre": "MR(93)",
                    "operacion": "ARM"
                }
            ]
        }
    )


class OccupationResponse(BaseModel):
    """Response para operaciones de ocupación individuales."""
    success: bool = Field(..., description="Si la operación fue exitosa")
    tag_spool: str = Field(..., description="TAG del spool procesado")
    message: str = Field(..., description="Mensaje descriptivo del resultado")

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "success": True,
                    "tag_spool": "MK-1335-CW-25238-011",
                    "message": "Spool MK-1335-CW-25238-011 tomado por MR(93)"
                }
            ]
        }
    )


class BatchOccupationResponse(BaseModel):
    """Response para operaciones batch con resumen de resultados."""
    total: int = Field(..., description="Total de spools procesados", ge=0)
    succeeded: int = Field(..., description="Cantidad exitosa", ge=0)
    failed: int = Field(..., description="Cantidad fallida", ge=0)
    details: list[OccupationResponse] = Field(..., description="Detalle por spool")

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "total": 3,
                    "succeeded": 2,
                    "failed": 1,
                    "details": [
                        {
                            "success": True,
                            "tag_spool": "MK-1335-CW-25238-011",
                            "message": "Spool tomado exitosamente"
                        },
                        {
                            "success": True,
                            "tag_spool": "MK-1335-CW-25238-012",
                            "message": "Spool tomado exitosamente"
                        },
                        {
                            "success": False,
                            "tag_spool": "MK-1335-CW-25238-013",
                            "message": "Spool ya ocupado por JP(94)"
                        }
                    ]
                }
            ]
        }
    )


class OccupationStatus(BaseModel):
    """Estado de ocupación de un spool."""
    tag_spool: str = Field(..., description="TAG del spool")
    ocupado: bool = Field(..., description="Si el spool está ocupado")
    ocupado_por: Optional[str] = Field(None, description="Worker que ocupa el spool")
    fecha_ocupacion: Optional[datetime] = Field(None, description="Timestamp de ocupación")

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "tag_spool": "MK-1335-CW-25238-011",
                    "ocupado": True,
                    "ocupado_por": "MR(93)",
                    "fecha_ocupacion": "2026-01-27T15:30:00Z"
                },
                {
                    "tag_spool": "MK-1335-CW-25238-012",
                    "ocupado": False,
                    "ocupado_por": None,
                    "fecha_ocupacion": None
                }
            ]
        }
    )


class OccupationEvent(BaseModel):
    """Evento de ocupación para logging en Metadata."""
    tag_spool: str = Field(..., description="TAG del spool")
    worker_id: int = Field(..., description="ID del trabajador")
    worker_nombre: str = Field(..., description="Nombre del trabajador")
    operacion: str = Field(..., description="Operación (ARM/SOLD/METROLOGIA)")
    accion: str = Field(..., description="Acción (TOMAR/PAUSAR/COMPLETAR)")
    lock_token: Optional[str] = Field(None, description="Token del lock Redis")
    metadata_json: Optional[str] = Field(None, description="Metadata adicional en JSON")


class LockToken(BaseModel):
    """Token de lock para tracking interno."""
    tag_spool: str = Field(..., description="TAG del spool")
    worker_id: int = Field(..., description="ID del trabajador owner")
    token: str = Field(..., description="UUID token único")
    expires_at: Optional[datetime] = Field(None, description="Timestamp de expiración")
