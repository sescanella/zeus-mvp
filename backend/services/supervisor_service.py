"""
SupervisorService — orquestación entre router y SupervisorRepository.

Single-user (Matías). No worker_id; cada mutación se identifica por session_id
(UUID por pestaña/sesión, generado por el frontend).

Garantías clave:
- Cada cambio de lista (add/remove/priority) emite un AuditEvent server-side.
  Si el audit append falla, se loggea pero NO bloquea la mutación principal.
- TAG_SPOOL no se valida contra el sheet de operaciones — single source of
  truth para la lista del supervisor es el sheet de auditoría.
"""
import json
import logging
from datetime import datetime
from typing import Optional

from backend.models.supervisor import (
    AuditEvent,
    EventType,
    LegacySnapshot,
    TrackedSpool,
)
from backend.repositories.supervisor_repository import SupervisorRepository
from backend.utils.date_formatter import now_chile

logger = logging.getLogger(__name__)


class SupervisorService:
    """
    Lógica de negocio para la lista y auditoría del supervisor.

    Validaciones:
    - tag_spool no vacío (post-strip).
    - priority en {0, 1, 2, 3}.
    - session_id no vacío.
    Las violaciones lanzan ValueError; el router las traduce a HTTP 400.
    """

    VALID_PRIORITIES = {0, 1, 2, 3}

    def __init__(self, supervisor_repo: SupervisorRepository):
        self.repo = supervisor_repo

    # ─── Validation helpers ──────────────────────────────────────────────

    @staticmethod
    def _validate_tag(tag_spool: str) -> str:
        """Strip y validar no-vacío. Devuelve la versión normalizada."""
        if not isinstance(tag_spool, str):
            raise ValueError("tag_spool debe ser string")
        clean = tag_spool.strip()
        if not clean:
            raise ValueError("tag_spool no puede estar vacío")
        return clean

    @classmethod
    def _validate_priority(cls, priority: int) -> int:
        if priority not in cls.VALID_PRIORITIES:
            raise ValueError("priority debe ser 0, 1, 2 o 3")
        return priority

    @staticmethod
    def _validate_session(session_id: str) -> str:
        if not isinstance(session_id, str) or not session_id.strip():
            raise ValueError("session_id requerido")
        return session_id.strip()

    # ─── Audit emission (best-effort, non-blocking) ──────────────────────

    def _emit_list_audit(
        self,
        event_type: EventType,
        tag_spool: str,
        session_id: str,
        payload: Optional[dict] = None,
    ) -> None:
        """
        Emite un evento de cambio de lista al audit Sheet.

        Si la escritura del audit falla, se loggea ERROR pero no se rethrow
        — la mutación principal de la lista ya fue exitosa y no queremos
        invalidarla por un fallo transitorio del Sheet.
        """
        event = AuditEvent(
            session_id=session_id,
            event_type=event_type,
            tag_spool=tag_spool,
            payload_json=json.dumps(payload, ensure_ascii=False) if payload else None,
        )
        try:
            self.repo.append_audit_events([event])
        except Exception as exc:
            logger.error(
                f"Failed to emit list audit event ({event_type.value}) "
                f"for {tag_spool}: {exc}",
                exc_info=True,
            )

    # ─── Lista — read ────────────────────────────────────────────────────

    def list_tracked_spools(self) -> list[TrackedSpool]:
        """Lee la lista completa que Matías está siguiendo."""
        return self.repo.list_tracked_spools()

    # ─── Lista — mutations ───────────────────────────────────────────────

    def add_to_list(
        self,
        tag_spool: str,
        priority: int = 0,
        session_id: str = "",
    ) -> TrackedSpool:
        """
        Agrega (o re-agrega, idempotente) un spool a la lista.

        Si el tag ya existía, su fila se actualiza con la nueva prioridad y
        timestamps frescos. Emite LIST_ADD.
        """
        clean_tag = self._validate_tag(tag_spool)
        self._validate_priority(priority)
        clean_session = self._validate_session(session_id)

        spool = TrackedSpool(tag_spool=clean_tag, priority=priority)
        written = self.repo.upsert_tracked_spool(spool)

        self._emit_list_audit(
            EventType.LIST_ADD,
            written.tag_spool,
            clean_session,
            payload={"priority": priority},
        )
        return written

    def remove_from_list(self, tag_spool: str, session_id: str) -> bool:
        """
        Elimina un spool de la lista. Idempotente.

        Returns:
            True si se borró una fila, False si la tag no estaba.
            Solo emite LIST_REMOVE si efectivamente se borró (evita audit ruidoso).
        """
        clean_tag = self._validate_tag(tag_spool)
        clean_session = self._validate_session(session_id)

        deleted = self.repo.remove_tracked_spool(clean_tag)
        if deleted:
            self._emit_list_audit(
                EventType.LIST_REMOVE, clean_tag, clean_session
            )
        return deleted

    def set_priority(
        self,
        tag_spool: str,
        priority: int,
        session_id: str,
    ) -> TrackedSpool:
        """
        Cambia la prioridad de un spool, preservando added_at y notes.

        Si el tag no existe, crea una fila nueva (semánticamente equivale
        a un add). Emite LIST_PRIORITY con la prioridad anterior y la nueva
        en el payload.
        """
        clean_tag = self._validate_tag(tag_spool)
        self._validate_priority(priority)
        clean_session = self._validate_session(session_id)

        existing = self._find_existing(clean_tag)
        if existing is None:
            spool = TrackedSpool(tag_spool=clean_tag, priority=priority)
            previous_priority: Optional[int] = None
        else:
            spool = TrackedSpool(
                tag_spool=existing.tag_spool,
                priority=priority,
                added_at=existing.added_at,
                updated_at=now_chile(),
                notes=existing.notes,
            )
            previous_priority = existing.priority

        written = self.repo.upsert_tracked_spool(spool)

        self._emit_list_audit(
            EventType.LIST_PRIORITY,
            written.tag_spool,
            clean_session,
            payload={
                "priority": priority,
                "previous_priority": previous_priority,
            },
        )
        return written

    def _find_existing(self, tag_spool: str) -> Optional[TrackedSpool]:
        """
        Busca el TrackedSpool actual para un tag, o None si no existe.

        Linealiza la lista completa. Es OK porque la lista del supervisor es
        chica (~100 filas máx). Si crece mucho, agregar repo.get_tracked_spool.
        """
        for s in self.repo.list_tracked_spools():
            if s.tag_spool == tag_spool:
                return s
        return None

    # ─── Audit — passthroughs ────────────────────────────────────────────

    def record_audit_batch(self, events: list[AuditEvent]) -> int:
        """
        Append un lote de eventos de UI al Audit tab.

        Sin validación adicional — la Pydantic AuditEventBatch (max 100,
        min 1) ya valida la estructura. El repo dedup por id.
        """
        return self.repo.append_audit_events(events)

    def get_audit_since(self, since: datetime) -> list[AuditEvent]:
        """Endpoint de debug: lee eventos con timestamp >= since."""
        return self.repo.get_audit_events_since(since)

    def record_legacy_snapshot(self, snapshot: LegacySnapshot) -> bool:
        """
        Persiste un snapshot crudo de localStorage (Capa 0 de migración).

        Idempotente por snapshot_id. Returns True si escribió, False si ya
        existía (multi-tab race / retry).
        """
        return self.repo.append_legacy_snapshot(snapshot)
