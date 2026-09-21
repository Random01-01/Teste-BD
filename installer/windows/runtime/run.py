import ctypes
import hashlib
import json
import os
import signal
import sys
import urllib.request
import webbrowser
from common import (APP_DIR, DATA_DIR, configure_django, load_env, port_free,
                    start_managed, shutdown_managed)
from serve import local_app


def main():
    if not (DATA_DIR / 'configured').exists():
        raise RuntimeError('A instalação precisa ser configurada. Abra o atalho Configurar Aura.')
    if os.name == 'nt':
        signal.signal(signal.SIGBREAK, signal.default_int_handler)
    values = load_env()
    port = int(values.get('AURA_PORT', '8765'))
    url = f'http://127.0.0.1:{port}/'
    mutex = None
    if os.name == 'nt':
        kernel = ctypes.WinDLL('kernel32', use_last_error=True)
        kernel.CreateMutexW.restype = ctypes.c_void_p
        kernel.CreateMutexW.argtypes = [ctypes.c_void_p, ctypes.c_bool, ctypes.c_wchar_p]
        kernel.CloseHandle.argtypes = [ctypes.c_void_p]
        mutex = kernel.CreateMutexW(None, False, 'Local\\Aura-' + hashlib.sha256(str(DATA_DIR).encode()).hexdigest()[:24])
        if not mutex:
            raise RuntimeError('Não foi possível obter o bloqueio da aplicação.')
        if ctypes.get_last_error() == 183:
            try:
                with urllib.request.urlopen(url + '__aura_health/', timeout=3) as response:
                    if json.load(response).get('instance') == values.get('AURA_INSTANCE_ID'):
                        webbrowser.open(url + '#login')
                        return
            finally:
                kernel.CloseHandle(mutex)
            raise RuntimeError('O Aura já está iniciando. Aguarde alguns segundos.')
    mysql = None
    try:
        if not port_free(port):
            raise RuntimeError(f'A porta {port} está ocupada por outro processo. Nenhum processo foi encerrado.')
        mysql = start_managed()
        configure_django()
        from django.conf import settings
        from django.core.wsgi import get_wsgi_application
        from waitress.server import create_server
        app = local_app(get_wsgi_application(), APP_DIR / 'frontend', settings.STATIC_ROOT,
                        port, values['AURA_INSTANCE_ID'])
        server = create_server(app, host='127.0.0.1', port=port, threads=4, clear_untrusted_proxy_headers=True)
        print(f'Aura em execução: {url}')
        print('Mantenha esta janela aberta. Para encerrar com segurança, pressione Ctrl+C e aguarde.')
        if os.getenv('AURA_NO_BROWSER') != '1':
            webbrowser.open(url + '#login')
        try:
            server.run()
        except KeyboardInterrupt:
            print('\nEncerrando o Aura e o banco privado...')
        finally:
            server.close()
    finally:
        shutdown_managed(mysql)
        if mutex:
            kernel.CloseHandle(mutex)


if __name__ == '__main__':
    try:
        main()
    except Exception as exc:
        print('Não foi possível iniciar: ' + str(exc))
        sys.exit(1)
