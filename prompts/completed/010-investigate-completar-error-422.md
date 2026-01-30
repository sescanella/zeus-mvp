<objective>
Investigate the root cause of Error 422 that occurs when attempting to complete a spool via the COMPLETAR operation.

**DO NOT FIX THE ERROR - ONLY INVESTIGATE AND DOCUMENT THE ROOT CAUSE**

This investigation is critical for understanding why the completion workflow is failing in production.
</objective>

<context>
From the error screenshot:
- **Operation**: ARMADO - COMPLETAR
- **Worker**: MR(94)
- **Spool**: TEST-02
- **Error**: HTTP 422 from POST `https://zeues-backend-mvp-production.up.railway.app/api/occupation/completar`
- **UI State**: User reached confirmation page (P5), clicked "CONFIRMAR 1 SPOOL" button

Error 422 typically indicates "Unprocessable Entity" - the request syntax is valid but the server cannot process it due to semantic/business logic errors.

Read CLAUDE.md for project architecture and conventions.
</context>

<investigation_requirements>
Thoroughly analyze the COMPLETAR endpoint to identify why it's returning 422:

1. **Backend Investigation**:
   - Examine `@routers/occupation.py` - locate the `/api/occupation/completar` endpoint
   - Trace the request flow: router → service layer → validation → state machine → repository
   - Identify ALL validation checks that could raise 422 errors
   - Check custom exceptions in `@exceptions.py` that map to HTTP 422

2. **State Machine Analysis**:
   - Review `@state_machines/arm_state_machine.py` for COMPLETAR transitions
   - Identify which states allow the `completar` transition
   - Check if TEST-02 might be in an incompatible state

3. **Validation Logic**:
   - Examine `@services/validation_service.py` for COMPLETAR-specific validations
   - Check occupation validation (is the worker allowed to complete this spool?)
   - Verify version/locking checks (optimistic locking failures)

4. **Redis Lock Investigation**:
   - Check `@repositories/redis_repository.py` for lock verification during COMPLETAR
   - Determine if expired locks or ownership mismatches could cause 422

5. **API Request Examination**:
   - Review `@zeues-frontend/lib/api.ts` - check the payload sent to `/completar`
   - Compare with backend expected schema in `@models/occupation.py` or similar

6. **Recent Changes**:
   - Use `!git log --oneline --since="2 weeks ago" -- backend/routers/occupation.py backend/services/ backend/state_machines/` to check recent modifications
   - Correlate error timing with any recent commits
</investigation_requirements>

<research>
For maximum efficiency, invoke all file reading tools in parallel:
- Read occupation router
- Read validation service
- Read ARM state machine
- Read exceptions file
- Read Redis repository
- Read frontend API client

After receiving results, carefully analyze the code flow to pinpoint the exact validation/check that triggers the 422 response.
</research>

<output>
Create a detailed investigation report: `./investigations/completar-error-422-analysis.md`

The report must include:

## Error Summary
- Exact error message and HTTP status
- Context (operation, worker, spool, timestamp from screenshot)

## Root Cause Analysis
- Specific line(s) of code causing the 422 response
- The validation/business rule that failed
- WHY this validation exists (explain the constraint's purpose)

## Reproduction Conditions
- Exact conditions needed to trigger this error
- Spool state requirements
- Worker/ownership requirements
- Redis lock state
- Any timing/race condition factors

## Data State Investigation
If possible, infer the likely state of TEST-02:
- Current state in ARM state machine
- Ocupado_Por value
- Redis lock status
- version field value

## Hypothesis
Clear hypothesis about what went wrong with this specific COMPLETAR attempt for TEST-02 by worker MR(94).

## Recommended Next Steps
(NOT fixes - just investigation recommendations):
- Additional logs to check
- Google Sheets data to verify
- Redis keys to inspect
- Further code areas to examine

## Code References
Link to all relevant code sections using `file:line` format.
</output>

<verification>
Before completing, verify your investigation covers:
- ✓ Identified the exact code path for /api/occupation/completar
- ✓ Listed ALL validation checks that return 422
- ✓ Explained the business logic behind the failing validation
- ✓ Provided hypothesis for why TEST-02 completion failed
- ✓ NO solutions or fixes proposed (investigation only)
</verification>

<success_criteria>
- Root cause identified with specific code references
- Clear understanding of which validation rule triggered the 422
- Logical hypothesis explaining the error for this specific case
- Investigation report saved to ./investigations/completar-error-422-analysis.md
- All relevant code paths examined (router → services → state machines → repositories)
</success_criteria>
