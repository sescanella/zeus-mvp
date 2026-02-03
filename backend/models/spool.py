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

    Representa un spool con sus estados de operaciones (ARM/SOLD/METROLOGIA),
    fechas de dependencias, y metadata de trabajadores.
    """
    tag_spool: str = Field(
        ...,
        description="TAG único del spool (columna G en Sheets)",
        min_length=1,
        examples=["MK-1335-CW-25238-011"]
    )

    # v4.0: Orden de Trabajo (OT) - Foreign key para Uniones sheet
    ot: Optional[str] = Field(
        None,
        description="Número de Orden de Trabajo (columna B en Sheets)",
        examples=["001", "123", "MK-1335"]
    )

    # v2.0: Número de Nota de Venta para filtrado multidimensional
    nv: Optional[str] = Field(
        None,
        description="Número de Nota de Venta (columna H en Sheets)",
        examples=["001", "002", "NV-123"]
    )

    # v4.0: Columna de métricas de uniones (col 68)
    total_uniones: Optional[int] = Field(
        None,
        description="Total de uniones en el spool (columna 68 'Total_Uniones')",
        ge=0,
        examples=[0, 8, 12]
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
    fecha_qc_metrologia: Optional[date] = Field(
        None,
        description="Fecha cuando se completó QC/Metrología (columna 38 'Fecha_QC_Metrología')",
        examples=["2025-11-15"]
    )

    # Metadata de trabajadores (columnas BC, BE)
    # v2.1: Formato "INICIALES(ID)" - ej: "MR(93)"
    armador: Optional[str] = Field(
        None,
        description="Trabajador que inició ARM en formato 'INICIALES(ID)' (columna BC)",
        examples=["MR(93)", "JP(94)"]
    )
    soldador: Optional[str] = Field(
        None,
        description="Trabajador que inició SOLD en formato 'INICIALES(ID)' (columna BE)",
        examples=["MG(95)", "CP(96)"]
    )

    # Metadata adicional (opcional para MVP)
    proyecto: Optional[str] = Field(
        None,
        description="Nombre del proyecto al que pertenece el spool",
        examples=["Proyecto Alpha"]
    )

    # v3.0: Campos de ocupación
    ocupado_por: Optional[str] = Field(
        None,
        description="Trabajador que actualmente ocupa el spool en formato 'INICIALES(ID)' (columna 64)",
        examples=["MR(93)", "JP(94)"]
    )
    fecha_ocupacion: Optional[str] = Field(
        None,
        description="Fecha cuando el spool fue ocupado en formato YYYY-MM-DD (columna 65)",
        examples=["2026-01-26"]
    )
    version: int = Field(
        0,
        description="Token de versión para optimistic locking - incrementa en cada TOMAR/PAUSAR/COMPLETAR (columna 66)",
        ge=0
    )

    # v3.0: Estado detallado
    estado_detalle: Optional[str] = Field(
        None,
        description="Estado detallado del spool con información de ciclos y progreso (columna 67 'Estado_Detalle')",
        examples=["RECHAZADO (Ciclo 2/3) - Pendiente reparación", "BLOQUEADO - Contactar supervisor", "EN_REPARACION (Ciclo 1/3) - Ocupado: MR(93)"]
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

    def puede_iniciar_metrologia(self) -> bool:
        """
        Verifica si el spool puede iniciar la operación METROLOGIA/QC.

        Reglas v2.1 (sin columna Metrólogo en Sheets):
        - fecha_soldadura debe estar llena (SOLD completado - prerequisito)
        - fecha_qc_metrologia debe estar vacía (METROLOGIA no iniciada)

        Returns:
            bool: True si cumple todas las condiciones
        """
        return (
            self.fecha_soldadura is not None and
            self.fecha_qc_metrologia is None
        )

    @property
    def esta_ocupado(self) -> bool:
        """
        Verifica si el spool está actualmente ocupado por un worker (v3.0).

        Un spool está ocupado si tiene un worker asignado en ocupado_por.

        Returns:
            bool: True si el spool está ocupado, False si está disponible
        """
        return self.ocupado_por is not None


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
