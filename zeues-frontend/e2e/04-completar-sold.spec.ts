import { test, expect } from '@playwright/test';

/**
 * Flujo 4: COMPLETAR SOLD (Soldadura) - v2.0
 *
 * Verifica el flujo completo para completar una acción de soldadura
 * que ya fue iniciada y está en progreso.
 *
 * FLUJO v2.0: Operación → Trabajador → Tipo → Spool → Confirmar → Éxito
 */
test.describe('Flujo 4: COMPLETAR SOLD (Soldadura) - v2.0', () => {

  test('debe completar el flujo COMPLETAR SOLD exitosamente', async ({ page }) => {

    await test.step('P1 - Selección de Operación', async () => {
      await page.goto('/');
      await page.getByRole('button', { name: /SOLDADURA \(SOLD\)/i }).click();
      await expect(page).toHaveURL('/operacion');
    });

    await test.step('P2 - Selección de Trabajador', async () => {
      await page.getByRole('button', { name: /Nicolás Rodriguez/i }).click();
      await expect(page).toHaveURL('/tipo-interaccion');
    });

    await test.step('P3 - Tipo Interacción', async () => {
      await expect(page.getByText(/SOLDADURA \(SOLD\)/i)).toBeVisible();
      await page.getByRole('button', { name: /COMPLETAR ACCIÓN/i }).click();
      await expect(page).toHaveURL(/\/seleccionar-spool\?tipo=completar/);
    });

    await test.step('P4 - Seleccionar Spool', async () => {
      await page.waitForTimeout(2000);
      const spoolRows = page.locator('tbody tr');
      await expect(spoolRows.first()).toBeVisible({ timeout: 10000 });
      await spoolRows.first().click();
      await expect(page).toHaveURL(/\/confirmar\?tipo=completar/);
    });

    await test.step('P5 - Confirmar', async () => {
      await page.getByRole('button', { name: /CONFIRMAR/i }).click();
      await expect(page).toHaveURL('/exito', { timeout: 15000 });
    });

    await test.step('P6 - Éxito', async () => {
      await expect(page.getByText(/COMPLETADO/i)).toBeVisible();
      await expect(page.getByText(/SEGUNDOS/i)).toBeVisible();
    });
  });

  test('debe redirigir automáticamente después de 5 segundos', async ({ page }) => {
    await page.goto('/');
    await page.getByRole('button', { name: /SOLDADURA \(SOLD\)/i }).click();
    await page.getByRole('button', { name: /Nicolás Rodriguez/i }).click();
    await page.getByRole('button', { name: /COMPLETAR ACCIÓN/i }).click();
    await page.waitForTimeout(2000);
    const spoolRows = page.locator('tbody tr');
    await spoolRows.first().click();
    await page.getByRole('button', { name: /CONFIRMAR/i }).click();
    await expect(page).toHaveURL('/exito', { timeout: 15000 });
    await expect(page).toHaveURL('/', { timeout: 8000 });
  });
});
