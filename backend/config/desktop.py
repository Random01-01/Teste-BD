"""Windows desktop ONLY. Bind to loopback, never publish these settings to a LAN."""
import os
from pathlib import Path
from .settings import *  # noqa: F403

DEBUG = False
DATA_DIR = Path(os.environ['AURA_DATA_DIR'])
DESKTOP_PORT = int(os.getenv('AURA_PORT', '8765'))
if not 1024 <= DESKTOP_PORT <= 65535:
    raise ValueError('AURA_PORT deve estar entre 1024 e 65535.')
ALLOWED_HOSTS = ['127.0.0.1', 'localhost']
FRONTEND_URL = f'http://127.0.0.1:{DESKTOP_PORT}/'
CORS_ALLOWED_ORIGINS = []  # The frontend and API share one local origin.
CSRF_TRUSTED_ORIGINS = [f'http://127.0.0.1:{DESKTOP_PORT}', f'http://localhost:{DESKTOP_PORT}']
SECURE_SSL_REDIRECT = False  # HTTP allowed only because the server binds loopback.
SECURE_HSTS_SECONDS = 0
SECURE_PROXY_SSL_HEADER = None
SESSION_COOKIE_SECURE = False
CSRF_COOKIE_SECURE = False
SESSION_COOKIE_SAMESITE = 'Lax'
CSRF_COOKIE_SAMESITE = 'Lax'
SESSION_COOKIE_NAME = 'aura_desktop_session'
CSRF_COOKIE_NAME = 'aura_desktop_csrf'
STATIC_ROOT = DATA_DIR / 'static'
EMAIL_BACKEND = os.getenv('EMAIL_BACKEND', 'django.core.mail.backends.filebased.EmailBackend')
EMAIL_FILE_PATH = str(DATA_DIR / 'emails')
X_FRAME_OPTIONS = 'DENY'
