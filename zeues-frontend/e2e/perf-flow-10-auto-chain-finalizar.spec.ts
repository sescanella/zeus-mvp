/**
 * T-111 Flow 10 — Auto-chain next modal after FINALIZAR.
 *
 * Hotspot H1 of the north-star-clicks audit (T-109). Combined with T-110
 * (skip OperationModal), this closes the rama-A click count from 28B → 21B.
 *
 * After a successful FINALIZAR (ARM/SOLD/REP) the next move is deterministic:
 *   FINALIZAR ARM  → INICIAR SOLD       (open WorkerModal pre-set to SOLD)
 *   FINALIZAR SOLD → MET                (open MetrologiaModal directly)
 *   FINALIZAR REP  → MET                (open MetrologiaModal directly)
 *
 * Pre-T-111 the operator had to dismiss the success toast and re-click the
 * card. T-111 replicates the post-RECHAZADO handoff pattern (see
 * page.tsx:handleMetComplete) so the next modal opens automatically.
 *
 * **Why REP and not ARM/SOLD**: the ARM/SOLD path goes through UnionesModal
 * (select unions → submit), which has documented Playwright headless click
 * flakiness (see flow-07 in-spec note). The REP path uses
 * `executeFinalizarPausarDirect` and goes straight to the API — same chain
 * helper, far more deterministic to drive in a browser. The unit suite
 * (page.test.tsx T-111 block) covers ARM/SOLD/REP exhaustively.
 *
 * **Why route-mocking and not real backend**: this spec must NOT mutate
 * staging. We intercept POST /api/v4/reparacion/completar and return a
 * canned 200 — the chain helper is fully frontend, so a real backend
 * round-trip is unnecessary to validate the UX contract.
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

// EN_REPARACION seq 198 in seed (see scripts/seed_load_test.py DISTRIBUTION).
// Occupied by a worker, operacion_actual=REPARACION.
//
// NOTE on seq 197 (MK-9999-SW-33425-197): originally the chosen spool, but it
// was accidentally transitioned to PENDIENTE_METROLOGIA during T-111 spec
// development when an early version of this test used a wrong route-mock URL
// and the real backend completed the reparación instead of returning the
// canned response. Re-seeding via scripts/seed_load_test.py restores it.
const EN_REP_TAG = 'MK-9999-CW-29048-198';

test.describe('T-111 Flow 10 — auto-chain next modal after FINALIZAR', () => {
  test.setTimeout(120_000);

  test('FINALIZAR REP auto-opens MetrologiaModal without re-clicking the card', async ({
    page,
    context,
  }) => {
    await hydrateLocalStorage(context, [EN_REP_TAG]);
    const { network, consoleLog } = attachInstrumentation(page);

    // Intercept the FINALIZAR REP endpoint so the test does NOT mutate staging.
    // The endpoint returns a 200-OK shaped like a real success response.
    // /spool-status reads (hydration + post-FINALIZAR refresh) are deliberately
    // left to hit the real backend — the only mutation we silence is the
    // completar-reparación POST.
    let finalizarCalled = 0;
    await page.route('**/api/completar-reparacion', async (route) => {
      finalizarCalled += 1;
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({ ok: true, tag_spool: EN_REP_TAG }),
      });
    });

    await page.goto('http://localhost:3000', { waitUntil: 'networkidle' });
    await expect.poll(async () => countSpoolCards(page), { timeout: 30_000 }).toBe(1);

    const networkBaseCount = network.length;

    const card = page.locator('[role="button"]').filter({ hasText: EN_REP_TAG }).first();
    await expect(card).toBeVisible();

    const t_chain0 = Date.now();
    await card.click();

    // EN_REPARACION + occupied → ActionModal directly (FINALIZAR / PAUSAR).
    const finalizarBtn = page.getByRole('button', { name: /^FINALIZAR$/ });
    await finalizarBtn.waitFor({ state: 'visible', timeout: 10_000 });
    await finalizarBtn.click();

    // T-111 contract: MetrologiaModal MUST open automatically after the
    // FINALIZAR call resolves — NO intermediate card re-click. Probe for the
    // unique "Marcar como APROBADA" button (same as flow-08/09).
    const aprobadaBtn = page.getByRole('button', { name: 'Marcar como APROBADA' });
    await aprobadaBtn.waitFor({ state: 'visible', timeout: 10_000 });
    const t_metrologia_modal_visible = Date.now() - t_chain0;

    // Assert the chain truly happened: the FINALIZAR endpoint was hit and
    // the operator never had to re-click the card to reach metrología.
    expect(finalizarCalled).toBe(1);

    // ActionModal underneath must NOT still be visible (modalStack.clear()
    // cleared it before the chain pushed 'metrologia').
    const actionHeader = page.getByRole('heading', { name: /SELECCIONAR ACCIÓN/i });
    await expect(actionHeader).not.toBeVisible();

    const network_during = network.slice(networkBaseCount);

    const metrics = {
      flow: 'flow-10-auto-chain-finalizar-rep',
      timestamp: new Date().toISOString(),
      notes: `T-111: FINALIZAR REP for ${EN_REP_TAG} → MetrologiaModal opens automatically (no card re-click).`,
      spool_cards_rendered: 1,
      timings_ms: {
        click_finalizar_to_metrologia_modal_ms: t_metrologia_modal_visible,
      },
      ...summariseNetwork(network_during),
      ...summariseConsole(consoleLog),
    };

    await writeArtefacts(
      page,
      'flow-10-auto-chain-finalizar-rep',
      metrics,
      network,
      consoleLog,
    );

    // Same favicon allowlist as flow-09 — environmental noise from Brave/Chromium.
    const appErrors = consoleLog.filter(
      (m) =>
        (m.type === 'error' || m.type === 'pageerror') &&
        !(m.text + (m.location ?? '')).includes('favicon.ico'),
    );
    expect(appErrors).toEqual([]);
  });
});
