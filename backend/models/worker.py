"""
Modelos Pydantic para Trabajadores.
"""
from pydantic import BaseModel, Field, ConfigDict, computed_field
from typing import Optional


class Worker(BaseModel):
    """
    Modelo de un trabajador de planta.

    Representa un trabajador que puede realizar operaciones (ARM/SOLD) en spools.
    """
    nombre: str = Field(
        ...,
        description="Nombre del trabajador",
        min_length=1,
        examples=["Juan"]
    )
    apellido: Optional[str] = Field(
        None,
        description="Apellido del trabajador (opcional)",
        examples=["Pérez"]
    )
    activo: bool = Field(
        True,
        description="Si el trabajador está activo para realizar acciones"
    )

    model_config = ConfigDict(
        frozen=True,  # Inmutable
        str_strip_whitespace=True,  # Limpiar espacios
    )

    @computed_field  # type: ignore[misc]
    @property
    def nombre_completo(self) -> str:
        """
        Retorna el nombre completo del trabajador.

        Returns:
            str: "Nombre Apellido" o solo "Nombre" si no tiene apellido
        """
        if self.apellido:
            return f"{self.nombre} {self.apellido}"
        return self.nombre


class WorkerListResponse(BaseModel):
    """Response para lista de trabajadores."""
    workers: list[Worker] = Field(
        default_factory=list,
        description="Lista de trabajadores activos"
    )
    total: int = Field(
        ...,
        description="Total de trabajadores activos",
        ge=0
    )

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "workers": [
                    {"nombre": "Juan", "apellido": "Pérez", "activo": True},
                    {"nombre": "María", "apellido": "González", "activo": True}
                ],
                "total": 2
            }
        }
    )
