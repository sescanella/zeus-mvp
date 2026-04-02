import type { EstadoTrabajo } from '@/lib/types';

/**
 * Human-readable labels for EstadoTrabajo values.
 * Single source of truth — used by SpoolCard badges and page filter chips.
 * "Pend. Metrología" is the canonical long form.
 */
export const ESTADO_LABELS: Record<EstadoTrabajo, string> = {
  LIBRE: 'Libre',
  EN_PROGRESO: 'En Progreso',
  PAUSADO: 'Pausado',
  COMPLETADO: 'Completado',
  RECHAZADO: 'Rechazado',
  PENDIENTE_METROLOGIA: 'Pend. Metrología',
  BLOQUEADO: 'Bloqueado',
};

/**
 * Tailwind classes for the estado badge inside SpoolCard.
 * Text + border only (no background fill) — sits on the dark card surface.
 */
export const ESTADO_COLORS: Record<EstadoTrabajo, string> = {
  LIBRE: 'text-white border-white/50',
  EN_PROGRESO: 'text-zeues-orange border-zeues-orange',
  PAUSADO: 'text-yellow-400 border-yellow-400',
  COMPLETADO: 'text-green-400 border-green-400',
  RECHAZADO: 'text-red-400 border-red-400',
  PENDIENTE_METROLOGIA: 'text-blue-300 border-blue-400',
  BLOQUEADO: 'text-red-500 border-red-500 bg-red-600/20',
};

/**
 * Tailwind classes for the filter chip buttons on the home page.
 * Includes border, text colour, and a light background fill for the active state.
 */
export const ESTADO_CHIP_COLORS: Record<EstadoTrabajo, string> = {
  LIBRE: 'border-white text-white bg-white/10',
  EN_PROGRESO: 'border-zeues-orange text-zeues-orange bg-zeues-orange/10',
  PAUSADO: 'border-yellow-400 text-yellow-400 bg-yellow-400/10',
  COMPLETADO: 'border-green-400 text-green-400 bg-green-400/10',
  RECHAZADO: 'border-red-400 text-red-400 bg-red-400/10',
  PENDIENTE_METROLOGIA: 'border-blue-300 text-blue-300 bg-blue-300/10',
  BLOQUEADO: 'border-red-500 text-red-500 bg-red-500/10',
};

/**
 * Ordered list of all EstadoTrabajo values for iteration (e.g., filter chips).
 */
export const ALL_ESTADOS: EstadoTrabajo[] = [
  'LIBRE',
  'EN_PROGRESO',
  'PAUSADO',
  'COMPLETADO',
  'RECHAZADO',
  'PENDIENTE_METROLOGIA',
  'BLOQUEADO',
];
