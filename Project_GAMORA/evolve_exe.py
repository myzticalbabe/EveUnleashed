"""Evolve Gamora's 316t exe over Nuitka build flags with live-measured fitness.

Genome -> policy mapping (E2R-3, written down, no other mapping exists):
  lto      in {no, yes}          -> omit | --lto=yes
  compress in {on, off}          -> omit | --onefile-no-compression
  nofollow in {none, numpy, z3, both}
               -> omit | --nofollow-import-to=numpy | z3-solver | both
Fixed harness (E2R-4, NOT genes): --jobs=16, --include-package=eve_unleashed,
  --standalone --onefile, interpreter C:/Azazael/.venvs/py316t (3.16t).
  jobs only changes build cost, never the product, so it stays fixed.

Fitness (E2R-3, 100% live-measured, denominators always quoted):
  infeasible (build exit != 0, doctor != READY, frozen audit missing)
    -> fitness 0.0 + recorded reason; culled, never patched around.
  feasible -> 0.5 * size_score + 0.5 * speed_score, both min-max
    normalized across the generation's feasible set.
  size_bytes  : os.path.getsize on the built exe (smaller better).
  cold_start_s: wall of the FIRST `exe doctor` run post-build via
    perf_counter (onefile temp-unpack included; product behavior, E2R-4).
    READY required; audit x/y/z parsed from the same run.

Loop: tournament select + uniform crossover + per-gene mutation (0.3),
  elitism 1, pop 3, 2 generations + baseline anchor. Population persisted
  to population_exe.json after EVERY evaluation (E2R-7: inherit, reseed
  never). Early stop when feasible-set stddev < 0.01 (flat gradient is
  information about the environment, E2R-6) — recorded, not run longer.
Shipped dist/gamora/Gamora-win10.exe is NEVER overwritten mid-loop;
  candidates build as Gamora-evo-<tag>.exe. Winner lands only by explicit
  promotion step after full e2e.
"""

import json
import os
import random
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)  # EveUnleashed/
PY316T = "C:/Azazael/.venvs/py316t/Scripts/python.exe"
POP_FILE = os.path.join(HERE, "population_exe.json")
OUT_DIR = os.path.join(ROOT, "dist", "gamora")

BASE_FLAGS = [
    "--standalone", "--onefile", "--assume-yes-for-downloads",
    "--jobs=16", "--include-package=eve_unleashed",
    "--output-dir=" + OUT_DIR,
]
GENES = {
    "lto": ("no", "yes"),
    "compress": ("on", "off"),
    "nofollow": ("none", "numpy", "z3", "both"),
}
BASELINE = {"lto": "no", "compress": "on", "nofollow": "none"}
MUTATION_RATE = 0.3
BUILD_TIMEOUT_S = 1500  # harness bound (E2R-4); product untouched


def flags_for(genome, tag):
    flags = list(BASE_FLAGS)
    if genome["lto"] == "yes":
        flags.append("--lto=yes")
    if genome["compress"] == "off":
        flags.append("--onefile-no-compression")
    nf = genome["nofollow"]
    if nf in ("numpy", "both"):
        flags.append("--nofollow-import-to=numpy")
    if nf in ("z3", "both"):
        flags.append("--nofollow-import-to=z3-solver")
    flags.append("--output-filename=Gamora-evo-%s.exe" % tag)
    flags.append(os.path.join("Project_GAMORA", "gamora.py"))
    return flags


def build(genome, tag):
    env = dict(os.environ)
    env["PYTHONPATH"] = os.path.join(ROOT, "src") + ";" + os.path.join(ROOT, "Project_LUCY")
    t0 = time.perf_counter()
    try:
        p = subprocess.run(
            [PY316T, "-m", "nuitka"] + flags_for(genome, tag),
            cwd=ROOT, env=env, capture_output=True, text=True,
            timeout=BUILD_TIMEOUT_S,
        )
        ok = p.returncode == 0
        tail = (p.stderr or "")[-2000:]
    except subprocess.TimeoutExpired:
        ok, tail = False, "TIMEOUT after %ss" % BUILD_TIMEOUT_S
    return ok, time.perf_counter() - t0, tail


def measure(tag):
    exe = os.path.join(OUT_DIR, "Gamora-evo-%s.exe" % tag)
    if not os.path.exists(exe):
        return None
    size = os.path.getsize(exe)
    t0 = time.perf_counter()
    try:
        p = subprocess.run([exe, "doctor"], capture_output=True, text=True, timeout=300)
    except (subprocess.TimeoutExpired, OSError) as e:
        return {"feasible": False, "reason": "doctor run failed: %s" % e}
    cold = time.perf_counter() - t0
    out = p.stdout or ""
    ready = "doctor: READY" in out
    audit_ok = ("frozen in" in out) and ("therapy (lucy)" in out)
    if p.returncode != 0 or not ready or not audit_ok:
        return {"feasible": False, "reason": "doctor rc=%s ready=%s audit=%s" % (p.returncode, ready, audit_ok),
                "size_bytes": size, "cold_start_s": round(cold, 2)}
    return {"feasible": True, "size_bytes": size, "cold_start_s": round(cold, 2)}


def evaluate(genome, tag):
    ok, build_s, tail = build(genome, tag)
    rec = {"tag": tag, "genome": dict(genome), "build_ok": ok,
           "build_s": round(build_s, 1)}
    if not ok:
        rec.update({"feasible": False, "reason": "build failed: %s" % tail[-300:],
                    "fitness": 0.0})
        return rec
    m = measure(tag)
    if m is None:
        rec.update({"feasible": False, "reason": "exe missing post-build", "fitness": 0.0})
        return rec
    rec.update(m)
    if not m["feasible"]:
        rec["fitness"] = 0.0
        return rec
    rec["fitness"] = None  # normalized across generation once all measured
    return rec


def normalize(recs):
    feas = [r for r in recs if r.get("feasible")]
    if not feas:
        return recs
    sizes = [r["size_bytes"] for r in feas]
    speeds = [r["cold_start_s"] for r in feas]
    for r in feas:
        s_span = max(sizes) - min(sizes) or 1
        t_span = max(speeds) - min(speeds) or 1
        s_score = 1.0 - (r["size_bytes"] - min(sizes)) / s_span
        t_score = 1.0 - (r["cold_start_s"] - min(speeds)) / t_span
        r["fitness"] = round(0.5 * s_score + 0.5 * t_score, 4)
        r["population_n"] = len(recs)
        r["feasible_n"] = len(feas)
    return recs


def mutate(genome, rng):
    child = dict(genome)
    for gene, choices in GENES.items():
        if rng.random() < MUTATION_RATE:
            child[gene] = rng.choice([c for c in choices if c != child[gene]])
    return child


def crossover(a, b, rng):
    return {g: (a[g] if rng.random() < 0.5 else b[g]) for g in GENES}


def tournament(recs, rng):
    cands = rng.sample(recs, min(2, len(recs)))
    cands.sort(key=lambda r: (r.get("fitness") or 0.0), reverse=True)
    return cands[0]["genome"]


def save_pop(population, path=POP_FILE):
    with open(path, "w") as f:
        json.dump(population, f, indent=1)


def load_pop(path=POP_FILE):
    if os.path.exists(path):
        with open(path) as f:
            return json.load(f)
    return None


def run(generations=2, pop_size=3, seed=31616):
    rng = random.Random(seed)
    prior = load_pop()  # E2R-7: inherit a persisted population if present
    if prior and prior.get("population"):
        pop = [p["genome"] for p in prior["population"][:pop_size]]
        start_gen = prior.get("generation", 0)
    else:
        pop = [dict(BASELINE),
               {"lto": "yes", "compress": "on", "nofollow": "none"},
               {"lto": "no", "compress": "on", "nofollow": "both"}]
        start_gen = 0
    history = prior.get("history", []) if prior else []
    for gen in range(start_gen, start_gen + generations):
        recs = []
        for i, genome in enumerate(pop):
            tag = "g%dm%d" % (gen, i)
            rec = evaluate(genome, tag)
            recs.append(rec)
            save_pop({"generation": gen, "population": recs, "history": history})
            print(json.dumps(rec), flush=True)
        recs = normalize(recs)
        save_pop({"generation": gen, "population": recs, "history": history})
        feas = [r["fitness"] for r in recs if r.get("feasible")]
        if feas and len(feas) > 1:
            mean = sum(feas) / len(feas)
            var = sum((f - mean) ** 2 for f in feas) / len(feas)
            if var ** 0.5 < 0.01:
                print("EARLY STOP gen %d: flat gradient stddev=%.4f (E2R-6)" % (gen, var ** 0.5), flush=True)
                history.append({"generation": gen, "results": recs, "early_stop": True})
                save_pop({"generation": gen, "population": recs, "history": history})
                break
        history.append({"generation": gen, "results": recs})
        ranked = sorted(recs, key=lambda r: (r.get("fitness") or 0.0), reverse=True)
        nxt = [ranked[0]["genome"]]  # elitism 1
        while len(nxt) < pop_size:
            child = crossover(tournament(recs, rng), tournament(recs, rng), rng)
            nxt.append(mutate(child, rng))
        pop = nxt
    save_pop({"generation": start_gen + generations, "population": recs, "history": history})
    best = max(recs, key=lambda r: (r.get("fitness") or 0.0))
    print("WINNER: " + json.dumps(best), flush=True)
    return best


if __name__ == "__main__":
    gens = int(sys.argv[1]) if len(sys.argv) > 1 else 2
    run(generations=gens)
