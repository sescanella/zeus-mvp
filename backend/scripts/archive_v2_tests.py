#!/usr/bin/env python3
"""
Archive v2.1 tests before v3.0 migration.

This script:
1. Validates test results from current pytest run
2. Moves entire tests/ directory to tests/v2.1-archive/
3. Creates timestamp markers and test results documentation
4. Preserves all test files for historical reference
5. Prepares for v3.0 smoke test suite

Usage:
    python backend/scripts/archive_v2_tests.py [--force]

Options:
    --force    Skip confirmation prompt
"""
import os
import sys
import shutil
import argparse
from datetime import datetime
from pathlib import Path


def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="Archive v2.1 tests to prepare for v3.0 migration"
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Skip confirmation prompt"
    )
    return parser.parse_args()


def get_project_root():
    """Get project root directory (where tests/ exists)."""
    # Script is in backend/scripts/, go up 2 levels
    return Path(__file__).parent.parent.parent


def check_directories():
    """Check that required directories exist."""
    root = get_project_root()
    tests_dir = root / "tests"
    scripts_dir = root / "backend" / "scripts"

    if not tests_dir.exists():
        print(f"ERROR: tests/ directory not found at {tests_dir}")
        return False

    if not scripts_dir.exists():
        print(f"Creating backend/scripts/ directory...")
        scripts_dir.mkdir(parents=True, exist_ok=True)

    return True


def read_pytest_results():
    """Read pytest results from last run."""
    # Check for pytest result file (written by test run)
    result_file = Path("/tmp/pytest_v21_results.txt")

    if not result_file.exists():
        print("WARNING: No pytest results file found at /tmp/pytest_v21_results.txt")
        print("Please run: pytest tests/ -v --tb=short 2>&1 | tee /tmp/pytest_v21_results.txt")
        return None

    with open(result_file, "r") as f:
        content = f.read()

    # Parse summary line (e.g., "31 failed, 169 passed, 5 warnings, 33 errors")
    summary_line = None
    for line in content.splitlines():
        if "passed" in line and ("failed" in line or "error" in line):
            summary_line = line.strip()
            break

    return {
        "summary": summary_line,
        "full_output": content,
        "timestamp": datetime.now().isoformat()
    }


def create_archive(force=False):
    """Archive tests/ directory to tests/v2.1-archive/."""
    root = get_project_root()
    tests_dir = root / "tests"
    archive_dir = root / "tests" / "v2.1-archive"

    if archive_dir.exists():
        print(f"ERROR: Archive directory already exists at {archive_dir}")
        print("Archive has already been created. Aborting.")
        return False

    # Confirm with user
    if not force:
        print("\nThis will move tests/ to tests/v2.1-archive/")
        print("Current tests will be preserved but no longer run by default.")
        response = input("\nProceed with archival? [y/N]: ")
        if response.lower() not in ['y', 'yes']:
            print("Aborted.")
            return False

    # Get pytest results
    pytest_results = read_pytest_results()

    # Create v2.1-archive directory structure
    print(f"\nCreating archive directory: {archive_dir}")
    archive_dir.mkdir(parents=True, exist_ok=True)

    # Move all test files to archive (except v2.1-archive itself)
    print("Moving test files to archive...")
    moved_files = []

    for item in tests_dir.iterdir():
        if item.name == "v2.1-archive":
            continue  # Don't move the archive directory itself

        dest = archive_dir / item.name
        print(f"  Moving {item.name} -> v2.1-archive/{item.name}")
        shutil.move(str(item), str(dest))
        moved_files.append(item.name)

    # Create timestamp marker
    timestamp_file = archive_dir / "ARCHIVED_ON.txt"
    with open(timestamp_file, "w") as f:
        f.write(f"v2.1 Tests Archived On: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"\nArchived by: backend/scripts/archive_v2_tests.py\n")
        f.write(f"Phase: 01-migration-foundation\n")
        f.write(f"Plan: 01-03\n")
        f.write(f"\nThese tests are preserved for historical reference.\n")
        f.write(f"v3.0 smoke tests are located in tests/v3.0/\n")

    print(f"Created: {timestamp_file}")

    # Create test results documentation
    results_file = archive_dir / "TEST_RESULTS.txt"
    with open(results_file, "w") as f:
        f.write("v2.1 Test Results Before Archival\n")
        f.write("=" * 70 + "\n\n")

        if pytest_results:
            f.write(f"Timestamp: {pytest_results['timestamp']}\n\n")
            f.write(f"Summary: {pytest_results['summary']}\n\n")
            f.write("=" * 70 + "\n")
            f.write("Full Output:\n")
            f.write("=" * 70 + "\n\n")
            f.write(pytest_results['full_output'])
        else:
            f.write("No pytest results available.\n")
            f.write("Tests were archived without running full test suite.\n")

    print(f"Created: {results_file}")

    # Create file manifest
    manifest_file = archive_dir / "MANIFEST.txt"
    with open(manifest_file, "w") as f:
        f.write("v2.1 Archived Files Manifest\n")
        f.write("=" * 70 + "\n\n")
        f.write(f"Total items moved: {len(moved_files)}\n\n")
        f.write("Files/directories:\n")
        for item in sorted(moved_files):
            f.write(f"  - {item}\n")

    print(f"Created: {manifest_file}")

    return True


def create_v3_structure():
    """Create new v3.0 test directory structure."""
    root = get_project_root()
    v3_dir = root / "tests" / "v3.0"

    if v3_dir.exists():
        print(f"\nv3.0 directory already exists at {v3_dir}")
        return True

    print(f"\nCreating v3.0 test structure...")
    v3_dir.mkdir(parents=True, exist_ok=True)

    # Create __init__.py
    init_file = v3_dir / "__init__.py"
    with open(init_file, "w") as f:
        f.write('"""v3.0 smoke tests for migration validation."""\n')
    print(f"Created: tests/v3.0/__init__.py")

    # Create conftest.py with v3.0-specific fixtures
    conftest_file = v3_dir / "conftest.py"
    with open(conftest_file, "w") as f:
        f.write('"""\nv3.0 test fixtures.\n\nProvides fixtures specific to v3.0 features:\n')
        f.write('- v3.0 column access\n')
        f.write('- Occupation state validation\n')
        f.write('- Version token testing\n')
        f.write('"""\n')
        f.write('import pytest\n')
        f.write('from backend.services.sheets_service import SheetsService\n')
        f.write('from backend.core.column_map_cache import ColumnMapCache\n\n\n')
        f.write('@pytest.fixture\n')
        f.write('def mock_column_map_v3():\n')
        f.write('    """Mock column map including v3.0 columns."""\n')
        f.write('    return {\n')
        f.write('        "tagspool": 6,\n')
        f.write('        "fechamateriales": 32,\n')
        f.write('        "armador": 34,\n')
        f.write('        "soldador": 36,\n')
        f.write('        # v3.0 columns\n')
        f.write('        "ocupadopor": 64,\n')
        f.write('        "fechaocupacion": 65,\n')
        f.write('        "version": 66,\n')
        f.write('    }\n')
    print(f"Created: tests/v3.0/conftest.py")

    return True


def update_pytest_ini():
    """Update pytest.ini to exclude v2.1-archive and configure v3.0 tests."""
    root = get_project_root()
    pytest_ini = root / "pytest.ini"

    content = """[pytest]
# Pytest configuration for v3.0

# Test discovery
testpaths = tests/v3.0
python_files = test_*.py
python_classes = Test*
python_functions = test_*

# Exclude v2.1 archived tests
norecursedirs = .git .tox dist build *.egg tests/v2.1-archive

# Markers
markers =
    v3: v3.0 feature tests
    migration: Migration validation tests
    smoke: Smoke tests for rapid validation
    backward_compat: Backward compatibility tests

# Output
addopts = -v --tb=short --strict-markers

# Coverage (optional)
# addopts = --cov=backend --cov-report=html --cov-report=term
"""

    with open(pytest_ini, "w") as f:
        f.write(content)

    print(f"Created: pytest.ini")
    return True


def main():
    """Main execution flow."""
    args = parse_args()

    print("=" * 70)
    print("v2.1 Test Archive Script")
    print("=" * 70)

    # Check directories
    if not check_directories():
        sys.exit(1)

    # Create archive
    if not create_archive(force=args.force):
        sys.exit(1)

    # Create v3.0 structure
    if not create_v3_structure():
        sys.exit(1)

    # Update pytest.ini
    if not update_pytest_ini():
        sys.exit(1)

    print("\n" + "=" * 70)
    print("Archive completed successfully!")
    print("=" * 70)
    print("\nNext steps:")
    print("1. Implement v3.0 smoke tests in tests/v3.0/")
    print("2. Run: pytest tests/v3.0/ -v")
    print("3. v2.1 tests preserved in tests/v2.1-archive/ for reference")
    print("\n")


if __name__ == "__main__":
    main()
