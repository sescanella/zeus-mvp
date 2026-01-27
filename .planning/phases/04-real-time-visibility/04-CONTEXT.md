# Phase 4: Real-Time Visibility - Context

**Gathered:** 2026-01-27
**Status:** Ready for planning

<domain>
## Phase Boundary

Display real-time updates of spool occupation status to workers. Workers see who is working on which spool and what's available, with sub-10-second refresh latency. This phase delivers live visibility into the manufacturing floor's current state without manual refresh.

New capabilities like notifications, alerts, or chat belong in other phases.

</domain>

<decisions>
## Implementation Decisions

### Real-time update mechanism
- **Technology:** Server-Sent Events (SSE) — one-way server → client, simple HTTP-based, built-in auto-reconnect
- **Event triggers:** All state changes (TOMAR, PAUSAR, COMPLETAR events) plus state machine transitions (ARM/SOLD progress changes)
- **Connection handling:** Auto-reconnect with exponential backoff on disconnect (retry delays increase: 1s, 2s, 4s... to avoid hammering server)
- **Mobile lifecycle:** Reconnect on wake/foreground — SSE disconnects when app backgrounds, auto-reconnects when returning to foreground
- **Connection status:** Visual indicator (green/red dot) always visible to show connection health
- **Heartbeat:** No keepalive mechanism — rely on browser EventSource auto-reconnect (simpler, less server load)

### Dashboard display design
- **Information shown per occupied spool:**
  - Worker name and ID (e.g., "MR(93)" or full "Mauricio Rodriguez (93)")
  - Operation in progress (ARM, SOLD, METROLOGIA)
  - Estado_Detalle combined state (e.g., "ARM parcial, SOLD pendiente")
- **Visual organization:** List view (scrollable rows) — simple vertical list, each row = one spool, easy to scan
- **Color coding:** No color coding — simple monochrome with icons (accessibility-first, clean design)
- **Navigation:** Dedicated dashboard page — new route/page in app, workers navigate there to see occupation status
- **Interaction:** No interaction — read-only display, purely informational, no tap actions
- **Empty state:** Yes, friendly message — show "No spools currently occupied" or "All spools available" with helpful icon
- **Update animation:** Instant update, no animation — items appear/disappear immediately, fast and simple

### Available spools filtering
- **Real-time updates:** Yes, via SSE — available spools list automatically removes items when TOMAr'd, adds back when PAUSAR'd
- **Filtering approach:** Current flow (P4 spool selection) — operation already selected in P2, P4 shows filtered spools matching that operation
- **Race condition UX:** Show friendly error message — display "This spool was just taken by [Worker]" and refresh list automatically when worker tries to TOMAR already-occupied spool
- **Additional context displayed:** State machine progress — show Estado_Detalle (e.g., "ARM completado, SOLD pendiente") so workers know what operations remain

### Claude's Discretion
- Redis pub/sub channel architecture (single channel vs dedicated channels per event type)
- Exact reconnection backoff timing (initial delay, max delay, backoff multiplier)
- SSE endpoint implementation details (sse-starlette library integration)
- Frontend EventSource integration pattern (React hooks, context, state management)
- Error message wording and formatting
- Icon choices for operations and connection status

</decisions>

<specifics>
## Specific Ideas

- **Connection status indicator:** Green/red dot should be small, unobtrusive, but always visible (e.g., top-right corner of dashboard)
- **Friendly error on race condition:** "Este carrete fue tomado por [Worker Name]" — use Spanish, match existing ZEUES tone
- **Estado_Detalle as context:** Workers use this to prioritize which spool to pick (e.g., prefer spools with ARM complete when doing SOLD)

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope.

</deferred>

---

*Phase: 04-real-time-visibility*
*Context gathered: 2026-01-27*
