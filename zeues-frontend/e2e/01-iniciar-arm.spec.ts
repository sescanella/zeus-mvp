import { test, expect } from '@playwright/test';

/**
 * Flujo 1: INICIAR ARM (Armado) - v2.0
 *
 * Verifica el flujo completo desde selección de operación hasta confirmación de éxito
 * para iniciar una acción de armado en un spool disponible.
 *
 * FLUJO v2.0: Operación → Trabajador → Tipo → Spool → Confirmar → Éxito
 */
test.describe('Flujo 1: INICIAR ARM (Armado) - v2.0', () => {

  test('debe completar el flujo INICIAR ARM exitosamente', async ({ page }) => {

    // ========================================
    // P1 - Selección de Operación
    // ========================================
    await test.step('P1 - Selección de Operación', async () => {
      await page.goto('/');

      // Verificar que aparecen las 3 operaciones
      await expect(page.getByRole('button', { name: /ARMADO \(ARM\)/i })).toBeVisible();
      await expect(page.getByRole('button', { name: /SOLDADURA \(SOLD\)/i })).toBeVisible();
      await expect(page.getByRole('button', { name: /METROLOGÍA/i })).toBeVisible();

      // Seleccionar "ARMADO (ARM)"
      await page.getByRole('button', { name: /ARMADO \(ARM\)/i }).click();

      // Verificar navegación a /operacion
      await expect(page).toHaveURL('/operacion');
    });

    // ========================================
    // P2 - Selección de Trabajador
    // ========================================
    await test.step('P2 - Selección de Trabajador', async () => {
      // Verificar título muestra "SELECCIONA TRABAJADOR"
      await expect(page.getByText(/SELECCIONA TRABAJADOR/i)).toBeVisible();

      // Verificar header muestra "ARMADO (ARM)"
      await expect(page.getByText(/ARMADO \(ARM\)/i)).toBeVisible();

      // Verificar botón "Volver" existe
      const volverBtn = page.getByRole('button', { name: /VOLVER A SELECCIONAR OPERACIÓN/i });
      await expect(volverBtn).toBeVisible();

      // Verificar que aparecen trabajadores
      await expect(page.getByText('Mauricio')).toBeVisible();
      await expect(page.getByText('Rodriguez')).toBeVisible();

      // Seleccionar "Mauricio Rodriguez"
      await page.getByRole('button', { name: /Mauricio Rodriguez/i }).click();

      // Verificar navegación a /tipo-interaccion
      await expect(page).toHaveURL('/tipo-interaccion');
    });

    // ========================================
    // P3 - Tipo Interacción: INICIAR ACCIÓN
    // ========================================
    await test.step('P3 - Tipo Interacción', async () => {
      // Verificar título muestra "ARMADO (ARM)"
      await expect(page.getByText(/ARMADO \(ARM\)/i)).toBeVisible();

      // Verificar info del trabajador
      await expect(page.getByText(/TRABAJADOR ASIGNADO/i)).toBeVisible();
      await expect(page.getByText(/Mauricio/i)).toBeVisible();
      await expect(page.getByText(/Rodriguez/i)).toBeVisible();

      // Seleccionar "INICIAR ACCIÓN"
      await page.getByRole('button', { name: /INICIAR ACCIÓN/i }).click();

      // Verificar navegación a /seleccionar-spool?tipo=iniciar
      await expect(page).toHaveURL(/\/seleccionar-spool\?tipo=iniciar/);
    });

    // ========================================
    // P4 - Seleccionar Spool: Elegir spool disponible
    // ========================================
    await test.step('P4 - Seleccionar Spool', async () => {
      // Verificar título
      await expect(page.getByText(/SELECCIONA SPOOL/i)).toBeVisible();

      // Esperar que carguen los spools
      await page.waitForTimeout(2000);

      // Verificar que aparecen spools disponibles (arm=0)
      // Usar selector de tabla para encontrar spools
      const spoolRows = page.locator('tbody tr');
      await expect(spoolRows.first()).toBeVisible({ timeout: 10000 });

      // Seleccionar primer spool disponible (click en primera fila)
      await spoolRows.first().click();

      // Verificar navegación a /confirmar?tipo=iniciar
      await expect(page).toHaveURL(/\/confirmar\?tipo=iniciar/);
    });

    // ========================================
    // P5 - Confirmar: Revisar y confirmar acción
    // ========================================
    await test.step('P5 - Confirmar', async () => {
      // Verificar título
      await expect(page.getByText(/CONFIRMAR/i)).toBeVisible();

      // Verificar resumen muestra los datos correctos
      await expect(page.getByText(/Mauricio/i)).toBeVisible();
      await expect(page.getByText(/Rodriguez/i)).toBeVisible();
      await expect(page.getByText(/ARMADO/i)).toBeVisible();

      // Verificar que existe botón "CANCELAR"
      const cancelarBtn = page.getByRole('button', { name: /CANCELAR/i });
      await expect(cancelarBtn).toBeVisible();

      // Presionar "CONFIRMAR"
      await page.getByRole('button', { name: /CONFIRMAR/i }).click();

      // Esperar navegación a /exito
      await expect(page).toHaveURL('/exito', { timeout: 15000 });
    });

    // ========================================
    // P6 - Éxito: Verificar mensaje y opciones
    // ========================================
    await test.step('P6 - Éxito', async () => {
      // Verificar mensaje de éxito "INICIADO"
      await expect(page.getByText(/INICIADO/i)).toBeVisible();

      // Verificar countdown con "SEGUNDOS"
      await expect(page.getByText(/SEGUNDOS/i)).toBeVisible();

      // Verificar botón CONTINUAR existe
      await expect(page.getByRole('button', { name: /CONTINUAR/i })).toBeVisible();

      // Test botón "CONTINUAR" regresa a P1
      await page.getByRole('button', { name: /CONTINUAR/i }).click();
      await expect(page).toHaveURL('/');
    });
  });

  // ========================================
  // Test de navegación: Botón Volver
  // ========================================
  test('debe permitir retroceder con botón Volver', async ({ page }) => {
    await page.goto('/');

    // P1 → P2: Seleccionar operación
    await page.getByRole('button', { name: /ARMADO \(ARM\)/i }).click();
    await expect(page).toHaveURL('/operacion');

    // P2: Verificar Volver → P1
    await page.getByRole('button', { name: /VOLVER A SELECCIONAR OPERACIÓN/i }).click();
    await expect(page).toHaveURL('/');
  });
});
