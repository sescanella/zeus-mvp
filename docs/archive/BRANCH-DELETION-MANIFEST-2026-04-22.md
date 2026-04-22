# Branch deletion manifest — 2026-04-22

All 13 feature/fix branches for merged PRs (#2–#14) were removed from `origin`. They were already deleted via GitHub's "Delete branch after merge" setting; this manifest just documents what existed and how to recover any of them if needed.

## Recovery

Every commit is preserved in GitHub's `refs/pull/<N>/head` ref (permanent, read-only). To restore a branch locally:

```bash
git fetch origin refs/pull/<N>/head:recovered/<branch-name>
```

Example:

```bash
git fetch origin refs/pull/10/head:recovered/feat/F-1-notas-spool
git checkout recovered/feat/F-1-notas-spool
```

## Manifest

| branch | tip SHA | PR | recovery ref |
|---|---|---|---|
| `feat/F-1-notas-spool` | `764e574` | [#10](https://github.com/sescanella/zeus-mvp/pull/10) | `refs/pull/10/head` |
| `feat/UX-1a-buscador-listing` | `1cefafa` | [#11](https://github.com/sescanella/zeus-mvp/pull/11) | `refs/pull/11/head` |
| `feat/UX-1d-filtro-trabajador` | `0b6b9ec` | [#12](https://github.com/sescanella/zeus-mvp/pull/12) | `refs/pull/12/head` |
| `feat/UX-2-batch-ingreso` | `beda894` | [#13](https://github.com/sescanella/zeus-mvp/pull/13) | `refs/pull/13/head` |
| `feat/UX-3-UX-5-uniones-modal-cleanup` | `7cb0ae3` | [#8](https://github.com/sescanella/zeus-mvp/pull/8) | `refs/pull/8/head` |
| `fix/D-1-validar-worker-id-reparacion` | `6e700d5` | [#9](https://github.com/sescanella/zeus-mvp/pull/9) | `refs/pull/9/head` |
| `fix/H2-validacion-metrologia-uniones` | `02964e0` | [#4](https://github.com/sescanella/zeus-mvp/pull/4) | `refs/pull/4/head` |
| `fix/T-021-audit-trail-enum` | `18e453b` | [#5](https://github.com/sescanella/zeus-mvp/pull/5) | `refs/pull/5/head` |
| `fix/T-095-rechazo-abre-selector-reparador` | `8910671` | [#3](https://github.com/sescanella/zeus-mvp/pull/3) | `refs/pull/3/head` |
| `fix/T-095-tomar-reparacion-422` | `68d6f46` | [#6](https://github.com/sescanella/zeus-mvp/pull/6) | `refs/pull/6/head` |
| `fix/T-096-metrologia-partial-sold-v3-detection` | `363040e` | [#2](https://github.com/sescanella/zeus-mvp/pull/2) | `refs/pull/2/head` |
| `fix/UX-3-count-input-editable` | `409b9d2` | [#14](https://github.com/sescanella/zeus-mvp/pull/14) | `refs/pull/14/head` |
| `fix/UX-4-buscador-alfanumerico` | `f62eb00` | [#7](https://github.com/sescanella/zeus-mvp/pull/7) | `refs/pull/7/head` |
