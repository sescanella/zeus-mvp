/**
 * audit-buffer.ts — singleton in-memory queue for supervisor audit events.
 *
 * Why a singleton: UI events (modal open/close, navigation, session lifecycle)
 * are emitted from many places; batching them reduces network cost. A
 * module-level buffer in Next.js client is naturally bound to the tab's
 * lifetime — exactly the granularity we want for `session_id`.
 *
 * Lifecycle:
 *   - First push lazily starts the 30s flush timer and installs unload listeners.
 *   - Every 30s, the buffer is drained via POST /api/supervisor/audit/batch
 *     (already chunked at 100 events server-side).
 *   - On `visibilitychange=hidden` or `beforeunload`, a sendBeacon flush fires
 *     to deliver the tail without blocking page exit.
 *
 * Failure mode: if a flush POST fails (network/5xx), the events return to the
 * head of the buffer for the next interval to retry. The buffer is capped at
 * MAX_BUFFER_SIZE — when re-queueing would exceed the cap, oldest events drop
 * (FIFO eviction). Acceptable: list mutations are audited server-side
 * (SupervisorService); UI events are nice-to-have analytics.
 *
 * SSR safety: every browser-API access (sessionStorage, navigator, window,
 * setInterval) is guarded by `typeof window === 'undefined'`. Mirrors the
 * pattern in local-storage.ts and haptic.ts.
 */

import { pushSupervisorAuditBatch } from './api';
import type { SupervisorAuditEvent, SupervisorEventType } from './types';

// ─── Configuration ───────────────────────────────────────────────────────────

const FLUSH_INTERVAL_MS = 30_000;
const MAX_BUFFER_SIZE = 500;
/** Upper bound on events sent via sendBeacon to stay below ~64KB Beacon limit. */
const UNLOAD_FLUSH_CAP = 100;
const SESSION_KEY = 'zeues_audit_session_id';
const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

// ─── Module state (per tab) ──────────────────────────────────────────────────

let buffer: SupervisorAuditEvent[] = [];
let flushTimer: ReturnType<typeof setInterval> | null = null;
let lifecycleListenersInstalled = false;
let cachedSessionId: string | null = null;

// ─── Helpers ─────────────────────────────────────────────────────────────────

function generateUuid(): string {
  if (
    typeof crypto !== 'undefined' &&
    typeof crypto.randomUUID === 'function'
  ) {
    return crypto.randomUUID();
  }
  // Fallback for older WebViews / non-browser contexts.
  return (
    Date.now().toString(36) + Math.random().toString(36).slice(2, 12)
  );
}

/**
 * Returns the current tab's session_id (lazy-init on first call).
 *
 * Lives in sessionStorage: survives reloads within the tab, dies when the tab
 * closes. New tab = new session. SSR-safe: returns a stable empty-ish string
 * server-side (server never pushes audit events anyway).
 */
export function getSessionId(): string {
  if (cachedSessionId) return cachedSessionId;
  if (typeof window === 'undefined') {
    return '';
  }

  try {
    const existing = window.sessionStorage.getItem(SESSION_KEY);
    if (existing && existing.length > 0) {
      cachedSessionId = existing;
      return existing;
    }
    const fresh = generateUuid();
    window.sessionStorage.setItem(SESSION_KEY, fresh);
    cachedSessionId = fresh;
    return fresh;
  } catch {
    // sessionStorage can throw in private mode / quota exceeded.
    // Fall back to in-memory only — still better than crashing.
    if (!cachedSessionId) cachedSessionId = generateUuid();
    return cachedSessionId;
  }
}

function ensureFlushTimer(): void {
  if (typeof window === 'undefined') return;
  if (flushTimer !== null) return;
  flushTimer = setInterval(() => {
    void flushAuditBuffer();
  }, FLUSH_INTERVAL_MS);
}

function ensureLifecycleListeners(): void {
  if (typeof window === 'undefined') return;
  if (lifecycleListenersInstalled) return;
  lifecycleListenersInstalled = true;

  // visibilitychange fires reliably on tab switches AND on iOS Safari close.
  window.addEventListener('visibilitychange', () => {
    if (document.visibilityState === 'hidden') flushOnUnload();
  });
  // beforeunload as belt-and-suspenders on desktop.
  window.addEventListener('beforeunload', () => {
    flushOnUnload();
  });
}

// ─── Public API ──────────────────────────────────────────────────────────────

export type PushInput = {
  event_type: SupervisorEventType;
  tag_spool?: string;
  modal?: string;
  route?: string;
  /**
   * Optional structured payload. Will be JSON-stringified into payload_json.
   * Backend stores it verbatim and never parses, so the shape is up to caller.
   */
  payload?: Record<string, unknown>;
};

/**
 * Queue one audit event for delivery.
 *
 * Stamps `id`, `timestamp`, and `session_id` automatically. Returns
 * synchronously — the actual POST happens on the next flush tick.
 *
 * Callers should NOT await this: it never throws and never blocks.
 */
export function pushAuditEvent(input: PushInput): void {
  if (typeof window === 'undefined') return;

  const event: SupervisorAuditEvent = {
    id: generateUuid(),
    timestamp: new Date().toISOString(),
    session_id: getSessionId(),
    event_type: input.event_type,
    tag_spool: input.tag_spool ?? null,
    modal: input.modal ?? null,
    route: input.route ?? null,
    payload_json: input.payload ? JSON.stringify(input.payload) : null,
  };

  buffer.push(event);

  // Cap the buffer in case flushes are failing repeatedly.
  if (buffer.length > MAX_BUFFER_SIZE) {
    buffer = buffer.slice(-MAX_BUFFER_SIZE);
  }

  ensureFlushTimer();
  ensureLifecycleListeners();
}

/**
 * Force-flush the buffer over the regular POST path.
 *
 * Used by tests, by the visibility/unload handlers (indirectly), and by
 * any caller that wants delivery before the next 30s tick.
 */
export async function flushAuditBuffer(): Promise<void> {
  if (typeof window === 'undefined') return;
  if (buffer.length === 0) return;

  const inFlight = buffer.splice(0, buffer.length);
  try {
    await pushSupervisorAuditBatch(inFlight);
  } catch (err) {
    // Return events to the head of the buffer; cap to MAX_BUFFER_SIZE.
    buffer = [...inFlight, ...buffer].slice(-MAX_BUFFER_SIZE);
    // eslint-disable-next-line no-console
    console.warn(
      'audit-buffer flush failed; will retry next interval',
      err
    );
  }
}

/**
 * Internal: flush via sendBeacon during page unload.
 *
 * sendBeacon is the only API reliably delivered during unload across browsers.
 * Falls back to fetch({keepalive:true}) when sendBeacon is missing (older
 * WebViews). Capped at UNLOAD_FLUSH_CAP events to stay within Beacon's ~64KB
 * body limit; tail-end events past the cap may be lost (acceptable).
 */
function flushOnUnload(): void {
  if (typeof window === 'undefined') return;
  if (buffer.length === 0) return;

  const events = buffer.splice(0, Math.min(buffer.length, UNLOAD_FLUSH_CAP));
  const url = `${API_URL}/api/supervisor/audit/batch`;
  const body = JSON.stringify({ events });

  try {
    if (
      typeof navigator !== 'undefined' &&
      typeof navigator.sendBeacon === 'function'
    ) {
      const blob = new Blob([body], { type: 'application/json' });
      navigator.sendBeacon(url, blob);
      return;
    }
    if (typeof fetch !== 'undefined') {
      fetch(url, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body,
        keepalive: true,
      }).catch(() => {
        /* swallow — we're unloading */
      });
    }
  } catch {
    // Best effort during unload; never throw.
  }
}

/**
 * Read-only snapshot of the in-memory queue (for tests).
 *
 * Returns a frozen copy, NOT a reference to the live buffer.
 */
export function getBufferSnapshot(): readonly SupervisorAuditEvent[] {
  return Object.freeze([...buffer]);
}

/**
 * Test-only: reset module state. Not exported in production builds.
 *
 * @internal
 */
export function __resetAuditBufferForTests(): void {
  if (flushTimer !== null) {
    clearInterval(flushTimer);
    flushTimer = null;
  }
  buffer = [];
  cachedSessionId = null;
  lifecycleListenersInstalled = false;
}
