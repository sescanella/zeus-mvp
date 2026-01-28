"""
Spools Router - Consulta de spools disponibles.

Endpoints para obtener spools disponibles para INICIAR o COMPLETAR acciones.
Aplica filtros de elegibilidad según reglas de negocio (estado, dependencias, ownership).

Endpoints:
- GET /api/spools/iniciar?operacion=ARM|SOLD - Spools elegibles para iniciar
- GET /api/spools/completar?operacion=ARM|SOLD&worker_nombre=... - Spools propios para completar
"""

from fastapi import APIRouter, Depends, Query, HTTPException, status

from backend.core.dependency import get_spool_service_v2, get_sheets_repository
from backend.services.spool_service_v2 import SpoolServiceV2
from backend.services.cycle_counter_service import CycleCounterService
from backend.repositories.sheets_repository import SheetsRepository
from backend.models.spool import SpoolListResponse
from backend.models.enums import ActionType
import logging

logger = logging.getLogger(__name__)

router = APIRouter()


def get_cycle_counter_service() -> CycleCounterService:
    """Factory for CycleCounterService (stateless)."""
    return CycleCounterService()


@router.get("/spools/iniciar", response_model=SpoolListResponse, status_code=status.HTTP_200_OK)
async def get_spools_para_iniciar(
    operacion: str = Query(..., description="Tipo de operación (ARM, SOLD o METROLOGIA)"),
    spool_service_v2: SpoolServiceV2 = Depends(get_spool_service_v2)
):
    """
    Lista spools disponibles para INICIAR la operación especificada (V2 Dynamic Mapping).

    Aplica reglas de negocio correctas usando mapeo dinámico de columnas:
    - **ARM**: Fecha_Materiales llena Y Armador vacío
    - **SOLD**: Fecha_Armado llena Y Soldador vacío
    - **METROLOGIA**: Fecha_Soldadura llena Y Fecha_QC_Metrología vacía

    V2 mejoras:
    - Lee header (row 1) para construir mapeo dinámico: nombre_columna → índice
    - Resistente a cambios de estructura en spreadsheet
    - Reglas de negocio correctas (no depende de estados numéricos obsoletos)

    Args:
        operacion: Tipo de operación a iniciar ("ARM", "SOLD" o "METROLOGIA").
                   Query param obligatorio.
        spool_service_v2: Servicio de spools V2 (inyectado automáticamente).

    Returns:
        SpoolListResponse con:
        - spools: Lista de objetos Spool elegibles para iniciar
        - total: Cantidad de spools elegibles
        - filtro_aplicado: Descripción del filtro usado

    Raises:
        HTTPException 400: Si operación es inválida (no es ARM, SOLD ni METROLOGIA).
        HTTPException 503: Si falla conexión Google Sheets.

    Example request:
        ```bash
        curl "http://localhost:8000/api/spools/iniciar?operacion=ARM"
        ```

    Example response (200 OK):
        ```json
        {
            "spools": [
                {
                    "tag_spool": "TEST-01",
                    "fecha_materiales": "2025-12-30",
                    "armador": null
                }
            ],
            "total": 1,
            "filtro_aplicado": "ARM - Fecha_Materiales llena Y Armador vacío"
        }
        ```
    """
    logger.info(f"GET /api/spools/iniciar (V2) - operacion={operacion}")

    # Validar operación (convertir string → ActionType enum)
    try:
        action_type = ActionType(operacion.upper())
    except ValueError:
        logger.warning(f"Invalid operation type: {operacion}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Operación inválida '{operacion}'. Debe ser ARM, SOLD o METROLOGIA."
        )

    # Obtener spools elegibles para iniciar usando V2
    if action_type == ActionType.ARM:
        spools = spool_service_v2.get_spools_disponibles_para_iniciar_arm()
        filtro = "ARM - Fecha_Materiales llena Y Armador vacío"
    elif action_type == ActionType.SOLD:
        spools = spool_service_v2.get_spools_disponibles_para_iniciar_sold()
        filtro = "SOLD - Fecha_Armado llena Y Soldador vacío"
    else:  # ActionType.METROLOGIA
        spools = spool_service_v2.get_spools_disponibles_para_iniciar_metrologia()
        filtro = "METROLOGIA - Fecha_Soldadura llena Y Fecha_QC_Metrología vacía"

    logger.info(f"Found {len(spools)} spools eligible to start {operacion}")

    # Construir response
    return SpoolListResponse(
        spools=spools,
        total=len(spools),
        filtro_aplicado=filtro
    )


@router.get("/spools/completar", response_model=SpoolListResponse, status_code=status.HTTP_200_OK)
async def get_spools_para_completar(
    operacion: str = Query(..., description="Tipo de operación (ARM o SOLD)"),
    worker_nombre: str = Query(..., description="Nombre completo del trabajador"),
    spool_service_v2: SpoolServiceV2 = Depends(get_spool_service_v2)
):
    """
    Lista spools que el trabajador puede COMPLETAR (V2 Dynamic Mapping).

    Aplica reglas de negocio correctas usando mapeo dinámico de columnas:
    - **ARM**: Armador lleno Y Fecha_Armado vacía (spools iniciados sin completar)
    - **SOLD**: Soldador lleno Y Fecha_Soldadura vacía (spools iniciados sin completar)

    V2 mejoras:
    - Lee header (row 1) para construir mapeo dinámico: nombre_columna → índice
    - Resistente a cambios de estructura en spreadsheet
    - Reglas de negocio correctas (no depende de estados numéricos obsoletos)
    - NOTA: Esta versión NO filtra por ownership. Retorna TODOS los spools en progreso.
      El filtrado por worker_nombre se debe implementar posteriormente si es necesario.

    Args:
        operacion: Tipo de operación a completar ("ARM" o "SOLD").
                   Query param obligatorio.
        worker_nombre: Nombre completo del trabajador (actualmente no usado en V2).
        spool_service_v2: Servicio de spools V2 (inyectado automáticamente).

    Returns:
        SpoolListResponse con:
        - spools: Lista de objetos Spool que pueden completarse
        - total: Cantidad de spools en progreso
        - filtro_aplicado: Descripción del filtro usado

    Raises:
        HTTPException 400: Si operación es inválida (no es ARM ni SOLD).
        HTTPException 503: Si falla conexión Google Sheets.

    Example request:
        ```bash
        curl "http://localhost:8000/api/spools/completar?operacion=ARM&worker_nombre=Nicolas"
        ```

    Example response (200 OK):
        ```json
        {
            "spools": [
                {
                    "tag_spool": "MK-1413-PW-23200-001-B",
                    "armador": "Nicolas",
                    "fecha_armado": null
                }
            ],
            "total": 1,
            "filtro_aplicado": "ARM - Armador lleno Y Fecha_Armado vacía"
        }
        ```

    Note:
        - V2 no aplica filtro ownership (retorna todos los spools en progreso)
        - Para filtrar por trabajador específico, agregar lógica adicional
    """
    logger.info(f"GET /api/spools/completar (V2) - operacion={operacion}, worker={worker_nombre}")

    # Validar operación (convertir string → ActionType enum)
    try:
        action_type = ActionType(operacion.upper())
    except ValueError:
        logger.warning(f"Invalid operation type: {operacion}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Operación inválida '{operacion}'. Debe ser ARM o SOLD."
        )

    # Obtener spools elegibles para completar usando V2
    if action_type == ActionType.ARM:
        spools = spool_service_v2.get_spools_disponibles_para_completar_arm()
        filtro = "ARM - Armador lleno Y Fecha_Armado vacía"
    else:  # ActionType.SOLD
        spools = spool_service_v2.get_spools_disponibles_para_completar_sold()
        filtro = "SOLD - Soldador lleno Y Fecha_Soldadura vacía"

    logger.info(f"Found {len(spools)} spools to complete for {operacion}")

    # Construir response
    return SpoolListResponse(
        spools=spools,
        total=len(spools),
        filtro_aplicado=filtro
    )


@router.get("/spools/cancelar", response_model=SpoolListResponse, status_code=status.HTTP_200_OK)
async def get_spools_para_cancelar(
    operacion: str = Query(..., description="Tipo de operación (ARM o SOLD)"),
    worker_id: int = Query(..., description="ID del trabajador"),
    spool_service_v2: SpoolServiceV2 = Depends(get_spool_service_v2)
):
    """
    Lista spools EN_PROGRESO del trabajador para CANCELAR (V2 Dynamic Mapping).

    Aplica reglas de negocio correctas usando mapeo dinámico de columnas:
    - **ARM**: Armador lleno Y Fecha_Armado vacía Y worker_id coincide
    - **SOLD**: Soldador lleno Y Fecha_Soldadura vacía Y worker_id coincide

    V2 mejoras:
    - Lee header (row 1) para construir mapeo dinámico: nombre_columna → índice
    - Resistente a cambios de estructura en spreadsheet
    - Reglas de negocio correctas (no depende de estados numéricos obsoletos)
    - Filtro ownership: Solo spools iniciados por el trabajador (formato "XX(ID)")

    Args:
        operacion: Tipo de operación a cancelar ("ARM" o "SOLD").
                   Query param obligatorio.
        worker_id: ID numérico del trabajador.
                   Query param obligatorio.
        spool_service_v2: Servicio de spools V2 (inyectado automáticamente).

    Returns:
        SpoolListResponse con:
        - spools: Lista de objetos Spool EN_PROGRESO del trabajador
        - total: Cantidad de spools cancelables
        - filtro_aplicado: Descripción del filtro usado

    Raises:
        HTTPException 400: Si operación es inválida (no es ARM ni SOLD).
        HTTPException 503: Si falla conexión Google Sheets.

    Example request:
        ```bash
        curl "http://localhost:8000/api/spools/cancelar?operacion=ARM&worker_id=93"
        ```

    Example response (200 OK):
        ```json
        {
            "spools": [
                {
                    "tag_spool": "MK-1335-CW-25238-011",
                    "armador": "Nicolas(93)",
                    "fecha_armado": null
                }
            ],
            "total": 1,
            "filtro_aplicado": "ARM - Armador lleno Y Fecha_Armado vacía Y worker_id=93"
        }
        ```
    """
    logger.info(f"GET /api/spools/cancelar (V2) - operacion={operacion}, worker_id={worker_id}")

    # Validar operación (convertir string → ActionType enum)
    try:
        action_type = ActionType(operacion.upper())
    except ValueError:
        logger.warning(f"Invalid operation type: {operacion}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Operación inválida '{operacion}'. Debe ser ARM o SOLD."
        )

    # Obtener spools cancelables del trabajador usando V2
    if action_type == ActionType.ARM:
        spools = spool_service_v2.get_spools_disponibles_para_cancelar_arm(worker_id)
        filtro = f"ARM - Armador lleno Y Fecha_Armado vacía Y worker_id={worker_id}"
    else:  # ActionType.SOLD
        spools = spool_service_v2.get_spools_disponibles_para_cancelar_sold(worker_id)
        filtro = f"SOLD - Soldador lleno Y Fecha_Soldadura vacía Y worker_id={worker_id}"

    logger.info(f"Found {len(spools)} spools to cancel for {operacion} by worker_id={worker_id}")

    # Construir response
    return SpoolListResponse(
        spools=spools,
        total=len(spools),
        filtro_aplicado=filtro
    )


@router.get("/spools/reparacion", response_model=dict, status_code=status.HTTP_200_OK)
async def get_spools_reparacion(
    sheets_repo: SheetsRepository = Depends(get_sheets_repository),
    cycle_counter: CycleCounterService = Depends(get_cycle_counter_service)
):
    """
    Lista spools RECHAZADO disponibles para reparación.

    Filtra spools donde estado_detalle contains "RECHAZADO" or "BLOQUEADO".
    Skip occupied spools (ocupado_por != None).
    For each spool:
    - Parse cycle count from Estado_Detalle
    - Check if blocked (cycle >= 3)
    - Include fecha_rechazo (from Fecha_QC_Metrologia)

    Returns:
        dict with:
        - spools: List of RECHAZADO/BLOQUEADO spools with cycle info
        - total: Total spools found
        - bloqueados: Count of BLOQUEADO spools
        - filtro_aplicado: Description of filter applied

    Raises:
        HTTPException 503: If Google Sheets connection fails

    Example response (200 OK):
        ```json
        {
            "spools": [
                {
                    "tag_spool": "MK-123",
                    "estado_detalle": "RECHAZADO (Ciclo 2/3) - Pendiente reparación",
                    "fecha_rechazo": "28-01-2026",
                    "cycle": 2,
                    "bloqueado": false
                },
                {
                    "tag_spool": "MK-456",
                    "estado_detalle": "BLOQUEADO - Contactar supervisor",
                    "fecha_rechazo": "25-01-2026",
                    "cycle": 3,
                    "bloqueado": true
                }
            ],
            "total": 2,
            "bloqueados": 1,
            "filtro_aplicado": "RECHAZADO + BLOQUEADO visibles (no ocupados)"
        }
        ```
    """
    logger.info("GET /api/spools/reparacion")

    # Fetch all spools
    all_spools = sheets_repo.get_all_spools()

    # Filter: RECHAZADO or BLOQUEADO, not occupied
    reparacion_spools = []
    bloqueados_count = 0

    for spool in all_spools:
        # Skip if occupied
        if spool.ocupado_por:
            continue

        # Check if RECHAZADO or BLOQUEADO in estado_detalle
        if not spool.estado_detalle:
            continue

        if "RECHAZADO" not in spool.estado_detalle and "BLOQUEADO" not in spool.estado_detalle:
            continue

        # Extract cycle count
        current_cycle = cycle_counter.extract_cycle_count(spool.estado_detalle)

        # Check if blocked
        is_blocked = cycle_counter.should_block(current_cycle)

        if is_blocked:
            bloqueados_count += 1

        # Build spool data
        spool_data = {
            "tag_spool": spool.tag_spool,
            "estado_detalle": spool.estado_detalle,
            "fecha_rechazo": spool.fecha_qc_metrologia,  # From Fecha_QC_Metrologia column
            "cycle": current_cycle,
            "bloqueado": is_blocked
        }

        reparacion_spools.append(spool_data)

    logger.info(f"Found {len(reparacion_spools)} reparacion spools ({bloqueados_count} bloqueados)")

    return {
        "spools": reparacion_spools,
        "total": len(reparacion_spools),
        "bloqueados": bloqueados_count,
        "filtro_aplicado": "RECHAZADO + BLOQUEADO visibles (no ocupados)"
    }
