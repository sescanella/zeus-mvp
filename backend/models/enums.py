"""
Enumeraciones para el sistema ZEUES.

Define los tipos de operaciones y estados posibles de las acciones.
"""
from enum import Enum


class ActionType(str, Enum):
    """
    Tipos de acción soportados en el sistema.

    ARM: Armado de spool
    SOLD: Soldado de spool
    METROLOGIA: Metrología/QC de spool
    REPARACION: Reparación de spool rechazado
    """
    ARM = "ARM"
    SOLD = "SOLD"
    METROLOGIA = "METROLOGIA"
    REPARACION = "REPARACION"


class ActionStatus(str, Enum):
    """
    Estados posibles de una acción en Google Sheets.

    PENDIENTE: 0 - Acción no iniciada
    EN_PROGRESO: 0.1 - Acción iniciada pero no completada
    COMPLETADO: 1.0 - Acción finalizada
    """
    PENDIENTE = "PENDIENTE"
    EN_PROGRESO = "EN_PROGRESO"
    COMPLETADO = "COMPLETADO"


class EventoTipo(str, Enum):
    """
    Tipos de eventos soportados en el sistema v3.0.

    Eventos v2.1:
    - INICIAR_ARM, COMPLETAR_ARM, CANCELAR_ARM
    - INICIAR_SOLD, COMPLETAR_SOLD, CANCELAR_SOLD
    - INICIAR_METROLOGIA, COMPLETAR_METROLOGIA

    Eventos v3.0:
    - TOMAR_SPOOL: Worker ocupa un spool (marca inicio de trabajo)
    - PAUSAR_SPOOL: Worker pausa trabajo en spool (libera recurso)

    Eventos Phase 6 (Reparación):
    - TOMAR_REPARACION: Worker takes rejected spool for repair
    - PAUSAR_REPARACION: Worker pauses repair work
    - COMPLETAR_REPARACION: Worker completes repair (returns to metrología queue)
    - CANCELAR_REPARACION: Worker cancels repair (returns to RECHAZADO)
    """
    # v2.1 Events (legacy)
    INICIAR_ARM = "INICIAR_ARM"
    COMPLETAR_ARM = "COMPLETAR_ARM"
    CANCELAR_ARM = "CANCELAR_ARM"
    INICIAR_SOLD = "INICIAR_SOLD"
    COMPLETAR_SOLD = "COMPLETAR_SOLD"
    CANCELAR_SOLD = "CANCELAR_SOLD"
    INICIAR_METROLOGIA = "INICIAR_METROLOGIA"
    COMPLETAR_METROLOGIA = "COMPLETAR_METROLOGIA"

    # v3.0 Events (new)
    TOMAR_SPOOL = "TOMAR_SPOOL"
    PAUSAR_SPOOL = "PAUSAR_SPOOL"

    # Phase 6 Events (Reparación)
    TOMAR_REPARACION = "TOMAR_REPARACION"
    PAUSAR_REPARACION = "PAUSAR_REPARACION"
    COMPLETAR_REPARACION = "COMPLETAR_REPARACION"
    CANCELAR_REPARACION = "CANCELAR_REPARACION"

    # Phase 8 Events (v4.0 Union-level tracking)
    UNION_ARM_REGISTRADA = "UNION_ARM_REGISTRADA"       # Union ARM completion
    UNION_SOLD_REGISTRADA = "UNION_SOLD_REGISTRADA"    # Union SOLD completion
    SPOOL_CANCELADO = "SPOOL_CANCELADO"                 # 0 unions selected (user cancels)


class EstadoOcupacion(str, Enum):
    """
    Estados de ocupación de un spool en v3.0.

    DISPONIBLE: Spool está libre, puede ser tomado por un worker
    OCUPADO: Spool está siendo trabajado por un worker
    """
    DISPONIBLE = "DISPONIBLE"
    OCUPADO = "OCUPADO"

    @classmethod
    def from_sheets_value(cls, value: float) -> "ActionStatus":
        """
        Convierte valor numérico de Google Sheets a enum ActionStatus.

        Args:
            value: Valor numérico de Sheets (0, 0.1, o 1.0)

        Returns:
            ActionStatus correspondiente

        Raises:
            ValueError: Si el valor no es 0, 0.1, o 1.0
        """
        if value == 0 or value == 0.0:
            return cls.PENDIENTE
        elif value == 0.1:
            return cls.EN_PROGRESO
        elif value == 1.0 or value == 1:
            return cls.COMPLETADO
        else:
            raise ValueError(
                f"Valor inválido de Sheets: {value}. "
                f"Valores permitidos: 0 (PENDIENTE), 0.1 (EN_PROGRESO), 1.0 (COMPLETADO)"
            )

    def to_sheets_value(self) -> float:
        """
        Convierte enum ActionStatus a valor numérico para Google Sheets.

        Returns:
            float: 0, 0.1, o 1.0 según el estado
        """
        mapping = {
            self.PENDIENTE: 0.0,
            self.EN_PROGRESO: 0.1,
            self.COMPLETADO: 1.0,
        }
        return mapping[self]
