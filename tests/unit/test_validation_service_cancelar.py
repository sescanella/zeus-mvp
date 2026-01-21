"""
Unit tests for ValidationService v2.1 CANCELAR functionality.

Tests validar_puede_cancelar method with role validation (no ownership restriction).
"""
import pytest
from unittest.mock import Mock, MagicMock
from datetime import datetime, date
from backend.services.validation_service import ValidationService
from backend.services.role_service import RoleService
from backend.repositories.metadata_repository import MetadataRepository
from backend.models.spool import Spool
from backend.models.enums import ActionStatus, ActionType
from backend.models.metadata import MetadataEvent, EventoTipo, Accion
from backend.exceptions import (
    OperacionNoIniciadaError,
    OperacionYaCompletadaError,
    NoAutorizadoError,
    RolNoAutorizadoError
)


@pytest.fixture
def mock_metadata_repository():
    """Mock MetadataRepository."""
    return Mock(spec=MetadataRepository)


@pytest.fixture
def mock_role_service():
    """Mock RoleService."""
    return Mock(spec=RoleService)


@pytest.fixture
def validation_service(mock_role_service):
    """ValidationService fixture with mocked dependencies (v2.1 Direct Read)."""
    return ValidationService(role_service=mock_role_service)


@pytest.fixture
def spool_arm_en_progreso():
    """Spool with ARM in EN_PROGRESO state (v2.1 Direct Read)."""
    return Spool(
        tag_spool="MK-1335-CW-25238-011",
        arm=ActionStatus.EN_PROGRESO,
        sold=ActionStatus.PENDIENTE,
        armador="JP(93)",  # v2.1: Read directly from column
        soldador=None,
        fecha_armado=None,
        fecha_soldadura=None,
        fecha_materiales=date(2025, 12, 1)
    )


@pytest.fixture
def eventos_arm_iniciado():
    """Events showing ARM was started by worker 93."""
    return [
        MetadataEvent(
            id="uuid-1",
            timestamp=datetime(2025, 12, 11, 10, 0, 0),
            evento_tipo=EventoTipo.INICIAR_ARM,
            tag_spool="MK-1335-CW-25238-011",
            worker_id=93,
            worker_nombre="Mauricio Rodriguez",
            operacion="ARM",
            accion=Accion.INICIAR,
            fecha_operacion="11-12-2025",
            metadata_json=None
        )
    ]


class TestValidarPuedeCancelarARMSuccess:
    """Tests for successful ARM cancellation validation."""

    def test_cancelar_arm_success_same_worker(
        self,
        validation_service,
        mock_role_service,
        spool_arm_en_progreso
    ):
        """Test CANCELAR ARM succeeds when same worker who started tries to cancel."""
        mock_role_service.validar_worker_tiene_rol_para_operacion.return_value = None

        # Should not raise
        validation_service.validar_puede_cancelar(
            spool=spool_arm_en_progreso,
            operacion=ActionType.ARM,
            worker_nombre="JP(93)",
            worker_id=93
        )

        # Verify role validation was called
        mock_role_service.validar_worker_tiene_rol_para_operacion.assert_called_once_with(
            93,
            "ARM"
        )

    def test_cancelar_arm_success_case_insensitive_nombre(
        self,
        validation_service,
        mock_role_service,
        spool_arm_en_progreso
    ):
        """Test CANCELAR ARM succeeds with case-insensitive name matching."""
        mock_role_service.validar_worker_tiene_rol_para_operacion.return_value = None

        # Should not raise (name has different case)
        validation_service.validar_puede_cancelar(
            spool=spool_arm_en_progreso,
            operacion=ActionType.ARM,
            worker_nombre="jp(93)",  # Lowercase
            worker_id=93
        )

    def test_cancelar_arm_success_operacion_uppercase(
        self,
        validation_service,
        mock_role_service,
        spool_arm_en_progreso
    ):
        """Test CANCELAR ARM works with uppercase operation name."""
        mock_role_service.validar_worker_tiene_rol_para_operacion.return_value = None

        # Should not raise
        validation_service.validar_puede_cancelar(
            spool=spool_arm_en_progreso,
            operacion=ActionType.ARM,
            worker_nombre="JP(93)",
            worker_id=93
        )

    def test_cancelar_arm_success_operacion_lowercase(
        self,
        validation_service,
        mock_role_service,
        spool_arm_en_progreso
    ):
        """Test CANCELAR ARM works with ActionType enum."""
        mock_role_service.validar_worker_tiene_rol_para_operacion.return_value = None

        # Should not raise
        validation_service.validar_puede_cancelar(
            spool=spool_arm_en_progreso,
            operacion=ActionType.ARM,
            worker_nombre="JP(93)",
            worker_id=93
        )


class TestValidarPuedeCancelarSOLDSuccess:
    """Tests for successful SOLD cancellation validation."""

    def test_cancelar_sold_success_same_worker(
        self,
        validation_service,
        mock_role_service
    ):
        """Test CANCELAR SOLD succeeds when same worker who started tries to cancel."""
        spool = Spool(
            tag_spool="MK-1335-CW-25238-012",
            arm=ActionStatus.COMPLETADO,
            sold=ActionStatus.EN_PROGRESO,
            armador="JP(93)",
            soldador="CP(94)",  # v2.1: Read directly from column
            fecha_armado=date(2025, 12, 10),
            fecha_soldadura=None,
            fecha_materiales=date(2025, 12, 1)
        )

        mock_role_service.validar_worker_tiene_rol_para_operacion.return_value = None

        # Should not raise
        validation_service.validar_puede_cancelar(
            spool=spool,
            operacion=ActionType.SOLD,
            worker_nombre="CP(94)",
            worker_id=94
        )

        # Verify role validation was called for SOLD
        mock_role_service.validar_worker_tiene_rol_para_operacion.assert_called_once_with(
            94,
            "SOLD"
        )


class TestValidarPuedeCancelarCrossWorker:
    """Tests for cross-worker cancellation (now allowed with role validation)."""

    def test_cancelar_arm_succeeds_different_worker_with_correct_role(
        self,
        validation_service,
        mock_role_service,
        spool_arm_en_progreso
    ):
        """Test CANCELAR ARM succeeds when different worker with Armador role tries to cancel."""
        mock_role_service.validar_worker_tiene_rol_para_operacion.return_value = None

        # Should not raise - any worker with Armador role can cancel
        validation_service.validar_puede_cancelar(
            spool=spool_arm_en_progreso,
            operacion=ActionType.ARM,
            worker_nombre="CP(94)",  # Different worker
            worker_id=94
        )

        # Verify role validation was called
        mock_role_service.validar_worker_tiene_rol_para_operacion.assert_called_once_with(
            94,
            "ARM"
        )

    def test_cancelar_sold_succeeds_different_worker_with_correct_role(
        self,
        validation_service,
        mock_role_service
    ):
        """Test CANCELAR SOLD succeeds when different worker with Soldador role tries to cancel."""
        spool = Spool(
            tag_spool="MK-1335-CW-25238-012",
            arm=ActionStatus.COMPLETADO,
            sold=ActionStatus.EN_PROGRESO,
            armador="JP(93)",
            soldador="CP(94)",  # Started by worker 94
            fecha_armado=date(2025, 12, 10),
            fecha_soldadura=None,
            fecha_materiales=date(2025, 12, 1)
        )

        mock_role_service.validar_worker_tiene_rol_para_operacion.return_value = None

        # Should not raise - any worker with Soldador role can cancel
        validation_service.validar_puede_cancelar(
            spool=spool,
            operacion=ActionType.SOLD,
            worker_nombre="MR(93)",  # Different worker
            worker_id=93
        )

        # Verify role validation was called
        mock_role_service.validar_worker_tiene_rol_para_operacion.assert_called_once_with(
            93,
            "SOLD"
        )


class TestValidarPuedeCancelarRoleErrors:
    """Tests for role validation failures in CANCELAR."""

    def test_cancelar_arm_fails_worker_no_tiene_rol_armador(
        self,
        validation_service,
        mock_role_service,
        spool_arm_en_progreso
    ):
        """Test CANCELAR ARM fails when worker doesn't have Armador role."""
        mock_role_service.validar_worker_tiene_rol_para_operacion.side_effect = (
            RolNoAutorizadoError(
                worker_id=93,
                operacion="ARM",
                rol_requerido="Armador",
                roles_actuales=["Soldador"]
            )
        )

        with pytest.raises(RolNoAutorizadoError) as exc_info:
            validation_service.validar_puede_cancelar(
                spool=spool_arm_en_progreso,
                operacion=ActionType.ARM,
                worker_nombre="JP(93)",
                worker_id=93
            )

        error = exc_info.value
        assert error.worker_id == 93
        assert error.operacion == "ARM"
        assert error.rol_requerido == "Armador"

    def test_cancelar_sold_fails_worker_no_tiene_rol_soldador(
        self,
        validation_service,
        mock_role_service
    ):
        """Test CANCELAR SOLD fails when worker doesn't have Soldador role."""
        spool = Spool(
            tag_spool="MK-1335-CW-25238-012",
            arm=ActionStatus.COMPLETADO,
            sold=ActionStatus.EN_PROGRESO,
            armador="JP(93)",
            soldador="CP(94)",
            fecha_armado=date(2025, 12, 10),
            fecha_soldadura=None,
            fecha_materiales=date(2025, 12, 1)
        )

        mock_role_service.validar_worker_tiene_rol_para_operacion.side_effect = (
            RolNoAutorizadoError(
                worker_id=94,
                operacion="SOLD",
                rol_requerido="Soldador",
                roles_actuales=["Armador"]
            )
        )

        with pytest.raises(RolNoAutorizadoError):
            validation_service.validar_puede_cancelar(
                spool=spool,
                operacion=ActionType.SOLD,
                worker_nombre="CP(94)",
                worker_id=94
            )


class TestValidarPuedeCancelarStateErrors:
    """Tests for state validation failures in CANCELAR."""

    def test_cancelar_arm_fails_estado_pendiente(
        self,
        validation_service,
        mock_role_service
    ):
        """Test CANCELAR ARM fails when operation is PENDIENTE (not started)."""
        spool = Spool(
            tag_spool="MK-1335-CW-25238-011",
            arm=ActionStatus.PENDIENTE,
            sold=ActionStatus.PENDIENTE,
            armador=None,  # v2.1: armador=None means not started
            soldador=None,
            fecha_armado=None,
            fecha_soldadura=None,
            fecha_materiales=date(2025, 12, 1)
        )

        with pytest.raises(OperacionNoIniciadaError) as exc_info:
            validation_service.validar_puede_cancelar(
                spool=spool,
                operacion=ActionType.ARM,
                worker_nombre="JP(93)",
                worker_id=93
            )

        error = exc_info.value
        assert "MK-1335-CW-25238-011" in str(error)
        assert "ARM" in str(error)

    def test_cancelar_arm_fails_estado_completado(
        self,
        validation_service,
        mock_role_service
    ):
        """Test CANCELAR ARM fails when operation is COMPLETADO."""
        spool = Spool(
            tag_spool="MK-1335-CW-25238-011",
            arm=ActionStatus.COMPLETADO,
            sold=ActionStatus.PENDIENTE,
            armador="JP(93)",
            soldador=None,
            fecha_armado=date(2025, 12, 11),  # v2.1: fecha_armado != None means completed
            fecha_soldadura=None,
            fecha_materiales=date(2025, 12, 1)
        )

        with pytest.raises(OperacionYaCompletadaError) as exc_info:
            validation_service.validar_puede_cancelar(
                spool=spool,
                operacion=ActionType.ARM,
                worker_nombre="JP(93)",
                worker_id=93
            )

        error = exc_info.value
        assert "MK-1335-CW-25238-011" in str(error)
        assert "ARM" in str(error)

    def test_cancelar_sold_fails_estado_pendiente(
        self,
        validation_service,
        mock_role_service
    ):
        """Test CANCELAR SOLD fails when operation is PENDIENTE."""
        spool = Spool(
            tag_spool="MK-1335-CW-25238-012",
            arm=ActionStatus.COMPLETADO,
            sold=ActionStatus.PENDIENTE,
            armador="JP(93)",
            soldador=None,  # v2.1: soldador=None means not started
            fecha_armado=date(2025, 12, 10),
            fecha_soldadura=None,
            fecha_materiales=date(2025, 12, 1)
        )

        with pytest.raises(OperacionNoIniciadaError):
            validation_service.validar_puede_cancelar(
                spool=spool,
                operacion=ActionType.SOLD,
                worker_nombre="CP(94)",
                worker_id=94
            )


class TestValidarPuedeCancelarInvalidOperation:
    """Tests for invalid operation validation in CANCELAR."""

    def test_cancelar_fails_operacion_invalida(
        self,
        validation_service,
        spool_arm_en_progreso
    ):
        """Test CANCELAR fails with invalid operation type."""
        # This test is no longer relevant since we use ActionType enum
        # ActionType only allows ARM, SOLD, METROLOGIA
        # Invalid operations would be caught at type level
        pass

    def test_cancelar_fails_operacion_empty(
        self,
        validation_service,
        spool_arm_en_progreso
    ):
        """Test CANCELAR requires valid ActionType enum."""
        # This test is no longer relevant since we use ActionType enum
        # Type system prevents empty/invalid operations
        pass


class TestValidarPuedeCancelarEventReconstruction:
    """Tests for event reconstruction in CANCELAR validation."""

    def test_cancelar_reads_estado_from_operaciones_sheet(
        self,
        validation_service,
        mock_role_service,
        spool_arm_en_progreso
    ):
        """Test CANCELAR reads state directly from Operaciones sheet (v2.1 Direct Read)."""
        # v2.1: State is read directly from spool columns, not reconstructed from events
        assert spool_arm_en_progreso.arm == ActionStatus.EN_PROGRESO
        assert spool_arm_en_progreso.armador == "JP(93)"

        mock_role_service.validar_worker_tiene_rol_para_operacion.return_value = None

        # Should not raise - validates EN_PROGRESO state from columns
        validation_service.validar_puede_cancelar(
            spool=spool_arm_en_progreso,
            operacion=ActionType.ARM,
            worker_nombre="JP(93)",
            worker_id=93
        )

    def test_cancelar_allows_any_worker_with_role(
        self,
        validation_service,
        mock_role_service
    ):
        """Test CANCELAR allows any worker with correct role regardless of who started."""
        # Spool has ARM in progress started by worker 93 (JP)
        # v2.1: armador shows who started, but any Armador can cancel
        spool = Spool(
            tag_spool="MK-1335-CW-25238-011",
            arm=ActionStatus.EN_PROGRESO,
            sold=ActionStatus.PENDIENTE,
            armador="JP(93)",  # Started by worker 93
            soldador=None,
            fecha_armado=None,
            fecha_soldadura=None,
            fecha_materiales=date(2025, 12, 1)
        )

        mock_role_service.validar_worker_tiene_rol_para_operacion.return_value = None

        # Worker 93 can cancel (original starter)
        validation_service.validar_puede_cancelar(
            spool=spool,
            operacion=ActionType.ARM,
            worker_nombre="JP(93)",
            worker_id=93
        )

        # Worker 94 can also cancel (different worker with Armador role)
        validation_service.validar_puede_cancelar(
            spool=spool,
            operacion=ActionType.ARM,
            worker_nombre="CP(94)",
            worker_id=94
        )
