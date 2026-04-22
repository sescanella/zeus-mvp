# docs/archive/

Historical snapshots preserved from the former `.planning/` GSD workflow.

**These documents are FROZEN.** They are not updated. They describe the state of the project at specific points in time (Jan–Mar 2026). They are kept because they contain forensic value that is not derivable from git history alone.

## Contents

- `milestones/v{3,4,5}.0-MILESTONE-AUDIT.md` — retrospective audits of completed milestones. Useful when asking "why was X decided" or "what did v4.0 actually ship".
- `codebase/` — seven snapshots of code state (architecture, structure, conventions, stack, testing, integrations, concerns) written Jan–Feb 2026. Older than the current code; read as context, not as truth.
- `RETROSPECTIVE.md` — v5.0 retrospective (Mar 2026).
- `PROJECT.md` — v5.x requirements snapshot (Apr 2026).
- `debug-postmortems/` — 39 resolved-bug write-ups with root causes and fixes. Reference when a similar symptom reappears.
- `CLEANUP-2026-04-22.md` — changelog of the repo cleanup that produced this archive.

## What was deleted (not rescued)

Everything else under `.planning/`: per-phase PLAN/SUMMARY/RESEARCH/VALIDATION/VERIFICATION artifacts, roadmaps/requirements files (redundant with audits), `quick/`, `research/`, `STATE.md`, `MILESTONES.md`, GSD config, and the duplicated `.planning/.planning/` tree.

If you need those, check git history before the `chore: archive .planning/ valuables to docs/archive/` commit.
