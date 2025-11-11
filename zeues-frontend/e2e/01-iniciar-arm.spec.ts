import { test, expect } from '@playwright/test';

/**
 * Flujo 1: INICIAR ARM (Armado)
 *
 * Verifica el flujo completo desde identificación hasta confirmación de éxito
 * para iniciar una acción de armado en un spool disponible.
 */
test.describe('Flujo 1: INICIAR ARM (Armado)', () => {

  test('debe completar el flujo INICIAR ARM exitosamente', async ({ page }) => {

    // ========================================
    // P1 - Identificación: Seleccionar trabajador
    // ========================================
    await test.step('P1 - Identificación', async () => {
      await page.goto('/');

      // Verificar que aparecen trabajadores del backend real
      await expect(page.getByText('Mauricio Rodriguez')).toBeVisible();
      await expect(page.getByText('Nicolás Rodriguez')).toBeVisible();
      await expect(page.getByText('Carlos Pimiento')).toBeVisible();

      // Seleccionar "Mauricio Rodriguez"
      await page.getByRole('button', { name: /Mauricio Rodriguez/i }).click();

      // Verificar navegación a /operacion
      await expect(page).toHaveURL('/operacion');
    });

    // ========================================
    // P2 - Operación: Seleccionar ARMADO
    // ========================================
    await test.step('P2 - Operación', async () => {
      // Verificar botón "Volver" existe
      const volverBtn = page.getByRole('button', { name: /Volver/i });
      await expect(volverBtn).toBeVisible();

      // Seleccionar "ARMADO (ARM)"
      await page.getByRole('button', { name: /ARMADO \(ARM\)/i }).click();

      // Verificar navegación a /tipo-interaccion
      await expect(page).toHaveURL('/tipo-interaccion');
    });

    // ========================================
    // P3 - Tipo Interacción: INICIAR ACCIÓN
    // ========================================
    await test.step('P3 - Tipo Interacción', async () => {
      // Verificar título muestra "ARMADO (ARM)"
      await expect(page.getByText(/ARMADO \(ARM\)/i)).toBeVisible();

      // Seleccionar "🔵 INICIAR ACCIÓN"
      await page.getByRole('button', { name: /INICIAR ACCIÓN/i }).click();

      // Verificar navegación a /seleccionar-spool?tipo=iniciar
      await expect(page).toHaveURL(/\/seleccionar-spool\?tipo=iniciar/);
    });

    // ========================================
    // P4 - Seleccionar Spool: Elegir spool disponible
    // ========================================
    await test.step('P4 - Seleccionar Spool', async () => {
      // Verificar título
      await expect(page.getByText(/Selecciona spool para INICIAR ARM/i)).toBeVisible();

      // Verificar que aparecen los 5 spools disponibles (arm=0)
      await expect(page.getByText('MK-1335-CW-25238-011')).toBeVisible();
      await expect(page.getByText('MK-1335-CW-25238-012')).toBeVisible();
      await expect(page.getByText('MK-1335-CW-25238-013')).toBeVisible();
      await expect(page.getByText('MK-1335-CW-25238-014')).toBeVisible();
      await expect(page.getByText('MK-1335-CW-25238-015')).toBeVisible();

      // Seleccionar primer spool
      await page.getByRole('button', { name: /MK-1335-CW-25238-011/ }).click();

      // Verificar navegación a /confirmar?tipo=iniciar
      await expect(page).toHaveURL(/\/confirmar\?tipo=iniciar/);
    });

    // ========================================
    // P5 - Confirmar: Revisar y confirmar acción
    // ========================================
    await test.step('P5 - Confirmar', async () => {
      // Verificar título
      await expect(page.getByText(/¿Confirmas INICIAR ARM\?/i)).toBeVisible();

      // Verificar resumen muestra los datos correctos
      await expect(page.getByText(/Mauricio Rodriguez/i)).toBeVisible();
      await expect(page.getByText(/ARMADO \(ARM\)/i)).toBeVisible();
      await expect(page.getByText(/MK-1335-CW-25238-011/i)).toBeVisible();

      // Verificar que existe botón "Cancelar"
      const cancelarBtn = page.getByRole('button', { name: /Cancelar/i });
      await expect(cancelarBtn).toBeVisible();

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
      // Verificar checkmark verde (SVG)
      const checkmark = page.locator('svg').first();
      await expect(checkmark).toBeVisible();

      // Verificar mensaje de éxito
      await expect(page.getByText(/¡Acción completada exitosamente!/i)).toBeVisible();

      // Verificar countdown (debe mostrar algún número entre 1 y 5)
      await expect(page.getByText(/Volviendo al inicio en \d+/i)).toBeVisible();

      // Verificar botones existen
      await expect(page.getByRole('button', { name: /REGISTRAR OTRA/i })).toBeVisible();
      await expect(page.getByRole('button', { name: /FINALIZAR/i })).toBeVisible();

      // Test botón "REGISTRAR OTRA" regresa a P1
      await page.getByRole('button', { name: /REGISTRAR OTRA/i }).click();
      await expect(page).toHaveURL('/');
    });
  });

  // ========================================
  // Test de navegación: Botón Volver
  // ========================================
  test('debe permitir retroceder con botón Volver', async ({ page }) => {
    await page.goto('/');

    // P1 → P2
    await page.getByRole('button', { name: /Mauricio Rodriguez/i }).click();
    await expect(page).toHaveURL('/operacion');

    // P2: Verificar Volver → P1
    await page.getByRole('button', { name: /Volver/i }).click();
    await expect(page).toHaveURL('/');
  });
});
