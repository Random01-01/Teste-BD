import { cp, mkdir, writeFile, rm } from 'node:fs/promises';
const api = process.env.API_URL || '/api';
if (api !== '/api' && !/^https:\/\//.test(api)) throw new Error('API_URL de produção deve usar HTTPS.');
await rm('dist', { recursive: true, force: true });
await mkdir('dist', { recursive: true });
await cp('frontend', 'dist', { recursive: true });
await writeFile('dist/js/config.js', `window.AURA_CONFIG = ${JSON.stringify({ API_URL: api.replace(/\/$/, ''), DEMO: false })};\n`);
await writeFile('dist/.nojekyll', '');
console.log('Front-end estático gerado em dist/. API:', api);
