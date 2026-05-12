# Runbook — Supervisor Feature (server-side list + audit log)

**Audience:** developer maintaining the feature. NOT Matías. He doesn't run this.

**Context:** the supervisor feature replaces the old `localStorage`-backed home list with a server-side source of truth (`ZEUES_App_Audit_*` Sheets). It was built after Matías lost ~40 spools on 2026-05-08 because his tablet's localStorage was wiped. See plan: `~/.claude/plans/hoy-el-usuario-de-silly-crane.md`.

This runbook captures two things the automated test suite cannot cover:
- **Section A**: browser-based smoke checklist (run before merging, ~10 min).
- **Section B**: production deploy gate (run before promoting to Railway).

---

## Section A — Browser smoke checklist

Run these on a real browser (Chrome desktop is enough for the dev pass). Local backend on `:8001`, frontend dev on `:3000`. Audit sheet pointed at `ZEUES_App_Audit_DEV` (`1SZSM1wPndC8tm91WAooaZ74PZnAJ-0_0xTQsRX5jxa4`).

### A1. Server is the source of truth (multi-browser sync)

1. Open `http://localhost:3000` in Chrome.
2. Add any spool tag.
3. Open the same URL in **incognito** (separate session, separate localStorage).
4. ✓ if the spool from step 2 appears without any localStorage interaction.

This proves the list is server-backed; localStorage is no longer authoritative.

### A2. localStorage wipe survives — **the bug Matías reported**

1. Add 3 spools.
2. DevTools → Application → Storage → "Clear site data".
3. Reload.
4. ✓ if the 3 spools reappear from the server.

**If this fails, do NOT deploy.** This is the literal scenario that wiped Matías's list.

### A3. Migration — happy path (Layers 0 + 1)

1. Clear the audit Sheet's `Lista` tab manually.
2. DevTools console (legacy `priority` field, if present, is tolerated and
   silently discarded by the parser — this seed verifies that tolerance):
   ```js
   localStorage.setItem('zeues_v5_spool_tags',
     JSON.stringify([{tag:'FAKE-A',priority:1},{tag:'FAKE-B'}]));
   ```
3. Reload.
4. ✓ if:
   - `Lista` tab in `ZEUES_App_Audit_DEV` shows 2 rows (FAKE-A, FAKE-B).
   - `Snapshots_Legacy` tab shows 1 new row with the verbatim raw value.
   - `Audit` tab shows a `LIST_MIGRATE` event.
   - DevTools → localStorage → `zeues_v5_spool_tags` is **gone**.
5. Reload again. ✓ if no new migration runs (snapshot dedup by snapshot_id).

### A4. Migration — partial-failure path (the safety net)

Hard to simulate without backend fault injection. Skipped in dev pass; relies on the `Promise.allSettled` unit logic in `SpoolListContext.runMigrationIfPending()` plus tests for that path in `test_supervisor_service.py`.

If you want to verify, modify `SupervisorService.add_to_list` temporarily to raise on a specific tag, seed localStorage with a mix of pass-and-fail tags, and confirm:
- localStorage remains intact (NOT cleared) when at least one tag fails.
- `LIST_MIGRATE_PARTIAL` event lands in the `Audit` tab.
- Reload after restoring the service: the failed tags re-attempt migration and clear localStorage on full success.

### A5. Migration — Layer 2 lazy retry on mutation

1. Block `GET /api/supervisor/list` (DevTools → Network → block URL pattern).
2. Reload. List looks empty (mount-time migration is skipped because `getSupervisorList()` errored).
3. Seed localStorage as in A3.
4. Unblock the URL.
5. Click "Añadir Spool" → add any new tag.
6. ✓ if the legacy localStorage tags also migrate as part of that mutation flow (Layer 2 catches it before the new add).

### A6. Optimistic + rollback toast

1. Stop the backend (`pkill -f "backend.main:app"`).
2. Try to add a spool.
3. ✓ if:
   - The card appears immediately (optimistic).
   - Within seconds, the card disappears.
   - Toast: "No se pudo agregar el spool — reintenta."
4. Restart backend. Add succeeds normally.

### A7. Audit log fills

1. Open `/`, click around: open ActionModal, navigate, close.
2. Wait 30s for flush.
3. Query:
   ```bash
   SINCE=$(date -u -v-10M +%Y-%m-%dT%H:%M:%S)Z
   curl -s "http://localhost:8001/api/supervisor/audit?since=$SINCE" \
     | jq '.events | length'
   ```
4. ✓ if ≥ 4 events (SESSION_START + MODAL_OPEN + MODAL_CLOSE + …).
5. Open `Audit` tab in `ZEUES_App_Audit_DEV` → rows present.

### A8. Tab close flushes (sendBeacon)

1. Trigger one MODAL_OPEN by clicking on a card.
2. Close the tab **immediately** (do NOT wait 30s).
3. After ~5s, query the audit endpoint.
4. ✓ if the event landed (proves `sendBeacon` flushed during unload).

### A9. Multi-tab idempotency

1. Open two tabs of `/`.
2. In both, simultaneously add the same TAG.
3. ✓ if `Audit` tab shows 2 LIST_ADD events but `Lista` has exactly 1 row for that TAG (server-side upsert dedup).

---

## Section B — Production deploy gate

Run this checklist **before** promoting the merge to Railway.

### B1. PROD audit sheet is configured correctly

- [ ] `ZEUES_App_Audit_PROD` exists at `1CF_SNO8k6zkIEXukQ3etoFWUnD_3uWCHj0AxdENST7k`.
- [ ] Distinct from `ZEUES_App_Audit_DEV` (`1SZSM1wPndC8tm91WAooaZ74PZnAJ-0_0xTQsRX5jxa4`).
- [ ] Distinct from operations sheets `17iOaq2sv4mSOuJY4B8dGQIsWTTUKPspCtb7gk6u-MaQ` (PROD ops) and `14Rcrmc6c2RTkJG_fRgtSFDYWgP6Qt6zfciUtnl-9AMo` (staging ops).
- [ ] Three tabs present: `Lista`, `Audit`, `Snapshots_Legacy`.
- [ ] Each tab has the expected header row in row 1:
  - `Lista`: `TAG_SPOOL | Added_At | Updated_At | Notes`
  - `Audit`: `ID | Timestamp | Session_ID | Event_Type | TAG_SPOOL | Modal | Route | Payload_JSON`
  - `Snapshots_Legacy`: `Snapshot_ID | Captured_At | Raw_JSON | User_Agent`
- [ ] All three tabs have **zero data rows** (only the header).
- [ ] Service account `zeus-mvp@zeus-mvp.iam.gserviceaccount.com` is **Editor** on the PROD audit Sheet.

### B2. Railway env vars

```bash
railway variables | grep -E "AUDIT|GOOGLE_SHEET_ID"
```

- [ ] `GOOGLE_AUDIT_SHEET_ID` is `1CF_SNO8k6zkIEXukQ3etoFWUnD_3uWCHj0AxdENST7k` (PROD audit, NOT DEV).
- [ ] `GOOGLE_SHEET_ID` is `17iOaq2sv4mSOuJY4B8dGQIsWTTUKPspCtb7gk6u-MaQ` (PROD ops).
- [ ] These are not the same id.

### B3. Boot validator passes in prod

After the deploy, watch Railway logs. Expected lines:
- `✅ v4.0 schema validation PASSED`
- `✅ Audit spreadsheet schema PASSED`

If either is missing or there's a `❌ CRITICAL` line, **roll back** before Matías loads the app.

### B4. First production load (Matías's tablet)

Within 5 minutes of the deploy going live, ask Matías to open the app and tell you:
- [ ] His existing spools appear unchanged in the home list.
- [ ] No "lista vacía" surprise screen.

Open the live PROD audit Sheet and confirm:
- [ ] `Lista` tab has the same TAGs Matías sees in the app.
- [ ] `Snapshots_Legacy` has 1 new row with his raw localStorage as `Raw_JSON`.
- [ ] `Audit` tab has a `LIST_MIGRATE` event with `payload_json = {"migrated": N}` matching the count.

### B5. Recovery — if step B4 fails

If something looks wrong on Matías's first load:

1. **Do NOT let him interact further** — every click could overwrite the localStorage we need to recover from.
2. Open `ZEUES_App_Audit_PROD` → `Snapshots_Legacy` tab.
3. Find the snapshot row keyed by his current session (most recent `Captured_At`).
4. Copy the value of `Raw_JSON` cell.
5. On his tablet, DevTools → Application → Local Storage → manually create the key `zeues_v5_spool_tags` with the copied value as the value.
6. Reload. He's back to the pre-deploy state.
7. Diagnose the failure server-side, redeploy, and re-run B4.

---

## Notes

- Browser smoke checks are intentionally manual. Adding Playwright would balloon the project's test-infra footprint for a single-supervisor app.
- The "items 4a / 4b" partial-failure migration paths are covered by unit tests in `tests/unit/test_supervisor_service.py` (e.g. `test_add_audit_failure_does_not_block_upsert`). The browser version of those scenarios requires fault injection that isn't worth the effort for this single-user feature.
- Search query logging (every NV/TAG keystroke in AddSpoolModal) is **deliberately excluded** — high volume, low signal. If we ever need to investigate "why can't I find spool X", the existing audit log + the operations Sheet are sufficient.
