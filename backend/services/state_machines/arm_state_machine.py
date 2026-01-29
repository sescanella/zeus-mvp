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

    async def on_enter_en_progreso(self, worker_nombre: str = None, **kwargs):
        """
        Callback when ARM work starts.

        Updates Armador column with worker name.

        Args:
            worker_nombre: Worker name assigned to this spool (injected by dependency injection)
            **kwargs: Other event arguments (ignored)
        """
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

    async def on_enter_completado(self, fecha_operacion: date = None, **kwargs):
        """
        Callback when ARM work completes.

        Updates Fecha_Armado column with completion date.

        Args:
            fecha_operacion: Completion date (injected by dependency injection)
            **kwargs: Other event arguments (ignored)
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

                # Update Fecha_Armado column
                self.sheets_repo.update_cell_by_column_name(
                    sheet_name=config.HOJA_OPERACIONES_NOMBRE,
                    row=row_num,
                    column_name="Fecha_Armado",
                    value=fecha_str
                )

    async def on_enter_pendiente(self, source: 'State' = None, **kwargs):
        """
        Callback when returning to pendiente state (CANCELAR).

        Clears Armador column to revert the spool to unassigned state.

        Args:
            source: Source state from transition (injected by dependency injection)
            **kwargs: Other event arguments (ignored)
        """
        # Only clear if coming from EN_PROGRESO (CANCELAR transition)
        if source and source.id == 'en_progreso' and self.sheets_repo:
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
