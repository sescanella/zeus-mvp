"""
Tests unitarios para ActionService.

Cobertura:
- Iniciar acciones (ARM/SOLD) - flujo happy path
- Completar acciones (ARM/SOLD) - flujo happy path
- Validación ownership (CRÍTICO)
- Manejo de excepciones
- Edge cases (timestamps custom, cache invalidation, etc.)

Coverage objetivo: >90%
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, date

from backend.services.action_service import ActionService
from backend.models.enums import ActionType, ActionStatus
from backend.models.action import ActionResponse, ActionData
from backend.models.spool import Spool
from backend.models.worker import Worker

from backend.exceptions import (
    WorkerNoEncontradoError,
    SpoolNoEncontradoError,
    OperacionNoPendienteError,
    OperacionNoIniciadaError,
    OperacionYaCompletadaError,
    NoAutorizadoError,
    DependenciasNoSatisfechasError,
    SheetsUpdateError
)


# ==================== FIXTURES ====================

@pytest.fixture
def mock_sheets_repo(mocker):
    """Mock de SheetsRepository."""
    return mocker.Mock()


@pytest.fixture
def mock_sheets_service(mocker):
    """Mock de SheetsService."""
    return mocker.Mock()


@pytest.fixture
def mock_validation_service(mocker):
    """Mock de ValidationService."""
    return mocker.Mock()


@pytest.fixture
def mock_spool_service(mocker):
    """Mock de SpoolService."""
    return mocker.Mock()


@pytest.fixture
def mock_worker_service(mocker):
    """Mock de WorkerService."""
    return mocker.Mock()


@pytest.fixture
def action_service(
    mock_sheets_repo,
    mock_sheets_service,
    mock_validation_service,
    mock_spool_service,
    mock_worker_service
):
    """Instancia de ActionService con mocks."""
    return ActionService(
        sheets_repo=mock_sheets_repo,
        sheets_service=mock_sheets_service,
        validation_service=mock_validation_service,
        spool_service=mock_spool_service,
        worker_service=mock_worker_service
    )


@pytest.fixture
def sample_worker():
    """Worker de ejemplo."""
    return Worker(
        nombre="Juan",
        apellido="Pérez",
        activo=True
    )


@pytest.fixture
def sample_spool_pendiente():
    """Spool con ARM pendiente."""
    return Spool(
        tag_spool="MK-123",
        fecha_materiales=date(2025, 1, 15),  # BA completa
        fecha_armado=None,                   # BB vacía
        armador=None,                        # BC vacía
        fecha_soldadura=None,                # BD vacía
        soldador=None,                       # BE vacía
        arm=ActionStatus.PENDIENTE,          # V=0
        sold=ActionStatus.PENDIENTE          # W=0
    )


@pytest.fixture
def sample_spool_arm_iniciado():
    """Spool con ARM iniciado."""
    return Spool(
        tag_spool="MK-123",
        fecha_materiales=date(2025, 1, 15),
        fecha_armado=None,
        armador="Juan Pérez",            # BC = Juan Pérez
        fecha_soldadura=None,
        soldador=None,
        arm=ActionStatus.EN_PROGRESO,    # V=0.1
        sold=ActionStatus.PENDIENTE
    )


@pytest.fixture
def sample_spool_arm_completado():
    """Spool con ARM completado, SOLD pendiente."""
    return Spool(
        tag_spool="MK-123",
        fecha_materiales=date(2025, 1, 15),
        fecha_armado=date(2025, 1, 20),   # BB completada
        armador="Juan Pérez",
        fecha_soldadura=None,
        soldador=None,
        arm=ActionStatus.COMPLETADO,      # V=1.0
        sold=ActionStatus.PENDIENTE       # W=0
    )


@pytest.fixture
def sample_spool_sold_iniciado():
    """Spool con SOLD iniciado."""
    return Spool(
        tag_spool="MK-123",
        fecha_materiales=date(2025, 1, 15),
        fecha_armado=date(2025, 1, 20),
        armador="Juan Pérez",
        fecha_soldadura=None,
        soldador="Pedro López",          # BE = Pedro López
        arm=ActionStatus.COMPLETADO,
        sold=ActionStatus.EN_PROGRESO    # W=0.1
    )


# ==================== TESTS: INICIAR ACCIÓN ====================

class TestIniciarAccion:
    """Tests para iniciar_accion()."""

    def test_iniciar_arm_exitoso(
        self,
        action_service,
        mock_worker_service,
        mock_spool_service,
        mock_validation_service,
        mock_sheets_repo,
        sample_worker,
        sample_spool_pendiente
    ):
        """Test: Iniciar ARM exitosamente."""
        # Arrange
        mock_worker_service.find_worker_by_nombre.return_value = sample_worker
        mock_spool_service.find_spool_by_tag.return_value = sample_spool_pendiente
        mock_validation_service.validar_puede_iniciar_arm.return_value = None
        mock_sheets_repo.find_row_by_column_value.return_value = 25  # Mock fila

        # Act
        response = action_service.iniciar_accion(
            worker_nombre="Juan Pérez",
            operacion=ActionType.ARM,
            tag_spool="MK-123"
        )

        # Assert
        assert response.success is True
        assert "ARM iniciada exitosamente" in response.message
        assert response.data.tag_spool == "MK-123"
        assert response.data.operacion == "ARM"
        assert response.data.trabajador == "Juan Pérez"
        assert response.data.fila_actualizada == 25
        assert response.data.columna_actualizada == "V"
        assert response.data.valor_nuevo == 0.1
        assert response.data.metadata_actualizada.armador == "Juan Pérez"
        assert response.data.metadata_actualizada.soldador is None

        # Verificar batch_update llamado correctamente
        mock_sheets_repo.batch_update.assert_called_once()
        call_args = mock_sheets_repo.batch_update.call_args[0]
        assert call_args[0] == "Operaciones"
        updates = call_args[1]
        assert len(updates) == 2
        assert updates[0] == {"row": 25, "column": "V", "value": 0.1}
        assert updates[1] == {"row": 25, "column": "BC", "value": "Juan Pérez"}

    def test_iniciar_sold_exitoso(
        self,
        action_service,
        mock_worker_service,
        mock_spool_service,
        mock_validation_service,
        mock_sheets_repo,
        sample_worker,
        sample_spool_arm_completado
    ):
        """Test: Iniciar SOLD exitosamente."""
        # Arrange
        mock_worker_service.find_worker_by_nombre.return_value = sample_worker
        mock_spool_service.find_spool_by_tag.return_value = sample_spool_arm_completado
        mock_validation_service.validar_puede_iniciar_sold.return_value = None
        mock_sheets_repo.find_row_by_column_value.return_value = 25  # Mock fila

        # Act
        response = action_service.iniciar_accion(
            worker_nombre="Juan Pérez",
            operacion=ActionType.SOLD,
            tag_spool="MK-123"
        )

        # Assert
        assert response.success is True
        assert response.data.operacion == "SOLD"
        assert response.data.columna_actualizada == "W"
        assert response.data.metadata_actualizada.soldador == "Juan Pérez"
        assert response.data.metadata_actualizada.armador is None

        # Verificar updates correctos para SOLD
        updates = mock_sheets_repo.batch_update.call_args[0][1]
        assert updates[0] == {"row": 25, "column": "W", "value": 0.1}
        assert updates[1] == {"row": 25, "column": "BE", "value": "Juan Pérez"}

    def test_iniciar_arm_trabajador_no_encontrado(
        self,
        action_service,
        mock_worker_service
    ):
        """Test: Error si trabajador no existe."""
        # Arrange
        mock_worker_service.find_worker_by_nombre.return_value = None

        # Act & Assert
        with pytest.raises(WorkerNoEncontradoError, match="Trabajador 'Inexistente' no encontrado"):
            action_service.iniciar_accion(
                worker_nombre="Inexistente",
                operacion=ActionType.ARM,
                tag_spool="MK-123"
            )

    def test_iniciar_arm_spool_no_encontrado(
        self,
        action_service,
        mock_worker_service,
        mock_spool_service,
        sample_worker
    ):
        """Test: Error si spool no existe."""
        # Arrange
        mock_worker_service.find_worker_by_nombre.return_value = sample_worker
        mock_spool_service.find_spool_by_tag.return_value = None

        # Act & Assert
        with pytest.raises(SpoolNoEncontradoError, match="Spool 'INEXISTENTE' no encontrado"):
            action_service.iniciar_accion(
                worker_nombre="Juan Pérez",
                operacion=ActionType.ARM,
                tag_spool="INEXISTENTE"
            )

    def test_iniciar_arm_ya_iniciado(
        self,
        action_service,
        mock_worker_service,
        mock_spool_service,
        mock_validation_service,
        sample_worker,
        sample_spool_arm_iniciado
    ):
        """Test: Error si ARM ya está iniciado."""
        # Arrange
        mock_worker_service.find_worker_by_nombre.return_value = sample_worker
        mock_spool_service.find_spool_by_tag.return_value = sample_spool_arm_iniciado
        mock_validation_service.validar_puede_iniciar_arm.side_effect = OperacionNoPendienteError(
            tag_spool="MK-123",
            operacion="ARM",
            estado_actual=0.1
        )

        # Act & Assert
        with pytest.raises(OperacionNoPendienteError):
            action_service.iniciar_accion(
                worker_nombre="Juan Pérez",
                operacion=ActionType.ARM,
                tag_spool="MK-123"
            )

    def test_iniciar_arm_dependencias_no_satisfechas(
        self,
        action_service,
        mock_worker_service,
        mock_spool_service,
        mock_validation_service,
        mock_sheets_repo,
        sample_worker
    ):
        """Test: Error si BA está vacía."""
        # Arrange
        spool_sin_materiales = Spool(
            tag_spool="MK-123",
            fecha_materiales=None,  # BA vacía
            fecha_armado=None,
            armador=None,
            fecha_soldadura=None,
            soldador=None,
            arm=ActionStatus.PENDIENTE,
            sold=ActionStatus.PENDIENTE
        )

        mock_sheets_repo.find_row_by_column_value.return_value = 25  # Mock fila

        mock_worker_service.find_worker_by_nombre.return_value = sample_worker
        mock_spool_service.find_spool_by_tag.return_value = spool_sin_materiales
        mock_validation_service.validar_puede_iniciar_arm.side_effect = DependenciasNoSatisfechasError(
            tag_spool="MK-123",
            operacion="ARM",
            dependencia_faltante="fecha_materiales",
            detalle="BA debe estar completada"
        )

        # Act & Assert
        with pytest.raises(DependenciasNoSatisfechasError):
            action_service.iniciar_accion(
                worker_nombre="Juan Pérez",
                operacion=ActionType.ARM,
                tag_spool="MK-123"
            )

    def test_iniciar_sold_dependencias_no_satisfechas(
        self,
        action_service,
        mock_worker_service,
        mock_spool_service,
        mock_validation_service,
        mock_sheets_repo,
        sample_worker,
        sample_spool_pendiente
    ):
        """Test: Error si BB está vacía (ARM no completado)."""
        # Arrange
        mock_worker_service.find_worker_by_nombre.return_value = sample_worker
        mock_spool_service.find_spool_by_tag.return_value = sample_spool_pendiente
        mock_sheets_repo.find_row_by_column_value.return_value = 25  # Mock fila
        mock_validation_service.validar_puede_iniciar_sold.side_effect = DependenciasNoSatisfechasError(
            tag_spool="MK-123",
            operacion="SOLD",
            dependencia_faltante="fecha_armado",
            detalle="BB debe estar completada"
        )

        # Act & Assert
        with pytest.raises(DependenciasNoSatisfechasError):
            action_service.iniciar_accion(
                worker_nombre="Juan Pérez",
                operacion=ActionType.SOLD,
                tag_spool="MK-123"
            )

    def test_iniciar_accion_error_sheets_update(
        self,
        action_service,
        mock_worker_service,
        mock_spool_service,
        mock_validation_service,
        mock_sheets_repo,
        sample_worker,
        sample_spool_pendiente
    ):
        """Test: Error al actualizar Google Sheets."""
        # Arrange
        mock_worker_service.find_worker_by_nombre.return_value = sample_worker
        mock_spool_service.find_spool_by_tag.return_value = sample_spool_pendiente
        mock_validation_service.validar_puede_iniciar_arm.return_value = None
        mock_sheets_repo.find_row_by_column_value.return_value = 25  # Mock fila
        mock_sheets_repo.batch_update.side_effect = Exception("API Error")

        # Act & Assert
        with pytest.raises(SheetsUpdateError, match="Error al actualizar Google Sheets"):
            action_service.iniciar_accion(
                worker_nombre="Juan Pérez",
                operacion=ActionType.ARM,
                tag_spool="MK-123"
            )


# ==================== TESTS: COMPLETAR ACCIÓN ====================

class TestCompletarAccion:
    """Tests para completar_accion()."""

    def test_completar_arm_exitoso(
        self,
        action_service,
        mock_worker_service,
        mock_spool_service,
        mock_validation_service,
        mock_sheets_repo,
        sample_worker,
        sample_spool_arm_iniciado
    ):
        """Test: Completar ARM exitosamente con trabajador correcto."""
        # Arrange
        mock_worker_service.find_worker_by_nombre.return_value = sample_worker
        mock_spool_service.find_spool_by_tag.return_value = sample_spool_arm_iniciado
        mock_validation_service.validar_puede_completar_arm.return_value = None
        mock_sheets_repo.find_row_by_column_value.return_value = 25  # Mock fila

        # Act
        with patch('backend.services.action_service.datetime') as mock_datetime:
            mock_datetime.now.return_value = datetime(2025, 1, 25, 14, 30)
            mock_datetime.strftime = datetime.strftime

            response = action_service.completar_accion(
                worker_nombre="Juan Pérez",
                operacion=ActionType.ARM,
                tag_spool="MK-123"
            )

        # Assert
        assert response.success is True
        assert "ARM completada exitosamente" in response.message
        assert response.data.columna_actualizada == "V"
        assert response.data.valor_nuevo == 1.0
        assert response.data.metadata_actualizada.fecha_armado == "25/01/2025"

        # Verificar batch_update
        updates = mock_sheets_repo.batch_update.call_args[0][1]
        assert len(updates) == 2
        assert updates[0] == {"row": 25, "column": "V", "value": 1.0}
        assert updates[1] == {"row": 25, "column": "BB", "value": "25/01/2025"}

    def test_completar_sold_exitoso(
        self,
        action_service,
        mock_worker_service,
        mock_spool_service,
        mock_validation_service,
        mock_sheets_repo,
        sample_spool_sold_iniciado
    ):
        """Test: Completar SOLD exitosamente."""
        # Arrange
        soldador = Worker(nombre="Pedro", apellido="López", activo=True)
        mock_worker_service.find_worker_by_nombre.return_value = soldador
        mock_spool_service.find_spool_by_tag.return_value = sample_spool_sold_iniciado
        mock_validation_service.validar_puede_completar_sold.return_value = None
        mock_sheets_repo.find_row_by_column_value.return_value = 25  # Mock fila

        # Act
        with patch('backend.services.action_service.datetime') as mock_datetime:
            mock_datetime.now.return_value = datetime(2025, 1, 26, 10, 0)
            mock_datetime.strftime = datetime.strftime

            response = action_service.completar_accion(
                worker_nombre="Pedro López",
                operacion=ActionType.SOLD,
                tag_spool="MK-123"
            )

        # Assert
        assert response.success is True
        assert response.data.operacion == "SOLD"
        assert response.data.columna_actualizada == "W"

        # Verificar updates para SOLD
        updates = mock_sheets_repo.batch_update.call_args[0][1]
        assert updates[0] == {"row": 25, "column": "W", "value": 1.0}
        assert updates[1] == {"row": 25, "column": "BD", "value": "26/01/2025"}

    def test_completar_arm_trabajador_incorrecto(
        self,
        action_service,
        mock_worker_service,
        mock_spool_service,
        mock_validation_service,
        mock_sheets_repo,
        sample_spool_arm_iniciado
    ):
        """Test CRÍTICO: Error si trabajador != quien inició (BC mismatch)."""
        # Arrange
        otro_trabajador = Worker(nombre="Pedro", apellido="López", activo=True)
        mock_worker_service.find_worker_by_nombre.return_value = otro_trabajador
        mock_spool_service.find_spool_by_tag.return_value = sample_spool_arm_iniciado  # BC="Juan Pérez"
        mock_sheets_repo.find_row_by_column_value.return_value = 25  # Mock fila

        # ValidationService detecta mismatch
        mock_validation_service.validar_puede_completar_arm.side_effect = NoAutorizadoError(
            tag_spool="MK-123",
            trabajador_esperado="Juan Pérez",
            trabajador_solicitante="Pedro López",
            operacion="ARM"
        )

        # Act & Assert
        with pytest.raises(NoAutorizadoError):
            action_service.completar_accion(
                worker_nombre="Pedro López",  # Diferente a BC
                operacion=ActionType.ARM,
                tag_spool="MK-123"
            )

        # Verificar que NO se llamó batch_update
        mock_sheets_repo.batch_update.assert_not_called()

    def test_completar_sold_trabajador_incorrecto(
        self,
        action_service,
        mock_worker_service,
        mock_spool_service,
        mock_validation_service,
        mock_sheets_repo,
        sample_spool_sold_iniciado
    ):
        """Test CRÍTICO: Error si trabajador != quien inició SOLD (BE mismatch)."""
        # Arrange
        otro_trabajador = Worker(nombre="Juan", apellido="Pérez", activo=True)
        mock_worker_service.find_worker_by_nombre.return_value = otro_trabajador
        mock_spool_service.find_spool_by_tag.return_value = sample_spool_sold_iniciado  # BE="Pedro López"
        mock_sheets_repo.find_row_by_column_value.return_value = 25  # Mock fila

        mock_validation_service.validar_puede_completar_sold.side_effect = NoAutorizadoError(
            tag_spool="MK-123",
            trabajador_esperado="Pedro López",
            trabajador_solicitante="Juan Pérez",
            operacion="SOLD"
        )

        # Act & Assert
        with pytest.raises(NoAutorizadoError):
            action_service.completar_accion(
                worker_nombre="Juan Pérez",  # Diferente a BE
                operacion=ActionType.SOLD,
                tag_spool="MK-123"
            )

    def test_completar_arm_no_iniciado(
        self,
        action_service,
        mock_worker_service,
        mock_spool_service,
        mock_validation_service,
        mock_sheets_repo,
        sample_worker,
        sample_spool_pendiente
    ):
        """Test: Error si ARM no está iniciado (V=0)."""
        # Arrange
        mock_worker_service.find_worker_by_nombre.return_value = sample_worker
        mock_spool_service.find_spool_by_tag.return_value = sample_spool_pendiente
        mock_sheets_repo.find_row_by_column_value.return_value = 25  # Mock fila
        mock_validation_service.validar_puede_completar_arm.side_effect = OperacionNoIniciadaError(
            tag_spool="MK-123",
            operacion="ARM"
        )

        # Act & Assert
        with pytest.raises(OperacionNoIniciadaError):
            action_service.completar_accion(
                worker_nombre="Juan Pérez",
                operacion=ActionType.ARM,
                tag_spool="MK-123"
            )

    def test_completar_arm_ya_completado(
        self,
        action_service,
        mock_worker_service,
        mock_spool_service,
        mock_validation_service,
        mock_sheets_repo,
        sample_worker,
        sample_spool_arm_completado
    ):
        """Test: Error si ARM ya está completado (V=1.0)."""
        # Arrange
        mock_worker_service.find_worker_by_nombre.return_value = sample_worker
        mock_spool_service.find_spool_by_tag.return_value = sample_spool_arm_completado
        mock_sheets_repo.find_row_by_column_value.return_value = 25  # Mock fila
        mock_validation_service.validar_puede_completar_arm.side_effect = OperacionYaCompletadaError(
            tag_spool="MK-123",
            operacion="ARM"
        )

        # Act & Assert
        with pytest.raises(OperacionYaCompletadaError):
            action_service.completar_accion(
                worker_nombre="Juan Pérez",
                operacion=ActionType.ARM,
                tag_spool="MK-123"
            )

    def test_completar_accion_trabajador_no_encontrado(
        self,
        action_service,
        mock_worker_service
    ):
        """Test: Error si trabajador no existe."""
        # Arrange
        mock_worker_service.find_worker_by_nombre.return_value = None

        # Act & Assert
        with pytest.raises(WorkerNoEncontradoError):
            action_service.completar_accion(
                worker_nombre="Inexistente",
                operacion=ActionType.ARM,
                tag_spool="MK-123"
            )

    def test_completar_accion_spool_no_encontrado(
        self,
        action_service,
        mock_worker_service,
        mock_spool_service,
        sample_worker
    ):
        """Test: Error si spool no existe."""
        # Arrange
        mock_worker_service.find_worker_by_nombre.return_value = sample_worker
        mock_spool_service.find_spool_by_tag.return_value = None

        # Act & Assert
        with pytest.raises(SpoolNoEncontradoError):
            action_service.completar_accion(
                worker_nombre="Juan Pérez",
                operacion=ActionType.ARM,
                tag_spool="INEXISTENTE"
            )

    def test_completar_accion_con_timestamp_custom(
        self,
        action_service,
        mock_worker_service,
        mock_spool_service,
        mock_validation_service,
        mock_sheets_repo,
        sample_worker,
        sample_spool_arm_iniciado
    ):
        """Test: Usar timestamp provisto en lugar de fecha actual."""
        # Arrange
        mock_worker_service.find_worker_by_nombre.return_value = sample_worker
        mock_spool_service.find_spool_by_tag.return_value = sample_spool_arm_iniciado
        mock_validation_service.validar_puede_completar_arm.return_value = None
        mock_sheets_repo.find_row_by_column_value.return_value = 25  # Mock fila

        # Act
        response = action_service.completar_accion(
            worker_nombre="Juan Pérez",
            operacion=ActionType.ARM,
            tag_spool="MK-123",
            timestamp=datetime(2024, 12, 31, 23, 59)  # Fecha custom
        )

        # Assert
        assert response.data.metadata_actualizada.fecha_armado == "31/12/2024"

        # Verificar batch_update con fecha custom
        updates = mock_sheets_repo.batch_update.call_args[0][1]
        assert updates[1] == {"row": 25, "column": "BB", "value": "31/12/2024"}

    def test_completar_accion_error_sheets_update(
        self,
        action_service,
        mock_worker_service,
        mock_spool_service,
        mock_validation_service,
        mock_sheets_repo,
        sample_worker,
        sample_spool_arm_iniciado
    ):
        """Test: Error al actualizar Google Sheets."""
        # Arrange
        mock_worker_service.find_worker_by_nombre.return_value = sample_worker
        mock_spool_service.find_spool_by_tag.return_value = sample_spool_arm_iniciado
        mock_validation_service.validar_puede_completar_arm.return_value = None
        mock_sheets_repo.find_row_by_column_value.return_value = 25  # Mock fila
        mock_sheets_repo.batch_update.side_effect = Exception("Network timeout")

        # Act & Assert
        with pytest.raises(SheetsUpdateError):
            action_service.completar_accion(
                worker_nombre="Juan Pérez",
                operacion=ActionType.ARM,
                tag_spool="MK-123"
            )


# ==================== TESTS: EDGE CASES ====================

class TestEdgeCases:
    """Tests para casos edge."""

    def test_format_fecha_sin_timestamp(self, action_service):
        """Test: Fecha actual cuando no se provee timestamp."""
        with patch('backend.services.action_service.datetime') as mock_datetime:
            mock_datetime.now.return_value = datetime(2025, 1, 15, 10, 0)
            mock_datetime.strftime = datetime.strftime

            fecha = action_service._format_fecha(None)

            assert fecha == "15/01/2025"

    def test_format_fecha_con_timestamp(self, action_service):
        """Test: Usa timestamp provisto correctamente."""
        fecha = action_service._format_fecha(datetime(2024, 12, 31, 23, 59))
        assert fecha == "31/12/2024"

    def test_get_column_names_operacion_invalida(self, action_service):
        """Test: Error con operación no soportada."""
        with pytest.raises(ValueError, match="Operación inválida"):
            action_service._get_column_names("INVALID")
