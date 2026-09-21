import http from 'node:http';
import { readFile } from 'node:fs/promises';
import { resolve, extname } from 'node:path';
import { previewOrigin, previewResponseHeaders } from './preview-cookies.mjs';
const root = resolve('frontend');
const embeddedOrigin = previewOrigin();
// Opt-in for a dedicated HTTPS development instance behind a host-rewriting
// platform proxy. Never enable from a request header or in production.
const dedicatedHttps = process.env.PREVIEW_COOKIE_POLICY === 'partitioned';
if (dedicatedHttps && !embeddedOrigin) throw new Error('PREVIEW_COOKIE_POLICY exige DEBUG=True e uma origem HTTPS configurada.');
const cookieNames = [process.env.CSRF_COOKIE_NAME || 'csrftoken', process.env.SESSION_COOKIE_NAME || 'sessionid'];
const previewLabel = process.env.PREVIEW_LABEL || '';
const instanceId = process.env.PREVIEW_INSTANCE_ID || '';
const managedPreview = Boolean(process.env.E2B_SANDBOX_ID);

const target = process.env.BACKEND_URL || 'http://127.0.0.1:8000';
const demo = process.env.DEV_DEMO === 'true' && process.env.DEBUG?.toLowerCase() === 'true';
const types = { '.html': 'text/html', '.css': 'text/css', '.js': 'text/javascript', '.svg': 'image/svg+xml', '.jpg': 'image/jpeg', '.png': 'image/png', '.woff2': 'font/woff2' };
http.createServer(async (req, res) => {
  const url = new URL(req.url, 'http://local');
  if (url.pathname.startsWith('/api/')) {
    let path = req.url;
    let body = null;
    if (url.pathname === '/api/demo-login/') {
      if (!demo || !process.env.DEMO_PASSWORD || req.method !== 'POST') { res.writeHead(404); return res.end(); }
      path = '/api/auth/login/';
      body = JSON.stringify({ email: process.env.DEMO_EMAIL || 'demo@example.com', password: process.env.DEMO_PASSWORD });
    }
    const headers = { ...req.headers, host: new URL(target).host };
    if (body) { headers['content-type'] = 'application/json'; headers['content-length'] = Buffer.byteLength(body); }
    const proxy = http.request(new URL(path, target), { method: req.method, headers }, upstream => {
      res.writeHead(upstream.statusCode, previewResponseHeaders(upstream.headers, req.headers.host, embeddedOrigin, cookieNames, dedicatedHttps));
      upstream.pipe(res);
    });
    proxy.on('error', () => { res.writeHead(502, { 'content-type': 'application/json' }); res.end(JSON.stringify({ detail: 'O back-end está indisponível. Inicie o Django na porta 8000.' })); });
    if (body) proxy.end(body); else req.pipe(proxy);
    return;
  }
  if (url.pathname === '/js/config.js') {
    res.writeHead(200, { 'content-type': 'text/javascript', 'cache-control': 'no-store' });
    return res.end(`window.AURA_CONFIG = ${JSON.stringify({ API_URL: '/api', DEMO: demo, MANAGED_PREVIEW: managedPreview, PREVIEW_LABEL: previewLabel, INSTANCE_ID: instanceId, START_PAGE: process.env.PREVIEW_START_PAGE || '' })};`);
  }
  try {
    const path = resolve(root, '.' + decodeURIComponent(url.pathname === '/' ? '/index.html' : url.pathname));
    if (!path.startsWith(root + '/')) { res.writeHead(403); return res.end(); }
    const file = await readFile(path);
    res.writeHead(200, { 'content-type': types[extname(path)] || 'application/octet-stream', 'cache-control': 'no-store' });
    res.end(file);
  } catch { res.writeHead(404); res.end('Não encontrado'); }
}).listen(Number(process.env.PORT || 5173), '0.0.0.0', () => console.log(`Aura disponível na porta ${process.env.PORT || 5173}${demo ? ' • demonstração fictícia' : ''}`));
