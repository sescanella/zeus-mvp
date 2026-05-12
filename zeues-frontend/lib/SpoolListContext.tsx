'use client';

/**
 * SpoolListContext — server-driven state backbone for v5.0 single-page view.
 *
 * Source of truth: ZEUES_App_Audit Lista tab via /api/supervisor/list.
 * localStorage is NO longer authoritative; it only exists transiently as
 * legacy data that gets migrated on first post-deploy load.
 *
 * Migration safety net (3 layers, defense in depth — Matías cannot lose work):
 *   Layer 0: snapshot the verbatim localStorage value to Snapshots_Legacy
 *            BEFORE any per-tag write. If snapshot POST fails, we bail.
 *   Layer 1: per-tag migration with Promise.allSettled — localStorage is
 *            cleared ONLY after every legacy tag is confirmed in the server.
 *   Layer 2: ensureMigrated() runs before each mutation, in case the
 *            mount-time migration was skipped or partially failed earlier.
 *
 * Mutation flow (add/remove/setPriority):
 *   1. Optimistic dispatch immediately.
 *   2. fire server write.
 *   3. on failure: revert dispatch + rethrow → page.tsx shows toast.
 */

import React, {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useReducer,
  useRef,
  useState,
} from 'react';
import type { SpoolCardData } from './types';
import {
  getSpoolStatus,
  batchGetStatus,
  getSupervisorList,
  addSupervisorList,
  removeSupervisorList,
  setSupervisorPriority,
  postSupervisorLegacySnapshot,
} from './api';
import { loadPersistedSpools, STORAGE_KEY } from './local-storage';
import { getSessionId, pushAuditEvent } from './audit-buffer';
import { classifyApiError } from './error-classifier';

// ─── Priority normalization ──────────────────────────────────────────────────
//
// Frontend uses `number | null` (null = sin prioridad) so SpoolCard's chip
// renderer can stay agnostic. Backend uses 0|1|2|3 (0 = sin prioridad). Convert
// at the boundary; never leak server enum into UI components.

type ServerPriority = 0 | 1 | 2 | 3;

function priorityToServer(p: number | null): ServerPriority {
  if (p === 1 || p === 2 || p === 3) return p;
  return 0;
}
function priorityFromServer(p: ServerPriority): number | null {
  return p === 0 ? null : p;
}

// ─── State & Actions ─────────────────────────────────────────────────────────

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

// ─── Migration helper (Layers 0 + 1) ─────────────────────────────────────────

/**
 * One-shot migration of legacy localStorage entries to the server.
 *
 * - Returns null if there is nothing to migrate (no localStorage entry, SSR).
 * - Layer 0: snapshots the raw localStorage value to Snapshots_Legacy first.
 *   If the snapshot POST fails, bails out without touching localStorage —
 *   the next reload retries from scratch.
 * - Layer 1: Promise.allSettled so partial failures don't abort the rest.
 *   Clears localStorage ONLY when 100% of legacy tags landed server-side.
 * - Emits LIST_MIGRATE or LIST_MIGRATE_PARTIAL to the audit buffer.
 */
async function runMigrationIfPending(): Promise<void> {
  if (typeof window === 'undefined') return;

  const legacyRaw = window.localStorage.getItem(STORAGE_KEY);
  if (legacyRaw === null || legacyRaw.length === 0) return;

  // Layer 0 — verbatim snapshot before mutating anything.
  const snapshotId =
    typeof crypto !== 'undefined' && typeof crypto.randomUUID === 'function'
      ? crypto.randomUUID()
      : `snap-${Date.now()}-${Math.random().toString(36).slice(2, 10)}`;
  try {
    await postSupervisorLegacySnapshot({
      snapshot_id: snapshotId,
      captured_at: new Date().toISOString(),
      raw: legacyRaw,
      user_agent:
        typeof navigator !== 'undefined' ? navigator.userAgent : 'unknown',
    });
  } catch (err) {
    // eslint-disable-next-line no-console
    console.error('Layer 0 snapshot failed; aborting migration', err);
    return;
  }

  // Layer 1 — per-tag migration with allSettled.
  const legacy = loadPersistedSpools();
  if (legacy.length === 0) {
    // Snapshot raw exists but parser produced nothing usable. Safe to clear.
    window.localStorage.removeItem(STORAGE_KEY);
    return;
  }

  const sessionId = getSessionId();
  const results = await Promise.allSettled(
    legacy.map((t) =>
      addSupervisorList(t.tag, sessionId, priorityToServer(t.priority))
    )
  );
  const ok = results.filter((r) => r.status === 'fulfilled').length;

  if (ok === legacy.length) {
    window.localStorage.removeItem(STORAGE_KEY);
    pushAuditEvent({
      event_type: 'LIST_MIGRATE',
      payload: { migrated: ok },
    });
  } else {
    pushAuditEvent({
      event_type: 'LIST_MIGRATE_PARTIAL',
      payload: { ok, total: legacy.length },
    });
    // localStorage stays for next attempt (Layer 2 will pick this up).
  }
}

// ─── Context ─────────────────────────────────────────────────────────────────

interface SpoolListContextValue {
  spools: SpoolCardData[];
  priorities: Map<string, number | null>;
  hydrated: boolean;
  hydrationError: boolean;
  retryHydration: () => Promise<void>;
  addSpool: (tag: string) => Promise<void>;
  removeSpool: (tag: string) => Promise<void>;
  setPriority: (tag: string, priority: number | null) => Promise<void>;
  refreshAll: () => Promise<void>;
  refreshSingle: (tag: string) => Promise<void>;
}

const SpoolListContext = createContext<SpoolListContextValue | undefined>(
  undefined
);

// ─── Provider ────────────────────────────────────────────────────────────────

export function SpoolListProvider({ children }: { children: React.ReactNode }) {
  const [state, dispatch] = useReducer(reducer, {
    spools: [],
    priorities: new Map(),
  });
  const [hydrated, setHydrated] = useState(false);
  const [hydrationError, setHydrationError] = useState(false);

  // Stable ref so callbacks do not depend on spools in their closures.
  const spoolsRef = useRef<SpoolCardData[]>(state.spools);
  useEffect(() => {
    spoolsRef.current = state.spools;
  }, [state.spools]);

  const prioritiesRef = useRef<Map<string, number | null>>(state.priorities);
  useEffect(() => {
    prioritiesRef.current = state.priorities;
  }, [state.priorities]);

  // Hydration: server fetch → migration if needed → re-fetch → populate state.
  // On failure: 1 retry with delay from classifyApiError, then surface error
  // to the UI (hydrationError=true) so it can show a Reintentar button.
  // Returns true on success, false on final failure.
  const hydrateOnce = useCallback(
    async (cancelledRef: { current: boolean }): Promise<boolean> => {
      const initialList = await getSupervisorList();
      if (cancelledRef.current) return true;

      if (initialList.length === 0) {
        await runMigrationIfPending();
        if (cancelledRef.current) return true;
      }

      const finalList = await getSupervisorList();
      if (cancelledRef.current) return true;

      const tags = finalList.map((s) => s.tag_spool);
      const fullCards = tags.length > 0 ? await batchGetStatus(tags) : [];
      if (cancelledRef.current) return true;

      const prioMap = new Map<string, number | null>();
      finalList.forEach((s) =>
        prioMap.set(s.tag_spool, priorityFromServer(s.priority))
      );

      dispatch({ type: 'SET_SPOOLS', spools: fullCards });
      dispatch({ type: 'LOAD_PRIORITIES', priorities: prioMap });
      return true;
    },
    []
  );

  const hydrate = useCallback(
    async (cancelledRef: { current: boolean }) => {
      try {
        await hydrateOnce(cancelledRef);
        if (cancelledRef.current) return;
        setHydrationError(false);
        setHydrated(true);
        pushAuditEvent({ event_type: 'SESSION_START' });
      } catch (firstErr) {
        if (cancelledRef.current) return;
        const classified = classifyApiError(firstErr);
        // eslint-disable-next-line no-console
        console.warn(
          'SpoolListContext hydration failed, retrying',
          classified.type,
          firstErr
        );
        const delay = classified.retryDelay ?? 2000;
        await new Promise((r) => setTimeout(r, delay));
        if (cancelledRef.current) return;
        try {
          await hydrateOnce(cancelledRef);
          if (cancelledRef.current) return;
          setHydrationError(false);
          setHydrated(true);
          pushAuditEvent({ event_type: 'SESSION_START' });
        } catch (secondErr) {
          if (cancelledRef.current) return;
          // eslint-disable-next-line no-console
          console.error(
            'SpoolListContext hydration failed after retry',
            secondErr
          );
          setHydrationError(true);
          setHydrated(true);
        }
      }
    },
    [hydrateOnce]
  );

  // Mount: kick off initial hydration.
  useEffect(() => {
    const cancelledRef = { current: false };
    void hydrate(cancelledRef);
    return () => {
      cancelledRef.current = true;
    };
  }, [hydrate]);

  // User-triggered retry from the empty error state. Resets flags and tries
  // again from scratch; same retry-once policy.
  const retryHydration = useCallback(async () => {
    setHydrated(false);
    setHydrationError(false);
    const cancelledRef = { current: false };
    await hydrate(cancelledRef);
  }, [hydrate]);

  // Layer 2: before any mutation, ensure migration ran. Idempotent — if there's
  // nothing in localStorage, this is a no-op.
  const ensureMigrated = useCallback(async () => {
    if (typeof window === 'undefined') return;
    if (window.localStorage.getItem(STORAGE_KEY) !== null) {
      await runMigrationIfPending();
    }
  }, []);

  // addSpool: optimistic dispatch + server write + rollback on failure.
  const addSpool = useCallback(
    async (tag: string) => {
      await ensureMigrated();
      if (spoolsRef.current.some((s) => s.tag_spool === tag)) return;

      // getSpoolStatus throws on 404 — let it propagate before we touch state.
      const optimistic = await getSpoolStatus(tag);
      dispatch({ type: 'ADD_SPOOL', spool: optimistic });
      try {
        await addSupervisorList(tag, getSessionId(), 0);
      } catch (err) {
        dispatch({ type: 'REMOVE_SPOOL', tag });
        throw err;
      }
    },
    [ensureMigrated]
  );

  // removeSpool: optimistic dispatch + server write + rollback on failure.
  const removeSpool = useCallback(
    async (tag: string) => {
      await ensureMigrated();
      const previous = spoolsRef.current.find((s) => s.tag_spool === tag);
      if (!previous) return;

      dispatch({ type: 'REMOVE_SPOOL', tag });
      try {
        await removeSupervisorList(tag, getSessionId());
      } catch (err) {
        dispatch({ type: 'ADD_SPOOL', spool: previous });
        throw err;
      }
    },
    [ensureMigrated]
  );

  // setPriority: optimistic dispatch + server write + rollback on failure.
  const setPriority = useCallback(
    async (tag: string, priority: number | null) => {
      await ensureMigrated();
      const previousPriority = prioritiesRef.current.get(tag) ?? null;

      dispatch({ type: 'SET_PRIORITY', tag, priority });
      try {
        await setSupervisorPriority(
          tag,
          priorityToServer(priority),
          getSessionId()
        );
      } catch (err) {
        dispatch({
          type: 'SET_PRIORITY',
          tag,
          priority: previousPriority,
        });
        throw err;
      }
    },
    [ensureMigrated]
  );

  // refreshAll: re-fetch full card data for all currently-tracked tags.
  // Does NOT re-fetch the supervisor Lista — relies on optimistic state for that.
  const refreshAll = useCallback(async () => {
    const tags = spoolsRef.current.map((s) => s.tag_spool);
    if (tags.length === 0) return;
    const fresh = await batchGetStatus(tags);
    dispatch({ type: 'SET_SPOOLS', spools: fresh });
  }, []);

  const refreshSingle = useCallback(async (tag: string) => {
    const spool = await getSpoolStatus(tag);
    dispatch({ type: 'UPDATE_SPOOL', spool });
  }, []);

  const value: SpoolListContextValue = {
    spools: state.spools,
    priorities: state.priorities,
    hydrated,
    hydrationError,
    retryHydration,
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

// ─── Hook ────────────────────────────────────────────────────────────────────

export function useSpoolList(): SpoolListContextValue {
  const ctx = useContext(SpoolListContext);
  if (ctx === undefined) {
    throw new Error('useSpoolList must be used within a SpoolListProvider');
  }
  return ctx;
}
