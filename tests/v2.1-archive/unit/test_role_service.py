"""
Unit tests for RoleService (v2.0 role validation).

Tests role validation for operations, obtener_roles_worker, and error handling.
"""
import pytest
from unittest.mock import Mock
from backend.services.role_service import RoleService
from backend.repositories.role_repository import RoleRepository
from backend.models.role import WorkerRole, RolTrabajador
from backend.exceptions import RolNoAutorizadoError


@pytest.fixture
def mock_role_repository():
    """Mock RoleRepository."""
    return Mock(spec=RoleRepository)


@pytest.fixture
def role_service(mock_role_repository):
    """RoleService fixture with mocked repository."""
    return RoleService(role_repository=mock_role_repository)


class TestValidarWorkerTieneRolParaOperacion:
    """Tests for validar_worker_tiene_rol_para_operacion method."""

    def test_validar_arm_success_worker_es_armador(
        self, role_service, mock_role_repository
    ):
        """Test ARM validation succeeds when worker has Armador role."""
        mock_role_repository.worker_has_role.return_value = True

        # Should not raise
        role_service.validar_worker_tiene_rol_para_operacion(
            worker_id=93,
            operacion="ARM"
        )

        mock_role_repository.worker_has_role.assert_called_once_with(
            93, RolTrabajador.ARMADOR
        )

    def test_validar_sold_success_worker_es_soldador(
        self, role_service, mock_role_repository
    ):
        """Test SOLD validation succeeds when worker has Soldador role."""
        mock_role_repository.worker_has_role.return_value = True

        # Should not raise
        role_service.validar_worker_tiene_rol_para_operacion(
            worker_id=94,
            operacion="SOLD"
        )

        mock_role_repository.worker_has_role.assert_called_once_with(
            94, RolTrabajador.SOLDADOR
        )

    def test_validar_metrologia_success_worker_es_metrologia(
        self, role_service, mock_role_repository
    ):
        """Test METROLOGIA validation succeeds when worker has Metrologia role."""
        mock_role_repository.worker_has_role.return_value = True

        # Should not raise
        role_service.validar_worker_tiene_rol_para_operacion(
            worker_id=95,
            operacion="METROLOGIA"
        )

        mock_role_repository.worker_has_role.assert_called_once_with(
            95, RolTrabajador.METROLOGIA
        )

    def test_validar_arm_failure_worker_no_es_armador(
        self, role_service, mock_role_repository
    ):
        """Test ARM validation fails when worker doesn't have Armador role."""
        mock_role_repository.worker_has_role.return_value = False
        mock_role_repository.get_worker_roles_as_enum.return_value = [
            RolTrabajador.SOLDADOR
        ]

        with pytest.raises(RolNoAutorizadoError) as exc_info:
            role_service.validar_worker_tiene_rol_para_operacion(
                worker_id=94,
                operacion="ARM"
            )

        error = exc_info.value
        assert error.data["worker_id"] == 94
        assert error.data["operacion"] == "ARM"
        assert error.data["rol_requerido"] == "Armador"
        assert error.data["roles_actuales"] == ["Soldador"]

    def test_validar_sold_failure_worker_no_es_soldador(
        self, role_service, mock_role_repository
    ):
        """Test SOLD validation fails when worker doesn't have Soldador role."""
        mock_role_repository.worker_has_role.return_value = False
        mock_role_repository.get_worker_roles_as_enum.return_value = [
            RolTrabajador.ARMADOR
        ]

        with pytest.raises(RolNoAutorizadoError) as exc_info:
            role_service.validar_worker_tiene_rol_para_operacion(
                worker_id=93,
                operacion="SOLD"
            )

        error = exc_info.value
        assert error.data["worker_id"] == 93
        assert error.data["operacion"] == "SOLD"
        assert error.data["rol_requerido"] == "Soldador"

    def test_validar_operacion_invalida_raises_value_error(
        self, role_service, mock_role_repository
    ):
        """Test validation fails for invalid operation."""
        with pytest.raises(ValueError) as exc_info:
            role_service.validar_worker_tiene_rol_para_operacion(
                worker_id=93,
                operacion="INVALID_OP"
            )

        assert "INVALID_OP" in str(exc_info.value)
        assert "no reconocida" in str(exc_info.value)

    def test_validar_operacion_case_insensitive(
        self, role_service, mock_role_repository
    ):
        """Test validation works with lowercase operation names."""
        mock_role_repository.worker_has_role.return_value = True

        # Should not raise
        role_service.validar_worker_tiene_rol_para_operacion(
            worker_id=93,
            operacion="arm"  # lowercase
        )

        mock_role_repository.worker_has_role.assert_called_once_with(
            93, RolTrabajador.ARMADOR
        )

    def test_validar_worker_sin_roles_raises_error(
        self, role_service, mock_role_repository
    ):
        """Test validation fails when worker has no roles at all."""
        mock_role_repository.worker_has_role.return_value = False
        mock_role_repository.get_worker_roles_as_enum.return_value = []

        with pytest.raises(RolNoAutorizadoError) as exc_info:
            role_service.validar_worker_tiene_rol_para_operacion(
                worker_id=96,
                operacion="ARM"
            )

        error = exc_info.value
        assert error.data["worker_id"] == 96
        assert error.data["roles_actuales"] == []  # Empty list, not None


class TestObtenerRolesWorker:
    """Tests for obtener_roles_worker method."""

    def test_obtener_roles_worker_with_multiple_roles(
        self, role_service, mock_role_repository
    ):
        """Test getting roles for worker with 2+ roles."""
        mock_role_repository.get_worker_roles_as_enum.return_value = [
            RolTrabajador.ARMADOR,
            RolTrabajador.SOLDADOR
        ]

        roles = role_service.obtener_roles_worker(worker_id=93)

        assert len(roles) == 2
        assert RolTrabajador.ARMADOR in roles
        assert RolTrabajador.SOLDADOR in roles
        mock_role_repository.get_worker_roles_as_enum.assert_called_once_with(93)

    def test_obtener_roles_worker_with_single_role(
        self, role_service, mock_role_repository
    ):
        """Test getting roles for worker with 1 role."""
        mock_role_repository.get_worker_roles_as_enum.return_value = [
            RolTrabajador.ARMADOR
        ]

        roles = role_service.obtener_roles_worker(worker_id=94)

        assert len(roles) == 1
        assert RolTrabajador.ARMADOR in roles

    def test_obtener_roles_worker_not_found(
        self, role_service, mock_role_repository
    ):
        """Test getting roles for non-existent worker returns empty list."""
        mock_role_repository.get_worker_roles_as_enum.return_value = []

        roles = role_service.obtener_roles_worker(worker_id=999)

        assert len(roles) == 0


class TestOperacionToRolMapping:
    """Tests for operacion → rol mapping."""

    def test_mapping_arm_to_armador(self, role_service, mock_role_repository):
        """Test ARM operation maps to Armador role."""
        mock_role_repository.worker_has_role.return_value = True

        role_service.validar_worker_tiene_rol_para_operacion(
            worker_id=93,
            operacion="ARM"
        )

        # Verify it checked for Armador role
        mock_role_repository.worker_has_role.assert_called_once_with(
            93, RolTrabajador.ARMADOR
        )

    def test_mapping_sold_to_soldador(self, role_service, mock_role_repository):
        """Test SOLD operation maps to Soldador role."""
        mock_role_repository.worker_has_role.return_value = True

        role_service.validar_worker_tiene_rol_para_operacion(
            worker_id=94,
            operacion="SOLD"
        )

        # Verify it checked for Soldador role
        mock_role_repository.worker_has_role.assert_called_once_with(
            94, RolTrabajador.SOLDADOR
        )

    def test_mapping_metrologia_to_metrologia(
        self, role_service, mock_role_repository
    ):
        """Test METROLOGIA operation maps to Metrologia role."""
        mock_role_repository.worker_has_role.return_value = True

        role_service.validar_worker_tiene_rol_para_operacion(
            worker_id=95,
            operacion="METROLOGIA"
        )

        # Verify it checked for Metrologia role
        mock_role_repository.worker_has_role.assert_called_once_with(
            95, RolTrabajador.METROLOGIA
        )


class TestRolNoAutorizadoErrorDetails:
    """Tests for RolNoAutorizadoError exception details."""

    def test_error_contains_worker_id(
        self, role_service, mock_role_repository
    ):
        """Test error message contains worker_id."""
        mock_role_repository.worker_has_role.return_value = False
        mock_role_repository.get_worker_roles_as_enum.return_value = [
            RolTrabajador.SOLDADOR
        ]

        with pytest.raises(RolNoAutorizadoError) as exc_info:
            role_service.validar_worker_tiene_rol_para_operacion(
                worker_id=94,
                operacion="ARM"
            )

        error = exc_info.value
        assert error.data["worker_id"] == 94
        assert "94" in str(error)

    def test_error_contains_operacion(
        self, role_service, mock_role_repository
    ):
        """Test error message contains operation name."""
        mock_role_repository.worker_has_role.return_value = False
        mock_role_repository.get_worker_roles_as_enum.return_value = []

        with pytest.raises(RolNoAutorizadoError) as exc_info:
            role_service.validar_worker_tiene_rol_para_operacion(
                worker_id=94,
                operacion="ARM"
            )

        error = exc_info.value
        assert error.data["operacion"] == "ARM"
        assert "ARM" in str(error)

    def test_error_contains_rol_requerido(
        self, role_service, mock_role_repository
    ):
        """Test error message contains required role."""
        mock_role_repository.worker_has_role.return_value = False
        mock_role_repository.get_worker_roles_as_enum.return_value = []

        with pytest.raises(RolNoAutorizadoError) as exc_info:
            role_service.validar_worker_tiene_rol_para_operacion(
                worker_id=94,
                operacion="ARM"
            )

        error = exc_info.value
        assert error.data["rol_requerido"] == "Armador"
        assert "Armador" in str(error)

    def test_error_contains_roles_actuales_when_present(
        self, role_service, mock_role_repository
    ):
        """Test error message contains current roles when worker has roles."""
        mock_role_repository.worker_has_role.return_value = False
        mock_role_repository.get_worker_roles_as_enum.return_value = [
            RolTrabajador.SOLDADOR,
            RolTrabajador.METROLOGIA
        ]

        with pytest.raises(RolNoAutorizadoError) as exc_info:
            role_service.validar_worker_tiene_rol_para_operacion(
                worker_id=95,
                operacion="ARM"
            )

        error = exc_info.value
        assert error.data["roles_actuales"] == ["Soldador", "Metrologia"]
        assert "Soldador" in str(error)
        assert "Metrologia" in str(error)

    def test_error_handles_no_roles_gracefully(
        self, role_service, mock_role_repository
    ):
        """Test error message handles worker with no roles gracefully."""
        mock_role_repository.worker_has_role.return_value = False
        mock_role_repository.get_worker_roles_as_enum.return_value = []

        with pytest.raises(RolNoAutorizadoError) as exc_info:
            role_service.validar_worker_tiene_rol_para_operacion(
                worker_id=96,
                operacion="ARM"
            )

        error = exc_info.value
        assert error.data["roles_actuales"] == []  # Empty list, not None
        # Error message should still be clear even with no roles
        assert "Armador" in str(error)
        assert "ARM" in str(error)
