"""Private loopback-only work manager. Run: python3 admin_server.py [port]."""
import base64
import hmac
import json
import os
import re
import secrets
import sys
import tempfile
import threading
import uuid
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlsplit

BASE = Path(__file__).resolve().parent
DATA = BASE / 'mirror' / 'works.json'
PASSWORD_FILE = BASE / '.work-admin-password'
LOCK = threading.Lock()


def normalize_link(value):
    if not isinstance(value, str) or len(value) > 2048:
        raise ValueError('Paste a valid YouTube or Instagram link.')
    parsed = urlsplit(value.strip())
    if parsed.scheme != 'https' or parsed.username or parsed.password or parsed.port not in (None, 443):
        raise ValueError('Use an https YouTube or Instagram link.')
    host = (parsed.hostname or '').lower()
    parts = parsed.path.strip('/').split('/')
    if host in ('youtube.com', 'www.youtube.com', 'm.youtube.com', 'youtu.be', 'www.youtu.be'):
        video = ''
        if host.endswith('youtu.be') and len(parts) == 1:
            video = parts[0]
        elif parts == ['watch']:
            video = parse_qs(parsed.query).get('v', [''])[0]
        elif len(parts) == 2 and parts[0] in ('shorts', 'embed', 'live'):
            video = parts[1]
        if not re.fullmatch(r'[A-Za-z0-9_-]{11}', video):
            raise ValueError('Use a link to a specific YouTube video or Short.')
        return {'provider': 'youtube', 'url': f'https://www.youtube.com/watch?v={video}', 'embedUrl': f'https://www.youtube.com/embed/{video}', 'suggestedCategory': 'Reels' if parts[0] == 'shorts' else 'Youtube'}
    if host in ('instagram.com', 'www.instagram.com'):
        if len(parts) != 2 or parts[0] not in ('p', 'reel', 'reels', 'tv') or not re.fullmatch(r'[A-Za-z0-9_-]{5,64}', parts[1]):
            raise ValueError('Use an Instagram post or Reel link, not a profile or share link.')
        kind = 'reel' if parts[0] == 'reels' else parts[0]
        url = f'https://www.instagram.com/{kind}/{parts[1]}/'
        return {'provider': 'instagram', 'url': url, 'embedUrl': url + 'embed/', 'suggestedCategory': 'Reels'}
    raise ValueError('Only YouTube and Instagram links are supported.')


def read_works():
    return json.loads(DATA.read_text()) if DATA.exists() else []


def save_works(items):
    DATA.parent.mkdir(parents=True, exist_ok=True)
    fd, name = tempfile.mkstemp(dir=DATA.parent, prefix='.works-', suffix='.tmp')
    try:
        with os.fdopen(fd, 'w') as out:
            json.dump(items, out, indent=2)
            out.write('\n')
        os.replace(name, DATA)
    finally:
        if os.path.exists(name):
            os.unlink(name)


class AdminHandler(BaseHTTPRequestHandler):
    def log_message(self, *_):
        pass

    def reply(self, status, body, kind='application/json'):
        if kind == 'application/json':
            body = json.dumps(body).encode()
        self.send_response(status)
        self.send_header('Content-Type', kind)
        self.send_header('Content-Length', str(len(body)))
        self.send_header('Cache-Control', 'no-store')
        self.send_header('X-Content-Type-Options', 'nosniff')
        self.send_header('X-Frame-Options', 'DENY')
        self.send_header('Referrer-Policy', 'no-referrer')
        if status == 401:
            self.send_header('WWW-Authenticate', 'Basic realm="Multimudia work manager", charset="UTF-8"')
        self.end_headers()
        self.wfile.write(body)

    def authorized(self, mutation=False):
        allowed = {f'localhost:{self.server.server_port}', f'127.0.0.1:{self.server.server_port}'}
        if self.headers.get('Host') not in allowed:
            self.reply(403, {'error': 'Invalid host.'})
            return False
        if mutation and self.headers.get('Origin') not in {f'http://{host}' for host in allowed}:
            self.reply(403, {'error': 'Changes must come from the local work manager.'})
            return False
        try:
            scheme, encoded = self.headers.get('Authorization', '').split(' ', 1)
            credentials = base64.b64decode(encoded, validate=True).decode()
            valid = scheme.lower() == 'basic' and hmac.compare_digest(credentials, 'admin:' + self.server.password)
        except (ValueError, UnicodeError):
            valid = False
        if not valid:
            self.reply(401, {'error': 'Sign in with your local admin credentials.'})
        return valid

    def do_GET(self):
        if not self.authorized():
            return
        path = urlsplit(self.path).path
        if path == '/api/works':
            with LOCK:
                self.reply(200, read_works())
        elif path in ('/', '/admin.js', '/admin.css'):
            filename, kind = {'/': ('index.html', 'text/html; charset=utf-8'), '/admin.js': ('admin.js', 'text/javascript'), '/admin.css': ('admin.css', 'text/css')}[path]
            self.reply(200, (BASE / 'admin' / filename).read_bytes(), kind)
        else:
            self.reply(404, {'error': 'Not found.'})

    def do_POST(self):
        if not self.authorized(mutation=True):
            return
        try:
            length = int(self.headers.get('Content-Length', '0'))
            if not 0 < length <= 8192 or self.headers.get('Content-Type', '').split(';')[0] != 'application/json':
                raise ValueError('Expected a small JSON request.')
            data = json.loads(self.rfile.read(length))
            if not isinstance(data, dict):
                raise ValueError('Invalid request.')
            path = urlsplit(self.path).path
            with LOCK:
                items = read_works()
                if path == '/api/preview':
                    self.reply(200, normalize_link(data.get('url')))
                    return
                if path == '/api/works/delete':
                    found = any(item['id'] == data.get('id') for item in items)
                    if not found:
                        self.reply(404, {'error': 'Work not found.'})
                        return
                    items = [item for item in items if item['id'] != data['id']]
                elif path == '/api/works':
                    link = normalize_link(data.get('url'))
                    title = data.get('title', '')
                    category = data.get('category')
                    if not isinstance(title, str) or not 1 <= len(title.strip()) <= 120:
                        raise ValueError('Add a title of 1–120 characters.')
                    if category not in ('Reels', 'Youtube'):
                        raise ValueError('Choose Reels or Youtube.')
                    item_id = data.get('id') or str(uuid.uuid4())
                    if data.get('id') and not any(item['id'] == item_id for item in items):
                        self.reply(404, {'error': 'Work not found.'})
                        return
                    if any(item['url'] == link['url'] and item['id'] != item_id for item in items):
                        raise ValueError('This video is already in your work. Edit the existing entry instead.')
                    old = next((item for item in items if item['id'] == item_id), {})
                    link.pop('suggestedCategory')
                    entry = {**link, 'id': item_id, 'title': title.strip(), 'category': category, 'createdAt': old.get('createdAt', datetime.now(timezone.utc).isoformat())}
                    items = [entry if item['id'] == item_id else item for item in items] if old else [entry, *items]
                else:
                    self.reply(404, {'error': 'Not found.'})
                    return
                save_works(items)
            self.reply(200, items)
        except (ValueError, TypeError, KeyError):
            # Invalid requests never reach the filesystem as HTML or executable code.
            message = str(sys.exc_info()[1])
            self.reply(400, {'error': message or 'Invalid input.'})


def main():
    if not PASSWORD_FILE.exists():
        fd = os.open(PASSWORD_FILE, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        with os.fdopen(fd, 'w') as out:
            out.write(secrets.token_urlsafe(18) + '\n')
    password = PASSWORD_FILE.read_text().strip()
    if not DATA.exists():
        save_works([])
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8779
    server = ThreadingHTTPServer(('127.0.0.1', port), AdminHandler)
    server.password = password
    print(f'Work manager: http://localhost:{port} | username: admin | password file: {PASSWORD_FILE}', flush=True)
    server.serve_forever()


if __name__ == '__main__':
    main()
