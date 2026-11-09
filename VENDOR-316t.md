# VENDOR-316t -- vendored 3.16t distribution manifest

Generated 2026-11-09. Everything below was MEASURED on this box, not assumed.

## Interpreter
- Python 3.16.0a1 free-threaded, sys._is_gil_enabled() == False
- venv: C:/Azazael/.venvs/py316t

## Wheels
- cp316t wheelhouse: C:/Azazael/.wheels/cp316t -- 66 wheels
- azazael azazael-1.0.0-py3-none-any.whl (3852733 bytes, sha256 4b2fa61c9812cdb5...) built on 316t via pip wheel . --no-deps

## Native kernels (tools/build_native.py, cp316t .pyd)
- _forensic_cy.cp316t-win_amd64.pyd (224768 bytes)
- _replay_cy.cp316t-win_amd64.pyd (216576 bytes)

## Vendored compat (replaces site-packages sitecustomize shim, deleted 2026-11-09)
- tools/compat_pydantic214.py -- backfills pydantic eval_type_backport via typing._eval_type
- wired into: tools/supervisor_mcp.py, tools/pmb_client.py, barta scripts/barta_scrape_mcp.py, llama-server codegraph_mcp.py + pams_server_launcher.py

## Acceptance baselines
- basedpyright on 316t: 849 files, 47 errors, 41 warnings; baseline logs/basedpyright_baseline.json
- eve native tests on 316t: 20 passed, 1 pre-existing fail (test_gaps_are_named, fails identically on 315t, untouched cognition.py)
- codegraph: 97532 nodes @ ecf93a4bf64d177ffa7fd45952286dde6783a26e == HEAD
- barta registry on 316t: 13 robust sources; native urllib fallback verified 577 bytes/HTTP 200

