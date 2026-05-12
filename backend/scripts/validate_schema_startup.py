#!/usr/bin/env python3
"""
Comprehensive schema validation for ZEUES v4.0 startup.

Validates all three sheets have required v4.0 columns before application starts.
Designed to fail fast at startup rather than runtime if schema migration is incomplete.

This script validates:
1. Operaciones sheet (72 columns): v3.0 (0-67) + v4.0 additions (68-72)
2. Uniones sheet (18 columns): Full structure for union-level tracking
3. Metadata sheet (11 columns): v3.0 (1-10) + v4.0 N_UNION column

Usage:
    python backend/scripts/validate_schema_startup.py           # Standalone validation
    python backend/scripts/validate_schema_startup.py --verbose # Detailed logging

Can also be imported and called from main.py:
    from backend.scripts.validate_schema_startup import validate_v4_schema
    success, details = validate_v4_schema()
    if not success:
        raise RuntimeError(f"v4.0 schema validation failed: {details}")
"""
import sys
import argparse
import logging
from pathlib import Path
from typing import Optional

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from backend.repositories.sheets_repository import SheetsRepository
from backend.core.column_map_cache import ColumnMapCache
from backend.config import config


# Single source of truth for sheet schemas lives in backend.core.sheet_schema.
# This script delegates to that registry — the v4.0_new/v5.1_new buckets that
# used to live here are now treated as `critical_columns` if production
# depends on them, or `expected_columns` if they are nice-to-have.
from backend.core.sheet_schema import (
    ALL_SCHEMAS,
    OPERACIONES_SCHEMA,
    UNIONES_SCHEMA,
    METADATA_SCHEMA,
)

# Backwards-compatible aliases (some callers might still import these names).
OPERACIONES_V4_COLUMNS = {
    "v3.0_critical": sorted(OPERACIONES_SCHEMA.critical_columns),
    "v4.0_new": sorted(OPERACIONES_SCHEMA.expected_columns),
    "v5.1_new": [],
}
UNIONES_V4_COLUMNS = sorted(UNIONES_SCHEMA.critical_columns)
METADATA_V4_COLUMNS = {
    "v3.0_existing": sorted(METADATA_SCHEMA.critical_columns),
    "v4.0_new": sorted(METADATA_SCHEMA.expected_columns),
}


def setup_logging(verbose: bool = False) -> None:
    """Configure logging output."""
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format='%(asctime)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )


def validate_sheet_columns(
    repo: SheetsRepository,
    sheet_name: str,
    required_columns: list[str]
) -> tuple[bool, list[str]]:
    """
    Validate that a sheet has all required columns using ColumnMapCache.

    Args:
        repo: SheetsRepository instance
        sheet_name: Name of sheet to validate
        required_columns: List of column names that must exist

    Returns:
        Tuple of (all_present, missing_columns)

    Raises:
        Exception: If sheet cannot be read or cached
    """
    logger = logging.getLogger(__name__)

    try:
        # Build column map (this will cache it)
        ColumnMapCache.get_or_build(sheet_name, repo)

        # Round-trip check (stronger than presence-only): for each required
        # column, the header at the cached index must normalize back to the
        # same required name. Catches collisions where two distinct sheet
        # columns normalize to the same key.
        ok, drifts = ColumnMapCache.validate_critical_columns_strict(
            sheet_name=sheet_name,
            required_columns=required_columns,
        )

        if ok:
            logger.debug(
                f"Sheet '{sheet_name}': All {len(required_columns)} "
                "required columns validated (round-trip)"
            )
            return True, []

        missing = [d["expected"] for d in drifts]
        logger.error(
            f"Sheet '{sheet_name}': drift detected on "
            f"{len(drifts)} columns: {drifts}"
        )
        return False, missing

    except Exception as e:
        logger.error(f"Failed to validate sheet '{sheet_name}': {e}")
        # Return failure with all columns as missing
        return False, required_columns


def validate_v4_schema(
    repo: Optional[SheetsRepository] = None,
    verbose: bool = False
) -> tuple[bool, dict]:
    """
    Validate all sheets have v4.0 schema.

    This is the main entry point for validation, used both standalone
    and from main.py startup hook.

    Args:
        repo: Optional SheetsRepository instance (creates one if None)
        verbose: Enable verbose logging

    Returns:
        Tuple of (success, details)

        success: bool - True if all validations pass

        details: dict with structure:
        {
            "Operaciones": {
                "status": "OK" | "FAIL",
                "missing": [...],
                "validated_count": int
            },
            "Uniones": {
                "status": "OK" | "FAIL",
                "missing": [...],
                "validated_count": int
            },
            "Metadata": {
                "status": "OK" | "FAIL",
                "missing": [...],
                "validated_count": int
            }
        }
    """
    if verbose:
        setup_logging(verbose=True)

    logger = logging.getLogger(__name__)
    logger.info("Starting v4.0 schema validation...")

    # Create repository if not provided
    if repo is None:
        try:
            repo = SheetsRepository()
        except Exception as e:
            logger.error(f"Failed to create SheetsRepository: {e}")
            return False, {"error": f"Repository initialization failed: {e}"}

    results = {}

    # 1. Validate Operaciones sheet
    logger.info("Validating Operaciones sheet...")
    try:
        # Combine v3.0 critical, v4.0 new, and v5.1 new columns
        operaciones_required = (
            OPERACIONES_V4_COLUMNS["v3.0_critical"] +
            OPERACIONES_V4_COLUMNS["v4.0_new"] +
            OPERACIONES_V4_COLUMNS["v5.1_new"]
        )

        ok, missing = validate_sheet_columns(
            repo=repo,
            sheet_name=config.HOJA_OPERACIONES_NOMBRE,
            required_columns=operaciones_required
        )

        results["Operaciones"] = {
            "status": "OK" if ok else "FAIL",
            "missing": missing,
            "validated_count": len(operaciones_required)
        }

        if ok:
            logger.info(f"Operaciones: OK ({len(operaciones_required)} columns validated)")
        else:
            logger.error(f"Operaciones: FAIL (missing {len(missing)} columns: {missing})")

    except Exception as e:
        logger.error(f"Operaciones validation failed: {e}")
        results["Operaciones"] = {
            "status": "FAIL",
            "missing": (
                OPERACIONES_V4_COLUMNS["v3.0_critical"]
                + OPERACIONES_V4_COLUMNS["v4.0_new"]
                + OPERACIONES_V4_COLUMNS["v5.1_new"]
            ),
            "validated_count": 0,
            "error": str(e)
        }

    # 2. Validate Uniones sheet
    logger.info("Validating Uniones sheet...")
    try:
        ok, missing = validate_sheet_columns(
            repo=repo,
            sheet_name="Uniones",
            required_columns=UNIONES_V4_COLUMNS
        )

        results["Uniones"] = {
            "status": "OK" if ok else "FAIL",
            "missing": missing,
            "validated_count": len(UNIONES_V4_COLUMNS)
        }

        if ok:
            logger.info(f"Uniones: OK ({len(UNIONES_V4_COLUMNS)} columns validated)")
        else:
            logger.error(f"Uniones: FAIL (missing {len(missing)} columns: {missing})")

    except Exception as e:
        logger.error(f"Uniones validation failed: {e}")
        results["Uniones"] = {
            "status": "FAIL",
            "missing": UNIONES_V4_COLUMNS,
            "validated_count": 0,
            "error": str(e)
        }

    # 3. Validate Metadata sheet
    logger.info("Validating Metadata sheet...")
    try:
        # Combine v3.0 existing and v4.0 new columns
        metadata_required = (
            METADATA_V4_COLUMNS["v3.0_existing"] +
            METADATA_V4_COLUMNS["v4.0_new"]
        )

        ok, missing = validate_sheet_columns(
            repo=repo,
            sheet_name=config.HOJA_METADATA_NOMBRE,
            required_columns=metadata_required
        )

        results["Metadata"] = {
            "status": "OK" if ok else "FAIL",
            "missing": missing,
            "validated_count": len(metadata_required)
        }

        if ok:
            logger.info(f"Metadata: OK ({len(metadata_required)} columns validated)")
        else:
            logger.error(f"Metadata: FAIL (missing {len(missing)} columns: {missing})")

    except Exception as e:
        logger.error(f"Metadata validation failed: {e}")
        results["Metadata"] = {
            "status": "FAIL",
            "missing": METADATA_V4_COLUMNS["v3.0_existing"] + METADATA_V4_COLUMNS["v4.0_new"],
            "validated_count": 0,
            "error": str(e)
        }

    # Overall success: all sheets must pass
    all_ok = all(r["status"] == "OK" for r in results.values())

    if all_ok:
        logger.info("v4.0 schema validation: SUCCESS")
        logger.info(f"  Operaciones: {results['Operaciones']['validated_count']} columns")
        logger.info(f"  Uniones: {results['Uniones']['validated_count']} columns")
        logger.info(f"  Metadata: {results['Metadata']['validated_count']} columns")
    else:
        logger.error("v4.0 schema validation: FAILED")
        for sheet_name, result in results.items():
            if result["status"] == "FAIL":
                logger.error(f"  {sheet_name}: {len(result['missing'])} missing columns")

    return all_ok, results


def main():
    """Main entry point for standalone script execution."""
    parser = argparse.ArgumentParser(
        description="Validate v4.0 schema for all sheets at startup"
    )
    parser.add_argument(
        '--verbose',
        action='store_true',
        help='Enable verbose logging'
    )
    parser.add_argument(
        '--json',
        action='store_true',
        help='Output results as JSON'
    )

    args = parser.parse_args()

    setup_logging(args.verbose)
    logger = logging.getLogger(__name__)

    try:
        # Run validation
        success, details = validate_v4_schema(verbose=args.verbose)

        # Output results
        if args.json:
            import json
            output = {
                "success": success,
                "details": details
            }
            print(json.dumps(output, indent=2))
        else:
            # Human-readable output
            print("\n" + "="*60)
            print("ZEUES v4.0 Schema Validation Report")
            print("="*60)

            for sheet_name, result in details.items():
                status_icon = "✅" if result["status"] == "OK" else "❌"
                print(f"\n{status_icon} {sheet_name}:")
                print(f"   Status: {result['status']}")
                print(f"   Validated: {result['validated_count']} columns")

                if result["missing"]:
                    print(f"   Missing ({len(result['missing'])}):")
                    for col in result["missing"]:
                        print(f"     - {col}")

                if "error" in result:
                    print(f"   Error: {result['error']}")

            print("\n" + "="*60)
            if success:
                print("✅ VALIDATION PASSED - v4.0 schema complete")
            else:
                print("❌ VALIDATION FAILED - missing required columns")
            print("="*60 + "\n")

        # Exit with appropriate code
        return 0 if success else 1

    except Exception as e:
        logger.error(f"Validation script failed: {e}")
        if args.verbose:
            import traceback
            traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
