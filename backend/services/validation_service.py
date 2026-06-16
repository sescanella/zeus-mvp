"""
Servicio de validación de reglas de negocio v2.1 (Direct Read).

Este archivo reemplaza validation_service.py con lógica Direct Read.
Estados se leen directamente desde columnas de Operaciones.
"""
import logging
from typing import Optional

from backend.models.spool import Spool
from backend.models.enums import ActionType
from backend.exceptions import (
    OperacionYaIniciadaError,
    OperacionYaCompletadaError,
    DependenciasNoSatisfechasError,
    OperacionNoIniciadaError,
    NoAutorizadoError,
    RolNoAutorizadoError,
    OperacionNoDisponibleError,
    ArmPrerequisiteError
)

logger = logging.getLogger(__name__)


class ValidationService:
    """
    Servicio de validación v2.1 Direct Read.

    Lee estados directamente desde columnas:
    - ARM PENDIENTE: armador = None
    - ARM EN_PROGRESO: armador != None AND fecha_armado = None
    - ARM COMPLETADO: fecha_armado != None
    """

    def __init__(self, role_service=None, union_repository=None):
        self.role_service = role_service
        self.union_repository = union_repository

    def validar_puede_iniciar_arm(self, spool: Spool, worker_id: Optional[int] = None) -> None:
        """Valida INICIAR ARM (v2.1 Direct Read)."""
        logger.info(f"[V2.1] Validating ARM start | Spool: {spool.tag_spool}")

        # 1. Validar prerequisito positivo (fecha_materiales llena)
        if spool.fecha_materiales is None:
            raise DependenciasNoSatisfechasError(
                tag_spool=spool.tag_spool,
                operacion="ARM",
                dependencia_faltante="fecha_materiales",
                detalle="Los materiales deben estar registrados"
            )

        # 2. Validar estado: si fecha_armado está llena, distinguir entre completado y corrupción
        if spool.fecha_armado is not None:
            if spool.armador is not None:
                # Caso A: Propiamente completado (armador Y fecha_armado llenos)
                raise OperacionYaCompletadaError(tag_spool=spool.tag_spool, operacion="ARM")
            else:
                # Caso B: Data inconsistency (fecha llena pero armador vacío)
                raise DependenciasNoSatisfechasError(
                    tag_spool=spool.tag_spool,
                    operacion="ARM",
                    dependencia_faltante="fecha_armado debe estar vacía",
                    detalle="No se puede iniciar ARM si ya hay fecha de armado registrada"
                )

        # 3. Validar ARM PENDIENTE (armador vacío)
        if spool.armador is not None:
            raise OperacionYaIniciadaError(tag_spool=spool.tag_spool, operacion="ARM", trabajador=spool.armador)

        # Validar rol
        if self.role_service and worker_id is not None:
            self.role_service.validar_worker_tiene_rol_para_operacion(worker_id, "ARM")

        logger.debug(f"[V2.1] ✅ ARM start validation passed | {spool.tag_spool}")

    def validar_puede_completar_arm(self, spool: Spool, worker_nombre: str, worker_id: int) -> None:
        """Valida COMPLETAR ARM (v2.1 Direct Read - sin restricción de ownership)."""
        logger.info(f"[V2.1] Validating ARM completion | Spool: {spool.tag_spool} | Worker: {worker_nombre}")

        # 1. Validar NO completado primero (si ya completado, no está EN_PROGRESO)
        if spool.fecha_armado is not None:
            raise OperacionNoIniciadaError(tag_spool=spool.tag_spool, operacion="ARM")

        # 2. Validar que la operación fue iniciada (armador debe existir)
        if spool.armador is None:
            # v2.1: Si armador=None, la operación NO FUE INICIADA
            raise OperacionNoIniciadaError(tag_spool=spool.tag_spool, operacion="ARM")

        # 3. Validar rol (cualquier trabajador con rol Armador puede completar)
        if self.role_service:
            self.role_service.validar_worker_tiene_rol_para_operacion(worker_id, "ARM")

        logger.debug(f"[V2.1] ✅ ARM completion validation passed | {spool.tag_spool}")

    def validar_puede_iniciar_sold(self, spool: Spool, worker_id: Optional[int] = None) -> None:
        """Valida INICIAR SOLD (v2.1 Direct Read)."""
        logger.info(f"[V2.1] Validating SOLD start | Spool: {spool.tag_spool}")

        # 1. Validar prerequisito positivo ARM COMPLETADO (fecha_armado llena)
        if spool.fecha_armado is None:
            raise DependenciasNoSatisfechasError(
                tag_spool=spool.tag_spool,
                operacion="SOLD",
                dependencia_faltante="fecha_armado (ARM debe completarse primero)",
                detalle="ARM debe estar completado antes de iniciar SOLD"
            )

        # 2. Validar estado: si fecha_soldadura está llena, distinguir entre completado y corrupción
        if spool.fecha_soldadura is not None:
            if spool.soldador is not None:
                # Caso A: Propiamente completado (soldador Y fecha_soldadura llenos)
                raise OperacionYaCompletadaError(tag_spool=spool.tag_spool, operacion="SOLD")
            else:
                # Caso B: Data inconsistency (fecha llena pero soldador vacío)
                raise DependenciasNoSatisfechasError(
                    tag_spool=spool.tag_spool,
                    operacion="SOLD",
                    dependencia_faltante="fecha_soldadura debe estar vacía",
                    detalle="No se puede iniciar SOLD si ya hay fecha de soldadura registrada"
                )

        # 3. Validar SOLD PENDIENTE (soldador vacío)
        if spool.soldador is not None:
            raise OperacionYaIniciadaError(tag_spool=spool.tag_spool, operacion="SOLD", trabajador=spool.soldador)

        # Validar rol
        if self.role_service and worker_id is not None:
            self.role_service.validar_worker_tiene_rol_para_operacion(worker_id, "SOLD")

        logger.debug(f"[V2.1] ✅ SOLD start validation passed | {spool.tag_spool}")

    def validar_puede_completar_sold(self, spool: Spool, worker_nombre: str, worker_id: int) -> None:
        """Valida COMPLETAR SOLD (v2.1 Direct Read - sin restricción de ownership)."""
        logger.info(f"[V2.1] Validating SOLD completion | Spool: {spool.tag_spool} | Worker: {worker_nombre}")

        # 1. Validar NO completado primero (si ya completado, no está EN_PROGRESO)
        if spool.fecha_soldadura is not None:
            raise OperacionNoIniciadaError(tag_spool=spool.tag_spool, operacion="SOLD")

        # 2. Validar que la operación fue iniciada (soldador debe existir)
        if spool.soldador is None:
            # v2.1: Si soldador=None, la operación NO FUE INICIADA
            raise OperacionNoIniciadaError(tag_spool=spool.tag_spool, operacion="SOLD")

        # 3. Validar rol (cualquier trabajador con rol Soldador puede completar)
        if self.role_service:
            self.role_service.validar_worker_tiene_rol_para_operacion(worker_id, "SOLD")

        logger.debug(f"[V2.1] ✅ SOLD completion validation passed | {spool.tag_spool}")

    def validar_puede_cancelar(
        self,
        spool: Spool,
        operacion: ActionType,
        worker_nombre: str,
        worker_id: int
    ) -> None:
        """Valida CANCELAR acción EN_PROGRESO (v2.1 Direct Read - sin restricción de ownership)."""
        logger.info(f"[V2.1] Validating {operacion.value} cancellation | Spool: {spool.tag_spool}")

        if operacion == ActionType.ARM:
            # Validar ARM EN_PROGRESO
            if spool.armador is None:
                raise OperacionNoIniciadaError(tag_spool=spool.tag_spool, operacion="ARM")
            if spool.fecha_armado is not None:
                raise OperacionYaCompletadaError(tag_spool=spool.tag_spool, operacion="ARM")

        elif operacion == ActionType.SOLD:
            # Validar SOLD EN_PROGRESO
            if spool.soldador is None:
                raise OperacionNoIniciadaError(tag_spool=spool.tag_spool, operacion="SOLD")
            if spool.fecha_soldadura is not None:
                raise OperacionYaCompletadaError(tag_spool=spool.tag_spool, operacion="SOLD")

        elif operacion == ActionType.METROLOGIA:
            # METROLOGIA: Solo hay estado COMPLETADO (fecha_qc_metrologia llena)
            # CANCELAR revierte COMPLETADO → PENDIENTE
            if spool.fecha_qc_metrologia is None:
                raise OperacionNoIniciadaError(tag_spool=spool.tag_spool, operacion="METROLOGIA")

        # Validar rol (cualquier trabajador con el rol correcto puede cancelar)
        if self.role_service:
            self.role_service.validar_worker_tiene_rol_para_operacion(worker_id, operacion.value)

        logger.debug(f"[V2.1] ✅ {operacion.value} cancellation validation passed | {spool.tag_spool}")

    def validar_puede_completar_metrologia(self, spool: Spool, worker_id: int) -> None:
        """
        Valida COMPLETAR METROLOGIA (v3.0 instant completion - no TOMAR phase).

        Prerequisites (ALL must be true):
        - ARM completado (fecha_armado != None)
        - SOLD completado (fecha_soldadura != None)
        - METROLOGIA no completada (fecha_qc_metrologia == None)
        - Spool NO ocupado (ocupado_por == None) - prevents race conditions

        Args:
            spool: Spool to validate
            worker_id: ID of worker attempting inspection

        Raises:
            DependenciasNoSatisfechasError: If ARM or SOLD not completed
            OperacionYaCompletadaError: If metrología already completed
            SpoolOccupiedError: If spool currently occupied by another worker
            RolNoAutorizadoError: If worker lacks METROLOGIA role
        """
        logger.info(f"[V3.0] Validating METROLOGIA completion | Spool: {spool.tag_spool} | Worker: {worker_id}")

        # Import here to avoid circular dependency
        from backend.exceptions import SpoolOccupiedError

        # 1. Check ARM completed (prerequisite) — with per-union fallback when
        #    Fecha_Armado is stale.
        #
        # Background: a small set of legacy/edge spools have all unions ARM-
        # completed (every Uniones.ARM_FECHA_FIN populated, counters > 0,
        # workers stamped) yet Operaciones.Fecha_Armado / Armador remain
        # empty. Two confirmed cases on 2026-05-08 (MK-1344-GW-27133-009 and
        # MK-1344-TW-27121-004) blocked metrología entry even though ARM was
        # really done at the union level. Root cause is in the write path:
        # OccupationService.finalizar_spool only writes the v2.1 columns
        # when action_taken=="COMPLETAR" (occupation_service.py:1602-1606).
        # If the operation took the PAUSAR branch (e.g. T-021 guard fired or
        # total_uniones was corrupted as an Excel-date and skipped the
        # numerical compare), the v2.1 columns stay empty.
        #
        # Read-side guard: if Fecha_Armado is empty, consult union_repository
        # before raising. If every union has ARM_FECHA_FIN set, accept ARM
        # as completed. Use distinctive log markers ([ARM_FALLBACK_OK] /
        # [ARM_FALLBACK_FAILED]) so this code path can be greppable in
        # Railway logs. Mirrors the SOLD H2 guard pattern below.
        if spool.fecha_armado is None:
            arm_completed_via_unions = False
            if self.union_repository is not None:
                tag_unions = None
                try:
                    tag_unions = self.union_repository.get_by_spool(spool.tag_spool)
                except Exception as e:
                    logger.warning(
                        f"[ARM_FALLBACK_FAILED] get_by_spool({spool.tag_spool}) raised "
                        f"{type(e).__name__}: {e}. Falling back to strict Fecha_Armado check."
                    )
                    tag_unions = None

                if isinstance(tag_unions, list) and len(tag_unions) > 0:
                    arm_pending = [u for u in tag_unions if u.arm_fecha_fin is None]
                    if not arm_pending:
                        arm_completed_via_unions = True
                        logger.info(
                            f"[ARM_FALLBACK_OK] {spool.tag_spool}: Fecha_Armado empty "
                            f"but all {len(tag_unions)} unions have ARM_FECHA_FIN set. "
                            f"Allowing metrología entry."
                        )

            if not arm_completed_via_unions:
                raise DependenciasNoSatisfechasError(
                    tag_spool=spool.tag_spool,
                    operacion="METROLOGIA",
                    dependencia_faltante="ARM completado",
                    detalle="Armado debe finalizar antes de metrología"
                )

        # 2. Check SOLD completed (prerequisite)
        if spool.fecha_soldadura is None:
            raise DependenciasNoSatisfechasError(
                tag_spool=spool.tag_spool,
                operacion="METROLOGIA",
                dependencia_faltante="SOLD completado",
                detalle="Soldadura debe finalizar antes de metrología"
            )

        # 2b. T-096 H2 hardening (second line of defense against partial SOLD
        # sneaking into metrología).
        #
        # Scope of this guard (validated empirically against production Sheet
        # on 2026-04-21 via backend/scripts/diagnose_H2_guard_impact.py):
        #
        #   - SOLD always hard-checked: if any SOLD-required union has
        #     sol_fecha_fin=None, metrología is blocked. Mirrors Matías's
        #     business rule "SOLD TERM = all unions soldered"
        #     (v5.1-scope.md § Máquina de estados).
        #   - ARM conditionally checked: only when at least one union of the
        #     spool has arm_fecha_fin set. If every arm_fecha_fin is None the
        #     spool was armed at the spool level (v2.1/v3.0 legacy style),
        #     and a per-unit ARM check would be a regression. Observed in
        #     production: MK-1343-MO-26627-016. The conditional check still
        #     catches the manual-edit scenario: someone who edited
        #     Fecha_Soldadura on a row whose ARM is tracked but not all
        #     unions have arm_fecha_fin — that is exactly the pattern the
        #     conditional check blocks.
        #   - If union_repository is unavailable or errors, the guard SKIPS
        #     rather than blocks. The guard is defense-in-depth; the primary
        #     protection is the write-side fix in occupation_service. A
        #     distinctive log prefix ([H2_GUARD_FAILED]) is used so failures
        #     can be grepped from Railway logs for post-facto audit.
        #
        # Import locally to avoid circular imports with occupation_service.
        if self.union_repository is not None:
            tag_unions = None
            try:
                from backend.services.occupation_service import SOLD_REQUIRED_TYPES
                tag_unions = self.union_repository.get_by_spool(spool.tag_spool)
            except Exception as e:
                logger.warning(
                    f"[H2_GUARD_FAILED] get_by_spool({spool.tag_spool}) raised "
                    f"{type(e).__name__}: {e}. Allowing metrología entry based "
                    f"on the primary Fecha_Soldadura check. Review Railway logs "
                    f"with grep '[H2_GUARD_FAILED]' if partial-SOLD corruption "
                    f"reappears."
                )
            else:
                if not isinstance(tag_unions, list):
                    logger.warning(
                        f"[H2_GUARD_FAILED] get_by_spool({spool.tag_spool}) "
                        f"returned non-list {type(tag_unions).__name__}. "
                        f"Allowing metrología entry; see Railway logs for audit."
                    )
                    tag_unions = None

            if isinstance(tag_unions, list) and len(tag_unions) > 0:
                sold_required = [
                    u for u in tag_unions if u.tipo_union in SOLD_REQUIRED_TYPES
                ]
                sold_pending = [u for u in sold_required if u.sol_fecha_fin is None]

                if sold_pending:
                    logger.warning(
                        f"[H2_GUARD_TRIGGERED] Blocking METROLOGIA for "
                        f"{spool.tag_spool}: Fecha_Soldadura is set but "
                        f"{len(sold_pending)} of {len(sold_required)} "
                        f"SOLD-required unions are pending."
                    )
                    raise DependenciasNoSatisfechasError(
                        tag_spool=spool.tag_spool,
                        operacion="METROLOGIA",
                        dependencia_faltante="SOLD completado en todas las uniones",
                        detalle=(
                            f"Quedan {len(sold_pending)} uniones sin soldar "
                            f"(de {len(sold_required)} requeridas)"
                        ),
                    )

                # ARM check is conditional to avoid the MK-1343 regression:
                # only enforce it when at least one union is ARM-tracked (has
                # arm_fecha_fin set). If every union has arm_fecha_fin=None
                # the spool was armed at the spool level (v2.1/v3.0 legacy
                # style), and per-unit ARM completeness is not meaningful.
                any_arm_tracked = any(u.arm_fecha_fin is not None for u in tag_unions)
                if any_arm_tracked:
                    arm_pending = [u for u in tag_unions if u.arm_fecha_fin is None]
                    if arm_pending:
                        logger.warning(
                            f"[H2_GUARD_TRIGGERED] Blocking METROLOGIA for "
                            f"{spool.tag_spool}: spool is ARM-tracked at union "
                            f"level but {len(arm_pending)} unions are pending "
                            f"ARM. This indicates a manually edited or partially "
                            f"completed spool."
                        )
                        raise DependenciasNoSatisfechasError(
                            tag_spool=spool.tag_spool,
                            operacion="METROLOGIA",
                            dependencia_faltante="ARM completado en todas las uniones",
                            detalle=(
                                f"Quedan {len(arm_pending)} uniones sin armar"
                            ),
                        )

        # 3. Check NOT already completed (APROBADO)
        if spool.fecha_qc_metrologia is not None:
            raise OperacionYaCompletadaError(
                tag_spool=spool.tag_spool,
                operacion="METROLOGIA"
            )

        # 3b. Check NOT RECHAZADO (needs reparación, not re-inspection)
        estado = spool.estado_detalle or ""
        if "RECHAZADO" in estado:
            raise OperacionYaCompletadaError(
                tag_spool=spool.tag_spool,
                operacion="METROLOGIA"
            )

        # 4. Check NOT occupied (CRITICAL for race condition prevention)
        # Occupied spools cannot be inspected - worker might be actively modifying
        if spool.ocupado_por is not None:
            # Extract worker ID and name from ocupado_por format "INICIALES(ID)"
            # Example: "MR(93)" -> ID: 93, Name: "MR(93)"
            try:
                owner_name = spool.ocupado_por
                # Extract ID from format "XX(ID)"
                owner_id = int(spool.ocupado_por.split('(')[1].rstrip(')'))
            except (IndexError, ValueError):
                # Fallback if format is unexpected
                owner_id = 0
                owner_name = spool.ocupado_por

            raise SpoolOccupiedError(
                tag_spool=spool.tag_spool,
                owner_id=owner_id,
                owner_name=owner_name
            )

        # 5. Validar rol (worker must have METROLOGIA role)
        if self.role_service:
            self.role_service.validar_worker_tiene_rol_para_operacion(worker_id, "METROLOGIA")

        logger.debug(f"[V3.0] ✅ METROLOGIA completion validation passed | {spool.tag_spool}")

    def validar_puede_tomar_reparacion(self, spool: Spool, worker_id: int) -> None:
        """
        Validate worker can TOMAR spool for reparación (Phase 6).

        Prerequisites (ALL must be true):
        - Estado_Detalle contains "RECHAZADO" or "REPARACION_PAUSADA"
        - Spool NOT occupied (ocupado_por == None)
        - Worker has appropriate role (no role restriction per user decision)

        Args:
            spool: Spool to validate
            worker_id: ID of worker attempting to take spool for repair

        Raises:
            OperacionNoDisponibleError: If spool not RECHAZADO
            SpoolOccupiedError: If spool currently occupied
        """
        logger.info(f"[V3.0 Phase 6] Validating REPARACION TOMAR | Spool: {spool.tag_spool} | Worker: {worker_id}")

        # Import here to avoid circular dependency
        from backend.exceptions import SpoolOccupiedError

        # 1. Check RECHAZADO or REPARACION_PAUSADA (can repair rejected or resume paused repair)
        if not spool.estado_detalle or (
            "RECHAZADO" not in spool.estado_detalle and "REPARACION_PAUSADA" not in spool.estado_detalle
        ):
            raise OperacionNoDisponibleError(
                tag_spool=spool.tag_spool,
                operacion="REPARACION",
                mensaje="Solo spools RECHAZADOS o REPARACION_PAUSADA pueden ser reparados"
            )

        # 2. Check NOT occupied
        if spool.ocupado_por is not None:
            # Extract worker ID and name from ocupado_por format "INICIALES(ID)"
            try:
                owner_name = spool.ocupado_por
                owner_id = int(spool.ocupado_por.split('(')[1].rstrip(')'))
            except (IndexError, ValueError):
                owner_id = 0
                owner_name = spool.ocupado_por

            raise SpoolOccupiedError(
                tag_spool=spool.tag_spool,
                owner_id=owner_id,
                owner_name=owner_name
            )

        # 3. No role restriction for REPARACION per user decision
        # Any active worker can repair (no specific role check needed)

        logger.debug(f"[V3.0 Phase 6] ✅ REPARACION TOMAR validation passed | {spool.tag_spool}")

    def validar_puede_cancelar_reparacion(
        self,
        spool: Spool,
        worker_nombre: str,
        worker_id: int
    ) -> None:
        """
        Validate worker can CANCELAR reparación (Phase 6).

        Prerequisites:
        - Estado_Detalle contains "EN_REPARACION" or "REPARACION_PAUSADA"

        Args:
            spool: Spool to validate
            worker_nombre: Name of worker attempting to cancel
            worker_id: ID of worker attempting to cancel

        Raises:
            OperacionNoIniciadaError: If reparación not in progress
        """
        logger.info(f"[V3.0 Phase 6] Validating REPARACION CANCELAR | Spool: {spool.tag_spool} | Worker: {worker_nombre}")

        # Check if EN_REPARACION or REPARACION_PAUSADA
        if not spool.estado_detalle or (
            "EN_REPARACION" not in spool.estado_detalle and
            "REPARACION_PAUSADA" not in spool.estado_detalle
        ):
            raise OperacionNoIniciadaError(
                tag_spool=spool.tag_spool,
                operacion="REPARACION"
            )

        # No ownership check for CANCELAR per existing pattern
        # Any worker with appropriate role can cancel

        logger.debug(f"[V3.0 Phase 6] ✅ REPARACION CANCELAR validation passed | {spool.tag_spool}")

    def validate_arm_prerequisite(self, tag_spool: str, ot: str) -> dict:
        """
        Validate ARM prerequisite for SOLD operation (v4.0).

        Business rule: SOLD operations require at least one union with ARM_FECHA_FIN != NULL.
        This validation occurs at INICIAR time to fail early with clear feedback.

        Args:
            tag_spool: Spool identifier for error messaging
            ot: Work order number to query unions

        Returns:
            dict: Validation result with unions_armadas count
                  e.g., {"valid": True, "unions_armadas": 5}

        Raises:
            ArmPrerequisiteError: If no ARM unions completed
            ValueError: If union_repository not configured
        """
        logger.info(f"[V4.0] Validating ARM prerequisite for SOLD | Spool: {tag_spool} | OT: {ot}")

        if self.union_repository is None:
            raise ValueError("UnionRepository not configured for ARM prerequisite validation")

        # Query all unions for this OT
        all_unions = self.union_repository.get_by_ot(ot)

        # Count unions with ARM_FECHA_FIN != NULL
        unions_armadas = sum(1 for u in all_unions if u.arm_fecha_fin is not None)
        unions_sin_armar = len(all_unions) - unions_armadas

        logger.debug(
            f"ARM prerequisite check: {unions_armadas} completed, "
            f"{unions_sin_armar} pending for OT {ot}"
        )

        # Raise error if no ARM unions completed
        if unions_armadas == 0:
            raise ArmPrerequisiteError(
                tag_spool=tag_spool,
                unions_sin_armar=unions_sin_armar
            )

        logger.debug(f"[V4.0] ✅ ARM prerequisite validation passed | {unions_armadas} ARM unions completed")

        return {
            "valid": True,
            "unions_armadas": unions_armadas
        }
