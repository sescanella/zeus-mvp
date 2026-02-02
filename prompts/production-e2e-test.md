# Production E2E Test - v3.0 Workflows

**Purpose:** Execute comprehensive end-to-end tests against production deployment (Railway backend + Google Sheets production) to validate all v3.0 TOMAR/PAUSAR/COMPLETAR workflows work correctly.

**Test Spool:** `TEST-02` (EXCLUSIVE - this prompt can modify/delete this spool's data)

**Environments:**
- Backend: https://zeues-backend-mvp-production.up.railway.app
- Google Sheets: Production (ID: 17iOaq2sv4mSOuJY4B8dGQIsWTTUKPspCtb7gk6u-MaQ)
- Test Worker: Use an active worker from production data (fetch from `/api/workers`)

---

## Test Scope

### ✅ What to Test (v3.0 Features)

**ARM Workflow:**
1. TOMAR spool TEST-02 for ARM operation
2. Validate occupation (Ocupado_Por set, Redis lock created)
3. PAUSAR ARM work (partial completion)
4. Validate state transition (lock released, progress preserved)
5. TOMAR again (different worker can continue)
6. COMPLETAR ARM work
7. Validate completion (ARM dates set, state updated)

**SOLD Workflow:**
1. TOMAR spool TEST-02 for SOLD operation (after ARM complete)
2. Validate ARM prerequisite enforced
3. PAUSAR SOLD work
4. TOMAR again and COMPLETAR SOLD
5. Validate final state (both ARM and SOLD complete)

**Metrología Workflow:**
1. Instant COMPLETAR with APROBADO result
2. Validate no TOMAR required (instant completion)
3. Test RECHAZADO → triggers "Pendiente reparación"

**Reparación Workflow:**
1. TOMAR spool in RECHAZADO state
2. COMPLETAR reparación
3. Validate return to metrología queue
4. Test cycle limit (max 3 rejections before BLOQUEADO)

**Edge Cases:**
- Race condition: Two workers TOMAR same spool (one should fail with 409 Conflict)
- Version conflict: Concurrent updates with stale version tokens
- Invalid operations: SOLD before ARM, COMPLETAR without TOMAR
- State validation: Estado_Detalle reflects correct combined state

**SSE Streaming:**
- Verify SSE endpoint streams updates
- Validate disponible spools refresh after TOMAR/PAUSAR/COMPLETAR
- Check "quien-tiene-que" dashboard shows real-time occupation

**Metadata Audit Trail:**
- All TOMAR/PAUSAR/COMPLETAR events logged
- Worker ID, timestamps, operation type recorded
- History endpoint returns complete session data

---

## Test Protocol

### Setup Phase
1. **Fetch active worker:**
   ```bash
   GET /api/workers
   # Select first active worker, extract ID
   ```

2. **Reset TEST-02 to clean state:**
   - Clear Ocupado_Por, Fecha_Ocupacion
   - Reset ARM/SOLD dates to NULL
   - Set Estado_Detalle to "Disponible para Armado"
   - Generate new version UUID
   - **Use Google Sheets API directly or backend endpoint if available**

3. **Verify baseline:**
   ```bash
   GET /api/spools/disponibles?operacion=ARM
   # Confirm TEST-02 appears in disponibles list
   ```

### Test Execution Pattern

For each test case:
1. **Setup**: Prepare spool to required state
2. **Execute**: Call API endpoint with TEST-02
3. **Validate**: Check response + Sheets state + Redis + Metadata
4. **Teardown**: Reset for next test (if needed)

### Validation Checklist (Per Operation)

**After TOMAR:**
- [ ] Response: 200 OK with occupation details
- [ ] Sheets: Ocupado_Por = "INICIALES(ID)", Fecha_Ocupacion set
- [ ] Sheets: version UUID changed
- [ ] Redis: Lock exists at `spool:TEST-02:lock` with 1-hour TTL
- [ ] Metadata: SPOOL_TOMADO event logged
- [ ] SSE: TEST-02 removed from disponibles stream

**After PAUSAR:**
- [ ] Response: 200 OK
- [ ] Sheets: Ocupado_Por = NULL, Fecha_Ocupacion = NULL
- [ ] Sheets: Progress preserved (ARM_FECHA_INICIO still set if partial)
- [ ] Redis: Lock released
- [ ] Metadata: SPOOL_PAUSADO event logged with duration
- [ ] SSE: TEST-02 appears in disponibles stream again

**After COMPLETAR:**
- [ ] Response: 200 OK
- [ ] Sheets: Operation dates set (Fecha_Armado or Fecha_Soldadura)
- [ ] Sheets: Armador or Soldador set to worker
- [ ] Sheets: Ocupado_Por cleared, version updated
- [ ] Sheets: Estado_Detalle reflects completion
- [ ] Redis: Lock released
- [ ] Metadata: SPOOL_COMPLETADO event logged
- [ ] SSE: TEST-02 status updated in streams

---

## Test Cases (Detailed)

### Test 1: ARM Full Workflow (TOMAR → PAUSAR → TOMAR → COMPLETAR)

**Objective:** Validate complete ARM workflow with handoff between workers

**Steps:**
1. Reset TEST-02 to initial state (disponible para ARM)
2. Worker A TOMAr TEST-02 for ARM
3. Validate occupation state (all checks above)
4. Worker A PAUSAr ARM work
5. Validate pause state (lock released, progress preserved)
6. Worker B TOMAr TEST-02 for ARM (different worker)
7. Worker B COMPLETAr ARM work
8. Validate completion (ARM dates, Armador set to Worker B)

**Expected Results:**
- ARM_FECHA_INICIO set by Worker A (preserved across PAUSAR)
- Fecha_Armado set by Worker B
- Armador = Worker B (last to complete)
- Estado_Detalle = "Disponible para Soldadura"
- Metadata shows 2 TOMAR sessions (Worker A partial, Worker B complete)

**Endpoint sequence:**
```bash
POST /api/occupation/tomar
{
  "tag_spool": "TEST-02",
  "worker_id": <worker_a_id>,
  "operacion": "ARM"
}

POST /api/occupation/pausar
{
  "tag_spool": "TEST-02",
  "worker_id": <worker_a_id>,
  "operacion": "ARM"
}

POST /api/occupation/tomar
{
  "tag_spool": "TEST-02",
  "worker_id": <worker_b_id>,
  "operacion": "ARM"
}

POST /api/occupation/completar
{
  "tag_spool": "TEST-02",
  "worker_id": <worker_b_id>,
  "operacion": "ARM"
}
```

---

### Test 2: SOLD Prerequisite Validation

**Objective:** Validate SOLD cannot start before ARM is complete

**Steps:**
1. Reset TEST-02 to initial state (no ARM, no SOLD)
2. Attempt to TOMAR TEST-02 for SOLD
3. **Expected:** 400 Bad Request or 422 Unprocessable Entity
4. Complete ARM workflow (TOMAR → COMPLETAR)
5. Now TOMAR TEST-02 for SOLD
6. **Expected:** 200 OK

**Expected Error Message:**
```json
{
  "detail": "SOLD requires ARM to be initiated first"
}
```

---

### Test 3: Race Condition (Concurrent TOMAR)

**Objective:** Validate Redis atomic locks prevent double occupation

**Steps:**
1. Reset TEST-02 to disponible state
2. Worker A TOMAr TEST-02 (should succeed)
3. **Immediately** (without releasing lock) Worker B TOMAr TEST-02
4. **Expected:** Worker B gets 409 Conflict
5. Worker A PAUSAr or COMPLETAr
6. Now Worker B can TOMAR

**Expected Error (Worker B):**
```json
{
  "detail": "Spool TEST-02 is already occupied by Worker A"
}
```

---

### Test 4: Optimistic Locking (Version Conflict)

**Objective:** Validate version tokens prevent lost updates

**Steps:**
1. Reset TEST-02, note current version UUID
2. Worker A TOMAr TEST-02 (version changes to v2)
3. Manually update Sheets with old version (v1) in request
4. Attempt operation with stale version
5. **Expected:** 409 Conflict with version mismatch error

**Implementation:**
This requires reading current version from Sheets, then attempting update with old version. May need direct Sheets API access or custom endpoint.

---

### Test 5: Metrología Instant Completion

**Objective:** Validate metrología workflow (no TOMAR, instant COMPLETAR)

**Steps:**
1. Reset TEST-02, complete ARM + SOLD workflows (Estado = "Pendiente Metrología")
2. Call metrología COMPLETAR with resultado=APROBADO
3. Validate NO Redis lock created
4. Validate Estado_Detalle = "APROBADO - Metrología"
5. Validate Metadata event logged

**Endpoint:**
```bash
POST /api/metrologia/completar
{
  "tag_spool": "TEST-02",
  "worker_id": <metrologo_id>,
  "resultado": "APROBADO"
}
```

**Then test RECHAZADO:**
```bash
# Reset to Pendiente Metrología again
POST /api/metrologia/completar
{
  "tag_spool": "TEST-02",
  "worker_id": <metrologo_id>,
  "resultado": "RECHAZADO"
}
# Expected Estado_Detalle: "RECHAZADO - Ciclo 1/3"
```

---

### Test 6: Reparación Bounded Cycles

**Objective:** Validate 3-cycle limit before BLOQUEADO

**Steps:**
1. Reset TEST-02 to RECHAZADO state (Cycle 0)
2. TOMAR for reparación, COMPLETAR
3. Validate Estado = "Pendiente Metrología" (returns to queue)
4. Metrología RECHAZADO again (Cycle 1)
5. Repeat: Reparación → Metrología RECHAZADO (Cycle 2)
6. Repeat: Reparación → Metrología RECHAZADO (Cycle 3)
7. **Expected:** Estado_Detalle = "BLOQUEADO - Requiere Supervisor"
8. Validate no more reparación TOMAr allowed

**Cycle Counter Logic:**
- Cycle increments on each RECHAZADO
- Resets to 0 on APROBADO
- After 3rd rejection → BLOQUEADO state

---

### Test 7: SSE Real-Time Streaming

**Objective:** Validate SSE streams update in < 10 seconds

**Steps:**
1. Open SSE connection: `GET /api/sse/disponible?operacion=ARM`
2. In separate request, TOMAR TEST-02 for ARM
3. Monitor SSE stream for update event
4. Validate TEST-02 removed from disponibles within 10 seconds
5. PAUSAr TEST-02
6. Validate TEST-02 reappears in SSE stream within 10 seconds

**SSE Event Format:**
```
event: spool_update
data: {"tag_spool": "TEST-02", "estado": "OCUPADO", "ocupado_por": "MR(93)"}
```

---

### Test 8: History Endpoint (Audit Trail)

**Objective:** Validate complete session history logged

**Steps:**
1. Execute full workflow: TOMAR → PAUSAR → TOMAR → COMPLETAR (ARM)
2. Call history endpoint: `GET /api/history/TEST-02`
3. Validate response contains:
   - All 4 events (2 TOMAR, 1 PAUSAR, 1 COMPLETAR)
   - Correct timestamps (chronological order)
   - Worker IDs for each event
   - Session durations calculated
   - Operation type (ARM)

**Expected Response Structure:**
```json
{
  "tag_spool": "TEST-02",
  "events": [
    {
      "evento_tipo": "SPOOL_TOMADO",
      "worker_id": 93,
      "operacion": "ARM",
      "timestamp": "2026-02-02 10:00:00"
    },
    {
      "evento_tipo": "SPOOL_PAUSADO",
      "duracion_min": 15,
      "timestamp": "2026-02-02 10:15:00"
    },
    // ... more events
  ]
}
```

---

## Error Handling Tests

### Test 9: Invalid State Transitions

**Scenarios to test:**
1. PAUSAr spool without TOMAr first → 400 Bad Request
2. COMPLETAr spool not occupied by current worker → 403 Forbidden
3. TOMAr spool for SOLD before ARM complete → 422 Unprocessable Entity
4. Metrología on spool without ARM+SOLD complete → 422 Unprocessable Entity

**For each:**
- Execute invalid operation
- Validate error response (status code + message)
- Validate no state change in Sheets
- Validate no Metadata event logged

---

### Test 10: Nonexistent Spool

**Objective:** Validate graceful handling of invalid TAG_SPOOL

**Steps:**
1. TOMAr spool "NONEXISTENT-999"
2. **Expected:** 404 Not Found

---

## Performance & Limits

### Test 11: Google Sheets Rate Limits

**Objective:** Validate system stays under 60 writes/min limit

**Steps:**
1. Execute rapid sequence of 50 operations (TOMAR/PAUSAR cycles)
2. Measure time taken
3. Validate no rate limit errors (429 Too Many Requests)
4. Validate average operation time < 2 seconds

**Expected:**
- 50 operations should complete in ~2 minutes (average 2.4 sec/op)
- No 429 errors from Google Sheets API
- All operations successfully logged in Metadata

---

## Reporting

### Success Criteria

Report should include:
- **Total tests:** 11 test cases
- **Passed:** X/11
- **Failed:** Y/11 (with detailed error logs)
- **Duration:** Total execution time
- **Coverage:** ARM (✓), SOLD (✓), Metrología (✓), Reparación (✓), SSE (✓), Error handling (✓)

### Failure Details

For each failed test:
1. Test case name
2. Expected behavior
3. Actual behavior (response + Sheets state)
4. Error messages
5. Screenshots (if using browser)
6. Relevant Metadata events

### Cleanup

After all tests:
1. Reset TEST-02 to clean "Disponible para Armado" state
2. Clear any orphaned Redis locks
3. Document any issues found in `.planning/issues/` directory

---

## Implementation Notes

### Tools Available

- **Bash + curl:** For API requests
- **Python script:** For complex validation (read Sheets, check Redis)
- **MCP Docker Browser:** For frontend E2E tests (future enhancement)

### Environment Variables Needed

```bash
export PROD_API_URL="https://zeues-backend-mvp-production.up.railway.app"
export TEST_SPOOL="TEST-02"
export GOOGLE_SHEET_ID="17iOaq2sv4mSOuJY4B8dGQIsWTTUKPspCtb7gk6u-MaQ"
```

### Helper Functions (Suggested)

```bash
# Fetch active worker
get_test_worker() {
  curl -s "$PROD_API_URL/api/workers" | jq -r '.[0].id'
}

# Reset TEST-02 (via API or direct Sheets)
reset_test_spool() {
  # Implementation depends on available endpoints
  echo "Resetting TEST-02..."
}

# Validate response
assert_status() {
  local expected=$1
  local actual=$2
  if [ "$expected" != "$actual" ]; then
    echo "❌ Expected $expected, got $actual"
    exit 1
  fi
}

# Check Redis lock
check_redis_lock() {
  local tag=$1
  redis-cli -u "$REDIS_URL" GET "spool:${tag}:lock"
}
```

---

## Execution Checklist

Before running:
- [ ] Backend deployed to Railway (health check passes)
- [ ] Google Sheets credentials configured
- [ ] Redis accessible (if checking locks directly)
- [ ] TEST-02 spool exists in Operaciones sheet
- [ ] At least 2 active workers available (for handoff tests)

After running:
- [ ] All tests executed
- [ ] Results documented
- [ ] TEST-02 cleaned up
- [ ] Issues logged (if any failures)
- [ ] v3.0 stability confirmed ✅

---

## Success Output Example

```
🧪 ZEUES v3.0 Production E2E Tests
==================================

Environment: https://zeues-backend-mvp-production.up.railway.app
Test Spool: TEST-02
Workers: MR(93), JD(45)

✅ Test 1: ARM Full Workflow (TOMAR → PAUSAR → TOMAR → COMPLETAR) - PASSED
✅ Test 2: SOLD Prerequisite Validation - PASSED
✅ Test 3: Race Condition (Concurrent TOMAR) - PASSED
✅ Test 4: Optimistic Locking (Version Conflict) - PASSED
✅ Test 5: Metrología Instant Completion - PASSED
✅ Test 6: Reparación Bounded Cycles - PASSED
✅ Test 7: SSE Real-Time Streaming - PASSED (6.2s latency)
✅ Test 8: History Endpoint (Audit Trail) - PASSED
✅ Test 9: Invalid State Transitions - PASSED
✅ Test 10: Nonexistent Spool - PASSED
✅ Test 11: Google Sheets Rate Limits - PASSED (47 ops/min)

==================================
Results: 11/11 PASSED ✅
Duration: 8 minutes 32 seconds
Coverage: 100%

v3.0 production deployment is STABLE and HEALTHY 🎉
```

---

## Future Enhancements

1. **Frontend E2E:** Add Playwright tests navigating UI (P1 → P6)
2. **Load testing:** Simulate 30 concurrent workers
3. **Chaos testing:** Random operation sequences
4. **v4.0 validation:** Add union-level workflow tests when ready

---

**Last updated:** 2026-02-02
