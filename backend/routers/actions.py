"""
Actions Router - Manufacturing action write operations.

CRITICAL endpoints for starting and completing manufacturing actions (ARM/SOLD).
Delegates all business logic to ActionService. Exception handlers in main.py
automatically map ZEUSException subclasses to appropriate HTTP status codes.

Key features:
- POST /api/iniciar-accion: Start action (assign spool to worker)
- POST /api/completar-accion: Complete action (OWNERSHIP VALIDATION - CRITICAL)

Ownership restriction: Only the worker who started an action can complete it.
Attempting to complete another worker's action → 403 FORBIDDEN.
"""

from fastapi import APIRouter, Depends, status
from backend.core.dependency import get_action_service, get_reparacion_service
from backend.services.action_service import ActionService
from backend.services.reparacion_service import ReparacionService
from backend.models.action import (
    ActionRequest,
    ActionResponse,
    BatchActionRequest,
    BatchActionResponse
)
from backend.models.enums import ActionType
import logging

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post("/iniciar-accion", response_model=ActionResponse, status_code=status.HTTP_200_OK)
async def iniciar_accion(
    request: ActionRequest,
    action_service: ActionService = Depends(get_action_service)
):
    """
    Inicia una acción de manufactura (Armado o Soldado) en un spool.

    Asigna el spool al trabajador y marca la acción como iniciada (0.1).
    Actualiza Google Sheets en batch (2 celdas: estado + trabajador).

    Validaciones:
    - Trabajador existe y está activo
    - Spool existe en hoja Operaciones
    - Operación está en estado PENDIENTE (V/W=0)
    - Dependencias satisfechas (BA llena para ARM, BB llena para SOLD)
    - Fecha de completado vacía (BB vacía para ARM, BD vacía para SOLD)

    Actualizaciones Sheets:
    - ARM: V→0.1 (col 22), BC=worker_nombre (col 55)
    - SOLD: W→0.1 (col 23), BE=worker_nombre (col 57)

    Args:
        request: Datos de la acción a iniciar (worker_nombre, operacion, tag_spool)
        action_service: Servicio de acciones (inyectado)

    Returns:
        ActionResponse con success=True y metadata de la operación

    Raises:
        HTTPException 404: Si trabajador o spool no encontrado
        HTTPException 400: Si operación ya iniciada/completada o dependencias no satisfechas
        HTTPException 503: Si falla actualización Google Sheets

    Example request:
        ```json
        {
            "worker_nombre": "Juan Pérez",
            "operacion": "ARM",
            "tag_spool": "MK-1335-CW-25238-011"
        }
        ```

    Example response:
        ```json
        {
            "success": true,
            "message": "Acción ARM iniciada exitosamente. Spool MK-1335-CW-25238-011 asignado a Juan Pérez",
            "data": {
                "tag_spool": "MK-1335-CW-25238-011",
                "operacion": "ARM",
                "trabajador": "Juan Pérez",
                "fila_actualizada": 25,
                "columna_actualizada": "V",
                "valor_nuevo": 0.1,
                "metadata_actualizada": {
                    "armador": "Juan Pérez",
                    "soldador": null,
                    "fecha_armado": null,
                    "fecha_soldadura": null
                }
            }
        }
        ```
    """
    logger.info(
        f"POST /api/iniciar-accion - worker_id={request.worker_id}, "
        f"operacion={request.operacion}, tag_spool={request.tag_spool}"
    )

    # Delegar a ActionService (orchestrator)
    # Todas las validaciones se realizan en ActionService
    # Excepciones se propagan automáticamente al exception handler
    # v2.0: Usa worker_id en vez de worker_nombre
    response = action_service.iniciar_accion(
        worker_id=request.worker_id,
        operacion=request.operacion,
        tag_spool=request.tag_spool
    )

    logger.info(
        f"Action started successfully - {request.operacion} on {request.tag_spool} "
        f"by worker_id {request.worker_id}"
    )

    return response


@router.post("/completar-accion", response_model=ActionResponse, status_code=status.HTTP_200_OK)
async def completar_accion(
    request: ActionRequest,
    action_service: ActionService = Depends(get_action_service)
):
    """
    Completa una acción de manufactura (Armado o Soldado) en un spool.

    Registra la fecha de finalización y marca la acción como completada (1.0).
    CRÍTICO: Valida ownership - solo quien inició puede completar (BC/BE check).

    Validaciones:
    - Trabajador existe y está activo
    - Spool existe en hoja Operaciones
    - Operación está en estado EN_PROGRESO (V/W=0.1)
    - **OWNERSHIP: BC/BE = worker_nombre (solo quien inició puede completar)**

    Actualizaciones Sheets:
    - ARM: V→1.0 (col 22), BB=fecha (col 54, formato DD/MM/YYYY)
    - SOLD: W→1.0 (col 23), BD=fecha (col 56, formato DD/MM/YYYY)

    Args:
        request: Datos de la acción a completar (worker_nombre, operacion, tag_spool, timestamp)
        action_service: Servicio de acciones (inyectado)

    Returns:
        ActionResponse con success=True y metadata de la operación

    Raises:
        HTTPException 404: Si trabajador o spool no encontrado
        HTTPException 400: Si operación no iniciada o ya completada
        HTTPException 403: Si trabajador != quien inició (CRÍTICO - ownership violation)
        HTTPException 503: Si falla actualización Google Sheets

    Example request:
        ```json
        {
            "worker_nombre": "Juan Pérez",
            "operacion": "ARM",
            "tag_spool": "MK-1335-CW-25238-011",
            "timestamp": "2025-11-10T14:30:00Z"
        }
        ```

    Example response (exitosa):
        ```json
        {
            "success": true,
            "message": "Acción ARM completada exitosamente. Spool MK-1335-CW-25238-011 completado por Juan Pérez",
            "data": {
                "tag_spool": "MK-1335-CW-25238-011",
                "operacion": "ARM",
                "trabajador": "Juan Pérez",
                "fila_actualizada": 25,
                "columna_actualizada": "V",
                "valor_nuevo": 1.0,
                "metadata_actualizada": {
                    "armador": null,
                    "soldador": null,
                    "fecha_armado": "10/11/2025",
                    "fecha_soldadura": null
                }
            }
        }
        ```

    Example response (403 - ownership violation):
        ```json
        {
            "success": false,
            "error": "NO_AUTORIZADO",
            "message": "Solo Juan López puede completar ARM en 'MK-1335-CW-25238-011' (él la inició). Tú eres Juan Pérez.",
            "data": {
                "tag_spool": "MK-1335-CW-25238-011",
                "trabajador_esperado": "Juan López",
                "trabajador_solicitante": "Juan Pérez",
                "operacion": "ARM"
            }
        }
        ```
    """
    logger.info(
        f"POST /api/completar-accion - worker_id={request.worker_id}, "
        f"operacion={request.operacion}, tag_spool={request.tag_spool}"
    )

    # Delegar a ActionService (orchestrator con ownership validation)
    # CRÍTICO: ActionService.completar_accion valida ownership + rol
    # Si worker != owner → raise NoAutorizadoError → 403 FORBIDDEN
    # v2.0: Usa worker_id en vez de worker_nombre
    response = action_service.completar_accion(
        worker_id=request.worker_id,
        operacion=request.operacion,
        tag_spool=request.tag_spool,
        timestamp=request.timestamp
    )

    logger.info(
        f"Action completed successfully - {request.operacion} on {request.tag_spool} "
        f"by worker_id {request.worker_id}"
    )

    return response


@router.post("/cancelar-accion", response_model=ActionResponse, status_code=status.HTTP_200_OK)
async def cancelar_accion(
    request: ActionRequest,
    action_service: ActionService = Depends(get_action_service)
):
    """
    Cancela una acción EN_PROGRESO (v2.0 CANCELAR feature).

    Revierte estado EN_PROGRESO → PENDIENTE mediante evento CANCELAR.
    CRÍTICO: Solo quien inició puede cancelar (ownership + rol validation).

    Validaciones:
    - Trabajador existe y está activo
    - Spool existe en hoja Operaciones
    - Operación está en estado EN_PROGRESO
    - **OWNERSHIP: Solo quien inició puede cancelar (desde evento INICIAR)**
    - **ROLE: Worker debe tener el rol necesario para la operación**

    Flujo v2.0:
    1. Buscar trabajador por ID
    2. Buscar spool por TAG
    3. Validar puede cancelar (EN_PROGRESO + ownership + rol)
    4. Crear evento CANCELAR_ARM/CANCELAR_SOLD
    5. Escribir evento en Metadata (estado reconstruido en próxima lectura)

    Args:
        request: Datos de la acción a cancelar (worker_id, operacion, tag_spool)
        action_service: Servicio de acciones (inyectado)

    Returns:
        ActionResponse con success=True y evento_id

    Raises:
        HTTPException 404: Si trabajador o spool no encontrado
        HTTPException 400: Si operación no está EN_PROGRESO
        HTTPException 403: Si trabajador != quien inició (CRÍTICO - ownership violation)
        HTTPException 403: Si trabajador no tiene rol necesario (RolNoAutorizadoError)
        HTTPException 503: Si falla escritura en Metadata

    Example request:
        ```json
        {
            "worker_id": 93,
            "operacion": "ARM",
            "tag_spool": "MK-1335-CW-25238-011"
        }
        ```

    Example response (exitosa):
        ```json
        {
            "success": true,
            "message": "Acción ARM cancelada exitosamente. Spool MK-1335-CW-25238-011 revertido a PENDIENTE",
            "data": {
                "tag_spool": "MK-1335-CW-25238-011",
                "operacion": "ARM",
                "trabajador": "Mauricio Rodriguez",
                "evento_id": "550e8400-e29b-41d4-a716-446655440000",
                "metadata_actualizada": {
                    "armador": null,
                    "soldador": null,
                    "fecha_armado": null,
                    "fecha_soldadura": null
                }
            }
        }
        ```

    Example response (403 - ownership violation):
        ```json
        {
            "success": false,
            "error": "NO_AUTORIZADO",
            "message": "Solo Mauricio Rodriguez puede cancelar ARM en 'MK-1335-CW-25238-011' (él la inició). Tú eres Carlos Pimiento.",
            "data": {
                "tag_spool": "MK-1335-CW-25238-011",
                "trabajador_esperado": "Mauricio Rodriguez",
                "trabajador_solicitante": "Carlos Pimiento",
                "operacion": "ARM"
            }
        }
        ```

    Example response (403 - rol no autorizado):
        ```json
        {
            "success": false,
            "error": "ROL_NO_AUTORIZADO",
            "message": "Trabajador 94 no tiene el rol 'Armador' necesario para realizar la operación 'ARM'. Roles actuales: Soldador, Metrologia",
            "data": {
                "worker_id": 94,
                "operacion": "ARM",
                "rol_requerido": "Armador",
                "roles_actuales": ["Soldador", "Metrologia"]
            }
        }
        ```
    """
    logger.info(
        f"POST /api/cancelar-accion - worker_id={request.worker_id}, "
        f"operacion={request.operacion}, tag_spool={request.tag_spool}"
    )

    # Delegar a ActionService (orchestrator con ownership + rol validation)
    # CRÍTICO: Valida que worker sea quien inició + tenga rol necesario
    # v2.0: Usa worker_id en vez de worker_nombre
    response = action_service.cancelar_accion(
        worker_id=request.worker_id,
        operacion=request.operacion,
        tag_spool=request.tag_spool
    )

    logger.info(
        f"Action cancelled successfully - {request.operacion} on {request.tag_spool} "
        f"by worker_id {request.worker_id}"
    )

    return response


# ============================================================================
# BATCH OPERATIONS ENDPOINTS (v2.0 Multiselect)
# ============================================================================

@router.post("/iniciar-accion-batch", response_model=BatchActionResponse, status_code=status.HTTP_200_OK)
async def iniciar_accion_batch(
    request: BatchActionRequest,
    action_service: ActionService = Depends(get_action_service)
):
    """
    Inicia múltiples acciones de manufactura simultáneamente (v2.0 batch operations).

    Procesa hasta 50 spools en una sola petición.
    Continúa procesando aunque algunos spools fallen (manejo errores parciales).
    Retorna resumen con exitosos/fallidos y detalle por spool.

    Validaciones (por cada spool):
    - Trabajador existe y está activo
    - Spool existe en hoja Operaciones
    - Operación está en estado PENDIENTE
    - Dependencias satisfechas (BA llena para ARM, BB llena para SOLD)
    - Trabajador tiene el rol necesario para la operación (v2.0)

    Flujo v2.0:
    1. Validar límite batch (máx 50 spools)
    2. Iterar sobre cada tag_spool
    3. Llamar iniciar_accion() para cada uno (captura excepciones individuales)
    4. Crear eventos INICIAR_ARM/INICIAR_SOLD en Metadata
    5. Construir BatchActionResponse con resumen

    Args:
        request: Datos batch (worker_id, operacion, tag_spools[])
        action_service: Servicio de acciones (inyectado)

    Returns:
        BatchActionResponse con resumen (total, exitosos, fallidos) y detalle por spool

    Raises:
        HTTPException 400: Si tag_spools > 50 o está vacío

    Example request:
        ```json
        {
            "worker_id": 93,
            "operacion": "ARM",
            "tag_spools": [
                "MK-1335-CW-25238-011",
                "MK-1335-CW-25238-012",
                "MK-1335-CW-25238-013"
            ]
        }
        ```

    Example response (todos exitosos):
        ```json
        {
            "success": true,
            "message": "Batch ARM iniciado: 3 de 3 spools exitosos",
            "total": 3,
            "exitosos": 3,
            "fallidos": 0,
            "resultados": [
                {
                    "tag_spool": "MK-1335-CW-25238-011",
                    "success": true,
                    "message": "Acción ARM iniciada exitosamente",
                    "evento_id": "a1b2c3d4-e5f6-4a5b-8c9d-1e2f3a4b5c6d",
                    "error_type": null
                },
                {
                    "tag_spool": "MK-1335-CW-25238-012",
                    "success": true,
                    "message": "Acción ARM iniciada exitosamente",
                    "evento_id": "b2c3d4e5-f6a7-5b6c-9d0e-2f3a4b5c6d7e",
                    "error_type": null
                },
                {
                    "tag_spool": "MK-1335-CW-25238-013",
                    "success": true,
                    "message": "Acción ARM iniciada exitosamente",
                    "evento_id": "c3d4e5f6-a7b8-6c7d-0e1f-3a4b5c6d7e8f",
                    "error_type": null
                }
            ]
        }
        ```

    Example response (errores parciales):
        ```json
        {
            "success": true,
            "message": "Batch ARM iniciado: 2 de 3 spools exitosos (1 fallo)",
            "total": 3,
            "exitosos": 2,
            "fallidos": 1,
            "resultados": [
                {
                    "tag_spool": "MK-1335-CW-25238-011",
                    "success": true,
                    "message": "Acción ARM iniciada exitosamente",
                    "evento_id": "a1b2c3d4-e5f6-4a5b-8c9d-1e2f3a4b5c6d",
                    "error_type": null
                },
                {
                    "tag_spool": "MK-1335-CW-25238-012",
                    "success": false,
                    "message": "Operación ya iniciada por otro trabajador",
                    "evento_id": null,
                    "error_type": "OperacionYaIniciadaError"
                },
                {
                    "tag_spool": "MK-1335-CW-25238-013",
                    "success": true,
                    "message": "Acción ARM iniciada exitosamente",
                    "evento_id": "c3d4e5f6-a7b8-6c7d-0e1f-3a4b5c6d7e8f",
                    "error_type": null
                }
            ]
        }
        ```
    """
    logger.info(
        f"POST /api/iniciar-accion-batch - worker_id={request.worker_id}, "
        f"operacion={request.operacion}, spools_count={len(request.tag_spools)}"
    )

    # Delegar a ActionService (batch orchestrator)
    # Procesa cada spool individualmente, continúa si algunos fallan
    # Retorna BatchActionResponse con resumen y detalle
    response = action_service.iniciar_accion_batch(
        worker_id=request.worker_id,
        operacion=request.operacion,
        tag_spools=request.tag_spools
    )

    logger.info(
        f"Batch action started - {request.operacion}: {response.exitosos} exitosos, "
        f"{response.fallidos} fallidos de {response.total} total"
    )

    return response


@router.post("/completar-accion-batch", response_model=BatchActionResponse, status_code=status.HTTP_200_OK)
async def completar_accion_batch(
    request: BatchActionRequest,
    action_service: ActionService = Depends(get_action_service)
):
    """
    Completa múltiples acciones de manufactura simultáneamente (v2.0 batch operations).

    Procesa hasta 50 spools en una sola petición.
    Continúa procesando aunque algunos spools fallen (manejo errores parciales).
    CRÍTICO: Valida ownership individualmente (solo quien inició puede completar).

    Validaciones (por cada spool):
    - Trabajador existe y está activo
    - Spool existe en hoja Operaciones
    - Operación está en estado EN_PROGRESO
    - **OWNERSHIP: Worker debe ser quien inició (desde evento INICIAR)**
    - **ROLE: Worker debe tener el rol necesario para la operación (v2.0)**

    Flujo v2.0:
    1. Validar límite batch (máx 50 spools)
    2. Iterar sobre cada tag_spool
    3. Llamar completar_accion() para cada uno (incluye ownership validation)
    4. Crear eventos COMPLETAR_ARM/COMPLETAR_SOLD en Metadata
    5. Construir BatchActionResponse con resumen

    Args:
        request: Datos batch (worker_id, operacion, tag_spools[], timestamp)
        action_service: Servicio de acciones (inyectado)

    Returns:
        BatchActionResponse con resumen (total, exitosos, fallidos) y detalle por spool

    Raises:
        HTTPException 400: Si tag_spools > 50 o está vacío

    Example request:
        ```json
        {
            "worker_id": 93,
            "operacion": "ARM",
            "tag_spools": [
                "MK-1335-CW-25238-011",
                "MK-1335-CW-25238-012",
                "MK-1335-CW-25238-013"
            ],
            "timestamp": "2025-12-12T14:30:00Z"
        }
        ```

    Example response (todos exitosos):
        ```json
        {
            "success": true,
            "message": "Batch ARM completado: 3 de 3 spools exitosos",
            "total": 3,
            "exitosos": 3,
            "fallidos": 0,
            "resultados": [
                {
                    "tag_spool": "MK-1335-CW-25238-011",
                    "success": true,
                    "message": "Acción ARM completada exitosamente",
                    "evento_id": "a1b2c3d4-e5f6-4a5b-8c9d-1e2f3a4b5c6d",
                    "error_type": null
                },
                {
                    "tag_spool": "MK-1335-CW-25238-012",
                    "success": true,
                    "message": "Acción ARM completada exitosamente",
                    "evento_id": "b2c3d4e5-f6a7-5b6c-9d0e-2f3a4b5c6d7e",
                    "error_type": null
                },
                {
                    "tag_spool": "MK-1335-CW-25238-013",
                    "success": true,
                    "message": "Acción ARM completada exitosamente",
                    "evento_id": "c3d4e5f6-a7b8-6c7d-0e1f-3a4b5c6d7e8f",
                    "error_type": null
                }
            ]
        }
        ```

    Example response (ownership errors - worker 94 intenta completar iniciados por 93):
        ```json
        {
            "success": false,
            "message": "Batch ARM completado: 0 de 3 spools exitosos (3 fallos)",
            "total": 3,
            "exitosos": 0,
            "fallidos": 3,
            "resultados": [
                {
                    "tag_spool": "MK-1335-CW-25238-011",
                    "success": false,
                    "message": "Solo Mauricio Rodriguez puede completar ARM en 'MK-1335-CW-25238-011' (él la inició)",
                    "evento_id": null,
                    "error_type": "NoAutorizadoError"
                },
                {
                    "tag_spool": "MK-1335-CW-25238-012",
                    "success": false,
                    "message": "Solo Mauricio Rodriguez puede completar ARM en 'MK-1335-CW-25238-012' (él la inició)",
                    "evento_id": null,
                    "error_type": "NoAutorizadoError"
                },
                {
                    "tag_spool": "MK-1335-CW-25238-013",
                    "success": false,
                    "message": "Solo Mauricio Rodriguez puede completar ARM en 'MK-1335-CW-25238-013' (él la inició)",
                    "evento_id": null,
                    "error_type": "NoAutorizadoError"
                }
            ]
        }
        ```
    """
    logger.info(
        f"POST /api/completar-accion-batch - worker_id={request.worker_id}, "
        f"operacion={request.operacion}, spools_count={len(request.tag_spools)}"
    )

    # Delegar a ActionService (batch orchestrator con ownership validation)
    # CRÍTICO: Valida ownership individualmente para cada spool
    # Procesa cada spool individualmente, continúa si algunos fallan
    # Retorna BatchActionResponse con resumen y detalle
    response = action_service.completar_accion_batch(
        worker_id=request.worker_id,
        operacion=request.operacion,
        tag_spools=request.tag_spools
    )

    logger.info(
        f"Batch action completed - {request.operacion}: {response.exitosos} exitosos, "
        f"{response.fallidos} fallidos de {response.total} total"
    )

    return response


@router.post("/cancelar-accion-batch", response_model=BatchActionResponse, status_code=status.HTTP_200_OK)
async def cancelar_accion_batch(
    request: BatchActionRequest,
    action_service: ActionService = Depends(get_action_service)
):
    """
    Cancela múltiples acciones EN_PROGRESO simultáneamente (v2.0 batch CANCELAR feature).

    Procesa hasta 50 spools en una sola petición.
    Continúa procesando aunque algunos spools fallen (manejo errores parciales).
    CRÍTICO: Valida ownership individualmente (solo quien inició puede cancelar).

    Validaciones (por cada spool):
    - Trabajador existe y está activo
    - Spool existe en hoja Operaciones
    - Operación está en estado EN_PROGRESO
    - **OWNERSHIP: Worker debe ser quien inició (desde evento INICIAR)**
    - **ROLE: Worker debe tener el rol necesario para la operación (v2.0)**

    Flujo v2.0:
    1. Validar límite batch (máx 50 spools)
    2. Iterar sobre cada tag_spool
    3. Llamar cancelar_accion() para cada uno (incluye ownership validation)
    4. Crear eventos CANCELAR_ARM/CANCELAR_SOLD/CANCELAR_METROLOGIA en Metadata
    5. Construir BatchActionResponse con resumen

    Args:
        request: Datos batch (worker_id, operacion, tag_spools[])
        action_service: Servicio de acciones (inyectado)

    Returns:
        BatchActionResponse con resumen (total, exitosos, fallidos) y detalle por spool

    Raises:
        HTTPException 400: Si tag_spools > 50 o está vacío

    Example request:
        ```json
        {
            "worker_id": 93,
            "operacion": "ARM",
            "tag_spools": [
                "MK-1335-CW-25238-011",
                "MK-1335-CW-25238-012",
                "MK-1335-CW-25238-013"
            ]
        }
        ```

    Example response (todos exitosos):
        ```json
        {
            "success": true,
            "message": "Batch ARM cancelado: 3 de 3 spools exitosos",
            "total": 3,
            "exitosos": 3,
            "fallidos": 0,
            "resultados": [
                {
                    "tag_spool": "MK-1335-CW-25238-011",
                    "success": true,
                    "message": "Acción ARM cancelada exitosamente",
                    "evento_id": "a1b2c3d4-e5f6-4a5b-8c9d-1e2f3a4b5c6d",
                    "error_type": null
                },
                {
                    "tag_spool": "MK-1335-CW-25238-012",
                    "success": true,
                    "message": "Acción ARM cancelada exitosamente",
                    "evento_id": "b2c3d4e5-f6a7-5b6c-9d0e-2f3a4b5c6d7e",
                    "error_type": null
                },
                {
                    "tag_spool": "MK-1335-CW-25238-013",
                    "success": true,
                    "message": "Acción ARM cancelada exitosamente",
                    "evento_id": "c3d4e5f6-a7b8-6c7d-0e1f-3a4b5c6d7e8f",
                    "error_type": null
                }
            ]
        }
        ```

    Example response (ownership errors - worker 94 intenta cancelar iniciados por 93):
        ```json
        {
            "success": false,
            "message": "Batch ARM cancelado: 0 de 3 spools exitosos (3 fallos)",
            "total": 3,
            "exitosos": 0,
            "fallidos": 3,
            "resultados": [
                {
                    "tag_spool": "MK-1335-CW-25238-011",
                    "success": false,
                    "message": "Solo Mauricio Rodriguez puede cancelar ARM en 'MK-1335-CW-25238-011' (él la inició)",
                    "evento_id": null,
                    "error_type": "NoAutorizadoError"
                },
                {
                    "tag_spool": "MK-1335-CW-25238-012",
                    "success": false,
                    "message": "Solo Mauricio Rodriguez puede cancelar ARM en 'MK-1335-CW-25238-012' (él la inició)",
                    "evento_id": null,
                    "error_type": "NoAutorizadoError"
                },
                {
                    "tag_spool": "MK-1335-CW-25238-013",
                    "success": false,
                    "message": "Solo Mauricio Rodriguez puede cancelar ARM en 'MK-1335-CW-25238-013' (él la inició)",
                    "evento_id": null,
                    "error_type": "NoAutorizadoError"
                }
            ]
        }
        ```
    """
    logger.info(
        f"POST /api/cancelar-accion-batch - worker_id={request.worker_id}, "
        f"operacion={request.operacion}, spools_count={len(request.tag_spools)}"
    )

    # Delegar a ActionService (batch orchestrator con ownership validation)
    # CRÍTICO: Valida ownership individualmente para cada spool
    # Procesa cada spool individualmente, continúa si algunos fallan
    # Retorna BatchActionResponse con resumen y detalle
    response = action_service.cancelar_accion_batch(
        worker_id=request.worker_id,
        operacion=request.operacion,
        tag_spools=request.tag_spools
    )

    logger.info(
        f"Batch cancelar completed - {request.operacion}: {response.exitosos} exitosos, "
        f"{response.fallidos} fallidos de {response.total} total"
    )

    return response


# ============================================================================
# REPARACION ENDPOINTS (v3.0 Phase 6)
# ============================================================================

@router.post("/tomar-reparacion", response_model=dict, status_code=status.HTTP_200_OK)
async def tomar_reparacion(
    request: ActionRequest,
    reparacion_service: ReparacionService = Depends(get_reparacion_service)
):
    """
    Worker takes RECHAZADO spool for repair (v3.0 Phase 6).

    Validates:
    - Spool exists and is RECHAZADO (not BLOQUEADO)
    - Spool not currently occupied
    - Worker exists and is active

    Updates:
    - Ocupado_Por = worker_nombre
    - Fecha_Ocupacion = current datetime
    - Estado_Detalle = "EN_REPARACION (Ciclo X/3) - Ocupado: {worker}"

    Args:
        request: ActionRequest (worker_id, tag_spool)
        reparacion_service: ReparacionService (injected)

    Returns:
        dict with success message and estado_detalle

    Raises:
        HTTPException 404: Spool or worker not found
        HTTPException 400: Spool not RECHAZADO
        HTTPException 403: Spool is BLOQUEADO (HTTP 403)
        HTTPException 409: Spool occupied by another worker

    Example request:
        ```json
        {
            "worker_id": 93,
            "tag_spool": "MK-1335-CW-25238-011"
        }
        ```

    Example response (200 OK):
        ```json
        {
            "success": true,
            "message": "Reparación tomada para spool MK-1335-CW-25238-011",
            "tag_spool": "MK-1335-CW-25238-011",
            "worker_nombre": "MR(93)",
            "estado_detalle": "EN_REPARACION (Ciclo 2/3) - Ocupado: MR(93)",
            "cycle": 2
        }
        ```
    """
    logger.info(f"POST /api/tomar-reparacion - worker_id={request.worker_id}, tag_spool={request.tag_spool}")

    # Worker nombre_completo needs to be fetched from worker_id
    # For now, use format "W{worker_id}" as placeholder - service will fetch actual name
    result = await reparacion_service.tomar_reparacion(
        tag_spool=request.tag_spool,
        worker_id=request.worker_id,
        worker_nombre=f"W({request.worker_id})"  # Placeholder - service fetches actual name
    )

    logger.info(f"Reparación tomada: {request.tag_spool} by worker_id {request.worker_id}")
    return result


@router.post("/pausar-reparacion", response_model=dict, status_code=status.HTTP_200_OK)
async def pausar_reparacion(
    request: ActionRequest,
    reparacion_service: ReparacionService = Depends(get_reparacion_service)
):
    """
    Worker pauses repair work and releases occupation (v3.0 Phase 6).

    Validates:
    - Spool exists and is EN_REPARACION
    - Worker owns the spool (ownership validation)

    Updates:
    - Ocupado_Por = None
    - Fecha_Ocupacion = None
    - Estado_Detalle = "REPARACION_PAUSADA (Ciclo X/3)"

    Args:
        request: ActionRequest (worker_id, tag_spool)
        reparacion_service: ReparacionService (injected)

    Returns:
        dict with success message and estado_detalle

    Raises:
        HTTPException 404: Spool not found
        HTTPException 400: Spool not EN_REPARACION
        HTTPException 403: Worker doesn't own the spool

    Example response (200 OK):
        ```json
        {
            "success": true,
            "message": "Reparación pausada para spool MK-1335-CW-25238-011",
            "tag_spool": "MK-1335-CW-25238-011",
            "estado_detalle": "REPARACION_PAUSADA (Ciclo 2/3)"
        }
        ```
    """
    logger.info(f"POST /api/pausar-reparacion - worker_id={request.worker_id}, tag_spool={request.tag_spool}")

    result = await reparacion_service.pausar_reparacion(
        tag_spool=request.tag_spool,
        worker_id=request.worker_id
    )

    logger.info(f"Reparación pausada: {request.tag_spool}")
    return result


@router.post("/completar-reparacion", response_model=dict, status_code=status.HTTP_200_OK)
async def completar_reparacion(
    request: ActionRequest,
    reparacion_service: ReparacionService = Depends(get_reparacion_service)
):
    """
    Worker completes repair and returns spool to metrología queue (v3.0 Phase 6).

    Validates:
    - Spool exists and is EN_REPARACION
    - Worker owns the spool (ownership validation)

    Updates:
    - Ocupado_Por = None
    - Fecha_Ocupacion = None
    - Estado_Detalle = "PENDIENTE_METROLOGIA"

    Args:
        request: ActionRequest (worker_id, tag_spool)
        reparacion_service: ReparacionService (injected)

    Returns:
        dict with success message and estado_detalle

    Raises:
        HTTPException 404: Spool not found
        HTTPException 400: Spool not EN_REPARACION
        HTTPException 403: Worker doesn't own the spool

    Example response (200 OK):
        ```json
        {
            "success": true,
            "message": "Reparación completada para spool MK-1335-CW-25238-011 - devuelto a metrología",
            "tag_spool": "MK-1335-CW-25238-011",
            "estado_detalle": "PENDIENTE_METROLOGIA",
            "cycle": 2
        }
        ```
    """
    logger.info(f"POST /api/completar-reparacion - worker_id={request.worker_id}, tag_spool={request.tag_spool}")

    result = await reparacion_service.completar_reparacion(
        tag_spool=request.tag_spool,
        worker_id=request.worker_id,
        worker_nombre=f"W({request.worker_id})"  # Placeholder
    )

    logger.info(f"Reparación completada: {request.tag_spool} -> PENDIENTE_METROLOGIA")
    return result


@router.post("/cancelar-reparacion", response_model=dict, status_code=status.HTTP_200_OK)
async def cancelar_reparacion(
    request: ActionRequest,
    reparacion_service: ReparacionService = Depends(get_reparacion_service)
):
    """
    Worker cancels repair work and returns spool to RECHAZADO (v3.0 Phase 6).

    Validates:
    - Spool exists and is EN_REPARACION or REPARACION_PAUSADA

    Updates:
    - Ocupado_Por = None
    - Fecha_Ocupacion = None
    - Estado_Detalle = "RECHAZADO (Ciclo X/3) - Pendiente reparación"

    Args:
        request: ActionRequest (worker_id, tag_spool)
        reparacion_service: ReparacionService (injected)

    Returns:
        dict with success message and estado_detalle

    Raises:
        HTTPException 404: Spool not found
        HTTPException 400: Spool not EN_REPARACION or REPARACION_PAUSADA

    Example response (200 OK):
        ```json
        {
            "success": true,
            "message": "Reparación cancelada para spool MK-1335-CW-25238-011",
            "tag_spool": "MK-1335-CW-25238-011",
            "estado_detalle": "RECHAZADO (Ciclo 2/3) - Pendiente reparación"
        }
        ```
    """
    logger.info(f"POST /api/cancelar-reparacion - worker_id={request.worker_id}, tag_spool={request.tag_spool}")

    result = await reparacion_service.cancelar_reparacion(
        tag_spool=request.tag_spool,
        worker_id=request.worker_id
    )

    logger.info(f"Reparación cancelada: {request.tag_spool}")
    return result
