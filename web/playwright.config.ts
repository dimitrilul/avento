import { defineConfig } from '@playwright/test'

export default defineConfig({
  testDir: './e2e',
  fullyParallel: false,
  workers: 1,
  globalSetup: './e2e/global-setup.ts',
  reporter: [['list'], ['html', { open: 'never' }]],
  use: {
    baseURL: 'http://127.0.0.1:5173',
    storageState: './e2e/.auth/user.json',
    colorScheme: 'dark',
    reducedMotion: 'reduce',
    trace: 'retain-on-failure',
  },
  expect: {
    toHaveScreenshot: {
      animations: 'disabled',
      caret: 'hide',
      maxDiffPixelRatio: 0.015,
    },
  },
  webServer: [
    {
      command: 'cd ../backend && rm -f /tmp/avento-playwright.db && rm -rf /tmp/avento-playwright-uploads && AVENTO_ENVIRONMENT=test AVENTO_DATABASE_URL=sqlite:////tmp/avento-playwright.db AVENTO_UPLOAD_DIR=/tmp/avento-playwright-uploads AVENTO_WEATHER_PROVIDER=disabled AVENTO_REVERSE_GEOCODING_PROVIDER=disabled AVENTO_SECRET_KEY=playwright-secret-that-is-long-enough .venv/bin/python -m uvicorn app.main:app --host 127.0.0.1 --port 8000',
      url: 'http://127.0.0.1:8000/health',
      timeout: 120_000,
      reuseExistingServer: false,
    },
    {
      command: 'npm run dev -- --host 127.0.0.1',
      url: 'http://127.0.0.1:5173',
      timeout: 120_000,
      reuseExistingServer: false,
    },
  ],
})
