# Phase 9: Redis & Version Detection - Context

**Gathered:** 2026-02-02
**Status:** Ready for planning

<domain>
## Phase Boundary

This phase enables the system to support dual workflows (v3.0 legacy + v4.0 union-level tracking) by implementing persistent Redis locks and intelligent version detection. Redis locks persist indefinitely until FINALIZAR releases them, with lazy cleanup preventing abandoned locks. The system detects spool version (v3.0 vs v4.0) based on union count and routes to the appropriate workflow automatically.

</domain>

<decisions>
## Implementation Decisions

### Cleanup Strategy

- **Abandoned lock definition:** Lock exists in Redis >24 hours without matching Sheets.Ocupado_Por value
- **Cleanup execution:** Inline with INICIAR operation (not separate background task)
- **Cleanup logging:** Silent cleanup (no Metadata events for cleanup operations)
- **Sheets mismatch handling:** If Sheets.Ocupado_Por has value but Redis lock missing, recreate Redis lock (Sheets is source of truth)
- **Worker status check:** Ignore worker active status during cleanup (24h rule is sufficient)
- **Bulk cleanup:** Clean only one abandoned lock per INICIAR operation (eventual consistency, better performance)
- **Manual cleanup:** No admin endpoint (automatic cleanup only)

### Startup Reconciliation

- **Source of truth:** Sheets wins — If Sheets.Ocupado_Por has value, recreate Redis lock to match
- **Timestamp validation:** Skip locks older than 24 hours during reconciliation (don't recreate old locks)
- **Inactive worker handling:** Preserve occupation even if worker inactive (worker status doesn't affect reconciliation)

### Version Detection UX

- **Version indicator:** Show version badge ('v3.0' or 'v4.0') on spool cards for transparency
- **Detection timing:** Fetch version at P4 (spool selection) — just-in-time detection
- **Caching:** Cache version per session (once detected, reuse for session duration)
- **Workflow mismatch:** Auto-redirect to correct workflow if worker tries to use v3.0 workflow on v4.0 spool
- **Version logic:** Frontend detects by union count (Total_Uniones > 0 = v4.0, Total_Uniones = 0 = v3.0)

### Error Handling

- **Union count query failure:** Retry with exponential backoff (3 retries) before falling back to default
- **Redis unavailability:** Operate in Sheets-only mode (write Ocupado_Por without Redis lock) — degraded mode
- **Redis health visibility:** Transparent to workers (no health status display)
- **Data inconsistency:** Trust Operaciones.Total_Uniones as source of truth (ignore Uniones sheet count if mismatch)
- **FINALIZAR validation:** Strict validation — Backend validates version matches expected workflow before allowing completion
- **Version change mid-session:** Auto-adapt — Allow version change between INICIAR and FINALIZAR, adapt workflow dynamically
- **Diagnostic endpoint:** Add GET /api/diagnostic/{tag}/version with detailed response (union count, version, decision logic)
- **Retry configuration:** 3 retries with exponential backoff for version detection failures

### Claude's Discretion

- Cleanup execution order (before or after lock acquisition during INICIAR)
- Startup reconciliation timing (blocking vs. async during FastAPI startup event)
- Default workflow when version detection fails after all retries
- Exponential backoff timing parameters (initial delay, multiplier, max delay)

</decisions>

<specifics>
## Specific Ideas

- **Redis lock persistence:** Remove all TTL logic from v3.0 — locks persist until explicitly released
- **Version badge placement:** Display on spool card in P4, visible but not intrusive
- **Degraded mode behavior:** System remains operational even if Redis completely fails (Sheets-only mode)
- **Reconciliation use case:** Handles deployment restarts, Redis crashes, or Railway service restarts gracefully

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 09-redis-version-detection*
*Context gathered: 2026-02-02*
