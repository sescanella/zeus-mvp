# Production Backup Metadata

**Migration Phase:** v2.1 → v3.0
**Backup Created:** 2026-01-26T18:15:00Z
**Backup Method:** Manual copy (Google Sheets UI)

## Backup Details

| Property | Value |
|----------|-------|
| **Original Sheet ID** | `17iOaq2sv4mSOuJY4B8dGQIsWTTUKPspCtb7gk6u-MaQ` |
| **Backup Sheet ID** | `1kWUjegxV00MOJver_9ljZqHxgJJBgErnH_J--N4TS9M` |
| **Backup Sheet Name** | `__Kronos_Registro_Piping R04_v2.1_backup_20260126` |
| **Backup URL** | [Open Backup](https://docs.google.com/spreadsheets/d/1kWUjegxV00MOJver_9ljZqHxgJJBgErnH_J--N4TS9M/edit) |
| **Row Count** | 2,556 rows |
| **Column Count** | 63 columns (v2.1 schema) |
| **Verified** | ✓ Complete copy confirmed |

## Rollback Window

| Property | Value |
|----------|-------|
| **Created** | 2026-01-26T18:15:00Z |
| **Expires** | 2026-02-02T18:15:00Z |
| **Duration** | 7 days |
| **Status** | Active |

## Backup Method

**Method:** Manual copy via Google Sheets UI (File → Make a copy)

**Reason:** Service account storage quota limitation prevented automated backup via `backup_sheet.py` script.

**Outcome:** Identical result to automated method - full sheet copy with all data preserved.

## Verification Results

✓ Backup sheet accessible via service account
✓ Row count matches production (2,556 rows)
✓ Column count matches v2.1 schema (63 columns)
✓ Last 5 columns verified: Precio Fabricación, Precio Revestimiento, Precio Pintura, Precio Embalaje, Precio Total
✓ Backup contains complete copy of production data

## Rollback Procedure

If migration to v3.0 fails and rollback is required:

1. **Stop all API operations** - Set maintenance mode
2. **Verify backup integrity** - Check backup sheet is still accessible
3. **Manual restoration required** - Copy data from backup sheet back to production
   - Note: Google Sheets API (gspread) doesn't support full sheet restoration
   - Use Google Sheets UI: Copy all cells from backup → Paste into production
   - Alternative: Use Google Drive API to replace entire file
4. **Verify restoration** - Check row/column counts match backup metadata
5. **Resume operations** - Exit maintenance mode

## Notes

- Backup created before adding v3.0 columns (Ocupado_Por, Fecha_Ocupacion, version, estado, requiere_supervisor, fecha_ultima_actualizacion)
- This backup preserves the last known good state of v2.1 production
- After successful migration and 7-day rollback window, backup can be archived or deleted
- Service account: zeus-mvp@zeus-mvp.iam.gserviceaccount.com

## Related Files

- Backup execution log: `backend/logs/migration/backup_execution.log`
- Backup script: `backend/scripts/backup_sheet.py`
- Migration coordinator: `backend/scripts/migration_coordinator.py`
