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




# ============================================================================
# TESTS: GET /api/v4/uniones/{tag}/metricas
# ============================================================================






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








# ============================================================================
# TESTS: POST /api/v4/occupation/finalizar
# ============================================================================














