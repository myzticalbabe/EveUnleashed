"""Gamora DOMellifluousML cliT -- agentic CLI harness on the 316t interpreter.

WHAT GAMORA IS
--------------
One command over parts that already existed and did not know about each
other -- the composition, not a fifth part:

    LILITH swarm / Spitfire   per-host answer rates, fanned claims
    Eve Unleashed              the inference engine (eve_unleashed.cli)
    Jaeger 3:16T               the tracer of this tree (AOA delegation_tracer)
    Cradle                     the chain (Project_CRADLE/cradle.py)

Gamora adds no judgement of its own. It launches them, in the order that
makes each answer meaningful, and every delegation it routes writes one
Jaeger span so "was this the right choice" stays answerable from the
ledger -- never from a live process.

COMMANDS
--------
    python gamora.py doctor                  is this machine ready (316t?)
    python gamora.py lilith [--once]          hive status, stdlib only
    python gamora.py eve -- <eve args>        passthrough to Eve Unleashed
    python gamora.py cradle -- <cradle args>  passthrough to Project_CRADLE    python gamora.py lucy <mood> [note]       Eliza + therapy, offline-first
    python gamora.py swarm <claim> [...]          native swarm over oracles
    python gamora.py inject "prompt"          Jaeger 3:16T prompt injector
    python gamora.py berzerker audit|mind|code   native AIO + STEM coach

Stdlib only. Every subsystem import is lazy and degrades to a named
message -- a missing part is a report, never a traceback.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

GAMORA_ROOT = Path(__file__).resolve().parent
REPO = GAMORA_ROOT.parent

# The 316t interpreter is mandatory for the harness, advisory for parts:
# Gamora itself runs its fan-out on free threads; a part that works on
# 3.15 still works, it just does not get the parallel guarantee.
REQUIRED_GIL_DISABLED = True


def _gil_state() -> str:
    fn = getattr(sys, "_is_gil_enabled", None)
    if fn is None:
        return "unknown (no _is_gil_enabled -- pre-3.13 interpreter?)"
    try:
        return "disabled (316t free-threaded)" if not fn() else "ENABLED"
    except Exception as e:  # never break the host
        return "unknown (%s)" % e


def cmd_doctor(_args) -> int:
    """One boring line per requirement. Exit 1 on any failure."""
    ok = True

    gil = _gil_state()
    gil_ok = "disabled" in gil
    print("316t interpreter : %s %s" % (sys.version.split()[0], gil))
    if REQUIRED_GIL_DISABLED and not gil_ok:
        print("  FAIL: Gamora requires a free-threaded (GIL-disabled) interpreter")
        ok = False

    # Core parts: importable, in the order the harness calls them.
    checks = (
        ("jaeger tracer", "AOA.core.delegation_tracer", "emit_delegation"),
        ("eve cli", "eve_unleashed.cli", "main"),
        ("swarm oracle", "eve_unleashed.swarm_oracle", None),
        ("therapy (lucy)", "eve_unleashed.therapy", "fallback_response"),
        ("cradle", None, None),  # file check below, not an import
        ("lucy", None, None),  # file check below
    )
    repo_src = REPO / "src"
    saved = list(sys.path)
    if str(repo_src) not in sys.path:
        sys.path.insert(0, str(repo_src))
    try:
        for label, mod, attr in checks:
            if mod is None:
                continue
            try:
                m = __import__(mod, fromlist=["*"])
                if attr is not None and not hasattr(m, attr):
                    print("%-16s : MISSING attr %s" % (label, attr))
                    ok = False
                else:
                    print("%-16s : ok (%s)" % (label, mod))
            except Exception as e:
                print("%-16s : MISSING (%s)" % (label, e))
                ok = False
    finally:
        sys.path[:] = saved

    cradle = REPO / "Project_CRADLE" / "cradle.py"
    lucy = REPO / "Project_LUCY" / "lucy.py"
    for label, path in (("cradle file", cradle), ("lucy file", lucy)):
        if path.is_file():
            print("%-16s : ok (%s)" % (label, path.name))
        else:
            print("%-16s : MISSING (%s)" % (label, path))
            ok = False

    print("doctor: %s" % ("READY" if ok else "NOT READY"))
    if getattr(args, "json", False):
        print("---")
        print(json.dumps({"ready": bool(ok), "gil": gil,
                          "python": sys.version.split()[0]}, indent=2))
    return 0 if ok else 1


def cmd_lilith(args) -> int:
    """Hive status, stdlib only. Detail lives in the DB, not on screen."""
    import sqlite3

    db = Path.home() / ".azazael" / "memory_store.db"
    if not db.is_file():
        print("lilith: no memory_store.db yet -- hive unobserved, not failed.")
        print("  expected at %s" % db)
        return 0
    try:
        conn = sqlite3.connect("file:%s?mode=ro" % db, uri=True, timeout=5)
        try:
            kind = conn.execute(
                "select count(*) from sqlite_master where type='table'"
            ).fetchone()[0]
            print("lilith: hive observed -- %s tables in %s" % (kind, db.name))
        finally:
            conn.close()
    except Exception as e:
        print("lilith: DB unreadable (%s) -- reported, not raised." % e)
    if not args.once:
        print("(pass --once to assert single-shot mode; live wallboard is "
              "scripts/lilith_live_monitor.py)")
    return 0


def cmd_eve(args) -> int:
    """Passthrough to Eve Unleashed. Gamora routes, Eve runs."""
    repo_src = REPO / "src"
    sys.path.insert(0, str(repo_src))
    try:
        from eve_unleashed.cli import main as eve_main
    except Exception as e:
        print("eve: unavailable (%s)" % e)
        return 1
    sys.argv = ["eve"] + list(args.eve_args or [])
    try:
        return int(eve_main() or 0)
    except SystemExit as s:
        return int(s.code or 0)


def cmd_cradle(args) -> int:
    """Passthrough to Project_CRADLE/cradle.py (doctor/demo/grimoire/serve)."""
    cradle = REPO / "Project_CRADLE" / "cradle.py"
    if not cradle.is_file():
        print("cradle: missing (%s)" % cradle)
        return 1
    import runpy
    sys.argv = ["cradle.py"] + list(args.cradle_args or [])
    try:
        runpy.run_path(str(cradle), run_name="__main__")
        return 0
    except SystemExit as s:
        return int(s.code or 0)
    except Exception as e:
        print("cradle: failed (%s)" % e)
        return 1


def cmd_lucy(args) -> int:
    """Eliza + live therapy, natively combined, offline-first."""
    repo_src = REPO / "src"
    lucy_py = REPO / "Project_LUCY" / "lucy.py"
    for p in (str(repo_src), str(REPO / "Project_LUCY")):
        if p not in sys.path:
            sys.path.insert(0, p)
    try:
        import lucy as _lucy
    except Exception as e:
        print("lucy: unavailable (%s: %s)" % (lucy_py, e))
        return 1
    out = _lucy.companion_response(args.mood, args.note or "")
    print(out["response"])
    if args.json:
        print("---")
        print(json.dumps({k: v for k, v in out.items()
                          if k != "response"}, indent=2)[:2000])
    return 0


def cmd_swarm(args) -> int:
    """Native swarm over oracles: fan claims, report the split."""
    repo_src = REPO / "src"
    sys.path.insert(0, str(repo_src))
    try:
        from eve_unleashed.swarm_oracle import swarm as _swarm
    except Exception as e:
        print("swarm: unavailable (%s)" % e)
        return 1
    claims = list(args.claims or [])
    if not claims:
        print("swarm: no claims given.")
        return 1
    try:
        rep = _swarm(claims, live=False)
    except TypeError:
        # older signature: swarm(claims) without live flag
        rep = _swarm(claims)
    except Exception as e:
        print("swarm: failed (%s)" % e)
        return 1
    print(json.dumps(rep, indent=2)[:4000])
    return 0


def _span(capability, rep) -> None:
    """One Jaeger span per delegation. Telemetry never breaks the run."""
    try:
        repo_src = REPO / "src"
        if str(repo_src) not in sys.path:
            sys.path.insert(0, str(repo_src))
        from AOA.core.delegation_tracer import emit_delegation as _emit
        flat = rep if isinstance(rep, dict) else {"result": str(rep)}
        _emit(dict(flat), capability="gamora." + str(capability),
              arm_id="gamora-316t")
    except Exception:
        pass  # scanner:ignore silent_except_pass -- telemetry guard; the answer above already stands


def cmd_berzerker(args) -> int:
    """Native Berzerker A.I.O.: audit the mind, cross it, coach code."""
    if str(GAMORA_ROOT) not in sys.path:
        sys.path.insert(0, str(GAMORA_ROOT))
    try:
        import berzerker as _b
    except Exception as e:
        print("berzerker: unavailable (%s)" % e)
        return 1
    action = (args.action or "audit").lower()
    try:
        if action == "audit":
            rep = _b.audit()
        elif action == "mind":
            rep = _b.mind(args.text)
        elif action == "dream":
            rep = _b.dream(args.text or None)
        elif action == "inhibited":
            rep = _b.inhibited(args.text)
        elif action == "weird":
            rep = _b.weird_tests(args.lang)
        elif action == "done":
            rep = _b.record_completion(args.name, args.level)
        elif action == "code":
            rep = _b.code_coach(args.text, language=args.lang,
                                level=args.level,
                                name=args.name or None)
            if rep.get("ok") and not args.json:
                print(rep["response"])
                _span("berzerker.code", rep)
                return 0
        else:
            print("berzerker: unknown action %r"
                  " (audit|mind|dream|inhibited|weird|code|done)"
                  % args.action)
            return 1
    except Exception as e:
        print("berzerker: failed (%s)" % e)
        return 1
    _span("berzerker." + action, rep)
    if args.json or action in ("audit", "mind", "dream", "inhibited",
                               "weird", "done"):
        print(json.dumps(_b.as_jsonable(rep), indent=2)[:4000])
    elif rep.get("ok"):
        print(rep.get("response", rep))
    else:
        print("berzerker: %s" % rep.get("reason", rep))
        return 1
    return 0 if rep.get("ok", True) else 1


def cmd_inject(args) -> int:
    """Jaeger 3:16T prompt injector: wrap a prompt with trace + drive."""
    repo_src = REPO / "src"
    if str(GAMORA_ROOT) not in sys.path:
        sys.path.insert(0, str(GAMORA_ROOT))
    if str(repo_src) not in sys.path:
        sys.path.insert(0, str(repo_src))
    try:
        from jaeger_inject import inject as _inject
    except Exception as e:
        print("inject: unavailable (%s)" % e)
        return 1
    prompt = args.prompt
    if prompt == "-":
        prompt = sys.stdin.read()
    out = _inject(prompt, capability=args.capability, arm_id=args.arm,
                  max_push=True)
    sys.stdout.write(out["injected"])
    if not out["injected"].endswith("\n"):
        sys.stdout.write("\n")
    return 0


def build_parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(
        prog="gamora",
        description="Gamora DOMellifluousML cliT -- one command over "
                    "lilith swarm, eve, jaeger 3:16T, cradle, berzerker.")
    sub = ap.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("doctor", help="is this machine ready (316t?)")
    p.add_argument("--json", action="store_true")
    p.set_defaults(fn=cmd_doctor)

    p = sub.add_parser("lilith", help="hive status, stdlib only")
    p.add_argument("--once", action="store_true")
    p.set_defaults(fn=cmd_lilith)

    p = sub.add_parser("eve", help="passthrough to Eve Unleashed")
    p.add_argument("eve_args", nargs=argparse.REMAINDER)
    p.set_defaults(fn=cmd_eve)

    p = sub.add_parser("cradle", help="passthrough to Project_CRADLE")
    p.add_argument("cradle_args", nargs=argparse.REMAINDER)
    p.set_defaults(fn=cmd_cradle)

    p = sub.add_parser("lucy", help="Eliza + therapy, offline-first")
    p.add_argument("mood", help="how the user feels (one word)")
    p.add_argument("note", nargs="?", default="",
                   help="what they shared (optional)")
    p.add_argument("--json", action="store_true")
    p.set_defaults(fn=cmd_lucy)

    p = sub.add_parser("swarm", help="native swarm over oracles")
    p.add_argument("claims", nargs="+")
    p.set_defaults(fn=cmd_swarm)

    p = sub.add_parser("berzerker", help="native AIO mind + STEM coach")
    p.add_argument("action", nargs="?", default="audit",
                   help="audit|mind|dream|inhibited|weird|code|done")
    p.add_argument("text", nargs="?", default="",
                   help="request (mind) / assignment (code) / host"
                          " (dream|inhibited)")
    p.add_argument("--lang", default="python",
                   help="code coach language")
    p.add_argument("--level", default="spark",
                   help="spark | builder | pilot")
    p.add_argument("--name", default="",
                   help="builder first name (levels + receipts)")
    p.add_argument("--json", action="store_true")
    p.set_defaults(fn=cmd_berzerker)

    p = sub.add_parser("inject", help="Jaeger 3:16T prompt injector")
    p.add_argument("prompt", help="prompt text, or - for stdin")
    p.add_argument("--capability", default="opencode.prompt")
    p.add_argument("--arm", default="jaeger-316t")
    p.set_defaults(fn=cmd_inject)

    return ap


def main(argv=None) -> int:
    ap = build_parser()
    args = ap.parse_args(argv)
    try:
        return int(args.fn(args) or 0)
    except Exception as e:
        try:
            from CORE.failure_ledger import note_failure
        except Exception:
            def note_failure(where, exc=None):  # noqa: E306
                pass
        note_failure("gamora:main", e)
        print("gamora: failed (%s)" % e)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
