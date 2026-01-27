"""
EstadoDetalleBuilder - Formats Estado_Detalle display strings.

Combines occupation status with ARM/SOLD state to produce human-readable
status strings for the Estado_Detalle column.

Display formats:
- Occupied: "MR(93) trabajando ARM (ARM en progreso, SOLD pendiente)"
- Available: "Disponible - ARM completado, SOLD pendiente"
"""

from typing import Optional


class EstadoDetalleBuilder:
    """
    Builder for Estado_Detalle display strings.

    Combines:
    - Occupation status (who is working)
    - ARM state (pendiente/en_progreso/completado)
    - SOLD state (pendiente/en_progreso/completado)
    """

    def build(
        self,
        ocupado_por: Optional[str],
        arm_state: str,
        sold_state: str,
        operacion_actual: Optional[str] = None
    ) -> str:
        """
        Build Estado_Detalle display string.

        Args:
            ocupado_por: Worker name occupying the spool (None if available)
            arm_state: ARM state (pendiente/en_progreso/completado)
            sold_state: SOLD state (pendiente/en_progreso/completado)
            operacion_actual: Current operation being worked (ARM/SOLD)

        Returns:
            Formatted display string

        Examples:
            >>> builder = EstadoDetalleBuilder()
            >>> builder.build("MR(93)", "en_progreso", "pendiente", "ARM")
            'MR(93) trabajando ARM (ARM en progreso, SOLD pendiente)'
            >>> builder.build(None, "completado", "pendiente")
            'Disponible - ARM completado, SOLD pendiente'
        """
        arm_display = self._state_to_display(arm_state)
        sold_display = self._state_to_display(sold_state)

        if ocupado_por:
            # Format: "Worker trabajando OPERATION (ARM state, SOLD state)"
            operacion_label = operacion_actual if operacion_actual else "operación"
            return f"{ocupado_por} trabajando {operacion_label} (ARM {arm_display}, SOLD {sold_display})"
        else:
            # Format: "Disponible - ARM state, SOLD state"
            return f"Disponible - ARM {arm_display}, SOLD {sold_display}"

    def _state_to_display(self, state: str) -> str:
        """
        Convert state ID to Spanish display term.

        Args:
            state: State ID (pendiente/en_progreso/completado)

        Returns:
            Spanish display term
        """
        mapping = {
            "pendiente": "pendiente",
            "en_progreso": "en progreso",
            "completado": "completado"
        }
        return mapping.get(state, state)
