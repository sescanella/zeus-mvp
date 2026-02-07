#!/usr/bin/env python3
"""
Migration Rollback Script - Restores ZEUES to v2.1 state.

Rollback operations:
1. Restore sheet from backup (requires backup_id)
2. Remove v3.0 columns if partially added
3. Clear column mapping cache
4. Restore v2.1 test suite from archive
5. Log all rollback operations
6. Generate rollback confirmation report

IMPORTANT: Rollback window is 7 days after migration.
After 7 days, v2.1 backups may be archived.

Usage:
    # Full rollback from backup
    python backend/scripts/rollback_migration.py --backup-id <BACKUP_SHEET_ID>

    # Remove v3.0 columns only (partial rollback)
    python backend/scripts/rollback_migration.py --remove-columns-only

    # Check rollback eligibility
    python backend/scripts/rollback_migration.py --check-eligibility
"""

import argparse
import json
import logging
import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, Optional

# Add parent directories to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from backend.config import Config
from backend.repositories.sheets_repository import SheetsRepository
from backend.core.column_map_cache import ColumnMapCache


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(levelname)s: %(message)s'
)
logger = logging.getLogger(__name__)


# Project paths
PROJECT_ROOT = Path(__file__).parent.parent.parent
BACKEND_ROOT = PROJECT_ROOT / "backend"
LOGS_DIR = BACKEND_ROOT / "logs"
TESTS_DIR = PROJECT_ROOT / "tests"
V21_ARCHIVE_DIR = TESTS_DIR / "v2.1-archive"
V30_TESTS_DIR = TESTS_DIR / "v3.0"


class MigrationRollback:
    """Handles rollback of v2.1 → v3.0 migration."""

    def __init__(self, backup_id: Optional[str] = None, dry_run: bool = False):
        """
        Initialize rollback handler.

        Args:
            backup_id: Google Sheet ID of backup to restore from
            dry_run: If True, simulate rollback without making changes
        """
        self.backup_id = backup_id
        self.dry_run = dry_run
        self.config = Config()
        self.repo = SheetsRepository(compatibility_mode="v3.0")
        self.rollback_log: list = []
        self.timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    def _log_operation(self, operation: str, status: str, details: str = ""):
        """Log rollback operation."""
        entry = {
            "timestamp": datetime.now().isoformat(),
            "operation": operation,
            "status": status,
            "details": details
        }
        self.rollback_log.append(entry)
        logger.info(f"{status}: {operation} - {details}")

    def _check_rollback_window(self) -> bool:
        """
        Check if rollback is within 7-day window.

        Returns:
            bool: True if within window, False otherwise
        """
        logger.info("Checking rollback window eligibility...")

        # Try to find migration timestamp from logs
        migration_logs = list(LOGS_DIR.glob("migration_*.log"))
        if not migration_logs:
            logger.warning("No migration logs found - cannot verify rollback window")
            return True  # Allow rollback if we can't determine migration date

        # Get most recent migration log
        latest_log = max(migration_logs, key=lambda p: p.stat().st_mtime)
        migration_date = datetime.fromtimestamp(latest_log.stat().st_mtime)
        days_since_migration = (datetime.now() - migration_date).days

        logger.info(f"Migration date: {migration_date.strftime('%Y-%m-%d')}")
        logger.info(f"Days since migration: {days_since_migration}")

        if days_since_migration <= 7:
            logger.info(f"✓ Within rollback window ({days_since_migration}/7 days)")
            return True
        else:
            logger.warning(f"⚠ Outside rollback window ({days_since_migration} > 7 days)")
            logger.warning("Rollback may not be safe - v2.1 backups may be archived")
            return False

    def _restore_from_backup(self) -> bool:
        """
        Step 1: Restore sheet from backup.

        Returns:
            bool: True if successful
        """
        logger.info("Step 1/5: Restoring from backup...")

        if not self.backup_id:
            logger.error("✗ No backup ID provided - cannot restore")
            self._log_operation("restore_from_backup", "FAILED", "No backup ID provided")
            return False

        if self.dry_run:
            logger.info(f"[DRY RUN] Would restore from backup: {self.backup_id}")
            self._log_operation("restore_from_backup", "DRY RUN", f"backup_id={self.backup_id}")
            return True

        try:
            # Note: Full sheet restoration requires Drive API and manual intervention
            # This is a destructive operation and should be done carefully
            logger.warning("⚠ Sheet restoration requires manual intervention")
            logger.warning("Steps to restore manually:")
            logger.warning(f"  1. Open backup sheet: https://docs.google.com/spreadsheets/d/{self.backup_id}")
            logger.warning(f"  2. File → Make a copy")
            logger.warning(f"  3. Replace production sheet ID in .env.local: GOOGLE_SHEET_ID={self.backup_id}")
            logger.warning(f"  4. Or use Drive API to copy backup over production")

            self._log_operation(
                "restore_from_backup",
                "MANUAL",
                f"Requires manual restoration from backup_id={self.backup_id}"
            )
            return False  # Return False to indicate manual intervention needed

        except Exception as e:
            logger.error(f"✗ Backup restoration failed: {e}")
            self._log_operation("restore_from_backup", "FAILED", str(e))
            return False

    def _remove_v3_columns(self) -> bool:
        """
        Step 2: Remove v3.0 columns if partially added.

        Returns:
            bool: True if successful
        """
        logger.info("Step 2/5: Removing v3.0 columns...")

        if self.dry_run:
            logger.info("[DRY RUN] Would remove columns: Ocupado_Por, Fecha_Ocupacion, version")
            self._log_operation("remove_v3_columns", "DRY RUN", "Would remove 3 columns")
            return True

        try:
            # Check if columns exist
            headers = self.repo.get_headers(Config.HOJA_OPERACIONES_NOMBRE)
            if len(headers) < 68:
                logger.info("✓ v3.0 columns not present (sheet has {len(headers)} columns)")
                self._log_operation("remove_v3_columns", "SKIPPED", "Columns not present")
                return True

            # Remove last 3 columns (68 → 65)
            logger.warning("⚠ Column removal requires manual intervention or Drive API")
            logger.warning("Google Sheets API does not support column deletion via gspread")
            logger.warning("Manual steps:")
            logger.warning(f"  1. Open sheet: https://docs.google.com/spreadsheets/d/{self.config.GOOGLE_SHEET_ID}")
            logger.warning("  2. Select columns 64-66 (Ocupado_Por, Fecha_Ocupacion, version)")
            logger.warning("  3. Right-click → Delete columns")

            self._log_operation(
                "remove_v3_columns",
                "MANUAL",
                "Requires manual column deletion"
            )
            return False

        except Exception as e:
            logger.error(f"✗ Column removal failed: {e}")
            self._log_operation("remove_v3_columns", "FAILED", str(e))
            return False

    def _clear_column_cache(self) -> bool:
        """
        Step 3: Clear column mapping cache.

        Returns:
            bool: True if successful
        """
        logger.info("Step 3/5: Clearing column mapping cache...")

        if self.dry_run:
            logger.info("[DRY RUN] Would clear column mapping cache")
            self._log_operation("clear_column_cache", "DRY RUN", "")
            return True

        try:
            ColumnMapCache.clear_cache()
            logger.info("✓ Column mapping cache cleared")
            self._log_operation("clear_column_cache", "SUCCESS", "Cache cleared")
            return True

        except Exception as e:
            logger.error(f"✗ Cache clearing failed: {e}")
            self._log_operation("clear_column_cache", "FAILED", str(e))
            return False

    def _restore_v21_tests(self) -> bool:
        """
        Step 4: Restore v2.1 test suite from archive.

        Returns:
            bool: True if successful
        """
        logger.info("Step 4/5: Restoring v2.1 test suite...")

        if self.dry_run:
            logger.info("[DRY RUN] Would restore v2.1 tests from archive")
            self._log_operation("restore_v21_tests", "DRY RUN", "")
            return True

        try:
            # Check if archive exists
            if not V21_ARCHIVE_DIR.exists():
                logger.warning("⚠ v2.1 test archive not found")
                self._log_operation("restore_v21_tests", "SKIPPED", "Archive not found")
                return True

            # Remove v3.0 tests
            if V30_TESTS_DIR.exists():
                import shutil
                shutil.rmtree(V30_TESTS_DIR)
                logger.info("✓ Removed v3.0 test suite")

            # Restore v2.1 tests from archive
            import shutil
            shutil.copytree(V21_ARCHIVE_DIR, TESTS_DIR, dirs_exist_ok=True)
            logger.info("✓ Restored v2.1 test suite from archive")

            self._log_operation("restore_v21_tests", "SUCCESS", "v2.1 tests restored")
            return True

        except Exception as e:
            logger.error(f"✗ Test restoration failed: {e}")
            self._log_operation("restore_v21_tests", "FAILED", str(e))
            return False

    def _generate_report(self) -> Dict:
        """
        Step 5: Generate rollback confirmation report.

        Returns:
            dict: Rollback report
        """
        logger.info("Step 5/5: Generating rollback report...")

        report = {
            "timestamp": datetime.now().isoformat(),
            "backup_id": self.backup_id,
            "dry_run": self.dry_run,
            "operations": self.rollback_log,
            "success": all(op["status"] in ["SUCCESS", "SKIPPED", "DRY RUN"] for op in self.rollback_log),
            "manual_steps_required": any(op["status"] == "MANUAL" for op in self.rollback_log)
        }

        # Write report to file
        report_path = LOGS_DIR / f"rollback_report_{self.timestamp}.json"
        with open(report_path, 'w') as f:
            json.dump(report, f, indent=2)

        logger.info(f"Report written to: {report_path}")
        return report

    def execute(self) -> bool:
        """
        Execute rollback operation.

        Returns:
            bool: True if rollback successful
        """
        logger.info("="*70)
        logger.info("ZEUES v3.0 → v2.1 Migration Rollback")
        logger.info("="*70)

        # Check rollback window
        within_window = self._check_rollback_window()
        if not within_window and not self.dry_run:
            response = input("\n⚠ Outside 7-day rollback window. Continue anyway? (yes/no): ")
            if response.lower() != "yes":
                logger.info("Rollback cancelled by user")
                return False

        # Execute rollback steps
        steps = [
            self._restore_from_backup,
            self._remove_v3_columns,
            self._clear_column_cache,
            self._restore_v21_tests
        ]

        for i, step in enumerate(steps, 1):
            logger.info(f"\n[{i}/{len(steps)}] Executing: {step.__name__}")
            success = step()
            if not success and not self.dry_run:
                logger.error(f"Step failed: {step.__name__}")

        # Generate report
        report = self._generate_report()

        # Print summary
        logger.info("\n" + "="*70)
        if report["success"]:
            logger.info("✓ Rollback completed successfully")
        elif report["manual_steps_required"]:
            logger.warning("⚠ Rollback requires manual steps (see log above)")
        else:
            logger.error("✗ Rollback failed")
        logger.info("="*70)

        # Print JSON report
        print("\nRollback Report:")
        print(json.dumps(report, indent=2))

        return report["success"] or report["manual_steps_required"]


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Rollback ZEUES v3.0 → v2.1 migration",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Full rollback from backup
  python backend/scripts/rollback_migration.py --backup-id 1A2B3C4D5E6F

  # Remove v3.0 columns only
  python backend/scripts/rollback_migration.py --remove-columns-only

  # Check rollback eligibility
  python backend/scripts/rollback_migration.py --check-eligibility

  # Dry run
  python backend/scripts/rollback_migration.py --backup-id 1A2B3C4D5E6F --dry-run
        """
    )

    parser.add_argument(
        '--backup-id',
        type=str,
        help='Google Sheet ID of backup to restore from'
    )
    parser.add_argument(
        '--remove-columns-only',
        action='store_true',
        help='Only remove v3.0 columns (no full restoration)'
    )
    parser.add_argument(
        '--check-eligibility',
        action='store_true',
        help='Check if rollback is within 7-day window'
    )
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Simulate rollback without making changes'
    )

    args = parser.parse_args()

    # Check eligibility only
    if args.check_eligibility:
        rollback = MigrationRollback()
        within_window = rollback._check_rollback_window()
        sys.exit(0 if within_window else 1)

    # Execute rollback
    rollback = MigrationRollback(
        backup_id=args.backup_id,
        dry_run=args.dry_run
    )

    success = rollback.execute()
    sys.exit(0 if success else 1)


if __name__ == '__main__':
    main()
