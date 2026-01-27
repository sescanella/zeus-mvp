#!/usr/bin/env python3
"""
Add Estado_Detalle column to Google Sheet for Phase 3 state machine.

Adds Estado_Detalle column at position 67 with idempotency.
Safe to run multiple times - checks if column already exists.

Usage:
    python backend/scripts/add_estado_detalle_column.py                  # Add column
    python backend/scripts/add_estado_detalle_column.py --dry-run        # Simulate
"""
import sys
import argparse
import logging
from datetime import datetime
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from backend.repositories.sheets_repository import SheetsRepository
from backend.config import config


# Estado_Detalle column definition
ESTADO_DETALLE_COLUMN = {
    "name": "Estado_Detalle",
    "type": "string",
    "description": "Combined state display (occupation + operation progress)",
    "position": 67  # After v3.0 columns (64-66)
}


def setup_logging(verbose: bool = False) -> None:
    """Configure logging output."""
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format='%(asctime)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )


def check_column_exists(repo: SheetsRepository, sheet_name: str) -> tuple[bool, int, list[str]]:
    """
    Check if Estado_Detalle column already exists in sheet.

    Args:
        repo: SheetsRepository instance
        sheet_name: Name of sheet to check

    Returns:
        Tuple of (column_exists, current_column_count, existing_headers)
    """
    logger = logging.getLogger(__name__)

    try:
        # Read sheet to get headers
        all_rows = repo.read_worksheet(sheet_name)
        if not all_rows:
            logger.error(f"❌ Sheet '{sheet_name}' is empty")
            return False, 0, []

        headers = all_rows[0]
        column_count = len(headers)

        logger.debug(f"Current column count: {column_count}")
        logger.debug(f"Last 5 columns: {headers[-5:]}")

        # Check if Estado_Detalle exists
        column_exists = ESTADO_DETALLE_COLUMN["name"] in headers

        if column_exists:
            col_index = headers.index(ESTADO_DETALLE_COLUMN["name"])
            logger.info(f"✅ Estado_Detalle column already exists at position {col_index + 1}")

        return column_exists, column_count, headers

    except Exception as e:
        logger.error(f"❌ Failed to check columns: {e}")
        raise


def add_column(
    repo: SheetsRepository,
    sheet_name: str,
    dry_run: bool = False
) -> bool:
    """
    Add Estado_Detalle column to sheet with idempotency.

    Args:
        repo: SheetsRepository instance
        sheet_name: Name of sheet to modify
        dry_run: If True, simulate without making changes

    Returns:
        True if column was added or already exists
    """
    logger = logging.getLogger(__name__)

    try:
        # Check if column already exists
        column_exists, current_count, headers = check_column_exists(repo, sheet_name)

        if column_exists:
            logger.info("✅ Column already exists - no changes needed (idempotent)")
            return True

        # Calculate new column position
        # Should be at position 67 (after v3.0 columns at 64-66)
        target_position = ESTADO_DETALLE_COLUMN["position"]
        new_total_columns = max(current_count + 1, target_position)

        logger.info(f"Current columns: {current_count}")
        logger.info(f"Adding: {ESTADO_DETALLE_COLUMN['name']} at position {target_position}")
        logger.info(f"New total columns: {new_total_columns}")

        if dry_run:
            logger.info("[DRY RUN] Would add column (no changes made)")
            return True

        # Get worksheet for batch update
        spreadsheet = repo._get_spreadsheet()
        worksheet = spreadsheet.worksheet(sheet_name)

        # First, expand the sheet's column count if needed
        current_col_count = worksheet.col_count
        if current_col_count < new_total_columns:
            logger.info(f"Expanding sheet from {current_col_count} to {new_total_columns} columns...")
            worksheet.resize(rows=worksheet.row_count, cols=new_total_columns)
            logger.info(f"✅ Sheet expanded to {new_total_columns} columns")

        # Add column header to row 1
        col_letter = repo._index_to_column_letter(target_position - 1)  # Convert to 0-indexed
        cell_address = f"{col_letter}1"

        logger.info(f"Adding column header at {cell_address}...")
        worksheet.update(cell_address, [[ESTADO_DETALLE_COLUMN["name"]]], value_input_option='USER_ENTERED')

        logger.info(f"✅ Successfully added '{ESTADO_DETALLE_COLUMN['name']}' column to '{sheet_name}'")

        # Log operation to Metadata sheet (if exists)
        try:
            log_migration_event(repo, sheet_name)
        except Exception as e:
            logger.warning(f"Failed to log to Metadata: {e}")

        return True

    except Exception as e:
        logger.error(f"❌ Failed to add column: {e}")
        raise


def log_migration_event(repo: SheetsRepository, sheet_name: str) -> None:
    """
    Log migration event to Metadata sheet.

    Args:
        repo: SheetsRepository instance
        sheet_name: Name of sheet modified
    """
    logger = logging.getLogger(__name__)

    try:
        # Check if Metadata sheet exists
        spreadsheet = repo._get_spreadsheet()
        try:
            metadata_sheet = spreadsheet.worksheet(config.HOJA_METADATA_NOMBRE)
        except Exception:
            logger.debug("Metadata sheet not found - skipping log")
            return

        # Prepare metadata row
        timestamp = datetime.utcnow().isoformat() + "Z"
        metadata_row = [
            "",  # id (will be generated)
            timestamp,  # timestamp
            "MIGRATION_ESTADO_DETALLE",  # evento_tipo
            "",  # tag_spool (N/A)
            0,  # worker_id (N/A)
            "SYSTEM",  # worker_nombre
            "MIGRATION",  # operacion
            "ADD_COLUMN",  # accion
            "",  # fecha_operacion (N/A)
            f'{{"sheet": "{sheet_name}", "column": "{ESTADO_DETALLE_COLUMN["name"]}", "position": {ESTADO_DETALLE_COLUMN["position"]}}}'  # metadata_json
        ]

        # Append to Metadata
        metadata_sheet.append_row(metadata_row, value_input_option='USER_ENTERED')
        logger.debug("✅ Logged migration event to Metadata")

    except Exception as e:
        logger.debug(f"Failed to log migration: {e}")
        # Don't fail migration if logging fails


def main():
    """Main entry point for column addition script."""
    parser = argparse.ArgumentParser(
        description="Add Estado_Detalle column to ZEUES Google Sheet"
    )
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Simulate column addition without making changes'
    )
    parser.add_argument(
        '--sheet-name',
        default=None,
        help=f'Sheet name to modify (default: {config.HOJA_OPERACIONES_NOMBRE})'
    )
    parser.add_argument(
        '--verbose',
        action='store_true',
        help='Enable verbose logging'
    )
    parser.add_argument(
        '--force',
        action='store_true',
        help='Skip confirmation prompts'
    )

    args = parser.parse_args()

    setup_logging(args.verbose)
    logger = logging.getLogger(__name__)

    # Get sheet name
    sheet_name = args.sheet_name or config.HOJA_OPERACIONES_NOMBRE

    try:
        # Create repository
        logger.info("Connecting to Google Sheets...")
        repo = SheetsRepository()
        logger.info("✅ Connected successfully")

        # Confirmation prompt (unless force or dry-run)
        if not args.force and not args.dry_run:
            print("\n⚠️  WARNING: This will modify the production spreadsheet")
            print(f"   Sheet: {sheet_name}")
            print(f"   Column to add: {ESTADO_DETALLE_COLUMN['name']} at position {ESTADO_DETALLE_COLUMN['position']}")
            response = input("\nContinue? (yes/no): ")
            if response.lower() not in ['yes', 'y']:
                logger.info("Migration cancelled by user")
                return 0

        # Add column
        success = add_column(
            repo=repo,
            sheet_name=sheet_name,
            dry_run=args.dry_run
        )

        if success:
            if args.dry_run:
                logger.info("✅ Dry run complete - no changes made")
            else:
                logger.info("✅ Migration complete")
            return 0
        else:
            logger.error("❌ Migration failed")
            return 1

    except Exception as e:
        logger.error(f"❌ Script failed: {e}")
        if args.verbose:
            import traceback
            traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
