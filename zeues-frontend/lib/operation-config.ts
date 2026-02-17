/**
 * Centralized configuration for operation workflows.
 *
 * This file defines the navigation flow and available actions for each operation.
 * Adding a new operation only requires updating this configuration file.
 */

import { Puzzle, Flame, SearchCheck, Wrench, type LucideIcon } from 'lucide-react';

export type OperationType = 'ARM' | 'SOLD' | 'METROLOGIA' | 'REPARACION';

export type ActionType =
  | 'tomar'            // v3.0: Take ownership of spool
  | 'pausar'           // v3.0: Pause work (release ownership temporarily)
  | 'completar'        // v3.0: Complete work (mark as finished)
  | 'cancelar'         // v3.0: Cancel repair (transition to BLOQUEADO state)
  | 'metrologia'       // Special: Instant metrología inspection
  | 'no-conformidad';  // Forms: No Conformidad (REG-QAC-002)

export interface OperationWorkflow {
  /**
   * Whether this operation skips the P3 (tipo-interaccion) page.
   *
   * - true: Navigate directly from P2 (worker selection) to P4 (spool selection)
   * - false: Standard flow through P3 (action type selection)
   */
  skipP3: boolean;

  /**
   * Available actions for this operation.
   *
   * If skipP3 is true, only the first action is used (direct navigation).
   * If skipP3 is false, all actions are shown as buttons in P3.
   */
  actions: readonly ActionType[];

  /**
   * Human-readable label for display in UI.
   */
  label: string;

  /**
   * Brief description of when to use this operation.
   */
  description: string;
}

/**
 * Operation workflow configuration.
 *
 * This is the single source of truth for operation behavior.
 */
export const OPERATION_WORKFLOWS: Record<OperationType, OperationWorkflow> = {
  'ARM': {
    skipP3: false,
    actions: ['tomar', 'pausar', 'completar'],
    label: 'ARMADO',
    description: 'Assembly workflow with multi-step actions',
  },
  'SOLD': {
    skipP3: false,
    actions: ['tomar', 'pausar', 'completar'],
    label: 'SOLDADURA',
    description: 'Welding workflow with multi-step actions',
  },
  'METROLOGIA': {
    skipP3: false,
    actions: ['metrologia', 'no-conformidad'],
    label: 'METROLOGÍA',
    description: 'Quality inspection (APROBADO/RECHAZADO) and non-conformity forms',
  },
  'REPARACION': {
    skipP3: false,
    actions: ['tomar', 'pausar', 'completar', 'cancelar'],
    label: 'REPARACIÓN',
    description: 'Repair workflow with CANCELAR option (after 3 failed attempts → BLOQUEADO)',
  },
} as const;

/**
 * Operation icon mapping for consistent UI representation.
 * Used across P1-P6 flow for visual operation identification.
 *
 * Centralized to avoid duplication across multiple pages.
 */
export const OPERATION_ICONS: Record<OperationType, LucideIcon> = {
  ARM: Puzzle,
  SOLD: Flame,
  METROLOGIA: SearchCheck,
  REPARACION: Wrench,
} as const;
