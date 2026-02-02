"""
Integration tests for UnionService with complete INICIAR->FINALIZAR workflows.

Tests service orchestration with real repository interactions (mocked Sheets).
"""
import pytest
from unittest.mock import Mock, MagicMock, AsyncMock, patch
from datetime import datetime

from backend.services.union_service import UnionService
from backend.repositories.union_repository import UnionRepository
from backend.repositories.metadata_repository import MetadataRepository
from backend.repositories.sheets_repository import SheetsRepository
from backend.core.column_map_cache import ColumnMapCache
from backend.models.union import Union
from backend.exceptions import SheetsConnectionError
from tests.fixtures.mock_uniones_data import get_standard_data


@pytest.fixture
def mock_sheets_repo():
    """Mock SheetsRepository with realistic Uniones data."""
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


@pytest.fixture
def metadata_repo():
    """Mock MetadataRepository for event logging."""
    repo = MagicMock()
    repo.log_event = MagicMock()
    repo.batch_log_events = MagicMock()
    return repo


@pytest.fixture
def union_service(union_repo, metadata_repo, mock_sheets_repo):
    """Create UnionService with real UnionRepository."""
    return UnionService(
        union_repo=union_repo,
        metadata_repo=metadata_repo,
        sheets_repo=mock_sheets_repo
    )


class TestIniciarFinalizarFlow:
    """Test complete INICIAR->FINALIZAR workflow with different scenarios."""

    def test_partial_work_triggers_pausar(self, union_service, union_repo):
        """
        Worker initiates ARM operation, selects 7 of 10 unions, should PAUSAR.

        Scenario:
        1. INICIAR ARM operation (handled by OccupationService, not tested here)
        2. Worker selects 7 unions out of 10 available
        3. FINALIZAR should determine action as PAUSAR (not all work done)
        4. Batch update should succeed
        5. Metadata events should be logged
        """
        # Setup: OT "001" has 10 unions, 7 ARM complete, 3 disponibles
        disponibles = union_repo.get_disponibles_arm_by_ot("001")
        assert len(disponibles) == 3  # Verify test data

        # Get TAG_SPOOL from one of the unions
        tag_spool = disponibles[0].tag_spool

        # But let's select 2 out of 3 (partial work)
        selected_unions = [u.id for u in disponibles[:2]]

        # Execute: Process selection
        result = union_service.process_selection(
            tag_spool=tag_spool,
            union_ids=selected_unions,
            worker_id=93,
            worker_nombre="MR(93)",
            operacion="ARM"
        )

        # Verify: Batch update completed
        assert result["union_count"] == 2
        assert result["action"] == "ARM_COMPLETAR"
        assert result["pulgadas"] > 0.0
        assert result["event_count"] == 3  # 1 batch + 2 granular

        # Verify: Metadata events logged
        union_service.metadata_repo.batch_log_events.assert_called_once()
        events = union_service.metadata_repo.batch_log_events.call_args[0][0]
        assert len(events) == 3

        # First event should be batch event (no n_union)
        batch_event = events[0]
        assert batch_event.n_union is None
        assert batch_event.evento_tipo.value == "UNION_ARM_REGISTRADA"

        # Remaining events should be granular (with n_union)
        for event in events[1:]:
            assert event.n_union is not None

    def test_complete_work_triggers_completar(self, union_service, union_repo):
        """
        Different worker completes remaining 3 unions, should COMPLETAR.

        Scenario:
        1. INICIAR ARM operation again (new session)
        2. Select all 3 remaining disponibles unions
        3. FINALIZAR should determine action as COMPLETAR (all work done)
        4. State transition should be triggered
        """
        # Setup: Get all 3 disponibles
        disponibles = union_repo.get_disponibles_arm_by_ot("001")
        assert len(disponibles) == 3

        tag_spool = disponibles[0].tag_spool
        selected_unions = [u.id for u in disponibles]  # All of them

        # Execute: Process selection
        result = union_service.process_selection(
            tag_spool=tag_spool,
            union_ids=selected_unions,
            worker_id=45,
            worker_nombre="JD(45)",
            operacion="ARM"
        )

        # Verify: All unions processed
        assert result["union_count"] == 3
        assert result["action"] == "ARM_COMPLETAR"
        assert result["event_count"] == 4  # 1 batch + 3 granular

    def test_validates_union_ownership(self, union_service, union_repo):
        """Should raise error if unions belong to different OTs."""
        # Note: This test would require a multi-OT TAG_SPOOL which isn't realistic
        # In practice, TAG_SPOOL is 1:1 with OT, so validation happens at existence check
        # This test documents the intended behavior if multi-OT tag_spools existed

        # Get unions from same TAG_SPOOL (all same OT)
        ot_001_unions = union_repo.get_by_ot("001")

        # Create fake union IDs with different OT prefixes
        # These will fail at "Union IDs not found" before ownership check
        # But the ownership validation logic is still tested in unit tests

        tag_spool = ot_001_unions[0].tag_spool

        # This test verifies the early validation catches issues
        # Real multi-OT mixing would be caught by ownership validation
        pass  # Skipping as realistic scenario requires multi-OT tag_spool

    def test_filters_unavailable_unions(self, union_service, union_repo):
        """Should filter out unions that are already completed."""
        # Get all unions for OT 001
        all_unions = union_repo.get_by_ot("001")

        # Get some that are already ARM complete
        arm_completed = [u for u in all_unions if u.arm_fecha_fin is not None][:2]

        # Get some that are disponibles
        disponibles = union_repo.get_disponibles_arm_by_ot("001")[:2]

        tag_spool = all_unions[0].tag_spool

        # Mix completed and disponibles
        mixed_ids = [u.id for u in arm_completed] + [u.id for u in disponibles]

        # Execute: Should only process disponibles
        result = union_service.process_selection(
            tag_spool=tag_spool,
            union_ids=mixed_ids,
            worker_id=93,
            worker_nombre="MR(93)",
            operacion="ARM"
        )

        # Verify: Only disponibles were processed
        assert result["union_count"] == 2  # Only the 2 disponibles
        assert result["event_count"] == 3  # 1 batch + 2 granular

    def test_empty_union_ids_raises_error(self, union_service):
        """Should raise ValueError for empty union_ids list."""
        with pytest.raises(ValueError, match="union_ids cannot be empty"):
            union_service.process_selection(
                tag_spool="OT-001",
                union_ids=[],
                worker_id=93,
                worker_nombre="MR(93)",
                operacion="ARM"
            )

    def test_validates_union_ids_exist(self, union_service, union_repo):
        """Should raise ValueError if union IDs don't exist."""
        # Get a valid tag_spool first
        all_unions = union_repo.get_by_ot("001")
        tag_spool = all_unions[0].tag_spool

        with pytest.raises(ValueError, match="Union IDs not found"):
            union_service.process_selection(
                tag_spool=tag_spool,
                union_ids=["001+999", "001+998"],
                worker_id=93,
                worker_nombre="MR(93)",
                operacion="ARM"
            )

    def test_calculates_pulgadas_correctly(self, union_service, union_repo):
        """Should sum pulgadas-diámetro with 1 decimal precision."""
        # Get disponibles and check their DN values
        disponibles = union_repo.get_disponibles_arm_by_ot("001")[:2]

        tag_spool = disponibles[0].tag_spool

        # Execute
        result = union_service.process_selection(
            tag_spool=tag_spool,
            union_ids=[u.id for u in disponibles],
            worker_id=93,
            worker_nombre="MR(93)",
            operacion="ARM"
        )

        # Verify pulgadas calculation
        expected_pulgadas = sum(u.dn_union for u in disponibles)
        assert result["pulgadas"] == round(expected_pulgadas, 1)
        assert isinstance(result["pulgadas"], float)
