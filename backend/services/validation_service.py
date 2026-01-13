"""
Servicio de validación de reglas de negocio para operaciones de manufactura.

v2.0 Event Sourcing:
- Estados ARM/SOLD se reconstruyen desde hoja Metadata (no desde Operaciones)
- ValidationService consulta MetadataRepository para obtener eventos
- Reconstruye estado actual (PENDIENTE/EN_PROGRESO/COMPLETADO) desde log de eventos
- Aplica reglas de negocio sobre estado reconstruido

Reglas críticas de negocio:
- Secuencia obligatoria: Materiales→Armado→Soldadura
- Transiciones de estado: PENDIENTE→EN_PROGRESO→COMPLETADO
- Restricción de propiedad: Solo quien inició puede completar
"""
import logging
from typing import Optional
from dataclasses import replace

from backend.models.spool import Spool
from backend.models.enums import ActionStatus, ActionType
from backend.models.metadata import EventoTipo, Accion
from backend.exceptions import (
    OperacionNoPendienteError,
    OperacionYaIniciadaError,
    OperacionYaCompletadaError,
    DependenciasNoSatisfechasError,
    OperacionNoIniciadaError,
    NoAutorizadoError,
    RolNoAutorizadoError  # v2.0: Validación de roles operativos
)

logger = logging.getLogger(__name__)


class ValidationService:
    """
    Servicio de validación de reglas de negocio (v2.0 Event Sourcing).

    Valida las condiciones necesarias para iniciar y completar operaciones
    de manufactura (ARM/SOLD) según las reglas de negocio del sistema ZEUES.

    v2.0: Reconstruye estados desde MetadataRepository antes de validar.
    """

    def __init__(self, metadata_repository=None, role_service=None):
        """
        Inicializa el servicio de validación con acceso a Metadata y roles (v2.0).

        Args:
            metadata_repository: Repositorio para consultar eventos (opcional para tests)
            role_service: Servicio para validar roles operativos (v2.0, opcional para tests)
        """
        self.metadata_repository = metadata_repository
        self.role_service = role_service  # v2.0: Validación de roles operativos

    def _reconstruir_estado_spool(self, spool: Spool) -> Spool:
        """
        Reconstruye el estado real de ARM/SOLD desde eventos en Metadata.

        v2.0: La hoja Operaciones es READ-ONLY, los estados vienen como PENDIENTE.
        Este método consulta Metadata y reconstruye el estado real.

        Args:
            spool: Spool con estados por defecto (PENDIENTE)

        Returns:
            Spool con estados reconstruidos (PENDIENTE/EN_PROGRESO/COMPLETADO)
        """
        if not self.metadata_repository:
            # Si no hay MetadataRepository, retornar spool sin modificar (para tests legacy)
            logger.warning("MetadataRepository no configurado, usando estados por defecto")
            return spool

        tag_spool = spool.tag_spool

        # Consultar eventos del spool
        events = self.metadata_repository.get_events_by_spool(tag_spool)

        # Reconstruir estado ARM
        arm_status = ActionStatus.PENDIENTE
        armador = None
        for event in events:
            if event.operacion == "ARM":
                if event.accion == Accion.INICIAR:
                    arm_status = ActionStatus.EN_PROGRESO
                    armador = event.worker_nombre
                elif event.accion == Accion.COMPLETAR:
                    arm_status = ActionStatus.COMPLETADO

        # Reconstruir estado SOLD
        sold_status = ActionStatus.PENDIENTE
        soldador = None
        for event in events:
            if event.operacion == "SOLD":
                if event.accion == Accion.INICIAR:
                    sold_status = ActionStatus.EN_PROGRESO
                    soldador = event.worker_nombre
                elif event.accion == Accion.COMPLETAR:
                    sold_status = ActionStatus.COMPLETADO

        logger.debug(
            f"Estado reconstruido para {tag_spool}: ARM={arm_status.value}, SOLD={sold_status.value}, "
            f"armador={armador}, soldador={soldador}"
        )

        # Crear nuevo Spool con estados reconstruidos
        # Nota: Spool es frozen, usamos replace de Pydantic
        return spool.model_copy(update={
            'arm': arm_status,
            'sold': sold_status,
            'armador': armador or spool.armador,  # Usar legacy si no hay en eventos
            'soldador': soldador or spool.soldador  # Usar legacy si no hay en eventos
        })

    def validar_puede_iniciar_arm(self, spool: Spool, worker_id: Optional[int] = None) -> None:
        """
        Valida si la operación ARM puede iniciarse en el spool.

        v2.0: Reconstruye estado desde Metadata antes de validar + validación de roles.

        Reglas de negocio:
        - ARM debe estar en estado PENDIENTE
        - fecha_materiales (AJ) debe estar llena
        - No debe haber evento INICIAR_ARM previo
        - Worker debe tener rol ARMADOR (v2.0) - solo si worker_id se proporciona

        Args:
            spool: Objeto Spool a validar
            worker_id: ID del trabajador que intenta iniciar (v2.0). Opcional para filtrado general.

        Raises:
            OperacionNoPendienteError: Si ARM no está en estado PENDIENTE
            DependenciasNoSatisfechasError: Si fecha_materiales está vacía
            RolNoAutorizadoError: Si worker no tiene rol ARMADOR (v2.0) - solo si worker_id se proporciona

        Logs:
            INFO: Inicio de validación
            DEBUG: Valores de dependencias
            ERROR: Fallos de validación con detalles
        """
        # v2.0: Reconstruir estado desde Metadata
        spool = self._reconstruir_estado_spool(spool)

        logger.info(f"Validating ARM start | Spool: {spool.tag_spool} | Worker: {worker_id} | Status: {spool.arm.value}")

        # Validar que ARM esté en estado PENDIENTE
        if spool.arm == ActionStatus.EN_PROGRESO:
            logger.error(
                f"ARM already started | Spool: {spool.tag_spool} | "
                f"Status: {spool.arm.value} | Armador: {spool.armador}"
            )
            raise OperacionYaIniciadaError(
                tag_spool=spool.tag_spool,
                operacion="ARM",
                trabajador=spool.armador
            )
        elif spool.arm == ActionStatus.COMPLETADO:
            logger.error(
                f"ARM already completed | Spool: {spool.tag_spool} | "
                f"Status: {spool.arm.value}"
            )
            raise OperacionYaCompletadaError(
                tag_spool=spool.tag_spool,
                operacion="ARM"
            )
        elif spool.arm != ActionStatus.PENDIENTE:
            logger.error(
                f"ARM not pending | Spool: {spool.tag_spool} | "
                f"Status: {spool.arm.value}"
            )
            raise OperacionNoPendienteError(
                tag_spool=spool.tag_spool,
                operacion="ARM",
                estado_actual=spool.arm.value
            )

        # Validar que fecha_materiales (BA) esté llena
        if spool.fecha_materiales is None:
            logger.error(
                f"Dependencies not met | Spool: {spool.tag_spool} | "
                f"BA (materiales): None"
            )
            raise DependenciasNoSatisfechasError(
                tag_spool=spool.tag_spool,
                operacion="ARM",
                dependencia_faltante="fecha_materiales (columna BA)",
                detalle="Los materiales deben estar registrados antes de iniciar el armado"
            )

        # Validar que fecha_armado (BB) esté vacía
        if spool.fecha_armado is not None:
            logger.error(
                f"Dependencies not met | Spool: {spool.tag_spool} | "
                f"BB (fecha_armado): {spool.fecha_armado}"
            )
            raise DependenciasNoSatisfechasError(
                tag_spool=spool.tag_spool,
                operacion="ARM",
                dependencia_faltante="fecha_armado debe estar vacía",
                detalle="El armado ya tiene fecha de finalización registrada"
            )

        # v2.0: Validar que worker tenga rol ARMADOR
        if self.role_service:
            self.role_service.validar_worker_tiene_rol_para_operacion(
                worker_id=worker_id,
                operacion="ARM"
            )
            logger.debug(f"Worker {worker_id} tiene rol ARMADOR - validación OK")
        else:
            logger.warning("RoleService no configurado, saltando validación de roles")

        logger.debug(
            f"ARM start validation passed | Spool: {spool.tag_spool} | "
            f"BA: {spool.fecha_materiales} | BB: None"
        )

    def validar_puede_completar_arm(self, spool: Spool, worker_nombre: str, worker_id: int) -> None:
        """
        Valida si la operación ARM puede completarse por el trabajador especificado.

        v2.0: Reconstruye estado desde Metadata antes de validar + validación de roles.

        Reglas de negocio:
        - ARM debe estar en estado EN_PROGRESO
        - worker_nombre debe coincidir con el que inició (de evento INICIAR_ARM)
        - RESTRICCIÓN CRÍTICA: Solo quien inició puede completar
        - Worker debe tener rol ARMADOR (v2.0)

        Args:
            spool: Objeto Spool a validar
            worker_nombre: Nombre del trabajador que intenta completar
            worker_id: ID del trabajador que intenta completar (v2.0)

        Raises:
            OperacionNoIniciadaError: Si ARM no está EN_PROGRESO
            NoAutorizadoError: Si worker_nombre != armador (CRÍTICO)
            RolNoAutorizadoError: Si worker no tiene rol ARMADOR (v2.0)

        Logs:
            INFO: Inicio de validación y verificación de propiedad
            DEBUG: Comparación de nombres
            ERROR: Fallos de autorización con detalles
        """
        # v2.0: Reconstruir estado desde Metadata
        spool = self._reconstruir_estado_spool(spool)

        logger.info(
            f"Validating ARM completion | Spool: {spool.tag_spool} | "
            f"Worker: {worker_nombre} | Status: {spool.arm.value}"
        )

        # Validar que ARM esté en estado EN_PROGRESO
        if spool.arm != ActionStatus.EN_PROGRESO:
            logger.error(
                f"ARM not in progress | Spool: {spool.tag_spool} | "
                f"Status: {spool.arm.value}"
            )
            raise OperacionNoIniciadaError(
                tag_spool=spool.tag_spool,
                operacion="ARM"
            )

        # CRÍTICO: Validar propiedad (ownership)
        # Normalizar nombres para comparación (case-insensitive, sin espacios)
        starter = spool.armador

        if starter is None or starter.strip() == "":
            logger.error(
                f"Ownership validation failed | Spool: {spool.tag_spool} | "
                f"No starter registered (BC is empty)"
            )
            raise NoAutorizadoError(
                tag_spool=spool.tag_spool,
                trabajador_esperado="DESCONOCIDO (BC vacío)",
                trabajador_solicitante=worker_nombre,
                operacion="ARM"
            )

        # Comparar nombres normalizados
        starter_normalized = starter.strip().lower()
        worker_normalized = worker_nombre.strip().lower()

        logger.info(
            f"Ownership validation | Spool: {spool.tag_spool} | "
            f"Expected: '{starter}' | Actual: '{worker_nombre}'"
        )

        if starter_normalized != worker_normalized:
            logger.error(
                f"Unauthorized completion attempt | Spool: {spool.tag_spool} | "
                f"Starter: {starter} | Requester: {worker_nombre}"
            )
            raise NoAutorizadoError(
                tag_spool=spool.tag_spool,
                trabajador_esperado=starter,
                trabajador_solicitante=worker_nombre,
                operacion="ARM"
            )

        # v2.0: Validar que worker tenga rol ARMADOR
        if self.role_service:
            self.role_service.validar_worker_tiene_rol_para_operacion(
                worker_id=worker_id,
                operacion="ARM"
            )
            logger.debug(f"Worker {worker_id} tiene rol ARMADOR - validación OK")
        else:
            logger.warning("RoleService no configurado, saltando validación de roles")

        logger.debug(
            f"ARM completion validation passed | Spool: {spool.tag_spool} | "
            f"Worker: {worker_nombre}"
        )

    def validar_puede_iniciar_sold(self, spool: Spool, worker_id: Optional[int] = None) -> None:
        """
        Valida si la operación SOLD puede iniciarse en el spool.

        v2.0: Reconstruye estado desde Metadata antes de validar + validación de roles.

        Reglas de negocio:
        - SOLD debe estar en estado PENDIENTE
        - Debe haber evento COMPLETAR_ARM previo (ARM completado)
        - No debe haber evento INICIAR_SOLD previo
        - Worker debe tener rol SOLDADOR (v2.0)

        Args:
            spool: Objeto Spool a validar
            worker_id: ID del trabajador que intenta iniciar (v2.0)

        Raises:
            OperacionNoPendienteError: Si SOLD no está en estado PENDIENTE
            DependenciasNoSatisfechasError: Si ARM no está completado
            RolNoAutorizadoError: Si worker no tiene rol SOLDADOR (v2.0)

        Logs:
            INFO: Inicio de validación
            DEBUG: Valores de dependencias
            ERROR: Fallos de validación con detalles
        """
        # v2.0: Reconstruir estado desde Metadata
        spool = self._reconstruir_estado_spool(spool)

        logger.info(
            f"Validating SOLD start | Spool: {spool.tag_spool} | "
            f"Status: {spool.sold.value}"
        )

        # Validar que SOLD esté en estado PENDIENTE
        if spool.sold == ActionStatus.EN_PROGRESO:
            logger.error(
                f"SOLD already started | Spool: {spool.tag_spool} | "
                f"Status: {spool.sold.value} | Soldador: {spool.soldador}"
            )
            raise OperacionYaIniciadaError(
                tag_spool=spool.tag_spool,
                operacion="SOLD",
                trabajador=spool.soldador
            )
        elif spool.sold == ActionStatus.COMPLETADO:
            logger.error(
                f"SOLD already completed | Spool: {spool.tag_spool} | "
                f"Status: {spool.sold.value}"
            )
            raise OperacionYaCompletadaError(
                tag_spool=spool.tag_spool,
                operacion="SOLD"
            )
        elif spool.sold != ActionStatus.PENDIENTE:
            logger.error(
                f"SOLD not pending | Spool: {spool.tag_spool} | "
                f"Status: {spool.sold.value}"
            )
            raise OperacionNoPendienteError(
                tag_spool=spool.tag_spool,
                operacion="SOLD",
                estado_actual=spool.sold.value
            )

        # Validar que fecha_armado (BB) esté llena (dependencia)
        if spool.fecha_armado is None:
            logger.error(
                f"Dependencies not met | Spool: {spool.tag_spool} | "
                f"BB (fecha_armado): None"
            )
            raise DependenciasNoSatisfechasError(
                tag_spool=spool.tag_spool,
                operacion="SOLD",
                dependencia_faltante="fecha_armado (columna BB)",
                detalle="El armado debe estar completado antes de iniciar la soldadura"
            )

        # Validar que fecha_soldadura (BD) esté vacía
        if spool.fecha_soldadura is not None:
            logger.error(
                f"Dependencies not met | Spool: {spool.tag_spool} | "
                f"BD (fecha_soldadura): {spool.fecha_soldadura}"
            )
            raise DependenciasNoSatisfechasError(
                tag_spool=spool.tag_spool,
                operacion="SOLD",
                dependencia_faltante="fecha_soldadura debe estar vacía",
                detalle="La soldadura ya tiene fecha de finalización registrada"
            )

        # v2.0: Validar que worker tenga rol SOLDADOR
        if self.role_service:
            self.role_service.validar_worker_tiene_rol_para_operacion(
                worker_id=worker_id,
                operacion="SOLD"
            )
            logger.debug(f"Worker {worker_id} tiene rol SOLDADOR - validación OK")
        else:
            logger.warning("RoleService no configurado, saltando validación de roles")

        logger.debug(
            f"SOLD start validation passed | Spool: {spool.tag_spool} | "
            f"BB: {spool.fecha_armado} | BD: None"
        )

    def validar_puede_completar_sold(self, spool: Spool, worker_nombre: str, worker_id: int) -> None:
        """
        Valida si la operación SOLD puede completarse por el trabajador especificado.

        v2.0: Reconstruye estado desde Metadata antes de validar + validación de roles.

        Reglas de negocio:
        - SOLD debe estar en estado EN_PROGRESO
        - worker_nombre debe coincidir con el que inició (de evento INICIAR_SOLD)
        - RESTRICCIÓN CRÍTICA: Solo quien inició puede completar
        - Worker debe tener rol SOLDADOR (v2.0)

        Args:
            spool: Objeto Spool a validar
            worker_nombre: Nombre del trabajador que intenta completar
            worker_id: ID del trabajador que intenta completar (v2.0)

        Raises:
            OperacionNoIniciadaError: Si SOLD no está EN_PROGRESO
            NoAutorizadoError: Si worker_nombre != soldador (CRÍTICO)
            RolNoAutorizadoError: Si worker no tiene rol SOLDADOR (v2.0)

        Logs:
            INFO: Inicio de validación y verificación de propiedad
            DEBUG: Comparación de nombres
            ERROR: Fallos de autorización con detalles
        """
        # v2.0: Reconstruir estado desde Metadata
        spool = self._reconstruir_estado_spool(spool)

        logger.info(
            f"Validating SOLD completion | Spool: {spool.tag_spool} | "
            f"Worker: {worker_nombre} | Status: {spool.sold.value}"
        )

        # Validar que SOLD esté en estado EN_PROGRESO
        if spool.sold != ActionStatus.EN_PROGRESO:
            logger.error(
                f"SOLD not in progress | Spool: {spool.tag_spool} | "
                f"Status: {spool.sold.value}"
            )
            raise OperacionNoIniciadaError(
                tag_spool=spool.tag_spool,
                operacion="SOLD"
            )

        # CRÍTICO: Validar propiedad (ownership)
        starter = spool.soldador

        if starter is None or starter.strip() == "":
            logger.error(
                f"Ownership validation failed | Spool: {spool.tag_spool} | "
                f"No starter registered (BE is empty)"
            )
            raise NoAutorizadoError(
                tag_spool=spool.tag_spool,
                trabajador_esperado="DESCONOCIDO (BE vacío)",
                trabajador_solicitante=worker_nombre,
                operacion="SOLD"
            )

        # Comparar nombres normalizados
        starter_normalized = starter.strip().lower()
        worker_normalized = worker_nombre.strip().lower()

        logger.info(
            f"Ownership validation | Spool: {spool.tag_spool} | "
            f"Expected: '{starter}' | Actual: '{worker_nombre}'"
        )

        if starter_normalized != worker_normalized:
            logger.error(
                f"Unauthorized completion attempt | Spool: {spool.tag_spool} | "
                f"Starter: {starter} | Requester: {worker_nombre}"
            )
            raise NoAutorizadoError(
                tag_spool=spool.tag_spool,
                trabajador_esperado=starter,
                trabajador_solicitante=worker_nombre,
                operacion="SOLD"
            )

        # v2.0: Validar que worker tenga rol SOLDADOR
        if self.role_service:
            self.role_service.validar_worker_tiene_rol_para_operacion(
                worker_id=worker_id,
                operacion="SOLD"
            )
            logger.debug(f"Worker {worker_id} tiene rol SOLDADOR - validación OK")
        else:
            logger.warning("RoleService no configurado, saltando validación de roles")

        logger.debug(
            f"SOLD completion validation passed | Spool: {spool.tag_spool} | "
            f"Worker: {worker_nombre}"
        )

    def validar_puede_cancelar(
        self,
        spool: Spool,
        operacion: str,
        worker_nombre: str,
        worker_id: int
    ) -> None:
        """
        Valida si una operación EN_PROGRESO puede ser cancelada (v2.0).

        CRÍTICO: Solo quien inició puede cancelar.
        Revierte estado EN_PROGRESO → PENDIENTE mediante evento CANCELAR.

        Reglas de negocio:
        - La operación debe estar en estado EN_PROGRESO
        - worker_nombre debe coincidir con quien inició (ownership)
        - Worker debe tener el rol necesario para la operación (v2.0)

        Args:
            spool: Objeto Spool a validar
            operacion: "ARM" o "SOLD"
            worker_nombre: Nombre del trabajador que intenta cancelar
            worker_id: ID del trabajador que intenta cancelar (v2.0)

        Raises:
            OperacionNoIniciadaError: Si operación no está EN_PROGRESO
            NoAutorizadoError: Si worker_nombre != quien inició (CRÍTICO)
            RolNoAutorizadoError: Si worker no tiene rol necesario (v2.0)
            ValueError: Si operación no es ARM o SOLD

        Examples:
            >>> # Worker 93 inició ARM, ahora intenta cancelar
            >>> service.validar_puede_cancelar(spool, "ARM", "Mauricio Rodriguez", 93)
            # OK - no lanza excepción

            >>> # Worker 94 intenta cancelar ARM iniciado por Worker 93
            >>> service.validar_puede_cancelar(spool, "ARM", "Carlos Pimiento", 94)
            # Lanza NoAutorizadoError
        """
        # v2.0: Reconstruir estado desde Metadata
        spool = self._reconstruir_estado_spool(spool)

        logger.info(
            f"Validating CANCELAR | Spool: {spool.tag_spool} | "
            f"Operacion: {operacion} | Worker: {worker_nombre}"
        )

        operacion_upper = operacion.upper()

        # Validar operación válida
        if operacion_upper not in ["ARM", "SOLD"]:
            raise ValueError(f"Operación '{operacion}' no soportada para CANCELAR. Solo ARM o SOLD.")

        # Obtener estado actual y worker que inició
        if operacion_upper == "ARM":
            estado_actual = spool.arm
            starter = spool.armador
            operacion_nombre = "ARM"
        else:  # SOLD
            estado_actual = spool.sold
            starter = spool.soldador
            operacion_nombre = "SOLD"

        # Validar que operación esté EN_PROGRESO
        if estado_actual != ActionStatus.EN_PROGRESO:
            logger.error(
                f"CANCELAR failed | Spool: {spool.tag_spool} | "
                f"{operacion_nombre} no está EN_PROGRESO (estado actual: {estado_actual.value})"
            )
            # Lanzar excepción según estado actual
            if estado_actual == ActionStatus.COMPLETADO:
                raise OperacionYaCompletadaError(
                    tag_spool=spool.tag_spool,
                    operacion=operacion_nombre
                )
            else:  # PENDIENTE o cualquier otro estado
                raise OperacionNoIniciadaError(
                    tag_spool=spool.tag_spool,
                    operacion=operacion_nombre
                )

        # CRÍTICO: Validar ownership (solo quien inició puede cancelar)
        if starter is None or starter.strip() == "":
            logger.error(
                f"Ownership validation failed | Spool: {spool.tag_spool} | "
                f"No starter registered (column empty)"
            )
            raise NoAutorizadoError(
                tag_spool=spool.tag_spool,
                trabajador_esperado="DESCONOCIDO (columna vacía)",
                trabajador_solicitante=worker_nombre,
                operacion=operacion_nombre
            )

        # Comparar nombres normalizados
        starter_normalized = starter.strip().lower()
        worker_normalized = worker_nombre.strip().lower()

        logger.info(
            f"Ownership validation for CANCELAR | Spool: {spool.tag_spool} | "
            f"Expected: '{starter}' | Actual: '{worker_nombre}'"
        )

        if starter_normalized != worker_normalized:
            logger.error(
                f"Unauthorized CANCELAR attempt | Spool: {spool.tag_spool} | "
                f"Starter: {starter} | Requester: {worker_nombre}"
            )
            raise NoAutorizadoError(
                tag_spool=spool.tag_spool,
                trabajador_esperado=starter,
                trabajador_solicitante=worker_nombre,
                operacion=operacion_nombre
            )

        # v2.0: Validar que worker tenga rol necesario
        if self.role_service:
            self.role_service.validar_worker_tiene_rol_para_operacion(
                worker_id=worker_id,
                operacion=operacion_nombre
            )
            logger.debug(f"Worker {worker_id} tiene rol necesario para CANCELAR {operacion_nombre} - validación OK")
        else:
            logger.warning("RoleService no configurado, saltando validación de roles")

        logger.debug(
            f"CANCELAR validation passed | Spool: {spool.tag_spool} | "
            f"Operacion: {operacion_nombre} | Worker: {worker_nombre}"
        )
