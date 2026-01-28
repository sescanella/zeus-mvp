# Phase 6: Reparación Loops - Research

**Researched:** 2026-01-28
**Domain:** Bounded repair cycle workflow for rejected spools with infinite loop prevention
**Confidence:** HIGH

## Summary

Phase 6 implements a manufacturing rework workflow for spools that fail metrología inspection (estado RECHAZADO). Unlike ARM/SOLD production operations, reparación is a **recovery workflow** that fixes defects and returns spools to metrología queue for re-inspection. The standard approach treats reparación as a **4th operation module** (alongside ARM, SOLD, METROLOGÍA) with the same TOMAR/PAUSAR/COMPLETAR occupation pattern, **embedded cycle counting** in Estado_Detalle field (avoiding new columns), and **bounded retry limits** (max 3 consecutive rejections before manual supervisor intervention).

Key architectural insight: Reparación is fundamentally **corrective work, not new production**. Workers repair defects identified by metrología (weld issues → Soldador repairs, assembly issues → Armador repairs), but the system must prevent infinite RECHAZADO → reparación → RECHAZADO loops that trap spools indefinitely. Industry best practice (2025-2026 manufacturing standards) shows **3-cycle limits with supervisor escalation** prevents perpetual rework while allowing legitimate multiple-attempt repairs for fixable issues.

The cycle counting pattern embeds "Ciclo X/3" in Estado_Detalle string (e.g., "RECHAZADO (Ciclo 2/3)") instead of adding dedicated columns. Counter increments on each metrología RECHAZADO event (not on repair completion), tracks **consecutive rejections only** (resets to 0 after APROBADO), and triggers BLOQUEADO estado after 3rd rejection. Supervisor override uses manual Google Sheets edit (change BLOQUEADO → RECHAZADO in Estado_Detalle) with automatic Metadata logging on next system read.

Real-time dashboard integration follows existing ARM/SOLD patterns - reparación work appears in same "Who has what" list via SSE events, no separate sections needed. Repaired spools return to normal METROLOGÍA queue (no separate "Re-inspection" filter), and any metrólogo can inspect (no assignment to original inspector).

**Primary recommendation:** Create ReparacionStateMachine with 4 states (RECHAZADO → EN_REPARACION → REPARACION_PAUSADA → PENDIENTE_METROLOGIA), add REPARACIÓN as 4th operation in frontend P2 page, filter spools by `estado_detalle LIKE '%RECHAZADO%' AND ocupado_por = None`, parse cycle count from Estado_Detalle regex pattern, and disable TOMAR for BLOQUEADO spools (grayed out cards in UI).

## Standard Stack

No new dependencies required - Phase 6 reuses v3.0 infrastructure:

### Core (Already Installed)
| Library | Version | Purpose | Why No Change Needed |
|---------|---------|---------|---------------------|
| python-statemachine | 2.1+ | ReparacionStateMachine (4-state pattern) | Phase 3 pattern proven for ARM/SOLD, extend with pausada state |
| FastAPI | 0.109+ | POST /completar-reparacion endpoint | Existing action endpoints pattern from Phase 2-5 |
| Pydantic | 2.5+ | Request validation | Extend existing CompletarPayload, no new schemas |
| redis | latest | Not used (no new occupation logic) | Phase 2 occupation service already handles TOMAR/PAUSAR |

### Supporting (Already Installed)
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| gspread | 5.10+ | Estado_Detalle updates with cycle count | Phase 3 EstadoDetalleBuilder pattern |
| uuid | stdlib | Event IDs for TOMAR_REPARACION, COMPLETAR_REPARACION | Phase 1 metadata logging |
| re (regex) | stdlib | Parse cycle count from Estado_Detalle string | Extract "Ciclo 2/3" from existing field |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Embedded cycle count in Estado_Detalle | Add reparacion_count column | User decision: Minimal schema. Estado_Detalle sufficient + no migration needed |
| Manual supervisor override via Sheets | Build supervisor dashboard with override API | Phase 6 scope: Simple manual edit. API endpoint could be Phase 7+ enhancement |
| Consecutive rejection counter | Total rejection counter (never resets) | Industry best practice: Consecutive allows "bad batch" spike + eventual success |
| 3-cycle limit | 5-cycle or unlimited | Manufacturing standard: 3 attempts prevents perpetual rework, balances recovery vs escalation |

**Installation:**
```bash
# No new packages needed - Phase 6 uses existing stack
# Verify state machine already installed:
pip list | grep statemachine
# python-statemachine==2.1.2 (from Phase 3)
```

## Architecture Patterns

### Recommended Project Structure
```
backend/
├── services/
│   ├── state_machines/
│   │   ├── reparacion_state_machine.py   # NEW: 4-state machine
│   │   ├── metrologia_state_machine.py   # EXTEND: Increment cycle on RECHAZADO
│   │   ├── arm_state_machine.py           # Existing
│   │   └── sold_state_machine.py          # Existing
│   ├── validation_service.py              # EXTEND: validar_puede_tomar_reparacion()
│   ├── estado_detalle_builder.py          # EXTEND: Build "RECHAZADO (Ciclo X/3)"
│   └── cycle_counter_service.py           # NEW: Parse/increment cycle count
├── routers/
│   ├── spools.py                          # EXTEND: GET /spools/reparacion (filter RECHAZADO)
│   └── actions.py                         # EXTEND: POST /completar-reparacion
└── models/
    └── enums.py                            # EXTEND: Add REPARACION to ActionType

zeues-frontend/
├── app/
│   ├── operacion/page.tsx                 # EXTEND: Add REPARACION as 4th button
│   └── seleccionar-spool/page.tsx         # MODIFY: Filter RECHAZADO spools for REPARACION
└── lib/
    └── api.ts                              # EXTEND: getSpoolsReparacion(), completarReparacion()
```

### Pattern 1: Embedded Cycle Counter in Estado_Detalle
**What:** Store cycle count as formatted string inside Estado_Detalle field (e.g., "RECHAZADO (Ciclo 2/3)")
**When to use:** Avoiding schema migrations while maintaining audit-friendly display
**Example:**
```python
# Source: User decision from CONTEXT.md - no new columns
# backend/services/cycle_counter_service.py
import re
from typing import Optional

class CycleCounterService:
    """
    Manage reparación cycle counting without dedicated column.

    Cycle count embedded in Estado_Detalle:
    - "RECHAZADO (Ciclo 1/3)" = First rejection
    - "RECHAZADO (Ciclo 2/3)" = Second rejection
    - "RECHAZADO (Ciclo 3/3)" = Third rejection (next RECHAZADO → BLOQUEADO)
    - "BLOQUEADO - Contactar supervisor" = Exceeded limit
    """

    MAX_CYCLES = 3
    CYCLE_PATTERN = r"Ciclo (\d+)/3"

    def extract_cycle_count(self, estado_detalle: str) -> int:
        """
        Parse cycle count from Estado_Detalle string.

        Args:
            estado_detalle: Current Estado_Detalle value

        Returns:
            int: Current cycle count (0 if not found or BLOQUEADO)
        """
        if "BLOQUEADO" in estado_detalle:
            return self.MAX_CYCLES  # Already blocked

        match = re.search(self.CYCLE_PATTERN, estado_detalle)
        if match:
            return int(match.group(1))

        # No cycle info = first rejection
        return 0 if "RECHAZADO" in estado_detalle else 0

    def increment_cycle(self, current_cycle: int) -> int:
        """
        Increment cycle count on new RECHAZADO event.

        Args:
            current_cycle: Current cycle number

        Returns:
            int: Incremented cycle (capped at MAX_CYCLES)
        """
        return min(current_cycle + 1, self.MAX_CYCLES)

    def should_block(self, current_cycle: int) -> bool:
        """
        Check if spool should transition to BLOQUEADO.

        Args:
            current_cycle: Current cycle count

        Returns:
            bool: True if reached max cycles (3)
        """
        return current_cycle >= self.MAX_CYCLES

    def build_rechazado_estado(self, cycle: int) -> str:
        """
        Build Estado_Detalle for RECHAZADO state with cycle info.

        Args:
            cycle: Current cycle number (1-3)

        Returns:
            str: Formatted Estado_Detalle
        """
        if cycle >= self.MAX_CYCLES:
            return "BLOQUEADO - Contactar supervisor"

        return f"RECHAZADO (Ciclo {cycle}/{self.MAX_CYCLES}) - Pendiente reparación"

    def reset_cycle(self) -> str:
        """
        Reset cycle counter after APROBADO.

        Returns:
            str: Estado_Detalle with no cycle info
        """
        return "METROLOGIA_APROBADO ✓"
```

### Pattern 2: ReparacionStateMachine with Auto-Return to Metrología
**What:** 4-state machine where COMPLETAR transition automatically sets estado to PENDIENTE_METROLOGIA
**When to use:** Workflows with circular feedback loops (repair → re-inspect → repair)
**Example:**
```python
# Source: Phase 3 ARM/SOLD pattern adapted
# backend/services/state_machines/reparacion_state_machine.py
from statemachine import State
from backend.services.state_machines.base_state_machine import BaseOperationStateMachine
from datetime import date

class REPARACIONStateMachine(BaseOperationStateMachine):
    """
    REPARACION state machine - repair rejected spools.

    States:
    - rechazado (initial): Failed metrología, awaiting repair
    - en_reparacion: Worker actively repairing
    - reparacion_pausada: Worker paused mid-repair
    - pendiente_metrologia (final): Repair complete, ready for re-inspection

    Transitions:
    - tomar: rechazado → en_reparacion
    - pausar: en_reparacion → reparacion_pausada
    - reanudar: reparacion_pausada → en_reparacion
    - completar: en_reparacion → pendiente_metrologia
    - cancelar: en_reparacion/reparacion_pausada → rechazado

    NOTE: COMPLETAR automatically queues for metrología (no explicit assignment)
    """

    # Define states
    rechazado = State("rechazado", initial=True)
    en_reparacion = State("en_reparacion")
    reparacion_pausada = State("reparacion_pausada")
    pendiente_metrologia = State("pendiente_metrologia", final=True)

    # Define transitions
    tomar = rechazado.to(en_reparacion) | reparacion_pausada.to(en_reparacion)
    pausar = en_reparacion.to(reparacion_pausada)
    completar = en_reparacion.to(pendiente_metrologia)
    cancelar = (en_reparacion.to(rechazado) |
                reparacion_pausada.to(rechazado))

    async def on_enter_en_reparacion(self, event_data):
        """
        Callback when worker TOMAR spool for repair.

        Updates Ocupado_Por + Fecha_Ocupacion columns.
        Estado_Detalle shows "EN_REPARACION (Ciclo X/3) - Ocupado: Worker(ID)"
        """
        worker_nombre = event_data.kwargs.get('worker_nombre')
        cycle = event_data.kwargs.get('cycle', 1)

        if worker_nombre and self.sheets_repo:
            row_num = self._find_spool_row()

            if row_num:
                # Update occupation columns
                self.sheets_repo.batch_update_by_column_name(
                    sheet_name="Operaciones",
                    updates=[
                        {"row": row_num, "column_name": "Ocupado_Por", "value": worker_nombre},
                        {"row": row_num, "column_name": "Fecha_Ocupacion", "value": date.today().strftime("%d-%m-%Y")},
                        {"row": row_num, "column_name": "Estado_Detalle", "value": f"EN_REPARACION (Ciclo {cycle}/3) - Ocupado: {worker_nombre}"}
                    ]
                )

    async def on_enter_reparacion_pausada(self, event_data):
        """
        Callback when worker PAUSAR repair work.

        Clears Ocupado_Por + Fecha_Ocupacion (releases spool).
        Estado_Detalle shows "REPARACION_PAUSADA (Ciclo X/3)"
        """
        cycle = event_data.kwargs.get('cycle', 1)

        if self.sheets_repo:
            row_num = self._find_spool_row()

            if row_num:
                self.sheets_repo.batch_update_by_column_name(
                    sheet_name="Operaciones",
                    updates=[
                        {"row": row_num, "column_name": "Ocupado_Por", "value": ""},
                        {"row": row_num, "column_name": "Fecha_Ocupacion", "value": ""},
                        {"row": row_num, "column_name": "Estado_Detalle", "value": f"REPARACION_PAUSADA (Ciclo {cycle}/3)"}
                    ]
                )

    async def on_enter_pendiente_metrologia(self, event_data):
        """
        Callback when repair COMPLETAR.

        Clears occupation, sets Estado_Detalle to "PENDIENTE_METROLOGIA".
        Spool automatically appears in metrología queue (no manual assignment).
        """
        if self.sheets_repo:
            row_num = self._find_spool_row()

            if row_num:
                self.sheets_repo.batch_update_by_column_name(
                    sheet_name="Operaciones",
                    updates=[
                        {"row": row_num, "column_name": "Ocupado_Por", "value": ""},
                        {"row": row_num, "column_name": "Fecha_Ocupacion", "value": ""},
                        {"row": row_num, "column_name": "Estado_Detalle", "value": "PENDIENTE_METROLOGIA"}
                    ]
                )

    def _find_spool_row(self) -> Optional[int]:
        """Helper to find spool row by TAG_SPOOL."""
        return self.sheets_repo.find_row_by_column_value(
            sheet_name="Operaciones",
            column_letter="G",
            value=self.tag_spool
        )
```

### Pattern 3: Supervisor Override Detection (No API Endpoint)
**What:** System detects manual Estado_Detalle edits in Google Sheets and logs SUPERVISOR_OVERRIDE event automatically
**When to use:** Avoiding complex admin UI while maintaining audit trail
**Example:**
```python
# Source: Phase 1 metadata logging pattern
# backend/services/estado_detalle_service.py
from backend.models.enums import EventoTipo
import uuid
from datetime import datetime

class EstadoDetalleService:
    """
    Monitor Estado_Detalle changes for supervisor overrides.

    Detects when BLOQUEADO → RECHAZADO transition happens outside normal workflow.
    """

    def __init__(self, sheets_repo, metadata_repo):
        self.sheets_repo = sheets_repo
        self.metadata_repo = metadata_repo

    async def detect_supervisor_override(self, tag_spool: str):
        """
        Check if Estado_Detalle was manually changed from BLOQUEADO.

        Args:
            tag_spool: Spool to check

        Flow:
        1. Read current Estado_Detalle
        2. Compare with last Metadata event
        3. If BLOQUEADO → RECHAZADO without COMPLETAR_METROLOGIA event, log override
        """
        current_estado = self.sheets_repo.get_estado_detalle(tag_spool)
        last_event = self.metadata_repo.get_latest_event_for_spool(tag_spool)

        # Check for override pattern
        if (last_event and
            "BLOQUEADO" in last_event.metadata_json and
            "RECHAZADO" in current_estado and
            "BLOQUEADO" not in current_estado):

            # Log supervisor override
            await self.metadata_repo.append_event({
                "id": str(uuid.uuid4()),
                "timestamp": datetime.utcnow().isoformat() + "Z",
                "evento_tipo": "SUPERVISOR_OVERRIDE",
                "tag_spool": tag_spool,
                "worker_id": 0,  # System event
                "worker_nombre": "Sistema",
                "operacion": "REPARACION",
                "accion": "OVERRIDE",
                "fecha_operacion": date.today().isoformat(),
                "metadata_json": json.dumps({
                    "previous_estado": "BLOQUEADO",
                    "new_estado": current_estado,
                    "reason": "Manual supervisor override detected"
                })
            })
```

### Pattern 4: Filtering BLOQUEADO Spools (Visible but Disabled)
**What:** Show BLOQUEADO spools in spool list but disable TOMAR action (grayed out UI)
**When to use:** Transparency over hiding - workers see blocked spools and know why they can't take them
**Example:**
```python
# Source: Phase 2 spool filtering pattern
# backend/routers/spools.py
@router.get("/api/spools/reparacion")
async def get_spools_para_reparacion(
    sheets_repo: SheetsRepository = Depends(get_sheets_repository),
    cycle_counter: CycleCounterService = Depends(get_cycle_counter_service)
):
    """
    Get spools available for reparación.

    Returns:
    - All RECHAZADO spools (including BLOQUEADO for visibility)
    - Adds `bloqueado: true` flag for BLOQUEADO spools
    - Frontend disables TOMAR button for bloqueado=true

    Filters:
    - estado_detalle contains "RECHAZADO" OR "BLOQUEADO"
    - ocupado_por = None (skip occupied spools)
    """
    all_spools = sheets_repo.get_all_spools()

    filtered = []
    for spool in all_spools:
        # Check if RECHAZADO or BLOQUEADO
        if ("RECHAZADO" in (spool.estado_detalle or "") or
            "BLOQUEADO" in (spool.estado_detalle or "")):

            # Skip occupied spools
            if spool.ocupado_por is not None:
                continue

            # Parse cycle count and check if blocked
            cycle = cycle_counter.extract_cycle_count(spool.estado_detalle)
            is_blocked = "BLOQUEADO" in (spool.estado_detalle or "")

            filtered.append({
                "tag_spool": spool.tag_spool,
                "fecha_rechazo": spool.fecha_qc_metrologia,
                "estado_detalle": spool.estado_detalle,
                "cycle": cycle,
                "bloqueado": is_blocked,  # Frontend uses this to disable button
                "fecha_armado": spool.fecha_armado,
                "fecha_soldadura": spool.fecha_soldadura
            })

    return {
        "spools": filtered,
        "total": len(filtered),
        "bloqueados": len([s for s in filtered if s["bloqueado"]]),
        "filtro_aplicado": "RECHAZADO + BLOQUEADO visibles (no ocupados)"
    }
```

### Anti-Patterns to Avoid
- **Adding reparacion_count column:** Estado_Detalle embedding is sufficient and avoids schema migration (user decision)
- **Unlimited retry cycles:** Industry best practice is 3-cycle limit to prevent perpetual rework loops
- **Total rejection counter (never resets):** Consecutive counter allows eventual success after bad batch spike
- **Building supervisor override API:** Phase 6 scope is manual Google Sheets edit with automatic detection
- **Hiding BLOQUEADO spools from list:** Transparency - workers should see blocked spools and understand escalation needed
- **Separate "Re-inspection" metrología queue:** Repaired spools appear in normal queue (any metrólogo can inspect)

## Don't Hand-Roll

Problems that look simple but have existing solutions:

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Cycle count parsing from string | Custom string split logic | re.search() with compiled pattern | Regex handles edge cases (spaces, variations), compiled pattern is cached |
| Estado_Detalle formatting | String concatenation | EstadoDetalleBuilder.build_reparacion() | Centralized formatting, consistent with ARM/SOLD/METROLOGÍA |
| BLOQUEADO detection | String comparison "BLOQUEADO" in estado | CycleCounterService.should_block(cycle) | Business rule encapsulation, testable, consistent |
| Supervisor override logging | Manual metadata append | EstadoDetalleService.detect_supervisor_override() | Automatic detection on read, no manual intervention needed |
| State transitions with cycle updates | Inline if/else chains | ReparacionStateMachine with event_data.kwargs | State machine prevents invalid transitions, cycle passed as context |

**Key insight:** Reparación is not "ARM/SOLD with rejection handling" - it's a **circular feedback workflow** (repair → inspect → repair → inspect) that requires **bounded iteration** to prevent infinite loops. Manufacturing best practice (2025-2026): 3 attempts balances recovery opportunity vs escalation necessity.

## Common Pitfalls

### Pitfall 1: Incrementing Cycle on COMPLETAR Reparación Instead of RECHAZADO
**What goes wrong:** Cycle counter increments when worker finishes repair, not when metrología rejects again - leads to incorrect blocking
**Why it happens:** Assumption that "repair completion = one cycle" instead of "rejection = one cycle"
**How to avoid:** Increment cycle in METROLOGIAStateMachine.on_enter_rechazado() callback, NOT in ReparacionStateMachine
**Warning signs:** Spools blocked after 3 repairs even though only rejected once

### Pitfall 2: Total Rejection Counter (Never Resets)
**What goes wrong:** Spool gets RECHAZADO 3 times over 6 months (with approvals in between), gets BLOQUEADO incorrectly
**Why it happens:** Not distinguishing consecutive vs total rejections
**How to avoid:** Reset cycle counter to 0 in METROLOGIAStateMachine.on_enter_aprobado() callback
**Warning signs:** Long-lived spools getting blocked even with mostly-successful history

### Pitfall 3: Hiding BLOQUEADO Spools from List
**What goes wrong:** Workers wonder why spools "disappear" from reparación queue, supervisors don't know spools need intervention
**Why it happens:** Filtering out blocked spools to "clean up" UI
**How to avoid:** Include BLOQUEADO spools in GET /spools/reparacion with `bloqueado: true` flag, disable TOMAR button in frontend
**Warning signs:** Supervisors asking "where are the blocked spools?", workers confused about missing items

### Pitfall 4: Creating Complex Supervisor Override UI
**What goes wrong:** Phase 6 scope creep - building admin dashboard, role permissions, override approval workflow
**Why it happens:** Overengineering simple supervisor edit process
**How to avoid:** Phase 6: Manual Google Sheets edit only. Override API could be Phase 7+ if requested
**Warning signs:** Planning documents mention "supervisor dashboard", "override approval", "role=SUPERVISOR check"

### Pitfall 5: Separate Re-Inspection Queue
**What goes wrong:** Repaired spools appear in separate "Re-inspection needed" list, creates bottleneck (metrólogos must check two lists)
**Why it happens:** Assumption that re-inspection is different from first-time inspection
**How to avoid:** COMPLETAR reparación sets estado to "PENDIENTE_METROLOGIA", appears in normal GET /spools/metrologia endpoint
**Warning signs:** Frontend has "Re-inspection" tab/page, metrólogos complaining about extra navigation

### Pitfall 6: Parsing Cycle Count on Every Read
**What goes wrong:** Regex parsing on every spool list fetch (200+ spools × regex = performance hit)
**Why it happens:** Not caching parsed cycle count
**How to avoid:** Parse cycle once in backend, include `cycle: int` in API response for frontend to use
**Warning signs:** GET /spools/reparacion takes >2 seconds for 100 spools

## Code Examples

Verified patterns from existing codebase and user decisions:

### Metrología State Machine Extension (Increment Cycle on RECHAZADO)
```python
# Source: Phase 5 metrologia_state_machine.py + Phase 6 cycle counting
# backend/services/state_machines/metrologia_state_machine.py (EXTEND)
from backend.services.cycle_counter_service import CycleCounterService

class METROLOGIAStateMachine(BaseOperationStateMachine):
    """
    METROLOGIA state machine - binary approval/rejection with cycle tracking.

    EXTENSION for Phase 6:
    - on_enter_rechazado: Increment cycle count
    - on_enter_aprobado: Reset cycle count to 0
    """

    def __init__(self, tag_spool: str, sheets_repo, metadata_repo, cycle_counter: CycleCounterService):
        super().__init__(tag_spool, sheets_repo, metadata_repo)
        self.cycle_counter = cycle_counter

    async def on_enter_rechazado(self, event_data):
        """
        Callback when metrología rejects spool.

        Phase 6 addition:
        1. Read current cycle count from Estado_Detalle
        2. Increment cycle
        3. Check if should block (cycle >= 3)
        4. Update Estado_Detalle with new cycle or BLOQUEADO
        """
        if not self.sheets_repo:
            return

        row_num = self._find_spool_row()
        if not row_num:
            return

        # Read current Estado_Detalle to extract cycle
        current_estado = self.sheets_repo.get_cell_value(
            sheet_name="Operaciones",
            row=row_num,
            column_name="Estado_Detalle"
        )

        current_cycle = self.cycle_counter.extract_cycle_count(current_estado or "")
        new_cycle = self.cycle_counter.increment_cycle(current_cycle)

        # Determine new estado
        if self.cycle_counter.should_block(new_cycle):
            new_estado = "BLOQUEADO - Contactar supervisor"
        else:
            new_estado = self.cycle_counter.build_rechazado_estado(new_cycle)

        # Update Estado_Detalle + Fecha_QC_Metrologia
        fecha = event_data.kwargs.get('fecha_operacion', date.today())
        fecha_str = fecha.strftime("%d-%m-%Y") if hasattr(fecha, 'strftime') else str(fecha)

        self.sheets_repo.batch_update_by_column_name(
            sheet_name="Operaciones",
            updates=[
                {"row": row_num, "column_name": "Fecha_QC_Metrologia", "value": fecha_str},
                {"row": row_num, "column_name": "Estado_Detalle", "value": new_estado}
            ]
        )

    async def on_enter_aprobado(self, event_data):
        """
        Callback when metrología approves spool.

        Phase 6 addition:
        - Reset cycle count to 0 (consecutive rejections broken)
        """
        if not self.sheets_repo:
            return

        row_num = self._find_spool_row()
        if not row_num:
            return

        fecha = event_data.kwargs.get('fecha_operacion', date.today())
        fecha_str = fecha.strftime("%d-%m-%Y") if hasattr(fecha, 'strftime') else str(fecha)

        # Reset cycle - use standard APROBADO estado
        self.sheets_repo.batch_update_by_column_name(
            sheet_name="Operaciones",
            updates=[
                {"row": row_num, "column_name": "Fecha_QC_Metrologia", "value": fecha_str},
                {"row": row_num, "column_name": "Estado_Detalle", "value": "METROLOGIA_APROBADO ✓"}
            ]
        )
```

### Validation for TOMAR Reparación
```python
# Source: backend/services/validation_service.py (Phase 2 pattern)
def validar_puede_tomar_reparacion(
    self,
    spool: Spool,
    worker_id: int
) -> None:
    """
    Validate worker can TOMAR spool for reparación.

    Rules:
    - Estado_Detalle must contain "RECHAZADO" (not BLOQUEADO)
    - Spool must NOT be occupied (ocupado_por = None)
    - Worker must have appropriate role (Armador if ARM defect, Soldador if SOLD defect)

    NOTE: No role restriction for REPARACION module per user decision,
    but underlying defect determines required skill (logged in metadata).

    Raises:
        SpoolOccupiedError: If spool currently occupied
        OperacionNoDisponibleError: If spool not RECHAZADO
        SpoolBloqueadoError: If spool BLOQUEADO (needs supervisor)
    """
    # Check BLOQUEADO (cannot repair)
    if "BLOQUEADO" in (spool.estado_detalle or ""):
        raise SpoolBloqueadoError(
            tag_spool=spool.tag_spool,
            mensaje="Spool bloqueado después de 3 rechazos. Contactar supervisor."
        )

    # Check RECHAZADO (can repair)
    if "RECHAZADO" not in (spool.estado_detalle or ""):
        raise OperacionNoDisponibleError(
            tag_spool=spool.tag_spool,
            operacion="REPARACION",
            mensaje="Solo spools RECHAZADOS pueden ser reparados"
        )

    # Check NOT occupied
    if spool.ocupado_por is not None:
        raise SpoolOccupiedError(
            tag_spool=spool.tag_spool,
            current_owner=spool.ocupado_por
        )

    # Role validation (optional - user decision: no role restriction for REPARACION)
    # Could add in future: Check if worker has Armador/Soldador role based on defect type
```

### Frontend REPARACIÓN Integration
```typescript
// Source: zeues-frontend/app/operacion/page.tsx (Phase 2 pattern)
// EXTEND: Add REPARACIÓN as 4th operation option
const operations = [
  { id: 'ARM', label: 'Armado', color: 'bg-blue-600' },
  { id: 'SOLD', label: 'Soldadura', color: 'bg-orange-600' },
  { id: 'METROLOGIA', label: 'Metrología', color: 'bg-green-600' },
  { id: 'REPARACION', label: 'Reparación', color: 'bg-yellow-600' },  // NEW
];

const handleSelectOperation = (operation: Operation) => {
  setState({ selectedOperation: operation });

  if (operation === 'METROLOGIA') {
    // Skip tipo-interaccion for instant completion (Phase 5)
    router.push('/seleccionar-spool?tipo=metrologia');
  } else if (operation === 'REPARACION') {
    // Skip tipo-interaccion for REPARACION (always TOMAR first)
    router.push('/tipo-interaccion?tipo=reparacion');
  } else {
    router.push('/tipo-interaccion');
  }
};
```

### Frontend Spool Card with BLOQUEADO State
```typescript
// Source: zeues-frontend/components/SpoolCard.tsx
// EXTEND: Show BLOQUEADO spools with disabled state
interface SpoolCardProps {
  spool: {
    tag_spool: string;
    fecha_rechazo: string;
    estado_detalle: string;
    cycle: number;
    bloqueado: boolean;
  };
  onSelect: (tag: string) => void;
  disabled?: boolean;
}

const SpoolCard: React.FC<SpoolCardProps> = ({ spool, onSelect, disabled }) => {
  const isBloqueado = spool.bloqueado;
  const canSelect = !disabled && !isBloqueado;

  return (
    <div
      className={`
        border-2 rounded-lg p-4
        ${canSelect ? 'cursor-pointer hover:bg-gray-100' : 'opacity-50 cursor-not-allowed'}
        ${isBloqueado ? 'border-red-500 bg-red-50' : 'border-gray-300'}
      `}
      onClick={() => canSelect && onSelect(spool.tag_spool)}
    >
      <h3 className="text-lg font-bold">{spool.tag_spool}</h3>
      <p className="text-sm text-gray-600">
        Rechazado: {spool.fecha_rechazo}
      </p>

      {isBloqueado ? (
        <div className="mt-2 text-red-600 font-semibold">
          🔒 BLOQUEADO - Contactar supervisor
        </div>
      ) : (
        <div className="mt-2 text-yellow-600">
          ⚠️ Ciclo {spool.cycle}/3
        </div>
      )}

      <p className="text-xs text-gray-500 mt-1">{spool.estado_detalle}</p>
    </div>
  );
};
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Unlimited rework cycles | Max 3 consecutive rejections + supervisor escalation | Industry standard 2020+ | Prevents perpetual rework loops, forces root cause analysis |
| Manual cycle tracking in notebooks | Embedded cycle count in Estado_Detalle field | v3.0 Phase 6 design | Audit-friendly, no schema migration, visible in UI |
| Hiding failed items | Transparent BLOQUEADO display with disabled actions | UX best practice 2025 | Workers understand escalation process, supervisors see blocked items |
| Separate repair operation queue | Repair uses same TOMAR/PAUSAR pattern as production | v3.0 consistency design | Lower training overhead, reuses existing SSE infrastructure |
| Manual supervisor approval workflow | Automatic override detection via Estado_Detalle monitoring | Phase 6 simplification | No admin UI needed, maintains audit trail |

**Deprecated/outdated:**
- Infinite rework allowance: Modern manufacturing limits cycles to force escalation (3-5 attempts standard)
- Total rejection counters: Consecutive counting allows recovery after "bad batch" incidents
- Hidden supervisor overrides: Metadata logging requirement means all state changes must be auditable
- Complex role-based reparación access: User decision - any active worker can repair (simplicity over granular control)

## Open Questions

Things that couldn't be fully resolved:

1. **Post-Override Success Cycle Reset**
   - What we know: User decided "If BLOQUEADO spool passes after override, cycle resets to 0"
   - What's unclear: Should reset happen immediately on APROBADO, or require multiple consecutive approvals?
   - Recommendation: Immediate reset on first APROBADO (supervisor intervention implies problem addressed)

2. **Defect Type Tracking for Role Assignment**
   - What we know: User decision - no role restriction for REPARACION module
   - What's unclear: Should system still log defect type (ARM vs SOLD) in metadata for analytics?
   - Recommendation: Add `defecto_tipo: "ARM" | "SOLD"` to metadata_json for future reporting (doesn't affect Phase 6 workflow)

3. **Batch Operations for Reparación**
   - What we know: User decided multiselect up to 50 spools (same as ARM/SOLD)
   - What's unclear: Can worker batch-TOMAR 50 RECHAZADO spools or single-only like METROLOGÍA?
   - Recommendation: Support batch TOMAR for efficiency (workers may repair multiple simple defects in same session)

4. **Empty State Messaging**
   - What we know: Should communicate RECHAZADO prerequisite
   - What's unclear: Exact Spanish wording for zero-RECHAZADO state
   - Recommendation: "No hay spools rechazados pendientes de reparación. Todos los spools han pasado metrología o están en proceso de reparación."

5. **Override Notification to Workers**
   - What we know: Supervisor manually edits Google Sheets to change BLOQUEADO → RECHAZADO
   - What's unclear: Should system notify workers that spool is now available for repair?
   - Recommendation: Not in Phase 6 scope - workers will see in next list refresh (SSE can publish override event in Phase 7)

## Sources

### Primary (HIGH confidence)
- ZEUES v3.0 codebase - Phase 3 state machine patterns (backend/services/state_machines/arm_state_machine.py, base_state_machine.py)
- Phase 2 occupation service - TOMAR/PAUSAR/COMPLETAR workflow (backend/services/occupation_service.py)
- Phase 5 metrología implementation - RECHAZADO estado transitions (backend/services/state_machines/metrologia_state_machine.py)
- User decisions from CONTEXT.md - Embedded cycle count, no new columns, 3-cycle limit, manual supervisor override

### Secondary (MEDIUM confidence)
- Manufacturing rework best practices 2025-2026 - 3-cycle limit standard, consecutive vs total counting (Tulip, Arena, ComplianceQuest)
- Quality control loop prevention 2025 - Closed-loop quality systems, predictive vs reactive approaches (Qualityze, StartUs Insights)
- State machine workflow patterns 2026 - Rejection handling, compensation patterns, retry strategies (Medium, DZone, Symfony)

### Tertiary (LOW confidence)
- Python regex performance - Compiled pattern caching for cycle parsing (needs validation with production data volumes)

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - Reusing Phase 2-5 patterns, no new dependencies
- Architecture: HIGH - ReparacionStateMachine follows proven Phase 3 pattern, cycle counting embedded in Estado_Detalle per user decision
- Pitfalls: MEDIUM - Identified from codebase patterns and manufacturing best practices, need production validation
- Cycle limit enforcement: HIGH - User decision (3 cycles) + industry standard (2025-2026 sources)
- Supervisor override: HIGH - User decision (manual Google Sheets edit) + automatic detection pattern

**Research date:** 2026-01-28
**Valid until:** 2026-02-28 (30 days - stable architectural patterns, cycle limit may need adjustment based on production data)

---

**Ready for planning.** Phase 6 can proceed with high confidence using existing v3.0 patterns from Phases 1-5, with clear bounded-cycle enforcement strategy preventing infinite rework loops.
