import { defineConfig, devices } from '@playwright/test';

/**
 * Configuración de Playwright para ZEUES Frontend MVP
 * Tests E2E para los 4 flujos principales: INICIAR/COMPLETAR ARM/SOLD
 */
export default defineConfig({
  testDir: './e2e',

  /* Timeout por test: 30 segundos (flujo completo < 30s) */
  timeout: 30 * 1000,

  /* Expect timeout: 5 segundos para assertions */
  expect: {
    timeout: 5000
  },

  /* Configuración de ejecución */
  fullyParallel: true,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 2 : 0,
  workers: process.env.CI ? 1 : undefined,

  /* Reporter: HTML para visualización de resultados */
  reporter: 'html',

  /* Configuración compartida para todos los proyectos */
  use: {
    /* Base URL del frontend */
    baseURL: 'http://localhost:3001',

    /* Screenshots solo en fallas */
    screenshot: 'only-on-failure',

    /* Videos solo en primera retry */
    video: 'retain-on-failure',

    /* Trace en fallas para debugging */
    trace: 'on-first-retry',
  },

  /* Proyectos de navegadores */
  projects: [
    {
      name: 'chromium',
      use: {
        ...devices['Desktop Chrome'],
        /* Viewport tablet (uso principal en producción) */
        viewport: { width: 768, height: 1024 }
      },
    },

    /* Opcional: descomentar para testing multi-browser */
    // {
    //   name: 'firefox',
    //   use: { ...devices['Desktop Firefox'] },
    // },
    // {
    //   name: 'webkit',
    //   use: { ...devices['Desktop Safari'] },
    // },

    /* Mobile testing */
    // {
    //   name: 'Mobile Chrome',
    //   use: { ...devices['Pixel 5'] },
    // },
  ],

  /* Dev server: levantar Next.js antes de los tests */
  webServer: {
    command: 'PORT=3001 npm run dev',
    url: 'http://localhost:3001',
    reuseExistingServer: !process.env.CI,
    timeout: 120 * 1000,
  },
});
