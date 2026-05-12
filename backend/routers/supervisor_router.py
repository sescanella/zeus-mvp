"""
Supervisor Router — server-side tracking list + audit log.

Endpoints (montados con prefix /api/supervisor):
- GET  /list              — lista los spools que Matías está siguiendo
- POST /list/add          — agrega un TAG_SPOOL a la lista (upsert idempotente)
- POST /list/remove       — quita un TAG_SPOOL de la lista
- POST /audit/batch       — append batched UI events (max 100/request)
- GET  /audit?since=ISO   — read audit events desde un timestamp (debug)
- POST /legacy-snapshot   — Capa 0: dump verbatim de localStorage durante migración

Single-user (Matías). No auth — mismo threat model que el resto de ZEUES.

Errores:
- ValueError del service → HTTP 400 (validación: tag vacío, session_id vacío).
  Atrapado explícitamente acá; no se delega al handler global.
- SheetsConnectionError / SheetsUpdateError del service/repo → HTTP 503, mapeado
  por el handler global en main.py.
- Pydantic validation errors → HTTP 422 (FastAPI default).
"""
import logging
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field

from backend.core.dependency import get_supervisor_service
from backend.models.supervisor import (
    AuditEvent,
    AuditEventBatch,
    LegacySnapshot,
    TrackedSpool,
)
from backend.services.supervisor_service import SupervisorService

logger = logging.getLogger(__name__)
router = APIRouter()


# ─── Request / response models ──────────────────────────────────────────────


class TrackedSpoolListResponse(BaseModel):
    items: list[TrackedSpool]


class ListAddRequest(BaseModel):
    tag_spool: str = Field(..., min_length=1)
    session_id: str = Field(..., min_length=1)


class ListMutateResponse(BaseModel):
    item: TrackedSpool


class ListRemoveRequest(BaseModel):
    tag_spool: str = Field(..., min_length=1)
    session_id: str = Field(..., min_length=1)


class ListRemoveResponse(BaseModel):
    removed: bool
    tag_spool: str


class AuditBatchResponse(BaseModel):
    appended: int


class AuditListResponse(BaseModel):
    events: list[AuditEvent]


class LegacySnapshotResponse(BaseModel):
    snapshot_id: str
    written: bool  # False si snapshot_id ya estaba (idempotent retry)


# ─── Endpoints ──────────────────────────────────────────────────────────────


@router.get("/list", response_model=TrackedSpoolListResponse)
async def get_list(
    svc: SupervisorService = Depends(get_supervisor_service),
):
    """Lista actual de spools que Matías está siguiendo."""
    items = svc.list_tracked_spools()
    return TrackedSpoolListResponse(items=items)


@router.post("/list/add", response_model=ListMutateResponse)
async def add_to_list(
    req: ListAddRequest,
    svc: SupervisorService = Depends(get_supervisor_service),
):
    """
    Agrega (o re-agrega, idempotente) un spool a la lista.

    Si el TAG ya estaba, su fila se actualiza con timestamp fresco.
    Emite un evento LIST_ADD al audit.
    """
    logger.info(
        f"POST /api/supervisor/list/add tag={req.tag_spool!r} "
        f"session={req.session_id[:8]}..."
    )
    try:
        item = svc.add_to_list(req.tag_spool, req.session_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return ListMutateResponse(item=item)


@router.post("/list/remove", response_model=ListRemoveResponse)
async def remove_from_list(
    req: ListRemoveRequest,
    svc: SupervisorService = Depends(get_supervisor_service),
):
    """
    Quita un spool de la lista. Idempotente.

    Si el TAG no estaba, devuelve {removed: false, tag_spool} con HTTP 200
    para no romper la UX optimista del frontend (el card ya fue removido).
    """
    logger.info(
        f"POST /api/supervisor/list/remove tag={req.tag_spool!r} "
        f"session={req.session_id[:8]}..."
    )
    try:
        removed = svc.remove_from_list(req.tag_spool, req.session_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return ListRemoveResponse(removed=removed, tag_spool=req.tag_spool)


@router.post("/audit/batch", response_model=AuditBatchResponse)
async def audit_batch(
    batch: AuditEventBatch,
    svc: SupervisorService = Depends(get_supervisor_service),
):
    """
    Append batched UI events (max 100 por request).

    Idempotente por AuditEvent.id — el repo deduplica antes de escribir.
    Devuelve cantidad efectivamente appendeada (post-dedup).
    """
    logger.info(
        f"POST /api/supervisor/audit/batch events_count={len(batch.events)}"
    )
    appended = svc.record_audit_batch(batch.events)
    return AuditBatchResponse(appended=appended)


@router.get("/audit", response_model=AuditListResponse)
async def get_audit(
    since: datetime = Query(
        ...,
        description="ISO 8601 timestamp; devuelve eventos con timestamp >= since",
    ),
    svc: SupervisorService = Depends(get_supervisor_service),
):
    """Endpoint de debug — lee eventos desde un timestamp dado."""
    logger.info(f"GET /api/supervisor/audit since={since.isoformat()}")
    events = svc.get_audit_since(since)
    return AuditListResponse(events=events)


@router.post("/legacy-snapshot", response_model=LegacySnapshotResponse)
async def legacy_snapshot(
    snapshot: LegacySnapshot,
    svc: SupervisorService = Depends(get_supervisor_service),
):
    """
    Capa 0 de migración — guarda verbatim el contenido de localStorage.

    Idempotente por snapshot_id. Si la fila ya existe (retry / multi-tab),
    devuelve {snapshot_id, written: false}.
    """
    logger.info(
        f"POST /api/supervisor/legacy-snapshot snapshot_id={snapshot.snapshot_id} "
        f"raw_len={len(snapshot.raw)}"
    )
    written = svc.record_legacy_snapshot(snapshot)
    return LegacySnapshotResponse(
        snapshot_id=snapshot.snapshot_id,
        written=written,
    )
