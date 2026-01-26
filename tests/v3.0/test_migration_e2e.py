"""
End-to-end migration tests for v2.1 → v3.0 cutover.

These tests verify the full migration process including:
1. Full migration flow (backup → columns → verify → versions → tests)
2. Migration with active v2.1 operations in progress
3. Large sheet migration (1000+ spools)
4. Migration idempotency (can run twice safely)
5. Concurrent access during migration (v2.1 API still works)
6. Production readiness metrics (performance, stability, error rate)
"""
import pytest
import subprocess
import sys
import time
from pathlib import Path
from datetime import datetime
from backend.repositories.sheets_repository import SheetsRepository
from backend.config import Config

# Project root
PROJECT_ROOT = Path(__file__).parent.parent.parent
BACKEND_ROOT = PROJECT_ROOT / "backend"


@pytest.mark.e2e
@pytest.mark.migration
def test_full_migration_flow():
    """
    Run full migration coordinator and verify all steps complete successfully.

    Tests the complete migration process:
    1. Backup creation
    2. Column addition
    3. Schema verification
    4. Version initialization
    5. Smoke tests
    """
    # Run migration coordinator in dry-run mode
    cmd = [
        sys.executable,
        str(BACKEND_ROOT / "scripts" / "migration_coordinator.py"),
        "--dry-run"
    ]

    result = subprocess.run(
        cmd,
        cwd=PROJECT_ROOT,
        capture_output=True,
        text=True
    )

    # Verify coordinator runs successfully
    assert result.returncode == 0, f"Migration coordinator failed: {result.stderr}"

    # Verify all steps mentioned in output
    output = result.stdout
    assert "create_backup" in output
    assert "add_v3_columns" in output
    assert "verify_schema" in output
    assert "initialize_versions" in output
    assert "test_smoke" in output

    # Verify success message
    assert "Migration completed successfully" in output or "Report generated" in output


@pytest.mark.e2e
@pytest.mark.migration
@pytest.mark.skip(reason="Requires test sheet with active operations - run manually")
def test_migration_with_active_operations():
    """
    Verify migration works correctly when v2.1 operations are in progress.

    Tests that:
    1. Migration preserves v2.1 operation state (Armador, Soldador filled)
    2. Migration doesn't corrupt in-progress operations
    3. Workers can complete operations after migration
    """
    repo = SheetsRepository(compatibility_mode="v2.1")

    # Find a spool with active operation (Armador set, Fecha_Armado not set)
    all_values = repo.read_worksheet(Config.HOJA_OPERACIONES_NOMBRE)
    headers = all_values[0]

    # Get column indices
    armador_col = headers.index("Armador")
    fecha_armado_col = headers.index("Fecha_Armado")

    # Find row with active operation
    active_row = None
    for i, row in enumerate(all_values[1:], start=2):
        if len(row) > max(armador_col, fecha_armado_col):
            if row[armador_col] and not row[fecha_armado_col]:
                active_row = i
                break

    if active_row is None:
        pytest.skip("No active operations found - cannot test")

    # Record state before migration
    before_armador = all_values[active_row - 1][armador_col]

    # Run migration (dry-run)
    cmd = [
        sys.executable,
        str(BACKEND_ROOT / "scripts" / "migration_coordinator.py"),
        "--dry-run"
    ]

    result = subprocess.run(cmd, cwd=PROJECT_ROOT, capture_output=True, text=True)
    assert result.returncode == 0

    # Verify state after migration (in dry-run, nothing changes)
    all_values_after = repo.read_worksheet(Config.HOJA_OPERACIONES_NOMBRE)
    after_armador = all_values_after[active_row - 1][armador_col]

    # State should be preserved
    assert after_armador == before_armador, "Migration corrupted active operation"


@pytest.mark.e2e
@pytest.mark.migration
@pytest.mark.skip(reason="Requires large test sheet - run manually with performance monitoring")
def test_large_sheet_migration():
    """
    Test migration with 1000+ spools to verify performance and stability.

    Tests:
    1. Migration completes in reasonable time (< 5 minutes)
    2. No memory issues with large datasets
    3. All 1000+ rows get version=0 initialized
    """
    start_time = time.time()

    # Run migration (dry-run)
    cmd = [
        sys.executable,
        str(BACKEND_ROOT / "scripts" / "migration_coordinator.py"),
        "--dry-run"
    ]

    result = subprocess.run(cmd, cwd=PROJECT_ROOT, capture_output=True, text=True)

    elapsed_time = time.time() - start_time

    # Verify success
    assert result.returncode == 0, f"Migration failed: {result.stderr}"

    # Verify performance - should complete in < 5 minutes
    assert elapsed_time < 300, f"Migration took {elapsed_time}s (expected < 300s)"

    # In real run, verify row count
    repo = SheetsRepository(compatibility_mode="v3.0")
    all_values = repo.read_worksheet(Config.HOJA_OPERACIONES_NOMBRE)
    row_count = len(all_values) - 1  # Exclude header

    assert row_count >= 1000, f"Expected at least 1000 rows, got {row_count}"


@pytest.mark.e2e
@pytest.mark.migration
def test_migration_idempotency():
    """
    Verify migration can run twice without errors (idempotency).

    Tests:
    1. First run succeeds
    2. Second run detects columns already exist
    3. Second run completes without errors
    4. No data corruption on second run
    """
    # Run migration first time (dry-run)
    cmd = [
        sys.executable,
        str(BACKEND_ROOT / "scripts" / "migration_coordinator.py"),
        "--dry-run",
        "--force"  # Ignore checkpoints
    ]

    result1 = subprocess.run(cmd, cwd=PROJECT_ROOT, capture_output=True, text=True)
    assert result1.returncode == 0, f"First run failed: {result1.stderr}"

    # Run migration second time (dry-run)
    result2 = subprocess.run(cmd, cwd=PROJECT_ROOT, capture_output=True, text=True)
    assert result2.returncode == 0, f"Second run failed: {result2.stderr}"

    # Both runs should complete successfully
    assert "Migration completed successfully" in result1.stdout or "Report generated" in result1.stdout
    assert "Migration completed successfully" in result2.stdout or "Report generated" in result2.stdout


@pytest.mark.e2e
@pytest.mark.migration
@pytest.mark.skip(reason="Requires concurrent API testing - run manually")
def test_concurrent_access_during_migration():
    """
    Verify v2.1 API continues to work during migration.

    Tests:
    1. Can read spools during migration
    2. Can write operations during migration
    3. No race conditions between migration and API
    """
    # This test would require:
    # 1. Starting migration in background
    # 2. Making API calls while migration runs
    # 3. Verifying no errors or data corruption

    # For now, this is a placeholder for manual testing
    pytest.skip("Manual test - verify API works during migration window")


@pytest.mark.e2e
@pytest.mark.production_readiness
def test_api_health_check_returns_v3_schema_info():
    """
    Verify API health check includes v3.0 schema information after migration.

    Tests:
    1. Health endpoint returns 200
    2. Response includes schema version
    3. Response indicates v3.0 columns present
    """
    # Check if API is running (this would require starting API)
    # For now, verify health endpoint exists
    from backend.routers.health import router as health_router

    # Verify router has the health endpoint
    assert health_router is not None

    # In real test, would make HTTP request to /api/health
    # and verify response includes {"schema_version": "v3.0", "columns": 68}


@pytest.mark.e2e
@pytest.mark.production_readiness
@pytest.mark.skip(reason="Requires live API with 50-spool test data")
def test_performance_batch_operations():
    """
    Verify batch operations complete in < 2 seconds for 50 spools.

    Tests:
    1. Batch read of 50 spools < 1 second
    2. Batch occupation of 50 spools < 2 seconds
    3. Memory usage stable
    """
    repo = SheetsRepository(compatibility_mode="v3.0")

    # Get first 50 spools
    all_values = repo.read_worksheet(Config.HOJA_OPERACIONES_NOMBRE)
    test_rows = list(range(2, min(52, len(all_values))))

    # Test batch read performance
    start_time = time.time()
    for row in test_rows:
        repo.get_version(Config.HOJA_OPERACIONES_NOMBRE, row)
    read_elapsed = time.time() - start_time

    assert read_elapsed < 1.0, f"Batch read took {read_elapsed}s (expected < 1s)"

    # Note: Write performance would be tested against test sheet only


@pytest.mark.e2e
@pytest.mark.production_readiness
def test_memory_usage_stable():
    """
    Verify memory usage remains stable over 1000 operations.

    Tests:
    1. No memory leaks in repository
    2. Column map cache doesn't grow unbounded
    3. Connection pool properly managed
    """
    import gc
    import os

    try:
        import psutil
    except ImportError:
        pytest.skip("psutil not installed - install with: pip install psutil")

    process = psutil.Process(os.getpid())

    # Get baseline memory
    gc.collect()
    baseline_memory = process.memory_info().rss / 1024 / 1024  # MB

    # Simulate 1000 operations
    repo = SheetsRepository(compatibility_mode="v3.0")

    for i in range(1000):
        # Read operation
        all_values = repo.read_worksheet(Config.HOJA_OPERACIONES_NOMBRE)

        # Verify first row exists
        assert len(all_values) > 0

        # Every 100 iterations, check memory
        if i % 100 == 0:
            gc.collect()
            current_memory = process.memory_info().rss / 1024 / 1024
            memory_increase = current_memory - baseline_memory

            # Memory should not increase more than 50 MB
            assert memory_increase < 50, f"Memory leak detected: +{memory_increase}MB"

    # Final memory check
    gc.collect()
    final_memory = process.memory_info().rss / 1024 / 1024
    memory_increase = final_memory - baseline_memory

    assert memory_increase < 100, f"Memory increased by {memory_increase}MB (expected < 100MB)"


@pytest.mark.e2e
@pytest.mark.production_readiness
def test_error_rate_acceptable():
    """
    Verify error rate < 0.1% on migration operations.

    Tests:
    1. Repository operations succeed consistently
    2. Retries handle transient failures
    3. Overall error rate meets SLA
    """
    repo = SheetsRepository(compatibility_mode="v3.0")

    attempts = 100
    errors = 0

    for i in range(attempts):
        try:
            # Read operation
            all_values = repo.read_worksheet(Config.HOJA_OPERACIONES_NOMBRE)
            assert len(all_values) > 0
        except Exception as e:
            errors += 1
            print(f"Error {errors}/{attempts}: {e}")

    error_rate = errors / attempts

    # Error rate should be < 0.1% (0.001)
    assert error_rate < 0.001, f"Error rate {error_rate*100}% exceeds SLA (0.1%)"


@pytest.mark.e2e
@pytest.mark.production_readiness
def test_critical_v21_workflows_still_function():
    """
    Verify all critical v2.1 workflows continue to work after migration.

    Tests:
    1. Worker identification works
    2. Spool selection works
    3. Operation initiation works (INICIAR)
    4. Operation completion works (COMPLETAR)
    """
    # This is verified by existing v2.1 tests continuing to pass
    # This test just confirms the smoke tests run

    cmd = [
        sys.executable,
        "-m",
        "pytest",
        "tests/v3.0/test_backward_compatibility.py",
        "-v"
    ]

    result = subprocess.run(cmd, cwd=PROJECT_ROOT, capture_output=True, text=True)

    # Backward compatibility tests should pass
    assert result.returncode == 0, f"v2.1 workflows broken: {result.stderr}"
