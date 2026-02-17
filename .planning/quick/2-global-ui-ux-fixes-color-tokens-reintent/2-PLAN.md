---
phase: quick-2
plan: 01
type: execute
wave: 1
depends_on: []
files_modified:
  - zeues-frontend/tailwind.config.ts
  - zeues-frontend/app/exito/page.tsx
  - zeues-frontend/app/formularios/no-conformidad/page.tsx
  - zeues-frontend/app/operacion/page.tsx
  - zeues-frontend/app/resultado-metrologia/page.tsx
  - zeues-frontend/app/seleccionar-spool/page.tsx
  - zeues-frontend/app/seleccionar-uniones/page.tsx
  - zeues-frontend/app/tipo-interaccion/page.tsx
  - zeues-frontend/components/BatchLimitModal.tsx
  - zeues-frontend/components/BlueprintPageWrapper.tsx
  - zeues-frontend/components/FixedFooter.tsx
  - zeues-frontend/components/SpoolFilterPanel.tsx
  - zeues-frontend/components/SpoolSelectionFooter.tsx
  - zeues-frontend/components/SpoolTable.tsx
  - zeues-frontend/components/UnionTable.tsx
autonomous: true
requirements: []
must_haves:
  truths:
    - "No hardcoded #001F3F hex values remain in .tsx files - all use zeues-navy token"
    - "No hardcoded #E55D26/#CC5322 hex values remain - all use zeues-orange-border/zeues-orange-pressed tokens"
    - "REINTENTAR button in no-conformidad calls handleSubmit() to retry the form submission"
    - "REINTENTAR button in resultado-metrologia retries with the last resultado via lastResultado state"
    - "Empty state guards in no-conformidad and resultado-metrologia auto-redirect to home with visible text"
    - "Textarea in no-conformidad has proper label association via htmlFor/id and aria-describedby"
  artifacts:
    - path: "zeues-frontend/tailwind.config.ts"
      provides: "Color token definitions for zeues-navy, zeues-orange-border, zeues-orange-pressed"
      contains: "zeues-navy"
  key_links:
    - from: "zeues-frontend/**/*.tsx"
      to: "zeues-frontend/tailwind.config.ts"
      via: "Tailwind class names using color tokens"
      pattern: "zeues-navy|zeues-orange-border|zeues-orange-pressed"
---

<objective>
Verify and commit already-implemented global UI/UX fixes across the ZEUES frontend.

Purpose: Document and commit 6 categories of improvements that are already coded and verified: Tailwind color tokens, hardcoded hex replacement, REINTENTAR retry logic, auto-redirect on empty state, and textarea accessibility.

Output: Committed changes across 15 files with verification that builds pass.
</objective>

<execution_context>
@/Users/sescanella/.claude/get-shit-done/workflows/execute-plan.md
@/Users/sescanella/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
All changes are ALREADY IMPLEMENTED and sitting as unstaged modifications in the working tree. This plan verifies and commits them.
</context>

<tasks>

<task type="auto">
  <name>Task 1: Verify all changes pass quality checks</name>
  <files>zeues-frontend/</files>
  <action>
Run the full frontend quality suite to confirm all 15 modified files produce no errors:

1. TypeScript type checking: `cd zeues-frontend && npx tsc --noEmit`
2. ESLint with zero warnings: `npm run lint`
3. Production build: `npm run build`

All three must pass cleanly. If any fail, diagnose and fix before proceeding.
  </action>
  <verify>All three commands exit with code 0 and zero warnings.</verify>
  <done>TypeScript, lint, and build all pass with no errors or warnings.</done>
</task>

<task type="auto">
  <name>Task 2: Commit changes in logical groups</name>
  <files>
zeues-frontend/tailwind.config.ts
zeues-frontend/app/exito/page.tsx
zeues-frontend/app/formularios/no-conformidad/page.tsx
zeues-frontend/app/operacion/page.tsx
zeues-frontend/app/resultado-metrologia/page.tsx
zeues-frontend/app/seleccionar-spool/page.tsx
zeues-frontend/app/seleccionar-uniones/page.tsx
zeues-frontend/app/tipo-interaccion/page.tsx
zeues-frontend/components/BatchLimitModal.tsx
zeues-frontend/components/BlueprintPageWrapper.tsx
zeues-frontend/components/FixedFooter.tsx
zeues-frontend/components/SpoolFilterPanel.tsx
zeues-frontend/components/SpoolSelectionFooter.tsx
zeues-frontend/components/SpoolTable.tsx
zeues-frontend/components/UnionTable.tsx
  </files>
  <action>
Stage and commit all 15 modified files in a single commit with a descriptive message covering all 6 categories of changes:

1. Tailwind color tokens added to tailwind.config.ts (zeues-navy, zeues-orange-border, zeues-orange-pressed)
2. 44 hardcoded `#001F3F` replaced with `zeues-navy` across 14 .tsx files
3. 6 hardcoded `#E55D26`/`#CC5322` replaced with token classes in 2 files
4. REINTENTAR retry logic fixed in no-conformidad (calls handleSubmit) and resultado-metrologia (lastResultado state)
5. Auto-redirect useEffect added to empty state guards in no-conformidad and resultado-metrologia
6. Textarea accessibility improved in no-conformidad (label htmlFor, id, aria-describedby)

Use a single commit since all changes are related UI/UX improvements that were done together.
Do NOT stage the `investigacion/` untracked directory.
  </action>
  <verify>`git log --oneline -1` shows the new commit. `git status` shows clean working tree (only `investigacion/` untracked).</verify>
  <done>All 15 files committed. Working tree clean except for unrelated `investigacion/` directory.</done>
</task>

</tasks>

<verification>
- `git diff --cached` is empty (all committed)
- `git log --oneline -1` shows descriptive commit message
- `git status` shows only `investigacion/` as untracked
- No hardcoded `#001F3F` remains in committed .tsx files (grep confirms)
</verification>

<success_criteria>
All 15 files committed with passing build. No regressions in TypeScript, lint, or production build.
</success_criteria>

<output>
After completion, create `.planning/quick/2-global-ui-ux-fixes-color-tokens-reintent/2-SUMMARY.md`
</output>
