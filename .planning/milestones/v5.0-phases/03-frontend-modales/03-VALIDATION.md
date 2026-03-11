---
phase: 3
slug: frontend-modales
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-10
---

# Phase 3 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | Jest 30.2.0 + @testing-library/react 16.3.2 + jest-axe 10.0.0 |
| **Config file** | `zeues-frontend/jest.config.js` |
| **Quick run command** | `cd zeues-frontend && npx jest __tests__/components/<ModalName>.test.tsx --no-coverage` |
| **Full suite command** | `cd zeues-frontend && npm test -- --no-coverage` |
| **Estimated runtime** | ~15 seconds |

---

## Sampling Rate

- **After every task commit:** Run `cd zeues-frontend && npx jest __tests__/components/<ModalName>.test.tsx --no-coverage`
- **After every plan wave:** Run `cd zeues-frontend && npm test -- --no-coverage`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 15 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 03-01 | 01 | 1 | UX-01 | unit | `npx jest __tests__/components/AddSpoolModal.test.tsx` | ❌ W0 | ⬜ pending |
| 03-02 | 02 | 1 | MODAL-01, STATE-01 | unit | `npx jest __tests__/components/OperationModal.test.tsx` | ❌ W0 | ⬜ pending |
| 03-03 | 02 | 1 | MODAL-02, MODAL-04, STATE-02 | unit | `npx jest __tests__/components/ActionModal.test.tsx` | ❌ W0 | ⬜ pending |
| 03-04 | 03 | 1 | MODAL-03, MODAL-06, MODAL-08 | unit | `npx jest __tests__/components/WorkerModal.test.tsx` | ❌ W0 | ⬜ pending |
| 03-05 | 03 | 1 | MODAL-05, MODAL-06 | unit | `npx jest __tests__/components/MetrologiaModal.test.tsx` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `zeues-frontend/__tests__/components/AddSpoolModal.test.tsx` — stubs for UX-01
- [ ] `zeues-frontend/__tests__/components/OperationModal.test.tsx` — stubs for MODAL-01, STATE-01
- [ ] `zeues-frontend/__tests__/components/ActionModal.test.tsx` — stubs for MODAL-02, MODAL-04, STATE-02
- [ ] `zeues-frontend/__tests__/components/WorkerModal.test.tsx` — stubs for MODAL-03, MODAL-06, MODAL-08
- [ ] `zeues-frontend/__tests__/components/MetrologiaModal.test.tsx` — stubs for MODAL-05, MODAL-06

*No new framework install needed — Jest + testing-library already configured.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Modal visual rendering (Blueprint palette) | UX-04 | Visual/CSS cannot be unit tested | Open each modal, verify navy bg, white borders, orange accents |
| Touch target size (h-16 buttons) | UX-04 | Size verification needs visual inspection | Verify buttons are 64px height on tablet |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 15s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
