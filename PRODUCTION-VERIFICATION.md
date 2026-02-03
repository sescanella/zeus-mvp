# Verificación en Producción - v4.0 Version Detection Fix

**Deploy Date:** 2026-02-03
**Commit:** `e0b0f29` - fix: add total_uniones field for v4.0 spool version detection

---

## 🚀 Deploy Status

### ✅ Git Push Completado
```bash
Commit: e0b0f29
Branch: main
Status: Pushed to GitHub successfully
```

### 🔄 Auto-Deploy en Progreso

**Railway (Backend):**
- Repository: `sescanella/zeus-mvp`
- Branch: `main`
- Auto-deploy: ✅ Configurado (trigger on push)
- URL: https://zeues-backend-mvp-production.up.railway.app
- Dashboard: https://railway.app (check deployment logs)

**Vercel (Frontend):**
- Repository: `sescanella/zeus-mvp`
- Branch: `main`
- Auto-deploy: ✅ Configurado (trigger on push)
- URL: https://zeues-frontend.vercel.app
- Dashboard: https://vercel.com/dashboard (check deployment status)

---

## ⏱️ Tiempo Estimado de Deploy

- **Railway:** ~3-5 minutos
- **Vercel:** ~2-3 minutos

**Total:** ~5-8 minutos desde el push

---

## 🔍 Pasos de Verificación en Producción

### 1. Verificar Backend Deployado

**Espera 3-5 minutos después del push, luego:**

```bash
# Test health endpoint
curl -s "https://zeues-backend-mvp-production.up.railway.app/health"

# Expected: {"status": "healthy"}
```

**Si responde correctamente, verificar endpoint de spools:**

```bash
curl -s "https://zeues-backend-mvp-production.up.railway.app/api/spools/iniciar?operacion=ARM" | \
  python3 -c "
import json, sys
data = json.load(sys.stdin)
test02 = [s for s in data.get('spools', []) if s['tag_spool'] == 'TEST-02']
if test02:
    print('✅ TEST-02 found')
    print(f\"   total_uniones: {test02[0].get('total_uniones', 'MISSING')}\")
    print(f\"   ot: {test02[0].get('ot', 'MISSING')}\")
else:
    print('❌ TEST-02 not found in response')
"
```

**Resultado Esperado:**
```
✅ TEST-02 found
   total_uniones: 12
   ot: ...
```

**Validación:**
- ✅ Campo `total_uniones` presente
- ✅ Valor correcto: `12` (matches Google Sheets)
- ✅ Campo `ot` presente

---

### 2. Verificar Frontend Deployado

**Espera 2-3 minutos después del push, luego:**

**Abrir en navegador:**
```
https://zeues-frontend.vercel.app
```

**Navegación:**
1. Seleccionar trabajador (ej: MR)
2. Seleccionar operación: **ARMADO**
3. Seleccionar tipo: **INICIAR**

**Buscar TEST-02:**
- NV: (vacío)
- TAG: `TEST-02`

**Resultado Esperado:**

```
┌─────────────────────────────────────────────┐
│ 🟢 1 spool v4.0 (con uniones), X v3.0      │  ← Mensaje verde
└─────────────────────────────────────────────┘

SEL  TAG SPOOL     VERSION    NV
───────────────────────────────────────────────
☐    TEST-02       v4.0 🟢    ...    ← Badge verde
```

**Validación Visual:**
- ✅ TEST-02 muestra badge **verde "v4.0"**
- ✅ Mensaje informativo en la parte superior
- ✅ NO aparece "DETECTANDO VERSIONES..." loading

---

### 3. Verificar Performance (Network Tab)

**Abrir Chrome DevTools (F12) → Network tab:**

**Verificar requests:**

```
GET /api/spools/iniciar?operacion=ARM    ← Solo 1 request
```

**❌ NO debe haber:**
```
GET /api/v4/uniones/TEST-02/metricas     ← NO debe existir
GET /api/v4/uniones/MK-1335.../metricas   ← NO debe existir
```

**Validación:**
- ✅ Solo 1 request a backend
- ✅ NO hay N queries a `/api/v4/uniones/{tag}/metricas`
- ✅ Performance mejorada (~150-200ms × N spools eliminados)

---

### 4. Verificar en Diferentes Navegadores

**Probar en:**
- ✅ Chrome (Desktop)
- ✅ Safari (Desktop)
- ✅ Mobile (iOS/Android)

**En cada navegador:**
1. Navegar a TEST-02
2. Verificar badge verde "v4.0"
3. Verificar que NO hay loading "DETECTANDO VERSIONES..."

---

## 📊 Checklist de Aceptación Producción

### Backend
- [ ] Railway deploy completado exitosamente
- [ ] Health endpoint responde: `{"status": "healthy"}`
- [ ] `/api/spools/iniciar` devuelve `total_uniones` para TEST-02
- [ ] Valor correcto: `total_uniones: 12`
- [ ] Campo `ot` presente

### Frontend
- [ ] Vercel deploy completado exitosamente
- [ ] App carga sin errores en https://zeues-frontend.vercel.app
- [ ] TEST-02 muestra badge verde "v4.0"
- [ ] Mensaje informativo: "N spools v4.0 (con uniones), M v3.0"
- [ ] NO aparece "DETECTANDO VERSIONES..."

### Performance
- [ ] Solo 1 request a `/api/spools/iniciar` (verificado en Network tab)
- [ ] NO hay requests a `/api/v4/uniones/{tag}/metricas`
- [ ] Load time < 1 segundo para lista de spools

### Cross-Browser
- [ ] Funciona correctamente en Chrome
- [ ] Funciona correctamente en Safari
- [ ] Funciona correctamente en Mobile

---

## 🔧 Troubleshooting Producción

### Backend no responde

**Síntoma:** Health endpoint retorna error o timeout

**Diagnóstico:**
1. Ir a Railway Dashboard: https://railway.app
2. Verificar logs de deployment
3. Buscar errores en startup

**Soluciones comunes:**
- Verificar que deployment completó exitosamente
- Check Railway logs para errores de startup
- Verificar que variables de entorno están configuradas
- Restart service en Railway dashboard si es necesario

---

### Frontend muestra v3.0 para TEST-02

**Síntoma:** Badge muestra gris "v3.0" en lugar de verde "v4.0"

**Diagnóstico:**
1. Abrir DevTools → Network tab
2. Ver response de `/api/spools/iniciar`
3. Buscar TEST-02 en response
4. Verificar si `total_uniones` está presente

**Si `total_uniones` está ausente:**
- Problema en backend deployment
- Verificar Railway logs
- Verificar que último commit está deployado

**Si `total_uniones` está presente pero badge sigue v3.0:**
- Problema en frontend deployment
- Clear browser cache (Cmd+Shift+R)
- Verificar Vercel deployment completó
- Verificar que último commit está deployado

---

### Deploy de Railway falla

**Síntoma:** Railway deployment shows error

**Diagnóstico:**
1. Check Railway logs
2. Buscar errores de build o startup
3. Verificar dependencies en requirements.txt

**Soluciones:**
- Verificar que tests pasan localmente: `pytest backend/tests/unit/`
- Verificar que requirements.txt está actualizado
- Re-deploy manualmente desde Railway dashboard

---

### Deploy de Vercel falla

**Síntoma:** Vercel deployment shows error

**Diagnóstico:**
1. Check Vercel logs
2. Buscar errores de TypeScript o build
3. Verificar dependencies en package.json

**Soluciones:**
- Verificar que build pasa localmente: `npm run build`
- Verificar que TypeScript pasa: `npx tsc --noEmit`
- Re-deploy manualmente desde Vercel dashboard

---

## 📸 Screenshots de Validación

**Tomar screenshots de:**

1. **Backend Response:**
   ```bash
   curl -s "https://zeues-backend-mvp-production.up.railway.app/api/spools/iniciar?operacion=ARM" | \
     jq '.spools[] | select(.tag_spool == "TEST-02")'
   ```

2. **Frontend Badge:**
   - TEST-02 con badge verde "v4.0"

3. **Network Tab:**
   - Solo 1 request visible (sin N queries)

4. **Railway Deployment:**
   - Status: Success

5. **Vercel Deployment:**
   - Status: Success

---

## ✅ Criterios de Éxito en Producción

**Deploy es exitoso si:**

1. ✅ Railway deployment: **Success**
2. ✅ Vercel deployment: **Success**
3. ✅ Backend health check: **Healthy**
4. ✅ TEST-02 badge: **Verde "v4.0"**
5. ✅ Performance: **1 query (no N queries)**
6. ✅ Cross-browser: **Funciona en todos**

**Métricas de performance:**
- Before: N+1 queries (~400ms × N spools)
- After: 1 query (~200-300ms total)
- Improvement: ~99% reduction in API calls for version detection

---

## 📝 URLs de Producción

**Backend API:**
- Base: https://zeues-backend-mvp-production.up.railway.app
- Health: https://zeues-backend-mvp-production.up.railway.app/health
- Docs: https://zeues-backend-mvp-production.up.railway.app/docs
- Spools: https://zeues-backend-mvp-production.up.railway.app/api/spools/iniciar?operacion=ARM

**Frontend:**
- App: https://zeues-frontend.vercel.app
- Selección: https://zeues-frontend.vercel.app/seleccionar-spool

**Dashboards:**
- Railway: https://railway.app
- Vercel: https://vercel.com/dashboard
- GitHub: https://github.com/sescanella/zeus-mvp/commit/e0b0f29

---

## 🎯 Next Steps After Verification

1. ✅ Verificar que TEST-02 muestra "v4.0" en producción
2. ✅ Monitor Railway logs por 10-15 minutos (check for errors)
3. ✅ Test con usuarios reales (si es posible)
4. ✅ Verificar que spools v3.0 existentes siguen funcionando
5. ✅ Update PROJECT.md con deploy info (si es necesario)

---

**Documento generado:** 2026-02-03
**Deploy commit:** e0b0f29
**Status:** ⏳ Waiting for Railway + Vercel auto-deploy (3-8 minutes)
