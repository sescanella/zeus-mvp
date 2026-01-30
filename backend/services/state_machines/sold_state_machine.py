"""
SOLD (Welding) operation state machine.

Manages SOLD operation lifecycle with ARM dependency:
- PENDIENTE → EN_PROGRESO (iniciar) - REQUIRES ARM initiated
- EN_PROGRESO → COMPLETADO (completar)
- EN_PROGRESO → PENDIENTE (cancelar)

Guard condition prevents SOLD from starting if ARM not initiated.
"""

from statemachine import State
from backend.services.state_machines.base_state_machine import BaseOperationStateMachine
from backend.exceptions import DependenciasNoSatisfechasError
from backend.config import config
from datetime import date
import logging

logger = logging.getLogger(__name__)


class SOLDStateMachine(BaseOperationStateMachine):
    """
    SOLD operation state machine with ARM dependency.

    States:
    - pendiente (initial): SOLD not started (Soldador = None)
    - en_progreso: SOLD in progress (Soldador != None, Fecha_Soldadura = None)
    - completado (final): SOLD completed (Fecha_Soldadura != None)

    Transitions:
    - iniciar: pendiente → en_progreso (GUARDED: ARM must be initiated)
    - completar: en_progreso → completado
    - cancelar: en_progreso → pendiente

    Guards:
    - arm_not_initiated: Blocks iniciar if ARM not started (Armador = None)
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
        Initialize SOLD state machine for a specific spool.

        Args:
            tag_spool: Spool identifier
            sheets_repo: SheetsRepository for column updates and ARM state check
            metadata_repo: MetadataRepository for event logging
        """
        super().__init__(tag_spool, sheets_repo, metadata_repo)

    def arm_not_initiated(self) -> bool:
        """
        Guard condition: Check if ARM is initiated.

        Returns:
            True if ARM NOT initiated (blocks transition)
            False if ARM initiated (allows transition)
        """
        # If sheets_repo is None (during testing), assume ARM is initiated
        if self.sheets_repo is None:
            return False

        # Read spool to check ARM status
        spool = self.sheets_repo.get_spool_by_tag(self.tag_spool)
        arm_initiated = spool.armador is not None

        return not arm_initiated

    def validate_arm_initiated(self):
        """
        Validator: Raise exception if ARM not initiated.

        Raises:
            DependenciasNoSatisfechasError: If ARM not initiated
        """
        if self.arm_not_initiated():
            raise DependenciasNoSatisfechasError(
                tag_spool=self.tag_spool,
                operacion="SOLD",
                dependencia_faltante="ARM iniciado",
                detalle="SOLD no puede iniciarse sin ARM iniciado"
            )

    def before_iniciar(self, **kwargs):
        """
        Before iniciar transition: Validate ARM dependency.

        Args:
            **kwargs: Event arguments (ignored)

        Raises:
            DependenciasNoSatisfechasError: If ARM not initiated
        """
        self.validate_arm_initiated()

    async def on_enter_en_progreso(self, worker_nombre: str = None, source: 'State' = None, **kwargs):
        """
        Callback when SOLD work starts or resumes.

        Behavior:
        - Initial start (pendiente → en_progreso): Update Soldador with worker_nombre
        - Resume (pausado → en_progreso): Do NOT update Soldador (preserve original)

        Args:
            worker_nombre: Worker name (only used for initial start)
            source: Source state from transition (auto-injected by statemachine)
            **kwargs: Other event arguments (ignored)
        """
        if worker_nombre and self.sheets_repo:
            # Check if resuming from pausado state
            if source and source.id == 'pausado':
                # Resume: Do not modify Soldador (preserve original worker)

                logger.info(f"SOLD resumed for {self.tag_spool}, Soldador unchanged")
                return

            # Initial start: Update Soldador column
            row_num = self.sheets_repo.find_row_by_column_value(
                sheet_name=config.HOJA_OPERACIONES_NOMBRE,
                column_letter="G",  # TAG_SPOOL column
                value=self.tag_spool
            )

            if row_num:
                self.sheets_repo.update_cell_by_column_name(
                    sheet_name=config.HOJA_OPERACIONES_NOMBRE,
                    row=row_num,
                    column_name="Soldador",
                    value=worker_nombre
                )

                logger.info(f"SOLD started for {self.tag_spool}, Soldador set to {worker_nombre}")

    async def on_enter_pausado(self, **kwargs):
        """
        Callback when SOLD work is paused.

        This callback is intentionally empty because:
        - Soldador column should remain set (worker who initiated SOLD is preserved)
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
        # Soldador persists to track who initiated SOLD before pause
        logger.info(f"SOLD paused for {self.tag_spool}, state: en_progreso → pausado")

    async def on_enter_completado(self, fecha_operacion: date = None, **kwargs):
        """
        Callback when SOLD work completes.

        Updates Fecha_Soldadura column with completion date.

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

                # Update Fecha_Soldadura column
                self.sheets_repo.update_cell_by_column_name(
                    sheet_name=config.HOJA_OPERACIONES_NOMBRE,
                    row=row_num,
                    column_name="Fecha_Soldadura",
                    value=fecha_str
                )

    async def on_enter_pendiente(self, source: 'State' = None, **kwargs):
        """
        Callback when returning to pendiente state (CANCELAR).

        Clears Soldador column to revert the spool to unassigned state.

        Args:
            source: Source state from transition (en_progreso or pausado)
            **kwargs: Other event arguments (ignored)
        """
        # Clear Soldador if coming from EN_PROGRESO or PAUSADO (CANCELAR transition)
        if source and source.id in ['en_progreso', 'pausado'] and self.sheets_repo:
            # Find row for this spool
            row_num = self.sheets_repo.find_row_by_column_value(
                sheet_name=config.HOJA_OPERACIONES_NOMBRE,
                column_letter="G",  # TAG_SPOOL column
                value=self.tag_spool
            )

            if row_num:
                # Clear Soldador column
                self.sheets_repo.update_cell_by_column_name(
                    sheet_name=config.HOJA_OPERACIONES_NOMBRE,
                    row=row_num,
                    column_name="Soldador",
                    value=""
                )

                logger.info(f"SOLD cancelled: {source.id} → pendiente, Soldador cleared for {self.tag_spool}")
