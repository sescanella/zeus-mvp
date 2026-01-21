"""
Unit tests for ValidationService v2.0 CANCELAR functionality.

Tests validar_puede_cancelar method with ownership + role validation.
"""
import pytest
from unittest.mock import Mock, MagicMock
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
from datetime import datetime


@pytest.fixture
def mock_metadata_repository():
    """Mock MetadataRepository."""
    return Mock(spec=MetadataRepository)


@pytest.fixture
def mock_role_service():
    """Mock RoleService."""
    return Mock(spec=RoleService)


@pytest.fixture
def validation_service(mock_metadata_repository, mock_role_service):
    """ValidationService fixture with mocked dependencies."""
    return ValidationService(
        metadata_repository=mock_metadata_repository,
        role_service=mock_role_service
    )


@pytest.fixture
def spool_arm_en_progreso():
    """Spool with ARM in EN_PROGRESO state."""
    return Spool(
        tag_spool="MK-1335-CW-25238-011",
        estado_arm=ActionStatus.PENDIENTE,  # Will be reconstructed from events
        estado_sold=ActionStatus.PENDIENTE,
        armador=None,
        soldador=None,
        fecha_armado=None,
        fecha_soldadura=None
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
        mock_metadata_repository,
        mock_role_service,
        spool_arm_en_progreso,
        eventos_arm_iniciado
    ):
        """Test CANCELAR ARM succeeds when same worker who started tries to cancel."""
        mock_metadata_repository.get_events_by_spool.return_value = eventos_arm_iniciado
        mock_role_service.validar_worker_tiene_rol_para_operacion.return_value = None

        # Should not raise
        validation_service.validar_puede_cancelar(
            spool=spool_arm_en_progreso,
            operacion="ARM",
            worker_nombre="Mauricio Rodriguez",
            worker_id=93
        )

        # Verify role validation was called
        mock_role_service.validar_worker_tiene_rol_para_operacion.assert_called_once_with(
            worker_id=93,
            operacion="ARM"
        )

    def test_cancelar_arm_success_case_insensitive_nombre(
        self,
        validation_service,
        mock_metadata_repository,
        mock_role_service,
        spool_arm_en_progreso,
        eventos_arm_iniciado
    ):
        """Test CANCELAR ARM succeeds with case-insensitive name matching."""
        mock_metadata_repository.get_events_by_spool.return_value = eventos_arm_iniciado
        mock_role_service.validar_worker_tiene_rol_para_operacion.return_value = None

        # Should not raise (name has different case)
        validation_service.validar_puede_cancelar(
            spool=spool_arm_en_progreso,
            operacion="ARM",
            worker_nombre="MAURICIO RODRIGUEZ",  # Uppercase
            worker_id=93
        )

    def test_cancelar_arm_success_operacion_uppercase(
        self,
        validation_service,
        mock_metadata_repository,
        mock_role_service,
        spool_arm_en_progreso,
        eventos_arm_iniciado
    ):
        """Test CANCELAR ARM works with uppercase operation name."""
        mock_metadata_repository.get_events_by_spool.return_value = eventos_arm_iniciado
        mock_role_service.validar_worker_tiene_rol_para_operacion.return_value = None

        # Should not raise
        validation_service.validar_puede_cancelar(
            spool=spool_arm_en_progreso,
            operacion="ARM",  # Already uppercase
            worker_nombre="Mauricio Rodriguez",
            worker_id=93
        )

    def test_cancelar_arm_success_operacion_lowercase(
        self,
        validation_service,
        mock_metadata_repository,
        mock_role_service,
        spool_arm_en_progreso,
        eventos_arm_iniciado
    ):
        """Test CANCELAR ARM works with lowercase operation name."""
        mock_metadata_repository.get_events_by_spool.return_value = eventos_arm_iniciado
        mock_role_service.validar_worker_tiene_rol_para_operacion.return_value = None

        # Should not raise
        validation_service.validar_puede_cancelar(
            spool=spool_arm_en_progreso,
            operacion="arm",  # Lowercase
            worker_nombre="Mauricio Rodriguez",
            worker_id=93
        )


class TestValidarPuedeCancelarSOLDSuccess:
    """Tests for successful SOLD cancellation validation."""

    def test_cancelar_sold_success_same_worker(
        self,
        validation_service,
        mock_metadata_repository,
        mock_role_service
    ):
        """Test CANCELAR SOLD succeeds when same worker who started tries to cancel."""
        spool = Spool(
            tag_spool="MK-1335-CW-25238-012",
            estado_arm=ActionStatus.COMPLETADO,
            estado_sold=ActionStatus.PENDIENTE,  # Will be reconstructed
            armador="Mauricio Rodriguez",
            soldador=None,
            fecha_armado="10-12-2025",
            fecha_soldadura=None
        )

        eventos_sold_iniciado = [
            MetadataEvent(
                id="uuid-1",
                timestamp=datetime(2025, 12, 10, 10, 0, 0),
                evento_tipo=EventoTipo.COMPLETAR_ARM,
                tag_spool="MK-1335-CW-25238-012",
                worker_id=93,
                worker_nombre="Mauricio Rodriguez",
                operacion="ARM",
                accion=Accion.COMPLETAR,
                fecha_operacion="10-12-2025",
                metadata_json=None
            ),
            MetadataEvent(
                id="uuid-2",
                timestamp=datetime(2025, 12, 11, 14, 0, 0),
                evento_tipo=EventoTipo.INICIAR_SOLD,
                tag_spool="MK-1335-CW-25238-012",
                worker_id=94,
                worker_nombre="Carlos Pimiento",
                operacion="SOLD",
                accion=Accion.INICIAR,
                fecha_operacion="11-12-2025",
                metadata_json=None
            )
        ]

        mock_metadata_repository.get_events_by_spool.return_value = eventos_sold_iniciado
        mock_role_service.validar_worker_tiene_rol_para_operacion.return_value = None

        # Should not raise
        validation_service.validar_puede_cancelar(
            spool=spool,
            operacion="SOLD",
            worker_nombre="Carlos Pimiento",
            worker_id=94
        )

        # Verify role validation was called for SOLD
        mock_role_service.validar_worker_tiene_rol_para_operacion.assert_called_once_with(
            worker_id=94,
            operacion="SOLD"
        )


class TestValidarPuedeCancelarOwnershipErrors:
    """Tests for ownership validation failures in CANCELAR."""

    def test_cancelar_arm_fails_different_worker(
        self,
        validation_service,
        mock_metadata_repository,
        mock_role_service,
        spool_arm_en_progreso,
        eventos_arm_iniciado
    ):
        """Test CANCELAR ARM fails when different worker tries to cancel."""
        mock_metadata_repository.get_events_by_spool.return_value = eventos_arm_iniciado
        # Role validation would pass, but ownership fails

        with pytest.raises(NoAutorizadoError) as exc_info:
            validation_service.validar_puede_cancelar(
                spool=spool_arm_en_progreso,
                operacion="ARM",
                worker_nombre="Carlos Pimiento",  # Different worker
                worker_id=94
            )

        error = exc_info.value
        assert "Mauricio Rodriguez" in str(error)  # Who started
        assert "Carlos Pimiento" in str(error)  # Who tried to cancel
        assert "ARM" in str(error)

        # Role validation should NOT be called if ownership fails first
        # (ownership is validated before role)
        assert mock_role_service.validar_worker_tiene_rol_para_operacion.call_count == 0

    def test_cancelar_sold_fails_different_worker(
        self,
        validation_service,
        mock_metadata_repository,
        mock_role_service
    ):
        """Test CANCELAR SOLD fails when different worker tries to cancel."""
        spool = Spool(
            tag_spool="MK-1335-CW-25238-012",
            estado_arm=ActionStatus.COMPLETADO,
            estado_sold=ActionStatus.PENDIENTE,
            armador="Mauricio Rodriguez",
            soldador=None,
            fecha_armado="10-12-2025",
            fecha_soldadura=None
        )

        eventos_sold_iniciado = [
            MetadataEvent(
                id="uuid-2",
                timestamp=datetime(2025, 12, 11, 14, 0, 0),
                evento_tipo=EventoTipo.INICIAR_SOLD,
                tag_spool="MK-1335-CW-25238-012",
                worker_id=94,
                worker_nombre="Carlos Pimiento",
                operacion="SOLD",
                accion=Accion.INICIAR,
                fecha_operacion="11-12-2025",
                metadata_json=None
            )
        ]

        mock_metadata_repository.get_events_by_spool.return_value = eventos_sold_iniciado

        with pytest.raises(NoAutorizadoError) as exc_info:
            validation_service.validar_puede_cancelar(
                spool=spool,
                operacion="SOLD",
                worker_nombre="Mauricio Rodriguez",  # Different worker
                worker_id=93
            )

        error = exc_info.value
        assert "Carlos Pimiento" in str(error)  # Who started
        assert "Mauricio Rodriguez" in str(error)  # Who tried to cancel


class TestValidarPuedeCancelarRoleErrors:
    """Tests for role validation failures in CANCELAR."""

    def test_cancelar_arm_fails_worker_no_tiene_rol_armador(
        self,
        validation_service,
        mock_metadata_repository,
        mock_role_service,
        spool_arm_en_progreso,
        eventos_arm_iniciado
    ):
        """Test CANCELAR ARM fails when worker doesn't have Armador role."""
        mock_metadata_repository.get_events_by_spool.return_value = eventos_arm_iniciado
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
                operacion="ARM",
                worker_nombre="Mauricio Rodriguez",
                worker_id=93
            )

        error = exc_info.value
        assert error.worker_id == 93
        assert error.operacion == "ARM"
        assert error.rol_requerido == "Armador"

    def test_cancelar_sold_fails_worker_no_tiene_rol_soldador(
        self,
        validation_service,
        mock_metadata_repository,
        mock_role_service
    ):
        """Test CANCELAR SOLD fails when worker doesn't have Soldador role."""
        spool = Spool(
            tag_spool="MK-1335-CW-25238-012",
            estado_arm=ActionStatus.COMPLETADO,
            estado_sold=ActionStatus.PENDIENTE,
            armador="Mauricio Rodriguez",
            soldador=None,
            fecha_armado="10-12-2025",
            fecha_soldadura=None
        )

        eventos_sold_iniciado = [
            MetadataEvent(
                id="uuid-2",
                timestamp=datetime(2025, 12, 11, 14, 0, 0),
                evento_tipo=EventoTipo.INICIAR_SOLD,
                tag_spool="MK-1335-CW-25238-012",
                worker_id=94,
                worker_nombre="Carlos Pimiento",
                operacion="SOLD",
                accion=Accion.INICIAR,
                fecha_operacion="11-12-2025",
                metadata_json=None
            )
        ]

        mock_metadata_repository.get_events_by_spool.return_value = eventos_sold_iniciado
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
                operacion="SOLD",
                worker_nombre="Carlos Pimiento",
                worker_id=94
            )


class TestValidarPuedeCancelarStateErrors:
    """Tests for state validation failures in CANCELAR."""

    def test_cancelar_arm_fails_estado_pendiente(
        self,
        validation_service,
        mock_metadata_repository,
        mock_role_service
    ):
        """Test CANCELAR ARM fails when operation is PENDIENTE (not started)."""
        spool = Spool(
            tag_spool="MK-1335-CW-25238-011",
            estado_arm=ActionStatus.PENDIENTE,
            estado_sold=ActionStatus.PENDIENTE,
            armador=None,
            soldador=None,
            fecha_armado=None,
            fecha_soldadura=None
        )

        # No events = operation never started
        mock_metadata_repository.get_events_by_spool.return_value = []

        with pytest.raises(OperacionNoIniciadaError) as exc_info:
            validation_service.validar_puede_cancelar(
                spool=spool,
                operacion="ARM",
                worker_nombre="Mauricio Rodriguez",
                worker_id=93
            )

        error = exc_info.value
        assert "MK-1335-CW-25238-011" in str(error)
        assert "ARM" in str(error)

    def test_cancelar_arm_fails_estado_completado(
        self,
        validation_service,
        mock_metadata_repository,
        mock_role_service
    ):
        """Test CANCELAR ARM fails when operation is COMPLETADO."""
        spool = Spool(
            tag_spool="MK-1335-CW-25238-011",
            estado_arm=ActionStatus.PENDIENTE,  # Will be reconstructed
            estado_sold=ActionStatus.PENDIENTE,
            armador=None,
            soldador=None,
            fecha_armado=None,
            fecha_soldadura=None
        )

        eventos_arm_completado = [
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
            ),
            MetadataEvent(
                id="uuid-2",
                timestamp=datetime(2025, 12, 11, 15, 0, 0),
                evento_tipo=EventoTipo.COMPLETAR_ARM,
                tag_spool="MK-1335-CW-25238-011",
                worker_id=93,
                worker_nombre="Mauricio Rodriguez",
                operacion="ARM",
                accion=Accion.COMPLETAR,
                fecha_operacion="11-12-2025",
                metadata_json=None
            )
        ]

        mock_metadata_repository.get_events_by_spool.return_value = eventos_arm_completado

        with pytest.raises(OperacionYaCompletadaError) as exc_info:
            validation_service.validar_puede_cancelar(
                spool=spool,
                operacion="ARM",
                worker_nombre="Mauricio Rodriguez",
                worker_id=93
            )

        error = exc_info.value
        assert "MK-1335-CW-25238-011" in str(error)
        assert "ARM" in str(error)

    def test_cancelar_sold_fails_estado_pendiente(
        self,
        validation_service,
        mock_metadata_repository,
        mock_role_service
    ):
        """Test CANCELAR SOLD fails when operation is PENDIENTE."""
        spool = Spool(
            tag_spool="MK-1335-CW-25238-012",
            estado_arm=ActionStatus.COMPLETADO,
            estado_sold=ActionStatus.PENDIENTE,
            armador="Mauricio Rodriguez",
            soldador=None,
            fecha_armado="10-12-2025",
            fecha_soldadura=None
        )

        # Only ARM events, no SOLD events
        eventos_solo_arm = [
            MetadataEvent(
                id="uuid-1",
                timestamp=datetime(2025, 12, 10, 10, 0, 0),
                evento_tipo=EventoTipo.COMPLETAR_ARM,
                tag_spool="MK-1335-CW-25238-012",
                worker_id=93,
                worker_nombre="Mauricio Rodriguez",
                operacion="ARM",
                accion=Accion.COMPLETAR,
                fecha_operacion="10-12-2025",
                metadata_json=None
            )
        ]

        mock_metadata_repository.get_events_by_spool.return_value = eventos_solo_arm

        with pytest.raises(OperacionNoIniciadaError):
            validation_service.validar_puede_cancelar(
                spool=spool,
                operacion="SOLD",
                worker_nombre="Carlos Pimiento",
                worker_id=94
            )


class TestValidarPuedeCancelarInvalidOperation:
    """Tests for invalid operation validation in CANCELAR."""

    def test_cancelar_fails_operacion_invalida(
        self,
        validation_service,
        mock_metadata_repository,
        spool_arm_en_progreso
    ):
        """Test CANCELAR fails with invalid operation name."""
        with pytest.raises(ValueError) as exc_info:
            validation_service.validar_puede_cancelar(
                spool=spool_arm_en_progreso,
                operacion="INVALID_OP",
                worker_nombre="Mauricio Rodriguez",
                worker_id=93
            )

        assert "INVALID_OP" in str(exc_info.value)
        assert "no soportada" in str(exc_info.value)

    def test_cancelar_fails_operacion_empty(
        self,
        validation_service,
        mock_metadata_repository,
        spool_arm_en_progreso
    ):
        """Test CANCELAR fails with empty operation name."""
        with pytest.raises(ValueError):
            validation_service.validar_puede_cancelar(
                spool=spool_arm_en_progreso,
                operacion="",
                worker_nombre="Mauricio Rodriguez",
                worker_id=93
            )


class TestValidarPuedeCancelarEventReconstruction:
    """Tests for event reconstruction in CANCELAR validation."""

    def test_cancelar_reconstructs_estado_from_events(
        self,
        validation_service,
        mock_metadata_repository,
        mock_role_service,
        spool_arm_en_progreso,
        eventos_arm_iniciado
    ):
        """Test CANCELAR correctly reconstructs state from Metadata events."""
        # Initial spool has estado_arm=PENDIENTE
        assert spool_arm_en_progreso.estado_arm == ActionStatus.PENDIENTE

        mock_metadata_repository.get_events_by_spool.return_value = eventos_arm_iniciado
        mock_role_service.validar_worker_tiene_rol_para_operacion.return_value = None

        # Should not raise - validates EN_PROGRESO state from events
        validation_service.validar_puede_cancelar(
            spool=spool_arm_en_progreso,
            operacion="ARM",
            worker_nombre="Mauricio Rodriguez",
            worker_id=93
        )

        # Verify it fetched events to reconstruct state
        mock_metadata_repository.get_events_by_spool.assert_called_once_with(
            tag_spool="MK-1335-CW-25238-011"
        )

    def test_cancelar_uses_latest_event_for_ownership(
        self,
        validation_service,
        mock_metadata_repository,
        mock_role_service,
        spool_arm_en_progreso
    ):
        """Test CANCELAR uses latest INICIAR event to determine ownership."""
        # Multiple INICIAR/CANCELAR events (worker 93 started, then cancelled, then started again)
        eventos_multiple = [
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
            ),
            MetadataEvent(
                id="uuid-2",
                timestamp=datetime(2025, 12, 11, 11, 0, 0),
                evento_tipo=EventoTipo.CANCELAR_ARM,
                tag_spool="MK-1335-CW-25238-011",
                worker_id=93,
                worker_nombre="Mauricio Rodriguez",
                operacion="ARM",
                accion=Accion.CANCELAR,
                fecha_operacion="11-12-2025",
                metadata_json=None
            ),
            MetadataEvent(
                id="uuid-3",
                timestamp=datetime(2025, 12, 11, 14, 0, 0),
                evento_tipo=EventoTipo.INICIAR_ARM,
                tag_spool="MK-1335-CW-25238-011",
                worker_id=94,
                worker_nombre="Carlos Pimiento",  # Different worker
                operacion="ARM",
                accion=Accion.INICIAR,
                fecha_operacion="11-12-2025",
                metadata_json=None
            )
        ]

        mock_metadata_repository.get_events_by_spool.return_value = eventos_multiple
        mock_role_service.validar_worker_tiene_rol_para_operacion.return_value = None

        # Worker 94 should be able to cancel (he's the current owner)
        validation_service.validar_puede_cancelar(
            spool=spool_arm_en_progreso,
            operacion="ARM",
            worker_nombre="Carlos Pimiento",
            worker_id=94
        )

        # Worker 93 should NOT be able to cancel (he cancelled earlier)
        with pytest.raises(NoAutorizadoError):
            validation_service.validar_puede_cancelar(
                spool=spool_arm_en_progreso,
                operacion="ARM",
                worker_nombre="Mauricio Rodriguez",
                worker_id=93
            )
