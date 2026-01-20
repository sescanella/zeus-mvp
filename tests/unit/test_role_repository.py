"""
Unit tests for RoleRepository (v2.0 multi-role system).

Tests multi-role queries, worker_has_role validation, and edge cases.
"""
import pytest
from unittest.mock import Mock, MagicMock
from backend.repositories.role_repository import RoleRepository
from backend.models.role import WorkerRole, RolTrabajador
from backend.exceptions import SheetsConnectionError


@pytest.fixture
def mock_spreadsheet():
    """Mock Google Spreadsheet."""
    return Mock()


@pytest.fixture
def mock_worksheet():
    """Mock worksheet with realistic multi-role data."""
    worksheet = Mock()
    # Header + 6 data rows
    # Worker 93: Armador, Soldador (2 roles)
    # Worker 94: Armador (1 role)
    # Worker 95: Soldador, Metrologia (2 roles)
    # Worker 96: Ayudante (1 role)
    # Worker 97: Revestimiento (inactive)
    worksheet.get_all_values.return_value = [
        ["Id", "Rol", "Activo"],  # Header
        ["93", "Armador", "TRUE"],
        ["93", "Soldador", "TRUE"],
        ["94", "Armador", "TRUE"],
        ["95", "Soldador", "TRUE"],
        ["95", "Metrologia", "TRUE"],
        ["96", "Ayudante", "TRUE"],
        ["97", "Revestimiento", "FALSE"],  # Inactive
    ]
    return worksheet


@pytest.fixture
def role_repository(mock_spreadsheet, mock_worksheet):
    """RoleRepository fixture with mocked Sheets."""
    mock_spreadsheet.worksheet.return_value = mock_worksheet
    return RoleRepository(mock_spreadsheet, hoja_nombre="Roles")


class TestRoleRepositoryInit:
    """Tests for RoleRepository initialization."""

    def test_init_success(self, mock_spreadsheet, mock_worksheet):
        """Test successful initialization with lazy loading."""
        mock_spreadsheet.worksheet.return_value = mock_worksheet
        repo = RoleRepository(mock_spreadsheet, hoja_nombre="Roles")

        # v2.0: Lazy loading - worksheet NOT loaded during __init__
        assert repo.spreadsheet == mock_spreadsheet
        assert repo.hoja_nombre == "Roles"
        assert repo._worksheet is None  # Not loaded yet
        mock_spreadsheet.worksheet.assert_not_called()  # No API call yet

    def test_init_hoja_no_encontrada(self, mock_spreadsheet):
        """Test lazy loading raises exception when Roles sheet not found."""
        import gspread
        mock_spreadsheet.worksheet.side_effect = gspread.exceptions.WorksheetNotFound("Worksheet not found")

        repo = RoleRepository(mock_spreadsheet, hoja_nombre="Roles")

        # v2.0: Lazy loading - exception raised when first method called
        with pytest.raises(SheetsConnectionError) as exc_info:
            repo.get_roles_by_worker_id(93)  # Triggers _get_worksheet()

        assert "Roles" in str(exc_info.value)


class TestGetRolesByWorkerId:
    """Tests for get_roles_by_worker_id method."""

    def test_get_roles_worker_with_multiple_roles(self, role_repository):
        """Test getting roles for worker with 2+ roles (Worker 93)."""
        roles = role_repository.get_roles_by_worker_id(worker_id=93)

        assert len(roles) == 2
        assert all(isinstance(r, WorkerRole) for r in roles)
        assert roles[0].id == 93
        assert roles[0].rol == RolTrabajador.ARMADOR
        assert roles[0].activo is True
        assert roles[1].id == 93
        assert roles[1].rol == RolTrabajador.SOLDADOR
        assert roles[1].activo is True

    def test_get_roles_worker_with_single_role(self, role_repository):
        """Test getting roles for worker with 1 role (Worker 94)."""
        roles = role_repository.get_roles_by_worker_id(worker_id=94)

        assert len(roles) == 1
        assert roles[0].id == 94
        assert roles[0].rol == RolTrabajador.ARMADOR
        assert roles[0].activo is True

    def test_get_roles_worker_not_found(self, role_repository):
        """Test getting roles for non-existent worker."""
        roles = role_repository.get_roles_by_worker_id(worker_id=999)

        assert len(roles) == 0

    def test_get_roles_excludes_inactive_roles(self, role_repository):
        """Test that inactive roles are excluded (Worker 97)."""
        roles = role_repository.get_roles_by_worker_id(worker_id=97)

        # Worker 97 has 1 role but it's inactive, so should return empty list
        assert len(roles) == 0


class TestGetWorkerRolesAsEnum:
    """Tests for get_worker_roles_as_enum method."""

    def test_get_enum_roles_multi_role_worker(self, role_repository):
        """Test getting enum roles for worker with multiple roles."""
        roles = role_repository.get_worker_roles_as_enum(worker_id=93)

        assert len(roles) == 2
        assert RolTrabajador.ARMADOR in roles
        assert RolTrabajador.SOLDADOR in roles
        assert RolTrabajador.METROLOGIA not in roles

    def test_get_enum_roles_single_role_worker(self, role_repository):
        """Test getting enum roles for worker with single role."""
        roles = role_repository.get_worker_roles_as_enum(worker_id=94)

        assert len(roles) == 1
        assert RolTrabajador.ARMADOR in roles

    def test_get_enum_roles_worker_not_found(self, role_repository):
        """Test getting enum roles for non-existent worker."""
        roles = role_repository.get_worker_roles_as_enum(worker_id=999)

        assert len(roles) == 0


class TestWorkerHasRole:
    """Tests for worker_has_role method."""

    def test_worker_has_role_true_armador(self, role_repository):
        """Test worker_has_role returns True for Armador (Worker 93)."""
        result = role_repository.worker_has_role(
            worker_id=93,
            rol=RolTrabajador.ARMADOR
        )

        assert result is True

    def test_worker_has_role_true_soldador(self, role_repository):
        """Test worker_has_role returns True for Soldador (Worker 93)."""
        result = role_repository.worker_has_role(
            worker_id=93,
            rol=RolTrabajador.SOLDADOR
        )

        assert result is True

    def test_worker_has_role_false_missing_role(self, role_repository):
        """Test worker_has_role returns False for missing role (Worker 94)."""
        result = role_repository.worker_has_role(
            worker_id=94,
            rol=RolTrabajador.SOLDADOR
        )

        assert result is False

    def test_worker_has_role_false_worker_not_found(self, role_repository):
        """Test worker_has_role returns False for non-existent worker."""
        result = role_repository.worker_has_role(
            worker_id=999,
            rol=RolTrabajador.ARMADOR
        )

        assert result is False

    def test_worker_has_role_false_inactive_role(self, role_repository):
        """Test worker_has_role returns False for inactive role (Worker 97)."""
        result = role_repository.worker_has_role(
            worker_id=97,
            rol=RolTrabajador.REVESTIMIENTO
        )

        assert result is False


class TestGetAllRoles:
    """Tests for get_all_roles method (admin feature)."""

    def test_get_all_roles_includes_all_roles(self, role_repository):
        """Test get_all_roles returns ALL roles (active and inactive)."""
        all_roles = role_repository.get_all_roles()

        # Should return 7 roles total (including Worker 97's inactive role)
        assert len(all_roles) == 7
        assert all(isinstance(r, WorkerRole) for r in all_roles)
        # Should include both active and inactive
        active_count = sum(1 for r in all_roles if r.activo)
        inactive_count = sum(1 for r in all_roles if not r.activo)
        assert active_count == 6
        assert inactive_count == 1

    def test_get_all_roles_correct_distribution(self, role_repository):
        """Test get_all_roles returns correct role distribution."""
        all_roles = role_repository.get_all_roles()

        # Count roles by type
        armador_count = sum(1 for r in all_roles if r.rol == RolTrabajador.ARMADOR)
        soldador_count = sum(1 for r in all_roles if r.rol == RolTrabajador.SOLDADOR)
        metrologia_count = sum(1 for r in all_roles if r.rol == RolTrabajador.METROLOGIA)
        ayudante_count = sum(1 for r in all_roles if r.rol == RolTrabajador.AYUDANTE)

        assert armador_count == 2  # Workers 93, 94
        assert soldador_count == 2  # Workers 93, 95
        assert metrologia_count == 1  # Worker 95
        assert ayudante_count == 1  # Worker 96


class TestEdgeCases:
    """Tests for edge cases and error handling."""

    def test_empty_roles_sheet(self, mock_spreadsheet):
        """Test handling of empty Roles sheet (only header)."""
        mock_worksheet = Mock()
        mock_worksheet.get_all_values.return_value = [
            ["Id", "Rol", "Activo"]  # Only header
        ]
        mock_spreadsheet.worksheet.return_value = mock_worksheet

        repo = RoleRepository(mock_spreadsheet, hoja_nombre="Roles")
        roles = repo.get_roles_by_worker_id(worker_id=93)

        assert len(roles) == 0

    def test_malformed_row_missing_columns(self, mock_spreadsheet):
        """Test handling of malformed rows (missing columns)."""
        mock_worksheet = Mock()
        mock_worksheet.get_all_values.return_value = [
            ["Id", "Rol", "Activo"],
            ["93", "Armador"],  # Missing Activo column
            ["94", "Soldador", "TRUE"],  # Valid row
        ]
        mock_spreadsheet.worksheet.return_value = mock_worksheet

        repo = RoleRepository(mock_spreadsheet, hoja_nombre="Roles")
        roles = repo.get_roles_by_worker_id(worker_id=93)

        # Should skip malformed row and only return valid rows
        assert len(roles) == 0  # Worker 93's row is malformed

    def test_invalid_rol_value_is_skipped(self, mock_spreadsheet):
        """Test handling of invalid rol value (skipped gracefully with warning)."""
        mock_worksheet = Mock()
        mock_worksheet.get_all_values.return_value = [
            ["Id", "Rol", "Activo"],
            ["93", "InvalidRole", "TRUE"],  # Invalid role - should be skipped
        ]
        mock_spreadsheet.worksheet.return_value = mock_worksheet

        repo = RoleRepository(mock_spreadsheet, hoja_nombre="Roles")

        # Should skip invalid row and return empty list
        roles = repo.get_roles_by_worker_id(worker_id=93)
        assert len(roles) == 0

    def test_non_numeric_worker_id_is_skipped(self, mock_spreadsheet):
        """Test handling of non-numeric worker ID (skipped gracefully with warning)."""
        mock_worksheet = Mock()
        mock_worksheet.get_all_values.return_value = [
            ["Id", "Rol", "Activo"],
            ["ABC", "Armador", "TRUE"],  # Non-numeric ID - should be skipped
        ]
        mock_spreadsheet.worksheet.return_value = mock_worksheet

        repo = RoleRepository(mock_spreadsheet, hoja_nombre="Roles")

        # Should skip invalid row and return empty list
        roles = repo.get_roles_by_worker_id(worker_id=93)
        assert len(roles) == 0
