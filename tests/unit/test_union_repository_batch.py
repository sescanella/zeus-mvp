"""
Unit tests for UnionRepository batch update operations.

Tests batch_update_arm and batch_update_sold methods that use
gspread.batch_update() for performance optimization.
"""
import pytest
from unittest.mock import Mock, MagicMock, patch
from datetime import datetime

from backend.repositories.union_repository import UnionRepository
from backend.exceptions import SheetsConnectionError
from backend.utils.date_formatter import now_chile


@pytest.fixture
def mock_sheets_repo():
    """Create mock SheetsRepository for testing."""
    mock = Mock()

    # Default header row for Uniones sheet (with TAG_SPOOL and ID)
    header = [
        "ID",                    # col 0
        "OT",                    # col 1
        "TAG_SPOOL",            # col 2
        "N_UNION",              # col 3
        "DN_UNION",             # col 4
        "TIPO_UNION",           # col 5
        "ARM_FECHA_INICIO",     # col 6
        "ARM_FECHA_FIN",        # col 7
        "ARM_WORKER",           # col 8
        "SOL_FECHA_INICIO",     # col 9
        "SOL_FECHA_FIN",        # col 10
        "SOL_WORKER",           # col 11
        "NDT_FECHA",            # col 12
        "NDT_STATUS",           # col 13
        "version",              # col 14
        "Creado_Por",           # col 15
        "Fecha_Creacion",       # col 16
        "Modificado_Por",       # col 17
        "Fecha_Modificacion"    # col 18
    ]

    # Mock data rows
    data_rows = [
        header,
        # Row 2: OT-123+1, ARM not completed
        ["OT-123+1", "001", "OT-123", "1", "6.0", "Tipo A", "", "", "", "", "", "", "", "", "uuid1", "MR(93)", "01-02-2026 10:00:00", "", ""],
        # Row 3: OT-123+2, ARM not completed
        ["OT-123+2", "001", "OT-123", "2", "4.0", "Tipo B", "", "", "", "", "", "", "", "", "uuid2", "MR(93)", "01-02-2026 10:00:00", "", ""],
        # Row 4: OT-123+5, ARM not completed
        ["OT-123+5", "001", "OT-123", "5", "8.0", "Tipo A", "", "", "", "", "", "", "", "", "uuid3", "MR(93)", "01-02-2026 10:00:00", "", ""],
        # Row 5: OT-123+3, ARM already completed
        ["OT-123+3", "001", "OT-123", "3", "6.0", "Tipo C", "01-02-2026 11:00:00", "01-02-2026 12:00:00", "MR(93)", "", "", "", "", "", "uuid4", "MR(93)", "01-02-2026 10:00:00", "", ""],
        # Row 6: OT-456+1, different spool
        ["OT-456+1", "002", "OT-456", "1", "6.0", "Tipo A", "", "", "", "", "", "", "", "", "uuid5", "JP(94)", "01-02-2026 10:00:00", "", ""],
    ]

    mock.read_worksheet.return_value = data_rows

    # Mock worksheet for batch_update
    mock_worksheet = Mock()
    mock_worksheet.batch_update = Mock()
    mock._get_worksheet = Mock(return_value=mock_worksheet)

    return mock


@pytest.fixture
def union_repo(mock_sheets_repo):
    """Create UnionRepository with mocked dependencies."""
    return UnionRepository(sheets_repo=mock_sheets_repo)


class TestBatchUpdateArm:
    """Tests for batch_update_arm method."""





    def test_batch_update_arm_empty_union_ids(self, union_repo, mock_sheets_repo):
        """Test batch update with empty union_ids returns 0."""
        timestamp = now_chile()
        count = union_repo.batch_update_arm(
            tag_spool="OT-123",
            union_ids=[],
            worker="MR(93)",
            timestamp=timestamp
        )

        assert count == 0
        # Verify batch_update NOT called
        mock_worksheet = mock_sheets_repo._get_worksheet.return_value
        mock_worksheet.batch_update.assert_not_called()

    def test_batch_update_arm_nonexistent_unions(self, union_repo, mock_sheets_repo):
        """Test batch update with unions that don't exist returns 0."""
        with patch('backend.core.column_map_cache.ColumnMapCache.get_or_build') as mock_cache:
            mock_cache.return_value = {
                "id": 0,
                "ot": 1,
                "tagspool": 2,
                "nunion": 3,
                "dnunion": 4,
                "tipounion": 5,
                "armfechainicio": 6,
                "armfechafin": 7,
                "armworker": 8,
            }

            timestamp = now_chile()
            count = union_repo.batch_update_arm(
                tag_spool="OT-123",
                union_ids=["NONEXISTENT+1", "NONEXISTENT+2"],
                worker="MR(93)",
                timestamp=timestamp
            )

            assert count == 0
            mock_worksheet = mock_sheets_repo._get_worksheet.return_value
            mock_worksheet.batch_update.assert_not_called()




class TestBatchUpdateSold:
    """Tests for batch_update_sold method."""


    def test_batch_update_sold_requires_arm_completion(self, mock_sheets_repo):
        """Test that SOLD update requires ARM completion (validation)."""
        # Setup mock data with ARM NOT complete
        header = mock_sheets_repo.read_worksheet.return_value[0]
        data_rows = [
            header,
            # Row 2: ARM NOT complete
            ["OT-123+1", "001", "OT-123", "1", "6.0", "Tipo A", "", "", "", "", "", "", "", "", "uuid1", "MR(93)", "01-02-2026 10:00:00", "", ""],
        ]
        mock_sheets_repo.read_worksheet.return_value = data_rows

        union_repo = UnionRepository(sheets_repo=mock_sheets_repo)

        with patch('backend.core.column_map_cache.ColumnMapCache.get_or_build') as mock_cache:
            mock_cache.return_value = {
                "id": 0,
                "ot": 1,
                "tagspool": 2,
                "nunion": 3,
                "dnunion": 4,
                "tipounion": 5,
                "armfechainicio": 6,
                "armfechafin": 7,
                "armworker": 8,
                "solfechainicio": 9,
                "solfechafin": 10,
                "solworker": 11,
            }

            timestamp = now_chile()
            count = union_repo.batch_update_sold(
                tag_spool="OT-123",
                union_ids=["OT-123+1"],
                worker="MG(95)",
                timestamp=timestamp
            )

            # No updates (ARM prerequisite not met)
            assert count == 0
            mock_worksheet = mock_sheets_repo._get_worksheet.return_value
            mock_worksheet.batch_update.assert_not_called()




class TestBatchUpdateRetry:
    """Tests for retry behavior on API errors."""

