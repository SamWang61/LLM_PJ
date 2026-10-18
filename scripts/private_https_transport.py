"""Requests cookie/redirect handling with one direct Node HTTPS request per pipe."""
import base64
from email.message import Message
import json
from pathlib import Path
import subprocess
from types import SimpleNamespace
from urllib.parse import urlparse

import requests
from requests.cookies import extract_cookies_to_jar

HOST = 'vibecart-acceptance-pr21-m44ncgz5ta-de.a.run.app'


class PrivateHTTPSAdapter(requests.adapters.BaseAdapter):
    def send(self, request, stream=False, timeout=None, verify=True, cert=None, proxies=None):
        url = urlparse(request.url)
        if (url.scheme != 'https' or url.hostname != HOST or url.port
                or url.username or url.password or verify is not True or cert
                or any((proxies or {}).values())):
            raise requests.RequestException('Private HTTPS transport scope mismatch')
        body = request.body
        if isinstance(body, str):
            body = body.encode('utf8')
        if body is not None and not isinstance(body, bytes):
            raise requests.RequestException('Unsupported private request body')
        payload = {'url': request.url, 'method': request.method,
                   'headers': dict(request.headers),
                   'body_base64': base64.b64encode(body).decode('ascii') if body is not None else None}
        try:
            result = subprocess.run(['node', str(Path(__file__).with_suffix('.cjs'))],
                input=json.dumps(payload), text=True, encoding='utf8', capture_output=True, timeout=65)
            data = json.loads(result.stdout)
            if result.returncode or 'error' in data:
                raise ValueError('transport')
            response = requests.Response()
            response.status_code = data['status']
            response._content = base64.b64decode(data['body_base64'])
            response._content_consumed = True
            response.url, response.request, response.encoding = request.url, request, 'utf8'
            message = Message()
            for name, value in data['headers']:
                message.add_header(name, value)
                response.headers[name] = value
            response.raw = SimpleNamespace(_original_response=SimpleNamespace(msg=message))
            extract_cookies_to_jar(response.cookies, request, response.raw)
            return response
        except (subprocess.SubprocessError, ValueError, KeyError, OSError):
            raise requests.ConnectionError('Private HTTPS pipe transport failed') from None

    def close(self):
        pass


def mount_private_transport(session):
    session.mount('https://', PrivateHTTPSAdapter())
