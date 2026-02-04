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
from backend.exceptions import SpoolNoEncontradoError, InvalidStateTransitionError
from backend.config import config

logger = logging.getLogger(__name__)


class StateService:
    """
    Orchestrator for state machine operations.

    Coordinates:
    - ARM and SOLD state machines (per-operation)
    - OccupationService (single-user mode)
    - Estado_Detalle updates (display string via builder)
    - Hydration logic to sync state machines with Sheets reality

    Single-user mode: No SSE event publishing needed.
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
            occupation_service: Service for occupation operations
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

        try:
            # Step 2: Fetch current spool state
            spool = self.sheets_repo.get_spool_by_tag(tag_spool)
            if not spool:
                raise SpoolNoEncontradoError(tag_spool)

            # Step 3: Hydrate state machines
            arm_machine = await self._hydrate_arm_machine(spool)
            sold_machine = await self._hydrate_sold_machine(spool)

            # Step 4: Trigger state transition (iniciar or reanudar based on current state)
            if operacion == ActionType.ARM:
                current_arm_state = arm_machine.get_state_id()

                if current_arm_state == "pausado":
                    # Resume paused work
                    await arm_machine.reanudar(worker_nombre=request.worker_nombre)
                    logger.info(f"ARM state: pausado → en_progreso for {tag_spool} (resumed by {request.worker_nombre})")

                elif current_arm_state == "pendiente":
                    # Start new work
                    await arm_machine.iniciar(
                        worker_nombre=request.worker_nombre,
                        fecha_operacion=date.today()
                    )
                    logger.info(f"ARM state: pendiente → en_progreso for {tag_spool} (started by {request.worker_nombre})")

                elif current_arm_state == "en_progreso":
                    # Edge case: Machine hydrated to EN_PROGRESO because Ocupado_Por is set but
                    # Armador is not (from previous partial TOMAR failure OR normal TOMAR intermediate state).
                    # Solution: Manually write Armador since we can't call iniciar from EN_PROGRESO.
                    logger.warning(
                        f"ARM already en_progreso for {tag_spool} (Ocupado_Por set, Armador=None). "
                        f"Manually writing Armador to complete state."
                    )
                    # Manually write Armador to complete the TOMAR operation
                    from backend.services.conflict_service import ConflictService
                    conflict_service = self.occupation_service.conflict_service
                    await conflict_service.update_with_retry(
                        tag_spool=tag_spool,
                        updates={"Armador": request.worker_nombre},
                        operation="TOMAR_EDGE_CASE_FIX"
                    )
                    logger.info(f"✅ ARM edge case resolved: Armador written for {tag_spool}")

                elif current_arm_state == "completado":
                    # Cannot restart completed work
                    raise InvalidStateTransitionError(
                        f"Cannot TOMAR ARM - operation already completed",
                        tag_spool=tag_spool,
                        current_state=current_arm_state,
                        attempted_transition="iniciar"
                    )

                else:
                    # Unknown state - should never happen
                    logger.error(f"Unknown ARM state '{current_arm_state}' for {tag_spool}")
                    raise InvalidStateTransitionError(
                        f"Unknown ARM state '{current_arm_state}'",
                        tag_spool=tag_spool,
                        current_state=current_arm_state,
                        attempted_transition="iniciar"
                    )

            elif operacion == ActionType.SOLD:
                current_sold_state = sold_machine.get_state_id()

                if current_sold_state == "pausado":
                    # Resume paused work
                    await sold_machine.reanudar(worker_nombre=request.worker_nombre)
                    logger.info(f"SOLD state: pausado → en_progreso for {tag_spool} (resumed by {request.worker_nombre})")

                elif current_sold_state == "pendiente":
                    # Start new work (will validate ARM dependency)
                    await sold_machine.iniciar(
                        worker_nombre=request.worker_nombre,
                        fecha_operacion=date.today()
                    )
                    logger.info(f"SOLD state: pendiente → en_progreso for {tag_spool} (started by {request.worker_nombre})")

                elif current_sold_state == "en_progreso":
                    # Edge case: Machine hydrated to EN_PROGRESO because Ocupado_Por is set but
                    # Soldador is not (from previous partial TOMAR failure OR normal TOMAR intermediate state).
                    # Solution: Manually write Soldador since we can't call iniciar from EN_PROGRESO.
                    logger.warning(
                        f"SOLD already en_progreso for {tag_spool} (Ocupado_Por set, Soldador=None). "
                        f"Manually writing Soldador to complete state."
                    )
                    # Manually write Soldador to complete the TOMAR operation
                    from backend.services.conflict_service import ConflictService
                    conflict_service = self.occupation_service.conflict_service
                    await conflict_service.update_with_retry(
                        tag_spool=tag_spool,
                        updates={"Soldador": request.worker_nombre},
                        operation="TOMAR_EDGE_CASE_FIX"
                    )
                    logger.info(f"✅ SOLD edge case resolved: Soldador written for {tag_spool}")

                elif current_sold_state == "completado":
                    # Cannot restart completed work
                    raise InvalidStateTransitionError(
                        f"Cannot TOMAR SOLD - operation already completed",
                        tag_spool=tag_spool,
                        current_state=current_sold_state,
                        attempted_transition="iniciar"
                    )

                else:
                    # Unknown state - should never happen
                    logger.error(f"Unknown SOLD state '{current_sold_state}' for {tag_spool}")
                    raise InvalidStateTransitionError(
                        f"Unknown SOLD state '{current_sold_state}'",
                        tag_spool=tag_spool,
                        current_state=current_sold_state,
                        attempted_transition="iniciar"
                    )

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

        except Exception as e:
            # CRITICAL: State machine transition failed after OccupationService wrote Ocupado_Por
            # We must rollback: clear Ocupado_Por and release Redis lock
            logger.error(
                f"❌ CRITICAL: State machine transition failed for {tag_spool}, rolling back occupation: {e}",
                exc_info=True
            )

            try:
                # Rollback: Clear Ocupado_Por and Fecha_Ocupacion
                from backend.services.conflict_service import ConflictService
                from backend.repositories.metadata_repository import MetadataRepository

                # Use existing conflict_service from occupation_service
                conflict_service = self.occupation_service.conflict_service

                await conflict_service.update_with_retry(
                    tag_spool=tag_spool,
                    updates={
                        "Ocupado_Por": "",
                        "Fecha_Ocupacion": ""
                    },
                    operation="ROLLBACK_TOMAR"
                )

                # NOTE: We cannot safely release the Redis lock here because we don't have the lock_token
                # (it's inside OccupationService.tomar which already succeeded before this rollback).
                # The lock will auto-expire after 1 hour (TTL), which is acceptable for this edge case.
                # The critical part is clearing Ocupado_Por so the spool appears available in Sheets.
                logger.info(
                    f"✅ Rollback successful: cleared Ocupado_Por for {tag_spool}. "
                    f"Redis lock will auto-expire after TTL."
                )

            except Exception as rollback_error:
                logger.error(
                    f"❌ CRITICAL: Rollback failed for {tag_spool}: {rollback_error}. "
                    f"Spool may be in inconsistent state (has Ocupado_Por but no Armador/Soldador). "
                    f"Manual intervention may be required.",
                    exc_info=True
                )

            # Re-raise original exception to fail the TOMAR request
            raise

    async def pausar(self, request: PausarRequest) -> OccupationResponse:
        """
        PAUSAR operation with state machine coordination.

        Flow:
        1. Fetch spool and hydrate state machines
        2. Trigger pausar transition on state machine (en_progreso → pausado)
        3. Delegate to OccupationService (verify lock + release occupation)
        4. Update Estado_Detalle with pausado state

        Args:
            request: PAUSAR request with tag_spool, worker_id, worker_nombre, operacion

        Returns:
            OccupationResponse with success status and message

        Raises:
            SpoolNoEncontradoError: If spool doesn't exist
            InvalidStateTransitionError: If current state is not en_progreso
            NoAutorizadoError: If worker doesn't own the lock (from OccupationService)
            LockExpiredError: If lock no longer exists (from OccupationService)
        """
        tag_spool = request.tag_spool
        operacion = request.operacion

        logger.info(f"StateService.pausar: {tag_spool} {operacion} by {request.worker_nombre}")

        # Step 1: Fetch spool and hydrate BEFORE calling OccupationService
        spool = self.sheets_repo.get_spool_by_tag(tag_spool)
        if not spool:
            raise SpoolNoEncontradoError(tag_spool)

        arm_machine = await self._hydrate_arm_machine(spool)
        sold_machine = await self._hydrate_sold_machine(spool)

        # Step 2: Trigger pausar transition BEFORE clearing occupation
        # This ensures state machine is in "pausado" state when EstadoDetalleBuilder reads it
        if operacion == ActionType.ARM:
            current_arm_state = arm_machine.get_state_id()

            # Defensive validation - state machine will also validate, but this provides clearer error
            if current_arm_state != "en_progreso":
                raise InvalidStateTransitionError(
                    f"Cannot PAUSAR ARM from state '{current_arm_state}'. "
                    f"PAUSAR is only allowed from 'en_progreso' state.",
                    tag_spool=tag_spool,
                    current_state=current_arm_state,
                    attempted_transition="pausar"
                )

            await arm_machine.pausar()
            logger.info(f"ARM state: en_progreso → pausado for {tag_spool}")

        elif operacion == ActionType.SOLD:
            current_sold_state = sold_machine.get_state_id()

            if current_sold_state != "en_progreso":
                raise InvalidStateTransitionError(
                    f"Cannot PAUSAR SOLD from state '{current_sold_state}'. "
                    f"PAUSAR is only allowed from 'en_progreso' state.",
                    tag_spool=tag_spool,
                    current_state=current_sold_state,
                    attempted_transition="pausar"
                )

            await sold_machine.pausar()
            logger.info(f"SOLD state: en_progreso → pausado for {tag_spool}")

        # Step 3: Delegate to OccupationService (clears Ocupado_Por, releases lock)
        response = await self.occupation_service.pausar(request)

        # Step 4: Update Estado_Detalle with pausado state
        self._update_estado_detalle(
            tag_spool=tag_spool,
            ocupado_por=None,  # Occupation cleared
            arm_state=arm_machine.get_state_id(),  # Now "pausado" for ARM operation
            sold_state=sold_machine.get_state_id()  # Now "pausado" for SOLD operation
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
        arm_machine = await self._hydrate_arm_machine(spool)
        sold_machine = await self._hydrate_sold_machine(spool)

        # Trigger completar transition based on operation (await for async callbacks)
        if operacion == ActionType.ARM:
            await arm_machine.completar(
                worker_nombre=request.worker_nombre,
                fecha_operacion=request.fecha_operacion
            )
            logger.info(f"ARM state machine transitioned to {arm_machine.get_state_id()}")
        elif operacion == ActionType.SOLD:
            await sold_machine.completar(
                worker_nombre=request.worker_nombre,
                fecha_operacion=request.fecha_operacion
            )
            logger.info(f"SOLD state machine transitioned to {sold_machine.get_state_id()}")

        # Build new estado_detalle after state machine transition
        nuevo_estado_detalle = self.estado_builder.build(
            ocupado_por=None,  # Clear occupation after completion
            arm_state=arm_machine.get_state_id(),
            sold_state=sold_machine.get_state_id()
        )

        # Update Estado_Detalle - now available since operation completed
        self._update_estado_detalle(
            tag_spool=tag_spool,
            ocupado_por=None,  # Clear occupation after completion
            arm_state=arm_machine.get_state_id(),
            sold_state=sold_machine.get_state_id()
        )

        logger.info(f"✅ StateService.completar completed for {tag_spool}")
        return response

    async def _hydrate_arm_machine(self, spool) -> ARMStateMachine:
        """
        Create ARM state machine and set it to match Sheets state.

        Hydration logic:
        - If Fecha_Armado exists → COMPLETADO state
        - Else if Armador exists AND Ocupado_Por is null → PAUSADO state
        - Else if Armador exists AND Ocupado_Por exists → EN_PROGRESO state
        - Else → PENDIENTE state (initial)

        ⚠️ TECHNICAL DEBT: This creates coupling between occupation state
        (Ocupado_Por column managed by OccupationService) and state machine state
        (managed by StateService). Ideally, state machine state should be
        determinable from state-specific columns only.

        Future Refactoring (v4.0): Add Estado_ARM column (enum: PENDIENTE/EN_PROGRESO/
        PAUSADO/COMPLETADO) that is updated by state machine callbacks. This would
        eliminate the coupling and make hydration deterministic.

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

        # CRITICAL: Activate initial state FIRST (required by python-statemachine 2.5.0)
        # Then manually override current_state to hydrate from Sheets
        await machine.activate_initial_state()

        # Hydrate to match Sheets reality
        if spool.fecha_armado:
            # ARM is completed
            machine.current_state = machine.completado
            logger.debug(f"ARM hydrated to COMPLETADO for {spool.tag_spool}")
        elif spool.armador:
            # ARM initiated - check if paused or in progress
            if spool.ocupado_por is None or spool.ocupado_por == "":
                # Paused: Worker assigned but no current occupation
                machine.current_state = machine.pausado
                logger.debug(f"ARM hydrated to PAUSADO for {spool.tag_spool}")
            else:
                # In progress: Worker assigned and occupied
                machine.current_state = machine.en_progreso
                logger.debug(f"ARM hydrated to EN_PROGRESO for {spool.tag_spool}")
        elif spool.ocupado_por and spool.ocupado_por != "":
            # EDGE CASE: Ocupado_Por is set but Armador is not
            # This indicates a partially-failed TOMAR operation where:
            # 1. OccupationService.tomar() wrote Ocupado_Por successfully
            # 2. State machine callback failed to write Armador (exception/crash/timeout)
            # 3. Rollback failed or was incomplete, leaving spool in inconsistent state
            #
            # Hydrate to EN_PROGRESO to allow PAUSAR to recover from this state.
            # PAUSAR will clear Ocupado_Por and release the lock, returning spool to clean PENDIENTE.
            machine.current_state = machine.en_progreso
            logger.warning(
                f"⚠️ INCONSISTENT STATE DETECTED: {spool.tag_spool} has "
                f"Ocupado_Por='{spool.ocupado_por}' but Armador=None. "
                f"Hydrating to EN_PROGRESO to allow recovery via PAUSAR. "
                f"This indicates a previous TOMAR operation failed mid-execution."
            )
        else:
            # ARM is pending (initial state)
            logger.debug(f"ARM hydrated to PENDIENTE for {spool.tag_spool}")

        return machine

    async def _hydrate_sold_machine(self, spool) -> SOLDStateMachine:
        """
        Create SOLD state machine and set it to match Sheets state.

        Hydration logic (same pattern as ARM):
        - If Fecha_Soldadura exists → COMPLETADO state
        - Else if Soldador exists AND Ocupado_Por is null → PAUSADO state
        - Else if Soldador exists AND Ocupado_Por exists → EN_PROGRESO state
        - Else → PENDIENTE state (initial)

        ⚠️ TECHNICAL DEBT: Same coupling issue as ARM hydration. See _hydrate_arm_machine()
        docstring for details and future refactoring plan.

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

        # CRITICAL: Activate initial state FIRST (required by python-statemachine 2.5.0)
        # Then manually override current_state to hydrate from Sheets
        await machine.activate_initial_state()

        # Hydrate to match Sheets reality
        if spool.fecha_soldadura:
            # SOLD is completed
            machine.current_state = machine.completado
            logger.debug(f"SOLD hydrated to COMPLETADO for {spool.tag_spool}")
        elif spool.soldador:
            # SOLD initiated - check if paused or in progress
            if spool.ocupado_por is None or spool.ocupado_por == "":
                # Paused: Worker assigned but no current occupation
                machine.current_state = machine.pausado
                logger.debug(f"SOLD hydrated to PAUSADO for {spool.tag_spool}")
            else:
                # In progress: Worker assigned and occupied
                machine.current_state = machine.en_progreso
                logger.debug(f"SOLD hydrated to EN_PROGRESO for {spool.tag_spool}")
        elif spool.ocupado_por and spool.ocupado_por != "":
            # EDGE CASE: Ocupado_Por is set but Soldador is not
            # This indicates a partially-failed TOMAR operation where:
            # 1. OccupationService.tomar() wrote Ocupado_Por successfully
            # 2. State machine callback failed to write Soldador (exception/crash/timeout)
            # 3. Rollback failed or was incomplete, leaving spool in inconsistent state
            #
            # Hydrate to EN_PROGRESO to allow PAUSAR to recover from this state.
            # PAUSAR will clear Ocupado_Por and release the lock, returning spool to clean PENDIENTE.
            machine.current_state = machine.en_progreso
            logger.warning(
                f"⚠️ INCONSISTENT STATE DETECTED: {spool.tag_spool} has "
                f"Ocupado_Por='{spool.ocupado_por}' but Soldador=None. "
                f"Hydrating to EN_PROGRESO to allow recovery via PAUSAR. "
                f"This indicates a previous TOMAR operation failed mid-execution."
            )
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

    async def trigger_metrologia_transition(self, tag_spool: str) -> Optional[str]:
        """
        Trigger automatic transition to metrología queue when all work is complete.

        Flow:
        1. Fetch current spool state from Sheets
        2. Load metrología state machine
        3. Check if already in metrología queue (PENDIENTE_METROLOGIA)
        4. Trigger transition to PENDIENTE_METROLOGIA state
        5. Update Estado_Detalle to "En Cola Metrología"
        6. Return new state or None if transition rejected

        Args:
            tag_spool: Spool identifier

        Returns:
            Optional[str]: New state after transition, or None if rejected

        Raises:
            SpoolNoEncontradoError: If spool doesn't exist
        """
        logger.info(f"Triggering metrología auto-transition for {tag_spool}")

        try:
            # Step 1: Fetch current spool state
            spool = self.sheets_repo.get_spool_by_tag(tag_spool)
            if not spool:
                raise SpoolNoEncontradoError(tag_spool)

            # Step 2: Load metrología state machine
            from backend.domain.state_machines.metrologia_machine import MetrologiaStateMachine

            metrologia_machine = MetrologiaStateMachine(
                tag_spool=tag_spool,
                sheets_repo=self.sheets_repo,
                metadata_repo=self.metadata_repo
            )

            # Activate initial state
            await metrologia_machine.activate_initial_state()

            # Step 3: Check current state
            current_state = metrologia_machine.get_state_id()

            if current_state != "pendiente":
                logger.warning(
                    f"Metrología already in state '{current_state}' for {tag_spool}, "
                    f"skipping auto-transition"
                )
                return None

            # Step 4: Update Estado_Detalle to indicate metrología queue
            # Note: The actual state transition happens when inspector calls aprobar/rechazar
            # We just update the display to show it's ready for inspection
            estado_detalle = "En Cola Metrología"

            row_num = self.sheets_repo.find_row_by_column_value(
                sheet_name=config.HOJA_OPERACIONES_NOMBRE,
                column_letter="G",  # TAG_SPOOL column
                value=tag_spool
            )

            if row_num:
                self.sheets_repo.update_cell_by_column_name(
                    sheet_name=config.HOJA_OPERACIONES_NOMBRE,
                    row=row_num,
                    column_name="Estado_Detalle",
                    value=estado_detalle
                )
                logger.info(f"✅ Estado_Detalle updated to '{estado_detalle}' for {tag_spool}")
            else:
                logger.warning(f"Could not find row for {tag_spool} to update Estado_Detalle")

            logger.info(f"✅ Metrología auto-transition complete for {tag_spool}")
            return current_state

        except SpoolNoEncontradoError:
            raise
        except Exception as e:
            logger.error(
                f"Failed to trigger metrología transition for {tag_spool}: {e}",
                exc_info=True
            )
            # Don't block FINALIZAR operation on metrología trigger failure
            return None
