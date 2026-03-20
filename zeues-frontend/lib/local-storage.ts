/**
 * localStorage persistence utility for v5.0 spool tag tracking.
 *
 * All functions use typeof window guard for Next.js SSR compatibility.
 * No `any` types used — parsed JSON stored as `unknown`.
 */

export const STORAGE_KEY = 'zeues_v5_spool_tags';

/**
 * Loads persisted spool tags from localStorage.
 *
 * Returns [] on:
 * - SSR environment (window undefined)
 * - Empty localStorage
 * - Malformed JSON
 * - Non-array JSON value
 *
 * Filters out non-string elements from stored array.
 *
 * @returns string[] of spool tags (may be empty)
 */
export function loadTags(): string[] {
  if (typeof window === 'undefined') return [];

  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (raw === null) return [];

    const parsed: unknown = JSON.parse(raw);
    if (!Array.isArray(parsed)) return [];

    return parsed.filter((item): item is string => typeof item === 'string');
  } catch {
    return [];
  }
}

/**
 * Saves spool tags array to localStorage.
 *
 * No-op when running on server (SSR safe).
 *
 * @param tags - Array of TAG_SPOOL strings to persist
 */
export function saveTags(tags: string[]): void {
  if (typeof window === 'undefined') return;
  localStorage.setItem(STORAGE_KEY, JSON.stringify(tags));
}
