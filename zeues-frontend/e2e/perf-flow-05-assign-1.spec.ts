/**
 * T-136 Flow 5 — Assign armador to 1 LIBRE spool.
 *
 * Pre-hydrates localStorage with a single LIBRE spool (seq=1 in seed),
 * walks the modal chain (card → ARMADO → INICIAR → worker), and
 * measures end-to-end click-to-card-state-updated.
 *
 * Backend hits POST /api/v4/occupation/iniciar.
 *
 * NOTE: this flow MUTATES staging state. The spool used here will be
 * occupied by an armador after this test. Re-run scripts/seed_load_test.py
 * to reset before re-running this test.
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

// First LIBRE spool in seed (seq=1).
const LIBRE_TAG = 'MK-9999-CW-13278-001';
// Manuel Marchetti, role=Armador, id=11. Format displayed as "MM(11)" in occupation.
const ARMADOR_NAME = 'Manuel Marchetti';

test.describe('T-136 Flow 5 — assign armador to 1 LIBRE spool', () => {
  test.setTimeout(120_000);

  test('walks modal chain and assigns armador', async ({ page, context }) => {
    await hydrateLocalStorage(context, [LIBRE_TAG]);
    const { network, consoleLog } = attachInstrumentation(page);

    await page.goto('http://localhost:3000', { waitUntil: 'networkidle' });
    await expect.poll(async () => countSpoolCards(page), { timeout: 30_000 }).toBe(1);

    const networkBaseCount = network.length;

    // Click the LIBRE card. SpoolCard role=button with aria-label that
    // contains the TAG_SPOOL.
    const card = page.locator('[role="button"]').filter({ hasText: LIBRE_TAG }).first();
    await expect(card).toBeVisible();

    const t_chain0 = Date.now();
    await card.click();

    // OperationModal — pick "ARMADO".
    // For a LIBRE spool, ARMADO is the only valid op and INICIAR is
    // pre-selected, so this skips ActionModal and goes straight to
    // WorkerModal ("¿QUIÉN VA A ARMAR?").
    const armadoBtn = page.getByRole('button', { name: 'ARMADO' });
    await armadoBtn.waitFor({ state: 'visible', timeout: 10_000 });
    const t_op_modal_visible = Date.now() - t_chain0;
    await armadoBtn.click();

    // WorkerModal — pick Manuel Marchetti (skips ActionModal entirely)
    const workerBtn = page.getByRole('button', { name: `Seleccionar ${ARMADOR_NAME}` });
    await workerBtn.waitFor({ state: 'visible', timeout: 10_000 });
    const t_worker_modal_visible = Date.now() - t_chain0;
    await workerBtn.click();

    // After clicking worker, frontend calls iniciarSpool (or v4 endpoint).
    // The card transitions to EN_PROGRESO; we wait for the modal chain to
    // close (the WorkerModal "¿QUIÉN VA A ARMAR?" header disappears).
    await page.getByText('¿QUIÉN VA A ARMAR?').waitFor({ state: 'hidden', timeout: 30_000 });
    const t_chain_complete = Date.now() - t_chain0;

    const network_during = network.slice(networkBaseCount);

    const metrics = {
      flow: 'flow-05-assign-1',
      timestamp: new Date().toISOString(),
      notes: `Modal chain on LIBRE ${LIBRE_TAG} → assigned ${ARMADOR_NAME}. MUTATES STAGING.`,
      spool_cards_rendered: await countSpoolCards(page),
      timings_ms: {
        click_to_operation_modal_ms: t_op_modal_visible,
        click_to_worker_modal_ms: t_worker_modal_visible,
        click_to_chain_complete_ms: t_chain_complete,
      },
      ...summariseNetwork(network_during),
      ...summariseConsole(consoleLog),
    };

    await writeArtefacts(page, 'flow-05-assign-1', metrics, network, consoleLog);

    expect(metrics.console_error_count).toBe(0);
    expect(metrics.api_request_count).toBeGreaterThan(0);
  });
});
