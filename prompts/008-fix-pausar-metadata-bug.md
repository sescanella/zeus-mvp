<objective>
Fix Bug 2 (CRITICAL): Metadata events not being logged in PAUSAR ARM workflow.

This fix is critical for regulatory compliance - the audit trail MUST capture all occupation events. Currently, PAUSAR_SPOOL events are silently failing, creating gaps in the immutable event log required for manufacturing traceability.

This prompt follows an iterative workflow: design implementation plan → critique the plan → convert critique to actionable feedback → apply feedback → implement fix → run tests → verify bug is resolved.
</objective>

<context>
Read the complete investigation report: @investigations/pausar-arm-bug-report.md

**Bug Summary (from investigation):**
- **What:** Metadata events not logged when worker executes PAUSAR ARM on spool
- **Where:** `backend/services/occupation_service.py:377-399` (pausar_spool method)
- **Root Cause:** Exception handling uses `logger.warning()` which silently swallows errors without full traceback
- **Impact:** Regulatory compliance violation - audit trail incomplete, events missing from Metadata sheet
- **Expected:** PAUSAR_SPOOL event with operacion=ARM, accion=PAUSAR written to Metadata sheet

**Technical Context:**
- ZEUES v3.0 real-time occupation tracking system
- Python FastAPI backend with Google Sheets as source of truth
- Metadata sheet: Event Sourcing audit trail (append-only, immutable)
- EventoTipo enum defines event types including PAUSAR_SPOOL
- MetadataRepository.log_occupation_event() writes events to Sheets

Read CLAUDE.md for full project architecture and conventions.
</context>

<iterative_workflow>

## Phase 1: Design Implementation Plan

Thoroughly analyze the investigation report and design a detailed implementation plan.

**Your plan must address:**

1. **Error Handling Fix**
   - Change `logger.warning()` to `logger.error()` with `exc_info=True`
   - Consider: Should metadata logging failure cause the entire operation to fail?
   - Current behavior: Best-effort (operation succeeds even if metadata fails)
   - Alternative: Fail-fast (operation fails if metadata fails - regulatory requirement?)

2. **Consistency with TOMAR/COMPLETAR**
   - Review how tomar_spool() handles metadata logging errors
   - Review how completar_spool() handles metadata logging errors
   - Ensure PAUSAR matches the pattern used in working code

3. **evento_tipo Validation**
   - Verify EventoTipo.PAUSAR_SPOOL exists and is correct value
   - Check if evento_tipo is being passed correctly to log_occupation_event()

4. **Testing Strategy**
   - Identify which test file should contain validation
   - Design test case that verifies metadata event is written
   - Consider: Should test use real Sheets API or mock?

**Deliverable:** Write your initial plan to `./implementation-plans/bug2-metadata-plan-v1.md`

Include:
- Specific files and line numbers to modify
- Code changes with before/after snippets
- Error handling strategy (best-effort vs fail-fast)
- Test plan with specific test cases
- Rollback strategy if issues arise

## Phase 2: Critique the Plan

Act as a senior code reviewer and thoroughly critique your plan from Phase 1.

**Critique dimensions:**

1. **Correctness:** Will this fix actually solve the root cause?
2. **Completeness:** Are there edge cases or related issues missed?
3. **Consistency:** Does this match patterns in TOMAR/COMPLETAR?
4. **Testing:** Will the test cases actually catch regressions?
5. **Risk:** What could go wrong? Are there safer alternatives?
6. **Regulatory:** Does this meet audit trail requirements?

**Ask hard questions:**
- "What if the Sheets API is temporarily down during PAUSAR?"
- "Should we fail the operation or just log the error?"
- "Are there other places in the codebase with the same pattern that need fixing?"
- "Does the test actually validate the event is written to Sheets, or just that the method was called?"

**Deliverable:** Write critique to `./implementation-plans/bug2-metadata-critique.md`

## Phase 3: Convert Critique to Actionable Feedback

Transform your critique into specific, actionable feedback items.

For EACH issue identified in the critique:
- State the problem clearly
- Propose a concrete solution
- Explain why this solution is better
- Estimate implementation effort (trivial/small/medium/large)

**Deliverable:** Write feedback to `./implementation-plans/bug2-metadata-feedback.md`

Format as checklist:
- [ ] Issue: [description]
      Solution: [specific action]
      Rationale: [why this improves the plan]
      Effort: [trivial/small/medium/large]

## Phase 4: Apply Feedback and Refine Plan

Update your original plan by applying the feedback from Phase 3.

**Process:**
1. Read bug2-metadata-plan-v1.md
2. Read bug2-metadata-feedback.md
3. Apply each feedback item to create improved plan
4. Document what changed and why

**Deliverable:** Write refined plan to `./implementation-plans/bug2-metadata-plan-v2-final.md`

Include changelog section showing:
- What changed from v1 to v2
- Which feedback items were applied
- Any feedback items rejected (with justification)

## Phase 5: Implement the Fix

Execute the final plan from Phase 4.

**Implementation checklist:**

1. **Activate virtual environment:**
   ```bash
   source venv/bin/activate
   ```

2. **Modify occupation_service.py:**
   - Change error handling in pausar_spool() method
   - Ensure consistency with tomar_spool() pattern
   - Add comments explaining error handling strategy

3. **Verify EventoTipo:**
   - Check backend/models/evento.py or similar
   - Confirm PAUSAR_SPOOL exists and is used correctly

4. **Update or create tests:**
   - Add test case validating metadata event is written
   - Test should fail BEFORE fix, pass AFTER fix
   - Consider testing both success and failure scenarios

5. **Follow CLAUDE.md conventions:**
   - Use proper date formatting (America/Santiago timezone)
   - Maintain Clean Architecture patterns
   - Add docstrings for any new methods

**Files to modify:**
- backend/services/occupation_service.py
- tests/integration/test_occupation_flow.py (or similar)

## Phase 6: Run Tests and Verify

Validate that the fix resolves the bug without introducing regressions.

**Testing sequence:**

1. **Run unit tests for occupation service:**
   ```bash
   PYTHONPATH=/Users/sescanella/Proyectos/KM/ZEUES-by-KM pytest tests/unit/test_occupation_service.py -v --tb=short
   ```

2. **Run integration tests:**
   ```bash
   PYTHONPATH=/Users/sescanella/Proyectos/KM/ZEUES-by-KM pytest tests/integration/test_occupation_flow.py -v --tb=short
   ```

3. **Run full test suite to check for regressions:**
   ```bash
   PYTHONPATH=/Users/sescanella/Proyectos/KM/ZEUES-by-KM pytest tests/ -v
   ```

4. **Manual verification (if possible):**
   - Run backend locally
   - Execute PAUSAR ARM operation on TEST-02 spool
   - Check Metadata sheet for PAUSAR_SPOOL event
   - Verify event has correct columns: tag_spool, worker_id, operacion=ARM, accion=PAUSAR

**Success criteria:**
- All new tests pass
- All existing tests still pass (no regressions)
- Metadata event is written to Sheets (manual verification or integration test)
- Error logging now shows full traceback if metadata fails

</iterative_workflow>

<deliverables>
Create these files during execution:

1. `./implementation-plans/bug2-metadata-plan-v1.md` - Initial implementation plan
2. `./implementation-plans/bug2-metadata-critique.md` - Critical review of plan
3. `./implementation-plans/bug2-metadata-feedback.md` - Actionable feedback checklist
4. `./implementation-plans/bug2-metadata-plan-v2-final.md` - Refined plan with changelog
5. Modified code files (occupation_service.py, test files)
6. `./implementation-plans/bug2-metadata-verification.md` - Test results and verification summary
</deliverables>

<constraints>
- **Regulatory compliance is paramount** - Metadata logging cannot be "best effort"
- **Maintain backward compatibility** - Do not break existing PAUSAR functionality
- **Follow existing patterns** - Match error handling in TOMAR/COMPLETAR exactly
- **Test coverage mandatory** - Must have test that validates metadata event written
- **All work in virtual environment** - ALWAYS activate venv before any Python work
- **Do not skip phases** - Complete all 6 phases in order (design → critique → feedback → apply → implement → verify)
</constraints>

<success_criteria>
Before declaring complete, verify ALL of these:

✓ All 6 phases completed with deliverables created
✓ bug2-metadata-plan-v2-final.md exists with changelog
✓ Code changes made to occupation_service.py
✓ Test case added that validates metadata event written
✓ All tests pass (new tests + existing tests)
✓ Error handling now uses logger.error() with exc_info=True
✓ Pattern matches TOMAR/COMPLETAR error handling
✓ Manual verification completed (or integration test validates Sheets write)
✓ bug2-metadata-verification.md documents test results

**The bug is fixed when:**
- PAUSAR ARM operation writes PAUSAR_SPOOL event to Metadata sheet
- If metadata write fails, error is logged with full traceback
- Test suite validates this behavior automatically
</success_criteria>

<verification>
Final self-check before declaring success:

1. Re-read the investigation report Bug 2 section
2. Confirm your implementation addresses the root cause (logger.warning → logger.error)
3. Verify test actually validates metadata is written (not just method called)
4. Check that all deliverables exist with substantive content
5. Confirm test results show bug is fixed

If any verification fails, continue work until all criteria met.
</verification>
