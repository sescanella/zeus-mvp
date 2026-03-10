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
  - "Disponible - ARM completado, SOLD completado, RECHAZADO (Ciclo 2/3) - Pendiente reparacion"
  - "BLOQUEADO - Contactar supervisor"
  - "REPARACION completado - PENDIENTE_METROLOGIA"
  - "EN_REPARACION (Ciclo 1/3) - Ocupado: MR(93)"
  - None or "" → defaults (LIBRE)

Reference:
- Plan: 00-01-PLAN.md (API-01)
- Research: 00-RESEARCH.md Pattern 3
"""
import re
from typing import Optional


def parse_estado_detalle(estado: Optional[str]) -> dict:
    """
    Parse Estado_Detalle string into structured dict.

    Guards against None and empty input. Uses regex patterns to detect the
    state type from the Estado_Detalle string written by EstadoDetalleBuilder.

    Args:
        estado: The Estado_Detalle string from Operaciones sheet column 67.
                Can be None (new spool) or empty string.

    Returns:
        dict with keys:
            operacion_actual: "ARM" | "SOLD" | "REPARACION" | None
            estado_trabajo:   "LIBRE" | "EN_PROGRESO" | "PAUSADO" | "COMPLETADO"
                              | "RECHAZADO" | "BLOQUEADO" | "PENDIENTE_METROLOGIA"
            ciclo_rep:        int (1-3) for RECHAZADO/REPARACION cycles, None otherwise
            worker:           str (e.g. "MR(93)") for occupied states, None otherwise
    """
    result = {
        "operacion_actual": None,
        "estado_trabajo": "LIBRE",
        "ciclo_rep": None,
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

    # Pattern: REPARACION in progress — "EN_REPARACION (Ciclo N/3) - Ocupado: MR(93)"
    m = re.search(r"EN_REPARACION.*?Ciclo\s+(\d+)/3", estado)
    if m:
        result["operacion_actual"] = "REPARACION"
        result["estado_trabajo"] = "EN_PROGRESO"
        result["ciclo_rep"] = int(m.group(1))
        return result

    # Pattern: BLOQUEADO — "BLOQUEADO - Contactar supervisor"
    if "BLOQUEADO" in estado:
        result["estado_trabajo"] = "BLOQUEADO"
        return result

    # Pattern: RECHAZADO with cycle — "RECHAZADO (Ciclo N/3) - ..."
    m = re.search(r"RECHAZADO.*?Ciclo\s+(\d+)/3", estado)
    if m:
        result["estado_trabajo"] = "RECHAZADO"
        result["ciclo_rep"] = int(m.group(1))
        return result
    if "RECHAZADO" in estado:
        result["estado_trabajo"] = "RECHAZADO"
        return result

    # Pattern: PENDIENTE_METROLOGIA — "REPARACION completado - PENDIENTE_METROLOGIA"
    if "PENDIENTE_METROLOGIA" in estado or "REPARACION completado" in estado:
        result["estado_trabajo"] = "PENDIENTE_METROLOGIA"
        return result

    # Pattern: METROLOGIA APROBADO — "... METROLOGIA APROBADO ✓"
    if "METROLOGIA APROBADO" in estado or "APROBADO \u2713" in estado:
        result["estado_trabajo"] = "COMPLETADO"
        return result

    # Pattern: Both ARM and SOLD completado — "... ARM completado, SOLD completado"
    if "ARM completado" in estado and "SOLD completado" in estado:
        result["estado_trabajo"] = "COMPLETADO"
        return result

    # Pattern: ARM done, SOLD not started — "ARM completado, SOLD pendiente"
    if "ARM completado" in estado and ("SOLD pendiente" in estado or "SOLD pausado" in estado):
        result["estado_trabajo"] = "PAUSADO"
        result["operacion_actual"] = "ARM"
        return result

    # Pattern: ARM paused
    if "ARM pausado" in estado:
        result["estado_trabajo"] = "PAUSADO"
        result["operacion_actual"] = "ARM"
        return result

    # Default: LIBRE (unknown format or unrecognized string)
    return result
