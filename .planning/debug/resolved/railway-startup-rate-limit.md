---
status: resolved
trigger: "railway-startup-rate-limit"
created: 2026-02-04T00:00:00Z
updated: 2026-02-04T01:10:00Z
---

## Current Focus

hypothesis: VERIFIED - Both fixes applied, deployment successful
test: Railway health check returns 200 OK
expecting: Backend fully operational
next_action: Archive debug session

## Symptoms

expected: Backend should start successfully in Railway and respond to health checks
actual: Backend fails to start with 502 error, logs show Google Sheets API rate limit (429) during schema validation
errors:
```
APIError: [429]: Quota exceeded for quota metric 'Read requests' and limit 'Read requests per minute per user' of service 'sheets.googleapis.com' for consumer 'project_number:772156205077'.
[ERROR] [backend.scripts.validate_schema_startup] v4.0 schema validation: FAILED
  Operaciones: 14 missing columns
  Uniones: 18 missing columns
  Metadata: 11 missing columns (FAIL)
```
reproduction:
1. Push code to main branch
2. Railway auto-deploys
3. FastAPI startup runs validate_schema_startup.py
4. Schema validation makes multiple Google Sheets API reads
5. Exceeds 60 reads/minute quota
6. Application fails to start

started: After push commit 12225aa (removed audit fields from Union model)
timeline: Previous deploys worked fine, issue appeared after Union model schema change

## Eliminated

- hypothesis: Rate limit was the only issue
  evidence: Deployment still failed after rate limit fix, error showed "14 missing columns" in Operaciones
  timestamp: 2026-02-04T00:45:00Z

## Evidence

- timestamp: 2026-02-04T00:05:00Z
  checked: validate_schema_startup.py code flow
  found: Script validates 3 sheets (Operaciones, Uniones, Metadata) sequentially
  implication: Each validation calls ColumnMapCache.get_or_build() which calls sheets_repo.read_worksheet()

- timestamp: 2026-02-04T00:07:00Z
  checked: ColumnMapCache.get_or_build() implementation in backend/core/column_map_cache.py
  found: Line 87 calls sheets_repository.read_worksheet(sheet_name) which internally calls worksheet.get_all_values()
  implication: Each sheet validation = 1 Google Sheets API read call

- timestamp: 2026-02-04T00:09:00Z
  checked: main.py startup event (lines 259-398)
  found: Startup sequence performs MULTIPLE Google Sheets reads before schema validation:
    1. Line 326: Pre-warm Operaciones cache (1 API call)
    2. Line 291: Redis reconciliation reads Operaciones sheet (1 API call)
    3. Lines 362-365: validate_v4_schema() reads 3 sheets (3 API calls)
  implication: Total of 5+ Google Sheets API calls during startup, likely hitting 60 reads/min quota

- timestamp: 2026-02-04T00:11:00Z
  checked: Railway deployment context
  found: Railway may restart containers multiple times during deployment (health checks, retries)
  implication: If Railway restarts 3 times in 1 minute, that's 15+ API calls → exceeds quota

- timestamp: 2026-02-04T00:15:00Z
  checked: SheetsRepository.read_worksheet() caching (lines 157-206)
  found: Has in-memory TTL cache, but cache is instance-based and cleared on startup
  implication: Cache does NOT survive across startup sequences - each startup reads fresh from API

- timestamp: 2026-02-04T00:17:00Z
  checked: Startup API call count in main.py (lines 259-398)
  found: CONFIRMED API call sequence during startup:
    1. Redis reconciliation: get_all_spools() → reads Operaciones (1 API call)
    2. Pre-warm cache: ColumnMapCache for Operaciones (DUPLICATE READ - 2nd API call)
    3. Schema validation: validate_v4_schema() reads Operaciones AGAIN (3rd API call)
    4. Schema validation: reads Uniones (4th API call)
    5. Schema validation: reads Metadata (5th API call)
    TOTAL: 5 API calls per startup
  implication: Operaciones sheet is read 3 TIMES redundantly during startup!

- timestamp: 2026-02-04T00:20:00Z
  checked: SheetsRepository singleton behavior (dependency.py lines 72-96)
  found: get_sheets_repository() IS a singleton with cache, BUT cache is in-memory and cleared on container restart
  implication: Cache cannot help across Railway container restarts

- timestamp: 2026-02-04T00:22:00Z
  checked: Cache sharing between startup steps
  found: All three startup steps (Redis reconciliation, pre-warm, schema validation) call get_sheets_repository() which returns SAME singleton instance with SAME cache
  implication: Cache SHOULD work! Second and third reads should be cache hits. Why aren't they?

- timestamp: 2026-02-04T00:25:00Z
  checked: validate_v4_schema() implementation (lines 162-329 in validate_schema_startup.py)
  found: Line 209 creates NEW SheetsRepository() if repo is None, bypassing dependency injection singleton!
  implication: Schema validation creates its OWN repository instance with EMPTY cache, causing redundant API calls

- timestamp: 2026-02-04T00:50:00Z
  checked: Deployment logs after first fix
  found: Still failing with 502, suggesting schema validation failure not just rate limit
  implication: Two separate bugs: rate limit AND schema mismatch

- timestamp: 2026-02-04T00:55:00Z
  checked: UNIONES_V4_COLUMNS vs mock_uniones_data.py
  found: Validation script expected 18 columns (with audit fields), but commit 12225aa reduced to 17 columns
  implication: Schema validation was checking for removed audit fields, causing false failure

- timestamp: 2026-02-04T01:00:00Z
  checked: mock_uniones_data.py actual structure
  found: 17 columns: ID, OT, N_UNION, TAG_SPOOL, DN_UNION, TIPO_UNION, ARM×3, SOLD×3, NDT×4, version
  implication: Validation script missed OT column and had wrong NDT field names

## Resolution

root_cause: TWO bugs causing Railway startup failure:

1. **Rate limit bug**: validate_schema_startup.py creates NEW SheetsRepository() at line 209, bypassing singleton and losing cached data. This causes redundant reads (5 API calls per startup), hitting 60 reads/min quota when Railway restarts containers.

2. **Schema mismatch bug**: UNIONES_V4_COLUMNS validation list was outdated after commit 12225aa removed audit fields. Expected 18 columns (with audit fields) but actual sheet has 17 columns. Also missing OT column and had wrong NDT field names.

fix:
1. Modified main.py line 365-367 to pass singleton sheets_repo to validate_v4_schema(repo=sheets_repo)
2. Updated UNIONES_V4_COLUMNS to match actual 17-column structure from mock_uniones_data.py

Impact:
  - Rate limit: Reduces API calls from 5 to 3 per startup (40% reduction)
  - Schema validation: Now validates correct 17 columns instead of failing on removed audit fields

verification: ✅ PASSED
  - Committed fixes:
    - Commit 0bb9dbd: Rate limit fix (singleton repo sharing)
    - Commit 7ebdf1e: Schema validation fix (17-column Uniones)
  - Deployed to Railway: 2026-02-04 01:05:00Z
  - Health check: https://zeues-backend-mvp-production.up.railway.app/api/health
    - Status: 200 OK
    - Response: {"status":"healthy","operational":true}
    - Sheets connection: ok
    - Redis connection: ok
  - Startup logs confirmed:
    ✅ No 429 rate limit errors
    ✅ Schema validation passed for all 3 sheets
    ✅ Backend responsive to requests

files_changed:
  - backend/main.py: Pass singleton sheets_repo to validate_v4_schema()
  - backend/scripts/validate_schema_startup.py: Fix UNIONES_V4_COLUMNS to match 17-column structure

root_cause:
fix:
verification:
files_changed: []
