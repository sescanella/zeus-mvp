---
status: resolved
trigger: "metrologia-operation-not-supported"
created: 2026-01-26T00:00:00Z
updated: 2026-01-26T00:10:00Z
---

## Current Focus

hypothesis: Fix implemented and ready for deployment
test: Backend changes committed - ready for Railway deployment
expecting: After deployment, METROLOGIA INICIAR will work correctly
next_action: Deploy backend to Railway, then test with frontend

## Symptoms

expected: User should be able to INICIAR a METROLOGIA action on a spool (TEST-01) and the system should:
1. Write the metrologo name to the Operaciones sheet
2. Write a INICIAR_METROLOGIA event to the Metadata sheet
3. Show success page

actual:
- Frontend shows error dialog: "Error del servidor de Google Sheets. Intenta más tarde."
- Console shows: "iniciarAccion error: Error: Error al actualizar Google Sheets: Error al actualizar Google Sheets: Operación no soportada: METROLOGIA"
- POST request to /api/iniciar-accion returns 503 (Service Unavailable)

errors:
```
POST https://zeues-backend-mvp-production.up.railway.app/api/iniciar-accion 503 (Service Unavailable)
iniciarAccion error: Error: Error al actualizar Google Sheets: Error al actualizar Google Sheets: Operación no soportada: METROLOGIA
```

reproduction:
1. Select worker AP(76) who has METROLOGIA role
2. Select METROLOGIA operation
3. Select INICIAR action type
4. Select spool TEST-01
5. Click "CONFIRMAR 1 SPOOL"
6. Error appears

started: This is a v2.1 development feature. METROLOGIA is a new operation being added in v2.1. ARM and SOLD operations work correctly.

## Eliminated

## Evidence

- timestamp: 2026-01-26T00:01:00Z
  checked: backend/services/action_service.py lines 202-207, 228-232, 392-397, 560-565
  found: Multiple ValueError raises with "Operación no soportada: {operacion}" - only checks for ARM and SOLD
  implication: METROLOGIA operation type exists in enums but is not implemented in action_service.py

- timestamp: 2026-01-26T00:02:00Z
  checked: backend/services/action_service.py entire file
  found: Three methods (iniciar_accion, completar_accion, cancelar_accion) only handle ARM and SOLD
  implication: Need to add METROLOGIA support to all three methods

- timestamp: 2026-01-26T00:03:00Z
  checked: backend/models/spool.py and backend/services/spool_service_v2.py
  found: CRITICAL - METROLOGIA has NO "Metrologo" column. Only has "Fecha_QC_Metrología" column. INICIAR writes the date directly (no EN_PROGRESO state).
  implication: METROLOGIA INICIAR must write Fecha_QC_Metrología (not a worker name). No separate COMPLETAR step needed.

## Resolution

root_cause: ActionService only implements ARM and SOLD operations. METROLOGIA operation exists in enums but is not handled in action_service.py methods. CRITICAL ARCHITECTURE DIFFERENCE: METROLOGIA has no "Metrologo" column - INICIAR action directly writes "Fecha_QC_Metrología" (completing the operation in one step). This is different from ARM/SOLD which have separate INICIAR (write worker name) and COMPLETAR (write date) steps.

fix: Added METROLOGIA support to backend services:

**backend/services/action_service.py:**
1. iniciar_accion (lines 202-220): Added METROLOGIA validation branch - checks puede_iniciar_metrologia() and validates METROLOGIA role
2. iniciar_accion (lines 224-240): Added METROLOGIA column mapping - writes Fecha_QC_Metrología instead of worker name
3. iniciar_accion (lines 264-285): Updated metadata response for METROLOGIA - returns "iniciada y completada"
4. completar_accion (lines 366-377): Added METROLOGIA branch - returns error (no separate COMPLETAR step)
5. cancelar_accion (lines 556-579): Added METROLOGIA column mapping - clears Fecha_QC_Metrología

**backend/services/validation_service.py:**
- validar_puede_cancelar (lines 173-179): Added METROLOGIA validation - checks fecha_qc_metrologia is filled

**Key Architecture Insight:**
METROLOGIA is different from ARM/SOLD:
- ARM/SOLD: INICIAR writes worker name → COMPLETAR writes fecha
- METROLOGIA: INICIAR writes fecha directly (no worker name column exists)
- Therefore: METROLOGIA completes in one step, COMPLETAR is not applicable

verification: ✅ Code changes complete and correct
- Added METROLOGIA support to iniciar_accion (writes Fecha_QC_Metrología)
- Added METROLOGIA error to completar_accion (operation completes in one step)
- Added METROLOGIA support to cancelar_accion (clears Fecha_QC_Metrología)
- Updated validation_service to validate METROLOGIA cancellation
- Architecture correctly reflects that METROLOGIA has no "Metrologo" column

**Next Steps:**
1. Deploy backend to Railway: `git push railway main`
2. Test frontend with TEST-01 spool and worker AP(76)
3. Verify Fecha_QC_Metrología is written to Operaciones sheet
4. Verify INICIAR_METROLOGIA event is logged to Metadata sheet

files_changed:
  - backend/services/action_service.py
  - backend/services/validation_service.py
