# ZEUES Frontend v5 Restructuring - TODO

## Etapa 0: Resolver Problemas del Frontend Actual

> No arrastrar deuda tecnica a la nueva version.

### 0.1 Bugs y Problemas Logicos

- [x] ~~**NO CONFORMIDAD button + handler eliminados** -- `tipo-interaccion/page.tsx`~~
- [x] ~~**`classifyApiError` structured-error branch arreglado** -- `api.ts` ahora lanza `ApiError` con status, `error-classifier.ts` usa `instanceof ApiError`~~
- [x] ~~**`handleSelectOperation` branches simplificados** -- `app/page.tsx`: eliminado if/else idéntico~~
- [x] ~~**`handleNewWork` redundante eliminado** -- `exito/page.tsx`: usa `handleFinish` en ambos lugares~~
- [x] ~~**`confirm()` nativo reemplazado por Modal** -- `confirmar/page.tsx`: modal styled con CANCELAR/CONFIRMAR~~
- [ ] **Race condition in seleccionar-uniones session storage** -- `seleccionar-uniones/page.tsx:30-33` clears selectedUnions on mount, then restores from sessionStorage. Both run on mount with no guaranteed ordering. *Requiere decisión sobre state management.*
- [x] ~~**Countdown stale value arreglado** -- `confirmar/page.tsx`: `retrySeconds` se calcula antes de `setErrorModal`~~
- [ ] **INICIAR in seleccionar-spool bypasses P5 confirmation** -- `seleccionar-spool/page.tsx:213-238`: Calls `iniciarSpool()` directly from P4, skipping confirmation. *Requiere decisión de flujo de negocio.*
- [ ] **METROLOGIA P3 config mismatch** -- `operation-config.ts`: METROLOGIA tiene `skipP3: false` pero P3 solo muestra un botón INSPECCIÓN. *Evaluar si debería tener `skipP3: true`.*

### 0.2 Codigo Muerto / Sin Usar

- [x] ~~**Context helpers eliminados** -- `context.tsx`: `calculatePulgadas`, `toggleUnionSelection`, `selectAllAvailableUnions` removidos + import `Union`~~
- [x] ~~**`handleNoConformidad` handler eliminado** -- `tipo-interaccion/page.tsx`~~
- [ ] **`handleInspeccion` uses unsafe type cast** -- `tipo-interaccion/page.tsx:76`: `setState({ selectedTipo: 'metrologia' as unknown as typeof state.selectedTipo })`. *Requiere ampliar el tipo `selectedTipo` en context.*
- [x] ~~**`isV4Spool` inlined** -- `version.ts`: lógica inlined en `detectSpoolVersion`~~
- [ ] **`workerRoles` computed but display-only** -- `tipo-interaccion/page.tsx:134-136`: Could be simplified.
- [x] ~~**`getActionLabel` se mantiene exportado** -- tests lo importan directamente~~

### 0.3 Inconsistencias entre Paginas

- [ ] **Footer component inconsistency** -- `seleccionar-uniones/page.tsx` y `resultado-metrologia/page.tsx` construyen footer inline en vez de usar `FixedFooter`.
- [ ] **Error handling patterns differ** -- 3 estrategias distintas: `classifyApiError`, string matching manual, sin clasificación. *Ahora que `classifyApiError` funciona con `ApiError`, migrar las otras páginas.*
- [ ] **Loading state patterns differ** -- 4 patrones distintos: `<Loading />`, Loader2 spinner, texto "CARGANDO...", texto "Detectando versión...".
- [ ] **Error retry patterns differ** -- `window.location.reload()` vs llamar función fetch directamente.
- [ ] **Navigation guard patterns differ** -- return `null` vs redirect UI con botón vs nada.
- [x] ~~**Operation icon mapping centralizado** -- `operacion/page.tsx` ahora importa `OPERATION_ICONS` de `operation-config.ts`~~
- [x] ~~**Operation name mapping centralizado** -- `operacion/page.tsx` ahora usa `OPERATION_WORKFLOWS[op].label`~~

### 0.4 Problemas de Estado / Context

- [ ] **sessionStorage not cleaned on full reset** -- `resetState()` no limpia sessionStorage (`unions_selection_*`, `spool_version_*`).
- [ ] **`spool_version_*` sessionStorage entries never cleaned** -- Write-only dead code que acumula entries.
- [ ] **selectedSpools not cleared on back navigation** -- Stale selection al volver de P5 a P4.
- [ ] **`batchResults` state persists across flows** -- Puede afectar el siguiente workflow si el usuario no pasa por /exito.

### 0.5 Accesibilidad (WCAG 2.1 AA)

- [x] ~~**Operation selection buttons aria-label** -- `app/page.tsx`: agregados~~
- [x] ~~**Dashboard link aria-label** -- `app/page.tsx`: agregado~~
- [x] ~~**Operation selection buttons focus indicators** -- `app/page.tsx`: agregados~~
- [x] ~~**Worker selection buttons focus indicators** -- `operacion/page.tsx`: agregados~~
- [ ] **Zero-selection modal lacks focus trapping** -- `seleccionar-uniones/page.tsx:319-360`: raw `<div>` sin focus trapping. Debería usar `Modal`.
- [x] ~~**UnionTable rows keyboard navigation** -- `UnionTable.tsx`: role, tabIndex, onKeyDown, aria-label agregados~~
- [x] ~~**CONFIRMAR button aria-label** -- `confirmar/page.tsx`: agregado~~
- [x] ~~**Dashboard Back button aria-label** -- `dashboard/page.tsx`: agregado~~
- [x] ~~**Error modal aria-label** -- `confirmar/page.tsx`: agregado~~
- [x] ~~**Loading component color contraste** -- `Loading.tsx`: cambiado a `text-white/70`~~

### 0.6 Hardcoded Values / Magic Numbers

- [x] ~~**OPERATION_TO_ROLES centralizado** -- movido a `operation-config.ts`~~
- [x] ~~**OPERATION_TITLES centralizado** -- movido a `operation-config.ts`~~
- [x] ~~**OPERATION_ICONS centralizado** -- `operacion/page.tsx` importa de `operation-config.ts`~~
- [x] ~~**Countdown extraído a constante** -- `exito/page.tsx`: `COUNTDOWN_SECONDS = 5`~~
- [ ] **Magic batch limit 50** -- `spool-selection-utils.ts:9`: `MAX_BATCH_SELECTION = 50` hardcoded.
- [ ] **Magic debounce delay 500** -- `hooks/useDebounce.ts:11`: 500ms hardcoded.
- [x] ~~**Dashboard API path centralizado** -- `dashboard/page.tsx` usa `getDashboardOccupied()` de `api.ts`~~
- [ ] **Worker name format constructed inline** -- `seleccionar-spool/page.tsx:217`: debería usar `nombre_completo`.

### 0.7 Performance

- [ ] **`fetchSpools` useCallback has `state` in deps** -- `seleccionar-spool/page.tsx`: callback se recrea en cada cambio de estado.
- [x] ~~**UnionTable sort memoizado** -- `UnionTable.tsx`: envuelto con `useMemo`~~
- [ ] **No fetch cancellation on unmount** -- 4 páginas usan `fetch()` sin `AbortController`.
- [x] ~~**ExitoPage timestamp estabilizado** -- `exito/page.tsx`: capturado una vez con `useRef`~~

### 0.8 API Integration Gaps

- [x] ~~**Dashboard centralizado en api.ts** -- `getDashboardOccupied()` agregada~~
- [x] ~~**REPARACION error handling completo** -- `tomarReparacion`, `pausarReparacion`, `cancelarReparacion` ahora manejan 404/400/409~~
- [ ] **`getSpoolsReparacion` siempre retorna `cycle: 0`** -- TODO en backend para exponer cycle/bloqueado real.
- [x] ~~**`completarMetrologia` double error handling arreglado** -- refactorizado a path único~~
- [ ] **`getSpoolsParaIniciar` called with 'METROLOGIA' type cast** -- `seleccionar-spool/page.tsx:67`: cast inseguro. *Relacionado con decisión de METROLOGIA P3/skipP3.*

---

## Resumen Etapa 0

| Sección | Total | Completados | Pendientes |
|---------|-------|-------------|------------|
| 0.1 Bugs | 9 | 6 | 3 (requieren decisiones) |
| 0.2 Código muerto | 6 | 4 | 2 |
| 0.3 Inconsistencias | 7 | 2 | 5 |
| 0.4 Estado/Context | 4 | 0 | 4 |
| 0.5 Accesibilidad | 10 | 8 | 2 (1 modal focus trap) |
| 0.6 Hardcoded | 8 | 5 | 3 |
| 0.7 Performance | 4 | 2 | 2 |
| 0.8 API | 5 | 3 | 2 |
| **TOTAL** | **53** | **30** | **23** |

### Pendientes que requieren decisión tuya:
1. **INICIAR bypasa P5** -- ¿Debe pasar por confirmar o el comportamiento actual es correcto?
2. **METROLOGIA skipP3** -- ¿Eliminar P3 para metrología (solo tiene 1 botón)?
3. **Race condition seleccionar-uniones** -- ¿Refactorizar session storage o eliminar?

---

## Etapa 1+: (Reservado para nueva estructura)
> Se definira despues de completar Etapa 0.
