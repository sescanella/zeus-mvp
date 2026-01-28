# ZEUES Load Testing

Load tests for Phase 4 Real-Time Visibility performance verification.

## Requirements

Install load test dependencies:

```bash
pip install -r backend/tests/load/requirements.txt
```

Dependencies:
- `locust==2.17.0` - Load testing framework
- `sseclient-py==1.8.0` - SSE client library
- `requests==2.31.0` - HTTP client

## Running Load Tests

### 1. Check Infrastructure

Verify backend is running and endpoints are accessible:

```bash
python backend/tests/load/test_sse_load.py --check-only
```

Expected output:
```
✓ Backend health check passed
✓ SSE endpoint accessible
✓ Dashboard endpoint accessible
```

### 2. Run Load Test (Web UI)

Start Locust with web interface (recommended for first run):

```bash
locust -f backend/tests/load/test_sse_load.py --host=http://localhost:8000
```

Then open http://localhost:8089 in browser:
- Number of users: 30 (concurrent workers)
- Spawn rate: 5 (users/second)
- Duration: 10m (or 8h for full simulation)

### 3. Run Load Test (Headless)

For automated testing without UI:

```bash
# 10-minute test with 30 concurrent users
locust -f backend/tests/load/test_sse_load.py \
  --host=http://localhost:8000 \
  --users=30 \
  --spawn-rate=5 \
  --run-time=10m \
  --headless
```

For 8-hour shift simulation:
```bash
locust -f backend/tests/load/test_sse_load.py \
  --host=http://localhost:8000 \
  --users=30 \
  --spawn-rate=5 \
  --run-time=8h \
  --headless
```

## Success Criteria (Phase 4)

The load test verifies these requirements:

1. **SSE Latency < 10 seconds**
   - Measures time from event publish to client receipt
   - Max latency must be under 10,000ms

2. **Dashboard Shows All Occupied Spools**
   - Verifies SSE events are received
   - Events received > 0

3. **Connection Stability**
   - SSE connections survive 8-hour shift
   - Connection failure rate < 10%
   - Auto-reconnect on disconnect

4. **API Quota < 80 requests/min**
   - 30 concurrent workers stay under Google Sheets quota
   - Measured as total requests / duration

## Test Results

After test completion, results are printed:

```
================================================================================
LOAD TEST RESULTS - Phase 4 Success Criteria
================================================================================
Duration: 600.2s (0.17h)
Total users: 30

SSE METRICS:
  Events received: 1247
  Connection failures: 3
  Average latency: 342.5ms
  Max latency: 1893.2ms
  P95 latency: 876.4ms

API METRICS:
  Total requests: 732
  Requests/min: 73.2
  Failed requests: 12

SUCCESS CRITERIA:
  1. SSE latency < 10s: PASS (max: 1893.2ms)
  2. Dashboard updates working: PASS (1247 events)
  3. Connection stability: PASS (3 failures)
  4. API quota < 80 req/min: PASS (73.2 req/min)

================================================================================
RESULT: 4/4 criteria passed
STATUS: ALL CRITERIA PASSED ✓
================================================================================
```

## Simulation Details

Each WorkerUser simulates:
- Opens 1 SSE connection to `/api/sse/stream`
- Performs actions with 12-second intervals (5 actions/min):
  - TOMAR spool (weight: 3)
  - PAUSAR spool (weight: 1)
  - COMPLETAR spool (weight: 2)
  - Check dashboard (weight: 1)
- Worker IDs: 93-102 (10 unique workers)
- Operations: ARM or SOLD (can randomize)

With 30 users:
- 30 concurrent SSE connections
- ~150 actions/minute total
- ~75 Google Sheets API requests/min (estimate)

## Troubleshooting

**"Backend not accessible"**
- Ensure backend is running: `uvicorn main:app --reload --port 8000`
- Check CORS configuration allows localhost

**"SSE endpoint failed"**
- Verify Redis is running (SSE requires Redis pub/sub)
- Check backend logs for SSE errors

**"API quota exceeded" (429 errors)**
- Reduce number of users or spawn rate
- Increase wait_time in WorkerUser class
- Review Google Sheets API quota limits

**Connection failures > 10%**
- Check network stability
- Verify Redis memory/connections
- Review backend error logs for SSE issues

## Performance Optimization

If tests fail criteria:

1. **High SSE latency:**
   - Check Redis pub/sub performance
   - Verify network latency
   - Review backend event publishing code

2. **API quota exceeded:**
   - Implement caching for read-heavy endpoints
   - Batch write operations
   - Review sheet access patterns

3. **Connection instability:**
   - Increase Redis connection pool size
   - Verify keepalive/timeout settings
   - Check for memory leaks in SSE handler

## CI/CD Integration

For automated testing in CI:

```bash
# Run 5-minute smoke test
locust -f backend/tests/load/test_sse_load.py \
  --host=http://localhost:8000 \
  --users=10 \
  --spawn-rate=2 \
  --run-time=5m \
  --headless \
  --csv=results/load-test \
  --html=results/load-test-report.html
```

Results exported to CSV and HTML for analysis.
