/**
 * parseEstadoDetalle — TypeScript mirror of backend estado_detalle_parser.py
 *
 * Parses Estado_Detalle strings written by EstadoDetalleBuilder (stored in
 * Operaciones sheet column 67) into structured objects for the v5.0 frontend.
 *
 * The 11-step pattern match order MUST be identical to the Python version.
 * Changing the order breaks state detection (e.g., RECHAZADO bare matches
 * before RECHAZADO with cycle).
 *
 * Reference: backend/services/estado_detalle_parser.py
 * Plan: 01-02-PLAN.md
 */

// TODO: Once Plan 01-01 adds these to lib/types.ts, replace with:
// import type { EstadoTrabajo, OperacionActual } from './types';
type EstadoTrabajo =
  | 'LIBRE'
  | 'EN_PROGRESO'
  | 'PAUSADO'
  | 'COMPLETADO'
  | 'RECHAZADO'
  | 'BLOQUEADO'
  | 'PENDIENTE_METROLOGIA';

type OperacionActual = 'ARM' | 'SOLD' | 'REPARACION' | null;

/**
 * Parsed result of an Estado_Detalle string.
 * Field names and types match the Python dict returned by parse_estado_detalle().
 */
export interface ParsedEstadoDetalle {
  /** Current operation in progress, or null if none */
  operacion_actual: OperacionActual;
  /** Current work state of the spool */
  estado_trabajo: EstadoTrabajo;
  /** Repair cycle number (1-3) for RECHAZADO/REPARACION states, null otherwise */
  ciclo_rep: number | null;
  /** Worker identifier (e.g. "MR(93)") for occupied states, null otherwise */
  worker: string | null;
}

const DEFAULT_RESULT: ParsedEstadoDetalle = {
  operacion_actual: null,
  estado_trabajo: 'LIBRE',
  ciclo_rep: null,
  worker: null,
};

/**
 * Parse an Estado_Detalle string into a structured object.
 *
 * Guards against null, undefined, and empty input — all return LIBRE defaults.
 * Uses regex patterns mirroring the Python re module (JavaScript RegExp syntax).
 *
 * The 11-step match order is intentional and MUST NOT be reordered.
 *
 * @param estado - The Estado_Detalle string from Operaciones sheet col 67
 * @returns ParsedEstadoDetalle with operacion_actual, estado_trabajo, ciclo_rep, worker
 */
export function parseEstadoDetalle(estado: string | null | undefined): ParsedEstadoDetalle {
  // Guard: null, undefined, empty, whitespace-only -> LIBRE defaults
  if (!estado || !estado.trim()) {
    return { ...DEFAULT_RESULT };
  }

  const s = estado.trim();

  // ─── Pattern 1: Occupied working ARM or SOLD ───────────────────────────────
  // "MR(93) trabajando ARM (ARM en progreso, SOLD pendiente)"
  // "MR(93) trabajando SOLD (ARM completado, SOLD en progreso)"
  const occupiedMatch = s.match(/^(\S+)\s+trabajando\s+(ARM|SOLD)\s+/);
  if (occupiedMatch) {
    return {
      ...DEFAULT_RESULT,
      worker: occupiedMatch[1],
      operacion_actual: occupiedMatch[2] as 'ARM' | 'SOLD',
      estado_trabajo: 'EN_PROGRESO',
    };
  }

  // ─── Pattern 2: REPARACION in progress ────────────────────────────────────
  // "EN_REPARACION (Ciclo 1/3) - Ocupado: MR(93)"
  const reparacionMatch = s.match(/EN_REPARACION.*?Ciclo\s+(\d+)\/3/);
  if (reparacionMatch) {
    return {
      ...DEFAULT_RESULT,
      operacion_actual: 'REPARACION',
      estado_trabajo: 'EN_PROGRESO',
      ciclo_rep: parseInt(reparacionMatch[1], 10),
    };
  }

  // ─── Pattern 3: BLOQUEADO ──────────────────────────────────────────────────
  // "BLOQUEADO - Contactar supervisor"
  if (s.includes('BLOQUEADO')) {
    return { ...DEFAULT_RESULT, estado_trabajo: 'BLOQUEADO' };
  }

  // ─── Pattern 4: RECHAZADO with cycle ──────────────────────────────────────
  // "Disponible - ARM completado, SOLD completado, RECHAZADO (Ciclo 2/3) - Pendiente reparacion"
  const rechazadoCicloMatch = s.match(/RECHAZADO.*?Ciclo\s+(\d+)\/3/);
  if (rechazadoCicloMatch) {
    return {
      ...DEFAULT_RESULT,
      estado_trabajo: 'RECHAZADO',
      ciclo_rep: parseInt(rechazadoCicloMatch[1], 10),
    };
  }

  // ─── Pattern 5: RECHAZADO bare ────────────────────────────────────────────
  if (s.includes('RECHAZADO')) {
    return { ...DEFAULT_RESULT, estado_trabajo: 'RECHAZADO' };
  }

  // ─── Pattern 6: PENDIENTE_METROLOGIA ──────────────────────────────────────
  // "REPARACION completado - PENDIENTE_METROLOGIA"
  if (s.includes('PENDIENTE_METROLOGIA') || s.includes('REPARACION completado')) {
    return { ...DEFAULT_RESULT, estado_trabajo: 'PENDIENTE_METROLOGIA' };
  }

  // ─── Pattern 7: METROLOGIA APROBADO ───────────────────────────────────────
  // "Disponible - ARM completado, SOLD completado, METROLOGIA APROBADO ✓"
  if (s.includes('METROLOGIA APROBADO') || s.includes('APROBADO \u2713')) {
    return { ...DEFAULT_RESULT, estado_trabajo: 'COMPLETADO' };
  }

  // ─── Pattern 8: Both ARM and SOLD completado ──────────────────────────────
  // "Disponible - ARM completado, SOLD completado"
  if (s.includes('ARM completado') && s.includes('SOLD completado')) {
    return { ...DEFAULT_RESULT, estado_trabajo: 'COMPLETADO' };
  }

  // ─── Pattern 9: ARM done, SOLD pending or paused ──────────────────────────
  // "Disponible - ARM completado, SOLD pendiente"
  // "Disponible - ARM completado, SOLD pausado"
  if (s.includes('ARM completado') && (s.includes('SOLD pendiente') || s.includes('SOLD pausado'))) {
    return {
      ...DEFAULT_RESULT,
      estado_trabajo: 'PAUSADO',
      operacion_actual: 'ARM',
    };
  }

  // ─── Pattern 10: ARM pausado ───────────────────────────────────────────────
  if (s.includes('ARM pausado')) {
    return {
      ...DEFAULT_RESULT,
      estado_trabajo: 'PAUSADO',
      operacion_actual: 'ARM',
    };
  }

  // ─── Pattern 11: Default fallback -> LIBRE ────────────────────────────────
  return { ...DEFAULT_RESULT };
}
