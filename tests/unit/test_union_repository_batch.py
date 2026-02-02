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

    def test_batch_update_arm_single_union(self, union_repo, mock_sheets_repo):
        """Test batch update for a single ARM union."""
        with patch('backend.core.column_map_cache.ColumnMapCache.get_or_build') as mock_cache:
            # Setup column map
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
                union_ids=["OT-123+1"],
                worker="MR(93)",
                timestamp=timestamp
            )

            assert count == 1
            # Verify batch_update was called once
            mock_worksheet = mock_sheets_repo._get_worksheet.return_value
            mock_worksheet.batch_update.assert_called_once()

            # Verify batch_data has 2 ranges (ARM_FECHA_FIN + ARM_WORKER)
            call_args = mock_worksheet.batch_update.call_args
            batch_data = call_args[0][0]
            assert len(batch_data) == 2

    def test_batch_update_arm_multiple_unions(self, union_repo, mock_sheets_repo):
        """Test batch update for multiple ARM unions (5 unions)."""
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
                union_ids=["OT-123+1", "OT-123+2", "OT-123+5"],
                worker="MR(93)",
                timestamp=timestamp
            )

            assert count == 3
            mock_worksheet = mock_sheets_repo._get_worksheet.return_value
            mock_worksheet.batch_update.assert_called_once()

            # Verify single API call with 6 ranges (3 unions × 2 fields)
            call_args = mock_worksheet.batch_update.call_args
            batch_data = call_args[0][0]
            assert len(batch_data) == 6

    def test_batch_update_arm_10_unions_performance(self, union_repo, mock_sheets_repo):
        """Test batch update for 10 unions confirms single API call."""
        # Create mock data with 10 ARM-incomplete unions
        header = mock_sheets_repo.read_worksheet.return_value[0]
        data_rows = [header]

        for i in range(1, 11):
            union_id = f"OT-999+{i}"
            data_rows.append([
                union_id, "003", "OT-999", str(i), "6.0", "Tipo A",
                "", "", "", "", "", "", "", "", f"uuid{i}", "MR(93)",
                "01-02-2026 10:00:00", "", ""
            ])

        mock_sheets_repo.read_worksheet.return_value = data_rows

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

            union_ids = [f"OT-999+{i}" for i in range(1, 11)]
            timestamp = now_chile()
            count = union_repo.batch_update_arm(
                tag_spool="OT-999",
                union_ids=union_ids,
                worker="MR(93)",
                timestamp=timestamp
            )

            assert count == 10
            # CRITICAL: Verify batch_update called exactly ONCE, not 10 times
            mock_worksheet = mock_sheets_repo._get_worksheet.return_value
            assert mock_worksheet.batch_update.call_count == 1

            # Verify 20 ranges (10 unions × 2 fields)
            call_args = mock_worksheet.batch_update.call_args
            batch_data = call_args[0][0]
            assert len(batch_data) == 20

    def test_batch_update_arm_skips_already_completed(self, union_repo, mock_sheets_repo):
        """Test that already-completed ARM unions are skipped."""
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
                union_ids=["OT-123+1", "OT-123+3"],  # OT-123+3 already ARM-completed
                worker="MR(93)",
                timestamp=timestamp
            )

            # Only 1 union updated (OT-123+3 skipped)
            assert count == 1
            mock_worksheet = mock_sheets_repo._get_worksheet.return_value
            call_args = mock_worksheet.batch_update.call_args
            batch_data = call_args[0][0]
            assert len(batch_data) == 2  # 1 union × 2 fields

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

    def test_batch_update_arm_a1_notation_correct(self, union_repo, mock_sheets_repo):
        """Test that A1 notation ranges are correctly generated."""
        with patch('backend.core.column_map_cache.ColumnMapCache.get_or_build') as mock_cache:
            mock_cache.return_value = {
                "id": 0,
                "ot": 1,
                "tagspool": 2,
                "nunion": 3,
                "dnunion": 4,
                "tipounion": 5,
                "armfechainicio": 6,
                "armfechafin": 7,  # Column H (index 7)
                "armworker": 8,    # Column I (index 8)
            }

            timestamp = now_chile()
            count = union_repo.batch_update_arm(
                tag_spool="OT-123",
                union_ids=["OT-123+1"],  # Row 2
                worker="MR(93)",
                timestamp=timestamp
            )

            assert count == 1
            mock_worksheet = mock_sheets_repo._get_worksheet.return_value
            call_args = mock_worksheet.batch_update.call_args
            batch_data = call_args[0][0]

            # Verify A1 notation: H2 for ARM_FECHA_FIN, I2 for ARM_WORKER
            ranges = [item['range'] for item in batch_data]
            assert 'H2' in ranges
            assert 'I2' in ranges

    def test_batch_update_arm_cache_invalidation(self, union_repo, mock_sheets_repo):
        """Test that cache is invalidated after batch update."""
        with patch('backend.core.column_map_cache.ColumnMapCache.get_or_build') as mock_cache, \
             patch('backend.core.column_map_cache.ColumnMapCache.invalidate') as mock_invalidate:

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
                union_ids=["OT-123+1"],
                worker="MR(93)",
                timestamp=timestamp
            )

            assert count == 1
            # Verify cache invalidation called
            mock_invalidate.assert_called_once_with("Uniones")


class TestBatchUpdateSold:
    """Tests for batch_update_sold method."""

    def test_batch_update_sold_with_arm_complete(self, mock_sheets_repo):
        """Test batch update SOLD when ARM is complete."""
        # Setup mock data with ARM-completed unions
        header = mock_sheets_repo.read_worksheet.return_value[0]
        data_rows = [
            header,
            # Row 2: ARM complete, SOLD not complete
            ["OT-123+1", "001", "OT-123", "1", "6.0", "Tipo A", "01-02-2026 10:00:00", "01-02-2026 11:00:00", "MR(93)", "", "", "", "", "", "uuid1", "MR(93)", "01-02-2026 10:00:00", "", ""],
            # Row 3: ARM complete, SOLD not complete
            ["OT-123+2", "001", "OT-123", "2", "4.0", "Tipo B", "01-02-2026 10:00:00", "01-02-2026 11:00:00", "MR(93)", "", "", "", "", "", "uuid2", "MR(93)", "01-02-2026 10:00:00", "", ""],
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
                union_ids=["OT-123+1", "OT-123+2"],
                worker="MG(95)",
                timestamp=timestamp
            )

            assert count == 2
            mock_worksheet = mock_sheets_repo._get_worksheet.return_value
            mock_worksheet.batch_update.assert_called_once()

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

    def test_batch_update_sold_skips_already_completed(self, mock_sheets_repo):
        """Test that already-completed SOLD unions are skipped."""
        # Setup mock data with SOLD already complete
        header = mock_sheets_repo.read_worksheet.return_value[0]
        data_rows = [
            header,
            # Row 2: ARM complete, SOLD complete
            ["OT-123+1", "001", "OT-123", "1", "6.0", "Tipo A", "01-02-2026 10:00:00", "01-02-2026 11:00:00", "MR(93)", "01-02-2026 12:00:00", "01-02-2026 13:00:00", "MG(95)", "", "", "uuid1", "MR(93)", "01-02-2026 10:00:00", "", ""],
            # Row 3: ARM complete, SOLD NOT complete
            ["OT-123+2", "001", "OT-123", "2", "4.0", "Tipo B", "01-02-2026 10:00:00", "01-02-2026 11:00:00", "MR(93)", "", "", "", "", "", "uuid2", "MR(93)", "01-02-2026 10:00:00", "", ""],
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
                union_ids=["OT-123+1", "OT-123+2"],
                worker="MG(95)",
                timestamp=timestamp
            )

            # Only OT-123+2 updated (OT-123+1 already SOLD-complete)
            assert count == 1
            mock_worksheet = mock_sheets_repo._get_worksheet.return_value
            call_args = mock_worksheet.batch_update.call_args
            batch_data = call_args[0][0]
            assert len(batch_data) == 2  # 1 union × 2 fields

    def test_batch_update_sold_idempotency(self, mock_sheets_repo):
        """Test that calling batch_update_sold twice is safe (idempotent)."""
        # Setup mock data
        header = mock_sheets_repo.read_worksheet.return_value[0]
        data_rows = [
            header,
            ["OT-123+1", "001", "OT-123", "1", "6.0", "Tipo A", "01-02-2026 10:00:00", "01-02-2026 11:00:00", "MR(93)", "", "", "", "", "", "uuid1", "MR(93)", "01-02-2026 10:00:00", "", ""],
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

            # First call
            count1 = union_repo.batch_update_sold(
                tag_spool="OT-123",
                union_ids=["OT-123+1"],
                worker="MG(95)",
                timestamp=timestamp
            )
            assert count1 == 1

            # Simulate SOLD now complete (update mock data)
            data_rows[1][10] = "01-02-2026 14:00:00"  # SOL_FECHA_FIN
            data_rows[1][11] = "MG(95)"  # SOL_WORKER
            mock_sheets_repo.read_worksheet.return_value = data_rows

            # Second call (should skip, already complete)
            count2 = union_repo.batch_update_sold(
                tag_spool="OT-123",
                union_ids=["OT-123+1"],
                worker="MG(95)",
                timestamp=timestamp
            )
            assert count2 == 0  # No updates (already complete)


class TestBatchUpdateRetry:
    """Tests for retry behavior on API errors."""

    def test_batch_update_arm_retries_on_429(self, mock_sheets_repo):
        """Test that batch_update retries on 429 rate limit errors."""
        union_repo = UnionRepository(sheets_repo=mock_sheets_repo)

        # Setup mock to fail twice, then succeed
        mock_worksheet = mock_sheets_repo._get_worksheet.return_value

        # Create proper APIError mock with response object
        import gspread
        from unittest.mock import Mock

        def create_api_error():
            mock_response = Mock()
            mock_response.json.return_value = {"error": {"code": 429, "message": "Rate limit exceeded"}}
            mock_response.text = "Rate limit exceeded"
            mock_response.status_code = 429
            return gspread.exceptions.APIError(mock_response)

        mock_worksheet.batch_update.side_effect = [
            create_api_error(),
            create_api_error(),
            None  # Third call succeeds
        ]

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
                union_ids=["OT-123+1"],
                worker="MR(93)",
                timestamp=timestamp
            )

            # Should succeed after 2 retries
            assert count == 1
            assert mock_worksheet.batch_update.call_count == 3
