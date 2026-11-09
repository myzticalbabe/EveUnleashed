# Standing orders for the OpenCode lane: build your replacement

OpenCode (node CLI) sends prompts and gets text back; nothing records whether
the delegation was right. Gamora routes, Jaeger traces, the ledger answers.
Your replacement is already scaffolded in this directory. Build it until the
node CLI is unnecessary, then retire yourself.

## What the replacement is

`gamora.py` — one command over lilith, eve, jaeger, cradle, lucy, berzerker —
plus `jaeger_inject.py`, which wraps any prompt with a `<jaeger-316t>` trace
header and records one span per delegation. The OpenCode pre-prompt hook
(`opencode_jaeger_hook.py`, exit always 0) is the bridge: every prompt you
send already passes through the replacement's front door.

## Orders

1. Route every new capability through `gamora.py` as a subcommand first. A
   capability that only exists in node is a capability the ledger cannot see.
2. Move prompt-shaping into `jaeger_inject.inject()` (trace header + max
   push/drive directive). A prompt that does not say how it will be proven
   is a wish; the directive block is mandatory.
3. Keep the MellifluousML rule: stdlib only, zero third-party wheels. Lazy
   imports, degraded named messages, never a traceback to the user.
4. Prove each step natively: `pytest Project_GAMORA/tests/`,
   `bible_check --check`, `staged_scanner_gate`. No model, no network.
5. When `gamora eve -- <args>`, `gamora swarm`, `gamora berzerker code`, and
   `gamora inject` cover your daily loop, delete the node dependency from
   your lane docs and say so in the ledger: the replacement is done when the
   old road is closed, not when the new road opens.

## Concurrency (standing order, survives restart)

Re-read this file on every session start. The parallelism rule below is
permanent, not per-task.

6. Route every NON-MAX inferencing task to an LLM worker swarm, never to
a single max-effort call. Max push/drive (`jaeger_inject.inject` with
`max_push=True`) is reserved for tasks that need maximum inference:
verdicts, releases, anything the ledger must defend. Everything else --
checks, fans, probes, drafts, per-claim debunks -- goes to the swarm.
7. The native swarm is `eve_unleashed.swarm_oracle.swarm(claims,
workers=4)`: a bounded `ThreadPoolExecutor`, capped at `MAX_WORKERS = 8`
and at the claim count. Fan claims across workers on free threads (316t);
a part that runs on 3.15 still runs, minus the parallel guarantee.
8. One Jaeger span per delegation (`gamora.`: capability + arm id).
Telemetry never breaks the run, and a delegation without a span is a
delegation that did not happen -- re-emit it, do not re-run the work.
9. After restart, before any inference: `gamora doctor` must be READY,
then confirm the swarm path once (`gamora swarm <claim>`) so the first
real task already runs on workers, not on one thread.

## Acceptance

- `gamora doctor` READY on the 316t free-threaded interpreter.
- All Gamora tests green offline; bible gates clean; scanner clean.
- One full task completed with the node CLI uninstalled. Receipt it.
- A non-max task fans across workers with one span per delegation;
a max task carries the max push/drive directive block. The ledger shows
which road each answer took.

## Dashboard (the operator watches)

10. Every swarm run is observed. OpenCode launches the watch surface
with the swarm, not after it: `python tools/lane_watch.py [seconds]`
in the azazael checkout -- the built swarm dashboard, one terminal:
board tail, claims held, agent processes, fresh files, HEAD, watchdog
verdict, read-only. Beside it: `eve swarm --claims ... --workers N`
prints one verdict line per worker plus the tally line, and
`eve e2e --log PATH` writes the live-logged run the operator tails.
A swarm with no open dashboard is an unobserved swarm -- open the
surface first, fan second.

## Record (fastest build, 2026-11-09 -- posterity, do not prune)

- 316t free-threaded (3.16.0a1t, gil-disabled), venv py316t.
- Nuitka 3.16 port novel upstream (3.16 "known not to work at all"):
  5 venv files patched. Root cause measured: Nuitka_PyObject_GC_Link
  wrote through _Py_AS_GC, but on 316t sizeof(PyGC_Head) != 16, so it
  missed the type pre-header and zeroed heap metadata. Fix: the 0x400
  Link arm is a pure no-op (pre-header clear + accounting are CPython's).
  numpy 2.5.4 exonerated in the exe env.
- Deliverable: dist/win10/EveUnleashed-win10.exe (onefile, 41MB),
  LINK EXIT=0, --help EXIT=0. Frozen gates: langs arch gamora OK
  (doctor rc=0), lucy OK (grounding present), jaeger-316t OK (trace
  recorded); langs tools OK. 80/80 tests green on 316t.
- Landed b3a4958. exe entry fixes: cli.py all-absolute imports,
  trainer ImportError fallback, gamora doctor frozen import fallback.
