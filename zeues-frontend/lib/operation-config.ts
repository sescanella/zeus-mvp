/**
 * Centralized operation configuration for ZEUES v3.0
 *
 * Single source of truth for operation display names, icons, and metadata.
 * Eliminates duplication across tipo-interaccion, seleccionar-spool, confirmar, etc.
 *
 * @module operation-config
 */

import { Puzzle, Flame, SearchCheck, Wrench, LucideIcon } from 'lucide-react';

/**
 * Operation type union (must match Context.selectedOperation type)
 */
export type Operation = 'ARM' | 'SOLD' | 'METROLOGIA' | 'REPARACION';

/**
 * Operation metadata interface
 */
interface OperationConfig {
  /** Display label in Spanish (uppercase) */
  label: string;
  /** Lucide icon component */
  icon: LucideIcon;
  /** Optional color for theming (future use) */
  color?: string;
}

/**
 * Operation configuration lookup table
 *
 * Usage:
 * ```typescript
 * const { label, icon: Icon } = OPERATION_CONFIG[state.selectedOperation];
 * return <Icon size={48} />;
 * ```
 */
export const OPERATION_CONFIG: Record<Operation, OperationConfig> = {
  ARM: {
    label: 'ARMADO',
    icon: Puzzle,
    color: '#FF6B35' // zeues-orange
  },
  SOLD: {
    label: 'SOLDADURA',
    icon: Flame,
    color: '#FF6B35'
  },
  METROLOGIA: {
    label: 'METROLOGÍA',
    icon: SearchCheck,
    color: '#FF6B35'
  },
  REPARACION: {
    label: 'REPARACIÓN',
    icon: Wrench,
    color: '#FF6B35'
  }
} as const;

/**
 * Type-safe helper to get operation config with validation
 *
 * @param operation - Operation to lookup
 * @returns Operation config object
 * @throws Error if operation is invalid
 */
export function getOperationConfig(operation: Operation | null): OperationConfig {
  if (!operation) {
    throw new Error('Operation is null or undefined');
  }

  const config = OPERATION_CONFIG[operation];

  if (!config) {
    throw new Error(`Invalid operation: ${operation}. Expected one of: ${Object.keys(OPERATION_CONFIG).join(', ')}`);
  }

  return config;
}

/**
 * Get operation label safely (with fallback)
 *
 * @param operation - Operation to lookup
 * @param fallback - Fallback label if operation invalid (default: 'DESCONOCIDO')
 * @returns Operation label
 */
export function getOperationLabel(operation: Operation | null, fallback = 'DESCONOCIDO'): string {
  if (!operation) return fallback;
  return OPERATION_CONFIG[operation]?.label || fallback;
}

/**
 * Get operation icon safely (with fallback to SearchCheck)
 *
 * @param operation - Operation to lookup
 * @returns Lucide icon component
 */
export function getOperationIcon(operation: Operation | null): LucideIcon {
  if (!operation) return SearchCheck;
  return OPERATION_CONFIG[operation]?.icon || SearchCheck;
}

/**
 * Check if an operation is valid
 *
 * @param operation - Operation to validate
 * @returns True if operation exists in config
 */
export function isValidOperation(operation: unknown): operation is Operation {
  return typeof operation === 'string' && operation in OPERATION_CONFIG;
}
