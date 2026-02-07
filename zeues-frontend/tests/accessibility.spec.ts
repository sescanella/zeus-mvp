import { test, expect } from '@playwright/test';
import AxeBuilder from '@axe-core/playwright';

test.describe('Accessibility Compliance (WCAG 2.1 Level AA)', () => {
  test('P1: Worker identification page has no a11y violations', async ({ page }) => {
    await page.goto('http://localhost:3000/');

    const accessibilityScanResults = await new AxeBuilder({ page })
      .withTags(['wcag2a', 'wcag2aa', 'wcag21a', 'wcag21aa'])
      .analyze();

    expect(accessibilityScanResults.violations).toEqual([]);
  });

  test('P2: Operation selection has no a11y violations', async ({ page }) => {
    // Navigate through flow
    await page.goto('http://localhost:3000/');
    await page.click('text=MANUEL RODRÍGUEZ');

    const accessibilityScanResults = await new AxeBuilder({ page })
      .withTags(['wcag2a', 'wcag2aa', 'wcag21a', 'wcag21aa'])
      .analyze();

    expect(accessibilityScanResults.violations).toEqual([]);
  });

  test('P4: Spool selection (Blueprint UI) has no a11y violations', async ({ page }) => {
    // Full flow navigation
    await page.goto('http://localhost:3000/');
    await page.click('text=MANUEL RODRÍGUEZ');
    await page.click('text=ARMADO');
    await page.click('text=TOMAR');

    const accessibilityScanResults = await new AxeBuilder({ page })
      .withTags(['wcag2a', 'wcag2aa', 'wcag21a', 'wcag21aa'])
      .exclude(['#advertisement']) // Exclude known third-party violations
      .analyze();

    expect(accessibilityScanResults.violations).toEqual([]);
  });

  test('Keyboard navigation: Tab through P4 spool table', async ({ page }) => {
    // Setup: Navigate to spool selection
    await page.goto('http://localhost:3000/');
    await page.click('text=MANUEL RODRÍGUEZ');
    await page.click('text=ARMADO');
    await page.click('text=TOMAR');

    // Test keyboard navigation
    await page.keyboard.press('Tab'); // Focus filter toggle
    await page.keyboard.press('Enter'); // Expand filters
    await page.keyboard.press('Tab'); // Focus NV input
    await page.keyboard.press('Tab'); // Focus TAG input
    await page.keyboard.press('Tab'); // Focus first spool row
    await page.keyboard.press('Enter'); // Select spool

    // Verify selection works via keyboard
    const selectedCount = await page.locator('text=SPOOLS SELECCIONADOS').count();
    expect(selectedCount).toBeGreaterThan(0);
  });

  test('Keyboard navigation: Collapsible filter panel toggle', async ({ page }) => {
    // Navigate to spool selection
    await page.goto('http://localhost:3000/');
    await page.click('text=MANUEL RODRÍGUEZ');
    await page.click('text=ARMADO');
    await page.click('text=TOMAR');

    // Wait for page to load
    await page.waitForSelector('text=FILTROS', { timeout: 5000 });

    // Verify filter panel is collapsed by default
    const panelCollapsed = await page.isVisible('text=BUSCAR NV');
    expect(panelCollapsed).toBe(false);

    // Press Tab until filter button is focused (may need multiple tabs)
    for (let i = 0; i < 10; i++) {
      await page.keyboard.press('Tab');
      const isFocused = await page.evaluate(() => {
        const activeElement = document.activeElement;
        return activeElement?.getAttribute('aria-controls') === 'filter-panel';
      });
      if (isFocused) break;
    }

    // Press Enter to expand
    await page.keyboard.press('Enter');

    // Verify panel is now visible
    const panelExpanded = await page.isVisible('text=BUSCAR NV');
    expect(panelExpanded).toBe(true);

    // Verify aria-expanded attribute
    const ariaExpanded = await page.getAttribute('[aria-controls="filter-panel"]', 'aria-expanded');
    expect(ariaExpanded).toBe('true');
  });

  test('Screen reader: Table rows announce correctly', async ({ page }) => {
    await page.goto('http://localhost:3000/');
    await page.click('text=MANUEL RODRÍGUEZ');
    await page.click('text=ARMADO');
    await page.click('text=TOMAR');

    // Wait for table to load
    await page.waitForSelector('table tbody tr', { timeout: 5000 });

    // Check that first table row has proper ARIA attributes
    const firstRow = page.locator('table tbody tr').first();

    // Should have role="button" for selectable rows
    const roleAttr = await firstRow.getAttribute('role');
    expect(roleAttr).toBe('button');

    // Should have aria-label describing the action
    const ariaLabel = await firstRow.getAttribute('aria-label');
    expect(ariaLabel).toContain('Seleccionar spool');

    // Should have tabIndex for keyboard navigation
    const tabIndex = await firstRow.getAttribute('tabIndex');
    expect(tabIndex).toBe('0');
  });
});
