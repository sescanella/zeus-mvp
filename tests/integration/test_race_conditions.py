"""
Integration tests for race condition prevention in concurrent spool operations.

Tests validate that atomic Redis locking prevents double booking and ensures
exactly one worker can TOMAR a spool when multiple workers attempt simultaneously.

Reference:
- Plan: 02-04-PLAN.md
- Lock service: backend/services/redis_lock_service.py
"""
import asyncio
import pytest
from httpx import AsyncClient
from typing import List

# Base URL for FastAPI backend
BASE_URL = "http://localhost:8000"


@pytest.mark.asyncio
async def test_concurrent_tomar_prevents_double_booking():
    """
    10 workers try to TOMAR same spool simultaneously.

    Expected behavior:
    - Exactly 1 success (200 OK)
    - Exactly 9 conflicts (409 CONFLICT)
    - Only one Ocupado_Por value in Sheets

    Validates:
    - Redis SET NX EX atomic lock acquisition
    - SpoolOccupiedError -> 409 mapping
    - No race conditions in concurrent requests
    """
    tag_spool = "TEST-RACE-001"

    async def attempt_tomar(worker_id: int) -> int:
        """Attempt to TOMAR spool and return status code."""
        async with AsyncClient(base_url=BASE_URL, timeout=30.0) as client:
            try:
                response = await client.post(
                    "/api/occupation/tomar",
                    json={
                        "tag_spool": tag_spool,
                        "worker_id": worker_id,
                        "worker_nombre": f"Worker{worker_id}",
                        "operacion": "ARM"
                    }
                )
                return response.status_code
            except Exception as e:
                # If request fails, return 500 to track error
                print(f"Worker {worker_id} request failed: {e}")
                return 500

    # Launch 10 concurrent requests
    tasks = [attempt_tomar(i) for i in range(1, 11)]
    results = await asyncio.gather(*tasks, return_exceptions=False)

    # Count status codes
    success_count = sum(1 for r in results if r == 200)
    conflict_count = sum(1 for r in results if r == 409)
    error_count = sum(1 for r in results if r not in [200, 409])

    # Assertions
    assert success_count == 1, f"Expected 1 success, got {success_count}. Results: {results}"
    assert conflict_count == 9, f"Expected 9 conflicts, got {conflict_count}. Results: {results}"
    assert error_count == 0, f"Expected 0 errors, got {error_count}. Results: {results}"

    print(f"✅ Race condition test passed: 1 success, 9 conflicts out of 10 concurrent attempts")


@pytest.mark.asyncio
async def test_concurrent_pausar_only_owner_succeeds():
    """
    Multiple workers try to PAUSAR same spool, only owner succeeds.

    Expected behavior:
    - Worker who owns lock: 200 OK
    - Other workers: 403 FORBIDDEN

    Validates:
    - Lock ownership verification
    - NoAutorizadoError -> 403 mapping
    """
    tag_spool = "TEST-RACE-002"
    owner_id = 1

    # First, have owner TOMAR the spool
    async with AsyncClient(base_url=BASE_URL, timeout=30.0) as client:
        tomar_response = await client.post(
            "/api/occupation/tomar",
            json={
                "tag_spool": tag_spool,
                "worker_id": owner_id,
                "worker_nombre": f"Worker{owner_id}",
                "operacion": "ARM"
            }
        )
        assert tomar_response.status_code == 200, f"TOMAR failed: {tomar_response.text}"

    async def attempt_pausar(worker_id: int) -> int:
        """Attempt to PAUSAR spool and return status code."""
        async with AsyncClient(base_url=BASE_URL, timeout=30.0) as client:
            try:
                response = await client.post(
                    "/api/occupation/pausar",
                    json={
                        "tag_spool": tag_spool,
                        "worker_id": worker_id,
                        "worker_nombre": f"Worker{worker_id}"
                    }
                )
                return response.status_code
            except Exception as e:
                print(f"Worker {worker_id} PAUSAR failed: {e}")
                return 500

    # Launch 5 concurrent PAUSAR attempts (owner + 4 others)
    tasks = [attempt_pausar(i) for i in range(1, 6)]
    results = await asyncio.gather(*tasks, return_exceptions=False)

    # Count status codes
    success_count = sum(1 for r in results if r == 200)
    forbidden_count = sum(1 for r in results if r == 403)

    # Assertions - only owner (worker_id=1) should succeed
    assert success_count == 1, f"Expected 1 success (owner), got {success_count}. Results: {results}"
    assert forbidden_count == 4, f"Expected 4 forbidden, got {forbidden_count}. Results: {results}"

    print(f"✅ Ownership test passed: Only owner can PAUSAR")


@pytest.mark.asyncio
async def test_concurrent_completar_only_owner_succeeds():
    """
    Multiple workers try to COMPLETAR same spool, only owner succeeds.

    Expected behavior:
    - Worker who owns lock: 200 OK
    - Other workers: 403 FORBIDDEN

    Validates:
    - Lock ownership verification for COMPLETAR
    - NoAutorizadoError -> 403 mapping
    """
    tag_spool = "TEST-RACE-003"
    owner_id = 1

    # First, have owner TOMAR the spool
    async with AsyncClient(base_url=BASE_URL, timeout=30.0) as client:
        tomar_response = await client.post(
            "/api/occupation/tomar",
            json={
                "tag_spool": tag_spool,
                "worker_id": owner_id,
                "worker_nombre": f"Worker{owner_id}",
                "operacion": "ARM"
            }
        )
        assert tomar_response.status_code == 200, f"TOMAR failed: {tomar_response.text}"

    async def attempt_completar(worker_id: int) -> int:
        """Attempt to COMPLETAR spool and return status code."""
        async with AsyncClient(base_url=BASE_URL, timeout=30.0) as client:
            try:
                response = await client.post(
                    "/api/occupation/completar",
                    json={
                        "tag_spool": tag_spool,
                        "worker_id": worker_id,
                        "worker_nombre": f"Worker{worker_id}",
                        "fecha_operacion": "2026-01-27"
                    }
                )
                return response.status_code
            except Exception as e:
                print(f"Worker {worker_id} COMPLETAR failed: {e}")
                return 500

    # Launch 5 concurrent COMPLETAR attempts (owner + 4 others)
    tasks = [attempt_completar(i) for i in range(1, 6)]
    results = await asyncio.gather(*tasks, return_exceptions=False)

    # Count status codes
    success_count = sum(1 for r in results if r == 200)
    forbidden_count = sum(1 for r in results if r == 403)

    # Assertions - only owner (worker_id=1) should succeed
    assert success_count == 1, f"Expected 1 success (owner), got {success_count}. Results: {results}"
    assert forbidden_count == 4, f"Expected 4 forbidden, got {forbidden_count}. Results: {results}"

    print(f"✅ Ownership test passed: Only owner can COMPLETAR")


@pytest.mark.asyncio
async def test_batch_tomar_partial_success():
    """
    Batch TOMAR with 10 spools, 3 already occupied by other workers.

    Expected behavior:
    - 7 spools available -> 7 successes
    - 3 spools occupied -> 3 failures
    - Response indicates partial success

    Validates:
    - Batch operations handle partial success correctly
    - Each spool processed independently
    - Detailed per-spool results returned
    """
    # Pre-occupy 3 spools with different workers
    pre_occupied_spools = ["TEST-BATCH-001", "TEST-BATCH-004", "TEST-BATCH-007"]

    async with AsyncClient(base_url=BASE_URL, timeout=30.0) as client:
        for idx, spool in enumerate(pre_occupied_spools, start=1):
            response = await client.post(
                "/api/occupation/tomar",
                json={
                    "tag_spool": spool,
                    "worker_id": 90 + idx,  # Workers 91, 92, 93
                    "worker_nombre": f"PreWorker{90 + idx}",
                    "operacion": "ARM"
                }
            )
            assert response.status_code == 200, f"Pre-occupation failed for {spool}"

    # Attempt batch TOMAR of all 10 spools by Worker 1
    batch_spools = [f"TEST-BATCH-{i:03d}" for i in range(1, 11)]

    async with AsyncClient(base_url=BASE_URL, timeout=30.0) as client:
        batch_response = await client.post(
            "/api/occupation/batch-tomar",
            json={
                "tag_spools": batch_spools,
                "worker_id": 1,
                "worker_nombre": "Worker1",
                "operacion": "ARM"
            }
        )

    assert batch_response.status_code == 200, f"Batch request failed: {batch_response.text}"

    batch_data = batch_response.json()

    # Assertions
    assert batch_data["total"] == 10, f"Expected total=10, got {batch_data['total']}"
    assert batch_data["succeeded"] == 7, f"Expected succeeded=7, got {batch_data['succeeded']}"
    assert batch_data["failed"] == 3, f"Expected failed=3, got {batch_data['failed']}"

    # Verify failed spools match pre-occupied ones
    failed_tags = [detail["tag_spool"] for detail in batch_data["details"] if not detail["success"]]
    assert set(failed_tags) == set(pre_occupied_spools), f"Failed spools mismatch: {failed_tags}"

    print(f"✅ Batch partial success test passed: 7 succeeded, 3 failed out of 10 spools")


@pytest.mark.asyncio
async def test_version_conflict_retry():
    """
    Simulate version conflict and verify retry logic.

    Note: This test is challenging to implement at integration level
    without direct control over Sheet versioning. Consider mocking
    or testing at unit level in test_conflict_service.py instead.

    Expected behavior:
    - First attempt: Version mismatch -> VersionConflictError
    - Retry: New version acquired, operation succeeds

    Validates:
    - Optimistic locking with version tokens
    - Retry logic with exponential backoff
    - Eventually consistent operations
    """
    # This test may need to be implemented at unit test level
    # with mocked Sheet operations to control version conflicts
    pytest.skip("Version conflict testing better suited for unit tests with mocks")


@pytest.mark.asyncio
async def test_lock_expiration_after_ttl():
    """
    Verify lock expires after TTL and another worker can acquire.

    Note: This test requires waiting for TTL (default 3600s = 1 hour).
    For integration testing, consider:
    1. Using shorter TTL in test environment
    2. Implementing manual lock expiration via Redis
    3. Testing at unit level with mocked Redis

    Expected behavior:
    - Worker A TOMAss spool
    - Lock expires after TTL
    - Worker B can TOMAR same spool (not 409)

    Validates:
    - Redis EX flag sets proper expiration
    - Expired locks allow new acquisition
    - System self-heals from abandoned locks
    """
    # This test requires either:
    # 1. Configurable TTL for testing (e.g., 5 seconds)
    # 2. Direct Redis manipulation to expire key
    # 3. Unit test with mocked Redis
    pytest.skip("Lock expiration testing requires test-specific TTL configuration")
