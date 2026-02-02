# Phase 10: Backend Services & Validation - Context

**Gathered:** 2026-02-02
**Status:** Ready for planning

<domain>
## Phase Boundary

Business logic layer that orchestrates union selection workflows with intelligent auto-determination (PAUSAR vs COMPLETAR) and ARM-before-SOLD validation. This phase sits between the API layer (Phase 11) and the repository layer (Phase 8), enforcing business rules while coordinating batch updates and metadata logging.

**What this phase delivers:**
- UnionService processes union selections with batch updates in <1s
- OccupationService handles INICIAR (spool occupation) and FINALIZAR (with auto-determination)
- ARM-before-SOLD validation enforced at INICIAR time for SOLD operations
- Automatic metrología transition when all work complete (mixed ARM/SOLD completion)
- Support for 0-union FINALIZAR with SPOOL_CANCELADO logging

</domain>

<decisions>
## Implementation Decisions

### Auto-determination Logic

**Core Algorithm:**
- **Simple count comparison:** COMPLETAR if `selected == total`, otherwise PAUSAR
- **Independent evaluation:** ARM and SOLD operations evaluate completion independently
  - ARM COMPLETAR: (already ARM-completed + newly selected ARM) == total spool unions
  - SOLD COMPLETAR: (already SOLD-completed + newly selected SOLD) == total SOLD-required unions
- **Fail on unavailable unions:** If union becomes unavailable between page load and FINALIZAR (race condition), return 409 Conflict error and force user to refresh
- **Recalculate total at FINALIZAR:** Query fresh data from Uniones sheet for accurate total count (don't cache from INICIAR)

**Operation Constraints:**
- **One operation per FINALIZAR:** API validation error if user attempts to select unions from both ARM and SOLD in single call
- **State machine transitions:** Service triggers state machine event, machine handles all state updates (cleaner separation)
- **API transparency:** Return explicit action in response: `{"action_taken": "COMPLETAR"|"PAUSAR", "unions_processed": N, "total_unions": M}`

**Data Validation:**
- **OT-based validation:** Two-step validation to verify unions belong to spool:
  1. Get OT from Operaciones where TAG_SPOOL matches
  2. Verify all selected union.OT == spool.OT
  3. Fail with 422 if any mismatch
- **Consistency check:** Fail with 422 validation error if `selected_count > total_available` (data inconsistency bug)

**Union Type Filtering:**
- **SOLD-required types (hardcoded constant):** `['BW', 'BR', 'SO', 'FILL', 'LET']`
- **ARM-only type:** `['FW']` (no SOLD needed)
- **SOLD disponibles query:** Filter OUT FW unions (SOLD workers never see FW unions)
- **SOLD auto-determination:** Count only SOLD-required unions for total. Exclude FW from calculation.

**Metrics Calculation:**
- **On-demand only:** FINALIZAR updates union timestamps only. Pulgadas-diámetro calculated by metrics endpoint on request (no denormalized writes to Operaciones during FINALIZAR).

### ARM-before-SOLD Validation

**Enforcement Point:**
- **At INICIAR time for SOLD:** Block worker from starting SOLD if 0 ARM unions completed. Fail early, validate upfront.

**Validation Rule:**
- **At least 1 union with ARM_FECHA_FIN != NULL:** Any completed armado union satisfies the rule. Partial ARM completion allows SOLD to start.

**Error Handling:**
- **403 Forbidden with clear message:** "Cannot start SOLD: No ARM unions completed for this spool. Complete at least 1 ARM union first."

**Implementation Location:**
- **OccupationService:** Inline validation within `OccupationService.iniciar_spool()` method (simpler, fewer layers)

**Query Strategy:**
- **Query every time:** Fresh data from Uniones sheet on each INICIAR for SOLD. No caching. Accept ~200-300ms latency for data accuracy.

**SOLD Union Filtering:**
- **Show only ARM-completed unions:** When querying disponibles for SOLD, filter to unions where `ARM_FECHA_FIN != NULL`. Worker can't select unions that haven't been ARM'd.

**SOLD Completion Logic:**
- **Count SOLD-completed unions:** COMPLETAR if (already SOLD-completed + newly selected SOLD) == total SOLD-required unions
- **Total = SOLD-required union count:** Not ARM-completed count, not global spool count. Only BW/BR/SO/FILL/LET unions.

### Metrología Auto-Transition

**Trigger Condition:**
- **Mixed completion logic:** Trigger when ALL work complete:
  - All FW unions have `ARM_FECHA_FIN != NULL` (ARM-only unions done)
  - All SOLD-required unions (BW/BR/SO/FILL/LET) have `SOL_FECHA_FIN != NULL` (ARM+SOLD unions done)
- **Smart detection:** Check both union type categories. System handles spools with mixed union types correctly.

**Execution Mode:**
- **Synchronous:** FINALIZAR triggers state machine transition immediately. Worker sees "Enviado a metrología" in success response. No async background jobs.

**Target State:**
- **PENDIENTE_METROLOGIA:** Spool transitions to metrología queue, waiting for inspector to pick it up.

**State Machine Integration:**
- **No guard checks:** Let state machine handle invalid transitions. Trust the state machine rejection logic (no defensive duplicate transition checks).

**Service Responsibility:**
- **Claude's discretion:** Claude will determine which service (UnionService, OccupationService, or state machine event) should trigger the transition based on separation of concerns.

**API Response:**
- **Explicit notification:** Response includes `{"metrologia_triggered": true, "new_state": "PENDIENTE_METROLOGIA"}`. Frontend can show specific confirmation message.

**ARM-only Behavior:**
- **No special ARM trigger:** ARM COMPLETAR doesn't trigger auto-transitions. Only final SOLD COMPLETAR (or FW-only ARM COMPLETAR) triggers metrología.

**Audit Trail:**
- **Dedicated Metadata event:** Log `METROLOGIA_AUTO_TRIGGERED` event after work completion. Clear audit trail separate from COMPLETAR event.

**Union Type Constants:**
- **Hardcoded in service layer:** Python constant `SOLD_REQUIRED_TYPES = ['BW', 'BR', 'SO', 'FILL', 'LET']`. Fast, simple. Code change required if types change (low frequency expectation).

### Zero-Union Cancellation

**User Confirmation:**
- **Frontend modal confirmation:** Frontend shows modal "¿Liberar sin registrar trabajo?" before calling API. Backend accepts 0 unions as valid input.

**Backend Behavior:**
- **Release lock + log event:**
  1. Delete Redis lock `spool:{tag}:lock`
  2. Clear Operaciones columns: `Ocupado_Por` and `Fecha_Ocupacion`
  3. Append Metadata event: `SPOOL_CANCELADO` for audit trail
  4. Don't touch Uniones sheet

**Operaciones Updates:**
- **Only clear occupation fields:** No version token update. No other columns touched. Spool returns to pre-INICIAR state exactly.

**API Response:**
- **200 OK with body:** `{"action_taken": "CANCELADO", "unions_processed": 0}`. Standard success response for traceable cancellation.

### Claude's Discretion

- Exact service orchestration sequence for metrología trigger (UnionService, OccupationService, or state machine event)
- Logging verbosity and debug information in service methods
- Exception hierarchy and error code organization
- Service method naming conventions

</decisions>

<specifics>
## Specific Ideas

**Union Type Business Rule:**
- 6 total union types in TIPO_UNION column: BW, BR, SO, FILL, FW, LET
- BW/BR/SO/FILL/LET require both ARM and SOLD operations
- FW is ARM-only (no SOLD needed)
- TIPO_UNION field in Uniones sheet is source of truth

**OT as Foreign Key:**
- Uniones sheet does NOT have TAG_SPOOL column
- Use OT column from Uniones to link to Operaciones.OT
- Validation must lookup OT via TAG_SPOOL first, then verify union.OT matches

**Mixed Completion Example:**
- Spool with 100 unions: 80 BW/BR/SO/FILL/LET (need ARM+SOLD), 20 FW (ARM-only)
- Metrología triggers when:
  - All 20 FW have ARM_FECHA_FIN != NULL
  - All 80 SOLD-required have SOL_FECHA_FIN != NULL
- SOLD COMPLETAR compares against 80 (SOLD-required count), not 100 (total count)

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope.

</deferred>

---

*Phase: 10-backend-services-validation*
*Context gathered: 2026-02-02*
