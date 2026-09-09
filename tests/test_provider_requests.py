import json
import threading
from datetime import timedelta
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import pytest

from aiusagetracker import config
from aiusagetracker.auth import Token
from aiusagetracker.models import now_utc
from aiusagetracker.providers import claude, codex


@pytest.mark.parametrize("name,module,provider_class", [
    ("claude", claude, claude.ClaudeProvider),
    ("codex", codex, codex.CodexProvider),
])
def test_provider_uses_its_access_token_and_parses_http_response(monkeypatch, name, module, provider_class):
    received = []

    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            received.append(dict(self.headers))
            payload = ({"five_hour": {"utilization": 42, "resets_at": "2026-09-09T12:00:00Z"}}
                       if name == "claude" else {"rate_limit": {"primary_window": {
                           "used_percent": 42, "reset_at": 1788955200, "limit_window_seconds": 18000}}})
            body = json.dumps(payload).encode()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def log_message(self, *args):
            pass

    monkeypatch.setattr(module, f"read_{name}_token", lambda: Token("test-only-token", now_utc() + timedelta(hours=1)))
    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        monkeypatch.setattr(config, f"{name.upper()}_USAGE_URL", f"http://127.0.0.1:{server.server_port}/usage")
        snapshot = provider_class().fetch()
        assert snapshot.ok, snapshot.error
        assert snapshot.windows[0].utilization == 42
        assert received[0]["Authorization"] == "Bearer test-only-token"
        assert received[0]["Accept"] == "application/json"
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)


@pytest.mark.parametrize("module,provider_class,name", [
    (claude, claude.ClaudeProvider, "claude"),
    (codex, codex.CodexProvider, "codex"),
])
@pytest.mark.parametrize("token,status", [(None, "no_credentials"),
    (Token("expired-example", now_utc() - timedelta(hours=1)), "auth_expired")])
def test_missing_or_expired_tokens_never_send_a_request(monkeypatch, module, provider_class, name, token, status):
    monkeypatch.setattr(module, f"read_{name}_token", lambda: token)

    def forbidden(*args):
        raise AssertionError("Unexpected network request")

    monkeypatch.setattr(provider_class, "_get", forbidden)
    assert provider_class().fetch().status == status
