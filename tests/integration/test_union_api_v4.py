"""
Integration tests for v4.0 union API workflows.

Tests end-to-end INICIAR → FINALIZAR flows, race conditions,
metrología auto-trigger, and performance validation.
"""

import pytest
import time
from unittest.mock import MagicMock, patch
from fastapi.testclient import TestClient


class TestUnionAPIV4Workflows:
    """Integration tests for v4.0 union API workflows"""

    @pytest.fixture
    def mock_union_repo(self):
        """Mock UnionRepository with realistic test data"""
        mock = MagicMock()

        # Simulate 10 unions for TEST-02
        test_unions = [
            {
                "id": f"TEST-02+{i}",
                "tag_spool": "TEST-02",
                "n_union": i,
                "dn_union": 3.5,
                "tipo_union": "BW",
                "arm_worker": None if i > 3 else "MR(93)",
                "arm_fecha_inicio": None,
                "arm_fecha_fin": None,
                "sol_worker": None,
                "sol_fecha_inicio": None,
                "sol_fecha_fin": None,
            }
            for i in range(1, 11)
        ]

        mock.get_by_ot.return_value = test_unions
        mock.get_disponibles_arm_by_ot.return_value = [u for u in test_unions if not u["arm_worker"]]
        mock.get_disponibles_sold_by_ot.return_value = []  # ARM not complete yet
        mock.batch_update_arm.return_value = None
        mock.batch_update_sold.return_value = None

        return mock

    @pytest.fixture
    def mock_spool_repo(self):
        """Mock SpoolRepository with v4.0 spool"""
        mock = MagicMock()

        # v4.0 spool (Total_Uniones > 0)
        mock.get_by_tag.return_value = MagicMock(
            tag_spool="TEST-02",
            ot="123",
            total_uniones=10,
            uniones_arm_completadas=3,
            uniones_sold_completadas=0,
            pulgadas_arm=10.50,
            pulgadas_sold=0.0,
            version="test-version-123",
            ocupado_por=None,
        )

        mock.update_occupation.return_value = None
        mock.release_occupation.return_value = None

        return mock

    @pytest.fixture
    def mock_metadata_repo(self):
        """Mock MetadataRepository"""
        mock = MagicMock()
        mock.log_event.return_value = None
        mock.batch_log_events.return_value = None
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
    def client_with_mocks(self, mock_union_repo, mock_spool_repo, mock_metadata_repo, mock_redis_client):
        """TestClient with all dependencies mocked"""
        from main import app

        with patch("backend.repositories.union_repository.UnionRepository") as MockUnionRepo, \
             patch("backend.repositories.spool_repository.SpoolRepository") as MockSpoolRepo, \
             patch("backend.repositories.metadata_repository.MetadataRepository") as MockMetaRepo, \
             patch("backend.core.redis_client.get_redis_client", return_value=mock_redis_client):

            MockUnionRepo.return_value = mock_union_repo
            MockSpoolRepo.return_value = mock_spool_repo
            MockMetaRepo.return_value = mock_metadata_repo

            yield TestClient(app)

    def test_iniciar_finalizar_pausar_flow(self, client_with_mocks, mock_union_repo):
        """Complete workflow: INICIAR → partial selection → PAUSAR"""
        client = client_with_mocks

        # 1. INICIAR
        response = client.post("/api/v4/occupation/iniciar", json={
            "tag_spool": "TEST-02",
            "worker_id": 93,
            "operacion": "ARM"
        })
        assert response.status_code == 200
        data = response.json()
        assert "ocupado exitosamente" in data["message"].lower()
        assert data["tag_spool"] == "TEST-02"

        # 2. Query disponibles
        response = client.get("/api/v4/uniones/TEST-02/disponibles?operacion=ARM")
        assert response.status_code == 200
        disponibles = response.json()["unions"]
        assert len(disponibles) > 3

        # 3. FINALIZAR with partial selection (should trigger PAUSAR)
        selected = [u["id"] for u in disponibles[:3]]
        response = client.post("/api/v4/occupation/finalizar", json={
            "tag_spool": "TEST-02",
            "worker_id": 93,
            "operacion": "ARM",
            "selected_unions": selected
        })
        assert response.status_code == 200
        data = response.json()
        assert data["action_taken"] == "PAUSAR"
        assert data["unions_processed"] == 3
        assert data["pulgadas"] > 0
        assert "3 uniones" in data["message"]

    def test_iniciar_finalizar_completar_flow(self, client_with_mocks, mock_union_repo):
        """Complete workflow: INICIAR → full selection → COMPLETAR"""
        client = client_with_mocks

        # Update mock to show all unions completed after selection
        def batch_update_side_effect(*args, **kwargs):
            # Simulate all ARM completed
            mock_union_repo.get_disponibles_arm_by_ot.return_value = []
            # Make SOLD unions available
            all_unions = mock_union_repo.get_by_ot.return_value
            mock_union_repo.get_disponibles_sold_by_ot.return_value = [
                u for u in all_unions if u["tipo_union"] in ["BW", "BR", "SO", "FILL", "LET"]
            ]

        mock_union_repo.batch_update_arm.side_effect = batch_update_side_effect

        # 1. INICIAR
        response = client.post("/api/v4/occupation/iniciar", json={
            "tag_spool": "TEST-02",
            "worker_id": 93,
            "operacion": "ARM"
        })
        assert response.status_code == 200

        # 2. Query disponibles
        response = client.get("/api/v4/uniones/TEST-02/disponibles?operacion=ARM")
        assert response.status_code == 200
        disponibles = response.json()["unions"]

        # 3. FINALIZAR with ALL unions selected (should trigger COMPLETAR)
        selected = [u["id"] for u in disponibles]
        response = client.post("/api/v4/occupation/finalizar", json={
            "tag_spool": "TEST-02",
            "worker_id": 93,
            "operacion": "ARM",
            "selected_unions": selected
        })
        assert response.status_code == 200
        data = response.json()
        assert data["action_taken"] == "COMPLETAR"
        assert data["unions_processed"] == len(disponibles)
        assert "completada" in data["message"].lower()

    def test_sold_requires_arm_prerequisite(self, client_with_mocks, mock_union_repo):
        """SOLD operation requires ARM unions to be complete"""
        client = client_with_mocks

        # Mock shows no ARM completed unions
        mock_union_repo.get_disponibles_arm_by_ot.return_value = [
            {"id": f"TEST-02+{i}", "n_union": i} for i in range(1, 6)
        ]

        # 1. Try INICIAR SOLD on spool without ARM complete (should fail)
        response = client.post("/api/v4/occupation/iniciar", json={
            "tag_spool": "TEST-02",
            "worker_id": 93,
            "operacion": "SOLD"
        })
        assert response.status_code == 403
        detail = response.json()["detail"]
        assert "ARM_PREREQUISITE" in detail["error"]
        assert "5 uniones ARM pendientes" in detail["message"]

    def test_sold_after_arm_complete(self, client_with_mocks, mock_union_repo, mock_spool_repo):
        """SOLD works after ARM is complete"""
        client = client_with_mocks

        # Mock shows all ARM completed
        mock_union_repo.get_disponibles_arm_by_ot.return_value = []

        # Mock disponibles SOLD
        test_unions = [
            {
                "id": f"TEST-02+{i}",
                "tag_spool": "TEST-02",
                "n_union": i,
                "dn_union": 3.5,
                "tipo_union": "BW",
                "arm_worker": "MR(93)",
                "sol_worker": None,
            }
            for i in range(1, 6)
        ]
        mock_union_repo.get_disponibles_sold_by_ot.return_value = test_unions

        # Update spool mock to show ARM complete
        mock_spool_repo.get_by_tag.return_value.uniones_arm_completadas = 10

        # INICIAR SOLD should succeed
        response = client.post("/api/v4/occupation/iniciar", json={
            "tag_spool": "TEST-02",
            "worker_id": 93,
            "operacion": "SOLD"
        })
        assert response.status_code == 200

    def test_metrologia_auto_trigger(self, client_with_mocks, mock_union_repo, mock_spool_repo):
        """100% SOLD completion triggers metrología transition"""
        client = client_with_mocks

        # Setup: All ARM complete, completing last SOLD unions
        mock_union_repo.get_disponibles_arm_by_ot.return_value = []
        mock_union_repo.get_disponibles_sold_by_ot.return_value = [
            {"id": "TEST-02+1", "tipo_union": "BW"}
        ]

        # Mock spool shows near-complete state
        mock_spool = mock_spool_repo.get_by_tag.return_value
        mock_spool.uniones_arm_completadas = 10
        mock_spool.uniones_sold_completadas = 9
        mock_spool.total_uniones = 10

        # Complete last SOLD union
        response = client.post("/api/v4/occupation/iniciar", json={
            "tag_spool": "TEST-02",
            "worker_id": 93,
            "operacion": "SOLD"
        })
        assert response.status_code == 200

        # Simulate completing all remaining SOLD
        mock_union_repo.get_disponibles_sold_by_ot.return_value = []

        response = client.post("/api/v4/occupation/finalizar", json={
            "tag_spool": "TEST-02",
            "worker_id": 93,
            "operacion": "SOLD",
            "selected_unions": ["TEST-02+1"]
        })
        assert response.status_code == 200
        data = response.json()
        assert data["metrologia_triggered"] is True
        assert "metrología" in data["message"].lower()

    def test_performance_10_unions_under_1s(self, client_with_mocks, mock_union_repo):
        """PERF-02: 10-union operation completes in < 1s"""
        client = client_with_mocks

        # Setup: 10 disponibles
        disponibles = [
            {
                "id": f"TEST-02+{i}",
                "tag_spool": "TEST-02",
                "n_union": i,
                "dn_union": 3.5,
                "tipo_union": "BW",
            }
            for i in range(1, 11)
        ]
        mock_union_repo.get_disponibles_arm_by_ot.return_value = disponibles

        # Simulate realistic latency (300ms for batch_update)
        def batch_update_with_latency(*args, **kwargs):
            time.sleep(0.3)  # Simulate Google Sheets API call

        mock_union_repo.batch_update_arm.side_effect = batch_update_with_latency

        # INICIAR
        response = client.post("/api/v4/occupation/iniciar", json={
            "tag_spool": "TEST-02",
            "worker_id": 93,
            "operacion": "ARM"
        })
        assert response.status_code == 200

        # Select 10 unions
        selected = [f"TEST-02+{i}" for i in range(1, 11)]

        start = time.time()
        response = client.post("/api/v4/occupation/finalizar", json={
            "tag_spool": "TEST-02",
            "worker_id": 93,
            "operacion": "ARM",
            "selected_unions": selected
        })
        duration = time.time() - start

        assert response.status_code == 200
        assert duration < 1.0, f"Operation took {duration:.2f}s, exceeds 1s target"
        data = response.json()
        assert data["unions_processed"] == 10

    def test_race_condition_handling(self, client_with_mocks, mock_union_repo):
        """Concurrent workers cause race condition - selected > available"""
        client = client_with_mocks

        # Setup: Worker 1 initiates
        response = client.post("/api/v4/occupation/iniciar", json={
            "tag_spool": "TEST-02",
            "worker_id": 93,
            "operacion": "ARM"
        })
        assert response.status_code == 200

        # Simulate Worker 2 completing some unions in between
        # Now only 3 unions available instead of 10
        mock_union_repo.get_disponibles_arm_by_ot.return_value = [
            {"id": f"TEST-02+{i}", "n_union": i} for i in range(8, 11)
        ]

        # Worker 1 tries to finalize with stale selection (10 unions)
        # This should trigger ValueError in service layer
        mock_union_repo.batch_update_arm.side_effect = ValueError(
            "Race condition detected: selected_count=10 > disponibles_count=3"
        )

        response = client.post("/api/v4/occupation/finalizar", json={
            "tag_spool": "TEST-02",
            "worker_id": 93,
            "operacion": "ARM",
            "selected_unions": [f"TEST-02+{i}" for i in range(1, 11)]
        })

        # Should return 409 Conflict
        assert response.status_code == 409
        detail = response.json()["detail"]
        assert "Race condition" in detail["message"] or "CONFLICT" in detail["error"]

    def test_empty_selection_cancellation(self, client_with_mocks):
        """Empty selected_unions list triggers cancellation"""
        client = client_with_mocks

        # INICIAR
        response = client.post("/api/v4/occupation/iniciar", json={
            "tag_spool": "TEST-02",
            "worker_id": 93,
            "operacion": "ARM"
        })
        assert response.status_code == 200

        # FINALIZAR with empty selection
        response = client.post("/api/v4/occupation/finalizar", json={
            "tag_spool": "TEST-02",
            "worker_id": 93,
            "operacion": "ARM",
            "selected_unions": []
        })
        assert response.status_code == 200
        data = response.json()
        assert data["action_taken"] == "CANCELAR"
        assert "cancelada" in data["message"].lower()
        assert data["unions_processed"] == 0

    def test_ownership_validation(self, client_with_mocks, mock_spool_repo):
        """Worker must own spool to finalize"""
        client = client_with_mocks

        # Worker 1 initiates
        response = client.post("/api/v4/occupation/iniciar", json={
            "tag_spool": "TEST-02",
            "worker_id": 93,
            "operacion": "ARM"
        })
        assert response.status_code == 200

        # Update mock to show spool occupied by Worker 1
        mock_spool_repo.get_by_tag.return_value.ocupado_por = "MR(93)"

        # Worker 2 tries to finalize
        response = client.post("/api/v4/occupation/finalizar", json={
            "tag_spool": "TEST-02",
            "worker_id": 94,  # Different worker
            "operacion": "ARM",
            "selected_unions": ["TEST-02+1"]
        })
        assert response.status_code == 403
        detail = response.json()["detail"]
        assert "NO_AUTORIZADO" in detail["error"] or "no es propietario" in detail["message"].lower()
