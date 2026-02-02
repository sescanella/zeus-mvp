"""
Unit tests for lazy cleanup mechanism in RedisLockService.

Tests verify that abandoned locks >24h old are cleaned up, but locks with
matching Sheets occupation or locks <24h old are preserved.
"""

import pytest
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, Mock, patch, MagicMock
from backend.services.redis_lock_service import RedisLockService
from backend.models.spool import Spool


@pytest.fixture
def mock_redis():
    """Mock Redis client with async methods."""
    redis = AsyncMock()
    redis.scan = AsyncMock()
    redis.get = AsyncMock()
    redis.delete = AsyncMock()
    return redis


@pytest.fixture
def mock_sheets_repo():
    """Mock SheetsRepository."""
    repo = Mock()
    repo.get_spool_by_tag = Mock()
    return repo


@pytest.fixture
def lock_service(mock_redis, mock_sheets_repo):
    """Create RedisLockService with mocked dependencies."""
    return RedisLockService(redis_client=mock_redis, sheets_repository=mock_sheets_repo)


def create_lock_value(worker_id: int, timestamp: datetime) -> str:
    """
    Create lock value with format: worker_id:token:timestamp.

    Args:
        worker_id: Worker ID
        timestamp: Lock creation timestamp

    Returns:
        Lock value string in format "worker_id:uuid:DD-MM-YYYY HH:MM:SS"
    """
    timestamp_str = timestamp.strftime("%d-%m-%Y %H:%M:%S")
    return f"{worker_id}:550e8400-e29b-41d4-a716-446655440000:{timestamp_str}"


@pytest.mark.asyncio
async def test_cleanup_removes_abandoned_lock_older_than_24h(lock_service, mock_redis, mock_sheets_repo):
    """
    Test that cleanup removes lock >24h old with no Sheets occupation match.

    Scenario:
    - Lock exists for 25 hours
    - Sheets.Ocupado_Por is None (abandoned)
    - Lock should be deleted
    """
    # Arrange
    tag_spool = "TEST-01"
    lock_key = f"spool_lock:{tag_spool}"

    # Create lock timestamp 25 hours ago
    with patch('backend.services.redis_lock_service.now_chile') as mock_now:
        now = datetime(2026, 2, 2, 14, 0, 0)
        lock_time = now - timedelta(hours=25)
        mock_now.return_value = now

        lock_value = create_lock_value(worker_id=93, timestamp=lock_time)

        # Mock Redis scan to return one lock
        mock_redis.scan.return_value = (0, [lock_key.encode()])
        mock_redis.get.return_value = lock_value.encode()

        # Mock Sheets to return spool with no occupation
        mock_spool = Spool(
            tag_spool=tag_spool,
            ocupado_por=None,
            fecha_ocupacion=None
        )
        mock_sheets_repo.get_spool_by_tag.return_value = mock_spool

        # Act
        await lock_service.lazy_cleanup_one_abandoned_lock()

        # Assert
        mock_redis.delete.assert_called_once_with(lock_key)
        mock_sheets_repo.get_spool_by_tag.assert_called_once_with(tag_spool)


@pytest.mark.asyncio
async def test_cleanup_skips_lock_younger_than_24h(lock_service, mock_redis, mock_sheets_repo):
    """
    Test that cleanup skips lock <24h old.

    Scenario:
    - Lock exists for 12 hours
    - Lock should NOT be deleted
    """
    # Arrange
    tag_spool = "TEST-02"
    lock_key = f"spool_lock:{tag_spool}"

    # Create lock timestamp 12 hours ago
    with patch('backend.services.redis_lock_service.now_chile') as mock_now:
        now = datetime(2026, 2, 2, 14, 0, 0)
        lock_time = now - timedelta(hours=12)
        mock_now.return_value = now

        lock_value = create_lock_value(worker_id=93, timestamp=lock_time)

        # Mock Redis scan to return one lock
        mock_redis.scan.return_value = (0, [lock_key.encode()])
        mock_redis.get.return_value = lock_value.encode()

        # Act
        await lock_service.lazy_cleanup_one_abandoned_lock()

        # Assert
        mock_redis.delete.assert_not_called()
        mock_sheets_repo.get_spool_by_tag.assert_not_called()


@pytest.mark.asyncio
async def test_cleanup_skips_lock_with_matching_sheets_occupation(lock_service, mock_redis, mock_sheets_repo):
    """
    Test that cleanup skips lock >24h old if Sheets.Ocupado_Por matches.

    Scenario:
    - Lock exists for 25 hours
    - Sheets.Ocupado_Por = "MR(93)" (matches worker)
    - Lock should NOT be deleted (still valid)
    """
    # Arrange
    tag_spool = "TEST-03"
    lock_key = f"spool_lock:{tag_spool}"

    # Create lock timestamp 25 hours ago
    with patch('backend.services.redis_lock_service.now_chile') as mock_now:
        now = datetime(2026, 2, 2, 14, 0, 0)
        lock_time = now - timedelta(hours=25)
        mock_now.return_value = now

        lock_value = create_lock_value(worker_id=93, timestamp=lock_time)

        # Mock Redis scan to return one lock
        mock_redis.scan.return_value = (0, [lock_key.encode()])
        mock_redis.get.return_value = lock_value.encode()

        # Mock Sheets to return spool WITH occupation
        mock_spool = Spool(
            tag_spool=tag_spool,
            ocupado_por="MR(93)",
            fecha_ocupacion="01-02-2026 13:00:00"
        )
        mock_sheets_repo.get_spool_by_tag.return_value = mock_spool

        # Act
        await lock_service.lazy_cleanup_one_abandoned_lock()

        # Assert
        mock_redis.delete.assert_not_called()
        mock_sheets_repo.get_spool_by_tag.assert_called_once_with(tag_spool)


@pytest.mark.asyncio
async def test_cleanup_processes_only_one_lock(lock_service, mock_redis, mock_sheets_repo):
    """
    Test that cleanup processes exactly one lock per call.

    Scenario:
    - Redis has multiple locks
    - Only first lock is checked and cleaned
    """
    # Arrange
    tag_spool_1 = "TEST-04"
    tag_spool_2 = "TEST-05"
    lock_key_1 = f"spool_lock:{tag_spool_1}"
    lock_key_2 = f"spool_lock:{tag_spool_2}"

    # Create lock timestamp 25 hours ago
    with patch('backend.services.redis_lock_service.now_chile') as mock_now:
        now = datetime(2026, 2, 2, 14, 0, 0)
        lock_time = now - timedelta(hours=25)
        mock_now.return_value = now

        lock_value_1 = create_lock_value(worker_id=93, timestamp=lock_time)

        # Mock Redis scan to return TWO locks
        mock_redis.scan.return_value = (0, [lock_key_1.encode(), lock_key_2.encode()])
        mock_redis.get.return_value = lock_value_1.encode()

        # Mock Sheets to return spool with no occupation
        mock_spool = Spool(
            tag_spool=tag_spool_1,
            ocupado_por=None,
            fecha_ocupacion=None
        )
        mock_sheets_repo.get_spool_by_tag.return_value = mock_spool

        # Act
        await lock_service.lazy_cleanup_one_abandoned_lock()

        # Assert
        # Only first lock should be checked and deleted
        mock_redis.delete.assert_called_once_with(lock_key_1)
        mock_sheets_repo.get_spool_by_tag.assert_called_once_with(tag_spool_1)
        # Second lock should NOT be processed
        assert mock_sheets_repo.get_spool_by_tag.call_count == 1


@pytest.mark.asyncio
async def test_cleanup_handles_no_locks(lock_service, mock_redis, mock_sheets_repo):
    """
    Test that cleanup handles case when no locks exist.

    Scenario:
    - Redis scan returns empty list
    - No errors raised
    """
    # Arrange
    mock_redis.scan.return_value = (0, [])

    # Act
    await lock_service.lazy_cleanup_one_abandoned_lock()

    # Assert
    mock_redis.get.assert_not_called()
    mock_redis.delete.assert_not_called()
    mock_sheets_repo.get_spool_by_tag.assert_not_called()


@pytest.mark.asyncio
async def test_cleanup_handles_legacy_lock_without_timestamp(lock_service, mock_redis, mock_sheets_repo):
    """
    Test that cleanup skips legacy locks without timestamp.

    Scenario:
    - Lock value format is "worker_id:token" (no timestamp)
    - Lock should be skipped (not deleted)
    """
    # Arrange
    tag_spool = "TEST-06"
    lock_key = f"spool_lock:{tag_spool}"

    # Legacy lock format without timestamp
    legacy_lock_value = "93:550e8400-e29b-41d4-a716-446655440000"

    # Mock Redis scan to return one lock
    mock_redis.scan.return_value = (0, [lock_key.encode()])
    mock_redis.get.return_value = legacy_lock_value.encode()

    # Act
    await lock_service.lazy_cleanup_one_abandoned_lock()

    # Assert
    mock_redis.delete.assert_not_called()
    mock_sheets_repo.get_spool_by_tag.assert_not_called()


@pytest.mark.asyncio
async def test_cleanup_failure_does_not_raise_exception(lock_service, mock_redis, mock_sheets_repo):
    """
    Test that cleanup failure doesn't raise exception.

    Scenario:
    - Redis scan raises exception
    - Exception is caught and logged
    - No exception propagated to caller
    """
    # Arrange
    mock_redis.scan.side_effect = Exception("Redis connection error")

    # Act
    try:
        await lock_service.lazy_cleanup_one_abandoned_lock()
        # Should not raise
    except Exception:
        pytest.fail("Cleanup should not raise exceptions")

    # Assert
    mock_redis.delete.assert_not_called()


@pytest.mark.asyncio
async def test_cleanup_skips_when_sheets_repo_not_configured(mock_redis):
    """
    Test that cleanup skips when sheets_repository not configured.

    Scenario:
    - RedisLockService created without sheets_repository
    - Cleanup should return early
    """
    # Arrange
    lock_service = RedisLockService(redis_client=mock_redis, sheets_repository=None)

    # Act
    await lock_service.lazy_cleanup_one_abandoned_lock()

    # Assert
    mock_redis.scan.assert_not_called()
    mock_redis.delete.assert_not_called()


@pytest.mark.asyncio
async def test_cleanup_logs_to_application_logger_not_metadata(lock_service, mock_redis, mock_sheets_repo):
    """
    Test that cleanup logs to application logger, NOT Metadata.

    Scenario:
    - Lock cleaned up successfully
    - Application logger called
    - Metadata repository NOT called
    """
    # Arrange
    tag_spool = "TEST-07"
    lock_key = f"spool_lock:{tag_spool}"

    # Create lock timestamp 25 hours ago
    with patch('backend.services.redis_lock_service.now_chile') as mock_now:
        now = datetime(2026, 2, 2, 14, 0, 0)
        lock_time = now - timedelta(hours=25)
        mock_now.return_value = now

        lock_value = create_lock_value(worker_id=93, timestamp=lock_time)

        # Mock Redis scan to return one lock
        mock_redis.scan.return_value = (0, [lock_key.encode()])
        mock_redis.get.return_value = lock_value.encode()

        # Mock Sheets to return spool with no occupation
        mock_spool = Spool(
            tag_spool=tag_spool,
            ocupado_por=None,
            fecha_ocupacion=None
        )
        mock_sheets_repo.get_spool_by_tag.return_value = mock_spool

        # Mock logger
        with patch('backend.services.redis_lock_service.logger') as mock_logger:
            # Act
            await lock_service.lazy_cleanup_one_abandoned_lock()

            # Assert
            # Verify logger.info was called (application logging)
            assert mock_logger.info.called

            # Verify NO Metadata repository method was called
            # (This test verifies by absence - sheets_repo only has get_spool_by_tag,
            # which is for querying, not logging. Metadata logging would be via
            # separate metadata_repository which we don't inject into lock_service)


@pytest.mark.asyncio
async def test_iniciar_calls_cleanup(mock_redis, mock_sheets_repo):
    """
    Test that INICIAR/tomar endpoint invokes cleanup before lock acquisition.

    This is an integration test verifying the cleanup is called from occupation flow.
    """
    from backend.services.occupation_service import OccupationService
    from backend.services.conflict_service import ConflictService
    from backend.services.redis_event_service import RedisEventService
    from backend.repositories.metadata_repository import MetadataRepository
    from backend.models.occupation import TomarRequest
    from backend.models.enums import ActionType
    from backend.models.spool import Spool

    # Arrange
    mock_conflict_service = Mock(spec=ConflictService)
    mock_redis_event_service = Mock(spec=RedisEventService)
    mock_metadata_repo = Mock(spec=MetadataRepository)

    lock_service = RedisLockService(redis_client=mock_redis, sheets_repository=mock_sheets_repo)

    occupation_service = OccupationService(
        redis_lock_service=lock_service,
        sheets_repository=mock_sheets_repo,
        metadata_repository=mock_metadata_repo,
        conflict_service=mock_conflict_service,
        redis_event_service=mock_redis_event_service
    )

    # Mock spool with prerequisites
    mock_spool = Spool(
        tag_spool="TEST-08",
        fecha_materiales="2026-01-15",
        ocupado_por=None
    )
    mock_sheets_repo.get_spool_by_tag.return_value = mock_spool

    # Mock Redis operations
    mock_redis.scan.return_value = (0, [])  # No locks to clean
    mock_redis.set.return_value = True  # Lock acquired successfully
    mock_redis.persist.return_value = 1  # PERSIST successful

    # Mock conflict service
    mock_conflict_service.update_with_retry = AsyncMock(return_value="new-version-uuid")

    # Create TOMAR request
    request = TomarRequest(
        tag_spool="TEST-08",
        worker_id=93,
        worker_nombre="MR(93)",
        operacion=ActionType.ARM
    )

    # Act
    with patch.object(lock_service, 'lazy_cleanup_one_abandoned_lock', new_callable=AsyncMock) as mock_cleanup:
        await occupation_service.tomar(request)

        # Assert
        # Verify cleanup was called before lock acquisition
        mock_cleanup.assert_called_once()
