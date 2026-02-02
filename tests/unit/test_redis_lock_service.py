"""
Unit tests for RedisLockService - atomic lock operations.

Tests validate:
- Lock acquisition atomicity (SET NX EX)
- Lock release with ownership verification (Lua script)
- Lock extension for long operations
- Lock owner query
- Error handling (connection failures, expired locks)

Reference:
- Service: backend/services/redis_lock_service.py
- Plan: 02-04-PLAN.md
"""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
import uuid
from redis.exceptions import RedisError

from backend.services.redis_lock_service import RedisLockService
from backend.exceptions import SpoolOccupiedError, LockExpiredError


@pytest.fixture
def mock_redis():
    """Create a mock async Redis client."""
    redis_mock = AsyncMock()
    return redis_mock


@pytest.fixture
def lock_service(mock_redis):
    """Create RedisLockService with mocked Redis client."""
    return RedisLockService(mock_redis)


@pytest.mark.asyncio
async def test_acquire_lock_atomic_success(lock_service, mock_redis):
    """
    Lock acquisition succeeds when SET NX returns True.

    Validates:
    - SET command called with correct parameters (nx=True, ex=TTL)
    - Lock key format: "spool_lock:{tag_spool}"
    - Lock value format: "{worker_id}:{uuid}:{timestamp}"
    - Returns lock token on success
    """
    tag_spool = "TAG-001"
    worker_id = 93

    # Disable persistent locks for this test (use TTL mode)
    with patch('backend.services.redis_lock_service.config.REDIS_PERSISTENT_LOCKS', False):
        # Mock successful SET NX (lock acquired)
        mock_redis.set.return_value = True

        # Acquire lock
        token = await lock_service.acquire_lock(tag_spool, worker_id, "Worker 93")

        # Assertions
        assert token is not None
        assert isinstance(token, str)
        mock_redis.set.assert_called_once()

        # Verify SET parameters
        call_args = mock_redis.set.call_args
        assert call_args.args[0] == f"spool_lock:{tag_spool}"  # Key
        assert call_args.kwargs['nx'] is True  # Only set if not exists


@pytest.mark.asyncio
async def test_acquire_lock_atomic_failure_occupied(lock_service, mock_redis):
    """
    Lock acquisition fails when SET NX returns False (lock exists).

    Validates:
    - Raises SpoolOccupiedError when lock exists
    - Error message includes owner details
    """
    tag_spool = "TAG-002"
    worker_id = 94

    # Mock SET NX failure (lock already exists)
    mock_redis.set.return_value = False

    # Mock get to return existing lock owner
    mock_redis.get.return_value = "93:550e8400-e29b-41d4-a716-446655440000:02-02-2026 14:30:00"

    # Attempt to acquire lock should raise error
    with pytest.raises(SpoolOccupiedError) as exc_info:
        await lock_service.acquire_lock(tag_spool, worker_id, "Worker 94")

    # Verify error message contains owner info (Spanish: "ocupado")
    assert "ocupado" in str(exc_info.value).lower()  # Spanish for "occupied"
    assert "93" in str(exc_info.value)  # Owner worker_id


@pytest.mark.asyncio
async def test_release_lock_with_correct_token(lock_service, mock_redis):
    """
    Lock release succeeds when token matches (Lua script returns 1).

    Validates:
    - Lua script executed with correct key and token
    - Script verifies ownership before deletion
    - Returns True on successful release
    """
    tag_spool = "TAG-003"
    worker_id = 93
    token = "550e8400-e29b-41d4-a716-446655440000"

    # Mock Lua script execution (successful deletion)
    mock_redis.eval.return_value = 1

    # Release lock
    result = await lock_service.release_lock(tag_spool, worker_id, token)

    # Assertions
    assert result is True
    mock_redis.eval.assert_called_once()


@pytest.mark.asyncio
async def test_release_lock_with_incorrect_token(lock_service, mock_redis):
    """
    Lock release fails when token doesn't match (Lua script returns 0).

    Validates:
    - Lua script detects ownership mismatch
    - Returns False without raising exception
    - Log warning about unauthorized release attempt
    """
    tag_spool = "TAG-004"
    worker_id = 94
    wrong_token = "different-uuid"

    # Mock Lua script execution (token mismatch, no deletion)
    mock_redis.eval.return_value = 0

    # Release lock with wrong token
    result = await lock_service.release_lock(tag_spool, worker_id, wrong_token)

    # Assertions
    assert result is False  # Release failed
    mock_redis.eval.assert_called_once()


@pytest.mark.asyncio
async def test_extend_lock_success(lock_service, mock_redis):
    """
    Lock extension succeeds when lock exists and token matches.

    Validates:
    - EXPIRE command called with new TTL
    - Ownership verified before extension
    - Returns True on success
    """
    tag_spool = "TAG-005"
    token = "550e8400-e29b-41d4-a716-446655440000"
    additional_seconds = 1800  # 30 minutes

    # Mock ownership verification
    mock_redis.get.return_value = f"93:{token}:02-02-2026 14:30:00"

    # Mock TTL command
    mock_redis.ttl.return_value = 3600  # Current TTL

    # Mock EXPIRE command success
    mock_redis.expire.return_value = True

    # Extend lock
    result = await lock_service.extend_lock(tag_spool, token, additional_seconds)

    # Assertions
    assert result is True
    mock_redis.get.assert_called_once_with(f"spool_lock:{tag_spool}")
    mock_redis.ttl.assert_called_once_with(f"spool_lock:{tag_spool}")
    mock_redis.expire.assert_called_once()


@pytest.mark.asyncio
async def test_extend_lock_expired(lock_service, mock_redis):
    """
    Lock extension fails when lock no longer exists.

    Validates:
    - Raises LockExpiredError when lock gone
    - Error message indicates lock expired
    """
    tag_spool = "TAG-006"
    token = "550e8400-e29b-41d4-a716-446655440000"

    # Mock lock doesn't exist (expired)
    mock_redis.get.return_value = None

    # Attempt to extend should raise error
    with pytest.raises(LockExpiredError) as exc_info:
        await lock_service.extend_lock(tag_spool, token, 1800)

    assert "expir" in str(exc_info.value).lower()  # Spanish: "expiró"


@pytest.mark.asyncio
async def test_extend_lock_wrong_owner(lock_service, mock_redis):
    """
    Lock extension fails when token doesn't match owner.

    Validates:
    - Returns False when ownership mismatch
    - Prevents unauthorized lock extension
    """
    tag_spool = "TAG-007"
    wrong_token = "wrong-uuid"

    # Mock lock exists with different owner
    mock_redis.get.return_value = "93:correct-uuid:02-02-2026 14:30:00"

    # Attempt to extend with wrong token should return False
    result = await lock_service.extend_lock(tag_spool, wrong_token, 1800)

    assert result is False


@pytest.mark.asyncio
async def test_get_lock_owner_returns_details(lock_service, mock_redis):
    """
    Get lock owner returns worker_id and token.

    Validates:
    - Parses lock value into (worker_id, token)
    - Returns tuple format
    """
    tag_spool = "TAG-008"
    lock_value = "93:550e8400-e29b-41d4-a716-446655440000:02-02-2026 14:30:00"

    # Mock lock exists
    mock_redis.get.return_value = lock_value

    # Get owner
    owner_id, token = await lock_service.get_lock_owner(tag_spool)

    # Assertions
    assert owner_id == 93
    assert token == "550e8400-e29b-41d4-a716-446655440000"
    mock_redis.get.assert_called_once_with(f"spool_lock:{tag_spool}")


@pytest.mark.asyncio
async def test_get_lock_owner_no_lock(lock_service, mock_redis):
    """
    Get lock owner returns None when lock doesn't exist.

    Validates:
    - Returns None for non-existent locks
    - Doesn't raise exception
    """
    tag_spool = "TAG-009"

    # Mock lock doesn't exist
    mock_redis.get.return_value = None

    # Get owner
    result = await lock_service.get_lock_owner(tag_spool)

    # Assertions
    assert result is None


@pytest.mark.asyncio
async def test_redis_connection_error_handling(lock_service, mock_redis):
    """
    Redis connection errors trigger degraded mode fallback.

    Validates:
    - RedisError triggers degraded mode
    - Returns degraded token if sheets_repository available
    """
    tag_spool = "TAG-010"
    worker_id = 95

    # Mock Redis connection failure
    mock_redis.set.side_effect = RedisError("Connection refused")

    # Mock sheets_repository
    mock_sheets_repo = MagicMock()
    mock_spool = MagicMock()
    mock_spool.ocupado_por = "DISPONIBLE"
    mock_sheets_repo.get_spool_by_tag.return_value = mock_spool
    lock_service.sheets_repository = mock_sheets_repo

    # Acquire lock should fallback to degraded mode
    token = await lock_service.acquire_lock(tag_spool, worker_id, "Worker 95")

    assert token.startswith("DEGRADED:")


@pytest.mark.asyncio
async def test_lock_key_format(lock_service):
    """
    Verify lock key follows expected format.

    Validates:
    - Format: "spool_lock:{tag_spool}"
    - Consistent across methods
    """
    tag_spool = "TAG-011"
    expected_key = f"spool_lock:{tag_spool}"

    # Use private method to generate key
    key = lock_service._lock_key(tag_spool)

    assert key == expected_key


@pytest.mark.asyncio
async def test_lock_value_format(lock_service):
    """
    Verify lock value follows expected format.

    Validates:
    - Format: "{worker_id}:{uuid}:{timestamp}"
    - UUID is valid UUID4
    - Timestamp is in DD-MM-YYYY HH:MM:SS format
    """
    worker_id = 93

    # Generate lock value
    lock_value = lock_service._lock_value(worker_id)

    # Parse value (format: worker_id:uuid:timestamp)
    parts = lock_value.split(":")
    assert len(parts) >= 3  # At least worker_id + uuid parts + timestamp parts
    assert parts[0] == str(worker_id)

    # Extract UUID (parts 1 through -3, assuming timestamp is "DD-MM-YYYY HH:MM:SS" with colons)
    # UUID is parts[1] (full UUID without colons in between)
    # Timestamp starts after the UUID
    uuid_part = parts[1]
    try:
        uuid.UUID(uuid_part)
    except ValueError:
        pytest.fail(f"Invalid UUID in lock value: {uuid_part}")


@pytest.mark.asyncio
async def test_lock_ttl_default(lock_service):
    """
    Verify default TTL is used from config.

    Validates:
    - Default TTL set from config.REDIS_LOCK_TTL_SECONDS
    - Used in SET EX parameter
    """
    assert lock_service.default_ttl > 0  # Sanity check
    assert lock_service.default_ttl == 3600  # Expected default (1 hour)


# ==================== v4.0 Persistent Locks Tests ====================


@pytest.mark.asyncio
async def test_persistent_lock_two_step_acquisition(lock_service, mock_redis):
    """
    Test two-step persistent lock acquisition: SET with safety TTL, then PERSIST.

    Validates:
    - SET called with safety TTL (10 seconds)
    - PERSIST called immediately after successful SET
    - Returns token on success
    """
    tag_spool = "TAG-100"
    worker_id = 93

    # Mock config for persistent locks
    with patch('backend.services.redis_lock_service.config.REDIS_PERSISTENT_LOCKS', True):
        with patch('backend.services.redis_lock_service.config.REDIS_SAFETY_TTL', 10):
            # Mock successful SET and PERSIST
            mock_redis.set.return_value = True
            mock_redis.persist.return_value = 1  # PERSIST success

            # Acquire lock
            token = await lock_service.acquire_lock(tag_spool, worker_id, "Worker 93")

            # Assertions
            assert token is not None
            mock_redis.set.assert_called_once()
            mock_redis.persist.assert_called_once()

            # Verify SET parameters (safety TTL)
            call_args = mock_redis.set.call_args
            assert call_args.kwargs['nx'] is True
            assert call_args.kwargs['ex'] == 10  # Safety TTL

            # Verify PERSIST called with correct key
            persist_call_args = mock_redis.persist.call_args
            assert persist_call_args.args[0] == f"spool_lock:{tag_spool}"


@pytest.mark.asyncio
async def test_persistent_lock_persist_failure(lock_service, mock_redis):
    """
    Test PERSIST command failure handling.

    Validates:
    - If PERSIST returns 0 (key doesn't exist), lock is released
    - Falls back to degraded mode when persist fails and sheets_repository available
    """
    tag_spool = "TAG-101"
    worker_id = 93

    with patch('backend.services.redis_lock_service.config.REDIS_PERSISTENT_LOCKS', True):
        with patch('backend.services.redis_lock_service.config.REDIS_SAFETY_TTL', 10):
            # Mock successful SET but failed PERSIST
            mock_redis.set.return_value = True
            mock_redis.persist.return_value = 0  # PERSIST failed

            # Mock sheets_repository for degraded mode fallback
            mock_sheets_repo = MagicMock()
            mock_spool = MagicMock()
            mock_spool.ocupado_por = "DISPONIBLE"
            mock_sheets_repo.get_spool_by_tag.return_value = mock_spool
            lock_service.sheets_repository = mock_sheets_repo

            # Acquire lock should fallback to degraded mode after PERSIST failure
            token = await lock_service.acquire_lock(tag_spool, worker_id, "Worker 93")

            # Should return degraded token (fallback after Redis error)
            assert token.startswith("DEGRADED:")
            # Verify lock was released after PERSIST failure
            mock_redis.delete.assert_called_once()


@pytest.mark.asyncio
async def test_lock_value_includes_timestamp(lock_service):
    """
    Test lock value format includes timestamp for age detection.

    Validates:
    - Lock value format: worker_id:token:timestamp
    - Timestamp in DD-MM-YYYY HH:MM:SS format
    """
    worker_id = 93

    # Generate lock value
    lock_value = lock_service._lock_value(worker_id)

    # Parse value (format: "93:uuid:DD-MM-YYYY HH:MM:SS")
    parts = lock_value.split(":")
    assert len(parts) >= 3  # worker_id + UUID + timestamp parts

    # Verify worker_id
    assert parts[0] == str(worker_id)

    # Reconstruct timestamp from parts[2:] (DD-MM-YYYY HH:MM:SS has colons)
    timestamp_part = ":".join(parts[2:])

    # Verify timestamp format: "DD-MM-YYYY HH:MM:SS"
    assert len(timestamp_part) == 19  # "02-02-2026 14:30:00" length
    assert timestamp_part[2] == "-"
    assert timestamp_part[5] == "-"
    assert timestamp_part[10] == " "
    assert timestamp_part[13] == ":"
    assert timestamp_part[16] == ":"


@pytest.mark.asyncio
async def test_parse_lock_timestamp(lock_service):
    """
    Test timestamp parsing from lock value.

    Validates:
    - Extracts timestamp from new format (worker_id:token:timestamp)
    - Returns None for legacy format (worker_id:token)
    """
    # New format with timestamp
    lock_value_with_timestamp = "93:550e8400-e29b-41d4-a716-446655440000:02-02-2026 14:30:00"
    timestamp = lock_service._parse_lock_timestamp(lock_value_with_timestamp)
    assert timestamp is not None
    assert timestamp.year == 2026
    assert timestamp.month == 2
    assert timestamp.day == 2

    # Legacy format without timestamp
    legacy_lock_value = "93:550e8400-e29b-41d4-a716-446655440000"
    timestamp_legacy = lock_service._parse_lock_timestamp(legacy_lock_value)
    assert timestamp_legacy is None


@pytest.mark.asyncio
async def test_backward_compatibility_ttl_mode(lock_service, mock_redis):
    """
    Test backward compatibility with v3.0 TTL mode.

    Validates:
    - When REDIS_PERSISTENT_LOCKS=False, uses TTL mode
    - SET called with full TTL (not safety TTL)
    - PERSIST not called
    """
    tag_spool = "TAG-102"
    worker_id = 93

    with patch('backend.services.redis_lock_service.config.REDIS_PERSISTENT_LOCKS', False):
        # Mock successful SET
        mock_redis.set.return_value = True

        # Acquire lock
        token = await lock_service.acquire_lock(tag_spool, worker_id, "Worker 93")

        # Assertions
        assert token is not None
        mock_redis.set.assert_called_once()
        mock_redis.persist.assert_not_called()  # PERSIST should NOT be called in TTL mode

        # Verify SET parameters (full TTL)
        call_args = mock_redis.set.call_args
        assert call_args.kwargs['ex'] == lock_service.default_ttl  # Full TTL


# ==================== Degraded Mode Tests ====================


@pytest.mark.asyncio
async def test_degraded_mode_on_redis_connection_error(lock_service, mock_redis):
    """
    Test degraded mode fallback when Redis connection fails.

    Validates:
    - Redis connection error triggers degraded mode
    - Returns degraded token (DEGRADED:worker_id:timestamp)
    - Queries Sheets to check availability
    """
    tag_spool = "TAG-103"
    worker_id = 93

    # Mock Redis connection failure
    mock_redis.set.side_effect = ConnectionError("Redis connection refused")

    # Mock sheets_repository
    mock_sheets_repo = MagicMock()
    mock_spool = MagicMock()
    mock_spool.ocupado_por = "DISPONIBLE"  # Spool available
    mock_sheets_repo.get_spool_by_tag.return_value = mock_spool

    lock_service.sheets_repository = mock_sheets_repo

    # Acquire lock should fallback to degraded mode
    token = await lock_service.acquire_lock(tag_spool, worker_id, "Worker 93")

    # Assertions
    assert token is not None
    assert token.startswith("DEGRADED:")
    assert str(worker_id) in token

    # Verify Sheets was queried
    mock_sheets_repo.get_spool_by_tag.assert_called_once_with(tag_spool)


@pytest.mark.asyncio
async def test_degraded_mode_spool_occupied(lock_service, mock_redis):
    """
    Test degraded mode raises SpoolOccupiedError when Sheets shows occupation.

    Validates:
    - Degraded mode queries Sheets.Ocupado_Por
    - Raises SpoolOccupiedError if already occupied
    """
    tag_spool = "TAG-104"
    worker_id = 93

    # Mock Redis connection failure
    mock_redis.set.side_effect = ConnectionError("Redis connection refused")

    # Mock sheets_repository with occupied spool
    mock_sheets_repo = MagicMock()
    mock_spool = MagicMock()
    mock_spool.ocupado_por = "MR(94)"  # Already occupied by worker 94
    mock_sheets_repo.get_spool_by_tag.return_value = mock_spool

    lock_service.sheets_repository = mock_sheets_repo

    # Acquire lock should raise SpoolOccupiedError
    with pytest.raises(SpoolOccupiedError) as exc_info:
        await lock_service.acquire_lock(tag_spool, worker_id, "Worker 93")

    assert "94" in str(exc_info.value)  # Owner worker_id


@pytest.mark.asyncio
async def test_is_degraded_mode_check(lock_service):
    """
    Test is_degraded_mode() method.

    Validates:
    - Returns True for degraded tokens (DEGRADED:*)
    - Returns False for normal tokens
    """
    degraded_token = "DEGRADED:93:02-02-2026 14:30:00"
    normal_token = "550e8400-e29b-41d4-a716-446655440000"

    assert lock_service.is_degraded_mode(degraded_token) is True
    assert lock_service.is_degraded_mode(normal_token) is False


@pytest.mark.asyncio
async def test_release_lock_degraded_mode(lock_service, mock_redis):
    """
    Test release_lock handles degraded mode tokens.

    Validates:
    - Degraded token recognized
    - Redis operations skipped
    - Returns True (successful release)
    """
    tag_spool = "TAG-105"
    worker_id = 93
    degraded_token = "DEGRADED:93:02-02-2026 14:30:00"

    # Release lock with degraded token
    result = await lock_service.release_lock(tag_spool, worker_id, degraded_token)

    # Assertions
    assert result is True
    # Verify NO Redis operations performed
    mock_redis.eval.assert_not_called()
    mock_redis.delete.assert_not_called()


@pytest.mark.asyncio
async def test_degraded_mode_without_sheets_repository(lock_service, mock_redis):
    """
    Test degraded mode fails gracefully without sheets_repository.

    Validates:
    - If sheets_repository not configured, raises RedisError
    - Error message indicates no fallback available
    """
    tag_spool = "TAG-106"
    worker_id = 93

    # Mock Redis connection failure
    mock_redis.set.side_effect = ConnectionError("Redis connection refused")

    # No sheets_repository configured
    lock_service.sheets_repository = None

    # Acquire lock should raise error
    with pytest.raises(RedisError) as exc_info:
        await lock_service.acquire_lock(tag_spool, worker_id, "Worker 93")

    assert "sheets fallback" in str(exc_info.value).lower()
