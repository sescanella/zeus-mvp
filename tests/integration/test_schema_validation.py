"""
Integration tests for v4.0 schema validation at startup.

Tests that validate_schema_startup.py correctly identifies missing columns
and passes when all required v4.0 columns are present.

Mocks SheetsRepository responses to simulate different schema states.
"""
import pytest
from unittest.mock import Mock, patch, MagicMock
from backend.scripts.validate_schema_startup import (
    validate_v4_schema,
    validate_sheet_columns,
    OPERACIONES_V4_COLUMNS,
    UNIONES_V4_COLUMNS,
    METADATA_V4_COLUMNS
)
from backend.core.column_map_cache import ColumnMapCache


@pytest.fixture(autouse=True)
def clear_column_cache():
    """Clear ColumnMapCache between tests for isolation."""
    ColumnMapCache.clear_all()
    yield
    ColumnMapCache.clear_all()


@pytest.fixture
def mock_sheets_repo():
    """Create a mock SheetsRepository for testing."""
    repo = Mock()
    repo._get_spreadsheet = Mock()
    return repo


class TestSchemaValidation:
    """Test suite for v4.0 schema validation."""

    def test_startup_fails_missing_operaciones_columns(self, mock_sheets_repo):
        """
        Test that validation fails when Operaciones is missing v4.0 columns.

        Scenario: Operaciones has only v3.0 schema (67 columns), missing v4.0 additions.
        Expected: validate_v4_schema returns False with "Total_Uniones" in missing list.
        """
        # Mock Operaciones with only v3.0 columns (no v4.0 additions)
        v3_headers = [
            "TAG_SPOOL", "Armador", "Soldador", "Fecha_Armado", "Fecha_Soldadura",
            "Ocupado_Por", "Fecha_Ocupacion", "version", "Estado_Detalle"
        ]
        # Missing: Total_Uniones, Uniones_ARM_Completadas, Uniones_SOLD_Completadas,
        # Pulgadas_ARM, Pulgadas_SOLD

        # Mock read_worksheet to return v3.0 headers
        def mock_read_worksheet(sheet_name):
            if sheet_name == "Operaciones":
                return [v3_headers]  # Header row only
            elif sheet_name == "Uniones":
                # Return valid Uniones to isolate Operaciones failure
                return [UNIONES_V4_COLUMNS]
            elif sheet_name == "Metadata":
                # Return valid Metadata to isolate Operaciones failure
                metadata_cols = METADATA_V4_COLUMNS["v3.0_existing"] + METADATA_V4_COLUMNS["v4.0_new"]
                return [metadata_cols]
            raise ValueError(f"Unknown sheet: {sheet_name}")

        mock_sheets_repo.read_worksheet = Mock(side_effect=mock_read_worksheet)

        # Run validation
        success, details = validate_v4_schema(repo=mock_sheets_repo)

        # Assert validation failed
        assert success is False, "Validation should fail with missing Operaciones v4.0 columns"

        # Assert Operaciones status is FAIL
        assert details["Operaciones"]["status"] == "FAIL"

        # Assert v4.0 columns are in missing list
        missing = details["Operaciones"]["missing"]
        assert "Total_Uniones" in missing
        assert "Uniones_ARM_Completadas" in missing
        assert "Uniones_SOLD_Completadas" in missing
        assert "Pulgadas_ARM" in missing
        assert "Pulgadas_SOLD" in missing

        # Assert Uniones and Metadata passed (to confirm isolation)
        assert details["Uniones"]["status"] == "OK"
        assert details["Metadata"]["status"] == "OK"

    def test_startup_fails_missing_uniones_sheet(self, mock_sheets_repo):
        """
        Test that validation fails when Uniones sheet is missing or empty.

        Scenario: Uniones sheet doesn't exist or has no headers.
        Expected: validate_v4_schema returns False with error about Uniones.
        """
        # Mock read_worksheet to raise exception for Uniones
        def mock_read_worksheet(sheet_name):
            if sheet_name == "Uniones":
                raise Exception("Sheet 'Uniones' not found")
            elif sheet_name == "Operaciones":
                # Return valid Operaciones
                operaciones_cols = (
                    OPERACIONES_V4_COLUMNS["v3.0_critical"] +
                    OPERACIONES_V4_COLUMNS["v4.0_new"]
                )
                return [operaciones_cols]
            elif sheet_name == "Metadata":
                # Return valid Metadata
                metadata_cols = (
                    METADATA_V4_COLUMNS["v3.0_existing"] +
                    METADATA_V4_COLUMNS["v4.0_new"]
                )
                return [metadata_cols]
            raise ValueError(f"Unknown sheet: {sheet_name}")

        mock_sheets_repo.read_worksheet = Mock(side_effect=mock_read_worksheet)

        # Run validation
        success, details = validate_v4_schema(repo=mock_sheets_repo)

        # Assert validation failed
        assert success is False, "Validation should fail when Uniones sheet missing"

        # Assert Uniones status is FAIL
        assert details["Uniones"]["status"] == "FAIL"

        # Assert all 18 Uniones columns are in missing list
        missing = details["Uniones"]["missing"]
        assert len(missing) == len(UNIONES_V4_COLUMNS)
        assert "TAG_SPOOL" in missing
        assert "N_UNION" in missing
        assert "DN_UNION" in missing





    def test_validate_sheet_columns_directly(self, mock_sheets_repo):
        """
        Test validate_sheet_columns function in isolation.

        Verifies the core validation logic works correctly.
        """
        # Mock sheet with some missing columns
        headers = ["TAG_SPOOL", "Armador", "Soldador"]  # Missing other columns
        mock_sheets_repo.read_worksheet = Mock(return_value=[headers])

        # Test with required columns
        required = ["TAG_SPOOL", "Armador", "Soldador", "Fecha_Armado"]

        all_present, missing = validate_sheet_columns(
            repo=mock_sheets_repo,
            sheet_name="Operaciones",
            required_columns=required
        )

        # Assert results
        assert all_present is False, "Should detect missing columns"
        assert "Fecha_Armado" in missing
        assert len(missing) == 1

