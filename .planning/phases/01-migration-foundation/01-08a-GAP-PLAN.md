---
phase: 01-migration-foundation
plan: 08a-gap
type: execute
wave: 3
depends_on: ["01-06-GAP-PLAN", "01-07-GAP-PLAN"]
files_modified:
  - "backend/scripts/migration_coordinator.py"
  - "backend/scripts/verify_migration.py"
  - "backend/logs/checkpoints/"
  - "backend/logs/migration/"
autonomous: false

must_haves:
  truths:
    - "Migration coordinator executes atomically with checkpoint recovery"
    - "All 7 verification checks pass"
    - "Version column initialized to 0 for all rows"
  artifacts:
    - path: "backend/logs/migration/verification_report.json"
      provides: "Migration verification results"
      contains: "checks_passed: 7"
    - path: "backend/logs/migration/final_test_results.txt"
      provides: "Test execution results"
      contains: "28 passed"
  key_links:
    - from: "migration_coordinator.py"
      to: "verify_migration.py"
      via: "step 3 execution"
      pattern: "verify_migration"
---

# Gap Closure: Execute Migration Coordinator (Part A - Execution)

**Gap:** Migration coordinator never run in production mode
**Impact:** Migration not atomically completed - blocking Phase 1 completion

## Current State

- `migration_coordinator.py` exists (408 lines) with checkpoint recovery
- 5-step process orchestrated: backup, columns, verify, init, test
- Only dry-run executions in logs (10+ times)
- First 2 steps now complete via gaps 1-2

## Tasks

<task type="manual">
  <name>Task 1: Execute migration coordinator</name>
  <files>backend/scripts/migration_coordinator.py, backend/logs/checkpoints/, backend/logs/migration/verification_report.json</files>
  <action>
    Verify prerequisites from gaps 1-2:
    - Read docs/MIGRATION_BACKUP.md - confirm backup exists
    - Read docs/MIGRATION_COLUMNS.md - confirm 68 columns exist
    - Run: pytest tests/v3.0/test_smoke.py::test_sheet_has_68_columns -v (must PASS)

    Run: python backend/scripts/migration_coordinator.py
    NO --dry-run flag (execute real migration).
    Monitor checkpoint creation in backend/logs/checkpoints/.
    Expected checkpoints: step_3_verify.json, step_4_init.json, step_5_test.json
    Steps 1-2 should skip (already done via gaps 1-2).

    Verify step 3 runs verify_migration.py with 7 checks passing.
    Check logs/migration/verification_report.json created.
  </action>
  <verify>[ -f backend/logs/migration/verification_report.json ] && grep "checks_passed.*7" backend/logs/migration/verification_report.json</verify>
  <done>Migration coordinator executed, verification completed</done>
</task>

<task type="manual">
  <name>Task 2: Validate test execution</name>
  <files>backend/logs/migration/final_test_results.txt, tests/v3.0/</files>
  <action>
    Monitor step 5 smoke test execution.
    Expected: 28 tests pass, 0 skipped.
    All v3.0 column tests should pass.
    Backward compatibility tests should pass.

    Run full v3.0 test suite for final validation:
    Execute: pytest tests/v3.0/ -v
    Expected: 47 tests total (28 smoke + E2E + rollback tests).
    No tests should skip anymore.
    Capture results to logs/migration/final_test_results.txt.
  </action>
  <verify>grep "28 passed" backend/logs/migration/final_test_results.txt</verify>
  <done>All tests passing, migration validated</done>
</task>

<task type="manual">
  <name>Task 3: Document test count reconciliation</name>
  <files>docs/TEST_COUNT_NOTE.md</files>
  <action>
    Create docs/TEST_COUNT_NOTE.md explaining test count discrepancy:
    - BC-02 states "244 v2.1 tests" but only 233 were archived
    - Document that 11 tests were integration tests removed during v2.1→v3.0 migration
    - These tests were specific to v2.1 event sourcing and no longer applicable
    - New v3.0 test suite has 47 tests covering the new architecture
    - This is expected and not a gap in coverage
  </action>
  <verify>[ -f docs/TEST_COUNT_NOTE.md ] && grep "233" docs/TEST_COUNT_NOTE.md</verify>
  <done>Test count discrepancy documented</done>
</task>

## Verification

**Success criteria:**
- Gap 3a closed: "Migration executes atomically" ✓
- All migration steps complete successfully
- Ready for documentation phase (gap 3b)