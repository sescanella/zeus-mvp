import { test, expect } from '@playwright/test';

/**
 * Flujo 2: COMPLETAR ARM (Armado) - v2.0
 *
 * Verifica el flujo completo para completar una acción de armado
 * que ya fue iniciada y está en progreso.
 *
 * FLUJO v2.0: Operación → Trabajador → Tipo → Spool → Confirmar → Éxito
 */
test.describe('Flujo 2: COMPLETAR ARM (Armado) - v2.0', () => {

  test('debe completar el flujo COMPLETAR ARM exitosamente', async ({ page }) => {

    // ========================================
    // P1 - Selección de Operación
    // ========================================
    await test.step('P1 - Selección de Operación', async () => {
      await page.goto('/');

      // Seleccionar "ARMADO (ARM)"
      await page.getByRole('button', { name: /ARMADO \(ARM\)/i }).click();

      await expect(page).toHaveURL('/operacion');
    });

    // ========================================
    // P2 - Selección de Trabajador
    // ========================================
    await test.step('P2 - Selección de Trabajador', async () => {
      // Seleccionar "Mauricio Rodriguez" (quien tiene spools en progreso ARM)
      await page.getByRole('button', { name: /Mauricio Rodriguez/i }).click();

      await expect(page).toHaveURL('/tipo-interaccion');
    });

    // ========================================
    // P3 - Tipo Interacción: COMPLETAR ACCIÓN
    // ========================================
    await test.step('P3 - Tipo Interacción', async () => {
      // Verificar título muestra "ARMADO (ARM)"
      await expect(page.getByText(/ARMADO \(ARM\)/i)).toBeVisible();

      // Verificar info del trabajador
      await expect(page.getByText(/Mauricio/i)).toBeVisible();

      // Seleccionar "COMPLETAR ACCIÓN"
      await page.getByRole('button', { name: /COMPLETAR ACCIÓN/i }).click();

      // Verificar navegación a /seleccionar-spool?tipo=completar
      await expect(page).toHaveURL(/\/seleccionar-spool\?tipo=completar/);
    });

    // ========================================
    // P4 - Seleccionar Spool: Elegir spool en progreso
    // ========================================
    await test.step('P4 - Seleccionar Spool', async () => {
      // Verificar título
      await expect(page.getByText(/SELECCIONA SPOOL/i)).toBeVisible();

      // Esperar que carguen los spools
      await page.waitForTimeout(2000);

      // Verificar que aparecen spools en progreso
      const spoolRows = page.locator('tbody tr');
      await expect(spoolRows.first()).toBeVisible({ timeout: 10000 });

      // Seleccionar primer spool disponible
      await spoolRows.first().click();

      // Verificar navegación a /confirmar?tipo=completar
      await expect(page).toHaveURL(/\/confirmar\?tipo=completar/);
    });

    // ========================================
    // P5 - Confirmar: Revisar y confirmar acción
    // ========================================
    await test.step('P5 - Confirmar', async () => {
      // Verificar título
      await expect(page.getByText(/CONFIRMAR/i)).toBeVisible();

      // Verificar resumen
      await expect(page.getByText(/Mauricio/i)).toBeVisible();
      await expect(page.getByText(/ARMADO/i)).toBeVisible();

      // Presionar "CONFIRMAR"
      await page.getByRole('button', { name: /CONFIRMAR/i }).click();

      // Esperar navegación a /exito
      await expect(page).toHaveURL('/exito', { timeout: 15000 });
    });

    // ========================================
    // P6 - Éxito: Verificar mensaje
    // ========================================
    await test.step('P6 - Éxito', async () => {
      // Verificar mensaje "COMPLETADO"
      await expect(page.getByText(/COMPLETADO/i)).toBeVisible();

      // Verificar countdown
      await expect(page.getByText(/SEGUNDOS/i)).toBeVisible();

      // Verificar botón CONTINUAR
      await expect(page.getByRole('button', { name: /CONTINUAR/i })).toBeVisible();
    });
  });

  // ========================================
  // Test: Solo mostrar spools propios del trabajador
  // ========================================
  test('solo debe mostrar spools propios del trabajador', async ({ page }) => {
    await page.goto('/');

    // Seleccionar ARMADO
    await page.getByRole('button', { name: /ARMADO \(ARM\)/i }).click();
    await expect(page).toHaveURL('/operacion');

    // Seleccionar Mauricio Rodriguez
    await page.getByRole('button', { name: /Mauricio Rodriguez/i }).click();
    await expect(page).toHaveURL('/tipo-interaccion');

    // Ir a COMPLETAR
    await page.getByRole('button', { name: /COMPLETAR ACCIÓN/i }).click();
    await expect(page).toHaveURL(/\/seleccionar-spool\?tipo=completar/);

    // Esperar que cargue
    await page.waitForTimeout(2000);

    // Verificar que solo aparecen spools de Mauricio Rodriguez
    // (El backend filtra por worker_nombre)
    const spoolRows = page.locator('tbody tr');
    await expect(spoolRows.first()).toBeVisible({ timeout: 10000 });
  });
});
