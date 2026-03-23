/**
 * Unit tests for zeues-frontend/lib/local-storage.ts
 *
 * Uses jsdom environment (provided by jest-environment-jsdom).
 * localStorage is mocked by jsdom automatically.
 */

import {
  loadTags,
  saveTags,
  loadPersistedSpools,
  savePersistedSpools,
  STORAGE_KEY,
} from '../../lib/local-storage';
import type { PersistedSpool } from '../../lib/local-storage';

describe('local-storage — STORAGE_KEY', () => {
  it('should use versioned key zeues_v5_spool_tags', () => {
    expect(STORAGE_KEY).toBe('zeues_v5_spool_tags');
  });
});

// ─── loadPersistedSpools ───────────────────────────────────────────────────────

describe('loadPersistedSpools', () => {
  beforeEach(() => {
    localStorage.clear();
  });

  it('returns [] when localStorage is empty', () => {
    expect(loadPersistedSpools()).toEqual([]);
  });

  it('returns [] when localStorage has malformed JSON', () => {
    localStorage.setItem(STORAGE_KEY, '{not valid json');
    expect(loadPersistedSpools()).toEqual([]);
  });

  it('returns [] when localStorage has non-array JSON (string)', () => {
    localStorage.setItem(STORAGE_KEY, JSON.stringify('just-a-string'));
    expect(loadPersistedSpools()).toEqual([]);
  });

  it('returns [] when localStorage has non-array JSON (object)', () => {
    localStorage.setItem(STORAGE_KEY, JSON.stringify({ tag: 'MK-123' }));
    expect(loadPersistedSpools()).toEqual([]);
  });

  it('parses new format {tag, priority} correctly', () => {
    const spools: PersistedSpool[] = [
      { tag: 'MK-123', priority: 1 },
      { tag: 'OT-456', priority: null },
    ];
    localStorage.setItem(STORAGE_KEY, JSON.stringify(spools));
    expect(loadPersistedSpools()).toEqual(spools);
  });

  it('migrates old format (plain string[]) to PersistedSpool[] with null priority', () => {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(['MK-123', 'OT-456']));
    expect(loadPersistedSpools()).toEqual([
      { tag: 'MK-123', priority: null },
      { tag: 'OT-456', priority: null },
    ]);
  });

  it('filters out invalid elements (null, numbers, objects without tag)', () => {
    localStorage.setItem(
      STORAGE_KEY,
      JSON.stringify(['MK-123', 42, null, { noTag: 'bad' }, { tag: 'OT-456', priority: 2 }])
    );
    expect(loadPersistedSpools()).toEqual([
      { tag: 'MK-123', priority: null },
      { tag: 'OT-456', priority: 2 },
    ]);
  });

  it('treats non-number priority as null', () => {
    localStorage.setItem(
      STORAGE_KEY,
      JSON.stringify([{ tag: 'MK-123', priority: 'high' }])
    );
    expect(loadPersistedSpools()).toEqual([{ tag: 'MK-123', priority: null }]);
  });
});

// ─── loadTags ─────────────────────────────────────────────────────────────────

describe('loadTags', () => {
  beforeEach(() => {
    localStorage.clear();
  });

  it('returns [] when localStorage is empty', () => {
    expect(loadTags()).toEqual([]);
  });

  it('returns string[] from new PersistedSpool[] format', () => {
    const spools: PersistedSpool[] = [
      { tag: 'MK-123', priority: 1 },
      { tag: 'OT-456', priority: null },
    ];
    localStorage.setItem(STORAGE_KEY, JSON.stringify(spools));
    expect(loadTags()).toEqual(['MK-123', 'OT-456']);
  });

  it('returns string[] migrated from old plain string[] format', () => {
    const tags = ['MK-123', 'OT-456', 'SP-789'];
    localStorage.setItem(STORAGE_KEY, JSON.stringify(tags));
    expect(loadTags()).toEqual(tags);
  });
});

// ─── savePersistedSpools ──────────────────────────────────────────────────────

describe('savePersistedSpools', () => {
  beforeEach(() => {
    localStorage.clear();
  });

  it('writes PersistedSpool[] as JSON under STORAGE_KEY', () => {
    const spools: PersistedSpool[] = [
      { tag: 'MK-123', priority: 1 },
      { tag: 'OT-456', priority: null },
    ];
    savePersistedSpools(spools);
    expect(JSON.parse(localStorage.getItem(STORAGE_KEY) as string)).toEqual(spools);
  });

  it('overwrites existing value', () => {
    localStorage.setItem(STORAGE_KEY, JSON.stringify([{ tag: 'OLD-001', priority: null }]));
    const newSpools: PersistedSpool[] = [{ tag: 'NEW-001', priority: 2 }];
    savePersistedSpools(newSpools);
    expect(JSON.parse(localStorage.getItem(STORAGE_KEY) as string)).toEqual(newSpools);
  });
});

// ─── saveTags (legacy) ────────────────────────────────────────────────────────

describe('saveTags (legacy)', () => {
  beforeEach(() => {
    localStorage.clear();
  });

  it('writes tags as PersistedSpool[] with null priorities under STORAGE_KEY', () => {
    const tags = ['MK-123', 'OT-456'];
    saveTags(tags);
    expect(JSON.parse(localStorage.getItem(STORAGE_KEY) as string)).toEqual([
      { tag: 'MK-123', priority: null },
      { tag: 'OT-456', priority: null },
    ]);
  });

  it('overwrites existing value', () => {
    localStorage.setItem(STORAGE_KEY, JSON.stringify([{ tag: 'OLD-001', priority: 1 }]));
    saveTags(['NEW-001', 'NEW-002']);
    expect(JSON.parse(localStorage.getItem(STORAGE_KEY) as string)).toEqual([
      { tag: 'NEW-001', priority: null },
      { tag: 'NEW-002', priority: null },
    ]);
  });
});

// ─── SSR safety ───────────────────────────────────────────────────────────────

describe('SSR safety — typeof window guard', () => {
  it('loadPersistedSpools does not throw (SSR guard present)', () => {
    expect(() => loadPersistedSpools()).not.toThrow();
  });

  it('loadTags does not throw (SSR guard present)', () => {
    expect(() => loadTags()).not.toThrow();
  });

  it('savePersistedSpools does not throw (SSR guard present)', () => {
    expect(() => savePersistedSpools([{ tag: 'MK-123', priority: null }])).not.toThrow();
  });

  it('saveTags does not throw (SSR guard present)', () => {
    expect(() => saveTags(['MK-123'])).not.toThrow();
  });
});
