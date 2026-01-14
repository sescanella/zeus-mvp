"""
Spools Router - Consulta de spools disponibles.

Endpoints para obtener spools disponibles para INICIAR o COMPLETAR acciones.
Aplica filtros de elegibilidad según reglas de negocio (estado, dependencias, ownership).

Endpoints:
- GET /api/spools/iniciar?operacion=ARM|SOLD - Spools elegibles para iniciar
- GET /api/spools/completar?operacion=ARM|SOLD&worker_nombre=... - Spools propios para completar
"""

from fastapi import APIRouter, Depends, Query, HTTPException, status

from backend.core.dependency import get_spool_service_v2
from backend.services.spool_service_v2 import SpoolServiceV2
from backend.models.spool import SpoolListResponse
from backend.models.enums import ActionType
import logging

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/spools/iniciar", response_model=SpoolListResponse, status_code=status.HTTP_200_OK)
async def get_spools_para_iniciar(
    operacion: str = Query(..., description="Tipo de operación (ARM o SOLD)"),
    spool_service_v2: SpoolServiceV2 = Depends(get_spool_service_v2)
):
    """
    Lista spools disponibles para INICIAR la operación especificada (V2 Dynamic Mapping).

    Aplica reglas de negocio correctas usando mapeo dinámico de columnas:
    - **ARM**: Fecha_Materiales llena Y Armador vacío
    - **SOLD**: Fecha_Armado llena Y Soldador vacío

    V2 mejoras:
    - Lee header (row 1) para construir mapeo dinámico: nombre_columna → índice
    - Resistente a cambios de estructura en spreadsheet
    - Reglas de negocio correctas (no depende de estados numéricos obsoletos)

    Args:
        operacion: Tipo de operación a iniciar ("ARM" o "SOLD").
                   Query param obligatorio.
        spool_service_v2: Servicio de spools V2 (inyectado automáticamente).

    Returns:
        SpoolListResponse con:
        - spools: Lista de objetos Spool elegibles para iniciar
        - total: Cantidad de spools elegibles
        - filtro_aplicado: Descripción del filtro usado

    Raises:
        HTTPException 400: Si operación es inválida (no es ARM ni SOLD).
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
            detail=f"Operación inválida '{operacion}'. Debe ser ARM o SOLD."
        )

    # Obtener spools elegibles para iniciar usando V2
    if action_type == ActionType.ARM:
        spools = spool_service_v2.get_spools_disponibles_para_iniciar_arm()
        filtro = "ARM - Fecha_Materiales llena Y Armador vacío"
    else:  # ActionType.SOLD
        spools = spool_service_v2.get_spools_disponibles_para_iniciar_sold()
        filtro = "SOLD - Fecha_Armado llena Y Soldador vacío"

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
