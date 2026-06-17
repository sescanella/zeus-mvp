"""
REPARACION (Repair) operation state machine.

Manages repair workflow for rejected spools with 4 states:
- RECHAZADO → EN_REPARACION (tomar)
- EN_REPARACION → REPARACION_PAUSADA (pausar)
- REPARACION_PAUSADA → EN_REPARACION (tomar - resume)
- EN_REPARACION → PENDIENTE_METROLOGIA (completar)
- EN_REPARACION/REPARACION_PAUSADA → RECHAZADO (cancelar)

Callbacks update Operaciones sheet columns (Ocupado_Por, Fecha_Ocupacion,
Estado_Detalle) automatically. There is no cycle counter and no BLOQUEADO
escalation — a spool can move through this cycle as many times as needed.
"""

from statemachine import State
from backend.services.state_machines.base_state_machine import BaseOperationStateMachine
from backend.config import config
from datetime import date


# Estado_Detalle constants written by this state machine.
ESTADO_DETALLE_RECHAZADO = "RECHAZADO - Pendiente reparación"
ESTADO_DETALLE_REPARACION_PAUSADA = "REPARACION_PAUSADA"
ESTADO_DETALLE_PENDIENTE_METROLOGIA = "PENDIENTE_METROLOGIA"


def _build_en_reparacion_estado(worker_nombre: str) -> str:
    """Format the EN_REPARACION Estado_Detalle for a given worker name."""
    return f"EN_REPARACION - Ocupado: {worker_nombre}"


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

    def __init__(self, tag_spool: str, sheets_repo, metadata_repo, *, start_value: str = None):
        """
        Initialize REPARACION state machine for a specific spool.

        Args:
            tag_spool: Spool identifier
            sheets_repo: SheetsRepository for column updates
            metadata_repo: MetadataRepository for event logging
            start_value: State ID to hydrate to ("rechazado", "en_reparacion",
                "reparacion_pausada"). Pass when resuming a spool already past
                the initial state.
        """
        super().__init__(tag_spool, sheets_repo, metadata_repo, start_value=start_value)

    async def on_enter_en_reparacion(self, worker_id=None, worker_nombre=None, **kwargs):
        """
        Callback when repair work starts or resumes.

        Updates:
        - Ocupado_Por: Worker name
        - Fecha_Ocupacion: Current date
        - Estado_Detalle: EN_REPARACION - Ocupado: <worker>

        Args:
            worker_id: Worker ID
            worker_nombre: Worker name (format: "INICIALES(ID)")
            **kwargs: Additional event data
        """
        if not worker_nombre or not self.sheets_repo:
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

        estado_detalle = _build_en_reparacion_estado(worker_nombre)

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
        - Estado_Detalle: REPARACION_PAUSADA

        Args:
            **kwargs: Event data (unused)
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

        # Clear occupation fields and update estado
        self.sheets_repo.batch_update_by_column_name(
            sheet_name=config.HOJA_OPERACIONES_NOMBRE,
            updates=[
                {"row": row_num, "column_name": "Ocupado_Por", "value": ""},
                {"row": row_num, "column_name": "Fecha_Ocupacion", "value": ""},
                {"row": row_num, "column_name": "Estado_Detalle", "value": ESTADO_DETALLE_REPARACION_PAUSADA}
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

        Args:
            **kwargs: Event data (unused)
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

        # Clear occupation fields and set PENDIENTE_METROLOGIA estado
        self.sheets_repo.batch_update_by_column_name(
            sheet_name=config.HOJA_OPERACIONES_NOMBRE,
            updates=[
                {"row": row_num, "column_name": "Ocupado_Por", "value": ""},
                {"row": row_num, "column_name": "Fecha_Ocupacion", "value": ""},
                {"row": row_num, "column_name": "Estado_Detalle", "value": ESTADO_DETALLE_PENDIENTE_METROLOGIA}
            ]
        )

    async def on_enter_rechazado(self, event=None, **kwargs):
        """
        Callback when returning to rechazado state (CANCELAR transition).

        Updates:
        - Ocupado_Por: Cleared (empty string)
        - Fecha_Ocupacion: Cleared (empty string)
        - Estado_Detalle: RECHAZADO - Pendiente reparación

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
        tag_col_letter = self.sheets_repo.get_tag_spool_column_letter(config.HOJA_OPERACIONES_NOMBRE)
        row_num = self.sheets_repo.find_row_by_column_value(
            sheet_name=config.HOJA_OPERACIONES_NOMBRE,
            column_letter=tag_col_letter,
            value=self.tag_spool
        )

        if not row_num:
            return

        # Clear occupation fields and restore RECHAZADO estado
        self.sheets_repo.batch_update_by_column_name(
            sheet_name=config.HOJA_OPERACIONES_NOMBRE,
            updates=[
                {"row": row_num, "column_name": "Ocupado_Por", "value": ""},
                {"row": row_num, "column_name": "Fecha_Ocupacion", "value": ""},
                {"row": row_num, "column_name": "Estado_Detalle", "value": ESTADO_DETALLE_RECHAZADO}
            ]
        )
