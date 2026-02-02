#!/usr/bin/env python3
"""
Validate Uniones sheet structure for ZEUES v4.0.

Validates that the Uniones sheet exists and has the correct 18-column structure
as specified in v4.0 requirements. This sheet is pre-populated by Engineering
external process and must be validated before v4.0 deployment.

Usage:
    python backend/scripts/validate_uniones_sheet.py                    # Validate structure
    python backend/scripts/validate_uniones_sheet.py --fix              # Add missing column headers
    python backend/scripts/validate_uniones_sheet.py --fix --dry-run    # Simulate fix without changes
    python backend/scripts/validate_uniones_sheet.py --verbose          # Detailed logging

Notes:
    - --fix adds column headers only (structure), not data
    - Engineering must populate data after headers are added
    - --dry-run simulates changes without modifying sheet
"""
import sys
import argparse
import logging
from pathlib import Path
from typing import Optional

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from backend.repositories.sheets_repository import SheetsRepository


# Expected Uniones sheet structure (18 columns)
EXPECTED_COLUMNS = [
    # Core fields (1-5)
    "ID",
    "TAG_SPOOL",
    "N_UNION",
    "DN_UNION",
    "TIPO_UNION",
    # ARM timestamps (6-8)
    "ARM_FECHA_INICIO",
    "ARM_FECHA_FIN",
    "ARM_WORKER",
    # SOLD timestamps (9-11)
    "SOL_FECHA_INICIO",
    "SOL_FECHA_FIN",
    "SOL_WORKER",
    # NDT fields (12-13)
    "NDT_FECHA",
    "NDT_STATUS",
    # Audit columns (14-18)
    "version",
    "Creado_Por",
    "Fecha_Creacion",
    "Modificado_Por",
    "Fecha_Modificacion"
]


def setup_logging(verbose: bool = False) -> None:
    """Configure logging output."""
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format='%(asctime)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )


def normalize_column_name(name: str) -> str:
    """
    Normalize column name for comparison (lowercase, no spaces/underscores).

    Args:
        name: Column name to normalize

    Returns:
        Normalized column name

    Examples:
        >>> normalize_column_name("ARM_FECHA_INICIO")
        'armfechainicio'
        >>> normalize_column_name("Creado Por")
        'creadopor'
    """
    return name.lower().replace(" ", "").replace("_", "")


def validate_sheet_structure(repo: SheetsRepository, sheet_name: str = "Uniones") -> tuple[bool, dict]:
    """
    Validate Uniones sheet structure against expected schema.

    Args:
        repo: SheetsRepository instance
        sheet_name: Name of sheet to validate (default: "Uniones")

    Returns:
        Tuple of (is_valid, details_dict)
        details_dict contains:
            - column_count: int
            - missing_columns: list[str]
            - extra_columns: list[str]
            - headers: list[str]
    """
    logger = logging.getLogger(__name__)

    try:
        # Check if sheet exists
        try:
            all_rows = repo.read_worksheet(sheet_name)
        except Exception as e:
            logger.error(f"Sheet '{sheet_name}' not found: {e}")
            return False, {
                "error": f"Sheet not found: {e}",
                "column_count": 0,
                "missing_columns": EXPECTED_COLUMNS,
                "extra_columns": [],
                "headers": []
            }

        if not all_rows or len(all_rows) == 0:
            logger.error(f"Sheet '{sheet_name}' is empty")
            return False, {
                "error": "Sheet is empty",
                "column_count": 0,
                "missing_columns": EXPECTED_COLUMNS,
                "extra_columns": [],
                "headers": []
            }

        # Get headers from row 1
        headers = all_rows[0]
        column_count = len(headers)

        logger.debug(f"Found {column_count} columns in '{sheet_name}'")
        logger.debug(f"Headers: {headers}")

        # Normalize headers for comparison
        normalized_headers = {normalize_column_name(h): h for h in headers}
        normalized_expected = {normalize_column_name(c): c for c in EXPECTED_COLUMNS}

        # Find missing columns
        missing_columns = []
        for norm_name, original_name in normalized_expected.items():
            if norm_name not in normalized_headers:
                missing_columns.append(original_name)

        # Find extra columns
        extra_columns = []
        for norm_name, original_name in normalized_headers.items():
            if norm_name not in normalized_expected:
                extra_columns.append(original_name)

        # Validate column count
        is_valid = (column_count == len(EXPECTED_COLUMNS) and
                    len(missing_columns) == 0 and
                    len(extra_columns) == 0)

        details = {
            "column_count": column_count,
            "missing_columns": missing_columns,
            "extra_columns": extra_columns,
            "headers": headers
        }

        return is_valid, details

    except Exception as e:
        logger.error(f"Failed to validate sheet structure: {e}")
        return False, {
            "error": str(e),
            "column_count": 0,
            "missing_columns": EXPECTED_COLUMNS,
            "extra_columns": [],
            "headers": []
        }


def fix_missing_columns(repo: SheetsRepository, missing_columns: list[str], sheet_name: str = "Uniones", dry_run: bool = False) -> bool:
    """
    Add missing column headers to Uniones sheet.

    Args:
        repo: SheetsRepository instance
        missing_columns: List of column names to add
        sheet_name: Name of sheet to modify
        dry_run: If True, simulate without modifying sheet

    Returns:
        True if columns were added successfully (or would be added in dry-run)
    """
    logger = logging.getLogger(__name__)

    try:
        if not missing_columns:
            logger.info("No missing columns to add")
            return True

        if dry_run:
            logger.info(f"[DRY RUN] Would add {len(missing_columns)} missing columns:")
            for col in missing_columns:
                logger.info(f"  - {col}")
            logger.warning("[DRY RUN] No changes made to sheet")
            return True

        logger.info(f"Adding {len(missing_columns)} missing columns...")

        # Get current headers
        all_rows = repo.read_worksheet(sheet_name)
        headers = all_rows[0]
        current_count = len(headers)

        # Get worksheet for batch update
        spreadsheet = repo._get_spreadsheet()
        worksheet = spreadsheet.worksheet(sheet_name)

        # Calculate new total columns
        new_total_columns = current_count + len(missing_columns)

        # Expand sheet if needed
        if worksheet.col_count < new_total_columns:
            logger.info(f"Expanding sheet from {worksheet.col_count} to {new_total_columns} columns...")
            worksheet.resize(rows=worksheet.row_count, cols=new_total_columns)

        # Prepare batch update for missing headers
        updates = []
        for i, col_name in enumerate(missing_columns):
            col_letter = repo._index_to_column_letter(current_count + i)
            cell_address = f"{col_letter}1"
            updates.append({
                'range': cell_address,
                'values': [[col_name]]
            })
            logger.info(f"  Column {current_count + i + 1} ({col_letter}1): {col_name}")

        # Execute batch update
        logger.info(f"Executing batch update for {len(updates)} column headers...")
        worksheet.batch_update(updates, value_input_option='USER_ENTERED')

        logger.info(f"Successfully added {len(missing_columns)} columns")
        logger.warning("IMPORTANT: Column headers added, but Engineering must populate data")
        return True

    except Exception as e:
        logger.error(f"Failed to add missing columns: {e}")
        return False


def main():
    """Main entry point for validation script."""
    parser = argparse.ArgumentParser(
        description="Validate Uniones sheet structure for ZEUES v4.0"
    )
    parser.add_argument(
        '--fix',
        action='store_true',
        help='Add missing column headers (structure only, no data migration)'
    )
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Simulate fix without modifying sheet (requires --fix)'
    )
    parser.add_argument(
        '--sheet-name',
        default='Uniones',
        help='Sheet name to validate (default: Uniones)'
    )
    parser.add_argument(
        '--verbose',
        action='store_true',
        help='Enable verbose logging'
    )

    args = parser.parse_args()

    setup_logging(args.verbose)
    logger = logging.getLogger(__name__)

    try:
        # Create repository
        logger.info("Connecting to Google Sheets...")
        repo = SheetsRepository()
        logger.info("Connected successfully")

        # Validate sheet structure
        logger.info(f"Validating '{args.sheet_name}' sheet structure...")
        is_valid, details = validate_sheet_structure(repo, args.sheet_name)

        # Report results
        if is_valid:
            logger.info(f"Uniones sheet valid: {details['column_count']} columns found")
            logger.info("All expected columns present")
            return 0
        else:
            # Report structural issues
            if "error" in details:
                logger.error(f"Validation error: {details['error']}")
                return 1

            logger.warning(f"Sheet validation failed:")
            logger.warning(f"  Expected columns: {len(EXPECTED_COLUMNS)}")
            logger.warning(f"  Found columns: {details['column_count']}")

            if details['missing_columns']:
                logger.warning(f"  Missing columns ({len(details['missing_columns'])}):")
                for col in details['missing_columns']:
                    logger.warning(f"    - {col}")

            if details['extra_columns']:
                logger.warning(f"  Extra columns ({len(details['extra_columns'])}):")
                for col in details['extra_columns']:
                    logger.warning(f"    - {col}")

            # Fix if requested
            if args.fix and details['missing_columns']:
                if args.dry_run:
                    logger.info("Simulating column header addition...")
                    success = fix_missing_columns(repo, details['missing_columns'], args.sheet_name, dry_run=True)
                    if success:
                        logger.info("[DRY RUN] Simulation successful - run without --dry-run to apply changes")
                        return 0
                    else:
                        logger.error("[DRY RUN] Simulation failed")
                        return 1
                else:
                    logger.info("Attempting to add missing columns...")
                    success = fix_missing_columns(repo, details['missing_columns'], args.sheet_name, dry_run=False)
                    if success:
                        logger.info("Missing columns added successfully")
                        # Re-validate
                        is_valid, details = validate_sheet_structure(repo, args.sheet_name)
                        if is_valid:
                            logger.info("Sheet validation passed after fix")
                            logger.info("Next step: Engineering must populate data in new columns")
                            return 0
                        else:
                            logger.error("Sheet validation still failing after fix")
                            return 1
                    else:
                        logger.error("Failed to add missing columns")
                        return 1
            elif args.fix and not details['missing_columns']:
                logger.info("No missing columns to add (--fix has no effect)")
                return 1

            return 1

    except Exception as e:
        logger.error(f"Script failed: {e}")
        if args.verbose:
            import traceback
            traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
