// Version detection utilities for v3.0 vs v4.0 spools

interface SpoolMetrics {
  total_uniones: number;
  [key: string]: unknown;
}

/**
 * Detects if a spool is v4.0 based on union count
 * v4.0 spools have total_uniones > 0
 * v3.0 spools have total_uniones = 0 or undefined
 */
export function isV4Spool(metrics: SpoolMetrics | null | undefined): boolean {
  if (!metrics) return false;
  return metrics.total_uniones > 0;
}

/**
 * Returns version string for display
 */
export function detectSpoolVersion(metrics: SpoolMetrics | null | undefined): 'v3.0' | 'v4.0' {
  return isV4Spool(metrics) ? 'v4.0' : 'v3.0';
}

/**
 * Cache key for session storage
 */
export function getVersionCacheKey(tagSpool: string): string {
  return `spool_version_${tagSpool}`;
}

/**
 * Cache version in session storage
 * SSR-safe: only runs in browser
 */
export function cacheSpoolVersion(tagSpool: string, version: 'v3.0' | 'v4.0'): void {
  if (typeof window !== 'undefined' && window.sessionStorage) {
    window.sessionStorage.setItem(getVersionCacheKey(tagSpool), version);
  }
}

/**
 * Get cached version from session storage
 * SSR-safe: returns null if not in browser
 */
export function getCachedVersion(tagSpool: string): 'v3.0' | 'v4.0' | null {
  if (typeof window !== 'undefined' && window.sessionStorage) {
    const cached = window.sessionStorage.getItem(getVersionCacheKey(tagSpool));
    if (cached === 'v3.0' || cached === 'v4.0') {
      return cached;
    }
  }
  return null;
}

/**
 * Clear cached version (useful when spool data changes)
 */
export function clearCachedVersion(tagSpool: string): void {
  if (typeof window !== 'undefined' && window.sessionStorage) {
    window.sessionStorage.removeItem(getVersionCacheKey(tagSpool));
  }
}

/**
 * Clear all cached versions
 */
export function clearAllCachedVersions(): void {
  if (typeof window !== 'undefined' && window.sessionStorage) {
    const keys = Object.keys(window.sessionStorage);
    keys.forEach(key => {
      if (key.startsWith('spool_version_')) {
        window.sessionStorage.removeItem(key);
      }
    });
  }
}
