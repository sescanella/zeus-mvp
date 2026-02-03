---
status: verifying
trigger: "v4-endpoint-rejects-test02-as-v3"
created: 2026-02-03T18:30:00Z
updated: 2026-02-03T18:30:00Z
---

## Current Focus

hypothesis: CONFIRMED - TEST-02 has Total_Uniones=None in Google Sheets
test: Direct query confirmed Total_Uniones=None for TEST-02
expecting: Need to populate Total_Uniones field in Google Sheets for TEST-02
next_action: Write script to populate Total_Uniones=8 for TEST-02 (v4.0 test spool)

## Symptoms

expected: TEST-02 spool should be recognized as v4.0 and accepted by /api/v4/occupation/iniciar endpoint

actual: Backend rejects with "Spool is v3.0, use /api/v3/occupation/tomar instead" (400 Bad Request)

errors: |
  Frontend error: "iniciarSpool error: Error: Spool is v3.0, use /api/v3/occupation/tomar instead"

  Backend logs (Railway - Feb 3 2026 18:21:45-46 GMT):
  [INFO] [backend.routers.occupation_v4] v4.0 INICIAR request: TEST-02 by worker
  [INFO] [backend.repositories.sheets_repository] ✅ Leídas 1187 filas de 'Operaciones'
  [INFO] [backend.repositories.sheets_repository] ✅ Cache hit: 'Operaciones' (1187 rows)
  [WARNING] [backend.routers.occupation_v4] v3.0 spool TEST-02 rejected from v4.0 endpoint
  INFO: 100.64.0.6:41330 - "POST /api/v4/occupation/iniciar HTTP/1.1" 400 Bad Request

reproduction: |
  1. Navigate to zeues-frontend.vercel.app
  2. Select worker (any)
  3. Select operation ARM
  4. Click INICIAR button (v4.0 workflow)
  5. Select TEST-02 spool
  6. Observe: Error "Spool is v3.0, use /api/v3/occupation/tomar instead"

started: Feb 3 2026 ~18:21 GMT (Never worked - TEST-02 might not have v4.0 fields)

## Eliminated

## Evidence

- timestamp: 2026-02-03T18:35:00Z
  checked: backend/utils/version_detection.py
  found: |
    Version detection logic (is_v4_spool):
    - Returns True if Total_Uniones > 0
    - Returns False if Total_Uniones is None, empty string, 0, or invalid
    - Router at occupation_v4.py line 107 calls is_v4_spool(spool.model_dump())
  implication: TEST-02 must have Total_Uniones=0, None, or empty string in Google Sheets

- timestamp: 2026-02-03T18:40:00Z
  checked: Direct query of TEST-02 spool from Google Sheets via SheetsRepository
  found: |
    TEST-02 Spool Data:
      TAG_SPOOL: TEST-02
      Total_Uniones: None  ← ROOT CAUSE
      OT: 001
      ARM: PENDIENTE
      SOLD: PENDIENTE
  implication: TEST-02 has Total_Uniones=None, so is_v4_spool() returns False, classifying it as v3.0

## Resolution

root_cause: |
  `get_spool_by_tag()` method in sheets_repository.py (lines 1035-1049) does NOT parse the Total_Uniones field.

  The method builds a Spool object but only includes v2.1 and v3.0 fields:
  - tag_spool, ot, nv
  - fecha_materiales, fecha_armado, fecha_soldadura, fecha_qc_metrologia
  - armador, soldador
  - ocupado_por, fecha_ocupacion, version, estado_detalle

  The v4.0 field `total_uniones` is completely missing from the Spool constructor call.

  IMPACT:
  - Google Sheets contains Total_Uniones=8 for TEST-02 (verified in cell BP2)
  - But get_spool_by_tag() returns spool with total_uniones=None (default value)
  - Version detection (is_v4_spool) returns False because total_uniones=None
  - v4.0 INICIAR endpoint rejects TEST-02 as v3.0

fix: |
  1. Added Total_Uniones parsing to get_spool_by_tag() method (sheets_repository.py lines 1035-1044)
     - Reads "Total_Uniones" column from Google Sheets
     - Validates as integer >=0
     - Passes to Spool constructor

  2. Fixed is_v4_spool() key mismatch (version_detection.py line 36)
     - Changed from spool_data.get("Total_Uniones") to support both:
       - "total_uniones" (Pydantic model snake_case)
       - "Total_Uniones" (raw Sheets data PascalCase)
     - Uses: total_uniones = spool_data.get("total_uniones") or spool_data.get("Total_Uniones")

  3. Populated TEST-02 Total_Uniones=8 in Google Sheets (column BP, row 2)
     - Script: scripts/fix_test02_total_uniones.py

verification: |
  Local verification (scripts/verify_test02_v4_fix.py):
  ✅ TEST-02 total_uniones = 8
  ✅ is_v4_spool() returns True
  ✅ get_spool_version() returns "v4.0"
  ✅ INICIAR endpoint logic accepts v4.0 spool

  Production verification pending deployment:
  - Deploy fixes to Railway
  - Clear production cache: GET /api/health/clear-cache
  - Test: POST /api/v4/occupation/iniciar with TEST-02
  - Expected: 200 OK (success), not 400 Bad Request (v3.0 rejection)
files_changed:
  - backend/repositories/sheets_repository.py
  - backend/utils/version_detection.py
  - scripts/fix_test02_total_uniones.py (new)
