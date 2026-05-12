/**
 * localStorage persistence for v5.0 spool tag tracking.
 * Tolerates legacy JSON entries with extra fields (e.g. `priority`) by
 * ignoring them on read.
 * All functions use typeof window guard for Next.js SSR compatibility.
 */

export const STORAGE_KEY = 'zeues_v5_spool_tags';

export interface PersistedSpool {
  tag: string;
}

/**
 * Loads persisted spools from localStorage.
 * Backward compatible: tolerates the old `string[]` format and the
 * intermediate `{tag, priority}[]` format (`priority` is silently discarded).
 */
export function loadPersistedSpools(): PersistedSpool[] {
  if (typeof window === 'undefined') return [];

  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (raw === null) return [];

    const parsed: unknown = JSON.parse(raw);
    if (!Array.isArray(parsed)) return [];

    return parsed.map((item: unknown): PersistedSpool | null => {
      // Object format: {tag, ...extras}. Extras are ignored.
      if (typeof item === 'object' && item !== null && 'tag' in item) {
        const obj = item as Record<string, unknown>;
        if (typeof obj.tag === 'string') {
          return { tag: obj.tag };
        }
      }
      // Old format: plain string
      if (typeof item === 'string') {
        return { tag: item };
      }
      return null;
    }).filter((x): x is PersistedSpool => x !== null);
  } catch {
    return [];
  }
}

/**
 * Loads just the tags (for API calls).
 */
export function loadTags(): string[] {
  return loadPersistedSpools().map((s) => s.tag);
}

/**
 * Saves spools to localStorage.
 */
export function savePersistedSpools(spools: PersistedSpool[]): void {
  if (typeof window === 'undefined') return;
  localStorage.setItem(STORAGE_KEY, JSON.stringify(spools));
}

/**
 * Legacy: saves just tags.
 * @deprecated Use savePersistedSpools instead.
 */
export function saveTags(tags: string[]): void {
  savePersistedSpools(tags.map((tag) => ({ tag })));
}
