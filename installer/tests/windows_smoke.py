"""CI-only real Windows/MySQL smoke test of the packaged application."""
import json
import os
from pathlib import Path
import secrets
import signal
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.request
import http.cookiejar


def main():
    payload = Path(sys.argv[1]).resolve()
    with tempfile.TemporaryDirectory(prefix='Aura CI ') as folder:
        data = Path(folder)
        os.environ.update(AURA_APP_DIR=str(payload), AURA_DATA_DIR=str(data), AURA_NO_BROWSER='1')
        sys.path.insert(0, str(payload / 'desktop'))
        import common
        import configure
        configure.ask = lambda label, default='': default
        mysql_bin = Path(os.environ['ProgramFiles']) / 'MySQL/MySQL Server 8.4/bin'
        state = configure.initialize_mysql(str(mysql_bin))
        assert state['ready'] and state['root_password'] and state['app_password']
        # Re-running setup must preserve the same DB identity and credentials.
        assert configure.initialize_mysql(str(mysql_bin))['app_password'] == state['app_password']
        values = common.new_values()
        values.update(DB_HOST='127.0.0.1', DB_PORT=str(state['port']), DB_USER='aura_app',
                      DB_PASSWORD=state['app_password'], DB_NAME='aura')
        common.write_env(common.ENV_FILE, values)
        mysql = common.start_managed()
        try:
            common.configure_django()
            from django.core.management import call_command
            from django.contrib.auth import get_user_model
            call_command('migrate', interactive=False, verbosity=0)
            call_command('collectstatic', interactive=False, verbosity=0)
            password = secrets.token_urlsafe(24)
            get_user_model().objects.create_superuser(email='ci@example.com', password=password)
            (data / 'configured').write_text('CI configured')
        finally:
            common.shutdown_managed(mysql)
        process = subprocess.Popen([sys.executable, str(payload / 'desktop/run.py')],
                                   creationflags=subprocess.CREATE_NEW_PROCESS_GROUP)
        jar = http.cookiejar.CookieJar()
        client = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(jar))
        base = 'http://127.0.0.1:8765'
        def request(path, method='GET', body=None, token=None, origin=None):
            headers = {'Content-Type': 'application/json'}
            if token: headers['X-CSRFToken'] = token
            if origin: headers['Origin'] = origin
            req = urllib.request.Request(base + path, data=None if body is None else json.dumps(body).encode(),
                                         headers=headers, method=method)
            try:
                with client.open(req, timeout=5) as response:
                    return response.status, response.read()
            except urllib.error.HTTPError as response:
                return response.code, response.read()
        try:
            for _ in range(60):
                if process.poll() is not None: raise RuntimeError('Desktop server exited')
                try:
                    if request('/__aura_health/')[0] == 200: break
                except (OSError, urllib.error.URLError): pass
                time.sleep(1)
            assert b'<html' in request('/')[1]
            assert request('/static/admin/css/base.css')[0] == 200
            token = json.loads(request('/api/auth/csrf/')[1])['csrfToken']
            credentials = {'email': 'ci@example.com', 'password': password}
            assert request('/api/auth/login/', 'POST', credentials)[0] == 403
            assert request('/api/auth/login/', 'POST', credentials, token, 'https://evil.example')[0] == 403
            status, body = request('/api/auth/login/', 'POST', credentials, token, base)
            assert status == 200, status
            user = json.loads(body)
            assert user['is_staff'] is True
            assert request('/api/auth/me/')[0] == 200
            assert request('/api/auth/logout/', 'POST', {}, user['csrfToken'], base)[0] == 200
            assert request('/api/auth/me/')[0] == 403
            # A real SQL backup, not a copy of live MySQL data files.
            subprocess.run([sys.executable, str(payload / 'desktop/backup.py')], check=True)
            assert list((data / 'backups').glob('*.zip'))
        finally:
            process.send_signal(signal.CTRL_BREAK_EVENT)
            try: process.wait(timeout=50)
            except subprocess.TimeoutExpired:
                subprocess.run(['taskkill', '/PID', str(process.pid), '/T', '/F'], check=False)
            if process.returncode not in (0, None):
                raise RuntimeError(f'Desktop failed to stop cleanly: {process.returncode}')
        print('Windows smoke passed: private MySQL, migrations, UI, admin static, CSRF, login/logout and backup.')


if __name__ == '__main__':
    main()
