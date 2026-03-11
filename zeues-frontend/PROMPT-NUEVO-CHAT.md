# Prompt inicial para nuevo chat — ZEUES Frontend Reestructuración

Pega esto como primer mensaje en el nuevo chat:

---

## Contexto: ZEUES Frontend — Reestructuración lista para comenzar

Acabo de completar la **Etapa 0** (limpieza de deuda técnica) del frontend. El proyecto está en `zeues-frontend/`. Antes de darme la nueva estructura, necesitas entender el estado actual:

### Lo que se hizo (Etapa 0 — 30/53 items resueltos)

**Archivos modificados (13 files, +225 -195 lines):**
- `app/page.tsx` — branches simplificados, aria-labels, focus indicators
- `app/operacion/page.tsx` — config centralizada (icons, roles, titles importados de operation-config.ts), focus indicators
- `app/tipo-interaccion/page.tsx` — NO CONFORMIDAD eliminado (botón + handler)
- `app/seleccionar-spool/page.tsx` — sin cambios
- `app/seleccionar-uniones/page.tsx` — sin cambios
- `app/confirmar/page.tsx` — confirm() nativo → Modal, countdown fix, aria-labels
- `app/exito/page.tsx` — handleNewWork eliminado, timestamp estabilizado con useRef, COUNTDOWN_SECONDS extraído
- `app/dashboard/page.tsx` — raw fetch → getDashboardOccupied() centralizada, aria-label
- `components/UnionTable.tsx` — keyboard nav (role, tabIndex, onKeyDown, aria-label), sort memoizado con useMemo
- `components/Loading.tsx` — color text-slate-700 → text-white/70 para contraste WCAG
- `lib/api.ts` — ApiError class, handleResponse lanza ApiError con status, getDashboardOccupied(), REPARACION error handling completo, completarMetrologia simplificado
- `lib/error-classifier.ts` — instanceof ApiError (ya no es dead code)
- `lib/context.tsx` — helpers no usados eliminados (calculatePulgadas, toggleUnionSelection, selectAllAvailableUnions)
- `lib/operation-config.ts` — OPERATION_TO_ROLES y OPERATION_TITLES exportados
- `lib/version.ts` — isV4Spool inlined en detectSpoolVersion

**Build status:** tsc ✅ | ESLint ✅ | build ✅

### 23 items pendientes de Etapa 0 (no bloquean la reestructuración)

**Requieren decisiones de negocio (3):**
1. INICIAR bypasa P5 confirmación — ¿intencional o bug?
2. METROLOGIA skipP3 — P3 solo tiene 1 botón INSPECCIÓN, ¿eliminar paso?
3. Race condition seleccionar-uniones session storage

**Inconsistencias (se resolverán durante la reestructuración):**
- Footer: 2 páginas usan footer inline vs FixedFooter
- Error handling: 3 patrones distintos (classifyApiError ya funciona, migrar resto)
- Loading: 4 patrones distintos
- Error retry: window.location.reload() vs llamar fetch
- Navigation guards: return null vs redirect UI

**Estado/Context (4):**
- sessionStorage no se limpia en resetState()
- spool_version_* es write-only dead code
- selectedSpools stale en back navigation
- batchResults persiste entre flows

**Menores (performance, hardcoded, API):**
- fetchSpools useCallback con state en deps
- No AbortController en fetch calls
- Magic batch limit 50, debounce 500
- Worker name format inline vs nombre_completo
- getSpoolsReparacion cycle siempre 0
- getSpoolsParaIniciar cast METROLOGIA a ARM|SOLD

### Inventario actual del frontend

**Páginas (9):**
| Ruta | Archivo | Función |
|------|---------|---------|
| `/` | `app/page.tsx` | P1: Selección operación (ARM/SOLD/MET/REP) |
| `/operacion` | `app/operacion/page.tsx` | P2: Selección trabajador por rol |
| `/tipo-interaccion` | `app/tipo-interaccion/page.tsx` | P3: Tipo acción (INICIAR/FINALIZAR o TOMAR/PAUSAR/COMPLETAR) |
| `/seleccionar-spool` | `app/seleccionar-spool/page.tsx` | P4: Selección spool con filtros + batch |
| `/seleccionar-uniones` | `app/seleccionar-uniones/page.tsx` | P5: Selección uniones v4.0 FINALIZAR |
| `/confirmar` | `app/confirmar/page.tsx` | P6: Confirmación + API call |
| `/exito` | `app/exito/page.tsx` | P7: Éxito + countdown 5s |
| `/resultado-metrologia` | `app/resultado-metrologia/page.tsx` | APROBADO/RECHAZADO |
| `/dashboard` | `app/dashboard/page.tsx` | Vista admin spools ocupados |

**Componentes reutilizables (10):**
| Componente | Reusabilidad | Descripción |
|------------|-------------|-------------|
| BlueprintPageWrapper | 10/10 | Container con grid navy — TODAS las páginas |
| Modal | 10/10 | Portal + backdrop + ESC + focus trap |
| FixedFooter | 10/10 | Footer sticky con 2-3 botones (back/primary/middle) |
| Loading | 8/10 | Spinner animado branded |
| ErrorMessage | 9/10 | Error display con tipo, icono, retry |
| SpoolTable | 9/10 | Tabla selección spools con keyboard nav |
| UnionTable | 9/10 | Tabla selección uniones con keyboard nav |
| SpoolFilterPanel | 8/10 | Modal filtros NV + TAG |
| SpoolSelectionFooter | 7/10 | Footer para P4 con contador |
| BatchLimitModal | 7/10 | Alert batch limit exceeded |

**Lib (7 archivos):**
- `api.ts` — Fetch nativo, ~15 endpoints, ApiError class
- `context.tsx` — React Context (selectedWorker, selectedOperation, accion, selectedTipo, selectedSpool(s), selectedUnions, pulgadasCompletadas, batchResults)
- `error-classifier.ts` — Clasifica ApiError por status → userMessage + shouldRetry
- `operation-config.ts` — OPERATION_WORKFLOWS, OPERATION_ICONS, OPERATION_TO_ROLES, OPERATION_TITLES
- `spool-selection-utils.ts` — getPageTitle, getEmptyMessage, MAX_BATCH_SELECTION
- `types.ts` — Worker, Spool, Union, Request/Response interfaces
- `version.ts` — detectSpoolVersion (v3.0 vs v4.0 por total_uniones)
- `hooks/useDebounce.ts` — Debounce hook

**Config:**
- Next.js 14, React 18, TypeScript strict, Tailwind CSS
- Palette: zeues-navy (#001F3F), zeues-orange (#FF5B00), zeues-stone, zeues-beige
- Breakpoints: desktop (default), tablet (768-1280px), narrow (≤640px)
- font-mono everywhere, border-4, h-16+ touch targets
- Path alias: `@/*` → `./*`

**Estado:** React Context puro (no Redux/Zustand). SessionStorage para union selections.

### El TODO completo está en `zeues-frontend/TODO-v5-restructuring.md`

---

**Estoy listo para recibir la nueva estructura. Dame el spec de las nuevas pantallas y la lógica, y planificamos la reestructuración.**
