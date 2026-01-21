<objective>
Remove the ownership restriction that currently prevents workers from completing or canceling actions started by other workers.

Currently: Only the worker who initiated an action (e.g., worker 93 starts ARM) can complete or cancel that same action.

Target behavior: Any worker with the correct role (Armador for ARM, Soldador for SOLD, Metrologia for METROLOGIA) can complete or cancel actions started by any other worker with that role.

This change improves operational flexibility in the manufacturing floor, allowing team members to help each other complete tasks while maintaining full audit trails in the Metadata sheet.
</objective>

<context>
This is the ZEUES v2.1 manufacturing traceability system with:
- Backend: Python + FastAPI + gspread
- Architecture: Direct Read/Write (v2.1) - reads state from Operaciones columns, writes audit events to Metadata
- Multi-role system: Workers can have multiple roles (Armador, Soldador, Metrologia)
- Operations: ARM (Assembly), SOLD (Welding), METROLOGIA (Quality Inspection)

The ownership restriction is currently enforced in the ValidationService, specifically in methods like:
- `validar_puede_completar_arm()` - checks if worker_nombre matches the armador in Operaciones sheet
- `validar_puede_completar_sold()` - checks if worker_nombre matches the soldador in Operaciones sheet
- `validar_puede_cancelar_arm()` - checks ownership before allowing cancellation
- `validar_puede_cancelar_sold()` - checks ownership before allowing cancellation

Read the following files to understand current implementation:
@./backend/services/validation_service.py
@./tests/unit/test_validation_service.py
@./tests/unit/test_validation_service_cancelar.py
@./backend/models/spool.py
@./backend/models/worker.py
@./CLAUDE.md
</context>

<requirements>
1. **Remove ownership validation**: Modify ValidationService to ONLY check:
   - Worker has the correct role for the operation (Armador for ARM, Soldador for SOLD)
   - Spool is in the correct state for the action (e.g., EN_PROGRESO for COMPLETAR)
   - Do NOT check if worker_nombre matches the worker who started the action

2. **Preserve state validation**: Keep all existing state checks:
   - COMPLETAR requires action to be EN_PROGRESO (not PENDIENTE or COMPLETADO)
   - CANCELAR requires action to be EN_PROGRESO (can't cancel if not started or already completed)
   - Prerequisites still apply (e.g., Fecha_Materiales required for ARM INICIAR)

3. **Audit trail preservation**: NO changes needed to Metadata schema:
   - Each Metadata record already captures the worker (worker_id, worker_nombre) who performed that specific action
   - INICIAR event shows who started → worker_id/worker_nombre of starter
   - COMPLETAR event shows who completed → worker_id/worker_nombre of completer
   - CANCELAR event shows who canceled → worker_id/worker_nombre of canceler
   - This provides full audit trail without schema changes

4. **Apply to all operations**: Remove ownership restriction for ARM, SOLD, and METROLOGIA

5. **Update tests**: Modify existing tests in:
   - `tests/unit/test_validation_service.py` - Remove or update tests that expect NoAutorizadoError for cross-worker completion
   - `tests/unit/test_validation_service_cancelar.py` - Update cancellation tests to allow any worker with correct role
   - Ensure all 244 tests continue to pass after changes

6. **Error handling**: Remove NoAutorizadoError raises related to ownership checks, but keep them for:
   - Role validation (worker doesn't have required role)
   - Invalid state transitions
</requirements>

<implementation>
Step-by-step approach:

1. **Modify ValidationService** (`./backend/services/validation_service.py`):
   - In `validar_puede_completar_arm()`: Remove the check `if spool.armador != worker_nombre: raise NoAutorizadoError(...)`
   - In `validar_puede_completar_sold()`: Remove the check `if spool.soldador != worker_nombre: raise NoAutorizadoError(...)`
   - In `validar_puede_cancelar_arm()`: Remove ownership validation, keep only state validation
   - In `validar_puede_cancelar_sold()`: Remove ownership validation, keep only state validation
   - Keep role validation - ensure worker has the correct role for the operation

2. **Update test files**:
   - `tests/unit/test_validation_service.py`:
     - Remove or modify tests like `test_validar_puede_completar_arm_different_worker_raises_error`
     - Update tests that pass different worker names to expect success instead of NoAutorizadoError
   - `tests/unit/test_validation_service_cancelar.py`:
     - Update cancellation tests that check cross-worker scenarios
     - Ensure tests validate role requirements but not ownership

3. **Verify role validation remains**:
   - Confirm that workers still need the appropriate role (from Roles sheet)
   - Role checks should remain in place (this is different from ownership)

4. **Run all tests**: Execute `./venv/bin/pytest tests/unit/ -v --tb=short` to ensure all 244 tests pass

**What NOT to change**:
- Do NOT modify Metadata schema or column structure (audit trail works as-is)
- Do NOT change SheetsRepository or database access layer
- Do NOT modify ActionService orchestration logic
- Do NOT change API endpoints or routers
- Do NOT modify Operaciones sheet structure (Armador/Soldador columns still track who started)
</implementation>

<verification>
Before declaring complete, verify:

1. **Run unit tests**: `./venv/bin/pytest tests/unit/ -v --tb=short`
   - All 244 tests should pass
   - No NoAutorizadoError for cross-worker COMPLETAR/CANCELAR scenarios
   - Role validation tests still pass

2. **Check ValidationService**:
   - Search for remaining ownership checks: `grep -n "!= worker_nombre" backend/services/validation_service.py`
   - Should return no matches (all ownership checks removed)

3. **Verify role validation remains**:
   - Confirm workers without correct role still cannot perform actions
   - Check tests that validate role requirements still pass

4. **Test audit trail** (optional manual verification):
   - Worker 93 INICIAR ARM → Metadata shows worker_id=93
   - Worker 94 COMPLETAR ARM → Metadata shows worker_id=94
   - Both records exist independently in Metadata

5. **Code review checklist**:
   - [ ] Ownership checks removed from all COMPLETAR methods
   - [ ] Ownership checks removed from all CANCELAR methods
   - [ ] Role validation checks remain intact
   - [ ] State validation checks remain intact (EN_PROGRESO, COMPLETADO, etc.)
   - [ ] All tests pass without errors
   - [ ] No Metadata schema changes (audit works as-is)
</verification>

<output>
Modify the following files:
- `./backend/services/validation_service.py` - Remove ownership validation from COMPLETAR and CANCELAR methods
- `./tests/unit/test_validation_service.py` - Update tests to expect success for cross-worker operations
- `./tests/unit/test_validation_service_cancelar.py` - Update cancellation tests

No new files should be created.
</output>

<success_criteria>
- All 244 unit tests pass: `./venv/bin/pytest tests/unit/ --tb=short`
- Worker A can COMPLETAR/CANCELAR actions started by Worker B (if both have same role)
- Workers without correct role still cannot perform actions (role validation intact)
- State validation remains (can't complete PENDIENTE action, can't cancel COMPLETADO action)
- Metadata audit trail works correctly (each action record shows the worker who performed it)
- No NoAutorizadoError raised for ownership mismatch, only for role mismatch
- Code is clean: no commented-out ownership checks, clear git diff showing removed validations
</success_criteria>
Completed: Tue Jan 20 23:13:46 -03 2026
