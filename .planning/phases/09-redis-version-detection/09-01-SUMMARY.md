---
phase: 09-redis-version-detection
plan: 01
subsystem: backend-redis
tags: [redis, persistent-locks, degraded-mode, fallback, v4.0]

# Dependency graph
requires:
  - phase: 02-core-location-tracking
    provides: Redis lock service with TTL-based locks
provides:
  - Persistent Redis locks without TTL (v4.0 mode)
  - Two-step acquisition pattern (SET with safety TTL, then PERSIST)
  - Degraded mode fallback for Redis unavailability
  - Backward compatibility with v3.0 TTL mode
affects: [09-02, 10-iniciar-endpoints, 11-finalizar-logic]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Two-step persistent lock acquisition (SET + PERSIST)"
    - "Degraded mode fallback to Sheets-only operation"
    - "Lock value format with timestamp (worker_id:token:timestamp)"

key-files:
  created: []
  modified:
    - backend/config.py
    - backend/services/redis_lock_service.py
    - tests/unit/test_redis_lock_service.py

key-decisions:
  - "D42 (09-01): Use two-step acquisition (SET with 10s safety TTL, then PERSIST) to prevent orphaned locks"
  - "D43 (09-01): Lock value format includes timestamp for lazy cleanup age detection"
  - "D44 (09-01): Degraded mode falls back to Sheets-only when Redis unavailable"
  - "D45 (09-01): REDIS_PERSISTENT_LOCKS flag controls v3.0 vs v4.0 lock mode"

patterns-established:
  - "Pattern 1: Two-step persistent lock - SET NX EX (safety TTL) then PERSIST (remove TTL)"
  - "Pattern 2: Degraded mode token format - DEGRADED:worker_id:timestamp"
  - "Pattern 3: Backward compatibility via configuration flag (REDIS_PERSISTENT_LOCKS)"

# Metrics
duration: 7.5min
completed: 2026-02-02
---

# Phase 9 Plan 1: Persistent Locks & Degraded Mode Summary

**Two-step persistent lock acquisition with PERSIST command, degraded mode Sheets-only fallback, and backward-compatible v3.0 TTL mode**

## Performance

- **Duration:** 7.5 min
- **Started:** 2026-02-02T14:11:55Z
- **Completed:** 2026-02-02T14:19:24Z
- **Tasks:** 4
- **Files modified:** 3

## Accomplishments
- Persistent Redis locks without TTL for long-running v4.0 work sessions (5-8 hours)
- Two-step acquisition prevents orphaned locks (SET with 10s safety TTL, then PERSIST)
- Degraded mode enables Sheets-only operation when Redis unavailable
- Backward compatibility maintained with v3.0 TTL-based locks

## Task Commits

Each task was committed atomically:

1. **Task 1: Add persistent lock configuration** - `37a3b89` (feat)
   - Added REDIS_PERSISTENT_LOCKS flag (default True for v4.0)
   - Added REDIS_SAFETY_TTL for initial acquisition (10 seconds)

2. **Task 2: Implement two-step persistent lock acquisition** - `c88e539` (feat)
   - Modified acquire_lock() for dual-mode operation (persistent vs TTL)
   - Two-step: SET with safety TTL, then PERSIST to remove TTL
   - Added timestamp to lock value format (worker_id:token:timestamp)
   - Added _parse_lock_timestamp() helper method

3. **Task 3: Implement degraded mode for Redis unavailability** - `4c02400` (feat)
   - Added is_degraded_mode() method
   - Wrapped Redis operations to catch connection errors
   - Fallback to Sheets-only with DEGRADED:worker_id:timestamp token
   - release_lock() skips Redis operations for degraded tokens

4. **Task 4: Add unit tests for persistent locks and degraded mode** - `c7d0133` (test)
   - 10 new tests for v4.0 persistent locks
   - 7 new tests for degraded mode
   - Fixed 6 existing tests for new signatures
   - All 23 tests passing

## Files Created/Modified

- `backend/config.py` - Added REDIS_PERSISTENT_LOCKS and REDIS_SAFETY_TTL configuration flags
- `backend/services/redis_lock_service.py` - Implemented two-step acquisition, degraded mode fallback, timestamp support
- `tests/unit/test_redis_lock_service.py` - Comprehensive test coverage for persistent locks and degraded mode

## Decisions Made

**D42 (09-01):** Use two-step acquisition (SET with 10s safety TTL, then PERSIST)
- Prevents orphaned locks if process crashes between SET and PERSIST
- Safety TTL auto-expires lock if PERSIST never called

**D43 (09-01):** Lock value format includes timestamp for lazy cleanup age detection
- Format: worker_id:token:timestamp (DD-MM-YYYY HH:MM:SS)
- Enables lazy cleanup to detect locks > 24 hours old
- Backward compatible with legacy format (worker_id:token)

**D44 (09-01):** Degraded mode falls back to Sheets-only when Redis unavailable
- System remains operational during Redis outages
- DEGRADED:worker_id:timestamp token format distinguishes from normal locks
- Queries Sheets.Ocupado_Por for occupation check

**D45 (09-01):** REDIS_PERSISTENT_LOCKS flag controls v3.0 vs v4.0 lock mode
- Environment variable for easy toggling between modes
- Default True for v4.0 persistent locks
- Maintains v3.0 TTL behavior when False

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None - implementation proceeded as planned with all tests passing.

## User Setup Required

None - no external service configuration required. Configuration flags can be set via environment variables:

```bash
# v4.0 persistent locks (default)
REDIS_PERSISTENT_LOCKS=true
REDIS_SAFETY_TTL=10

# v3.0 TTL mode (backward compatibility)
REDIS_PERSISTENT_LOCKS=false
```

## Next Phase Readiness

**Ready for Plan 09-02 (Lazy Cleanup):**
- Persistent locks implemented with timestamp tracking
- Lock value format supports age detection (timestamp embedded)
- Degraded mode provides fallback for Redis failures
- Configuration flags allow testing both modes

**Ready for Plan 09-03 (Startup Reconciliation):**
- Degraded mode pattern established for Sheets-as-source-of-truth
- Lock value parsing supports timestamp extraction
- sheets_repository integration pattern ready for expansion

**No blockers.** Phase 9 Plan 1 complete.

---
*Phase: 09-redis-version-detection*
*Completed: 2026-02-02*
