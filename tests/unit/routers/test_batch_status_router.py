"""
Unit tests for batch spool status endpoint — POST /api/spools/batch-status.

Tests validate:
- 200 response with BatchStatusResponse when valid tags provided
- Missing tags are silently skipped (no 404 per missing tag)
- total reflects only the found spools count
- Validation: empty tags list returns 422
- Validation: more than 100 tags returns 422
- SpoolStatus fields populated correctly in batch response

Uses FastAPI TestClient with dependency_overrides to mock SheetsRepository.

Reference:
- Router: backend/routers/spool_status_router.py
- Models: backend/models/spool_status.py
- Plan: 00-02-PLAN.md (API-02)
"""
import pytest
from unittest.mock import MagicMock
from fastapi.testclient import TestClient

from backend.main import app
from backend.core.dependency import get_sheets_repository
from backend.models.spool import Spool


# ==================== HELPERS ====================


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


def _make_spool_map(*spools: Spool) -> dict:
    """Build a tag -> Spool lookup dict for mock side_effect use."""
    return {s.tag_spool: s for s in spools}


def _make_repo_for_spools(*spools: Spool) -> MagicMock:
    """
    Return a SheetsRepository mock where get_spool_by_tag returns the spool
    for known tags and None for unknown tags.
    """
    spool_map = _make_spool_map(*spools)
    repo = MagicMock()
    repo.get_spool_by_tag = MagicMock(side_effect=lambda tag: spool_map.get(tag))
    return repo


# ==================== FIXTURES ====================


SPOOL_A = make_mock_spool(
    tag_spool="A-001",
    ocupado_por="MR(93)",
    estado_detalle="MR(93) trabajando ARM (ARM en progreso, SOLD pendiente)",
    total_uniones=5,
    uniones_arm_completadas=0,
    uniones_sold_completadas=0,
)

SPOOL_B = make_mock_spool(
    tag_spool="B-002",
    ocupado_por=None,
    estado_detalle=None,
    total_uniones=3,
    uniones_arm_completadas=3,
    uniones_sold_completadas=0,
)


@pytest.fixture
def client_with_two_spools():
    """TestClient with two known spools (A-001, B-002) in the mock repo."""
    repo = _make_repo_for_spools(SPOOL_A, SPOOL_B)
    app.dependency_overrides[get_sheets_repository] = lambda: repo
    yield TestClient(app)
    app.dependency_overrides.clear()


@pytest.fixture
def client_with_no_spools():
    """TestClient where all tag lookups return None (empty repo)."""
    repo = _make_repo_for_spools()
    app.dependency_overrides[get_sheets_repository] = lambda: repo
    yield TestClient(app)
    app.dependency_overrides.clear()


@pytest.fixture
def client_with_one_spool():
    """TestClient with only SPOOL_A (A-001) available."""
    repo = _make_repo_for_spools(SPOOL_A)
    app.dependency_overrides[get_sheets_repository] = lambda: repo
    yield TestClient(app)
    app.dependency_overrides.clear()


# ==================== SUCCESS: VALID BATCH ====================


def test_batch_status_returns_200(client_with_two_spools):
    """POST /api/spools/batch-status returns 200 for a valid tags list."""
    response = client_with_two_spools.post(
        "/api/spools/batch-status",
        json={"tags": ["A-001", "B-002"]},
    )
    assert response.status_code == 200


def test_batch_status_returns_all_found_spools(client_with_two_spools):
    """Batch with 2 existing tags returns total=2 and 2 items in spools list."""
    response = client_with_two_spools.post(
        "/api/spools/batch-status",
        json={"tags": ["A-001", "B-002"]},
    )
    data = response.json()
    assert data["total"] == 2
    assert len(data["spools"]) == 2


def test_batch_status_response_contains_tag_spool_field(client_with_two_spools):
    """Each item in spools list contains tag_spool field."""
    response = client_with_two_spools.post(
        "/api/spools/batch-status",
        json={"tags": ["A-001", "B-002"]},
    )
    data = response.json()
    tags = {s["tag_spool"] for s in data["spools"]}
    assert "A-001" in tags
    assert "B-002" in tags


def test_batch_status_computed_fields_present(client_with_two_spools):
    """Each SpoolStatus in response contains computed fields."""
    response = client_with_two_spools.post(
        "/api/spools/batch-status",
        json={"tags": ["A-001"]},
    )
    data = response.json()
    spool = data["spools"][0]
    assert "operacion_actual" in spool
    assert "estado_trabajo" in spool
    assert "ciclo_rep" in spool


def test_batch_status_occupied_spool_has_correct_operacion_actual(client_with_two_spools):
    """Spool A-001 has operacion_actual=ARM (from estado_detalle)."""
    response = client_with_two_spools.post(
        "/api/spools/batch-status",
        json={"tags": ["A-001"]},
    )
    data = response.json()
    spool_a = next(s for s in data["spools"] if s["tag_spool"] == "A-001")
    assert spool_a["operacion_actual"] == "ARM"
    assert spool_a["estado_trabajo"] == "EN_PROGRESO"
    assert spool_a["ocupado_por"] == "MR(93)"


def test_batch_status_libre_spool_has_libre_estado(client_with_two_spools):
    """Spool B-002 has no estado_detalle, so estado_trabajo=LIBRE."""
    response = client_with_two_spools.post(
        "/api/spools/batch-status",
        json={"tags": ["B-002"]},
    )
    data = response.json()
    spool_b = data["spools"][0]
    assert spool_b["estado_trabajo"] == "LIBRE"
    assert spool_b["operacion_actual"] is None


def test_batch_status_single_tag_returns_total_1(client_with_one_spool):
    """Batch with single valid tag returns total=1."""
    response = client_with_one_spool.post(
        "/api/spools/batch-status",
        json={"tags": ["A-001"]},
    )
    data = response.json()
    assert data["total"] == 1
    assert len(data["spools"]) == 1


# ==================== MISSING TAGS: SILENTLY SKIPPED ====================


def test_batch_status_missing_tag_is_skipped(client_with_one_spool):
    """Tag not in the repo is silently omitted from the response."""
    response = client_with_one_spool.post(
        "/api/spools/batch-status",
        json={"tags": ["A-001", "DOES-NOT-EXIST"]},
    )
    data = response.json()
    assert data["total"] == 1
    assert len(data["spools"]) == 1
    assert data["spools"][0]["tag_spool"] == "A-001"


def test_batch_status_all_missing_tags_returns_empty(client_with_no_spools):
    """When no tags are found, response has total=0 and empty spools list."""
    response = client_with_no_spools.post(
        "/api/spools/batch-status",
        json={"tags": ["NONEXISTENT-1", "NONEXISTENT-2"]},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 0
    assert data["spools"] == []


def test_batch_status_no_404_for_missing_tags(client_with_no_spools):
    """Missing tags never cause a 404 — endpoint always returns 200."""
    response = client_with_no_spools.post(
        "/api/spools/batch-status",
        json={"tags": ["GHOST-TAG"]},
    )
    assert response.status_code == 200


def test_batch_status_partial_match_total_reflects_found_count(client_with_one_spool):
    """total equals number of found spools, not the number requested."""
    # Request 3 tags, only 1 exists
    response = client_with_one_spool.post(
        "/api/spools/batch-status",
        json={"tags": ["A-001", "MISSING-1", "MISSING-2"]},
    )
    data = response.json()
    assert data["total"] == 1
    assert len(data["spools"]) == 1


# ==================== VALIDATION: 422 ERRORS ====================


def test_batch_status_empty_tags_returns_422(client_with_no_spools):
    """POST with empty tags list returns 422 (min_length=1 validation)."""
    response = client_with_no_spools.post(
        "/api/spools/batch-status",
        json={"tags": []},
    )
    assert response.status_code == 422


def test_batch_status_over_100_tags_returns_422(client_with_no_spools):
    """POST with 101 tags returns 422 (max_length=100 validation)."""
    tags = [f"TAG-{i:03d}" for i in range(101)]
    response = client_with_no_spools.post(
        "/api/spools/batch-status",
        json={"tags": tags},
    )
    assert response.status_code == 422


def test_batch_status_exactly_100_tags_is_accepted(client_with_no_spools):
    """POST with exactly 100 tags is valid (boundary value, max_length=100)."""
    tags = [f"TAG-{i:03d}" for i in range(100)]
    response = client_with_no_spools.post(
        "/api/spools/batch-status",
        json={"tags": tags},
    )
    # Should not be 422 — all tags missing returns 200 with empty spools
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 0


def test_batch_status_missing_body_returns_422(client_with_no_spools):
    """POST with no body returns 422."""
    response = client_with_no_spools.post("/api/spools/batch-status")
    assert response.status_code == 422


def test_batch_status_missing_tags_field_returns_422(client_with_no_spools):
    """POST with body missing the 'tags' field returns 422."""
    response = client_with_no_spools.post(
        "/api/spools/batch-status",
        json={"wrong_field": ["A-001"]},
    )
    assert response.status_code == 422
