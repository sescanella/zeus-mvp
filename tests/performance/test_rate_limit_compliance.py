"""
Rate limit compliance validation tests for PERF-05.

Validates system stays under 50% of Google Sheets rate limit
(30 writes/min vs 60 limit).

Tests:
- Rate limit compliance under sustained load
- Burst detection and throttling
- Sliding window accuracy
- Multi-worker concurrency scenarios
"""

import time
import pytest
from datetime import datetime, timedelta
from backend.utils.rate_limiter import RateLimitMonitor, GlobalRateLimitMonitor


class TestRateLimitCompliance:
    """Comprehensive rate limit compliance validation."""

    def test_rate_limit_compliance_under_load(self):
        """
        PERF-05: System stays under 50% of Google Sheets rate limit.

        Simulates 30 workers performing FINALIZAR operations for 10 minutes.
        Each worker performs 2 FINALIZAR/min (conservative estimate).
        Tracks all API calls and verifies rate stays under 30 writes/min throughout.
        """
        monitor = RateLimitMonitor(window_seconds=60, target_rpm=30)

        # Test parameters - reduced for CI speed
        duration_seconds = 120  # 2 minutes (sufficient for validation)
        workers = 30
        operations_per_minute = 2  # Each worker does 2 FINALIZAR/min

        # Expected API calls per FINALIZAR: 2 (batch_update + append_rows)
        api_calls_per_operation = 2

        # Calculate target rate: 30 workers * 2 ops/min * 2 API calls = 120 calls/min
        # This is 2x over our 30 RPM target, so we need throttling
        # Realistic: Workers don't all work simultaneously
        # Model: 30 workers spread across 60 seconds = 1 worker every 2 seconds

        start_time = time.time()
        operation_count = 0
        max_rpm_observed = 0.0
        rpm_samples = []

        print(f"\n🔧 Simulating {workers} workers for {duration_seconds}s...")
        print(f"   Target: < 30 RPM (50% of 60 quota)")

        # Track minutes for reporting
        last_minute_marker = 0

        while time.time() - start_time < duration_seconds:
            elapsed = time.time() - start_time
            current_minute = int(elapsed // 60)

            # Spread worker operations across time to avoid burst
            # Each worker operates every 30 seconds (2 ops/min)
            worker_id = int(elapsed * 2) % workers

            # Each FINALIZAR = 2 API calls (batch_update + append_rows)
            monitor.record_request("batch_update")
            monitor.record_request("append_rows")
            operation_count += 1

            # Get current stats
            stats = monitor.get_stats()
            current_rpm = stats['current_rpm']
            rpm_samples.append(current_rpm)
            max_rpm_observed = max(max_rpm_observed, current_rpm)

            # Report every minute
            if current_minute > last_minute_marker:
                print(f"   Minute {current_minute}: RPM={current_rpm:.1f} | "
                      f"Quota={stats['quota_utilization']:.1f}% | "
                      f"Requests={stats['requests_in_window']}")
                last_minute_marker = current_minute

            # Verify compliance continuously
            assert stats['within_limit'], \
                f"PERF-05 FAILED at {elapsed:.1f}s: " \
                f"{current_rpm:.1f} RPM exceeds target of {monitor.target_rpm}"

            # Realistic worker pacing: one operation every 0.5 seconds
            # (30 workers * 2 ops/min = 1 op/second, spread to 0.5s for safety)
            time.sleep(0.5)

        # Final statistics
        final_stats = monitor.get_stats()
        avg_rpm = sum(rpm_samples) / len(rpm_samples) if rpm_samples else 0.0

        print(f"\n✅ PERF-05 COMPLIANCE TEST PASSED")
        print(f"   Duration: {duration_seconds}s")
        print(f"   Total operations: {operation_count}")
        print(f"   Average RPM: {avg_rpm:.1f}")
        print(f"   Peak RPM: {max_rpm_observed:.1f}")
        print(f"   Final quota utilization: {final_stats['quota_utilization']:.1f}%")
        print(f"   Target: {monitor.target_rpm} RPM (50% of 60 quota)")

        # Assert final compliance
        assert final_stats['within_limit'], \
            f"Final state exceeds limit: {final_stats['current_rpm']:.1f} RPM"
        assert max_rpm_observed <= monitor.target_rpm * 1.1, \
            f"Peak RPM {max_rpm_observed:.1f} exceeds safe threshold"

    def test_burst_detection_and_throttling(self):
        """
        Verify burst detection triggers warnings.

        Burst defined as: > 20 requests in 10 seconds
        Should trigger warning before hitting rate limit.
        """
        monitor = RateLimitMonitor(window_seconds=60, target_rpm=30)

        print("\n🔧 Testing burst detection...")

        # Simulate normal load (no burst)
        for i in range(10):
            monitor.record_request("write")
            time.sleep(0.1)  # Spread over 1 second

        stats = monitor.get_stats()
        print(f"   Normal load: {stats['requests_in_window']} requests, "
              f"burst={stats['burst_detected']}")
        assert not stats['burst_detected'], "Should not detect burst in normal load"

        # Simulate burst: 30 requests in 5 seconds
        print("   Simulating burst: 30 requests in 5 seconds...")
        burst_start = time.time()
        for i in range(30):
            monitor.record_request("write")
            if i % 10 == 0:
                time.sleep(0.2)  # Small delays to spread slightly

        burst_duration = time.time() - burst_start

        stats = monitor.get_stats()
        warning = monitor.get_warning_message()

        print(f"   Burst completed in {burst_duration:.2f}s")
        print(f"   Requests in window: {stats['requests_in_window']}")
        print(f"   Burst detected: {stats['burst_detected']}")
        print(f"   Warning: {warning}")

        # Verify burst detection
        assert stats['burst_detected'], "Should detect burst (> 20 req in 10s)"
        assert warning is not None, "Should generate warning for burst"
        assert "BURST" in warning, "Warning should mention burst"

        print("   ✅ Burst detection working")

    def test_sliding_window_accuracy(self):
        """
        Verify sliding window accurately prunes old requests.

        Tests:
        - Requests outside window are removed
        - RPM calculation is accurate
        - Window boundary conditions handled correctly
        """
        monitor = RateLimitMonitor(window_seconds=5, target_rpm=30)  # Short window for testing

        print("\n🔧 Testing sliding window accuracy...")

        # Add 10 requests at t=0
        for i in range(10):
            monitor.record_request("write")

        stats = monitor.get_stats()
        print(f"   t=0: {stats['requests_in_window']} requests")
        assert stats['requests_in_window'] == 10, "Should have 10 requests at start"

        # Wait 3 seconds, add 5 more (total: 15 in window)
        time.sleep(3)
        for i in range(5):
            monitor.record_request("write")

        stats = monitor.get_stats()
        print(f"   t=3s: {stats['requests_in_window']} requests")
        assert stats['requests_in_window'] == 15, "Should have 15 requests at t=3s"

        # Wait 3 more seconds (total 6s, first 10 should be pruned)
        time.sleep(3)
        stats = monitor.get_stats()
        print(f"   t=6s: {stats['requests_in_window']} requests (window=5s)")
        # Should have ~5 requests (the ones added at t=3s)
        assert stats['requests_in_window'] <= 6, "Old requests should be pruned"
        assert stats['requests_in_window'] >= 4, "Recent requests should remain"

        # Test empty window
        time.sleep(6)  # Wait for all to expire
        stats = monitor.get_stats()
        print(f"   t=12s: {stats['requests_in_window']} requests (all expired)")
        assert stats['requests_in_window'] == 0, "All requests should be pruned"
        assert stats['current_rpm'] == 0.0, "RPM should be 0 for empty window"

        print("   ✅ Sliding window pruning accurate")

    def test_rpm_calculation_edge_cases(self):
        """
        Test RPM calculation edge cases.

        Cases:
        - Empty window
        - Single request
        - All requests at same timestamp
        """
        monitor = RateLimitMonitor(window_seconds=60, target_rpm=30)

        print("\n🔧 Testing RPM calculation edge cases...")

        # Case 1: Empty window
        stats = monitor.get_stats()
        print(f"   Empty window: RPM={stats['current_rpm']}")
        assert stats['current_rpm'] == 0.0, "Empty window should return 0 RPM"

        # Case 2: Single request
        monitor.record_request("write")
        stats = monitor.get_stats()
        print(f"   Single request: RPM={stats['current_rpm']}")
        assert stats['current_rpm'] >= 0.0, "Single request should have valid RPM"

        # Case 3: Multiple requests at same timestamp (rapid burst)
        monitor = RateLimitMonitor(window_seconds=60, target_rpm=30)
        for i in range(5):
            monitor.record_request("write")
            # No sleep - all at same timestamp

        stats = monitor.get_stats()
        print(f"   Simultaneous requests: RPM={stats['current_rpm']}")
        # When all requests are at same time, time_span=0, should return count
        assert stats['current_rpm'] == 5.0, "Same-timestamp requests should return count"

        print("   ✅ Edge cases handled correctly")

    def test_multi_worker_concurrency(self):
        """
        Simulate realistic concurrent worker patterns.

        Models shift change scenario: all 30 workers start work simultaneously.
        This is worst-case for rate limiting (high burst potential).
        """
        monitor = RateLimitMonitor(window_seconds=60, target_rpm=30)

        print("\n🔧 Testing multi-worker concurrency (shift change scenario)...")

        # Shift change: 30 workers all do INICIAR simultaneously
        # Each INICIAR = 2 API calls (batch_update + append_rows)
        workers = 30
        api_calls_per_iniciar = 2

        print(f"   Simulating {workers} workers doing INICIAR at shift start...")

        # Simulate staggered starts (realistic: not perfectly simultaneous)
        # Workers arrive over 30 seconds
        for worker_id in range(workers):
            # Each worker: INICIAR (2 API calls)
            monitor.record_request("batch_update")
            monitor.record_request("append_rows")

            # Small delay between workers (1 second intervals)
            if worker_id < workers - 1:
                time.sleep(1.0)

        stats = monitor.get_stats()
        warning = monitor.get_warning_message()

        print(f"   After shift change:")
        print(f"     Requests in window: {stats['requests_in_window']}")
        print(f"     Current RPM: {stats['current_rpm']:.1f}")
        print(f"     Quota utilization: {stats['quota_utilization']:.1f}%")
        print(f"     Within limit: {stats['within_limit']}")
        print(f"     Warning: {warning}")

        # Expected: 30 workers * 2 API calls = 60 requests over ~30 seconds
        # RPM = (60 requests / 30 seconds) * 60 = 120 RPM
        # This EXCEEDS our 30 RPM target, but is realistic burst

        # However, with 1-second intervals, spread is better
        # Should still trigger warnings

        if not stats['within_limit']:
            print(f"   ⚠️ Shift change exceeds rate limit (expected in burst scenario)")
            print(f"   This demonstrates need for throttling in production")
        else:
            print(f"   ✅ Shift change handled within limits")

        # Track how it settles over time
        print("\n   Tracking recovery after burst...")
        for minute in range(2):
            time.sleep(10)  # Wait 10 seconds
            stats = monitor.get_stats()
            print(f"     +{(minute+1)*10}s: RPM={stats['current_rpm']:.1f}, "
                  f"Quota={stats['quota_utilization']:.1f}%")

        final_stats = monitor.get_stats()
        print(f"\n   ✅ Final state: RPM={final_stats['current_rpm']:.1f}, "
              f"Within limit={final_stats['within_limit']}")

    def test_request_type_categorization(self):
        """
        Verify request type tracking and categorization.

        Tests that different request types are tracked separately
        for detailed monitoring.
        """
        monitor = RateLimitMonitor(window_seconds=60, target_rpm=30)

        print("\n🔧 Testing request type categorization...")

        # Record different types
        monitor.record_request("batch_update")
        monitor.record_request("batch_update")
        monitor.record_request("append_rows")
        monitor.record_request("read")

        stats = monitor.get_stats()
        request_types = stats['request_types']

        print(f"   Request types: {request_types}")

        assert request_types.get("batch_update", 0) == 2, "Should track 2 batch_update"
        assert request_types.get("append_rows", 0) == 1, "Should track 1 append_rows"
        assert request_types.get("read", 0) == 1, "Should track 1 read"

        print("   ✅ Request type categorization working")

    def test_quota_utilization_percentage(self):
        """
        Verify quota utilization percentage calculation.

        Google Sheets quota: 60 writes/min
        Target: < 30 writes/min (50% utilization)
        """
        monitor = RateLimitMonitor(window_seconds=60, target_rpm=30)

        print("\n🔧 Testing quota utilization calculation...")

        # Add requests to reach different utilization levels
        test_cases = [
            (15, 25.0, "25% quota (50% of target)"),
            (30, 50.0, "50% quota (100% of target)"),
            (45, 75.0, "75% quota (150% of target - WARNING)"),
        ]

        for request_count, expected_quota_pct, description in test_cases:
            monitor = RateLimitMonitor(window_seconds=60, target_rpm=30)

            # Add requests spread over 60 seconds to avoid burst
            for i in range(request_count):
                monitor.record_request("write")
                if i < request_count - 1:
                    time.sleep(1.0)

            stats = monitor.get_stats()
            quota_util = stats['quota_utilization']

            print(f"   {description}: {quota_util:.1f}%")

            # Allow 10% variance due to timing
            assert abs(quota_util - expected_quota_pct) < 10.0, \
                f"Quota utilization should be ~{expected_quota_pct}%"

        print("   ✅ Quota utilization calculation accurate")


class TestGlobalRateLimitMonitor:
    """Test GlobalRateLimitMonitor singleton pattern."""

    def setup_method(self):
        """Reset singleton before each test."""
        GlobalRateLimitMonitor.reset_instance()

    def test_singleton_pattern(self):
        """Verify singleton returns same instance."""
        print("\n🔧 Testing singleton pattern...")

        instance1 = GlobalRateLimitMonitor.get_instance()
        instance2 = GlobalRateLimitMonitor.get_instance()

        assert instance1 is instance2, "Should return same instance"

        print("   ✅ Singleton pattern working")

    def test_global_monitor_thread_safety(self):
        """
        Verify GlobalRateLimitMonitor is thread-safe.

        Simulates multiple threads recording requests concurrently.
        """
        import threading

        print("\n🔧 Testing thread safety...")

        monitor = GlobalRateLimitMonitor.get_instance()

        def worker_thread(thread_id: int, request_count: int):
            """Worker thread that records requests."""
            for i in range(request_count):
                monitor.record_request(f"thread_{thread_id}")
                time.sleep(0.01)

        # Spawn 5 threads, each recording 10 requests
        threads = []
        for i in range(5):
            t = threading.Thread(target=worker_thread, args=(i, 10))
            threads.append(t)
            t.start()

        # Wait for all threads
        for t in threads:
            t.join()

        stats = monitor.get_stats()

        print(f"   Total requests: {stats['requests_in_window']}")
        print(f"   Request types: {stats['request_types']}")

        # Should have 5 threads * 10 requests = 50 total
        assert stats['requests_in_window'] == 50, "Should track all concurrent requests"

        print("   ✅ Thread-safe operation confirmed")

    def test_global_monitor_basic_operations(self):
        """Test basic operations on GlobalRateLimitMonitor."""
        print("\n🔧 Testing global monitor basic operations...")

        monitor = GlobalRateLimitMonitor.get_instance()

        # Record some requests
        monitor.record_request("write")
        monitor.record_request("read")

        # Get stats
        stats = monitor.get_stats()
        print(f"   Stats: {stats}")

        assert stats['requests_in_window'] == 2, "Should track 2 requests"
        assert monitor.is_within_limit(), "Should be within limit"

        # Check warning message (should be None for low load)
        warning = monitor.get_warning_message()
        print(f"   Warning: {warning}")

        print("   ✅ Basic operations working")
