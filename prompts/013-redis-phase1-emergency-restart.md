<objective>
Execute Phase 1 of the Redis Crisis Recovery Plan: Emergency Redis restart and production validation testing.

**Context:** Production E2E tests on 2026-02-02 revealed critical Redis connection failure ("Too many connections"). Only 3/8 tests passed (37.5%). All occupation features (TOMAR/PAUSAR/COMPLETAR) are non-functional. The 7-day rollback window expires TODAY (2026-02-02).

**Critical Status:**
- Redis: UNHEALTHY (too many connections)
- Google Sheets: OPERATIONAL
- Occupation features: DOWN (500 errors)
- SSE Streaming: NOT WORKING
- Rollback deadline: TODAY

This is a **P0 Critical Production Outage**. Your mission is to restore production service immediately.
</objective>

<context>
**Production Environment:**
- Backend API: https://zeues-backend-mvp-production.up.railway.app
- Redis: Railway-hosted Redis service
- Test spool: TEST-02

**Baseline Test Results (2026-02-02 08:12:17):**
- 3/8 tests PASSED (37.5% success rate)
- 5/8 tests FAILED due to Redis connection error
- See: `/test-results/production-e2e-simple-20260202_081217.md`

**Reference Documents:**
@/E2E-TEST-INDEX.md
@/PRODUCTION-E2E-SUMMARY.md
@/REDIS-FIX-CHECKLIST.md
@/test_production_v3_e2e_simple.py
</context>

<requirements>

**Step 1: Provide Railway Redis Restart Instructions**

Since you cannot directly access Railway Dashboard, provide clear, step-by-step instructions for the user to restart the Redis service:

1. Explain how to navigate to Railway Dashboard
2. How to locate the Redis service in the ZEUES Production project
3. How to click the "Restart" button
4. What status to wait for ("Running")
5. Typical restart time (30-60 seconds)

Format these instructions clearly for a DevOps engineer to follow.

**Step 2: Verify Redis Health**

After user confirms restart, verify Redis health:

```bash
curl https://zeues-backend-mvp-production.up.railway.app/api/redis-health
```

**Expected response:**
```json
{
  "status": "healthy",
  "operational": true
}
```

If unhealthy, instruct user to wait 2 minutes and retry. Attempt up to 3 times.

**Step 3: Test Basic Occupation Operations**

Test TOMAR operation to verify Redis is functioning:

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

**Expected:** 200 OK response (not 500 Internal Server Error)

Document the actual response received.

**Step 4: Re-run Full E2E Test Suite**

Execute the production E2E test suite:

```bash
cd /Users/sescanella/Proyectos/KM/ZEUES-by-KM
source venv/bin/activate
python test_production_v3_e2e_simple.py
```

**Expected Results:**
- At least 6/8 tests should pass (75%+ success rate) after Redis fix
- Compare with baseline: 3/8 passed before fix

The test suite will automatically:
- Generate a new timestamped report in `./test-results/`
- Display colored terminal output with pass/fail status
- Calculate success rate

**Step 5: Rollback Decision Point**

Based on test results, make a clear recommendation:

**IF Redis is healthy AND tests pass ≥6/8 (75%+):**
→ **CONTINUE with v3.0**
→ Proceed to Phase 2 (connection pooling fixes)
→ Document: "Redis crisis resolved via restart. Phase 1 SUCCESS."

**IF Redis is unhealthy OR tests pass <6/8:**
→ **PREPARE ROLLBACK to v2.1**
→ Explain rollback steps:
  1. Notify users of planned 30-min downtime
  2. Deploy v2.1 git tag: `git checkout v2.1 && git push production main --force`
  3. Verify v2.1 operational via health check
  4. Document: "Redis unfixable within rollback window. Rolled back to v2.1."

**IF results are borderline (exactly 6/8):**
→ **HOLD and MONITOR**
→ Recommend 1-hour production monitoring before proceeding
→ Watch Railway logs for "Too many connections" errors
→ Re-run E2E tests after 1 hour to confirm stability

</requirements>

<output>

Generate a comprehensive Phase 1 Report and save to:

`./PHASE1-REDIS-EMERGENCY-REPORT.md`

**Report Structure:**

```markdown
# ZEUES v3.0 Redis Crisis - Phase 1 Emergency Report

**Date:** [timestamp]
**Executed by:** Claude Code
**Duration:** [X minutes]

---

## 1. Redis Restart Status

**Railway Redis Service:**
- Status before restart: [DOWN/Too many connections]
- Restart performed: [timestamp]
- Status after restart: [HEALTHY/UNHEALTHY]
- Restart successful: [YES/NO]

**Redis Health Check:**
```json
[paste curl response]
```

---

## 2. Basic Operations Test

**TOMAR Operation Test:**
- Endpoint: POST /api/occupation/tomar
- Test spool: TEST-02
- Worker: MR(93)
- Response status: [200/500/other]
- Response body:
```json
[paste response]
```

**Verdict:** [SUCCESS/FAILED]

---

## 3. E2E Test Results Comparison

**Baseline (Before Fix):**
- Date: 2026-02-02 08:12:17
- Passed: 3/8 (37.5%)
- Failed: 5/8
- Status: UNSTABLE

**After Redis Restart:**
- Date: [timestamp]
- Passed: X/8 (Y%)
- Failed: Z/8
- Status: [STABLE/UNSTABLE/DEGRADED]

**Test-by-Test Comparison:**

| Test | Before | After | Status |
|------|--------|-------|--------|
| 1. ARM TOMAR → PAUSAR → COMPLETAR | FAILED | [PASSED/FAILED] | [FIXED/STILL BROKEN] |
| 2. Race Condition | FAILED | [PASSED/FAILED] | [FIXED/STILL BROKEN] |
| 3. Invalid PAUSAR | PASSED | [PASSED/FAILED] | [MAINTAINED/REGRESSED] |
| 4. Nonexistent Spool | PASSED | [PASSED/FAILED] | [MAINTAINED/REGRESSED] |
| 5. History Endpoint | FAILED | [PASSED/FAILED] | [FIXED/STILL BROKEN] |
| 6. Health Check | PASSED | [PASSED/FAILED] | [MAINTAINED/REGRESSED] |
| 7. SOLD Flow | FAILED | [PASSED/FAILED] | [FIXED/STILL BROKEN] |
| 8. Metrología Instant | FAILED | [PASSED/FAILED] | [FIXED/STILL BROKEN] |

**Improvement:** +[X] tests fixed ([Y]% improvement)

**Generated Report:** [path to new test report]

---

## 4. Rollback Decision

**Decision:** [CONTINUE v3.0 / ROLLBACK to v2.1 / HOLD and MONITOR]

**Justification:**
[Explain the decision based on test results and Redis health]

**Reasoning:**
- Redis health: [HEALTHY/UNHEALTHY]
- Test success rate: [X%]
- Threshold met: [YES/NO] (≥75% needed)
- Production risk: [LOW/MEDIUM/HIGH]

**IF CONTINUE:**
- ✅ Redis connection crisis resolved
- ✅ Test success rate meets threshold (≥75%)
- ✅ Ready to proceed to Phase 2 (connection pooling)
- ⚠️ Monitor production for 2 hours for any Redis errors

**IF ROLLBACK:**
- ❌ Redis remains unstable after restart
- ❌ Test success rate below threshold (<75%)
- ❌ Cannot fix within rollback window (expires today)
- 🔄 Rollback steps: [list specific git commands]

**IF HOLD:**
- ⚠️ Results borderline (exactly 75% or minor issues)
- 🕐 Monitor production for 1 hour
- 🔁 Re-run E2E tests after monitoring period
- 📊 Check Railway Redis connection metrics

---

## 5. Next Steps

**Immediate (Next 2 hours):**
- [Action items based on decision]

**Phase 2 Prerequisites (if continuing):**
- [ ] Redis healthy for 2+ hours without errors
- [ ] E2E tests remain ≥75% success rate
- [ ] Railway Redis connection count monitored
- [ ] Production logs show no "Too many connections"

**Phase 2 Ready:** [YES/NO/PENDING]

---

## 6. Supporting Evidence

**Screenshots/Logs:**
- Redis health check: [paste curl output]
- TOMAR test response: [paste curl output]
- E2E test terminal output: [paste summary]
- Railway Redis metrics: [describe status if available]

**Timestamp Log:**
- Redis restart requested: [time]
- Redis health verified: [time]
- TOMAR test executed: [time]
- E2E tests started: [time]
- E2E tests completed: [time]
- Report generated: [time]

---

## Conclusion

[1-2 paragraph summary of Phase 1 outcome and recommendation for Phase 2]

---

**Phase 1 Status:** [SUCCESS / PARTIAL SUCCESS / FAILED]
**Ready for Phase 2:** [YES / NO]
**Report generated:** [timestamp]
```

</output>

<verification>

Before declaring Phase 1 complete, verify:

1. **Redis restart instructions provided** - Clear, step-by-step guidance given
2. **Redis health check executed** - Curl command run, response documented
3. **TOMAR operation tested** - Basic occupation test performed, result recorded
4. **E2E test suite executed** - Full test suite run, results captured
5. **Comparison completed** - Before (3/8) vs After (X/8) clearly documented
6. **Decision made** - Clear CONTINUE/ROLLBACK/HOLD decision with justification
7. **Report saved** - `./PHASE1-REDIS-EMERGENCY-REPORT.md` created with all data
8. **Next steps defined** - Clear actions for next 2 hours and Phase 2 readiness

**Critical verification questions:**
- Is Redis health endpoint returning "healthy"?
- Did test success rate improve from 37.5% baseline?
- Did we meet ≥75% threshold (6/8 tests)?
- Is the rollback decision clearly justified?
- Are Phase 2 prerequisites listed?

</verification>

<success_criteria>

**Phase 1 is complete when:**

✅ Redis restart instructions provided and user confirmed restart
✅ Redis health endpoint returns `{"status": "healthy", "operational": true}`
✅ TOMAR operation returns 200 OK (not 500 error)
✅ E2E test suite executed successfully
✅ Test results show improvement from 3/8 baseline
✅ Clear CONTINUE/ROLLBACK/HOLD decision made with justification
✅ Phase 1 report generated and saved to `./PHASE1-REDIS-EMERGENCY-REPORT.md`
✅ Next steps clearly defined

**Minimum success threshold:**
- Redis: HEALTHY
- E2E Tests: ≥6/8 PASSED (75%+)
- Decision: CONTINUE to Phase 2

**Failure threshold (triggers rollback):**
- Redis: UNHEALTHY after 3 restart attempts
- E2E Tests: <6/8 PASSED (<75%)
- Decision: ROLLBACK to v2.1

</success_criteria>

<constraints>

**Time Constraints:**
- Rollback window expires TODAY (2026-02-02)
- Phase 1 must complete within 2 hours of starting
- Redis restart typically takes 1-2 minutes
- E2E test suite runs in ~30 seconds

**Resource Constraints:**
- Cannot directly access Railway Dashboard (provide instructions for user)
- Must use production API endpoints (no direct Redis access)
- Test spool TEST-02 must be available in production Sheets

**Decision Constraints:**
- MUST make CONTINUE/ROLLBACK/HOLD decision - no ambiguity
- CANNOT proceed to Phase 2 unless test success rate ≥75%
- MUST recommend rollback if Redis unfixable within window

</constraints>

<important_notes>

**Why this matters:**
This is a critical production outage affecting all manufacturing floor operations. Workers cannot track spool progress, which halts production. Quick resolution is essential.

**Dependencies for Phase 2:**
- Phase 2 (connection pooling) cannot start until Redis is confirmed healthy
- Phase 2 requires 2+ hours of stable Redis operation before implementation
- If Phase 1 fails, Phase 2 and 3 are skipped (rollback to v2.1 instead)

**Parallel tool calling:**
When verifying multiple endpoints, use parallel curl commands for efficiency. However, the E2E test suite must run sequentially as tests may have dependencies.

**User interaction:**
You will need to ask the user to confirm when they've restarted Redis in Railway Dashboard. Use clear prompts and wait for their confirmation before proceeding to health checks.

</important_notes>
