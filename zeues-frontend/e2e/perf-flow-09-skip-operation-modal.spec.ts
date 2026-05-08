/**
 * T-110 Flow 9 — Skip OperationModal in deterministic transitions.
 *
 * Hotspot H2 of the north-star-clicks audit (T-109). When a spool's next
 * step is deterministic, the OperationModal asks a question with one
 * possible answer. T-110 skips it.
 *
 * Two cases covered:
 *   - ARM_TERM (seq 111-130 in seed): fecha_armado set, fecha_soldadura
 *     null, not occupied. Click on card MUST go directly to WorkerModal
 *     for INICIAR SOLD (no OperationModal, no ActionModal).
 *   - SOLD_TERM (seq 171-180 in seed): PENDIENTE_METROLOGIA. Click on
 *     card MUST open MetrologiaModal directly (no OperationModal).
 *
 * Both cases save 1 click each — total -2 clicks per spool cycle.
 *
 * NOTE: this flow does NOT mutate staging — it only opens modals and
 * verifies headings, then closes without confirming. Safe to re-run.
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

// First ARM_TERM in seed (seq=111 — see scripts/seed_load_test.py DISTRIBUTION).
const ARM_TERM_TAG = 'MK-9999-SW-32216-111';
// First SOLD_TERM in seed (seq=171).
const SOLD_TERM_TAG = 'MK-9999-BW-78039-171';

test.describe('T-110 Flow 9 — skip OperationModal in deterministic transitions', () => {
  test.setTimeout(120_000);

  test('ARM_TERM card click skips OperationModal and lands on WorkerModal for SOLD', async ({
    page,
    context,
  }) => {
    await hydrateLocalStorage(context, [ARM_TERM_TAG]);
    const { network, consoleLog } = attachInstrumentation(page);

    await page.goto('http://localhost:3000', { waitUntil: 'networkidle' });
    await expect.poll(async () => countSpoolCards(page), { timeout: 30_000 }).toBe(1);

    const networkBaseCount = network.length;

    const card = page.locator('[role="button"]').filter({ hasText: ARM_TERM_TAG }).first();
    await expect(card).toBeVisible();

    const t_chain0 = Date.now();
    await card.click();

    // T-110 contract: OperationModal MUST NOT appear. The only valid next
    // op for an ARM_TERM spool is INICIAR SOLD, so deriveOperation returns
    // 'SOLD' and we land directly on WorkerModal.
    const operationHeader = page.getByRole('heading', { name: /SELECCIONAR OPERACIÓN/i });

    // WorkerModal heading for SOLD is rendered as "¿Quién va a soldar?"
    // in the DOM (CSS uppercases it for display). Match case-insensitively.
    const workerHeader = page.getByRole('heading', { name: /quién va a soldar/i });
    await workerHeader.waitFor({ state: 'visible', timeout: 10_000 });
    const t_worker_modal_visible = Date.now() - t_chain0;

    // Operation header must NOT have appeared at any point — verify it's
    // not present now (sufficient given the chain is synchronous).
    await expect(operationHeader).not.toBeVisible();

    const network_during = network.slice(networkBaseCount);

    const metrics = {
      flow: 'flow-09-skip-operation-modal-arm-term',
      timestamp: new Date().toISOString(),
      notes: `T-110: ARM_TERM card click → WorkerModal directly (skips OperationModal). Tag ${ARM_TERM_TAG}.`,
      spool_cards_rendered: 1,
      timings_ms: {
        click_to_worker_modal_ms: t_worker_modal_visible,
      },
      ...summariseNetwork(network_during),
      ...summariseConsole(consoleLog),
    };

    await writeArtefacts(
      page,
      'flow-09-skip-operation-modal-arm-term',
      metrics,
      network,
      consoleLog,
    );

    // Ignore environmental favicon 404 (Next.js dev server doesn't ship one
    // and Brave/Chromium auto-fetches it). Anything else is a real regression.
    const appErrors = consoleLog.filter(
      (m) =>
        (m.type === 'error' || m.type === 'pageerror') &&
        !(m.text + (m.location ?? '')).includes('favicon.ico'),
    );
    expect(appErrors).toEqual([]);
  });

  test('SOLD_TERM card click skips OperationModal and lands on MetrologiaModal', async ({
    page,
    context,
  }) => {
    await hydrateLocalStorage(context, [SOLD_TERM_TAG]);
    const { network, consoleLog } = attachInstrumentation(page);

    await page.goto('http://localhost:3000', { waitUntil: 'networkidle' });
    await expect.poll(async () => countSpoolCards(page), { timeout: 30_000 }).toBe(1);

    const networkBaseCount = network.length;

    const card = page.locator('[role="button"]').filter({ hasText: SOLD_TERM_TAG }).first();
    await expect(card).toBeVisible();

    const t_chain0 = Date.now();
    await card.click();

    // T-110 contract: SOLD_TERM (PENDIENTE_METROLOGIA) skips OperationModal
    // and opens MetrologiaModal directly. Same probe as flow-08 — wait for
    // "Marcar como APROBADA" button which is unique to MetrologiaModal.
    const operationHeader = page.getByRole('heading', { name: /SELECCIONAR OPERACIÓN/i });

    const aprobadaBtn = page.getByRole('button', { name: 'Marcar como APROBADA' });
    await aprobadaBtn.waitFor({ state: 'visible', timeout: 10_000 });
    const t_metrologia_modal_visible = Date.now() - t_chain0;

    await expect(operationHeader).not.toBeVisible();

    const network_during = network.slice(networkBaseCount);

    const metrics = {
      flow: 'flow-09-skip-operation-modal-sold-term',
      timestamp: new Date().toISOString(),
      notes: `T-110: SOLD_TERM card click → MetrologiaModal directly (skips OperationModal). Tag ${SOLD_TERM_TAG}.`,
      spool_cards_rendered: 1,
      timings_ms: {
        click_to_metrologia_modal_ms: t_metrologia_modal_visible,
      },
      ...summariseNetwork(network_during),
      ...summariseConsole(consoleLog),
    };

    await writeArtefacts(
      page,
      'flow-09-skip-operation-modal-sold-term',
      metrics,
      network,
      consoleLog,
    );

    // Ignore environmental favicon 404 (see flow-09 ARM_TERM test).
    const appErrors = consoleLog.filter(
      (m) =>
        (m.type === 'error' || m.type === 'pageerror') &&
        !(m.text + (m.location ?? '')).includes('favicon.ico'),
    );
    expect(appErrors).toEqual([]);
  });
});
