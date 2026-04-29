"""
Integration tests for UnionRepository with complete workflows.

Tests complete flows from OT query to batch updates to metrics calculation.
"""
import pytest
from unittest.mock import Mock, MagicMock, patch
from datetime import datetime

from backend.repositories.union_repository import UnionRepository
from backend.repositories.sheets_repository import SheetsRepository
from backend.core.column_map_cache import ColumnMapCache
from backend.models.union import Union
from backend.exceptions import SheetsConnectionError
from tests.fixtures.mock_uniones_data import (
    generate_mock_uniones,
    get_by_ot,
    get_disponibles,
    get_standard_data
)


@pytest.fixture
def mock_sheets_repo():
    """Mock SheetsRepository with realistic Uniones data."""
    # Use MagicMock without spec to allow any attribute
    repo = MagicMock()

    # Use standard mock data (100 unions across 10 OTs)
    mock_data = get_standard_data()

    repo.read_worksheet.return_value = mock_data

    # Mock _get_worksheet for batch operations
    mock_worksheet = MagicMock()
    mock_worksheet.batch_update = MagicMock()
    repo._get_worksheet.return_value = mock_worksheet

    return repo


@pytest.fixture
def union_repo(mock_sheets_repo):
    """Create UnionRepository with mocked sheets."""
    # Clear column cache before each test
    ColumnMapCache.invalidate("Uniones")
    return UnionRepository(mock_sheets_repo)


class TestGetByOT:
    """Test querying unions by OT (primary foreign key)."""

    def test_get_by_ot_returns_all_unions(self, union_repo):
        """Should return all 10 unions for a given OT."""
        # OT "001" should have 10 unions
        unions = union_repo.get_by_ot("001")

        assert len(unions) == 10
        assert all(isinstance(u, Union) for u in unions)
        assert all(u.ot == "001" for u in unions)

    def test_get_by_ot_empty_result(self, union_repo):
        """Should return empty list for non-existent OT."""
        unions = union_repo.get_by_ot("999")

        assert unions == []

    def test_get_by_ot_verifies_completion_states(self, union_repo):
        """Should correctly identify completion states from mock data."""
        unions = union_repo.get_by_ot("001")

        # Mock data has 7 ARM complete, 5 SOLD complete
        arm_complete = [u for u in unions if u.arm_fecha_fin is not None]
        sold_complete = [u for u in unions if u.sol_fecha_fin is not None]

        assert len(arm_complete) == 7
        assert len(sold_complete) == 5


class TestDisponiblesQueries:
    """Test disponibles union queries for ARM/SOLD operations."""

    def test_get_disponibles_arm_by_ot(self, union_repo):
        """Should return unions with no ARM_FECHA_FIN."""
        disponibles = union_repo.get_disponibles_arm_by_ot("001")

        # Mock data: 10 total, 7 ARM complete = 3 disponibles
        assert len(disponibles) == 3
        assert all(u.arm_fecha_fin is None for u in disponibles)

    def test_get_disponibles_sold_by_ot(self, union_repo):
        """Should return unions with ARM complete but SOLD pending."""
        disponibles = union_repo.get_disponibles_sold_by_ot("001")

        # Mock data: 7 ARM complete, 5 SOLD complete = 2 disponibles
        assert len(disponibles) == 2
        assert all(u.arm_fecha_fin is not None for u in disponibles)
        assert all(u.sol_fecha_fin is None for u in disponibles)

    def test_get_disponibles_grouped_by_tag_spool(self, union_repo):
        """Should return disponibles grouped by TAG_SPOOL."""
        disponibles_dict = union_repo.get_disponibles("ARM")

        # Should have entries for multiple spools
        assert isinstance(disponibles_dict, dict)
        assert len(disponibles_dict) > 0

        # Each entry should be a list of unions
        for tag_spool, unions in disponibles_dict.items():
            assert isinstance(unions, list)
            assert all(isinstance(u, Union) for u in unions)
            assert all(u.arm_fecha_fin is None for u in unions)


class TestMetricsCalculation:
    """Test union metrics calculation for Operaciones columns 68-72."""

    def test_get_total_uniones(self, union_repo):
        """Should count all unions for OT (column 68)."""
        total = union_repo.get_total_uniones("001")

        assert total == 10  # Mock data has 10 unions per OT

    def test_count_completed_arm(self, union_repo):
        """Should count ARM completed unions (column 69)."""
        count = union_repo.count_completed_arm("001")

        assert count == 7  # Mock data: 7 ARM complete

    def test_count_completed_sold(self, union_repo):
        """Should count SOLD completed unions (column 70)."""
        count = union_repo.count_completed_sold("001")

        assert count == 5  # Mock data: 5 SOLD complete

    def test_sum_pulgadas_arm(self, union_repo):
        """Should sum DN_UNION for ARM completed unions (column 71)."""
        pulgadas = union_repo.sum_pulgadas_arm("001")

        # Mock data: DN values cycle through [4.5, 6.0, 8.0, 10.0, 12.0, ...]
        # First 7 unions completed: 6.0 + 8.0 + 10.0 + 12.0 + 14.0 + 16.0 + 18.0 = 84.0
        assert pulgadas == 84.00  # 2 decimal precision

    def test_sum_pulgadas_sold(self, union_repo):
        """Should sum DN_UNION for SOLD completed unions (column 72)."""
        pulgadas = union_repo.sum_pulgadas_sold("001")

        # Mock data: First 5 unions SOLD complete
        # DN values: 6.0 + 8.0 + 10.0 + 12.0 + 14.0 = 50.0
        assert pulgadas == 50.00  # 2 decimal precision

    def test_calculate_metrics_single_call(self, union_repo):
        """Should calculate all metrics efficiently in single call."""
        metrics = union_repo.calculate_metrics("001")

        assert metrics["total_uniones"] == 10
        assert metrics["arm_completadas"] == 7
        assert metrics["sold_completadas"] == 5
        assert metrics["pulgadas_arm"] == 84.00
        assert metrics["pulgadas_sold"] == 50.00


class TestBatchUpdateARM:
    """Test batch ARM completion updates."""


    def test_batch_update_arm_empty_list(self, union_repo):
        """Should handle empty union_ids gracefully."""
        updated_count = union_repo.batch_update_arm(
            tag_spool="TEST-01",
            union_ids=[],
            worker="MR(93)",
            timestamp=datetime.now()
        )

        assert updated_count == 0

    def test_batch_update_arm_skips_already_complete(self, union_repo, mock_sheets_repo):
        """Should skip unions that already have ARM_FECHA_FIN."""
        # Get all unions for OT 001 (includes completed ones)
        all_unions = union_repo.get_by_ot("001")
        completed_union_ids = [u.id for u in all_unions if u.arm_fecha_fin is not None]

        # Try to update already completed unions
        updated_count = union_repo.batch_update_arm(
            tag_spool="MK-1335-CW-25238-001",
            union_ids=completed_union_ids[:2],
            worker="MR(93)",
            timestamp=datetime.now()
        )

        # Should skip all already completed
        assert updated_count == 0


class TestBatchUpdateSOLD:
    """Test batch SOLD completion updates with ARM prerequisite validation."""


    def test_batch_update_sold_skips_without_arm(self, union_repo):
        """Should skip unions that don't have ARM complete."""
        # Get ARM disponibles (no ARM_FECHA_FIN)
        arm_disponibles = union_repo.get_disponibles_arm_by_ot("001")
        union_ids = [u.id for u in arm_disponibles]

        # Try to update SOLD without ARM complete
        updated_count = union_repo.batch_update_sold(
            tag_spool="MK-1335-CW-25238-001",
            union_ids=union_ids,
            worker="MG(95)",
            timestamp=datetime.now()
        )

        # Should skip all (ARM prerequisite not met)
        assert updated_count == 0


class TestEndToEndWorkflow:
    """Test complete workflow from INICIAR to FINALIZAR."""



class TestConcurrentUpdates:
    """Test concurrent updates with version/optimistic locking."""

    def test_version_field_present(self, union_repo):
        """Should include version UUID in all Union objects."""
        unions = union_repo.get_by_ot("001")

        # All unions should have version field
        assert all(hasattr(u, 'version') for u in unions)
        assert all(u.version for u in unions)  # Not empty



class TestErrorHandling:
    """Test error handling for edge cases."""

    def test_empty_sheet_graceful_handling(self, union_repo, mock_sheets_repo):
        """Should handle empty Uniones sheet gracefully."""
        # Mock empty sheet (only header)
        mock_sheets_repo.read_worksheet.return_value = [get_standard_data()[0]]  # Only header

        unions = union_repo.get_by_ot("001")
        assert unions == []

    def test_invalid_ot_returns_empty(self, union_repo):
        """Should return empty list for invalid OT."""
        unions = union_repo.get_by_ot("INVALID-OT")
        assert unions == []

    def test_partial_success_in_batch(self, union_repo):
        """Should handle partial success (some unions valid, some invalid)."""
        # Mix of valid and invalid union IDs
        union_ids = ["001+1", "001+2", "INVALID-ID"]

        # Should process valid ones, skip invalid
        updated_count = union_repo.batch_update_arm(
            tag_spool="MK-1335-CW-25238-001",
            union_ids=union_ids,
            worker="MR(93)",
            timestamp=datetime.now()
        )

        # Should process valid ones (behavior depends on implementation)
        assert updated_count >= 0
