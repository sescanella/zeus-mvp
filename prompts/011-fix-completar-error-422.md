<objective>
Fix the COMPLETAR Error 422 caused by date format mismatch between frontend and backend.

**Multi-Phase Approach:**
1. Create an implementation plan
2. Critically evaluate the plan
3. Convert critique into actionable feedback
4. Implement the solution with feedback incorporated

This fix is CRITICAL for production - it blocks all COMPLETAR operations for ARM and SOLD workflows, affecting all workers.
</objective>

<context>
Read the investigation report: @investigations/completar-error-422-analysis.md

**Root Cause Summary:**
- Frontend sends: `{"fecha_operacion": "30-01-2026"}` (DD-MM-YYYY)
- Backend expects: ISO 8601 `"2026-01-30"` (YYYY-MM-DD)
- Pydantic validation fails → HTTP 422

**Fix Strategy (Per User Selection):**
- **Location:** Backend only (adapt backend to accept frontend format)
- **Testing:** Integration tests (full COMPLETAR flow with real dates)

**Project Context:**
Read CLAUDE.md for architecture, tech stack, and conventions.

**Tech Stack:**
- Backend: FastAPI + Pydantic
- Frontend: Next.js + TypeScript
- Data: Google Sheets (dates written as DD-MM-YYYY per project standards)
</context>

<phase_1_planning>
**Step 1: Create Implementation Plan**

Thoroughly analyze the codebase and create a detailed implementation plan covering:

1. **Backend Changes:**
   - Identify all Pydantic models with `date` fields in occupation flow
   - Determine best approach to accept DD-MM-YYYY format:
     - Custom Pydantic validator (`@field_validator`)
     - Custom type with `__get_validators__`
     - Pre-processing in router before validation
   - Assess impact on other endpoints (TOMAR, PAUSAR)
   - Ensure backward compatibility if needed

2. **Testing Strategy:**
   - Integration test for COMPLETAR with DD-MM-YYYY date
   - Test both valid and invalid date formats
   - Verify date is correctly written to Sheets as DD-MM-YYYY
   - Test all three occupation endpoints (TOMAR, PAUSAR, COMPLETAR)

3. **Files to Modify:**
   - List specific files and line numbers
   - Specify exact changes needed
   - Identify any utility functions to create/modify

4. **Risk Assessment:**
   - Identify potential breaking changes
   - Consider edge cases (leap years, invalid dates, timezone issues)
   - Verify compatibility with existing data

**Output Plan to:** `./plans/fix-completar-error-422-plan.md`

Use this structure:
```markdown
# Implementation Plan: Fix COMPLETAR Error 422

## Problem Statement
[Brief summary]

## Proposed Solution
[High-level approach]

## Implementation Steps

### Backend Changes
1. [Specific change with file:line reference]
2. [...]

### Testing
1. [Test case 1]
2. [...]

## Files to Modify
- `file/path.py:line` - [what changes]

## Risk Assessment
- [Risk 1] - [Mitigation]

## Success Criteria
- [ ] COMPLETAR accepts DD-MM-YYYY format
- [ ] Integration tests pass
- [ ] No regression in TOMAR/PAUSAR
```
</phase_1_planning>

<phase_2_critique>
**Step 2: Critically Evaluate the Plan**

After creating the plan, perform a rigorous critique:

1. **Technical Soundness:**
   - Is the chosen Pydantic approach optimal?
   - Are there simpler alternatives?
   - Does it align with FastAPI best practices?

2. **Completeness:**
   - Are all affected models identified?
   - Is the testing strategy comprehensive enough?
   - Are edge cases covered?

3. **Project Alignment:**
   - Does it follow CLAUDE.md conventions?
   - Is it consistent with existing date handling (`format_date_for_sheets`)?
   - Does it respect the "dates in DD-MM-YYYY" project standard?

4. **Risks:**
   - Could this break existing functionality?
   - Are there timezone implications?
   - What happens if frontend eventually sends ISO format?

5. **Maintainability:**
   - Is the solution clear and well-documented?
   - Will future developers understand why this exists?
   - Is it easy to test and debug?

**Output Critique to:** `./plans/fix-completar-error-422-critique.md`

Be brutally honest - identify weaknesses, overlooked issues, and potential improvements.
</phase_2_critique>

<phase_3_feedback>
**Step 3: Convert Critique to Actionable Feedback**

Transform the critique into concrete improvements:

1. For each weakness identified, propose a specific fix
2. Prioritize feedback (MUST fix vs SHOULD improve vs NICE to have)
3. Update the implementation plan with feedback incorporated
4. Create a final, improved plan

**Output Feedback to:** `./plans/fix-completar-error-422-feedback.md`

Structure:
```markdown
# Feedback on Implementation Plan

## Critical Issues (MUST Fix)
1. [Issue] → [Specific improvement]

## Important Improvements (SHOULD Fix)
1. [Issue] → [Specific improvement]

## Nice-to-Have Enhancements
1. [Issue] → [Specific improvement]

## Revised Implementation Plan
[Updated plan incorporating all MUST and SHOULD feedback]
```
</phase_3_feedback>

<phase_4_implementation>
**Step 4: Implement the Solution**

Now implement the REVISED plan with feedback incorporated:

1. **Backend Changes:**
   - Modify Pydantic models to accept DD-MM-YYYY
   - Add proper validation and error handling
   - Ensure dates are converted to Python `date` objects correctly
   - Update any related models (TOMAR, PAUSAR if affected)

2. **Integration Tests:**
   - Create test file: `tests/integration/test_completar_date_format.py`
   - Test COMPLETAR with DD-MM-YYYY format
   - Test invalid formats (MM-DD-YYYY, YYYY-MM-DD if should reject, etc.)
   - Test edge cases (leap years, invalid dates, etc.)
   - Verify Sheets writes DD-MM-YYYY correctly

3. **Documentation:**
   - Add inline comments explaining the date format handling
   - Update docstrings if needed

4. **Verification:**
   - Run ALL existing tests to ensure no regression
   - Run new integration tests
   - Test manually with curl if possible
</phase_4_implementation>

<implementation_constraints>
**Critical Constraints:**

1. **Date Format Consistency:**
   - Backend must accept DD-MM-YYYY from frontend
   - Backend must write DD-MM-YYYY to Sheets (existing behavior)
   - WHY: Project-wide standard per CLAUDE.md

2. **No Frontend Changes:**
   - Frontend continues sending DD-MM-YYYY
   - WHY: Backend-only fix per user selection

3. **Pydantic Compatibility:**
   - Must work with FastAPI automatic validation
   - Must return clear error messages for invalid dates
   - WHY: FastAPI best practices for API design

4. **Test Coverage:**
   - Must include integration tests covering full flow
   - WHY: Prevent similar issues in production

5. **Virtual Environment:**
   - ALWAYS activate venv before running tests
   - WHY: Isolated dependencies per CLAUDE.md
</implementation_constraints>

<verification>
Before declaring complete, verify:

1. **Plan Quality:**
   - ✓ Implementation plan created with specific file references
   - ✓ Critique identifies genuine weaknesses
   - ✓ Feedback provides actionable improvements
   - ✓ All planning documents saved to ./plans/

2. **Implementation Quality:**
   - ✓ Backend accepts DD-MM-YYYY format successfully
   - ✓ COMPLETAR endpoint returns 200 (not 422) with valid DD-MM-YYYY date
   - ✓ Integration tests pass (run with: `source venv/bin/activate && pytest tests/integration/test_completar_date_format.py -v`)
   - ✓ All existing tests still pass (no regression)
   - ✓ Code follows project conventions from CLAUDE.md

3. **Testing:**
   - ✓ Test with valid DD-MM-YYYY: `"30-01-2026"` → Success
   - ✓ Test with invalid format: `"2026-01-30"` → Clear error (if should reject)
   - ✓ Test with invalid date: `"32-13-2026"` → Validation error
   - ✓ Verify Sheets receives DD-MM-YYYY format

4. **Manual Verification (Optional but Recommended):**
   ```bash
   # Test COMPLETAR with DD-MM-YYYY
   curl -X POST http://localhost:8000/api/occupation/completar \
     -H "Content-Type: application/json" \
     -d '{"tag_spool":"TEST-02","worker_id":94,"operacion":"ARM","fecha_operacion":"30-01-2026"}'
   ```
</verification>

<output>
**Planning Phase Outputs:**
1. `./plans/fix-completar-error-422-plan.md` - Initial implementation plan
2. `./plans/fix-completar-error-422-critique.md` - Critical evaluation
3. `./plans/fix-completar-error-422-feedback.md` - Actionable feedback + revised plan

**Implementation Outputs:**
1. Modified backend files (Pydantic models, validators)
2. `tests/integration/test_completar_date_format.py` - Integration tests
3. Updated documentation/comments as needed

**Verification Output:**
- Summary of test results
- Confirmation that Error 422 is resolved
</output>

<success_criteria>
**Planning Success:**
- All three planning documents created with thorough analysis
- Critique identifies real weaknesses (not superficial)
- Feedback provides concrete, implementable improvements
- Revised plan incorporates critical feedback

**Implementation Success:**
- COMPLETAR accepts `{"fecha_operacion": "30-01-2026"}` without Error 422
- Integration tests pass with 100% success rate
- No regression in existing tests
- Code is clean, well-commented, and follows project conventions
- Manual curl test (if performed) returns 200 OK

**Production Readiness:**
- Fix resolves the production blocker
- All workers can successfully complete spools
- Date format consistency maintained across system
</success_criteria>
