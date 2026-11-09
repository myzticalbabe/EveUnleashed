# THE RESURRECTION MANDATE

Advancement must not require abandonment. Every deliverable in this repo
installs on the oldest **provable** interpreter, not just the newest one.
Obsolete machines are part of the swarm, not a burden on it.

## The floor rule

- The claimed floor (`Requires-Python`) is the lowest version with a **live
  proof**: `pip install` exit 0, import clean, CLI smoke — on a real
  interpreter (fetched via `uv python install`, never a fragment copy).
- Static evidence (grammar parse at `feature_version`, stdlib API sweep) may
  *support* a floor but never *set* one. An unrun version is an unclaimed
  version.
- Standing floor: **3.8** (proved on 3.8.20; 3.9/3.10/3.14/3.15t also proved).
  3.7 is grammar- and API-clean and is accepted the day a runnable 3.7
  appears. 3.6 is out of scope: it needs a rewrite (no PEP 563, no stdlib
  dataclasses), not a floor-drop.

## The proof ladder (run in order for any floor change)

1. Grammar: `ast.parse` every file with `feature_version=(3, N)`.
2. API sweep: grep for version-gated stdlib (`to_thread`, `removeprefix`,
   `zoneinfo`, `Literal`/`Protocol`/`TypedDict`, walrus, `X | Y` at runtime…).
3. Live run: `uv python install N` → install wheel `--target` → import +
   engine + CLI smoke.
4. Wheel metadata carries the proved floor and every real dependency
   (`install_requires`, e.g. numpy) — a bare interpreter must succeed.

## Build discipline

- Ship `py3-none-any` wheels. Native speedups (`.pyd`/Cython) are optional
  and must sit behind a `try/except ImportError` ENGINE fallback, never a
  hard import.
- No "legacy edition" forks. One codebase reads correctly everywhere and
  fast where free-threaded.
- Swarms are built on `ThreadPoolExecutor`-era primitives so they fan out on
  any floor; free-threading is acceleration, not a prerequisite.
