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
        Retorna el nombre del trabajador en formato 'INICIALES(ID)'.

        El formato toma la primera letra del primer nombre y la primera letra
        del primer apellido (ignorando nombres/apellidos compuestos), las
        convierte a MAYÚSCULAS y las combina con el ID entre paréntesis.

        Returns:
            str: Formato "XX(ID)" donde XX son las iniciales del primer nombre y
                 primer apellido en MAYÚSCULAS, e ID es el identificador numérico.

        Examples:
            - "Mauricio Rodriguez" con id=93 → "MR(93)"
            - "Juan Carlos Pérez López" con id=94 → "JP(94)"
            - "María José García" con id=95 → "MG(95)"

        Note:
            - Siempre retorna MAYÚSCULAS sin espacios
            - Para nombres compuestos usa solo la primera palabra de cada campo
        """
        # Extraer primera letra del primer nombre
        primer_nombre = self.nombre.strip().split()[0] if self.nombre.strip() else ""
        inicial_nombre = primer_nombre[0].upper() if primer_nombre else ""

        # Extraer primera letra del primer apellido
        primer_apellido = self.apellido.strip().split()[0] if self.apellido.strip() else ""
        inicial_apellido = primer_apellido[0].upper() if primer_apellido else ""

        # Formato: "XX(ID)"
        iniciales = f"{inicial_nombre}{inicial_apellido}"
        return f"{iniciales}({self.id})"


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
                    {"id": 93, "nombre": "Mauricio", "apellido": "Rodriguez", "nombre_completo": "MR(93)", "rol": "Armador", "activo": True},
                    {"id": 94, "nombre": "Nicolás", "apellido": "Rodriguez", "nombre_completo": "NR(94)", "rol": "Armador", "activo": True},
                    {"id": 95, "nombre": "Carlos", "apellido": "Pimiento", "nombre_completo": "CP(95)", "rol": "Soldador", "activo": True}
                ],
                "total": 3
            }
        }
    )
