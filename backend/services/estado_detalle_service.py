"""
EstadoDetalleService - Detects manual Estado_Detalle changes by supervisors.

Monitors for BLOQUEADO → RECHAZADO transitions that indicate supervisor override
of the 3-cycle blocking rule. Automatically logs these interventions to Metadata.

Phase 6 feature:
- Detects when a BLOQUEADO spool is manually changed to RECHAZADO
- Logs SUPERVISOR_OVERRIDE event to audit trail
- Called during spool fetch operations to maintain audit trail
"""

import logging
import uuid
import json
from datetime import datetime
from typing import Optional

from backend.repositories.sheets_repository import SheetsRepository
from backend.repositories.metadata_repository import MetadataRepository
from backend.models.enums import EventoTipo

logger = logging.getLogger(__name__)


class EstadoDetalleService:
    """
    Service for detecting and logging supervisor overrides of Estado_Detalle.

    Monitors for manual changes that bypass system rules (e.g., BLOQUEADO → RECHAZADO)
    and maintains audit trail of supervisor interventions.
    """

    def __init__(
        self,
        sheets_repo: SheetsRepository,
        metadata_repo: MetadataRepository
    ):
        """
        Initialize estado detalle service with injected dependencies.

        Args:
            sheets_repo: Repository for reading current Estado_Detalle from Sheets
            metadata_repo: Repository for logging override events
        """
        self.sheets_repo = sheets_repo
        self.metadata_repo = metadata_repo
        logger.info("EstadoDetalleService initialized")

    def detect_supervisor_override(self, tag_spool: str) -> Optional[dict]:
        """
        Detect if supervisor manually changed BLOQUEADO → RECHAZADO.

        Flow:
        1. Read current Estado_Detalle from Operaciones sheet
        2. Get last metadata event for this spool
        3. If last event shows BLOQUEADO and current is RECHAZADO:
           - Log SUPERVISOR_OVERRIDE event to Metadata
           - Include previous/new estado in metadata_json
           - Use worker_id=0 for system events
        4. Return override details if detected

        Args:
            tag_spool: Spool identifier to check

        Returns:
            dict with override details if detected, None otherwise
            Example: {
                "detected": True,
                "previous_estado": "BLOQUEADO",
                "current_estado": "RECHAZADO (Ciclo 2/3)",
                "event_id": "uuid-string"
            }

        Raises:
            None - Best-effort detection, logs warnings on failures
        """
        try:
            # Step 1: Read current Estado_Detalle from Sheets
            spool = self.sheets_repo.get_spool_by_tag(tag_spool)
            if not spool:
                logger.warning(f"Spool {tag_spool} not found for override detection")
                return None

            current_estado = spool.estado_detalle or ""
            logger.debug(f"Current Estado_Detalle for {tag_spool}: '{current_estado}'")

            # Step 2: Get last metadata event for this spool
            try:
                all_events = self.metadata_repo.get_events_by_spool(tag_spool)
                if not all_events:
                    logger.debug(f"No previous events found for {tag_spool}")
                    return None

                # Get the most recent event (events are sorted by timestamp)
                last_event = all_events[-1]
                last_estado = self._extract_estado_from_metadata(last_event)
                logger.debug(f"Last recorded Estado_Detalle for {tag_spool}: '{last_estado}'")

            except Exception as e:
                logger.warning(f"Failed to retrieve last event for {tag_spool}: {e}")
                return None

            # Step 3: Check for BLOQUEADO → RECHAZADO transition
            is_override = (
                "BLOQUEADO" in last_estado and
                "RECHAZADO" in current_estado and
                "BLOQUEADO" not in current_estado
            )

            if not is_override:
                # Normal transition, no override detected
                return None

            logger.info(f"🚨 Supervisor override detected: {tag_spool} changed from BLOQUEADO to RECHAZADO")

            # Step 4: Log SUPERVISOR_OVERRIDE event
            try:
                event_id = str(uuid.uuid4())
                metadata_json = json.dumps({
                    "previous_estado": last_estado,
                    "new_estado": current_estado,
                    "detection_timestamp": datetime.utcnow().isoformat() + "Z",
                    "override_type": "BLOQUEADO_TO_RECHAZADO"
                })

                metadata_event = {
                    "id": event_id,
                    "timestamp": datetime.utcnow().isoformat() + "Z",
                    "evento_tipo": "SUPERVISOR_OVERRIDE",  # New event type
                    "tag_spool": tag_spool,
                    "worker_id": 0,  # System event
                    "worker_nombre": "SYSTEM",
                    "operacion": "REPARACION",
                    "accion": "OVERRIDE",
                    "fecha_operacion": datetime.utcnow().date().isoformat(),
                    "metadata_json": metadata_json
                }

                self.metadata_repo.append_event(metadata_event)
                logger.info(f"✅ Supervisor override logged: {tag_spool} (event: {event_id})")

                return {
                    "detected": True,
                    "previous_estado": last_estado,
                    "current_estado": current_estado,
                    "event_id": event_id
                }

            except Exception as e:
                logger.error(f"Failed to log supervisor override for {tag_spool}: {e}")
                # Return detection result even if logging fails
                return {
                    "detected": True,
                    "previous_estado": last_estado,
                    "current_estado": current_estado,
                    "event_id": None,
                    "error": str(e)
                }

        except Exception as e:
            logger.error(f"Error during override detection for {tag_spool}: {e}")
            return None

    def _extract_estado_from_metadata(self, event) -> str:
        """
        Extract Estado_Detalle from metadata event.

        Looks in metadata_json for estado information, or derives from evento_tipo.

        Args:
            event: MetadataEvent Pydantic model

        Returns:
            str: Estado_Detalle value (empty string if not found)
        """
        try:
            # Try to get estado from metadata_json
            metadata_json_str = event.metadata_json or "{}"
            metadata = json.loads(metadata_json_str)

            # Check common keys for estado information
            estado = metadata.get("estado_detalle") or metadata.get("state") or metadata.get("previous_estado", "")

            # If not in metadata, derive from evento_tipo
            if not estado:
                evento_tipo = str(event.evento_tipo)
                if "COMPLETAR_REPARACION" in evento_tipo:
                    estado = "PENDIENTE_METROLOGIA"
                elif "TOMAR_REPARACION" in evento_tipo:
                    estado = "EN_REPARACION"
                elif "PAUSAR_REPARACION" in evento_tipo:
                    estado = "REPARACION_PAUSADA"
                elif "RECHAZAR_METROLOGIA" in evento_tipo or "RECHAZAR" in evento_tipo:
                    # Try to extract cycle info from metadata
                    cycle = metadata.get("cycle", 0)
                    if cycle >= 3:
                        estado = "BLOQUEADO"
                    else:
                        estado = f"RECHAZADO (Ciclo {cycle}/3)"

            return estado

        except Exception as e:
            logger.warning(f"Failed to extract estado from metadata: {e}")
            return ""

    def check_spools_for_overrides(self, tag_spools: list[str]) -> list[dict]:
        """
        Batch check multiple spools for supervisor overrides.

        Useful for periodic auditing or during spool list fetch operations.

        Args:
            tag_spools: List of spool identifiers to check

        Returns:
            list[dict]: List of override detection results (only includes detected overrides)
        """
        overrides = []

        for tag_spool in tag_spools:
            result = self.detect_supervisor_override(tag_spool)
            if result and result.get("detected"):
                overrides.append(result)

        if overrides:
            logger.info(f"Found {len(overrides)} supervisor overrides in batch of {len(tag_spools)} spools")
        else:
            logger.debug(f"No supervisor overrides detected in batch of {len(tag_spools)} spools")

        return overrides
