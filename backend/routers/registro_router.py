"""
Mi Registro Router - Worker daily production log.

Allows workers to consult their union work records for a given date,
replacing the paper-based tracking system.

Endpoints:
- GET /api/registro/{worker_id} - Get worker's production log (default: today)
"""
import logging
from typing import Optional
from collections import defaultdict

from fastapi import APIRouter, Depends, HTTPException, Query

from backend.core.dependency import get_union_repository, get_worker_service
from backend.repositories.union_repository import UnionRepository
from backend.services.worker_service import WorkerService
from backend.models.registro_api import (
    RegistroResponse,
    RegistroResumen,
    SpoolGroup,
    WorkerUnionRecord,
)
from backend.utils.date_formatter import today_chile, format_date_for_sheets
from backend.exceptions import SheetsConnectionError

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/registro/{worker_id}", response_model=RegistroResponse)
async def get_registro(
    worker_id: int,
    fecha: Optional[str] = Query(
        None,
        description="Date filter in DD-MM-YYYY format. Defaults to today (Chile timezone).",
        pattern=r"^\d{2}-\d{2}-\d{4}$",
    ),
    union_repo: UnionRepository = Depends(get_union_repository),
    worker_service: WorkerService = Depends(get_worker_service),
):
    """
    Get a worker's daily production log (Mi Registro).

    Returns all unions worked by the worker on the given date,
    grouped by spool and operation (ARM/SOLD).

    Args:
        worker_id: Numeric worker ID (e.g. 93)
        fecha: Optional date filter (DD-MM-YYYY). Defaults to today (Chile TZ).
        union_repo: UnionRepository dependency
        worker_service: WorkerService dependency

    Returns:
        RegistroResponse with worker info, summary, and spool groups

    Raises:
        404: Worker not found
        500: Google Sheets connection error
    """
    try:
        # Step 1: Look up worker name
        worker = worker_service.find_worker_by_id(worker_id)
        if not worker:
            raise HTTPException(
                status_code=404,
                detail=f"Worker {worker_id} not found"
            )

        worker_nombre = worker.nombre_completo

        # Step 2: Default fecha to today (Chile timezone)
        if not fecha:
            fecha = format_date_for_sheets(today_chile())

        # Step 3: Query union records for this worker
        records = union_repo.get_by_worker_id(worker_id, fecha)

        # Step 4: Group by (tag_spool, operacion)
        groups: dict[tuple[str, str], list[dict]] = defaultdict(list)
        for rec in records:
            key = (rec["tag_spool"], rec["operacion"])
            groups[key].append(rec)

        # Step 5: Build SpoolGroup list
        spool_groups = []
        for (tag_spool, operacion), group_records in groups.items():
            uniones = [
                WorkerUnionRecord(
                    n_union=r["n_union"],
                    dn_union=r["dn_union"],
                    tipo_union=r["tipo_union"],
                    fecha_inicio=r["fecha_inicio"],
                    fecha_fin=r["fecha_fin"],
                )
                for r in group_records
            ]

            pd_total = sum(r["dn_union"] or 0 for r in group_records)

            # Derive otro_trabajador: if ARM match, show sol_worker; if SOLD, show arm_worker
            first_rec = group_records[0]
            if operacion == "ARM":
                otro = first_rec.get("sol_worker")
            else:  # SOLD
                otro = first_rec.get("arm_worker")
            otro_trabajador = otro if otro else "Pendiente"

            spool_groups.append(
                SpoolGroup(
                    tag_spool=tag_spool,
                    operacion=operacion,
                    uniones=uniones,
                    pd_total=pd_total,
                    otro_trabajador=otro_trabajador,
                )
            )

        # Step 6: Compute resumen
        total_uniones = sum(len(sg.uniones) for sg in spool_groups)
        pd_total_global = sum(sg.pd_total for sg in spool_groups)
        unique_spools = len({sg.tag_spool for sg in spool_groups})

        resumen = RegistroResumen(
            fecha=fecha,
            pd_total=pd_total_global,
            total_uniones=total_uniones,
            total_spools=unique_spools,
        )

        logger.info(
            f"GET /api/registro/{worker_id}: {worker_nombre} on {fecha} - "
            f"{total_uniones} uniones, {unique_spools} spools, {pd_total_global:.2f} PD"
        )

        return RegistroResponse(
            worker_id=worker_id,
            worker_nombre=worker_nombre,
            fecha=fecha,
            resumen=resumen,
            spools=spool_groups,
        )

    except HTTPException:
        raise
    except SheetsConnectionError as e:
        logger.error(f"Sheets connection error for worker {worker_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to read data: {str(e)}"
        )
    except Exception as e:
        logger.error(
            f"Unexpected error in get_registro for worker {worker_id}: {e}",
            exc_info=True,
        )
        raise HTTPException(
            status_code=500,
            detail=f"Internal server error: {str(e)}"
        )
