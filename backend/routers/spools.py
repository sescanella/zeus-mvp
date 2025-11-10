"""
Spools Router - Consulta de spools disponibles.

Endpoints para obtener spools disponibles para INICIAR o COMPLETAR acciones.
Aplica filtros de elegibilidad según reglas de negocio (estado, dependencias, ownership).

Endpoints:
- GET /api/spools/iniciar?operacion=ARM|SOLD - Spools elegibles para iniciar
- GET /api/spools/completar?operacion=ARM|SOLD&worker_nombre=... - Spools propios para completar
"""

from fastapi import APIRouter, Depends, Query, HTTPException, status

from backend.core.dependency import get_spool_service
from backend.services.spool_service import SpoolService
from backend.models.spool import SpoolListResponse
from backend.models.enums import ActionType
import logging

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/spools/iniciar", response_model=SpoolListResponse, status_code=status.HTTP_200_OK)
async def get_spools_para_iniciar(
    operacion: str = Query(..., description="Tipo de operación (ARM o SOLD)"),
    spool_service: SpoolService = Depends(get_spool_service)
):
    """
    Lista spools disponibles para INICIAR la operación especificada.

    Aplica filtros de elegibilidad según operación:
    - **ARM**: Requiere V=0 (pendiente), BA llena (materiales OK), BB vacía (sin fecha armado)
    - **SOLD**: Requiere W=0 (pendiente), BB llena (armado completo), BD vacía (sin fecha soldadura)

    Solo retorna spools que cumplen TODOS los criterios. Si un spool tiene:
    - ARM=0.1 (ya iniciado) → NO aparece en lista ARM
    - ARM=1.0 (ya completado) → NO aparece en lista ARM
    - BA vacía (sin materiales) → NO aparece en lista ARM
    - BB llena (ya armado) → NO aparece en lista ARM (debe completarse primero)

    Args:
        operacion: Tipo de operación a iniciar ("ARM" o "SOLD").
                   Query param obligatorio.
        spool_service: Servicio de spools (inyectado automáticamente).

    Returns:
        SpoolListResponse con:
        - spools: Lista de objetos Spool elegibles para iniciar
        - total: Cantidad de spools elegibles
        - filtro_aplicado: Descripción del filtro usado

    Raises:
        HTTPException 400: Si operación es inválida (no es ARM ni SOLD).
        HTTPException 503: Si falla conexión Google Sheets.
                           Manejado automáticamente por exception handler en main.py.

    Example request:
        ```bash
        curl "http://localhost:8000/api/spools/iniciar?operacion=ARM"
        ```

    Example response (200 OK):
        ```json
        {
            "spools": [
                {
                    "tag_spool": "MK-1335-CW-25238-011",
                    "arm": 0.0,
                    "sold": 0.0,
                    "fecha_materiales": "2025-01-10",
                    "fecha_armado": null,
                    "armador": null,
                    "fecha_soldadura": null,
                    "soldador": null
                }
            ],
            "total": 1,
            "filtro_aplicado": "ARM pendiente (V=0, BA llena, BB vacía)"
        }
        ```

    Example response (400 - operación inválida):
        ```bash
        curl "http://localhost:8000/api/spools/iniciar?operacion=INVALID"
        ```
        ```json
        {
            "detail": "Operación inválida 'INVALID'. Debe ser ARM o SOLD."
        }
        ```

    Note:
        - Lista vacía es válida (significa que no hay spools disponibles)
        - Cache se aplica en SheetsRepository (TTL 1 min para Operaciones)
        - Filtrado se realiza en SpoolService (no en este router)
    """
    logger.info(f"GET /api/spools/iniciar - operacion={operacion}")

    # Validar operación (convertir string → ActionType enum)
    try:
        action_type = ActionType(operacion.upper())
    except ValueError:
        logger.warning(f"Invalid operation type: {operacion}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Operación inválida '{operacion}'. Debe ser ARM o SOLD."
        )

    # Obtener spools elegibles para iniciar
    spools = spool_service.get_spools_para_iniciar(action_type)

    # Construir descripción del filtro aplicado
    if action_type == ActionType.ARM:
        filtro = "ARM pendiente (V=0, BA llena, BB vacía)"
    else:  # ActionType.SOLD
        filtro = "SOLD pendiente (W=0, BB llena, BD vacía)"

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
    spool_service: SpoolService = Depends(get_spool_service)
):
    """
    Lista spools que el trabajador puede COMPLETAR (solo spools propios).

    **CRÍTICO**: Aplica filtro de ownership - solo retorna spools donde worker_nombre
    es quien inició la acción (BC para ARM, BE para SOLD).

    Esto previene que un trabajador complete una acción iniciada por otro trabajador.
    El filtrado se realiza en SpoolService comparando nombres de forma case-insensitive
    y eliminando espacios extra.

    Filtros aplicados según operación:
    - **ARM**: Requiere V=0.1 (en progreso), BC=worker_nombre (trabajador es armador)
    - **SOLD**: Requiere W=0.1 (en progreso), BE=worker_nombre (trabajador es soldador)

    Si un trabajador NO ha iniciado ninguna acción, retorna lista vacía (NO es error).

    Args:
        operacion: Tipo de operación a completar ("ARM" o "SOLD").
                   Query param obligatorio.
        worker_nombre: Nombre completo del trabajador (ej: "Juan Pérez").
                      Query param obligatorio. Se recomienda URL encoding.
        spool_service: Servicio de spools (inyectado automáticamente).

    Returns:
        SpoolListResponse con:
        - spools: Lista de objetos Spool que el trabajador puede completar
        - total: Cantidad de spools propios en progreso
        - filtro_aplicado: Descripción del filtro usado (incluye nombre trabajador)

    Raises:
        HTTPException 400: Si operación es inválida (no es ARM ni SOLD).
        HTTPException 503: Si falla conexión Google Sheets.
                           Manejado automáticamente por exception handler en main.py.

    Example request:
        ```bash
        # URL encoding: "Juan Pérez" → "Juan%20P%C3%A9rez"
        curl "http://localhost:8000/api/spools/completar?operacion=ARM&worker_nombre=Juan%20P%C3%A9rez"
        ```

    Example response (200 OK - tiene spools):
        ```json
        {
            "spools": [
                {
                    "tag_spool": "MK-1335-CW-25238-011",
                    "arm": 0.1,
                    "sold": 0.0,
                    "armador": "Juan Pérez",
                    "fecha_armado": null
                }
            ],
            "total": 1,
            "filtro_aplicado": "ARM en progreso de Juan Pérez (V=0.1, BC=Juan Pérez)"
        }
        ```

    Example response (200 OK - sin spools):
        ```json
        {
            "spools": [],
            "total": 0,
            "filtro_aplicado": "ARM en progreso de Juan Pérez (V=0.1, BC=Juan Pérez)"
        }
        ```

    Example response (400 - operación inválida):
        ```bash
        curl "http://localhost:8000/api/spools/completar?operacion=INVALID&worker_nombre=Juan"
        ```
        ```json
        {
            "detail": "Operación inválida 'INVALID'. Debe ser ARM o SOLD."
        }
        ```

    Note:
        - Lista vacía NO es error (significa que el trabajador no tiene spools en progreso)
        - Matching de nombres es case-insensitive: "juan perez" == "Juan Pérez"
        - Espacios extra son eliminados antes de comparar
        - Cache se aplica en SheetsRepository (TTL 1 min para Operaciones)
        - Filtrado ownership se realiza en SpoolService (no en este router)
    """
    logger.info(f"GET /api/spools/completar - operacion={operacion}, worker={worker_nombre}")

    # Validar operación (convertir string → ActionType enum)
    try:
        action_type = ActionType(operacion.upper())
    except ValueError:
        logger.warning(f"Invalid operation type: {operacion}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Operación inválida '{operacion}'. Debe ser ARM o SOLD."
        )

    # Obtener spools elegibles para completar (solo propios del trabajador)
    spools = spool_service.get_spools_para_completar(action_type, worker_nombre)

    # Construir descripción del filtro aplicado
    if action_type == ActionType.ARM:
        filtro = f"ARM en progreso de {worker_nombre} (V=0.1, BC={worker_nombre})"
    else:  # ActionType.SOLD
        filtro = f"SOLD en progreso de {worker_nombre} (W=0.1, BE={worker_nombre})"

    logger.info(f"Worker '{worker_nombre}' has {len(spools)} spools to complete for {operacion}")

    # Construir response
    return SpoolListResponse(
        spools=spools,
        total=len(spools),
        filtro_aplicado=filtro
    )
