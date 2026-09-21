import datetime
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import zipfile
from common import DATA_DIR, ENV_FILE, MANAGED_FILE, load_env


def main():
    values = load_env()
    if MANAGED_FILE.exists():
        state = json.loads(MANAGED_FILE.read_text(encoding='utf-8'))
        binary = Path(state['bin_dir']) / 'mysqldump.exe'
    else:
        executable = shutil.which('mysqldump.exe')
        if not executable:
            import os
            candidates = list(Path(os.getenv('ProgramFiles', 'C:/Program Files')).glob('MySQL/MySQL Server */bin/mysqldump.exe'))
            executable = str(candidates[-1]) if candidates else None
        if not executable:
            raise RuntimeError('Instale os utilitários MySQL ou adicione mysqldump.exe ao PATH para fazer backup.')
        binary = Path(executable)
    folder = DATA_DIR / 'backups'
    folder.mkdir(exist_ok=True)
    destination = folder / ('aura-' + datetime.datetime.now().strftime('%Y%m%d-%H%M%S') + '.zip')
    with tempfile.TemporaryDirectory(prefix='.backup-', dir=DATA_DIR) as temp:
        temp = Path(temp)
        defaults = temp / 'client.cnf'
        def quote(value):
            if any(char in value for char in '\r\n\0'):
                raise ValueError('Configuração inválida.')
            return '"' + value.replace('\\', '\\\\').replace('"', '\\"') + '"'
        defaults.write_text('[client]\n' + '\n'.join(f'{key}={quote(str(value))}' for key, value in {
            'host': values['DB_HOST'], 'port': values['DB_PORT'], 'user': values['DB_USER'],
            'password': values['DB_PASSWORD'],
        }.items()), encoding='utf-8')
        sql = temp / 'database.sql'
        with sql.open('wb') as output:
            result = subprocess.run([str(binary), f'--defaults-extra-file={defaults}', '--single-transaction',
                '--no-tablespaces', '--skip-lock-tables', '--set-gtid-purged=OFF', '--hex-blob',
                values['DB_NAME']], stdout=output, stderr=subprocess.PIPE, timeout=300)
        if result.returncode:
            raise RuntimeError('Falha no backup. Mantenha o Aura/MySQL em execução e confira os dados de conexão.')
        with zipfile.ZipFile(destination, 'x', compression=zipfile.ZIP_DEFLATED) as archive:
            archive.write(sql, 'database.sql')
            archive.write(ENV_FILE, 'configuracao.env')
            archive.writestr('LEIAME.txt', 'Backup privado do Aura. Contém dados de clientes e senha do banco.\n'
                            'Mantenha criptografado e não envie ao GitHub. Consulte o LEIAME do instalador para restauração.\n')
    print('Backup concluído: ' + str(destination))
    print('ATENÇÃO: o ZIP NÃO é criptografado e contém dados e credenciais. Proteja a cópia externa.')


if __name__ == '__main__':
    try:
        main()
    except Exception as exc:
        print('Backup não concluído: ' + str(exc))
        sys.exit(1)
