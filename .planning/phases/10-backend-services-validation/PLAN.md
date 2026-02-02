# Phase 10: Backend Services & Validation - Execution Plan

**Goal**: Business logic orchestrates union selection with auto-determination of PAUSAR vs COMPLETAR and ARM-before-SOLD validation

## Success Criteria

From roadmap - what must be TRUE after this phase:

1. ✓ UnionService can process selection with batch update and metadata logging in under 1 second for 10 unions
2. ✓ UnionService calculates pulgadas-diámetro by summing DN_UNION with 2 decimal precision
3. ✓ OccupationService.iniciar_spool() writes Ocupado_Por and Fecha_Ocupacion without touching Uniones sheet
4. ✓ OccupationService.finalizar_spool() auto-determines PAUSAR (partial) vs COMPLETAR (100%) based on selection count
5. ✓ ValidationService enforces ARM-before-SOLD rule: SOLD requires at least 1 union with ARM_FECHA_FIN != NULL
6. ✓ System triggers automatic transition to metrología queue when SOLD is 100% complete
7. ✓ System allows 0 unions selected in FINALIZAR after modal confirmation (logs SPOOL_CANCELADO event)

## Requirements Coverage

Phase 10 implements these requirements from REQUIREMENTS.md:

- **SVC-01**: UnionService.process_selection() orchestrates batch update + metadata logging
- **SVC-02**: UnionService.calcular_pulgadas() sums DN_UNION with 2 decimal precision
- **SVC-03**: UnionService.build_eventos_metadata() creates batch + granular events
- **SVC-04**: OccupationService.iniciar_spool() writes occupation without touching Uniones
- **SVC-05**: OccupationService.finalizar_spool() auto-determines PAUSAR/COMPLETAR
- **SVC-06**: ValidationService enforces ARM→SOLD prerequisite
- **SVC-07**: System auto-determines PAUSAR vs COMPLETAR based on selection count
- **SVC-08**: System triggers metrología queue when SOLD 100% complete
- **VAL-01**: System validates INICIAR SOLD requires >= 1 union with ARM_FECHA_FIN != NULL
- **VAL-02**: System prevents selecting union for SOLD if ARM_FECHA_FIN IS NULL
- **VAL-03**: System supports partial ARM completion
- **VAL-04**: System supports partial SOLD completion with armadas constraint
- **VAL-05**: System handles edge cases with mixed union counts
- **VAL-06**: System enforces optimistic locking with version UUID
- **VAL-07**: System allows 0 unions selected in FINALIZAR (cancellation)

## Execution Plans

### Wave 1 (Parallel Execution)
Foundation services that can be built independently:

#### Plan 10-01: Create UnionService for Batch Operations
- Create UnionService class with dependency injection
- Implement process_selection() for batch orchestration
- Add calcular_pulgadas() with 2 decimal precision
- Build metadata events (batch + granular)
- Define SOLD_REQUIRED_TYPES constant
- **Duration estimate**: 15-20 minutes

#### Plan 10-02: Enhance OccupationService with INICIAR/FINALIZAR
- Add IniciarRequest and FinalizarRequest models
- Implement iniciar_spool() without touching Uniones
- Add finalizar_spool() with auto-determination
- Support zero-union cancellation
- **Duration estimate**: 15-20 minutes

### Wave 2 (Depends on Wave 1)
Enhanced functionality building on foundation:

#### Plan 10-03: Add ARM-before-SOLD Validation
- Create ArmPrerequisiteError exception
- Add validate_arm_prerequisite() to ValidationService
- Integrate into iniciar_spool() for SOLD
- Filter SOLD disponibles to ARM-completed only
- **Duration estimate**: 10-15 minutes

#### Plan 10-04: Implement Metrología Auto-Transition
- Add should_trigger_metrologia() detection
- Integrate into finalizar_spool() flow
- Trigger state machine transition
- Add METROLOGIA_AUTO_TRIGGERED event
- **Duration estimate**: 10-15 minutes

### Wave 3 (Depends on Wave 2)
Validation and testing:

#### Plan 10-05: Integration Tests and Performance Validation
- Complete INICIAR->FINALIZAR integration test
- ARM-to-SOLD workflow validation
- Metrología auto-transition scenarios
- Zero-union cancellation testing
- Performance validation (<1s for 10 unions)
- **Duration estimate**: 20-25 minutes

## Total Estimated Duration

- Wave 1: ~35 minutes (parallel execution)
- Wave 2: ~25 minutes (parallel execution)
- Wave 3: ~25 minutes
- **Total**: ~40-50 minutes (with parallel execution)

## Technical Decisions

Based on phase context and user decisions:

1. **Service Separation**: UnionService handles union operations, OccupationService handles spool occupation
2. **Auto-determination**: Simple count comparison - COMPLETAR if selected == total
3. **ARM Validation**: Enforced at INICIAR time for SOLD operations (fail early)
4. **Metrología Trigger**: Synchronous during FINALIZAR when all work complete
5. **Union Types**: Hardcoded SOLD_REQUIRED_TYPES = ['BW', 'BR', 'SO', 'FILL', 'LET']
6. **Zero Cancellation**: Releases lock, clears occupation, logs SPOOL_CANCELADO

## Dependencies

- Phase 7: Data Model Foundation (Complete)
- Phase 8: Backend Data Layer (Complete)
- Phase 9: Redis & Version Detection (Complete)
- UnionRepository with batch operations
- Redis persistent locks infrastructure
- State machines for transitions

## Risk Mitigation

1. **Race Conditions**: Return 409 Conflict if union unavailable
2. **Partial Updates**: Log warnings, continue with successful unions
3. **Performance**: Use batch operations, never loop updates
4. **Version Conflicts**: 3 retries with exponential backoff

## Verification Strategy

After execution, verify:

1. UnionService orchestrates batch operations correctly
2. INICIAR doesn't touch Uniones sheet
3. FINALIZAR auto-determines action correctly
4. ARM validation blocks SOLD when appropriate
5. Metrología triggers for complete spools
6. Zero-union cancellation works properly
7. Performance meets <1s requirement for 10 unions
8. All unit and integration tests pass

---

*Phase planned: 2026-02-02*
*Ready for execution with /gsd:execute-phase 10*