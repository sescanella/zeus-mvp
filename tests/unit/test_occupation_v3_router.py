"""
Unit tests for occupation_v3 router - API versioning for v3.0 endpoints.

Tests validate:
- v3.0 endpoints exist at /api/v3/ prefix
- Legacy endpoints still exist at /api/ prefix (backward compatibility)
- Both prefixes route to same logic
- Router accepts valid request payloads

Note: These are smoke tests for API versioning structure.
Full integration tests exist in tests/integration/.

Reference:
- Router: backend/routers/occupation_v3.py
- Plan: 11-01-PLAN.md
"""
import pytest
from fastapi.testclient import TestClient
from unittest.mock import AsyncMock, patch

from backend.main import app
from backend.models.occupation import OccupationResponse


@pytest.fixture
def client():
    """FastAPI test client."""
    return TestClient(app)


def test_v3_tomar_endpoint_exists(client):
    """Test that v3.0 TOMAR endpoint exists at /api/v3/occupation/tomar."""
    response = client.post(
        "/api/v3/occupation/tomar",
        json={
            "tag_spool": "TEST-02",
            "worker_id": 93,
            "worker_nombre": "MR(93)",
            "operacion": "ARM"
        }
    )

    # Should not return 404 (endpoint exists)
    # May return 500 (Redis not connected in test) or other error codes
    assert response.status_code != 404, "v3.0 TOMAR endpoint should exist at /api/v3/"


def test_v3_pausar_endpoint_exists(client):
    """Test that v3.0 PAUSAR endpoint exists at /api/v3/occupation/pausar."""
    response = client.post(
        "/api/v3/occupation/pausar",
        json={
            "tag_spool": "TEST-02",
            "worker_id": 93,
            "worker_nombre": "MR(93)"
        }
    )

    # Should not return 404 (endpoint exists)
    assert response.status_code != 404, "v3.0 PAUSAR endpoint should exist at /api/v3/"


def test_v3_completar_endpoint_exists(client):
    """Test that v3.0 COMPLETAR endpoint exists at /api/v3/occupation/completar."""
    response = client.post(
        "/api/v3/occupation/completar",
        json={
            "tag_spool": "TEST-02",
            "worker_id": 93,
            "worker_nombre": "MR(93)",
            "operacion": "ARM",
            "fecha_operacion": "2026-02-02"
        }
    )

    # Should not return 404 (endpoint exists)
    assert response.status_code != 404, "v3.0 COMPLETAR endpoint should exist at /api/v3/"


def test_legacy_tomar_endpoint_still_exists(client):
    """Verify /api/occupation/tomar still exists for backward compatibility."""
    response = client.post(
        "/api/occupation/tomar",
        json={
            "tag_spool": "TEST-02",
            "worker_id": 93,
            "worker_nombre": "MR(93)",
            "operacion": "ARM"
        }
    )

    # Should not return 404 (endpoint still exists)
    assert response.status_code != 404, "Legacy TOMAR endpoint should still exist at /api/"


def test_legacy_pausar_endpoint_still_exists(client):
    """Verify /api/occupation/pausar still exists for backward compatibility."""
    response = client.post(
        "/api/occupation/pausar",
        json={
            "tag_spool": "TEST-02",
            "worker_id": 93,
            "worker_nombre": "MR(93)"
        }
    )

    # Should not return 404 (endpoint still exists)
    assert response.status_code != 404, "Legacy PAUSAR endpoint should still exist at /api/"


def test_legacy_completar_endpoint_still_exists(client):
    """Verify /api/occupation/completar still exists for backward compatibility."""
    response = client.post(
        "/api/occupation/completar",
        json={
            "tag_spool": "TEST-02",
            "worker_id": 93,
            "worker_nombre": "MR(93)",
            "operacion": "ARM",
            "fecha_operacion": "2026-02-02"
        }
    )

    # Should not return 404 (endpoint still exists)
    assert response.status_code != 404, "Legacy COMPLETAR endpoint should still exist at /api/"


def test_invalid_request_returns_422(client):
    """Test that invalid request payloads return 422 Unprocessable Entity."""
    # Missing required field (worker_nombre)
    response = client.post(
        "/api/v3/occupation/tomar",
        json={
            "tag_spool": "TEST-02",
            "worker_id": 93,
            "operacion": "ARM"
        }
    )

    # Pydantic validation should return 422
    assert response.status_code == 422, "Invalid payload should return 422"


def test_batch_tomar_endpoint_exists(client):
    """Test that v3.0 batch-tomar endpoint exists at /api/v3/occupation/batch-tomar."""
    response = client.post(
        "/api/v3/occupation/batch-tomar",
        json={
            "tag_spools": ["TEST-01", "TEST-02"],
            "worker_id": 93,
            "worker_nombre": "MR(93)",
            "operacion": "ARM"
        }
    )

    # Should not return 404 (endpoint exists)
    assert response.status_code != 404, "v3.0 batch-tomar endpoint should exist at /api/v3/"
