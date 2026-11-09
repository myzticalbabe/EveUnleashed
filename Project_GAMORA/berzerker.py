"""Gamora Berzerker A.I.O. -- native mind + STEM coding coach for girls.

WHAT THIS IS
------------
The Colosseum's mind (docs/COLOSSEUM_*.md) is the Berzerker A-I-O: 23 named
processes across 3 strata (conscious / subconscious / unconscious), all live
in cognition.PROCESSES with loci in eve_unleashed/. This module adopts that
mind NATIVELY into Gamora's cliT -- stdlib only, no models, no network -- and
turns it into a coding agent for STEM girls: patient, exact, receipted.

ENVIRONMENT SURVEY (ideas adopted natively)
-------------------------------------------
- Windows host (dev pillar): Eve cli debunk/factcheck/verify, swarm_oracle
  bounded pool (shutdown wait=False, 8 workers max), live_log receipts,
  one Jaeger span per delegation (recorded, never raised).
- WSL Ubuntu (gcc/go/node, oneAPI/CUDA): prefer real toolchains when
  present; berzerker only ADVISES (shutil.which probes, never executes
  untrusted code). Native kernels stay optional.
- Kali (offensive surface, docker running): defensive stance -- intuition
  names a wall, never defeats one; unknown hosts stay unknown; every
  failure is a named lesson, not a traceback.
- G: archive (52 exes, source-of-truth): shippable-artifact idea from
  MellifluousML -- digest over content (sha256), tamper refusal by name.
- Ollama/LM Studio + Colosseum rule: no model, no answer. The coach
  never invents an answer; offline-first scaffolds + try-it prompts.
- Standalone (Nuitka onefile): zero third-party wheels; this file imports
  eve parts LAZILY and degrades to a named message.

MellifluousML rule: stdlib only. Every subsystem import is lazy and any
missing part is a report, never a traceback.
"""

from __future__ import annotations

import hashlib
import json
import shutil
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent

COACH_LEVELS = ("spark", "builder", "pilot")
COACH_LANGS = ("python", "javascript", "go", "rust")

_STARTER = {
    "python": 'name = input("What should we call you? ")\nprint("Hello, " + name + "! You ran Python.")\n',
    "javascript": 'const name = prompt("What should we call you?");\nconsole.log("Hello, " + name + "! You ran JavaScript.");\n',
    "go": 'package main\n\nimport "fmt"\n\nfunc main() {\n\tfmt.Println("Hello! You ran Go.")\n}\n',
    "rust": 'fn main() {\n\tprintln!("Hello! You ran Rust.");\n}\n',
}

_TOOL_HINT = {
    "python": ("python", "the 316t interpreter beside this file"),
    "javascript": ("node", "node --check"),
    "go": ("go", "go vet / go run"),
    "rust": ("rustc", "rustc --crate-type lib"),
}


def _src_on_path():
    src = str(REPO / "src")
    if src not in sys.path:
        sys.path.insert(0, src)
    return src


def audit():
    """Berzerker census: 23 processes, 3 strata, 0 hidden gaps."""
    _src_on_path()
    try:
        from eve_unleashed import cognition as _c
    except Exception as e:
        return {"ok": False, "reason": "cognition unavailable (%s)" % e}
    rep = _c.audit()
    by_stratum = {}
    for r in rep["processes"]:
        by_stratum.setdefault(r["stratum"], []).append(r["name"])
    return {"ok": True, "total": rep["total"], "used": rep["used"],
            "declared": rep["declared"], "absent": rep["absent"],
            "strata": {k: sorted(v) for k, v in by_stratum.items()},
            "gaps": rep["gaps"],
            "note": "gaps are named plans, never hidden absences"}


def mind(request):
    """One request across the three strata: parse, recall, record."""
    _src_on_path()
    try:
        from eve_unleashed import cognition as _c
    except Exception as e:
        return {"ok": False, "reason": "cognition unavailable (%s)" % e}
    request = str(request or "").strip()[:500]
    if not request:
        return {"ok": False, "reason": "nothing to think about: empty request"}
    try:
        nx = _c.nexus(request)
    except Exception as e:
        return {"ok": False, "reason": "nexus unavailable (%s)" % e}
    paradigms = {}
    for s in ("conscious", "subconscious", "unconscious"):
        try:
            paradigms[s] = _c.paradigm(s)["members"]
        except Exception:
            paradigms[s] = []
    return {"ok": True, "request": request, "nexus": nx,
            "paradigms": paradigms}


def _debunk_notes(problem):
    """Native Rock throw: take the statement apart with its own words."""
    _src_on_path()
    try:
        from eve_unleashed.debunk import debunk_claim as _d
    except Exception as e:
        return {"available": False, "reason": "debunk unavailable (%s)" % e}
    try:
        d = _d(problem)
    except Exception as e:
        return {"available": False, "reason": "debunk failed (%s)" % e}
    return {"available": True, "verdict": d.get("verdict"),
            "propositions": d.get("propositions", [])[:5],
            "flags": d.get("fallacy_flags", [])[:5]}


def _toolchain(lang):
    tool, _hint = _TOOL_HINT.get(lang, ("python", ""))
    found = shutil.which(tool)
    return {"tool": tool, "present": bool(found),
            "path": found or "not on PATH -- the scaffold below still runs "
                    "once %s is installed" % tool}


def code_coach(problem, language="python", level="spark", name=None):
    """STEM coding coach for girls: scaffold first, answer never invented.

    The coach debunks the assignment (Rock), checks what toolchain is
    present (advisory only), and returns a starter + 3 try-it steps at
    the girl's level. No model, no network, deterministic.
    """
    language = str(language or "python").lower().strip()
    if language not in COACH_LANGS:
        return {"ok": False,
                "reason": "unknown language %r (known: %s)"
                          % (language, ", ".join(COACH_LANGS))}
    level = str(level or "spark").lower().strip()
    if level not in COACH_LEVELS:
        return {"ok": False,
                "reason": "unknown level %r (known: %s)"
                          % (level, ", ".join(COACH_LEVELS))}
    problem = _scrub(problem)
    if not problem:
        return {"ok": False, "reason": "tell me the assignment in one "
                                       "sentence, then we build it together"}
    if len(problem) > 1000:
        problem = problem[:1000]

    notes = _debunk_notes(problem)
    tools = _toolchain(language)
    digest = hashlib.sha256(
        ("%s|%s|%s" % (language, level, problem)).encode("utf-8")).hexdigest()

    if level == "spark":
        steps = ["Read the assignment aloud and circle the ONE thing it "
                 "asks the computer to do.",
                 "Type the starter below exactly, run it, and tell me what "
                 "it printed.",
                 "Change one word in the starter and predict the new "
                 "output before you run it again."]
    elif level == "builder":
        steps = ["Split the task into input, one small rule, and output -- "
                 "write the three as comments first.",
                 "Fill in the rule with the smallest true thing (one if, "
                 "one loop).",
                 "Run it on two examples: one normal, one weird. Keep the "
                 "weird one as your test."]
    else:
        steps = ["State the claim your program must keep true, then write "
                 "the check that would prove it false.",
                 "Build the smallest version that passes the check.",
                 "Write the lesson in one line: what broke, and what the "
                 "fix was. Lessons are the deliverable."]

    starter = _STARTER[language]
    lines = [
        "Hey builder -- I am Berzerker, your coding coach. We solve this "
        "together, step by step.",
        "",
        "Your assignment, in its own words: %s" % problem,
    ]
    if notes.get("available"):
        lines.append("Rock throw (debunk): %s." % notes.get("verdict"))
        for p in notes.get("propositions", [])[:3]:
            lines.append("  - checkable piece: %s" % p)
        for f in notes.get("flags", [])[:3]:
            lines.append("  - watch out for: %s" % f)
    else:
        lines.append("Rock throw: %s." % notes.get("reason"))
    lines += [
        "Toolchain: %s %s." % (tools["tool"],
                               "found" if tools["present"]
                               else "not found yet -- " + tools["path"]),
        "",
        "Starter (%s, level %s) -- type it, run it, own it:" % (language,
                                                                level),
        starter.rstrip(),
        "",
        "Your 3 steps:",
    ]
    for i, s in enumerate(steps, 1):
        lines.append("  %d. %s" % (i, s))
    if level in ("builder", "pilot"):
        lines.append("")
        lines.append("Your weird tests (keep the weird one):")
        for w in weird_tests(language).get("weird", []):
            lines.append("  - %s" % w)
    if name:
        sug = suggest_level(name)
        lines.append("")
        lines.append("Level: steady at %s -- %s." % (level,
                                                     sug["reason"]))
    lines += [
        "",
        "Receipt: sha256 %s. No answer was invented; every line above "
        "runs offline." % digest[:16],
    ]
    return {"ok": True, "language": language, "level": level,
            "problem": problem, "debunk": notes, "toolchain": tools,
            "starter": starter, "steps": steps,
            "digest": digest,
            "response": "\n".join(lines)}


def _scrub(text):
    """Guardrail: the coach needs a first name, never contact details."""
    import re
    text = re.sub(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}",
                  "[redacted-email]", str(text or ""))
    text = re.sub(r"\d[\d\-\.\s]{6,}\d", "[redacted-number]", text)
    return text.strip()[:1000]


def dream(host=None):
    """Recalibration table: hit-rate per rung + per-host answer rates."""
    _src_on_path()
    try:
        from eve_unleashed.intuition import dream as _dream
    except Exception as e:
        return {"ok": False, "reason": "dream unavailable (%s)" % e}
    try:
        rep = _dream()
    except Exception as e:
        return {"ok": False, "reason": "dream failed (%s)" % e}
    out = {"ok": True, "pairs": rep["pairs"],
           "hit_rate": rep["hit_rate"], "by_rung": rep["by_rung"]}
    if host:
        host = str(host).lower().strip()
        out["host"] = {host: rep["hosts"].get(host, {"fetches": 0})}
    else:
        out["hosts"] = rep["hosts"]
    return out


def inhibited(host, threshold=0.5):
    """Rungs that keep failing for this host and should be skipped."""
    _src_on_path()
    try:
        from eve_unleashed.intuition import inhibited_rungs as _inh
    except Exception as e:
        return {"ok": False, "reason": "inhibition unavailable (%s)" % e}
    try:
        rungs = _inh(host, threshold=float(threshold))
    except Exception as e:
        return {"ok": False, "reason": "inhibition failed (%s)" % e}
    return {"ok": True, "host": str(host or ""),
            "inhibited": sorted(rungs),
            "note": ("skip these rungs for this host" if rungs
                       else "nothing to skip -- the ladder stands")}


_WEIRD = {
    "python": ["empty input: just press Enter",
                 "a huge number: 10 ** 100",
                 "emoji: 'you did it! Hurrah.'"],
    "javascript": ["empty input: submit with nothing typed",
                     "a huge number: 10n ** 100n",
                     "emoji: 'you did it! Hurrah.'"],
    "go": ["empty input: an empty string",
             "a huge number: 1 << 100 (math/big)",
             "emoji: 'you did it! Hurrah.'"],
    "rust": ["empty input: an empty String",
               "a huge number: u128::MAX",
               "emoji: 'you did it! Hurrah.'"],
}


def weird_tests(language="python"):
    """The weird half of the pair: normal + weird, keep the weird one."""
    language = str(language or "python").lower().strip()
    if language not in COACH_LANGS:
        return {"ok": False, "reason": "unknown language %r" % language}
    return {"ok": True, "language": language,
            "weird": list(_WEIRD[language])}


def _ledger_path():
    home = Path.home() / ".azazael"
    try:
        home.mkdir(parents=True, exist_ok=True)
    except Exception:
        pass  # scanner:ignore silent_except_pass -- ledger dir is best-effort; record_completion reports unwritable below


def _ledger_read():
    try:
        return json.loads(_ledger_path().read_text(encoding="utf-8"))
    except Exception:
        return {}


def record_completion(name, level):
    """One finished session, tallied. Lessons are the deliverable."""
    name = str(name or "").strip().lower()[:40]
    if not name or level not in COACH_LEVELS:
        return {"ok": False, "reason": "need a name and a true level"}
    try:
        data = _ledger_read()
        cell = data.setdefault(name, {"spark": 0, "builder": 0,
                                      "pilot": 0})
        cell[level] = int(cell.get(level, 0)) + 1
        _ledger_path().write_text(json.dumps(data, indent=1),
                                  encoding="utf-8")
    except Exception as e:
        return {"ok": False, "reason": "ledger unwritable (%s)" % e}
    return {"ok": True, "name": name, "level": level,
            "suggests": suggest_level(name)["suggests"]}


def suggest_level(name):
    """Three finished sessions earn the next rung. Never assigned early."""
    name = str(name or "").strip().lower()[:40]
    counts = _ledger_read().get(name, {})
    for lvl, nxt in (("spark", "builder"), ("builder", "pilot")):
        if int(counts.get(lvl, 0)) >= 3 and not int(counts.get(nxt, 0)):
            return {"ok": True, "name": name, "suggests": nxt,
                    "reason": "%d %s sessions finished -- try %s"
                              % (counts[lvl], lvl, nxt)}
    cur = "spark"
    for lvl in ("pilot", "builder"):
        if int(counts.get(lvl, 0)):
            cur = lvl
            break
    return {"ok": True, "name": name, "suggests": cur,
            "reason": "steady at %s" % cur}


def as_jsonable(obj):
    try:
        json.dumps(obj)
        return obj
    except Exception:
        return {"note": "unserializable -- reported, not raised",
                "type": str(type(obj))}
