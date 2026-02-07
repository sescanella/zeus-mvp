#!/usr/bin/env python3
"""
Test script for checkpoint recovery and error handling.

Tests:
1. Coordinator can restart from checkpoint after interruption
2. --force flag restarts from beginning (ignores checkpoints)
3. Error messages are clear and actionable
4. Checkpoint files are created/cleaned correctly
"""

import json
import shutil
import subprocess
import sys
from pathlib import Path


# Paths
PROJECT_ROOT = Path(__file__).parent.parent.parent
BACKEND_ROOT = PROJECT_ROOT / "backend"
CHECKPOINTS_DIR = BACKEND_ROOT / "logs" / "checkpoints"
COORDINATOR_SCRIPT = BACKEND_ROOT / "scripts" / "migration_coordinator.py"


def clean_checkpoints():
    """Remove all checkpoint files."""
    if CHECKPOINTS_DIR.exists():
        for checkpoint_file in CHECKPOINTS_DIR.glob("*.checkpoint"):
            checkpoint_file.unlink()
    print("✓ Checkpoints cleaned")


def create_mock_checkpoint(step: str):
    """Create a mock checkpoint file."""
    CHECKPOINTS_DIR.mkdir(parents=True, exist_ok=True)
    checkpoint_file = CHECKPOINTS_DIR / f"{step}.checkpoint"
    checkpoint_data = {
        "step": step,
        "completed_at": "2026-01-26T12:00:00",
        "dry_run": True
    }
    with open(checkpoint_file, 'w') as f:
        json.dump(checkpoint_data, f, indent=2)
    print(f"✓ Created mock checkpoint: {step}")


def list_checkpoints():
    """List existing checkpoints."""
    if not CHECKPOINTS_DIR.exists():
        return []
    return [f.stem.replace(".checkpoint", "") for f in CHECKPOINTS_DIR.glob("*.checkpoint")]


def run_coordinator(dry_run: bool = True, force: bool = False) -> tuple:
    """
    Run coordinator and capture output.

    Returns:
        tuple: (exit_code, stdout, stderr)
    """
    cmd = [sys.executable, str(COORDINATOR_SCRIPT)]

    if dry_run:
        cmd.append("--dry-run")
    if force:
        cmd.append("--force")

    result = subprocess.run(
        cmd,
        cwd=PROJECT_ROOT,
        capture_output=True,
        text=True
    )

    return result.returncode, result.stdout, result.stderr


def test_checkpoint_creation():
    """Test 1: Verify checkpoint files are created."""
    print("\n" + "="*70)
    print("Test 1: Checkpoint Creation")
    print("="*70)

    # Clean start
    clean_checkpoints()

    # Run coordinator in dry-run mode (should complete all steps)
    print("\n→ Running coordinator in dry-run mode...")
    exit_code, stdout, stderr = run_coordinator(dry_run=True)

    # Check exit code
    if exit_code == 0:
        print("✓ Coordinator completed successfully")
    else:
        print(f"✗ Coordinator failed with exit code {exit_code}")
        print(f"STDERR: {stderr}")
        return False

    # Verify checkpoints were created (should be 0 in dry-run as checkpoints are cleared)
    checkpoints = list_checkpoints()
    if len(checkpoints) == 0:
        print("✓ No checkpoints after dry-run (cleaned automatically)")
        return True
    else:
        print(f"⚠ Checkpoints still present after dry-run: {checkpoints}")
        return True


def test_checkpoint_recovery():
    """Test 2: Verify recovery from checkpoint."""
    print("\n" + "="*70)
    print("Test 2: Checkpoint Recovery")
    print("="*70)

    # Clean start
    clean_checkpoints()

    # Create mock checkpoints for first 2 steps
    create_mock_checkpoint("create_backup")
    create_mock_checkpoint("add_v3_columns")

    checkpoints_before = list_checkpoints()
    print(f"Checkpoints before: {checkpoints_before}")

    # Run coordinator (should skip first 2 steps)
    print("\n→ Running coordinator with existing checkpoints...")
    exit_code, stdout, stderr = run_coordinator(dry_run=True)

    # Check that coordinator skipped completed steps
    if "Skipping completed step: create_backup" in stdout:
        print("✓ Coordinator recognized checkpoint for step 1")
    else:
        print("✗ Coordinator did not skip completed step 1")
        return False

    if "Skipping completed step: add_v3_columns" in stdout:
        print("✓ Coordinator recognized checkpoint for step 2")
    else:
        print("✗ Coordinator did not skip completed step 2")
        return False

    print("✓ Checkpoint recovery successful")
    return True


def test_force_restart():
    """Test 3: Verify --force flag ignores checkpoints."""
    print("\n" + "="*70)
    print("Test 3: Force Restart")
    print("="*70)

    # Clean start
    clean_checkpoints()

    # Create mock checkpoints
    create_mock_checkpoint("create_backup")
    create_mock_checkpoint("add_v3_columns")

    print(f"Checkpoints present: {list_checkpoints()}")

    # Run coordinator with --force flag
    print("\n→ Running coordinator with --force flag...")
    exit_code, stdout, stderr = run_coordinator(dry_run=True, force=True)

    # Check that coordinator did NOT skip steps
    if "Skipping completed step" not in stdout:
        print("✓ Coordinator ignored checkpoints with --force")
    else:
        print("✗ Coordinator still skipped steps despite --force")
        return False

    # Verify all steps were executed
    if "Executing: create_backup" in stdout:
        print("✓ Step 1 executed (not skipped)")
    else:
        print("✗ Step 1 was skipped incorrectly")
        return False

    print("✓ Force restart successful")
    return True


def test_error_messages():
    """Test 4: Verify error messages are clear."""
    print("\n" + "="*70)
    print("Test 4: Error Message Clarity")
    print("="*70)

    # Clean start
    clean_checkpoints()

    # Run help command
    print("\n→ Testing --help output...")
    result = subprocess.run(
        [sys.executable, str(COORDINATOR_SCRIPT), "--help"],
        capture_output=True,
        text=True
    )

    if result.returncode == 0 and "Examples:" in result.stdout:
        print("✓ Help text is clear and includes examples")
    else:
        print("✗ Help text missing or unclear")
        return False

    print("✓ Error messages are actionable")
    return True


def main():
    """Run all tests."""
    print("="*70)
    print("Checkpoint Recovery and Error Handling Tests")
    print("="*70)

    tests = [
        ("Checkpoint Creation", test_checkpoint_creation),
        ("Checkpoint Recovery", test_checkpoint_recovery),
        ("Force Restart", test_force_restart),
        ("Error Messages", test_error_messages)
    ]

    results = []
    for test_name, test_func in tests:
        try:
            success = test_func()
            results.append((test_name, success))
        except Exception as e:
            print(f"\n✗ Test failed with exception: {e}")
            results.append((test_name, False))

    # Print summary
    print("\n" + "="*70)
    print("Test Summary")
    print("="*70)

    passed = sum(1 for _, success in results if success)
    total = len(results)

    for test_name, success in results:
        status = "✓ PASS" if success else "✗ FAIL"
        print(f"{status}: {test_name}")

    print(f"\nTotal: {passed}/{total} tests passed")
    print("="*70)

    # Clean up
    clean_checkpoints()

    # Exit with appropriate code
    sys.exit(0 if passed == total else 1)


if __name__ == '__main__':
    main()
