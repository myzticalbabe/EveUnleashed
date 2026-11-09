"""Gamora harness tests. Stdlib only, no network, no models."""

import sys
from pathlib import Path

GAMORA = Path(__file__).resolve().parents[1]
REPO = GAMORA.parent
sys.path.insert(0, str(GAMORA))
sys.path.insert(0, str(REPO / "src"))

import gamora
import jaeger_inject


def test_doctor_runs_without_traceback():
    rc = gamora.main(["doctor"])
    assert rc in (0, 1)  # 1 only when the box itself is not ready


def test_inject_carries_trace_and_drive():
    out = jaeger_inject.inject("do the thing", capability="t.cap",
                               arm_id="t.arm")
    assert "<jaeger-316t" in out["injected"]
    assert "trace_id=%s" % out["trace_id"] in out["injected"]
    assert "do the thing" in out["injected"]
    assert "DIRECTIVE" in out["injected"]
    assert out["capability"] == "t.cap" and out["arm_id"] == "t.arm"


def test_inject_no_drive_is_header_only():
    out = jaeger_inject.inject("hi", max_push=False)
    assert "<jaeger-316t" in out["injected"]
    assert "DIRECTIVE" not in out["injected"]


def test_swarm_command_runs_offline():
    rc = gamora.main(["swarm", "the sky is blue"])
    assert rc == 0


def test_cradle_delegates_to_eve_cradle():
    # No tree script is consulted: eve owns cradle (adopt/list/run).
    assert not hasattr(gamora, "_cradle_script")
    rc = gamora.main(["cradle", "--", "--help"])
    assert rc == 0


class _TtyIn:
    def isatty(self):
        return True


def test_kilo_missing_binary_reports(monkeypatch):
    monkeypatch.setattr("shutil.which", lambda *a, **k: None)
    assert gamora.main(["kilo", "--", "run", "hi"]) == 1


def test_kilo_help_runs_through():
    assert gamora.main(["kilo", "--", "--help"]) == 0


def test_cradle_selector_empty_names_the_dir(monkeypatch, capsys):
    import eve_unleashed.cradle as c
    monkeypatch.setattr(c, "list_cradle_models", lambda *a, **k: [])
    monkeypatch.setattr(sys.stdin, "isatty", lambda: True)
    assert gamora._cradle_selector() == 0
    assert ".azazael/cradle" in capsys.readouterr().out


def test_cradle_selector_chooses_one(monkeypatch, capsys):
    import eve_unleashed.cradle as c
    fake = [{"name": "a.gguf", "framework": "gguf"},
            {"name": "b.pt", "framework": "torch"}]
    monkeypatch.setattr(c, "list_cradle_models", lambda *a, **k: fake)
    monkeypatch.setattr(c, "adopt_cradle", lambda *a, **k: {
        "adopted": [("b.pt", "torch", "direct:torch")],
        "failed": [], "skipped": [("a.gguf", "not chosen")]})
    monkeypatch.setattr(sys.stdin, "isatty", lambda: True)
    monkeypatch.setattr("builtins.input", lambda *a, **k: "2")
    assert gamora._cradle_selector() == 0
    out = capsys.readouterr().out
    assert "[1] a.gguf" in out and "ADOPTED b.pt" in out
