import argparse
import getpass
import json
import os
from pathlib import Path
import re
import secrets
import subprocess
import sys
import time
from common import (APP_DIR, DATA_DIR, ENV_FILE, MANAGED_FILE, configure_django, connect,
                    load_env, mysql_args, new_values, port_free, start_managed, stop_owned,
                    write_env, write_json, shutdown_managed)


def ask(label, default=''):
    value = input(f'{label}' + (f' [{default}]' if default else '') + ': ').strip()
    return value or default


def client_file(path, password):
    # Only generated hex passwords are used for bootstrap; no command-line secrets.
    path.write_text('[client]\nuser=root\npassword=' + password + '\n', encoding='utf-8')


def initialize_mysql(bin_dir):
    binary = Path(bin_dir) / 'mysqld.exe'
    client = Path(bin_dir) / 'mysql.exe'
    if not binary.is_file() or not client.is_file():
        raise RuntimeError('Binários oficiais MySQL 8.4 não encontrados.')
    version = subprocess.check_output([str(binary), '--version'], text=True)
    if not re.search(r'\b8\.4\.', version):
        raise RuntimeError('O setup completo requer os binários do MySQL 8.4 LTS.')
    if MANAGED_FILE.exists():
        state = json.loads(MANAGED_FILE.read_text(encoding='utf-8'))
        if state.get('ready'):
            return state
    else:
        if (DATA_DIR / 'mysql').exists() and any((DATA_DIR / 'mysql').iterdir()):
            raise RuntimeError('Já há dados MySQL sem metadados do Aura. Nenhum arquivo foi apagado.')
        port = int(ask('Porta da instância MySQL privada do Aura', '3307'))
        if not 1024 <= port <= 65535 or not port_free(port):
            raise RuntimeError('Porta inválida ou ocupada. Nenhum serviço existente foi alterado.')
        state = {'bin_dir': str(Path(bin_dir).resolve()), 'data_dir': str(DATA_DIR / 'mysql'),
                 'port': port, 'memory_name': 'AuraSetup' + secrets.token_hex(16),
                 'root_password': secrets.token_hex(32), 'app_password': secrets.token_hex(32), 'ready': False}
        write_json(MANAGED_FILE, state)  # Private ACL is set by the PowerShell launcher.
    directory = Path(state['data_dir'])
    directory.mkdir(exist_ok=True)
    (DATA_DIR / 'logs').mkdir(exist_ok=True)
    if not any(directory.iterdir()):
        print('Inicializando banco privado. Isso pode levar alguns minutos...')
        result = subprocess.run([str(binary), '--no-defaults', '--initialize-insecure',
                                 f'--basedir={binary.parent.parent}', f'--datadir={directory}',
                                 f'--log-error={DATA_DIR / "logs" / "mysql.log"}'],
                                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=180)
        if result.returncode:
            raise RuntimeError('Falha na inicialização do MySQL. Dados preservados; consulte logs/mysql.log.')
    process = subprocess.Popen(mysql_args(state, bootstrap=True), stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    defaults = DATA_DIR / '.mysql-bootstrap.cnf'
    sql = (
        'CREATE DATABASE IF NOT EXISTS aura CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;\n'
        "CREATE USER IF NOT EXISTS 'aura_app'@'localhost' IDENTIFIED BY '" + state['app_password'] + "';\n"
        "ALTER USER 'aura_app'@'localhost' IDENTIFIED BY '" + state['app_password'] + "';\n"
        "GRANT ALL PRIVILEGES ON aura.* TO 'aura_app'@'localhost';\n"
        "ALTER USER 'root'@'localhost' IDENTIFIED BY '" + state['root_password'] + "';\n"
    )
    try:
        # Bootstrap is shared-memory ONLY: an empty root password is never exposed
        # over TCP. On interrupted setup, try the saved random password first.
        for attempt in range(60):
            if process.poll() is not None:
                raise RuntimeError('MySQL não iniciou. Consulte o log privado de instalação.')
            for password in (state['root_password'], ''):
                client_file(defaults, password)
                args = [str(client), f'--defaults-extra-file={defaults}', '--protocol=MEMORY',
                        f'--shared-memory-base-name={state["memory_name"]}', '--connect-timeout=2']
                result = subprocess.run(args, input='SELECT 1;', text=True, stdout=subprocess.DEVNULL,
                                        stderr=subprocess.DEVNULL, timeout=10)
                if result.returncode == 0:
                    result = subprocess.run(args, input=sql, text=True, stdout=subprocess.DEVNULL,
                                            stderr=subprocess.DEVNULL, timeout=30)
                    if result.returncode:
                        raise RuntimeError('Falha ao configurar o banco privado. Execute novamente o configurador; nenhum dado será apagado.')
                    state['ready'] = True
                    write_json(MANAGED_FILE, state)
                    # Shut down gracefully with the new root password, still off TCP.
                    client_file(defaults, state['root_password'])
                    subprocess.run(args, input='SHUTDOWN;', text=True, stdout=subprocess.DEVNULL,
                                   stderr=subprocess.DEVNULL, timeout=15)
                    try:
                        process.wait(timeout=30)
                    except subprocess.TimeoutExpired:
                        pass
                    return state
            time.sleep(1)
        raise RuntimeError('Tempo esgotado ao preparar o MySQL. Consulte logs/mysql.log.')
    finally:
        defaults.unlink(missing_ok=True)
        stop_owned(process)


def existing_database():
    print('Use um banco MySQL LOCAL dedicado ao Aura, vazio ou de uma instalação Aura existente.')
    print('A conta informada precisa poder criar/alterar tabelas nesse banco. Não use root.')
    values = new_values()
    values['DB_HOST'] = '127.0.0.1'
    values['DB_PORT'] = ask('Porta do MySQL existente', '3306')
    values['DB_NAME'] = ask('Nome do banco dedicado', 'aura')
    values['DB_USER'] = ask('Usuário do banco', 'aura_app')
    values['DB_PASSWORD'] = getpass.getpass('Senha do banco (não aparece na tela): ')
    if not values['DB_PASSWORD'] or values['DB_USER'].lower() == 'root':
        raise RuntimeError('Use um usuário de aplicação com senha, não root.')
    if not values['DB_PORT'].isdigit() or not 1 <= int(values['DB_PORT']) <= 65535:
        raise RuntimeError('Porta inválida.')
    with connect(values) as db:
        with db.cursor() as cursor:
            cursor.execute('SHOW TABLES')
            tables = {row[0] for row in cursor.fetchall()}
    aura_tables = {'users_user', 'services_service', 'appointments_appointment', 'clients_clientprofile', 'django_migrations'}
    if tables and not aura_tables.issubset(tables):
        raise RuntimeError('Esse banco já contém tabelas de outra aplicação. Use um banco dedicado; nada foi alterado.')
    return values


def create_admin():
    from django.contrib.auth import get_user_model
    from django.contrib.auth.password_validation import validate_password
    from django.core.exceptions import ValidationError
    from django.core.validators import validate_email
    User = get_user_model()
    if User.objects.filter(is_superuser=True, is_active=True).exists():
        print('Conta administradora existente preservada. Nenhuma senha foi redefinida.')
        return
    print('\nCrie sua conta administradora. Não existe senha padrão.')
    while True:
        email = input('E-mail da administradora: ').strip().lower()
        password = getpass.getpass('Senha (mínimo de 8 caracteres, não comum): ')
        confirmation = getpass.getpass('Confirme a senha: ')
        try:
            validate_email(email)
            validate_password(password, User(email=email))
            if password != confirmation:
                raise ValidationError('As senhas não coincidem.')
            if User.objects.filter(email=email).exists():
                raise ValidationError('E-mail já existente. Escolha outro ou recupere o acesso existente.')
        except ValidationError as exc:
            print(' '.join(exc.messages))
            continue
        User.objects.create_superuser(email=email, password=password, first_name='Administradora')
        print('Administradora criada com senha armazenada em hash.')
        return


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--mode', choices=['Essential', 'Complete'], required=True)
    parser.add_argument('--mysql-bin', default='')
    args = parser.parse_args()
    if os.name != 'nt':
        raise RuntimeError('Este configurador é específico para Windows x64.')
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    process = None
    try:
        if ENV_FILE.exists():
            print('Configuração existente preservada. Aplicando somente atualizações/migrations.')
        elif args.mode == 'Complete':
            state = initialize_mysql(args.mysql_bin)
            values = new_values()
            values.update(DB_HOST='127.0.0.1', DB_PORT=str(state['port']), DB_NAME='aura',
                          DB_USER='aura_app', DB_PASSWORD=state['app_password'])
            write_env(ENV_FILE, values)
        else:
            write_env(ENV_FILE, existing_database())
        process = start_managed()
        configure_django()
        from django.core.management import call_command
        call_command('check', verbosity=0)
        call_command('migrate', interactive=False, verbosity=1)
        call_command('collectstatic', interactive=False, verbosity=0)
        create_admin()
        (DATA_DIR / 'configured').write_text('Aura configurado\n', encoding='utf-8')
        print('\nConcluído! Abra o atalho Iniciar Aura. Dados guardados em: ' + str(DATA_DIR))
        print('Não há envio real de e-mails até configurar SMTP. Não use dados reais durante os testes.')
    finally:
        shutdown_managed(process)


if __name__ == '__main__':
    try:
        main()
    except (Exception, KeyboardInterrupt) as exc:
        # Connector errors can contain usernames/hostnames but never print env or SQL.
        print('\nConfiguração não concluída: ' + (str(exc) or 'operação cancelada'))
        print('Os arquivos e dados existentes foram preservados. Corrija o problema e execute Configurar Aura novamente.')
        sys.exit(1)
