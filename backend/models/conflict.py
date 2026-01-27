"""
Conflict models for optimistic locking and version control (v3.0).

Supports concurrent sheet updates with version token validation,
exponential backoff retry, and conflict resolution strategies.
"""

from pydantic import BaseModel, Field, field_validator
from enum import Enum
from typing import Optional


class ConflictResolution(str, Enum):
    """
    Strategy for resolving version conflicts.

    - RETRY: Attempt operation again with updated version
    - ABORT: Give up and return error to user
    - MERGE: Attempt to merge changes (future enhancement)
    """
    RETRY = "RETRY"
    ABORT = "ABORT"
    MERGE = "MERGE"


class VersionConflict(BaseModel):
    """
    Represents a version conflict during concurrent update.

    Tracks conflict metadata for logging and retry decisions.
    """
    tag_spool: str = Field(..., description="Spool identifier")
    expected_version: str = Field(..., description="Version token expected by this operation")
    actual_version: str = Field(..., description="Current version token in sheet")
    operation: str = Field(..., description="Operation type (TOMAR/PAUSAR/COMPLETAR)")
    retry_count: int = Field(default=0, description="Number of retries attempted so far")
    max_retries: int = Field(default=3, description="Maximum retry attempts before giving up")

    @field_validator('retry_count')
    @classmethod
    def validate_retry_count(cls, v: int) -> int:
        """Ensure retry_count is non-negative."""
        if v < 0:
            raise ValueError("retry_count must be non-negative")
        return v

    @field_validator('max_retries')
    @classmethod
    def validate_max_retries(cls, v: int) -> int:
        """Ensure max_retries is positive and reasonable."""
        if v < 1:
            raise ValueError("max_retries must be at least 1")
        if v > 10:
            raise ValueError("max_retries should not exceed 10 to prevent excessive load")
        return v

    def can_retry(self) -> bool:
        """Check if another retry attempt is allowed."""
        return self.retry_count < self.max_retries

    def increment_retry(self) -> None:
        """Increment retry counter."""
        self.retry_count += 1


class RetryConfig(BaseModel):
    """
    Configuration for exponential backoff retry strategy.

    Implements jittered exponential backoff to reduce thundering herd:
    delay = min(base_delay * (exponential_base ^ attempt) + jitter, max_delay)
    """
    max_attempts: int = Field(
        default=3,
        ge=1,
        le=10,
        description="Maximum retry attempts (1-10)"
    )
    base_delay_ms: int = Field(
        default=100,
        ge=10,
        le=5000,
        description="Base delay in milliseconds (10-5000)"
    )
    max_delay_ms: int = Field(
        default=10000,
        ge=100,
        le=60000,
        description="Maximum delay cap in milliseconds (100-60000)"
    )
    exponential_base: float = Field(
        default=2.0,
        ge=1.5,
        le=4.0,
        description="Exponential backoff multiplier (1.5-4.0)"
    )
    jitter: bool = Field(
        default=True,
        description="Add random jitter to prevent thundering herd"
    )

    @field_validator('max_delay_ms')
    @classmethod
    def validate_max_delay(cls, v: int, info) -> int:
        """Ensure max_delay_ms is greater than base_delay_ms."""
        # Note: info.data contains previously validated fields
        base_delay = info.data.get('base_delay_ms', 100)
        if v < base_delay:
            raise ValueError(f"max_delay_ms ({v}) must be >= base_delay_ms ({base_delay})")
        return v

    def calculate_delay(self, attempt: int) -> float:
        """
        Calculate delay in seconds for given attempt number.

        Args:
            attempt: Attempt number (0-indexed)

        Returns:
            Delay in seconds (includes jitter if enabled)

        Example:
            >>> config = RetryConfig()
            >>> config.calculate_delay(0)  # First retry
            0.1  # 100ms base delay
            >>> config.calculate_delay(1)  # Second retry
            0.2  # 200ms (100 * 2^1)
            >>> config.calculate_delay(2)  # Third retry
            0.4  # 400ms (100 * 2^2)
        """
        import random

        # Calculate exponential backoff
        delay_ms = self.base_delay_ms * (self.exponential_base ** attempt)

        # Cap at max_delay_ms
        delay_ms = min(delay_ms, self.max_delay_ms)

        # Add jitter if enabled (±25% random variation)
        if self.jitter:
            jitter_factor = random.uniform(0.75, 1.25)
            delay_ms *= jitter_factor

        # Convert to seconds
        return delay_ms / 1000.0


class ConflictMetrics(BaseModel):
    """
    Metrics for tracking conflict patterns and resolution success.

    Used for monitoring hot spots and system health.
    """
    tag_spool: str = Field(..., description="Spool with conflicts")
    total_conflicts: int = Field(default=0, description="Total conflicts detected")
    retries_succeeded: int = Field(default=0, description="Retries that succeeded")
    retries_failed: int = Field(default=0, description="Retries that exhausted max attempts")
    avg_retry_count: float = Field(default=0.0, description="Average retries per conflict")

    @property
    def success_rate(self) -> float:
        """Calculate retry success rate (0.0-1.0)."""
        total = self.retries_succeeded + self.retries_failed
        if total == 0:
            return 0.0
        return self.retries_succeeded / total

    @property
    def is_hot_spot(self) -> bool:
        """
        Determine if spool is a hot spot (high conflict rate).

        Threshold: >5 conflicts indicates frequent contention.
        """
        return self.total_conflicts > 5

    def record_conflict(self, retry_count: int, succeeded: bool) -> None:
        """Record a conflict resolution attempt."""
        self.total_conflicts += 1
        if succeeded:
            self.retries_succeeded += 1
        else:
            self.retries_failed += 1

        # Update running average
        total_attempts = self.retries_succeeded + self.retries_failed
        self.avg_retry_count = (
            (self.avg_retry_count * (total_attempts - 1) + retry_count) / total_attempts
        )
