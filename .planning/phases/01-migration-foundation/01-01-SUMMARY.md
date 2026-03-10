---
phase: 01-migration-foundation
plan: 01
subsystem: ui
tags: [typescript, nextjs, localstorage, types, api-client, jest]

# Dependency graph
requires:
  - phase: 00-backend-nuevos-endpoints
    provides: SpoolStatus backend model, /api/spool/{tag}/status, /api/spools/batch-status endpoints
provides:
  - SpoolCardData interface (12 fields mirroring backend SpoolStatus)
  - EstadoTrabajo and OperacionActual union types
  - getSpoolStatus(tag) and batchGetStatus(tags) API client functions
  - localStorage persistence utility (loadTags, saveTags, addTag, removeTag, clearTags)
affects:
  - 01-02 (useSpoolList hook uses loadTags/saveTags/addTag/removeTag)
  - 01-03 (useBatchRefresh uses batchGetStatus and SpoolCardData)
  - Phase 2 SpoolCard component uses SpoolCardData type
  - Phase 4 integration uses all three foundations

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "SSR-safe localStorage: typeof window guard on every access in Next.js"
    - "snake_case TypeScript interfaces: match backend JSON response keys exactly (no camelCase conversion)"
    - "handleResponse<T> reuse: v5.0 API functions follow same pattern as existing api.ts functions"
    - "TDD with jsdom: jest-environment-jsdom provides localStorage mock automatically"

key-files:
  created:
    - zeues-frontend/lib/local-storage.ts
    - zeues-frontend/__tests__/lib/local-storage.test.ts
  modified:
    - zeues-frontend/lib/types.ts
    - zeues-frontend/lib/api.ts

key-decisions:
  - "snake_case field names in SpoolCardData match backend JSON directly — no camelCase transform needed in API client"
  - "getSpoolStatus and batchGetStatus use handleResponse without extra try/catch wrapping (follows pattern of simpler functions like completarMetrologia)"
  - "STORAGE_KEY exported as named const (not just used internally) so test can assert exact key value"

patterns-established:
  - "SSR-safe localStorage access: check typeof window !== 'undefined' before every localStorage call"
  - "JSON parse guard chain: try/catch + Array.isArray + element type filter for safe deserialization"

requirements-completed: [CARD-02, CARD-03, API-01, API-02]

# Metrics
duration: 3min
completed: 2026-03-10
---

# Phase 01 Plan 01: Data Layer Foundation Summary

**SpoolCardData interface (12 fields), getSpoolStatus/batchGetStatus API functions, and SSR-safe localStorage utility with 23 passing tests — v5.0 data layer complete**

## Performance

- **Duration:** 3 min
- **Started:** 2026-03-10T22:32:58Z
- **Completed:** 2026-03-10T22:35:45Z
- **Tasks:** 3
- **Files modified:** 4 (2 modified, 2 created)

## Accomplishments

- Added SpoolCardData (12 fields), EstadoTrabajo (7 literals), OperacionActual types to types.ts; updated IniciarRequest.worker_nombre to optional and FinalizarRequest with action_override
- Added getSpoolStatus and batchGetStatus to api.ts following existing handleResponse pattern
- Created local-storage.ts with 5 exported functions (SSR-safe, no `any` types) and 23 tests all passing

## Task Commits

Each task was committed atomically:

1. **Task 1: Add SpoolCardData types and update IniciarRequest/FinalizarRequest** - `bbab86b` (feat)
2. **Task 2: Add getSpoolStatus and batchGetStatus to API client** - `527c361` (feat)
3. **Task 3 RED: Failing localStorage tests** - `4812724` (test)
4. **Task 3 GREEN: localStorage implementation** - `89417f3` (feat)

**Plan metadata:** (docs commit after SUMMARY)

_Note: TDD tasks may have multiple commits (test → feat → refactor)_

## Files Created/Modified

- `zeues-frontend/lib/types.ts` - Added EstadoTrabajo, OperacionActual, SpoolCardData; made IniciarRequest.worker_nombre optional; added action_override and made selected_unions optional on FinalizarRequest
- `zeues-frontend/lib/api.ts` - Imported SpoolCardData; added getSpoolStatus and batchGetStatus in v5.0 section before v4.0 section
- `zeues-frontend/lib/local-storage.ts` - New file: STORAGE_KEY, loadTags, saveTags, addTag, removeTag, clearTags with SSR guards
- `zeues-frontend/__tests__/lib/local-storage.test.ts` - New file: 23 unit tests covering all specified behaviors

## Decisions Made

- snake_case field names in SpoolCardData match backend JSON directly — no camelCase transform needed in API client
- getSpoolStatus and batchGetStatus use handleResponse without extra try/catch wrapping (simpler pattern matches cleaner functions like completarMetrologia, callers handle errors)
- STORAGE_KEY exported as named const so test can assert exact key value and other modules can reference it

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None. The jest CLI flag changed from `--testPathPattern` to `--testPathPatterns` in jest 30 — adapted immediately.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- SpoolCardData, EstadoTrabajo, OperacionActual types ready for Phase 2 components
- getSpoolStatus and batchGetStatus ready for 01-03 useBatchRefresh hook
- loadTags, saveTags, addTag, removeTag ready for 01-02 useSpoolList hook
- tsc --noEmit passes with zero errors, 23 localStorage tests passing

---
*Phase: 01-migration-foundation*
*Completed: 2026-03-10*
