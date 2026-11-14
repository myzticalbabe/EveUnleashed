"""Eve native dashboard: a real desktop window (Tk, stdlib only).

`eve dash` -- no browser, no localhost, no JavaScript. Same builders as the
web dashboard, same selection store, same cradle control.
"""
import queue
import threading

from eve_unleashed import dashboard as _web
from eve_unleashed import model_picker as _mp


def row_for(e: dict, current: str | None) -> tuple:
    """Treeview row: (mark, id, detail, status). Pure + tested."""
    eid = _mp.entry_id(e)
    mark = "\u25cf" if eid == current else ""
    detail = e.get("base") or e.get("path") or ""
    if e.get("down"):
        status = "down"
    elif e.get("note"):
        status = e["note"]
    elif e.get("kind") == "agent" and not e.get("authed", True):
        status = "needs login"
    else:
        status = "up"
    return (mark, eid, detail, status)


def fmt_head(s: dict) -> str:
    c = s.get("cradle", {})
    cr = "serving %s" % ", ".join(c.get("models") or []) if c.get("running") else "down"
    return ("py %s   sel: %s   cradle: %s   mem %.0f%%   disk %.0f%%   %s"
            % (s.get("python", "?"), s.get("selection") or "(none)", cr,
               (s.get("mem") or {}).get("pct", 0),
               (s.get("disk") or {}).get("pct", 0),
               s.get("time", "")))


class Dash:
    def __init__(self):
        import tkinter as tk
        from tkinter import ttk
        self.tk = tk
        self.root = tk.Tk()
        self.root.title("Eve")
        self.root.geometry("860x620")
        self.q: queue.Queue = queue.Queue()
        self.entries: list = []
        self._busy = False

        self.head = tk.StringVar(value="starting…")
        ttk.Label(self.root, textvariable=self.head, font=("TkDefaultFont", 10, "bold"),
                  padding=6).pack(fill="x")

        cols = ("mark", "id", "detail", "status")
        self.tree = ttk.Treeview(self.root, columns=cols, show="headings", height=14)
        for c, w in (("mark", 30), ("id", 320), ("detail", 330), ("status", 140)):
            self.tree.heading(c, text=c)
            self.tree.column(c, width=w, stretch=(c in ("id", "detail")))
        self.tree.pack(fill="both", expand=True, padx=6)

        bar = ttk.Frame(self.root, padding=6)
        bar.pack(fill="x")
        self.b_use = ttk.Button(bar, text="Use selected", command=self.on_use)
        self.b_use.pack(side="left", padx=2)
        self.b_ref = ttk.Button(bar, text="Refresh", command=self.refresh)
        self.b_ref.pack(side="left", padx=2)
        self.b_start = ttk.Button(bar, text="Cradle start", command=self.on_start)
        self.b_start.pack(side="left", padx=2)
        self.b_stop = ttk.Button(bar, text="Cradle stop", command=self.on_stop)
        self.b_stop.pack(side="left", padx=2)
        self.msg = tk.StringVar()
        ttk.Label(bar, textvariable=self.msg).pack(side="left", padx=8)

        ask = ttk.Frame(self.root, padding=(6, 0, 6, 6))
        ask.pack(fill="x")
        self.prompt = tk.StringVar()
        ttk.Entry(ask, textvariable=self.prompt).pack(side="left", fill="x", expand=True)
        ttk.Button(ask, text="Ask local", command=self.on_ask).pack(side="left", padx=4)

        self.out = tk.Text(self.root, height=10, wrap="word")
        self.out.pack(fill="both", expand=False, padx=6, pady=(0, 6))
        self.root.after(200, self.poll)
        self.refresh()

    # -- background work -------------------------------------------
    def _work(self, fn, done):
        def run():
            try:
                out = fn()
            except Exception as e:  # never kill the UI thread
                out = {"__error__": str(e)}
            self.q.put((done, out))
        threading.Thread(target=run, daemon=True).start()

    def poll(self):
        try:
            while True:
                done, out = self.q.get_nowait()
                done(out)
        except queue.Empty:
            pass
        self.root.after(300, self.poll)

    def refresh(self):
        if self._busy:
            return
        self._busy = True
        self.msg.set("probing…")
        self._work(lambda: (_web.build_status(), _web.build_models()),
                   self.on_refreshed)

    def on_refreshed(self, out):
        self._busy = False
        if isinstance(out, dict) and out.get("__error__"):
            self.msg.set("probe failed: %s" % out["__error__"])
            return
        status, models = out
        self.head.set(fmt_head(status))
        self.entries = models.get("entries", [])
        cur = models.get("current")
        sel = self.tree.selection()
        focused = self.tree.item(sel[0])["values"][1] if sel else None
        self.tree.delete(*self.tree.get_children())
        for e in self.entries:
            self.tree.insert("", "end", values=row_for(e, cur))
        if focused:
            for item in self.tree.get_children():
                if self.tree.item(item)["values"][1] == focused:
                    self.tree.selection_set(item)
                    break
        self.msg.set("%d providers · %s" % (len(self.entries), status.get("time", "")))

    # -- actions ----------------------------------------------------
    def _selected_entry(self):
        sel = self.tree.selection()
        if not sel:
            self.msg.set("nothing selected")
            return None
        eid = self.tree.item(sel[0])["values"][1]
        return next((e for e in self.entries if _mp.entry_id(e) == eid), None)

    def on_use(self):
        e = self._selected_entry()
        if e is None:
            return
        _mp.save_selection(e)
        self.msg.set("selected: %s" % _mp.entry_id(e))
        self.refresh()

    def on_start(self):
        self.msg.set("starting cradle… (model load takes minutes)")
        self._work(_web.cradle_start, self.on_started)

    def on_started(self, out):
        self.msg.set("cradle pid %s" % out.get("pid") if out.get("ok")
                     else "start failed: %s" % out.get("error"))
        self.refresh()

    def on_stop(self):
        self._work(_web.cradle_stop, lambda out: (self.msg.set(
            "cradle stopped" if out.get("ok") else "stop failed: %s" % out.get("error")),
            self.refresh()))

    def on_ask(self):
        prompt = self.prompt.get().strip()
        if not prompt:
            return
        self.say("you: %s\n" % prompt)
        self.prompt.set("")
        self.msg.set("thinking…")
        from eve_unleashed import cli as _cli
        self._work(lambda: _cli._local_answer(prompt), self.on_answered)

    def on_answered(self, out):
        text, reason = out
        self.say(("eve: %s\n" % text) if text else ("(no answer: %s)\n" % reason))
        self.msg.set("done")

    def say(self, s: str):
        self.out.insert("end", s)
        self.out.see("end")


def run() -> int:
    Dash().root.mainloop()
    return 0


def cmd_dash(args) -> int:
    from eve_unleashed import native_dash as _nd
    return _nd.run()
