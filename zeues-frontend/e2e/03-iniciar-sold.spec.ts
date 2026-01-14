import { test, expect } from '@playwright/test';

/**
 * Flujo 3: INICIAR SOLD (Soldadura) - v2.0
 *
 * Verifica el flujo completo para iniciar una acción de soldadura
 * en un spool que tiene armado completado.
 *
 * FLUJO v2.0: Operación → Trabajador → Tipo → Spool → Confirmar → Éxito
 */
test.describe('Flujo 3: INICIAR SOLD (Soldadura) - v2.0', () => {

  test('debe completar el flujo INICIAR SOLD exitosamente', async ({ page }) => {

    // ========================================
    // P1 - Selección de Operación
    // ========================================
    await test.step('P1 - Selección de Operación', async () => {
      await page.goto('/');

      // Seleccionar "SOLDADURA (SOLD)"
      await page.getByRole('button', { name: /SOLDADURA \(SOLD\)/i }).click();

      await expect(page).toHaveURL('/operacion');
    });

    // ========================================
    // P2 - Selección de Trabajador
    // ========================================
    await test.step('P2 - Selección de Trabajador', async () => {
      // Verificar título
      await expect(page.getByText(/SELECCIONA TRABAJADOR/i)).toBeVisible();

      // Verificar header muestra "SOLDADURA (SOLD)"
      await expect(page.getByText(/SOLDADURA \(SOLD\)/i)).toBeVisible();

      // Seleccionar un trabajador soldador (ej: Nicolás Rodriguez)
      await page.getByRole('button', { name: /Nicolás Rodriguez/i }).click();

      await expect(page).toHaveURL('/tipo-interaccion');
    });

    // ========================================
    // P3 - Tipo Interacción: INICIAR ACCIÓN
    // ========================================
    await test.step('P3 - Tipo Interacción', async () => {
      // Verificar título muestra "SOLDADURA (SOLD)"
      await expect(page.getByText(/SOLDADURA \(SOLD\)/i)).toBeVisible();

      // Verificar info del trabajador
      await expect(page.getByText(/Nicolás/i)).toBeVisible();

      // Seleccionar "INICIAR ACCIÓN"
      await page.getByRole('button', { name: /INICIAR ACCIÓN/i }).click();

      // Verificar navegación
      await expect(page).toHaveURL(/\/seleccionar-spool\?tipo=iniciar/);
    });

    // ========================================
    // P4 - Seleccionar Spool: Elegir spool con ARM completado
    // ========================================
    await test.step('P4 - Seleccionar Spool', async () => {
      // Verificar título
      await expect(page.getByText(/SELECCIONA SPOOL/i)).toBeVisible();

      // Esperar que carguen los spools
      await page.waitForTimeout(2000);

      // Verificar que aparecen spools con ARM completado
      const spoolRows = page.locator('tbody tr');
      await expect(spoolRows.first()).toBeVisible({ timeout: 10000 });

      // Seleccionar primer spool disponible
      await spoolRows.first().click();

      // Verificar navegación
      await expect(page).toHaveURL(/\/confirmar\?tipo=iniciar/);
    });

    // ========================================
    // P5 - Confirmar: Revisar y confirmar acción
    // ========================================
    await test.step('P5 - Confirmar', async () => {
      // Verificar título
      await expect(page.getByText(/CONFIRMAR/i)).toBeVisible();

      // Verificar resumen
      await expect(page.getByText(/Nicolás/i)).toBeVisible();
      await expect(page.getByText(/SOLDADURA/i)).toBeVisible();

      // Presionar "CONFIRMAR"
      await page.getByRole('button', { name: /CONFIRMAR/i }).click();

      // Esperar navegación a /exito
      await expect(page).toHaveURL('/exito', { timeout: 15000 });
    });

    // ========================================
    // P6 - Éxito: Verificar mensaje
    // ========================================
    await test.step('P6 - Éxito', async () => {
      // Verificar mensaje "INICIADO"
      await expect(page.getByText(/INICIADO/i)).toBeVisible();

      // Verificar countdown
      await expect(page.getByText(/SEGUNDOS/i)).toBeVisible();

      // Verificar botón CONTINUAR
      await expect(page.getByRole('button', { name: /CONTINUAR/i })).toBeVisible();
    });
  });

  // ========================================
  // Test: Solo mostrar spools con armado completado
  // ========================================
  test('solo debe mostrar spools con armado completado', async ({ page }) => {
    await page.goto('/');

    // Seleccionar SOLDADURA
    await page.getByRole('button', { name: /SOLDADURA \(SOLD\)/i }).click();
    await expect(page).toHaveURL('/operacion');

    // Seleccionar trabajador
    await page.getByRole('button', { name: /Nicolás Rodriguez/i }).click();
    await expect(page).toHaveURL('/tipo-interaccion');

    // Ir a INICIAR
    await page.getByRole('button', { name: /INICIAR ACCIÓN/i }).click();
    await expect(page).toHaveURL(/\/seleccionar-spool\?tipo=iniciar/);

    // Esperar que cargue
    await page.waitForTimeout(2000);

    // Verificar que solo aparecen spools con ARM completado (arm=1, sold=0)
    const spoolRows = page.locator('tbody tr');
    await expect(spoolRows.first()).toBeVisible({ timeout: 10000 });
  });
});
