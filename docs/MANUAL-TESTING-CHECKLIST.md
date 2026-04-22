# ZEUES v4.0 - Manual Testing Checklist

**Version:** v4.0 Uniones System
**Date:** 2026-02-02
**Environment:** Production (Railway + Vercel)
**URLs:**
- Frontend: https://zeues-frontend.vercel.app
- Backend: https://zeues-backend-mvp-production.up.railway.app
- API Docs: https://zeues-backend-mvp-production.up.railway.app/docs

---

## 📋 Testing Strategy

**Order of Testing:**
1. Critical v4.0 Flows (Priority 1) - 2-3 hours
2. v3.0 Backward Compatibility (Priority 2) - 1 hour
3. Real-time & SSE (Priority 3) - 30 min
4. Performance Validation (Priority 4) - 1 hour
5. Edge Cases & Error Handling (Priority 5) - 1 hour

**Testing Data:**
- Use real spools from Google Sheets
- Test worker: MR(93) or any active worker
- Have both v3.0 spools (no unions) and v4.0 spools (with unions) available

---

## 🎯 Priority 1: Critical v4.0 Flows

### Test Case 1.1: INICIAR Workflow (Occupation without Work)

**Preconditions:**
- Worker is logged in
- Spool has unions in Uniones sheet (v4.0 spool)
- Spool is DISPONIBLE (Ocupado_Por = '' or 'DISPONIBLE')

**Steps:**
1. Select worker (e.g., MR(93))
2. Select operation (ARM or SOLD)
3. Click "INICIAR" button
4. Select a v4.0 spool from list
5. Confirm on P6

**Expected Results:**
- ✅ Operaciones.Ocupado_Por = "MR(93)"
- ✅ Operaciones.Fecha_Ocupacion = current timestamp
- ✅ Redis lock created: `spool:{TAG_SPOOL}:lock` = "93"
- ✅ Uniones sheet NOT modified (no ARM/SOLD timestamps written)
- ✅ P7 shows success message
- ✅ Spool disappears from DISPONIBLE dashboard

**Actual Results:**
- [ ] Pass
- [ ] Fail - Details: _____________________

---

### Test Case 1.2: FINALIZAR with Partial Selection (PAUSAR)

**Preconditions:**
- Worker has spool occupied (from Test 1.1)
- Spool has 10 total unions
- Operation: ARM

**Steps:**
1. Select same worker
2. Select same operation (ARM)
3. Click "FINALIZAR" button
4. Select occupied spool (should show in "Ocupados por ti")
5. On P5 union selection page:
   - Verify 10 checkboxes appear
   - Select ONLY 7 unions (not all 10)
   - Verify counter shows "Seleccionadas: 7/10"
   - Verify pulgadas counter shows sum of DN_UNION for selected unions
6. Click "Continuar"
7. Confirm on P6

**Expected Results:**
- ✅ Uniones sheet: 7 unions have ARM_FECHA_INICIO and ARM_FECHA_FIN timestamps
- ✅ Uniones sheet: 7 unions have ARM_WORKER = "MR(93)"
- ✅ Uniones sheet: 3 unions remain with ARM_FECHA_FIN = NULL
- ✅ Operaciones.Uniones_ARM_Completadas = 7
- ✅ Operaciones.Pulgadas_ARM = sum of DN_UNION for 7 unions (1 decimal)
- ✅ Operaciones.Ocupado_Por = "DISPONIBLE" (lock released)
- ✅ Redis lock deleted
- ✅ Metadata logs SPOOL_ARM_PAUSADO event with {uniones_completadas: 7, total: 10, pulgadas: X.X}
- ✅ Metadata logs 7 granular UNION_ARM_REGISTRADA events with N_UNION values
- ✅ P7 shows "Trabajo pausado" message with pulgadas count
- ✅ Auto-determination: System chose PAUSAR (not COMPLETAR) because 7 < 10

**Actual Results:**
- [ ] Pass
- [ ] Fail - Details: _____________________

---

### Test Case 1.3: FINALIZAR with Full Selection (COMPLETAR)

**Preconditions:**
- Spool from Test 1.2 has 3 remaining unions (ARM_FECHA_FIN = NULL)
- Same or different worker can INICIAR

**Steps:**
1. INICIAR the same spool (operation: ARM)
2. FINALIZAR and select the remaining 3 unions
3. Verify counter shows "Seleccionadas: 3/3"
4. Confirm

**Expected Results:**
- ✅ Uniones sheet: All 10 unions now have ARM_FECHA_FIN timestamps
- ✅ Operaciones.Uniones_ARM_Completadas = 10
- ✅ Operaciones.Pulgadas_ARM = sum of all 10 unions
- ✅ Metadata logs SPOOL_ARM_COMPLETADO event (not PAUSADO)
- ✅ Metadata logs 3 granular UNION_ARM_REGISTRADA events
- ✅ P7 shows "Trabajo completado" message
- ✅ Auto-determination: System chose COMPLETAR because 3/3 = 100%
- ✅ Spool status changes to enable SOLD operation

**Actual Results:**
- [ ] Pass
- [ ] Fail - Details: _____________________

---

### Test Case 1.4: ARM → SOLD Prerequisite Validation

**Preconditions:**
- Spool has 0 unions with ARM_FECHA_FIN (no armado work done)

**Steps:**
1. Select worker
2. Select operation: SOLD
3. Try to INICIAR the spool

**Expected Results:**
- ✅ Backend returns 403 Forbidden error
- ✅ Error message: "Cannot start SOLD: at least one union must be armada first"
- ✅ Frontend shows error toast/modal
- ✅ Spool is NOT occupied

**Actual Results:**
- [ ] Pass
- [ ] Fail - Details: _____________________

---

### Test Case 1.5: SOLD Workflow with Partial Completion

**Preconditions:**
- Spool from Test 1.3 has all 10 unions armadas
- None have SOLD work done yet

**Steps:**
1. INICIAR spool with operation: SOLD
2. FINALIZAR and select 6 out of 10 unions
3. Confirm

**Expected Results:**
- ✅ Uniones sheet: 6 unions have SOL_FECHA_INICIO and SOL_FECHA_FIN timestamps
- ✅ Uniones sheet: 6 unions have SOL_WORKER = "MR(93)"
- ✅ Uniones sheet: 4 unions remain with SOL_FECHA_FIN = NULL
- ✅ Operaciones.Uniones_SOLD_Completadas = 6
- ✅ Operaciones.Pulgadas_SOLD = sum of DN_UNION for 6 unions
- ✅ Metadata logs SPOOL_SOLD_PAUSADO event
- ✅ Metadata logs 6 granular UNION_SOLD_REGISTRADA events
- ✅ Auto-determination: PAUSAR (6 < 10)

**Actual Results:**
- [ ] Pass
- [ ] Fail - Details: _____________________

---

### Test Case 1.6: SOLD Complete → Auto Metrología Trigger

**Preconditions:**
- Spool from Test 1.5 has 4 remaining unions to solder

**Steps:**
1. INICIAR spool with operation: SOLD
2. FINALIZAR and select remaining 4 unions (4/4 = 100%)
3. Confirm

**Expected Results:**
- ✅ Operaciones.Uniones_SOLD_Completadas = 10
- ✅ Operaciones.Pulgadas_SOLD = sum of all 10 unions
- ✅ Operaciones.Estado_Detalle = "PENDIENTE_METROLOGIA" or similar
- ✅ Metadata logs SPOOL_SOLD_COMPLETADO event
- ✅ Auto-determination: COMPLETAR (4/4 = 100%)
- ✅ Spool appears in Metrología queue

**Actual Results:**
- [ ] Pass
- [ ] Fail - Details: _____________________

---

### Test Case 1.7: Zero-Union Selection (Cancel with Modal)

**Preconditions:**
- Worker has spool occupied

**Steps:**
1. FINALIZAR occupied spool
2. On P5 union selection page, select 0 unions
3. Click "Continuar"
4. Modal appears: "¿Liberar sin registrar?"
5. Click "Confirmar"

**Expected Results:**
- ✅ Modal shows warning message
- ✅ After confirmation:
  - Operaciones.Ocupado_Por = "DISPONIBLE"
  - Redis lock deleted
  - Metadata logs SPOOL_CANCELADO event with {operacion: "ARM", motivo: "Sin uniones seleccionadas"}
  - NO union timestamps written
  - NO pulgadas updates
- ✅ P7 shows cancellation message
- ✅ Spool returns to DISPONIBLE list

**Actual Results:**
- [ ] Pass
- [ ] Fail - Details: _____________________

---

### Test Case 1.8: Union Selection UI Elements

**Preconditions:**
- Spool has 10 unions, 7 already armadas, 3 pending

**Steps:**
1. INICIAR spool with operation: ARM
2. FINALIZAR and observe P5 page

**Expected Results:**
- ✅ Page shows union table with columns: Checkbox, N_UNION, DN_UNION, TIPO_UNION
- ✅ 7 completed unions show "✓ Armada" badge
- ✅ 7 completed unions have checkboxes DISABLED
- ✅ 3 pending unions have checkboxes ENABLED
- ✅ Live counter updates as you check boxes: "Seleccionadas: 2/3 | Pulgadas: 5.5"
- ✅ Pulgadas counter shows 1 decimal precision
- ✅ Counter is sticky/visible while scrolling (if many unions)

**Actual Results:**
- [ ] Pass
- [ ] Fail - Details: _____________________

---

### Test Case 1.9: Pulgadas Calculation Accuracy

**Preconditions:**
- Spool with unions having specific DN_UNION values
- Example: 3 unions with DN=2.5, 2.5, 3.0 (total = 8.0)

**Steps:**
1. INICIAR spool (ARM)
2. FINALIZAR and select the 3 unions
3. Verify live counter
4. Confirm and check Operaciones sheet

**Expected Results:**
- ✅ Live counter shows: "Pulgadas: 8.0" (correct sum)
- ✅ Operaciones.Pulgadas_ARM = 8.0 (1 decimal precision)
- ✅ Metadata event payload has pulgadas: 8.0
- ✅ No rounding errors (verify with calculator)

**Actual Results:**
- [ ] Pass
- [ ] Fail - Details: _____________________

---

### Test Case 1.10: Dual Workflow Button Display (v3.0 vs v4.0)

**Setup:**
- Have 2 spools:
  - Spool A: v3.0 (no unions in Uniones sheet, count = 0)
  - Spool B: v4.0 (has unions in Uniones sheet, count > 0)

**Steps:**
1. Select worker and operation
2. On P3 (action type page), observe button display

**Expected Results for Spool A (v3.0):**
- ✅ Shows 3 buttons: TOMAR, PAUSAR, COMPLETAR
- ✅ No INICIAR/FINALIZAR buttons visible

**Expected Results for Spool B (v4.0):**
- ✅ Shows 2 buttons: INICIAR, FINALIZAR
- ✅ No TOMAR/PAUSAR/COMPLETAR buttons visible

**Version Detection:**
- ✅ Frontend queries GET /api/v4/uniones/{tag}/disponibles?operacion=ARM
- ✅ If response has unions.length > 0 → v4.0
- ✅ If response has unions.length = 0 → v3.0

**Actual Results:**
- [ ] Pass
- [ ] Fail - Details: _____________________

---

## 🔄 Priority 2: v3.0 Backward Compatibility

### Test Case 2.1: TOMAR v3.0 Spool (3-Button Flow)

**Preconditions:**
- Spool has NO unions in Uniones sheet (v3.0 spool)
- Operation: ARM

**Steps:**
1. Select worker and operation
2. Click "TOMAR" button (not INICIAR)
3. Select v3.0 spool
4. Confirm

**Expected Results:**
- ✅ Operaciones.Ocupado_Por = "MR(93)"
- ✅ Operaciones.Fecha_Ocupacion = timestamp
- ✅ Redis lock created
- ✅ Uses v3.0 endpoint: POST /api/occupation/tomar (NOT /api/v4/occupation/iniciar)
- ✅ No errors about "missing unions"

**Actual Results:**
- [ ] Pass
- [ ] Fail - Details: _____________________

---

### Test Case 2.2: PAUSAR v3.0 Spool

**Preconditions:**
- v3.0 spool is occupied (from Test 2.1)

**Steps:**
1. Click "PAUSAR" button
2. Select occupied spool
3. Confirm

**Expected Results:**
- ✅ Operaciones.Ocupado_Por = "DISPONIBLE"
- ✅ Redis lock deleted
- ✅ Metadata logs SPOOL_ARM_PAUSADO event (old format, no union fields)
- ✅ Uses v3.0 endpoint: POST /api/occupation/pausar
- ✅ No pulgadas fields in metadata

**Actual Results:**
- [ ] Pass
- [ ] Fail - Details: _____________________

---

### Test Case 2.3: COMPLETAR v3.0 Spool

**Preconditions:**
- v3.0 spool is occupied

**Steps:**
1. Click "COMPLETAR" button
2. Select occupied spool
3. Provide fecha_operacion (required)
4. Confirm

**Expected Results:**
- ✅ Operaciones.Fecha_Armado = provided date (for ARM)
- ✅ Operaciones.Armador = "MR(93)"
- ✅ Operaciones.Ocupado_Por = "DISPONIBLE"
- ✅ Redis lock deleted
- ✅ Uses v3.0 endpoint: POST /api/occupation/completar
- ✅ Metadata logs SPOOL_ARM_COMPLETADO event (old format)
- ✅ Estado_Detalle updates correctly

**Actual Results:**
- [ ] Pass
- [ ] Fail - Details: _____________________

---

### Test Case 2.4: Metrología on v3.0 Spool

**Preconditions:**
- v3.0 spool has ARM and SOLD complete

**Steps:**
1. Select Metrología worker
2. Select operation: METROLOGIA
3. Click "COMPLETAR" (instant, no TOMAR)
4. Select spool
5. Choose resultado: APROBADO or RECHAZADO
6. Confirm

**Expected Results:**
- ✅ Instant completion (no occupation, no Redis lock)
- ✅ Metadata logs METROLOGIA_COMPLETADA event with resultado
- ✅ Estado_Detalle updates to "APROBADO" or "RECHAZADO - Ciclo 1/3"
- ✅ Uses v3.0 endpoint: POST /api/metrologia/completar
- ✅ No union-level work required

**Actual Results:**
- [ ] Pass
- [ ] Fail - Details: _____________________

---

### Test Case 2.5: Reparación on v3.0 Spool

**Preconditions:**
- v3.0 spool is RECHAZADO from metrología

**Steps:**
1. Select any worker (no role restriction)
2. Select operation: REPARACION
3. TOMAR spool
4. COMPLETAR spool

**Expected Results:**
- ✅ Spool occupation works (TOMAR/PAUSAR/COMPLETAR flow)
- ✅ After COMPLETAR, Estado_Detalle = "PENDIENTE_METROLOGIA"
- ✅ Spool returns to metrología queue
- ✅ Cycle counter preserved or incremented
- ✅ Uses v3.0 reparación endpoints

**Actual Results:**
- [ ] Pass
- [ ] Fail - Details: _____________________

---

## 🔴 Priority 3: Real-time & SSE Streaming

### Test Case 3.1: SSE Disponible Dashboard Updates

**Setup:**
- Open 2 browser tabs/windows
- Tab 1: Dashboard showing DISPONIBLE spools (ARM operation)
- Tab 2: Worker workflow to TOMAR/INICIAR a spool

**Steps:**
1. In Tab 1, observe initial list of disponible spools
2. In Tab 2, INICIAR one of the visible spools
3. Watch Tab 1 dashboard

**Expected Results:**
- ✅ Tab 1 updates within <10 seconds (SSE event received)
- ✅ Occupied spool disappears from DISPONIBLE list
- ✅ No page refresh required
- ✅ EventSource connection shows in browser DevTools Network tab
- ✅ SSE endpoint: GET /api/sse/disponible?operacion=ARM

**Actual Results:**
- [ ] Pass
- [ ] Fail - Details: _____________________
- Latency measured: _____ seconds

---

### Test Case 3.2: SSE "Quien Tiene Qué" Dashboard

**Setup:**
- Open dashboard showing occupied spools
- Have another worker PAUSAR a spool

**Steps:**
1. Observe dashboard with occupied spools
2. In another session, PAUSAR/FINALIZAR a spool
3. Watch dashboard update

**Expected Results:**
- ✅ Dashboard updates within <10 seconds
- ✅ Released spool disappears from "Quien tiene qué" list
- ✅ SSE endpoint: GET /api/sse/quien-tiene-que

**Actual Results:**
- [ ] Pass
- [ ] Fail - Details: _____________________
- Latency measured: _____ seconds

---

### Test Case 3.3: SSE Reconnection (Mobile Lifecycle)

**Steps:**
1. Open dashboard on mobile/tablet
2. Switch to another app (put browser in background)
3. Wait 30+ seconds
4. Return to browser tab

**Expected Results:**
- ✅ EventSource reconnects automatically
- ✅ Dashboard shows current data (not stale)
- ✅ Exponential backoff works (1s, 2s, 4s... max 30s)
- ✅ Page Visibility API pauses/resumes connection

**Actual Results:**
- [ ] Pass
- [ ] Fail - Details: _____________________

---

## ⚡ Priority 4: Performance Validation

### Test Case 4.1: FINALIZAR Latency (10 Unions)

**Setup:**
- Spool with exactly 10 unions
- All available for selection

**Steps:**
1. INICIAR spool
2. FINALIZAR and select all 10 unions
3. Click "Continuar"
4. Measure time from click to P7 success page

**Expected Results:**
- ✅ p95 latency: < 1 second (target from PERF-01)
- ✅ p99 latency: < 2 seconds (acceptable threshold)
- ✅ No timeout errors
- ✅ Backend makes exactly 2 Google Sheets API calls:
  1. gspread.batch_update() for Uniones + Operaciones metrics
  2. Metadata batch_log_events() for eventos

**Measurement:**
- [ ] Trial 1: _____ ms
- [ ] Trial 2: _____ ms
- [ ] Trial 3: _____ ms
- [ ] Trial 4: _____ ms
- [ ] Trial 5: _____ ms
- [ ] p95: _____ ms (should be < 1000ms)
- [ ] Pass/Fail: _____

---

### Test Case 4.2: Google Sheets Rate Limit Compliance

**Setup:**
- Monitor backend logs for rate limit warnings

**Steps:**
1. Perform 10 FINALIZAR operations in rapid succession
2. Check backend logs and Railway metrics

**Expected Results:**
- ✅ No "Rate limit exceeded" errors from Google Sheets API
- ✅ System stays under 30 writes/min (50% of 60 limit)
- ✅ RateLimitMonitor (if integrated) shows utilization < 50%

**Monitoring:**
- Backend endpoint: GET /api/rate-limit/stats (if available)
- Railway logs: Search for "429" or "rate limit"

**Actual Results:**
- [ ] Pass
- [ ] Fail - Details: _____________________
- Peak writes/min: _____

---

### Test Case 4.3: Batch Metadata Logging (Large Selection)

**Setup:**
- Spool with 20 unions (if available, or use max available)

**Steps:**
1. FINALIZAR and select all 20 unions
2. Check Metadata sheet after completion

**Expected Results:**
- ✅ Metadata has 1 batch event (SPOOL_ARM_COMPLETADO, N_UNION = NULL)
- ✅ Metadata has 20 granular events (UNION_ARM_REGISTRADA, N_UNION = 1-20)
- ✅ Total: 21 rows appended
- ✅ Batch append happens in chunks (900 rows max per chunk)
- ✅ All events have correct timestamps

**Actual Results:**
- [ ] Pass
- [ ] Fail - Details: _____________________

---

### Test Case 4.4: Redis Lock Cleanup (Abandoned Locks)

**Setup:**
- Manually create orphaned Redis lock (simulate crash)

**Steps:**
1. Use Redis CLI or backend script to create lock:
   ```bash
   redis-cli SET "spool:TEST-99:lock" "93"
   ```
2. Ensure Operaciones.Ocupado_Por for TEST-99 is "DISPONIBLE" (mismatch)
3. Wait 24+ hours OR manually trigger cleanup
4. Try to INICIAR TEST-99

**Expected Results:**
- ✅ Lazy cleanup on INICIAR removes orphaned lock (> 24h old)
- ✅ INICIAR succeeds without "Already occupied" error
- ✅ Startup reconciliation also cleans up on app restart

**Actual Results:**
- [ ] Pass
- [ ] Fail - Details: _____________________

---

### Test Case 4.5: Persistent Redis Locks (No TTL)

**Setup:**
- INICIAR a spool and leave occupied for 5+ hours

**Steps:**
1. INICIAR spool at 9:00 AM
2. Do NOT FINALIZAR
3. Check Redis lock at 2:00 PM (5 hours later)

**Expected Results:**
- ✅ Redis lock still exists (no TTL expiration)
- ✅ Operaciones.Ocupado_Por still shows worker
- ✅ Worker can FINALIZAR successfully after 5+ hours
- ✅ Supports real-world 5-8 hour work sessions

**Actual Results:**
- [ ] Pass
- [ ] Fail - Details: _____________________

---

## 🐛 Priority 5: Edge Cases & Error Handling

### Test Case 5.1: Concurrent INICIAR (Race Condition)

**Setup:**
- 2 workers try to INICIAR same spool simultaneously

**Steps:**
1. Open 2 browser sessions (Worker A, Worker B)
2. Both select same spool
3. Click INICIAR at the exact same time (within 100ms)

**Expected Results:**
- ✅ Only 1 worker succeeds (Redis SETNX atomic operation)
- ✅ Other worker gets 409 Conflict error
- ✅ Error message: "Spool already occupied by another worker"
- ✅ No data corruption in Sheets

**Actual Results:**
- [ ] Pass
- [ ] Fail - Details: _____________________

---

### Test Case 5.2: Optimistic Locking (Version Conflict)

**Setup:**
- 2 workers occupy same spool sequentially
- Simulate version mismatch

**Steps:**
1. Worker A: INICIAR spool (gets version UUID v1)
2. Worker A: PAUSAR (updates version to v2)
3. Manually change Operaciones.version in Sheets to v3
4. Worker B: INICIAR same spool (gets version v3)
5. Worker B: Try to FINALIZAR (should retry with new version)

**Expected Results:**
- ✅ System detects version mismatch
- ✅ Retries up to 3 times with exponential backoff
- ✅ If retry succeeds, operation completes
- ✅ If retry fails, returns 409 Conflict error

**Actual Results:**
- [ ] Pass
- [ ] Fail - Details: _____________________

---

### Test Case 5.3: Missing Uniones Data (v4.0 Spool with Empty Unions)

**Setup:**
- Spool marked as v4.0 but Uniones sheet has NO rows for TAG_SPOOL

**Steps:**
1. Try to INICIAR this spool
2. Try to FINALIZAR

**Expected Results:**
- ✅ INICIAR succeeds (occupation only, doesn't touch Uniones)
- ✅ FINALIZAR fails gracefully with error: "No unions found for this spool"
- ✅ Frontend shows error toast
- ✅ No crash or 500 error

**Actual Results:**
- [ ] Pass
- [ ] Fail - Details: _____________________

---

### Test Case 5.4: Invalid Union Selection (Backend Validation)

**Setup:**
- Spool with 10 unions, 7 armadas

**Steps:**
1. INICIAR spool for SOLD operation
2. In P5, manually modify frontend state to include union with ARM_FECHA_FIN = NULL
3. Submit selection to backend

**Expected Results:**
- ✅ Backend validates ARM prerequisite for SOLD
- ✅ Returns 400 Bad Request error
- ✅ Error message: "Cannot select union N for SOLD: not armada yet"
- ✅ No partial data written

**Actual Results:**
- [ ] Pass
- [ ] Fail - Details: _____________________

---

### Test Case 5.5: Network Timeout (Slow Sheets API)

**Setup:**
- Simulate slow Google Sheets response (if possible via throttling)

**Steps:**
1. FINALIZAR with 10 unions
2. Introduce network latency (Chrome DevTools → Network → Throttling)

**Expected Results:**
- ✅ Frontend shows loading spinner
- ✅ Operation completes successfully (with delay)
- ✅ No timeout error if < 30 seconds
- ✅ If > 30 seconds, graceful timeout error message

**Actual Results:**
- [ ] Pass
- [ ] Fail - Details: _____________________

---

### Test Case 5.6: Ownership Validation (FINALIZAR Wrong Worker)

**Steps:**
1. Worker A: INICIAR spool
2. Worker B: Try to FINALIZAR same spool (different worker_id)

**Expected Results:**
- ✅ Backend returns 403 Forbidden error
- ✅ Error message: "Worker does not own this spool"
- ✅ Redis lock unchanged
- ✅ No data written

**Actual Results:**
- [ ] Pass
- [ ] Fail - Details: _____________________

---

### Test Case 5.7: Startup Schema Validation

**Steps:**
1. Restart backend (Railway or local)
2. Check startup logs

**Expected Results:**
- ✅ Schema validation runs at startup
- ✅ Validates Operaciones (72 columns), Metadata (11 columns), Uniones (18 columns)
- ✅ If columns missing, logs ERROR and deployment fails
- ✅ If extra columns exist, logs WARNING but continues
- ✅ Logs show: "Schema validation: PASSED"

**Actual Results:**
- [ ] Pass
- [ ] Fail - Details: _____________________

---

## 📊 Testing Summary Template

**Tested by:** _____________________
**Date:** _____________________
**Environment:** Production / Staging / Local

**Overall Results:**

| Priority | Test Cases | Passed | Failed | Blocked |
|----------|-----------|--------|--------|---------|
| 1 - Critical v4.0 Flows | 10 | ___ | ___ | ___ |
| 2 - v3.0 Compatibility | 5 | ___ | ___ | ___ |
| 3 - Real-time & SSE | 3 | ___ | ___ | ___ |
| 4 - Performance | 5 | ___ | ___ | ___ |
| 5 - Edge Cases | 7 | ___ | ___ | ___ |
| **TOTAL** | **30** | ___ | ___ | ___ |

**Pass Rate:** _____ % (target: > 90%)

---

## 🐛 Bugs Found

List all bugs discovered during testing:

### Bug #1: [Title]
- **Severity:** Critical / High / Medium / Low
- **Test Case:** _____
- **Steps to Reproduce:**
  1. _____
  2. _____
- **Expected:** _____
- **Actual:** _____
- **Screenshots/Logs:** _____
- **Fix with:** `/gsd:debug "[description]"`

---

### Bug #2: [Title]
...

---

## 🎯 Post-Testing Actions

After completing all tests:

1. **If > 5 critical bugs found:**
   ```bash
   /gsd:insert-phase 13 "Critical v4.0 Bug Fixes - Production Validation"
   ```

2. **For individual bugs:**
   ```bash
   /gsd:debug "[bug description]"
   ```

3. **For quick fixes:**
   ```bash
   /gsd:quick "Fix: [specific issue]"
   ```

4. **When stable:**
   - Monitor production for 1 week
   - Gather user feedback
   - Plan v4.1 milestone with new features

---

## 📚 Reference

**Key Files:**
- v4.0 Milestone Audit: `docs/archive/milestones/v4.0-MILESTONE-AUDIT.md`
- (v4.0 requirements / roadmap were retired with the `.planning/` cleanup in Apr 2026; the audit is the surviving reference.)

**API Docs:** https://zeues-backend-mvp-production.up.railway.app/docs

**Google Sheets Structure:**
- Operaciones: 72 columns (68-72 are v4.0 metrics)
- Uniones: 18 columns
- Metadata: 11 columns (position 11 is N_UNION)

---

**Version:** 1.0
**Last Updated:** 2026-02-02
**Status:** Ready for production testing
