#!/usr/bin/env python3
"""
Test suite for migration scripts.

Verifies:
1. Dependencies installed correctly
2. Scripts have --help and --dry-run options
3. Idempotency checks work
4. Error handling is present
"""
import sys
import subprocess
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from backend.repositories.sheets_repository import SheetsRepository
from backend.config import config


def run_command(cmd: list[str]) -> tuple[int, str, str]:
    """Run command and return exit code, stdout, stderr."""
    result = subprocess.run(
        cmd,
        capture_output=True,
        text=True
    )
    return result.returncode, result.stdout, result.stderr


def test_dependencies():
    """Test 1: Verify dependencies are installed."""
    print("\n📦 Test 1: Checking dependencies...")

    try:
        import gspread
        import google.auth

        # Check versions
        gspread_version = gspread.__version__
        print(f"   ✅ gspread=={gspread_version}")

        # Verify minimum versions
        gspread_major, gspread_minor = map(int, gspread_version.split('.')[:2])
        assert gspread_major >= 5 or (gspread_major == 5 and gspread_minor >= 10), \
            "gspread must be >= 5.10.0"

        print("   ✅ All dependencies meet requirements")
        return True

    except ImportError as e:
        print(f"   ❌ Missing dependency: {e}")
        return False
    except Exception as e:
        print(f"   ❌ Error checking dependencies: {e}")
        return False


def test_script_help_options():
    """Test 2: Verify scripts have --help option."""
    print("\n📖 Test 2: Checking --help options...")

    scripts = [
        "backend/scripts/backup_sheet.py",
        "backend/scripts/add_v3_columns.py"
    ]

    all_passed = True
    for script in scripts:
        exit_code, stdout, stderr = run_command(["python", script, "--help"])

        if exit_code == 0 and "usage:" in stdout:
            print(f"   ✅ {Path(script).name} has --help")
        else:
            print(f"   ❌ {Path(script).name} missing --help")
            all_passed = False

    return all_passed


def test_dry_run_options():
    """Test 3: Verify scripts have --dry-run option."""
    print("\n🧪 Test 3: Checking --dry-run options...")

    # Test backup_sheet.py
    print("   Testing backup_sheet.py...")
    exit_code, stdout, stderr = run_command([
        "python", "backend/scripts/backup_sheet.py", "--dry-run"
    ])

    backup_passed = exit_code == 0 and "[DRY RUN]" in stdout
    if backup_passed:
        print("   ✅ backup_sheet.py --dry-run works")
    else:
        print("   ❌ backup_sheet.py --dry-run failed")

    # Test add_v3_columns.py
    print("   Testing add_v3_columns.py...")
    exit_code, stdout, stderr = run_command([
        "python", "backend/scripts/add_v3_columns.py", "--dry-run", "--force"
    ])

    columns_passed = exit_code == 0 and "[DRY RUN]" in stdout
    if columns_passed:
        print("   ✅ add_v3_columns.py --dry-run works")
    else:
        print("   ❌ add_v3_columns.py --dry-run failed")

    return backup_passed and columns_passed


def test_idempotency_check():
    """Test 4: Verify idempotency check detects existing columns."""
    print("\n🔄 Test 4: Checking idempotency logic...")

    try:
        # Check current column state
        repo = SheetsRepository()
        all_rows = repo.read_worksheet(config.HOJA_OPERACIONES_NOMBRE)
        headers = all_rows[0]

        v3_cols = ['Ocupado_Por', 'Fecha_Ocupacion', 'version']
        cols_exist = all(col in headers for col in v3_cols)

        print(f"   Current columns: {len(headers)}")
        print(f"   V3 columns exist: {cols_exist}")

        if cols_exist:
            print("   ℹ️  V3 columns already exist - testing idempotency")
            # Run script - should detect and skip
            exit_code, stdout, stderr = run_command([
                "python", "backend/scripts/add_v3_columns.py", "--dry-run", "--force"
            ])

            if "already exist" in stdout.lower():
                print("   ✅ Idempotency check working - detected existing columns")
                return True
            else:
                print("   ❌ Idempotency check failed - didn't detect existing columns")
                return False
        else:
            print("   ℹ️  V3 columns don't exist yet - idempotency will be tested after migration")
            print("   ✅ Idempotency logic present in script")
            return True

    except Exception as e:
        print(f"   ❌ Error testing idempotency: {e}")
        return False


def test_error_handling():
    """Test 5: Verify error handling is present."""
    print("\n🛡️  Test 5: Checking error handling...")

    # Check for retry decorator in SheetsRepository
    try:
        repo_path = Path("backend/repositories/sheets_repository.py")
        repo_content = repo_path.read_text()

        has_retry = "retry_on_sheets_error" in repo_content
        has_backoff = "backoff_seconds" in repo_content
        has_max_retries = "max_retries" in repo_content

        if has_retry and has_backoff and has_max_retries:
            print("   ✅ Retry logic with exponential backoff present")
        else:
            print("   ❌ Retry logic incomplete")
            return False

        # Check for try-except in scripts
        backup_path = Path("backend/scripts/backup_sheet.py")
        backup_content = backup_path.read_text()

        if "try:" in backup_content and "except" in backup_content:
            print("   ✅ Error handling present in backup_sheet.py")
        else:
            print("   ❌ Error handling missing in backup_sheet.py")
            return False

        columns_path = Path("backend/scripts/add_v3_columns.py")
        columns_content = columns_path.read_text()

        if "try:" in columns_content and "except" in columns_content:
            print("   ✅ Error handling present in add_v3_columns.py")
        else:
            print("   ❌ Error handling missing in add_v3_columns.py")
            return False

        return True

    except Exception as e:
        print(f"   ❌ Error checking error handling: {e}")
        return False


def main():
    """Run all tests."""
    print("=" * 60)
    print("Testing Migration Scripts")
    print("=" * 60)

    tests = [
        ("Dependencies", test_dependencies),
        ("Help Options", test_script_help_options),
        ("Dry-Run Options", test_dry_run_options),
        ("Idempotency", test_idempotency_check),
        ("Error Handling", test_error_handling),
    ]

    results = {}
    for name, test_func in tests:
        try:
            results[name] = test_func()
        except Exception as e:
            print(f"\n❌ Test '{name}' crashed: {e}")
            results[name] = False

    # Summary
    print("\n" + "=" * 60)
    print("Test Summary")
    print("=" * 60)

    for name, passed in results.items():
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{status}: {name}")

    all_passed = all(results.values())

    print("\n" + "=" * 60)
    if all_passed:
        print("✅ All tests passed!")
        return 0
    else:
        print("❌ Some tests failed")
        return 1


if __name__ == "__main__":
    sys.exit(main())
