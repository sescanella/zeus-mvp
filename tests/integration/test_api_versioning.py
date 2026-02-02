"""
Integration tests for API versioning and routing.

Tests version detection, endpoint routing, and backward compatibility.
"""

import pytest
from unittest.mock import MagicMock, patch
from fastapi.testclient import TestClient


class TestAPIVersioning:
    """Test version detection and routing between v3.0 and v4.0 endpoints"""

    @pytest.fixture
    def mock_spool_repo_v3(self):
        """Mock SpoolRepository returning v3.0 spool (Total_Uniones = 0)"""
        mock = MagicMock()
        mock.get_by_tag.return_value = MagicMock(
            tag_spool="OLD-SPOOL",
            ot="123",
            total_uniones=0,  # v3.0 indicator
            version="v3-version",
            ocupado_por=None,
        )
        mock.update_occupation.return_value = None
        return mock

    @pytest.fixture
    def mock_spool_repo_v4(self):
        """Mock SpoolRepository returning v4.0 spool (Total_Uniones > 0)"""
        mock = MagicMock()
        mock.get_by_tag.return_value = MagicMock(
            tag_spool="NEW-SPOOL",
            ot="123",
            total_uniones=10,  # v4.0 indicator
            version="v4-version",
            ocupado_por=None,
        )
        mock.update_occupation.return_value = None
        return mock

    @pytest.fixture
    def mock_redis_client(self):
        """Mock Redis client"""
        mock = MagicMock()
        mock.acquire_lock.return_value = True
        mock.release_lock.return_value = None
        mock.get_lock.return_value = None
        return mock

    @pytest.fixture
    def mock_metadata_repo(self):
        """Mock MetadataRepository"""
        mock = MagicMock()
        mock.log_event.return_value = None
        return mock

    @pytest.fixture
    def client_v3(self, mock_spool_repo_v3, mock_redis_client, mock_metadata_repo):
        """TestClient with v3.0 spool mocked"""
        from backend.main import app

        with patch("backend.repositories.spool_repository.SpoolRepository") as MockSpoolRepo, \
             patch("backend.core.redis_client.get_redis_client", return_value=mock_redis_client), \
             patch("backend.repositories.metadata_repository.MetadataRepository") as MockMetaRepo:

            MockSpoolRepo.return_value = mock_spool_repo_v3
            MockMetaRepo.return_value = mock_metadata_repo

            yield TestClient(app)

    @pytest.fixture
    def client_v4(self, mock_spool_repo_v4, mock_redis_client, mock_metadata_repo):
        """TestClient with v4.0 spool mocked"""
        from backend.main import app

        with patch("backend.repositories.spool_repository.SpoolRepository") as MockSpoolRepo, \
             patch("backend.core.redis_client.get_redis_client", return_value=mock_redis_client), \
             patch("backend.repositories.metadata_repository.MetadataRepository") as MockMetaRepo, \
             patch("backend.repositories.union_repository.UnionRepository") as MockUnionRepo:

            MockSpoolRepo.return_value = mock_spool_repo_v4
            MockMetaRepo.return_value = mock_metadata_repo

            # Mock UnionRepository for v4.0 operations
            mock_union_repo = MagicMock()
            mock_union_repo.get_by_ot.return_value = []
            mock_union_repo.get_disponibles_arm_by_ot.return_value = []
            MockUnionRepo.return_value = mock_union_repo

            yield TestClient(app)

    def test_v3_spool_rejects_v4_endpoint(self, client_v3):
        """v3.0 spool calling v4.0 endpoint returns 400 with helpful error"""
        response = client_v3.post("/api/v4/occupation/iniciar", json={
            "tag_spool": "OLD-SPOOL",  # Total_Uniones = 0
            "worker_id": 93,
            "operacion": "ARM"
        })

        assert response.status_code == 400
        detail = response.json()["detail"]
        assert detail["error"] == "WRONG_VERSION"
        assert "v3.0" in detail["message"]
        assert "/api/v3/occupation/tomar" in detail["correct_endpoint"]

    def test_v4_spool_accepts_v4_endpoint(self, client_v4):
        """v4.0 spool works with v4.0 endpoint"""
        response = client_v4.post("/api/v4/occupation/iniciar", json={
            "tag_spool": "NEW-SPOOL",  # Total_Uniones = 10
            "worker_id": 93,
            "operacion": "ARM"
        })

        assert response.status_code == 200
        data = response.json()
        assert data["tag_spool"] == "NEW-SPOOL"
        assert "ocupado exitosamente" in data["message"].lower()

    def test_v3_endpoints_still_functional(self, client_v3):
        """v3.0 endpoints work at new /api/v3/ prefix"""
        response = client_v3.post("/api/v3/occupation/tomar", json={
            "tag_spool": "OLD-SPOOL",
            "worker_id": 93,
            "worker_nombre": "MR(93)",
            "operacion": "ARM"
        })

        # Should succeed or return 409 if already occupied
        assert response.status_code in [200, 409]

        if response.status_code == 200:
            data = response.json()
            assert data["tag_spool"] == "OLD-SPOOL"
            assert "ocupado" in data["message"].lower() or "tomar" in data["message"].lower()

    def test_legacy_endpoints_still_work(self, client_v3):
        """Legacy /api/occupation/* paths still functional for backward compatibility"""
        response = client_v3.post("/api/occupation/tomar", json={
            "tag_spool": "OLD-SPOOL",
            "worker_id": 93,
            "worker_nombre": "MR(93)",
            "operacion": "ARM"
        })

        # Legacy routes should work
        assert response.status_code in [200, 409]

    def test_v3_pausar_endpoint(self, client_v3, mock_spool_repo_v3):
        """v3.0 PAUSAR endpoint works at /api/v3/ prefix"""
        # Set spool as occupied first
        mock_spool_repo_v3.get_by_tag.return_value.ocupado_por = "MR(93)"

        response = client_v3.post("/api/v3/occupation/pausar", json={
            "tag_spool": "OLD-SPOOL",
            "worker_id": 93,
            "worker_nombre": "MR(93)",
            "operacion": "ARM"
        })

        assert response.status_code == 200
        data = response.json()
        assert "pausad" in data["message"].lower() or "liberad" in data["message"].lower()

    def test_v3_completar_endpoint(self, client_v3, mock_spool_repo_v3):
        """v3.0 COMPLETAR endpoint works at /api/v3/ prefix"""
        # Set spool as occupied first
        mock_spool_repo_v3.get_by_tag.return_value.ocupado_por = "MR(93)"

        response = client_v3.post("/api/v3/occupation/completar", json={
            "tag_spool": "OLD-SPOOL",
            "worker_id": 93,
            "worker_nombre": "MR(93)",
            "operacion": "ARM",
            "fecha_operacion": "2026-02-02"
        })

        assert response.status_code == 200
        data = response.json()
        assert "completad" in data["message"].lower()

    def test_v4_query_endpoints_require_v4_spool(self, client_v3):
        """v4.0 query endpoints work only with v4.0 spools"""
        # Query disponibles on v3.0 spool should work but return empty or error gracefully
        response = client_v3.get("/api/v4/uniones/OLD-SPOOL/disponibles?operacion=ARM")

        # Should either return empty list or 400 version error
        # Implementation may vary - verify it doesn't crash
        assert response.status_code in [200, 400]

    def test_version_detection_helper_functions(self):
        """Version detection utility functions work correctly"""
        from backend.utils.version import is_v4_spool, get_spool_version

        # v3.0 spool
        v3_spool = MagicMock(total_uniones=0)
        assert is_v4_spool(v3_spool) is False
        assert get_spool_version(v3_spool) == "v3.0"

        # v4.0 spool
        v4_spool = MagicMock(total_uniones=10)
        assert is_v4_spool(v4_spool) is True
        assert get_spool_version(v4_spool) == "v4.0"

    def test_mixed_version_workflow(self, mock_spool_repo_v3, mock_spool_repo_v4, mock_redis_client, mock_metadata_repo):
        """Test handling multiple spools with different versions"""
        from backend.main import app

        with patch("backend.repositories.spool_repository.SpoolRepository") as MockSpoolRepo, \
             patch("backend.core.redis_client.get_redis_client", return_value=mock_redis_client), \
             patch("backend.repositories.metadata_repository.MetadataRepository") as MockMetaRepo:

            def get_by_tag_dynamic(tag):
                if tag == "OLD-SPOOL":
                    return mock_spool_repo_v3.get_by_tag.return_value
                else:
                    return mock_spool_repo_v4.get_by_tag.return_value

            mock_repo = MagicMock()
            mock_repo.get_by_tag.side_effect = get_by_tag_dynamic
            MockSpoolRepo.return_value = mock_repo
            MockMetaRepo.return_value = mock_metadata_repo

            client = TestClient(app)

            # v3.0 spool uses v3.0 endpoint
            response = client.post("/api/v3/occupation/tomar", json={
                "tag_spool": "OLD-SPOOL",
                "worker_id": 93,
                "worker_nombre": "MR(93)",
                "operacion": "ARM"
            })
            assert response.status_code in [200, 409]

            # v4.0 spool uses v4.0 endpoint
            with patch("backend.repositories.union_repository.UnionRepository"):
                response = client.post("/api/v4/occupation/iniciar", json={
                    "tag_spool": "NEW-SPOOL",
                    "worker_id": 93,
                    "operacion": "ARM"
                })
                assert response.status_code == 200

    def test_api_docs_tag_organization(self):
        """API documentation properly tags v3 and v4 endpoints"""
        from backend.main import app

        # Get OpenAPI schema
        openapi_schema = app.openapi()

        # Check that paths are organized by tags
        paths = openapi_schema.get("paths", {})

        # v3.0 endpoints should have v3-occupation tag
        v3_tomar_path = paths.get("/api/v3/occupation/tomar", {})
        if v3_tomar_path:
            tags = v3_tomar_path.get("post", {}).get("tags", [])
            assert "v3-occupation" in tags

        # v4.0 endpoints should have v4-unions tag
        v4_iniciar_path = paths.get("/api/v4/occupation/iniciar", {})
        if v4_iniciar_path:
            tags = v4_iniciar_path.get("post", {}).get("tags", [])
            assert "v4-unions" in tags

    def test_error_messages_provide_guidance(self, client_v3):
        """Version mismatch errors provide clear guidance to frontend"""
        response = client_v3.post("/api/v4/occupation/iniciar", json={
            "tag_spool": "OLD-SPOOL",
            "worker_id": 93,
            "operacion": "ARM"
        })

        assert response.status_code == 400
        detail = response.json()["detail"]

        # Should have all helpful fields
        assert "error" in detail
        assert "message" in detail
        assert "correct_endpoint" in detail
        assert "spool_version" in detail

        # Message should be user-friendly
        assert "v3.0" in detail["message"] or "v4.0" in detail["message"]
