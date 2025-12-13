"""
Unit tests for WorkerService v2.0 (find_worker_by_id method).

Tests worker_id-based lookups for v2.0 migration.
"""
import pytest
from unittest.mock import Mock
from backend.services.worker_service import WorkerService
from backend.repositories.sheets_repository import SheetsRepository
from backend.models.worker import Worker
from backend.exceptions import WorkerNoEncontradoError


@pytest.fixture
def mock_sheets_repository():
    """Mock SheetsRepository."""
    return Mock(spec=SheetsRepository)


@pytest.fixture
def worker_service(mock_sheets_repository):
    """WorkerService fixture with mocked repository."""
    return WorkerService(sheets_repository=mock_sheets_repository)


class TestFindWorkerById:
    """Tests for find_worker_by_id method (v2.0 feature)."""

    def test_find_worker_by_id_success(
        self, worker_service, mock_sheets_repository
    ):
        """Test finding worker by ID successfully."""
        from backend.models.role import RolTrabajador
        mock_worker = Worker(
            id=93,
            nombre="Mauricio",
            apellido="Rodriguez",
            rol=RolTrabajador.ARMADOR,
            activo=True
        )
        # Mock get_all_active_workers to return list with our worker
        worker_service.get_all_active_workers = Mock(return_value=[mock_worker])

        result = worker_service.find_worker_by_id(worker_id=93)

        assert result == mock_worker
        assert result.id == 93
        assert result.nombre == "Mauricio"
        assert result.apellido == "Rodriguez"

    def test_find_worker_by_id_not_found(
        self, worker_service, mock_sheets_repository
    ):
        """Test finding non-existent worker returns None."""
        # Mock get_all_active_workers to return empty list
        worker_service.get_all_active_workers = Mock(return_value=[])

        result = worker_service.find_worker_by_id(worker_id=999)

        # Method returns None, doesn't raise exception
        assert result is None

    def test_find_worker_by_id_inactive_worker(
        self, worker_service, mock_sheets_repository
    ):
        """Test finding inactive worker returns None (filtered out)."""
        # get_all_active_workers filters out inactive workers
        # So inactive worker won't be in the list
        worker_service.get_all_active_workers = Mock(return_value=[])

        result = worker_service.find_worker_by_id(worker_id=94)

        # Inactive workers are not returned by find_worker_by_id
        assert result is None

    def test_find_worker_by_id_calls_get_all_active_workers(
        self, worker_service, mock_sheets_repository
    ):
        """Test find_worker_by_id calls get_all_active_workers internally."""
        from backend.models.role import RolTrabajador
        mock_worker = Worker(
            id=95,
            nombre="Test",
            apellido="Worker",
            rol=RolTrabajador.SOLDADOR,
            activo=True
        )
        worker_service.get_all_active_workers = Mock(return_value=[mock_worker])

        worker_service.find_worker_by_id(worker_id=95)

        # Verify get_all_active_workers was called
        worker_service.get_all_active_workers.assert_called_once()


class TestFindWorkerByIdErrorHandling:
    """Tests for error handling in find_worker_by_id."""

    def test_find_worker_by_id_negative_id(
        self, worker_service, mock_sheets_repository
    ):
        """Test find_worker_by_id with negative ID returns None."""
        worker_service.get_all_active_workers = Mock(return_value=[])

        result = worker_service.find_worker_by_id(worker_id=-1)

        # Negative IDs just won't be found
        assert result is None

    def test_find_worker_by_id_zero_id(
        self, worker_service, mock_sheets_repository
    ):
        """Test find_worker_by_id with zero ID returns None."""
        worker_service.get_all_active_workers = Mock(return_value=[])

        result = worker_service.find_worker_by_id(worker_id=0)

        # Zero ID just won't be found
        assert result is None


class TestComparisonWithFindWorkerByNombre:
    """Tests comparing find_worker_by_id vs find_worker_by_nombre."""

    def test_find_by_id_vs_find_by_nombre_same_worker(
        self, worker_service, mock_sheets_repository
    ):
        """Test both methods return the same worker."""
        from backend.models.role import RolTrabajador
        mock_worker = Worker(
            id=93,
            nombre="Mauricio",
            apellido="Rodriguez",
            rol=RolTrabajador.ARMADOR,
            activo=True
        )

        # Both methods use get_all_active_workers internally
        worker_service.get_all_active_workers = Mock(return_value=[mock_worker])

        worker_by_id = worker_service.find_worker_by_id(worker_id=93)
        worker_by_nombre = worker_service.find_worker_by_nombre(
            nombre="Mauricio Rodriguez"
        )

        assert worker_by_id.id == worker_by_nombre.id
        assert worker_by_id.nombre == worker_by_nombre.nombre
        assert worker_by_id.apellido == worker_by_nombre.apellido

    def test_find_by_id_uses_integer_lookup(
        self, worker_service, mock_sheets_repository
    ):
        """Test find_by_id uses integer lookup (more efficient conceptually)."""
        from backend.models.role import RolTrabajador
        mock_worker = Worker(
            id=93,
            nombre="Mauricio",
            apellido="Rodriguez",
            rol=RolTrabajador.ARMADOR,
            activo=True
        )
        worker_service.get_all_active_workers = Mock(return_value=[mock_worker])

        # find_by_id uses integer lookup (more efficient)
        result = worker_service.find_worker_by_id(worker_id=93)

        assert result.id == 93
        # Verify it called get_all_active_workers
        worker_service.get_all_active_workers.assert_called_once()
