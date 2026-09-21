import { test, expect } from '@playwright/test';
import http from 'node:http';
import https from 'node:https';
import { execFileSync } from 'node:child_process';
import { mkdtempSync, readFileSync, rmSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join } from 'node:path';

const preview = process.env.PREVIEW_ORIGIN || (process.env.E2B_SANDBOX_ID
  ? `https://${process.env.PORT || 5173}-${process.env.E2B_SANDBOX_ID}.e2b.app` : 'https://aura-preview.example:4443');
const previewUrl = new URL(preview);
const frontendTarget = process.env.PREVIEW_TEST_TARGET || 'http://127.0.0.1:5173';
const csrfCookieName = process.env.CSRF_COOKIE_NAME || 'csrftoken';
const sessionCookieName = process.env.SESSION_COOKIE_NAME || 'sessionid';
const port = Number(previewUrl.port || 443);
const parent = `https://arena-parent.example:${port}`;
let gateway, certificates;

// Real cross-site HTTPS iframe, real proxy/Django and real browser cookies.
// Only DNS and the certificate authority are local test fixtures; no response,
// cookie, CSRF header, Origin or Referer is mocked or rewritten by the test.
// An optional Host-only rewrite reproduces a platform proxy terminating HTTPS.
test.use({
  ignoreHTTPSErrors: true,
  launchOptions: {
    ...(process.env.PLAYWRIGHT_CHROMIUM_EXECUTABLE ? { executablePath: process.env.PLAYWRIGHT_CHROMIUM_EXECUTABLE } : {}),
    args: ['--no-sandbox', '--disable-dev-shm-usage', '--no-zygote',
      `--host-resolver-rules=MAP ${previewUrl.hostname} 127.0.0.1, MAP arena-parent.example 127.0.0.1`],
  },
});

test.beforeAll(async () => {
  certificates = mkdtempSync(join(tmpdir(), 'aura-https-test-'));
  execFileSync('openssl', ['req', '-x509', '-newkey', 'rsa:2048', '-nodes', '-days', '1',
    '-keyout', join(certificates, 'key.pem'), '-out', join(certificates, 'cert.pem'),
    '-subj', '/CN=aura-preview-test'], { stdio: 'ignore' });
  gateway = https.createServer({
    key: readFileSync(join(certificates, 'key.pem')),
    cert: readFileSync(join(certificates, 'cert.pem')),
  }, (req, res) => {
    if (req.headers.host?.startsWith('arena-parent.example')) {
      res.writeHead(200, { 'Content-Type': 'text/html' });
      res.end(`<iframe title="Aura" src="${preview}/#login" style="width:1400px;height:1000px"></iframe>`);
      return;
    }
    const upstream = http.request(`${frontendTarget}${req.url}`, {
      method: req.method, headers: { ...req.headers, ...(process.env.PREVIEW_TEST_REWRITE_HOST === 'true' ? { host: new URL(frontendTarget).host } : {}) },
    }, response => {
      res.writeHead(response.statusCode, response.headers);
      response.pipe(res);
    });
    upstream.on('error', () => { res.writeHead(502); res.end(); });
    req.pipe(upstream);
  });
  await new Promise((resolve, reject) => {
    gateway.once('error', reject);
    gateway.listen(port, '127.0.0.1', resolve);
  });
});

test.afterAll(async () => {
  if (gateway) {
    gateway.closeAllConnections();
    await new Promise(resolve => gateway.close(resolve));
  }
  if (certificates) rmSync(certificates, { recursive: true, force: true });
});

test('cross-site iframe supports login, persistent session, protected writes, logout and password recovery', async ({ page, context }) => {
  await page.goto(parent);
  const app = page.frameLocator('iframe');
  if (process.env.PREVIEW_TEST_EMAIL && process.env.PREVIEW_TEST_PASSWORD) {
    await app.locator('[name=email]').fill(process.env.PREVIEW_TEST_EMAIL);
    await app.locator('[name=password]').fill(process.env.PREVIEW_TEST_PASSWORD);
    await app.getByRole('button', { name: 'Entrar no meu espaço', exact: true }).click();
  } else {
    await app.getByRole('button', { name: 'Explorar como profissional · demonstração', exact: true }).click();
  }
  await expect(app.getByRole('heading', { name: 'Seu dia, em harmonia.' })).toBeVisible();
  const cookies = await context.cookies(preview);
  for (const name of [csrfCookieName, sessionCookieName]) {
    const cookie = cookies.find(c => c.name === name);
    expect(cookie, `missing ${name}`).toBeTruthy();
    expect(cookie.secure).toBe(true);
    expect(cookie.sameSite).toBe('None');
    expect(cookie.partitionKey).toContain('arena-parent.example');
  }
  expect(cookies.find(c => c.name === sessionCookieName).httpOnly).toBe(true);
  await app.getByRole('link', { name: 'Configurações', exact: true }).click();
  await app.getByRole('button', { name: 'Salvar preferências', exact: true }).click();
  await expect(app.locator('#toast')).toContainText('Suas preferências foram salvas.');
  await page.reload();
  await expect(app.getByRole('heading', { name: 'Seu dia, em harmonia.' })).toBeVisible();
  await app.locator('[data-action=account]').click();
  await app.getByRole('button', { name: 'Sair da minha conta', exact: true }).click();
  await expect(app.locator('#auth-form')).toBeVisible();
  expect((await context.cookies(preview)).some(c => c.name === sessionCookieName)).toBe(false);
  await app.locator('[name=email]').fill('missing-preview-user@example.com');
  await app.locator('[name=password]').fill('Wrong-test-only-password!');
  await app.getByRole('button', { name: 'Entrar no meu espaço', exact: true }).click();
  await expect(app.locator('.form-error')).toContainText('E-mail ou senha inválidos.');
  await app.getByRole('link', { name: 'Esqueci minha senha', exact: true }).click();
  await app.locator('[name=email]').fill('missing-preview-user@example.com');
  await app.getByRole('button', { name: 'Enviar link de recuperação', exact: true }).click();
  await expect(app.getByRole('heading', { name: 'Confira sua caixa de entrada.' })).toBeVisible();
});
