<objective>
Debug why Metadata events are still not being written despite code fix being deployed.

**Critical Issue:** After fixing the date format bug and enhancing error logging, the Operaciones sheet updates correctly but Metadata sheet STILL receives no events. The try/except block is likely catching and logging exceptions, but we need to identify the ROOT CAUSE.

**End Goal:** Identify why `metadata_repository.log_event()` is failing and implement a permanent fix.
</objective>

<context>
**Situation:**
1. ✅ Code fix was committed and pushed (commit c946fbb)
2. ✅ Operaciones sheet updates correctly with proper date format
3. ❌ Metadata sheet receives NO events (completely empty for TEST-02)
4. ⚠️ Backend is running with system Python 3.9, NOT venv
5. 🔍 Enhanced error logging SHOULD be showing errors in logs

**Technical Context:**
- Project: ZEUES v3.0
- Backend: FastAPI + Google Sheets + python-statemachine 2.5.0
- Virtual environment path: `./venv/`
- Backend process: Running on port 8000 with `uvicorn main:app --reload`

**Relevant Files:**
- @backend/services/occupation_service.py:199-220 - Metadata logging with error handling
- @backend/repositories/metadata_repository.py:331-392 - `log_event()` implementation
- @backend/models/metadata.py - MetadataEvent model
- @main.py - FastAPI app initialization and dependency injection
</context>

<investigation_requirements>
Systematically investigate in this order:

1. **Backend Process Verification**
   - ✅ Confirmed: Backend running on PID 92588 with system Python 3.9
   - ⚠️ Problem: NOT using virtual environment (should use `./venv/bin/python`)
   - Action needed: Restart backend with correct Python interpreter

2. **Code Deployment Status**
   - Check if running code matches git commit c946fbb
   - Verify `occupation_service.py` has the enhanced error logging (lines 213-218)
   - Confirm date formatter fix is active

3. **Log Analysis**
   - Search backend logs for "CRITICAL: Metadata logging failed"
   - Look for stack traces showing the exception type
   - Check for Google Sheets API errors, authentication failures, or permission issues

4. **Dependency Injection Chain**
   - Verify `main.py` creates `MetadataRepository` instance
   - Confirm `OccupationService` receives the repository via DI
   - Check if repository initialization fails silently

5. **Google Sheets Access**
   - Verify Metadata sheet exists and is named correctly (config.HOJA_METADATA_NOMBRE)
   - Check service account has write permissions to Metadata sheet
   - Test manual write to Metadata sheet via gspread

6. **MetadataEvent Model**
   - Review `MetadataEvent.from_sheets_row()` and `to_sheets_row()` methods
   - Check if model validation is failing (Pydantic errors)
   - Verify EventoTipo enum accepts "TOMAR_ARM" format

7. **Root Cause Hypothesis Testing**
   Run these tests in order:
   - Test 1: Restart backend with venv Python → Does metadata write succeed?
   - Test 2: Check logs for exception details → What specific error is occurring?
   - Test 3: Manually call `log_event()` via Python REPL → Does it work outside FastAPI context?
   - Test 4: Check Metadata sheet headers → Do they match expected column count (10)?
</investigation_requirements>

<implementation>
Follow this debugging workflow:

**Phase 1: Restart Backend with Virtual Environment**
```bash
# Kill current backend
pkill -f "uvicorn main:app"

# Activate venv and restart
source venv/bin/activate
PYTHONPATH=/Users/sescanella/Proyectos/KM/ZEUES-by-KM uvicorn main:app --reload --port 8000
```

**Phase 2: Reproduce Issue and Capture Logs**
```bash
# In a new terminal, tail the logs
# (Assuming logs go to stdout/stderr)

# Trigger TOMAR operation for TEST-02
curl -X POST http://localhost:8000/api/occupation/tomar \
  -H "Content-Type: application/json" \
  -d '{
    "tag_spool": "TEST-02",
    "worker_id": 93,
    "worker_nombre": "MR(93)",
    "operacion": "ARM"
  }'

# Watch for log output containing:
# - "CRITICAL: Metadata logging failed"
# - Stack traces with exception type
```

**Phase 3: Analyze Exception Type**

Based on logs, determine if error is:
- `gspread.exceptions.APIError` → Google API rate limit or quota
- `gspread.exceptions.WorksheetNotFound` → Sheet name mismatch
- `gspread.exceptions.SpreadsheetNotFound` → Auth or sheet ID issue
- `ValidationError` → Pydantic model validation failure
- `AttributeError/TypeError` → Missing/wrong parameter types

**Phase 4: Implement Fix**

Depending on root cause:

- **If worksheet not found:** Verify `config.HOJA_METADATA_NOMBRE` matches actual sheet name
- **If auth failure:** Check service account credentials and permissions
- **If API error:** Add retry logic (already exists via decorator)
- **If validation error:** Fix MetadataEvent model or data types
- **If dependency injection issue:** Fix main.py initialization

**Phase 5: Verify Fix**
1. Clear Redis locks: `redis-cli FLUSHALL` (or specific key)
2. Test TOMAR operation on fresh spool
3. Verify event appears in Metadata sheet
4. Check logs show "✅ Metadata logged: TOMAR_ARM"
</implementation>

<verification>
Before declaring complete:

1. **Backend Process Check**
   - Confirm backend running with venv Python: `ps aux | grep uvicorn | grep venv`
   - Verify process has latest code (restart if needed)

2. **Log Evidence**
   - Captured the specific exception message and stack trace
   - Identified the exact line where metadata write fails

3. **Root Cause Documented**
   - Specific file:line causing the failure
   - Exact exception type and message
   - Clear explanation of WHY it's failing

4. **Fix Validated**
   - Code change implemented (if needed)
   - Manual test confirms metadata events now write successfully
   - Both Operaciones AND Metadata sheets update correctly

5. **Regression Prevention**
   - Recommend monitoring/alerting for metadata failures
   - Suggest integration test to verify end-to-end flow
</verification>

<output>
Create `./DEBUG-METADATA-FAILURE-ROOT-CAUSE.md` with:

## Investigation Summary

**Root Cause:** [Specific issue - e.g., "Backend running with wrong Python interpreter", "Metadata sheet not found", "Service account lacks write permission", etc.]

**Evidence:**
```
[Paste relevant log output showing the exception]
```

**Technical Details:**
- File: [specific file:line]
- Exception Type: [e.g., WorksheetNotFound, APIError]
- Exception Message: [exact message]

## Fix Applied

**Change 1:** [Description]
```python
# Before
[old code]

# After
[new code]
```

**Change 2:** [If applicable]

## Verification Steps

**Test Command:**
```bash
[Command to reproduce and verify fix]
```

**Expected Result:**
- Operaciones sheet: Correct date format in Fecha_Ocupacion
- Metadata sheet: Event row created with TOMAR_ARM
- Logs: "✅ Metadata logged: TOMAR_ARM for TEST-02"

## Recommendations

1. **Immediate:**
   - [Action items to prevent recurrence]

2. **Long-term:**
   - Add integration test for metadata writes
   - Set up monitoring for "CRITICAL: Metadata logging failed"
   - Consider making metadata failure a hard error (raise exception instead of log and continue)

## Files Modified
- [List of files changed]
</output>

<success_criteria>
- Backend restarted with correct Python interpreter (venv)
- Specific exception type and message identified from logs
- Root cause clearly documented with evidence
- Fix implemented (if code change needed)
- Manual test confirms metadata events now write to Google Sheets
- Investigation report saved to ./DEBUG-METADATA-FAILURE-ROOT-CAUSE.md
</success_criteria>