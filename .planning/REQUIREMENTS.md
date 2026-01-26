# Requirements: ZEUES v3.0

**Defined:** 2026-01-26
**Core Value:** Real-time visibility of spool occupation - See EN VIVO who is working on which spool

## v3.0 Requirements

Requirements for v3.0 real-time location tracking system. Each maps to roadmap phases.

### Location Tracking

- [ ] **LOC-01**: Worker can TOMAR available spool (occupation constraint enforced)
- [ ] **LOC-02**: Worker can PAUSAR spool without completing (→ DISPONIBLE)
- [ ] **LOC-03**: Worker can COMPLETAR spool (finish + → DISPONIBLE)
- [ ] **LOC-04**: System prevents 2 workers TOMAR same spool (race condition protection)
- [ ] **LOC-05**: Worker can see real-time list of DISPONIBLE spools (< 10s refresh)
- [ ] **LOC-06**: Worker can see real-time list of OCUPADO spools with owner

### State Management

- [ ] **STATE-01**: System displays combined state (occupation + ARM progress + SOLD progress)
- [ ] **STATE-02**: Metadata logs all TOMAR/PAUSAR/COMPLETAR events (audit trail)
- [ ] **STATE-03**: Estado_Detalle shows "Armando: Juan (93) - ARM parcial, SOLD pendiente"
- [ ] **STATE-04**: System uses hierarchical state machine (< 15 states, not 27+)

### Collaborative Work

- [ ] **COLLAB-01**: Any worker with correct role can continue partially-completed work
- [ ] **COLLAB-02**: System enforces operation dependencies (SOLD requires ARM initiated)
- [ ] **COLLAB-03**: System tracks multiple workers on same spool sequentially
- [ ] **COLLAB-04**: Worker can view occupation history per spool

### Metrología

- [ ] **METRO-01**: Metrólogo can COMPLETAR with result (APROBADO / RECHAZADO)
- [ ] **METRO-02**: Metrología workflow skips TOMAR (instant completion)
- [ ] **METRO-03**: RECHAZADO triggers estado "Pendiente reparación"
- [ ] **METRO-04**: Metrología requires ARM + SOLD both COMPLETADO

### Reparación

- [ ] **REPAR-01**: Worker can TOMAR spool RECHAZADO for reparación
- [ ] **REPAR-02**: Reparación specifies responsible role (Armador/Soldador)
- [ ] **REPAR-03**: COMPLETAR reparación returns spool to metrología queue
- [ ] **REPAR-04**: System limits reparación cycles (max 3 loops)

### Backward Compatibility

- [ ] **BC-01**: v2.1 data migrates to v3.0 schema without loss
- [ ] **BC-02**: 244 existing tests continue passing during migration
- [ ] **BC-03**: Dual-write period (2-4 weeks) supports gradual cutover

## v2.1 Requirements (Validated)

Production features already validated in v2.1:

### Authentication & Workers

- ✓ **V21-AUTH-01**: Worker management with multi-role system — v2.1
- ✓ **V21-AUTH-02**: Role-based access control (Armador, Soldador, Metrología, Ayudante) — v2.1
- ✓ **V21-AUTH-03**: Service Account authentication with Google Sheets — v2.1

### Core Operations

- ✓ **V21-OPS-01**: INICIAR operation (ARM, SOLD) — v2.1
- ✓ **V21-OPS-02**: COMPLETAR operation with ownership validation — v2.1
- ✓ **V21-OPS-03**: CANCELAR operation EN_PROGRESO — v2.1
- ✓ **V21-OPS-04**: Batch operations (up to 50 spools) — v2.1

### Data & Audit

- ✓ **V21-DATA-01**: Google Sheets as source of truth (Operaciones, Trabajadores, Roles, Metadata) — v2.1
- ✓ **V21-DATA-02**: Metadata Event Sourcing (append-only audit trail) — v2.1
- ✓ **V21-DATA-03**: Direct Read architecture (Operaciones READ-ONLY) — v2.1

### Frontend

- ✓ **V21-UI-01**: Mobile-first UI for tablets (large buttons h-16/h-20) — v2.1
- ✓ **V21-UI-02**: 7-page linear flow (Worker → Operation → Type → Spool → Confirm → Success) — v2.1
- ✓ **V21-UI-03**: Batch UI (multiselect with checkboxes, contador, select all) — v2.1

### Infrastructure

- ✓ **V21-INFRA-01**: FastAPI backend deployed on Railway — v2.1
- ✓ **V21-INFRA-02**: Next.js frontend deployed on Vercel — v2.1
- ✓ **V21-INFRA-03**: 244 passing tests (pytest + Playwright) — v2.1

## Out of Scope

Explicitly excluded features with reasoning.

| Feature | Reason |
|---------|--------|
| **Automatic PAUSAR on timeout** | Manual control only. Workers decide when to release spools. Automatic timeout could release mid-critical-operation. Adds complexity without clear value. |
| **GPS/RFID physical tracking** | Logical occupation (worker assignment) sufficient for manufacturing floor scale (30-50 workers). Physical sensors cost $50K+ (UWB/BLE infrastructure). Avoid hardware dependency. |
| **Sub-1-second real-time sync** | 5-10 second refresh sufficient for manufacturing floor (not warehouse picking). Google Sheets API limits (200-500ms latency) make sub-second impossible. Over-engineering. |
| **Reservation system** | No "reserve for later" without physically taking spool. Prevents inventory hoarding, ensures real physical state. Reservation adds ghost occupations. |
| **Multi-operation TOMAR** | Worker can only TOMAR for ONE operation at a time (ARM or SOLD, not both simultaneously). Prevents blocking other workers. Single-threaded work is manufacturing reality. |
| **Retroactive edits** | Metadata is append-only (no editing history). Regulatory requirement for audit trail integrity. Allow edits → enable fraud. |
| **Complex role hierarchies** | Flat role system (4 roles: Armador, Soldador, Metrología, Ayudante). No supervisor approval workflows, manager hierarchies, or delegated permissions in v3.0. Defer to v3.1+ if needed. |
| **Video/photo uploads** | Metrología result is binary (APROBADO/RECHAZADO). Photos for defect documentation defer to v3.1+. Adds storage complexity (Google Drive integration). |
| **Real-time chat/notifications** | Workers use physical proximity (manufacturing floor). No Slack-style chat or push notifications. Dashboard visibility sufficient. |
| **Mobile apps (iOS/Android)** | Web-first on tablets. Native apps defer to v4.0+. PWA sufficient for offline capability if needed later. |
| **Advanced analytics/dashboards** | Basic "who has what" dashboard only. BI dashboards (productivity metrics, bottleneck analysis, cycle time) defer to v3.1+. Focus on operational visibility first. |

## Traceability

Which phases cover which requirements. Updated during roadmap creation.

| Requirement | Phase | Status |
|-------------|-------|--------|
| LOC-01 | TBD | Pending |
| LOC-02 | TBD | Pending |
| LOC-03 | TBD | Pending |
| LOC-04 | TBD | Pending |
| LOC-05 | TBD | Pending |
| LOC-06 | TBD | Pending |
| STATE-01 | TBD | Pending |
| STATE-02 | TBD | Pending |
| STATE-03 | TBD | Pending |
| STATE-04 | TBD | Pending |
| COLLAB-01 | TBD | Pending |
| COLLAB-02 | TBD | Pending |
| COLLAB-03 | TBD | Pending |
| COLLAB-04 | TBD | Pending |
| METRO-01 | TBD | Pending |
| METRO-02 | TBD | Pending |
| METRO-03 | TBD | Pending |
| METRO-04 | TBD | Pending |
| REPAR-01 | TBD | Pending |
| REPAR-02 | TBD | Pending |
| REPAR-03 | TBD | Pending |
| REPAR-04 | TBD | Pending |
| BC-01 | TBD | Pending |
| BC-02 | TBD | Pending |
| BC-03 | TBD | Pending |

**Coverage:**
- v3.0 requirements: 25 total
- Mapped to phases: 0 (awaiting roadmap)
- Unmapped: 25 ⚠️

---
*Requirements defined: 2026-01-26*
*Last updated: 2026-01-26 after initial definition*
