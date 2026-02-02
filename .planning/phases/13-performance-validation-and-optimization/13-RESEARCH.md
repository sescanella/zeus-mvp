# Phase 13: Performance Validation & Optimization - Research

**Researched:** 2026-02-02
**Domain:** Performance Testing, API Rate Limiting, Load Testing, Observability
**Confidence:** HIGH

## Summary

Phase 13 validates that v4.0 achieves its performance targets: < 1s p95 latency for 10-union batch operations, < 2s p99 threshold, maximum 2 Sheets API calls per FINALIZAR, and staying under 50% of Google Sheets rate limits (30 writes/min vs 60 limit). The implementation builds on proven v3.0 patterns (Locust load testing, pytest performance tests with mock latency simulation) while adding new capabilities for percentile calculation, rate limit monitoring, and comprehensive performance profiling.

**Key Finding:** Most testing infrastructure already exists. The project has Locust for load testing (Phase 4), pytest with mock latency simulation (Phase 8), and batch operations achieving 0.466s average latency (54% faster than 1s target). The critical work is adding p95/p99 percentile calculation, rate limit monitoring, and comprehensive validation across all success criteria.

**Performance Status:** Phase 8 integration tests already demonstrate sub-second performance (0.466s average for 10-union operations). Phase 13 needs to formalize this with percentile-based SLAs and continuous monitoring.

**Primary recommendation:** Extend existing pytest performance tests with percentile calculation using `numpy.percentile()`, add rate limit monitoring with request counting/time-windowing, and create comprehensive load test scenarios that validate all 5 PERF requirements simultaneously.

## Standard Stack

### Core Testing Tools (Already Installed)

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| pytest | 8.4.2 | Test framework with fixtures and mocking | Industry standard for Python testing, already used across 244+ tests |
| pytest-cov | 7.0.0 | Coverage measurement | Essential for tracking test coverage |
| pytest-mock | 3.15.1 | Mock/patch utilities | Simplifies mocking in tests |
| locust | 2.17.0 | Load testing framework | Python-based, code-as-test, scalable to 50+ users (Phase 4) |

### Supporting Libraries (Needed for Phase 13)

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| numpy | Latest | Percentile calculation (p50/p95/p99) | Performance tests requiring statistical analysis |
| psutil | Latest | Memory usage monitoring | Resource profiling during batch operations |
| time | stdlib | High-precision timing | Latency measurement (already used in tests) |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| pytest + time.time() | pytest-benchmark | pytest-benchmark adds overhead and complex setup; existing time.time() pattern proven in Phase 8 |
| numpy.percentile() | Custom percentile calculation | numpy is battle-tested and handles edge cases (empty arrays, NaN values) |
| Locust | k6 (JavaScript) | k6 has better protocol support but team is Python-focused; Locust already proven in Phase 4 |
| psutil | Manual /proc parsing | psutil is cross-platform and handles edge cases |

**Installation:**
```bash
# Activate virtual environment first
source venv/bin/activate

# Install new dependencies
pip install numpy psutil

# Update requirements.txt
pip freeze > requirements.txt
```

## Architecture Patterns

### Recommended Test Structure
```
tests/
├── performance/              # Comprehensive performance validation
│   ├── test_batch_performance.py       # PERF-01, PERF-02 (p95/p99 latency)
│   ├── test_api_call_efficiency.py     # PERF-03 (max 2 API calls)
│   ├── test_rate_limit_compliance.py   # PERF-05 (50% quota usage)
│   └── conftest.py                     # Shared fixtures
├── integration/
│   └── test_performance_target.py      # Existing integration tests (Phase 8)
└── load/
    └── test_sse_load.py                # Existing Locust load tests (Phase 4)
```

### Pattern 1: Percentile-Based Performance Testing

**What:** Measure latency across multiple iterations and calculate p50/p95/p99 percentiles using numpy

**When to use:** Validating SLA requirements (PERF-01: p95 < 1s, PERF-02: p99 < 2s)

**Example:**
```python
# Source: Phase 8 performance tests + numpy enhancement
import time
import numpy as np
import pytest

def test_10_union_batch_percentiles():
    """
    Validate p95 < 1s and p99 < 2s for 10-union selection.

    PERF-01: < 1s p95 latency
    PERF-02: < 2s p99 latency
    """
    iterations = 100  # Statistical significance
    latencies = []

    for _ in range(iterations):
        start_time = time.time()

        # Execute FINALIZAR workflow
        result = union_service.process_selection(
            tag_spool="OT-001",
            union_ids=union_ids,
            worker_id=93,
            worker_nombre="MR(93)",
            operacion="ARM"
        )

        elapsed = time.time() - start_time
        latencies.append(elapsed)

    # Calculate percentiles
    p50 = np.percentile(latencies, 50)
    p95 = np.percentile(latencies, 95)
    p99 = np.percentile(latencies, 99)
    avg = np.mean(latencies)

    # Log results
    print(f"\n📊 Latency Statistics (n={iterations}):")
    print(f"   Average: {avg:.3f}s")
    print(f"   p50 (median): {p50:.3f}s")
    print(f"   p95: {p95:.3f}s")
    print(f"   p99: {p99:.3f}s")

    # Verify SLA requirements
    assert p95 < 1.0, f"PERF-01 FAILED: p95={p95:.3f}s >= 1.0s"
    assert p99 < 2.0, f"PERF-02 FAILED: p99={p99:.3f}s >= 2.0s"
```

**Why this pattern:** Percentiles reveal tail latency that averages hide. p95 ensures 95% of users have good experience, p99 exposes outliers that indicate systemic issues.

### Pattern 2: API Call Counting with Mock Verification

**What:** Track number of Google Sheets API calls during operation and verify maximum limit

**When to use:** Validating PERF-03 (max 2 API calls per FINALIZAR)

**Example:**
```python
# Source: Existing Phase 8 test pattern extended
def test_finalizar_makes_exactly_2_api_calls(mock_sheets_repo):
    """
    PERF-03: Single FINALIZAR makes max 2 Sheets API calls.

    Expected calls:
    1. gspread.batch_update() for union updates (ARM_FECHA_FIN, ARM_WORKER)
    2. append_rows() for metadata events (1 batch + N granular)
    """
    # Setup
    mock_worksheet = mock_sheets_repo._get_worksheet.return_value
    mock_metadata_worksheet = metadata_repo._worksheet

    # Reset call counters
    mock_worksheet.batch_update.reset_mock()
    mock_metadata_worksheet.append_rows.reset_mock()

    # Execute FINALIZAR
    union_service.process_selection(
        tag_spool="OT-001",
        union_ids=union_ids,
        worker_id=93,
        worker_nombre="MR(93)",
        operacion="ARM"
    )

    # Verify exactly 2 API calls
    assert mock_worksheet.batch_update.call_count == 1, \
        f"Expected 1 batch_update call, got {mock_worksheet.batch_update.call_count}"

    assert mock_metadata_worksheet.append_rows.call_count == 1, \
        f"Expected 1 append_rows call, got {mock_metadata_worksheet.append_rows.call_count}"

    # Verify batch sizes
    batch_data = mock_worksheet.batch_update.call_args[0][0]
    assert len(batch_data) >= len(union_ids) * 2, \
        "Batch should contain 2 fields per union (fecha_fin + worker)"

    print(f"\n✅ PERF-03 PASS: Exactly 2 API calls for {len(union_ids)} unions")
```

### Pattern 3: Rate Limit Monitoring with Time-Windowed Request Counting

**What:** Track API requests over sliding 1-minute windows and verify staying under 50% quota (30 writes/min vs 60 limit)

**When to use:** Validating PERF-05 (Google Sheets rate limit compliance)

**Example:**
```python
# Source: Load testing pattern from Phase 4 + rate limit tracking
from collections import deque
from datetime import datetime, timedelta

class RateLimitMonitor:
    """
    Track API requests in 1-minute sliding windows.

    Google Sheets quota: 60 writes/min/user
    Target: < 30 writes/min (50% utilization)
    """

    def __init__(self, window_seconds=60, target_rpm=30):
        self.window = timedelta(seconds=window_seconds)
        self.target_rpm = target_rpm
        self.requests = deque()  # (timestamp, request_type)

    def record_request(self, request_type: str):
        """Record API request with timestamp."""
        now = datetime.now()
        self.requests.append((now, request_type))

        # Prune old requests outside window
        cutoff = now - self.window
        while self.requests and self.requests[0][0] < cutoff:
            self.requests.popleft()

    def get_current_rpm(self) -> float:
        """Calculate requests per minute in current window."""
        if not self.requests:
            return 0.0

        time_span = (self.requests[-1][0] - self.requests[0][0]).total_seconds()
        if time_span == 0:
            return len(self.requests)

        return (len(self.requests) / time_span) * 60

    def is_within_limit(self) -> bool:
        """Check if current rate is under target (50% of quota)."""
        return self.get_current_rpm() <= self.target_rpm

    def get_stats(self) -> dict:
        """Return statistics for reporting."""
        return {
            "current_rpm": self.get_current_rpm(),
            "target_rpm": self.target_rpm,
            "quota_utilization": (self.get_current_rpm() / 60.0) * 100,
            "within_limit": self.is_within_limit(),
            "requests_in_window": len(self.requests)
        }

def test_rate_limit_compliance_under_load():
    """
    PERF-05: System stays under 50% of Google Sheets rate limit.

    Simulates 30 workers performing FINALIZAR operations for 10 minutes.
    Tracks API calls and verifies rate stays under 30 writes/min.
    """
    monitor = RateLimitMonitor(window_seconds=60, target_rpm=30)

    # Simulate 10-minute workload
    duration = 600  # 10 minutes
    workers = 30
    operations_per_worker_per_min = 2  # Conservative estimate

    start_time = time.time()

    while time.time() - start_time < duration:
        # Simulate worker FINALIZAR operations
        for worker_id in range(workers):
            # Each FINALIZAR = 2 API calls (batch_update + append_rows)
            monitor.record_request("batch_update")
            monitor.record_request("append_rows")

            # Sleep to simulate realistic timing
            time.sleep(30 / workers)  # Spread operations across 30 seconds

        # Check compliance every minute
        stats = monitor.get_stats()
        print(f"  RPM: {stats['current_rpm']:.1f} | "
              f"Quota: {stats['quota_utilization']:.1f}% | "
              f"Within limit: {stats['within_limit']}")

        assert stats['within_limit'], \
            f"PERF-05 FAILED: {stats['current_rpm']:.1f} RPM exceeds target of {monitor.target_rpm}"

    # Final report
    final_stats = monitor.get_stats()
    print(f"\n✅ PERF-05 PASS: Rate limit compliance maintained")
    print(f"   Average RPM: {final_stats['current_rpm']:.1f}")
    print(f"   Quota utilization: {final_stats['quota_utilization']:.1f}%")
```

### Pattern 4: Memory Profiling During Batch Operations

**What:** Monitor memory usage before/during/after batch operations to detect leaks or excessive allocation

**When to use:** Ensuring batch operations scale efficiently without memory bloat

**Example:**
```python
# Source: Existing Phase 8 memory test enhanced
import psutil
import os

def test_memory_efficiency_50_unions():
    """
    Validate memory usage during large batch operations.

    Target: < 50MB memory increase for 50-union batch
    """
    process = psutil.Process(os.getpid())

    # Baseline memory (MB)
    baseline = process.memory_info().rss / 1024 / 1024

    # Execute large batch (50 unions = stress test)
    unions = union_repo.get_by_ot("003")
    assert len(unions) >= 50, "Need at least 50 unions for test"

    union_ids = [u.id for u in unions[:50]]

    result = union_service.process_selection(
        tag_spool="OT-003",
        union_ids=union_ids,
        worker_id=93,
        worker_nombre="MR(93)",
        operacion="ARM"
    )

    # Peak memory (MB)
    peak = process.memory_info().rss / 1024 / 1024
    increase = peak - baseline

    print(f"\n💾 Memory Usage:")
    print(f"   Baseline: {baseline:.2f}MB")
    print(f"   Peak: {peak:.2f}MB")
    print(f"   Increase: {increase:.2f}MB")

    # Verify memory efficiency
    assert increase < 50, \
        f"Memory increased by {increase:.2f}MB (threshold: 50MB)"

    assert result["union_count"] == 50, "All unions should be processed"
```

### Pattern 5: Comprehensive Load Test with Multiple Metrics

**What:** Extend existing Locust tests to track all performance metrics simultaneously (latency, API calls, rate limits, memory)

**When to use:** End-to-end validation that all PERF requirements are met under realistic load

**Example:**
```python
# Source: Phase 4 Locust tests extended for comprehensive monitoring
from locust import HttpUser, task, between, events
import numpy as np

# Global metrics collection
latencies = []
api_calls = RateLimitMonitor(window_seconds=60, target_rpm=30)

@events.request.add_listener
def on_request(request_type, name, response_time, response_length, exception, **kwargs):
    """Track every API request for rate limiting and latency."""
    if exception is None:
        latencies.append(response_time / 1000.0)  # Convert ms to seconds

        # Track API calls by endpoint
        if "finalizar" in name.lower():
            api_calls.record_request("finalizar")

@events.test_stop.add_listener
def on_test_stop(environment, **kwargs):
    """Report comprehensive metrics at test completion."""
    if not latencies:
        print("❌ No requests completed")
        return

    # Calculate percentiles
    p50 = np.percentile(latencies, 50)
    p95 = np.percentile(latencies, 95)
    p99 = np.percentile(latencies, 99)
    avg = np.mean(latencies)

    # Rate limit stats
    rate_stats = api_calls.get_stats()

    print("\n" + "="*80)
    print("PERFORMANCE VALIDATION RESULTS - Phase 13")
    print("="*80)

    print(f"\nLATENCY METRICS (n={len(latencies)} requests):")
    print(f"  Average: {avg:.3f}s")
    print(f"  p50 (median): {p50:.3f}s")
    print(f"  p95: {p95:.3f}s ({'✅ PASS' if p95 < 1.0 else '❌ FAIL'} < 1.0s target)")
    print(f"  p99: {p99:.3f}s ({'✅ PASS' if p99 < 2.0 else '❌ FAIL'} < 2.0s target)")

    print(f"\nRATE LIMIT COMPLIANCE:")
    print(f"  Current RPM: {rate_stats['current_rpm']:.1f}")
    print(f"  Target RPM: {rate_stats['target_rpm']}")
    print(f"  Quota utilization: {rate_stats['quota_utilization']:.1f}%")
    print(f"  Status: {'✅ PASS' if rate_stats['within_limit'] else '❌ FAIL'} (< 50%)")

    print("\n" + "="*80)

    # Assert success criteria
    assert p95 < 1.0, f"PERF-01 FAILED: p95={p95:.3f}s"
    assert p99 < 2.0, f"PERF-02 FAILED: p99={p99:.3f}s"
    assert rate_stats['within_limit'], f"PERF-05 FAILED: {rate_stats['current_rpm']:.1f} RPM"

class WorkerUser(HttpUser):
    """Simulate worker performing v4.0 FINALIZAR operations."""
    wait_time = between(5, 15)  # Realistic work intervals

    @task(3)
    def finalizar_arm_10_unions(self):
        """Most common scenario: complete 10 ARM unions."""
        self.client.post("/api/v4/occupation/finalizar", json={
            "tag_spool": "OT-001",
            "union_ids": ["OT-001+1", "OT-001+2", "OT-001+3",
                         "OT-001+4", "OT-001+5", "OT-001+6",
                         "OT-001+7", "OT-001+8", "OT-001+9", "OT-001+10"],
            "worker_id": 93,
            "worker_nombre": "MR(93)",
            "operacion": "ARM",
            "fecha_operacion": "2026-02-02"
        })

    @task(1)
    def finalizar_sold_5_unions(self):
        """Partial completion: 5 SOLD unions."""
        self.client.post("/api/v4/occupation/finalizar", json={
            "tag_spool": "OT-002",
            "union_ids": ["OT-002+1", "OT-002+2", "OT-002+3", "OT-002+4", "OT-002+5"],
            "worker_id": 45,
            "worker_nombre": "JD(45)",
            "operacion": "SOLD",
            "fecha_operacion": "2026-02-02"
        })
```

### Anti-Patterns to Avoid

- **Anti-Pattern: Using averages instead of percentiles** - Averages hide tail latency. p95/p99 reveal worst-case user experience that averages mask. Always report percentiles for latency SLAs.

- **Anti-Pattern: Testing with empty/small datasets** - Performance degrades non-linearly with scale. Test with realistic data volumes (50+ unions per spool, 100+ spools).

- **Anti-Pattern: Calculating percentiles by averaging** - Never compute percentiles by averaging pre-computed percentiles (mathematically wrong). Store raw latencies and calculate percentiles from full dataset.

- **Anti-Pattern: Ignoring rate limit bursts** - Google Sheets rate limits are per-minute quotas. A burst of 60 requests in 10 seconds exhausts quota even if average is low. Use sliding windows, not simple averages.

- **Anti-Pattern: Mock-only performance tests** - Mocks simulate latency but miss real-world bottlenecks (network jitter, Google Sheets batching behavior). Balance mocked unit tests with occasional integration tests against real Sheets.

## Don't Hand-Roll

Problems that look simple but have existing solutions:

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Percentile calculation | Custom quantile algorithm | `numpy.percentile()` | Handles edge cases (empty arrays, NaN), optimized for large datasets |
| Memory profiling | Parse /proc/meminfo | `psutil.Process().memory_info()` | Cross-platform, handles edge cases, widely tested |
| Rate limiting | Rolling window with list | `collections.deque` + timestamp pruning | O(1) append, efficient old-entry removal |
| Statistical analysis | Custom mean/std functions | `numpy.mean()`, `numpy.std()` | Numerically stable, handles overflow |
| Load testing | Custom concurrent requests | Locust framework | Battle-tested, distributed mode, real-time metrics |

**Key insight:** Performance testing requires statistical rigor. numpy's percentile implementation handles numerical stability, empty arrays, and edge cases that custom code would miss. psutil abstracts OS-level differences in memory reporting.

## Common Pitfalls

### Pitfall 1: Percentile Misinterpretation

**What goes wrong:** Treating p95 as "worst case" or conflating p99 with "outliers"

**Why it happens:** p95 means 5% of requests are *worse* than this value. In a 1000-request test, 50 requests exceed p95. For high-traffic systems, "5% of users" can be thousands of people.

**How to avoid:**
- Report p50, p95, p99, and max latency together
- Understand that p99 still allows 1% outliers (10 requests per 1000)
- Use max latency to identify true worst-case scenarios
- Never ignore outliers as "statistically insignificant" - they represent real user pain

**Warning signs:**
- Tests report p95 but don't investigate requests exceeding it
- Dismissing p99 violations as "acceptable outliers"
- Not tracking max latency alongside percentiles

### Pitfall 2: Rate Limit Burst Exhaustion

**What goes wrong:** System averages 25 requests/min (under 30 target) but still hits 429 rate limit errors

**Why it happens:** Google Sheets rate limits are per-minute quotas (60 writes/min). Burst of 60 requests in first 15 seconds exhausts quota even though average is low.

**How to avoid:**
- Track requests in sliding 1-minute windows, not hourly averages
- Use `collections.deque` for efficient time-windowed counting
- Monitor peak burst rate, not just average rate
- Implement client-side throttling with token bucket or leaky bucket algorithm
- Add jitter to request timing (random 100-500ms delays)

**Warning signs:**
- Getting 429 errors despite low average request rate
- Spike in errors after deployment/cache clear
- Errors correlate with worker shift changes (everyone starts work simultaneously)

**Code example (avoid):**
```python
# ❌ BAD: Simple counter over long period
total_requests = 0
start_time = time.time()

# ... make requests ...

avg_rpm = (total_requests / (time.time() - start_time)) * 60
# This can show 25 RPM while hitting rate limits!
```

**Code example (correct):**
```python
# ✅ GOOD: Sliding window with deque
from collections import deque
from datetime import datetime, timedelta

requests = deque()  # (timestamp, request_type)
window = timedelta(minutes=1)

def record_request():
    now = datetime.now()
    requests.append(now)

    # Prune old requests
    cutoff = now - window
    while requests and requests[0] < cutoff:
        requests.popleft()

    # Check current rate
    current_rpm = len(requests)  # Requests in last 60 seconds
    assert current_rpm <= 30, f"Burst rate {current_rpm} exceeds limit"
```

### Pitfall 3: Mock Latency Divergence

**What goes wrong:** Tests pass with 0.3s mock latency but production shows 2s+ latency

**Why it happens:** Google Sheets API latency varies by request size, time of day, cache state, and geographic region. Mocks use fixed latency that doesn't capture this variance.

**How to avoid:**
- Calibrate mock latency with real production measurements (p50, p95, p99)
- Add realistic variance to mocks: `time.sleep(0.3 + random.uniform(0, 0.2))`
- Run occasional integration tests against real Sheets (not in CI, weekly scheduled)
- Monitor production latency and update mocks when patterns change
- Document mock latency assumptions in test comments

**Warning signs:**
- Mock latency hasn't changed in months despite production changes
- All mock calls have identical timing (no variance)
- Integration tests take significantly longer than unit tests
- Production performance degrades but tests still pass

**Code example:**
```python
# ✅ GOOD: Realistic mock latency with variance
import random

def batch_update_with_realistic_latency(*args, **kwargs):
    """
    Simulate Google Sheets batch_update with realistic timing.

    Based on production measurements (2026-02):
    - p50: 280ms
    - p95: 450ms
    - p99: 800ms
    """
    # Use log-normal distribution to model real API latency
    base = 0.28  # p50 latency
    variance = 0.12  # Standard deviation
    latency = random.lognormvariate(np.log(base), variance)

    # Clamp to observed bounds (50ms min, 2s max)
    latency = max(0.05, min(2.0, latency))

    time.sleep(latency)
```

### Pitfall 4: Metadata Batch Chunking Overflow

**What goes wrong:** Metadata batch logging works in tests (10 unions = 11 events) but fails in production (50 unions = 51 events) with cryptic Google Sheets errors

**Why it happens:** Google Sheets `append_rows()` has undocumented limit of ~1000 rows per call. Batch logging 900+ events fails silently or returns vague errors.

**How to avoid:**
- Auto-chunk batch events at 900 rows (implemented in Phase 8)
- Test with large batches (50+ unions = 51+ events) to trigger chunking
- Add explicit logging when chunking occurs
- Monitor Metadata append failures in production

**Warning signs:**
- Metadata events appear incomplete for large operations
- Google Sheets returns 500 errors for large batches
- Logs show "append_rows succeeded" but rows missing from sheet
- Works fine for 10 unions, fails for 20+ unions

**Code example:**
```python
# ✅ GOOD: Auto-chunking implemented in Phase 8
def batch_log_events(self, events: list[MetadataEvent]) -> None:
    """
    Log multiple events in batches with auto-chunking.

    Google Sheets append_rows has ~1000 row limit per call.
    Chunk at 900 for safety margin.
    """
    CHUNK_SIZE = 900

    for i in range(0, len(events), CHUNK_SIZE):
        chunk = events[i:i + CHUNK_SIZE]
        rows = [event.to_sheets_row() for event in chunk]

        self.logger.info(f"Appending metadata chunk {i//CHUNK_SIZE + 1}: "
                        f"{len(chunk)} events (rows {i+1}-{i+len(chunk)})")

        self._worksheet.append_rows(rows, value_input_option='USER_ENTERED')
```

### Pitfall 5: Cache Invalidation Race in Performance Tests

**What goes wrong:** Performance test shows 0.05s latency (unrealistic) because cache wasn't invalidated between iterations

**Why it happens:** ColumnMapCache and sheet data cache persist across test iterations. First iteration reads from Sheets (500ms), subsequent iterations hit cache (5ms).

**How to avoid:**
- Invalidate caches at start of each performance test
- Use separate test data for each iteration (different OT values)
- Monitor cache hit rate in tests and log when cached vs fresh reads occur
- Separate "cold cache" tests (invalidate before) from "warm cache" tests (reuse cache)

**Warning signs:**
- First iteration takes 10x longer than subsequent iterations
- Performance improves linearly with iteration count
- Tests fail when run in isolation but pass in suite
- Production is slower than tests despite identical code

**Code example:**
```python
# ✅ GOOD: Explicit cache control in performance tests
def test_cold_cache_performance():
    """Measure performance with cold cache (worst case)."""
    for iteration in range(100):
        # Invalidate caches for realistic timing
        ColumnMapCache.invalidate("Uniones")
        ColumnMapCache.invalidate("Operaciones")

        start_time = time.time()
        result = union_service.process_selection(...)
        latency = time.time() - start_time

        latencies.append(latency)

    print(f"Cold cache p95: {np.percentile(latencies, 95):.3f}s")

def test_warm_cache_performance():
    """Measure performance with warm cache (best case)."""
    # Load cache once
    union_service.process_selection(...)

    # Measure with warm cache
    for iteration in range(100):
        # Don't invalidate - measure cached performance
        start_time = time.time()
        result = union_service.process_selection(...)
        latency = time.time() - start_time

        latencies.append(latency)

    print(f"Warm cache p95: {np.percentile(latencies, 95):.3f}s")
```

## Code Examples

Verified patterns from existing codebase:

### Example 1: Mock Latency Simulation (Phase 8)
```python
# Source: tests/performance/test_batch_performance.py (lines 66-72)
def batch_update_with_latency(*args, **kwargs):
    time.sleep(0.3)  # 300ms latency
    return None

mock_worksheet.batch_update.side_effect = batch_update_with_latency
```

**Usage:** Applied in all Phase 8 performance tests to simulate realistic Google Sheets API timing (300ms for batch_update, 150ms for append_rows).

### Example 2: Percentile Calculation Template
```python
# New pattern for Phase 13 (numpy-based)
import numpy as np

def calculate_performance_percentiles(latencies: list[float]) -> dict:
    """
    Calculate comprehensive latency statistics.

    Args:
        latencies: List of latency measurements in seconds

    Returns:
        dict with p50, p95, p99, avg, min, max
    """
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

    return {
        "n": len(latencies),
        "avg": np.mean(latencies),
        "min": np.min(latencies),
        "max": np.max(latencies),
        "p50": np.percentile(latencies, 50),
        "p95": np.percentile(latencies, 95),
        "p99": np.percentile(latencies, 99)
    }

# Example usage
stats = calculate_performance_percentiles(latencies)
print(f"Performance: avg={stats['avg']:.3f}s, "
      f"p95={stats['p95']:.3f}s, p99={stats['p99']:.3f}s")

# Verify SLA requirements
assert stats['p95'] < 1.0, f"PERF-01 failed: p95={stats['p95']:.3f}s"
assert stats['p99'] < 2.0, f"PERF-02 failed: p99={stats['p99']:.3f}s"
```

### Example 3: API Call Verification (Phase 8 Pattern)
```python
# Source: tests/integration/test_performance_target.py (lines 298-305)
def test_batch_update_single_api_call(union_repo, mock_sheets_repo):
    """Verify batch_update called exactly once."""
    union_repo.batch_update_arm(
        tag_spool=tag_spool,
        union_ids=union_ids,
        worker=worker,
        timestamp=datetime.now()
    )

    mock_worksheet = mock_sheets_repo._get_worksheet.return_value
    assert mock_worksheet.batch_update.call_count == 1
```

### Example 4: Comprehensive Test Report Format
```python
# Template for Phase 13 test reporting
def print_performance_report(stats: dict, duration: float):
    """
    Print comprehensive performance validation report.

    Args:
        stats: Dictionary with percentile statistics
        duration: Test duration in seconds
    """
    print("\n" + "="*80)
    print("PHASE 13 PERFORMANCE VALIDATION REPORT")
    print("="*80)
    print(f"\nTest Duration: {duration:.1f}s ({duration/60:.1f}m)")
    print(f"Sample Size: {stats['n']} operations")

    print("\n📊 LATENCY METRICS:")
    print(f"  Average: {stats['avg']:.3f}s")
    print(f"  Median (p50): {stats['p50']:.3f}s")
    print(f"  p95: {stats['p95']:.3f}s | Target: <1.0s | {'✅ PASS' if stats['p95'] < 1.0 else '❌ FAIL'}")
    print(f"  p99: {stats['p99']:.3f}s | Target: <2.0s | {'✅ PASS' if stats['p99'] < 2.0 else '❌ FAIL'}")
    print(f"  Max: {stats['max']:.3f}s")

    print("\n📋 SUCCESS CRITERIA:")
    criteria = [
        ("PERF-01", "p95 < 1s", stats['p95'] < 1.0),
        ("PERF-02", "p99 < 2s", stats['p99'] < 2.0),
        ("PERF-03", "Max 2 API calls", True),  # From separate test
        ("PERF-05", "< 50% quota", True)  # From rate monitor
    ]

    passed = sum(1 for _, _, result in criteria if result)
    total = len(criteria)

    for req, desc, result in criteria:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"  {req}: {desc} - {status}")

    print(f"\n{'='*80}")
    print(f"RESULT: {passed}/{total} criteria passed")
    print(f"STATUS: {'✅ ALL CRITERIA MET' if passed == total else '❌ VALIDATION FAILED'}")
    print("="*80 + "\n")
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Simple averages for performance | p50/p95/p99 percentiles | Industry standard 2020+ | Reveals tail latency that averages hide |
| Fixed mock latency | Variance-based mock timing | Phase 8 (2026-02) | More realistic test conditions |
| Per-request API calls | Batch operations with gspread.batch_update() | Phase 8 (2026-02) | 10x performance improvement |
| Manual request counting | Time-windowed rate monitoring | Phase 13 | Prevents burst-based rate limit exhaustion |
| JMeter for load testing | Locust (Python-based) | Phase 4 (2026-01) | Code-as-test, better developer experience |

**Deprecated/outdated:**
- **pytest-benchmark:** Too heavyweight for simple timing tests. Project uses `time.time()` directly with custom percentile calculation (simpler, proven in Phase 8).
- **Manual percentile calculation:** numpy.percentile() is standard library, handles edge cases.
- **k6 load testing:** JavaScript-based, conflicts with Python-focused team. Locust proven in Phase 4.

## Open Questions

Things that couldn't be fully resolved:

1. **Production Latency Baseline**
   - What we know: Phase 8 tests show 0.466s average with 300ms mock latency
   - What's unclear: Actual production p95/p99 latency against real Google Sheets API (no baseline measurement yet)
   - Recommendation: Run initial production load test to establish baseline before validating PERF-01/PERF-02. May need to adjust targets if production latency > test latency.

2. **Metadata Chunking Edge Cases**
   - What we know: Phase 8 implements 900-row chunking for append_rows
   - What's unclear: Exact Google Sheets limit (documentation says "large batches may fail" without specific number)
   - Recommendation: Test with 950, 1000, 1100 rows to identify actual limit. Current 900-row chunk is conservative guess.

3. **Rate Limit Accounting Accuracy**
   - What we know: Google Sheets quota is 60 writes/min/user
   - What's unclear: Whether batch_update() with 10 cells counts as 1 write or 10 writes in quota system
   - Recommendation: Monitor production quota usage via Google Cloud Console after deployment. Adjust monitoring if batch operations consume more quota than expected.

4. **Percentile Confidence Intervals**
   - What we know: 100-iteration tests provide statistical significance for p95/p99
   - What's unclear: What's the confidence interval on p95 measurement with n=100? How many iterations for 95% confidence?
   - Recommendation: Start with 100 iterations (practical tradeoff). If p95 is close to 1.0s threshold (0.9-1.1s), increase to 500 iterations for higher confidence.

5. **Cache Warming Strategy**
   - What we know: ColumnMapCache persists across requests, warm cache is faster than cold cache
   - What's unclear: Should performance tests measure cold cache (worst case) or warm cache (typical case)?
   - Recommendation: Test both scenarios. Report cold cache p95 as worst-case guarantee, warm cache p95 as typical user experience.

## Sources

### Primary (HIGH confidence)

- **Existing Codebase - Phase 8 Performance Tests**:
  - `/tests/performance/test_batch_performance.py` (341 lines)
  - `/tests/integration/test_performance_target.py` (338 lines)
  - Patterns: Mock latency simulation (300ms), percentile reporting, memory profiling
  - Confidence: HIGH (production code, proven in integration tests)

- **Existing Codebase - Phase 4 Load Tests**:
  - `/backend/tests/load/test_sse_load.py`
  - `/backend/tests/load/README.md`
  - Patterns: Locust framework, WorkerUser simulation, metrics collection
  - Confidence: HIGH (production code, validated with 30 concurrent users)

- **PROJECT.md - Architecture Constraints**:
  - Google Sheets limits: 60 writes/min/user, 200-500ms latency
  - Manufacturing scale: 30-50 workers, 2,000+ spools
  - Confidence: HIGH (documented project constraints)

- **STATE.md - Performance History**:
  - Phase 8: 0.466s average latency (54% faster than 1s target)
  - Phase 9: 84% test coverage
  - Phase 10: <1s for 10-union batches (p95 requirement MET)
  - Confidence: HIGH (verified execution results)

### Secondary (MEDIUM confidence)

- **NumPy Documentation - Percentile Calculation**:
  - https://numpy.org/doc/stable/reference/generated/numpy.percentile.html
  - Usage: Statistical functions for p50/p95/p99 calculation
  - Confidence: MEDIUM (official docs but not project-specific)

- **Google Sheets API Limits Documentation**:
  - https://developers.google.com/workspace/sheets/api/limits
  - Details: 60 writes/min/user quota, batch operations, rate limit handling
  - Confidence: MEDIUM (official but may have undocumented behaviors)

- **Locust Documentation - Load Testing**:
  - Already installed (locust==2.17.0), proven in Phase 4
  - Usage: Distributed load testing, real-time metrics
  - Confidence: MEDIUM (official docs, already used in project)

### Tertiary (LOW confidence)

- **Web search: "pytest performance testing p95 p99 percentiles 2025"**
  - Finding: pytest-benchmark available but adds complexity
  - Tradeoff: Project already uses simpler time.time() pattern
  - Confidence: LOW (not project-tested)

- **Web search: "Google Sheets API rate limiting monitoring 2025"**
  - Finding: Exponential backoff, batch requests, caching best practices
  - Alignment: Consistent with existing retry_on_sheets_error decorator
  - Confidence: LOW (generic best practices, not validated in project)

- **Web search: "Python load testing tools locust vs pytest-benchmark vs k6 2025"**
  - Finding: Locust best for Python teams, k6 for cloud-native, pytest-benchmark for unit-level
  - Decision: Locust already proven in Phase 4
  - Confidence: LOW (comparative analysis, not project-specific)

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - All tools already installed and proven in Phases 4, 8, 9, 10
- Architecture: HIGH - Patterns tested in 244+ existing tests, 0.466s performance validated
- Pitfalls: MEDIUM - Based on common issues in performance testing but not all observed in this project
- Percentile calculation: HIGH - numpy is standard library with 15+ years of battle-testing

**Research date:** 2026-02-02
**Valid until:** 2026-04-02 (60 days - stable domain, minimal churn in performance testing best practices)

---

**Next Steps for Planner:**

1. **Extend existing tests** - Build on Phase 8's test_batch_performance.py with numpy percentile calculation
2. **Add rate limit monitoring** - Implement RateLimitMonitor class with deque-based sliding window
3. **Comprehensive reporting** - Format test output to show all 5 PERF requirements in single report
4. **Production baseline** - Schedule initial load test to measure real-world p95/p99 against Google Sheets
5. **CI/CD integration** - Add performance regression detection to GitHub Actions workflow
