# Pitfalls Research: Real-Time Location Tracking + State Management

**Domain:** Real-time manufacturing traceability system refactoring
**Researched:** 2026-01-26
**Confidence:** MEDIUM-HIGH

**Context:** Refactoring working v2.1 production system (244 passing tests) to add real-time tracking, dynamic state machines, and occupation conflicts. Google Sheets as data source with ~200-500ms latency.

---

## Critical Pitfalls

### Pitfall 1: Race Conditions on TOMAR (Simultaneous Occupation)

**What goes wrong:**
Two workers attempt to TOMAR the same spool at nearly the same time. Both read the spool as DISPONIBLE, both write their worker_id, resulting in:
- Lost updates (last write wins, first worker overwritten)
- Data corruption (spool assigned to 2 workers simultaneously)
- Audit trail inconsistency (both TOMAR events logged but only one persists)

**Why it happens:**
Google Sheets has NO transaction support and ~200-500ms write latency. The "check-then-set" pattern creates a race window:
```
Time 0ms: Worker A reads spool → DISPONIBLE
Time 50ms: Worker B reads spool → DISPONIBLE (stale)
Time 100ms: Worker A writes ocupado_por_id=93
Time 200ms: Worker B writes ocupado_por_id=94 (overwrites A)
```

**How to avoid:**
1. **Optimistic Locking with Version Field:**
   - Add `version` column to Operaciones sheet
   - Read: Get current version with spool data
   - Write: Update WHERE tag_spool=X AND version=N, SET version=N+1
   - Detect: If 0 rows updated, conflict occurred
   - **Implementation:** Use gspread's `batch_update` with conditional range protection

2. **Pessimistic Locking via Metadata Log:**
   - Write TOMAR intent to Metadata BEFORE updating Operaciones
   - Use Metadata timestamp + worker_id as conflict arbiter
   - Query Metadata for conflicts in last 5 seconds
   - Reject if another TOMAR exists within window

3. **Backend Serialization:**
   - Use FastAPI in-memory lock (asyncio.Lock) per spool
   - Serialize TOMAR requests for same TAG_SPOOL
   - Does NOT protect against multiple backend instances

**Warning signs:**
- Frontend reports success but backend shows different ocupado_por_id
- Metadata shows 2 TOMAR events within 1 second for same spool
- Workers report "I took it but it's assigned to someone else"
- Test failure: Parallel TOMAR requests both succeed

**Phase to address:**
**Phase 1: Core State Machine** - MUST implement locking before any frontend integration. Write comprehensive race condition tests (pytest-asyncio with concurrent requests).

**Real example:**
Kraken Engineering (Jan 2025) solved MySQL race conditions with INSERT INTO SELECT combining optimistic checks with atomic writes. Similar pattern needed for Sheets.

---

### Pitfall 2: State Explosion from Dynamic States

**What goes wrong:**
v3.0 introduces composed states: `{operacion}_{occupation}_{progress}` (e.g., `ARM_OCUPADO_COMPLETADO`). With 3 operations × 3 occupation states × 3 progress states = 27 possible states, plus special cases:
- Reparación loops create infinite states (SOLD_REPARACION_EN_PROGRESO → SOLD_REPARACION_COMPLETADO → needs METROLOGIA again)
- State machine becomes unmaintainable (every new state requires transition logic for all 27+ existing states)
- Validation rules explode (can TOMAR from which states? Can PAUSAR from which?)
- Frontend struggles to handle 27+ UI states

**Why it happens:**
Classic state machine anti-pattern: using state combinations instead of hierarchical states or state context.

**How to avoid:**
1. **Hierarchical State Machines:**
   - Primary state: Operation phase (ARM, SOLD, METROLOGIA)
   - Sub-state: Occupation (DISPONIBLE, OCUPADO, PAUSADO)
   - Context: Progress (NOT_STARTED, EN_PROGRESO, COMPLETADO)
   - Total: 3 primary + 3 sub + 3 context = **9 manageable states**

2. **State Context Pattern:**
   ```python
   class SpoolState:
       operacion: OperationType  # ARM, SOLD, METROLOGIA
       occupation: OccupationStatus  # DISPONIBLE, OCUPADO, PAUSADO
       progress: ProgressStatus  # NOT_STARTED, EN_PROGRESO, COMPLETADO

       def can_tomar(self, worker: Worker) -> bool:
           # Simple rules: occupation == DISPONIBLE AND worker has role
           return self.occupation == DISPONIBLE and worker.has_role(self.operacion)
   ```

3. **Bounded State Model:**
   - Limit Reparación to 3 cycles max (prevent infinite loops)
   - Define explicit terminal states (COMPLETADO_FINAL, RECHAZADO)
   - Document state transitions in state diagram (not 27×27 matrix, but hierarchical tree)

**Warning signs:**
- Validation code has nested if/else blocks > 5 levels deep
- Adding new action requires editing > 10 files
- State transition tests number in hundreds
- Developers say "I don't understand all the states"
- Frontend has 27 different CSS classes for state colors

**Phase to address:**
**Phase 1: Core State Machine** - Design hierarchical model BEFORE implementation. Draw state diagram, get peer review. Add tests that enumerate all valid transitions (should be ~20, not 200).

**Real examples:**
- Game programming patterns: Hierarchical state machines for character AI (jumping while running = primary state + modifier)
- Automotive embedded systems: Finite state machines with context variables (engine state + temperature context)

---

### Pitfall 3: Breaking v2.1 Production During Refactor

**What goes wrong:**
Aggressive refactoring breaks working v2.1 system in production:
- Change INICIAR/COMPLETAR to TOMAR/PAUSAR/COMPLETAR without migration
- v2.1 data in Sheets incompatible with v3.0 schema
- 244 passing tests become 180 passing, 64 failing
- Production workers blocked from using system during "migration"
- Rollback fails because data format already changed

**Why it happens:**
Attempting too much at once. Refactoring without backward compatibility. No phased migration strategy.

**How to avoid:**
1. **Expand-Migrate-Contract Pattern:**
   - **Phase A (Expand):** Add new v3.0 columns WITHOUT removing v2.1 columns
     - Add: `ocupado_por_id`, `ocupado_desde`, `pausado_por_id`, `estado_operacion`
     - Keep: `Armador`, `Fecha_Armado`, `Soldador`, `Fecha_Soldadura` (v2.1)
   - **Phase B (Migrate):** Write to BOTH old and new columns simultaneously
     - TOMAR writes to both `ocupado_por_id` AND `Armador` (v2.1 format)
     - v2.1 API continues working, v3.0 API also works
   - **Phase C (Contract):** After validation, remove old columns
     - Only after 2+ weeks of dual writes with no issues

2. **Feature Flags for v3.0:**
   ```python
   # config.py
   V3_ENABLED = os.getenv("V3_ENABLED", "false") == "true"

   # routers/spools.py
   if V3_ENABLED:
       return await tomar_spool(spool_id, worker_id)  # v3.0
   else:
       return await iniciar_accion(spool_id, worker_id, "ARM")  # v2.1
   ```

3. **Parallel API Endpoints:**
   - Keep v2.1 endpoints: `/api/iniciar-accion`, `/api/completar-accion`
   - Add v3.0 endpoints: `/api/v3/tomar`, `/api/v3/pausar`
   - Both work simultaneously during migration period
   - Deprecate v2.1 after 1 month

4. **Comprehensive Test Suite BEFORE Refactor:**
   - Ensure 244/244 tests passing
   - Add integration tests for backward compatibility
   - Test rollback scenarios

**Warning signs:**
- "Let's just refactor everything at once"
- Deleting columns from Sheets before v3.0 deployed
- Test suite drops from 244 → 180 passing
- No rollback plan documented
- Production workers report "system not working"

**Phase to address:**
**Phase 0: Migration Strategy** - Document expand-migrate-contract plan BEFORE any code changes. Create branch protection: `main` requires 244/244 tests passing. Add backward compatibility tests.

**Real examples:**
- Refactoring at Scale (2025): Limit exposure with small stable steps, even if overall effort bigger
- PlanetScale (2025): Backward-compatible database changes using expand-contract pattern
- Vfunction (2025): Dark mode pattern - call both old and new implementations, compare results, return old results

---

### Pitfall 4: Polling Degradation with Scale

**What goes wrong:**
Frontend polls `/api/spools` every 2 seconds for "real-time" updates. Works fine with 5 workers and 50 spools. Breaks catastrophically with 30 workers and 500 spools:
- Backend CPU spikes to 100% (30 workers × 0.5 req/sec = 15 req/sec)
- Google Sheets API rate limits hit (quota: 100 req/min for reads)
- Sheets response time degrades: 200ms → 2,000ms (cold cache)
- Frontend shows stale data (poll interval can't keep up)
- Workers see conflicts not visible on their screen

**Why it happens:**
Polling architecture doesn't scale. Google Sheets has NO push notifications. No WebSocket support. Rate limits prevent high-frequency polling.

**How to avoid:**
1. **Intelligent Polling Strategy:**
   - **Exponential backoff:** 2s → 5s → 10s → 30s when no changes detected
   - **Smart refresh:** Poll only when user is on active spool list page
   - **Conditional requests:** Send `If-Modified-Since` header, skip parse if 304 Not Modified

2. **Backend Caching Layer:**
   ```python
   # services/cache_service.py
   class SpoolCache:
       def __init__(self):
           self._cache: Dict[str, Spool] = {}
           self._last_refresh: datetime = None

       async def get_spools(self, force_refresh: bool = False) -> List[Spool]:
           if force_refresh or self._stale():
               self._cache = await self._fetch_from_sheets()
               self._last_refresh = datetime.now()
           return list(self._cache.values())

       def _stale(self) -> bool:
           return datetime.now() - self._last_refresh > timedelta(seconds=5)
   ```
   - Cache spools for 5 seconds
   - Single Sheets request serves 15 concurrent frontend polls
   - Reduces Sheets API calls by 15×

3. **Optimistic UI Updates:**
   - When worker calls TOMAR, immediately update local state to OCUPADO
   - Show optimistic state while backend processes
   - Revert if backend returns error (conflict detected)
   - User sees instant feedback, backend syncs asynchronously

4. **Partial Data Loading:**
   - Don't poll entire 500-spool list every 2 seconds
   - Frontend sends filter: `?operacion=ARM&estado=DISPONIBLE`
   - Backend returns only relevant 20 spools
   - Reduces payload from 500 rows × 65 cols → 20 rows × 10 cols

**Warning signs:**
- Backend response time > 1 second during work hours
- Google Sheets API quota warnings in logs
- Frontend shows "Loading..." for > 3 seconds
- Workers report "screen not updating"
- CPU usage correlates with worker count

**Phase to address:**
**Phase 2: Real-Time Sync** - Implement caching BEFORE frontend polling. Load test with 30 concurrent users. Monitor Sheets API quota usage in production.

**Real examples:**
- Coefficient (2025): Hourly refresh scheduling for Sheets sync (true real-time impossible)
- PubNub (2025): Live polling systems use long polling + WebSockets for scale
- Google Sheets API limits: 100 read requests/minute per user per project

---

### Pitfall 5: Ignoring Event Sourcing Audit Trail

**What goes wrong:**
v3.0 refactor removes reliance on Metadata event log for state determination (v2.1 reads directly from Operaciones columns). Development team assumes Metadata is "optional" and:
- Skips writing TOMAR events to Metadata ("just update ocupado_por_id")
- Removes append-only constraint (allows UPDATE on Metadata)
- Doesn't log PAUSAR events (not in v2.1)
- Audit trail becomes incomplete: can't reconstruct what happened

When production incident occurs:
- Spool shows OCUPADO by worker 94, but worker says they PAUSAR'd it
- Metadata has no PAUSAR event (wasn't logged)
- Can't determine if bug, race condition, or user error
- Supervisor asks "Who worked on this spool yesterday?" → No way to know

**Why it happens:**
Event Sourcing considered "extra work" when Direct Read (v2.1 architecture) provides state. Teams undervalue audit trails until they need them.

**How to avoid:**
1. **Metadata is NON-NEGOTIABLE:**
   - EVERY state change MUST append to Metadata
   - TOMAR, PAUSAR, REANUDAR, COMPLETAR, CANCELAR all logged
   - Include before/after state snapshot in `metadata_json`

2. **Append-Only Enforcement:**
   ```python
   # repositories/sheets_repository.py
   class SheetsRepository:
       async def append_metadata(self, event: MetadataEvent) -> None:
           # ONLY append_row allowed, NEVER update_row
           metadata_sheet.append_row(event.to_row())
           # Raise exception if attempt to modify existing rows
   ```

3. **Test Audit Trail Completeness:**
   ```python
   # tests/integration/test_audit_trail.py
   async def test_tomar_logs_metadata():
       await tomar_spool(tag_spool="SP001", worker_id=93)

       metadata = await get_metadata_events(tag_spool="SP001")
       assert len(metadata) == 1
       assert metadata[0].evento_tipo == "TOMAR_ARM"
       assert metadata[0].worker_id == 93
   ```

4. **Metadata Schema v3.0:**
   - Add new columns: `accion` (TOMAR, PAUSAR, REANUDAR), `estado_antes`, `estado_despues`
   - Preserve v2.1 columns for backward compatibility
   - Document schema changes in migration guide

**Warning signs:**
- Code comments like "TODO: Add metadata logging later"
- Metadata sheet has gaps in timestamps
- Can't answer "Who worked on this spool last week?"
- Production incidents lack investigation data
- Developers say "We don't use Metadata anymore"

**Phase to address:**
**Phase 1: Core State Machine** - Update MetadataService to log all v3.0 actions. Add integration tests verifying metadata logging. Make append_metadata mandatory in all action workflows.

**Real examples:**
- Event Sourcing pattern: Metadata is source of truth for "what happened" (even if not for "current state")
- Manufacturing auditing: Regulatory compliance requires complete action history
- ZEUES v2.1: Already has Metadata audit trail, don't break it in v3.0

---

### Pitfall 6: Infinite Reparación Loops

**What goes wrong:**
Metrología finds defect → SOLD goes to Reparación → Metrología again → defect still exists → Reparación again → infinite loop:
- Spool stuck in SOLD_REPARACION forever
- No maximum cycle limit
- Frontend shows spool but workers can't proceed
- Production blocked on 1 bad spool

Worse: Complex loop states multiply:
- SOLD_REPARACION_EN_PROGRESO
- SOLD_REPARACION_PAUSADO
- SOLD_REPARACION_COMPLETADO → back to SOLD_DISPONIBLE → or METROLOGIA?

**Why it happens:**
No business rule for maximum rework cycles. State machine allows transitions back to earlier states without bounds.

**How to avoid:**
1. **Maximum Rework Cycles:**
   ```python
   # models/spool.py
   class Spool:
       reparacion_count: int = 0
       MAX_REPARACION = 3

       def can_reparar(self) -> bool:
           return self.reparacion_count < self.MAX_REPARACION

       def iniciar_reparacion(self):
           if not self.can_reparar():
               raise ReparacionLimitExceeded(
                   f"Spool {self.tag_spool} exceeded {self.MAX_REPARACION} repairs"
               )
           self.reparacion_count += 1
   ```

2. **Terminal States:**
   - Add explicit terminal states: `RECHAZADO`, `COMPLETADO_FINAL`
   - After 3 Reparación cycles, force supervisor decision:
     - APROBAR → COMPLETADO_FINAL
     - RECHAZAR → RECHAZADO (remove from production)
   - Terminal states CANNOT transition to other states

3. **Supervisor Override Workflow:**
   - After 3 repairs, only SUPERVISOR role can approve/reject
   - Frontend shows warning: "Spool requires supervisor decision"
   - Supervisor reviews history, makes final call

4. **Clear Reparación Workflow:**
   - Reparación is NOT a separate operation, it's a sub-phase of SOLD
   - Flow: SOLD_COMPLETADO → METROLOGIA → if defect found → SOLD_REPARACION
   - SOLD_REPARACION is special state within SOLD operation
   - After repair, goes directly to METROLOGIA (not SOLD_DISPONIBLE)

**Warning signs:**
- Spools with > 5 Reparación events in Metadata
- Frontend shows same spool in Reparación list for days
- Workers report "can't finish this spool"
- No maximum cycle enforcement in code
- State diagram has cycles with no exit condition

**Phase to address:**
**Phase 3: Reparación & Metrología** - Design Reparación workflow with bounded cycles BEFORE implementation. Add `reparacion_count` column to Operaciones. Create supervisor override endpoint.

**Real examples:**
- Manufacturing best practices: Maximum 3 rework attempts before quality review
- Game state machines: Boss battles have max attempt counters to prevent player frustration
- Healthcare systems: Medication refill limits prevent infinite loops

---

## Technical Debt Patterns

| Shortcut | Immediate Benefit | Long-term Cost | When Acceptable |
|----------|-------------------|----------------|-----------------|
| Skipping version column for optimistic locking | Faster implementation (1 day saved) | Race conditions in production, data corruption | **NEVER** - Race conditions are critical |
| Using flat state enum (27 states) instead of hierarchical | Simpler initial design (2 days saved) | Unmaintainable state machine, impossible to extend | **MVP only** - Refactor after validation |
| No backend caching, poll Sheets every request | Zero complexity (3 days saved) | API rate limits, slow response times, high costs | **Local dev only** - Production requires cache |
| No backward compatibility, hard cutover to v3.0 | Faster migration (1 week saved) | Production downtime, rollback impossible, data loss risk | **NEVER** - Business continuity critical |
| No Metadata logging for v3.0 actions | Simpler code (1 day saved) | No audit trail, regulatory non-compliance, debugging impossible | **NEVER** - Audit trail is regulatory requirement |
| No maximum Reparación cycles | Simpler workflow (2 days saved) | Infinite loops, production blockages, supervisor overhead | **MVP only** - Add limit after first production cycle |

---

## Integration Gotchas

| Integration | Common Mistake | Correct Approach |
|-------------|----------------|------------------|
| Google Sheets API | Hardcoded column indices (e.g., `row[37]` for Armador) | Dynamic header mapping: `headers["Armador"]` - Sheet structure changes frequently |
| Google Sheets Rate Limits | Polling every 2 seconds without caching | Backend cache (5s TTL) + exponential backoff + conditional requests |
| Google Sheets Transactions | Assuming atomic updates (check-then-set) | Optimistic locking with version field OR Metadata-based conflict detection |
| FastAPI Async | Using blocking `gspread` calls in async endpoints | Wrap gspread in `asyncio.to_thread()` or use `gspread-asyncio` |
| Next.js API Routes | Polling from client without debouncing | React Query with 5s staleTime + refetchOnWindowFocus: false |
| Event Sourcing | Reading Metadata to determine current state (v2.0 anti-pattern) | Direct Read from Operaciones columns (v2.1), use Metadata ONLY for audit |

---

## Performance Traps

| Trap | Symptoms | Prevention | When It Breaks |
|------|----------|------------|----------------|
| N+1 Sheets Queries | Response time 5s+, timeout errors | Batch read entire sheet once, filter in memory | > 10 concurrent users |
| Full Sheet Reload on Every Poll | 500 rows × 65 cols parsed every 2s | Backend cache with 5s TTL, serve from memory | > 5 concurrent users |
| No Index on TAG_SPOOL | O(n) lookup for every spool operation | In-memory dict: `{tag_spool: row_index}` | > 200 spools |
| Synchronous Sheets API Calls | Blocks FastAPI event loop, low throughput | Async wrappers or background tasks | > 3 concurrent requests |
| Frontend Polls All Spools | 500 spools × 10KB payload every 2s | Filter query: `?operacion=ARM&estado=DISPONIBLE` returns 20 spools | > 100 spools in DB |
| Metadata Sheet Linear Scan | 10,000+ rows scanned for audit queries | Add `tag_spool_index` column, filter before parse | > 5,000 Metadata rows |

---

## Security Mistakes

| Mistake | Risk | Prevention |
|---------|------|------------|
| No worker_id validation on TOMAR | Worker A can TOMAR on behalf of Worker B | Backend validates JWT worker_id matches request body |
| Frontend-only role checks | User modifies JS to bypass role filter | Backend validates worker has role for operacion before TOMAR |
| No CSRF protection on state changes | Attacker tricks worker into TOMAR via malicious link | Use FastAPI CSRF middleware or SameSite cookies |
| Exposing Google Service Account key | Attacker gains full Sheets access | Store in Railway secrets, NEVER in code/env files in git |
| No rate limiting on TOMAR endpoint | Attacker spams TOMAR, creates race conditions | FastAPI SlowAPI: max 5 TOMAR/minute per worker |
| Metadata allows UPDATE | Attacker modifies audit trail | Enforce append-only at repository layer, Sheets protection |

---

## UX Pitfalls

| Pitfall | User Impact | Better Approach |
|---------|-------------|-----------------|
| No optimistic UI on TOMAR | 2-5s delay before spool shows OCUPADO | Immediate local state update, revert on error |
| 27-state color coding | Workers can't remember what each color means | 3 colors only: Green (DISPONIBLE), Yellow (OCUPADO), Red (BLOQUEADO) |
| No conflict feedback | TOMAR fails silently, worker confused | Clear error: "Spool tomado por Juan (94) hace 30 segundos" |
| Real-time expectations with 5s polling | Workers see stale data, make decisions on outdated info | Set expectations: "Actualizado hace 3 segundos" timestamp |
| No loading states during TOMAR | Button remains clickable, duplicate requests | Disable button, show spinner, prevent double-click |
| PAUSAR without reason field | Can't debug why spools paused | Required text field: "Motivo de pausa" (min 10 chars) |

---

## "Looks Done But Isn't" Checklist

- [ ] **TOMAR endpoint:** Often missing race condition handling — verify concurrent TOMAR test with 10 parallel requests
- [ ] **State Machine:** Often missing hierarchical states — verify state diagram shows < 15 total states, not 27+
- [ ] **Backward Compatibility:** Often missing dual writes — verify v2.1 endpoints still work after v3.0 deploy
- [ ] **Metadata Logging:** Often missing v3.0 actions — verify TOMAR/PAUSAR/REANUDAR events in Metadata sheet
- [ ] **Backend Caching:** Often missing invalidation logic — verify cache clears after TOMAR write
- [ ] **Polling Strategy:** Often missing exponential backoff — verify poll interval increases when no changes
- [ ] **Reparación Cycles:** Often missing max count — verify > 3 repairs triggers supervisor flow
- [ ] **Error Handling:** Often missing conflict messages — verify frontend shows "Tomado por X" on conflict
- [ ] **Rate Limiting:** Often missing per-worker limits — verify 429 after 5 TOMAR in 10 seconds
- [ ] **Rollback Plan:** Often missing documented steps — verify can rollback v3.0 → v2.1 without data loss

---

## Recovery Strategies

| Pitfall | Recovery Cost | Recovery Steps |
|---------|---------------|----------------|
| Race condition in production | MEDIUM | 1. Add version column to Operaciones<br>2. Deploy optimistic locking fix<br>3. Audit Metadata for lost updates<br>4. Manual correction of corrupted spools |
| State explosion (27+ states) | HIGH | 1. Draw new hierarchical state diagram<br>2. Refactor to primary + sub-state model<br>3. Migrate existing spools to new states<br>4. Rewrite validation logic<br>5. Update frontend (1-2 weeks) |
| Broken backward compatibility | HIGH | 1. Restore v2.1 columns in Sheets<br>2. Implement expand-migrate-contract<br>3. Deploy dual-write code<br>4. Validate both APIs work<br>5. Gradual cutover (2-4 weeks) |
| API rate limits exceeded | LOW | 1. Add backend cache (5s TTL)<br>2. Reduce frontend poll frequency<br>3. Monitor quota usage<br>4. Request quota increase from Google |
| Missing Metadata events | MEDIUM | 1. Add mandatory metadata logging<br>2. Accept historical gap<br>3. Document incomplete audit period<br>4. Ensure all future events logged |
| Infinite Reparación loop | LOW | 1. Add reparacion_count column<br>2. Implement max cycle check<br>3. Manually resolve stuck spools<br>4. Create supervisor override flow |

---

## Pitfall-to-Phase Mapping

| Pitfall | Prevention Phase | Verification |
|---------|------------------|--------------|
| Race conditions on TOMAR | Phase 1: Core State Machine | Pytest: 10 parallel TOMAR requests, only 1 succeeds, 9 get conflict errors |
| State explosion | Phase 1: Core State Machine | State diagram review: < 15 states total, hierarchical structure documented |
| Breaking v2.1 production | Phase 0: Migration Strategy | Integration tests: v2.1 endpoints return 200 OK after v3.0 deploy |
| Polling degradation | Phase 2: Real-Time Sync | Load test: 30 concurrent users, response time < 1s, Sheets API < 80 req/min |
| Missing Metadata logging | Phase 1: Core State Machine | Integration tests: Every action creates 1 Metadata event, append-only enforced |
| Infinite Reparación loops | Phase 3: Reparación & Metrología | E2E test: 4th repair attempt triggers supervisor flow, spool BLOQUEADO |
| No backend caching | Phase 2: Real-Time Sync | Performance test: 100 req/s served from cache, Sheets called 1×/5sec |
| No optimistic UI | Phase 4: Frontend Integration | UX test: TOMAR shows OCUPADO immediately, reverts if conflict (< 200ms) |
| Hardcoded column indices | Phase 0: Migration Strategy | Smoke test: Add column to Sheets, API still works (dynamic header mapping) |
| No rate limiting | Phase 5: Security & Deployment | Penetration test: 10 TOMAR/sec returns 429 Too Many Requests |

---

## Sources

**Race Conditions & Locking (HIGH confidence):**
- Kraken Engineering Blog (Jan 2025): "Avoiding race conditions using MySQL locks" - https://engineering.kraken.tech/news/2025/01/20/mysql-race-conditions.html
- Medium (2025): "Solving Race Conditions With EF Core Optimistic Locking" - https://www.milanjovanovic.tech/blog/solving-race-conditions-with-ef-core-optimistic-locking
- Medium (2025): "The Art of Staying in Sync: How Distributed Systems Avoid Race Conditions" - https://medium.com/@alexglushenkov/the-art-of-staying-in-sync-how-distributed-systems-avoid-race-conditions-f59b58817e02

**Refactoring Production Systems (HIGH confidence):**
- Vfunction (2025): "7 Pitfalls to Avoid in Refactoring Projects" - https://vfunction.com/blog/7-pitfalls-to-avoid-in-application-refactoring-projects/
- O'Reilly (2025): "Refactoring at Scale: Messy Software Without Breaking It" - https://understandlegacycode.com/blog/key-points-of-refactoring-at-scale/
- SE Radio 656 (Feb 2025): "Rewrite versus Refactor" - https://se-radio.net/2025/02/se-radio-656-ivett-ordog-on-rewrite-versus-refactor/

**Backward-Compatible Migrations (HIGH confidence):**
- PlanetScale (2025): "Backward compatible database changes" - https://planetscale.com/blog/backward-compatible-databases-changes
- JetBrains Blog (Feb 2025): "Database Migrations in the Real World" - https://blog.jetbrains.com/idea/2025/02/database-migrations-in-the-real-world/
- PingCAP (2025): "Database Design Patterns for Ensuring Backward Compatibility" - https://www.pingcap.com/article/database-design-patterns-for-ensuring-backward-compatibility/

**State Machine Pitfalls (MEDIUM confidence):**
- Workflow Engine (2025): "Why Developers Never Use State Machines" - https://workflowengine.io/blog/why-developers-never-use-state-machines/
- State Machine Events (2025): "Common pitfalls to avoid when working with state machines" - https://statemachine.events/article/Common_pitfalls_to_avoid_when_working_with_state_machines.html
- Game Programming Patterns: "State Pattern" - https://gameprogrammingpatterns.com/state.html

**Google Sheets Real-Time Limitations (MEDIUM confidence):**
- Google Developers: "Google Sheets API Usage Limits" - https://developers.google.com/workspace/sheets/api/limits
- Coefficient (2025): "Real-time sync Google Sheets data to Salesforce" - https://coefficient.io/use-cases/real-time-sync-google-sheets-salesforce-dashboard
- Zapier Community (2025): "Google sheets API induced delays" - https://community.zapier.com/code-webhooks-52/google-sheets-api-induced-delays-37344

**Polling Architecture Performance (MEDIUM confidence):**
- GeeksforGeeks (2025): "Polling in System Design" - https://www.geeksforgeeks.org/system-design/polling-in-system-design/
- Merge Society (2025): "WebSocket vs Polling: Real-Time Web Communication Guide" - https://www.mergesociety.com/code-report/websocket-polling
- MIT Technology Review (Oct 2025): "Enabling real-time responsiveness with event-driven architecture" - https://www.technologyreview.com/2025/10/06/1124323/enabling-real-time-responsiveness-with-event-driven-architecture/

---

*Pitfalls research for: ZEUES v3.0 - Real-Time Location Tracking + State Management*
*Researched: 2026-01-26*
*Researcher: gsd-project-researcher agent*
