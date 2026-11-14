"""Eve dashboard: one localhost page over the whole harness.

Stdlib only. No external assets, no CDN, no auth (binds 127.0.0.1).
`eve dashboard [--port 8899]` -- Gamora is the harness, this is its face.
"""
import json
import os
import platform
import shutil
import signal
import subprocess
import sys
import time
import urllib.request
from functools import partial
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

HOME = Path.home()
AZ = HOME / ".azazael"
CRADLE_DIR = AZ / "cradle"
PID_FILE = AZ / "cradle-server.pid"
LOG_FILE = AZ / "log" / "cradle-server.log"
CRADLE_PORT = 8080
CRADLE_BASE = "http://127.0.0.1:%d" % CRADLE_PORT


# ---------------------------------------------------------------- probes

def _http_json(url, timeout=3.0):
    try:
        with urllib.request.urlopen(url, timeout=timeout) as r:
            if r.status != 200:
                return None
            return json.loads(r.read().decode("utf-8", "replace"))
    except Exception:
        return None


def _pid_alive(pid: int) -> bool:
    try:
        os.kill(pid, 0)
        return True
    except Exception:
        return False


def _mem() -> dict:
    try:
        import psutil  # type: ignore
        m = psutil.virtual_memory()
        return {"total_gb": round(m.total / 1e9, 1), "pct": m.percent}
    except Exception:
        pass
    try:
        info = {}
        for line in Path("/proc/meminfo").read_text().splitlines():
            k, _, v = line.partition(":")
            info[k.strip()] = v.strip()
        total = int(info.get("MemTotal", "0").split()[0]) // 1024
        avail = int(info.get("MemAvailable", "0").split()[0]) // 1024
        pct = round(100.0 * (total - avail) / total, 1) if total else 0.0
        return {"total_gb": round(total / 1024, 1), "pct": pct}
    except Exception:
        return {"total_gb": 0.0, "pct": 0.0}


def _disk() -> dict:
    try:
        import psutil  # type: ignore
        d = psutil.disk_usage(str(HOME))
        return {"total_gb": round(d.total / 1e9, 1), "pct": d.percent}
    except Exception:
        pass
    try:
        st = os.statvfs(str(HOME))
        total = st.f_blocks * st.f_frsize
        free = st.f_bavail * st.f_frsize
        pct = round(100.0 * (total - free) / total, 1) if total else 0.0
        return {"total_gb": round(total / 1e9, 1), "pct": pct}
    except Exception:
        return {"total_gb": 0.0, "pct": 0.0}


def build_status() -> dict:
    """Everything the header needs. JSON-serializable, no exceptions."""
    from eve_unleashed import model_picker as _mp
    sel = _mp.current_id()
    health = _http_json(CRADLE_BASE + "/health", timeout=2.0)
    mods = _http_json(CRADLE_BASE + "/v1/models", timeout=2.0)
    names = []
    if isinstance(mods, dict):
        data = mods.get("data") or []
        names = [m.get("id", "?") for m in data if isinstance(m, dict)]
    pid = None
    try:
        pid = int(PID_FILE.read_text().strip().split()[0])
    except Exception:
        pid = None
    return {
        "ok": True,
        "time": time.strftime("%H:%M:%S"),
        "python": platform.python_version(),
        "platform": platform.platform(),
        "cpu_count": os.cpu_count() or 0,
        "mem": _mem(),
        "disk": _disk(),
        "llama_server": shutil.which("llama-server") or "",
        "cradle": {
            "running": health == {"status": "ok"},
            "pid": pid if (pid and _pid_alive(pid)) else None,
            "models": names,
            "ggufs": sorted(p.name for p in CRADLE_DIR.glob("*.gguf")) if CRADLE_DIR.is_dir() else [],
        },
        "selection": sel,
        "ready": True,
    }


def build_models() -> dict:
    from eve_unleashed import model_picker as _mp
    entries = _mp.discover()
    return {"current": _mp.current_id(), "entries": entries}


# ------------------------------------------------------------ control

def cradle_start() -> dict:
    if not CRADLE_DIR.is_dir():
        return {"ok": False, "error": "no cradle dir (~/.azazael/cradle)"}
    ggufs = sorted(CRADLE_DIR.glob("*.gguf"))
    if not ggufs:
        return {"ok": False, "error": "no .gguf adopted into the cradle"}
    if _http_json(CRADLE_BASE + "/health", timeout=2.0) == {"status": "ok"}:
        return {"ok": True, "already": True}
    exe = shutil.which("llama-server")
    if not exe:
        return {"ok": False, "error": "no llama-server on PATH (build llama.cpp)"}
    gguf = ggufs[0]
    LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
    log = open(LOG_FILE, "a")
    proc = subprocess.Popen(
        [exe, "-m", str(gguf), "--port", str(CRADLE_PORT),
         "--ctx-size", "2048", "--alias", "cradle-" + gguf.stem],
        stdout=log, stderr=subprocess.STDOUT,
        stdin=subprocess.DEVNULL, start_new_session=True)
    PID_FILE.write_text(str(proc.pid))
    for _ in range(60):
        if _http_json(CRADLE_BASE + "/health", timeout=2.0) == {"status": "ok"}:
            return {"ok": True, "pid": proc.pid, "model": gguf.name}
        if proc.poll() is not None:
            return {"ok": False, "error": "llama-server exited during load (see log)"}
        time.sleep(5)
    return {"ok": True, "pid": proc.pid, "model": gguf.name,
            "note": "still loading (large model); health not ok yet"}


def cradle_stop() -> dict:
    try:
        pid = int(PID_FILE.read_text().strip().split()[0])
    except Exception:
        return {"ok": True, "already": True, "note": "no pidfile"}
    if not _pid_alive(pid):
        try:
            PID_FILE.unlink()
        except Exception:
            pass
        return {"ok": True, "already": True, "note": "stale pidfile cleared"}
    try:
        os.kill(pid, signal.SIGTERM)
    except Exception as e:
        return {"ok": False, "error": str(e)}
    for _ in range(20):
        if not _pid_alive(pid):
            try:
                PID_FILE.unlink()
            except Exception:
                pass
            return {"ok": True, "stopped": pid}
        time.sleep(0.5)
    return {"ok": False, "error": "pid %d did not exit" % pid}


def log_tail(name: str = "cradle", lines: int = 60) -> str:
    path = LOG_FILE if name == "cradle" else None
    if path is None or not path.exists():
        return "(no log)"
    try:
        data = path.read_text(errors="replace").splitlines()
        return "\n".join(data[-lines:])
    except Exception as e:
        return "(unreadable: %s)" % e


# ---------------------------------------------------------------- page

PAGE = """<!doctype html><html><head><meta charset=utf-8>
<meta name=viewport content="width=device-width,initial-scale=1">
<title>Eve Dashboard</title>
<style>
body{background:#0b0e14;color:#d6deeb;font:14px/1.45 system-ui,sans-serif;margin:0}
header{display:flex;gap:16px;align-items:center;padding:12px 20px;background:#11151f;border-bottom:1px solid #263}
h1{font-size:18px;margin:0}.ok{color:#7ee787}.bad{color:#ff7b72}
main{display:grid;grid-template-columns:repeat(auto-fit,minmax(340px,1fr));gap:12px;padding:12px 20px}
section{background:#11151f;border:1px solid #223;border-radius:8px;padding:12px}
h2{font-size:14px;margin:0 0 8px;color:#9db4d0;text-transform:uppercase;letter-spacing:.06em}
table{width:100%;border-collapse:collapse;font-size:13px}
td,th{padding:4px 6px;text-align:left;border-bottom:1px solid #1c2230}
tr.cur td{color:#7ee787}button{background:#1f6feb;color:#fff;border:0;border-radius:6px;padding:4px 10px;cursor:pointer}
button:disabled{background:#333}button.danger{background:#a40e26}
.bar{height:8px;background:#222;border-radius:4px;overflow:hidden;margin:3px 0 8px}
.bar>i{display:block;height:100%;background:#1f6feb}
pre{background:#000;border:1px solid #223;border-radius:6px;padding:8px;max-height:300px;overflow:auto;font-size:12px;white-space:pre-wrap}
small{color:#8b949e}
</style></head><body>
<header><h1>EVE <span id=ready class=ok>●</span></h1>
<span id=headline><small>loading…</small></span></header>
<main>
<section><h2>Providers</h2><div id=models><small>loading…</small></div></section>
<section><h2>Cradle (server)</h2><div id=cradle><small>loading…</small></div>
<div style="margin-top:8px"><button id=bstart>Start</button>
<button id=bstop class=danger>Stop</button> <small id=cmsg></small></div></section>
<section><h2>System</h2><div id=sys><small>loading…</small></div></section>
<section><h2>Log: cradle-server</h2><pre id=log><small>loading…</small></pre></section>
</main>
<script>
async function jget(u){const r=await fetch(u);return r.json()}
async function jpost(u,b){const r=await fetch(u,{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify(b||{})});return r.json()}
function esc(s){return String(s).replace(/[&<>"]/g,c=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;"}[c]))}
async function refresh(){
 const s=await jget("/api/status");
 document.getElementById("ready").className=s.ready?"ok":"bad";
 const c=s.cradle;
 document.getElementById("headline").innerHTML="<small>py "+esc(s.python)+" · sel "+esc(s.selection||"(none)")+" · "+esc(s.time)+"</small>";
 document.getElementById("sys").innerHTML=
  "CPU ×"+s.cpu_count+"<br>MEM "+s.mem.pct+"% of "+s.mem.total_gb+" GB<div class=bar><i style='width:"+s.mem.pct+"%'></i></div>"+
  "DISK "+s.disk.pct+"% of "+s.disk.total_gb+" GB<div class=bar><i style='width:"+s.disk.pct+"%'></i></div>"+
  "<small>llama-server: "+(esc(s.llama_server)||"<span class=bad>missing</span>")+"</small>";
 document.getElementById("cradle").innerHTML=
  (c.running?"<span class=ok>● serving</span>":"<span class=bad>● down</span>")+
  " <small>pid "+(c.pid||"—")+"</small><br><small>models: "+esc((c.models||[]).join(", ")||"—")+
  "<br>cradle gguf: "+esc((c.ggufs||[]).join(", ")||"—")+"</small>");
 const m=await jget("/api/models");
 let h="<table><tr><th></th><th>provider/model</th><th></th></tr>";
 m.entries.forEach(e=>{
  const id=e.provider+"/"+e.model, cur=id===m.current;
  const st=e.down?"<span class=bad>down</span>":(e.note?"<small>"+esc(e.note)+"</small>":"<span class=ok>up</span>");
  h+="<tr"+(cur?" class=cur":"")+"><td>"+(cur?"●":"")+"</td><td>"+esc(id)+"<br><small>"+esc(e.base||e.path||"")+"</small></td><td>"+st+(cur?"":" <button data-id='"+esc(id)+"'>use</button>")+"</td></tr>";
 });
 document.getElementById("models").innerHTML=h+"</table>";
 document.querySelectorAll("button[data-id]").forEach(b=>b.onclick=async()=>{
  const r=await jpost("/api/select",{id:b.dataset.id});alert(r.selected||r.error);refresh();
 });
 const l=await jget("/api/log?name=cradle");
 document.getElementById("log").textContent=l.tail;
}
document.getElementById("bstart").onclick=async()=>{document.getElementById("cmsg").textContent="starting… (model load takes minutes)";const r=await jpost("/api/cradle/start");document.getElementById("cmsg").textContent=r.ok?("pid "+(r.pid||"?")):r.error;refresh()};
document.getElementById("bstop").onclick=async()=>{const r=await jpost("/api/cradle/stop");document.getElementById("cmsg").textContent=r.ok?"stopped":r.error;refresh()};
refresh();setInterval(refresh,8000);
</script></body></html>
"""


class _Handler(BaseHTTPRequestHandler):
    server_version = "EveDashboard/1.0"

    def _send(self, obj, code=200):
        body = json.dumps(obj).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _body(self):
        try:
            n = int(self.headers.get("Content-Length") or 0)
        except Exception:
            n = 0
        if not n:
            return {}
        try:
            return json.loads(self.rfile.read(n).decode("utf-8") or "{}")
        except Exception:
            return {}

    def do_GET(self):
        from urllib.parse import urlparse, parse_qs
        u = urlparse(self.path)
        if u.path == "/":
            body = PAGE.encode()
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return
        if u.path == "/api/status":
            try:
                self._send(build_status())
            except Exception as e:
                self._send({"ok": False, "ready": False, "error": str(e)}, 500)
            return
        if u.path == "/api/models":
            try:
                self._send(build_models())
            except Exception as e:
                self._send({"current": None, "entries": [], "error": str(e)}, 500)
            return
        if u.path == "/api/log":
            q = parse_qs(u.query)
            self._send({"tail": log_tail(q.get("name", ["cradle"])[0])})
            return
        self._send({"error": "not found"}, 404)

    def do_POST(self):
        from eve_unleashed import model_picker as _mp
        if self.path == "/api/select":
            want = (self._body().get("id") or "").strip()
            entries = _mp.discover()
            match = next((e for e in entries if _mp.entry_id(e) == want), None)
            if match is None:
                lowered = want.lower()
                match = next((e for e in entries
                              if lowered in _mp.entry_id(e).lower()), None)
            if match is None:
                self._send({"ok": False, "error": "no provider matches %r" % want})
                return
            _mp.save_selection(match)
            self._send({"ok": True, "selected": _mp.entry_id(match)})
            return
        if self.path == "/api/cradle/start":
            self._send(cradle_start())
            return
        if self.path == "/api/cradle/stop":
            self._send(cradle_stop())
            return
        self._send({"error": "not found"}, 404)

    def log_message(self, *a):
        pass


def serve(port: int = 8899) -> int:
    srv = ThreadingHTTPServer(("127.0.0.1", port), _Handler)
    print("eve dashboard: http://127.0.0.1:%d  (Ctrl-C to stop)" % port)
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        pass
    return 0

