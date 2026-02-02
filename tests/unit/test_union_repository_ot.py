"""
Unit tests for UnionRepository OT-based query methods.

v4.0: Tests for get_by_ot, get_disponibles_arm_by_ot, and get_disponibles_sold_by_ot.
"""
import pytest
from unittest.mock import Mock, MagicMock
from datetime import datetime

from backend.repositories.union_repository import UnionRepository
from backend.models.union import Union
from backend.exceptions import SheetsConnectionError


@pytest.fixture
def mock_sheets_repo():
    """Create mock SheetsRepository for testing."""
    mock_repo = Mock()
    return mock_repo


@pytest.fixture
def union_repository(mock_sheets_repo):
    """Create UnionRepository with mocked dependencies."""
    return UnionRepository(sheets_repo=mock_sheets_repo)


@pytest.fixture
def sample_uniones_data():
    """
    Sample Uniones sheet data with OT column in position 1 (Column B).

    Columns: ID_UNION, OT, N_UNION, DN_UNION, TIPO_UNION, ARM_FECHA_INICIO, ARM_FECHA_FIN,
             ARM_WORKER, SOL_FECHA_INICIO, SOL_FECHA_FIN, SOL_WORKER, NDT_UNION, R_NDT_UNION,
             ID, TAG_SPOOL, NDT_FECHA, NDT_STATUS, version, Creado_Por, Fecha_Creacion,
             Modificado_Por, Fecha_Modificacion
    """
    headers = [
        'ID_UNION', 'OT', 'N_UNION', 'DN_UNION', 'TIPO_UNION',
        'ARM_FECHA_INICIO', 'ARM_FECHA_FIN', 'ARM_WORKER',
        'SOL_FECHA_INICIO', 'SOL_FECHA_FIN', 'SOL_WORKER',
        'NDT_UNION', 'R_NDT_UNION', 'ID', 'TAG_SPOOL',
        'NDT_FECHA', 'NDT_STATUS', 'version',
        'Creado_Por', 'Fecha_Creacion', 'Modificado_Por', 'Fecha_Modificacion'
    ]

    # OT "001" has 3 unions
    # Union 1: ARM complete, SOLD complete
    # Union 2: ARM complete, SOLD not started
    # Union 3: ARM not started
    row1 = [
        '001+1', '001', '1', '10.0', 'BW',
        '01-02-2026 08:00:00', '01-02-2026 09:00:00', 'MR(93)',
        '01-02-2026 10:00:00', '01-02-2026 11:00:00', 'JP(94)',
        '', '', '001+1', 'SPOOL-001',
        '', '', 'uuid-1',
        'MR(93)', '01-02-2026 08:00:00', '', ''
    ]

    row2 = [
        '001+2', '001', '2', '12.5', 'BW',
        '01-02-2026 08:00:00', '01-02-2026 09:00:00', 'MR(93)',
        '', '', '',
        '', '', '001+2', 'SPOOL-001',
        '', '', 'uuid-2',
        'MR(93)', '01-02-2026 08:00:00', '', ''
    ]

    row3 = [
        '001+3', '001', '3', '8.0', 'BW',
        '', '', '',
        '', '', '',
        '', '', '001+3', 'SPOOL-001',
        '', '', 'uuid-3',
        'MR(93)', '01-02-2026 08:00:00', '', ''
    ]

    # OT "002" has 2 unions
    # Union 1: ARM not started
    # Union 2: ARM not started
    row4 = [
        '002+1', '002', '1', '14.0', 'BW',
        '', '', '',
        '', '', '',
        '', '', '002+1', 'SPOOL-002',
        '', '', 'uuid-4',
        'MR(93)', '01-02-2026 08:00:00', '', ''
    ]

    row5 = [
        '002+2', '002', '2', '10.0', 'BW',
        '', '', '',
        '', '', '',
        '', '', '002+2', 'SPOOL-002',
        '', '', 'uuid-5',
        'MR(93)', '01-02-2026 08:00:00', '', ''
    ]

    return [headers, row1, row2, row3, row4, row5]


@pytest.fixture
def mock_column_map():
    """Column map for Uniones sheet structure."""
    return {
        'idunion': 0,
        'ot': 1,
        'nunion': 2,
        'dnunion': 3,
        'tipounion': 4,
        'armfechainicio': 5,
        'armfechafin': 6,
        'armworker': 7,
        'solfechainicio': 8,
        'solfechafin': 9,
        'solworker': 10,
        'ndtunion': 11,
        'rndtunion': 12,
        'id': 13,
        'tagspool': 14,
        'ndtfecha': 15,
        'ndtstatus': 16,
        'version': 17,
        'creadopor': 18,
        'fechacreacion': 19,
        'modificadopor': 20,
        'fechamodificacion': 21,
    }


class TestGetByOT:
    """Test get_by_ot method that queries by OT column directly."""

    def test_get_by_ot_with_valid_ot_returns_multiple_unions(
        self, union_repository, mock_sheets_repo, sample_uniones_data, mock_column_map, monkeypatch
    ):
        """Test get_by_ot with valid OT returns all unions for that OT."""
        # Arrange
        mock_sheets_repo.read_worksheet.return_value = sample_uniones_data

        # Mock ColumnMapCache
        mock_cache = MagicMock()
        mock_cache.get_or_build.return_value = mock_column_map
        monkeypatch.setattr('backend.repositories.union_repository.ColumnMapCache', mock_cache)

        # Act
        result = union_repository.get_by_ot('001')

        # Assert
        assert len(result) == 3
        assert all(isinstance(u, Union) for u in result)
        assert all(u.ot == '001' for u in result)

        # Verify OT column was queried (Column B, index 1)
        mock_sheets_repo.read_worksheet.assert_called_once_with('Uniones')

        # Verify union details
        assert result[0].n_union == 1
        assert result[0].dn_union == 10.0
        assert result[0].arm_fecha_fin is not None
        assert result[0].sol_fecha_fin is not None

        assert result[1].n_union == 2
        assert result[1].dn_union == 12.5
        assert result[1].arm_fecha_fin is not None
        assert result[1].sol_fecha_fin is None

        assert result[2].n_union == 3
        assert result[2].dn_union == 8.0
        assert result[2].arm_fecha_fin is None
        assert result[2].sol_fecha_fin is None

    def test_get_by_ot_with_invalid_ot_returns_empty_list(
        self, union_repository, mock_sheets_repo, sample_uniones_data, mock_column_map, monkeypatch
    ):
        """Test get_by_ot with invalid OT returns empty list."""
        # Arrange
        mock_sheets_repo.read_worksheet.return_value = sample_uniones_data

        mock_cache = MagicMock()
        mock_cache.get_or_build.return_value = mock_column_map
        monkeypatch.setattr('backend.repositories.union_repository.ColumnMapCache', mock_cache)

        # Act
        result = union_repository.get_by_ot('999')

        # Assert
        assert result == []

    def test_get_by_ot_with_empty_sheet_returns_empty_list(
        self, union_repository, mock_sheets_repo, mock_column_map, monkeypatch
    ):
        """Test get_by_ot with empty sheet returns empty list gracefully."""
        # Arrange
        mock_sheets_repo.read_worksheet.return_value = []

        mock_cache = MagicMock()
        mock_cache.get_or_build.return_value = mock_column_map
        monkeypatch.setattr('backend.repositories.union_repository.ColumnMapCache', mock_cache)

        # Act
        result = union_repository.get_by_ot('001')

        # Assert
        assert result == []

    def test_get_by_ot_uses_ot_column_not_tag_spool(
        self, union_repository, mock_sheets_repo, sample_uniones_data, mock_column_map, monkeypatch
    ):
        """CRITICAL: Verify get_by_ot queries OT column, not TAG_SPOOL column."""
        # Arrange
        mock_sheets_repo.read_worksheet.return_value = sample_uniones_data

        mock_cache = MagicMock()
        mock_cache.get_or_build.return_value = mock_column_map
        monkeypatch.setattr('backend.repositories.union_repository.ColumnMapCache', mock_cache)

        # Act
        result = union_repository.get_by_ot('001')

        # Assert
        # Verify OT column (index 1) was used for filtering
        # If TAG_SPOOL (index 14) was used, this would fail
        assert len(result) == 3

        # All results should have ot='001', not tag_spool='001'
        assert all(u.ot == '001' for u in result)

        # TAG_SPOOL will have different format (e.g., "SPOOL-001")
        assert all(u.tag_spool == 'SPOOL-001' for u in result)

    def test_get_by_ot_raises_error_on_sheets_failure(
        self, union_repository, mock_sheets_repo
    ):
        """Test get_by_ot raises SheetsConnectionError on Google Sheets failure."""
        # Arrange
        mock_sheets_repo.read_worksheet.side_effect = Exception("Sheets API error")

        # Act & Assert
        with pytest.raises(SheetsConnectionError, match="Failed to read Uniones sheet"):
            union_repository.get_by_ot('001')


class TestGetDisponiblesARMByOT:
    """Test get_disponibles_arm_by_ot method."""

    def test_get_disponibles_arm_by_ot_filters_correctly(
        self, union_repository, mock_sheets_repo, sample_uniones_data, mock_column_map, monkeypatch
    ):
        """Test get_disponibles_arm_by_ot returns only unions where ARM_FECHA_FIN is NULL."""
        # Arrange
        mock_sheets_repo.read_worksheet.return_value = sample_uniones_data

        mock_cache = MagicMock()
        mock_cache.get_or_build.return_value = mock_column_map
        monkeypatch.setattr('backend.repositories.union_repository.ColumnMapCache', mock_cache)

        # Act
        result = union_repository.get_disponibles_arm_by_ot('001')

        # Assert
        # OT "001" has 3 unions total, but only union 3 has ARM_FECHA_FIN=NULL
        assert len(result) == 1
        assert result[0].n_union == 3
        assert result[0].arm_fecha_fin is None

    def test_get_disponibles_arm_by_ot_returns_empty_when_all_complete(
        self, union_repository, mock_sheets_repo, mock_column_map, monkeypatch
    ):
        """Test get_disponibles_arm_by_ot returns empty list when all ARM complete."""
        # Arrange
        headers = [
            'ID_UNION', 'OT', 'N_UNION', 'DN_UNION', 'TIPO_UNION',
            'ARM_FECHA_INICIO', 'ARM_FECHA_FIN', 'ARM_WORKER',
            'SOL_FECHA_INICIO', 'SOL_FECHA_FIN', 'SOL_WORKER',
            'NDT_UNION', 'R_NDT_UNION', 'ID', 'TAG_SPOOL',
            'NDT_FECHA', 'NDT_STATUS', 'version',
            'Creado_Por', 'Fecha_Creacion', 'Modificado_Por', 'Fecha_Modificacion'
        ]

        # All unions have ARM_FECHA_FIN populated
        row1 = [
            '003+1', '003', '1', '10.0', 'BW',
            '01-02-2026 08:00:00', '01-02-2026 09:00:00', 'MR(93)',
            '', '', '',
            '', '', '003+1', 'SPOOL-003',
            '', '', 'uuid-6',
            'MR(93)', '01-02-2026 08:00:00', '', ''
        ]

        data = [headers, row1]
        mock_sheets_repo.read_worksheet.return_value = data

        mock_cache = MagicMock()
        mock_cache.get_or_build.return_value = mock_column_map
        monkeypatch.setattr('backend.repositories.union_repository.ColumnMapCache', mock_cache)

        # Act
        result = union_repository.get_disponibles_arm_by_ot('003')

        # Assert
        assert result == []

    def test_get_disponibles_arm_by_ot_returns_empty_for_invalid_ot(
        self, union_repository, mock_sheets_repo, sample_uniones_data, mock_column_map, monkeypatch
    ):
        """Test get_disponibles_arm_by_ot returns empty list for invalid OT."""
        # Arrange
        mock_sheets_repo.read_worksheet.return_value = sample_uniones_data

        mock_cache = MagicMock()
        mock_cache.get_or_build.return_value = mock_column_map
        monkeypatch.setattr('backend.repositories.union_repository.ColumnMapCache', mock_cache)

        # Act
        result = union_repository.get_disponibles_arm_by_ot('999')

        # Assert
        assert result == []


class TestGetDisponiblesSOLDByOT:
    """Test get_disponibles_sold_by_ot method."""

    def test_get_disponibles_sold_by_ot_requires_arm_completion(
        self, union_repository, mock_sheets_repo, sample_uniones_data, mock_column_map, monkeypatch
    ):
        """Test get_disponibles_sold_by_ot returns only unions where ARM complete and SOLD not."""
        # Arrange
        mock_sheets_repo.read_worksheet.return_value = sample_uniones_data

        mock_cache = MagicMock()
        mock_cache.get_or_build.return_value = mock_column_map
        monkeypatch.setattr('backend.repositories.union_repository.ColumnMapCache', mock_cache)

        # Act
        result = union_repository.get_disponibles_sold_by_ot('001')

        # Assert
        # OT "001" has 3 unions:
        # - Union 1: ARM complete, SOLD complete (not disponible)
        # - Union 2: ARM complete, SOLD not started (disponible)
        # - Union 3: ARM not started (not disponible - ARM prerequisite)
        assert len(result) == 1
        assert result[0].n_union == 2
        assert result[0].arm_fecha_fin is not None
        assert result[0].sol_fecha_fin is None

    def test_get_disponibles_sold_by_ot_excludes_arm_incomplete(
        self, union_repository, mock_sheets_repo, sample_uniones_data, mock_column_map, monkeypatch
    ):
        """Test get_disponibles_sold_by_ot excludes unions where ARM not complete."""
        # Arrange
        mock_sheets_repo.read_worksheet.return_value = sample_uniones_data

        mock_cache = MagicMock()
        mock_cache.get_or_build.return_value = mock_column_map
        monkeypatch.setattr('backend.repositories.union_repository.ColumnMapCache', mock_cache)

        # Act
        result = union_repository.get_disponibles_sold_by_ot('002')

        # Assert
        # OT "002" has 2 unions, both with ARM not started
        assert result == []

    def test_get_disponibles_sold_by_ot_excludes_sold_complete(
        self, union_repository, mock_sheets_repo, mock_column_map, monkeypatch
    ):
        """Test get_disponibles_sold_by_ot excludes unions where SOLD already complete."""
        # Arrange
        headers = [
            'ID_UNION', 'OT', 'N_UNION', 'DN_UNION', 'TIPO_UNION',
            'ARM_FECHA_INICIO', 'ARM_FECHA_FIN', 'ARM_WORKER',
            'SOL_FECHA_INICIO', 'SOL_FECHA_FIN', 'SOL_WORKER',
            'NDT_UNION', 'R_NDT_UNION', 'ID', 'TAG_SPOOL',
            'NDT_FECHA', 'NDT_STATUS', 'version',
            'Creado_Por', 'Fecha_Creacion', 'Modificado_Por', 'Fecha_Modificacion'
        ]

        # Union with both ARM and SOLD complete
        row1 = [
            '004+1', '004', '1', '10.0', 'BW',
            '01-02-2026 08:00:00', '01-02-2026 09:00:00', 'MR(93)',
            '01-02-2026 10:00:00', '01-02-2026 11:00:00', 'JP(94)',
            '', '', '004+1', 'SPOOL-004',
            '', '', 'uuid-7',
            'MR(93)', '01-02-2026 08:00:00', '', ''
        ]

        data = [headers, row1]
        mock_sheets_repo.read_worksheet.return_value = data

        mock_cache = MagicMock()
        mock_cache.get_or_build.return_value = mock_column_map
        monkeypatch.setattr('backend.repositories.union_repository.ColumnMapCache', mock_cache)

        # Act
        result = union_repository.get_disponibles_sold_by_ot('004')

        # Assert
        assert result == []

    def test_get_disponibles_sold_by_ot_returns_empty_for_invalid_ot(
        self, union_repository, mock_sheets_repo, sample_uniones_data, mock_column_map, monkeypatch
    ):
        """Test get_disponibles_sold_by_ot returns empty list for invalid OT."""
        # Arrange
        mock_sheets_repo.read_worksheet.return_value = sample_uniones_data

        mock_cache = MagicMock()
        mock_cache.get_or_build.return_value = mock_column_map
        monkeypatch.setattr('backend.repositories.union_repository.ColumnMapCache', mock_cache)

        # Act
        result = union_repository.get_disponibles_sold_by_ot('999')

        # Assert
        assert result == []


class TestOTQueryEdgeCases:
    """Test edge cases for OT-based queries."""

    def test_get_by_ot_handles_malformed_rows_gracefully(
        self, union_repository, mock_sheets_repo, mock_column_map, monkeypatch
    ):
        """Test get_by_ot skips malformed rows and continues processing."""
        # Arrange
        headers = [
            'ID_UNION', 'OT', 'N_UNION', 'DN_UNION', 'TIPO_UNION',
            'ARM_FECHA_INICIO', 'ARM_FECHA_FIN', 'ARM_WORKER',
            'SOL_FECHA_INICIO', 'SOL_FECHA_FIN', 'SOL_WORKER',
            'NDT_UNION', 'R_NDT_UNION', 'ID', 'TAG_SPOOL',
            'NDT_FECHA', 'NDT_STATUS', 'version',
            'Creado_Por', 'Fecha_Creacion', 'Modificado_Por', 'Fecha_Modificacion'
        ]

        # Valid row
        row1 = [
            '005+1', '005', '1', '10.0', 'BW',
            '', '', '',
            '', '', '',
            '', '', '005+1', 'SPOOL-005',
            '', '', 'uuid-8',
            'MR(93)', '01-02-2026 08:00:00', '', ''
        ]

        # Malformed row - missing required ID field
        row2 = [
            '', '005', '2', '12.0', 'BW',
            '', '', '',
            '', '', '',
            '', '', '', 'SPOOL-005',
            '', '', 'uuid-9',
            'MR(93)', '01-02-2026 08:00:00', '', ''
        ]

        # Valid row
        row3 = [
            '005+3', '005', '3', '8.0', 'BW',
            '', '', '',
            '', '', '',
            '', '', '005+3', 'SPOOL-005',
            '', '', 'uuid-10',
            'MR(93)', '01-02-2026 08:00:00', '', ''
        ]

        data = [headers, row1, row2, row3]
        mock_sheets_repo.read_worksheet.return_value = data

        mock_cache = MagicMock()
        mock_cache.get_or_build.return_value = mock_column_map
        monkeypatch.setattr('backend.repositories.union_repository.ColumnMapCache', mock_cache)

        # Act
        result = union_repository.get_by_ot('005')

        # Assert
        # Should return 2 valid unions, skipping malformed row
        assert len(result) == 2
        assert result[0].n_union == 1
        assert result[1].n_union == 3

    def test_ot_queries_use_column_map_cache(
        self, union_repository, mock_sheets_repo, sample_uniones_data, mock_column_map, monkeypatch
    ):
        """Test that all OT queries use ColumnMapCache for dynamic column access."""
        # Arrange
        mock_sheets_repo.read_worksheet.return_value = sample_uniones_data

        mock_cache = MagicMock()
        mock_cache.get_or_build.return_value = mock_column_map
        monkeypatch.setattr('backend.repositories.union_repository.ColumnMapCache', mock_cache)

        # Act
        union_repository.get_by_ot('001')

        # Assert
        # Verify ColumnMapCache was used (no hardcoded indices)
        mock_cache.get_or_build.assert_called()
