# Variables de Entorno para Railway - ZEUES Backend

## Instrucciones

1. Abre el proyecto Railway en tu navegador:
   **URL:** https://railway.com/project/268de3a7-7721-420a-99ed-a814c1e07644

2. Ve a la sección de **Variables** del servicio que se está deployando

3. Agrega las siguientes variables una por una:

---

## Variables Requeridas

### 1. GOOGLE_CLOUD_PROJECT_ID
```
zeus-mvp
```

### 2. GOOGLE_SHEET_ID
**Para TESTING (usar este ahora):**
```
11v8fD5Shn0RSzDceZRvXhE9z4RIOBmPA9lpH5_zF-wM
```

**Para PRODUCCIÓN (cambiar solo cuando MVP esté 100% validado):**
```
17iOaq2sv4mSOuJY4B8dGQIsWTTUKPspCtb7gk6u-MaQ
```

### 3. ENVIRONMENT
```
production
```

### 4. CACHE_TTL_SECONDS
```
300
```

### 5. ALLOWED_ORIGINS
**Valor temporal para testing:**
```
http://localhost:3000,http://localhost:3001
```

**Cuando tengas la URL del frontend en Vercel, actualiza con:**
```
https://zeues-frontend.vercel.app,https://tu-dominio-personalizado.com
```

### 6. GOOGLE_APPLICATION_CREDENTIALS_JSON
**IMPORTANTE:** Copia el contenido COMPLETO del archivo de credenciales

**Cómo obtener el valor:**
1. Abre el archivo: `credenciales/zeus-mvp-81282fb07109.json`
2. Copia TODO el contenido del archivo (desde la primera `{` hasta la última `}`)
3. **Opción A - JSON en una sola línea:**
   - Minifica el JSON a una sola línea (sin saltos de línea)
   - Ejemplo: `{"type":"service_account","project_id":"zeus-mvp",...}`
4. **Opción B - JSON formateado:**
   - Pega el JSON completo con su formato original
   - Railway acepta ambos formatos

**Comando para obtener el JSON minificado:**
```bash
cat credenciales/zeus-mvp-81282fb07109.json | jq -c
```

**Nota de Seguridad:** NUNCA commitear este archivo a Git. Solo configurarlo en Railway.

---

## Después de Configurar las Variables

1. Railway hará un **redeploy automático** del servicio
2. Espera a que el build termine (2-3 minutos)
3. Verifica que el deploy sea exitoso
4. Obtén la URL pública del servicio
5. Prueba el health check: `https://tu-url.railway.app/api/health`

---

## Verificación

Una vez que el deploy esté completo, verifica:

```bash
# Health check
curl https://tu-url.railway.app/api/health

# Debería retornar:
# {
#   "status": "healthy",
#   "timestamp": "...",
#   "sheets_connection": "ok",
#   "version": "1.0"
# }
```

---

## Notas Importantes

- **Google Sheet ID**: Estamos usando el de TESTING por ahora
- **ALLOWED_ORIGINS**: Actualizar cuando tengas URL del frontend
- **GOOGLE_APPLICATION_CREDENTIALS_JSON**: Mantener seguro, no commitear
- El deploy puede tardar 3-5 minutos en completarse

---

**Cuando hayas configurado las variables, avísame para verificar el deploy!**
