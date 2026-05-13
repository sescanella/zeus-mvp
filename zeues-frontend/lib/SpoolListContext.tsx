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
 * Mutation flow (add/remove):
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
import type { SpoolCardData, Worker } from './types';
import {
  getSpoolStatus,
  batchGetStatus,
  getSupervisorList,
  addSupervisorList,
  removeSupervisorList,
  postSupervisorLegacySnapshot,
  type BatchStatusError,
} from './api';
import { loadPersistedSpools, STORAGE_KEY } from './local-storage';
import { getSessionId, pushAuditEvent } from './audit-buffer';
import { classifyApiError } from './error-classifier';

// ─── State & Actions ─────────────────────────────────────────────────────────

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
      return { ...state, spools: action.spools };

    case 'ADD_SPOOL': {
      const exists = state.spools.some(
        (s) => s.tag_spool === action.spool.tag_spool
      );
      if (exists) return state;
      return { ...state, spools: [...state.spools, action.spool] };
    }

    case 'REMOVE_SPOOL':
      return {
        ...state,
        spools: state.spools.filter((s) => s.tag_spool !== action.tag),
      };

    case 'UPDATE_SPOOL':
      return {
        ...state,
        spools: state.spools.map((s) =>
          s.tag_spool === action.spool.tag_spool ? action.spool : s
        ),
      };

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
    legacy.map((t) => addSupervisorList(t.tag, sessionId))
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
  hydrated: boolean;
  hydrationError: boolean;
  retryHydration: () => Promise<void>;
  addSpool: (tag: string) => Promise<void>;
  removeSpool: (tag: string) => Promise<void>;
  /**
   * Re-fetch all tracked spools. Returns per-tag errors (e.g. SPOOL_DATA_CORRUPT)
   * so the caller can surface them as toasts. Empty array if all OK.
   */
  refreshAll: () => Promise<BatchStatusError[]>;
  refreshSingle: (tag: string) => Promise<void>;
  applyIniciarOptimistic: (
    tag: string,
    worker: Worker,
    operacion: 'ARM' | 'SOLD',
  ) => void;
}

// Format a Date as "DD-MM-YYYY HH:MM:SS" in America/Santiago — the same format
// the backend writes to Sheets. Used only for display until the 30s poller
// supersedes it with the server-side timestamp.
function formatChileDateTime(d: Date): string {
  const parts = new Intl.DateTimeFormat('en-GB', {
    timeZone: 'America/Santiago',
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
    hour12: false,
  }).formatToParts(d);
  const get = (t: string) => parts.find((p) => p.type === t)?.value ?? '00';
  return `${get('day')}-${get('month')}-${get('year')} ${get('hour')}:${get('minute')}:${get('second')}`;
}

const SpoolListContext = createContext<SpoolListContextValue | undefined>(
  undefined
);

// ─── Provider ────────────────────────────────────────────────────────────────

export function SpoolListProvider({ children }: { children: React.ReactNode }) {
  const [state, dispatch] = useReducer(reducer, {
    spools: [],
  });
  const [hydrated, setHydrated] = useState(false);
  const [hydrationError, setHydrationError] = useState(false);

  // Stable ref so callbacks do not depend on spools in their closures.
  const spoolsRef = useRef<SpoolCardData[]>(state.spools);
  useEffect(() => {
    spoolsRef.current = state.spools;
  }, [state.spools]);

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
      // B-002: batchGetStatus now returns { spools, errors }. At hydration
      // we only need the spools — errors (if any) are logged below and
      // will re-surface to the operator on the next poller tick.
      const batchResult = tags.length > 0
        ? await batchGetStatus(tags)
        : { spools: [], errors: [] };
      const fullCards = batchResult.spools;
      if (batchResult.errors.length > 0) {
        // eslint-disable-next-line no-console
        console.warn(
          `SpoolListContext.hydrate: ${batchResult.errors.length} spool(s) ` +
          `failed to parse on first load — will retry on next 30s poll`,
          batchResult.errors
        );
      }
      if (cancelledRef.current) return true;

      dispatch({ type: 'SET_SPOOLS', spools: fullCards });
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
        await addSupervisorList(tag, getSessionId());
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

  // refreshAll: re-fetch full card data for all currently-tracked tags.
  // Does NOT re-fetch the supervisor Lista — relies on optimistic state for that.
  //
  // B-002: returns the per-tag errors from batch-status so the poller in
  // page.tsx can surface them as toasts. Empty array on success / no errors.
  const refreshAll = useCallback(async (): Promise<BatchStatusError[]> => {
    const tags = spoolsRef.current.map((s) => s.tag_spool);
    if (tags.length === 0) return [];
    const { spools: fresh, errors } = await batchGetStatus(tags);
    dispatch({ type: 'SET_SPOOLS', spools: fresh });
    return errors;
  }, []);

  const refreshSingle = useCallback(async (tag: string) => {
    const spool = await getSpoolStatus(tag);
    dispatch({ type: 'UPDATE_SPOOL', spool });
  }, []);

  // Optimistic UI for INICIAR success (B-001). The Google Sheets API has a
  // 200-800ms read-after-write inconsistency window: refreshSingle right
  // after a successful write reads back the pre-write row, leaving the card
  // stuck on "Libre" until the 30s poller fires. We derive the new card
  // locally from inputs the caller already has — backend's _derive_estado
  // rule #5 says ocupado_por set → estado_trabajo = EN_PROGRESO. The poller
  // reconciles any divergence within 30 s.
  const applyIniciarOptimistic = useCallback(
    (tag: string, worker: Worker, operacion: 'ARM' | 'SOLD') => {
      const prev = spoolsRef.current.find((s) => s.tag_spool === tag);
      if (!prev) return;

      const nombre = worker.apellido
        ? `${worker.nombre} ${worker.apellido}`
        : worker.nombre;

      const next: SpoolCardData = {
        ...prev,
        ocupado_por: worker.nombre_completo,
        ocupado_por_display: nombre,
        fecha_ocupacion: formatChileDateTime(new Date()),
        operacion_actual: operacion,
        estado_trabajo: 'EN_PROGRESO',
      };
      dispatch({ type: 'UPDATE_SPOOL', spool: next });
    },
    [],
  );

  const value: SpoolListContextValue = {
    spools: state.spools,
    hydrated,
    hydrationError,
    retryHydration,
    addSpool,
    removeSpool,
    refreshAll,
    refreshSingle,
    applyIniciarOptimistic,
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
