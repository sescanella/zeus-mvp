import { test, expect } from '@playwright/test';

/**
 * Test 10: Flujo de Cancelación
 *
 * Verifica que el botón "Cancelar" funciona correctamente en la página
 * de confirmación y resetea el estado de la aplicación.
 */
test.describe('Flujo de Cancelación', () => {

  // ========================================
  // Test 10: Cancelar en página de confirmación
  // ========================================
  test('Test 10: debe permitir cancelar acción y resetear estado', async ({ page }) => {

    await test.step('Completar flujo hasta página de confirmación', async () => {
      await page.goto('/');

      // P1: Seleccionar trabajador
      await page.getByRole('button', { name: /Juan Pérez/i }).click();
      await expect(page).toHaveURL('/operacion');

      // P2: Seleccionar operación ARMADO
      await page.getByRole('button', { name: /ARMADO \(ARM\)/i }).click();
      await expect(page).toHaveURL('/tipo-interaccion');

      // P3: Seleccionar INICIAR
      await page.getByRole('button', { name: /INICIAR ACCIÓN/i }).click();
      await expect(page).toHaveURL(/\/seleccionar-spool\?tipo=iniciar/);

      // P4: Seleccionar un spool
      const firstSpool = page.getByRole('button').filter({ hasText: /MK-/ }).first();
      await firstSpool.click();
      await expect(page).toHaveURL(/\/confirmar\?tipo=iniciar/);
    });

    await test.step('Verificar botón Cancelar existe', async () => {
      const cancelarBtn = page.getByRole('button', { name: /Cancelar/i });
      await expect(cancelarBtn).toBeVisible();
    });

    await test.step('Clic en Cancelar y confirmar alerta', async () => {
      // Escuchar el diálogo de confirmación
      page.on('dialog', async (dialog) => {
        // Verificar mensaje de confirmación
        expect(dialog.message()).toContain('¿Seguro que quieres cancelar?');
        // Aceptar la cancelación
        await dialog.accept();
      });

      // Clic en botón Cancelar
      await page.getByRole('button', { name: /Cancelar/i }).click();
    });

    await test.step('Verificar redirección a página inicial (P1)', async () => {
      // Debe redirigir a la página de identificación (raíz)
      await expect(page).toHaveURL('/', { timeout: 3000 });
    });

    await test.step('Verificar estado está limpio', async () => {
      // Verificar que aparecen los trabajadores nuevamente
      await expect(page.getByText('Juan Pérez')).toBeVisible();
      await expect(page.getByText('María López')).toBeVisible();
      await expect(page.getByText('Carlos Díaz')).toBeVisible();
      await expect(page.getByText('Ana García')).toBeVisible();
    });

    await test.step('Verificar que puede iniciar nuevo flujo', async () => {
      // Seleccionar trabajador nuevamente para verificar que el estado se reseteó
      await page.getByRole('button', { name: /María López/i }).click();
      await expect(page).toHaveURL('/operacion');

      // Verificar que puede seleccionar operación
      await expect(page.getByText(/ARMADO \(ARM\)/i)).toBeVisible();
      await expect(page.getByText(/SOLDADO \(SOLD\)/i)).toBeVisible();
    });
  });

  // ========================================
  // Test adicional: Cancelar desde flujo COMPLETAR
  // ========================================
  test('debe permitir cancelar desde flujo COMPLETAR ARM', async ({ page }) => {

    await test.step('Completar flujo COMPLETAR hasta confirmación', async () => {
      await page.goto('/');
      await page.getByRole('button', { name: /Juan Pérez/i }).click();
      await page.getByRole('button', { name: /ARMADO \(ARM\)/i }).click();
      await page.getByRole('button', { name: /COMPLETAR ACCIÓN/i }).click();

      // Seleccionar spool en progreso
      const firstSpool = page.getByRole('button').filter({ hasText: /MK-/ }).first();
      await firstSpool.click();
      await expect(page).toHaveURL(/\/confirmar\?tipo=completar/);
    });

    await test.step('Cancelar y verificar reset', async () => {
      // Configurar handler para el diálogo
      page.on('dialog', async (dialog) => {
        await dialog.accept();
      });

      await page.getByRole('button', { name: /Cancelar/i }).click();

      // Verificar redirección a P1
      await expect(page).toHaveURL('/', { timeout: 3000 });
    });
  });

  // ========================================
  // Test adicional: Rechazar cancelación
  // ========================================
  test('debe permanecer en confirmación si usuario rechaza cancelar', async ({ page }) => {

    await test.step('Llegar a página de confirmación', async () => {
      await page.goto('/');
      await page.getByRole('button', { name: /Carlos Díaz/i }).click();
      await page.getByRole('button', { name: /SOLDADO \(SOLD\)/i }).click();
      await page.getByRole('button', { name: /INICIAR ACCIÓN/i }).click();

      const firstSpool = page.getByRole('button').filter({ hasText: /MK-/ }).first();
      await firstSpool.click();
      await expect(page).toHaveURL(/\/confirmar\?tipo=iniciar/);
    });

    await test.step('Rechazar cancelación en el diálogo', async () => {
      // Rechazar el diálogo (dismiss)
      page.on('dialog', async (dialog) => {
        expect(dialog.message()).toContain('¿Seguro que quieres cancelar?');
        await dialog.dismiss(); // Rechazar la cancelación
      });

      await page.getByRole('button', { name: /Cancelar/i }).click();

      // Esperar un momento para que procese
      await page.waitForTimeout(500);
    });

    await test.step('Verificar que permanece en página de confirmación', async () => {
      // Debe permanecer en /confirmar
      await expect(page).toHaveURL(/\/confirmar\?tipo=iniciar/);

      // Verificar que sigue viendo el botón CONFIRMAR
      await expect(page.getByRole('button', { name: /CONFIRMAR/i })).toBeVisible();

      // Verificar que sigue viendo los datos de confirmación
      await expect(page.getByText(/Carlos Díaz/i)).toBeVisible();
      await expect(page.getByText(/SOLDADO \(SOLD\)/i)).toBeVisible();
    });
  });
});
