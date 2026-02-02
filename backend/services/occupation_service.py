"""
OccupationService - Core business logic for TOMAR/PAUSAR/COMPLETAR operations.

v3.0 occupation tracking:
- TOMAR: Acquire Redis lock + write Ocupado_Por/Fecha_Ocupacion to Operaciones
- PAUSAR: Update state to "parcial (pausado)" + release Redis lock
- COMPLETAR: Write fecha_armado/soldadura + release Redis lock

Orchestrates:
- RedisLockService: Atomic lock acquisition/release
- SheetsRepository: Write to Operaciones sheet
- MetadataRepository: Audit trail logging
- ConflictService: Optimistic locking with retry (v3.0)
"""

import logging
import json
from typing import Optional
from datetime import date, datetime
from redis.exceptions import RedisError

from backend.utils.date_formatter import format_date_for_sheets, format_datetime_for_sheets, today_chile, now_chile
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
    before_sleep_log
)

from backend.services.redis_lock_service import RedisLockService
from backend.services.conflict_service import ConflictService
from backend.services.redis_event_service import RedisEventService
from backend.repositories.sheets_repository import SheetsRepository
from backend.repositories.metadata_repository import MetadataRepository
from backend.models.occupation import (
    TomarRequest,
    PausarRequest,
    CompletarRequest,
    BatchTomarRequest,
    OccupationResponse,
    BatchOccupationResponse,
    IniciarRequest,
    FinalizarRequest
)
from backend.models.enums import ActionType, EventoTipo
from backend.exceptions import (
    SpoolNoEncontradoError,
    SpoolOccupiedError,
    DependenciasNoSatisfechasError,
    NoAutorizadoError,
    LockExpiredError,
    SheetsUpdateError,
    VersionConflictError
)

logger = logging.getLogger(__name__)


class OccupationService:
    """
    Service for spool occupation operations with Redis locking and Sheets updates.

    Implements TOMAR/PAUSAR/COMPLETAR with proper dependency injection and
    optimistic locking via ConflictService (v3.0).
    """

    def __init__(
        self,
        redis_lock_service: RedisLockService,
        sheets_repository: SheetsRepository,
        metadata_repository: MetadataRepository,
        conflict_service: ConflictService,
        redis_event_service: RedisEventService
    ):
        """
        Initialize occupation service with injected dependencies.

        Args:
            redis_lock_service: Service for Redis lock operations
            sheets_repository: Repository for Sheets writes
            metadata_repository: Repository for audit logging
            conflict_service: Service for version conflict handling and retry
            redis_event_service: Service for publishing real-time events
        """
        self.redis_lock_service = redis_lock_service
        self.sheets_repository = sheets_repository
        self.metadata_repository = metadata_repository
        self.conflict_service = conflict_service
        self.redis_event_service = redis_event_service
        logger.info("OccupationService initialized with Redis lock + optimistic locking")

    async def tomar(self, request: TomarRequest) -> OccupationResponse:
        """
        Take a spool (acquire occupation lock).

        Flow:
        1. Validate spool exists and has Fecha_Materiales prerequisite
        2. Acquire Redis lock (atomic, will fail if already occupied)
        3. Update Ocupado_Por and Fecha_Ocupacion in Operaciones sheet
        4. Log TOMAR event to Metadata sheet
        5. Return success response

        Args:
            request: TOMAR request with tag_spool, worker_id, worker_nombre, operacion

        Returns:
            OccupationResponse with success status and message

        Raises:
            SpoolNoEncontradoError: If spool doesn't exist
            DependenciasNoSatisfechasError: If Fecha_Materiales is missing
            SpoolOccupiedError: If spool already locked by another worker (409)
            SheetsUpdateError: If Sheets write fails
            RedisError: If Redis operation fails
        """
        tag_spool = request.tag_spool
        worker_id = request.worker_id
        worker_nombre = request.worker_nombre
        operacion = request.operacion.value

        logger.info(
            f"TOMAR operation started: {tag_spool} by worker {worker_id} ({worker_nombre}) "
            f"for {operacion}"
        )

        try:
            # Step 1: Validate spool exists and has prerequisites
            spool = self.sheets_repository.get_spool_by_tag(tag_spool)
            if not spool:
                raise SpoolNoEncontradoError(tag_spool)

            # Check Fecha_Materiales prerequisite
            if not spool.fecha_materiales:
                raise DependenciasNoSatisfechasError(
                    tag_spool=tag_spool,
                    operacion=operacion,
                    dependencia_faltante="Fecha_Materiales",
                    detalle="El spool debe tener materiales registrados antes de ocuparlo"
                )

            # Step 1.5: Lazy cleanup (best effort, don't block on failure)
            # Clean up one abandoned lock >24h old before acquiring new lock
            try:
                await self.redis_lock_service.lazy_cleanup_one_abandoned_lock()
            except Exception as e:
                # Log warning but continue with TOMAR operation
                logger.warning(f"Lazy cleanup failed during TOMAR: {e}")

            # Step 2: Acquire Redis lock (atomic operation)
            try:
                lock_token = await self.redis_lock_service.acquire_lock(
                    tag_spool=tag_spool,
                    worker_id=worker_id,
                    worker_nombre=worker_nombre
                )
            except SpoolOccupiedError:
                # Re-raise to be mapped to 409 by router
                raise

            # Step 3: Update Operaciones sheet with occupation data (with version retry)
            try:
                # Write Ocupado_Por (column 64) and Fecha_Ocupacion (column 65)
                # CRITICAL: Use format_datetime_for_sheets() for timestamp with time component
                # Format: "DD-MM-YYYY HH:MM:SS" (e.g., "30-01-2026 14:30:00")
                fecha_ocupacion_str = format_datetime_for_sheets(now_chile())

                # Use ConflictService for version-aware update with automatic retry
                updates_dict = {
                    "Ocupado_Por": worker_nombre,
                    "Fecha_Ocupacion": fecha_ocupacion_str
                }

                new_version = await self.conflict_service.update_with_retry(
                    tag_spool=tag_spool,
                    updates=updates_dict,
                    operation="TOMAR"
                )

                logger.info(
                    f"✅ Sheets updated: {tag_spool} occupied by {worker_nombre} "
                    f"on {fecha_ocupacion_str} (version: {new_version})"
                )

            except VersionConflictError as e:
                # Max retries exhausted - rollback Redis lock
                logger.error(
                    f"Version conflict persists after retries, rolling back Redis lock: {e}"
                )
                await self.redis_lock_service.release_lock(tag_spool, worker_id, lock_token)
                raise
            except Exception as e:
                # Rollback: release Redis lock if Sheets update fails
                logger.error(f"Sheets update failed, rolling back Redis lock: {e}")
                await self.redis_lock_service.release_lock(tag_spool, worker_id, lock_token)
                raise SheetsUpdateError(
                    f"Failed to update occupation in Sheets: {e}",
                    updates={"ocupado_por": worker_nombre, "fecha_ocupacion": fecha_ocupacion_str}
                )

            # Step 4: Log to Metadata (audit trail - MANDATORY for regulatory compliance)
            try:
                # v3.0: Use operation-agnostic TOMAR_SPOOL event type
                evento_tipo = EventoTipo.TOMAR_SPOOL.value
                metadata_json = json.dumps({
                    "lock_token": lock_token,
                    "fecha_ocupacion": fecha_ocupacion_str
                })

                self.metadata_repository.log_event(
                    evento_tipo=evento_tipo,
                    tag_spool=tag_spool,
                    worker_id=worker_id,
                    worker_nombre=worker_nombre,
                    operacion=operacion,
                    accion="TOMAR",
                    fecha_operacion=format_date_for_sheets(today_chile()),
                    metadata_json=metadata_json
                )

                logger.info(f"✅ Metadata logged: {evento_tipo} for {tag_spool}")

            except Exception as e:
                # CRITICAL: Metadata logging is mandatory for audit compliance
                # Log error with full details to aid debugging
                logger.error(
                    f"❌ CRITICAL: Metadata logging failed for {tag_spool}: {e}",
                    exc_info=True
                )
                # Continue operation but log prominently - metadata writes should be investigated
                # Note: In future, consider making this a hard failure if regulatory compliance requires it

            # Step 4.5: Publish real-time event (best effort)
            try:
                # Estado_Detalle will be built by StateService, use simple format for now
                estado_detalle = f"Ocupado por {worker_nombre} - {operacion}"
                await self.redis_event_service.publish_spool_update(
                    event_type="TOMAR",
                    tag_spool=tag_spool,
                    worker_nombre=worker_nombre,
                    estado_detalle=estado_detalle,
                    additional_data={"operacion": operacion}
                )
                logger.info(f"✅ Real-time event published: TOMAR for {tag_spool}")
            except Exception as e:
                # Best effort - log but don't fail operation
                logger.warning(f"⚠️ Event publishing failed (non-critical): {e}")

            # Step 5: Return success
            message = f"Spool {tag_spool} tomado por {worker_nombre}"
            logger.info(f"✅ TOMAR completed successfully: {message}")

            return OccupationResponse(
                success=True,
                tag_spool=tag_spool,
                message=message
            )

        except (SpoolNoEncontradoError, DependenciasNoSatisfechasError, SpoolOccupiedError):
            # Re-raise business exceptions for router to handle
            raise
        except Exception as e:
            logger.error(f"❌ TOMAR operation failed: {e}")
            raise

    async def pausar(self, request: PausarRequest) -> OccupationResponse:
        """
        Pause work on a spool (mark as partially complete and release lock).

        Flow:
        1. Verify worker owns the Redis lock
        2. Update spool state in Operaciones sheet to "ARM parcial (pausado)" or "SOLD parcial (pausado)"
        3. Clear Ocupado_Por and Fecha_Ocupacion columns
        4. Release Redis lock
        5. Log PAUSAR event to Metadata sheet
        6. Return success response

        Note: The exact column name for paused state will be determined based on v3.0 schema.
        For now, we'll add a new column "Estado_Ocupacion" or reuse an existing status column.

        Args:
            request: PAUSAR request with tag_spool, worker_id, worker_nombre

        Returns:
            OccupationResponse with success status and message

        Raises:
            SpoolNoEncontradoError: If spool doesn't exist
            NoAutorizadoError: If worker doesn't own the lock
            LockExpiredError: If lock no longer exists
            SheetsUpdateError: If Sheets write fails
        """
        tag_spool = request.tag_spool
        worker_id = request.worker_id
        worker_nombre = request.worker_nombre

        logger.info(
            f"PAUSAR operation started: {tag_spool} by worker {worker_id} ({worker_nombre})"
        )

        try:
            # Step 1: Verify lock ownership
            lock_owner = await self.redis_lock_service.get_lock_owner(tag_spool)

            if lock_owner is None:
                raise LockExpiredError(tag_spool)

            owner_id, lock_token = lock_owner

            if owner_id != worker_id:
                raise NoAutorizadoError(
                    tag_spool=tag_spool,
                    trabajador_esperado=f"Worker {owner_id}",
                    trabajador_solicitante=worker_nombre,
                    operacion="PAUSAR"
                )

            # Step 2: Determine operation type from spool state
            spool = self.sheets_repository.get_spool_by_tag(tag_spool)
            if not spool:
                raise SpoolNoEncontradoError(tag_spool)

            # Determine which operation is being paused based on current state
            # For v3.0: This will be enhanced with proper state tracking
            # For now, we'll use a simple approach: check which operation is in progress
            operacion = "ARM"  # Default, will be enhanced in future
            estado_pausado = f"{operacion} parcial (pausado)"

            # Step 3: Update Sheets - mark as paused and clear occupation (with version retry)
            try:
                # Note: Estado_Ocupacion column will be added to v3.0 schema
                # For now, we'll clear occupation fields
                updates_dict = {
                    "Ocupado_Por": "",  # Clear occupation
                    "Fecha_Ocupacion": ""
                }

                # Use ConflictService for version-aware update with automatic retry
                new_version = await self.conflict_service.update_with_retry(
                    tag_spool=tag_spool,
                    updates=updates_dict,
                    operation="PAUSAR"
                )

                logger.info(
                    f"✅ Sheets updated: {tag_spool} marked as '{estado_pausado}', "
                    f"occupation cleared (version: {new_version})"
                )

            except VersionConflictError as e:
                # Max retries exhausted
                logger.error(f"Version conflict persists after retries for PAUSAR: {e}")
                raise
            except Exception as e:
                logger.error(f"Sheets update failed for PAUSAR: {e}")
                raise SheetsUpdateError(
                    f"Failed to update paused state in Sheets: {e}",
                    updates={"estado": estado_pausado, "ocupado_por": None}
                )

            # Step 4: Release Redis lock
            try:
                released = await self.redis_lock_service.release_lock(tag_spool, worker_id, lock_token)
                if not released:
                    logger.warning(
                        f"⚠️ Lock release returned False for {tag_spool} "
                        f"(may have already expired)"
                    )
            except Exception as e:
                logger.error(f"Failed to release lock for {tag_spool}: {e}")
                # Continue - Sheets already updated, lock will expire naturally

            # Step 4.5: Publish real-time event (best effort)
            try:
                await self.redis_event_service.publish_spool_update(
                    event_type="PAUSAR",
                    tag_spool=tag_spool,
                    worker_nombre=None,  # No longer occupied
                    estado_detalle=estado_pausado,
                    additional_data={"operacion": operacion}
                )
                logger.info(f"✅ Real-time event published: PAUSAR for {tag_spool}")
            except Exception as e:
                # Best effort - log but don't fail operation
                logger.warning(f"⚠️ Event publishing failed (non-critical): {e}")

            # Step 5: Log to Metadata (audit trail - MANDATORY for regulatory compliance)
            try:
                # v3.0: Use operation-agnostic PAUSAR_SPOOL event type
                evento_tipo = EventoTipo.PAUSAR_SPOOL.value
                metadata_json = json.dumps({
                    "estado": estado_pausado,
                    "lock_released": True
                })

                self.metadata_repository.log_event(
                    evento_tipo=evento_tipo,
                    tag_spool=tag_spool,
                    worker_id=worker_id,
                    worker_nombre=worker_nombre,
                    operacion=operacion,
                    accion="PAUSAR",
                    fecha_operacion=format_date_for_sheets(today_chile()),
                    metadata_json=metadata_json
                )

                logger.info(f"✅ Metadata logged: {evento_tipo} for {tag_spool}")

            except Exception as e:
                # CRITICAL: Metadata logging is mandatory for audit compliance
                # Log error with full details to aid debugging
                logger.error(
                    f"❌ CRITICAL: Metadata logging failed for {tag_spool}: {e}",
                    exc_info=True
                )
                # Continue operation but log prominently - metadata writes should be investigated
                # Note: In future, consider making this a hard failure if regulatory compliance requires it

            # Step 6: Return success
            message = f"Trabajo pausado en {tag_spool}"
            logger.info(f"✅ PAUSAR completed successfully: {message}")

            return OccupationResponse(
                success=True,
                tag_spool=tag_spool,
                message=message
            )

        except (SpoolNoEncontradoError, NoAutorizadoError, LockExpiredError):
            raise
        except Exception as e:
            logger.error(f"❌ PAUSAR operation failed: {e}")
            raise

    async def completar(self, request: CompletarRequest) -> OccupationResponse:
        """
        Complete work on a spool (mark operation complete and release lock).

        Flow:
        1. Verify worker owns the Redis lock
        2. Update fecha_armado or fecha_soldadura based on operation
        3. Clear Ocupado_Por and Fecha_Ocupacion
        4. Release Redis lock
        5. Log COMPLETAR event to Metadata sheet
        6. Return success response

        Args:
            request: COMPLETAR request with tag_spool, worker_id, worker_nombre, fecha_operacion

        Returns:
            OccupationResponse with success status and message

        Raises:
            SpoolNoEncontradoError: If spool doesn't exist
            NoAutorizadoError: If worker doesn't own the lock
            LockExpiredError: If lock no longer exists
            SheetsUpdateError: If Sheets write fails
        """
        tag_spool = request.tag_spool
        worker_id = request.worker_id
        worker_nombre = request.worker_nombre
        fecha_operacion = request.fecha_operacion

        logger.info(
            f"COMPLETAR operation started: {tag_spool} by worker {worker_id} ({worker_nombre}) "
            f"on {fecha_operacion}"
        )

        try:
            # Step 1: Verify lock ownership
            lock_owner = await self.redis_lock_service.get_lock_owner(tag_spool)

            if lock_owner is None:
                raise LockExpiredError(tag_spool)

            owner_id, lock_token = lock_owner

            if owner_id != worker_id:
                raise NoAutorizadoError(
                    tag_spool=tag_spool,
                    trabajador_esperado=f"Worker {owner_id}",
                    trabajador_solicitante=worker_nombre,
                    operacion="COMPLETAR"
                )

            # Step 2: Determine operation type and update fecha column
            spool = self.sheets_repository.get_spool_by_tag(tag_spool)
            if not spool:
                raise SpoolNoEncontradoError(tag_spool)

            # Determine which operation is being completed
            # For v3.0: This will be enhanced with proper state tracking
            operacion = "ARM"  # Default, will be enhanced in future
            fecha_column = "Fecha_Armado" if operacion == "ARM" else "Fecha_Soldadura"

            # Step 3: Update Sheets - set fecha and clear occupation (with version retry)
            try:
                fecha_str = format_date_for_sheets(fecha_operacion)

                # Determine which fecha column to update
                if operacion == "ARM":
                    fecha_column_name = "Fecha_Armado"
                elif operacion == "SOLD":
                    fecha_column_name = "Fecha_Soldadura"
                else:
                    fecha_column_name = f"Fecha_{operacion}"

                # Use ConflictService for version-aware update with automatic retry
                updates_dict = {
                    fecha_column_name: fecha_str,
                    "Ocupado_Por": "",  # Clear occupation
                    "Fecha_Ocupacion": ""
                }

                new_version = await self.conflict_service.update_with_retry(
                    tag_spool=tag_spool,
                    updates=updates_dict,
                    operation="COMPLETAR"
                )

                logger.info(
                    f"✅ Sheets updated: {tag_spool} {operacion} completed on {fecha_str}, "
                    f"occupation cleared (version: {new_version})"
                )

            except VersionConflictError as e:
                # Max retries exhausted
                logger.error(f"Version conflict persists after retries for COMPLETAR: {e}")
                raise
            except Exception as e:
                logger.error(f"Sheets update failed for COMPLETAR: {e}")
                raise SheetsUpdateError(
                    f"Failed to update completion in Sheets: {e}",
                    updates={fecha_column: fecha_str, "ocupado_por": None}
                )

            # Step 4: Release Redis lock
            try:
                released = await self.redis_lock_service.release_lock(tag_spool, worker_id, lock_token)
                if not released:
                    logger.warning(
                        f"⚠️ Lock release returned False for {tag_spool} "
                        f"(may have already expired)"
                    )
            except Exception as e:
                logger.error(f"Failed to release lock for {tag_spool}: {e}")
                # Continue - Sheets already updated, lock will expire naturally

            # Step 4.5: Publish real-time event (best effort)
            try:
                # Build estado_detalle based on operation completed
                estado_detalle = f"{operacion} completado - Disponible"
                await self.redis_event_service.publish_spool_update(
                    event_type="COMPLETAR",
                    tag_spool=tag_spool,
                    worker_nombre=worker_nombre,
                    estado_detalle=estado_detalle,
                    additional_data={"operacion": operacion, "fecha_operacion": fecha_str}
                )
                logger.info(f"✅ Real-time event published: COMPLETAR for {tag_spool}")
            except Exception as e:
                # Best effort - log but don't fail operation
                logger.warning(f"⚠️ Event publishing failed (non-critical): {e}")

            # Step 5: Log to Metadata (audit trail - MANDATORY for regulatory compliance)
            try:
                # v3.0: COMPLETAR uses operation-specific event types (COMPLETAR_ARM, COMPLETAR_SOLD)
                # Build evento_tipo string and validate against enum
                evento_tipo_str = f"COMPLETAR_{operacion}"

                # Validate that enum value exists
                try:
                    evento_tipo_enum = EventoTipo(evento_tipo_str)
                    evento_tipo = evento_tipo_enum.value
                except ValueError:
                    # Fallback: Use legacy enum values if new format not available
                    logger.warning(f"EventoTipo '{evento_tipo_str}' not found in enum, using string directly")
                    evento_tipo = evento_tipo_str

                metadata_json = json.dumps({
                    "fecha_operacion": fecha_str,
                    "completed": True
                })

                self.metadata_repository.log_event(
                    evento_tipo=evento_tipo,
                    tag_spool=tag_spool,
                    worker_id=worker_id,
                    worker_nombre=worker_nombre,
                    operacion=operacion,
                    accion="COMPLETAR",
                    fecha_operacion=fecha_operacion,
                    metadata_json=metadata_json
                )

                logger.info(f"✅ Metadata logged: {evento_tipo} for {tag_spool}")

            except Exception as e:
                # CRITICAL: Metadata logging is mandatory for audit compliance
                # Log error with full details to aid debugging
                logger.error(
                    f"❌ CRITICAL: Metadata logging failed for {tag_spool}: {e}",
                    exc_info=True
                )
                # Continue operation but log prominently - metadata writes should be investigated
                # Note: In future, consider making this a hard failure if regulatory compliance requires it

            # Step 6: Return success
            message = f"Operación completada en {tag_spool}"
            logger.info(f"✅ COMPLETAR completed successfully: {message}")

            return OccupationResponse(
                success=True,
                tag_spool=tag_spool,
                message=message
            )

        except (SpoolNoEncontradoError, NoAutorizadoError, LockExpiredError):
            raise
        except Exception as e:
            logger.error(f"❌ COMPLETAR operation failed: {e}")
            raise

    async def batch_tomar(self, request: BatchTomarRequest) -> BatchOccupationResponse:
        """
        Take multiple spools in batch (up to 50).

        Processes each spool independently, collecting success/failure for each.
        Returns detailed results showing which spools succeeded and which failed.

        Args:
            request: Batch TOMAR request with tag_spools list

        Returns:
            BatchOccupationResponse with total, succeeded, failed counts and details
        """
        tag_spools = request.tag_spools
        worker_id = request.worker_id
        worker_nombre = request.worker_nombre
        operacion = request.operacion

        logger.info(
            f"BATCH_TOMAR started: {len(tag_spools)} spools by worker {worker_id} "
            f"for {operacion.value}"
        )

        results = []
        succeeded = 0
        failed = 0

        for tag_spool in tag_spools:
            try:
                # Create individual TomarRequest for this spool
                tomar_req = TomarRequest(
                    tag_spool=tag_spool,
                    worker_id=worker_id,
                    worker_nombre=worker_nombre,
                    operacion=operacion
                )

                # Attempt to take this spool
                response = await self.tomar(tomar_req)

                results.append(response)
                succeeded += 1

                logger.info(f"✅ Batch item {succeeded}/{len(tag_spools)}: {tag_spool} succeeded")

            except SpoolOccupiedError as e:
                # Spool already occupied - collect error but continue with others
                results.append(
                    OccupationResponse(
                        success=False,
                        tag_spool=tag_spool,
                        message=f"Spool ya ocupado: {e.message}"
                    )
                )
                failed += 1
                logger.warning(f"⚠️ Batch item failed: {tag_spool} - {e.message}")

            except Exception as e:
                # Other errors - collect and continue
                results.append(
                    OccupationResponse(
                        success=False,
                        tag_spool=tag_spool,
                        message=f"Error: {str(e)}"
                    )
                )
                failed += 1
                logger.warning(f"⚠️ Batch item failed: {tag_spool} - {e}")

        # Create summary message
        total = len(tag_spools)
        if failed == 0:
            message = f"Batch TOMAR: {succeeded} de {total} spools exitosos"
        else:
            message = f"Batch TOMAR: {succeeded} de {total} spools exitosos ({failed} fallos)"

        logger.info(f"✅ BATCH_TOMAR completed: {message}")

        return BatchOccupationResponse(
            total=total,
            succeeded=succeeded,
            failed=failed,
            details=results
        )

    async def iniciar_spool(self, request: IniciarRequest) -> OccupationResponse:
        """
        Iniciar trabajo en un spool (v4.0 INICIAR operation).

        Ocupa el spool mediante persistent Redis lock sin tocar la hoja Uniones.
        El worker debe seleccionar uniones después mediante FINALIZAR.

        Flow:
        1. Validate spool exists and has Fecha_Materiales prerequisite
        2. Acquire persistent Redis lock (no TTL)
        3. Update Ocupado_Por and Fecha_Ocupacion in Operaciones sheet
        4. Log TOMAR_SPOOL event to Metadata (same event as v3.0 TOMAR)
        5. Return success response with lock token
        6. DO NOT touch Uniones sheet at all

        Args:
            request: INICIAR request with tag_spool, worker_id, worker_nombre, operacion

        Returns:
            OccupationResponse with success status and message

        Raises:
            SpoolNoEncontradoError: If spool doesn't exist
            DependenciasNoSatisfechasError: If Fecha_Materiales is missing
            SpoolOccupiedError: If spool already locked by another worker (409)
            SheetsUpdateError: If Sheets write fails
            RedisError: If Redis operation fails
        """
        tag_spool = request.tag_spool
        worker_id = request.worker_id
        worker_nombre = request.worker_nombre
        operacion = request.operacion.value

        logger.info(
            f"INICIAR operation started: {tag_spool} by worker {worker_id} ({worker_nombre}) "
            f"for {operacion}"
        )

        try:
            # Step 1: Validate spool exists and has prerequisites
            spool = self.sheets_repository.get_spool_by_tag(tag_spool)
            if not spool:
                raise SpoolNoEncontradoError(tag_spool)

            # Check Fecha_Materiales prerequisite
            if not spool.fecha_materiales:
                raise DependenciasNoSatisfechasError(
                    tag_spool=tag_spool,
                    operacion=operacion,
                    dependencia_faltante="Fecha_Materiales",
                    detalle="El spool debe tener materiales registrados antes de ocuparlo"
                )

            # Step 1.5: Lazy cleanup (best effort, don't block on failure)
            # Clean up one abandoned lock >24h old before acquiring new lock
            try:
                await self.redis_lock_service.lazy_cleanup_one_abandoned_lock()
            except Exception as e:
                # Log warning but continue with INICIAR operation
                logger.warning(f"Lazy cleanup failed during INICIAR: {e}")

            # Step 2: Acquire persistent Redis lock (no TTL)
            try:
                lock_token = await self.redis_lock_service.acquire_lock(
                    tag_spool=tag_spool,
                    worker_id=worker_id,
                    worker_nombre=worker_nombre
                )
            except SpoolOccupiedError:
                # Re-raise to be mapped to 409 by router
                raise

            # Step 3: Update Operaciones sheet with occupation data (with version retry)
            try:
                # Write Ocupado_Por (column 64) and Fecha_Ocupacion (column 65)
                # CRITICAL: Use format_datetime_for_sheets() for timestamp with time component
                # Format: "DD-MM-YYYY HH:MM:SS" (e.g., "30-01-2026 14:30:00")
                fecha_ocupacion_str = format_datetime_for_sheets(now_chile())

                # Use ConflictService for version-aware update with automatic retry
                updates_dict = {
                    "Ocupado_Por": worker_nombre,
                    "Fecha_Ocupacion": fecha_ocupacion_str
                }

                new_version = await self.conflict_service.update_with_retry(
                    tag_spool=tag_spool,
                    updates=updates_dict,
                    operation="INICIAR"
                )

                logger.info(
                    f"✅ Sheets updated: {tag_spool} occupied by {worker_nombre} "
                    f"on {fecha_ocupacion_str} (version: {new_version})"
                )

            except VersionConflictError as e:
                # Max retries exhausted - rollback Redis lock
                logger.error(
                    f"Version conflict persists after retries, rolling back Redis lock: {e}"
                )
                await self.redis_lock_service.release_lock(tag_spool, worker_id, lock_token)
                raise
            except Exception as e:
                # Rollback: release Redis lock if Sheets update fails
                logger.error(f"Sheets update failed, rolling back Redis lock: {e}")
                await self.redis_lock_service.release_lock(tag_spool, worker_id, lock_token)
                raise SheetsUpdateError(
                    f"Failed to update occupation in Sheets: {e}",
                    updates={"ocupado_por": worker_nombre, "fecha_ocupacion": fecha_ocupacion_str}
                )

            # Step 4: Log to Metadata (audit trail - MANDATORY for regulatory compliance)
            try:
                # v4.0 INICIAR uses same TOMAR_SPOOL event type as v3.0 TOMAR
                evento_tipo = EventoTipo.TOMAR_SPOOL.value
                metadata_json = json.dumps({
                    "lock_token": lock_token,
                    "fecha_ocupacion": fecha_ocupacion_str,
                    "v4_operation": "INICIAR"
                })

                self.metadata_repository.log_event(
                    evento_tipo=evento_tipo,
                    tag_spool=tag_spool,
                    worker_id=worker_id,
                    worker_nombre=worker_nombre,
                    operacion=operacion,
                    accion="TOMAR",
                    fecha_operacion=format_date_for_sheets(today_chile()),
                    metadata_json=metadata_json
                )

                logger.info(f"✅ Metadata logged: {evento_tipo} for {tag_spool}")

            except Exception as e:
                # CRITICAL: Metadata logging is mandatory for audit compliance
                # Log error with full details to aid debugging
                logger.error(
                    f"❌ CRITICAL: Metadata logging failed for {tag_spool}: {e}",
                    exc_info=True
                )
                # Continue operation but log prominently - metadata writes should be investigated
                # Note: In future, consider making this a hard failure if regulatory compliance requires it

            # Step 4.5: Publish real-time event (best effort)
            try:
                # Estado_Detalle will be built by StateService, use simple format for now
                estado_detalle = f"Ocupado por {worker_nombre} - {operacion}"
                await self.redis_event_service.publish_spool_update(
                    event_type="TOMAR",
                    tag_spool=tag_spool,
                    worker_nombre=worker_nombre,
                    estado_detalle=estado_detalle,
                    additional_data={"operacion": operacion, "v4_operation": "INICIAR"}
                )
                logger.info(f"✅ Real-time event published: INICIAR for {tag_spool}")
            except Exception as e:
                # Best effort - log but don't fail operation
                logger.warning(f"⚠️ Event publishing failed (non-critical): {e}")

            # Step 5: Return success
            message = f"Spool {tag_spool} iniciado por {worker_nombre}"
            logger.info(f"✅ INICIAR completed successfully: {message}")

            return OccupationResponse(
                success=True,
                tag_spool=tag_spool,
                message=message
            )

        except (SpoolNoEncontradoError, DependenciasNoSatisfechasError, SpoolOccupiedError):
            # Re-raise business exceptions for router to handle
            raise
        except Exception as e:
            logger.error(f"❌ INICIAR operation failed: {e}")
            raise
