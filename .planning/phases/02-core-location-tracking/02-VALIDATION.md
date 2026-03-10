---
phase: 2
slug: core-location-tracking
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-10
---

# Phase 2 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | jest 29.x + @testing-library/react + jest-axe |
| **Config file** | zeues-frontend/jest.config.ts |
| **Quick run command** | `cd zeues-frontend && npx jest --testPathPattern='components/(NotificationToast|SpoolCard|SpoolCardList|SpoolTable|SpoolFilterPanel|Modal)' --bail` |
| **Full suite command** | `cd zeues-frontend && npx jest --coverage` |
| **Estimated runtime** | ~15 seconds |

---

## Sampling Rate

- **After every task commit:** Run quick run command (component-scoped)
- **After every plan wave:** Run full suite command
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 15 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 02-01 | 01 | 1 | UX-02, MODAL-07 | unit + a11y | `npx jest NotificationToast` | ❌ W0 | ⬜ pending |
| 02-02 | 02 | 1 | CARD-02, STATE-05, STATE-06 | unit + a11y | `npx jest SpoolCard` | ❌ W0 | ⬜ pending |
| 02-03 | 02 | 1 | CARD-06 | unit + a11y | `npx jest SpoolCardList` | ❌ W0 | ⬜ pending |
| 02-04 | 03 | 2 | UX-01 | unit (backward compat) | `npx jest SpoolTable` | ✅ | ⬜ pending |
| 02-05 | 03 | 2 | — | unit (backward compat) | `npx jest SpoolFilterPanel` | ✅ | ⬜ pending |
| 02-06 | 03 | 2 | — | unit | `npx jest Modal` | ✅ | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `zeues-frontend/__tests__/components/NotificationToast.test.tsx` — stubs for UX-02, MODAL-07
- [ ] `zeues-frontend/__tests__/components/SpoolCard.test.tsx` — stubs for CARD-02, STATE-05, STATE-06
- [ ] `zeues-frontend/__tests__/components/SpoolCardList.test.tsx` — stubs for CARD-06

*Existing test infrastructure (jest, jest-axe, @testing-library/react) covers all needs. No new framework install required.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Timer real-time update | STATE-05 | Visual verification of tick behavior | Open SpoolCard with occupied spool, verify timer increments every second |
| Toast auto-dismiss visual | UX-02 | Timing-dependent visual behavior | Trigger toast, verify disappears in 3-5 seconds |
| Blueprint palette consistency | UX-04 | Visual design review | Compare component colors against #001F3F / #FF6B35 |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 15s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
