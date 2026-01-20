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
    RolNoAutorizadoError
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

    def __init__(self, role_service=None):
        self.role_service = role_service

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
        """Valida COMPLETAR ARM con ownership (v2.1 Direct Read)."""
        logger.info(f"[V2.1] Validating ARM completion | Spool: {spool.tag_spool} | Worker: {worker_nombre}")

        # 1. Validar NO completado primero (si ya completado, no está EN_PROGRESO)
        if spool.fecha_armado is not None:
            raise OperacionNoIniciadaError(tag_spool=spool.tag_spool, operacion="ARM")

        # 2. Validar que la operación fue iniciada (armador debe existir)
        if spool.armador is None:
            # v2.1: Si armador=None, la operación NO FUE INICIADA
            raise OperacionNoIniciadaError(tag_spool=spool.tag_spool, operacion="ARM")

        # 3. CRÍTICO: Ownership validation (armador debe coincidir con worker)
        if spool.armador.strip().lower() != worker_nombre.strip().lower():
            raise NoAutorizadoError(
                tag_spool=spool.tag_spool,
                trabajador_esperado=spool.armador,
                trabajador_solicitante=worker_nombre,
                operacion="ARM"
            )

        # Validar rol
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
        """Valida COMPLETAR SOLD con ownership (v2.1 Direct Read)."""
        logger.info(f"[V2.1] Validating SOLD completion | Spool: {spool.tag_spool} | Worker: {worker_nombre}")

        # 1. Validar NO completado primero (si ya completado, no está EN_PROGRESO)
        if spool.fecha_soldadura is not None:
            raise OperacionNoIniciadaError(tag_spool=spool.tag_spool, operacion="SOLD")

        # 2. Validar que la operación fue iniciada (soldador debe existir)
        if spool.soldador is None:
            # v2.1: Si soldador=None, la operación NO FUE INICIADA
            raise OperacionNoIniciadaError(tag_spool=spool.tag_spool, operacion="SOLD")

        # 3. CRÍTICO: Ownership validation (soldador debe coincidir con worker)
        if spool.soldador.strip().lower() != worker_nombre.strip().lower():
            raise NoAutorizadoError(
                tag_spool=spool.tag_spool,
                trabajador_esperado=spool.soldador,
                trabajador_solicitante=worker_nombre,
                operacion="SOLD"
            )

        # Validar rol
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
        """Valida CANCELAR acción EN_PROGRESO con ownership (v2.1 Direct Read)."""
        logger.info(f"[V2.1] Validating {operacion.value} cancellation | Spool: {spool.tag_spool}")

        if operacion == ActionType.ARM:
            # Validar ARM EN_PROGRESO
            if spool.armador is None:
                raise OperacionNoIniciadaError(tag_spool=spool.tag_spool, operacion="ARM")
            if spool.fecha_armado is not None:
                raise OperacionYaCompletadaError(tag_spool=spool.tag_spool, operacion="ARM")

            # Ownership
            if spool.armador.strip().lower() != worker_nombre.strip().lower():
                raise NoAutorizadoError(
                    tag_spool=spool.tag_spool,
                    trabajador_esperado=spool.armador,
                    trabajador_solicitante=worker_nombre,
                    operacion="ARM"
                )
        elif operacion == ActionType.SOLD:
            # Validar SOLD EN_PROGRESO
            if spool.soldador is None:
                raise OperacionNoIniciadaError(tag_spool=spool.tag_spool, operacion="SOLD")
            if spool.fecha_soldadura is not None:
                raise OperacionYaCompletadaError(tag_spool=spool.tag_spool, operacion="SOLD")

            # Ownership
            if spool.soldador.strip().lower() != worker_nombre.strip().lower():
                raise NoAutorizadoError(
                    tag_spool=spool.tag_spool,
                    trabajador_esperado=spool.soldador,
                    trabajador_solicitante=worker_nombre,
                    operacion="SOLD"
                )

        # Validar rol
        if self.role_service:
            self.role_service.validar_worker_tiene_rol_para_operacion(worker_id, operacion.value)

        logger.debug(f"[V2.1] ✅ {operacion.value} cancellation validation passed | {spool.tag_spool}")
