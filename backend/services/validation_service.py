"""
Servicio de validación de reglas de negocio para operaciones de manufactura.

Este servicio implementa la lógica pura de validación sin dependencias externas.
Enforces las reglas críticas de negocio:
- Secuencia obligatoria: BA→BB→BD (Materiales→Armado→Soldadura)
- Transiciones de estado: 0→0.1→1.0
- Restricción de propiedad: Solo quien inició puede completar
"""
import logging
from typing import Optional

from backend.models.spool import Spool
from backend.models.enums import ActionStatus, ActionType
from backend.exceptions import (
    OperacionNoPendienteError,
    OperacionYaIniciadaError,
    OperacionYaCompletadaError,
    DependenciasNoSatisfechasError,
    OperacionNoIniciadaError,
    NoAutorizadoError
)

logger = logging.getLogger(__name__)


class ValidationService:
    """
    Servicio de validación pura de reglas de negocio.

    Valida las condiciones necesarias para iniciar y completar operaciones
    de manufactura (ARM/SOLD) según las reglas de negocio del sistema ZEUES.

    Este servicio no tiene dependencias externas y realiza validación pura
    basada en el estado del objeto Spool.
    """

    def __init__(self):
        """Inicializa el servicio de validación sin dependencias."""
        pass

    def validar_puede_iniciar_arm(self, spool: Spool) -> None:
        """
        Valida si la operación ARM puede iniciarse en el spool.

        Reglas de negocio:
        - ARM debe estar en estado PENDIENTE (V=0)
        - Column BA (fecha_materiales) debe estar llena
        - Column BB (fecha_armado) debe estar vacía

        Args:
            spool: Objeto Spool a validar

        Raises:
            OperacionNoPendienteError: Si ARM no está en estado PENDIENTE
            DependenciasNoSatisfechasError: Si BA está vacía o BB está llena

        Logs:
            INFO: Inicio de validación
            DEBUG: Valores de dependencias
            ERROR: Fallos de validación con detalles
        """
        logger.info(f"Validating ARM start | Spool: {spool.tag_spool} | Status: {spool.arm.value}")

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

        logger.debug(
            f"ARM start validation passed | Spool: {spool.tag_spool} | "
            f"BA: {spool.fecha_materiales} | BB: None"
        )

    def validar_puede_completar_arm(self, spool: Spool, worker_nombre: str) -> None:
        """
        Valida si la operación ARM puede completarse por el trabajador especificado.

        Reglas de negocio:
        - ARM debe estar en estado EN_PROGRESO (V=0.1)
        - Column BC (armador) debe coincidir con worker_nombre
        - RESTRICCIÓN CRÍTICA: Solo quien inició puede completar

        Args:
            spool: Objeto Spool a validar
            worker_nombre: Nombre del trabajador que intenta completar

        Raises:
            OperacionNoIniciadaError: Si ARM no está EN_PROGRESO
            NoAutorizadoError: Si worker_nombre != armador (CRÍTICO)

        Logs:
            INFO: Inicio de validación y verificación de propiedad
            DEBUG: Comparación de nombres
            ERROR: Fallos de autorización con detalles
        """
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

        logger.debug(
            f"ARM completion validation passed | Spool: {spool.tag_spool} | "
            f"Worker: {worker_nombre}"
        )

    def validar_puede_iniciar_sold(self, spool: Spool) -> None:
        """
        Valida si la operación SOLD puede iniciarse en el spool.

        Reglas de negocio:
        - SOLD debe estar en estado PENDIENTE (W=0)
        - Column BB (fecha_armado) debe estar llena (dependencia)
        - Column BD (fecha_soldadura) debe estar vacía

        Args:
            spool: Objeto Spool a validar

        Raises:
            OperacionNoPendienteError: Si SOLD no está en estado PENDIENTE
            DependenciasNoSatisfechasError: Si BB está vacía o BD está llena

        Logs:
            INFO: Inicio de validación
            DEBUG: Valores de dependencias
            ERROR: Fallos de validación con detalles
        """
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

        logger.debug(
            f"SOLD start validation passed | Spool: {spool.tag_spool} | "
            f"BB: {spool.fecha_armado} | BD: None"
        )

    def validar_puede_completar_sold(self, spool: Spool, worker_nombre: str) -> None:
        """
        Valida si la operación SOLD puede completarse por el trabajador especificado.

        Reglas de negocio:
        - SOLD debe estar en estado EN_PROGRESO (W=0.1)
        - Column BE (soldador) debe coincidir con worker_nombre
        - RESTRICCIÓN CRÍTICA: Solo quien inició puede completar

        Args:
            spool: Objeto Spool a validar
            worker_nombre: Nombre del trabajador que intenta completar

        Raises:
            OperacionNoIniciadaError: Si SOLD no está EN_PROGRESO
            NoAutorizadoError: Si worker_nombre != soldador (CRÍTICO)

        Logs:
            INFO: Inicio de validación y verificación de propiedad
            DEBUG: Comparación de nombres
            ERROR: Fallos de autorización con detalles
        """
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

        logger.debug(
            f"SOLD completion validation passed | Spool: {spool.tag_spool} | "
            f"Worker: {worker_nombre}"
        )
