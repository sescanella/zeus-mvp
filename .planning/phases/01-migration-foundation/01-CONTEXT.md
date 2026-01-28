# Phase 1: Migration Foundation - Context

**Gathered:** 2026-01-26
**Status:** Ready for planning

<domain>
## Phase Boundary

Safe v2.1 → v3.0 schema migration using **branch-based approach**. v2.1 remains in production untouched while v3.0 is built in separate branch. When v3.0 is fully ready and tested, perform one-time cutover with data migration script. This phase adds new columns to Google Sheet schema to support real-time occupation tracking without breaking existing functionality.

**Key decision:** NO dual-write complexity - clean separation between v2.1 production and v3.0 development.

</domain>

<decisions>
## Implementation Decisions

### Migration Strategy
- **Branch-based migration** - Build v3.0 in separate branch, one-time cutover when ready
- v2.1 stays in production untouched during v3.0 development
- One-time data migration script transforms v2.1 data to v3.0 schema at cutover
- **Rollback window:** 1 week after cutover - keep v2.1 branch available for emergency rollback
- After 1 week validation period, v2.1 becomes archived reference only

### New Column Behavior
- **Three new columns added:** Ocupado_Por, Fecha_Ocupacion, version
- **Position:** End of sheet (after existing 65 columns) - safest, no column index disruption
- **Initial values:** All NULL/empty for existing spools - fresh start, no inferred occupation
- **Version column:** Starts at 0 for new rows, increments on each TOMAR/PAUSAR/COMPLETAR
- **Keep v2.1 columns:** Maintain both old (Armador, Soldador, Fecha_Armado, Fecha_Soldadura) and new columns for redundancy
- **Write strategy:** v3.0 writes to BOTH old and new columns - maintains backward compatibility
  - TOMAR ARM → write to both Armador AND Ocupado_Por
  - COMPLETAR ARM → write to both Fecha_Armado AND Fecha_Ocupacion
- **PAUSAR behavior:** PAUSAR only clears Ocupado_Por/Fecha_Ocupacion - v2.1 columns (Armador/Soldador) keep last person who started work (frozen as historical record)

### Data Safety
- **Automatic backup before migration:** Phase 1 creates Sheet copy before adding columns
- Explicit safety step ensures rollback capability
- Backup naming convention: [Sheet Name]_v2.1_backup_[timestamp]

### Test Strategy
- **Archive v2.1 tests:** Move 244 existing tests to `tests/v2.1-archive/` without running against v3.0
- No validation run needed - trust that adding columns won't break v2.1 behavior
- **Basic smoke tests for v3.0:** Phase 1 includes 3-5 foundational tests:
  1. Can read new columns (Ocupado_Por, Fecha_Ocupacion, version)
  2. Can write to new columns
  3. Version increments correctly
  4. v2.1 columns still readable
  5. Sheet backup creation works

### Claude's Discretion
- Testing environment choice (test Sheet copy vs staging vs production) - Claude decides based on risk assessment
- Exact backup retention policy beyond 1-week rollback window
- Migration script error handling and logging verbosity
- Column header validation approach (dynamic mapping verification)

</decisions>

<specifics>
## Specific Ideas

- "v2.1 works well now - don't want dual-write complexity"
- Branch migration chosen specifically to avoid synchronization issues and keep v2.1 stable
- Version column uses standard optimistic locking pattern (start at 0, increment on writes)
- v2.1 columns frozen during PAUSAR preserves "who last worked on this" information even when occupation released

</specifics>

<deferred>
## Deferred Ideas

None - discussion stayed within phase scope. Migration strategy focused purely on schema evolution, not feature additions.

</deferred>

---

*Phase: 01-migration-foundation*
*Context gathered: 2026-01-26*
