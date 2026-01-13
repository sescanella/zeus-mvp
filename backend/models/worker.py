"""
Modelos Pydantic para Trabajadores.
"""
from pydantic import BaseModel, Field, ConfigDict, computed_field
from typing import Optional
from enum import Enum


class RolTrabajador(str, Enum):
    """Roles disponibles para trabajadores en v2.0."""
    ARMADOR = "Armador"
    SOLDADOR = "Soldador"
    AYUDANTE = "Ayudante"
    METROLOGIA = "Metrologia"
    REVESTIMIENTO = "Revestimiento"
    PINTURA = "Pintura"
    DESPACHO = "Despacho"


class Worker(BaseModel):
    """
    Modelo de un trabajador de planta (v2.0).

    Representa un trabajador que puede realizar operaciones en spools.
    v2.0 incluye Id numérico y Rol específico.
    """
    id: int = Field(
        ...,
        description="ID único del trabajador (numérico)",
        gt=0,
        examples=[93, 94, 95]
    )
    nombre: str = Field(
        ...,
        description="Nombre del trabajador",
        min_length=1,
        examples=["Mauricio"]
    )
    apellido: str = Field(
        ...,
        description="Apellido del trabajador",
        min_length=1,
        examples=["Rodriguez"]
    )
    rol: Optional[RolTrabajador] = Field(
        None,
        description="Rol del trabajador en la planta (DEPRECATED: usar hoja Roles en su lugar)",
        examples=[RolTrabajador.ARMADOR, RolTrabajador.SOLDADOR]
    )
    roles: list[str] = Field(
        default_factory=list,
        description="Lista de roles del trabajador desde hoja Roles (v2.0 multi-role)",
        examples=[["Armador"], ["Armador", "Soldador"], ["Soldador", "Metrologia"]]
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
                    {"id": 93, "nombre": "Mauricio", "apellido": "Rodriguez", "rol": "Armador", "activo": True},
                    {"id": 94, "nombre": "Nicolás", "apellido": "Rodriguez", "rol": "Armador", "activo": True},
                    {"id": 95, "nombre": "Carlos", "apellido": "Pimiento", "rol": "Soldador", "activo": True}
                ],
                "total": 3
            }
        }
    )
