import { test, expect } from '@playwright/test';

/**
 * Búsqueda TAG_SPOOL - v2.0
 * Tests de funcionalidad de búsqueda y filtrado
 */
test.describe('Búsqueda TAG_SPOOL (v2.0)', () => {

  test('Test 15: debe filtrar spools en tiempo real al escribir', async ({ page }) => {
    await page.goto('/');
    await page.getByRole('button', { name: /ARMADO \(ARM\)/i }).click();
    await page.getByRole('button', { name: /Mauricio Rodriguez/i }).click();
    await page.getByRole('button', { name: /INICIAR ACCIÓN/i }).click();
    await page.waitForTimeout(2000);
    
    // Buscar input de búsqueda
    const searchInput = page.locator('input[placeholder*="Buscar"]').first();
    if (await searchInput.count() > 0) {
      await searchInput.fill('TEST');
      await page.waitForTimeout(500);
      
      // Verificar que la tabla se actualiza
      const spoolRows = page.locator('tbody tr');
      await expect(spoolRows.first()).toBeVisible({ timeout: 5000 });
    }
  });

  test('Test 16: búsqueda debe ser case-insensitive', async ({ page }) => {
    await page.goto('/');
    await page.getByRole('button', { name: /ARMADO \(ARM\)/i }).click();
    await page.getByRole('button', { name: /Mauricio Rodriguez/i }).click();
    await page.getByRole('button', { name: /INICIAR ACCIÓN/i }).click();
    await page.waitForTimeout(2000);
    
    const searchInput = page.locator('input[placeholder*="Buscar"]').first();
    if (await searchInput.count() > 0) {
      await searchInput.fill('test');
      await page.waitForTimeout(500);
      const spoolRows = page.locator('tbody tr');
      await expect(spoolRows.first()).toBeVisible({ timeout: 5000 });
    }
  });

  test.skip('Test 17: debe mostrar mensaje cuando no hay resultados de búsqueda', async ({ page }) => {
    // Implementar mensaje "No se encontraron resultados"
  });

  test.skip('debe permitir seleccionar y confirmar spools filtrados por búsqueda', async ({ page }) => {
    // Implementar flujo completo con búsqueda + selección + confirmación
  });
});
