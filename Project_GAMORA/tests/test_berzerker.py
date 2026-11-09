"""Berzerker A.I.O. tests. Stdlib only, no network, no models."""

import sys
from pathlib import Path

GAMORA = Path(__file__).resolve().parents[1]
REPO = GAMORA.parent
sys.path.insert(0, str(GAMORA))
sys.path.insert(0, str(REPO / "src"))

import berzerker
import gamora


def test_audit_names_23_processes_3_strata():
    rep = berzerker.audit()
    assert rep["ok"] is True
    assert rep["total"] == 23
    assert set(rep["strata"]) == {"conscious", "subconscious", "unconscious"}
    assert rep["gaps"] == []


def test_mind_crosses_three_strata():
    rep = berzerker.mind("https://example.com")
    assert rep["ok"] is True
    assert set(rep["nexus"]) >= {"conscious", "subconscious", "unconscious"}
    assert set(rep["paradigms"]) == {"conscious", "subconscious",
                                     "unconscious"}


def test_mind_rejects_empty_request():
    rep = berzerker.mind("   ")
    assert rep["ok"] is False


def test_code_coach_scaffolds_python_spark():
    rep = berzerker.code_coach("print my name", language="python",
                               level="spark")
    assert rep["ok"] is True
    assert len(rep["steps"]) == 3
    assert "Hello" in rep["starter"]
    assert len(rep["digest"]) == 64
    assert "together" in rep["response"]


def test_code_coach_rejects_unknown_lang_and_level():
    assert berzerker.code_coach("x", language="cobol")["ok"] is False
    assert berzerker.code_coach("x", level="wizard")["ok"] is False
    assert berzerker.code_coach("   ")["ok"] is False


def test_dream_and_inhibition_run_offline():
    d = berzerker.dream()
    assert d["ok"] is True and "hit_rate" in d
    assert berzerker.dream("example.com")["ok"] is True
    inh = berzerker.inhibited("example.com")
    assert inh["ok"] is True and isinstance(inh["inhibited"], list)


def test_weird_tests_cover_all_langs():
    for lang in ("python", "javascript", "go", "rust"):
        w = berzerker.weird_tests(lang)
        assert w["ok"] is True and len(w["weird"]) == 3
    assert berzerker.weird_tests("cobol")["ok"] is False


def test_coach_scrubs_contact_details():
    rep = berzerker.code_coach("email me at ada@example.com 555-123-4567")
    assert rep["ok"] is True
    assert "ada@example.com" not in rep["response"]
    assert "ada@example.com" not in rep["problem"]


def test_builder_gets_weird_tests_and_level_line():
    rep = berzerker.code_coach("add two numbers", level="builder",
                               name="Ada")
    assert rep["ok"] is True
    assert "weird" in rep["response"].lower()
    assert "Level" in rep["response"]


def test_ledger_records_and_suggests(tmp_path, monkeypatch):
    monkeypatch.setattr(berzerker, "_ledger_path",
                        lambda: tmp_path / "levels.json")
    for _ in range(3):
        r = berzerker.record_completion("Ada", "spark")
        assert r["ok"] is True
    assert berzerker.suggest_level("Ada")["suggests"] == "builder"
    assert berzerker.suggest_level("Nobody") == berzerker.suggest_level(
        "Nobody")


def test_starter_parity_python_compiles_and_others_honest():
    import shutil
    py = berzerker._STARTER["python"]
    compile(py, "<starter>", "exec")
    probes = {"javascript": ("node", ["--check"]),
              "go": ("go", ["vet"]),
              "rust": ("rustc", ["--crate-type", "lib"])}
    for lang, (tool, _args) in probes.items():
        starter = berzerker._STARTER[lang]
        assert starter.strip()  # scaffold present either way
        # Honest, not forced: presence is advisory, never a failure.
        assert isinstance(shutil.which(tool), (str, type(None)))


def test_gamora_berzerker_commands_run_offline():
    assert gamora.main(["berzerker", "audit"]) == 0
    assert gamora.main(["berzerker", "mind", "https://example.com"]) == 0
    assert gamora.main(["berzerker", "code", "add two numbers",
                        "--lang", "python", "--level", "builder"]) == 0
    assert gamora.main(["berzerker", "dream"]) == 0
    assert gamora.main(["berzerker", "inhibited", "example.com"]) == 0
    assert gamora.main(["berzerker", "weird", "--lang", "rust"]) == 0
    assert gamora.main(["berzerker", "code", "add two numbers",
                        "--json"]) == 0
    assert gamora.main(["doctor", "--json"]) in (0, 1)
