"""
ConflictService - Version conflict detection and retry logic (v3.0).

Implements optimistic locking with automatic retry and exponential backoff
for handling concurrent sheet updates safely.

Key responsibilities:
- Generate version tokens (UUID4)
- Calculate retry delays with exponential backoff and jitter
- Execute updates with automatic retry on version conflicts
- Detect conflict patterns (hot spots)
- Track conflict metrics for monitoring
"""

import uuid
import logging
import asyncio
import time
from typing import Callable, Any, Optional, Dict, List
from datetime import datetime

from backend.models.conflict import (
    VersionConflict,
    RetryConfig,
    ConflictMetrics,
    ConflictResolution
)
from backend.exceptions import VersionConflictError
from backend.repositories.sheets_repository import SheetsRepository

logger = logging.getLogger(__name__)


class ConflictService:
    """
    Service for handling version conflicts with automatic retry.

    Implements exponential backoff retry pattern with jitter to handle
    concurrent updates gracefully.
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
        self._conflict_metrics: Dict[str, ConflictMetrics] = {}
        logger.info("ConflictService initialized with automatic retry support")

    def generate_version_token(self) -> str:
        """
        Generate a new version token using UUID4.

        Returns:
            str: UUID4 string (e.g., "550e8400-e29b-41d4-a716-446655440000")

        Example:
            >>> service.generate_version_token()
            "7c9e6679-7425-40de-944b-e07fc1f90ae7"
        """
        return str(uuid.uuid4())

    def calculate_retry_delay(
        self,
        attempt: int,
        config: Optional[RetryConfig] = None
    ) -> float:
        """
        Calculate delay in seconds for given retry attempt.

        Uses exponential backoff with jitter to prevent thundering herd.

        Args:
            attempt: Attempt number (0-indexed)
            config: Retry configuration (uses default if None)

        Returns:
            float: Delay in seconds

        Example:
            >>> service.calculate_retry_delay(0)  # First retry
            0.1  # 100ms base delay
            >>> service.calculate_retry_delay(1)  # Second retry
            0.2  # 200ms (exponential growth)
            >>> service.calculate_retry_delay(2)  # Third retry
            0.4  # 400ms
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
        Update spool with automatic retry on version conflicts.

        Flow:
        1. Read current version
        2. Attempt update with version check
        3. On VersionConflictError: wait with exponential backoff, retry
        4. On success: return new version
        5. After max_attempts: raise final error

        Args:
            tag_spool: Spool identifier
            updates: Dictionary of {column_name: value} updates
            operation: Operation type (TOMAR/PAUSAR/COMPLETAR)
            max_attempts: Override default max attempts

        Returns:
            str: New version token after successful update

        Raises:
            VersionConflictError: If max retries exceeded
            SpoolNoEncontradoError: If spool not found
            SheetsUpdateError: If update fails for non-conflict reason

        Example:
            >>> new_version = await service.update_with_retry(
            ...     tag_spool="TAG-123",
            ...     updates={"Ocupado_Por": "MR(93)"},
            ...     operation="TOMAR"
            ... )
        """
        config = RetryConfig(max_attempts=max_attempts or self.default_config.max_attempts)
        attempt = 0
        last_conflict: Optional[VersionConflict] = None

        start_time = time.time()

        while attempt < config.max_attempts:
            try:
                # Step 1: Read current version
                current_version = self.sheets_repository.get_spool_version(tag_spool)

                logger.info(
                    f"Attempt {attempt + 1}/{config.max_attempts}: "
                    f"Updating {tag_spool} with version {current_version}"
                )

                # Step 2: Attempt update with version check
                new_version = self.sheets_repository.update_spool_with_version(
                    tag_spool=tag_spool,
                    updates=updates,
                    expected_version=current_version
                )

                # Step 3: Success - record metrics and return
                elapsed = time.time() - start_time
                logger.info(
                    f"✅ Update succeeded for {tag_spool} after {attempt + 1} attempts "
                    f"({elapsed:.2f}s total)"
                )

                # Record successful conflict resolution if retried
                if attempt > 0:
                    self._record_conflict(tag_spool, attempt, succeeded=True)

                return new_version

            except VersionConflictError as e:
                attempt += 1
                last_conflict = VersionConflict(
                    tag_spool=tag_spool,
                    expected_version=e.data.get("expected_version", "unknown"),
                    actual_version=e.data.get("actual_version", "unknown"),
                    operation=operation,
                    retry_count=attempt,
                    max_retries=config.max_attempts
                )

                if attempt >= config.max_attempts:
                    # Max retries exhausted
                    elapsed = time.time() - start_time
                    logger.error(
                        f"❌ Max retries ({config.max_attempts}) exhausted for {tag_spool} "
                        f"after {elapsed:.2f}s"
                    )
                    self._record_conflict(tag_spool, attempt, succeeded=False)
                    raise

                # Calculate delay and retry
                delay = self.calculate_retry_delay(attempt - 1, config)
                logger.warning(
                    f"⚠️ Version conflict on {tag_spool} (attempt {attempt}/{config.max_attempts}). "
                    f"Retrying in {delay:.2f}s..."
                )

                await asyncio.sleep(delay)

        # Should not reach here, but handle as error
        if last_conflict:
            raise VersionConflictError(
                expected=last_conflict.expected_version,
                actual=last_conflict.actual_version,
                message=f"Max retries exhausted for {tag_spool} operation {operation}"
            )

        raise RuntimeError(f"Unexpected error in retry logic for {tag_spool}")

    def detect_conflict_pattern(
        self,
        conflicts: List[VersionConflict]
    ) -> Dict[str, Any]:
        """
        Analyze conflict patterns to detect hot spots and provide recommendations.

        Args:
            conflicts: List of version conflicts to analyze

        Returns:
            dict: Analysis results with hot_spots, recommendations, metrics

        Example:
            >>> conflicts = [
            ...     VersionConflict(tag_spool="TAG-123", ...),
            ...     VersionConflict(tag_spool="TAG-123", ...),
            ...     VersionConflict(tag_spool="TAG-456", ...)
            ... ]
            >>> analysis = service.detect_conflict_pattern(conflicts)
            >>> analysis["hot_spots"]
            ["TAG-123"]  # TAG-123 has 2 conflicts (hot spot)
        """
        if not conflicts:
            return {
                "hot_spots": [],
                "recommendations": [],
                "total_conflicts": 0,
                "unique_spools": 0
            }

        # Count conflicts per spool
        spool_conflict_counts: Dict[str, int] = {}
        for conflict in conflicts:
            spool_conflict_counts[conflict.tag_spool] = \
                spool_conflict_counts.get(conflict.tag_spool, 0) + 1

        # Identify hot spots (spools with >1 conflict)
        hot_spots = [
            tag_spool for tag_spool, count in spool_conflict_counts.items()
            if count > 1
        ]

        # Generate recommendations
        recommendations = []
        if hot_spots:
            recommendations.append(
                f"Hot spots detected: {len(hot_spots)} spools with frequent conflicts. "
                "Consider adding operation-level locks or UI guidance to reduce contention."
            )

        total_conflicts = len(conflicts)
        unique_spools = len(spool_conflict_counts)

        if total_conflicts > 10 and (total_conflicts / unique_spools) > 2:
            recommendations.append(
                "High overall conflict rate detected. "
                "Review UX to discourage simultaneous operations on same spools."
            )

        return {
            "hot_spots": hot_spots,
            "recommendations": recommendations,
            "total_conflicts": total_conflicts,
            "unique_spools": unique_spools,
            "conflict_counts": spool_conflict_counts
        }

    def _record_conflict(
        self,
        tag_spool: str,
        retry_count: int,
        succeeded: bool
    ) -> None:
        """
        Record a conflict resolution attempt for metrics tracking.

        Args:
            tag_spool: Spool identifier
            retry_count: Number of retries performed
            succeeded: Whether retry succeeded
        """
        if tag_spool not in self._conflict_metrics:
            self._conflict_metrics[tag_spool] = ConflictMetrics(tag_spool=tag_spool)

        metrics = self._conflict_metrics[tag_spool]
        metrics.record_conflict(retry_count, succeeded)

        # Log if this is a hot spot
        if metrics.is_hot_spot:
            logger.warning(
                f"🔥 Hot spot detected: {tag_spool} has {metrics.total_conflicts} conflicts "
                f"(success rate: {metrics.success_rate:.1%})"
            )

    def get_metrics(self, tag_spool: Optional[str] = None) -> Dict[str, ConflictMetrics]:
        """
        Get conflict metrics for monitoring.

        Args:
            tag_spool: Get metrics for specific spool (all if None)

        Returns:
            dict: Conflict metrics by spool
        """
        if tag_spool:
            return {tag_spool: self._conflict_metrics.get(tag_spool)}

        return self._conflict_metrics.copy()

    def reset_metrics(self) -> None:
        """Reset all conflict metrics (useful for testing)."""
        self._conflict_metrics.clear()
        logger.info("Conflict metrics reset")
