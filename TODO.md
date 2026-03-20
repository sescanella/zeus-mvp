# TODO — ZEUES

Ultima actualizacion: 2026-03-20

## Urgente

Sin items urgentes.

## Pendiente

Sin items pendientes.

## Deuda tecnica

- [ ] `sheets_service.py`: Worker/Trabajadores parsing con row[0] hardcoded (evaluado: no vale la pena — 5 cols fijas, format detection robusto)

## Verificar en produccion

- [ ] Fecha_Armado se escribe correctamente al FINALIZAR armado (pre-existente, sin verificar)
- [ ] Fecha_Soldadura se escribe correctamente al FINALIZAR soldadura (pre-existente, sin verificar)
- [ ] Cycle/bloqueado en getSpoolsReparacion — verificar que SpoolTable muestra ciclo correcto

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
