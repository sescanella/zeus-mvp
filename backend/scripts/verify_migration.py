#!/usr/bin/env python3
"""
Migration Verification Script - Validates v2.1 → v3.0 migration success.

Verification checks:
1. Column count = 68 (65 v2.1 + 3 v3.0)
2. New column headers exist (Ocupado_Por, Fecha_Ocupacion, version)
3. Sample 10 random rows, verify version=0
4. Confirm Ocupado_Por and Fecha_Ocupacion empty
5. Validate v2.1 data intact (spot check)
6. Test column mapping cache recognizes new columns
7. Return JSON report with pass/fail

Usage:
    python backend/scripts/verify_migration.py              # Full verification
    python backend/scripts/verify_migration.py --dry-run   # Check without validation
"""

import argparse
import json
import logging
import random
import sys
from pathlib import Path
from typing import Dict, List, Optional

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


class MigrationVerifier:
    """Verifies v2.1 → v3.0 migration was successful."""

    def __init__(self, dry_run: bool = False):
        """
        Initialize verifier.

        Args:
            dry_run: If True, check configuration without validation
        """
        self.dry_run = dry_run
        self.config = Config()
        self.repo = SheetsRepository(compatibility_mode="v3.0")
        self.report: Dict = {
            "timestamp": None,
            "dry_run": dry_run,
            "checks": {},
            "success": False,
            "errors": []
        }

    def _check_column_count(self) -> bool:
        """Check 1: Verify sheet has 68 columns."""
        logger.info("Check 1/7: Verifying column count...")

        try:
            headers = self.repo.get_headers(Config.HOJA_OPERACIONES_NOMBRE)
            actual_count = len(headers)
            expected_count = 68

            self.report["checks"]["column_count"] = {
                "expected": expected_count,
                "actual": actual_count,
                "passed": actual_count == expected_count
            }

            if actual_count == expected_count:
                logger.info(f"✓ Column count correct: {actual_count}")
                return True
            else:
                logger.error(f"✗ Column count mismatch: expected {expected_count}, got {actual_count}")
                return False

        except Exception as e:
            logger.error(f"✗ Column count check failed: {e}")
            self.report["errors"].append(f"Column count check: {e}")
            return False

    def _check_new_headers(self) -> bool:
        """Check 2: Verify new column headers exist."""
        logger.info("Check 2/7: Verifying new column headers...")

        try:
            headers = self.repo.get_headers(Config.HOJA_OPERACIONES_NOMBRE)
            expected_headers = ["Ocupado_Por", "Fecha_Ocupacion", "version"]
            found_headers = []

            # Normalize and check
            headers_lower = [h.lower().replace("_", "").replace(" ", "") for h in headers]

            for expected in expected_headers:
                normalized = expected.lower().replace("_", "")
                if normalized in headers_lower:
                    found_headers.append(expected)

            self.report["checks"]["new_headers"] = {
                "expected": expected_headers,
                "found": found_headers,
                "passed": len(found_headers) == len(expected_headers)
            }

            if len(found_headers) == len(expected_headers):
                logger.info(f"✓ All new headers found: {found_headers}")
                return True
            else:
                missing = set(expected_headers) - set(found_headers)
                logger.error(f"✗ Missing headers: {missing}")
                return False

        except Exception as e:
            logger.error(f"✗ Header check failed: {e}")
            self.report["errors"].append(f"Header check: {e}")
            return False

    def _check_sample_versions(self, sample_size: int = 10) -> bool:
        """Check 3: Sample random rows and verify version=0."""
        logger.info(f"Check 3/7: Sampling {sample_size} rows for version initialization...")

        try:
            # Get total row count
            all_data = self.repo.get_all_values(Config.HOJA_OPERACIONES_NOMBRE)
            total_rows = len(all_data) - 1  # Exclude header

            if total_rows == 0:
                logger.warning("Sheet has no data rows to sample")
                self.report["checks"]["sample_versions"] = {
                    "sample_size": 0,
                    "passed": True,
                    "note": "No data rows to verify"
                }
                return True

            # Sample random rows
            sample_size = min(sample_size, total_rows)
            sample_rows = random.sample(range(2, total_rows + 2), sample_size)  # +2 for header and 1-indexing

            versions_correct = []
            versions_incorrect = []

            for row in sample_rows:
                version = self.repo.get_version(Config.HOJA_OPERACIONES_NOMBRE, row)
                if version == 0:
                    versions_correct.append(row)
                else:
                    versions_incorrect.append((row, version))

            self.report["checks"]["sample_versions"] = {
                "sample_size": sample_size,
                "correct": len(versions_correct),
                "incorrect": len(versions_incorrect),
                "incorrect_rows": versions_incorrect,
                "passed": len(versions_incorrect) == 0
            }

            if len(versions_incorrect) == 0:
                logger.info(f"✓ All {sample_size} sampled rows have version=0")
                return True
            else:
                logger.error(f"✗ {len(versions_incorrect)} rows have incorrect versions: {versions_incorrect}")
                return False

        except Exception as e:
            logger.error(f"✗ Version sampling failed: {e}")
            self.report["errors"].append(f"Version sampling: {e}")
            return False

    def _check_occupation_empty(self, sample_size: int = 10) -> bool:
        """Check 4: Verify Ocupado_Por and Fecha_Ocupacion are empty."""
        logger.info(f"Check 4/7: Verifying occupation fields empty...")

        try:
            # Get total row count
            all_data = self.repo.get_all_values(Config.HOJA_OPERACIONES_NOMBRE)
            total_rows = len(all_data) - 1  # Exclude header

            if total_rows == 0:
                logger.warning("Sheet has no data rows to check")
                self.report["checks"]["occupation_empty"] = {
                    "sample_size": 0,
                    "passed": True,
                    "note": "No data rows to verify"
                }
                return True

            # Sample random rows
            sample_size = min(sample_size, total_rows)
            sample_rows = random.sample(range(2, total_rows + 2), sample_size)

            occupied_rows = []

            for row in sample_rows:
                ocupado_por = self.repo.get_ocupado_por(Config.HOJA_OPERACIONES_NOMBRE, row)
                fecha_ocupacion = self.repo.get_fecha_ocupacion(Config.HOJA_OPERACIONES_NOMBRE, row)

                if ocupado_por is not None or fecha_ocupacion is not None:
                    occupied_rows.append((row, ocupado_por, fecha_ocupacion))

            self.report["checks"]["occupation_empty"] = {
                "sample_size": sample_size,
                "empty": sample_size - len(occupied_rows),
                "occupied": len(occupied_rows),
                "occupied_rows": occupied_rows,
                "passed": len(occupied_rows) == 0
            }

            if len(occupied_rows) == 0:
                logger.info(f"✓ All {sample_size} sampled rows have empty occupation fields")
                return True
            else:
                logger.warning(f"⚠ {len(occupied_rows)} rows have occupation data (may be expected if migration running on active system)")
                return True  # Don't fail - could be normal if system is active

        except Exception as e:
            logger.error(f"✗ Occupation check failed: {e}")
            self.report["errors"].append(f"Occupation check: {e}")
            return False

    def _check_v21_data_intact(self, sample_size: int = 5) -> bool:
        """Check 5: Validate v2.1 data intact (spot check)."""
        logger.info(f"Check 5/7: Spot-checking v2.1 data integrity...")

        try:
            # Get sample rows
            all_data = self.repo.get_all_values(Config.HOJA_OPERACIONES_NOMBRE)
            total_rows = len(all_data) - 1

            if total_rows == 0:
                logger.warning("Sheet has no data rows to check")
                self.report["checks"]["v21_data_intact"] = {
                    "sample_size": 0,
                    "passed": True,
                    "note": "No data rows to verify"
                }
                return True

            sample_size = min(sample_size, total_rows)
            sample_rows = random.sample(range(2, total_rows + 2), sample_size)

            intact_rows = 0
            corrupt_rows = []

            for row in sample_rows:
                # Check that TAG_SPOOL exists (critical field)
                row_data = all_data[row - 1]  # -1 for 0-indexing
                if len(row_data) > 0 and row_data[0]:  # TAG_SPOOL is column A (index 0)
                    intact_rows += 1
                else:
                    corrupt_rows.append(row)

            self.report["checks"]["v21_data_intact"] = {
                "sample_size": sample_size,
                "intact": intact_rows,
                "corrupt": len(corrupt_rows),
                "corrupt_rows": corrupt_rows,
                "passed": len(corrupt_rows) == 0
            }

            if len(corrupt_rows) == 0:
                logger.info(f"✓ All {sample_size} sampled rows have intact v2.1 data")
                return True
            else:
                logger.error(f"✗ {len(corrupt_rows)} rows have corrupt data: {corrupt_rows}")
                return False

        except Exception as e:
            logger.error(f"✗ v2.1 data integrity check failed: {e}")
            self.report["errors"].append(f"v2.1 data integrity: {e}")
            return False

    def _check_column_mapping(self) -> bool:
        """Check 6: Test column mapping cache recognizes new columns."""
        logger.info("Check 6/7: Testing column mapping cache...")

        try:
            # Clear cache and rebuild
            ColumnMapCache.clear_cache()
            column_map = ColumnMapCache.get_or_build(
                self.repo,
                Config.HOJA_OPERACIONES_NOMBRE
            )

            # Check for v3.0 columns
            expected_keys = ["ocupadopor", "fechaocupacion", "version"]
            found_keys = []

            for key in expected_keys:
                if key in column_map:
                    found_keys.append(key)

            self.report["checks"]["column_mapping"] = {
                "expected_keys": expected_keys,
                "found_keys": found_keys,
                "column_map_size": len(column_map),
                "passed": len(found_keys) == len(expected_keys)
            }

            if len(found_keys) == len(expected_keys):
                logger.info(f"✓ Column mapping recognizes all v3.0 columns")
                return True
            else:
                missing = set(expected_keys) - set(found_keys)
                logger.error(f"✗ Column mapping missing keys: {missing}")
                return False

        except Exception as e:
            logger.error(f"✗ Column mapping check failed: {e}")
            self.report["errors"].append(f"Column mapping: {e}")
            return False

    def _generate_report(self) -> Dict:
        """Check 7: Generate final JSON report."""
        logger.info("Check 7/7: Generating final report...")

        from datetime import datetime
        self.report["timestamp"] = datetime.now().isoformat()

        # Determine overall success
        all_checks_passed = all(
            check.get("passed", False)
            for check in self.report["checks"].values()
        )
        self.report["success"] = all_checks_passed and len(self.report["errors"]) == 0

        return self.report

    def verify(self) -> bool:
        """
        Run all verification checks.

        Returns:
            bool: True if all checks pass, False otherwise
        """
        if self.dry_run:
            logger.info("[DRY RUN] Would verify migration")
            return True

        logger.info("="*70)
        logger.info("ZEUES v3.0 Migration Verification")
        logger.info("="*70)

        # Run all checks
        checks = [
            self._check_column_count(),
            self._check_new_headers(),
            self._check_sample_versions(),
            self._check_occupation_empty(),
            self._check_v21_data_intact(),
            self._check_column_mapping()
        ]

        # Generate report
        report = self._generate_report()

        # Print summary
        logger.info("="*70)
        if report["success"]:
            logger.info("✓ Migration verification PASSED")
        else:
            logger.error("✗ Migration verification FAILED")

        logger.info(f"Checks passed: {sum(checks)}/{len(checks)}")
        logger.info(f"Errors: {len(report['errors'])}")
        logger.info("="*70)

        # Print JSON report
        print("\nJSON Report:")
        print(json.dumps(report, indent=2))

        return report["success"]


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Verify ZEUES v2.1 → v3.0 migration",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Check configuration without validation'
    )

    args = parser.parse_args()

    verifier = MigrationVerifier(dry_run=args.dry_run)
    success = verifier.verify()
    sys.exit(0 if success else 1)


if __name__ == '__main__':
    main()
