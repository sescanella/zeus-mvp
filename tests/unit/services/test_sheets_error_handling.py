"""
Unit tests for Sheets data parsing and repository error handling.

Tests cover:
- SheetsService: malformed data parsing, missing columns, invalid values
- SheetsRepository: connection errors, auth failures, API rate limits, empty sheets
"""

import pytest
from unittest.mock import patch, MagicMock, PropertyMock
from datetime import date

import gspread
from gspread.exceptions import APIError, SpreadsheetNotFound, WorksheetNotFound

from backend.services.sheets_service import SheetsService
from backend.repositories.sheets_repository import SheetsRepository
from backend.exceptions import SheetsConnectionError, SheetsUpdateError


# ==================== FIXTURES ====================


@pytest.fixture
def column_map():
    """Minimal column map for Operaciones sheet testing."""
    return {
        "split": 0,
        "ot": 1,
        "nv": 2,
        "fechamateriales": 3,
        "fechaarmado": 4,
        "armador": 5,
        "fechasoldadura": 6,
        "soldador": 7,
        "ocupadopor": 8,
        "fechaocupacion": 9,
        "estadodetalle": 10,
        "totaluniones": 11,
        "unionesarmcompletadas": 12,
        "unionessoldcompletadas": 13,
        "pulgadasarm": 14,
        "pulgadassold": 15,
    }


@pytest.fixture
def sheets_service(column_map):
    """SheetsService instance with test column map."""
    return SheetsService(column_map=column_map)


def _make_row(overrides=None, length=72):
    """Build a minimal valid spool row with optional overrides."""
    row = [""] * length
    row[0] = "SPOOL-001"  # SPLIT (tag_spool) - required
    if overrides:
        for idx, val in overrides.items():
            row[idx] = val
    return row


# ==================== SheetsService: MALFORMED DATA PARSING ====================


class TestSheetsServiceMalformedData:

    def test_parse_spool_row_missing_tag_raises(self, sheets_service):
        """Row with empty SPLIT column should raise ValueError."""
        row = _make_row()
        row[0] = ""  # empty tag_spool
        with pytest.raises(ValueError, match="SPLIT.*vacío"):
            sheets_service.parse_spool_row(row)

    def test_parse_spool_row_short_row_padded(self, sheets_service):
        """Short row (fewer than 72 cols) should be padded and parsed."""
        row = ["SPOOL-SHORT"] + [""] * 10  # only 11 columns
        spool = sheets_service.parse_spool_row(row)
        assert spool.tag_spool == "SPOOL-SHORT"
        assert spool.ocupado_por is None
        assert spool.total_uniones is None

    def test_parse_spool_row_none_in_numeric_fields(self, sheets_service):
        """None/empty in numeric v4.0 fields should default to None."""
        row = _make_row({11: "", 12: None, 14: ""})
        spool = sheets_service.parse_spool_row(row)
        assert spool.total_uniones is None
        assert spool.uniones_arm_completadas is None
        assert spool.pulgadas_arm is None

    def test_parse_spool_row_invalid_number_in_total_uniones(self, sheets_service):
        """Non-numeric Total_Uniones should default to None with warning."""
        row = _make_row({11: "abc"})
        spool = sheets_service.parse_spool_row(row)
        assert spool.total_uniones is None

    def test_parse_spool_row_negative_total_uniones(self, sheets_service):
        """Negative Total_Uniones should default to None."""
        row = _make_row({11: "-5"})
        spool = sheets_service.parse_spool_row(row)
        assert spool.total_uniones is None

    def test_parse_spool_row_valid_numeric_fields(self, sheets_service):
        """Valid numeric v4.0 fields should parse correctly."""
        row = _make_row({11: "10", 12: "5", 13: "3", 14: "120.5", 15: "80.0"})
        spool = sheets_service.parse_spool_row(row)
        assert spool.total_uniones == 10
        assert spool.uniones_arm_completadas == 5
        assert spool.uniones_sold_completadas == 3
        assert spool.pulgadas_arm == 120.5
        assert spool.pulgadas_sold == 80.0

    def test_safe_float_none(self):
        """safe_float with None input returns default."""
        assert SheetsService.safe_float(None) == 0.0

    def test_safe_float_non_numeric_string(self):
        """safe_float with non-numeric string returns default."""
        assert SheetsService.safe_float("not-a-number") == 0.0

    def test_parse_date_unrecognized_format(self):
        """parse_date with unrecognized format returns None."""
        assert SheetsService.parse_date("April 5th 2026") is None

    def test_parse_date_valid_formats(self):
        """parse_date handles DD-MM-YYYY and DD/MM/YYYY correctly."""
        assert SheetsService.parse_date("21-01-2026") == date(2026, 1, 21)
        assert SheetsService.parse_date("30/7/2025") == date(2025, 7, 30)

    def test_parse_worker_row_too_few_columns(self):
        """Worker row with fewer than 4 columns raises ValueError."""
        with pytest.raises(ValueError, match="incompleta"):
            SheetsService.parse_worker_row(["93", "Juan"])

    def test_parse_worker_row_empty_nombre(self):
        """Worker row with empty nombre raises ValueError."""
        with pytest.raises(ValueError, match="Nombre.*vacío"):
            SheetsService.parse_worker_row(["93", "", "Rodriguez", "Armador", "TRUE"])


# ==================== SheetsService: CONSTRUCTOR VALIDATION ====================


class TestSheetsServiceInit:

    def test_empty_column_map_raises(self):
        """SheetsService with empty column_map should raise ValueError."""
        with pytest.raises(ValueError, match="column_map is required"):
            SheetsService(column_map={})

    def test_none_column_map_raises(self):
        """SheetsService with None column_map should raise ValueError."""
        with pytest.raises(ValueError, match="column_map is required"):
            SheetsService(column_map=None)


# ==================== SheetsRepository: CONNECTION ERRORS ====================


class TestSheetsRepositoryErrors:

    @patch("backend.repositories.sheets_repository.config")
    def test_api_error_429_triggers_retry_and_raises(self, mock_config):
        """gspread APIError 429 should be retried then raise SheetsConnectionError."""
        mock_config.GOOGLE_SHEET_ID = "test-sheet-id"
        mock_config.HOJA_TRABAJADORES_NOMBRE = "Trabajadores"
        mock_config.get_credentials_dict.return_value = None

        repo = SheetsRepository()

        # Simulate auth succeeding but worksheet read hitting rate limit
        mock_client = MagicMock()
        mock_spreadsheet = MagicMock()
        mock_worksheet = MagicMock()

        # Create a mock APIError for 429
        mock_response = MagicMock()
        mock_response.status_code = 429
        mock_response.json.return_value = {
            "error": {"code": 429, "message": "Rate limit exceeded", "status": "RESOURCE_EXHAUSTED"}
        }
        api_error = APIError(mock_response)

        mock_worksheet.get_all_values.side_effect = api_error
        mock_spreadsheet.worksheet.return_value = mock_worksheet
        mock_client.open_by_key.return_value = mock_spreadsheet

        # Inject mocked client to skip auth
        repo._client = mock_client
        repo._spreadsheet = mock_spreadsheet
        # Clear any cache
        repo._cache = MagicMock()
        repo._cache.get.return_value = None

        with pytest.raises(SheetsConnectionError):
            repo.read_worksheet("Operaciones")

    @patch("backend.repositories.sheets_repository.config")
    def test_auth_failure_raises_connection_error(self, mock_config):
        """Auth failure should raise SheetsConnectionError."""
        mock_config.get_credentials_dict.return_value = None

        repo = SheetsRepository()

        with pytest.raises(SheetsConnectionError, match="credenciales"):
            repo._get_client()

    @patch("backend.repositories.sheets_repository.config")
    def test_spreadsheet_not_found_raises(self, mock_config):
        """SpreadsheetNotFound should raise SheetsConnectionError."""
        mock_config.GOOGLE_SHEET_ID = "nonexistent-id"

        repo = SheetsRepository()

        mock_client = MagicMock()
        mock_client.open_by_key.side_effect = SpreadsheetNotFound("not found")
        repo._client = mock_client

        with pytest.raises(SheetsConnectionError, match="no encontrado"):
            repo._get_spreadsheet()

    @patch("backend.repositories.sheets_repository.config")
    def test_worksheet_not_found_raises(self, mock_config):
        """Reading a nonexistent worksheet should raise SheetsConnectionError."""
        mock_config.HOJA_TRABAJADORES_NOMBRE = "Trabajadores"

        repo = SheetsRepository()

        mock_spreadsheet = MagicMock()
        mock_spreadsheet.worksheet.side_effect = WorksheetNotFound("NoSheet")
        mock_spreadsheet.worksheets.return_value = [MagicMock(title="Operaciones")]
        repo._client = MagicMock()
        repo._spreadsheet = mock_spreadsheet
        repo._cache = MagicMock()
        repo._cache.get.return_value = None

        with pytest.raises(SheetsConnectionError, match="no encontrada"):
            repo.read_worksheet("NonExistentSheet")

    @patch("backend.repositories.sheets_repository.config")
    def test_empty_sheet_returns_empty_list(self, mock_config):
        """Sheet with 0 rows should return empty list."""
        mock_config.HOJA_TRABAJADORES_NOMBRE = "Trabajadores"

        repo = SheetsRepository()

        mock_spreadsheet = MagicMock()
        mock_worksheet = MagicMock()
        mock_worksheet.get_all_values.return_value = []
        mock_spreadsheet.worksheet.return_value = mock_worksheet
        repo._client = MagicMock()
        repo._spreadsheet = mock_spreadsheet
        repo._cache = MagicMock()
        repo._cache.get.return_value = None

        result = repo.read_worksheet("Operaciones")
        assert result == []

    @patch("backend.repositories.sheets_repository.config")
    def test_batch_update_failure_raises_update_error(self, mock_config):
        """Failed batch update should raise SheetsUpdateError."""
        repo = SheetsRepository()

        mock_spreadsheet = MagicMock()
        mock_worksheet = MagicMock()
        mock_worksheet.batch_update.side_effect = Exception("Network timeout")
        mock_spreadsheet.worksheet.return_value = mock_worksheet
        repo._client = MagicMock()
        repo._spreadsheet = mock_spreadsheet
        repo._cache = MagicMock()

        updates = [{"row": 10, "column": "V", "value": "test"}]
        with pytest.raises(SheetsUpdateError, match="batch update"):
            repo.batch_update("Operaciones", updates)
