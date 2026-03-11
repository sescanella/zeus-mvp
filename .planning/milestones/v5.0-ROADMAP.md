# ZEUES v5.0 — Roadmap

## Phase 0: Backend — Nuevos Endpoints (prerequisito)

**Goal:** Proveer los endpoints que el nuevo frontend necesita.
**Requirements:** [API-01, API-02, API-03]
**Plans:** 3/3 plans complete

Plans:
- [x] 00-01-PLAN.md — parseEstadoDetalle + SpoolStatus model + GET /api/spool/{tag}/status
- [x] 00-02-PLAN.md — POST /api/spools/batch-status (batch refresh)
- [x] 00-03-PLAN.md — FINALIZAR action_override + worker_nombre derivation

### Tasks
- [x] 0.1 — Crear `GET /api/spool/{tag}/status` (expose get_spool_by_tag + campos computados)
- [x] 0.2 — Crear `POST /api/spools/batch-status` (batch refresh, acepta {tags: string[]})
- [x] 0.3 — Modificar `POST /api/v4/occupation/finalizar` (añadir action_override: PAUSAR | COMPLETAR)
- [x] 0.4 — Crear modelo SpoolStatus con campos computados (operacion_actual, estado_trabajo, ciclo_rep)
- [x] 0.5 — Crear `parseEstadoDetalle()` en backend (parsing robusto de Estado_Detalle → estado estructurado)
- [x] 0.6 — Tests unitarios para endpoints nuevos
- [x] 0.7 — Estandarizar worker_nombre derivation (solo worker_id desde frontend, backend deriva nombre)

### Success Criteria
- GET /api/spool/{tag}/status retorna Spool con operacion_actual, estado_trabajo
- POST /api/spools/batch-status retorna N spools en 1 sola llamada
- FINALIZAR con action_override=PAUSAR limpia ocupación sin tocar uniones
- FINALIZAR con action_override=COMPLETAR auto-selecciona todas las uniones restantes
- 100% tests pasando

---

## Phase 1: Frontend — Fundaciones

**Goal:** Crear las utilidades y hooks base que todos los componentes necesitan.
**Requirements:** [CARD-02, CARD-03, STATE-01, STATE-02, MODAL-01, MODAL-02, MODAL-03, MODAL-04, MODAL-05, MODAL-06, MODAL-07, MODAL-08, UX-02, API-01, API-02]
**Plans:** 3/3 plans complete

Plans:
- [x] 01-01-PLAN.md — SpoolCardData types + API functions + localStorage persistence
- [x] 01-02-PLAN.md — parseEstadoDetalle (TS) + spool-state-machine (TDD)
- [x] 01-03-PLAN.md — useModalStack + useNotificationToast hooks (TDD)

### Tasks
- [x] 1.1 — Crear SpoolCardData interface en lib/types.ts
- [x] 1.2 — Crear lib/local-storage.ts (persistencia localStorage)
- [x] 1.3 — Crear lib/spool-state-machine.ts (getValidOperations, getValidActions)
- [x] 1.4 — Crear lib/parse-estado-detalle.ts (parseEstadoDetalle → objeto estructurado)
- [x] 1.5 — Crear hooks/useModalStack.ts (pila de modales)
- [x] 1.6 — Crear hooks/useNotificationToast.ts (cola de notificaciones)
- [x] 1.7 — Agregar funciones API nuevas a lib/api.ts (getSpoolStatus, batchGetStatus)

### Success Criteria
- localStorage persiste y recupera tags correctamente
- spool-state-machine retorna operaciones/acciones correctas para cada estado
- parseEstadoDetalle parsea todos los formatos de Estado_Detalle
- useModalStack gestiona push/pop/clear
- tsc --noEmit sin errores

---

## Phase 2: Frontend — Componentes Core

**Goal:** Crear los componentes visuales reutilizables (3 nuevos + 3 modificados).
**Requirements:** [CARD-02, CARD-06, STATE-05, STATE-06, MODAL-07, UX-01, UX-02, UX-04]
**Plans:** 2/2 plans complete

Plans:
- [x] 02-01-PLAN.md — NotificationToast + SpoolCard + SpoolCardList (new components)
- [x] 02-02-PLAN.md — SpoolTable + SpoolFilterPanel + Modal modifications (backward-compatible props)

### Tasks
- [x] 2.1 — Crear NotificationToast.tsx (toast con auto-dismiss, role="alert")
- [x] 2.2 — Crear SpoolCard.tsx (card individual con estado, timer, badges)
- [x] 2.3 — Crear SpoolCardList.tsx (contenedor con empty state)
- [x] 2.4 — Modificar SpoolTable.tsx (añadir prop disabledSpools)
- [x] 2.5 — Modificar SpoolFilterPanel.tsx (añadir prop showSelectionControls)
- [x] 2.6 — Modificar Modal.tsx (ESC solo cierra modal top del stack)

### Success Criteria
- SpoolCard renderiza todos los estados posibles (libre, iniciado, pausado, completado, rechazado, bloqueado)
- Timer funciona en tiempo real para spools ocupados
- Toast aparece y desaparece en 3-5 segundos
- Componentes modificados mantienen backward compatibility

---

## Phase 3: Frontend — Modales

**Goal:** Crear los 5 modales del flujo de operaciones.
**Requirements:** [MODAL-01, MODAL-02, MODAL-03, MODAL-04, MODAL-05, MODAL-06, MODAL-07, MODAL-08, UX-01, STATE-01, STATE-02]
**Plans:** 2/2 plans complete

Plans:
- [x] 03-01-PLAN.md — AddSpoolModal + OperationModal + ActionModal (presentational modals)
- [x] 03-02-PLAN.md — WorkerModal + MetrologiaModal (API-calling modals)

### Tasks
- [x] 3.1 — Crear AddSpoolModal.tsx (reutiliza SpoolTable + SpoolFilterPanel)
- [x] 3.2 — Crear OperationModal.tsx (ARM/SOLD/REP/MET filtrado por estado)
- [x] 3.3 — Crear ActionModal.tsx (INICIAR/FINALIZAR/PAUSAR/CANCELAR filtrado por estado)
- [x] 3.4 — Crear WorkerModal.tsx (workers filtrados por rol)
- [x] 3.5 — Crear MetrologiaModal.tsx (APROBADA/RECHAZADA)

### Success Criteria
- Flujo completo: Card → Operation → Action → Worker → API → Toast
- Flujo MET: Card → Operation → Metrologia → API → Toast
- CANCELAR sin worker cierra modales directo
- Cada modal muestra solo opciones válidas según estado del spool
- Errores de API se muestran inline en el modal activo

---

## Phase 4: Frontend — Integración

**Goal:** Ensamblar todo en la pantalla principal funcional.
**Requirements:** [CARD-01, CARD-02, CARD-03, CARD-04, CARD-05, CARD-06, MODAL-01, MODAL-02, MODAL-03, MODAL-04, MODAL-05, MODAL-06, MODAL-07, MODAL-08, STATE-01, STATE-02, STATE-03, STATE-04, STATE-05, STATE-06, UX-01, UX-02, UX-03, UX-04]
**Plans:** 2/2 plans complete

Plans:
- [x] 04-01-PLAN.md — SpoolListContext + spool-state-machine type cleanup
- [x] 04-02-PLAN.md — page.tsx rewrite with modal wiring + polling + CANCELAR + auto-remove

### Tasks
- [x] 4.1 — Crear SpoolListContext (nuevo context para card list + localStorage sync)
- [x] 4.2 — Reescribir app/page.tsx (single page: Anadir Spool + SpoolCardList + Toasts)
- [x] 4.3 — Wire flujo modal completo (AddSpool → select → Operation → Action → Worker → API → refresh card)
- [x] 4.4 — Implementar polling 30s (batch-status para refrescar todos los cards)
- [x] 4.5 — Implementar auto-remove en MET APROBADA
- [x] 4.6 — Implementar CANCELAR dual (frontend-only vs backend según ocupado_por)

### Success Criteria
- Flujo E2E funciona: anadir spool → operar → ver resultado en card
- Cards se refrescan cada 30s via batch-status
- MET APROBADA remueve card con animación
- CANCELAR funciona en ambos escenarios
- localStorage persiste entre recargas
- npm run build pasa sin errores

---

## Phase 5: Limpieza

**Goal:** Eliminar código muerto del flujo multi-pantalla.
**Plans:** 2/2 plans complete

Plans:
- [ ] 05-01-PLAN.md — Delete dead pages, components, context.tsx, barrel cleanup
- [ ] 05-02-PLAN.md — Rewrite accessibility tests for v5.0 + final verification

### Tasks
- [ ] 5.1 — Eliminar páginas: operacion/, tipo-interaccion/, seleccionar-spool/, seleccionar-uniones/, confirmar/, exito/, resultado-metrologia/
- [ ] 5.2 — Eliminar componentes: FixedFooter.tsx, SpoolSelectionFooter.tsx, BatchLimitModal.tsx
- [ ] 5.3 — Limpiar context.tsx viejo y spool-selection-utils.ts
- [ ] 5.4 — Actualizar components/index.ts barrel exports
- [ ] 5.5 — Actualizar tests de accesibilidad para nueva arquitectura modal
- [ ] 5.6 — npm run build + tsc --noEmit + npm run lint (todo verde)

### Success Criteria
- 0 archivos muertos
- Build limpio sin warnings
- Tests actualizados y pasando
