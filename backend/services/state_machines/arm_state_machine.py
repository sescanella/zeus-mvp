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
import logging

logger = logging.getLogger(__name__)


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
    pausado = State("pausado")  # NEW: Intermediate paused state
    completado = State("completado", final=True)

    # Define transitions
    iniciar = pendiente.to(en_progreso)
    pausar = en_progreso.to(pausado)  # NEW: Pause work
    reanudar = pausado.to(en_progreso)  # NEW: Resume work
    completar = en_progreso.to(completado)
    cancelar = (en_progreso.to(pendiente) |  # Cancel in-progress work
                pausado.to(pendiente))        # Cancel paused work

    def __init__(self, tag_spool: str, sheets_repo, metadata_repo):
        """
        Initialize ARM state machine for a specific spool.

        Args:
            tag_spool: Spool identifier
            sheets_repo: SheetsRepository for column updates
            metadata_repo: MetadataRepository for event logging
        """
        super().__init__(tag_spool, sheets_repo, metadata_repo)

    async def on_enter_en_progreso(self, worker_nombre: str = None, source: 'State' = None, **kwargs):
        """
        Callback when ARM work starts or resumes.

        Behavior:
        - Initial start (pendiente → en_progreso): Update Armador with worker_nombre
        - Resume (pausado → en_progreso): Do NOT update Armador (preserve original)

        Args:
            worker_nombre: Worker name (only used for initial start)
            source: Source state from transition (auto-injected by statemachine)
            **kwargs: Other event arguments (ignored)
        """
        if worker_nombre and self.sheets_repo:
            # Check if resuming from pausado state
            if source and source.id == 'pausado':
                # Resume: Do not modify Armador (preserve original worker)
                logger.info(f"ARM resumed for {self.tag_spool}, Armador unchanged")
                return

            # Initial start: Update Armador column
            row_num = self.sheets_repo.find_row_by_column_value(
                sheet_name=config.HOJA_OPERACIONES_NOMBRE,
                column_letter="G",  # TAG_SPOOL column
                value=self.tag_spool
            )

            if row_num:
                self.sheets_repo.update_cell_by_column_name(
                    sheet_name=config.HOJA_OPERACIONES_NOMBRE,
                    row=row_num,
                    column_name="Armador",
                    value=worker_nombre
                )
                logger.info(f"ARM started for {self.tag_spool}, Armador set to {worker_nombre}")

    async def on_enter_pausado(self, **kwargs):
        """
        Callback when ARM work is paused.

        This callback is intentionally empty because:
        - Armador column should remain set (worker who initiated ARM is preserved)
        - Ocupado_Por is cleared by OccupationService.pausar() (not by state machine)
        - Estado_Detalle is updated by StateService after this transition

        Separation of concerns:
        - State machine manages operation state (pendiente/en_progreso/pausado/completado)
        - OccupationService manages occupation locks (Ocupado_Por, Fecha_Ocupacion)
        - StateService coordinates both and updates Estado_Detalle

        Args:
            **kwargs: Event arguments (ignored)
        """
        # No Sheets update needed
        # Armador persists to track who initiated ARM before pause
        logger.info(f"ARM paused for {self.tag_spool}, state: en_progreso → pausado")

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
            source: Source state from transition (en_progreso or pausado)
            **kwargs: Other event arguments (ignored)
        """
        # Clear Armador if coming from EN_PROGRESO or PAUSADO (CANCELAR transition)
        if source and source.id in ['en_progreso', 'pausado'] and self.sheets_repo:
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
                logger.info(f"ARM cancelled: {source.id} → pendiente, Armador cleared for {self.tag_spool}")
