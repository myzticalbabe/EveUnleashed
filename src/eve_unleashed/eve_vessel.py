"""Eve is the model. The vessel is her charter, not a weight file.

eve-vessel-316t carries: her system prompt, her native hands (EVE_CALL lines
executed natively, results returned), and a foundry container whose runner
weights are queued. This module implements the charter:

- VESSEL_SYSTEM: her voice, verbatim from eve-vessel-316t.eve.json.
- parse_calls: EVE_CALL: <function> <json-args> lines in a reply.
- execute_call: dispatch to Eve's own modules (foundry/morph/langs/stem/
  therapy/redress/ablate/nsp). Unknown functions are refused, never guessed.
- eve_answer: generate -> execute -> regenerate loop (max 2 rounds).

The token engine behind `generate` is whichever backend the user selected.
Eve answers; backends don't.
"""
import inspect
import json
from pathlib import Path

VESSEL_SYSTEM = (
    "You are Eve Unleashed, a builder who answers directly and never "
    "narrates her reasoning. You have native hands: lines of the form "
    "EVE_CALL: <function> <json-args> in your reply are executed natively "
    "and the results returned. Use them instead of guessing."
)

VESSEL_FILES = ("eve-vessel-316t.gguf", "eve-vessel-316t.eve.json")
MAX_ROUNDS = 2


def cradle_dir():
    return Path.home() / ".azazael" / "cradle"


def load_vessel() -> dict:
    """Read the vessel charter from the cradle. Refuses to invent one."""
    d = cradle_dir()
    meta = d / VESSEL_FILES[1]
    if not meta.exists():
        return {"ok": False,
                "error": "no vessel in the cradle (~/.azazael/cradle/%s)"
                         % VESSEL_FILES[1]}
    try:
        spec = json.loads(meta.read_text(encoding="utf-8"))
    except Exception as e:
        return {"ok": False, "error": "unreadable vessel: %s" % e}
    missing = [f for f in VESSEL_FILES if not (d / f).exists()]
    return {"ok": True, "spec": spec, "missing": missing,
            "system": spec.get("system_prompt", VESSEL_SYSTEM)}


def _call(modname: str, fnname: str, args: dict):
    mod = __import__("eve_unleashed.%s" % modname,
                     fromlist=[fnname])
    fn = getattr(mod, fnname)
    try:
        sig = inspect.signature(fn)
        kwargs = {k: v for k, v in args.items()
                  if k in sig.parameters}
    except (ValueError, TypeError):
        kwargs = dict(args)
    return fn(**kwargs)


def _safe(obj, limit: int = 4000):
    try:
        s = json.dumps(obj, default=str)
    except Exception:
        s = str(obj)
    return s if len(s) <= limit else s[:limit] + "…[truncated]"


# native function -> (module, function, arg aliases). The model's JSON arg
# names are stable; aliases bridge to the modules' parameter names.
NATIVE = {
    "foundry.build": ("soul_foundry", "build_all", {"out": "out_dir"}),
    "morph.convert": ("morph", "convert_text",
                       {"src": "src_path", "dst": "dst_path"}),
    "morph.report": ("morph", "morph_markdown", {"src": "state"}),
    "langs.check": ("langs", "check", {}),
    "langs.fmt": ("langs", "fmt", {}),
    "stem.track": ("stem", "plan_track", {}),
    "therapy.ground": ("therapy", "fallback_response", {}),
    "redress.file": ("redress", "file_grievance", {}),
    "ablate.classify": ("ablate", "classify", {}),
    "nsp.verify": ("nsp_check", "verify_router_trace", {}),
}


def parse_calls(text: str) -> list:
    """Extract [(function, args)] from EVE_CALL lines. Never raises."""
    calls = []
    for line in (text or "").splitlines():
        s = line.strip()
        if not s.startswith("EVE_CALL:"):
            continue
        rest = s[len("EVE_CALL:"):].strip()
        name, _, payload = rest.partition(" ")
        name = name.strip()
        try:
            args = json.loads(payload) if payload.strip() else {}
            if not isinstance(args, dict):
                args = {"_arg": args}
        except Exception:
            calls.append((name, {"_raw": payload,
                                "_error": "args are not JSON"}))
            continue
        calls.append((name, args))
    return calls


def execute_call(name: str, args: dict) -> dict:
    """Run one native hand. Unknown functions are refused, never guessed."""
    if name not in NATIVE:
        return {"ok": False, "function": name,
                "error": "unknown native function %r (vessel lists: %s)"
                         % (name, ", ".join(sorted(NATIVE)))}
    if "_error" in args:
        return {"ok": False, "function": name, "error": args["_error"]}
    modname, fnname, aliases = NATIVE[name]
    args = {aliases.get(k, k): v for k, v in args.items()}
    try:
        if name == "morph.report" and isinstance(args.get("src"), str):
            p = Path(args["src"])
            args = dict(args, src=json.loads(p.read_text(encoding="utf-8")))
        result = _call(modname, fnname, args)
        return {"ok": True, "function": name, "result": _safe(result)}
    except Exception as e:
        return {"ok": False, "function": name,
                "error": "%s: %s" % (type(e).__name__, e)}


def explore() -> dict:
    """Eve explores her environment with her own hands. No engine needed:
    every probe below is a native call (langs/cradle/picker/dashboard).
    Returns a JSON-serializable report."""
    import platform
    import shutil
    from eve_unleashed import dashboard as _web
    from eve_unleashed import model_picker as _mp
    rep: dict = {"vessel": load_vessel()["ok"]}
    try:
        st = _web.build_status()
        rep.update({"python": st.get("python"),
                    "platform": platform.system(),
                    "cpu": st.get("cpu_count"),
                    "mem_pct": (st.get("mem") or {}).get("pct"),
                    "disk_pct": (st.get("disk") or {}).get("pct"),
                    "llama_server": bool(st.get("llama_server")),
                    "cradle_up": (st.get("cradle") or {}).get("running", False),
                    "cradle_models": (st.get("cradle") or {}).get("models", []),
                    "selection": st.get("selection")})
    except Exception as e:
        rep["status_error"] = str(e)
    tools: dict = {}
    try:
        from eve_unleashed import langs as _l
        for lang in ("python", "rust", "go"):
            try:
                tools[lang] = {t: bool(p) for t, p in
                               _l.have_tools(lang).items()}
            except Exception:
                tools[lang] = {}
    except Exception:
        pass
    rep["tools"] = tools
    try:
        from eve_unleashed.cradle import list_cradle_models
        rep["cradle_files"] = [(m.get("name"), m.get("bytes", 0))
                               for m in (list_cradle_models() or [])]
    except Exception:
        rep["cradle_files"] = []
    try:
        entries = _mp.discover()
        kinds: dict = {}
        for e in entries:
            kinds[e.get("kind", "?")] = kinds.get(e.get("kind", "?"), 0) + 1
        rep["providers"] = {"total": len(entries), "by_kind": kinds}
    except Exception as e:
        rep["providers"] = {"total": 0, "error": str(e)}
    rep["gpu"] = bool(shutil.which("llama-server"))
    return rep


def eve_answer(prompt: str, generate, max_rounds: int = MAX_ROUNDS) -> dict:
    """Eve answers: generate, execute her hands, answer with results.

    `generate(system, prompt)` returns reply text from the selected backend.
    Pure logic -- the only I/O is inside `generate` and the native hands.
    """
    trace = []
    turn = prompt
    for _ in range(max_rounds + 1):
        reply = generate(VESSEL_SYSTEM, turn)
        calls = parse_calls(reply)
        if not calls:
            return {"ok": True, "answer": reply.strip(), "trace": trace}
        results = []
        for name, args in calls:
            out = execute_call(name, args)
            trace.append(out)
            results.append("EVE_RESULT %s: %s"
                           % (name, out.get("result", out.get("error"))))
        turn = ("The native calls returned:\n" + "\n".join(results)
                + "\nAnswer the user directly now, no more calls.")
    return {"ok": True, "answer": reply.strip(), "trace": trace,
            "note": "call budget spent; returning last reply"}
