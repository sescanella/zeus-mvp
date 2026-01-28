# Phase 5: Metrología Workflow - Research

**Researched:** 2026-01-27
**Domain:** Instant completion inspection workflow with binary approval/rejection
**Confidence:** HIGH

## Summary

Phase 5 implements a quality inspection workflow fundamentally different from ARM/SOLD operations. Instead of a TOMAR → work → COMPLETAR lifecycle with occupation periods, metrología executes instant binary approval (APROBADO/RECHAZADO) on finished spools. The standard approach uses a **simplified state machine** (PENDIENTE → APROBADO/RECHAZADO terminal states), **direct COMPLETAR action** (skipping TOMAR/PAUSAR), and **Estado_Detalle column updates** for result display without adding dedicated Metrólogo/Fecha_Metrologia columns.

Key architectural insight: Metrología is fundamentally a **validation checkpoint**, not a manufacturing operation. Inspections happen in seconds (not hours), require no resource locking (metrólogo physically moves between spools, doesn't "occupy" them), and have binary outcomes (pass/fail) instead of progressive completion. This justifies skipping the entire occupation layer (Phase 2) and state machine complexity (Phase 3) used for ARM/SOLD.

The standard validation pattern enforces prerequisites (ARM AND SOLD both COMPLETADO) at the spool filtering stage (GET endpoint), blocks occupied spools (cannot inspect if ocupado_por != None to prevent race conditions with active workers), and uses metadata_json field to store resultado (APROBADO/RECHAZADO) for audit trail without schema changes.

**Primary recommendation:** Create METROLOGIA state machine with 3 states (PENDIENTE, APROBADO, RECHAZADO) where APROBADO/RECHAZADO are terminal, skip tipo-interacción page in frontend flow (direct from operation selection → worker → spool → resultado), use single-spool-only UI (no batch), and update Estado_Detalle to display "METROLOGIA APROBADO" or "METROLOGIA RECHAZADO - Pendiente reparación" for clear next-step communication.

## Standard Stack

No new dependencies required - Phase 5 uses existing v3.0 infrastructure:

### Core (Already Installed)
| Library | Version | Purpose | Why No Change Needed |
|---------|---------|---------|---------------------|
| FastAPI | 0.109+ | API endpoints for completar-metrologia | Existing pattern from ARM/SOLD completar actions |
| Pydantic | 2.5+ | Request/response validation | Extend existing ActionPayload with resultado field |
| python-statemachine | 2.1+ | State machine for METROLOGIA states | Phase 3 pattern reusable (simpler 3-state machine) |
| redis | latest | Not used (no occupation locking) | Metrología skips Redis entirely - no TOMAR |

### Supporting (Already Installed)
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| gspread | 5.10+ | Google Sheets updates | Update Estado_Detalle column (Phase 3 pattern) |
| uuid | stdlib | Event IDs for metadata | Standard metadata logging (Phase 1) |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Skip state machine entirely | Simple boolean flag | State machine provides consistency with ARM/SOLD architecture, easier to extend for Phase 6 reparación cycles |
| Add Metrólogo column | Reuse ocupado_por temporarily | User decision: Keep minimal, no new columns. Estado_Detalle sufficient for display |
| Batch approval | Single-spool only | User decision: Simplicity for Phase 5. Batch could speed approvals but increases complexity |

**Installation:**
```bash
# No new packages needed - Phase 5 uses existing stack
# Verify state machine library already installed:
pip list | grep statemachine
# python-statemachine==2.1.2 (from Phase 3)
```

## Architecture Patterns

### Recommended Project Structure
```
backend/
├── services/
│   ├── state_machines/
│   │   ├── metrologia_state_machine.py   # NEW: 3-state machine
│   │   ├── arm_state_machine.py           # Existing (Phase 3)
│   │   └── sold_state_machine.py          # Existing (Phase 3)
│   ├── validation_service.py              # EXTEND: Add validar_puede_completar_metrologia()
│   └── estado_detalle_builder.py          # EXTEND: Handle METROLOGIA states
├── routers/
│   ├── spools.py                          # EXTEND: GET /spools/metrologia endpoint
│   └── actions.py                         # EXTEND: POST /completar-metrologia endpoint
└── models/
    └── action.py                           # EXTEND: Add resultado field to payload

zeues-frontend/
├── app/
│   ├── operacion/page.tsx                 # EXTEND: Add METROLOGIA option
│   ├── seleccionar-spool/page.tsx         # MODIFY: Skip tipo-interaccion for METROLOGIA
│   └── resultado-metrologia/page.tsx      # NEW: APROBADO/RECHAZADO selection
└── lib/
    └── api.ts                              # EXTEND: completarMetrologia() function
```

### Pattern 1: Simplified State Machine (3 States Only)
**What:** METROLOGIA uses minimal state machine with PENDIENTE initial state and two terminal states (APROBADO, RECHAZADO)
**When to use:** Quality checkpoints with binary outcomes, no progressive completion
**Example:**
```python
# Source: Phase 3 ARM/SOLD pattern adapted
# backend/services/state_machines/metrologia_state_machine.py
from statemachine import State
from backend.services.state_machines.base_state_machine import BaseOperationStateMachine

class METROLOGIAStateMachine(BaseOperationStateMachine):
    """
    METROLOGIA state machine - binary approval/rejection.

    States:
    - pendiente (initial): Awaiting inspection
    - aprobado (final): Passed inspection
    - rechazado (final): Failed inspection, needs reparación

    Transitions:
    - aprobar: pendiente → aprobado
    - rechazar: pendiente → rechazado

    NOTE: No iniciar/completar split - single transition on resultado selection
    """

    # Define states
    pendiente = State("pendiente", initial=True)
    aprobado = State("aprobado", final=True)
    rechazado = State("rechazado", final=True)

    # Define transitions
    aprobar = pendiente.to(aprobado)
    rechazar = pendiente.to(rechazado)

    async def on_enter_aprobado(self, event_data):
        """Update Fecha_QC_Metrologia column with today's date"""
        fecha = event_data.kwargs.get('fecha_operacion', date.today())
        # Update sheet column (Pattern from ARM completado callback)

    async def on_enter_rechazado(self, event_data):
        """Update Fecha_QC_Metrologia + Estado_Detalle with rejection notice"""
        fecha = event_data.kwargs.get('fecha_operacion', date.today())
        # Update Fecha_QC_Metrologia (same as aprobado)
        # Estado_Detalle handled by builder separately
```

### Pattern 2: Direct Completion Endpoint (No TOMAR Phase)
**What:** Single POST endpoint that validates prerequisites and completes in one atomic operation
**When to use:** Operations completing in <10 seconds with no occupation period
**Example:**
```python
# Source: Existing completar-accion pattern from Phase 1
# backend/routers/actions.py
@router.post("/api/completar-metrologia")
async def completar_metrologia(
    payload: MetrologiaPayload,  # worker_id, tag_spool, resultado: APROBADO|RECHAZADO
    validation_service: ValidationService = Depends(get_validation_service),
    state_service: StateService = Depends(get_state_service)
):
    """
    Complete metrología inspection with binary result.

    Flow:
    1. Validate prerequisites (ARM + SOLD completado, NOT occupied)
    2. Trigger state transition based on resultado
    3. Update Estado_Detalle via builder
    4. Log metadata event (COMPLETAR_METROLOGIA)
    5. Publish SSE event for dashboard update

    Returns 200 with success message or 400/403/404 on validation failure
    """
    # Validate prerequisites (use existing pattern from validar_puede_completar_arm)
    spool = sheets_repo.get_spool_by_tag(payload.tag_spool)
    validation_service.validar_puede_completar_metrologia(spool, payload.worker_id)

    # Create state machine instance
    metrologia_machine = METROLOGIAStateMachine(
        tag_spool=payload.tag_spool,
        sheets_repo=sheets_repo,
        metadata_repo=metadata_repo
    )

    # Trigger transition based on resultado
    if payload.resultado == "APROBADO":
        metrologia_machine.aprobar(fecha_operacion=date.today())
    else:
        metrologia_machine.rechazar(fecha_operacion=date.today())

    # Update Estado_Detalle (via builder callback pattern)
    # Return success response
```

### Pattern 3: Prerequisite Filtering at GET Stage
**What:** Filter spools at API level to only show inspection-ready items (ARM + SOLD completed, NOT occupied)
**When to use:** Prevent invalid actions by hiding invalid options in UI
**Example:**
```python
# Source: Existing GET /spools/iniciar pattern from Phase 1
# backend/routers/spools.py
@router.get("/api/spools/metrologia")
async def get_spools_para_metrologia(
    sheets_repo: SheetsRepository = Depends(get_sheets_repository)
):
    """
    Get spools ready for metrología inspection.

    Filters:
    - fecha_armado != None (ARM completed)
    - fecha_soldadura != None (SOLD completed)
    - fecha_qc_metrologia == None (METROLOGIA not done)
    - ocupado_por == None (not currently being worked)

    Returns empty array with hint if no spools available
    """
    all_spools = sheets_repo.get_all_spools()

    filtered = [
        spool for spool in all_spools
        if spool.fecha_armado is not None
        and spool.fecha_soldadura is not None
        and spool.fecha_qc_metrologia is None
        and spool.ocupado_por is None  # CRITICAL: Block occupied spools
    ]

    return {
        "spools": filtered,
        "total": len(filtered),
        "filtro_aplicado": "ARM + SOLD completados, no ocupados"
    }
```

### Pattern 4: Estado_Detalle Result Display
**What:** Use EstadoDetalleBuilder to format human-readable status with next-step guidance
**When to use:** Terminal states that need clear communication of next actions
**Example:**
```python
# Source: Phase 3 EstadoDetalleBuilder pattern
# backend/services/estado_detalle_builder.py
class EstadoDetalleBuilder:
    def build(
        self,
        ocupado_por: Optional[str],
        arm_state: str,
        sold_state: str,
        metrologia_state: Optional[str] = None  # NEW parameter
    ) -> str:
        """
        Build Estado_Detalle with metrología result.

        Examples:
        - metrologia_state = "aprobado" → "METROLOGIA APROBADO - Listo para siguiente fase"
        - metrologia_state = "rechazado" → "METROLOGIA RECHAZADO - Pendiente reparación"
        - metrologia_state = "pendiente" → "Disponible - ARM completado, SOLD completado, METROLOGIA pendiente"
        """
        if metrologia_state == "aprobado":
            return "METROLOGIA APROBADO - Listo para siguiente fase"
        elif metrologia_state == "rechazado":
            return "METROLOGIA RECHAZADO - Pendiente reparación"

        # Fall back to existing ARM/SOLD display logic
        # ... (existing code)
```

### Anti-Patterns to Avoid
- **Adding TOMAR before COMPLETAR:** Metrología doesn't need occupation - inspection is instant, metrólogo moves freely
- **Batch approval without validation:** Each spool needs independent validation (occupation status, prerequisites) - batch increases error surface
- **Reusing ocupado_por for metrólogo:** Occupation is for prolonged work periods, not instant inspections - semantic mismatch
- **Allowing inspection of occupied spools:** Race condition - worker could be actively modifying while metrólogo inspects

## Don't Hand-Roll

Problems that look simple but have existing solutions:

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| State transitions with validation | Custom if/else chains | python-statemachine with guards | Existing Phase 3 pattern, prevents invalid transitions, self-documenting |
| Resultado enum validation | String comparison | Pydantic Literal["APROBADO", "RECHAZADO"] | Type-safe at API boundary, auto-generates OpenAPI docs |
| Estado_Detalle formatting | String concatenation | EstadoDetalleBuilder.build() | Centralized display logic, consistent with ARM/SOLD |
| Prerequisite validation | Inline checks in endpoint | ValidationService.validar_puede_completar_metrologia() | Separation of concerns, testable independently |
| SSE event publishing | Manual Redis publish | RedisEventService.publish_state_change() | Phase 4 pattern, consistent event format |

**Key insight:** Phase 5 is **not** ARM/SOLD minus TOMAR - it's a fundamentally different workflow (validation checkpoint vs manufacturing operation). Attempting to force-fit TOMAR occupation would add unnecessary complexity without value.

## Common Pitfalls

### Pitfall 1: Allowing Metrología on Occupied Spools
**What goes wrong:** Metrólogo approves spool while worker is actively reworking it, creates data inconsistency
**Why it happens:** Forgetting to check ocupado_por in GET filter, assuming "SOLD completado" means "finished forever"
**How to avoid:** Add `ocupado_por == None` filter in GET /spools/metrologia endpoint (Pattern 3)
**Warning signs:** Users report inspecting spools that "disappear" or change state unexpectedly

### Pitfall 2: Treating RECHAZADO as Non-Terminal State
**What goes wrong:** State machine allows RECHAZADO → PENDIENTE transition, enables direct re-inspection without reparación
**Why it happens:** Assumption that "rejected items can be retried" - missing the reparación cycle (Phase 6)
**How to avoid:** Mark rechazado as `final=True` in state machine definition, Phase 6 will handle reparación → new metrología cycle
**Warning signs:** Spools bouncing between RECHAZADO and APROBADO without metadata audit trail

### Pitfall 3: Skipping Prerequisite Validation in Backend
**What goes wrong:** Frontend filters spools correctly but backend endpoint accepts any spool, malicious/buggy client bypasses validation
**Why it happens:** Trusting frontend filtering alone, not implementing defense-in-depth
**How to avoid:** Implement `validar_puede_completar_metrologia()` in ValidationService that checks fecha_armado, fecha_soldadura, ocupado_por
**Warning signs:** Data corruption where metrología completed on unfinished spools

### Pitfall 4: Using TOMAR Flow for Metrología
**What goes wrong:** Metrólogo has to TOMAR spool (blocks it for hours) before completing instant inspection, creates artificial bottleneck
**Why it happens:** Cargo-culting ARM/SOLD flow without understanding domain difference (prolonged work vs instant validation)
**How to avoid:** Skip tipo-interacción page in frontend, go directly Operation → Worker → Spool → Resultado
**Warning signs:** Metrólogos complaining about "extra clicks", spools stuck in occupied state for inspections that took 30 seconds

### Pitfall 5: Adding Metrólogo/Fecha_Metrologia Columns
**What goes wrong:** Schema bloat, unnecessary migration complexity, doesn't match user decision to keep minimal
**Why it happens:** Pattern-matching ARM (Armador, Fecha_Armado) and SOLD (Soldador, Fecha_Soldadura) without questioning necessity
**How to avoid:** Reuse Fecha_QC_Metrologia (already exists), store worker_id in metadata (audit trail), display via Estado_Detalle
**Warning signs:** Planning documents mention "add 2 new columns" - red flag per user decision

## Code Examples

Verified patterns from existing codebase:

### Validation Method for Metrología Prerequisites
```python
# Source: backend/services/validation_service.py (Phase 1 pattern)
def validar_puede_completar_metrologia(
    self,
    spool: Spool,
    worker_id: int
) -> None:
    """
    Validate spool ready for metrología completion.

    Rules:
    - ARM must be COMPLETADO (fecha_armado != None)
    - SOLD must be COMPLETADO (fecha_soldadura != None)
    - METROLOGIA must be PENDIENTE (fecha_qc_metrologia == None)
    - Spool must NOT be occupied (ocupado_por == None)
    - Worker must have METROLOGIA role

    Raises:
        DependenciasNoSatisfechasError: If ARM or SOLD not completed
        OperacionYaCompletadaError: If metrología already done
        SpoolOccupiedError: If spool currently occupied
        RolNoAutorizadoError: If worker lacks METROLOGIA role
    """
    # Check ARM completed
    if spool.fecha_armado is None:
        raise DependenciasNoSatisfechasError(
            tag_spool=spool.tag_spool,
            operacion="METROLOGIA",
            dependencia_faltante="ARM debe estar completado",
            detalle="Armado debe finalizar antes de metrología"
        )

    # Check SOLD completed
    if spool.fecha_soldadura is None:
        raise DependenciasNoSatisfechasError(
            tag_spool=spool.tag_spool,
            operacion="METROLOGIA",
            dependencia_faltante="SOLD debe estar completado",
            detalle="Soldadura debe finalizar antes de metrología"
        )

    # Check NOT already completed
    if spool.fecha_qc_metrologia is not None:
        raise OperacionYaCompletadaError(
            tag_spool=spool.tag_spool,
            operacion="METROLOGIA"
        )

    # Check NOT occupied (CRITICAL for race condition prevention)
    if spool.ocupado_por is not None:
        raise SpoolOccupiedError(
            tag_spool=spool.tag_spool,
            current_owner=spool.ocupado_por
        )

    # Check role authorization
    if self.role_service:
        self.role_service.validar_worker_tiene_rol_para_operacion(
            worker_id,
            "METROLOGIA"
        )
```

### Frontend Flow Modification (Skip Tipo-Interacción)
```typescript
// Source: zeues-frontend/app/operacion/page.tsx (modify existing)
const handleSelectOperation = (operation: 'ARM' | 'SOLD' | 'METROLOGIA') => {
  setState({ selectedOperation: operation });

  // METROLOGIA bypasses tipo-interaccion page entirely
  if (operation === 'METROLOGIA') {
    router.push('/seleccionar-spool?tipo=metrologia');
  } else {
    router.push('/tipo-interaccion');  // ARM/SOLD go to INICIAR/COMPLETAR choice
  }
};
```

### Metadata Logging with Resultado
```python
# Source: backend/repositories/metadata_repository.py (Phase 1 pattern)
metadata_event = MetadataEvent(
    id=str(uuid.uuid4()),
    timestamp=datetime.utcnow().isoformat() + "Z",
    evento_tipo=EventoTipo.COMPLETAR_METROLOGIA,
    tag_spool=tag_spool,
    worker_id=worker_id,
    worker_nombre=worker_nombre,
    operacion="METROLOGIA",
    accion="COMPLETAR",
    fecha_operacion=date.today().isoformat(),
    metadata_json=json.dumps({
        "resultado": "APROBADO",  # or "RECHAZADO"
        "inspeccion_duracion_segundos": 15
    })
)
metadata_repo.append_event(metadata_event)
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Dedicated QC columns per spool | Single Fecha_QC_Metrologia reuse | v3.0 simplification | Minimal schema, faster migration |
| TOMAR before inspect | Direct completar | Phase 5 design | 2 fewer clicks, no artificial occupation |
| Progressive completion | Binary approval | Industry standard for QC | Clear pass/fail, no partial inspection concept |
| Manual inspection logging | Automated metadata | Phase 1 Event Sourcing | Complete audit trail with timestamps |

**Deprecated/outdated:**
- Multi-step inspection workflows: Quality checkpoints are inherently atomic (pass or fail in single evaluation)
- Inspection occupation periods: Modern QC is fast (seconds to minutes), doesn't justify resource locking overhead
- Inspection notes in main schema: Metadata JSON sufficient for comments, avoids column proliferation

## Open Questions

Things that couldn't be fully resolved:

1. **Retry Limit for Reparación Cycles**
   - What we know: Phase 6 will implement reparación workflow after RECHAZADO
   - What's unclear: Should Phase 5 enforce max retry limit (e.g., 3 rejections → supervisor escalation)?
   - Recommendation: Phase 5 allows unlimited RECHAZADO (just updates estado), Phase 6 adds cycle counting

2. **Batch Approval UX Tradeoff**
   - What we know: User decided single-spool for Phase 5 simplicity
   - What's unclear: Performance impact if metrólogo has 50 spools to approve (50 clicks vs batch)
   - Recommendation: Start single-spool, measure if metrólogos request batch in user feedback

3. **Empty State Hint Wording**
   - What we know: Should communicate ARM+SOLD prerequisite
   - What's unclear: Exact Spanish wording that's clearest to workers
   - Recommendation: "No hay spools listos para metrología. Verifica que ARM y SOLD estén completados." (can refine in testing)

4. **SSE Event for Dashboard**
   - What we know: Phase 4 implements SSE for real-time updates
   - What's unclear: Should APROBADO/RECHAZADO publish to "spools:updates" channel?
   - Recommendation: Yes - publish with type "COMPLETAR_METROLOGIA" for dashboard to show completed spools disappearing from list

## Sources

### Primary (HIGH confidence)
- Existing ZEUES v3.0 codebase - ValidationService patterns (backend/services/validation_service.py)
- Phase 3 state machine implementation - ARMStateMachine structure (backend/services/state_machines/arm_state_machine.py)
- Phase 1 metadata repository - Event logging pattern (backend/repositories/metadata_repository.py)
- Phase 2 occupation service - Spool locking patterns (backend/services/occupation_service.py)

### Secondary (MEDIUM confidence)
- python-statemachine documentation - Final states and one-way transitions (https://github.com/fgmacedo/python-statemachine)
- Pydantic Literal type validation - Enum alternatives (https://docs.pydantic.dev/latest/concepts/types/)

### Tertiary (LOW confidence)
- Industry QC workflow patterns - Need validation with actual metrólogos in production

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - Reusing existing v3.0 libraries, no new dependencies
- Architecture: HIGH - Based on proven Phase 3 state machine + Phase 1 validation patterns
- Pitfalls: MEDIUM - Identified from codebase patterns, need production validation
- Frontend flow: HIGH - Clear from user decisions in CONTEXT.md (skip tipo-interacción)

**Research date:** 2026-01-27
**Valid until:** 2026-02-27 (30 days - stable architectural patterns, may need UX refinement based on metrólogo feedback)

---

**Ready for planning.** Phase 5 can proceed with high confidence using existing patterns from Phases 1-4.
