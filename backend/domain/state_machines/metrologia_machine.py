"""
METROLOGIA (Quality Inspection) state machine.

Manages instant binary inspection workflow:
- PENDIENTE → APROBADO (aprobar)
- PENDIENTE → RECHAZADO (rechazar)

No occupation states - inspection is instant (< 30 seconds).
Both APROBADO and RECHAZADO are terminal states (final=True) to prevent
re-inspection without reparación cycle.
"""

from statemachine import State
from backend.services.state_machines.base_state_machine import BaseOperationStateMachine
from backend.config import config
from datetime import date


# Estado_Detalle constants written by this state machine.
ESTADO_DETALLE_APROBADO = "METROLOGIA APROBADO ✓"
ESTADO_DETALLE_RECHAZADO = "RECHAZADO - Pendiente reparación"


class MetrologiaStateMachine(BaseOperationStateMachine):
    """
    METROLOGIA inspection state machine with binary outcomes.

    States:
    - pendiente (initial): Awaiting inspection (ARM + SOLD complete)
    - aprobado (final): Passed inspection, ready for next phase
    - rechazado (final): Failed inspection, needs reparación

    Transitions:
    - aprobar: pendiente → aprobado
    - rechazar: pendiente → rechazado

    NOTE: Both terminal states are final=True to enforce reparación workflow.
    Direct re-inspection (RECHAZADO → PENDIENTE) is NOT allowed - must go
    through reparación cycle first.
    """

    # Define states
    pendiente = State("pendiente", initial=True)
    aprobado = State("aprobado", final=True)
    rechazado = State("rechazado", final=True)

    # Define transitions
    aprobar = pendiente.to(aprobado)
    rechazar = pendiente.to(rechazado)

    def __init__(self, tag_spool: str, sheets_repo, metadata_repo):
        """
        Initialize METROLOGIA state machine for a specific spool.

        Args:
            tag_spool: Spool identifier
            sheets_repo: SheetsRepository for column updates
            metadata_repo: MetadataRepository for event logging
        """
        super().__init__(tag_spool, sheets_repo, metadata_repo)

    def on_enter_aprobado(self, fecha_operacion=None):
        """
        Callback when inspection passes.

        Updates Fecha_QC_Metrologia column with completion date and writes
        the approved Estado_Detalle.

        Args:
            fecha_operacion: Date of inspection completion (defaults to today)
        """
        fecha = fecha_operacion if fecha_operacion else date.today()
        if self.sheets_repo:
            # Find row for this spool
            tag_col_letter = self.sheets_repo.get_tag_spool_column_letter(config.HOJA_OPERACIONES_NOMBRE)
            row_num = self.sheets_repo.find_row_by_column_value(
                sheet_name=config.HOJA_OPERACIONES_NOMBRE,
                column_letter=tag_col_letter,
                value=self.tag_spool
            )

            if row_num:
                # Format date as DD-MM-YYYY for consistency with existing data
                fecha_str = fecha.strftime("%d-%m-%Y") if hasattr(fecha, 'strftime') else str(fecha)

                # Update Fecha_QC_Metrologia + Estado_Detalle columns
                self.sheets_repo.batch_update_by_column_name(
                    sheet_name=config.HOJA_OPERACIONES_NOMBRE,
                    updates=[
                        {"row": row_num, "column_name": "Fecha_QC_Metrología", "value": fecha_str},
                        {"row": row_num, "column_name": "Estado_Detalle", "value": ESTADO_DETALLE_APROBADO}
                    ]
                )

    def on_enter_rechazado(self, fecha_operacion=None):
        """
        Callback when inspection fails.

        Updates Estado_Detalle only (NOT Fecha_QC_Metrología).
        Fecha_QC_Metrología represents approval date, not inspection date.
        Every rejection writes the same RECHAZADO marker — there is no cycle
        counter and no automatic BLOQUEADO escalation; a rejected spool can be
        repaired and re-inspected as many times as needed.
        """
        if not self.sheets_repo:
            return

        # Find row for this spool
        tag_col_letter = self.sheets_repo.get_tag_spool_column_letter(config.HOJA_OPERACIONES_NOMBRE)
        row_num = self.sheets_repo.find_row_by_column_value(
            sheet_name=config.HOJA_OPERACIONES_NOMBRE,
            column_letter=tag_col_letter,
            value=self.tag_spool
        )

        if not row_num:
            return

        # Update Estado_Detalle only (no Fecha_QC_Metrología for RECHAZADO)
        self.sheets_repo.batch_update_by_column_name(
            sheet_name=config.HOJA_OPERACIONES_NOMBRE,
            updates=[
                {"row": row_num, "column_name": "Estado_Detalle", "value": ESTADO_DETALLE_RECHAZADO}
            ]
        )
