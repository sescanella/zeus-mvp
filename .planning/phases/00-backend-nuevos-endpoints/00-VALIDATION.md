---
phase: 0
slug: backend-nuevos-endpoints
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-10
---

# Phase 0 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 7.x |
| **Config file** | pytest.ini (implicit via pyproject.toml) |
| **Quick run command** | `PYTHONPATH="$(pwd)" pytest tests/unit/ -v --tb=short -q` |
| **Full suite command** | `PYTHONPATH="$(pwd)" pytest tests/ -v --tb=short` |
| **Estimated runtime** | ~15 seconds |

---

## Sampling Rate

- **After every task commit:** Run `PYTHONPATH="$(pwd)" pytest tests/unit/ -v --tb=short -q`
- **After every plan wave:** Run `PYTHONPATH="$(pwd)" pytest tests/ -v --tb=short`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 15 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 0-01-01 | 01 | 1 | API-01 | unit | `pytest tests/unit/services/test_spool_status.py -v` | ❌ W0 | ⬜ pending |
| 0-01-02 | 01 | 1 | API-01 | unit | `pytest tests/unit/routers/test_spool_status_router.py -v` | ❌ W0 | ⬜ pending |
| 0-02-01 | 02 | 1 | API-02 | unit | `pytest tests/unit/routers/test_batch_status.py -v` | ❌ W0 | ⬜ pending |
| 0-03-01 | 03 | 1 | API-03 | unit | `pytest tests/unit/services/test_finalizar_action_override.py -v` | ❌ W0 | ⬜ pending |
| 0-04-01 | 01 | 1 | API-01 | unit | `pytest tests/unit/models/test_spool_status_model.py -v` | ❌ W0 | ⬜ pending |
| 0-05-01 | 01 | 1 | API-01 | unit | `pytest tests/unit/utils/test_parse_estado_detalle.py -v` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/unit/utils/test_parse_estado_detalle.py` — stubs for Estado_Detalle parser
- [ ] `tests/unit/models/test_spool_status_model.py` — stubs for SpoolStatus model
- [ ] `tests/unit/services/test_spool_status.py` — stubs for spool status service
- [ ] `tests/unit/routers/test_spool_status_router.py` — stubs for GET endpoint
- [ ] `tests/unit/routers/test_batch_status.py` — stubs for POST batch endpoint
- [ ] `tests/unit/services/test_finalizar_action_override.py` — stubs for action_override

*Existing infrastructure covers framework installation — pytest already configured.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Batch-status with production data | API-02 | Requires Google Sheets connection | Call batch-status with 5+ real tags, verify response shape |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 15s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
