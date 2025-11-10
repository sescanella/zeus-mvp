"""
Modelo Pydantic para respuestas de error.
"""
from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, Any


class ErrorResponse(BaseModel):
    """
    Response estándar para errores en la API.

    Utilizado por los exception handlers para retornar errores consistentes.
    """
    success: bool = Field(
        False,
        description="Siempre False para errores"
    )
    error: str = Field(
        ...,
        description="Código de error (ej: SPOOL_NO_ENCONTRADO, NO_AUTORIZADO)",
        examples=["SPOOL_NO_ENCONTRADO", "NO_AUTORIZADO", "OPERACION_YA_INICIADA"]
    )
    message: str = Field(
        ...,
        description="Mensaje de error legible para el usuario",
        examples=[
            "Spool 'MK-123' no encontrado en hoja Operaciones",
            "Solo Juan Pérez puede completar esta acción (él la inició)"
        ]
    )
    data: Optional[dict[str, Any]] = Field(
        None,
        description="Contexto adicional sobre el error (opcional)"
    )

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "success": False,
                    "error": "SPOOL_NO_ENCONTRADO",
                    "message": "Spool 'MK-1335-CW-25238-999' no encontrado en hoja Operaciones",
                    "data": {
                        "tag_spool": "MK-1335-CW-25238-999"
                    }
                },
                {
                    "success": False,
                    "error": "NO_AUTORIZADO",
                    "message": "Solo Juan López puede completar ARM en 'MK-1335-CW-25238-011'. Tú eres Juan Pérez.",
                    "data": {
                        "tag_spool": "MK-1335-CW-25238-011",
                        "trabajador_esperado": "Juan López",
                        "trabajador_solicitante": "Juan Pérez"
                    }
                },
                {
                    "success": False,
                    "error": "OPERACION_YA_INICIADA",
                    "message": "La operación ARM del spool MK-1335-CW-25238-011 ya está iniciada por María González",
                    "data": {
                        "tag_spool": "MK-1335-CW-25238-011",
                        "operacion": "ARM",
                        "armador": "María González"
                    }
                },
                {
                    "success": False,
                    "error": "DEPENDENCIAS_NO_SATISFECHAS",
                    "message": "No se puede iniciar ARM en spool MK-123: falta Fecha_Materiales (BA vacía)",
                    "data": {
                        "tag_spool": "MK-123",
                        "operacion": "ARM",
                        "dependencia_faltante": "Fecha_Materiales"
                    }
                },
                {
                    "success": False,
                    "error": "SHEETS_CONNECTION_ERROR",
                    "message": "Error al conectar con Google Sheets: Authentication failed",
                    "data": None
                }
            ]
        }
    )
