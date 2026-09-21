"""Single-origin WSGI application for the loopback-only Windows edition."""
import json
import os
from pathlib import Path


def local_app(django_app, frontend, static_root, port, instance_id):
    from whitenoise import WhiteNoise
    def security_headers(headers, path, url):
        headers['Cache-Control'] = 'no-store'
        headers['X-Content-Type-Options'] = 'nosniff'
        headers['X-Frame-Options'] = 'DENY'
    assets = WhiteNoise(django_app, root=str(frontend), index_file=True, max_age=0,
                        add_headers_function=security_headers)
    assets.add_files(str(static_root), prefix='static/')
    hosts = {f'127.0.0.1:{port}', f'localhost:{port}'}

    def application(environ, start_response):
        if environ.get('HTTP_HOST', '').lower() not in hosts:
            start_response('400 Bad Request', [('Content-Type', 'text/plain')])
            return [b'Invalid local host']
        if environ.get('PATH_INFO') == '/__aura_health/':
            body = json.dumps({'application': 'Aura', 'instance': instance_id}).encode()
            start_response('200 OK', [('Content-Type', 'application/json'), ('Cache-Control', 'no-store')])
            return [body]
        return assets(environ, start_response)
    return application
