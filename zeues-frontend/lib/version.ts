// Version detection utilities for v3.0 vs v4.0 spools

/**
 * Minimal interface for spool version detection.
 * Any object with total_uniones field can be used.
 */
export interface SpoolMetrics {
  total_uniones?: number | null;
}

/**
 * Detects if a spool is v4.0 based on union count
 * v4.0 spools have total_uniones > 0
 * v3.0 spools have total_uniones = 0 or undefined
 */
function isV4Spool(metrics: SpoolMetrics | null | undefined): boolean {
  if (!metrics) return false;
  return (metrics.total_uniones ?? 0) > 0;
}

/**
 * Returns version string for display
 *
 * v4.0 spools have union-level tracking (total_uniones > 0)
 * v3.0 spools have spool-level tracking only (total_uniones = 0 or null)
 *
 * @param metrics - Object with optional total_uniones field
 * @returns Version identifier: 'v4.0' or 'v3.0'
 *
 * @example
 * const version = detectSpoolVersion(spool);
 * if (version === 'v4.0') {
 *   // Show union selection UI
 * }
 */
export function detectSpoolVersion(metrics: SpoolMetrics | null | undefined): 'v3.0' | 'v4.0' {
  return isV4Spool(metrics) ? 'v4.0' : 'v3.0';
}

