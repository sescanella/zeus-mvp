<objective>
Investigate critical bugs in the PAUSAR ARM workflow for spool TEST-02 where Estado_Detalle displays incorrect state and Metadata events are not being logged.

This investigation is critical because PAUSAR is a core v3.0 feature enabling collaborative workflows. Workers rely on Estado_Detalle to understand spool availability, and Metadata logging is a regulatory requirement for audit trails.
</objective>

<context>
**Observed Behavior (spool TEST-02 after PAUSAR ARM):**
- ✓ `Armador` column: Remained as MR(93) (EXPECTED - worker who initiated ARM should persist)
- ✓ `Ocupado_Por` (col 64): Cleared from MR(93) to empty (CORRECT - spool released)
- ✓ `Fecha_Ocupacion` (col 65): Cleared to empty (CORRECT - occupation timestamp removed)
- ✗ `Estado_Detalle` (col 67): Shows "Disponible - ARM pendiente, SOLD pendiente" (INCORRECT)
- ✗ Metadata sheet: No event logged (CRITICAL BUG - audit trail missing)

**Expected Behavior:**
- `Estado_Detalle` should show: "ARM_PAUSADO" or "PAUSADO - ARM iniciado, SOLD pendiente"
- Metadata should contain event: `PAUSAR_SPOOL` with operacion=ARM, accion=PAUSAR

**System Context:**
- ZEUES v3.0 real-time occupation tracking system
- Backend: Python FastAPI + Google Sheets + Redis
- State machines: Separate ARM/SOLD machines (python-statemachine 2.5.0)
- Estado_Detalle builder: `EstadoDetalleBuilder` combines occupation + ARM + SOLD states
- Metadata: Event Sourcing audit trail (append-only, regulatory requirement)

Read CLAUDE.md for full project architecture and conventions.
</context>

<investigation_scope>
**Primary Investigation Areas:**

1. **Estado_Detalle Generation Logic**
   - File: `backend/services/estado_detalle_service.py` or similar
   - Component: `EstadoDetalleBuilder` class
   - Question: How does it determine state when ARM is PAUSADO?
   - Hypothesis: Builder may not recognize ARM_PAUSADO state from ARM state machine

2. **PAUSAR ARM Workflow**
   - File: `backend/services/occupation_service.py` → `pausar_spool()` method
   - File: `backend/state_machines/arm_state_machine.py` → `pausar` transition
   - Question: Does state machine callback update Estado_Detalle correctly?
   - Question: Is Estado_Detalle updated AFTER state transition?

3. **Metadata Logging**
   - File: `backend/repositories/metadata_repository.py` → `log_occupation_event()`
   - File: `backend/services/occupation_service.py` → metadata logging call
   - Question: Is `log_metadata()` being called in pausar_spool()?
   - Question: Are there try/except blocks swallowing errors silently?
   - Question: Is evento_tipo correct? (should be `EventoTipo.PAUSAR_SPOOL`)

4. **State Machine Callbacks**
   - File: `backend/state_machines/arm_state_machine.py`
   - Question: Does `on_pausar()` callback exist?
   - Question: Does it call `EstadoDetalleBuilder` to regenerate Estado_Detalle?
   - Question: Does it update Google Sheets with new Estado_Detalle value?

**Files to Examine:**
@backend/services/occupation_service.py
@backend/state_machines/arm_state_machine.py
@backend/services/estado_detalle_service.py
@backend/repositories/metadata_repository.py
@backend/repositories/sheets_repository.py
</investigation_scope>

<investigation_process>
**Step 1: Map the Expected Flow**

Thoroughly trace what SHOULD happen when `pausar_spool()` is called:

1. Validate spool is occupied by worker
2. Load ARM state machine and hydrate to current state
3. Trigger `arm_machine.pausar()` transition
4. State machine callback should:
   - Clear Ocupado_Por, Fecha_Ocupacion
   - Regenerate Estado_Detalle using EstadoDetalleBuilder
   - Update Google Sheets row with new Estado_Detalle
5. Log Metadata event (PAUSAR_SPOOL)
6. Publish Redis SSE event
7. Release Redis lock

Document this expected flow explicitly.

**Step 2: Identify Deviations**

For each step in the expected flow, check the actual implementation:

- Read `occupation_service.py::pausar_spool()` method
- Read `arm_state_machine.py` transitions and callbacks
- Read `EstadoDetalleBuilder` state detection logic
- Look for missing steps, incorrect event types, swallowed exceptions

**Step 3: Root Cause Analysis**

For Estado_Detalle bug:
- Does `EstadoDetalleBuilder` have logic for ARM_PAUSADO state?
- Is the builder called AFTER the state machine transition?
- Is the generated Estado_Detalle written to Sheets?
- Check if Estado_Detalle is being overwritten by a default "Disponible" value

For Metadata bug:
- Search for `log_metadata` or `log_occupation_event` calls in pausar_spool()
- Check if metadata logging is wrapped in try/except that silently fails
- Verify evento_tipo value (should be EventoTipo.PAUSAR_SPOOL)
- Check if metadata_repo method signature matches the call

**Step 4: Cross-Reference with Working Code**

Compare PAUSAR implementation with TOMAR and COMPLETAR:
- How does `tomar_spool()` log metadata? (should be similar pattern)
- How does `completar_spool()` update Estado_Detalle? (should use same builder)
- Look for patterns that work in TOMAR/COMPLETAR but are missing in PAUSAR

**Step 5: Check Tests**

Examine existing tests for PAUSAR workflow:
- Search for test files: `tests/integration/test_occupation*.py`
- Look for test cases validating Estado_Detalle after PAUSAR
- Look for test cases validating Metadata events for PAUSAR
- If tests exist and pass, investigate why production behavior differs
- If tests are missing, note this as a gap
</investigation_process>

<deliverable>
Create a detailed investigation report: `./investigations/pausar-arm-bug-report.md`

**Required Sections:**

1. **Executive Summary**
   - Brief description of the two bugs (Estado_Detalle + Metadata)
   - Impact assessment (user confusion, regulatory compliance)

2. **Expected vs Actual Behavior**
   - Side-by-side comparison table
   - Include column values, event logging

3. **Root Cause Analysis**

   For EACH bug, provide:
   - File and line number where the bug originates
   - Code snippet showing the problematic code
   - Explanation of WHY this causes the observed behavior
   - Link to related code that works correctly (TOMAR/COMPLETAR)

4. **Detailed Findings**

   Answer these questions explicitly:
   - Is `EstadoDetalleBuilder` called after ARM state machine transition in PAUSAR?
   - Does `EstadoDetalleBuilder` have logic to handle ARM_PAUSADO state?
   - Is `log_metadata()` or `log_occupation_event()` called in `pausar_spool()`?
   - What is the evento_tipo value being passed (if any)?
   - Are there any try/except blocks silently swallowing errors?

5. **Fix Strategy**

   For EACH bug, provide:
   - What needs to be changed (specific file, method, lines)
   - Pseudocode or code snippet showing the fix
   - Any side effects or dependencies to consider
   - Testing approach to validate the fix

6. **Test Coverage Gap Analysis**

   - Which test cases exist for PAUSAR workflow?
   - Which test cases are MISSING that would have caught these bugs?
   - Recommendations for new test cases

7. **Comparison with Working Code**

   - Show how TOMAR handles Estado_Detalle (working reference)
   - Show how COMPLETAR handles Metadata logging (working reference)
   - Highlight what PAUSAR is doing differently

8. **Next Steps**

   Prioritized action items:
   1. Fix Estado_Detalle generation
   2. Fix Metadata logging
   3. Add missing test cases
   4. Verify fix with TEST-02 spool
</deliverable>

<constraints>
- **DO NOT FIX THE CODE YET** - This is investigation only, not implementation
- Focus on understanding ROOT CAUSES, not symptoms
- Provide file paths and line numbers for all findings
- Use code snippets to illustrate problems clearly
- Cross-reference with working code (TOMAR/COMPLETAR) extensively
- If you discover additional related bugs, document them too
</constraints>

<success_criteria>
Before declaring investigation complete, verify:

✓ Both bugs (Estado_Detalle + Metadata) have identified root causes
✓ Each root cause includes file path, line number, and code snippet
✓ Fix strategy is specific and actionable (not vague recommendations)
✓ Working code examples are provided for comparison
✓ Test coverage gaps are identified with specific test case recommendations
✓ Report is saved to ./investigations/pausar-arm-bug-report.md
✓ Report answers ALL questions in "Detailed Findings" section explicitly

The investigation is complete when another developer can implement the fixes based solely on your report without re-investigating.
</success_criteria>

<verification>
After completing the report, perform this self-check:

1. Re-read the "Observed Behavior" section at the top
2. Verify your root cause analysis explains EXACTLY why Estado_Detalle shows "Disponible - ARM pendiente, SOLD pendiente"
3. Verify your root cause analysis explains EXACTLY why Metadata event is missing
4. Check that you've provided file:line references for all bugs
5. Confirm fix strategy is concrete, not abstract

If any verification step fails, continue investigation until all criteria are met.
</verification>
