"""
StateService - Orchestrator for state machine operations.

Coordinates ARM and SOLD state machines with OccupationService, implementing
hydration logic to sync with current Sheets state.

v3.0 state management:
- Separate state machines per operation (ARM/SOLD)
- Hydration from Sheets columns (Armador/Soldador/Fecha_*)
- Estado_Detalle updates via EstadoDetalleBuilder
- Integration with Phase 2 OccupationService (Redis locks)
"""

import logging
from typing import Optional
from datetime import date

from backend.services.state_machines.arm_state_machine import ARMStateMachine
from backend.services.state_machines.sold_state_machine import SOLDStateMachine
from backend.services.occupation_service import OccupationService
from backend.services.estado_detalle_builder import EstadoDetalleBuilder
from backend.repositories.sheets_repository import SheetsRepository
from backend.repositories.metadata_repository import MetadataRepository
from backend.models.occupation import TomarRequest, PausarRequest, CompletarRequest, OccupationResponse
from backend.models.enums import ActionType
from backend.exceptions import SpoolNoEncontradoError
from backend.config import config

logger = logging.getLogger(__name__)


class StateService:
    """
    Orchestrator for state machine operations.

    Coordinates:
    - ARM and SOLD state machines (per-operation)
    - OccupationService (Redis locks, Phase 2)
    - Estado_Detalle updates (display string via builder)
    - Hydration logic to sync state machines with Sheets reality
    """

    def __init__(
        self,
        occupation_service: OccupationService,
        sheets_repository: SheetsRepository,
        metadata_repository: MetadataRepository
    ):
        """
        Initialize state service with injected dependencies.

        Args:
            occupation_service: Service for Redis locks and occupation operations
            sheets_repository: Repository for Sheets reads/writes
            metadata_repository: Repository for audit logging
        """
        self.occupation_service = occupation_service
        self.sheets_repo = sheets_repository
        self.metadata_repo = metadata_repository
        self.estado_builder = EstadoDetalleBuilder()
        logger.info("StateService initialized with state machine orchestration")

    async def tomar(self, request: TomarRequest) -> OccupationResponse:
        """
        TOMAR operation with state machine coordination.

        Flow:
        1. Delegate to OccupationService (Redis lock + Ocupado_Por update)
        2. Fetch current spool state from Sheets
        3. Hydrate state machines from current Sheets state
        4. Trigger state transition (iniciar) based on operation
        5. Update Estado_Detalle with new combined state

        Args:
            request: TOMAR request with tag_spool, worker_id, worker_nombre, operacion

        Returns:
            OccupationResponse with success status and message

        Raises:
            SpoolNoEncontradoError: If spool doesn't exist
            SpoolOccupiedError: If spool already locked
            DependenciasNoSatisfechasError: If operation dependencies not met
        """
        tag_spool = request.tag_spool
        operacion = request.operacion

        logger.info(
            f"StateService.tomar: {tag_spool} by {request.worker_nombre} for {operacion.value}"
        )

        # Step 1: Delegate to OccupationService (Redis lock + Ocupado_Por)
        response = await self.occupation_service.tomar(request)

        # Step 2: Fetch current spool state
        spool = self.sheets_repo.get_spool_by_tag(tag_spool)
        if not spool:
            raise SpoolNoEncontradoError(tag_spool)

        # Step 3: Hydrate state machines
        arm_machine = self._hydrate_arm_machine(spool)
        sold_machine = self._hydrate_sold_machine(spool)

        # Step 4: Trigger state transition
        if operacion == ActionType.ARM:
            # Trigger ARM iniciar transition
            arm_machine.iniciar(
                worker_nombre=request.worker_nombre,
                fecha_operacion=date.today()
            )
            logger.info(f"ARM state machine transitioned to {arm_machine.get_state_id()}")
        elif operacion == ActionType.SOLD:
            # Trigger SOLD iniciar transition (will validate ARM dependency)
            sold_machine.iniciar(
                worker_nombre=request.worker_nombre,
                fecha_operacion=date.today()
            )
            logger.info(f"SOLD state machine transitioned to {sold_machine.get_state_id()}")

        # Step 5: Update Estado_Detalle
        self._update_estado_detalle(
            tag_spool=tag_spool,
            ocupado_por=request.worker_nombre,
            arm_state=arm_machine.get_state_id(),
            sold_state=sold_machine.get_state_id(),
            operacion_actual=operacion.value
        )

        logger.info(f"✅ StateService.tomar completed for {tag_spool}")
        return response

    async def pausar(self, request: PausarRequest) -> OccupationResponse:
        """
        PAUSAR operation with state machine coordination.

        Flow:
        1. Delegate to OccupationService (verify lock + release)
        2. Update Estado_Detalle to show available state
        3. Log PAUSAR event

        Args:
            request: PAUSAR request with tag_spool, worker_id, worker_nombre

        Returns:
            OccupationResponse with success status and message

        Raises:
            NoAutorizadoError: If worker doesn't own the lock
            LockExpiredError: If lock no longer exists
        """
        tag_spool = request.tag_spool

        logger.info(f"StateService.pausar: {tag_spool} by {request.worker_nombre}")

        # Delegate to OccupationService
        response = await self.occupation_service.pausar(request)

        # Fetch current spool state
        spool = self.sheets_repo.get_spool_by_tag(tag_spool)
        if spool:
            # Hydrate state machines to get current states
            arm_machine = self._hydrate_arm_machine(spool)
            sold_machine = self._hydrate_sold_machine(spool)

            # Update Estado_Detalle with "Disponible - ARM X, SOLD Y" format
            self._update_estado_detalle(
                tag_spool=tag_spool,
                ocupado_por=None,  # Clear occupation
                arm_state=arm_machine.get_state_id(),
                sold_state=sold_machine.get_state_id()
            )

        logger.info(f"✅ StateService.pausar completed for {tag_spool}")
        return response

    async def completar(self, request: CompletarRequest) -> OccupationResponse:
        """
        COMPLETAR operation with state machine coordination.

        Flow:
        1. Delegate to OccupationService (verify lock + update fecha + release)
        2. Hydrate state machines
        3. Trigger completar transition
        4. Update Estado_Detalle

        Args:
            request: COMPLETAR request with tag_spool, worker_id, worker_nombre, fecha_operacion

        Returns:
            OccupationResponse with success status and message

        Raises:
            NoAutorizadoError: If worker doesn't own the lock
            LockExpiredError: If lock no longer exists
        """
        tag_spool = request.tag_spool
        operacion = request.operacion

        logger.info(f"StateService.completar: {tag_spool} by {request.worker_nombre}")

        # Delegate to OccupationService
        response = await self.occupation_service.completar(request)

        # Fetch current spool state after OccupationService writes
        spool = self.sheets_repo.get_spool_by_tag(tag_spool)
        if not spool:
            raise SpoolNoEncontradoError(tag_spool)

        # Hydrate state machines
        arm_machine = self._hydrate_arm_machine(spool)
        sold_machine = self._hydrate_sold_machine(spool)

        # Trigger completar transition based on operation
        if operacion == ActionType.ARM:
            arm_machine.completar(
                worker_nombre=request.worker_nombre,
                fecha_operacion=request.fecha_operacion
            )
            logger.info(f"ARM state machine transitioned to {arm_machine.get_state_id()}")
        elif operacion == ActionType.SOLD:
            sold_machine.completar(
                worker_nombre=request.worker_nombre,
                fecha_operacion=request.fecha_operacion
            )
            logger.info(f"SOLD state machine transitioned to {sold_machine.get_state_id()}")

        # Update Estado_Detalle - now available since operation completed
        self._update_estado_detalle(
            tag_spool=tag_spool,
            ocupado_por=None,  # Clear occupation after completion
            arm_state=arm_machine.get_state_id(),
            sold_state=sold_machine.get_state_id()
        )

        logger.info(f"✅ StateService.completar completed for {tag_spool}")
        return response

    def _hydrate_arm_machine(self, spool) -> ARMStateMachine:
        """
        Create ARM state machine and set it to match Sheets state.

        Hydration logic:
        - If Fecha_Armado exists → COMPLETADO state
        - Else if Armador exists → EN_PROGRESO state
        - Else → PENDIENTE state (initial)

        Args:
            spool: Spool model with current state

        Returns:
            ARMStateMachine instance hydrated to current state
        """
        machine = ARMStateMachine(
            tag_spool=spool.tag_spool,
            sheets_repo=self.sheets_repo,
            metadata_repo=self.metadata_repo
        )

        # Hydrate to match Sheets reality
        if spool.fecha_armado:
            # ARM is completed
            machine.current_state = machine.completado
            logger.debug(f"ARM hydrated to COMPLETADO for {spool.tag_spool}")
        elif spool.armador:
            # ARM is in progress
            machine.current_state = machine.en_progreso
            logger.debug(f"ARM hydrated to EN_PROGRESO for {spool.tag_spool}")
        else:
            # ARM is pending (initial state)
            logger.debug(f"ARM hydrated to PENDIENTE for {spool.tag_spool}")

        return machine

    def _hydrate_sold_machine(self, spool) -> SOLDStateMachine:
        """
        Create SOLD state machine and set it to match Sheets state.

        Hydration logic (same pattern as ARM):
        - If Fecha_Soldadura exists → COMPLETADO state
        - Else if Soldador exists → EN_PROGRESO state
        - Else → PENDIENTE state (initial)

        Args:
            spool: Spool model with current state

        Returns:
            SOLDStateMachine instance hydrated to current state
        """
        machine = SOLDStateMachine(
            tag_spool=spool.tag_spool,
            sheets_repo=self.sheets_repo,
            metadata_repo=self.metadata_repo
        )

        # Hydrate to match Sheets reality
        if spool.fecha_soldadura:
            # SOLD is completed
            machine.current_state = machine.completado
            logger.debug(f"SOLD hydrated to COMPLETADO for {spool.tag_spool}")
        elif spool.soldador:
            # SOLD is in progress
            machine.current_state = machine.en_progreso
            logger.debug(f"SOLD hydrated to EN_PROGRESO for {spool.tag_spool}")
        else:
            # SOLD is pending (initial state)
            logger.debug(f"SOLD hydrated to PENDIENTE for {spool.tag_spool}")

        return machine

    def _update_estado_detalle(
        self,
        tag_spool: str,
        ocupado_por: Optional[str],
        arm_state: str,
        sold_state: str,
        operacion_actual: Optional[str] = None
    ):
        """
        Update Estado_Detalle column with formatted display string.

        Args:
            tag_spool: Spool identifier
            ocupado_por: Worker name occupying spool (None if available)
            arm_state: ARM state ID (pendiente/en_progreso/completado)
            sold_state: SOLD state ID (pendiente/en_progreso/completado)
            operacion_actual: Current operation being worked (ARM/SOLD)
        """
        # Build display string
        estado_detalle = self.estado_builder.build(
            ocupado_por=ocupado_por,
            arm_state=arm_state,
            sold_state=sold_state,
            operacion_actual=operacion_actual
        )

        # Find row for this spool
        row_num = self.sheets_repo.find_row_by_column_value(
            sheet_name=config.HOJA_OPERACIONES_NOMBRE,
            column_letter="G",  # TAG_SPOOL column
            value=tag_spool
        )

        if row_num:
            # Update Estado_Detalle column
            self.sheets_repo.update_cell_by_column_name(
                sheet_name=config.HOJA_OPERACIONES_NOMBRE,
                row=row_num,
                column_name="Estado_Detalle",
                value=estado_detalle
            )
            logger.debug(f"Estado_Detalle updated for {tag_spool}: {estado_detalle}")
        else:
            logger.warning(f"Could not find row for {tag_spool} to update Estado_Detalle")
