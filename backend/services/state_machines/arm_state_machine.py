"""
ARM (Assembly) operation state machine.

Manages ARM operation lifecycle:
- PENDIENTE → EN_PROGRESO (iniciar)
- EN_PROGRESO → COMPLETADO (completar)
- EN_PROGRESO → PENDIENTE (cancelar)

Callbacks update Operaciones sheet columns (Armador, Fecha_Armado) automatically.
No dependency guards - ARM is the first operation.
"""

from statemachine import State
from backend.services.state_machines.base_state_machine import BaseOperationStateMachine
from backend.config import config
from datetime import date


class ARMStateMachine(BaseOperationStateMachine):
    """
    ARM operation state machine.

    States:
    - pendiente (initial): ARM not started (Armador = None)
    - en_progreso: ARM in progress (Armador != None, Fecha_Armado = None)
    - completado (final): ARM completed (Fecha_Armado != None)

    Transitions:
    - iniciar: pendiente → en_progreso
    - completar: en_progreso → completado
    - cancelar: en_progreso → pendiente
    """

    # Define states
    pendiente = State("pendiente", initial=True)
    en_progreso = State("en_progreso")
    completado = State("completado", final=True)

    # Define transitions
    iniciar = pendiente.to(en_progreso)
    completar = en_progreso.to(completado)
    cancelar = en_progreso.to(pendiente)

    def __init__(self, tag_spool: str, sheets_repo, metadata_repo):
        """
        Initialize ARM state machine for a specific spool.

        Args:
            tag_spool: Spool identifier
            sheets_repo: SheetsRepository for column updates
            metadata_repo: MetadataRepository for event logging
        """
        super().__init__(tag_spool, sheets_repo, metadata_repo)

    async def on_enter_en_progreso(self, event_data):
        """
        Callback when ARM work starts.

        Updates Armador column with worker name.

        Args:
            event_data: Transition event data with kwargs containing worker_nombre
        """
        worker_nombre = event_data.kwargs.get('worker_nombre')
        if worker_nombre and self.sheets_repo:
            # Find row for this spool
            row_num = self.sheets_repo.find_row_by_column_value(
                sheet_name=config.HOJA_OPERACIONES_NOMBRE,
                column_letter="G",  # TAG_SPOOL column
                value=self.tag_spool
            )

            if row_num:
                # Update Armador column
                self.sheets_repo.update_cell_by_column_name(
                    sheet_name=config.HOJA_OPERACIONES_NOMBRE,
                    row=row_num,
                    column_name="Armador",
                    value=worker_nombre
                )

    async def on_enter_completado(self, event_data):
        """
        Callback when ARM work completes.

        Updates Fecha_Armado column with completion date.

        Args:
            event_data: Transition event data with kwargs containing fecha_operacion
        """
        fecha = event_data.kwargs.get('fecha_operacion', date.today())
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

                # Update Fecha_Armado column
                self.sheets_repo.update_cell_by_column_name(
                    sheet_name=config.HOJA_OPERACIONES_NOMBRE,
                    row=row_num,
                    column_name="Fecha_Armado",
                    value=fecha_str
                )

    async def on_enter_pendiente(self, event_data):
        """
        Callback when returning to pendiente state (CANCELAR).

        Clears Armador column to revert the spool to unassigned state.

        Args:
            event_data: Transition event data
        """
        # Only clear if coming from EN_PROGRESO (CANCELAR transition)
        if event_data.transition.source == self.en_progreso and self.sheets_repo:
            # Find row for this spool
            row_num = self.sheets_repo.find_row_by_column_value(
                sheet_name=config.HOJA_OPERACIONES_NOMBRE,
                column_letter="G",  # TAG_SPOOL column
                value=self.tag_spool
            )

            if row_num:
                # Clear Armador column
                self.sheets_repo.update_cell_by_column_name(
                    sheet_name=config.HOJA_OPERACIONES_NOMBRE,
                    row=row_num,
                    column_name="Armador",
                    value=""
                )
