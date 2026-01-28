"""
MetrologiaService - Orchestrator for instant quality inspection workflow.

Manages binary APROBADO/RECHAZADO outcomes without occupation periods.
Skips TOMAR phase entirely - inspection completes in single atomic operation.

v3.0 Phase 5 feature:
- Instant completion (no en_progreso state)
- Binary resultado (APROBADO/RECHAZADO)
- No Redis locking (no occupation)
- Metadata logging with resultado in metadata_json
"""

import logging
import uuid
import json
from datetime import date, datetime
from typing import Literal

from backend.domain.state_machines.metrologia_machine import MetrologiaStateMachine
from backend.services.validation_service import ValidationService
from backend.repositories.sheets_repository import SheetsRepository
from backend.repositories.metadata_repository import MetadataRepository
from backend.services.redis_event_service import RedisEventService
from backend.exceptions import SpoolNoEncontradoError
from backend.models.enums import EventoTipo

logger = logging.getLogger(__name__)


class MetrologiaService:
    """
    Service for instant metrología inspection workflow.

    Orchestrates:
    - Prerequisite validation (ARM + SOLD complete, not occupied)
    - State machine transitions (aprobar/rechazar)
    - Fecha_QC_Metrologia column updates
    - Metadata event logging
    - SSE event publishing for dashboard
    """

    def __init__(
        self,
        validation_service: ValidationService,
        sheets_repository: SheetsRepository,
        metadata_repository: MetadataRepository,
        redis_event_service: RedisEventService
    ):
        """
        Initialize metrología service with injected dependencies.

        Args:
            validation_service: Service for prerequisite validation
            sheets_repository: Repository for Sheets reads/writes
            metadata_repository: Repository for audit logging
            redis_event_service: Service for real-time event publishing
        """
        self.validation_service = validation_service
        self.sheets_repo = sheets_repository
        self.metadata_repo = metadata_repository
        self.redis_event_service = redis_event_service
        logger.info("MetrologiaService initialized with instant completion workflow")

    def completar(
        self,
        tag_spool: str,
        worker_id: int,
        worker_nombre: str,
        resultado: Literal["APROBADO", "RECHAZADO"]
    ) -> dict:
        """
        Complete metrología inspection with binary result.

        Flow:
        1. Fetch spool and validate prerequisites
        2. Instantiate state machine
        3. Trigger aprobar/rechazar transition based on resultado
        4. Update Fecha_QC_Metrologia via state machine callback
        5. Log metadata event with resultado
        6. Publish SSE event for dashboard

        Args:
            tag_spool: Spool identifier
            worker_id: Inspector worker ID
            worker_nombre: Inspector name in format "INICIALES(ID)"
            resultado: Binary inspection result (APROBADO/RECHAZADO)

        Returns:
            dict with success message and resultado

        Raises:
            SpoolNoEncontradoError: If spool doesn't exist
            DependenciasNoSatisfechasError: If ARM or SOLD not completed
            OperacionYaCompletadaError: If metrología already done
            SpoolOccupiedError: If spool currently occupied
            RolNoAutorizadoError: If worker lacks METROLOGIA role
        """
        logger.info(
            f"MetrologiaService.completar: {tag_spool} by {worker_nombre} -> {resultado}"
        )

        # Step 1: Fetch spool and validate prerequisites
        spool = self.sheets_repo.get_spool_by_tag(tag_spool)
        if not spool:
            raise SpoolNoEncontradoError(tag_spool)

        self.validation_service.validar_puede_completar_metrologia(spool, worker_id)

        # Step 2: Instantiate state machine
        metrologia_machine = MetrologiaStateMachine(
            tag_spool=tag_spool,
            sheets_repo=self.sheets_repo,
            metadata_repo=self.metadata_repo
        )

        # Step 3: Trigger state transition based on resultado
        fecha_operacion = date.today()
        if resultado == "APROBADO":
            metrologia_machine.aprobar(fecha_operacion=fecha_operacion)
            logger.info(f"METROLOGIA APROBADO: {tag_spool}")
        else:  # RECHAZADO
            metrologia_machine.rechazar(fecha_operacion=fecha_operacion)
            logger.info(f"METROLOGIA RECHAZADO: {tag_spool}")

        # Step 4: Log metadata event (Fecha_QC_Metrologia already updated by state machine)
        evento_tipo = (
            EventoTipo.COMPLETAR_METROLOGIA
            if hasattr(EventoTipo, 'COMPLETAR_METROLOGIA')
            else "COMPLETAR_METROLOGIA"
        )

        metadata_event = {
            "id": str(uuid.uuid4()),
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "evento_tipo": evento_tipo,
            "tag_spool": tag_spool,
            "worker_id": worker_id,
            "worker_nombre": worker_nombre,
            "operacion": "METROLOGIA",
            "accion": "COMPLETAR",
            "fecha_operacion": fecha_operacion.isoformat(),
            "metadata_json": json.dumps({
                "resultado": resultado,
                "state": metrologia_machine.get_state_id()
            })
        }

        # Log to Metadata sheet (best-effort)
        try:
            self.metadata_repo.append_event(metadata_event)
        except Exception as e:
            logger.warning(f"Failed to log metadata for {tag_spool}: {e}")

        # Step 5: Publish SSE event for dashboard (best-effort)
        try:
            event_data = {
                "tag_spool": tag_spool,
                "worker_id": worker_id,
                "worker_nombre": worker_nombre,
                "operacion": "METROLOGIA",
                "accion": "COMPLETAR",
                "resultado": resultado,
                "timestamp": datetime.utcnow().isoformat() + "Z"
            }
            self.redis_event_service.publish_state_change(
                event_type="COMPLETAR_METROLOGIA",
                data=event_data
            )
        except Exception as e:
            logger.warning(f"Failed to publish SSE event for {tag_spool}: {e}")

        logger.info(f"✅ MetrologiaService.completar: {tag_spool} -> {resultado}")
        return {
            "success": True,
            "message": f"Metrología {resultado.lower()} para spool {tag_spool}",
            "resultado": resultado,
            "tag_spool": tag_spool,
            "fecha_operacion": fecha_operacion.isoformat()
        }
