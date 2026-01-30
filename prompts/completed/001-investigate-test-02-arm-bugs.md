<objective>
Investigate and fix critical data recording bugs in the ARM (Armado) action for spool TEST-02.

**Context:** When initiating ARM for TEST-02, several columns in the Operaciones sheet were incorrectly populated, and the Metadata audit trail failed to record the event entirely.

**End Goal:** Identify root causes, implement fixes, and verify correct data recording according to v3.0 specifications.
</objective>

<context>
**Project:** ZEUES v3.0 - Real-time location tracking system
**Tech Stack:** FastAPI + Google Sheets + Redis + python-statemachine 2.5.0
**Relevant Files:**
- @backend/services/state_service.py - State machine orchestration
- @backend/services/occupation_service.py - TOMAR/PAUSAR/COMPLETAR logic
- @backend/repositories/sheets_repository.py - Google Sheets writes
- @backend/repositories/metadata_repository.py - Audit trail writes
- @backend/utils/date_formatter.py - Timezone formatting utilities
- @CLAUDE.md - Project standards and conventions

**Data Model:**
- Operaciones Sheet (67 columns): Columns 64-67 added in v3.0
- Metadata Sheet (10 columns): Event sourcing audit trail
- Timezone: America/Santiago (Chile)
</context>

<bug_report>
**Action Performed:** Initiated ARM for spool TEST-02 using worker MR(93)

**Operaciones Sheet Results:**

✅ CORRECT:
- Column 64 `Ocupado_Por`: "MR(93)"
- Column [Armador]: "MR(93)"
- Column 67 `Estado_Detalle`: "MR(93) trabajando ARM (ARM en progreso, SOLD pendiente)"

❌ INCORRECT:
- Column 65 `Fecha_Ocupacion`: "2026-01-30" (wrong format, should be "30-01-2026 HH:MM:SS")
- Column 66 `version`: "5902a559-2de3-4743-a8cd-013bb39164c2" (should be version 3.0, not UUID)

**Metadata Sheet Results:**

❌ CRITICAL: No event record created (completely missing)
</bug_report>

<investigation_requirements>
Thoroughly investigate each bug with systematic analysis:

1. **Date Format Bug (Column 65)**
   - Trace the code path from TOMAR endpoint → occupation_service → sheets_repository
   - Verify `date_formatter.py` usage: `format_datetime_for_sheets(now_chile())`
   - Check if wrong formatter being used (e.g., `format_date_for_sheets()` instead of `format_datetime_for_sheets()`)
   - Expected format: "DD-MM-YYYY HH:MM:SS" (e.g., "30-01-2026 14:30:00")
   - WHY this matters: Audit compliance requires precise timestamps with time component

2. **Version Field Bug (Column 66)**
   - Determine what "version 3.0" means in user's expectation
   - Verify if `version` column should store:
     - Application version string ("3.0")?
     - UUID4 for optimistic locking (current behavior)?
   - Check CLAUDE.md and PROJECT.md for v3.0 specifications
   - If UUID is correct, explain to user why (optimistic locking)
   - If string version is expected, identify where conversion happens

3. **Missing Metadata Event (CRITICAL)**
   - Trace TOMAR workflow: Does it call `metadata_repository.record_event()`?
   - Check for exceptions/errors swallowed silently
   - Verify metadata_repository implementation
   - Check backend logs for failed writes
   - WHY this matters: Regulatory compliance - audit trail is mandatory and immutable

4. **Root Cause Analysis**
   - Are bugs in same function/file (shared root cause)?
   - Recent changes that could have introduced regressions?
   - Missing test coverage for these paths?
</investigation_requirements>

<implementation>
For each confirmed bug:

1. **Read source code** to understand current implementation
2. **Identify exact line(s)** causing the issue
3. **Implement fix** following project conventions:
   - Use `format_datetime_for_sheets(now_chile())` for timestamps
   - Use dynamic header mapping: `headers["Fecha_Ocupacion"]` NOT `row[64]`
   - Ensure metadata writes are not wrapped in try/except that swallows errors
   - Follow Clean Architecture: Services call repositories, not direct Sheets access

4. **Add defensive checks**:
   - Log metadata writes for debugging
   - Validate date format before writing
   - Add error handling that surfaces failures, not hides them

5. **Verify against v3.0 standards** from CLAUDE.md
</implementation>

<verification>
Before declaring complete, verify your fixes:

1. **Read the corrected code** and confirm:
   - `format_datetime_for_sheets(now_chile())` used for Fecha_Ocupacion
   - `version` field purpose clarified (UUID or string?)
   - `metadata_repository.record_event()` called in TOMAR flow
   - No silent exception handling around metadata writes

2. **Check test coverage**:
   - Do existing tests cover these code paths?
   - Should new tests be added to prevent regression?

3. **Explain to user**:
   - Root cause of each bug
   - Whether `version` field UUID is correct behavior or bug
   - Confirmation that metadata event will now be recorded
</verification>

<output>
**Investigation Report:**
Create `./DEBUG-TEST-02-ARM-FINDINGS.md` with:

1. **Bug #1: Date Format**
   - Root cause: [specific file:line]
   - Fix applied: [code change]
   - Verification: [how to confirm fix works]

2. **Bug #2: Version Field**
   - Analysis: [is UUID correct or wrong?]
   - Root cause: [if bug, specific file:line]
   - Fix applied: [code change or explanation why current behavior is correct]

3. **Bug #3: Missing Metadata**
   - Root cause: [specific file:line]
   - Fix applied: [code change]
   - Verification: [how to confirm metadata writes]

**Code Changes:**
- Modify relevant files with Edit tool
- Add comments explaining critical sections
- Follow CLAUDE.md conventions (never use `datetime.now()`, always use Chile timezone utilities)

**Testing Recommendation:**
- List manual test steps to reproduce and verify fix
- Suggest automated tests to add (if applicable)
</output>

<success_criteria>
- All three bugs have root causes identified with specific file:line references
- Fixes implemented following v3.0 conventions from CLAUDE.md
- Investigation report saved to ./DEBUG-TEST-02-ARM-FINDINGS.md
- User understands whether `version` UUID is correct behavior or bug
- Metadata event recording path verified and fixed if broken
- Date formatting uses correct `format_datetime_for_sheets()` utility
</success_criteria>