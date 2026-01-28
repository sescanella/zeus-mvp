"""
Dashboard Router - REST endpoint for initial dashboard data.

Provides GET /api/dashboard/occupied endpoint that returns current occupied spools
for initial dashboard state. SSE handles real-time updates after initial load.

v3.0 Phase 4: Dashboard visibility infrastructure.
"""

import logging
from typing import List
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from backend.repositories.sheets_repository import SheetsRepository
from backend.core.dependency import get_sheets_repository
from backend.config import config

logger = logging.getLogger(__name__)

router = APIRouter()


class OccupiedSpoolResponse(BaseModel):
    """Response model for occupied spool data."""
    tag_spool: str
    worker_nombre: str
    estado_detalle: str
    fecha_ocupacion: str


@router.get(
    "/api/dashboard/occupied",
    response_model=List[OccupiedSpoolResponse],
    summary="Get currently occupied spools",
    description="""
    Returns list of spools currently occupied by workers.

    This endpoint provides initial state for dashboard. Real-time updates
    are delivered via SSE endpoint (/api/sse/stream).

    Response includes:
    - tag_spool: Spool identifier
    - worker_nombre: Worker currently occupying spool (format: "INICIALES(ID)")
    - estado_detalle: Current state description (e.g., "ARM: En Progreso")
    - fecha_ocupacion: Date when occupation started (ISO format)

    Results sorted by fecha_ocupacion DESC (newest first).
    """
)
async def get_occupied_spools(
    sheets_repo: SheetsRepository = Depends(get_sheets_repository)
) -> List[OccupiedSpoolResponse]:
    """
    Get list of currently occupied spools.

    Queries Operaciones sheet for spools where Ocupado_Por is not empty,
    returning complete occupation details for dashboard display.

    Args:
        sheets_repo: SheetsRepository for reading Operaciones sheet

    Returns:
        List of OccupiedSpoolResponse with occupation details

    Raises:
        HTTPException: 503 if Sheets read fails
    """
    try:
        logger.info("Dashboard: Fetching occupied spools")

        # Read Operaciones sheet
        worksheet = sheets_repo.read_worksheet(config.HOJA_OPERACIONES_NOMBRE)

        # Get all data as list of lists
        all_data = worksheet.get_all_values()

        if not all_data or len(all_data) < 2:
            logger.warning("Dashboard: No data in Operaciones sheet")
            return []

        # First row is headers
        headers = all_data[0]

        # Build column index mapping
        # v3.0 columns (Ocupado_Por, Fecha_Ocupacion, Estado_Detalle) may not exist in v2.1 schema
        # Return empty list gracefully if columns missing (backwards compatibility)
        try:
            tag_spool_idx = headers.index("TAG_SPOOL")
            ocupado_por_idx = headers.index("Ocupado_Por")
            fecha_ocupacion_idx = headers.index("Fecha_Ocupacion")
            estado_detalle_idx = headers.index("Estado_Detalle")
        except ValueError as e:
            # v3.0 columns don't exist yet (sheet still on v2.1 schema)
            logger.warning(f"Dashboard: v3.0 columns not found (sheet may be v2.1 schema): {e}")
            logger.info("Dashboard: Returning empty list (no occupied spools on v2.1 schema)")
            return []

        # Parse occupied spools (rows where Ocupado_Por is not empty)
        occupied_spools = []

        for row in all_data[1:]:  # Skip header row
            # Check if row has enough columns
            if len(row) <= max(tag_spool_idx, ocupado_por_idx, fecha_ocupacion_idx, estado_detalle_idx):
                continue

            ocupado_por = row[ocupado_por_idx].strip() if ocupado_por_idx < len(row) else ""

            # Filter: only include occupied spools
            if not ocupado_por:
                continue

            tag_spool = row[tag_spool_idx].strip() if tag_spool_idx < len(row) else ""
            fecha_ocupacion = row[fecha_ocupacion_idx].strip() if fecha_ocupacion_idx < len(row) else ""
            estado_detalle = row[estado_detalle_idx].strip() if estado_detalle_idx < len(row) else ""

            # Skip if tag_spool is empty (invalid row)
            if not tag_spool:
                continue

            occupied_spools.append(
                OccupiedSpoolResponse(
                    tag_spool=tag_spool,
                    worker_nombre=ocupado_por,
                    estado_detalle=estado_detalle if estado_detalle else "Ocupado",
                    fecha_ocupacion=fecha_ocupacion if fecha_ocupacion else "N/A"
                )
            )

        # Sort by fecha_ocupacion DESC (newest first)
        # For simple sort, reverse list (assumes chronological insertion)
        occupied_spools.reverse()

        logger.info(f"Dashboard: Found {len(occupied_spools)} occupied spools")
        return occupied_spools

    except HTTPException:
        # Re-raise HTTP exceptions
        raise
    except Exception as e:
        logger.error(f"Dashboard: Failed to fetch occupied spools: {e}", exc_info=True)
        raise HTTPException(
            status_code=503,
            detail=f"Failed to read occupied spools: {str(e)}"
        )
