#!/usr/bin/env python3
"""
Extend Operaciones sheet with union metric aggregation columns for v4.0.

Adds 5 new columns (68-72) for union-level tracking:
- Total_Uniones: Count of unions for this spool
- Uniones_ARM_Completadas: Count where ARM_FECHA_FIN != NULL
- Uniones_SOLD_Completadas: Count where SOL_FECHA_FIN != NULL
- Pulgadas_ARM: Sum of DN_UNION where ARM completed
- Pulgadas_SOLD: Sum of DN_UNION where SOLD completed

Idempotent: Safe to run multiple times - checks if columns already exist.

Usage:
    python backend/scripts/extend_operaciones_schema.py                  # Add columns
    python backend/scripts/extend_operaciones_schema.py --dry-run        # Simulate
"""
import sys
import argparse
import logging
from datetime import datetime
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from backend.repositories.sheets_repository import SheetsRepository
from backend.core.column_map_cache import ColumnMapCache
from backend.config import config


# v4.0 metric aggregation columns
V4_METRIC_COLUMNS = [
    {
        "name": "Total_Uniones",
        "type": "integer",
        "description": "Count of unions for this spool",
        "position": 68,
        "default": "0"
    },
    {
        "name": "Uniones_ARM_Completadas",
        "type": "integer",
        "description": "Count of unions where ARM_FECHA_FIN is not null",
        "position": 69,
        "default": "0"
    },
    {
        "name": "Uniones_SOLD_Completadas",
        "type": "integer",
        "description": "Count of unions where SOL_FECHA_FIN is not null",
        "position": 70,
        "default": "0"
    },
    {
        "name": "Pulgadas_ARM",
        "type": "float",
        "description": "Sum of DN_UNION where ARM completed",
        "position": 71,
        "default": "0"
    },
    {
        "name": "Pulgadas_SOLD",
        "type": "float",
        "description": "Sum of DN_UNION where SOLD completed",
        "position": 72,
        "default": "0"
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


def check_columns_exist(repo: SheetsRepository, sheet_name: str) -> tuple[bool, int, list[str], list[str]]:
    """
    Check which v4.0 metric columns already exist in sheet.

    Args:
        repo: SheetsRepository instance
        sheet_name: Name of sheet to check

    Returns:
        Tuple of (all_exist, current_column_count, existing_headers, missing_columns)
    """
    logger = logging.getLogger(__name__)

    try:
        # Read sheet to get headers
        all_rows = repo.read_worksheet(sheet_name)
        if not all_rows:
            logger.error(f"❌ Sheet '{sheet_name}' is empty")
            return False, 0, [], [col["name"] for col in V4_METRIC_COLUMNS]

        headers = all_rows[0]
        column_count = len(headers)

        logger.debug(f"Current column count: {column_count}")
        logger.debug(f"Last 5 columns: {headers[-5:]}")

        # Check which columns exist
        missing_columns = []
        for col_def in V4_METRIC_COLUMNS:
            if col_def["name"] not in headers:
                missing_columns.append(col_def["name"])
            else:
                col_index = headers.index(col_def["name"])
                logger.info(f"✅ {col_def['name']} already exists at position {col_index + 1}")

        all_exist = len(missing_columns) == 0

        if all_exist:
            logger.info(f"✅ All {len(V4_METRIC_COLUMNS)} v4.0 metric columns already exist")
        else:
            logger.info(f"📋 {len(missing_columns)} columns need to be added: {missing_columns}")

        return all_exist, column_count, headers, missing_columns

    except Exception as e:
        logger.error(f"❌ Failed to check columns: {e}")
        raise


def add_columns(
    repo: SheetsRepository,
    sheet_name: str,
    dry_run: bool = False
) -> bool:
    """
    Add v4.0 metric columns to sheet with idempotency.

    Args:
        repo: SheetsRepository instance
        sheet_name: Name of sheet to modify
        dry_run: If True, simulate without making changes

    Returns:
        True if columns were added or already exist
    """
    logger = logging.getLogger(__name__)

    try:
        # Check which columns need to be added
        all_exist, current_count, headers, missing_columns = check_columns_exist(repo, sheet_name)

        if all_exist:
            logger.info("✅ All columns already exist - no changes needed (idempotent)")
            return True

        # Calculate new column positions
        target_position = V4_METRIC_COLUMNS[-1]["position"]
        new_total_columns = max(current_count + len(missing_columns), target_position)

        logger.info(f"Current columns: {current_count}")
        logger.info(f"Adding: {len(missing_columns)} columns")
        logger.info(f"New total columns: {new_total_columns}")

        if dry_run:
            logger.info(f"[DRY RUN] Would add {len(missing_columns)} columns (no changes made)")
            for col_def in V4_METRIC_COLUMNS:
                if col_def["name"] in missing_columns:
                    logger.info(f"  - {col_def['name']} at position {col_def['position']}")
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

        # Prepare batch updates for headers and default values
        row_count = len(all_rows := repo.read_worksheet(sheet_name))
        batch_updates = []

        for col_def in V4_METRIC_COLUMNS:
            if col_def["name"] not in missing_columns:
                continue  # Skip columns that already exist

            col_letter = repo._index_to_column_letter(col_def["position"] - 1)  # Convert to 0-indexed

            # Add header at row 1
            header_range = f"{col_letter}1"
            batch_updates.append({
                'range': header_range,
                'values': [[col_def["name"]]]
            })
            logger.debug(f"Queued header update: {col_def['name']} at {header_range}")

            # Add default values for all data rows (row 2 onwards)
            if row_count > 1:
                data_range = f"{col_letter}2:{col_letter}{row_count}"
                default_values = [[col_def["default"]]] * (row_count - 1)
                batch_updates.append({
                    'range': data_range,
                    'values': default_values
                })
                logger.debug(f"Queued data update: {row_count - 1} rows with default '{col_def['default']}'")

        # Execute all updates in a single batch call
        if batch_updates:
            logger.info(f"Executing batch update with {len(batch_updates)} operations...")
            worksheet.batch_update(batch_updates, value_input_option='USER_ENTERED')
            logger.info(f"✅ Successfully added {len(missing_columns)} columns to '{sheet_name}'")

        # Invalidate column map cache to pick up new columns
        ColumnMapCache.invalidate(sheet_name)
        logger.info(f"✅ Cache invalidated for '{sheet_name}' - next read will rebuild mapping")

        # Log operation to Metadata sheet (if exists)
        try:
            log_migration_event(repo, sheet_name, missing_columns)
        except Exception as e:
            logger.warning(f"Failed to log to Metadata: {e}")

        return True

    except Exception as e:
        logger.error(f"❌ Failed to add columns: {e}")
        raise


def log_migration_event(repo: SheetsRepository, sheet_name: str, added_columns: list[str]) -> None:
    """
    Log migration event to Metadata sheet.

    Args:
        repo: SheetsRepository instance
        sheet_name: Name of sheet modified
        added_columns: List of column names that were added
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
            "MIGRATION_V4_METRICS",  # evento_tipo
            "",  # tag_spool (N/A)
            0,  # worker_id (N/A)
            "SYSTEM",  # worker_nombre
            "MIGRATION",  # operacion
            "ADD_COLUMNS",  # accion
            "",  # fecha_operacion (N/A)
            f'{{"sheet": "{sheet_name}", "columns_added": {added_columns}, "phase": "07-data-model-foundation"}}'  # metadata_json
        ]

        # Append to Metadata
        metadata_sheet.append_row(metadata_row, value_input_option='USER_ENTERED')
        logger.debug("✅ Logged migration event to Metadata")

    except Exception as e:
        logger.debug(f"Failed to log migration: {e}")
        # Don't fail migration if logging fails


def main():
    """Main entry point for schema extension script."""
    parser = argparse.ArgumentParser(
        description="Extend Operaciones sheet with v4.0 union metric columns"
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
            print(f"   Columns to add: {len(V4_METRIC_COLUMNS)} metric aggregation columns (68-72)")
            print(f"   Columns: {', '.join([col['name'] for col in V4_METRIC_COLUMNS])}")
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
