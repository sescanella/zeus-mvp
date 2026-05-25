"""
ReparacionService - Orchestrator for reparación workflow.

Manages RECHAZADO spool repair with TOMAR/PAUSAR/COMPLETAR/CANCELAR actions.

Features:
- Multi-worker access (no role restriction)
- TOMAR/PAUSAR/COMPLETAR pattern (occupation-based workflow)
- Automatic return to PENDIENTE_METROLOGIA after completion
- No rejection-cycle limit: a spool can be rejected and repaired as many
  times as needed; there is no automatic BLOQUEADO state.
"""

import logging
from datetime import date, datetime

from backend.utils.date_formatter import format_datetime_for_sheets, format_date_for_sheets, now_chile, today_chile
from backend.services.state_machines.reparacion_state_machine import (
    REPARACIONStateMachine,
    ESTADO_DETALLE_RECHAZADO,
    ESTADO_DETALLE_REPARACION_PAUSADA,
    ESTADO_DETALLE_PENDIENTE_METROLOGIA,
    _build_en_reparacion_estado,
)
from backend.services.validation_service import ValidationService
from backend.repositories.sheets_repository import SheetsRepository
from backend.repositories.metadata_repository import MetadataRepository
from backend.exceptions import SpoolNoEncontradoError
from backend.services.metadata_event_builder import MetadataEventBuilder

logger = logging.getLogger(__name__)


class ReparacionService:
    """
    Service for reparación workflow with occupation management.

    Single-user mode:
    - State machine transitions (tomar/pausar/completar/cancelar)
    - Ocupado_Por, Fecha_Ocupacion, Estado_Detalle column updates
    - Metadata event logging
    """

    def __init__(
        self,
        validation_service: ValidationService,
        sheets_repository: SheetsRepository,
        metadata_repository: MetadataRepository
    ):
        """
        Initialize reparación service with injected dependencies.

        Args:
            validation_service: Service for prerequisite validation
            sheets_repository: Repository for Sheets reads/writes
            metadata_repository: Repository for audit logging
        """
        self.validation_service = validation_service
        self.sheets_repo = sheets_repository
        self.metadata_repo = metadata_repository
        logger.info("ReparacionService initialized (single-user mode, no cycle limit)")

    async def tomar_reparacion(
        self,
        tag_spool: str,
        worker_id: int,
        worker_nombre: str
    ) -> dict:
        """
        Worker takes RECHAZADO spool for repair.

        Flow:
        1. Fetch spool and validate can TOMAR (RECHAZADO/REPARACION_PAUSADA, not occupied)
        2. Instantiate state machine hydrated to current state
        3. Trigger TOMAR transition (state machine writes Ocupado_Por,
           Fecha_Ocupacion, Estado_Detalle)
        4. Log metadata event

        Args:
            tag_spool: Spool identifier
            worker_id: Worker ID
            worker_nombre: Worker name in format "INICIALES(ID)"

        Returns:
            dict with success message and estado_detalle

        Raises:
            SpoolNoEncontradoError: If spool doesn't exist
            OperacionNoDisponibleError: If spool not in RECHAZADO state
            SpoolOccupiedError: If spool currently occupied
        """
        logger.info(f"ReparacionService.tomar_reparacion: {tag_spool} by {worker_nombre}")

        # Step 1: Fetch spool and validate can TOMAR
        spool = self.sheets_repo.get_spool_by_tag(tag_spool)
        if not spool:
            raise SpoolNoEncontradoError(tag_spool)

        self.validation_service.validar_puede_tomar_reparacion(spool, worker_id)

        # Step 2: Instantiate state machine hydrated to current state
        # (python-statemachine 2.5.0 async engine ignores direct assignment
        # to .current_state — must pass start_value to the constructor and
        # call activate_initial_state() before triggering transitions).
        if spool.estado_detalle and "REPARACION_PAUSADA" in spool.estado_detalle:
            start_state = "reparacion_pausada"
        else:
            start_state = "rechazado"

        reparacion_machine = REPARACIONStateMachine(
            tag_spool=tag_spool,
            sheets_repo=self.sheets_repo,
            metadata_repo=self.metadata_repo,
            start_value=start_state,
        )
        await reparacion_machine.activate_initial_state()

        # Trigger TOMAR transition
        await reparacion_machine.tomar(worker_id=worker_id, worker_nombre=worker_nombre)
        logger.info(f"REPARACION TOMAR: {tag_spool} -> {reparacion_machine.current_state.id}")

        # Step 3: Log metadata event (Ocupado_Por/Fecha_Ocupacion/Estado_Detalle already updated by state machine)
        try:
            event = (
                MetadataEventBuilder()
                .for_tomar(tag_spool, worker_id, worker_nombre)
                .with_operacion("REPARACION")
                .with_metadata({
                    "state": reparacion_machine.get_state_id()
                })
                .build()
            )
            self.metadata_repo.log_event(**event)
        except Exception as e:
            logger.error(
                f"CRITICAL: Metadata audit trail logging failed for {tag_spool}: {e}",
                exc_info=True
            )

        estado_detalle = _build_en_reparacion_estado(worker_nombre)

        logger.info(f"✅ ReparacionService.tomar_reparacion: {tag_spool}")
        return {
            "success": True,
            "message": f"Reparación tomada para spool {tag_spool}",
            "tag_spool": tag_spool,
            "worker_nombre": worker_nombre,
            "estado_detalle": estado_detalle
        }

    async def pausar_reparacion(
        self,
        tag_spool: str,
        worker_id: int
    ) -> dict:
        """
        Worker pauses repair work and releases occupation.

        Flow:
        1. Fetch spool and validate ownership
        2. Instantiate state machine and trigger PAUSAR transition
        3. Clear Ocupado_Por, Fecha_Ocupacion, update Estado_Detalle via state machine callback
        4. Log metadata event

        Args:
            tag_spool: Spool identifier
            worker_id: Worker ID (for ownership verification)

        Returns:
            dict with success message and estado_detalle

        Raises:
            SpoolNoEncontradoError: If spool doesn't exist
            OperacionNoIniciadaError: If spool not in EN_REPARACION state
            NoAutorizadoError: If spool occupied by different worker
        """
        logger.info(f"ReparacionService.pausar_reparacion: {tag_spool}")

        # Step 1: Fetch spool and validate ownership
        spool = self.sheets_repo.get_spool_by_tag(tag_spool)
        if not spool:
            raise SpoolNoEncontradoError(tag_spool)

        # Validate ownership (spool must be EN_REPARACION and occupied by this worker)
        if not spool.ocupado_por or f"({worker_id})" not in spool.ocupado_por:
            from backend.exceptions import NoAutorizadoError
            raise NoAutorizadoError(
                f"Spool {tag_spool} no está ocupado por este trabajador"
            )

        # Step 2: Instantiate state machine hydrated to EN_REPARACION
        reparacion_machine = REPARACIONStateMachine(
            tag_spool=tag_spool,
            sheets_repo=self.sheets_repo,
            metadata_repo=self.metadata_repo,
            start_value="en_reparacion",
        )
        await reparacion_machine.activate_initial_state()

        # Trigger PAUSAR transition
        await reparacion_machine.pausar()
        logger.info(f"REPARACION PAUSAR: {tag_spool} -> {reparacion_machine.current_state.id}")

        # Step 3: Log metadata event
        try:
            event = (
                MetadataEventBuilder()
                .for_pausar(tag_spool, worker_id, spool.ocupado_por)  # Use current worker name
                .with_operacion("REPARACION")
                .with_metadata({
                    "state": reparacion_machine.get_state_id()
                })
                .build()
            )
            self.metadata_repo.log_event(**event)
        except Exception as e:
            logger.error(
                f"CRITICAL: Metadata audit trail logging failed for {tag_spool}: {e}",
                exc_info=True
            )

        logger.info(f"✅ ReparacionService.pausar_reparacion: {tag_spool}")
        return {
            "success": True,
            "message": f"Reparación pausada para spool {tag_spool}",
            "tag_spool": tag_spool,
            "estado_detalle": ESTADO_DETALLE_REPARACION_PAUSADA
        }

    async def completar_reparacion(
        self,
        tag_spool: str,
        worker_id: int,
        worker_nombre: str
    ) -> dict:
        """
        Worker completes repair and returns spool to metrología queue.

        Flow:
        1. Fetch spool and validate ownership
        2. Instantiate state machine and trigger COMPLETAR transition
        3. Clear Ocupado_Por, Fecha_Ocupacion, set Estado_Detalle=PENDIENTE_METROLOGIA via state machine
        4. Log metadata event

        Args:
            tag_spool: Spool identifier
            worker_id: Worker ID (for ownership verification)
            worker_nombre: Worker name in format "INICIALES(ID)"

        Returns:
            dict with success message and estado_detalle

        Raises:
            SpoolNoEncontradoError: If spool doesn't exist
            OperacionNoIniciadaError: If spool not in EN_REPARACION state
            NoAutorizadoError: If spool occupied by different worker
        """
        logger.info(f"ReparacionService.completar_reparacion: {tag_spool} by {worker_nombre}")

        # Step 1: Fetch spool and validate ownership
        spool = self.sheets_repo.get_spool_by_tag(tag_spool)
        if not spool:
            raise SpoolNoEncontradoError(tag_spool)

        # Validate ownership
        if not spool.ocupado_por or f"({worker_id})" not in spool.ocupado_por:
            from backend.exceptions import NoAutorizadoError
            trabajador_esperado = spool.ocupado_por or "desconocido"
            raise NoAutorizadoError(
                tag_spool=tag_spool,
                trabajador_esperado=trabajador_esperado,
                trabajador_solicitante=worker_nombre,
                operacion="REPARACION"
            )

        # Step 2: Instantiate state machine hydrated to EN_REPARACION
        reparacion_machine = REPARACIONStateMachine(
            tag_spool=tag_spool,
            sheets_repo=self.sheets_repo,
            metadata_repo=self.metadata_repo,
            start_value="en_reparacion",
        )
        await reparacion_machine.activate_initial_state()

        # Trigger COMPLETAR transition
        await reparacion_machine.completar()
        logger.info(f"REPARACION COMPLETAR: {tag_spool} -> {reparacion_machine.current_state.id}")

        # Step 3: Log metadata event
        try:
            event = (
                MetadataEventBuilder()
                .for_completar(tag_spool, worker_id, worker_nombre, today_chile())
                .with_operacion("REPARACION")
                .with_metadata({
                    "state": reparacion_machine.get_state_id(),
                    "next_state": "PENDIENTE_METROLOGIA"
                })
                .build()
            )
            self.metadata_repo.log_event(**event)
        except Exception as e:
            logger.error(
                f"CRITICAL: Metadata audit trail logging failed for {tag_spool}: {e}",
                exc_info=True
            )

        logger.info(f"✅ ReparacionService.completar_reparacion: {tag_spool} -> PENDIENTE_METROLOGIA")
        return {
            "success": True,
            "message": f"Reparación completada para spool {tag_spool} - devuelto a metrología",
            "tag_spool": tag_spool,
            "estado_detalle": ESTADO_DETALLE_PENDIENTE_METROLOGIA
        }

    async def cancelar_reparacion(
        self,
        tag_spool: str,
        worker_id: int
    ) -> dict:
        """
        Worker cancels repair work and returns spool to RECHAZADO.

        Flow:
        1. Fetch spool and validate can CANCELAR (EN_REPARACION or REPARACION_PAUSADA)
        2. Instantiate state machine and trigger CANCELAR transition
        3. Clear Ocupado_Por, Fecha_Ocupacion, restore RECHAZADO estado via state machine callback
        4. Log metadata event

        Args:
            tag_spool: Spool identifier
            worker_id: Worker ID

        Returns:
            dict with success message and estado_detalle

        Raises:
            SpoolNoEncontradoError: If spool doesn't exist
            OperacionNoIniciadaError: If spool not in EN_REPARACION or REPARACION_PAUSADA state
        """
        logger.info(f"ReparacionService.cancelar_reparacion: {tag_spool}")

        # Step 1: Fetch spool and validate can CANCELAR
        spool = self.sheets_repo.get_spool_by_tag(tag_spool)
        if not spool:
            raise SpoolNoEncontradoError(tag_spool)

        worker_nombre = spool.ocupado_por or ""
        self.validation_service.validar_puede_cancelar_reparacion(spool, worker_nombre, worker_id)

        # Step 2: Instantiate state machine hydrated to current state
        if spool.estado_detalle and "REPARACION_PAUSADA" in spool.estado_detalle:
            start_state = "reparacion_pausada"
        else:
            start_state = "en_reparacion"

        reparacion_machine = REPARACIONStateMachine(
            tag_spool=tag_spool,
            sheets_repo=self.sheets_repo,
            metadata_repo=self.metadata_repo,
            start_value=start_state,
        )
        await reparacion_machine.activate_initial_state()

        # Trigger CANCELAR transition
        await reparacion_machine.cancelar()
        logger.info(f"REPARACION CANCELAR: {tag_spool} -> {reparacion_machine.current_state.id}")

        # Step 3: Log metadata event
        try:
            event = (
                MetadataEventBuilder()
                .for_cancelar(tag_spool, worker_id, spool.ocupado_por or "Unknown")
                .with_operacion("REPARACION")
                .with_metadata({
                    "state": reparacion_machine.get_state_id()
                })
                .build()
            )
            self.metadata_repo.log_event(**event)
        except Exception as e:
            logger.error(
                f"CRITICAL: Metadata audit trail logging failed for {tag_spool}: {e}",
                exc_info=True
            )

        logger.info(f"✅ ReparacionService.cancelar_reparacion: {tag_spool} -> RECHAZADO")
        return {
            "success": True,
            "message": f"Reparación cancelada para spool {tag_spool}",
            "tag_spool": tag_spool,
            "estado_detalle": ESTADO_DETALLE_RECHAZADO
        }
