/**
 * T-136 Flow 7 — UnionesModal load timing for a 7-union spool.
 *
 * Picks a spool in EN_SOLD with 7 unions, opens the SOLDADURA → INICIAR →
 * UnionesModal flow, and measures time-to-grid-loaded.
 *
 * NOTE: due to the same Playwright headless click reliability issues
 * documented in flow 6, this spec stops at "UnionesModal grid loaded"
 * and does NOT actually weld each union. The 7-union welding wall-clock
 * is approximated from per-call backend timings.
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

// EN_SOLD spool with 8 unions. Picked deterministically — see seed
// validation script. Other 8+ union candidates: 134 (10), 138 (10),
// 143 (10), 144 (6).
const EN_SOLD_TAG = 'MK-9999-CW-53456-141';

test.describe('T-136 Flow 7 — UnionesModal load for 7-union spool', () => {
  test.setTimeout(120_000);

  test('opens UnionesModal grid for an EN_SOLD spool', async ({ page, context }) => {
    await hydrateLocalStorage(context, [EN_SOLD_TAG]);
    const { network, consoleLog } = attachInstrumentation(page);

    await page.goto('http://localhost:3000', { waitUntil: 'networkidle' });
    await expect.poll(async () => countSpoolCards(page), { timeout: 30_000 }).toBe(1);

    const networkBaseCount = network.length;

    // Click the card. SpoolCard role=button.
    const card = page.locator('[role="button"]').filter({ hasText: EN_SOLD_TAG }).first();
    await expect(card).toBeVisible();

    const t_chain0 = Date.now();
    await card.click();

    // For an EN_SOLD spool, clicking the card opens ActionModal directly
    // (FINALIZAR/PAUSAR/CANCELAR) instead of OperationModal — the operation
    // is already known from the spool's state. We click FINALIZAR which
    // opens UnionesModal where the operator selects which unions to mark
    // as completed.
    const finalizarBtn = page.getByRole('button', { name: 'FINALIZAR' });
    await finalizarBtn.waitFor({ state: 'visible', timeout: 10_000 });
    await finalizarBtn.click();

    // UnionesModal loads from /api/v4/uniones/<tag>/disponibles + similar.
    // Detect by waiting for at least one DN union combobox.
    const firstUnionDN = page.getByRole('combobox', { name: /DN union \d+/ }).first();
    await firstUnionDN.waitFor({ state: 'visible', timeout: 30_000 });
    const t_uniones_grid_loaded = Date.now() - t_chain0;

    // Count visible union rows
    const unionCount = await page.getByRole('combobox', { name: /DN union \d+/ }).count();

    const network_during = network.slice(networkBaseCount);
    const disponibles_calls = network_during.filter((r) => r.url.includes('/disponibles')).length;

    const metrics = {
      flow: 'flow-07-uniones',
      timestamp: new Date().toISOString(),
      notes: `Opened UnionesModal for ${EN_SOLD_TAG} (EN_SOLD). Did NOT weld — see in-spec note.`,
      spool_cards_rendered: 1,
      timings_ms: {
        click_to_uniones_grid_loaded_ms: t_uniones_grid_loaded,
      },
      ...summariseNetwork(network_during),
      ...summariseConsole(consoleLog),
      ...{
        union_rows_visible: unionCount,
        disponibles_request_count: disponibles_calls,
      } as Record<string, unknown>,
    };

    await writeArtefacts(page, 'flow-07-uniones', metrics, network, consoleLog);

    expect(metrics.console_error_count).toBe(0);
    expect(unionCount).toBeGreaterThan(0);
  });
});
