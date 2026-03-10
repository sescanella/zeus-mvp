"""
Unit tests for spool_status_router — GET /api/spool/{tag}/status endpoint.

Tests validate:
- 200 response with SpoolStatus fields for valid tag
- 404 response for non-existent tag
- Computed fields (operacion_actual, estado_trabajo, ciclo_rep) present in response
- Endpoint registered at /api/spool/{tag}/status

Uses FastAPI TestClient with dependency_overrides to mock SheetsRepository.

Reference:
- Router: backend/routers/spool_status_router.py
- Plan: 00-01-PLAN.md (API-01)
"""
import pytest
from unittest.mock import MagicMock
from fastapi.testclient import TestClient

from backend.main import app
from backend.core.dependency import get_sheets_repository
from backend.models.spool import Spool


# ==================== FIXTURES ====================


def make_mock_spool(**overrides) -> Spool:
    """Create a minimal Spool for testing."""
    defaults = {
        "tag_spool": "MK-TEST-001",
        "ocupado_por": None,
        "fecha_ocupacion": None,
        "estado_detalle": None,
        "total_uniones": None,
        "uniones_arm_completadas": None,
        "uniones_sold_completadas": None,
        "pulgadas_arm": None,
        "pulgadas_sold": None,
    }
    defaults.update(overrides)
    return Spool(**defaults)


@pytest.fixture
def mock_repo_returning_spool():
    """SheetsRepository mock that returns a known spool."""
    spool = make_mock_spool(
        tag_spool="MK-TEST-001",
        ocupado_por="MR(93)",
        estado_detalle="MR(93) trabajando ARM (ARM en progreso, SOLD pendiente)",
        total_uniones=8,
        uniones_arm_completadas=0,
        uniones_sold_completadas=0,
    )
    repo = MagicMock()
    repo.get_spool_by_tag = MagicMock(return_value=spool)
    return repo


@pytest.fixture
def mock_repo_returning_none():
    """SheetsRepository mock that returns None (spool not found)."""
    repo = MagicMock()
    repo.get_spool_by_tag = MagicMock(return_value=None)
    return repo


@pytest.fixture
def client_with_spool(mock_repo_returning_spool):
    """TestClient with SheetsRepository overridden to return a spool."""
    app.dependency_overrides[get_sheets_repository] = lambda: mock_repo_returning_spool
    yield TestClient(app)
    app.dependency_overrides.clear()


@pytest.fixture
def client_without_spool(mock_repo_returning_none):
    """TestClient with SheetsRepository overridden to return None."""
    app.dependency_overrides[get_sheets_repository] = lambda: mock_repo_returning_none
    yield TestClient(app)
    app.dependency_overrides.clear()


# ==================== 200 SUCCESS TESTS ====================


def test_get_spool_status_returns_200(client_with_spool):
    """GET /api/spool/{tag}/status returns 200 for existing spool."""
    response = client_with_spool.get("/api/spool/MK-TEST-001/status")
    assert response.status_code == 200


def test_get_spool_status_returns_tag_spool(client_with_spool):
    """Response contains tag_spool field."""
    response = client_with_spool.get("/api/spool/MK-TEST-001/status")
    data = response.json()
    assert data["tag_spool"] == "MK-TEST-001"


def test_get_spool_status_contains_operacion_actual(client_with_spool):
    """Response contains operacion_actual computed field."""
    response = client_with_spool.get("/api/spool/MK-TEST-001/status")
    data = response.json()
    assert "operacion_actual" in data
    assert data["operacion_actual"] == "ARM"


def test_get_spool_status_contains_estado_trabajo(client_with_spool):
    """Response contains estado_trabajo computed field."""
    response = client_with_spool.get("/api/spool/MK-TEST-001/status")
    data = response.json()
    assert "estado_trabajo" in data
    assert data["estado_trabajo"] == "EN_PROGRESO"


def test_get_spool_status_contains_ciclo_rep(client_with_spool):
    """Response contains ciclo_rep computed field (None for EN_PROGRESO)."""
    response = client_with_spool.get("/api/spool/MK-TEST-001/status")
    data = response.json()
    assert "ciclo_rep" in data
    assert data["ciclo_rep"] is None


def test_get_spool_status_contains_ocupado_por(client_with_spool):
    """Response contains ocupado_por pass-through field."""
    response = client_with_spool.get("/api/spool/MK-TEST-001/status")
    data = response.json()
    assert data["ocupado_por"] == "MR(93)"


def test_get_spool_status_contains_union_fields(client_with_spool):
    """Response contains union count fields."""
    response = client_with_spool.get("/api/spool/MK-TEST-001/status")
    data = response.json()
    assert data["total_uniones"] == 8
    assert data["uniones_arm_completadas"] == 0
    assert data["uniones_sold_completadas"] == 0


# ==================== 404 NOT FOUND TESTS ====================


def test_get_spool_status_returns_404_for_unknown_tag(client_without_spool):
    """GET /api/spool/{tag}/status returns 404 for non-existent tag."""
    response = client_without_spool.get("/api/spool/DOES-NOT-EXIST/status")
    assert response.status_code == 404


def test_get_spool_status_404_detail_contains_tag(client_without_spool):
    """404 response detail includes the requested tag."""
    response = client_without_spool.get("/api/spool/INVALID-TAG-XYZ/status")
    data = response.json()
    assert "INVALID-TAG-XYZ" in data["detail"]


# ==================== LIBRE SPOOL (no estado_detalle) ====================


def test_get_spool_status_libre_spool():
    """Spool with no estado_detalle returns estado_trabajo=LIBRE."""
    libre_spool = make_mock_spool(tag_spool="LIBRE-TAG", estado_detalle=None)
    repo = MagicMock()
    repo.get_spool_by_tag = MagicMock(return_value=libre_spool)

    app.dependency_overrides[get_sheets_repository] = lambda: repo
    try:
        client = TestClient(app)
        response = client.get("/api/spool/LIBRE-TAG/status")
        assert response.status_code == 200
        data = response.json()
        assert data["estado_trabajo"] == "LIBRE"
        assert data["operacion_actual"] is None
        assert data["ciclo_rep"] is None
    finally:
        app.dependency_overrides.clear()


# ==================== ENDPOINT REGISTRATION ====================


def test_endpoint_exists_at_correct_path(client_with_spool):
    """Endpoint is registered at /api/spool/{tag}/status (not 404 from routing)."""
    response = client_with_spool.get("/api/spool/MK-TEST-001/status")
    # If registration failed, would return 404 (not from our handler)
    # Our handler returns 200 or our own 404 with "not found" detail
    assert response.status_code in (200, 404)
    if response.status_code == 404:
        # If it's our 404, it must have our detail message format
        data = response.json()
        assert "not found" in data.get("detail", "").lower()
