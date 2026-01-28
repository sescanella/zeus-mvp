---
status: resolved
trigger: "fecha-materiales-validation-fail"
created: 2026-01-28T00:00:00Z
updated: 2026-01-28T00:30:00Z
---

## Current Focus

hypothesis: ROOT CAUSE CONFIRMED - parse_date in get_spool_by_tag doesn't support DD-MM-YYYY format used in Google Sheet
test: Verified parse_date implementations across sheets_repository.py
expecting: Fix by adding DD-MM-YYYY format support to get_spool_by_tag's parse_date function
next_action: Apply fix to add DD-MM-YYYY format handling

## Symptoms

expected: User should be able to INICIAR ARM operation on spool TEST-02 because it has Fecha_Materiales = "20-01-2026"
actual: Backend returns error "No se puede iniciar ARM en spool 'TEST-02': falta Fecha_Materiales (El spool debe tener materiales registrados antes de ocuparlo)"
errors:
- Frontend error message: "ERROR: No se puede iniciar ARM en spool 'TEST-02': falta Fecha_Materiales (El spool debe tener materiales registrados antes de ocuparlo)"
- Backend API call to /api/occupation/tomar (POST) returns 400 Bad Request
- Error originates from tomarOcupacion endpoint validation
reproduction:
1. Navigate to frontend confirmation page for ARMADO - INICIAR
2. Select worker MR(93)
3. Select spool TEST-02
4. Click "CONFIRMAR 1 SPOOL"
5. Error appears on confirmation page
started: Recently (after recent code changes in v2.1 development)
context:
- Screenshot 1 shows frontend error on confirmation page
- Screenshot 2 shows Google Sheets row 15 with TEST-02 having Fecha_Materiales = "20-01-2026" in column AH
- This is v2.1 Direct Read architecture (reads state from Operaciones sheet columns directly)
- Only tested with TEST-02 so far, scope unknown for other spools

## Eliminated

## Evidence

- timestamp: 2026-01-28T00:15:00Z
  checked: parse_date function in sheets_repository.py get_spool_by_tag (lines 933-945)
  found: parse_date only supports YYYY-MM-DD and DD/MM/YYYY formats, NOT DD-MM-YYYY
  implication: Date "20-01-2026" from Google Sheet fails to parse, returns None

- timestamp: 2026-01-28T00:16:00Z
  checked: parse_date function in get_spools_for_metrologia (lines 1012-1027)
  found: This version DOES support DD-MM-YYYY format as third fallback
  implication: Inconsistency between parse_date implementations - some functions handle DD-MM-YYYY, others don't

## Resolution

root_cause: parse_date function in get_spool_by_tag (lines 933-945) does not support DD-MM-YYYY date format. Google Sheet has Fecha_Materiales = "20-01-2026" which fails to parse, returning None. Validation then sees fecha_materiales = None and rejects TOMAR operation.

Inconsistency: get_spools_for_metrologia has a more complete parse_date (lines 1012-1027) that DOES support DD-MM-YYYY as third fallback, but get_spool_by_tag and get_all_spools use incomplete versions.

fix: Added DD-MM-YYYY format support to parse_date functions in get_spool_by_tag (line 933) and get_all_spools (line 1117) to match the implementation already present in get_spools_for_metrologia. Now all three functions consistently support YYYY-MM-DD, DD/MM/YYYY, and DD-MM-YYYY date formats.

verification:
- ✅ Code fix applied to 2 parse_date functions in sheets_repository.py
- ✅ Date parsing verified manually: "20-01-2026" successfully parses to date(2026, 1, 20)
- ✅ Backend server restarted to pick up changes
- ⚠️ Full E2E test requires user verification: Navigate to frontend, select worker MR(93), select spool TEST-02, confirm TOMAR operation should now succeed
- Impact: All spools with dates in DD-MM-YYYY format (like "20-01-2026") will now parse correctly instead of returning None

files_changed:
  - backend/repositories/sheets_repository.py: Added DD-MM-YYYY format handling to parse_date in get_spool_by_tag (lines 933-948) and get_all_spools (lines 1117-1131)
