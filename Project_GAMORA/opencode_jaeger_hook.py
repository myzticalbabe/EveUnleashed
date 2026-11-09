"""Gamora opencode hook -- call jaeger_inject from the OpenCode CLI.

WIRING (opencode.json, one hook):
    { "hooks": { "pre-prompt": "python C:/Azazael/azazael/Project_GAMORA/opencode_jaeger_hook.py" } }

Reads the prompt from argv[1:] (or stdin when argv is empty), injects the
Jaeger 3:16T header + drive block, writes the injected prompt to stdout.
Exit code is always 0: injection never blocks a prompt.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from jaeger_inject import inject


def main() -> int:
    if len(sys.argv) > 1:
        prompt = " ".join(sys.argv[1:])
    else:
        prompt = sys.stdin.read()
    try:
        out = inject(prompt)
        sys.stdout.write(out["injected"])
    except Exception:
        # Injection must never eat a prompt: pass it through raw.
        sys.stdout.write(prompt)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
