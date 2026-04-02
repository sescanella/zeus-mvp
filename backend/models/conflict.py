"""
Conflict models for retry configuration (v3.0+).

Provides exponential backoff retry strategy for transient Google Sheets errors.
"""

from pydantic import BaseModel, Field, field_validator


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

        # Cap at max_delay_ms before jitter
        delay_ms = min(delay_ms, self.max_delay_ms)

        # Add jitter if enabled (±25% random variation)
        if self.jitter:
            jitter_factor = random.uniform(0.75, 1.25)
            delay_ms *= jitter_factor
            # Cap again after jitter so result never exceeds max_delay_ms
            delay_ms = min(delay_ms, self.max_delay_ms)

        # Convert to seconds
        return delay_ms / 1000.0


