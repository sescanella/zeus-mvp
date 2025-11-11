# Recursos de Google - ZEUES MVP

**Sistema:** ZEUES (Sistema de Trazabilidad)
**Cliente:** Kronos Mining
**Fecha:** 7 de noviembre de 2025

---

## Google Drive - Carpeta de Trabajo

**URL:** https://drive.google.com/drive/u/0/folders/1QDlvt3OwGlYL1hClZVyZRdzIrz7qREGQ

**Nombre de la carpeta:** `kronos_mining`

**Nomenclatura:**
- **Kronos** = Empresa/Cliente
- **ZEUES** = Sistema de trazabilidad que estamos desarrollando

Esta carpeta contiene todos los archivos relacionados con el sistema ZEUES para el cliente Kronos.

### Archivos en la Carpeta

1. **`_Kronos_Registro_Piping R04`** - Google Sheets de PRODUCCIÓN (cliente Kronos)
2. **`_Kronos_Registro_Piping TESTS`** - Google Sheets de TESTING (para desarrollo de ZEUES)

---

## Google Sheets

### Sheets de TESTING (Desarrollo/MVP)

**Nombre del archivo:** `_Kronos_Registro_Piping TESTS`

**URL:** https://docs.google.com/spreadsheets/d/11v8fD5Shn0RSzDceZRvXhE9z4RIOBmPA9lpH5_zF-wM/edit?gid=1994081358#gid=1994081358

**Uso:**
- Utilizar EXCLUSIVAMENTE durante el desarrollo del MVP
- Todas las pruebas de integración con Google Sheets API
- Datos de prueba y validaciones
- Entrenamiento y demos

**Configuración:**
- Debe tener la estructura definida en `ADMIN-configuracion-sheets.md`
- Compartir con Service Account para testing
- Datos de trabajadores y spools de prueba

---

### Sheets de PRODUCCIÓN (Oficial)

**Nombre del archivo:** `_Kronos_Registro_Piping R04`

**URL:** https://docs.google.com/spreadsheets/d/17iOaq2sv4mSOuJY4B8dGQIsWTTUKPspCtb7gk6u-MaQ/edit?gid=1994081358#gid=1994081358

⚠️ **IMPORTANTE - NO UTILIZAR HASTA QUE EL MVP ESTÉ 100% FUNCIONAL**

**Uso:**
- SOLO cuando el sistema esté completamente probado y validado
- Datos reales de producción
- Cambio se realizará mediante actualización de variable de entorno

**Criterios para migrar a producción:**
- ✅ Todas las pruebas end-to-end pasadas exitosamente
- ✅ Validación completa con usuarios finales en Sheets de testing
- ✅ Sin errores durante 2 días consecutivos de uso en testing
- ✅ Aprobación del equipo de administración
- ✅ Backup del Sheets de producción realizado

---

## Google Cloud Platform

### Proyecto Configurado

**Nombre del Proyecto:** `zeus-mvp`
**Fecha de creación:** 7 de noviembre de 2025
**Estado:** Activo

### Service Account

**Nombre:** `zeus-mvp`
**Email:** `zeus-mvp@zeus-mvp.iam.gserviceaccount.com`
**Estado:** Habilitado
**Clave creada:** 7 nov 2025
**Archivo JSON:** `zeus-mvp-81282fb0710902ac73ea82e1c43550cea2dabe05.json`

⚠️ **IMPORTANTE:** El archivo JSON contiene credenciales privadas. NO commitear a GitHub.

### APIs Habilitadas

- ✅ Google Sheets API v4

---

## Configuración de Variables de Entorno

### Para Desarrollo (.env.local)
```env
# Google Cloud Project
GOOGLE_CLOUD_PROJECT_ID=zeus-mvp

# Google Sheets - TESTING
GOOGLE_SHEET_ID=11v8fD5Shn0RSzDceZRvXhE9z4RIOBmPA9lpH5_zF-wM

# Service Account (copiar del archivo JSON descargado)
GOOGLE_SERVICE_ACCOUNT_EMAIL=zeus-mvp@zeus-mvp.iam.gserviceaccount.com
GOOGLE_PRIVATE_KEY="-----BEGIN PRIVATE KEY-----\n...\n-----END PRIVATE KEY-----\n"

# Configuración de Hojas
HOJA_OPERACIONES_NOMBRE=Operaciones
HOJA_TRABAJADORES_NOMBRE=Trabajadores

# Aplicación
NODE_ENV=development
NEXT_PUBLIC_API_URL=http://localhost:3000
CACHE_TTL_SECONDS=300
```

### Para Producción (.env.production)
```env
# Google Cloud Project
GOOGLE_CLOUD_PROJECT_ID=zeus-mvp

# Google Sheets - PRODUCCIÓN (cambiar solo cuando MVP esté 100% validado)
GOOGLE_SHEET_ID=17iOaq2sv4mSOuJY4B8dGQIsWTTUKPspCtb7gk6u-MaQ

# Service Account (mismo que desarrollo)
GOOGLE_SERVICE_ACCOUNT_EMAIL=zeus-mvp@zeus-mvp.iam.gserviceaccount.com
GOOGLE_PRIVATE_KEY="-----BEGIN PRIVATE KEY-----\n...\n-----END PRIVATE KEY-----\n"

# Configuración de Hojas
HOJA_OPERACIONES_NOMBRE=Operaciones
HOJA_TRABAJADORES_NOMBRE=Trabajadores

# Aplicación
NODE_ENV=production
NEXT_PUBLIC_API_URL=https://zeues-mvp.vercel.app
CACHE_TTL_SECONDS=300
```

**Instrucciones para obtener GOOGLE_PRIVATE_KEY:**
1. Abre el archivo JSON descargado: `zeus-mvp-81282fb0710902ac73ea82e1c43550cea2dabe05.json`
2. Busca el campo `"private_key"`
3. Copia TODO el contenido (incluyendo `-----BEGIN PRIVATE KEY-----` y `-----END PRIVATE KEY-----`)
4. Pégalo en el `.env.local` entre comillas dobles
5. Asegúrate de mantener los caracteres `\n` (saltos de línea)

---

## Checklist de Permisos

### Sheets de Testing
- [ ] Compartido con Service Account (Editor)
- [ ] Estructura de columnas estandarizada
- [ ] Hoja "Trabajadores" creada y poblada
- [ ] Hoja "Operaciones" con spools de prueba
- [ ] Permisos de lectura para equipo técnico

### Sheets de Producción
- [ ] Backup realizado antes de compartir
- [ ] Compartido con Service Account (Editor) - SOLO cuando MVP esté listo
- [ ] Estructura validada contra Sheets de testing
- [ ] Datos históricos preservados
- [ ] Plan de rollback definido

---

## Extracción de IDs de Sheets

Para extraer el ID de un Google Sheets desde su URL:

```
https://docs.google.com/spreadsheets/d/[SPREADSHEET_ID]/edit...
                                        ^^^^^^^^^^^^^^^^
```

**Sheets Testing ID:** `11v8fD5Shn0RSzDceZRvXhE9z4RIOBmPA9lpH5_zF-wM`
**Sheets Producción ID:** `17iOaq2sv4mSOuJY4B8dGQIsWTTUKPspCtb7gk6u-MaQ`

---

## Notas de Seguridad

1. **Nunca commitear** las credenciales del Service Account al repositorio
2. **Usar variables de entorno** para todas las configuraciones sensibles
3. **Mantener las credenciales** solo en:
   - `.env.local` (desarrollo, en .gitignore)
   - Vercel/plataforma de deployment (producción)
   - Documentación física segura del equipo
4. **Rotar credenciales** si hay sospecha de compromiso

---

## Changelog

### 7 de noviembre de 2025 - v1.2
- ✅ Agregada información del proyecto Google Cloud: `zeus-mvp`
- ✅ Agregada información de Service Account completa
- ✅ Email de Service Account: `zeus-mvp@zeus-mvp.iam.gserviceaccount.com`
- ✅ Archivo JSON específico documentado
- ✅ Variables de entorno actualizadas con datos reales
- ✅ Instrucciones para extraer GOOGLE_PRIVATE_KEY del JSON

### 7 de noviembre de 2025 - v1.1
- Agregados nombres específicos de archivos del Drive
- Agregado nombre de carpeta: `kronos_mining`
- Agregados nombres de Sheets: `_Kronos_Registro_Piping R04` y `_Kronos_Registro_Piping TESTS`
- Aclarada nomenclatura: Kronos = Cliente/Empresa, ZEUES = Sistema

### 7 de noviembre de 2025 - v1.0
- Creación inicial del documento
- Configuración de URLs de Google Drive y Sheets
- Definición de variables de entorno
- Checklist de permisos

---

**Última actualización:** 7 de noviembre de 2025 - 16:30
