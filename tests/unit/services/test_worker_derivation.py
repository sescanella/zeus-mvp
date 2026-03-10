"""
Unit tests for worker_nombre derivation from worker_id (task 0.7).

Tests that IniciarRequest and FinalizarRequest accept worker_nombre=None
and that OccupationService derives it from WorkerService when not provided.

Requirements:
- IniciarRequest.worker_nombre is now Optional (backward compat: still works when provided)
- FinalizarRequest.worker_nombre is now Optional
- When worker_nombre=None, OccupationService calls worker_service.find_worker_by_id()
- When worker_nombre is provided, no derivation call is made
- When worker_id not found, an error is raised

Reference: .planning/phases/00-backend-nuevos-endpoints/00-03-PLAN.md (Task 2)
"""
import pytest
from unittest.mock import AsyncMock, MagicMock
from datetime import datetime, date

from backend.services.occupation_service import OccupationService
from backend.models.occupation import (
    IniciarRequest,
    FinalizarRequest,
    OccupationResponse
)
from backend.models.spool import Spool
from backend.models.worker import Worker
from backend.models.union import Union
from backend.exceptions import SpoolNoEncontradoError


# ============================================================================
# FIXTURES
# ============================================================================

def make_worker(worker_id: int = 93, nombre: str = "Mauricio", apellido: str = "Rodriguez") -> Worker:
    """Create a test Worker object."""
    return Worker(
        id=worker_id,
        nombre=nombre,
        apellido=apellido,
        rol="Armador",
        roles=[],
        activo=True
    )


def make_union(n: int) -> Union:
    return Union(
        id=f"OT-200+{n}",
        ot="200",
        tag_spool="WORKER-SPOOL",
        n_union=n,
        dn_union=2.5,
        tipo_union="BW",
        arm_fecha_inicio=None,
        arm_fecha_fin=None,
        arm_worker=None,
        sol_fecha_inicio=None,
        sol_fecha_fin=None,
        sol_worker=None,
        ndt_fecha=None,
        ndt_status=None,
        version="uuid-w",
        creado_por="SYSTEM(0)",
        fecha_creacion=datetime(2026, 1, 1)
    )


@pytest.fixture
def mock_sheets_repo():
    repo = MagicMock()
    mock_spool = MagicMock(spec=Spool)
    mock_spool.tag_spool = "WORKER-SPOOL"
    mock_spool.ot = "200"
    mock_spool.total_uniones = 3  # v4.0
    mock_spool.fecha_materiales = date(2026, 1, 15)
    mock_spool.fecha_armado = None
    mock_spool.fecha_soldadura = None
    mock_spool.armador = None
    mock_spool.soldador = None
    mock_spool.ocupado_por = "MR(93)"
    mock_spool.fecha_ocupacion = "10-03-2026 08:00:00"

    repo.get_spool_by_tag = MagicMock(return_value=mock_spool)

    mock_headers = [
        "TAG_SPOOL", "OT", "NV", "Fecha_Materiales", "Fecha_Armado", "Armador",
        "Fecha_Soldadura", "Soldador", "Ocupado_Por", "Fecha_Ocupacion",
        "version", "Estado_Detalle", "Total_Uniones"
    ]
    repo.read_worksheet = MagicMock(return_value=[mock_headers])
    repo.find_row_by_column_value = MagicMock(return_value=2)
    repo.batch_update_by_column_name = MagicMock()
    repo._index_to_column_letter = MagicMock(return_value="A")
    return repo


@pytest.fixture
def mock_union_repo():
    repo = MagicMock()
    unions = [make_union(i) for i in range(1, 4)]
    repo.get_disponibles_arm_by_ot = MagicMock(return_value=unions)
    repo.batch_update_arm_full = MagicMock(return_value=2)
    repo.get_by_ids = MagicMock(return_value=unions[:2])
    return repo


@pytest.fixture
def mock_metadata_repo():
    repo = MagicMock()
    repo.log_event = MagicMock()
    return repo


@pytest.fixture
def mock_conflict_service():
    service = MagicMock()
    service.update_with_retry = AsyncMock(return_value="v2")
    return service


@pytest.fixture
def mock_worker_service():
    """WorkerService mock that returns a Worker for id=93."""
    service = MagicMock()
    service.find_worker_by_id = MagicMock(return_value=make_worker(93))
    return service


@pytest.fixture
def occupation_service_with_worker(
    mock_sheets_repo, mock_union_repo, mock_metadata_repo,
    mock_conflict_service, mock_worker_service
):
    """OccupationService with WorkerService injected."""
    return OccupationService(
        sheets_repository=mock_sheets_repo,
        metadata_repository=mock_metadata_repo,
        conflict_service=mock_conflict_service,
        union_repository=mock_union_repo,
        worker_service=mock_worker_service
    )


@pytest.fixture
def occupation_service_no_worker(
    mock_sheets_repo, mock_union_repo, mock_metadata_repo, mock_conflict_service
):
    """OccupationService WITHOUT WorkerService injected."""
    return OccupationService(
        sheets_repository=mock_sheets_repo,
        metadata_repository=mock_metadata_repo,
        conflict_service=mock_conflict_service,
        union_repository=mock_union_repo
    )


# ============================================================================
# MODEL VALIDATION TESTS: IniciarRequest
# ============================================================================

class TestIniciarRequestWorkerNombreOptional:
    """Tests for IniciarRequest.worker_nombre being optional."""

    def test_worker_nombre_none_accepted(self):
        """IniciarRequest accepts worker_nombre=None."""
        req = IniciarRequest(
            tag_spool="WORKER-SPOOL",
            worker_id=93,
            worker_nombre=None,
            operacion="ARM"
        )
        assert req.worker_nombre is None

    def test_worker_nombre_string_still_works(self):
        """IniciarRequest with worker_nombre string is backward compatible."""
        req = IniciarRequest(
            tag_spool="WORKER-SPOOL",
            worker_id=93,
            worker_nombre="MR(93)",
            operacion="ARM"
        )
        assert req.worker_nombre == "MR(93)"

    def test_worker_nombre_omitted_defaults_to_none(self):
        """IniciarRequest without worker_nombre defaults to None."""
        req = IniciarRequest(
            tag_spool="WORKER-SPOOL",
            worker_id=93,
            operacion="ARM"
        )
        assert req.worker_nombre is None


# ============================================================================
# MODEL VALIDATION TESTS: FinalizarRequest
# ============================================================================

class TestFinalizarRequestWorkerNombreOptional:
    """Tests for FinalizarRequest.worker_nombre being optional."""

    def test_worker_nombre_none_accepted(self):
        """FinalizarRequest accepts worker_nombre=None."""
        req = FinalizarRequest(
            tag_spool="WORKER-SPOOL",
            worker_id=93,
            worker_nombre=None,
            operacion="ARM",
            selected_unions=["OT-200+1"]
        )
        assert req.worker_nombre is None

    def test_worker_nombre_string_still_works(self):
        """FinalizarRequest with worker_nombre string is backward compatible."""
        req = FinalizarRequest(
            tag_spool="WORKER-SPOOL",
            worker_id=93,
            worker_nombre="MR(93)",
            operacion="ARM",
            selected_unions=["OT-200+1"]
        )
        assert req.worker_nombre == "MR(93)"


# ============================================================================
# SERVICE TESTS: iniciar_spool() derivation
# ============================================================================

class TestIniciarWorkerDerivation:
    """Tests for worker_nombre derivation in iniciar_spool()."""

    @pytest.mark.asyncio
    async def test_iniciar_with_none_nombre_calls_worker_service(
        self, occupation_service_with_worker, mock_worker_service
    ):
        """iniciar_spool with worker_nombre=None calls find_worker_by_id."""
        request = IniciarRequest(
            tag_spool="WORKER-SPOOL",
            worker_id=93,
            worker_nombre=None,
            operacion="ARM"
        )

        result = await occupation_service_with_worker.iniciar_spool(request)

        mock_worker_service.find_worker_by_id.assert_called_once_with(93)

    @pytest.mark.asyncio
    async def test_iniciar_with_nombre_provided_skips_worker_service(
        self, occupation_service_with_worker, mock_worker_service
    ):
        """iniciar_spool with worker_nombre provided does NOT call find_worker_by_id."""
        request = IniciarRequest(
            tag_spool="WORKER-SPOOL",
            worker_id=93,
            worker_nombre="MR(93)",
            operacion="ARM"
        )

        result = await occupation_service_with_worker.iniciar_spool(request)

        mock_worker_service.find_worker_by_id.assert_not_called()

    @pytest.mark.asyncio
    async def test_iniciar_derives_nombre_completo_format(
        self, occupation_service_with_worker, mock_sheets_repo
    ):
        """iniciar_spool uses Worker.nombre_completo (INICIALES(ID) format)."""
        # Worker.nombre_completo for Mauricio Rodriguez = "MR(93)"
        request = IniciarRequest(
            tag_spool="WORKER-SPOOL",
            worker_id=93,
            worker_nombre=None,
            operacion="ARM"
        )

        result = await occupation_service_with_worker.iniciar_spool(request)

        # Verify Sheets write used the derived nombre "MR(93)"
        mock_sheets_repo.batch_update_by_column_name.assert_called()
        call_args = mock_sheets_repo.batch_update_by_column_name.call_args
        updates = call_args[1]["updates"] if "updates" in call_args[1] else call_args[0][1]
        ocupado_por_values = [u["value"] for u in updates if u["column_name"] == "Ocupado_Por"]
        assert len(ocupado_por_values) > 0
        assert "MR(93)" in ocupado_por_values[0]

    @pytest.mark.asyncio
    async def test_iniciar_with_none_nombre_and_unknown_worker_raises_error(
        self, occupation_service_with_worker, mock_worker_service
    ):
        """iniciar_spool raises error when worker_id not found."""
        mock_worker_service.find_worker_by_id = MagicMock(return_value=None)

        request = IniciarRequest(
            tag_spool="WORKER-SPOOL",
            worker_id=999,
            worker_nombre=None,
            operacion="ARM"
        )

        with pytest.raises(SpoolNoEncontradoError):
            await occupation_service_with_worker.iniciar_spool(request)


# ============================================================================
# SERVICE TESTS: finalizar_spool() derivation
# ============================================================================

class TestFinalizarWorkerDerivation:
    """Tests for worker_nombre derivation in finalizar_spool()."""

    @pytest.mark.asyncio
    async def test_finalizar_with_none_nombre_calls_worker_service(
        self, occupation_service_with_worker, mock_worker_service
    ):
        """finalizar_spool with worker_nombre=None calls find_worker_by_id."""
        request = FinalizarRequest(
            tag_spool="WORKER-SPOOL",
            worker_id=93,
            worker_nombre=None,
            operacion="ARM",
            selected_unions=["OT-200+1", "OT-200+2"]
        )

        result = await occupation_service_with_worker.finalizar_spool(request)

        mock_worker_service.find_worker_by_id.assert_called_once_with(93)

    @pytest.mark.asyncio
    async def test_finalizar_with_nombre_provided_skips_worker_service(
        self, occupation_service_with_worker, mock_worker_service
    ):
        """finalizar_spool with worker_nombre provided does NOT call find_worker_by_id."""
        request = FinalizarRequest(
            tag_spool="WORKER-SPOOL",
            worker_id=93,
            worker_nombre="MR(93)",
            operacion="ARM",
            selected_unions=["OT-200+1", "OT-200+2"]
        )

        result = await occupation_service_with_worker.finalizar_spool(request)

        mock_worker_service.find_worker_by_id.assert_not_called()

    @pytest.mark.asyncio
    async def test_finalizar_with_none_nombre_and_unknown_worker_raises_error(
        self, occupation_service_with_worker, mock_worker_service
    ):
        """finalizar_spool raises error when worker_id not found during derivation."""
        mock_worker_service.find_worker_by_id = MagicMock(return_value=None)

        request = FinalizarRequest(
            tag_spool="WORKER-SPOOL",
            worker_id=999,
            worker_nombre=None,
            operacion="ARM",
            selected_unions=["OT-200+1"]
        )

        with pytest.raises(SpoolNoEncontradoError):
            await occupation_service_with_worker.finalizar_spool(request)
