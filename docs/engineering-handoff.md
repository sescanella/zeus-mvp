# Uniones Sheet Engineering Handoff

**Purpose:** Complete the Uniones sheet structure for ZEUES v4.0 deployment
**Date:** 2026-02-02
**Target Audience:** Engineering team responsible for Uniones data population

---

## Executive Summary

The ZEUES v4.0 system requires a pre-populated **Uniones** sheet with 18 columns to enable union-level tracking. Currently, the sheet has **13 columns** and is missing **9 critical columns** that must be added before v4.0 can deploy.

**Your mission:** Add the 9 missing columns and populate them with data according to the specifications below.

---

## Current State

### What Exists (13 columns)

The Uniones sheet currently has these columns:

1. **N_UNION** - Union number within spool (1, 2, 3...)
2. **DN_UNION** - Diameter in inches (e.g., 2.5, 4.0, 6.0)
3. **TIPO_UNION** - Union type (e.g., "Brida", "Socket", "Acople")
4. **ARM_FECHA_INICIO** - Armado start timestamp
5. **ARM_FECHA_FIN** - Armado completion timestamp
6. **ARM_WORKER** - Worker who completed armado
7. **SOL_FECHA_INICIO** - Soldadura start timestamp
8. **SOL_FECHA_FIN** - Soldadura completion timestamp
9. **SOL_WORKER** - Worker who completed soldadura
10-13. (Other existing columns)

### What's Missing (9 columns)

These columns must be added to complete the v4.0 schema:

| Column Name        | Position | Type   | Purpose                           | Example Value                |
| ------------------ | -------- | ------ | --------------------------------- | ---------------------------- |
| ID                 | 1        | int    | Unique record identifier          | 1, 2, 3...                   |
| TAG_SPOOL          | 2        | string | Foreign key to Operaciones        | "TEST-01", "ARM-2024-042"    |
| NDT_FECHA          | 12       | date   | Non-destructive testing date      | "21-01-2026"                 |
| NDT_STATUS         | 13       | string | NDT result                        | "APROBADO", "RECHAZADO", ""  |
| version            | 14       | UUID   | Optimistic locking token          | "a1b2c3d4-e5f6-..."          |
| Creado_Por         | 15       | string | Audit: Created by worker          | "MR(93)"                     |
| Fecha_Creacion     | 16       | date   | Audit: Creation date              | "21-01-2026"                 |
| Modificado_Por     | 17       | string | Audit: Last modified by worker    | "JS(47)"                     |
| Fecha_Modificacion | 18       | date   | Audit: Last modification date     | "22-01-2026"                 |

---

## Schema Definition

### Complete 18-Column Structure

Here is the full schema with data types and constraints:

```
Column  | Name                | Type   | Nullable | Constraints/Format
--------|---------------------|--------|----------|------------------------------------
1       | ID                  | int    | NO       | Sequential (1, 2, 3...)
2       | TAG_SPOOL           | string | NO       | Must match Operaciones.TAG_SPOOL
3       | N_UNION             | int    | NO       | Unique within each TAG_SPOOL (1-20)
4       | DN_UNION            | float  | NO       | Diameter in inches, 1 decimal (2.5)
5       | TIPO_UNION          | string | NO       | e.g., "Brida", "Socket", "Acople"
6       | ARM_FECHA_INICIO    | date   | YES      | DD-MM-YYYY HH:MM:SS
7       | ARM_FECHA_FIN       | date   | YES      | DD-MM-YYYY HH:MM:SS
8       | ARM_WORKER          | string | YES      | Format: INICIALES(ID) e.g., "MR(93)"
9       | SOL_FECHA_INICIO    | date   | YES      | DD-MM-YYYY HH:MM:SS
10      | SOL_FECHA_FIN       | date   | YES      | DD-MM-YYYY HH:MM:SS
11      | SOL_WORKER          | string | YES      | Format: INICIALES(ID) e.g., "JS(47)"
12      | NDT_FECHA           | date   | YES      | DD-MM-YYYY (no time component)
13      | NDT_STATUS          | string | YES      | "APROBADO" | "RECHAZADO" | "" (empty)
14      | version             | UUID   | NO       | UUID4 format (auto-generated)
15      | Creado_Por          | string | NO       | Format: INICIALES(ID) e.g., "MR(93)"
16      | Fecha_Creacion      | date   | NO       | DD-MM-YYYY HH:MM:SS
17      | Modificado_Por      | string | YES      | Format: INICIALES(ID) e.g., "JS(47)"
18      | Fecha_Modificacion  | date   | YES      | DD-MM-YYYY HH:MM:SS
```

### Data Relationships

1. **TAG_SPOOL → Operaciones.TAG_SPOOL** (Foreign Key)
   - Each TAG_SPOOL can have multiple unions (1-to-many relationship)
   - Example: "ARM-2024-042" might have 10 unions (N_UNION: 1-10)

2. **N_UNION Uniqueness**
   - N_UNION must be unique **within each TAG_SPOOL**
   - OK: TAG_SPOOL="TEST-01", N_UNION=1 AND TAG_SPOOL="TEST-02", N_UNION=1
   - ERROR: TAG_SPOOL="TEST-01", N_UNION=1 AND TAG_SPOOL="TEST-01", N_UNION=1

3. **Worker References**
   - ARM_WORKER, SOL_WORKER, Creado_Por, Modificado_Por must match Trabajadores sheet
   - Format: `INICIALES(ID)` where ID is from Trabajadores.Id column
   - Example: "Miguel Rodríguez" with Id=93 → "MR(93)"

---

## Data Format Specifications

### Date Formats

**Date with Time:**
```
Format: DD-MM-YYYY HH:MM:SS
Examples:
  - "21-01-2026 14:30:00"
  - "05-03-2026 08:15:45"
```

**Date Only:**
```
Format: DD-MM-YYYY
Examples:
  - "21-01-2026"
  - "05-03-2026"
```

**Timezone:** All dates are in America/Santiago (Chile) timezone.

### Worker Format

**Pattern:** `INICIALES(ID)`

**How to construct:**
1. Get worker's first name and last name initials
2. Get worker's ID from Trabajadores sheet
3. Combine as: `INITIALS(ID)`

**Examples:**
- Miguel Rodríguez (ID=93) → `MR(93)`
- Juan Silva (ID=47) → `JS(47)`
- Ana María Torres (ID=12) → `AT(12)`

### UUID Format (version column)

**Pattern:** UUID4 (8-4-4-4-12 hex digits)

**Examples:**
- `a1b2c3d4-e5f6-7890-abcd-ef1234567890`
- `550e8400-e29b-41d4-a716-446655440000`

**Generation:** Use UUID4 generator (random, not time-based)

---

## Example Data Rows

### Example 1: Fresh Union (Not Started)

```csv
ID  | TAG_SPOOL   | N_UNION | DN_UNION | TIPO_UNION | ARM_FECHA_INICIO | ARM_FECHA_FIN | ARM_WORKER | SOL_FECHA_INICIO | SOL_FECHA_FIN | SOL_WORKER | NDT_FECHA | NDT_STATUS | version                               | Creado_Por | Fecha_Creacion       | Modificado_Por | Fecha_Modificacion
1   | TEST-01     | 1       | 4.0      | Brida      |                  |               |            |                  |               |            |           |            | a1b2c3d4-e5f6-7890-abcd-ef1234567890  | MR(93)     | 21-01-2026 08:00:00  |                |
```

### Example 2: ARM Completed, SOLD Pending

```csv
ID  | TAG_SPOOL   | N_UNION | DN_UNION | TIPO_UNION | ARM_FECHA_INICIO      | ARM_FECHA_FIN         | ARM_WORKER | SOL_FECHA_INICIO | SOL_FECHA_FIN | SOL_WORKER | NDT_FECHA | NDT_STATUS | version                               | Creado_Por | Fecha_Creacion       | Modificado_Por | Fecha_Modificacion
2   | TEST-01     | 2       | 6.0      | Socket     | 21-01-2026 09:00:00   | 21-01-2026 11:30:00   | MR(93)     |                  |               |            |           |            | b2c3d4e5-f6a7-8901-bcde-f01234567891  | MR(93)     | 21-01-2026 08:00:00  | MR(93)         | 21-01-2026 11:30:00
```

### Example 3: Fully Complete with NDT

```csv
ID  | TAG_SPOOL   | N_UNION | DN_UNION | TIPO_UNION | ARM_FECHA_INICIO      | ARM_FECHA_FIN         | ARM_WORKER | SOL_FECHA_INICIO      | SOL_FECHA_FIN         | SOL_WORKER | NDT_FECHA    | NDT_STATUS | version                               | Creado_Por | Fecha_Creacion       | Modificado_Por | Fecha_Modificacion
3   | TEST-02     | 1       | 2.5      | Acople     | 22-01-2026 08:00:00   | 22-01-2026 10:00:00   | JS(47)     | 22-01-2026 13:00:00   | 22-01-2026 15:30:00   | JS(47)     | 23-01-2026   | APROBADO   | c3d4e5f6-a7b8-9012-cdef-012345678902  | JS(47)     | 22-01-2026 08:00:00  | JS(47)         | 22-01-2026 15:30:00
```

---

## Population Requirements

### 1. ID Column (Sequential Integers)

**Requirements:**
- Auto-increment starting from 1
- No gaps in sequence
- Unique across entire sheet

**How to populate:**
- Start with ID=1 for first row
- Increment by 1 for each row: 1, 2, 3, 4...

### 2. TAG_SPOOL Column (Foreign Key)

**Requirements:**
- Must match existing TAG_SPOOL values in Operaciones sheet
- Each TAG_SPOOL can appear multiple times (one row per union)

**How to populate:**
1. Get list of TAG_SPOOL values from Operaciones sheet
2. For each TAG_SPOOL, create N rows (one per union)
3. Each row gets the same TAG_SPOOL value

**Example:**
If Operaciones has TAG_SPOOL="TEST-01" with 10 unions:
- Create 10 rows with TAG_SPOOL="TEST-01"
- N_UNION values: 1, 2, 3, 4, 5, 6, 7, 8, 9, 10

### 3. N_UNION Column (Union Number)

**Requirements:**
- Sequential within each TAG_SPOOL (1, 2, 3...)
- Resets to 1 for each new TAG_SPOOL

**How to populate:**
- For each TAG_SPOOL, number unions starting from 1
- If spool has 10 unions: N_UNION = 1, 2, 3... 10

### 4. DN_UNION Column (Diameter)

**Requirements:**
- Float with 1 decimal place
- Represents diameter in inches

**Common values:**
- 2.5, 4.0, 6.0, 8.0, 10.0, 12.0

### 5. TIPO_UNION Column (Union Type)

**Requirements:**
- String value from allowed set

**Common values:**
- "Brida"
- "Socket"
- "Acople"
- "Codo"

### 6. NDT Columns (Non-Destructive Testing)

**NDT_FECHA:**
- Date only (no time)
- Populated after inspection completes
- Can be empty for uninspected unions

**NDT_STATUS:**
- Must be one of: "APROBADO", "RECHAZADO", or empty string
- Populated after inspection completes
- Typically aligned with NDT_FECHA (both populated together)

### 7. version Column (UUID4)

**Requirements:**
- UUID4 format (random)
- Must be unique for each row
- Used for optimistic locking

**How to generate:**
```python
import uuid
version = str(uuid.uuid4())
```

**Tools:**
- Python: `uuid.uuid4()`
- Online: https://www.uuidgenerator.net/version4
- Google Sheets: Use formula `=CONCATENATE(...)` or external script

### 8. Audit Columns (Created/Modified)

**Creado_Por + Fecha_Creacion:**
- Set once when row is created
- Never changed after creation
- Creado_Por: Worker who created the record (format: INICIALES(ID))
- Fecha_Creacion: Timestamp when created (DD-MM-YYYY HH:MM:SS)

**Modificado_Por + Fecha_Modificacion:**
- Empty initially
- Set whenever row is updated
- Modificado_Por: Worker who last modified (format: INICIALES(ID))
- Fecha_Modificacion: Timestamp of last modification (DD-MM-YYYY HH:MM:SS)

---

## Validation Tools

### Automated Validation Script

**Location:** `backend/scripts/validate_uniones_sheet.py`

**Usage:**
```bash
# Check structure (read-only)
python backend/scripts/validate_uniones_sheet.py

# Add missing column headers (structure only, no data)
python backend/scripts/validate_uniones_sheet.py --fix

# Verbose output
python backend/scripts/validate_uniones_sheet.py --verbose
```

**What it validates:**
- All 18 columns present
- Column names match expected (normalized: case-insensitive, ignores spaces/underscores)
- Reports missing and extra columns

**What it does NOT validate:**
- Data quality (dates, worker formats, foreign keys)
- Row completeness
- Business logic constraints

### Manual Validation Checklist

Before marking Uniones sheet as complete, verify:

- [ ] Sheet has exactly 18 columns
- [ ] All 9 new columns added (ID, TAG_SPOOL, NDT_FECHA, NDT_STATUS, version, Creado_Por, Fecha_Creacion, Modificado_Por, Fecha_Modificacion)
- [ ] ID column has sequential integers (no gaps)
- [ ] TAG_SPOOL values match Operaciones sheet
- [ ] N_UNION values are unique within each TAG_SPOOL
- [ ] DN_UNION values are positive floats
- [ ] Date formats match DD-MM-YYYY (or DD-MM-YYYY HH:MM:SS)
- [ ] Worker formats match INICIALES(ID) pattern
- [ ] version column has UUID4 values (no duplicates)
- [ ] NDT_STATUS values are "APROBADO", "RECHAZADO", or empty
- [ ] Audit columns (Creado_Por, Fecha_Creacion) populated for all rows

---

## Deployment Coordination

### Pre-Deployment Steps

1. **Engineering completes Uniones sheet population**
   - Add 9 missing columns
   - Populate all required data

2. **Run validation script**
   ```bash
   python backend/scripts/validate_uniones_sheet.py
   ```
   - Should report: "Uniones sheet valid: 18 columns found"

3. **Notify development team**
   - Confirm validation passed
   - Provide timestamp of completion

4. **Development team runs full schema validation**
   ```bash
   python backend/scripts/validate_schema_startup.py
   ```
   - Validates Uniones + Operaciones + Metadata schemas

5. **v4.0 deployment proceeds**
   - FastAPI startup validation will verify schema
   - If schema incomplete, deployment will fail fast

### Timeline Expectations

| Task                                    | Owner        | Estimated Time | Blocking?       |
| --------------------------------------- | ------------ | -------------- | --------------- |
| Add 9 column headers                    | Engineering  | 10 minutes     | YES (v4.0 blocker) |
| Populate ID, version, audit columns     | Engineering  | 2-4 hours      | YES (v4.0 blocker) |
| Populate TAG_SPOOL, N_UNION             | Engineering  | 4-8 hours      | YES (v4.0 blocker) |
| Populate NDT fields (if available)      | Engineering  | 2-4 hours      | NO (can be empty) |
| Run validation script                   | Engineering  | 2 minutes      | YES (verification) |
| Development team schema validation      | Dev Team     | 5 minutes      | YES (verification) |
| v4.0 deployment                         | Dev Team     | 30 minutes     | (final step)    |

**Critical Path:** Uniones sheet must be 100% complete before v4.0 deployment begins.

---

## Support & Questions

### Contact

**Development Team:**
- Primary: [Your dev team contact]
- Repository: `/Users/sescanella/Proyectos/KM/ZEUES-by-KM`

**Documentation:**
- v4.0 Requirements: `.planning/PROJECT.md`
- Schema Migration History: `.planning/phases/07-data-model-foundation/`
- Validation Scripts: `backend/scripts/`

### Common Questions

**Q: Can we add columns in a different order?**
A: Yes, the system uses dynamic column mapping. Order doesn't matter as long as column names match.

**Q: What happens if we miss a column?**
A: FastAPI startup validation will fail and prevent deployment. You'll see error: "Missing columns: [column names]"

**Q: Can we add extra columns?**
A: Yes, extra columns are allowed. The system only reads the 18 required columns.

**Q: How do we generate UUID values?**
A: Use Python `uuid.uuid4()` or online tool: https://www.uuidgenerator.net/version4

**Q: What if we don't have NDT data yet?**
A: NDT columns (NDT_FECHA, NDT_STATUS) can be empty. They'll be populated later during inspection workflow.

**Q: Should ARM/SOLD timestamps be populated?**
A: Only if you have historical data. For new spools, leave empty - workers will populate during v4.0 workflow.

**Q: How to handle spools with no unions yet?**
A: Skip them. Only create Uniones rows for spools where union count is known.

---

## Option: Automated Header Addition

If you prefer the development team to add column headers (structure only), we can run:

```bash
python backend/scripts/validate_uniones_sheet.py --fix
```

**What this does:**
- Adds 9 missing column headers to Uniones sheet
- Does NOT populate any data
- Engineering still responsible for populating all rows

**Benefits:**
- Saves Engineering 10 minutes of manual column addition
- Ensures column names match exactly what system expects
- Reduces risk of typos in column names

**Decision:** Let us know if you want development team to run `--fix` or if you prefer to add columns manually.

---

**Next Steps:**
1. Review this document with your team
2. Decide on timeline for Uniones completion
3. Coordinate with development team on deployment date
4. Execute population process
5. Run validation script
6. Confirm readiness for v4.0 deployment

---

*Document Version: 1.0*
*Created: 2026-02-02*
*Status: Active*
