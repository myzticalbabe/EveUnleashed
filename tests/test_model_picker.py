"""Tests for eve_unleashed.model_picker (stdlib only, no network beyond localhost)."""

import json
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer

import pytest

from eve_unleashed import model_picker as mp


def test_entry_id():
    assert mp.entry_id({"provider": "kilo", "model": "kilo/x"}) == "kilo/kilo/x"


def test_embed_filter():
    assert mp._is_embed("mxbai-embed-large")
    assert not mp._is_embed("tiny:1b")


def test_custom_add_remove_roundtrip(tmp_path, monkeypatch):
    monkeypatch.setattr(mp, "PROVIDERS_FILE", tmp_path / "p.json")
    monkeypatch.setattr(mp, "SELECTION_FILE", tmp_path / "s.json")
    e = mp.add_custom("lab", "http://192.168.1.9:8080", "tiny", "")
    assert e["name"] == "lab"
    assert mp.load_customs()[0]["base"] == "http://192.168.1.9:8080"
    assert mp.remove_custom("lab") is True
    assert mp.remove_custom("lab") is False


def test_selection_roundtrip(tmp_path, monkeypatch):
    monkeypatch.setattr(mp, "SELECTION_FILE", tmp_path / "s.json")
    assert mp.load_selection() is None
    sel = mp.save_selection(
        {"provider": "kilo", "model": "kilo/x", "kind": "agent", "agent": "kilo"}
    )
    assert mp.load_selection()["model"] == "kilo/x"
    assert mp.current_id() == "kilo/kilo/x"
    assert sel["kind"] == "agent"


class _Stub(BaseHTTPRequestHandler):
    def _send(self, obj):
        body = json.dumps(obj).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        self._send({"data": [{"id": "stub-model"}, {"id": "bge-embed"}]})

    def log_message(self, *a):
        pass


def test_discover_finds_server_not_embeds(monkeypatch):
    srv = HTTPServer(("127.0.0.1", 0), _Stub)
    port = srv.server_address[1]
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    try:
        monkeypatch.setattr(mp, "DEFAULT_PORTS", (port,))
        found = [
            e
            for e in mp.discover()
            if e["kind"] == "server"
            and e.get("base", "").endswith(":{:d}/v1".format(port))
        ]
    finally:
        srv.shutdown()
    assert [e["model"] for e in found] == ["stub-model"]


def test_discover_agents_lists_kilo_when_present():
    import shutil

    if not shutil.which("kilo"):
        pytest.skip("kilo CLI not installed")
    entries = mp.discover_agents()
    assert entries, "kilo installed but no agent entries discovered"
    assert all(e["kind"] == "agent" for e in entries)
    # kilo should be present among providers (opencode may also be present)
    providers = {e["provider"] for e in entries}
    assert "kilo" in providers, f"kilo provider not found; got: {providers}"


def test_run_agent_reports_signin_cleanly():
    import shutil

    if not shutil.which("kilo"):
        pytest.skip("kilo CLI not installed")
    out = mp.run_agent(
        "kilo",
        "kilo/~deepseek/deepseek-flash-latest",
        "reply with exactly: PICKER_TEST_OK",
        timeout=120.0,
    )
    assert out["status"] == "error"
    # kilo may return "sign in" or "add credits" depending on auth state
    err = out["error"].lower()
    assert "sign in" in err or "add credits" in err or "auth" in err
