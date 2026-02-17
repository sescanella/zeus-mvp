# Quick Task 1: Añadir pantalla P3 para Metrología con botón INSPECCIÓN

## Goal

Add P3 (tipo-interaccion) screen for Metrología with a single orange "INSPECCIÓN" button, making the flow consistent with ARM/SOLD.

**Flow change:** P1 → P2 → **P3 (INSPECCIÓN)** → P4 → Resultado → P6

## Tasks

### Task 1: Update operation-config.ts

**Files:** `zeues-frontend/lib/operation-config.ts`
**Action:** Change `METROLOGIA.skipP3` from `true` to `false`, update description
**Verify:** Config no longer skips P3 for METROLOGIA
**Done:** ✅

### Task 2: Update tipo-interaccion/page.tsx

**Files:** `zeues-frontend/app/tipo-interaccion/page.tsx`
**Action:**
- Remove Metrología bypass redirect (lines 26-30)
- Add `handleInspeccion()` handler
- Add INSPECCIÓN button block (orange, 120px, no icon)
- Exclude METROLOGIA from v4.0 INICIAR/FINALIZAR buttons
**Verify:** P3 renders INSPECCIÓN button for METROLOGIA, navigates to `/seleccionar-spool?tipo=metrologia`
**Done:** ✅

### Task 3: Verify build

**Action:** Run `tsc --noEmit`, `npm run lint`, `npm run build`
**Verify:** All pass with 0 errors
**Done:** ✅
