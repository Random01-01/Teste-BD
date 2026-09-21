/**
 * Only the local development proxy uses this policy. Production Django cookies
 * remain controlled by Django settings. Normally scope to one HTTPS host. A
 * dedicated HTTPS-only development instance may opt in for all responses: its
 * platform proxy may rewrite Host. Never trust caller-supplied forwarding headers.
 */
export function previewOrigin(env = process.env) {
  if (env.DEBUG?.toLowerCase() !== 'true') return null;
  const value = env.PREVIEW_ORIGIN || (env.E2B_SANDBOX_ID
    ? `https://${env.PORT || 5173}-${env.E2B_SANDBOX_ID}.e2b.app` : '');
  if (!value) return null;
  const url = new URL(value);
  if (url.protocol !== 'https:' || url.username || url.password || url.pathname !== '/' || url.search || url.hash) {
    throw new Error('PREVIEW_ORIGIN deve ser uma origem HTTPS, sem caminho ou credenciais.');
  }
  return url.origin;
}

export function previewResponseHeaders(headers, requestHost, origin, cookieNames = ['csrftoken', 'sessionid'], dedicatedHttps = false) {
  if (!origin || (!dedicatedHttps && requestHost?.toLowerCase() !== new URL(origin).host.toLowerCase())) return headers;
  const values = headers['set-cookie'];
  if (!values) return headers;
  return {
    ...headers,
    'set-cookie': (Array.isArray(values) ? values : [values]).map(value => {
      const parts = value.split(';').map(part => part.trim());
      const name = parts[0].split('=', 1)[0];
      if (!cookieNames.includes(name)) return value;
      // Keep HttpOnly, Path, expiry and deletion attributes. The browser still
      // sends real Django cookies; no token/session is invented by the proxy.
      return parts.filter((part, index) => index === 0 || !/^(samesite(?:=|$)|secure$|partitioned$)/i.test(part))
        .concat('SameSite=None', 'Secure', 'Partitioned').join('; ');
    }),
  };
}
