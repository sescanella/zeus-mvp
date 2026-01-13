"""
Modelos Pydantic para Spools (piezas de tubería).
"""
from pydantic import BaseModel, Field, ConfigDict
from typing import Optional
from datetime import date
from .enums import ActionStatus, ActionType


class Spool(BaseModel):
    """
    Modelo completo de un spool (pieza de tubería).

    Representa un spool con sus estados de operaciones (ARM/SOLD),
    fechas de dependencias, y metadata de trabajadores.
    """
    tag_spool: str = Field(
        ...,
        description="TAG único del spool (columna G en Sheets)",
        min_length=1,
        examples=["MK-1335-CW-25238-011"]
    )

    # v2.0: Número de Nota de Venta para filtrado multidimensional
    nv: Optional[str] = Field(
        None,
        description="Número de Nota de Venta (columna H en Sheets)",
        examples=["001", "002", "NV-123"]
    )

    # Estados de acciones (columnas V, W)
    arm: ActionStatus = Field(
        ActionStatus.PENDIENTE,
        description="Estado de la operación ARM (Armado)"
    )
    sold: ActionStatus = Field(
        ActionStatus.PENDIENTE,
        description="Estado de la operación SOLD (Soldado)"
    )

    # Fechas de dependencias (columnas BA, BB, BD)
    fecha_materiales: Optional[date] = Field(
        None,
        description="Fecha cuando materiales estuvieron disponibles (columna BA)",
        examples=["2025-11-01"]
    )
    fecha_armado: Optional[date] = Field(
        None,
        description="Fecha cuando se completó el armado (columna BB)",
        examples=["2025-11-08"]
    )
    fecha_soldadura: Optional[date] = Field(
        None,
        description="Fecha cuando se completó la soldadura (columna BD)",
        examples=["2025-11-10"]
    )

    # Metadata de trabajadores (columnas BC, BE)
    armador: Optional[str] = Field(
        None,
        description="Nombre del trabajador que inició ARM (columna BC)",
        examples=["Juan Pérez"]
    )
    soldador: Optional[str] = Field(
        None,
        description="Nombre del trabajador que inició SOLD (columna BE)",
        examples=["María González"]
    )

    # Metadata adicional (opcional para MVP)
    proyecto: Optional[str] = Field(
        None,
        description="Nombre del proyecto al que pertenece el spool",
        examples=["Proyecto Alpha"]
    )

    model_config = ConfigDict(
        frozen=True,  # Inmutable
        str_strip_whitespace=True,
    )

    def puede_iniciar_arm(self) -> bool:
        """
        Verifica si el spool puede iniciar la operación ARM.

        Reglas:
        - ARM debe estar en estado PENDIENTE (V=0)
        - fecha_materiales debe estar llena (BA tiene valor)
        - fecha_armado debe estar vacía (BB vacía)

        Returns:
            bool: True si cumple todas las condiciones
        """
        return (
            self.arm == ActionStatus.PENDIENTE and
            self.fecha_materiales is not None and
            self.fecha_armado is None
        )

    def puede_completar_arm(self, worker_nombre: str) -> bool:
        """
        Verifica si el trabajador puede completar la operación ARM.

        Reglas:
        - ARM debe estar EN_PROGRESO (V=0.1)
        - armador debe coincidir con worker_nombre (restricción propiedad)

        Args:
            worker_nombre: Nombre completo del trabajador

        Returns:
            bool: True si cumple todas las condiciones
        """
        return (
            self.arm == ActionStatus.EN_PROGRESO and
            self.armador == worker_nombre
        )

    def puede_iniciar_sold(self) -> bool:
        """
        Verifica si el spool puede iniciar la operación SOLD.

        Reglas:
        - SOLD debe estar en estado PENDIENTE (W=0)
        - fecha_armado debe estar llena (BB tiene valor - ARM completado)
        - fecha_soldadura debe estar vacía (BD vacía)

        Returns:
            bool: True si cumple todas las condiciones
        """
        return (
            self.sold == ActionStatus.PENDIENTE and
            self.fecha_armado is not None and
            self.fecha_soldadura is None
        )

    def puede_completar_sold(self, worker_nombre: str) -> bool:
        """
        Verifica si el trabajador puede completar la operación SOLD.

        Reglas:
        - SOLD debe estar EN_PROGRESO (W=0.1)
        - soldador debe coincidir con worker_nombre (restricción propiedad)

        Args:
            worker_nombre: Nombre completo del trabajador

        Returns:
            bool: True si cumple todas las condiciones
        """
        return (
            self.sold == ActionStatus.EN_PROGRESO and
            self.soldador == worker_nombre
        )


class SpoolListResponse(BaseModel):
    """Response para lista de spools."""
    spools: list[Spool] = Field(
        default_factory=list,
        description="Lista de spools"
    )
    total: int = Field(
        ...,
        description="Total de spools retornados",
        ge=0
    )
    filtro_aplicado: str = Field(
        ...,
        description="Descripción del filtro aplicado a la lista",
        examples=["ARM: V=0, BA llena, BB vacía"]
    )

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "spools": [
                    {
                        "tag_spool": "MK-1335-CW-25238-011",
                        "arm": "PENDIENTE",
                        "sold": "PENDIENTE",
                        "fecha_materiales": "2025-11-01",
                        "fecha_armado": None,
                        "fecha_soldadura": None,
                        "armador": None,
                        "soldador": None,
                        "proyecto": "Proyecto Alpha"
                    }
                ],
                "total": 1,
                "filtro_aplicado": "ARM: V=0, BA llena, BB vacía"
            }
        }
    )
