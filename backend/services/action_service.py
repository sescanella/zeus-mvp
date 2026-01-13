"""
ActionService - Orquestador de acciones de manufactura (v2.0 Event Sourcing).

v2.0 Cambios críticos:
- Hoja Operaciones es READ-ONLY (no se modifica)
- Todos los eventos se escriben en hoja Metadata (Event Sourcing)
- Estados se reconstruyen desde Metadata, no desde columnas

Responsabilidades:
- Coordinar flujos INICIAR/COMPLETAR
- Validar ownership (solo quien inició puede completar)
- Escribir eventos en Metadata (append-only)
- Logging comprehensivo

Dependencias:
- MetadataRepository: Escritura de eventos (NEW v2.0)
- ValidationService: Validación ownership + estados (reconstruye desde Metadata)
- SpoolService: Búsqueda por TAG
- WorkerService: Búsqueda por nombre
"""

import logging
from typing import Optional
from datetime import datetime, date

from backend.repositories.metadata_repository import MetadataRepository
from backend.services.validation_service import ValidationService
from backend.services.spool_service import SpoolService
from backend.services.worker_service import WorkerService

from backend.models.enums import ActionType
from backend.models.action import ActionRequest, ActionResponse, ActionData, ActionMetadata
from backend.models.metadata import MetadataEvent, EventoTipo, Accion
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
    RolNoAutorizadoError,  # v2.0: Role-based access control
    SheetsUpdateError
)

logger = logging.getLogger(__name__)


class ActionService:
    """
    Servicio de orquestación de acciones de manufactura (v2.0 Event Sourcing).

    v2.0: Escribe eventos en Metadata, NO modifica hoja Operaciones.
    """

    def __init__(
        self,
        metadata_repository: Optional[MetadataRepository] = None,
        validation_service: Optional[ValidationService] = None,
        spool_service: Optional[SpoolService] = None,
        worker_service: Optional[WorkerService] = None
    ):
        """
        Inicializar con dependencias inyectadas.

        Args:
            metadata_repository: Repositorio para escribir eventos (v2.0 NEW)
            validation_service: Servicio de validación (reconstruye estado desde Metadata)
            spool_service: Servicio de operaciones con spools
            worker_service: Servicio de operaciones con trabajadores
        """
        self.metadata_repository = metadata_repository or MetadataRepository(sheets_repo=None)
        self.validation_service = validation_service or ValidationService(
            metadata_repository=self.metadata_repository
        )
        self.spool_service = spool_service or SpoolService()
        self.worker_service = worker_service or WorkerService()
        logger.info("ActionService v2.0 inicializado con Event Sourcing")

    def _get_evento_tipo(self, operacion: ActionType, accion: Accion) -> EventoTipo:
        """
        Obtener EventoTipo desde operación + acción.

        Args:
            operacion: ARM o SOLD
            accion: INICIAR o COMPLETAR

        Returns:
            EventoTipo correspondiente (INICIAR_ARM, COMPLETAR_SOLD, etc.)
        """
        event_type_str = f"{accion.value}_{operacion.value}"
        return EventoTipo(event_type_str)

    def _build_success_response(
        self,
        tag_spool: str,
        operacion: ActionType,
        trabajador: str,
        metadata: ActionMetadata,
        accion_tipo: str,  # "iniciada" o "completada"
        evento_id: str  # UUID del evento escrito en Metadata
    ) -> ActionResponse:
        """
        Construir ActionResponse exitoso (v2.0 Event Sourcing).

        Args:
            tag_spool: TAG del spool procesado
            operacion: Tipo de operación (ARM/SOLD)
            trabajador: Nombre del trabajador
            metadata: Metadata actualizada (ActionMetadata object)
            accion_tipo: "iniciada" o "completada"
            evento_id: UUID del evento escrito en Metadata

        Returns:
            ActionResponse con success=True y datos completos
        """
        return ActionResponse(
            success=True,
            message=f"Acción {operacion.value} {accion_tipo} exitosamente. "
                   f"Evento registrado en Metadata (ID: {evento_id[:8]}...)",
            data=ActionData(
                tag_spool=tag_spool,
                operacion=operacion.value,
                trabajador=trabajador,
                fila_actualizada=0,  # v2.0: No hay fila (Operaciones es READ-ONLY)
                columna_actualizada="Metadata",  # v2.0: Se escribe en Metadata
                valor_nuevo=0.0,  # v2.0: No hay valor numérico
                metadata_actualizada=metadata
            )
        )

    def iniciar_accion(
        self,
        worker_id: int,
        operacion: ActionType,
        tag_spool: str
    ) -> ActionResponse:
        """
        Iniciar una acción de manufactura (v2.0 Event Sourcing con roles).

        v2.0 Flujo:
        1. Buscar trabajador activo por ID
        2. Buscar spool por TAG (obtener datos base)
        3. Validar puede iniciar + validar rol operativo (ValidationService reconstruye estado desde Metadata)
        4. Crear evento INICIAR_ARM/INICIAR_SOLD
        5. Escribir evento en hoja Metadata (append-only)
        6. Retornar respuesta con evento_id

        Args:
            worker_id: ID del trabajador (ej: 93, 94, 95)
            operacion: ActionType.ARM o ActionType.SOLD
            tag_spool: Código del spool (ej: "MK-1335-CW-25238-011")

        Returns:
            ActionResponse con success=True y evento_id

        Raises:
            WorkerNoEncontradoError: Si trabajador no existe o está inactivo
            SpoolNoEncontradoError: Si spool no existe
            OperacionNoPendienteError: Si acción ya está iniciada/completada
            DependenciasNoSatisfechasError: Si fecha_materiales no está completa
            RolNoAutorizadoError: Si trabajador no tiene rol necesario (v2.0)
            SheetsUpdateError: Si falla escritura en Metadata
        """
        logger.info(
            f"[v2.0] Iniciando {operacion.value} para spool {tag_spool} "
            f"por trabajador ID {worker_id}"
        )

        try:
            # PASO 1: Buscar trabajador activo por ID
            trabajador = self.worker_service.find_worker_by_id(worker_id)
            if trabajador is None:
                raise WorkerNoEncontradoError(
                    f"Trabajador ID {worker_id} no encontrado o está inactivo"
                )
            logger.debug(f"Trabajador encontrado: {trabajador.nombre_completo} (ID: {trabajador.id})")

            # PASO 2: Buscar spool
            spool = self.spool_service.find_spool_by_tag(tag_spool)
            if spool is None:
                raise SpoolNoEncontradoError(
                    f"Spool '{tag_spool}' no encontrado en la hoja de operaciones"
                )

            logger.debug(
                f"Spool encontrado: {spool.tag_spool}, "
                f"fecha_materiales={spool.fecha_materiales}"
            )

            # PASO 3: Validar puede iniciar + validar rol operativo (ValidationService reconstruye estado desde Metadata)
            if operacion == ActionType.ARM:
                self.validation_service.validar_puede_iniciar_arm(spool, worker_id=worker_id)
            elif operacion == ActionType.SOLD:
                self.validation_service.validar_puede_iniciar_sold(spool, worker_id=worker_id)
            else:
                raise ValueError(f"Operación no soportada: {operacion}")

            logger.debug(f"Validación de inicio exitosa para {operacion.value}")

            # PASO 4: Crear evento INICIAR_ARM/INICIAR_SOLD
            evento_tipo = self._get_evento_tipo(operacion, Accion.INICIAR)
            fecha_hoy = date.today().isoformat()  # YYYY-MM-DD

            evento = MetadataEvent(
                evento_tipo=evento_tipo,
                tag_spool=tag_spool,
                worker_id=trabajador.id,
                worker_nombre=trabajador.nombre_completo,
                operacion=operacion.value,
                accion=Accion.INICIAR,
                fecha_operacion=fecha_hoy,
                metadata_json=None  # Opcional: podríamos agregar IP, device, etc.
            )

            logger.debug(f"Evento creado: {evento_tipo.value}, ID={evento.id}")

            # PASO 5: Escribir evento en Metadata (append-only)
            self.metadata_repository.append_event(evento)
            logger.info(
                f"[v2.0] Acción {operacion.value} iniciada exitosamente. "
                f"Evento escrito en Metadata: {evento.id}"
            )

            # PASO 6: Construir respuesta
            worker_nombre = trabajador.nombre_completo
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
                metadata=metadata,
                accion_tipo="iniciada",
                evento_id=evento.id
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
        worker_id: int,
        operacion: ActionType,
        tag_spool: str,
        timestamp: Optional[datetime] = None
    ) -> ActionResponse:
        """
        Completar una acción de manufactura (v2.0 Event Sourcing con roles).

        CRÍTICO: Valida ownership - solo quien inició puede completar.

        v2.0 Flujo:
        1. Buscar trabajador activo por ID
        2. Buscar spool por TAG
        3. Validar puede completar + ownership + rol operativo (ValidationService reconstruye desde Metadata)
        4. Crear evento COMPLETAR_ARM/COMPLETAR_SOLD
        5. Escribir evento en hoja Metadata (append-only)
        6. Retornar respuesta con evento_id

        Args:
            worker_id: ID del trabajador (ej: 93, 94, 95)
            operacion: ActionType.ARM o ActionType.SOLD
            tag_spool: Código del spool
            timestamp: Fecha opcional (no usado en v2.0 - se usa date.today())

        Returns:
            ActionResponse con success=True y evento_id

        Raises:
            WorkerNoEncontradoError: Si trabajador no existe o está inactivo
            SpoolNoEncontradoError: Si spool no existe
            OperacionNoIniciadaError: Si acción no está iniciada
            OperacionYaCompletadaError: Si acción ya está completa
            NoAutorizadoError: Si trabajador != quien inició (ownership desde Metadata)
            RolNoAutorizadoError: Si trabajador no tiene rol necesario (v2.0)
            SheetsUpdateError: Si falla escritura en Metadata
        """
        logger.info(
            f"[v2.0] Completando {operacion.value} para spool {tag_spool} "
            f"por trabajador ID {worker_id}"
        )

        try:
            # PASO 1: Buscar trabajador activo por ID
            trabajador = self.worker_service.find_worker_by_id(worker_id)
            if trabajador is None:
                raise WorkerNoEncontradoError(
                    f"Trabajador ID {worker_id} no encontrado o está inactivo"
                )
            logger.debug(f"Trabajador encontrado: {trabajador.nombre_completo} (ID: {trabajador.id})")

            # PASO 2: Buscar spool
            spool = self.spool_service.find_spool_by_tag(tag_spool)
            if spool is None:
                raise SpoolNoEncontradoError(
                    f"Spool '{tag_spool}' no encontrado en la hoja de operaciones"
                )

            logger.debug(f"Spool encontrado: {spool.tag_spool}")

            # PASO 3: Validar puede completar + ownership + rol operativo (CRÍTICO)
            # ValidationService reconstruye estado desde Metadata y valida ownership + rol
            worker_nombre = trabajador.nombre_completo
            if operacion == ActionType.ARM:
                self.validation_service.validar_puede_completar_arm(spool, worker_nombre=worker_nombre, worker_id=worker_id)
                logger.debug(f"Ownership y rol validados desde Metadata para ARM")
            elif operacion == ActionType.SOLD:
                self.validation_service.validar_puede_completar_sold(spool, worker_nombre=worker_nombre, worker_id=worker_id)
                logger.debug(f"Ownership y rol validados desde Metadata para SOLD")
            else:
                raise ValueError(f"Operación no soportada: {operacion}")

            logger.debug(f"Validación de completado + ownership exitosa para {operacion.value}")

            # PASO 4: Crear evento COMPLETAR_ARM/COMPLETAR_SOLD
            evento_tipo = self._get_evento_tipo(operacion, Accion.COMPLETAR)
            fecha_hoy = date.today().isoformat()  # YYYY-MM-DD

            evento = MetadataEvent(
                evento_tipo=evento_tipo,
                tag_spool=tag_spool,
                worker_id=trabajador.id,
                worker_nombre=trabajador.nombre_completo,
                operacion=operacion.value,
                accion=Accion.COMPLETAR,
                fecha_operacion=fecha_hoy,
                metadata_json=None  # Opcional: podríamos agregar IP, device, etc.
            )

            logger.debug(f"Evento creado: {evento_tipo.value}, ID={evento.id}")

            # PASO 5: Escribir evento en Metadata (append-only)
            self.metadata_repository.append_event(evento)
            logger.info(
                f"[v2.0] Acción {operacion.value} completada exitosamente. "
                f"Evento escrito en Metadata: {evento.id}"
            )

            # PASO 6: Construir respuesta
            if operacion == ActionType.ARM:
                metadata = ActionMetadata(
                    armador=worker_nombre,
                    soldador=None,
                    fecha_armado=fecha_hoy,
                    fecha_soldadura=None
                )
            else:  # SOLD
                metadata = ActionMetadata(
                    armador=None,
                    soldador=worker_nombre,
                    fecha_armado=None,
                    fecha_soldadura=fecha_hoy
                )

            return self._build_success_response(
                tag_spool=tag_spool,
                operacion=operacion,
                trabajador=worker_nombre,
                metadata=metadata,
                accion_tipo="completada",
                evento_id=evento.id
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

    def cancelar_accion(
        self,
        worker_id: int,
        operacion: ActionType,
        tag_spool: str
    ) -> ActionResponse:
        """
        Cancelar una acción EN_PROGRESO (v2.0 CANCELAR feature).

        Revierte estado EN_PROGRESO → PENDIENTE mediante evento CANCELAR.
        CRÍTICO: Solo quien inició puede cancelar (ownership validation).

        v2.0 Flujo:
        1. Buscar trabajador activo por ID
        2. Buscar spool por TAG
        3. Validar puede cancelar: EN_PROGRESO + ownership + rol (ValidationService)
        4. Crear evento CANCELAR_ARM/CANCELAR_SOLD
        5. Escribir evento en hoja Metadata (append-only)
        6. Retornar respuesta con evento_id

        Args:
            worker_id: ID del trabajador que intenta cancelar (debe ser quien inició)
            operacion: ActionType.ARM o ActionType.SOLD
            tag_spool: Código del spool

        Returns:
            ActionResponse con success=True y evento_id

        Raises:
            WorkerNoEncontradoError: Si trabajador no existe o está inactivo
            SpoolNoEncontradoError: Si spool no existe
            OperacionNoIniciadaError: Si operación no está EN_PROGRESO
            NoAutorizadoError: Si trabajador != quien inició (CRÍTICO)
            RolNoAutorizadoError: Si trabajador no tiene rol necesario
            SheetsUpdateError: Si falla escritura en Metadata

        Examples:
            >>> # Worker 93 inició ARM, ahora cancela
            >>> service.cancelar_accion(93, ActionType.ARM, "MK-1335-CW-25238-011")
            ActionResponse(success=True, ...)

            >>> # Worker 94 intenta cancelar ARM iniciado por Worker 93
            >>> service.cancelar_accion(94, ActionType.ARM, "MK-1335-CW-25238-011")
            # Lanza NoAutorizadoError
        """
        logger.info(
            f"[v2.0] Cancelando {operacion.value} para spool {tag_spool} "
            f"por trabajador ID {worker_id}"
        )

        try:
            # PASO 1: Buscar trabajador activo por ID
            trabajador = self.worker_service.find_worker_by_id(worker_id)
            if trabajador is None:
                raise WorkerNoEncontradoError(
                    f"Trabajador ID {worker_id} no encontrado o está inactivo"
                )
            logger.debug(f"Trabajador encontrado: {trabajador.nombre_completo} (ID: {trabajador.id})")

            # PASO 2: Buscar spool
            spool = self.spool_service.find_spool_by_tag(tag_spool)
            if spool is None:
                raise SpoolNoEncontradoError(
                    f"Spool '{tag_spool}' no encontrado en la hoja de operaciones"
                )

            logger.debug(f"Spool encontrado: {spool.tag_spool}")

            # PASO 3: Validar puede cancelar: EN_PROGRESO + ownership + rol (CRÍTICO)
            worker_nombre = trabajador.nombre_completo
            self.validation_service.validar_puede_cancelar(
                spool=spool,
                operacion=operacion.value,
                worker_nombre=worker_nombre,
                worker_id=worker_id
            )
            logger.debug(f"Validación de CANCELAR exitosa: EN_PROGRESO + ownership + rol")

            # PASO 4: Crear evento CANCELAR_ARM/CANCELAR_SOLD
            evento_tipo = self._get_evento_tipo(operacion, Accion.CANCELAR)
            fecha_hoy = date.today().isoformat()  # YYYY-MM-DD

            evento = MetadataEvent(
                evento_tipo=evento_tipo,
                tag_spool=tag_spool,
                worker_id=trabajador.id,
                worker_nombre=trabajador.nombre_completo,
                operacion=operacion.value,
                accion=Accion.CANCELAR,
                fecha_operacion=fecha_hoy,
                metadata_json=None  # Opcional: podríamos agregar motivo de cancelación
            )

            logger.debug(f"Evento CANCELAR creado: {evento_tipo.value}, ID={evento.id}")

            # PASO 5: Escribir evento en Metadata (append-only)
            self.metadata_repository.append_event(evento)
            logger.info(
                f"[v2.0] Acción {operacion.value} cancelada exitosamente. "
                f"Evento CANCELAR escrito en Metadata: {evento.id}"
            )

            # PASO 6: Construir respuesta
            if operacion == ActionType.ARM:
                metadata = ActionMetadata(
                    armador=None,  # Revierte a PENDIENTE (sin trabajador)
                    soldador=None,
                    fecha_armado=None,
                    fecha_soldadura=None
                )
            else:  # SOLD
                metadata = ActionMetadata(
                    armador=None,
                    soldador=None,  # Revierte a PENDIENTE (sin trabajador)
                    fecha_armado=None,
                    fecha_soldadura=None
                )

            return self._build_success_response(
                tag_spool=tag_spool,
                operacion=operacion,
                trabajador=worker_nombre,
                metadata=metadata,
                accion_tipo="cancelada",  # Nueva acción_tipo
                evento_id=evento.id
            )

        except (
            WorkerNoEncontradoError,
            SpoolNoEncontradoError,
            OperacionNoIniciadaError,
            NoAutorizadoError
        ) as e:
            logger.error(f"Error de validación al cancelar acción: {e}")
            raise
        except Exception as e:
            logger.error(f"Error inesperado al cancelar acción: {e}", exc_info=True)
            raise SheetsUpdateError(f"Error al actualizar Google Sheets: {str(e)}")

    # ========================================================================
    # BATCH OPERATIONS (v2.0 Multiselect)
    # ========================================================================

    def iniciar_accion_batch(
        self,
        worker_id: int,
        operacion: ActionType,
        tag_spools: list[str]
    ) -> 'BatchActionResponse':
        """
        Iniciar múltiples acciones simultáneamente (v2.0 batch operations).

        Procesa hasta 50 spools en una sola operación.
        Continúa procesando aunque algunos spools fallen (manejo errores parciales).

        v2.0 Flujo:
        1. Validar límite batch (máx 50 spools)
        2. Iterar sobre cada tag_spool
        3. Llamar iniciar_accion() para cada uno (captura excepciones individuales)
        4. Construir BatchActionResponse con resumen (exitosos/fallidos)

        Args:
            worker_id: ID del trabajador que realiza las acciones
            operacion: ActionType.ARM o ActionType.SOLD
            tag_spools: Lista de TAGs (máximo 50)

        Returns:
            BatchActionResponse con resumen y detalle por spool

        Raises:
            ValueError: Si tag_spools > 50 o está vacío

        Examples:
            >>> # Iniciar 3 spools ARM con worker 93
            >>> tags = ["MK-1335-CW-25238-011", "MK-1335-CW-25238-012", "MK-1335-CW-25238-013"]
            >>> response = service.iniciar_accion_batch(93, ActionType.ARM, tags)
            >>> print(response.exitosos, response.fallidos)
            3 0

            >>> # Con errores parciales (1 ya iniciado)
            >>> response = service.iniciar_accion_batch(93, ActionType.ARM, tags)
            >>> print(response.exitosos, response.fallidos)
            2 1
        """
        from backend.models.action import BatchActionResponse, BatchActionResult

        logger.info(
            f"[v2.0 BATCH] Iniciando {operacion.value} para {len(tag_spools)} spools "
            f"por trabajador ID {worker_id}"
        )

        # Validación básica
        if not tag_spools:
            raise ValueError("tag_spools no puede estar vacío")
        if len(tag_spools) > 50:
            raise ValueError(f"Batch limitado a 50 spools (recibido: {len(tag_spools)})")

        resultados: list[BatchActionResult] = []
        exitosos = 0
        fallidos = 0

        # Procesar cada spool individualmente
        for tag_spool in tag_spools:
            try:
                # Llamar al método individual
                response = self.iniciar_accion(
                    worker_id=worker_id,
                    operacion=operacion,
                    tag_spool=tag_spool
                )

                # Extraer evento_id del mensaje (formato: "Evento registrado en Metadata (ID: abc12345...)")
                evento_id = None
                if "ID:" in response.message:
                    # Extraer UUID del mensaje
                    start_idx = response.message.find("ID:") + 4
                    end_idx = response.message.find("...", start_idx)
                    if end_idx > start_idx:
                        evento_id = response.message[start_idx:end_idx].strip()

                resultados.append(BatchActionResult(
                    tag_spool=tag_spool,
                    success=True,
                    message=f"Acción {operacion.value} iniciada exitosamente",
                    evento_id=evento_id,
                    error_type=None
                ))
                exitosos += 1
                logger.debug(f"[BATCH] Spool {tag_spool}: éxito")

            except (
                WorkerNoEncontradoError,
                SpoolNoEncontradoError,
                OperacionNoPendienteError,
                OperacionYaIniciadaError,
                OperacionYaCompletadaError,
                DependenciasNoSatisfechasError
            ) as e:
                # Error de validación - continuar con siguiente spool
                error_type = type(e).__name__
                resultados.append(BatchActionResult(
                    tag_spool=tag_spool,
                    success=False,
                    message=str(e),
                    evento_id=None,
                    error_type=error_type
                ))
                fallidos += 1
                logger.warning(f"[BATCH] Spool {tag_spool}: fallo ({error_type}): {e}")

            except Exception as e:
                # Error inesperado - continuar con siguiente spool
                error_type = "UnexpectedError"
                resultados.append(BatchActionResult(
                    tag_spool=tag_spool,
                    success=False,
                    message=f"Error inesperado: {str(e)}",
                    evento_id=None,
                    error_type=error_type
                ))
                fallidos += 1
                logger.error(f"[BATCH] Spool {tag_spool}: error inesperado: {e}", exc_info=True)

        # Construir mensaje resumen
        total = len(tag_spools)
        if fallidos == 0:
            mensaje = f"Batch {operacion.value} iniciado: {exitosos} de {total} spools exitosos"
        else:
            mensaje = f"Batch {operacion.value} iniciado: {exitosos} de {total} spools exitosos ({fallidos} fallos)"

        logger.info(
            f"[v2.0 BATCH] Iniciar {operacion.value} completado: "
            f"{exitosos} exitosos, {fallidos} fallidos de {total} total"
        )

        return BatchActionResponse(
            success=(exitosos > 0),  # Éxito si al menos uno se procesó
            message=mensaje,
            total=total,
            exitosos=exitosos,
            fallidos=fallidos,
            resultados=resultados
        )

    def completar_accion_batch(
        self,
        worker_id: int,
        operacion: ActionType,
        tag_spools: list[str]
    ) -> 'BatchActionResponse':
        """
        Completar múltiples acciones simultáneamente (v2.0 batch operations).

        Procesa hasta 50 spools en una sola operación.
        Continúa procesando aunque algunos spools fallen (manejo errores parciales).
        CRÍTICO: Valida ownership individualmente (solo quien inició puede completar).

        v2.0 Flujo:
        1. Validar límite batch (máx 50 spools)
        2. Iterar sobre cada tag_spool
        3. Llamar completar_accion() para cada uno (captura excepciones individuales)
        4. Construir BatchActionResponse con resumen (exitosos/fallidos)

        Args:
            worker_id: ID del trabajador que realiza las acciones
            operacion: ActionType.ARM o ActionType.SOLD
            tag_spools: Lista de TAGs (máximo 50)

        Returns:
            BatchActionResponse con resumen y detalle por spool

        Raises:
            ValueError: Si tag_spools > 50 o está vacío

        Examples:
            >>> # Completar 3 spools ARM con worker 93 (quien los inició)
            >>> tags = ["MK-1335-CW-25238-011", "MK-1335-CW-25238-012", "MK-1335-CW-25238-013"]
            >>> response = service.completar_accion_batch(93, ActionType.ARM, tags)
            >>> print(response.exitosos, response.fallidos)
            3 0

            >>> # Con ownership error (worker 94 intenta completar iniciados por 93)
            >>> response = service.completar_accion_batch(94, ActionType.ARM, tags)
            >>> print(response.exitosos, response.fallidos)
            0 3  # Todos fallan por NoAutorizadoError
        """
        from backend.models.action import BatchActionResponse, BatchActionResult

        logger.info(
            f"[v2.0 BATCH] Completando {operacion.value} para {len(tag_spools)} spools "
            f"por trabajador ID {worker_id}"
        )

        # Validación básica
        if not tag_spools:
            raise ValueError("tag_spools no puede estar vacío")
        if len(tag_spools) > 50:
            raise ValueError(f"Batch limitado a 50 spools (recibido: {len(tag_spools)})")

        resultados: list[BatchActionResult] = []
        exitosos = 0
        fallidos = 0

        # Procesar cada spool individualmente
        for tag_spool in tag_spools:
            try:
                # Llamar al método individual (incluye ownership validation)
                response = self.completar_accion(
                    worker_id=worker_id,
                    operacion=operacion,
                    tag_spool=tag_spool
                )

                # Extraer evento_id del mensaje
                evento_id = None
                if "ID:" in response.message:
                    start_idx = response.message.find("ID:") + 4
                    end_idx = response.message.find("...", start_idx)
                    if end_idx > start_idx:
                        evento_id = response.message[start_idx:end_idx].strip()

                resultados.append(BatchActionResult(
                    tag_spool=tag_spool,
                    success=True,
                    message=f"Acción {operacion.value} completada exitosamente",
                    evento_id=evento_id,
                    error_type=None
                ))
                exitosos += 1
                logger.debug(f"[BATCH] Spool {tag_spool}: éxito")

            except (
                WorkerNoEncontradoError,
                SpoolNoEncontradoError,
                OperacionNoIniciadaError,
                OperacionYaCompletadaError,
                NoAutorizadoError  # CRÍTICO: ownership validation
            ) as e:
                # Error de validación - continuar con siguiente spool
                error_type = type(e).__name__
                resultados.append(BatchActionResult(
                    tag_spool=tag_spool,
                    success=False,
                    message=str(e),
                    evento_id=None,
                    error_type=error_type
                ))
                fallidos += 1
                logger.warning(f"[BATCH] Spool {tag_spool}: fallo ({error_type}): {e}")

            except Exception as e:
                # Error inesperado - continuar con siguiente spool
                error_type = "UnexpectedError"
                resultados.append(BatchActionResult(
                    tag_spool=tag_spool,
                    success=False,
                    message=f"Error inesperado: {str(e)}",
                    evento_id=None,
                    error_type=error_type
                ))
                fallidos += 1
                logger.error(f"[BATCH] Spool {tag_spool}: error inesperado: {e}", exc_info=True)

        # Construir mensaje resumen
        total = len(tag_spools)
        if fallidos == 0:
            mensaje = f"Batch {operacion.value} completado: {exitosos} de {total} spools exitosos"
        else:
            mensaje = f"Batch {operacion.value} completado: {exitosos} de {total} spools exitosos ({fallidos} fallos)"

        logger.info(
            f"[v2.0 BATCH] Completar {operacion.value} completado: "
            f"{exitosos} exitosos, {fallidos} fallidos de {total} total"
        )

        return BatchActionResponse(
            success=(exitosos > 0),  # Éxito si al menos uno se procesó
            message=mensaje,
            total=total,
            exitosos=exitosos,
            fallidos=fallidos,
            resultados=resultados
        )

    def cancelar_accion_batch(
        self,
        worker_id: int,
        operacion: ActionType,
        tag_spools: list[str]
    ) -> 'BatchActionResponse':
        """
        Cancelar múltiples acciones EN_PROGRESO simultáneamente (v2.0 batch operations).

        Procesa hasta 50 spools en una sola operación.
        Continúa procesando aunque algunos spools fallen (manejo errores parciales).
        CRÍTICO: Valida ownership individualmente (solo quien inició puede cancelar).

        v2.0 Flujo:
        1. Validar límite batch (máx 50 spools)
        2. Iterar sobre cada tag_spool
        3. Llamar cancelar_accion() para cada uno (captura excepciones individuales)
        4. Construir BatchActionResponse con resumen (exitosos/fallidos)

        Args:
            worker_id: ID del trabajador que realiza las cancelaciones
            operacion: ActionType.ARM, ActionType.SOLD, o ActionType.METROLOGIA
            tag_spools: Lista de TAGs (máximo 50)

        Returns:
            BatchActionResponse con resumen y detalle por spool

        Raises:
            ValueError: Si tag_spools > 50 o está vacío

        Examples:
            >>> # Cancelar 3 spools ARM con worker 93 (quien los inició)
            >>> tags = ["MK-1335-CW-25238-011", "MK-1335-CW-25238-012", "MK-1335-CW-25238-013"]
            >>> response = service.cancelar_accion_batch(93, ActionType.ARM, tags)
            >>> print(response.exitosos, response.fallidos)
            3 0

            >>> # Con ownership error (worker 94 intenta cancelar iniciados por 93)
            >>> response = service.cancelar_accion_batch(94, ActionType.ARM, tags)
            >>> print(response.exitosos, response.fallidos)
            0 3  # Todos fallan por NoAutorizadoError
        """
        from backend.models.action import BatchActionResponse, BatchActionResult

        logger.info(
            f"[v2.0 BATCH] Cancelando {operacion.value} para {len(tag_spools)} spools "
            f"por trabajador ID {worker_id}"
        )

        # Validación básica
        if not tag_spools:
            raise ValueError("tag_spools no puede estar vacío")
        if len(tag_spools) > 50:
            raise ValueError(f"Batch limitado a 50 spools (recibido: {len(tag_spools)})")

        resultados: list[BatchActionResult] = []
        exitosos = 0
        fallidos = 0

        # Procesar cada spool individualmente
        for tag_spool in tag_spools:
            try:
                # Llamar al método individual (incluye ownership validation)
                response = self.cancelar_accion(
                    worker_id=worker_id,
                    operacion=operacion,
                    tag_spool=tag_spool
                )

                # Extraer evento_id del mensaje
                evento_id = None
                if "ID:" in response.message:
                    start_idx = response.message.find("ID:") + 4
                    end_idx = response.message.find("...", start_idx)
                    if end_idx > start_idx:
                        evento_id = response.message[start_idx:end_idx].strip()

                resultados.append(BatchActionResult(
                    tag_spool=tag_spool,
                    success=True,
                    message=f"Acción {operacion.value} cancelada exitosamente",
                    evento_id=evento_id,
                    error_type=None
                ))
                exitosos += 1
                logger.debug(f"[BATCH] Spool {tag_spool}: éxito (cancelado)")

            except (
                WorkerNoEncontradoError,
                SpoolNoEncontradoError,
                OperacionNoIniciadaError,
                NoAutorizadoError,  # CRÍTICO: ownership validation
                RolNoAutorizadoError
            ) as e:
                # Error de validación - continuar con siguiente spool
                error_type = type(e).__name__
                resultados.append(BatchActionResult(
                    tag_spool=tag_spool,
                    success=False,
                    message=str(e),
                    evento_id=None,
                    error_type=error_type
                ))
                fallidos += 1
                logger.warning(f"[BATCH] Spool {tag_spool}: fallo ({error_type}): {e}")

            except Exception as e:
                # Error inesperado - continuar con siguiente spool
                error_type = "UnexpectedError"
                resultados.append(BatchActionResult(
                    tag_spool=tag_spool,
                    success=False,
                    message=f"Error inesperado: {str(e)}",
                    evento_id=None,
                    error_type=error_type
                ))
                fallidos += 1
                logger.error(f"[BATCH] Spool {tag_spool}: error inesperado: {e}", exc_info=True)

        # Construir mensaje resumen
        total = len(tag_spools)
        if fallidos == 0:
            mensaje = f"Batch {operacion.value} cancelado: {exitosos} de {total} spools exitosos"
        else:
            mensaje = f"Batch {operacion.value} cancelado: {exitosos} de {total} spools exitosos ({fallidos} fallos)"

        logger.info(
            f"[v2.0 BATCH] Cancelar {operacion.value} completado: "
            f"{exitosos} exitosos, {fallidos} fallidos de {total} total"
        )

        return BatchActionResponse(
            success=(exitosos > 0),  # Éxito si al menos uno se procesó
            message=mensaje,
            total=total,
            exitosos=exitosos,
            fallidos=fallidos,
            resultados=resultados
        )
