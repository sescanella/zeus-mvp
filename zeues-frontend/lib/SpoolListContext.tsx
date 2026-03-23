'use client';

/**
 * SpoolListContext — state management backbone for v5.0 single-page view.
 *
 * Single source of truth for the spool card list. Manages:
 * - Adding/removing spools (with API fetch + localStorage sync)
 * - Batch refresh polling via refreshAll (stable callback using useRef)
 * - Single card refresh via refreshSingle
 * - On-mount hydration from localStorage
 * - Priority management per spool (1=urgente, 2=alta, 3=normal, null=sin prioridad)
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
import { loadPersistedSpools, savePersistedSpools } from './local-storage';
import type { PersistedSpool } from './local-storage';

// ─── State & Actions ──────────────────────────────────────────────────────────

interface SpoolListState {
  spools: SpoolCardData[];
  priorities: Map<string, number | null>;
}

type SpoolListAction =
  | { type: 'SET_SPOOLS'; spools: SpoolCardData[] }
  | { type: 'ADD_SPOOL'; spool: SpoolCardData }
  | { type: 'REMOVE_SPOOL'; tag: string }
  | { type: 'UPDATE_SPOOL'; spool: SpoolCardData }
  | { type: 'SET_PRIORITY'; tag: string; priority: number | null }
  | { type: 'LOAD_PRIORITIES'; priorities: Map<string, number | null> };

function reducer(state: SpoolListState, action: SpoolListAction): SpoolListState {
  switch (action.type) {
    case 'SET_SPOOLS':
      return { ...state, spools: action.spools };

    case 'ADD_SPOOL': {
      // Guard against duplicates
      const exists = state.spools.some(
        (s) => s.tag_spool === action.spool.tag_spool
      );
      if (exists) return state;
      return { ...state, spools: [...state.spools, action.spool] };
    }

    case 'REMOVE_SPOOL': {
      const newPriorities = new Map(state.priorities);
      newPriorities.delete(action.tag);
      return {
        spools: state.spools.filter((s) => s.tag_spool !== action.tag),
        priorities: newPriorities,
      };
    }

    case 'UPDATE_SPOOL':
      return {
        ...state,
        spools: state.spools.map((s) =>
          s.tag_spool === action.spool.tag_spool ? action.spool : s
        ),
      };

    case 'SET_PRIORITY': {
      const newPriorities = new Map(state.priorities);
      newPriorities.set(action.tag, action.priority);
      return { ...state, priorities: newPriorities };
    }

    case 'LOAD_PRIORITIES':
      return { ...state, priorities: action.priorities };

    default:
      return state;
  }
}

// ─── Context ──────────────────────────────────────────────────────────────────

interface SpoolListContextValue {
  spools: SpoolCardData[];
  priorities: Map<string, number | null>;
  addSpool: (tag: string) => Promise<void>;
  removeSpool: (tag: string) => void;
  setPriority: (tag: string, priority: number | null) => void;
  refreshAll: () => Promise<void>;
  refreshSingle: (tag: string) => Promise<void>;
}

const SpoolListContext = createContext<SpoolListContextValue | undefined>(
  undefined
);

// ─── Provider ─────────────────────────────────────────────────────────────────

export function SpoolListProvider({ children }: { children: React.ReactNode }) {
  const [state, dispatch] = useReducer(reducer, { spools: [], priorities: new Map() });

  // Stable ref so refreshAll does not depend on spools in its closure
  const spoolsRef = useRef<SpoolCardData[]>(state.spools);
  useEffect(() => {
    spoolsRef.current = state.spools;
  }, [state.spools]);

  // On mount: load persisted spools (with priorities) and hydrate via batchGetStatus
  useEffect(() => {
    const persisted = loadPersistedSpools();
    if (persisted.length === 0) return;

    // Load priorities
    const prioMap = new Map<string, number | null>();
    persisted.forEach((p) => prioMap.set(p.tag, p.priority));
    dispatch({ type: 'LOAD_PRIORITIES', priorities: prioMap });

    // Hydrate spool data from API
    const tags = persisted.map((p) => p.tag);
    batchGetStatus(tags).then((fresh) => {
      dispatch({ type: 'SET_SPOOLS', spools: fresh });
    });
  }, []);

  // Sync localStorage whenever spools or priorities change
  useEffect(() => {
    const persisted: PersistedSpool[] = state.spools.map((s) => ({
      tag: s.tag_spool,
      priority: state.priorities.get(s.tag_spool) ?? null,
    }));
    savePersistedSpools(persisted);
  }, [state.spools, state.priorities]);

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

  // setPriority: update priority for a tracked spool
  const setPriority = useCallback((tag: string, priority: number | null) => {
    dispatch({ type: 'SET_PRIORITY', tag, priority });
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
    priorities: state.priorities,
    addSpool,
    removeSpool,
    setPriority,
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
