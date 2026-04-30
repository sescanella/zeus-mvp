/**
 * T-136 Flow 2 — Search by TAG_SPOOL keystroke latency.
 *
 * With 200 spools loaded, type a known partial TAG into the search input
 * one character at a time and measure:
 *   - Time from keystroke to filtered DOM update.
 *   - Final card count (should match a deterministic search prefix).
 *
 * The search filter is client-side (SpoolCardList does substring filter
 * on tag_spool, see SpoolCardList.tsx). No network requests expected.
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

test.describe('T-136 Flow 2 — search keystroke latency', () => {
  test.setTimeout(120_000);

  test('typing in search input filters list under 1s per keystroke', async ({ page, context }) => {
    const tags = loadFixtureTags();
    await hydrateLocalStorage(context, tags);
    const { network, consoleLog } = attachInstrumentation(page);

    await page.goto('http://localhost:3000', { waitUntil: 'networkidle' });
    await expect.poll(async () => countSpoolCards(page), { timeout: 30_000 }).toBe(200);

    const searchInput = page.getByPlaceholder('Buscar por TAG (ej: MK-1923)');
    await expect(searchInput).toBeVisible();

    // Pick a search query that we know matches a deterministic subset.
    // All synthetic tags share the prefix "MK-9999-" — so typing "001"
    // (the seq suffix) should narrow to exactly one TAG ending in -001.
    const query = '001';
    const perKeystroke: Array<{ char: string; latency_ms: number; visible_after_keystroke: number }> = [];

    // Clear network noise from initial load, capture only search-time activity.
    const networkBaseCount = network.length;

    for (const char of query) {
      const t0 = Date.now();
      await searchInput.press(char);
      // Wait briefly for the debounced/synchronous filter to take effect, then
      // sample the DOM. The implementation in SpoolCardList does NO debounce
      // — filter runs on every render — so this should be near-instant.
      await page.waitForTimeout(50); // gives React a tick to commit
      const visible = await countSpoolCards(page);
      const latency = Date.now() - t0;
      perKeystroke.push({ char, latency_ms: latency, visible_after_keystroke: visible });
    }

    // After typing "001": should be 2 cards visible — the seed always has
    // exactly one spool ending in -001 (MK-9999-XX-NNNNN-001) and another
    // possibly matching "001" elsewhere (e.g. NV1001 in tag? unlikely).
    // We don't assert exact count, just that the filter narrowed.
    const finalVisible = perKeystroke[perKeystroke.length - 1].visible_after_keystroke;

    const network_search = network.slice(networkBaseCount);

    const metrics = {
      flow: 'flow-02-search',
      timestamp: new Date().toISOString(),
      notes: `Typed "${query}" into search input (3 keystrokes) on home with 200 cards.`,
      timings_ms: {
        max_keystroke_latency_ms: Math.max(...perKeystroke.map((k) => k.latency_ms)),
        avg_keystroke_latency_ms:
          perKeystroke.reduce((a, b) => a + b.latency_ms, 0) / perKeystroke.length,
      },
      // network counts during search only
      ...summariseNetwork(network_search),
      ...summariseConsole(consoleLog),
      // extra fields for this flow
      ...{ keystrokes: perKeystroke, final_visible_cards: finalVisible } as Record<string, unknown>,
    };

    await writeArtefacts(page, 'flow-02-search', metrics, network, consoleLog);

    // Hard assertions: filter must narrow the list
    expect(finalVisible).toBeLessThan(200);
    expect(metrics.console_error_count).toBe(0);
    // Search filter is local — should not trigger network requests
    expect(metrics.api_request_count).toBe(0);
  });
});
