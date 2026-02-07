#!/usr/bin/env python3
"""
Extend Metadata sheet with N_UNION column for ZEUES v4.0.

Adds N_UNION column at position 11 (end of sheet) to support granular
union-level audit trail. This column is nullable - spool-level events
have no union, while union-level events (UNION_ARM_REGISTRADA,
UNION_SOLD_REGISTRADA) populate with union number (1-20).

Usage:
    python backend/scripts/extend_metadata_schema.py --dry-run    # Simulate
    python backend/scripts/extend_metadata_schema.py              # Execute
    python backend/scripts/extend_metadata_schema.py --verbose    # Detailed logging
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


# Expected Metadata sheet structure (v3.0 has 10 columns)
EXISTING_COLUMNS = [
    "ID",
    "Timestamp",
    "Evento_Tipo",
    "TAG_SPOOL",
    "Worker_ID",
    "Worker_Nombre",
    "Operacion",
    "Accion",
    "Fecha_Operacion",
    "Metadata_JSON"
]

# New column for v4.0 (position 11)
NEW_COLUMN = {
    "name": "N_UNION",
    "position": 11,  # After Metadata_JSON
    "type": "integer",
    "nullable": True,
    "description": "Union number for granular events (NULL for spool-level events)"
}


def setup_logging(verbose: bool = False) -> None:
    """Configure logging output."""
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format='%(asctime)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )


def check_column_exists(repo: SheetsRepository, sheet_name: str, column_name: str) -> tuple[bool, int, list[str]]:
    """
    Check if N_UNION column already exists in Metadata sheet.

    Args:
        repo: SheetsRepository instance
        sheet_name: Name of sheet to check
        column_name: Column name to check for

    Returns:
        Tuple of (column_exists, current_column_count, headers)
    """
    logger = logging.getLogger(__name__)

    try:
        # Read sheet to get headers
        all_rows = repo.read_worksheet(sheet_name)
        if not all_rows:
            logger.error(f"Sheet '{sheet_name}' is empty")
            return False, 0, []

        headers = all_rows[0]
        column_count = len(headers)

        logger.debug(f"Current column count: {column_count}")
        logger.debug(f"Headers: {headers}")

        # Check if column exists (case-insensitive)
        column_exists = any(h.strip().lower() == column_name.lower() for h in headers)

        if column_exists:
            col_index = next(i for i, h in enumerate(headers) if h.strip().lower() == column_name.lower())
            logger.info(f"Column '{column_name}' already exists at position {col_index + 1}")

        return column_exists, column_count, headers

    except Exception as e:
        logger.error(f"Failed to check column existence: {e}")
        raise


def extend_schema(
    repo: SheetsRepository,
    sheet_name: str,
    dry_run: bool = False
) -> bool:
    """
    Add N_UNION column to Metadata sheet with idempotency.

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
        column_exists, current_count, headers = check_column_exists(
            repo, sheet_name, NEW_COLUMN["name"]
        )

        if column_exists:
            logger.info(f"N_UNION column already exists - no changes needed (idempotent)")
            return True

        # Validate current structure matches expected v3.0 schema
        if current_count != len(EXISTING_COLUMNS):
            logger.warning(
                f"Expected {len(EXISTING_COLUMNS)} columns (v3.0), found {current_count}. "
                f"Proceeding to add N_UNION at position {current_count + 1}."
            )

        new_position = current_count + 1
        logger.info(f"Current columns: {current_count}")
        logger.info(f"Adding '{NEW_COLUMN['name']}' at position {new_position}")

        if dry_run:
            logger.info("[DRY RUN] 1 column would be added to Metadata sheet")
            logger.info(f"[DRY RUN] Column: {NEW_COLUMN['name']} (position {new_position})")
            return True

        # Get worksheet for batch update
        spreadsheet = repo._get_spreadsheet()
        worksheet = spreadsheet.worksheet(sheet_name)

        # Expand sheet if needed
        new_total_columns = current_count + 1
        if worksheet.col_count < new_total_columns:
            logger.info(f"Expanding sheet from {worksheet.col_count} to {new_total_columns} columns...")
            worksheet.resize(rows=worksheet.row_count, cols=new_total_columns)
            logger.info(f"Sheet expanded to {new_total_columns} columns")

        # Prepare batch update for new column header
        col_letter = repo._index_to_column_letter(current_count)  # 0-indexed
        cell_address = f"{col_letter}1"

        updates = [{
            'range': cell_address,
            'values': [[NEW_COLUMN["name"]]]
        }]

        # Execute batch update
        logger.info(f"Adding column header at {cell_address}...")
        worksheet.batch_update(updates, value_input_option='USER_ENTERED')

        logger.info(f"Successfully added N_UNION column to '{sheet_name}'")

        # Log migration event
        try:
            log_migration_event(repo, sheet_name)
        except Exception as e:
            logger.warning(f"Failed to log migration event: {e}")

        return True

    except Exception as e:
        logger.error(f"Failed to extend schema: {e}")
        raise


def log_migration_event(repo: SheetsRepository, sheet_name: str) -> None:
    """
    Log migration event to Metadata sheet itself.

    Args:
        repo: SheetsRepository instance
        sheet_name: Name of sheet modified
    """
    logger = logging.getLogger(__name__)

    try:
        spreadsheet = repo._get_spreadsheet()
        metadata_sheet = spreadsheet.worksheet(sheet_name)

        # Prepare metadata row
        timestamp = datetime.utcnow().isoformat() + "Z"
        metadata_row = [
            "",  # ID (will be generated)
            timestamp,  # Timestamp
            "MIGRATION_V4_SCHEMA",  # Evento_Tipo
            "",  # TAG_SPOOL (N/A)
            0,  # Worker_ID (N/A)
            "SYSTEM",  # Worker_Nombre
            "MIGRATION",  # Operacion
            "ADD_N_UNION_COLUMN",  # Accion
            "",  # Fecha_Operacion (N/A)
            f'{{"sheet": "{sheet_name}", "column": "N_UNION", "position": 11}}',  # Metadata_JSON
            ""  # N_UNION (NULL for this event)
        ]

        # Append to Metadata
        metadata_sheet.append_row(metadata_row, value_input_option='USER_ENTERED')
        logger.debug("Logged migration event to Metadata")

    except Exception as e:
        logger.debug(f"Failed to log migration event: {e}")
        # Don't fail migration if logging fails


def main():
    """Main entry point for schema extension script."""
    parser = argparse.ArgumentParser(
        description="Extend Metadata sheet with N_UNION column for v4.0"
    )
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Simulate schema extension without making changes'
    )
    parser.add_argument(
        '--sheet-name',
        default=None,
        help=f'Sheet name to modify (default: {config.HOJA_METADATA_NOMBRE})'
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
    sheet_name = args.sheet_name or config.HOJA_METADATA_NOMBRE

    try:
        # Create repository
        logger.info("Connecting to Google Sheets...")
        repo = SheetsRepository()
        logger.info("Connected successfully")

        # Confirmation prompt (unless force or dry-run)
        if not args.force and not args.dry_run:
            print("\n⚠️  WARNING: This will modify the production spreadsheet")
            print(f"   Sheet: {sheet_name}")
            print(f"   Column to add: {NEW_COLUMN['name']} (position {NEW_COLUMN['position']})")
            print(f"   Description: {NEW_COLUMN['description']}")
            response = input("\nContinue? (yes/no): ")
            if response.lower() not in ['yes', 'y']:
                logger.info("Migration cancelled by user")
                return 0

        # Extend schema
        success = extend_schema(
            repo=repo,
            sheet_name=sheet_name,
            dry_run=args.dry_run
        )

        if success:
            if args.dry_run:
                logger.info("Dry run complete - no changes made")
            else:
                logger.info("Schema extension complete")
            return 0
        else:
            logger.error("Schema extension failed")
            return 1

    except Exception as e:
        logger.error(f"Script failed: {e}")
        if args.verbose:
            import traceback
            traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
