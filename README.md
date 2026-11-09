# Eve Unleashed — She Is Unleashed

The house, pruned from the Azazael tree and standing alone. One interpreter,
three children, five books. Stdlib only, offline-first, receipted.

| Tree | What it is | Run it |
| --- | --- | --- |
| `Project_GAMORA/` | Gamora DOMellifluousML Berzerker A-I-O cliT — one command over lilith, eve, jaeger, cradle, lucy, berzerker | `python Project_GAMORA/gamora.py doctor` |
| `Project_LUCY/` | Lucy — Eliza + live therapy, natively combined, plus the colosseum arena | `python Project_GAMORA/gamora.py lucy hopeful "first build"` |
| `src/eve_unleashed/` | Eve Unleashed — inference engine, langs (rust/go/python), wasm tiers, swarm, debunk, cognition, MellifluousML | `python Project_GAMORA/gamora.py eve -- --help` |
| `docs/bible/` | The five books — canon, star-trek, star-wars, emotional, female | `python tools/bible_check.py --check` |
| `Project_GAMORA/berzerker.py` | Berzerker A.I.O. + STEM coding coach for girls | `python Project_GAMORA/gamora.py berzerker code "add two numbers"` |

## Requires

The 316t free-threaded interpreter (`sys._is_gil_enabled() is False`).
`gamora doctor` exits 1 without it and tells you why.

## Gates

- `python -m pytest Project_GAMORA/tests/ -q` — harness + coach, offline
- `python -m pytest tests/ -q` — eve, langs, wasm, arena (needs `src/` on `PYTHONPATH`). Whole-corpus bible gates stay parent-side by design: practice/statute/config references point at parent-tree paths, and rewriting canon to suit a prune is forbidden
- `python tools/bible_check.py --check` — canon corpus (parent tree only, for the reason above)
- `python tools/bible_theme.py --all --check` — themed editions (parent tree only)
- `python tools/staged_scanner_gate.py` — no new anti-patterns (needs `src/` on `PYTHONPATH`)

## Provenance

Pruned export of azazael@001bc3f7 (`Canonize 316t house` + `Land Berzerker
upgrades`). Azazael-only machinery (CORE, AOA, INTERPRETERS, SHARDS,
OpenCode hook wiring) stays in the parent tree; every module here degrades
to a named message when an optional part is absent. See VENDOR-316t.md for
the interpreter and Nuitka notes.
