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
 * T-110: also returns 'SOLD' for the post-ARM intermediate state
 * (estado_trabajo='LIBRE', fecha_armado set, fecha_soldadura still null,
 * not occupied) — the only valid next operation is SOLD, so the
 * OperationModal would just ask a question with one possible answer.
 *
 * MET is intentionally NOT returned here because the MET path is not
 * routed through handleSelectOperation in page.tsx (it uses onSelectMet
 * which pushes the MetrologiaModal directly). MET skipping is handled
 * by isMetReady() and a dedicated branch in handleCardClick.
 *
 * Returns null when the operation cannot be determined (e.g., truly empty
 * LIBRE spool with no work yet), meaning the OperationModal should be shown.
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

  // T-110 hotspot H2: ARM finished, SOLD pending. The backend leaves the
  // spool LIBRE (not occupied) with fecha_armado set and fecha_soldadura
  // null — the only valid next move is INICIAR SOLD. Skip OperationModal.
  if (
    spool.estado_trabajo === 'LIBRE' &&
    !spool.ocupado_por &&
    spool.fecha_armado !== null &&
    spool.fecha_soldadura === null
  ) {
    return 'SOLD';
  }

  return null;
}

/**
 * T-110 hotspot H2: ARM + SOLD complete, metrología pending. Backend
 * returns estado_trabajo='PENDIENTE_METROLOGIA' (see _derive_estado in
 * backend/models/spool_status.py). The only valid next action is to
 * inspect — open MetrologiaModal directly, skip OperationModal.
 *
 * Kept separate from deriveOperation because the MET flow does not
 * route through handleSelectOperation in page.tsx — it pushes
 * 'metrologia' onto the modal stack directly.
 */
export function isMetReady(spool: SpoolCardData): boolean {
  return spool.estado_trabajo === 'PENDIENTE_METROLOGIA';
}
