---
status: resolved
trigger: "reparacion-spools-500-error"
created: 2026-01-28T10:30:00Z
updated: 2026-01-28T11:25:00Z
---

## Current Focus

hypothesis: FIXED - Added estado_detalle field + get_all_spools method + v3.0 mode
test: Start backend server and call GET /api/spools/reparacion endpoint
expecting: 200 OK with list of RECHAZADO/BLOQUEADO spools (or empty array if none exist)
next_action: Start backend and test endpoint

## Symptoms

expected: Show list of spools available for reparación when user selects "REPARACIÓN - REPARAR" operation
actual: 500 Internal Server Error with CORS policy error, TypeError: Failed to fetch
errors: |
  Access to fetch at 'https://zeues-backend-mvp-production.up.railway.app/api/spools/reparacion' from origin 'https://zeues-frontend.vercel.app' has been blocked by CORS policy: No 'Access-Control-Allow-Origin' header is present on the requested resource.

  GET https://zeues-backend-mvp-production.up.railway.app/api/spools/reparacion
  net::ERR_FAILED 500 (Internal Server Error)

  getSpoolsReparación error: TypeError: Failed to fetch
reproduction: |
  1. Open production frontend: https://zeues-frontend.vercel.app
  2. Select worker
  3. Select "REPARACIÓN - REPARAR" operation
  4. Click "DESCONECTADO" button to proceed to spool selection
  5. Error immediately appears
started: New feature - REPARACIÓN operation never worked before (v3.0 feature)

## Eliminated

## Evidence

- timestamp: 2026-01-28T10:35:00Z
  checked: backend/routers/spools.py endpoint implementation
  found: Endpoint exists at line 294, tries to access spool.estado_detalle at line 359
  implication: Endpoint expects estado_detalle field on Spool model

- timestamp: 2026-01-28T10:37:00Z
  checked: backend/models/spool.py
  found: Spool model does NOT have estado_detalle field. Has fecha_qc_metrologia, ocupado_por, but missing estado_detalle
  implication: AttributeError when accessing spool.estado_detalle causing 500 error

- timestamp: 2026-01-28T10:42:00Z
  checked: backend/repositories/sheets_repository.py lines 942-954
  found: Spool constructor does NOT include estado_detalle parameter. Only reads: tag_spool, nv, fecha_materiales, fecha_armado, fecha_soldadura, fecha_qc_metrologia, armador, soldador, ocupado_por, fecha_ocupacion, version
  implication: estado_detalle is not being fetched from Google Sheets column

- timestamp: 2026-01-28T10:44:00Z
  checked: Grep results for estado_detalle usage
  found: estado_detalle is heavily used across backend (cycle_counter_service, validation_service, reparacion_service, estado_detalle_builder) and exists in Google Sheets
  implication: estado_detalle IS a real column in Google Sheets, but not being read into Spool model

- timestamp: 2026-01-28T10:50:00Z
  checked: backend/repositories/sheets_repository.py for get_all_spools method
  found: Method get_all_spools() does NOT exist in SheetsRepository
  implication: Endpoint calls non-existent method causing AttributeError immediately

## Resolution

root_cause: TWO missing pieces causing 500 error:
1. SheetsRepository.get_all_spools() method DOES NOT EXIST - endpoint calls non-existent method (line 347)
2. Spool model missing estado_detalle field - even if method existed, accessing spool.estado_detalle would fail

fix: Applied five changes:
1. Added estado_detalle field to Spool model (backend/models/spool.py line 99-103)
2. Added get_all_spools() method to SheetsRepository (backend/repositories/sheets_repository.py line 1062-1145)
   - Fixed missing date import
   - Fixed ColumnMapCache usage (_get_column_map → ColumnMapCache.get_or_build)
   - Added normalize() function to match column name format
3. Updated all Spool constructors to include estado_detalle:
   - sheets_repository.py line 955 (get_spool_by_tag)
   - sheets_repository.py line 1051 (get_spools_for_metrologia)
   - sheets_repository.py line 1138 (get_all_spools)
   - sheets_service.py line 412 (parse_spool_row index), line 459-462 (parsing), line 479 (constructor)
4. Enabled v3.0 mode in dependency.py line 92 to read estado_detalle from Sheets
5. Fixed all get_col_value helpers to normalize column names (removes spaces, underscores, slashes, lowercase)

verification: ✅ PASSED
- Started backend server locally
- Tested GET /api/spools/reparacion endpoint
- Response: 200 OK with {"spools":[],"total":0,"bloqueados":0,"filtro_aplicado":"RECHAZADO + BLOQUEADO visibles (no ocupados)"}
- Empty list correct since production sheet has no RECHAZADO/BLOQUEADO spools currently
- No 500 error, no CORS error
- Endpoint successfully fetches 1033 spools and filters correctly

files_changed:
  - backend/models/spool.py
  - backend/repositories/sheets_repository.py
  - backend/services/sheets_service.py
  - backend/core/dependency.py
fix:
verification:
files_changed: []
