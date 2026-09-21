#!/usr/bin/env python3
"""Build allowlisted installer payloads. Never zip the working tree wholesale."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import shutil
import zipfile

ROOT = Path(__file__).resolve().parent.parent
EDITIONS = {'Essential': 'Essencial', 'Complete': 'Completo'}


def files_to_ship(root=ROOT):
    root = Path(root)
    files = {}
    for app in ['config', 'users', 'clients', 'services', 'appointments']:
        for path in (root / 'backend' / app).rglob('*.py'):
            if path.name == 'tests.py' or '__pycache__' in path.parts or 'management' in path.parts:
                continue
            files[path.relative_to(root).as_posix()] = path
    for name in ['manage.py', 'requirements.txt', 'requirements-windows.txt']:
        files['backend/' + name] = root / 'backend' / name
    files['frontend/index.html'] = root / 'frontend/index.html'
    for folder in ['css', 'js', 'assets']:
        for path in (root / 'frontend' / folder).rglob('*'):
            if path.is_file() and path.suffix.lower() in {'.css', '.js', '.svg', '.png', '.jpg', '.jpeg', '.woff2', '.txt'}:
                files[path.relative_to(root).as_posix()] = path
    for path in (root / 'installer/windows/runtime').iterdir():
        if path.suffix in {'.py', '.ps1'}:
            files['desktop/' + path.name] = path
    for name in ['LEIAME.txt', 'CONTEUDO.txt', 'aura.ico']:
        files[name] = root / 'installer/windows' / name
    return files


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def build(output, version, root=ROOT):
    if not re.fullmatch(r'\d+\.\d+\.\d+', version):
        raise ValueError('Use versão numérica X.Y.Z para os instaladores Windows.')
    output = Path(output).resolve()
    # Only a dedicated output directory may be overwritten; never a repository.
    if output == Path(root).resolve() or output in Path(root).resolve().parents:
        raise ValueError('Diretório de saída inseguro.')
    output.mkdir(parents=True, exist_ok=True)
    inputs = files_to_ship(root)
    for edition, label in EDITIONS.items():
        payload = output / 'payload' / edition
        if payload.exists():
            shutil.rmtree(payload)
        for relative, source in inputs.items():
            destination = payload / relative
            destination.parent.mkdir(parents=True, exist_ok=True)
            if source.suffix == '.ps1' or relative in {'LEIAME.txt', 'CONTEUDO.txt'}:
                destination.write_text(source.read_text(encoding='utf-8-sig'), encoding='utf-8-sig')
            else:
                shutil.copyfile(source, destination)
        # Static desktop config never inherits preview/demo or external API URLs.
        (payload / 'frontend/js/config.js').write_text('window.AURA_CONFIG = { API_URL: "/api", DEMO: false };\n', encoding='utf-8')
        for name, script, args in [('INSTALAR', 'Configure-Aura.ps1', ' -Mode ' + edition),
                                   ('INICIAR', 'Start-Aura.ps1', ''), ('BACKUP', 'Backup-Aura.ps1', '')]:
            (payload / (name + '.cmd')).write_bytes((
                '@echo off\r\n' + f'powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0desktop\\{script}"{args}\r\nexit /b %errorlevel%\r\n'
            ).encode('ascii'))
        info = {'application': 'Aura', 'version': version, 'edition': edition, 'platform': 'windows-x64',
                'online': True, 'database': 'MySQL', 'default_admin': False}
        (payload / 'release-info.json').write_text(json.dumps(info, indent=2), encoding='utf-8')
        manifest = {'release': info, 'files': {p.relative_to(payload).as_posix(): digest(p)
                    for p in sorted(payload.rglob('*')) if p.is_file()}}
        (payload / 'manifest.json').write_text(json.dumps(manifest, indent=2), encoding='utf-8')
        zip_path = output / f'Aura-Arquivos-{label}-{version}.zip'
        with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as archive:
            for path in sorted(payload.rglob('*')):
                if path.is_file():
                    archive.write(path, f'Aura-{label}-{version}/' + path.relative_to(payload).as_posix())
    for name in ['LEIAME.txt', 'CONTEUDO.txt']:
        shutil.copyfile(Path(root) / 'installer/windows' / name, output / name)
    checksums(output)


def checksums(output):
    output = Path(output)
    files = sorted(p for p in output.iterdir() if p.is_file() and p.name != 'SHA256SUMS.txt')
    (output / 'SHA256SUMS.txt').write_text(''.join(f'{digest(p)}  {p.name}\n' for p in files), encoding='utf-8')


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--version', default='0.1.0')
    parser.add_argument('--output', type=Path, default=ROOT / 'dist/windows')
    parser.add_argument('--checksums-only', action='store_true')
    args = parser.parse_args()
    if args.checksums_only:
        checksums(args.output)
    else:
        build(args.output, args.version)
    print('Pacotes gerados em:', args.output)
