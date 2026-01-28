"""
ReparacionService - Orchestrator for reparación workflow with bounded cycles.

Manages RECHAZADO spool repair with TOMAR/PAUSAR/COMPLETAR actions.
Enforces 3-cycle limit via CycleCounterService and BLOQUEADO escalation.

v3.0 Phase 6 feature:
- Multi-worker access (no role restriction)
- TOMAR/PAUSAR/COMPLETAR pattern (occupation-based workflow)
- Cycle tracking in Estado_Detalle
- Automatic return to PENDIENTE_METROLOGIA after completion
- BLOQUEADO enforcement after 3 consecutive rejections
"""

import logging
import uuid
import json
from datetime import date, datetime

from backend.utils.date_formatter import format_datetime_for_sheets, format_date_for_sheets, now_chile, today_chile
from backend.services.state_machines.reparacion_state_machine import REPARACIONStateMachine
from backend.services.validation_service import ValidationService
from backend.services.cycle_counter_service import CycleCounterService
from backend.repositories.sheets_repository import SheetsRepository
from backend.repositories.metadata_repository import MetadataRepository
from backend.services.redis_event_service import RedisEventService
from backend.exceptions import SpoolNoEncontradoError
from backend.models.enums import EventoTipo

logger = logging.getLogger(__name__)


class ReparacionService:
    """
    Service for reparación workflow with occupation management and cycle tracking.

    Orchestrates:
    - Cycle validation (max 3 consecutive rejections)
    - State machine transitions (tomar/pausar/completar/cancelar)
    - Ocupado_Por, Fecha_Ocupacion, Estado_Detalle column updates
    - Metadata event logging
    - SSE event publishing for dashboard
    """

    def __init__(
        self,
        validation_service: ValidationService,
        cycle_counter_service: CycleCounterService,
        sheets_repository: SheetsRepository,
        metadata_repository: MetadataRepository,
        redis_event_service: RedisEventService
    ):
        """
        Initialize reparación service with injected dependencies.

        Args:
            validation_service: Service for prerequisite validation
            cycle_counter_service: Service for cycle counting and BLOQUEADO enforcement
            sheets_repository: Repository for Sheets reads/writes
            metadata_repository: Repository for audit logging
            redis_event_service: Service for real-time event publishing
        """
        self.validation_service = validation_service
        self.cycle_counter = cycle_counter_service
        self.sheets_repo = sheets_repository
        self.metadata_repo = metadata_repository
        self.redis_event_service = redis_event_service
        logger.info("ReparacionService initialized with cycle tracking")

    async def tomar_reparacion(
        self,
        tag_spool: str,
        worker_id: int,
        worker_nombre: str
    ) -> dict:
        """
        Worker takes RECHAZADO spool for repair.

        Flow:
        1. Fetch spool and validate can TOMAR (RECHAZADO, not BLOQUEADO, not occupied)
        2. Extract cycle count from Estado_Detalle
        3. Check not BLOQUEADO (cycle < 3)
        4. Instantiate state machine and trigger TOMAR transition
        5. Update Ocupado_Por, Fecha_Ocupacion, Estado_Detalle via state machine callback
        6. Log metadata event
        7. Publish SSE event for dashboard

        Args:
            tag_spool: Spool identifier
            worker_id: Worker ID
            worker_nombre: Worker name in format "INICIALES(ID)"

        Returns:
            dict with success message and estado_detalle

        Raises:
            SpoolNoEncontradoError: If spool doesn't exist
            OperacionNoDisponibleError: If spool not in RECHAZADO state
            SpoolBloqueadoError: If spool blocked after 3 rejections (HTTP 403)
            SpoolOccupiedError: If spool currently occupied
        """
        logger.info(f"ReparacionService.tomar_reparacion: {tag_spool} by {worker_nombre}")

        # Step 1: Fetch spool and validate can TOMAR
        spool = self.sheets_repo.get_spool_by_tag(tag_spool)
        if not spool:
            raise SpoolNoEncontradoError(tag_spool)

        self.validation_service.validar_puede_tomar_reparacion(spool, worker_id)

        # Step 2: Extract cycle count from Estado_Detalle
        current_cycle = self.cycle_counter.extract_cycle_count(spool.estado_detalle or "")

        # Step 3: Check not BLOQUEADO (validation already checked, but double-check)
        if self.cycle_counter.should_block(current_cycle):
            logger.error(f"❌ Cannot TOMAR BLOQUEADO spool {tag_spool} (cycle={current_cycle})")
            from backend.exceptions import SpoolBloqueadoError
            raise SpoolBloqueadoError(tag_spool)

        # Step 4: Instantiate state machine and trigger TOMAR transition
        reparacion_machine = REPARACIONStateMachine(
            tag_spool=tag_spool,
            sheets_repo=self.sheets_repo,
            metadata_repo=self.metadata_repo,
            cycle_counter=self.cycle_counter
        )

        # Hydrate to current state (RECHAZADO or REPARACION_PAUSADA)
        if spool.estado_detalle and "REPARACION_PAUSADA" in spool.estado_detalle:
            reparacion_machine.current_state = reparacion_machine.reparacion_pausada
        else:
            reparacion_machine.current_state = reparacion_machine.rechazado

        # Trigger TOMAR transition
        reparacion_machine.tomar(worker_id=worker_id, worker_nombre=worker_nombre)
        logger.info(f"REPARACION TOMAR: {tag_spool} -> {reparacion_machine.current_state.id}")

        # Step 5: Log metadata event (Ocupado_Por/Fecha_Ocupacion/Estado_Detalle already updated by state machine)
        evento_tipo = EventoTipo.TOMAR_REPARACION

        metadata_event = {
            "id": str(uuid.uuid4()),
            "timestamp": format_datetime_for_sheets(now_chile()),
            "evento_tipo": evento_tipo,
            "tag_spool": tag_spool,
            "worker_id": worker_id,
            "worker_nombre": worker_nombre,
            "operacion": "REPARACION",
            "accion": "TOMAR",
            "fecha_operacion": format_date_for_sheets(today_chile()),
            "metadata_json": json.dumps({
                "cycle": current_cycle,
                "max_cycles": self.cycle_counter.MAX_CYCLES,
                "state": reparacion_machine.get_state_id()
            })
        }

        # Log to Metadata sheet (best-effort)
        try:
            self.metadata_repo.append_event(metadata_event)
        except Exception as e:
            logger.warning(f"Failed to log metadata for {tag_spool}: {e}")

        # Step 6: Build estado_detalle for SSE event
        estado_detalle = self.cycle_counter.build_reparacion_estado(
            "en_reparacion",
            current_cycle,
            worker_nombre
        )

        # Step 7: Publish SSE event for dashboard (best-effort)
        try:
            await self.redis_event_service.publish_spool_update(
                event_type="TOMAR_REPARACION",
                tag_spool=tag_spool,
                worker_nombre=worker_nombre,
                estado_detalle=estado_detalle,
                additional_data={"operacion": "REPARACION", "cycle": current_cycle}
            )
        except Exception as e:
            logger.warning(f"Failed to publish SSE event for {tag_spool}: {e}")

        logger.info(f"✅ ReparacionService.tomar_reparacion: {tag_spool}")
        return {
            "success": True,
            "message": f"Reparación tomada para spool {tag_spool}",
            "tag_spool": tag_spool,
            "worker_nombre": worker_nombre,
            "estado_detalle": estado_detalle,
            "cycle": current_cycle
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
        5. Publish SSE event for dashboard

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

        # Step 2: Instantiate state machine and trigger PAUSAR transition
        reparacion_machine = REPARACIONStateMachine(
            tag_spool=tag_spool,
            sheets_repo=self.sheets_repo,
            metadata_repo=self.metadata_repo,
            cycle_counter=self.cycle_counter
        )

        # Hydrate to EN_REPARACION state
        reparacion_machine.current_state = reparacion_machine.en_reparacion

        # Trigger PAUSAR transition
        reparacion_machine.pausar()
        logger.info(f"REPARACION PAUSAR: {tag_spool} -> {reparacion_machine.current_state.id}")

        # Step 3: Extract cycle count for metadata
        current_cycle = self.cycle_counter.extract_cycle_count(spool.estado_detalle or "")

        # Step 4: Log metadata event
        evento_tipo = EventoTipo.PAUSAR_REPARACION

        metadata_event = {
            "id": str(uuid.uuid4()),
            "timestamp": format_datetime_for_sheets(now_chile()),
            "evento_tipo": evento_tipo,
            "tag_spool": tag_spool,
            "worker_id": worker_id,
            "worker_nombre": spool.ocupado_por,  # Current worker name
            "operacion": "REPARACION",
            "accion": "PAUSAR",
            "fecha_operacion": format_date_for_sheets(today_chile()),
            "metadata_json": json.dumps({
                "cycle": current_cycle,
                "max_cycles": self.cycle_counter.MAX_CYCLES,
                "state": reparacion_machine.get_state_id()
            })
        }

        # Log to Metadata sheet (best-effort)
        try:
            self.metadata_repo.append_event(metadata_event)
        except Exception as e:
            logger.warning(f"Failed to log metadata for {tag_spool}: {e}")

        # Step 5: Build estado_detalle for SSE event
        estado_detalle = self.cycle_counter.build_reparacion_estado(
            "reparacion_pausada",
            current_cycle
        )

        # Step 6: Publish SSE event for dashboard (best-effort)
        try:
            await self.redis_event_service.publish_spool_update(
                event_type="PAUSAR_REPARACION",
                tag_spool=tag_spool,
                worker_nombre=None,  # No longer occupied
                estado_detalle=estado_detalle,
                additional_data={"operacion": "REPARACION", "cycle": current_cycle}
            )
        except Exception as e:
            logger.warning(f"Failed to publish SSE event for {tag_spool}: {e}")

        logger.info(f"✅ ReparacionService.pausar_reparacion: {tag_spool}")
        return {
            "success": True,
            "message": f"Reparación pausada para spool {tag_spool}",
            "tag_spool": tag_spool,
            "estado_detalle": estado_detalle
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
        5. Publish SSE event for dashboard

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
            raise NoAutorizadoError(
                f"Spool {tag_spool} no está ocupado por este trabajador"
            )

        # Step 2: Instantiate state machine and trigger COMPLETAR transition
        reparacion_machine = REPARACIONStateMachine(
            tag_spool=tag_spool,
            sheets_repo=self.sheets_repo,
            metadata_repo=self.metadata_repo,
            cycle_counter=self.cycle_counter
        )

        # Hydrate to EN_REPARACION state
        reparacion_machine.current_state = reparacion_machine.en_reparacion

        # Trigger COMPLETAR transition
        reparacion_machine.completar()
        logger.info(f"REPARACION COMPLETAR: {tag_spool} -> {reparacion_machine.current_state.id}")

        # Step 3: Extract cycle count for metadata
        current_cycle = self.cycle_counter.extract_cycle_count(spool.estado_detalle or "")

        # Step 4: Log metadata event
        evento_tipo = EventoTipo.COMPLETAR_REPARACION

        metadata_event = {
            "id": str(uuid.uuid4()),
            "timestamp": format_datetime_for_sheets(now_chile()),
            "evento_tipo": evento_tipo,
            "tag_spool": tag_spool,
            "worker_id": worker_id,
            "worker_nombre": worker_nombre,
            "operacion": "REPARACION",
            "accion": "COMPLETAR",
            "fecha_operacion": format_date_for_sheets(today_chile()),
            "metadata_json": json.dumps({
                "cycle": current_cycle,
                "max_cycles": self.cycle_counter.MAX_CYCLES,
                "state": reparacion_machine.get_state_id(),
                "next_state": "PENDIENTE_METROLOGIA"
            })
        }

        # Log to Metadata sheet (best-effort)
        try:
            self.metadata_repo.append_event(metadata_event)
        except Exception as e:
            logger.warning(f"Failed to log metadata for {tag_spool}: {e}")

        # Step 5: Build estado_detalle for SSE event
        estado_detalle = "PENDIENTE_METROLOGIA"

        # Step 6: Publish SSE event for dashboard (best-effort)
        try:
            await self.redis_event_service.publish_spool_update(
                event_type="COMPLETAR_REPARACION",
                tag_spool=tag_spool,
                worker_nombre=None,  # No longer occupied
                estado_detalle=estado_detalle,
                additional_data={"operacion": "REPARACION", "cycle": current_cycle}
            )
        except Exception as e:
            logger.warning(f"Failed to publish SSE event for {tag_spool}: {e}")

        logger.info(f"✅ ReparacionService.completar_reparacion: {tag_spool} -> PENDIENTE_METROLOGIA")
        return {
            "success": True,
            "message": f"Reparación completada para spool {tag_spool} - devuelto a metrología",
            "tag_spool": tag_spool,
            "estado_detalle": estado_detalle,
            "cycle": current_cycle
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
        5. Publish SSE event for dashboard

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

        self.validation_service.validar_puede_cancelar_reparacion(spool, worker_id)

        # Step 2: Instantiate state machine and trigger CANCELAR transition
        reparacion_machine = REPARACIONStateMachine(
            tag_spool=tag_spool,
            sheets_repo=self.sheets_repo,
            metadata_repo=self.metadata_repo,
            cycle_counter=self.cycle_counter
        )

        # Hydrate to current state (EN_REPARACION or REPARACION_PAUSADA)
        if spool.estado_detalle and "REPARACION_PAUSADA" in spool.estado_detalle:
            reparacion_machine.current_state = reparacion_machine.reparacion_pausada
        else:
            reparacion_machine.current_state = reparacion_machine.en_reparacion

        # Trigger CANCELAR transition
        reparacion_machine.cancelar()
        logger.info(f"REPARACION CANCELAR: {tag_spool} -> {reparacion_machine.current_state.id}")

        # Step 3: Extract cycle count for metadata
        current_cycle = self.cycle_counter.extract_cycle_count(spool.estado_detalle or "")

        # Step 4: Log metadata event
        evento_tipo = EventoTipo.CANCELAR_REPARACION

        metadata_event = {
            "id": str(uuid.uuid4()),
            "timestamp": format_datetime_for_sheets(now_chile()),
            "evento_tipo": evento_tipo,
            "tag_spool": tag_spool,
            "worker_id": worker_id,
            "worker_nombre": spool.ocupado_por or "Unknown",
            "operacion": "REPARACION",
            "accion": "CANCELAR",
            "fecha_operacion": format_date_for_sheets(today_chile()),
            "metadata_json": json.dumps({
                "cycle": current_cycle,
                "max_cycles": self.cycle_counter.MAX_CYCLES,
                "state": reparacion_machine.get_state_id()
            })
        }

        # Log to Metadata sheet (best-effort)
        try:
            self.metadata_repo.append_event(metadata_event)
        except Exception as e:
            logger.warning(f"Failed to log metadata for {tag_spool}: {e}")

        # Step 5: Build estado_detalle for SSE event
        estado_detalle = self.cycle_counter.build_rechazado_estado(current_cycle)

        # Step 6: Publish SSE event for dashboard (best-effort)
        try:
            await self.redis_event_service.publish_spool_update(
                event_type="CANCELAR_REPARACION",
                tag_spool=tag_spool,
                worker_nombre=None,  # No longer occupied
                estado_detalle=estado_detalle,
                additional_data={"operacion": "REPARACION", "cycle": current_cycle}
            )
        except Exception as e:
            logger.warning(f"Failed to publish SSE event for {tag_spool}: {e}")

        logger.info(f"✅ ReparacionService.cancelar_reparacion: {tag_spool} -> RECHAZADO")
        return {
            "success": True,
            "message": f"Reparación cancelada para spool {tag_spool}",
            "tag_spool": tag_spool,
            "estado_detalle": estado_detalle
        }
