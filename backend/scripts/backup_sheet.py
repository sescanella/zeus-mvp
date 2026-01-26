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

        if dry_run:
            logger.info(f"[DRY RUN] Would create backup: {backup_name}")
            if backup_folder_id:
                logger.info(f"[DRY RUN] Would store in folder: {backup_folder_id}")
            else:
                logger.info(f"[DRY RUN] Would store in root Drive")
            logger.info(f"[DRY RUN] Source has {len(spreadsheet.worksheets())} worksheets")
            return None

        # Create copy
        logger.info(f"Creating backup: {backup_name}")
        backup = client.copy(
            file_id=sheet_id,
            title=backup_name,
            copy_comments=False,  # Skip comments for faster backup
            copy_permissions=False  # Don't copy share settings
        )

        backup_id = backup.id
        logger.info(f"✅ Backup created: {backup_name}")
        logger.info(f"   Backup ID: {backup_id}")
        logger.info(f"   URL: https://docs.google.com/spreadsheets/d/{backup_id}")

        # Move to backup folder if specified
        if backup_folder_id:
            try:
                # Note: gspread doesn't have direct move method
                # This would require Drive API v3 integration
                logger.warning(
                    f"Moving to folder {backup_folder_id} requires Drive API v3. "
                    "Backup created in root Drive folder."
                )
            except Exception as e:
                logger.warning(f"Failed to move to folder: {e}. Backup remains in root.")

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
