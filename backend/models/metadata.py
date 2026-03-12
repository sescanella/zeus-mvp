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
        description="Operación realizada (ARM, SOLD, METROLOGIA, REPARACION)",
        pattern="^(ARM|SOLD|METROLOGIA|REPARACION)$",
        examples=["ARM", "SOLD", "METROLOGIA", "REPARACION"]
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
    n_union: Optional[int] = Field(
        None,
        description="Union number within spool (1-20) for v4.0 union-level granularity",
        ge=1,
        le=20,
        examples=[1, 5, 10]
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
                "metadata_json": '{"device": "tablet-01"}',
                "n_union": 5
            }
        }
    )

    def to_sheets_row(self) -> list[str]:
        """
        Convierte el evento a una fila de Google Sheets.

        Returns:
            list[str]: Lista con valores para escribir en Sheets (columnas A-K)
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
            self.metadata_json or "",
            str(self.n_union) if self.n_union is not None else ""  # Column K
        ]

    @classmethod
    def from_sheets_row(cls, row: list[str], column_map: Optional[dict] = None) -> "MetadataEvent":
        """
        Crea un MetadataEvent desde una fila de Google Sheets.

        Args:
            row: Lista de valores de una fila de Sheets (columnas A-K, backward compatible with A-J)
            column_map: Optional dynamic column mapping {normalized_name: index}.
                        If None, falls back to hardcoded indices for backward compatibility.

        Returns:
            MetadataEvent: Instancia del evento
        """
        def get_idx(name: str, fallback: int) -> int:
            """Resolve column index from column_map or fallback to hardcoded index."""
            if column_map is None:
                return fallback
            normalized = name.lower().replace(" ", "").replace("_", "")
            return column_map.get(normalized, fallback)

        idx_id = get_idx("ID", 0)
        idx_timestamp = get_idx("Timestamp", 1)
        idx_evento_tipo = get_idx("Evento_Tipo", 2)
        idx_tag_spool = get_idx("TAG_SPOOL", 3)
        idx_worker_id = get_idx("Worker_ID", 4)
        idx_worker_nombre = get_idx("Worker_Nombre", 5)
        idx_operacion = get_idx("Operacion", 6)
        idx_accion = get_idx("Accion", 7)
        idx_fecha_operacion = get_idx("Fecha_Operacion", 8)
        idx_metadata_json = get_idx("Metadata_JSON", 9)
        idx_n_union = get_idx("N_UNION", 10)

        # Parse timestamp with backward compatibility
        timestamp_str = row[idx_timestamp]
        try:
            # Try new format DD-MM-YYYY HH:MM:SS
            timestamp = datetime.strptime(timestamp_str, "%d-%m-%Y %H:%M:%S").replace(tzinfo=pytz.timezone('America/Santiago'))
        except ValueError:
            # Fallback to old ISO 8601 format
            timestamp = datetime.fromisoformat(timestamp_str.replace("Z", "+00:00"))

        # Parse n_union with backward compatibility
        n_union = None
        if len(row) > idx_n_union and row[idx_n_union]:
            try:
                n_union = int(row[idx_n_union])
            except (ValueError, TypeError):
                # Gracefully handle non-integer values
                pass

        return cls(
            id=row[idx_id],
            timestamp=timestamp,
            evento_tipo=EventoTipo(row[idx_evento_tipo]),
            tag_spool=row[idx_tag_spool],
            worker_id=int(row[idx_worker_id]),
            worker_nombre=row[idx_worker_nombre],
            operacion=row[idx_operacion],
            accion=Accion(row[idx_accion]),
            fecha_operacion=row[idx_fecha_operacion],
            metadata_json=row[idx_metadata_json] if len(row) > idx_metadata_json and row[idx_metadata_json] else None,
            n_union=n_union
        )
