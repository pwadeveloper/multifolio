"""Isolated storage and HTTP checks; never modifies portfolio entries."""
import base64
import http.client
import json
from pathlib import Path
import sys
import tempfile
import threading
import unittest
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import admin_server as admin

class AdminTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory()
        admin.DATA = Path(cls.temp.name) / 'works.json'
        cls.server = admin.ThreadingHTTPServer(('127.0.0.1', 0), admin.AdminHandler)
        cls.server.password = 'test-password'
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown(); cls.server.server_close(); cls.thread.join(); cls.temp.cleanup()

    def request(self, method, path, body=None, auth=True, origin=True, host=None):
        port = self.server.server_port
        headers = {'Host': host or f'localhost:{port}'}
        if auth: headers['Authorization'] = 'Basic ' + base64.b64encode(b'admin:test-password').decode()
        if origin: headers['Origin'] = f'http://localhost:{port}'
        if body is not None: headers['Content-Type'] = 'application/json'
        conn = http.client.HTTPConnection('127.0.0.1', port)
        conn.request(method, path, json.dumps(body) if body is not None else None, headers)
        response = conn.getresponse(); raw = response.read(); status = response.status; conn.close()
        return status, json.loads(raw)

    def test_auth_and_origin(self):
        self.assertEqual(self.request('GET','/api/works',auth=False)[0],401)
        self.assertEqual(self.request('GET','/api/works',host='evil.example')[0],403)
        self.assertEqual(self.request('POST','/api/works',{},origin=False)[0],403)
        self.assertEqual(self.request('GET','/.work-admin-password')[0],404)

    def test_link_validation(self):
        for url in ['https://youtu.be/dQw4w9WgXcQ?t=1','https://www.youtube.com/watch?v=dQw4w9WgXcQ','https://youtube.com/shorts/dQw4w9WgXcQ']:
            self.assertEqual(admin.normalize_link(url)['embedUrl'],'https://www.youtube.com/embed/dQw4w9WgXcQ')
        self.assertEqual(admin.normalize_link('https://www.instagram.com/reel/ABC_def123/?igsh=tracking')['embedUrl'],'https://www.instagram.com/reel/ABC_def123/embed/')
        for url in ['javascript:alert(1)','https://youtube.com.evil.test/watch?v=dQw4w9WgXcQ','https://www.instagram.com/someuser/','https://youtube.com/watch?v=bad','https://localhost/admin','https://user:pass@youtube.com/watch?v=dQw4w9WgXcQ']:
            with self.assertRaises(ValueError): admin.normalize_link(url)

    def test_crud_persistence_and_duplicate(self):
        item = {'title':'Example work','category':'Reels','url':'https://youtu.be/dQw4w9WgXcQ'}
        status, rows = self.request('POST','/api/works',item)
        self.assertEqual(status,200); self.assertEqual(len(rows),1)
        self.assertEqual(json.loads(admin.DATA.read_text()),rows)
        self.assertEqual(self.request('POST','/api/works',item)[0],400)
        item.update(id=rows[0]['id'],title='Updated work',category='Youtube')
        status, rows = self.request('POST','/api/works',item)
        self.assertEqual(status,200); self.assertEqual(rows[0]['title'],'Updated work')
        self.assertEqual(rows[0]['category'],'Youtube')
        status, rows = self.request('POST','/api/works/delete',{'id':item['id']})
        self.assertEqual((status,rows),(200,[]))
        self.assertEqual(self.request('POST','/api/works/delete',{'id':item['id']})[0],404)

if __name__ == '__main__': unittest.main()
