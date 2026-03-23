# TODO — ZEUES

Ultima actualizacion: 2026-03-23

## Urgente

Sin items urgentes.

## Pendiente

- [ ] Corregir palabras sin ñ en la UI (ej: "Reparacion" → "Reparación", "Soldadura" sin tildes, etc.)
- [ ] Planificar milestone v5.1 (`/gsd:new-milestone`)

## Deuda tecnica

- [ ] `sheets_service.py`: Worker/Trabajadores parsing con row[0] hardcoded (evaluado: no vale la pena — 5 cols fijas, format detection robusto)
- [ ] Auditoría UI/UX — items MEDIUM pendientes:
  - [ ] Hover states en botones oscuros (OperationModal, ActionModal — solo tienen `active:`, falta `hover:bg-white/10`)
  - [ ] Retry buttons en WorkerModal y MetrologiaModal (sin boton REINTENTAR en error de fetch)
  - [ ] SpoolCard `✕` Unicode → Lucide `<X>` icon (inconsistencia con resto del codebase)
  - [ ] Error toasts auto-dismiss 4s → persistir hasta dismiss manual (anti-pattern NN Group)
  - [ ] SpoolTable sin `aria-label` en `<table>`
  - [ ] SpoolCardList sin `role="list"` semantico
  - [ ] Palette "Terrosos Desaturados" sin usar en tailwind.config.ts (limpiar tokens muertos)
  - [ ] Modal sin animacion de entrada/salida (scale/fade)
  - [ ] Modal no restaura focus al cerrar (save activeElement on open, restore on close)
- [ ] PROJECT.md: limpiar "Known Technical Debt" — items ya resueltos en 2026-03-20

## Verificar en produccion

- [ ] Fecha_Armado se escribe correctamente al FINALIZAR armado (pre-existente, sin verificar)
- [ ] Fecha_Soldadura se escribe correctamente al FINALIZAR soldadura (pre-existente, sin verificar)
- [ ] Cycle/bloqueado en getSpoolsReparacion — verificar que SpoolTable muestra ciclo correcto

## Completado (2026-03-23)

- [x] Auditoría UI/UX completa (3 agentes paralelos: pages, components, theme)
- [x] Modal.tsx: focus trap (Tab/Shift+Tab cycling), auto-focus on open
- [x] globals.css: `prefers-reduced-motion: reduce` global + body bg dark theme
- [x] Loading.tsx: `role="status"` + `aria-label="Cargando"`
- [x] Touch targets 44px+ en 7 componentes (toast dismiss, close X, CANCELAR/VOLVER, filter buttons, LIMPIAR)
- [x] `cursor-pointer` + `hover:bg-white/10` en todos los botones (6 archivos)
- [x] WorkerModal/MetrologiaModal: theme tokens (`bg-zeues-navy`) + border consistency
- [x] ErrorMessage.tsx: dark theme colors, `role="alert"`, Blueprint retry button
- [x] AddSpoolModal: filtros inline (sin modal anidado), inputMode numeric, placeholders reales

## Completado (2026-03-20)

- [x] `role_repository.py`: Migrado de IDX hardcoded a column map dinamico desde header row
- [x] `api.ts:315`: cycle/bloqueado ahora se extraen de estado_detalle (regex "Ciclo X/3" + BLOQUEADO)
- [x] Eliminado `parseEstadoDetalle` TS mirror (466 lineas muertas)
- [x] Eliminado `UnionTable.tsx` huerfano (145 lineas)
- [x] Eliminado `addTag`/`removeTag`/`clearTags` de local-storage.ts (superseded por SpoolListContext)
- [x] Eliminado stale v3.0 en `operation-config.ts` (ActionType, OperationWorkflow, OPERATION_WORKFLOWS, OPERATION_ICONS)
- [x] `filters/registry.py`: Clarificado comentario — REPARACION FINALIZAR no es bug, usa endpoints v3.0

## Completado (2026-03-12)

- [x] Multi-add en AddSpoolModal — modal queda abierto, contador verde, boton LISTO
- [x] Boton X en SpoolCard para descartar spools (44x44px touch target)
- [x] Armador se registra al INICIAR armado (formato "MR(93)")
- [x] Soldador se registra al INICIAR soldadura
- [x] FINALIZAR no pregunta worker — usa Ocupado_Por automaticamente
- [x] Indices de columna hardcodeados reemplazados por ColumnMapCache dinamico
- [x] Normalizar nombres de columna con accent stripping para spool listing
