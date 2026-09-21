const config = window.AURA_CONFIG || {};
export const demo = config.DEMO === true;
export const managedPreview = config.MANAGED_PREVIEW === true;
export const previewLabel = config.PREVIEW_LABEL || '';
let csrf = '';
let csrfRefresh = null;
const base = (config.API_URL || '/api').replace(/\/$/, '');
const safeMethods = ['GET', 'HEAD', 'OPTIONS'];

function messages(value) {
  if (typeof value === 'string') return value;
  if (Array.isArray(value)) return value.map(messages).join(' ');
  return Object.entries(value || {}).filter(([key]) => !['code', 'csrfReason'].includes(key))
    .map(([key, val]) => `${['detail', 'non_field_errors'].includes(key) ? '' : key + ': '}${messages(val)}`).join(' ');
}

async function request(path, method, data) {
  let response;
  try {
    response = await fetch(base + path, {
      method, credentials: 'include', cache: 'no-store',
      headers: {
        Accept: 'application/json',
        ...(data !== undefined ? { 'Content-Type': 'application/json' } : {}),
        ...(!safeMethods.includes(method) ? { 'X-CSRFToken': csrf } : {}),
      },
      ...(data !== undefined ? { body: JSON.stringify(data) } : {}),
    });
  } catch { throw new Error('Não foi possível conectar ao servidor. Verifique sua conexão e tente novamente.'); }
  const result = response.status === 204 ? null : await response.json().catch(() => ({ detail: 'O servidor retornou uma resposta inesperada.' }));
  return { response, result };
}

function unwrap({ response, result }) {
  if (!response.ok) {
    const cookieBlocked = result?.code === 'csrf_failed' && result.csrfReason === 'cookie_missing';
    const message = cookieBlocked
      ? (managedPreview
        ? 'O navegador não está enviando os cookies de segurança da prévia. Recarregue pelo painel de prévia do Arena. O endereço direto exige autorização da plataforma.'
        : 'O navegador não está enviando os cookies de segurança. Abra o Aura em uma nova aba para entrar ou recuperar sua senha.')
      : result?.code === 'csrf_failed' && ['origin_rejected', 'referer_rejected'].includes(result.csrfReason)
        ? 'O endereço desta página não está autorizado pelo servidor. Verifique a configuração de origens do back-end.'
        : messages(result);
    const error = new Error(message);
    error.status = response.status;
    error.code = result?.code;
    error.csrfReason = result?.csrfReason;
    throw error;
  }
  if (result?.csrfToken) csrf = result.csrfToken;
  return result;
}

async function refreshCsrf() {
  // Share one refresh across concurrent requests. A GET never creates a session
  // or authenticates a user: Django still requires its matching CSRF cookie.
  if (!csrfRefresh) {
    csrfRefresh = request('/auth/csrf/', 'GET').then(unwrap).then(result => {
      if (!result?.csrfToken) throw new Error('Não foi possível obter o token de segurança. Tente novamente.');
    }).finally(() => { csrfRefresh = null; });
  }
  await csrfRefresh;
}

export async function api(path, method = 'GET', data) {
  method = method.toUpperCase();
  const unsafe = !safeMethods.includes(method);
  if (unsafe && !csrf) await refreshCsrf();
  let outcome = await request(path, method, data);
  // Retry ONCE, only when the server explicitly confirms that CSRF rejected the
  // request before any view ran. Never replay a network failure, login failure,
  // permission denial, rate limit or an ambiguous server error.
  if (unsafe && outcome.response.status === 403 && outcome.result?.code === 'csrf_failed'
      && ['cookie_missing', 'token_invalid'].includes(outcome.result.csrfReason)) {
    await refreshCsrf();
    outcome = await request(path, method, data);
  }
  return unwrap(outcome);
}
