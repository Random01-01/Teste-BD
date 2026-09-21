const config = window.AURA_CONFIG || {};
export const demo = config.DEMO === true;
let csrf = '';
const base = (config.API_URL || '/api').replace(/\/$/, '');
function messages(value) {
  if (typeof value === 'string') return value;
  if (Array.isArray(value)) return value.map(messages).join(' ');
  return Object.entries(value || {}).map(([key, val]) => `${['detail', 'non_field_errors'].includes(key) ? '' : key + ': '}${messages(val)}`).join(' ');
}
export async function api(path, method = 'GET', data) {
  if (!['GET', 'HEAD'].includes(method) && !csrf) await api('/auth/csrf/');
  let response;
  try {
    response = await fetch(base + path, {
      method, credentials: 'include', headers: { 'Accept': 'application/json', ...(data !== undefined ? { 'Content-Type': 'application/json' } : {}), ...(!['GET', 'HEAD'].includes(method) ? { 'X-CSRFToken': csrf } : {}) },
      ...(data !== undefined ? { body: JSON.stringify(data) } : {}),
    });
  } catch { throw new Error('Não foi possível conectar ao servidor. Verifique sua conexão e tente novamente.'); }
  const result = response.status === 204 ? null : await response.json().catch(() => ({ detail: 'O servidor retornou uma resposta inesperada.' }));
  if (!response.ok) { const error = new Error(messages(result)); error.status = response.status; throw error; }
  if (result?.csrfToken) csrf = result.csrfToken;
  return result;
}
