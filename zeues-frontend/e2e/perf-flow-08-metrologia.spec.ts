/**
 * T-136 Flow 8 — MetrologiaModal load for a MET_PEND spool.
 *
 * Picks a spool in PENDIENTE_METROLOGIA, opens MetrologiaModal via the
 * card click → operation chain, and measures time-to-modal-loaded.
 *
 * NOTE: does NOT actually approve or reject — this is the "Bug 7 path"
 * (T-131) which we deliberately don't exercise here to avoid mutating
 * staging state during the audit. The Bug 7 regression is still covered
 * by tests/unit/test_reparacion_machine.py (6 async tests, see notas.md).
 */
import { test, expect } from '@playwright/test';
import {
  hydrateLocalStorage,
  attachInstrumentation,
  countSpoolCards,
  writeArtefacts,
  summariseNetwork,
  summariseConsole,
} from './helpers/perf-instrument';

const MET_PEND_TAG = 'MK-9999-TW-37964-181';

test.describe('T-136 Flow 8 — MetrologiaModal load', () => {
  test.setTimeout(120_000);

  test('opens MetrologiaModal for MET_PEND spool', async ({ page, context }) => {
    await hydrateLocalStorage(context, [MET_PEND_TAG]);
    const { network, consoleLog } = attachInstrumentation(page);

    await page.goto('http://localhost:3000', { waitUntil: 'networkidle' });
    await expect.poll(async () => countSpoolCards(page), { timeout: 30_000 }).toBe(1);

    const networkBaseCount = network.length;

    // Click the card.
    const card = page.locator('[role="button"]').filter({ hasText: MET_PEND_TAG }).first();
    await expect(card).toBeVisible();

    const t_chain0 = Date.now();
    await card.click();

    // For a MET_PEND spool, OperationModal opens with METROLOGIA pre-routed.
    // We expect either:
    //   (a) OperationModal with METROLOGIA button visible, OR
    //   (b) MetrologiaModal directly.
    // Try METROLOGIA first; if not found, look for the modal heading.
    const metrologiaBtn = page.getByRole('button', { name: 'METROLOGIA' });
    let modalReached: 'operation' | 'direct' = 'operation';
    try {
      await metrologiaBtn.waitFor({ state: 'visible', timeout: 5_000 });
      await metrologiaBtn.click();
    } catch {
      // No OperationModal — likely went straight to MetrologiaModal
      modalReached = 'direct';
    }

    // MetrologiaModal — wait for "Marcar como APROBADA" button (always
    // present once the modal has loaded).
    const aprobadaBtn = page.getByRole('button', { name: 'Marcar como APROBADA' });
    await aprobadaBtn.waitFor({ state: 'visible', timeout: 30_000 });
    const t_metrologia_modal_loaded = Date.now() - t_chain0;

    const network_during = network.slice(networkBaseCount);

    const metrics = {
      flow: 'flow-08-metrologia',
      timestamp: new Date().toISOString(),
      notes: `Opened MetrologiaModal for ${MET_PEND_TAG} (MET_PEND). Did NOT approve/reject — Bug 7 covered by unit tests.`,
      spool_cards_rendered: 1,
      timings_ms: {
        click_to_metrologia_modal_loaded_ms: t_metrologia_modal_loaded,
      },
      ...summariseNetwork(network_during),
      ...summariseConsole(consoleLog),
      ...{
        modal_reached_via: modalReached,
      } as Record<string, unknown>,
    };

    await writeArtefacts(page, 'flow-08-metrologia', metrics, network, consoleLog);

    expect(metrics.console_error_count).toBe(0);
  });
});
