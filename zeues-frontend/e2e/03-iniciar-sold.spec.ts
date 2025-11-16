import { test, expect } from '@playwright/test';

/**
 * Flujo 3: INICIAR SOLD (Soldado)
 *
 * Verifica el flujo completo para iniciar una acción de soldado
 * en spools que ya tienen el armado completado (arm=1.0).
 */
test.describe('Flujo 3: INICIAR SOLD (Soldado)', () => {

  test('debe completar el flujo INICIAR SOLD exitosamente', async ({ page }) => {

    // ========================================
    // P1 - Identificación: Seleccionar trabajador
    // ========================================
    await test.step('P1 - Identificación', async () => {
      await page.goto('/');

      // Seleccionar "Carlos Pimiento" (soldador)
      await page.getByRole('button', { name: /Carlos Pimiento/i }).click();

      await expect(page).toHaveURL('/operacion');
    });

    // ========================================
    // P2 - Operación: Seleccionar SOLDADO
    // ========================================
    await test.step('P2 - Operación', async () => {
      // Seleccionar "SOLDADO (SOLD)"
      await page.getByRole('button', { name: /SOLDADO \(SOLD\)/i }).click();

      await expect(page).toHaveURL('/tipo-interaccion');
    });

    // ========================================
    // P3 - Tipo Interacción: INICIAR ACCIÓN
    // ========================================
    await test.step('P3 - Tipo Interacción', async () => {
      // Verificar título muestra "SOLDADO (SOLD)"
      await expect(page.getByText(/SOLDADO \(SOLD\)/i)).toBeVisible();

      // Seleccionar "🔵 INICIAR ACCIÓN"
      await page.getByRole('button', { name: /INICIAR ACCIÓN/i }).click();

      // Verificar navegación a /seleccionar-spool?tipo=iniciar
      await expect(page).toHaveURL(/\/seleccionar-spool\?tipo=iniciar/);
    });

    // ========================================
    // P4 - Seleccionar Spool: Elegir spool listo para soldar
    // ========================================
    await test.step('P4 - Seleccionar Spool', async () => {
      // Verificar título
      await expect(page.getByText(/Selecciona spool para INICIAR SOLD/i)).toBeVisible();

      // Verificar que aparecen spools listos para soldar (arm=1.0, sold=0)
      // Usar selector genérico para trabajar con cualquier spool disponible
      const spoolButtons = page.getByRole('button').filter({ hasText: /TEST-/ });
      await expect(spoolButtons.first()).toBeVisible();

      // Seleccionar primer spool disponible
      await spoolButtons.first().click();

      // Verificar navegación a /confirmar?tipo=iniciar
      await expect(page).toHaveURL(/\/confirmar\?tipo=iniciar/);
    });

    // ========================================
    // P5 - Confirmar: Revisar y confirmar acción
    // ========================================
    await test.step('P5 - Confirmar', async () => {
      // Verificar título
      await expect(page.getByText(/¿Confirmas INICIAR SOLD\?/i)).toBeVisible();

      // Verificar resumen muestra "SOLDADO (SOLD)"
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

      // Verificar countdown
      await expect(page.getByText(/Volviendo al inicio en \d+/i)).toBeVisible();

      // Test botón "REGISTRAR OTRA" regresa a P1
      await page.getByRole('button', { name: /REGISTRAR OTRA/i }).click();
      await expect(page).toHaveURL('/');
    });
  });

  // ========================================
  // Test de validación de prerequisito ARM
  // ========================================
  test('solo debe mostrar spools con armado completado', async ({ page }) => {
    await page.goto('/');

    // Seleccionar Carlos Pimiento
    await page.getByRole('button', { name: /Carlos Pimiento/i }).click();

    // Seleccionar SOLDADO (SOLD)
    await page.getByRole('button', { name: /SOLDADO \(SOLD\)/i }).click();

    // Seleccionar INICIAR ACCIÓN
    await page.getByRole('button', { name: /INICIAR ACCIÓN/i }).click();

    // Verificar que aparecen spools con arm=1.0 y sold=0
    const spoolButtons = page.getByRole('button').filter({ hasText: /TEST-/ });
    await expect(spoolButtons.first()).toBeVisible();

    // Verificar que NO aparecen spools con arm=0 (aún no armados)
    // Los spools TEST-ARM-BUFFER tienen arm=0 y no deben aparecer para INICIAR SOLD
    await expect(page.getByText(/TEST-ARM-BUFFER/i)).not.toBeVisible();
  });
});
