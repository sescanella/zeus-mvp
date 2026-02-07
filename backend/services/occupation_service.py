"""
OccupationService - Core business logic for TOMAR/PAUSAR/COMPLETAR operations.

Simplified for single-user mode (1 tablet, 1 worker):
- TOMAR: Write Ocupado_Por/Fecha_Ocupacion to Operaciones
- PAUSAR: Update state to "parcial (pausado)" and clear occupation
- COMPLETAR: Write fecha_armado/soldadura and clear occupation

Orchestrates:
- SheetsRepository: Write to Operaciones sheet
- MetadataRepository: Audit trail logging
- ConflictService: Version-aware updates with retry
"""

import logging
import json
from typing import Optional
from datetime import date, datetime

from backend.utils.date_formatter import format_date_for_sheets, format_datetime_for_sheets, today_chile, now_chile
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
    before_sleep_log
)

from backend.services.conflict_service import ConflictService
from backend.repositories.sheets_repository import SheetsRepository
from backend.repositories.metadata_repository import MetadataRepository
from backend.services.union_service import UnionService
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
from backend.services.metadata_event_builder import MetadataEventBuilder, build_metadata_event

# SOLD_REQUIRED_TYPES: Union types that require SOLD operation (imported from union_service)
# FW unions are ARM-only (no SOLD needed)
SOLD_REQUIRED_TYPES = ['BW', 'BR', 'SO', 'FILL', 'LET']
from backend.exceptions import (
    SpoolNoEncontradoError,
    SpoolOccupiedError,
    DependenciasNoSatisfechasError,
    NoAutorizadoError,
    LockExpiredError,
    SheetsUpdateError,
    VersionConflictError,
    ArmPrerequisiteError
)

logger = logging.getLogger(__name__)


class OccupationService:
    """
    Service for spool occupation operations with Sheets updates.

    Simplified for single-user mode: No Redis locks needed with 1 tablet.
    Implements TOMAR/PAUSAR/COMPLETAR with version-aware updates via ConflictService.
    """

    def __init__(
        self,
        sheets_repository: SheetsRepository,
        metadata_repository: MetadataRepository,
        conflict_service: ConflictService,
        union_repository=None,  # Optional dependency for v4.0 operations
        validation_service=None,  # Optional dependency for v4.0 validations
        union_service: Optional[UnionService] = None  # Optional dependency for v4.0 batch + granular logging
    ):
        """
        Initialize occupation service with injected dependencies.

        Args:
            sheets_repository: Repository for Sheets writes
            metadata_repository: Repository for audit logging
            conflict_service: Service for version conflict handling and retry
            union_repository: Repository for union-level operations (v4.0)
            validation_service: Service for business rule validation (v4.0)
            union_service: Service for batch union updates with metadata logging (v4.0)
        """
        self.sheets_repository = sheets_repository
        self.metadata_repository = metadata_repository
        self.conflict_service = conflict_service
        self.union_repository = union_repository
        self.validation_service = validation_service
        self.union_service = union_service
        logger.info("OccupationService initialized (single-user mode)")

    async def tomar(self, request: TomarRequest) -> OccupationResponse:
        """
        Take a spool (mark as occupied in Sheets).

        Simplified for single-user mode: No locks needed with 1 tablet.

        Flow:
        1. Validate spool exists and has Fecha_Materiales prerequisite
        2. Check if already occupied in Sheets (Ocupado_Por != NULL)
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
            SpoolOccupiedError: If spool already occupied (409)
            SheetsUpdateError: If Sheets write fails
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

            # Step 2: Check if already occupied (single-user validation)
            if spool.ocupado_por and spool.ocupado_por != "DISPONIBLE":
                raise SpoolOccupiedError(
                    tag_spool=tag_spool,
                    owner_id=worker_id,  # In single-user mode, always same worker
                    owner_name=spool.ocupado_por
                )

            # Step 3: Update Operaciones sheet with occupation data
            try:
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
                logger.error(f"Version conflict persists after retries: {e}")
                raise
            except Exception as e:
                logger.error(f"Sheets update failed: {e}")
                raise SheetsUpdateError(
                    f"Failed to update occupation in Sheets: {e}",
                    updates={"ocupado_por": worker_nombre, "fecha_ocupacion": fecha_ocupacion_str}
                )

            # Step 4: Log to Metadata (audit trail - MANDATORY)
            try:
                event = (
                    MetadataEventBuilder()
                    .for_tomar(tag_spool, worker_id, worker_nombre)
                    .with_operacion(operacion)
                    .with_metadata({"fecha_ocupacion": fecha_ocupacion_str})
                    .build()
                )
                self.metadata_repository.log_event(**event)

                logger.info(f"✅ Metadata logged: TOMAR_SPOOL for {tag_spool}")

            except Exception as e:
                logger.error(
                    f"❌ CRITICAL: Metadata logging failed for {tag_spool}: {e}",
                    exc_info=True
                )

            # Step 5: Return success
            message = f"Spool {tag_spool} tomado por {worker_nombre}"
            logger.info(f"✅ TOMAR completed successfully: {message}")

            return OccupationResponse(
                success=True,
                tag_spool=tag_spool,
                message=message
            )

        except (SpoolNoEncontradoError, DependenciasNoSatisfechasError, SpoolOccupiedError):
            raise
        except Exception as e:
            logger.error(f"❌ TOMAR operation failed: {e}")
            raise

    async def pausar(self, request: PausarRequest) -> OccupationResponse:
        """
        Pause work on a spool (mark as partially complete and clear occupation).

        Simplified for single-user mode: No lock ownership check needed.

        Flow:
        1. Validate spool exists and is occupied
        2. Update spool state in Operaciones sheet to "ARM parcial (pausado)" or "SOLD parcial (pausado)"
        3. Clear Ocupado_Por and Fecha_Ocupacion columns
        4. Log PAUSAR event to Metadata sheet
        5. Return success response

        Args:
            request: PAUSAR request with tag_spool, worker_id, worker_nombre

        Returns:
            OccupationResponse with success status and message

        Raises:
            SpoolNoEncontradoError: If spool doesn't exist
            NoAutorizadoError: If spool not occupied
            SheetsUpdateError: If Sheets write fails
        """
        tag_spool = request.tag_spool
        worker_id = request.worker_id
        worker_nombre = request.worker_nombre

        logger.info(
            f"PAUSAR operation started: {tag_spool} by worker {worker_id} ({worker_nombre})"
        )

        try:
            # Step 1: Validate spool exists and is occupied
            spool = self.sheets_repository.get_spool_by_tag(tag_spool)
            if not spool:
                raise SpoolNoEncontradoError(tag_spool)

            # Check if spool is occupied
            if not spool.ocupado_por or spool.ocupado_por == "DISPONIBLE":
                raise NoAutorizadoError(
                    tag_spool=tag_spool,
                    trabajador_esperado="Ninguno",
                    trabajador_solicitante=worker_nombre,
                    operacion="PAUSAR"
                )

            # Determine which operation is being paused
            operacion = "ARM"  # Default, will be enhanced with state tracking
            estado_pausado = f"{operacion} parcial (pausado)"

            # Step 2: Clear occupation fields
            try:
                updates_dict = {
                    "Ocupado_Por": "",
                    "Fecha_Ocupacion": ""
                }

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
                logger.error(f"Version conflict persists after retries for PAUSAR: {e}")
                raise
            except Exception as e:
                logger.error(f"Sheets update failed for PAUSAR: {e}")
                raise SheetsUpdateError(
                    f"Failed to update paused state in Sheets: {e}",
                    updates={"estado": estado_pausado, "ocupado_por": None}
                )

            # Step 3: Log to Metadata (audit trail - MANDATORY)
            try:
                evento_tipo = EventoTipo.PAUSAR_SPOOL.value
                metadata_json = json.dumps({
                    "estado": estado_pausado
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
                logger.error(
                    f"❌ CRITICAL: Metadata logging failed for {tag_spool}: {e}",
                    exc_info=True
                )

            # Step 4: Return success
            message = f"Trabajo pausado en {tag_spool}"
            logger.info(f"✅ PAUSAR completed successfully: {message}")

            return OccupationResponse(
                success=True,
                tag_spool=tag_spool,
                message=message
            )

        except (SpoolNoEncontradoError, NoAutorizadoError):
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
        Iniciar trabajo en un spool (P5 Confirmation workflow).

        Called from P5 (Confirmation screen) when user confirms INICIAR action.
        Writes Ocupado_Por, Fecha_Ocupacion, and Estado_Detalle to Operaciones sheet.

        Flow (P5 Confirmation):
        1. Validate spool exists and has Fecha_Materiales prerequisite
        2. Validate ARM prerequisite for SOLD operations (v4.0)
        3. NO validate if already occupied (trust P4 filters, accept LWW race)
        4. Build Estado_Detalle with EstadoDetalleBuilder (hardcoded states)
        5. Write Ocupado_Por + Fecha_Ocupacion + Estado_Detalle to Sheets (with retry)
        6. Log INICIAR_SPOOL event to Metadata (minimal fields)
        7. Return success response
        8. DO NOT touch Uniones sheet (no union selection in INICIAR)

        Version Compatibility:
        - v2.1 spools: Write only v3.0 fields (Ocupado_Por, Fecha_Ocupacion, Estado_Detalle)
        - v4.0 spools: Same as v2.1 (no Uniones modification until FINALIZAR)

        Args:
            request: INICIAR request with tag_spool, worker_id, worker_nombre, operacion

        Returns:
            OccupationResponse with success status and message

        Raises:
            SpoolNoEncontradoError: If spool doesn't exist (404)
            DependenciasNoSatisfechasError: If Fecha_Materiales is missing (400)
            ArmPrerequisiteError: If SOLD operation without ARM completion (403)
            SpoolOccupiedError: If spool already occupied (race condition) (409)
            SheetsUpdateError: If Sheets write fails (500)
        """
        tag_spool = request.tag_spool
        worker_id = request.worker_id
        worker_nombre = request.worker_nombre
        operacion = request.operacion.value

        logger.info(
            f"[P5 INICIAR] Started: {tag_spool} by worker {worker_id} ({worker_nombre}) "
            f"for {operacion}"
        )

        try:
            # Step 1: Validate spool exists and has prerequisites
            spool = self.sheets_repository.get_spool_by_tag(tag_spool)
            if not spool:
                raise SpoolNoEncontradoError(tag_spool)

            # Detect spool version (v2.1/v3.0 vs v4.0)
            # v3.0: total_uniones = None (no column) or 0 (CONTAR.SI formula with no unions)
            # v4.0: total_uniones >= 1 (has registered unions in Uniones sheet)
            is_v21 = spool.total_uniones is None or spool.total_uniones == 0
            version_str = "v3.0" if is_v21 else "v4.0"
            logger.info(f"Spool {tag_spool} detected as {version_str} (total_uniones={spool.total_uniones})")

            # Check Fecha_Materiales prerequisite
            if not spool.fecha_materiales:
                raise DependenciasNoSatisfechasError(
                    tag_spool=tag_spool,
                    operacion=operacion,
                    dependencia_faltante="Fecha_Materiales",
                    detalle="El spool debe tener materiales registrados antes de ocuparlo"
                )

            # Step 2: Validate ARM prerequisite for SOLD operations (simple version-aware logic)
            if operacion == "SOLD":
                # Version detection (already done at line 660: is_v21 = spool.total_uniones is None)

                if is_v21:  # v2.1/v3.0 spool - use Fecha_Armado column
                    if not spool.fecha_armado:
                        logger.warning(f"ARM prerequisite failed for v3.0 spool {tag_spool}: Fecha_Armado is empty")
                        raise ArmPrerequisiteError(
                            tag_spool=tag_spool,
                            message="No se puede iniciar SOLD: ARM no completado (Fecha_Armado vacía)"
                        )
                    logger.info(f"✅ ARM prerequisite passed for v3.0 spool {tag_spool} (Fecha_Armado: {spool.fecha_armado})")

                else:  # v4.0 spool - use Uniones_ARM_Completadas column
                    # Treat None as 0 explicitly (column not initialized yet)
                    unions_completed = spool.uniones_arm_completadas or 0
                    total = spool.total_uniones or 0

                    if unions_completed < 1:
                        logger.warning(
                            f"ARM prerequisite failed for v4.0 spool {tag_spool}: "
                            f"{unions_completed}/{total} unions with ARM completed (need >= 1)"
                        )
                        raise ArmPrerequisiteError(
                            tag_spool=tag_spool,
                            message=f"No se puede iniciar SOLD: {unions_completed}/{total} uniones armadas (requiere >= 1)",
                            unions_sin_armar=total - unions_completed
                        )
                    logger.info(
                        f"✅ ARM prerequisite passed for v4.0 spool {tag_spool} "
                        f"({unions_completed}/{total} unions with ARM completed)"
                    )

            # Step 3: NO validate if already occupied (decision: trust P4 filters, accept LWW)
            # If race condition occurs, last-write-wins (LWW)
            # Error detected when P4 re-reads and spool disappears from available list

            # Step 4: Build Estado_Detalle with EstadoDetalleBuilder
            from backend.services.estado_detalle_builder import EstadoDetalleBuilder

            # Hardcoded states based on operacion
            if operacion == "ARM":
                arm_state = "en_progreso"
                sold_state = "pendiente"
            elif operacion == "SOLD":
                arm_state = "completado"
                sold_state = "en_progreso"
            else:  # METROLOGIA, REPARACION, etc.
                arm_state = "completado"
                sold_state = "completado"

            builder = EstadoDetalleBuilder()
            estado_detalle = builder.build(
                ocupado_por=worker_nombre,
                arm_state=arm_state,
                sold_state=sold_state,
                operacion_actual=operacion
            )

            logger.info(f"Estado_Detalle built: '{estado_detalle}'")

            # Step 5: Write to Operaciones sheet (with @retry_on_sheets_error)
            try:
                fecha_ocupacion_str = format_datetime_for_sheets(now_chile())

                # Build updates dict
                updates_dict = {
                    "Ocupado_Por": worker_nombre,          # Column 64
                    "Fecha_Ocupacion": fecha_ocupacion_str,  # Column 65
                    "Estado_Detalle": estado_detalle       # Column 67
                }

                # Get spool row number for batch update
                from backend.core.column_map_cache import ColumnMapCache
                from backend.config import config

                column_map = ColumnMapCache.get_or_build(config.HOJA_OPERACIONES_NOMBRE, self.sheets_repository)

                def normalize(name: str) -> str:
                    return name.lower().replace(" ", "").replace("_", "").replace("/", "")

                # Find TAG_SPOOL column
                tag_column_index = None
                for col_name in ["TAG_SPOOL", "SPLIT", "tag_spool"]:
                    normalized = normalize(col_name)
                    if normalized in column_map:
                        tag_column_index = column_map[normalized]
                        break

                if tag_column_index is None:
                    tag_column_index = 6  # Fallback to column G

                column_letter = self.sheets_repository._index_to_column_letter(tag_column_index)

                row_num = self.sheets_repository.find_row_by_column_value(
                    sheet_name=config.HOJA_OPERACIONES_NOMBRE,
                    column_letter=column_letter,
                    value=tag_spool
                )

                if row_num is None:
                    raise SpoolNoEncontradoError(tag_spool)

                # Prepare batch update
                batch_updates = [
                    {"row": row_num, "column_name": key, "value": value}
                    for key, value in updates_dict.items()
                ]

                # Execute batch update with automatic retry (@retry_on_sheets_error)
                self.sheets_repository.batch_update_by_column_name(
                    sheet_name=config.HOJA_OPERACIONES_NOMBRE,
                    updates=batch_updates
                )

                logger.info(
                    f"✅ Sheets updated: {tag_spool} occupied by {worker_nombre} "
                    f"on {fecha_ocupacion_str}"
                )

            except Exception as e:
                logger.error(f"Sheets update failed for INICIAR: {e}")
                raise SheetsUpdateError(
                    f"Failed to update occupation in Sheets: {e}",
                    updates={"ocupado_por": worker_nombre, "fecha_ocupacion": fecha_ocupacion_str}
                )

            # Step 6: Log to Metadata (minimal fields only)
            try:
                evento_tipo = EventoTipo.INICIAR_SPOOL.value  # NEW event type
                metadata_json = json.dumps({
                    "ocupado_por": worker_nombre,
                    "fecha_ocupacion": fecha_ocupacion_str
                    # NO include: lock_token, v4_operation, spool_version (minimalismo)
                })

                self.metadata_repository.log_event(
                    evento_tipo=evento_tipo,
                    tag_spool=tag_spool,
                    worker_id=worker_id,
                    worker_nombre=worker_nombre,
                    operacion=operacion,
                    accion="INICIAR",
                    fecha_operacion=format_date_for_sheets(today_chile()),
                    metadata_json=metadata_json
                )

                logger.info(f"✅ Metadata logged: {evento_tipo} for {tag_spool}")

            except Exception as e:
                # CRITICAL: Metadata logging is mandatory for audit compliance
                logger.error(
                    f"❌ CRITICAL: Metadata logging failed for {tag_spool}: {e}",
                    exc_info=True
                )
                # Continue operation - metadata write failures should be investigated
                # but don't block user workflow

            # Step 7: Return success
            message = f"Spool {tag_spool} iniciado por {worker_nombre}"
            logger.info(f"✅ [P5 INICIAR] Completed successfully: {message}")

            return OccupationResponse(
                success=True,
                tag_spool=tag_spool,
                message=message
            )

        except (SpoolNoEncontradoError, DependenciasNoSatisfechasError, ArmPrerequisiteError, SpoolOccupiedError):
            # Re-raise business exceptions for router to handle
            raise
        except Exception as e:
            logger.error(f"❌ [P5 INICIAR] Operation failed: {e}", exc_info=True)
            raise

    def _determine_action(
        self,
        selected_count: int,
        total_available: int,
        operacion: str
    ) -> str:
        """
        Determine if action should be PAUSAR or COMPLETAR based on selected vs total.

        Auto-determination logic:
        - If selected_count == total_available → COMPLETAR (all work done)
        - If selected_count < total_available → PAUSAR (partial work)
        - If selected_count > total_available → 409 Conflict (race condition)

        For SOLD: total_available counts only SOLD_REQUIRED_TYPES unions (BW/BR/SO/FILL/LET).
        FW unions are ARM-only and excluded from SOLD completion logic.

        Args:
            selected_count: Number of unions selected by worker
            total_available: Total available unions for this operation
                            (for SOLD: filtered to SOLD_REQUIRED_TYPES only)
            operacion: Operation type ("ARM" or "SOLD")

        Returns:
            str: "PAUSAR" or "COMPLETAR"

        Raises:
            ValueError: If selected_count > total_available (race condition)
        """
        if selected_count > total_available:
            raise ValueError(
                f"Race condition detected: {selected_count} unions selected but only "
                f"{total_available} available for {operacion}"
            )

        if selected_count == total_available:
            return "COMPLETAR"
        else:
            return "PAUSAR"

    def should_trigger_metrologia(self, tag_spool: str) -> bool:
        """
        Determine if spool should automatically transition to metrología queue.

        Metrología triggers when ALL work is complete:
        - FW unions (ARM-only): All have ARM_FECHA_FIN != NULL
        - SOLD-required unions (BW/BR/SO/FILL/LET): All have SOL_FECHA_FIN != NULL

        Args:
            tag_spool: TAG_SPOOL value to check

        Returns:
            bool: True if all work complete and metrología should trigger

        Raises:
            ValueError: If UnionRepository not configured
        """
        if self.union_repository is None:
            raise ValueError("UnionRepository not configured for metrología detection")

        logger.info(f"Checking metrología trigger for {tag_spool}")

        try:
            # Get all unions for this spool
            all_unions = self.union_repository.get_by_spool(tag_spool)

            if not all_unions:
                logger.warning(f"No unions found for {tag_spool}, cannot trigger metrología")
                return False

            # SOLD_REQUIRED_TYPES: Union types that need SOLD operation
            # FW unions are ARM-only (no SOLD needed)
            from backend.services.union_service import SOLD_REQUIRED_TYPES

            # Separate unions into FW (ARM-only) and SOLD-required
            fw_unions = [u for u in all_unions if u.tipo_union not in SOLD_REQUIRED_TYPES]
            sold_required_unions = [u for u in all_unions if u.tipo_union in SOLD_REQUIRED_TYPES]

            logger.debug(
                f"Union breakdown for {tag_spool}: "
                f"{len(fw_unions)} FW (ARM-only), {len(sold_required_unions)} SOLD-required"
            )

            # Check FW unions: All must have ARM_FECHA_FIN != NULL
            for union in fw_unions:
                if union.arm_fecha_fin is None:
                    logger.debug(
                        f"FW union {union.id} ARM incomplete (arm_fecha_fin=None), "
                        f"cannot trigger metrología"
                    )
                    return False

            # Check SOLD-required unions: All must have SOL_FECHA_FIN != NULL
            for union in sold_required_unions:
                if union.sol_fecha_fin is None:
                    logger.debug(
                        f"SOLD-required union {union.id} SOLD incomplete (sol_fecha_fin=None), "
                        f"cannot trigger metrología"
                    )
                    return False

            # All checks passed - metrología should trigger
            logger.info(
                f"✅ All work complete for {tag_spool}: "
                f"{len(fw_unions)} FW ARM'd, {len(sold_required_unions)} SOLD'd - "
                f"triggering metrología"
            )
            return True

        except Exception as e:
            logger.error(f"Failed to check metrología trigger for {tag_spool}: {e}")
            # Don't block operation on metrología check failure
            return False

    async def finalizar_spool(self, request: FinalizarRequest) -> OccupationResponse:
        """
        Finalizar trabajo en un spool (v4.0 FINALIZAR operation).

        Procesa las uniones seleccionadas y auto-determina si debe PAUSAR o COMPLETAR
        basado en si se procesaron todas las uniones disponibles.

        selected_unions vacío = cancellation (libera lock sin tocar Uniones).

        Flow:
        1. Verify worker owns the Redis lock
        2. Get fresh union totals from UnionRepository
        3. If selected_unions is empty → handle as cancellation
        4. Calculate if action is PAUSAR or COMPLETAR based on selected vs total
        5. Update Uniones sheet with batch operation
        6. Release Redis lock and clear Ocupado_Por
        7. Log appropriate event to Metadata
        8. Return response with action_taken and unions_processed

        Args:
            request: FINALIZAR request with tag_spool, worker_id, worker_nombre, operacion, selected_unions

        Returns:
            OccupationResponse with action_taken and unions_processed

        Raises:
            SpoolNoEncontradoError: If spool doesn't exist
            NoAutorizadoError: If worker doesn't own the lock
            LockExpiredError: If lock no longer exists
            ValueError: If race condition (union became unavailable)
            SheetsUpdateError: If Sheets write fails
        """
        tag_spool = request.tag_spool
        worker_id = request.worker_id
        worker_nombre = request.worker_nombre
        operacion = request.operacion.value
        selected_unions = request.selected_unions

        logger.info(
            f"[P5 FINALIZAR] Started: {tag_spool} by worker {worker_id} ({worker_nombre}) "
            f"for {operacion}, {len(selected_unions)} unions selected"
        )

        try:
            # Step 1: NO verify lock ownership (decision: trust P4 filters)
            # FINALIZAR can only be called if spool appeared in P4 filtered list
            # (Ocupado_Por = worker_actual), so lock validation is redundant

            # Step 2: Validate spool exists
            spool = self.sheets_repository.get_spool_by_tag(tag_spool)
            if not spool:
                raise SpoolNoEncontradoError(tag_spool)

            # Step 2.5: Detect v3.0 spools and use simplified COMPLETAR path
            #
            # v3.0 detection: total_uniones = None (no column) or 0 (CONTAR.SI formula)
            # v4.0 detection: total_uniones >= 1 (has registered unions)
            #
            # IMPORTANT: v3.0 spools may have total_uniones=0 due to the formula
            # =CONTAR.SI(Uniones!$D:$D,Gx) counting 0 when no unions are registered.
            is_v30 = spool.total_uniones is None or spool.total_uniones == 0

            if is_v30:
                logger.info(
                    f"v3.0 spool detected for {tag_spool} "
                    f"(total_uniones={spool.total_uniones})"
                )

                # Warning: v3.0 should not receive selected_unions from UI
                # (but if it does, we ignore them - not an error)
                if len(selected_unions) > 0:
                    logger.warning(
                        f"v3.0 spool {tag_spool} received {len(selected_unions)} "
                        f"selected_unions (will be ignored by simplified COMPLETAR logic)"
                    )

                return await self._finalizar_v30_spool(
                    tag_spool=tag_spool,
                    worker_id=worker_id,
                    worker_nombre=worker_nombre,
                    operacion=operacion,
                    spool=spool
                )

            # Step 3: Handle zero-union cancellation (v4.0 only)
            if len(selected_unions) == 0:
                logger.info(f"Zero unions selected - handling as cancellation for {tag_spool}")

                # Release Redis lock
                try:
                    await self.redis_lock_service.release_lock(tag_spool, worker_id, lock_token)
                except Exception as e:
                    logger.warning(f"Failed to release lock during cancellation: {e}")

                # Clear occupation fields (with version retry)
                try:
                    updates_dict = {
                        "Ocupado_Por": "",
                        "Fecha_Ocupacion": ""
                    }

                    await self.conflict_service.update_with_retry(
                        tag_spool=tag_spool,
                        updates=updates_dict,
                        operation="CANCELAR"
                    )

                    logger.info(f"✅ Occupation cleared for {tag_spool}")

                except Exception as e:
                    logger.error(f"Failed to clear occupation during cancellation: {e}")
                    # Continue - lock already released

                # Log cancellation event to Metadata
                try:
                    evento_tipo = EventoTipo.SPOOL_CANCELADO.value
                    metadata_json = json.dumps({
                        "reason": "zero_unions_selected"
                    })

                    self.metadata_repository.log_event(
                        evento_tipo=evento_tipo,
                        tag_spool=tag_spool,
                        worker_id=worker_id,
                        worker_nombre=worker_nombre,
                        operacion=operacion,
                        accion="CANCELAR",
                        fecha_operacion=format_date_for_sheets(today_chile()),
                        metadata_json=metadata_json
                    )

                    logger.info(f"✅ Metadata logged: {evento_tipo} for {tag_spool}")

                except Exception as e:
                    logger.error(f"❌ CRITICAL: Metadata logging failed for cancellation: {e}")


                return OccupationResponse(
                    success=True,
                    tag_spool=tag_spool,
                    message=f"Trabajo cancelado en {tag_spool}",
                    action_taken="CANCELADO",
                    unions_processed=0
                )

            # Step 4a: Handle REPARACION workflow (spool-level only, no unions)
            if operacion == "REPARACION":
                logger.info(f"[REPARACION FINALIZAR] Processing {tag_spool} without union tracking")

                # REPARACION always marks as completed (no PAUSAR support)
                action_taken = "COMPLETAR"

                # Clear occupation, metrología date, and update estado_detalle
                # CRITICAL: Clear Fecha_QC_Metrología so spool returns to PENDIENTE_METROLOGIA state
                updates_dict = {
                    "Ocupado_Por": "",
                    "Fecha_Ocupacion": "",
                    "Fecha_QC_Metrología": "",  # Reset metrología - spool must be re-inspected after repair
                    "Estado_Detalle": "REPARACION completado - PENDIENTE_METROLOGIA"
                }

                # Use batch_update_by_column_name with automatic retry
                from backend.core.column_map_cache import ColumnMapCache
                from backend.config import config

                column_map = ColumnMapCache.get_or_build(config.HOJA_OPERACIONES_NOMBRE, self.sheets_repository)

                def normalize(name: str) -> str:
                    return name.lower().replace(" ", "").replace("_", "").replace("/", "")

                # Find TAG_SPOOL column
                tag_column_index = None
                for col_name in ["TAG_SPOOL", "SPLIT", "tag_spool"]:
                    normalized = normalize(col_name)
                    if normalized in column_map:
                        tag_column_index = column_map[normalized]
                        break

                if tag_column_index is None:
                    tag_column_index = 6  # Fallback

                batch_updates = [{"column_name": k, "value": v} for k, v in updates_dict.items()]

                try:
                    self.sheets_repository.batch_update_by_column_name(
                        tag_spool=tag_spool,
                        tag_column_index=tag_column_index,
                        updates=batch_updates,
                        expected_version=None  # REPARACION doesn't use version column
                    )
                    logger.info(f"✅ REPARACION occupation cleared for {tag_spool}")
                except Exception as e:
                    logger.error(f"Failed to clear occupation for REPARACION: {e}")
                    raise SheetsUpdateError(
                        f"Failed to clear REPARACION occupation: {e}",
                        updates=updates_dict
                    )

                # Log metadata event
                try:
                    evento_tipo = EventoTipo.FINALIZAR_SPOOL.value
                    metadata_json = json.dumps({
                        "pulgadas": 0.0,  # REPARACION has no pulgadas metric
                        "action_determined": action_taken
                    })

                    self.metadata_repository.log_event(
                        evento_tipo=evento_tipo,
                        tag_spool=tag_spool,
                        worker_id=worker_id,
                        worker_nombre=worker_nombre,
                        operacion=operacion,
                        accion="FINALIZAR",
                        fecha_operacion=format_date_for_sheets(today_chile()),
                        metadata_json=metadata_json
                    )

                    logger.info(f"✅ Metadata logged: {evento_tipo} for REPARACION {tag_spool}")

                except Exception as e:
                    logger.error(f"❌ CRITICAL: Metadata logging failed for REPARACION: {e}")

                # Return early for REPARACION
                return OccupationResponse(
                    success=True,
                    tag_spool=tag_spool,
                    message=f"REPARACION finalizada en {tag_spool} - PENDIENTE_METROLOGIA",
                    action_taken=action_taken,
                    unions_processed=0,
                    pulgadas=0.0
                )

            # Step 4b: Standard ARM/SOLD workflow with union tracking
            if self.union_repository is None:
                raise ValueError("UnionRepository not configured for v4.0 operations")

            # Get available unions for this operation
            if operacion == "ARM":
                disponibles = self.union_repository.get_disponibles_arm_by_ot(spool.ot)
            elif operacion == "SOLD":
                # Get all ARM-completed unions
                all_disponibles = self.union_repository.get_disponibles_sold_by_ot(spool.ot)
                # Filter to only SOLD-required types (exclude FW which is ARM-only)
                disponibles = [
                    u for u in all_disponibles
                    if u.tipo_union in SOLD_REQUIRED_TYPES
                ]
                logger.debug(
                    f"SOLD disponibles filtered: {len(all_disponibles)} total ARM-complete, "
                    f"{len(disponibles)} SOLD-required types for OT {spool.ot}"
                )
            else:
                raise ValueError(f"Unsupported operation: {operacion}")

            total_available = len(disponibles)
            selected_count = len(selected_unions)

            logger.info(
                f"Union availability for {tag_spool}: {selected_count} selected, "
                f"{total_available} available for {operacion}"
            )

            # Step 5: Auto-determine action (PAUSAR vs COMPLETAR)
            try:
                action_taken = self._determine_action(selected_count, total_available, operacion)
                logger.info(f"Auto-determined action: {action_taken}")
            except ValueError as e:
                # Race condition - union became unavailable
                logger.error(f"Race condition detected: {e}")
                raise

            # Step 5.5: Check if metrología should trigger (after COMPLETAR determination)
            # Only check if action is COMPLETAR - PAUSAR means work is not done
            metrologia_triggered = False
            if action_taken == "COMPLETAR":
                try:
                    metrologia_triggered = self.should_trigger_metrologia(tag_spool)
                    logger.info(
                        f"Metrología trigger check for {tag_spool}: "
                        f"{'TRIGGERED' if metrologia_triggered else 'NOT TRIGGERED'}"
                    )
                except Exception as e:
                    logger.error(f"Failed to check metrología trigger for {tag_spool}: {e}")
                    # Don't block operation on metrología check failure
                    metrologia_triggered = False

            # Step 6: Process union selection through UnionService OR direct repository
            skip_metadata_logging = False
            pulgadas = 0.0  # Initialize for metadata logging

            try:
                if self.union_service:
                    # Parse Fecha_Ocupacion to get timestamp_inicio
                    if not spool.fecha_ocupacion:
                        logger.warning(f"Spool {tag_spool} missing Fecha_Ocupacion, using now() as fallback")
                        timestamp_inicio = now_chile()
                    else:
                        # Parse formato: "DD-MM-YYYY HH:MM:SS"
                        from datetime import datetime as dt
                        try:
                            timestamp_inicio = dt.strptime(spool.fecha_ocupacion, "%d-%m-%Y %H:%M:%S")
                            logger.info(f"Parsed Fecha_Ocupacion: {spool.fecha_ocupacion} → {timestamp_inicio}")
                        except ValueError as e:
                            logger.warning(f"Failed to parse Fecha_Ocupacion '{spool.fecha_ocupacion}': {e}, using now()")
                            timestamp_inicio = now_chile()

                    timestamp_fin = now_chile()

                    # Use UnionService for batch update + metadata logging
                    result = self.union_service.process_selection(
                        tag_spool=tag_spool,
                        union_ids=selected_unions,
                        worker_id=worker_id,
                        worker_nombre=worker_nombre,
                        operacion=operacion,
                        timestamp_inicio=timestamp_inicio,
                        timestamp_fin=timestamp_fin
                    )

                    updated_count = result["union_count"]
                    pulgadas = result.get("pulgadas", 0.0)
                    event_count = result.get("event_count", 0)

                    logger.info(
                        f"✅ UnionService processed: {updated_count} unions, "
                        f"{pulgadas} pulgadas, {event_count} metadata events"
                    )

                    # Skip manual metadata logging since UnionService handled it
                    skip_metadata_logging = True
                else:
                    # Direct UnionRepository with full timestamp support (P5 workflow)
                    # CRITICAL: timestamp_inicio from Fecha_Ocupacion, timestamp_fin from now()

                    # Parse Fecha_Ocupacion from spool
                    if not spool.fecha_ocupacion:
                        logger.warning(f"Spool {tag_spool} missing Fecha_Ocupacion, using now() as fallback")
                        timestamp_inicio = now_chile()
                    else:
                        # Parse formato: "DD-MM-YYYY HH:MM:SS"
                        from datetime import datetime as dt
                        try:
                            timestamp_inicio = dt.strptime(spool.fecha_ocupacion, "%d-%m-%Y %H:%M:%S")
                            logger.info(f"Parsed Fecha_Ocupacion: {spool.fecha_ocupacion} → {timestamp_inicio}")
                        except ValueError as e:
                            logger.warning(f"Failed to parse Fecha_Ocupacion '{spool.fecha_ocupacion}': {e}, using now()")
                            timestamp_inicio = now_chile()

                    timestamp_fin = now_chile()

                    if operacion == "ARM":
                        updated_count = self.union_repository.batch_update_arm_full(
                            tag_spool=tag_spool,
                            union_ids=selected_unions,
                            worker=worker_nombre,
                            timestamp_inicio=timestamp_inicio,  # From Fecha_Ocupacion
                            timestamp_fin=timestamp_fin          # Current time
                        )
                    elif operacion == "SOLD":
                        updated_count = self.union_repository.batch_update_sold_full(
                            tag_spool=tag_spool,
                            union_ids=selected_unions,
                            worker=worker_nombre,
                            timestamp_inicio=timestamp_inicio,  # From Fecha_Ocupacion
                            timestamp_fin=timestamp_fin          # Current time
                        )

                    # Calculate pulgadas for metadata
                    processed_unions = self.union_repository.get_by_ids(selected_unions)
                    pulgadas = sum([u.dn_union for u in processed_unions if u.dn_union])

                    logger.info(
                        f"✅ Batch update: {updated_count} unions updated in Uniones sheet, "
                        f"{pulgadas} pulgadas"
                    )
                    skip_metadata_logging = False

            except Exception as e:
                logger.error(f"Failed to process union selection: {e}")
                raise SheetsUpdateError(
                    f"Failed to update unions: {e}",
                    updates={"unions": selected_unions}
                )

            # Step 7: Clear occupation fields in Operaciones sheet
            # Build updates dict (varies by PAUSAR vs COMPLETAR)
            try:
                updates_dict = {
                    "Ocupado_Por": "",
                    "Fecha_Ocupacion": ""
                }

                # If COMPLETAR: add fecha_operacion + worker (NO v4.0 counters - managed by formulas)
                if action_taken == "COMPLETAR":
                    if operacion == "ARM":
                        updates_dict.update({
                            "Fecha_Armado": format_date_for_sheets(today_chile()),
                            "Armador": worker_nombre
                            # NOTE: Uniones_ARM_Completadas and Pulgadas_ARM are NOT written here
                            # These columns contain Google Sheets formulas that auto-calculate from Uniones sheet
                        })
                    elif operacion == "SOLD":
                        updates_dict.update({
                            "Fecha_Soldadura": format_date_for_sheets(today_chile()),
                            "Soldador": worker_nombre
                            # NOTE: Uniones_SOLD_Completadas and Pulgadas_SOLD are NOT written here
                            # These columns contain Google Sheets formulas that auto-calculate from Uniones sheet
                        })

                    updates_dict["Estado_Detalle"] = f"{operacion} completado - Disponible"
                else:  # PAUSAR
                    updates_dict["Estado_Detalle"] = f"{operacion} parcial (pausado)"

                # Use batch_update_by_column_name with automatic retry
                from backend.core.column_map_cache import ColumnMapCache
                from backend.config import config

                column_map = ColumnMapCache.get_or_build(config.HOJA_OPERACIONES_NOMBRE, self.sheets_repository)

                def normalize(name: str) -> str:
                    return name.lower().replace(" ", "").replace("_", "").replace("/", "")

                # Find TAG_SPOOL column
                tag_column_index = None
                for col_name in ["TAG_SPOOL", "SPLIT", "tag_spool"]:
                    normalized = normalize(col_name)
                    if normalized in column_map:
                        tag_column_index = column_map[normalized]
                        break

                if tag_column_index is None:
                    tag_column_index = 6  # Fallback

                column_letter = self.sheets_repository._index_to_column_letter(tag_column_index)
                row_num = self.sheets_repository.find_row_by_column_value(
                    sheet_name=config.HOJA_OPERACIONES_NOMBRE,
                    column_letter=column_letter,
                    value=tag_spool
                )

                if row_num is None:
                    raise SpoolNoEncontradoError(tag_spool)

                batch_updates = [
                    {"row": row_num, "column_name": key, "value": value}
                    for key, value in updates_dict.items()
                ]

                self.sheets_repository.batch_update_by_column_name(
                    sheet_name=config.HOJA_OPERACIONES_NOMBRE,
                    updates=batch_updates
                )

                logger.info(f"✅ Occupation cleared for {tag_spool} ({action_taken})")

            except Exception as e:
                logger.error(f"Failed to clear occupation: {e}")
                # Continue - unions already updated

            # Step 8: Log appropriate event to Metadata (only if not handled by UnionService)
            if not skip_metadata_logging:
                try:
                    if action_taken == "PAUSAR":
                        evento_tipo = EventoTipo.PAUSAR_SPOOL.value
                    elif action_taken == "COMPLETAR":
                        # Use operation-specific event type
                        evento_tipo_str = f"COMPLETAR_{operacion}"
                        try:
                            evento_tipo_enum = EventoTipo(evento_tipo_str)
                            evento_tipo = evento_tipo_enum.value
                        except ValueError:
                            evento_tipo = evento_tipo_str

                    metadata_json = json.dumps({
                        "unions_processed": updated_count,
                        "selected_unions": selected_unions,
                        "pulgadas": pulgadas  # ALWAYS include (both PAUSAR and COMPLETAR)
                    })

                    self.metadata_repository.log_event(
                        evento_tipo=evento_tipo,
                        tag_spool=tag_spool,
                        worker_id=worker_id,
                        worker_nombre=worker_nombre,
                        operacion=operacion,
                        accion=action_taken,
                        fecha_operacion=format_date_for_sheets(today_chile()),
                        metadata_json=metadata_json
                    )

                    logger.info(f"✅ Metadata logged: {evento_tipo} for {tag_spool}")

                except Exception as e:
                    logger.error(f"❌ CRITICAL: Metadata logging failed: {e}", exc_info=True)
            else:
                logger.info(f"✅ Metadata logging handled by UnionService (batch + granular events)")

            # Step 8.3: Trigger metrología auto-transition if flagged
            metrologia_new_state = None
            if metrologia_triggered:
                try:
                    # Import StateService to trigger transition
                    # Note: This creates a circular dependency, but it's acceptable for this use case
                    # Alternative: Inject StateService as optional dependency (future refactor)
                    from backend.services.state_service import StateService

                    # Create StateService instance with current dependencies
                    state_service = StateService(
                        occupation_service=self,
                        sheets_repository=self.sheets_repository,
                        metadata_repository=self.metadata_repository
                    )

                    # Trigger metrología transition
                    metrologia_new_state = await state_service.trigger_metrologia_transition(tag_spool)

                    if metrologia_new_state:
                        logger.info(
                            f"✅ Metrología auto-transition successful for {tag_spool}: "
                            f"state={metrologia_new_state}"
                        )

                        # Log METROLOGIA_AUTO_TRIGGERED event
                        try:
                            metrologia_metadata = json.dumps({
                                "trigger_reason": "all_work_complete",
                                "operacion_completed": operacion,
                                "unions_processed": updated_count,
                                "new_state": metrologia_new_state
                            })

                            self.metadata_repository.log_event(
                                evento_tipo=EventoTipo.METROLOGIA_AUTO_TRIGGERED.value,
                                tag_spool=tag_spool,
                                worker_id=worker_id,
                                worker_nombre=worker_nombre,
                                operacion=operacion,
                                accion="AUTO_TRIGGER",
                                fecha_operacion=format_date_for_sheets(today_chile()),
                                metadata_json=metrologia_metadata
                            )

                            logger.info(
                                f"✅ Metadata logged: METROLOGIA_AUTO_TRIGGERED for {tag_spool}"
                            )

                        except Exception as e:
                            logger.error(
                                f"❌ CRITICAL: Metrología metadata logging failed: {e}",
                                exc_info=True
                            )

                    else:
                        logger.warning(
                            f"Metrología auto-transition skipped for {tag_spool} "
                            f"(state machine rejected or already in queue)"
                        )

                except Exception as e:
                    logger.error(
                        f"Failed to trigger metrología auto-transition for {tag_spool}: {e}",
                        exc_info=True
                    )
                    # Don't block FINALIZAR operation on metrología trigger failure


            # Step 9: Return success response
            if action_taken == "COMPLETAR":
                message = f"Operación completada en {tag_spool} - {updated_count} uniones procesadas"
                # Add metrología notification if triggered
                if metrologia_triggered and metrologia_new_state:
                    message += " (Listo para metrología)"
            else:
                message = f"Trabajo pausado en {tag_spool} - {updated_count} uniones procesadas"

            logger.info(f"✅ FINALIZAR completed successfully: {message}")

            return OccupationResponse(
                success=True,
                tag_spool=tag_spool,
                message=message,
                action_taken=action_taken,
                unions_processed=updated_count,
                metrologia_triggered=metrologia_triggered if metrologia_triggered else None,
                new_state=metrologia_new_state if metrologia_new_state else None
            )

        except (SpoolNoEncontradoError, NoAutorizadoError, LockExpiredError, ValueError):
            raise
        except Exception as e:
            logger.error(f"❌ FINALIZAR operation failed: {e}")
            raise

    async def _finalizar_v30_spool(
        self,
        tag_spool: str,
        worker_id: int,
        worker_nombre: str,
        operacion: str,
        spool
    ) -> OccupationResponse:
        """
        Simplified FINALIZAR for v3.0 spools (no union tracking).

        v3.0 spools don't have union-level tracking, so they use all-or-nothing
        COMPLETAR logic (like the legacy completar endpoint).

        Flow:
        1. Update Fecha_Armado or Fecha_Soldadura based on operacion
        2. Clear Ocupado_Por and Fecha_Ocupacion
        3. Log COMPLETAR event to Metadata
        4. Return success with COMPLETAR action

        Args:
            tag_spool: Spool TAG identifier
            worker_id: Worker ID number
            worker_nombre: Worker name
            operacion: Operation type (ARM or SOLD)
            spool: Spool object from sheets

        Returns:
            OccupationResponse with success and COMPLETAR action
        """
        logger.info(f"[v3.0 FINALIZAR] Processing {tag_spool} for {operacion}")

        try:
            # Step 1: Build updates dict (clear occupation + update fecha)
            updates_dict = {
                "Ocupado_Por": "",
                "Fecha_Ocupacion": ""
            }

            # Add fecha column update based on operacion
            fecha_str = format_date_for_sheets(today_chile())
            if operacion == "ARM":
                updates_dict.update({
                    "Fecha_Armado": fecha_str,
                    "Armador": worker_nombre
                })
            elif operacion == "SOLD":
                updates_dict.update({
                    "Fecha_Soldadura": fecha_str,
                    "Soldador": worker_nombre
                })
            else:
                # Other operations (METROLOGIA, REPARACION, etc.)
                updates_dict[f"Fecha_{operacion}"] = fecha_str

            # Update Estado_Detalle
            updates_dict["Estado_Detalle"] = f"{operacion} completado - Disponible"

            # Step 2: Write to Operaciones sheet with batch update
            from backend.core.column_map_cache import ColumnMapCache
            from backend.config import config

            column_map = ColumnMapCache.get_or_build(
                config.HOJA_OPERACIONES_NOMBRE,
                self.sheets_repository
            )

            def normalize(name: str) -> str:
                return name.lower().replace(" ", "").replace("_", "").replace("/", "")

            # Find TAG_SPOOL column
            tag_column_index = None
            for col_name in ["TAG_SPOOL", "SPLIT", "tag_spool"]:
                normalized = normalize(col_name)
                if normalized in column_map:
                    tag_column_index = column_map[normalized]
                    break

            if tag_column_index is None:
                tag_column_index = 6  # Fallback

            column_letter = self.sheets_repository._index_to_column_letter(tag_column_index)
            row_num = self.sheets_repository.find_row_by_column_value(
                sheet_name=config.HOJA_OPERACIONES_NOMBRE,
                column_letter=column_letter,
                value=tag_spool
            )

            if row_num is None:
                raise SpoolNoEncontradoError(tag_spool)

            batch_updates = [
                {"row": row_num, "column_name": key, "value": value}
                for key, value in updates_dict.items()
            ]

            self.sheets_repository.batch_update_by_column_name(
                sheet_name=config.HOJA_OPERACIONES_NOMBRE,
                updates=batch_updates
            )

            logger.info(f"✅ Sheets updated for v3.0 spool {tag_spool}: {operacion} completado")

            # Step 3: Log COMPLETAR event to Metadata
            try:
                evento_tipo_str = f"COMPLETAR_{operacion}"
                try:
                    evento_tipo_enum = EventoTipo(evento_tipo_str)
                    evento_tipo = evento_tipo_enum.value
                except ValueError:
                    evento_tipo = evento_tipo_str

                metadata_json = json.dumps({
                    "fecha_operacion": fecha_str,
                    "completed": True,
                    "spool_version": "v3.0"
                })

                self.metadata_repository.log_event(
                    evento_tipo=evento_tipo,
                    tag_spool=tag_spool,
                    worker_id=worker_id,
                    worker_nombre=worker_nombre,
                    operacion=operacion,
                    accion="COMPLETAR",
                    fecha_operacion=format_date_for_sheets(today_chile()),
                    metadata_json=metadata_json
                )

                logger.info(f"✅ Metadata logged: {evento_tipo} for v3.0 spool {tag_spool}")

            except Exception as e:
                logger.error(f"❌ CRITICAL: Metadata logging failed: {e}", exc_info=True)

            # Step 4: Return success
            message = f"Operación completada en {tag_spool} (v3.0 spool - sin seguimiento de uniones)"
            logger.info(f"✅ [v3.0 FINALIZAR] Completed: {message}")

            return OccupationResponse(
                success=True,
                tag_spool=tag_spool,
                message=message,
                action_taken="COMPLETAR",
                unions_processed=0  # v3.0 spools don't track unions
            )

        except Exception as e:
            logger.error(f"❌ [v3.0 FINALIZAR] Failed for {tag_spool}: {e}", exc_info=True)
            raise
