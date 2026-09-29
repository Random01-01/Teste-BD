#!/usr/bin/env python3
"""Create a separate, disposable HTTPS-only test instance. Never overwrite data."""
import os
from pathlib import Path
import secrets
import subprocess
import sys

ROOT = Path(__file__).resolve().parent.parent
BACKEND = ROOT / 'backend'
ENV_FILE = BACKEND / '.env.test-preview'
DATABASE = BACKEND / 'test-preview.sqlite3'


def main():
    if ENV_FILE.exists() or DATABASE.exists():
        raise SystemExit('A instância de teste já existe. Nenhum arquivo foi alterado. Use o .env.test-preview existente.')
    sandbox = os.getenv('E2B_SANDBOX_ID')
    origin = os.getenv('TEST_PREVIEW_ORIGIN') or (f'https://8080-{sandbox}.e2b.app' if sandbox else '')
    if not origin:
        raise SystemExit('Defina TEST_PREVIEW_ORIGIN com a origem HTTPS do seu proxy de teste.')
    from urllib.parse import urlsplit
    parsed = urlsplit(origin)
    if parsed.scheme != 'https' or not parsed.netloc or parsed.username or parsed.password or parsed.path not in ('', '/') or parsed.query or parsed.fragment:
        raise SystemExit('TEST_PREVIEW_ORIGIN precisa ser uma origem HTTPS sem caminho ou credenciais.')
    origin = f'https://{parsed.netloc}'
    config = {
        'DEBUG': 'True',
        'SECRET_KEY': secrets.token_urlsafe(50),
        'DB_ENGINE': 'sqlite',
        'DB_SQLITE_PATH': str(DATABASE),
        'DJANGO_ENV_FILE': str(ENV_FILE),
        'ALLOWED_HOSTS': 'localhost,127.0.0.1,testserver,' + parsed.hostname + (f',8001-{sandbox}.e2b.app' if sandbox else ''),
        'CORS_ALLOWED_ORIGINS': origin,
        'CSRF_TRUSTED_ORIGINS': origin,
        'FRONTEND_URL': origin + '/',
        'PORT': '8080',
        'BACKEND_URL': 'http://127.0.0.1:8001',
        'PREVIEW_ORIGIN': origin,
        'PREVIEW_COOKIE_POLICY': 'partitioned',
        'COOKIE_SECURE': 'True',
        'COOKIE_SAMESITE': 'None',
        'SESSION_COOKIE_NAME': 'aura_test_session',
        'CSRF_COOKIE_NAME': 'aura_test_csrf',
        'PREVIEW_LABEL': 'Aura — Teste limpo',
        'PREVIEW_INSTANCE_ID': 'isolated-' + secrets.token_hex(6),
        'PREVIEW_START_PAGE': 'login',
        'DEV_DEMO': 'false',
        'DEMO_EMAIL': 'demo@example.com',
        'DEMO_PASSWORD': secrets.token_urlsafe(32),
        'EMAIL_BACKEND': 'django.core.mail.backends.filebased.EmailBackend',
        'EMAIL_FILE_PATH': str(BACKEND / '.test-preview-emails'),
    }
    with ENV_FILE.open('x', encoding='utf-8') as file:
        os.chmod(ENV_FILE, 0o600)
        file.write('\n'.join(f'{key}={value}' for key, value in config.items()) + '\n')
    env = {**os.environ, **config}
    for args in [('migrate', '--noinput'), ('seed_demo',), ('check',)]:
        subprocess.run([sys.executable, 'manage.py', *args], cwd=BACKEND, env=env, check=True)
    print('Instância isolada criada; a base normal foi preservada.')
    print('Crie a conta de acesso sem incluir sua senha no código:')
    print('DJANGO_ENV_FILE=backend/.env.test-preview python backend/manage.py createsuperuser')
    print('Inicie a API: DJANGO_ENV_FILE=backend/.env.test-preview python backend/manage.py runserver 0.0.0.0:8001 --noreload')
    print('Inicie a interface: node --env-file=backend/.env.test-preview scripts/dev-server.mjs')
    print('Acesso pela prévia autorizada da plataforma; não distribua a URL e2b.app diretamente.')


if __name__ == '__main__':
    main()
