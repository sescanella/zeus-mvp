<objective>
Investigate the root cause of the Error 400 (Bad Request) occurring when attempting to PAUSAR a spool in the ARMADO operation.

DO NOT fix the issue - only investigate and document findings.

Context: User is getting "Error 400" when clicking "CONFIRMAR 1 SPOOL" to pause spool TEST-02 in ARMADO operation. The error occurs in production (Railway backend), but the problem is confirmed to NOT be Railway-specific.
</objective>

<context>
- **User flow:** Worker MR(93) → ARMADO operation → PAUSAR action → Spool TEST-02 selected → Confirmation page → Error 400
- **Failed request:** `POST https://zeues-backend-mvp-production.up.railway.app/api/occupation/pausar`
- **Response:** `400 (Bad Request)`
- **Frontend error:** `pausarOcupacion error: Error: Error 400:`
- **Environment:** Production (Vercel frontend + Railway backend)
- **Recent commits:** Several PAUSAR-related fixes (see git log)

This is v3.0 codebase. Reference CLAUDE.md for architecture.
</context>

<investigation_scope>
Thoroughly analyze and document:

1. **Request validation chain:**
   - What does `/api/occupation/pausar` endpoint expect?
   - What is the frontend sending in the request payload?
   - Where does validation fail and why does it return 400?

2. **Frontend-backend contract:**
   - Examine `zeues-frontend/lib/api.ts` pausarOcupacion function
   - Check request payload structure (PausarRequest schema)
   - Identify any missing or incorrectly formatted fields

3. **Backend validation logic:**
   - Review `backend/routers/occupation.py` PAUSAR endpoint
   - Check Pydantic schema validation (PausarRequest model)
   - Identify which field(s) are causing the 400 Bad Request

4. **Recent regression analysis:**
   - Review git history for recent PAUSAR changes
   - Check if recent fixes introduced new validation requirements
   - Compare with TOMAR/COMPLETAR flows (do they work?)

5. **State prerequisites:**
   - Does PAUSAR require specific spool state?
   - Is there occupation lock validation failing?
   - Are there worker-spool relationship checks?
</investigation_scope>

<required_files>
Examine these files to trace the request flow:

Frontend:
- `zeues-frontend/lib/api.ts` - pausarOcupacion function
- `zeues-frontend/app/confirmar/page.tsx` - Where error occurs
- `zeues-frontend/lib/types.ts` - PausarRequest interface

Backend:
- `backend/routers/occupation.py` - PAUSAR endpoint
- `backend/models/requests.py` - PausarRequest Pydantic model
- `backend/services/occupation_service.py` - pausar_spool logic
- `backend/services/validation_service.py` - Validation rules

Recent changes:
- Run: `git log --oneline --grep="PAUSAR\|pausar" -10`
- Check commits: ac64c55, 8143499, 3b51b2f, f029975, 9eb246c
</required_files>

<investigation_process>
1. **Trace the request path:**
   - Start at frontend: What payload is being sent?
   - Follow to backend: What validation is rejecting it?
   - Identify exact validation rule that returns 400

2. **Compare with working flows:**
   - Does TOMAR work with same spool/worker?
   - Does COMPLETAR work?
   - What's different about PAUSAR?

3. **Check git history:**
   - When was this last working?
   - What changed between working and broken state?
   - Were new required fields added?

4. **Examine error handling:**
   - Is the 400 response providing detail?
   - Check FastAPI validation error responses
   - Look for HTTPException(400) raises

5. **Document hypothesis:**
   - Form 2-3 hypotheses about root cause
   - Rank by likelihood based on evidence
   - Note what additional tests would confirm each
</investigation_process>

<output>
Create a detailed investigation report at: `./investigations/pausar-400-error-analysis.md`

Include:

## Error Summary
- What: [Exact error message and HTTP status]
- When: [User action that triggers it]
- Where: [Request path, endpoint, line numbers]

## Request Flow Analysis
- **Frontend payload:** [Show actual request structure]
- **Expected backend schema:** [Show Pydantic model]
- **Validation failure point:** [Exact location and reason]

## Root Cause Hypotheses
Ranked by likelihood:

1. **[Most likely cause]**
   - Evidence: [Code references, line numbers]
   - Reasoning: [Why this is likely]
   - Test to confirm: [How to verify]

2. **[Second possibility]**
   - Evidence: [...]
   - Reasoning: [...]
   - Test to confirm: [...]

3. **[Third possibility]**
   - Evidence: [...]
   - Reasoning: [...]
   - Test to confirm: [...]

## Recent Changes Impact
- [List relevant commits and their effect]
- [Identify if regression was introduced]

## Comparison with Working Flows
- [How TOMAR differs from PAUSAR]
- [Why TOMAR works but PAUSAR fails]

## Next Steps for Fix
- [What needs to change to resolve - but don't implement]
- [Which files would need modification]
- [Recommended testing approach]

## References
- File paths with line numbers
- Git commit SHAs
- Relevant documentation
</output>

<constraints>
- **DO NOT fix the issue** - investigation only
- **DO NOT modify any code files** - read-only analysis
- Use Read tool extensively to examine code
- Use Bash for git log commands only
- Include specific line numbers in findings
- Provide evidence for each hypothesis
</constraints>

<verification>
Before completing, ensure:
- ✓ Request payload structure is documented
- ✓ Validation failure point is identified with line numbers
- ✓ At least 2-3 hypotheses are ranked by likelihood
- ✓ Evidence includes specific file paths and line numbers
- ✓ Report is saved to ./investigations/pausar-400-error-analysis.md
- ✓ Next steps for fix are outlined (but not implemented)
</verification>

<success_criteria>
- Root cause identified with specific file:line reference
- Clear explanation of WHY the 400 error occurs
- Ranked hypotheses with supporting evidence
- Actionable next steps for the developer to fix
- No code modifications made (investigation only)
</success_criteria>
