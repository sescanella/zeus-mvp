"""
Modelos Pydantic para Acciones (iniciar/completar operaciones).
"""
from pydantic import BaseModel, Field, field_validator, ConfigDict
from typing import Optional
from datetime import datetime
from .enums import ActionType


class ActionRequest(BaseModel):
    """
    Request body para iniciar, completar o cancelar una acción (v2.0).

    Utilizado por endpoints POST /api/iniciar-accion, POST /api/completar-accion, POST /api/cancelar-accion.
    v2.0: Usa worker_id (int) en vez de worker_nombre (str).
    """
    worker_id: int = Field(
        ...,
        description="ID del trabajador (v2.0: reemplaza worker_nombre)",
        gt=0,
        examples=[93, 94, 95]
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
                    "worker_id": 93,
                    "operacion": "ARM",
                    "tag_spool": "MK-1335-CW-25238-011"
                },
                {
                    "worker_id": 94,
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
    fila_actualizada: int = Field(..., description="Número de fila actualizada en Sheets (v2.0: 0 si Event Sourcing)", ge=0)
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


# ============================================================================
# BATCH OPERATIONS MODELS (v2.0)
# ============================================================================

class BatchActionRequest(BaseModel):
    """
    Request body para operaciones batch (v2.0 multiselect).

    Permite INICIAR/COMPLETAR hasta 50 spools simultáneamente.
    Utilizado por endpoints POST /api/iniciar-accion-batch, POST /api/completar-accion-batch.
    """
    worker_id: int = Field(
        ...,
        description="ID del trabajador que realiza las acciones",
        gt=0,
        examples=[93, 94, 95]
    )
    operacion: ActionType = Field(
        ...,
        description="Tipo de operación a realizar (ARM o SOLD)"
    )
    tag_spools: list[str] = Field(
        ...,
        description="Lista de TAGs de spools (máximo 50)",
        min_length=1,
        max_length=50,
        examples=[["MK-1335-CW-25238-011", "MK-1335-CW-25238-012", "MK-1335-CW-25238-013"]]
    )
    timestamp: Optional[datetime] = Field(
        None,
        description="Timestamp para completar acción (default: now())"
    )

    @field_validator('timestamp', mode='before')
    @classmethod
    def set_timestamp_default(cls, v):
        """Si no se provee timestamp, usar datetime.now()."""
        return v or datetime.now()

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
                    "worker_id": 93,
                    "operacion": "ARM",
                    "tag_spools": [
                        "MK-1335-CW-25238-011",
                        "MK-1335-CW-25238-012",
                        "MK-1335-CW-25238-013"
                    ]
                },
                {
                    "worker_id": 94,
                    "operacion": "SOLD",
                    "tag_spools": ["MK-1335-CW-25238-014", "MK-1335-CW-25238-015"],
                    "timestamp": "2025-12-12T14:30:00Z"
                }
            ]
        }
    )


class BatchActionResult(BaseModel):
    """
    Resultado de procesamiento de un spool individual dentro de batch.

    Usado en BatchActionResponse para reportar éxito o error por spool.
    """
    tag_spool: str = Field(..., description="TAG del spool procesado")
    success: bool = Field(..., description="Si la acción fue exitosa para este spool")
    message: Optional[str] = Field(None, description="Mensaje de éxito o error")
    evento_id: Optional[str] = Field(None, description="UUID del evento en Metadata (si exitoso)")
    error_type: Optional[str] = Field(None, description="Tipo de error (si falló)")

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "tag_spool": "MK-1335-CW-25238-011",
                    "success": True,
                    "message": "Acción ARM iniciada exitosamente",
                    "evento_id": "a1b2c3d4-e5f6-4a5b-8c9d-1e2f3a4b5c6d",
                    "error_type": None
                },
                {
                    "tag_spool": "MK-1335-CW-25238-012",
                    "success": False,
                    "message": "Operación ya iniciada por otro trabajador",
                    "evento_id": None,
                    "error_type": "OperacionYaIniciadaError"
                }
            ]
        }
    )


class BatchActionResponse(BaseModel):
    """
    Response de operación batch con resumen de resultados.

    Incluye contadores de éxitos/fallos y detalle por spool.
    """
    success: bool = Field(..., description="Si al menos un spool fue procesado exitosamente")
    message: str = Field(..., description="Resumen de la operación batch")
    total: int = Field(..., description="Total de spools procesados", ge=0)
    exitosos: int = Field(..., description="Cantidad de spools exitosos", ge=0)
    fallidos: int = Field(..., description="Cantidad de spools fallidos", ge=0)
    resultados: list[BatchActionResult] = Field(..., description="Detalle por spool")

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "success": True,
                    "message": "Batch ARM iniciado: 3 de 3 spools exitosos",
                    "total": 3,
                    "exitosos": 3,
                    "fallidos": 0,
                    "resultados": [
                        {
                            "tag_spool": "MK-1335-CW-25238-011",
                            "success": True,
                            "message": "Acción ARM iniciada exitosamente",
                            "evento_id": "a1b2c3d4-e5f6-4a5b-8c9d-1e2f3a4b5c6d",
                            "error_type": None
                        },
                        {
                            "tag_spool": "MK-1335-CW-25238-012",
                            "success": True,
                            "message": "Acción ARM iniciada exitosamente",
                            "evento_id": "b2c3d4e5-f6a7-5b6c-9d0e-2f3a4b5c6d7e",
                            "error_type": None
                        },
                        {
                            "tag_spool": "MK-1335-CW-25238-013",
                            "success": True,
                            "message": "Acción ARM iniciada exitosamente",
                            "evento_id": "c3d4e5f6-a7b8-6c7d-0e1f-3a4b5c6d7e8f",
                            "error_type": None
                        }
                    ]
                },
                {
                    "success": True,
                    "message": "Batch ARM iniciado: 2 de 3 spools exitosos (1 fallo)",
                    "total": 3,
                    "exitosos": 2,
                    "fallidos": 1,
                    "resultados": [
                        {
                            "tag_spool": "MK-1335-CW-25238-011",
                            "success": True,
                            "message": "Acción ARM iniciada exitosamente",
                            "evento_id": "a1b2c3d4-e5f6-4a5b-8c9d-1e2f3a4b5c6d",
                            "error_type": None
                        },
                        {
                            "tag_spool": "MK-1335-CW-25238-012",
                            "success": False,
                            "message": "Operación ya iniciada por otro trabajador",
                            "evento_id": None,
                            "error_type": "OperacionYaIniciadaError"
                        },
                        {
                            "tag_spool": "MK-1335-CW-25238-013",
                            "success": True,
                            "message": "Acción ARM iniciada exitosamente",
                            "evento_id": "c3d4e5f6-a7b8-6c7d-0e1f-3a4b5c6d7e8f",
                            "error_type": None
                        }
                    ]
                }
            ]
        }
    )
