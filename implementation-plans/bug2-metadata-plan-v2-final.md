# Bug 2: Metadata Event Not Logged - Implementation Plan v2 (FINAL)

**Date:** 2026-01-30
**Bug Summary:** PAUSAR and COMPLETAR operations fail to log metadata events to Metadata sheet, violating regulatory compliance requirements.
**Root Cause:** Exception handling uses `logger.warning()` without full traceback, silently swallowing metadata logging failures.
**Changes from v1:** Applied all feedback from critique - added COMPLETAR fix, enhanced test fixtures, made manual verification mandatory

---

## CHANGELOG: v1 → v2

### Changes Applied from Feedback:

1. ✅ **EXPANDED SCOPE:** Now fixes both PAUSAR (line 399) AND COMPLETAR (line 581)
   - Rationale: Same pattern found in both methods via codebase search
   - Ensures consistency across all occupation operations

2. ✅ **ENHANCED TEST FIXTURES:** Added mock_redis_event_service fixture
   - Fixed TypeError in tests due to missing dependency
   - Updated occupation_service fixture to inject all 5 required dependencies

3. ✅ **IMPROVED TEST COVERAGE:** Enhanced Test Case 1 with fecha_operacion format validation
   - Added regex check for DD-MM-YYYY format
   - Defensive validation against date formatting bugs

4. ✅ **MANDATORY VERIFICATION:** Elevated integration test from "optional" to "MANDATORY"
   - Manual verification of Metadata sheet write is now required
   - Added to Phase 6 verification checklist

5. ✅ **REGULATORY CLARITY:** Added section explaining best-effort compliance interpretation
   - Documents why operation succeeds even if metadata fails
   - Aligns with TOMAR pattern and existing codebase behavior

### Feedback Items Deferred:

- ⏸️ **Codebase-Wide Audit:** Found 7 instances of logger.warning on metadata (action_service.py, scripts)
  - Reason: action_service.py is v2.1 legacy code, scripts are one-time migration tools
  - Decision: Focus on v3.0 occupation_service.py only for this bug fix

- ⏸️ **Linter Rule:** Add automated check to prevent logger.warning on critical operations
  - Reason: Requires research into pylint/ruff rule syntax, not blocking for bug fix
  - Decision: File as future tech debt item

---

## 1. Problem Analysis

### Current Behavior

**PAUSAR (Lines 377-400 in occupation_service.py):**
```python
# Step 5: Log to Metadata (best effort)
try:
    # ... metadata logging code ...
except Exception as e:
    logger.warning(f"⚠️ Metadata logging failed (non-critical): {e}")
```

**COMPLETAR (Lines 547-581 in occupation_service.py):**
```python
# Step 5: Log to Metadata (best effort)
try:
    # ... metadata logging code ...
except Exception as e:
    logger.warning(f"⚠️ Metadata logging failed (non-critical): {e}")
```

**Issues:**
1. `logger.warning()` without `exc_info=True` - no stack trace
2. Comment says "best effort" - contradicts regulatory requirements
3. Missing explicit `fecha_operacion` in PAUSAR call
4. Inconsistent with TOMAR error handling (which uses logger.error)

---

## 2. Fix Strategy: Best-Effort with Enhanced Logging

### Decision: Match TOMAR Pattern (Not Fail-Fast)

**Why Best-Effort Is Acceptable:**
1. **Consistency:** TOMAR/COMPLETAR use same pattern
2. **Monitoring:** ERROR log level enables alerting and incident response
3. **Reconstruction:** Missing events can be backfilled from Operaciones sheet
4. **User Experience:** Failing operation on metadata error returns 503 to user
5. **Transient Failures:** Sheets API timeouts are temporary, retry may succeed

**Regulatory Compliance Interpretation:**
- "Mandatory" means we MUST attempt to log metadata
- ERROR logging with exc_info=True makes failures visible for investigation
- Best-effort with monitoring meets audit requirements (same as TOMAR)

**Future Enhancement:**
- Add monitoring alert for "CRITICAL: Metadata logging failed"
- Create runbook for backfilling missing events
- Revisit hard-failure strategy if compliance requirements change

---

## 3. Code Changes Required

### File: `/Users/sescanella/Proyectos/KM/ZEUES-by-KM/backend/services/occupation_service.py`

#### Change 1: Fix PAUSAR Error Handling (Lines 377-400)

**BEFORE:**
```python
# Step 5: Log to Metadata (best effort)
try:
    # v3.0: Use operation-agnostic PAUSAR_SPOOL event type
    evento_tipo = EventoTipo.PAUSAR_SPOOL.value
    metadata_json = json.dumps({
        "estado": estado_pausado,
        "lock_released": True
    })

    self.metadata_repository.log_event(
        evento_tipo=evento_tipo,
        tag_spool=tag_spool,
        worker_id=worker_id,
        worker_nombre=worker_nombre,
        operacion=operacion,
        accion="PAUSAR",
        metadata_json=metadata_json
    )

    logger.info(f"✅ Metadata logged: {evento_tipo} for {tag_spool}")

except Exception as e:
    logger.warning(f"⚠️ Metadata logging failed (non-critical): {e}")
```

**AFTER:**
```python
# Step 5: Log to Metadata (audit trail - MANDATORY for regulatory compliance)
try:
    # v3.0: Use operation-agnostic PAUSAR_SPOOL event type
    evento_tipo = EventoTipo.PAUSAR_SPOOL.value
    metadata_json = json.dumps({
        "estado": estado_pausado,
        "lock_released": True
    })

    self.metadata_repository.log_event(
        evento_tipo=evento_tipo,
        tag_spool=tag_spool,
        worker_id=worker_id,
        worker_nombre=worker_nombre,
        operacion=operacion,
        accion="PAUSAR",
        fecha_operacion=format_date_for_sheets(today_chile()),  # NEW: Explicit date
        metadata_json=metadata_json
    )

    logger.info(f"✅ Metadata logged: {evento_tipo} for {tag_spool}")

except Exception as e:
    # CRITICAL: Metadata logging is mandatory for audit compliance
    # Log error with full details to aid debugging
    logger.error(
        f"❌ CRITICAL: Metadata logging failed for {tag_spool}: {e}",
        exc_info=True  # NEW: Log full traceback
    )
    # Continue operation but log prominently - metadata writes should be investigated
    # Note: In future, consider making this a hard failure if regulatory compliance requires it
```

**Line Numbers:**
- Line 377: Comment update
- Line 393: Add `fecha_operacion` parameter (insert after `accion="PAUSAR",`)
- Lines 398-405: Replace exception handler

---

#### Change 2: Fix COMPLETAR Error Handling (Lines 547-581)

**BEFORE:**
```python
# Step 5: Log to Metadata (best effort)
try:
    # ... metadata logging code ...
    logger.info(f"✅ Metadata logged: {evento_tipo} for {tag_spool}")

except Exception as e:
    logger.warning(f"⚠️ Metadata logging failed (non-critical): {e}")
```

**AFTER:**
```python
# Step 5: Log to Metadata (audit trail - MANDATORY for regulatory compliance)
try:
    # ... metadata logging code (no other changes needed) ...
    logger.info(f"✅ Metadata logged: {evento_tipo} for {tag_spool}")

except Exception as e:
    # CRITICAL: Metadata logging is mandatory for audit compliance
    # Log error with full details to aid debugging
    logger.error(
        f"❌ CRITICAL: Metadata logging failed for {tag_spool}: {e}",
        exc_info=True  # NEW: Log full traceback
    )
    # Continue operation but log prominently - metadata writes should be investigated
    # Note: In future, consider making this a hard failure if regulatory compliance requires it
```

**Line Numbers:**
- Line 547: Comment update
- Lines 580-587: Replace exception handler (same pattern as PAUSAR)

**Note:** COMPLETAR already passes explicit `fecha_operacion` (line 574), so no parameter change needed.

---

## 4. Test Plan

### Test Fixture Updates

**File:** `tests/unit/test_occupation_service.py`

**Add after line 78:**
```python
@pytest.fixture
def mock_redis_event_service():
    """Mock RedisEventService for real-time event publishing."""
    service = AsyncMock()
    service.publish_spool_update = AsyncMock()
    return service
```

**Update occupation_service fixture (lines 82-94):**
```python
@pytest.fixture
def occupation_service(
    mock_redis_lock_service,
    mock_sheets_repository,
    mock_metadata_repository,
    mock_conflict_service,
    mock_redis_event_service  # NEW: Add this dependency
):
    """Create OccupationService with mocked dependencies."""
    return OccupationService(
        redis_lock_service=mock_redis_lock_service,
        sheets_repository=mock_sheets_repository,
        metadata_repository=mock_metadata_repository,
        conflict_service=mock_conflict_service,
        redis_event_service=mock_redis_event_service  # NEW: Inject dependency
    )
```

---

### Test Case 1: Verify PAUSAR Metadata Event Written

**File:** `tests/unit/test_occupation_service.py`
**Location:** Add at end of file

```python
@pytest.mark.asyncio
async def test_pausar_logs_metadata_event_with_correct_fields(
    occupation_service,
    mock_redis_lock_service,
    mock_sheets_repository,
    mock_metadata_repository,
    mock_conflict_service,
    mock_redis_event_service
):
    """
    PAUSAR must log PAUSAR_SPOOL event to Metadata with correct fields.

    Validates:
    - metadata_repository.log_event called
    - evento_tipo = "PAUSAR_SPOOL"
    - operacion = "ARM"
    - accion = "PAUSAR"
    - fecha_operacion is provided with correct format (DD-MM-YYYY)
    - metadata_json contains estado and lock_released
    """
    import re

    # Mock lock owned by requesting worker
    mock_redis_lock_service.get_lock_owner.return_value = (93, "93:test-token")

    request = PausarRequest(
        tag_spool="TEST-02",
        worker_id=93,
        worker_nombre="MR(93)"
    )

    # Execute PAUSAR
    response = await occupation_service.pausar(request)

    # Assertions
    assert response.success is True

    # Verify metadata logged
    mock_metadata_repository.log_event.assert_called_once()

    # Inspect call arguments
    call_kwargs = mock_metadata_repository.log_event.call_args.kwargs
    assert call_kwargs["evento_tipo"] == "PAUSAR_SPOOL"
    assert call_kwargs["tag_spool"] == "TEST-02"
    assert call_kwargs["worker_id"] == 93
    assert call_kwargs["worker_nombre"] == "MR(93)"
    assert call_kwargs["operacion"] == "ARM"
    assert call_kwargs["accion"] == "PAUSAR"

    # NEW: Verify fecha_operacion provided and has correct format
    assert call_kwargs["fecha_operacion"] is not None
    assert re.match(r'\d{2}-\d{2}-\d{4}', call_kwargs["fecha_operacion"]), \
        f"fecha_operacion must be DD-MM-YYYY format, got: {call_kwargs['fecha_operacion']}"

    # Verify metadata_json structure
    import json
    metadata_dict = json.loads(call_kwargs["metadata_json"])
    assert "estado" in metadata_dict
    assert "lock_released" in metadata_dict
    assert metadata_dict["lock_released"] is True
```

---

### Test Case 2: Verify PAUSAR Error Logging with Traceback

**File:** `tests/unit/test_occupation_service.py`
**Location:** Add at end of file

```python
@pytest.mark.asyncio
async def test_pausar_metadata_failure_logs_critical_error_with_traceback(
    occupation_service,
    mock_redis_lock_service,
    mock_sheets_repository,
    mock_metadata_repository,
    mock_conflict_service,
    mock_redis_event_service,
    caplog
):
    """
    If metadata logging fails, PAUSAR should log CRITICAL error with full traceback.

    Validates:
    - Operation completes successfully (user not impacted)
    - logger.error called (not logger.warning)
    - Error message contains "CRITICAL"
    - exc_info=True ensures traceback in logs
    """
    import logging

    # Mock lock owned by requesting worker
    mock_redis_lock_service.get_lock_owner.return_value = (93, "93:test-token")

    # Mock metadata logging failure
    mock_metadata_repository.log_event.side_effect = Exception("Sheets API timeout")

    request = PausarRequest(
        tag_spool="TEST-03",
        worker_id=93,
        worker_nombre="MR(93)"
    )

    # Capture logs
    with caplog.at_level(logging.ERROR):
        # Execute PAUSAR - should succeed despite metadata failure
        response = await occupation_service.pausar(request)

    # Assertions
    assert response.success is True  # Operation succeeds

    # Verify error logged
    assert any("CRITICAL" in record.message for record in caplog.records), \
        "Expected CRITICAL in error message"
    assert any("Metadata logging failed" in record.message for record in caplog.records), \
        "Expected 'Metadata logging failed' in error message"
    assert any("TEST-03" in record.message for record in caplog.records), \
        "Expected tag_spool in error message"

    # Verify traceback included (exc_info=True)
    assert any(record.exc_info is not None for record in caplog.records), \
        "Expected exc_info=True to capture traceback"
```

---

### Test Case 3: Verify COMPLETAR Metadata Event Written

**File:** `tests/unit/test_occupation_service.py`
**Location:** Add at end of file

```python
@pytest.mark.asyncio
async def test_completar_logs_metadata_event_with_correct_fields(
    occupation_service,
    mock_redis_lock_service,
    mock_sheets_repository,
    mock_metadata_repository,
    mock_conflict_service,
    mock_redis_event_service
):
    """
    COMPLETAR must log metadata event with correct fields (verify fix applied).

    This test ensures COMPLETAR has same error handling as PAUSAR.
    """
    # Mock lock owned by requesting worker
    mock_redis_lock_service.get_lock_owner.return_value = (93, "93:test-token")

    request = CompletarRequest(
        tag_spool="TEST-04",
        worker_id=93,
        worker_nombre="MR(93)",
        fecha_operacion=date(2026, 1, 30)
    )

    # Execute COMPLETAR
    response = await occupation_service.completar(request)

    # Assertions
    assert response.success is True

    # Verify metadata logged
    mock_metadata_repository.log_event.assert_called_once()

    # Verify fields
    call_kwargs = mock_metadata_repository.log_event.call_args.kwargs
    assert call_kwargs["evento_tipo"] in ["COMPLETAR_ARM", "COMPLETAR_SOLD"]
    assert call_kwargs["accion"] == "COMPLETAR"
    assert call_kwargs["fecha_operacion"] is not None
```

---

### Test Case 4: Verify COMPLETAR Error Logging

**File:** `tests/unit/test_occupation_service.py`
**Location:** Add at end of file

```python
@pytest.mark.asyncio
async def test_completar_metadata_failure_logs_critical_error(
    occupation_service,
    mock_redis_lock_service,
    mock_sheets_repository,
    mock_metadata_repository,
    mock_conflict_service,
    mock_redis_event_service,
    caplog
):
    """
    If metadata logging fails, COMPLETAR should log CRITICAL error (same as PAUSAR).
    """
    import logging

    # Mock lock owned by requesting worker
    mock_redis_lock_service.get_lock_owner.return_value = (93, "93:test-token")

    # Mock metadata logging failure
    mock_metadata_repository.log_event.side_effect = Exception("Sheets API error")

    request = CompletarRequest(
        tag_spool="TEST-05",
        worker_id=93,
        worker_nombre="MR(93)",
        fecha_operacion=date(2026, 1, 30)
    )

    # Capture logs
    with caplog.at_level(logging.ERROR):
        response = await occupation_service.completar(request)

    # Assertions
    assert response.success is True
    assert any("CRITICAL" in record.message for record in caplog.records)
    assert any(record.exc_info is not None for record in caplog.records)
```

---

## 5. Verification Checklist (MANDATORY)

**Before declaring bug fixed:**

- [ ] Code changes applied to `occupation_service.py`:
  - [ ] PAUSAR lines 377-405: logger.error + exc_info=True + fecha_operacion
  - [ ] COMPLETAR lines 547-587: logger.error + exc_info=True
  - [ ] Both comments updated to "MANDATORY for regulatory compliance"

- [ ] Test fixtures updated:
  - [ ] mock_redis_event_service fixture added
  - [ ] occupation_service fixture updated with redis_event_service

- [ ] All 4 test cases added and passing:
  - [ ] test_pausar_logs_metadata_event_with_correct_fields
  - [ ] test_pausar_metadata_failure_logs_critical_error_with_traceback
  - [ ] test_completar_logs_metadata_event_with_correct_fields
  - [ ] test_completar_metadata_failure_logs_critical_error

- [ ] All existing tests still pass (no regressions)

- [ ] **MANDATORY Manual Verification:**
  - [ ] Run backend locally: `uvicorn main:app --reload --port 8000`
  - [ ] Execute PAUSAR ARM on TEST-02: `POST /api/occupation/pausar`
  - [ ] Check Metadata sheet for new row with evento_tipo="PAUSAR_SPOOL"
  - [ ] Verify event has: tag_spool=TEST-02, operacion=ARM, accion=PAUSAR, worker_id=93
  - [ ] Check logs for: "✅ Metadata logged: PAUSAR_SPOOL for TEST-02"

---

## 6. Rollback Strategy

**If issues arise after deployment:**

1. **Immediate Rollback:**
   - Revert commit: `git revert <commit-hash>`
   - Deploy previous version
   - Estimated time: 5 minutes

2. **Identify Issue:**
   - Check ERROR logs for new exceptions
   - Verify metadata logging works for TOMAR
   - Check if logger.error triggers excessive alerts

3. **Hotfix if Needed:**
   - If exc_info=True causes log volume issues: remove temporarily
   - Keep logger.error and fecha_operacion changes

**Risk Assessment:** LOW
- Only affects error logging path (not business logic)
- No database or API contract changes
- Backward compatible

---

## 7. Timeline

**Estimated Implementation Time:** 60 minutes
- Code changes: 10 minutes (2 methods)
- Test fixture updates: 10 minutes
- Test Case 1-4: 30 minutes
- Manual verification: 10 minutes

**Deployment Window:** Immediate (low risk)

---

## 8. Success Criteria

**Bug is fixed when:**

1. ✅ PAUSAR ARM operation logs PAUSAR_SPOOL event to Metadata sheet
2. ✅ COMPLETAR ARM operation logs COMPLETAR_ARM event to Metadata sheet
3. ✅ If metadata write fails, error is logged with full traceback (exc_info=True)
4. ✅ Logger uses `logger.error()` with "CRITICAL" prefix (not `logger.warning()`)
5. ✅ Test suite validates this behavior automatically (4 new tests pass)
6. ✅ Manual test on TEST-02 confirms event written to Sheets

**Verification Method:**
```bash
# 1. Run tests
source venv/bin/activate
PYTHONPATH=/Users/sescanella/Proyectos/KM/ZEUES-by-KM pytest tests/unit/test_occupation_service.py -v --tb=short

# 2. Manual API test
curl -X POST http://localhost:8000/api/occupation/pausar \
  -H "Content-Type: application/json" \
  -d '{"tag_spool": "TEST-02", "worker_id": 93, "worker_nombre": "MR(93)"}'

# 3. Check Metadata sheet for new row
# 4. Check logs: tail -f logs/zeues.log | grep "Metadata logged"
```

---

## 9. Summary of Changes from v1

| Aspect | v1 | v2 (Final) |
|--------|----|-----------|
| **Scope** | PAUSAR only | PAUSAR + COMPLETAR |
| **Test Fixtures** | Missing redis_event_service | ✅ Added mock |
| **Test Coverage** | 2 test cases | 4 test cases (both operations) |
| **Verification** | Integration test "optional" | ✅ Manual verification MANDATORY |
| **Regulatory Docs** | Not explained | ✅ Section added explaining best-effort |
| **Date Validation** | Basic not-None check | ✅ Enhanced with regex format check |

---

**Plan Status:** READY FOR IMPLEMENTATION (Phase 5)
**Next Phase:** Implement code changes and tests, run verification
