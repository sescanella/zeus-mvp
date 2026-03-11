import { test, expect } from '@playwright/test';
import AxeBuilder from '@axe-core/playwright';

/**
 * Accessibility tests for v5.0 single-page modal architecture.
 *
 * All tests start at http://localhost:3000/ — the single page.
 * Modal stack: AddSpoolModal -> OperationModal -> ActionModal -> WorkerModal/MetrologiaModal.
 *
 * Rewritten in Phase 5 Plan 02 — old tests navigated multi-page routes
 * (/operacion, /tipo-interaccion, /seleccionar-spool) that no longer exist.
 */
test.describe('Accessibility Compliance (WCAG 2.1 Level AA)', () => {
  test('Main page has no a11y violations', async ({ page }) => {
    await page.goto('http://localhost:3000/');
    await page.waitForLoadState('networkidle');

    const results = await new AxeBuilder({ page })
      .withTags(['wcag2a', 'wcag2aa', 'wcag21a', 'wcag21aa'])
      .analyze();

    expect(results.violations).toEqual([]);
  });

  test('"Anadir Spool" button is keyboard accessible', async ({ page }) => {
    await page.goto('http://localhost:3000/');
    await page.waitForLoadState('networkidle');

    // Tab to focus the "Anadir Spool" button
    await page.keyboard.press('Tab');

    const focusedAriaLabel = await page.evaluate(() => {
      const el = document.activeElement;
      return el ? el.getAttribute('aria-label') : null;
    });

    // Button should have aria-label "Anadir spool al listado"
    expect(focusedAriaLabel).toBe('Anadir spool al listado');

    // Press Enter to open AddSpoolModal
    await page.keyboard.press('Enter');

    // Modal should open — look for the dialog role or modal content
    const modalVisible = await page
      .locator('[role="dialog"]')
      .first()
      .isVisible({ timeout: 5000 })
      .catch(() => false);
    expect(modalVisible).toBe(true);
  });

  test('AddSpoolModal has no a11y violations', async ({ page }) => {
    await page.goto('http://localhost:3000/');
    await page.waitForLoadState('networkidle');

    // Open AddSpoolModal via the "Anadir Spool" button
    const addButton = page.locator('button[aria-label="Anadir spool al listado"]');
    await addButton.click();

    // Wait for modal to appear
    await page.locator('[role="dialog"]').first().waitFor({ state: 'visible', timeout: 5000 });

    const results = await new AxeBuilder({ page })
      .withTags(['wcag2a', 'wcag2aa', 'wcag21a', 'wcag21aa'])
      .analyze();

    expect(results.violations).toEqual([]);
  });

  test('Keyboard navigation: Collapsible filter panel in AddSpoolModal', async ({ page }) => {
    await page.goto('http://localhost:3000/');
    await page.waitForLoadState('networkidle');

    // Open AddSpoolModal
    const addButton = page.locator('button[aria-label="Anadir spool al listado"]');
    await addButton.click();
    await page.locator('[role="dialog"]').first().waitFor({ state: 'visible', timeout: 5000 });

    // Wait for the success state (filter panel visible)
    await page.waitForSelector('[aria-controls="filter-panel"]', { timeout: 5000 });

    // Filter panel should be collapsed by default (aria-expanded="false")
    const initialAriaExpanded = await page.getAttribute(
      '[aria-controls="filter-panel"]',
      'aria-expanded'
    );
    expect(initialAriaExpanded).toBe('false');

    // Tab within modal until filter toggle is focused
    for (let i = 0; i < 10; i++) {
      await page.keyboard.press('Tab');
      const isFocused = await page.evaluate(() => {
        const el = document.activeElement;
        return el?.getAttribute('aria-controls') === 'filter-panel';
      });
      if (isFocused) break;
    }

    // Press Enter to expand the filter panel
    await page.keyboard.press('Enter');

    // Verify panel is now expanded
    const expandedAriaExpanded = await page.getAttribute(
      '[aria-controls="filter-panel"]',
      'aria-expanded'
    );
    expect(expandedAriaExpanded).toBe('true');

    // Verify filter inputs are visible
    const filterPanel = page.locator('#filter-panel');
    await expect(filterPanel).toBeVisible({ timeout: 3000 });
  });

  test('SpoolTable rows in AddSpoolModal have correct ARIA attributes', async ({ page }) => {
    await page.goto('http://localhost:3000/');
    await page.waitForLoadState('networkidle');

    // Open AddSpoolModal
    const addButton = page.locator('button[aria-label="Anadir spool al listado"]');
    await addButton.click();
    await page.locator('[role="dialog"]').first().waitFor({ state: 'visible', timeout: 5000 });

    // Wait for success state — either table rows load or empty-state message appears
    const tableBody = page.locator('table tbody');
    await tableBody.waitFor({ state: 'visible', timeout: 5000 }).catch(() => {
      // No table rendered — backend not available; skip row ARIA checks
    });

    const rowCount = await page.locator('table tbody tr').count();

    if (rowCount > 0) {
      // Verify first row has proper ARIA for keyboard-accessible selection
      const firstRow = page.locator('table tbody tr').first();

      const roleAttr = await firstRow.getAttribute('role');
      expect(roleAttr).toBe('button');

      const tabIndex = await firstRow.getAttribute('tabIndex');
      expect(tabIndex).toBe('0');

      const ariaLabel = await firstRow.getAttribute('aria-label');
      expect(ariaLabel).toBeTruthy();
      expect(ariaLabel?.toLowerCase()).toContain('spool');
    } else {
      // Empty state — table exists with proper structure even with no rows
      const table = page.locator('table');
      const tableExists = await table.count();
      // Either a table or an empty-state message must be present
      const emptyMsg = page.locator('text=/sin spools|no hay spools|vacío/i');
      const hasContent = tableExists > 0 || (await emptyMsg.count()) > 0;
      expect(hasContent).toBe(true);
    }
  });

  test('Modal ESC key closes AddSpoolModal', async ({ page }) => {
    await page.goto('http://localhost:3000/');
    await page.waitForLoadState('networkidle');

    // Open AddSpoolModal
    const addButton = page.locator('button[aria-label="Anadir spool al listado"]');
    await addButton.click();
    await page.locator('[role="dialog"]').first().waitFor({ state: 'visible', timeout: 5000 });

    // Press Escape to close modal
    await page.keyboard.press('Escape');

    // Modal should close
    const modalGone = await page
      .locator('[role="dialog"]')
      .first()
      .isVisible()
      .then((v) => !v)
      .catch(() => true);
    expect(modalGone).toBe(true);

    // Focus should return to the triggering button
    await page.waitForTimeout(300);
    const focusedLabel = await page.evaluate(() => {
      const el = document.activeElement;
      return el ? el.getAttribute('aria-label') : null;
    });
    expect(focusedLabel).toBe('Anadir spool al listado');
  });
});
