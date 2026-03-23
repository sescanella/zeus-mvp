/**
 * localStorage persistence for v5.0 spool tag tracking + priority.
 * All functions use typeof window guard for Next.js SSR compatibility.
 */

export const STORAGE_KEY = 'zeues_v5_spool_tags';

export interface PersistedSpool {
  tag: string;
  priority: number | null; // 1=urgente, 2=alta, 3=normal, null=sin prioridad
}

/**
 * Loads persisted spools from localStorage.
 * Backward compatible: migrates old string[] format to PersistedSpool[].
 */
export function loadPersistedSpools(): PersistedSpool[] {
  if (typeof window === 'undefined') return [];

  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (raw === null) return [];

    const parsed: unknown = JSON.parse(raw);
    if (!Array.isArray(parsed)) return [];

    return parsed.map((item: unknown): PersistedSpool | null => {
      // New format: {tag, priority}
      if (typeof item === 'object' && item !== null && 'tag' in item) {
        const obj = item as Record<string, unknown>;
        if (typeof obj.tag === 'string') {
          const p = typeof obj.priority === 'number' ? obj.priority : null;
          return { tag: obj.tag, priority: p };
        }
      }
      // Old format: plain string
      if (typeof item === 'string') {
        return { tag: item, priority: null };
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
 * Saves spools with priorities to localStorage.
 */
export function savePersistedSpools(spools: PersistedSpool[]): void {
  if (typeof window === 'undefined') return;
  localStorage.setItem(STORAGE_KEY, JSON.stringify(spools));
}

/**
 * Legacy: saves just tags (priorities set to null).
 * @deprecated Use savePersistedSpools instead.
 */
export function saveTags(tags: string[]): void {
  savePersistedSpools(tags.map((tag) => ({ tag, priority: null })));
}
