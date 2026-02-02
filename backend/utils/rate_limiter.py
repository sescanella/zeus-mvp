"""
Rate limit monitoring utilities for Google Sheets API compliance.

Implements sliding window tracking to ensure system stays under 50% of
Google Sheets rate limit (30 writes/min vs 60 limit).

PERF-05: System must stay under 50% quota utilization
"""

from collections import deque
from datetime import datetime, timedelta
from typing import Dict, Tuple, Optional
import threading


class RateLimitMonitor:
    """
    Track API requests in sliding time windows.

    Google Sheets quota: 60 writes/min/user
    Target: < 30 writes/min (50% utilization)

    Uses collections.deque for O(1) append and efficient old-entry removal.
    """

    def __init__(self, window_seconds: int = 60, target_rpm: int = 30):
        """
        Initialize rate limit monitor.

        Args:
            window_seconds: Time window for rate calculation (default 60s)
            target_rpm: Target requests per minute (default 30, 50% of 60 quota)
        """
        self.window = timedelta(seconds=window_seconds)
        self.target_rpm = target_rpm
        self.requests: deque = deque()  # (timestamp, request_type)
        self._lock = threading.Lock()  # Thread-safe operations

    def record_request(self, request_type: str = "write") -> None:
        """
        Log API request with timestamp.

        Automatically prunes old requests outside sliding window.

        Args:
            request_type: Type of request (write, read, batch)
        """
        with self._lock:
            now = datetime.now()
            self.requests.append((now, request_type))

            # Prune old requests outside window
            cutoff = now - self.window
            while self.requests and self.requests[0][0] < cutoff:
                self.requests.popleft()

    def get_current_rpm(self) -> float:
        """
        Calculate requests per minute in current window.

        Returns:
            Requests per minute (RPM) as float
        """
        with self._lock:
            if not self.requests:
                return 0.0

            # Prune old requests first
            now = datetime.now()
            cutoff = now - self.window
            while self.requests and self.requests[0][0] < cutoff:
                self.requests.popleft()

            if not self.requests:
                return 0.0

            # Calculate time span
            time_span = (self.requests[-1][0] - self.requests[0][0]).total_seconds()

            # Handle edge case: all requests at same time
            if time_span == 0:
                return float(len(self.requests))

            # Convert to requests per minute
            return (len(self.requests) / time_span) * 60

    def is_within_limit(self) -> bool:
        """
        Check if current rate is under target (30 RPM).

        Returns:
            True if under target, False if exceeding
        """
        return self.get_current_rpm() <= self.target_rpm

    def get_quota_utilization(self) -> float:
        """
        Get percentage of 60 RPM quota being used.

        Returns:
            Quota utilization as percentage (0-100+)
        """
        current_rpm = self.get_current_rpm()
        return (current_rpm / 60.0) * 100

    def get_stats(self) -> Dict[str, any]:
        """
        Return comprehensive statistics for reporting.

        Returns:
            Dictionary with current_rpm, target_rpm, quota_utilization,
            within_limit, requests_in_window, time_until_reset
        """
        with self._lock:
            current_rpm = self.get_current_rpm()

            # Calculate time until oldest request drops off window
            time_until_reset = 0.0
            if self.requests:
                now = datetime.now()
                oldest = self.requests[0][0]
                window_end = oldest + self.window
                time_until_reset = max(0.0, (window_end - now).total_seconds())

            # Categorize requests by type
            request_types = {}
            for _, req_type in self.requests:
                request_types[req_type] = request_types.get(req_type, 0) + 1

            return {
                "current_rpm": current_rpm,
                "target_rpm": self.target_rpm,
                "quota_utilization": self.get_quota_utilization(),
                "within_limit": self.is_within_limit(),
                "requests_in_window": len(self.requests),
                "time_until_reset": time_until_reset,
                "request_types": request_types,
                "burst_detected": self._detect_burst()
            }

    def _detect_burst(self) -> bool:
        """
        Detect rapid request clusters (burst).

        Burst defined as: > 20 requests in last 10 seconds

        Returns:
            True if burst detected, False otherwise
        """
        if len(self.requests) < 20:
            return False

        now = datetime.now()
        burst_window = timedelta(seconds=10)
        cutoff = now - burst_window

        # Count recent requests
        recent_count = sum(1 for ts, _ in self.requests if ts >= cutoff)

        return recent_count > 20

    def get_warning_message(self) -> Optional[str]:
        """
        Get warning message if approaching or exceeding limits.

        Returns:
            Warning message if applicable, None otherwise
        """
        stats = self.get_stats()

        if stats["burst_detected"]:
            return f"⚠️ BURST DETECTED: > 20 requests in 10s. Current RPM: {stats['current_rpm']:.1f}"

        if stats["current_rpm"] > self.target_rpm:
            return f"❌ QUOTA EXCEEDED: {stats['current_rpm']:.1f} RPM > {self.target_rpm} target"

        if stats["quota_utilization"] > 40:  # 80% of target (40% of quota)
            return f"⚠️ APPROACHING LIMIT: {stats['quota_utilization']:.1f}% quota utilization"

        return None


class GlobalRateLimitMonitor:
    """
    Singleton global rate limit monitor for production use.

    Thread-safe singleton pattern ensures all services use same monitor.
    """

    _instance: Optional['GlobalRateLimitMonitor'] = None
    _lock = threading.Lock()

    def __init__(self):
        """Initialize with default 60s window, 30 RPM target."""
        self.monitor = RateLimitMonitor(window_seconds=60, target_rpm=30)

    @classmethod
    def get_instance(cls) -> 'GlobalRateLimitMonitor':
        """
        Get singleton instance (thread-safe).

        Returns:
            GlobalRateLimitMonitor singleton instance
        """
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance

    def record_request(self, request_type: str = "write") -> None:
        """
        Record API request in global monitor.

        Args:
            request_type: Type of request (write, read, batch)
        """
        self.monitor.record_request(request_type)

    def get_stats(self) -> Dict[str, any]:
        """
        Get current statistics from global monitor.

        Returns:
            Statistics dictionary
        """
        return self.monitor.get_stats()

    def get_warning_message(self) -> Optional[str]:
        """
        Get warning message if applicable.

        Returns:
            Warning message or None
        """
        return self.monitor.get_warning_message()

    def is_within_limit(self) -> bool:
        """
        Check if within rate limit.

        Returns:
            True if within limit, False otherwise
        """
        return self.monitor.is_within_limit()

    @classmethod
    def reset_instance(cls) -> None:
        """Reset singleton instance (for testing only)."""
        with cls._lock:
            cls._instance = None
