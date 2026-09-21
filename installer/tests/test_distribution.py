import importlib.util
import json
from pathlib import Path
import sys
import tempfile
import unittest
import zipfile

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location('packager', ROOT / 'scripts/build-windows.py')
packager = importlib.util.module_from_spec(spec)
spec.loader.exec_module(packager)
sys.path.insert(0, str(ROOT / 'installer/windows/runtime'))
import common


class DistributionTests(unittest.TestCase):
    def test_allowlist_excludes_databases_secrets_tests_and_demo(self):
        files = packager.files_to_ship()
        self.assertIn('backend/config/desktop.py', files)
        self.assertIn('backend/users/security.py', files)
        self.assertIn('backend/appointments/migrations/0004_schedule_settings.py', files)
        self.assertIn('desktop/run.py', files)
        for name in files:
            self.assertNotIn('.env', name)
            self.assertNotIn('sqlite', name)
            self.assertNotIn('node_modules', name)
            self.assertNotIn('__pycache__', name)
            self.assertNotIn('seed_demo', name)
            self.assertNotIn('tests.py', name)

    def test_two_packages_manifests_and_no_default_account(self):
        with tempfile.TemporaryDirectory() as folder:
            output = Path(folder)
            packager.build(output, '0.1.0')
            self.assertEqual(len(list(output.glob('*.zip'))), 2)
            for edition in ['Essential', 'Complete']:
                payload = output / 'payload' / edition
                info = json.loads((payload / 'release-info.json').read_text())
                self.assertEqual(info['edition'], edition)
                self.assertFalse(info['default_admin'])
                manifest = json.loads((payload / 'manifest.json').read_text())
                for name, sha in manifest['files'].items():
                    self.assertEqual(packager.digest(payload / name), sha, name)
                self.assertIn('-Mode ' + edition, (payload / 'INSTALAR.cmd').read_text())
                self.assertTrue((payload / 'desktop/Configure-Aura.ps1').read_bytes().startswith(b'\xef\xbb\xbf'))
                self.assertNotIn('MANAGED_PREVIEW', (payload / 'frontend/js/config.js').read_text())
            for file in output.glob('*.zip'):
                with zipfile.ZipFile(file) as archive:
                    self.assertTrue(all(not name.startswith('/') and '..' not in Path(name).parts for name in archive.namelist()))

    def test_rejects_unsafe_output_and_invalid_version(self):
        with self.assertRaises(ValueError):
            packager.build(ROOT, '0.1.0')
        with self.assertRaises(ValueError):
            packager.build(ROOT / 'dist/windows', 'bad/version')

    def test_credentials_are_not_corrupted_by_dotenv_quoting(self):
        from dotenv import dotenv_values
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / '.env'
            values = {'SECRET_KEY': 'test-only', 'DB_PASSWORD': 'a#b"c\\d${literal} test',
                      'DATA': 'C:\\Users\\Teste com espaço\\Aura'}
            common.write_env(path, values)
            self.assertEqual(dict(dotenv_values(path, interpolate=False)), values)
            with self.assertRaises(ValueError):
                common.write_env(path, {'BAD': 'line1\nline2'})

    def test_mysql_bootstrap_has_no_network_or_password_arguments(self):
        state = {'bin_dir': 'C:/Program Files/MySQL/bin', 'data_dir': 'C:/Data/Aura/mysql',
                 'memory_name': 'isolated-test-name', 'port': 3307}
        bootstrap = common.mysql_args(state, bootstrap=True)
        self.assertIn('--skip-networking', bootstrap)
        self.assertIn('--shared-memory', bootstrap)
        self.assertFalse(any(arg.startswith('--port=') for arg in bootstrap))
        regular = common.mysql_args(state)
        self.assertIn('--bind-address=127.0.0.1', regular)
        self.assertIn('--port=3307', regular)
        self.assertFalse(any('password' in arg for arg in bootstrap + regular))

    def test_local_wsgi_serves_ui_and_blocks_foreign_hosts(self):
        from serve import local_app
        def api(environ, start_response):
            start_response('200 OK', [('Content-Type', 'application/json')])
            return [b'{"api":true}']
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            (root / 'index.html').write_text('<h1>Aura local</h1>')
            (root / 'static').mkdir()
            app = local_app(api, root, root / 'static', 8765, 'test-instance')
            def request(host, path):
                status = []
                response = app({'HTTP_HOST': host, 'PATH_INFO': path, 'REQUEST_METHOD': 'GET',
                                'SERVER_NAME': '127.0.0.1', 'SERVER_PORT': '8765', 'wsgi.url_scheme': 'http'},
                               lambda code, headers: status.append(code))
                try:
                    body = b''.join(response)
                finally:
                    if hasattr(response, 'close'): response.close()
                return status[0], body
            self.assertIn('200', request('127.0.0.1:8765', '/')[0])
            self.assertIn(b'Aura local', request('localhost:8765', '/')[1])
            self.assertIn(b'test-instance', request('localhost:8765', '/__aura_health/')[1])
            self.assertIn(b'"api":true', request('localhost:8765', '/api/services/')[1])
            self.assertIn('400', request('evil.example', '/api/services/')[0])


if __name__ == '__main__':
    unittest.main()
