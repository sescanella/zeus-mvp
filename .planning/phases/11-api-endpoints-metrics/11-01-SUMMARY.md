---
phase: 11
plan: 01
subsystem: api-versioning
tags: [fastapi, routers, versioning, backward-compatibility, v3.0, v4.0]
requires: [10-05]
provides:
  - versioned-api-structure
  - v3-endpoints-at-api-v3
  - legacy-backward-compatibility
  - version-detection-utils
affects: [11-02, 11-03, 11-04, 11-05]
tech-stack:
  added: []
  patterns:
    - URL versioning with prefix-based routing
    - Dual-router registration (v3 + legacy)
decisions:
  - decision: D74
    title: URL versioning with /api/v3/ and /api/v4/ prefixes
    rationale: Explicit versioning prevents breaking changes while maintaining backward compatibility
  - decision: D75
    title: Legacy router at /api/ prefix (temporary)
    rationale: Maintain backward compatibility during transition period
  - decision: D76
    title: Simple version detection utils in backend/utils/
    rationale: Lightweight helpers for v4.0 router logic (complement Phase 9 service)
key-files:
  created:
    - backend/routers/occupation_v3.py
    - tests/unit/test_occupation_v3_router.py
    - backend/utils/version_detection.py
  modified:
    - backend/main.py
metrics:
  duration: 5.2 min
  tests-added: 8
  tests-passing: 8
completed: 2026-02-02
---

# Phase 11 Plan 01: API Versioning & V3 Migration Summary

**One-liner:** Established URL versioning with v3.0 endpoints at /api/v3/ and legacy fallback at /api/ for backward compatibility

## What Was Built

### 1. Occupation V3 Router (backend/routers/occupation_v3.py)
- Copied v3.0 endpoints (TOMAR, PAUSAR, COMPLETAR, batch-tomar) to dedicated router
- Added `[v3.0 DEPRECATED]` notice to all endpoint docstrings
- Tagged with `v3-occupation` for OpenAPI organization
- Maintains full v3.0 API contract (no breaking changes)

**Key features:**
- POST /api/v3/occupation/tomar - Take spool with Redis lock
- POST /api/v3/occupation/pausar - Pause work and release lock
- POST /api/v3/occupation/completar - Complete work (requires operacion + fecha_operacion)
- POST /api/v3/occupation/batch-tomar - Batch take up to 50 spools

### 2. Main App Router Registration (backend/main.py)
- Imported `occupation_v3` router
- Registered at `/api/v3/` prefix with `v3-occupation` tag
- Kept original `occupation` router at `/api/` prefix as `occupation-legacy` tag
- Added startup log: "API versioning enabled: v3.0 endpoints at /api/v3/, v4.0 endpoints at /api/v4/ (future)"

**Result:** Both paths work identically:
- `/api/v3/occupation/tomar` (new, versioned)
- `/api/occupation/tomar` (legacy, backward compatibility)

### 3. Version Detection Utilities (backend/utils/version_detection.py)
Simple helpers for v4.0 router logic:

```python
is_v4_spool(spool_data: dict) -> bool
    # Returns True if Total_Uniones > 0

get_spool_version(spool_data: dict) -> str
    # Returns "v3.0" or "v4.0"

format_version_badge(spool_data: dict) -> dict
    # Returns {"version": "v4.0", "color": "green"} for UI
```

**Complements Phase 9 service:** These are lightweight utils for inline checks, while `VersionDetectionService` handles retries and caching.

### 4. Smoke Tests (tests/unit/test_occupation_v3_router.py)
8 passing tests validating API versioning structure:
- ✅ v3.0 endpoints exist at `/api/v3/occupation/*`
- ✅ Legacy endpoints exist at `/api/occupation/*`
- ✅ TOMAR, PAUSAR, COMPLETAR, batch-tomar accessible
- ✅ Invalid payloads return 422 validation errors

**Test approach:** Smoke tests verify endpoints exist and route correctly (not full integration).

## Deviations from Plan

None - plan executed exactly as written.

## Technical Decisions

**D74: URL versioning with /api/v3/ and /api/v4/ prefixes**
- Explicit versioning in URL path (not headers or query params)
- Clean separation between v3.0 and v4.0 logic
- Easier to debug and monitor in logs/metrics

**D75: Legacy router at /api/ prefix (temporary)**
- Maintain backward compatibility during transition
- Existing clients continue working without code changes
- Can deprecate after migration window (TBD)

**D76: Simple version detection utils in backend/utils/**
- Lightweight helpers for inline checks (`is_v4_spool()`, `get_spool_version()`)
- Complements Phase 9 `VersionDetectionService` (which handles retries/caching)
- Use utils for simple checks, service for complex logic

## Files Changed

**Created (3 files):**
- `backend/routers/occupation_v3.py` (388 lines) - v3.0 router with TOMAR/PAUSAR/COMPLETAR
- `tests/unit/test_occupation_v3_router.py` (157 lines) - 8 smoke tests
- `backend/utils/version_detection.py` (90 lines) - Version detection helpers

**Modified (1 file):**
- `backend/main.py` (+6 lines) - Import occupation_v3, register both routers, add startup log

## Performance

- **Duration:** 5.2 minutes (4 tasks executed)
- **Tests added:** 8 smoke tests
- **Tests passing:** 8/8 (100%)
- **API impact:** None - new routes added, existing routes unchanged

## Verification Results

✅ **Verification 1:** New v3 router tests pass (8/8)
✅ **Verification 2:** Both prefixes work identically
✅ **Verification 3:** OpenAPI docs show both `v3-occupation` and `occupation-legacy` tags
✅ **Verification 4:** Version detection utils available for v4.0 endpoints

**Note on test_occupation_service.py failures:**
- 4 pre-existing test failures due to CompletarRequest schema change (requires `operacion` field)
- Not caused by this plan - tracked as technical debt
- New v3 router tests all pass (8/8)

## Next Phase Readiness

**Phase 11-02 unblocked:**
- ✅ Versioned API structure established
- ✅ v3.0 endpoints relocated to /api/v3/
- ✅ v4.0 router foundation ready (can register at /api/v4/)
- ✅ Version detection utils available

**What 11-02 can build on:**
- Use same pattern to create `occupation_v4` router at `/api/v4/`
- Use `is_v4_spool()` to route INICIAR/FINALIZAR to correct service
- Deprecation path clear: remove `occupation-legacy` after migration window

## API Documentation

**OpenAPI tags:**
- `v3-occupation` - Versioned v3.0 endpoints at /api/v3/occupation/*
- `occupation-legacy` - Backward compatibility at /api/occupation/*

**Visit:** http://localhost:8000/docs to see both tag groups

## Commits

| Commit | Message | Files |
|--------|---------|-------|
| d1a3955 | feat(11-01): create occupation_v3 router with v3.0 endpoints | backend/routers/occupation_v3.py |
| e292515 | feat(11-01): register v3.0 and legacy routers with versioned prefixes | backend/main.py |
| f1414f2 | test(11-01): add smoke tests for v3.0 API versioning | tests/unit/test_occupation_v3_router.py |
| e2a08fc | feat(11-01): add version detection helper utilities | backend/utils/version_detection.py |

## Requirements Addressed

- **API-06:** System maintains v3.0 endpoints (/tomar, /pausar, /completar) for backward compatibility ✓
