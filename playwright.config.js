import { defineConfig } from '@playwright/test';
const preview = process.env.PREVIEW_ORIGIN || (process.env.E2B_SANDBOX_ID
  ? `https://${process.env.PORT || 5173}-${process.env.E2B_SANDBOX_ID}.e2b.app` : 'https://aura-preview.example:4443');
export default defineConfig({
  testDir: './tests',
  testMatch: '**/*.spec.js',
  fullyParallel: false,
  workers: 1,
  timeout: 30000,
  reporter: 'list',
  use: {
    baseURL: 'http://127.0.0.1:5173',
    trace: 'retain-on-failure',
    launchOptions: process.env.PLAYWRIGHT_CHROMIUM_EXECUTABLE ? {
      executablePath: process.env.PLAYWRIGHT_CHROMIUM_EXECUTABLE,
      args: ['--no-sandbox', '--disable-dev-shm-usage', '--no-zygote'],
    } : {},
  },
  webServer: [
    { command: `${process.env.PYTHON || 'python'} manage.py runserver 0.0.0.0:8000 --noreload`, cwd: 'backend', env: { PREVIEW_ORIGIN: preview }, url: 'http://127.0.0.1:8000/api/services/', reuseExistingServer: !process.env.CI },
    { command: 'npm run dev', env: { PREVIEW_ORIGIN: preview }, url: 'http://127.0.0.1:5173', reuseExistingServer: !process.env.CI },
  ],
});
