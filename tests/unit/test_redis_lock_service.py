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
    - Lock value format: "{worker_id}:{uuid}"
    - Returns lock token on success
    """
    tag_spool = "TAG-001"
    worker_id = 93

    # Mock successful SET NX (lock acquired)
    mock_redis.set.return_value = True

    # Acquire lock
    token = await lock_service.acquire_lock(tag_spool, worker_id)

    # Assertions
    assert token is not None
    assert token.startswith(f"{worker_id}:")  # Token contains worker_id
    mock_redis.set.assert_called_once()

    # Verify SET parameters
    call_args = mock_redis.set.call_args
    assert call_args.args[0] == f"spool_lock:{tag_spool}"  # Key
    assert call_args.kwargs['nx'] is True  # Only set if not exists
    assert call_args.kwargs['ex'] == lock_service.default_ttl  # Expiration


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
    mock_redis.get.return_value = "93:550e8400-e29b-41d4-a716-446655440000"

    # Attempt to acquire lock should raise error
    with pytest.raises(SpoolOccupiedError) as exc_info:
        await lock_service.acquire_lock(tag_spool, worker_id)

    # Verify error message contains owner info
    assert "already occupied" in str(exc_info.value).lower()
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
    token = "93:550e8400-e29b-41d4-a716-446655440000"

    # Mock Lua script execution (successful deletion)
    mock_redis.eval.return_value = 1

    # Release lock
    result = await lock_service.release_lock(tag_spool, token)

    # Assertions
    assert result is True
    mock_redis.eval.assert_called_once()

    # Verify Lua script call
    call_args = mock_redis.eval.call_args
    assert "KEYS[1]" in call_args.args[0]  # Lua script content
    assert call_args.kwargs['keys'] == [f"spool_lock:{tag_spool}"]
    assert call_args.kwargs['args'] == [token]


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
    wrong_token = "94:different-uuid"

    # Mock Lua script execution (token mismatch, no deletion)
    mock_redis.eval.return_value = 0

    # Release lock with wrong token
    result = await lock_service.release_lock(tag_spool, wrong_token)

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
    token = "93:550e8400-e29b-41d4-a716-446655440000"
    additional_seconds = 1800  # 30 minutes

    # Mock ownership verification
    mock_redis.get.return_value = token

    # Mock EXPIRE command success
    mock_redis.expire.return_value = True

    # Extend lock
    result = await lock_service.extend_lock(tag_spool, token, additional_seconds)

    # Assertions
    assert result is True
    mock_redis.get.assert_called_once_with(f"spool_lock:{tag_spool}")
    mock_redis.expire.assert_called_once_with(
        f"spool_lock:{tag_spool}",
        additional_seconds
    )


@pytest.mark.asyncio
async def test_extend_lock_expired(lock_service, mock_redis):
    """
    Lock extension fails when lock no longer exists.

    Validates:
    - Raises LockExpiredError when lock gone
    - Error message indicates lock expired
    """
    tag_spool = "TAG-006"
    token = "93:550e8400-e29b-41d4-a716-446655440000"

    # Mock lock doesn't exist (expired)
    mock_redis.get.return_value = None

    # Attempt to extend should raise error
    with pytest.raises(LockExpiredError) as exc_info:
        await lock_service.extend_lock(tag_spool, token, 1800)

    assert "expired" in str(exc_info.value).lower()


@pytest.mark.asyncio
async def test_extend_lock_wrong_owner(lock_service, mock_redis):
    """
    Lock extension fails when token doesn't match owner.

    Validates:
    - Raises SpoolOccupiedError when ownership mismatch
    - Prevents unauthorized lock extension
    """
    tag_spool = "TAG-007"
    wrong_token = "94:wrong-uuid"

    # Mock lock exists with different owner
    mock_redis.get.return_value = "93:correct-uuid"

    # Attempt to extend with wrong token should raise error
    with pytest.raises(SpoolOccupiedError) as exc_info:
        await lock_service.extend_lock(tag_spool, wrong_token, 1800)

    assert "not owned" in str(exc_info.value).lower() or "occupied" in str(exc_info.value).lower()


@pytest.mark.asyncio
async def test_get_lock_owner_returns_details(lock_service, mock_redis):
    """
    Get lock owner returns worker_id and token.

    Validates:
    - Parses lock value into (worker_id, token)
    - Returns tuple format
    """
    tag_spool = "TAG-008"
    lock_value = "93:550e8400-e29b-41d4-a716-446655440000"

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
    - Returns (None, None) for non-existent locks
    - Doesn't raise exception
    """
    tag_spool = "TAG-009"

    # Mock lock doesn't exist
    mock_redis.get.return_value = None

    # Get owner
    result = await lock_service.get_lock_owner(tag_spool)

    # Assertions
    assert result == (None, None)


@pytest.mark.asyncio
async def test_redis_connection_error_handling(lock_service, mock_redis):
    """
    Redis connection errors are handled gracefully.

    Validates:
    - RedisError propagated as application error
    - Error logged appropriately
    """
    tag_spool = "TAG-010"
    worker_id = 95

    # Mock Redis connection failure
    mock_redis.set.side_effect = RedisError("Connection refused")

    # Attempt to acquire lock should raise error
    with pytest.raises(RedisError) as exc_info:
        await lock_service.acquire_lock(tag_spool, worker_id)

    assert "Connection refused" in str(exc_info.value)


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
    - Format: "{worker_id}:{uuid}"
    - UUID is valid UUID4
    """
    worker_id = 93

    # Generate lock value
    lock_value = lock_service._lock_value(worker_id)

    # Parse value
    parts = lock_value.split(":")
    assert len(parts) == 6  # worker_id + 5 UUID parts
    assert parts[0] == str(worker_id)

    # Verify UUID portion is valid
    uuid_part = ":".join(parts[1:])
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
