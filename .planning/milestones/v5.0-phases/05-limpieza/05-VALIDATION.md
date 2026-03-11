---
phase: 5
slug: limpieza
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-10
---

# Phase 5 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | Jest (jest-environment-jsdom) + Playwright (@axe-core/playwright) |
| **Config file** | `zeues-frontend/jest.config.js` |
| **Quick run command** | `cd zeues-frontend && npx tsc --noEmit` |
| **Full suite command** | `cd zeues-frontend && npm run build && npm test && npm run lint` |
| **Estimated runtime** | ~30 seconds |

---

## Sampling Rate

- **After every task commit:** Run `cd zeues-frontend && npx tsc --noEmit`
- **After every plan wave:** Run `cd zeues-frontend && npm run build && npm test`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 30 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 05-01-01 | 01 | 1 | (cleanup) | build | `npx tsc --noEmit` | ✅ | ⬜ pending |
| 05-01-02 | 01 | 1 | (cleanup) | build | `npx tsc --noEmit` | ✅ | ⬜ pending |
| 05-01-03 | 01 | 1 | (cleanup) | build | `npx tsc --noEmit` | ✅ | ⬜ pending |
| 05-01-04 | 01 | 1 | (cleanup) | build | `npm run build` | ✅ | ⬜ pending |
| 05-02-01 | 02 | 2 | (cleanup) | playwright | `npx playwright test tests/accessibility.spec.ts` | ❌ W0 | ⬜ pending |
| 05-02-02 | 02 | 2 | (cleanup) | build+lint | `npm run build && npm run lint` | ✅ | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/accessibility.spec.ts` — must be rewritten for v5.0 single-page modal architecture (current tests 100% tied to deleted pages)

*Wave 0 gap identified by research: accessibility tests navigate old multi-page routes that will 404 after Phase 5 deletions.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| No dead files remain in app/ | (cleanup) | File presence check | `ls zeues-frontend/app/` — only page.tsx, layout.tsx, dashboard/, globals.css should remain |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 30s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
