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
from datetime import date, datetime
from typing import Literal

from backend.utils.date_formatter import format_datetime_for_sheets, format_date_for_sheets, now_chile
from backend.domain.state_machines.metrologia_machine import MetrologiaStateMachine
from backend.services.validation_service import ValidationService
from backend.repositories.sheets_repository import SheetsRepository
from backend.repositories.metadata_repository import MetadataRepository
from backend.exceptions import SpoolNoEncontradoError
from backend.services.metadata_event_builder import MetadataEventBuilder

logger = logging.getLogger(__name__)


class MetrologiaService:
    """
    Service for instant metrología inspection workflow.

    Orchestrates:
    - Prerequisite validation (ARM + SOLD complete, not occupied)
    - State machine transitions (aprobar/rechazar)
    - Fecha_QC_Metrologia column updates
    - Metadata event logging

    Single-user mode: No SSE event publishing needed.
    """

    def __init__(
        self,
        validation_service: ValidationService,
        sheets_repository: SheetsRepository,
        metadata_repository: MetadataRepository
    ):
        """
        Initialize metrología service with injected dependencies.

        Args:
            validation_service: Service for prerequisite validation
            sheets_repository: Repository for Sheets reads/writes
            metadata_repository: Repository for audit logging
        """
        self.validation_service = validation_service
        self.sheets_repo = sheets_repository
        self.metadata_repo = metadata_repository
        logger.info("MetrologiaService initialized with instant completion workflow")

    async def completar(
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
        try:
            event = (
                MetadataEventBuilder()
                .for_metrologia(tag_spool, worker_id, worker_nombre, resultado)
                .with_operacion("METROLOGIA")
                .with_metadata({
                    "resultado": resultado,
                    "state": metrologia_machine.get_state_id()
                })
                .build()
            )
            self.metadata_repo.append_event(event)
        except Exception as e:
            logger.warning(f"Failed to log metadata for {tag_spool}: {e}")

        # Step 5: Build estado_detalle for SSE event
        from backend.services.estado_detalle_builder import EstadoDetalleBuilder
        builder = EstadoDetalleBuilder()
        estado_detalle = builder.build(
            ocupado_por=spool.ocupado_por,
            arm_state="completado",  # ARM always complete for metrología
            sold_state="completado",  # SOLD always complete for metrología
            metrologia_state=metrologia_machine.get_state_id()
        )

        logger.info(f"✅ MetrologiaService.completar: {tag_spool} -> {resultado}")
        return {
            "success": True,
            "message": f"Metrología {resultado.lower()} para spool {tag_spool}",
            "resultado": resultado,
            "tag_spool": tag_spool,
            "fecha_operacion": format_date_for_sheets(fecha_operacion)
        }
