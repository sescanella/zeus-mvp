# Integration Test Guide

This guide explains how to run integration tests for Phase 2 race condition prevention.

## Prerequisites

### 1. Redis Server Running

Start Redis locally:
```bash
# macOS (Homebrew)
brew services start redis

# Or manually
redis-server

# Verify running
redis-cli ping  # Should return "PONG"
```

### 2. Google Sheets Access

Ensure credentials are configured:
```bash
# Check credentials file exists
ls -la credenciales/zeus-mvp-81282fb07109.json

# Verify environment variable
echo $GOOGLE_SHEET_ID
```

### 3. FastAPI Backend Running

Start the backend server:
```bash
# Activate venv
source venv/bin/activate

# Start server
cd backend
uvicorn main:app --reload --port 8000

# Verify server running
curl http://localhost:8000/api/health
```

## Running Integration Tests

### Full Integration Test Suite

Run all race condition tests:
```bash
# From project root with venv activated
pytest tests/integration/test_race_conditions.py -v

# With detailed output
pytest tests/integration/test_race_conditions.py -v -s
```

### Specific Test Cases

Run individual tests:

**Test 1: Concurrent TOMAR (10 workers)**
```bash
pytest tests/integration/test_race_conditions.py::test_concurrent_tomar_prevents_double_booking -v
```

Expected output:
- ✅ 1 success (200 OK)
- ✅ 9 conflicts (409 CONFLICT)
- ✅ Race condition prevented

**Test 2: Concurrent PAUSAR (ownership)**
```bash
pytest tests/integration/test_race_conditions.py::test_concurrent_pausar_only_owner_succeeds -v
```

Expected output:
- ✅ 1 success (owner)
- ✅ 4 forbidden (non-owners)

**Test 3: Concurrent COMPLETAR (ownership)**
```bash
pytest tests/integration/test_race_conditions.py::test_concurrent_completar_only_owner_succeeds -v
```

Expected output:
- ✅ 1 success (owner)
- ✅ 4 forbidden (non-owners)

**Test 4: Batch TOMAR (partial success)**
```bash
pytest tests/integration/test_race_conditions.py::test_batch_tomar_partial_success -v
```

Expected output:
- ✅ 7 succeeded
- ✅ 3 failed (pre-occupied)

## Running Unit Tests

Unit tests don't require infrastructure:

**All unit tests:**
```bash
pytest tests/unit/ -v
```

**Redis lock service tests:**
```bash
pytest tests/unit/test_redis_lock_service.py -v
```

**Occupation service tests:**
```bash
pytest tests/unit/test_occupation_service.py -v
```

**Conflict service tests:**
```bash
pytest tests/unit/test_conflict_service.py -v
```

## Verification Checklist

After running all tests, verify:

- [ ] Integration tests pass (all green)
- [ ] Unit tests pass (all green)
- [ ] Race condition test shows 1 success + 9 conflicts
- [ ] Ownership tests prevent unauthorized operations
- [ ] Batch operations handle partial success correctly
- [ ] No errors in backend logs
- [ ] Redis lock metrics look reasonable
- [ ] Google Sheets data consistent after tests

## Troubleshooting

### Integration Tests Fail

**Error: Connection refused (FastAPI)**
- Start backend server: `uvicorn main:app --reload`
- Check port 8000 not in use: `lsof -i :8000`

**Error: Redis connection failed**
- Start Redis: `brew services start redis`
- Check Redis running: `redis-cli ping`

**Error: Google Sheets API error**
- Verify credentials file exists
- Check GOOGLE_SHEET_ID environment variable
- Verify service account has sheet access

**Error: 404 endpoint not found**
- Verify routes registered in main.py
- Check endpoint paths match test URLs
- Review FastAPI startup logs

### Unit Tests Fail

**Error: Import errors**
- Activate venv: `source venv/bin/activate`
- Install dependencies: `pip install -r backend/requirements.txt`

**Error: Mock assertion failures**
- Review mock setup in fixtures
- Check service method signatures match mocks
- Verify expected vs actual call arguments

## Test Data Cleanup

After integration tests, clean up test data:

```bash
# Connect to Redis and flush test locks
redis-cli
> KEYS spool_lock:TEST-*
> DEL spool_lock:TEST-RACE-001
> DEL spool_lock:TEST-RACE-002
# ... delete all TEST-* locks

# Google Sheets cleanup (manual)
# Remove test rows with TAG starting with "TEST-"
```

## Performance Expectations

Integration tests should complete within:
- Concurrent TOMAR test: < 10 seconds
- Ownership tests: < 5 seconds each
- Batch TOMAR test: < 15 seconds
- Total suite: < 60 seconds

If tests take longer:
- Check Redis latency: `redis-cli --latency`
- Check Google Sheets API rate limiting
- Verify network connectivity

## Next Steps After Tests Pass

1. Review backend logs for warnings/errors
2. Check Redis lock metrics
3. Verify Google Sheets data integrity
4. Document any edge cases discovered
5. Consider adding more test scenarios if needed
6. Update test data fixtures for new scenarios

---

**Note:** These tests validate Phase 2 race condition prevention implementation.
All tests should PASS after Plans 02-01, 02-02, and 02-03 are complete.
