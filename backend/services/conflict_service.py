"""
ConflictService - Retry logic for transient Sheets errors.

Originally implemented optimistic locking with version tokens (v3.0).
Version column removed from Operaciones sheet. Now provides:
- Retry with exponential backoff on transient Sheets errors
- Metrics tracking (kept for monitoring)
"""

import logging
import asyncio
import time
from typing import Optional, Dict

from backend.models.conflict import RetryConfig
from backend.exceptions import SheetsUpdateError
from backend.repositories.sheets_repository import SheetsRepository

logger = logging.getLogger(__name__)


class ConflictService:
    """
    Service for retrying spool updates on transient Sheets errors.

    Version-based conflict detection removed (column deleted from sheet).
    Retains exponential backoff retry for network/rate-limit errors.
    """

    def __init__(
        self,
        sheets_repository: SheetsRepository,
        default_config: Optional[RetryConfig] = None
    ):
        """
        Initialize conflict service.

        Args:
            sheets_repository: Repository for reading/writing sheets
            default_config: Default retry configuration (creates new if None)
        """
        self.sheets_repository = sheets_repository
        self.default_config = default_config or RetryConfig()
        logger.info("ConflictService initialized with transient-error retry support")

    def generate_version_token(self) -> str:
        """Stub: kept for backward compatibility. Returns '0'."""
        return "0"

    def calculate_retry_delay(
        self,
        attempt: int,
        config: Optional[RetryConfig] = None
    ) -> float:
        """
        Calculate delay in seconds for given retry attempt.

        Uses exponential backoff with jitter to prevent thundering herd.
        """
        retry_config = config or self.default_config
        return retry_config.calculate_delay(attempt)

    async def update_with_retry(
        self,
        tag_spool: str,
        updates: dict,
        operation: str,
        max_attempts: Optional[int] = None
    ) -> str:
        """
        Update spool with automatic retry on transient Sheets errors.

        Version conflict detection removed. Retries only on SheetsUpdateError
        (network failures, rate limits).

        Args:
            tag_spool: Spool identifier
            updates: Dictionary of {column_name: value} updates
            operation: Operation type (TOMAR/PAUSAR/COMPLETAR)
            max_attempts: Override default max attempts

        Returns:
            str: Always "0" (no version tracking)

        Raises:
            SpoolNoEncontradoError: If spool not found
            SheetsUpdateError: If update fails after all retries
        """
        config = RetryConfig(max_attempts=max_attempts or self.default_config.max_attempts)
        start_time = time.time()

        for attempt in range(config.max_attempts):
            try:
                logger.info(
                    f"Attempt {attempt + 1}/{config.max_attempts}: "
                    f"Updating {tag_spool} for {operation}"
                )

                result = self.sheets_repository.update_spool_with_version(
                    tag_spool=tag_spool,
                    updates=updates
                )

                elapsed = time.time() - start_time
                logger.info(
                    f"Update succeeded for {tag_spool} after {attempt + 1} attempts "
                    f"({elapsed:.2f}s total)"
                )
                return result

            except SheetsUpdateError as e:
                if attempt + 1 >= config.max_attempts:
                    elapsed = time.time() - start_time
                    logger.error(
                        f"Max retries ({config.max_attempts}) exhausted for {tag_spool} "
                        f"after {elapsed:.2f}s"
                    )
                    raise

                delay = self.calculate_retry_delay(attempt, config)
                logger.warning(
                    f"Transient error on {tag_spool} (attempt {attempt + 1}/{config.max_attempts}). "
                    f"Retrying in {delay:.2f}s..."
                )
                await asyncio.sleep(delay)

        # Should not reach here
        raise SheetsUpdateError(
            f"Unexpected error in retry logic for {tag_spool}",
            updates=updates
        )

    def reset_metrics(self) -> None:
        """Reset all conflict metrics (kept for testing compatibility)."""
        logger.info("Conflict metrics reset")
