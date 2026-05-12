"""
Modelos Pydantic para la feature de supervisor (Matías).

Tres categorias de datos en el spreadsheet ZEUES_App_Audit:
- TrackedSpool: lista de spools que Matías está siguiendo (tab `Lista`).
- AuditEvent:   bitácora append-only de todas sus acciones en la app (tab `Audit`).
- LegacySnapshot: backup crudo de localStorage capturado durante migración (tab `Snapshots_Legacy`).

Convenciones tomadas de backend/models/metadata.py:
- frozen=True para registros inmutables (event sourcing).
- to_sheets_row() y from_sheets_row(row, column_map=None) en cada modelo.
- Timestamps default vía now_chile(); serialización vía format_datetime_for_sheets().
- Resolución dinámica de columnas con normalize_column_name().
"""
from datetime import datetime
from enum import Enum
from typing import Optional
import uuid

import pytz
from pydantic import BaseModel, ConfigDict, Field

from backend.utils.date_formatter import format_datetime_for_sheets, now_chile
from backend.utils.normalize import normalize_column_name


# ─── Helpers ──────────────────────────────────────────────────────────────────


def _resolve_idx(name: str, fallback: int, column_map: Optional[dict]) -> int:
    """Resuelve el índice de una columna usando column_map, con fallback hardcoded."""
    if column_map is None:
        return fallback
    return column_map.get(normalize_column_name(name), fallback)


_SCL_TZ = pytz.timezone("America/Santiago")


def _parse_sheets_datetime(raw: str) -> datetime:
    """
    Parse a timestamp from Sheets, accepting either DD-MM-YYYY HH:MM:SS (preferido)
    o ISO 8601 (compatibilidad). Devuelve datetime aware en timezone Santiago.

    NOTA: pytz requiere `.localize(naive_dt)` para asignar correctamente el
    offset DST. Usar `.replace(tzinfo=pytz.timezone(...))` produce el offset
    histórico LMT de Chile (-04:42:46), causando un desfase de ~43 minutos.
    """
    raw = raw.strip()
    try:
        naive = datetime.strptime(raw, "%d-%m-%Y %H:%M:%S")
        return _SCL_TZ.localize(naive)
    except ValueError:
        return datetime.fromisoformat(raw.replace("Z", "+00:00"))


# ─── Enums ────────────────────────────────────────────────────────────────────


class EventType(str, Enum):
    """
    Tipos de eventos que registramos en la tab `Audit`.

    Decididos en la sesión del 2026-05-08:
    - Sesión y navegación: SESSION_START, SESSION_END, NAVIGATE.
    - Modales (visibilidad UX): MODAL_OPEN, MODAL_CLOSE.
    - Cambios de lista (críticos): LIST_ADD, LIST_REMOVE.
    - Migración one-shot: LIST_MIGRATE (full success), LIST_MIGRATE_PARTIAL (algún fallo).
    """
    SESSION_START = "SESSION_START"
    SESSION_END = "SESSION_END"
    LIST_ADD = "LIST_ADD"
    LIST_REMOVE = "LIST_REMOVE"
    LIST_MIGRATE = "LIST_MIGRATE"
    LIST_MIGRATE_PARTIAL = "LIST_MIGRATE_PARTIAL"
    MODAL_OPEN = "MODAL_OPEN"
    MODAL_CLOSE = "MODAL_CLOSE"
    NAVIGATE = "NAVIGATE"


# ─── TrackedSpool (tab `Lista`) ────────────────────────────────────────────────


class TrackedSpool(BaseModel):
    """
    Una fila en la tab `Lista` del spreadsheet ZEUES_App_Audit.

    Mutable: `updated_at` y `notes` cambian con el uso. La invariante
    "una fila por TAG_SPOOL" la garantiza el SupervisorService haciendo
    upsert (no este modelo).

    Columnas: TAG_SPOOL | Added_At | Updated_At | Notes
    """

    tag_spool: str = Field(
        ...,
        description="Código del spool",
        min_length=1,
        examples=["MK-1344-GW-27133-002"],
    )
    added_at: datetime = Field(
        default_factory=now_chile,
        description="Cuándo Matías agregó el spool a su lista",
    )
    updated_at: datetime = Field(
        default_factory=now_chile,
        description="Última modificación de notas",
    )
    notes: Optional[str] = Field(
        None,
        description="Notas libres del supervisor sobre el spool",
    )

    model_config = ConfigDict(
        str_strip_whitespace=True,
        json_schema_extra={
            "example": {
                "tag_spool": "MK-1344-GW-27133-002",
                "added_at": "08-05-2026 09:42:00",
                "updated_at": "08-05-2026 09:42:00",
                "notes": "",
            }
        },
    )

    def to_sheets_row(self) -> list[str]:
        """Serializa a fila para la tab `Lista` (4 columnas)."""
        return [
            self.tag_spool,
            format_datetime_for_sheets(self.added_at),
            format_datetime_for_sheets(self.updated_at),
            self.notes or "",
        ]

    @classmethod
    def from_sheets_row(
        cls, row: list[str], column_map: Optional[dict] = None
    ) -> "TrackedSpool":
        """
        Parsea una fila de la tab `Lista` a TrackedSpool.

        Args:
            row: valores de la fila (4+ columnas).
            column_map: opcional, dict {normalized_name: index} producido por
                        ColumnMapCache. Si es None, se usan índices hardcoded.
        """
        idx_tag = _resolve_idx("TAG_SPOOL", 0, column_map)
        idx_added = _resolve_idx("Added_At", 1, column_map)
        idx_updated = _resolve_idx("Updated_At", 2, column_map)
        idx_notes = _resolve_idx("Notes", 3, column_map)

        notes_raw = row[idx_notes] if len(row) > idx_notes else ""
        notes = notes_raw if notes_raw else None

        return cls(
            tag_spool=row[idx_tag],
            added_at=_parse_sheets_datetime(row[idx_added]),
            updated_at=_parse_sheets_datetime(row[idx_updated]),
            notes=notes,
        )


# ─── AuditEvent (tab `Audit`) ─────────────────────────────────────────────────


class AuditEvent(BaseModel):
    """
    Una fila en la tab `Audit` del spreadsheet ZEUES_App_Audit.

    Inmutable (event sourcing). Append-only. El cliente genera `id` (UUID) y
    `session_id`; el repo deduplica por `id` antes de hacer append para que
    los reintentos sean seguros.

    Columnas: ID | Timestamp | Session_ID | Event_Type | TAG_SPOOL | Modal | Route | Payload_JSON
    """

    id: str = Field(
        default_factory=lambda: str(uuid.uuid4()),
        description="UUID del evento (cliente lo genera para idempotencia)",
        min_length=1,
    )
    timestamp: datetime = Field(
        default_factory=now_chile,
        description="Cuándo ocurrió el evento (timezone Santiago)",
    )
    session_id: str = Field(
        ...,
        description="UUID por pestaña/sesión del navegador",
        min_length=1,
    )
    event_type: EventType = Field(
        ...,
        description="Tipo de evento",
    )
    tag_spool: Optional[str] = Field(
        None,
        description="Spool relacionado, si aplica",
    )
    modal: Optional[str] = Field(
        None,
        description="Nombre del modal abierto/cerrado, si aplica",
        examples=["ActionModal", "MetrologiaModal", "AddSpoolModal"],
    )
    route: Optional[str] = Field(
        None,
        description="Ruta del navegador, si aplica",
        examples=["/", "/dashboard"],
    )
    payload_json: Optional[str] = Field(
        None,
        description=(
            "Payload extra serializado como string JSON. NO se parsea en backend "
            "para mantener el schema estable cuando el frontend agrega campos."
        ),
    )

    model_config = ConfigDict(
        frozen=True,
        str_strip_whitespace=True,
        json_schema_extra={
            "example": {
                "id": "550e8400-e29b-41d4-a716-446655440000",
                "timestamp": "08-05-2026 09:42:00",
                "session_id": "f47ac10b-58cc-4372-a567-0e02b2c3d479",
                "event_type": "MODAL_OPEN",
                "tag_spool": "MK-1344-GW-27133-002",
                "modal": "ActionModal",
                "route": "/",
                "payload_json": '{"trigger":"card_click"}',
            }
        },
    )

    def to_sheets_row(self) -> list[str]:
        """Serializa a fila para la tab `Audit` (8 columnas)."""
        return [
            self.id,
            format_datetime_for_sheets(self.timestamp),
            self.session_id,
            self.event_type.value,
            self.tag_spool or "",
            self.modal or "",
            self.route or "",
            self.payload_json or "",
        ]

    @classmethod
    def from_sheets_row(
        cls, row: list[str], column_map: Optional[dict] = None
    ) -> "AuditEvent":
        """Parsea una fila de la tab `Audit` a AuditEvent."""
        idx_id = _resolve_idx("ID", 0, column_map)
        idx_ts = _resolve_idx("Timestamp", 1, column_map)
        idx_session = _resolve_idx("Session_ID", 2, column_map)
        idx_event = _resolve_idx("Event_Type", 3, column_map)
        idx_tag = _resolve_idx("TAG_SPOOL", 4, column_map)
        idx_modal = _resolve_idx("Modal", 5, column_map)
        idx_route = _resolve_idx("Route", 6, column_map)
        idx_payload = _resolve_idx("Payload_JSON", 7, column_map)

        def opt(idx: int) -> Optional[str]:
            if idx >= len(row):
                return None
            value = row[idx]
            return value if value else None

        return cls(
            id=row[idx_id],
            timestamp=_parse_sheets_datetime(row[idx_ts]),
            session_id=row[idx_session],
            event_type=EventType(row[idx_event]),
            tag_spool=opt(idx_tag),
            modal=opt(idx_modal),
            route=opt(idx_route),
            payload_json=opt(idx_payload),
        )


# ─── AuditEventBatch (request envelope para POST /audit/batch) ────────────────


class AuditEventBatch(BaseModel):
    """
    Envelope de request para POST /api/supervisor/audit/batch.

    El máximo de 100 eventos por batch es para evitar requests gigantes en
    redes flakeas y para mantener cada flush dentro del límite de timing
    de Sheets API. El frontend acumula en buffer y flushea cada 30s.
    """

    events: list[AuditEvent] = Field(
        ...,
        description="Lote de eventos. Máximo 100 por request.",
        min_length=1,
        max_length=100,
    )

    model_config = ConfigDict(str_strip_whitespace=True)


# ─── LegacySnapshot (tab `Snapshots_Legacy`) ──────────────────────────────────


class LegacySnapshot(BaseModel):
    """
    Una fila en la tab `Snapshots_Legacy` del spreadsheet ZEUES_App_Audit.

    Capa 0 de la migración: antes de tocar nada, el frontend dumpea el
    contenido completo y verbatim de localStorage[zeues_v5_spool_tags] aquí.
    Si la migración fila-por-fila falla, el snapshot crudo es recuperable
    a mano: copias el `raw` de vuelta a localStorage del navegador.

    Inmutable. Idempotente por `snapshot_id` (cliente lo genera).

    Columnas: Snapshot_ID | Captured_At | Raw_JSON | User_Agent
    """

    snapshot_id: str = Field(
        ...,
        description="UUID generado por el cliente para idempotencia en reintentos",
        min_length=1,
    )
    captured_at: datetime = Field(
        default_factory=now_chile,
        description="Cuándo se capturó el snapshot (timezone Santiago)",
    )
    raw: str = Field(
        ...,
        description=(
            "El string verbatim de localStorage[zeues_v5_spool_tags]. "
            "NO se parsea — se preserva byte-por-byte para recovery manual."
        ),
        min_length=1,
    )
    user_agent: Optional[str] = Field(
        None,
        description="navigator.userAgent del navegador que capturó el snapshot",
    )

    model_config = ConfigDict(
        frozen=True,
        str_strip_whitespace=False,  # NO trim — el raw es bytes verbatim
        json_schema_extra={
            "example": {
                "snapshot_id": "550e8400-e29b-41d4-a716-446655440000",
                "captured_at": "08-05-2026 09:42:00",
                "raw": '[{"tag":"MK-1"}]',
                "user_agent": "Mozilla/5.0 (...)",
            }
        },
    )

    def to_sheets_row(self) -> list[str]:
        """Serializa a fila para la tab `Snapshots_Legacy` (4 columnas)."""
        return [
            self.snapshot_id,
            format_datetime_for_sheets(self.captured_at),
            self.raw,
            self.user_agent or "",
        ]

    @classmethod
    def from_sheets_row(
        cls, row: list[str], column_map: Optional[dict] = None
    ) -> "LegacySnapshot":
        """Parsea una fila de la tab `Snapshots_Legacy` a LegacySnapshot."""
        idx_id = _resolve_idx("Snapshot_ID", 0, column_map)
        idx_captured = _resolve_idx("Captured_At", 1, column_map)
        idx_raw = _resolve_idx("Raw_JSON", 2, column_map)
        idx_ua = _resolve_idx("User_Agent", 3, column_map)

        ua = row[idx_ua] if len(row) > idx_ua and row[idx_ua] else None

        return cls(
            snapshot_id=row[idx_id],
            captured_at=_parse_sheets_datetime(row[idx_captured]),
            raw=row[idx_raw],
            user_agent=ua,
        )
