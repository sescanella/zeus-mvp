"""
Pydantic models for No Conformidad (Non-Conformity) forms.

REG-QAC-002: First form in the modular forms system.
"""
from typing import Literal
from pydantic import BaseModel, Field


class NoConformidadRequest(BaseModel):
    """Request model for registering a No Conformidad."""
    tag_spool: str = Field(..., min_length=1)
    worker_id: int
    origen: Literal["Interna", "Cliente/ITO", "Otro"]
    tipo: Literal[
        "Proceso",
        "Procedimiento/Protocolo",
        "Producto",
        "Post-Venta",
        "Condición Insegura",
    ]
    descripcion: str = Field(..., min_length=1, max_length=2000)


class NoConformidadResponse(BaseModel):
    """Response model after registering a No Conformidad."""
    success: bool
    message: str
    registro_id: str
    tag_spool: str
