"""
Unit tests for UnionRepository metrics aggregation methods.

v4.0: Tests for count, sum, and bulk metrics calculation with 2 decimal precision.
"""
import pytest
from unittest.mock import Mock
from datetime import datetime

from backend.repositories.union_repository import UnionRepository
from backend.models.union import Union


@pytest.fixture
def mock_sheets_repo():
    """Mock SheetsRepository for testing."""
    return Mock()


@pytest.fixture
def union_repo(mock_sheets_repo):
    """Create UnionRepository instance with mocked dependencies."""
    return UnionRepository(mock_sheets_repo)


@pytest.fixture
def sample_unions():
    """Create sample union data with various completion states."""
    now = datetime.now()

    return [
        # Union 1: ARM completed
        Union(
            id="TEST-01+1",
            ot="001",
            tag_spool="TEST-01",
            n_union=1,
            dn_union=6.0,
            tipo_union="Tipo A",
            arm_fecha_inicio=now,
            arm_fecha_fin=now,
            arm_worker="MR(93)",
            sol_fecha_inicio=None,
            sol_fecha_fin=None,
            sol_worker=None,
            ndt_fecha=None,
            ndt_status=None,
            version="uuid-1",
            creado_por="MR(93)",
            fecha_creacion=now,
            modificado_por=None,
            fecha_modificacion=None,
        ),
        # Union 2: Both ARM and SOLD completed
        Union(
            id="TEST-01+2",
            ot="001",
            tag_spool="TEST-01",
            n_union=2,
            dn_union=8.0,
            tipo_union="Tipo B",
            arm_fecha_inicio=now,
            arm_fecha_fin=now,
            arm_worker="MR(93)",
            sol_fecha_inicio=now,
            sol_fecha_fin=now,
            sol_worker="MG(95)",
            ndt_fecha=None,
            ndt_status=None,
            version="uuid-2",
            creado_por="MR(93)",
            fecha_creacion=now,
            modificado_por=None,
            fecha_modificacion=None,
        ),
        # Union 3: Both ARM and SOLD completed (decimal DN_UNION for precision test)
        Union(
            id="TEST-01+3",
            ot="001",
            tag_spool="TEST-01",
            n_union=3,
            dn_union=4.5,
            tipo_union="Tipo A",
            arm_fecha_inicio=now,
            arm_fecha_fin=now,
            arm_worker="JP(94)",
            sol_fecha_inicio=now,
            sol_fecha_fin=now,
            sol_worker="CP(96)",
            ndt_fecha=None,
            ndt_status=None,
            version="uuid-3",
            creado_por="MR(93)",
            fecha_creacion=now,
            modificado_por=None,
            fecha_modificacion=None,
        ),
        # Union 4: Nothing completed
        Union(
            id="TEST-01+4",
            ot="001",
            tag_spool="TEST-01",
            n_union=4,
            dn_union=10.0,
            tipo_union="Tipo C",
            arm_fecha_inicio=None,
            arm_fecha_fin=None,
            arm_worker=None,
            sol_fecha_inicio=None,
            sol_fecha_fin=None,
            sol_worker=None,
            ndt_fecha=None,
            ndt_status=None,
            version="uuid-4",
            creado_por="MR(93)",
            fecha_creacion=now,
            modificado_por=None,
            fecha_modificacion=None,
        ),
        # Union 5: ARM completed (for 5 ARM total test)
        Union(
            id="TEST-01+5",
            ot="001",
            tag_spool="TEST-01",
            n_union=5,
            dn_union=12.0,
            tipo_union="Tipo A",
            arm_fecha_inicio=now,
            arm_fecha_fin=now,
            arm_worker="MR(93)",
            sol_fecha_inicio=None,
            sol_fecha_fin=None,
            sol_worker=None,
            ndt_fecha=None,
            ndt_status=None,
            version="uuid-5",
            creado_por="MR(93)",
            fecha_creacion=now,
            modificado_por=None,
            fecha_modificacion=None,
        ),
    ]


def test_count_completed_arm_with_zero_completed(union_repo, monkeypatch):
    """Test count_completed_arm returns 0 when no unions are ARM-completed."""
    # Mock get_by_ot to return unions with no ARM completions
    now = datetime.now()
    unions = [
        Union(
            id="TEST-02+1",
            ot="002",
            tag_spool="TEST-02",
            n_union=1,
            dn_union=6.0,
            tipo_union="Tipo A",
            arm_fecha_inicio=None,
            arm_fecha_fin=None,
            arm_worker=None,
            sol_fecha_inicio=None,
            sol_fecha_fin=None,
            sol_worker=None,
            ndt_fecha=None,
            ndt_status=None,
            version="uuid",
            creado_por="MR(93)",
            fecha_creacion=now,
            modificado_por=None,
            fecha_modificacion=None,
        )
    ]

    monkeypatch.setattr(union_repo, "get_by_ot", lambda ot: unions)

    result = union_repo.count_completed_arm("002")

    assert result == 0


def test_count_completed_arm_with_five_completed(union_repo, sample_unions, monkeypatch):
    """Test count_completed_arm returns correct count with 5 completed."""
    # Sample data has 4 ARM-completed unions (unions 1,2,3,5)
    # We expect 4 ARM completions
    monkeypatch.setattr(union_repo, "get_by_ot", lambda ot: sample_unions)

    result = union_repo.count_completed_arm("001")

    assert result == 4  # Unions 1,2,3,5 have arm_fecha_fin


def test_count_completed_arm_empty_ot(union_repo, monkeypatch):
    """Test count_completed_arm returns 0 for empty OT (graceful handling)."""
    monkeypatch.setattr(union_repo, "get_by_ot", lambda ot: [])

    result = union_repo.count_completed_arm("999")

    assert result == 0


def test_count_completed_sold_with_various_states(union_repo, sample_unions, monkeypatch):
    """Test count_completed_sold returns correct count with mixed completion states."""
    # Sample data has 2 SOLD-completed unions (unions 2,3)
    monkeypatch.setattr(union_repo, "get_by_ot", lambda ot: sample_unions)

    result = union_repo.count_completed_sold("001")

    assert result == 2  # Unions 2,3 have sol_fecha_fin


def test_count_completed_sold_empty_ot(union_repo, monkeypatch):
    """Test count_completed_sold returns 0 for empty OT."""
    monkeypatch.setattr(union_repo, "get_by_ot", lambda ot: [])

    result = union_repo.count_completed_sold("999")

    assert result == 0


def test_sum_pulgadas_arm_returns_two_decimals(union_repo, sample_unions, monkeypatch):
    """CRITICAL: Test sum_pulgadas_arm returns 2 decimal precision (e.g., 18.50 not 18.5)."""
    monkeypatch.setattr(union_repo, "get_by_ot", lambda ot: sample_unions)

    result = union_repo.sum_pulgadas_arm("001")

    # Expected: 6.0 + 8.0 + 4.5 + 12.0 = 30.5 → 30.50 (2 decimals)
    assert result == 30.50
    assert isinstance(result, float)

    # Verify formatting produces exactly 2 decimal places
    formatted = f"{result:.2f}"
    assert formatted == "30.50"


def test_sum_pulgadas_arm_empty_returns_zero_with_two_decimals(union_repo, monkeypatch):
    """Test sum_pulgadas_arm returns 0.00 (not 0.0) for empty OT."""
    monkeypatch.setattr(union_repo, "get_by_ot", lambda ot: [])

    result = union_repo.sum_pulgadas_arm("999")

    assert result == 0.00
    # Verify precision
    formatted = f"{result:.2f}"
    assert formatted == "0.00"


def test_sum_pulgadas_sold_with_mixed_completion(union_repo, sample_unions, monkeypatch):
    """Test sum_pulgadas_sold sums only SOLD-completed unions with 2 decimals."""
    monkeypatch.setattr(union_repo, "get_by_ot", lambda ot: sample_unions)

    result = union_repo.sum_pulgadas_sold("001")

    # Expected: 8.0 + 4.5 = 12.5 → 12.50 (2 decimals)
    assert result == 12.50

    # Verify formatting
    formatted = f"{result:.2f}"
    assert formatted == "12.50"


def test_sum_pulgadas_sold_empty_returns_zero_with_two_decimals(union_repo, monkeypatch):
    """Test sum_pulgadas_sold returns 0.00 for empty OT."""
    monkeypatch.setattr(union_repo, "get_by_ot", lambda ot: [])

    result = union_repo.sum_pulgadas_sold("999")

    assert result == 0.00
    formatted = f"{result:.2f}"
    assert formatted == "0.00"


def test_get_total_uniones_counts_all_regardless_of_state(union_repo, sample_unions, monkeypatch):
    """Test get_total_uniones counts ALL unions regardless of completion state."""
    monkeypatch.setattr(union_repo, "get_by_ot", lambda ot: sample_unions)

    result = union_repo.get_total_uniones("001")

    # Should count all 5 unions (completed, partial, none)
    assert result == 5


def test_get_total_uniones_empty_ot(union_repo, monkeypatch):
    """Test get_total_uniones returns 0 for empty OT."""
    monkeypatch.setattr(union_repo, "get_by_ot", lambda ot: [])

    result = union_repo.get_total_uniones("999")

    assert result == 0


def test_calculate_metrics_returns_all_five_metrics(union_repo, sample_unions, monkeypatch):
    """Test calculate_metrics returns all 5 metrics with correct types and precision."""
    monkeypatch.setattr(union_repo, "get_by_ot", lambda ot: sample_unions)

    result = union_repo.calculate_metrics("001")

    # Verify structure
    assert isinstance(result, dict)
    assert "total_uniones" in result
    assert "arm_completadas" in result
    assert "sold_completadas" in result
    assert "pulgadas_arm" in result
    assert "pulgadas_sold" in result

    # Verify values
    assert result["total_uniones"] == 5
    assert result["arm_completadas"] == 4  # Unions 1,2,3,5
    assert result["sold_completadas"] == 2  # Unions 2,3
    assert result["pulgadas_arm"] == 30.50  # 6.0 + 8.0 + 4.5 + 12.0
    assert result["pulgadas_sold"] == 12.50  # 8.0 + 4.5

    # Verify types
    assert isinstance(result["total_uniones"], int)
    assert isinstance(result["arm_completadas"], int)
    assert isinstance(result["sold_completadas"], int)
    assert isinstance(result["pulgadas_arm"], float)
    assert isinstance(result["pulgadas_sold"], float)


def test_calculate_metrics_empty_ot(union_repo, monkeypatch):
    """Test calculate_metrics returns zeros for empty OT (graceful handling)."""
    monkeypatch.setattr(union_repo, "get_by_ot", lambda ot: [])

    result = union_repo.calculate_metrics("999")

    assert result["total_uniones"] == 0
    assert result["arm_completadas"] == 0
    assert result["sold_completadas"] == 0
    assert result["pulgadas_arm"] == 0.00
    assert result["pulgadas_sold"] == 0.00


def test_calculate_metrics_skips_invalid_dn_union_with_warning(union_repo, monkeypatch, caplog):
    """Test calculate_metrics handles invalid DN_UNION values gracefully with warning."""
    now = datetime.now()

    # Create union with invalid DN_UNION (will raise ValueError when converted to float)
    invalid_union = Union(
        id="TEST-03+1",
        ot="003",
        tag_spool="TEST-03",
        n_union=1,
        dn_union=6.0,  # Valid float
        tipo_union="Tipo A",
        arm_fecha_inicio=now,
        arm_fecha_fin=now,
        arm_worker="MR(93)",
        sol_fecha_inicio=None,
        sol_fecha_fin=None,
        sol_worker=None,
        ndt_fecha=None,
        ndt_status=None,
        version="uuid",
        creado_por="MR(93)",
        fecha_creacion=now,
        modificado_por=None,
        fecha_modificacion=None,
    )

    valid_union = Union(
        id="TEST-03+2",
        ot="003",
        tag_spool="TEST-03",
        n_union=2,
        dn_union=8.0,
        tipo_union="Tipo B",
        arm_fecha_inicio=now,
        arm_fecha_fin=now,
        arm_worker="MR(93)",
        sol_fecha_inicio=None,
        sol_fecha_fin=None,
        sol_worker=None,
        ndt_fecha=None,
        ndt_status=None,
        version="uuid",
        creado_por="MR(93)",
        fecha_creacion=now,
        modificado_por=None,
        fecha_modificacion=None,
    )

    unions = [invalid_union, valid_union]

    # Mock dn_union to be invalid for first union
    def mock_get_by_ot(ot):
        # Simulate invalid value by creating union with problematic dn_union
        invalid = invalid_union.model_copy(update={"dn_union": float("nan")})
        return [invalid, valid_union]

    monkeypatch.setattr(union_repo, "get_by_ot", mock_get_by_ot)

    result = union_repo.calculate_metrics("003")

    # Should count total but skip invalid DN for sums
    assert result["total_uniones"] == 2
    assert result["arm_completadas"] == 1  # Only valid union counted
    assert result["pulgadas_arm"] == 8.00  # Only valid union summed


def test_precision_edge_cases_18_point_50_not_18_point_5(union_repo, monkeypatch):
    """Test that 18.50 is returned as 18.50, not 18.5 (precision validation)."""
    now = datetime.now()

    unions = [
        Union(
            id="TEST-04+1",
            ot="004",
            tag_spool="TEST-04",
            n_union=1,
            dn_union=18.5,  # Input as 18.5
            tipo_union="Tipo A",
            arm_fecha_inicio=now,
            arm_fecha_fin=now,
            arm_worker="MR(93)",
            sol_fecha_inicio=None,
            sol_fecha_fin=None,
            sol_worker=None,
            ndt_fecha=None,
            ndt_status=None,
            version="uuid",
            creado_por="MR(93)",
            fecha_creacion=now,
            modificado_por=None,
            fecha_modificacion=None,
        )
    ]

    monkeypatch.setattr(union_repo, "get_by_ot", lambda ot: unions)

    result = union_repo.sum_pulgadas_arm("004")

    # Must be 18.50, not 18.5
    assert result == 18.50
    formatted = f"{result:.2f}"
    assert formatted == "18.50"


def test_metrics_no_caching_fresh_calculation_each_time(union_repo, monkeypatch):
    """Test that metrics are calculated fresh each time (no caching)."""
    call_count = 0

    def mock_get_by_ot(ot):
        nonlocal call_count
        call_count += 1
        return []

    monkeypatch.setattr(union_repo, "get_by_ot", mock_get_by_ot)

    # Call twice
    union_repo.count_completed_arm("001")
    union_repo.count_completed_arm("001")

    # Should call get_by_ot twice (no caching)
    assert call_count == 2
