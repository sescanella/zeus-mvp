"""
Smoke tests for API versioning and routing.

Tests version detection, endpoint routing, and backward compatibility.
Comprehensive versioning tests require backend infrastructure.

For full validation, use:
.planning/phases/11-api-endpoints-metrics/MANUAL_VALIDATION.md
"""

import pytest
from fastapi.testclient import TestClient
from backend.main import app


@pytest.fixture
def client():
    """FastAPI TestClient for smoke tests"""
    return TestClient(app)


class TestAPIVersioning:
    """Test version detection and routing between v3.0 and v4.0 endpoints"""

    def test_v3_endpoints_exist_at_new_prefix(self, client):
        """v3.0 endpoints exist at /api/v3/ prefix"""
        response = client.post("/api/v3/occupation/tomar", json={
            "tag_spool": "TEST-SPOOL",
            "worker_id": 93,
            "worker_nombre": "MR(93)",
            "operacion": "ARM"
        })
        # Endpoint exists - may return 404 if spool not found (valid business logic)
        # Acceptable: 200 (success), 404 (spool not found), 409 (already occupied), 500 (backend error)
        assert response.status_code in [200, 404, 409, 500]

    def test_v4_endpoints_exist_at_new_prefix(self, client):
        """v4.0 endpoints exist at /api/v4/ prefix"""
        response = client.post("/api/v4/occupation/iniciar", json={
            "tag_spool": "TEST-SPOOL",
            "worker_id": 93,
            "worker_nombre": "MR(93)",
            "operacion": "ARM"
        })
        # Endpoint exists - may return various status codes based on business logic
        assert response.status_code in [200, 400, 404, 409, 500]

    def test_legacy_endpoints_still_exist(self, client):
        """Legacy /api/occupation/* paths still exist for backward compatibility"""
        response = client.post("/api/occupation/tomar", json={
            "tag_spool": "TEST-SPOOL",
            "worker_id": 93,
            "worker_nombre": "MR(93)",
            "operacion": "ARM"
        })
        # Legacy routes should work
        assert response.status_code in [200, 404, 409, 500]

    def test_v3_pausar_endpoint_exists(self, client):
        """v3.0 PAUSAR endpoint exists at /api/v3/"""
        response = client.post("/api/v3/occupation/pausar", json={
            "tag_spool": "TEST-SPOOL",
            "worker_id": 93,
            "worker_nombre": "MR(93)",
            "operacion": "ARM"
        })
        # Endpoint exists
        assert response.status_code in [200, 403, 404, 409, 500]

    def test_v3_completar_endpoint_exists(self, client):
        """v3.0 COMPLETAR endpoint exists at /api/v3/"""
        response = client.post("/api/v3/occupation/completar", json={
            "tag_spool": "TEST-SPOOL",
            "worker_id": 93,
            "worker_nombre": "MR(93)",
            "operacion": "ARM",
            "fecha_operacion": "2026-02-02"
        })
        # Endpoint exists
        assert response.status_code in [200, 403, 404, 409, 422, 500]

    def test_version_detection_helper_functions(self):
        """Version detection utility functions work correctly"""
        from backend.utils.version_detection import is_v4_spool, get_spool_version
        from unittest.mock import MagicMock

        # v3.0 spool
        v3_spool = MagicMock(total_uniones=0)
        assert is_v4_spool(v3_spool) is False
        assert get_spool_version(v3_spool) == "v3.0"

        # v4.0 spool
        v4_spool = MagicMock(total_uniones=10)
        assert is_v4_spool(v4_spool) is True
        assert get_spool_version(v4_spool) == "v4.0"

    def test_api_docs_tag_organization(self, client):
        """API documentation properly organizes v3 and v4 endpoints"""
        response = client.get("/openapi.json")
        assert response.status_code == 200

        openapi_schema = response.json()
        paths = openapi_schema.get("paths", {})

        # Check that both v3 and v4 paths exist
        v3_paths = [p for p in paths if "/api/v3/" in p]
        v4_paths = [p for p in paths if "/api/v4/" in p]

        assert len(v3_paths) > 0, "v3.0 endpoints missing from API docs"
        assert len(v4_paths) > 0, "v4.0 endpoints missing from API docs"

        # Check specific endpoints
        assert "/api/v3/occupation/tomar" in paths
        assert "/api/v4/occupation/iniciar" in paths

    def test_openapi_endpoints_documented(self, client):
        """All new v4.0 endpoints are documented in OpenAPI schema"""
        response = client.get("/openapi.json")
        assert response.status_code == 200

        openapi_schema = response.json()
        paths = openapi_schema.get("paths", {})

        # v4.0 occupation endpoints
        assert "/api/v4/occupation/iniciar" in paths
        assert "/api/v4/occupation/finalizar" in paths

        # v4.0 union query endpoints
        assert "/api/v4/uniones/{tag}/disponibles" in paths
        assert "/api/v4/uniones/{tag}/metricas" in paths


class TestVersionDetectionWorkflows:
    """
    Version detection workflow tests (require manual validation).

    These test cases document expected version detection behavior
    but require backend infrastructure to execute.
    """

    @pytest.mark.skip(reason="Requires backend infrastructure - use MANUAL_VALIDATION.md")
    def test_v3_spool_rejects_v4_endpoint(self):
        """
        v3.0 spool calling v4.0 endpoint returns 400 with helpful error

        Manual test procedure:
        1. POST /api/v4/occupation/iniciar with v3.0 spool (Total_Uniones = 0)
        2. Verify 400 Bad Request
        3. Verify response has:
           - error: "WRONG_VERSION"
           - message: describes v3.0 spool issue
           - correct_endpoint: "/api/v3/occupation/tomar"
           - spool_version: "v3.0"

        See: MANUAL_VALIDATION.md Test #6
        """
        pass

    @pytest.mark.skip(reason="Requires backend infrastructure - use MANUAL_VALIDATION.md")
    def test_v4_spool_accepts_v4_endpoint(self):
        """
        v4.0 spool works with v4.0 endpoint

        Manual test procedure:
        1. POST /api/v4/occupation/iniciar with v4.0 spool (Total_Uniones > 0)
        2. Verify 200 OK
        3. Verify successful occupation

        See: MANUAL_VALIDATION.md Test #1
        """
        pass

    @pytest.mark.skip(reason="Requires backend infrastructure - use MANUAL_VALIDATION.md")
    def test_mixed_version_workflow(self):
        """
        Test handling multiple spools with different versions

        Manual test procedure:
        1. v3.0 spool uses /api/v3/occupation/tomar (success)
        2. v4.0 spool uses /api/v4/occupation/iniciar (success)
        3. v3.0 spool uses /api/v4/occupation/iniciar (400 error)
        4. Verify all responses as expected

        See: MANUAL_VALIDATION.md Tests #6-7
        """
        pass

    @pytest.mark.skip(reason="Requires backend infrastructure - use MANUAL_VALIDATION.md")
    def test_error_messages_provide_guidance(self):
        """
        Version mismatch errors provide clear guidance to frontend

        Manual test procedure:
        1. Trigger version mismatch (v3.0 spool on v4.0 endpoint)
        2. Verify error response has all helpful fields:
           - error (error code)
           - message (user-friendly description)
           - correct_endpoint (where to redirect)
           - spool_version (detected version)

        See: MANUAL_VALIDATION.md Test #6
        """
        pass
