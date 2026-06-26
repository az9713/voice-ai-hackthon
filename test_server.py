"""Test the voice-adapter backend without any real keys.

Stubs the brain and the Vocal Bridge token call, then drives every route over
real HTTP. Verifies .env loading, routing, session handling, and error guards.

    python test_server.py
"""
import json
import os
import threading
import urllib.request
import urllib.error
from http.server import HTTPServer

# Set keys before importing server so the route guards pass.
os.environ["ANTHROPIC_API_KEY"] = "test-key"
os.environ["VOCAL_BRIDGE_API_KEY"] = "vb_test"

import server


def call(method, path, payload=None, port=5099):
    data = json.dumps(payload).encode() if payload is not None else None
    req = urllib.request.Request(f"http://localhost:{port}{path}", data=data, method=method,
                                 headers={"Content-Type": "application/json"})
    try:
        r = urllib.request.urlopen(req)
        return r.status, r.read()
    except urllib.error.HTTPError as e:
        return e.code, e.read()


def test_env_loader(tmp=".env.servertest"):
    open(tmp, "w").write('FOO_TEST="bar"\n# comment\nBAZ_TEST=qux\n')
    try:
        server.load_env(tmp)
        assert os.environ.get("FOO_TEST") == "bar"
        assert os.environ.get("BAZ_TEST") == "qux"
    finally:
        os.remove(tmp)


def main():
    test_env_loader()

    # Stub the brain (module-qualified call in server -> patch here works).
    server.agent_brain.handle_query = lambda q, h: (f"echo:{q}", h + [{"role": "assistant", "content": "x"}], ["get_booking"])
    # Stub the Vocal Bridge token proxy (don't hit the network).
    server.requests.post = lambda *a, **k: type("R", (), {"status_code": 200, "text": "{}",
                                                          "json": lambda self: {"token": "fake", "livekit_url": "wss://x", "room_name": "r"}})()

    srv = HTTPServer(("127.0.0.1", 5099), server.Handler)
    threading.Thread(target=srv.serve_forever, daemon=True).start()

    # /api/brain threads history per session
    s, body = call("POST", "/api/brain", {"query": "hi", "session": "s1"})
    j = json.loads(body)
    assert s == 200 and j["response"] == "echo:hi" and j["tools"] == ["get_booking"], (s, j)
    assert server.SESSIONS["s1"], "session history not stored"

    # /api/voice-token proxies and returns the token JSON
    s, body = call("POST", "/api/voice-token")
    assert s == 200 and json.loads(body)["token"] == "fake", (s, body)

    # unknown route -> 404
    s, _ = call("GET", "/nope")
    assert s == 404, s

    srv.shutdown()
    print("server tests ok: .env loader, /api/brain (session-threaded), /api/voice-token proxy, 404")


if __name__ == "__main__":
    main()
