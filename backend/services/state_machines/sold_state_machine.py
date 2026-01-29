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
    completado = State("completado", final=True)

    # Define transitions
    iniciar = pendiente.to(en_progreso)
    completar = en_progreso.to(completado)
    cancelar = en_progreso.to(pendiente)

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

    async def on_enter_en_progreso(self, worker_nombre: str = None, **kwargs):
        """
        Callback when SOLD work starts.

        Updates Soldador column with worker name.

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
                # Update Soldador column
                self.sheets_repo.update_cell_by_column_name(
                    sheet_name=config.HOJA_OPERACIONES_NOMBRE,
                    row=row_num,
                    column_name="Soldador",
                    value=worker_nombre
                )

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
                # Clear Soldador column
                self.sheets_repo.update_cell_by_column_name(
                    sheet_name=config.HOJA_OPERACIONES_NOMBRE,
                    row=row_num,
                    column_name="Soldador",
                    value=""
                )
