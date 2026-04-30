/**
 * T-136 Flow 4 — Add new spool via modal.
 *
 * Starts with an empty home (no localStorage). Opens AddSpoolModal,
 * waits for the available-spools list to load, picks the first row,
 * and measures end-to-end click→card-visible time.
 *
 * Captures:
 *   - Modal open + initial fetch (getSpoolsParaIniciar('ARM'))
 *   - Row click → SpoolListContext fetch (getSpoolStatus) → home re-render
 */
import { test, expect } from '@playwright/test';
import {
  attachInstrumentation,
  countSpoolCards,
  writeArtefacts,
  summariseNetwork,
  summariseConsole,
} from './helpers/perf-instrument';

test.describe('T-136 Flow 4 — add spool', () => {
  test.setTimeout(120_000);

  test('add a single spool via AddSpoolModal', async ({ page }) => {
    const { network, consoleLog } = attachInstrumentation(page);

    // Start with empty list (no localStorage hydration)
    await page.goto('http://localhost:3000', { waitUntil: 'networkidle' });
    await expect.poll(async () => countSpoolCards(page), { timeout: 10_000 }).toBe(0);

    // Click "Añadir spool" button
    const addBtn = page.getByRole('button', { name: 'Añadir spool al listado' });
    await expect(addBtn).toBeVisible();

    const networkBeforeOpen = network.length;
    const t_open0 = Date.now();
    await addBtn.click();

    // Wait for AddSpoolModal initial fetch to finish (getSpoolsParaIniciar('ARM'),
    // 136 spools). The modal does NOT render rows until the user types — so we
    // detect "ready to search" by waiting for the placeholder count text
    // "136 SPOOLS DISPONIBLES" to appear.
    await page.getByText(/\d+ SPOOLS DISPONIBLES/).waitFor({ state: 'visible', timeout: 30_000 });
    const t_modal_loaded = Date.now() - t_open0;
    const networkAfterModalLoad = network.length;

    // Type "MK" in the TAG search input to surface rows.
    const tagInput = page.getByPlaceholder('Ej: MK-1923');
    const t_type0 = Date.now();
    await tagInput.fill('MK');
    const firstRow = page.getByRole('button', { name: /^Seleccionar spool MK-9999-/ }).first();
    await firstRow.waitFor({ state: 'visible', timeout: 10_000 });
    const t_search_to_rows_visible = Date.now() - t_type0;

    // Pick the first row
    const t_click0 = Date.now();
    await firstRow.click();

    // After click, AddSpoolModal calls onAdd(tag) which dispatches
    // SpoolListContext.addSpool(tag) which fetches getSpoolStatus(tag).
    // Wait until exactly 1 spool card is visible on the home (modal stays
    // open after add — we close it ourselves after measurement).
    // First close the modal to see the home update properly.
    const closeBtn = page.getByRole('button', { name: 'Cerrar modal de agregar spools' });
    await closeBtn.click();

    await expect.poll(async () => countSpoolCards(page), { timeout: 30_000 }).toBeGreaterThanOrEqual(1);
    const t_visible = Date.now() - t_click0;
    const cards = await countSpoolCards(page);

    const network_during = network.slice(networkBeforeOpen);
    const network_modal_open = network.slice(networkBeforeOpen, networkAfterModalLoad);
    const network_after_click = network.slice(networkAfterModalLoad);

    const metrics = {
      flow: 'flow-04-add-spool',
      timestamp: new Date().toISOString(),
      notes: 'Empty home → open AddSpoolModal → pick first row → close → card appears.',
      spool_cards_rendered: cards,
      timings_ms: {
        modal_open_to_list_loaded_ms: t_modal_loaded,
        search_to_rows_visible_ms: t_search_to_rows_visible,
        click_to_card_visible_ms: t_visible,
      },
      ...summariseNetwork(network_during),
      ...summariseConsole(consoleLog),
      ...{
        network_during_modal_open: network_modal_open.length,
        network_after_click: network_after_click.length,
        network_modal_open_total_ms: network_modal_open.reduce(
          (a, b) => a + b.duration_ms,
          0
        ),
        network_after_click_total_ms: network_after_click.reduce(
          (a, b) => a + b.duration_ms,
          0
        ),
      } as Record<string, unknown>,
    };

    await writeArtefacts(page, 'flow-04-add-spool', metrics, network, consoleLog);

    expect(cards).toBeGreaterThanOrEqual(1);
    expect(metrics.console_error_count).toBe(0);
  });
});
