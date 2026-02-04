"""
Unit tests for UnionRepository (v4.0 union-level tracking).

Tests verify:
- Dynamic column mapping (ColumnMapCache usage)
- TAG_SPOOL as foreign key (not OT)
- Query operations (get_by_spool, get_disponibles)
- Aggregation operations (count_completed, sum_pulgadas)
- Error handling for missing columns
"""
import pytest
from unittest.mock import Mock, MagicMock
from datetime import datetime

from backend.repositories.union_repository import UnionRepository
from backend.models.union import Union
from backend.core.column_map_cache import ColumnMapCache


@pytest.fixture(autouse=True)
def clear_column_cache():
    """Clear ColumnMapCache before each test to ensure isolation."""
    ColumnMapCache.clear_all()
    yield
    ColumnMapCache.clear_all()


@pytest.fixture
def mock_sheets_repository():
    """Create mock SheetsRepository for testing."""
    mock = Mock()

    # Default header row for Uniones sheet (19 cols: OT required by _row_to_union)
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
        "Fecha_Modificacion",   # col 18
    ]

    # Sample data rows (OT column required by UnionRepository._row_to_union)
    rows = [
        header,  # Row 0 (header)

        # Row 1: OT-123, union 1, ARM complete, SOLD pending
        [
            "OT-123+1",             # ID
            "123",                  # OT
            "OT-123",               # TAG_SPOOL
            "1",                    # N_UNION
            "2.5",                  # DN_UNION
            "Tipo A",               # TIPO_UNION
            "20-01-2026 08:00:00",  # ARM_FECHA_INICIO
            "20-01-2026 10:00:00",  # ARM_FECHA_FIN (complete)
            "MR(93)",               # ARM_WORKER
            "",                     # SOL_FECHA_INICIO
            "",                     # SOL_FECHA_FIN (pending)
            "",                     # SOL_WORKER
            "",                     # NDT_FECHA
            "",                     # NDT_STATUS
            "version-uuid-1",       # version
            "MR(93)",               # Creado_Por
            "19-01-2026 14:00:00",  # Fecha_Creacion
            "",                     # Modificado_Por
            "",                     # Fecha_Modificacion
        ],

        # Row 2: OT-123, union 2, ARM pending
        [
            "OT-123+2",
            "123",                  # OT
            "OT-123",
            "2",
            "3.0",
            "Tipo B",
            "",                     # ARM_FECHA_INICIO (pending)
            "",                     # ARM_FECHA_FIN (pending)
            "",
            "",
            "",
            "",
            "",
            "",
            "version-uuid-2",
            "MR(93)",
            "19-01-2026 14:00:00",
            "",
            "",
        ],

        # Row 3: OT-124, union 1, ARM and SOLD complete
        [
            "OT-124+1",
            "124",                  # OT
            "OT-124",
            "1",
            "4.0",
            "Tipo A",
            "21-01-2026 08:00:00",  # ARM_FECHA_INICIO
            "21-01-2026 10:00:00",  # ARM_FECHA_FIN (complete)
            "JP(94)",
            "21-01-2026 11:00:00",  # SOL_FECHA_INICIO
            "21-01-2026 13:00:00",  # SOL_FECHA_FIN (complete)
            "MG(95)",
            "",
            "",
            "version-uuid-3",
            "JP(94)",
            "20-01-2026 09:00:00",
            "",
            "",
        ],

        # Row 4: OT-125, union 1, ARM pending
        [
            "OT-125+1",
            "125",                  # OT
            "OT-125",
            "1",
            "1.5",
            "Tipo C",
            "",                     # ARM_FECHA_INICIO (pending)
            "",                     # ARM_FECHA_FIN (pending)
            "",
            "",
            "",
            "",
            "",
            "",
            "version-uuid-4",
            "MR(93)",
            "22-01-2026 10:00:00",
            "",
            "",
        ],
    ]

    mock.read_worksheet.return_value = rows
    return mock


class TestUnionRepository:
    """Test suite for UnionRepository."""

    def test_get_by_spool_returns_unions(self, mock_sheets_repository):
        """Test get_by_spool returns correct unions for a given TAG_SPOOL."""
        repo = UnionRepository(mock_sheets_repository)

        # Query for OT-123 (should return 2 unions)
        unions = repo.get_by_spool("OT-123")

        assert len(unions) == 2
        assert all(u.tag_spool == "OT-123" for u in unions)
        assert unions[0].n_union == 1
        assert unions[0].dn_union == 2.5
        assert unions[1].n_union == 2
        assert unions[1].dn_union == 3.0

    def test_get_by_spool_returns_empty_for_unknown(self, mock_sheets_repository):
        """Test get_by_spool returns empty list for non-existent spool."""
        repo = UnionRepository(mock_sheets_repository)

        unions = repo.get_by_spool("NONEXISTENT")

        assert unions == []

    def test_get_disponibles_arm(self, mock_sheets_repository):
        """Test get_disponibles returns only ARM-available unions."""
        repo = UnionRepository(mock_sheets_repository)

        disponibles = repo.get_disponibles("ARM")

        # Should return unions with ARM_FECHA_FIN = NULL
        # OT-123 union 2: ARM pending
        # OT-125 union 1: ARM pending
        assert "OT-123" in disponibles
        assert len(disponibles["OT-123"]) == 1
        assert disponibles["OT-123"][0].n_union == 2

        assert "OT-125" in disponibles
        assert len(disponibles["OT-125"]) == 1

        # OT-124 should NOT be in disponibles (ARM complete)
        # OT-123 union 1 should NOT be in disponibles (ARM complete)
        assert all(u.arm_fecha_fin is None for unions in disponibles.values() for u in unions)

    def test_get_disponibles_sold(self, mock_sheets_repository):
        """Test get_disponibles returns only SOLD-available unions."""
        repo = UnionRepository(mock_sheets_repository)

        disponibles = repo.get_disponibles("SOLD")

        # Should return unions with ARM_FECHA_FIN != NULL and SOL_FECHA_FIN = NULL
        # Only OT-123 union 1 meets criteria
        assert "OT-123" in disponibles
        assert len(disponibles["OT-123"]) == 1
        assert disponibles["OT-123"][0].n_union == 1
        assert disponibles["OT-123"][0].arm_fecha_fin is not None
        assert disponibles["OT-123"][0].sol_fecha_fin is None

        # OT-124 should NOT be in disponibles (SOLD complete)
        # OT-123 union 2 should NOT be in disponibles (ARM not complete)
        # OT-125 should NOT be in disponibles (ARM not complete)

    def test_count_completed(self, mock_sheets_repository):
        """Test count_completed returns correct count for ARM and SOLD."""
        repo = UnionRepository(mock_sheets_repository)

        # OT-123 has 1 ARM completed (union 1), 1 ARM pending (union 2)
        arm_count = repo.count_completed("OT-123", "ARM")
        assert arm_count == 1

        # OT-123 has 0 SOLD completed
        sold_count = repo.count_completed("OT-123", "SOLD")
        assert sold_count == 0

        # OT-124 has 1 ARM and 1 SOLD completed
        arm_count_124 = repo.count_completed("OT-124", "ARM")
        sold_count_124 = repo.count_completed("OT-124", "SOLD")
        assert arm_count_124 == 1
        assert sold_count_124 == 1

    def test_sum_pulgadas(self, mock_sheets_repository):
        """Test sum_pulgadas returns correct sum with decimal precision."""
        repo = UnionRepository(mock_sheets_repository)

        # OT-123 ARM completed: union 1 with 2.5 pulgadas
        arm_sum = repo.sum_pulgadas("OT-123", "ARM")
        assert arm_sum == 2.5

        # OT-123 SOLD completed: 0 (no SOLD complete)
        sold_sum = repo.sum_pulgadas("OT-123", "SOLD")
        assert sold_sum == 0.0

        # OT-124 ARM and SOLD: union 1 with 4.0 pulgadas
        arm_sum_124 = repo.sum_pulgadas("OT-124", "ARM")
        sold_sum_124 = repo.sum_pulgadas("OT-124", "SOLD")
        assert arm_sum_124 == 4.0
        assert sold_sum_124 == 4.0

    def test_handles_missing_columns_gracefully(self, mock_sheets_repository):
        """Test repository doesn't crash if optional columns are missing."""
        # Modify mock to have minimal columns (OT required by _row_to_union)
        minimal_header = [
            "ID", "OT", "TAG_SPOOL", "N_UNION", "DN_UNION", "TIPO_UNION",
            "Creado_Por", "Fecha_Creacion"
        ]
        minimal_row = [
            "OT-126+1",
            "126",                  # OT
            "OT-126",
            "1",
            "5.0",
            "Tipo A",
            "MR(93)",
            "23-01-2026 10:00:00",
        ]
        mock_sheets_repository.read_worksheet.return_value = [minimal_header, minimal_row]

        repo = UnionRepository(mock_sheets_repository)
        unions = repo.get_by_spool("OT-126")

        assert len(unions) == 1
        assert unions[0].tag_spool == "OT-126"
        # Optional fields should be None
        assert unions[0].arm_fecha_inicio is None
        assert unions[0].arm_fecha_fin is None
        assert unions[0].ndt_status is None

    def test_uses_column_map_cache(self, mock_sheets_repository):
        """Test repository uses ColumnMapCache for dynamic column access."""
        repo = UnionRepository(mock_sheets_repository)

        # First call should build cache
        unions_1 = repo.get_by_spool("OT-123")

        # Verify ColumnMapCache was populated
        cached_sheets = ColumnMapCache.get_cached_sheets()
        assert "Uniones" in cached_sheets

        # Second call should use cache (verify read_worksheet called only once for cache build)
        unions_2 = repo.get_by_spool("OT-123")

        # Should return same results
        assert len(unions_1) == len(unions_2)

    def test_uses_tag_spool_as_foreign_key(self, mock_sheets_repository):
        """Test repository uses TAG_SPOOL for queries but synthesizes ID from OT+N_UNION."""
        # Use same header and row structure as main fixture (19 cols, OT required)
        header = mock_sheets_repository.read_worksheet.return_value[0]
        row_special = [
            "9999",                   # ID (sequential, will be overridden by synthesis)
            "SPECIAL",                # OT
            "SPECIAL-001",            # TAG_SPOOL
            "1", "6.0", "Tipo D",     # N_UNION, DN_UNION, TIPO_UNION
            "", "", "",              # ARM_FECHA_INICIO, ARM_FECHA_FIN, ARM_WORKER
            "", "", "",              # SOL_*
            "", "",                   # NDT_*
            "version-uuid-5",         # version
            "MR(93)",                  # Creado_Por (worker format)
            "24-01-2026 11:00:00",    # Fecha_Creacion
            "", "",                   # Modificado_Por, Fecha_Modificacion
        ]
        assert len(row_special) == 19, "Row must match header length"
        mock_sheets_repository.read_worksheet.return_value = [header, row_special]

        repo = UnionRepository(mock_sheets_repository)
        unions = repo.get_by_spool("SPECIAL-001")

        assert len(unions) == 1
        assert unions[0].tag_spool == "SPECIAL-001"
        # ID is synthesized as OT+N_UNION, NOT TAG_SPOOL+N_UNION
        assert unions[0].id == "SPECIAL+1"

    def test_row_to_union_validates_required_fields(self, mock_sheets_repository):
        """Test _row_to_union raises ValueError for missing required fields."""
        # Create row with missing TAG_SPOOL
        header = [
            "ID", "TAG_SPOOL", "N_UNION", "DN_UNION", "TIPO_UNION",
            "Creado_Por", "Fecha_Creacion"
        ]
        invalid_row = [
            "OT-999+1",
            "",  # TAG_SPOOL missing (empty)
            "1",
            "2.0",
            "Tipo A",
            "MR(93)",
            "25-01-2026 12:00:00",
        ]
        mock_sheets_repository.read_worksheet.return_value = [header, invalid_row]

        repo = UnionRepository(mock_sheets_repository)

        # Should return empty list (parse error logged but not raised)
        unions = repo.get_by_spool("OT-999")
        assert len(unions) == 0

    def test_datetime_parsing_handles_multiple_formats(self, mock_sheets_repository):
        """Test datetime parsing handles both full and date-only formats."""
        header = [
            "ID", "OT", "TAG_SPOOL", "N_UNION", "DN_UNION", "TIPO_UNION",
            "ARM_FECHA_INICIO", "ARM_FECHA_FIN",
            "Creado_Por", "Fecha_Creacion"
        ]
        row_with_dates = [
            "OT-200+1",
            "200",                   # OT
            "OT-200",
            "1",
            "3.5",
            "Tipo B",
            "26-01-2026 14:30:00",  # Full datetime
            "26-01-2026",           # Date only
            "MR(93)",
            "25-01-2026 10:00:00",
        ]
        mock_sheets_repository.read_worksheet.return_value = [header, row_with_dates]

        repo = UnionRepository(mock_sheets_repository)
        unions = repo.get_by_spool("OT-200")

        assert len(unions) == 1
        assert unions[0].arm_fecha_inicio is not None
        assert unions[0].arm_fecha_fin is not None
        # Both should be datetime objects
        assert isinstance(unions[0].arm_fecha_inicio, datetime)
        assert isinstance(unions[0].arm_fecha_fin, datetime)

    def test_empty_sheet_returns_empty_list(self, mock_sheets_repository):
        """Test repository handles empty sheet gracefully."""
        # Empty sheet (header only)
        header = ["ID", "TAG_SPOOL", "N_UNION"]
        mock_sheets_repository.read_worksheet.return_value = [header]

        repo = UnionRepository(mock_sheets_repository)
        unions = repo.get_by_spool("ANY")

        assert unions == []

    def test_get_disponibles_returns_empty_for_empty_sheet(self, mock_sheets_repository):
        """Test get_disponibles handles empty sheet gracefully."""
        header = ["ID", "TAG_SPOOL"]
        mock_sheets_repository.read_worksheet.return_value = [header]

        repo = UnionRepository(mock_sheets_repository)
        disponibles_arm = repo.get_disponibles("ARM")
        disponibles_sold = repo.get_disponibles("SOLD")

        assert disponibles_arm == {}
        assert disponibles_sold == {}

    def test_union_properties_work_correctly(self, mock_sheets_repository):
        """Test Union model properties (arm_completada, pulgadas_arm, etc.)."""
        repo = UnionRepository(mock_sheets_repository)
        unions = repo.get_by_spool("OT-123")

        # Union 1: ARM complete, SOLD pending
        union_1 = unions[0]
        assert union_1.arm_completada is True
        assert union_1.sol_completada is False
        assert union_1.pulgadas_arm == 2.5
        assert union_1.pulgadas_sold == 0

        # Union 2: ARM pending
        union_2 = unions[1]
        assert union_2.arm_completada is False
        assert union_2.sol_completada is False
        assert union_2.pulgadas_arm == 0
        assert union_2.pulgadas_sold == 0

    def test_count_and_sum_for_nonexistent_spool(self, mock_sheets_repository):
        """Test count_completed and sum_pulgadas for non-existent spool."""
        repo = UnionRepository(mock_sheets_repository)

        count_arm = repo.count_completed("NONEXISTENT", "ARM")
        count_sold = repo.count_completed("NONEXISTENT", "SOLD")
        sum_arm = repo.sum_pulgadas("NONEXISTENT", "ARM")
        sum_sold = repo.sum_pulgadas("NONEXISTENT", "SOLD")

        assert count_arm == 0
        assert count_sold == 0
        assert sum_arm == 0.0
        assert sum_sold == 0.0
