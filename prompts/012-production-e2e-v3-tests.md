<objective>
Execute comprehensive end-to-end tests against ZEUES v3.0 production deployment to validate all TOMAR/PAUSAR/COMPLETAR workflows work correctly with real Google Sheets and Railway backend.

**Purpose:** Smoke test production stability before continuing v4.0 development. Detect regressions, validate v3.0 features, and ensure 7-day rollback window (expires 2026-02-02) has stable baseline.

**Test Scope:** ARM, SOLD, Metrología, Reparación workflows + Race conditions + SSE streaming + Metadata audit trail

**Test Spool:** `TEST-02` only (exclusive - can modify/reset this spool's data)
</objective>

<context>
@CLAUDE.md - for production URLs and architecture details
@.planning/PROJECT.md - for v3.0 requirements and success criteria

**Production Environment:**
- Backend API: https://zeues-backend-mvp-production.up.railway.app
- Frontend: https://zeues-frontend.vercel.app
- Google Sheets: Production (ID: 17iOaq2sv4mSOuJY4B8dGQIsWTTUKPspCtb7gk6u-MaQ)
- Redis: Production instance via Railway
- Metadata: Append-only audit trail

**Why this matters:** v3.0 has been in production since 2026-01-28. We're developing v4.0 while v3.0 must remain stable. These tests validate production health before each v4.0 phase deployment.

**Context Note:** This is NOT a development test suite. This runs against LIVE production data with REAL Google Sheets writes. Only TEST-02 spool should be modified.
</context>

<requirements>
**11 Test Cases to Execute:**

1. **ARM Full Workflow** - TOMAR → PAUSAR → TOMAR (different worker) → COMPLETAR
2. **SOLD Prerequisite** - Validate SOLD cannot start before ARM complete
3. **Race Condition** - Two workers TOMAR same spool (one gets 409 Conflict)
4. **Optimistic Locking** - Version conflict with stale UUID tokens
5. **Metrología Instant** - COMPLETAR without TOMAR, binary APROBADO/RECHAZADO
6. **Reparación Cycles** - 3-cycle limit before BLOQUEADO state
7. **SSE Streaming** - Real-time updates in < 10 seconds
8. **History Endpoint** - Complete audit trail with session durations
9. **Invalid Transitions** - Error handling (PAUSAR without TOMAR, COMPLETAR wrong worker, etc.)
10. **Nonexistent Spool** - 404 for invalid TAG_SPOOL
11. **Rate Limits** - 50 rapid operations stay under Google Sheets 60 writes/min limit

**Validation Requirements (Per Operation):**
After each operation, validate:
- HTTP response (status code + JSON structure)
- Google Sheets state (Ocupado_Por, dates, Estado_Detalle, version)
- Redis lock (exists/released at `spool:TEST-02:lock`)
- Metadata event logged (correct evento_tipo, worker_id, timestamps)
- SSE stream updated (if applicable)

**Critical Constraint:** Only modify TEST-02 spool. Do NOT touch other production spools. This is LIVE production data.
</requirements>

<implementation>
**Setup Phase:**

1. **Fetch Active Workers:**
   ```bash
   curl -s https://zeues-backend-mvp-production.up.railway.app/api/workers | jq '.[] | select(.activo == true) | {id, nombre, apellido}'
   ```
   Select 2 workers: Worker A and Worker B (for handoff tests)

2. **Reset TEST-02 to Clean State:**
   Read current TEST-02 from Google Sheets, then prepare clean baseline:
   - Ocupado_Por: NULL
   - Fecha_Ocupacion: NULL
   - ARM_FECHA_INICIO: NULL
   - ARM_FECHA_FIN: NULL (Fecha_Armado)
   - SOL_FECHA_INICIO: NULL
   - SOL_FECHA_FIN: NULL (Fecha_Soldadura)
   - Armador: NULL
   - Soldador: NULL
   - Estado_Detalle: "Disponible para Armado"
   - version: Generate new UUID4

   **How to reset:** Use Google Sheets API directly with service account credentials from environment. The `SheetsRepository` class in backend can be used as reference.

3. **Verify Baseline:**
   ```bash
   curl https://zeues-backend-mvp-production.up.railway.app/api/spools/disponibles?operacion=ARM | jq '.[] | select(.tag_spool == "TEST-02")'
   ```
   Confirm TEST-02 appears in disponibles list.

**Test Execution Pattern:**

For each test case:
1. **Setup:** Prepare TEST-02 to required state (use helper function)
2. **Execute:** POST to API endpoint with TEST-02 and worker_id
3. **Validate:** Check response + query Sheets + check Redis (if accessible) + verify Metadata
4. **Log Result:** Record PASSED/FAILED with details
5. **Teardown:** Reset for next test (if needed)

**Helper Functions (Create in Python or Bash):**

```python
import requests
import uuid
from datetime import datetime

BASE_URL = "https://zeues-backend-mvp-production.up.railway.app"
TEST_SPOOL = "TEST-02"

def tomar_spool(worker_id: int, operacion: str) -> dict:
    """Execute TOMAR operation"""
    response = requests.post(
        f"{BASE_URL}/api/occupation/tomar",
        json={"tag_spool": TEST_SPOOL, "worker_id": worker_id, "operacion": operacion}
    )
    return {"status": response.status_code, "body": response.json()}

def pausar_spool(worker_id: int, operacion: str) -> dict:
    """Execute PAUSAR operation"""
    response = requests.post(
        f"{BASE_URL}/api/occupation/pausar",
        json={"tag_spool": TEST_SPOOL, "worker_id": worker_id, "operacion": operacion}
    )
    return {"status": response.status_code, "body": response.json()}

def completar_spool(worker_id: int, operacion: str) -> dict:
    """Execute COMPLETAR operation"""
    response = requests.post(
        f"{BASE_URL}/api/occupation/completar",
        json={"tag_spool": TEST_SPOOL, "worker_id": worker_id, "operacion": operacion}
    )
    return {"status": response.status_code, "body": response.json()}

def get_spool_state() -> dict:
    """Read TEST-02 current state from Sheets"""
    # Use SheetsRepository to read Operaciones sheet
    # Return dict with: ocupado_por, fecha_ocupacion, estado_detalle, version, etc.
    pass

def reset_test_spool():
    """Reset TEST-02 to clean 'Disponible para Armado' state"""
    # Use SheetsRepository.update_spool_state() to write clean state
    pass

def validate_metadata_event(evento_tipo: str, worker_id: int, operacion: str) -> bool:
    """Check if Metadata has expected event logged"""
    # Query Metadata sheet for recent event matching criteria
    # Return True if found, False otherwise
    pass
```

**Test Case Examples (Implement all 11):**

**Test 1: ARM Full Workflow (TOMAR → PAUSAR → TOMAR → COMPLETAR)**
```python
def test_arm_full_workflow(worker_a_id, worker_b_id):
    print("Test 1: ARM Full Workflow")

    # Reset
    reset_test_spool()

    # Worker A TOMAr
    result = tomar_spool(worker_a_id, "ARM")
    assert result["status"] == 200, f"TOMAR failed: {result}"

    # Validate occupation
    state = get_spool_state()
    assert state["ocupado_por"] == f"INICIALES({worker_a_id})", "Ocupado_Por not set"
    assert state["fecha_ocupacion"] is not None, "Fecha_Ocupacion not set"
    assert validate_metadata_event("SPOOL_TOMADO", worker_a_id, "ARM"), "Metadata missing TOMADO event"

    # Worker A PAUSAr
    result = pausar_spool(worker_a_id, "ARM")
    assert result["status"] == 200, f"PAUSAR failed: {result}"

    # Validate pause
    state = get_spool_state()
    assert state["ocupado_por"] is None, "Ocupado_Por not cleared after PAUSAR"
    assert state["arm_fecha_inicio"] is not None, "ARM_FECHA_INICIO lost after PAUSAR"
    assert validate_metadata_event("SPOOL_PAUSADO", worker_a_id, "ARM"), "Metadata missing PAUSADO event"

    # Worker B TOMAr (different worker)
    result = tomar_spool(worker_b_id, "ARM")
    assert result["status"] == 200, f"TOMAR by Worker B failed: {result}"

    # Worker B COMPLETAr
    result = completar_spool(worker_b_id, "ARM")
    assert result["status"] == 200, f"COMPLETAR failed: {result}"

    # Validate completion
    state = get_spool_state()
    assert state["fecha_armado"] is not None, "Fecha_Armado not set"
    assert state["armador"] == f"INICIALES({worker_b_id})", "Armador should be Worker B"
    assert "Disponible para Soldadura" in state["estado_detalle"], "Estado should be Disponible para Soldadura"
    assert validate_metadata_event("SPOOL_COMPLETADO", worker_b_id, "ARM"), "Metadata missing COMPLETADO event"

    print("✅ Test 1 PASSED")
```

**Test 3: Race Condition (Concurrent TOMAR)**
```python
def test_race_condition(worker_a_id, worker_b_id):
    print("Test 3: Race Condition")

    reset_test_spool()

    # Worker A TOMAr
    result_a = tomar_spool(worker_a_id, "ARM")
    assert result_a["status"] == 200, "Worker A TOMAR should succeed"

    # Worker B TOMAr immediately (should fail with 409 Conflict)
    result_b = tomar_spool(worker_b_id, "ARM")
    assert result_b["status"] == 409, f"Expected 409 Conflict, got {result_b['status']}"
    assert "already occupied" in result_b["body"]["detail"].lower(), "Error message should mention occupation"

    # Worker A PAUSAr to release
    pausar_spool(worker_a_id, "ARM")

    # Now Worker B can TOMAR
    result_b = tomar_spool(worker_b_id, "ARM")
    assert result_b["status"] == 200, "Worker B TOMAR should succeed after release"

    print("✅ Test 3 PASSED")
```

**Test 7: SSE Real-Time Streaming**
```python
import sseclient
import threading
import time

def test_sse_streaming(worker_a_id):
    print("Test 7: SSE Streaming")

    reset_test_spool()

    # Open SSE connection in background thread
    sse_events = []
    def listen_sse():
        response = requests.get(f"{BASE_URL}/api/sse/disponible?operacion=ARM", stream=True)
        client = sseclient.SSEClient(response)
        for event in client.events():
            sse_events.append({"time": time.time(), "data": event.data})
            if len(sse_events) >= 3:  # Capture first 3 events
                break

    sse_thread = threading.Thread(target=listen_sse, daemon=True)
    sse_thread.start()
    time.sleep(2)  # Wait for SSE connection to establish

    # TOMAR TEST-02
    start_time = time.time()
    tomar_spool(worker_a_id, "ARM")

    # Wait for SSE update (max 10 seconds)
    time.sleep(12)

    # Validate SSE received update about TEST-02 within 10 seconds
    found_update = False
    for event in sse_events:
        if event["time"] - start_time <= 10 and TEST_SPOOL in event["data"]:
            found_update = True
            latency = event["time"] - start_time
            print(f"   SSE latency: {latency:.1f}s")
            break

    assert found_update, "SSE did not receive TEST-02 update within 10 seconds"

    print("✅ Test 7 PASSED")
```

**Why These Patterns:**
- **Assertions first:** Fail fast with clear error messages
- **State validation:** Always check Sheets state after operations (not just HTTP response)
- **Metadata verification:** Critical for audit trail compliance
- **Cleanup:** Reset TEST-02 between tests to avoid state pollution
</implementation>

<output>
Create a Python script that executes all 11 tests sequentially:

**File:** `./test_production_v3_e2e.py`

**Structure:**
```python
#!/usr/bin/env python3
"""
ZEUES v3.0 Production E2E Test Suite

Tests all TOMAR/PAUSAR/COMPLETAR workflows against live production.
ONLY modifies TEST-02 spool.

Usage:
    python test_production_v3_e2e.py

Environment:
    - GOOGLE_SERVICE_ACCOUNT_EMAIL: Service account email
    - GOOGLE_PRIVATE_KEY: Service account private key
    - REDIS_URL: Redis connection URL (optional, for lock validation)
"""

import requests
import json
import time
from datetime import datetime
from typing import Dict, List, Optional

# ... (include helper functions from implementation section)

def main():
    print("🧪 ZEUES v3.0 Production E2E Tests")
    print("=" * 50)
    print(f"Environment: {BASE_URL}")
    print(f"Test Spool: {TEST_SPOOL}")
    print("")

    # Fetch workers
    workers = requests.get(f"{BASE_URL}/api/workers").json()
    active_workers = [w for w in workers if w.get("activo")]
    if len(active_workers) < 2:
        print("❌ ERROR: Need at least 2 active workers")
        return

    worker_a = active_workers[0]
    worker_b = active_workers[1]
    print(f"Workers: {worker_a['nombre']} ({worker_a['id']}), {worker_b['nombre']} ({worker_b['id']})")
    print("")

    # Run all tests
    results = []
    start_time = time.time()

    try:
        test_arm_full_workflow(worker_a['id'], worker_b['id'])
        results.append(("Test 1: ARM Full Workflow", "PASSED", None))
    except Exception as e:
        results.append(("Test 1: ARM Full Workflow", "FAILED", str(e)))

    # ... (add remaining 10 tests)

    # Final cleanup
    reset_test_spool()

    # Report
    duration = time.time() - start_time
    print("")
    print("=" * 50)
    passed = sum(1 for _, status, _ in results if status == "PASSED")
    failed = sum(1 for _, status, _ in results if status == "FAILED")
    print(f"Results: {passed}/{len(results)} PASSED ✅")
    if failed > 0:
        print(f"         {failed}/{len(results)} FAILED ❌")
    print(f"Duration: {duration:.0f} seconds")
    print("")

    # Failed tests details
    if failed > 0:
        print("Failed Tests:")
        for name, status, error in results:
            if status == "FAILED":
                print(f"  ❌ {name}")
                print(f"     Error: {error}")

    print("")
    print("v3.0 production deployment is " + ("STABLE ✅" if failed == 0 else "UNSTABLE ⚠️"))

if __name__ == "__main__":
    main()
```

**Report File:** `./test-results/production-e2e-{timestamp}.md`

After tests complete, save detailed results:
```markdown
# ZEUES v3.0 Production E2E Test Results

**Date:** 2026-02-02 15:30:00
**Environment:** https://zeues-backend-mvp-production.up.railway.app
**Test Spool:** TEST-02
**Workers:** MR(93), JD(45)
**Duration:** 8 minutes 32 seconds

## Summary

- **Total Tests:** 11
- **Passed:** 10/11 ✅
- **Failed:** 1/11 ❌
- **Coverage:** ARM (✓), SOLD (✓), Metrología (✓), Reparación (✓), SSE (⚠️), Error Handling (✓)

## Test Results

### ✅ Test 1: ARM Full Workflow
- TOMAR by Worker A: 200 OK
- PAUSAR by Worker A: 200 OK
- TOMAR by Worker B: 200 OK
- COMPLETAR by Worker B: 200 OK
- Metadata: 4 events logged correctly
- Estado_Detalle: "Disponible para Soldadura"

### ❌ Test 7: SSE Real-Time Streaming
- TOMAR executed successfully
- SSE update received in 12.3 seconds (> 10s threshold)
- **Issue:** SSE latency exceeds acceptance criteria
- **Recommendation:** Investigate Redis pub/sub delay

...

## Issues Found

1. **SSE Latency High:** 12.3s latency (threshold: 10s)
   - Possible cause: Redis pub/sub processing delay
   - Impact: Dashboard updates delayed
   - Severity: Medium

## Recommendations

1. Investigate SSE latency issue before v4.0 Phase 8 deployment
2. Consider adding Redis pub/sub monitoring
3. All other v3.0 features stable - safe to continue v4.0 development

## Cleanup

- TEST-02 reset to "Disponible para Armado" ✓
- No orphaned Redis locks detected ✓
- Production data integrity maintained ✓
```
</output>

<verification>
Before declaring tests complete, verify:

1. **All 11 tests executed** - Check test results list has 11 entries
2. **TEST-02 cleaned up** - Final state is "Disponible para Armado" with NULL dates
3. **No production impact** - Only TEST-02 was modified, other spools untouched
4. **Results documented** - Markdown report saved to `./test-results/`
5. **Environment stable** - Backend health check passes: `GET /api/health`

**If any test fails:**
- Document the failure with full error details
- Capture current TEST-02 state from Sheets
- Check last 5 Metadata events for TEST-02
- Do NOT continue to next test until failure is analyzed
- Mark production as UNSTABLE in final report

**Manual Verification Steps:**
1. Open Google Sheets and locate TEST-02 row
2. Verify Estado_Detalle column shows expected state
3. Check Metadata sheet for complete event history
4. If possible, check Redis for orphaned locks: `redis-cli KEYS "spool:TEST-02:*"`
</verification>

<success_criteria>
- [ ] All 11 test cases implemented and executed
- [ ] Test script created at `./test_production_v3_e2e.py`
- [ ] Results report saved to `./test-results/production-e2e-{timestamp}.md`
- [ ] At least 9/11 tests pass (>80% success rate for production stability)
- [ ] TEST-02 cleaned up to baseline state
- [ ] No other production spools modified
- [ ] SSE latency measured (even if fails threshold)
- [ ] Metadata audit trail verified for all operations
- [ ] Final report includes issues found + recommendations
</success_criteria>

<constraints>
**CRITICAL Safety Constraints:**

1. **TEST-02 Only:** Never modify any spool except TEST-02. This is LIVE production data used by real workers.

2. **No Destructive Operations:** Do not delete rows from Metadata sheet (append-only). Do not truncate Operaciones sheet.

3. **Rate Limiting:** Space out rapid operations (Test 11) with 1-second delays to respect Google Sheets 60 writes/min limit. Why: Exceeding rate limits causes 429 errors that block legitimate production traffic.

4. **Redis Access Optional:** If Redis credentials not available, skip Redis lock validation. HTTP response + Sheets state validation is sufficient.

5. **Rollback Safety:** If TEST-02 gets corrupted during testing, restore from known baseline. Why: v3.0 has 7-day rollback window expiring 2026-02-02 - we need clean baseline for emergency rollback.

6. **No Frontend Testing:** This prompt focuses on backend API testing only. Frontend E2E with Playwright is out of scope (future enhancement).

7. **Timeout Handling:** If any API call takes > 30 seconds, mark test as FAILED and move to next test. Why: Production should respond in < 5 seconds - long timeouts indicate infrastructure issues.
</constraints>
