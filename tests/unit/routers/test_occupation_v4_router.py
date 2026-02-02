"""
Unit tests for occupation_v4 router - v4.0 INICIAR/FINALIZAR workflows.

Tests validate:
- v4.0 INICIAR endpoint at /api/v4/occupation/iniciar
- Basic endpoint existence and request validation
- Error response structures

Note: These are smoke tests for endpoint existence and basic structure.
Full integration tests with mocked dependencies exist in tests/integration/.

Reference:
- Router: backend/routers/occupation_v4.py
- Plan: 11-03-PLAN.md
"""
import pytest
from fastapi.testclient import TestClient

from backend.main import app


@pytest.fixture
def client():
    """FastAPI test client."""
    return TestClient(app)


# ==================== INICIAR ENDPOINT TESTS ====================


def test_iniciar_v4_endpoint_exists(client):
    """Test that v4.0 INICIAR endpoint exists at /api/v4/occupation/iniciar."""
    response = client.post(
        "/api/v4/occupation/iniciar",
        json={
            "tag_spool": "OT-123",
            "worker_id": 93,
            "worker_nombre": "MR(93)",
            "operacion": "ARM"
        }
    )

    # Should not return 404 (endpoint exists)
    # May return 500 (dependencies not configured) or other error codes
    assert response.status_code != 404, "v4.0 INICIAR endpoint should exist at /api/v4/"


def test_iniciar_requires_tag_spool(client):
    """Missing tag_spool returns 422 validation error."""
    response = client.post(
        "/api/v4/occupation/iniciar",
        json={
            # Missing tag_spool
            "worker_id": 93,
            "worker_nombre": "MR(93)",
            "operacion": "ARM"
        }
    )

    assert response.status_code == 422  # Pydantic validation error


def test_iniciar_requires_worker_id(client):
    """Missing worker_id returns 422 validation error."""
    response = client.post(
        "/api/v4/occupation/iniciar",
        json={
            "tag_spool": "OT-123",
            # Missing worker_id
            "worker_nombre": "MR(93)",
            "operacion": "ARM"
        }
    )

    assert response.status_code == 422  # Pydantic validation error


def test_iniciar_requires_worker_nombre(client):
    """Missing worker_nombre returns 422 validation error."""
    response = client.post(
        "/api/v4/occupation/iniciar",
        json={
            "tag_spool": "OT-123",
            "worker_id": 93,
            # Missing worker_nombre
            "operacion": "ARM"
        }
    )

    assert response.status_code == 422  # Pydantic validation error


def test_iniciar_requires_operacion(client):
    """Missing operacion returns 422 validation error."""
    response = client.post(
        "/api/v4/occupation/iniciar",
        json={
            "tag_spool": "OT-123",
            "worker_id": 93,
            "worker_nombre": "MR(93)"
            # Missing operacion
        }
    )

    assert response.status_code == 422  # Pydantic validation error


def test_iniciar_invalid_operacion(client):
    """Invalid operacion type returns 422 validation error."""
    response = client.post(
        "/api/v4/occupation/iniciar",
        json={
            "tag_spool": "OT-123",
            "worker_id": 93,
            "worker_nombre": "MR(93)",
            "operacion": "INVALID"  # Not ARM or SOLD
        }
    )

    assert response.status_code == 422  # Pydantic validation error


def test_iniciar_arm_payload_structure(client):
    """Valid ARM payload structure is accepted (may fail on business logic)."""
    response = client.post(
        "/api/v4/occupation/iniciar",
        json={
            "tag_spool": "OT-123",
            "worker_id": 93,
            "worker_nombre": "MR(93)",
            "operacion": "ARM"
        }
    )

    # Should pass Pydantic validation (not 422)
    assert response.status_code != 422, "Valid payload should pass Pydantic validation"


def test_iniciar_sold_payload_structure(client):
    """Valid SOLD payload structure is accepted (may fail on business logic)."""
    response = client.post(
        "/api/v4/occupation/iniciar",
        json={
            "tag_spool": "OT-123",
            "worker_id": 93,
            "worker_nombre": "MR(93)",
            "operacion": "SOLD"
        }
    )

    # Should pass Pydantic validation (not 422)
    assert response.status_code != 422, "Valid payload should pass Pydantic validation"


def test_iniciar_worker_id_must_be_positive(client):
    """Worker ID must be positive integer."""
    response = client.post(
        "/api/v4/occupation/iniciar",
        json={
            "tag_spool": "OT-123",
            "worker_id": -1,  # Invalid: negative
            "worker_nombre": "MR(-1)",
            "operacion": "ARM"
        }
    )

    assert response.status_code == 422  # Pydantic validation error


def test_iniciar_tag_spool_cannot_be_empty(client):
    """TAG_SPOOL cannot be empty string."""
    response = client.post(
        "/api/v4/occupation/iniciar",
        json={
            "tag_spool": "",  # Invalid: empty string
            "worker_id": 93,
            "worker_nombre": "MR(93)",
            "operacion": "ARM"
        }
    )

    assert response.status_code == 422  # Pydantic validation error


def test_iniciar_worker_nombre_cannot_be_empty(client):
    """worker_nombre cannot be empty string."""
    response = client.post(
        "/api/v4/occupation/iniciar",
        json={
            "tag_spool": "OT-123",
            "worker_id": 93,
            "worker_nombre": "",  # Invalid: empty string
            "operacion": "ARM"
        }
    )

    assert response.status_code == 422  # Pydantic validation error
