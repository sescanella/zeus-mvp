"""
ActionService - Orquestador de acciones de manufactura.

Responsabilidades:
- Coordinar flujos INICIAR/COMPLETAR
- Validar ownership (solo quien inició puede completar)
- Actualizar Google Sheets en batch
- Invalidar cache
- Logging comprehensivo

Dependencias:
- SheetsRepository: Actualización batch de celdas
- SheetsService: Re-fetch después de updates
- ValidationService: Validación ownership + estados
- SpoolService: Búsqueda por TAG
- WorkerService: Búsqueda por nombre
"""

import logging
from typing import Optional
from datetime import datetime

from backend.repositories.sheets_repository import SheetsRepository
from backend.services.sheets_service import SheetsService
from backend.services.validation_service import ValidationService
from backend.services.spool_service import SpoolService
from backend.services.worker_service import WorkerService

from backend.models.enums import ActionType
from backend.models.action import ActionRequest, ActionResponse, ActionData, ActionMetadata
from backend.models.spool import Spool
from backend.models.worker import Worker
from backend.config import config

from backend.exceptions import (
    WorkerNoEncontradoError,
    SpoolNoEncontradoError,
    OperacionNoPendienteError,
    OperacionYaIniciadaError,
    OperacionNoIniciadaError,
    OperacionYaCompletadaError,
    DependenciasNoSatisfechasError,
    NoAutorizadoError,
    SheetsUpdateError
)

logger = logging.getLogger(__name__)


class ActionService:
    """Servicio de orquestación de acciones de manufactura."""

    # Mapeo de columnas (constantes de clase)
    COLUMN_MAPPING = {
        ActionType.ARM: {
            "estado": ("V", 21),
            "trabajador": ("BC", 54),
            "fecha": ("BB", 53)
        },
        ActionType.SOLD: {
            "estado": ("W", 22),
            "trabajador": ("BE", 56),
            "fecha": ("BD", 55)
        }
    }

    def __init__(
        self,
        sheets_repo: Optional[SheetsRepository] = None,
        sheets_service: Optional[SheetsService] = None,
        validation_service: Optional[ValidationService] = None,
        spool_service: Optional[SpoolService] = None,
        worker_service: Optional[WorkerService] = None
    ):
        """
        Inicializar con dependencias inyectadas.

        Args:
            sheets_repo: Repositorio para acceso a Google Sheets
            sheets_service: Servicio de parseo de filas
            validation_service: Servicio de validación de reglas de negocio
            spool_service: Servicio de operaciones con spools
            worker_service: Servicio de operaciones con trabajadores
        """
        self.sheets_repo = sheets_repo or SheetsRepository()
        self.sheets_service = sheets_service or SheetsService()
        self.validation_service = validation_service or ValidationService()
        self.spool_service = spool_service or SpoolService()
        self.worker_service = worker_service or WorkerService()
        logger.info("ActionService inicializado con todas las dependencias")

    def _get_column_names(self, operacion: ActionType) -> dict:
        """
        Obtener nombres de columnas para operación.

        Args:
            operacion: Tipo de operación (ARM/SOLD)

        Returns:
            Dict con tuplas (letra, índice) para estado/trabajador/fecha

        Raises:
            ValueError: Si operación es inválida
        """
        if operacion not in self.COLUMN_MAPPING:
            raise ValueError(f"Operación inválida: {operacion}")
        return self.COLUMN_MAPPING[operacion]

    def _format_fecha(self, timestamp: Optional[datetime] = None) -> str:
        """
        Formatear fecha a DD/MM/YYYY.

        Args:
            timestamp: Fecha opcional (datetime object)

        Returns:
            Fecha formateada en formato DD/MM/YYYY
        """
        if timestamp:
            return timestamp.strftime("%d/%m/%Y")

        return datetime.now().strftime("%d/%m/%Y")

    def _invalidate_cache(self):
        """Invalidar cache del repository después de update."""
        try:
            # El cache se invalida automáticamente en SheetsRepository.batch_update
            logger.debug("Cache invalidado automáticamente por SheetsRepository")
        except Exception as e:
            logger.warning(f"Error al invalidar cache: {e}")

    def _build_success_response(
        self,
        tag_spool: str,
        operacion: ActionType,
        trabajador: str,
        fila: int,
        columna: str,
        valor: float,
        metadata: ActionMetadata,
        accion_tipo: str  # "iniciada" o "completada"
    ) -> ActionResponse:
        """
        Construir ActionResponse exitoso.

        Args:
            tag_spool: TAG del spool procesado
            operacion: Tipo de operación (ARM/SOLD)
            trabajador: Nombre del trabajador
            fila: Número de fila actualizada
            columna: Letra de columna actualizada (V/W)
            valor: Nuevo valor (0.1 o 1.0)
            metadata: Metadata actualizada (ActionMetadata object)
            accion_tipo: "iniciada" o "completada"

        Returns:
            ActionResponse con success=True y datos completos
        """
        return ActionResponse(
            success=True,
            message=f"Acción {operacion.value} {accion_tipo} exitosamente. "
                   f"Spool {tag_spool} {'asignado a' if accion_tipo == 'iniciada' else 'completado por'} {trabajador}",
            data=ActionData(
                tag_spool=tag_spool,
                operacion=operacion.value,
                trabajador=trabajador,
                fila_actualizada=fila,
                columna_actualizada=columna,
                valor_nuevo=valor,
                metadata_actualizada=metadata
            )
        )

    def iniciar_accion(
        self,
        worker_nombre: str,
        operacion: ActionType,
        tag_spool: str
    ) -> ActionResponse:
        """
        Iniciar una acción de manufactura.

        Flujo:
        1. Buscar trabajador activo
        2. Buscar spool por TAG
        3. Validar puede iniciar (según operación)
        4. Actualizar Google Sheets (estado=0.1, trabajador=nombre)
        5. Invalidar cache
        6. Retornar respuesta con metadata

        Args:
            worker_nombre: Nombre del trabajador (ej: "Juan Pérez")
            operacion: ActionType.ARM o ActionType.SOLD
            tag_spool: Código del spool (ej: "MK-123")

        Returns:
            ActionResponse con success=True y metadata

        Raises:
            WorkerNoEncontradoError: Si trabajador no existe o está inactivo
            SpoolNoEncontradoError: Si spool no existe
            OperacionNoPendienteError: Si acción ya está iniciada/completada
            DependenciasNoSatisfechasError: Si BA/BB no están completas
            SheetsUpdateError: Si falla actualización de Sheets
        """
        logger.info(
            f"Iniciando {operacion.value} para spool {tag_spool} "
            f"por trabajador {worker_nombre}"
        )

        try:
            # PASO 1: Buscar trabajador
            trabajador = self.worker_service.find_worker_by_nombre(worker_nombre)
            if trabajador is None:
                raise WorkerNoEncontradoError(
                    f"Trabajador '{worker_nombre}' no encontrado o está inactivo"
                )
            logger.debug(f"Trabajador encontrado: {trabajador.nombre_completo}")

            # PASO 2: Buscar spool
            spool = self.spool_service.find_spool_by_tag(tag_spool)
            if spool is None:
                raise SpoolNoEncontradoError(
                    f"Spool '{tag_spool}' no encontrado en la hoja de operaciones"
                )

            # PASO 2.5: Buscar número de fila del spool
            fila = self.sheets_repo.find_row_by_column_value(
                config.HOJA_OPERACIONES_NOMBRE,
                "G",  # Columna TAG_SPOOL
                spool.tag_spool
            )
            if fila is None:
                raise SpoolNoEncontradoError(
                    f"No se pudo encontrar fila para spool '{tag_spool}'"
                )

            logger.debug(
                f"Spool encontrado: {spool.tag_spool} (fila {fila}), "
                f"ARM={spool.arm.value}, SOLD={spool.sold.value}"
            )

            # PASO 3: Validar puede iniciar
            if operacion == ActionType.ARM:
                self.validation_service.validar_puede_iniciar_arm(spool)
            elif operacion == ActionType.SOLD:
                self.validation_service.validar_puede_iniciar_sold(spool)
            else:
                raise ValueError(f"Operación no soportada: {operacion}")

            logger.debug(f"Validación de inicio exitosa para {operacion.value}")

            # PASO 4: Preparar batch update
            columns = self._get_column_names(operacion)
            estado_col, estado_idx = columns["estado"]
            trabajador_col, trabajador_idx = columns["trabajador"]

            updates = [
                {
                    "row": fila,
                    "column": estado_col,
                    "value": 0.1
                },
                {
                    "row": fila,
                    "column": trabajador_col,
                    "value": worker_nombre
                }
            ]

            logger.debug(f"Preparando batch update: {updates}")

            # PASO 5: Ejecutar batch update
            self.sheets_repo.batch_update(config.HOJA_OPERACIONES_NOMBRE, updates)
            logger.info(
                f"Acción {operacion.value} iniciada exitosamente. "
                f"Fila {fila} actualizada: {estado_col}→0.1, "
                f"{trabajador_col}→{worker_nombre}"
            )

            # PASO 6: Invalidar cache
            self._invalidate_cache()

            # PASO 7: Construir respuesta
            if operacion == ActionType.ARM:
                metadata = ActionMetadata(
                    armador=worker_nombre,
                    soldador=None,
                    fecha_armado=None,
                    fecha_soldadura=None
                )
            else:  # SOLD
                metadata = ActionMetadata(
                    armador=None,
                    soldador=worker_nombre,
                    fecha_armado=None,
                    fecha_soldadura=None
                )

            return self._build_success_response(
                tag_spool=tag_spool,
                operacion=operacion,
                trabajador=worker_nombre,
                fila=fila,
                columna=estado_col,
                valor=0.1,
                metadata=metadata,
                accion_tipo="iniciada"
            )

        except (
            WorkerNoEncontradoError,
            SpoolNoEncontradoError,
            OperacionNoPendienteError,
            OperacionYaIniciadaError,
            OperacionYaCompletadaError,
            DependenciasNoSatisfechasError
        ) as e:
            logger.error(f"Error de validación al iniciar acción: {e}")
            raise
        except Exception as e:
            logger.error(f"Error inesperado al iniciar acción: {e}", exc_info=True)
            raise SheetsUpdateError(f"Error al actualizar Google Sheets: {str(e)}")

    def completar_accion(
        self,
        worker_nombre: str,
        operacion: ActionType,
        tag_spool: str,
        timestamp: Optional[datetime] = None
    ) -> ActionResponse:
        """
        Completar una acción de manufactura.

        CRÍTICO: Valida ownership - solo quien inició puede completar.

        Flujo:
        1. Buscar trabajador activo
        2. Buscar spool por TAG
        3. Validar puede completar + ownership (BC/BE = worker_nombre)
        4. Formatear fecha (timestamp o actual)
        5. Actualizar Google Sheets (estado=1.0, fecha=DD/MM/YYYY)
        6. Invalidar cache
        7. Retornar respuesta con metadata

        Args:
            worker_nombre: Nombre del trabajador
            operacion: ActionType.ARM o ActionType.SOLD
            tag_spool: Código del spool
            timestamp: Fecha opcional (datetime object)

        Returns:
            ActionResponse con success=True y metadata

        Raises:
            WorkerNoEncontradoError: Si trabajador no existe o está inactivo
            SpoolNoEncontradoError: Si spool no existe
            OperacionNoIniciadaError: Si acción no está iniciada (estado != 0.1)
            OperacionYaCompletadaError: Si acción ya está completa (estado = 1.0)
            NoAutorizadoError: Si trabajador != quien inició (BC/BE mismatch)
            SheetsUpdateError: Si falla actualización de Sheets
        """
        logger.info(
            f"Completando {operacion.value} para spool {tag_spool} "
            f"por trabajador {worker_nombre}"
        )

        try:
            # PASO 1: Buscar trabajador
            trabajador = self.worker_service.find_worker_by_nombre(worker_nombre)
            if trabajador is None:
                raise WorkerNoEncontradoError(
                    f"Trabajador '{worker_nombre}' no encontrado o está inactivo"
                )
            logger.debug(f"Trabajador encontrado: {trabajador.nombre_completo}")

            # PASO 2: Buscar spool
            spool = self.spool_service.find_spool_by_tag(tag_spool)
            if spool is None:
                raise SpoolNoEncontradoError(
                    f"Spool '{tag_spool}' no encontrado en la hoja de operaciones"
                )

            # PASO 2.5: Buscar número de fila del spool
            fila = self.sheets_repo.find_row_by_column_value(
                config.HOJA_OPERACIONES_NOMBRE,
                "G",  # Columna TAG_SPOOL
                spool.tag_spool
            )
            if fila is None:
                raise SpoolNoEncontradoError(
                    f"No se pudo encontrar fila para spool '{tag_spool}'"
                )

            logger.debug(
                f"Spool encontrado: {spool.tag_spool} (fila {fila}), "
                f"ARM={spool.arm.value}, SOLD={spool.sold.value}, "
                f"BC={spool.armador}, BE={spool.soldador}"
            )

            # PASO 3: Validar puede completar + ownership (CRÍTICO)
            if operacion == ActionType.ARM:
                self.validation_service.validar_puede_completar_arm(spool, worker_nombre)
                logger.debug(f"Ownership validado: BC={spool.armador} == {worker_nombre}")
            elif operacion == ActionType.SOLD:
                self.validation_service.validar_puede_completar_sold(spool, worker_nombre)
                logger.debug(f"Ownership validado: BE={spool.soldador} == {worker_nombre}")
            else:
                raise ValueError(f"Operación no soportada: {operacion}")

            logger.debug(f"Validación de completado + ownership exitosa para {operacion.value}")

            # PASO 4: Preparar fecha
            fecha = self._format_fecha(timestamp)
            logger.debug(f"Fecha de completado: {fecha}")

            # PASO 5: Preparar batch update
            columns = self._get_column_names(operacion)
            estado_col, estado_idx = columns["estado"]
            fecha_col, fecha_idx = columns["fecha"]

            updates = [
                {
                    "row": fila,
                    "column": estado_col,
                    "value": 1.0
                },
                {
                    "row": fila,
                    "column": fecha_col,
                    "value": fecha
                }
            ]

            logger.debug(f"Preparando batch update: {updates}")

            # PASO 6: Ejecutar batch update
            self.sheets_repo.batch_update(config.HOJA_OPERACIONES_NOMBRE, updates)
            logger.info(
                f"Acción {operacion.value} completada exitosamente. "
                f"Fila {fila} actualizada: {estado_col}→1.0, "
                f"{fecha_col}→{fecha}"
            )

            # PASO 7: Invalidar cache
            self._invalidate_cache()

            # PASO 8: Construir respuesta
            if operacion == ActionType.ARM:
                metadata = ActionMetadata(
                    armador=worker_nombre,
                    soldador=None,
                    fecha_armado=fecha,
                    fecha_soldadura=None
                )
            else:  # SOLD
                metadata = ActionMetadata(
                    armador=None,
                    soldador=worker_nombre,
                    fecha_armado=None,
                    fecha_soldadura=fecha
                )

            return self._build_success_response(
                tag_spool=tag_spool,
                operacion=operacion,
                trabajador=worker_nombre,
                fila=fila,
                columna=estado_col,
                valor=1.0,
                metadata=metadata,
                accion_tipo="completada"
            )

        except (
            WorkerNoEncontradoError,
            SpoolNoEncontradoError,
            OperacionNoIniciadaError,
            OperacionYaCompletadaError,
            NoAutorizadoError
        ) as e:
            logger.error(f"Error de validación al completar acción: {e}")
            raise
        except Exception as e:
            logger.error(f"Error inesperado al completar acción: {e}", exc_info=True)
            raise SheetsUpdateError(f"Error al actualizar Google Sheets: {str(e)}")
