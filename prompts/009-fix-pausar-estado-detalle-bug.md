<objective>
Fix Bug 1: Estado_Detalle shows "Disponible - ARM pendiente, SOLD pendiente" instead of "ARM_PAUSADO" after PAUSAR ARM operation.

This fix is critical for manufacturing floor visibility - workers rely on Estado_Detalle to understand which spools are available vs paused. Incorrect state display causes confusion and blocks collaborative workflows where workers continue partially-completed work.

This prompt follows an iterative workflow: design implementation plan → critique the plan → convert critique to actionable feedback → apply feedback → implement fix → run tests → verify bug is resolved.
</objective>

<context>
Read the complete investigation report: @investigations/pausar-arm-bug-report.md

**Bug Summary (from investigation):**
- **What:** Estado_Detalle shows "Disponible - ARM pendiente, SOLD pendiente" after PAUSAR ARM (should show "ARM_PAUSADO" or similar)
- **Where:**
  - `backend/state_machines/arm_state_machine.py:34-42` - Missing pausado state
  - `backend/services/estado_detalle_builder.py:62-68` - No paused detection logic
- **Root Cause:** ARM state machine has NO pausado state; EstadoDetalleBuilder can't detect paused scenario (Armador exists, Ocupado_Por cleared)
- **Impact:** Workers see incorrect availability status on tablet, causing manufacturing floor confusion

**Technical Context:**
- ZEUES v3.0 uses hierarchical state machines (python-statemachine 2.5.0)
- Separate ARM/SOLD state machines to prevent state explosion (6 states vs 27)
- EstadoDetalleBuilder combines occupation + ARM + SOLD states into human-readable display
- Estado_Detalle column (67) shown on worker tablets for real-time status
- Current ARM states: pendiente → en_progreso → completado (NO pausado state)

**Investigation recommends two approaches:**
1. **State Machine Approach:** Add pausado state to ARM/SOLD machines (comprehensive, aligned with architecture)
2. **Heuristic Approach:** Detect paused via EstadoDetalleBuilder (simpler, less invasive)

Read CLAUDE.md for full project architecture and conventions.
</context>

<iterative_workflow>

## Phase 1: Design Implementation Plan

Thoroughly analyze the investigation report and design a detailed implementation plan.

**Your plan must address:**

1. **Approach Selection**
   - State Machine Approach: Add pausado state to ARMStateMachine and SOLDStateMachine
   - Heuristic Approach: Add paused detection logic to EstadoDetalleBuilder
   - Hybrid: Combine both approaches
   - **Decision criteria:** Architectural consistency, complexity, maintainability, test coverage

2. **If State Machine Approach:**
   - Add `pausado` state to ARMStateMachine (pendiente → en_progreso → pausado → en_progreso → completado)
   - Add `pausado` state to SOLDStateMachine (same pattern)
   - Add `pausar` transition that moves en_progreso → pausado
   - Add `reanudar` transition that moves pausado → en_progreso
   - Update StateService.pausar() to trigger state machine transition BEFORE clearing occupation
   - Update on_pausar() callback to clear Ocupado_Por and regenerate Estado_Detalle
   - Update EstadoDetalleBuilder to recognize pausado state

3. **If Heuristic Approach:**
   - Add logic to EstadoDetalleBuilder.build()
   - Detect paused: Armador exists + Ocupado_Por is None + Fecha_Armado is None
   - Similarly for SOLD: Soldador exists + Ocupado_Por is None + Fecha_Soldadura is None
   - Return "ARM_PAUSADO" or "PAUSADO - ARM iniciado, SOLD pendiente"

4. **Estado_Detalle Display Format:**
   - Design human-readable format (e.g., "PAUSADO - ARM iniciado, SOLD pendiente")
   - Ensure consistency with existing format patterns
   - Consider i18n if needed

5. **Testing Strategy:**
   - Test that PAUSAR ARM updates Estado_Detalle to "ARM_PAUSADO"
   - Test that PAUSAR SOLD updates Estado_Detalle to "SOLD_PAUSADO"
   - Test that resuming (TOMAR again) returns to "en_progreso"
   - Test edge cases (what if both ARM and SOLD paused?)

**Deliverable:** Write your initial plan to `./implementation-plans/bug1-estado-detalle-plan-v1.md`

Include:
- Chosen approach with justification
- Specific files and line numbers to modify
- Code changes with before/after snippets
- Estado_Detalle display format examples
- Test plan with specific test cases
- Migration considerations (existing paused spools in production?)

## Phase 2: Critique the Plan

Act as a senior code reviewer and thoroughly critique your plan from Phase 1.

**Critique dimensions:**

1. **Architectural Consistency:** Does this align with hierarchical state machine design?
2. **Completeness:** Does this handle both ARM and SOLD operations?
3. **Display Clarity:** Is the Estado_Detalle format clear to workers on tablets?
4. **Testing:** Will tests catch all edge cases (resume, both paused, etc.)?
5. **Migration:** What happens to spools currently in paused state in production?
6. **Consistency:** Does this match how TOMAR/COMPLETAR update Estado_Detalle?

**Ask hard questions:**
- "What if we add pausado state but EstadoDetalleBuilder doesn't recognize it?"
- "Should pausado be a sub-state of en_progreso or a separate top-level state?"
- "What happens if worker PAUSES ARM, then PAUSES SOLD - what should Estado_Detalle show?"
- "Does the state machine transition happen BEFORE or AFTER clearing Ocupado_Por?"
- "Will existing integration tests break with state machine changes?"

**Deliverable:** Write critique to `./implementation-plans/bug1-estado-detalle-critique.md`

## Phase 3: Convert Critique to Actionable Feedback

Transform your critique into specific, actionable feedback items.

For EACH issue identified in the critique:
- State the problem clearly
- Propose a concrete solution
- Explain why this solution is better
- Estimate implementation effort (trivial/small/medium/large)
- Flag any breaking changes or migration needs

**Deliverable:** Write feedback to `./implementation-plans/bug1-estado-detalle-feedback.md`

Format as checklist:
- [ ] Issue: [description]
      Solution: [specific action]
      Rationale: [why this improves the plan]
      Effort: [trivial/small/medium/large]
      Breaking: [yes/no - explain if yes]

## Phase 4: Apply Feedback and Refine Plan

Update your original plan by applying the feedback from Phase 3.

**Process:**
1. Read bug1-estado-detalle-plan-v1.md
2. Read bug1-estado-detalle-feedback.md
3. Apply each feedback item to create improved plan
4. Document what changed and why
5. Add migration plan if needed for production spools

**Deliverable:** Write refined plan to `./implementation-plans/bug1-estado-detalle-plan-v2-final.md`

Include changelog section showing:
- What changed from v1 to v2
- Which feedback items were applied
- Any feedback items rejected (with justification)
- Migration strategy for production data (if needed)

## Phase 5: Implement the Fix

Execute the final plan from Phase 4.

**Implementation checklist:**

1. **Activate virtual environment:**
   ```bash
   source venv/bin/activate
   ```

2. **If State Machine Approach:**
   - Modify backend/state_machines/arm_state_machine.py
   - Add pausado state with transitions
   - Modify backend/state_machines/sold_state_machine.py
   - Add pausado state with transitions
   - Update backend/services/state_service.py
   - Trigger state machine transition in pausar() method
   - Update callbacks (on_pausar) to handle Estado_Detalle

3. **If Heuristic Approach:**
   - Modify backend/services/estado_detalle_builder.py
   - Add paused detection logic in build() method
   - Handle both ARM and SOLD paused scenarios

4. **Either Approach:**
   - Update EstadoDetalleBuilder to recognize new states/patterns
   - Ensure human-readable display format
   - Add docstrings explaining paused state logic

5. **Testing:**
   - Add test cases to tests/integration/test_occupation_flow.py
   - Test PAUSAR ARM → Estado_Detalle = "ARM_PAUSADO"
   - Test PAUSAR SOLD → Estado_Detalle = "SOLD_PAUSADO"
   - Test resume (TOMAR after PAUSAR) → Estado_Detalle = "en_progreso"
   - Test edge cases identified in plan

6. **Follow CLAUDE.md conventions:**
   - Maintain Clean Architecture patterns
   - Use proper state machine patterns (python-statemachine 2.5.0)
   - Add comprehensive docstrings

**Files to modify (typical):**
- backend/state_machines/arm_state_machine.py
- backend/state_machines/sold_state_machine.py
- backend/services/estado_detalle_builder.py
- backend/services/state_service.py (if state machine approach)
- tests/integration/test_occupation_flow.py

## Phase 6: Run Tests and Verify

Validate that the fix resolves the bug without introducing regressions.

**Testing sequence:**

1. **Run state machine tests:**
   ```bash
   PYTHONPATH=/Users/sescanella/Proyectos/KM/ZEUES-by-KM pytest tests/unit/test_arm_state_machine.py -v --tb=short
   PYTHONPATH=/Users/sescanella/Proyectos/KM/ZEUES-by-KM pytest tests/unit/test_sold_state_machine.py -v --tb=short
   ```

2. **Run estado_detalle tests:**
   ```bash
   PYTHONPATH=/Users/sescanella/Proyectos/KM/ZEUES-by-KM pytest tests/unit/test_estado_detalle*.py -v --tb=short
   ```

3. **Run integration tests:**
   ```bash
   PYTHONPATH=/Users/sescanella/Proyectos/KM/ZEUES-by-KM pytest tests/integration/test_occupation_flow.py -v --tb=short
   ```

4. **Run full test suite:**
   ```bash
   PYTHONPATH=/Users/sescanella/Proyectos/KM/ZEUES-by-KM pytest tests/ -v
   ```

5. **Manual verification (recommended):**
   - Run backend locally
   - Execute TOMAR ARM on TEST-02 spool
   - Check Estado_Detalle = "ARM en progreso" or similar
   - Execute PAUSAR ARM on TEST-02 spool
   - Check Estado_Detalle = "ARM_PAUSADO" or "PAUSADO - ARM iniciado, SOLD pendiente"
   - Execute TOMAR ARM again (resume)
   - Check Estado_Detalle returns to "ARM en progreso"
   - Execute COMPLETAR ARM
   - Check Estado_Detalle = "ARM completado, SOLD pendiente" or similar

**Success criteria:**
- All new tests pass
- All existing tests still pass (no state machine regressions)
- Estado_Detalle shows correct paused state after PAUSAR
- Estado_Detalle returns to en_progreso after resume (TOMAR after PAUSAR)
- Display format is clear and consistent with existing patterns

</iterative_workflow>

<deliverables>
Create these files during execution:

1. `./implementation-plans/bug1-estado-detalle-plan-v1.md` - Initial implementation plan with approach selection
2. `./implementation-plans/bug1-estado-detalle-critique.md` - Critical review of plan
3. `./implementation-plans/bug1-estado-detalle-feedback.md` - Actionable feedback checklist
4. `./implementation-plans/bug1-estado-detalle-plan-v2-final.md` - Refined plan with changelog
5. Modified code files (state machines, estado_detalle_builder, test files)
6. `./implementation-plans/bug1-estado-detalle-verification.md` - Test results and verification summary
</deliverables>

<constraints>
- **Architectural consistency is paramount** - Must align with hierarchical state machine design
- **Mobile-first display** - Estado_Detalle must be clear on tablet screens for workers
- **Maintain backward compatibility** - Do not break existing state machine transitions
- **Handle both ARM and SOLD** - Solution must work for both operations symmetrically
- **Test coverage mandatory** - Must have tests for pausar, resume, and display format
- **All work in virtual environment** - ALWAYS activate venv before any Python work
- **Do not skip phases** - Complete all 6 phases in order (design → critique → feedback → apply → implement → verify)
- **Consider production migration** - If state machine changes, ensure existing spools migrate cleanly
</constraints>

<success_criteria>
Before declaring complete, verify ALL of these:

✓ All 6 phases completed with deliverables created
✓ bug1-estado-detalle-plan-v2-final.md exists with approach justification and changelog
✓ Code changes made to state machines and/or estado_detalle_builder
✓ Test cases added for PAUSAR → Estado_Detalle validation
✓ Test cases added for resume (TOMAR after PAUSAR) validation
✓ All tests pass (new tests + existing tests)
✓ Estado_Detalle shows "ARM_PAUSADO" or similar after PAUSAR ARM
✓ Estado_Detalle returns to "en_progreso" after resume
✓ Display format is clear and human-readable
✓ Solution handles both ARM and SOLD symmetrically
✓ bug1-estado-detalle-verification.md documents test results and manual verification

**The bug is fixed when:**
- PAUSAR ARM updates Estado_Detalle to paused state (not "Disponible")
- Workers on tablets see clear indication spool is paused
- Resume (TOMAR after PAUSAR) correctly returns to en_progreso state
- Test suite validates this behavior automatically
</success_criteria>

<verification>
Final self-check before declaring success:

1. Re-read the investigation report Bug 1 section
2. Confirm your implementation addresses the root cause (missing pausado state or detection)
3. Verify Estado_Detalle format is clear for manufacturing floor workers
4. Check that solution handles both ARM and SOLD operations
5. Verify test actually validates Estado_Detalle value (not just state machine transition)
6. Confirm all deliverables exist with substantive content
7. Check test results show bug is fixed

If any verification fails, continue work until all criteria met.
</verification>
