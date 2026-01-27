"""
HistoryService - Occupation history aggregation from Metadata events.

Aggregates Metadata events into occupation timeline showing which workers
worked on each spool and for how long.

v3.0 Phase 3: Complete occupation history visibility (COLLAB-04).
"""

import logging
from typing import List, Optional
from datetime import datetime

from backend.repositories.metadata_repository import MetadataRepository
from backend.repositories.sheets_repository import SheetsRepository
from backend.models.history import OccupationSession, HistoryResponse
from backend.models.metadata import EventoTipo
from backend.exceptions import SpoolNoEncontradoError

logger = logging.getLogger(__name__)


class HistoryService:
    """
    Service for aggregating occupation history from Metadata events.

    Provides:
    - Occupation timeline showing worker sessions
    - Duration calculation between TOMAR and PAUSAR/COMPLETAR
    - Human-readable duration format (e.g., "2h 15m")
    """

    def __init__(
        self,
        metadata_repository: MetadataRepository,
        sheets_repository: SheetsRepository
    ):
        """
        Initialize history service with injected dependencies.

        Args:
            metadata_repository: Repository for reading Metadata events
            sheets_repository: Repository for spool verification
        """
        self.metadata_repo = metadata_repository
        self.sheets_repo = sheets_repository

    async def get_occupation_history(self, tag_spool: str) -> HistoryResponse:
        """
        Retrieve occupation history for a spool.

        Returns chronological list of workers who worked on spool
        with durations calculated from TOMAR/PAUSAR/COMPLETAR events.

        Args:
            tag_spool: Spool TAG identifier

        Returns:
            HistoryResponse with sessions showing worker timeline

        Raises:
            SpoolNoEncontradoError: If spool doesn't exist
        """
        logger.info(f"[HISTORY] Building occupation history for {tag_spool}")

        # Verify spool exists
        spool = self.sheets_repo.get_spool_by_tag(tag_spool)
        if not spool:
            raise SpoolNoEncontradoError(f"Spool {tag_spool} not found")

        # Query Metadata for all occupation-related events
        # Note: We include all COMPLETAR events since they end occupation sessions
        events = self.metadata_repo.get_events_by_spool(tag_spool)

        # Filter to occupation-related events only
        occupation_event_types = {
            EventoTipo.TOMAR_SPOOL,
            EventoTipo.PAUSAR_SPOOL,
            EventoTipo.COMPLETAR_ARM,
            EventoTipo.COMPLETAR_SOLD,
            # TOMAR_SPOOL is the generic v3.0 event type
            # Keep COMPLETAR_* for backward compatibility with v2.x events
        }

        occupation_events = [
            e for e in events
            if e.evento_tipo in occupation_event_types
        ]

        logger.info(
            f"[HISTORY] Found {len(occupation_events)} occupation events "
            f"for {tag_spool} (from {len(events)} total events)"
        )

        # Build session timeline
        sessions = self._build_sessions(occupation_events)

        logger.info(
            f"[HISTORY] Aggregated {len(sessions)} occupation sessions "
            f"for {tag_spool}"
        )

        return HistoryResponse(
            tag_spool=tag_spool,
            sessions=sessions
        )

    def _build_sessions(
        self,
        events: List
    ) -> List[OccupationSession]:
        """
        Build occupation sessions from chronological events.

        Matches TOMAR_SPOOL with corresponding PAUSAR/COMPLETAR events
        to create complete sessions with durations.

        Args:
            events: Chronological list of occupation events

        Returns:
            List of occupation sessions
        """
        sessions = []
        current_session: Optional[dict] = None

        for event in events:
            if event.evento_tipo == EventoTipo.TOMAR_SPOOL:
                # Start new session
                # If there's an unclosed session, close it without end time
                if current_session:
                    sessions.append(
                        OccupationSession(**current_session)
                    )

                current_session = {
                    "worker_nombre": event.worker_nombre,
                    "worker_id": event.worker_id,
                    "operacion": event.operacion,
                    "start_time": event.timestamp,
                    "end_time": None,
                    "duration": None
                }
                logger.debug(
                    f"[HISTORY] Started session: {event.worker_nombre} "
                    f"on {event.operacion} at {event.timestamp}"
                )

            elif event.evento_tipo in {
                EventoTipo.PAUSAR_SPOOL,
                EventoTipo.COMPLETAR_ARM,
                EventoTipo.COMPLETAR_SOLD
            }:
                # Close current session
                if current_session:
                    # Verify operation matches (COMPLETAR events are operation-specific)
                    session_op = current_session["operacion"]
                    if event.evento_tipo == EventoTipo.PAUSAR_SPOOL or \
                       (event.evento_tipo == EventoTipo.COMPLETAR_ARM and session_op == "ARM") or \
                       (event.evento_tipo == EventoTipo.COMPLETAR_SOLD and session_op == "SOLD"):

                        current_session["end_time"] = event.timestamp
                        current_session["duration"] = self._calculate_duration(
                            current_session["start_time"],
                            event.timestamp
                        )
                        sessions.append(
                            OccupationSession(**current_session)
                        )
                        logger.debug(
                            f"[HISTORY] Closed session: {current_session['worker_nombre']} "
                            f"duration {current_session['duration']}"
                        )
                        current_session = None
                    else:
                        logger.warning(
                            f"[HISTORY] Event {event.evento_tipo} doesn't match "
                            f"session operation {session_op}, ignoring"
                        )
                else:
                    logger.warning(
                        f"[HISTORY] Found {event.evento_tipo} without TOMAR, "
                        f"skipping orphan event"
                    )

        # If there's an unclosed session at the end, add it
        if current_session:
            logger.debug(
                f"[HISTORY] Session still in progress: "
                f"{current_session['worker_nombre']} on {current_session['operacion']}"
            )
            sessions.append(
                OccupationSession(**current_session)
            )

        return sessions

    def _calculate_duration(self, start: datetime, end: datetime) -> str:
        """
        Format duration as 'Xh Ym' for human readability.

        Args:
            start: Session start timestamp
            end: Session end timestamp

        Returns:
            Human-readable duration string (e.g., "2h 15m", "45m")
        """
        delta = end - start
        hours = delta.seconds // 3600
        minutes = (delta.seconds % 3600) // 60

        if hours > 0:
            return f"{hours}h {minutes}m"
        else:
            return f"{minutes}m"
