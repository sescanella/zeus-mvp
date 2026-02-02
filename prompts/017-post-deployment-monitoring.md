<objective>
Perform comprehensive post-deployment monitoring and verification after the Redis Crisis recovery deployment.

**Context:** All 3 phases of the Redis Crisis recovery have been deployed to production:
- Phase 1: Root cause identified (Redis pool exhaustion)
- Phase 2: Connection pooling implemented (max=20 connections)
- Phase 3: Test suite fixed + CompletarRequest model bug fixed

**Your mission:** Verify the deployment is successful, monitor production for 2 hours, run full E2E test suite, and confirm all issues are resolved.
</objective>

<context>
**Deployed Commits:**
- `ac0502b` - Phase 2: Redis connection pooling
- `b5acfc9` - Phase 3: E2E test schema fixes
- `f0ec7b5` - Phase 3: CompletarRequest model fix + documentation

**Expected Improvements:**
1. Redis health: "healthy" (was "unhealthy")
2. Connection pool: <20 active connections (was exhausted)
3. COMPLETAR operations: 200 OK (was 500 error)
4. E2E tests: 8/8 passing (was 3/8)

**Reference Documents:**
@PHASE1-REDIS-EMERGENCY-REPORT.md
@PHASE2-REDIS-POOLING-REPORT.md
@PHASE3-TEST-SUITE-DOCS-REPORT.md
@INCIDENT-POSTMORTEM-REDIS-CRISIS.md
</context>

<requirements>

## Task 1: Verify Railway Deployment Status

**Check Railway Dashboard:**
1. Navigate to: https://railway.app
2. Find ZEUES Production project
3. Verify latest deployment shows "Success" or "Deployed"
4. Check deployment logs for errors

**If deployment failed:**
- Document error messages
- Check build logs
- Determine if rollback needed
- Report findings immediately

**If deployment succeeded:**
- Note deployment timestamp
- Proceed to health checks

---

## Task 2: Production Health Checks

**Execute these checks immediately after deployment:**

### Check 1: Overall System Health

```bash
curl https://zeues-backend-mvp-production.up.railway.app/api/health
```

**Expected Response:**
```json
{
  "status": "healthy",
  "operational": true,
  "sheets_connection": "ok",
  "redis_connection": "ok",
  "timestamp": "2026-02-02T...",
  "details": {
    "redis_error": null,
    "redis_pool_stats": {
      "max_connections": 20,
      "active_connections": 2,
      "available_connections": 18,
      "utilization_percent": 10.0
    }
  }
}
```

**Verification:**
- ✅ `status` = "healthy" (not "unhealthy" or "degraded")
- ✅ `operational` = true
- ✅ `redis_connection` = "ok"
- ✅ `active_connections` < 20
- ✅ `utilization_percent` < 80%

**If unhealthy:**
- Document exact response
- Check Redis logs in Railway
- May need to restart Redis service
- Investigate before proceeding

---

### Check 2: Redis Connection Pool Statistics

```bash
curl https://zeues-backend-mvp-production.up.railway.app/api/redis-connection-stats
```

**Expected Response:**
```json
{
  "max_connections": 20,
  "active_connections": 3,
  "available_connections": 17,
  "utilization_percent": 15.0,
  "alert": null,
  "timestamp": "2026-02-02T..."
}
```

**Verification:**
- ✅ `max_connections` = 20 (Phase 2 fix applied)
- ✅ `active_connections` < 15 (healthy utilization)
- ✅ `utilization_percent` < 80% (no alert)
- ✅ `alert` = null (no high utilization warning)

**Red flags:**
- ❌ `max_connections` ≠ 20 → Phase 2 not deployed
- ❌ `utilization_percent` > 80% → Still exhausting pool
- ❌ `alert` = "HIGH_UTILIZATION" → Monitor closely

---

### Check 3: TOMAR Operation (Baseline)

```bash
curl -X POST https://zeues-backend-mvp-production.up.railway.app/api/occupation/tomar \
  -H "Content-Type: application/json" \
  -d '{
    "tag_spool": "TEST-02",
    "worker_id": 93,
    "worker_nombre": "MR(93)",
    "operacion": "ARM"
  }'
```

**Expected Response:**
```json
{
  "message": "Spool TEST-02 ocupado por MR(93) para ARM",
  "tag_spool": "TEST-02",
  "worker_nombre": "MR(93)",
  "operacion": "ARM"
}
```

**Verification:**
- ✅ Status code: 200 OK (or 409 if already occupied)
- ✅ No 500 Internal Server Error
- ✅ Response has `message` field

**Note:** 409 Conflict is acceptable if spool already occupied. What matters is NO 500 errors.

---

### Check 4: COMPLETAR Operation (Critical Fix)

**This is the key test for the CompletarRequest model bug fix.**

```bash
curl -X POST https://zeues-backend-mvp-production.up.railway.app/api/occupation/completar \
  -H "Content-Type: application/json" \
  -d '{
    "tag_spool": "TEST-02",
    "worker_id": 93,
    "worker_nombre": "MR(93)",
    "operacion": "ARM",
    "fecha_operacion": "2026-02-02"
  }'
```

**Expected Response (if worker owns spool):**
```json
{
  "message": "ARM completado para TEST-02",
  "tag_spool": "TEST-02",
  "estado": "ARM_Completado"
}
```

**Expected Response (if worker doesn't own spool):**
```json
{
  "detail": "Worker 93 no es el ocupante actual de TEST-02"
}
```

**Verification:**
- ✅ Status code: 200 OK or 403 Forbidden (both acceptable)
- ❌ Status code: 500 → **Model bug NOT fixed**
- ❌ Error: "'CompletarRequest' object has no attribute 'operacion'" → **Deployment failed**

**If 500 error:**
- CRITICAL: Model fix not deployed
- Check git log on production
- May need to redeploy or rollback

---

### Check 5: Workers API (Baseline)

```bash
curl https://zeues-backend-mvp-production.up.railway.app/api/workers
```

**Expected Response:**
```json
{
  "workers": [
    {"id": 93, "nombre": "MR", "apellido": "...", "activo": true},
    ...
  ]
}
```

**Verification:**
- ✅ Status code: 200 OK
- ✅ Returns list of workers
- ✅ No errors

---

## Task 3: Run Full E2E Test Suite

**Execute the complete production E2E test suite:**

```bash
cd /Users/sescanella/Proyectos/KM/ZEUES-by-KM
source venv/bin/activate
python test_production_v3_e2e_simple.py
```

**Expected Output:**
```
============================================================
ZEUES v3.0 Production E2E Tests (Simplified)
============================================================
Environment: https://zeues-backend-mvp-production.up.railway.app
Test Spool: TEST-02
Timestamp: 2026-02-02T...

Pre-check: Verifying Redis health...
✅ Redis health check passed

============================================================
Test 1: ARM TOMAR → PAUSAR → COMPLETAR
============================================================
   MR(93) TOMAR ARM...
✅ TOMAR succeeded
   MR(93) PAUSAR ARM...
✅ PAUSAR succeeded
   MR(93) TOMAR ARM again...
✅ TOMAR succeeded
   MR(93) COMPLETAR ARM...
✅ COMPLETAR succeeded: ARM completado para TEST-02
✅ Test 1 PASSED

[... Tests 2-8 ...]

============================================================
Test Results Summary
============================================================
Total Tests: 8
Passed: 8/8 ✅
Failed: 0/8
Duration: ~30 seconds

v3.0 production deployment is STABLE ✅ (100% success rate)
```

**Verification:**
- ✅ All 8 tests pass (100% success rate)
- ✅ Redis health pre-check passes
- ✅ No 500 errors
- ✅ No 422 validation errors on COMPLETAR
- ✅ Test duration < 60 seconds

**Baseline Comparison:**

| Phase | Tests Passing | Success Rate | Status |
|-------|---------------|--------------|--------|
| Pre-crisis | 8/8 | 100% | ✅ Normal |
| Phase 1 (Crisis) | 3/8 | 38% | ❌ Redis down |
| **Post-deployment** | **8/8** | **100%** | ✅ **RESOLVED** |

**If tests fail:**
- Document which tests failed
- Capture error messages
- Check if Redis health passed
- Determine if rollback needed

---

## Task 4: 2-Hour Monitoring Period

**Monitor production continuously for 2 hours after deployment.**

### What to Monitor

**1. Railway Redis Metrics**
- Go to: Railway Dashboard → Redis service → Metrics
- Watch: Connected clients graph
- Alert if: Connections approach 20

**Sample every 15 minutes:**

| Time | Active Connections | Utilization % | Status |
|------|-------------------|---------------|--------|
| T+0min | [X] | [Y]% | [OK/HIGH] |
| T+15min | [X] | [Y]% | [OK/HIGH] |
| T+30min | [X] | [Y]% | [OK/HIGH] |
| T+45min | [X] | [Y]% | [OK/HIGH] |
| T+60min | [X] | [Y]% | [OK/HIGH] |
| T+75min | [X] | [Y]% | [OK/HIGH] |
| T+90min | [X] | [Y]% | [OK/HIGH] |
| T+105min | [X] | [Y]% | [OK/HIGH] |
| T+120min | [X] | [Y]% | [OK/HIGH] |

**Health check every 15 minutes:**
```bash
# Save as monitor.sh
#!/bin/bash
for i in {1..8}; do
  echo "=== Check $i ($(date)) ==="
  curl -s https://zeues-backend-mvp-production.up.railway.app/api/redis-connection-stats | jq
  sleep 900  # 15 minutes
done
```

**2. Railway Backend Logs**
- Go to: Railway Dashboard → Backend service → Logs
- Watch for: Errors, warnings, "Too many connections"
- Filter: Last 2 hours

**Log patterns to watch for:**
- ✅ "Redis pool initialized with max_connections=20"
- ✅ "TOMAR operation: Redis pool at X% capacity"
- ❌ "Too many connections"
- ❌ "Redis not responding"
- ❌ "'CompletarRequest' object has no attribute 'operacion'"

**3. Error Rate Monitoring**
If you have access to error tracking (Sentry, etc.):
- Monitor 500 error rate
- Should be ZERO after deployment
- Alert if any 500 errors occur

**4. API Response Times**
Monitor endpoint latency:
```bash
# Test TOMAR response time
time curl -X POST .../api/occupation/tomar -d '{...}'
# Should be < 2 seconds
```

---

## Task 5: Post-Monitoring Report

**After 2-hour monitoring period, generate report:**

`./POST-DEPLOYMENT-MONITORING-REPORT.md`

**Report Structure:**

```markdown
# Post-Deployment Monitoring Report - Redis Crisis Recovery

**Deployment Date:** 2026-02-02
**Monitoring Period:** 2 hours (T+0 to T+120min)
**Status:** [STABLE / UNSTABLE / ISSUES DETECTED]

---

## Deployment Verification

### Railway Deployment
- Deployment timestamp: [timestamp]
- Build status: [SUCCESS/FAILED]
- Commits deployed:
  - ac0502b (Phase 2: Connection pooling)
  - b5acfc9 (Phase 3: Test fixes)
  - f0ec7b5 (Phase 3: Model fix)

### Health Checks (T+0)

**System Health:**
```json
[paste /api/health response]
```
Status: ✅ HEALTHY / ❌ UNHEALTHY

**Connection Pool:**
```json
[paste /api/redis-connection-stats response]
```
Status: ✅ OPTIMAL / ⚠️ HIGH / ❌ EXHAUSTED

**TOMAR Test:** [200 OK / ERROR]
**COMPLETAR Test:** [200 OK / 403 / 500 ERROR]

---

## E2E Test Results

**Execution:** [timestamp]
**Success Rate:** X/8 ([Y]%)

| Test | Status | Notes |
|------|--------|-------|
| 1. ARM Flow | [PASS/FAIL] | [notes] |
| 2. Race Condition | [PASS/FAIL] | [notes] |
| 3. Invalid PAUSAR | [PASS/FAIL] | [notes] |
| 4. Nonexistent Spool | [PASS/FAIL] | [notes] |
| 5. History | [PASS/FAIL] | [notes] |
| 6. Health Check | [PASS/FAIL] | [notes] |
| 7. SOLD Flow | [PASS/FAIL] | [notes] |
| 8. Metrología | [PASS/FAIL] | [notes] |

**Comparison with Baseline:**
- Pre-crisis: 8/8 (100%)
- During crisis: 3/8 (38%)
- Post-deployment: X/8 ([Y]%)

---

## 2-Hour Monitoring Results

### Redis Connection Pool Utilization

[Table of connection stats every 15 min]

**Statistics:**
- Average active connections: [X]
- Peak active connections: [Y]
- Average utilization: [Z]%
- Peak utilization: [W]%

**Alerts:**
- High utilization warnings: [0 / X occurrences]
- Connection exhaustion: [0 / X occurrences]

### Backend Error Logs

**Errors detected:** [0 / X errors]

[If errors occurred, list them:]
- [timestamp]: [error message]
- [timestamp]: [error message]

**"Too many connections" errors:** [0 / X occurrences]

### API Performance

**Response times sampled:**
- TOMAR endpoint: [X]ms average
- COMPLETAR endpoint: [Y]ms average
- Health check: [Z]ms average

**All < 2 seconds:** [YES / NO]

---

## Issues Detected

[If any issues found, document here:]

### Issue 1: [Title]
- **Severity:** [P0/P1/P2]
- **Description:** [details]
- **Impact:** [production impact]
- **Action taken:** [immediate action]

[If no issues:]
**No issues detected during monitoring period.** ✅

---

## Comparison with Crisis Baseline

| Metric | Pre-Crisis | During Crisis | Post-Deployment |
|--------|------------|---------------|-----------------|
| Redis Status | Healthy | Unhealthy | [Healthy/Unhealthy] |
| Active Connections | 5-10 | 20+ (exhausted) | [X] |
| TOMAR Success Rate | 100% | 0% (500 error) | [Y]% |
| COMPLETAR Success Rate | 100% | 0% (500 error) | [Z]% |
| E2E Test Success | 100% | 38% | [W]% |

---

## Success Criteria Verification

| Criterion | Target | Actual | Status |
|-----------|--------|--------|--------|
| Redis health | "healthy" | [status] | [✅/❌] |
| Connection pool | <20 active | [X] | [✅/❌] |
| Pool utilization | <80% | [Y]% | [✅/❌] |
| Zero 500 errors | 0 errors | [Z] | [✅/❌] |
| E2E tests | 8/8 passing | [W]/8 | [✅/❌] |
| 2-hour stability | No "Too many connections" | [occurrences] | [✅/❌] |

**All criteria met:** [YES / NO]

---

## Recommendations

### Immediate Actions

[If all green:]
- ✅ Deployment successful
- ✅ Continue normal operations
- ✅ Monitor for 24 more hours
- ✅ Schedule post-incident review

[If issues detected:]
- [ ] Investigate [issue]
- [ ] Consider rollback if critical
- [ ] Extend monitoring period
- [ ] Alert stakeholders

### Follow-up Actions (Next 24 Hours)

1. **Archive Incident Reports**
   ```bash
   mkdir -p .planning/incidents/2026-02-02-redis-crisis
   mv PHASE*.md INCIDENT*.md .planning/incidents/2026-02-02-redis-crisis/
   ```

2. **Stakeholder Communication**
   - Email incident postmortem to team
   - Schedule post-incident review (48 hours)
   - Share lessons learned

3. **Extended Monitoring**
   - Continue monitoring for 24 hours
   - Track E2E test success rate
   - Watch for any regression

### Medium-term (Next Week)

4. **Review Postmortem**
   - Read `INCIDENT-POSTMORTEM-REDIS-CRISIS.md`
   - Identify v4.0 improvements
   - Plan observability milestone

5. **Implement Quick Wins**
   - Add load testing framework
   - Set up Prometheus metrics
   - Create monitoring dashboard

---

## Conclusion

[2-3 paragraph summary of monitoring results and deployment status]

**Overall Assessment:** [STABLE / NEEDS ATTENTION / CRITICAL ISSUES]

**Ready for Normal Operations:** [YES / NO]

---

**Report Generated:** [timestamp]
**Next Review:** [24 hours after deployment]
**Status:** [COMPLETE / ONGOING]
```

</output>

<verification>

Before completing, verify:
1. Railway deployment status checked
2. All 5 health checks executed and documented
3. E2E test suite run and results captured
4. 2-hour monitoring period completed (or in progress)
5. Connection pool stats sampled every 15 minutes
6. Backend logs reviewed for errors
7. Post-monitoring report generated
8. Success criteria verified
9. Recommendations provided

</verification>

<success_criteria>

Monitoring complete when:
✅ Railway deployment verified successful
✅ All health checks pass (Redis, TOMAR, COMPLETAR, etc.)
✅ E2E test suite passes 8/8 (100%)
✅ 2-hour monitoring period completed
✅ Zero "Too many connections" errors during monitoring
✅ Connection pool utilization stays <80%
✅ Post-monitoring report generated
✅ Success criteria verified (all green)

**Deployment status:** STABLE (all criteria met)

</success_criteria>

<important_notes>

**Why 2-hour monitoring is critical:**

Even though Phase 2 fixed the connection pool configuration, we need to verify the fix holds under production load. Connection leaks or configuration issues may not appear immediately but will manifest over time (1-2 hours).

**What to do if issues detected:**

1. **Minor issues (utilization 70-80%):**
   - Continue monitoring
   - Reduce `max_connections` to 15 if needed
   - Extend monitoring to 4 hours

2. **Major issues (exhaustion, 500 errors):**
   - Investigate immediately
   - Check if Phase 2 code deployed correctly
   - Consider rollback to previous version
   - Alert stakeholders

3. **Critical issues (production down):**
   - Immediate rollback via Railway
   - Notify stakeholders
   - Activate incident response
   - Schedule emergency debugging session

**Success indicators:**

- ✅ Flat connection count (no growth over 2 hours)
- ✅ Stable utilization (stays within ±10%)
- ✅ Zero errors in logs
- ✅ Consistent E2E test success (run multiple times)

</important_notes>
