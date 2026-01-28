"""
REPARACION (Repair) operation state machine.

Manages repair workflow for rejected spools with 4 states:
- RECHAZADO → EN_REPARACION (tomar)
- EN_REPARACION → REPARACION_PAUSADA (pausar)
- REPARACION_PAUSADA → EN_REPARACION (tomar - resume)
- EN_REPARACION → PENDIENTE_METROLOGIA (completar)
- EN_REPARACION/REPARACION_PAUSADA → RECHAZADO (cancelar)

Callbacks update Operaciones sheet columns (Ocupado_Por, Fecha_Ocupacion, Estado_Detalle) automatically.
Integrates with CycleCounterService to maintain cycle count across state transitions.
"""

from statemachine import State
from backend.services.state_machines.base_state_machine import BaseOperationStateMachine
from backend.config import config
from datetime import date


class REPARACIONStateMachine(BaseOperationStateMachine):
    """
    REPARACION operation state machine with occupation management.

    States:
    - rechazado (initial): Failed metrología, awaiting repair
    - en_reparacion: Worker actively repairing (ocupado_por set)
    - reparacion_pausada: Worker paused mid-repair (ocupado_por cleared)
    - pendiente_metrologia (final): Repair complete, ready for re-inspection

    Transitions:
    - tomar: rechazado → en_reparacion, reparacion_pausada → en_reparacion
    - pausar: en_reparacion → reparacion_pausada
    - completar: en_reparacion → pendiente_metrologia
    - cancelar: en_reparacion/reparacion_pausada → rechazado
    """

    # Define states
    rechazado = State("rechazado", initial=True)
    en_reparacion = State("en_reparacion")
    reparacion_pausada = State("reparacion_pausada")
    pendiente_metrologia = State("pendiente_metrologia", final=True)

    # Define transitions
    tomar = (
        rechazado.to(en_reparacion) |
        reparacion_pausada.to(en_reparacion)
    )
    pausar = en_reparacion.to(reparacion_pausada)
    completar = en_reparacion.to(pendiente_metrologia)
    cancelar = (
        en_reparacion.to(rechazado) |
        reparacion_pausada.to(rechazado)
    )

    def __init__(self, tag_spool: str, sheets_repo, metadata_repo, cycle_counter=None):
        """
        Initialize REPARACION state machine for a specific spool.

        Args:
            tag_spool: Spool identifier
            sheets_repo: SheetsRepository for column updates
            metadata_repo: MetadataRepository for event logging
            cycle_counter: CycleCounterService for cycle tracking
        """
        super().__init__(tag_spool, sheets_repo, metadata_repo)
        self.cycle_counter = cycle_counter

    async def on_enter_en_reparacion(self, worker_id=None, worker_nombre=None, **kwargs):
        """
        Callback when repair work starts or resumes.

        Updates:
        - Ocupado_Por: Worker name
        - Fecha_Ocupacion: Current date
        - Estado_Detalle: EN_REPARACION (Ciclo X/3) - Ocupado: Worker

        Args:
            worker_id: Worker ID
            worker_nombre: Worker name (format: "INICIALES(ID)")
            **kwargs: Additional event data
        """
        if not worker_nombre or not self.sheets_repo:
            return

        # Find row for this spool
        row_num = self.sheets_repo.find_row_by_column_value(
            sheet_name=config.HOJA_OPERACIONES_NOMBRE,
            column_letter="G",  # TAG_SPOOL column
            value=self.tag_spool
        )

        if not row_num:
            return

        # Get current cycle count from Estado_Detalle
        current_estado = self.sheets_repo.get_cell_value(
            sheet_name=config.HOJA_OPERACIONES_NOMBRE,
            row=row_num,
            column_name="Estado_Detalle"
        )

        # Extract cycle count (0 if not found)
        cycle = 0
        if self.cycle_counter:
            cycle = self.cycle_counter.extract_cycle_count(current_estado or "")

        # Build estado with cycle info
        estado_detalle = f"EN_REPARACION (Ciclo {cycle}/{self.cycle_counter.MAX_CYCLES}) - Ocupado: {worker_nombre}" if self.cycle_counter else f"EN_REPARACION - Ocupado: {worker_nombre}"

        # Format date as DD-MM-YYYY
        fecha_str = date.today().strftime("%d-%m-%Y")

        # Update Ocupado_Por, Fecha_Ocupacion, Estado_Detalle atomically
        self.sheets_repo.batch_update_by_column_name(
            sheet_name=config.HOJA_OPERACIONES_NOMBRE,
            updates=[
                {"row": row_num, "column_name": "Ocupado_Por", "value": worker_nombre},
                {"row": row_num, "column_name": "Fecha_Ocupacion", "value": fecha_str},
                {"row": row_num, "column_name": "Estado_Detalle", "value": estado_detalle}
            ]
        )

    async def on_enter_reparacion_pausada(self, **kwargs):
        """
        Callback when worker pauses repair work.

        Updates:
        - Ocupado_Por: Cleared (empty string)
        - Fecha_Ocupacion: Cleared (empty string)
        - Estado_Detalle: REPARACION_PAUSADA (Ciclo X/3)

        Args:
            **kwargs: Event data (unused)
        """
        if not self.sheets_repo:
            return

        # Find row for this spool
        row_num = self.sheets_repo.find_row_by_column_value(
            sheet_name=config.HOJA_OPERACIONES_NOMBRE,
            column_letter="G",  # TAG_SPOOL column
            value=self.tag_spool
        )

        if not row_num:
            return

        # Get current cycle count from Estado_Detalle
        current_estado = self.sheets_repo.get_cell_value(
            sheet_name=config.HOJA_OPERACIONES_NOMBRE,
            row=row_num,
            column_name="Estado_Detalle"
        )

        # Extract cycle count
        cycle = 0
        if self.cycle_counter:
            cycle = self.cycle_counter.extract_cycle_count(current_estado or "")

        # Build estado with cycle info
        estado_detalle = f"REPARACION_PAUSADA (Ciclo {cycle}/{self.cycle_counter.MAX_CYCLES})" if self.cycle_counter else "REPARACION_PAUSADA"

        # Clear occupation fields and update estado
        self.sheets_repo.batch_update_by_column_name(
            sheet_name=config.HOJA_OPERACIONES_NOMBRE,
            updates=[
                {"row": row_num, "column_name": "Ocupado_Por", "value": ""},
                {"row": row_num, "column_name": "Fecha_Ocupacion", "value": ""},
                {"row": row_num, "column_name": "Estado_Detalle", "value": estado_detalle}
            ]
        )

    async def on_enter_pendiente_metrologia(self, **kwargs):
        """
        Callback when repair work completes.

        Updates:
        - Ocupado_Por: Cleared (empty string)
        - Fecha_Ocupacion: Cleared (empty string)
        - Estado_Detalle: PENDIENTE_METROLOGIA

        Note: Spool automatically returns to metrología queue for re-inspection.
        Cycle counter is preserved until next metrología decision (APROBADO resets, RECHAZADO increments).

        Args:
            **kwargs: Event data (unused)
        """
        if not self.sheets_repo:
            return

        # Find row for this spool
        row_num = self.sheets_repo.find_row_by_column_value(
            sheet_name=config.HOJA_OPERACIONES_NOMBRE,
            column_letter="G",  # TAG_SPOOL column
            value=self.tag_spool
        )

        if not row_num:
            return

        # Clear occupation fields and set PENDIENTE_METROLOGIA estado
        self.sheets_repo.batch_update_by_column_name(
            sheet_name=config.HOJA_OPERACIONES_NOMBRE,
            updates=[
                {"row": row_num, "column_name": "Ocupado_Por", "value": ""},
                {"row": row_num, "column_name": "Fecha_Ocupacion", "value": ""},
                {"row": row_num, "column_name": "Estado_Detalle", "value": "PENDIENTE_METROLOGIA"}
            ]
        )

    async def on_enter_rechazado(self, event=None, **kwargs):
        """
        Callback when returning to rechazado state (CANCELAR transition).

        Updates:
        - Ocupado_Por: Cleared (empty string)
        - Fecha_Ocupacion: Cleared (empty string)
        - Estado_Detalle: RECHAZADO (Ciclo X/3) - restores previous cycle info

        Args:
            event: Transition event (optional)
            **kwargs: Additional event data
        """
        # Only clear if coming from EN_REPARACION or REPARACION_PAUSADA (CANCELAR transition)
        # Check if event has transition source
        if event and hasattr(event, 'transition') and hasattr(event.transition, 'source'):
            if event.transition.source not in [self.en_reparacion, self.reparacion_pausada]:
                return
        # If no event or no transition info, skip (initial state setup)
        elif not event:
            return

        if not self.sheets_repo:
            return

        # Find row for this spool
        row_num = self.sheets_repo.find_row_by_column_value(
            sheet_name=config.HOJA_OPERACIONES_NOMBRE,
            column_letter="G",  # TAG_SPOOL column
            value=self.tag_spool
        )

        if not row_num:
            return

        # Get current cycle count from Estado_Detalle
        current_estado = self.sheets_repo.get_cell_value(
            sheet_name=config.HOJA_OPERACIONES_NOMBRE,
            row=row_num,
            column_name="Estado_Detalle"
        )

        # Extract cycle count
        cycle = 0
        if self.cycle_counter:
            cycle = self.cycle_counter.extract_cycle_count(current_estado or "")

        # Build RECHAZADO estado with preserved cycle
        estado_detalle = self.cycle_counter.build_rechazado_estado(cycle) if self.cycle_counter else "RECHAZADO - Pendiente reparación"

        # Clear occupation fields and restore RECHAZADO estado
        self.sheets_repo.batch_update_by_column_name(
            sheet_name=config.HOJA_OPERACIONES_NOMBRE,
            updates=[
                {"row": row_num, "column_name": "Ocupado_Por", "value": ""},
                {"row": row_num, "column_name": "Fecha_Ocupacion", "value": ""},
                {"row": row_num, "column_name": "Estado_Detalle", "value": estado_detalle}
            ]
        )
