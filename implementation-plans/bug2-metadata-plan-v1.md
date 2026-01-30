# Bug 2: Metadata Event Not Logged - Implementation Plan v1

**Date:** 2026-01-30
**Bug Summary:** PAUSAR ARM operations fail to log PAUSAR_SPOOL events to Metadata sheet, violating regulatory compliance requirements.
**Root Cause:** Exception handling uses `logger.warning()` without full traceback, silently swallowing metadata logging failures.

---

## 1. Problem Analysis

### Current Behavior (Lines 377-400 in occupation_service.py)

```python
# Step 5: Log to Metadata (best effort)  # <- Line 377
try:
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
    logger.warning(f"⚠️ Metadata logging failed (non-critical): {e}")  # <- Line 399
    # NO RE-RAISE - exception is silently swallowed
```

**Issues Identified:**
1. Comment says "best effort" - contradicts CLAUDE.md regulatory requirement ("Metadata audit trail mandatory")
2. `logger.warning()` without `exc_info=True` - no stack trace for debugging
3. Exception message only shows `{e}` - loses exception type and context
4. Missing explicit `fecha_operacion` parameter (relies on default)
5. Inconsistent with TOMAR error handling pattern

---

## 2. Fix Strategy: Match TOMAR Pattern

### Decision: Best-Effort with Enhanced Logging (Not Fail-Fast)

**Rationale:**
- TOMAR uses best-effort approach (logs error but doesn't fail operation)
- Both TOMAR and COMPLETAR allow operation to succeed even if metadata fails
- Regulatory compliance is served by having metadata failure visible in logs
- Making metadata a hard failure would impact user experience (503 errors)
- **Consistency with existing codebase is paramount**

**Alternative Considered (Rejected):**
- Make metadata logging a hard failure (raise exception)
- Reason for rejection: Would break existing pattern in TOMAR/COMPLETAR, requires frontend changes to handle 503 errors

---

## 3. Code Changes Required

### File: `/Users/sescanella/Proyectos/KM/ZEUES-by-KM/backend/services/occupation_service.py`

#### Change 1: Update Error Handling (Lines 377-400)

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

**Changes Made:**
1. Comment changed from "best effort" to "MANDATORY for regulatory compliance"
2. Added explicit `fecha_operacion=format_date_for_sheets(today_chile())` parameter
3. Changed `logger.warning()` to `logger.error()` with **CRITICAL** prefix
4. Added `exc_info=True` to log full traceback
5. Enhanced error message format to match TOMAR pattern
6. Added comment about future hard failure consideration

**Line Numbers:**
- Line 377: Comment update
- Line 393: Add `fecha_operacion` parameter (after `accion="PAUSAR"`)
- Lines 398-405: Replace exception handler

---

## 4. Test Plan

### Test Case 1: Verify Metadata Event Is Written (CRITICAL)

**File:** `tests/unit/test_occupation_service.py`
**New Test:** `test_pausar_logs_metadata_event_with_correct_fields`

```python
@pytest.mark.asyncio
async def test_pausar_logs_metadata_event_with_correct_fields(
    occupation_service,
    mock_redis_lock_service,
    mock_sheets_repository,
    mock_metadata_repository
):
    """
    PAUSAR must log PAUSAR_SPOOL event to Metadata with correct fields.

    Validates:
    - metadata_repository.log_event called
    - evento_tipo = "PAUSAR_SPOOL"
    - operacion = "ARM"
    - accion = "PAUSAR"
    - fecha_operacion is provided (not None)
    - metadata_json contains estado and lock_released
    """
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
    assert call_kwargs["fecha_operacion"] is not None  # NEW: Verify date provided

    # Verify metadata_json structure
    import json
    metadata_dict = json.loads(call_kwargs["metadata_json"])
    assert "estado" in metadata_dict
    assert "lock_released" in metadata_dict
    assert metadata_dict["lock_released"] is True
```

**Expected Outcome:**
- Test PASSES after fix applied
- Test should already PASS if metadata logging is working (but investigation shows it's failing)

---

### Test Case 2: Verify Error Logging with Full Traceback (NEW)

**File:** `tests/unit/test_occupation_service.py`
**New Test:** `test_pausar_metadata_failure_logs_critical_error_with_traceback`

```python
@pytest.mark.asyncio
async def test_pausar_metadata_failure_logs_critical_error_with_traceback(
    occupation_service,
    mock_redis_lock_service,
    mock_sheets_repository,
    mock_metadata_repository,
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
    assert any("CRITICAL" in record.message for record in caplog.records)
    assert any("Metadata logging failed" in record.message for record in caplog.records)
    assert any("TEST-03" in record.message for record in caplog.records)

    # Verify traceback included (exc_info=True)
    # caplog captures exc_info, check that at least one record has it
    assert any(record.exc_info is not None for record in caplog.records)
```

**Expected Outcome:**
- Test FAILS before fix (logs warning, not error)
- Test PASSES after fix (logs error with exc_info=True)

---

### Test Case 3: Integration Test with Real Metadata Repository (Optional)

**File:** `tests/integration/test_occupation_metadata.py` (new file)
**Purpose:** Validate metadata actually written to Sheets (not just method called)

**Defer to Phase 5:** This test requires real Sheets credentials and is lower priority than unit tests.

---

## 5. Verification Checklist

**Before declaring bug fixed:**

- [ ] Code changes applied to `occupation_service.py` lines 377-405
- [ ] `logger.error()` used instead of `logger.warning()`
- [ ] `exc_info=True` added to error logging
- [ ] Comment updated to "MANDATORY for regulatory compliance"
- [ ] Explicit `fecha_operacion` parameter added
- [ ] Error message format matches TOMAR pattern (includes "CRITICAL")
- [ ] Test Case 1 added and passes
- [ ] Test Case 2 added and passes
- [ ] All existing tests still pass (no regressions)
- [ ] Manual verification: PAUSAR ARM on TEST-02 writes event to Metadata sheet

---

## 6. Rollback Strategy

**If issues arise after deployment:**

1. **Immediate Rollback:**
   - Revert commit with code changes
   - Deploy previous version to production
   - Estimated rollback time: 5 minutes

2. **Identify Issue:**
   - Check logs for new errors or exceptions
   - Verify metadata logging still works for TOMAR/COMPLETAR
   - Check if `logger.error()` is causing monitoring alerts

3. **Hotfix if Needed:**
   - If `exc_info=True` causes log volume issues, remove it temporarily
   - Keep other changes (logger.error, fecha_operacion, comment)

**Risk Assessment:** LOW
- Changes only affect error logging, not business logic
- PAUSAR flow unchanged (still best-effort metadata)
- No database or API contract changes

---

## 7. Side Effects and Considerations

### Positive Side Effects:
1. Metadata failures become visible in monitoring (ERROR log level)
2. Full traceback aids debugging production issues
3. Consistent error handling across TOMAR/PAUSAR/COMPLETAR
4. Explicit date parameter removes ambiguity

### Potential Negative Side Effects:
1. **Log Volume Increase:** If metadata failures are frequent, ERROR logs could trigger alerts
   - Mitigation: Monitor for 24 hours, tune alerting thresholds if needed
2. **Performance:** `exc_info=True` adds traceback formatting overhead
   - Impact: Negligible (only on exception path, not happy path)

### Open Questions:
1. **Should metadata logging be a hard failure?**
   - Current plan: NO (match TOMAR behavior)
   - Future consideration: Evaluate regulatory requirements with compliance team
2. **Is operacion detection correct?**
   - Current: Hardcoded to "ARM" (line 316)
   - Future enhancement: Detect from spool state (Armador vs Soldador)

---

## 8. Timeline

**Estimated Implementation Time:** 45 minutes
- Code changes: 10 minutes
- Test Case 1: 15 minutes
- Test Case 2: 15 minutes
- Verification: 5 minutes

**Deployment Window:** Immediate (low risk, backward compatible)

---

## 9. Success Criteria

**Bug is fixed when:**
1. ✅ PAUSAR ARM operation logs PAUSAR_SPOOL event to Metadata sheet
2. ✅ If metadata write fails, error is logged with full traceback
3. ✅ Logger uses `logger.error()` with `exc_info=True` (not `logger.warning()`)
4. ✅ Test suite validates this behavior automatically
5. ✅ Manual test on TEST-02 confirms event written to Sheets

**Verification Method:**
1. Run unit tests: `pytest tests/unit/test_occupation_service.py -v --tb=short`
2. Execute PAUSAR ARM on TEST-02 via API: `POST /api/occupation/pausar`
3. Check Metadata sheet for new row with evento_tipo="PAUSAR_SPOOL"
4. Check logs for success message: "✅ Metadata logged: PAUSAR_SPOOL for TEST-02"

---

**Plan Status:** READY FOR CRITIQUE (Phase 2)
**Next Phase:** Critique this plan to identify weaknesses and edge cases
