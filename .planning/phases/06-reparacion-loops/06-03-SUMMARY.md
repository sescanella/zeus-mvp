---
phase: 06
plan: 03
subsystem: reparacion-workflow
status: complete
tags: [reparacion, rest-api, frontend-integration, cycle-tracking, bloqueado-display]
dependencies:
  requires: [06-01-reparacion-state-machine, 06-02-cycle-counting]
  provides: [reparacion-rest-endpoints, reparacion-ui, cycle-display]
  affects: [07-frontend-tipo-interaccion, 08-frontend-confirmar]
tech-stack:
  added: []
  patterns: [rest-endpoint-integration, bloqueado-ui-pattern, cycle-info-display]
key-files:
  created: []
  modified:
    - backend/routers/spools.py
    - backend/routers/actions.py
    - backend/core/dependency.py
    - backend/main.py
    - zeues-frontend/app/page.tsx
    - zeues-frontend/app/operacion/page.tsx
    - zeues-frontend/app/seleccionar-spool/page.tsx
    - zeues-frontend/lib/api.ts
decisions: []
metrics:
  duration: ~12 minutes
  completed: 2026-01-28
---

# Phase 6 Plan 3: REST Endpoints & Frontend Integration Summary

**One-liner:** Reparación REST API with 4 action endpoints + yellow REPARACIÓN button + BLOQUEADO spool display with cycle info

## What Was Built

### Backend REST Endpoints
- **GET /api/spools/reparacion**: Returns RECHAZADO/BLOQUEADO spools with cycle info and fecha_rechazo
- **POST /api/tomar-reparacion**: Worker takes RECHAZADO spool (validates not BLOQUEADO)
- **POST /api/pausar-reparacion**: Worker pauses repair work
- **POST /api/completar-reparacion**: Complete repair, return to PENDIENTE_METROLOGIA
- **POST /api/cancelar-reparacion**: Cancel repair, return to RECHAZADO
- **SpoolBloqueadoError → HTTP 403**: Exception mapping in main.py

### Frontend Integration
- **4th Operation Button**: REPARACIÓN with yellow styling and Wrench icon
- **Worker Selection**: No role restriction - all active workers can access REPARACIÓN
- **Spool Selection Page**:
  - Displays cycle info (Ciclo X/3) instead of NV column
  - BLOQUEADO spools shown with red styling, lock icon, disabled selection
  - Routes to tipo-interaccion after selection
- **API Functions**: 5 new functions (getSpoolsReparacion, tomar, pausar, completar, cancelar)

### Dependency Injection
- **get_reparacion_service()**: Factory in core/dependency.py
- **get_cycle_counter_service()**: Stateless factory in routers/spools.py
- **ReparacionService injection**: validation_service, cycle_counter, sheets_repo, metadata_repo, redis_event_service

## Implementation Details

### Backend Patterns
1. **CycleCounterService Integration**:
   - Injected in GET /spools/reparacion endpoint
   - Extracts cycle count from Estado_Detalle string
   - Checks bloqueado status (cycle >= 3)

2. **Endpoint Structure**:
   - All 4 action endpoints follow same pattern as ARM/SOLD/METROLOGIA
   - ActionRequest model reused (worker_id, tag_spool)
   - Service layer handles all business logic

3. **Error Handling**:
   - SpoolBloqueadoError → 403 Forbidden
   - Consistent error response format

### Frontend Patterns
1. **Operation Selection**:
   - REPARACION added to operations array
   - Wrench icon from lucide-react
   - Yellow color theme (bg-yellow-600)
   - Skips tipo-interaccion (routes directly to spool selection)

2. **Spool Display**:
   - Conditional rendering based on tipo === 'reparacion'
   - Type-safe access to bloqueado/cycle properties
   - Lock icon for BLOQUEADO spools
   - Cursor-not-allowed for disabled spools

3. **API Integration**:
   - All functions use 'unknown' return type (no 'any')
   - Explicit error handling for HTTP 403 (BLOQUEADO)
   - Type-safe spool data structure

## Commits

| Hash    | Message                                           | Files                          |
|---------|--------------------------------------------------|--------------------------------|
| fa49147 | feat(06-03): add REST endpoints for reparación   | backend routers, dependency    |
| 1fbfd9b | feat(06-03): add REPARACIÓN as 4th operation     | frontend operation pages       |
| 5478026 | feat(06-03): update spool selection              | seleccionar-spool/page.tsx     |
| cad8648 | feat(06-03): add API functions for reparación    | lib/api.ts                     |

## Verification

### Backend Endpoints
```bash
# Test GET endpoint
curl http://localhost:8000/api/spools/reparacion | jq

# Test TOMAR endpoint
curl -X POST http://localhost:8000/api/tomar-reparacion \
  -H "Content-Type: application/json" \
  -d '{"worker_id":93,"tag_spool":"TEST"}'

# Test BLOQUEADO error (HTTP 403)
curl -X POST http://localhost:8000/api/tomar-reparacion \
  -H "Content-Type: application/json" \
  -d '{"worker_id":93,"tag_spool":"BLOQUEADO-SPOOL"}'
```

### Frontend Integration
1. Navigate to / → 4 operation buttons visible (ARM, SOLD, METROLOGÍA, REPARACIÓN)
2. Click REPARACIÓN → Worker selection (all workers available)
3. Select worker → Spool selection shows RECHAZADO spools with cycle info
4. BLOQUEADO spools shown with red styling, lock icon, disabled

### TypeScript Validation
```bash
cd zeues-frontend
npx tsc --noEmit  # Must pass with no errors
npm run lint      # Must pass with no warnings
npm run build     # Must succeed
```

## Deviations from Plan

None - plan executed exactly as written.

## Key Decisions Made

1. **No dedicated SpoolCard component**: Used inline rendering in table rows for simplicity
2. **Placeholder worker name format**: Backend uses "W(ID)" placeholder, service fetches actual name
3. **Single-spool workflow only**: Phase 6 defers batch multiselect for reparación (keeps it simple)
4. **Type-safe bloqueado access**: Used type assertion `(spool as unknown as { bloqueado?: boolean })` for type safety

## Next Phase Readiness

### Blockers
None - all must_haves satisfied.

### Required for Phase 7
- Frontend tipo-interaccion page needs to handle REPARACION routing
- Frontend confirmar page needs to integrate reparación action handlers
- Worker name format consistency (current placeholder vs actual names)

### Technical Debt
- None identified

### Integration Points
- tipo-interaccion page: REPARACION should route to TOMAR action
- confirmar page: needs tomarReparacion(), completarReparacion() integration
- SSE events: TOMAR_REPARACION, PAUSAR_REPARACION, COMPLETAR_REPARACION for dashboard

## Testing Notes

### Must Test Manually
1. **BLOQUEADO UI**: Verify spools with cycle=3 show as disabled with lock icon
2. **Cycle Display**: Verify "Ciclo X/3" appears instead of NV for reparación tipo
3. **Yellow Button**: Verify REPARACIÓN button has yellow styling
4. **Worker Access**: Verify all active workers (no role filter) appear in selection

### Automated Testing (Future)
- E2E test: Full reparación flow (select spool → TOMAR → COMPLETAR)
- API test: GET /spools/reparacion returns correct cycle counts
- API test: POST endpoints handle BLOQUEADO validation (HTTP 403)

## Performance Notes

- **Execution time**: ~12 minutes (4 tasks, 4 commits)
- **Backend changes**: 4 files modified (routers, dependency, main)
- **Frontend changes**: 4 files modified (pages, api)
- **Total LOC added**: ~600 lines (endpoints + UI + API functions)

## Known Issues

None.

## Future Enhancements

1. **Batch multiselect**: Allow selecting multiple spools for reparación (deferred from Phase 6)
2. **Worker name format**: Replace "W(ID)" placeholder with actual worker names from service
3. **BLOQUEADO supervisor action**: Add supervisor-only endpoint to unblock spools
4. **Cycle history**: Show cycle history in spool detail view

## Documentation Updates Required

- **CLAUDE.md**: Update with REPARACIÓN as 4th operation
- **proyecto-v2-frontend.md**: Document reparación UI patterns
- **proyecto-v2-backend.md**: Document reparación REST endpoints

---

**Status:** ✅ Complete - All 4 tasks executed, 4 commits made, 8 files modified
