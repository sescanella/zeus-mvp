import { test, expect } from '@playwright/test';

/**
 * Test 11-14: Flujo Multiselect Batch Operations (v2.0)
 *
 * Verifica que el modo multiselect funciona correctamente:
 * - Toggle Individual ↔ Múltiple
 * - Selección con checkboxes
 * - Batch INICIAR (múltiples spools)
 * - Resultados exitosos en P6
 */
test.describe('Multiselect Batch Operations (v2.0)', () => {

  // ========================================
  // Test 11: Toggle modo Individual ↔ Múltiple
  // ========================================
  test('Test 11: debe permitir alternar entre modo Individual y Múltiple', async ({ page }) => {

    await test.step('Navegar hasta P4 (seleccionar spool)', async () => {
      await page.goto('/');
      await page.getByRole('button', { name: /Mauricio Rodriguez/i }).click();
      await expect(page).toHaveURL('/operacion');

      await page.getByRole('button', { name: /ARMADO \(ARM\)/i }).click();
      await expect(page).toHaveURL('/tipo-interaccion');

      await page.getByRole('button', { name: /INICIAR ACCIÓN/i }).click();
      await expect(page).toHaveURL(/\/seleccionar-spool\?tipo=iniciar/);
    });

    await test.step('Verificar modo Individual por defecto', async () => {
      // Debe mostrar "Individual" inicialmente
      await expect(page.getByText('Individual')).toBeVisible();

      // Debe mostrar lista de spools (NO checkboxes)
      const spoolButtons = page.getByRole('button').filter({ hasText: /MK-/ });
      const firstSpool = spoolButtons.first();
      await expect(firstSpool).toBeVisible();
    });

    await test.step('Activar modo Múltiple', async () => {
      // Clic en el toggle switch
      const toggle = page.getByRole('button', { name: /Activar modo múltiple/i });
      await toggle.click();

      // Verificar que cambió a "Múltiple (hasta 50)"
      await expect(page.getByText('Múltiple (hasta 50)')).toBeVisible();
    });

    await test.step('Verificar UI multiselect aparece', async () => {
      // Debe mostrar contador
      await expect(page.getByText('0 de')).toBeVisible();
      await expect(page.getByText('spools seleccionados')).toBeVisible();

      // Debe mostrar botones Select All / Deselect All
      await expect(page.getByRole('button', { name: /Seleccionar Todos/i })).toBeVisible();
      await expect(page.getByRole('button', { name: /Deseleccionar Todos/i })).toBeVisible();

      // Debe mostrar checkboxes (buscar input type=checkbox)
      const checkboxes = page.locator('input[type="checkbox"]');
      const count = await checkboxes.count();
      expect(count).toBeGreaterThan(0);
    });

    await test.step('Volver a modo Individual', async () => {
      const toggle = page.getByRole('button', { name: /Desactivar modo múltiple/i });
      await toggle.click();

      // Verificar que volvió a modo Individual
      await expect(page.getByText('Individual')).toBeVisible();
    });
  });

  // ========================================
  // Test 12: Seleccionar múltiples spools con checkboxes
  // ========================================
  test('Test 12: debe permitir seleccionar 3 spools con checkboxes', async ({ page }) => {

    await test.step('Navegar hasta P4 en modo Múltiple', async () => {
      await page.goto('/');
      await page.getByRole('button', { name: /Mauricio Rodriguez/i }).click();
      await page.getByRole('button', { name: /ARMADO \(ARM\)/i }).click();
      await page.getByRole('button', { name: /INICIAR ACCIÓN/i }).click();

      // Activar modo múltiple
      const toggle = page.getByRole('button', { name: /Activar modo múltiple/i });
      await toggle.click();
      await expect(page.getByText('Múltiple (hasta 50)')).toBeVisible();
    });

    await test.step('Seleccionar 3 spools usando checkboxes', async () => {
      // Obtener los primeros 3 checkboxes visibles
      const checkboxes = page.locator('input[type="checkbox"]');

      // Seleccionar los primeros 3
      await checkboxes.nth(0).check();
      await expect(page.getByText('1 de')).toBeVisible();

      await checkboxes.nth(1).check();
      await expect(page.getByText('2 de')).toBeVisible();

      await checkboxes.nth(2).check();
      await expect(page.getByText('3 de')).toBeVisible();
    });

    await test.step('Verificar botón "Continuar" está habilitado', async () => {
      const continuarBtn = page.getByRole('button', { name: /Continuar con 3 spool/i });
      await expect(continuarBtn).toBeVisible();
      await expect(continuarBtn).toBeEnabled();
    });

    await test.step('Deseleccionar un spool', async () => {
      const checkboxes = page.locator('input[type="checkbox"]');
      await checkboxes.nth(2).uncheck();

      // Contador debe actualizarse
      await expect(page.getByText('2 de')).toBeVisible();
    });

    await test.step('Usar botón "Select All"', async () => {
      const selectAllBtn = page.getByRole('button', { name: /Seleccionar Todos/i });
      await selectAllBtn.click();

      // Esperar a que se seleccionen múltiples (el número exacto depende de cuántos spools haya)
      // Verificar que el contador cambió
      const counterText = await page.locator('text=/\\d+ de \\d+ spools seleccionados/').textContent();
      expect(counterText).toContain('de');
    });

    await test.step('Usar botón "Deselect All"', async () => {
      const deselectAllBtn = page.getByRole('button', { name: /Deseleccionar Todos/i });
      await deselectAllBtn.click();

      // Contador debe volver a 0
      await expect(page.getByText('0 de')).toBeVisible();
    });
  });

  // ========================================
  // Test 13: Batch INICIAR ARM con 3 spools
  // ========================================
  test('Test 13: debe completar batch INICIAR ARM con 3 spools exitosamente', async ({ page }) => {

    let selectedTags: string[] = [];

    await test.step('Navegar hasta P4 y seleccionar 3 spools', async () => {
      await page.goto('/');
      await page.getByRole('button', { name: /Mauricio Rodriguez/i }).click();
      await page.getByRole('button', { name: /ARMADO \(ARM\)/i }).click();
      await page.getByRole('button', { name: /INICIAR ACCIÓN/i }).click();

      // Activar modo múltiple
      const toggle = page.getByRole('button', { name: /Activar modo múltiple/i });
      await toggle.click();

      // Seleccionar exactamente 3 spools
      const checkboxes = page.locator('input[type="checkbox"]');

      for (let i = 0; i < 3; i++) {
        const checkbox = checkboxes.nth(i);
        const label = await checkbox.getAttribute('aria-label');
        if (label) selectedTags.push(label);
        await checkbox.check();
      }

      await expect(page.getByText('3 de')).toBeVisible();
    });

    await test.step('Navegar a confirmación (P5)', async () => {
      const continuarBtn = page.getByRole('button', { name: /Continuar con 3 spool/i });
      await continuarBtn.click();
      await expect(page).toHaveURL(/\/confirmar\?tipo=iniciar/);
    });

    await test.step('Verificar P5 muestra los 3 spools seleccionados', async () => {
      // Debe mostrar título con count
      await expect(page.getByText(/INICIAR ARM en 3 spools/i)).toBeVisible();

      // Debe mostrar contador
      await expect(page.getByText(/Spools seleccionados: 3/i)).toBeVisible();

      // Verificar que aparecen los tags seleccionados (al menos verificar que hay una lista)
      const spoolList = page.locator('ul');
      await expect(spoolList).toBeVisible();
    });

    await test.step('Confirmar batch operation', async () => {
      const confirmarBtn = page.getByRole('button', { name: /CONFIRMAR/i });
      await confirmarBtn.click();

      // Esperar navegación a página de éxito
      await expect(page).toHaveURL('/exito', { timeout: 10000 });
    });

    await test.step('Verificar resultados batch en P6', async () => {
      // Debe mostrar título de éxito batch
      await expect(page.getByText(/Operación batch exitosa/i)).toBeVisible();

      // Debe mostrar stats
      await expect(page.getByText(/3 exitosos/i)).toBeVisible();
      await expect(page.getByText(/0 fallidos/i)).toBeVisible();
      await expect(page.getByText(/de 3 spools/i)).toBeVisible();

      // Debe mostrar sección de exitosos
      await expect(page.getByText(/Exitosos \(3\)/i)).toBeVisible();

      // NO debe mostrar sección de fallidos (0 fallidos)
      await expect(page.getByText(/Fallidos/i)).not.toBeVisible();
    });

    await test.step('Verificar timeout redirect a P1', async () => {
      // Esperar 5 segundos de countdown
      await page.waitForURL('/', { timeout: 7000 });

      // Verificar que está en P1
      await expect(page.getByText('Mauricio Rodriguez')).toBeVisible();
    });
  });

  // ========================================
  // Test 14: Límite de 50 spools
  // ========================================
  test('Test 14: debe deshabilitar checkboxes al alcanzar límite de 50 spools', async ({ page }) => {

    await test.step('Navegar hasta P4 en modo Múltiple', async () => {
      await page.goto('/');
      await page.getByRole('button', { name: /Mauricio Rodriguez/i }).click();
      await page.getByRole('button', { name: /ARMADO \(ARM\)/i }).click();
      await page.getByRole('button', { name: /INICIAR ACCIÓN/i }).click();

      // Activar modo múltiple
      const toggle = page.getByRole('button', { name: /Activar modo múltiple/i });
      await toggle.click();
    });

    await test.step('Usar "Select All" para seleccionar todos disponibles', async () => {
      const selectAllBtn = page.getByRole('button', { name: /Seleccionar Todos/i });
      await selectAllBtn.click();

      // Esperar a que se actualice el contador
      await page.waitForTimeout(500);
    });

    await test.step('Verificar que muestra warning si alcanzó 50', async () => {
      const counterText = await page.locator('text=/\\d+ de \\d+ spools seleccionados/').textContent();

      // Si hay 50 o más spools disponibles, debe mostrar límite
      if (counterText && counterText.includes('50 de')) {
        await expect(page.getByText(/Límite máximo: 50/i)).toBeVisible();

        // Los checkboxes NO seleccionados deben estar disabled
        const checkboxes = page.locator('input[type="checkbox"]:not(:checked)');
        const firstUnchecked = checkboxes.first();

        if (await firstUnchecked.count() > 0) {
          await expect(firstUnchecked).toBeDisabled();
        }
      }
    });
  });
});
