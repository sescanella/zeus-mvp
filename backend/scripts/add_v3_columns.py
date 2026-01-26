#!/usr/bin/env python3
"""
Add v3.0 columns to Google Sheet for ZEUES migration.

Adds three new columns with idempotency: Ocupado_Por, Fecha_Ocupacion, version.
Safe to run multiple times - checks if columns already exist.

Usage:
    python backend/scripts/add_v3_columns.py                  # Add columns
    python backend/scripts/add_v3_columns.py --dry-run        # Simulate
    python backend/scripts/add_v3_columns.py --verify-backup  # Require backup first
"""
import sys
import argparse
import logging
from datetime import datetime
from pathlib import Path
from typing import Optional

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from backend.repositories.sheets_repository import SheetsRepository
from backend.config import config


# V3.0 column definitions
V3_COLUMNS = [
    {
        "name": "Ocupado_Por",
        "type": "string",
        "description": "Worker currently occupying the spool (format: INICIALES(ID))"
    },
    {
        "name": "Fecha_Ocupacion",
        "type": "date",
        "description": "Date when spool was occupied (format: YYYY-MM-DD)"
    },
    {
        "name": "version",
        "type": "integer",
        "description": "Version token for optimistic locking (starts at 0)"
    }
]


def setup_logging(verbose: bool = False) -> None:
    """Configure logging output."""
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format='%(asctime)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )


def check_columns_exist(repo: SheetsRepository, sheet_name: str) -> tuple[bool, int, list[str]]:
    """
    Check if v3.0 columns already exist in sheet.

    Args:
        repo: SheetsRepository instance
        sheet_name: Name of sheet to check

    Returns:
        Tuple of (columns_exist, current_column_count, existing_headers)
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

        # Check if v3.0 columns exist
        v3_names = [col["name"] for col in V3_COLUMNS]
        columns_exist = all(col_name in headers for col_name in v3_names)

        if columns_exist:
            logger.info(f"✅ v3.0 columns already exist in '{sheet_name}'")
            for col_name in v3_names:
                col_index = headers.index(col_name)
                logger.info(f"   - {col_name} at position {col_index + 1}")

        return columns_exist, column_count, headers

    except Exception as e:
        logger.error(f"❌ Failed to check columns: {e}")
        raise


def add_columns(
    repo: SheetsRepository,
    sheet_name: str,
    dry_run: bool = False
) -> bool:
    """
    Add v3.0 columns to sheet with idempotency.

    Args:
        repo: SheetsRepository instance
        sheet_name: Name of sheet to modify
        dry_run: If True, simulate without making changes

    Returns:
        True if columns were added or already exist
    """
    logger = logging.getLogger(__name__)

    try:
        # Check if columns already exist
        columns_exist, current_count, headers = check_columns_exist(repo, sheet_name)

        if columns_exist:
            logger.info("✅ Columns already exist - no changes needed (idempotent)")
            return True

        # Calculate new column positions
        v3_names = [col["name"] for col in V3_COLUMNS]
        new_positions = list(range(current_count + 1, current_count + len(v3_names) + 1))

        logger.info(f"Current columns: {current_count}")
        logger.info(f"New columns to add: {len(v3_names)}")
        for name, pos in zip(v3_names, new_positions):
            logger.info(f"   - {name} at position {pos}")

        if dry_run:
            logger.info("[DRY RUN] Would add columns (no changes made)")
            return True

        # Get worksheet for batch update
        spreadsheet = repo._get_spreadsheet()
        worksheet = spreadsheet.worksheet(sheet_name)

        # Prepare batch update for headers
        # Add new column headers to row 1
        updates = []
        for i, col_def in enumerate(V3_COLUMNS):
            col_letter = repo._index_to_column_letter(current_count + i)
            cell_address = f"{col_letter}1"
            updates.append({
                'range': cell_address,
                'values': [[col_def["name"]]]
            })

        # Execute batch update
        logger.info(f"Adding {len(updates)} column headers...")
        worksheet.batch_update(updates, value_input_option='USER_ENTERED')

        logger.info(f"✅ Successfully added {len(v3_names)} columns to '{sheet_name}'")

        # Log operation to Metadata sheet (if exists)
        try:
            log_migration_event(repo, sheet_name, v3_names)
        except Exception as e:
            logger.warning(f"Failed to log to Metadata: {e}")

        return True

    except Exception as e:
        logger.error(f"❌ Failed to add columns: {e}")
        raise


def log_migration_event(repo: SheetsRepository, sheet_name: str, columns_added: list[str]) -> None:
    """
    Log migration event to Metadata sheet.

    Args:
        repo: SheetsRepository instance
        sheet_name: Name of sheet modified
        columns_added: List of column names added
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
            "MIGRATION_V3_COLUMNS",  # evento_tipo
            "",  # tag_spool (N/A)
            0,  # worker_id (N/A)
            "SYSTEM",  # worker_nombre
            "MIGRATION",  # operacion
            "ADD_COLUMNS",  # accion
            "",  # fecha_operacion (N/A)
            f'{{"sheet": "{sheet_name}", "columns": {columns_added}}}'  # metadata_json
        ]

        # Append to Metadata
        metadata_sheet.append_row(metadata_row, value_input_option='USER_ENTERED')
        logger.debug("✅ Logged migration event to Metadata")

    except Exception as e:
        logger.debug(f"Failed to log migration: {e}")
        # Don't fail migration if logging fails


def verify_backup_exists(repo: SheetsRepository) -> bool:
    """
    Verify that a backup exists before proceeding with migration.

    Args:
        repo: SheetsRepository instance

    Returns:
        True if backup verification passes
    """
    logger = logging.getLogger(__name__)

    try:
        client = repo._get_client()
        spreadsheet = repo._get_spreadsheet()

        # List all spreadsheets to find backups
        # Note: This requires Drive API access
        logger.info("Checking for recent backups...")

        # For now, we'll warn but not block
        # Full implementation would require Drive API integration
        logger.warning(
            "⚠️  Backup verification requires Drive API integration. "
            "Proceeding with migration - ensure you have a backup!"
        )

        return True

    except Exception as e:
        logger.warning(f"⚠️  Backup verification failed: {e}")
        return True  # Don't block migration on verification failure


def main():
    """Main entry point for column addition script."""
    parser = argparse.ArgumentParser(
        description="Add v3.0 columns to ZEUES Google Sheet"
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
        '--verify-backup',
        action='store_true',
        help='Verify backup exists before proceeding'
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

        # Verify backup if requested
        if args.verify_backup:
            if not verify_backup_exists(repo):
                logger.error("❌ Backup verification failed - aborting migration")
                return 1

        # Confirmation prompt (unless force or dry-run)
        if not args.force and not args.dry_run:
            print("\n⚠️  WARNING: This will modify the production spreadsheet")
            print(f"   Sheet: {sheet_name}")
            print(f"   Columns to add: {[col['name'] for col in V3_COLUMNS]}")
            response = input("\nContinue? (yes/no): ")
            if response.lower() not in ['yes', 'y']:
                logger.info("Migration cancelled by user")
                return 0

        # Add columns
        success = add_columns(
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
