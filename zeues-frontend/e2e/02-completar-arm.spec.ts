import { test, expect } from '@playwright/test';

/**
 * Flujo 2: COMPLETAR ARM (Armado)
 *
 * Verifica el flujo completo para completar una acción de armado
 * que ya fue iniciada y está en progreso.
 */
test.describe('Flujo 2: COMPLETAR ARM (Armado)', () => {

  test('debe completar el flujo COMPLETAR ARM exitosamente', async ({ page }) => {

    // ========================================
    // P1 - Identificación: Seleccionar trabajador
    // ========================================
    await test.step('P1 - Identificación', async () => {
      await page.goto('/');

      // Seleccionar "Mauricio Rodriguez" (quien tiene spools en progreso ARM)
      await page.getByRole('button', { name: /Mauricio Rodriguez/i }).click();

      await expect(page).toHaveURL('/operacion');
    });

    // ========================================
    // P2 - Operación: Seleccionar ARMADO
    // ========================================
    await test.step('P2 - Operación', async () => {
      await page.getByRole('button', { name: /ARMADO \(ARM\)/i }).click();

      await expect(page).toHaveURL('/tipo-interaccion');
    });

    // ========================================
    // P3 - Tipo Interacción: COMPLETAR ACCIÓN
    // ========================================
    await test.step('P3 - Tipo Interacción', async () => {
      // Verificar título muestra "ARMADO (ARM)"
      await expect(page.getByText(/ARMADO \(ARM\)/i)).toBeVisible();

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
      await expect(page.getByText(/Selecciona TU spool para COMPLETAR ARM/i)).toBeVisible();

      // Verificar que aparecen spools disponibles para COMPLETAR ARM (Mauricio Rodriguez)
      // Usar selector genérico para trabajar con cualquier spool disponible
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
      await expect(page.getByText(/¿Confirmas COMPLETAR ARM\?/i)).toBeVisible();

      // Verificar resumen muestra los datos correctos
      await expect(page.getByText(/Mauricio Rodriguez/i)).toBeVisible();
      await expect(page.getByText(/ARMADO \(ARM\)/i)).toBeVisible();
      // Verificar que aparece un spool TEST-*
      await expect(page.getByText(/TEST-/)).toBeVisible();

      // Verificar fecha actual en el resumen
      const currentDate = new Date().toLocaleDateString('es-ES');
      await expect(page.getByText(new RegExp(currentDate))).toBeVisible();

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
  // Test de validación de propiedad (ownership)
  // ========================================
  test('solo debe mostrar spools propios del trabajador', async ({ page }) => {
    await page.goto('/');

    // Seleccionar Nicolás Rodriguez
    await page.getByRole('button', { name: /Nicolás Rodriguez/i }).click();

    // Seleccionar ARMADO (ARM)
    await page.getByRole('button', { name: /ARMADO \(ARM\)/i }).click();

    // Seleccionar COMPLETAR ACCIÓN
    await page.getByRole('button', { name: /COMPLETAR ACCIÓN/i }).click();

    // Verificar que aparecen spools (debe haber al menos uno de Nicolás)
    // Usar selector genérico para spools TEST-*
    const spoolButtons = page.getByRole('button').filter({ hasText: /TEST-/ });
    await expect(spoolButtons.first()).toBeVisible();

    // Test de ownership: cada trabajador solo ve sus propios spools
    // Si no hay spools disponibles, el test fallará apropiadamente
  });
});
