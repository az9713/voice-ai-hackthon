"""Voice adapter backend: serves the page, mints Vocal Bridge tokens, runs the brain.

Keys come from .env (loaded below). Stdlib only — no Flask/dotenv to install.

    cp .env.example .env   # then fill in ANTHROPIC_API_KEY and VOCAL_BRIDGE_API_KEY
    python mock_sabre.py   # terminal 1
    python server.py       # terminal 2, then open http://localhost:5000

Routes:
  GET  /                -> voice.html (the browser voice client)
  POST /api/voice-token -> proxies Vocal Bridge /api/v1/token (keeps your vb_ key server-side)
  POST /api/brain       -> {query, session} -> agent_brain.handle_query -> {response, tools}
"""
import json
import os
from http.server import BaseHTTPRequestHandler, HTTPServer

import requests
import agent_brain                 # importing this loads .env (agent_brain.load_env runs at import)
from agent_brain import load_env   # re-exported for tests / convenience

os.environ.setdefault("SABRE_BASE", "http://localhost:8080")
VB_URL = os.environ.get("VOCAL_BRIDGE_URL", "https://vocalbridgeai.com")
HERE = os.path.dirname(os.path.abspath(__file__))
SESSIONS = {}  # session_id -> conversation history. ponytail: in-memory; fine for local dev


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def _json(self, code, obj):
        body = json.dumps(obj).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _body(self):
        n = int(self.headers.get("Content-Length", 0))
        try:
            return json.loads(self.rfile.read(n)) if n else {}
        except ValueError:
            return {}

    def do_GET(self):
        if self.path in ("/", "/voice.html"):
            try:
                data = open(os.path.join(HERE, "voice.html"), "rb").read()
            except FileNotFoundError:
                return self._json(404, {"error": "voice.html not found"})
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)
            return
        self._json(404, {"error": "not found"})

    def do_POST(self):
        if self.path == "/api/voice-token":
            key = os.environ.get("VOCAL_BRIDGE_API_KEY")
            if not key:
                return self._json(500, {"error": "VOCAL_BRIDGE_API_KEY not set in .env"})
            r = requests.post(f"{VB_URL}/api/v1/token",
                              headers={"X-API-Key": key, "Content-Type": "application/json"},
                              json={"participant_name": "web-user"}, timeout=20)
            return self._json(r.status_code, r.json() if r.text else {})

        if self.path == "/api/brain":
            if not os.environ.get("ANTHROPIC_API_KEY"):
                return self._json(500, {"error": "ANTHROPIC_API_KEY not set in .env"})
            b = self._body()
            sid = b.get("session", "default")
            reply, history, tools = agent_brain.handle_query(b.get("query", ""), SESSIONS.get(sid, []))
            SESSIONS[sid] = history
            return self._json(200, {"response": reply, "tools": tools})

        self._json(404, {"error": "not found"})


def serve(port=5000):
    print(f"voice adapter backend on http://localhost:{port}")
    HTTPServer(("127.0.0.1", port), Handler).serve_forever()


if __name__ == "__main__":
    serve()
