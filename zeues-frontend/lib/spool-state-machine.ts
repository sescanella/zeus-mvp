/**
 * spool-state-machine — pure functions for spool action availability
 *
 * Determines which actions (INICIAR, FINALIZAR, PAUSAR, CANCELAR) are valid
 * for a given spool based on its current state.
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

/** All operations — always shown regardless of spool state */
export const ALL_OPERATIONS: Operation[] = ['ARM', 'SOLD', 'MET', 'REP'];

/** Available action types for a spool */
export type Action = 'INICIAR' | 'FINALIZAR' | 'PAUSAR';

/**
 * Returns the list of valid actions for a spool based on its occupation status.
 *
 * Actions are determined ONLY by ocupado_por — not by estado_trabajo:
 *   - Occupied (non-null, non-empty ocupado_por): FINALIZAR, PAUSAR
 *   - Free (null or empty ocupado_por): INICIAR
 *
 * CANCELAR removed — "Quitar" on SpoolCard handles spool removal + backend release.
 *
 * @param spool - SpoolCardData with ocupado_por
 * @returns Array of valid Action types
 */
export function getValidActions(spool: SpoolCardData): Action[] {
  if (spool.ocupado_por !== null && spool.ocupado_por !== '') {
    return ['FINALIZAR', 'PAUSAR'];
  }
  return ['INICIAR'];
}

/**
 * Derives the operation from the spool's current state.
 *
 * When a spool has an active operacion_actual (ARM, SOLD, REPARACION),
 * the operation is already known — no need to ask the user.
 *
 * Returns null when the operation cannot be determined (e.g., LIBRE spool
 * with no active operation), meaning the OperationModal should be shown.
 *
 * Maps backend OperacionActual → frontend Operation:
 *   ARM → ARM, SOLD → SOLD, REPARACION → REP
 */
const OPERACION_TO_OPERATION: Record<string, Operation> = {
  ARM: 'ARM',
  SOLD: 'SOLD',
  REPARACION: 'REP',
};

export function deriveOperation(spool: SpoolCardData): Operation | null {
  if (spool.operacion_actual) {
    return OPERACION_TO_OPERATION[spool.operacion_actual] ?? null;
  }
  return null;
}
