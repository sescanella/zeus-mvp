"""
CycleCounterService - Manages reparación cycle counting without dedicated column.

Cycle count embedded in Estado_Detalle:
- "RECHAZADO (Ciclo 1/3)" = First rejection
- "RECHAZADO (Ciclo 2/3)" = Second rejection
- "RECHAZADO (Ciclo 3/3)" = Third rejection (next RECHAZADO → BLOQUEADO)
- "BLOQUEADO - Contactar supervisor" = Exceeded limit
"""

import re
from typing import Optional


class CycleCounterService:
    """
    Manage reparación cycle counting without dedicated column.

    Cycle count embedded in Estado_Detalle:
    - "RECHAZADO (Ciclo 1/3)" = First rejection
    - "RECHAZADO (Ciclo 2/3)" = Second rejection
    - "RECHAZADO (Ciclo 3/3)" = Third rejection (next RECHAZADO → BLOQUEADO)
    - "BLOQUEADO - Contactar supervisor" = Exceeded limit

    Features:
    - Parse cycle from Estado_Detalle string
    - Increment cycle count on each RECHAZADO
    - Check if spool should be blocked (>= MAX_CYCLES)
    - Build formatted estado strings with cycle info
    - Reset cycle counter after APROBADO
    """

    MAX_CYCLES = 3
    CYCLE_PATTERN = re.compile(r"Ciclo (\d+)/3")

    def extract_cycle_count(self, estado_detalle: str) -> int:
        """
        Parse cycle count from Estado_Detalle string.

        Args:
            estado_detalle: Current Estado_Detalle value

        Returns:
            int: Current cycle count (0 if not found, MAX_CYCLES if BLOQUEADO)

        Examples:
            >>> counter = CycleCounterService()
            >>> counter.extract_cycle_count("RECHAZADO (Ciclo 2/3)")
            2
            >>> counter.extract_cycle_count("BLOQUEADO - Contactar supervisor")
            3
            >>> counter.extract_cycle_count("PENDIENTE_METROLOGIA")
            0
        """
        if not estado_detalle:
            return 0

        # Check for BLOQUEADO first
        if "BLOQUEADO" in estado_detalle:
            return self.MAX_CYCLES

        # Try to extract cycle number
        match = self.CYCLE_PATTERN.search(estado_detalle)
        if match:
            return int(match.group(1))

        # No cycle info found
        return 0

    def increment_cycle(self, current_cycle: int) -> int:
        """
        Increment cycle count on new RECHAZADO event.

        Args:
            current_cycle: Current cycle number

        Returns:
            int: Incremented cycle (capped at MAX_CYCLES)

        Examples:
            >>> counter = CycleCounterService()
            >>> counter.increment_cycle(0)
            1
            >>> counter.increment_cycle(2)
            3
            >>> counter.increment_cycle(3)
            3
        """
        return min(current_cycle + 1, self.MAX_CYCLES)

    def should_block(self, current_cycle: int) -> bool:
        """
        Check if spool should transition to BLOQUEADO.

        Args:
            current_cycle: Current cycle count

        Returns:
            bool: True if reached max cycles (3)

        Examples:
            >>> counter = CycleCounterService()
            >>> counter.should_block(2)
            False
            >>> counter.should_block(3)
            True
        """
        return current_cycle >= self.MAX_CYCLES

    def build_rechazado_estado(self, cycle: int) -> str:
        """
        Build Estado_Detalle for RECHAZADO state with cycle info.

        Args:
            cycle: Current cycle number (1-3)

        Returns:
            str: Formatted Estado_Detalle

        Examples:
            >>> counter = CycleCounterService()
            >>> counter.build_rechazado_estado(1)
            'RECHAZADO (Ciclo 1/3) - Pendiente reparación'
            >>> counter.build_rechazado_estado(3)
            'BLOQUEADO - Contactar supervisor'
        """
        if cycle >= self.MAX_CYCLES:
            return "BLOQUEADO - Contactar supervisor"

        return f"RECHAZADO (Ciclo {cycle}/{self.MAX_CYCLES}) - Pendiente reparación"

    def build_reparacion_estado(
        self,
        state: str,
        cycle: int,
        worker: Optional[str] = None
    ) -> str:
        """
        Build estado for EN_REPARACION, REPARACION_PAUSADA states.

        Args:
            state: State name (en_reparacion, reparacion_pausada)
            cycle: Current cycle count
            worker: Optional worker name for EN_REPARACION state

        Returns:
            str: Formatted Estado_Detalle

        Examples:
            >>> counter = CycleCounterService()
            >>> counter.build_reparacion_estado("en_reparacion", 2, "MR(93)")
            'EN_REPARACION (Ciclo 2/3) - Ocupado: MR(93)'
            >>> counter.build_reparacion_estado("reparacion_pausada", 2)
            'REPARACION_PAUSADA (Ciclo 2/3)'
        """
        if state == "en_reparacion":
            if worker:
                return f"EN_REPARACION (Ciclo {cycle}/{self.MAX_CYCLES}) - Ocupado: {worker}"
            return f"EN_REPARACION (Ciclo {cycle}/{self.MAX_CYCLES})"

        if state == "reparacion_pausada":
            return f"REPARACION_PAUSADA (Ciclo {cycle}/{self.MAX_CYCLES})"

        # Fallback for unknown states
        return f"{state.upper()} (Ciclo {cycle}/{self.MAX_CYCLES})"

    def reset_cycle(self) -> str:
        """
        Reset cycle counter after APROBADO.

        Returns:
            str: Estado_Detalle with no cycle info

        Examples:
            >>> counter = CycleCounterService()
            >>> counter.reset_cycle()
            'METROLOGIA_APROBADO ✓'
        """
        return "METROLOGIA_APROBADO ✓"
