/**
 * spool-state-machine — pure functions for spool operation and action availability
 *
 * Determines which operations (ARM, SOLD, MET, REP) and actions (INICIAR,
 * FINALIZAR, PAUSAR, CANCELAR) are valid for a given spool based on its
 * current state.
 *
 * These are pure functions with no side effects — safe to call anywhere.
 *
 * Plan: 01-02-PLAN.md Feature 2
 * Updated: 04-01-PLAN.md Task 2 — removed local duplicate types, import from types.ts
 */

import type { SpoolCardData } from './types';

// Re-export SpoolCardData so existing consumers (OperationModal, ActionModal, tests)
// that import from '@/lib/spool-state-machine' continue to work without changes.
export type { SpoolCardData } from './types';

/** Available operation types for a spool */
export type Operation = 'ARM' | 'SOLD' | 'MET' | 'REP';

/** Available action types for a spool */
export type Action = 'INICIAR' | 'FINALIZAR' | 'PAUSAR' | 'CANCELAR';

/**
 * Returns the list of valid operations for a spool based on its current state.
 *
 * The returned operations determine which operation tabs/buttons are shown
 * in the v5.0 single-page UI spool card.
 *
 * ARM disambiguation for PAUSADO state:
 *   - If uniones_arm_completadas >= total_uniones (and both non-null, total > 0):
 *     ARM is fully done → next operation is SOLD
 *   - Otherwise: ARM is partially done → continue ARM
 *
 * @param spool - SpoolCardData with estado_trabajo, operacion_actual, and union counts
 * @returns Array of valid Operation types (may be empty)
 */
export function getValidOperations(spool: SpoolCardData): Operation[] {
  switch (spool.estado_trabajo) {
    case 'LIBRE':
      return ['ARM'];

    case 'EN_PROGRESO':
      switch (spool.operacion_actual) {
        case 'ARM':
          return ['ARM'];
        case 'SOLD':
          return ['SOLD'];
        case 'REPARACION':
          return ['REP'];
        default:
          return [];
      }

    case 'PAUSADO':
      if (spool.operacion_actual === 'ARM') {
        return isArmFullyCompleted(spool) ? ['SOLD'] : ['ARM'];
      }
      return [];

    case 'COMPLETADO':
      return ['MET'];

    case 'PENDIENTE_METROLOGIA':
      return ['MET'];

    case 'RECHAZADO':
      return ['REP'];

    case 'BLOQUEADO':
      return [];

    default:
      // null or unrecognized estado_trabajo
      return [];
  }
}

/**
 * Returns the list of valid actions for a spool based on its occupation status.
 *
 * Actions are determined ONLY by ocupado_por — not by estado_trabajo:
 *   - Occupied (non-null, non-empty ocupado_por): FINALIZAR, PAUSAR, CANCELAR
 *   - Free (null or empty ocupado_por): INICIAR, CANCELAR
 *
 * @param spool - SpoolCardData with ocupado_por
 * @returns Array of valid Action types
 */
export function getValidActions(spool: SpoolCardData): Action[] {
  if (spool.ocupado_por !== null && spool.ocupado_por !== '') {
    return ['FINALIZAR', 'PAUSAR', 'CANCELAR'];
  }
  return ['INICIAR', 'CANCELAR'];
}

// ─── Internal helpers ──────────────────────────────────────────────────────────

/**
 * Determine if ARM is fully completed for PAUSADO + ARM disambiguation.
 *
 * Returns true if:
 *   - Both total_uniones and uniones_arm_completadas are non-null
 *   - total_uniones > 0 (guards against 0/0 edge case)
 *   - uniones_arm_completadas >= total_uniones
 *
 * Returns false (ARM is partial) in all other cases, including when counts
 * are unavailable — fail-safe defaults to continuing ARM.
 */
function isArmFullyCompleted(spool: SpoolCardData): boolean {
  const { total_uniones, uniones_arm_completadas } = spool;
  if (
    total_uniones === null ||
    total_uniones === 0 ||
    uniones_arm_completadas === null
  ) {
    return false;
  }
  return uniones_arm_completadas >= total_uniones;
}
