#!/usr/bin/env python3
"""
Backup Google Sheet script for ZEUES v3.0 migration.

Creates complete copy of production spreadsheet with timestamp.
Stores backup in Google Drive folder for rollback capability.

Usage:
    python backend/scripts/backup_sheet.py                  # Create backup
    python backend/scripts/backup_sheet.py --dry-run        # Simulate backup
"""
import sys
import argparse
import logging
from datetime import datetime
from pathlib import Path
from typing import Optional

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

import gspread
from google.oauth2.service_account import Credentials

from backend.config import config


def setup_logging(verbose: bool = False) -> None:
    """Configure logging output."""
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format='%(asctime)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )


def get_gspread_client() -> gspread.Client:
    """
    Create authenticated gspread client.

    Returns:
        Authenticated gspread.Client

    Raises:
        ValueError: If credentials not found
        Exception: If authentication fails
    """
    creds_dict = config.get_credentials_dict()
    if not creds_dict:
        raise ValueError(
            "Google Service Account credentials not found. "
            "Check GOOGLE_APPLICATION_CREDENTIALS_JSON or local JSON file."
        )

    # Create credentials with Drive API scope for copying
    creds = Credentials.from_service_account_info(
        creds_dict,
        scopes=config.get_scopes()
    )

    return gspread.authorize(creds)


def create_backup(
    client: gspread.Client,
    sheet_id: str,
    backup_folder_id: Optional[str] = None,
    dry_run: bool = False
) -> Optional[str]:
    """
    Create complete copy of Google Sheet with timestamp.

    Uses Sheets API only (not Drive API copy) to avoid permission issues.
    Creates new spreadsheet and copies all worksheets with data.

    Args:
        client: Authenticated gspread client
        sheet_id: ID of sheet to backup
        backup_folder_id: Google Drive folder ID for backups (optional)
        dry_run: If True, simulate without creating backup

    Returns:
        Backup spreadsheet ID if created, None if dry run

    Raises:
        gspread.exceptions.SpreadsheetNotFound: If sheet not found
        Exception: If backup creation fails
    """
    logger = logging.getLogger(__name__)

    try:
        # Open source spreadsheet
        logger.info(f"Opening spreadsheet: {sheet_id}")
        spreadsheet = client.open_by_key(sheet_id)
        logger.info(f"✅ Spreadsheet opened: {spreadsheet.title}")

        # Generate backup name with timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_name = f"{spreadsheet.title}_v2.1_backup_{timestamp}"

        worksheets = spreadsheet.worksheets()
        logger.info(f"Source has {len(worksheets)} worksheets")

        if dry_run:
            logger.info(f"[DRY RUN] Would create backup: {backup_name}")
            if backup_folder_id:
                logger.info(f"[DRY RUN] Would store in folder: {backup_folder_id}")
            else:
                logger.info(f"[DRY RUN] Would store in root Drive")
            logger.info(f"[DRY RUN] Would copy {len(worksheets)} worksheets")
            for ws in worksheets:
                logger.info(f"[DRY RUN]   - {ws.title} ({ws.row_count} rows x {ws.col_count} cols)")
            return None

        # Create new spreadsheet using Sheets API only
        logger.info(f"Creating backup spreadsheet: {backup_name}")
        backup = client.create(backup_name)
        backup_id = backup.id
        logger.info(f"✅ Backup spreadsheet created: {backup_id}")

        # Copy each worksheet
        for idx, source_ws in enumerate(worksheets):
            logger.info(f"Copying worksheet {idx+1}/{len(worksheets)}: {source_ws.title}")

            # Get all data from source worksheet
            all_data = source_ws.get_all_values()
            row_count = len(all_data)
            col_count = len(all_data[0]) if all_data else 0

            logger.info(f"  Reading {row_count} rows x {col_count} cols")

            # Create or use worksheet in backup
            if idx == 0:
                # First worksheet already exists (Sheet1)
                backup_ws = backup.sheet1
                backup_ws.update_title(source_ws.title)
            else:
                # Add new worksheet
                backup_ws = backup.add_worksheet(
                    title=source_ws.title,
                    rows=max(row_count, 100),
                    cols=max(col_count, 26)
                )

            # Ensure worksheet has enough rows/cols
            if backup_ws.row_count < row_count:
                backup_ws.add_rows(row_count - backup_ws.row_count)
            if backup_ws.col_count < col_count:
                backup_ws.add_cols(col_count - backup_ws.col_count)

            # Write data to backup worksheet
            if all_data:
                logger.info(f"  Writing data to backup worksheet...")
                backup_ws.update(
                    range_name='A1',
                    values=all_data,
                    value_input_option='RAW'
                )
                logger.info(f"  ✅ {source_ws.title} copied successfully")
            else:
                logger.info(f"  ⚠️  {source_ws.title} is empty, skipping data copy")

        logger.info(f"✅ Backup created: {backup_name}")
        logger.info(f"   Backup ID: {backup_id}")
        logger.info(f"   URL: https://docs.google.com/spreadsheets/d/{backup_id}")

        # Note: Moving to folder would require Drive API v3
        if backup_folder_id:
            logger.warning(
                f"Moving to folder {backup_folder_id} requires Drive API v3. "
                "Backup created in root Drive folder."
            )

        return backup_id

    except gspread.exceptions.SpreadsheetNotFound:
        logger.error(f"❌ Spreadsheet not found: {sheet_id}")
        raise
    except Exception as e:
        logger.error(f"❌ Backup failed: {e}")
        raise


def verify_backup(client: gspread.Client, backup_id: str) -> bool:
    """
    Verify backup was created successfully.

    Args:
        client: Authenticated gspread client
        backup_id: ID of backup spreadsheet

    Returns:
        True if backup is valid
    """
    logger = logging.getLogger(__name__)

    try:
        backup = client.open_by_key(backup_id)
        worksheet_count = len(backup.worksheets())

        logger.info(f"✅ Backup verification passed")
        logger.info(f"   Title: {backup.title}")
        logger.info(f"   Worksheets: {worksheet_count}")

        return True

    except Exception as e:
        logger.error(f"❌ Backup verification failed: {e}")
        return False


def main():
    """Main entry point for backup script."""
    parser = argparse.ArgumentParser(
        description="Backup Google Sheet for ZEUES v3.0 migration"
    )
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Simulate backup without creating copy'
    )
    parser.add_argument(
        '--sheet-id',
        default=None,
        help=f'Sheet ID to backup (default: {config.GOOGLE_SHEET_ID})'
    )
    parser.add_argument(
        '--backup-folder',
        default=None,
        help='Google Drive folder ID for backups'
    )
    parser.add_argument(
        '--verbose',
        action='store_true',
        help='Enable verbose logging'
    )
    parser.add_argument(
        '--verify',
        action='store_true',
        help='Verify backup after creation'
    )

    args = parser.parse_args()

    setup_logging(args.verbose)
    logger = logging.getLogger(__name__)

    # Get sheet ID
    sheet_id = args.sheet_id or config.GOOGLE_SHEET_ID
    if not sheet_id:
        logger.error("❌ No sheet ID provided. Set GOOGLE_SHEET_ID or use --sheet-id")
        return 1

    try:
        # Create client
        logger.info("Authenticating with Google Sheets API...")
        client = get_gspread_client()
        logger.info("✅ Authentication successful")

        # Create backup
        backup_id = create_backup(
            client=client,
            sheet_id=sheet_id,
            backup_folder_id=args.backup_folder,
            dry_run=args.dry_run
        )

        # Verify if requested
        if backup_id and args.verify:
            if not verify_backup(client, backup_id):
                logger.error("❌ Backup verification failed")
                return 1

        if args.dry_run:
            logger.info("✅ Dry run complete - no changes made")
        else:
            logger.info("✅ Backup complete")
            if backup_id:
                logger.info(f"   Backup ID: {backup_id}")

        return 0

    except Exception as e:
        logger.error(f"❌ Script failed: {e}")
        if args.verbose:
            import traceback
            traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
