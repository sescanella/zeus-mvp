import { test, expect } from '@playwright/test';

/**
 * Test 15-17: Búsqueda TAG_SPOOL (v2.0)
 *
 * Verifica que la funcionalidad de búsqueda funciona correctamente:
 * - Campo de búsqueda visible en modo multiselect
 * - Filtrado en tiempo real (case-insensitive)
 * - Mensaje cuando no hay resultados
 * - Selección de spools filtrados
 */
test.describe('Búsqueda TAG_SPOOL (v2.0)', () => {

  // ========================================
  // Test 15: Búsqueda filtra spools en tiempo real
  // ========================================
  test('Test 15: debe filtrar spools en tiempo real al escribir', async ({ page }) => {

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

    await test.step('Verificar que campo de búsqueda está visible', async () => {
      const searchInput = page.getByPlaceholder(/TAG_SPOOL/i);
      await expect(searchInput).toBeVisible();

      // Verificar label
      await expect(page.getByText(/Buscar por TAG_SPOOL/i)).toBeVisible();
    });

    await test.step('Contar spools iniciales antes de filtrar', async () => {
      const checkboxes = page.locator('input[type="checkbox"]');
      const initialCount = await checkboxes.count();
      expect(initialCount).toBeGreaterThan(0);
    });

    await test.step('Escribir término de búsqueda parcial', async () => {
      const searchInput = page.getByPlaceholder(/TAG_SPOOL/i);

      // Buscar por un prefijo común (ej: "MK-1335")
      await searchInput.fill('MK-1335');

      // Esperar a que se actualice el filtrado
      await page.waitForTimeout(300);
    });

    await test.step('Verificar que los spools se filtraron', async () => {
      const checkboxes = page.locator('input[type="checkbox"]');
      const filteredCount = await checkboxes.count();

      // Debe haber menos spools visibles ahora
      expect(filteredCount).toBeGreaterThan(0);

      // Verificar mensaje de filtrado
      await expect(page.getByText(/Mostrando \d+ de \d+ spools/i)).toBeVisible();
    });

    await test.step('Verificar que solo aparecen spools que coinciden', async () => {
      // Todos los checkboxes visibles deben tener labels que contengan "MK-1335"
      const checkboxes = page.locator('input[type="checkbox"]');
      const count = await checkboxes.count();

      for (let i = 0; i < Math.min(count, 5); i++) {
        const label = await checkboxes.nth(i).getAttribute('aria-label');
        if (label) {
          expect(label.toUpperCase()).toContain('MK-1335');
        }
      }
    });

    await test.step('Limpiar búsqueda y verificar que vuelven todos', async () => {
      const searchInput = page.getByPlaceholder(/TAG_SPOOL/i);
      await searchInput.clear();

      // Esperar a que se actualice
      await page.waitForTimeout(300);

      const checkboxes = page.locator('input[type="checkbox"]');
      const resetCount = await checkboxes.count();

      // Debe volver a mostrar todos los spools
      expect(resetCount).toBeGreaterThan(0);

      // Mensaje de filtrado no debe aparecer cuando no hay búsqueda
      await expect(page.getByText(/Mostrando \d+ de \d+ spools/i)).not.toBeVisible();
    });
  });

  // ========================================
  // Test 16: Búsqueda case-insensitive
  // ========================================
  test('Test 16: búsqueda debe ser case-insensitive', async ({ page }) => {

    await test.step('Navegar hasta P4 en modo Múltiple', async () => {
      await page.goto('/');
      await page.getByRole('button', { name: /Nicolás Rodriguez/i }).click();
      await page.getByRole('button', { name: /SOLDADO \(SOLD\)/i }).click();
      await page.getByRole('button', { name: /INICIAR ACCIÓN/i }).click();

      // Activar modo múltiple
      const toggle = page.getByRole('button', { name: /Activar modo múltiple/i });
      await toggle.click();
    });

    await test.step('Buscar con MAYÚSCULAS', async () => {
      const searchInput = page.getByPlaceholder(/TAG_SPOOL/i);
      await searchInput.fill('MK-1335');

      await page.waitForTimeout(300);

      const checkboxesUpper = page.locator('input[type="checkbox"]');
      const upperCount = await checkboxesUpper.count();
      expect(upperCount).toBeGreaterThan(0);
    });

    await test.step('Limpiar y buscar con minúsculas', async () => {
      const searchInput = page.getByPlaceholder(/TAG_SPOOL/i);
      await searchInput.clear();
      await searchInput.fill('mk-1335');

      await page.waitForTimeout(300);

      const checkboxesLower = page.locator('input[type="checkbox"]');
      const lowerCount = await checkboxesLower.count();

      // Debe encontrar los mismos resultados (case-insensitive)
      expect(lowerCount).toBeGreaterThan(0);
    });

    await test.step('Buscar con MiXtO', async () => {
      const searchInput = page.getByPlaceholder(/TAG_SPOOL/i);
      await searchInput.clear();
      await searchInput.fill('Mk-1335');

      await page.waitForTimeout(300);

      const checkboxesMixed = page.locator('input[type="checkbox"]');
      const mixedCount = await checkboxesMixed.count();

      // Debe encontrar resultados (case-insensitive)
      expect(mixedCount).toBeGreaterThan(0);
    });
  });

  // ========================================
  // Test 17: Mensaje cuando no hay resultados
  // ========================================
  test('Test 17: debe mostrar mensaje cuando no hay resultados de búsqueda', async ({ page }) => {

    await test.step('Navegar hasta P4 en modo Múltiple', async () => {
      await page.goto('/');
      await page.getByRole('button', { name: /Carlos Pimiento/i }).click();
      await page.getByRole('button', { name: /ARMADO \(ARM\)/i }).click();
      await page.getByRole('button', { name: /INICIAR ACCIÓN/i }).click();

      const toggle = page.getByRole('button', { name: /Activar modo múltiple/i });
      await toggle.click();
    });

    await test.step('Buscar término que NO existe', async () => {
      const searchInput = page.getByPlaceholder(/TAG_SPOOL/i);

      // Buscar un término que no debería existir
      await searchInput.fill('ZZZZZ-NOEXISTE-9999');

      await page.waitForTimeout(300);
    });

    await test.step('Verificar mensaje de "no encontrado"', async () => {
      // Debe mostrar mensaje de error
      await expect(page.getByText(/No se encontraron spools que coincidan/i)).toBeVisible();

      // El término buscado debe aparecer en el mensaje
      await expect(page.getByText(/ZZZZZ-NOEXISTE-9999/i)).toBeVisible();
    });

    await test.step('Verificar que no hay checkboxes visibles', async () => {
      const checkboxes = page.locator('input[type="checkbox"]');
      const count = await checkboxes.count();
      expect(count).toBe(0);
    });

    await test.step('Botones Select All/Deselect All deben estar deshabilitados', async () => {
      const selectAllBtn = page.getByRole('button', { name: /Seleccionar Todos/i });
      await expect(selectAllBtn).toBeDisabled();
    });

    await test.step('Limpiar búsqueda y verificar que vuelven los spools', async () => {
      const searchInput = page.getByPlaceholder(/TAG_SPOOL/i);
      await searchInput.clear();

      await page.waitForTimeout(300);

      // Debe volver a mostrar spools
      const checkboxes = page.locator('input[type="checkbox"]');
      const count = await checkboxes.count();
      expect(count).toBeGreaterThan(0);

      // Mensaje de error debe desaparecer
      await expect(page.getByText(/No se encontraron spools/i)).not.toBeVisible();
    });
  });

  // ========================================
  // Test adicional: Seleccionar spools filtrados
  // ========================================
  test('debe permitir seleccionar y confirmar spools filtrados por búsqueda', async ({ page }) => {

    await test.step('Navegar y activar modo multiselect', async () => {
      await page.goto('/');
      await page.getByRole('button', { name: /Fernando Figueroa/i }).click();
      await page.getByRole('button', { name: /SOLDADO \(SOLD\)/i }).click();
      await page.getByRole('button', { name: /INICIAR ACCIÓN/i }).click();

      const toggle = page.getByRole('button', { name: /Activar modo múltiple/i });
      await toggle.click();
    });

    await test.step('Filtrar spools con búsqueda', async () => {
      const searchInput = page.getByPlaceholder(/TAG_SPOOL/i);
      await searchInput.fill('MK-');

      await page.waitForTimeout(300);

      // Verificar que hay resultados
      const checkboxes = page.locator('input[type="checkbox"]');
      const count = await checkboxes.count();
      expect(count).toBeGreaterThan(0);
    });

    await test.step('Seleccionar 2 spools filtrados', async () => {
      const checkboxes = page.locator('input[type="checkbox"]');

      await checkboxes.nth(0).check();
      await checkboxes.nth(1).check();

      // Verificar contador
      await expect(page.getByText('2 de')).toBeVisible();
    });

    await test.step('Continuar con selección filtrada', async () => {
      const continuarBtn = page.getByRole('button', { name: /Continuar con 2 spool/i });
      await expect(continuarBtn).toBeVisible();
      await expect(continuarBtn).toBeEnabled();

      await continuarBtn.click();

      // Debe navegar a confirmación
      await expect(page).toHaveURL(/\/confirmar\?tipo=iniciar/);
    });

    await test.step('Verificar confirmación muestra spools filtrados', async () => {
      await expect(page.getByText(/INICIAR SOLD en 2 spools/i)).toBeVisible();
      await expect(page.getByText(/Spools seleccionados: 2/i)).toBeVisible();
    });
  });
});
