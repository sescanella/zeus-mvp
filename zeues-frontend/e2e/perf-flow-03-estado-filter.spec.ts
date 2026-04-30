/**
 * T-136 Flow 3 — Apply estado filter (LIBRE / EN_ARM / etc).
 *
 * Open filter panel, click LIBRE chip, measure time until DOM only shows
 * LIBRE cards. Filter is client-side (SpoolCardList filters by estado_trabajo),
 * so no network requests expected.
 *
 * Expected: ~60 LIBRE cards visible (per seeding distribution).
 */
import { test, expect } from '@playwright/test';
import {
  loadFixtureTags,
  hydrateLocalStorage,
  attachInstrumentation,
  countSpoolCards,
  writeArtefacts,
  summariseNetwork,
  summariseConsole,
} from './helpers/perf-instrument';

test.describe('T-136 Flow 3 — estado filter', () => {
  test.setTimeout(120_000);

  test('clicking LIBRE chip filters list', async ({ page, context }) => {
    const tags = loadFixtureTags();
    await hydrateLocalStorage(context, tags);
    const { network, consoleLog } = attachInstrumentation(page);

    await page.goto('http://localhost:3000', { waitUntil: 'networkidle' });
    await expect.poll(async () => countSpoolCards(page), { timeout: 30_000 }).toBe(200);

    // Open filter panel
    const filterToggle = page.getByRole('button', { name: /filtros/i });
    await filterToggle.click();
    await page.waitForTimeout(200); // allow panel to render

    const networkBaseCount = network.length;

    // Click "LIBRE" chip — match the button by its text label.
    // ESTADO_LABELS[LIBRE] is "LIBRE" (per lib/constants.ts convention).
    const libreChip = page.getByRole('button', { name: /^[\d\s]*LIBRE$/i });

    const t0 = Date.now();
    await libreChip.click();
    await page.waitForTimeout(100); // commit
    const filtered = await countSpoolCards(page);
    const t_filter = Date.now() - t0;

    const network_during = network.slice(networkBaseCount);

    const metrics = {
      flow: 'flow-03-estado-filter',
      timestamp: new Date().toISOString(),
      notes: 'Clicked LIBRE estado chip on home with 200 cards.',
      spool_cards_rendered: filtered,
      timings_ms: {
        click_to_filter_ms: t_filter,
      },
      ...summariseNetwork(network_during),
      ...summariseConsole(consoleLog),
    };

    await writeArtefacts(page, 'flow-03-estado-filter', metrics, network, consoleLog);

    // Seed produces ~110 LIBRE-derived spools (60 truly free + ~50 partial/paused
    // states that lack ocupado_por and estado_detalle, which the backend
    // _derive_estado treats as LIBRE). See backend/models/spool_status.py.
    // Assert filtered list narrowed but is non-empty.
    expect(filtered).toBeGreaterThan(0);
    expect(filtered).toBeLessThan(200);
    expect(metrics.console_error_count).toBe(0);
    expect(metrics.api_request_count).toBe(0);
  });
});
