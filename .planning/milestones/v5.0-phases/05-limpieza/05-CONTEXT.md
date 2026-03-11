# Phase 5: Limpieza - Context

**Gathered:** 2026-03-10
**Status:** Ready for planning
**Source:** Auto-generated from ROADMAP.md + REQUIREMENTS.md

<domain>
## Phase Boundary

This phase eliminates dead code from the old multi-page flow (v4.0 9-page navigation) now that v5.0 single-page + modal stack is assembled in Phase 4. No new features — purely deletion and cleanup.

</domain>

<decisions>
## Implementation Decisions

### Dead Page Removal
- Delete all old route directories: operacion/, tipo-interaccion/, seleccionar-spool/, seleccionar-uniones/, confirmar/, exito/, resultado-metrologia/
- These pages are fully replaced by the single-page modal flow

### Dead Component Removal
- Delete FixedFooter.tsx — replaced by modal-based actions
- Delete SpoolSelectionFooter.tsx — replaced by SpoolCardList + modals
- Delete BatchLimitModal.tsx — batch limit concept removed in v5.0

### Context Cleanup
- Clean old context.tsx (multi-page state management) — replaced by SpoolListContext
- Clean spool-selection-utils.ts — selection logic now in spool-state-machine.ts

### Barrel Export Updates
- Update components/index.ts to remove deleted component exports
- Ensure no dangling imports remain

### Accessibility Test Updates
- Update accessibility tests for modal-based architecture
- Remove tests for deleted pages
- Add/update tests for modal stack accessibility

### Build Verification
- npm run build must pass cleanly
- tsc --noEmit must pass
- npm run lint must pass with 0 warnings

### Claude's Discretion
- Order of deletion (pages first vs components first)
- Whether to batch deletions or do incremental commits
- How to handle any shared utilities used by both old and new code

</decisions>

<specifics>
## Specific Ideas

- Pages to delete: operacion/, tipo-interaccion/, seleccionar-spool/, seleccionar-uniones/, confirmar/, exito/, resultado-metrologia/
- Components to delete: FixedFooter.tsx, SpoolSelectionFooter.tsx, BatchLimitModal.tsx
- Files to clean: context.tsx, spool-selection-utils.ts
- Barrel file: components/index.ts

</specifics>

<deferred>
## Deferred Ideas

None — this phase is self-contained cleanup with no future dependencies.

</deferred>

---

*Phase: 05-limpieza*
*Context gathered: 2026-03-10 via auto-generation from ROADMAP.md*
