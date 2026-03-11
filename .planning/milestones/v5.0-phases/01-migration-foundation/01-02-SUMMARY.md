---
phase: 01-migration-foundation
plan: 02
subsystem: frontend-logic
tags: [tdd, pure-functions, estado-detalle, state-machine, typescript]
dependency_graph:
  requires: []
  provides:
    - parseEstadoDetalle function (mirrors backend estado_detalle_parser.py exactly)
    - getValidOperations / getValidActions pure functions
    - SpoolCardData, Operation, Action TypeScript types (local until Plan 01-01 merges)
  affects:
    - 01-01: SpoolCardData type will be consolidated into types.ts
    - 01-03: hooks will consume getValidOperations + getValidActions
    - Future card components that determine which buttons to render
tech_stack:
  added: []
  patterns:
    - TDD RED-GREEN cycle with Jest
    - Pure function / no side effects
    - Local type aliases with TODO to import from types.ts after Plan 01-01
key_files:
  created:
    - zeues-frontend/lib/parse-estado-detalle.ts
    - zeues-frontend/lib/spool-state-machine.ts
    - zeues-frontend/__tests__/lib/parse-estado-detalle.test.ts
    - zeues-frontend/__tests__/lib/spool-state-machine.test.ts
  modified: []
decisions:
  - "Local type aliases for EstadoTrabajo/OperacionActual/SpoolCardData used instead of import from types.ts — Plan 01-02 is Wave 1 alongside Plan 01-01; TODO comment added to consolidate after 01-01 runs"
  - "isArmFullyCompleted() returns false (ARM partial) when total_uniones is 0 or null — fail-safe default prevents premature SOLD unlock"
  - "PAUSADO + null operacion_actual returns [] not ['ARM'] — only PAUSADO+ARM is documented; other PAUSADO combos are undefined behavior"
  - "getValidActions is keyed only on ocupado_por, not on estado_trabajo — matches backend design: occupation state is the single source of truth for action availability"
metrics:
  duration: "~3 minutes"
  completed_date: "2026-03-10"
  tasks_completed: 2
  files_created: 4
  tests_written: 48
  tests_passing: 48
---

# Phase 01 Plan 02: Logic Layer — parseEstadoDetalle + spool-state-machine Summary

**One-liner:** TypeScript mirror of backend estado_detalle_parser.py (11-step pattern match) plus pure state machine functions (getValidOperations, getValidActions) with ARM-done disambiguation via uniones counts.

## What Was Built

### Feature 1: parseEstadoDetalle

`zeues-frontend/lib/parse-estado-detalle.ts` — pure function mirroring `backend/services/estado_detalle_parser.py` exactly.

- Exports: `parseEstadoDetalle(estado: string | null | undefined): ParsedEstadoDetalle`
- Exports: `ParsedEstadoDetalle` interface
- 11-step pattern match order identical to Python version (order is critical — changing it breaks state detection)
- Returns `{ operacion_actual, estado_trabajo, ciclo_rep, worker }` with LIBRE defaults for null/empty
- No `any` types used

**Patterns covered:**
1. Occupied ARM/SOLD — `"MR(93) trabajando ARM/SOLD (...)"`
2. REPARACION in progress — `"EN_REPARACION (Ciclo N/3) - Ocupado: ..."`
3. BLOQUEADO — `"BLOQUEADO - Contactar supervisor"`
4. RECHAZADO with cycle — `"... RECHAZADO (Ciclo N/3) ..."`
5. RECHAZADO bare — `"RECHAZADO"`
6. PENDIENTE_METROLOGIA — `"REPARACION completado - PENDIENTE_METROLOGIA"`
7. METROLOGIA APROBADO — `"... METROLOGIA APROBADO ✓"`
8. ARM + SOLD completado — `"... ARM completado, SOLD completado"`
9. ARM done, SOLD pending/paused — `"... ARM completado, SOLD pendiente/pausado"`
10. ARM pausado — `"ARM pausado"`
11. Default fallback → LIBRE

### Feature 2: spool-state-machine

`zeues-frontend/lib/spool-state-machine.ts` — pure functions for UI button availability.

- `getValidOperations(spool): Operation[]` — switch on estado_trabajo, returns 0-1 operations
- `getValidActions(spool): Action[]` — keyed on ocupado_por, returns 2-3 actions
- `Operation = 'ARM' | 'SOLD' | 'MET' | 'REP'`
- `Action = 'INICIAR' | 'FINALIZAR' | 'PAUSAR' | 'CANCELAR'`

**ARM disambiguation logic** (`isArmFullyCompleted`):
- PAUSADO + ARM: if `uniones_arm_completadas >= total_uniones` (both non-null, total > 0) → `['SOLD']`
- Otherwise → `['ARM']` (fail-safe: continue ARM when data unavailable)

**getValidActions contract:**
- `ocupado_por` non-null and non-empty → `['FINALIZAR', 'PAUSAR', 'CANCELAR']`
- `ocupado_por` null or empty → `['INICIAR', 'CANCELAR']`

## TDD Execution Summary

| Phase | Feature 1 | Feature 2 |
|-------|-----------|-----------|
| RED   | 27 tests, 0 passing (module not found) | 21 tests, 0 passing (module not found) |
| GREEN | 27 tests, 27 passing | 21 tests, 21 passing |
| REFACTOR | Not needed | Not needed |
| Total | 27 tests | 21 tests |

**Combined: 48 tests, 48 passing. `tsc --noEmit` passes clean.**

## Commits

| Commit | Type | Description |
|--------|------|-------------|
| b3f3523 | test | add failing tests for parseEstadoDetalle (RED) |
| 4e8c0e6 | feat | implement parseEstadoDetalle mirroring backend parser (GREEN) |
| 9fb9116 | test | add failing tests for spool-state-machine (RED) |
| 1a7cd16 | feat | implement spool-state-machine with ARM disambiguation (GREEN) |

## Deviations from Plan

None — plan executed exactly as written.

The Plan 01 dependency note was anticipated: both plans run in Wave 1 so execution order is not guaranteed. Types were defined locally in each file with TODO comments to import from `types.ts` once Plan 01-01 runs and merges the `SpoolCardData`, `EstadoTrabajo`, and `OperacionActual` types.

## Self-Check: PASSED

- zeues-frontend/lib/parse-estado-detalle.ts: FOUND
- zeues-frontend/lib/spool-state-machine.ts: FOUND
- zeues-frontend/__tests__/lib/parse-estado-detalle.test.ts: FOUND
- zeues-frontend/__tests__/lib/spool-state-machine.test.ts: FOUND
- Commit b3f3523: FOUND
- Commit 4e8c0e6: FOUND
- Commit 9fb9116: FOUND
- Commit 1a7cd16: FOUND
