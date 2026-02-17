"""
Service for No Conformidad (Non-Conformity) form business logic.

Validates worker, builds row, appends to NoConformidad sheet.
"""
import uuid
import logging

from backend.models.no_conformidad import NoConformidadRequest
from backend.repositories.forms_repository import FormsRepository
from backend.services.worker_service import WorkerService
from backend.utils.date_formatter import now_chile, format_datetime_for_sheets
from backend.exceptions import WorkerNoEncontradoError


class NoConformidadService:
    """Business logic for No Conformidad registration."""

    def __init__(
        self,
        forms_repo: FormsRepository,
        worker_service: WorkerService,
    ):
        self.forms_repo = forms_repo
        self.worker_service = worker_service
        self.logger = logging.getLogger(__name__)

    def registrar(self, request: NoConformidadRequest) -> dict:
        """
        Register a No Conformidad entry.

        1. Validate worker exists
        2. Generate UUID
        3. Build row with Chile timestamp
        4. Append to sheet

        Returns:
            dict with success, message, registro_id, tag_spool
        """
        # 1. Validate worker
        worker = self.worker_service.find_worker_by_id(request.worker_id)
        if not worker:
            raise WorkerNoEncontradoError(str(request.worker_id))

        # 2. Generate ID
        registro_id = str(uuid.uuid4())

        # 3. Build row
        timestamp = format_datetime_for_sheets(now_chile())
        row_data = [
            registro_id,
            timestamp,
            request.tag_spool,
            request.worker_id,
            worker.nombre_completo,
            request.origen,
            request.tipo,
            request.descripcion,
        ]

        # 4. Append
        self.forms_repo.append_no_conformidad(row_data)

        self.logger.info(
            f"No Conformidad registered: {registro_id} "
            f"for spool {request.tag_spool} by worker {worker.nombre_completo}"
        )

        return {
            "success": True,
            "message": f"No Conformidad registrada para spool {request.tag_spool}",
            "registro_id": registro_id,
            "tag_spool": request.tag_spool,
        }
