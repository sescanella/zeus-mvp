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

        Updates Fecha_QC_Metrologia column with completion date.

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

                # Update Fecha_QC_Metrologia column
                self.sheets_repo.update_cell_by_column_name(
                    sheet_name=config.HOJA_OPERACIONES_NOMBRE,
                    row=row_num,
                    column_name="Fecha_QC_Metrología",
                    value=fecha_str
                )

    def on_enter_rechazado(self, fecha_operacion=None):
        """
        Callback when inspection fails.

        Updates Fecha_QC_Metrologia column with completion date.
        Note: Estado_Detalle will be updated separately by EstadoDetalleBuilder
        to display "METROLOGIA RECHAZADO - Pendiente reparación".

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

                # Update Fecha_QC_Metrologia column (same as aprobado)
                # Result is stored in metadata_json, not in separate column
                self.sheets_repo.update_cell_by_column_name(
                    sheet_name=config.HOJA_OPERACIONES_NOMBRE,
                    row=row_num,
                    column_name="Fecha_QC_Metrología",
                    value=fecha_str
                )
