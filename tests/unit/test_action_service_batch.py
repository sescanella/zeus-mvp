"""
Tests para operaciones batch en ActionService (v2.0 multiselect).

Cobertura:
- Batch exitoso (todos los spools procesados)
- Batch con errores parciales (algunos spools fallan)
- Batch con todos los errores (ningún spool procesado)
- Validación límites (máx 50 spools)
- Ownership validation en batch completar
- Performance batch (< 3 seg para 10 spools)

Fixtures:
- action_service_batch: ActionService con mocks configurados
- mock_metadata_repo_batch: MetadataRepository mockeado
- mock_validation_service_batch: ValidationService mockeado
- mock_spool_service_batch: SpoolService mockeado
- mock_worker_service_batch: WorkerService mockeado
"""

import pytest
from unittest.mock import MagicMock, patch
from datetime import datetime
import time

from backend.services.action_service import ActionService
from backend.models.enums import ActionType
from backend.models.worker import Worker
from backend.models.spool import Spool
from backend.models.action import ActionResponse, ActionData, ActionMetadata
from backend.exceptions import (
    WorkerNoEncontradoError,
    SpoolNoEncontradoError,
    OperacionYaIniciadaError,
    NoAutorizadoError
)


# ============================================================================
# FIXTURES
# ============================================================================

@pytest.fixture
def mock_metadata_repo_batch():
    """MetadataRepository mockeado para batch tests."""
    repo = MagicMock()
    repo.append_event = MagicMock(return_value=None)
    return repo


@pytest.fixture
def mock_validation_service_batch(mock_metadata_repo_batch):
    """ValidationService mockeado para batch tests."""
    service = MagicMock()
    service.validar_puede_iniciar_arm = MagicMock(return_value=None)
    service.validar_puede_iniciar_sold = MagicMock(return_value=None)
    service.validar_puede_completar_arm = MagicMock(return_value=None)
    service.validar_puede_completar_sold = MagicMock(return_value=None)
    service.validar_puede_cancelar = MagicMock(return_value=None)  # v2.0: CANCELAR batch
    return service


@pytest.fixture
def mock_spool_service_batch():
    """SpoolService mockeado para batch tests."""
    service = MagicMock()

    def find_spool_side_effect(tag_spool: str):
        """Retorna spools válidos para tags conocidos."""
        if tag_spool.startswith("MK-1335"):
            return Spool(
                tag_spool=tag_spool,
                fecha_materiales="2025-11-15",  # Formato ISO: YYYY-MM-DD
                estado_armado=0.0,
                estado_soldado=0.0,
                armador=None,
                soldador=None,
                fecha_armado=None,
                fecha_soldadura=None
            )
        return None  # Spool no encontrado

    service.find_spool_by_tag = MagicMock(side_effect=find_spool_side_effect)
    return service


@pytest.fixture
def mock_worker_service_batch():
    """WorkerService mockeado para batch tests."""
    service = MagicMock()

    def find_worker_side_effect(worker_id: int):
        """Retorna workers válidos para IDs conocidos."""
        workers = {
            93: Worker(id=93, nombre="Mauricio", apellido="Rodriguez", activo=True, rol=None),
            94: Worker(id=94, nombre="Carlos", apellido="Pimiento", activo=True, rol=None),
            95: Worker(id=95, nombre="Yesid", apellido="Duarte", activo=True, rol=None),
        }
        return workers.get(worker_id)

    service.find_worker_by_id = MagicMock(side_effect=find_worker_side_effect)
    return service


@pytest.fixture
def action_service_batch(
    mock_metadata_repo_batch,
    mock_validation_service_batch,
    mock_spool_service_batch,
    mock_worker_service_batch
):
    """ActionService configurado para batch tests."""
    return ActionService(
        metadata_repository=mock_metadata_repo_batch,
        validation_service=mock_validation_service_batch,
        spool_service=mock_spool_service_batch,
        worker_service=mock_worker_service_batch
    )


# ============================================================================
# TESTS INICIAR BATCH - CASOS EXITOSOS
# ============================================================================

def test_iniciar_batch_todos_exitosos(action_service_batch):
    """
    Test: Batch INICIAR ARM con 3 spools, todos exitosos.

    Dado:
    - Worker 93 (Mauricio Rodriguez)
    - 3 spools pendientes (MK-1335-CW-25238-011, 012, 013)

    Cuando:
    - Se llama iniciar_accion_batch() con 3 tags

    Entonces:
    - BatchActionResponse.success = True
    - total=3, exitosos=3, fallidos=0
    - 3 resultados individuales exitosos
    - Cada resultado tiene evento_id
    """
    # Arrange
    worker_id = 93
    operacion = ActionType.ARM
    tag_spools = [
        "MK-1335-CW-25238-011",
        "MK-1335-CW-25238-012",
        "MK-1335-CW-25238-013"
    ]

    # Act
    response = action_service_batch.iniciar_accion_batch(
        worker_id=worker_id,
        operacion=operacion,
        tag_spools=tag_spools
    )

    # Assert
    assert response.success is True
    assert response.total == 3
    assert response.exitosos == 3
    assert response.fallidos == 0
    assert len(response.resultados) == 3
    assert "3 de 3 spools exitosos" in response.message

    # Verificar resultados individuales
    for resultado in response.resultados:
        assert resultado.success is True
        assert resultado.evento_id is not None  # SÍ extraemos evento_id del mensaje
        assert resultado.error_type is None
        assert "ARM iniciada exitosamente" in resultado.message


def test_iniciar_batch_un_spool(action_service_batch):
    """
    Test: Batch INICIAR ARM con 1 solo spool.

    Dado:
    - Worker 93
    - 1 spool pendiente

    Cuando:
    - Se llama iniciar_accion_batch() con 1 tag

    Entonces:
    - BatchActionResponse.success = True
    - total=1, exitosos=1, fallidos=0
    """
    # Arrange
    worker_id = 93
    operacion = ActionType.ARM
    tag_spools = ["MK-1335-CW-25238-011"]

    # Act
    response = action_service_batch.iniciar_accion_batch(
        worker_id=worker_id,
        operacion=operacion,
        tag_spools=tag_spools
    )

    # Assert
    assert response.success is True
    assert response.total == 1
    assert response.exitosos == 1
    assert response.fallidos == 0
    assert "1 de 1 spools exitosos" in response.message


# ============================================================================
# TESTS INICIAR BATCH - ERRORES PARCIALES
# ============================================================================

def test_iniciar_batch_errores_parciales(action_service_batch, mock_validation_service_batch):
    """
    Test: Batch INICIAR ARM con 3 spools, 1 ya iniciado.

    Dado:
    - Worker 93
    - 3 spools: 2 pendientes, 1 ya iniciado

    Cuando:
    - Se llama iniciar_accion_batch() con 3 tags
    - ValidationService lanza OperacionYaIniciadaError para spool 012

    Entonces:
    - BatchActionResponse.success = True (al menos 2 exitosos)
    - total=3, exitosos=2, fallidos=1
    - 2 resultados exitosos, 1 fallido con error_type
    """
    # Arrange
    worker_id = 93
    operacion = ActionType.ARM
    tag_spools = [
        "MK-1335-CW-25238-011",  # Éxito
        "MK-1335-CW-25238-012",  # Ya iniciado
        "MK-1335-CW-25238-013"   # Éxito
    ]

    # Mock: spool 012 ya iniciado
    def validar_side_effect(spool, **kwargs):
        if spool.tag_spool == "MK-1335-CW-25238-012":
            raise OperacionYaIniciadaError(
                tag_spool=spool.tag_spool,
                operacion="ARM",
                trabajador="Otro Trabajador"
            )

    mock_validation_service_batch.validar_puede_iniciar_arm.side_effect = validar_side_effect

    # Act
    response = action_service_batch.iniciar_accion_batch(
        worker_id=worker_id,
        operacion=operacion,
        tag_spools=tag_spools
    )

    # Assert
    assert response.success is True  # Al menos 1 exitoso
    assert response.total == 3
    assert response.exitosos == 2
    assert response.fallidos == 1
    assert ("2 de 3 spools exitosos (1 fallo)" in response.message or
            "2 de 3 spools exitosos (1 fallos)" in response.message)  # Aceptar singular o plural

    # Verificar resultado fallido
    resultado_fallido = next(r for r in response.resultados if not r.success)
    assert resultado_fallido.tag_spool == "MK-1335-CW-25238-012"
    assert resultado_fallido.error_type == "OperacionYaIniciadaError"
    assert "iniciada" in resultado_fallido.message  # Acepta "ya iniciada" o "está iniciada"


def test_iniciar_batch_spool_no_encontrado(action_service_batch, mock_spool_service_batch):
    """
    Test: Batch INICIAR con 3 spools, 1 no encontrado.

    Dado:
    - Worker 93
    - 3 spools: 2 existen, 1 no existe en Sheets

    Cuando:
    - SpoolService retorna None para spool "INVALID-TAG"

    Entonces:
    - total=3, exitosos=2, fallidos=1
    - 1 resultado con error_type="SpoolNoEncontradoError"
    """
    # Arrange
    worker_id = 93
    operacion = ActionType.ARM
    tag_spools = [
        "MK-1335-CW-25238-011",  # Éxito
        "INVALID-TAG",           # No encontrado
        "MK-1335-CW-25238-013"   # Éxito
    ]

    # Act
    response = action_service_batch.iniciar_accion_batch(
        worker_id=worker_id,
        operacion=operacion,
        tag_spools=tag_spools
    )

    # Assert
    assert response.success is True
    assert response.total == 3
    assert response.exitosos == 2
    assert response.fallidos == 1

    # Verificar resultado fallido
    resultado_fallido = next(r for r in response.resultados if not r.success)
    assert resultado_fallido.tag_spool == "INVALID-TAG"
    assert resultado_fallido.error_type == "SpoolNoEncontradoError"


# ============================================================================
# TESTS INICIAR BATCH - TODOS ERRORES
# ============================================================================

def test_iniciar_batch_todos_fallidos(action_service_batch, mock_validation_service_batch):
    """
    Test: Batch INICIAR con 3 spools, todos ya iniciados.

    Dado:
    - Worker 93
    - 3 spools ya iniciados

    Cuando:
    - ValidationService lanza OperacionYaIniciadaError para todos

    Entonces:
    - BatchActionResponse.success = False (0 exitosos)
    - total=3, exitosos=0, fallidos=3
    """
    # Arrange
    worker_id = 93
    operacion = ActionType.ARM
    tag_spools = [
        "MK-1335-CW-25238-011",
        "MK-1335-CW-25238-012",
        "MK-1335-CW-25238-013"
    ]

    # Mock: todos ya iniciados
    def validar_side_effect(spool, **kwargs):
        raise OperacionYaIniciadaError(
            tag_spool=spool.tag_spool,
            operacion="ARM",
            trabajador="Otro Trabajador"
        )

    mock_validation_service_batch.validar_puede_iniciar_arm.side_effect = validar_side_effect

    # Act
    response = action_service_batch.iniciar_accion_batch(
        worker_id=worker_id,
        operacion=operacion,
        tag_spools=tag_spools
    )

    # Assert
    assert response.success is False  # 0 exitosos
    assert response.total == 3
    assert response.exitosos == 0
    assert response.fallidos == 3
    assert "0 de 3 spools" in response.message or "3 fallos" in response.message


# ============================================================================
# TESTS COMPLETAR BATCH - CASOS EXITOSOS
# ============================================================================

def test_completar_batch_todos_exitosos(action_service_batch):
    """
    Test: Batch COMPLETAR ARM con 3 spools, todos exitosos.

    Dado:
    - Worker 93 (quien inició todos)
    - 3 spools en estado EN_PROGRESO

    Cuando:
    - Se llama completar_accion_batch() con 3 tags

    Entonces:
    - BatchActionResponse.success = True
    - total=3, exitosos=3, fallidos=0
    """
    # Arrange
    worker_id = 93
    operacion = ActionType.ARM
    tag_spools = [
        "MK-1335-CW-25238-011",
        "MK-1335-CW-25238-012",
        "MK-1335-CW-25238-013"
    ]

    # Act
    response = action_service_batch.completar_accion_batch(
        worker_id=worker_id,
        operacion=operacion,
        tag_spools=tag_spools
    )

    # Assert
    assert response.success is True
    assert response.total == 3
    assert response.exitosos == 3
    assert response.fallidos == 0
    assert "3 de 3 spools exitosos" in response.message


# ============================================================================
# TESTS COMPLETAR BATCH - OWNERSHIP VALIDATION
# ============================================================================

def test_completar_batch_ownership_error(action_service_batch, mock_validation_service_batch):
    """
    Test: Batch COMPLETAR ARM con ownership violation.

    Dado:
    - Worker 94 (Carlos) intenta completar
    - 3 spools iniciados por Worker 93 (Mauricio)

    Cuando:
    - ValidationService lanza NoAutorizadoError para todos

    Entonces:
    - BatchActionResponse.success = False
    - total=3, exitosos=0, fallidos=3
    - Todos los resultados con error_type="NoAutorizadoError"
    """
    # Arrange
    worker_id = 94  # Carlos intenta completar
    operacion = ActionType.ARM
    tag_spools = [
        "MK-1335-CW-25238-011",  # Iniciado por Mauricio (93)
        "MK-1335-CW-25238-012",
        "MK-1335-CW-25238-013"
    ]

    # Mock: ownership violation
    def validar_side_effect(spool, **kwargs):
        raise NoAutorizadoError(
            tag_spool=spool.tag_spool,
            trabajador_esperado="Mauricio Rodriguez",
            trabajador_solicitante="Carlos Pimiento",
            operacion="ARM"
        )

    mock_validation_service_batch.validar_puede_completar_arm.side_effect = validar_side_effect

    # Act
    response = action_service_batch.completar_accion_batch(
        worker_id=worker_id,
        operacion=operacion,
        tag_spools=tag_spools
    )

    # Assert
    assert response.success is False
    assert response.total == 3
    assert response.exitosos == 0
    assert response.fallidos == 3

    # Verificar que todos tienen ownership error
    for resultado in response.resultados:
        assert resultado.success is False
        assert resultado.error_type == "NoAutorizadoError"
        assert "Mauricio Rodriguez" in resultado.message


def test_completar_batch_ownership_parcial(action_service_batch, mock_validation_service_batch):
    """
    Test: Batch COMPLETAR con ownership parcial.

    Dado:
    - Worker 93 intenta completar 3 spools
    - 2 iniciados por él, 1 iniciado por Worker 94

    Cuando:
    - ValidationService lanza NoAutorizadoError para 1 spool

    Entonces:
    - total=3, exitosos=2, fallidos=1
    - 1 resultado con ownership error
    """
    # Arrange
    worker_id = 93
    operacion = ActionType.ARM
    tag_spools = [
        "MK-1335-CW-25238-011",  # Iniciado por 93 - OK
        "MK-1335-CW-25238-012",  # Iniciado por 94 - ERROR
        "MK-1335-CW-25238-013"   # Iniciado por 93 - OK
    ]

    # Mock: ownership error solo para spool 012
    def validar_side_effect(spool, **kwargs):
        if spool.tag_spool == "MK-1335-CW-25238-012":
            raise NoAutorizadoError(
                tag_spool=spool.tag_spool,
                trabajador_esperado="Carlos Pimiento",
                trabajador_solicitante="Mauricio Rodriguez",
                operacion="ARM"
            )

    mock_validation_service_batch.validar_puede_completar_arm.side_effect = validar_side_effect

    # Act
    response = action_service_batch.completar_accion_batch(
        worker_id=worker_id,
        operacion=operacion,
        tag_spools=tag_spools
    )

    # Assert
    assert response.success is True  # 2 exitosos
    assert response.total == 3
    assert response.exitosos == 2
    assert response.fallidos == 1

    # Verificar resultado con ownership error
    resultado_fallido = next(r for r in response.resultados if not r.success)
    assert resultado_fallido.tag_spool == "MK-1335-CW-25238-012"
    assert resultado_fallido.error_type == "NoAutorizadoError"


# ============================================================================
# TESTS VALIDACIÓN LÍMITES
# ============================================================================

def test_iniciar_batch_limite_50_spools(action_service_batch):
    """
    Test: Batch INICIAR con exactamente 50 spools (límite máximo).

    Dado:
    - 50 spools pendientes

    Cuando:
    - Se llama iniciar_accion_batch() con 50 tags

    Entonces:
    - No lanza excepción
    - Procesa los 50 spools exitosamente
    """
    # Arrange
    worker_id = 93
    operacion = ActionType.ARM
    tag_spools = [f"MK-1335-CW-25238-{i:03d}" for i in range(1, 51)]  # 50 spools

    # Act
    response = action_service_batch.iniciar_accion_batch(
        worker_id=worker_id,
        operacion=operacion,
        tag_spools=tag_spools
    )

    # Assert
    assert response.total == 50
    assert response.exitosos == 50
    assert response.fallidos == 0


def test_iniciar_batch_excede_limite_51_spools(action_service_batch):
    """
    Test: Batch INICIAR con 51 spools (excede límite).

    Dado:
    - 51 spools pendientes

    Cuando:
    - Se llama iniciar_accion_batch() con 51 tags

    Entonces:
    - Lanza ValueError "Batch limitado a 50 spools"
    """
    # Arrange
    worker_id = 93
    operacion = ActionType.ARM
    tag_spools = [f"MK-1335-CW-25238-{i:03d}" for i in range(1, 52)]  # 51 spools

    # Act & Assert
    with pytest.raises(ValueError) as exc_info:
        action_service_batch.iniciar_accion_batch(
            worker_id=worker_id,
            operacion=operacion,
            tag_spools=tag_spools
        )

    assert "Batch limitado a 50 spools" in str(exc_info.value)
    assert "51" in str(exc_info.value)


def test_iniciar_batch_vacio(action_service_batch):
    """
    Test: Batch INICIAR con lista vacía.

    Dado:
    - tag_spools = []

    Cuando:
    - Se llama iniciar_accion_batch()

    Entonces:
    - Lanza ValueError "tag_spools no puede estar vacío"
    """
    # Arrange
    worker_id = 93
    operacion = ActionType.ARM
    tag_spools = []

    # Act & Assert
    with pytest.raises(ValueError) as exc_info:
        action_service_batch.iniciar_accion_batch(
            worker_id=worker_id,
            operacion=operacion,
            tag_spools=tag_spools
        )

    assert "tag_spools no puede estar vacío" in str(exc_info.value)


# ============================================================================
# TESTS PERFORMANCE
# ============================================================================

def test_batch_performance_10_spools(action_service_batch):
    """
    Test: Performance batch con 10 spools.

    Dado:
    - 10 spools pendientes

    Cuando:
    - Se llama iniciar_accion_batch() con 10 tags

    Entonces:
    - Tiempo total < 3 segundos
    - Procesa los 10 spools exitosamente
    """
    # Arrange
    worker_id = 93
    operacion = ActionType.ARM
    tag_spools = [f"MK-1335-CW-25238-{i:03d}" for i in range(1, 11)]  # 10 spools

    # Act
    start_time = time.time()
    response = action_service_batch.iniciar_accion_batch(
        worker_id=worker_id,
        operacion=operacion,
        tag_spools=tag_spools
    )
    elapsed_time = time.time() - start_time

    # Assert
    assert elapsed_time < 3.0, f"Batch tardó {elapsed_time:.2f}s (límite: 3s)"
    assert response.total == 10
    assert response.exitosos == 10


# ============================================================================
# TESTS OPERACIÓN SOLD (Soldado)
# ============================================================================

def test_iniciar_batch_sold_exitoso(action_service_batch):
    """
    Test: Batch INICIAR SOLD con 3 spools exitosos.

    Dado:
    - Worker 94 (Carlos - Soldador)
    - 3 spools con ARM completado

    Cuando:
    - Se llama iniciar_accion_batch() SOLD con 3 tags

    Entonces:
    - total=3, exitosos=3, fallidos=0
    """
    # Arrange
    worker_id = 94
    operacion = ActionType.SOLD
    tag_spools = [
        "MK-1335-CW-25238-011",
        "MK-1335-CW-25238-012",
        "MK-1335-CW-25238-013"
    ]

    # Act
    response = action_service_batch.iniciar_accion_batch(
        worker_id=worker_id,
        operacion=operacion,
        tag_spools=tag_spools
    )

    # Assert
    assert response.success is True
    assert response.total == 3
    assert response.exitosos == 3
    assert response.fallidos == 0
    assert "SOLD iniciado" in response.message


def test_completar_batch_sold_exitoso(action_service_batch):
    """
    Test: Batch COMPLETAR SOLD con 3 spools exitosos.

    Dado:
    - Worker 94 (quien inició SOLD)
    - 3 spools en estado SOLD EN_PROGRESO

    Cuando:
    - Se llama completar_accion_batch() SOLD con 3 tags

    Entonces:
    - total=3, exitosos=3, fallidos=0
    """
    # Arrange
    worker_id = 94
    operacion = ActionType.SOLD
    tag_spools = [
        "MK-1335-CW-25238-011",
        "MK-1335-CW-25238-012",
        "MK-1335-CW-25238-013"
    ]

    # Act
    response = action_service_batch.completar_accion_batch(
        worker_id=worker_id,
        operacion=operacion,
        tag_spools=tag_spools
    )

    # Assert
    assert response.success is True
    assert response.total == 3
    assert response.exitosos == 3
    assert response.fallidos == 0
    assert "SOLD completado" in response.message


# ================================
# CANCELAR BATCH TESTS (v2.0 CANCELAR feature)
# ================================


def test_cancelar_accion_batch_success(action_service_batch):
    """
    Test: Batch CANCELAR ARM con 3 spools exitosos.

    Dado:
    - Worker 93 (quien inició ARM en los 3 spools)
    - 3 spools en estado ARM EN_PROGRESO

    Cuando:
    - Se llama cancelar_accion_batch() ARM con 3 tags

    Entonces:
    - total=3, exitosos=3, fallidos=0
    - Todos los spools se cancelan exitosamente
    """
    # Arrange
    worker_id = 93
    operacion = ActionType.ARM
    tag_spools = [
        "MK-1335-CW-25238-011",
        "MK-1335-CW-25238-012",
        "MK-1335-CW-25238-013"
    ]

    # Act
    response = action_service_batch.cancelar_accion_batch(
        worker_id=worker_id,
        operacion=operacion,
        tag_spools=tag_spools
    )

    # Assert
    assert response.success is True
    assert response.total == 3
    assert response.exitosos == 3
    assert response.fallidos == 0
    assert "ARM cancelado" in response.message
    assert len(response.resultados) == 3
    for resultado in response.resultados:
        assert resultado.success is True
        assert resultado.evento_id is not None
        assert resultado.error_type is None


def test_cancelar_accion_batch_partial_errors(action_service_batch):
    """
    Test: Batch CANCELAR ARM con errores parciales (algunos spools no están EN_PROGRESO).

    Dado:
    - Worker 93
    - 3 spools: 2 EN_PROGRESO (iniciados por 93), 1 PENDIENTE (no iniciado)

    Cuando:
    - Se llama cancelar_accion_batch() ARM con 3 tags

    Entonces:
    - total=3, exitosos=2, fallidos=1
    - 2 spools se cancelan exitosamente
    - 1 spool falla con OperacionNoIniciadaError
    """
    # Arrange
    worker_id = 93
    operacion = ActionType.ARM
    tag_spools = [
        "MK-1335-CW-25238-011",  # EN_PROGRESO (éxito)
        "MK-1335-CW-25238-012",  # EN_PROGRESO (éxito)
        "MK-1335-CW-25238-021"   # PENDIENTE (falla - no está EN_PROGRESO)
    ]

    # Configurar mock para simular estado PENDIENTE en tercer spool
    from backend.exceptions import OperacionNoIniciadaError

    def validar_cancelar_side_effect(spool, operacion, worker_nombre, worker_id):
        if spool.tag_spool == "MK-1335-CW-25238-021":
            raise OperacionNoIniciadaError(
                tag_spool=spool.tag_spool,
                operacion=operacion
            )
        return None  # Otros spools OK

    action_service_batch.validation_service.validar_puede_cancelar.side_effect = validar_cancelar_side_effect

    # Act
    response = action_service_batch.cancelar_accion_batch(
        worker_id=worker_id,
        operacion=operacion,
        tag_spools=tag_spools
    )

    # Assert
    assert response.success is True  # Al menos 1 exitoso
    assert response.total == 3
    assert response.exitosos == 2
    assert response.fallidos == 1
    assert "2 de 3" in response.message

    # Verificar resultados individuales
    exitosos = [r for r in response.resultados if r.success]
    fallidos = [r for r in response.resultados if not r.success]

    assert len(exitosos) == 2
    assert len(fallidos) == 1
    assert fallidos[0].error_type == "OperacionNoIniciadaError"


def test_cancelar_accion_batch_ownership_violation(action_service_batch):
    """
    Test: Batch CANCELAR ARM con violación de ownership (worker diferente intenta cancelar).

    Dado:
    - Worker 94 (NO inició ARM en ningún spool)
    - 3 spools en ARM EN_PROGRESO (iniciados por worker 93)

    Cuando:
    - Se llama cancelar_accion_batch() ARM con worker 94 (quien NO inició)

    Entonces:
    - total=3, exitosos=0, fallidos=3
    - Todos los spools fallan con NoAutorizadoError (ownership violation)
    """
    # Arrange
    worker_id = 94  # Worker diferente (93 inició ARM)
    operacion = ActionType.ARM
    tag_spools = [
        "MK-1335-CW-25238-011",
        "MK-1335-CW-25238-012",
        "MK-1335-CW-25238-013"
    ]

    # Configurar mock para simular ownership violation
    # Worker 94 intenta cancelar spools iniciados por worker 93
    def validar_cancelar_ownership_side_effect(spool, operacion, worker_nombre, worker_id):
        # Worker 94 (Carlos Pimiento) NO puede cancelar spools de worker 93 (Mauricio Rodriguez)
        raise NoAutorizadoError(
            tag_spool=spool.tag_spool,
            trabajador_esperado="Mauricio Rodriguez",  # Quien inició
            trabajador_solicitante=worker_nombre,  # Carlos Pimiento
            operacion=operacion
        )

    action_service_batch.validation_service.validar_puede_cancelar.side_effect = validar_cancelar_ownership_side_effect

    # Act
    response = action_service_batch.cancelar_accion_batch(
        worker_id=worker_id,
        operacion=operacion,
        tag_spools=tag_spools
    )

    # Assert
    assert response.success is False  # Todos fallaron
    assert response.total == 3
    assert response.exitosos == 0
    assert response.fallidos == 3
    assert "0 de 3" in response.message

    # Verificar que todos los resultados son ownership errors
    for resultado in response.resultados:
        assert resultado.success is False
        assert resultado.error_type == "NoAutorizadoError"
        assert "Solo" in resultado.message  # Mensaje de ownership


def test_cancelar_accion_batch_limit_validation(action_service_batch):
    """
    Test: Batch CANCELAR ARM con límite de 50 spools superado.

    Dado:
    - 51 tags de spools (excede límite de 50)

    Cuando:
    - Se llama cancelar_accion_batch() ARM con 51 tags

    Entonces:
    - Lanza ValueError con mensaje "Batch limitado a 50 spools"
    """
    # Arrange
    worker_id = 93
    operacion = ActionType.ARM
    tag_spools = [f"MK-{i:04d}" for i in range(51)]  # 51 spools

    # Act & Assert
    with pytest.raises(ValueError) as excinfo:
        action_service_batch.cancelar_accion_batch(
            worker_id=worker_id,
            operacion=operacion,
            tag_spools=tag_spools
        )

    assert "Batch limitado a 50 spools" in str(excinfo.value)
    assert "51" in str(excinfo.value)
