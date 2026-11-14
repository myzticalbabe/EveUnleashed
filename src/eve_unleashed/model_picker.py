"""Provider-agnostic model picker for Eve Unleashed (stdlib only).

Any generation backend Eve can speak to is a *provider entry*::

    server  OpenAI-compatible HTTP (/v1/models + /chat/completions):
            Ollama, LM Studio, llama.cpp, vLLM, or any custom base URL
    gguf    a .gguf file on disk (runs via the cradle sidecar runner)
    cradle  a named model adopted into ~/.azazael/cradle
    cloud   an OpenAI-compatible cloud (key from env, never stored)

Nothing is hardcoded to one vendor: unknown servers are still listed
(probed live), and operators can register any endpoint with
``eve models --add``. Selection persists to ``~/.azazael/eve_model.json``;
custom endpoints persist to ``~/.azazael/eve_providers.json``.
"""

from __future__ import annotations

import json
import os
import urllib.request
from pathlib import Path

STORE_DIR = Path.home() / ".azazael"
SELECTION_FILE = STORE_DIR / "eve_model.json"
PROVIDERS_FILE = STORE_DIR / "eve_providers.json"
CRADLE_DIR = STORE_DIR / "cradle"

#: Ports probed for OpenAI-compatible servers (Ollama :11434 included).
DEFAULT_PORTS = (8080, 1234, 11434, 1337)

#: Local GGUF search roots (cradle first: operator-placed models outrank libs).
GGUF_ROOTS = (
    STORE_DIR / "cradle",
    Path.home() / ".lmstudio" / "models",
    Path.home() / "models",
)

#: OpenAI-compatible clouds: provider -> (base url, key env var, default model).
#: Only listed when the key env var is set. Anthropic/Gemini native APIs are
#: intentionally absent (different protocol -- no silent half-support).
CLOUDS = {
    "openai": ("https://api.openai.com/v1", "OPENAI_API_KEY", "gpt-4o-mini"),
    "openrouter": ("https://openrouter.ai/api/v1", "OPENROUTER_API_KEY", "openai/gpt-oss-120b"),
    "deepseek": ("https://api.deepseek.com/v1", "DEEPSEEK_API_KEY", "deepseek-chat"),
    "groq": ("https://api.groq.com/openai/v1", "GROQ_API_KEY", "llama-3.3-70b-versatile"),
    "together": ("https://api.together.xyz/v1", "TOGETHER_API_KEY", "meta-llama/Llama-3.3-70B-Instruct-Turbo"),
    "xai": ("https://api.x.ai/v1", "XAI_API_KEY", "grok-3-mini"),
    "mistral": ("https://api.mistral.ai/v1", "MISTRAL_API_KEY", "mistral-small-latest"),
}

EMBED_HINTS = ("embed", "e5-", "bge-", "gte-", "minilm", "nomic",
               "mpnet", "roberta", "clip-")

#: Agent CLIs that can serve as inference providers when logged in.
#: Harnessed by this interpreter only (subprocess, absolute exe, no shell).
#: {name: (models argv, run argv builder)}
AGENT_CLIS = ("kilo", "opencode")
KILO_AUTH_FILE = Path.home() / ".local" / "share" / "kilo" / "auth.json"


def _is_embed(mid: str) -> bool:
    lowered = (mid or "").lower()
    return any(h in lowered for h in EMBED_HINTS)


def _fetch_ids(base: str, api_key: str | None = None, timeout: float = 2.0):
    """GET <base>/v1/models (or Ollama /api/tags). Returns [ids] or None."""
    headers = {"User-Agent": "eve-model-picker/1.0"}
    if api_key:
        headers["Authorization"] = "Bearer " + api_key
    for suffix in ("/v1/models", "/api/tags"):
        try:
            req = urllib.request.Request(base.rstrip("/") + suffix, headers=headers)
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                payload = json.loads(resp.read().decode("utf-8", "replace") or "{}")
        except Exception:
            continue
        ids = []
        for item in (payload.get("data") or payload.get("models") or []):
            if isinstance(item, dict):
                mid = item.get("id") or item.get("model") or item.get("name")
            else:
                mid = item
            if isinstance(mid, str) and mid:
                ids.append(mid)
        if ids:
            return ids
    return None


def _provider_label(port: int, host: str = "localhost") -> str:
    if port == 11434:
        return "ollama"
    if port == 1234:
        return "lm-studio"
    if port == 8080:
        return "llama.cpp"
    return "openai-compatible"


def discover(timeout: float = 2.0) -> list:
    """Probe everything; return entries [{provider, model, kind, ...}]."""
    entries: list = []

    ports = list(DEFAULT_PORTS)
    customs = load_customs()
    for c in customs:
        try:
            from urllib.parse import urlsplit
            port = urlsplit(c.get("base", "")).port
            if port and port not in ports:
                ports.append(port)
        except Exception:
            pass
    for port in ports:
        base = "http://localhost:%d" % port
        ids = _fetch_ids(base, timeout=timeout)
        if not ids:
            continue
        gen = [m for m in ids if not _is_embed(m)]
        if not gen:
            continue
        for mid in gen:
            entries.append({"provider": _provider_label(port), "model": mid,
                            "kind": "server", "base": base + "/v1"})

    # custom endpoints (probed live; kept even when down, flagged)
    for c in customs:
        base = c.get("base", "").rstrip("/")
        key = os.environ.get(c.get("key_env", ""), "") if c.get("key_env") else ""
        ids = _fetch_ids(base, api_key=key or None, timeout=timeout) if base else None
        model = c.get("model", "")
        if ids:
            gen = [m for m in ids if not _is_embed(m)]
            model = model or (gen[0] if gen else "")
        entries.append({"provider": c.get("name", "custom"), "model": model,
                        "kind": "server", "base": base + "/v1" if base else "",
                        "key_env": c.get("key_env", ""), "down": not ids})

    # local GGUF files
    seen = set()
    import shutil as _sh
    gguf_runner = bool(_sh.which("llama-server"))
    for root in GGUF_ROOTS:
        try:
            if not root.is_dir():
                continue
            for p in sorted(root.rglob("*.gguf")):
                if p.stat().st_size < 1000 or str(p) in seen:
                    continue
                seen.add(str(p))
                name = p.stem
                if any(h in name.lower() for h in ("mmproj",) + EMBED_HINTS):
                    continue
                entries.append({"provider": "gguf", "model": name,
                                "kind": "gguf", "path": str(p),
                                "note": "" if gguf_runner else "needs llama-server"})
        except Exception:
            continue

    # cradle registry
    try:
        from eve_unleashed.cradle import list_cradle_models
        import shutil as _sh2
        runner_ok = bool(_sh2.which("llama-server"))
        for m in list_cradle_models() or []:
            if m.get("framework") != "gguf":
                continue
            if m.get("bytes", 0) < 1024 * 1024:
                continue  # spec/vessel containers are not runnable weights
            entries.append({"provider": "cradle", "model": m.get("name", ""),
                            "kind": "cradle",
                            "note": "" if runner_ok else "needs llama-server"})
    except Exception:
        pass

    # keyed clouds (OpenAI-compatible only)
    for provider, (base, key_env, default_model) in CLOUDS.items():
        if not os.environ.get(key_env):
            continue
        ids = _fetch_ids(base, api_key=os.environ[key_env], timeout=timeout)
        model = default_model
        if ids:
            gen = [m for m in ids if not _is_embed(m)]
            if gen and default_model not in gen:
                model = gen[0]
        entries.append({"provider": provider, "model": model,
                        "kind": "cloud", "base": base, "key_env": key_env})

    # Agent CLIs (node spin-up) get their own budget, not the 2 s probe budget.
    entries.extend(discover_agents(timeout=max(timeout, 45.0)))

    # de-dup, keep order
    uniq, keys = [], set()
    for e in entries:
        k = (e["provider"], e["model"], e.get("base", ""))
        if k not in keys:
            keys.add(k)
            uniq.append(e)
    return uniq


def entry_id(e: dict) -> str:
    return "%s/%s" % (e["provider"], e["model"])


def _which(exe: str):
    import shutil
    return shutil.which(exe)


def _kilo_credentials() -> int:
    try:
        data = json.loads(KILO_AUTH_FILE.read_text())
        creds = data.get("credentials") or data
        return len(creds) if isinstance(creds, (list, dict)) else 0
    except Exception:
        return 0


def discover_agents(timeout: float = 30.0) -> list:
    """Agent-CLI providers (kilo/opencode): free + keyed models via their own auth.

    Listed always when the binary exists; usable after their own login
    (``kilo auth login``). Never spends quota without an explicit selection."""
    import subprocess
    entries: list = []
    for agent in AGENT_CLIS:
        exe = _which(agent)
        if not exe:
            continue
        models: list = []
        try:
            proc = subprocess.run([exe, "models"], capture_output=True, text=True,
                                  timeout=timeout)
            for line in (proc.stdout or "").splitlines():
                line = line.strip().strip("`")
                if "/" in line and " " not in line and line.startswith(agent + "/"):
                    models.append(line[len(agent) + 1:])
        except Exception:
            pass
        authed = _kilo_credentials() > 0 if agent == "kilo" else True
        if not models:
            entries.append({"provider": agent, "model": "", "kind": "agent",
                            "agent": agent, "authed": authed})
        for m in models:
            # run_model keeps the full CLI id (e.g. kilo/...); model is display.
            entries.append({"provider": agent, "model": m,
                            "run_model": "%s/%s" % (agent, m),
                            "kind": "agent", "agent": agent, "authed": authed})
    return entries


def run_agent(agent: str, model: str, prompt: str, timeout: float = 180.0) -> dict:
    """One non-interactive inference via an agent CLI. No shell, absolute exe."""
    import subprocess
    exe = _which(agent)
    if not exe:
        return {"status": "error", "error": "%s: not on PATH" % agent}
    argv = [exe, "run"]
    if model:
        argv += ["-m", model]
    argv += ["--format", "json", prompt]
    try:
        proc = subprocess.run(argv, capture_output=True, text=True, timeout=timeout)
    except Exception as exc:
        return {"status": "error", "error": "%s: %s" % (agent, exc)}
    out = (proc.stdout or "").strip()
    texts: list = []
    for line in out.splitlines():
        line = line.strip()
        if not line.startswith("{"):
            continue
        try:
            obj = json.loads(line)
        except Exception:
            continue
        if obj.get("type") == "error":
            err = (obj.get("error") or {})
            msg = err.get("data", {}).get("message") or err.get("message")
            if not msg:
                try:
                    body = json.loads(err.get("responseBody", "") or "{}")
                    msg = ((body.get("error") or {}).get("message"))
                except Exception:
                    msg = None
            return {"status": "error", "error": "%s: %s" % (agent, msg or "agent error")}
        texts.extend(_collect_text(obj))
    text = "\n".join(t for t in texts if t).strip()
    if text:
        return {"status": "ok", "result": text, "provider": agent, "model": model}
    if proc.returncode != 0:
        tail = ((proc.stderr or "").strip().splitlines() or [""])[-1]
        hint = " (run `%s auth login` first?)" % agent if "sign in" in tail.lower() else ""
        return {"status": "error", "error": "%s exit %d: %s%s" % (agent, proc.returncode, tail[:200], hint)}
    return {"status": "error", "error": "%s returned no text" % agent}


def _collect_text(obj) -> list:
    """Tolerant text extraction from opencode-family JSON event lines."""
    found: list = []
    if isinstance(obj, dict):
        part = obj.get("part")
        if isinstance(part, dict) and part.get("type") == "text":
            t = part.get("text")
            if isinstance(t, str) and t.strip():
                found.append(t)
        for key in ("text", "content", "message", "result"):
            v = obj.get(key)
            if isinstance(v, str) and v.strip() and key != "message":
                found.append(v)
            elif isinstance(v, dict):
                found.extend(_collect_text(v))
            elif isinstance(v, list):
                for item in v:
                    if isinstance(item, (dict, list)):
                        found.extend(_collect_text(item))
                    elif isinstance(item, str) and item.strip() and len(item) > 20:
                        found.append(item)
    elif isinstance(obj, list):
        for item in obj:
            found.extend(_collect_text(item))
    return found


def load_customs() -> list:
    try:
        return json.loads(PROVIDERS_FILE.read_text()) or []
    except Exception:
        return []


def save_customs(items: list) -> None:
    STORE_DIR.mkdir(parents=True, exist_ok=True)
    PROVIDERS_FILE.write_text(json.dumps(items, indent=2))


def add_custom(name: str, base: str, model: str = "", key_env: str = "") -> dict:
    items = [c for c in load_customs() if c.get("name") != name]
    entry = {"name": name, "base": base.rstrip("/"), "model": model, "key_env": key_env}
    items.append(entry)
    save_customs(items)
    return entry


def remove_custom(name: str) -> bool:
    items = load_customs()
    kept = [c for c in items if c.get("name") != name]
    if len(kept) == len(items):
        return False
    save_customs(kept)
    return True


def load_selection() -> dict | None:
    try:
        data = json.loads(SELECTION_FILE.read_text())
        return data if isinstance(data, dict) and data.get("model") else None
    except Exception:
        return None


def save_selection(entry: dict) -> dict:
    STORE_DIR.mkdir(parents=True, exist_ok=True)
    sel = {"provider": entry.get("provider"), "model": entry.get("model"),
           "kind": entry.get("kind"), "base": entry.get("base", ""),
           "path": entry.get("path", ""), "key_env": entry.get("key_env", ""),
           "agent": entry.get("agent", ""), "run_model": entry.get("run_model", "")}
    SELECTION_FILE.write_text(json.dumps(sel, indent=2))
    return sel


def current_id() -> str | None:
    sel = load_selection()
    return "%s/%s" % (sel["provider"], sel["model"]) if sel else None
