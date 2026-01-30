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

    def test_startup_fails_missing_metadata_column(self, mock_sheets_repo):
        """
        Test that validation fails when Metadata is missing N_UNION column.

        Scenario: Metadata has only v3.0 schema (10 columns), missing v4.0 N_UNION.
        Expected: validate_v4_schema returns False with "N_UNION" in missing list.
        """
        # Mock Metadata with only v3.0 columns
        metadata_v3_headers = [
            "ID", "Timestamp", "Evento_Tipo", "TAG_SPOOL", "Worker_ID",
            "Worker_Nombre", "Operacion", "Accion", "Fecha_Operacion", "Metadata_JSON"
        ]
        # Missing: N_UNION

        def mock_read_worksheet(sheet_name):
            if sheet_name == "Metadata":
                return [metadata_v3_headers]  # v3.0 only
            elif sheet_name == "Operaciones":
                # Return valid Operaciones
                operaciones_cols = (
                    OPERACIONES_V4_COLUMNS["v3.0_critical"] +
                    OPERACIONES_V4_COLUMNS["v4.0_new"]
                )
                return [operaciones_cols]
            elif sheet_name == "Uniones":
                # Return valid Uniones
                return [UNIONES_V4_COLUMNS]
            raise ValueError(f"Unknown sheet: {sheet_name}")

        mock_sheets_repo.read_worksheet = Mock(side_effect=mock_read_worksheet)

        # Run validation
        success, details = validate_v4_schema(repo=mock_sheets_repo)

        # Assert validation failed
        assert success is False, "Validation should fail with missing Metadata N_UNION column"

        # Assert Metadata status is FAIL
        assert details["Metadata"]["status"] == "FAIL"

        # Assert N_UNION is in missing list
        missing = details["Metadata"]["missing"]
        assert "N_UNION" in missing
        assert len(missing) == 1, "Only N_UNION should be missing"

        # Assert Operaciones and Uniones passed (to confirm isolation)
        assert details["Operaciones"]["status"] == "OK"
        assert details["Uniones"]["status"] == "OK"

    def test_startup_succeeds_all_columns_present(self, mock_sheets_repo):
        """
        Test that validation succeeds when all sheets have correct v4.0 schema.

        Scenario: All three sheets have all required columns.
        Expected: validate_v4_schema returns True with all statuses OK.
        """
        # Mock all sheets with complete v4.0 schema
        def mock_read_worksheet(sheet_name):
            if sheet_name == "Operaciones":
                operaciones_cols = (
                    OPERACIONES_V4_COLUMNS["v3.0_critical"] +
                    OPERACIONES_V4_COLUMNS["v4.0_new"]
                )
                return [operaciones_cols]
            elif sheet_name == "Uniones":
                return [UNIONES_V4_COLUMNS]
            elif sheet_name == "Metadata":
                metadata_cols = (
                    METADATA_V4_COLUMNS["v3.0_existing"] +
                    METADATA_V4_COLUMNS["v4.0_new"]
                )
                return [metadata_cols]
            raise ValueError(f"Unknown sheet: {sheet_name}")

        mock_sheets_repo.read_worksheet = Mock(side_effect=mock_read_worksheet)

        # Run validation
        success, details = validate_v4_schema(repo=mock_sheets_repo)

        # Assert validation succeeded
        assert success is True, "Validation should succeed with all v4.0 columns present"

        # Assert all sheets have OK status
        assert details["Operaciones"]["status"] == "OK"
        assert details["Uniones"]["status"] == "OK"
        assert details["Metadata"]["status"] == "OK"

        # Assert no missing columns
        assert details["Operaciones"]["missing"] == []
        assert details["Uniones"]["missing"] == []
        assert details["Metadata"]["missing"] == []

        # Assert validated counts are correct
        expected_operaciones_count = (
            len(OPERACIONES_V4_COLUMNS["v3.0_critical"]) +
            len(OPERACIONES_V4_COLUMNS["v4.0_new"])
        )
        assert details["Operaciones"]["validated_count"] == expected_operaciones_count
        assert details["Uniones"]["validated_count"] == len(UNIONES_V4_COLUMNS)

        expected_metadata_count = (
            len(METADATA_V4_COLUMNS["v3.0_existing"]) +
            len(METADATA_V4_COLUMNS["v4.0_new"])
        )
        assert details["Metadata"]["validated_count"] == expected_metadata_count

    def test_validation_handles_extra_columns_gracefully(self, mock_sheets_repo):
        """
        Test that validation succeeds even if sheets have extra columns.

        Scenario: Sheets have all required columns PLUS some extra ones.
        Expected: Validation passes (extra columns are OK, missing columns are not).
        """
        # Mock sheets with extra columns beyond required
        def mock_read_worksheet(sheet_name):
            if sheet_name == "Operaciones":
                operaciones_cols = (
                    OPERACIONES_V4_COLUMNS["v3.0_critical"] +
                    OPERACIONES_V4_COLUMNS["v4.0_new"] +
                    ["Extra_Column_1", "Extra_Column_2"]  # Extra columns
                )
                return [operaciones_cols]
            elif sheet_name == "Uniones":
                return [UNIONES_V4_COLUMNS + ["Extra_Union_Col"]]  # Extra column
            elif sheet_name == "Metadata":
                metadata_cols = (
                    METADATA_V4_COLUMNS["v3.0_existing"] +
                    METADATA_V4_COLUMNS["v4.0_new"] +
                    ["Extra_Metadata_Col"]  # Extra column
                )
                return [metadata_cols]
            raise ValueError(f"Unknown sheet: {sheet_name}")

        mock_sheets_repo.read_worksheet = Mock(side_effect=mock_read_worksheet)

        # Run validation
        success, details = validate_v4_schema(repo=mock_sheets_repo)

        # Assert validation succeeded (extra columns don't cause failure)
        assert success is True, "Validation should succeed with extra columns present"

        # Assert all sheets have OK status
        assert details["Operaciones"]["status"] == "OK"
        assert details["Uniones"]["status"] == "OK"
        assert details["Metadata"]["status"] == "OK"

        # Assert no missing columns
        assert details["Operaciones"]["missing"] == []
        assert details["Uniones"]["missing"] == []
        assert details["Metadata"]["missing"] == []

    def test_validation_case_insensitive_column_matching(self, mock_sheets_repo):
        """
        Test that column validation is case-insensitive and ignores underscores/spaces.

        Scenario: Headers have different casing/spacing than expected.
        Expected: Validation passes due to normalization.
        """
        # Mock sheets with different casing/spacing
        def mock_read_worksheet(sheet_name):
            if sheet_name == "Operaciones":
                # Mix of cases and spacing
                operaciones_cols = [
                    "tag_spool",  # lowercase
                    "ARMADOR",  # uppercase
                    "Soldador",  # normal
                    "fecha armado",  # space instead of underscore
                    "Fecha_Soldadura",  # normal
                    "ocupado por",  # space, lowercase
                    "FECHA_OCUPACION",  # uppercase
                    "VERSION",  # uppercase
                    "estado detalle",  # space, lowercase
                    "total uniones",  # space, lowercase (v4.0)
                    "Uniones ARM Completadas",  # spaces (v4.0)
                    "UNIONES_SOLD_COMPLETADAS",  # uppercase (v4.0)
                    "pulgadas_arm",  # lowercase (v4.0)
                    "Pulgadas SOLD"  # mixed case, space (v4.0)
                ]
                return [operaciones_cols]
            elif sheet_name == "Uniones":
                return [UNIONES_V4_COLUMNS]  # Normal case
            elif sheet_name == "Metadata":
                metadata_cols = (
                    METADATA_V4_COLUMNS["v3.0_existing"] +
                    METADATA_V4_COLUMNS["v4.0_new"]
                )
                return [metadata_cols]  # Normal case
            raise ValueError(f"Unknown sheet: {sheet_name}")

        mock_sheets_repo.read_worksheet = Mock(side_effect=mock_read_worksheet)

        # Run validation
        success, details = validate_v4_schema(repo=mock_sheets_repo)

        # Assert validation succeeded (normalization handled different cases)
        assert success is True, "Validation should succeed with case-insensitive matching"

        # Assert Operaciones passed despite different casing
        assert details["Operaciones"]["status"] == "OK"
        assert details["Operaciones"]["missing"] == []

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

    def test_validation_with_empty_sheet(self, mock_sheets_repo):
        """
        Test that validation fails gracefully when sheet is empty.

        Scenario: Sheet exists but has no rows (not even headers).
        Expected: Validation fails with appropriate error.
        """
        def mock_read_worksheet(sheet_name):
            if sheet_name == "Operaciones":
                return []  # Empty sheet
            elif sheet_name == "Uniones":
                return [UNIONES_V4_COLUMNS]
            elif sheet_name == "Metadata":
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
        assert success is False

        # Assert Operaciones failed with error
        assert details["Operaciones"]["status"] == "FAIL"
        # Empty sheet should have all columns missing
        expected_count = (
            len(OPERACIONES_V4_COLUMNS["v3.0_critical"]) +
            len(OPERACIONES_V4_COLUMNS["v4.0_new"])
        )
        assert len(details["Operaciones"]["missing"]) == expected_count
