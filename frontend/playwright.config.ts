import { defineConfig, devices } from '@playwright/test';

export default defineConfig({
  testDir: './tests/e2e',
  fullyParallel: false,
  workers: 1,
  retries: process.env.CI ? 1 : 0,
  reporter: process.env.CI ? 'github' : 'list',
  use: {
    baseURL: 'http://127.0.0.1:44321',
    trace: 'retain-on-failure',
    screenshot: 'only-on-failure',
    ...devices['Desktop Chrome'],
  },
  webServer: [
    {
      command: process.env.E2E_BACKEND_COMMAND
        ?? 'E2E_BACKEND_PORT=45000 ../backend/.venv/bin/python ../backend/tests/e2e_server.py',
      url: 'http://127.0.0.1:45000/api/salud',
      reuseExistingServer: !process.env.CI,
      timeout: 60_000,
    },
    {
      command: 'API_PROXY_TARGET=http://127.0.0.1:45000 npm run dev -- --ignore-lock --host 127.0.0.1 --port 44321',
      url: 'http://127.0.0.1:44321',
      reuseExistingServer: !process.env.CI,
      timeout: 60_000,
    },
  ],
});
