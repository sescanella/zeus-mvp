import { test, expect } from '@playwright/test';

/**
 * Flujo de Cancelación - v2.0
 * FLUJO v2.0: Operación → Trabajador → Tipo → CANCELAR → Confirmar → Éxito
 */
test.describe('Flujo de Cancelación - v2.0', () => {

  test('Test 10: debe permitir cancelar acción y resetear estado', async ({ page }) => {
    await page.goto('/');
    
    // P1-P2-P3: Flujo hasta seleccionar spool
    await page.getByRole('button', { name: /ARMADO \(ARM\)/i }).click();
    await page.getByRole('button', { name: /Mauricio Rodriguez/i }).click();
    await page.getByRole('button', { name: /INICIAR ACCIÓN/i }).click();
    await page.waitForTimeout(2000);
    
    const spoolRows = page.locator('tbody tr');
    await spoolRows.first().click();
    
    // P5: Cancelar desde confirmación
    const cancelarBtn = page.getByRole('button', { name: /CANCELAR/i });
    await expect(cancelarBtn).toBeVisible();
    await cancelarBtn.click();
    
    // Verificar redirección a inicio
    await expect(page).toHaveURL('/');
  });

  test('debe permitir cancelar desde flujo COMPLETAR ARM', async ({ page }) => {
    await page.goto('/');
    await page.getByRole('button', { name: /ARMADO \(ARM\)/i }).click();
    await page.getByRole('button', { name: /Mauricio Rodriguez/i }).click();
    await page.getByRole('button', { name: /COMPLETAR ACCIÓN/i }).click();
    await page.waitForTimeout(2000);
    
    const spoolRows = page.locator('tbody tr');
    await spoolRows.first().click();
    
    const cancelarBtn = page.getByRole('button', { name: /CANCELAR/i });
    await cancelarBtn.click();
    await expect(page).toHaveURL('/');
  });

  test.skip('debe permanecer en confirmación si usuario rechaza cancelar', async ({ page }) => {
    // Implementar modal de confirmación si aplica
  });
});
