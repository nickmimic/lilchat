#!/usr/bin/env python3
"""lilchat server: serves chat.html and proxies LLM / SearXNG / URL-fetch requests.

Everything the browser needs lives on one port, so the UI is same-origin whether
it is opened on this Mac or from another device on the LAN.
"""
from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler
import urllib.request, urllib.parse, urllib.error, html, json, re, os

PORT    = 8889
SEARXNG = 'http://localhost:8888'   # your SearXNG instance
LLM     = 'http://localhost:8086'   # your OpenAI-compatible model server

HERE      = os.path.dirname(os.path.abspath(__file__))
CHAT_HTML = os.path.join(HERE, 'chat.html')

BROWSER_HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
    'Accept-Language': 'en-US,en;q=0.5',
}


class Handler(BaseHTTPRequestHandler):
    protocol_version = 'HTTP/1.1'

    # ── helpers ──────────────────────────────────────────────────────────
    def _send(self, status, body, ctype='text/plain; charset=utf-8'):
        if isinstance(body, str):
            body = body.encode('utf-8')
        self.send_response(status)
        self.send_header('Content-Type', ctype)
        self.send_header('Content-Length', str(len(body)))
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        self.wfile.write(body)

    def _json_err(self, status, msg):
        self._send(status, json.dumps({'error': msg}), 'application/json')

    # ── routes ───────────────────────────────────────────────────────────
    def do_OPTIONS(self):
        self.send_response(204)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type, Authorization')
        self.send_header('Content-Length', '0')
        self.end_headers()

    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        if parsed.path in ('/', '/chat.html'):
            return self.serve_chat()
        if parsed.path == '/fetch':
            return self.fetch_url(parsed)
        if parsed.path == '/search':
            return self.search(parsed)
        if parsed.path.startswith('/v1/'):
            return self.proxy_llm(parsed, 'GET')
        self._send(404, 'not found')

    def do_POST(self):
        parsed = urllib.parse.urlparse(self.path)
        if parsed.path.startswith('/v1/'):
            return self.proxy_llm(parsed, 'POST')
        self._send(404, 'not found')

    # ── handlers ─────────────────────────────────────────────────────────
    def serve_chat(self):
        try:
            with open(CHAT_HTML, 'rb') as f:
                self._send(200, f.read(), 'text/html; charset=utf-8')
        except FileNotFoundError:
            self._send(404, 'chat.html not found next to proxy.py')

    def fetch_url(self, parsed):
        target = urllib.parse.parse_qs(parsed.query).get('url', [None])[0]
        if not target:
            return self._send(400, 'missing url')
        try:
            req = urllib.request.Request(target, headers=BROWSER_HEADERS)
            with urllib.request.urlopen(req, timeout=10) as r:
                raw = r.read().decode('utf-8', errors='ignore')
            for tag in ('script', 'style', 'nav', 'footer', 'header'):
                raw = re.sub(rf'<{tag}[\s\S]*?</{tag}>', '', raw, flags=re.I)
            raw = re.sub(r'<[^>]+>', ' ', raw)
            text = re.sub(r'\s+', ' ', html.unescape(raw)).strip()[:6000]
            self._send(200, text)
        except Exception as e:
            self._send(502, f'Fetch failed: {e}')

    def search(self, parsed):
        try:
            with urllib.request.urlopen(SEARXNG + self.path, timeout=15) as r:
                self._send(200, r.read(), 'application/json')
        except Exception:
            self._json_err(502, 'SearXNG not reachable. Is it running on port 8888?')

    def proxy_llm(self, parsed, method):
        url = LLM + parsed.path + ('?' + parsed.query if parsed.query else '')
        length = int(self.headers.get('Content-Length') or 0)
        body = self.rfile.read(length) if length else None
        req = urllib.request.Request(url, data=body, method=method)
        for h in ('Content-Type', 'Authorization', 'Accept'):
            if self.headers.get(h):
                req.add_header(h, self.headers[h])
        try:
            resp = urllib.request.urlopen(req, timeout=600)
        except urllib.error.HTTPError as e:
            # pass the model server's own error body straight through
            return self._send(e.code, e.read() or str(e).encode(),
                              e.headers.get('Content-Type', 'application/json'))
        except Exception as e:
            return self._json_err(502, f'LLM unreachable at {LLM}: {e}')

        with resp:
            self.send_response(resp.status)
            for k, v in resp.headers.items():
                if k.lower() not in ('transfer-encoding', 'connection', 'content-length', 'keep-alive'):
                    self.send_header(k, v)
            self.send_header('Access-Control-Allow-Origin', '*')
            self.send_header('Connection', 'close')
            self.end_headers()
            # small chunks + flush so streamed tokens arrive as they are generated
            while True:
                chunk = resp.read(1024)
                if not chunk:
                    break
                try:
                    self.wfile.write(chunk)
                    self.wfile.flush()
                except (BrokenPipeError, ConnectionResetError):
                    break  # browser closed the tab / stopped generation

    def log_message(self, *a):
        pass


if __name__ == '__main__':
    print(f'lilchat  →  http://localhost:{PORT}/')
    print(f'  LLM     : {LLM}')
    print(f'  SearXNG : {SEARXNG}')
    try:
        ThreadingHTTPServer(('', PORT), Handler).serve_forever()
    except KeyboardInterrupt:
        pass
