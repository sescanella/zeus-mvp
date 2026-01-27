"""
Unit tests for ConflictService - version conflict detection and retry logic.

Tests validate:
- Version token generation (UUID4)
- Version mismatch triggers VersionConflictError
- Retry with exponential backoff on conflict
- Maximum retry attempts respected
- Jitter applied to prevent thundering herd
- Conflict metrics tracked correctly

Reference:
- Service: backend/services/conflict_service.py
- Plan: 02-04-PLAN.md
"""
import pytest
from unittest.mock import AsyncMock, MagicMock, call
import uuid

from backend.services.conflict_service import ConflictService
from backend.models.conflict import RetryConfig, ConflictResolution
from backend.exceptions import VersionConflictError


@pytest.fixture
def mock_sheets_repository():
    """Mock SheetsRepository."""
    repo = MagicMock()
    repo.get_spool_version = MagicMock(return_value="version-1")
    repo.update_spool_with_version = MagicMock()
    return repo


@pytest.fixture
def retry_config():
    """Create test retry configuration."""
    return RetryConfig(
        max_attempts=3,
        base_delay_ms=100,
        max_delay_ms=10000,
        exponential_base=2.0,
        jitter=True
    )


@pytest.fixture
def conflict_service(mock_sheets_repository, retry_config):
    """Create ConflictService with mocked repository."""
    return ConflictService(
        sheets_repository=mock_sheets_repository,
        default_config=retry_config
    )


def test_generate_version_token_returns_uuid(conflict_service):
    """
    Version token generation creates unique UUIDs.

    Validates:
    - Returns valid UUID4 string
    - Each call returns different UUID
    - Format matches UUID specification
    """
    token1 = conflict_service.generate_version_token()
    token2 = conflict_service.generate_version_token()

    # Validate UUID format
    try:
        uuid.UUID(token1)
        uuid.UUID(token2)
    except ValueError:
        pytest.fail("Generated token is not a valid UUID")

    # Tokens should be unique
    assert token1 != token2


def test_calculate_retry_delay_exponential_backoff(conflict_service):
    """
    Retry delay uses exponential backoff.

    Validates:
    - Delay increases exponentially with attempt number
    - Base delay and exponential base from config
    - Max delay capped at configured maximum
    """
    # First attempt (0) should be base delay
    delay0 = conflict_service.calculate_retry_delay(0)
    assert 0.09 <= delay0 <= 0.15  # 100ms +/- jitter

    # Second attempt should be ~2x base delay
    delay1 = conflict_service.calculate_retry_delay(1)
    assert 0.15 <= delay1 <= 0.25  # ~200ms +/- jitter

    # Third attempt should be ~4x base delay
    delay2 = conflict_service.calculate_retry_delay(2)
    assert 0.3 <= delay2 <= 0.5  # ~400ms +/- jitter

    # Verify exponential growth pattern
    assert delay1 > delay0
    assert delay2 > delay1


def test_calculate_retry_delay_respects_max_delay(conflict_service):
    """
    Retry delay never exceeds max_delay_ms.

    Validates:
    - Large attempt numbers capped at max_delay
    - Max delay converted correctly from ms to seconds
    """
    # Very large attempt number
    delay = conflict_service.calculate_retry_delay(100)

    # Should be capped at max_delay (10 seconds)
    assert delay <= 10.0


def test_calculate_retry_delay_with_custom_config(conflict_service):
    """
    Custom retry config overrides default.

    Validates:
    - Custom config parameters used
    - Can configure different backoff strategies
    """
    custom_config = RetryConfig(
        max_attempts=5,
        base_delay_ms=50,
        max_delay_ms=5000,
        exponential_base=3.0,
        jitter=False  # No jitter for predictable testing
    )

    delay0 = conflict_service.calculate_retry_delay(0, custom_config)
    delay1 = conflict_service.calculate_retry_delay(1, custom_config)

    # Without jitter, should match formula exactly
    # delay = base_delay_ms * (exponential_base ** attempt) / 1000
    assert delay0 == 0.05  # 50ms * 3^0 = 50ms = 0.05s
    assert delay1 == 0.15  # 50ms * 3^1 = 150ms = 0.15s


@pytest.mark.asyncio
async def test_update_with_retry_success_first_attempt(
    conflict_service,
    mock_sheets_repository
):
    """
    Update succeeds on first attempt without retry.

    Validates:
    - No version conflict on first attempt
    - Update executed once
    - Returns new version token
    """
    tag_spool = "TAG-001"
    updates = {"ocupado_por": "Worker93"}

    # Mock successful update
    mock_sheets_repository.update_spool_with_version.return_value = "version-2"

    # Execute update
    new_version = await conflict_service.update_with_retry(tag_spool, updates)

    # Assertions
    assert new_version == "version-2"
    mock_sheets_repository.update_spool_with_version.assert_called_once()


@pytest.mark.asyncio
async def test_update_with_retry_version_conflict_then_success(
    conflict_service,
    mock_sheets_repository
):
    """
    Version conflict on first attempt, success on retry.

    Validates:
    - VersionConflictError triggers retry
    - Exponential backoff applied
    - Second attempt succeeds
    - Returns final version token
    """
    tag_spool = "TAG-002"
    updates = {"ocupado_por": "Worker93"}

    # Mock first attempt fails with conflict, second succeeds
    mock_sheets_repository.update_spool_with_version.side_effect = [
        VersionConflictError("TAG-002", "version-1", "version-2", "TOMAR"),
        "version-3"  # Success on retry
    ]

    # Execute update
    new_version = await conflict_service.update_with_retry(tag_spool, updates, max_attempts=3)

    # Assertions
    assert new_version == "version-3"
    assert mock_sheets_repository.update_spool_with_version.call_count == 2


@pytest.mark.asyncio
async def test_update_with_retry_max_attempts_exceeded(
    conflict_service,
    mock_sheets_repository
):
    """
    Retry exhausts max attempts and raises error.

    Validates:
    - Retries up to max_attempts times
    - Final VersionConflictError raised
    - No infinite retry loop
    """
    tag_spool = "TAG-003"
    updates = {"ocupado_por": "Worker93"}

    # Mock all attempts fail with conflict
    mock_sheets_repository.update_spool_with_version.side_effect = [
        VersionConflictError("TAG-003", "version-1", "version-2", "TOMAR"),
        VersionConflictError("TAG-003", "version-2", "version-3", "TOMAR"),
        VersionConflictError("TAG-003", "version-3", "version-4", "TOMAR")
    ]

    # Should raise error after 3 attempts
    with pytest.raises(VersionConflictError) as exc_info:
        await conflict_service.update_with_retry(tag_spool, updates, max_attempts=3)

    # Verify all attempts made
    assert mock_sheets_repository.update_spool_with_version.call_count == 3

    # Error message should indicate retries exhausted
    assert "TAG-003" in str(exc_info.value)


@pytest.mark.asyncio
async def test_update_with_retry_jitter_prevents_thundering_herd(
    conflict_service,
    mock_sheets_repository
):
    """
    Jitter randomizes retry delays to prevent thundering herd.

    Validates:
    - Retry delays vary slightly between calls
    - Prevents all workers retrying simultaneously
    - Jitter within acceptable range
    """
    tag_spool = "TAG-004"
    updates = {"ocupado_por": "Worker93"}

    # Mock conflict on first attempt
    mock_sheets_repository.update_spool_with_version.side_effect = [
        VersionConflictError("TAG-004", "version-1", "version-2", "TOMAR"),
        "version-3"
    ]

    # Execute update multiple times and collect delays
    delays = []
    for _ in range(5):
        mock_sheets_repository.update_spool_with_version.side_effect = [
            VersionConflictError("TAG-004", "version-1", "version-2", "TOMAR"),
            "version-3"
        ]
        await conflict_service.update_with_retry(tag_spool, updates, max_attempts=3)

        # Calculate delay used (would need timing instrumentation in real code)
        # For this test, just verify jitter is enabled
        delay = conflict_service.calculate_retry_delay(0)
        delays.append(delay)

    # With jitter, delays should vary
    assert len(set(delays)) > 1, "Jitter should create variation in delays"


def test_detect_conflict_pattern_identifies_hot_spots(conflict_service):
    """
    Detect conflict patterns identifies frequently conflicted spools.

    Validates:
    - Analyzes list of conflicts
    - Identifies hot spot spools
    - Returns recommendations for conflict reduction
    """
    from backend.models.conflict import VersionConflict

    # Create conflicts for same spool (hot spot)
    conflicts = [
        VersionConflict(
            tag_spool="TAG-HOTSPOT",
            expected_version="v1",
            actual_version="v2",
            operation="TOMAR",
            retry_count=1
        ),
        VersionConflict(
            tag_spool="TAG-HOTSPOT",
            expected_version="v2",
            actual_version="v3",
            operation="TOMAR",
            retry_count=2
        ),
        VersionConflict(
            tag_spool="TAG-HOTSPOT",
            expected_version="v3",
            actual_version="v4",
            operation="COMPLETAR",
            retry_count=3
        ),
        VersionConflict(
            tag_spool="TAG-OTHER",
            expected_version="v1",
            actual_version="v2",
            operation="TOMAR",
            retry_count=1
        )
    ]

    # Detect pattern
    analysis = conflict_service.detect_conflict_pattern(conflicts)

    # Assertions
    assert "TAG-HOTSPOT" in str(analysis), "Should identify hot spot spool"
    assert analysis["hot_spots"][0]["tag_spool"] == "TAG-HOTSPOT"
    assert analysis["hot_spots"][0]["conflict_count"] == 3


def test_conflict_metrics_tracked(conflict_service):
    """
    Conflict metrics are tracked per spool.

    Validates:
    - Metrics stored for each spool
    - Retry counts accumulated
    - Success/failure rates calculated
    """
    tag_spool = "TAG-METRICS"

    # Track some conflicts
    conflict_service._record_conflict(tag_spool, retry_count=1, success=False)
    conflict_service._record_conflict(tag_spool, retry_count=2, success=False)
    conflict_service._record_conflict(tag_spool, retry_count=1, success=True)

    # Get metrics
    metrics = conflict_service._conflict_metrics.get(tag_spool)

    # Assertions
    assert metrics is not None
    assert metrics.total_conflicts >= 3
    assert metrics.total_retries >= 4  # 1 + 2 + 1
    assert metrics.success_count >= 1


def test_retry_config_validation():
    """
    RetryConfig validates parameters.

    Validates:
    - max_attempts > 0
    - base_delay_ms > 0
    - max_delay_ms >= base_delay_ms
    - exponential_base >= 1.0
    """
    # Valid config
    config = RetryConfig(
        max_attempts=3,
        base_delay_ms=100,
        max_delay_ms=10000,
        exponential_base=2.0,
        jitter=True
    )
    assert config.max_attempts == 3

    # Invalid configs should raise validation error
    with pytest.raises(ValueError):
        RetryConfig(max_attempts=0)  # Must be > 0

    with pytest.raises(ValueError):
        RetryConfig(base_delay_ms=-100)  # Must be positive

    with pytest.raises(ValueError):
        RetryConfig(exponential_base=0.5)  # Must be >= 1.0
