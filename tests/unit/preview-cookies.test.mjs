import test from 'node:test';
import assert from 'node:assert/strict';
import { previewOrigin, previewResponseHeaders } from '../../scripts/preview-cookies.mjs';

const origin = 'https://5173-sandbox.e2b.app';
const cookies = [
  'csrftoken=csrf-fixture; expires=Tue, 21 Sep 2027 00:00:00 GMT; Max-Age=31449600; Path=/; SameSite=Lax',
  'sessionid=session-fixture; HttpOnly; Path=/; SameSite=Lax',
];

test('HTTPS embedded preview gets Secure, SameSite=None and Partitioned cookies', () => {
  const result = previewResponseHeaders({ 'set-cookie': cookies }, new URL(origin).host, origin);
  for (const value of result['set-cookie']) {
    assert.match(value, /; SameSite=None; Secure; Partitioned$/);
    assert.doesNotMatch(value, /SameSite=Lax/);
    assert.match(value, /Path=\//);
  }
  assert.match(result['set-cookie'][1], /HttpOnly/);
  assert.match(result['set-cookie'][0], /expires=Tue, 21 Sep 2027/);
  assert.match(cookies[0], /SameSite=Lax/); // Input is not mutated.
});

test('local requests, other hosts and unrelated cookies are not rewritten', () => {
  const headers = { 'set-cookie': cookies };
  assert.equal(previewResponseHeaders(headers, '127.0.0.1:5173', origin), headers);
  assert.equal(previewResponseHeaders(headers, 'evil.example', origin), headers);
  assert.equal(previewResponseHeaders(headers, new URL(origin).host, null), headers);
  const other = 'unrelated=fixture; Path=/; SameSite=Strict';
  assert.equal(previewResponseHeaders({ 'set-cookie': [other] }, new URL(origin).host, origin)['set-cookie'][0], other);
});

test('cookie deletion is partitioned as well and preserves expiration', () => {
  const result = previewResponseHeaders({ 'set-cookie': ['sessionid=""; Max-Age=0; Path=/; SameSite=None; Secure; Partitioned'] }, new URL(origin).host, origin);
  assert.match(result['set-cookie'][0], /Max-Age=0/);
  assert.equal(result['set-cookie'][0].match(/Partitioned/g).length, 1);
});

test('preview policy requires DEBUG and a configured HTTPS origin', () => {
  assert.equal(previewOrigin({ DEBUG: 'True', E2B_SANDBOX_ID: 'sandbox' }), origin);
  assert.equal(previewOrigin({ DEBUG: 'True', PREVIEW_ORIGIN: 'https://preview.example/' }), 'https://preview.example');
  assert.equal(previewOrigin({ DEBUG: 'False', PREVIEW_ORIGIN: origin, E2B_SANDBOX_ID: 'sandbox' }), null);
  assert.equal(previewOrigin({ DEBUG: 'True' }), null);
  for (const bad of ['http://preview.example', 'https://preview.example/path', 'https://user:pass@preview.example', 'https://preview.example/?q=1']) {
    assert.throws(() => previewOrigin({ DEBUG: 'True', PREVIEW_ORIGIN: bad }));
  }
});

test('dedicated HTTPS instance preserves isolated cookies behind a rewritten Host', () => {
  const names = ['aura_test_csrf', 'aura_test_session'];
  const headers = { 'set-cookie': [
    'aura_test_csrf=fixture; Path=/; SameSite=None; Secure',
    'aura_test_session=fixture; HttpOnly; Path=/; SameSite=None; Secure',
  ] };
  assert.equal(previewResponseHeaders(headers, '127.0.0.1:8080', origin, names), headers);
  const modified = previewResponseHeaders(headers, '127.0.0.1:8080', origin, names, true);
  assert.ok(modified['set-cookie'].every(value => /SameSite=None; Secure; Partitioned$/.test(value)));
  assert.match(modified['set-cookie'][1], /HttpOnly/);
  // A dedicated flag never enables preview behavior without an HTTPS origin.
  assert.equal(previewResponseHeaders(headers, '127.0.0.1:8080', null, names, true), headers);
});
