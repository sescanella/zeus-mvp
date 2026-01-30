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
import pytz
from backend.utils.date_formatter import now_chile, format_datetime_for_sheets
# Import EventoTipo from central enums.py (single source of truth)
from backend.models.enums import EventoTipo


class Accion(str, Enum):
    """Tipo de acción (v2.1: iniciar/completar/cancelar, v3.0: tomar/pausar)."""
    # v2.1 Actions (legacy)
    INICIAR = "INICIAR"
    COMPLETAR = "COMPLETAR"
    CANCELAR = "CANCELAR"  # v2.0: Revertir operación EN_PROGRESO

    # v3.0 Actions (new)
    TOMAR = "TOMAR"    # Worker takes/occupies spool
    PAUSAR = "PAUSAR"  # Worker pauses/releases spool


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
        default_factory=now_chile,
        description="Timestamp del evento en timezone Santiago (DD-MM-YYYY HH:MM:SS)",
        examples=["10-12-2025 14:30:00"]
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
        description="Trabajador en formato 'INICIALES(ID)' - v2.1",
        min_length=1,
        examples=["MR(93)", "CP(95)", "JP(94)"]
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
        description="Fecha de la operación (formato: DD-MM-YYYY)",
        pattern=r"^\d{2}-\d{2}-\d{4}$",
        examples=["10-12-2025"]
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
                "timestamp": "10-12-2025 14:30:00",
                "evento_tipo": "INICIAR_ARM",
                "tag_spool": "MK-1335-CW-25238-011",
                "worker_id": 93,
                "worker_nombre": "MR(93)",
                "operacion": "ARM",
                "accion": "INICIAR",
                "fecha_operacion": "10-12-2025",
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
            format_datetime_for_sheets(self.timestamp),  # DD-MM-YYYY HH:MM:SS
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
        # Parse timestamp with backward compatibility
        timestamp_str = row[1]
        try:
            # Try new format DD-MM-YYYY HH:MM:SS
            timestamp = datetime.strptime(timestamp_str, "%d-%m-%Y %H:%M:%S").replace(tzinfo=pytz.timezone('America/Santiago'))
        except ValueError:
            # Fallback to old ISO 8601 format
            timestamp = datetime.fromisoformat(timestamp_str.replace("Z", "+00:00"))

        return cls(
            id=row[0],
            timestamp=timestamp,
            evento_tipo=EventoTipo(row[2]),
            tag_spool=row[3],
            worker_id=int(row[4]),
            worker_nombre=row[5],
            operacion=row[6],
            accion=Accion(row[7]),
            fecha_operacion=row[8],
            metadata_json=row[9] if len(row) > 9 and row[9] else None
        )
