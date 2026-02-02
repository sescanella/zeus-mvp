"""
Shared fixtures and utilities for performance testing.

Provides:
- Percentile calculation with numpy
- Mock latency calibration
- Performance reporting utilities
- Time-based measurement helpers
"""
import time
import numpy as np
from typing import Optional


def calculate_performance_percentiles(latencies: list[float]) -> dict:
    """
    Calculate comprehensive latency statistics using numpy.

    Args:
        latencies: List of latency measurements in seconds

    Returns:
        dict with keys:
            - n (int): Sample size
            - avg (float): Average latency
            - min (float): Minimum latency
            - max (float): Maximum latency
            - p50 (float): 50th percentile (median)
            - p95 (float): 95th percentile
            - p99 (float): 99th percentile

    Edge cases:
        - Empty array returns all zeros
        - NaN values are filtered out before calculation
        - Single value returns that value for all percentiles

    Example:
        >>> latencies = [0.3, 0.4, 0.5, 0.6, 0.7]
        >>> stats = calculate_performance_percentiles(latencies)
        >>> print(f"p95: {stats['p95']:.3f}s")
        p95: 0.680s
    """
    # Handle empty array
    if not latencies:
        return {
            "n": 0,
            "avg": 0.0,
            "min": 0.0,
            "max": 0.0,
            "p50": 0.0,
            "p95": 0.0,
            "p99": 0.0
        }

    # Convert to numpy array and filter NaN values
    arr = np.array(latencies)
    arr = arr[~np.isnan(arr)]

    # Handle all NaN case
    if len(arr) == 0:
        return {
            "n": 0,
            "avg": 0.0,
            "min": 0.0,
            "max": 0.0,
            "p50": 0.0,
            "p95": 0.0,
            "p99": 0.0
        }

    return {
        "n": len(arr),
        "avg": float(np.mean(arr)),
        "min": float(np.min(arr)),
        "max": float(np.max(arr)),
        "p50": float(np.percentile(arr, 50)),
        "p95": float(np.percentile(arr, 95)),
        "p99": float(np.percentile(arr, 99))
    }


def print_performance_report(stats: dict, duration: float, test_name: str = "Performance Test"):
    """
    Print comprehensive performance validation report.

    Args:
        stats: Dictionary with percentile statistics from calculate_performance_percentiles
        duration: Test duration in seconds
        test_name: Name of the test for reporting

    Example:
        >>> stats = calculate_performance_percentiles([0.4, 0.5, 0.6])
        >>> print_performance_report(stats, 120.0, "10-union batch test")
    """
    print("\n" + "="*80)
    print(f"{test_name.upper()}")
    print("="*80)
    print(f"\nTest Duration: {duration:.1f}s ({duration/60:.1f}m)")
    print(f"Sample Size: {stats['n']} operations")

    print("\n📊 LATENCY METRICS:")
    print(f"  Average: {stats['avg']:.3f}s")
    print(f"  Median (p50): {stats['p50']:.3f}s")
    print(f"  p95: {stats['p95']:.3f}s | Target: <1.0s | {'✅ PASS' if stats['p95'] < 1.0 else '❌ FAIL'}")
    print(f"  p99: {stats['p99']:.3f}s | Target: <2.0s | {'✅ PASS' if stats['p99'] < 2.0 else '❌ FAIL'}")
    print(f"  Min: {stats['min']:.3f}s")
    print(f"  Max: {stats['max']:.3f}s")

    print("\n" + "="*80 + "\n")


def simulate_sheets_batch_update_latency(base_latency: float = 0.3, variance: Optional[float] = None):
    """
    Simulate Google Sheets batch_update API latency with realistic variance.

    Based on Phase 8 production measurements:
    - p50: 280ms
    - p95: 450ms
    - p99: 800ms

    Args:
        base_latency: Base latency in seconds (default 300ms)
        variance: Standard deviation for lognormal distribution (default: no variance)

    Usage:
        >>> mock_worksheet.batch_update.side_effect = lambda *a, **kw: simulate_sheets_batch_update_latency()
    """
    if variance:
        import random
        # Use log-normal distribution to model real API latency
        latency = random.lognormvariate(np.log(base_latency), variance)
        # Clamp to observed bounds (50ms min, 2s max)
        latency = max(0.05, min(2.0, latency))
    else:
        latency = base_latency

    time.sleep(latency)


def simulate_sheets_append_rows_latency(base_latency: float = 0.15, variance: Optional[float] = None):
    """
    Simulate Google Sheets append_rows API latency.

    Typically faster than batch_update (150ms base).

    Args:
        base_latency: Base latency in seconds (default 150ms)
        variance: Standard deviation for lognormal distribution (default: no variance)

    Usage:
        >>> mock_worksheet.append_rows.side_effect = lambda *a, **kw: simulate_sheets_append_rows_latency()
    """
    if variance:
        import random
        latency = random.lognormvariate(np.log(base_latency), variance)
        latency = max(0.05, min(1.0, latency))
    else:
        latency = base_latency

    time.sleep(latency)
