import { test, expect } from '@playwright/test';

/**
 * Tests de Error Handling
 *
 * Verifica el manejo correcto de errores de API y errores de red:
 * - Test 3: Ownership Violation (403 Forbidden)
 * - Test 4: Error de Validación (400 Bad Request)
 * - Test 5: Spool No Encontrado (404 Not Found)
 * - Test 6: Error de Conexión (Network Error)
 * - Test 7: Error del Servidor (503 Service Unavailable)
 */
test.describe('Error Handling - Validación de API Errors', () => {

  // ========================================
  // Test 3: Ownership Violation (403) - CRÍTICO
  // ========================================
  test('Test 3: debe mostrar error 403 cuando otro trabajador intenta completar', async ({ page }) => {
    /**
     * Simula el escenario crítico donde un trabajador intenta completar
     * una acción que no le pertenece. El backend debe retornar 403 Forbidden.
     */

    await test.step('Navegar al flujo COMPLETAR ARM', async () => {
      await page.goto('/');
      await page.getByRole('button', { name: /Nicolás Rodriguez/i }).click();
      await page.getByRole('button', { name: /ARMADO \(ARM\)/i }).click();
      await page.getByRole('button', { name: /COMPLETAR ACCIÓN/i }).click();
    });

    await test.step('Interceptar API y simular error 403', async () => {
      // Mock API para retornar 403 Forbidden al intentar completar
      await page.route('**/api/completar-accion', async (route) => {
        await route.fulfill({
          status: 403,
          contentType: 'application/json',
          body: JSON.stringify({
            detail: 'Solo Mauricio Rodriguez puede completar esta acción. Esta acción pertenece a otro trabajador.',
          }),
        });
      });

      // Seleccionar un spool y confirmar
      const firstSpool = page.getByRole('button').filter({ hasText: /MK-/ }).first();
      await firstSpool.click();
      await page.getByRole('button', { name: /CONFIRMAR/i }).click();
    });

    await test.step('Verificar ErrorMessage tipo forbidden (403)', async () => {
      // Verificar icono 🚫
      await expect(page.getByText('🚫')).toBeVisible();

      // Verificar título "No Autorizado"
      await expect(page.getByText('No Autorizado')).toBeVisible();

      // Verificar mensaje contiene "Solo Mauricio Rodriguez puede completar"
      await expect(page.getByText(/Solo Mauricio Rodriguez puede completar/i)).toBeVisible();

      // Verificar que NO hay botón Reintentar (error forbidden no es recuperable)
      await expect(page.getByRole('button', { name: /Reintentar/i })).not.toBeVisible();
    });
  });

  // ========================================
  // Test 4: Error de Validación (400)
  // ========================================
  test('Test 4: debe mostrar error 400 cuando operación ya está iniciada', async ({ page }) => {
    /**
     * Simula el escenario donde se intenta iniciar una operación
     * que ya está en progreso (arm=0.1).
     */

    await test.step('Navegar al flujo INICIAR ARM', async () => {
      await page.goto('/');
      await page.getByRole('button', { name: /Mauricio Rodriguez/i }).click();
      await page.getByRole('button', { name: /ARMADO \(ARM\)/i }).click();
      await page.getByRole('button', { name: /INICIAR ACCIÓN/i }).click();
    });

    await test.step('Interceptar API y simular error 400', async () => {
      // Mock API para retornar 400 Bad Request
      await page.route('**/api/iniciar-accion', async (route) => {
        await route.fulfill({
          status: 400,
          contentType: 'application/json',
          body: JSON.stringify({
            detail: 'La operación ARM ya está iniciada en este spool. Estado actual: EN_PROGRESO',
          }),
        });
      });

      // Seleccionar un spool y confirmar
      const firstSpool = page.getByRole('button').filter({ hasText: /MK-/ }).first();
      await firstSpool.click();
      await page.getByRole('button', { name: /CONFIRMAR/i }).click();
    });

    await test.step('Verificar ErrorMessage tipo validation (400)', async () => {
      // Verificar icono ⚠️
      await expect(page.getByText('⚠️')).toBeVisible();

      // Verificar título "Error de Validación"
      await expect(page.getByText('Error de Validación')).toBeVisible();

      // Verificar mensaje contiene "ya está iniciada"
      await expect(page.getByText(/ya está iniciada/i)).toBeVisible();

      // Verificar que NO hay botón Reintentar
      await expect(page.getByRole('button', { name: /Reintentar/i })).not.toBeVisible();
    });
  });

  // ========================================
  // Test 5: Spool No Encontrado (404)
  // ========================================
  test('Test 5: debe mostrar error 404 cuando spool no existe', async ({ page }) => {
    /**
     * Simula el escenario donde se intenta iniciar una acción
     * en un spool que no existe en Google Sheets.
     */

    await test.step('Navegar al flujo INICIAR ARM', async () => {
      await page.goto('/');
      await page.getByRole('button', { name: /Mauricio Rodriguez/i }).click();
      await page.getByRole('button', { name: /ARMADO \(ARM\)/i }).click();
      await page.getByRole('button', { name: /INICIAR ACCIÓN/i }).click();
    });

    await test.step('Interceptar API y simular error 404', async () => {
      // Mock API para retornar 404 Not Found
      await page.route('**/api/iniciar-accion', async (route) => {
        await route.fulfill({
          status: 404,
          contentType: 'application/json',
          body: JSON.stringify({
            detail: 'Spool no encontrado. El spool INVALID-TAG-12345 no existe en Google Sheets.',
          }),
        });
      });

      // Seleccionar un spool y confirmar
      const firstSpool = page.getByRole('button').filter({ hasText: /MK-/ }).first();
      await firstSpool.click();
      await page.getByRole('button', { name: /CONFIRMAR/i }).click();
    });

    await test.step('Verificar ErrorMessage tipo not-found (404)', async () => {
      // Verificar icono 🔍
      await expect(page.getByText('🔍')).toBeVisible();

      // Verificar título "No Encontrado"
      await expect(page.getByText('No Encontrado')).toBeVisible();

      // Verificar mensaje contiene "no existe"
      await expect(page.getByText(/no existe/i)).toBeVisible();

      // Verificar que NO hay botón Reintentar
      await expect(page.getByRole('button', { name: /Reintentar/i })).not.toBeVisible();
    });
  });

  // ========================================
  // Test 6: Error de Conexión (Network Error)
  // ========================================
  test('Test 6: debe mostrar error de red cuando backend no está disponible', async ({ page }) => {
    /**
     * Simula el escenario donde el backend no está disponible
     * (servidor caído, sin conexión a internet, etc.)
     */

    await test.step('Navegar a selección de spools', async () => {
      await page.goto('/');
      await page.getByRole('button', { name: /Mauricio Rodriguez/i }).click();
      await page.getByRole('button', { name: /ARMADO \(ARM\)/i }).click();
      await page.getByRole('button', { name: /INICIAR ACCIÓN/i }).click();
    });

    await test.step('Interceptar API y simular network error', async () => {
      // Mock API para simular falla de conexión
      await page.route('**/api/spools/iniciar*', async (route) => {
        await route.abort('failed');
      });

      // Esperar que cargue y muestre error de red
      await page.waitForTimeout(1000);
    });

    await test.step('Verificar ErrorMessage tipo network', async () => {
      // Verificar icono 🔌
      await expect(page.getByText('🔌')).toBeVisible();

      // Verificar título "Error de Conexión"
      await expect(page.getByText('Error de Conexión')).toBeVisible();

      // Verificar mensaje sobre conexión
      await expect(page.getByText(/conexión/i)).toBeVisible();

      // Verificar que SÍ hay botón Reintentar (error recuperable)
      await expect(page.getByRole('button', { name: /Reintentar/i })).toBeVisible();
    });

    await test.step('Verificar botón Reintentar funciona', async () => {
      // Remover el mock para permitir conexión exitosa
      await page.unroute('**/api/spools/iniciar*');

      // Clic en Reintentar
      await page.getByRole('button', { name: /Reintentar/i }).click();

      // Verificar que ahora carga la lista de spools correctamente
      await expect(page.getByText(/MK-/)).toBeVisible({ timeout: 5000 });
    });
  });

  // ========================================
  // Test 7: Error del Servidor (503)
  // ========================================
  test('Test 7: debe mostrar error 503 cuando Google Sheets no está disponible', async ({ page }) => {
    /**
     * Simula el escenario donde Google Sheets API no está disponible
     * o hay un error en el servidor (503 Service Unavailable).
     */

    await test.step('Navegar al flujo INICIAR ARM', async () => {
      await page.goto('/');
      await page.getByRole('button', { name: /Mauricio Rodriguez/i }).click();
      await page.getByRole('button', { name: /ARMADO \(ARM\)/i }).click();
      await page.getByRole('button', { name: /INICIAR ACCIÓN/i }).click();
    });

    await test.step('Interceptar API y simular error 503', async () => {
      // Mock API para retornar 503 Service Unavailable
      await page.route('**/api/iniciar-accion', async (route) => {
        await route.fulfill({
          status: 503,
          contentType: 'application/json',
          body: JSON.stringify({
            detail: 'Error del servidor de Google Sheets. El servicio no está disponible temporalmente.',
          }),
        });
      });

      // Seleccionar un spool y confirmar
      const firstSpool = page.getByRole('button').filter({ hasText: /MK-/ }).first();
      await firstSpool.click();
      await page.getByRole('button', { name: /CONFIRMAR/i }).click();
    });

    await test.step('Verificar ErrorMessage tipo server (503)', async () => {
      // Verificar icono ❌
      await expect(page.getByText('❌').first()).toBeVisible();

      // Verificar título "Error del Servidor"
      await expect(page.getByText('Error del Servidor')).toBeVisible();

      // Verificar mensaje sobre Google Sheets
      await expect(page.getByText(/Google Sheets/i)).toBeVisible();

      // Verificar que SÍ hay botón Reintentar (error recuperable)
      await expect(page.getByRole('button', { name: /Reintentar/i })).toBeVisible();
    });
  });
});
