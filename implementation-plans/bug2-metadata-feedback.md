# Bug 2: Metadata Event Not Logged - Actionable Feedback

**Date:** 2026-01-30
**Source:** bug2-metadata-critique.md
**Purpose:** Convert critique issues into concrete action items for plan v2

---

## Feedback Checklist

### CRITICAL PRIORITY (Must Address Before Implementation)

- [x] **Issue 1: Missing RedisEventService Mock**
      **Problem:** Test fixtures don't include `redis_event_service` dependency, tests will fail with TypeError
      **Solution:** Add `mock_redis_event_service` fixture and inject into `occupation_service` fixture
      **Rationale:** OccupationService constructor requires 5 dependencies (line 66-88), tests only provide 4
      **Effort:** Trivial (5 minutes)

      **Specific Changes:**
      ```python
      # Add to test_occupation_service.py after line 78
      @pytest.fixture
      def mock_redis_event_service():
          """Mock RedisEventService."""
          service = AsyncMock()
          service.publish_spool_update = AsyncMock()
          return service

      # Update occupation_service fixture (line 82-94) to:
      @pytest.fixture
      def occupation_service(
          mock_redis_lock_service,
          mock_sheets_repository,
          mock_metadata_repository,
          mock_conflict_service,
          mock_redis_event_service  # ADD THIS
      ):
          return OccupationService(
              redis_lock_service=mock_redis_lock_service,
              sheets_repository=mock_sheets_repository,
              metadata_repository=mock_metadata_repository,
              conflict_service=mock_conflict_service,
              redis_event_service=mock_redis_event_service  # ADD THIS
          )
      ```

- [x] **Issue 2: Test Cases Missing Fixture Parameters**
      **Problem:** New test cases don't include `mock_conflict_service` and `mock_redis_event_service` in function signatures
      **Solution:** Add these fixtures to test function parameters
      **Rationale:** pytest requires all fixtures used by dependencies to be explicitly listed
      **Effort:** Trivial (2 minutes)

      **Specific Changes:**
      ```python
      async def test_pausar_logs_metadata_event_with_correct_fields(
          occupation_service,
          mock_redis_lock_service,
          mock_sheets_repository,
          mock_metadata_repository,
          mock_conflict_service,  # ADD THIS
          mock_redis_event_service  # ADD THIS
      ):
      ```

- [x] **Issue 3: Add Integration Test to Verification Plan**
      **Problem:** Plan marks integration test as "optional" but mocks don't validate real Sheets writes
      **Solution:** Make manual verification mandatory in Phase 6, add explicit checklist item
      **Rationale:** Regulatory compliance requires actual writes to Sheets, not just method calls
      **Effort:** Small (already planned, just elevate priority)

      **Specific Changes to Plan:**
      - Section 4, Test Case 3: Change "Optional" to "MANDATORY"
      - Section 5, Verification Checklist: Add as required step (not optional)
      - Section 9, Success Criteria: Make manual test a blocker for completion

### IMPORTANT PRIORITY (Should Address for Quality)

- [x] **Issue 4: Check COMPLETAR for Same Bug Pattern**
      **Problem:** COMPLETAR has identical logger.warning pattern (line 581), inconsistent if only PAUSAR fixed
      **Solution:** Search codebase for `logger.warning.*Metadata` and fix all instances
      **Rationale:** Consistency across codebase, prevent similar bugs in COMPLETAR
      **Effort:** Small (10 minutes to search + apply same fix)

      **Specific Actions:**
      1. Search: `git grep "logger.warning.*Metadata" backend/`
      2. If COMPLETAR found: Apply identical fix (logger.error + exc_info=True)
      3. Update test plan to cover both PAUSAR and COMPLETAR
      4. Commit both changes together for consistency

- [x] **Issue 5: Clarify Best-Effort vs Hard Failure Strategy**
      **Problem:** Plan says "MANDATORY" but allows operation to succeed on metadata failure
      **Solution:** Explicitly document best-effort rationale in plan v2
      **Rationale:** Aligns with TOMAR behavior, clarifies compliance interpretation
      **Effort:** Trivial (documentation only, no code change)

      **Specific Changes to Plan:**
      Add new section "6.5 Regulatory Compliance Interpretation":
      ```
      **Why Best-Effort Is Acceptable:**
      1. TOMAR/COMPLETAR use same pattern (consistency)
      2. ERROR log level enables monitoring and incident response
      3. Missing events can be reconstructed from Operaciones sheet state
      4. Failing operation on metadata error impacts user experience (503 errors)
      5. Metadata failures are typically transient (Sheets API timeouts)

      **Future Enhancement:**
      - Add monitoring alert for "CRITICAL: Metadata logging failed"
      - Create runbook for backfilling events from Operaciones sheet
      - Revisit hard-failure strategy if compliance requirements change
      ```

### MINOR PRIORITY (Nice to Have)

- [x] **Issue 6: Enhance Test Case 1 Assertions**
      **Problem:** Test verifies fecha_operacion is not None, but doesn't validate format
      **Solution:** Add assertion to check fecha_operacion matches DD-MM-YYYY format
      **Rationale:** Defensive validation, catches date formatting bugs
      **Effort:** Trivial (2 minutes)

      **Specific Changes:**
      ```python
      # Add to test_pausar_logs_metadata_event_with_correct_fields
      import re
      assert call_kwargs["fecha_operacion"] is not None
      # NEW: Validate format is DD-MM-YYYY
      assert re.match(r'\d{2}-\d{2}-\d{4}', call_kwargs["fecha_operacion"])
      ```

- [ ] **Issue 7: Add Codebase-Wide Metadata Pattern Audit**
      **Problem:** Critique asks "are there other places with same pattern?"
      **Solution:** Search entire backend/ for logger.warning on metadata operations
      **Rationale:** Prevent similar bugs in other services
      **Effort:** Medium (30 minutes to search, analyze, fix)

      **Specific Actions:**
      ```bash
      # Search for all metadata logging patterns
      git grep -n "metadata.*log" backend/services/
      git grep -n "logger.warning" backend/services/ | grep -i metadata

      # Review each occurrence:
      # - Is it in try/except for metadata logging?
      # - Should it be logger.error?
      # - Does it have exc_info=True?
      ```

      **Decision:** DEFER to future tech debt cleanup (not blocking for this bug fix)

- [ ] **Issue 8: Add Linter Rule to Prevent Future Violations**
      **Problem:** No automated check prevents logger.warning on critical operations
      **Solution:** Add pylint or ruff rule to warn on logger.warning in metadata context
      **Rationale:** Prevent regressions
      **Effort:** Medium (research rule syntax, add to config)

      **Decision:** DEFER to future tech debt cleanup (not blocking for this bug fix)

---

## Summary of Actions for Plan v2

### Changes to Code Implementation:

1. ✅ **No Change:** Core fix remains the same (logger.error + exc_info=True + fecha_operacion)
2. ✅ **Optional Addition:** Fix COMPLETAR too if same pattern found (Issue 4)

### Changes to Test Plan:

1. ✅ **ADD:** mock_redis_event_service fixture (Issue 1)
2. ✅ **UPDATE:** occupation_service fixture to inject redis_event_service (Issue 1)
3. ✅ **UPDATE:** Test Case 1 and 2 to include all required fixtures (Issue 2)
4. ✅ **ENHANCE:** Test Case 1 to validate fecha_operacion format (Issue 6)
5. ✅ **ELEVATE:** Make manual verification mandatory, not optional (Issue 3)

### Changes to Documentation:

1. ✅ **ADD:** Section 6.5: Regulatory Compliance Interpretation (Issue 5)
2. ✅ **UPDATE:** Section 4, Test Case 3: Change "Optional" to "MANDATORY" (Issue 3)
3. ✅ **UPDATE:** Section 5: Add manual verification as required checklist item (Issue 3)

### Deferred Actions (Not Blocking):

1. ⏸️ **DEFER:** Codebase-wide metadata audit (Issue 7)
2. ⏸️ **DEFER:** Add linter rule (Issue 8)

---

## Rejected Feedback Items

**None.** All critique issues are valid and should be addressed.

---

## Validation Before Moving to Phase 4

**Self-Check:**
- [x] All CRITICAL issues have concrete solutions
- [x] All IMPORTANT issues are addressed or explicitly deferred
- [x] Solutions are specific (file names, line numbers, code snippets)
- [x] Effort estimates provided for each item
- [x] Deferred items have clear rationale

**Ready for Phase 4:** ✅ YES

---

**Feedback Status:** COMPLETE
**Next Phase:** Apply feedback and create bug2-metadata-plan-v2-final.md
