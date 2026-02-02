"""
Unit tests for union query endpoints (v4.0 Phase 11).

Tests for GET /api/v4/uniones/{tag}/disponibles and /api/v4/uniones/{tag}/metricas.
"""
import pytest
from unittest.mock import Mock, MagicMock
from fastapi.testclient import TestClient

from backend.main import app
from backend.core.dependency import get_union_repository, get_sheets_repository
from backend.models.union import Union
from backend.exceptions import SheetsConnectionError
from datetime import datetime


# ============================================================================
# FIXTURES
# ============================================================================


@pytest.fixture
def mock_union_repo():
    """Mock UnionRepository for testing."""
    return Mock()


@pytest.fixture
def mock_sheets_repo():
    """Mock SheetsRepository for testing."""
    return Mock()


@pytest.fixture
def client(mock_union_repo, mock_sheets_repo):
    """FastAPI TestClient with mocked dependencies."""
    app.dependency_overrides[get_union_repository] = lambda: mock_union_repo
    app.dependency_overrides[get_sheets_repository] = lambda: mock_sheets_repo

    client = TestClient(app)
    yield client

    # Cleanup
    app.dependency_overrides.clear()


@pytest.fixture
def sample_unions():
    """Sample union data for testing."""
    return [
        Union(
            id="TEST-01+1",
            ot="001",
            tag_spool="TEST-01",
            n_union=1,
            dn_union=6.0,
            tipo_union="BW",
            arm_fecha_inicio=None,
            arm_fecha_fin=None,
            arm_worker=None,
            sol_fecha_inicio=None,
            sol_fecha_fin=None,
            sol_worker=None,
            ndt_fecha=None,
            ndt_status=None,
            version="uuid1",
            creado_por="MR(93)",
            fecha_creacion=datetime(2026, 1, 1),
            modificado_por=None,
            fecha_modificacion=None
        ),
        Union(
            id="TEST-01+2",
            ot="001",
            tag_spool="TEST-01",
            n_union=2,
            dn_union=4.5,
            tipo_union="FW",
            arm_fecha_inicio=None,
            arm_fecha_fin=None,
            arm_worker=None,
            sol_fecha_inicio=None,
            sol_fecha_fin=None,
            sol_worker=None,
            ndt_fecha=None,
            ndt_status=None,
            version="uuid2",
            creado_por="MR(93)",
            fecha_creacion=datetime(2026, 1, 1),
            modificado_por=None,
            fecha_modificacion=None
        ),
        Union(
            id="TEST-01+3",
            ot="001",
            tag_spool="TEST-01",
            n_union=3,
            dn_union=8.0,
            tipo_union="SO",
            arm_fecha_inicio=datetime(2026, 1, 1),
            arm_fecha_fin=datetime(2026, 1, 1, 12, 0),
            arm_worker="MR(93)",
            sol_fecha_inicio=None,
            sol_fecha_fin=None,
            sol_worker=None,
            ndt_fecha=None,
            ndt_status=None,
            version="uuid3",
            creado_por="MR(93)",
            fecha_creacion=datetime(2026, 1, 1),
            modificado_por=None,
            fecha_modificacion=None
        )
    ]


# ============================================================================
# TESTS: GET /api/v4/uniones/{tag}/disponibles
# ============================================================================


def test_disponibles_arm_returns_incomplete(client, mock_union_repo, mock_sheets_repo, sample_unions):
    """ARM disponibles returns unions where ARM_FECHA_FIN is NULL."""
    # Setup
    mock_sheets_repo.get_spool_by_tag.return_value = {"OT": "001", "TAG_SPOOL": "TEST-01"}

    # Return only unions where arm_fecha_fin is None (first 2)
    mock_union_repo.get_disponibles_arm_by_ot.return_value = sample_unions[:2]

    # Execute
    response = client.get("/api/v4/uniones/TEST-01/disponibles?operacion=ARM")

    # Verify
    assert response.status_code == 200
    data = response.json()

    assert data["tag_spool"] == "TEST-01"
    assert data["operacion"] == "ARM"
    assert data["count"] == 2
    assert len(data["unions"]) == 2

    # Verify first union structure
    union1 = data["unions"][0]
    assert union1["id"] == "TEST-01+1"
    assert union1["n_union"] == 1
    assert union1["dn_union"] == 6.0
    assert union1["tipo_union"] == "BW"

    # Verify repository was called correctly
    mock_sheets_repo.get_spool_by_tag.assert_called_once_with("TEST-01")
    mock_union_repo.get_disponibles_arm_by_ot.assert_called_once_with("001")


def test_disponibles_sold_requires_arm_complete(client, mock_union_repo, mock_sheets_repo, sample_unions):
    """SOLD disponibles returns only unions where ARM_FECHA_FIN is NOT NULL and SOL_FECHA_FIN is NULL."""
    # Setup
    mock_sheets_repo.get_spool_by_tag.return_value = {"OT": "001", "TAG_SPOOL": "TEST-01"}

    # Return only union where arm_fecha_fin is set but sol_fecha_fin is None (third union)
    mock_union_repo.get_disponibles_sold_by_ot.return_value = [sample_unions[2]]

    # Execute
    response = client.get("/api/v4/uniones/TEST-01/disponibles?operacion=SOLD")

    # Verify
    assert response.status_code == 200
    data = response.json()

    assert data["tag_spool"] == "TEST-01"
    assert data["operacion"] == "SOLD"
    assert data["count"] == 1
    assert len(data["unions"]) == 1

    # Verify union structure
    union = data["unions"][0]
    assert union["id"] == "TEST-01+3"
    assert union["n_union"] == 3
    assert union["dn_union"] == 8.0
    assert union["tipo_union"] == "SO"

    # Verify repository was called correctly
    mock_sheets_repo.get_spool_by_tag.assert_called_once_with("TEST-01")
    mock_union_repo.get_disponibles_sold_by_ot.assert_called_once_with("001")


def test_disponibles_empty_list_when_none_available(client, mock_union_repo, mock_sheets_repo):
    """Returns empty list when no unions are available."""
    # Setup
    mock_sheets_repo.get_spool_by_tag.return_value = {"OT": "001", "TAG_SPOOL": "TEST-01"}
    mock_union_repo.get_disponibles_arm_by_ot.return_value = []

    # Execute
    response = client.get("/api/v4/uniones/TEST-01/disponibles?operacion=ARM")

    # Verify
    assert response.status_code == 200
    data = response.json()

    assert data["count"] == 0
    assert data["unions"] == []


def test_disponibles_404_spool_not_found(client, mock_sheets_repo):
    """Returns 404 when spool doesn't exist."""
    # Setup
    mock_sheets_repo.get_spool_by_tag.return_value = None

    # Execute
    response = client.get("/api/v4/uniones/NONEXISTENT/disponibles?operacion=ARM")

    # Verify
    assert response.status_code == 404
    data = response.json()
    assert "not found" in data["detail"].lower()


def test_disponibles_400_invalid_operacion(client, mock_sheets_repo):
    """Returns 422 (validation error) for invalid operacion parameter."""
    # Setup
    mock_sheets_repo.get_spool_by_tag.return_value = {"OT": "001", "TAG_SPOOL": "TEST-01"}

    # Execute
    response = client.get("/api/v4/uniones/TEST-01/disponibles?operacion=INVALID")

    # Verify - FastAPI validation returns 422 for pattern mismatch
    assert response.status_code == 422


def test_disponibles_500_sheets_connection_error(client, mock_union_repo, mock_sheets_repo):
    """Returns 500 when Google Sheets connection fails."""
    # Setup
    mock_sheets_repo.get_spool_by_tag.return_value = {"OT": "001", "TAG_SPOOL": "TEST-01"}
    mock_union_repo.get_disponibles_arm_by_ot.side_effect = SheetsConnectionError("Connection failed")

    # Execute
    response = client.get("/api/v4/uniones/TEST-01/disponibles?operacion=ARM")

    # Verify
    assert response.status_code == 500
    data = response.json()
    assert "Failed to read union data" in data["detail"]


# ============================================================================
# TESTS: GET /api/v4/uniones/{tag}/metricas
# ============================================================================


def test_metricas_returns_five_fields(client, mock_union_repo, mock_sheets_repo):
    """GET /metricas returns exactly 5 required fields."""
    # Setup
    mock_sheets_repo.get_spool_by_tag.return_value = {"OT": "001", "TAG_SPOOL": "TEST-01"}
    mock_union_repo.calculate_metrics.return_value = {
        "total_uniones": 10,
        "arm_completadas": 7,
        "sold_completadas": 5,
        "pulgadas_arm": 18.50,
        "pulgadas_sold": 12.75
    }

    # Execute
    response = client.get("/api/v4/uniones/TEST-01/metricas")

    # Verify
    assert response.status_code == 200
    data = response.json()

    # Verify all 5 fields present
    assert data["tag_spool"] == "TEST-01"
    assert data["total_uniones"] == 10
    assert data["arm_completadas"] == 7
    assert data["sold_completadas"] == 5
    assert data["pulgadas_arm"] == 18.50
    assert data["pulgadas_sold"] == 12.75

    # Verify no extra fields
    assert len(data) == 6  # 5 metrics + tag_spool


def test_metricas_2_decimal_precision(client, mock_union_repo, mock_sheets_repo):
    """Pulgadas values have exactly 2 decimal places."""
    # Setup
    mock_sheets_repo.get_spool_by_tag.return_value = {"OT": "001", "TAG_SPOOL": "TEST-01"}
    mock_union_repo.calculate_metrics.return_value = {
        "total_uniones": 5,
        "arm_completadas": 3,
        "sold_completadas": 2,
        "pulgadas_arm": 18.50,  # Not 18.5
        "pulgadas_sold": 12.00   # Not 12
    }

    # Execute
    response = client.get("/api/v4/uniones/TEST-01/metricas")

    # Verify
    assert response.status_code == 200
    data = response.json()

    # Verify 2 decimal precision maintained
    assert data["pulgadas_arm"] == 18.50
    assert data["pulgadas_sold"] == 12.00


def test_metricas_404_spool_not_found(client, mock_sheets_repo):
    """Returns 404 when spool doesn't exist."""
    # Setup
    mock_sheets_repo.get_spool_by_tag.return_value = None

    # Execute
    response = client.get("/api/v4/uniones/NONEXISTENT/metricas")

    # Verify
    assert response.status_code == 404
    data = response.json()
    assert "not found" in data["detail"].lower()


def test_metricas_404_no_unions(client, mock_union_repo, mock_sheets_repo):
    """Returns 404 when spool has no unions."""
    # Setup
    mock_sheets_repo.get_spool_by_tag.return_value = {"OT": "001", "TAG_SPOOL": "TEST-01"}
    mock_union_repo.calculate_metrics.return_value = {
        "total_uniones": 0,
        "arm_completadas": 0,
        "sold_completadas": 0,
        "pulgadas_arm": 0.00,
        "pulgadas_sold": 0.00
    }

    # Execute
    response = client.get("/api/v4/uniones/TEST-01/metricas")

    # Verify
    assert response.status_code == 404
    data = response.json()
    assert "No unions found" in data["detail"]


def test_metricas_500_sheets_connection_error(client, mock_union_repo, mock_sheets_repo):
    """Returns 500 when Google Sheets connection fails."""
    # Setup
    mock_sheets_repo.get_spool_by_tag.return_value = {"OT": "001", "TAG_SPOOL": "TEST-01"}
    mock_union_repo.calculate_metrics.side_effect = SheetsConnectionError("Connection failed")

    # Execute
    response = client.get("/api/v4/uniones/TEST-01/metricas")

    # Verify
    assert response.status_code == 500
    data = response.json()
    assert "Failed to read union data" in data["detail"]


def test_metricas_zero_pulgadas_when_no_completions(client, mock_union_repo, mock_sheets_repo):
    """Returns 0.00 pulgadas when no unions are completed."""
    # Setup
    mock_sheets_repo.get_spool_by_tag.return_value = {"OT": "001", "TAG_SPOOL": "TEST-01"}
    mock_union_repo.calculate_metrics.return_value = {
        "total_uniones": 10,
        "arm_completadas": 0,
        "sold_completadas": 0,
        "pulgadas_arm": 0.00,
        "pulgadas_sold": 0.00
    }

    # Execute
    response = client.get("/api/v4/uniones/TEST-01/metricas")

    # Verify
    assert response.status_code == 200
    data = response.json()

    assert data["pulgadas_arm"] == 0.00
    assert data["pulgadas_sold"] == 0.00


# ============================================================================
# TESTS: POST /api/v4/occupation/finalizar
# ============================================================================


def test_finalizar_pausar_partial(client, mock_union_repo, mock_sheets_repo):
    """Partial selection results in PAUSAR."""
    # Setup - mock dependencies
    from backend.models.spool import Spool
    from backend.models.worker import Worker
    from backend.models.occupation import OccupationResponse
    from backend.core.dependency import get_occupation_service, get_worker_service

    # Mock spool (v4.0)
    mock_spool = Mock(spec=Spool)
    mock_spool.tag_spool = "TEST-02"
    mock_spool.total_uniones = 10
    mock_spool.ot = "001"
    mock_spool.model_dump.return_value = {"TAG_SPOOL": "TEST-02", "Total_Uniones": "10", "OT": "001"}
    mock_sheets_repo.get_spool_by_tag.return_value = mock_spool

    # Mock worker
    mock_worker = Mock(spec=Worker)
    mock_worker.apellido = "Rodriguez"
    mock_worker_service = Mock()
    mock_worker_service.get_worker_by_id.return_value = mock_worker

    # Mock occupation service (PAUSAR result)
    mock_occupation_service = Mock()
    mock_occupation_response = OccupationResponse(
        success=True,
        tag_spool="TEST-02",
        message="Trabajo pausado - 3 uniones procesadas",
        action_taken="PAUSAR",
        unions_processed=3,
        metrologia_triggered=False
    )
    mock_occupation_service.finalizar_spool = Mock(return_value=mock_occupation_response)

    # Mock metrics calculation (pulgadas)
    mock_union_repo.calculate_metrics.return_value = {
        "total_uniones": 10,
        "arm_completadas": 3,
        "sold_completadas": 0,
        "pulgadas_arm": 16.50,
        "pulgadas_sold": 0.00
    }

    # Override dependencies
    app.dependency_overrides[get_occupation_service] = lambda: mock_occupation_service
    app.dependency_overrides[get_worker_service] = lambda: mock_worker_service

    # Execute
    response = client.post("/api/v4/occupation/finalizar", json={
        "tag_spool": "TEST-02",
        "worker_id": 93,
        "operacion": "ARM",
        "selected_unions": ["TEST-02+1", "TEST-02+2", "TEST-02+3"]
    })

    # Verify
    assert response.status_code == 200
    data = response.json()
    assert data["action_taken"] == "PAUSAR"
    assert data["unions_processed"] == 3
    assert data["pulgadas"] == 16.50
    assert data["metrologia_triggered"] is False

    # Cleanup
    app.dependency_overrides.clear()


def test_finalizar_completar_full(client, mock_union_repo, mock_sheets_repo):
    """Full selection results in COMPLETAR."""
    # Setup - mock dependencies
    from backend.models.spool import Spool
    from backend.models.worker import Worker
    from backend.models.occupation import OccupationResponse
    from backend.core.dependency import get_occupation_service, get_worker_service

    # Mock spool (v4.0)
    mock_spool = Mock(spec=Spool)
    mock_spool.tag_spool = "TEST-02"
    mock_spool.total_uniones = 10
    mock_spool.ot = "001"
    mock_spool.model_dump.return_value = {"TAG_SPOOL": "TEST-02", "Total_Uniones": "10", "OT": "001"}
    mock_sheets_repo.get_spool_by_tag.return_value = mock_spool

    # Mock worker
    mock_worker = Mock(spec=Worker)
    mock_worker.apellido = "Rodriguez"
    mock_worker_service = Mock()
    mock_worker_service.get_worker_by_id.return_value = mock_worker

    # Mock occupation service (COMPLETAR result)
    mock_occupation_service = Mock()
    mock_occupation_response = OccupationResponse(
        success=True,
        tag_spool="TEST-02",
        message="Operación completada - 10 uniones procesadas",
        action_taken="COMPLETAR",
        unions_processed=10,
        metrologia_triggered=False
    )
    mock_occupation_service.finalizar_spool = Mock(return_value=mock_occupation_response)

    # Mock metrics calculation (pulgadas)
    mock_union_repo.calculate_metrics.return_value = {
        "total_uniones": 10,
        "arm_completadas": 10,
        "sold_completadas": 0,
        "pulgadas_arm": 48.75,
        "pulgadas_sold": 0.00
    }

    # Override dependencies
    app.dependency_overrides[get_occupation_service] = lambda: mock_occupation_service
    app.dependency_overrides[get_worker_service] = lambda: mock_worker_service

    # Execute
    response = client.post("/api/v4/occupation/finalizar", json={
        "tag_spool": "TEST-02",
        "worker_id": 93,
        "operacion": "ARM",
        "selected_unions": [f"TEST-02+{i}" for i in range(1, 11)]
    })

    # Verify
    assert response.status_code == 200
    data = response.json()
    assert data["action_taken"] == "COMPLETAR"
    assert data["unions_processed"] == 10
    assert data["pulgadas"] == 48.75

    # Cleanup
    app.dependency_overrides.clear()


def test_finalizar_cancelado_zero(client, mock_union_repo, mock_sheets_repo):
    """Zero unions results in CANCELADO."""
    # Setup - mock dependencies
    from backend.models.spool import Spool
    from backend.models.worker import Worker
    from backend.models.occupation import OccupationResponse
    from backend.core.dependency import get_occupation_service, get_worker_service

    # Mock spool (v4.0)
    mock_spool = Mock(spec=Spool)
    mock_spool.tag_spool = "TEST-02"
    mock_spool.total_uniones = 10
    mock_spool.ot = "001"
    mock_spool.model_dump.return_value = {"TAG_SPOOL": "TEST-02", "Total_Uniones": "10", "OT": "001"}
    mock_sheets_repo.get_spool_by_tag.return_value = mock_spool

    # Mock worker
    mock_worker = Mock(spec=Worker)
    mock_worker.apellido = "Rodriguez"
    mock_worker_service = Mock()
    mock_worker_service.get_worker_by_id.return_value = mock_worker

    # Mock occupation service (CANCELADO result)
    mock_occupation_service = Mock()
    mock_occupation_response = OccupationResponse(
        success=True,
        tag_spool="TEST-02",
        message="Trabajo cancelado en TEST-02",
        action_taken="CANCELADO",
        unions_processed=0
    )
    mock_occupation_service.finalizar_spool = Mock(return_value=mock_occupation_response)

    # Override dependencies
    app.dependency_overrides[get_occupation_service] = lambda: mock_occupation_service
    app.dependency_overrides[get_worker_service] = lambda: mock_worker_service

    # Execute
    response = client.post("/api/v4/occupation/finalizar", json={
        "tag_spool": "TEST-02",
        "worker_id": 93,
        "operacion": "ARM",
        "selected_unions": []
    })

    # Verify
    assert response.status_code == 200
    data = response.json()
    assert data["action_taken"] == "CANCELADO"
    assert data["unions_processed"] == 0
    assert data["pulgadas"] is None

    # Cleanup
    app.dependency_overrides.clear()


def test_finalizar_race_condition(client, mock_sheets_repo):
    """Selected > disponibles returns 409."""
    # Setup - mock dependencies
    from backend.models.spool import Spool
    from backend.models.worker import Worker
    from backend.core.dependency import get_occupation_service, get_worker_service

    # Mock spool (v4.0)
    mock_spool = Mock(spec=Spool)
    mock_spool.tag_spool = "TEST-02"
    mock_spool.total_uniones = 10
    mock_spool.ot = "001"
    mock_spool.model_dump.return_value = {"TAG_SPOOL": "TEST-02", "Total_Uniones": "10", "OT": "001"}
    mock_sheets_repo.get_spool_by_tag.return_value = mock_spool

    # Mock worker
    mock_worker = Mock(spec=Worker)
    mock_worker.apellido = "Rodriguez"
    mock_worker_service = Mock()
    mock_worker_service.get_worker_by_id.return_value = mock_worker

    # Mock occupation service (race condition - ValueError)
    mock_occupation_service = Mock()
    mock_occupation_service.finalizar_spool.side_effect = ValueError(
        "Selected 5 unions but only 3 available - more unions than available"
    )

    # Override dependencies
    app.dependency_overrides[get_occupation_service] = lambda: mock_occupation_service
    app.dependency_overrides[get_worker_service] = lambda: mock_worker_service

    # Execute
    response = client.post("/api/v4/occupation/finalizar", json={
        "tag_spool": "TEST-02",
        "worker_id": 93,
        "operacion": "ARM",
        "selected_unions": ["TEST-02+1", "TEST-02+2", "TEST-02+3", "TEST-02+4", "TEST-02+5"]
    })

    # Verify
    assert response.status_code == 409
    detail = response.json()["detail"]
    assert detail["error"] == "RACE_CONDITION"
    assert "no longer available" in detail["message"]

    # Cleanup
    app.dependency_overrides.clear()


def test_finalizar_not_owner(client, mock_sheets_repo):
    """Worker doesn't own spool returns 403."""
    # Setup - mock dependencies
    from backend.models.spool import Spool
    from backend.models.worker import Worker
    from backend.exceptions import NoAutorizadoError
    from backend.core.dependency import get_occupation_service, get_worker_service

    # Mock spool (v4.0)
    mock_spool = Mock(spec=Spool)
    mock_spool.tag_spool = "TEST-02"
    mock_spool.total_uniones = 10
    mock_spool.ot = "001"
    mock_spool.model_dump.return_value = {"TAG_SPOOL": "TEST-02", "Total_Uniones": "10", "OT": "001"}
    mock_sheets_repo.get_spool_by_tag.return_value = mock_spool

    # Mock worker
    mock_worker = Mock(spec=Worker)
    mock_worker.apellido = "Rodriguez"
    mock_worker_service = Mock()
    mock_worker_service.get_worker_by_id.return_value = mock_worker

    # Mock occupation service (not owner - NoAutorizadoError)
    mock_occupation_service = Mock()
    mock_occupation_service.finalizar_spool.side_effect = NoAutorizadoError(
        tag_spool="TEST-02",
        trabajador_esperado="Worker 94",
        trabajador_solicitante="Rodriguez(93)",
        operacion="FINALIZAR"
    )

    # Override dependencies
    app.dependency_overrides[get_occupation_service] = lambda: mock_occupation_service
    app.dependency_overrides[get_worker_service] = lambda: mock_worker_service

    # Execute
    response = client.post("/api/v4/occupation/finalizar", json={
        "tag_spool": "TEST-02",
        "worker_id": 93,
        "operacion": "ARM",
        "selected_unions": ["TEST-02+1"]
    })

    # Verify
    assert response.status_code == 403
    detail = response.json()["detail"]
    assert detail["error"] == "NO_AUTORIZADO"

    # Cleanup
    app.dependency_overrides.clear()


def test_finalizar_metrologia_triggered(client, mock_union_repo, mock_sheets_repo):
    """COMPLETAR with 100% SOLD triggers metrología."""
    # Setup - mock dependencies
    from backend.models.spool import Spool
    from backend.models.worker import Worker
    from backend.models.occupation import OccupationResponse
    from backend.core.dependency import get_occupation_service, get_worker_service

    # Mock spool (v4.0)
    mock_spool = Mock(spec=Spool)
    mock_spool.tag_spool = "TEST-02"
    mock_spool.total_uniones = 10
    mock_spool.ot = "001"
    mock_spool.model_dump.return_value = {"TAG_SPOOL": "TEST-02", "Total_Uniones": "10", "OT": "001"}
    mock_sheets_repo.get_spool_by_tag.return_value = mock_spool

    # Mock worker
    mock_worker = Mock(spec=Worker)
    mock_worker.apellido = "Rodriguez"
    mock_worker_service = Mock()
    mock_worker_service.get_worker_by_id.return_value = mock_worker

    # Mock occupation service (COMPLETAR with metrología trigger)
    mock_occupation_service = Mock()
    mock_occupation_response = OccupationResponse(
        success=True,
        tag_spool="TEST-02",
        message="Operación completada - 10 uniones procesadas",
        action_taken="COMPLETAR",
        unions_processed=10,
        metrologia_triggered=True,
        new_state="pendiente"
    )
    mock_occupation_service.finalizar_spool = Mock(return_value=mock_occupation_response)

    # Mock metrics calculation (pulgadas)
    mock_union_repo.calculate_metrics.return_value = {
        "total_uniones": 10,
        "arm_completadas": 10,
        "sold_completadas": 10,
        "pulgadas_arm": 48.75,
        "pulgadas_sold": 48.75
    }

    # Override dependencies
    app.dependency_overrides[get_occupation_service] = lambda: mock_occupation_service
    app.dependency_overrides[get_worker_service] = lambda: mock_worker_service

    # Execute
    response = client.post("/api/v4/occupation/finalizar", json={
        "tag_spool": "TEST-02",
        "worker_id": 93,
        "operacion": "SOLD",
        "selected_unions": [f"TEST-02+{i}" for i in range(1, 11)]
    })

    # Verify
    assert response.status_code == 200
    data = response.json()
    assert data["action_taken"] == "COMPLETAR"
    assert data["unions_processed"] == 10
    assert data["metrologia_triggered"] is True
    assert data["new_state"] == "pendiente"
    assert "(Listo para metrología)" in data["message"]

    # Cleanup
    app.dependency_overrides.clear()


def test_finalizar_v3_spool_rejected(client, mock_sheets_repo):
    """v3.0 spool returns 400 with helpful error."""
    # Setup - mock v3.0 spool
    from backend.models.spool import Spool

    mock_spool = Mock(spec=Spool)
    mock_spool.tag_spool = "TEST-01"
    mock_spool.total_uniones = 0
    mock_spool.model_dump.return_value = {"TAG_SPOOL": "TEST-01", "Total_Uniones": "0"}
    mock_sheets_repo.get_spool_by_tag.return_value = mock_spool

    # Execute
    response = client.post("/api/v4/occupation/finalizar", json={
        "tag_spool": "TEST-01",
        "worker_id": 93,
        "operacion": "ARM",
        "selected_unions": ["TEST-01+1"]
    })

    # Verify
    assert response.status_code == 400
    detail = response.json()["detail"]
    assert detail["error"] == "WRONG_VERSION"
    assert detail["spool_version"] == "v3.0"
    assert detail["correct_endpoint"] == "/api/v3/occupation/completar"
