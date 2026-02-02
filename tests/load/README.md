# ZEUES v4.0 Load Testing

Comprehensive performance validation for Phase 13 validating all PERF requirements under realistic load.

## Overview

This directory contains Locust-based load tests that simulate 30-50 concurrent workers performing INICIAR/FINALIZAR operations with union selection.

## Performance Requirements

| Requirement | Target | Description |
|------------|--------|-------------|
| **PERF-01** | p95 < 1s | 95th percentile latency for 10-union batches |
| **PERF-02** | p99 < 2s | 99th percentile latency for all operations |
| **PERF-03** | Max 2 API calls | Single FINALIZAR uses max 2 Google Sheets API calls |
| **PERF-04** | 900 row chunks | Metadata batch logging auto-chunks at 900 rows |
| **PERF-05** | < 30 writes/min | Stay under 50% of Google Sheets quota (60 RPM) |

## Quick Start

### Prerequisites

```bash
# Activate virtual environment
source venv/bin/activate

# Ensure dependencies installed
pip install locust numpy psutil
```

### Run Load Test

```bash
# Headless mode (5-minute test with 30 users)
cd tests/load
locust -f locustfile.py --headless -u 30 -r 5 -t 5m --host http://localhost:8000

# Web UI mode (interactive)
locust -f locustfile.py --host http://localhost:8000
# Open http://localhost:8089 in browser
```

### View Results

After test completion, results are exported to `tests/load/results/`:

- `performance_report_YYYYMMDD_HHMMSS.json` - Complete metrics data
- `performance_metrics_YYYYMMDD_HHMMSS.csv` - Trending analysis
- `performance_report_YYYYMMDD_HHMMSS.html` - Human-readable report with charts

## Test Scenarios

### WorkerUser Tasks (locustfile.py)

| Task | Weight | Description |
|------|--------|-------------|
| `finalizar_arm_10_unions` | 3 | Most common: complete 10 ARM unions |
| `finalizar_sold_5_unions` | 2 | Partial completion: 5 SOLD unions (triggers PAUSAR) |
| `finalizar_arm_50_unions` | 1 | Stress test: 50 unions in single batch |
| `iniciar_new_spool` | 1 | Occupy spool without union selection |
| `query_disponibles_arm` | 1 | Read-only: query available ARM unions |
| `query_metricas` | 1 | Read-only: query pulgadas-diámetro metrics |

Wait time: 5-15 seconds between operations (realistic work intervals)

## Metrics Collection

### Latency Tracking

- **numpy percentiles**: p50, p95, p99 calculation
- **Per-operation breakdown**: latency by endpoint
- **Statistical analysis**: mean, std, min, max

### Rate Limit Monitoring

- **RateLimitMonitor**: sliding 60-second window
- **Burst detection**: >20 requests in 10 seconds
- **Quota utilization**: percentage of 60 RPM limit

### Memory Profiling

- **psutil monitoring**: baseline, peak, increase
- **Sampling**: every 10th request to reduce overhead
- **Threshold**: <50MB increase for large batches

### Error Categorization

- **By status code**: 403, 404, 409, 500
- **By exception type**: ValueError, ConnectionError, etc.
- **Detailed logging**: endpoint name + error message

## CI/CD Integration

### Exit Codes

- `0`: All PERF requirements met
- `1`: One or more PERF requirements failed (AssertionError)

### GitHub Actions Example

```yaml
- name: Run performance validation
  run: |
    source venv/bin/activate
    cd tests/load
    locust -f locustfile.py --headless -u 30 -r 5 -t 5m --host http://localhost:8000
  timeout-minutes: 10
```

### JUnit XML Output

(Future enhancement - requires pytest-locust plugin)

## Customization

### Adjust Test Parameters

```bash
# More users (50 workers)
locust -f locustfile.py --headless -u 50 -r 10 -t 10m --host http://localhost:8000

# Longer duration (30 minutes)
locust -f locustfile.py --headless -u 30 -r 5 -t 30m --host http://localhost:8000

# Custom spawn rate (1 user per second)
locust -f locustfile.py --headless -u 30 -r 1 -t 5m --host http://localhost:8000
```

### Modify User Behavior

Edit `locustfile.py` task weights:

```python
@task(5)  # Increase weight to 5 (more frequent)
def finalizar_arm_10_unions(self):
    ...
```

### Change Performance Thresholds

Edit `test_comprehensive_performance.py`:

```python
# Stricter latency requirement
assert lat["p95"] < 0.8, f"PERF-01 FAILED: p95={lat['p95']:.3f}s >= 0.8s"

# Lower rate limit target
rate_monitor = RateLimitMonitor(window_seconds=60, target_rpm=20)
```

## Troubleshooting

### Test Fails with Connection Errors

- **Check backend running**: `curl http://localhost:8000/health`
- **Verify Redis available**: `redis-cli ping`
- **Check logs**: `tail -f backend/logs/app.log`

### Rate Limit Exceeded

- **Reduce concurrent users**: `-u 20` instead of `-u 30`
- **Increase spawn rate interval**: `-r 2` instead of `-r 5`
- **Add delays**: Modify `wait_time = between(10, 20)` in locustfile.py

### Memory Usage Too High

- **Reduce batch size**: Change 50-union stress test to 30 unions
- **Shorter test duration**: `-t 2m` instead of `-t 5m`
- **Fewer concurrent users**: `-u 20` instead of `-u 30`

### Reports Not Generated

- **Check results directory**: `ls tests/load/results/`
- **Permissions issue**: `chmod 755 tests/load/results`
- **Disk space**: `df -h`

## Architecture

### Event Flow

1. **on_test_init**: Initialize PerformanceMetrics instance
2. **on_test_start**: Record baseline memory, start timestamp
3. **on_request** (per request): Track latency, API calls, errors, sample memory
4. **on_test_stop**: Calculate statistics, generate reports, validate criteria

### Metrics Collection

```
PerformanceMetrics
├── latencies: List[float]              # All request latencies
├── latencies_by_operation: Dict        # Per-endpoint breakdown
├── rate_monitor: RateLimitMonitor      # Sliding window tracking
├── api_calls_by_endpoint: Counter      # Call frequency
├── error_count: Counter                # Error categorization
├── memory_samples: List[float]         # Memory over time
└── requests_by_status: Counter         # HTTP status codes
```

### Report Generation

```
export_metrics()
├── JSON: Complete metrics data structure
├── CSV: Time-series data for trending
└── HTML: Human-readable with visualizations
```

## Performance Baselines

### Phase 8 (Integration Tests)

- **Average latency**: 0.466s (54% faster than 1s target)
- **10-union batch**: Consistently < 1s

### Phase 13 (Load Tests - Expected)

- **p95**: 0.7-0.9s under 30-user load
- **p99**: 1.2-1.8s under stress
- **Rate**: 15-25 RPM average (25-42% quota)
- **Memory**: +20-40MB during peak load

## References

- Phase 13 RESEARCH.md: Performance testing patterns
- Phase 8 integration tests: Mock latency simulation baseline
- Phase 4 SSE load tests: Original Locust patterns
- RateLimitMonitor (13-03): Sliding window implementation

---

**Last updated**: 2026-02-02
**Phase**: 13-04 Comprehensive Load Testing
