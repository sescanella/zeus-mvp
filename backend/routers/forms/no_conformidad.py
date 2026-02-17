"""
Router for No Conformidad (Non-Conformity) form endpoint.

POST /api/forms/no-conformidad
"""
from fastapi import APIRouter, Depends, status
from fastapi.responses import JSONResponse

from backend.models.no_conformidad import NoConformidadRequest, NoConformidadResponse
from backend.services.forms.no_conformidad_service import NoConformidadService
from backend.core.dependency import get_no_conformidad_service
from backend.exceptions import ZEUSException

router = APIRouter()


@router.post(
    "/no-conformidad",
    response_model=NoConformidadResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Registrar No Conformidad",
    description="Registra una No Conformidad (REG-QAC-002) para un spool.",
)
async def registrar_no_conformidad(
    request: NoConformidadRequest,
    service: NoConformidadService = Depends(get_no_conformidad_service),
):
    """Register a No Conformidad for a spool."""
    result = service.registrar(request)
    return NoConformidadResponse(**result)
