# Pasos de Verificación Manual - Fix v4.0 Detección de Versión

**Fecha:** 2026-02-03
**Issue:** TEST-02 mostraba "v3.0" en lugar de "v4.0" a pesar de tener 12 uniones

---

## ✅ Cambios Implementados

### Backend
1. **Modelo Spool** - Agregado campo `total_uniones: Optional[int]`
2. **SpoolServiceV2** - Parseo de columna 68 (`Total_Uniones`) y columna 2 (`OT`)
3. **SheetsRepository** - Parseo de `Total_Uniones` en `get_all_spools()`

### Frontend
1. **Optimización** - Eliminado loop de N queries a `/api/v4/uniones/{tag}/metricas`
2. **Detección inline** - Versión detectada desde `spool.total_uniones` (O(1))
3. **UI mejorada** - Mensaje diferenciado para mezcla v3.0/v4.0

### Tests
- **7 unit tests** agregados en `backend/tests/unit/test_spool_version_detection.py`
- **100% passing**

---

## 🔍 Pasos de Verificación Backend

### 1. Iniciar Backend

```bash
cd /Users/sescanella/Proyectos/KM/ZEUES-by-KM
source venv/bin/activate
PYTHONPATH=/Users/sescanella/Proyectos/KM/ZEUES-by-KM uvicorn main:app --reload --port 8000
```

Espera hasta ver:
```
INFO:     Uvicorn running on http://127.0.0.1:8000 (Press CTRL+C to quit)
INFO:     Started reloader process using WatchFiles
INFO:     Started server process
INFO:     Application startup complete.
```

### 2. Verificar TEST-02 en endpoint

**Terminal 2:**
```bash
curl -s "http://localhost:8000/api/spools/iniciar?operacion=ARM" | \
  python3 -c "
import json, sys
data = json.load(sys.stdin)
test02 = [s for s in data.get('spools', []) if s['tag_spool'] == 'TEST-02']
if test02:
    print(json.dumps(test02[0], indent=2))
else:
    print('TEST-02 not found')
"
```

**Resultado Esperado:**
```json
{
  "tag_spool": "TEST-02",
  "ot": "...",
  "nv": "...",
  "total_uniones": 12,    ← ✅ CAMPO PRESENTE
  "arm": 0,
  "sold": 0,
  ...
}
```

**Validación:**
- ✅ Campo `total_uniones` presente
- ✅ Valor `12` (matches Google Sheets column 68)
- ✅ Campo `ot` presente (v4.0 FK)

### 3. Verificar otros spools v3.0

```bash
curl -s "http://localhost:8000/api/spools/iniciar?operacion=ARM" | \
  python3 -c "
import json, sys
data = json.load(sys.stdin)
for spool in data.get('spools', [])[:5]:
    print(f\"{spool['tag_spool']}: total_uniones={spool.get('total_uniones', 'MISSING')}\")
"
```

**Resultado Esperado:**
```
TEST-02: total_uniones=12           ← v4.0 spool
MK-1335-CW-25238-011: total_uniones=0    ← v3.0 spool
MK-1335-CW-25237-012: total_uniones=0    ← v3.0 spool
...
```

---

## 🖥️ Pasos de Verificación Frontend

### 1. Iniciar Frontend

**Terminal 3:**
```bash
cd /Users/sescanella/Proyectos/KM/ZEUES-by-KM/zeues-frontend
npm run dev
```

Espera hasta ver:
```
  ▲ Next.js 14.2.35
  - Local:        http://localhost:3000
  - Ready in XXXms
```

### 2. Abrir Navegador

1. Abrir Chrome DevTools (F12)
2. Ir a tab **Network**
3. Navegar a: `http://localhost:3000`
4. Seleccionar un trabajador (ej: MR)
5. Seleccionar operación: **ARMADO**
6. Seleccionar tipo interacción: **INICIAR**

### 3. Verificar Performance (1 query vs N queries)

**En Network tab, buscar:**

**✅ CORRECTO (1 query):**
```
GET /api/spools/iniciar?operacion=ARM    ← Solo esta request
```

**❌ INCORRECTO (N queries):**
```
GET /api/spools/iniciar?operacion=ARM
GET /api/v4/uniones/TEST-02/metricas     ← NO debería existir
GET /api/v4/uniones/MK-1335.../metricas   ← NO debería existir
...
```

**Validación:**
- ✅ Solo 1 request a `/api/spools/iniciar`
- ✅ NO hay requests a `/api/v4/uniones/{tag}/metricas`

### 4. Verificar Badge de Versión

**Buscar TEST-02 en la lista:**

**Campos de búsqueda:**
- NV: (dejar vacío o filtrar)
- TAG: `TEST-02`

**Resultado Esperado:**

```
┌─────────────────────────────────────────────┐
│ 🟢 1 spool v4.0 (con uniones), 0 v3.0      │  ← Mensaje verde
└─────────────────────────────────────────────┘

SEL  TAG SPOOL     VERSION    NV
───────────────────────────────────────────────
☐    TEST-02       v4.0 🟢    NV0000    ← Badge verde
```

**Si hay mezcla v3.0 y v4.0:**
```
┌─────────────────────────────────────────────┐
│ 🟢 1 spool v4.0 (con uniones), 5 v3.0      │  ← Mensaje verde
└─────────────────────────────────────────────┘

SEL  TAG SPOOL              VERSION    NV
──────────────────────────────────────────────
☐    TEST-02                v4.0 🟢    NV0000
☐    MK-1335-CW-25238-011   v3.0 ⚪    NV0001
☐    MK-1335-CW-25237-012   v3.0 ⚪    NV0001
```

**Validación:**
- ✅ TEST-02 muestra badge verde "v4.0"
- ✅ Spools v3.0 muestran badge gris "v3.0"
- ✅ Mensaje informativo en la parte superior
- ✅ NO aparece "DETECTANDO VERSIONES..." (eliminado)

### 5. Verificar Console Logs

**En Console tab:**

**✅ CORRECTO (sin errors):**
```
No errors or warnings related to version detection
```

**❌ INCORRECTO:**
```
Error detecting version for TEST-02: ...
```

---

## 🧪 Pasos de Verificación Tests

```bash
cd /Users/sescanella/Proyectos/KM/ZEUES-by-KM
source venv/bin/activate
PYTHONPATH=/Users/sescanella/Proyectos/KM/ZEUES-by-KM pytest backend/tests/unit/test_spool_version_detection.py -v
```

**Resultado Esperado:**
```
============================== test session starts ===============================
...
backend/tests/unit/test_spool_version_detection.py::TestSpoolModelV4::test_spool_model_accepts_total_uniones PASSED [ 14%]
backend/tests/unit/test_spool_version_detection.py::TestSpoolModelV4::test_spool_model_total_uniones_optional PASSED [ 28%]
backend/tests/unit/test_spool_version_detection.py::TestSpoolModelV4::test_spool_model_validates_non_negative_total_uniones PASSED [ 42%]
backend/tests/unit/test_spool_version_detection.py::TestSpoolModelV4::test_spool_model_total_uniones_zero_is_valid PASSED [ 57%]
backend/tests/unit/test_spool_version_detection.py::TestFrontendVersionDetection::test_detect_v4_spool_from_total_uniones PASSED [ 71%]
backend/tests/unit/test_spool_version_detection.py::TestFrontendVersionDetection::test_detect_v3_spool_from_zero_unions PASSED [ 85%]
backend/tests/unit/test_spool_version_detection.py::TestFrontendVersionDetection::test_detect_v3_spool_from_none_unions PASSED [100%]

=============================== 7 passed in 0.11s ================================
```

**Validación:**
- ✅ 7/7 tests passing
- ✅ No warnings relacionados a total_uniones

---

## 📦 Verificación TypeScript y Build

### TypeScript Check

```bash
cd zeues-frontend
npx tsc --noEmit
```

**Resultado Esperado:**
```
(sin output = sin errores)
```

### Production Build

```bash
npm run build
```

**Resultado Esperado:**
```
✓ Compiled successfully
✓ Linting and checking validity of types ...
✓ Generating static pages (12/12)
```

**Validación:**
- ✅ Sin errores de TypeScript
- ✅ Build exitoso
- ✅ Sin warnings relacionados a `total_uniones` o version detection

---

## 📊 Checklist de Aceptación

### Backend
- [ ] Campo `total_uniones` presente en modelo Spool
- [ ] Campo `ot` presente en modelo Spool
- [ ] Endpoint `/api/spools/iniciar` devuelve `total_uniones` para TEST-02
- [ ] Valor correcto: `total_uniones: 12` (matches Sheets col 68)
- [ ] Manejo de errores: valores inválidos defaults to `None`
- [ ] Tests unitarios: 7/7 passing

### Frontend
- [ ] TEST-02 muestra badge verde "v4.0"
- [ ] Spools v3.0 muestran badge gris "v3.0"
- [ ] Mensaje informativo: "N spools v4.0 (con uniones), M v3.0"
- [ ] NO aparece "DETECTANDO VERSIONES..."
- [ ] Performance: Solo 1 request a `/api/spools/iniciar`
- [ ] NO hay requests a `/api/v4/uniones/{tag}/metricas`
- [ ] TypeScript: Sin errores
- [ ] Build: Exitoso

### Logs
- [ ] Backend: Sin warnings sobre invalid Total_Uniones para spools existentes
- [ ] Frontend Console: Sin errores de version detection
- [ ] Network: 1 query en lugar de N queries

---

## 🔧 Troubleshooting

### Backend no devuelve `total_uniones`

**Síntoma:** Endpoint devuelve spools sin campo `total_uniones`

**Diagnóstico:**
```bash
# Verificar que cambios están en main.py
grep -n "total_uniones" backend/models/spool.py

# Verificar columna 68 en Sheets
# Abrir Google Sheets manualmente y verificar columna 68 "Total_Uniones"
```

**Solución:**
1. Verificar que backend está usando código actualizado
2. Restart backend (Ctrl+C y reiniciar)
3. Verificar que Google Sheets tiene columna 68 con header "Total_Uniones"

### Frontend sigue haciendo N queries

**Síntoma:** Network tab muestra requests a `/api/v4/uniones/{tag}/metricas`

**Diagnóstico:**
```bash
# Verificar que frontend está usando código actualizado
grep -n "getUnionMetricas" zeues-frontend/app/seleccionar-spool/page.tsx
# Debería estar SOLO en imports (línea 8), no en código ejecutado
```

**Solución:**
1. Restart frontend (Ctrl+C y `npm run dev`)
2. Clear browser cache (Cmd+Shift+R en Chrome)
3. Verificar que no hay `detectingVersions` state

### Badge sigue mostrando v3.0 para TEST-02

**Síntoma:** TEST-02 muestra badge gris "v3.0" en lugar de verde "v4.0"

**Diagnóstico:**
1. Verificar Network tab: ¿response de `/api/spools/iniciar` incluye `total_uniones: 12`?
2. Si NO: problema en backend
3. Si SÍ: problema en frontend detection logic

**Solución Backend:**
```bash
# Test endpoint manualmente
curl -s "http://localhost:8000/api/spools/iniciar?operacion=ARM" | \
  jq '.spools[] | select(.tag_spool == "TEST-02") | .total_uniones'
# Debe devolver: 12
```

**Solución Frontend:**
```typescript
// Verificar lógica en page.tsx línea ~145
const spoolsWithVersion = fetchedSpools.map(spool => ({
  ...spool,
  version: (spool.total_uniones && spool.total_uniones > 0) ? 'v4.0' as const : 'v3.0' as const
}));
```

---

## ✅ Criterios de Éxito

**La implementación es exitosa si:**

1. ✅ TEST-02 muestra badge **verde "v4.0"** en frontend
2. ✅ Backend devuelve `total_uniones: 12` en endpoint
3. ✅ Frontend hace **1 query** en lugar de N queries
4. ✅ Tests: **7/7 passing**
5. ✅ TypeScript: **sin errores**
6. ✅ Build: **exitoso**

**Performance esperada:**
- Antes: N queries (1 por spool) → ~150-200ms por spool × N spools
- Después: 1 query total → ~200-300ms para todos los spools

**Para TEST-02 con 12 uniones:**
- Antes: 1 query + 1 query `/metricas` = ~400ms
- Después: Incluido en 1 query = ~0ms adicional

---

**Documento generado:** 2026-02-03
**Autor:** Claude Code
**Issue:** Fix v4.0 spool version detection via total_uniones field
