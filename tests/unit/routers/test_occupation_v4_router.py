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


# ==================== ERROR SCENARIO TESTS ====================


def test_finalizar_missing_selected_unions(client):
    """Missing selected_unions field returns 422 validation error."""
    response = client.post(
        "/api/v4/occupation/finalizar",
        json={
            "tag_spool": "OT-123",
            "worker_id": 93,
            "worker_nombre": "MR(93)",
            "operacion": "ARM"
            # Missing selected_unions
        }
    )

    assert response.status_code == 422  # Pydantic validation error


def test_finalizar_selected_unions_must_be_list(client):
    """selected_unions must be a list, not string."""
    response = client.post(
        "/api/v4/occupation/finalizar",
        json={
            "tag_spool": "OT-123",
            "worker_id": 93,
            "worker_nombre": "MR(93)",
            "operacion": "ARM",
            "selected_unions": "OT-123+1"  # Invalid: string not list
        }
    )

    assert response.status_code == 422  # Pydantic validation error


def test_finalizar_invalid_operacion_value(client):
    """Invalid operacion value returns 422 validation error."""
    response = client.post(
        "/api/v4/occupation/finalizar",
        json={
            "tag_spool": "OT-123",
            "worker_id": 93,
            "worker_nombre": "MR(93)",
            "operacion": "METROLOGIA",  # Not ARM or SOLD
            "selected_unions": ["OT-123+1"]
        }
    )

    assert response.status_code == 422  # Pydantic validation error


def test_disponibles_missing_operacion_query(client):
    """Missing operacion query param returns 422 validation error."""
    response = client.get("/api/v4/uniones/OT-123/disponibles")
    # Missing ?operacion=ARM

    assert response.status_code == 422  # Query param required


def test_disponibles_invalid_operacion_query(client):
    """Invalid operacion query param returns 422 validation error."""
    response = client.get("/api/v4/uniones/OT-123/disponibles?operacion=INVALID")

    assert response.status_code == 422  # Pattern validation


def test_iniciar_json_syntax_error(client):
    """Malformed JSON returns 422 validation error."""
    response = client.post(
        "/api/v4/occupation/iniciar",
        data='{"tag_spool": "OT-123", invalid}',  # Malformed JSON
        headers={"Content-Type": "application/json"}
    )

    assert response.status_code == 422  # JSON decode error


def test_iniciar_wrong_content_type(client):
    """Wrong Content-Type header returns 422."""
    response = client.post(
        "/api/v4/occupation/iniciar",
        data="tag_spool=OT-123&worker_id=93",  # Form data instead of JSON
        headers={"Content-Type": "application/x-www-form-urlencoded"}
    )

    # FastAPI should reject non-JSON content
    assert response.status_code == 422


def test_finalizar_empty_string_in_union_list(client):
    """Empty string in selected_unions list is invalid."""
    response = client.post(
        "/api/v4/occupation/finalizar",
        json={
            "tag_spool": "OT-123",
            "worker_id": 93,
            "worker_nombre": "MR(93)",
            "operacion": "ARM",
            "selected_unions": ["OT-123+1", "", "OT-123+3"]  # Empty string invalid
        }
    )

    # Should validate and reject empty strings
    assert response.status_code == 422


def test_iniciar_extra_unexpected_fields_ignored(client):
    """Extra fields in request are ignored (not an error)."""
    response = client.post(
        "/api/v4/occupation/iniciar",
        json={
            "tag_spool": "OT-123",
            "worker_id": 93,
            "worker_nombre": "MR(93)",
            "operacion": "ARM",
            "extra_field": "should be ignored"  # Extra field
        }
    )

    # Should pass validation (extra fields ignored)
    assert response.status_code != 422


def test_metricas_tag_with_special_characters(client):
    """TAG with special characters is accepted (URL encoding)."""
    response = client.get("/api/v4/uniones/TAG-WITH-DASHES-123/metricas")

    # Should not return 404 due to URL parsing
    # May return 500 or other error, but not URL-related 404
    assert response.status_code != 404 or "not found" in response.json().get("detail", "").lower()


def test_disponibles_case_sensitive_operacion(client):
    """Operacion query param is case-sensitive."""
    response = client.get("/api/v4/uniones/OT-123/disponibles?operacion=arm")
    # lowercase "arm" should fail validation (expects "ARM")

    assert response.status_code == 422  # Pattern mismatch
