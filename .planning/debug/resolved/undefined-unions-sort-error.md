---
status: resolved
trigger: "undefined-unions-sort-error"
created: 2026-02-03T00:00:00Z
updated: 2026-02-03T00:08:00Z
---

## Current Focus

hypothesis: CONFIRMED - Field name mismatch between backend (English 'unions') and frontend (Spanish 'uniones')
test: Fix frontend to use correct field name 'unions'
expecting: Page will load unions successfully
next_action: Fix frontend code to access response.unions instead of response.uniones

## Symptoms

expected:
- After selecting TEST-02 spool in INICIAR workflow
- Union selection page should fetch unions for TEST-02 from backend
- Display list of available unions with checkboxes
- Show count like "Seleccionadas: 0/5 | Pulgadas: 0.0"
- User can select unions and click "Reintentar" button

actual:
- Page loads with correct title "Seleccionar Uniones - TEST-02"
- Shows "Seleccionadas: 0/0 | Pulgadas: 0.0" (0 total unions)
- Red error message: "Cannot read properties of undefined (reading 'sort')"
- Console shows: Error fetching unions: TypeError: Cannot read properties of undefined (reading 'sort')
  at page-abb6fabe0fd8c8e1c.js:13987
- No unions displayed in UI
- "Reintentar" button is present but disabled

errors:
```
Error fetching unions: TypeError: Cannot read properties of undefined (reading 'sort')
  at page-abb6fabe0fd8c8e1c.js:13987
```

reproduction:
1. Navigate to app
2. Select ARM operation
3. Select worker Mauricio Rodríguez
4. Click "Iniciar" (INICIAR workflow)
5. Select TEST-02 spool (v4.0)
6. Click "Continuar"
7. Observe: Union selection page loads but shows error and 0/0 unions

started: Just fixed navigation to reach this page (commit 96636d9)

## Eliminated

## Evidence

- timestamp: 2026-02-03T00:01:00Z
  checked: zeues-frontend/app/seleccionar-uniones/page.tsx line 69
  found: `const sorted = response.uniones.sort(...)` - calling .sort() on response.uniones without null check
  implication: If API returns malformed response (missing 'uniones' property), this will throw "Cannot read properties of undefined (reading 'sort')"

- timestamp: 2026-02-03T00:02:00Z
  checked: zeues-frontend/lib/api.ts lines 1405-1431 (getDisponiblesUnions function)
  found: Function expects DisponiblesResponse type with 'uniones' property. Uses handleResponse helper which can throw on non-ok status
  implication: API call may be failing (returning error) OR backend not returning expected structure

- timestamp: 2026-02-03T00:03:00Z
  checked: backend/routers/union_router.py line 108
  found: Backend returns `DisponiblesResponse(unions=union_summaries)` - uses English field name 'unions'
  implication: Backend uses 'unions' (English) but frontend expects 'uniones' (Spanish)

- timestamp: 2026-02-03T00:04:00Z
  checked: backend/models/union_api.py line 55
  found: `unions: List[UnionSummary]` - Pydantic model defines English field name
  implication: Backend schema is correct (English). Frontend is incorrect (Spanish)

- timestamp: 2026-02-03T00:05:00Z
  checked: zeues-frontend/lib/types.ts line 254
  found: TypeScript interface defines `uniones: Union[]` (Spanish)
  implication: TypeScript type definition is out of sync with backend Pydantic model

## Resolution

root_cause: Field name mismatch between backend and frontend. Backend returns 'unions' (English) in DisponiblesResponse, but frontend TypeScript types and code expect 'uniones' (Spanish). When frontend tries to access response.uniones, it gets undefined, then calling .sort() on undefined causes TypeError.

fix: Updated frontend to use English field name 'unions' to match backend Pydantic model. Applied two changes:
1. zeues-frontend/lib/types.ts: Changed DisponiblesResponse interface from 'uniones' to 'unions' and from 'disponibles_count' to 'count'
2. zeues-frontend/app/seleccionar-uniones/page.tsx: Changed response.uniones.sort() to response.unions.sort()

verification:
- TypeScript compilation: PASSED (npx tsc --noEmit - no errors)
- Production build: PASSED (npm run build - completed successfully)
- Field names now match backend schema exactly (unions/count vs uniones/disponibles_count)
- No other references to old field names found in codebase
- Fix is minimal and targeted - only updated type definition and one line of code

files_changed:
- zeues-frontend/lib/types.ts
- zeues-frontend/app/seleccionar-uniones/page.tsx
