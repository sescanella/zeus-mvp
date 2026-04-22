# Codebase Concerns

**Analysis Date:** 2026-01-26

## Tech Debt

**Deprecated Event Sourcing v2.0 Code:**
- Issue: Backup file `validation_service_v2.0_backup.py` remains in codebase after v2.1 migration from Event Sourcing to Direct Read/Write
- Files: `backend/services/validation_service_v2.0_backup.py` (588 lines)
- Impact: Code duplication increases maintenance burden; developers may accidentally reference outdated patterns. Backup should be archived externally or removed.
- Fix approach: Move backup to `.archive/` directory outside main source tree or delete if no longer needed. Update git history if necessary.

**Unused Spool Service Version:**
- Issue: `spool_service_v2.py` exists alongside primary `spool_service.py`, suggesting incomplete migration or abandoned refactoring
- Files: `backend/services/spool_service_v2.py` (540 lines), `backend/services/spool_service.py` (242 lines)
- Impact: Unclear which version is active; risk of bugfixes being applied to wrong file. Creates cognitive load for developers.
- Fix approach: Audit which version is actually used in dependencies. Remove unused version and update imports if necessary.

**Incomplete TODO in Sheets Service:**
- Issue: `TODO: Agregar si existe columna proyecto` comment left in production code
- Files: `backend/services/sheets_service.py:448`
- Impact: Indicates incomplete feature implementation. May affect data completeness if `proyecto` column is added later without updating this code.
- Fix approach: Complete the feature or remove the TODO with a decision note if `proyecto` is out of scope.

**Column Mapping Fragility:**
- Issue: Architecture relies on dynamic column mapping via `ColumnMapCache` to handle frequently-changing Google Sheets structure, but no version control on schema changes
- Files: `backend/core/column_map_cache.py` (243 lines), `backend/services/sheets_service.py`, `backend/repositories/sheets_repository.py`
- Impact: If Google Sheets column names change without notice, entire system fails at runtime. CRITICAL columns (TAG_SPOOL, Armador, Fecha_Armado) must always exist.
- Fix approach: Implement schema versioning/validation on startup. Add monitoring alerts for unexpected column disappearance. Document required columns in README.

## Known Issues

**Vercel Cache Invalidation History:**
- Issue: Multiple recent commits indicate persistent Vercel caching problems (commits: `61e90d7`, `4c7bdc7`, `1497db5`, `121a018`, `bb6c277`)
- Symptoms: Frontend code changes not reflected in deployed version; users seeing stale UI
- Files: `zeues-frontend/app/seleccionar-spool/page.tsx` (372 lines) - recent debugging
- Trigger: Variable renames and placeholder text changes to force rebuild indicate cache busting strategy rather than root cause fix
- Workaround: Force rebuild via commit message changes; not a sustainable solution
- Recommendation: Implement proper cache headers in Vercel config or migrate to different deployment strategy that doesn't require workarounds.

**Frontend Console Debug Logging:**
- Issue: Debug logging left in production code
- Files: `zeues-frontend/app/seleccionar-spool/page.tsx:96-102` - `console.log('[FILTER DEBUG v2.1.2]', {...})`
- Impact: Pollutes browser console; may reveal internal data structures to end users; performance overhead
- Fix approach: Remove debug logging from production or gate it behind `config.ENVIRONMENT === 'development'`

**Metadata Audit Trail Optional (Best Effort):**
- Issue: Metadata repository writes are "best effort" and not critical for v2.1 Direct Read architecture
- Files: `backend/services/action_service.py:85` - MetadataRepository optional
- Impact: Audit trail may be incomplete if Google Sheets API fails during metadata write. State is still written to Operaciones sheet, but audit is lost.
- Trigger: Rate limiting (429 errors) or temporary connectivity issues
- Recommendation: Consider making metadata writes synchronous and blocking, or implement a queue for guaranteed delivery. Document audit trail limitations.

## Security Considerations

**Service Account Credentials Exposure Risk:**
- Risk: Google Service Account credentials stored in multiple locations (env vars, file, JSON); potential for accidental exposure in logs or error messages
- Files: `backend/config.py:74` - private key replacement, `backend/repositories/sheets_repository.py:106-107` - credential loading
- Current mitigation: `.env.local` in `.gitignore`, credentials JSON in `credenciales/` also gitignored
- Recommendations:
  1. Add credential sanitization to logging (never log private_key, only project_id)
  2. Implement credential rotation policy
  3. Ensure Railway environment variables are encrypted
  4. Audit GitHub Actions workflows to ensure credentials aren't exposed in job logs

**No Authentication on Endpoints:**
- Risk: All endpoints (`GET /api/workers`, `GET /api/spools/*`, `POST /api/*-accion`) accept requests from any source if CORS allows
- Files: `backend/main.py:100-106` - CORS middleware allows any method from `ALLOWED_ORIGINS`
- Current mitigation: CORS restricts origins (localhost + production), ownership validation on CANCELAR/COMPLETAR
- Recommendations:
  1. Add API key or JWT token validation
  2. Consider rate limiting per IP/worker
  3. Log authentication attempts for audit trail

**CANCELAR Action Removes Ownership Restrictions:**
- Risk: Recent commit `60f5c10` "remove ownership restriction for completing/canceling actions" may have security implications
- Files: `backend/services/validation_service.py` - ownership check implementation
- Current status: Unclear if this was intentional or accidental; needs review
- Recommendations: Verify business requirement and add explicit security test to prevent regression

## Performance Bottlenecks

**Full Sheet Read on Every Request:**
- Problem: Every API call may trigger full sheet read if cache misses or TTL expires (300 seconds default)
- Files: `backend/repositories/sheets_repository.py:148` (read_worksheet), `backend/config.py:40` (CACHE_TTL_SECONDS)
- Cause: Google Sheets API limits (300 quota units per 60 seconds). Reading full Operaciones sheet (1000+ rows × 65 columns) uses significant quota.
- Impact: Under load, system hits 429 rate limits; requests fail with "SHEETS_RATE_LIMIT"
- Improvement path:
  1. Implement partial reads (query specific rows by TAG_SPOOL instead of full sheet)
  2. Increase cache TTL for read-only data
  3. Implement batch query optimization (already attempted in commit `ef3a0f7`, then reverted)
  4. Add quota monitoring dashboard

**Metadata Event Read Loads All History:**
- Problem: `get_all_events()` in MetadataRepository reads entire Metadata sheet on every call
- Files: `backend/repositories/metadata_repository.py:177-236` (188 lines of debug logging)
- Cause: Used for Event Sourcing audit trail; no pagination or filtering
- Impact: Performance degrades as Metadata sheet grows; eventually becomes unsustainable
- Improvement path:
  1. Implement pagination by date range
  2. Add selective event querying (by spool, worker, date)
  3. Archive old metadata to separate sheet
  4. Consider moving to proper database for audit trail

**Frontend Filter Logic Not Optimized:**
- Problem: Filtering 1000+ spools with multiple string conditions happens in-memory every render
- Files: `zeues-frontend/app/seleccionar-spool/page.tsx:90-93` (filter logic), 96-102 (debug logging suggests performance concerns)
- Cause: No backend-side filtering; API returns all spools matching operation
- Impact: UI lag on tablets with poor connectivity; multiple re-renders trigger multiple filter operations
- Improvement path:
  1. Implement backend filtering by NV, TAG_SPOOL
  2. Add pagination to spools endpoint (return 50 at a time, not 1000+)
  3. Add debouncing to filter input fields

**Worker Role Loading Duplicated:**
- Problem: Multiple calls to RoleRepository to fetch same data; cache missing optimization opportunity
- Files: `backend/services/worker_service.py:61,76` - batch loading optimization noted but implementation may be incomplete
- Cause: Each worker fetch triggers new role repository call
- Impact: Repeated Sheets API calls for same data
- Improvement path: Implement worker + roles batch fetch; cache combined result per request

## Fragile Areas

**Direct Read Architecture Migration (v2.0→v2.1):**
- Files: `backend/services/action_service.py`, `backend/services/validation_service.py`, `backend/repositories/sheets_repository.py`
- Why fragile: Major architectural shift from Event Sourcing (state reconstructed from events) to Direct Read (state from Operaciones columns). Old and new code may coexist, creating confusion.
- Safe modification:
  1. Add comprehensive integration tests covering both single and batch operations
  2. Test scenarios: missing columns, null values, concurrent updates
  3. Implement schema validation on startup
  4. Monitor production for orphaned records (spools where both Armador AND Soldador are set)
- Test coverage: 244 tests passing, but gaps likely in edge cases (concurrent updates, partial failures in batch operations)

**Batch Operation Partial Failures:**
- Files: `zeues-frontend/lib/api.ts:413-488` (batch API functions), `backend/routers/actions.py` (batch endpoints)
- Why fragile: Batch operations can succeed for some spools and fail for others. Frontend must handle partial success; no transaction semantics.
- Safe modification:
  1. Frontend: Display detailed breakdown of which spools succeeded/failed
  2. Backend: Ensure failed operations don't corrupt state (rollback partial updates)
  3. Add idempotency keys to prevent duplicate processing on retry
- Test coverage: `tests/unit/test_action_service_batch.py` (933 lines) covers error cases

**Worker Name Format (INICIALES(ID)):**
- Files: `backend/models/worker.py:47`, `backend/services/worker_service.py`, frontend worker selection
- Why fragile: New format "INICIALES(ID)" (e.g., "MR(93)") used as unique identifier in Sheets columns (Armador, Soldador). If format parsing fails, ownership validation breaks.
- Safe modification:
  1. Add format validation: `^[A-Z]{2}\(\d+\)$`
  2. Test edge cases: workers with accented names (José → JJ?), same initials (Juan/Jorge → JJ), single names
  3. Add migration script if changing format
- Test coverage: `tests/unit/test_worker_nombre_formato.py` (165 lines)

**Context API State Management:**
- Files: `zeues-frontend/lib/context.tsx`
- Why fragile: Simple Context API without strict state machine. Pages can navigate in unexpected order (e.g., skip P2, go directly to P4). Manual state cleanup required.
- Safe modification:
  1. Add strict state validation on each page (require previous page completed)
  2. Implement state reset timeouts (5min of inactivity → reset)
  3. Add state persistence to localStorage for recovery
  4. Test navigation edge cases: back button, direct URL access, browser refresh

**Timezone Handling (Chile Specific):**
- Files: `backend/config.py:46`, `backend/utils/date_formatter.py`, `backend/services/sheets_service.py`
- Why fragile: System uses Chile timezone (UTC-3/-4 depending on daylight saving). Dates written to Sheets must match expected format. If timezone environment variable missing or incorrect, date calculations wrong.
- Safe modification:
  1. Add timezone validation on startup
  2. Test daylight saving time transitions (March, September)
  3. Consider using UTC internally, convert only for display
- Test coverage: Likely lacking for DST edge cases

## Test Coverage Gaps

**Frontend E2E Tests Missing:**
- What's not tested: 7-page user flow end-to-end; navigation between pages; error recovery
- Files: No Playwright E2E tests found for complete workflows
- Risk: Regression could break entire user flow without detection
- Priority: HIGH - Critical path through app untested
- Recommendation: Add Playwright E2E test suite covering:
  1. Happy path: P1→P7 with single spool
  2. Batch operations: P1→P7 with multiple spools
  3. Error scenarios: API failures, network errors, missing selections
  4. Edge cases: Back button usage, direct URL navigation

**Backend Role Authorization Tests:**
- What's not tested: Multi-role workers; METROLOGIA operation; role-based access control
- Files: `tests/unit/test_role_service.py` (350 lines) exists but may not cover all scenarios
- Risk: Unauthorized users may access operations they shouldn't
- Priority: HIGH - Security implications
- Recommendation: Add tests for:
  1. Worker with multiple roles can INICIAR correct operations
  2. Worker without role cannot INICIAR that operation
  3. Cross-operation boundaries (Armador cannot INICIAR SOLD)

**Concurrent Update Scenarios Not Tested:**
- What's not tested: Two workers attempting same spool simultaneously; race conditions in batch operations
- Files: No concurrency tests found
- Risk: Unpredictable behavior under load; data corruption possible
- Priority: MEDIUM - Rare in practice but high impact
- Recommendation: Implement stress tests with concurrent requests

**Google Sheets Connection Failure Recovery:**
- What's not tested: Network timeouts, malformed responses, quota exhaustion recovery
- Files: `backend/repositories/sheets_repository.py:19-53` (retry decorator exists)
- Risk: App may hang or fail ungracefully if Sheets API becomes slow/unavailable
- Priority: MEDIUM - Operational resilience
- Recommendation: Add tests for:
  1. Retry logic with backoff
  2. Graceful degradation (cached data fallback)
  3. Timeout behavior (requests shouldn't hang indefinitely)

## Scaling Limits

**Google Sheets Row Capacity:**
- Current capacity: ~1000-2000 spools (Operaciones sheet)
- Limit: Google Sheets hard limit 10M cells. Each spool ~65 columns = ~65k cells per 1000 spools
- Scaling path:
  1. Archive completed spools to separate sheet
  2. Implement soft delete (flag column) instead of removing rows
  3. Consider migration to proper database when exceeding 5000 spools

**Rate Limiting at 300 Quota Units/min:**
- Current capacity: ~50-100 requests/minute depending on sheet complexity
- Limit: Google Sheets API 300 quota units per 60 seconds
- Scaling path:
  1. Implement request batching (combine multiple reads)
  2. Increase cache TTL for high-volume reads
  3. Pre-compute summary data instead of querying on every request
  4. Consider Google Sheets API v4 batch operations

**Frontend Tablet Performance:**
- Current capacity: Lists up to 1000 spools without lag on iPad
- Limit: Browser memory, rendering performance
- Scaling path:
  1. Implement pagination (50 per page)
  2. Virtual scrolling for large lists
  3. Reduce filter complexity

## Dependencies at Risk

**gspread Library (Python):**
- Risk: Third-party library with infrequent updates; Google Sheets API changes could break integration
- Current version: Listed in requirements.txt (version not pinned visible in constraints)
- Impact: If gspread drops support for certain features or Google deprecates API endpoints
- Migration plan: Monitor gspread releases; have fallback using raw Google Sheets API (google-auth-oauthlib)

**Vercel Deployment (Frontend):**
- Risk: Vendor lock-in; caching issues (evidenced by multiple commits to work around them)
- Current state: Production uses Vercel; local uses Next.js dev server
- Impact: Cache invalidation problems reduce deployment reliability
- Migration plan: Consider self-hosted Next.js on Railway (same provider as backend) to control caching

**Railway Hosting (Backend):**
- Risk: Vendor lock-in; limited monitoring/logging compared to enterprise platforms
- Current state: Production runs on Railway; local uses uvicorn
- Impact: Limited visibility into production issues; may need better logging/monitoring setup
- Migration plan: Add Sentry for error tracking; implement structured logging (JSON format for log aggregation)

## Missing Critical Features

**API Authentication:**
- Problem: No API key, JWT, or session validation. Any client can call endpoints.
- Blocks: Enterprise deployment; multi-tenant support
- Recommendation: Implement JWT with service account; add API key validation

**Audit Trail Completeness:**
- Problem: Metadata writes are "best effort" (optional); failures result in incomplete audit trail
- Blocks: Regulatory compliance (if required); forensic investigation of issues
- Recommendation: Make metadata writes critical (blocking action until written)

**Error Recovery UI:**
- Problem: Frontend has minimal error recovery (no retry buttons in error states)
- Blocks: Resilience on poor connections
- Recommendation: Add explicit retry button and exponential backoff for failed requests

**Spool State Reconciliation:**
- Problem: No tool to verify Sheets data consistency (e.g., orphaned records, dangling references)
- Blocks: Operational maintenance; debugging state corruption
- Recommendation: Add admin CLI tool to validate/repair sheet data

**Multi-Language Support:**
- Problem: All UI is Spanish; no i18n framework
- Blocks: International expansion
- Recommendation: Implement i18n (react-i18next) if needed

---

*Concerns audit: 2026-01-26*
