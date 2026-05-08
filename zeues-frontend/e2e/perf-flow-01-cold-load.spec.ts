/**
 * T-136 Flow 1 — Home cold load with 200 spools.
 *
 * Pre-populates localStorage with all 200 staging tags, navigates fresh,
 * and measures: domcontentloaded, load, networkidle, total cards rendered.
 *
 * This is the canonical "first paint" timing for the home page under load.
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

test.describe('T-136 Flow 1 — home cold load', () => {
  test.setTimeout(120_000);

  test('renders 200 staging spools with no console errors', async ({ page, context }) => {
    const tags = loadFixtureTags();
    expect(tags.length).toBe(200);

    await hydrateLocalStorage(context, tags);
    const { network, consoleLog } = attachInstrumentation(page);

    const t0 = Date.now();
    const navResp = await page.goto('http://localhost:3000', { waitUntil: 'domcontentloaded' });
    const t_dcl = Date.now() - t0;
    expect(navResp?.ok()).toBeTruthy();

    await page.waitForLoadState('load', { timeout: 60_000 });
    const t_load = Date.now() - t0;

    await page.waitForLoadState('networkidle', { timeout: 60_000 });
    const t_idle = Date.now() - t0;

    const cards = await countSpoolCards(page);

    const metrics = {
      flow: 'flow-01-cold-load',
      timestamp: new Date().toISOString(),
      notes: 'Cold load with 200 staging spools pre-hydrated in localStorage.',
      spool_cards_rendered: cards,
      timings_ms: {
        domcontentloaded: t_dcl,
        load: t_load,
        network_idle: t_idle,
      },
      ...summariseNetwork(network),
      ...summariseConsole(consoleLog),
    };

    await writeArtefacts(page, 'flow-01-cold-load', metrics, network, consoleLog);

    expect(cards).toBe(200);
    expect(metrics.console_error_count).toBe(0);
  });
});
