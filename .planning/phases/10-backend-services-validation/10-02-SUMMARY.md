# Phase 10 Plan 02: Enhance OccupationService with INICIAR/FINALIZAR Summary

---
phase: 10
plan: 02
subsystem: backend-services
tags: [occupation-service, iniciar, finalizar, auto-determination, union-workflows, v4.0]

requires:
  - 09-01  # RedisLockService with persistent locks
  - 09-02  # Startup reconciliation from Sheets
  - 08-01  # UnionRepository with batch operations

provides:
  - iniciar_spool() method for v4.0 occupation without Uniones touch
  - finalizar_spool() method with PAUSAR/COMPLETAR auto-determination
  - Zero-union cancellation support (release lock without updates)
  - IniciarRequest and FinalizarRequest Pydantic models
  - OccupationResponse with action_taken and unions_processed fields

affects:
  - 10-03  # Validation Service (will use OccupationService methods)
  - 10-04  # Router endpoints (will expose INICIAR/FINALIZAR)

tech-stack:
  added:
    - IniciarRequest model (tag_spool, worker_id, worker_nombre, operacion)
    - FinalizarRequest model (same + selected_unions list)
  patterns:
    - Auto-determination logic (selected vs available comparison)
    - Zero-union cancellation (empty list = CANCELADO)
    - Race condition detection (409 Conflict if union unavailable)

key-files:
  created:
    - tests/unit/services/test_occupation_service_v4.py (13 tests)
  modified:
    - backend/models/occupation.py (IniciarRequest, FinalizarRequest, enhanced OccupationResponse)
    - backend/services/occupation_service.py (iniciar_spool, finalizar_spool, _determine_action)

decisions:
  - D56: INICIAR uses same TOMAR_SPOOL event type as v3.0 (backward compatibility)
  - D57: FINALIZAR auto-determines PAUSAR vs COMPLETAR (simplifies UX)
  - D58: Empty selected_unions list triggers cancellation (no 409 error)
  - D59: UnionRepository injected as optional dependency (v3.0 backward compat)
  - D60: Race condition returns 409 Conflict (not silent failure)

metrics:
  duration: 4.4 min
  completed: 2026-02-02
---

## One-liner

v4.0 occupation workflows (INICIAR/FINALIZAR) with auto-determination and zero-union cancellation support

## Narrative

### What Was Built

Enhanced OccupationService with v4.0 INICIAR/FINALIZAR operations that support union-level workflows with intelligent auto-determination of PAUSAR vs COMPLETAR actions.

**Key Components:**

1. **IniciarRequest and FinalizarRequest Models** (Task 1)
   - IniciarRequest: tag_spool, worker_id, worker_nombre, operacion
   - FinalizarRequest: same fields + selected_unions list (empty = cancellation)
   - OccupationResponse: added action_taken and unions_processed fields

2. **iniciar_spool() Method** (Task 2)
   - Validates spool exists and has Fecha_Materiales prerequisite
   - Acquires persistent Redis lock (no TTL) via RedisLockService
   - Updates Ocupado_Por and Fecha_Ocupacion in Operaciones sheet
   - Logs TOMAR_SPOOL event to Metadata (same as v3.0 TOMAR)
   - **CRITICAL:** Does NOT touch Uniones sheet at all
   - Full rollback on version conflict or Sheets failure

3. **finalizar_spool() Method with Auto-determination** (Tasks 3-5)
   - Validates worker owns the spool (check Redis lock)
   - Gets fresh union totals from UnionRepository
   - Calculates action: PAUSAR (partial) or COMPLETAR (full) based on selected vs total
   - Zero-union cancellation: empty list releases lock without touching Uniones
   - Batch updates Uniones sheet via UnionRepository
   - Releases Redis lock and clears Ocupado_Por
   - Logs appropriate event (PAUSAR_SPOOL or COMPLETAR_ARM/SOLD)
   - Returns action_taken and unions_processed in response

4. **Auto-determination Helper** (Task 4)
   - `_determine_action()`: Compares selected count vs total available
   - Independent evaluation for ARM and SOLD operations
   - Returns "PAUSAR" or "COMPLETAR" based on comparison
   - Raises 409 Conflict if union became unavailable (race condition)

5. **Comprehensive Unit Tests** (Task 6)
   - 13 tests covering all INICIAR/FINALIZAR scenarios
   - Mock-based tests with UnionRepository, RedisLockService, etc.
   - Tests for success cases, error cases, ownership validation, race conditions
   - All tests passing

### Technical Decisions

**Decision D56: INICIAR uses TOMAR_SPOOL event type**
- Maintains backward compatibility with v3.0 Metadata queries
- Adds v4_operation marker in metadata_json for differentiation
- Same event structure, different operation semantics

**Decision D57: Auto-determination of PAUSAR vs COMPLETAR**
- Simplifies UX by eliminating 3-button flow (TOMAR/PAUSAR/COMPLETAR)
- Worker only chooses unions, system determines action automatically
- selected_count == total_available → COMPLETAR
- selected_count < total_available → PAUSAR

**Decision D58: Empty selected_unions triggers cancellation**
- Zero-union selection is NOT an error (409 Conflict)
- Treated as intentional cancellation (user decides to stop work)
- Releases Redis lock, clears Ocupado_Por, logs SPOOL_CANCELADO event
- Does NOT touch Uniones sheet

**Decision D59: UnionRepository as optional dependency**
- Maintains backward compatibility with v3.0 operations (TOMAR/PAUSAR/COMPLETAR)
- v4.0 operations (INICIAR/FINALIZAR) require UnionRepository
- Raises ValueError if FINALIZAR called without UnionRepository configured

**Decision D60: Race condition returns 409 Conflict**
- If selected_count > total_available, raise ValueError (mapped to 409)
- Indicates union became unavailable between INICIAR and FINALIZAR
- Worker must refresh union list and retry

### Verification Results

**Unit Tests:**
- 13 tests created in `test_occupation_service_v4.py`
- All tests passing (100% success rate)
- Coverage: INICIAR success/failure, FINALIZAR PAUSAR/COMPLETAR, cancellation, race conditions, ownership validation

**Test Breakdown:**
- INICIAR tests: 3 (success, missing prerequisite, already occupied)
- FINALIZAR PAUSAR: 1 (partial selection)
- FINALIZAR COMPLETAR: 1 (full selection)
- Zero-union cancellation: 1
- Race condition: 1
- Ownership validation: 2 (not owner, lock expired)
- Auto-determination helpers: 3
- SOLD operation: 1

## Deviations from Plan

None - plan executed exactly as written.

## Lessons Learned

**What Went Well:**
1. **Clean separation of concerns:** INICIAR (occupation) and FINALIZAR (union processing) are distinct operations
2. **Auto-determination logic:** Simple comparison (selected vs total) eliminates UX complexity
3. **Zero-union cancellation:** Treating empty list as cancellation (not error) provides better UX
4. **Comprehensive test coverage:** 13 tests cover all edge cases and error scenarios
5. **Backward compatibility:** v3.0 operations continue to work, v4.0 adds new capabilities

**What Could Be Improved:**
1. **Spool model missing `ot` field:** Tests had to use MagicMock to simulate v4.0 field (will be added in future phase)
2. **No integration tests:** Unit tests use mocks, real UnionRepository integration not tested yet
3. **No performance tests:** Batch union updates not benchmarked for large selections (10-20 unions)

**Next Steps:**
1. Add integration tests with real UnionRepository
2. Add `ot` field to Spool model (Phase 11?)
3. Performance benchmark for batch union updates
4. Frontend integration with INICIAR/FINALIZAR endpoints

## Next Phase Readiness

**Blockers:** None

**Concerns:**
- Spool model missing `ot` field (test workaround using MagicMock)
- No integration tests with real UnionRepository yet
- Auto-determination logic assumes disponibles query is accurate

**Ready for Phase 10-03:** Yes
- OccupationService ready with v4.0 methods
- UnionRepository integration working (via mocks)
- Auto-determination logic tested and validated
- Zero-union cancellation support complete
