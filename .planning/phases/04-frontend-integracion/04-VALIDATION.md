---
phase: 4
slug: frontend-integracion
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-10
---

# Phase 4 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | jest 29.x + @testing-library/react |
| **Config file** | zeues-frontend/jest.config.js |
| **Quick run command** | `cd zeues-frontend && npx jest --passWithNoTests --bail` |
| **Full suite command** | `cd zeues-frontend && npx jest --passWithNoTests && npx tsc --noEmit && npm run lint` |
| **Estimated runtime** | ~30 seconds |

---

## Sampling Rate

- **After every task commit:** Run `cd zeues-frontend && npx jest --passWithNoTests --bail`
- **After every plan wave:** Run `cd zeues-frontend && npx jest --passWithNoTests && npx tsc --noEmit && npm run lint`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 30 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 04-01-01 | 01 | 1 | CARD-03, CARD-06 | unit | `npx jest SpoolListContext` | ❌ W0 | ⬜ pending |
| 04-01-02 | 01 | 1 | CARD-01, CARD-02 | unit | `npx jest page.test` | ❌ W0 | ⬜ pending |
| 04-02-01 | 02 | 2 | MODAL-01 to MODAL-06 | unit | `npx jest modal-wiring` | ❌ W0 | ⬜ pending |
| 04-02-02 | 02 | 2 | CARD-03 | unit | `npx jest polling` | ❌ W0 | ⬜ pending |
| 04-02-03 | 02 | 2 | CARD-04, CARD-05 | unit | `npx jest auto-remove` | ❌ W0 | ⬜ pending |
| 04-02-04 | 02 | 2 | STATE-03, STATE-04 | unit | `npx jest cancelar` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `__tests__/lib/SpoolListContext.test.tsx` — stubs for CARD-03, CARD-06
- [ ] `__tests__/app/page.test.tsx` — stubs for page integration

*Existing test infrastructure covers framework and config.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| 30s polling refreshes cards visually | CARD-03 | Timer-based visual behavior | Open app, wait 30s, verify cards update |
| MET APROBADA fade-out animation | CARD-04 | CSS animation visual verification | Complete MET flow, observe card removal |
| localStorage survives reload | CARD-03 | Browser storage persistence | Add spools, reload page, verify list intact |
| Blueprint palette consistency | UX-04 | Visual design verification | Inspect page colors match navy/orange palette |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 30s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
