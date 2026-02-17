/**
 * Pure utility functions for spool selection page.
 * Extracted from seleccionar-spool/page.tsx for testability and reuse.
 */

import { OPERATION_WORKFLOWS, type OperationType } from './operation-config';

/** Maximum spools selectable in a single batch (backend constraint) */
export const MAX_BATCH_SELECTION = 50;

type TipoParam = 'tomar' | 'pausar' | 'completar' | 'cancelar' | 'metrologia' | 'reparacion' | 'no-conformidad' | null;
type Accion = 'INICIAR' | 'FINALIZAR' | null;
type Operation = OperationType;

/**
 * Maps operation code to human-readable label.
 * Delegates to OPERATION_WORKFLOWS (single source of truth).
 */
export function getOperationLabel(operation: Operation): string {
  return OPERATION_WORKFLOWS[operation].label;
}

/**
 * Maps tipo parameter to action label for display.
 */
export function getActionLabel(tipo: TipoParam): string {
  switch (tipo) {
    case 'tomar': return 'TOMAR';
    case 'pausar': return 'PAUSAR';
    case 'completar': return 'COMPLETAR';
    case 'cancelar': return 'CANCELAR';
    case 'metrologia': return 'INSPECCIONAR';
    case 'reparacion': return 'REPARAR';
    case 'no-conformidad': return 'NO CONFORMIDAD';
    default: return 'SELECCIONAR';
  }
}

interface PageTitleParams {
  accion: Accion;
  tipo: TipoParam;
  operationLabel: string;
  selectedOperation: Operation;
}

/**
 * Generates the page title for the spool selection screen.
 * Handles both v4.0 (accion-based) and v3.0 (tipo-based) workflows.
 */
export function getPageTitle({ accion, tipo, operationLabel, selectedOperation }: PageTitleParams): string {
  // v4.0: Check accion first (INICIAR/FINALIZAR)
  if (accion === 'INICIAR') {
    return `SELECCIONAR SPOOL PARA INICIAR - ${operationLabel}`;
  }
  if (accion === 'FINALIZAR') {
    return `SELECCIONAR SPOOL PARA FINALIZAR - ${operationLabel}`;
  }

  // v3.0: Fall back to tipo-based titles
  switch (tipo) {
    case 'tomar':
      return `SELECCIONAR SPOOL PARA TOMAR - ${operationLabel}`;
    case 'pausar':
      return `SELECCIONAR SPOOL PARA PAUSAR - ${operationLabel}`;
    case 'completar':
      return `SELECCIONAR SPOOL PARA COMPLETAR - ${operationLabel}`;
    case 'cancelar':
      return selectedOperation === 'REPARACION'
        ? 'SELECCIONAR REPARACION PARA CANCELAR'
        : `SELECCIONAR SPOOL PARA CANCELAR - ${operationLabel}`;
    case 'metrologia':
      return 'SELECCIONAR SPOOL PARA INSPECCION';
    case 'no-conformidad':
      return 'SELECCIONAR SPOOL - NO CONFORMIDAD';
    case 'reparacion':
      return 'SELECCIONAR SPOOL PARA REPARAR';
    default:
      return `${operationLabel} - ${getActionLabel(tipo)}`;
  }
}

interface EmptyMessageParams {
  accion: Accion;
  tipo: TipoParam;
  operationLabel: string;
  selectedOperation: Operation;
}

/**
 * Generates the empty-state message when no spools match the criteria.
 * Handles both v4.0 (accion-based) and v3.0 (tipo-based) workflows.
 */
export function getEmptyMessage({ accion, tipo, operationLabel, selectedOperation }: EmptyMessageParams): string {
  // v4.0: Check accion first (INICIAR/FINALIZAR)
  if (accion === 'INICIAR') {
    return `No hay spools disponibles para iniciar en ${operationLabel}`;
  }
  if (accion === 'FINALIZAR') {
    return `No tienes spools ocupados actualmente para ${operationLabel}`;
  }

  // v3.0: Fall back to tipo-based messages
  switch (tipo) {
    case 'tomar':
      return `No hay spools disponibles para ${operationLabel}`;
    case 'pausar':
      return 'No tienes spools en progreso para pausar';
    case 'completar':
      return 'No tienes spools en progreso para completar';
    case 'cancelar':
      return selectedOperation === 'REPARACION'
        ? 'No tienes reparaciones en progreso para cancelar'
        : 'No tienes spools en progreso para cancelar';
    case 'metrologia':
      return 'No hay spools disponibles para inspeccion de metrologia';
    case 'no-conformidad':
      return 'No hay spools disponibles para registrar no conformidad';
    case 'reparacion':
      return 'No hay spools rechazados disponibles para reparacion';
    default:
      return 'No hay spools disponibles';
  }
}
