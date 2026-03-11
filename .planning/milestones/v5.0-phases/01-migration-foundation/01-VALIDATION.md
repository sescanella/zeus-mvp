---
phase: 1
slug: migration-foundation
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-10
---

# Phase 1 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | jest 30.2.0 (frontend) |
| **Config file** | zeues-frontend/jest.config.ts |
| **Quick run command** | `cd zeues-frontend && npx jest --passWithNoTests` |
| **Full suite command** | `cd zeues-frontend && npx jest --passWithNoTests && npx tsc --noEmit && npm run lint` |
| **Estimated runtime** | ~15 seconds |

---

## Sampling Rate

- **After every task commit:** Run `cd zeues-frontend && npx jest --passWithNoTests`
- **After every plan wave:** Run `cd zeues-frontend && npx jest --passWithNoTests && npx tsc --noEmit && npm run lint`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 15 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 01-01 | 01 | 1 | CARD-02 | type-check | `npx tsc --noEmit` | ❌ W0 | ⬜ pending |
| 01-02 | 02 | 1 | CARD-03 | unit | `npx jest local-storage` | ❌ W0 | ⬜ pending |
| 01-03 | 03 | 1 | STATE-01, STATE-02 | unit | `npx jest spool-state-machine` | ❌ W0 | ⬜ pending |
| 01-04 | 04 | 1 | CARD-02 | unit | `npx jest parse-estado-detalle` | ❌ W0 | ⬜ pending |
| 01-05 | 05 | 1 | MODAL-01..08 | unit | `npx jest useModalStack` | ❌ W0 | ⬜ pending |
| 01-06 | 06 | 1 | UX-02 | unit | `npx jest useNotificationToast` | ❌ W0 | ⬜ pending |
| 01-07 | 07 | 1 | API-01, API-02 | type-check | `npx tsc --noEmit` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `zeues-frontend/lib/__tests__/local-storage.test.ts` — stubs for CARD-03
- [ ] `zeues-frontend/lib/__tests__/spool-state-machine.test.ts` — stubs for STATE-01, STATE-02
- [ ] `zeues-frontend/lib/__tests__/parse-estado-detalle.test.ts` — stubs for CARD-02
- [ ] `zeues-frontend/hooks/__tests__/useModalStack.test.ts` — stubs for MODAL-01..08
- [ ] `zeues-frontend/hooks/__tests__/useNotificationToast.test.ts` — stubs for UX-02

*Existing jest infrastructure covers framework needs — only test files needed.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| localStorage persists across page reload | CARD-03 | Browser-only behavior | Add tag, reload page, verify tag present |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 15s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
