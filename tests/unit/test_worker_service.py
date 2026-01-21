"""
Tests unitarios para WorkerService.

Prueba operaciones CRUD de trabajadores y filtrado por activo.
Coverage objetivo: >80%
"""
import pytest
from unittest.mock import Mock

from backend.services.worker_service import WorkerService
from backend.repositories.sheets_repository import SheetsRepository
from backend.models.worker import Worker


# ==================== FIXTURES ====================

@pytest.fixture
def mock_sheets_repository(mocker):
    """Mock del repositorio de Google Sheets."""
    return mocker.Mock(spec=SheetsRepository)


@pytest.fixture
def worker_service(mock_sheets_repository):
    """Instancia de WorkerService con dependencias mockeadas."""
    return WorkerService(sheets_repository=mock_sheets_repository)


@pytest.fixture
def sample_workers_data():
    """
    Datos de prueba con trabajadores activos e inactivos (v2.0: con id).
    """
    from backend.models.role import RolTrabajador
    return [
        Worker(id=93, nombre="Juan", apellido="Pérez", rol=RolTrabajador.ARMADOR, activo=True),
        Worker(id=94, nombre="María", apellido="González", rol=RolTrabajador.SOLDADOR, activo=True),
        Worker(id=95, nombre="Pedro", apellido="López", rol=RolTrabajador.AYUDANTE, activo=False),  # Inactivo
        Worker(id=96, nombre="Ana", apellido="Martínez", rol=RolTrabajador.ARMADOR, activo=True),
        Worker(id=97, nombre="Carlos", apellido="Rodríguez", rol=RolTrabajador.SOLDADOR, activo=False),  # Inactivo
    ]


# ==================== TESTS: GET ALL ACTIVE WORKERS ====================

class TestGetAllActiveWorkers:
    """Tests para obtener todos los trabajadores activos."""

    def test_get_all_active_workers_returns_only_active(
        self,
        worker_service,
        mock_sheets_repository,
        sample_workers_data,
        mocker
    ):
        """get_all_active_workers retorna solo trabajadores activos."""
        # Mock repository
        mock_sheets_repository.read_worksheet.return_value = [
            ['Nombre', 'Apellido', 'Activo'],  # Header
            *[['row'] for _ in sample_workers_data]  # Data rows
        ]

        # Mock parser (v2.0: classmethod directo)
        mocker.patch(
            'backend.services.sheets_service.SheetsService.parse_worker_row',
            side_effect=sample_workers_data
        )

        # Ejecutar
        result = worker_service.get_all_active_workers()

        # Verificar: solo 3 activos (Juan, María, Ana)
        assert len(result) == 3
        assert all(w.activo for w in result)

        # Verificar nombres de activos
        nombres = [w.nombre for w in result]
        assert "Juan" in nombres
        assert "María" in nombres
        assert "Ana" in nombres
        assert "Pedro" not in nombres  # Inactivo
        assert "Carlos" not in nombres  # Inactivo

    def test_get_all_active_workers_excludes_inactive(
        self,
        worker_service,
        mock_sheets_repository,
        mocker
    ):
        """get_all_active_workers excluye trabajadores inactivos."""
        from backend.models.role import RolTrabajador
        workers = [
            Worker(id=95, nombre="Pedro", apellido="López", rol=RolTrabajador.AYUDANTE, activo=False),
            Worker(id=97, nombre="Carlos", apellido="Rodríguez", rol=RolTrabajador.SOLDADOR, activo=False),
        ]

        mock_sheets_repository.read_worksheet.return_value = [
            ['header'],
            *[['row'] for _ in workers]
        ]
        mocker.patch(
            'backend.services.sheets_service.SheetsService.parse_worker_row',
            side_effect=workers
        )

        # Ejecutar
        result = worker_service.get_all_active_workers()

        # Verificar: lista vacía (todos inactivos)
        assert len(result) == 0

    def test_get_all_active_workers_returns_empty_if_none(
        self,
        worker_service,
        mock_sheets_repository,
        mocker
    ):
        """get_all_active_workers retorna lista vacía si no hay trabajadores."""
        mock_sheets_repository.read_worksheet.return_value = [
            ['header']  # Solo header, sin datos
        ]
        mocker.patch(
            'backend.services.sheets_service.SheetsService.parse_worker_row',
            side_effect=[]
        )

        # Ejecutar
        result = worker_service.get_all_active_workers()

        # Verificar: lista vacía
        assert len(result) == 0
        assert isinstance(result, list)


# ==================== TESTS: FIND WORKER BY NOMBRE ====================

class TestFindWorkerByNombre:
    """Tests para búsqueda de trabajadores por nombre."""

    def test_find_worker_by_nombre_exact_match(
        self,
        worker_service,
        mock_sheets_repository,
        sample_workers_data,
        mocker
    ):
        """find_worker_by_nombre encuentra trabajador con nombre exacto."""
        mock_sheets_repository.read_worksheet.return_value = [
            ['header'],
            *[['row'] for _ in sample_workers_data]
        ]
        mocker.patch(
            'backend.services.sheets_service.SheetsService.parse_worker_row',
            side_effect=sample_workers_data
        )

        # Ejecutar búsqueda de Juan Pérez
        result = worker_service.find_worker_by_nombre("Juan Pérez")

        # Verificar
        assert result is not None
        assert result.nombre == "Juan"
        assert result.apellido == "Pérez"
        assert result.nombre_completo == "JP(93)"  # v2.1: Formato INICIALES(ID)

    def test_find_worker_by_nombre_case_insensitive(
        self,
        worker_service,
        mock_sheets_repository,
        mocker
    ):
        """find_worker_by_nombre funciona case-insensitive."""
        from backend.models.role import RolTrabajador
        worker = Worker(id=93, nombre="Juan", apellido="Pérez", rol=RolTrabajador.ARMADOR, activo=True)

        mock_sheets_repository.read_worksheet.return_value = [
            ['header'],
            ['row']
        ]
        mocker.patch(
            'backend.services.sheets_service.SheetsService.parse_worker_row',
            return_value=worker
        )

        # Ejecutar con diferentes combinaciones de mayúsculas
        result_lower = worker_service.find_worker_by_nombre("juan pérez")
        result_upper = worker_service.find_worker_by_nombre("JUAN PÉREZ")
        result_mixed = worker_service.find_worker_by_nombre("JuAn PéReZ")

        # Verificar: todos encuentran al trabajador
        assert result_lower is not None
        assert result_upper is not None
        assert result_mixed is not None

    def test_find_worker_by_nombre_with_whitespace(
        self,
        worker_service,
        mock_sheets_repository,
        mocker
    ):
        """find_worker_by_nombre normaliza espacios."""
        from backend.models.role import RolTrabajador
        worker = Worker(id=94, nombre="María", apellido="González", rol=RolTrabajador.SOLDADOR, activo=True)

        mock_sheets_repository.read_worksheet.return_value = [
            ['header'],
            ['row']
        ]
        mocker.patch(
            'backend.services.sheets_service.SheetsService.parse_worker_row',
            return_value=worker
        )

        # Ejecutar con espacios extra
        result = worker_service.find_worker_by_nombre("  María González  ")

        # Verificar: encuentra al trabajador
        assert result is not None
        assert result.nombre == "María"

    def test_find_worker_by_nombre_not_found_returns_none(
        self,
        worker_service,
        mock_sheets_repository,
        sample_workers_data,
        mocker
    ):
        """find_worker_by_nombre retorna None si no encuentra."""
        mock_sheets_repository.read_worksheet.return_value = [
            ['header'],
            *[['row'] for _ in sample_workers_data]
        ]
        mocker.patch(
            'backend.services.sheets_service.SheetsService.parse_worker_row',
            side_effect=sample_workers_data
        )

        # Ejecutar búsqueda de trabajador inexistente
        result = worker_service.find_worker_by_nombre("Trabajador Inexistente")

        # Verificar: retorna None
        assert result is None

    def test_find_worker_by_nombre_excludes_inactive_workers(
        self,
        worker_service,
        mock_sheets_repository,
        sample_workers_data,
        mocker
    ):
        """find_worker_by_nombre excluye trabajadores inactivos."""
        mock_sheets_repository.read_worksheet.return_value = [
            ['header'],
            *[['row'] for _ in sample_workers_data]
        ]
        mocker.patch(
            'backend.services.sheets_service.SheetsService.parse_worker_row',
            side_effect=sample_workers_data
        )

        # Ejecutar búsqueda de Pedro López (inactivo)
        result = worker_service.find_worker_by_nombre("Pedro López")

        # Verificar: retorna None (Pedro está inactivo)
        assert result is None

    def test_find_worker_by_nombre_only_searches_active(
        self,
        worker_service,
        mock_sheets_repository,
        mocker
    ):
        """find_worker_by_nombre solo busca entre trabajadores activos."""
        from backend.models.role import RolTrabajador
        workers = [
            Worker(id=93, nombre="Juan", apellido="Pérez", rol=RolTrabajador.ARMADOR, activo=True),  # Activo
            Worker(id=98, nombre="Juan", apellido="Pérez", rol=RolTrabajador.ARMADOR, activo=False),  # Inactivo (duplicado)
        ]

        mock_sheets_repository.read_worksheet.return_value = [
            ['header'],
            *[['row'] for _ in workers]
        ]
        mocker.patch(
            'backend.services.sheets_service.SheetsService.parse_worker_row',
            side_effect=workers
        )

        # Ejecutar
        result = worker_service.find_worker_by_nombre("Juan Pérez")

        # Verificar: encuentra solo el activo
        assert result is not None
        assert result.activo is True

    def test_find_worker_by_single_name_not_found(
        self,
        worker_service,
        mock_sheets_repository,
        sample_workers_data,
        mocker
    ):
        """find_worker_by_nombre con solo nombre (sin apellido) no encuentra."""
        mock_sheets_repository.read_worksheet.return_value = [
            ['header'],
            *[['row'] for _ in sample_workers_data]
        ]
        mocker.patch(
            'backend.services.sheets_service.SheetsService.parse_worker_row',
            side_effect=sample_workers_data
        )

        # Ejecutar búsqueda solo con nombre (sin apellido)
        result = worker_service.find_worker_by_nombre("Juan")

        # Verificar: no encuentra (debe ser nombre completo)
        assert result is None

    def test_find_worker_by_apellido_only_not_found(
        self,
        worker_service,
        mock_sheets_repository,
        sample_workers_data,
        mocker
    ):
        """find_worker_by_nombre con solo apellido no encuentra."""
        mock_sheets_repository.read_worksheet.return_value = [
            ['header'],
            *[['row'] for _ in sample_workers_data]
        ]
        mocker.patch(
            'backend.services.sheets_service.SheetsService.parse_worker_row',
            side_effect=sample_workers_data
        )

        # Ejecutar búsqueda solo con apellido
        result = worker_service.find_worker_by_nombre("Pérez")

        # Verificar: no encuentra (debe ser nombre completo)
        assert result is None
