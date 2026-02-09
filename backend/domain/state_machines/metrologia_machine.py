"""
METROLOGIA (Quality Inspection) state machine.

Manages instant binary inspection workflow:
- PENDIENTE → APROBADO (aprobar)
- PENDIENTE → RECHAZADO (rechazar)

No occupation states - inspection is instant (< 30 seconds).
Both APROBADO and RECHAZADO are terminal states (final=True) to prevent
re-inspection without reparación cycle (Phase 6).
"""

from statemachine import State
from backend.services.state_machines.base_state_machine import BaseOperationStateMachine
from backend.config import config
from datetime import date


class MetrologiaStateMachine(BaseOperationStateMachine):
    """
    METROLOGIA inspection state machine with binary outcomes.

    States:
    - pendiente (initial): Awaiting inspection (ARM + SOLD complete)
    - aprobado (final): Passed inspection, ready for next phase
    - rechazado (final): Failed inspection, needs reparación (Phase 6)

    Transitions:
    - aprobar: pendiente → aprobado
    - rechazar: pendiente → rechazado

    NOTE: Both terminal states are final=True to enforce reparación workflow.
    Direct re-inspection (RECHAZADO → PENDIENTE) is NOT allowed - must go
    through reparación cycle first (Phase 6 feature).
    """

    # Define states
    pendiente = State("pendiente", initial=True)
    aprobado = State("aprobado", final=True)
    rechazado = State("rechazado", final=True)

    # Define transitions
    aprobar = pendiente.to(aprobado)
    rechazar = pendiente.to(rechazado)

    def __init__(self, tag_spool: str, sheets_repo, metadata_repo, cycle_counter=None):
        """
        Initialize METROLOGIA state machine for a specific spool.

        Args:
            tag_spool: Spool identifier
            sheets_repo: SheetsRepository for column updates
            metadata_repo: MetadataRepository for event logging
            cycle_counter: CycleCounterService for Phase 6 reparación cycle tracking
        """
        super().__init__(tag_spool, sheets_repo, metadata_repo)
        self.cycle_counter = cycle_counter

    def on_enter_aprobado(self, fecha_operacion=None):
        """
        Callback when inspection passes.

        Updates Fecha_QC_Metrologia column with completion date.
        Phase 6: Resets cycle counter (consecutive rejections broken).

        Args:
            fecha_operacion: Date of inspection completion (defaults to today)
        """
        fecha = fecha_operacion if fecha_operacion else date.today()
        if self.sheets_repo:
            # Find row for this spool
            row_num = self.sheets_repo.find_row_by_column_value(
                sheet_name=config.HOJA_OPERACIONES_NOMBRE,
                column_letter="G",  # TAG_SPOOL column
                value=self.tag_spool
            )

            if row_num:
                # Format date as DD-MM-YYYY for consistency with existing data
                fecha_str = fecha.strftime("%d-%m-%Y") if hasattr(fecha, 'strftime') else str(fecha)

                # Phase 6: Reset cycle counter on approval
                estado_detalle = "METROLOGIA_APROBADO ✓"
                if self.cycle_counter:
                    estado_detalle = self.cycle_counter.reset_cycle()

                # Update Fecha_QC_Metrologia + Estado_Detalle columns
                self.sheets_repo.batch_update_by_column_name(
                    sheet_name=config.HOJA_OPERACIONES_NOMBRE,
                    updates=[
                        {"row": row_num, "column_name": "Fecha_QC_Metrología", "value": fecha_str},
                        {"row": row_num, "column_name": "Estado_Detalle", "value": estado_detalle}
                    ]
                )

    def on_enter_rechazado(self, fecha_operacion=None):
        """
        Callback when inspection fails.

        Updates Estado_Detalle only (NOT Fecha_QC_Metrología).
        Fecha_QC_Metrología represents approval date, not inspection date.
        Phase 6: Increments cycle counter and checks if should block after 3 rejections.
        """
        if self.sheets_repo:
            # Find row for this spool
            row_num = self.sheets_repo.find_row_by_column_value(
                sheet_name=config.HOJA_OPERACIONES_NOMBRE,
                column_letter="G",  # TAG_SPOOL column
                value=self.tag_spool
            )

            if row_num:
                # Phase 6: Increment cycle counter on rejection
                estado_detalle = "METROLOGIA RECHAZADO - Pendiente reparación"
                if self.cycle_counter:
                    # Read current Estado_Detalle to extract cycle
                    current_estado = self.sheets_repo.get_cell_value(
                        sheet_name=config.HOJA_OPERACIONES_NOMBRE,
                        row=row_num,
                        column_name="Estado_Detalle"
                    )

                    # Extract current cycle and increment
                    current_cycle = self.cycle_counter.extract_cycle_count(current_estado or "")
                    new_cycle = self.cycle_counter.increment_cycle(current_cycle)

                    # Build new estado (BLOQUEADO if at limit, else RECHAZADO with cycle)
                    estado_detalle = self.cycle_counter.build_rechazado_estado(new_cycle)

                # Update Estado_Detalle only (no Fecha_QC_Metrología for RECHAZADO)
                self.sheets_repo.batch_update_by_column_name(
                    sheet_name=config.HOJA_OPERACIONES_NOMBRE,
                    updates=[
                        {"row": row_num, "column_name": "Estado_Detalle", "value": estado_detalle}
                    ]
                )
