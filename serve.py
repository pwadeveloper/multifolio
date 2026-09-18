#!/usr/bin/env python3
"""Serve the dejiajetomobi.com mirror locally.

    python3 serve.py [port]     # default 8777

Handles the things a plain `http.server` gets wrong for this site:
  * .rsc payloads need Content-Type: text/x-component (React Server Components)
  * ?_rsc=... query strings must be ignored when resolving files
  * extensionless routes (/design) map to /design/index.html
  * the homepage RSC lives at /.rsc
"""
import os, sys, posixpath, urllib.parse
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "mirror")

class H(SimpleHTTPRequestHandler):
    def __init__(self, *a, **kw):
        super().__init__(*a, directory=ROOT, **kw)

    def do_GET(self):
        # The GA <script> tag is stripped from the HTML, but the RSC payload still
        # carries the URL (blanking it breaks hydration). Serve an inert stub so the
        # mirror neither 404s nor sends pageviews to the live analytics property.
        if self.path.split("?")[0] in ("/gtag/js", "/gtag/js/"):
            body = b"window.dataLayer=window.dataLayer||[];\n"
            self.send_response(200)
            self.send_header("Content-Type", "application/javascript")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return
        return super().do_GET()

    def translate_path(self, path):
        path = urllib.parse.urlsplit(path).path          # drop ?_rsc=...
        path = urllib.parse.unquote(path)
        parts = [p for p in path.split("/") if p not in ("", ".", "..")]
        fs = os.path.join(ROOT, *parts)
        if os.path.isdir(fs):
            idx = os.path.join(fs, "index.html")
            if os.path.exists(idx):
                return idx
        if path.endswith("/.rsc") or path == "/.rsc":
            return os.path.join(ROOT, ".rsc")
        return fs

    def guess_type(self, path):
        if path.endswith(".rsc"):
            return "text/x-component; charset=utf-8"
        if path.endswith(".webmanifest"):
            return "application/manifest+json"
        return super().guess_type(path)

    def end_headers(self):
        self.send_header("Cache-Control", "no-store")
        super().end_headers()

    def log_message(self, fmt, *args):
        pass

if __name__ == "__main__":
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8777
    print(f"serving mirror at http://localhost:{port}  (ctrl-c to stop)")
    ThreadingHTTPServer(("127.0.0.1", port), H).serve_forever()
