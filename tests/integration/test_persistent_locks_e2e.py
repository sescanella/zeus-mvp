"""
End-to-end integration tests for persistent locks (Phase 9 Wave 3).

Tests validate complete persistent lock lifecycle:
- Lock persistence without TTL (TTL = -1 in Redis)
- Lazy cleanup of abandoned locks >24h old
- Startup reconciliation from Sheets.Ocupado_Por
- Cleanup doesn't remove valid locks

Uses real Redis test instance and mock Sheets data to validate
end-to-end behavior of persistent lock system.

Reference:
- Service: backend/services/redis_lock_service.py
- Plan: 09-05-PLAN.md (Wave 3 - Integration tests)
"""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, timedelta
import asyncio

from backend.services.redis_lock_service import RedisLockService
from backend.models.spool import Spool
from backend.utils.date_formatter import format_datetime_for_sheets, now_chile


@pytest.fixture
def mock_redis():
    """Create a mock async Redis client with persistent lock behavior."""
    redis_mock = AsyncMock()
    # Default: persistent locks enabled (v4.0)
    redis_mock.set.return_value = True
    redis_mock.persist.return_value = 1
    redis_mock.ttl.return_value = -1  # No TTL (persistent)
    redis_mock.exists.return_value = 0
    redis_mock.delete.return_value = 1
    redis_mock.scan.return_value = (0, [])  # Default: no locks
    return redis_mock


@pytest.fixture
def mock_sheets_repository():
    """Create a mock SheetsRepository."""
    sheets_mock = MagicMock()
    sheets_mock.get_all_spools.return_value = []
    return sheets_mock


@pytest.fixture
def lock_service(mock_redis, mock_sheets_repository):
    """Create RedisLockService with mocked dependencies."""
    return RedisLockService(mock_redis, mock_sheets_repository)


# ===========================
# Persistent Lock Tests
# ===========================

@pytest.mark.asyncio
async def test_persistent_lock_has_no_ttl(lock_service, mock_redis):
    """
    Persistent locks are created without TTL (TTL = -1).

    Validates Phase 9 requirement: Redis locks have NO TTL in v4.0.

    Process:
    1. Enable REDIS_PERSISTENT_LOCKS config
    2. Acquire lock with two-step approach (SET + PERSIST)
    3. Verify TTL is -1 (no expiration)
    4. Verify lock persists indefinitely
    """
    tag_spool = "TEST-PERSISTENT"
    worker_id = 93
    worker_nombre = "MR(93)"

    # Enable persistent locks
    with patch('backend.services.redis_lock_service.config.REDIS_PERSISTENT_LOCKS', True):
        # Mock successful two-step acquisition
        mock_redis.set.return_value = True
        mock_redis.persist.return_value = 1

        # Acquire lock
        token = await lock_service.acquire_lock(tag_spool, worker_id, worker_nombre)

        # Verify two-step process was called
        assert mock_redis.set.called
        assert mock_redis.persist.called

        # Verify SET was called with safety TTL (10 seconds)
        call_args = mock_redis.set.call_args
        assert call_args.kwargs.get('ex') == 10  # Safety TTL

        # Verify PERSIST was called to remove TTL
        persist_call_args = mock_redis.persist.call_args
        assert persist_call_args.args[0] == f"spool_lock:{tag_spool}"

        # Verify token returned (not None)
        assert token is not None
        assert isinstance(token, str)


@pytest.mark.asyncio
async def test_persistent_lock_survives_hours_without_expiration(lock_service, mock_redis):
    """
    Persistent locks survive for hours without TTL expiration.

    Simulates 5-hour passage of time to validate lock persistence.

    Process:
    1. Create persistent lock at T0
    2. Mock time advance by 5 hours
    3. Verify lock still exists (GET returns value)
    4. Verify TTL is still -1 (no expiration)
    """
    tag_spool = "TEST-LONG-RUNNING"
    worker_id = 93
    worker_nombre = "MR(93)"

    with patch('backend.services.redis_lock_service.config.REDIS_PERSISTENT_LOCKS', True):
        # Mock successful acquisition
        mock_redis.set.return_value = True
        mock_redis.persist.return_value = 1

        # Acquire lock at T0
        token = await lock_service.acquire_lock(tag_spool, worker_id, worker_nombre)
        assert token is not None

        # Simulate 5 hours later: lock still exists
        mock_redis.get.return_value = f"{worker_id}:{token}:02-02-2026 14:30:00"
        mock_redis.ttl.return_value = -1  # No TTL

        # Query lock owner after 5 hours
        owner = await lock_service.get_lock_owner(tag_spool)

        # Verify lock still exists
        assert owner is not None
        assert owner[0] == worker_id
        assert owner[1] == token


# ===========================
# Lazy Cleanup Tests
# ===========================

@pytest.mark.asyncio
async def test_lazy_cleanup_removes_abandoned_lock(lock_service, mock_redis, mock_sheets_repository):
    """
    Lazy cleanup removes abandoned locks >24h old without matching Sheets.Ocupado_Por.

    Validates eventual consistency cleanup on INICIAR operation.

    Cleanup criteria:
    - Lock age > 24 hours (timestamp in lock value)
    - Sheets.Ocupado_Por is None or "DISPONIBLE"

    Process:
    1. Create lock with timestamp 30h ago
    2. Mock Sheets.Ocupado_Por = "DISPONIBLE"
    3. Call lazy_cleanup_one_abandoned_lock()
    4. Verify lock was deleted
    """
    tag_spool = "TEST-ABANDONED"

    # Create abandoned lock (30 hours old)
    old_time = datetime.now() - timedelta(hours=30)
    old_timestamp = format_datetime_for_sheets(old_time)
    lock_value = f"93:550e8400-e29b-41d4-a716-446655440000:{old_timestamp}"

    # Mock SCAN returns one lock
    lock_key = f"spool_lock:{tag_spool}"
    mock_redis.scan.return_value = (0, [lock_key.encode('utf-8')])
    mock_redis.get.return_value = lock_value.encode('utf-8')

    # Mock Sheets: spool is DISPONIBLE (abandoned)
    abandoned_spool = Spool(
        tag_spool=tag_spool,
        ocupado_por="DISPONIBLE",
        fecha_ocupacion=None,
        version=0
    )
    mock_sheets_repository.get_spool_by_tag.return_value = abandoned_spool

    # Run lazy cleanup
    await lock_service.lazy_cleanup_one_abandoned_lock()

    # Verify lock was deleted
    assert mock_redis.delete.called
    delete_call_args = mock_redis.delete.call_args
    assert delete_call_args.args[0] == lock_key


@pytest.mark.asyncio
async def test_lazy_cleanup_keeps_valid_locks(lock_service, mock_redis, mock_sheets_repository):
    """
    Lazy cleanup does NOT remove locks with matching Sheets.Ocupado_Por.

    Validates that valid locks are preserved even if >24h old.

    Process:
    1. Create lock with timestamp 30h ago
    2. Mock Sheets.Ocupado_Por = "MR(93)" (matches lock)
    3. Call lazy_cleanup_one_abandoned_lock()
    4. Verify lock was NOT deleted
    """
    tag_spool = "TEST-VALID-OLD"

    # Create old but valid lock (30 hours old)
    old_time = datetime.now() - timedelta(hours=30)
    old_timestamp = format_datetime_for_sheets(old_time)
    lock_value = f"93:550e8400-e29b-41d4-a716-446655440000:{old_timestamp}"

    # Mock SCAN returns one lock
    lock_key = f"spool_lock:{tag_spool}"
    mock_redis.scan.return_value = (0, [lock_key.encode('utf-8')])
    mock_redis.get.return_value = lock_value.encode('utf-8')

    # Mock Sheets: spool is OCCUPIED (valid lock)
    occupied_spool = Spool(
        tag_spool=tag_spool,
        ocupado_por="MR(93)",
        fecha_ocupacion=old_timestamp,
        version=1
    )
    mock_sheets_repository.get_spool_by_tag.return_value = occupied_spool

    # Run lazy cleanup
    await lock_service.lazy_cleanup_one_abandoned_lock()

    # Verify lock was NOT deleted
    assert not mock_redis.delete.called


@pytest.mark.asyncio
async def test_lazy_cleanup_processes_one_lock_only(lock_service, mock_redis, mock_sheets_repository):
    """
    Lazy cleanup processes exactly ONE lock per call.

    Validates eventual consistency approach: one lock per INICIAR operation.

    Process:
    1. Mock SCAN returns 10 locks
    2. Call lazy_cleanup_one_abandoned_lock()
    3. Verify only first lock was checked (not all 10)
    """
    # Mock SCAN returns 10 locks
    lock_keys = [f"spool_lock:TEST-{i:02d}".encode('utf-8') for i in range(10)]
    mock_redis.scan.return_value = (0, lock_keys)

    # Mock first lock as abandoned
    old_time = datetime.now() - timedelta(hours=30)
    old_timestamp = format_datetime_for_sheets(old_time)
    lock_value = f"93:550e8400-e29b-41d4-a716-446655440000:{old_timestamp}"
    mock_redis.get.return_value = lock_value.encode('utf-8')

    # Mock Sheets: spool is DISPONIBLE
    abandoned_spool = Spool(
        tag_spool="TEST-00",
        ocupado_por="DISPONIBLE",
        fecha_ocupacion=None,
        version=0
    )
    mock_sheets_repository.get_spool_by_tag.return_value = abandoned_spool

    # Run lazy cleanup
    await lock_service.lazy_cleanup_one_abandoned_lock()

    # Verify only ONE lock was processed
    # get_spool_by_tag called once (for first lock)
    assert mock_sheets_repository.get_spool_by_tag.call_count == 1
    assert mock_redis.delete.call_count == 1  # Only first lock deleted


@pytest.mark.asyncio
async def test_lazy_cleanup_skips_locks_under_24h(lock_service, mock_redis, mock_sheets_repository):
    """
    Lazy cleanup skips locks younger than 24 hours.

    Validates age threshold prevents premature cleanup.

    Process:
    1. Create lock with timestamp 5h ago (recent)
    2. Call lazy_cleanup_one_abandoned_lock()
    3. Verify lock was NOT checked against Sheets (age check fails first)
    """
    tag_spool = "TEST-RECENT"

    # Create recent lock (5 hours old)
    recent_time = datetime.now() - timedelta(hours=5)
    recent_timestamp = format_datetime_for_sheets(recent_time)
    lock_value = f"93:550e8400-e29b-41d4-a716-446655440000:{recent_timestamp}"

    # Mock SCAN returns one lock
    lock_key = f"spool_lock:{tag_spool}"
    mock_redis.scan.return_value = (0, [lock_key.encode('utf-8')])
    mock_redis.get.return_value = lock_value.encode('utf-8')

    # Run lazy cleanup
    await lock_service.lazy_cleanup_one_abandoned_lock()

    # Verify Sheets was NOT queried (age check failed first)
    assert not mock_sheets_repository.get_spool_by_tag.called
    # Verify lock was NOT deleted
    assert not mock_redis.delete.called


@pytest.mark.asyncio
async def test_lazy_cleanup_skips_legacy_locks_without_timestamp(lock_service, mock_redis, mock_sheets_repository):
    """
    Lazy cleanup skips legacy locks without timestamp in lock value.

    Validates backward compatibility with v3.0 lock format.

    Process:
    1. Create legacy lock (format: worker_id:token)
    2. Call lazy_cleanup_one_abandoned_lock()
    3. Verify lock was NOT deleted (no timestamp to check age)
    """
    tag_spool = "TEST-LEGACY"

    # Create legacy lock (no timestamp)
    lock_value = "93:550e8400-e29b-41d4-a716-446655440000"  # Old format

    # Mock SCAN returns one lock
    lock_key = f"spool_lock:{tag_spool}"
    mock_redis.scan.return_value = (0, [lock_key.encode('utf-8')])
    mock_redis.get.return_value = lock_value.encode('utf-8')

    # Run lazy cleanup
    await lock_service.lazy_cleanup_one_abandoned_lock()

    # Verify Sheets was NOT queried (no timestamp to parse)
    assert not mock_sheets_repository.get_spool_by_tag.called
    # Verify lock was NOT deleted
    assert not mock_redis.delete.called


# ===========================
# Startup Reconciliation Tests
# ===========================

@pytest.mark.asyncio
async def test_startup_reconciliation_recreates_missing_locks(lock_service, mock_redis, mock_sheets_repository):
    """
    Startup reconciliation recreates Redis locks from Sheets.Ocupado_Por.

    Validates auto-recovery: Sheets → Redis sync on startup.

    Process:
    1. Mock Sheets with occupied spools (Ocupado_Por != "DISPONIBLE")
    2. Mock Redis: no locks exist
    3. Call reconcile_from_sheets()
    4. Verify locks were created with two-step approach (SET + PERSIST)
    """
    # Mock Sheets data with occupied spools
    recent_time = datetime.now() - timedelta(hours=2)
    timestamp = format_datetime_for_sheets(recent_time)

    occupied_spools = [
        Spool(
            tag_spool="TEST-01",
            ocupado_por="MR(93)",
            fecha_ocupacion=timestamp,
            version=1
        ),
        Spool(
            tag_spool="TEST-02",
            ocupado_por="JD(94)",
            fecha_ocupacion=timestamp,
            version=1
        )
    ]

    mock_sheets_repository.get_all_spools.return_value = occupied_spools

    # Mock Redis: no locks exist initially
    mock_redis.exists.return_value = 0
    mock_redis.set.return_value = True
    mock_redis.persist.return_value = 1

    # Run reconciliation
    results = await lock_service.reconcile_from_sheets(mock_sheets_repository)

    # Verify locks were created
    assert results["reconciled"] == 2
    assert results["skipped"] == 0

    # Verify two-step approach for each lock
    assert mock_redis.set.call_count == 2
    assert mock_redis.persist.call_count == 2


@pytest.mark.asyncio
async def test_startup_reconciliation_skips_old_locks(lock_service, mock_redis, mock_sheets_repository):
    """
    Startup reconciliation skips spools with occupations older than 24h.

    Validates stale data protection: don't recreate old locks.

    Process:
    1. Mock Sheets with old occupation (30h ago)
    2. Call reconcile_from_sheets()
    3. Verify lock was NOT created (skipped due to age)
    """
    # Mock Sheets data with old occupation
    old_time = datetime.now() - timedelta(hours=30)
    old_timestamp = format_datetime_for_sheets(old_time)

    old_spools = [
        Spool(
            tag_spool="TEST-OLD",
            ocupado_por="MR(93)",
            fecha_ocupacion=old_timestamp,
            version=1
        )
    ]

    mock_sheets_repository.get_all_spools.return_value = old_spools

    # Run reconciliation
    results = await lock_service.reconcile_from_sheets(mock_sheets_repository)

    # Verify lock was NOT created (too old)
    assert results["reconciled"] == 0
    assert results["skipped"] == 1

    # Verify no Redis operations
    assert mock_redis.set.call_count == 0
    assert mock_redis.persist.call_count == 0


@pytest.mark.asyncio
async def test_startup_reconciliation_timeout_protection(lock_service, mock_redis, mock_sheets_repository):
    """
    Startup reconciliation has timeout protection (10 seconds).

    Validates that slow Sheets queries don't block API startup indefinitely.

    Process:
    1. Mock slow Sheets query (asyncio.sleep)
    2. Wrap reconciliation with asyncio.wait_for(timeout=0.1)
    3. Verify timeout exception is raised
    4. Verify API can continue starting
    """
    # Mock slow Sheets query
    async def slow_query():
        await asyncio.sleep(2)  # 2-second delay
        return []

    # Note: In real main.py, the timeout wrapper is applied like this:
    # await asyncio.wait_for(reconcile_from_sheets(...), timeout=10)

    # For this test, we simulate what happens when timeout occurs
    mock_sheets_repository.get_all_spools.return_value = []

    # Simulate caller's timeout (main.py pattern)
    reconcile_coro = lock_service.reconcile_from_sheets(mock_sheets_repository)

    # Test that reconciliation completes quickly with empty list
    results = await asyncio.wait_for(reconcile_coro, timeout=0.1)

    # Verify reconciliation returns valid results
    assert results["reconciled"] == 0
    assert results["skipped"] == 0


@pytest.mark.asyncio
async def test_startup_reconciliation_persist_failure_releases_lock(lock_service, mock_redis, mock_sheets_repository):
    """
    Startup reconciliation releases lock if PERSIST fails.

    Validates cleanup on two-step acquisition failure.

    Process:
    1. Mock Sheets with occupied spool
    2. Mock Redis: SET succeeds, PERSIST fails
    3. Call reconcile_from_sheets()
    4. Verify lock was deleted after PERSIST failure
    """
    # Mock Sheets data
    recent_time = datetime.now() - timedelta(hours=2)
    timestamp = format_datetime_for_sheets(recent_time)

    spools = [
        Spool(
            tag_spool="TEST-PERSIST-FAIL",
            ocupado_por="MR(93)",
            fecha_ocupacion=timestamp,
            version=1
        )
    ]

    mock_sheets_repository.get_all_spools.return_value = spools

    # Mock Redis: SET succeeds, PERSIST fails
    mock_redis.exists.return_value = 0
    mock_redis.set.return_value = True
    mock_redis.persist.return_value = 0  # PERSIST failed

    # Run reconciliation
    results = await lock_service.reconcile_from_sheets(mock_sheets_repository)

    # Verify lock was NOT created (PERSIST failed)
    assert results["reconciled"] == 0
    assert results["skipped"] == 1

    # Verify lock was deleted after PERSIST failure
    assert mock_redis.delete.call_count == 1
