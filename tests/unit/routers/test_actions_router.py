"""
Unit tests for actions router — Reparacion endpoints.

Tests validate:
- Endpoints exist at expected paths
- Pydantic validation catches missing/invalid fields (422)
- worker_id validation against Trabajadores sheet (D-1 fix)

Reference:
- Router: backend/routers/actions.py
- Scope: v5.1 Track A, D-1 (worker_id validation in ReparacionService)
"""
from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient

from backend.core.dependency import get_reparacion_service, get_worker_service
from backend.main import app


@pytest.fixture
def client():
    """FastAPI test client."""
    return TestClient(app)


# ==================== ENDPOINT EXISTENCE ====================


def test_tomar_reparacion_endpoint_exists(client):
    """POST /api/tomar-reparacion is registered."""
    response = client.post("/api/tomar-reparacion", json={})
    assert response.status_code != 404


def test_completar_reparacion_endpoint_exists(client):
    """POST /api/completar-reparacion is registered."""
    response = client.post("/api/completar-reparacion", json={})
    assert response.status_code != 404


def test_pausar_reparacion_endpoint_exists(client):
    """POST /api/pausar-reparacion is registered."""
    response = client.post("/api/pausar-reparacion", json={})
    assert response.status_code != 404


def test_cancelar_reparacion_endpoint_exists(client):
    """POST /api/cancelar-reparacion is registered."""
    response = client.post("/api/cancelar-reparacion", json={})
    assert response.status_code != 404


# ==================== PYDANTIC VALIDATION (422) ====================


def test_tomar_requires_worker_id(client):
    response = client.post(
        "/api/tomar-reparacion",
        json={"tag_spool": "MK-1923-TW-17422-004"},
    )
    assert response.status_code == 422


def test_tomar_requires_tag_spool(client):
    response = client.post(
        "/api/tomar-reparacion",
        json={"worker_id": 93},
    )
    assert response.status_code == 422


def test_tomar_rejects_zero_worker_id(client):
    """ReparacionRequest enforces worker_id > 0."""
    response = client.post(
        "/api/tomar-reparacion",
        json={"worker_id": 0, "tag_spool": "MK-1923-TW-17422-004"},
    )
    assert response.status_code == 422


# ==================== D-1: WORKER EXISTENCE VALIDATION ====================


def test_tomar_returns_404_when_worker_not_found(client):
    """
    D-1 fix: if worker_id is numerically valid (>0) but does not exist
    in Trabajadores sheet, the router must reject with 404 instead of
    stamping a placeholder `W({id})` as occupant.
    """
    mock_worker_service = MagicMock()
    mock_worker_service.find_worker_by_id.return_value = None  # simulate: not found

    mock_reparacion_service = MagicMock()

    app.dependency_overrides[get_worker_service] = lambda: mock_worker_service
    app.dependency_overrides[get_reparacion_service] = lambda: mock_reparacion_service
    try:
        response = client.post(
            "/api/tomar-reparacion",
            json={"worker_id": 99999, "tag_spool": "MK-1923-TW-17422-004"},
        )

        assert response.status_code == 404
        mock_worker_service.find_worker_by_id.assert_called_once_with(99999)
        # Critical: service must NEVER be called when worker doesn't exist
        mock_reparacion_service.tomar_reparacion.assert_not_called()
    finally:
        app.dependency_overrides.clear()


def test_completar_returns_404_when_worker_not_found(client):
    """D-1 fix: completar-reparacion rejects unknown worker_id with 404."""
    mock_worker_service = MagicMock()
    mock_worker_service.find_worker_by_id.return_value = None

    mock_reparacion_service = MagicMock()

    app.dependency_overrides[get_worker_service] = lambda: mock_worker_service
    app.dependency_overrides[get_reparacion_service] = lambda: mock_reparacion_service
    try:
        response = client.post(
            "/api/completar-reparacion",
            json={"worker_id": 99999, "tag_spool": "MK-1923-TW-17422-004"},
        )

        assert response.status_code == 404
        mock_reparacion_service.completar_reparacion.assert_not_called()
    finally:
        app.dependency_overrides.clear()


def test_tomar_uses_worker_nombre_completo_when_worker_exists(client):
    """
    D-1 fix: when worker exists, router passes `worker.nombre_completo`
    (e.g., "MR(93)") to the service, not the `W({id})` placeholder.
    """
    fake_worker = MagicMock()
    fake_worker.nombre_completo = "MR(93)"

    mock_worker_service = MagicMock()
    mock_worker_service.find_worker_by_id.return_value = fake_worker

    async def fake_tomar(tag_spool, worker_id, worker_nombre):
        return {
            "success": True,
            "tag_spool": tag_spool,
            "worker_nombre": worker_nombre,
            "estado_detalle": f"EN_REPARACION - Ocupado: {worker_nombre}",
            "cycle": 1,
            "message": "ok",
        }

    mock_reparacion_service = MagicMock()
    mock_reparacion_service.tomar_reparacion.side_effect = fake_tomar

    app.dependency_overrides[get_worker_service] = lambda: mock_worker_service
    app.dependency_overrides[get_reparacion_service] = lambda: mock_reparacion_service
    try:
        response = client.post(
            "/api/tomar-reparacion",
            json={"worker_id": 93, "tag_spool": "MK-1923-TW-17422-004"},
        )

        assert response.status_code == 200
        mock_reparacion_service.tomar_reparacion.assert_called_once()
        _, kwargs = mock_reparacion_service.tomar_reparacion.call_args
        assert kwargs["worker_nombre"] == "MR(93)"
        assert "W(" not in kwargs["worker_nombre"]  # no legacy placeholder
    finally:
        app.dependency_overrides.clear()


def test_completar_uses_worker_nombre_completo_when_worker_exists(client):
    """
    D-1 fix (symmetric with tomar): when worker exists, completar-reparacion
    router passes `worker.nombre_completo` to the service, not the legacy
    `W({id})` placeholder.
    """
    fake_worker = MagicMock()
    fake_worker.nombre_completo = "MR(93)"

    mock_worker_service = MagicMock()
    mock_worker_service.find_worker_by_id.return_value = fake_worker

    async def fake_completar(tag_spool, worker_id, worker_nombre):
        return {
            "success": True,
            "tag_spool": tag_spool,
            "worker_nombre": worker_nombre,
            "estado_detalle": "PENDIENTE_METROLOGIA",
            "cycle": 1,
            "message": "ok",
        }

    mock_reparacion_service = MagicMock()
    mock_reparacion_service.completar_reparacion.side_effect = fake_completar

    app.dependency_overrides[get_worker_service] = lambda: mock_worker_service
    app.dependency_overrides[get_reparacion_service] = lambda: mock_reparacion_service
    try:
        response = client.post(
            "/api/completar-reparacion",
            json={"worker_id": 93, "tag_spool": "MK-1923-TW-17422-004"},
        )

        assert response.status_code == 200
        mock_reparacion_service.completar_reparacion.assert_called_once()
        _, kwargs = mock_reparacion_service.completar_reparacion.call_args
        assert kwargs["worker_nombre"] == "MR(93)"
        assert "W(" not in kwargs["worker_nombre"]  # no legacy placeholder
    finally:
        app.dependency_overrides.clear()
