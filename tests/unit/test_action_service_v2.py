"""
Unit tests for ActionService v2.0 features.

Tests CANCELAR action, worker_id migration in iniciar/completar, and integration.
"""
import pytest
from unittest.mock import Mock, MagicMock, call
from datetime import datetime
from backend.services.action_service import ActionService
from backend.services.worker_service import WorkerService
from backend.services.spool_service import SpoolService
from backend.services.validation_service import ValidationService
from backend.repositories.metadata_repository import MetadataRepository
from backend.models.worker import Worker
from backend.models.spool import Spool
from backend.models.enums import ActionStatus, ActionType
from backend.models.metadata import MetadataEvent, EventoTipo, Accion
from backend.models.action import ActionResponse
from backend.exceptions import (
    WorkerNoEncontradoError,
    SpoolNoEncontradoError,
    OperacionNoIniciadaError,
    NoAutorizadoError
)


@pytest.fixture
def mock_worker_service():
    """Mock WorkerService."""
    return Mock(spec=WorkerService)


@pytest.fixture
def mock_spool_service():
    """Mock SpoolService."""
    return Mock(spec=SpoolService)


@pytest.fixture
def mock_validation_service():
    """Mock ValidationService."""
    return Mock(spec=ValidationService)


@pytest.fixture
def mock_metadata_repository():
    """Mock MetadataRepository."""
    return Mock(spec=MetadataRepository)


@pytest.fixture
def action_service(
    mock_worker_service,
    mock_spool_service,
    mock_validation_service,
    mock_metadata_repository
):
    """ActionService fixture with mocked dependencies."""
    return ActionService(
        worker_service=mock_worker_service,
        spool_service=mock_spool_service,
        validation_service=mock_validation_service,
        metadata_repository=mock_metadata_repository
    )


@pytest.fixture
def worker_93():
    """Worker fixture for testing."""
    return Worker(
        id=93,
        nombre="Mauricio",
        apellido="Rodriguez",
        activo=True
    )


@pytest.fixture
def worker_94():
    """Worker fixture for testing."""
    return Worker(
        id=94,
        nombre="Carlos",
        apellido="Pimiento",
        activo=True
    )


@pytest.fixture
def spool_pendiente():
    """Spool in PENDIENTE state."""
    return Spool(
        tag_spool="MK-1335-CW-25238-011",
        estado_arm=ActionStatus.PENDIENTE,
        estado_sold=ActionStatus.PENDIENTE,
        armador=None,
        soldador=None,
        fecha_armado=None,
        fecha_soldadura=None
    )


@pytest.fixture
def spool_arm_en_progreso():
    """Spool with ARM EN_PROGRESO."""
    return Spool(
        tag_spool="MK-1335-CW-25238-011",
        estado_arm=ActionStatus.EN_PROGRESO,
        estado_sold=ActionStatus.PENDIENTE,
        armador="Mauricio Rodriguez",
        soldador=None,
        fecha_armado=None,
        fecha_soldadura=None
    )


class TestCancelarAccionSuccess:
    """Tests for successful cancelar_accion execution."""

    def test_cancelar_arm_success(
        self,
        action_service,
        mock_worker_service,
        mock_spool_service,
        mock_validation_service,
        mock_metadata_repository,
        worker_93,
        spool_arm_en_progreso
    ):
        """Test successful ARM cancellation."""
        # Setup mocks
        mock_worker_service.find_worker_by_id.return_value = worker_93
        mock_spool_service.find_spool_by_tag.return_value = spool_arm_en_progreso
        mock_validation_service.validar_puede_cancelar.return_value = None

        # Execute
        response = action_service.cancelar_accion(
            worker_id=93,
            operacion=ActionType.ARM,
            tag_spool="MK-1335-CW-25238-011"
        )

        # Verify response
        assert isinstance(response, ActionResponse)
        assert response.success is True
        assert "cancelada exitosamente" in response.message
        assert response.data.tag_spool == "MK-1335-CW-25238-011"
        assert response.data.operacion == "ARM"
        assert response.data.trabajador == "Mauricio Rodriguez"

        # Verify workflow
        mock_worker_service.find_worker_by_id.assert_called_once_with(93)
        mock_spool_service.find_spool_by_tag.assert_called_once_with(
            "MK-1335-CW-25238-011"
        )
        mock_validation_service.validar_puede_cancelar.assert_called_once()
        mock_metadata_repository.append_event.assert_called_once()

        # Verify event creation
        event_call = mock_metadata_repository.append_event.call_args[0][0]
        assert event_call.evento_tipo == EventoTipo.CANCELAR_ARM
        assert event_call.tag_spool == "MK-1335-CW-25238-011"
        assert event_call.worker_id == 93
        assert event_call.worker_nombre == "Mauricio Rodriguez"
        assert event_call.operacion == "ARM"
        assert event_call.accion == Accion.CANCELAR

    def test_cancelar_sold_success(
        self,
        action_service,
        mock_worker_service,
        mock_spool_service,
        mock_validation_service,
        mock_metadata_repository,
        worker_94
    ):
        """Test successful SOLD cancellation."""
        spool_sold_en_progreso = Spool(
            tag_spool="MK-1335-CW-25238-012",
            estado_arm=ActionStatus.COMPLETADO,
            estado_sold=ActionStatus.EN_PROGRESO,
            armador="Mauricio Rodriguez",
            soldador="Carlos Pimiento",
            fecha_armado="2025-12-10",
            fecha_soldadura=None
        )

        # Setup mocks
        mock_worker_service.find_worker_by_id.return_value = worker_94
        mock_spool_service.find_spool_by_tag.return_value = spool_sold_en_progreso
        mock_validation_service.validar_puede_cancelar.return_value = None

        # Execute
        response = action_service.cancelar_accion(
            worker_id=94,
            operacion=ActionType.SOLD,
            tag_spool="MK-1335-CW-25238-012"
        )

        # Verify response
        assert response.success is True
        assert "SOLD" in response.message
        assert response.data.operacion == "SOLD"
        assert response.data.trabajador == "Carlos Pimiento"

        # Verify event creation
        event_call = mock_metadata_repository.append_event.call_args[0][0]
        assert event_call.evento_tipo == EventoTipo.CANCELAR_SOLD
        assert event_call.operacion == "SOLD"

    def test_cancelar_creates_correct_metadata_event(
        self,
        action_service,
        mock_worker_service,
        mock_spool_service,
        mock_validation_service,
        mock_metadata_repository,
        worker_93,
        spool_arm_en_progreso
    ):
        """Test cancelar creates correct metadata event structure."""
        mock_worker_service.find_worker_by_id.return_value = worker_93
        mock_spool_service.find_spool_by_tag.return_value = spool_arm_en_progreso
        mock_validation_service.validar_puede_cancelar.return_value = None

        action_service.cancelar_accion(
            worker_id=93,
            operacion=ActionType.ARM,
            tag_spool="MK-1335-CW-25238-011"
        )

        # Get the event that was written
        event = mock_metadata_repository.append_event.call_args[0][0]

        # Verify event structure
        assert isinstance(event, MetadataEvent)
        assert event.evento_tipo == EventoTipo.CANCELAR_ARM
        assert event.tag_spool == "MK-1335-CW-25238-011"
        assert event.worker_id == 93
        assert event.worker_nombre == "Mauricio Rodriguez"
        assert event.operacion == "ARM"
        assert event.accion == Accion.CANCELAR
        assert event.fecha_operacion is not None  # Should be today
        assert event.metadata_json is None  # No extra metadata for CANCELAR


class TestCancelarAccionErrors:
    """Tests for error handling in cancelar_accion."""

    def test_cancelar_fails_worker_not_found(
        self,
        action_service,
        mock_worker_service
    ):
        """Test cancelar fails when worker not found."""
        mock_worker_service.find_worker_by_id.side_effect = WorkerNoEncontradoError(
            worker_nombre="Worker ID 999"
        )

        with pytest.raises(WorkerNoEncontradoError):
            action_service.cancelar_accion(
                worker_id=999,
                operacion=ActionType.ARM,
                tag_spool="MK-1335-CW-25238-011"
            )

    def test_cancelar_fails_spool_not_found(
        self,
        action_service,
        mock_worker_service,
        mock_spool_service,
        worker_93
    ):
        """Test cancelar fails when spool not found."""
        mock_worker_service.find_worker_by_id.return_value = worker_93
        mock_spool_service.find_spool_by_tag.side_effect = SpoolNoEncontradoError(
            tag_spool="INVALID-TAG"
        )

        with pytest.raises(SpoolNoEncontradoError):
            action_service.cancelar_accion(
                worker_id=93,
                operacion=ActionType.ARM,
                tag_spool="INVALID-TAG"
            )

    def test_cancelar_fails_operacion_no_iniciada(
        self,
        action_service,
        mock_worker_service,
        mock_spool_service,
        mock_validation_service,
        worker_93,
        spool_pendiente
    ):
        """Test cancelar fails when operation not started."""
        mock_worker_service.find_worker_by_id.return_value = worker_93
        mock_spool_service.find_spool_by_tag.return_value = spool_pendiente
        mock_validation_service.validar_puede_cancelar.side_effect = (
            OperacionNoIniciadaError(
                tag_spool="MK-1335-CW-25238-011",
                operacion="ARM"
            )
        )

        with pytest.raises(OperacionNoIniciadaError):
            action_service.cancelar_accion(
                worker_id=93,
                operacion=ActionType.ARM,
                tag_spool="MK-1335-CW-25238-011"
            )

    def test_cancelar_fails_ownership_violation(
        self,
        action_service,
        mock_worker_service,
        mock_spool_service,
        mock_validation_service,
        worker_94,
        spool_arm_en_progreso
    ):
        """Test cancelar fails when different worker tries to cancel."""
        mock_worker_service.find_worker_by_id.return_value = worker_94
        mock_spool_service.find_spool_by_tag.return_value = spool_arm_en_progreso
        mock_validation_service.validar_puede_cancelar.side_effect = NoAutorizadoError(
            tag_spool="MK-1335-CW-25238-011",
            trabajador_esperado="Mauricio Rodriguez",
            trabajador_solicitante="Carlos Pimiento",
            operacion="ARM"
        )

        with pytest.raises(NoAutorizadoError):
            action_service.cancelar_accion(
                worker_id=94,
                operacion=ActionType.ARM,
                tag_spool="MK-1335-CW-25238-011"
            )


class TestIniciarAccionWorkerIdMigration:
    """Tests for iniciar_accion worker_id migration (v2.0)."""

    def test_iniciar_arm_uses_worker_id(
        self,
        action_service,
        mock_worker_service,
        mock_spool_service,
        mock_validation_service,
        mock_metadata_repository,
        worker_93,
        spool_pendiente
    ):
        """Test iniciar_accion now uses worker_id instead of worker_nombre."""
        mock_worker_service.find_worker_by_id.return_value = worker_93
        mock_spool_service.find_spool_by_tag.return_value = spool_pendiente
        mock_validation_service.validar_puede_iniciar_arm.return_value = None

        response = action_service.iniciar_accion(
            worker_id=93,  # v2.0: worker_id (int) instead of worker_nombre (str)
            operacion=ActionType.ARM,
            tag_spool="MK-1335-CW-25238-011"
        )

        # Verify worker lookup used ID
        mock_worker_service.find_worker_by_id.assert_called_once_with(93)

        # Verify event has worker_id
        event = mock_metadata_repository.append_event.call_args[0][0]
        assert event.worker_id == 93
        assert event.worker_nombre == "Mauricio Rodriguez"

    def test_iniciar_sold_uses_worker_id(
        self,
        action_service,
        mock_worker_service,
        mock_spool_service,
        mock_validation_service,
        mock_metadata_repository,
        worker_94
    ):
        """Test iniciar SOLD uses worker_id."""
        spool_arm_completado = Spool(
            tag_spool="MK-1335-CW-25238-012",
            estado_arm=ActionStatus.COMPLETADO,
            estado_sold=ActionStatus.PENDIENTE,
            armador="Mauricio Rodriguez",
            soldador=None,
            fecha_armado="2025-12-10",
            fecha_soldadura=None
        )

        mock_worker_service.find_worker_by_id.return_value = worker_94
        mock_spool_service.find_spool_by_tag.return_value = spool_arm_completado
        mock_validation_service.validar_puede_iniciar_sold.return_value = None

        response = action_service.iniciar_accion(
            worker_id=94,
            operacion=ActionType.SOLD,
            tag_spool="MK-1335-CW-25238-012"
        )

        # Verify worker lookup used ID
        mock_worker_service.find_worker_by_id.assert_called_once_with(94)

        # Verify event has worker_id
        event = mock_metadata_repository.append_event.call_args[0][0]
        assert event.worker_id == 94


class TestCompletarAccionWorkerIdMigration:
    """Tests for completar_accion worker_id migration (v2.0)."""

    def test_completar_arm_uses_worker_id(
        self,
        action_service,
        mock_worker_service,
        mock_spool_service,
        mock_validation_service,
        mock_metadata_repository,
        worker_93,
        spool_arm_en_progreso
    ):
        """Test completar_accion now uses worker_id instead of worker_nombre."""
        mock_worker_service.find_worker_by_id.return_value = worker_93
        mock_spool_service.find_spool_by_tag.return_value = spool_arm_en_progreso
        mock_validation_service.validar_puede_completar_arm.return_value = None

        response = action_service.completar_accion(
            worker_id=93,  # v2.0: worker_id (int)
            operacion=ActionType.ARM,
            tag_spool="MK-1335-CW-25238-011",
            timestamp=datetime(2025, 12, 11, 15, 0, 0)
        )

        # Verify worker lookup used ID
        mock_worker_service.find_worker_by_id.assert_called_once_with(93)

        # Verify validation called with worker_id
        call_args = mock_validation_service.validar_puede_completar_arm.call_args
        assert call_args[1]['worker_id'] == 93

        # Verify event has worker_id
        event = mock_metadata_repository.append_event.call_args[0][0]
        assert event.worker_id == 93

    def test_completar_sold_uses_worker_id(
        self,
        action_service,
        mock_worker_service,
        mock_spool_service,
        mock_validation_service,
        mock_metadata_repository,
        worker_94
    ):
        """Test completar SOLD uses worker_id."""
        spool_sold_en_progreso = Spool(
            tag_spool="MK-1335-CW-25238-012",
            estado_arm=ActionStatus.COMPLETADO,
            estado_sold=ActionStatus.EN_PROGRESO,
            armador="Mauricio Rodriguez",
            soldador="Carlos Pimiento",
            fecha_armado="2025-12-10",
            fecha_soldadura=None
        )

        mock_worker_service.find_worker_by_id.return_value = worker_94
        mock_spool_service.find_spool_by_tag.return_value = spool_sold_en_progreso
        mock_validation_service.validar_puede_completar_sold.return_value = None

        response = action_service.completar_accion(
            worker_id=94,
            operacion=ActionType.SOLD,
            tag_spool="MK-1335-CW-25238-012",
            timestamp=datetime(2025, 12, 11, 16, 0, 0)
        )

        # Verify worker lookup used ID
        mock_worker_service.find_worker_by_id.assert_called_once_with(94)

        # Verify event has worker_id
        event = mock_metadata_repository.append_event.call_args[0][0]
        assert event.worker_id == 94


class TestValidationServiceIntegration:
    """Tests for ValidationService integration with worker_id."""

    def test_validar_puede_iniciar_arm_receives_worker_id(
        self,
        action_service,
        mock_worker_service,
        mock_spool_service,
        mock_validation_service,
        mock_metadata_repository,
        worker_93,
        spool_pendiente
    ):
        """Test ValidationService receives worker_id for role validation."""
        mock_worker_service.find_worker_by_id.return_value = worker_93
        mock_spool_service.find_spool_by_tag.return_value = spool_pendiente
        mock_validation_service.validar_puede_iniciar_arm.return_value = None

        action_service.iniciar_accion(
            worker_id=93,
            operacion=ActionType.ARM,
            tag_spool="MK-1335-CW-25238-011"
        )

        # Verify ValidationService received worker_id
        call_args = mock_validation_service.validar_puede_iniciar_arm.call_args
        assert call_args[1]['worker_id'] == 93

    def test_validar_puede_completar_arm_receives_worker_id(
        self,
        action_service,
        mock_worker_service,
        mock_spool_service,
        mock_validation_service,
        mock_metadata_repository,
        worker_93,
        spool_arm_en_progreso
    ):
        """Test ValidationService receives worker_id for role validation in completar."""
        mock_worker_service.find_worker_by_id.return_value = worker_93
        mock_spool_service.find_spool_by_tag.return_value = spool_arm_en_progreso
        mock_validation_service.validar_puede_completar_arm.return_value = None

        action_service.completar_accion(
            worker_id=93,
            operacion=ActionType.ARM,
            tag_spool="MK-1335-CW-25238-011"
        )

        # Verify ValidationService received worker_id
        call_args = mock_validation_service.validar_puede_completar_arm.call_args
        assert call_args[1]['worker_id'] == 93

    def test_validar_puede_cancelar_receives_worker_id(
        self,
        action_service,
        mock_worker_service,
        mock_spool_service,
        mock_validation_service,
        mock_metadata_repository,
        worker_93,
        spool_arm_en_progreso
    ):
        """Test ValidationService receives worker_id for role validation in cancelar."""
        mock_worker_service.find_worker_by_id.return_value = worker_93
        mock_spool_service.find_spool_by_tag.return_value = spool_arm_en_progreso
        mock_validation_service.validar_puede_cancelar.return_value = None

        action_service.cancelar_accion(
            worker_id=93,
            operacion=ActionType.ARM,
            tag_spool="MK-1335-CW-25238-011"
        )

        # Verify ValidationService received worker_id
        call_args = mock_validation_service.validar_puede_cancelar.call_args
        assert call_args[1]['worker_id'] == 93


class TestGetEventoTipoForCancelar:
    """Tests for _get_evento_tipo with CANCELAR action."""

    def test_get_evento_tipo_cancelar_arm(
        self,
        action_service,
        mock_worker_service,
        mock_spool_service,
        mock_validation_service,
        mock_metadata_repository,
        worker_93,
        spool_arm_en_progreso
    ):
        """Test evento_tipo for CANCELAR ARM is correct."""
        mock_worker_service.find_worker_by_id.return_value = worker_93
        mock_spool_service.find_spool_by_tag.return_value = spool_arm_en_progreso
        mock_validation_service.validar_puede_cancelar.return_value = None

        action_service.cancelar_accion(
            worker_id=93,
            operacion=ActionType.ARM,
            tag_spool="MK-1335-CW-25238-011"
        )

        event = mock_metadata_repository.append_event.call_args[0][0]
        assert event.evento_tipo == EventoTipo.CANCELAR_ARM

    def test_get_evento_tipo_cancelar_sold(
        self,
        action_service,
        mock_worker_service,
        mock_spool_service,
        mock_validation_service,
        mock_metadata_repository,
        worker_94
    ):
        """Test evento_tipo for CANCELAR SOLD is correct."""
        spool_sold_en_progreso = Spool(
            tag_spool="MK-1335-CW-25238-012",
            estado_arm=ActionStatus.COMPLETADO,
            estado_sold=ActionStatus.EN_PROGRESO,
            armador="Mauricio Rodriguez",
            soldador="Carlos Pimiento",
            fecha_armado="2025-12-10",
            fecha_soldadura=None
        )

        mock_worker_service.find_worker_by_id.return_value = worker_94
        mock_spool_service.find_spool_by_tag.return_value = spool_sold_en_progreso
        mock_validation_service.validar_puede_cancelar.return_value = None

        action_service.cancelar_accion(
            worker_id=94,
            operacion=ActionType.SOLD,
            tag_spool="MK-1335-CW-25238-012"
        )

        event = mock_metadata_repository.append_event.call_args[0][0]
        assert event.evento_tipo == EventoTipo.CANCELAR_SOLD
