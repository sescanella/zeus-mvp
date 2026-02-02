"""
Version detection service for identifying v3.0 vs v4.0 spools.

Determines spool version based on Total_Uniones column (68) from Operaciones sheet.
Includes retry logic with exponential backoff for transient failures.
"""
import logging
from typing import Dict
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
    before_sleep_log
)

from backend.exceptions import SheetsConnectionError
from backend.repositories.sheets_repository import SheetsRepository


logger = logging.getLogger(__name__)


class VersionDetectionService:
    """
    Service for detecting spool version (v3.0 vs v4.0) based on union count.

    Version detection logic:
    - v4.0: Total_Uniones > 0 (unions populated by Engineering)
    - v3.0: Total_Uniones = 0 or None (legacy workflow, no union data)

    Includes retry logic with exponential backoff for transient Sheets failures.
    On failure after retries, defaults to v3.0 (safer legacy workflow).
    """

    def __init__(self, sheets_repository: SheetsRepository):
        """
        Initialize version detection service.

        Args:
            sheets_repository: Repository for querying Operaciones sheet
        """
        self.sheets_repo = sheets_repository
        self.logger = logging.getLogger(__name__)

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),  # 2s, 4s, 10s (capped)
        retry=retry_if_exception_type((SheetsConnectionError, TimeoutError)),
        before_sleep=before_sleep_log(logger, logging.WARNING),
        reraise=False  # Don't reraise - we default to v3.0 on failure
    )
    async def detect_version(self, tag_spool: str) -> Dict[str, any]:
        """
        Detect spool version with retry logic.

        Queries Total_Uniones column (68) from Operaciones sheet.
        Applies exponential backoff retry on transient failures.

        Args:
            tag_spool: TAG of the spool to detect version for

        Returns:
            dict with keys:
                - version: "v3.0" or "v4.0"
                - union_count: int (value from Total_Uniones column 68)
                - detection_logic: str (explanation for diagnostics)

        Defaults to v3.0 on detection failure (safer legacy workflow).

        Examples:
            >>> await service.detect_version("TEST-02")
            {
                "version": "v4.0",
                "union_count": 8,
                "detection_logic": "Total_Uniones=8 -> v4.0"
            }

            >>> await service.detect_version("OLD-SPOOL")
            {
                "version": "v3.0",
                "union_count": 0,
                "detection_logic": "Total_Uniones=0 -> v3.0"
            }
        """
        try:
            # Query spool from Operaciones sheet
            self.logger.info(f"Detecting version for spool: {tag_spool}")
            spool = self.sheets_repo.get_spool_by_tag(tag_spool)

            # Get union count from Total_Uniones column (68)
            # May be None (column not populated) or 0 (no unions)
            union_count = getattr(spool, 'total_uniones', None) or 0

            # v4.0 detection: count > 0 (Engineering populated unions)
            # v3.0 detection: count = 0 or None (legacy workflow)
            version = "v4.0" if union_count > 0 else "v3.0"

            detection_logic = f"Total_Uniones={union_count} -> {version}"
            self.logger.info(f"Version detected for {tag_spool}: {detection_logic}")

            return {
                "version": version,
                "union_count": union_count,
                "detection_logic": detection_logic,
                "tag_spool": tag_spool
            }

        except Exception as e:
            # After 3 retries (~16s total), detection failed
            # Default to v3.0 (legacy workflow is safer for unknown spools)
            self.logger.error(
                f"Version detection failed for {tag_spool} after retries: {e}. "
                f"Defaulting to v3.0"
            )
            return {
                "version": "v3.0",
                "union_count": 0,
                "detection_logic": f"Detection failed, defaulting to v3.0: {str(e)}",
                "tag_spool": tag_spool
            }
