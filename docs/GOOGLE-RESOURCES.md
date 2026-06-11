# Recursos de Google - ZEUES MVP

**Sistema:** ZEUES (Sistema de Trazabilidad)
**Cliente:** Kronos Mining
**Fecha:** 22 de mayo de 2026

---

## Google Drive - Carpeta de Trabajo

**URL:** https://drive.google.com/drive/u/0/folders/1QDlvt3OwGlYL1hClZVyZRdzIrz7qREGQ

**Nombre de la carpeta:** `kronos_mining`

**Nomenclatura:**
- **Kronos** = Empresa/Cliente
- **ZEUES** = Sistema de trazabilidad que estamos desarrollando

Esta carpeta contiene todos los archivos relacionados con el sistema ZEUES para el cliente Kronos.

### Archivos en la Carpeta

ZEUES usa **4 Google Sheets distintos**: dos para operaciones (prod / testing) y dos para
el log de auditoría de la lista del supervisor (prod / dev).

| Spreadsheet | Propósito | Variable de entorno |
|---|---|---|
| `_Kronos_Registro_Piping R04` | Operaciones **PRODUCCIÓN** (datos reales del cliente) | `GOOGLE_SHEET_ID` |
| Operaciones de testing | Operaciones **TESTING** (desarrollo y pruebas) | `GOOGLE_SHEET_ID` |
| `ZEUES_App_Audit_PROD` | Log de auditoría de la lista del supervisor — **PRODUCCIÓN** | `GOOGLE_AUDIT_SHEET_ID` |
| `ZEUES_App_Audit_DEV` | Log de auditoría de la lista del supervisor — **DEV** | `GOOGLE_AUDIT_SHEET_ID` |

---

## Google Sheets

### Sheets de Operaciones — TESTING

**URL:** https://docs.google.com/spreadsheets/d/14Rcrmc6c2RTkJG_fRgtSFDYWgP6Qt6zfciUtnl-9AMo/edit

**ID:** `14Rcrmc6c2RTkJG_fRgtSFDYWgP6Qt6zfciUtnl-9AMo`

**Uso:**
- Spreadsheet de operaciones que usa el desarrollo local y las pruebas.
- Todas las pruebas de integración con Google Sheets API.
- Datos de prueba y validaciones.
- Entrenamiento y demos.

**Configuración:**
- Misma estructura de columnas que producción (ver modelo de datos en `CLAUDE.md`).
- Compartido con el Service Account (Editor).

---

### Sheets de Operaciones — PRODUCCIÓN (Oficial)

**Nombre del archivo:** `_Kronos_Registro_Piping R04`

**URL:** https://docs.google.com/spreadsheets/d/17iOaq2sv4mSOuJY4B8dGQIsWTTUKPspCtb7gk6u-MaQ/edit

**ID:** `17iOaq2sv4mSOuJY4B8dGQIsWTTUKPspCtb7gk6u-MaQ`

⚠️ **DATOS REALES DEL CLIENTE.** Nunca apuntar el desarrollo local aquí. Este ID está en la
blocklist de `scripts/dump_staging_tags.py`, que se niega a correr contra producción.

**Uso:**
- Datos reales de producción del cliente Kronos.
- El backend en Railway apunta aquí vía `GOOGLE_SHEET_ID`.

---

### Sheets de Auditoría — DEV

**Nombre del archivo:** `ZEUES_App_Audit_DEV`

**URL:** https://docs.google.com/spreadsheets/d/1SZSM1wPndC8tm91WAooaZ74PZnAJ-0_0xTQsRX5jxa4/edit

**ID:** `1SZSM1wPndC8tm91WAooaZ74PZnAJ-0_0xTQsRX5jxa4`

**Uso:**
- Versión de desarrollo del log de auditoría de la lista del supervisor.
- Apuntada por `GOOGLE_AUDIT_SHEET_ID` en `.env.local`.

---

### Sheets de Auditoría — PRODUCCIÓN

**Nombre del archivo:** `ZEUES_App_Audit_PROD`

**URL:** https://docs.google.com/spreadsheets/d/1CF_SNO8k6zkIEXukQ3etoFWUnD_3uWCHj0AxdENST7k/edit

**ID:** `1CF_SNO8k6zkIEXukQ3etoFWUnD_3uWCHj0AxdENST7k`

**Uso:**
- Fuente de verdad server-side de la lista del supervisor (reemplazó al `localStorage`).
- Registra eventos `LIST_ADD` / `LIST_REMOVE` / `SESSION_*` / `LIST_MIGRATE`.
- Tres pestañas: `Lista`, `Audit`, `Snapshots_Legacy`.
- Apuntada por `GOOGLE_AUDIT_SHEET_ID` en Railway.
- Contexto y verificación: `docs/RUNBOOK-supervisor-feature.md`.

> `config.py` valida al arrancar que `GOOGLE_AUDIT_SHEET_ID` ≠ `GOOGLE_SHEET_ID`, para que
> los datos de auditoría nunca se escriban en el spreadsheet de operaciones.

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
# Google Sheets - TESTING (operaciones)
GOOGLE_SHEET_ID=14Rcrmc6c2RTkJG_fRgtSFDYWgP6Qt6zfciUtnl-9AMo

# Google Sheets - DEV (auditoría de la lista del supervisor)
GOOGLE_AUDIT_SHEET_ID=1SZSM1wPndC8tm91WAooaZ74PZnAJ-0_0xTQsRX5jxa4

# Service Account (copiar del archivo JSON descargado)
GOOGLE_SERVICE_ACCOUNT_EMAIL=zeus-mvp@zeus-mvp.iam.gserviceaccount.com
GOOGLE_PRIVATE_KEY="-----BEGIN PRIVATE KEY-----\n...\n-----END PRIVATE KEY-----\n"
```

### Para Producción (Railway)
```env
# Google Sheets - PRODUCCIÓN (operaciones — datos reales del cliente)
GOOGLE_SHEET_ID=17iOaq2sv4mSOuJY4B8dGQIsWTTUKPspCtb7gk6u-MaQ

# Google Sheets - PRODUCCIÓN (auditoría de la lista del supervisor)
GOOGLE_AUDIT_SHEET_ID=1CF_SNO8k6zkIEXukQ3etoFWUnD_3uWCHj0AxdENST7k

# Service Account (mismo que desarrollo)
GOOGLE_SERVICE_ACCOUNT_EMAIL=zeus-mvp@zeus-mvp.iam.gserviceaccount.com
GOOGLE_PRIVATE_KEY="-----BEGIN PRIVATE KEY-----\n...\n-----END PRIVATE KEY-----\n"
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

| Spreadsheet | ID |
|---|---|
| Operaciones TESTING | `14Rcrmc6c2RTkJG_fRgtSFDYWgP6Qt6zfciUtnl-9AMo` |
| Operaciones PRODUCCIÓN | `17iOaq2sv4mSOuJY4B8dGQIsWTTUKPspCtb7gk6u-MaQ` |
| Auditoría DEV | `1SZSM1wPndC8tm91WAooaZ74PZnAJ-0_0xTQsRX5jxa4` |
| Auditoría PRODUCCIÓN | `1CF_SNO8k6zkIEXukQ3etoFWUnD_3uWCHj0AxdENST7k` |

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

### 22 de mayo de 2026 - v2.0
- ✅ Documentadas las 4 spreadsheets reales: operaciones (prod/testing) + auditoría (prod/dev)
- ✅ Corregido el ID de operaciones de testing: `14Rcrmc...` (el viejo `11v8fD5...` ya no se usa)
- ✅ Agregados `ZEUES_App_Audit_PROD` (`1CF_SNO8k...`) y `ZEUES_App_Audit_DEV` (`1SZSM1w...`)
- ✅ Agregada variable `GOOGLE_AUDIT_SHEET_ID` a las secciones de entorno
- ✅ Variables de entorno alineadas con `.env.local` y Railway reales

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

**Última actualización:** 22 de mayo de 2026
