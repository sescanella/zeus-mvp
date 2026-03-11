'use client';

/**
 * SpoolListContext — state management backbone for v5.0 single-page view.
 *
 * Single source of truth for the spool card list. Manages:
 * - Adding/removing spools (with API fetch + localStorage sync)
 * - Batch refresh polling via refreshAll (stable callback using useRef)
 * - Single card refresh via refreshSingle
 * - On-mount hydration from localStorage
 *
 * Plan: 04-01-PLAN.md Task 1
 */

import React, {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useReducer,
  useRef,
} from 'react';
import type { SpoolCardData } from './types';
import { getSpoolStatus, batchGetStatus } from './api';
import { loadTags, saveTags } from './local-storage';

// ─── State & Actions ──────────────────────────────────────────────────────────

interface SpoolListState {
  spools: SpoolCardData[];
}

type SpoolListAction =
  | { type: 'SET_SPOOLS'; spools: SpoolCardData[] }
  | { type: 'ADD_SPOOL'; spool: SpoolCardData }
  | { type: 'REMOVE_SPOOL'; tag: string }
  | { type: 'UPDATE_SPOOL'; spool: SpoolCardData };

function reducer(state: SpoolListState, action: SpoolListAction): SpoolListState {
  switch (action.type) {
    case 'SET_SPOOLS':
      return { spools: action.spools };

    case 'ADD_SPOOL': {
      // Guard against duplicates
      const exists = state.spools.some(
        (s) => s.tag_spool === action.spool.tag_spool
      );
      if (exists) return state;
      return { spools: [...state.spools, action.spool] };
    }

    case 'REMOVE_SPOOL':
      return {
        spools: state.spools.filter((s) => s.tag_spool !== action.tag),
      };

    case 'UPDATE_SPOOL':
      return {
        spools: state.spools.map((s) =>
          s.tag_spool === action.spool.tag_spool ? action.spool : s
        ),
      };

    default:
      return state;
  }
}

// ─── Context ──────────────────────────────────────────────────────────────────

interface SpoolListContextValue {
  spools: SpoolCardData[];
  addSpool: (tag: string) => Promise<void>;
  removeSpool: (tag: string) => void;
  refreshAll: () => Promise<void>;
  refreshSingle: (tag: string) => Promise<void>;
}

const SpoolListContext = createContext<SpoolListContextValue | undefined>(
  undefined
);

// ─── Provider ─────────────────────────────────────────────────────────────────

export function SpoolListProvider({ children }: { children: React.ReactNode }) {
  const [state, dispatch] = useReducer(reducer, { spools: [] });

  // Stable ref so refreshAll does not depend on spools in its closure
  const spoolsRef = useRef<SpoolCardData[]>(state.spools);
  useEffect(() => {
    spoolsRef.current = state.spools;
  }, [state.spools]);

  // On mount: load persisted tags and hydrate via batchGetStatus
  useEffect(() => {
    const tags = loadTags();
    if (tags.length === 0) return;

    batchGetStatus(tags).then((fresh) => {
      dispatch({ type: 'SET_SPOOLS', spools: fresh });
    });
  }, []);

  // Sync localStorage whenever spools array changes
  useEffect(() => {
    saveTags(state.spools.map((s) => s.tag_spool));
  }, [state.spools]);

  // addSpool: fetch from API then add to state (guard duplicates in reducer)
  const addSpool = useCallback(async (tag: string) => {
    // Early exit if already tracked (avoids unnecessary API call)
    const alreadyTracked = spoolsRef.current.some((s) => s.tag_spool === tag);
    if (alreadyTracked) return;

    const spool = await getSpoolStatus(tag);
    dispatch({ type: 'ADD_SPOOL', spool });
  }, []);

  // removeSpool: remove from reducer state (localStorage syncs via effect)
  const removeSpool = useCallback((tag: string) => {
    dispatch({ type: 'REMOVE_SPOOL', tag });
  }, []);

  // refreshAll: stable callback that uses ref to avoid stale closures
  const refreshAll = useCallback(async () => {
    const tags = spoolsRef.current.map((s) => s.tag_spool);
    if (tags.length === 0) return;
    const fresh = await batchGetStatus(tags);
    dispatch({ type: 'SET_SPOOLS', spools: fresh });
  }, []);

  // refreshSingle: fetch one card and update in place
  const refreshSingle = useCallback(async (tag: string) => {
    const spool = await getSpoolStatus(tag);
    dispatch({ type: 'UPDATE_SPOOL', spool });
  }, []);

  const value: SpoolListContextValue = {
    spools: state.spools,
    addSpool,
    removeSpool,
    refreshAll,
    refreshSingle,
  };

  return (
    <SpoolListContext.Provider value={value}>
      {children}
    </SpoolListContext.Provider>
  );
}

// ─── Hook ─────────────────────────────────────────────────────────────────────

export function useSpoolList(): SpoolListContextValue {
  const ctx = useContext(SpoolListContext);
  if (ctx === undefined) {
    throw new Error('useSpoolList must be used within a SpoolListProvider');
  }
  return ctx;
}
