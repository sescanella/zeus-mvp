# ZEUES Backend - Deploy en Producción

**Status:** ✅ DEPLOYED & FUNCTIONAL
**Fecha:** 10 Nov 2025
**Plataforma:** Railway

---

## 🚀 URL de Producción

**API Base URL:**
```
https://zeues-backend-mvp-production.up.railway.app
```

**OpenAPI Docs:**
```
https://zeues-backend-mvp-production.up.railway.app/api/docs
```

**ReDoc:**
```
https://zeues-backend-mvp-production.up.railway.app/api/redoc
```

---

## ✅ Endpoints Verificados

### Health Check
```bash
curl https://zeues-backend-mvp-production.up.railway.app/api/health
```
**Response:**
```json
{
  "status": "healthy",
  "timestamp": "2025-11-10T23:55:38.143566Z",
  "environment": "production",
  "sheets_connection": "ok",
  "version": "1.0.0"
}
```

### Workers
```bash
curl https://zeues-backend-mvp-production.up.railway.app/api/workers
```
✅ Retorna lista de trabajadores activos desde Google Sheets

### Spools
```bash
curl "https://zeues-backend-mvp-production.up.railway.app/api/spools/iniciar?operacion=ARM"
```
✅ Retorna spools disponibles para iniciar ARM

```bash
curl "https://zeues-backend-mvp-production.up.railway.app/api/spools/completar?operacion=ARM&worker_nombre=Juan%20Pérez"
```
✅ Retorna spools de Juan Pérez para completar ARM

### Actions
```bash
curl -X POST https://zeues-backend-mvp-production.up.railway.app/api/iniciar-accion \
  -H "Content-Type: application/json" \
  -d '{
    "worker_nombre": "Juan Pérez",
    "operacion": "ARM",
    "tag_spool": "SP-001"
  }'
```
✅ Inicia acción de armado

```bash
curl -X POST https://zeues-backend-mvp-production.up.railway.app/api/completar-accion \
  -H "Content-Type: application/json" \
  -d '{
    "worker_nombre": "Juan Pérez",
    "operacion": "ARM",
    "tag_spool": "SP-001"
  }'
```
✅ Completa acción de armado

---

## 🔧 Configuración Railway

### Variables de Entorno (6)

| Variable | Valor | Descripción |
|----------|-------|-------------|
| `GOOGLE_CLOUD_PROJECT_ID` | `zeus-mvp` | ID del proyecto Google Cloud |
| `GOOGLE_SHEET_ID` | `11v8fD5Shn0RSzDceZRvXhE9z4RIOBmPA9lpH5_zF-wM` | Sheet de TESTING |
| `ENVIRONMENT` | `production` | Ambiente de ejecución |
| `CACHE_TTL_SECONDS` | `300` | TTL cache (5 minutos) |
| `ALLOWED_ORIGINS` | `http://localhost:3000,http://localhost:3001` | CORS origins |
| `GOOGLE_APPLICATION_CREDENTIALS_JSON` | `{...}` | Service Account JSON completo |

### Start Command
```
uvicorn backend.main:app --host 0.0.0.0 --port $PORT
```

### Deploy Method
- **Actual:** Manual via `railway up --service zeues-backend-mvp`
- **Recomendado:** Conectar GitHub para deploys automáticos

---

## 📝 Archivos de Deploy

### Creados Durante Deploy
1. **`Procfile`** - Start command (Railway no lo usa actualmente)
2. **`railway.json`** - Configuración Railway
3. **`.github/workflows/backend.yml`** - CI/CD GitHub Actions
4. **`backend/README.md`** - Documentación del backend
5. **`.env.production.example`** - Template variables de entorno
6. **`scripts/setup_railway_vars.sh`** - Helper script

### Modificados Para Deploy
1. **`backend/config.py`**:
   - Agregado `GOOGLE_APPLICATION_CREDENTIALS_JSON`
   - Método `get_credentials_dict()` con prioridad env var > archivo

2. **`backend/repositories/sheets_repository.py`**:
   - Cambiado `from_service_account_file()` → `from_service_account_info()`
   - Soporte para credenciales desde variable de entorno

---

## 🐛 Problemas Resueltos Durante Deploy

### Bug #1: No Start Command
**Error:** "No start command was found"
**Causa:** Railway no detectó Procfile automáticamente
**Solución:** Configurar Start Command manualmente en Settings > Deploy

### Bug #2: Credenciales No Encontradas
**Error:** "Archivo de credenciales no encontrado: /app/credenciales/..."
**Causa:** Backend buscaba archivo físico que no existe en Railway
**Solución:**
- Agregar variable `GOOGLE_APPLICATION_CREDENTIALS_JSON` con JSON completo
- Modificar código para usar `from_service_account_info()` con diccionario

### Bug #3: Deploys No Automáticos
**Issue:** Cambios en GitHub no se deployaban automáticamente
**Causa:** Railway no está conectado al repositorio GitHub
**Workaround:** Deploy manual con `railway up --service zeues-backend-mvp`
**Solución futura:** Conectar GitHub en Settings > Source > Connect Repo

---

## 🔄 Comandos Deploy

### Deploy Manual (Actual)
```bash
# Desde el directorio raíz del proyecto
railway up --service zeues-backend-mvp
```

### Ver Logs
```bash
railway logs --service zeues-backend-mvp
```

### Ver Status
```bash
railway status
```

### Listar Servicios
```bash
railway list
```

---

## 📊 Métricas de Producción

### Performance
- ✅ Latencia promedio: ~200ms (health check)
- ✅ Conexión Google Sheets: OK
- ✅ Cache activo: 300s TTL

### Testing
- ✅ 123 tests unitarios passing (local)
- ✅ 10 tests E2E passing (local)
- ✅ Coverage: 83% average, 95% ActionService

### Integración
- ✅ Google Sheets API conectado
- ✅ Service Account autenticado
- ✅ Sheet de TESTING: 292 spools, 5 trabajadores

---

## 🔐 Seguridad

### Credenciales
- ✅ Archivo `credenciales/*.json` en `.gitignore`
- ✅ Credenciales en variable de entorno Railway (no en código)
- ✅ Service Account con permisos mínimos (Sheets + Drive)

### CORS
- ⚠️ Actualizar `ALLOWED_ORIGINS` cuando frontend esté deployado
- Cambiar de localhost a URL de producción (ej: Vercel)

---

## 📌 Próximos Pasos

### Inmediato
- [ ] Conectar GitHub para deploys automáticos
- [ ] Actualizar `ALLOWED_ORIGINS` con URL del frontend
- [ ] Configurar monitoring/alertas en Railway

### Corto Plazo
- [ ] Migrar a Google Sheet de PRODUCCIÓN (cuando MVP esté 100% validado)
- [ ] Configurar dominio personalizado (opcional)
- [ ] Implementar rate limiting

### Largo Plazo
- [ ] Configurar CI/CD pipeline completo con GitHub Actions
- [ ] Agregar tests de integración en pipeline
- [ ] Implementar staging environment

---

## 🆘 Troubleshooting

### Si el backend no responde:
1. Verificar logs: `railway logs --service zeues-backend-mvp`
2. Verificar health check: `curl .../api/health`
3. Verificar variables de entorno en Railway dashboard

### Si Google Sheets falla:
1. Verificar que `GOOGLE_APPLICATION_CREDENTIALS_JSON` tiene el JSON completo
2. Verificar que Service Account tiene permisos en el Sheet
3. Verificar que `GOOGLE_SHEET_ID` es correcto

### Si endpoints retornan 503:
1. Verificar conexión a Google Sheets
2. Verificar logs para ver error específico
3. Verificar quotas de Google Sheets API

---

## 📚 Documentación Adicional

- **Backend completo:** `proyecto-backend.md`
- **API Docs:** `proyecto-backend-api.md`
- **Google Resources:** `docs/GOOGLE-RESOURCES.md`
- **Setup Railway:** `RAILWAY-ENV-SETUP.md`

---

**Última actualización:** 10 Nov 2025 - 23:55 UTC
**Deploy ID:** ef935f5
**Status:** ✅ PRODUCTION READY
