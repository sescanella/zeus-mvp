"""
Modelos Pydantic para Metadata (Event Sourcing).

Representa eventos en la hoja Metadata que registran todas las acciones
realizadas en el sistema ZEUES v2.0.
"""
from pydantic import BaseModel, Field, ConfigDict
from datetime import datetime
from enum import Enum
from typing import Optional
import uuid


class EventoTipo(str, Enum):
    """Tipos de eventos que se registran en Metadata."""
    INICIAR_ARM = "INICIAR_ARM"
    COMPLETAR_ARM = "COMPLETAR_ARM"
    CANCELAR_ARM = "CANCELAR_ARM"  # v2.0: Revertir EN_PROGRESO a PENDIENTE
    INICIAR_SOLD = "INICIAR_SOLD"
    COMPLETAR_SOLD = "COMPLETAR_SOLD"
    CANCELAR_SOLD = "CANCELAR_SOLD"  # v2.0: Revertir EN_PROGRESO a PENDIENTE
    INICIAR_METROLOGIA = "INICIAR_METROLOGIA"
    COMPLETAR_METROLOGIA = "COMPLETAR_METROLOGIA"
    CANCELAR_METROLOGIA = "CANCELAR_METROLOGIA"  # v2.0: Revertir EN_PROGRESO a PENDIENTE


class Accion(str, Enum):
    """Tipo de acción (iniciar, completar, o cancelar)."""
    INICIAR = "INICIAR"
    COMPLETAR = "COMPLETAR"
    CANCELAR = "CANCELAR"  # v2.0: Revertir operación EN_PROGRESO


class MetadataEvent(BaseModel):
    """
    Modelo de un evento en la hoja Metadata.

    Cada evento representa una acción realizada por un trabajador sobre un spool.
    Sigue el patrón Event Sourcing: eventos inmutables, append-only.
    """
    id: str = Field(
        default_factory=lambda: str(uuid.uuid4()),
        description="UUID único del evento",
        examples=["550e8400-e29b-41d4-a716-446655440000"]
    )
    timestamp: datetime = Field(
        default_factory=datetime.utcnow,
        description="Timestamp UTC del evento (ISO 8601)",
        examples=["2025-12-10T14:30:00Z"]
    )
    evento_tipo: EventoTipo = Field(
        ...,
        description="Tipo de evento",
        examples=[EventoTipo.INICIAR_ARM, EventoTipo.COMPLETAR_SOLD]
    )
    tag_spool: str = Field(
        ...,
        description="Código del spool (TAG_SPOOL / CODIGO_BARRA)",
        min_length=1,
        examples=["MK-1335-CW-25238-011"]
    )
    worker_id: int = Field(
        ...,
        description="ID del trabajador que realiza la acción",
        gt=0,
        examples=[93, 94, 95]
    )
    worker_nombre: str = Field(
        ...,
        description="Nombre completo del trabajador",
        min_length=1,
        examples=["Mauricio Rodriguez", "Carlos Pimiento"]
    )
    operacion: str = Field(
        ...,
        description="Operación realizada (ARM, SOLD, METROLOGIA)",
        pattern="^(ARM|SOLD|METROLOGIA)$",
        examples=["ARM", "SOLD", "METROLOGIA"]
    )
    accion: Accion = Field(
        ...,
        description="Tipo de acción (INICIAR o COMPLETAR)",
        examples=[Accion.INICIAR, Accion.COMPLETAR]
    )
    fecha_operacion: str = Field(
        ...,
        description="Fecha de la operación (formato ISO: YYYY-MM-DD)",
        pattern=r"^\d{4}-\d{2}-\d{2}$",
        examples=["2025-12-10"]
    )
    metadata_json: Optional[str] = Field(
        None,
        description="JSON con datos adicionales (IP, device, etc.)",
        examples=['{"ip": "192.168.1.10", "device": "tablet-01"}']
    )

    model_config = ConfigDict(
        frozen=True,  # Inmutable (Event Sourcing)
        str_strip_whitespace=True,
        json_schema_extra={
            "example": {
                "id": "550e8400-e29b-41d4-a716-446655440000",
                "timestamp": "2025-12-10T14:30:00Z",
                "evento_tipo": "INICIAR_ARM",
                "tag_spool": "MK-1335-CW-25238-011",
                "worker_id": 93,
                "worker_nombre": "Mauricio Rodriguez",
                "operacion": "ARM",
                "accion": "INICIAR",
                "fecha_operacion": "2025-12-10",
                "metadata_json": '{"device": "tablet-01"}'
            }
        }
    )

    def to_sheets_row(self) -> list[str]:
        """
        Convierte el evento a una fila de Google Sheets.

        Returns:
            list[str]: Lista con valores para escribir en Sheets (columnas A-J)
        """
        return [
            self.id,
            self.timestamp.isoformat() + "Z",  # ISO 8601 con Z
            self.evento_tipo.value,
            self.tag_spool,
            str(self.worker_id),
            self.worker_nombre,
            self.operacion,
            self.accion.value,
            self.fecha_operacion,
            self.metadata_json or ""
        ]

    @classmethod
    def from_sheets_row(cls, row: list[str]) -> "MetadataEvent":
        """
        Crea un MetadataEvent desde una fila de Google Sheets.

        Args:
            row: Lista de valores de una fila de Sheets (columnas A-J)

        Returns:
            MetadataEvent: Instancia del evento
        """
        return cls(
            id=row[0],
            timestamp=datetime.fromisoformat(row[1].replace("Z", "+00:00")),
            evento_tipo=EventoTipo(row[2]),
            tag_spool=row[3],
            worker_id=int(row[4]),
            worker_nombre=row[5],
            operacion=row[6],
            accion=Accion(row[7]),
            fecha_operacion=row[8],
            metadata_json=row[9] if len(row) > 9 and row[9] else None
        )
