# Phase 8: Backend Data Layer - Context

**Gathered:** 2026-02-02
**Status:** Ready for planning

<domain>
## Phase Boundary

Repository layer that reads and writes union-level data to Google Sheets with batch operations and performance optimization. Provides CRUD operations for the Uniones sheet, aggregates metrics for Operaciones tracking, and handles Metadata logging with chunking.

**Key relationship:** Operaciones.OT (Column C) ↔ Uniones.OT (Column B) — Query unions by work order number, not TAG_SPOOL.

</domain>

<decisions>
## Implementation Decisions

### Query Filtering Strategy
- Return full Union model objects (all 18 fields) from repository queries
- Client-side filtering: Repository returns all unions for an OT, service layer filters by ARM/SOLD state
- No caching at repository level — always fetch fresh data from Sheets for consistency
- Use ColumnMapCache for dynamic header mapping (consistent with v3.0 pattern)
- Disponible logic:
  - ARM disponibles: `ARM_FECHA_FIN IS NULL`
  - SOLD disponibles: `ARM_FECHA_FIN NOT NULL AND SOL_FECHA_FIN IS NULL`

**OT-based queries:** The relationship between Operaciones and Uniones is via **OT column** (Operaciones Column C, Uniones Column B), NOT TAG_SPOOL.

**Scale context:** Uniones sheet will grow to ~300 rows in 1 month, ~1000 rows in 6 months. Typical OT has 5-10 unions.

### Batch Update Mechanics
- Update ARM_FECHA_FIN + ARM_WORKER fields on completion (same for SOL_*)
- Timestamp format: `DD-MM-YYYY HH:MM:SS` (Chile timezone, consistent with v3.0)
- Separate A1 range per union in batch request (e.g., 7 unions = 7 ranges)
- Validate unions exist and are in expected state BEFORE attempting batch_update()

### Metrics Calculation Approach
- Calculate metrics on-demand (no caching in Operaciones sheet)
- Precision: 2 decimal places for pulgadas sums (e.g., 18.50)
- Dedicated aggregation methods: `count_completed_arm(ot)`, `sum_pulgadas_arm(ot)`, etc.
- Accept OT as parameter (caller provides OT, repository doesn't look up from Operaciones)
- Total_Uniones counts ALL unions for an OT regardless of state
- Pulgadas_ARM/SOLD sum DN_UNION where ARM_FECHA_FIN/SOL_FECHA_FIN NOT NULL
- Return 0 for counts and 0.00 for sums when no unions exist for an OT (graceful handling)

### Error Handling & Recovery
- Retry with exponential backoff on 429 rate limit errors (automatic retry up to 3 times)
- Batch operations must be idempotent (safe to retry multiple times)
- Log failed operations to Metadata sheet for audit trail
- Skip invalid rows with warning when encountering malformed data (e.g., DN_UNION not a number) — resilient to data quality issues

### Claude's Discretion
- Single get_unions_by_ot(ot) method vs separate methods per pattern (get_disponibles_arm, get_disponibles_sold) — balance simplicity and intent clarity given 300-1000 row scale
- Partial batch_update() failure handling: roll back vs accept partial success vs retry failed updates — choose based on data consistency needs
- A1 notation vs R1C1 notation for batch_update() ranges — follow gspread best practices
- Specific retry backoff timings (e.g., 1s, 2s, 4s) and max retry count for rate limiting

</decisions>

<specifics>
## Specific Ideas

- **OT relationship critical:** Always query Uniones by OT from Operaciones.Column C, never by TAG_SPOOL directly
- Scale expectations guide optimization: ~300 rows in 1 month, ~1000 rows in 6 months, 5-10 unions per OT typical
- Performance target from Phase 10: batch update + metadata logging < 1 second for 10 unions
- Follow v3.0 date formatting patterns: `format_datetime_for_sheets(now_chile())` for timestamps
- Use ColumnMapCache for all column access (no hardcoded indices)

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope.

</deferred>

---

*Phase: 08-backend-data-layer*
*Context gathered: 2026-02-02*
