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


def test_cradle_prefers_tree_then_installed_data(tmp_path, monkeypatch):
    assert gamora._cradle_script() == gamora.REPO / "Project_CRADLE" / "cradle.py"
    fake_prefix = tmp_path / "prefix"
    (fake_prefix / "gamora_data").mkdir(parents=True)
    shipped = fake_prefix / "gamora_data" / "cradle.py"
    shipped.write_text("# shipped cradle\n")
    monkeypatch.setattr(sys, "prefix", str(fake_prefix))
    monkeypatch.setattr(gamora, "REPO", tmp_path / "empty-tree")
    assert gamora._cradle_script() == shipped
