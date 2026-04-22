# Project Retrospective

*A living document updated after each milestone. Lessons feed forward into future planning.*

## Milestone: v5.0 — Single Page + Modal Stack

**Shipped:** 2026-03-11
**Phases:** 6 | **Plans:** 14 | **Sessions:** 1 day

### What Was Built
- Complete UX rewrite from 9-page linear navigation to single-page card list + modal stack
- Backend parseEstadoDetalle parser + SpoolStatus model + batch-status + action_override
- 5 modal components (AddSpool, Operation, Action, Worker, Metrologia) with full test coverage
- SpoolListContext with useReducer + localStorage sync + 30s polling
- Dead code cleanup removing ~3000+ lines of v4.0 multi-page flow

### What Worked
- **TDD RED-GREEN cycle** produced clean, well-tested components from the start
- **Wave-based parallelism** in plans (frontend + backend simultaneously) compressed timeline
- **Reusing existing components** (SpoolTable, Modal, SpoolFilterPanel) with prop extensions avoided rewrites
- **action_override pattern** elegantly eliminated union selection UI without breaking backend logic
- **parseEstadoDetalle** shared logic between Python and TypeScript kept state interpretation consistent

### What Was Inefficient
- **Summary frontmatter** lacked one_liner fields — CLI couldn't auto-extract accomplishments for MILESTONES.md
- **Nyquist validation** left at PARTIAL (draft) for all 6 phases — VALIDATION.md files created but never completed
- **Type duplication** between spool-state-machine.ts and types.ts required extra cleanup plan (04-01)

### Patterns Established
- **Single-page + modal stack** as preferred UX pattern for manufacturing floor apps
- **SpoolListContext** reducer pattern (SET_SPOOLS/ADD_SPOOL/REMOVE_SPOOL/UPDATE_SPOOL) for card list state
- **useRef for polling callbacks** prevents stale closures in 30s intervals
- **Arrow-function jest.mock factories** (no TS type annotations) — SWC transformer requirement
- **isTopOfStack ESC guard** on Modal component prevents deep-stack modals from all closing on ESC

### Key Lessons
1. **action_override > UI complexity** — Eliminating union selection by adding a backend parameter was far simpler than maintaining checkbox UI with live counters
2. **Page Visibility API is essential** — Without it, background tabs waste API quota on invisible polling
3. **Dead code deletion pays for itself** — Removing 7 route directories immediately simplified testing and build pipeline
4. **CANCELAR dual logic** must be explicit — frontend-only vs backend paths need clear separation (libre vs occupied)

### Cost Observations
- Model mix: 100% opus (Claude Opus 4.6)
- Sessions: 1 (single-day development)
- Notable: All 6 phases + 14 plans completed in ~5 hours, including planning + execution + verification

---

## Cross-Milestone Trends

### Process Evolution

| Milestone | Sessions | Phases | Plans | Key Change |
|-----------|----------|--------|-------|------------|
| v3.0 | 3 days | 6 | 31 | First GSD milestone, established patterns |
| v4.0 | 1 day | 7 | 42 | Largest plan count, union-level data model |
| v5.0 | 1 day | 6 | 14 | UX rewrite, fewest plans but high impact |

### Cumulative Quality

| Milestone | Tests | Requirements | Audit Score |
|-----------|-------|-------------|-------------|
| v3.0 | 161 | 24/24 | PASSED |
| v4.0 | 244 | 32/32 | PASSED |
| v5.0 | 301 | 27/27 | PASSED |

### Top Lessons (Verified Across Milestones)

1. **TDD pays off consistently** — RED-GREEN cycle across v3.0, v4.0, and v5.0 catches integration issues early
2. **Reuse over rewrite** — Extending existing components with optional props (v4.0 union selection, v5.0 modal props) is safer than rewrites
3. **Estado_Detalle as state source** — Encoding state in a single column avoids schema migrations and keeps parsing centralized
