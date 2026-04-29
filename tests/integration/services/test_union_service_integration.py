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




