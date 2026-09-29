import test from 'node:test';
import assert from 'node:assert/strict';

async function client(t, outcomes, config = {}) {
  const calls = [];
  globalThis.window = { AURA_CONFIG: { API_URL: '/api', ...config } };
  t.mock.method(globalThis, 'fetch', async (url, options) => {
    calls.push({ url, ...options });
    const outcome = outcomes.shift();
    assert.ok(outcome, 'Unexpected request: ' + url);
    if (outcome instanceof Error) throw outcome;
    const [status, body] = outcome;
    return new Response(status === 204 ? null : JSON.stringify(body), { status });
  });
  const { api } = await import(`../../frontend/js/api.js?test=${Math.random()}`);
  return { api, calls };
}
const rejected = reason => [403, { code: 'csrf_failed', csrfReason: reason, detail: 'CSRF rejected.' }];

test('stale token is refreshed and only the rejected request is retried', async t => {
  const { api, calls } = await client(t, [
    [200, { csrfToken: 'old' }], rejected('token_invalid'),
    [200, { csrfToken: 'fresh' }], [200, { id: 1, csrfToken: 'rotated-after-login' }],
    [200, { detail: 'Updated' }],
  ]);
  assert.equal((await api('/auth/login/', 'POST', { email: 'test@example.com' })).id, 1);
  await api('/settings/', 'PATCH', { interval_minutes: 10 });
  assert.deepEqual(calls.map(c => c.method), ['GET', 'POST', 'GET', 'POST', 'PATCH']);
  assert.equal(calls[1].headers['X-CSRFToken'], 'old');
  assert.equal(calls[3].headers['X-CSRFToken'], 'fresh');
  assert.equal(calls[4].headers['X-CSRFToken'], 'rotated-after-login');
  assert.equal(calls[1].body, calls[3].body);
  assert.ok(calls.every(c => c.credentials === 'include' && c.cache === 'no-store'));
});

test('blocked cookies stop after one retry with an actionable error', async t => {
  const { api, calls } = await client(t, [
    [200, { csrfToken: 'old' }], rejected('cookie_missing'),
    [200, { csrfToken: 'fresh' }], rejected('cookie_missing'),
  ]);
  await assert.rejects(api('/auth/password-reset/', 'POST', { email: 'test@example.com' }), error => {
    assert.equal(error.code, 'csrf_failed');
    assert.equal(error.csrfReason, 'cookie_missing');
    assert.match(error.message, /nova aba/);
    return true;
  });
  assert.equal(calls.length, 4);
});

for (const [label, status, body] of [
  ['invalid credentials', 400, { detail: 'E-mail ou senha inválidos.' }],
  ['permission denial', 403, { detail: 'Sem permissão.' }],
  ['rate limit', 429, { detail: 'Tente mais tarde.' }],
  ['server failure', 500, { detail: 'Falha no servidor.' }],
  ['untrusted origin', ...rejected('origin_rejected')],
]) {
  test(`${label} does not replay the mutation`, async t => {
    const { api, calls } = await client(t, [[200, { csrfToken: 'token' }], [status, body]]);
    await assert.rejects(api('/auth/login/', 'POST', {}), error => error.status === status);
    assert.equal(calls.length, 2);
  });
}

test('ambiguous network failures do not replay mutations', async t => {
  const { api, calls } = await client(t, [[200, { csrfToken: 'token' }], new Error('network')]);
  await assert.rejects(api('/appointments/', 'POST', {}), /conectar ao servidor/);
  assert.equal(calls.length, 2);
});

test('concurrent initial writes share a single CSRF request', async t => {
  const { api, calls } = await client(t, [[200, { csrfToken: 'token' }], [200, {}], [200, {}]]);
  await Promise.all([api('/settings/', 'PATCH', {}), api('/notifications/read_all/', 'POST', {})]);
  assert.equal(calls.filter(c => c.url.endsWith('/auth/csrf/')).length, 1);
  assert.equal(calls.filter(c => c.headers['X-CSRFToken'] === 'token').length, 2);
});


test('managed preview does not recommend an unauthorized direct URL', async t => {
  const { api } = await client(t, [
    [200, { csrfToken: 'old' }], rejected('cookie_missing'),
    [200, { csrfToken: 'fresh' }], rejected('cookie_missing'),
  ], { MANAGED_PREVIEW: true });
  await assert.rejects(api('/auth/login/', 'POST', {}), error => {
    assert.match(error.message, /painel de prévia do Arena/);
    assert.doesNotMatch(error.message, /Abra o Aura em uma nova aba/);
    assert.doesNotMatch(error.message, /csrfReason/);
    return true;
  });
});
