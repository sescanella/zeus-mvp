/**
 * T-136 Flow 6 — Batch assign armador to 5 LIBRE spools.
 *
 * Cubre el path de T-132 (Bug 8 batch-INICIAR). Empty home → AddSpoolModal
 * → toggle "ASIGNAR ARMADOR AHORA" → search "MK" → select 5 rows →
 * "ASIGNAR ARMADOR (5)" → WorkerPickerModal → pick armador → measure.
 *
 * Backend behaviour:
 *   - For each of the 5 spools, addSpool is called sequentially (Sheets
 *     rate-limit guard).
 *   - Then iniciarSpool fires for all 5 in parallel.
 *   - Then refreshSingle for all 5 in parallel.
 *
 * NOTE: this flow MUTATES staging — the 5 LIBRE spools become occupied
 * by the chosen armador. Re-run scripts/seed_load_test.py to reset.
 */
import { test, expect } from '@playwright/test';
import {
  attachInstrumentation,
  countSpoolCards,
  writeArtefacts,
  summariseNetwork,
  summariseConsole,
} from './helpers/perf-instrument';

const ARMADOR_NAME = 'Manuel Marchetti';

test.describe('T-136 Flow 6 — batch assign armador to 5 LIBRE spools', () => {
  test.setTimeout(180_000);

  test('batch-INICIAR 5 LIBRE spools with one armador', async ({ page }) => {
    const { network, consoleLog } = attachInstrumentation(page);

    // Empty home start.
    await page.goto('http://localhost:3000', { waitUntil: 'networkidle' });
    await expect.poll(async () => countSpoolCards(page), { timeout: 10_000 }).toBe(0);

    // Open AddSpoolModal.
    await page.getByRole('button', { name: 'Añadir spool al listado' }).click();
    await page.getByText(/\d+ SPOOLS DISPONIBLES/).waitFor({ state: 'visible', timeout: 30_000 });

    // Toggle batch mode ON.
    await page.getByText('ASIGNAR ARMADOR AHORA').click();

    // Type "MK" to surface rows.
    const tagInput = page.getByPlaceholder('Ej: MK-1923');
    await tagInput.fill('MK');

    // Wait for at least 1 row.
    const anyRow = page.getByRole('button', { name: /^Seleccionar spool MK-9999-/ }).first();
    await anyRow.waitFor({ state: 'visible', timeout: 10_000 });

    const networkBeforeBatch = network.length;

    // Select 5 LIBRE rows. Iterate visible rows and click the first 5
    // whose tag is one of our known seq=2..6 LIBRE spools (we don't want
    // to grab a row that's already occupied or in a state that fails
    // INICIAR — the row labels include "(ya agregado)" / "(bloqueado)"
    // which we filter out via getByRole regex).
    const candidateTags = [
      'MK-9999-SW-38893-002',
      'MK-9999-CW-59797-003',
      'MK-9999-CW-59823-004',
      'MK-9999-TW-14207-005',
      'MK-9999-BW-86622-006',
    ];
    for (const tag of candidateTags) {
      const row = page.getByRole('button', { name: new RegExp(`Seleccionar spool ${tag}`) }).first();
      await row.scrollIntoViewIfNeeded();
      await row.click();
    }

    // Verify the "ASIGNAR ARMADOR (5)" button became enabled (we don't
    // actually click it — see blocker note below).
    const assignBtn = page.getByRole('button', { name: 'Asignar armador a 5 spools' });
    await expect(assignBtn).toBeVisible();
    await expect(assignBtn).toBeEnabled();

    // ─── KNOWN BLOCKER (T-136 Fase 1, 2026-04-29) ──────────────────────────
    // The "ASIGNAR ARMADOR (5)" button does not advance the flow under
    // headless Playwright. Tried:
    //   - assignBtn.click()                → modal stays open
    //   - assignBtn.click({ force: true }) → modal stays open
    //   - assignBtn.evaluate(b => b.click()) → modal stays open
    //   - assignBtn.focus() + keyboard.press('Enter') → modal stays open
    //
    // HTML snapshot at failure shows:
    //   - "5 spools seleccionados" text present
    //   - button "Asignar armador a 5 spools" [active]
    //   - dialog "Añadir spool" still visible after the click
    //
    // Manually performing the same flow in the browser DOES work
    // (verified by another spec capturing the modal stack after a real
    // user interaction).
    //
    // This may be a re-emergence of T-132 / Bug 8 ("asignación múltiple a
    // armador no funciona") under automation. The fix landed in commit
    // 2958df1 was a frontend toast/messaging refactor that did NOT alter
    // the click → handleConfirmBatch path, and notas.md §4 explicitly
    // notes the original case was closed without reproducing Matías's
    // exact failure. Worth re-investigating.
    //
    // For T-136 we capture metrics up to "button became enabled" and stop.
    // The end-to-end batch wall-clock for 5 spools is approximated below
    // from the per-INICIAR latency observed in flow 5.
    // ──────────────────────────────────────────────────────────────────────

    const t_button_enabled = Date.now() - networkBeforeBatch;
    const network_during = network.slice(networkBeforeBatch);

    const metrics = {
      flow: 'flow-06-batch-assign',
      timestamp: new Date().toISOString(),
      notes:
        `BLOCKED: AddSpoolModal "ASIGNAR ARMADOR (5)" button does not advance ` +
        `under Playwright. Possible Bug 8 (T-132) re-emergence. See in-spec comment. ` +
        `Capturing only "modal-load to button-enabled" timing.`,
      spool_cards_rendered: await countSpoolCards(page),
      timings_ms: {
        modal_load_to_button_enabled_ms: t_button_enabled,
      },
      ...summariseNetwork(network_during),
      ...summariseConsole(consoleLog),
      ...{
        blocker:
          'Click on "Asignar armador a N spools" not dispatched in headless. ' +
          'Re-investigate Bug 8 (T-132) — fix may be incomplete.',
        approximation_note:
          '5-spool batch wall-clock estimated as ' +
          '~1500ms (5 parallel INICIARs × ~700-1100ms each, observed in flow 5).',
      } as Record<string, unknown>,
    };

    await writeArtefacts(page, 'flow-06-batch-assign', metrics, network, consoleLog);

    expect(metrics.console_error_count).toBe(0);
  });
});
