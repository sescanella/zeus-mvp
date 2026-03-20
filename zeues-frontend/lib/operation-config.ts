/**
 * Centralized configuration for operation workflows.
 *
 * Defines role mappings and display titles for each operation type.
 */

export type OperationType = 'ARM' | 'SOLD' | 'METROLOGIA' | 'REPARACION';

export const OPERATION_TO_ROLES: Record<OperationType, string[]> = {
  ARM: ['Armador', 'Ayudante'],
  SOLD: ['Soldador', 'Ayudante'],
  METROLOGIA: ['Metrologia'],
  REPARACION: ['Armador', 'Soldador'],
} as const;

export const OPERATION_TITLES: Record<OperationType, string> = {
  ARM: '¿Quién va a armar?',
  SOLD: '¿Quién va a soldar?',
  METROLOGIA: '¿Quién va a medir?',
  REPARACION: '¿Quién va a reparar?',
} as const;
