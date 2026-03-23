"""
Unit tests for ConflictService - transient error retry logic.

Tests validate:
- Retry with exponential backoff on transient Sheets errors
- Maximum retry attempts respected
- Jitter applied to prevent thundering herd
- Successful update on first attempt

Reference:
- Service: backend/services/conflict_service.py
"""
import pytest
from unittest.mock import MagicMock
import uuid

from backend.services.conflict_service import ConflictService
from backend.models.conflict import RetryConfig
from backend.exceptions import SheetsUpdateError


@pytest.fixture
def mock_sheets_repository():
    """Mock SheetsRepository."""
    repo = MagicMock()
    repo.update_spool_with_version = MagicMock(return_value="0")
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


def test_generate_version_token_returns_stub(conflict_service):
    """
    Version token generation returns stub value.

    Version column removed from Operaciones sheet.
    """
    token = conflict_service.generate_version_token()
    assert token == "0"


def test_calculate_retry_delay_exponential_backoff(conflict_service):
    """
    Retry delay uses exponential backoff.

    Validates:
    - Delay increases exponentially with attempt number
    - Base delay and exponential base from config
    - Max delay capped at configured maximum
    """
    # First attempt (0) should be base delay (jitter +/-25% so ~75ms-125ms)
    delay0 = conflict_service.calculate_retry_delay(0)
    assert 0.07 <= delay0 <= 0.15

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
    """
    delay = conflict_service.calculate_retry_delay(100)
    assert delay <= 10.0


def test_calculate_retry_delay_with_custom_config(conflict_service):
    """
    Custom retry config overrides default.
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

    assert delay0 == 0.05  # 50ms * 3^0 = 50ms = 0.05s
    assert delay1 == 0.15  # 50ms * 3^1 = 150ms = 0.15s


@pytest.mark.asyncio
async def test_update_with_retry_success_first_attempt(
    conflict_service,
    mock_sheets_repository
):
    """
    Update succeeds on first attempt without retry.
    """
    tag_spool = "TAG-001"
    updates = {"ocupado_por": "Worker93"}

    mock_sheets_repository.update_spool_with_version.return_value = "0"

    result = await conflict_service.update_with_retry(tag_spool, updates, operation="TOMAR")

    assert result == "0"
    mock_sheets_repository.update_spool_with_version.assert_called_once()


@pytest.mark.asyncio
async def test_update_with_retry_transient_error_then_success(
    conflict_service,
    mock_sheets_repository
):
    """
    Transient Sheets error on first attempt, success on retry.
    """
    tag_spool = "TAG-002"
    updates = {"ocupado_por": "Worker93"}

    mock_sheets_repository.update_spool_with_version.side_effect = [
        SheetsUpdateError("Transient error", updates=updates),
        "0"  # Success on retry
    ]

    result = await conflict_service.update_with_retry(tag_spool, updates, operation="TOMAR", max_attempts=3)

    assert result == "0"
    assert mock_sheets_repository.update_spool_with_version.call_count == 2


@pytest.mark.asyncio
async def test_update_with_retry_max_attempts_exceeded(
    conflict_service,
    mock_sheets_repository
):
    """
    Retry exhausts max attempts and raises error.
    """
    tag_spool = "TAG-003"
    updates = {"ocupado_por": "Worker93"}

    mock_sheets_repository.update_spool_with_version.side_effect = [
        SheetsUpdateError("Error 1", updates=updates),
        SheetsUpdateError("Error 2", updates=updates),
        SheetsUpdateError("Error 3", updates=updates),
    ]

    with pytest.raises(SheetsUpdateError):
        await conflict_service.update_with_retry(tag_spool, updates, operation="TOMAR", max_attempts=3)

    assert mock_sheets_repository.update_spool_with_version.call_count == 3


def test_retry_config_validation():
    """
    RetryConfig validates parameters.
    """
    config = RetryConfig(
        max_attempts=3,
        base_delay_ms=100,
        max_delay_ms=10000,
        exponential_base=2.0,
        jitter=True
    )
    assert config.max_attempts == 3

    with pytest.raises(ValueError):
        RetryConfig(max_attempts=0)

    with pytest.raises(ValueError):
        RetryConfig(base_delay_ms=-100)

    with pytest.raises(ValueError):
        RetryConfig(exponential_base=0.5)
