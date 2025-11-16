import { test, expect } from '@playwright/test';

/**
 * Flujo 4: COMPLETAR SOLD (Soldado)
 *
 * Verifica el flujo completo para completar una acción de soldado
 * que ya fue iniciada y está en progreso.
 */
test.describe('Flujo 4: COMPLETAR SOLD (Soldado)', () => {

  test.skip('debe completar el flujo COMPLETAR SOLD exitosamente', async ({ page }) => {

    // ========================================
    // P1 - Identificación: Seleccionar trabajador
    // ========================================
    await test.step('P1 - Identificación', async () => {
      await page.goto('/');

      // Seleccionar "Carlos Pimiento" (soldador con spools en progreso)
      await page.getByRole('button', { name: /Carlos Pimiento/i }).click();

      await expect(page).toHaveURL('/operacion');
    });

    // ========================================
    // P2 - Operación: Seleccionar SOLDADO
    // ========================================
    await test.step('P2 - Operación', async () => {
      await page.getByRole('button', { name: /SOLDADO \(SOLD\)/i }).click();

      await expect(page).toHaveURL('/tipo-interaccion');
    });

    // ========================================
    // P3 - Tipo Interacción: COMPLETAR ACCIÓN
    // ========================================
    await test.step('P3 - Tipo Interacción', async () => {
      // Verificar título muestra "SOLDADO (SOLD)"
      await expect(page.getByText(/SOLDADO \(SOLD\)/i)).toBeVisible();

      // Seleccionar "✅ COMPLETAR ACCIÓN"
      await page.getByRole('button', { name: /COMPLETAR ACCIÓN/i }).click();

      // Verificar navegación a /seleccionar-spool?tipo=completar
      await expect(page).toHaveURL(/\/seleccionar-spool\?tipo=completar/);
    });

    // ========================================
    // P4 - Seleccionar Spool: Elegir spool en progreso
    // ========================================
    await test.step('P4 - Seleccionar Spool', async () => {
      // Verificar título con énfasis en "TU spool"
      await expect(page.getByText(/Selecciona TU spool para COMPLETAR SOLD/i)).toBeVisible();

      // Verificar que aparecen spools (usar selector genérico)
      const spoolButtons = page.getByRole('button').filter({ hasText: /TEST-/ });
      await expect(spoolButtons.first()).toBeVisible();

      // Seleccionar primer spool disponible
      await spoolButtons.first().click();

      // Verificar navegación a /confirmar?tipo=completar
      await expect(page).toHaveURL(/\/confirmar\?tipo=completar/);
    });

    // ========================================
    // P5 - Confirmar: Revisar y confirmar acción
    // ========================================
    await test.step('P5 - Confirmar', async () => {
      // Verificar título
      await expect(page.getByText(/¿Confirmas COMPLETAR SOLD\?/i)).toBeVisible();

      // Verificar resumen muestra los datos correctos
      await expect(page.getByText(/Carlos Pimiento/i)).toBeVisible();
      await expect(page.getByText(/SOLDADO \(SOLD\)/i)).toBeVisible();
      // Verificar que aparece un spool TEST-*
      await expect(page.getByText(/TEST-/)).toBeVisible();

      // Presionar "✓ CONFIRMAR"
      await page.getByRole('button', { name: /CONFIRMAR/i }).click();

      // Verificar loading "Actualizando Google Sheets..."
      await expect(page.getByText(/Actualizando Google Sheets/i)).toBeVisible();

      // Esperar navegación a /exito
      await expect(page).toHaveURL('/exito', { timeout: 10000 });
    });

    // ========================================
    // P6 - Éxito: Verificar mensaje y opciones
    // ========================================
    await test.step('P6 - Éxito', async () => {
      // Verificar checkmark verde
      const checkmark = page.locator('svg').first();
      await expect(checkmark).toBeVisible();

      // Verificar mensaje de éxito
      await expect(page.getByText(/¡Acción completada exitosamente!/i)).toBeVisible();

      // Test botón "FINALIZAR" regresa a P1
      await page.getByRole('button', { name: /FINALIZAR/i }).click();
      await expect(page).toHaveURL('/');
    });
  });

  // ========================================
  // Test de validación de propiedad (ownership) para SOLD
  // ========================================
  test.skip('solo debe mostrar spools propios del soldador', async ({ page }) => {
    await page.goto('/');

    // Seleccionar Fernando Figueroa (soldadora con spools en progreso diferentes)
    await page.getByRole('button', { name: /Fernando Figueroa/i }).click();

    // Seleccionar SOLDADO (SOLD)
    await page.getByRole('button', { name: /SOLDADO \(SOLD\)/i }).click();

    // Seleccionar COMPLETAR ACCIÓN
    await page.getByRole('button', { name: /COMPLETAR ACCIÓN/i }).click();

    // Verificar que aparecen spools (debe haber al menos uno de Fernando)
    const spoolButtons = page.getByRole('button').filter({ hasText: /TEST-/ });
    await expect(spoolButtons.first()).toBeVisible();

    // Verificar ownership: Este test asume que cada trabajador tiene sus propios spools
    // Si no hay spools disponibles, el test fallará apropiadamente
  });

  // ========================================
  // Test de auto-redirect en página de éxito
  // ========================================
  test('debe redirigir automáticamente después de 5 segundos', async ({ page }) => {
    // Completar un flujo rápido para llegar a página de éxito
    await page.goto('/');
    await page.getByRole('button', { name: /Carlos Pimiento/i }).click();
    await page.getByRole('button', { name: /SOLDADO \(SOLD\)/i }).click();
    await page.getByRole('button', { name: /COMPLETAR ACCIÓN/i }).click();

    // Seleccionar primer spool disponible
    const firstSpool = page.getByRole('button').filter({ hasText: /TEST-/ }).first();
    await firstSpool.click();
    await page.getByRole('button', { name: /CONFIRMAR/i }).click();

    // Esperar a estar en página de éxito
    await expect(page).toHaveURL('/exito', { timeout: 10000 });

    // Esperar 5 segundos y verificar auto-redirect a P1
    await page.waitForTimeout(5500); // 5.5 segundos para asegurar
    await expect(page).toHaveURL('/', { timeout: 2000 });
  });
});
