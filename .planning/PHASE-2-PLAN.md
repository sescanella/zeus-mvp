# Phase 2: Legacy Code Removal - Execution Plan

**Created:** 2026-02-07
**Estimated Effort:** 1 day (8 hours)
**Risk Level:** MEDIUM (requires careful validation)
**LOC Reduction Target:** ~2,870 LOC

---

## Overview

Phase 2 removes obsolete v2.1 and v3.0 code paths that have been replaced by v4.0.

**Key Principle:** The frontend uses BOTH v3.0 (`/api/occupation/*`) and v4.0 (`/api/v4/occupation/*`) endpoints. We need to:
1. Keep v3.0 endpoints that frontend actively uses
2. Remove only truly dead v2.1 code (`action_service.py`, `/api/iniciar-accion`)
3. Clean up Redis references (single-user mode)

---

## Task Breakdown

### Task 2.1: Remove v2.1 ActionService (1,096 LOC)

**Status:** Safe to delete
**Files:**
- `backend/services/action_service.py` (1,096 LOC) - DELETE
- `backend/routers/actions.py` (986 LOC) - REVIEW (may contain reparacion endpoints)

**Verification:**
```bash
# Check if frontend calls v2.1 endpoints
grep -r "iniciar-accion" zeues-frontend/app/ zeues-frontend/lib/
# Expected: 0 matches in active code (only in docs)
```

**Dependencies to check:**
- `backend/routers/actions.py` imports from action_service
- `backend/core/dependency.py` may inject action_service

---

### Task 2.2: Evaluate v3.0 Occupation Router (387 LOC)

**Status:** ⚠️ CANNOT DELETE - Frontend uses these endpoints

**Evidence:**
```
zeues-frontend/lib/api.ts:616:    fetch(`${API_URL}/api/occupation/tomar`
zeues-frontend/lib/api.ts:679:    fetch(`${API_URL}/api/occupation/pausar`
zeues-frontend/lib/api.ts:743:    fetch(`${API_URL}/api/occupation/completar`
zeues-frontend/app/confirmar/page.tsx uses tomarOcupacion, pausarOcupacion, completarOcupacion
```

**Decision:** KEEP `backend/routers/occupation.py`
**Action:** Add deprecation notice in docstrings for future removal

---

### Task 2.3: Clean Redis References (~150 LOC)

**Files with Redis references:**
1. `backend/services/occupation_service.py` - Comments only
2. `backend/routers/health.py` - Health check references
3. `backend/requirements.txt` - Redis dependency (if exists)

**Actions:**
- Remove dead Redis lock comments
- Remove Redis from requirements.txt (if not used)
- Clean up health check Redis references

---

### Task 2.4: Archive Unused Frontend API Functions

**Already Done in Phase 1:**
- ✅ `checkHealth()` removed
- ✅ `getWorkerRoles()` removed

**Remaining - v3.0 functions to KEEP:**
- `tomarOcupacion()` - Used by confirmar/page.tsx
- `pausarOcupacion()` - Used by confirmar/page.tsx
- `completarOcupacion()` - Used by confirmar/page.tsx
- `tomarOcupacionBatch()` - May still be used

---

### Task 2.5: Merge SpoolService + SpoolServiceV2 (Optional - 250 LOC)

**Status:** DEFER to Phase 3
**Reason:** Service layer refactor has higher risk, requires more testing

---

## Execution Order

```
┌─────────────────────────────────────────────────────────────┐
│  Task 2.1: Remove action_service.py                        │
│  - Delete backend/services/action_service.py               │
│  - Update imports in actions.py router                     │
│  - Run unit tests                                          │
├─────────────────────────────────────────────────────────────┤
│  Task 2.3: Clean Redis References                          │
│  - Remove dead comments                                    │
│  - Update requirements.txt                                 │
│  - Clean health.py references                              │
├─────────────────────────────────────────────────────────────┤
│  Validation                                                 │
│  - pytest tests/unit/ tests/integration/                   │
│  - Frontend build: npm run build                           │
│  - TypeScript check: npx tsc --noEmit                      │
└─────────────────────────────────────────────────────────────┘
```

---

## Revised LOC Reduction

| Task | LOC | Status |
|------|-----|--------|
| 2.1 Remove action_service.py | 1,096 | ✅ Safe |
| 2.2 Remove occupation.py | ~~387~~ | ❌ KEEP (frontend uses) |
| 2.3 Clean Redis refs | ~150 | ✅ Safe |
| 2.4 Frontend cleanup | N/A | ✅ Done in Phase 1 |
| 2.5 Merge SpoolServices | ~~250~~ | ⏸️ Defer |
| **Total Phase 2** | **~1,246** | |

---

## Risk Mitigation

### Pre-Execution Checks

1. **Verify action_service is unused:**
   ```bash
   grep -r "action_service" backend/routers/ backend/core/
   grep -r "ActionService" backend/
   ```

2. **Verify actions.py structure:**
   ```bash
   # Check what endpoints are in actions.py
   grep -E "^@router\.(get|post)" backend/routers/actions.py
   ```

3. **Verify Redis is truly unused:**
   ```bash
   grep -r "import redis" backend/
   grep -r "from redis" backend/
   ```

### Rollback Plan

```bash
# If issues found after Phase 2:
git revert HEAD  # Undo Phase 2 commit
git push origin main --force-with-lease
railway up  # Redeploy
```

---

## Validation Checklist

After Phase 2, ALL must pass:

```bash
# Backend tests
source venv/bin/activate
PYTHONPATH=/Users/sescanella/Proyectos/KM/ZEUES-by-KM pytest tests/unit/ -v --tb=short

# Frontend
cd zeues-frontend
npx tsc --noEmit
npm run lint
npm run build

# Smoke test (if running locally)
curl http://localhost:8000/api/health
# Expected: {"status": "healthy"}
```

---

## Agent Team for Phase 2

**Recommended:** 2 parallel agents

### Agent 2.1: Backend Legacy Cleanup
- Focus: Remove action_service.py
- Verify: No import errors
- Test: Run unit tests

### Agent 2.2: Redis/Comments Cleanup
- Focus: Remove Redis references
- Verify: requirements.txt updated
- Test: Health endpoint works

---

## Next Steps

1. ✅ Review this plan
2. Create tasks for Phase 2
3. Execute Task 2.1 (action_service.py removal)
4. Execute Task 2.3 (Redis cleanup)
5. Validate and commit
6. Proceed to Phase 3 (Frontend Refactoring) or Phase 4 (API Optimization)

---

**Author:** Claude Code
**Phase 1 Status:** ✅ Completed (17,973 LOC archived/deleted)
**Phase 2 Status:** 📋 Planned
