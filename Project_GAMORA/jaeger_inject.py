"""Jaeger 3:16T prompt injector -- the OpenCode CLI, evolved.

WHAT THIS IS
------------
OpenCode (node CLI) sends prompts and gets text back; nothing records
whether the delegation was right. This module wraps any prompt with a
Jaeger trace header plus a max push/drive directive block, and records
the delegation as one span through the tree's own tracer
(AOA.core.delegation_tracer.emit_delegation) backed by the SDK-free
SQLiteSpanExporter (src/CORE/cd3_exporter.py).

"Max push/drive" is explicit, not hype: the injected block states the
goal (produce the change, not describe it), the constraints (stdlib
first, evidence over claims, never break the host), and the verification
(run the smallest check that covers the change). A prompt that does not
say how it will be proven is a wish.

WIRING INTO OPENCODE
--------------------
One line in opencode.json hooks, or call it by hand:

    python Project_GAMORA/jaeger_inject.py --capability opencode.prompt --arm jaeger-316t "do the thing"

    echo "do the thing" | python Project_GAMORA/jaeger_inject.py --capability opencode.prompt --arm jaeger-316t -

The span write never fails the prompt: tracing disabled, no writer
importable, or a write error all degrade to header-only injection.
"""

from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent

#: Max push/drive directive block. Short on purpose: it rides every prompt.
DRIVE_BLOCK = (
    "DIRECTIVE (jaeger-316t max push/drive): produce the change, not a "
    "description of it. Constraints: stdlib first; evidence over claims; "
    "never break the host; smallest diff that meets the goal. Verification: "
    "run the smallest check that covers the change and report it. "
    "If a requirement is ambiguous, state the reading you chose."
)


def _trace_ids():
    """Fresh trace/span ids from the tree tracer, or stdlib fallback."""
    try:
        repo_src = REPO / "src"
        if str(repo_src) not in sys.path:
            sys.path.insert(0, str(repo_src))
        from AOA.core.delegation_tracer import new_span_id, new_trace_id
        return new_trace_id(), new_span_id()
    except Exception:
        import secrets
        return secrets.token_hex(16), secrets.token_hex(8)


def _record_span(prompt, *, capability, arm_id, trace_id, span_id):
    """One span per injection. Never raises, never fails the prompt."""
    try:
        repo_src = REPO / "src"
        if str(repo_src) not in sys.path:
            sys.path.insert(0, str(repo_src))
        from AOA.core.delegation_tracer import emit_delegation
        t0 = time.perf_counter()
        flat = {"status": "ok",
                "prompt_chars": len(prompt or ""),
                "injector": "jaeger-316t"}
        duration_ms = (time.perf_counter() - t0) * 1000.0
        emit_delegation(flat, capability=capability, arm_id=arm_id,
                        trace_id=trace_id, span_id=span_id,
                        duration_ms=duration_ms)
        return True
    except Exception:
        try:
            from CORE.failure_ledger import note_failure  # noqa: E401
        except Exception:
            pass  # scanner:ignore silent_except_pass -- last-resort telemetry guard; record() must never raise
        return False


def inject(prompt, *, capability="opencode.prompt", arm_id="jaeger-316t",
           max_push=True):
    """Wrap prompt with a Jaeger 3:16T header (+ drive block)."""
    prompt = prompt or ""
    trace_id, span_id = _trace_ids()
    recorded = _record_span(prompt, capability=capability, arm_id=arm_id,
                            trace_id=trace_id, span_id=span_id)
    header = ("<jaeger-316t trace_id=%s span_id=%s capability=%s arm=%s "
              "recorded=%s>" % (trace_id, span_id, capability, arm_id,
                                "yes" if recorded else "header-only"))
    parts = [header, prompt.strip()]
    if max_push:
        parts.append(DRIVE_BLOCK)
    injected = "\n\n".join(p for p in parts if p)
    return {"injected": injected, "trace_id": trace_id, "span_id": span_id,
            "capability": capability, "arm_id": arm_id,
            "recorded": recorded}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(
        description="Jaeger 3:16T prompt injector (OpenCode CLI evolved).")
    ap.add_argument("prompt", help="prompt text, or - for stdin")
    ap.add_argument("--capability", default="opencode.prompt")
    ap.add_argument("--arm", default="jaeger-316t")
    ap.add_argument("--no-drive", action="store_true",
                    help="header only, no push/drive block")
    args = ap.parse_args(argv)
    prompt = args.prompt
    if prompt == "-":
        prompt = sys.stdin.read()
    out = inject(prompt, capability=args.capability, arm_id=args.arm,
                 max_push=not args.no_drive)
    sys.stdout.write(out["injected"])
    if not out["injected"].endswith("\n"):
        sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
