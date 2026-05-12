"""
Parser for Estado_Detalle strings — pure function, no side effects.

Estado_Detalle is written by EstadoDetalleBuilder in the backend and stored
in column 67 of the Operaciones Google Sheet. This module parses those strings
back into structured dicts for the v5.0 single-page frontend.

Known formats (from EstadoDetalleBuilder):
  - "MR(93) trabajando ARM (ARM en progreso, SOLD pendiente)"
  - "MR(93) trabajando SOLD (ARM completado, SOLD en progreso)"
  - "Disponible - ARM completado, SOLD pendiente"
  - "Disponible - ARM completado, SOLD completado, METROLOGIA APROBADO ✓"
  - "RECHAZADO - Pendiente reparación"
  - "PENDIENTE_METROLOGIA"
  - "EN_REPARACION - Ocupado: MR(93)"
  - None or "" → defaults (LIBRE)
"""
import re
from typing import Optional


def parse_estado_detalle(estado: Optional[str]) -> dict:
    """
    Parse Estado_Detalle string into structured dict.

    Guards against None and empty input.

    Args:
        estado: The Estado_Detalle string from Operaciones sheet column 67.
                Can be None (new spool) or empty string.

    Returns:
        dict with keys:
            operacion_actual: "ARM" | "SOLD" | "REPARACION" | None
            estado_trabajo:   "LIBRE" | "EN_PROGRESO" | "PAUSADO" | "COMPLETADO"
                              | "RECHAZADO" | "PENDIENTE_METROLOGIA"
            worker:           str (e.g. "MR(93)") for occupied states, None otherwise
    """
    result = {
        "operacion_actual": None,
        "estado_trabajo": "LIBRE",
        "worker": None,
    }

    if not estado or not estado.strip():
        return result

    estado = estado.strip()

    # Pattern: Occupied — "MR(93) trabajando ARM (...)" or "MR(93) trabajando SOLD (...)"
    m = re.match(r"^(\S+)\s+trabajando\s+(ARM|SOLD)\s+", estado)
    if m:
        result["worker"] = m.group(1)
        result["operacion_actual"] = m.group(2)
        result["estado_trabajo"] = "EN_PROGRESO"
        return result

    # Pattern: REPARACION in progress
    if "EN_REPARACION" in estado:
        result["operacion_actual"] = "REPARACION"
        result["estado_trabajo"] = "EN_PROGRESO"
        return result

    # Pattern: RECHAZADO
    if "RECHAZADO" in estado:
        result["estado_trabajo"] = "RECHAZADO"
        return result

    # Pattern: PENDIENTE_METROLOGIA
    if "PENDIENTE_METROLOGIA" in estado or "REPARACION completado" in estado:
        result["estado_trabajo"] = "PENDIENTE_METROLOGIA"
        return result

    # Pattern: METROLOGIA APROBADO — "... METROLOGIA APROBADO ✓"
    if "METROLOGIA APROBADO" in estado or "APROBADO ✓" in estado:
        result["estado_trabajo"] = "COMPLETADO"
        return result

    # Pattern: Both ARM and SOLD completado
    if "ARM completado" in estado and "SOLD completado" in estado:
        result["estado_trabajo"] = "COMPLETADO"
        return result

    # Pattern: ARM done, SOLD not started
    if "ARM completado" in estado and ("SOLD pendiente" in estado or "SOLD pausado" in estado):
        result["estado_trabajo"] = "PAUSADO"
        result["operacion_actual"] = "ARM"
        return result

    # Pattern: ARM paused
    if "ARM pausado" in estado:
        result["estado_trabajo"] = "PAUSADO"
        result["operacion_actual"] = "ARM"
        return result

    # Default: LIBRE
    return result
