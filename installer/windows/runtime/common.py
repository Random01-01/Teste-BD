"""Shared Windows runtime helpers. No credentials are embedded in the release."""
import json
import os
from pathlib import Path
import secrets
import socket
import subprocess
import time

APP_DIR = Path(os.getenv('AURA_APP_DIR', str(Path(__file__).resolve().parent.parent)))
DATA_DIR = Path(os.getenv('AURA_DATA_DIR', str(Path(os.getenv('LOCALAPPDATA', str(Path.home()))) / 'Aura')))
ENV_FILE = DATA_DIR / '.env'
MANAGED_FILE = DATA_DIR / 'mysql-managed.json'


def write_json(path, data):
    path = Path(path)
    temp = path.with_suffix(path.suffix + '.tmp')
    temp.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding='utf-8')
    os.replace(temp, path)


def write_env(path, values):
    # JSON double-quoted values are also dotenv-compatible. Prevent line injection.
    for value in values.values():
        if any(char in str(value) for char in ('\n', '\r', '\0')):
            raise ValueError('Configurações não podem conter quebras de linha.')
    text = '\n'.join(f'{key}={json.dumps(str(value), ensure_ascii=False)}' for key, value in values.items()) + '\n'
    temp = Path(str(path) + '.tmp')
    temp.write_text(text, encoding='utf-8')
    os.replace(temp, path)


def load_env():
    from dotenv import dotenv_values
    if not ENV_FILE.is_file():
        raise RuntimeError('Execute primeiro o atalho Configurar Aura.')
    return dict(dotenv_values(ENV_FILE, interpolate=False))


def configure_django():
    import sys
    values = load_env()
    # Installed-instance settings must not inherit unrelated development secrets.
    os.environ.update({key: value for key, value in values.items() if value is not None})
    os.environ.update(DJANGO_ENV_FILE=str(ENV_FILE), AURA_DATA_DIR=str(DATA_DIR),
                      DJANGO_SETTINGS_MODULE='config.desktop')
    sys.path.insert(0, str(APP_DIR / 'backend'))
    import django
    django.setup()


def port_free(port):
    with socket.socket() as sock:
        try:
            sock.bind(('127.0.0.1', port))
            return True
        except OSError:
            return False


def mysql_args(state, bootstrap=False):
    binary = Path(state['bin_dir']) / 'mysqld.exe'
    args = [str(binary), '--no-defaults', f'--basedir={binary.parent.parent}',
            f'--datadir={state["data_dir"]}', '--mysqlx=0', '--local-infile=0',
            '--secure-file-priv=NULL', '--skip-log-bin', '--innodb-buffer-pool-size=128M',
            f'--log-error={DATA_DIR / "logs" / "mysql.log"}']
    if bootstrap:
        args += ['--skip-networking', '--shared-memory', f'--shared-memory-base-name={state["memory_name"]}']
    else:
        args += ['--bind-address=127.0.0.1', f'--port={state["port"]}']
    return args


def stop_owned(process):
    """Terminate only a process started by this invocation; never kill by port/name."""
    if process and process.poll() is None:
        process.terminate()
        try:
            process.wait(timeout=30)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait(timeout=10)


def connect(values):
    import MySQLdb
    return MySQLdb.connect(host=values['DB_HOST'], port=int(values['DB_PORT']),
                          user=values['DB_USER'], passwd=values['DB_PASSWORD'],
                          db=values['DB_NAME'], charset='utf8mb4', connect_timeout=3)


def start_managed():
    if not MANAGED_FILE.exists():
        return None
    state = json.loads(MANAGED_FILE.read_text(encoding='utf-8'))
    if not state.get('ready'):
        raise RuntimeError('A configuração do MySQL não terminou. Execute Configurar Aura novamente.')
    if not port_free(int(state['port'])):
        raise RuntimeError(f'A porta MySQL {state["port"]} está ocupada. Não foi encerrado nenhum processo. Feche a outra instância ou reinicie o Windows.')
    process = subprocess.Popen(mysql_args(state), stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    values = load_env()
    try:
        for _ in range(60):
            if process.poll() is not None:
                break
            try:
                with connect(values) as db:
                    pass
                return process
            except Exception:
                time.sleep(1)
        raise RuntimeError('MySQL local não iniciou. Consulte o log privado na pasta de dados/logs/mysql.log.')
    except BaseException:
        stop_owned(process)
        raise


def new_values():
    return {
        'DEBUG': 'False', 'SECRET_KEY': secrets.token_urlsafe(48), 'DB_ENGINE': 'mysql',
        'ALLOWED_HOSTS': 'localhost,127.0.0.1', 'COOKIE_SAMESITE': 'Lax',
        'FRONTEND_URL': 'http://127.0.0.1:8765/', 'AURA_PORT': '8765',
        'AURA_INSTANCE_ID': secrets.token_hex(16),
        'EMAIL_BACKEND': 'django.core.mail.backends.filebased.EmailBackend',
    }


def shutdown_managed(process):
    if not process or process.poll() is not None:
        return
    state = json.loads(MANAGED_FILE.read_text(encoding='utf-8'))
    defaults = DATA_DIR / '.mysql-shutdown.cnf'
    try:
        defaults.write_text('[client]\nuser=root\npassword=' + state['root_password'] + '\n', encoding='utf-8')
        subprocess.run([str(Path(state['bin_dir']) / 'mysql.exe'), f'--defaults-extra-file={defaults}',
                        '--protocol=TCP', '--host=127.0.0.1', f'--port={state["port"]}', '--connect-timeout=3'],
                       input='SHUTDOWN;', text=True, stdout=subprocess.DEVNULL,
                       stderr=subprocess.DEVNULL, timeout=15)
        try:
            process.wait(timeout=30)
        except subprocess.TimeoutExpired:
            print('MySQL demorou a encerrar; confira logs/mysql.log antes de reiniciar.')
    finally:
        defaults.unlink(missing_ok=True)
        stop_owned(process)
