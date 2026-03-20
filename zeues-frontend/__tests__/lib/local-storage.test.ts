/**
 * Unit tests for zeues-frontend/lib/local-storage.ts
 *
 * Uses jsdom environment (provided by jest-environment-jsdom).
 * localStorage is mocked by jsdom automatically.
 */

import {
  loadTags,
  saveTags,
  STORAGE_KEY,
} from '../../lib/local-storage';

describe('local-storage — STORAGE_KEY', () => {
  it('should use versioned key zeues_v5_spool_tags', () => {
    expect(STORAGE_KEY).toBe('zeues_v5_spool_tags');
  });
});

describe('loadTags', () => {
  beforeEach(() => {
    localStorage.clear();
  });

  it('returns [] when localStorage is empty', () => {
    expect(loadTags()).toEqual([]);
  });

  it('returns [] when localStorage has malformed JSON', () => {
    localStorage.setItem(STORAGE_KEY, '{not valid json');
    expect(loadTags()).toEqual([]);
  });

  it('returns [] when localStorage has non-array JSON (string)', () => {
    localStorage.setItem(STORAGE_KEY, JSON.stringify('just-a-string'));
    expect(loadTags()).toEqual([]);
  });

  it('returns [] when localStorage has non-array JSON (object)', () => {
    localStorage.setItem(STORAGE_KEY, JSON.stringify({ tag: 'MK-123' }));
    expect(loadTags()).toEqual([]);
  });

  it('returns string[] when localStorage has valid JSON array of strings', () => {
    const tags = ['MK-123', 'OT-456', 'SP-789'];
    localStorage.setItem(STORAGE_KEY, JSON.stringify(tags));
    expect(loadTags()).toEqual(tags);
  });

  it('filters out non-string elements from array', () => {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(['MK-123', 42, null, { tag: 'bad' }, 'OT-456']));
    expect(loadTags()).toEqual(['MK-123', 'OT-456']);
  });
});

describe('saveTags', () => {
  beforeEach(() => {
    localStorage.clear();
  });

  it('writes JSON.stringify(tags) under STORAGE_KEY', () => {
    const tags = ['MK-123', 'OT-456'];
    saveTags(tags);
    expect(localStorage.getItem(STORAGE_KEY)).toBe(JSON.stringify(tags));
  });

  it('overwrites existing value', () => {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(['OLD-001']));
    saveTags(['NEW-001', 'NEW-002']);
    expect(JSON.parse(localStorage.getItem(STORAGE_KEY) as string)).toEqual(['NEW-001', 'NEW-002']);
  });
});

describe('SSR safety — typeof window guard', () => {
  it('loadTags does not throw (SSR guard present)', () => {
    expect(() => loadTags()).not.toThrow();
  });

  it('saveTags does not throw (SSR guard present)', () => {
    expect(() => saveTags(['MK-123'])).not.toThrow();
  });
});
